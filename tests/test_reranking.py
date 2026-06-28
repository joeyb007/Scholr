import numpy as np
from unittest.mock import MagicMock
from scholr.reranking import select_top_by_similarity
from scholr.state import Paper


def _paper(pid: str, abstract: str) -> Paper:
    return Paper(paper_id=pid, title=f"Title {pid}", abstract=abstract, source_query="q")


def test_select_top_by_similarity_narrows_to_top_n(mocker):
    papers = [_paper("p1", "a1"), _paper("p2", "a2"), _paper("p3", "a3")]

    fake_model = MagicMock()
    # query embedding, then one embedding per paper abstract, in that call order
    fake_model.encode.side_effect = [
        np.array([1.0, 0.0]),                          # query
        np.array([[0.1, 0.9], [0.95, 0.1], [0.5, 0.5]]),  # p1, p2, p3 abstracts
    ]
    mocker.patch("scholr.reranking._get_bi_encoder", return_value=fake_model)

    result = select_top_by_similarity("query text", papers, top_n=2)

    assert [p.paper_id for p in result] == ["p2", "p3"]


def test_select_top_by_similarity_returns_all_if_pool_smaller_than_top_n(mocker):
    papers = [_paper("p1", "a1"), _paper("p2", "a2")]
    fake_get_model = mocker.patch("scholr.reranking._get_bi_encoder")

    result = select_top_by_similarity("query text", papers, top_n=5)

    assert result == papers
    fake_get_model.assert_not_called()


from scholr.reranking import rerank_by_cross_encoder


def test_rerank_by_cross_encoder_orders_by_score(mocker):
    papers = [_paper("p1", "a1"), _paper("p2", "a2"), _paper("p3", "a3")]

    fake_model = MagicMock()
    fake_model.predict.return_value = np.array([0.2, 0.9, 0.5])
    mocker.patch("scholr.reranking._get_cross_encoder", return_value=fake_model)

    result = rerank_by_cross_encoder("query text", papers, top_k=2)

    assert [p.paper_id for p in result] == ["p2", "p3"]
    call_args = fake_model.predict.call_args[0][0]
    assert call_args[0] == ("query text", "Title p1. a1")


def test_rerank_by_cross_encoder_returns_all_if_fewer_than_top_k(mocker):
    papers = [_paper("p1", "a1")]
    fake_model = MagicMock()
    fake_model.predict.return_value = np.array([0.5])
    mocker.patch("scholr.reranking._get_cross_encoder", return_value=fake_model)

    result = rerank_by_cross_encoder("query text", papers, top_k=5)

    assert [p.paper_id for p in result] == ["p1"]


def test_rerank_by_cross_encoder_empty_input(mocker):
    fake_get_model = mocker.patch("scholr.reranking._get_cross_encoder")

    result = rerank_by_cross_encoder("query text", [], top_k=5)

    assert result == []
    fake_get_model.assert_not_called()


from scholr.reranking import rerank_papers


def test_rerank_papers_narrows_then_reranks(mocker):
    papers = [_paper(f"p{i}", f"a{i}") for i in range(5)]
    narrowed = papers[:3]

    mock_narrow = mocker.patch("scholr.reranking.select_top_by_similarity", return_value=narrowed)
    mock_cross = mocker.patch("scholr.reranking.rerank_by_cross_encoder", return_value=narrowed[:2])

    result = rerank_papers("query text", papers, bi_top_n=3, final_top_k=2)

    mock_narrow.assert_called_once_with("query text", papers, 3)
    mock_cross.assert_called_once_with("query text", narrowed, 2)
    assert result == narrowed[:2]
