// Run: node src/nucleic.check.ts. RNA and DNA typed as one-letter codes (src/nucleic.ts): "rna: AACGUU" and
// "dna: ATGC" in Name to Structure give the oligonucleotide, 5'-OH to 3'-OH, with D-ribose (or 2-deoxy-D-ribose) β on
// each base. Bad letters are named, more than 30 nucleotides are refused, and Structure > Insert RNA… and Insert DNA…
// open the name field ready for codes, as Insert Peptide… does.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { MAX_NUCLEOTIDES, nucleicProblem, nucleicSmiles, nucleicText } from "./nucleic.ts";

// The text.
const smiles = (text: string, dna = false) => { const r = nucleicSmiles(text, dna); assert.ok(r && "smiles" in r, `${text} reads`); return r.smiles; };
assert.equal(nucleicSmiles("", false), undefined);
assert.equal(smiles("A C G U"), smiles("ACGU"), "spaces are left out");
assert.equal(smiles("acgu"), smiles("ACGU"), "codes in either case");
assert.equal(smiles("ACGT"), smiles("ACGU"), "T in RNA is U, as ChemDraw's FASTA RNA");
assert.equal(smiles("ACGU", true), smiles("ACGT", true), "U in DNA is T, as ChemDraw's FASTA DNA");
assert.equal(smiles("5'-ACGU-3'"), smiles("ACGU"), "5'- and -3' round the codes");
assert.equal(smiles("5’-ACGU-3’"), smiles("ACGU"), "with a curly apostrophe");
assert.equal(smiles("pACGU"), `OP(=O)(O)${smiles("ACGU")}`, "p before: a 5'-phosphate");
assert.equal(smiles("5'-pACGU-3'"), smiles("pACGU"));
assert.equal(smiles("ACGUp"), `${smiles("ACGU")}P(=O)(O)O`, "p after: a 3'-phosphate");
assert.deepEqual(nucleicSmiles("ABCU", false), { problem: "Not a nucleotide: B" });
assert.deepEqual(nucleicSmiles("AXCZN", true), { problem: "Not nucleotides: X, Z, N" });
assert.deepEqual(nucleicSmiles("AC-GU", false), { problem: "Not a nucleotide: -" });
assert.deepEqual(nucleicSmiles("5'-", false), { problem: "Type the bases, for example AACGUU." });
assert.deepEqual(nucleicSmiles("p", true), { problem: "Type the bases, for example ATGC." });
assert.ok("smiles" in nucleicSmiles("A".repeat(MAX_NUCLEOTIDES), false)!, "30 nucleotides");
assert.deepEqual(nucleicSmiles("A".repeat(MAX_NUCLEOTIDES + 1), false), { problem: "Up to 30 nucleotides." });
// Only after "rna:" or "dna:", so a word of capitals (CAT, ACG) is never a sequence.
assert.equal(nucleicText("CAT"), undefined);
assert.deepEqual(nucleicText("RNA:ACGU"), { smiles: smiles("ACGU") });
assert.deepEqual(nucleicText("dna: ACGT"), { smiles: smiles("ACGT", true) });
assert.equal(nucleicProblem("rna: "), undefined, "no message before any code is typed");
assert.equal(nucleicProblem("dna: AB"), "Not a nucleotide: B");
assert.equal(nucleicProblem("aspirin"), undefined);

