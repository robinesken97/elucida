// A predicted spectrum as the Spectrum panel draws it, and as a figure for the page (Add to drawing): the lines of each
// ¹H multiplet, the solvent's peaks, the axis ticks and the peak labels. The figure is in bond lengths, y up, with the
// axis along y = 0 from x = 0 (the high-shift end) to its width.
import { multiplicity, type Nucleus, type Prediction, type Signal } from "./nmr.ts";

export const SOLVENTS = ["CDCl₃", "DMSO-d₆", "CD₃OD", "D₂O", "C₆D₆", "Acetone-d₆", "CD₃CN"];

// Residual solvent and water peaks (Fulmer et al., Organometallics 2010, 29, 2176): each peak's shift with the number
// of deuteriums the nucleus couples to and J to deuterium (Hz). CHD₂ residual protons are quintets; CDCl₃ is a 1:1:1
// triplet in ¹³C and CD₃ a septet.
const SOLVENT_PEAKS: Record<string, { h: [number, number, number][]; water?: number; c: [number, number, number][] }> = {
  "CDCl₃": { h: [[7.26, 0, 0]], water: 1.56, c: [[77.16, 1, 32]] },
  "DMSO-d₆": { h: [[2.5, 2, 1.9]], water: 3.33, c: [[39.52, 3, 21]] },
  "CD₃OD": { h: [[3.31, 2, 1.7]], water: 4.87, c: [[49.0, 3, 21.4]] },
  "D₂O": { h: [[4.79, 0, 0]], c: [] },
  "C₆D₆": { h: [[7.16, 0, 0]], water: 0.4, c: [[128.06, 1, 24]] },
  "Acetone-d₆": { h: [[2.05, 2, 2.2]], water: 2.84, c: [[29.84, 3, 19.4], [206.26, 0, 0]] },
  "CD₃CN": { h: [[1.94, 2, 2.5]], water: 2.13, c: [[1.32, 3, 21], [118.26, 0, 0]] },
};
// A peak split by n deuteriums (spin 1): 2n + 1 lines, heights from repeated 1:1:1, adding up to `total`.
function deuterated(ppm: number, n: number, j: number, mhz: number, total: number) {
  let row = [1];
  for (let k = 0; k < n; k++) row = Array.from({ length: row.length + 2 }, (_, i) => (row[i - 2] ?? 0) + (row[i - 1] ?? 0) + (row[i] ?? 0));
  const sum = row.reduce((a, b) => a + b, 0);
  return row.map((h, i) => ({ ppm: ppm + ((i - n) * j) / mhz, h: (h / sum) * total }));
}
export type SolventPeak = { name: string; ppm: number; lines: { ppm: number; h: number }[]; broad: boolean };
// The solvent's own peaks: the residual peak (and water) in ¹H, the deuterated carbons in ¹³C. mhz: the ¹H frequency.
export function solventPeaks(solvent: string, nucleus: Nucleus, mhz: number): SolventPeak[] {
  const s = SOLVENT_PEAKS[solvent];
  if (!s) return [];
  const f = nucleus === "1H" ? mhz : mhz * 0.25145;
  return nucleus === "1H"
    ? [...s.h.map(([ppm, n, j]) => ({ name: solvent, ppm, lines: deuterated(ppm, n, j, f, 1), broad: false })), ...(s.water !== undefined ? [{ name: "H₂O", ppm: s.water, lines: deuterated(s.water, 0, 0, f, 0.8), broad: true }] : [])]
    : s.c.map(([ppm, n, j]) => ({ name: solvent, ppm, lines: deuterated(ppm, n, j, f, 1.5), broad: false }));
}

