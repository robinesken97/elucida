// Run: node src/spectrumplot.check.ts. Fails loudly if the spectrum figure (Add to drawing > Spectrum) goes wrong, or
// if the page and the Spectrum panel stop drawing the same lines (one line engine, one sampler).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { hydrogens, placeCaptions, type Arrow, type CurvePoint, type Mol } from "./render.ts";
import { predict, readTables, type Prediction } from "./nmr.ts";
import type { Graph } from "./naming.ts";
import { parse, serialize } from "./file.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE, PRESETS } from "./docstyle.ts";
import { readOct, writeOct } from "./oct.ts";
import { addTitle, columnsOf, fitCurve, GREY, NOTICE, placeFigure, withNotice, fullRange, inkOf, labelRow, layoutLabels, lines, peakIn, piecesOf, sample, solventPeaks, spectrumFigure, spectrumLines, ticks, tint, type Figure, type LabelPeak, type Line } from "./spectrumplot.ts";
import { msFigure, type IonOf } from "./msanalysis.ts";
import { widthOf } from "./arial.ts";

// Ethyl acetate's ¹H prediction, roughly: a quartet, a singlet and a triplet.
const h1: Prediction = { nucleus: "1H", signals: [
  { atoms: [1], shift: 4.12, nuclei: 2, couplings: [{ j: 7, n: 3 }], sd: 0.05, based: 20, level: 5 },
  { atoms: [3], shift: 2.05, nuclei: 3, couplings: [], sd: 0.03, based: 40, level: 6 },
  { atoms: [0], shift: 1.26, nuclei: 3, couplings: [{ j: 7, n: 2 }], sd: 0.04, based: 30, level: 5 },
] };
const fig = spectrumFigure({ prediction: h1, nucleus: "1H", mhz: 400, solvent: "CDCl₃", solventPeaks: true, range: fullRange(h1, "1H"), colours: [undefined, "#2F6FED", undefined], width: 14, height: 3.5, em: 0.55 });
// The axis first, along y = 0 for the whole width.
assert.deepEqual(fig.lines[0], { from: [0, 0], to: [14, 0], role: "axis" });
// One trace for the compound, one grey for the solvent, and the coloured singlet's fill (a closed curve in its tint);
// every point inside the box, the tallest at the top.
const traces = fig.curves.filter((c) => !c.fill), fills = fig.curves.filter((c) => c.fill);
assert.equal(traces.filter((c) => !c.grey).length, 1);
assert.equal(traces.filter((c) => c.grey).length, 1);
assert.deepEqual(fills.map((c) => c.fill), [tint("#2F6FED")]);
assert.equal(tint("#2F6FED"), "#B6CDF9");
const anchors = (c: Figure["curves"][number]) => c.points.map((q) => q.at);
assert.ok(fig.curves.every((c) => anchors(c).every(([x, y]) => x >= -1e-9 && x <= 14 + 1e-9 && y >= -1e-9 && y <= 3.5 + 1e-9)));
assert.ok(Math.abs(Math.max(...fig.curves.flatMap((c) => anchors(c).map((q) => q[1]))) - 3.5) < 1e-9);
// High shifts on the left: the quartet's label is left of the triplet's.
const label = (t: string) => fig.texts.find((x) => x.text === t)!;
assert.ok(label("4.12").at[0] < label("1.26").at[0]);
assert.equal(label("q, 2H").at[0], label("4.12").at[0]);
// A coloured peak keeps its colour in its label; the solvent is named in grey; ppm sits at the right end.
assert.equal(label("2.05").colour, "#2F6FED");
assert.equal(label("CDCl₃").grey, true);
assert.equal(label("ppm").align, "right");
// Labels clear of each other, and above the tallest peak.
const shifts = ["4.12", "2.05", "1.26"].map(label);
assert.ok(shifts.every((t) => t.at[1] > 3.5));
// Ticks every whole ppm from 0 to 10 (none outside the range).
const tickTexts = fig.texts.filter((t) => t.role?.startsWith("tick:")).map((t) => Number(t.text));
assert.ok(tickTexts.length >= 5 && tickTexts.every((v) => v >= 0 && v <= 10.5));

// ¹³C: sticks, no curve; a narrowed range leaves out the peaks outside it.
const c13: Prediction = { nucleus: "13C", signals: [{ atoms: [2], shift: 171, nuclei: 1, couplings: [], sd: 1, based: 9, level: 4 }, { atoms: [0], shift: 14.2, nuclei: 1, couplings: [], sd: 1, based: 9, level: 4 }] };
const narrow = spectrumFigure({ prediction: c13, nucleus: "13C", mhz: 400, solvent: "CDCl₃", solventPeaks: false, range: [0, 100], colours: [], width: 10, height: 3, em: 0.5 });
assert.equal(narrow.curves.length, 0);
assert.ok(narrow.texts.some((t) => t.text === "14.2") && !narrow.texts.some((t) => t.text === "171.0"));
assert.equal(narrow.lines.filter((l) => l.from[1] === 0 && l.to[1] === 3).length, 1);

