import asyncio
import argparse
from uuid import uuid4

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

from scholr.pipeline import run_pipeline

console = Console()

_EVENT_STYLES: list[tuple[str, str, str]] = [
    ("[Session]",    "dim cyan",          "SESSION   "),
    ("[Planner]",    "bold yellow",        "PLANNER   "),
    ("[Retrieval]",  "cyan",               "FETCH     "),
    ("[Level",       "bold green",         "EXPAND    "),
    ("[Expansion]",  "green",              "EXPAND    "),
    ("[Coverage]",   "magenta",            "COVERAGE  "),
    ("[Compression]","yellow",             "COMPRESS  "),
    ("[Synthesis]",  "bold bright_yellow", "SYNTHESIZE"),
    ("[Done]",       "bold green",         "DONE      "),
]


def _print_event(event: str) -> None:
    for prefix, style, label in _EVENT_STYLES:
        if event.startswith(prefix):
            rest = event[len(prefix):].strip()
            tag = f"[{style}]{label}[/{style}]"
            console.print(f"  {tag}  {rest}")
            return
    console.print(f"  {event}", style="dim")


def _short_id(paper_id: str) -> str:
    part = paper_id.split("/abs/")[-1]
    return part.split("v")[0] if "v" in part else part


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scholr — bounded recursive arXiv research assistant"
    )
    parser.add_argument("query", nargs="+", help="Research question")
    parser.add_argument("--session", default=None, help="Resume a previous session ID")
    args = parser.parse_args()

    query = " ".join(args.query)
    session_id = args.session or str(uuid4())

    console.print()
    console.rule("[bold]Scholr[/bold]", style="dim")
    console.print(f"  [dim]query[/dim]    {query}")
    console.print(f"  [dim]session[/dim]  {session_id}")
    console.print()

    state = await run_pipeline(
        query=query,
        session_id=session_id,
        on_event=_print_event,
    )

    out = state.final_output
    console.print()
    console.rule(
        f"[dim]{out.papers_used} papers · depth {state.depth_reached}[/dim]",
        style="dim",
    )
    console.print()

    console.print(Panel(
        f"[white]{out.final_answer}[/white]",
        title="[bold]Answer[/bold]",
        border_style="bright_yellow",
        padding=(1, 2),
    ))
    console.print()

    for label, content in [
        ("Intuition",       out.intuition),
        ("Mechanism",       out.mechanism),
        ("Limitations",     out.limitations),
        ("Open Questions",  out.open_questions),
    ]:
        console.print(f"  [bold]{label}[/bold]")
        console.print(f"  {content}")
        console.print()

    console.rule(f"[dim]Evidence · {len(out.evidence_map)} claims[/dim]", style="dim")
    console.print()

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    table.add_column("Claim", style="white", ratio=3)
    table.add_column("Papers", style="cyan", ratio=1)

    for claim in out.evidence_map:
        ids = "  ".join(_short_id(pid) for pid in claim.paper_ids)
        table.add_row(claim.claim, ids)

    console.print(table)

    console.rule(style="dim")
    footer = Text()
    footer.append("  session  ", style="dim")
    footer.append(state.session_id, style="cyan")
    footer.append("    papers  ", style="dim")
    footer.append(str(out.papers_used), style="white")
    footer.append("    depth  ", style="dim")
    footer.append(str(state.depth_reached), style="white")
    console.print(footer)
    console.print()


asyncio.run(main())
