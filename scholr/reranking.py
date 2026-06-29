import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

from scholr.state import Paper

_BI_ENCODER_MODEL = "BAAI/bge-small-en-v1.5"
_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_bi_encoder: SentenceTransformer | None = None
_cross_encoder: CrossEncoder | None = None


def _get_bi_encoder() -> SentenceTransformer:
    global _bi_encoder
    if _bi_encoder is None:
        _bi_encoder = SentenceTransformer(_BI_ENCODER_MODEL)
    return _bi_encoder


def _get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(_CROSS_ENCODER_MODEL)
    return _cross_encoder


def select_top_by_similarity(query: str, papers: list[Paper], top_n: int) -> list[Paper]:
    """Bi-encoder cosine similarity over abstracts only. Narrows a large
    candidate pool down to top_n before the more expensive cross-encoder stage."""
    if len(papers) <= top_n:
        return papers

    model = _get_bi_encoder()
    query_emb = model.encode(query, normalize_embeddings=True)
    paper_embs = model.encode([p.abstract for p in papers], normalize_embeddings=True)
    scores = np.asarray(paper_embs) @ np.asarray(query_emb)

    ranked = sorted(zip(papers, scores), key=lambda pair: pair[1], reverse=True)
    return [p for p, _ in ranked[:top_n]]


def rerank_by_cross_encoder(query: str, papers: list[Paper], top_k: int) -> list[Paper]:
    """Cross-encoder jointly scores query against title+abstract (the full text
    we have per paper) for a precision-focused final rerank."""
    if not papers:
        return []

    model = _get_cross_encoder()
    pairs = [(query, f"{p.title}. {p.abstract}") for p in papers]
    scores = model.predict(pairs)

    ranked = sorted(zip(papers, scores), key=lambda pair: pair[1], reverse=True)
    return [p for p, _ in ranked[:top_k]]


def rerank_papers(
    query: str,
    papers: list[Paper],
    bi_top_n: int,
    final_top_k: int,
) -> list[Paper]:
    """Two-stage rerank: bi-encoder narrows the candidate pool by abstract
    similarity (fast, runs over the full pool), then the cross-encoder does
    a precision-focused rerank on the narrowed set using title+abstract."""
    narrowed = select_top_by_similarity(query, papers, bi_top_n)
    return rerank_by_cross_encoder(query, narrowed, final_top_k)
