import type { Conversation } from "@/types/scholr";
import { pool } from "@/lib/db";
import { ShareViewer } from "@/components/ShareViewer";

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
      messages: messages.map((m: { content: unknown }) => m.content as import("@/types/scholr").ConversationMessage),
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

  return <ShareViewer conv={conv} />;
}
