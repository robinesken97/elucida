// Run: node src/maps.check.ts. Fails loudly if an atom map number is drawn on its atom's label, marks or bonds.
import assert from "node:assert/strict";
import { render, renderParts, type Atom, type Bond, type Drawing, type Ink, type Mol, type PartCache } from "./render.ts";

type P = [number, number];
const pt = 4 / 3;
const S = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
// Each character is 0.6 em wide and its ink 0.72 em tall (about Arial's); the outline is the box edge.
const inks = new Map<string, Ink>();
const measure = (text: string): Ink => {
  let ink = inks.get(text);
  if (!ink) {
    const w = 0.6 * S.size * text.length, a = 0.72 * S.size, outline: P[] = [];
    for (let k = 0; k <= 40; k++) { const f = k / 40; outline.push([w * f, 0], [w * f, -a], [0, -a * f], [w, -a * f]); }
    inks.set(text, (ink = { width: w, ascent: a, outline }));
  }
  return ink;
};

// A drawing from atoms (x, y in bond lengths) and bonds.
const mol = (atoms: [string, number, number, Partial<Atom>?][], bonds: [number, number, number?][]): Mol => ({
  atoms: atoms.map(([label, x, y, more]) => ({ label, location: [x, y, 0], ...more })),
  bonds: bonds.map(([a, b, type]): Bond => ({ type: type ?? 1, atoms: [a, b] })),
});
const c = Math.cos(Math.PI / 6), s = 0.5;
const ring = (n: number, cx: number, cy: number, r: number, first: string, more: Partial<Atom>) =>
  [...Array(n)].map((_, k): [string, number, number, Partial<Atom>?] => { const t = -Math.PI / 2 + (2 * Math.PI * k) / n; return [k ? "C" : first, cx + r * Math.cos(t), cy + r * Math.sin(t), k ? undefined : more]; });
const cases: Record<string, Mol> = {
  ethanol: mol([["C", 0, 0, { map: 1 }], ["C", c, s, { map: 2 }], ["O", 2 * c, 0, { map: 3 }]], [[0, 1], [1, 2]]),
  reversed: mol([["O", 0, 0, { map: 4 }], ["C", c, s], ["C", 2 * c, 0]], [[0, 1], [1, 2]]),
  acetone: mol([["C", 0, 0], ["C", c, s, { map: 8 }], ["C", 2 * c, 0], ["O", c, s + 1, { map: 7 }]], [[0, 1], [1, 2], [1, 3, 2]]),
  ammonium: mol([["C", 0, 0], ["C", c, s], ["N", 2 * c, 0, { charge: 1, map: 11 }]], [[0, 1], [1, 2]]),
  carbocation: mol([["C", 0, 0], ["C", c, s, { charge: 1, map: 13 }], ["C", 2 * c, 0]], [[0, 1], [1, 2]]),
  ether: mol([["C", 0, 0], ["O", c, s, { pairs: 2, map: 17 }], ["C", 2 * c, 0]], [[0, 1], [1, 2]]),
  chloride: mol([["C", 0, 0], ["Cl", c, -s, { map: 16 }]], [[0, 1]]),
  lone: mol([["O", 0, 0, { map: 5 }]], []),
  pyridine: (() => { const m = mol([...ring(6, 0, 0, 1, "N", { map: 9 }), ["C", 2 * c, 1]], [0, 1, 2, 3, 4, 5].map((k): [number, number, number] => [k, (k + 1) % 6, k % 2 ? 1 : 2])); m.bonds.push({ type: 1, atoms: [2, 6] }); m.atoms[2].map = 10; return m; })(),
  pyrrole: mol(ring(5, 0, 0, 0.85, "N", { map: 14 }), [0, 1, 2, 3, 4].map((k): [number, number, number] => [k, (k + 1) % 5, k === 1 || k === 3 ? 2 : 1])),
  // Every atom mapped, the fused atoms (0 and 1) on the shared bond.
  naphthalene: mol(([[0, s], [0, -s], [-c, 1], [-2 * c, s], [-2 * c, -s], [-c, -1], [c, 1], [2 * c, s], [2 * c, -s], [c, -1]] as P[]).map(([x, y], i): [string, number, number, Partial<Atom>] => ["C", x, y, { map: 20 + i }]),
    [[0, 1, 2], [0, 2], [2, 3, 2], [3, 4], [4, 5, 2], [5, 1], [0, 6], [6, 7, 2], [7, 8], [8, 9, 2], [9, 1]]),
  // A spiro atom (0): one ring above it, one below.
  spiro: mol([["C", 0, 0, { map: 40 }], ["C", -0.7, 0.7], ["C", 0, 1.4], ["C", 0.7, 0.7], ["C", -0.7, -0.7], ["C", 0, -1.4], ["C", 0.7, -0.7]], [[0, 1], [1, 2], [2, 3], [3, 0], [0, 4], [4, 5], [5, 6], [6, 0]]),
};

