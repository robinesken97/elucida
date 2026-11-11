// Run: node src/sequence.check.ts. The sequence choices under the name field (src/sequence.ts): they read the ends from
// the text, typed or chosen, and write text that peptide.ts and nucleic.ts draw with those ends.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { sequenceParts, sequenceText } from "./sequence.ts";
import { peptideSmiles } from "./peptide.ts";
import { nucleicText } from "./nucleic.ts";

assert.deepEqual(sequenceParts("peptide: "), { kind: "peptide", codes: "", start: false, end: false });
assert.deepEqual(sequenceParts("peptide: Ac-ACD-NH2"), { kind: "peptide", codes: "ACD", start: true, end: true });
assert.deepEqual(sequenceParts("RNA: pACGUp"), { kind: "rna", codes: "ACGU", start: true, end: true });
assert.deepEqual(sequenceParts("dna: 5'-pATGC-3'"), { kind: "dna", codes: "ATGC", start: true, end: false });
assert.equal(sequenceParts("aspirin"), undefined);

// Every choice, before and after codes are typed, reads back the same and draws.
for (const kind of ["peptide", "rna", "dna"] as const)
  for (const start of [false, true])
    for (const end of [false, true])
      for (const codes of ["", kind === "peptide" ? "ACDG" : kind === "rna" ? "ACGU" : "ATGC"]) {
        const { text, caret } = sequenceText({ kind, codes, start, end });
        assert.deepEqual(sequenceParts(text), { kind, codes, start, end }, text);
        // Codes typed at the caret keep the ends.
        const typed = text.slice(0, caret) + (codes ? "" : kind === "peptide" ? "GG" : "AC") + text.slice(caret);
        assert.deepEqual({ ...sequenceParts(typed), codes: "" }, { kind, codes: "", start, end }, typed);
        if (kind === "peptide") assert.ok(peptideSmiles(typed), typed);
        else { const n = nucleicText(typed); assert.ok(n && "smiles" in n, typed); }
      }
assert.equal(peptideSmiles(sequenceText({ kind: "peptide", codes: "G", start: true, end: true }).text), "CC(=O)NCC(=O)N");
const n = nucleicText(sequenceText({ kind: "rna", codes: "A", start: true, end: false }).text);
assert.ok(n && "smiles" in n && n.smiles.startsWith("OP(=O)(O)OC"), "a 5'-phosphate");

