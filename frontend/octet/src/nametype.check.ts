// Run: node src/nametype.check.ts. The typography of names (nametype.ts): each name's runs written with _italic_,
// ^superscript^ and ~subscript~ marks must be as IUPAC prints the name, and the runs' text must be the name itself.
import assert from "node:assert/strict";
import { nameRuns } from "./nametype.ts";
import { plainOf, type TextRun } from "./richtext.ts";

const marked = (runs: TextRun[]) => runs.map((r) => (r.italic ? `_${r.text}_` : r.script === "super" ? `^${r.text}^` : r.script === "sub" ? `~${r.text}~` : r.text)).join("");
const cases: [string, string][] = [
  ["N,N-dimethylformamide", "_N_,_N_-dimethylformamide"],
  ["N1,N1'-(ethane-1,2-diyl)bis(N1-methylbenzene-1,4-diamine)", "_N_^1^,_N_^1^'-(ethane-1,2-diyl)bis(_N_^1^-methylbenzene-1,4-diamine)"],
  ["N,N''-methylenediurea", "_N_,_N_''-methylenediurea"],
  ["ethanethioic O-acid", "ethanethioic _O_-acid"],
  ["S-methyl ethanethioate", "_S_-methyl ethanethioate"],
  ["2-tert-butyl-4-methylphenol", "2-_tert_-butyl-4-methylphenol"],
  ["(2R,3S)-2,3-dibromobutane", "(2_R_,3_S_)-2,3-dibromobutane"],
  ["(E)-but-2-ene", "(_E_)-but-2-ene"],
  ["(1R*,3R*,5SR)-3-chloro-5-nitrocyclohexan-1-ol", "(1_R_*,3_R_*,5_SR_)-3-chloro-5-nitrocyclohexan-1-ol"],
  ["rac-(1R,3R)-1-amino-3-chloropropane-1,3-diol", "_rac_-(1_R_,3_R_)-1-amino-3-chloropropane-1,3-diol"],
  ["1H-indole", "1_H_-indole"],
  ["quinolin-2(1H)-one", "quinolin-2(1_H_)-one"],
  ["21H,23H-porphyrin", "21_H_,23_H_-porphyrin"],
  ["9H-fluoren-9-ylmethanol", "9_H_-fluoren-9-ylmethanol"],
  ["1H-benzo[d][1,2,3]triazole", "1_H_-benzo[_d_][1,2,3]triazole"],
  ["dibenzo[b,e][1,4]dimercurine", "dibenzo[_b_,_e_][1,4]dimercurine"],
  ["pyrido[1,2-a]pyrimidine", "pyrido[1,2-_a_]pyrimidine"],
  ["bicyclo[2.2.1]heptane", "bicyclo[2.2.1]heptane"],
  ["[1,1'-biphenyl]-4-carboxylic acid", "[1,1'-biphenyl]-4-carboxylic acid"],
  ["cis-diamminedichloridoplatinum(II)", "_cis_-diamminedichloridoplatinum(II)"],
  ["fac-triamminetrichloridocobalt(III)", "_fac_-triamminetrichloridocobalt(III)"],
  ["(SP-4-3)-carbonylchloridobis(triphenylphosphane)iridium", "(_SP_-4-3)-carbonylchloridobis(triphenylphosphane)iridium"],
  ["(T-4-R)-bromidochlorido(pyridine)(triphenylphosphane)zinc(II)", "(_T_-4-_R_)-bromidochlorido(pyridine)(triphenylphosphane)zinc(II)"],
  ["(TBPY-5-11)-tricarbonylbis(triphenylphosphane)iron", "(_TBPY_-5-11)-tricarbonylbis(triphenylphosphane)iron"],
  ["Δ-tris(ethane-1,2-diamine-κ2N,N')cobalt(3+)", "Δ-tris(ethane-1,2-diamine-κ^2^_N_,_N_')cobalt(3+)"],
  ["tris(2,2'-bipyridine-κ2N1,N1')ruthenium(2+)", "tris(2,2'-bipyridine-κ^2^_N_^1^,_N_^1^')ruthenium(2+)"],
  ["tetrakis(μ-acetato-κO:κO')dirhodium(Rh—Rh)", "tetrakis(μ-acetato-κ_O_:κ_O_')dirhodium(_Rh_—_Rh_)"],
  ["nonacarbonyl-1κ5C,2κ4C-rheniumcobalt(Re—Co)", "nonacarbonyl-1κ^5^_C_,2κ^4^_C_-rheniumcobalt(_Re_—_Co_)"],
  ["tetra-μ3-carbonyl-1:2:3κ3C-octahedro-hexarhodium(12 Rh—Rh)", "tetra-μ~3~-carbonyl-1:2:3κ^3^_C_-_octahedro_-hexarhodium(12 _Rh_—_Rh_)"],
  ["dodecacarbonyl-1κ4C,2κ4C,3κ4C-dichlorido-1κCl,2κCl-triosmium(Os1—Os3)(Os2—Os3)", "dodecacarbonyl-1κ^4^_C_,2κ^4^_C_,3κ^4^_C_-dichlorido-1κ_Cl_,2κ_Cl_-triosmium(_Os_^1^—_Os_^3^)(_Os_^2^—_Os_^3^)"],
  ["(η6-benzene)tricarbonylchromium", "(η^6^-benzene)tricarbonylchromium"],
  ["1λ5-phosphinine", "1λ^5^-phosphinine"],
  // Nothing to style: no runs of their own.
  ["ethanol", "ethanol"], ["4-(4-phenylphenoxy)-1,1'-biphenyl", "4-(4-phenylphenoxy)-1,1'-biphenyl"], ["sodium chloride--water (1/6)", "sodium chloride--water (1/6)"],
  ["2,3,4,5,6-pentahydroxyhexanal", "2,3,4,5,6-pentahydroxyhexanal"], ["benzene", "benzene"], ["2-(hydroxymethyl)propane-1,3-diol", "2-(hydroxymethyl)propane-1,3-diol"],
];
for (const [name, want] of cases) {
  const runs = nameRuns(name);
  assert.equal(plainOf(runs), name, `${name}: the same characters`);
  assert.equal(marked(runs), want, name);
}
console.log(`nametype.check: ${cases.length} names set in italic and superscript as IUPAC prints them`);
