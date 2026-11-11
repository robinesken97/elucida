// Run: node src/macrocycles.check.ts. Phthalocyanine and corrole: retained parents that Octet adds to its OPSIN build
// (tools/opsin/pack/arylGroups.patch) and to the namer (fusion.ts), from the IUPAC tetrapyrrole recommendations
// (1986): TP-1.6 Fig. 4 (phthalocyanine) and TP-5.3 Fig. 11 (corrole). As both are Octet's own data, the namer's round
// trip through OPSIN checks the two against each other only, so each parent is checked here against sources outside
// that data:
// 1. PubChem's standard InChI for the parent (copied by hand: phthalocyanine CID 5282330, corrole CID 6857582).
// 2. The figures' rings, written as cycles of locants: every bond of OPSIN's structure joins the locants they join.
// 3. Derivatives written by hand from the figures' Kekulé structures (walked from another atom than OPSIN's SMILES),
//    with a chlorine at one position and a methyl at each other: OPSIN's reading of each name must be that structure.
// Then the free bases as drawn: Structure to Name gives 21H,23H-porphyrin, 29H,31H-phthalocyanine and
// 21H,22H,23H-corrole names when every pyrrole N points into the ring, and none for an N-confused porphyrin or a
// pyrrole drawn turned out (naming.ts macrocycle).
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("macrocycles.check: skipped (no OPSIN build)"); process.exit(0); }
// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
await chem.ready;
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
const { attachOpsin, nameToAtoms, nameToSmiles } = await import("./names.ts");
attachOpsin(opsin, readFileSync(new URL("names.txt", dir), "utf8"));
const { checkedName, macrocycle, setComplexNamer, setNamer, withoutRingEZ } = await import("./naming.ts");
const { iupacName } = await import("./namer.ts");
const { complexName } = await import("./complexes.ts");
setNamer(iupacName);
setComplexNamer((m) => complexName(m, { read: nameToSmiles, atoms: nameToAtoms, inchi: chem.toInchi, aux: chem.toInchiAux, cip: chem.cipOf }));
const inchiOf = (s: Mol | string) => { try { return chem.toInchi(typeof s === "string" ? chem.parseStructure(s) : s); } catch { return undefined; } };
const opsinInchi = (name: string) => { const s = nameToSmiles(name); return s ? chem.toInchi(s) : undefined; };

// 1. PubChem's InChI (read 23 October 2026; the free bases with their two or three NH).
const PUBCHEM: [string, string][] = [
  ["29H,31H-phthalocyanine", "InChI=1S/C32H18N8/c1-2-10-18-17(9-1)25-33-26(18)38-28-21-13-5-6-14-22(21)30(35-28)40-32-24-16-8-7-15-23(24)31(36-32)39-29-20-12-4-3-11-19(20)27(34-29)37-25/h1-16H,(H2,33,34,35,36,37,38,39,40)"],
  ["21H,22H,23H-corrole", "InChI=1S/C19H14N4/c1-3-14-10-16-5-7-18(22-16)19-8-6-17(23-19)11-15-4-2-13(21-15)9-12(1)20-14/h1-11,20-22H"],
];
for (const [name, want] of PUBCHEM) {
  assert.equal(opsinInchi(name), want, name);
  assert.equal(opsinInchi(name.replace(/^[\dH,]+-/, "")), want, `${name} without indicated hydrogen`);
}

// 2. The rings of the figures as cycles of locants (the benzo and pyrrole rings, then the inner ring), and the N atoms.
const RINGS: [string, string[], string][] = [
  ["29H,31H-phthalocyanine", [
    "1 2 3 4 4a 28a", "28 28a 4a 5 29", "7a 8 9 10 11 11a", "7 7a 11a 12 32", "14a 15 16 17 18 18a", "14 14a 18a 19 31",
    "21a 22 23 24 25 25a", "21 21a 25a 26 30", "5 6 7 32 12 13 14 31 19 20 21 30 26 27 28 29",
  ], "6 13 20 27 29 30 31 32"],
  ["21H,22H,23H-corrole", ["1 2 3 4 21", "6 7 8 9 22", "11 12 13 14 23", "16 17 18 19 24", "1 21 4 5 6 22 9 10 11 23 14 15 16 24 19"], "21 22 23 24"],
];
for (const [name, rings, ns] of RINGS) {
  const b = JSON.parse(nameToAtoms(name)!) as { atoms: [string, number, number, string?][]; bonds: [number, number, number][] };
  const loc = b.atoms.map((a) => (a[3] ?? "").split(" ").find((l) => /^\d+a?$/.test(l)));
  const got = new Set(b.bonds.filter(([x, y]) => loc[x] && loc[y]).map(([x, y]) => [loc[x], loc[y]].sort().join("-")));
  const want = new Set(rings.flatMap((r) => r.split(" ").map((l, k, all) => [l, all[(k + 1) % all.length]].sort().join("-"))));
  assert.deepEqual([...got].sort(), [...want].sort(), `${name}: bonds by locant`);
  assert.deepEqual(b.atoms.flatMap((a, i) => (a[0] === "N" ? [loc[i]] : [])).sort(), ns.split(" ").sort(), `${name}: N atoms`);
  assert.equal(new Set(loc.filter(Boolean)).size, b.atoms.filter((a) => a[0] !== "H").length, `${name}: one locant for each atom`);
}

