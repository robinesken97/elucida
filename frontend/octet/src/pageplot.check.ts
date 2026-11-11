// Run: node src/pageplot.check.ts. Fails loudly if a page spectrum's record and roles go wrong: a resize that scales
// its text, loses what the user changed, brings back a deleted part, or a file Octet 1.1.0 would read differently.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { hydrogens, type Arrow, type Caption, type Mol } from "./render.ts";
import { predict, readTables, type Prediction } from "./nmr.ts";
import type { Graph } from "./naming.ts";
import { parse, serialize } from "./file.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { readOct, writeOct } from "./oct.ts";
import { fullRange, NOTICE, placeFigure } from "./spectrumplot.ts";
import { analyse, fromJcamp } from "./measured.ts";
import { addCaption, duplicateSelection, extractSelection, groupSelection, insertMol, tidyGroups, transformParts } from "./edit.ts";
import { widthOf } from "./arial.ts";
import { followLeaders, labelLines, lonePlot, MAX_TRACE, placePlot, plotFigure, plotName, plotsIn, plotShift, plotTop, readPlot, reframe, replot, rescale, signalKeys, traceOf, type Plot, type PlotEnv } from "./pageplot.ts";
import { describe, groupTitle } from "./access.ts";
import { msFigure, type IonOf } from "./msanalysis.ts";

const PT = 1 / 14.4, env: PlotEnv = { captionSize: 10, bond: 14.4, measure: (t) => widthOf(t, 1) };
readTables(gunzipSync(readFileSync(new URL("../data/nmr/shifts.bin.gz", import.meta.url))));
function graph(els: string[], bonds: [number, number, number][]): Graph {
  const used = els.map(() => 0);
  for (const [a, b, o] of bonds) { used[a] += o; used[b] += o; }
  return { atoms: els.map((el, i) => ({ el, charge: 0, h: hydrogens(el, 0, used[i]) })), bonds: bonds.map(([a, b, order]) => ({ a, b, order: order as 1 | 2 | 3 })) };
}
// Octane-3,5-dione (CCCC(=O)CC(=O)CC).
const DIONE = graph(["C", "C", "C", "C", "O", "C", "C", "O", "C", "C"], [[0, 1, 1], [1, 2, 1], [2, 3, 1], [3, 4, 2], [3, 5, 1], [5, 6, 1], [6, 7, 2], [6, 8, 1], [8, 9, 1]]);
const h1 = predict(DIONE, "1H")!, c13 = predict(DIONE, "13C")!;
// The record Add to drawing > Spectrum makes (Editor.tsx addSpectrum): 400 MHz, CDCl₃ with its peaks, 202 pt wide.
const recordOf = (p: Prediction, colours: (string | undefined)[] = []): Plot => {
  const keys = signalKeys(p.signals);
  return {
    kind: "predicted", nucleus: p.nucleus, mhz: 400, solvent: "CDCl₃", solventPeaks: true, range: fullRange(p, p.nucleus), frame: [14, 3.5], origin: [0, 0], scale: 1, text: 1, labels: "auto",
    title: `${p.nucleus === "1H" ? "¹H" : "¹³C"} NMR (400 MHz, CDCl₃), predicted`, notice: true, roles: [],
    signals: p.signals.map((s, k) => ({ key: keys[k], shift: s.shift, nuclei: s.nuclei, couplings: s.couplings.map((c) => ({ j: c.j, n: c.n })), ...(s.broad ? { broad: true as const } : {}), ...(colours[k] ? { colour: colours[k] } : {}) })),
  };
};
const structure: Mol = { atoms: [{ label: "C", location: [7, 2, 0] }], bonds: [] };
const add = (p: Plot): [Mol, number[]] => { const fig = plotFigure(p, env); return placePlot(structure, { ...p, origin: [0, -plotTop(fig, p, env)] }, env, fig); };
const groupOf = (m: Mol) => m.groups!.find((g) => g.plot)!;
const parts = (m: Mol) => { const ids = new Set(groupOf(m).items); return { caps: (m.captions ?? []).filter((c) => ids.has(c.id)), lines: (m.arrows ?? []).filter((a) => ids.has(a.id)) }; };
const role = (x: Caption | Arrow) => x.role!.role;
// Where a right handle drag of w bond lengths takes the frame (left, bottom, right, top).
const BOX: [number, number, number, number] = [-1, -3, 15, 6];
const wider = (m: Mol, w: number) => reframe(m, groupOf(m).id, BOX, [BOX[0], BOX[1], BOX[2] + w, BOX[3]], env);

// Keys: the atoms' class, with #2 for a second signal of the same class. Every predicted signal has a code.
assert.ok(h1.signals.every((s) => s.code) && c13.signals.every((s) => s.code));
assert.deepEqual(signalKeys([{ code: "a", shift: 1 }, { code: "b", shift: 2 }, { code: "a", shift: 3 }]), ["a", "b", "a#2"]);
assert.equal(new Set(signalKeys(h1.signals)).size, h1.signals.length);

