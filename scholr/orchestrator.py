import asyncio
from collections.abc import Callable
from uuid import uuid4

from scholr.decomposer import decompose_query
from scholr.llm import get_client, llm_parse
from scholr.pipeline import _validate_evidence, run_pipeline
from scholr.session import fresh_state, save_session
from scholr.state import (
    EvidenceClaim, ResearchState, SynthesisResult, existing_ids
)
from scholr.synthesis import _SYSTEM as _SYNTH_SYSTEM, _build_user_prompt, stream_answer

MAX_ORCHESTRATORS = 5

_COMPARE_SYSTEM = """You are a scientific synthesis engine specialising in comparative analysis. \
Produce a structured explanation that directly compares and contrasts the provided topics. \
Rules:
- Every claim in evidence_map MUST cite at least one paper_id from the provided list
- Do NOT make any claim unsupported by a provided paper_id
- final_answer must explicitly compare and contrast — do not describe topics in isolation
- papers_used must equal the number of distinct paper_ids cited across all evidence_map entries
- depth_reached must be set to the value provided in the context"""

_COMPARE_STREAM_SYSTEM = """You are a scientific writer specialising in comparative analysis. \
Write a clear, flowing comparison of the provided topics based only on the paper facts given. \
Directly contrast mechanisms, strengths, and limitations. Write 3–5 paragraphs. \
No bullet points, no headers, no citations — just the comparison."""


async def run_research(
    query: str,
    session_id: str,
    on_event: Callable[[str], None] = lambda _: None,
    on_token: Callable[[str], None] | None = None,
) -> ResearchState | str:
    """Returns ResearchState on success, or a str suggestion if query is too complex."""
    decomp = await decompose_query(query, on_event)

    if decomp.too_complex:
        return decomp.suggestion

    subtopics = decomp.subtopics[:MAX_ORCHESTRATORS]

    if len(subtopics) == 1:
        return await run_pipeline(subtopics[0].focus, session_id, on_event, on_token)

    # Fan out — sub-pipelines run without streaming (on_token fires only in meta-synthesis)
    async def run_subtopic(i: int, focus: str, label: str) -> ResearchState | None:
        def prefixed(e: str) -> None:
            on_event(f"[{label}] {e}")
        try:
            return await run_pipeline(focus, f"{session_id}-{i}", prefixed, on_token=None)
        except Exception as e:
            on_event(f"[{label}] failed: {e}")
            return None

    on_event(f"[Orchestrator] running {len(subtopics)} research threads sequentially")
    states: list[ResearchState] = []
    for i, st in enumerate(subtopics):
        on_event(f"[Orchestrator] thread {i + 1}/{len(subtopics)}: {st.subtopic}")
        result = await run_subtopic(i, st.focus, st.subtopic)
        if result is not None:
            states.append(result)

    if not states:
        raise ValueError(f"All research threads failed for: {query!r}. Try rephrasing.")

    if len(states) == 1:
        return states[0]

    merged = _merge_states(query, session_id, states)
    return await _compare_synthesize(merged, on_event, on_token)


def _merge_states(
    query: str,
    session_id: str,
    states: list[ResearchState],
) -> ResearchState:
    merged = fresh_state(query, session_id)
    seen_ids: set[str] = set()

    for state in states:
        for paper in state.papers:
            if paper.paper_id not in seen_ids:
                seen_ids.add(paper.paper_id)
                merged.papers.append(paper)
        merged.paper_facts.update(state.paper_facts)
        for concept, pids in state.concept_to_papers.items():
            if concept not in merged.concept_to_papers:
                merged.concept_to_papers[concept] = []
            for pid in pids:
                if pid not in merged.concept_to_papers[concept]:
                    merged.concept_to_papers[concept].append(pid)
        merged.depth_reached = max(merged.depth_reached, state.depth_reached)

    return merged


async def _compare_synthesize(
    state: ResearchState,
    on_event: Callable[[str], None],
    on_token: Callable[[str], None] | None,
) -> ResearchState:
    facts_text = "\n\n".join(
        f"paper_id: {pid}\nfacts:\n" + "\n".join(f"  - {f}" for f in facts)
        for pid, facts in state.paper_facts.items()
    )
    concept_text = "\n".join(
        f"  {concept}: {', '.join(pids)}"
        for concept, pids in state.concept_to_papers.items()
    )
    valid_ids = [p.paper_id for p in state.papers]
    user = (
        f"Comparison question: {state.query}\n\n"
        f"Paper facts:\n{facts_text}\n\n"
        f"Concept map:\n{concept_text}\n\n"
        f"Valid paper IDs (only cite these): {valid_ids}\n"
        f"depth_reached: {state.depth_reached}"
    )

    streamed_answer: str | None = None
    if on_token is not None:
        on_event("[Synthesis] streaming comparison")
        response = await get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _COMPARE_STREAM_SYSTEM},
                {"role": "user", "content": user},
            ],
            stream=True,
        )
        streamed_answer = ""
        async for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                on_token(delta)
                streamed_answer += delta

    on_event("[Synthesis] building evidence map")
    result = await llm_parse(_COMPARE_SYSTEM, user, SynthesisResult)
    on_event(f"[Synthesis] {len(result.evidence_map)} evidence claims")

    if streamed_answer is not None:
        result = result.model_copy(update={"final_answer": streamed_answer})

    state.final_output = result
    _validate_evidence(state)
    save_session(state)
    on_event("[Done]")
    return state
