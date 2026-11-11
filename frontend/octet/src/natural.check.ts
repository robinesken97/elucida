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
  // PubChem's (CID 11174599): the SMILES this file had before is another stereoisomer.
  ["tetrodotoxin", "C([C@@]1([C@H]2[C@@H]3[C@H](N=C(N[C@@]34[C@@H]([C@@H]1O[C@]([C@H]4O)(O2)O)O)N)O)O)O"],
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
// With Show Stereochemistry on, each is drawn with no warning and as the same stereoisomer as its SMILES: a macrocycle's
// E double bonds stay E (sirolimus); a cage's bridgeheads (adamantane, cubane, DABCO), a bridgehead N its ring system
// sets (quinine, strychnine), a phosphate's P (ITP), an indole's N (K-252a), a 4-arylpiperidine's C4 and the
// bridgeheads of a bicyclic that is its own mirror image (norbornene, tropinone) are not unset;
// an N@ with three bonds gets no drawn H (corymine); a CH2 marked @ gets no wedge (cryogenine); C60 is a Schlegel diagram.
const cipOn = (m: ReturnType<typeof parseStructure>) => ({ ...m, atoms: m.atoms.map((a) => ({ ...a, cip: true as const })) });
const shown = (smiles: string) => { const m = cipOn(parseStructure(smiles)); return problems(m, stereoFacts(m, true)).filter((p) => WARNINGS.has(p.type)); };
for (const [name, smiles] of [
  ["sirolimus", "CO[C@@H]1C[C@H](C[C@@H](C)[C@@H]2CC(=O)[C@H](C)\\C=C(C)\\[C@@H](O)[C@@H](OC)C(=O)[C@H](C)C[C@H](C)\\C=C\\C=C\\C=C(C)\\[C@H](C[C@@H]3CC[C@@H](C)[C@@](O)(O3)C(=O)C(=O)N4CCCC[C@H]4C(=O)O2)OC)CC[C@H]1O"],
  ["adamantane", "C1C2CC3CC1CC(C2)C3"], ["cubane", "C12C3C4C1C5C2C3C45"], ["DABCO", "C1CN2CCN1CC2"],
  ["norbornene", "C1CC2CC1C=C2"], ["tropinone", "CN1C2CCC1CC(=O)C2"], ["7-oxanorbornene", "C1=CC2CCC1O2"], ["bicyclo[3.2.1]octane", "C1CC2CCC(C1)C2"],
  ["quinine", structures.find(([n]) => n === "quinine")![1]], ["strychnine", DRUGS.strychnine], ["1-methyl-4-phenylpiperidine", "CN1CCC(CC1)c1ccccc1"],
  ["ITP", "C1=NC2=C(C(=O)N1)N=CN2[C@H]3[C@@H]([C@@H]([C@H](O3)COP(=O)(O)OP(=O)(O)OP(=O)(O)O)O)O"],
  ["K-252a", "C[C@@]12[C@](C[C@@H](O1)N3C4=CC=CC=C4C5=C6C(=C7C8=CC=CC=C8N2C7=C53)CNC6=O)(C(=O)OC)O"],
  ["corymine", "C(OC)(=O)[C@@]12[C@]34[C@@]5([C@@](C[C@]1(/C(=C\\C)/C[N@@]5CC3)[H])(O[C@H]2O)[H])N(C)C=6C4=CC=CC6"],
  ["cryogenine", "[H][C@]1([C@H]2N([C@@H]3C4=CC(=C(C=C4C5=C(C=CC(=C5)/C=C\\C(=O)O[C@@H](C2)C3)O)OC)OC)CCC1)[H]"],
  ["C60", "C12=C3C4=C5C6=C1C7=C8C9=C1C%10=C%11C(=C29)C3=C2C3=C4C4=C5C5=C9C6=C7C6=C7C8=C1C1=C8C%10=C%10C%11=C2C2=C3C3=C4C4=C5C5=C%11C%12=C(C6=C95)C7=C1C1=C%12C5=C%11C4=C3C3=C5C(=C81)C%10=C23"],
  // A wedge from a quaternary centre whose neighbours are all stereocentres, to one with its own wedge (ginkgolide B).
  ["ginkgolide B", "C[C@@H]1C(=O)O[C@@H]2[C@]1([C@@]34C(=O)O[C@H]5[C@]3([C@@H]2O)[C@@]6([C@@H](C5)C(C)(C)C)[C@H](C(=O)O[C@H]6O4)O)O"],
  // A 3-substituted quinuclidine's C4 and N1 are not stereocentres (InChI reads them the same either way).
  ["(R)-quinuclidin-3-ol", "O[C@H]1CN2CCC1CC2"],
  // Indigo cannot make this pterin Kekulé (c(=N) beside [nH]); Octet does, so it has an InChI.
  ["sapropterin", "C[C@H](O)[C@H](O)[C@H]1CNc2[nH]c(=N)nc(O)c2N1"],
  // Indigo's own wedges leave four of this cage's centres open; InChI says which wedges to turn or take away.
  ["Jiadifenolide", "C[C@@H]1CC[C@]23[C@@]14C[C@H]([C@@]5([C@]2(COC5=O)C)O)O[C@@]4(C(=O)O3)O"],
  // An allene's and an isothiocyanate's middle carbon shows its label, so it is not lost in line.
  ["phenylallene", "C=C=Cc1ccccc1"], ["phenyl isothiocyanate", "S=C=Nc1ccccc1"],
  // An atom on a bond that turning a side group 10° clears (kobophenol A, trabectedin).
  ["kobophenol A", "C1=CC(=CC=C1[C@@H]2[C@H]([C@H]([C@H](O2)C3=CC=C(C=C3)O)C4=CC(=CC5=C4[C@@H]([C@H](O5)C6=CC=C(C=C6)O)C7=CC(=CC8=C7[C@H]([C@@H](O8)C9=CC=C(C=C9)O)C1=CC(=CC(=C1)O)O)O)O)C1=CC(=CC(=C1)O)O)O"],
  ["trabectedin", "CC1=C(C(=C2[C@@H]3[C@@H]4[C@H]5C6=C([C@@H](N4[C@H]([C@@H](N3C)CC2=C1)O)COC(=O)[C@@]7(CS5)C8=CC(=C(C=C8CCN7)O)OC)C9=C(C(=C6OC(=O)C)C)OCO9)O)OC"],
  // An atom on a bond in a cage too tangled to draw flat, which only stepping the atoms round clears.
  ["hypercubane", "C/1=C/C\\28/C=C\\C\\39\\C=C/C\\46/C=C\\C17/C=C\\C/5%15\\C=C/C%13(/C=C2)\\C=C/C%11(/C=C3)\\C=C/C(/C=C4)(\\C=C5)C%12%17C6%10C7%16C8%14C9%10C%11%12C%13%14C%15%16%17"],
  // Biapenem's C6' between a triazolium's two N (alike, but for where the charge is drawn), and a sarcophagine's
  // bridgeheads (three arms alike), are no stereocentres.
  ["biapenem", "C[C@@H]1[C@@H]2[C@H](C(=O)N2C(=C1SC3CN4C=NC=[N+]4C3)C(=O)[O-])[C@@H](C)O"],
  ["sarcophagine", "C1CNCC2CNCCNCC(CN1)CNCCNC2"],
  // A structure of over 100 atoms whose layouts all have an atom in line: its best is cleaned up too.
  ["quinolidomicin A1", "CO[C@H](CC[C@@H](C)/C=C/C=C/[C@H]1C[C@@H](O)C[C@@H](O)CCCC[C@H](C)CC[C@@H](O)C[C@@H](O)C/C=C\\C=C/C=C/[C@H](O)CC(=O)C[C@H](O)C/C=C\\C=C\\[C@@H](O)C[C@H](O)C[C@@H](O)CC[C@H](C)[C@H](O)C[C@@H](O)[C@@H](C)[C@H](O)/C(C)=C/C=C\\[C@H](C)[C@@H](O)[C@H](C)[C@H]2O[C@@](O)(CC(=O)O1)C[C@H](O)[C@@H]2C)C1=C(SC)C(=O)C=C(O)C1=O"],
]) {
  assert.deepEqual(shown(smiles).map((p) => p.message), [], `${name}, Show Stereochemistry on`);
  assert.equal(toInchi(parseStructure(smiles)), toInchi(smiles), `${name}: the same stereoisomer`);
}
// An atom on a bond is moved off, or the bond is (their SMILES leave centres unset): boromycin; PCBM, written aromatic
// (Indigo takes a second to make a fullerene Kekulé where it checks its answer); and ziconotide, of over 100 atoms with
// no stereochemistry in its SMILES, which otherwise keeps Indigo's layout.
for (const [name, smiles] of [["boromycin", "CC(C)[C@@H]([NH3+])C(=O)O[C@H](C)[C@@H]1C/C=C/CC[C@H](O)C(C)(C)[C@@H]2CC[C@@H](C)[C@]3(O2)O[B-]24OC(C(=O)O1)[C@@]1(O[C@@H](CC[C@H]1C)C(C)(C)[C@H](O)CCC[C@@H]1C[C@H](OC(=O)C3O2)[C@@H](C)O1)O4"], ["PCBM", "COC(=O)CCCC1(c2ccccc2)C23c4c5c6c7c8c9c(c%10c%11c2c2c%12c4c4c%13c5c5c7c7c8c8c%14c9c%10c9c%10c%11c2c2c%11c%12c4c4c%12c%13c5c5c7c7c8c8c%14c9c9c%10c2c2c%11c4c4c%12c5c7c5c8c9c2c45)C613"], ["ziconotide", "CC1C(=O)NC(C(=O)NC2CSSCC3C(=O)NC(C(=O)NC(C(=O)NCC(=O)NC(C(=O)NC(CSSCC(C(=O)NC(CSSCC(C(=O)NC(C(=O)NCC(=O)NC(C(=O)NCC(=O)N1)CCCCN)CCCCN)N)C(=O)NC(C(=O)NCC(=O)NC(C(=O)N3)CO)C(C)O)NC(=O)C(NC(=O)C(NC(=O)C(NC(=O)C(NC(=O)C(NC(=O)C(NC2=O)CO)CCCNC(=N)N)CC(C)C)CCSC)CC4=CC=C(C=C4)O)CC(=O)O)C(=O)N)CCCCN)CO)CCCNC(=N)N)CCCCN"]]) {
  const m = parseStructure(smiles);
  assert.deepEqual(problems(m, stereoFacts(m)).filter((p) => p.type === "near").map((p) => p.message), [], name);
  assert.equal(toInchi(m), toInchi(smiles), `${name}: the same stereoisomer`);
}
// A wedge Indigo draws where its layout shows no hand (bonds in line) is placed again, not left between two
// stereocentres (zenazocine, MR-2034; their SMILES leave a centre unset). A protonated amine's N inverts, so it is no
// stereocentre (fumigaclavine B). A 295-atom peptide whose layouts all read wrong (centres drawn in a T, where InChI
// reads no wedge) is cleaned up and given H atoms at those centres (charybdotoxin).
for (const smiles of ["CC(C)CCC(=O)CCC1([C@H]2CC3=C([C@@]1(CCN2C)C)C=C(C=C3)O)C", "CC1[C@H]2Cc3ccc(O)cc3[C@]1(C)CCN2C[C@H]1CCCO1"]) {
  assert.deepEqual(shown(smiles).filter((p) => p.type === "between").map((p) => p.message), [], smiles);
  assert.equal(toInchi(parseStructure(smiles)), toInchi(smiles), smiles);
}
assert.ok(!shown("C[C@@H]1C[NH+]([C@@H]2CC3=CNC4=CC=CC(=C34)C2[C@H]1O)C").some((p) => p.message.startsWith("N")), "fumigaclavine B: its N+");
{
  const charybdotoxin = "CSCC[C@@H]1NC(=O)[C@@H]2CSSC[C@H](NC(=O)[C@H](CO)NC(=O)[C@@H](NC(=O)[C@H](CC(N)=O)NC(=O)[C@@H](NC(=O)[C@H](Cc3ccccc3)NC(=O)[C@@H]3CCC(=O)N3)[C@@H](C)O)C(C)C)C(=O)N[C@@H]([C@@H](C)O)C(=O)N[C@@H]([C@@H](C)O)C(=O)N[C@@H](CO)C(=O)N[C@@H](CCCCN)C(=O)N[C@@H](CCC(=O)O)C(=O)N[C@H]3CSSC[C@H](NC(=O)[C@H](CCCCN)NC(=O)[C@H](CCCCN)NC(=O)[C@H](CC(N)=O)NC1=O)C(=O)N[C@@H](CCCNC(=N)N)C(=O)N[C@H](C(=O)N[C@@H](Cc1ccc(O)cc1)C(=O)N[C@@H](CO)C(=O)O)CSSC[C@H](NC(=O)[C@H](C(C)C)NC(=O)[C@H](CO)NC(=O)[C@H](Cc1c[nH]c4ccccc14)NC3=O)C(=O)N[C@@H](CCC(N)=O)C(=O)N[C@@H](CCCNC(=N)N)C(=O)N[C@@H](CC(C)C)C(=O)N[C@@H](Cc1cnc[nH]1)C(=O)N[C@@H](CC(N)=O)C(=O)N[C@@H]([C@@H](C)O)C(=O)N[C@@H](CO)C(=O)N[C@@H](CCCNC(=N)N)C(=O)NCC(=O)N[C@@H](CCCCN)C(=O)N2";
  assert.equal(toInchi(parseStructure(charybdotoxin)), toInchi(charybdotoxin), "charybdotoxin: the same stereoisomer");
}
// A true unset stereocentre still warns: a chiral cage (twistane), camphor, norcamphor, a 2,5-dimethylbicyclo[2.2.2]-
// octa-2,5-diene (chiral, though its bridgeheads are alike), Tröger's base, 2-norbornanol and a tropane drawn with no
// wedges, cis- or trans-4-methylcyclohexanol, a sulfoxide's S and a phosphorothioate's P.
for (const smiles of ["C1CC2CC3C1CC2CC3", "C12(C(=O)CC(CC1)C2(C)C)C", "O=C1CC2CCC1C2", "CC1=CC2CCC1C=C2C", "Cc1ccc2c(c1)CN1Cc3cc(C)ccc3N(C2)C1", "OC1CC2CCC1C2", "CN1C2CCC1CC(O)C2", "CC1CCC(O)CC1", "CS(=O)c1ccccc1", "COP(=S)(O)OCC"])
  assert.ok(shown(smiles).some((p) => p.type === "unspecified"), `${smiles}: unset`);
