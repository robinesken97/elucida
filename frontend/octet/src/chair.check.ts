// Run: node src/chair.check.ts. Fails loudly if a chair drawn by hand stops reading as its stereoisomer, or if the bold
// and wedged edges that draw a ring in perspective start reading as stereochemistry again (issue 46).
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { EMPTY, addChair, chairHydrogens, chairOf, deleteAtom, mayHaveChair, perspectiveBonds, setElement, setLabel, sprout } from "./edit.ts";
import type { Bond, Mol } from "./render.ts";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
await chem.ready;

// Speed. Every structure update reads chairs (formula, stereochemistry, name and warnings expand labels first), so a
// drawing with no chair must cost no more than it did before chairs were read (f11487e). The chair work
// (perspectiveBonds and chairHydrogens) is timed against the rest of expandWithOrigins on the same drawing, each on
// fresh copies so nothing kept is reused: the rest does what f11487e's whole expandWithOrigins did, a little faster.
// Measured on Sam's Mac: 0.27 to 0.31 for a 741-atom peptide and 0.35 to 0.37 for 40 paclitaxels in one drawing; with
// the ring search on every drawing (before the chair test) it was 1.5 and 8.5. The bound, 0.6, is twice the highest
// measured share, and well below a ring search.
{
  const peptide = chem.indigoLayout("N[C@@H](C)C(=O)N[C@@H](CC(C)C)C(=O)N[C@@H](Cc1ccccc1)C(=O)N[C@@H](CO)C(=O)N1CCC[C@H]1C(=O)".repeat(20) + "O");
  const one = chem.indigoLayout("CC1=C2[C@@]([C@]([C@H]([C@@H]3[C@]4([C@H](OC4)C[C@@H]([C@]3(C(=O)[C@@H]2OC(=O)C)C)O)OC(=O)C)OC(=O)c5ccccc5)(C[C@@H]1OC(=O)[C@H](O)[C@@H](NC(=O)c6ccccc6)c7ccccc7)O)(C)C");
  const taxols: Mol = { atoms: [], bonds: [] };
  for (let k = 0; k < 40; k++) {
    const b = taxols.atoms.length;
    taxols.atoms.push(...one.atoms.map((a) => ({ ...a, location: [a.location[0] + 20 * (k % 8), a.location[1] + 20 * Math.floor(k / 8), 0] as [number, number, number] })));
    taxols.bonds.push(...one.bonds.map((x) => ({ ...x, atoms: [x.atoms[0] + b, x.atoms[1] + b] as [number, number] })));
  }
  const fresh = (m: Mol): Mol => ({ atoms: m.atoms.map((a) => ({ ...a })), bonds: m.bonds.map((b) => ({ ...b })) });
  const median = (t: number[]) => [...t].sort((x, y) => x - y)[t.length >> 1];
  for (const [what, m] of [["741-atom peptide", peptide], ["40 paclitaxels", taxols]] as const) {
    assert.equal(peptide.atoms.length, 741);
    assert.ok(!mayHaveChair(m), `${what}: no chair`);
    const chair: number[] = [], whole: number[] = [];
    for (let r = 0; r < 70; r++) {
      const x = fresh(m), y = fresh(m);
      let t = performance.now();
      perspectiveBonds(x);
      chairHydrogens(x);
      const c = performance.now() - t;
      t = performance.now();
      chem.expandWithOrigins(y);
      if (r >= 10) { chair.push(c); whole.push(performance.now() - t); }
    }
    const share = median(chair) / (median(whole) - median(chair));
    assert.ok(share < 0.6, `${what}: chair work ${median(chair).toFixed(3)} ms is ${share.toFixed(2)} of the rest of expandWithOrigins (${(median(whole) - median(chair)).toFixed(3)} ms)`);
    assert.ok(median(chair) < 1, `${what}: chair work under 1 ms`);
  }
  assert.ok(mayHaveChair(addChair(EMPTY, 1, { point: [0, 0] })) && mayHaveChair(addChair(EMPTY, 2, { point: [0, 0], turn: 1 })), "a chair is a possible chair");
}
console.log("chair.check: drawings with no chair cost no ring search ok");

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("chair.check: skipped (no OPSIN build)"); process.exit(0); }
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
const { problems } = await import("./check.ts");
setNamer(iupacName);
setComplexNamer((m) => complexName(m, { read: nameToSmiles, atoms: nameToAtoms, inchi: chem.toInchi, aux: chem.toInchiAux, cip: chem.cipOf }));
const inchiOf = (s: Mol | string) => { try { return chem.toInchi(typeof s === "string" ? chem.parseStructure(s) : s); } catch { return undefined; } };
// As the editor names (Editor.tsx nameFor).
const nameFor = (m: Mol) => { const name = checkedName(m, chem.expandLabels(m), nameToSmiles, inchiOf, chem.cipOf, knownName); return name && withAbbreviation(name, abbreviationOf(inchiOf(m))); };
const warnings = (m: Mol) => problems({ ...m, atoms: m.atoms.map((a) => ({ ...a, cip: true as const })) }, chem.stereoFacts(m)).map((p) => p.type);