// Residue labels: H–Ala–…–OH, or rA–P–rC. Each keeps its atoms, and the bonds say which atom each joins, so the
// labelled sequence is the same compound as the full structure (InChI, stereo too), at every end, and Expand Label
// draws a residue out.
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
await chem.ready;
const { residues } = await import("./sequence.ts");
const { nameToSmiles: named } = await import("./names.ts");
// As Return draws them: a peptide from peptide.ts (never OPSIN), RNA and DNA from nucleic.ts.
const nameToSmiles = (text: string) => peptideSmiles(text) ?? named(text);
const cases = ["peptide: ACDEFGHIKLMNPQRSTVWY", "peptide: Ac-GPW-NH2", "peptide: G", "peptide: PK-NH2", "rna: AACGUU", "rna: pACGUp", "dna: ATGC", "dna: pTp"];
for (const text of cases) {
  const full = chem.parseStructure(nameToSmiles(text)!), labelled = residues(full, text);
  assert.ok(labelled, `${text}: labelled`);
  assert.equal(chem.toInchi(labelled!), chem.toInchi(full), `${text}: the same compound`);
}
// Saved and opened again (.oct files and ChemDraw files are CDXML): still the same compound, labels and all.
const { toCdxml, fromCdxml } = await import("./cdxml.ts");
const { DEFAULT_STYLE } = await import("./docstyle.ts");
const { labelSmiles } = await import("./labels.ts");
const expand = (t: string) => { const m = labelSmiles(t); return m ? chem.parseStructure(m) : undefined; };
for (const text of cases) {
  const labelled = residues(chem.parseStructure(nameToSmiles(text)!), text)!, back = fromCdxml(toCdxml(labelled, DEFAULT_STYLE, { expand })).mol;
  assert.deepEqual(back.atoms.map((a) => a.text ?? a.label), labelled.atoms.map((a) => a.text ?? a.label), `${text}: labels saved`);
  assert.equal(chem.toInchi(back), chem.toInchi(labelled), `${text}: saved and opened`);
}
// Expand Label on each residue in turn: the full structure again.
const { expandLabel } = await import("./edit.ts");
for (const text of cases) {
  const full = chem.parseStructure(nameToSmiles(text)!);
  let m = residues(full, text)!;
  for (let i = m.atoms.length - 1; i >= 0; i--) if (m.atoms[i].inner) m = expandLabel(m, i, m.atoms[i].inner!);
  assert.ok(m.atoms.every((a) => !a.inner) && m.bonds.every((b) => !b.ports), `${text}: every residue drawn out`);
  assert.equal(chem.toInchi(m), chem.toInchi(full), `${text}: drawn out, the same compound`);
}
const ala = residues(chem.parseStructure(nameToSmiles("peptide: AG")!), "peptide: AG")!;
assert.deepEqual(ala.atoms.map((a) => a.text ?? a.label), ["H", "Ala", "Gly", "OH"]);
assert.deepEqual(residues(chem.parseStructure(nameToSmiles("rna: pAC")!), "rna: pAC")!.atoms.map((a) => a.text), ["P", "rA", "P", "rC"]);
// Contract Label on a drawn residue, bonded on both sides: the labels the Sequence tool draws, the same compound,
// saved and opened again too, and Expand Label gives the atoms back.
const { contractLabel } = await import("./edit.ts");
{
  const text = "peptide: GAV", full = chem.parseStructure(nameToSmiles(text)!);
  // Residue A is atoms 4 to 8 of the SMILES (G is 0 to 3): N, Cα, CH3, C, O.
  const m = contractLabel(full, 4, new Set([4, 5, 6, 7, 8]), "Ala");
  assert.equal(m.atoms.filter((x) => x.text === "Ala").length, 1);
  assert.equal(m.bonds.filter((b) => b.ports).length, 2, "both bonds keep the atom they join");
  assert.equal(chem.toInchi(m), chem.toInchi(full), "contracted, the same compound");
  assert.equal(chem.toInchi(fromCdxml(toCdxml(m, DEFAULT_STYLE, { expand })).mol), chem.toInchi(full), "contracted, saved and opened");
  const i = m.atoms.findIndex((x) => x.text === "Ala");
  assert.equal(chem.toInchi(expandLabel(m, i, m.atoms[i].inner!)), chem.toInchi(full), "drawn out again");
}
// Contract Label's suggestion for a residue in a drawn chain, and a residue label renamed (Ala to Gly, rA to rC): the
// new residue's atoms, each bond on its side. Any other name drops the kept atoms.
const { residueName, relabel } = await import("./sequence.ts");
{
  const full = chem.parseStructure(nameToSmiles("peptide: GAV")!);
  assert.equal(residueName(full, new Set([4, 5, 6, 7, 8]), chem.toInchi), "Ala");
  assert.equal(residueName(full, new Set([0, 1, 2, 3]), chem.toInchi), "Gly", "the first residue, its N-terminus capped as the amino acid");
  assert.equal(residueName(full, new Set([4, 5, 6]), chem.toInchi), undefined, "part of a residue is no residue");
  const m = residues(full, "peptide: GAV")!, i = m.atoms.findIndex((x) => x.text === "Ala");
  const gly = relabel(m, i, "Gly", chem.parseStructure)!;
  assert.equal(chem.toInchi(gly), chem.toInchi(chem.parseStructure(nameToSmiles("peptide: GGV")!)), "Ala renamed Gly");
  const rna = chem.parseStructure(nameToSmiles("rna: AAU")!), r = residues(rna, "rna: AAU")!, k = r.atoms.findIndex((x) => x.text === "rA");
  assert.equal(chem.toInchi(relabel(r, k, "rC", chem.parseStructure)!), chem.toInchi(chem.parseStructure(nameToSmiles("rna: CAU")!)), "rA renamed rC");
  assert.equal(relabel(m, i, "rC", chem.parseStructure), undefined, "a residue of another kind is not a rename");
  const { setLabel } = await import("./edit.ts");
  const ome = setLabel(m, i, "Xyz");
  assert.ok(!ome.atoms[i].inner && !ome.bonds.some((b) => b.ports && b.atoms.some((x, e) => x === i && b.ports![e] >= 0)), "another name drops the kept atoms");
}
// Saved as Octet saves (.oct, and .cdx with Octet's own data inside), copied as Octet's own data, as MOL and as SMILES:
// the same compound each time.
const { writeOct, readOct, writeCdx, readCdx } = await import("./oct.ts");
const { serialize, parse } = await import("./file.ts");
for (const text of ["peptide: Ac-GPW-NH2", "rna: pACGUp"]) {
  const full = chem.parseStructure(nameToSmiles(text)!), m = residues(full, text)!, want = chem.toInchi(full);
  assert.equal(chem.toInchi(readOct(writeOct(m, DEFAULT_STYLE, { expand })).mol), want, `${text}: .oct`);
  assert.equal(chem.toInchi(readCdx(writeCdx(m, DEFAULT_STYLE, { expand })).mol), want, `${text}: .cdx`);
  assert.equal(chem.toInchi(parse(serialize(m))), want, `${text}: Octet's own data`);
  assert.equal(chem.toInchi(chem.parseStructure(chem.toMolfile(m))), want, `${text}: MOL`);
  assert.equal(chem.toInchi(chem.toSmiles(m)), want, `${text}: SMILES`);
}
// A bond turned end to end keeps each link at its end; a damaged file's links are refused.
{
  const { flipBond } = await import("./edit.ts");
  const full = chem.parseStructure(nameToSmiles("peptide: GAV")!), m = residues(full, "peptide: GAV")!;
  assert.equal(chem.toInchi(m.bonds.reduce((x, _, k) => flipBond(x, k), m)), chem.toInchi(full), "every bond flipped");
  const bad = JSON.parse(serialize(m));
  bad.structure.bonds[1].ports = [99, -1];
  assert.throws(() => parse(JSON.stringify(bad)), /damaged/);
  const worse = JSON.parse(serialize(m));
  worse.structure.atoms[1].inner.bonds[0].atoms = [0, 999];
  assert.throws(() => parse(JSON.stringify(worse)), /damaged/);
}
// The names Contract Label suggests: one compound each.
const { residueTexts } = await import("./sequence.ts");
const keys = residueTexts().map(([smiles]) => chem.toInchi(smiles));
assert.equal(new Set(keys).size, keys.length, "each residue name is one compound");
// A preview laid out with its atoms in another order: the labels come from the SMILES read again.
const { residuesOf } = await import("./sequence.ts");
{
  const full = chem.parseStructure(nameToSmiles("peptide: AG")!), turned = { ...full, atoms: [...full.atoms].reverse() };
  assert.deepEqual(residuesOf("peptide: AG", turned, chem.parseStructure)!.atoms.map((x) => x.text ?? x.label), ["H", "Ala", "Gly", "OH"]);
}

// Atoms not in the order of the SMILES: drawn in full.
const shuffled = chem.parseStructure(nameToSmiles("peptide: AG")!);
assert.equal(residues({ ...shuffled, atoms: [...shuffled.atoms].reverse() }, "peptide: AG"), undefined);

// The editor shows the choices under the field while it holds a sequence.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /className="name-options"/);
assert.match(editor, /kind: k, start: false, end: false/, "another kind starts with the usual ends");
assert.match(editor, /onPointerDown=\{\(e\) => e\.preventDefault\(\)\}/, "the field keeps the focus");
console.log("sequence: ok");
