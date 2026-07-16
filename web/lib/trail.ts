// Derives the "research trail" UI state from the backend's SSE event stream.
// Kept as pure reducers so the (fiddly) event parsing is isolated and testable.
import type { Paper } from "@/types/scholr";

export type StepKind = "decompose" | "branch" | "converge" | "compose";
export type StepState = "pending" | "active" | "done";

export interface TrailStep {
  id: string;
  kind: StepKind;
  label: string;
  detail?: string;
  state: StepState;
}

export type SourceState = "found" | "cited" | "dropped";

export interface TrailSource {
  id: string;
  tag: string;      // short angle marker, e.g. "C"
  title: string;
  meta: string;     // authors · year
  abstract?: string;
  state: SourceState;
}

export interface TrailState {
  title: string;
  steps: TrailStep[];
  sources: TrailSource[];
  done: boolean;
}

export interface PaperEvent {
  id: string;
  angle: string;
  title: string;
  authors: string;
  year: string;
  abstract?: string;
}

export function emptyTrail(): TrailState {
  return { title: "Starting research…", steps: [], sources: [], done: false };
}

function tagFor(angle: string): string {
  const a = angle.trim();
  if (!a) return "◦";
  return a[0].toUpperCase();
}

function upsertStep(steps: TrailStep[], step: TrailStep): TrailStep[] {
  const i = steps.findIndex((s) => s.id === step.id);
  if (i === -1) return [...steps, step];
  const next = steps.slice();
  next[i] = { ...next[i], ...step };
  return next;
}

// Which branch a (possibly unprefixed) event belongs to. Single-topic runs emit no
// subtopic prefix, so an unprefixed branch event maps to the lone branch if there is one.
function branchIdFor(angle: string, steps: TrailStep[]): string {
  if (angle) return "branch:" + angle;
  const branches = steps.filter((s) => s.kind === "branch");
  if (branches.length === 1) return branches[0].id;
  return "branch:main";
}

export function applyProgress(trail: TrailState, raw: string): TrailState {
  // Peel off a leading subtopic prefix ("[CNNs] [Retrieval] …") when a second
  // bracketed tag follows — that first bracket names the angle, not the stage.
  let angle = "";
  let event = raw;
  const pm = raw.match(/^\[([^\]]+)\]\s+(\[.*)$/);
  if (pm) {
    angle = pm[1];
    event = pm[2];
  }

  let { title, steps } = trail;
  const { sources, done } = trail;

  if (/\[Orchestrator\]\s+decomposing/i.test(event)) {
    steps = upsertStep(steps, {
      id: "decompose", kind: "decompose",
      label: "Reading your question", detail: "finding the angles to research", state: "active",
    });
    return { title: "Reading your question", steps, sources, done };
  }

  const subs = event.match(/\[Orchestrator\]\s+\d+\s+subtopic\(s\):\s+(.+)/i);
  if (subs) {
    const angles = subs[1].split(",").map((s) => s.trim()).filter(Boolean);
    steps = upsertStep(steps, {
      id: "decompose", kind: "decompose",
      label: angles.length > 1 ? `${angles.length} angles to research` : "Focused research",
      detail: angles.join("  ·  "), state: "done",
    });
    for (const a of angles) {
      steps = upsertStep(steps, {
        id: "branch:" + a, kind: "branch",
        label: `${a} — queued`, detail: "", state: "pending",
      });
    }
    title = angles.length > 1 ? `Researching ${angles.length} angles` : `Researching ${angles[0]}`;
    return { title, steps, sources, done };
  }

  // Reranking → the converge beat (paper counts already live in the string)
  const rerank = event.match(/\[Rerank\]\s+narrowing\s+(\d+)\s+.*?(\d+)/i);
  if (/\[Rerank\]/i.test(event)) {
    // mark all branches done once we start converging
    steps = steps.map((s) => (s.kind === "branch" ? { ...s, state: "done" as StepState } : s));
    const detail = rerank ? `weighing ${rerank[1]} candidates → ${rerank[2]}` : "weighing candidates";
    steps = upsertStep(steps, {
      id: "converge", kind: "converge",
      label: "Weighing which papers matter most", detail, state: "active",
    });
    return { title: "Converging on the strongest papers", steps, sources, done };
  }

  if (/\[Compression\]/i.test(event)) {
    steps = steps.map((s) => (s.kind === "converge" ? { ...s, state: "done" as StepState } : s));
    steps = upsertStep(steps, {
      id: "converge", kind: "converge",
      label: "Kept the strongest papers", state: "done",
    });
    return { title, steps, sources, done };
  }

  if (/\[Synthesis\]/i.test(event)) {
    steps = steps.map((s) => (s.kind === "converge" ? { ...s, state: "done" as StepState } : s));
    steps = upsertStep(steps, {
      id: "compose", kind: "compose",
      label: "Writing your answer", detail: "grounding every claim in a source", state: "active",
    });
    return { title: "Composing your answer", steps, sources, done };
  }

  // Per-branch activity
  const found = event.match(/\[Retrieval\]\s+(\d+)\s+papers?\s+found/i);
  if (found) {
    const id = branchIdFor(angle, steps);
    steps = upsertStep(steps, {
      id, kind: "branch",
      label: angle ? `${angle} — sources gathered` : "Sources gathered",
      detail: `found ${found[1]} papers`, state: "done",
    });
    return { title, steps, sources, done };
  }
  if (/\[Retrieval\]/i.test(event) || /\[Planner\]/i.test(event)) {
    const id = branchIdFor(angle, steps);
    steps = upsertStep(steps, {
      id, kind: "branch",
      label: angle ? `${angle} — scanning 200M+ papers…` : "Scanning 200M+ papers…",
      detail: "", state: "active",
    });
    return { title, steps, sources, done };
  }

  return trail;
}

export function applyPaper(trail: TrailState, p: PaperEvent): TrailState {
  if (trail.sources.some((s) => s.id === p.id)) return trail;
  const meta = [p.authors, p.year].filter(Boolean).join(" · ");
  const source: TrailSource = {
    id: p.id, tag: tagFor(p.angle), title: p.title, meta, abstract: p.abstract, state: "found",
  };
  return { ...trail, sources: [...trail.sources, source] };
}

// On the final result: cite the papers that made the cut, dim the rest, close the trail.
export function finalizeTrail(trail: TrailState, papers: Paper[], elapsedMs?: number): TrailState {
  const citedIds = new Set(papers.map((p) => p.id));
  const sources = trail.sources.map((s) => ({
    ...s, state: (citedIds.has(s.id) ? "cited" : "dropped") as SourceState,
  }));
  const steps = trail.steps.map((s) => ({ ...s, state: "done" as StepState }));
  const secs = elapsedMs ? ` · ${(elapsedMs / 1000).toFixed(1)}s` : "";
  const total = trail.sources.length || papers.length;
  return {
    title: `Researched ${total} sources → ${papers.length} cited${secs}`,
    steps, sources, done: true,
  };
}
