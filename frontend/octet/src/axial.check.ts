// Run: node src/axial.check.ts. Fails loudly if Octet's own CIP ranking or its (M) and (P) labels go wrong, or if
// what Indigo says about stereocentres for the stereochemistry warnings changes. The handedness rule that gives M and
// P is first checked on ordinary stereocentres against Indigo's R and S.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { cipOf, parseStructure, ready, stereoFacts, stereoLabels } = await import("./chem.ts");
const { problems } = await import("./check.ts");
const { axialLabels, compareBranches, handedness } = await import("./axial.ts");
type Mol = import("./render.ts").Mol;
type V3 = [number, number, number];
await ready;

// R or S of a drawn stereocentre by Octet's own rule: ligands ranked by compareBranches, depth from its wedges, a
// lone hydrogen opposite the other three.
function ownRS(m: Mol, c: number): string | undefined {
  const near = m.bonds.flatMap((b) => (b.atoms[0] === c ? [b.atoms[1]] : b.atoms[1] === c ? [b.atoms[0]] : []));
  const z = (i: number) => m.bonds.reduce((t, b) => t + (b.atoms[0] === c && b.atoms[1] === i ? (b.stereo === 1 ? 1 : b.stereo === 6 ? -1 : 0) : 0), 0);
  const p = (i: number): V3 => [m.atoms[i].location[0], m.atoms[i].location[1], z(i)];
  const ranked = [...near].sort((a, b) => -compareBranches(m, c, a, b));
  for (let k = 1; k < ranked.length; k++) if (!compareBranches(m, c, ranked[k - 1], ranked[k])) return undefined;
  const o = p(c), places = ranked.map(p);
  if (places.length === 3) {
    const u = places.map((q) => { const d: V3 = [q[0] - o[0], q[1] - o[1], q[2] - o[2]]; const l = Math.hypot(...d); return d.map((x) => x / l) as V3; });
    places.push([o[0] - u.reduce((t, d) => t + d[0], 0), o[1] - u.reduce((t, d) => t + d[1], 0), o[2] - u.reduce((t, d) => t + d[2], 0)]);
  }
  return places.length === 4 ? handedness(places[0], places[1], places[2], places[3]) : undefined;
}
// Stereocentres with one to three ligands of each kind, rings, multiple bonds and isotopes.
const SMILES = [
  "C[C@H](N)C(=O)O", "C[C@@H](N)C(=O)O", "CC[C@H](C)O", "CC[C@@H](C)O", "O[C@H](Cl)Br", "F[C@](Cl)(Br)I", "F[C@@](Cl)(Br)I",
  "C[C@H](C=C)CC", "C[C@@H](C#N)C=O", "OC[C@H](O)C=O", "N[C@@H](CS)C(=O)O", "C[C@H]1CCCC[C@@H]1O", "C[C@@H]1CC[C@H](O)CC1C",
  "[2H][C@H](C)O", "[13CH3][C@H](C)O", "CC(C)[C@H](N)C(=O)O", "c1ccccc1[C@H](O)C", "C[C@H](c1ccccc1)c1ccccn1",
  "O=C[C@H](O)[C@@H](O)[C@H](O)CO", "C[C@]12CC[C@H]3[C@@H](CC=C4C[C@@H](O)CC[C@]34C)[C@@H]1CC[C@@H]2O",
];
let compared = 0;
for (const s of SMILES) {
  const m = parseStructure(s), cip = cipOf(m);
  assert.ok(cip, s);
  m.atoms.forEach((_, i) => {
    const want = cip!.atoms[i]?.replace(/[()]/g, "");
    if (!want || !/^[RS]$/.test(want)) return;
    assert.equal(ownRS(m, i), want, `${s}: atom ${i}`);
    compared++;
  });
}
assert.ok(compared >= 30, `compared ${compared} stereocentres`);

