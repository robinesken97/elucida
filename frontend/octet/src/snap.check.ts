// Run: node src/snap.check.ts. Fails loudly if snapping breaks.
import assert from "node:assert/strict";
import { EMPTY, fragments, merge, pos, sprout, type P } from "./edit.ts";
import type { Mol } from "./render.ts";
import { type Guide, snapBoxes, snapMove } from "./snap.ts";

// Two ethanes side by side. Moving the second (atoms 2, 3) a little off line snaps it back level.
const a = sprout(EMPTY, [0, 0]), m = merge(a, a, [3, 0.04]);
const ids = new Set([2, 3]);
const near = snapMove(m, ids, [0, -0.02], 0.1);
assert.equal(near.guides.length > 0, true, "a guide shows");
assert.ok(Math.abs(near.d[1] - -0.04) < 1e-9, "it lines up exactly");
// Dropping an atom close to another atom snaps onto it.
// Atom 2 starts at (3, 0.04); atom 1 is at (cos 30°, sin 30°). Drag atom 2 to within 0.04 of atom 1.
const onto = snapMove(m, ids, [Math.cos(Math.PI / 6) - 3 + 0.03, Math.sin(Math.PI / 6) - 0.04 + 0.02], 0.1);
assert.ok(onto.point, "point snap");
assert.ok(Math.abs(onto.d[0] - (Math.cos(Math.PI / 6) - 3)) < 1e-9 && Math.abs(onto.d[1] - (Math.sin(Math.PI / 6) - 0.04)) < 1e-9, "lands exactly on the atom");
// Far from everything: no change.
const free = snapMove(m, ids, [0, 5], 0.1);
assert.deepEqual(free.d, [0, 5]);
assert.equal(free.guides.length, 0);
// A structure inside a box (no other structures): its middle snaps to the box's middle on both axes.
const inBox = snapMove(a, new Set([0, 1]), [0.05, -0.03], 0.1, { moving: [0, 0, 0.866, 0.5], targets: [[-2, -2.25, 2.866, 2.75]] });
assert.ok(Math.abs(inBox.d[0]) < 1e-9 && Math.abs(inBox.d[1]) < 1e-9 && inBox.guides.length === 2, `centred in its box: ${inBox.d}`);
// A box moved round a structure centres on it the same way.
const round = snapBoxes([-2, -2, 3, 3], [[0, 0, 1, 1]], [0.04, 0.03], 0.1);
assert.ok(round.d.every((v) => Math.abs(v) < 1e-9), `centred round it: ${round.d}`);

