// One set of panel controls for every panel (plan B1.4): Minimise, Full screen and Close at the top right of the
// header, in Octet's own style on every platform (no coloured dots). A panel shows only the controls that apply. Also
// the pill a minimised spectrum or Mass spec panel becomes, beside its structure, and the motion between the two.
import { useLayoutEffect, useRef } from "react";
import { ArrowsIn, ArrowsOut, ChartLine, Minus, X } from "@phosphor-icons/react";
import type { Store } from "./store";
import { reduced, timing } from "./motion";

type Controls = { minimise?: (keyboard: boolean) => void; full?: { on: boolean; toggle: () => void }; close?: () => void };

export function PanelControls({ minimise, full, close }: Controls) {
  return (
    <span className="panel-controls">
      {minimise && <button className="actions-close" onClick={(e) => minimise(e.detail === 0)} aria-label="Minimise" data-tip="Minimise"><Minus size={12} /></button>}
      {full && <button className="actions-close" onClick={full.toggle} aria-label={full.on ? "Leave full screen" : "Full screen"} data-tip={full.on ? "Leave full screen" : "Full screen"}>{full.on ? <ArrowsIn size={12} /> : <ArrowsOut size={12} />}</button>}
      {close && <button className="actions-close" onClick={() => close()} aria-label="Close" data-tip="Close"><X size={12} /></button>}
    </span>
  );
}

// The X that closes a pill or a spectrum tab: one button with one look (editor.css .close-x). It is out of the tab
// order: Delete or Backspace on the pill or the tab does the same.
export function CloseX({ name, onClose }: { name: string; onClose: () => void }) {
  return <button type="button" className="close-x" tabIndex={-1} aria-label={`Close ${name}`} data-tip="Close" onClick={() => onClose()}><X size={12} /></button>;
}

// A pill: a minimised panel, beside its structure. box: the structure's box (drawing units, y up). Its X closes the
// panel; Delete or Backspace on it does the same.
export type Pill = { key: string; short: string; count?: number; name: string; box?: [number, number, number, number]; onRestore: (keyboard: boolean) => void; onClose: () => void; onPoint: (on: boolean) => void };

// Each pill sits 8 px right of its structure, level with its top; pills on one structure go one under another. A pill
// with no structure (a measured spectrum on its own) sits at the bottom left of the canvas.
export function Pills({ pills, views, scale }: { pills: Pill[]; views: Store<{ x: number; y: number; zoom: number }>; scale: number }) {
  const layer = useRef<HTMLDivElement>(null);
  // Each pill's place from the view, set straight on it (no React render as the view moves). A structure off screen
  // keeps its pill in view, at the nearest edge of the canvas (above the strip: --dock).
  const place = useRef(() => {});
  place.current = () => {
    const v = views.get(), el = layer.current;
    if (!el) return;
    const room = el.getBoundingClientRect(), dock = parseFloat(getComputedStyle(el).getPropertyValue("--dock")) || 0;
    for (const pill of el.querySelectorAll<HTMLElement>(".pill:not(.docked)")) {
      const x = v.x + Number(pill.dataset.x) * v.zoom + 8, y = v.y + Number(pill.dataset.y) * v.zoom + Number(pill.dataset.row) * 28;
      pill.style.left = `${Math.max(72, Math.min(room.width - pill.offsetWidth - 16, x))}px`;
      pill.style.top = `${Math.max(16, Math.min(room.height - dock - 40, y))}px`;
    }
  };
  useLayoutEffect(() => place.current());
  useLayoutEffect(() => views.subscribe(() => place.current()), [views]);
  const row = new Map<string, number>();
  const one = (p: Pill) => {
    const at = p.box ? `${p.box[2]},${p.box[3]}` : "", n = row.get(at) ?? 0;
    row.set(at, n + 1);
    return (
      <span key={p.key} className={p.box ? "pill" : "pill docked"} data-pill={p.key} data-x={p.box ? p.box[2] * scale : undefined} data-y={p.box ? -p.box[3] * scale : undefined} data-row={n}
        style={{ "--row": n } as React.CSSProperties}
        onPointerDown={(e) => e.stopPropagation()} onPointerEnter={() => p.onPoint(true)} onPointerLeave={() => p.onPoint(false)}>
        <button className="pill-open" aria-label={p.name} data-tip="Show" onClick={(e) => p.onRestore(e.detail === 0)}
          onKeyDown={(e) => { if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); e.stopPropagation(); p.onClose(); } }}>
          <ChartLine size={16} aria-hidden />{p.short}{p.count && <span className="pill-count" aria-hidden>{p.count}</span>}
        </button>
        <CloseX name={p.name} onClose={p.onClose} />
      </span>
    );
  };
  return (
    <div ref={layer} className="pills">
      {pills.map(one)}
    </div>
  );
}

