// Run: node src/namer.check.ts. Each name becomes a structure (OPSIN), Octet names the structure, and OPSIN must read
// Octet's name back as the same structure (same standard InChI). No wrong names are allowed; misses are counted.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacName } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer.check: skipped (no OPSIN build)"); process.exit(0); }
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

const list = [
  "methane","ethane","propane","butane","2-methylpropane","2,2-dimethylpropane",
  "hexane","3-methylhexane","2,3-dimethylpentane","4-ethyl-2-methylhexane","ethene","propene",
  "but-1-ene","but-2-ene","buta-1,3-diene","ethyne","propyne","but-1-yne",
  "pent-1-en-4-yne","2-methylbut-2-ene","methanol","ethanol","propan-1-ol","propan-2-ol",
  "2-methylpropan-2-ol","butan-2-ol","propane-1,2-diol","propane-1,2,3-triol","2-methylpropan-1-ol","prop-2-en-1-ol",
  "2-chloroethanol","2-methoxyethanol","ethanethiol","propane-1-thiol","methanamine","ethanamine",
  "propan-2-amine","N-methylmethanamine","N,N-dimethylmethanamine","N-ethylethanamine","N,N-diethylethanamine","butan-1-amine",
  "methanal","ethanal","propanal","butanal","2-methylpropanal","propan-2-one",
  "butan-2-one","pentan-3-one","pentane-2,4-dione","1-phenylethan-1-one","diphenylmethanone","3-methylbutan-2-one",
  "formic acid","acetic acid","propanoic acid","butanoic acid","2-methylpropanoic acid","butanedioic acid",
  "hexanedioic acid","2-hydroxypropanoic acid","chloroacetic acid","phenylacetic acid","3-phenylpropanoic acid","but-2-enoic acid",
  "2-aminopropanoic acid","2-oxopropanoic acid","methyl acetate","ethyl acetate","propyl acetate","methyl propanoate",
  "ethyl butanoate","methyl benzoate","ethyl formate","phenyl acetate","benzyl acetate","tert-butyl acetate",
  "acetamide","propanamide","N-methylacetamide","N,N-dimethylformamide","N,N-dimethylacetamide","benzamide",
  "N-phenylacetamide","acetonitrile","propanenitrile","benzonitrile","2-methylpropanenitrile","chloromethane",
  "dichloromethane","trichloromethane","tetrachloromethane","bromoethane","1,2-dichloroethane","2-iodopropane",
  "fluorobenzene","methoxymethane","ethoxyethane","methoxybenzene","1-methoxypropane","2-methoxypropane",
  "benzene","toluene","ethylbenzene","1,2-dimethylbenzene","1,3-dimethylbenzene","1,4-dimethylbenzene",
  "1,3,5-trimethylbenzene","ethenylbenzene","phenol","aniline","benzoic acid","benzaldehyde",
  "4-chlorophenol","2-nitrophenol","4-methylaniline","3-bromobenzoic acid","4-hydroxybenzoic acid","2-hydroxybenzoic acid",
  "4-aminobenzoic acid","2-(acetyloxy)benzoic acid","N-(4-hydroxyphenyl)acetamide","4-nitrobenzaldehyde","benzene-1,4-diol","methyl 4-hydroxybenzoate",
  "2-[4-(2-methylpropyl)phenyl]propanoic acid","4-methoxybenzoic acid","N,N-dimethylaniline","N-methylaniline","1-chloro-4-nitrobenzene","1-bromo-3-chlorobenzene",
  "2,4,6-trimethylphenol","2-phenylethan-1-ol","phenylmethanol","phenylmethanamine","cyclopropane","cyclobutane",
  "cyclopentane","cyclohexane","cycloheptane","methylcyclohexane","cyclohexanol","cyclohexanone",
  "cyclohexanamine","cyclohexanecarboxylic acid","cyclohexene","2-methylcyclohexan-1-ol","cyclopentane-1,2-diol","cyclohexane-1,4-dione",
  "cyclohexylmethanol","pyridine","2-methylpyridine","pyridin-3-amine","pyridine-3-carboxylic acid","pyridin-4-ol",
  "4-(dimethylamino)pyridine","pyrimidine","pyrazine","furan","thiophene","1H-pyrrole",
  "furan-2-carbaldehyde","thiophene-2-carboxylic acid","1-methyl-1H-pyrrole","1H-imidazole","1-methyl-1H-imidazole","piperidine",
  "morpholine","piperazine","pyrrolidine","oxolane","oxane","1-methylpiperidine",
  "4-methylmorpholine","piperidin-4-one","1,4-dioxane","2-aminoethan-1-ol","3-aminopropanoic acid","4-hydroxybutan-2-one",
  "2-chloro-N,N-dimethylacetamide","2-(dimethylamino)ethan-1-ol","nitromethane","nitrobenzene","1,3-dinitrobenzene","2-methyl-1-nitropropane",
];