// An allene drawn as a chemist draws it: the near end flat (H up, methyl down), the far methyl on a wedge. Seen
// along the axis, the near methyl (1) turns to the far methyl (3) anticlockwise: M.
const atom = (label: string, x: number, y: number) => ({ label, location: [x, y, 0] as V3 });
const allene: Mol = {
  atoms: [atom("C", -1.87, -0.5), atom("C", -1, 0), atom("C", 0, 0), atom("C", 1, 0), atom("C", 1.87, 0.5)],
  bonds: [{ type: 1, atoms: [1, 0] }, { type: 2, atoms: [1, 2] }, { type: 2, atoms: [2, 3] }, { type: 1, atoms: [3, 4], stereo: 1 }],
};
const flip = (m: Mol): Mol => ({ ...m, bonds: m.bonds.map((b) => (b.stereo === 1 ? { ...b, stereo: 6 } : b.stereo === 6 ? { ...b, stereo: 1 } : b)) });
assert.deepEqual(axialLabels(allene).atoms, [undefined, undefined, "M", undefined, undefined]);
assert.equal(axialLabels(flip(allene)).atoms[2], "P");
// Seen from the other end it is the same axis: the drawing turned half a turn keeps M.
const turned: Mol = { ...allene, atoms: allene.atoms.map((a) => ({ ...a, location: [-a.location[0], -a.location[1], 0] as V3 })) };
assert.equal(axialLabels(turned).atoms[2], "M");
// With no wedge, or with the same group twice at one end, there is no label.
assert.equal(axialLabels({ ...allene, bonds: allene.bonds.map((b) => ({ ...b, stereo: undefined })) }).atoms[2], undefined);
const twoMethyls: Mol = { atoms: [...allene.atoms, atom("C", -1.87, 0.5)], bonds: [...allene.bonds, { type: 1, atoms: [1, 5] }] };
assert.equal(axialLabels(twoMethyls).atoms[2], undefined);
// SMILES allenes keep their axis through the layout: the two forms get opposite labels, and Show Stereochemistry
// shows them on the middle atom.
const [a1, a2] = ["CC=[C@]=CC", "CC=[C@@]=CC"].map((s) => axialLabels(parseStructure(s)).atoms[2]);
assert.ok(a1 && a2 && a1 !== a2, `${a1} ${a2}`);
assert.equal(stereoLabels(parseStructure("CC=[C@]=CC"))?.atoms[2], a1);
// A longer cumulene with four double bonds is an axis too (drawn by hand: Indigo's layout drops its stereo); with
// three it is not (it is E or Z).
const longer: Mol = {
  atoms: [atom("C", -2.87, -0.5), atom("C", -2, 0), atom("C", -1, 0), atom("C", 0, 0), atom("C", 1, 0), atom("C", 2, 0), atom("C", 2.87, 0.5)],
  bonds: [{ type: 1, atoms: [1, 0] }, ...[1, 2, 3, 4].map((i) => ({ type: 2, atoms: [i, i + 1] as [number, number] })), { type: 1, atoms: [5, 6], stereo: 1 }],
};
assert.equal(axialLabels(longer).atoms[3], "M");
const triene: Mol = { atoms: longer.atoms.slice(0, 6).concat([atom("C", 1.87, 0.5)]), bonds: [{ type: 1, atoms: [1, 0] }, ...[1, 2, 3].map((i) => ({ type: 2, atoms: [i, i + 1] as [number, number] })), { type: 1, atoms: [4, 6], stereo: 1 }] };
assert.ok(!axialLabels(triene).atoms.some(Boolean));

// A hindered biaryl: 6,6'-dimethylbiphenyl-2,2'-diol, with the far ring's methyl on a wedge, then on a hash.
function biaryl(smiles: string, wedge: 1 | 6 | undefined, from: (m: Mol) => [number, number] | undefined) {
  const m = parseStructure(smiles), ends = from(m);
  m.bonds = m.bonds.map((b) => ({ ...b, stereo: undefined }));
  if (ends && wedge) m.bonds = m.bonds.map((b) => (b.atoms.includes(ends[0]) && b.atoms.includes(ends[1]) ? { ...b, atoms: ends, stereo: wedge } : b));
  return m;
}
// Atoms in this SMILES: the axis is 7–8; on the far ring, 9 carries the methyl (10) and 14 the OH.
const diol = "Cc1cccc(O)c1-c1c(C)cccc1O";
const axis = (m: Mol) => m.bonds.findIndex((b) => b.atoms.includes(7) && b.atoms.includes(8));
const up = biaryl(diol, 1, () => [9, 10]), down = biaryl(diol, 6, () => [9, 10]), flat = biaryl(diol, undefined, () => undefined);
const [pu, pd] = [axialLabels(up).bonds[axis(up)], axialLabels(down).bonds[axis(down)]];
assert.ok(pu && pd && pu !== pd, `${pu} ${pd}`);
assert.ok(!axialLabels(flat).bonds.some(Boolean));
// The same depth given by a wedge on the ring bond from the axis atom to that ortho atom gives the same label.
const ring = biaryl(diol, 1, () => [8, 9]);
assert.equal(axialLabels(ring).bonds[axis(ring)], pu);
// Only two ortho substituents (2,2'-dimethylbiphenyl) is not hindered enough, as ChemDraw holds; a ring with the same
// group at both ortho places (2,6-dimethylphenyl) is not an axis at all.
assert.ok(!axialLabels(biaryl("Cc1ccccc1-c1c(C)cccc1", 1, () => [8, 9])).bonds.some(Boolean));
assert.ok(!axialLabels(biaryl("Cc1cccc(C)c1-c1c(C)cccc1O", 1, () => [9, 10])).bonds.some(Boolean));

