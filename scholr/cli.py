import asyncio
import argparse
import os
import sys
from uuid import uuid4

from openai import AuthenticationError
from pyfiglet import figlet_format
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.align import Align
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from scholr.llm import set_api_key, validate_api_key
from scholr.orchestrator import run_research

console = Console()

_LABELS: list[tuple[str, str]] = [
    ("[Session]",     "session   "),
    ("[Planner]",     "planner   "),
    ("[Retrieval]",   "fetch     "),
    ("[Level",        "expand    "),
    ("[Expansion]",   "expand    "),
    ("[Coverage]",    "coverage  "),
    ("[Compression]", "compress  "),
    ("[Synthesis]",   "synthesize"),
    ("[Done]",        "done      "),
]

_HINTS = [
    "explain transformer architecture",
    "how do diffusion models work",
    "what are the limits of RLHF",
]


def _print_logo() -> None:
    for line in figlet_format("Scholr", font="slant").splitlines():
        styled = Text(no_wrap=True)
        for char in line:
            if char in "/\\":
                styled.append(char, style="bright_white")
            elif char == "_":
                styled.append(char, style="grey62")
            else:
                styled.append(char)
        console.print(Align(styled, align="center"))


def _short_id(paper_id: str) -> str:
    if paper_id.startswith("arXiv:"):
        return paper_id[6:]
    return paper_id[:12]


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _print_wrapped(text: str, width: int = 80) -> None:
    import textwrap
    for line in textwrap.wrap(text, width=width):
        console.print(f"  {line}")


def _event_label(event: str) -> str:
    for prefix, label in _LABELS:
        if event.startswith(prefix):
            rest = event[len(prefix):].strip()
            return f"  [dim]{label}[/dim]  {rest}"
    return f"  [dim]{event}[/dim]"


class _TooComplexError(Exception):
    pass


