import pytest
from unittest.mock import AsyncMock
from scholr.compression import compress_papers
from scholr.state import CompressionOutput, PaperCompression, ResearchState, Paper


def _make_state() -> ResearchState:
    return ResearchState(
        query="test", session_id="s1",
        papers=[
            Paper(paper_id="p1", title="T1", abstract="A1", source_query="q1"),
            Paper(paper_id="p2", title="T2", abstract="A2", source_query="q2"),
        ],
    )


async def test_compress_papers_returns_facts_dict(mocker):
    expected = CompressionOutput(compressions=[
        PaperCompression(paper_id="p1", key_points=["fact1", "fact2", "fact3"]),
        PaperCompression(paper_id="p2", key_points=["fact4", "fact5", "fact6"]),
    ])
    mocker.patch("scholr.compression.llm_parse", new_callable=AsyncMock, return_value=expected)

    result = await compress_papers(_make_state(), lambda _: None)
    assert "p1" in result
    assert "p2" in result
    assert len(result["p1"]) == 3


async def test_compress_papers_emits_event(mocker):
    mocker.patch(
        "scholr.compression.llm_parse",
        new_callable=AsyncMock,
        return_value=CompressionOutput(compressions=[
            PaperCompression(paper_id="p1", key_points=["f1", "f2", "f3"]),
        ]),
    )
    state = ResearchState(
        query="test", session_id="s1",
        papers=[Paper(paper_id="p1", title="T1", abstract="A1", source_query="q1")],
    )
    events = []
    await compress_papers(state, events.append)
    assert any("[Compression]" in e for e in events)
