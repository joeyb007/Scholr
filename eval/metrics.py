import math


def precision_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of the top-k ranked items that are relevant."""
    top_k = ranked_ids[:k]
    if not top_k:
        return 0.0
    return sum(1 for pid in top_k if pid in relevant_ids) / len(top_k)


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of all relevant items captured within the top-k ranked items."""
    if not relevant_ids:
        return 0.0
    top_k = ranked_ids[:k]
    return sum(1 for pid in top_k if pid in relevant_ids) / len(relevant_ids)


def _dcg_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    top_k = ranked_ids[:k]
    return sum(
        relevance.get(pid, 0) / math.log2(i + 2)
        for i, pid in enumerate(top_k)
    )


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    """Normalized Discounted Cumulative Gain — rewards relevant items appearing
    earlier in the ranking, not just appearing somewhere in the top-k."""
    dcg = _dcg_at_k(ranked_ids, relevance, k)
    ideal_order = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal_order))
    return dcg / idcg if idcg > 0 else 0.0
