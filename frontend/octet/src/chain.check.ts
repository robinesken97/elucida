// Run: node src/chain.check.ts. Peptides and oligonucleotides along a straight backbone (src/chain.ts, issues 27 and
// 99): the Sequence tool draws them so (chem.ts fullMol) and Clean Up lays out a drawn one so (cleanUp), the backbone a
// level zigzag on two heights, a peptide's side chains above and below by turns, the bases of RNA and DNA all on one
// side, and the same compound every time (stereochemistry too). A chain whose side chains bond to each other (a
// disulfide) or that closes a ring is left to the usual clean-up, and a sequence of residue labels goes back into rows.
// HELM and FASTA in and out (src/helm.ts). Laying out a chain costs Clean Up next to nothing.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type { Mol } from "./render.ts";

const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
await chem.ready;
const { chainLayout } = await import("./chain.ts");
const { fragments } = await import("./edit.ts");
const { peptideSmiles } = await import("./peptide.ts");
const { nucleicText } = await import("./nucleic.ts");
const { residues } = await import("./sequence.ts");
const { readSequence, toFasta, toHelm } = await import("./helm.ts");

const smilesOf = (text: string) => peptideSmiles(text) ?? (nucleicText(text) as { smiles: string }).smiles;
const drawn = (text: string) => chem.fullMol(smilesOf(text));
// Drawn by hand: Indigo's own layout, each atom moved up to 0.3 bond lengths.
let seed = 7;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) * 2 - 1;
const byHand = (text: string): Mol => { const m = chem.parseStructure(smilesOf(text), false); return { ...m, atoms: m.atoms.map((a) => ({ ...a, location: [a.location[0] + rnd() * 0.3, a.location[1] + rnd() * 0.3, 0] })) }; };
const near = (m: Mol, i: number) => m.bonds.flatMap((b) => (b.atoms[0] === i ? [b.atoms[1]] : b.atoms[1] === i ? [b.atoms[0]] : []));
const y = (m: Mol, i: number) => m.atoms[i].location[1];
// A peptide's backbone: each N–Cα–C(=O) and its Cα's side chain atom, in order along the chain.
const carbonyl = (m: Mol, c: number) => m.atoms[c].label === "C" && m.bonds.some((b) => b.type === 2 && b.atoms.includes(c) && m.atoms[b.atoms[0] === c ? b.atoms[1] : b.atoms[0]].label === "O");
function backbone(m: Mol) {
  const out: { n: number; a: number; c: number; side?: number }[] = [];
  m.atoms.forEach((_, a) => {
    const n = near(m, a).find((j) => m.atoms[j].label === "N"), c = near(m, a).find((j) => carbonyl(m, j));
    if (m.atoms[a].label === "C" && n !== undefined && c !== undefined) out.push({ n, a, c, side: near(m, a).find((j) => j !== n && j !== c) });
  });
  return out.sort((p, q) => m.atoms[p.a].location[0] - m.atoms[q.a].location[0]);
}
// The heights the atoms lie at.
const levels = (m: Mol, atoms: number[]) => { const ys = atoms.map((i) => y(m, i)), low = Math.min(...ys); return [...new Set(ys.map((v) => Math.round((v - low) * 100)))].length; };

