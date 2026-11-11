// Run: node src/namer-hetero.check.ts. Groups built on N, O, S, P and the halogens (namer-hetero.ts). Each name (or
// "smiles:" structure) becomes a structure, Octet names it, and OPSIN must read Octet's name back as the same structure
// (same standard InChI). Every one must be named, and none may be wrong.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-hetero.check: skipped (no OPSIN build)"); process.exit(0); }
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

// Every input must be named, and read back as the same structure.
function must(label: string, inputs: string[]) {
  const out: string[] = [];
  for (const input of inputs) {
    const smiles = input.startsWith("smiles:") ? input.slice(7) : opsin.parseToSmiles(input);
    assert.ok(smiles, `OPSIN reads ${input}`);
    const g = graphOf(molOf(smiles), cipOf(smiles));
    assert.ok(g, `a graph for ${input}`);
    const r = iupacNameWhy(g);
    assert.ok(r.name, `no name for ${input} (${smiles}): ${r.why}`);
    const back = opsin.parseToSmiles(r.name);
    assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${input} -> ${r.name}, a different structure`);
    out.push(`${input} -> ${r.name}`);
  }
  console.log(`namer-hetero.check: ${label} ${out.length}/${inputs.length}${process.argv.includes("-v") ? `: ${out.join("; ")}` : ""}`);
}

// Thio analogues of acids, esters, amides, aldehydes, ketones and acid halides (P-65.1.5, P-66.1.4.1, P-64.6). The
// thioamide is from Sam's ChemDraw files (4-methoxybenzenecarbothioamide).
must("thio", [
  "smiles:C(=S)(N)C1=CC=C(OC)C=C1", "4-methoxybenzene-1-carbothioamide", "ethanethioamide", "N-methylethanethioamide", "N-phenylbenzenecarbothioamide",
  "ethanedithioamide", "propane-2-thione", "cyclohexanethione", "1-phenylethane-1-thione", "pyrrolidine-2-thione", "quinoline-2(1H)-thione",
  "1,7-dihydro-6H-purine-6-thione", "ethanethioic S-acid", "ethanethioic O-acid", "ethanedithioic acid", "benzenecarbothioic S-acid",
  "S-methyl ethanethioate", "O-methyl ethanethioate", "methyl ethanedithioate", "S-phenyl benzenecarbothioate", "S-(2-aminoethyl) ethanethioate",
  "ethanethial", "methanethial", "benzenecarbothialdehyde", "ethanethioyl chloride", "benzenecarbothioyl chloride",
  "4-carbamothioylbenzoic acid", "4-(dimethylcarbamothioyl)benzoic acid", "4-(ethanethioylamino)benzoic acid", "3-(acetylsulfanyl)propanoic acid",
  "4-[(methylsulfanyl)carbonyl]benzoic acid", "4-(methoxycarbonothioyl)benzoic acid", "4-methanethioylbenzoic acid", "4-(sulfanylcarbonyl)benzoic acid",
  "4-(hydroxycarbonothioyl)benzoic acid", "4-(sulfanylcarbonothioyl)benzoic acid", "4-(ethanethioyl)benzoic acid", "4-(4-methylbenzenecarbothioyl)benzoic acid",
  "4-(cyclohexanecarbothioyl)benzoic acid", "4-(ethanethioyloxy)benzoic acid", "4-sulfanylidenecyclohexan-1-one", "3-amino-3-sulfanylidenepropanamide",
  "sulfanylideneacetic acid", "thiourea", "prop-2-en-1-ylthiourea", "N,N'-diphenylthiourea", "O-methyl carbamothioate",
  "2-{[(tert-butoxy)carbonothioyl]amino}acetic acid",
  // Selenoic and telluroic O-acids as the principal group (P-65.1.5.1), as OPSIN builds seleno- and tellurohomocysteic
  // acid.
  "ethaneselenoic O-acid", "ethanetelluroic O-acid", "benzenecarboselenoic O-acid", "smiles:N[C@@H](CCS(=O)(O)=O)C(=[Se])O",
  "smiles:N[C@@H](CCS(=O)(O)=O)C(=[Te])O", "2-oxobutaneselenoic O-acid",
]);

// Hydrazines, hydrazones and diazenes (P-68.3.1.2, P-68.3.1.3). The amine on a ring N and the azo compound are from
// Sam's ChemDraw files.
must("N-N", [
  "smiles:C1C(C)CCN(N(C2C=CC=CC=2)C2C=CC=CC=2)C1", "smiles:N(=N/CCC(C)CC(=O)C)\\C1C=CC=CC=1", "4-methyl-N,N-diphenylpiperidin-1-amine",
  "piperidin-1-amine", "phenylhydrazine", "1,1-dimethylhydrazine", "1,2-diphenylhydrazine", "4-hydrazinylbenzoic acid", "4-(2-phenylhydrazinyl)benzoic acid",
  "4-(2,2-dimethylhydrazinyl)benzoic acid", "4-(1-methylhydrazinyl)benzoic acid", "(propan-2-ylidene)hydrazine", "1-phenyl-2-(propan-2-ylidene)hydrazine",
  "cyclohexylidenehydrazine", "1-benzylidene-2-phenylhydrazine", "2-(2-phenylhydrazinylidene)propanoic acid", "2-hydrazinylidenepropanoic acid",
  "4-[2-(4-nitrophenyl)hydrazinylidene]pentanoic acid", "diphenyldiazene", "(E)-diphenyldiazene", "(Z)-diphenyldiazene", "methyl(phenyl)diazene",
  "phenyldiazene", "4-(phenyldiazenyl)benzoic acid", "4-[(E)-phenyldiazenyl]benzoic acid", "4-[(E)-(4-hydroxyphenyl)diazenyl]benzoic acid",
  "2-methyl-2-(phenyldiazenyl)propanenitrile", "2,2'-azobis(2-methylpropionitrile)", "smiles:C(#N)C(C)(C)/N=N/C(C#N)(C)C",
  "4-cyanobutanoic acid", "3-cyanopropanoyl chloride", "4-(cyanomethyl)benzoic acid", "4-(2-cyanopropan-2-yl)benzoic acid",
]);
// Hydroxylamines, N-hydroxy and N-alkoxy amides and rings, nitroso compounds (P-68.3.1.1, P-61.5.1).
must("N-O", [
  "N-phenylhydroxylamine", "N,O-dimethylhydroxylamine", "O-benzylhydroxylamine", "N,N-diethylhydroxylamine", "O-methylhydroxylamine",
  "4-(hydroxyamino)benzoic acid", "4-(aminooxy)butanoic acid", "4-[(dimethylamino)oxy]butanoic acid", "4-(methoxyamino)benzoic acid",
  "piperidin-1-ol", "morpholin-4-ol", "1-hydroxypyrrolidine-2,5-dione", "1-methoxypiperidine", "N-methoxy-N-methylacetamide", "N-hydroxyacetamide",
  "N-hydroxybenzamide", "N-methoxy-N-methylbenzamide", "nitrosobenzene", "N-methyl-N-nitrosomethanamine", "1-nitrosopiperidine", "4-nitrosophenol",
]);
// Peroxides, hydroperoxides, peroxy acids, esters and anhydrides (P-63.4.2, P-65.1.4, P-65.7.5); mCPBA, Octet's
// reagent list.
must("O-O", [
  "3-chlorobenzenecarboperoxoic acid", "ethaneperoxoic acid", "methaneperoxoic acid", "4-(hydroperoxycarbonyl)benzoic acid",
  "tert-butyl benzenecarboperoxoate", "tert-butyl ethaneperoxoate", "benzoic peroxyanhydride", "acetic peroxyanhydride", "dibenzoyl peroxide",
  "2-methylpropane-2-peroxol", "methaneperoxol", "1-methyl-1-phenylethyl hydroperoxide", "4-hydroperoxybenzoic acid", "4-hydroperoxybutan-1-ol",
  "(tert-butylperoxy)benzene", "2-methyl-2-(methylperoxy)propane", "di-tert-butyl peroxide", "dimethyl peroxide",
]);
// Disulfides and polysulfides (P-63.4.2.2), and N-halo compounds.
must("S-S, N-X", [
  "(methyldisulfanyl)methane", "(methyltrisulfanyl)methane", "diphenyl disulfide", "cystamine", "L-cystine", "4-disulfanylbutanoic acid",
  "1-bromopyrrolidine-2,5-dione", "1-chloropyrrolidine-2,5-dione", "1-iodopyrrolidine-2,5-dione", "N-chloromethanamine", "N-bromoacetamide",
  "N,N-dichloro-4-methylaniline",
]);
// Sulfur oxoacids and their derivatives (P-65.3, P-66.1.1.4, P-67.1.2): sulfonamides, sulfonate esters (busulfan,
// triflates, tosylates), sulfinic acids, sulfonic anhydrides (Tf2O), sulfonyl groups on a ring N, sulfates and
// sulfamates, and R/S at a sulfoxide S.
must("S oxoacids", [
  "methanesulfonamide", "N-methylbenzenesulfonamide", "4-aminobenzene-1-sulfonamide", "N,N-diethylmethanesulfonamide",
  "5-(dimethylamino)naphthalene-1-sulfonamide", "4-sulfamoylbenzoic acid", "4-(dimethylsulfamoyl)benzoic acid", "4-(methanesulfonamido)benzoic acid",
  "4-[(4-methylbenzene-1-sulfonyl)amino]benzoic acid", "1,1,1-trifluoro-N-(trifluoromethanesulfonyl)methanesulfonamide",
  "methyl methanesulfonate", "ethyl 4-methylbenzene-1-sulfonate", "methyl trifluoromethanesulfonate", "busulfan",
  "2-[(methanesulfonyl)oxy]ethyl 4-methylbenzene-1-sulfonate", "methyl [(methanesulfonyl)oxy]acetate", "trifluoromethanesulfonic anhydride",
  "4-methylbenzenesulfonic methanesulfonic anhydride", "ethanesulfinic acid", "2-aminoethane-1-sulfinic acid", "methyl benzenesulfinate",
  "benzenesulfinamide", "benzenesulfinyl chloride", "4-sulfinobenzoic acid", "4-sulfinamoylbenzoic acid", "4-(methoxysulfonyl)benzoic acid",
  "4-(chlorosulfonyl)benzoic acid", "piperidine-1-sulfonic acid", "morpholine-4-sulfonamide", "piperidine-1-sulfonyl chloride",
  "1-(methanesulfonyl)piperidine", "4-[(piperidin-1-yl)sulfonyl]benzoic acid", "dimethyl sulfate", "ethyl hydrogen sulfate", "sulfuric acid",
  "sulfamic acid", "phenylsulfamic acid", "methyl sulfamate", "methyl dimethylsulfamate", "sulfuric diamide", "N,N'-dimethylsulfuric diamide",
  "dimethylsulfamoyl chloride", "methyl sulfurochloridate", "sulfuryl dichloride", "sulfurous dichloride", "dimethyl sulfite",
  "4-(sulfooxy)benzoic acid", "4-(sulfamoyloxy)benzoic acid", "4-[(methoxysulfonyl)oxy]benzoic acid", "4-(sulfoamino)benzoic acid",
  "(S)-(methanesulfinyl)benzene", "1-[(R)-methanesulfinyl]-4-methylbenzene", "L-methionine (S)-S-oxide", "2-[(S)-methanesulfinyl]acetic acid",
]);
// Phosphorus oxoacids and their esters, amides and halides (P-67.1), phosphanium salts, nitrate and nitrite esters.
must("P oxoacids, nitrates", [
  "phosphoric acid", "trimethyl phosphate", "triphenyl phosphate", "ethyl dimethyl phosphate", "dimethyl hydrogen phosphate", "methyl dihydrogen phosphate",
  "pyridoxal 5'-phosphate", "inosinic acid", "O-phospho-L-serine", "methylphosphonic acid", "(2-aminoethyl)phosphonic acid", "diphenylphosphinic acid",
  "methyl hydrogen methylphosphonate", "diethyl (2-oxopropyl)phosphonate", "ethyl (diethoxyphosphoryl)acetate", "trimethyl phosphite",
  "dimethyl methylphosphonite", "methyl diphenylphosphinite", "phosphoryl trichloride", "methylphosphonic dichloride", "diphenylphosphinic chloride",
  "trichlorophosphane", "chloro(diphenyl)phosphane", "dichloro(phenyl)phosphane", "phosphorodichloridic acid", "ethyl phosphorodichloridate",
  "diethyl phosphorochloridate", "propan-2-yl methylphosphonofluoridate", "N,N,N',N',N'',N''-hexamethylphosphoric triamide",
  "N,N,N',N',N'',N''-hexamethylphosphorous triamide", "P,P-diphenylphosphinic amide", "P-methylphosphonic diamide", "phosphoramidic acid",
  "diethyl phosphoramidate", "diethyl N-phenylphosphoramidate", "methyl phosphorodiamidate", "4-phosphonobenzoic acid",
  "4-(dimethoxyphosphoryl)benzoic acid", "4-[hydroxy(methyl)phosphoryl]benzoic acid", "4-(phosphonooxy)benzoic acid",
  "4-[(diethoxyphosphoryl)oxy]benzoic acid", "4-(dimethoxyphosphanyl)benzoic acid", "4-(phosphonoamino)benzoic acid", "coenzyme A",
  "methyl(triphenyl)phosphanium bromide", "tetraphenylphosphanium chloride", "(carboxymethyl)(triphenyl)phosphanium chloride",
  "methyl nitrate", "propane-1,2,3-triyl trinitrate", "ethane-1,2-diyl dinitrate", "2-hydroxypropane-1,3-diyl dinitrate",
  "ethane-1,2-diyl bis(4-methylbenzene-1-sulfonate)", "propane-1,3-diyl bis(trifluoromethanesulfonate)", "ethane-1,2-diyl dibenzenesulfonate",
  "benzene-1,4-diyl dimethanesulfonate", "(2R,3R)-butane-2,3-diyl dimethanesulfonate", "2,2-bis[(nitrooxy)methyl]propane-1,3-diyl dinitrate","4-(nitrooxy)butanoic acid", "3-methylbutyl nitrite", "4-[(nitrosooxy)methyl]benzoic acid",
]);
// N-oxides (P-74.2.1.2), imines on a ring N and imine N atoms cited as prefixes (P-62.3.1.2).
must("N-oxides, imines", [
  "pyridine 1-oxide", "4-methylmorpholine 4-oxide", "N,N-dimethylmethanamine N-oxide", "N-ethyl-N-methylethanamine N-oxide",
  "N,N-dimethylaniline N-oxide", "6-(piperidin-1-yl)pyrimidine-2,4-diamine 3-oxide", "quinoline 1-oxide", "4-nitropyridine 1-oxide",
  "pyridine-4-carboxylic acid 1-oxide", "methyl pyridine-4-carboxylate 1-oxide", "2-methylpyridine 1-oxide", "pyrazine 1,4-dioxide",
  "N-(piperidin-1-yl)ethanimine", "4-(benzylideneamino)benzoic acid", "4-{[(E)-benzylidene]amino}benzoic acid",
  "4-(propan-2-ylideneamino)phenol", "4-(cyclohexylideneamino)benzoic acid", "(2E)-2-(2-phenylhydrazinylidene)propanoic acid",
  "1-phenyl-2-[(E)-1-phenylethylidene]hydrazine",
]);
// Diphosphates and triphosphates, phosphorothioates, isothiocyanates and thiocyanates, ring S-oxides, hypervalent
// iodine and iodanium salts, hypohalites, (dihydroxyamino).
must("more", [
  "diphosphoric acid", "triphosphoric acid", "methyl trihydrogen diphosphate", "tetraethyl diphosphate", "3-methylbut-3-en-1-yl trihydrogen diphosphate",
  "adenosine 5'-diphosphate", "adenosine 5'-triphosphate", "O,O-diethyl O-(4-nitrophenyl) phosphorothioate", "O,O,O-trimethyl phosphorothioate",
  "O,O,S-trimethyl phosphorodithioate", "4-[(dimethoxyphosphorothioyl)sulfanyl]butanoic acid", "diazinon", "isothiocyanatobenzene",
  "isothiocyanatomethane", "4-isothiocyanatobenzoic acid", "1-isothiocyanato-4-methylbenzene", "thiocyanatobenzene", "4-thiocyanatobenzoic acid",
  "isocyanatobenzene", "cyanatobenzene", "thiolane 1,1-dioxide", "thiolane 1-oxide", "thiophene 1-oxide", "4-methylthiane 1,1-dioxide",
  "thiolane-3-carboxylic acid 1,1-dioxide", "3-(1,1-dioxo-1λ6-thiolan-3-yl)propanoic acid", "4-(1-oxo-1λ4-thian-4-yl)benzoic acid",
  "N-(1,1-dioxo-1λ6-thiolan-3-yl)acetamide", "biotin sulfone","[bis(acetyloxy)-λ3-iodanyl]benzene", "[bis(trifluoroacetyloxy)iodo]benzene", "(dichloro-λ3-iodanyl)benzene",
  "iodosylbenzene", "iodylbenzene", "4-iodosylbenzoic acid", "diphenyliodanium chloride", "methyl hypochlorite", "tert-butyl hypochlorite",
  "4-(chlorooxy)butanoic acid", "4-(dihydroxyamino)benzoic acid", "alanosine",
]);
// Sulfanium and sulfoxonium salts, phosphorus ylides (Wittig reagents).
must("onium, ylides", [
  "trimethylsulfanium iodide", "trimethylsulfoxonium iodide", "dimethyl(phenyl)sulfanium bromide", "(triphenyl-λ5-phosphanylidene)methane",
  "ethyl (triphenyl-λ5-phosphanylidene)acetate", "1-(triphenyl-λ5-phosphanylidene)propan-2-one", "(cyclohexylidene)(triphenyl)-λ5-phosphane",
  "triphenyl(propan-2-ylidene)-λ5-phosphane", "4-(triphenyl-λ5-phosphanylidene)butanoic acid",
]);
// Sulfonyl azides and phosphorazidates, triazenes, phosphane sulfides, N-nitroso and N-amino sulfonamides.
must("azides, triazenes", [
  "4-methylbenzene-1-sulfonyl azide", "methanesulfonyl azide", "4-acetamidobenzenesulfonyl azide", "4-(azidosulfonyl)benzoic acid",
  "diphenyl phosphorazidate", "3,3-dimethyl-1-phenyltriaz-1-ene", "(1E)-3,3-dimethyl-1-phenyltriaz-1-ene", "4-[(1E)-3,3-dimethyltriaz-1-en-1-yl]benzoic acid",
  "5-[(1E)-3,3-dimethyltriaz-1-en-1-yl]-1H-imidazole-4-carboxamide", "triphenylphosphane sulfide", "4-(diphenylphosphorothioyl)benzoic acid",
  "N-methyl-N-nitroso-4-methylbenzene-1-sulfonamide", "4-methylbenzene-1-sulfonohydrazide", "N'-(propan-2-ylidene)-4-methylbenzene-1-sulfonohydrazide",
  "2-hydroxy-5-[(E)-{4-[(pyridin-2-yl)sulfamoyl]phenyl}diazenyl]benzoic acid",
]);
// Thiosulfonates, sulfenyl groups, N-fluoro sulfonimides (NFSI), phosphoramidites as prefixes.
must("sulfenyl, thiosulfonates", [
  "S-methyl methanesulfonothioate", "allicin", "4-[(methylsulfanyl)sulfonyl]benzoic acid", "1-chloro-4-(chlorosulfanyl)benzene",
  "benzenesulfenyl chloride", "N-(phenylsulfanyl)phthalimide", "N-(phenylsulfanyl)aniline", "4-(hydroxysulfanyl)benzoic acid",
  "(methoxysulfanyl)benzene", "1-(phenylsulfanyl)piperidine", "N-(benzenesulfonyl)-N-fluorobenzenesulfonamide",
  "3-{[bis(diisopropylamino)phosphanyl]oxy}propanenitrile", "2-cyanoethyl N,N-diisopropylchlorophosphoramidite",
  "(R)-2-methylpropane-2-sulfinamide", "(S)-2-methylpropane-2-sulfinamide", "(S)-4-methylbenzene-1-sulfinamide",
  "(R)-N-[(E)-benzylidene]-2-methylpropane-2-sulfinamide", "N-benzylidene-2-methylpropane-2-sulfinamide",
  "methyl (R)-4-methylbenzene-1-sulfinate", "methyl (S)-4-methylbenzene-1-sulfinate", "smiles:CCO[S@@](=O)C",
  "smiles:Cc1ccc(cc1)[S@@](=O)O[C@@H]1C[C@H](C)CC[C@H]1C(C)C",
  "N-(benzenesulfonyl)acetamide", "N-(4-methylbenzene-1-sulfonyl)benzamide", "N-(methanesulfonyl)-4-nitrobenzamide",
]);
// Hydrogen drawn as atoms, as in Sam's ChemDraw files (his mCPBA is drawn with its peroxy H).
must("drawn H", [
  "smiles:C(OO[H])(=O)C1=CC=CC(Cl)=C1", "smiles:OO[H]", "smiles:C([H])(=O)C", "smiles:[C@]1([H])(C2C=CC=CC=2)CCCC[C@@]1([H])O",
  "smiles:C1([H])OC1(C)C1=CC=CC=C1",
]);
// Small molecules with no carbon (IUPAC 2005, IR-6, IR-8). Single atoms (water, HCl) are not named: a lone atom
// drawn is ambiguous.
must("inorganic", [
  "hydrogen peroxide", "disulfane", "dichlorine", "dibromine", "diiodine", "difluorine", "dinitrogen", "dioxygen", "ozone", "nitrous oxide",
  "hydrazoic acid", "hypochlorous acid", "chlorous acid", "chloric acid", "perchloric acid", "hypobromous acid", "bromic acid", "perbromic acid",
  "hypoiodous acid", "iodic acid", "periodic acid", "orthoperiodic acid", "nitrous acid", "nitric acid", "nitrosyl chloride", "chloramine",
  "dichloramine", "nitrogen trichloride", "nitrogen trifluoride", "sulfur dioxide", "sulfur trioxide", "phosphorus pentachloride",
  "hydroxylamine", "hydrazine", "sulfuric acid", "phosphoric acid", "phosphoryl trichloride", "trichlorophosphane", "sulfurous dichloride",
  "sulfoxylic acid", "peroxomonosulfuric acid", "dithionic acid", "trithionic acid", "tetrathionic acid", "hypodiphosphoric acid",
  "nitrous amide", "amidosulfurous acid", "pentathionic acid", "disulfuric acid", "trisulfuric acid", "sulfenamic acid", "phosphenic acid",
]);
