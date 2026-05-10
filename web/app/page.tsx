"use client";

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import type { Conversation, ConversationMessage, ResearchResult } from "@/types/scholr";
import { Sidebar } from "@/components/Sidebar";
import { Thread } from "@/components/Thread";
import { EvidencePanel } from "@/components/EvidencePanel";
import { Composer } from "@/components/Composer";
import { AuthGate } from "@/components/AuthGate";
import { UpgradeModal } from "@/components/UpgradeModal";
import { downloadBibtex } from "@/lib/bibtex";

// Renumber citations to sequential 1-based order of first appearance.
// Keeps evidence panel badges in sync with [n] tokens in the answer text.
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

function applyRemapToMessages(messages: ConversationMessage[]): ConversationMessage[] {
  return messages.map(m =>
    m.role === "assistant" && m.result ? { ...m, result: remapCitations(m.result) } : m
  );
}

// Split answer_paragraphs into atomic tokens so **bold** and [n] markers
// are never split mid-token during fake streaming.
function tokenise(paragraphs: string[]): string[] {
  const tokens: string[] = [];
  paragraphs.forEach((para, pi) => {
    if (pi > 0) tokens.push("\n\n");
    para.split(/(\[\d+\]|\*\*[^*]+\*\*)/g).forEach(seg => {
      if (/^(\[\d+\]|\*\*[^*]+\*\*)$/.test(seg)) {
        tokens.push(seg);
      } else {
        seg.split(/(\s+)/).forEach(w => { if (w) tokens.push(w); });
      }
    });
  });
  return tokens;
}

const STAGE_MAP: [string, string][] = [
  ["[Session]",          "Loading prior context"],
  ["[Orchestrator]",     "Analyzing your question"],
  ["[Planner]",          "Planning search strategy"],
  ["[Retrieval]",        "Searching 200M+ papers"],
  ["[Level",             "Deepening research"],
  ["[Expansion]",        "Expanding into related concepts"],
  ["[Coverage]",         "Checking coverage"],
  ["[Compression]",      "Extracting key findings"],
  ["[Synthesis] stream", "Drafting answer"],
  ["[Synthesis]",        "Building evidence map"],
  ["[Done]",             ""],
];

function toStageLabel(event: string): string {
  // Sub-topic prefixed events e.g. "[CNNs] [Planner] ..." — skip to avoid oscillation
  if (/^\[[^\]]+\] \[/.test(event)) return "";

  // Multi-topic thread progress: "[Orchestrator] thread 1/2: CNNs"
  const threadMatch = event.match(/\[Orchestrator\] thread (\d+)\/(\d+): (.+)/);
  if (threadMatch) return `Researching ${threadMatch[3]} (${threadMatch[1]}/${threadMatch[2]})`;

  for (const [prefix, label] of STAGE_MAP) {
    if (event.startsWith(prefix) || event.includes(prefix.slice(1, -1))) return label;
  }
  return "";
}

function newConversation(): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "New inquiry",
    createdAt: new Date().toISOString(),
    depthReached: 0,
    papersUsed: 0,
    messages: [],
  };
}