// The panel's helpers: a triplet's lines, the solvent's quintet, ticks and the label layout.
assert.deepEqual(lines(h1.signals[2], 400).map((l) => l.h), [0.75, 1.5, 0.75]);
assert.equal(solventPeaks("DMSO-d₆", "1H", 400)[0].lines.length, 5);
assert.deepEqual(ticks(0, 10, 640).out, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
// An IR range (4000 to 400 cm⁻¹) on a 480 px panel: 500 apart.
assert.deepEqual(ticks(400, 4000, 480).out, [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]);
assert.deepEqual(layoutLabels([10, 10, 10], [4, 4, 4], 0, 100), [6, 10, 14]);
assert.deepEqual(layoutLabels([98, 99], [4, 4], 0, 100), [94, 98]);

// --- One line engine: the page keeps the splitting -------------------------------------------------------------

// The sampler: an even grid no further apart than half the narrowest half width, with each line's centre a point.
const ls = spectrumLines(h1.signals, "1H", 400);
assert.equal(ls.length, 4 + 1 + 3);
assert.ok(ls.every((l) => l.signal >= 0 && Math.abs(l.w - 0.6 / 400) < 1e-12));
const t0 = sample(ls, 0, 10);
assert.ok(ls.every((l) => t0.x.some((x, i) => x === l.ppm && t0.apex![i])));
assert.ok(t0.x.every((x, i) => !i || (x > t0.x[i - 1] && x - t0.x[i - 1] <= 0.3 / 400 + 1e-12)));
assert.ok(Math.abs(peakIn(t0) - 3) < 1e-3); // the singlet's top
// A curve longer than 1000 points is cut at its lowest point, the two pieces sharing it.
const long: CurvePoint[] = Array.from({ length: 2500 }, (_, i) => ({ at: [i, i === 800 || i === 1700 ? -1 : 1] }));
const cut = piecesOf(long);
assert.deepEqual(cut.map((c) => c.length), [801, 901, 800]);
assert.deepEqual([cut[0][800].at, cut[1][0].at, cut[1][900].at, cut[2][0].at], [[800, -1], [800, -1], [1700, -1], [1700, -1]]);
// Without slopes (a measured trace) the curve's points are corners on the points given.
const corners = fitCurve({ x: Float64Array.from([0, 1, 2, 3, 4]), y: Float64Array.from([0, 0, 1, 0, 0]) }, 0.01);
assert.deepEqual(corners, [{ at: [0, 0] }, { at: [1, 0] }, { at: [2, 1] }, { at: [3, 0] }, { at: [4, 0] }]);
// A noisy trace: every point within tol of the straight lines between the corners kept, which are points of it.
let noise = 3;
const jitter = () => { noise = (noise * 1103515245 + 12345) & 0x7fffffff; return noise / 0x7fffffff - 0.5; };
const nx = Float64Array.from({ length: 4000 }, (_, i) => i / 100), ny = nx.map((v) => Math.sin(v) + 1 / (1 + (v - 20) ** 2 * 400) + 0.02 * jitter());
const kept = fitCurve({ x: nx, y: ny }, 0.03);
assert.ok(kept.length < 1000 && kept.every((q) => nx.some((v, i) => v === q.at[0] && ny[i] === q.at[1])));
for (let i = 0, k = 0; i < nx.length; i++) {
  while (kept[k + 1].at[0] < nx[i]) k++;
  const [a, b] = [kept[k].at, kept[k + 1].at];
  assert.ok(Math.abs(a[1] + ((nx[i] - a[0]) / (b[0] - a[0])) * (b[1] - a[1]) - ny[i]) <= 0.03 + 1e-12);
}

// Octane-3,5-dione (CCCC(=O)CC(=O)CC): two triplets, a quartet, a sextet and two singlets in ¹H.
readTables(gunzipSync(readFileSync(new URL("../data/nmr/shifts.bin.gz", import.meta.url))));
function graph(els: string[], bonds: [number, number, number][]): Graph {
  const used = els.map(() => 0);
  for (const [a, b, o] of bonds) { used[a] += o; used[b] += o; }
  return { atoms: els.map((el, i) => ({ el, charge: 0, h: hydrogens(el, 0, used[i]) })), bonds: bonds.map(([a, b, order]) => ({ a, b, order: order as 1 | 2 | 3 })) };
}
const dione = predict(graph(["C", "C", "C", "C", "O", "C", "C", "O", "C", "C"], [[0, 1, 1], [1, 2, 1], [2, 3, 1], [3, 4, 2], [3, 5, 1], [5, 6, 1], [6, 7, 2], [6, 8, 1], [8, 9, 1]]), "1H")!;
const ester = predict(graph(["C", "C", "O", "O", "C", "C"], [[0, 1, 1], [1, 2, 2], [1, 3, 1], [3, 4, 1], [4, 5, 1]]), "1H")!;

// A pen curve's ink, sampled so no two points are further apart than `dx` across: each cubic piece at enough steps.
function inked(points: CurvePoint[], dx: number, closed = false): [number, number][] {
  const out: [number, number][] = [points[0].at];
  const n = closed ? points.length : points.length - 1;
  for (let i = 0; i < n; i++) {
    const a = points[i], b = points[(i + 1) % points.length], p0 = a.at, p1 = a.c2 ?? a.at, p2 = b.c1 ?? b.at, p3 = b.at;
    const steps = Math.max(1, Math.ceil(Math.abs(p3[0] - p0[0]) / dx));
    for (let j = 1; j <= steps; j++) {
      const t = j / steps, u = 1 - t, k = [u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t];
      out.push([k[0] * p0[0] + k[1] * p1[0] + k[2] * p2[0] + k[3] * p3[0], k[0] * p0[1] + k[1] * p1[1] + k[2] * p2[1] + k[3] * p3[1]]);
    }
  }
  return out;
}
// The maxima of a trace (points in x order) that stand at least `rise` above the lowest point on each side before a
// higher one: the peaks a reader sees.
function maxima(pts: [number, number][], rise: number): number[] {
  const out: number[] = [];
  for (let i = 1; i < pts.length - 1; i++) {
    const v = pts[i][1];
    if (!(v >= pts[i - 1][1] && v > pts[i + 1][1])) continue;
    let left = v, right = v;
    for (let j = i - 1; j >= 0 && pts[j][1] <= v; j--) left = Math.min(left, pts[j][1]);
    for (let j = i + 1; j < pts.length && pts[j][1] <= v; j++) right = Math.min(right, pts[j][1]);
    if (v - Math.max(left, right) >= rise) out.push(pts[i][0]);
  }
  return out;
}
// The height of the pen curves at x, each cubic piece taken as running straight across in x (its handles a third of the
// way along, as the page's are).
function pageAt(curves: { points: CurvePoint[] }[]): (x: number) => number {
  type Q = [number, number];
  const pieces = curves.flatMap((c) => c.points.slice(1).map((b, i): Q[] => { const a = c.points[i]; return a.at[0] <= b.at[0] ? [a.at, a.c2 ?? a.at, b.c1 ?? b.at, b.at] : [b.at, b.c1 ?? b.at, a.c2 ?? a.at, a.at]; }))
    .filter((q) => q[3][0] > q[0][0]).sort((p, q) => p[0][0] - q[0][0]);
  return (x) => {
    let a = 0, b = pieces.length - 1;
    while (a < b) { const m = (a + b + 1) >> 1; if (pieces[m][0][0] <= x) a = m; else b = m - 1; }
    const [p0, p1, p2, p3] = pieces[a], t = Math.min(1, Math.max(0, (x - p0[0]) / (p3[0] - p0[0]))), u = 1 - t;
    return u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1];
  };
}
// Every line summed exactly at a shift.
const exact = (ls: Line[], ppm: number) => ls.reduce((s, l) => s + (l.h * l.w * l.w) / ((ppm - l.ppm) ** 2 + l.w * l.w), 0);
const PT = 1 / 14.4, W = 14, H = 3.5; // a point in bond lengths (ACS 1996); the figure's size

