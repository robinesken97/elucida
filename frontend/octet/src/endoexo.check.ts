// Run: node src/endoexo.check.ts. endo, exo, syn and anti in names (src/endoexo.ts), through Name to Structure. Each
// name with PubChem's InChIKey for it (5 November 2026). A name with endo or exo alone gives the relative stereo, so
// either hand of the structure is right for it; a name that also gives (1R) or (1S) has one hand.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { DRUGS } from "./drugs.ts";
import { attachOpsin, nameToSmiles } from "./names.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("endoexo.check: skipped (no OPSIN build)"); process.exit(0); }
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
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();
const keyOf = (s: string | undefined) => { if (!s) return undefined; const o = new indigo.MapStringString(); try { return indigo.convert(s, "inchi-key", o).trim() as string; } catch { return undefined; } finally { o.delete(); } };
const mirror = (s: string) => s.replace(/@@?/g, (x) => (x === "@" ? "@@" : "@"));
// The structure's InChIKey, and its mirror image's.
const hands = (name: string) => { const s = nameToSmiles(name); return s ? [keyOf(s), keyOf(mirror(s))] : []; };

// Relative: either hand.
const RELATIVE: Record<string, string> = {
  "cis-5-norbornene-endo-2,3-dicarboxylic anhydride": "KNDQHSIWLOJIGP-UMRXKNAASA-N", // carbic anhydride, 129-64-6
  "cis-5-Norbornene-exo-2,3-dicarboxylic anhydride": "KNDQHSIWLOJIGP-RNGGSSJXSA-N", // 2746-19-2
  "endo-bicyclo[2.2.1]hept-5-ene-2,3-dicarboxylic anhydride": "KNDQHSIWLOJIGP-UMRXKNAASA-N",
  "endo-bicyclo[2.2.1]heptan-2-ol": "ZQTYQMYDIHMKQB-XVMARJQXSA-N", // endo-norborneol
  "bicyclo[2.2.1]heptan-2-exo-ol": "ZQTYQMYDIHMKQB-VQVTYTSYSA-N", // exo-norborneol
  "2-exo-bromobicyclo[2.2.1]heptane": "QXYOAWHKJRWNID-RRKCRQDMSA-N",
  "endo,exo-bicyclo[2.2.1]hept-5-ene-2,3-dicarboxylic acid": "NIDNOXCRFUCAKQ-XZBKPIIZSA-N", // the trans diacid
  "(2-endo,3-exo)-bicyclo[2.2.1]hept-5-ene-2,3-dicarboxylic acid": "NIDNOXCRFUCAKQ-XZBKPIIZSA-N",
  "2-endo,3-exo-bicyclo[2.2.1]hept-5-ene-2,3-dicarboxylic acid": "NIDNOXCRFUCAKQ-XZBKPIIZSA-N",
  "exo,exo-bicyclo[2.2.1]hept-5-ene-2,3-dicarboxylic acid": "NIDNOXCRFUCAKQ-RNGGSSJXSA-N",
  "endo-1,7,7-trimethylbicyclo[2.2.1]heptan-2-ol": "DTGKSKDOIYIVQL-QXFUBDJGSA-N", // borneol
  "exo-1,7,7-trimethylbicyclo[2.2.1]heptan-2-ol": "DTGKSKDOIYIVQL-OYNCUSHFSA-N", // isoborneol
};
for (const [name, want] of Object.entries(RELATIVE)) assert.ok(hands(name).includes(want), name);
// Absolute: the hand the name gives.
const ABSOLUTE: Record<string, string> = {
  "(1S)-endo-1,7,7-trimethylbicyclo[2.2.1]heptan-2-ol": "DTGKSKDOIYIVQL-QXFUBDJGSA-N", // (-)-borneol
  "(1R)-endo-1,7,7-trimethylbicyclo[2.2.1]heptan-2-ol": "DTGKSKDOIYIVQL-WEDXCCLWSA-N", // (+)-borneol
  "(1R)-exo-1,7,7-trimethylbicyclo[2.2.1]heptan-2-ol": "DTGKSKDOIYIVQL-MRTMQBJTSA-N", // (-)-isoborneol
};
for (const [name, want] of Object.entries(ABSOLUTE)) assert.equal(keyOf(nameToSmiles(name)), want, name);

// syn and anti on C7 (r and s, which OPSIN does not read): two different structures. syn points towards C2 and C3, the
// bridge numbered first. PubChem has no record of either to check the side against.
const syn = hands("syn-bicyclo[2.2.1]hept-2-en-7-ol"), anti = hands("anti-bicyclo[2.2.1]hept-2-en-7-ol");
assert.ok(syn[0] && anti[0] && syn[0] !== anti[0], "syn and anti differ");
assert.equal(syn[0]!.slice(0, 14), "PSKWDFVNXXATCG");
assert.notEqual(hands("7-syn-bromobicyclo[2.2.1]hept-2-ene")[0], hands("7-anti-bromobicyclo[2.2.1]hept-2-ene")[0]);

// Words Octet cannot place are never dropped: no structure.
for (const name of ["endo-2-methylbicyclo[2.2.1]heptan-2-ol", "1-endo-bicyclo[2.2.1]heptane", "syn-bicyclo[2.2.1]heptan-2-ol"]) assert.equal(nameToSmiles(name), undefined, name);
// The words in other names change nothing.
assert.equal(keyOf(nameToSmiles("benzene")), "UHOVQNZJYSORNB-UHFFFAOYSA-N");
console.log(`endoexo.check: ${Object.keys(RELATIVE).length + Object.keys(ABSOLUTE).length + 4} names`);
