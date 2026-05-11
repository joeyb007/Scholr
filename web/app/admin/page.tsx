import { auth } from "@/lib/auth";
import { pool } from "@/lib/db";
import { notFound } from "next/navigation";

const ADMIN_EMAIL = "josephbarbosa416@gmail.com";

async function getStats() {
  const [users, queries, convos, waitlist, recentUsers, recentWaitlist, topConvos] = await Promise.all([
    pool.query("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') AS today FROM users"),
    pool.query("SELECT COALESCE(SUM(queries_today), 0) AS today, COALESCE(SUM(queries_today), 0) AS running FROM users WHERE queries_reset_date = CURRENT_DATE"),
    pool.query("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') AS today FROM conversations"),
    pool.query("SELECT COUNT(*) AS total FROM waitlist"),
    pool.query("SELECT email, created_at FROM users ORDER BY created_at DESC LIMIT 8"),
    pool.query("SELECT email, created_at FROM waitlist ORDER BY created_at DESC LIMIT 8"),
    pool.query("SELECT title, papers_used, depth_reached, created_at FROM conversations ORDER BY created_at DESC LIMIT 10"),
  ]);

  return {
    users: { total: users.rows[0].total, today: users.rows[0].today },
    queries: { today: queries.rows[0].today },
    convos: { total: convos.rows[0].total, today: convos.rows[0].today },
    waitlist: { total: waitlist.rows[0].total },
    recentUsers: recentUsers.rows,
    recentWaitlist: recentWaitlist.rows,
    topConvos: topConvos.rows,
  };
}

function Stat({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div style={{ background: "var(--raised)", border: "1px solid var(--border)", borderRadius: 6, padding: "16px 20px" }}>
      <div style={{ fontFamily: "var(--mono)", fontSize: 10, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 8 }}>{label}</div>
      <div style={{ fontFamily: "var(--serif)", fontSize: 32, color: "var(--fg)", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--faint)", marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function fmt(d: string) {
  return new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default async function AdminPage() {
  const session = await auth();
  const email = (session?.user as { email?: string })?.email;
  if (email !== ADMIN_EMAIL) return notFound();

  const s = await getStats();

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)", padding: "40px 48px", fontFamily: "var(--mono)" }}>
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontFamily: "var(--serif)", fontSize: 24, color: "var(--fg)", marginBottom: 4 }}>scholr admin</div>
        <div style={{ fontSize: 10, color: "var(--faint)", letterSpacing: "0.1em" }}>last loaded: {new Date().toLocaleString()}</div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 40 }}>
        <Stat label="Total users" value={s.users.total} sub={`+${s.users.today} today`} />
        <Stat label="Queries today" value={s.queries.today} sub="across all users" />
        <Stat label="Conversations" value={s.convos.total} sub={`+${s.convos.today} today`} />
        <Stat label="Waitlist" value={s.waitlist.total} sub="signups" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24 }}>
        <div>
          <div style={{ fontSize: 10, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 12 }}>Recent users</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {s.recentUsers.map((u: { email: string; created_at: string }, i: number) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--raised)", borderRadius: 4 }}>
                <span style={{ fontSize: 11, color: "var(--fg)" }}>{u.email}</span>
                <span style={{ fontSize: 10, color: "var(--faint)" }}>{fmt(u.created_at)}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 10, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 12 }}>Waitlist</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {s.recentWaitlist.length === 0
              ? <div style={{ fontSize: 11, color: "var(--faint)", fontStyle: "italic" }}>No signups yet</div>
              : s.recentWaitlist.map((w: { email: string; created_at: string }, i: number) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--raised)", borderRadius: 4 }}>
                  <span style={{ fontSize: 11, color: "var(--amber)" }}>{w.email}</span>
                  <span style={{ fontSize: 10, color: "var(--faint)" }}>{fmt(w.created_at)}</span>
                </div>
              ))}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 10, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--dim)", marginBottom: 12 }}>Recent queries</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {s.topConvos.map((c: { title: string; papers_used: number; depth_reached: number; created_at: string }, i: number) => (
              <div key={i} style={{ padding: "8px 12px", background: "var(--raised)", borderRadius: 4 }}>
                <div style={{ fontSize: 11, color: "var(--fg)", marginBottom: 3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.title}</div>
                <div style={{ fontSize: 9, color: "var(--faint)" }}>{c.papers_used} papers · depth {c.depth_reached} · {fmt(c.created_at)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
