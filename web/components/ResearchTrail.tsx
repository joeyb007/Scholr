"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { TrailState } from "@/lib/trail";

// Live "research trail" — thinking steps fan out across angles, sources accumulate,
// then converge. Driven by TrailState derived from the SSE stream. The panel animates
// its height as content grows (capped just below the composer, then each column scrolls
// on its own), auto-follows the newest item during research, tracks elapsed time, shows
// a fade when a column has more below, and once finished eases closed into a summary bar.
// Click the header to re-expand.

function hrefFor(id: string): string {
  return id.startsWith("arXiv:")
    ? `https://arxiv.org/abs/${id.slice(6)}`
    : `https://openalex.org/works/${id}`;
}

export function ResearchTrail({ trail }: { trail: TrailState }) {
  const { title, steps, sources, done } = trail;

  const headRef = useRef<HTMLDivElement>(null);
  const trailColRef = useRef<HTMLDivElement>(null);
  const sourcesColRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | undefined>(undefined);
  const [collapsed, setCollapsed] = useState(false);
  const [maxH, setMaxH] = useState(460);
  const [elapsed, setElapsed] = useState(0);
  const [trailMore, setTrailMore] = useState(false);
  const [sourcesMore, setSourcesMore] = useState(false);

  const checkMore = () => {
    const t = trailColRef.current, s = sourcesColRef.current;
    if (t) setTrailMore(t.scrollHeight - t.scrollTop - t.clientHeight > 4);
    if (s) setSourcesMore(s.scrollHeight - s.scrollTop - s.clientHeight > 4);
  };

  // Cap the panel so its bottom sits just above the composer, responsive to window size.
  useEffect(() => {
    const update = () => setMaxH(Math.max(280, window.innerHeight - 300));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  // Live elapsed timer while research is running (whole seconds).
  useEffect(() => {
    if (done) return;
    const start = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 250);
    return () => clearInterval(id);
  }, [done]);

  useEffect(() => {
    if (done) setCollapsed(true);
  }, [done]);

  // Follow the newest step / source while research is active.
  useEffect(() => {
    if (collapsed || done) return;
    if (trailColRef.current) trailColRef.current.scrollTop = trailColRef.current.scrollHeight;
    if (sourcesColRef.current) sourcesColRef.current.scrollTop = sourcesColRef.current.scrollHeight;
  }, [steps.length, sources.length, collapsed, done]);

  useLayoutEffect(() => {
    const measure = () => {
      const h = headRef.current?.offsetHeight ?? 0;
      const body = Math.max(
        trailColRef.current?.scrollHeight ?? 0,
        sourcesColRef.current?.scrollHeight ?? 0,
      );
      setHeight(collapsed ? h : Math.min(h + body, maxH));
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (headRef.current) ro.observe(headRef.current);
    if (trailColRef.current) ro.observe(trailColRef.current);
    if (sourcesColRef.current) ro.observe(sourcesColRef.current);
    return () => ro.disconnect();
  }, [collapsed, trail, maxH]);

  // Re-evaluate the "more below" fades whenever layout could have changed.
  useEffect(() => { checkMore(); }, [steps.length, sources.length, collapsed, done, height]);

  return (
    <div className={`rt${done ? " rt--done" : ""}${collapsed ? " rt--collapsed" : ""}`} style={{ height }}>
      <div
        className="rt__head"
        ref={headRef}
        onClick={done ? () => setCollapsed((c) => !c) : undefined}
        role={done ? "button" : undefined}
        tabIndex={done ? 0 : undefined}
        onKeyDown={done ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setCollapsed((c) => !c); } } : undefined}
        aria-expanded={done ? !collapsed : undefined}
      >
        <span className={`rt__pulse${done ? " rt__pulse--done" : ""}`} />
        <span className="rt__title">{title}</span>
        {!done && <span className="rt__time">{elapsed}s</span>}
        {done && <span className="rt__chev">▾</span>}
      </div>
      <div className="rt__body">
        <div className="rt__col rt__col--trail">
          <div className="rt__trail" ref={trailColRef} onScroll={checkMore}>
            <div className="rt__col-label">Thinking</div>
            {steps.map((s) => (
              <div key={s.id} className={`rt-step rt-step--${s.kind} rt-step--${s.state}`}>
                <div className="rt-step__rail">
                  <div className="rt-step__node" />
                  <div className="rt-step__line" />
                </div>
                <div className="rt-step__txt">
                  <div className="rt-step__main">{s.label}</div>
                  {s.detail && <div className="rt-step__detail">{s.detail}</div>}
                </div>
              </div>
            ))}
          </div>
          {!collapsed && trailMore && <div className="rt__fade" />}
        </div>
        <div className="rt__col rt__col--sources">
          <div className="rt__sources" ref={sourcesColRef} onScroll={checkMore}>
            <div className="rt__col-label">Sources{sources.length ? ` · ${sources.length}` : ""}</div>
            <div className="rt__src-grid">
              {sources.slice(0, 18).map((s) => (
                <a
                  key={s.id}
                  href={hrefFor(s.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`rt-src rt-src--${s.state}`}
                >
                  <div className="rt-src__tag">{s.tag}</div>
                  <div className="rt-src__main">
                    <div className="rt-src__title">{s.title}</div>
                    {s.meta && <div className="rt-src__meta">{s.meta}</div>}
                    {s.abstract && <div className="rt-src__abstract">{s.abstract}</div>}
                  </div>
                  <span className="rt-src__open">↗</span>
                </a>
              ))}
            </div>
          </div>
          {!collapsed && sourcesMore && <div className="rt__fade" />}
        </div>
      </div>
    </div>
  );
}
