"""Captures a candidate paper pool for each benchmark query directly from
OpenAlex — one request per query, run strictly sequentially with a delay
between requests.

Usage: python -m eval.capture_candidates
"""
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

os.environ["SCHOLR_MAILTO"] = "josephb338@icloud.com"

from scholr.retrieval import _fetch_openalex

_QUERIES_FILE = Path(__file__).parent / "queries.json"
_OUTPUT_FILE = Path(__file__).parent / "candidates.json"
_DELAY_BETWEEN_REQUESTS = 3
_CANDIDATES_PER_QUERY = 8


async def main() -> None:
    queries = json.loads(_QUERIES_FILE.read_text())

    output: dict = {}
    if _OUTPUT_FILE.exists():
        output = json.loads(_OUTPUT_FILE.read_text())
        print(f"Resuming — {len(output)} queries already captured")

    for i, item in enumerate(queries, start=1):
        if item["id"] in output:
            print(f"[{i}/{len(queries)}] Skipping {item['id']} (already captured)")
            continue

        keywords = item["keywords"]
        print(f"[{i}/{len(queries)}] {item['query']}")
        print(f"  search: '{keywords}'")
        try:
            papers = await _fetch_openalex(keywords, _CANDIDATES_PER_QUERY)
            output[item["id"]] = {
                "query": item["query"],
                "papers": [
                    {"paper_id": p.paper_id, "title": p.title, "abstract": p.abstract}
                    for p in papers
                ],
            }
            print(f"  -> {len(papers)} candidates")
        except Exception as e:
            print(f"  -> FAILED: {e} — skipping")

        _OUTPUT_FILE.write_text(json.dumps(output, indent=2))

        if i < len(queries):
            await asyncio.sleep(_DELAY_BETWEEN_REQUESTS)

    print(f"\nDone. {len(output)} query candidate pools written to {_OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
