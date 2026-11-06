// Run: node src/namer-fused.check.ts. Fused ring systems outside the namer's table (fusion.ts): each name becomes a
// structure (OPSIN), Octet names the structure, and OPSIN must read Octet's name back as the same structure (same
// standard InChI). Every name in these lists must be named, and none may be wrong. --names prints Octet's names.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-fused.check: skipped (no OPSIN build)"); process.exit(0); }
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

// Names every structure in a list: none may be missed or wrong.
function run(label: string, names: string[]) {
  const missed: string[] = [], wrong: string[] = [], out: string[] = [];
  const t0 = performance.now();
  for (const input of names) {
    const smiles = input.startsWith("smiles:") ? input.slice(7) : opsin.parseToSmiles(input);
    assert.ok(smiles, `OPSIN reads ${input}`);
    const g = graphOf(molOf(smiles), cipOf(smiles));
    const r = g ? iupacNameWhy(g) : { why: "graph" };
    if (!r.name) { missed.push(`${input} (${r.why})`); continue; }
    const back = opsin.parseToSmiles(r.name);
    if (back && convert(back, "inchi") === convert(smiles, "inchi")) out.push(`${input} -> ${r.name}`);
    else wrong.push(`${input} -> ${r.name}`);
  }
  const ms = (performance.now() - t0) / names.length;
  if (process.argv.includes("--names")) console.log(out.join("\n"));
  if (missed.length) console.log(`${label} missed: ${missed.join("; ")}`);
  if (wrong.length) console.log(`${label} WRONG: ${wrong.join("; ")}`);
  console.log(`namer-fused.check: ${label} ${out.length}/${names.length} named, ${wrong.length} wrong (${ms.toFixed(1)} ms each)`);
  assert.equal(wrong.length, 0, `a ${label} name OPSIN reads as a different structure`);
  if (!process.argv.includes("--all")) assert.equal(missed.length, 0, `a ${label} structure has no name`);
}

