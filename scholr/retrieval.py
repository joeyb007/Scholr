import asyncio
from collections.abc import Callable
import arxiv
from scholr.state import Paper


async def retrieve_papers(
    queries: list[str],
    existing_ids: set[str],
    on_event: Callable[[str], None],
) -> list[Paper]:
    seen = set(existing_ids)
    results: list[Paper] = []
    for query in queries:
        on_event(f"[Retrieval] {query}")
        papers = await asyncio.to_thread(_fetch_arxiv, query, 8)
        for p in papers:
            if p.paper_id not in seen:
                seen.add(p.paper_id)
                results.append(p)
    return results


def _fetch_arxiv(query: str, max_results: int) -> list[Paper]:
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
        for r in search.results()
    ]
