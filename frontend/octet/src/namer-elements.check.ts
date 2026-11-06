// Run: node src/namer-elements.check.ts. Structure to Name for main-group elements beyond C, N, O, S, P and the
// halogens: Si, B, Se, Te, As, Sb, Bi, Ge, Sn, Pb, Al, Ga, In, Tl and Hg. Each name becomes a structure (OPSIN), Octet
// names the structure, and OPSIN must read Octet's name back as the same structure (same standard InChI). Every one
// must be named; where a name is given, Octet must give that name.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-elements.check: skipped (no OPSIN build)"); process.exit(0); }
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

// Input (a name OPSIN reads, or smiles:...) and, where it matters, the name Octet must give.
const cases: [string, string?][] = [
  // Silicon: silanes, silyl ethers and protecting groups, silanols, chlorosilanes, siloxanes, silanamines, rings.
  ["trimethyl(phenyl)silane", "trimethyl(phenyl)silane"], ["ethynyl(trimethyl)silane", "ethynyl(trimethyl)silane"],
  ["methoxy(trimethyl)silane"], ["tert-butyl(dimethyl)(phenoxy)silane"], ["chloro(trimethyl)silane", "chloro(trimethyl)silane"],
  ["tert-butyl(chloro)dimethylsilane", "tert-butyl(chloro)(dimethyl)silane"], ["chloro(triisopropyl)silane"], ["tert-butyl(chloro)diphenylsilane"],
  ["4-{[tert-butyl(dimethyl)silyl]oxy}butan-1-ol", "4-{[tert-butyl(dimethyl)silyl]oxy}butan-1-ol"], ["{[tri(propan-2-yl)silyl]oxy}benzene"],
  ["2-(trimethylsilyl)ethan-1-ol", "2-(trimethylsilyl)ethan-1-ol"], ["4-(trimethylsilyl)but-3-yn-2-one"], ["trimethyl(prop-2-en-1-yl)silane"],
  ["ethyl 3-(trimethylsilyl)propanoate"], ["4-(trimethylsilyl)aniline"], ["2-(trimethylsilyl)pyridine", "2-(trimethylsilyl)pyridine"],
  ["trimethyl(thiophen-2-yl)silane"], ["(diazomethyl)(trimethyl)silane"], ["trimethylsilyl acetate", "trimethylsilyl acetate"],
  ["trimethylsilanol", "trimethylsilanol"], ["triphenylsilanol"], ["dimethylsilanediol", "dimethylsilanediol"], ["phenylsilanetriol"],
  ["4-[hydroxy(dimethyl)silyl]phenol"], ["phenylsilane"], ["triethylsilane"], ["tetrachlorosilane"], ["tetraethoxysilane"],
  ["hexamethyldisiloxane", "hexamethyldisiloxane"], ["hexamethyldisilane", "hexamethyldisilane"], ["1,1,3,3-tetramethyldisiloxane", "1,1,3,3-tetramethyldisiloxane"],
  ["octamethyltrisiloxane", "octamethyltrisiloxane"], ["1,1,3,3-tetramethyldisiloxane-1,3-diol"], ["1,3-dichloro-1,1,3,3-tetrakis(propan-2-yl)disiloxane"],
  ["1,1,1,3,3,3-hexamethyl-2-(trimethylsilyl)trisilane", "1,1,1,3,3,3-hexamethyl-2-(trimethylsilyl)trisilane"],
  ["1,1,1-trimethyl-N-(trimethylsilyl)silanamine", "1,1,1-trimethyl-N-(trimethylsilyl)silanamine"], ["N,N-diethyl-1,1,1-trimethylsilanamine"],
  ["1-(trimethylsilyl)-1H-imidazole", "1-(trimethylsilyl)-1H-imidazole"], ["azido(trimethyl)silane", "azido(trimethyl)silane"],
  ["octamethylcyclotetrasiloxane", "octamethyl-1,3,5,7,2,4,6,8-tetraoxatetrasilocane"],
  ["1,1-dimethylsilolane", "1,1-dimethylsilolane"], ["silinane", "silinane"], ["1,1-dimethyl-1H-silole", "1,1-dimethyl-1H-silole"],
  ["tert-butyl(dimethyl){[(2S)-oxiran-2-yl]methoxy}silane"], ["trimethyl(trifluoromethyl)silane"], ["smiles:C=C(O[Si](C)(C)C)c1ccccc1"],
  ["smiles:CC(C)(C)[Si](c1ccccc1)(c1ccccc1)OCCO", "2-{[tert-butyl(diphenyl)silyl]oxy}ethan-1-ol"], ["smiles:CCO[Si](CCCN)(OCC)OCC", "3-(triethoxysilyl)propan-1-amine"],
  ["smiles:C[Si](C)(C)C#N", "trimethylsilanecarbonitrile"], ["smiles:N#C[Si](C)(C)c1ccc(C(=O)O)cc1"], ["smiles:C[Si](C)(C)SC"],
  ["smiles:O=C(O[Si](C)(C)C)C(F)(F)F", "trimethylsilyl trifluoroacetate"], ["smiles:C[Si](C)(C)CC(=O)Cl"],
  ["2,2,2-trifluoro-N-methyl-N-(trimethylsilyl)acetamide"], ["N-(trimethylsilyl)acetamide", "N-(trimethylsilyl)acetamide"], ["smiles:O=C1CCCN1[Si](C)(C)C"],
  // Boron: boronic and borinic acids, boronate esters (pinacol, neopentyl glycol), boranes, borates.
  ["phenylboronic acid", "phenylboronic acid"], ["(4-formylphenyl)boronic acid", "(4-formylphenyl)boronic acid"], ["4-boronobenzoic acid", "4-boronobenzoic acid"],
  ["(pyridin-3-yl)boronic acid", "(pyridin-3-yl)boronic acid"], ["(3-aminophenyl)boronic acid"], ["(2,4-difluorophenyl)boronic acid"], ["1,4-phenylenebis(boronic acid)"],
  ["diphenylborinic acid", "diphenylborinic acid"], ["boric acid", "boric acid"],
  ["4,4,5,5-tetramethyl-2-phenyl-1,3,2-dioxaborolane", "4,4,5,5-tetramethyl-2-phenyl-1,3,2-dioxaborolane"],
  ["4-(tetramethyl-1,3,2-dioxaborolan-2-yl)aniline", "4-(tetramethyl-1,3,2-dioxaborolan-2-yl)aniline"],
  ["methyl 4-(4,4,5,5-tetramethyl-1,3,2-dioxaborolan-2-yl)benzoate"], ["1-methyl-4-(4,4,5,5-tetramethyl-1,3,2-dioxaborolan-2-yl)-1H-pyrazole"],
  ["4,4,5,5-tetramethyl-1,3,2-dioxaborolane", "4,4,5,5-tetramethyl-1,3,2-dioxaborolane"], ["2-ethenyl-4,4,5,5-tetramethyl-1,3,2-dioxaborolane"],
  ["2-methoxy-4,4,5,5-tetramethyl-1,3,2-dioxaborolane"], ["4,4,4',4',5,5,5',5'-octamethyl-2,2'-bi-1,3,2-dioxaborolane"],
  ["5,5-dimethyl-2-phenyl-1,3,2-dioxaborinane", "5,5-dimethyl-2-phenyl-1,3,2-dioxaborinane"],
  ["dimethyl phenylboronate", "dimethyl phenylboronate"], ["trimethyl borate", "trimethyl borate"], ["triisopropyl borate"], ["methyl diphenylborinate"],
  ["smiles:COB(OC)c1ccc(C(C)=O)cc1", "dimethyl (4-acetylphenyl)boronate"], ["triethylborane", "triethylborane"], ["dichloro(phenyl)borane"],
  ["9-borabicyclo[3.3.1]nonane", "9-borabicyclo[3.3.1]nonane"], ["borinane"], ["1H-borole"], ["borinine"],
  ["tribromoborane"], ["tris(pentafluorophenyl)borane"], ["smiles:CC(C)C[C@@H](NC(=O)[C@H](Cc1ccccc1)NC(=O)c1cnccn1)B(O)O"],
  ["potassium trifluoro(phenyl)boranuide", "potassium trifluoro(phenyl)boranuide"], ["potassium ethenyl(trifluoro)boranuide"],
  ["sodium tris(acetyloxy)boranuide", "sodium tris(acetyloxy)boranuide"], ["sodium cyanoboranuide", "sodium cyanoboranuide"],
  ["sodium tetraphenylboranuide"], ["lithium triethylboranuide"], ["smiles:C[N+](C)(C)C.F[B-](F)(F)c1ccccc1"],
  // Selenium and tellurium, like sulfur: selanyl prefixes, selenols, diselanes, selenoxides, Se acids, selenophene.
  ["(methylselanyl)benzene", "(methylselanyl)benzene"], ["(phenylselanyl)benzene"], ["benzeneselenol", "benzeneselenol"], ["methaneselenol"],
  ["(phenyldiselanyl)benzene", "1,1'-diselanediyldibenzene"], ["(methaneseleninyl)benzene", "(methaneseleninyl)benzene"], ["(methaneselenonyl)benzene"],
  ["(chloroselanyl)benzene", "(chloroselanyl)benzene"], ["benzeneseleninic acid", "benzeneseleninic acid"], ["benzeneselenonic acid"], ["4-selenonobenzoic acid"],
  ["selenomethionine", "(2S)-2-amino-4-(methylselanyl)butanoic acid"], ["selenocysteine", "(2R)-2-amino-3-selanylpropanoic acid"], ["selenocystine"],
  ["2-(phenylselanyl)propanoic acid"], ["4-(phenylselanyl)benzoic acid"], ["(methyldiselanyl)methane"],
  ["selenophene", "selenophene"], ["tellurophene", "tellurophene"], ["2-methylselenophene"], ["selenophene-2-carboxylic acid"],
  ["1-(selenophen-2-yl)ethan-1-one"], ["2,2'-biselenophene"], ["1,3-selenazole", "1,3-selenazole"], ["1,2,5-selenadiazole", "1,2,5-selenadiazole"],
  ["selenane"], ["selenolane"], ["1,3-selenazolidine"],
  // Rings neither saturated nor mancude: the mancude parent with indicated hydrogen and hydro prefixes.
  ["1,1-dimethyl-2,5-dihydro-1H-silole", "1,1-dimethyl-2,5-dihydro-1H-silole"], ["smiles:C[Si]1(C)C=CCC1", "1,1-dimethyl-2,3-dihydro-1H-silole"],
  ["1,2-dihydro-1,2-azaborinine", "1,2-dihydro-1,2-azaborinine"], ["3H-1,2-diselenole", "3H-1,2-diselenole"], ["4,5-dihydro-1,2-selenazole"],
  ["2H-selenopyran", "2H-selenine"], ["4H-selenopyran", "4H-selenine"], ["3,6-dihydro-2H-1,2-oxaborinine"], ["smiles:O=C1C=C[Se]C1", "selenophen-3(2H)-one"],
  ["2,3-dihydroselenophene", "2,3-dihydroselenophene"],
  ["(methyltellanyl)benzene"], ["(phenyltellanyl)benzene"], ["benzenetellurol"], ["benzenetelluronic acid"],
  // Benzo-fused rings with Se, Te and B: ebselen, tavaborole, crisaborole, catechol boronates.
  ["1-benzoselenophene", "1-benzoselenophene"], ["1-benzoselenophene-2-carboxylic acid"], ["1-benzotellurophene"], ["2-benzoselenophene"],
  ["2,1,3-benzoselenadiazole", "2,1,3-benzoselenadiazole"], ["5-bromo-2,1,3-benzoselenadiazole"], ["1,3-benzoselenazole"], ["2-methyl-1,3-benzoselenazole"],
  ["2-phenyl-1,2-benzoselenazol-3(2H)-one", "2-phenyl-1,2-benzoselenazol-3(2H)-one"], ["2-phenyl-1,3,2-benzodioxaborole", "2-phenyl-2H-1,3,2-benzodioxaborole"],
  ["5-fluoro-2,1-benzoxaborol-1(3H)-ol", "5-fluoro-1-hydroxy-1,3-dihydro-2,1-benzoxaborole"],
  ["4-[(1-hydroxy-1,3-dihydro-2,1-benzoxaborol-5-yl)oxy]benzonitrile", "4-[(1-hydroxy-1,3-dihydro-2,1-benzoxaborol-5-yl)oxy]benzonitrile"],
  // Arsenic, antimony, bismuth: arsanes, arsonic and arsinic acids, oxides.
  ["N,N-dimethylboranamine", "N,N-dimethylboranamine"], ["1,1-diethyl-N,N-dimethylboranamine"], ["N,N-di(propan-2-yl)boranamine"],
  ["dodecamethylcyclohexasilane", "dodecamethylhexasilinane"], ["tetradecafluorohexane"],
  ["triphenylarsane", "triphenylarsane"], ["triphenylstibane", "triphenylstibane"], ["triphenylbismuthane", "triphenylbismuthane"],
  ["phenylarsonic acid", "phenylarsonic acid"], ["(4-aminophenyl)arsonic acid", "(4-aminophenyl)arsonic acid"], ["dimethylarsinic acid", "dimethylarsinic acid"],
  ["4-arsonobenzoic acid", "4-arsonobenzoic acid"], ["triphenylarsane oxide", "triphenylarsane oxide"], ["phenylstibonic acid"], ["diphenylstibinic acid"],
  ["dimethylarsinous acid"], ["phenylarsonous acid"], ["dichloro(methyl)arsane"], ["chloro(diphenyl)arsane"], ["1,2-bis(diphenylarsanyl)ethane"],
  ["1H-arsole", "1H-arsole"], ["arsinine", "arsinine"], ["arsoric acid"],
  ["tetraphenylarsonium chloride", "tetraphenylarsanium chloride"], ["methyltriphenylarsanium bromide"], ["smiles:[Br-].C[Sb+](C)(C)C", "tetramethylstibanium bromide"],
  // Germanium, tin, lead, aluminium, gallium, indium, mercury.
  ["tetraethylgermane", "tetraethylgermane"], ["tributyl(phenyl)stannane", "tributyl(phenyl)stannane"], ["tributyl(chloro)stannane"],
  ["tributyl(thiophen-2-yl)stannane"], ["tributyl(prop-2-en-1-yl)stannane"], ["hexabutyldistannane", "hexabutyldistannane"],
  ["hexabutyldistannoxane", "hexabutyldistannoxane"], ["2-(trimethylstannyl)pyridine"], ["tetraethylplumbane", "tetraethylplumbane"],
  ["triethylalumane"], ["trimethylgallane"], ["trimethylindigane"], ["1H-alumole"], ["bis(2-methylpropyl)alumane"], ["chloro(diethyl)alumane"],
  ["lithium aluminium hydride", "lithium tetrahydroaluminate"], ["smiles:Cl[Al](Cl)Cl", "trichloroalumane"], ["smiles:Cl[Sn](Cl)(Cl)Cl", "tetrachlorostannane"],
  ["smiles:CCCC[Sn](CCCC)(CCCC)SC1=CC=CC=C1", "tributyl(phenylsulfanyl)stannane"], ["smiles:CC[Hg]Sc1ccccc1C(=O)O", "2-[(ethylmercurio)sulfanyl]benzoic acid"],
  ["dimethylmercury", "dimethylmercury"], ["chloro(methyl)mercury", "chloro(methyl)mercury"], ["diphenylmercury"],
  ["(acetyloxy)(phenyl)mercury", "(acetyloxy)(phenyl)mercury"], ["4-(chloromercurio)benzoic acid", "4-(chloromercurio)benzoic acid"],
];

const out: string[] = [];
for (const [input, want] of cases) {
  const smiles = input.startsWith("smiles:") ? input.slice(7) : opsin.parseToSmiles(input);
  assert.ok(smiles, `OPSIN reads ${input}`);
  const g = graphOf(molOf(smiles), cipOf(smiles));
  assert.ok(g, `a graph for ${input}`);
  const r = iupacNameWhy(g);
  assert.ok(r.name, `no name for ${input} (${smiles}): ${r.why}`);
  const back = opsin.parseToSmiles(r.name);
  assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${input} -> ${r.name}, a different structure`);
  if (want) assert.equal(r.name, want, `${input}`);
  out.push(`${input} -> ${r.name}`);
}
if (process.argv.includes("--names")) console.log(out.join("\n"));
console.log(`namer-elements.check: ${cases.length}/${cases.length} named and read back`);
