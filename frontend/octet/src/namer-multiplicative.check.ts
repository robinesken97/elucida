// Run: node src/namer-multiplicative.check.ts [--names]. Multiplicative names (IUPAC 2013, P-15.3, P-51.3): identical
// parents joined by a multiplying group are named once, multiplied. Each input (a name OPSIN reads, or smiles:...)
// becomes a structure; Octet names it, and OPSIN must read the name back as the same structure (same standard InChI).
// Every case must give the name shown, multiplicative or (where the rules keep it) substitutive.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-multiplicative.check: skipped (no OPSIN build)"); process.exit(0); }
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

// Input (a name OPSIN reads, or smiles:...) and the name Octet must give.
const cases: [string, string][] = [
  // Chains with a principal group, joined by heteroatoms (P-15.3.1.1 (c), (d)).
  ["diethylene glycol", "2,2'-oxydi(ethan-1-ol)"], ["triethylene glycol", "2,2'-[ethane-1,2-diylbis(oxy)]di(ethan-1-ol)"],
  ["smiles:OCCOCCOCCOCCOCCO", "2,2'-[ethane-1,2-diylbis(oxyethane-2,1-diyloxy)]di(ethan-1-ol)"], ["diglycolic acid", "2,2'-oxydiacetic acid"],
  ["smiles:OC(=O)COCCOCCOCC(O)=O", "2,2'-[oxybis(ethane-2,1-diyloxy)]diacetic acid"], ["smiles:OCCSCCO", "2,2'-sulfanediyldi(ethan-1-ol)"],
  ["smiles:SCCOCCS", "2,2'-oxydi(ethane-1-thiol)"], ["smiles:NCCOCCOCCN", "2,2'-[ethane-1,2-diylbis(oxy)]di(ethan-1-amine)"],
  ["smiles:N#CCCOCCC#N", "3,3'-oxydipropanenitrile"], ["smiles:NC(=O)COCC(N)=O", "2,2'-oxydiacetamide"], ["smiles:CC(=O)CCOCCC(C)=O", "4,4'-oxydi(butan-2-one)"],
  ["smiles:CC(O)COCC(C)O", "1,1'-oxydi(propan-2-ol)"], ["smiles:CC(CO)OC(C)CO", "2,2'-oxydi(propan-1-ol)"], ["smiles:OCC(O)COCC(O)CO", "3,3'-oxydi(propane-1,2-diol)"],
  ["smiles:CN(C)C(=O)CCSCCC(=O)N(C)C", "3,3'-sulfanediylbis(N,N-dimethylpropanamide)"], ["smiles:OC(=O)CCSCCSCCC(O)=O", "3,3'-[ethane-1,2-diylbis(sulfanediyl)]dipropanoic acid"],
  ["cystamine", "2,2'-disulfanediyldi(ethan-1-amine)"], ["smiles:OC(=O)C(Cl)OC(Cl)C(O)=O", "2,2'-oxybis(2-chloroacetic acid)"],
  // N as the multiplying group: azanediyl, substituted azanediyl, nitrilo; ethane-1,2-diyldinitrilo (EDTA).
  ["diethanolamine", "2,2'-azanediyldi(ethan-1-ol)"], ["triethanolamine", "2,2',2''-nitrilotri(ethan-1-ol)"], ["smiles:OCCN(C)CCO", "2,2'-(methylazanediyl)di(ethan-1-ol)"],
  ["smiles:OC(=O)CNCC(O)=O", "2,2'-azanediyldiacetic acid"], ["smiles:OC(=O)CN(CC(O)=O)CC(O)=O", "2,2',2''-nitrilotriacetic acid"],
  ["smiles:OC(=O)CN(CC(O)=O)CCN(CC(O)=O)CC(O)=O", "2,2',2'',2'''-(ethane-1,2-diyldinitrilo)tetraacetic acid"],
  ["smiles:OCCN(CCC(O)=O)CCC(O)=O", "3,3'-[(2-hydroxyethyl)azanediyl]dipropanoic acid"], ["smiles:OCCNCCNCCO", "2,2'-[ethane-1,2-diylbis(azanediyl)]di(ethan-1-ol)"],
  // Rings as units, with or without a principal group (P-15.3.1.1 (a)): methylene, oxy, sulfonyl, carbonyl and the rest.
  ["smiles:Nc1ccc(Cc2ccc(N)cc2)cc1", "4,4'-methylenedianiline"], ["smiles:Oc1ccc(Oc2ccc(O)cc2)cc1", "4,4'-oxydiphenol"],
  ["smiles:Nc1ccc(S(=O)(=O)c2ccc(N)cc2)cc1", "4,4'-sulfonyldianiline"], ["bisphenol A", "4,4'-(propane-2,2-diyl)diphenol"],
  ["smiles:OC(=O)c1ccccc1SSc1ccccc1C(O)=O", "2,2'-disulfanediyldibenzoic acid"], ["smiles:CC(=O)c1ccc(C(C)=O)cc1", "1,1'-(1,4-phenylene)di(ethan-1-one)"],
  ["diphenylmethane", "1,1'-methylenedibenzene"], ["diphenyl ether", "1,1'-oxydibenzene"], ["triphenylmethane", "1,1',1''-methanetriyltribenzene"],
  ["bibenzyl", "1,1'-(ethane-1,2-diyl)dibenzene"], ["smiles:c1ccccc1Sc1ccccc1", "1,1'-sulfanediyldibenzene"], ["smiles:c1ccccc1SSc1ccccc1", "1,1'-disulfanediyldibenzene"],
  ["smiles:O=S(c1ccccc1)c1ccccc1", "1,1'-sulfinyldibenzene"], ["smiles:O=S(=O)(c1ccccc1)c1ccccc1", "1,1'-sulfonyldibenzene"], ["smiles:C1CCCCC1OC1CCCCC1", "1,1'-oxydicyclohexane"],
  ["smiles:OC(=O)c1ccc(cc1)C(=O)c1ccc(cc1)C(O)=O", "4,4'-carbonyldibenzoic acid"], ["smiles:OC(=O)c1ccc(cc1)CC(=O)Cc1ccc(cc1)C(O)=O", "4,4'-(2-oxopropane-1,3-diyl)dibenzoic acid"],
  ["smiles:Oc1ccc(S(=O)(=O)c2ccc(O)cc2)cc1", "4,4'-sulfonyldiphenol"], ["smiles:OC(=O)c1ccc(OOc2ccc(C(O)=O)cc2)cc1", "4,4'-peroxydibenzoic acid"],
  ["smiles:Oc1ccc([Se][Se]c2ccc(O)cc2)cc1", "4,4'-diselanediyldiphenol"], ["smiles:Oc1ccc(Nc2ccc(O)cc2)cc1", "4,4'-azanediyldiphenol"],
  ["smiles:Oc1ccc(N(c3ccccc3)c2ccc(O)cc2)cc1", "4,4'-(phenylazanediyl)diphenol"], ["smiles:Oc1ccc(N(c3ccc(O)cc3)c2ccc(O)cc2)cc1", "4,4',4''-nitrilotriphenol"],
  ["smiles:C[Si](C)(c1ccc(O)cc1)c1ccc(O)cc1", "4,4'-(dimethylsilanediyl)diphenol"], ["smiles:O=Cc1ccc(Oc2ccc(C=O)cc2)cc1", "4,4'-oxydibenzaldehyde"],
  ["smiles:N#Cc1ccc(Oc2ccc(C#N)cc2)cc1", "4,4'-oxydibenzonitrile"], ["smiles:OS(=O)(=O)c1ccc(Oc2ccc(cc2)S(O)(=O)=O)cc1", "4,4'-oxydi(benzene-1-sulfonic acid)"],
  ["smiles:ClC(=O)c1ccc(Oc2ccc(cc2)C(Cl)=O)cc1", "4,4'-oxydibenzoyl dichloride"], ["smiles:OC1CCC(CC1)OC1CCC(O)CC1", "4,4'-oxydi(cyclohexan-1-ol)"],
  ["smiles:c1cncc(c1)Oc1cccnc1", "3,3'-oxydipyridine"], ["smiles:C(CN1CCCCC1)N1CCCCC1", "1,1'-(ethane-1,2-diyl)dipiperidine"], ["smiles:C(N1CCOCC1)N1CCOCC1", "4,4'-methylenedimorpholine"],
  ["smiles:CC(=O)N1CCN(CC1)C(C)=O", "1,1'-(piperazine-1,4-diyl)di(ethan-1-one)"], ["smiles:C(=O)(C=1N=C(NC1)C(=O)O)C=1N=C(NC1)C(=O)O", "4,4'-carbonyldi(1H-imidazole-2-carboxylic acid)"],
  // Substituted units (P-15.3.2.4.1): bis(...), the substituents at the same locants.
  ["smiles:Brc1ccc(Oc2ccc(Br)cc2)cc1", "1,1'-oxybis(4-bromobenzene)"], ["smiles:OC(=O)c1ccc(Oc2ccc(C(O)=O)c(Br)c2)cc1Br", "4,4'-oxybis(2-bromobenzoic acid)"],
  ["smiles:O=C=Nc1ccc(Cc2ccc(N=C=O)cc2)cc1", "1,1'-methylenebis(4-isocyanatobenzene)"], ["smiles:O=C=NC1CCC(CC2CCC(N=C=O)CC2)CC1", "1,1'-methylenebis(4-isocyanatocyclohexane)"],
  ["smiles:CN(C)c1ccc(Cc2ccc(N(C)C)cc2)cc1", "4,4'-methylenebis(N,N-dimethylaniline)"], ["smiles:Cc1ccc(O)c(Cc2cc(C)ccc2O)c1", "2,2'-methylenebis(4-methylphenol)"],
  ["smiles:OC(=O)c1cc(Cc2ccc(O)c(C(O)=O)c2)ccc1O", "3,3'-methylenebis(6-hydroxybenzoic acid)"], ["smiles:Clc1ccccc1Cc1ccccc1Cl", "1,1'-methylenebis(2-chlorobenzene)"],
  ["smiles:ClC(Cl)(Cl)C(c1ccc(Cl)cc1)c1ccc(Cl)cc1", "1,1'-(2,2,2-trichloroethane-1,1-diyl)bis(4-chlorobenzene)"],
  // Rings and chains in the multiplying group: phenylene, cyclohexanediyl, pyridine-2,6-diyl, naphthalene-1,5-diyl, alkanediyl,
  // and the units on chains (3,3'-(1,4-phenylene)di(propan-1-ol), P-59.2.1.3).
  ["smiles:OC(=O)Cc1ccc(CC(O)=O)cc1", "2,2'-(1,4-phenylene)diacetic acid"], ["smiles:OCCCc1ccc(CCCO)cc1", "3,3'-(1,4-phenylene)di(propan-1-ol)"],
  ["smiles:OCc1ccc(CO)cc1", "(1,4-phenylene)dimethanol"], ["smiles:NCc1ccc(CN)cc1", "(1,4-phenylene)dimethanamine"],
  ["smiles:OC(=O)Cc1cc(CC(O)=O)cc(CC(O)=O)c1", "2,2',2''-(benzene-1,3,5-triyl)triacetic acid"], ["smiles:OC(=O)CCc1cccc(CCC(O)=O)n1", "3,3'-(pyridine-2,6-diyl)dipropanoic acid"],
  ["smiles:Oc1ccc(cc1)C1(CCCCC1)c1ccc(O)cc1", "4,4'-(cyclohexane-1,1-diyl)diphenol"], ["smiles:Oc1ccc(C2CCC(c3ccc(O)cc3)CC2)cc1", "4,4'-(cyclohexane-1,4-diyl)diphenol"],
  ["smiles:Oc1ccc(-c2cccc3c(-c4ccc(O)cc4)cccc23)cc1", "4,4'-(naphthalene-1,5-diyl)diphenol"], ["smiles:OC(=O)c1ccc(-c2ccc(o2)-c2ccc(C(O)=O)cc2)cc1", "4,4'-(furan-2,5-diyl)dibenzoic acid"],
  ["smiles:OC(=O)c1ccc(cc1)C#Cc1ccc(cc1)C(O)=O", "4,4'-(ethyne-1,2-diyl)dibenzoic acid"], ["smiles:CC(c1ccc(O)cc1)c1ccc(O)cc1", "4,4'-(ethane-1,1-diyl)diphenol"],
  ["smiles:CC(C)(Cc1ccc(O)cc1)Cc1ccc(O)cc1", "4,4'-(2,2-dimethylpropane-1,3-diyl)diphenol"], ["smiles:C=C(c1ccc(O)cc1)c1ccc(O)cc1", "4,4'-(ethene-1,1-diyl)diphenol"],
  ["smiles:FC(F)(F)C(c1ccc(O)cc1)(c1ccc(O)cc1)C(F)(F)F", "4,4'-(1,1,1,3,3,3-hexafluoropropane-2,2-diyl)diphenol"],
  ["smiles:Oc1ccc(Cc2ccc(Cc3ccc(O)cc3)cc2)cc1", "4,4'-[1,4-phenylenebis(methylene)]diphenol"], ["smiles:OC(=O)COc1ccc(OCC(O)=O)cc1", "2,2'-[1,4-phenylenebis(oxy)]diacetic acid"],
  ["smiles:Nc1ccc(Oc2ccc(Oc3ccc(N)cc3)cc2)cc1", "4,4'-[1,4-phenylenebis(oxy)]dianiline"], ["smiles:c1ccccc1OCCOc1ccccc1", "1,1'-[ethane-1,2-diylbis(oxy)]dibenzene"],
  ["smiles:CC(C)(c1ccc(Oc2ccc(N)cc2)cc1)c1ccc(Oc2ccc(N)cc2)cc1", "4,4'-[propane-2,2-diylbis(4,1-phenyleneoxy)]dianiline"],
  ["smiles:C1OC1COCC1CO1", "2,2'-[oxybis(methylene)]dioxirane"], ["smiles:c1ccnc(c1)CCc1ccccn1", "2,2'-(ethane-1,2-diyl)dipyridine"],
  // Unsymmetrical central groups (P-15.3.3.1), and the most units (P-51.3.2.1).
  ["smiles:CC(Cc1ccccc1)c1ccccc1", "1,1'-(propane-1,2-diyl)dibenzene"], ["smiles:OC(=O)c1ccc(cc1)C(c1ccc(cc1)C(O)=O)Cc1ccc(cc1)C(O)=O", "4,4',4''-(ethane-1,1,2-triyl)tribenzoic acid"],
  ["smiles:Oc1ccc(cc1)C(c1ccc(O)cc1)c1ccc(O)cc1", "4,4',4''-methanetriyltriphenol"], ["smiles:c1ccccc1CC(Cc1ccccc1)(Cc1ccccc1)Cc1ccccc1", "1,1'-(2,2-dibenzylpropane-1,3-diyl)dibenzene"],
  // Stereo: descriptors of the units go in front, primed; those of the multiplying group stay with it.
  ["smiles:C[C@@H](O[C@H](C)C(O)=O)C(O)=O", "(2R,2'R)-2,2'-oxydipropanoic acid"], ["smiles:C[C@@H](O)COC[C@@H](C)O", "(2R,2'R)-1,1'-oxydi(propan-2-ol)"],
  ["L-cystine", "(2R,2'R)-3,3'-disulfanediylbis(2-aminopropanoic acid)"], ["smiles:Oc1ccc(/C=C/c2ccc(O)cc2)cc1", "4,4'-[(1E)-ethene-1,2-diyl]diphenol"],
  ["smiles:OC(=O)c1ccc(/N=N/c2ccc(C(O)=O)cc2)cc1", "4,4'-[(E)-diazene-1,2-diyl]dibenzoic acid"], ["diethylstilbestrol", "4,4'-[(3E)-hex-3-ene-3,4-diyl]diphenol"],
  ["smiles:Oc1ccccc1C=NCCN=Cc1ccccc1O", "2,2'-[ethane-1,2-diylbis(azanylylidenemethanylylidene)]diphenol"],
  ["smiles:Oc1ccccc1/C=N/CC/N=C/c1ccccc1O", "2,2'-{ethane-1,2-diylbis[azanylylidene(E)-methanylylidene]}diphenol"],
  ["smiles:Oc1ccccc1/C=N/[C@@H]1CCCC[C@H]1/N=C/c1ccccc1O", "2,2'-{[(1R,2R)-cyclohexane-1,2-diyl]bis[azanylylidene(E)-methanylylidene]}diphenol"],
  // Ions and salts.
  ["smiles:[O-]C(=O)c1ccc(Oc2ccc(C([O-])=O)cc2)cc1.[Na+].[Na+]", "disodium 4,4'-oxydibenzoate"],
  // Esters of a multiplied acid, the alkyl groups all alike (P-65.6.3.2.1).
  ["smiles:COC(=O)c1ccc(Oc2ccc(cc2)C(=O)OC)cc1", "dimethyl 4,4'-oxydibenzoate"], ["smiles:COC(=O)COCC(=O)OC", "dimethyl 2,2'-oxydiacetate"],
  ["smiles:CCOC(=O)CCSCCC(=O)OCC", "diethyl 3,3'-sulfanediyldipropanoate"],
  ["smiles:CCOC(=O)CN(CC(=O)OCC)CCN(CC(=O)OCC)CC(=O)OCC", "tetraethyl 2,2',2'',2'''-(ethane-1,2-diyldinitrilo)tetraacetate"],
  ["smiles:CCOC(=O)c1ccc(Oc2ccc(cc2)C(=O)OC)cc1", "methyl 4-[4-(ethoxycarbonyl)phenoxy]benzoate"],
  // Esters of a polyol framed as a multiplying group (P-15.3.0, P-13.6.2): oxydi(ethane-2,1-diyl), 1,4-phenylene.
  ["smiles:CC(=O)OCCOCCOC(C)=O", "oxydi(ethane-2,1-diyl) diacetate"], ["smiles:CC(=O)OCCOCCOCCOC(C)=O", "ethane-1,2-diylbis(oxyethane-2,1-diyl) diacetate"],
  ["smiles:O=C(OCCOCCOC(=O)c1ccccc1)c1ccccc1", "oxydi(ethane-2,1-diyl) dibenzoate"], ["smiles:CC(=O)Oc1ccc(OC(C)=O)cc1", "1,4-phenylene diacetate"],
  ["smiles:CC(=O)Oc1ccc(cc1)C(C)(C)c1ccc(OC(C)=O)cc1", "propane-2,2-diyldi(4,1-phenylene) diacetate"], ["smiles:CC(=O)OCC(=O)COC(C)=O", "2-oxopropane-1,3-diyl diacetate"],
  ["smiles:CS(=O)(=O)OCCOCCOS(C)(=O)=O", "oxydi(ethane-2,1-diyl) dimethanesulfonate"], ["smiles:CC(=O)OCCOC(C)=O", "ethane-1,2-diyl diacetate"],
  // Amides joined through their N (P-15.3.2.2.1).
  ["smiles:CC(=O)NCNC(C)=O", "N,N'-methylenediacetamide"], ["smiles:C=CC(=O)NCNC(=O)C=C", "N,N'-methylenedi(prop-2-enamide)"],
  ["smiles:CC(=O)NCCNC(C)=O", "N,N'-(ethane-1,2-diyl)diacetamide"], ["smiles:CC(=O)Nc1ccc(NC(C)=O)cc1", "N,N'-(1,4-phenylene)diacetamide"],
  ["smiles:CN(C(C)=O)CN(C)C(C)=O", "N,N'-methylenebis(N-methylacetamide)"], ["smiles:NC(=O)c1ccc(cc1)NCNc1ccc(cc1)C(N)=O", "4,4'-[methylenebis(azanediyl)]dibenzamide"],
  ["smiles:OC(=O)CCC(=O)NCCNC(=O)CCC(O)=O", "4,4'-[ethane-1,2-diylbis(azanediyl)]bis(4-oxobutanoic acid)"],
  // Ureas joined through an N, as amides are (P-15.3.2.2.1): each unit's N locants run N, N', then N'', N'''.
  ["smiles:NC(=O)NCNC(=O)N", "N,N''-methylenediurea"], ["smiles:NC(=O)NCCNC(=O)N", "N,N''-(ethane-1,2-diyl)diurea"],
  ["smiles:CNC(=O)NCNC(=O)NC", "N,N''-methylenebis(N'-methylurea)"], ["smiles:CN(C)C(=O)NCNC(=O)N(C)C", "N,N''-methylenebis(N',N'-dimethylurea)"],
  ["smiles:NC(=O)Nc1ccc(cc1)Cc1ccc(cc1)NC(=O)N", "N,N''-[methylenedi(4,1-phenylene)]diurea"],
  // Thioureas stay substitutive: OPSIN reads the multiplicative name as another structure.
  ["smiles:NC(=S)NCCNC(=S)N", "[2-(carbamothioylamino)ethyl]thiourea"],
  // Amine units joined through an amine N: N, or N with its carbon's locant where the unit has more than one amine.
  ["smiles:Nc1ccc(N(C)CCN(C)c2ccc(N)cc2)cc1", "N1,N1'-(ethane-1,2-diyl)bis(N1-methylbenzene-1,4-diamine)"],
  ["smiles:NCCN(C)CCN(C)CCN", "N1,N1'-(ethane-1,2-diyl)bis(N1-methylethane-1,2-diamine)"],
  // Ring assemblies as units (P-28): the second unit's locants primed past the first's own primes.
  ["smiles:c1ccc(cc1)-c1ccc(Oc2ccc(cc2)-c2ccccc2)cc1", "4,4''-oxydi(1,1'-biphenyl)"], ["smiles:c1ccc(cc1)-c1ccccc1Oc1ccccc1-c1ccccc1", "2,2''-oxydi(1,1'-biphenyl)"],
  ["smiles:c1ccc(cc1)-c1ccc(OCCOc2ccc(cc2)-c2ccccc2)cc1", "4,4''-[ethane-1,2-diylbis(oxy)]di(1,1'-biphenyl)"],
  ["smiles:OC(=O)c1ccc(cc1)-c1ccc(Cc2ccc(cc2)-c2ccc(cc2)C(O)=O)cc1", "4',4'''-methylenedi([1,1'-biphenyl]-4-carboxylic acid)"],
  // Esters of different alkyl groups: a compound alkyl group after its locant in enclosing marks (P-16.5.1).
  ["smiles:O=C(OC)CCCC(=O)OCC(C)C", "1-methyl 5-(2-methylpropyl) pentanedioate"], ["smiles:CCOC(=O)CCC(=O)OC(C)C", "1-ethyl 4-(propan-2-yl) butanedioate"],
  ["smiles:CCOC(=O)CC(=O)OC", "1-ethyl 3-methyl propanedioate"],
  // Substitutive names stand: acyclic hydrocarbons are never units (P-15.3.4.2), different locants (P-51.3.3),
  // unsymmetrical substitution (P-15.3.4.1), a senior parent elsewhere (P-51.3.2.3), units of different configuration.
  ["smiles:CCOCC", "ethoxyethane"], ["smiles:ClCCOCCCl", "1-chloro-2-(2-chloroethoxy)ethane"], ["smiles:CS(C)=O", "(methanesulfinyl)methane"],
  ["smiles:OC(=O)C1CCC(CC1)CC1CCCCC1C(O)=O", "2-[(4-carboxycyclohexyl)methyl]cyclohexane-1-carboxylic acid"],
  ["smiles:OC(=O)c1ccc(Cl)cc1Cc1cccc(c1)C#N", "4-chloro-2-[(3-cyanophenyl)methyl]benzoic acid"], ["smiles:CC(C(O)=O)OCCC(O)=O", "2-(2-carboxyethoxy)propanoic acid"],
  ["smiles:Oc1ccc(Cl)cc1CCc1ccc(Cl)c(O)c1", "2-chloro-5-[2-(5-chloro-2-hydroxyphenyl)ethyl]phenol"],
  ["smiles:OC(=O)c1ccc(OCC(Cl)OCCc2ccc(C(O)=O)cc2)cc1", "4-{2-[2-(4-carboxyphenoxy)-1-chloroethoxy]ethyl}benzoic acid"],
  ["smiles:C1CCCCC1NC1CCCCC1", "N-cyclohexylcyclohexanamine"], ["smiles:NCCNCCN", "N1-(2-aminoethyl)ethane-1,2-diamine"], ["smiles:O=C(c1ccccc1)c1ccccc1", "diphenylmethanone"],
  ["smiles:OC(=O)CC(=O)N(CC(O)=O)CC(O)=O", "3-[bis(carboxymethyl)amino]-3-oxopropanoic acid"], ["smiles:c1ccccc1/N=N/c1ccccc1", "(E)-diphenyldiazene"],
  ["smiles:C[C@@H](O[C@@H](C)C(O)=O)C(O)=O", "(2R)-2-[(1S)-1-carboxyethoxy]propanoic acid"], ["smiles:C[C@@H](O)COC[C@H](C)O", "(2R)-1-[(2S)-2-hydroxypropoxy]propan-2-ol"],
  ["smiles:C[N+](C)(CCO)CCO", "2-hydroxy-N-(2-hydroxyethyl)-N,N-dimethylethan-1-aminium"],
];

const out: string[] = [];
const t0 = performance.now();
for (const [input, want] of cases) {
  const smiles = input.startsWith("smiles:") ? input.slice(7) : opsin.parseToSmiles(input);
  assert.ok(smiles, `OPSIN reads ${input}`);
  const g = graphOf(molOf(smiles), cipOf(smiles));
  assert.ok(g, `a graph for ${input}`);
  const r = iupacNameWhy(g);
  if (process.argv.includes("--names")) { console.log(`${input} -> ${r.name ?? `(${r.why})`}`); continue; }
  assert.ok(r.name, `no name for ${input} (${smiles}): ${r.why}`);
  const back = opsin.parseToSmiles(r.name);
  assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${input} -> ${r.name}, a different structure`);
  assert.equal(r.name, want, input);
  out.push(`${input} -> ${r.name}`);
}
const ms = (performance.now() - t0) / cases.length;
console.log(`namer-multiplicative.check: ${out.length}/${cases.length} named and read back (${ms.toFixed(1)} ms each, OPSIN and InChI included)`);
