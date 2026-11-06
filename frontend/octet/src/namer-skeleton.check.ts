// Run: node src/namer-skeleton.check.ts. Carbon skeletons and functional groups: the λ-convention in fused rings,
// polycyclic von Baeyer systems and cubane, ring triple bonds (didehydro), corrin, thio and peroxy carbonic acid
// derivatives, diacyl sulfides, hydrazine and diazene acids, rings with halogen atoms, ring imines and acyl groups on
// ring heteroatoms. Each name becomes a structure (OPSIN), Octet names the structure, and OPSIN must read Octet's name
// back as the same structure (same standard InChI). Every one must be named, and none may be wrong; with "=", the name
// must be exactly the one given. Hydrogen counts come from the input (a ring Br with an H is drawn with its H).
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-skeleton.check: skipped (no OPSIN build)"); process.exit(0); }
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
type Ket = { root: { nodes: { $ref: string }[] }; [k: string]: unknown };
type Frag = { type: string; atoms: { label: string; charge?: number; cip?: string }[]; bonds: { type: number; atoms: [number, number]; cip?: string }[] };
const frags = (ket: Ket) => ket.root.nodes.map(({ $ref }) => ket[$ref] as Frag).filter((f) => f?.type === "molecule");
// The CIP labels Octet gives (cip.ts) the structure as Indigo lays the SMILES out (with wedges), on the atoms and bonds
// Indigo reads. A drawn double bond always has a geometry; one the SMILES leaves open (Indigo gives it no label) has no
// E or Z.
function cipOf(smiles: string, bonds: { cip?: string }[]) {
  const o = new indigo.MapStringString(), m: Mol = { atoms: [], bonds: [] };
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
  if (m.bonds.length !== bonds.length) throw new Error(`cipOf: Indigo read ${smiles} two ways`);
  const c = cipLabels(m);
  return { atoms: c.atoms, bonds: bonds.map((b, k) => (b.cip ? c.bonds[k] : undefined)) };
}
// The structure and each atom's hydrogen count, read from SMILES by Indigo (Kekulé bonds).
function graph(smiles: string) {
  const o = new indigo.MapStringString();
  o.set("output-content-type", "application/json");
  o.set("dearomatize-on-load", "true");
  try {
    const before = frags(JSON.parse(JSON.parse(indigo.calculateCip(smiles, "ket", o)).struct));
    const after = frags(JSON.parse(JSON.parse(indigo.convert_explicit_hydrogens(smiles, "unfold", "ket", o)).struct));
    const atoms: Frag["atoms"] = [], bonds: Frag["bonds"] = [], h: number[] = [];
    before.forEach((f, k) => {
      const base = atoms.length, count = f.atoms.map(() => 0);
      for (const b of after[k].bonds) if (b.atoms[1] >= f.atoms.length) count[b.atoms[0]]++; else if (b.atoms[0] >= f.atoms.length) count[b.atoms[1]]++;
      atoms.push(...f.atoms);
      bonds.push(...f.bonds.map((b) => ({ ...b, atoms: [b.atoms[0] + base, b.atoms[1] + base] as [number, number] })));
      h.push(...count);
    });
    const mol: Mol = { atoms: atoms.map((a, i) => ({ label: a.label, charge: a.charge, implicitHCount: h[i], location: [0, 0, 0] as [number, number, number] })), bonds: bonds.map((b) => ({ type: b.type, atoms: b.atoms })) };
    return graphOf(mol, cipOf(smiles, bonds));
  } finally { o.delete(); }
}

