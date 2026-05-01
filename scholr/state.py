from __future__ import annotations
from pydantic import BaseModel, Field


class Paper(BaseModel):
    paper_id: str
    title: str
    abstract: str
    source_query: str


class PlannerOutput(BaseModel):
    queries: list[str]
    intent: str
    scope: str


class PaperExpansion(BaseModel):
    paper_id: str
    concepts: list[str]
    follow_up_queries: list[str]


class ExpansionOutput(BaseModel):
    expansions: list[PaperExpansion]


class CoverageOutput(BaseModel):
    sufficient: bool
    missing_aspects: list[str]
    extra_queries: list[str]


class PaperCompression(BaseModel):
    paper_id: str
    key_points: list[str]


class CompressionOutput(BaseModel):
    compressions: list[PaperCompression]


class EvidenceClaim(BaseModel):
    claim: str
    paper_ids: list[str] = Field(min_length=1)


class SynthesisResult(BaseModel):
    final_answer: str
    key_concepts: list[str]
    intuition: str
    mechanism: str
    limitations: str
    open_questions: str
    evidence_map: list[EvidenceClaim]
    papers_used: int
    depth_reached: int


class SubtopicQuery(BaseModel):
    subtopic: str   # short label e.g. "CNNs"
    focus: str      # arXiv-style research question e.g. "convolutional neural networks image classification"


class DecomposerOutput(BaseModel):
    subtopics: list[SubtopicQuery]  # 1–5 items; empty if too_complex
    too_complex: bool
    suggestion: str                 # populated only when too_complex=True
    intent: str                     # "explanation", "comparison", "survey", "limitations", "applications"


class ResearchState(BaseModel):
    query: str
    session_id: str
    planned_queries: list[str] = []
    papers: list[Paper] = []
    concept_to_papers: dict[str, list[str]] = {}
    paper_facts: dict[str, list[str]] = {}
    final_output: SynthesisResult | None = None
    depth_reached: int = 0
    events: list[str] = []


def existing_ids(state: ResearchState) -> set[str]:
    return {p.paper_id for p in state.papers}
