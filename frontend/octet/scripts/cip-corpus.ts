// Octet's CIP labels against ChemDraw's own, in Sam's drawings (~/octet-research/corpus/sam; skipped when the folder
// is missing). ChemDraw saves its labels in CDXML: AS on each atom (R, S, r, s; u for a stereocentre it cannot
// settle, N for none) and BS on each bond (E, Z, u, N). Each drawing is read with Octet's CDXML reader and labelled
// as Show Stereochemistry labels it (chem.ts stereoLabels). Indigo's labels (what Octet showed before) are listed
// beside them. The drawings stay out of this repository: some hold ChemDraw clip art.
// Run: node scripts/cip-corpus.ts [--all] (--all lists every labelled atom and bond, not only the disagreements).
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import type { Mol } from "../src/render.ts";

const folder = `${homedir()}/octet-research/corpus/sam`;
if (!existsSync(folder)) { console.log("cip-corpus: skipped (no corpus)"); process.exit(0); }
const all = process.argv.includes("--all");
// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("../src/chem.ts");
const { fromCdxml, parseXml } = await import("../src/cdxml.ts");
const { fragments, subset } = await import("../src/edit.ts");
await chem.ready;
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();

// Indigo's labels for a structure (labels expanded), as Octet took them before it had its own labeller.
function indigoLabels(m: Mol): { atoms: (string | undefined)[]; bonds: (string | undefined)[] } | undefined {
  const bonds = m.bonds.filter((b) => b.type !== 10);
  const ket = { root: { nodes: [{ $ref: "mol0" }] }, mol0: { type: "molecule", atoms: m.atoms.map((a) => ({ label: a.label, location: a.location, ...(a.charge ? { charge: a.charge } : {}), ...(a.isotope ? { isotope: a.isotope } : {}) })), bonds: bonds.map((b) => ({ type: b.type === 14 ? 1 : b.type, atoms: b.atoms, ...(b.stereo ? { stereo: b.stereo } : {}) })) } };
  const o = new indigo.MapStringString();
  o.set("output-content-type", "application/json");
  try {
    const out = JSON.parse(JSON.parse(indigo.calculateCip(JSON.stringify(ket), "ket", o)).struct).mol0;
    const clean = (c?: string) => c?.replace(/[()]/g, "") || undefined;
    const map = new Map(bonds.map((b, n) => [b, n]));
    return { atoms: out.atoms.map((a: { cip?: string }) => clean(a.cip)), bonds: m.bonds.map((b) => (map.has(b) ? clean(out.bonds[map.get(b)!]?.cip) : undefined)) };
  } catch { return undefined; } finally { o.delete(); }
}

