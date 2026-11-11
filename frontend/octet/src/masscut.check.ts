// Run: node src/masscut.check.ts. Fails loudly if a mass-fragmentation cut finds the wrong bonds, sides or sums.
import assert from "node:assert/strict";
import type { Mol } from "./render.ts";
import { addFormulas, bendOf, crossedBonds, cutEndAt, cutPoints, cutSides, cutThrough, extendCut, type Piece } from "./masscut.ts";

// Pentane drawn left to right: C0–C1–C2–C3–C4.
const pentane: Mol = { atoms: [0, 1, 2, 3, 4].map((i) => ({ label: "C", location: [i * 0.866, i % 2 ? 0.5 : 0, 0] })), bonds: [0, 1, 2, 3].map((i) => ({ type: 1, atoms: [i, i + 1] })) };
// The pieces a cut leaves, as fragmentMasses gives them, from a fake that counts carbons (CH3 at the ends of a piece,
// CH2 inside it, as homolysis leaves them).
const fake = (m: Mol, cut: number[]): Piece[] => {
  const root = m.atoms.map((_, i) => i), find = (i: number): number => (root[i] === i ? i : (root[i] = find(root[i])));
  m.bonds.forEach((b, k) => { if (!cut.includes(k)) root[find(b.atoms[0])] = find(b.atoms[1]); });
  const touched = new Set(cut.flatMap((k) => m.bonds[k].atoms.map(find)));
  return [...touched].map((r) => {
    const atoms = m.atoms.map((_, i) => i).filter((i) => find(i) === r), h = atoms.reduce((s, i) => s + (i === 0 || i === 4 ? 3 : 2), 0);
    return { atoms, formula: `C${atoms.length > 1 ? atoms.length : ""}H${h}`, exact: atoms.length * 12 + h * 1.007825 };
  });
};

// A vertical cut downwards between C1 and C2 crosses bond 1; C1 is on the right of a downward cut.
const down: [number, number][] = [[1.3, 2], [1.3, -2]];
assert.deepEqual(crossedBonds(pentane, down), [{ bond: 1, side: -1 }]);
const one = cutSides(pentane, down, fake)!;
assert.deepEqual(one.map((s) => [s.side, s.formula, s.atoms.sort()]), [[1, "C3H7", [2, 3, 4]], [-1, "C2H5", [0, 1]]]);
// Two cuts' worth of bonds on one path (a curve through bonds 0 and 3): the two end pieces are on one side, added up.
const bent: [number, number][] = [[0.4, -1], [0.4, 1], [3.1, 1], [3.1, -1]];
const two = cutSides(pentane, bent, fake)!;
assert.equal(two.length, 2);
const outside = two.find((s) => s.atoms.includes(0))!, inside = two.find((s) => s.atoms.includes(2))!;
assert.equal(outside.formula, "C2H6");
assert.deepEqual(outside.atoms.sort(), [0, 4]);
assert.ok(Math.abs(outside.exact - (24 + 6 * 1.007825)) < 1e-9);
assert.equal(inside.formula, "C3H6");
assert.notEqual(outside.side, inside.side);
// Nothing crossed: no sides.
assert.equal(cutSides(pentane, [[0, 3], [3, 3]], fake), undefined);
// A ring bond alone leaves one piece, so one side.
const ring: Mol = { atoms: [0, 1, 2].map((i) => ({ label: "C", location: [Math.cos((i * 2 * Math.PI) / 3), Math.sin((i * 2 * Math.PI) / 3), 0] })), bonds: [[0, 1], [1, 2], [2, 0]].map((a) => ({ type: 1, atoms: a })) };
assert.equal(cutSides(ring, [[0.2, 0.2], [1, 1]], fake)!.length, 1);

// Hill order, with H after C, and alphabetical with no carbon.
assert.equal(addFormulas(["CH3", "C2H5O", "Cl"]), "C3H8ClO");
assert.equal(addFormulas(["HO", "Br"]), "BrHO");
assert.equal(addFormulas(["C6H5", "C"]), "C7H5");

// Option's curve: straight when the pointer kept near the line, bent to its farthest point otherwise (left positive).
assert.equal(bendOf([[0, 0], [1, 0.01], [2, 0]]), 0);
assert.ok(Math.abs(bendOf([[0, 0], [1, 0.5], [2, 0]]) - 0.25) < 1e-9);
assert.ok(bendOf([[0, 0], [1, -0.5], [2, 0]]) < 0);
assert.equal(bendOf([[0, 0], [1, 5], [2, 0]]), 0.5);

// Mass Spec Analysis lines with corners (a key pressed during the drag): a curve of straight runs through them, its ends
// the line's ends. A corner on the point before it (a key pressed before the pointer moved) is left out.
assert.deepEqual(cutThrough([[0, 0], [1, 0]]), { from: [0, 0], to: [1, 0] });
const corner = cutThrough([[0.4, -1], [0.4, 1], [0.4, 1], [3.1, 1], [3.1, -1]]);
assert.deepEqual(corner.from, [0.4, -1]);
assert.deepEqual(corner.to, [3.1, -1]);
assert.deepEqual(cutPoints(corner), [[0.4, -1], [0.4, 1], [3.1, 1], [3.1, -1]]);
// The bent line crosses bonds 0 and 3, as the path does.
assert.deepEqual(crossedBonds(pentane, cutPoints(corner)).map((c) => c.bond), [0, 3]);
// A drag from an end makes the line longer from that end: a straight line gains a corner where it ended.
const straight = { kind: "cut", from: [1.3, 2] as [number, number], to: [1.3, -2] as [number, number] };
assert.deepEqual(cutPoints(extendCut(straight, "to", [], [2.2, -2])), [[1.3, 2], [1.3, -2], [2.2, -2]]);
assert.deepEqual(cutPoints(extendCut(straight, "from", [[2, 3]], [2.2, 2])), [[1.3, -2], [1.3, 2], [2, 3], [2.2, 2]]);
assert.deepEqual(cutPoints(extendCut(corner, "to", [], [4, -1])).slice(-2), [[3.1, -1], [4, -1]]);
// Only a fragmentation line's ends are taken, within reach; the line drawn last wins.
const lines = [straight, { kind: "line", from: [1.3, 2] as [number, number], to: [5, 5] as [number, number] }, { ...straight, to: [1.35, -2] as [number, number] }];
assert.equal(cutEndAt(lines, [1.32, -2.01], 0.1)?.line, lines[2]);
assert.equal(cutEndAt(lines, [1.3, 2.05], 0.1)?.end, "from");
assert.equal(cutEndAt(lines, [5, 5], 0.1), undefined);
assert.equal(cutEndAt(lines, [1.3, 0], 0.1), undefined);
console.log("masscut.check: ok");
