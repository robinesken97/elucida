// Run: node src/natural.check.ts. Fails loudly if Name to Structure (and a pasted SMILES, PubChem's answer: all go
// through parseStructure) draws a bridged or caged natural product badly (GitHub issue 9: taxol and strychnine). Each
// must come out as ChemDraw draws it: no atom on a bond or on another atom, no stereo flags (abs) on a structure of
// one known configuration, and one wedge or hash for each stereocentre with its narrow end on the centre, never one
// that joins two stereocentres. The stereochemistry must not change: the same standard InChI as the SMILES, and the
// same CIP labels as Indigo's own drawing.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { indigoLayout, parseStructure, ready, stereoFacts, toInchi } = await import("./chem.ts");
const { problems } = await import("./check.ts");
const { cipLabels } = await import("./cip.ts");
const { DRUGS } = await import("./drugs.ts");
await ready;

// The SMILES Name to Structure reads for each name (drugs.ts, OPSIN and the dictionary).
const structures: [string, string][] = [
  ["taxol", DRUGS.paclitaxel],
  ["strychnine", DRUGS.strychnine],
  ["morphine", "C1=CC(O)=C2C=3[C@@]45[C@@H](O2)[C@@H](O)C=C[C@H]4[C@@H](CC13)N(C)CC5"],
  ["codeine", "C1=CC(OC)=C2C=3[C@@]45[C@@H](O2)[C@@H](O)C=C[C@H]4[C@@H](CC13)N(C)CC5"],
  ["quinine", "COC=1C=C2C(=CC=NC2=CC1)[C@@H](O)[C@H]1N2C[C@@H]([C@H](C1)CC2)C=C"],
  ["cocaine", "C(C1=CC=CC=C1)(=O)O[C@@H]1[C@@H]([C@H]2CC[C@@H](C1)N2C)C(=O)OC"],
  ["camphor", "C12(C(=O)CC(CC1)C2(C)C)C"],
  ["adamantane", "C12CC3CC(CC(C1)C3)C2"],
  ["cubane", "C12C3C4C5C3C1C5C24"],
  ["artemisinin", DRUGS.artemisinin],
  ["reserpine", "CO[C@H]1[C@@H](C[C@@H]2CN3CCC4=C([C@H]3C[C@@H]2[C@@H]1C(=O)OC)NC5=C4C=CC(=C5)OC)OC(=O)C6=CC(=C(C(=C6)OC)OC)OC"],
  ["vinblastine", "CC[C@@]1(C[C@@H]2C[C@@](C3=C(CCN(C2)C1)C4=CC=CC=C4N3)(C5=C(C=C6C(=C5)[C@]78CCN9[C@H]7[C@@](C=CC9)([C@H]([C@@]([C@@H]8N6C)(C(=O)OC)O)OC(=O)C)CC)OC)C(=O)OC)O"],
  ["cholesterol", "CC(C)CCC[C@@H](C)[C@H]1CC[C@H]2[C@@H]3CC=C4C[C@@H](O)CC[C@]4(C)[C@H]3CC[C@]12C"],
  ["brucine", "COC1=C(C=C2C(=C1)[C@]34CCN5[C@H]3C[C@@H]6[C@@H]7[C@@H]4N2C(=O)C[C@@H]7OCC=C6C5)OC"],
  ["tetrodotoxin", "C([C@@]1([C@@H]2[C@@H]3[C@H](N=C(N[C@]34[C@@H]([C@@](O2)(O[C@H]1C4O)O)O)N)O)O)O"],
  ["ryanodine", "C[C@H]1CC[C@@]2([C@@]3(C[C@]4([C@@]5([C@]([C@H]([C@@]3([C@]5([C@]2([C@@H]1O)O4)O)O)OC(=O)c6ccc[nH]6)(C(C)C)O)C)O)C)O"],
];
const WARNINGS = new Set(["near", "linear", "between", "backwards", "ambiguous", "unspecified", "enhanced"]);
const wedge = (b: { stereo?: number }) => b.stereo === 1 || b.stereo === 6;
for (const [name, smiles] of structures) {
  const m = parseStructure(smiles), raw = indigoLayout(smiles);
  assert.deepEqual(problems(m, stereoFacts(m, true)).filter((p) => WARNINGS.has(p.type)).map((p) => p.message), [], name);
  assert.deepEqual(m.atoms.flatMap((a, i) => (a.enhanced ? [`${i}: ${a.enhanced}`] : [])), [], `${name}: no stereo flags`);
  assert.equal(toInchi(m), toInchi(smiles), `${name}: the same stereoisomer`);
  // Indigo's own drawing's labels, where a wedge does not join two stereocentres (Octet's labeller reads a wide end too).
  const was = cipLabels(raw).atoms, now = cipLabels(m).atoms, joined = new Set(raw.bonds.filter(wedge).map((b) => b.atoms[1]));
  raw.atoms.forEach((_, i) => { if (!joined.has(i)) assert.equal(now[i], was[i], `${name}: the CIP label of atom ${i + 1}`); });
  assert.equal(Object.values(now).filter(Boolean).length, smiles.match(/@+/g)?.length ?? 0, `${name}: every stereocentre labelled`);
  // One wedge or hash for each stereocentre, its narrow end on the centre.
  const centres = m.bonds.filter(wedge).map((b) => b.atoms[0]);
  assert.equal(new Set(centres).size, centres.length, `${name}: one wedge a centre`);
  // An H drawn for a wedge sits clear of every other bond, so its label does not cover one.
  for (let i = raw.atoms.length; i < m.atoms.length; i++) {
    const q = m.atoms[i].location;
    for (const b of m.bonds.filter((x) => !x.atoms.includes(i))) {
      const [r, s] = b.atoms.map((k) => m.atoms[k].location), dx = s[0] - r[0], dy = s[1] - r[1];
      const f = Math.max(0, Math.min(1, ((q[0] - r[0]) * dx + (q[1] - r[1]) * dy) / (dx * dx + dy * dy)));
      assert.ok(Math.hypot(r[0] + f * dx - q[0], r[1] + f * dy - q[1]) >= 0.4, `${name}: the H at atom ${i + 1} is on a bond`);
    }
  }
}
// Taxol is the issue's first structure: Indigo's own drawing puts two carbons on bonds (C41 and C42 in the report).
assert.ok(problems(indigoLayout(DRUGS.paclitaxel)).some((p) => p.type === "near"));
// Strychnine's ring-fusion centres take wedged H atoms, as ChemDraw draws them.
{
  const m = parseStructure(DRUGS.strychnine), hs = m.bonds.filter((b) => wedge(b) && m.atoms[b.atoms[1]].label === "H");
  assert.ok(hs.length >= 3, `strychnine has ${hs.length} wedged H atoms`);
}
// A SMILES that sets and or or groups (CXSMILES) keeps its flags, and each centre it sets absolutely shows abs.
{
  const m = parseStructure("C[C@H](O)C[C@@H](N)CC |&1:1|");
  assert.deepEqual(m.atoms.flatMap((a, i) => (a.enhanced ? [[i, a.enhanced]] : [])), [[1, "&1"], [4, "abs"]]);
}
// A structure with no stereocentres and no crowding comes out as Indigo lays it out.
for (const smiles of ["CC(=O)Nc1ccc(O)cc1", "c1ccc2ccccc2c1", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"])
  assert.deepEqual(parseStructure(smiles).atoms.map((a) => a.location), indigoLayout(smiles).atoms.map((a) => a.location), smiles);
console.log(`natural.check: ${structures.length} bridged and caged structures drawn cleanly, with their stereochemistry`);