for (const [name, p, want] of [["ethyl acetate", ester, 4 + 1 + 3], ["octane-3,5-dione", dione, 1 + 4 + 3 + 6 + 3 + 3]] as const) {
  for (const mhz of [300, 400, 600]) {
    const range = fullRange(p, "1H"), [lo, hi] = range, f = spectrumFigure({ prediction: p, nucleus: "1H", mhz, solvent: "CDCl₃", solventPeaks: false, range, colours: [], width: W, height: H, em: 0.55 });
    const own = spectrumLines(p.signals, "1H", mhz), top = Math.max(...own.map((l) => exact(own, l.ppm)));
    const curves = f.curves.filter((c) => !c.grey && !c.fill);
    assert.ok(curves.every((c) => c.points.length <= 1000), `${name} at ${mhz} MHz: a curve over 1000 points`);
    // Each piece's handles are a third of the way to its neighbours, so a piece is the cubic between its ends.
    for (const c of curves) c.points.forEach((q, i) => { if (q.c2) assert.ok(Math.abs(q.c2[0] - (2 * q.at[0] + c.points[i + 1].at[0]) / 3) < 1e-9); });
    // The page curve, sampled every 0.01 pt, is within 0.5% of the tallest peak from the exact trace.
    const ink = curves.flatMap((c) => inked(c.points, 0.01 * PT)).sort((a, b) => a[0] - b[0]), ppmAt = (x: number) => hi - (x / W) * (hi - lo);
    const off = Math.max(...ink.map(([x, y]) => Math.abs(y / H - exact(own, ppmAt(x)) / top)));
    assert.ok(off <= 0.005, `${name} at ${mhz} MHz: ${(off * 100).toFixed(2)}% off`);
    // Every q, t and sextet shows its full count of maxima, as the exact trace does (one curve, sampled every 0.01 pt).
    const rise = 0.01 * H, truth = maxima(ink.map(([x]) => [x, (exact(own, ppmAt(x)) / top) * H] as [number, number]), rise), seen = maxima(ink, rise);
    assert.equal(truth.length, want, `${name} at ${mhz} MHz: the exact trace has ${truth.length} maxima`);
    assert.equal(seen.length, want, `${name} at ${mhz} MHz: the page curve has ${seen.length} maxima`);
    assert.ok(seen.every((x, i) => Math.abs(x - truth[i]) < 0.05 * PT));
    // The page curve is the panel's trace: at every point the panel samples (600 px wide), the same value.
    const panel = sample(own, lo, hi, (hi - lo) / 1200), onPage = pageAt(curves), worst = Math.max(...Array.from(panel.x, (v, i) => Math.abs(onPage(((hi - v) / (hi - lo)) * W) / H - panel.y[i] / top)));
    assert.ok(worst <= 0.005, `${name} at ${mhz} MHz: the page is ${(worst * 100).toFixed(2)}% off the panel`);
    assert.ok(columnsOf(panel, (v) => ((hi - v) / (hi - lo)) * 600, 600).length <= 1202);
    // The same counts after saving and opening, as .oct and as CDXML (points to 0.01 pt).
    if (mhz !== 400) continue;
    const arrows: Arrow[] = curves.map((c, i) => ({ id: i + 1, kind: "curve", from: c.points[0].at, to: c.points[c.points.length - 1].at, curve: { points: c.points } }));
    const mol: Mol = { atoms: [], bonds: [], arrows };
    const viaOct = parse(serialize(mol)), viaCdxml = fromCdxml(toCdxml(mol, DEFAULT_STYLE)).mol;
    for (const [how, back] of [["oct", viaOct], ["CDXML", viaCdxml]] as const) {
      const got = (back.arrows ?? []).filter((a) => a.kind === "curve"), y0 = Math.min(...got.flatMap((a) => a.curve!.points.map((q) => q.at[1])));
      assert.equal(got.length, curves.length, `${name}: ${how} kept ${got.length} curves`);
      const again = got.flatMap((a) => inked(a.curve!.points, 0.01 * PT)).map(([x, y]): [number, number] => [x, y - y0]).sort((a, b) => a[0] - b[0]);
      assert.equal(maxima(again, rise).length, want, `${name}: ${maxima(again, rise).length} maxima after ${how}`);
    }
  }
}

