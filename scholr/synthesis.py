from collections.abc import Callable
from openai import LengthFinishReasonError
from scholr.llm import get_client, llm_parse
from scholr.state import EvidenceClaim, ResearchState, SynthesisResult

# A real synthesis is ~1–2k tokens. Capping well below gpt-4o-mini's 16k ceiling means a
# degenerate generation loop fails in tens of seconds instead of running to the ceiling for
# minutes. 3500 keeps headroom over a legitimately rich synthesis while failing runaways fast.
_SYNTH_MAX_TOKENS = 3500
# On a length failure, retry over fewer papers — the runaway is driven by too many facts
# feeding a combinatorial evidence_map, so a smaller pool completes reliably.
_SYNTH_RETRY_PAPERS = 8

_SYSTEM = """You are a scientific synthesis engine. Produce a structured explanation grounded \
entirely in the provided paper facts. Rules:
- Be concise and non-repetitive — never restate a claim, sentence, or paragraph you have \
already written, and keep each evidence_map entry a distinct claim
- Every claim in evidence_map MUST cite at least one paper_id from the provided list
- Do NOT make any claim that is not supported by a paper_id in the list
- papers_used must equal the number of distinct paper_ids cited across all evidence_map entries
- depth_reached must be set to the value provided in the context
- answer_paragraphs: write the answer as a list of 2-4 paragraph strings. Embed [n] citation \
tokens inline at the point of reference, where n is the 1-based position of the paper in the \
valid_ids list (valid_ids[0] → [1], valid_ids[1] → [2], etc.). Bold 2-3 key technical terms \
per paragraph using **term** markdown — choose the most important concepts, mechanisms, or \
named entities that a reader should notice
- follow_up_questions: generate exactly 3 short, specific research questions not covered by \
this answer that would deepen understanding of the topic"""

_STREAM_SYSTEM = """You are a scientific writer. Answer the research question in clear, \
flowing prose based only on the provided paper facts. Write 2-4 paragraphs. \
No bullet points, no section headers, no citations — just the answer."""


def _build_user_prompt(state: ResearchState, max_papers: int | None = None) -> str:
    # Trim papers and their facts together so valid_ids and paper_facts stay consistent —
    # citation [n] tokens index into valid_ids, so both must reference the same paper set.
    papers = state.papers if max_papers is None else state.papers[:max_papers]
    valid_ids = [p.paper_id for p in papers]
    id_set = set(valid_ids)
    facts_text = "\n\n".join(
        f"paper_id: {pid}\nfacts:\n" + "\n".join(f"  - {f}" for f in facts)
        for pid, facts in state.paper_facts.items()
        if pid in id_set
    )
    concept_text = "\n".join(
        f"  {concept}: {', '.join(pids)}"
        for concept, pids in state.concept_to_papers.items()
    )
    return (
        f"Question: {state.query}\n\n"
        f"Paper facts:\n{facts_text}\n\n"
        f"Concept map:\n{concept_text}\n\n"
        f"Valid paper IDs (only cite these): {valid_ids}\n"
        f"depth_reached: {state.depth_reached}"
    )


async def stream_answer(
    state: ResearchState,
    on_token: Callable[[str], None],
) -> str:
    response = await get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _STREAM_SYSTEM},
            {"role": "user", "content": _build_user_prompt(state)},
        ],
        stream=True,
    )
    full_text = ""
    async for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            on_token(delta)
            full_text += delta
    return full_text


def _fallback_synthesis(state: ResearchState) -> SynthesisResult:
    """Build a minimal grounded result from the compressed facts so a query degrades to a
    real cited answer instead of erroring when the model won't emit valid structured output."""
    papers = state.papers
    id_to_n = {p.paper_id: i + 1 for i, p in enumerate(papers)}
    claims: list[EvidenceClaim] = []
    para_bits: list[str] = []
    for p in papers[:8]:
        facts = state.paper_facts.get(p.paper_id) or []
        if not facts:
            continue
        claims.append(EvidenceClaim(claim=facts[0], paper_ids=[p.paper_id]))
        para_bits.append(f"{facts[0]} [{id_to_n[p.paper_id]}]")
    if not claims and papers:
        claims = [EvidenceClaim(claim=papers[0].title or "See sources.", paper_ids=[papers[0].paper_id])]
    answer = " ".join(para_bits) or "The most relevant papers on this topic are listed in the sources."
    return SynthesisResult(
        final_answer=answer,
        answer_paragraphs=[answer] if answer else [],
        key_concepts=[],
        intuition="", mechanism="", limitations="", open_questions="",
        evidence_map=claims,
        follow_up_questions=[],
        papers_used=len({pid for c in claims for pid in c.paper_ids}),
        depth_reached=state.depth_reached,
    )


async def synthesize_structured(
    system: str,
    user: str,
    state: ResearchState,
    on_event: Callable[[str], None],
    retry_user: str | None = None,
) -> SynthesisResult:
    """Structured synthesis that never raises on a runaway. gpt-4o-mini occasionally falls into
    a repetition loop and blows the token cap; on that failure we escalate to gpt-4o (far less
    loop-prone), and if even that fails we return a grounded fallback rather than error out."""
    try:
        return await llm_parse(system, user, SynthesisResult, max_tokens=_SYNTH_MAX_TOKENS)
    except LengthFinishReasonError:
        on_event("[Synthesis] output truncated — retrying with gpt-4o")
        try:
            return await llm_parse(
                system, retry_user or user, SynthesisResult,
                max_tokens=_SYNTH_MAX_TOKENS, model="gpt-4o",
            )
        except Exception:
            on_event("[Synthesis] falling back to grounded summary")
            return _fallback_synthesis(state)


async def synthesize(
    state: ResearchState,
    on_event: Callable[[str], None],
) -> SynthesisResult:
    on_event("[Synthesis] building evidence map")
    result = await synthesize_structured(
        _SYSTEM, _build_user_prompt(state), state, on_event,
        retry_user=_build_user_prompt(state, max_papers=_SYNTH_RETRY_PAPERS),
    )
    on_event(f"[Synthesis] {len(result.evidence_map)} evidence claims")
    return result
