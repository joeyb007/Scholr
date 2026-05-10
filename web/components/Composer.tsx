"use client";

import { useState, useRef, useEffect, KeyboardEvent, CSSProperties } from "react";
import { createPortal } from "react-dom";

interface ChipOption {
  label: string;
  value: number | null;
}

interface ChipPopoverProps {
  chipLabel: string;
  title: string;
  description: string;
  options: ChipOption[];
  value: number | null;
  onChange: (v: number | null) => void;
  active?: boolean;
}

function ChipPopover({ chipLabel, title, description, options, value, onChange, active }: ChipPopoverProps) {
  const [open, setOpen] = useState(false);
  const [panelStyle, setPanelStyle] = useState<CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  function handleToggle() {
    if (!open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPanelStyle({
        position: "fixed",
        left: rect.left,
        bottom: window.innerHeight - rect.top + 8,
      });
    }
    setOpen(o => !o);
  }

  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (
        panelRef.current && !panelRef.current.contains(e.target as Node) &&
        triggerRef.current && !triggerRef.current.contains(e.target as Node)
      ) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div className="chip-pop">
      <button
        ref={triggerRef}
        className={`composer__chip${active ? " composer__chip--active" : ""}`}
        onClick={handleToggle}
      >
        {chipLabel}
      </button>
      {open && createPortal(
        <div className="chip-pop__panel" ref={panelRef} style={panelStyle}>
          <div className="chip-pop__title">{title}</div>
          <div className="chip-pop__desc">{description}</div>
          <div className="chip-pop__options">
            {options.map(opt => (
              <button
                key={String(opt.value)}
                className={`chip-pop__option${opt.value === value ? " chip-pop__option--active" : ""}`}
                onClick={() => { onChange(opt.value); setOpen(false); }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}

interface ComposerProps {
  onSubmit: (query: string) => void;
  disabled: boolean;
  depth: number;
  onDepthChange: (d: number) => void;
  yearFrom: number | null;
  onYearFromChange: (y: number | null) => void;
  k: number;
  onKChange: (k: number) => void;
}

export function Composer({ onSubmit, disabled, depth, onDepthChange, yearFrom, onYearFromChange, k, onKChange }: ComposerProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey && text.trim()) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleSubmit() {
    if (!text.trim() || disabled) return;
    onSubmit(text.trim());
    setText("");
  }

  const depthLabel = `depth ${depth}`;
  const yearLabel = yearFrom === null ? "any year" : `${yearFrom}+`;
  const kLabel = `k = ${k}`;

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
          <span className="composer__params-label">search parameters</span>
          <ChipPopover
            chipLabel={depthLabel}
            title="Research depth"
            description="How many levels of concept expansion to explore. Higher depth finds more connections but takes longer."
            options={[
              { label: "depth 0 — surface scan", value: 0 },
              { label: "depth 1 — standard", value: 1 },
              { label: "depth 2 — deep dive", value: 2 },
            ]}
            value={depth}
            onChange={v => onDepthChange(v ?? 1)}
            active={depth !== 1}
          />
          <ChipPopover
            chipLabel={yearLabel}
            title="Publication year"
            description="Filter to papers published after this year. Useful for fast-moving fields where older literature is less relevant."
            options={[
              { label: "any year", value: null },
              { label: "2015+", value: 2015 },
              { label: "2018+", value: 2018 },
              { label: "2020+", value: 2020 },
              { label: "2022+", value: 2022 },
            ]}
            value={yearFrom}
            onChange={onYearFromChange}
            active={yearFrom !== null}
          />
          <ChipPopover
            chipLabel={kLabel}
            title="Papers per search"
            description="Number of papers fetched per query. More papers means broader coverage but a longer wait."
            options={[
              { label: "k = 4 — fast", value: 4 },
              { label: "k = 8 — balanced", value: 8 },
              { label: "k = 16 — thorough", value: 16 },
            ]}
            value={k}
            onChange={v => onKChange(v ?? 8)}
            active={k !== 8}
          />
          <button
            className={`composer__send${text.trim() && !disabled ? " composer__send--active" : ""}`}
            onMouseDown={e => { e.preventDefault(); handleSubmit(); }}
          >↵ send</button>
        </div>
      </div>
    </div>
  );
}
