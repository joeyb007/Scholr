import asyncio
import argparse
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


def _print_event(event: str) -> None:
    for prefix, label in _LABELS:
        if event.startswith(prefix):
            rest = event[len(prefix):].strip()
            console.print(f"  [dim]{label}[/dim]  {rest}")
            return
    console.print(f"  [dim]{event}[/dim]")


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
    console.print(Align(
        figlet_format("Scholr", font="slant"),
        align="center",
        style="bold white",
    ))

    console.rule(style="dim")
    console.print()

    console.print(Align(
        Panel(
            f"[white]{query}[/white]",
            subtitle=f"[dim]session · {session_id[:8]}[/dim]",
            border_style="dim",
            padding=(0, 2),
            width=60,
        ),
        align="center",
    ))
    console.print()

    state = await run_pipeline(
        query=query,
        session_id=session_id,
        on_event=_print_event,
    )

    out = state.final_output
    console.print()
    console.rule(style="dim")
    console.print()

    console.print("  [bold]Answer[/bold]")
    console.print()
    console.print(f"  {out.final_answer}")
    console.print()

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

    table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 2),
        show_edge=False,
    )
    table.add_column("Claim", style="white", ratio=4)
    table.add_column("Papers", style="dim", ratio=1)

    for claim in out.evidence_map:
        ids = "  ".join(_short_id(pid) for pid in claim.paper_ids)
        table.add_row(claim.claim, ids)

    console.print(Align(f"  [dim]evidence · {len(out.evidence_map)} claims[/dim]", align="left"))
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


asyncio.run(main())