// The kept targets and the grid give exactly what comparing every pair gives: the reference below is the plain
// search, run on random drawings (atoms on top of each other too, for ties) with the same atoms and boxes reused, as
// a drag reuses them.
function plainAtom(m: Mol, ids: Set<number>, d: P, tol: number) {
  const moving = [...ids].filter((i) => i < m.atoms.length).map((i) => pos(m, i));
  const others = fragments(m).map((g) => g.filter((i) => !ids.has(i))).filter((g) => g.length);
  let best: { gap: number; shift: P; at: P } | undefined;
  for (const q of moving) for (const g of others) for (const i of g) {
    const s = pos(m, i), shift: P = [s[0] - q[0] - d[0], s[1] - q[1] - d[1]], gap = Math.hypot(...shift);
    if (gap < tol && (!best || gap < best.gap)) best = { gap, shift, at: s };
  }
  return best && { d: [d[0] + best.shift[0], d[1] + best.shift[1]], guides: [], point: best.at };
}
function plainBoxes(moving: number[], boxes: number[][], d: P, tol: number) {
  if (!boxes.length) return { d, guides: [] };
  const mb = moving.map((v, k) => v + d[k % 2]);
  const axis = (k: 0 | 1) => {
    const o = 1 - k, refs = [mb[k], (mb[k] + mb[k + 2]) / 2, mb[k + 2]];
    const targets = boxes.flatMap((b) => [b[k], (b[k] + b[k + 2]) / 2, b[k + 2]].map((at) => ({ at, lo: b[o], hi: b[o + 2] })));
    for (const p of boxes) for (const q of boxes) {
      if (p === q || p[k + 2] >= q[k] || p[o] > q[o + 2] || q[o] > p[o + 2]) continue;
      targets.push({ at: (p[k + 2] + q[k]) / 2, lo: Math.min(p[o], q[o]), hi: Math.max(p[o + 2], q[o + 2]) });
    }
    let pick: { diff: number; line: { at: number; lo: number; hi: number }; size?: number; next?: number[] } | undefined;
    for (const [n, r] of refs.entries()) for (const t of targets) {
      const diff = t.at - r, weight = n === 1 ? 0.7 : 1;
      if (Math.abs(diff) < tol && (!pick || Math.abs(diff) * weight < Math.abs(pick.diff))) pick = { diff, line: t };
    }
    // Equal spacing: every space between a box and its nearest neighbour after it in line, put beside each box in line
    // with the moving one, where nothing in line comes between.
    const line = (a: number[], b: number[]) => a[o] <= b[o + 2] && b[o] <= a[o + 2];
    const sizes = boxes.flatMap((a) => {
      const after = boxes.filter((b) => b !== a && b[k] > a[k + 2] && line(a, b)).sort((p, q) => p[k] - q[k])[0];
      return after ? [after[k] - a[k + 2]] : [];
    });
    for (const t of boxes) if (line(t, mb)) for (const size of sizes) for (const diff of [t[k + 2] + size - mb[k], t[k] - size - mb[k + 2]]) {
      if (!(Math.abs(diff) < tol) || (pick && Math.abs(diff) > Math.abs(pick.diff))) continue;
      const [from, to] = diff === t[k + 2] + size - mb[k] ? [t[k + 2], mb[k] + diff] : [mb[k + 2] + diff, t[k]];
      if (!boxes.some((x) => x !== t && line(x, mb) && x[k] < to && x[k + 2] > from)) pick = { diff, line: { at: NaN, lo: from, hi: to }, size, next: t };
    }
    return pick;
  };
  const sx = axis(0), sy = axis(1), out: P = [d[0] + (sx?.diff ?? 0), d[1] + (sy?.diff ?? 0)];
  const fb = moving.map((v, k) => v + out[k % 2]), guides: Guide[] = [];
  const marks = (k: 0 | 1, s: NonNullable<typeof sx>) => {
    const o = 1 - k, t = s.next!, axisOf = k === 0 ? "y" as const : "x" as const;
    guides.push({ axis: axisOf, at: (Math.max(fb[o], t[o]) + Math.min(fb[o + 2], t[o + 2])) / 2, from: s.line.lo, to: s.line.hi, gap: true });
    for (const a of boxes) {
      const after = boxes.filter((b) => b !== a && b[k] > a[k + 2] && a[o] <= b[o + 2] && b[o] <= a[o + 2]).sort((p, q) => p[k] - q[k])[0];
      if (after && Math.abs(after[k] - a[k + 2] - s.size!) < 1e-6) guides.push({ axis: axisOf, at: (Math.max(a[o], after[o]) + Math.min(a[o + 2], after[o + 2])) / 2, from: a[k + 2], to: after[k], gap: true });
    }
  };
  if (sx?.size !== undefined) marks(0, sx);
  else if (sx) guides.push({ axis: "x", at: sx.line.at, from: Math.min(fb[1], sx.line.lo) - 0.3, to: Math.max(fb[3], sx.line.hi) + 0.3 });
  if (sy?.size !== undefined) marks(1, sy);
  else if (sy) guides.push({ axis: "y", at: sy.line.at, from: Math.min(fb[0], sy.line.lo) - 0.3, to: Math.max(fb[2], sy.line.hi) + 0.3 });
  return { d: out, guides };
}
let seed = 11;
const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
for (let trial = 0; trial < 40; trial++) {
  // Chains of a few atoms, some placed exactly on others' atoms.
  let mol = EMPTY;
  for (let c = 0; c < 6; c++) { const start: P = rand() < 0.3 && mol.atoms.length ? pos(mol, Math.floor(rand() * mol.atoms.length)) : [rand() * 10, rand() * 10]; mol = merge(mol, sprout(sprout(EMPTY, [0, 0]), 1), start); }
  const ids = new Set(fragments(mol).filter(() => rand() < 0.4).flat());
  const boxes = Array.from({ length: 12 }, () => { const x = rand() * 12, y = rand() * 12; return [x, y, x + rand() * 2, y + rand() * 2]; }), moving = [1, 1, 2.5, 2];
  for (const tol of [0.05, 0.3, 1.25, 30]) for (let step = 0; step < 30; step++) {
    const d: P = [rand() * 6 - 3, rand() * 6 - 3];
    const got = snapMove(mol, ids, d, tol, { moving, targets: boxes }), atom = plainAtom(mol, ids, d, tol);
    const others = fragments(mol).some((g) => g.some((i) => !ids.has(i)));
    assert.deepEqual(got, atom ?? (ids.size && others ? plainBoxes(moving, boxes, d, tol) : others ? { d, guides: [] } : plainBoxes(moving, boxes, d, tol)), `trial ${trial}, tol ${tol}, d ${d}`);
    assert.deepEqual(snapBoxes(moving, boxes, d, tol), plainBoxes(moving, boxes, d, tol));
  }
}
// Many boxes on a grid (equal edges and middles, for ties), as a drawing of many captions has.
const grid = Array.from({ length: 300 }, (_, k) => { const x = (k % 20) * 1.5 + (k % 7) * 0.01, y = Math.floor(k / 20) * 1.2; return [x, y, x + 1 + (k % 3) * 0.25, y + 0.6]; });
for (let n = 0; n < 400; n++) {
  const d: P = [rand() * 30 - 2, rand() * 18 - 2], tol = [0.02, 0.1, 0.5][n % 3];
  assert.deepEqual(snapBoxes([0, 0, 1.25, 0.6], grid, d, tol), plainBoxes([0, 0, 1.25, 0.6], grid, d, tol), `grid, d ${d}`);
}
// Broken boxes (no number, or infinite) snap nothing, and the rest snap as before.
const broken = [[NaN, 0, 1, 1], [0, Infinity, 2, Infinity], [3, 3, 4, 4], [-Infinity, 1, 0.5, 2]];
for (const d of [[0, 0], [2.95, 2.97], [0.4, -0.1], [NaN, 1]] as P[]) assert.deepEqual(snapBoxes([0, 0, 1, 1], broken, d, 0.1), plainBoxes([0, 0, 1, 1], broken, d, 0.1), `broken boxes, d ${d}`);
// Equal spacing, as in Sam's slide (31 October 2026): three wide boxes in a column, the top two 0.5 apart. The third,
// dragged to 0.55 below the second, snaps to 0.5 below it, and both spaces are marked.
{
  const column = [[0, 10, 20, 14], [0, 5.5, 20, 9.5]], third = [0, 0, 20, 4];
  const got = snapBoxes(third, column, [0.3, 0.95], 0.1);
  assert.ok(Math.abs(got.d[1] - 1) < 1e-9, `spaced: ${got.d}`);
  const marks = got.guides.filter((g) => g.gap);
  assert.equal(marks.length, 2);
  assert.ok(marks.every((g) => g.axis === "x" && Math.abs(g.to - g.from - 0.5) < 1e-9));
  // The same across, and a box with something in line between it and the other is not spaced from it.
  const row = [[0, 0, 2, 2], [3, 0, 5, 2]];
  assert.ok(Math.abs(snapBoxes([0, 0, 2, 2], row, [6.05, 0.5], 0.1).d[0] - 6) < 1e-9);
  assert.ok(!snapBoxes([0, 0, 2, 2], [...row, [5.3, 0, 5.6, 2]], [6.05, 0.5], 0.1).guides.some((g) => g.gap));
}
console.log("snap.check: ok");