// Stereocentres as Indigo reads them, for the warnings. Butan-2-ol: C0 is the centre (bonds to C1, the CH2 C2 and O4).
const butanol = (bond: Mol["bonds"][number] | undefined): Mol => {
  const m: Mol = { atoms: [atom("C", 0, 0), atom("C", -0.87, -0.5), atom("C", 0.87, -0.5), atom("C", 1.73, 0), atom("O", 0, 1)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [0, 2] }, { type: 1, atoms: [2, 3] }, { type: 1, atoms: [0, 4] }] };
  if (bond) m.bonds = m.bonds.map((b) => (b.atoms.every((i) => bond.atoms.includes(i)) ? bond : b));
  return m;
};
const sets = (f: ReturnType<typeof stereoFacts>) => [[...f.centres], [...f.unset], [...f.conflict], [...f.achiral]];
// A structure with no wedge, Show Stereochemistry off and no flag is not read; with Show Stereochemistry on it is.
assert.deepEqual(sets(stereoFacts(butanol(undefined))), [[], [], [], []]);
const shown = butanol(undefined);
assert.deepEqual(sets(stereoFacts({ ...shown, atoms: shown.atoms.map((a) => ({ ...a, cip: true as const })) })), [[0], [0], [], []]);
assert.deepEqual(sets(stereoFacts(butanol({ type: 1, atoms: [0, 4], stereo: 1 }))), [[0], [], [], []]);
// A wedge drawn from the OH to the centre (narrow end on the O): the centre is unset, and the wedge is backwards.
const back = butanol({ type: 1, atoms: [4, 0], stereo: 1 });
assert.deepEqual(sets(stereoFacts(back)), [[0], [0], [], []]);
assert.deepEqual(problems(back, stereoFacts(back)).map((p) => [p.type, p.bond]), [["backwards", 3]]);
// Three wedges on one centre conflict.
const three: Mol = { ...butanol(undefined), bonds: butanol(undefined).bonds.map((b) => (b.atoms[0] === 0 ? { ...b, stereo: 1 } : b)) };
assert.deepEqual(sets(stereoFacts(three))[2], [0]);
// A wedge between two stereocentres (2,3-dibromobutane's C1 and C3).
const dibromo = parseStructure("CC(Br)C(Br)C");
dibromo.bonds = dibromo.bonds.map((b) => (b.atoms.includes(1) && b.atoms.includes(3) ? { ...b, atoms: [1, 3] as [number, number], stereo: 1 } : b));
assert.deepEqual(problems(dibromo, stereoFacts(dibromo)).map((p) => p.type), ["between"]);
// A meso compound flagged racemic cannot be chiral; its chiral diastereomer can. Only asked for with `chiral`.
const flagged = (smiles: string) => { const m = parseStructure(smiles); return { ...m, atoms: m.atoms.map((a, i) => (m.bonds.some((b) => b.stereo && b.atoms[0] === i) ? { ...a, enhanced: "&1" } : a)) }; };
assert.equal(stereoFacts(flagged("C[C@@H](O)[C@H](C)O"), true).achiral.size, 6);
assert.equal(stereoFacts(flagged("C[C@@H](O)[C@@H](C)O"), true).achiral.size, 0);
assert.equal(stereoFacts(flagged("C[C@@H](O)[C@H](C)O")).achiral.size, 0);
// A label's atoms are expanded for Indigo, and the facts come back on the drawn atoms: C0 with an OMe label.
const labelled: Mol = { ...butanol({ type: 1, atoms: [0, 4], stereo: 1 }), atoms: butanol(undefined).atoms.map((a, i) => (i === 4 ? { ...a, text: "OMe" } : a)) };
assert.deepEqual(sets(stereoFacts(labelled)), [[0], [], [], []]);
console.log("axial.check: ok");