// The motion between a panel and its pill (B1.17): the panel clips down to the pill's box (minimise) or opens out of it
// (restore), its content fading from 40%. Reduced motion: opacity only. Keyboard actions: none. done runs at the end.
export function fold(panel: HTMLElement | null, pill: DOMRect | undefined, way: "in" | "out", keyboard: boolean, done?: () => void) {
  if (!panel || keyboard) return done?.();
  const r = panel.getBoundingClientRect(), radius = getComputedStyle(panel).borderTopLeftRadius;
  const to = pill && r.width ? `inset(${pill.top - r.top}px ${r.right - pill.right}px ${r.bottom - pill.bottom}px ${pill.left - r.left}px round 12px)` : "inset(40% 40% 40% 40% round 12px)";
  const open = `inset(0px 0px 0px 0px round ${radius})`;
  const frames = reduced() ? [{ opacity: 1 }, { opacity: 0 }] : [{ clipPath: open, opacity: 1 }, { clipPath: to, opacity: 0.4 }];
  const time = timing(way === "in" ? "--motion" : "--motion-slow"), motion = panel.animate(way === "in" ? frames : [...frames].reverse(), { ...time, fill: way === "in" ? "forwards" : "none" });
  // A window in the background may hold its animations, so the end comes on time either way.
  let ended = false;
  const end = () => { if (ended) return; ended = true; done?.(); if (way === "in") setTimeout(() => motion.cancel(), 50); };
  motion.onfinish = end;
  setTimeout(end, time.duration + 50);
}

// The strip's top edge (B1.3): a drag sets its height, ↑ and ↓ by 16 px (with Shift by 64), Home and End go to the
// limits, and a double-click goes back to the default. A drag let go more than 48 px under the least height minimises
// the panel.
export type Sizing = { height: number; min: number; max: number; onHeight: (h: number) => void; onReset: () => void };
export function ResizeEdge({ sizing, onMinimise }: { sizing: Sizing; onMinimise: (keyboard: boolean) => void }) {
  const { height, min, max, onHeight, onReset } = sizing, clamp = (h: number) => Math.round(Math.min(max, Math.max(min, h)));
  return (
    <div className="resize-edge" role="separator" aria-orientation="horizontal" aria-label="Height" tabIndex={0}
      aria-valuenow={Math.round(height)} aria-valuemin={min} aria-valuemax={max}
      onPointerDown={(e) => {
        if (e.button !== 0) return;
        e.preventDefault();
        e.stopPropagation();
        const el = e.currentTarget, y0 = e.clientY, h0 = height;
        el.setPointerCapture(e.pointerId);
        const move = (m: PointerEvent) => onHeight(clamp(h0 + y0 - m.clientY));
        const up = (u: PointerEvent) => {
          el.removeEventListener("pointermove", move);
          el.removeEventListener("pointerup", up);
          if (h0 + y0 - u.clientY < min - 48) onMinimise(false);
        };
        el.addEventListener("pointermove", move);
        el.addEventListener("pointerup", up);
      }}
      onKeyDown={(e) => {
        const step = e.shiftKey ? 64 : 16, next = { ArrowUp: height + step, ArrowDown: height - step, Home: min, End: max }[e.key];
        if (next === undefined) return;
        e.preventDefault();
        onHeight(clamp(next));
      }}
      onDoubleClick={onReset} />
  );
}
