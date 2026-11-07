// Run: node src/bondchain.check.ts. Fails loudly if the bond and chain tools stop acting as ChemDraw's do.
import assert from "node:assert/strict";
import { EMPTY, addChain, chainPoints, chainTo, clickBond, dragBond, jumpHot, keyBond, merge, nextSide, pos, setBondSpec, snake, sprout, type BondSpec, type P } from "./edit.ts";
import { QUADRUPLE, type Mol } from "./render.ts";
import { BONDS } from "./kinds.ts";

const SOLID: BondSpec = { type: 1 }, BOLD: BondSpec = { type: 1, display: "bold" }, DASHED: BondSpec = { type: 1, display: "dashed" };
const WAVY: BondSpec = { type: 1, display: "wavy" }, WEDGE: BondSpec = { type: 1, stereo: 1 }, DOUBLE: BondSpec = { type: 2 };
const kind = (m: Mol, k = 0) => { const b = m.bonds[k]; return `${b.type}${b.stereo ? "s" + b.stereo : ""}${b.display ? " " + b.display : ""}${b.position ? " " + b.position : ""}`; };
const mid = (m: Mol, k = 0): P => { const [a, b] = m.bonds[k].atoms.map((i) => pos(m, i)); return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; };
const angleAt = (m: Mol, i: number, j: number, k: number) => {
  const a = pos(m, j), u = [pos(m, i)[0] - a[0], pos(m, i)[1] - a[1]], v = [pos(m, k)[0] - a[0], pos(m, k)[1] - a[1]];
  return Math.round((Math.acos((u[0] * v[0] + u[1] * v[1]) / Math.hypot(u[0], u[1]) / Math.hypot(v[0], v[1])) * 180) / Math.PI);
};

// CORE-10: the Solid tool makes a single bond double; later clicks move the second line round its three places;
// a triple bond goes back to single.
const ethane = sprout(EMPTY, [0, 0]);
let m = clickBond(ethane, 0, SOLID, mid(ethane));
assert.equal(kind(m), "2");
// A bond drawn up and to the right, its second line drawn on the right: then centre, then left, then right.
m = clickBond(m, 0, SOLID, mid(m), 1); assert.equal(kind(m), "2 centre");
m = clickBond(m, 0, SOLID, mid(m), 0); assert.equal(kind(m), "2 left");
m = clickBond(m, 0, SOLID, mid(m), -1); assert.equal(kind(m), "2 right");
// The same bond drawn the other way round goes round the other way, so it looks the same on screen.
const back: Mol = { ...ethane, bonds: [{ type: 2, atoms: [1, 0] }] };
assert.equal(nextSide(back, 0, -1), "centre");
assert.equal(nextSide(back, 0, 0), "right");
assert.equal(clickBond({ ...ethane, bonds: [{ type: 3, atoms: [0, 1] }] }, 0, SOLID, mid(ethane)).bonds[0].type, 1);
console.log("bondchain.check: single tool ok");

