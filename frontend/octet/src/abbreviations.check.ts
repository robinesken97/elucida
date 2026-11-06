// Run: node src/abbreviations.check.ts. Recognition of literature abbreviations, as the editor runs it: the Structure
// panel shows a structure's abbreviation by its formula ("TREN · C6H18N4"), and Structure to Name writes the checked
// name with the abbreviation after it ("N1,N1-bis(2-aminoethyl)ethane-1,2-diamine (TREN)"). Each structure is drawn
// from its name as Name to Structure draws it.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import type { Mol } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("abbreviations.check: skipped (no OPSIN build)"); process.exit(0); }
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
const json = (file: string) => JSON.parse(readFileSync(new URL(file, import.meta.url), "utf8"));
const { DRUGS } = await import("./drugs.ts");
const { abbreviationOf, attachOpsin, knownName, nameToAtoms, nameToSmiles } = await import("./names.ts");
attachOpsin(opsin, readFileSync(new URL("names.txt", dir), "utf8"), json("./nameindex.json"), DRUGS, json("./abbreviations.json"));
const { checkedName, setComplexNamer, setNamer, withAbbreviation } = await import("./naming.ts");
const { iupacName } = await import("./namer.ts");
const { complexName } = await import("./complexes.ts");
setNamer(iupacName);
setComplexNamer((m) => complexName(m, { read: nameToSmiles, atoms: nameToAtoms, inchi: chem.toInchi, aux: chem.toInchiAux, cip: chem.cipOf }));

// A structure as Name to Structure draws it (Editor.tsx structureFor).
const drawn = (name: string): Mol => chem.parseStructure(nameToSmiles(name)!);
// The Structure panel's line for the first structure: its abbreviation, then its formula (Actions.tsx).
const header = (m: Mol) => { const a = chem.analyse(m, 3, abbreviationOf)?.[0]; return a && (a.abbreviation ? `${a.abbreviation} · ${a.formula}` : a.formula); };
// Structure to Name as the editor runs it (Editor.tsx nameFor).
const inchiOf = (s: Mol | string) => { try { return chem.toInchi(typeof s === "string" ? chem.parseStructure(s, false) : s); } catch { return undefined; } };
const caption = (m: Mol) => { const name = checkedName(m, chem.expandLabels(m), nameToSmiles, inchiOf, chem.cipOf, knownName); return name && withAbbreviation(name, abbreviationOf(inchiOf(m))); };

// The panel header.
assert.equal(header(drawn("TREN")), "TREN · C6H18N4");
assert.equal(header(drawn("tris(2-aminoethyl)amine")), "TREN · C6H18N4", "drawn from its name, it is still TREN");
assert.equal(header(drawn("triethylamine")), "Et3N · C6H15N", "Et3N is listed before TEA");
assert.equal(header(drawn("dichloromethane")), "DCM · CH2Cl2");
assert.equal(header(drawn("water")), "H2O", "a formula is not cited");
assert.equal(header(drawn("aspirin")), "C9H8O4", "a drug's name is not cited");
assert.equal(header(drawn("NBS")), "NBS · C4H4BrNO2");
assert.equal(header(drawn("Ir(ppy)3")), "Ir(ppy)3 · C33H24IrN3");
// Without the names engine (abbreviations not loaded), the formula alone.
assert.equal(chem.analyse(drawn("TREN"), 3)?.[0].abbreviation, undefined);
// Each structure in a drawing has its own.
const two = drawn("TREN"), more = drawn("cyclam"), both = { atoms: [...two.atoms, ...more.atoms.map((a) => ({ ...a, location: [a.location[0] + 20, a.location[1], 0] as [number, number, number] }))], bonds: [...two.bonds, ...more.bonds.map((b) => ({ ...b, atoms: [b.atoms[0] + two.atoms.length, b.atoms[1] + two.atoms.length] as [number, number] }))] };
assert.deepEqual(chem.analyse(both, 3, abbreviationOf)?.map((a) => a.abbreviation), ["TREN", "cyclam"]);
// Pieces that make one compound, and are all there is, are one line: a salt, ferrocene's ions, ligands drawn apart.
assert.equal(header(drawn("dppf")), "dppf · C34H28FeP2");
assert.equal(header(drawn("[Ru(bpy)3]Cl2")), "[Ru(bpy)3]Cl2 · C30H24Cl2N6Ru");
assert.equal(header(drawn("Ni(cod)2")), "Ni(cod)2 · C16H24Ni");
assert.equal(chem.analyse(drawn("dppf"), 3)?.length, 3, "without abbreviations, each piece");
assert.equal(chem.analyse(drawn("NaCl"), 3, abbreviationOf)?.length, 2, "a salt with no abbreviation stays in pieces");

// The name caption.
assert.equal(caption(drawn("TREN")), "N1,N1-bis(2-aminoethyl)ethane-1,2-diamine (TREN)");
assert.equal(caption(drawn("DBU")), "2,3,4,6,7,8,9,10-octahydropyrimido[1,2-a]azepine (DBU)");
assert.equal(caption(drawn("Et3N")), "N,N-diethylethanamine (Et3N)");
assert.equal(caption(drawn("TEA")), "N,N-diethylethanamine (Et3N)", "one abbreviation for one structure");
assert.equal(caption(drawn("water")), "water");
assert.equal(caption(drawn("NaCl")), "sodium chloride");
assert.equal(caption(drawn("ethanol")), "ethanol (EtOH)");
assert.match(caption(drawn("dppf")) ?? "", / \(dppf\)$/);
assert.match(caption(drawn("[Ru(bpy)3]Cl2")) ?? "", / \(\[Ru\(bpy\)3\]Cl2\)$/);
assert.equal(withAbbreviation("Wilkinson's catalyst", "Wilkinson's catalyst"), "Wilkinson's catalyst", "never the name twice");
assert.equal(withAbbreviation("pyridine"), "pyridine");
console.log("abbreviations.check: the Structure panel and Structure to Name cite TREN, Et3N, DCM and the rest; formulas and drug names are not cited");
