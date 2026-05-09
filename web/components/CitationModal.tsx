"use client";

import { useState } from "react";
import type { Paper } from "@/types/scholr";

type Format = "APA" | "MLA" | "Chicago" | "BibTeX";
const FORMATS: Format[] = ["APA", "MLA", "Chicago", "BibTeX"];

function bibtexKey(paper: Paper): string {
  const lastPart = (paper.authors || "").split(",")[0].trim().split(/\s+/).slice(-1)[0] || "Unknown";
  const firstWord = paper.title.split(/\s+/).find(w => w.length > 3) ?? paper.title.split(/\s+/)[0] ?? "";
  return `${lastPart}${paper.year ?? ""}${firstWord}`.replace(/[^a-zA-Z0-9]/g, "").slice(0, 20);
}

function formatCitation(paper: Paper, fmt: Format): string {
  const authors = paper.authors || "Unknown";
  const year = paper.year ? String(paper.year) : "n.d.";
  const title = paper.title;
  const venue = paper.venue || "";

  switch (fmt) {
    case "APA":
      return `${authors} (${year}). ${title}.${venue ? ` ${venue}.` : ""}`;
    case "MLA":
      return `${authors}. "${title}."${venue ? ` ${venue},` : ""} ${year}.`;
    case "Chicago":
      return `${authors}. "${title}."${venue ? ` ${venue}` : ""} (${year}).`;
    case "BibTeX": {
      const key = bibtexKey(paper);
      const lines = [
        `@article{${key},`,
        `  title     = {${title}},`,
        `  author    = {${authors}},`,
        year !== "n.d." ? `  year      = {${year}},` : null,
        venue ? `  journal   = {${venue}},` : null,
        `}`,
      ].filter(Boolean) as string[];
      return lines.join("\n");
    }
  }
}

interface CitationModalProps {
  paper: Paper;
  onClose: () => void;
}

export function CitationModal({ paper, onClose }: CitationModalProps) {
  const [fmt, setFmt] = useState<Format>("APA");
  const [copied, setCopied] = useState(false);
  const [closing, setClosing] = useState(false);

  const text = formatCitation(paper, fmt);

  function dismiss() {
    setClosing(true);
    setTimeout(onClose, 140);
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className={`cite-modal${closing ? " cite-modal--out" : ""}`} onClick={e => { if (e.target === e.currentTarget) dismiss(); }}>
      <div className="cite-modal__box">
        <div className="cite-modal__header">
          <div className="cite-modal__title">{paper.title}</div>
          <button className="cite-modal__close" onClick={dismiss}>✕ close</button>
        </div>
        <div className="cite-modal__tabs">
          {FORMATS.map(f => (
            <button
              key={f}
              className={`cite-modal__tab${fmt === f ? " cite-modal__tab--active" : ""}`}
              onClick={() => setFmt(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="cite-modal__code" onClick={handleCopy}>{text}</div>
        <div className={`cite-modal__hint${copied ? " cite-modal__hint--copied" : ""}`}>
          {copied ? "copied!" : "click to copy"}
        </div>
      </div>
    </div>
  );
}