// CORE-12: style tools keep a double bond double.
const dbl = clickBond(ethane, 0, SOLID, mid(ethane));
assert.equal(kind(clickBond(dbl, 0, BOLD, mid(dbl))), "2 bold");
assert.equal(kind(clickBond(dbl, 0, DASHED, mid(dbl))), "2 dashed");
assert.equal(kind(clickBond(clickBond(dbl, 0, DASHED, mid(dbl)), 0, DASHED, mid(dbl))), "2 aromatic");
assert.equal(kind(clickBond(clickBond(dbl, 0, BOLD, mid(dbl)), 0, SOLID, mid(dbl))), "2");
// The style stays on the side it was, and a second click with the same style moves the line.
const leftBold = clickBond({ ...dbl, bonds: [{ ...dbl.bonds[0], position: "left" }] }, 0, BOLD, mid(dbl));
assert.equal(kind(leftBold), "2 bold left");
assert.equal(kind(clickBond(leftBold, 0, BOLD, mid(dbl), -1)), "2 bold right");
// Wavy: a wavy bond, then a double bond, then a double either.
m = clickBond(ethane, 0, WAVY, mid(ethane)); assert.equal(kind(m), "1 wavy");
m = clickBond(m, 0, WAVY, mid(m)); assert.equal(kind(m), "2");
m = clickBond(m, 0, WAVY, mid(m)); assert.equal(kind(m), "2 either");
// The Double tool moves the second line of a double bond; a wedge tool leaves it as it is.
assert.equal(kind(clickBond(dbl, 0, DOUBLE, mid(dbl), 0)), "2 left");
assert.equal(clickBond(dbl, 0, WEDGE, mid(dbl)), dbl);
// A bold single bond clicked with Bold becomes a bold double; a dashed one with Dashed a dashed double.
assert.equal(kind(clickBond(clickBond(ethane, 0, BOLD, mid(ethane)), 0, BOLD, mid(ethane))), "2 bold");
assert.equal(kind(clickBond(clickBond(ethane, 0, DASHED, mid(ethane)), 0, DASHED, mid(ethane))), "2 dashed");
console.log("bondchain.check: style tools ok");

// CORE-14: the wide end of a wedge goes on the half of the bond clicked (atoms with as many bonds), else the narrow
// end goes on the atom with more bonds. A second click turns it round.
const near = (m: Mol, k: number, t: number): P => { const [a, b] = m.bonds[k].atoms.map((i) => pos(m, i)); return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; };
m = clickBond(ethane, 0, WEDGE, near(ethane, 0, 0.62));
assert.deepEqual(m.bonds[0].atoms, [0, 1], "wide end at atom 1, nearer the click");
m = clickBond(ethane, 0, WEDGE, near(ethane, 0, 0.38));
assert.deepEqual(m.bonds[0].atoms, [1, 0], "wide end at atom 0, nearer the click");
assert.deepEqual(clickBond(m, 0, WEDGE, near(m, 0, 0.5)).bonds[0].atoms, [0, 1]);
const propane = sprout(ethane, 1);
assert.deepEqual(clickBond(propane, 0, WEDGE, near(propane, 0, 0.9)).bonds[0].atoms, [1, 0], "narrow end on the atom with more bonds");
console.log("bondchain.check: wedge ok");