// Zacopride's SMILES leaves its quinuclidine's C3 unset: that warns, and its C4 and N1 do not.
assert.deepEqual(shown("COC1=CC(=C(C=C1C(=O)NC2CN3CCC2CC3)Cl)N").map((p) => p.type), ["unspecified"], "zacopride");
// A double bond a SMILES that sets stereochemistry leaves open is drawn crossed (norelgestromin's oxime), one it sets
// is not (in a ring of 8, E stays E), and a crossed double bond leaves E or Z open in the InChI.
{
  const oxime = "C#C[C@]1(O)CC[C@H]2[C@@H]3CCC4=CC(=NO)CC[C@@H]4[C@H]3CC[C@@]21CC", m = parseStructure(oxime);
  assert.equal(m.bonds.filter((b) => b.display === "either").length, 1, "norelgestromin: the oxime crossed");
  assert.equal(toInchi(m), toInchi(oxime), "norelgestromin: the same stereoisomer");
  for (const ring of ["C1CCC/C=C/CC1", "C1CCC/C=C\\CC1"]) {
    const e = parseStructure(ring);
    assert.ok(!e.bonds.some((b) => b.display === "either") && toInchi(e) === toInchi(ring), ring);
  }
  const butene = parseStructure("C/C=C/C");
  assert.equal(toInchi({ ...butene, bonds: butene.bonds.map((b) => (b.type === 2 ? { ...b, display: "either" as const } : b)) }), toInchi("CC=CC"), "a crossed double bond");
}
// No label lies over a bond (within 0.3 of a bond length of it) or over another label (within 0.6), and no atom over
// another (within 0.35): an O on a bond in a cage (artemisinin), an N on a C-O bond (saxitoxin), two O labels (lolitrem
// B), an N and an S (glionitrin A), two carbons (α-amanitin), and a Cl by a bond Indigo stretches across a cage (endrin
// aldehyde, laid out again). Each is moved off, as the same stereoisomer.
for (const [name, smiles] of [
  ["artemisinin", "C[C@@H]1CC[C@H]2[C@H](C(=O)O[C@H]3[C@@]24[C@H]1CC[C@](O3)(OO4)C)C"],
  ["saxitoxin", "C1CN2C(=N[C@H]([C@H]3[C@]2(C1(O)O)NC(=N3)N)COC(=O)N)N"],
  ["lolitrem B", "CC(=C[C@H]1O[C@H]2[C@@H]3[C@@]4(O3)[C@H](CC[C@]5([C@]4(CC[C@@H]6[C@@]5(c7c(c8c([nH]7)ccc9c8C[C@@H]3[C@@H](C9=O)C(OC3(C)C)(C)C)C6)C)O)C)O[C@@H]2C(O1)(C)C)C"],
  ["glionitrin A", "CN1C(=O)C23CC4=C(N2C(=O)C1(SS3)CO)C=C(C=C4)[N+](=O)[O-]"],
  ["endrin aldehyde", "C1[C@H]([C@@H]2[C@@H]3[C@H]1[C@H]4[C@]5([C@]2(C([C@@]3([C@@]45Cl)Cl)(Cl)Cl)Cl)Cl)C=O"],
  ["α-amanitin", "CC[C@H](C)[C@H]1C(=O)NCC(=O)N[C@H]2C[S@@](=O)C3=C(C[C@@H](C(=O)NCC(=O)N1)NC(=O)[C@@H](NC(=O)[C@@H]4C[C@H](CN4C(=O)[C@@H](NC2=O)CC(=O)N)O)[C@@H](C)[C@H](CO)O)C5=C(N3)C=C(C=C5)O"],
]) {
  const m = parseStructure(smiles), xy = m.atoms.map((a) => a.location), shownAt = (i: number) => m.atoms[i].label !== "C" || !!m.atoms[i].text;
  const gap = (r: number[], p: number[], q: number[]) => {
    const dx = q[0] - p[0], dy = q[1] - p[1], f = Math.max(0, Math.min(1, ((r[0] - p[0]) * dx + (r[1] - p[1]) * dy) / (dx * dx + dy * dy || 1)));
    return Math.hypot(p[0] + f * dx - r[0], p[1] + f * dy - r[1]);
  };
  const over: string[] = [];
  xy.forEach((p, i) => {
    if (shownAt(i)) for (const b of m.bonds) if (!b.atoms.includes(i) && gap(p, xy[b.atoms[0]], xy[b.atoms[1]]) < 0.3) over.push(`${m.atoms[i].label}${i} on a bond`);
    xy.forEach((q, j) => {
      if (j <= i || m.bonds.some((b) => b.atoms.includes(i) && b.atoms.includes(j))) return;
      const d = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (d < 0.35 || (shownAt(i) && shownAt(j) && d < 0.6)) over.push(`${m.atoms[i].label}${i} on ${m.atoms[j].label}${j}`);
    });
  });
  assert.deepEqual(over, [], `${name}: labels and atoms clear`);
  assert.equal(toInchi(m), toInchi(smiles), `${name}: the same stereoisomer`);
}
// No bond passes through a label's ink as render() draws it (its H atoms and charge too, on the side render() puts
// them: OH or HO), and no two labels' ink touch, in Arial at ACS sizes as the editor draws them (a bond length a bond),
// ink within half a px of a bond's middle line or of another label counting: saxitoxin's HO over its HN, vinblastine's
// ester O over its indole NH, the wedge into dexamethasone's 17-OH, and ginkgolide B's crowded cage (PubChem's SMILES,
// 4 November 2026). The same after Clean Up of Indigo's drawing of each, at its own size and scaled to half and twice
// (a label is drawn at its atom's scale).
{
  const { cleanUp } = await import("./chem.ts");
  const { render } = await import("./render.ts");
  const { arialInk } = await import("./cdxml.ts");
  const pt = 4 / 3, ACS = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.6 * pt, size: 10 * pt }, arial = arialInk(ACS.size);
  // Does the segment from a to b cross the box [x0, y0, x1, y1]?
  const crosses = (a: number[], b: number[], [x0, y0, x1, y1]: number[]) => {
    let t0 = 0, t1 = 1;
    const dx = b[0] - a[0], dy = b[1] - a[1];
    for (const [p, q] of [[-dx, a[0] - x0], [dx, x1 - a[0]], [-dy, a[1] - y0], [dy, y1 - a[1]]]) {
      if (!p) { if (q < 0) return false; continue; }
      const r = q / p;
      if (p < 0) { if (r > t1) return false; t0 = Math.max(t0, r); } else { if (r < t0) return false; t1 = Math.min(t1, r); }
    }
    return true;
  };
  for (const [name, smiles] of [
    ["saxitoxin", "C1CN2C(=N[C@H]([C@H]3[C@]2(C1(O)O)NC(=N3)N)COC(=O)N)N"],
    ["vinblastine", "CC[C@@]1(C[C@H]2C[C@@](C3=C(CCN(C2)C1)C4=CC=CC=C4N3)(C5=C(C=C6C(=C5)[C@]78CCN9[C@H]7[C@@](C=CC9)([C@H]([C@@]([C@@H]8N6C)(C(=O)OC)O)OC(=O)C)CC)OC)C(=O)OC)O"],
    ["dexamethasone", "C[C@@H]1C[C@H]2[C@@H]3CCC4=CC(=O)C=C[C@@]4([C@]3([C@H](C[C@@]2([C@]1(C(=O)CO)O)C)O)F)C"],
    ["ginkgolide B", "C[C@@H]1C(=O)O[C@@H]2[C@]1([C@@]34C(=O)O[C@H]5[C@]3([C@@H]2O)[C@@]6([C@@H](C5)C(C)(C)C)[C@H](C(=O)O[C@H]6O4)O)O"],
  ]) {
    const over = (m: ReturnType<typeof parseStructure>) => {
      const d = render(m, ACS, arial, ACS.bond), k = d.scale, at = (i: number) => [m.atoms[i].location[0] * k, -m.atoms[i].location[1] * k];
      const box = d.label.map((b) => b && [b[0] - 0.5, b[1] - 0.5, b[2] + 0.5, b[3] + 0.5]), name_ = (i: number) => `${m.atoms[i].label}${i + 1}`, out: string[] = [];
      box.forEach((b, i) => {
        if (!b) return;
        for (const x of m.bonds) if (!x.atoms.includes(i) && crosses(at(x.atoms[0]), at(x.atoms[1]), b)) out.push(`${name_(i)} under the bond ${x.atoms.map((j) => j + 1).join("-")}`);
        box.forEach((c, j) => { if (c && j > i && b[0] < c[2] && c[0] < b[2] && b[1] < c[3] && c[1] < b[3]) out.push(`${name_(i)} touching ${name_(j)}`); });
      });
      return out;
    };
    const m = parseStructure(smiles);
    assert.deepEqual(over(m), [], `${name}: labels clear as drawn`);
    assert.equal(toInchi(m), toInchi(smiles), `${name}: the same stereoisomer`);
    const raw = parseStructure(smiles, false);
    for (const scale of [1, 0.5, 2]) {
      const cleaned = cleanUp({ ...raw, atoms: raw.atoms.map((a) => ({ ...a, location: [a.location[0] * scale, a.location[1] * scale, 0] as [number, number, number], scale })) });
      assert.deepEqual(over(cleaned), [], `${name}: labels clear after Clean Up at ${scale}`);
      assert.equal(toInchi(cleaned), toInchi(smiles), `${name}: the same stereoisomer after Clean Up at ${scale}`);
    }
  }
}
console.log(`natural.check: ${structures.length} bridged and caged structures drawn cleanly, with their stereochemistry`);
