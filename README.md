<p align="center">
  <img alt="Scholr" src="web/public/scholr.png" width="100">
</p>

<p align="center">
  A bounded recursive AI research assistant that retrieves and synthesizes academic papers into structured, evidence-grounded explanations.
</p>

<br>

---

## How it works

Ask a research question. Scholr automatically decomposes it into subtopics, runs a bounded recursive retrieval pipeline per subtopic, and synthesizes a final explanation where every claim is traced back to a real paper.

```
Query
  → Decomposer        detect subtopics (e.g. "contrast CNNs and RNNs" → 2 threads)
  → Per subtopic:
      Planner         GPT-4o generates targeted search queries (retries up to 3× if no results)
      Retrieval       OpenAlex API, 200M+ papers
      Expansion       extract concepts, generate follow-up queries
      Compression     abstracts → atomic factual statements
      Synthesis       structured explanation per subtopic
  → Compare           meta-synthesis combining all subtopics with evidence map
```

- Hallucinated citations are stripped automatically
- Recursion is hard-capped at depth 2 and 12 papers per subtopic
- Session state persists across follow-up questions so the planner avoids already-explored concepts
- Exposed as both an interactive CLI and an MCP tool for Claude Desktop / Cursor

---

## Installation

Requires Python 3.12+ and an OpenAI API key.

```bash
git clone https://github.com/joeyb007/Scholr
cd scholr
pip install -e .
export OPENAI_API_KEY=sk-...
```

This registers `scholr` as a command — run it from anywhere:

```bash
scholr
```

To install in an isolated environment (recommended):

```bash
pipx install .
```

**Optional:** add your email to join OpenAlex's polite pool for higher retrieval rate limits:

```bash
export SCHOLR_MAILTO=you@example.com
```

---

## Usage

### CLI

```bash
scholr
```

Scholr starts an interactive REPL. Type any research question and hit enter:

```
  > explain transformer architecture
  > contrast CNNs and RNNs
  > what are the limitations of attention mechanisms
```

Follow-up questions in the same session build on prior context — the planner sees what concepts were already explored and steers toward gaps.

---

### MCP (Claude Desktop / Cursor)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "scholr": {
      "command": "python3",
      "args": ["/absolute/path/to/scholr/mcp_server.py"],
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
| Orchestration | Flat async pipeline, bounded recursion, multi-thread fan-out |
| MCP | `mcp` Python SDK (FastMCP) |
| Sessions | JSON files on disk |
| Tests | pytest + pytest-asyncio + pytest-mock |