// Issue #10: the w and h keys over a bond act as a click with the Wedge or Hashed Wedge tool. On a bond already that
// wedge they turn it round; on another bond the wedge points as a click would. Other bond keys only set the style.
const HASHWEDGE: BondSpec = { type: 1, stereo: 6 };
assert.equal(kind(keyBond(ethane, 0, WEDGE)), "1s1");
assert.deepEqual(keyBond(ethane, 0, WEDGE, near(ethane, 0, 0.62)).bonds[0].atoms, [0, 1], "wide end nearer the pointer");
m = keyBond(ethane, 0, WEDGE, near(ethane, 0, 0.38));
assert.deepEqual(m.bonds[0].atoms, [1, 0]);
assert.deepEqual(keyBond(m, 0, WEDGE).bonds[0].atoms, [0, 1], "w over a wedge turns it round");
assert.deepEqual(keyBond(keyBond(m, 0, WEDGE), 0, WEDGE).bonds[0].atoms, [1, 0]);
m = keyBond(ethane, 0, HASHWEDGE, near(ethane, 0, 0.38));
assert.equal(kind(m), "1s6");
assert.deepEqual(keyBond(m, 0, HASHWEDGE).bonds[0].atoms, [0, 1], "h over a hashed wedge turns it round");
m = keyBond(ethane, 0, WEDGE, near(ethane, 0, 0.38));
const hashed = keyBond(m, 0, HASHWEDGE, near(ethane, 0, 0.62));
assert.equal(kind(hashed), "1s6");
assert.deepEqual(hashed.bonds[0].atoms, [0, 1], "a new style is pointed, not turned round");
assert.deepEqual(keyBond(propane, 0, WEDGE).bonds[0].atoms, [1, 0], "narrow end on the atom with more bonds");
// With no pointer (the keyboard hotspot, a selection) a tie keeps the drawn order, wherever the bond lies.
const offGrid: Mol = { ...ethane, atoms: [{ ...ethane.atoms[0], location: [0.1, 0.2, 0] }, { ...ethane.atoms[1], location: [0.7, 0.3, 0] }] };
assert.deepEqual(keyBond(offGrid, 0, WEDGE).bonds[0].atoms, [0, 1], "no pointer keeps the order");
assert.deepEqual(keyBond(offGrid, 0, HASHWEDGE).bonds[0].atoms, [0, 1]);
const bold = setBondSpec(ethane, 0, BOLD);
assert.deepEqual(keyBond(bold, 0, BOLD), setBondSpec(bold, 0, BOLD), "b over a bold bond keeps it bold");
assert.deepEqual(keyBond(ethane, 0, SOLID), setBondSpec(ethane, 0, SOLID));
// A wedge click or key keeps the bond's colour.
const coloured: Mol = { ...ethane, bonds: [{ ...ethane.bonds[0], colour: "#c00000" }] };
assert.equal(clickBond(coloured, 0, WEDGE, mid(coloured)).bonds[0].colour, "#c00000");
assert.equal(keyBond(coloured, 0, WEDGE).bonds[0].colour, "#c00000");
// Every bond kind with a narrow end: a key and a click with its tool do the same to a single bond, a bond of another
// kind and a bond already of that kind (turned round), wherever the pointer is.
for (const k of ["wedge", "hashwedge", "hollow", "dative"] as const) {
  const spec = BONDS[k].spec;
  for (const start of [ethane, propane, setBondSpec(ethane, 0, BOLD), setBondSpec(ethane, 0, HASHWEDGE), setBondSpec(ethane, 0, { type: 3 })])
    for (const t of [0.2, 0.5, 0.8]) {
      let byKey = start, byClick = start;
      for (let n = 0; n < 3; n++) {
        byKey = keyBond(byKey, 0, spec, near(start, 0, t)); byClick = clickBond(byClick, 0, spec, near(start, 0, t));
        assert.deepEqual(byKey, byClick, `${k} key and click, press ${n + 1}`);
      }
    }
  const once = keyBond(ethane, 0, spec, near(ethane, 0, 0.38));
  assert.deepEqual(once.bonds[0].atoms, [1, 0], `${k} key near atom 0`);
  assert.deepEqual(keyBond(once, 0, spec).bonds[0].atoms, [...once.bonds[0].atoms].reverse(), `${k} key over its own kind turns it round`);
}
console.log("bondchain.check: wedge keys ok");

// CORE-15: a bond from an atom whose label runs to the right (CO2Me) is not hidden under that label.
for (const text of [1, -1]) {
  const m = sprout(ethane, 1, SOLID, text), d = [pos(m, 2)[0] - pos(m, 1)[0], pos(m, 2)[1] - pos(m, 1)[1]];
  assert.ok(d[0] * text <= 0.5 + 1e-9, `bond clear of a label running ${text > 0 ? "right" : "left"}`);
}
const lone: Mol = { atoms: [{ label: "O", text: "OH", location: [0, 0, 0] }], bonds: [] };
assert.ok(pos(sprout(lone, 0, SOLID, 1), 1)[0] < 0, "a lone label's first bond goes the other way");
console.log("bondchain.check: bonds clear of labels ok");

// CORE-11: a bond drawn over a bond raises its order, as ChemDraw's: up to quadruple, then back to single.
m = dragBond(ethane, 0, pos(ethane, 1)); assert.equal(kind(m), "2");
m = dragBond(m, 0, pos(m, 1)); assert.equal(kind(m), "3");
m = dragBond(m, 0, pos(m, 1)); assert.equal(kind(m), String(QUADRUPLE), "a drag along a triple bond makes it quadruple");
m = dragBond(m, 1, pos(m, 0)); assert.equal(kind(m), "1");
assert.equal(kind(dragBond(ethane, 0, pos(ethane, 1), BOLD)), "2 bold");
assert.equal(kind(dragBond(clickBond(ethane, 0, DASHED, mid(ethane)), 0, pos(ethane, 1), DASHED)), "2 aromatic");
assert.equal(dragBond(ethane, 0, [3, 3]).bonds.length, 2, "a drag elsewhere still adds a bond");
console.log("bondchain.check: bond over bond ok");

