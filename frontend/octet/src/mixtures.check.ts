// Run: node src/mixtures.check.ts. Grouped mixtures (mixtures.ts), named as ChemDraw 26.1 names them: the components'
// checked names joined by "--", then their ratio, "A--B (0.72/0.28)". The ratio comes from the repeat count of a
// multiple-group bracket pair round each component. Each name must read back through Name to Structure (names.ts) as
// the components, each as many times as it draws them.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import type { Mol, Shape } from "./render.ts";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("mixtures.check: skipped (no OPSIN build)"); process.exit(0); }
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
const { checkedName, setComplexNamer, setNamer } = await import("./naming.ts");
const { iupacName } = await import("./namer.ts");
const { complexName } = await import("./complexes.ts");
const { mixtureName, mixturesOf, withSalts } = await import("./mixtures.ts");
const { fragments, subset } = await import("./edit.ts");
setNamer(iupacName);
setComplexNamer((m) => complexName(m, { read: nameToSmiles, atoms: nameToAtoms, inchi: chem.toInchi, aux: chem.toInchiAux, cip: chem.cipOf }));
const inchiOf = (s: Mol | string) => { try { return chem.toInchi(typeof s === "string" ? chem.parseStructure(s) : s); } catch { return undefined; } };

// A drawing of several structures side by side (each drawn from SMILES, moved right of the last), all in one group,
// with a multiple-group bracket pair round each one given a count.
function drawing(parts: { smiles: string; count?: number }[], grouped = true): Mol {
  const doc: Mol = { atoms: [], bonds: [], shapes: [], groups: [] };
  let x = 0, id = 1;
  for (const p of parts) {
    const m = chem.parseStructure(p.smiles), xs = m.atoms.map((a) => a.location[0]), ys = m.atoms.map((a) => a.location[1]);
    const dx = x - Math.min(...xs) + 1, base = doc.atoms.length;
    doc.atoms.push(...m.atoms.map((a) => ({ ...a, location: [a.location[0] + dx, a.location[1], 0] as [number, number, number] })));
    doc.bonds.push(...m.bonds.map((b) => ({ ...b, atoms: [b.atoms[0] + base, b.atoms[1] + base] as [number, number] })));
    const left = x + 0.5, right = x + 1.5 + Math.max(...xs) - Math.min(...xs);
    if (p.count !== undefined) doc.shapes!.push({ id: id++, kind: "brackets", from: [left, Math.min(...ys) - 0.5], to: [right, Math.max(...ys) + 0.5], polymer: { usage: "mult", ...(p.count !== 2 ? { label: String(p.count) } : {}) } } as Shape);
    x = right + 1;
  }
  if (grouped) doc.groups!.push({ id: id++, atoms: doc.atoms.map((_, i) => i), items: doc.shapes!.map((s) => s.id) });
  return doc;
}
// Structure to Name as the editor runs it (Editor.tsx nameStructures): each grouped mixture by mixtureName from its
// components' checked names; else each structure alone.
function names(doc: Mol): string[] {
  const targets = withSalts(doc, fragments(doc).filter((g) => g.length)), mixes = mixturesOf(doc, targets), inMix = new Set(mixes.flatMap((x) => x.atoms));
  const one = (atoms: number[]) => { const p = subset(doc, new Set(atoms)); return { name: checkedName(p, chem.expandLabels(p), nameToSmiles, inchiOf, chem.cipOf) ?? "", mol: p }; };
  return [
    ...mixes.map((mix) => mixtureName(mix.parts.map((p) => ({ ...one(p.atoms), count: p.count })), nameToSmiles, inchiOf) ?? "(none)"),
    ...targets.filter((t) => !t.some((i) => inMix.has(i))).map((t) => one(t).name || "(none)"),
  ];
}

// ChemDraw's own example (its 26.1 help): two regioisomers in brackets of 0.72 and 0.28, grouped.
const A = "OC(=O)c1cccc(n1)C(C)n1nnc2cc(ccc12)-c1cncc(OCC)n1", B = "OC(=O)c1cccc(n1)C(C)n1nnc2ccc(cc12)-c1cncc(OCC)n1";
const example = names(drawing([{ smiles: A, count: 0.72 }, { smiles: B, count: 0.28 }]));
const [na, nb] = [A, B].map((s) => checkedName(chem.parseStructure(s), chem.expandLabels(chem.parseStructure(s)), nameToSmiles, inchiOf, chem.cipOf));
assert.ok(na && nb && na !== nb, `${na} and ${nb}`);
assert.deepEqual(example, [`${na}--${nb} (0.72/0.28)`]);
console.log(`mixtures.check: ${example[0]}`);
// Read back: the two components, each once (a fractional ratio).
assert.equal(inchiOf(nameToSmiles(example[0])!), inchiOf(`${A}.${B}`));

const cases: [string, { smiles: string; count?: number }[], string][] = [
  // Whole-number ratios draw each component that many times when read back.
  ["ethanol and water, 2:1", [{ smiles: "CCO", count: 2 }, { smiles: "O" }], "ethanol--water (2/1)"],
  ["water and ethanol, drawn the other way round", [{ smiles: "O" }, { smiles: "CCO", count: 2 }], "water--ethanol (1/2)"],
  // With no brackets each component counts once.
  ["toluene and benzene", [{ smiles: "Cc1ccccc1" }, { smiles: "c1ccccc1" }], "methylbenzene--benzene (1/1)"],
  ["three components", [{ smiles: "CC(C)=O", count: 0.5 }, { smiles: "CO", count: 0.3 }, { smiles: "ClCCl", count: 0.2 }], "propan-2-one--methanol--dichloromethane (0.5/0.3/0.2)"],
  // A salt in a mixture is one component: sodium chloride and water.
  ["a salt and water", [{ smiles: "[Na+].[Cl-]" }, { smiles: "O", count: 6 }], "sodium chloride--water (1/6)"],
];
for (const [label, parts, want] of cases) {
  const got = names(drawing(parts));
  assert.deepEqual(got, [want], label);
}
// Not grouped: each structure has its own name.
assert.deepEqual(names(drawing([{ smiles: "CCO", count: 2 }, { smiles: "O" }], false)), ["ethanol", "water"]);
// A component Octet cannot name: no name for the mixture.
assert.deepEqual(names(drawing([{ smiles: "CCO" }, { smiles: "[Xe]" }])).length, 1);

// The check turns down a name that does not read back as the drawing: a wrong component, or a count Name to Structure
// would draw another number of times.
const ethanol = chem.parseStructure("CCO"), water = chem.parseStructure("O");
assert.equal(mixtureName([{ name: "ethanol", mol: ethanol, count: 2 }, { name: "water", mol: water, count: 1 }], nameToSmiles, inchiOf), "ethanol--water (2/1)");
assert.equal(mixtureName([{ name: "methanol", mol: ethanol, count: 2 }, { name: "water", mol: water, count: 1 }], nameToSmiles, inchiOf), undefined);
assert.equal(mixtureName([{ name: "ethanol", mol: ethanol, count: 2 }, { name: "water", mol: water, count: 1 }], (n) => nameToSmiles(n.replace("(2/1)", "(3/1)")), inchiOf), undefined);
assert.equal(mixtureName([{ name: "ethanol", mol: ethanol, count: 1 }], nameToSmiles, inchiOf), undefined);
console.log(`mixtures.check: ChemDraw's example and ${cases.length} grouped mixtures named with their ratios, each read back`);
