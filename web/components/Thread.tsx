"use client";

import { useState } from "react";
import type { ConversationMessage, ResearchResult } from "@/types/scholr";
import type { TrailState } from "@/lib/trail";
import { ParsedText, CitePill } from "./CitePill";
import { ResearchTrail } from "./ResearchTrail";

// Reveals the answer token-by-token, each token fading in with a stable key so only
// newly-revealed tokens animate (no re-parsing the whole string each tick → no pop).
function StreamingAnswer({ tokens, count, hoveredCite, onHover, onCiteClick }: {
  tokens: string[];
  count: number;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  onCiteClick: (n: number) => void;
}) {
  const paras: { tok: string; idx: number }[][] = [[]];
  tokens.slice(0, count).forEach((tok, idx) => {
    if (tok === "\n\n") paras.push([]);
    else paras[paras.length - 1].push({ tok, idx });
  });
  return (
    <div className="answer__body">
      {paras.map((para, pi) => (
        <p key={pi}>
          {para.map(({ tok, idx }) => {
            const cite = tok.match(/^\[(\d+)\]$/);
            if (cite) {
              return (
                <span key={idx} className="tok">
                  <CitePill n={parseInt(cite[1])} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />
                </span>
              );
            }
            const bold = tok.match(/^\*\*([^*]+)\*\*$/);
            if (bold) return <strong key={idx} className="tok answer__bold">{bold[1]}</strong>;
            return <span key={idx} className="tok">{tok}</span>;
          })}
        </p>
      ))}
    </div>
  );
}

interface SectionRowProps {
  label: string;
  text: string;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  onCiteClick: (n: number) => void;
}

function SectionRow({ label, text, hoveredCite, onHover, onCiteClick }: SectionRowProps) {
  return (
    <div className="section">
      <div className="section__label">{label}</div>
      <div className="section__body">
        <ParsedText text={text} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />
      </div>
    </div>
  );
}

interface PriorPillProps {
  query: string;
  expanded: boolean;
  onToggle: () => void;
}

function PriorPill({ query, expanded, onToggle }: PriorPillProps) {
  return (
    <div className="prior" onClick={onToggle} style={{ cursor: "pointer" }}>
      <span className="prior__label">PRIOR ↑</span>
      <span className="prior__preview">{query}</span>
      <span className="prior__expand">{expanded ? "collapse" : "expand"}</span>
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="answer__copy"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch { /* clipboard unavailable */ }
      }}
    >
      {copied ? "✓ copied" : "⧉ copy"}
    </button>
  );
}

interface AssistantMessageProps {
  result: ResearchResult | null;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  onCiteClick: (n: number) => void;
  onFollowUp: (q: string) => void;
}

