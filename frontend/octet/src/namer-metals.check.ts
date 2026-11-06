// Run: node src/namer-metals.check.ts. Names for structures with metal atoms (metals.ts). Each name becomes a structure
// (OPSIN), Octet names the structure, and OPSIN must read Octet's name back as the same structure (same standard
// InChI). Structures OPSIN reads no correct name for (dative bonds, chelate rings) must get no name.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { sandwichIons } from "./metals.ts";
import { addGroupAt } from "./edit.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-metals.check: skipped (no OPSIN build)"); process.exit(0); }
const pack = readFileSync(new URL("opsin-data.bin", dir));
const files = new Map<string, Int8Array>();
for (let p = 0; ; ) {
  const n = pack.readUInt16BE(p); p += 2;
  if (!n) break;
  const name = pack.toString("latin1", p, p + n); p += n;
  const size = pack.readInt32BE(p); p += 4;
  files.set(name, new Int8Array(pack.buffer, pack.byteOffset + p, size)); p += size;
}
(globalThis as { opsinResource?: unknown }).opsinResource = (name: string) => files.get(name) ?? null;
const opsin = await import(new URL("opsin.js", dir).href);
opsin.init();
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();
const convert = (s: string, f: string, dearomatize = false) => {
  const o = new indigo.MapStringString();
  if (dearomatize) o.set("dearomatize-on-load", "true");
  try { return indigo.convert(s, f, o).trim(); } finally { o.delete(); }
};
// The structure and its CIP labels, read from SMILES by Indigo (Kekulé bonds).
const parsed = (smiles: string) => {
  const o = new indigo.MapStringString();
  o.set("output-content-type", "application/json");
  o.set("dearomatize-on-load", "true");
  try {
    const ket = JSON.parse(JSON.parse(indigo.calculateCip(smiles, "ket", o)).struct);
    // Several fragments (a salt): one molecule with all of them.
    const atoms: { label: string; charge?: number; cip?: string }[] = [], bonds: { type: number; atoms: [number, number]; cip?: string }[] = [];
    for (const { $ref } of ket.root.nodes) {
      const f = ket[$ref], base = atoms.length;
      if (f?.type !== "molecule") continue;
      atoms.push(...f.atoms);
      bonds.push(...f.bonds.map((b: { type: number; atoms: [number, number]; cip?: string }) => ({ ...b, atoms: [b.atoms[0] + base, b.atoms[1] + base] })));
    }
    return { atoms, bonds };
  } finally { o.delete(); }
};
const molOf = (smiles: string): Mol => {
  const m = parsed(smiles);
  return { atoms: m.atoms.map((a) => ({ label: a.label, charge: a.charge, location: [0, 0, 0] as [number, number, number] })), bonds: m.bonds.map((b) => ({ type: b.type, atoms: b.atoms })) };
};
// The CIP labels Octet gives (cip.ts) the structure as Indigo lays the SMILES out (with wedges), on the atoms and bonds
// of `parsed`. A drawn double bond always has a geometry; one the SMILES leaves open (Indigo gives it no label) has no
// E or Z.
const cipOf = (smiles: string) => {
  const o = new indigo.MapStringString(), p = parsed(smiles), m: Mol = { atoms: [], bonds: [] };
  o.set("output-content-type", "application/json");
  o.set("dearomatize-on-load", "true");
  try {
    const ket = JSON.parse(JSON.parse(indigo.layout(smiles, "ket", o)).struct);
    for (const { $ref } of ket.root.nodes) {
      const f = ket[$ref], base = m.atoms.length;
      if (f?.type !== "molecule") continue;
      m.atoms.push(...f.atoms.map((a: Mol["atoms"][number]) => ({ label: a.label, location: a.location, charge: a.charge, isotope: a.isotope, ...(a.radical ? { radical: a.radical === 1 ? 3 : a.radical - 1 } : {}) })));
      m.bonds.push(...f.bonds.map((b: Mol["bonds"][number]) => ({ type: b.type, atoms: [b.atoms[0] + base, b.atoms[1] + base] as [number, number], ...(b.stereo === 1 || b.stereo === 6 ? { stereo: b.stereo } : {}) })));
    }
  } finally { o.delete(); }
  if (m.atoms.length !== p.atoms.length || m.bonds.length !== p.bonds.length) throw new Error(`cipOf: Indigo read ${smiles} two ways`);
  const c = cipLabels(m);
  return { atoms: c.atoms, bonds: p.bonds.map((b, k) => (b.cip ? c.bonds[k] : undefined)) };
};
// A structure (a name OPSIN reads, or "smiles:" and SMILES) and Octet's name for it, or why there is none.
const structure = (input: string) => {
  const smiles = input.startsWith("smiles:") ? input.slice(7) : opsin.parseToSmiles(input);
  assert.ok(smiles, `OPSIN reads ${input}`);
  return { smiles, ...iupacNameWhy(graphOf(molOf(smiles), cipOf(smiles))!) };
};
// Octet names the structure, and OPSIN reads the name back as the same structure.
const roundTrip = (input: string) => {
  const { smiles, name, why } = structure(input);
  assert.ok(name, `no name for ${input} (${smiles}): ${why}`);
  const back = opsin.parseToSmiles(name);
  assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${input} -> ${name}, a different structure`);
  return name;
};

// Every name here is named, and read back as the same structure.
const names = [
  // Lone metal atoms and ions.
  "sodium", "iron", "platinum", "gold", "copper", "uranium", "iron(3+)",
  // Metallocenes as parents (IR-10.2.6), with suffixes and prefixes, and as the prefix ferrocenyl.
  "ferrocene", "ruthenocene", "osmocene", "cobaltocene", "nickelocene", "chromocene", "vanadocene", "titanocene", "zirconocene",
  "ferrocenecarbaldehyde", "ferrocenecarboxylic acid", "ferrocene-1,1'-dicarboxylic acid", "ferrocenol", "ferrocene-1,1'-diol",
  "ferrocenamine", "ferrocenethiol", "ferrocenesulfonic acid", "ferrocenecarbonitrile", "ferrocenecarboxamide", "methyl ferrocenecarboxylate",
  "ferrocenecarbonyl chloride", "ferrocene-1,1'-dicarbonyl dichloride", "ferrocenesulfonyl chloride", "N,N-dimethylferrocenamine",
  "N-methylferrocenecarboxamide", "N1,N1'-dimethylferrocene-1,1'-diamine", "methylferrocene", "1,1'-dimethylferrocene",
  "1,2-dimethylferrocene", "1,3-dimethylferrocene", "decamethylferrocene", "ethenylferrocene", "chloroferrocene", "phenylferrocene",
  "1'-methylferrocene-1-carboxylic acid", "acetylferrocene", "1,1'-diacetylferrocene", "ferrocenylmethanol", "(2-methylferrocenyl)methanol",
  "N,N-dimethyl-1-ferrocenylmethanamine", "1,1'-bis(diphenylphosphanyl)ferrocene", "2-ferrocenylpyridine", "ferrocenylacetic acid",
  "ferrocenyl acetate", "ferrocenylmethyl acetate", "N-ferrocenylacetamide", "[1'-(hydroxymethyl)ferrocenyl]methanol",
  "ferrocenide", "ruthenocenide", "smiles:[CH-]1C=C[C-]=C1.[CH-]1C=CC=C1.[Fe+2]", "nitroferrocene", "1,1'-dinitroferrocene",
  "4-ferrocenylbenzoic acid", "3-ferrocenylpropanoic acid", "ferrocenylmethyl 4-nitrobenzoate",
  // Organometallic compounds by additive names (IR-9, P-69).
  "butyllithium", "sec-butyllithium", "tert-butyllithium", "methyllithium", "phenyllithium", "(4-methoxyphenyl)lithium", "ethynyllithium",
  "methylmagnesium bromide", "phenylmagnesium bromide", "ethylmagnesium chloride", "isopropylmagnesium chloride", "vinylmagnesium bromide",
  "allylmagnesium bromide", "(4-fluorophenyl)magnesium bromide", "dimethylmagnesium", "diethylzinc", "diphenylzinc", "methylcopper",
  "tetramethyltitanium", "chlorotrimethyltitanium", "dichlorobis(cyclopentadienyl)titanium", "bis(cyclopentadienyl)iron",
  "tetrakis(dimethylamino)titanium", "pentacarbonyliron", "tetracarbonylnickel", "hexacarbonylchromium", "hexacarbonylmolybdenum",
  "hexacarbonyltungsten", "bromopentacarbonylmanganese", "pentacarbonyl(methyl)manganese", "dicyanozinc", "osmium tetroxide",
  "copper(II) oxide", "iron oxychloride", "uranyl",
  // Salts and metal halides, oxides and alkoxides (IR-5).
  "copper(II) acetate", "copper(I) acetate", "palladium(II) acetate", "iron(III) chloride", "iron(II) chloride", "iron(II) sulfate",
  "copper(II) sulfate", "manganese(III) acetate", "cobalt(II) chloride", "ruthenium(III) chloride", "rhodium(III) chloride",
  "gold(III) chloride", "titanium tetrachloride", "titanium(IV) isopropoxide", "zirconium(IV) chloride", "chromium trioxide",
  "manganese dioxide", "iron(III) oxide", "scandium(III) triflate", "samarium(II) iodide", "copper(I) iodide", "ethylzinc iodide",
  "uranyl nitrate", "potassium dichromate", "sodium chromate", "potassium perrhenate", "sodium amide", "calcium diamide",
  "lithium nitride", "calcium nitride", "beryllium chloride", "cadmium chloride",
  // Oxoacids (IR-8 Table).
  "chromic acid", "dichromic acid", "permanganic acid", "perrhenic acid", "technetic acid",
  // Drawn with bonds to the metal: named as the salt of its ions (InChI, as IUPAC, counts these bonds as ionic).
  "smiles:CC(=O)O[Na]", "smiles:CC(=O)O[Ca]OC(C)=O", "smiles:Cl[Fe](Cl)Cl", "smiles:CC(=O)O[Cu]OC(C)=O", "smiles:C[O][Na]",
  "smiles:CC(C)O[Ti](OC(C)C)(OC(C)C)OC(C)C", "smiles:[Os](Cl)(Cl)Cl", "smiles:Cl[Mg]Cl", "smiles:FC(F)(F)S(=O)(=O)O[Cu]OS(=O)(=O)C(F)(F)F",
  // Hydrates (IR-5.5).
  "copper(II) sulfate pentahydrate", "sodium acetate trihydrate", "iron(III) chloride hexahydrate", "magnesium sulfate heptahydrate",
  "sodium carbonate decahydrate", "cobalt(II) chloride dihydrate", "smiles:CC(=O)O[Na].O.O.O",
  // Metallocenes with the negative charge on another ring carbon.
  "smiles:[CH-]1C=CC(C=O)=C1.[CH-]1C=CC=C1.[Fe+2]", "smiles:C1=C[C-](C)C=C1.C1=CC=C[CH-]1.[Ru+2]",
];
const out = names.map((n) => `${n} -> ${roundTrip(n)}`);
console.log(`namer-metals.check: ${out.length} named and read back`);

// The names themselves, for the forms chosen: metallocene locants 1 to 5 and 1' to 5'; additive names with the
// ligands in alphabetical order, each after the first in brackets; oxidation numbers for metals of several charges.
const expect: [string, string][] = [
  ["ferrocene", "ferrocene"], ["1,1'-dimethylferrocene", "1,1'-dimethylferrocene"], ["decamethylferrocene", "1,1',2,2',3,3',4,4',5,5'-decamethylferrocene"],
  ["ferrocenecarbaldehyde", "ferrocenecarbaldehyde"], ["ferrocen-1-ol", "ferrocenol"], ["1'-methylferrocene-1-carboxylic acid", "1'-methylferrocene-1-carboxylic acid"],
  ["ferrocenylmethanol", "ferrocenylmethanol"], ["(2-methylferrocenyl)methanol", "(2-methylferrocenyl)methanol"],
  ["1,1'-bis(diphenylphosphanyl)ferrocene", "[1'-(diphenylphosphanyl)ferrocenyl](diphenyl)phosphane"],
  ["acetylferrocene", "1-ferrocenylethan-1-one"], ["methyl ferrocenecarboxylate", "methyl ferrocenecarboxylate"],
  ["butyllithium", "butyllithium"], ["methylmagnesium bromide", "bromo(methyl)magnesium"], ["isopropylmagnesium chloride", "chloro(propan-2-yl)magnesium"],
  ["diethylzinc", "diethylzinc"], ["pentacarbonyliron", "pentacarbonyliron"], ["bromopentacarbonylmanganese", "bromo(pentacarbonyl)manganese"],
  ["dichlorobis(cyclopentadienyl)titanium", "dichlorobis(cyclopenta-2,4-dien-1-yl)titanium"], ["osmium tetroxide", "tetraoxoosmium"],
  ["copper(II) acetate", "copper(II) acetate"], ["iron(III) chloride", "iron(III) chloride"], ["titanium tetrachloride", "titanium(IV) chloride"],
  ["ethylzinc iodide", "ethylzinc(1+) iodide"], ["uranyl", "dioxouranium(2+)"], ["chromic acid", "chromic acid"], ["sodium", "sodium"],
  ["lithium nitride", "lithium nitride"], ["sodium amide", "sodium amide"], ["smiles:CC(=O)O[Na]", "sodium acetate"],
  ["zinc trifluoromethanesulfonate", "zinc bis(trifluoromethanesulfonate)"], ["ferrocenide", "ferrocenide"],
  ["copper(II) sulfate pentahydrate", "copper(II) sulfate pentahydrate"],
];
for (const [input, name] of expect) assert.equal(structure(input).name, name, input);
console.log(`namer-metals.check: ${expect.length} names as expected`);

// No name OPSIN can read for these: dative bonds and chelate rings need κ and η (IR-9.2.4, IR-10.2.5), which OPSIN does
// not read. Sam's tris(2,2'-bipyridine)ruthenium(2+), a bis(terpyridine)osmium complex, Jacobsen's Mn(salen)Cl,
// dichloridobis(pyridine)platinum and tetrakis(triphenylphosphane)palladium(0) as drawn. (Cisplatin cannot be tested
// here: Indigo's graph keeps no hydrogen count, so its H3N-Pt reads as H2N-Pt.)
const none: [string, string][] = [
  ["smiles:C12C3=CC=CC=N3[Ru]34(N5=CC=CC=C5C5N3=CC=CC=5)(N=1C=CC=C2)N1=C(C2C=CC=CN=24)C=CC=C1", "chelate ring"],
  ["smiles:C12=N([Os]345(N6C(C7N3=C(C3C=CC=CN=34)C=CC=7)=CC=CC=6)N3=C1C=CC=C3C1N5=CC=CC=1)C=CC=C2", "chelate ring"],
  ["smiles:[C@H]12[N]3[Mn]4(Cl)([N]([C@@H]1CCCC2)=CC1=CC(C(C)(C)C)=CC(C(C)(C)C)=C1O4)OC1=C(C=3)C=C(C(C)(C)C)C=C1C(C)(C)C", "chelate ring"],
  ["smiles:Cl[Pt](Cl)(N1=CC=CC=C1)N1=CC=CC=C1", "dative bond"],
  // Two metals sharing an O: the standard InChI of a drawn KO-MnO3 is not that of potassium permanganate.
  ["smiles:[Mn](=O)(=O)(=O)O[K]", "several metal atoms"],
  // A metallocene beside another piece is not the metallocene alone.
  ["smiles:[CH-]1C=CC=C1.[CH-]1C=CC=C1.[Fe+2].CCO", "salt"],
  ["smiles:C1=CC=C(C=C1)P(C1=CC=CC=C1)(C1=CC=CC=C1)[Pd](P(C1=CC=CC=C1)(C1=CC=CC=C1)C1=CC=CC=C1)(P(C1=CC=CC=C1)(C1=CC=CC=C1)C1=CC=CC=C1)P(C1=CC=CC=C1)(C1=CC=CC=C1)C1=CC=CC=C1", "dative bond"],
];
for (const [input, why] of none) {
  const r = structure(input);
  assert.equal(r.name, undefined, `${input} -> ${r.name}`);
  assert.equal(r.why, why, input);
}
console.log(`namer-metals.check: ${none.length} complexes with no name OPSIN reads, as expected`);

// A metallocene drawn with the j key (two Cp rings joined to the metal through multi-centre points) is named as its
// ions, as OPSIN draws it and as its standard InChI has it.
const ketInchi = (m: Mol) => convert(JSON.stringify({ root: { nodes: [{ $ref: "mol0" }] }, mol0: { type: "molecule",
  atoms: m.atoms.map((a) => ({ label: a.label, location: a.location, ...(a.charge ? { charge: a.charge } : {}) })), bonds: m.bonds.map((b) => ({ type: b.type, atoms: b.atoms })) } }), "inchi");
for (const [metal, want] of [["Fe", "ferrocene"], ["Ru", "ruthenocene"], ["Os", "osmocene"], ["Co", "cobaltocene"]]) {
  let m: Mol = { atoms: [{ label: metal, location: [0, 0, 0] }], bonds: [] };
  [m] = addGroupAt(m, 0, "cpLigand");
  [m] = addGroupAt(m, 0, "cpLigand");
  const ions = sandwichIons(m)!, name = iupacNameWhy(graphOf(ions)!).name;
  assert.equal(name, want);
  assert.equal(ketInchi(ions), convert(opsin.parseToSmiles(want), "inchi"), `${want} drawn with j`);
}
// Not a sandwich: one Cp ring on the metal, or an η6 arene.
let half: Mol = { atoms: [{ label: "Fe", location: [0, 0, 0] }], bonds: [] };
[half] = addGroupAt(half, 0, "cpLigand");
assert.equal(sandwichIons(half), undefined);
let arene: Mol = { atoms: [{ label: "Cr", location: [0, 0, 0] }], bonds: [] };
[arene] = addGroupAt(arene, 0, "phenylLigand");
assert.equal(sandwichIons(arene), undefined);
console.log("namer-metals.check: metallocenes drawn with j named as their ions");
