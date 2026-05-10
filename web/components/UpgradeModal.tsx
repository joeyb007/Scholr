"use client";

import { useState } from "react";

interface UpgradeModalProps {
  used: number;
  limit: number;
  onClose: () => void;
}

export function UpgradeModal({ used, limit, onClose }: UpgradeModalProps) {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [closing, setClosing] = useState(false);

  function dismiss() {
    setClosing(true);
    setTimeout(onClose, 140);
  }

  async function handleSubmit() {
    if (!email.trim()) return;
    await fetch("/api/waitlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    setSubmitted(true);
  }

  return (
    <div className={`confirm-overlay${closing ? " confirm-overlay--out" : ""}`} onClick={e => { if (e.target === e.currentTarget) dismiss(); }}>
      <div className="confirm-box upgrade-box">
        <div className="upgrade__logo">S</div>
        <div className="upgrade__title">You've used your {limit} free queries today</div>
        <div className="upgrade__body">
          Scholr is free during beta. Join the waitlist to get early access to unlimited queries, deeper research, and priority support.
        </div>
        {submitted ? (
          <div className="upgrade__success">You're on the list — we'll be in touch.</div>
        ) : (
          <div className="upgrade__form">
            <input
              className="upgrade__input"
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSubmit()}
              autoFocus
            />
            <button className="upgrade__submit" onClick={handleSubmit}>
              Join waitlist
            </button>
          </div>
        )}
        <button className="upgrade__dismiss" onClick={dismiss}>
          {submitted ? "done" : "maybe later"}
        </button>
      </div>
    </div>
  );
}