let named = 0, missed: string[] = [];
const wrong: string[] = [];
const t0 = performance.now();
for (const input of list) {
  const smiles = opsin.parseToSmiles(input);
  if (!smiles) { missed.push(`${input} (OPSIN)`); continue; }
  const g = graphOf(molOf(smiles), cipOf(smiles));
  const name = g && iupacName(g);
  if (!name) { missed.push(input); continue; }
  const back = opsin.parseToSmiles(name);
  const same = back && convert(back, "inchi") === convert(smiles, "inchi");
  if (same) named++;
  else wrong.push(`${input} -> ${name}`);
}
const ms = (performance.now() - t0) / list.length;
if (missed.length) console.log(`missed: ${missed.join("; ")}`);
if (wrong.length) console.log(`WRONG: ${wrong.join("; ")}`);
console.log(`namer.check: ${named}/${list.length} named, ${wrong.length} wrong (${ms.toFixed(1)} ms each, OPSIN and InChI included)`);
assert.equal(wrong.length, 0, "a name OPSIN reads as a different structure");

// Phase 2: stereochemistry, fused rings, and more classes. Counted, and no name may be wrong.
const more = [
  "L-alanine", "(2S)-2-aminopropanoic acid", "(2R)-butan-2-ol", "(2E)-but-2-enoic acid", "(2Z)-but-2-enoic acid", "(2E,4E)-hexa-2,4-dienoic acid",
  "(2R,3S)-3-chlorobutan-2-ol", "methyl (2S)-2-hydroxypropanoate", "(1R)-1-phenylethan-1-ol", "(1S,2R)-2-methylcyclohexan-1-ol", "L-serine", "L-phenylalanine",
  "naphthalene", "naphthalen-1-ol", "naphthalen-2-amine", "naphthalene-2-carboxylic acid", "1-methylnaphthalene", "2-methoxynaphthalene",
  "quinoline", "quinolin-8-ol", "isoquinoline", "quinoxaline", "quinazoline", "phthalazine", "cinnoline",
  "1H-indole", "1-methyl-1H-indole", "1H-indole-3-carbaldehyde", "1H-indol-5-ol", "2-(1H-indol-3-yl)acetic acid", "5-bromo-1H-indole",
  "1-benzofuran", "1-benzothiophene", "1H-benzimidazole", "2-methyl-1H-benzimidazole", "1,3-benzoxazole", "1,3-benzothiazole", "1H-indazole",
  "anthracene", "phenanthrene", "9H-fluorene", "9H-carbazole", "acridine", "9H-xanthene", "1H-indene", "7H-purine", "9H-purin-6-amine",
  "2,3-dihydro-1H-indene", "1,2,3,4-tetrahydronaphthalene", "decahydronaphthalene", "2,3-dihydro-1H-indole", "1,2,3,4-tetrahydroquinoline",
  "2,3-dihydro-1H-inden-1-one", "3,4-dihydronaphthalen-1(2H)-one", "quinolin-2(1H)-one", "2H-1-benzopyran-2-one", "1H-indole-2,3-dione", "1,3-dihydro-2H-indol-2-one",
  "naphthalen-2-ylmethanol", "2-(naphthalen-1-yl)acetic acid", "N-(naphthalen-1-yl)acetamide", "(quinolin-2-yl)methanol",
  "acetyl chloride", "benzoyl chloride", "propanoyl chloride", "acetic anhydride", "benzoic anhydride", "sodium acetate", "potassium benzoate",
  "methanesulfonic acid", "4-methylbenzene-1-sulfonic acid", "methanesulfonyl chloride", "urea", "methyl carbamate", "tert-butyl carbamate",
  "1,1'-biphenyl", "4-methyl-1,1'-biphenyl", "2,2'-bipyridine", "(methanesulfinyl)methane", "(methanesulfonyl)methane",
];
// Phase 3: more fused systems, hydro and added hydrogen, lactams, ring assemblies, salts and other classes.
const extra = [
  "phenazine", "10H-phenothiazine", "2-chloro-10H-phenothiazine", "3-methyl-10H-phenoxazine", "5-methyl-9H-xanthene", "2H-indazole",
  "3H-indole", "1,8-naphthyridine", "pteridine", "9,10-dihydroanthracene", "1,2-dihydronaphthalene", "octahydro-1H-indole",
  "5,6,7,8-tetrahydronaphthalen-2-ol", "2,3,4,9-tetrahydro-1H-carbazole", "(1R)-2,3-dihydro-1H-inden-1-ol", "2,3-dihydro-1H-inden-2-ol",
  "naphthalene-1,4-dione", "anthracene-9,10-dione", "9H-fluoren-9-one", "9H-xanthen-9-one", "acridin-9(10H)-one", "naphthalen-2(1H)-one",
  "1H-isoindole-1,3(2H)-dione", "1H-indene-1,3(2H)-dione", "2-benzofuran-1(3H)-one", "1,3-benzoxazol-2(3H)-one", "quinazolin-4(3H)-one",
  "3,4-dihydroquinolin-2(1H)-one", "4H-1-benzopyran-4-one", "4-oxo-1,4-dihydroquinoline-3-carboxylic acid", "1,3,7-trimethyl-3,7-dihydro-1H-purine-2,6-dione",
  "2-amino-1,9-dihydro-6H-purin-6-one", "L-tryptophan", "(2S)-2-(6-methoxynaphthalen-2-yl)propanoic acid", "1H-indol-1-ylmethanol",
  "pyrrolidin-2-one", "oxolan-2-one", "1-methylpyrrolidin-2-one", "1H-pyrazole", "pyridazine", "2-(piperidin-1-yl)ethan-1-ol",
  "[1,1'-biphenyl]-4-carboxylic acid", "4'-methyl[1,1'-biphenyl]-4-ol", "2,3'-bipyridine", "1,1'-binaphthalene", "2,2'-bithiophene",
  "butanedioyl dichloride", "cyclohexanecarbonyl chloride", "naphthalene-2-carbonyl chloride", "acetic propanoic anhydride", "propanoic anhydride",
  "benzene-1,3-disulfonic acid", "4-sulfobenzoic acid", "4-methylbenzene-1-sulfonyl chloride", "N,N'-dimethylurea", "N,N,N',N'-tetramethylurea",
  "methyl N-methylcarbamate", "1-(methanesulfonyl)-4-methylbenzene", "2-(propane-2-sulfonyl)propane", "calcium diacetate", "disodium butanedioate",
  "sodium methanesulfonate", "lithium (2S)-2-hydroxypropanoate",
];
// Counts a list: named, missed, and wrong (none allowed).
function run(label: string, names: string[]) {
  let ok = 0;
  const missedHere: string[] = [], wrongHere: string[] = [];
  for (const input of names) {
    const smiles = opsin.parseToSmiles(input);
    if (!smiles) { missedHere.push(`${input} (OPSIN)`); continue; }
    const g = graphOf(molOf(smiles), cipOf(smiles)), name = g && iupacName(g);
    if (!name) { missedHere.push(input); continue; }
    const back = opsin.parseToSmiles(name);
    if (back && convert(back, "inchi") === convert(smiles, "inchi")) ok++;
    else wrongHere.push(`${input} -> ${name}`);
  }
  if (process.argv.includes("--missed") && missedHere.length) console.log(`${label} missed: ${missedHere.join("; ")}`);
  if (wrongHere.length) console.log(`${label} WRONG: ${wrongHere.join("; ")}`);
  console.log(`namer.check: ${label} ${ok}/${names.length} named, ${wrongHere.length} wrong`);
  assert.equal(wrongHere.length, 0, `a ${label} name OPSIN reads as a different structure`);
}
// Phase 4: salts with inorganic and organic ions, cations, phosphanes, imines and oximes, carbamates as prefixes,
// and bicyclic von Baeyer and spiro rings.
const classes = [
  "sodium chloride", "potassium carbonate", "caesium carbonate", "sodium hydrogencarbonate", "sodium hydroxide", "sodium hydride",
  "sodium azide", "sodium cyanide", "lithium chloride", "magnesium sulfate", "sodium sulfate", "tripotassium phosphate", "calcium chloride",
  "potassium permanganate", "sodium methoxide", "potassium tert-butoxide", "sodium phenoxide", "ammonium chloride", "ammonium acetate",
  "tetramethylammonium chloride", "tetrabutylammonium bromide", "triethylammonium chloride", "pyridinium chloride", "1-methylpyridin-1-ium iodide",
  "anilinium chloride", "1,1-dimethylpiperidin-1-ium chloride", "choline chloride", "sodium tetrafluoroborate", "silver nitrate",
  "triphenylphosphane", "tributylphosphane", "methyl(diphenyl)phosphane", "triphenylphosphane oxide", "1,2-bis(diphenylphosphanyl)ethane",
  "4-(diphenylphosphanyl)benzoic acid", "diphenylmethanimine", "N-hydroxypropan-2-imine", "N-methylethanimine", "N-hydroxycyclohexanimine",
  "2-(hydroxyimino)propanoic acid", "N-phenylpropan-2-imine", "1-phenylethan-1-one oxime",
  "[(tert-butoxycarbonyl)amino]acetic acid", "2-{[(benzyloxy)carbonyl]amino}propanoic acid", "4-[(tert-butoxycarbonyl)amino]benzoic acid",
  "bicyclo[2.2.1]heptane", "bicyclo[2.2.1]hept-2-ene", "bicyclo[2.2.2]octane", "bicyclo[3.2.1]octane", "bicyclo[1.1.1]pentane",
  "bicyclo[3.3.1]nonane", "bicyclo[4.1.0]heptane", "bicyclo[2.2.1]hepta-2,5-diene", "1,7,7-trimethylbicyclo[2.2.1]heptan-2-one",
  "2,6,6-trimethylbicyclo[3.1.1]hept-2-ene", "7-oxabicyclo[2.2.1]heptane", "8-azabicyclo[3.2.1]octane", "1,4-diazabicyclo[2.2.2]octane",
  "1-azabicyclo[2.2.2]octane", "bicyclo[2.2.1]heptan-2-ol", "8-methyl-8-azabicyclo[3.2.1]octan-3-one",
  "spiro[4.5]decane", "spiro[2.2]pentane", "spiro[4.4]nonane", "spiro[5.5]undecan-3-one", "1,4-dioxaspiro[4.5]decane", "spiro[4.5]decan-6-ol",
];
run("phase 2", more);
run("phase 3", extra);
run("phase 4", classes);
// Aromatic ortho-fused rings take fusion names, never von Baeyer ones (2H-1,3-benzodioxole, not
// 7,9-dioxabicyclo[4.3.0]nona-1,3,5-triene); without a fused name in the table they are not named yet.
for (const input of ["2H-1,3-benzodioxole", "imidazo[1,2-a]pyridine", "5-phenyl-1,3-dihydro-2H-1,4-benzodiazepin-2-one"]) {
  const smiles = opsin.parseToSmiles(input), g = graphOf(molOf(smiles), cipOf(smiles)), name = g && iupacName(g);
  assert.ok(!name?.includes("bicyclo"), `${input} -> ${name}`);
}

// Diazo and azido groups (P-61.4, P-61.5), cited only as prefixes. Sam's prenyl diazoacetate (20 October 2026) gave
// "Octet cannot name this structure yet". Every one must be named, and read back as the same structure.
const n2 = [
  "3-methylbut-2-en-1-yl diazoacetate", "ethyl diazoacetate", "diazomethane", "2-diazo-1-phenylethan-1-one",
  "ethyl 2-diazo-3-oxobutanoate", "azidobenzene", "(azidomethyl)benzene", "1-azidobutane", "4-azidobenzoic acid",
];
const n2Out: string[] = [];
for (const input of n2) {
  const smiles = opsin.parseToSmiles(input);
  assert.ok(smiles, `OPSIN reads ${input}`);
  const g = graphOf(molOf(smiles), cipOf(smiles));
  const name = g && iupacName(g);
  assert.ok(name, `no name for ${input} (${smiles})`);
  const back = opsin.parseToSmiles(name);
  assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${input} -> ${name}, a different structure`);
  n2Out.push(`${input} -> ${name}`);
}
console.log(`namer.check: diazo and azido ${n2Out.length}/${n2.length}: ${n2Out.join("; ")}`);
