// Builds src/nameindex.json: the names Structure to Name can give from Octet's own tables when its namer has no
// name, by standard InChI. From common.ts the systematic name each abbreviation stands for (DBU), or the key where it is
// a name (Wilkinson's catalyst, tetrakis(triphenylphosphine)palladium(0)); from drugs.ts every drug name (not "=name"
// entries) and the KNOWN names.
// Also builds src/abbreviations.json: for each structure in common.ts, by standard InChI, the first key listed for it
// that Octet can cite (citable), for Structure to Name and the Structure panel.
// Run after changing common.ts or drugs.ts: node tools/names/index.mjs (src/names.check.ts fails until then).
import { readFileSync, writeFileSync } from "node:fs";
const src = new URL("../../src/", import.meta.url), dir = new URL("vendor/opsin/", src);
const pack = readFileSync(new URL("opsin-data.bin", dir));
const files = new Map();
for (let p = 0; ; ) {
  const n = pack.readUInt16BE(p); p += 2;
  if (!n) break;
  const name = pack.toString("latin1", p, p + n); p += n;
  const size = pack.readInt32BE(p); p += 4;
  files.set(name, new Int8Array(pack.buffer, pack.byteOffset + p, size)); p += size;
}
globalThis.opsinResource = (name) => files.get(name) ?? null;
const opsin = await import(new URL("opsin.js", dir));
opsin.init();
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", src))).default();
const { COMMON, citable } = await import(new URL("common.ts", src));
const { DRUGS, KNOWN } = await import(new URL("drugs.ts", src));
const { hydrogens, NONMETAL, orderOf } = await import(new URL("render.ts", src));
// The structure as the app draws SMILES (Indigo's layout, Kekulé bonds) and counts its hydrogens: an atom bonded to
// a metal keeps the hydrogens Octet draws (src/chem.ts, ketOf).
export function drawnKet(smiles) {
  const o = new indigo.MapStringString();
  o.set("output-content-type", "application/json");
  o.set("dearomatize-on-load", "true");
  try {
    const ket = JSON.parse(JSON.parse(indigo.layout(smiles, "ket", o)).struct);
    for (const { $ref } of ket.root.nodes) {
      const f = ket[$ref];
      if (f?.type !== "molecule") continue;
      const used = f.atoms.map(() => 0), metalled = f.atoms.map(() => false);
      for (const b of f.bonds) for (const [i, j] of [b.atoms, [b.atoms[1], b.atoms[0]]]) { used[i] += orderOf(b.type); if (!NONMETAL.has(f.atoms[j].label)) metalled[i] = true; }
      f.atoms.forEach((a, i) => { if (metalled[i] && NONMETAL.has(a.label)) a.explicitValence = Math.round(used[i]) + hydrogens(a.label, a.charge ?? 0, used[i]); });
    }
    return JSON.stringify(ket);
  } finally { o.delete(); }
}
export function inchiOf(smiles) {
  const o = new indigo.MapStringString();
  try { return indigo.convert(drawnKet(smiles), "inchi", o).trim() || undefined; } catch { return undefined; } finally { o.delete(); }
}
// In order of preference: the first name for an InChI is kept.
export function entries() {
  const word = (k) => /[a-z]{4}/.test(k);
  return [
    ...Object.values(COMMON).filter((v) => !v.startsWith("smiles:")).map((v) => [v, opsin.parseToSmiles(v)]),
    ...Object.entries(DRUGS).filter(([, v]) => !v.startsWith("=")),
    ...KNOWN.map((n) => [n, opsin.parseToSmiles(n)]),
    ...Object.entries(COMMON).map(([k, v]) => [k, v.startsWith("=") ? COMMON[v.slice(1)] : v]).filter(([k, v]) => v.startsWith("smiles:") && word(k)).map(([k, v]) => [k, v.slice(7)]),
  ];
}
export function build() {
  const index = {};
  for (const [name, smiles] of entries()) {
    const inchi = smiles && inchiOf(smiles);
    if (inchi && !(inchi in index)) index[inchi] = name;
  }
  return index;
}
// A structure's elements from its standard InChI: the formula layer, with the protons the /p layer adds or takes away.
export function countsOf(inchi) {
  const counts = {}, p = /\/p([+-]\d+)/.exec(inchi);
  for (const part of inchi.split("/")[1].split(".")) {
    const [, times, formula] = /^(\d*)(.*)$/.exec(part);
    for (const [, el, n] of formula.matchAll(/([A-Z][a-z]?)(\d*)/g)) counts[el] = (counts[el] ?? 0) + Number(times || 1) * Number(n || 1);
  }
  if (p) counts.H = (counts.H ?? 0) + Number(p[1]);
  if (counts.H === 0) delete counts.H;
  return counts;
}
export function abbreviations() {
  const out = {};
  for (const [k, v] of Object.entries(COMMON)) {
    const w = v.startsWith("=") ? COMMON[v.slice(1)] : v, smiles = w.startsWith("smiles:") ? w.slice(7) : opsin.parseToSmiles(w);
    const inchi = smiles && inchiOf(smiles);
    if (inchi && !(inchi in out) && citable(k, countsOf(inchi))) out[inchi] = k;
  }
  return out;
}
const write = (file, index) => writeFileSync(new URL(file, src), JSON.stringify(index, null, 0).replace(/","/g, '",\n"') + "\n");
if (import.meta.url === `file://${process.argv[1]}`) {
  const index = build(), cited = abbreviations();
  write("nameindex.json", index);
  write("abbreviations.json", cited);
  console.log(`nameindex: ${Object.keys(index).length} names; abbreviations: ${Object.keys(cited).length}`);
}