// --- Add to drawing --------------------------------------------------------------------------------------------
const [m0, items] = add(recordOf(h1));
const g0 = groupOf(m0), p0 = g0.plot!;
// One plain group with the record; every part has a role, each role once, and sits where Octet put it.
assert.ok(!g0.integral && g0.items.length === items.length);
const all0 = [...parts(m0).caps, ...parts(m0).lines];
assert.equal(all0.length, items.length);
assert.equal(new Set(all0.map(role)).size, all0.length, "a role twice");
assert.deepEqual([...p0.roles].sort(), all0.map(role).sort());
assert.ok(all0.every((x) => { const at = "from" in x ? x.from : [x.x, x.y]; return at[0] === x.role!.at[0] && at[1] === x.role!.at[1]; }));
for (const r of ["axis", "unit", "trace", "title", "notice"]) assert.ok(p0.roles.includes(r), r);
assert.ok(h1.signals.every((s, k) => p0.roles.some((r) => r.startsWith(`peak:${signalKeys(h1.signals)[k]}`))), "each peak has its label");
assert.deepEqual(plotShift(m0, g0), [0, 0]);
// No caption has a size of its own: they draw at the document's caption size (10 pt in ACS 1996).
assert.ok(parts(m0).caps.every((c) => c.size === undefined && c.font === undefined));
// Built again at the same frame, nothing moves: Octet never lays it out again unasked.
const same = replot(m0, g0.id, {}, env);
assert.deepEqual(same.captions, m0.captions);
assert.deepEqual(same.arrows, m0.arrows);

// --- Resize: 202 pt (14 bond lengths) to 504 pt -----------------------------------------------------------------------------------
// The furthest peak label's distance from its peak (pt): a label's middle against its peak's place on the axis.
function furthest(m: Mol): number {
  const p = groupOf(m).plot!, [lo, hi] = p.range, W = p.frame[0], em = (env.captionSize * p.text) / env.bond, keys = new Map(p.signals!.map((s) => [s.key, s.shift]));
  let most = 0;
  for (const c of parts(m).caps) {
    const r = role(c), k = /^peak:([^/~]+)/.exec(r)?.[1];
    if (k === undefined || !keys.has(k)) continue;
    const mid = c.angle === 90 ? c.x - 0.36 * em : c.x, peak = p.origin[0] + ((hi - keys.get(k)!) / (hi - lo)) * W;
    most = Math.max(most, Math.abs(mid - peak) / PT);
  }
  return most;
}
const GROW = 504 * PT - 14, m1 = wider(m0, GROW), p1 = groupOf(m1).plot!;
assert.ok(Math.abs(p1.frame[0] * 14.4 - 504) < 1e-6 && p1.frame[1] === 3.5, `frame ${p1.frame}`);
assert.deepEqual(p1.origin, p0.origin, "the left side stays");
// Every caption stays at the caption size; the labels come nearer their peaks (Auto turns them across at 504 pt).
assert.ok(parts(m1).caps.every((c) => c.size === undefined), "a caption scaled");
// For each orientation the furthest label comes nearer: across 92 pt to 34 pt, turned 23 pt to 6 pt (Auto is turned
// at 202 pt and across at 504 pt).
for (const labels of ["horizontal", "vertical"] as const) {
  const [a] = add({ ...recordOf(h1), labels }), [far0, far1] = [furthest(a), furthest(wider(a, GROW))];
  assert.ok(far1 < far0 / 2.5, `${labels}: furthest label ${far0.toFixed(0)} pt, then ${far1.toFixed(0)} pt`);
}
assert.ok(parts(m0).caps.filter((c) => role(c).startsWith("peak:")).every((c) => c.angle === 90) && parts(m1).caps.filter((c) => role(c).startsWith("peak:")).every((c) => !c.angle));
// The axis is 504 pt long; the structure is untouched.
const axis1 = parts(m1).lines.find((a) => role(a) === "axis")!;
assert.ok(Math.abs((axis1.to[0] - axis1.from[0]) * 14.4 - 504) < 1e-6);
assert.deepEqual(m1.atoms, m0.atoms);
// Parts that are still there keep their ids, so what was picked stays picked.
const ids0 = new Map(all0.map((x) => [role(x), x.id]));
assert.ok([...parts(m1).caps, ...parts(m1).lines].every((x) => !ids0.has(role(x)) || ids0.get(role(x)) === x.id));
// Back to 202 pt gives the same spectrum again.
const m2 = wider(m1, -GROW);
assert.deepEqual(parts(m2).caps.map((c) => [role(c), c.text, c.x, c.y, c.angle]).sort(), parts(m0).caps.map((c) => [role(c), c.text, c.x, c.y, c.angle]).sort());
// A drag on the left handle keeps the right side; one up keeps the bottom; a drag below the smallest frame stops there.
{
  const left = reframe(m0, g0.id, BOX, [BOX[0] - 2, BOX[1], BOX[2], BOX[3]], env), p = groupOf(left).plot!;
  assert.ok(Math.abs(p.origin[0] + p.frame[0] - (p0.origin[0] + p0.frame[0])) < 1e-9 && p.frame[0] === 16);
  const up = reframe(m0, g0.id, BOX, [BOX[0], BOX[1], BOX[2], BOX[3] + 1], env), q = groupOf(up).plot!;
  assert.ok(q.frame[1] === 4.5 && q.origin[1] === p0.origin[1]);
  const down = reframe(m0, g0.id, BOX, [BOX[0], BOX[1] - 1, BOX[2], BOX[3]], env), d = groupOf(down).plot!;
  assert.ok(d.frame[1] === 4.5 && Math.abs(d.origin[1] - (p0.origin[1] - 1)) < 1e-9, "the bottom handle keeps the top");
  const tiny = reframe(m0, g0.id, BOX, [BOX[0], BOX[1], BOX[0] + 0.1, BOX[3]], env);
  assert.ok(groupOf(tiny).plot!.frame[0] >= 3);
}