type X = { name: string; attrs: Record<string, string>; kids: X[] };
const tally = { atoms: 0, atomsAgree: 0, atomsIndigo: 0, bonds: 0, bondsAgree: 0, bondsIndigo: 0, extra: 0, extraIndigo: 0, unsettled: 0, unsettledOctet: 0 };
const lines: string[] = [];
for (const f of readdirSync(folder).filter((f) => f.endsWith(".cdxml")).sort()) {
  const tree = parseXml(readFileSync(`${folder}/${f}`, "utf8")) as X;
  // Each node gets a short atom number, so the atom Octet reads it as can be found.
  const code = new Map<string, string>(), as = new Map<string, string>(), bs: { B: string; E: string; BS: string }[] = [];
  const walk = (x: X) => {
    if (x.name === "n") { code.set(x.attrs.id, `n${code.size.toString(36)}`); x.attrs.ShowAtomNumber = "yes"; x.attrs.AtomNumber = code.get(x.attrs.id)!; if (x.attrs.AS) as.set(x.attrs.id, x.attrs.AS); }
    if (x.name === "b" && x.attrs.BS) bs.push({ B: x.attrs.B, E: x.attrs.E, BS: x.attrs.BS });
    x.kids.forEach(walk);
  };
  walk(tree);
  if (![...as.values(), ...bs.map((b) => b.BS)].some((v) => v !== "N")) continue;
  let m: Mol;
  try { m = fromCdxml(tree).mol; } catch { continue; }
  const back = new Map([...code].map(([id, c]) => [c, id])), idOf = m.atoms.map((a) => (a.number ? back.get(a.number) : undefined));
  m = { ...m, atoms: m.atoms.map((a) => ({ ...a, number: undefined })) };
  const octet = chem.stereoLabels(m);
  // Indigo, structure by structure, with labels expanded.
  const ind: { atoms: (string | undefined)[]; bonds: (string | undefined)[] } = { atoms: m.atoms.map(() => undefined), bonds: m.bonds.map(() => undefined) };
  for (const g of fragments(m)) {
    const ids = [...g].sort((a, b) => a - b), part = subset(m, new Set(ids)), { mol, from } = chem.expandWithOrigins(part), got = indigoLabels(mol);
    got?.atoms.forEach((c, k) => { if (c && !part.atoms[from[k]].text) ind.atoms[ids[from[k]]] = c; });
    const local = new Map(ids.map((i, n) => [i, n]));
    m.bonds.forEach((b, j) => {
      const [p, q] = b.atoms.map((i) => local.get(i));
      if (p === undefined || q === undefined) return;
      const k = mol.bonds.findIndex((x) => (from[x.atoms[0]] === p && from[x.atoms[1]] === q) || (from[x.atoms[0]] === q && from[x.atoms[1]] === p));
      if (k >= 0 && got?.bonds[k]) ind.bonds[j] = got.bonds[k];
    });
  }
  for (const [id, want] of as) {
    const i = idOf.indexOf(id);
    if (i < 0) continue;
    const ours = octet?.atoms[i], theirs = ind.atoms[i], label = /^[RSrs]$/.test(want);
    if (label) { tally.atoms++; if (ours === want) tally.atomsAgree++; if (theirs === want) tally.atomsIndigo++; }
    else if (want === "u") { tally.unsettled++; if (!ours) tally.unsettledOctet++; }
    else if (ours && /^[RSrs]$/.test(ours)) tally.extra++;
    if (want === "N" && theirs && /^[RSrs]$/.test(theirs)) tally.extraIndigo++;
    if (all ? want !== "N" || ours : (label && ours !== want) || (!label && ours && /^[RSrs]$/.test(ours))) lines.push(`${f.slice(0, 44).padEnd(44)} atom ${String(i).padEnd(4)} ${m.atoms[i].label.padEnd(2)} ChemDraw ${want}  Octet ${ours ?? "-"}  Indigo ${theirs ?? "-"}`);
  }
  for (const { B, E, BS } of bs) {
    const i = idOf.indexOf(B), j = idOf.indexOf(E), k = m.bonds.findIndex((b) => b.atoms.includes(i) && b.atoms.includes(j));
    if (k < 0) continue;
    const ours = octet?.bonds[k], theirs = ind.bonds[k], label = /^[EZ]$/.test(BS);
    if (label) { tally.bonds++; if (ours === BS) tally.bondsAgree++; if (theirs === BS) tally.bondsIndigo++; }
    else if (ours && /^[EZ]$/.test(ours)) tally.extra++;
    if (all ? BS !== "N" || ours : (label && ours !== BS) || (!label && ours && /^[EZ]$/.test(ours))) lines.push(`${f.slice(0, 44).padEnd(44)} bond ${String(k).padEnd(4)}    ChemDraw ${BS}  Octet ${ours ?? "-"}  Indigo ${theirs ?? "-"}`);
  }
}
console.log(`cip-corpus: stereocentres ChemDraw labels: ${tally.atoms}, Octet agrees on ${tally.atomsAgree} (Indigo ${tally.atomsIndigo})`);
console.log(`cip-corpus: double bonds ChemDraw labels: ${tally.bonds}, Octet agrees on ${tally.bondsAgree} (Indigo ${tally.bondsIndigo})`);
console.log(`cip-corpus: ChemDraw's unsettled centres (u): ${tally.unsettled}, Octet leaves ${tally.unsettledOctet} unlabelled`);
console.log(`cip-corpus: labels where ChemDraw has none: Octet ${tally.extra}, Indigo ${tally.extraIndigo} (atoms)`);
for (const l of lines) console.log(l);