// A coloured signal's fill is one closed curve from that signal's lines alone, under the trace.
const coloured = spectrumFigure({ prediction: dione, nucleus: "1H", mhz: 400, solvent: "CDCl₃", solventPeaks: false, range: [0, 6], colours: dione.signals.map((s) => (s.shift > 2.4 && s.shift < 2.45 ? "#D2453B" : undefined)), width: W, height: H, em: 0.55 });
const fill = coloured.curves.filter((c) => c.fill);
assert.equal(fill.length, 1);
const quartet = inked(fill[0].points, 0.01 * PT).filter(([, y]) => y > 0.01 * H);
assert.equal(maxima(fill[0].points.length > 2 ? inked(fill[0].points.slice(1, -1), 0.01 * PT) : [], 0.01 * H).length, 4);
assert.ok(quartet.every(([x]) => Math.abs((6 - (x / W) * 6) - 2.42) < 0.05));
assert.ok(coloured.curves.indexOf(fill[0]) < coloured.curves.findIndex((c) => !c.fill && !c.grey));

// A large molecule (211 atoms, about 100 ¹H signals of up to 24 lines): every curve has at most 1000 points, and the
// panel's lines, grid and columns take under 5 ms.
let seed = 7;
const rand = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
const big: Prediction = { nucleus: "1H", signals: Array.from({ length: 100 }, (_, k) => ({
  atoms: [k], shift: 0.6 + 8.6 * rand(), nuclei: 1 + Math.floor(3 * rand()), sd: 0.1, based: 5, level: 3,
  couplings: Array.from({ length: Math.floor(4 * rand()) }, () => ({ j: 1.5 + 14 * rand(), n: 1 + Math.floor(2 * rand()) })), ...(k % 25 === 0 ? { broad: true } : {}),
})) };
const bigFig = spectrumFigure({ prediction: big, nucleus: "1H", mhz: 600, solvent: "CDCl₃", solventPeaks: true, range: fullRange(big, "1H"), colours: big.signals.map((_, k) => (k % 10 ? undefined : "#22775B")), width: W, height: H, em: 0.55 });
assert.ok(bigFig.curves.length > 2 && bigFig.curves.every((c) => c.points.length <= 1000), bigFig.curves.map((c) => c.points.length).join(" "));
// Its page curve is within 0.5% of the exact trace too: the tails the sampler leaves out add up to under 0.1%.
{
  const [lo, hi] = fullRange(big, "1H"), all = spectrumLines(big.signals, "1H", 600), top = Math.max(...all.map((l) => exact(all, l.ppm)));
  const plain = spectrumFigure({ prediction: big, nucleus: "1H", mhz: 600, solvent: "CDCl₃", solventPeaks: false, range: [lo, hi], colours: [], width: W, height: H, em: 0.55 });
  const onPage = pageAt(plain.curves), off = Math.max(...Array.from({ length: 20001 }, (_, i) => { const x = (W * i) / 20000; return Math.abs(onPage(x) / H - exact(all, hi - (x / W) * (hi - lo)) / top); }));
  assert.ok(off <= 0.005, `the large molecule's page curve is ${(off * 100).toFixed(2)}% off`);
}
const times: number[] = [];
for (let run = 0; run < 21; run++) {
  const t = performance.now(), [lo, hi] = fullRange(big, "1H");
  columnsOf(sample(spectrumLines(big.signals, "1H", 600).filter((l) => l.signal >= 0), lo, hi, (hi - lo) / 1200), (ppm) => ((hi - ppm) / (hi - lo)) * 600, 600);
  times.push(performance.now() - t);
}
times.sort((a, b) => a - b);
assert.ok(times[10] < 5, `the panel's trace took ${times[10].toFixed(1)} ms`);

