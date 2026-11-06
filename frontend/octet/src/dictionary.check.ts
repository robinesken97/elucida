// Run: node src/dictionary.check.ts. Name to Structure beyond OPSIN and Octet's own tables (src/dictionary.ts,
// src/condensed.ts): the Wikidata dictionary (data/names/dictionary.tsv.gz), CAS numbers, InChI and InChIKeys,
// condensed formulas, peptide sequences, lists of names, suggestions for misspellings, and what is refused. Reference
// InChIKeys are PubChem's for each name (27 October 2026; not shipped) unless a line says otherwise. Also the time a
// lookup and a suggestion take once the dictionary has loaded: typing must never wait.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { DRUGS } from "./drugs.ts";
import { attachOpsin, looksLikeSmiles, nameToSmiles, namesStarting, suggestName } from "./names.ts";
import { attachDictionary, casProblem, casValid, dictionarySmiles, nameList, peptideName } from "./dictionary.ts";
import { condensedSmiles } from "./condensed.ts";

const dir = new URL("./vendor/opsin/", import.meta.url), table = new URL("../data/names/dictionary.tsv.gz", import.meta.url);
if (!existsSync(new URL("opsin.js", dir)) || !existsSync(table)) { console.log("dictionary.check: skipped (no OPSIN build or no dictionary)"); process.exit(0); }
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
const text = gunzipSync(readFileSync(table)).toString("utf8");
let t0 = performance.now();
await attachDictionary(text);
const loadMs = performance.now() - t0;
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();
const keyOf = (s: string | undefined) => { if (!s) return undefined; const o = new indigo.MapStringString(); try { return indigo.convert(s, "inchi-key", o).trim() as string; } catch { return undefined; } finally { o.delete(); } };
const read = (name: string) => keyOf(nameToSmiles(name));

// Names a chemist types, each with its structure. Most come from OPSIN, Octet's tables or the dictionary; glucose is
// OPSIN's reading, D-glucose in its open-chain form as IUPAC's carbohydrate rules name it (PubChem's "glucose" is the
// pyranose, WQZGKKKJIJFFOK-GASJEMHNSA-N).
const NAMES: Record<string, string> = {
  aspirin: "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", caffeine: "RYYVLZVUVIJVGH-UHFFFAOYSA-N", nicotine: "SNICXCGAKADSCV-JTQLQIEISA-N",
  vanillin: "MWOOGOJBHIARFG-UHFFFAOYSA-N", menthol: "NOOLISFMXDJSKH-UHFFFAOYSA-N", ibuprofen: "HEFNNWSXXWATRW-UHFFFAOYSA-N",
  paracetamol: "RZVAJINKPMORJF-UHFFFAOYSA-N", acetaminophen: "RZVAJINKPMORJF-UHFFFAOYSA-N", "citric acid": "KRKNYBCHXYNGOX-UHFFFAOYSA-N",
  glucose: "GZCGUPFRVQAUEE-SLPGGIOYSA-N", cholesterol: "HVYWMOMLDIMFJA-DPAQBDIFSA-N", morphine: "BQJCRHHNABKAKU-KBQPJGBKSA-N",
  "penicillin G": "JGSARLDLIJGVTE-MBNYWOFBSA-N", DDT: "YVGGHNCTFXOJCH-UHFFFAOYSA-N", TNT: "SPSSULHKWOKEEL-UHFFFAOYSA-N",
  PETN: "TZRXHJWUDPFEEY-UHFFFAOYSA-N", EDTA: "KCXVZYZYPLLWCC-UHFFFAOYSA-N", TREN: "MBYLVOKEDDQJDY-UHFFFAOYSA-N",
  Tylenol: "RZVAJINKPMORJF-UHFFFAOYSA-N",
};
for (const [name, want] of Object.entries(NAMES)) assert.equal(read(name), want, name);

// The dictionary changes no name Octet read right before: the 200 names names.check.ts tests (read from it), and every
// name Structure to Name can give from Octet's own tables (nameindex.json) still reads back as its structure.
// As names.check.ts, the structure as the app draws it (tools/names/index.mjs).
const { drawnKet, inchiOf } = await import(new URL("../tools/names/index.mjs", import.meta.url).href);
const drawnKey = (s: string | undefined) => keyOf(s && drawnKet(s));
const want = [...readFileSync(new URL("./names.check.ts", import.meta.url), "utf8").matchAll(/"([^"]+)": "([A-Z]{14}-[A-Z]{10}-[A-Z])"/g)];
assert.ok(want.length >= 190, "names.check.ts's names are found");
for (const [, name, key] of want) assert.equal(drawnKey(nameToSmiles(name)), key, `${name} (names.check.ts)`);
const index: Record<string, string> = JSON.parse(readFileSync(new URL("./nameindex.json", import.meta.url), "utf8"));
for (const [inchi, name] of Object.entries(index)) assert.equal(inchiOf(nameToSmiles(name) ?? ""), inchi, `${name} (nameindex.json)`);