// Each input (a name, or smiles:...) must get a name that OPSIN reads back as the same structure. With "=", the name
// must also be exactly the one given.
function run(label: string, inputs: string[]) {
  let ms = 0;
  for (const input of inputs) {
    const [source, want] = input.split(" = ");
    const smiles = source.startsWith("smiles:") ? source.slice(7) : opsin.parseToSmiles(source);
    assert.ok(smiles, `OPSIN reads ${source}`);
    const g = graph(smiles);
    assert.ok(g, `graph of ${source}`);
    const t = performance.now();
    const r = iupacNameWhy(g);
    ms += performance.now() - t;
    assert.ok(r.name, `no name for ${source} (${smiles}): ${r.why}`);
    const back = opsin.parseToSmiles(r.name);
    assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${source} -> ${r.name}, a different structure`);
    if (want) assert.equal(r.name, want, source);
  }
  console.log(`namer-skeleton.check: ${label} ${inputs.length}/${inputs.length} (${(ms / inputs.length).toFixed(1)} ms each)`);
}

// =O on a ring S or P of a fused system, by the λ-convention (P-14.1.3): a heterone suffix, or oxo prefixes. The λ goes
// with the heteroatom's locant where the name starts with locants (1λ⁶,2-benzothiazine), else in front of the name.
run("λ in fused rings", [
  "isobenzothiofuranone = 2λ⁴-benzothiophen-2-one", "phenothiazinone = 10H-5λ⁴-phenothiazin-5-one", "thianthrenone = 5λ⁴-thianthren-5-one",
  "phosphindolone = 1H-1λ⁵-benzophosphol-1-one", "piazthiolone = 2λ⁴,1,3-benzothiadiazol-2-one", "thiochromenone = 2H-1λ⁴-benzothiopyran-1-one",
  "acridophosphinone = 5λ⁵-dibenzo[b,e]phosphinin-5(10H)-one", "phenoxaphosphinone = 10H-10λ⁵-dibenzo[b,e][1,4]oxaphosphinin-10-one",
  "phenoxathiinone", "phosphanthridinone", "triphenodithiazinone", "phenothiarsinone",
  "smiles:CN1C(C(=O)Nc2ccccn2)=C(O)c2ccccc2S1(=O)=O = 4-hydroxy-2-methyl-1,1-dioxo-N-(pyridin-2-yl)-2H-1λ⁶,2-benzothiazine-3-carboxamide",
  "smiles:CN1C(C(=O)Nc2ncc(C)s2)=C(O)c2ccccc2S1(=O)=O = 4-hydroxy-2-methyl-N-(5-methyl-1,3-thiazol-2-yl)-1,1-dioxo-2H-1λ⁶,2-benzothiazine-3-carboxamide",
  "smiles:NS(=O)(=O)c1cc2c(cc1Cl)NCNS2(=O)=O = 6-chloro-1,1-dioxo-3,4-dihydro-2H-1λ⁶,2,4-benzothiadiazine-7-sulfonamide",
]);

// Polycyclic von Baeyer systems (P-23.2.5.1): main ring, main bridge, symmetric division, low superscripts; cubane is
// a retained name (P-23.7); adamantane takes no ene ending, so adamantene is named by von Baeyer rules.
run("von Baeyer", [
  "cubane = cubane", "1,4-dichlorocubane = 1,4-dichlorocubane", "cubane-1,4-dicarboxylic acid = cubane-1,4-dicarboxylic acid", "2,3,7-trichlorocubane",
  "cubene = pentacyclo[4.2.0.0²,⁵.0³,⁸.0⁴,⁷]oct-1-ene", "prismane = tetracyclo[2.2.0.0²,⁶.0³,⁵]hexane", "prismene = tetracyclo[2.2.0.0²,⁶.0³,⁵]hex-1-ene",
  "adamantene = tricyclo[3.3.1.1³,⁷]dec-1-ene", "tricyclo[4.2.2.2^{2,5}]dodecane = tricyclo[4.2.2.2²,⁵]dodecane",
  "11-chlorotricyclo[4.2.2.2^{2,5}]dodecane = 3-chlorotricyclo[4.2.2.2²,⁵]dodecane", "tricyclo[2.2.1.0^{2,6}]heptane = tricyclo[2.2.1.0²,⁶]heptane",
  "pentacyclo[4.3.0.0^{2,5}.0^{3,8}.0^{4,7}]nonane = pentacyclo[4.3.0.0²,⁵.0³,⁸.0⁴,⁷]nonane",
  "smiles:CN1[C@@H]2CC(C[C@H]1[C@H]1[C@@H]2O1)OC(=O)[C@H](CO)c1ccccc1 = (1S,2S,4R,5R)-9-methyl-3-oxa-9-azatricyclo[3.3.1.0²,⁴]nonan-7-yl (2S)-3-hydroxy-2-phenylpropanoate",
  "ajmalene = (1R,9R,10S,12S,13S,16S)-13-ethyl-8-methyl-8,15-diazahexacyclo[14.2.1.0¹,⁹.0²,⁷.0¹⁰,¹⁵.0¹²,¹⁷]nonadeca-2,4,6,17-tetraene",
]);

// A ring triple bond in a fused system: a double bond of the parent made triple by didehydro, cited with the hydro
// prefixes (P-31.1.4.2.4).
run("ring triple bonds", [
  "9,10-didehydrophenanthrene = 9,10-didehydrophenanthrene", "1,2-didehydronaphthalene = 1,2-didehydronaphthalene",
  "smiles:C1CC2=CC=CC=C2C#C1 = 1,2-didehydro-3,4-dihydronaphthalene", "smiles:C1CCC2C(C1)CCC#C2 = 5,6-didehydro-1,2,3,4,4a,7,8,8a-octahydronaphthalene",
  "androstyne = (8R,9S,10S,13S,14S)-10,13-dimethyl-16,17-didehydro-2,3,4,5,6,7,8,9,10,11,12,13,14,15-tetradecahydro-1H-cyclopenta[a]phenanthrene",
  "estryne", "gonyne", "dihydromorphinyne = (4aR,10R,10aR)-7,8-didehydro-1,2,3,4,4a,9,10,10a-octahydro-10,4a-(epiminoethano)phenanthrene",
  "diacetyldihydromorphinyne", "aconityne", "spirostyne",
]);

// Corrin (P-101): a parent with no mancude form, named only with its own saturated atoms.
run("corrin", [
  "corrine = corrin", "corrinal = corrin-1-carbaldehyde", "corrinol = corrin-1-ol", "corrinone = corrin-2-one", "corrinic acid = corrin-1-carboxylic acid",
  "corrinide = corrin-24-ide", "smiles:C12CCC(=N1)C=C1CCC(=N1)C=C1CCC(=N1)CC1CCC2N1 = 15,16-dihydrocorrin",
]);

// Carbonic acid derivatives (P-65.2.1, P-66.1.6, P-66.4.1): thio and seleno analogues with O- and S- locants where both
// elements are in the name, peroxy acids, diacyl sulfides and disulfides, hydrazine and diazene acids, N-sulfonyl ureas.
run("carbonic acid derivatives", [
  "isothiourea = carbamimidothioic acid", "isoselenourea = carbamimidoselenoic acid", "isotellurourea = carbamimidotelluroic acid",
  "smiles:CSC(=N)N = methyl carbamimidothioate", "smiles:CN(C)C(=S)S = N,N-dimethylcarbamodithioic acid",
  "smiles:CN(C)C(=S)SC = methyl N,N-dimethylcarbamodithioate", "smiles:CCCN(CCC)C(=O)SCC = S-ethyl N,N-dipropylcarbamothioate",
  "smiles:CN(C)C(=S)OC = O-methyl N,N-dimethylcarbamothioate", "smiles:COC(=O)SC = O,S-dimethyl carbonothioate", "smiles:COC(=S)OC = O,O-dimethyl carbonothioate",
  "smiles:CCOC(=S)SC = O-ethyl S-methyl carbonodithioate", "smiles:CSC(=O)SC = S,S-dimethyl carbonodithioate", "smiles:CSC(=S)SC = dimethyl carbonotrithioate",
  "smiles:CCOC(=S)S = O-ethyl hydrogen carbonodithioate", "smiles:SC(=S)S = carbonotrithioic acid", "smiles:ClC(=S)Cl = carbonothioyl dichloride",
  "smiles:ClC(=S)Oc1ccccc1 = O-phenyl carbonochloridothioate", "smiles:ClC(=O)SC = S-methyl carbonochloridothioate", "smiles:NC(=S)Cl = carbamothioyl chloride",
  "smiles:CSC(=NC#N)SC = dimethyl N-cyanocarbonimidodithioate", "smiles:COC(=N)SC = O,S-dimethyl carbonimidothioate",
  "pyridate = O-(6-chloro-3-phenylpyridazin-4-yl) S-octyl carbonothioate", "peroxocarbonic acid = carbonoperoxoic acid",
  "peroxodicarbonic acid = peroxydicarbonic acid", "smiles:CC(C)OC(=O)OOC(=O)OC(C)C = bis(propan-2-yl) peroxydicarbonate",
  "thiuram disulfide = dicarbamothioyl disulfide", "thiuram monosulfide = dicarbamothioyl sulfide",
  "smiles:CCN(CC)C(=S)SSC(=S)N(CC)CC = bis(diethylcarbamothioyl) disulfide", "smiles:CCOC(=S)SSC(=S)OCC = bis(ethoxycarbonothioyl) disulfide",
  "smiles:CC(=O)SSC(C)=O = diacetyl disulfide", "smiles:CC(=O)SC(C)=O = diacetyl sulfide",
  "biguanidine = hydrazine-1,2-dicarboximidamide", "aminoguanidine = hydrazinecarboximidamide", "isosemicarbazide = hydrazinecarboximidic acid",
  "carbazone = diazenecarbohydrazide", "diazenecarboxamide = diazenecarboxamide", "carbodiazone = didiazenylmethanone",
  "smiles:O=C(N=Nc1ccccc1)NNc1ccccc1 = N',2-diphenyldiazene-1-carbohydrazide", "smiles:CC(=O)N=Nc1ccccc1 = 1-(phenyldiazenyl)ethan-1-one", "cyanogen azide = carbononitridic azide",
  "smiles:Cc1ccc(cc1)S(=O)(=O)NC(=O)NN1CC2CCCC2C1 = N-(4-methylbenzene-1-sulfonyl)-N'-(octahydrocyclopenta[c]pyrrol-2-yl)urea",
  "smiles:Cc1cnc(cn1)C(=O)NCCc1ccc(cc1)S(=O)(=O)NC(=O)NC1CCCCC1", "smiles:COc1ccc(Cl)cc1C(=O)NCCc1ccc(cc1)S(=O)(=O)NC(=O)NC1CCCCC1",
  "smiles:CC1Cc2ccccc2N1NC(=O)c1ccc(Cl)c(c1)S(N)(=O)=O = 4-chloro-N-(2-methyl-2,3-dihydro-1H-indol-1-yl)-3-sulfamoylbenzamide",
  // Formic acid takes a nitro prefix (P-65.1.8.2: O2N-COOH nitroformic acid, PIN); halogens, -CN, -N3, -NH2 and the like
  // make carbonic acid derivatives instead (P-65.1.8.1).
  "nitroformic acid = nitroformic acid", "smiles:COC(=O)[N+](=O)[O-] = methyl nitroformate", "smiles:[Na+].[O-]C(=O)[N+](=O)[O-] = sodium nitroformate",
  "chloroformic acid = carbonochloridic acid",
]);

// Rings with halogen atoms (Hantzsch–Widman fluora, chlora, broma, ioda, P-22.2.2.1.1), always with λ; acyl groups on a
// ring P or As, which stand where a ring N would.
run("ring heteroatoms", [
  "bromole = 1λ³-bromole", "chlorole = 1λ³-chlorole", "iodole = 1λ³-iodole", "methoxychlorole = 2-methoxy-1λ³-chlorole",
  "chlorazinane = 1λ³,2-chlorazinane", "chlorazinine = 2H-1λ³,2-chlorazine", "chlorazinal = 2H-1λ³,2-chlorazine-3-carbaldehyde",
  "chlorazinone = 2H-1λ⁵,2-chlorazin-1-one", "arsindolinic acid = 2,3-dihydro-1H-1-benzarsole-1-carboxylic acid",
  "phosphindolinal = 2,3-dihydro-1H-1-benzophosphole-1-carbaldehyde", "smiles:CC(=O)P1CCCC1 = 1-(phospholan-1-yl)ethan-1-one",
  // Hypervalent iodine in a ring with OH, O-alkyl, acyloxy and =O on it: IBA, IBX, Dess–Martin periodinane, Togni reagents.
  "1-hydroxy-1λ3,2-benziodoxol-3(1H)-one = 1-hydroxy-3H-1λ³,2-benziodoxol-3-one", "smiles:OI1(=O)OC(=O)c2ccccc12 = 1-hydroxy-3H-1λ⁵,2-benziodoxole-1,3-dione",
  "smiles:CC(=O)OI1(OC(C)=O)(OC(C)=O)OC(=O)c2ccccc12 = 1,1,1-tris(acetyloxy)-3H-1λ⁵,2-benziodoxol-3-one",
  "3,3-dimethyl-1-(trifluoromethyl)-1λ3,2-benziodoxole = 3,3-dimethyl-1-(trifluoromethyl)-3H-1λ³,2-benziodoxole", "smiles:c1ccc2c(c1)[IH]c1ccccc12 = 5λ³-dibenzo[b,d]iodole",
]);

// Drugs: an amidine and a guanidine with =N-sulfonyl and =N-cyano (famotidine, cimetidine, with their E and Z), and a
// fused parent that needs three indicated hydrogens (topiramate, written bis[1,3]dioxolo as OPSIN reads it).
run("drugs", [
  "smiles:NC(N)=Nc1nc(CSCC/C(N)=N/S(N)(=O)=O)cs1", "smiles:CC/C(N)=N/S(N)(=O)=O = (1Z)-N'-sulfamoylpropanimidamide",
  "smiles:NC(N)=NS(=O)(=O)c1ccccc1 = N''-(benzenesulfonyl)guanidine", "smiles:CN/C(NCC)=N\\C#N = (E)-N''-cyano-N-ethyl-N'-methylguanidine",
  "smiles:CN/C(NCCSCc1nc[nH]c1C)=N\\C#N", "smiles:C1OC2COC3OCOC3C2O1 = 5,5a,8a,8b-tetrahydro-2H,3aH,7H-bis[1,3]dioxolo[4,5-b:4',5'-d]pyran",
  "smiles:CC1(C)O[C@@H]2CO[C@@]3(COS(N)(=O)=O)OC(C)(C)O[C@H]3[C@@H]2O1",
]);

// Ring imines, as ring ketones are (with indicated and added hydrogen), and nitroso on a carbonyl carbon.
run("imines and nitroso", [
  "pyrimidoone = 2H-pyran-2-imine", "pyrrolidin-2-imine = pyrrolidin-2-imine", "pyridin-2(1H)-imine = pyridin-2(1H)-imine",
  "quinolin-2(1H)-imine = quinolin-2(1H)-imine", "acridin-9(10H)-imine = acridin-9(10H)-imine", "1H-isoindole-1,3(2H)-diimine",
  "harmanamidone = (7-methoxy-9H-pyrido[3,4-b]indol-1-yl)(nitroso)methanone", "smiles:O=NC(=O)c1ccccc1 = nitroso(phenyl)methanone",
  "sulfoxylose = (2R,3S,4R)-2,3,4,5-tetrahydroxy-1-oxopentane-1-sulfonic acid", "smiles:CCC(=O)S(C)(=O)=O = 1-(methanesulfonyl)propan-1-one",
]);

// R and S next to a triple bond, where the triple bond's duplicate atoms decide the rank (cip.ts ranks them).
run("stereo next to triple bonds", [
  "morphinyne = (4aR,10R,10aR)-3,4-didehydro-1,2,4a,9,10,10a-hexahydro-10,4a-(epiminoethano)phenanthrene",
  "diacetylmorphinyne", "gorgostyne", "(3S)-3-methyl-3-phenylpent-1-yne = [(3S)-3-methylpent-1-yn-3-yl]benzene",
  "(3R)-3-methyl-3-phenylpent-1-yne = [(3R)-3-methylpent-1-yn-3-yl]benzene",
  "smiles:C[C@]12CC[C@H]3[C@@H](CCc4cc(O)ccc34)[C@@H]1CC[C@@]2(O)C#C", // ethinylestradiol
  "smiles:CC[C@]12CC[C@H]3[C@@H](CCC4=CC(=O)CC[C@H]34)[C@@H]1CC[C@@]2(O)C#C", // levonorgestrel
  // cholecalciferol, with the brackets of P-16.5.4.1.5: [(2E)-…], not ((2E)-…)
  "smiles:C[C@H](CCCC(C)C)[C@H]1CC[C@H]2/C(=C/C=C3/C[C@@H](O)CCC3=C)CCC[C@]12C = (1S,3Z)-3-[(2E)-2-{(1R,3aS,7aR)-7a-methyl-1-[(2R)-6-methylheptan-2-yl]-2,3,3a,4,5,6,7,7a-octahydro-1H-inden-4-ylidene}ethylidene]-4-methylidenecyclohexan-1-ol",
]);

// No name rather than a wrong one: OPSIN reads no O- or S-acid of the carbamothioic acids.
assert.equal(iupacNameWhy(graph("NC(=O)S")!).why, "thio acid");
console.log("namer-skeleton.check: no name for carbamothioic S-acid, as expected");