// --- One label layout: leaders never cross ----------------------------------------------------------------------

type Q = [number, number];
// Whether two segments meet (cross, touch or overlap).
function meet(p1: Q, p2: Q, q1: Q, q2: Q): boolean {
  const cross = (o: Q, a: Q, b: Q) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const on = (o: Q, a: Q, b: Q) => Math.min(o[0], a[0]) - 1e-9 <= b[0] && b[0] <= Math.max(o[0], a[0]) + 1e-9 && Math.min(o[1], a[1]) - 1e-9 <= b[1] && b[1] <= Math.max(o[1], a[1]) + 1e-9;
  const d1 = cross(q1, q2, p1), d2 = cross(q1, q2, p2), d3 = cross(p1, p2, q1), d4 = cross(p1, p2, q2), z = 1e-12;
  if (((d1 > z && d2 < -z) || (d1 < -z && d2 > z)) && ((d3 > z && d4 < -z) || (d3 < -z && d4 > z))) return true;
  return (Math.abs(d1) <= z && on(q1, q2, p1)) || (Math.abs(d2) <= z && on(q1, q2, p2)) || (Math.abs(d3) <= z && on(p1, p2, q1)) || (Math.abs(d4) <= z && on(p1, p2, q2));
}
// Whether a segment meets a box [x0, y0, x1, y1].
const inBox = (p: Q, q: Q, b: number[]) => [p, q].some(([x, y]) => x > b[0] && x < b[2] && y > b[1] && y < b[3])
  || meet(p, q, [b[0], b[1]], [b[2], b[1]]) || meet(p, q, [b[2], b[1]], [b[2], b[3]]) || meet(p, q, [b[2], b[3]], [b[0], b[3]]) || meet(p, q, [b[0], b[3]], [b[0], b[1]]);
// The pairs of leader segments from different labels of a figure that meet: none, for every figure.
function crossings(f: Figure): number {
  const ls = f.lines.filter((l) => l.role?.startsWith("leader:"));
  let n = 0;
  for (let i = 0; i < ls.length; i++) for (let j = i + 1; j < ls.length; j++) if (ls[i].role !== ls[j].role && meet(ls[i].from, ls[i].to, ls[j].from, ls[j].to)) n++;
  return n;
}
// A figure's label texts as boxes, each with its peak's role (em: the label size in figure units; Arial widths, a
// turned text stood on end).
function textBoxes(f: Figure, em: number) {
  return f.texts.filter((t) => t.role?.startsWith("peak:") || t.role?.startsWith("solvent:")).map((t) => {
    const w = widthOf(t.text, em), [x, y] = t.at, role = t.role!.split("/")[0];
    if (t.angle) return { role, box: [x - 0.72 * em, y, x + 0.21 * em, y + w] };
    const x0 = t.align === "centre" ? x - w / 2 : t.align === "right" ? x - w : x;
    return { role, box: [x0, y - 0.21 * em, x0 + w, y + 0.72 * em] };
  });
}
const overlaps = (a: number[], b: number[]) => a[0] < b[2] - 1e-9 && b[0] < a[2] - 1e-9 && a[1] < b[3] - 1e-9 && b[1] < a[3] - 1e-9;
// Labels of different peaks that overlap.
function overlapping(f: Figure, em: number): number {
  const bs = textBoxes(f, em);
  let n = 0;
  for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) if (bs[i].role !== bs[j].role && overlaps(bs[i].box, bs[j].box)) n++;
  return n;
}

// More than the row holds: packed and centred on it.
assert.deepEqual(layoutLabels([0, 1, 2], [40, 40, 40], 0, 100), [10, 50, 90]);
assert.deepEqual(layoutLabels([50, 50, 50, 50], [40, 40, 40, 40], 0, 100), [-10, 30, 70, 110]);

