import asyncio
import os
from collections.abc import Callable

import httpx

from scholr.state import Paper

_S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_S2_FIELDS = "paperId,title,abstract,externalIds"
_MAX_RESULTS = 8
_FETCH_TIMEOUT = 30.0

# With a free API key: 1 req/sec. Without: 100 req/5min (~1 req/3sec).
_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
_DELAY = 1.1 if _API_KEY else 3.1

# One request at a time — enforced globally across all parallel pipelines.
_SEMAPHORE = asyncio.Semaphore(1)


async def retrieve_papers(
    queries: list[str],
    existing_ids: set[str],
    on_event: Callable[[str], None],
) -> list[Paper]:
    seen = set(existing_ids)

    async def fetch_one(query: str) -> list[Paper]:
        on_event(f"[Retrieval] {query}")
        try:
            async with _SEMAPHORE:
                return await asyncio.wait_for(
                    _fetch_s2(query, _MAX_RESULTS),
                    timeout=_FETCH_TIMEOUT,
                )
        except asyncio.TimeoutError:
            on_event(f"[Retrieval] timeout — skipping: {query}")
            return []
        except Exception as e:
            on_event(f"[Retrieval] error ({type(e).__name__}): {e}")
            return []

    all_results = await asyncio.gather(*[fetch_one(q) for q in queries])

    results: list[Paper] = []
    for papers in all_results:
        for p in papers:
            if p.paper_id not in seen:
                seen.add(p.paper_id)
                results.append(p)
    return results


async def _fetch_s2(query: str, max_results: int) -> list[Paper]:
    await asyncio.sleep(_DELAY)
    headers = {"x-api-key": _API_KEY} if _API_KEY else {}
    async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as http:
        resp = await http.get(
            _S2_URL,
            params={"query": query, "fields": _S2_FIELDS, "limit": max_results},
            headers=headers,
        )
        resp.raise_for_status()
        return _parse_papers(resp.json().get("data", []), query)


def _parse_papers(data: list[dict], query: str) -> list[Paper]:
    papers = []
    for item in data:
        abstract = item.get("abstract")
        if not abstract:
            continue
        arxiv_id = (item.get("externalIds") or {}).get("ArXiv")
        paper_id = f"arXiv:{arxiv_id}" if arxiv_id else item["paperId"]
        papers.append(Paper(
            paper_id=paper_id,
            title=item.get("title", "Untitled"),
            abstract=abstract,
            source_query=query,
        ))
    return papers