// Two monocycles: fusion descriptors with the base's letters and the attached component's locants (P-25.3.1.3).
run("bicyclic", [
  "imidazo[1,2-a]pyridine", "1H-pyrrolo[2,3-b]pyridine", "1H-pyrrolo[3,2-c]pyridine", "thieno[2,3-b]pyridine", "thieno[3,2-c]pyridine",
  "furo[3,2-b]pyridine", "furo[2,3-c]pyridine", "pyrazolo[1,5-a]pyrimidine", "1H-pyrazolo[3,4-d]pyrimidine", "[1,2,4]triazolo[4,3-a]pyridine",
  "[1,2,4]triazolo[1,5-a]pyrimidine", "imidazo[2,1-b][1,3]thiazole", "pyrido[2,3-d]pyrimidine", "pyrazino[2,3-b]pyrazine", "7H-pyrrolo[2,3-d]pyrimidine",
  "indolizine", "4H-quinolizine", "1H-pyrrolizine", "thieno[3,2-b]thiophene", "1H-cyclopenta[b]pyridine", "5H-cyclopenta[b]pyridine",
  "imidazo[1,2-b]pyridazine", "imidazo[1,5-a]pyridine", "pyrrolo[1,2-a]pyrazine", "[1,2,4]triazolo[4,3-b]pyridazine", "furo[3,4-c]pyridine",
  "1H-imidazo[4,5-b]pyridine", "3H-imidazo[4,5-c]pyridine", "pyrrolo[2,1-b][1,3]oxazole", "2H-furo[3,2-b]pyran", "pyrimido[4,5-d]pyrimidine",
]);
// Benzo names (P-25.2.2.4): a benzene ring and a heteromonocycle.
run("benzo", [
  "2H-1,4-benzoxazine", "4H-3,1-benzoxazine", "2H-1,3-benzodioxole", "2,3-dihydro-1,4-benzodioxine", "2,1,3-benzothiadiazole",
  "2,1,3-benzoxadiazole", "1H-1,4-benzodiazepine", "1H-3-benzazepine", "1-benzoxepine", "1,2,3-benzotriazine", "1H-benzotriazole",
  "4H-1-benzothiopyran", "1H-2-benzopyran", "1,3-benzoxathiole", "5H-benzo[7]annulene",
]);
// Polycyclic components and several attached components.
run("polycyclic", [
  "pyrrolo[3,4-c]quinoline", "9H-pyrido[3,4-b]indole", "9H-pyrido[2,3-b]indole", "benzo[g]quinoline", "benzo[h]quinoline", "naphtho[2,3-b]furan",
  "naphtho[2,1-b]furan", "dibenzo[b,d]furan", "dibenzo[b,d]thiophene", "5H-dibenzo[b,f]azepine", "dibenzo[b,e][1,4]dioxine", "[1]benzofuro[3,2-b]pyridine",
  "pyrido[1,2-a]benzimidazole", "tetraphene", "dibenzo[a,h]anthracene", "benzo[c]phenanthrene", "5H-dibenzo[a,d][7]annulene", "dibenzo[b,e]oxepine",
  "11H-dibenzo[b,e][1,4]diazepine", "4H-[1,2,4]triazolo[4,3-a][1,4]benzodiazepine", "4H-thieno[2,3-b][1,5]benzodiazepine", "[1]benzothieno[3,2-d]pyrimidine",
  "1H-benzo[de]isoquinoline", "1H,3H-benzo[de]isochromene", "2H-naphtho[1,8-bc]furan", "1H-cyclopenta[a]naphthalene", "benzo[f]quinoxaline",
  "thieno[2,3-b]quinoline", "furo[3,2-g][1]benzopyran", "[1,3]dioxolo[4,5-g]quinoline", "difuro[3,2-b:2',3'-d]pyridine", "furo[3,2-b]thieno[2,3-e]pyridine",
]);
// Retained names outside the namer's own table (P-25.1.1, P-25.2.1).
run("retained", [
  "acenaphthylene", "azulene", "pyrene", "chrysene", "fluoranthene", "1H-phenalene", "triphenylene", "biphenylene", "s-indacene", "as-indacene",
  "tetracene", "picene", "perylene", "coronene", "pentalene", "heptalene", "1H-perimidine", "1,10-phenanthroline", "phenanthridine", "thianthrene",
  "phenoxathiine", "aceanthrylene", "acephenanthrylene", "rubicene", "ovalene", "pentacene", "9H-thioxanthene",
]);
// Substituted, partly saturated and with suffixes: indicated and added hydrogen on fused systems.
run("derivatives", [
  "5-methyl-2-phenyl-3a,4,5,9b-tetrahydro-1H-pyrrolo[3,4-c]quinoline-1,3(2H)-dione", "2-phenylimidazo[1,2-a]pyridine", "1-methyl-9H-pyrido[3,4-b]indole",
  "4,5,6,7-tetrahydrothieno[3,2-c]pyridine", "1,5-dihydro-4H-pyrazolo[3,4-d]pyrimidin-4-one", "1H-benzo[de]isoquinoline-1,3(2H)-dione",
  "1H,3H-benzo[de]isochromene-1,3-dione", "10,11-dihydro-5H-dibenzo[b,f]azepine", "5-methyl-5H-dibenzo[b,f]azepine", "3,4-dihydro-2H-1,4-benzoxazine",
  "2,3,4,5-tetrahydro-1H-3-benzazepine", "acenaphthylene-1,2-dione", "1,2-dihydroacenaphthylene", "pyrene-1-carboxylic acid", "dibenzo[b,d]furan-2-ol",
  "2-methyl-2H-1,3-benzodioxole", "1,3-benzodioxol-5-ol", "9H-pyrido[3,4-b]indol-1-amine", "imidazo[1,2-a]pyridin-3-ylmethanol",
  "7-chloro-1-methyl-5-phenyl-1,3-dihydro-2H-1,4-benzodiazepin-2-one",
]);
// Ring systems of drugs, dyes and natural products: second-order components (benzo[5,6]cyclohepta[1,2-b]pyridine),
// FR-3.5 benzo units, multi-parent names (FR-6), orientation as a base criterion (benzo[pqr]tetraphene, FR-2.3 g),
// and several added hydrogens (pteridine-2,4(1H,3H)-dione).
run("scaffolds", [
  "imidazo[1,2-a]pyrimidine", "imidazo[1,2-a]pyrazine", "imidazo[1,2-c]pyrimidine", "imidazo[1,5-a]pyrazine", "imidazo[2,1-b][1,3,4]thiadiazole",
  "pyrazolo[1,5-a]pyridine", "1H-pyrazolo[3,4-b]pyridine", "1H-pyrazolo[4,3-c]pyridine", "pyrazolo[1,5-a][1,3,5]triazine",
  "pyrazolo[1,5-c]pyrimidine", "pyrrolo[1,2-a]pyrimidine", "5H-pyrrolo[2,3-b]pyrazine", "5H-pyrrolo[3,2-d]pyrimidine",
  "pyrrolo[1,2-b]pyridazine", "pyrrolo[2,1-f][1,2,4]triazine", "[1,2,4]triazolo[1,5-a]pyridine", "5,6,7,8-tetrahydro[1,2,4]triazolo[4,3-a]pyrazine",
  "3H-[1,2,3]triazolo[4,5-d]pyrimidine", "[1,2,3]triazolo[1,5-a]pyridine", "tetrazolo[1,5-a]pyridine", "thieno[2,3-d]pyrimidine",
  "thieno[3,2-d]pyrimidine", "thieno[3,2-b]pyridine", "thieno[2,3-c]pyridine", "thieno[3,4-b]pyrazine", "4H-thieno[3,2-b]pyrrole",
  "furo[2,3-d]pyrimidine", "furo[3,2-c]pyridine", "furo[2,3-b]pyridine", "[1,3]oxazolo[4,5-b]pyridine", "[1,3]thiazolo[5,4-b]pyridine",
  "[1,3]thiazolo[4,5-d]pyrimidine", "[1,2]oxazolo[5,4-b]pyridine", "pyrido[3,4-d]pyrimidine", "pyrido[2,3-b]pyrazine",
  "pyrido[3,2-d]pyrimidine", "4H-pyrido[1,2-a]pyrimidin-4-one", "pyrimido[1,2-a]pyrimidine", "octahydro-2H-pyrazino[1,2-a]pyrazine",
  "4H-pyrido[3,2-b][1,4]oxazine", "2H-pyrido[3,2-b][1,4]oxazine", "2H-[1,3]dioxolo[4,5-b]pyridine", "2,3-dihydro[1,4]dioxino[2,3-b]pyridine",
  "5H-cyclopenta[c]pyridine", "6,7-dihydro-5H-cyclopenta[d]pyrimidine", "5H-cyclohepta[b]pyridine", "octahydroindolizine",
  "octahydro-2H-quinolizine", "hexahydro-1H-pyrrolizine", "hexahydro-1H-furo[3,4-c]pyrrole", "octahydrocyclopenta[c]pyrrole",
  "5H-pyrido[4,3-b]indole", "9H-pyrimido[4,5-b]indole", "6H-indolo[2,3-b]quinoxaline", "11H-indolo[3,2-c]quinoline",
  "5H-dibenzo[b,e][1,4]diazepine", "11H-dibenzo[b,e]azepine", "dibenzo[b,f][1,4]oxazepine", "dibenzo[b,f]thiepine",
  "6H-dibenzo[b,e]oxepine", "10,11-dihydro-5H-dibenzo[a,d][7]annulene", "naphtho[1,2-b]thiophene", "naphtho[2,3-b]thiophene",
  "5H-[1]benzopyrano[2,3-b]pyridine", "benzo[g]isoquinoline", "benzo[f]isoquinoline", "benzo[h]isoquinoline", "benzo[f]quinoline",
  "benzo[c]cinnoline", "benzo[g]quinoxaline", "benzo[g]phthalazine", "benzo[g]pteridine", "7,8,10-trimethylbenzo[g]pteridine-2,4(3H,10H)-dione",
  "imidazo[2,1-b][1,3]benzothiazole", "[1,2,4]triazolo[3,4-b][1,3]benzothiazole", "[1,3]thiazolo[3,2-a]benzimidazole",
  "pyrimido[1,2-a]benzimidazole", "imidazo[1,2-a]quinoline", "1H-imidazo[4,5-c]quinoline", "1-(2-methylpropyl)-1H-imidazo[4,5-c]quinolin-4-amine",
  "1H-pyrazolo[3,4-b]quinoline", "[1,2,4]triazolo[4,3-a]quinoxaline", "imidazo[1,5-a]quinoxaline", "pyrrolo[1,2-a]quinoxaline",
  "pyrrolo[2,1-a]isoquinoline", "5,6-dihydropyrrolo[2,1-a]isoquinoline", "2H-pyrido[2,1-a]isoquinoline", "3-(2-methylpropyl)-9,10-dimethoxy-1,3,4,6,7,11b-hexahydro-2H-pyrido[2,1-a]isoquinolin-2-one",
  "2H-pyrazino[2,1-a]isoquinoline", "indolo[2,3-a]quinolizine", "[1]benzothieno[2,3-d]pyrimidine", "8H-thieno[2,3-b]indole",
  "naphtho[1,2-d][1,3]oxazole", "1H-anthra[1,2-d]imidazole", "1H-phenanthro[9,10-d]imidazole", "acenaphtho[1,2-b]quinoxaline",
  "acenaphtho[1,2-b]pyrazine", "11H-indeno[1,2-b]quinoxaline", "5H-indeno[1,2-b]pyridine", "6H-dibenzo[b,d]pyran",
  "6H-dibenzo[b,d]pyran-6-one", "6,6,9-trimethyl-3-pentyl-6H-dibenzo[b,d]pyran-1-ol", "6H-[1]benzofuro[3,2-c][1]benzopyran",
  "6H-[1]benzofuro[3,2-c][1]benzopyran-6-one", "2-phenyl-4H-1-benzopyran-4-one", "1-methyl-3-propyl-1,6-dihydro-7H-pyrazolo[4,3-d]pyrimidin-7-one",
  "imidazo[5,1-f][1,2,4]triazin-4(3H)-one", "2,3,4,9-tetrahydro-1H-pyrido[3,4-b]indole", "pyrazino[1',2':1,6]pyrido[3,4-b]indole",
  "11H-benzo[5,6]cyclohepta[1,2-b]pyridine", "6,11-dihydro-5H-benzo[5,6]cyclohepta[1,2-b]pyridine", "4H-benzo[4,5]cyclohepta[1,2-b]thiophene",
  "2H-naphtho[1,8-bc]thiophene", "5H-pyrrolo[2,1-c][1,4]benzodiazepine", "4H-imidazo[1,5-a][1,4]benzodiazepine", "pyrazino[2,1-a]pyrido[2,3-c][2]benzazepine",
  "1H-pyrrolo[3,2-b]pyridine", "1H-pyrrolo[2,3-c]pyridine", "furo[3,2-b]furan", "thieno[2,3-b]thiophene", "1H-thieno[3,4-c]pyrrole",
  "cyclopenta[b]thiophene", "4H-cyclopenta[b]thiophene", "2H-cyclopenta[c]furan", "1H-benzo[g]indole", "3H-benzo[e]indole",
  "1H-benzo[f]indole", "naphtho[2,3-d][1,3]dioxole", "2H-naphtho[2,3-d][1,3]dioxole", "benzo[1,2-b:4,5-b']dithiophene",
  "benzo[1,2-b:4,3-b']dithiophene", "dithieno[3,2-b:2',3'-d]thiophene", "4H-dithieno[3,2-b:2',3'-d]pyrrole", "pyrrolo[3,4-c]pyrrole",
  "2,5-dihydropyrrolo[3,4-c]pyrrole-1,4-dione", "1H-benzo[de]isoquinoline-1,3(2H)-dione", "benzo[lmn][3,8]phenanthroline",
  "1H-cyclopenta[l]phenanthrene", "benzo[a]pyrene", "benzo[e]pyrene", "benzo[ghi]perylene", "dibenzo[a,l]pyrene", "indeno[1,2,3-cd]pyrene",
  "benzo[b]fluoranthene", "benzo[k]fluoranthene", "11H-benzo[a]fluorene", "7H-benzo[c]fluorene", "dibenzo[c,g]carbazole",
  "7H-dibenzo[c,g]carbazole", "quino[2,3-b]acridine", "5,12-dihydroquino[2,3-b]acridine-7,14-dione", "9H-pyrido[2,3-b]indole",
  "1H-pyrrolo[3,2-h]quinoline", "pyrido[2,3-g]quinoline", "pyrido[3,2-g]quinoline", "1,7-phenanthroline", "4,7-phenanthroline",
  "1,10-phenanthroline-5,6-dione", "dipyrido[3,2-a:2',3'-c]phenazine", "pyrazino[2,3-f][1,10]phenanthroline", "benzo[f][1,7]naphthyridine",
  "benzo[c][1,8]naphthyridine", "benzo[b][1,6]naphthyridine", "10H-pyrido[3,2-b][1,4]benzothiazine", "benzo[b][1,4]benzodioxine",
  "thieno[3,2-b][1]benzothiophene", "[1]benzothieno[3,2-b][1]benzothiophene",
  "pteridine-2,4(1H,3H)-dione", "quinazoline-2,4(1H,3H)-dione", "quinoxaline-2,3(1H,4H)-dione", "1,10-phenanthroline-5,6-dione",
  "benzo[1,2-b:4,5-c']difuran", "benzo[1,2:4,5]di[7]annulene", "benzo[1,2-d:4,5-d']bis[1,3]thiazole", "naphtho[1,2-b:5,6-b']dithiophene",
  "3,8-phenanthroline", "2,9-phenanthroline", "1,7-phenanthroline", "benzo[a]acridine", "benzo[c]acridine", "pyrido[3,2-a]phenazine",
]);
// Retained parents named as a whole (porphyrin with its 21H,23H indicated hydrogen, phthalocyanine and corrole as
// macrocycles.check.ts checks them, pleiadene), benzene rings fused to small rings by von Baeyer names
// (bicyclo[4.2.0]octa-1,3,5-triene, drawn either Kekulé way), and adamantane.
run("retained whole", [
  "21H,23H-porphyrin", "5,10,15,20-tetraphenyl-21H,23H-porphyrin", "2,3,7,8,12,13,17,18-octaethyl-21H,23H-porphyrin", "pleiadene",
  "29H,31H-phthalocyanine", "30H,32H-phthalocyanine", "2,9,16,23-tetra-tert-butyl-29H,31H-phthalocyanine", "1,4,8,11,15,18,22,25-octabutoxy-29H,31H-phthalocyanine",
  "21H,22H,23H-corrole", "5,10,15-triphenyl-21H,22H,23H-corrole", "5,10,15-tris(pentafluorophenyl)-21H,22H,23H-corrole", "corrin",
  "bicyclo[4.2.0]octa-1,3,5-triene", "bicyclo[4.2.0]octa-1,3,5-trien-7-ol", "smiles:C1CC2=C1C=CC=C2", "bicyclo[4.1.0]hepta-1,3,5-triene",
  "adamantane", "adamantan-1-amine", "adamantan-2-one", "3,5-dimethyladamantan-1-amine", "2-azaadamantane", "adamantan-1-yl acetate",
]);
// Bridged fused systems (FR-8, P-25.4): the fused system with the most rings and atoms, bridges named as OPSIN reads
// them and numbered after it (CAS style: hydro prefixes count the bridgeheads); fused cations.
run("bridged fused", [
  "1,2,3,4-tetrahydro-1,4-methanonaphthalene", "1,4-dihydro-1,4-methanonaphthalene", "9,10-dihydro-9,10-ethanoanthracene",
  "9,10-dihydro-9,10-ethenoanthracene", "1,4-dihydro-1,4-epoxynaphthalene", "3a,4,7,7a-tetrahydro-4,7-methano-1H-indene",
  "octahydro-1H-4,7-methanoindene", "1,2,3,4,4a,5,6,7,8,8a-decahydro-1,4:5,8-dimethanonaphthalene", "1,2,3,4-tetrahydro-1,4-ethanonaphthalene",
  "(4R,4aR,7S,7aR,12bS)-3-methyl-2,3,4,4a,7,7a-hexahydro-1H-4,12-methano[1]benzofuro[3,2-e]isoquinoline-7,9-diol",
  "(4R,4aR,7S,7aR,12bS)-9-methoxy-3-methyl-2,3,4,4a,7,7a-hexahydro-1H-4,12-methano[1]benzofuro[3,2-e]isoquinolin-7-ol",
  "(4R,4aS,7aR,12bS)-4a-hydroxy-9-methoxy-3-methyl-1,2,3,4,4a,5,6,7a-octahydro-7H-4,12-methano[1]benzofuro[3,2-e]isoquinolin-7-one",
  "1,2,3,4,4a,9,10,10a-octahydro-10,4a-(epiminoethano)phenanthrene", "aconitane",
  "6,11-dimethyl-3-(3-methylbut-2-en-1-yl)-1,2,3,4,5,6-hexahydro-2,6-methano-3-benzazocin-8-ol",
  "quinolizin-5-ium", "indolizin-4-ium", "1-methyl-1H-imidazo[1,2-a]pyridin-4-ium", "pyrido[1,2-a]pyrimidin-5-ium", "2,3-dihydro-1H-pyrrolizin-4-ium",
]);
// Spiro unions with a polycyclic component (P-24.5): components in alphabetical order, the second primed; identical
// components as spirobi[...]; saturated monocyclic components by their saturated names.
run("spiro", [
  "spiro[cyclohexane-1,1'-indene]", "2',3'-dihydrospiro[cyclohexane-1,1'-indene]", "spiro[cyclopropane-1,3'-indol]-2'(1'H)-one",
  "1,2-dihydrospiro[indole-3,4'-piperidine]", "3',6'-dihydroxy-3H-spiro[[2]benzofuran-1,9'-xanthen]-3-one", "9,9'-spirobi[fluorene]",
  "3,4-dihydrospiro[1-benzopyran-2,4'-piperidine]", "1',3'-dihydrospiro[1,3-dioxolane-2,2'-indene]", "2,2'-spirobi[2H-1-benzopyran]",
  "spiro[indene-1,4'-piperidine]", "spiro[azetidine-3,3'-indol]-2'(1'H)-one", "spiro[cyclohexane-1,1'-inden]-3'-amine",
  "3',4'-dihydro-2'H-spiro[piperidine-4,1'-naphthalene]", "2',3'-dihydrospiro[cyclohexane-1,1'-inden]-4-one", "4-methylspiro[cyclohexane-1,1'-indene]",
  "spirostane", "1'H-spiro[cyclohexane-1,2'-naphthalene]", "spiro[cyclohexa-2,5-diene-1,1'-indene]", "spiro[cyclopent-2-ene-1,1'-indene]",
  "7-chloro-2',4,6-trimethoxy-6'-methyl-3H-spiro[1-benzofuran-2,1'-cyclohex-2-ene]-3,4'-dione", "spiro[cyclohexa-2,5-diene-1,1'(4'H)-naphthalen]-4-one",
]);
// Rings of nine members or more (two fusion bonds at most, as OPSIN numbers them): [n]annulenes and replacement
// names (benzo crown ethers).
run("large rings", [
  "6,7,9,10,17,18,20,21-octahydrodibenzo[b,k][1,4,7,10,13,16]hexaoxacyclooctadecine", "2,3,5,6,8,9,11,12-octahydro-1,4,7,10,13-benzopentaoxacyclopentadecine",
  "benzo[18]annulene", "cyclododeca[b]pyridine", "benzo[10]annulene", "6,7,8,9,10,11-hexahydro-5H-benzo[9]annulene",
  "2,3,5,6,8,9,11,12,14,15-decahydro-1,4,7,10,13,16-benzohexaoxacyclooctadecine",
]);
// Acyl groups on fused and other rings, numbered as the ring (these once failed with "Cannot read properties of
// undefined (reading 'indexOf')"): folic acid, methotrexate, carbonyldiimidazole and imidazole acids.
run("ring acyl groups", [
  "folic acid", "smiles:CN(Cc1cnc2nc(N)nc(N)c2n1)c1ccc(cc1)C(=O)N[C@@H](CCC(O)=O)C(O)=O", "1,1'-carbonyldiimidazole",
  "carbonyldiimidazolal", "carbonyldiimidazoleic acid", "1,1'-carbonylbis(2-methylimidazole)", "1,1'-carbonyldi(1,2,4-triazole)",
]);
