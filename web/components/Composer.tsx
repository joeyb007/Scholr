"use client";

import { useState, useRef, KeyboardEvent } from "react";

interface ComposerProps {
  onSubmit: (query: string) => void;
  disabled: boolean;
  depth: number;
  onDepthChange: (d: number) => void;
}

export function Composer({ onSubmit, disabled, depth, onDepthChange }: ComposerProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey && text.trim()) {
      e.preventDefault();
      onSubmit(text.trim());
      setText("");
    }
  }

  return (
    <div className="composer">
      <div className="composer__box">
        <div className="composer__input-row">
          <span className="composer__prompt">{">"}</span>
          <input
            ref={inputRef}
            className="composer__input"
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="ask a follow-up — or start a new inquiry"
          />
        </div>
        <div className="composer__chips">
          {[0, 1, 2].map(d => (
            <button
              key={d}
              onClick={() => onDepthChange(d)}
              className={`composer__chip${depth === d ? " composer__chip--active" : ""}`}
            >
              depth {d}
            </button>
          ))}
          <button className="composer__chip">k = 10</button>
          <button className="composer__chip">filter: 2010+</button>
          <button className="composer__chip composer__chip--add">+ model sonnet</button>
          <span className="composer__send">↵ send</span>
        </div>
      </div>
    </div>
  );
}
