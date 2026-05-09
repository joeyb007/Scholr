import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { pool } from "@/lib/db";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { rows } = await pool.query(
    `SELECT id, title, depth_reached, papers_used, share_token, created_at
     FROM conversations WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50`,
    [(session.user as { id: string }).id]
  );
  return NextResponse.json({ conversations: rows });
}

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id: clientId, title, depthReached, papersUsed, messages } = await req.json();
  const userId = (session.user as { id: string }).id;

  const { rows: [conv] } = await pool.query(
    `INSERT INTO conversations (id, user_id, title, depth_reached, papers_used)
     VALUES (COALESCE($1::uuid, gen_random_uuid()), $2, $3, $4, $5) RETURNING id`,
    [clientId ?? null, userId, title, depthReached ?? 0, papersUsed ?? 0]
  );

  for (const msg of messages ?? []) {
    await pool.query(
      "INSERT INTO messages (conversation_id, role, content) VALUES ($1, $2, $3)",
      [conv.id, msg.role, JSON.stringify(msg)]
    );
  }

  return NextResponse.json({ id: conv.id });
}
