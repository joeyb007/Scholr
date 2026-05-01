import asyncio
import time
from collections.abc import Callable
import arxiv
from scholr.state import Paper

_FETCH_TIMEOUT = 30.0
_MAX_RESULTS = 8

# Global semaphore — caps concurrent arXiv requests across all parallel pipelines.
# arXiv rate-limits aggressively; 2 simultaneous requests is safe.
_SEMAPHORE = asyncio.Semaphore(2)


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
                    asyncio.to_thread(_fetch_arxiv, query, _MAX_RESULTS),
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


def _fetch_arxiv(query: str, max_results: int) -> list[Paper]:
    time.sleep(1)  # be a good citizen between requests
    client = arxiv.Client(page_size=max_results, num_retries=3)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    return [
        Paper(
            paper_id=r.entry_id,
            title=r.title,
            abstract=r.summary,
            source_query=query,
        )
        for r in client.results(search)
    ]