// --- What the user changed --------------------------------------------------------------------------------------
{
  const RED = "#B42323", BLUE = "#2F6FED", d: [number, number] = [-3 * PT, 2 * PT];
  const label = parts(m0).caps.find((c) => c.text.startsWith("2.42"))!, trace = parts(m0).lines.find((a) => role(a) === "trace")!, notice = parts(m0).caps.find((c) => c.text === NOTICE)!;
  const tick = parts(m0).caps.find((c) => role(c) === "tick:4/n")!;
  // A label moved and typed over, a tick number set in bold and 12 pt, the trace recoloured, the notice deleted.
  let m: Mol = {
    ...m0, captions: m0.captions!.filter((c) => c.id !== notice.id).map((c) => (c.id === label.id ? { ...c, x: c.x + d[0], y: c.y + d[1], text: "2.40 (q, 2H)" } : c.id === tick.id ? { ...c, bold: true, size: 12 } : c)),
    arrows: m0.arrows!.map((a) => (a.id === trace.id ? { ...a, colour: BLUE } : a)),
  };
  m = { ...m, groups: m.groups!.map((g) => (g.plot ? { ...g, items: g.items.filter((id) => id !== notice.id) } : g)) };
  // Turned labels stay turned for this check, so the label's place can be compared.
  m = { ...m, groups: m.groups!.map((g) => (g.plot ? { ...g, plot: { ...g.plot, labels: "vertical" as const } } : g)) };
  const r = wider(m, GROW), rc = parts(r).caps, rl = parts(r).lines;
  const fresh = parts(wider({ ...m0, groups: m0.groups!.map((g) => (g.plot ? { ...g, plot: { ...g.plot, labels: "vertical" as const } } : g)) }, GROW)).caps.find((c) => role(c) === role(label))!;
  const moved = rc.find((c) => role(c) === role(label))!;
  assert.equal(moved.text, "2.40 (q, 2H)");
  assert.ok(Math.abs(moved.x - (fresh.x + d[0])) < 1e-9 && Math.abs(moved.y - (fresh.y + d[1])) < 1e-9, "the moved label keeps its offset");
  assert.equal(moved.angle, 90);
  assert.ok(rl.filter((a) => role(a).split("~")[0] === "trace").some((a) => a.colour === BLUE) && rl.find((a) => role(a) === "trace")!.colour === BLUE, "the trace keeps its colour");
  const t = rc.find((c) => role(c) === "tick:4/n")!;
  assert.ok(t.bold && t.size === 12, "the tick number keeps its style and size");
  assert.ok(!rc.some((c) => c.text === NOTICE), "the deleted notice came back");
  // And it stays deleted on the next resize, and after saving.
  const again = wider(readOct(writeOct(r, DEFAULT_STYLE)).mol, -PT * 100);
  assert.ok(!parts(again).caps.some((c) => c.text === NOTICE));
  // A deleted leader (every piece of it) stays deleted; its label stays.
  const leader = `leader:${role(label).split("/")[0]}`, cut = (x: Arrow) => role(x).split("~")[0] === leader;
  const noLeader: Mol = { ...m0, arrows: m0.arrows!.filter((a) => !cut(a)), groups: m0.groups!.map((g) => (g.plot ? { ...g, items: g.items.filter((id) => !m0.arrows!.some((a) => a.id === id && cut(a))) } : g)) };
  const nl = wider(noLeader, GROW);
  assert.ok(!parts(nl).lines.some(cut) && parts(nl).caps.some((c) => role(c).startsWith(role(label).split("/")[0])));
}

