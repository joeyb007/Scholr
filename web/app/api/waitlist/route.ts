import { NextRequest, NextResponse } from "next/server";
import { pool } from "@/lib/db";

export async function POST(req: NextRequest) {
  const { email } = await req.json();
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: "Invalid email" }, { status: 400 });
  }

  await pool.query(
    "INSERT INTO waitlist (email) VALUES ($1) ON CONFLICT (email) DO NOTHING",
    [email]
  );

  return NextResponse.json({ ok: true });
}