function AssistantMessage({ result, hoveredCite, onHover, onCiteClick, onFollowUp }: AssistantMessageProps) {
  if (!result) return null;

  return (
    <div className="answer">
      <div className="answer__label-row">
        <div className="answer__label">Answer</div>
        <CopyButton text={result.answer_paragraphs.map(p => p.replace(/\*\*/g, "")).join("\n\n")} />
      </div>
      <div className="answer__body">
        {result.answer_paragraphs.map((p, i) => (
          <p key={i}>
            <ParsedText text={p} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />
          </p>
        ))}
      </div>

      {result && (
        <>
          <SectionRow label="Mechanism" text={result.mechanism} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />
          <SectionRow label="Intuition" text={result.intuition} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />
          <SectionRow label="Limitations" text={result.limitations} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />
          <SectionRow label="Open questions" text={result.open_questions} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />

          {result.follow_up_questions.length > 0 && (
            <div className="followups">
              <div className="followups__label">Suggested follow-ups</div>
              <div className="followups__pills">
                {result.follow_up_questions.map((q, i) => (
                  <button key={i} className="followup-pill" onClick={() => onFollowUp(q)}>{q}</button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const ORDERED_STAGES = [
  "Analyzing your question",
  "Planning search strategy",
  "Searching 200M+ papers",
  "Expanding into related concepts",
  "Checking coverage",
  "Extracting key findings",
  "Building evidence map",
];

function stageProgress(stage: string): number {
  // Parallel fan-out: "Researching CNNs · RNNs"
  if (stage.includes(" · ")) return 30;
  // Sequential thread: "Researching X (N/M)"
  const threadMatch = stage.match(/Researching .+ \((\d+)\/(\d+)\)/);
  if (threadMatch) {
    const n = parseInt(threadMatch[1]), total = parseInt(threadMatch[2]);
    return Math.round(10 + ((n - 0.5) / total) * 70);
  }
  const idx = ORDERED_STAGES.indexOf(stage);
  if (idx === -1) return stage === "Drafting answer" ? 90 : 8;
  return Math.round(((idx + 1) / ORDERED_STAGES.length) * 85);
}

interface ThreadProps {
  messages: ConversationMessage[];
  fakeTokens: string[];
  fakeCount: number;
  isFakeStreaming: boolean;
  isStreaming: boolean;
  progressStage: string;
  trail: TrailState | null;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  onCiteClick: (n: number) => void;
  onFollowUp: (q: string) => void;
  onExportBibtex: () => void;
  onShare: () => void;
  title: string;
  sessionId?: string;
  onMobileMenu?: () => void;
  onMobileSources?: () => void;
  sourcesCount?: number;
}

export function Thread({ messages, fakeTokens, fakeCount, isFakeStreaming, isStreaming, progressStage, trail, hoveredCite, onHover, onCiteClick, onFollowUp, onExportBibtex, onShare, title, sessionId, onMobileMenu, onMobileSources, sourcesCount }: ThreadProps) {
  const [expandedPriors, setExpandedPriors] = useState<Set<number>>(new Set());

  function togglePrior(i: number) {
    setExpandedPriors(prev => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i); else next.add(i);
      return next;
    });
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div className="topbar">
        <div className="topbar__left">
          {onMobileMenu && (
            <button className="topbar__hamburger" onClick={onMobileMenu}>≡</button>
          )}
          <span className="topbar__title">{title || "New inquiry"}</span>
          {sessionId && (
            <span className="topbar__session">SESSION · {sessionId.slice(0, 8)}</span>
          )}
        </div>
        <div className="topbar__actions">
          <button className="topbar__action topbar__action--desktop" onClick={onExportBibtex}>↗<span className="topbar__action-text"> EXPORT BIBTEX</span></button>
          <button className="topbar__action topbar__action--desktop" onClick={onShare}>⤴<span className="topbar__action-text"> SHARE</span></button>
          <span className="topbar__grounded">● GROUNDED</span>
          {onMobileSources && (
            <button className="topbar__sources" onClick={onMobileSources}>
              sources{sourcesCount ? ` (${sourcesCount})` : ""}
            </button>
          )}
        </div>
      </div>

      <div className="thread">
        {messages.map((msg, i) => {
          const isPrior = msg.role === "user" && i < messages.length - 2;
          const isPriorAssistant = msg.role === "assistant" && i > 0 &&
            messages[i - 1]?.role === "user" && (i - 1) < messages.length - 2;

          if (isPrior) {
            const expanded = expandedPriors.has(i);
            return (
              <div key={i}>
                <PriorPill query={msg.query ?? ""} expanded={expanded} onToggle={() => togglePrior(i)} />
                {expanded && (
                  <>
                    <div className="question">
                      <div className="question__label">You asked</div>
                      <div className="question__text">{msg.query}</div>
                    </div>
                    {messages[i + 1]?.result && (
                      <AssistantMessage
                        result={messages[i + 1].result ?? null}
                        hoveredCite={hoveredCite}
                        onHover={onHover}
                        onCiteClick={onCiteClick}
                        onFollowUp={onFollowUp}
                      />
                    )}
                  </>
                )}
              </div>
            );
          }

          if (isPriorAssistant) return null;

          if (msg.role === "user") {
            const result = messages[i + 1]?.result;
            return (
              <div key={i} className="question">
                <div className="question__label">You asked</div>
                <div className="question__text">{msg.query}</div>
                {result && (
                  <div className="question__meta">
                    ↳ {result.papers_used} papers · depth {result.depth_reached}
                  </div>
                )}
              </div>
            );
          }

          const isLast = i === messages.length - 1;
          const showFake = isLast && isFakeStreaming;
          // Trail: live (page-level) during research, then the collapsed summary from the message.
          const activeTrail = msg.trail ?? (isLast && isStreaming ? trail : null);
          return (
            <div key={i}>
              {activeTrail && <ResearchTrail trail={activeTrail} />}
              {isLast && isStreaming && !activeTrail && progressStage && (
                <div className="progress">
                  <div className="progress__bar-track">
                    <div className={`progress__bar-fill${progressStage.includes(" · ") ? " progress__bar-fill--pulse" : ""}`} style={{ width: `${stageProgress(progressStage)}%` }} />
                  </div>
                  <div className="progress__stage">
                    <div className="progress__dot" />
                    {progressStage}…
                  </div>
                </div>
              )}
              {showFake && (
                <div className="answer">
                  <div className="answer__label">Answer</div>
                  <StreamingAnswer tokens={fakeTokens} count={fakeCount} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />
                </div>
              )}
              {!isStreaming && !showFake && msg.suggestion && (
                <div className="answer">
                  <div className="answer__label">Out of scope</div>
                  <div className="answer__suggestion">{msg.suggestion}</div>
                </div>
              )}
              {!isStreaming && !showFake && msg.error && (
                <div className="answer">
                  <div className="answer__label">Error</div>
                  <div className="answer__error">{msg.error}</div>
                  {messages[i - 1]?.query && (
                    <button className="answer__retry" onClick={() => onFollowUp(messages[i - 1].query!)}>↻ try again</button>
                  )}
                </div>
              )}
              {!isStreaming && !showFake && msg.result && (
                <AssistantMessage
                  result={msg.result ?? null}
                  hoveredCite={hoveredCite}
                  onHover={onHover}
                  onCiteClick={onCiteClick}
                  onFollowUp={onFollowUp}
                />
              )}
            </div>
          );
        })}
        <div className="thread__spacer" />
      </div>
    </div>
  );
}
