"""Compares baseline (insertion-order truncation) vs. reranked ordering on
the same labeled candidate pools, reporting precision@k, recall@k, and
nDCG@k for both. Writes eval/results.md.

Usage: python -m eval.run_eval
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("SCHOLR_MAILTO", "josephb338@icloud.com")

from eval.metrics import ndcg_at_k, precision_at_k, recall_at_k
from scholr.reranking import rerank_papers
from scholr.state import Paper

_CANDIDATES_FILE = Path(__file__).parent / "candidates.json"
_LABELS_FILE = Path(__file__).parent / "labels.json"
_RESULTS_FILE = Path(__file__).parent / "results.md"

_TOP_K = 5
_BI_ENCODER_TOP_N = 10


def main() -> None:
    candidates = json.loads(_CANDIDATES_FILE.read_text())
    labels = json.loads(_LABELS_FILE.read_text())

    rows = []
    for qid, entry in candidates.items():
        query = entry["query"]
        papers = [
            Paper(paper_id=p["paper_id"], title=p["title"], abstract=p["abstract"], source_query=query)
            for p in entry["papers"]
        ]
        relevance: dict[str, int] = labels[qid]["judgments"]
        relevant_ids = {pid for pid, score in relevance.items() if score > 0}

        baseline_ranked = [p.paper_id for p in papers]

        reranked_papers = rerank_papers(query, papers, _BI_ENCODER_TOP_N, _TOP_K)
        reranked_ranked = [p.paper_id for p in reranked_papers]

        rows.append({
            "id": qid,
            "query": query,
            "n_candidates": len(papers),
            "baseline": {
                "precision": precision_at_k(baseline_ranked, relevant_ids, _TOP_K),
                "recall": recall_at_k(baseline_ranked, relevant_ids, _TOP_K),
                "ndcg": ndcg_at_k(baseline_ranked, relevance, _TOP_K),
            },
            "reranked": {
                "precision": precision_at_k(reranked_ranked, relevant_ids, _TOP_K),
                "recall": recall_at_k(reranked_ranked, relevant_ids, _TOP_K),
                "ndcg": ndcg_at_k(reranked_ranked, relevance, _TOP_K),
            },
        })
        print(
            f"{qid}: baseline nDCG@{_TOP_K}={rows[-1]['baseline']['ndcg']:.3f}  "
            f"reranked nDCG@{_TOP_K}={rows[-1]['reranked']['ndcg']:.3f}"
        )

    def _avg(key: str, metric: str) -> float:
        return sum(r[key][metric] for r in rows) / len(rows)

    print(f"\nBaseline  P@{_TOP_K}={_avg('baseline','precision'):.3f}  R@{_TOP_K}={_avg('baseline','recall'):.3f}  nDCG@{_TOP_K}={_avg('baseline','ndcg'):.3f}")
    print(f"Reranked  P@{_TOP_K}={_avg('reranked','precision'):.3f}  R@{_TOP_K}={_avg('reranked','recall'):.3f}  nDCG@{_TOP_K}={_avg('reranked','ndcg'):.3f}")

    lines = [
        "# Reranking Eval Results",
        "",
        f"Benchmark: {len(rows)} hand-written queries, LLM-as-judge relevance labels (0/1/2), top-{_TOP_K} comparison.",
        "",
        f"| Metric | Baseline (insertion order) | Reranked (bi-encoder + cross-encoder) |",
        "|---|---|---|",
        f"| Precision@{_TOP_K} | {_avg('baseline', 'precision'):.3f} | {_avg('reranked', 'precision'):.3f} |",
        f"| Recall@{_TOP_K} | {_avg('baseline', 'recall'):.3f} | {_avg('reranked', 'recall'):.3f} |",
        f"| nDCG@{_TOP_K} | {_avg('baseline', 'ndcg'):.3f} | {_avg('reranked', 'ndcg'):.3f} |",
        "",
        "## Per-query breakdown",
        "",
        f"| Query | Candidates | Baseline nDCG@{_TOP_K} | Reranked nDCG@{_TOP_K} |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['query']} | {r['n_candidates']} "
            f"| {r['baseline']['ndcg']:.3f} | {r['reranked']['ndcg']:.3f} |"
        )

    lines += [
        "",
        "## Methodology",
        "",
        "- Candidate pools captured by querying OpenAlex directly with keyword search "
        f"(per-page={_TOP_K*2}, one request per query, sequential with 3s delay).",
        "- Relevance judged by an LLM (Claude) reading each paper's title+abstract against the query, "
        "graded 0 (not relevant) / 1 (relevant) / 2 (highly relevant). LLM-as-judge labeling — "
        "not independent human annotation.",
        f"- Baseline: insertion order from OpenAlex, truncated to top {_TOP_K}.",
        f"- Reranked: bi-encoder (`BAAI/bge-small-en-v1.5`) cosine similarity over abstracts "
        f"narrows pool to top {_BI_ENCODER_TOP_N}, then cross-encoder "
        f"(`cross-encoder/ms-marco-MiniLM-L-6-v2`) scores query vs title+abstract for final top {_TOP_K}.",
        "",
        "## Limitations",
        "",
        "- 20 queries is a small sample — treat averages as directional, not statistically rigorous.",
        "- LLM-as-judge labeling may correlate with the LLM-driven retrieval pipeline's biases.",
        "- Cross-encoder trained on MS MARCO (general web passages), not scientific text.",
        "- Eval uses simple direct-query capture rather than the full production pipeline's "
        "multi-round retrieval, so candidate pools are smaller than in production (6-8 vs 15-60 papers).",
    ]

    _RESULTS_FILE.write_text("\n".join(lines))
    print(f"\nWrote results to {_RESULTS_FILE}")


if __name__ == "__main__":
    main()