// CAS registry numbers, with the check digit checked. A wrong one is refused, with the reason.
const CAS: Record<string, string> = {
  "64-17-5": "LFQSCWFLJHTTHZ-UHFFFAOYSA-N", "50-78-2": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "58-08-2": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
  "CAS 64-17-5": "LFQSCWFLJHTTHZ-UHFFFAOYSA-N", "CAS RN: 50-78-2": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "[7732-18-5]": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
  "103-90-2": "RZVAJINKPMORJF-UHFFFAOYSA-N",
};
for (const [cas, want] of Object.entries(CAS)) { assert.ok(casValid(cas), cas); assert.equal(read(cas), want, cas); }
for (const bad of ["64-17-6", "50-78-1", "58-08-3"]) {
  assert.ok(!casValid(bad), bad);
  assert.equal(nameToSmiles(bad), undefined, bad);
  assert.match(casProblem(bad) ?? "", /^Not a CAS number\. The last digit must be \d\.$/, bad);
}
assert.equal(casProblem("64-17-6"), "Not a CAS number. The last digit must be 5.");
assert.equal(casProblem("64-17-5"), undefined);
assert.equal(casProblem("ethanol"), undefined);

// InChI reads through Indigo (the text looks like SMILES to Octet, so Indigo gets it); an InChIKey reads from the
// dictionary.
const inchi = "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)";
assert.ok(looksLikeSmiles(inchi));
assert.equal(keyOf(inchi), "BSYNRYMUTXBXSQ-UHFFFAOYSA-N");
assert.equal(read("BSYNRYMUTXBXSQ-UHFFFAOYSA-N"), "BSYNRYMUTXBXSQ-UHFFFAOYSA-N");
assert.equal(read("InChIKey=RYYVLZVUVIJVGH-UHFFFAOYSA-N"), "RYYVLZVUVIJVGH-UHFFFAOYSA-N");
assert.equal(dictionarySmiles("AAAAAAAAAAAAAA-UHFFFAOYSA-N"), undefined);

// Condensed formulas, read whole where they have one reading.
const CONDENSED: Record<string, string> = {
  PhCH2OH: "WVDDGKGOMKODPV-UHFFFAOYSA-N", CH3CH2OH: "LFQSCWFLJHTTHZ-UHFFFAOYSA-N", Me3SiCl: "IJOOHPMOJXWVHK-UHFFFAOYSA-N",
  "PhB(OH)2": "HXITXNWTGFUOAU-UHFFFAOYSA-N", "(CH3)3COH": "DKGAVHZHDRPRBM-UHFFFAOYSA-N", CH3COOEt: "XEKOWRVHYACXOJ-UHFFFAOYSA-N",
  "HC≡CCH2OH": "TVDSBUOJIPERQY-UHFFFAOYSA-N", BnNH2: "WGQKYBSKWIADBV-UHFFFAOYSA-N", C2H5OH: "LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
  CH3COOH: "QTBSBXVTEAMEQO-UHFFFAOYSA-N", C6H5CHO: "HUMNYLRZRPPJDN-UHFFFAOYSA-N",
};
for (const [f, want] of Object.entries(CONDENSED)) { assert.equal(keyOf(condensedSmiles(f)), want, f); assert.equal(read(f), want, f); }
// Each reading by hand: acetone (CO a ketone), DMSO (SO a sulfoxide), dimethyl sulfone, pentane ((CH2)3 a chain),
// trifluoroacetic acid, nitrobenzene, acetonitrile (a triple bond left to fill), propan-2-ol (a bracket on CH).
const BY_HAND: Record<string, string> = {
  CH3COCH3: "CC(C)=O", CH3SOCH3: "CS(C)=O", CH3SO2CH3: "CS(C)(=O)=O", "CH3(CH2)3CH3": "CCCCC", CF3COOH: "OC(=O)C(F)(F)F",
  PhNO2: "[O-][N+](=O)c1ccccc1", CH3CN: "CC#N", "CH3CH(OH)CH3": "CC(C)O", "(CH3CO)2O": "CC(=O)OC(C)=O", HCOOH: "OC=O",
};
for (const [f, smiles] of Object.entries(BY_HAND)) assert.equal(keyOf(condensedSmiles(f)), keyOf(smiles), f);

// Peptide sequences, through their systematic names (each residue L unless D- comes first).
assert.equal(peptideName("Ala-Gly-Ser"), "L-alanyl-glycyl-L-serine");
assert.equal(read("Ala-Gly-Ser"), "NBTGEURICRTMGL-WHFBIAKZSA-N");
assert.equal(read("H-Ala-Gly-Ser-OH"), "NBTGEURICRTMGL-WHFBIAKZSA-N");
assert.equal(peptideName("Ac-Ala-Gly-NH2"), "N-acetyl-L-alanyl-glycinamide");
assert.equal(peptideName("H-Ala-D-Phe-OH"), "L-alanyl-D-phenylalanine");
assert.equal(read("alpha alanine"), keyOf(opsin.parseToSmiles("alanine")));
assert.equal(read("beta alanine"), keyOf("NCCC(=O)O"));
assert.equal(peptideName("Ala"), undefined);
assert.equal(peptideName("Foo-Bar"), undefined);
// Each residue alone is its amino acid.
for (const code of ["Ala", "Arg", "Asn", "Asp", "Cys", "Gln", "Glu", "Gly", "His", "Ile", "Leu", "Lys", "Met", "Phe", "Pro", "Ser", "Thr", "Trp", "Tyr", "Val"])
  assert.ok(read(`H-${code}-OH`), code);

