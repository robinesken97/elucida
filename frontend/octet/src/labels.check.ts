// Run: node src/labels.check.ts. Fails loudly if label reading breaks.
import assert from "node:assert/strict";
import { anchorElement, formulaRuns, isElement, labelSmiles, units } from "./labels.ts";

assert.deepEqual(units("CO2Et").map((u) => [u.text, u.count ?? ""]), [["C", ""], ["O", "2"], ["Et", ""]]);
assert.deepEqual(units("NHBoc").map((u) => u.text), ["N", "H", "Boc"]);
assert.deepEqual(units("N(Boc)2").map((u) => [u.text, u.count ?? ""]), [["N", ""], ["(Boc)", "2"]]);
assert.deepEqual(units("CCl3").map((u) => [u.text, u.count ?? ""]), [["C", ""], ["Cl", "3"]]);
assert.equal(anchorElement("OMe"), "O");
assert.equal(anchorElement("Ph"), undefined);
assert.ok(isElement("Cl") && !isElement("OMe"));
const cases: Record<string, string> = {
  OMe: "O(C)", CO2Et: "C(=O)O(CC)", CO2H: "C(=O)O", CF3: "C(F)(F)(F)", NHBoc: "N(C(=O)OC(C)(C)C)", NMe2: "N(C)(C)",
  CH2OH: "CO", OH: "O", CN: "C#N", "N(Boc)2": "N(C(=O)OC(C)(C)C)(C(=O)OC(C)(C)C)", Ph: "c1ccccc1", PPh3: "P(c1ccccc1)(c1ccccc1)(c1ccccc1)",
};
for (const [label, smiles] of Object.entries(cases)) assert.equal(labelSmiles(label), smiles, label);
assert.equal(labelSmiles("Hello world"), undefined);
// Labels written right to left read from the atom that attaches, and no label starts its SMILES with a branch.
const reversed: Record<string, string> = {
  H2O2: "OO", HO2C: "C(=O)O", HOOC: "C(=O)O", OHC: "C=O", O2N: "[N+](=O)[O-]", MeO: "O(C)", EtO2C: "C(=O)O(CC)", Et3N: "N(CC)(CC)(CC)", BocHN: "N(C(=O)OC(C)(C)C)",
};
for (const [label, smiles] of Object.entries(reversed)) assert.equal(labelSmiles(label), smiles, label);
for (const label of ["H2O2", "Me3Si", "(CH2)3", "Ph2", "H2(Boc)2", "HN(Me)2"]) assert.ok(!labelSmiles(label)?.startsWith("("), label);
assert.equal(labelSmiles("C999"), undefined);
// Labels Indigo cannot lay out in good time are not read: an atom with more than eight neighbours or more than four
// groups with a ring on it, a ring atom with more than four neighbours, or more than 120 atoms. Others are read.
for (const label of ["Ph4", "Ph6", "Ph10", "(Ph)6", "PhPh4", "PhPh5", "CPh5", "CPh50", "CyCy5", "TsTs5", "Fmoc12", "CPh4Ph4", "(PhPh4)4", "PhCl12", "CCl99", "(CCl9)30", "(C99)99", "C99C99", "CyPh4ClTr", "TsCyTrPMeClTr", "TBDPSP99", "Si12Si99MeC5"]) assert.equal(labelSmiles(label), undefined, label);
for (const label of ["Ph2", "Ph3", "CPh3", "Ph3C", "Ph3P", "BPh4", "Ph4B", "Pd(PPh3)4", "CTr4", "SF5", "PF6", "W(CO)6", "Fe(CO)5", "CCl3", "C99", "(CH2)3", "TBDPS", "Si(iPr)3", "Fmoc", "Mes", "Tr"]) assert.ok(labelSmiles(label), label);
// Formulas in conditions and tables: counts after an element, group or bracket are subscripts; other numbers are not.
const runs = (t: string) => formulaRuns(t).map((r) => (r.sub ? `_${r.text}` : r.text)).join("");
for (const [t, want] of Object.entries({
  K2CO3: "K_2CO_3", "Pd(PPh3)4": "Pd(PPh_3)_4", Et3N: "Et_3N", "DMSO-d6": "DMSO-d_6", "[Rh(cod)Cl]2": "[Rh(cod)Cl]_2", B2pin2: "B_2pin_2",
  "1,4-dioxane": "1,4-dioxane", "12 h": "12 h", L1: "L1", B3LYP: "B3LYP", "THF/H2O (4:1)": "THF/H_2O (4:1)", "2a": "2a",
})) assert.equal(runs(t), want, t);
// A label of more than one line is text: no chemistry reads it (it counts as an unknown atom), and it is no element.
for (const t of ["Direct,\nNo ISC", "OMe\nCH3", "N\nH"]) assert.ok(labelSmiles(t) === undefined && !isElement(t), JSON.stringify(t));
console.log("labels.check: ok");
