// Run: node src/labels.check.ts. Fails loudly if label reading breaks.
import assert from "node:assert/strict";
import { anchorElement, chemicalText, formulaRuns, isElement, labelSmiles, pieces, units } from "./labels.ts";
import { render, type Ink } from "./render.ts";
import { widthOf } from "./arial.ts";

assert.deepEqual(units("CO2Et").map((u) => [u.text, u.count ?? ""]), [["C", ""], ["O", "2"], ["Et", ""]]);
assert.deepEqual(units("NHBoc").map((u) => u.text), ["N", "H", "Boc"]);
assert.deepEqual(units("N(Boc)2").map((u) => [u.text, u.count ?? ""]), [["N", ""], ["(Boc)", "2"]]);
assert.deepEqual(units("CCl3").map((u) => [u.text, u.count ?? ""]), [["C", ""], ["Cl", "3"]]);
// A word Octet cannot read as elements and groups is one unit (an abbreviation it does not know), after its first
// element when an abbreviation follows: ODMT is O and DMT, never O, D, M, T.
for (const [label, want] of Object.entries({ ODMT: "O|DMT", DMT: "DMT", ODMTr: "O|DMTr", CH2ODMT: "C|H2|O|DMT", NPhth: "N|Phth", NHPG: "N|H|PG",
  SEM: "SEM", OSEM: "O|SEM", PG: "PG", ONf: "O|Nf", Nu: "Nu", ALK: "ALK", "R'": "R'", OR: "O|R", NR2: "N|R2", OTBS: "O|TBS", NHBoc: "N|H|Boc" }))
  assert.equal(units(label).map((u) => u.text + (u.count ?? "")).join("|"), want, label);
assert.equal(anchorElement("OMe"), "O");
assert.equal(anchorElement("Ph"), undefined);
assert.ok(isElement("Cl") && !isElement("OMe"));
const cases: Record<string, string> = {
  OMe: "OC", CO2Et: "C(=O)OCC", CO2H: "C(=O)O", CF3: "C(F)(F)F", NHBoc: "NC(=O)OC(C)(C)C", NMe2: "N(C)C",
  CH2OH: "CO", OH: "O", CN: "C#N", "N(Boc)2": "N(C(=O)OC(C)(C)C)C(=O)OC(C)(C)C", Ph: "c1ccccc1", PPh3: "P(c1ccccc1)(c1ccccc1)(c1ccccc1)",
  // Read from the attachment atom with every valence used (condensed.ts condensedLabel): azide, nitro, nitrile,
  // isocyanate, sulfone, sulfonyl azide, ester and amide groups inside a label, which a left-to-right reading made
  // amines and alcohols (CH2N3 was C(N)(N)(N), with two H on each N).
  CH2N3: "CN=[N+]=[N-]", SO2N3: "S(=O)(=O)N=[N+]=[N-]", CON3: "C(=O)N=[N+]=[N-]", CH2NO2: "C[N+](=O)[O-]", CH2CN: "CC#N",
  CH2NCO: "CN=C=O", CH2NCS: "CN=C=S", CH2SCN: "CSC#N", SO2Me: "S(=O)(=O)C", SO2NH2: "S(=O)(=O)N", CH2CO2Me: "CC(=O)OC",
  CONHMe: "C(=O)NC", NHSO2Me: "NS(=O)(=O)C", CHN2: "C=[N+]=[N-]", PO3H2: "P(=O)(O)O", NCMe2: "N=C(C)C",
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
  "Pd(0)L2": "Pd(0)L_2", HNR2: "HNR_2", PdX2: "PdX_2", R2: "R2",
})) assert.equal(runs(t), want, t);
// A label of more than one line is text: no chemistry reads it (it counts as an unknown atom), and it is no element.
for (const t of ["Direct,\nNo ISC", "OMe\nCH3", "N\nH"]) assert.ok(labelSmiles(t) === undefined && !isElement(t), JSON.stringify(t));
console.log("labels.check: ok");

