"use client";

import { useState, useRef, useEffect } from "react";

type Progress = string;

interface EvidencePaper {
  id: string;
  title: string;
}

interface EvidenceClaim {
  claim: string;
  papers: EvidencePaper[];
}

interface Result {
  session_id: string;
  papers_used: number;
  depth_reached: number;
  mechanism: string;
  intuition: string;
  limitations: string;
  open_questions: string;
  evidence: EvidenceClaim[];
}

type Status = "idle" | "running" | "done" | "error";

const HINTS = [
  "explain how transformers work",
  "contrast CNNs and RNNs",
  "what are the limits of RLHF",
];

function Section({ label, content }: { label: string; content: string }) {
  return (
    <div>
      <hr className="rule" />
      <div style={{ padding: "20px 0 4px", color: "var(--text-dim)", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        {label}
      </div>
      <p style={{ color: "var(--text)", whiteSpace: "pre-wrap" }}>{content}</p>
    </div>
  );
}

function EvidenceTable({ evidence }: { evidence: EvidenceClaim[] }) {
  return (
    <div>
      <hr className="rule" />
      <div style={{ padding: "20px 0 4px", color: "var(--text-dim)", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        Evidence
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ color: "var(--text-dim)", fontSize: "11px" }}>
            <th style={{ textAlign: "left", paddingBottom: "8px", fontWeight: "normal", width: "140px" }}>Paper ID</th>
            <th style={{ textAlign: "left", paddingBottom: "8px", fontWeight: "normal", width: "220px" }}>Title</th>
            <th style={{ textAlign: "left", paddingBottom: "8px", fontWeight: "normal" }}>Claim</th>
          </tr>
        </thead>
        <tbody>
          {evidence.map((claim, ci) =>
            claim.papers.map((paper, pi) => (
              <tr key={`${ci}-${pi}`} style={{ verticalAlign: "top" }}>
                <td style={{ padding: "3px 16px 3px 0", color: "var(--text-dim)", whiteSpace: "nowrap" }}>
                  <a
                    href={`https://openalex.org/works/${paper.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--text-dim)", textDecoration: "underline", textDecorationColor: "var(--border)" }}
                  >
                    {paper.id.startsWith("arXiv:") ? paper.id.slice(6) : paper.id.slice(0, 12)}
                  </a>
                </td>
                <td style={{ padding: "3px 16px 3px 0", color: "var(--text-dim)" }}>
                  {paper.title.length > 40 ? paper.title.slice(0, 39) + "…" : paper.title}
                </td>
                <td style={{ padding: "3px 0", color: "var(--text)" }}>{pi === 0 ? claim.claim : ""}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [progress, setProgress] = useState<Progress[]>([]);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status === "running") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [answer, progress, status]);

  const lastProgress = progress[progress.length - 1] ?? "";

  async function submit(q: string) {
    if (!q.trim() || status === "running") return;
    setStatus("running");
    setProgress([]);
    setAnswer("");
    setResult(null);
    setError(null);

    try {
      const res = await fetch("/api/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, session_id: sessionId }),
      });

      if (!res.ok || !res.body) throw new Error("Request failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const msg = JSON.parse(line.slice(6));
          if (msg.type === "progress") {
            setProgress((p) => [...p, msg.data]);
          } else if (msg.type === "token") {
            setAnswer((a) => a + msg.data);
          } else if (msg.type === "result") {
            setResult(msg.data);
            setSessionId(msg.data.session_id);
            setStatus("done");
          } else if (msg.type === "error") {
            setError(msg.data);
            setStatus("error");
          }
        }
      }
    } catch (e) {
      setError(String(e));
      setStatus("error");
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    submit(query);
    setQuery("");
  }

  const isRunning = status === "running";
  const hasOutput = answer || result || error;

  return (
    <main style={{ maxWidth: "780px", margin: "0 auto", padding: "80px 24px 120px" }}>

      {/* Logo */}
      <div style={{ textAlign: "center", marginBottom: "48px" }}>
        <pre style={{ display: "inline-block", textAlign: "left", lineHeight: 1.2, color: "var(--text)", fontSize: "13px" }}>{`   _____      __          __
  / ___/_____/ /_  ____  / /____
  \\__ \\/ ___/ __ \\/ __ \\/ / ___/
 ___/ / /__/ / / / /_/ / / /
/____/\\___/_/ /_/\\____/_/_/`}</pre>
        <div style={{ marginTop: "12px", color: "var(--text-dim)", fontSize: "12px" }}>
          autonomous AI research agent · 200M+ papers
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} style={{ marginBottom: "40px" }}>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={{ color: "var(--text-dim)" }}>{">"}</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={HINTS[0]}
            disabled={isRunning}
            autoFocus
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--text)",
              fontFamily: "inherit",
              fontSize: "inherit",
              opacity: isRunning ? 0.4 : 1,
            }}
          />
          {isRunning && (
            <span style={{ color: "var(--text-dim)", fontSize: "11px" }}>{lastProgress.split("]")[0]?.replace("[", "") ?? "…"}</span>
          )}
        </div>
        <hr className="rule" style={{ marginTop: "8px" }} />
        {status === "idle" && (
          <div style={{ marginTop: "8px", color: "var(--text-dim)", fontSize: "11px" }}>
            {HINTS.slice(1).map((h) => (
              <span key={h} style={{ marginRight: "24px", cursor: "pointer" }} onClick={() => { setQuery(h); inputRef.current?.focus(); }}>
                {h}
              </span>
            ))}
          </div>
        )}
      </form>

      {/* Output */}
      {hasOutput && (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>

          {/* Answer */}
          {(answer || isRunning) && (
            <div>
              <hr className="rule" />
              <div style={{ padding: "20px 0 4px", color: "var(--text-dim)", fontSize: "11px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                Answer
              </div>
              <p style={{ whiteSpace: "pre-wrap" }} className={isRunning && !result ? "cursor" : ""}>
                {answer}
              </p>
            </div>
          )}

          {/* Sections */}
          {result && (
            <>
              <Section label="Mechanism" content={result.mechanism} />
              <Section label="Intuition" content={result.intuition} />
              <Section label="Limitations" content={result.limitations} />
              <Section label="Open Questions" content={result.open_questions} />
              <EvidenceTable evidence={result.evidence} />

              <div style={{ textAlign: "center", color: "var(--text-dim)", fontSize: "11px", paddingTop: "8px" }}>
                <hr className="rule" style={{ marginBottom: "16px" }} />
                <span style={{ color: "var(--text)" }}>{result.papers_used} papers</span>
                <span style={{ margin: "0 12px" }}>·</span>
                <span style={{ color: "var(--text)" }}>depth {result.depth_reached}</span>
                <span style={{ margin: "0 12px" }}>·</span>
                <span>session {result.session_id.slice(0, 8)}</span>
              </div>
            </>
          )}

          {/* Error */}
          {error && (
            <div style={{ color: "var(--text-dim)", padding: "16px 0" }}>
              {error}
            </div>
          )}
        </div>
      )}

      <div ref={bottomRef} />
    </main>
  );
}
