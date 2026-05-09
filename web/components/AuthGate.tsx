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
      <div className="gate__box">
        <div className="gate__title">
          {mode === "signin" ? "Sign in to Scholr" : "Create account"}
        </div>
        <div className="gate__sub">Research 200M+ academic papers</div>

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