// The Sequence tool's peptide: the backbone on two heights, the side chains by turns above and below it, the same
// compound as the SMILES (each stereocentre too). So is the same peptide drawn by hand and cleaned up.
for (const [how, make] of [["drawn", drawn], ["cleaned up", (t: string) => chem.cleanUp(byHand(t))]] as const) {
  const text = "peptide: Ac-AFWKRYIT-NH2", m = make(text), bb = backbone(m);
  assert.equal(bb.length, 8, `${how}: eight residues`);
  assert.equal(levels(m, bb.flatMap((r) => [r.n, r.a, r.c])), 2, `${how}: the backbone on two heights`);
  assert.ok(bb.every((r, k) => Math.sign(y(m, r.side!) - y(m, r.a)) === (k % 2 ? -1 : 1) * Math.sign(y(m, bb[0].side!) - y(m, bb[0].a))), `${how}: side chains by turns`);
  assert.equal(chem.toInchi(m), chem.toInchi(smilesOf(text)), `${how}: the same compound`);
}
// A proline's ring on the other side from the side chain before it; RNA's and DNA's bases all on one side, above the
// backbone; each the same compound, drawn and cleaned up.
{
  const m = drawn("peptide: KPW"), bb = backbone(m), ring = near(m, bb[1].n).find((j) => j !== bb[0].c && j !== bb[1].a)!;
  assert.ok(Math.sign(y(m, ring) - y(m, bb[1].n)) !== Math.sign(y(m, bb[0].side!) - y(m, bb[0].a)), "proline's ring opposite lysine's side chain");
  assert.equal(chem.toInchi(m), chem.toInchi(smilesOf("peptide: KPW")));
}
for (const text of ["rna: pACGU", "dna: GATTACAp"]) for (const m of [drawn(text), chem.cleanUp(byHand(text))]) {
  const p = m.atoms.flatMap((a, i) => (a.label === "P" ? [i] : [])), c1 = m.atoms.flatMap((a, i) => (a.label === "C" && near(m, i).some((j) => m.atoms[j].label === "N") && near(m, i).some((j) => m.atoms[j].label === "O" && near(m, j).length === 2) ? [i] : []));
  assert.equal(c1.length, text.replace(/^\w+: p?|p$/g, "").length, `${text}: a sugar for each base`);
  assert.ok(Math.max(...c1.map((i) => y(m, i))) - Math.min(...c1.map((i) => y(m, i))) < 0.05, `${text}: the sugars side by side`);
  assert.ok(c1.every((i) => p.every((j) => y(m, i) > y(m, j))), `${text}: the bases above the backbone`);
  assert.equal(chem.toInchi(m), chem.toInchi(smilesOf(text)), `${text}: the same compound`);
}
// Clean Up again leaves the chain as it is: a threonine's OH and CH3, a histidine's ring and a thymine's ring keep their
// sides.
for (const text of ["peptide: Ac-TVLHWKT-NH2", "dna: GATTACAp"]) {
  const once = chem.cleanUp(drawn(text)), twice = chem.cleanUp(once);
  assert.ok(once.atoms.every((a, i) => Math.hypot(a.location[0] - twice.atoms[i].location[0], a.location[1] - twice.atoms[i].location[1]) < 0.2), `${text}: Clean Up again`);
}
// No atom goes on another: an α-benzylproline's benzyl keeps clear of its ring, and a layout that would put an N-methyl
// on the phenyl before it is not used. Each is the same compound, drawn and cleaned up.
for (const smiles of ["C[C@H]([C@@H](C(=O)N1CCC[C@H]1C(=O)N2CCC[C@@]2(Cc3ccccc3)C(=O)N[C@@H]([C@@H](C)O)C(=O)N)N)O", "C[C@H](C(=O)NCC(=O)N[C@@H](Cc1ccccc1)C(=O)N(C)[C@@H](CCSC)C(=O)N)NC(=O)[C@H](Cc1ccc(O)cc1)N"]) {
  for (const m of [chem.fullMol(smiles), chem.cleanUp(chem.parseStructure(smiles, false))]) {
    assert.ok(m.atoms.every((a, i) => m.atoms.every((b, j) => j <= i || Math.hypot(a.location[0] - b.location[0], a.location[1] - b.location[1]) > 0.3)), `${smiles}: no atom on another`);
    assert.equal(chem.toInchi(m), chem.toInchi(smiles), `${smiles}: the same compound`);
  }
}
{
  const m = chem.parseStructure("CC(=O)N1CCC[C@@]1(Cc1ccccc1)C(=O)N[C@@H](C)C(=O)N[C@@H](C)C(=O)N", false);
  assert.ok(chainLayout(m, fragments(m)[0]), "an α-benzylproline along a straight backbone");
}
// Left to the usual clean-up: a dipeptide, two cysteines joined by a disulfide, a cyclic peptide, and any other
// structure.
for (const smiles of ["N[C@@H](C)C(=O)N[C@@H](C)C(=O)O", "N[C@@H](CS1)C(=O)NCC(=O)N[C@@H](CS1)C(=O)O", "O=C1CNC(=O)CNC(=O)CNC(=O)CN1", "Cn1cnc2c1c(=O)n(C)c(=O)n2C"]) {
  const m = chem.parseStructure(smiles);
  assert.equal(chainLayout(m, fragments(m)[0]), undefined, smiles);
}
// Residue labels moved about by hand go back into rows of ten, from the H end.
{
  const text = "peptide: Ac-ACDEFGHIKLMNPQ-NH2", rows = residues(chem.parseStructure(smilesOf(text)), text)!;
  const moved = { ...rows, atoms: rows.atoms.map((a) => ({ ...a, location: [a.location[0] + rnd() * 1.5, a.location[1] + rnd() * 1.5, 0] as [number, number, number] })) };
  const m = chem.cleanUp(moved), at = (k: number) => m.atoms[k].location;
  assert.ok(rows.atoms.every((_, k) => Math.abs(at(k)[0] - at(0)[0] - rows.atoms[k].location[0]) < 1e-9 && Math.abs(at(k)[1] - at(0)[1] - rows.atoms[k].location[1]) < 1e-9), "back in rows");
  assert.equal(chem.toInchi(m), chem.toInchi(rows), "the same compound");
}

