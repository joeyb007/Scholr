import asyncio
from collections.abc import Callable
import arxiv
from scholr.state import Paper

_FETCH_TIMEOUT = 15.0


async def retrieve_papers(
    queries: list[str],
    existing_ids: set[str],
    on_event: Callable[[str], None],
) -> list[Paper]:
    seen = set(existing_ids)

    async def fetch_one(query: str) -> list[Paper]:
        on_event(f"[Retrieval] {query}")
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_fetch_arxiv, query, 8),
                timeout=_FETCH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            on_event(f"[Retrieval] timeout — skipping: {query}")
            return []
        except Exception:
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
    client = arxiv.Client(num_retries=2)
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
