// Run: node src/mdl.check.ts. Fails loudly if MOL, SDF, RXN or RD files (V3000 and V2000) or reaction SMILES lose
// enhanced stereo, map numbers or a reaction's arrow (CH-9, CH-10), or if a written label beside a wedge reads wrongly.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { importStructure, parseStructure, ready, toMolfile, toReaction, toSdf, toSmiles } = await import("./chem.ts");
type Mol = import("./render.ts").Mol;
type Atom = import("./render.ts").Atom;
await ready;

const A = (label: string, x: number, y: number, more: Partial<Atom> = {}): Atom => ({ label, location: [x, y, 0], ...more });
// A stereocentre (&1, map 1) with F wedged, Cl, N and a methyl (map 2); and ethene, apart from it.
const m: Mol = {
  atoms: [A("C", 0, 0, { enhanced: "&1", map: 1 }), A("F", 0, 1), A("Cl", 0.87, -0.5), A("N", -0.87, -0.5), A("C", 0.6, -1.2, { map: 2 }), A("C", 5, 0), A("C", 6, 0)],
  bonds: [{ type: 1, atoms: [0, 1], stereo: 1 }, { type: 1, atoms: [0, 2] }, { type: 1, atoms: [0, 3] }, { type: 1, atoms: [0, 4] }, { type: 2, atoms: [5, 6] }],
};

// MOL: V3000 by default, with the and group and the map numbers; V2000 keeps the map numbers.
const v3 = toMolfile(m), v2 = toMolfile(m, true);
assert.match(v3, /V3000/);
assert.match(v3, /MDLV30\/STERAC1 ATOMS=\(1 1\)/, "the &1 group is kept");
assert.match(v3, /^M {2}V30 1 C [-\d. ]+ 1 /m, "atom 1 keeps map number 1");
assert.match(v2, /V2000/);
assert.doesNotMatch(v2, /V3000/);
assert.match(v2.split("\n").find((l) => / C {3}/.test(l))!, / 1 {2}0 {2}0$/, "a V2000 atom line keeps its map number");
// Reading them back keeps the flags and the numbers.
for (const text of [v3, v2]) {
  const back = importStructure(text);
  assert.equal(back.atoms.filter((a) => a.map).length, 2);
  if (text === v3) assert.equal(back.atoms.find((a) => a.map === 1)?.enhanced, "&1");
}

// SDF: one record for each structure.
const sdf = toSdf(m);
assert.equal(sdf.split("$$$$").length - 1, 2);
assert.match(toSdf(m, true), /V2000/);
// A lone atom is a record of its own, with its atom: methane, and a label such as MeOH drawn out.
const lone = toSdf({ atoms: [A("C", 0, 0, { text: "MeOH" }), A("C", 3, 0), A("C", 6, 0), A("O", 7, 0)], bonds: [{ type: 1, atoms: [2, 3] }] });
assert.deepEqual(lone.split("$$$$\n").slice(0, -1).map((r) => /COUNTS (\d+)/.exec(r)?.[1]), ["2", "1", "2"]);

// A written label beside a wedge reads as the same structure drawn out (its group sits at the label, not at 0, 0).
const lab: Mol = { atoms: [A("C", 0, 0), A("F", 0, 1), A("Cl", 0.87, -0.5), A("Br", 0.3, -0.9), A("C", -0.87, -0.5, { text: "OMe" })], bonds: [{ type: 1, atoms: [0, 1], stereo: 1 }, { type: 1, atoms: [0, 2] }, { type: 1, atoms: [0, 3] }, { type: 1, atoms: [0, 4] }] };
const out: Mol = { atoms: [...lab.atoms.slice(0, 4), A("O", -0.87, -0.5), A("C", -1.74, 0)], bonds: [...lab.bonds, { type: 1, atoms: [4, 5] }] };
assert.equal(toSmiles(lab), toSmiles(out));

