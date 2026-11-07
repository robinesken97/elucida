// Run: node src/beside.check.ts. Fails loudly if shift numbers beside atoms cross a bond, an atom label, an atom number
// or each other on the starter drawings and the template library, or if the Spectrum panel would show a second copy of
// a number already added.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { numbered, placeBeside, type Beside, type Room, type Spot } from "./beside.ts";
import { parse } from "./file.ts";
import { LIBRARY } from "./library.ts";
import { orderOf, render, type Box, type Ink, type Mol } from "./render.ts";
import { rings } from "./rings.ts";
import { widthOf } from "./arial.ts";

type P = [number, number];
const pt = 4 / 3, L = 14.4 * pt;
const S = { bond: L, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
// Arial's advance widths and its cap height; the outline is the text's box.
const ink = (text: string): Ink => {
  const w = widthOf(text, S.size), a = 0.716 * S.size, outline: P[] = [];
  for (let k = 0; k <= 20; k++) { const f = k / 20; outline.push([w * f, 0], [w * f, -a], [0, -a * f], [w, -a * f]); }
  return { width: w, ascent: a, outline };
};
// What is round the atoms of a structure drawn at ACS 1996 (px, y down).
function roomOf(m: Mol, taken: Box[] = []): Room {
  const d = render(m, S, ink, L), bonded = m.atoms.map((): number[] => []);
  for (const b of m.bonds) { bonded[b.atoms[0]].push(b.atoms[1]); bonded[b.atoms[1]].push(b.atoms[0]); }
  const ringList = rings({ atoms: m.atoms.map(() => ({ el: "C", charge: 0, h: 0 })), bonds: m.bonds.map((b) => ({ a: b.atoms[0], b: b.atoms[1], order: 1 as const })) });
  return { at: m.atoms.map((a): P => [a.location[0] * L, -a.location[1] * L]), bonded, rings: ringList, ink: d.polygons, labels: d.label, taken };
}
// A shift number as Add to drawing writes it: Arial at 8 pt (0.8 times ACS 1996's 10 pt caption size).
const size = 8 * pt;
const number = (atom: number, text: string): Beside => ({ atom, w: widthOf(text, size), up: 0.716 * size, down: text.includes(",") ? 0.147 * size : 0, L });

// What a box crosses (half a px of slack): bond ink, atom labels, the marks given, and the other boxes.
const meets = (a: Box, b: Box) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
function cuts(a: P, b: P, x: Box) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  let t0 = 0, t1 = 1;
  for (const [p, q] of [[-dx, a[0] - x[0]], [dx, x[2] - a[0]], [-dy, a[1] - x[1]], [dy, x[3] - a[1]]]) {
    if (p === 0) { if (q < 0) return false; continue; }
    const r = q / p;
    if (p < 0) t0 = Math.max(t0, r); else t1 = Math.min(t1, r);
    if (t0 >= t1) return false;
  }
  return true;
}
function crossings(room: Room, spots: Spot[]) {
  const out = { bonds: 0, labels: 0, marks: 0, numbers: 0 };
  spots.forEach((s, k) => {
    const b: Box = [s.box[0] + 0.5, s.box[1] + 0.5, s.box[2] - 0.5, s.box[3] - 0.5];
    if (room.ink.some((poly) => poly.some((p, j) => cuts(p, poly[(j + 1) % poly.length], b)))) out.bonds++;
    if (room.labels.some((l) => l && meets(l, b))) out.labels++;
    if (room.taken.some((t) => meets(t, b))) out.marks++;
    if (spots.some((o, j) => j !== k && meets(o.box, b))) out.numbers++;
  });
  return out;
}
// Each carbon's numbers: ¹³C on every carbon ("128.5", as long as most), ¹H on every carbon with a hydrogen.
const carbons = (m: Mol) => m.atoms.flatMap((a, i) => (a.label === "C" ? [i] : []));
const withH = (m: Mol) => carbons(m).filter((i) => m.bonds.filter((b) => b.atoms.includes(i)).reduce((s, b) => s + orderOf(b.type), 0) < 4);

