import asyncio
import os
from collections.abc import Callable

import httpx

from scholr.state import Paper

_OA_URL = "https://api.openalex.org/works"
_DEFAULT_K = 8
_FETCH_TIMEOUT = 30.0
_DELAY = 0.1  # API key puts us on the polite pool (10 req/sec); 0.1s keeps us well under
_RETRY_429_WAITS = [30, 60]  # seconds to wait on consecutive 429s before giving up

# Adding an email identifies you to OpenAlex's polite pool (higher rate limits).
# Set SCHOLR_MAILTO in your environment or it defaults to a generic identifier.
_MAILTO = os.environ.get("SCHOLR_MAILTO", "scholr-tool")
_API_KEY = os.environ.get("OPENALEX_API_KEY")

# Match semaphore to max queries per round so all fire concurrently within polite pool limits.
_SEMAPHORE = asyncio.Semaphore(5)


async def retrieve_papers(
    queries: list[str],
    existing_ids: set[str],
    on_event: Callable[[str], None],
    k: int = _DEFAULT_K,
    year_from: int | None = None,
) -> list[Paper]:
    seen = set(existing_ids)

    async def fetch_one(query: str) -> list[Paper]:
        on_event(f"[Retrieval] {query}")
        for attempt, wait in enumerate([0] + _RETRY_429_WAITS):
            if wait:
                on_event(f"[Retrieval] rate limited — waiting {wait}s (attempt {attempt}/{len(_RETRY_429_WAITS)})")
                await asyncio.sleep(wait)
            try:
                async with _SEMAPHORE:
                    return await asyncio.wait_for(
                        _fetch_openalex(query, k, year_from),
                        timeout=_FETCH_TIMEOUT,
                    )
            except asyncio.TimeoutError:
                on_event(f"[Retrieval] timeout — skipping: {query}")
                return []
            except Exception as e:
                if "429" in str(e) and attempt < len(_RETRY_429_WAITS):
                    continue
                on_event(f"[Retrieval] error ({type(e).__name__}): {e}")
                return []
        return []

    all_results = await asyncio.gather(*[fetch_one(q) for q in queries])

    results: list[Paper] = []
    for papers in all_results:
        for p in papers:
            if p.paper_id not in seen:
                seen.add(p.paper_id)
                results.append(p)
    return results


_SELECT = "id,title,abstract_inverted_index,ids,authorships,publication_year,primary_location"


async def _fetch_openalex(query: str, max_results: int, year_from: int | None = None) -> list[Paper]:
    await asyncio.sleep(_DELAY)
    # Build params without 'select' — httpx URL-encodes commas (%2C) which OpenAlex
    # does not accept in the select field. We append it raw to the URL instead.
    params: dict = {
        "search": query,
        "per-page": max_results,
        "mailto": _MAILTO,
    }
    if _API_KEY:
        params["api_key"] = _API_KEY
    if year_from is not None:
        params["filter"] = f"from_publication_date:{year_from}-01-01"
    async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as http:
        req = http.build_request("GET", _OA_URL, params=params)
        url = str(req.url) + f"&select={_SELECT}"
        resp = await http.get(url)
        resp.raise_for_status()
        return _parse_works(resp.json().get("results", []), query)


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex stores abstracts as an inverted index {word: [positions]}."""
    if not inverted_index:
        return ""
    pairs = [
        (idx, word)
        for word, indices in inverted_index.items()
        for idx in indices
    ]
    pairs.sort()
    return " ".join(word for _, word in pairs)


def _parse_works(data: list[dict], query: str) -> list[Paper]:
    papers = []
    for item in data:
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
        if not abstract:
            continue
        ids = item.get("ids") or {}
        arxiv_url = ids.get("arxiv", "")
        arxiv_id = arxiv_url.split("abs/")[-1].rstrip("/") if arxiv_url else ""
        paper_id = f"arXiv:{arxiv_id}" if arxiv_id else item["id"].split("/")[-1]

        raw_authors = [
            a.get("author", {}).get("display_name", "")
            for a in (item.get("authorships") or [])[:3]
        ]
        authors = ", ".join(a for a in raw_authors if a)
        if len(item.get("authorships") or []) > 3:
            authors += " et al."

        venue = (
            ((item.get("primary_location") or {}).get("source") or {})
            .get("display_name", "") or ""
        )

        papers.append(Paper(
            paper_id=paper_id,
            title=item.get("title") or "Untitled",
            abstract=abstract,
            source_query=query,
            authors=authors,
            year=item.get("publication_year"),
            venue=venue,
        ))
    return papers
