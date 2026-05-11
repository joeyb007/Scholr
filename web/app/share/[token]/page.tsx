import type { Conversation, ConversationMessage } from "@/types/scholr";
import { pool } from "@/lib/db";

async function getSharedConversation(token: string): Promise<Conversation | null> {
  try {
    const { rows: [conv] } = await pool.query(
      "SELECT * FROM conversations WHERE share_token = $1",
      [token]
    );
    if (!conv) return null;
    const { rows: messages } = await pool.query(
      "SELECT role, content FROM messages WHERE conversation_id = $1 ORDER BY created_at",
      [conv.id]
    );
    return {
      id: conv.id,
      title: conv.title,
      createdAt: conv.created_at,
      depthReached: conv.depth_reached,
      papersUsed: conv.papers_used,
      messages: messages.map((m: { content: unknown }) => m.content as ConversationMessage),
    };
  } catch {
    return null;
  }
}

export default async function SharePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const conv = await getSharedConversation(token);

  if (!conv) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", fontFamily: "var(--serif)", color: "var(--dim)", fontStyle: "italic" }}>
        This shared research could not be found.
      </div>
    );
  }

  const lastResult = conv.messages.findLast((m: { role: string }) => m.role === "assistant");

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Top bar */}
        <div style={{ padding: "16px 28px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
          <div>
            <span style={{ fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 17, color: "var(--fg)" }}>{conv.title}</span>
          </div>
          <div style={{ display: "flex", gap: 16, fontFamily: "var(--mono)", fontSize: 10, color: "var(--dim)" }}>
            <span style={{ color: "var(--amber)" }}>● GROUNDED</span>
            <span style={{ color: "var(--faint)" }}>read-only</span>
          </div>
        </div>

        {/* Thread */}
        <div style={{ flex: 1, overflowY: "auto", padding: "28px 28px 0" }}>
          {conv.messages.map((msg: ConversationMessage, i: number) => {
            if (msg.role === "user") {
              return (
                <div key={i} style={{ marginBottom: 24 }}>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 8 }}>You asked</div>
                  <div style={{ fontFamily: "var(--serif)", fontSize: 24, lineHeight: 1.25, letterSpacing: "-0.005em", color: "var(--fg)" }}>{msg.query}</div>
                  {msg.result && (
                    <div style={{ fontFamily: "var(--mono)", fontSize: 10.5, color: "var(--dim)", marginTop: 8 }}>
                      ↳ depth {msg.result.depth_reached} · {msg.result.papers_used} papers
                    </div>
                  )}
                </div>
              );
            }
            const result = msg.result;
            if (!result) return null;
            return (
              <div key={i} style={{ marginBottom: 32 }}>
                <div style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 12 }}>Answer</div>
                <div style={{ fontFamily: "var(--serif)", fontSize: 16, lineHeight: 1.7, color: "var(--body)", marginBottom: 24 }}>
                  {(result.answer_paragraphs ?? []).map((p: string, pi: number) => (
                    <p key={pi} style={{ marginBottom: 14 }}>{p.replace(/\[\d+\]/g, "")}</p>
                  ))}
                </div>
              </div>
            );
          })}
          <div style={{ height: 40 }} />
        </div>
      </div>

      {/* Evidence panel */}
      <div style={{ width: 320, flexShrink: 0, background: "var(--panel)", borderLeft: "1px solid var(--border)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ padding: "16px 20px 12px", borderBottom: "1px solid var(--border)" }}>
          <span style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase", color: "var(--dim)" }}>Evidence</span>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "0 20px" }}>
          {(lastResult?.result?.papers_used ?? 0) > 0 && (
            <div style={{ color: "var(--dim)", fontFamily: "var(--serif)", fontStyle: "italic", fontSize: 13, paddingTop: 24 }}>
              {lastResult?.result?.papers_used} papers cited
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