// The corpus: the three starter drawings and the first structures of each template set, 50 in all.
const starters = ["structure", "reaction", "cycle"].map((n) => parse(readFileSync(new URL(`./starters/${n}.json`, import.meta.url), "utf8")));
const sets = LIBRARY.map((c) => c.items.map((t) => t.mol).filter((m) => m.atoms.some((a) => a.label === "C") && m.bonds.length && !m.atoms.some((a) => a.location[2])));
const corpus = [...starters];
for (let k = 0; corpus.length < 50; k++) for (const s of sets) if (s[k] && corpus.length < 50) corpus.push(s[k]);
assert.equal(corpus.length, 50);
// The clear gap between two numbers, and between a number and an atom label: at least about a word space at 8 pt
// (0.15 bond lengths, 2.9 px), more than the air kept against bonds (0.06 bond lengths), so two numbers never read as one.
const GAP = 0.15 * L, AIR = 0.06 * L;
const gap = (a: Box, b: Box) => Math.max(a[0] - b[2], b[0] - a[2], a[1] - b[3], b[1] - a[3]);
function gaps(room: Room, spots: Spot[]) {
  let numbers = Infinity, labels = Infinity;
  spots.forEach((s, k) => {
    spots.forEach((o, j) => { if (j > k) numbers = Math.min(numbers, gap(s.box, o.box)); });
    for (const l of room.labels) if (l) labels = Math.min(labels, gap(s.box, l));
  });
  return { numbers, labels };
}
let placed = 0;
for (const m of corpus) {
  const room = roomOf(m);
  for (const items of [carbons(m).map((i) => number(i, "128.5")), withH(m).map((i) => number(i, "2.42"))]) {
    const spots = placeBeside(items, room);
    assert.equal(spots.length, items.length);
    assert.deepEqual(crossings(room, spots), { bonds: 0, labels: 0, marks: 0, numbers: 0 }, `${m.atoms.length} atoms: a number crosses`);
    const g = gaps(room, spots);
    assert.ok(g.numbers >= GAP - 1e-6 && g.labels >= GAP - 1e-6, `${m.atoms.length} atoms: numbers ${g.numbers.toFixed(2)} px apart, ${g.labels.toFixed(2)} px from a label`);
    placed += spots.length;
  }
}
assert.ok(GAP > AIR);

// Ferrocene and acetylferrocene, ¹H and ¹³C, as the predictions put them (nmrmetal.check.ts): the numbers on the
// squashed Cp rings keep the gap from each other and from Fe, and cross nothing.
const fc = LIBRARY.flatMap((c) => c.items).find((t) => t.name === "Ferrocene")!.mol, fcN = fc.atoms.length, [ax, ay] = fc.atoms[2].location;
const acFc: Mol = {
  ...fc,
  atoms: [...fc.atoms, { label: "C", location: [ax, ay - 1, 0] }, { label: "O", location: [ax + 0.87, ay - 1.5, 0] }, { label: "C", location: [ax - 0.87, ay - 1.5, 0] }],
  bonds: [...fc.bonds, { type: 1, atoms: [2, fcN] }, { type: 2, atoms: [fcN, fcN + 1] }, { type: 1, atoms: [fcN, fcN + 2] }],
};
const cp = [2, 3, 4, 5, 6, 8, 9, 10, 11, 12], bare = [8, 9, 10, 11, 12];
for (const [what, m, list] of [
  ["ferrocene ¹H", fc, cp.map((i) => [i, "4.16"])],
  ["ferrocene ¹³C", fc, cp.map((i) => [i, "67.8"])],
  ["acetylferrocene ¹H", acFc, [[3, "4.77"], [6, "4.77"], [4, "4.50"], [5, "4.50"], ...bare.map((i) => [i, "4.20"]), [fcN + 2, "2.39"]]],
  ["acetylferrocene ¹³C", acFc, [[2, "79.2"], [3, "72.3"], [6, "72.3"], [4, "69.8"], [5, "69.8"], ...bare.map((i) => [i, "69.5"]), [fcN, "202.0"], [fcN + 2, "27.4"]]],
] as [string, Mol, [number, string][]][]) {
  assert.equal(m.atoms[0].label, "Fe");
  const room = roomOf(m), spots = placeBeside(list.map(([i, t]) => number(i, t)), room), g = gaps(room, spots);
  assert.equal(spots.length, list.length);
  assert.deepEqual(crossings(room, spots), { bonds: 0, labels: 0, marks: 0, numbers: 0 }, `${what}: a number crosses`);
  assert.ok(g.numbers >= GAP - 1e-6, `${what}: numbers ${g.numbers.toFixed(2)} px apart`);
  assert.ok(g.labels >= GAP - 1e-6, `${what}: a number ${g.labels.toFixed(2)} px from Fe`);
}
assert.ok(placed > 600, "the corpus places hundreds of numbers");
// With atom numbers shown first (a number beside every atom), the shift numbers clear them too. Where one cannot (no
// place within 1.5 bond lengths is clear of everything else), it takes the least overlap: 1 of these 50 structures.
let crowded = 0;
for (const m of corpus) {
  const numbers = placeBeside(m.atoms.map((_, i) => number(i, String(i + 1))), roomOf(m)), room = roomOf(m, numbers.map((s) => s.box));
  const spots = placeBeside(carbons(m).map((i) => number(i, "128.5")), room);
  spots.forEach((s, k) => {
    const others = { ...room, taken: [...room.taken, ...spots.filter((_, j) => j !== k).map((o) => o.box)] };
    if (Object.values(crossings(others, [s])).some(Boolean)) {
      crowded++;
      assert.ok(Object.values(crossings(others, placeBeside([number(s.atom, "128.5")], others))).some(Boolean), `${m.atoms.length} atoms: atom ${s.atom} crosses where a clear place was free`);
    }
  });
}
assert.ok(crowded <= 1, `${crowded} shift numbers cross an atom number`);

