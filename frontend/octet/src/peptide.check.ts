// Run: node src/peptide.check.ts. Peptides typed as one-letter codes (issue 27, src/peptide.ts): "peptide: ACDEFG" in
// Name to Structure gives the structure of the three-letter sequence, bad letters and more than 60 residues are
// refused with a short message, and Structure > Insert Peptide… opens the name field ready for codes.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { MAX_RESIDUES, peptideProblem, peptideSmiles, peptideText, threeLetter } from "./peptide.ts";

// The conversion.
assert.deepEqual(threeLetter("ACDEFGHIKLMNPQRSTVWY"), { sequence: "Ala-Cys-Asp-Glu-Phe-Gly-His-Ile-Lys-Leu-Met-Asn-Pro-Gln-Arg-Ser-Thr-Val-Trp-Tyr" });
assert.deepEqual(threeLetter("GG"), { sequence: "Gly-Gly" });
assert.deepEqual(threeLetter("G G"), { sequence: "Gly-Gly" }, "spaces are left out");
assert.deepEqual(threeLetter("G"), { sequence: "H-Gly-OH" }, "one residue is the amino acid");
assert.deepEqual(threeLetter("H-AG-OH"), { sequence: "H-Ala-Gly-OH" });
assert.deepEqual(threeLetter("Ac-AG-NH2"), { sequence: "Ac-Ala-Gly-NH2" });
assert.deepEqual(threeLetter("ac-AG-nh2"), { sequence: "Ac-Ala-Gly-NH2" }, "the ends in any case");
assert.deepEqual(threeLetter("H-HH"), { sequence: "H-His-His" }, "H- is the end, H after it is histidine");
assert.equal(threeLetter(""), undefined);
// Refused, with the letters named.
assert.deepEqual(threeLetter("ABG"), { problem: "Not an amino acid: B" });
assert.deepEqual(threeLetter("JABOJ"), { problem: "Not amino acids: J, B, O" });
assert.deepEqual(threeLetter("ag"), { problem: "Type the amino acids in capitals, for example ACDEFG." });
assert.deepEqual(threeLetter("A-G"), { problem: "Ends can be H-, Ac-, -OH or -NH2." });
assert.ok("sequence" in threeLetter("G".repeat(MAX_RESIDUES))!, "60 residues");
assert.deepEqual(threeLetter("G".repeat(MAX_RESIDUES + 1)), { problem: "Up to 60 amino acids." });
// Only after "peptide:", so a name or formula of capitals (CHO, ACE) is never a peptide.
assert.deepEqual(peptideText("peptide: ACDEFG"), { sequence: "Ala-Cys-Asp-Glu-Phe-Gly" });
assert.deepEqual(peptideText("Peptide:GG"), { sequence: "Gly-Gly" });
assert.equal(peptideText("CHO"), undefined);
assert.equal(peptideProblem("peptide: "), undefined, "no message before any code is typed");
assert.equal(peptideProblem("peptide: ABG"), "Not an amino acid: B");
assert.equal(peptideProblem("aspirin"), undefined);

// The menu item and the toolbar's Sequence tool open the name field with "peptide: " in it. A click with the tool
// opens it, so the structure lands there (as ChemDraw starts a sequence where you click). The Actions panel has none.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /insert_peptide: \(\) => insertSequence\("peptide: "\),/);
assert.match(editor, /function insertSequence\(prefix: string\) \{\n\s+warmLayout\(\);\n\s+openNaming\(prefix\);/);
assert.match(editor, /casProblem\(naming\) \?\? peptideProblem\(naming\)/, "the name field says why codes are refused");
assert.match(readFileSync(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8"), /item\("insert_peptide", "Insert Peptide…", ""\)/);
assert.doesNotMatch(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /insert_peptide|insert_rna|insert_dna/, "sequences are in the toolbar");
const tools = readFileSync(new URL("tools.tsx", import.meta.url), "utf8");
assert.match(tools, /peptide: \{ name: "Peptide", prefix: "peptide: " \}, rna: \{ name: "RNA", prefix: "rna: " \}, dna: \{ name: "DNA", prefix: "dna: " \}/);
assert.match(tools, /\{ id: "sequence", name: SEQUENCES\[p\.variants\.sequence\]/, "the Sequence tool is on the toolbar");
assert.match(editor, /if \(tool === "sequence"\) return insertSequence\(SEQUENCES\[sequenceChoice\]\.prefix\);/);

// Through Name to Structure: the same structure as the three-letter sequence typed out, with OPSIN built.
const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("peptide: ok (Name to Structure skipped, no OPSIN build)"); process.exit(0); }
const { DRUGS } = await import("./drugs.ts");
const { attachOpsin, nameToSmiles } = await import("./names.ts");
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
attachOpsin(opsin, readFileSync(new URL("names.txt", dir), "utf8"), JSON.parse(readFileSync(new URL("./nameindex.json", import.meta.url), "utf8")), DRUGS);

for (const [codes, three] of [
  ["ACDEFGHIKLMNPQRSTVWY", "Ala-Cys-Asp-Glu-Phe-Gly-His-Ile-Lys-Leu-Met-Asn-Pro-Gln-Arg-Ser-Thr-Val-Trp-Tyr"],
  ["GG", "Gly-Gly"], ["Ac-AG-NH2", "Ac-Ala-Gly-NH2"], ["H-FA-OH", "H-Phe-Ala-OH"],
]) {
  const typed = nameToSmiles(three);
  assert.ok(typed, `${three} reads`);
  assert.equal(nameToSmiles(`peptide: ${codes}`), typed, `peptide: ${codes} is ${three}`);
}
assert.equal(nameToSmiles("peptide: GG"), nameToSmiles("glycylglycine"), "GG is glycylglycine");
assert.equal(nameToSmiles("peptide: ABG"), undefined);
assert.equal(nameToSmiles(`peptide: ${"G".repeat(61)}`), undefined, "61 residues are refused");
const sixty = nameToSmiles(`peptide: H-${"AG".repeat(30)}-OH`);
assert.ok(sixty, "60 residues with both ends draw");
assert.equal(sixty, nameToSmiles(`H-${Array(30).fill("Ala-Gly").join("-")}-OH`), "and are the three-letter sequence");

// The SMILES built without OPSIN, for the name field's live preview (namepreview.ts): the same structure as Name to
// Structure gives (same standard InChI) for every residue, inside a chain and at either end, with each end as typed.
assert.equal(peptideSmiles("aspirin"), undefined);
assert.equal(peptideSmiles("peptide: ABG"), undefined);
assert.equal(peptideSmiles("peptide: "), undefined);
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { ready, toInchi, parseStructure } = await import("./chem.ts");
await ready;
const inchi = (smiles: string) => toInchi(parseStructure(smiles, false));
const ALL = "ACDEFGHIKLMNPQRSTVWY";
for (const text of [...[...ALL].flatMap((k) => [k, `G${k}G`, `${k}A`, `A${k}`]), ALL, "Ac-AG-NH2", "H-FA-OH", "Ac-P", "P-NH2", `${ALL}${ALL}${ALL}`]) {
  const typed = `peptide: ${text}`, built = peptideSmiles(typed), want = nameToSmiles(typed);
  assert.ok(built && want, `${typed} reads`);
  const got = inchi(built);
  assert.ok(got?.startsWith("InChI=1S/"), `${typed} has an InChI`);
  assert.equal(got, inchi(want), `${typed}: the SMILES built is OPSIN's structure`);
}
console.log("peptide: ok");