const L = S.bond, X = (m: Mol, i: number): P => [m.atoms[i].location[0] * L, -m.atoms[i].location[1] * L];
const boxOf = (d: Drawing, k: number) => { const n = d.maps[k], w = measure(n.text).width * (n.size / S.size); return [n.at[0] - w / 2, n.at[1] - n.h / 2, n.at[0] + w / 2, n.at[1] + n.h / 2]; };
const inside = (b: number[], [x, y]: P, pad: number) => x > b[0] - pad && x < b[2] + pad && y > b[1] - pad && y < b[3] + pad;
const overlap = (a: number[], b: number[]) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];

for (const [name, m] of Object.entries(cases)) {
  const d = render(m, S, measure, L);
  assert.deepEqual(d.maps.map((n) => n.atom), m.atoms.flatMap((a, i) => (a.map ? [i] : [])), `${name}: one number for each mapped atom`);
  d.maps.forEach((n, k) => {
    const b = boxOf(d, k), a = m.atoms[n.atom];
    assert.equal(n.text, String(a.map), `${name}: the number is the atom's map`);
    assert.ok(Math.abs(n.size - 0.75 * S.size) < 1e-9, `${name}: three quarters of the label size`);
    // Clear of every label (element, H, counts, charges) by a gap.
    for (const l of d.labels) {
      const f = l.size / S.size, g = measure(l.text);
      assert.ok(!overlap([b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1], [l.x, l.y - g.ascent * f, l.x + g.width * f, l.y]), `${name}: map ${a.map} clear of the label ${l.text}`);
    }
    // Clear of every bond line and mark (lone pairs too): no point on any polygon's edge comes into the box.
    for (const poly of d.polygons) poly.forEach((p, j) => {
      const q = poly[(j + 1) % poly.length];
      for (let t = 0; t <= 1; t += 0.05) assert.ok(!inside(b, [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t], 1), `${name}: map ${a.map} clear of the bonds and marks`);
    });
    // The atom's ink and the drawing's box hold it, so captions and export keep clear of it.
    assert.ok(inside(d.ink[n.atom], [b[0], b[1]], 1e-6) && inside(d.ink[n.atom], [b[2], b[3]], 1e-6), `${name}: the atom's ink holds map ${a.map}`);
    assert.ok(inside(d.box, [b[0], b[1]], 1e-6) && inside(d.box, [b[2], b[3]], 1e-6), `${name}: the drawing's box holds map ${a.map}`);
  });
}