// --- One named object, and leaders that follow their labels -----------------------------------------------------
{
  // The Actions panel's title and the screen reader's name for a page spectrum: what it plots, not its parts.
  assert.equal(plotName(p0), "¹H NMR spectrum");
  assert.equal(plotName(recordOf(c13)), "¹³C NMR spectrum");
  assert.equal(groupTitle(m0, g0), "¹H NMR spectrum");
  const plainGroup = { ...g0, plot: undefined };
  assert.equal(groupTitle({ ...m0, captions: [] }, plainGroup), "Group");
  const read = describe(m0, { box: () => [0, 0, 1, 1], name: () => undefined, formula: () => "" } as unknown as Parameters<typeof describe>[1]).find((x) => x.key === `g${g0.id}`)!;
  assert.deepEqual([read.role, read.name], ["spectrum", p0.title]);

  // A label's leader: its parts in order, and whether each starts where the last ends and the first is under the label.
  const leaderOf = (m: Mol, r: string) => parts(m).lines.filter((a) => role(a) === `leader:${r}` || role(a).startsWith(`leader:${r}~`)).sort((a, b) => role(a).localeCompare(role(b)));
  const chained = (ls: Arrow[]) => ls.every((a, k) => !k || Math.hypot(ls[k - 1].to[0] - a.from[0], ls[k - 1].to[1] - a.from[1]) < 1e-9);
  const nudged = (m: Mol, id: number, d: [number, number]): Mol => ({ ...m, captions: m.captions!.map((c) => (c.id === id ? { ...c, x: c.x + d[0], y: c.y + d[1] } : c)) });
  for (const labels of ["vertical", "horizontal"] as const) {
    // The label's line the leader joins: the turned label, or the bottom line across ("(q, 2H)" under "2.42").
    const top = parts(m0).caps.find((c) => c.text.startsWith("2.42"))!, r = role(top).split("/")[0];
    const [m] = add({ ...recordOf(h1), labels }), label = parts(m).caps.find((c) => role(c) === `${r}/0` || role(c) === r)!, was = leaderOf(m, r);
    assert.ok(was.length === 3 || was.length === 1, `${labels}: ${was.length} parts`);
    // Nudged 1 pt left, then dragged 5 pt right and 3 pt up: the stub moves with the label, the slant joins the stub to
    // the drop, and the drop stays on its peak.
    let cur = m;
    for (const d of [[-PT, 0], [5 * PT, 3 * PT]] as [number, number][]) cur = followLeaders(cur, nudged(cur, label.id, d));
    const now = leaderOf(cur, r), moved = parts(cur).caps.find((c) => c.id === label.id)!, dl: [number, number] = [moved.x - label.x, moved.y - label.y];
    assert.ok(Math.abs(dl[0] - 4 * PT) < 1e-9 && Math.abs(dl[1] - 3 * PT) < 1e-9);
    assert.ok(Math.abs(now[0].from[0] - was[0].from[0] - dl[0]) < 1e-9 && Math.abs(now[0].from[1] - was[0].from[1] - dl[1]) < 1e-9, `${labels}: the leader starts under the label`);
    assert.ok(chained(now), `${labels}: the leader is in one piece`);
    assert.deepEqual(now[now.length - 1].to, was[was.length - 1].to, `${labels}: the leader still ends on its peak`);
    // One step, one drawing: the label and its leader change together.
    assert.ok(cur.arrows!.filter((a) => !now.includes(a)).every((a) => m.arrows!.includes(a)));
    // A resize builds the leader again, still joining the label where it was moved to.
    const r1 = wider(cur, GROW), l1 = parts(r1).caps.find((c) => c.id === label.id || role(c) === `${r}/0` || role(c) === r)!, n1 = leaderOf(r1, r), fresh = leaderOf(wider(m, GROW), r);
    assert.ok(chained(n1), `${labels}: after a resize the leader is in one piece`);
    assert.ok(Math.abs(n1[0].from[0] - fresh[0].from[0] - (l1.x - l1.role!.at[0])) < 1e-9 && Math.abs(n1[0].from[1] - fresh[0].from[1] - (l1.y - l1.role!.at[1])) < 1e-9, `${labels}: after a resize the leader starts under the label`);
    assert.deepEqual(n1[n1.length - 1].to, fresh[fresh.length - 1].to, `${labels}: after a resize the leader ends on its peak`);
    // The label and its whole leader moved together (in one edit): nothing more moves.
    const ids = new Set(was.map((a) => a.id)), both: Mol = { ...nudged(m, label.id, [PT, 0]), arrows: m.arrows!.map((a) => (ids.has(a.id) ? { ...a, from: [a.from[0] + PT, a.from[1]], to: [a.to[0] + PT, a.to[1]] } : a)) };
    assert.equal(followLeaders(m, both), both);
    // A leader the user moved stays where they put it when its label moves after.
    const own: Mol = { ...m, arrows: m.arrows!.map((a) => (a.id === was[0].id ? { ...a, from: [a.from[0], a.from[1] + PT], to: [a.to[0], a.to[1] + PT] } : a)) };
    const after = nudged(own, label.id, [PT, 0]);
    assert.equal(followLeaders(own, after), after);
    assert.deepEqual(leaderOf(wider(after, GROW), r).map((a) => [a.from, a.to]).length > 0, true);
    // Across, the shift line moved alone leaves the leader on the line under it.
    const upper = parts(m).caps.find((c) => role(c) === `${r}/1`);
    if (upper) { const u = nudged(m, upper.id, [PT, 0]); assert.equal(followLeaders(m, u), u); }
    // A text change or another edit leaves the leader alone.
    const typed: Mol = { ...m, captions: m.captions!.map((c) => (c.id === label.id ? { ...c, text: "2.40" } : c)) };
    assert.equal(followLeaders(m, typed), typed);
  }
}
// A rebuild (a resize) that moves a label leaves its leader to replot: followLeaders moves nothing more.
{
  const r1 = wider(m0, 4);
  assert.equal(followLeaders(m0, r1), r1);
}
// A mass spectrum (Add to drawing > Mass spec) has no record, but its parts keep their roles, so a label moved takes
// its leader with it as a page spectrum's does, and the group is named "Mass spectrum".
{
  const ions = [100, 150, 151, 300].map((mz, k) => ({ ion: { mono: mz, top: mz, pattern: [{ mz, rel: 100 - 20 * k }] } as unknown as IonOf }));
  const [m] = placeFigure(structure, msFigure({ ions, range: [90, 320], width: 14, height: 3.5, em: 0.55, pt: PT }), [0, -6]);
  const g = m.groups![0], ids = new Set(g.items), caps = (m.captions ?? []).filter((c) => ids.has(c.id)), lines = (m.arrows ?? []).filter((a) => ids.has(a.id));
  assert.equal(groupTitle(m, g), "Mass spectrum");
  const read = describe(m, { box: () => [0, 0, 1, 1], name: () => undefined, formula: () => "" } as unknown as Parameters<typeof describe>[1]).find((x) => x.key === `g${g.id}`)!;
  assert.deepEqual([read.role, read.name], ["spectrum", "Mass spectrum"]);
  const label = caps.find((c) => c.role?.role === "peak:3/0")!, leader = lines.filter((a) => a.role?.role.startsWith("leader:peak:3")).sort((a, b) => a.role!.role.localeCompare(b.role!.role));
  assert.ok(label && leader.length > 0);
  const moved: Mol = { ...m, captions: m.captions!.map((c) => (c.id === label.id ? { ...c, x: c.x - 0.5, y: c.y + 0.2 } : c)) }, now = followLeaders(m, moved);
  const after = leader.map((a) => now.arrows!.find((x) => x.id === a.id)!);
  assert.ok(Math.abs(after[0].from[0] - leader[0].from[0] + 0.5) < 1e-9 && Math.abs(after[0].from[1] - leader[0].from[1] - 0.2) < 1e-9);
  assert.deepEqual(after[after.length - 1].to, leader[leader.length - 1].to);
  assert.ok(after.every((a, k) => !k || Math.hypot(after[k - 1].to[0] - a.from[0], after[k - 1].to[1] - a.from[1]) < 1e-9));
  // Read from its CDXML alone (the copy Octet keeps in the file damaged), the rounded parts still join: the leader follows.
  const back = fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol, lb = back.captions!.find((c) => c.role?.role === "peak:3/0")!;
  const mb: Mol = { ...back, captions: back.captions!.map((c) => (c.id === lb.id ? { ...c, x: c.x - 0.5 } : c)) };
  assert.notEqual(followLeaders(back, mb), mb);
}