// A chair drawn as the Chair tool draws one: atoms 0 to 5 round it, 0 the left tip (its axial bond up) and 3 the right
// tip (down); the lower edge (1 and 2) is nearest. The ring O of a pyranose is 4, at the back on the right, so 3 is C1,
// 2 C2, 1 C3, 0 C4 and 5 C5, as textbooks draw D-glucopyranose (4C1).
const chair = (turn = 0): Mol => addChair(EMPTY, 1, { point: [0, 0], turn });
// A substituent on ring atom i, labelled text: axial (the first bond the Bond tool adds there), or equatorial (the
// second, with the first then deleted).
function off(m: Mol, i: number, text: string, axial: boolean): Mol {
  m = sprout(m, i);
  if (!axial) { m = sprout(m, i); m = deleteAtom(m, m.atoms.length - 2); }
  return setLabel(m, m.atoms.length - 1, text);
}
// N-acetylglucosamine as issue 46 draws it: every group equatorial (β), or the anomeric OH axial (α).
function glcNAc(alpha: boolean, turn = 0): Mol {
  let m = setElement(chair(turn), 4, "O");
  m = off(m, 3, "OH", alpha);
  m = off(m, 2, "NHAc", false);
  m = off(m, 1, "OH", false);
  m = off(m, 0, "OH", false);
  return off(m, 5, "CH2OH", false);
}
const ref = (name: string) => inchiOf(nameToSmiles(name) ?? assert.fail(`${name} is read`));
const beta = ref("2-acetamido-2-deoxy-beta-D-glucopyranose"), alpha = ref("2-acetamido-2-deoxy-alpha-D-glucopyranose");
assert.ok(beta && alpha && beta !== alpha);

// The chair is read: up the page, its ring atoms axial up and down in turn.
{
  const m = chair(), c = chairOf(m, [0, 1, 2, 3, 4, 5])!;
  assert.ok(c && c.up[1] > 0.99, "upright");
  assert.deepEqual(c.axial.map((d) => Math.sign(d[1])), [1, -1, 1, -1, 1, -1]);
  assert.equal(chairOf({ ...m, atoms: m.atoms.map((a, i) => ({ ...a, location: [Math.cos(i), Math.sin(i), 0] as [number, number, number] })) }, [0, 1, 2, 3, 4, 5]), undefined, "a flat hexagon is no chair");
}
// β and α N-acetylglucosamine drawn by hand are the stereoisomers, and their names have every descriptor.
for (const [a, want, desc] of [[false, beta, "(2R,3R,4R,5S,6R)"], [true, alpha, "(2S,3R,4R,5S,6R)"]] as const) {
  const m = glcNAc(a), what = a ? "α" : "β";
  assert.equal(chairHydrogens(m).length, 5, `${what}: five centres read`);
  assert.equal(inchiOf(m), want, `${what}-N-acetylglucosamine drawn as a chair`);
  const name = nameFor(m);
  assert.ok(name?.includes(desc), `${what}: ${name}`);
  assert.equal(inchiOf(nameToSmiles(name!.replace(/ \([^()]*\)$/, ""))!), want, `${what}: the name reads back`);
  assert.deepEqual(warnings(m), [], `${what}: no stereo warnings`);
  // Show Stereochemistry labels the five centres, as the name has them.
  assert.equal(chem.stereoLabels(m)?.atoms.filter(Boolean).length, 5, `${what}: R and S shown`);
  // Turned a little on the page, it reads the same; turned on its side, it is not read (no guess).
  assert.equal(inchiOf(glcNAc(a, (15 * Math.PI) / 180)), want, `${what} turned 15°`);
  assert.equal(chairHydrogens(glcNAc(a, Math.PI / 2)).length, 0, `${what} on its side`);
}
console.log("chair.check: N-acetylglucosamine drawn as a chair named with its stereochemistry ok");