const binomial = (n: number) => { const row = [1]; for (let k = 1; k <= n; k++) row.push((row[k - 1] * (n - k + 1)) / k); return row; };
// A ¹H signal's lines: first-order splitting by each coupling (n + 1 lines with binomial heights, J apart), the
// heights adding up to the signal's number of hydrogens.
export function lines(s: Signal, mhz: number): { ppm: number; h: number }[] {
  let out = [{ ppm: s.shift, h: s.nuclei }];
  for (const c of s.couplings) {
    const w = binomial(c.n), step = c.j / mhz, total = 2 ** c.n;
    out = out.flatMap((l) => w.map((k, i) => ({ ppm: l.ppm + (i - c.n / 2) * step, h: (l.h * k) / total })));
  }
  return out;
}
// The shift range to show all of a spectrum: 0 to 10 ppm for ¹H and 0 to 200 for ¹³C, wider if a shift is outside.
export function fullRange(p: Prediction | undefined, nucleus: Nucleus): [number, number] {
  const shifts = p?.signals.map((s) => s.shift) ?? [], [lo, hi] = nucleus === "1H" ? [0, 10] : [0, 200], pad = nucleus === "1H" ? 0.5 : 10;
  return [Math.min(lo, ...shifts.map((x) => x - pad)), Math.max(hi, ...shifts.map((x) => x + pad))];
}
// Axis ticks: the first step that gives at most one label per `room` (64 px in the panel), up to an IR range's.
export function ticks(lo: number, hi: number, width: number, room = 64) {
  const step = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000].find((s) => (hi - lo) / s <= width / room) ?? 10000;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(Math.round(v / step) * step);
  return { out, places: step < 0.1 ? 2 : step < 1 ? 1 : 0 };
}
// Labels at least `gap` apart and inside the plot, each as near its peak as it can be: pushed right past the one
// before, pulled back left from the right end, then each group of crowded labels centred on its peaks.
export function spread(xs: number[], gap: number, width: number): number[] {
  const order = xs.map((x, i) => ({ x, i })).sort((a, b) => a.x - b.x), at = order.map((o) => o.x), n = at.length;
  for (let k = 0; k < n; k++) at[k] = Math.max(at[k], k ? at[k - 1] + gap : gap / 2);
  for (let k = n - 1; k >= 0; k--) at[k] = Math.min(at[k], k < n - 1 ? at[k + 1] - gap : width - gap / 2);
  for (let k = 0; k < n; k++) at[k] = Math.max(at[k], k ? at[k - 1] + gap : gap / 2);
  const out = xs.slice();
  order.forEach((o, k) => { out[o.i] = at[k]; });
  return out;
}
// A measured trace as a plot draws it, `width` pixels wide: each point as [pixel, value] when the points are further
// apart than half a pixel; otherwise, for each pixel, the lowest and highest of the points in it (in the order they
// come), so no peak is lost between pixels. px: a point's pixel from its x. Points well outside the plot are left out.
export function traceColumns(s: { first: number; last: number; y: ArrayLike<number>; xs?: ArrayLike<number> }, px: (x: number) => number, width: number): [number, number][] {
  const n = s.y.length, xAt = (i: number) => (s.xs ? s.xs[i] : s.first + (i * (s.last - s.first)) / Math.max(1, n - 1));
  let i0 = 0, i1 = n - 1;
  if (!s.xs && n > 1) {
    // The pixel is a straight line in the point's index: the points from 2 px left of the plot to 2 px right of it.
    const a = px(xAt(0)), b = px(xAt(1)) - a, at = (p: number) => (b ? (p - a) / b : 0);
    i0 = Math.max(0, Math.floor(Math.min(at(-2), at(width + 2))));
    i1 = Math.min(n - 1, Math.ceil(Math.max(at(-2), at(width + 2))));
  }
  const out: [number, number][] = [];
  if (i1 - i0 <= 2 * width) {
    for (let i = i0; i <= i1; i++) { const p = px(xAt(i)); if (p >= -2 && p <= width + 2) out.push([p, s.y[i]]); }
    return out;
  }
  let col = NaN, lo = 0, hi = 0, loAt = 0, hiAt = 0;
  const flush = () => { if (!Number.isNaN(col)) out.push(...((loAt <= hiAt ? [[col, lo], [col, hi]] : [[col, hi], [col, lo]]) as [number, number][])); };
  for (let i = i0; i <= i1; i++) {
    const p = Math.round(px(xAt(i))), v = s.y[i];
    if (p < -2 || p > width + 2) continue;
    if (p !== col) { flush(); col = p; lo = hi = v; loAt = hiAt = i; continue; }
    if (v < lo) { lo = v; loAt = i; }
    if (v > hi) { hi = v; hiAt = i; }
  }
  flush();
  return out;
}

// Lorentzian lines summed at each of `xs` (ppm): each line's height times its half width squared over the distance
// squared plus the half width squared.
export const lorentz = (xs: number[], ls: { ppm: number; h: number; w: number }[]) => xs.map((v) => ls.reduce((sum, l) => sum + (l.h * l.w * l.w) / ((v - l.ppm) ** 2 + l.w * l.w), 0));

