# Reranking Eval Results

Benchmark: 20 hand-written queries, LLM-as-judge relevance labels (0/1/2), top-5 comparison.

| Metric | Baseline (insertion order) | Reranked (bi-encoder + cross-encoder) |
|---|---|---|
| Precision@5 | 0.720 | 0.780 |
| Recall@5 | 0.742 | 0.789 |
| nDCG@5 | 0.751 | 0.832 |

## Per-query breakdown

| Query | Candidates | Baseline nDCG@5 | Reranked nDCG@5 |
|---|---|---|---|
| How does backpropagation work in neural networks? | 7 | 0.620 | 0.891 |
| What is the attention mechanism in transformer models? | 7 | 0.701 | 0.902 |
| What are the limitations of convolutional neural networks for image classification? | 6 | 0.967 | 0.531 |
| How does reinforcement learning from human feedback (RLHF) work? | 8 | 0.869 | 0.934 |
| What causes catastrophic forgetting in neural networks? | 7 | 1.000 | 1.000 |
| How do diffusion models generate images? | 6 | 0.872 | 0.822 |
| What is the vanishing gradient problem and how is it solved? | 6 | 0.631 | 0.500 |
| How does contrastive learning work in self-supervised representation learning? | 8 | 0.401 | 0.916 |
| What are graph neural networks used for? | 6 | 0.680 | 0.733 |
| What is the role of positional encoding in transformer models? | 8 | 0.906 | 0.235 |
| What is knowledge distillation in deep learning? | 7 | 0.750 | 1.000 |
| How do variational autoencoders learn latent representations? | 8 | 0.979 | 0.922 |
| How does federated learning preserve data privacy? | 7 | 1.000 | 1.000 |
| What are the theoretical guarantees of generative adversarial networks? | 8 | 0.840 | 0.896 |
| How does curriculum learning improve neural network training? | 8 | 0.778 | 1.000 |
| What causes mode collapse in GANs and how can it be mitigated? | 8 | 0.891 | 0.516 |
| How do mixture-of-experts architectures scale large language models? | 8 | 0.395 | 0.902 |
| What is the lottery ticket hypothesis in neural network pruning? | 8 | 0.915 | 1.000 |
| How does retrieval-augmented generation reduce hallucination in language models? | 8 | 0.647 | 0.934 |
| What is the double descent phenomenon in deep learning generalization? | 7 | 0.168 | 1.000 |

## Methodology

- Candidate pools captured by querying OpenAlex directly with keyword search (per-page=10, one request per query, sequential with 3s delay).
- Relevance judged by an LLM (Claude) reading each paper's title+abstract against the query, graded 0 (not relevant) / 1 (relevant) / 2 (highly relevant). LLM-as-judge labeling — not independent human annotation.
- Baseline: insertion order from OpenAlex, truncated to top 5.
- Reranked: bi-encoder (`BAAI/bge-small-en-v1.5`) cosine similarity over abstracts narrows pool to top 10, then cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) scores query vs title+abstract for final top 5.

## Limitations

- 20 queries is a small sample — treat averages as directional, not statistically rigorous.
- LLM-as-judge labeling may correlate with the LLM-driven retrieval pipeline's biases.
- Cross-encoder trained on MS MARCO (general web passages), not scientific text.
- Eval uses simple direct-query capture rather than the full production pipeline's multi-round retrieval, so candidate pools are smaller than in production (6-8 vs 15-60 papers).