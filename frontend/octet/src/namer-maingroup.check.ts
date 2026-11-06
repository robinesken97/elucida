// Run: node src/namer-maingroup.check.ts. Structure to Name for the heavier main-group elements and charged species
// (namer-maingroup.ts and the namer's rules for them): ring oxides by the λ-convention, ring anions and cations of
// P, As, Sb, Si, Se and Te, selenonates and isoselenocyanates, silyl esters and azanides, inorganic species, N drawn
// with five bonds, N-oxides, selones, sulfoximines, cyanides on P, and isotopes (P-82). Each input becomes a structure
// (OPSIN, or the SMILES given), with each atom's hydrogens and isotope as written; Octet names it, and OPSIN must read
// the name back as the same structure (same standard InChI). Every case must be named, and give the name shown.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "./naming.ts";
import { iupacNameWhy } from "./namer.ts";
import { cipLabels } from "./cip.ts";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer-maingroup.check: skipped (no OPSIN build)"); process.exit(0); }
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
type KetAtom = { label: string; charge?: number; isotope?: number; cip?: string };
type KetMol = { type: string; atoms: KetAtom[]; bonds: { type: number; atoms: [number, number]; cip?: string }[] };
const molecules = (ket: { root: { nodes: { $ref: string }[] }; [k: string]: unknown }) => ket.root.nodes.map(({ $ref }) => ket[$ref] as KetMol).filter((f) => f?.type === "molecule");
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
// The structure read by Indigo (Kekulé bonds): each atom with its isotope (D and T are labels) and the
// hydrogens the SMILES gives it ([AsH5] five, [Se] none), which Indigo adds as atoms after each fragment's own.
function read(smiles: string): { mol: Mol; cip: { atoms: (string | undefined)[]; bonds: (string | undefined)[] } } {
  const o = new indigo.MapStringString();
  o.set("output-content-type", "application/json");
  o.set("dearomatize-on-load", "true");
  try {
    const before = molecules(JSON.parse(JSON.parse(indigo.calculateCip(smiles, "ket", o)).struct));
    const after = molecules(JSON.parse(JSON.parse(indigo.convert_explicit_hydrogens(smiles, "unfold", "ket", o)).struct));
    const atoms: (KetAtom & { h: number })[] = [], bonds: KetMol["bonds"] = [];
    before.forEach((f, k) => {
      const base = atoms.length, own = f.atoms.length, h = f.atoms.map(() => 0);
      for (const b of after[k].bonds) if (b.atoms[1] >= own) h[b.atoms[0]]++; else if (b.atoms[0] >= own) h[b.atoms[1]]++;
      atoms.push(...f.atoms.map((a, i) => ({ ...a, h: h[i] })));
      bonds.push(...f.bonds.map((b) => ({ ...b, atoms: [b.atoms[0] + base, b.atoms[1] + base] as [number, number] })));
    });
    return {
      mol: { atoms: atoms.map((a) => ({ label: a.label, charge: a.charge, implicitHCount: a.h, ...(a.isotope ? { isotope: a.isotope } : {}), location: [0, 0, 0] as [number, number, number] })), bonds: bonds.map((b) => ({ type: b.type, atoms: b.atoms })) },
      cip: cipOf(smiles, bonds),
    };
  } finally { o.delete(); }
}

