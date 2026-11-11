// Run: node src/check.check.ts. Fails loudly if structure checks break.
import assert from "node:assert/strict";
import { EMPTY, LARGE, addCharge, atomAt, bondTo, moveAtoms, setElement, setLabel, sprout } from "./edit.ts";
import type { Mol } from "./render.ts";
import { hiddenWarnings, hideProblems, messy, problemAt, problems, showWarnings, valences, type StereoFacts } from "./check.ts";

// A nitrogen with four bonds is flagged, with a positive charge as the fix; once charged it is fine.
let m = setElement(sprout(EMPTY, [0, 0]), 0, "N");
for (const p of [[-1, 0], [0, 1], [0, -1]] as [number, number][]) m = bondTo(m, 0, p);
const found = problems(m);
assert.equal(found.length, 1);
assert.match(found[0].message, /^N1 has 4 bonds\. Nitrogen has a maximum of 3\./);
assert.deepEqual(found[0].fix, { label: "Add a positive charge", command: "fix:0:1" });
assert.equal(found[0].type, "valence");
assert.equal(problems(addCharge(m, 0, 1)).length, 0);
// The valences an atom can have: an ion as the element it then has as many valence electrons as; from period 3,
// pairs of electrons more.
assert.deepEqual([valences("N", 0), valences("N", 1), valences("O", -1), valences("S", 0), valences("S", 1), valences("Cl", 0), valences("B", -1), valences("C", 1)], [[3], [4], [1], [2, 4, 6], [3, 5], [1, 3, 5, 7], [4], [3]]);
// A centre atom with n single bonds (to carbons), and the drawing's problems as type and message.
const star = (label: string, n: number, charge = 0): Mol => {
  let x = setElement(sprout(EMPTY, [0, 0]), 0, label);
  for (let k = 1; k < n; k++) x = bondTo(x, 0, [Math.cos(k * 1.3), Math.sin(k * 1.3)]);
  return charge ? addCharge(x, 0, charge) : x;
};
const said = (x: Mol, stereo?: StereoFacts) => problems(x, stereo).map((p) => `${p.type}: ${p.message}`);
// Valence through the whole main group: S, Se and Cl between two valences, P with four bonds (each mended by a positive
// charge: a phosphonium, a halonium), a perchlorate's chlorine (7) and a sulfonium (S+ with three).
assert.deepEqual(said(star("Se", 3)), ["valence: Se1 has 3 bonds. Selenium has a valence of 2, 4 or 6. Add a positive charge, or add or remove a bond."]);
assert.equal(problems(star("P", 4))[0].fix?.command, "fix:0:1");
assert.deepEqual(said(star("S", 3, 1)), []);
assert.deepEqual(said(star("Cl", 2)), ["valence: Cl1 has 2 bonds. Chlorine has a valence of 1, 3, 5 or 7. Add a positive charge, or add or remove a bond."]);
assert.deepEqual(said(star("C", 5)), ["valence: C1 has 5 bonds. Carbon has a maximum of 4. Remove a bond."]);
{
  let cl = setElement(sprout(EMPTY, [0, 0]), 0, "Cl");
  for (const [k, t] of [[1, 2], [2, 2], [3, 2]] as const) cl = bondTo(cl, 0, [Math.cos(k * 1.5), Math.sin(k * 1.5)], { type: t });
  assert.deepEqual(said(cl), [], "perchlorate");
}
// Aromatic bonds count 1 or 1.5 for the rule: thiophene's S and pyrrole's N drawn with aromatic bonds are fine.
{
  const ring = (het: string): Mol => ({ atoms: [het, "C", "C", "C", "C"].map((label, k) => ({ label, location: [Math.cos(k * 1.2566), Math.sin(k * 1.2566), 0] as [number, number, number] })), bonds: [0, 1, 2, 3, 4].map((k) => ({ type: 4, atoms: [k, (k + 1) % 5] as [number, number] })) });
  assert.deepEqual([said(ring("S")), said(ring("N")), said(ring("O"))], [[], [], []]);
}
// Labels are checked through the atom they attach by: CH3 or OMe with two bonds is wrong, with one it is fine.
{
  const two = (text: string) => setLabel(bondTo(sprout(EMPTY, [-1, 0]), 1, [1, 0]), 1, text);
  assert.deepEqual(said(two("CH3")), ["valence: CH3 has 2 bonds. It can have 1. Remove a bond."]);
  assert.deepEqual(said(two("OMe")), ["valence: OMe has 2 bonds. It can have 1. Remove a bond."]);
  assert.deepEqual(said(two("Et3N")), ["valence: Et3N has 2 bonds. It can have no bonds. Remove its bonds or change the label."]);
  assert.deepEqual(said(two("Ph")), ["valence: Ph has 2 bonds. It can have 1. Remove a bond."]);
  // C6H4 shares its hydrogens out among its carbons, so Octet cannot tell; it says nothing.
  for (const text of ["CH2", "NH", "O", "C6H4"]) assert.deepEqual(said(two(text)), [], text);
  const one = (text: string) => setLabel(sprout(EMPTY, [0, 0]), 1, text);
  for (const text of ["CH3", "OMe", "Ph", "NO2", "CO2Et", "CO2H", "SO3H", "NHBoc", "TMS", "H3C", "CH2OH", "CN", "OTf", "Boc"]) assert.deepEqual(said(one(text)), [], text);
  assert.deepEqual(said(one("CH(CH3")), ["parens: The label CH(CH3 has unbalanced parentheses. Add or remove a parenthesis."]);
  // An isotope written before a label, and an atom's mass number: O-13 is a known isotope, O-31 and C-24 are not.
  assert.deepEqual(said(one("24CH3")), ["isotopes: 24CH3 has an isotope that is not known: Carbon has no isotope of mass 24. Change the mass number."]);
  assert.deepEqual(said(one("13CH3")), []);
  const o = (isotope: number): Mol => ({ atoms: [{ label: "O", location: [0, 0, 0], isotope }], bonds: [] });
  assert.deepEqual([said(o(13)), said(o(18)), said(o(31))], [[], [], ["isotopes: O1 has mass number 31. Oxygen has no isotope of mass 31. Change the mass number."]]);
}
// Lone single bonds, unlabelled atoms in a straight line, atoms close to a bond, and two bonds on one pair of atoms.
{
  const lone = sprout(EMPTY, [0, 0]);
  assert.deepEqual(said(lone), ["isolated: Octet reads this lone bond as ethane. To draw a line, use the Line tool."]);
  assert.equal(problems(lone)[0].bond, 0);
  assert.deepEqual(said(setLabel(lone, 1, "OH")), []);
  assert.deepEqual(said({ ...lone, atoms: lone.atoms.map((a, i) => (i ? { ...a, radical: 3 } : a)) }), [], "a carbene's bond is not ethane");
  const path = (...ps: [number, number][]): Mol => ({ atoms: ps.map(([x, y]) => ({ label: "C", location: [x, y, 0] as [number, number, number] })), bonds: ps.slice(1).map((_, k) => ({ type: 1, atoms: [k, k + 1] as [number, number] })) });
  assert.deepEqual(said(path([-1, 0], [0, 0], [1, 0], [1.5, 0.87])), ["linear: C2 has two bonds in a straight line, so it does not show. Add a label or bend a bond."]);
  assert.deepEqual(said(path([-1, 0], [0, 0], [0.87, 0.5], [1.73, 0])), [], "a zig-zag chain");
  const allene: Mol = { atoms: [-1, 0, 1].map((x) => ({ label: "C", location: [x, 0, 0] as [number, number, number] })).concat([{ label: "C", location: [-1.5, 0.87, 0] }, { label: "C", location: [1.5, 0.87, 0] }]), bonds: [{ type: 2, atoms: [0, 1] }, { type: 2, atoms: [1, 2] }, { type: 1, atoms: [0, 3] }, { type: 1, atoms: [2, 4] }] };
  assert.deepEqual(said(allene), ["linear: C2 has two bonds in a straight line, so it does not show. Add a label or bend a bond."], "ChemDraw marks an allene's middle atom too");
  const near: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [1, 0, 0] }, { label: "C", location: [0.5, 0.1, 0] }, { label: "C", location: [0.5, 1.1, 0] }], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [2, 3] }] };
  assert.deepEqual(said(near).filter((t) => !t.startsWith("isolated")), ["near: C3 is very close to a bond that it is not part of. Move it or join it."]);
  const twice: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [1, 0, 0] }, { label: "O", location: [1.5, 0.87, 0] }], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 0] }, { type: 1, atoms: [1, 2] }] };
  assert.deepEqual(said(twice), ["misc: Two bonds join the same two atoms. Delete one of them."]);
  // Brackets that cross one bond on the left and none on the right; then one on each side.
  const chain = path([-2, 0], [-1, 0.5], [0, 0], [1, 0.5]);
  const bracket = (x1: number): Mol => ({ ...chain, shapes: [{ id: 1, kind: "brackets", from: [-0.5, -1], to: [x1, 1] }] });
  assert.deepEqual(said(bracket(1.5)), ["parens: These brackets cross 1 bond on the left and 0 on the right. Make the two sides cross the same bonds."]);
  assert.deepEqual(said(bracket(0.5)), []);
}
// Hidden warnings: an atom or bond with Display Warnings off has no problem marked, but Check Structure (all) sees it.
{
  const lone = sprout(EMPTY, [0, 0]), hid = { ...lone, bonds: [{ ...lone.bonds[0], ignoreWarnings: true as const }] };
  assert.deepEqual(problems(hid), []);
  assert.deepEqual(problems(hid, undefined, true).map((p) => p.hidden), [true]);
  // Brackets with Display Warnings off, as ChemDraw keeps it on any picked object.
  const path: Mol = { atoms: [[-2, 0], [-1, 0.5], [0, 0], [1, 0.5]].map(([x, y]) => ({ label: "C", location: [x, y, 0] as [number, number, number] })), bonds: [0, 1, 2].map((k) => ({ type: 1, atoms: [k, k + 1] as [number, number] })) };
  const hidBrackets: Mol = { ...path, shapes: [{ id: 1, kind: "brackets", from: [-0.5, -1], to: [1.5, 1], ignoreWarnings: true }] };
  assert.deepEqual(problems(hidBrackets), []);
  assert.deepEqual(problems(hidBrackets, undefined, true).map((p) => [p.shape, p.hidden]), [[1, true]]);
  // Hide this warning (the card's X, or the right-click menu on its mark): that object's warning goes, the rest stay.
  const bad = { ...setElement(path, 1, "N"), shapes: [{ id: 1, kind: "brackets" as const, from: [-0.5, -1] as [number, number], to: [1.5, 1] as [number, number] }] };
  const n5 = bondTo(bondTo(bad, 1, [-1, 1.5]), 1, [-1, -0.5]);
  assert.deepEqual(problems(n5).map((p) => p.type).sort(), ["parens", "valence"]);
  // A right-click on the red ring (past the atom's own hit radius) or in the brackets' red box finds that warning.
  assert.equal(atomAt(n5, [-1.3, 0.8]), undefined);
  assert.equal(problemAt(n5, problems(n5), [-1.3, 0.8])?.atom, 1);
  assert.equal(problemAt(n5, problems(n5), [1.6, 0])?.shape, 1);
  assert.equal(problemAt(n5, problems(n5), [3, 3]), undefined);
  const quiet = hideProblems(n5, problems(n5).filter((p) => p.atom === 1));
  assert.deepEqual(problems(quiet).map((p) => p.type), ["parens"]);
  assert.equal(quiet.atoms[1].ignoreWarnings, true);
  assert.ok(hiddenWarnings(quiet) && hiddenWarnings(quiet, new Set([1])) && !hiddenWarnings(quiet, new Set([0])));
  // Show warnings: on the selection only, or on the whole drawing with nothing selected.
  const all = hideProblems(quiet, [{ shape: 1 }]);
  assert.deepEqual(problems(all), []);
  assert.deepEqual(problems(showWarnings(all, new Set([0]), new Set([1]))).map((p) => p.type), ["parens"]);
  assert.deepEqual(problems(showWarnings(all)).map((p) => p.type).sort(), ["parens", "valence"]);
  assert.ok(!hiddenWarnings(showWarnings(all)));
  // A caption's warning: Interpret Chemically goes off.
  const cap: Mol = { ...EMPTY, captions: [{ id: 4, text: "CH5", x: 0, y: 0 }] };
  assert.equal(hideProblems(cap, [{ caption: 4 }]).captions![0].chemical, false);
}
// The stereochemistry warnings from Indigo's facts: a wedge between two stereocentres; a wedge drawn the wrong way
// round (its fix swaps the ends); unset and conflicting centres only where Show Stereochemistry is on; enhanced flags.
{
  const facts = (centres: number[], unset: number[] = [], conflict: number[] = [], achiral: number[] = []): StereoFacts => ({ centres: new Set(centres), unset: new Set(unset), conflict: new Set(conflict), achiral: new Set(achiral) });
  const m2: Mol = { atoms: [0, 1, 2, 3].map((x) => ({ label: "C", location: [x, x % 2 ? 0.5 : 0, 0] as [number, number, number] })), bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2], stereo: 1 }, { type: 1, atoms: [2, 3] }] };
  assert.deepEqual(said(m2, facts([1, 2])), ["between: This wedge or hash joins two stereocentres, so it is not clear which one it sets. Start it at one stereocentre only."]);
  // A centre whose neighbours are all centres (C2 here) has no other bond to wedge: no warning where the wide end (C3)
  // is set by its own wedge, as it would be in a cage (ginkgolide's quaternary carbons).
  const cage: Mol = { ...m2, bonds: [m2.bonds[0], m2.bonds[1], { ...m2.bonds[2], stereo: 6 }] };
  assert.deepEqual(said(cage, facts([0, 1, 2])), []);
  assert.equal(said(m2, facts([0, 1, 2])).length, 1, "C3 has no wedge of its own");
  assert.equal(said(cage, facts([1, 2])).length, 1, "C1 is not a stereocentre, so C2 could be wedged to it");
  const back = problems(m2, facts([2]));
  assert.deepEqual(back.map((p) => [p.type, p.bond, p.fix?.command]), [["backwards", 1, "flip_bond:1"]]);
  assert.deepEqual(said(m2, facts([1])), [], "the narrow end is on the stereocentre");
  const shown: Mol = { ...m2, atoms: m2.atoms.map((a) => ({ ...a, cip: true as const })) };
  assert.deepEqual(said(m2, facts([0], [0])), [], "unset, Show Stereochemistry off");
  assert.deepEqual(said(shown, facts([0], [0])), ["unspecified: C1 is a stereocentre with no wedge or hash bond. Add one to set its configuration."]);
  assert.deepEqual(said(shown, facts([2], [2], [])).filter((t) => t.startsWith("ambiguous")), ["ambiguous: The wedge and hash bonds at C3 conflict, or do not set its configuration. Change a wedge or hash."]);
  const flagged: Mol = { ...m2, atoms: m2.atoms.map((a, k) => (k === 1 ? { ...a, enhanced: "&1" } : k === 3 ? { ...a, enhanced: "or2" } : a)) };
  assert.deepEqual(said(flagged, facts([1, 2], [], [], [0, 1, 2, 3])).filter((t) => t.startsWith("enhanced")), [
    "enhanced: C4 has the stereo flag or2, but it is not a stereocentre. Remove the flag.",
    "enhanced: This compound cannot be racemic: it is not chiral. Remove its stereo flags.",
    "enhanced: This compound cannot be relative: it is not chiral. Remove its stereo flags.",
  ]);
}
// Clean drawings are not messy; a squashed bond or overlapping atoms are.
const clean = sprout(sprout(EMPTY, [0, 0]), 1);
assert.equal(messy(clean), false);
assert.equal(messy(moveAtoms(clean, new Set([2]), [-0.5, 0])), true);
// An aromatic bond counts 1.5 and a bond of an unknown type counts 1: N with an aromatic bond, a double bond, a
// query bond and a single bond has 5.5 bond orders.
const odd = { ...m, bonds: m.bonds.map((b, k) => ({ ...b, type: [4, 2, 7, 1][k] })) };
assert.match(problems(odd)[0].message, /^N1 has 5\.5 bond orders\./);
// A large drawing uses a grid, a small one the plain loops: both give the same answer. Random chains of near-unit
// bonds (some cross, some atoms land close) are checked alone, then inside a drawing made large by spare atoms far
// away, with the chain selected and with nothing selected.
{
  let seed = 7;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const spare = Array.from({ length: LARGE + 1 }, (_, k) => ({ label: "C", location: [1000 + (k % 20) * 2, (k / 20 | 0) * 2, 0] as [number, number, number] }));
  let messyCount = 0;
  for (let t = 0; t < 400; t++) {
    const n = 4 + Math.floor(rand() * 30), atoms: Mol["atoms"] = [], bonds: Mol["bonds"] = [];
    let x = rand() * 4, y = rand() * 4, a = 0;
    for (let i = 0; i < n; i++) {
      const l = t % 4 ? 0.8 + rand() * 0.45 : 0.6 + rand() * 0.8;
      a += (rand() - 0.5) * 2.5;
      if (i && rand() < 0.15) { x = rand() * 6; y = rand() * 6; } else if (i) { x += l * Math.cos(a); y += l * Math.sin(a); bonds.push({ type: 1, atoms: [i - 1, i] }); }
      atoms.push({ label: "C", location: [x, y, 0] });
    }
    const small: Mol = { atoms, bonds }, large: Mol = { atoms: [...atoms, ...spare], bonds };
    const chain = new Set(atoms.map((_, i) => i)), part = new Set([...chain].filter((i) => i % 3));
    for (const ids of [chain, part]) assert.equal(messy(large, ids), messy(small, ids), `same answer on drawing ${t}`);
    assert.equal(messy(large, new Set()), messy(small, new Set()), `same answer on drawing ${t}, nothing selected`);
    if (messy(small)) messyCount++;
  }
  assert.ok(messyCount > 50 && messyCount < 350, `both answers are tested (${messyCount} of 400 messy)`);
}
console.log("check.check: ok");