// 3. Derivatives drawn by hand. pc: Fig. 4's Kekulé structure (NH at 29 and 31) from N6 round to C5; cor: Fig. 11's
// (NH at 21, 22, 23) from C10 round to C9. s: a substituent at each locant given.
const at = (s: Record<string, string>, l: string) => (s[l] ? `(${s[l]})` : "");
const pc = (s: Record<string, string>) => {
  const c = (l: string) => `C${at(s, l)}`;
  return `N1=C2C=3${c("8")}=${c("9")}${c("10")}=${c("11")}C3C(=N2)N=C2C=3${c("15")}=${c("16")}${c("17")}=${c("18")}C3C(N2${at(s, "31")})=NC=2C=3${c("22")}=${c("23")}${c("24")}=${c("25")}C3C(N2)=NC2=C3${c("1")}=${c("2")}${c("3")}=${c("4")}C3=C1N2${at(s, "29")}`;
};
const cor = (s: Record<string, string>) => {
  const c = (l: string) => `C${at(s, l)}`;
  return `C1${at(s, "10")}C2=${c("12")}${c("13")}=C(N2${at(s, "23")})${c("15")}=C2${c("17")}=${c("18")}C(=N2)C2=${c("2")}${c("3")}=C(N2${at(s, "21")})${c("5")}=C2${c("7")}=${c("8")}C=1N2${at(s, "22")}`;
};
// A chlorine fixes the numbering (no symmetry of either ring keeps its place), so each methyl's place is its locant's.
const DERIVED: [string, string][] = [["29H,31H-phthalocyanine", pc({})], ["21H,22H,23H-corrole", cor({})]];
for (const l of ["2", "3", "4", "8", "9", "10", "11", "15", "16", "17", "18", "22", "23", "24", "25", "29", "31"])
  DERIVED.push([`1-chloro-${l}-methyl-29H,31H-phthalocyanine`, pc({ 1: "Cl", [l]: "C" })]);
for (const l of ["3", "5", "7", "8", "10", "12", "13", "15", "17", "18", "21", "22", "23"])
  DERIVED.push([`2-chloro-${l}-methyl-21H,22H,23H-corrole`, cor({ 2: "Cl", [l]: "C" })]);
for (const [name, smiles] of DERIVED) assert.equal(opsinInchi(name), chem.toInchi(smiles), name);
// The test tells places apart: a methyl one place off is another structure.
for (const [name, smiles] of [["1-chloro-2-methyl-29H,31H-phthalocyanine", pc({ 1: "Cl", 3: "C" })], ["1-chloro-8-methyl-29H,31H-phthalocyanine", pc({ 1: "Cl", 11: "C" })],
  ["1-chloro-29-methyl-29H,31H-phthalocyanine", pc({ 1: "Cl", 31: "C" })], ["2-chloro-7-methyl-21H,22H,23H-corrole", cor({ 2: "Cl", 8: "C" })],
  ["2-chloro-21-methyl-21H,22H,23H-corrole", cor({ 2: "Cl", 23: "C" })]] as const) assert.notEqual(opsinInchi(name), chem.toInchi(smiles), name);
console.log(`macrocycles.check: phthalocyanine and corrole match PubChem, their figures' rings and ${DERIVED.length} derivatives drawn by hand`);