// Reactions: an RXN file of one step, an RD file of every step, and reaction SMILES, with map numbers.
const step = { reactants: [[0, 1, 2, 3, 4]], products: [[5, 6]], agents: [] };
const rxn = toReaction(m, [step], "rxn"), rxn2 = toReaction(m, [step], "rxn", true);
assert.match(rxn, /^\$RXN V3000/);
assert.match(rxn, /BEGIN REACTANT[\s\S]*BEGIN PRODUCT/);
assert.match(rxn2, /^\$RXN\n/);
assert.match(toReaction(m, [step], "smiles"), /^[^>]*:1\][^>]*>>C=C/, "reaction SMILES with map numbers");
const rdf = toReaction(m, [step, { reactants: [[5, 6]], products: [[0, 1, 2, 3, 4]], agents: [] }], "rdf");
assert.match(rdf, /^\$RDFILE 1\n\$DATM/);
assert.equal(rdf.split("$RFMT").length - 1, 2);
// Read back: the arrow comes too, and an RD file's reactions do not overlap.
const r1 = importStructure(rxn);
assert.equal(r1.arrows?.length, 1);
assert.equal(r1.atoms.length, 7);
const r2 = importStructure(rdf), [a, b] = r2.arrows!;
assert.equal(r2.arrows?.length, 2);
assert.ok(Math.abs(a.from[1] - b.from[1]) > 2, "each reaction of an RD file on a line of its own");
// An RD file pasted as text reads as Import reads it: every reaction, each with its arrow.
assert.equal(parseStructure(rdf).arrows?.length, 2);
assert.equal(parseStructure(rdf).atoms.length, r2.atoms.length);
// Reaction SMILES keeps the arrow and the plus signs; an agent stands over the arrow.
const r3 = parseStructure("CC(=O)O.OCC>[H+]>CC(=O)OCC.O");
assert.equal(r3.arrows?.length, 1);
assert.equal(r3.captions?.filter((c) => c.text === "+").length, 2);
// A bond's Rxn mark (reaction centre, from Map Reaction Atoms) goes in RXN files and comes back.
const marked: Mol = { ...m, bonds: m.bonds.map((x, k) => (k === 4 ? { ...x, rxn: "change" as const } : x)) };
assert.match(toReaction(marked, [step], "rxn"), /RXCTR=8/);
assert.match(toReaction(marked, [step], "rxn", true).split("\n").find((l) => /^ {2}1 {2}2 {2}2/.test(l)) ?? "", / 8$/);
assert.equal(importStructure(toReaction(marked, [step], "rxn")).bonds.find((x) => x.type === 2)?.rxn, "change");
// An agent goes in the RXN file as one.
const withAgent: Mol = { ...m, atoms: [...m.atoms, A("Pd", 3, 1)] };
assert.match(toReaction(withAgent, [{ ...step, agents: [[7]] }], "rxn"), /BEGIN AGENT[\s\S]*Pd/);

// An SD file whose records were all drawn at one place: each comes in apart from the others.
const same: Mol = { atoms: [A("C", 0, 0), A("O", 1, 0), A("N", 0, 0), A("S", 1, 0)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [2, 3] }] };
const two = importStructure(toSdf(same));
assert.ok(two.atoms[2].location[0] > two.atoms[1].location[0] + 1, "the second record stands to the right of the first");

// CML keeps its drawing.
const cml = importStructure(`<?xml version="1.0"?><cml><molecule><atomArray><atom id="a1" elementType="C" x2="0" y2="0"/><atom id="a2" elementType="O" x2="2" y2="0"/></atomArray><bondArray><bond atomRefs2="a1 a2" order="1"/></bondArray></molecule></cml>`);
assert.equal(cml.atoms.length, 2);
assert.equal(Math.round(cml.atoms[1].location[0] - cml.atoms[0].location[0]), 1, "scaled to one bond length, as drawn");

// Tritium typed as T is hydrogen-3, as D is hydrogen-2: MOL out and in (V3000 and V2000, and the query writer's H with
// MASS=3), and its mass in the formula's weight.
const tritiated: Mol = { atoms: [A("C", 0, 0), A("T", 1, 0), A("D", -1, 0)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [0, 2] }] };
for (const text of [toMolfile(tritiated), toMolfile(tritiated, true)]) assert.deepEqual(importStructure(text).atoms.map((a) => [a.label, a.isotope]), [["C", undefined], ["T", undefined], ["D", undefined]], text);
const { writeV3000, readV3000 } = await import("./molv3.ts");
const query = writeV3000(tritiated);
assert.match(query, /^M {2}V30 2 H [-\d. ]+ 0 MASS=3$/m);
assert.deepEqual(readV3000(query).atoms.map((a) => a.label), ["C", "T", "D"]);
const { analyse } = await import("./chem.ts");
const weight = (mol: Mol) => analyse(mol)![0].weight;
assert.equal(weight(tritiated), weight({ ...tritiated, atoms: [A("C", 0, 0), A("H", 1, 0, { isotope: 3 }), A("H", -1, 0, { isotope: 2 })] }));

console.log("mdl ok");