async def run_query(query: str, session_id: str) -> str:
    answer_started = False

    def on_token(token: str) -> None:
        nonlocal answer_started
        if not answer_started:
            answer_started = True
            status.stop()
            console.print()
            console.print("  [bold]Answer[/bold]")
            console.print()
            console.print("  ", end="")
        sys.stdout.write(token)
        sys.stdout.flush()

    try:
        with console.status("  [dim]initializing...[/dim]", spinner="dots") as status:
            def on_event(event: str) -> None:
                low = event.lower()
                if "error" in low or "timeout" in low or "failed" in low:
                    console.print(f"  [dim]{event}[/dim]")
                elif not answer_started:
                    status.update(_event_label(event))
                elif "[Synthesis]" in event and "building evidence map" in event:
                    sys.stdout.write("\n\n")
                    sys.stdout.flush()
                    status.update("  [dim]synthesize  [/dim]  building evidence map")
                    status.start()

            result = await run_research(
                query=query,
                session_id=session_id,
                on_event=on_event,
                on_token=on_token,
            )
            if isinstance(result, str):
                raise _TooComplexError(result)
            state = result
    except _TooComplexError as e:
        console.print(f"\n  [dim]Query too complex.[/dim]\n\n  {e}\n")
        return session_id
    except KeyboardInterrupt:
        if answer_started:
            console.print()
        console.print("\n  [dim]cancelled[/dim]\n")
        return session_id
    except AuthenticationError:
        if answer_started:
            console.print()
        console.print("\n  [red]Invalid API key.[/red]")
        console.print("  Run [dim]export OPENAI_API_KEY=sk-...[/dim] and restart, or type your key at the prompt.\n")
        return session_id
    except ValueError as e:
        if answer_started:
            console.print()
        console.print(f"\n  [dim]{e}[/dim]\n")
        return session_id

    out = state.final_output

    if not answer_started:
        console.print()
        console.print("  [bold]Answer[/bold]")
        console.print()
        _print_wrapped(out.final_answer)
    console.print()

    for label, content in [
        ("Mechanism",      out.mechanism),
        ("Intuition",      out.intuition),
        ("Limitations",    out.limitations),
        ("Open Questions", out.open_questions),
    ]:
        console.print(f"  [dim]{label}[/dim]")
        _print_wrapped(content)
        console.print()

    console.rule(style="dim")
    console.print()

    paper_by_id = {p.paper_id: p for p in state.papers}

    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style="dim",
        padding=(0, 2),
        show_edge=False,
    )
    table.add_column("Paper ID",  style="dim",   no_wrap=True)
    table.add_column("Title",     style="dim",   max_width=36)
    table.add_column("Claim",     style="white")

    for claim in out.evidence_map:
        for i, pid in enumerate(claim.paper_ids):
            paper = paper_by_id.get(pid)
            title = _truncate(paper.title, 36) if paper else ""
            table.add_row(
                _short_id(pid),
                title,
                claim.claim if i == 0 else "",
            )

    console.print(f"  [dim]evidence · {len(out.evidence_map)} claims[/dim]")
    console.print()
    console.print(table)

    console.rule(style="dim")
    console.print()
    footer = Text(justify="center")
    footer.append(f"{out.papers_used} papers", style="white")
    footer.append("  ·  ", style="dim")
    footer.append(f"depth {state.depth_reached}", style="white")
    footer.append("  ·  ", style="dim")
    footer.append(f"session {state.session_id[:8]}", style="dim")
    console.print(Align(footer, align="center"))
    console.print()

    return state.session_id


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scholr — bounded recursive arXiv research assistant"
    )
    parser.add_argument("--session", default=None, help="Resume a previous session ID")
    args = parser.parse_args()

    console.print()
    _print_logo()
    console.rule(style="dim")
    console.print()

    session_id = args.session or str(uuid4())

    prompt_session: PromptSession = PromptSession(
        style=Style.from_dict({"prompt": "ansigray"}),
    )

    async def _prompt_for_key(reason: str) -> bool:
        console.print(f"  [dim]{reason}[/dim]")
        try:
            key = await PromptSession().prompt_async("  API key: ", is_password=True)
            key = key.strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n  [dim]goodbye[/dim]\n")
            return False
        if not key:
            console.print("  [dim]No key provided. Exiting.[/dim]\n")
            return False
        set_api_key(key)
        return True

    async def _validate_with_spinner() -> bool:
        with console.status("  [dim]validating API key...[/dim]", spinner="dots"):
            return await validate_api_key()

    if not os.environ.get("OPENAI_API_KEY"):
        if not await _prompt_for_key("No OPENAI_API_KEY found."):
            return
        if not await _validate_with_spinner():
            console.print("  [red]Key rejected by OpenAI.[/red] Check it and try again.\n")
            return
        console.print("  [dim]key valid — to persist: export OPENAI_API_KEY=sk-...[/dim]")
        console.print()
    else:
        if not await _validate_with_spinner():
            if not await _prompt_for_key("API key in environment is invalid."):
                return
            if not await _validate_with_spinner():
                console.print("  [red]Key rejected by OpenAI.[/red] Check it and try again.\n")
                return
            console.print("  [dim]key valid — to persist: export OPENAI_API_KEY=sk-...[/dim]")
            console.print()

    first_prompt = True
    while True:
        if first_prompt:
            console.print(f'  [dim]e.g. "{_HINTS[0]}"[/dim]')
            console.print("  [dim]ctrl+c to exit[/dim]")
            first_prompt = False

        try:
            query = await prompt_session.prompt_async("  > ")
            query = query.strip()
        except KeyboardInterrupt:
            console.print("\n  [dim]goodbye[/dim]\n")
            break
        except EOFError:
            break

        if not query:
            continue

        if query.lower() in {"exit", "quit", "q"}:
            console.print("\n  [dim]goodbye[/dim]\n")
            break

        console.print()
        session_id = await run_query(query, session_id)


def sync_main() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    sync_main()