// HELM and FASTA in: the Sequence tool's text, or why not.
assert.deepEqual(readSequence("PEPTIDE1{I.C.E.C.R.E.A.M.S.A.N.D.W.I.C.H}$$$$"), { text: "peptide: ICECREAMSANDWICH" });
assert.deepEqual(readSequence("PEPTIDE1{[ac].A.C.[am]}$$$$V2.0"), { text: "peptide: Ac-AC-NH2" });
assert.deepEqual(readSequence("RNA1{P.R(A)P.R(C)P.R(G)}$$$$"), { text: "rna: pACG" });
assert.deepEqual(readSequence("RNA1{[dR](A)P.[dR](T)P}$$$$V2.0"), { text: "dna: ATp" });
assert.deepEqual(readSequence("PEPTIDE1{A.[Aib].C}$$$$"), { problem: "Octet does not know the HELM monomer [Aib]." });
assert.ok("problem" in readSequence("PEPTIDE1{C.A.C}$PEPTIDE1,PEPTIDE1,1:R3-3:R3$$$")!, "a disulfide");
assert.ok("problem" in readSequence("RNA1{R(A)P.[dR](T)}$$$$")!, "RNA and DNA in one chain");
assert.deepEqual(readSequence("RNA1{R(A)P.R(T)}$$$$"), { problem: "Octet does not know the HELM monomer R(T)." }, "ribothymidine is not rU");
assert.deepEqual(readSequence("RNA1{[dR](U)P.[dR](A)}$$$$"), { problem: "Octet does not know the HELM monomer [dR](U)P." }, "deoxyuridine is not dT");
assert.deepEqual(readSequence(">sp|P01308|INS_HUMAN Insulin\nMALWMRLLPL\nLALLALWGPD\n"), { text: "peptide: MALWMRLLPLLALLALWGPD" });
assert.deepEqual(readSequence(">a DNA\nacgttgca\n>another\nAAA"), { text: "dna: ACGTTGCA" }, "the first record");
assert.deepEqual(readSequence(">an RNA\nACGUU"), { text: "rna: ACGUU" });
for (const text of ["ACGT", "aspirin", "CCO", ""]) assert.equal(readSequence(text), undefined, text);
// HELM and FASTA out, drawn out and as residue labels, read back as the same compound.
for (const text of ["peptide: Ac-ACDEFGHIKLMNPQRSTVWY-NH2", "peptide: GPG", "rna: pACGU", "dna: GATTACAp"]) {
  const full = drawn(text), labels = residues(chem.parseStructure(smilesOf(text)), text)!;
  const helm = toHelm(full, chem.toInchi, chem.toSmiles)!, back = readSequence(helm) as { text: string };
  assert.equal(toHelm(labels, chem.toInchi, chem.toSmiles), helm, `${text}: HELM, as labels too`);
  assert.equal(chem.toInchi(smilesOf(back.text)), chem.toInchi(full), `${text}: HELM read back is the same compound`);
  assert.equal(toFasta(full, chem.toInchi), text.replace(/^\w+: (Ac-|p)?|(-NH2|p)$/g, ""), `${text}: FASTA`);
  assert.equal(toFasta(labels, chem.toInchi), toFasta(full, chem.toInchi), `${text}: FASTA, as labels too`);
}
assert.equal(toHelm(drawn("rna: AC"), chem.toInchi, chem.toSmiles), "RNA1{R(A)P.R(C)}$$$$V2.0");
// A residue Octet does not know (N-methylalanine) is written as SMILES with its links, its stereocentre kept, and an
// end it does not know (a methyl ester) joins its residue. FASTA has X for each.
{
  const m = chem.fullMol("CC(=O)N[C@@H](C)C(=O)N(C)[C@@H](C)C(=O)NCC(=O)OC");
  const helm = toHelm(m, chem.toInchi, chem.toSmiles)!, own = /^PEPTIDE1\{\[ac\]\.A\.\[(.*?)\]\.\[(.*)\]\}\$\$\$\$V2\.0$/.exec(helm);
  assert.ok(own, helm);
  assert.equal(chem.toInchi(own[1].replace("[*:1]", "[H]").replace("[*:2]", "O")), chem.toInchi("CN[C@@H](C)C(=O)O"), "N-methyl-L-alanine");
  assert.equal(chem.toInchi(own[2].replace("[*:1]", "[H]")), chem.toInchi("NCC(=O)OC"), "glycine methyl ester");
  assert.equal(toFasta(m, chem.toInchi), "AXX");
}
assert.equal(toHelm(chem.parseStructure("Cn1cnc2c1c(=O)n(C)c(=O)n2C"), chem.toInchi, chem.toSmiles), undefined, "caffeine is no chain");

