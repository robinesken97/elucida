// Run: node src/interpret.check.ts. Fails loudly if a reaction step's parts are read wrongly (reactants, products,
// what stands above and below the arrow), or if mapping a scheme (CH-23) numbers it wrongly or marks the wrong bonds.
import assert from "node:assert/strict";
import { addArrow, addCaption, fragments, pickAtoms, pos } from "./edit.ts";
import { findReaction } from "./reaction.ts";
import { alignByMap, clearScheme, interpret, mapScheme, rolesOf } from "./interpret.ts";
import type { Atom, Bond, Box, Mol } from "./render.ts";

const A = (label: string, x: number, y: number): Atom => ({ label, location: [x, y, 0] });
const b = (i: number, j: number, type = 1): Bond => ({ type, atoms: [i, j] });
// A → B → C, each a two-atom structure; a reagent structure above the first arrow, text below it, and text kept on the
// second arrow. B's atoms are listed out of drawing order in its bond, as a drawing often has them.
let m: Mol = {
  atoms: [A("C", 0, 0), A("O", 1, 0), A("C", 6, 0), A("O", 7, 0), A("C", 12, 0), A("O", 13, 0), A("Pd", 3.5, 1.2)],
  bonds: [b(0, 1), b(3, 2, 2), b(4, 5)],
};
let first: number, second: number, below: number, kept: number;
[m, first] = addArrow(m, { kind: "reaction", from: [2, 0], to: [5, 0] });
[m, second] = addArrow(m, { kind: "reaction", from: [8, 0], to: [11, 0] });
[m, below] = addCaption(m, { text: "H2O", x: 3.5, y: -1.2, align: "centre" });
[m, kept] = addCaption(m, { text: "heat", x: 9.5, y: 0.5, align: "centre", on: { arrow: second, side: "above" } });
const ink = (atoms: number[]): Box => { const ps = atoms.map((i) => pos(m, i)); return [Math.min(...ps.map((p) => p[0])) - 0.2, Math.min(...ps.map((p) => p[1])) - 0.2, Math.max(...ps.map((p) => p[0])) + 0.2, Math.max(...ps.map((p) => p[1])) + 0.2]; };
const capBox = (id: number): Box | undefined => { const c = m.captions?.find((x) => x.id === id); return c && [c.x - 0.4, c.y - 0.2, c.x + 0.4, c.y + 0.2]; };
const r = findReaction(m, first, m.arrows!, ink, capBox)!;
const steps = interpret(m, r, capBox);
assert.equal(steps.length, 2);
const atomsOf = (list: { kind: string }[]) => list.map((x) => ("atoms" in x ? (x.atoms as number[]).sort() : (x as { id: number }).id));
assert.deepEqual(atomsOf(steps[0].reactants), [[0, 1]]);
assert.deepEqual(atomsOf(steps[0].products), [[2, 3]], "B is the first step's product");
assert.deepEqual(atomsOf(steps[1].reactants), [[2, 3]], "and the second step's reactant");
assert.deepEqual(atomsOf(steps[1].products), [[4, 5]]);
assert.deepEqual(atomsOf(steps[0].above), [[6]], "Pd drawn over the first arrow");
assert.deepEqual(atomsOf(steps[0].below), [below], "H2O under it");
assert.deepEqual(atomsOf(steps[1].above), [kept], "text kept on the second arrow");
const roles = rolesOf(steps);
assert.equal(roles.atoms.get(0), "reactant");
assert.equal(roles.atoms.get(2), "product", "an intermediate shows as the product it is first");
assert.equal(roles.atoms.get(6), "above");
assert.equal(roles.captions.get(below), "below");