// CORE-17: a chain from an atom with bonds keeps 120° at that atom and all along, whichever way it is dragged.
for (const t of [0, -30, 30, 60, 90, -90, 180]) {
  const q: P = [pos(ethane, 1)[0] + 4 * Math.cos((t * Math.PI) / 180), pos(ethane, 1)[1] + 4 * Math.sin((t * Math.PI) / 180)];
  const { mol, bonds } = chainTo(ethane, 1, q);
  assert.ok(bonds >= 4);
  assert.equal(angleAt(mol, 0, 1, 2), 120, `angle at the start atom for a drag at ${t}°`);
  for (let i = 2; i < mol.atoms.length - 1; i++) assert.equal(angleAt(mol, i - 1, i, i + 1), 120);
}
// Straight on from a chain end, the chain carries on the same zig-zag.
const butane = chainTo(EMPTY, [0, 0], [3 * Math.cos(Math.PI / 6), 0]).mol, end = butane.atoms.length - 1;
const longer = chainTo(butane, end, [pos(butane, end)[0] + 3, pos(butane, end)[1]]).mol;
for (let i = 1; i < longer.atoms.length - 1; i++) assert.equal(angleAt(longer, i - 1, i, i + 1), 120);
assert.ok(longer.atoms.every((a, i) => i === 0 || Math.abs(a.location[1] - longer.atoms[i - 1].location[1]) > 0.4), "one zig-zag along the line");
console.log("bondchain.check: chain from an atom ok");

// CORE-18: on empty canvas the first bond goes to the pointer's side of the drag.
const up = chainPoints(EMPTY, [0, 0], [4, 0], 1), down = chainPoints(EMPTY, [0, 0], [4, 0], -1);
assert.ok(up[0][1] > 0 && down[0][1] < 0);
// Add Chain: n atoms from a point, n new atoms from an atom, zig-zag.
const five = addChain(EMPTY, [0, 0], 5);
assert.equal(five.mol.atoms.length, 5);
assert.equal(five.mol.bonds.length, 4);
assert.equal(five.last, 4);
for (let i = 1; i < 4; i++) assert.equal(angleAt(five.mol, i - 1, i, i + 1), 120);
const attached = addChain(ethane, 1, 3);
assert.equal(attached.mol.atoms.length, 5);
assert.equal(angleAt(attached.mol, 0, 1, 2), 120);
// The Snaking Chain follows the pointer: on, then back.
let path = snake([0, 0], [[Math.cos(Math.PI / 6), 0.5]], [4, 0]);
assert.ok(path.length >= 4);
const sm = (pts: P[]) => ({ atoms: [[0, 0] as P, ...pts].map((q) => ({ label: "C", location: [q[0], q[1], 0] as [number, number, number] })), bonds: pts.map((_, k) => ({ type: 1, atoms: [k, k + 1] as [number, number] })) });
for (let i = 1; i < path.length; i++) assert.equal(angleAt(sm(path), i - 1, i, i + 1), 120);
path = snake([0, 0], path, [4, 4]);
const turned = path.length;
path = snake([0, 0], path, [0.9, 0.5]);
assert.ok(path.length < turned && path.length >= 1, "going back takes atoms off");
console.log("bondchain.check: chain tool ok");