// A seeded fuzz of 10,000 rows (¹H multiplets and ¹³C sticks, 1 to 40 peaks, 120 to 620 pt, labels across and turned):
// order kept, no overlap, inside the frame when they fit, and no leader meets another leader, a bracket it does not end
// on, any peak's ink or another label.
{
  let z = 11;
  const r = () => { z = (z * 1103515245 + 12345) & 0x7fffffff; return z / 0x7fffffff; };
  const stats = [0, 0, 0];
  for (let run = 0; run < 10000; run++) {
    const h1 = run % 2 === 0, turned = run % 4 >= 2, W = 120 + 500 * r(), H = 50, n = 1 + Math.floor(40 * r()), crowd = r() < 0.5;
    const centre = W * r();
    const peaks: (LabelPeak & { top: number })[] = Array.from({ length: n }, () => {
      const x = crowd ? Math.min(W, Math.max(0, centre + (r() - 0.5) * 30)) : W * r(), half = h1 ? 6 * r() * r() : 0;
      return { x, a: Math.max(0, x - half), b: Math.min(W, x + half), width: turned ? 13 : 14 + 30 * r(), top: H * (0.05 + 0.95 * r()), plain: r() < 0.1 };
    });
    const ink = (a: number, b: number) => Math.max(0, ...peaks.filter((p) => p.b >= a && p.a <= b).map((p) => p.top));
    const row = labelRow(peaks, { lo: 0, hi: W, ceiling: H, ink, pt: 1, gap: 2.5, band: 9, stub: 2.5 });
    const order = peaks.map((_, i) => i).sort((a, b) => peaks[a].x - peaks[b].x || a - b);
    for (let k = 1; k < n; k++) {
      const [u, v] = [order[k - 1], order[k]];
      assert.ok(row.at[v] - row.at[u] >= (peaks[u].width + peaks[v].width) / 2 - 1e-6, `run ${run}: labels ${u} and ${v} overlap or swap`);
    }
    if (peaks.reduce((w, p) => w + p.width, 0) <= W) assert.ok(peaks.every((p, i) => row.at[i] - p.width / 2 >= -1e-6 && row.at[i] + p.width / 2 <= W + 1e-6), `run ${run}: a label outside the frame`);
    const segs = row.leaders.flatMap((pts, i) => pts.slice(1).map((q, k) => ({ i, p: pts[k], q })));
    const labelBox = (i: number) => [row.at[i] - peaks[i].width / 2, row.base, row.at[i] + peaks[i].width / 2, row.base + 30];
    for (let u = 0; u < segs.length; u++) {
      const { i, p, q } = segs[u];
      for (let v = u + 1; v < segs.length; v++) if (segs[v].i !== i) assert.ok(!meet(p, q, segs[v].p, segs[v].q), `run ${run}: leaders ${i} and ${segs[v].i} meet`);
      for (const [j, pk] of peaks.entries()) assert.ok(!inBox(p, q, [pk.a, 0, pk.b, pk.top]), `run ${run}: leader ${i} runs through peak ${j}`);
      for (let j = 0; j < n; j++) if (j !== i) assert.ok(!inBox(p, q, labelBox(j)), `run ${run}: leader ${i} runs through label ${j}`);
      for (const b of row.brackets) if (!b.peaks.includes(i)) for (let k = 1; k < b.points.length; k++) assert.ok(!meet(p, q, b.points[k - 1], b.points[k]), `run ${run}: leader ${i} meets a bracket`);
    }
    stats[0] += row.brackets.length; stats[1] += row.leaders.filter((l) => l.length === 4).length; stats[2] += row.leaders.filter((l) => !l.length).length;
    for (const b of row.brackets) for (let k = 1; k < b.points.length; k++) for (const pk of peaks) assert.ok(!inBox(b.points[k - 1], b.points[k], [pk.a, 0, pk.b, pk.top]), `run ${run}: a bracket runs through a peak`);
  }
  // The runs had brackets, slanted leaders and names left without one.
  assert.ok(stats.every((v) => v > 1000), stats.join(" "));
}

// Octane-3,5-dione at 202 pt (14 bond lengths in ACS 1996), labels at 8 and 10 pt, with the solvent's peaks: no two
// leaders meet and no labels overlap. Its ¹³C 205.2 and 204.9 share one bracket.
const c13dione = predict(graph(["C", "C", "C", "C", "O", "C", "C", "O", "C", "C"], [[0, 1, 1], [1, 2, 1], [2, 3, 1], [3, 4, 2], [3, 5, 1], [5, 6, 1], [6, 7, 2], [6, 8, 1], [8, 9, 1]]), "13C")!;
const figOf = (p: Prediction, wPt: number, labelPt: number, more: Partial<Parameters<typeof spectrumFigure>[0]> = {}) =>
  spectrumFigure({ prediction: p, nucleus: p.nucleus, mhz: 400, solvent: "CDCl₃", solventPeaks: true, range: fullRange(p, p.nucleus), colours: [], width: wPt * PT, height: H, em: labelPt * PT, pt: PT, ...more });