// A copy of part of a page spectrum (Option-drag, Duplicate, Copy and Paste) is plain: it has no role, so the
// original keeps its own and still takes its leader. A copy of the whole spectrum keeps its roles in its own group.
{
  const label = parts(m0).caps.find((c) => c.text.startsWith("2.42"))!, r = role(label).split("/")[0];
  const leader = parts(m0).lines.filter((a) => role(a).startsWith(`leader:${r}`)), ids = new Set(leader.map((a) => a.id));
  const moves = (m: Mol, label: number, first: number) => {
    const now = followLeaders(m, { ...m, captions: m.captions!.map((c) => (c.id === label ? { ...c, x: c.x + 0.3 } : c)) });
    return Math.abs(now.arrows!.find((a) => a.id === first)!.from[0] - m.arrows!.find((a) => a.id === first)!.from[0] - 0.3) < 1e-9;
  };
  const first = leader.find((a) => role(a) === `leader:${r}`)!.id;
  assert.ok(moves(m0, label.id, first));
  // Option-drag of the label alone, and of the label with its leader.
  for (const items of [new Set([label.id]), new Set([label.id, ...ids])]) {
    const d = duplicateSelection(m0, new Set(), items), copies = [...items].map((id) => d.ids.get(id)!);
    assert.ok([...d.mol.captions!, ...d.mol.arrows!].filter((x) => copies.includes(x.id)).every((x) => !x.role), "a copy has no role");
    assert.ok(moves(d.mol, label.id, first), "the original label still takes its leader");
  }
  // Copy and Paste: the part as the clipboard holds it, pasted beside.
  const pasted = insertMol(m0, extractSelection(m0, new Set(), new Set([label.id, ...ids])), [1, 1]);
  assert.ok([...pasted.mol.captions!, ...pasted.mol.arrows!].filter((x) => pasted.items.has(x.id)).every((x) => !x.role));
  assert.ok(moves(pasted.mol, label.id, first));
  // The whole spectrum copied: its own group and record, its roles, and each label takes its own leader.
  const whole = duplicateSelection(m0, new Set(), new Set(g0.items)), g1 = whole.mol.groups!.find((g) => g.plot && g.id !== g0.id)!;
  assert.ok(g1 && g1.items.every((id) => [...whole.mol.captions!, ...whole.mol.arrows!].find((x) => x.id === id)?.role));
  assert.ok(moves(whole.mol, whole.ids.get(label.id)!, whole.ids.get(first)!) && moves(whole.mol, label.id, first));
}

// --- Moved, turned, and with other things -----------------------------------------------------------------------
{
  // The whole spectrum moved: its record holds, and a resize keeps it where it was moved to.
  const all = new Set(g0.items), moved = transformParts(m0, new Set(), all, (q) => [q[0] + 5, q[1] - 2]);
  assert.deepEqual(plotShift(moved, groupOf(moved)), [5, -2]);
  const r = wider(moved, 3), axis = parts(r).lines.find((a) => role(a) === "axis")!;
  assert.ok(Math.abs(axis.from[0] - (p0.origin[0] + 5)) < 1e-9 && Math.abs(axis.from[1] - (p0.origin[1] - 2)) < 1e-9);
  // Turned a quarter: the parts no longer agree, so the record is not used and the handles scale it as before.
  const turned = transformParts(m0, new Set(), all, (q) => [-q[1], q[0]]);
  assert.equal(plotShift(turned, groupOf(turned)), undefined);
  assert.equal(lonePlot(turned, new Set(), all), undefined);
  assert.equal(replot(turned, g0.id, { frame: [20, 3.5] }, env), turned);
  // The handles change the frame only for a spectrum alone; with the structure too, Scale… builds it at its new frame.
  assert.equal(lonePlot(m0, new Set(), all)?.id, g0.id);
  assert.equal(lonePlot(m0, new Set([0]), all), undefined);
  assert.deepEqual(plotsIn(m0, all).map((g) => g.id), [g0.id]);
  assert.deepEqual(plotsIn(m0, new Set([...all].slice(1))), []);
  // Scale… 200% with Labels and lines on: twice the frame, text at 20 pt and lines twice as wide; a resize after that
  // keeps 20 pt. Off: twice the frame, text at the caption size.
  const c: [number, number] = [0, 0], f = (q: [number, number]): [number, number] => [c[0] + 2 * q[0], c[1] + 2 * q[1]];
  const on = rescale(m0, g0.id, f, [2, 2], 2, env), pon = groupOf(on).plot!;
  assert.deepEqual([pon.frame, pon.text, pon.origin], [[28, 7], 2, [2 * p0.origin[0], 2 * p0.origin[1]]]);
  assert.ok(parts(on).caps.every((x) => x.size === 20) && parts(on).lines.every((x) => x.scale === 2));
  assert.ok(parts(wider(on, 2)).caps.every((x) => x.size === 20));
  const off = rescale(m0, g0.id, f, [2, 2], 1, env);
  assert.ok(groupOf(off).plot!.frame[0] === 28 && parts(off).caps.every((x) => x.size === undefined) && parts(off).lines.every((x) => x.scale === undefined));
}