// CORE-16: Shift+Option+arrow moves the hotspot to the nearest atom of another structure that way, round past the edge.
const pair = merge(merge(ethane, ethane, [4, 0]), ethane, [-8, 0]);
assert.equal(jumpHot(pair, { atom: 1 }, [1, 0], true).atom, 2);
assert.equal(jumpHot(pair, { atom: 1 }, [-1, 0], true).atom! >= 4, true, "to the structure on the left");
assert.deepEqual(jumpHot(ethane, { atom: 1 }, [1, 0], true), { atom: 1 }, "no other structure: it stays");
console.log("bondchain.check: hotspot to the next structure ok");

// The document's chain angle (ChemDraw's Chain Angle): every angle of a dragged or snaking chain is that angle.
{
  const angleAt = (a: P, b: P, c: P) => Math.round((Math.acos(((a[0] - b[0]) * (c[0] - b[0]) + (a[1] - b[1]) * (c[1] - b[1])) / (Math.hypot(a[0] - b[0], a[1] - b[1]) * Math.hypot(c[0] - b[0], c[1] - b[1]))) * 180) / Math.PI);
  for (const angle of [120, 110, 135]) {
    const pts = [[0, 0] as P, ...chainPoints(EMPTY, [0, 0], [5, 0], 1, angle)];
    for (let k = 1; k + 1 < pts.length; k++) assert.equal(angleAt(pts[k - 1], pts[k], pts[k + 1]), angle, `chain angle ${angle}`);
    for (let k = 1; k < pts.length; k++) assert.ok(Math.abs(Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]) - 1) < 1e-9, "unit bonds");
    const s = snake([0, 0], [[Math.cos(0.3), Math.sin(0.3)]], [6, 0], angle), all = [[0, 0] as P, ...s];
    for (let k = 1; k + 1 < all.length; k++) assert.equal(angleAt(all[k - 1], all[k], all[k + 1]), angle, `snake angle ${angle}`);
  }
  // From a chain end, the first bond is at the chain angle to the bond there.
  const end = sprout(EMPTY, [0, 0]), first = chainPoints(end, 1, [5, 3], 1, 110)[0];
  assert.equal(angleAt(pos(end, 0), pos(end, 1), first), 110);
  console.log("bondchain.check: chain angle ok");
}

