from collections.abc import Callable
from scholr.llm import llm_parse
from scholr.state import PlannerOutput, ResearchState

_SYSTEM = """You are a research query planner. Convert a natural language question into \
3-5 arXiv-style keyword search strings that cover different dimensions of the topic \
(mechanism, limitations, theory, alternatives, applications). Rules:
- Each query must target a DIFFERENT dimension — no overlapping concepts
- Queries must be keyword-based, not conversational sentences
- Avoid concepts that are already in the concept map (already explored)
- Prefer specific technical terms over general phrases"""


async def plan_queries(
    state: ResearchState,
    on_event: Callable[[str], None],
) -> list[str]:
    on_event("[Planner] generating queries")
    explored = list(state.concept_to_papers.keys())
    user = (
        f"Question: {state.query}\n\n"
        f"Already explored concepts (avoid repeating): {explored or 'none'}"
    )
    output = await llm_parse(_SYSTEM, user, PlannerOutput)
    on_event(f"[Planner] intent={output.intent} scope={output.scope}")
    return output.queries
