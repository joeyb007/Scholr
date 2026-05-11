"use client";

import { useState } from "react";
import type { Conversation, ConversationMessage, ResearchResult } from "@/types/scholr";
import { ParsedText } from "./CitePill";
import { EvidencePanel } from "./EvidencePanel";

function remapCitations(result: ResearchResult): ResearchResult {
  const order: number[] = [];
  const seen = new Set<number>();
  for (const para of result.answer_paragraphs) {
    for (const m of para.matchAll(/\[(\d+)\]/g)) {
      const n = parseInt(m[1]);
      if (!seen.has(n)) { seen.add(n); order.push(n); }
    }
  }
  if (order.length === 0) return result;
  const remap = new Map(order.map((n, i) => [n, i + 1]));
  const answer_paragraphs = result.answer_paragraphs.map(p =>
    p.replace(/\[(\d+)\]/g, (_, n) => {
      const newN = remap.get(parseInt(n));
      return newN !== undefined ? `[${newN}]` : `[${n}]`;
    })
  );
  const papers = result.papers
    .filter(p => remap.has(p.n))
    .map(p => ({ ...p, n: remap.get(p.n)! }))
    .sort((a, b) => a.n - b.n);
  return { ...result, answer_paragraphs, papers };
}

interface ShareViewerProps {
  conv: Conversation;
}

export function ShareViewer({ conv }: ShareViewerProps) {
  const [hoveredCite, setHoveredCite] = useState<number | null>(null);

  function handleCiteClick(n: number) {
    document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  const lastResult = conv.messages
    .filter(m => m.role === "assistant" && m.result)
    .map(m => remapCitations(m.result!))
    .at(-1) ?? null;

  const papers = lastResult?.papers ?? [];

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ padding: "16px 28px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
          <span style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 17, color: "var(--fg)" }}>{conv.title}</span>
          <div style={{ display: "flex", gap: 16, fontFamily: "var(--mono)", fontSize: 10 }}>
            <span style={{ color: "var(--amber)" }}>● GROUNDED</span>
            <span style={{ color: "var(--faint)" }}>read-only</span>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "28px 28px 0" }}>
          {conv.messages.map((msg: ConversationMessage, i: number) => {
            if (msg.role === "user") {
              return (
                <div key={i} style={{ marginBottom: 20 }}>
                  <div className="question__label">You asked</div>
                  <div className="question__text">{msg.query}</div>
                </div>
              );
            }
            const result = msg.result ? remapCitations(msg.result) : null;
            if (!result) return null;
            return (
              <div key={i} style={{ marginBottom: 32 }}>
                <div className="answer__label">Answer</div>
                <div className="answer__body">
                  {result.answer_paragraphs.map((p, pi) => (
                    <p key={pi}>
                      <ParsedText text={p} hoveredCite={hoveredCite} onHover={setHoveredCite} onCiteClick={handleCiteClick} />
                    </p>
                  ))}
                </div>
              </div>
            );
          })}
          <div style={{ height: 40 }} />
        </div>
      </div>

      <EvidencePanel
        papers={papers}
        depth={lastResult?.depth_reached ?? 0}
        hoveredCite={hoveredCite}
        onHover={setHoveredCite}
      />
    </div>
  );
}