// A list of names gives each structure, in order: commas, semicolons or new lines between. A comma inside a name does
// not split it, and a CAS index name ("Benzoic acid, 2-hydroxy-") reads whole.
const three = "benzaldehyde, aniline; acetic acid";
assert.deepEqual(nameList(three, nameToSmiles)?.map(keyOf), ["HUMNYLRZRPPJDN-UHFFFAOYSA-N", "PAYRUJLWNCNPSJ-UHFFFAOYSA-N", "QTBSBXVTEAMEQO-UHFFFAOYSA-N"]);
assert.equal(nameToSmiles(three)?.split(".").length, 3);
assert.equal(nameList("caffeine\naspirin\nPhCH2OH", nameToSmiles)?.length, 3);
assert.equal(nameList("2,4-dinitrophenol", nameToSmiles), undefined);
assert.equal(read("Benzoic acid, 2-hydroxy-"), keyOf("OC(=O)c1ccccc1O"));
assert.equal(nameList("benzaldehyde, unobtainium", nameToSmiles), undefined);

// Refused: a molecular formula (more than one structure has it), nonsense, and SMILES left to Indigo.
for (const t of ["C6H6", "C2H6O", "C6H12O6", "C3H7OH", "qwertyuiop", "Foo-Bar", "1234", "CO", "CCO"]) assert.equal(nameToSmiles(t), undefined, t);

// German names, as ChemDraw reads them, with or without umlauts.
assert.equal(read("Essigsäure"), "QTBSBXVTEAMEQO-UHFFFAOYSA-N");
assert.equal(read("Essigsaeure"), "QTBSBXVTEAMEQO-UHFFFAOYSA-N");
// A name OPSIN misreads reads as the compound Wikidata and PubChem give: tropicamide, not an amide of tropic acid.
assert.equal(read("tropicamide"), "BGDKAVGWHJFAGW-UHFFFAOYSA-N");

// The template library's search and the command palette find dictionary names after Octet's own.
assert.ok(namesStarting("tylen").includes("Tylenol"), "Tylenol");
assert.ok(namesStarting("essigs").some((n) => n.startsWith("Essigs")), "Essigsäure");
assert.deepEqual(namesStarting("TREN").slice(0, 1), ["TREN"], "Octet's own names first");

// Misspellings: a suggestion that reads.
assert.ok(["acetaminophen", "paracetamol"].includes(suggestName("acetaminophin", false) ?? ""), "acetaminophin");
assert.equal(suggestName("benzaldehide", false), "benzaldehyde");
assert.equal(suggestName("ibuprofin", false), "ibuprofen");
assert.equal(suggestName("caffiene", false), "caffeine");
// "Vanilin" is a name in the dictionary (German), so it reads at once.
assert.equal(read("vanilin"), "MWOOGOJBHIARFG-UHFFFAOYSA-N");

// Speed. A lookup in the dictionary, and a suggestion as typing makes it (the quick one, on every keystroke).
const keys = text.split("\n").flatMap((l) => (l.split("\t")[1] ?? "").split("|")).filter(Boolean).map((n) => n.replace(/^!/, ""));
const sample = Array.from({ length: 50000 }, (_, i) => keys[(i * 7919) % keys.length]);
t0 = performance.now();
for (const k of sample) assert.ok(dictionarySmiles(k), k);
const lookupUs = ((performance.now() - t0) / sample.length) * 1000;
const typos = ["acetaminophin", "benzaldehide", "ibuprofin", "vanilin", "caffiene", "nicotin", "chlorofrom", "toluen", "acetylsalicilic acid", "methanl", "paracetemol", "cholesterl", "morphne", "benzne", "pyridin"];
const each: number[] = [];
for (let round = 0; round < 3; round++) for (const t of typos) { const s = performance.now(); suggestName(t, false); each.push(performance.now() - s); }
const worst = Math.max(...each.slice(typos.length)), mean = each.slice(typos.length).reduce((a, b) => a + b, 0) / (each.length - typos.length);
const lines = text.split("\n").filter(Boolean).length;
console.log(`dictionary.check: ${lines} compounds, ${keys.length} names; loaded in ${loadMs.toFixed(0)} ms; a lookup ${lookupUs.toFixed(1)} µs; a suggestion ${mean.toFixed(1)} ms on average, ${worst.toFixed(1)} ms at most`);
assert.ok(lookupUs < 50, "a lookup takes under 50 µs");
// Typing must not lag: under 5 ms a suggestion on average, and never as slow as a frame (a CI machine is slower than
// a laptop, so the worst case has room; a scan of the whole dictionary would take hundreds of milliseconds).
assert.ok(mean < 5, "a suggestion takes under 5 ms on average");
assert.ok(worst < 20, "no suggestion takes 20 ms");
