"use client";

import type { Paper } from "@/types/scholr";
import { SourceCard } from "./SourceCard";

interface EvidencePanelProps {
  papers: Paper[];
  depth: number;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function EvidencePanel({ papers, depth, hoveredCite, onHover, mobileOpen, onMobileClose }: EvidencePanelProps) {
  return (
    <div className={`evidence${mobileOpen ? " evidence--mobile-open" : ""}`}>
      {onMobileClose && (
        <button className="evidence__mobile-close" onClick={onMobileClose}>✕ close</button>
      )}
      <div className="evidence__header">
        <div className="evidence__title-row">
          <span className="evidence__title">Evidence</span>
          <span className="evidence__count">{papers.length} sources · depth {depth}</span>
        </div>
        <div className="evidence__hint">
          Hover a citation in the answer to highlight its source.
        </div>
      </div>
      <div className="evidence__list">
        {papers.length === 0
          ? <div className="evidence__empty">Sources will appear here.</div>
          : papers.map(p => (
              <SourceCard key={p.id} paper={p} hoveredCite={hoveredCite} onHover={onHover} />
            ))
        }
      </div>
    </div>
  );
}