// Mapping the scheme: a stand-in mapper numbers each atom by its place in its structure (as Indigo would C to C and O
// to O). One numbering runs through A, B and C; the double bond made in B and broken again in C gets Rxn marks.
const mapper = (rs: Mol[], ps: Mol[]) => ({ reactants: rs.map((x) => x.atoms.map((a) => (a.label === "C" ? 1 : 2))), products: ps.map((x) => x.atoms.map((a) => (a.label === "C" ? 1 : 2))) });
const structures = (list: { kind: string }[]) => list.flatMap((x) => ("atoms" in x ? [x.atoms as number[]] : []));
const mapped = mapScheme(m, steps.map((s) => ({ reactants: structures(s.reactants), products: structures(s.products) })), mapper, (atoms) => pickAtoms(m, atoms))!;
assert.deepEqual(mapped.atoms.slice(0, 6).map((a) => a.map), [1, 2, 1, 2, 1, 2], "each atom keeps its number through the scheme");
assert.equal(mapped.atoms[6].map, undefined, "an agent is not mapped");
assert.deepEqual(mapped.bonds.map((x) => x.rxn), ["change", "change", "change"], "the C–O bond order changes in each step");
const cleared = clearScheme(mapped, new Set([0, 1, 2, 3, 4, 5]));
assert.ok(cleared.atoms.every((a) => !a.map) && cleared.bonds.every((x) => !x.rxn));
// A bond broken: A (C–O) → C + O apart.
const brk: Mol = { atoms: [A("C", 0, 0), A("O", 1, 0), A("C", 5, 0), A("O", 7, 0)], bonds: [b(0, 1)] };
const out = mapScheme(brk, [{ reactants: [[0, 1]], products: [[2], [3]] }], (rs, ps) => ({ reactants: [[1, 2]], products: ps.map((x) => [x.atoms[0].label === "C" ? 1 : 2]) }), (atoms) => pickAtoms(brk, atoms))!;
assert.equal(out.bonds[0].rxn, "makebreak");
assert.equal(fragments(out).length, 3);

// Augmented Clean Up Reaction: a product drawn a quarter turn round (and at twice the bond length) is turned back to lie
// as its reactant, at one bond length; a mirror-image drawing is turned over in 3D, so its wedge becomes a hash.
{
  const L3: Mol = { atoms: [A("C", 0, 0, ), A("C", 1, 0), A("O", 1.5, 0.87), A("C", 0, 6), A("C", 0, 8), A("O", -1.73, 9)], bonds: [b(0, 1), b(1, 2), b(3, 4), b(4, 5)] };
  L3.atoms.forEach((a, i) => { a.map = [1, 2, 3, 1, 2, 3][i]; });
  const out = alignByMap(L3, [{ reactants: [[0, 1, 2]], products: [[3, 4, 5]] }]);
  const v = (m: Mol, i: number, j: number) => [m.atoms[j].location[0] - m.atoms[i].location[0], m.atoms[j].location[1] - m.atoms[i].location[1]].map((x) => Math.round(x * 100) / 100);
  assert.deepEqual(v(out, 3, 4), [1, 0], "C1→C2 lies as in the reactant, one bond length");
  assert.deepEqual(v(out, 4, 5), [0.5, 0.87]);
  // The mirror image: O on the other side; it is turned over, and its wedge becomes a hash.
  const M: Mol = { atoms: [A("C", 0, 0), A("C", 1, 0), A("O", 1.5, 0.87), A("C", 5, 0), A("C", 6, 0), A("O", 6.5, -0.87)], bonds: [b(0, 1), b(1, 2), b(3, 4), { type: 1, atoms: [4, 5], stereo: 1 }] };
  M.atoms.forEach((a, i) => { a.map = [1, 2, 3, 1, 2, 3][i]; });
  const over = alignByMap(M, [{ reactants: [[0, 1, 2]], products: [[3, 4, 5]] }]);
  assert.deepEqual(v(over, 4, 5), [0.5, 0.87], "turned over to match");
  assert.equal(over.bonds[3].stereo, 6, "a wedge turned over in 3D is a hash: the stereo is kept");
}
console.log("interpret ok");