// After a label that reads one way, level with the atom: OH and NH3+ to the right, HO to the left, Cl to the right.
const level = (name: string, side: 1 | -1) => {
  const m = cases[name], d = render(m, S, measure, L), k = d.maps.findIndex((x) => d.label[x.atom]), n = d.maps[k], lb = d.label[n.atom]!, b = boxOf(d, k);
  assert.ok(Math.abs(n.at[1] - X(m, n.atom)[1]) < 1e-9, `${name}: level with the atom`);
  assert.ok(side > 0 ? b[0] > lb[2] && b[0] - lb[2] < 0.3 * S.size : b[2] < lb[0] && lb[0] - b[2] < 0.3 * S.size, `${name}: just past the end of the label`);
};
level("ethanol", 1); level("reversed", -1); level("ammonium", 1); level("chloride", 1);
// A centred label or a bare carbon: out on the open side, near the atom.
{
  const at = (name: string, k = 0) => { const m = cases[name], d = render(m, S, measure, L), n = d.maps[k]; return { d: [n.at[0] - X(m, n.atom)[0], n.at[1] - X(m, n.atom)[1]] as P, n }; };
  assert.ok(at("acetone", 1).d[1] < 0 && Math.abs(at("acetone", 1).d[0]) < 1e-6, "acetone: the O's number is above the O");
  assert.ok(at("acetone").d[1] > 0 && Math.abs(at("acetone").d[0]) < 1e-6, "acetone: the C=O carbon's number is below it");
  assert.ok(at("ether").d[1] < 0, "ether: above the O, away from its bonds and past its lone pair");
  assert.ok(at("carbocation").d[1] < 0, "carbocation: above the carbon, past its +");
  assert.ok(at("pyrrole").d[1] > 0, "pyrrole: below the NH, past its H");
  for (const [name, k] of [["pyridine", 0], ["pyridine", 1], ["pyrrole", 0]] as const) {
    const { d, n } = at(name, k), m = cases[name], here = X(m, n.atom);
    assert.ok(Math.hypot(here[0] + d[0], here[1] + d[1]) > Math.hypot(...here), `${name}: map ${m.atoms[n.atom].map} out of the ring`);
  }
  for (const name of ["ethanol", "carbocation", "acetone"]) for (const n of render(cases[name], S, measure, L).maps) {
    const here = X(cases[name], n.atom);
    if (cases[name].atoms[n.atom].label !== "C" || cases[name].atoms[n.atom].charge) continue;
    assert.ok(Math.hypot(n.at[0] - here[0], n.at[1] - here[1]) < 1.2 * S.size, `${name}: map ${cases[name].atoms[n.atom].map} near its carbon`);
  }
}
// A fused or spiro atom: its number goes out of every ring, not into a gap between two bonds of one ring.
{
  const inPolygon = (q: P, poly: P[]) => poly.reduce((inside, p, k) => { const r = poly[(k + 1) % poly.length]; return (p[1] > q[1]) !== (r[1] > q[1]) && q[0] < p[0] + ((q[1] - p[1]) * (r[0] - p[0])) / (r[1] - p[1]) ? !inside : inside; }, false);
  for (const [name, rings] of [["naphthalene", [[0, 2, 3, 4, 5, 1], [0, 6, 7, 8, 9, 1]]], ["spiro", [[0, 1, 2, 3], [0, 4, 5, 6]]]] as const) {
    const m = cases[name];
    for (const n of render(m, S, measure, L).maps) for (const r of rings)
      assert.ok(!inPolygon(n.at, r.map((i) => X(m, i))), `${name}: map ${n.text} out of the ring ${r.join(" ")}`);
  }
}
// Drawn structure by structure, each number keeps its place and gets the drawing's atom number.
{
  const a = cases.ethanol, b = cases.pyridine, both: Mol = { atoms: [...a.atoms, ...b.atoms.map((x) => ({ ...x, location: [x.location[0] + 5, x.location[1], 0] as [number, number, number] }))], bonds: [...a.bonds, ...b.bonds.map((x) => ({ ...x, atoms: [x.atoms[0] + 3, x.atoms[1] + 3] as [number, number] }))] };
  const whole = render(both, S, measure, L), parts = renderParts(both, S, measure, L, { parts: new WeakMap(), last: new Map() } as PartCache);
  assert.deepEqual(parts.maps.map((n) => [n.atom, n.text, n.at.map((v) => +v.toFixed(6))]), whole.maps.map((n) => [n.atom, n.text, n.at.map((v) => +v.toFixed(6))]));
  // While a drag moves a structure, its numbers move with it.
  const cache: PartCache = { parts: new WeakMap(), last: new Map() }, before = renderParts(both, S, measure, L, cache);
  const moved: Mol = { ...both, atoms: both.atoms.map((x) => ({ ...x, location: [x.location[0] + 1, x.location[1], 0] as [number, number, number] })) };
  const during = renderParts(moved, S, measure, L, cache, false);
  assert.ok(during.parts.every((p) => p.at[0] === L), "the drag reuses each structure's drawing");
  during.maps.forEach((n, k) => assert.ok(Math.abs(n.at[0] - before.maps[k].at[0] - L) < 1e-9 && Math.abs(n.at[1] - before.maps[k].at[1]) < 1e-9, `map ${n.text} moves with its structure`));
}
console.log("maps.check: map numbers clear of labels, marks and bonds ok");
