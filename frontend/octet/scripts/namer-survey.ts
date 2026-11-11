// Run: node src/namer.check.ts. Each name becomes a structure (OPSIN), Octet names the structure, and OPSIN must read
// Octet's name back as the same structure (same standard InChI). No wrong names are allowed; misses are counted.

import { existsSync, readFileSync } from "node:fs";
import { graphOf } from "../src/naming.ts";
import { iupacName, iupacNameWhy } from "../src/namer.ts";
import type { Mol } from "../src/render.ts";

const dir = new URL("../src/vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("namer.check: skipped (no OPSIN build)"); process.exit(0); }
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
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();
const convert = (s: string, f: string, dearomatize = false) => {
  const o = new indigo.MapStringString();
  if (dearomatize) o.set("dearomatize-on-load", "true");
  try { return indigo.convert(s, f, o).trim(); } finally { o.delete(); }
};
// The structure and its CIP labels, read from SMILES by Indigo (Kekulé bonds).
const parsed = (smiles: string) => {
  const o = new indigo.MapStringString();
  o.set("output-content-type", "application/json");
  o.set("dearomatize-on-load", "true");
  try {
    const ket = JSON.parse(JSON.parse(indigo.calculateCip(smiles, "ket", o)).struct);
    // Several fragments (a salt): one molecule with all of them.
    const atoms: { label: string; charge?: number; radical?: number; cip?: string }[] = [], bonds: { type: number; atoms: [number, number]; cip?: string }[] = [];
    for (const { $ref } of ket.root.nodes) {
      const f = ket[$ref], base = atoms.length;
      if (f?.type !== "molecule") continue;
      atoms.push(...f.atoms);
      bonds.push(...f.bonds.map((b: { type: number; atoms: [number, number]; cip?: string }) => ({ ...b, atoms: [b.atoms[0] + base, b.atoms[1] + base] })));
    }
    return { atoms, bonds };
  } finally { o.delete(); }
};
const molOf = (smiles: string): Mol => {
  const m = parsed(smiles);
  // A radical stays on its atom (KET's 1, 2 and 3 are Octet's 3, 1 and 2), so graphOf leaves the structure out.
  return { atoms: m.atoms.map((a) => ({ label: a.label, charge: a.charge, ...(a.radical ? { radical: a.radical === 1 ? 3 : a.radical - 1 } : {}), location: [0, 0, 0] as [number, number, number] })), bonds: m.bonds.map((b) => ({ type: b.type, atoms: b.atoms })) };
};
// The CIP labels Octet gives (src/cip.ts) the structure as it draws it from the SMILES (Indigo's layout, with wedges),
// on the atoms and bonds of `parsed`. chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does;
// these stand in for the browser.
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("../src/chem.ts");
await chem.ready;
let otherOrder = 0;
const cipOf = (smiles: string) => {
  const p = parsed(smiles), m = chem.parseStructure(smiles), cip = chem.cipOf(m), key = (b: { atoms: number[] }) => `${Math.min(...b.atoms)} ${Math.max(...b.atoms)}`;
  if (m.atoms.length !== p.atoms.length || m.atoms.some((a, i) => a.label !== p.atoms[i].label)) { otherOrder++; throw new Error("atom order"); }
  const bond = new Map(m.bonds.map((b, k) => [key(b), k]));
  // A drawn double bond always has a geometry; one the SMILES leaves open (Indigo gives it no label) has no E or Z.
  return { atoms: cip.atoms, bonds: p.bonds.map((b) => (b.cip ? cip.bonds[bond.get(key(b)) ?? -1] : undefined)) };
};
// The hydrogens in the input (Indigo's gross formula). A name that reads back wrong for a structure drawn with a
// different count from the input's is not counted: the drawing is not the input. withHydrogens() below gives each
// atom its count, so this is a check on that.
const hydrogensOf = (smiles: string) => {
  const o = new indigo.MapStringString(), sel = new indigo.VectorInt();
  try { return [...String(JSON.parse(indigo.calculate(smiles, o, sel))["gross-formula"]).matchAll(/\bH(\d*)(?![a-z])/g)].reduce((t, m) => t + Number(m[1] || 1), 0); } finally { o.delete(); sel.delete(); }
};


// The gap survey (not a check): every name OPSIN knows by name (names.txt), Octet's reagent names (common.ts) and
// drug names (drugs.ts), drawn from OPSIN's SMILES, then named by Octet and read back. Prints the reasons Octet
// gives no name, largest first, and every name that reads back as a different structure.
// Run: node scripts/namer-survey.ts [limit | corpus] [--save file]. --save writes the inputs named right to the file,
// one per line, and the wrong ones to file.wrong, so two versions of the namer can be compared input by input.
import { COMMON } from "../src/common.ts";
import { DRUGS } from "../src/drugs.ts";
void iupacName;
const args = process.argv.slice(2), at = args.indexOf("--save");
const save = at < 0 ? undefined : args.splice(at, 2)[1];
const corpus = args[0] === "corpus";
const limit = corpus ? Infinity : Number(args[0] ?? Infinity);
const inputs: string[] = [...new Set([
  ...readFileSync(new URL("names.txt", dir), "utf8").split("\n").map((s) => s.trim()).filter(Boolean),
  ...Object.values(COMMON).filter((v) => !v.startsWith("smiles:")),
  ...Object.keys(DRUGS),
])].slice(0, limit);
// "corpus": the structures in Sam's ChemDraw files (~/octet-research/corpus/sam), read by Indigo, one per fragment.
const drawings = new Map<string, Mol>(); // corpus: each structure's drawing, labels expanded, by its SMILES
if (corpus) {
  const { readdirSync } = await import("node:fs");
  const { homedir } = await import("node:os");
  const { fromCdxml } = await import("../src/cdxml.ts");
  const { fragments, subset } = await import("../src/edit.ts");
  const folder = `${homedir()}/octet-research/corpus/sam`;
  const found = new Set<string>();
  for (const f of readdirSync(folder).filter((f) => f.endsWith(".cdxml"))) {
    let m: Mol;
    try { m = fromCdxml(readFileSync(`${folder}/${f}`, "utf8")).mol; } catch { continue; }
    for (const g of fragments(m)) {
      if (g.length < 3) continue;
      try {
        const part = chem.expandLabels(subset(m, new Set(g))), smiles = chem.toSmiles(part).split(" ")[0];
        if (smiles && !smiles.includes("*") && !smiles.includes(".")) { found.add(smiles); if (!drawings.has(smiles)) drawings.set(smiles, part); }
      } catch { /* a part Indigo cannot read */ }
    }
  }
  inputs.length = 0;
  inputs.push(...[...found].map((x) => `smiles:${x}`));
}
// Each atom's hydrogen count as the SMILES gives it ([N] none, [PH5] five, [SbH] one), and its isotope: Indigo adds
// the hydrogens as atoms after each fragment's own atoms. molOf alone gives every atom its usual count.
const withHydrogens = (m: Mol, smiles: string): Mol => {
  const o = new indigo.MapStringString();
  o.set("output-content-type", "application/json");
  o.set("dearomatize-on-load", "true");
  try {
    const frags = (ket: { root: { nodes: { $ref: string }[] }; [k: string]: unknown }) => ket.root.nodes.map(({ $ref }) => ket[$ref] as { type: string; atoms: { isotope?: number }[]; bonds: { atoms: [number, number] }[] }).filter((f) => f?.type === "molecule");
    const before = frags(JSON.parse(JSON.parse(indigo.calculateCip(smiles, "ket", o)).struct));
    const after = frags(JSON.parse(JSON.parse(indigo.convert_explicit_hydrogens(smiles, "unfold", "ket", o)).struct)), h: number[] = [];
    if (before.length !== after.length) return m;
    before.forEach((f, k) => {
      const own = f.atoms.length, count = f.atoms.map(() => 0);
      for (const b of after[k].bonds) if (b.atoms[1] >= own) count[b.atoms[0]]++; else if (b.atoms[0] >= own) count[b.atoms[1]]++;
      h.push(...count);
    });
    const isotopes = before.flatMap((f) => f.atoms.map((a) => a.isotope));
    return h.length === m.atoms.length ? { ...m, atoms: m.atoms.map((a, i) => ({ ...a, implicitHCount: h[i], ...(isotopes[i] ? { isotope: isotopes[i] } : {}) })) } : m;
  } catch { return m; } finally { o.delete(); }
};
const why = new Map<string, string[]>(), wrong: string[] = [], right: string[] = [], otherH: string[] = [], unread: string[] = [], complexes: string[] = [];
// The name complexes.ts gives a structure with a metal atom: the corpus drawing itself, or the structure drawn from
// SMILES with a bracket atom's hydrogens on a metal as its label (NH3), as the app draws ammine ligands.
const { complexName } = await import("../src/complexes.ts");
const opsinApi = {
  read: (n: string) => { try { return opsin.parseToSmiles(n) ?? undefined; } catch { return undefined; } },
  atoms: (n: string) => { try { return opsin.parseToAtoms(n) ?? undefined; } catch { return undefined; } },
  inchi: chem.toInchi, aux: chem.toInchiAux, cip: chem.cipOf,
};
const complexOf = (smiles: string): string | undefined => {
  // A metal, or a main-group atom that can be a central atom (complexes.ts MAIN).
  if (!/\[(?:Li|Na|K|Be|Mg|Ca|Sc|Ti|V|Cr|Mn|Fe|Co|Ni|Cu|Zn|Y|Zr|Nb|Mo|Tc|Ru|Rh|Pd|Ag|Cd|La|Hf|Ta|W|Re|Os|Ir|Pt|Au|U)\b|B(?!r)|Al|Ga|In|Si|Ge|Sn|Pb|P|As|Sb/.test(smiles)) return undefined;
  try {
    let m = drawings.get(smiles);
    if (!m) {
      const d = chem.parseStructure(smiles), tokens = [...smiles.matchAll(/\[[^\]]+\]|Cl|Br|[BCNOPSFI]|[bcnops]/g)].map((t) => t[0]);
      if (tokens.length !== d.atoms.length) return undefined;
      const metal = (i: number) => /^\[(?!(?:H|B|C|N|O|F|Si|P|S|Cl|As|Se|Br|Te|I)\b)[A-Z]/.test(tokens[i]);
      m = chem.expandLabels({ ...d, atoms: d.atoms.map((a, i) => {
        const h = /^\[([A-Z][a-z]?)H(\d*)/.exec(tokens[i]);
        return h && d.bonds.some((b) => b.atoms.includes(i) && metal(b.atoms[0] === i ? b.atoms[1] : b.atoms[0])) ? { ...a, text: `${h[1]}H${h[2]}` } : a;
      }) });
    }
    return complexName(m, opsinApi);
  } catch { return undefined; }
};
let tried = 0, named = 0;
for (const input of inputs) {
  let smiles: string | null = null;
  try { smiles = input.startsWith("smiles:") ? input.slice(7) : opsin.parseToSmiles(input); } catch { smiles = null; }
  if (!smiles || smiles.includes("*")) continue;
  let g;
  try { g = graphOf(withHydrogens(molOf(smiles), smiles), cipOf(smiles), true); } catch { continue; } // with isotopes, as the app names them
  if (!g) continue;
  tried++;
  const r = iupacNameWhy(g);
  if (!r.name) {
    // A coordination compound: named by complexes.ts, which checks its name in parts (OPSIN reads no κ).
    const cx = complexOf(smiles);
    if (cx) { named++; right.push(input); complexes.push(`${input} -> ${cx}`); continue; }
    const k = r.why ?? "?"; why.set(k, [...(why.get(k) ?? []), input]); continue;
  }
  let back: string | null = null;
  try { back = opsin.parseToSmiles(r.name); } catch { back = null; }
  if (back && convert(back, "inchi") === convert(smiles, "inchi")) { named++; right.push(input); }
  else if (hydrogensOf(smiles) !== g.atoms.reduce((t, a) => t + a.h + (a.el === "H" ? 1 : 0), 0)) { otherH.push(`${input} -> ${r.name}`); tried--; }
  // A name OPSIN cannot parse is not shown in the app (naming.ts checkedName), so it is not a wrong name. It is
  // listed with the names OPSIN cannot read.
  else if (!back) unread.push(`${input} -> ${r.name}`);
  else wrong.push(`${input} -> ${r.name}`);
}
console.log(`survey: ${tried} structures, ${named} named right (${(100 * named / tried).toFixed(1)}%), ${wrong.length} wrong, ${tried - named - wrong.length} unnamed`);
if (complexes.length) console.log(`named as complexes, checked in parts by complexes.ts (${complexes.length}): ${complexes.slice(0, 40).join("; ")}`);
if (unread.length) console.log(`names OPSIN cannot read (${unread.length}): ${unread.slice(0, 20).join("; ")}`);
if (otherOrder) console.log(`left out, read in another atom order (${otherOrder})`);
if (otherH.length) console.log(`left out, drawn with other hydrogen counts (${otherH.length}): ${otherH.slice(0, 6).join("; ")}`);
for (const [k, v] of [...why].sort((a, b) => b[1].length - a[1].length)) console.log(`${String(v.length).padStart(5)}  ${k}: ${v.slice(0, 6).join("; ")}`);
if (save) { const { writeFileSync } = await import("node:fs"); writeFileSync(save, `${right.join("\n")}\n`); writeFileSync(`${save}.wrong`, `${wrong.join("\n")}\n`); }
if (wrong.length) console.log(`WRONG (${wrong.length}): ${wrong.slice(0, 40).join("; ")}`);