// --- Auto turns the labels, in a group, flipped ----------------------------------------------------------------
{
  // A label moved and coloured while turned (Auto at 202 pt) keeps its colour and move across (Auto at 504 pt), and
  // turned again.
  const label = parts(m0).caps.find((c) => c.text.startsWith("2.42"))!, d: [number, number] = [2 * PT, -PT], RED = "#B42323";
  const m: Mol = { ...m0, captions: m0.captions!.map((c) => (c.id === label.id ? { ...c, x: c.x + d[0], y: c.y + d[1], colour: RED, bold: true } : c)) };
  const fresh = parts(wider(m0, GROW)).caps.filter((c) => role(c).startsWith(`${role(label)}/`));
  const across = parts(wider(m, GROW)).caps.filter((c) => role(c).startsWith(`${role(label)}/`));
  assert.equal(across.length, 2);
  assert.ok(across.every((c) => c.colour === RED && c.bold && !c.angle), "the label's colour across");
  assert.ok(across.every((c) => { const f = fresh.find((x) => role(x) === role(c))!; return Math.abs(c.x - f.x - d[0]) < 1e-9 && Math.abs(c.y - f.y - d[1]) < 1e-9; }), "the label's move across");
  const back = parts(wider(wider(m, GROW), -GROW)).caps.find((c) => role(c) === role(label))!;
  assert.ok(back.colour === RED && back.angle === 90 && Math.abs(back.x - label.x - d[0]) < 1e-9, "turned again");
  // A spectrum grouped with its structure: a resize that adds ticks puts them in the outer group too, and takes the
  // parts gone out of it.
  const [outer, oid] = groupSelection(m0, new Set([0]), new Set(g0.items))!;
  const r = reframe(outer, g0.id, BOX, [BOX[0], BOX[1], BOX[2] + 40, BOX[3]], env), inner = groupOf(r), out = r.groups!.find((g) => g.id === oid)!;
  const live = new Set([...r.captions!, ...r.arrows!].map((x) => x.id));
  assert.ok(inner.items.length !== g0.items.length && inner.items.every((id) => out.items.includes(id)) && out.items.every((id) => live.has(id)), "the outer group");
  assert.equal(tidyGroups(r).groups!.length, 2);
  // Flipped either way, the parts that still agree sit on one line, so the record is not used.
  for (const f of [(q: [number, number]): [number, number] => [q[0], -q[1]], (q: [number, number]): [number, number] => [-q[0], q[1]]]) {
    const flipped = transformParts(m0, new Set(), new Set(g0.items), f);
    assert.equal(plotShift(flipped, groupOf(flipped)), undefined);
  }
  // A record that would build too much is left out: a hundred thousand lines, or a range of millions of points.
  assert.equal(readPlot({ ...p0, signals: [{ key: "a", shift: 5, nuclei: 1, couplings: Array.from({ length: 16 }, () => ({ j: 7, n: 64 })) }] }), undefined);
  assert.equal(readPlot({ ...p0, mhz: 1500, range: [-1e5, 1e5] }), undefined);
  assert.equal(readPlot({ ...p0, mhz: 0 }), undefined);
  assert.equal(readPlot({ ...p0, nucleus: "19F" }), undefined);
  assert.deepEqual(readPlot(JSON.parse(JSON.stringify(p0))), p0);
}

// --- Saving, and Octet 1.1.0 ------------------------------------------------------------------------------------
{
  // .oct and CDXML keep the record and the roles, and a resize after opening gives what it gives before saving.
  for (const [how, back] of [["oct", readOct(writeOct(m0, DEFAULT_STYLE)).mol], ["CDXML", fromCdxml(toCdxml(m0, DEFAULT_STYLE)).mol]] as const) {
    const g = groupOf(back);
    assert.ok(g && g.items.length === items.length, `${how}: the group`);
    assert.deepEqual(readPlot(JSON.parse(JSON.stringify(g.plot))), g.plot, `${how}: the record`);
    assert.deepEqual(g.plot!.roles, p0.roles, `${how}: the roles`);
    assert.deepEqual(plotShift(back, g)?.map((v) => Math.round(v * 1e3) || 0), [0, 0], `${how}: the parts where Octet put them`);
    const a = parts(wider(back, 2)).caps.map((x) => [role(x), x.text, Math.round(x.x * 100), Math.round(x.y * 100)]).sort();
    const b = parts(wider(m0, 2)).caps.map((x) => [role(x), x.text, Math.round(x.x * 100), Math.round(x.y * 100)]).sort();
    assert.deepEqual(a, b, `${how}: a resize after opening`);
  }
  // The .oct stays version 1, and the only keys a 1.1.1 page spectrum adds are "plot" on its group and "role" on its
  // parts, which Octet 1.1.0 leaves out (it reads only the keys it knows). Without them it is the same drawing.
  const json = JSON.parse(serialize(m0));
  assert.equal(json.version, 1);
  const strip = (x: Record<string, unknown>[] | undefined, key: string) => x?.forEach((o) => delete o[key]);
  strip(json.groups, "plot"); strip(json.captions, "role"); strip(json.arrows, "role");
  const plain: Mol = { ...m0, captions: m0.captions!.map(({ role: _, ...c }) => c), arrows: m0.arrows!.map(({ role: _, ...a }) => a), groups: m0.groups!.map(({ plot: _, ...g }) => g) };
  assert.deepEqual(json, JSON.parse(serialize(plain)));
  const old = parse(JSON.stringify(json));
  assert.ok(old.groups?.length === 1 && !old.groups[0].plot && !old.groups[0].integral && old.captions!.every((c) => !c.role));
  // A record or role that is not sound is left out, and the group is a plain group.
  for (const bad of [{ ...p0, frame: [0, 1] }, { ...p0, labels: "sideways" }, { ...p0, signals: undefined }, { ...p0, roles: "x" }, { ...p0, signals: [{ key: "a", shift: 1, nuclei: 1, couplings: [{ j: 7, n: 1e9 }] }] }]) assert.equal(readPlot(bad), undefined);
  const damaged = JSON.parse(serialize(m0));
  damaged.groups[0].plot.frame = "wide";
  damaged.captions[0].role = { role: 7 };
  const opened = parse(JSON.stringify(damaged));
  assert.ok(opened.groups?.length === 1 && !opened.groups[0].plot && !opened.captions![0].role);
}

