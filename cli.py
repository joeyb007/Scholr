import asyncio
import argparse
import sys
from uuid import uuid4

from pyfiglet import figlet_format
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from scholr.pipeline import run_pipeline

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


def _short_id(paper_id: str) -> str:
    part = paper_id.split("/abs/")[-1]
    return part.split("v")[0] if "v" in part else part


def _event_label(event: str) -> str:
    for prefix, label in _LABELS:
        if event.startswith(prefix):
            rest = event[len(prefix):].strip()
            return f"  [dim]{label}[/dim]  {rest}"
    return f"  [dim]{event}[/dim]"


async def run_query(query: str, session_id: str) -> None:
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

    with console.status("  [dim]initializing...[/dim]", spinner="dots") as status:
        def on_event(event: str) -> None:
            status.update(_event_label(event))

        state = await run_pipeline(
            query=query,
            session_id=session_id,
            on_event=on_event,
            on_token=on_token,
        )

    out = state.final_output

    if answer_started:
        console.print("\n")
    else:
        console.print()
        console.print("  [bold]Answer[/bold]")
        console.print()
        console.print(f"  {out.final_answer}\n")

    for label, content in [
        ("Mechanism",      out.mechanism),
        ("Intuition",      out.intuition),
        ("Limitations",    out.limitations),
        ("Open Questions", out.open_questions),
    ]:
        console.print(f"  [dim]{label}[/dim]")
        console.print(f"  {content}")
        console.print()

    console.rule(style="dim")
    console.print()

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), show_edge=False)
    table.add_column("Claim", style="white", ratio=4)
    table.add_column("Papers", style="dim", ratio=1)
    for claim in out.evidence_map:
        ids = "  ".join(_short_id(pid) for pid in claim.paper_ids)
        table.add_row(claim.claim, ids)

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
    console.print(Align(
        figlet_format("Scholr", font="slant"),
        align="center",
        style="bold white",
    ))
    console.rule(style="dim")
    console.print()

    session_id = args.session or str(uuid4())

    while True:
        try:
            query = console.input("  [dim]>[/dim] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not query:
            continue

        if query.lower() in {"exit", "quit", "q"}:
            break

        console.print()
        session_id = await run_query(query, session_id)


asyncio.run(main())