// The free bases as drawn (Indigo's layout of the SMILES), every pyrrole N pointing into the ring.
const drawn = (smiles: string) => chem.expandLabels(chem.parseStructure(smiles));
const editorName = (m: Mol) => checkedName(m, m, nameToSmiles, inchiOf, chem.cipOf);
const porphyrin = (r: string) => `C12=CC=C(N1)C(${r})=C1C=CC(=N1)C(${r})=C1C=CC(N1)=C(${r})C=1C=CC(N1)=C2${r}`;
const corrole = (r: string) => `C12=CC=C(N1)C(${r})=C1C=CC(N1)=C(${r})C1=CC=C(N1)C(${r})=C1C=CC2=N1`;
const PC = "C12=C3C=CC=CC3=C(N1)N=C1C3=CC=CC=C3C(=N1)N=C1C3=CC=CC=C3C(N1)=NC=1C3=CC=CC=C3C(N1)=N2";
const PH = "c3ccccc3", F5 = "c3c(F)c(F)c(F)c(F)c3F";
const FREE: [string, string, string][] = [
  ["H2P", porphyrin("[H]"), "21H,23H-porphyrin"],
  ["H2TPP", porphyrin(PH), "5,10,15,20-tetraphenyl-21H,23H-porphyrin"],
  ["H2OEP", "C12=C(CC)C(CC)=C(N1)C=C1C(CC)=C(CC)C(=N1)C=C1C(CC)=C(CC)C(N1)=CC=1C(CC)=C(CC)C(N1)=C2", "2,3,7,8,12,13,17,18-octaethyl-21H,23H-porphyrin"],
  ["H2TMeOPP", porphyrin("c3ccc(OC)cc3"), "5,10,15,20-tetrakis(4-methoxyphenyl)-21H,23H-porphyrin"],
  ["H2Pc", PC, "29H,31H-phthalocyanine"],
  ["H2Pc(tBu)4", "C12=C3C=CC(C(C)(C)C)=CC3=C(N1)N=C1C3=CC=C(C(C)(C)C)C=C3C(=N1)N=C1C3=CC=C(C(C)(C)C)C=C3C(N1)=NC=1C3=CC(C(C)(C)C)=CC=C3C(N1)=N2",
    "2,9,16,24-tetra-tert-butyl-29H,31H-phthalocyanine"],
  ["H2Pc(tBu)4, C4h", nameToSmiles("2,9,16,23-tetra-tert-butyl-29H,31H-phthalocyanine")!, "2,9,16,23-tetra-tert-butyl-29H,31H-phthalocyanine"],
  ["H2Pc(OBu)8", nameToSmiles("1,4,8,11,15,18,22,25-octabutoxy-29H,31H-phthalocyanine")!, "1,4,8,11,15,18,22,25-octabutoxy-29H,31H-phthalocyanine"],
  ["H3corrole", corrole("[H]"), "21H,22H,23H-corrole"],
  ["H3TPC", corrole(PH), "5,10,15-triphenyl-21H,22H,23H-corrole"],
  ["H3tpfc", corrole(F5), "5,10,15-tris(pentafluorophenyl)-21H,22H,23H-corrole"],
];
for (const [label, smiles, want] of FREE) {
  const m = drawn(smiles);
  assert.equal(macrocycle(m)?.inward, true, `${label}: N atoms point in`);
  assert.equal(editorName(m), want, label);
}
// A pyrrole drawn turned out (N21 and its two β carbons mirrored in the line through C1 and C4): the meso bonds beside
// it are E, which the name does not say, so no name.
const turned = drawn(porphyrin(PH)), [c1, c4] = [0, 3];
for (const i of [1, 2, 4]) {
  const [x, y] = turned.atoms[i].location, [ax, ay] = turned.atoms[c1].location, [bx, by] = turned.atoms[c4].location;
  const dx = bx - ax, dy = by - ay, t = ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), px = ax + t * dx, py = ay + t * dy;
  turned.atoms[i] = { ...turned.atoms[i], location: [2 * px - x, 2 * py - y, 0] };
}
assert.equal(turned.atoms[4].label, "N");
assert.equal(macrocycle(turned)?.inward, false, "turned out");
assert.notEqual(inchiOf(turned), inchiOf(drawn(porphyrin(PH))), "turned out: another stereoisomer");
assert.equal(editorName(turned), undefined, "turned out");
// N-confused tetraphenylporphyrin: its first ring is joined to the macrocycle through C1 and C4 with C21 between them
// inside and N2 outside. Not pyrrole-type, so its E and Z count.
const nConfused = drawn(`C12NC=C(C=1)C(${PH})=C1C=CC(=N1)C(${PH})=C1C=CC(N1)=C(${PH})C=1C=CC(N1)=C2${PH}`);
assert.equal(macrocycle(nConfused)?.inward, false, "N-confused");
assert.equal(editorName(nConfused), undefined, "N-confused");
// Large rings with no fused smaller ring have no macrocycle bonds: their E and Z always count (namer-complex.check.ts
// names (Z)- and (E)-cyclooctene).
assert.equal(macrocycle(drawn("C1=CCCCCCC1")), undefined);
assert.equal(macrocycle(drawn("O=C1CC=CCCCCCCCCO1")), undefined);
const coe = "InChI=1S/C8H14/c1-2-4-6-8-7-5-3-1/h1-2H,3-8H2/b2-1-";
assert.equal(withoutRingEZ(coe), coe);
console.log(`macrocycles.check: ${FREE.length} free bases named, a pyrrole turned out and an N-confused porphyrin not named`);
