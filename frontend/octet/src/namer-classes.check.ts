// Run: node src/namer-classes.check.ts. Functional classes built on carbon (P-65, P-66, P-68): esters of polyacids and
// polyols, carbonic acid and its derivatives, amidines and guanidines, imides, hydrazides, hydroxamic acids, ketenes
// and cyanides. Each name becomes a structure (OPSIN), Octet names the structure, and OPSIN must read Octet's name
// back as the same structure (same standard InChI). Where the name itself matters, it must be the one given.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-classes.check: skipped (no OPSIN build)"); process.exit(0); }
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

// Each entry: a name (or "smiles:…") OPSIN reads, and the name Octet must give, when it differs from the input.
// Octet's name must read back as the same structure.
function check(label: string, cases: (string | [string, string])[]) {
  const out: string[] = [];
  for (const c of cases) {
    const [input, want] = typeof c === "string" ? [c, c] : c;
    const smiles = input.startsWith("smiles:") ? input.slice(7) : opsin.parseToSmiles(input);
    assert.ok(smiles, `OPSIN reads ${input}`);
    const g = graphOf(molOf(smiles), cipOf(smiles));
    assert.ok(g, `graph for ${input}`);
    const r = iupacNameWhy(g);
    assert.ok(r.name, `no name for ${input} (${smiles}): ${r.why}`);
    const back = opsin.parseToSmiles(r.name);
    assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${input} -> ${r.name}, a different structure`);
    if (!want.startsWith("smiles:")) assert.equal(r.name, want, `${input}`);
    out.push(r.name);
  }
  console.log(`namer-classes.check: ${label} ${out.length}/${cases.length}`);
}

// A carbonyl, ester, amide or nitrile carbon on a ring N names the ring as the parent (P-65.1.2.2, P-66.1.1.4.3), and
// a ketone on a ring N is a ketone (P-64.1.2): piperidine-1-carboxylic acid, 1-(piperidin-1-yl)ethan-1-one.
check("ring N", [
  "piperidine-1-carboxylic acid", "piperidine-1-carbaldehyde", "morpholine-4-carbaldehyde", "1H-indole-1-carbaldehyde",
  "tert-butyl 3-hydroxy-3-methylazetidine-1-carboxylate", "piperidine-1-carbonyl chloride", "N,N-dimethylpiperidine-1-carboxamide",
  "N-phenylpiperidine-1-carboxamide", "piperidine-1-carbonitrile", "1-acetylpiperidine-4-carboxylic acid", "1-carbamoylpiperidine-4-carboxylic acid",
  "4-(piperidine-1-carbonyl)benzoic acid", ["1-(piperidin-1-yl)ethan-1-one", "1-(piperidin-1-yl)ethan-1-one"], "phenyl(pyrrolidin-1-yl)methanone",
  ["di(1H-imidazol-1-yl)methanone", "bis(1H-imidazol-1-yl)methanone"], "1-acetylpyrrolidin-2-one",
  ["2-[(piperidine-1-carbonyl)oxy]acetic acid", "[(piperidine-1-carbonyl)oxy]acetic acid"],
  // Sam's Boc-protected azetidine (corpus).
  ["smiles:C1(O)(C)CN(C(OC(C)(C)C)=O)C1", "tert-butyl 3-hydroxy-3-methylazetidine-1-carboxylate"],
]);

// Several esters (P-65.6.3.2): of a polyacid, alkyl groups in alphanumerical order with locants when they differ; of a
// polyol with one acid, the polyol's "diyl" name; other esters as acyloxy and alkoxy-oxo prefixes (P-65.6.3.3).
check("esters", [
  // Sam's dimethyl diazomalonate.
  ["dimethyl diazopropanedioate", "dimethyl diazopropanedioate"], "diethyl propanedioate", "diethyl butanedioate", "dimethyl ethanedioate",
  ["ethyl methyl butanedioate", "1-ethyl 4-methyl butanedioate"], "1-ethyl 4-methyl 2-hydroxybutanedioate", "4-ethyl 1-methyl 2-hydroxybutanedioate",
  "dimethyl (2R,3R)-2,3-dihydroxybutanedioate", "dimethyl benzene-1,4-dicarboxylate", "di-tert-butyl butanedioate",
  "3-ethyl 5-methyl 2,6-dimethylpyridine-3,5-dicarboxylate", ["triacetin", "propane-1,2,3-triyl triacetate"], "ethane-1,2-diyl diacetate",
  ["benzene-1,4-diyl diacetate", "1,4-phenylene diacetate"], "(2R)-propane-1,2-diyl diacetate", ["tristearin", "propane-1,2,3-triyl trioctadecanoate"],
  ["triolein", "propane-1,2,3-triyl tris[(9Z)-octadec-9-enoate]"], "ethane-1,2-diyl bis(2-methylprop-2-enoate)",
  "methyl 4-(acetyloxy)benzoate", "4-methoxy-4-oxobutanoic acid", "2-(acetyloxy)ethyl propanoate", "methyl [(tert-butoxycarbonyl)amino]acetate",
  "methyl (1R,2R,3S,5S)-3-(benzoyloxy)-8-methyl-8-azabicyclo[3.2.1]octane-2-carboxylate", ["methyl 3,4-diacetoxybenzoate", "methyl 3,4-bis(acetyloxy)benzoate"],
]);

// Carbonic acid and its derivatives (P-65.2.1, P-65.5.1, P-66.1.6), as the compound and as prefixes; imides
// (P-66.2.1.1) as N-acyl amides.
check("carbonic", [
  "carbonic acid", "carbamic acid", ["phenylcarbamic acid", "N-phenylcarbamic acid"], "N,N-dimethylcarbamic acid", "carbonochloridic acid",
  "dimethyl carbonate", "ethyl methyl carbonate", "diphenyl carbonate", ["triphosgene", "bis(trichloromethyl) carbonate"], "methyl hydrogen carbonate",
  "ethyl carbonochloridate", ["diphosgene", "trichloromethyl carbonochloridate"], ["phosgene", "carbonyl dichloride"], "carbonyl difluoride",
  "carbamoyl chloride", ["dimethylcarbamoyl chloride", "N,N-dimethylcarbamoyl chloride"], "di-tert-butyl dicarbonate", "dicarbonic acid",
  "N-cyclohexyl-N'-phenylurea", ["biuret", "carbamoylurea"], ["triuret", "N,N'-dicarbamoylurea"], ["allophanic acid", "N-carbamoylcarbamic acid"],
  ["smiles:CCCC(C)(COC(N)=O)COC(N)=O", "2-methyl-2-propylpropane-1,3-diyl dicarbamate"], ["smiles:CNC(=O)Oc1cccc2ccccc12", "naphthalen-1-yl N-methylcarbamate"],
  ["smiles:CC(C)(C)OC(=O)NCCNC(=O)OC(C)(C)C", "tert-butyl N-{2-[(tert-butoxycarbonyl)amino]ethyl}carbamate"],
  ["smiles:ClC(=O)OCC1c2ccccc2-c2ccccc12", "(9H-fluoren-9-yl)methyl carbonochloridate"],
  ["smiles:CC(C)(C)OC(=O)N1CCC(CC1)C(=O)O", "1-(tert-butoxycarbonyl)piperidine-4-carboxylic acid"],
  ["citrulline", "(2S)-2-amino-5-(carbamoylamino)pentanoic acid"], ["isatoic acid", "2-(carboxyamino)benzoic acid"], "(carbamoylamino)acetic acid",
  "4-[(methoxycarbonyl)oxy]benzoic acid", "4-[(dimethylcarbamoyl)oxy]benzoic acid", "4-(chlorocarbonyl)benzoic acid", "4-chloro-4-oxobutanoic acid",
  "4-[(chlorocarbonyl)amino]benzoic acid", ["oxaluric acid", "(carbamoylamino)(oxo)acetic acid"],
  "N-acetylacetamide", "N,N-diacetylacetamide", "N-benzoylbenzamide", ["acetylurea", "N-carbamoylacetamide"], ["tert-butyl acetylcarbamate", "tert-butyl N-acetylcarbamate"],
  "4-(diacetylamino)benzoic acid", "4-[acetyl(methyl)amino]benzoic acid",
]);

// Amidines (P-66.4.1.1), guanidines (P-66.4.1.2.1) and carbodiimides; isocyanates, cyanates, cyanamides and
// carbononitridic halides (P-66.5.1.1); ketenes (P-64.1.1).
check("imines", [
  "methanimidamide", "ethanimidamide", "N-methylethanimidamide", "N'-methylethanimidamide", "N,N-dimethylmethanimidamide", "N'-hydroxyethanimidamide",
  "benzenecarboximidamide", "piperidine-1-carboximidamide", "4-carbamimidoylbenzoic acid", "3-amino-3-iminopropanoic acid",
  "guanidine", "N-methylguanidine", "N''-methylguanidine", "N,N-dimethylguanidine", "N,N'-dimethylguanidine", ["agmatine", "N-(4-aminobutyl)guanidine"],
  ["arginine", "(2S)-2-amino-5-carbamimidamidopentanoic acid"], ["smiles:NC(N)=NCCC[C@H](N)C(O)=O", "(2S)-2-amino-5-[(diaminomethylidene)amino]pentanoic acid"],
  ["creatine", "[carbamimidoyl(methyl)amino]acetic acid"], ["biguanide", "N-carbamimidoylguanidine"],
  ["smiles:CN(C)C(=N)NC(=N)N", "N'-carbamimidoyl-N,N-dimethylguanidine"], // metformin
  "methanediimine", "N,N'-dicyclohexylmethanediimine", "3-{[(ethylimino)methylidene]amino}-N,N-dimethylpropan-1-amine",
  "isocyanic acid", "isocyanatobenzene", "isothiocyanatomethane", "1,6-diisocyanatohexane", "2,4-diisocyanato-1-methylbenzene",
  ["allyl isothiocyanate", "3-isothiocyanatoprop-1-ene"], "cyanatobenzene", "thiocyanatobenzene", "cyanic acid",
  "cyanamide", "N,N-dimethylcyanamide", "(cyanoamino)acetic acid", ["cyanogen bromide", "carbononitridic bromide"], "carbononitridic chloride",
  "ethenone", ["2-phenylethen-1-one", "phenylethenone"], ["dimethylketene", "2-methylprop-1-en-1-one"],
  // Prefixes without locants: brackets after the first.
  ["bromochloromethane", "bromo(chloro)methane"], ["mandelic acid", "hydroxy(phenyl)acetic acid"],
]);

// Hydrazides (P-66.3.1) and hydroxamic acids (N-hydroxy amides), Weinreb amides, hydroxyurea.
check("hydrazides", [
  "acetohydrazide", "benzohydrazide", "propanehydrazide", "formohydrazide", "butanedihydrazide", "N'-phenylacetohydrazide", "N-methylacetohydrazide",
  "N',N'-dimethylbenzohydrazide", "pyridine-4-carbohydrazide", "N'-acetylacetohydrazide", "4-(hydrazinecarbonyl)benzoic acid",
  "4-(2-acetylhydrazinyl)benzoic acid", ["semioxamazide", "2-hydrazinyl-2-oxoacetamide"],
  ["agaritine", "(2S)-2-amino-5-{2-[4-(hydroxymethyl)phenyl]hydrazinyl}-5-oxopentanoic acid"],
  "N-hydroxyacetamide", "N-hydroxybenzamide", "N-hydroxy-N-phenylacetamide", "N-methoxy-N-methylbenzamide", "hydroxyurea", "N,N'-dihydroxyurea",
  "tert-butyl N-hydroxycarbamate", ["smiles:ONC(=O)CCCCCCC(=O)Nc1ccccc1", "N1-hydroxy-N8-phenyloctanediamide"], // vorinostat
]);
check("ring acyl", [["dibenzamide", "N-benzoylbenzamide"], ["tribenzamide", "N,N-dibenzoylbenzamide"], "1H-pyrrole-2-carbonyl chloride",
  ["smiles:O=C(c1ccc[nH]1)NCC(=O)O", "[(1H-pyrrole-2-carbonyl)amino]acetic acid"]]);

// Imidic acids, imidates and imidoyl halides (P-65.1.3.1); isoureas and other imidic carbonic acid derivatives
// (P-65.2.1.2); N-hydroxy guanidines and amidoximes; esters on a ring N (N-hydroxysuccinimide esters).
check("imidic", [
  "ethanimidic acid", "methanimidic acid", "benzenecarboximidic acid", "methyl ethanimidate", "methyl N-phenylethanimidate",
  "methyl 2,2,2-trichloroethanimidate", "N-phenylethanimidoyl chloride", "N-phenylbenzenecarboximidoyl chloride",
  ["isourea", "carbamimidic acid"], "methyl carbamimidate", "methyl N,N'-dicyclohexylcarbamimidate", "N-phenylcarbonimidoyl dichloride",
  "dimethyl carbonimidate", "carbamimidoyl chloride", "N-hydroxyguanidine", "N'-hydroxybenzenecarboximidamide",
  ["canavanine", "(2S)-2-amino-4-(carbamimidamidooxy)butanoic acid"], "N-methylcyclohexanecarboxamide",
  "2,5-dioxopyrrolidin-1-yl acetate", "bis(2,5-dioxopyrrolidin-1-yl) carbonate", "2,5-dioxopyrrolidin-1-yl 4-azidobenzoate",
]);

// Carboxylic acid groups on a hydrazine or diazene N take it as the parent (P-68.3.1.1.1): semicarbazide, carbazates,
// DEAD, DIAD and TMAD.
check("hydrazine", [
  ["semicarbazide", "hydrazinecarboxamide"], ["carbazic acid", "hydrazinecarboxylic acid"], "tert-butyl hydrazinecarboxylate",
  "hydrazinecarbonyl chloride", "2-phenylhydrazine-1-carboxamide", "N-phenylhydrazinecarboxamide", "2,2-dimethylhydrazine-1-carboxamide",
  ["biurea", "hydrazine-1,2-dicarboxamide"], "hydrazine-1,2-dicarboxylic acid", "ethyl 2-acetylhydrazine-1-carboxylate",
  "diethyl diazene-1,2-dicarboxylate", ["smiles:CCOC(=O)/N=N/C(=O)OCC", "diethyl (E)-diazene-1,2-dicarboxylate"],
  ["dipropan-2-yl (E)-diazene-1,2-dicarboxylate", "bis(propan-2-yl) (E)-diazene-1,2-dicarboxylate"],
  ["N,N,N',N'-tetramethyldiazene-1,2-dicarboxamide", "N1,N1,N2,N2-tetramethyldiazene-1,2-dicarboxamide"],
]);

// Nitriles as prefixes: the C of a cyano group is never in the chain unless the chain is the nitrile (P-66.5.1.2).
// Substituted methoxy to phenoxy keep their short forms (P-63.2.2.2); an amide's N counts as a position (P-14.3.4).
check("prefixes", [
  "cyanoacetic acid", "ethyl cyanoacetate", "3-cyanopropanoic acid", "2-cyanoethyl acetate", "2-cyano-2-methylpropanoic acid",
  "ethyl cyanoformate", "2-hydroxy-2-methylpropanenitrile", "3-(2-cyanoethoxy)propanoic acid", "butanedinitrile",
  ["smiles:OC(=O)CNC(=O)OCC1c2ccccc2-c2ccccc12", "({[(9H-fluoren-9-yl)methoxy]carbonyl}amino)acetic acid"],
  ["smiles:CCN(CC)CC(=O)Nc1c(C)cccc1C", "2-(diethylamino)-N-(2,6-dimethylphenyl)acetamide"], ["smiles:ClCC(=O)NC", "2-chloro-N-methylacetamide"],
  ["smiles:NC(=N)NC(=O)Cc1c(Cl)cccc1Cl", "N-carbamimidoyl-2-(2,6-dichlorophenyl)acetamide"], // guanfacine
  ["N-acetyl-L-cysteine", "(2R)-2-acetamido-3-sulfanylpropanoic acid"], ["hippuric acid", "benzamidoacetic acid"],
  ["thyroxine", "(2S)-2-amino-3-[4-(4-hydroxy-3,5-diiodophenoxy)-3,5-diiodophenyl]propanoic acid"],
]);

// Enclosing marks nest {[({[( )]})]} (P-16.5.4). Fusion, von Baeyer and ring assembly brackets do not count; a mark
// next to one of its own level takes the next level (P-16.5.4.1.5).
check("brackets", [
  "(3S)-2-[(2S)-2-{[(2S)-1-ethoxy-1-oxo-4-phenylbutan-2-yl]amino}propanoyl]-1,2,3,4-tetrahydroisoquinoline-3-carboxylic acid",
  "(7,7-dimethyl-2-oxobicyclo[2.2.1]heptan-1-yl)methanesulfonic acid", "N-(dibenzo[b,d]furan-1-yl)acetamide",
  ["smiles:N#Cc1ccc(cc1)-c1ccc(OCCCCCO)cc1", "4'-[(5-hydroxypentyl)oxy][1,1'-biphenyl]-4-carbonitrile"],
]);

// Locants are left out only where nothing else could be meant (P-14.3.4, P-31.1.4.2.4): Blue Book examples.
check("locants", [
  "chloromethane", "ethanol", "chloroethane", "chloroethene", "propene", "propyne", "propan-2-one", "butan-2-one",
  "prop-2-enoic acid", "prop-2-ynoic acid", "propa-1,2-diene", "cyclohexanethiol", "bromobenzene", "pyrazinecarboxylic acid",
  "methylurea", "tetrafluorourea", "chloropropanedioic acid", "chlorobutanedioic acid", "2-methylpropanediamide",
  "N1,N3-dimethylpropanediamide", "difluoroacetic acid", "heptafluorobutanoic acid", "2,2,3,3,3-pentafluoropropan-1-ol",
  "hexachlorobenzene", "1-chloro-2-(pentafluoroethyl)benzene", "decahydronaphthalene", "diphenylethenone",
  ["smiles:CC(=O)c1ccccc1", "1-phenylethan-1-one"], ["smiles:CC(=O)c1ccccn1", "1-(pyridin-2-yl)ethan-1-one"],
  ["smiles:OCCCl", "2-chloroethan-1-ol"], ["smiles:ClCC(N)=O", "2-chloroacetamide"], ["smiles:NCCS(O)(=O)=O", "2-aminoethane-1-sulfonic acid"],
]);

// Benzyl and benzylidene are the preferred prefixes when not substituted (P-29.6.1).
check("benzyl", [
  "2-benzylpyridine", "2-[(4-bromophenyl)methyl]pyridine", "benzyl acetate", "benzyl carbamate", "N-benzylaniline", "4-(benzyloxy)phenol",
  "2-benzylidenecyclohexan-1-one", "(1-chloroethyl)benzene", ["smiles:O=C1OC[C@H](Cc2ccccc2)N1", "(4S)-4-benzyl-1,3-oxazolidin-2-one"],
  ["smiles:C[S@@](=O)OCc1ccccc1", "benzyl (S)-methanesulfinate"], "(R)-N-[(E)-benzylidene]-2-methylpropane-2-sulfinamide",
]);

// N-cyano guanidines and amidines (cimetidine); acid pseudohalides (P-65.5.3).
check("cyano and pseudohalides", [
  "N-cyanoguanidine", ["smiles:N#CN=C(N)N", "N''-cyanoguanidine"], "N'-cyano-N,N-dimethylmethanimidamide",
  ["smiles:CC1=C(N=CN1)CSCCNC(=NC)NC#N", "smiles:"], // cimetidine
  "benzoyl isothiocyanate", "acetyl isocyanate", "benzoyl cyanate", "benzoyl thiocyanate", "butanedioyl diisocyanate", "4-(isothiocyanatocarbonyl)benzoic acid",
]);

// Anhydrides as prefixes, and alkoxycarbonyl prefixes with their brackets: [(benzyloxy)carbonyl] (P-65.7.7, P-65.6.3.3).
check("anhydride prefixes", [
  "2-[(acetyloxy)carbonyl]benzoic acid", "4-[(benzoyloxy)carbonyl]benzoic acid", ["smiles:CC(=O)OC(=O)CC(O)=O", "3-(acetyloxy)-3-oxopropanoic acid"],
  "acetic benzoic anhydride", "4-methylbenzoic anhydride", "4-[(benzyloxy)carbonyl]benzoic acid",
  ["smiles:C[C@H](NC(=O)OCc1ccccc1)C(O)=O", "(2S)-2-{[(benzyloxy)carbonyl]amino}propanoic acid"],
]);

// More than two carboxylic groups on a chain: all as "carbo…" suffixes on the chain without them (P-65.1.2.2.2).
check("tricarboxylic", [
  ["citric acid", "2-hydroxypropane-1,2,3-tricarboxylic acid"], "triethyl 2-hydroxypropane-1,2,3-tricarboxylate", "propane-1,2,3-tricarboxylic acid",
  "butane-1,2,4-tricarboxylic acid", "methanetricarboxylic acid", "triethyl methanetricarboxylate", "propane-1,2,3-tricarbonitrile",
  ["aconitic acid", "prop-1-ene-1,2,3-tricarboxylic acid"], "butanedioic acid", "methylbutanedioic acid",
]);

// N-acyl lactams; a substituted acetyl group needs no locant (phenylacetyl). Sam's
// 3-(phenylacetyl)-4-phenyl-1,3-oxazolidin-2-one waits only for the 1,3-oxazolidine ring; its pyrrolidinone analogue:
check("acetyl", [
  ["smiles:O=C1CC[C@H](c2ccccc2)N1C(=O)Cc1ccccc1", "(5R)-5-phenyl-1-(phenylacetyl)pyrrolidin-2-one"],
  ["smiles:ClCC(=O)Oc1ccccc1C(O)=O", "2-[(chloroacetyl)oxy]benzoic acid"], ["smiles:O=C(C(Cl)Cl)Nc1ccccc1", "2,2-dichloro-N-phenylacetamide"],
]);

// Peroxy acids, their esters and diacyl peroxides (P-65.1.4): mCPBA, peracetic acid, BPO.
check("peroxy", [
  ["peracetic acid", "ethaneperoxoic acid"], "benzenecarboperoxoic acid", ["3-chlorobenzenecarboperoxoic acid", "3-chlorobenzene-1-carboperoxoic acid"],
  "methaneperoxoic acid", "tert-butyl benzenecarboperoxoate", "tert-butyl ethaneperoxoate", "dibenzoyl peroxide", "diacetyl peroxide",
  "acetyl benzoyl peroxide", "bis(3,5,5-trimethylhexanoyl) peroxide",
]);

// N-hydroxy lactams and imides (cyclic hydroxamic acids).
check("N-hydroxy imides", ["1-hydroxypyrrolidine-2,5-dione", "1-hydroxypyrrolidin-2-one", "1-methoxypiperidin-2-one", ["isatinol", "1-hydroxy-1H-indole-2,3-dione"]]);
check("nitro acyl, carbohydrazide", ["1-nitropropan-1-one", "nitro(phenyl)methanone", "4-nitro-4-oxobutanoic acid", ["carbohydrazide", "carbonic dihydrazide"]]);

// Carboxy, not 2-hydroxy-2-oxoethyl; bis for compound prefixes; stereodescriptors ignored in alphanumerical order.
check("carboxy prefixes", [
  ["smiles:OC(=O)CN(CC(=O)O)CC(=O)O", "2,2',2''-nitrilotriacetic acid"], ["diglycolic acid", "2,2'-oxydiacetic acid"],
  ["phthalonic acid", "2-(carboxycarbonyl)benzoic acid"], ["cystathionine", "(2S)-2-amino-4-{[(2R)-2-amino-2-carboxyethyl]sulfanyl}butanoic acid"],
  "4-[(2-chloroethyl)(methyl)amino]benzoic acid", ["triethanolamine", "2,2',2''-nitrilotri(ethan-1-ol)"],
]);
check("C=N stereo", [["smiles:C/C(=N/O)/N", "(1Z)-N'-hydroxyethanimidamide"], ["smiles:CCO/C(C)=N/c1ccccc1", "ethyl (1E)-N-phenylethanimidate"],
  ["smiles:CC/C(Cl)=N/c1ccccc1", "(1Z)-N-phenylpropanimidoyl chloride"]]);