// Input (a name OPSIN reads, or smiles:...) and the name Octet must give.
const cases: [string, string][] = [
  // =O on ring Se, Te, As, Sb, S and P by the λ-convention (P-14.1.3), in monocycles and fused systems.
  ["smiles:O=[Se]1C=CC=C1", "1λ⁴-selenophen-1-one"], ["smiles:O=[Se]1(=O)CCCC1", "1λ⁶-selenolane-1,1-dione"], ["smiles:O=[Te]1CC=CC=C1", "2H-1λ⁴-tellurin-1-one"],
  ["smiles:O=[As]1(c2ccccc2)CCCC1", "1-phenyl-1λ⁵-arsolan-1-one"], ["smiles:O=[Se]1N=CC=C1", "1λ⁴,2-selenazol-1-one"],
  ["smiles:C1=CC=CC=2OC3=CC=CC=C3[AsH](C12)=O", "10H-10λ⁵-dibenzo[b,e][1,4]oxarsinin-10-one"],
  ["smiles:C1=CC=CC=2OC3=CC=CC=C3[SbH](C12)=O", "10H-10λ⁵-dibenzo[b,e][1,4]oxastibinin-10-one"],
  ["smiles:C1=CC=CC=2[Se](C3=CC=CC=C3[Se]C12)=O", "5λ⁴-dibenzo[b,e][1,4]diselenin-5-one"], ["smiles:N=1[Se](N=C2C=CC=CC12)=O", "2λ⁴,1,3-benzoselenadiazol-2-one"],
  ["smiles:C1=CC=CC=2[AsH](C3=CC=CC=C3CC12)=O", "5λ⁵-dibenzo[b,e]arsinin-5(10H)-one"], ["smiles:O=S1c2ccccc2Cc2ccccc21", "9H-10λ⁴-thioxanthen-10-one"],
  ["smiles:O=P1(c2ccccc2)c2ccccc2-c2ccccc21", "5-phenyl-5H-5λ⁵-dibenzo[b,d]phosphol-5-one"], ["smiles:OP1(=O)CCCC1", "1-hydroxy-1λ⁵-phospholan-1-one"],
  ["smiles:OP1CCCCC1", "phosphinan-1-ol"], ["smiles:P1(CCC2=CC=CC=C12)O", "2,3-dihydro-1H-1-benzophosphol-1-ol"],
  ["smiles:O=[As]c1ccccc1", "oxo(phenyl)arsane"], ["smiles:Cl[Bi]=O", "chloro(oxo)bismuthane"],
  // =S on a ring P is a λ⁵ thione as =O is a λ⁵ one. Cages of P and O or S are named on adamantane by replacement
  // (P-23.7, P-15.4): P4O6, P4O10, P4S10 (phosphorus pentasulfide).
  ["smiles:S=P1(C)CCCC1", "1-methyl-1λ⁵-phospholane-1-thione"], ["smiles:S=P1(C)C=CC=C1", "1-methyl-1H-1λ⁵-phosphole-1-thione"],
  ["smiles:P12OP3OP(OP(O1)O3)O2", "2,4,6,8,9,10-hexaoxa-1,3,5,7-tetraphosphaadamantane"],
  ["smiles:P12(=O)OP3(=O)OP(=O)(O1)OP(=O)(O2)O3", "2,4,6,8,9,10-hexaoxa-1λ⁵,3λ⁵,5λ⁵,7λ⁵-tetraphosphaadamantane-1,3,5,7-tetraone"],
  ["phosphorus pentasulfide", "2,4,6,8,9,10-hexathia-1λ⁵,3λ⁵,5λ⁵,7λ⁵-tetraphosphaadamantane-1,3,5,7-tetrathione"],
  // Ring anions of P, As, Sb and Si; their parent hydride anions; Se and Te ring cations; ylides (P-72, P-73).
  ["smiles:[P-]1C=CC2=CC=CC=C12", "1H-1-benzophosphol-1-ide"], ["smiles:C1=CC=CC=2OC3=CC=CC=C3[As-]C12", "10H-dibenzo[b,e][1,4]oxarsinin-10-ide"],
  ["smiles:C1=CC=CC=2OC3=CC=CC=C3[SiH-]C12", "10H-dibenzo[b,e][1,4]oxasilin-10-ide"], ["smiles:c1ccccc1[P-]c1ccccc1", "diphenylphosphanide"],
  ["smiles:C[Si-](C)c1ccccc1", "dimethyl(phenyl)silanide"], ["smiles:[Se+]1=CC=CC=C1", "selenopyrylium"], ["smiles:[Te+]1=CC=CC=C1", "telluropyrylium"],
  ["smiles:[Se+]1=CC=CC2=CC=CC=C12", "1-benzoselenopyran-1-ium"], ["smiles:C1(=[Se+]C=CC2=CC=CC=C12)C(=O)O", "1-carboxy-2-benzoselenopyran-2-ium"],
  ["smiles:[O+]1=[C-]C=CC=C1", "pyrylium-2-ide"], ["smiles:[Se+]1=[C-]C=CC2=CC=CC=C12", "1-benzoselenopyran-1-ium-2-ide"],
  // Se and Te acid anions, cyanates and isocyanates; silyl esters, silyl azanides, nitramines.
  ["smiles:NCCC[Se](=O)(=O)[O-]", "3-aminopropane-1-selenonate"], ["smiles:[O-][Se](=O)c1ccccc1.[Na+]", "sodium benzeneseleninate"],
  ["smiles:c1ccccc1N=C=[Se]", "isoselenocyanatobenzene"], ["smiles:N#C[Te]C", "tellurocyanatomethane"], ["smiles:O=C(N=C=[Se])c1ccccc1", "benzoyl isoselenocyanate"],
  ["smiles:N=C=[Se]", "isoselenocyanic acid"], ["smiles:C[Si](C)(C)N=C=O", "isocyanato(trimethyl)silane"],
  ["lithium bis(trimethylsilyl)azanide", "lithium bis(trimethylsilyl)azanide"], ["trimethylsilyl trifluoromethanesulfonate", "trimethylsilyl trifluoromethanesulfonate"],
  ["smiles:C[Si](C)(C)OP(=O)(O[Si](C)(C)C)O[Si](C)(C)C", "tris(trimethylsilyl) phosphate"], ["smiles:C[Si](C)(C)OS(=O)(=O)O[Si](C)(C)C", "bis(trimethylsilyl) sulfate"],
  ["smiles:[N+](=O)([O-])N1CN(CN(C1)[N+](=O)[O-])[N+](=O)[O-]", "1,3,5-trinitro-1,3,5-triazinane"], ["smiles:CN(C)[N+](=O)[O-]", "N-methyl-N-nitromethanamine"],
  ["smiles:[N-](c1ccccc1)C(=O)OC", "(methoxycarbonyl)(phenyl)azanide"], ["smiles:[Na+].[N-](C(=O)OC(C)(C)C)C(=O)OC(C)(C)C", "sodium bis(tert-butoxycarbonyl)azanide"],
  // Inorganic species (IR-6, IR-8; P-67.1.1.1).
  ["smiles:O[Se](=O)(=O)O[Se](=O)(=O)O", "diselenic acid"], ["smiles:O[Se](=O)(=O)[Se](=O)(=O)O", "hypodiselenic acid"], ["smiles:[Te](O)(O)(O)(O)(O)O", "orthotelluric acid"],
  ["smiles:[O-][Te](=O)(=O)[O-]", "tellurate"], ["smiles:[O-][Xe](=O)(=O)([O-])([O-])[O-]", "perxenate"], ["smiles:O[As](=O)(O)[As](=O)(O)O", "hypodiarsoric acid"],
  ["smiles:O[PH](=O)O[PH](=O)O", "diphosphonic acid"], ["smiles:[NH2+](O)[O-]", "azinic acid"], ["smiles:[N+](O)(O)(O)[O-]", "azoric acid"],
  ["smiles:[NH3+][O-]", "ammonia oxide"], ["smiles:[NH+]([O-])=O", "nitryl hydride"], ["smiles:N[N+](=O)[O-]", "nitramide"], ["smiles:N[O-]", "aminooxidanide"],
  ["smiles:[O-][Si]([O-])([O-])[O-]", "orthosilicate"], ["smiles:[SbH2-]", "stibanide"], ["smiles:[AsH5]", "λ⁵-arsane"], ["smiles:[GaH4-]", "tetrahydrogallate"],
  ["smiles:Br[Al-](Br)(Br)Br", "tetrabromoaluminate"], ["smiles:Cl[Ga-](Cl)(Cl)Cl", "tetrachlorogallate"], ["smiles:Br[Se](Br)=O", "seleninyl dibromide"],
  ["smiles:Cl[Te](Cl)(=O)=O", "telluronyl dichloride"], ["smiles:[PH3]=[PH3]", "1λ⁵,2λ⁵-diphosphene"], ["smiles:[PH2]#P[PH3][PH4]", "1λ⁵,2λ⁵,3λ⁵,4λ⁵-tetraphosph-1-yne"],
  ["smiles:PPP", "triphosphane"], ["smiles:[AsH]=[AsH]", "diarsene"], ["smiles:[BH]=[BH]", "diborene"], ["smiles:[SH2]=N", "λ⁴-sulfanimine"],
  ["smiles:[SeH2](=O)=N", "imino-λ⁶-selanone"], ["smiles:OSC#N", "hydroxysulfanecarbonitrile"], ["smiles:N#CN=[N+]=[N-]", "carbononitridic azide"],
  ["smiles:[NH+]#[C-]", "hydrogen isocyanide"], ["smiles:[O-]OC(=O)[O-]", "peroxocarbonate"],
  // N drawn with five bonds is named in its charge-separated form; amine N-oxides as prefixes.
  ["smiles:CN(=O)=O", "nitromethane"], ["smiles:O=N(=O)c1ccccc1", "nitrobenzene"], ["smiles:O=N1=CC=CC=C1", "pyridine 1-oxide"],
  ["smiles:CN(C)(C)=O", "N,N-dimethylmethanamine N-oxide"], ["smiles:OC(=O)CN(C)(C)=O", "[dimethyl(oxido)azaniumyl]acetic acid"],
  ["smiles:[NH2]([C@@H](CCSC)C(=O)O)=O", "(2S)-4-(methylsulfanyl)-2-(oxidoazaniumyl)butanoic acid"],
  // Azoxy compounds (P-68.3.1.3.3): diazene oxides, and as prefixes.
  ["azoxybenzene", "1,2-diphenyldiazene 1-oxide"], ["smiles:C/[N+]([O-])=N/c1ccccc1", "(Z)-1-methyl-2-phenyldiazene 1-oxide"],
  ["methylazoxymethanol acetate", "[(Z)-2-methyl-2-oxidodiazen-2-ium-1-yl]methyl acetate"], ["smiles:CC(=O)OC/[N+]([O-])=N/C", "[(Z)-2-methyl-1-oxidodiazen-1-ium-1-yl]methyl acetate"],
  // Selones and tellones under a senior group; sulfoximines and sulfonimidic acids; cyanides on P.
  ["smiles:N1C(=[Se])NC=2N=CNC2C1=O", "2-selanylidene-1,2,3,7-tetrahydro-6H-purin-6-one"], ["smiles:O=C1CCC(=[Te])CC1", "4-tellanylidenecyclohexan-1-one"],
  ["smiles:CS(=O)(=N)c1ccccc1", "(methanesulfonimidoyl)benzene"], ["smiles:OC(=O)c1ccc(S(C)(=O)=N)cc1", "4-(methanesulfonimidoyl)benzoic acid"],
  ["smiles:FC(S(=O)(O)=N)(F)F", "trifluoromethanesulfonimidic acid"], ["smiles:CCOP(=O)(C#N)OCC", "diethyl phosphorocyanidate"],
  ["smiles:O=P(C#N)(N(C)C)OCC", "ethyl N,N-dimethylphosphoramidocyanidate"], ["smiles:ClP(=O)(N(C)C)OC", "methyl N,N-dimethylphosphoramidochloridate"],
  // Isotopes (P-82): in the parent, its suffix, prefixes, species and salts; locants left out where nothing else is meant.
  ["smiles:[2H]C([2H])([2H])O", "(²H₃)methanol"], ["smiles:CO[2H]", "(O-²H₁)methanol"], ["smiles:[2H]C([2H])([2H])O[2H]", "(²H₄)methanol"],
  ["smiles:[2H]C(Cl)(Cl)Cl", "trichloro(²H₁)methane"], ["smiles:[2H]c1c([2H])c([2H])c([2H])c([2H])c1[2H]", "(²H₆)benzene"],
  ["smiles:[2H]C([2H])([2H])S(=O)C([2H])([2H])[2H]", "[(²H₃)methanesulfinyl](²H₃)methane"], ["smiles:[2H]O[2H]", "(²H₂)water"],
  ["smiles:[13CH4]", "(¹³C)methane"], ["smiles:CC([2H])([2H])O", "(1,1-²H₂)ethanol"], ["smiles:C[13C](=O)O", "(1-¹³C)acetic acid"],
  ["smiles:FC(F)(F)C(=O)O[2H]", "trifluoro(O-²H₁)acetic acid"], ["smiles:OC(=O)c1ccc(O[2H])cc1", "4-[(²H₁)hydroxy]benzoic acid"],
  ["smiles:[2H]N([2H])c1ccccc1", "(N,N-²H₂)aniline"], ["smiles:[2H]c1nc([2H])c([2H])c([2H])c1[2H]", "(²H₅)pyridine"],
  ["smiles:[2H]C([2H])([2H])C(=O)C([2H])([2H])[2H]", "(²H₆)propan-2-one"], ["smiles:[2H]C([2H])([2H])c1c([2H])c([2H])c([2H])c([2H])c1[2H]", "[(²H₃)methyl](²H₅)benzene"],
  ["smiles:[2H]C([2H])([2H])OC(=O)OC([2H])([2H])[2H]", "bis[(²H₃)methyl] carbonate"], ["smiles:C[C@H]([2H])O", "(1S)-(1-²H₁)ethanol"],
  ["smiles:[Na+].[B-]([2H])([2H])([2H])[2H]", "sodium (²H₄)tetrahydroborate"], ["smiles:[B-]([3H])([3H])([3H])[3H]", "(³H₄)tetrahydroborate"],
  ["smiles:[2H]C([2H])([2H])[13CH3]", "(1-¹³C,2,2,2-²H₃)ethane"], ["smiles:[15NH3]", "(¹⁵N)ammonia"],
];