// Pasting HELM or FASTA, on the canvas or in the name field, opens the sequence; Edit > Copy As has HELM (⌥⌘E on the
// Mac) and FASTA.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), menu = readFileSync(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8");
assert.equal(editor.match(/if \(text && pasteSequence\(text\)\) return/g)?.length, 2, "both paste paths");
assert.match(editor, /onPaste=\{\(e\) => \{ if \(pasteSequence\(e\.clipboardData\.getData\("text\/plain"\), true\)\) e\.preventDefault\(\); \}\}/);
assert.match(editor, /el === nameField\.current && pasteSequence\(c\.text, true\)/, "Edit > Paste on Linux too");
assert.match(editor, /helm: \["HELM", \(m\) => toHelm\(m, toInchi, toSmiles\) \?\? ""\], fasta: \["FASTA", \(m\) => toFasta\(m, toInchi\) \?\? ""\]/);
assert.match(menu, /item\("copy_helm", "HELM", if cfg!\(target_os = "macos"\) \{ "Alt\+CmdOrCtrl\+E" \} else \{ "" \}\)/);
assert.match(menu, /item\("copy_fasta", "FASTA", ""\)/);

// Cost: finding no chain in a structure that has none, and laying out a 60-residue peptide.
const time = (run: () => unknown, n: number) => { run(); const t = performance.now(); for (let k = 0; k < n; k++) run(); return (performance.now() - t) / n; };
const taxol = chem.parseStructure("CC1=C2C(C(=O)C3(C)C(CC4OCC4(OC(C)=O)C3C(OC(=O)c5ccccc5)C(O)(CC1OC(=O)C(O)C(NC(=O)c6ccccc6)c7ccccc7)C2(C)C)O)OC(C)=O");
const long = chem.parseStructure(smilesOf(`peptide: ${"ACDEFGHIKLMNPQRSTVWY".repeat(3)}`), false);
const none = time(() => chainLayout(taxol, fragments(taxol)[0]), 200), sixty = time(() => chainLayout(long, fragments(long)[0]), 20);
assert.ok(none < 0.5, `no chain in taxol: ${none.toFixed(3)} ms`);
assert.ok(sixty < 30, `a 60-residue peptide: ${sixty.toFixed(1)} ms`);
console.log(`chain: ok (no chain found in ${none.toFixed(3)} ms, a 60-residue peptide laid out in ${sixty.toFixed(1)} ms)`);
