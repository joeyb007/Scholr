# Scholr

A bounded recursive AI research assistant that retrieves and synthesizes arXiv papers into structured, evidence-grounded explanations.

Ask a research question. Scholr plans search queries, retrieves papers, recursively expands key concepts, and synthesizes a final explanation where every claim is traced back to a specific paper.

---

## How it works

```
User Query
  → Query Planner          (GPT-4o generates arXiv search strings)
  → Level 0 Retrieval      (arXiv API, up to 5 papers per query)
  → Concept Expansion      (extract concepts, generate follow-up queries)
  → Level 1 Retrieval      (follow research leads, bounded to depth=2)
  → Coverage Check         (one optional retry if gaps detected)
  → Paper Compression      (abstracts → atomic factual statements)
  → Synthesis              (structured explanation with evidence map)
```

Every claim in the output is mapped to at least one paper ID. Hallucinated citations are stripped automatically. Recursion is hard-capped at depth 2 and 12 total papers — no runaway agents.

Session state (concept map + visited papers) persists across follow-up questions so the planner knows what's already been explored.

---

## Installation

Requires Python 3.12+ and an OpenAI API key.

```bash
git clone https://github.com/yourusername/scholr
cd scholr
pip install -e .
export OPENAI_API_KEY=sk-...
```

---

## Usage

### CLI

```bash
python cli.py "explain transformer architecture"
```

```
Session: a3f2c1d4-...
Query: explain transformer architecture

[Session] loading context
[Planner] generating queries
[Planner] intent=explanation scope=architecture
[Retrieval] transformer self attention mechanism
[Retrieval] positional encoding transformers
[Retrieval] attention bottleneck scaling limitations
[Level 0] expanding concepts
[Expansion] processing 8 papers
[Coverage] evaluating 8 papers
[Coverage] sufficient=True
[Compression] extracting facts from 8 papers
[Synthesis] generating final explanation
[Synthesis] generated 6 evidence claims
[Done]

============================================================
ANSWER
The Transformer architecture replaces recurrence with self-attention,
enabling parallel computation over entire sequences...

MECHANISM
Each token attends to all other tokens via query-key-value dot products.
Multi-head attention runs this process in parallel across h subspaces...

LIMITATIONS
Attention scales quadratically with sequence length (O(n²) memory),
making long-context processing expensive...

EVIDENCE (6 claims)
  • Self-attention enables parallel computation across sequence positions.
    sources: http://arxiv.org/abs/1706.03762v7
  • Multi-head attention captures different representation subspaces.
    sources: http://arxiv.org/abs/1706.03762v7, http://arxiv.org/abs/1810.04805v2
  ...

Session ID: a3f2c1d4-...
```

**Continue a session** (planner avoids concepts already explored):

```bash
python cli.py "what are the alternatives to self-attention" --session a3f2c1d4-...
```

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

Restart Claude Desktop. The `research` tool will appear and can be called as:

```
research("explain how diffusion models work")
research("what are the limitations", session_id="...")
```

The response includes the full structured explanation, evidence map, execution trace, and session ID for follow-up queries.

---

## Running tests

Unit tests run fully offline — all LLM and arXiv calls are mocked:

```bash
pip install -e ".[dev]"
pytest -v -m "not e2e"
```

End-to-end tests hit real APIs (~30–90s, requires API key):

```bash
pytest tests/test_e2e.py -v -m e2e
```

---

## Stack

| | |
|---|---|
| Language | Python 3.12+ |
| LLM | OpenAI GPT-4o via structured outputs |
| Retrieval | arXiv API (`arxiv` package) |
| MCP | `mcp` Python SDK (FastMCP) |
| Sessions | JSON files on disk |
| Tests | pytest + pytest-asyncio + pytest-mock |
