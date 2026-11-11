// Run: node src/perf.check.ts (it also runs with the other checks:
//   for f in src/*.check.ts; do node "$f" >/dev/null 2>&1 || echo "FAIL $f"; done).
// Fails when an operation on a large drawing gets slow, so a slow-down shows before a release. The drawing is made
// here: a grid of rings with labelled side groups, wedges and chains, about 1000 atoms (the size of a busy page).
// Two tests for each operation:
// - Budget: its time on the large drawing is under a budget in ms. The budgets are about 10 times the times on Sam's
//   Mac (node 24, Apple silicon), so a slower computer passes and a much slower operation fails.
// - Growth: on a drawing 4 times as large it takes less than 10 times as long. An operation that grows with the size
//   takes about 4 to 6 times as long; one that grows with the square of the size (a loop over pairs) takes about 16
//   times, on any computer.
// This checks the code that the editor runs, without the window. Before a release, also measure the app itself in
// headless Chrome with a 4x CPU slow-down (Sam's bench: ~/octet-research/tools/perf/bench.mjs).
import assert from "node:assert/strict";
import { atomsIn, bondOrders, complete, fragments, groupSelection } from "./edit.ts";
import { messy, problems } from "./check.ts";
import { render, type Ink, type Mol } from "./render.ts";
import { toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { parse, serialize } from "./file.ts";

type P = [number, number];
// n benzene rings in a square grid, 4 bond lengths apart. Each has a side group (an atom label, or a group such as
// OMe or CO2H) and every third has a chain of two with a wedge and a hashed wedge.
function drawing(n: number): Mol {
  const atoms: Mol["atoms"] = [], bonds: Mol["bonds"] = [], cols = Math.ceil(Math.sqrt(n));
  const sides: [string, string?][] = [["O"], ["N"], ["Cl"], ["C", "OMe"], ["C", "CO2H"], ["S"], ["F"], ["N", "NH2"]];
  const add = (label: string, x: number, y: number, text?: string) => atoms.push({ label, location: [x, y, 0], ...(text ? { text } : {}) }) - 1;
  for (let r = 0; r < n; r++) {
    const cx = (r % cols) * 4, cy = Math.floor(r / cols) * 4, base = atoms.length;
    for (let i = 0; i < 6; i++) add("C", cx + Math.cos((Math.PI / 3) * i + Math.PI / 6), cy + Math.sin((Math.PI / 3) * i + Math.PI / 6));
    for (let i = 0; i < 6; i++) bonds.push({ type: i % 2 ? 1 : 2, atoms: [base + i, base + ((i + 1) % 6)] });
    const [label, text] = sides[r % sides.length], a = Math.PI / 6;
    bonds.push({ type: 1, atoms: [base, add(label, cx + 2 * Math.cos(a), cy + 2 * Math.sin(a), text)] });
    if (r % 3 === 0) {
      const b = (7 * Math.PI) / 6, c1 = add("C", cx + 2 * Math.cos(b), cy + 2 * Math.sin(b)), c2 = add("C", cx + 2 * Math.cos(b) - 0.87, cy + 2 * Math.sin(b) + 0.5);
      bonds.push({ type: 1, stereo: 1, atoms: [base + 3, c1] }, { type: 1, stereo: 6, atoms: [c1, c2] });
    }
  }
  return { atoms, bonds };
}

// The renderer's measurer, as in render.check.ts: every glyph is a box with its edge as the outline.
const pt = 4 / 3, S = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
const box: P[] = [];
for (let i = 0; i <= 40; i++) { const f = i / 40; box.push([9.6 * f, 0], [9.6 * f, -9.5], [0, -9.5 * f], [9.6, -9.5 * f]); }
const ink = (text: string): Ink => ({ width: 9.6 * text.length, ascent: 9.5, outline: box });

// The time of one call (ms): the best of 3 batches, each of at least 15 ms, so a pause for garbage collection or
// another program does not fail the check.
function time(f: () => unknown): number {
  f();
  let best = Infinity;
  for (let k = 0; k < 3; k++) {
    let n = 0;
    const t0 = performance.now();
    do { f(); n++; } while (performance.now() - t0 < 15);
    best = Math.min(best, (performance.now() - t0) / n);
  }
  return best;
}

// What each operation is (for the editor), its budget in ms on the large drawing, and how to run it on a drawing.
const OPS: [string, number, (m: Mol, all: Set<number>, half: Set<number>, text: string) => unknown][] = [
  ["render (each change to the structures)", 50, (m) => render(m, S, ink, S.bond)],
  ["complete (each move of a selection box)", 1, (m, _, half) => complete(m, half)],
  ["messy, nothing selected (each change)", 10, (m) => messy(m, new Set())],
  ["messy, all selected (each selection)", 10, (m, all) => messy(m, all)],
  ["groupSelection (Group)", 4, (m, all) => groupSelection(m, all, new Set())],
  ["fragments (structures)", 1, (m) => fragments(m)],
  ["problems (chemical warnings)", 3, (m) => problems(m)],
  ["bondOrders", 0.3, (m) => bondOrders(m)],
  ["atomsIn (atoms in a selection box)", 0.3, (m) => atomsIn(m, [-1, -1], [30, 30])],
  ["toCdxml (Save, Export, Copy)", 50, (m) => toCdxml(m, DEFAULT_STYLE)],
  ["serialize (Octet's own form)", 5, (m) => serialize(m)],
  ["parse (Paste, Open)", 5, (_m, _a, _h, text) => parse(text)],
];

const sized = (rings: number) => {
  const m = drawing(rings), all = new Set(m.atoms.map((_, i) => i));
  return { m, all, half: new Set([...all].filter((i) => i % 2 === 0)), text: serialize(m) };
};
const large = sized(128), larger = sized(512);
console.log(`perf.check: ${large.m.atoms.length} atoms, then ${larger.m.atoms.length}`);
const slow: string[] = [];
for (const [what, budget, op] of OPS) {
  const run = (d: typeof large) => () => op(d.m, d.all, d.half, d.text);
  // Other programs on a busy computer can slow one measurement. When a test fails, measure again (3 times at most)
  // and keep the best time for each size. A slow operation fails each time.
  let t = Infinity, t4 = Infinity;
  for (let k = 0; k < 3 && (t > budget || t4 / t > 10); k++) { t = Math.min(t, time(run(large))); t4 = Math.min(t4, time(run(larger))); }
  const growth = t4 / t;
  console.log(`  ${what.padEnd(44)} ${t.toFixed(3).padStart(8)} ms (budget ${budget}), x${growth.toFixed(1)} at 4 times the size`);
  if (t > budget) slow.push(`${what} takes ${t.toFixed(2)} ms, over its budget of ${budget} ms`);
  if (growth > 10) slow.push(`${what} takes ${growth.toFixed(1)} times as long on a drawing 4 times as large`);
}
assert.deepEqual(slow, [], slow.join("\n"));
console.log("perf.check: ok");