// Issue 35: off a ring atom of a chair cyclohexane the first new bond is axial (upright, away from the atom's two ring
// neighbours, so up and down in turn round the ring) and the second equatorial (parallel to the ring bonds once
// removed, out of the ring). Each of the six atoms of the Ring tool's two chairs, the same turned, and the Conformers
// templates' chairs drawn with depth, where the new atom's depth must be the template's own axial or equatorial H's.
{
  const { addChair, addRing, neighbours } = await import("./edit.ts");
  const { readFileSync } = await import("node:fs");
  const library = JSON.parse(readFileSync(new URL("library.json", import.meta.url), "utf8")) as { name: string; items: { name: string; mol: Mol }[] }[];
  const template = (name: string) => library.find((s) => s.name === "Conformers")!.items.find((t) => t.name === name)!.mol;
  const unitOf = (v: P): P => { const l = Math.hypot(v[0], v[1]); return [v[0] / l, v[1] / l]; };
  const way = (m: Mol, i: number, j: number) => unitOf([pos(m, j)[0] - pos(m, i)[0], pos(m, j)[1] - pos(m, i)[1]]);
  const parallel = (a: P, b: P) => Math.abs(Math.abs(a[0] * b[0] + a[1] * b[1]) - 1) < 1e-6;
  // up: the chair's upright axis on the page; ring: its six atoms in order.
  const check = (m: Mol, ring: number[], up: P, label: string) => {
    const c: P = [ring.reduce((s, i) => s + pos(m, i)[0], 0) / 6, ring.reduce((s, i) => s + pos(m, i)[1], 0) / 6], sides: number[] = [];
    ring.forEach((i, k) => {
      const one = sprout(m, i), a = one.atoms.length - 1, d = way(one, i, a);
      assert.ok(parallel(d, up), `${label}, atom ${k}: the first bond is axial`);
      const side = Math.sign(d[0] * up[0] + d[1] * up[1]);
      for (const n of neighbours(m, i)) assert.ok(Math.sign((pos(m, n)[0] - pos(m, i)[0]) * up[0] + (pos(m, n)[1] - pos(m, i)[1]) * up[1]) === -side, `${label}, atom ${k}: away from the ring`);
      sides.push(side);
      const two = sprout(one, i), b = two.atoms.length - 1, e = way(two, i, b), once = way(m, ring[(k + 1) % 6], ring[(k + 2) % 6]);
      assert.ok(parallel(e, once), `${label}, atom ${k}: the second bond is equatorial`);
      assert.ok(e[0] * (pos(m, i)[0] - c[0]) + e[1] * (pos(m, i)[1] - c[1]) > 0, `${label}, atom ${k}: out of the ring`);
      assert.ok(Math.abs(Math.hypot(pos(two, b)[0] - pos(m, i)[0], pos(two, b)[1] - pos(m, i)[1]) - 1) < 1e-9, "one bond length");
      // A third click goes into the widest gap, as at any atom.
      assert.equal(sprout(two, i).atoms.length, two.atoms.length + 1);
    });
    assert.deepEqual(sides.map((s, k) => s * sides[(k + 1) % 6]), [-1, -1, -1, -1, -1, -1], `${label}: up and down in turn`);
  };
  for (const which of [1, 2] as const) for (const turn of [0, 0.7, -2.1]) {
    const m = addChair(EMPTY, which, { point: [3, 1], turn });
    check(m, [0, 1, 2, 3, 4, 5], [-Math.sin(turn), Math.cos(turn)], `chair ${which} turned ${turn}`);
    // An axial bond first drawn by hand: the next is equatorial; an equatorial one first: the next is axial.
    const ax = sprout(m, 0), eq = sprout(ax, 0);
    const handEq = { ...m, atoms: [...m.atoms, eq.atoms[eq.atoms.length - 1]], bonds: [...m.bonds, { type: 1, atoms: [0, m.atoms.length] as [number, number] }] };
    assert.ok(parallel(way(sprout(handEq, 0), 0, handEq.atoms.length), [-Math.sin(turn), Math.cos(turn)]), "after an equatorial bond, an axial one");
  }
  // The Conformers templates, with depth.
  for (const [name, withH] of [["Cyclohexane chair", "Chair, axial and equatorial H"], ["Cyclohexane chair (flipped)", "Chair, axial and equatorial H (flipped)"]]) {
    const m = template(name), h = template(withH);
    check(m, [0, 1, 2, 3, 4, 5], [0, 1], name);
    for (let i = 0; i < 6; i++) {
      // The template's H atoms on ring atom i: the axial one first (chairWith), then the equatorial one.
      const hs = h.bonds.flatMap((b) => (b.atoms[0] === i && h.atoms[b.atoms[1]].label === "H" ? [b.atoms[1]] : []));
      const one = sprout(m, i), two = sprout(one, i);
      for (const [mol, hAt] of [[one, hs[0]], [two, hs[1]]] as const) {
        const z = mol.atoms[mol.atoms.length - 1].location[2], want = h.atoms[hAt].location[2] - h.atoms[i].location[2];
        assert.ok(Math.sign(z - m.atoms[i].location[2]) === Math.sign(want) && Math.abs(z - m.atoms[i].location[2] - want) < 0.2, `${name}, atom ${i}: depth ${z} as the template's H (${want})`);
      }
    }
  }
  // Not a chair: a flat cyclohexane and a benzene keep the widest gap (away from both ring bonds).
  for (const flat of [addRing(EMPTY, 6, false, { point: [0, 0] }), addRing(EMPTY, 6, true, { point: [0, 0] })]) {
    const one = sprout(flat, 0), d = way(one, 0, one.atoms.length - 1), out = unitOf([pos(flat, 0)[0], pos(flat, 0)[1]]);
    assert.ok(parallel(d, out) && d[0] * out[0] + d[1] * out[1] > 0, "a flat ring's bond points out from its middle");
  }
  console.log("bondchain.check: axial and equatorial bonds off a chair ok");
}