// "205.2" on a branch carbon with bonds at 30°, 150° and 270° sits in a gap and clears both of its bonds.
const branch: Mol = { atoms: [[0, 0], [Math.cos(Math.PI / 6), 0.5], [-Math.cos(Math.PI / 6), 0.5], [0, -1]].map(([x, y]) => ({ label: "C", location: [x, y, 0] as [number, number, number] })), bonds: [1, 2, 3].map((k) => ({ type: 1, atoms: [0, k] as [number, number] })) };
const branchRoom = roomOf(branch), [top] = placeBeside([number(0, "205.2")], branchRoom);
assert.deepEqual(crossings(branchRoom, [top]), { bonds: 0, labels: 0, marks: 0, numbers: 0 });
const mid = Math.atan2(-(top.box[1] + top.box[3]) / 2, (top.box[0] + top.box[2]) / 2) * (180 / Math.PI);
assert.ok([30, 150, 270, -90].every((a) => Math.abs(((mid - a + 540) % 360) - 180) > 30), "in a gap, off its bonds");
assert.ok(Math.hypot(Math.max(top.box[0], 0, -top.box[2]), Math.max(top.box[1], 0, -top.box[3])) < 0.75 * L, "and close to its atom");
const middle: P = [(top.box[0] + top.box[2]) / 2, (top.box[1] + top.box[3]) / 2], from = (q: P) => Math.hypot(middle[0] - q[0], middle[1] - q[1]);
assert.ok(branchRoom.at.slice(1).every((q) => from(q!) > from(branchRoom.at[0]!)), "nearer its own atom than the others");

// Atom numbers and (R) and (S) placed first are kept clear of: a mark where the number would go moves the number.
const mark: Box = [top.box[0], top.box[1], top.box[2], top.box[3]], [moved] = placeBeside([number(0, "205.2")], { ...branchRoom, taken: [mark] });
assert.deepEqual(crossings({ ...branchRoom, taken: [mark] }, [moved]), { bonds: 0, labels: 0, marks: 0, numbers: 0 });

// Atoms with least room go first, and the order the numbers come in does not change where they go.
const ring = corpus[3], ringRoom = roomOf(ring), list = carbons(ring).map((i) => number(i, "128.5"));
assert.deepEqual(placeBeside([...list].reverse(), ringRoom).sort((p, q) => p.atom - q.atom), placeBeside(list, ringRoom).sort((p, q) => p.atom - q.atom));

// Add to drawing, then the overlay: each atom with an added number (text of numbers within 1.5 bond lengths, nearest
// it) has one, so the panel draws no second copy. Other text near an atom does not count.
for (const m of corpus.slice(0, 20)) {
  const room = roomOf(m), list = carbons(m).map((i) => number(i, String(100 + i) + ".5")), spots = placeBeside(list, room);
  const want = new Map(list.map((t) => [t.atom, `${100 + t.atom}.5`]));
  const has = numbered(room.at, room.at.map(() => L), spots.map((s) => ({ text: want.get(s.atom)!, box: s.box })), want);
  assert.deepEqual([...has].sort((p, q) => p - q), list.map((t) => t.atom).sort((p, q) => p - q));
}
assert.equal(numbered(branchRoom.at, branchRoom.at.map(() => L), [{ text: "Me", box: top.box }]).size, 0, "text that is not a number");
assert.equal(numbered(branchRoom.at, branchRoom.at.map(() => L), [{ text: "205.2", box: [top.box[0], top.box[1] - 3 * L, top.box[2], top.box[3] - 3 * L] }]).size, 0, "a number far from every atom");
assert.deepEqual([...numbered(branchRoom.at, branchRoom.at.map(() => L), [{ text: "1.02, 0.98", box: top.box }])], [0], "two shifts with a comma");
// ¹³C numbers added to the page do not hide the ¹H ones (and the other way round).
assert.equal(numbered(branchRoom.at, branchRoom.at.map(() => L), [{ text: "205.2", box: top.box }], new Map([[0, "2.42"]])).size, 0, "a ¹³C number is not a ¹H one");
assert.deepEqual([...numbered(branchRoom.at, branchRoom.at.map(() => L), [{ text: "205.1", box: top.box }], new Map([[0, "205.2"]]))], [0], "a ¹³C number from another prediction");

// Speed: a 60-atom structure's numbers in well under a frame.
const big = corpus.reduce((p, q) => (q.atoms.length > p.atoms.length ? q : p)), bigRoom = roomOf(big), bigList = carbons(big).map((i) => number(i, "128.5"));
const t0 = performance.now();
for (let k = 0; k < 10; k++) placeBeside(bigList, bigRoom);
assert.ok((performance.now() - t0) / 10 < 30, `${big.atoms.length} atoms place in under 30 ms`);
console.log("beside.check: ok");
