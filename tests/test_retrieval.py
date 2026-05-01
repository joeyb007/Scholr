import pytest
from scholr.retrieval import retrieve_papers
from scholr.state import Paper


def _make_paper(paper_id: str) -> Paper:
    return Paper(
        paper_id=paper_id,
        title=f"Title {paper_id}",
        abstract=f"Abstract {paper_id}",
        source_query="test query",
    )


async def test_retrieve_papers_basic(mocker):
    mocker.patch(
        "scholr.retrieval._fetch_arxiv",
        return_value=[_make_paper("p1"), _make_paper("p2")],
    )
    papers = await retrieve_papers(["query1"], set(), lambda _: None)
    assert len(papers) == 2
    assert papers[0].paper_id == "p1"


async def test_retrieve_papers_deduplicates_existing(mocker):
    mocker.patch(
        "scholr.retrieval._fetch_arxiv",
        return_value=[_make_paper("p1"), _make_paper("p2")],
    )
    papers = await retrieve_papers(["query1"], {"p1"}, lambda _: None)
    assert len(papers) == 1
    assert papers[0].paper_id == "p2"


async def test_retrieve_papers_deduplicates_across_queries(mocker):
    mocker.patch(
        "scholr.retrieval._fetch_arxiv",
        return_value=[_make_paper("p1")],
    )
    papers = await retrieve_papers(["q1", "q2"], set(), lambda _: None)
    assert len(papers) == 1


async def test_retrieve_papers_emits_events(mocker):
    mocker.patch("scholr.retrieval._fetch_arxiv", return_value=[])
    events = []
    await retrieve_papers(["query1"], set(), events.append)
    assert any("query1" in e for e in events)


async def test_retrieve_papers_empty_queries(mocker):
    fetch = mocker.patch("scholr.retrieval._fetch_arxiv", return_value=[])
    papers = await retrieve_papers([], set(), lambda _: None)
    assert papers == []
    fetch.assert_not_called()