// The bold and wedged front edges of issue 46: depth, not stereochemistry. Cyclohexane names and has no warnings; the
// sugar still names as drawn without them. Its bold edge low (nearest), as drawn.
const front = (m: Mol): Mol => ({ ...m, bonds: m.bonds.map((b): Bond => {
  const k = [0, 1, 2, 3].findIndex((x) => b.atoms.includes(x) && b.atoms.includes(x + 1));
  return k === 1 ? { ...b, display: "bold" } : k === 0 ? { ...b, atoms: [0, 1], stereo: 1 } : k === 2 ? { ...b, atoms: [3, 2], stereo: 1 } : b;
}) });
{
  const c = front(chair());
  assert.equal(perspectiveBonds(c).size, 3);
  assert.equal(nameFor(c), "cyclohexane");
  assert.deepEqual(warnings(c), []);
  for (const [a, want] of [[false, beta], [true, alpha]] as const) {
    const m = front(glcNAc(a));
    assert.equal(inchiOf(m), want, `${a ? "α" : "β"} with bold and wedged edges`);
    assert.deepEqual(warnings(m), [], "no warning on the edges");
    assert.ok(nameFor(m)?.includes(a ? "(2S,3R,4R,5S,6R)" : "(2R,3R,4R,5S,6R)"));
  }
  // The bold edge drawn at the top: the chair is seen from below, so it is the mirror image (L).
  const top: Mol = { ...glcNAc(false), bonds: glcNAc(false).bonds.map((b): Bond => (b.atoms.includes(4) && b.atoms.includes(5) ? { ...b, display: "bold" } : b.atoms.includes(5) && b.atoms.includes(0) ? { ...b, atoms: [0, 5], stereo: 1 } : b)) };
  assert.equal(inchiOf(top), ref("2-acetamido-2-deoxy-beta-L-glucopyranose"), "seen from below");
}
// The same on the Conformers templates, which have depth (issue 46 pasted the chair): read in 3D as before.
{
  const lib = JSON.parse(readFileSync(new URL("./library.json", import.meta.url), "utf8"));
  const find = (o: unknown, n: string): { mol: Mol } | undefined => {
    if (Array.isArray(o)) { for (const x of o) { const r = find(x, n); if (r) return r; } return undefined; }
    if (!o || typeof o !== "object") return undefined;
    if ((o as { name?: string }).name === n && "mol" in o) return o as { mol: Mol };
    for (const v of Object.values(o)) { const r = find(v, n); if (r) return r; }
    return undefined;
  };
  // Front edges: the lowest bond bold, a wedge from each of its ends' other ring neighbours to them.
  const edged = (m: Mol): Mol => {
    const ring = [0, 1, 2, 3, 4, 5], y = (i: number) => m.atoms[i].location[1], k = ring.reduce((a, b) => (y(a) + y((a + 1) % 6) < y(b) + y((b + 1) % 6) ? a : b));
    const [p, q] = [k, (k + 1) % 6], [pp, qq] = [(k + 5) % 6, (k + 2) % 6];
    return { ...m, bonds: m.bonds.map((b): Bond => (b.atoms.includes(p) && b.atoms.includes(q) ? { ...b, display: "bold" } : b.atoms.includes(p) && b.atoms.includes(pp) ? { ...b, atoms: [pp, p], stereo: 1 } : b.atoms.includes(q) && b.atoms.includes(qq) ? { ...b, atoms: [qq, q], stereo: 1 } : b)) };
  };
  const cy = edged(find(lib, "Cyclohexane chair")!.mol), glc = find(lib, "β-D-Glucopyranose (chair)")!.mol;
  assert.equal(perspectiveBonds(cy).size, 3);
  assert.equal(nameFor(cy), "cyclohexane");
  assert.deepEqual(warnings(cy), []);
  assert.equal(inchiOf(edged(glc)), inchiOf(glc), "β-D-glucopyranose's template with front edges");
  assert.equal(inchiOf(glc), ref("beta-D-glucopyranose"));
  // Drawn flat, the template reads the same from its chair.
  assert.equal(inchiOf({ ...glc, atoms: glc.atoms.map((a) => ({ ...a, location: [a.location[0], a.location[1], 0] as [number, number, number] })) }), inchiOf(glc), "β-D-glucopyranose flat");
}
console.log("chair.check: bold and wedged ring edges draw depth, not stereochemistry ok");