for (const p of [dione, c13dione]) for (const size of [8, 10]) for (const labels of ["horizontal", "vertical", "auto"] as const) {
  const f = figOf(p, 202, size, { labels });
  assert.equal(crossings(f), 0, `${p.nucleus} ${size} pt ${labels}: leaders meet`);
  assert.equal(overlapping(f, size * PT), 0, `${p.nucleus} ${size} pt ${labels}: labels overlap`);
}
{
  const f = figOf(c13dione, 202, 10), k = [205.2, 204.9].map((v) => c13dione.signals.findIndex((s) => Math.abs(s.shift - v) < 0.05));
  assert.ok(k.every((i) => i >= 0));
  const brackets = [...new Set(f.lines.filter((l) => l.role?.startsWith("bracket:")).map((l) => l.role))];
  assert.deepEqual(brackets.filter((b) => b!.includes(`peak:${k[0]}`) || b!.includes(`peak:${k[1]}`)), [`bracket:peak:${k[0]},peak:${k[1]}`]);
  // Both leaders end on the bracket.
  const bracketY = f.lines.find((l) => l.role === brackets[0] && l.from[1] === l.to[1])!.from[1];
  for (const i of k) assert.ok(f.lines.some((l) => l.role === `leader:peak:${i}` && Math.abs(Math.min(l.from[1], l.to[1]) - bracketY) < 1e-9));
}
// CDCl₃ at 7.26 among 11 aromatic signals, at 202 pt: no labels overlap and no leaders meet, across or turned.
{
  const aromatic: Prediction = { nucleus: "1H", signals: Array.from({ length: 11 }, (_, k) => ({ atoms: [k], shift: 7.0 + 0.07 * k + (k === 4 ? 0.005 : 0), nuclei: 1, couplings: [{ j: 7.8, n: 1 }, { j: 1.4, n: 1 }], sd: 0.1, based: 9, level: 4 })) };
  for (const labels of ["horizontal", "vertical", "auto"] as const) {
    const f = figOf(aromatic, 202, 10, { labels });
    assert.ok(f.texts.some((t) => t.text === "CDCl₃" && t.grey));
    assert.equal(overlapping(f, 10 * PT), 0, `aromatic ${labels}: labels overlap`);
    assert.equal(crossings(f), 0, `aromatic ${labels}: leaders meet`);
  }
}
// The mass spectrum's figure uses the same layout: close ions share a bracket and no leaders meet.
{
  const ions = [100, 100.02, 101, 150, 151, 151.05, 152, 300].map((mz, k) => ({ ion: { mono: mz, top: mz, pattern: [{ mz, rel: 100 - 9 * k }, { mz: mz + 1, rel: 10 }] } as unknown as IonOf }));
  const f = msFigure({ ions, range: [90, 320], width: 14, height: H, em: 0.55, pt: PT });
  assert.equal(crossings(f), 0);
  assert.ok(f.lines.some((l) => l.role?.startsWith("bracket:")));
}
// 100 labels lay out in under 2 ms (the median of 1,000 runs).
{
  let z = 5;
  const r = () => { z = (z * 1103515245 + 12345) & 0x7fffffff; return z / 0x7fffffff; };
  const peaks = Array.from({ length: 100 }, () => { const x = 600 * r(); return { x, a: x - 2 * r(), b: x + 2 * r(), width: 14 + 20 * r() }; });
  const ink = inkOf(peaks.map((p) => [p.x, 40 * r()]));
  const times: number[] = [];
  for (let run = 0; run < 1000; run++) { const t = performance.now(); labelRow(peaks, { lo: 0, hi: 600, ceiling: 50, ink, pt: 1, gap: 2.5, band: 9, stub: 2.5 }); times.push(performance.now() - t); }
  times.sort((a, b) => a - b);
  assert.ok(times[500] < 2, `100 labels took ${times[500].toFixed(2)} ms`);
}

// --- Vertical label text ------------------------------------------------------------------------------------------

// Turned labels are one line in ACS order, read bottom to top (angle 90).
{
  const f = figOf(dione, 202, 10, { labels: "vertical" }), q = f.texts.find((t) => t.text.startsWith("2.42"))!;
  assert.equal(q.text, "2.42 (q, 2H)");
  assert.equal(q.angle, 90);
  assert.equal(q.align, "left");
}
// 10 signals within 0.3 ppm at 202 pt fit turned, and not across.
{
  const ten: Prediction = { nucleus: "1H", signals: Array.from({ length: 10 }, (_, k) => ({ atoms: [k], shift: 3.5 + (0.3 * k) / 9, nuclei: 1, couplings: [{ j: 7, n: 2 }], sd: 0.1, based: 9, level: 4 })) };
  const inside = (f: Figure) => textBoxes(f, 10 * PT).every(({ box }) => box[0] >= -1e-9 && box[2] <= 202 * PT + 1e-9);
  assert.ok(inside(figOf(ten, 202, 10, { labels: "vertical", solventPeaks: false })));
  assert.ok(!inside(figOf(ten, 202, 10, { labels: "horizontal", solventPeaks: false })));
  assert.ok(figOf(ten, 202, 10, { solventPeaks: false }).texts.some((t) => t.angle === 90));
}
// Auto: octane-3,5-dione ¹H turned at 202 pt, across at 504 pt (labels at 8 and 10 pt, with and without the solvent's
// peaks).
for (const size of [8, 10]) for (const solventPeaks of [true, false]) {
  assert.ok(figOf(dione, 202, size, { solventPeaks }).texts.filter((t) => t.role?.startsWith("peak:")).every((t) => t.angle === 90), `${size} pt at 202 pt`);
  assert.ok(figOf(dione, 504, size, { solventPeaks }).texts.filter((t) => t.role?.startsWith("peak:")).every((t) => !t.angle), `${size} pt at 504 pt`);
}
// A turned label keeps its angle through CDXML (RotationAngle).
{
  const t = figOf(dione, 202, 10, { labels: "vertical" }).texts.find((x) => x.angle)!;
  const back = fromCdxml(toCdxml({ atoms: [], bonds: [], captions: [{ id: 1, text: t.text, x: t.at[0], y: t.at[1], align: "left", angle: t.angle }] }, DEFAULT_STYLE)).mol;
  assert.equal(back.captions?.[0].angle, 90);
  assert.equal(back.captions?.[0].text, t.text);
}