// --- ¹³C, and a measured spectrum -------------------------------------------------------------------------------
{
  const [m] = add(recordOf(c13, c13.signals.map((_, k) => (k === 0 ? "#D2453B" : undefined)))), r = wider(m, 10);
  assert.ok(parts(r).caps.every((c) => c.size === undefined) && parts(r).lines.some((a) => a.colour === "#D2453B"));
  // A measured ¹H spectrum: its points in range, at most MAX_TRACE, with its multiplets.
  const N = 40000, y = new Float64Array(N), MHZ = 400, w = 0.5 / MHZ;
  const lines: [number, number][] = [[4.12 - 10.5 / MHZ, 1], [4.12 - 3.5 / MHZ, 3], [4.12 + 3.5 / MHZ, 3], [4.12 + 10.5 / MHZ, 1], [1.26 - 7 / MHZ, 1], [1.26, 2], [1.26 + 7 / MHZ, 1]];
  for (let i = 0; i < N; i++) { const x = 11 - (12 * i) / (N - 1); for (const [p, h] of lines) y[i] += (h * w * w) / ((x - p) ** 2 + w * w); }
  const ms = fromJcamp({ title: "Check", kind: "nmr", nucleus: "1H", mhz: MHZ, solvent: "CDCl₃", xUnit: "ppm", yUnit: "", first: 11, last: -1, y }, 1), a = analyse(ms);
  const trace = traceOf(ms, a, [0, 8], () => "#2F6FED");
  assert.ok(trace.x.length <= MAX_TRACE && trace.x.length === trace.y.length && trace.peaks.length === a.groups.length);
  const p: Plot = { kind: "measured", nucleus: "1H", mhz: MHZ, solvent: "CDCl₃", solventPeaks: false, range: [0, 8], frame: [14, 3.5], origin: [0, 0], scale: 1, text: 1, labels: "auto", title: "¹H NMR (400 MHz, CDCl₃)", notice: false, roles: [], trace };
  assert.deepEqual(readPlot(JSON.parse(JSON.stringify(p))), p);
  const [mm] = add(p), rm = wider(mm, 10), q = parts(rm).caps.find((c) => c.text === "4.12")!;
  assert.ok(q && q.colour === "#2F6FED" && parts(rm).caps.every((c) => c.size === undefined) && !parts(rm).caps.some((c) => c.text === NOTICE));
  assert.ok(Math.abs(groupOf(rm).plot!.frame[0] - 24) < 1e-9);
}