// Issue 44: the counts inside a bracket are subscripts on the canvas and in pictures, as the 2 after it is (and as
// ChemDraw draws the CDXML). Pieces keep the label's text in order; reading a label for its chemistry is unchanged.
const drawn = (label: string) => units(label).flatMap(pieces).map((u) => [u.text, u.count ?? ""]);
assert.deepEqual(drawn("N(CH3)2"), [["N", ""], ["(CH", "3"], [")", "2"]]);
assert.deepEqual(drawn("C(O)OCH3"), [["C", ""], ["(O)", ""], ["O", ""], ["C", ""], ["H", "3"]]);
assert.deepEqual(drawn("CH2CH(CH3)2"), [["C", ""], ["H", "2"], ["C", ""], ["H", ""], ["(CH", "3"], [")", "2"]]);
assert.deepEqual(drawn("Pd(PPh3)4"), [["Pd", ""], ["(PPh", "3"], [")", "4"]]);
assert.deepEqual(drawn("Fe(0)"), [["Fe", ""], ["(0)", ""]]); // an oxidation state is no count
for (const l of ["N(CH3)2", "C(O)OCH3", "CH2CH(CH3)2", "Pd(PPh3)4"]) assert.equal(drawn(l).flat().join(""), l);
assert.equal(labelSmiles("N(CH3)2"), "N(C)C");
// A label that leaves out what a chemist takes as read gets no double bond it does not write (Si=O, S≡C) and no
// O–O: it is read left to right as before.
for (const [label, smiles] of Object.entries({ SiOMe: "[Si]O(C)", SCMe: "SC(C)" })) assert.equal(labelSmiles(label), smiles, label);
assert.ok(!/OO|#/.test(labelSmiles("CCO2H") ?? ""), "CCO2H: no peroxide, no triple bond");
// Drawn: every digit of these labels is a subscript (75% size), read left to right and right to left.
{
  const pt = 4 / 3, L = 14.4 * pt, S = { bond: L, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
  const ink = (text: string): Ink => { const w = widthOf(text, S.size), a = 0.716 * S.size; return { width: w, ascent: a, outline: [[0, 0], [w, -a]] }; };
  for (const text of ["N(CH3)2", "C(O)OCH3", "CH2CH(CH3)2"]) for (const dx of [1, -1]) {
    const d = render({ atoms: [{ label: "C", location: [0, 0, 0] }, { label: text[0], text, location: [dx, 0, 0] }], bonds: [{ atoms: [0, 1], type: "single" }] } as never, S, ink, L);
    const small = d.labels.filter((l) => l.size < S.size * 0.9).map((l) => l.text).join(""), digits = text.replace(/\D/g, "");
    assert.equal([...small].sort().join(""), [...digits].sort().join(""), `${text} drawn ${dx > 0 ? "left to right" : "right to left"}: subscripts ${small}`);
    assert.equal(d.labels.map((l) => l.text).join("").length, text.length);
  }
}

// Superscript and subscript set by hand on part of a label (issue 44): drawn, not read. Fe with III raised reads as
// Fe(III) (iron, oxidation state III, no charge). A raised mass number (13CH3), a charge (NH4+) and a count stay.
{
  assert.equal(chemicalText("FeIII", [{ text: "Fe" }, { text: "III", script: "super" }]), "Fe(III)");
  assert.equal(chemicalText("CH2Rb", [{ text: "CH2R" }, { text: "b", script: "super" }]), "CH2R");
  assert.equal(chemicalText("OMea", [{ text: "OMe" }, { text: "a", script: "sub" }]), "OMe");
  assert.equal(chemicalText("13CH3", [{ text: "13", script: "super" }, { text: "CH3" }]), "13CH3");
  assert.equal(chemicalText("NH4+", [{ text: "NH" }, { text: "4", script: "sub" }, { text: "+", script: "super" }]), "NH4+");
  assert.equal(chemicalText("OH", [{ text: "OH", script: "super" }]), "OH"); // all raised: read as it is
  assert.equal(chemicalText("OMe", [{ text: "O", bold: true } as never, { text: "Me" }]), "OMe"); // no script: unchanged
  assert.equal(chemicalText("FeIII", [{ text: "Fe" }, { text: "II", script: "super" }]), "FeIII"); // runs that do not spell the text: as typed
  // Drawn: Fe in full size, III small and raised, after the Fe however the label reads.
  const pt = 4 / 3, L = 14.4 * pt, S = { bond: L, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
  const ink = (text: string): Ink => { const w = widthOf(text, S.size), a = 0.716 * S.size; return { width: w, ascent: a, outline: [[0, 0], [w, -a]] }; };
  for (const dx of [1, -1]) {
    const d = render({ atoms: [{ label: "C", location: [0, 0, 0] }, { label: "Fe", text: "FeIII", runs: [{ text: "Fe" }, { text: "III", script: "super" }], location: [dx, 0, 0] }], bonds: [{ atoms: [0, 1], type: "single" }] } as never, S, ink, L);
    const fe = d.labels.find((l) => l.text === "Fe")!, iii = d.labels.filter((l) => l !== fe);
    assert.ok(fe && iii.map((l) => l.text).join("") === "III", `FeIII drawn ${dx}`);
    for (const l of iii) {
      assert.ok(Math.abs(l.size - 0.75 * S.size) < 1e-6 && Math.abs(fe.size - S.size) < 1e-6, "III at 75%");
      assert.ok(l.y < fe.y - 0.2 * S.size, "III raised");
      assert.ok(l.x > fe.x, `III after Fe (${dx > 0 ? "left to right" : "right to left"})`);
    }
  }
  console.log("labels.check: superscript and subscript in labels ok");
}