// Never a guess: a flat ring, a wedge off the chair (the wedges set it), and a wedge on a flat ring's bond (a real
// stereo bond) are left as they are.
{
  const hexagon: Mol = { atoms: [0, 1, 2, 3, 4, 5].map((k) => ({ label: "C", location: [Math.cos((k * Math.PI) / 3), Math.sin((k * Math.PI) / 3), 0] as [number, number, number] })),
    bonds: [0, 1, 2, 3, 4, 5].map((k) => ({ type: 1, atoms: [k, (k + 1) % 6] as [number, number] })) };
  const subbed = [0, 2].reduce((m, i) => { const p = m.atoms[i].location; return { atoms: [...m.atoms, { label: "O", location: [p[0] * 2, p[1] * 2, 0] as [number, number, number] }], bonds: [...m.bonds, { type: 1, atoms: [i, m.atoms.length] as [number, number] }] }; }, hexagon);
  assert.equal(chairHydrogens(subbed).length, 0, "a flat ring sets nothing");
  const wedged = glcNAc(false), k = wedged.bonds.findIndex((b) => b.atoms.includes(3) && b.atoms.some((x) => x > 5));
  assert.equal(chairHydrogens({ ...wedged, bonds: wedged.bonds.map((b, n) => (n === k ? { ...b, atoms: [3, b.atoms.find((x) => x !== 3)!] as [number, number], stereo: 6 as const } : b)) }).length, 0, "a wedge off the ring: the wedges set it");
  assert.equal(perspectiveBonds({ ...subbed, bonds: subbed.bonds.map((b, n) => (n === 0 ? { ...b, stereo: 1 as const } : b)) }).size, 0, "a wedge on a flat ring's bond is stereo");
}
console.log("chair.check: flat rings and wedged chairs left as drawn ok");

// Two chairs that share a bond (trans-decalin, as a steroid is drawn): each carbon where they join is read once, so
// the formula keeps its H count and the flat drawing reads as the same structure in 3D does.
{
  const R = 0.9428, z0 = 0.1667, A = [0, 1, 2, 3, 4, 5].map((k) => [R * Math.cos((k * Math.PI) / 3), k % 2 ? z0 : -z0, R * Math.sin((k * Math.PI) / 3)]);
  // Ring B is ring A turned through the middle of their shared bond (0 to 1); an O on atom 3, equatorial.
  const mid = A[0].map((x, i) => (x + A[1][i]) / 2), o = A[3].map((x, i) => (i === 1 ? x - 0.33 : x + (x / R) * 0.94));
  const pts = [...A, ...[2, 3, 4, 5].map((k) => A[k].map((x, i) => 2 * mid[i] - x)), o];
  const view = (p: number[]): [number, number, number] => { const t = (20 * Math.PI) / 180; return [p[2], p[1] * Math.cos(t) + p[0] * Math.sin(t), p[1] * Math.sin(t) - p[0] * Math.cos(t)]; };
  const bonds = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0], [0, 6], [6, 7], [7, 8], [8, 9], [9, 1], [3, 10]].map((a) => ({ type: 1, atoms: a as [number, number] }));
  const deep: Mol = { atoms: pts.map((p, i) => ({ label: i === 10 ? "O" : "C", location: view(p) })), bonds };
  const flat: Mol = { ...deep, atoms: deep.atoms.map((a) => ({ ...a, location: [a.location[0], a.location[1], 0] as [number, number, number] })) };
  assert.ok(chairOf(flat, [0, 1, 2, 3, 4, 5]) && chairOf(flat, [0, 6, 7, 8, 9, 1]), "both rings are chairs");
  assert.deepEqual(chairHydrogens(flat).map((h) => h.centre).sort(), [0, 1, 3], "each centre read once");
  assert.equal(chem.analyse(flat)?.[0].formula, "C10H18O");
  assert.ok(/\/t8-,9-,10-/.test(inchiOf(deep) ?? ""), "the 3D drawing has three centres");
  assert.equal(inchiOf(flat), inchiOf(deep), "trans-decalinol drawn flat as two chairs");
}
console.log("chair.check: fused chairs read once at each shared carbon ok");
