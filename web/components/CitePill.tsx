"use client";

interface CitePillProps {
  n: number;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  onCiteClick?: (n: number) => void;
}

export function CitePill({ n, hoveredCite, onHover, onCiteClick }: CitePillProps) {
  return (
    <sup
      className={`cite${hoveredCite === n ? " cite--active" : ""}`}
      onMouseEnter={() => onHover(n)}
      onMouseLeave={() => onHover(null)}
      onClick={() => onCiteClick?.(n)}
      style={{ cursor: onCiteClick ? "pointer" : "default" }}
    >
      {n}
    </sup>
  );
}

interface ParsedTextProps {
  text: string;
  hoveredCite: number | null;
  onHover: (n: number | null) => void;
  onCiteClick?: (n: number) => void;
}

export function ParsedText({ text, hoveredCite, onHover, onCiteClick }: ParsedTextProps) {
  const parts = text.split(/(\[\d+\]|\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, i) => {
        const citeMatch = part.match(/^\[(\d+)\]$/);
        if (citeMatch) {
          return (
            <CitePill
              key={i}
              n={parseInt(citeMatch[1])}
              hoveredCite={hoveredCite}
              onHover={onHover}
              onCiteClick={onCiteClick}
            />
          );
        }
        const boldMatch = part.match(/^\*\*([^*]+)\*\*$/);
        if (boldMatch) {
          return <strong key={i} className="answer__bold">{boldMatch[1]}</strong>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