// The menu items and the Sequence tool (peptide.check.ts) open the name field with the prefix in it, and the field
// says why codes are refused. Codes never go to PubChem and are never corrected to a name.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /insert_rna: \(\) => insertSequence\("rna: "\),/);
assert.match(editor, /insert_dna: \(\) => insertSequence\("dna: "\),/);
assert.match(editor, /peptideProblem\(naming\) \?\? nucleicProblem\(naming\)/);
assert.match(editor, /PEPTIDE\.test\(s\) \|\| NUCLEIC\.test\(s\) \|\| looksLikeSmiles\(s\)\) return false;/);
assert.match(readFileSync(new URL("names.ts", import.meta.url), "utf8"), /PEPTIDE\.test\(s\) \|\| NUCLEIC\.test\(s\) \|\| nameToSmiles\(s\)\) return undefined;/);
const menu = readFileSync(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8");
assert.match(menu, /item\("insert_peptide", "Insert Peptide…", ""\)\?,\n\s+&item\("insert_rna", "Insert RNA…", ""\)\?,\n\s+&item\("insert_dna", "Insert DNA…", ""\)\?,/);

// Through Name to Structure, as the editor draws it. The reference InChIs are OPSIN's for the systematic names
// (adenylyl-(3'→5')-…-uridine), so the SMILES built here is checked against a structure made another way. Adenosine's
// is PubChem's (CID 60961): β-D-ribofuranose, (2R,3R,4S,5R).
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
await chem.ready;
const { nameToSmiles } = await import("./names.ts");
const { nameList } = await import("./dictionary.ts");
const drawn = (text: string) => chem.parseStructure(nameToSmiles(text)!);
const inchi = (text: string) => chem.toInchi(drawn(text));
const formula = (text: string) => chem.analyse(drawn(text))?.[0].formula;

assert.equal(nameList("rna: AC GU", nameToSmiles), undefined, "a sequence is one structure, not a list");
assert.equal(inchi("rna: A"), "InChI=1S/C10H13N5O4/c11-8-5-9(13-2-12-8)15(3-14-5)10-7(18)6(17)4(1-16)19-10/h2-4,6-7,10,16-18H,1H2,(H2,11,12,13)/t4-,6-,7-,10-/m1/s1", "rna: A is adenosine");
assert.equal(inchi("dna: T"), "InChI=1S/C10H14N2O5/c1-5-3-12(10(16)11-9(5)15)8-2-6(14)7(4-13)17-8/h3,6-8,13-14H,2,4H2,1H3,(H,11,15,16)/t6-,7+,8+/m0/s1", "dna: T is thymidine");
assert.equal(formula("rna: AACGUU"), "C57H71N22O40P5");
assert.equal(inchi("rna: AACGUU"), "InChI=1S/C57H71N22O40P5/c58-24-1-4-74(55(91)69-24)49-33(86)38(20(111-49)9-106-123(100,101)118-40-22(113-52(35(40)88)78-16-67-28-43(60)63-14-65-45(28)78)11-105-121(96,97)115-37-18(7-80)109-51(32(37)85)77-15-66-27-42(59)62-13-64-44(27)77)117-122(98,99)108-12-23-41(36(89)53(114-23)79-17-68-29-46(79)72-54(61)73-47(29)90)119-124(102,103)107-10-21-39(34(87)50(112-21)76-6-3-26(82)71-57(76)93)116-120(94,95)104-8-19-30(83)31(84)48(110-19)75-5-2-25(81)70-56(75)92/h1-6,13-23,30-41,48-53,80,83-89H,7-12H2,(H,94,95)(H,96,97)(H,98,99)(H,100,101)(H,102,103)(H2,58,69,91)(H2,59,62,64)(H2,60,63,65)(H,70,81,92)(H,71,82,93)(H3,61,72,73,90)/t18-,19-,20-,21-,22-,23-,30-,31-,32-,33-,34-,35-,36-,37-,38-,39-,40-,41-,48-,49-,50-,51-,52-,53-/m1/s1");
assert.equal(formula("dna: ATGC"), "C39H50N15O22P3");
assert.equal(inchi("dna: ATGC"), "InChI=1S/C39H50N15O22P3/c1-16-8-52(39(60)50-35(16)57)27-6-19(23(72-27)11-68-78(63,64)74-18-5-28(70-21(18)9-55)53-14-45-30-32(41)43-13-44-33(30)53)75-79(65,66)69-12-24-20(7-29(73-24)54-15-46-31-34(54)48-37(42)49-36(31)58)76-77(61,62)67-10-22-17(56)4-26(71-22)51-3-2-25(40)47-38(51)59/h2-3,8,13-15,17-24,26-29,55-56H,4-7,9-12H2,1H3,(H,61,62)(H,63,64)(H,65,66)(H2,40,47,59)(H2,41,43,44)(H,50,57,60)(H3,42,48,49,58)/t17-,18-,19-,20-,21+,22+,23+,24+,26+,27+,28+,29+/m0/s1");
assert.equal(nameToSmiles("rna: ABC"), undefined, "bad letters draw nothing");
assert.equal(nameToSmiles(`dna: ${"A".repeat(31)}`), undefined, "31 nucleotides draw nothing");
// The longest drawn as the editor draws it, timed.
const t = performance.now(), longest = drawn(`rna: ${"ACGU".repeat(8).slice(0, MAX_NUCLEOTIDES)}`);
console.log(`nucleic: a ${MAX_NUCLEOTIDES}-mer of RNA (${longest.atoms.length} atoms) drawn in ${Math.round(performance.now() - t)} ms`);

// Against OPSIN, with OPSIN built: every nucleoside, the 5'- and 3'-phosphates, and the two sequences by name.
const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("nucleic: ok (OPSIN comparison skipped, no OPSIN build)"); process.exit(0); }
const pack = readFileSync(new URL("opsin-data.bin", dir)), files = new Map<string, Int8Array>();
for (let p = 0; ; ) {
  const n = pack.readUInt16BE(p); p += 2;
  if (!n) break;
  const name = pack.toString("latin1", p, p + n); p += n;
  const size = pack.readInt32BE(p); p += 4;
  files.set(name, new Int8Array(pack.buffer, pack.byteOffset + p, size)); p += size;
}
gl.opsinResource = (name: string) => files.get(name) ?? null;
const opsin = await import(new URL("opsin.js", dir).href);
opsin.init();
const named = (name: string) => chem.toInchi(chem.parseStructure(opsin.parseToSmiles(name), false));
for (const [text, name] of [
  ["rna: A", "adenosine"], ["rna: G", "guanosine"], ["rna: C", "cytidine"], ["rna: U", "uridine"],
  ["dna: A", "2'-deoxyadenosine"], ["dna: G", "2'-deoxyguanosine"], ["dna: C", "2'-deoxycytidine"], ["dna: T", "thymidine"],
  ["rna: pA", "adenosine 5'-monophosphate"], ["rna: Ap", "adenosine 3'-monophosphate"], ["dna: pT", "thymidine 5'-monophosphate"],
  ["rna: AU", "adenylyl-(3'->5')-uridine"],
  ["rna: AACGUU", "adenylyl-(3'->5')-adenylyl-(3'->5')-cytidylyl-(3'->5')-guanylyl-(3'->5')-uridylyl-(3'->5')-uridine"],
  ["dna: ATGC", "2'-deoxyadenylyl-(3'->5')-thymidylyl-(3'->5')-2'-deoxyguanylyl-(3'->5')-2'-deoxycytidine"],
]) assert.equal(inchi(text), named(name), `${text} is ${name}`);
console.log("nucleic: ok");
