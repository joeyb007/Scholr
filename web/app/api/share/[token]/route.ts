import { NextRequest, NextResponse } from "next/server";
import { pool } from "@/lib/db";

export async function GET(req: NextRequest, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;

  const { rows: [conv] } = await pool.query(
    "SELECT * FROM conversations WHERE share_token = $1",
    [token]
  );
  if (!conv) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const { rows: messages } = await pool.query(
    "SELECT role, content FROM messages WHERE conversation_id = $1 ORDER BY created_at",
    [conv.id]
  );

  return NextResponse.json({
    ...conv,
    messages: messages.map((m: { role: string; content: unknown }) => m.content),
  });
}