// --- A peak label across is one label --------------------------------------------------------------------------
// "2.42" over "(q, 2H)": a double-click on either line picks both (labelLines, Editor's double-click), they move
// together, and the leader follows. A turned label, a tick's number, a mass spectrum's label and a plain copy are one
// caption each.
{
  const ids = (m: Mol, r: string) => parts(m).caps.filter((c) => role(c) === r).map((c) => c.id);
  const lineOf = (m: Mol, text: string) => parts(m).caps.find((c) => c.text.startsWith(text))!;
  const [m] = add({ ...recordOf(h1), labels: "horizontal" }), top = lineOf(m, "2.42"), r = role(top).split("/")[0];
  const under = parts(m).caps.find((c) => role(c) === `${r}/0`)!;
  assert.ok(role(top) === `${r}/1` && under && under.text.includes("H"), `${role(top)} over ${under?.text}`);
  const both = [under.id, top.id].sort();
  assert.deepEqual(labelLines(m, top.id).sort(), both);
  assert.deepEqual(labelLines(m, under.id).sort(), both);
  // Every label across in the spectrum: one or two lines, each line in exactly one label.
  const peakCaps = parts(m).caps.filter((c) => /^(peak|solvent):/.test(role(c)));
  assert.ok(peakCaps.every((c) => { const l = labelLines(m, c.id); return l.includes(c.id) && l.length <= 2 && l.every((id) => labelLines(m, id).length === l.length); }));
  // Both lines nudged as one edit (a nudge or a drag of what is picked): the leader follows, in one piece, still on
  // its peak, and nothing else moves. Undo is that one edit.
  const d: [number, number] = [3 * PT, 2 * PT], picked = new Set(both);
  const moved: Mol = { ...m, captions: m.captions!.map((c) => (picked.has(c.id) ? { ...c, x: c.x + d[0], y: c.y + d[1] } : c)) }, now = followLeaders(m, moved);
  const leaderOf = (x: Mol) => parts(x).lines.filter((a) => role(a) === `leader:${r}` || role(a).startsWith(`leader:${r}~`)).sort((a, b) => role(a).localeCompare(role(b)));
  const was = leaderOf(m), after = leaderOf(now);
  assert.ok(was.length === 3 || was.length === 1);
  assert.ok(Math.abs(after[0].from[0] - was[0].from[0] - d[0]) < 1e-9 && Math.abs(after[0].from[1] - was[0].from[1] - d[1]) < 1e-9, "the leader starts under the label");
  assert.ok(after.every((a, k) => !k || Math.hypot(after[k - 1].to[0] - a.from[0], after[k - 1].to[1] - a.from[1]) < 1e-9), "the leader is in one piece");
  assert.deepEqual(after[after.length - 1].to, was[was.length - 1].to, "the leader ends on its peak");
  assert.ok(now.arrows!.filter((a) => !after.some((x) => x.id === a.id)).every((a) => m.arrows!.includes(a)));
  assert.deepEqual(now.captions, moved.captions);
  // Colour and bold on what is picked reach both lines, and a resize keeps them on both.
  const styled: Mol = { ...now, captions: now.captions!.map((c) => (picked.has(c.id) ? { ...c, colour: "#D2453B", bold: true } : c)) }, r1 = wider(styled, 2);
  assert.ok(parts(r1).caps.filter((c) => role(c).startsWith(`${r}/`)).every((c) => c.colour === "#D2453B" && c.bold));
  assert.deepEqual(labelLines(r1, top.id).sort(), both, "a resize keeps the label's lines");
  // Turned, a label is one caption, as before.
  const [v] = add({ ...recordOf(h1), labels: "vertical" }), turned = parts(v).caps.find((c) => role(c) === r)!;
  assert.deepEqual(labelLines(v, turned.id), [turned.id]);
  // A tick's number, the title, and a caption outside any spectrum are themselves.
  for (const c of parts(m).caps.filter((x) => !/^(peak|solvent):/.test(role(x)))) assert.deepEqual(labelLines(m, c.id), [c.id], role(c));
  const [free, fid] = addCaption(m, { text: "2.42", x: 0, y: 0 });
  assert.deepEqual(labelLines(free, fid), [fid]);
  // A copy of both lines (Option-drag, Duplicate) is plain text: each line is itself, and the original pair still pairs.
  const dup = duplicateSelection(m, new Set(), picked), copy = dup.ids.get(top.id)!;
  assert.deepEqual(labelLines(dup.mol, copy), [copy]);
  assert.deepEqual(labelLines(dup.mol, top.id).sort(), both);
  // Two spectra in one group: a label pairs only within its own spectrum, though the roles are the same.
  const [m2] = placePlot(m, { ...recordOf(h1), labels: "horizontal", origin: [0, -12] }, env), g2 = m2.groups!.filter((g) => g.plot);
  const outer = groupSelection(m2, new Set(), new Set(g2.flatMap((g) => g.items)))!, inner = outer[0].groups!.find((g) => g.plot && g.id !== groupOf(m).id)!;
  const top2 = outer[0].captions!.find((c) => inner.items.includes(c.id) && c.role?.role === `${r}/1`)!;
  assert.deepEqual(labelLines(outer[0], top.id).sort(), both);
  assert.ok(labelLines(outer[0], top2.id).length === 2 && labelLines(outer[0], top2.id).every((id) => inner.items.includes(id)));
  // A measured spectrum's label across pairs the same way.
  const N = 20000, y = new Float64Array(N), MHZ = 400, w = 0.5 / MHZ;
  const lines: [number, number][] = [[4.12 - 10.5 / MHZ, 1], [4.12 - 3.5 / MHZ, 3], [4.12 + 3.5 / MHZ, 3], [4.12 + 10.5 / MHZ, 1]];
  for (let i = 0; i < N; i++) { const x = 11 - (12 * i) / (N - 1); for (const [p, h] of lines) y[i] += (h * w * w) / ((x - p) ** 2 + w * w); }
  const ms = fromJcamp({ title: "Check", kind: "nmr", nucleus: "1H", mhz: MHZ, solvent: "CDCl₃", xUnit: "ppm", yUnit: "", first: 11, last: -1, y }, 1);
  const [mm] = add({ kind: "measured", nucleus: "1H", mhz: MHZ, solvent: "CDCl₃", solventPeaks: false, range: [0, 8], frame: [24, 3.5], origin: [0, 0], scale: 1, text: 1, labels: "horizontal", title: "", notice: false, roles: [], trace: traceOf(ms, analyse(ms), [0, 8], () => undefined) });
  const q = lineOf(mm, "4.12"), ql = labelLines(mm, q.id);
  assert.ok(ql.length === 2 && ql.includes(q.id) && parts(mm).caps.find((c) => ql.includes(c.id) && c.id !== q.id)!.text.includes("H"), `measured: ${ql.length} lines`);
  // A mass spectrum's label is one line: itself.
  const ions = [100, 150].map((mz, k) => ({ ion: { mono: mz, top: mz, pattern: [{ mz, rel: 100 - 20 * k }] } as unknown as IonOf }));
  const [msm] = placeFigure(structure, msFigure({ ions, range: [90, 320], width: 14, height: 3.5, em: 0.55, pt: PT }), [0, -6]), lab = msm.captions!.find((c) => c.role?.role.startsWith("peak:"))!;
  assert.deepEqual(labelLines(msm, lab.id), [lab.id]);
}

// --- Speed: a 60-peak ¹³C spectrum built again at a new frame, as each step of a drag is -----------------------
{
  const sixty: Prediction = { nucleus: "13C", signals: Array.from({ length: 60 }, (_, k) => ({ atoms: [k], shift: 10 + k * 3.1, nuclei: 1, couplings: [], sd: 1, based: 5, code: `c${k}` })) };
  const [m] = add(recordOf(sixty)), times: number[] = [];
  let cur = m;
  for (let k = 0; k < 30; k++) { const t0 = performance.now(); cur = wider(cur, 0.1); times.push(performance.now() - t0); }
  times.sort((a, b) => a - b);
  assert.ok(times[15] < 16, `median ${times[15].toFixed(1)} ms a step`);
}
console.log("pageplot.check: ok");
