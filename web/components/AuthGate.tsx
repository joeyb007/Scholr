"use client";

import { signIn } from "next-auth/react";
import { useState } from "react";

interface AuthGateProps {
  onAuthenticated: () => void;
}

export function AuthGate({ onAuthenticated }: AuthGateProps) {
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleGoogle() {
    await signIn("google", { callbackUrl: "/" });
  }

  async function handleCredentials(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (mode === "register") {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error ?? "Registration failed");
        setLoading(false);
        return;
      }
    }

    const result = await signIn("credentials", { email, password, redirect: false });
    if (result?.error) {
      setError("Invalid email or password");
      setLoading(false);
    } else {
      onAuthenticated();
    }
  }

  return (
    <div className="gate">
      <div className="gate__hero">
        <img src="/scholr.png" className="gate__hero-logo" alt="Scholr" />
        <div className="gate__headline">Research that cites its sources.</div>
        <div className="gate__pitch">
          Ask any research question. Scholr searches 200M+ academic papers and returns a structured answer where every claim links back to a real paper you can verify.
        </div>
        <div className="gate__features">
          <div className="gate__feature">
            <div className="gate__feature-dot" />
            <div className="gate__feature-text">Searches OpenAlex's 200M+ paper corpus — no paywalls, no hallucinations</div>
          </div>
          <div className="gate__feature">
            <div className="gate__feature-dot" />
            <div className="gate__feature-text">Every claim is inline-cited and linked to the source paper</div>
          </div>
          <div className="gate__feature">
            <div className="gate__feature-dot" />
            <div className="gate__feature-text">Follow-up questions build on prior context — like a research session, not a search</div>
          </div>
          <div className="gate__feature">
            <div className="gate__feature-dot" />
            <div className="gate__feature-text">Export citations as BibTeX with one click</div>
          </div>
        </div>
      </div>

      <div className="gate__panel">
        <div className="gate__title">
          {mode === "signin" ? "Sign in" : "Create account"}
        </div>
        <div className="gate__sub">10 free queries per day during beta</div>

        <button className="gate__google" onClick={handleGoogle}>
          Continue with Google
        </button>

        <div className="gate__divider">or</div>

        <form onSubmit={handleCredentials}>
          <input
            className="gate__input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <input
            className="gate__input"
            type="password"
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
          {error && <div className="gate__error">{error}</div>}
          <button className="gate__submit" type="submit" disabled={loading}>
            {loading ? "…" : mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>

        <button className="gate__toggle" onClick={() => setMode(m => m === "signin" ? "register" : "signin")}>
          {mode === "signin" ? "No account? Create one →" : "Already have an account? Sign in →"}
        </button>
      </div>
    </div>
  );
}