// Add to drawing > Spectrum (Editor.tsx addSpectrum): octane-3,5-dione ¹H at 202 pt in ACS 1996, with its title and
// the notice, under a structure.
{
  const em = 10 * PT, fig = figOf(dione, 202, 10), title = "¹H NMR (400 MHz, CDCl₃), predicted";
  const top = addTitle(fig, { title, notice: true, width: 202 * PT, height: H, em });
  const [m, items] = placeFigure({ atoms: [{ label: "C", location: [7, 2, 0] }], bonds: [] }, fig, [0, -top]), caps = m.captions ?? [];
  // A5: no caption has a size or font of its own, so each draws in the document style: 10 pt in ACS 1996, and 7 pt
  // once the document is RSC.
  assert.ok(caps.length > 10 && caps.every((c) => c.size === undefined && c.font === undefined));
  for (const [preset, pt] of [["ACS Document 1996", 10], ["RSC", 7]] as const) {
    const placed = placeCaptions(m, { ink: [], scale: 1 }, () => 0, m.arrows, 1, PRESETS[preset].captionSize);
    assert.equal(placed.length, caps.length);
    assert.ok(placed.every((c) => c.size === pt), `${preset}: captions at ${[...new Set(placed.map((c) => c.size))].join(", ")} pt`);
  }
  assert.equal(caps.filter((c) => c.text === title).length, 1);
  // A6: the licence's own sentence, grey, wrapped to the figure's width, under the axis's unit.
  const licence = readFileSync(new URL("../data/nmr/LICENCE.txt", import.meta.url), "utf8").replace(/\s+/g, " ");
  assert.equal(NOTICE, "Contains information from nmrshiftdb2 (www.nmrshiftdb.org), which is made available here under the nmrshiftdb2 Database License.");
  assert.ok(licence.includes(NOTICE));
  const notice = caps.filter((c) => c.text.includes("nmrshiftdb2")), ppm = caps.find((c) => c.text === "ppm")!;
  assert.deepEqual(notice.map((c) => [c.text, c.colour, c.width, c.align]), [[NOTICE, GREY, 202 * PT, "left"]]);
  assert.ok(notice[0].y < ppm.y - em);
  // A7: every part in one plain group (a click picks it whole, a double-click one part), the structure in none.
  assert.equal(items.length, fig.lines.length + fig.curves.length + fig.texts.length);
  assert.equal(m.groups?.length, 1);
  assert.ok(!m.groups![0].integral && !m.groups![0].atoms.length);
  assert.deepEqual([...m.groups![0].items].sort((a, b) => a - b), [...items].sort((a, b) => a - b));
  // One label moved 1 pt left, typed over and coloured red keeps all of that, and the rest of the spectrum, in .oct
  // and in CDXML.
  const q = caps.find((c) => c.text.startsWith("2.42"))!, RED = "#B42323";
  const edited: Mol = { ...m, captions: caps.map((c) => (c.id === q.id ? { ...c, x: c.x - PT, text: "2.40 (q, 2H)", colour: RED } : c)) };
  for (const [how, back] of [["oct", readOct(writeOct(edited, DEFAULT_STYLE)).mol], ["CDXML", fromCdxml(toCdxml(edited, DEFAULT_STYLE)).mol]] as const) {
    assert.equal(back.captions?.length, caps.length, `${how}: captions`);
    assert.equal(back.arrows?.length, m.arrows?.length, `${how}: lines and curves`);
    assert.equal(back.groups?.length, 1, `${how}: groups`);
    assert.ok(!back.groups![0].integral && back.groups![0].items.length === items.length, `${how}: the group`);
    const r = back.captions!.find((c) => c.text === "2.40 (q, 2H)")!;
    assert.ok(r && r.colour === RED && r.angle === q.angle && Math.abs(r.x - (q.x - PT)) < 0.01 * PT && Math.abs(r.y - q.y) < 0.01 * PT, `${how}: the edited label`);
    assert.ok(back.captions!.every((c) => c.size === undefined || c.size === 10), `${how}: sizes`);
  }
}
// Add to drawing > Shifts beside atoms: the notice once, under the structure, when the drawing has none.
{
  const one: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [] }, once = withNotice(one, [0], 14);
  assert.deepEqual(once.captions?.map((c) => [c.text, c.under, c.colour, c.width]), [[NOTICE, [0], GREY, 14]]);
  assert.equal(withNotice(once, [0], 14), once);
  assert.equal(withNotice(one, [], 14), one);
}
console.log("spectrumplot.check: ok");