type P = [number, number];
// The figure: lines (the axis, ticks, ¹³C sticks and label leaders), curves (the ¹H trace) and texts, each text at its
// baseline. grey: the solvent's. size: a text's size against the figure's label size (1).
export type Figure = {
  lines: { from: P; to: P; colour?: string; grey?: true }[];
  curves: { points: P[]; grey?: true }[];
  texts: { text: string; at: P; align: "left" | "centre" | "right"; size: number; colour?: string; grey?: true }[];
};
// The spectrum as the panel shows it (the shifts from `range`, solvent peaks if asked), `width` long and its tallest
// peak `height` high, as a figure. em: the labels' size in bond lengths, to space them.
export function spectrumFigure(o: {
  prediction: Prediction; nucleus: Nucleus; mhz: number; solvent: string; solventPeaks: boolean; range: [number, number];
  colours: (string | undefined)[]; width: number; height: number; em: number;
}): Figure {
  const { prediction: p, nucleus, mhz, width: W, height: H, em } = o, [lo, hi] = o.range, h1 = nucleus === "1H";
  const x = (ppm: number) => ((hi - ppm) / (hi - lo)) * W, N = 600, xs = Array.from({ length: N + 1 }, (_, i) => hi - ((hi - lo) * i) / N);
  const least = (0.75 * (hi - lo)) / N, shown = (ppm: number) => ppm >= lo && ppm <= hi;
  const out: Figure = { lines: [], curves: [], texts: [] };
  const split = p.signals.map((s) => (h1 ? lines(s, mhz) : [{ ppm: s.shift, h: s.nuclei }]));
  const solvent = o.solventPeaks ? solventPeaks(o.solvent, nucleus, mhz) : [];
  const trace = h1 ? lorentz(xs, p.signals.flatMap((s, k) => split[k].map((l) => ({ ...l, w: Math.max((s.broad ? 12 : 0.6) / mhz, least) })))) : undefined;
  const solventTrace = h1 && solvent.length ? lorentz(xs, solvent.flatMap((s) => s.lines.map((l) => ({ ...l, w: Math.max((s.broad ? 6 : 0.6) / mhz, least) })))) : undefined;
  const top = h1 ? Math.max(1e-9, ...(trace ?? [0]), ...(solventTrace ?? [0])) : Math.max(1, ...p.signals.map((s) => s.nuclei), ...solvent.flatMap((s) => s.lines.map((l) => l.h)));
  const y = (v: number) => (v / top) * H;
  // The value at a shift on a trace (the nearest sample).
  const at = (t: number[] | undefined, ppm: number) => t?.[Math.max(0, Math.min(N, Math.round(((hi - ppm) / (hi - lo)) * N)))] ?? 0;
  const tip = (k: number) => (h1 ? Math.max(...split[k].map((l) => at(trace, l.ppm))) : p.signals[k].nuclei);

  // The axis, its ticks and their shifts, and ppm under its low end.
  out.lines.push({ from: [0, 0], to: [W, 0] });
  const { out: tickAt, places } = ticks(lo, hi, W, 4 * em);
  for (const v of tickAt) {
    out.lines.push({ from: [x(v), 0], to: [x(v), -0.15] });
    out.texts.push({ text: v.toFixed(places), at: [x(v), -0.15 - 0.85 * em], align: "centre", size: 0.9 });
  }
  out.texts.push({ text: "ppm", at: [W, -0.15 - 1.9 * em], align: "right", size: 0.9 });
  // The traces: ¹H as one curve, the solvent's in grey; ¹³C as sticks.
  if (solventTrace) out.curves.push({ points: solventTrace.map((v, i): P => [(W * i) / N, y(v)]), grey: true });
  if (trace) out.curves.push({ points: trace.map((v, i): P => [(W * i) / N, y(v)]) });
  if (!h1) {
    for (const s of solvent) for (const l of s.lines) if (shown(l.ppm)) out.lines.push({ from: [x(l.ppm), 0], to: [x(l.ppm), y(l.h)], grey: true });
    p.signals.forEach((s, k) => { if (shown(s.shift)) out.lines.push({ from: [x(s.shift), 0], to: [x(s.shift), y(s.nuclei)], colour: o.colours[k] }); });
  }
  for (const s of solvent) {
    if (!shown(s.ppm)) continue;
    const peak = h1 ? Math.max(at(solventTrace, s.ppm), at(trace, s.ppm)) : Math.max(...s.lines.map((l) => l.h));
    out.texts.push({ text: s.name, at: [x(s.ppm), y(peak) + 0.2], align: "centre", size: 0.8, grey: true });
  }
  // Each peak's label above the tallest peak, spread so none overlap: the shift, and for ¹H the multiplicity and the
  // number of hydrogens under it. A leader joins each label to its peak.
  const ks = p.signals.map((s, k) => (shown(s.shift) ? k : -1)).filter((k) => k >= 0);
  const label = (s: Signal) => (h1 ? `${multiplicity(s)}, ${s.nuclei}H` : s.nuclei > 1 ? `${s.nuclei}C` : "");
  const gap = em * 0.6 * Math.max(4, ...ks.map((k) => label(p.signals[k]).length * 0.8)) + 0.2;
  const placed = spread(ks.map((k) => x(p.signals[k].shift)), gap, W), base = H + 0.45;
  ks.forEach((k, i) => {
    const s = p.signals[k], lx = placed[i], c = o.colours[k], second = label(s);
    out.lines.push({ from: [lx, base], to: [lx, base - 0.12], colour: c });
    out.lines.push({ from: [lx, base - 0.12], to: [x(s.shift), Math.max(y(tip(k)) + 0.08, Math.min(base - 0.3, y(tip(k)) + 0.4))], colour: c });
    if (second) out.texts.push({ text: second, at: [lx, base + 0.3 * em], align: "centre", size: 0.8, colour: c });
    out.texts.push({ text: s.shift.toFixed(h1 ? 2 : 1), at: [lx, base + (second ? 1.25 : 0.3) * em], align: "centre", size: 1, colour: c });
  });
  return out;
}
