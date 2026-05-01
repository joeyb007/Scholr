import asyncio
import argparse
from uuid import uuid4
from scholr.pipeline import run_pipeline


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scholr — bounded recursive arXiv research assistant"
    )
    parser.add_argument("query", nargs="+", help="Research question")
    parser.add_argument("--session", default=None, help="Resume a previous session ID")
    args = parser.parse_args()

    query = " ".join(args.query)
    session_id = args.session or str(uuid4())

    print(f"Session: {session_id}")
    print(f"Query: {query}\n")

    state = await run_pipeline(
        query=query,
        session_id=session_id,
        on_event=lambda e: print(e, flush=True),
    )

    out = state.final_output
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"ANSWER\n{out.final_answer}\n")
    print(f"INTUITION\n{out.intuition}\n")
    print(f"MECHANISM\n{out.mechanism}\n")
    print(f"LIMITATIONS\n{out.limitations}\n")
    print(f"OPEN QUESTIONS\n{out.open_questions}\n")
    print(f"EVIDENCE ({len(out.evidence_map)} claims)")
    for claim in out.evidence_map:
        print(f"  • {claim.claim}")
        print(f"    sources: {', '.join(claim.paper_ids)}")
    print(f"\nPapers used: {out.papers_used} | Depth reached: {state.depth_reached}")
    print(f"Session ID: {state.session_id}")


asyncio.run(main())