export default function Home() {
  const { data: session, status } = useSession();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isFakeStreaming, setIsFakeStreaming] = useState(false);
  const [fakeStreamText, setFakeStreamText] = useState("");
  const [progressStage, setProgressStage] = useState("");
  const [hoveredCite, setHoveredCite] = useState<number | null>(null);
  const [depth, setDepth] = useState(1);
  const [yearFrom, setYearFrom] = useState<number | null>(null);
  const [k, setK] = useState(8);
  const [upgradeInfo, setUpgradeInfo] = useState<{ used: number; limit: number } | null>(null);
  const [ready, setReady] = useState(false);
  const [showLoader, setShowLoader] = useState(true);
  const [loaderFading, setLoaderFading] = useState(false);
  const mountTime = useRef(Date.now());

  useEffect(() => {
    if (!ready) return;
    const elapsed = Date.now() - mountTime.current;
    const remaining = Math.max(0, 750 - elapsed);
    const fadeTimer = setTimeout(() => {
      setLoaderFading(true);
      setTimeout(() => setShowLoader(false), 350);
    }, remaining);
    return () => clearTimeout(fadeTimer);
  }, [ready]);

  const activeConv = conversations.find(c => c.id === activeId) ?? null;
  const lastResult = activeConv?.messages.findLast(m => m.role === "assistant" && m.result != null)?.result ?? null;

  const citedPapers = lastResult?.papers ?? [];

  useEffect(() => {
    if (status === "authenticated") {
      fetch("/api/conversations")
        .then(r => r.json())
        .then(data => {
          if (data.conversations?.length) {
            const loaded: Conversation[] = data.conversations.map((c: { id: string; title: string; created_at: string; depth_reached: number; papers_used: number }) => ({
              id: c.id,
              title: c.title,
              createdAt: c.created_at,
              depthReached: c.depth_reached,
              papersUsed: c.papers_used,
              messages: [],
            }));
            setConversations(loaded);
            setActiveId(loaded[0].id);
            // Fetch the first conversation's messages immediately so content renders without a click
            fetch(`/api/conversations/${loaded[0].id}`)
              .then(r => r.json())
              .then(msgData => {
                setConversations(prev =>
                  prev.map(c => c.id === loaded[0].id ? { ...c, messages: applyRemapToMessages(msgData.messages ?? []) } : c)
                );
              })
              .catch(() => {});
          } else {
            const fresh = newConversation();
            setConversations([fresh]);
            setActiveId(fresh.id);
          }
          setReady(true);
        })
        .catch(() => {
          const fresh = newConversation();
          setConversations([fresh]);
          setActiveId(fresh.id);
          setReady(true);
        });
    } else if (status === "unauthenticated") {
      const fresh = newConversation();
      setConversations([fresh]);
      setActiveId(fresh.id);
      setReady(true);
    }
  }, [status]);

  function handleNew() {
    if (activeConv && activeConv.messages.length === 0) return;
    const conv = newConversation();
    setConversations(prev => [conv, ...prev]);
    setActiveId(conv.id);
    setFakeStreamText("");
  }

  async function handleDelete(id: string) {
    setConversations(prev => prev.filter(c => c.id !== id));
    if (activeId === id) {
      const remaining = conversations.filter(c => c.id !== id);
      setActiveId(remaining[0]?.id ?? null);
    }
    await fetch(`/api/conversations/${id}`, { method: "DELETE" }).catch(() => {});
  }

  async function handleSelect(id: string) {
    setActiveId(id);
    const existing = conversations.find(c => c.id === id);
    if (existing && existing.messages.length === 0) {
      try {
        const res = await fetch(`/api/conversations/${id}`);
        if (res.ok) {
          const data = await res.json();
          setConversations(prev =>
            prev.map(c => c.id === id ? { ...c, messages: applyRemapToMessages(data.messages ?? []) } : c)
          );
        }
      } catch {}
    }
  }

  async function handleSubmit(query: string) {
    if (!activeId || isStreaming) return;

    const isFirstQuery = (activeConv?.messages.length ?? 0) === 0;

    if (status === "authenticated") {
      const limitRes = await fetch("/api/query-limit", { method: "POST" });
      if (!limitRes.ok) {
        const data = await limitRes.json();
        setConversations(prev => prev.map(c =>
          c.id === activeId ? { ...c, messages: c.messages.slice(0, -2) } : c
        ));
        setIsStreaming(false);
        setUpgradeInfo({ used: data.used ?? 10, limit: data.limit ?? 10 });
        return;
      }
    }
    const userMsg: ConversationMessage = { role: "user", query };
    const assistantMsg: ConversationMessage = { role: "assistant", result: null };

    setConversations(prev => prev.map(c =>
      c.id === activeId
        ? { ...c, title: c.messages.length === 0 ? query.slice(0, 60) : c.title, messages: [...c.messages, userMsg, assistantMsg] }
        : c
    ));

    setIsStreaming(true);
    setIsFakeStreaming(false);
    setFakeStreamText("");
    setProgressStage("");

    const sessionId = activeConv?.sessionId;

    try {
      const userId = (session?.user as { id?: string })?.id;
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/research`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(userId ? { "X-User-Id": userId } : {}),
        },
        body: JSON.stringify({ query, session_id: sessionId, k, year_from: yearFrom }),
      });

      if (!res.ok) {
        let errMsg = "Request failed";
        try { const d = await res.json(); errMsg = d.detail ?? errMsg; } catch {}
        setIsStreaming(false);
        setProgressStage("");
        setConversations(prev => prev.map(c => {
          if (c.id !== activeId) return c;
          const msgs = [...c.messages];
          msgs[msgs.length - 1] = { role: "assistant", result: null, error: errMsg };
          return { ...c, messages: msgs };
        }));
        return;
      }
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let finalResult: ResearchResult | null = null;
      let errorMsg: string | null = null;
      let suggestionMsg: string | null = null;
      let parallelTopics: string[] = [];
      let parallelTotal = 0;

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
            const event = msg.data as string;
            const parallelStart = event.match(/\[Orchestrator\] running (\d+) research threads in parallel/);
            if (parallelStart) { parallelTopics = []; parallelTotal = parseInt(parallelStart[1]); continue; }
            const threadMatch = event.match(/\[Orchestrator\] thread \d+\/\d+: (.+)/);
            if (threadMatch && parallelTotal > 1) {
              parallelTopics.push(threadMatch[1]);
              setProgressStage(`Researching ${parallelTopics.join(" · ")}`);
              continue;
            }
            const l = toStageLabel(event);
            if (l) setProgressStage(l);
          }
          else if (msg.type === "result") finalResult = msg.data as ResearchResult;
          else if (msg.type === "suggestion") suggestionMsg = msg.data as string;
          else if (msg.type === "error") errorMsg = msg.data as string;
        }
      }

      if (suggestionMsg || errorMsg) {
        setIsStreaming(false);
        setProgressStage("");
        const payload = suggestionMsg
          ? { role: "assistant" as const, result: null, suggestion: suggestionMsg }
          : { role: "assistant" as const, result: null, error: errorMsg! };
        setConversations(prev => prev.map(c => {
          if (c.id !== activeId) return c;
          const msgs = [...c.messages];
          msgs[msgs.length - 1] = payload;
          return { ...c, messages: msgs };
        }));
      }

      if (finalResult) {
        const fr = remapCitations(finalResult);
        setIsStreaming(false);

        // Commit full result immediately (evidence panel populates)
        setConversations(prev => prev.map(c => {
          if (c.id !== activeId) return c;
          const msgs = [...c.messages];
          msgs[msgs.length - 1] = { role: "assistant", result: fr };
          return { ...c, depthReached: fr.depth_reached, papersUsed: fr.papers_used, sessionId: fr.session_id, messages: msgs };
        }));

        // Fake-stream the formatted answer
        const tokens = tokenise(fr.answer_paragraphs);
        setIsFakeStreaming(true);
        setFakeStreamText("");
        let revealed = "";
        let i = 0;
        const tick = setInterval(() => {
          if (i >= tokens.length) {
            clearInterval(tick);
            setIsFakeStreaming(false);
            return;
          }
          revealed += tokens[i++];
          setFakeStreamText(revealed);
        }, 22);

        if (status === "authenticated") {
          if (isFirstQuery) {
            fetch("/api/conversations", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                id: activeId,
                title: query.slice(0, 60),
                depthReached: fr.depth_reached,
                papersUsed: fr.papers_used,
                messages: [userMsg, { role: "assistant", result: fr }],
              }),
            }).catch(() => {});
          } else {
            fetch(`/api/conversations/${activeId}`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                depthReached: fr.depth_reached,
                papersUsed: fr.papers_used,
                messages: [userMsg, { role: "assistant", result: fr }],
              }),
            }).catch(() => {});
          }
        }
      }
    } catch (e) {
      console.error(e);
      setIsStreaming(false);
    }
  }

  function handleCiteClick(n: number) {
    document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function handleExportBibtex() {
    if (lastResult?.papers?.length) downloadBibtex(lastResult.papers);
  }

  async function handleShare() {
    if (!activeId) return;
    try {
      const res = await fetch(`/api/conversations/${activeId}/share`, { method: "POST" });
      if (res.ok) {
        const { token } = await res.json();
        await navigator.clipboard.writeText(`${window.location.origin}/share/${token}`);
        alert("Share link copied to clipboard");
      }
    } catch {}
  }

  const showAuthGate = status === "unauthenticated";

  return (
    <div className="app">
      {showAuthGate && <AuthGate onAuthenticated={() => {}} />}
      {upgradeInfo && <UpgradeModal used={upgradeInfo.used} limit={upgradeInfo.limit} onClose={() => setUpgradeInfo(null)} />}

      <Sidebar conversations={conversations} activeId={activeId} onSelect={handleSelect} onNew={handleNew} onDelete={handleDelete} />

      <div className="app__center">
        {showLoader ? (
          <div className={`pane-loader${loaderFading ? " pane-loader--out" : ""}`}>
            <img src="/scholr.png" className="pane-loader__logo" alt="Scholr" />
            <div className="pane-loader__dots">
              <div className="pane-loader__dot" />
              <div className="pane-loader__dot" />
              <div className="pane-loader__dot" />
            </div>
          </div>
        ) : activeConv ? (
          <div className="pane-content-in" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <Thread
              messages={activeConv.messages}
              fakeStreamText={fakeStreamText}
              isFakeStreaming={isFakeStreaming}
              isStreaming={isStreaming}
              progressStage={progressStage}
              hoveredCite={hoveredCite}
              onHover={setHoveredCite}
              onCiteClick={handleCiteClick}
              onFollowUp={handleSubmit}
              onExportBibtex={handleExportBibtex}
              onShare={handleShare}
              title={activeConv.title}
              sessionId={activeConv.sessionId}
            />
            <Composer onSubmit={handleSubmit} disabled={isStreaming} depth={depth} onDepthChange={setDepth} yearFrom={yearFrom} onYearFromChange={setYearFrom} k={k} onKChange={setK} />
          </div>
        ) : (
          <div className="app__empty pane-content-in">
            Select or start a new inquiry
          </div>
        )}
      </div>

      <EvidencePanel
        papers={citedPapers}
        depth={lastResult?.depth_reached ?? 0}
        hoveredCite={hoveredCite}
        onHover={setHoveredCite}
      />
    </div>
  );
}
