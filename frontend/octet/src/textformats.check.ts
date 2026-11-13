// Run: node src/textformats.check.ts. Fails loudly if File > More Formats' text formats break: CML (issue 78) and
// connection tables (issue 105) stop reading back as the same molecules, a hostile connection table reads, SLN (issue
// 120) is written wrongly for chains, branches, rings, charges, isotopes, radicals or stereo, or SLN or a connection
// table is written for what it cannot hold. Also that the four commands stay in File > More Formats.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { importStructure, parseStructure, ready, toCml, toInchi } = await import("./chem.ts");
const { fromCt, toCt, toSln } = await import("./textformats.ts");
type Mol = import("./render.ts").Mol;
await ready;

// CML: the molecules read back the same (stereo, charge, isotope, radical, E or Z, a metal), each atom where it was.
for (const s of ["C[C@H](N)C(=O)[O-].[13CH4].[CH3].C/C=C/C", "Cn1cnc2c1c(=O)n(C)c(=O)n2C", "Cl[Pd]P(c1ccccc1)(c1ccccc1)c1ccccc1"]) {
  const m = parseStructure(s), cml = toCml(m), back = importStructure(cml);
  assert.match(cml, /^<\?xml[^\n]*\n<cml>/);
  assert.equal(toInchi(back), toInchi(m), `${s} reads back from CML`);
  back.atoms.forEach((a, i) => assert.ok(Math.hypot(a.location[0] - m.atoms[i].location[0], a.location[1] - m.atoms[i].location[1]) < 1e-4, `${s}: atom ${i} keeps its place`));
}
// A written label goes as its atoms.
const toluene = parseStructure("Cc1ccccc1"), anisole: Mol = { ...toluene, atoms: toluene.atoms.map((a, i) => (i === 0 ? { ...a, text: "OMe" } : a)) };
assert.equal(toInchi(importStructure(toCml(anisole))), toInchi(parseStructure("COc1ccccc1")));

// A connection table: the title, the counts, x y z and the element, then each bond's atoms, order and a plain type.
const acid = toCt(parseStructure("CC(=O)O"), "acetic acid")!;
const lines = acid.split("\n");
assert.equal(lines[0], "acetic acid");
assert.equal(lines[1], " 4 3");
assert.match(lines[2], /^ +-?\d+\.\d{4} +-?\d+\.\d{4} +0\.0000 C$/);
assert.ok(lines.slice(6, 9).every((l) => /^ +\d+ +\d+ +[123] +0$/.test(l)), "a bond is its atoms, its order and type 0");
assert.ok(!acid.includes("-0.0000"));
// It reads back as the same molecule, a written label expanded; and a 3D table keeps its depth.
for (const m of [parseStructure("CC(=O)O"), parseStructure("C1CC2CCC1C2"), parseStructure("N#CC=C"), anisole]) assert.equal(toInchi(importStructure(fromCt(toCt(m)!))), toInchi(m));
assert.equal(importStructure(fromCt("x\n 2 1\n 0 0 0 C\n 1.5 0 1.5 O\n 1 2 1 0\n")).atoms[1].location[2]?.toFixed(3), "1.000");
// Symbols in capitals, an aromatic order (4) and a missing type column read.
assert.equal(toInchi(importStructure(fromCt("x\n 2 1\n 0 0 0 C\n 1 0 0 CL\n 1 2 1\n"))), toInchi(parseStructure("CCl")));
assert.equal(toInchi(importStructure(fromCt(`benzene\n 6 6\n${[0, 1, 2, 3, 4, 5].map((k) => ` ${Math.cos(k).toFixed(4)} ${Math.sin(k).toFixed(4)} 0 C`).join("\n")}\n${[1, 2, 3, 4, 5, 6].map((k) => ` ${k} ${(k % 6) + 1} 4 0`).join("\n")}\n`))), toInchi(parseStructure("c1ccccc1")));
// A hostile table does not read: no counts, too many atoms, too few lines, no element, no place or one too far, a bond
// to no atom or to its own atom, an order of 5.
for (const t of ["", "x\n", "x\n 1000 0\n", "x\n 1 0\n", "x\n 1 0\n 0 0 0 Xx\n", "x\n 1 0\n NaN 0 0 C\n", "x\n 1 0\n 0 1e9 0 C\n", "x\n 2 1\n 0 0 0 C\n 1 0 0 O\n 1 3 1 0\n",
  "x\n 2 1\n 0 0 0 C\n 1 0 0 O\n 1 1 1 0\n", "x\n 2 1\n 0 0 0 C\n 1 0 0 O\n 1 2 5 0\n", "x\n -1 0\n", "x\n 1.5 0\n 0 0 0 C\n"]) assert.throws(() => fromCt(t), /It is not a connection table\./, JSON.stringify(t));
// A line is split into the fields it needs only: a 16 MB line of fields is refused at once (split whole, it took 250 ms,
// and a 64 MB file 1.4 s and 1.5 GB).
const long = `x\n 1 0\n${"0 ".repeat(8e6)}C\n`, start = performance.now();
assert.throws(() => fromCt(long), /It is not a connection table\./);
assert.ok(performance.now() - start < 50, "a long line is refused at once");

