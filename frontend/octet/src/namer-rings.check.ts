// Run: node src/namer-rings.check.ts. Monocycles (Hantzsch–Widman and retained names, indicated and added hydrogen,
// hydro prefixes), ring unsaturation, double-bonded substituents (ylidene) and long chains. Each name becomes a
// structure (OPSIN), Octet names the structure, and OPSIN must read Octet's name back as the same structure (same
// standard InChI). Every one must be named, and none may be wrong.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-rings.check: skipped (no OPSIN build)"); process.exit(0); }
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
const convert = (s: string, f: string) => {
  const o = new indigo.MapStringString();
  try { return indigo.convert(s, f, o).trim(); } finally { o.delete(); }
};
// The structure and its CIP labels, read from SMILES by Indigo (Kekulé bonds).
const parsed = (smiles: string) => {
  const o = new indigo.MapStringString();
  o.set("output-content-type", "application/json");
  o.set("dearomatize-on-load", "true");
  try {
    const ket = JSON.parse(JSON.parse(indigo.calculateCip(smiles, "ket", o)).struct);
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

// Each input (a name, or smiles:...) must get a name that OPSIN reads back as the same structure. With "=", the name
// must also be exactly the one given.
function run(label: string, inputs: string[]) {
  const out: string[] = [];
  for (const input of inputs) {
    const [source, want] = input.split(" = ");
    const smiles = source.startsWith("smiles:") ? source.slice(7) : opsin.parseToSmiles(source);
    assert.ok(smiles, `OPSIN reads ${source}`);
    const g = graphOf(molOf(smiles), cipOf(smiles));
    assert.ok(g, `graph of ${source}`);
    const r = iupacNameWhy(g);
    assert.ok(r.name, `no name for ${source} (${smiles}): ${r.why}`);
    const back = opsin.parseToSmiles(r.name);
    assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${source} -> ${r.name}, a different structure`);
    if (want) assert.equal(r.name, want, source);
    out.push(r.name);
  }
  console.log(`namer-rings.check: ${label} ${out.length}/${inputs.length}`);
}

// Monocycles (P-22.2): Hantzsch–Widman names, retained names, replacement names for large rings; mancude rings with
// indicated hydrogen, added hydrogen and hydro prefixes (P-31.1.4.2.4, P-31.1.4.3.4). Sam's corpus: N-phenylmaleimide,
// N-methylpyridinones and the oxazolidinone.
run("monocycles", [
  "1-phenyl-1H-pyrrole-2,5-dione = 1-phenyl-1H-pyrrole-2,5-dione", "smiles:C1C(=O)N(C)C=CC=1 = 1-methylpyridin-2(1H)-one",
  "smiles:C1C=CN(C)C(=O)C=1C(F)(F)F = 1-methyl-3-(trifluoromethyl)pyridin-2(1H)-one",
  "smiles:O1C[C@H](C2C=CC=CC=2)NC1=O = (4S)-4-phenyl-1,3-oxazolidin-2-one",
  "pyridin-2(1H)-one", "4H-pyran-4-one = 4H-pyran-4-one", "2H-pyran-2-one = 2H-pyran-2-one", "thymine = 5-methylpyrimidine-2,4(1H,3H)-dione",
  "cytosine = 4-aminopyrimidin-2(1H)-one", "isocytosine", "uracil", "barbituric acid", "cyanuric acid", "alloxan", "hydantoin = imidazolidine-2,4-dione",
  "1,3-oxazinane", "1,2,4-triazine", "1,2,3-triazine", "1H-1,2,4-triazole = 1H-1,2,4-triazole", "1H-1,2,3-triazole", "2H-1,2,3-triazole",
  "4H-1,2,4-triazole", "1H-tetrazole = 1H-tetrazole", "2H-tetrazole", "5-phenyl-1H-tetrazole", "1,2,4,5-tetrazine", "1,3,4-oxadiazole = 1,3,4-oxadiazole",
  "1,2,4-oxadiazole", "1,2,5-oxadiazole", "1,3,4-thiadiazole", "2H-1,3-dioxole", "1,3-dioxol-2-one = 2H-1,3-dioxol-2-one", "4H-1,3-dioxine",
  "2,2-dimethyl-4H-1,3-dioxin-4-one", "azepane = azepane", "1H-azepine", "1,4-diazepane", "azocane", "azonane", "azecane",
  "oxacyclododecane = 1-oxacyclododecane", "1-oxacyclohexadecan-2-one", "1,4,7,10,13,16-hexaoxacyclooctadecane",
  "2,3-dihydrofuran", "2,5-dihydrofuran", "3,4-dihydro-2H-pyran = 3,4-dihydro-2H-pyran", "1,2,3,6-tetrahydropyridine = 1,2,3,6-tetrahydropyridine",
  "4,5-dihydro-1H-imidazole", "4,5-dihydro-1,3-oxazole", "2,3-dihydro-1H-pyrrole", "furan-2(5H)-one = furan-2(5H)-one",
  "ascorbic acid = (5R)-5-[(1S)-1,2-dihydroxyethyl]-3,4-dihydroxyfuran-2(5H)-one", "glucal", "guvacine = 1,2,5,6-tetrahydropyridine-3-carboxylic acid",
  "imidazolidine", "pyrazolidine", "imidazolidin-2-one", "pyrazolidin-3-one", "1,3-thiazolidine", "thiomorpholine", "1,4-oxazepane", "oxepane",
  "thiirane", "2H-azirine", "azetidin-2-one", "oxetan-2-one", "1,3,5-trioxane", "1,2,4,5-tetroxane", "1,3-dithiolane", "1,2-dithiolane", "1,3-dithiane",
  "2H-thiopyran", "4H-1,4-oxazine", "2H-1,4-oxazine", "1,4-dihydropyridine", "pyridazin-3(2H)-one", "pyrazin-2(1H)-one", "pyrimidin-4(3H)-one",
  "4-hydroxy-6-methyl-2H-pyran-2-one", "5-fluoropyrimidine-2,4(1H,3H)-dione", "1H-pyrazol-5(4H)-one",
  "3-methyl-1-phenyl-1H-pyrazol-5(4H)-one = 5-methyl-2-phenyl-2,4-dihydro-3H-pyrazol-3-one", "1,2-dihydro-3H-pyrazol-3-one",
  "4,4-dimethyl-4,5-dihydro-1,3-oxazole", "uridine", "thymidine", "cytidine", "orotic acid", "2-(1H-tetrazol-5-yl)pyridine",
  "(1,2,4-triazin-3-yl)methanol", "1-(2H-pyran-2-yl)ethan-1-one", "3,4-dihydro-2H-pyran-2-ylmethanol",
]);

// Double-bonded substituents (P-29.2): methylidene, propan-2-ylidene, ring ylidenes, with E and Z at the parent atom.
run("ylidene", [
  "alpha-myrcene = 2-methyl-6-methylideneocta-1,7-diene", "beta-myrcene = 7-methyl-3-methylideneocta-1,6-diene", "beta-farnesene",
  "beta-pinene = 6,6-dimethyl-2-methylidenebicyclo[3.1.1]heptane", "camphene", "beta-terpinene", "terpinolene = 1-methyl-4-(propan-2-ylidene)cyclohex-1-ene",
  "fulvene = 5-methylidenecyclopenta-1,3-diene", "gamma-terpineol", "itaconic acid = methylidenebutanedioic acid", "methylidenecyclohexane = methylidenecyclohexane",
  "(2E)-2-ethylidenecyclohexan-1-one = (2E)-2-ethylidenecyclohexan-1-one", "(2Z)-2-ethylidenecyclohexan-1-one", "2-methylidenebutanoic acid",
  "(2Z)-2-benzylidene-1-benzofuran-3(2H)-one", "4-methylidene-4H-pyran", "3-methylideneoxolan-2-one", "(propan-2-ylidene)propanedioic acid",
  "cyclohexylidenemethanol", "(cyclohexylidene)acetic acid", "5-benzylidene-1,3-thiazolidine-2,4-dione", "2-(oxolan-3-ylidene)acetic acid",
  "2,2-dimethyl-5-methylidene-1,3-dioxane-4,6-dione", "(diphenylmethylidene)propanedinitrile", "(2E)-2-[(2Z)-but-2-en-1-ylidene]cyclohexan-1-one",
]);

// Ring unsaturation: a ring's one multiple bond takes no locant on its own, and does with a suffix; ring triple bonds.
run("ring unsaturation", [
  "cyclohexene = cyclohexene", "cyclooctyne = cyclooctyne", "cyclohex-2-en-1-ol = cyclohex-2-en-1-ol", "cyclohex-2-ene-1-carboxylic acid = cyclohex-2-ene-1-carboxylic acid",
  "cyclopent-2-en-1-amine = cyclopent-2-en-1-amine", "p-menthyne", "benzyne", "(1Z,5Z)-cycloocta-1,5-diene",
  "cytidine = 4-amino-1-[(2R,3R,4S,5R)-3,4-dihydroxy-5-(hydroxymethyl)oxolan-2-yl]pyrimidin-2(1H)-one",
  "bicyclo[2.2.1]hept-2-yne = bicyclo[2.2.1]hept-2-yne", "bornyne = 1,7,7-trimethylbicyclo[2.2.1]hept-2-yne", "tropyne", "caryne", "spiro[4.5]dec-6-yne",
]);

// Rings with phosphorus (P-22.2.2.1): phosphinine, 1H-phosphole, 1,3,2-dioxaphospholane.
run("phosphorus rings", [
  "phosphinine = phosphinine", "phosphinane = phosphinane", "1H-phosphole = 1H-phosphole", "1-phenyl-1H-phosphole", "1,3,2-dioxaphospholane = 1,3,2-dioxaphospholane",
  "2-methyl-1,3,2-dioxaphospholane", "1-methylphospholane", "1,2-azaphosphinine",
  "1-oxa-4-phosphacyclododecane = 1-oxa-4-phosphacyclododecane", "1,4,7-trioxa-10-phosphacyclododecane", "smiles:S1CN=CSNCC=CN=CC(OC)OP1",
]);

// Substituents on a ring N: halogen, hydroxy and alkoxy as prefixes (NBS, NHS); an acyl group as a ketone or aldehyde
// with the ring as a prefix (P-66.1.1.4.5), or as an acyl prefix when the ring is the parent (Sam's Evans auxiliary).
run("ring N substituents", [
  "1-bromopyrrolidine-2,5-dione = 1-bromopyrrolidine-2,5-dione", "1-chloropyrrolidine-2,5-dione", "1-iodopyrrolidine-2,5-dione",
  "1-hydroxypyrrolidine-2,5-dione = 1-hydroxypyrrolidine-2,5-dione", "1-methoxypyridin-2(1H)-one", "1-hydroxypiperidine",
  "piperidine-1-carbaldehyde = piperidine-1-carbaldehyde", "1-(piperidin-1-yl)ethan-1-one", "di(imidazol-1-yl)methanone = bis(1H-imidazol-1-yl)methanone",
  "1-acetylpyrrolidin-2-one = 1-acetylpyrrolidin-2-one", "smiles:O1C[C@H](C2C=CC=CC=2)N(C(=O)CC2C=CC=CC=2)C1=O = (4S)-4-phenyl-3-(phenylacetyl)-1,3-oxazolidin-2-one",
  "1-(morpholin-4-yl)propan-1-one", "(4-methylpiperazin-1-yl)(phenyl)methanone = (4-methylpiperazin-1-yl)(phenyl)methanone", "1H-imidazole-1-carbaldehyde",
  "1-benzoylpiperidine-4-carboxylic acid = 1-benzoylpiperidine-4-carboxylic acid", "2,2,2-trifluoro-1-(pyrrolidin-1-yl)ethan-1-one",
  "smiles:C1(O)(C)CN(C(OC(C)(C)C)=O)C1 = tert-butyl 3-hydroxy-3-methylazetidine-1-carboxylate", "tert-butyl piperazine-1-carboxylate = tert-butyl piperazine-1-carboxylate",
  "(2S)-1-(tert-butoxycarbonyl)pyrrolidine-2-carboxylic acid = (2S)-1-(tert-butoxycarbonyl)pyrrolidine-2-carboxylic acid", "piperidine-1-carboxylic acid",
  "N,N-dimethylpiperidine-1-carboxamide = N,N-dimethylpiperidine-1-carboxamide", "N-phenylmorpholine-4-carboxamide", "morpholine-4-carbonyl chloride = morpholine-4-carbonyl chloride",
  "ethyl 4-oxopiperidine-1-carboxylate", "tert-butyl 3-oxoazetidine-1-carboxylate",
]);

// Prefixes in alphabetical order, ignoring locants, indicated hydrogen and stereodescriptors (P-14.5): fluconazole,
// rivaroxaban.
run("prefix order", [
  "smiles:OC(Cn1cncn1)(Cn1cncn1)c1ccc(F)cc1F = 2-(2,4-difluorophenyl)-1,3-bis(1H-1,2,4-triazol-1-yl)propan-2-ol",
  "smiles:O=C1N(c2ccc(N3CCOCC3=O)cc2)C[C@@H](CNC(=O)c2ccc(Cl)s2)O1 = 5-chloro-N-({(5R)-2-oxo-3-[4-(3-oxomorpholin-4-yl)phenyl]-1,3-oxazolidin-5-yl}methyl)thiophene-2-carboxamide",
  "smiles:CCC1(c2ccccc2)C(=O)NC(=O)NC1=O = 5-ethyl-5-phenyl-1,3-diazinane-2,4,6-trione", "smiles:O=C1NC(=O)C(c2ccccc2)(c2ccccc2)N1 = 5,5-diphenylimidazolidine-2,4-dione",
  "smiles:CN1C=CC(=O)C=C1 = 1-methylpyridin-4(1H)-one", "smiles:CC1=NN(C)C(=O)C1 = 2,5-dimethyl-2,4-dihydro-3H-pyrazol-3-one",
  "smiles:CS(=O)(=O)c1ccc(C2=C(c3ccccc3)C(=O)OC2)cc1 = 4-[4-(methanesulfonyl)phenyl]-3-phenylfuran-2(5H)-one",
]);

// =O on a ring S or P by the λ-convention (P-14.1.3): heterones as suffixes, oxo as prefixes.
run("ring S and P oxides", [
  "sulfolane = 1λ⁶-thiolane-1,1-dione", "sulfolene = 2,5-dihydro-1λ⁶-thiophene-1,1-dione", "thiolane 1-oxide = 1λ⁴-thiolan-1-one",
  "thiophene 1,1-dioxide = 1λ⁶-thiophene-1,1-dione", "2H-thiopyran 1,1-dioxide = 2H-1λ⁶-thiopyran-1,1-dione",
  "thiomorpholine 1,1-dioxide = 1λ⁶,4-thiazinane-1,1-dione", "1,3-dithiolane 1,1-dioxide", "thietane 1,1-dioxide", "thiane-4-one 1,1-dioxide = 1λ⁶-thiane-1,1,4-trione",
  "thiolane-3-carboxylic acid 1,1-dioxide = 1,1-dioxo-1λ⁶-thiolane-3-carboxylic acid", "(1,1-dioxidothiolan-3-yl)methanol", "1,2-thiazolidine 1,1-dioxide",
  "1,2-thiazol-3(2H)-one 1,1-dioxide", "1-phenylphospholane 1-oxide = 1-phenyl-1λ⁵-phospholan-1-one", "1-phenyl-1H-phosphole 1-oxide",
  "2-methyl-1,3,2-dioxaphospholane 2-oxide", "1-thiacyclododecane 1,1-dioxide", "biotin sulfone", "smiles:O=S1(=O)CCN(c2ccccc2)CC1",
  "smiles:S1C(Cl)=COS(=O)P(=O)(C)C(C2=NN=CS2)S(=O)(=O)1", "smiles:N1=PS(=O)C=C(C(=O)O)C(=O)ONNN(C(=O)N)1",
]);

// A large ring's double bond from its last atom to atom 1 takes a compound locant: 1(13).
run("large rings", ["smiles:C1CCCCCCCCN(C)CC=N1", "smiles:C1CS(=O)N=NN=CC=NC=PC=NOS1", "4-oxa-1-azacyclotridec-1(13)-ene"]);

// Hydrogen drawn as an atom counts on its neighbour: 15 of the 114 structures in Sam's corpus have one.
run("drawn hydrogen", [
  "smiles:O1C[C@H](CC2=CC=CC=C2)N([H])C1=O = (4S)-4-benzyl-1,3-oxazolidin-2-one",
  "smiles:C(=O)(C[H])C1C=CC=CC=1 = 1-phenylethan-1-one", "smiles:[H][C@@](C)(O)CC = (2S)-butan-2-ol",
]);

// A ring's acyl group is numbered as the ring, with its indicated hydrogen: pyrrolysine, (1H-pyrrole-2-carbonyl).
run("ring acyl groups", [
  "pyrrolysine = (2S)-2-amino-6-{[(2R,3R)-3-methyl-3,4-dihydro-2H-pyrrole-2-carbonyl]amino}hexanoic acid",
  "smiles:C(=O)(C=1N=C(NC1)C(=O)O)C=1N=C(NC1)C(=O)O = 4,4'-carbonyldi(1H-imidazole-2-carboxylic acid)",
  "(1H-pyrrole-2-carbonyl)glycine = [(1H-pyrrole-2-carbonyl)amino]acetic acid", "furan-2-carbonyl chloride = furan-2-carbonyl chloride",
]);

// A thione under a senior group is the prefix sulfanylidene (P-64.6.1).
run("thiones", [
  "propylthiouracil = 6-propyl-2-sulfanylidene-2,3-dihydropyrimidin-4(1H)-one", "rhodanine = 2-sulfanylidene-1,3-thiazolidin-4-one",
  "2-sulfanylideneimidazolidin-4-one", "4-oxo-2-sulfanylidene-1,3-thiazolidine-3-acetic acid", "3-sulfanylidenebutanoic acid",
]);

// Ketenes (P-64.1): the C=O carbon is a ketone at the end of a chain with a double bond.
run("ketenes", [
  "ethenone = ethenone", "2-phenylethen-1-one", "diphenylethenone", "dimethylketene = 2-methylprop-1-en-1-one", "fulvenone",
]);

// Chains of any length (P-14.2.1 numerical terms) and polyenes.
run("long chains", [
  "docosanoic acid = docosanoic acid", "henicosane = henicosane", "tricosane = tricosane", "dotriacontan-1-ol = dotriacontan-1-ol",
  "hentriacontane = hentriacontane", "tetratriacontanoic acid", "pentatriacontan-18-one", "(15Z)-tetracos-15-enoic acid", "squalane", "squalene",
  "lycopene", "all-trans-zeta-carotene", "gamma-carotene", "hectane = hectane",
]);
