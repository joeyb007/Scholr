import pytest
from eval.metrics import precision_at_k, recall_at_k, ndcg_at_k


def test_precision_at_k_counts_relevant_in_top_k():
    ranked = ["p1", "p2", "p3", "p4"]
    relevant = {"p1", "p3"}
    assert precision_at_k(ranked, relevant, k=2) == 0.5
    assert precision_at_k(ranked, relevant, k=4) == 0.5


def test_precision_at_k_empty_ranked_list():
    assert precision_at_k([], {"p1"}, k=5) == 0.0


def test_recall_at_k_counts_fraction_of_relevant_found():
    ranked = ["p1", "p2", "p3"]
    relevant = {"p1", "p3", "p5"}
    assert recall_at_k(ranked, relevant, k=2) == pytest.approx(1 / 3)
    assert recall_at_k(ranked, relevant, k=3) == pytest.approx(2 / 3)


def test_recall_at_k_no_relevant_papers():
    assert recall_at_k(["p1"], set(), k=5) == 0.0


def test_ndcg_at_k_perfect_ranking_scores_one():
    ranked = ["p1", "p2", "p3"]
    relevance = {"p1": 2, "p2": 1, "p3": 0}
    assert ndcg_at_k(ranked, relevance, k=3) == pytest.approx(1.0)


def test_ndcg_at_k_worse_ranking_scores_less_than_one():
    ranked = ["p3", "p2", "p1"]  # reversed: worst paper first
    relevance = {"p1": 2, "p2": 1, "p3": 0}
    score = ndcg_at_k(ranked, relevance, k=3)
    assert 0.0 <= score < 1.0


def test_ndcg_at_k_no_relevant_papers_scores_zero():
    assert ndcg_at_k(["p1", "p2"], {}, k=2) == 0.0