// SLN: hydrogens on their atom, = # :, branches, rings (one number for each ring atom, closed by @), structures apart.
const sln = (s: string) => toSln(parseStructure(s));
const cases: [string, string][] = [
  ["CCO", "CH3CH2OH"], ["CC(=O)O", "CH3C(=O)OH"], ["CN(C)C", "CH3N(CH3)CH3"], ["C#N", "CH#N"],
  ["C1CCCCC1", "C[1]H2CH2CH2CH2CH2CH2@1"], ["c1ccccc1", "C[1]H=CHCH=CHCH=CH@1"], ["C12CC1C2", "C[1]HCH2CH@1CH2@1"],
  ["C1CC2CCC1C2", "C[1]H2CH2C[2]HCH2CH2CH@1CH2@2"], ["C1CC12CC2", "C[1]H2CH2C[2]@1CH2CH2@2"],
  // Charges, an isotope and radicals in brackets after the atom, before its hydrogens.
  ["[NH4+]", "N[+]H4"], ["CC(=O)[O-]", "CH3C(=O)O[-]"], ["[Na+].[Cl-]", "Na[+].Cl[-]"], ["[Fe+2]", "Fe[+2]"], ["[13CH4]", "C[I=13]H4"], ["[CH3]", "C[*]H3"],
  // The ring number first, then the charge, then the rest.
  ["C[N+]1(C)CCCC1", "CH3N[1:+](CH3)CH2CH2CH2CH2@1"], ["[15NH4+]", "N[+;I=15]H4"],
  // Hydrogens drawn as atoms: plain ones join their atom's count; a deuterium stays an atom, after a single bond written
  // out, as does an atom whose symbol starts with H.
  ["[H][C@](F)(Cl)Br", "C[s=S]H(F)(Cl)Br"], ["[2H]C([2H])([2H])O", "H[I=2]C(-H[I=2])(-H[I=2])OH"], ["C[Hg]C", "CH3-HgCH3"], ["[H][H]", "H-H"],
  // R and S on centres (with a ring number before them), E and Z on double bonds.
  ["C[C@H](N)C(=O)O", "CH3C[s=S]H(NH2)C(=O)OH"], ["C/C=C/C", "CH3CH=[s=E]CHCH3"], ["C/C=C\\C", "CH3CH=[s=Z]CHCH3"],
  ["C[C@H]1CCCO1", "CH3C[1:s=S]HCH2CH2CH2O@1"],
];
for (const [s, want] of cases) assert.equal(sln(s), want, s);
// Refused: an atom that is no element, a quadruple bond, an and or or group, a pseudo-asymmetric centre (SLN's s= cannot
// tell r from R), a stereo axis. An absolute group is written.
const ala = parseStructure("C[C@H](N)C(=O)O"), at = (m: Mol, i: number, more: object): Mol => ({ ...m, atoms: m.atoms.map((a, k) => (k === i ? { ...a, ...more } : a)) });
assert.equal(toSln(at(ala, 2, { label: "R", text: "R1" })), undefined);
assert.equal(toCt(at(ala, 2, { label: "R", text: "R1" })), undefined);
assert.equal(toSln({ ...ala, bonds: ala.bonds.map((b, k) => (k === 0 ? { ...b, type: 14 } : b)) }), undefined);
assert.equal(toSln(at(ala, 1, { enhanced: "&1" })), undefined);
assert.equal(toSln(at(ala, 1, { enhanced: "or1" })), undefined);
assert.equal(toSln(at(ala, 1, { enhanced: "abs" })), "CH3C[s=S]H(NH2)C(=O)OH");
assert.equal(sln("C[C@H]1CC[C@@H](C)CC1"), undefined);
assert.equal(sln("Cc1cccc(C)c1-c1c(C)cccc1C"), "CH3C[1]=CHCH=CHC(CH3)=C@1C[2]=C(CH3)CH=CHCH=C@2CH3", "a biaryl with no wedge has no axis");

// The commands: in File > More Formats, written through Export's Save dialog, read through Import, SLN through Copy As.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), exportRs = readFileSync(new URL("../src-tauri/src/export.rs", import.meta.url), "utf8"), main = readFileSync(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8");
assert.match(editor, /\["more_cml", "Export CML…", <BracketsAngle size=\{18\} \/>, \(\) => checkFirst\(\(\) => void exportText\("cml"\)\)\],/);
assert.match(editor, /\["more_ct_import", "Import a Connection Table…", <TrayArrowDown size=\{18\} \/>, \(\) => void importFile\(true\)\],/);
assert.match(editor, /\["more_ct_export", "Export Connection Table…", <TrayArrowUp size=\{18\} \/>, \(\) => checkFirst\(\(\) => void exportText\("ct"\)\)\],/);
assert.match(editor, /\["more_sln", "Copy as SLN", <Quotes size=\{18\} \/>, \(\) => copyAs\("sln"\)\],/);
assert.match(editor, /sln: \["SLN", \(m\) => toSln\(m\) \?\? ""\]/);
assert.match(editor, /if \(f === "cml"\) return toCml\(part\);\n\s+if \(f === "ct"\) return toCt\(part, name\);/);
assert.match(editor, /invoke<\[string, string\] \| null>\("import_structure", \{ ct \}\)/);
assert.match(editor, /importStructure\(ct \? fromCt\(picked\[1\]\) : picked\[1\]\)/);
assert.match(editor, /exportFile\(\{ name, format: f, mdl: text \}\)/);
assert.match(exportRs, /\("cml", "Chemical Markup Language \(CML\)", &\["cml"\]\),\n\s+\("ct", "Connection Table \(CT\)", &\["ct"\]\),/);
assert.match(main, /if ct == Some\(true\) \{ \("Connection Table \(CT\)", &\["ct"\]\) \}/);
console.log("textformats.check: CML, connection tables and SLN ok");
