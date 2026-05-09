"use client";

import { useState } from "react";
import type { Paper } from "@/types/scholr";
import { CitationModal } from "./CitationModal";

interface SourceCardProps {
  paper: Paper;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
}

export function SourceCard({ paper, hoveredCite, onHover }: SourceCardProps) {
  const [showCitation, setShowCitation] = useState(false);
  const url = paper.id.startsWith("arXiv:")
    ? `https://arxiv.org/abs/${paper.id.slice(6)}`
    : `https://openalex.org/works/${paper.id}`;

  const shortId = paper.id.startsWith("arXiv:")
    ? paper.id.slice(6)
    : paper.id.replace("W", "W").slice(0, 12);

  const meta = [paper.authors, paper.year, paper.venue].filter(Boolean).join(" · ");

  return (
    <>
      <div
        id={`source-${paper.n}`}
        className={`card${hoveredCite === paper.n ? " card--active" : ""}`}
        onMouseEnter={() => onHover(paper.n)}
        onMouseLeave={() => onHover(null)}
      >
        <div className="card__badge">{paper.n}</div>
        <div className="card__body">
          <div className="card__title">{paper.title}</div>
          {meta && <div className="card__meta">{meta}</div>}
          {paper.claim && <div className="card__claim">&ldquo;{paper.claim}&rdquo;</div>}
          <div className="card__actions">
            <span className="card__id">{shortId}</span>
            <a href={url} target="_blank" rel="noopener noreferrer" className="card__link">↗ open</a>
            <button className="card__cite-btn" onClick={() => setShowCitation(true)}>get citation</button>
          </div>
        </div>
      </div>
      {showCitation && <CitationModal paper={paper} onClose={() => setShowCitation(false)} />}
    </>
  );
}
