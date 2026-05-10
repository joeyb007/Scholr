import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { pool } from "@/lib/db";

const FREE_LIMIT = 10;

export async function POST() {
  const session = await auth();
  if (!session?.user?.id) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userId = (session.user as { id: string }).id;

  const { rows: [user] } = await pool.query(
    "SELECT queries_today, queries_reset_date FROM users WHERE id = $1",
    [userId]
  );

  if (!user) return NextResponse.json({ error: "User not found" }, { status: 404 });

  const today = new Date().toISOString().slice(0, 10);
  const resetDate = user.queries_reset_date?.toISOString?.()?.slice(0, 10) ?? today;
  const needsReset = resetDate < today;
  const current = needsReset ? 0 : (user.queries_today ?? 0);

  if (current >= FREE_LIMIT) {
    return NextResponse.json({ error: "limit_reached", used: current, limit: FREE_LIMIT }, { status: 429 });
  }

  await pool.query(
    "UPDATE users SET queries_today = $1, queries_reset_date = $2 WHERE id = $3",
    [current + 1, today, userId]
  );

  return NextResponse.json({ used: current + 1, limit: FREE_LIMIT });
}
