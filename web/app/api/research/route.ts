// Unused route — frontend calls the Railway backend directly.
// Kept as placeholder for future proxy upgrade (requires Vercel Pro for 300s timeout).
export async function POST() {
  return new Response("Not implemented", { status: 501 });
}
