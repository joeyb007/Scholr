<p align="center">
  <img alt="Scholr" src="web/public/scholr.png" width="100">
</p>

<p align="center">
  A recursive AI research assistant that retrieves, reranks, and synthesizes academic papers into structured, evidence-grounded explanations.
</p>

<p align="center">
  <a href="https://tryscholr.com"><strong>tryscholr.com</strong></a>
</p>

<br>

---

## How it works

Ask a research question. Scholr decomposes it into subtopics, runs a bounded recursive retrieval pipeline per subtopic, reranks candidates using a bi-encoder + cross-encoder stack, and synthesizes a final explanation where every claim is traced to a real paper.

```
Query
  → Decomposer        detect subtopics (e.g. "contrast CNNs and RNNs" → 2 threads)
  → Per subtopic:
      Planner         GPT-4o generates targeted search queries (retries up to 3× if no results)
      Retrieval       OpenAlex API — 200M+ papers, up to 60 candidates per subtopic
      Expansion       extract concepts, generate follow-up queries
      Reranking       bi-encoder (BAAI/bge-small-en-v1.5) cosine similarity over abstracts
                      → cross-encoder (ms-marco-MiniLM-L-6-v2) scores query + title + abstract
                      → top 15 papers selected for synthesis
      Compression     abstracts → atomic factual statements
      Synthesis       structured explanation per subtopic
  → Compare           meta-synthesis combining all subtopics with evidence map
```

- Hallucinated citations are stripped automatically
- Recursion is hard-capped at depth 2; candidate pools capped at 60 before reranking
- Session state persists in Postgres across follow-up questions so the planner steers toward unexplored concepts
- Exposed as a web app, interactive CLI, and MCP tool for Claude Desktop / Cursor

---

## Reranking eval

Two-stage reranking measured against a 20-query ML/AI benchmark with LLM-as-judge relevance labels (0 = not relevant / 1 = relevant / 2 = highly relevant).

| Metric | Baseline (insertion order) | Reranked (bi-encoder + cross-encoder) | Δ |
|---|---|---|---|
| Precision@5 | 0.720 | 0.780 | +8.3% |
| Recall@5 | 0.742 | 0.789 | +6.3% |
| nDCG@5 | 0.751 | 0.832 | **+10.8%** |

nDCG rewards surfacing the most relevant papers at the top of the ranked list, not just anywhere in the top k. Full per-query breakdown and methodology in [`eval/results.md`](eval/results.md).

---

## Installation

Requires Python 3.12+ and an OpenAI API key.

```bash
git clone https://github.com/joeyb007/Scholr
cd Scholr
pip install -e .
export OPENAI_API_KEY=sk-...
```

**Optional:** add your email to join OpenAlex's polite pool for higher retrieval rate limits:

```bash
export SCHOLR_MAILTO=you@example.com
```

---

## Usage

### Web app

Live at [tryscholr.com](https://tryscholr.com). Sign in with Google or email/password. All conversation history persists across sessions.

### CLI

```bash
scholr
```

Starts an interactive REPL. Follow-up questions in the same session build on prior context — the planner sees what concepts were already explored and steers toward gaps.

```
  > explain transformer architecture
  > contrast CNNs and RNNs
  > what are the limitations of attention mechanisms
```

### MCP (Claude Desktop / Cursor)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scholr": {
      "command": "python3",
      "args": ["/absolute/path/to/Scholr/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

Restart Claude Desktop. The `scholr` tool will appear automatically.

---

## Running tests

Unit tests run fully offline — all LLM and retrieval calls are mocked:

```bash
pip install -e ".[dev]"
pytest -v -m "not e2e"
```

End-to-end tests hit real APIs (~2–5 min, requires API key):

```bash
pytest tests/test_e2e.py -v -m e2e
```

---

## Stack

| | |
|---|---|
| Language | Python 3.12+ |
| LLM | OpenAI GPT-4o via structured outputs |
| Retrieval | OpenAlex API — 200M+ papers, no key required |
| Reranking | sentence-transformers — BAAI/bge-small-en-v1.5 (bi-encoder) + ms-marco-MiniLM-L-6-v2 (cross-encoder) |
| Orchestration | Flat async pipeline, bounded recursion, multi-thread fan-out |
| Backend | FastAPI, deployed on Railway |
| Frontend | Next.js (App Router), deployed on Vercel |
| Auth | NextAuth.js — Google OAuth + email/password |
| Database | Neon Postgres (session persistence) |
| MCP | `mcp` Python SDK (FastMCP) |
| Tests | pytest + pytest-asyncio + pytest-mock |
