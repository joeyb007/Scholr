"use client";

import { useState } from "react";
import type { ConversationMessage, ResearchResult } from "@/types/scholr";
import { ParsedText } from "./CitePill";

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
}

function PriorPill({ query }: PriorPillProps) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="prior" onClick={() => setExpanded(e => !e)} style={{ cursor: "pointer" }}>
      <span className="prior__label">PRIOR ↑</span>
      <span className="prior__preview">{query}</span>
      <span className="prior__expand">{expanded ? "collapse" : "expand"}</span>
    </div>
  );
}

interface AssistantMessageProps {
  result: ResearchResult | null;
  streamingAnswer: string;
  isStreaming: boolean;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  onCiteClick: (n: number) => void;
  onFollowUp: (q: string) => void;
}

function AssistantMessage({ result, hoveredCite, onHover, onCiteClick, onFollowUp }: AssistantMessageProps) {
  if (!result) return null;

  return (
    <div className="answer">
      <div className="answer__label">Answer</div>
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
  const idx = ORDERED_STAGES.indexOf(stage);
  if (idx === -1) return stage === "Drafting answer" ? 90 : 8;
  return Math.round(((idx + 1) / ORDERED_STAGES.length) * 85);
}

interface ThreadProps {
  messages: ConversationMessage[];
  fakeStreamText: string;
  isFakeStreaming: boolean;
  isStreaming: boolean;
  progressStage: string;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  onCiteClick: (n: number) => void;
  onFollowUp: (q: string) => void;
  onExportBibtex: () => void;
  onShare: () => void;
  title: string;
  sessionId?: string;
}

export function Thread({ messages, fakeStreamText, isFakeStreaming, isStreaming, progressStage, hoveredCite, onHover, onCiteClick, onFollowUp, onExportBibtex, onShare, title, sessionId }: ThreadProps) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div className="topbar">
        <div className="topbar__left">
          <span className="topbar__title">{title || "New inquiry"}</span>
          {sessionId && (
            <span className="topbar__session">SESSION · {sessionId.slice(0, 8)}</span>
          )}
        </div>
        <div className="topbar__actions">
          <button className="topbar__action" onClick={onExportBibtex}>↗ EXPORT BIBTEX</button>
          <button className="topbar__action" onClick={onShare}>⤴ SHARE</button>
          <span className="topbar__grounded">● GROUNDED</span>
        </div>
      </div>

      <div className="thread">
        {messages.map((msg, i) => {
          const isPrior = msg.role === "user" && i < messages.length - 2;

          if (isPrior) {
            return <PriorPill key={i} query={msg.query ?? ""} />;
          }

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
          const showProgress = isLast && isStreaming && progressStage;
          const showFake = isLast && isFakeStreaming;
          return (
            <div key={i}>
              {showProgress && (
                <div className="progress">
                  <div className="progress__bar-track">
                    <div className="progress__bar-fill" style={{ width: `${stageProgress(progressStage)}%` }} />
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
                  <div className="answer__body">
                    {fakeStreamText.split("\n\n").map((para, pi) => (
                      <p key={pi}>
                        <ParsedText text={para} hoveredCite={hoveredCite} onHover={onHover} onCiteClick={onCiteClick} />
                        {pi === fakeStreamText.split("\n\n").length - 1 && <span className="answer__cursor">▌</span>}
                      </p>
                    ))}
                  </div>
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
                </div>
              )}
              {!isStreaming && !showFake && msg.result && (
                <AssistantMessage
                  result={msg.result ?? null}
                  streamingAnswer=""
                  isStreaming={false}
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
