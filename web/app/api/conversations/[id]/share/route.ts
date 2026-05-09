import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { pool } from "@/lib/db";

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth();
  if (!session?.user?.id) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { id } = await params;
  const userId = (session.user as { id: string }).id;

  const { rows: [conv] } = await pool.query(
    `UPDATE conversations SET share_token = gen_random_uuid()
     WHERE id = $1 AND user_id = $2 RETURNING share_token`,
    [id, userId]
  );
  if (!conv) return NextResponse.json({ error: "Not found" }, { status: 404 });

  return NextResponse.json({ token: conv.share_token });
}