const out: string[] = [];
const t0 = performance.now();
for (const [input, want] of cases) {
  const smiles = input.startsWith("smiles:") ? input.slice(7) : opsin.parseToSmiles(input);
  assert.ok(smiles, `OPSIN reads ${input}`);
  const { mol, cip } = read(smiles);
  const g = graphOf(mol, cip, true);
  assert.ok(g, `a graph for ${input}`);
  const r = iupacNameWhy(g);
  assert.ok(r.name, `no name for ${input} (${smiles}): ${r.why}`);
  const back = opsin.parseToSmiles(r.name);
  assert.ok(back && convert(back, "inchi") === convert(smiles, "inchi"), `${input} -> ${r.name}, a different structure`);
  assert.equal(r.name, want, input);
  out.push(`${input} -> ${r.name}`);
}
const ms = (performance.now() - t0) / cases.length;
if (process.argv.includes("--names")) console.log(out.join("\n"));
console.log(`namer-maingroup.check: ${cases.length}/${cases.length} named and read back (${ms.toFixed(1)} ms each, OPSIN and InChI included)`);

// Isotopes the namer cannot place are not named: a D on a ring's carbaldehyde carbon has no locant OPSIN reads.
for (const s of ["O=C([2H])c1ccccc1"]) {
  const { mol, cip } = read(s);
  assert.equal(iupacNameWhy(graphOf(mol, cip, true)!).why, "isotope", s);
}
// Without isotopes allowed (the NMR and property panels), a drawing with them has no graph.
assert.equal(graphOf(read("[2H]C([2H])([2H])O").mol), undefined);
console.log("namer-maingroup.check: isotopes the namer cannot place give no name");
