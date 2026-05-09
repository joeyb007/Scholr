import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { pool } from "@/lib/db";

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth();
  if (!session?.user?.id) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const userId = (session.user as { id: string }).id;

  const { rows: [conv] } = await pool.query(
    "SELECT * FROM conversations WHERE id = $1 AND user_id = $2",
    [id, userId]
  );
  if (!conv) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const { rows: messages } = await pool.query(
    "SELECT role, content FROM messages WHERE conversation_id = $1 ORDER BY created_at",
    [id]
  );

  return NextResponse.json({
    ...conv,
    messages: messages.map((m: { role: string; content: unknown }) => m.content),
  });
}

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth();
  if (!session?.user?.id) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const userId = (session.user as { id: string }).id;
  const { depthReached, papersUsed, messages } = await req.json();

  await pool.query(
    `UPDATE conversations SET depth_reached = $1, papers_used = $2 WHERE id = $3 AND user_id = $4`,
    [depthReached ?? 0, papersUsed ?? 0, id, userId]
  );

  for (const msg of messages ?? []) {
    await pool.query(
      "INSERT INTO messages (conversation_id, role, content) VALUES ($1, $2, $3)",
      [id, msg.role, JSON.stringify(msg)]
    );
  }

  return NextResponse.json({ ok: true });
}

export async function DELETE(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth();
  if (!session?.user?.id) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const userId = (session.user as { id: string }).id;

  await pool.query(
    "DELETE FROM conversations WHERE id = $1 AND user_id = $2",
    [id, userId]
  );
  return NextResponse.json({ ok: true });
}
