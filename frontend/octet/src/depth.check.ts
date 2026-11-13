// Run: node src/depth.check.ts. Fails if a structure with depth (from a CIF or 3D MOL file, or 3D Clean Up) waits for
// its stereochemistry to give its formula, or can stop the editor for good. Indigo reads stereocentres from depth with
// a symmetry search that has no limit: tetrakis(triisopropylsilyl)silane with its hydrogens drawn as atoms took 20
// seconds for its formula, and the Actions panel stopped the window with it. The checks run in a child process that is
// stopped after 30 seconds, so a hang fails here.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

if (process.argv[2] !== "run") {
  const run = spawnSync(process.execPath, [fileURLToPath(import.meta.url), "run"], { stdio: ["ignore", "inherit", "inherit"], timeout: 30_000 });
  assert.equal(run.signal, null, "depth.check: a call never ended (stopped after 30 seconds)");
  process.exit(run.status ?? 1);
}

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
const { hydrogens } = await import("./render.ts");
type Mol = import("./render.ts").Mol;
await chem.ready;

// A structure with every hydrogen drawn as an atom and each atom at its own depth, as a CIF file gives it.
let seed = 7;
const depth = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) - 0.5;
function in3d(smiles: string): Mol {
  const m = chem.parseStructure(smiles), used = m.atoms.map(() => 0);
  for (const b of m.bonds) for (const i of b.atoms) used[i] += b.type;
  const atoms = m.atoms.map((a) => ({ ...a, location: [a.location[0], a.location[1], depth()] as [number, number, number] })), bonds = [...m.bonds];
  m.atoms.forEach((a, i) => {
    for (let k = hydrogens(a.label, 0, used[i]); k > 0; k--) {
      atoms.push({ label: "H", location: [a.location[0] + 0.3 * Math.cos(k * 2), a.location[1] + 0.3 * Math.sin(k * 2), depth()] });
      bonds.push({ type: 1, atoms: [i, atoms.length - 1] });
    }
  });
  return { atoms, bonds };
}
const timed = <T>(f: () => T): [T | Error, number] => { const t = performance.now(); try { return [f(), performance.now() - t]; } catch (e) { return [e as Error, performance.now() - t]; } };

const tips = "[Si](C(C)C)(C(C)C)C(C)C", busy = in3d(`[Si](${tips})(${tips})(${tips})${tips}`);
assert.equal(busy.atoms.length, 125);
// The formula and masses do not read stereochemistry, so they do not need the depth: they come at once.
const [found, ms] = timed(() => chem.analyse(busy));
assert.ok(ms < 1000, `the formula took ${Math.round(ms)} ms`);
assert.equal((found as chem.Analysis)[0].formula, "C36H84Si5");
// A call that reads stereochemistry stops at Indigo's timeout (10 seconds) and fails, so the window is free again.
const [smiles, smilesMs] = timed(() => chem.toSmiles(busy));
assert.ok(smiles instanceof RangeError, "SMILES past the ceiling fails");
assert.ok(smilesMs < 11_000, `the SMILES took ${Math.round(smilesMs)} ms`);
console.log("depth.check: a crowded structure with depth gives its formula and does not stop the editor ok");

// Depth still sets stereochemistry where it is read: L-alanine in 3D is L-alanine.
const alanine: Mol = {
  atoms: ([["C", -0.577, 0.433, 0.017], ["C", 0.877, 0.034, -0.143], ["C", -1.418, -0.782, 0.31], ["N", -1.046, 1.16, -1.146], ["O", 1.36, -0.984, 0.322], ["O", 1.647, 0.891, -0.836], ["H", -0.66, 1.123, 0.86]] as const)
    .map(([label, x, y, z]) => ({ label, location: [x, y, z] as [number, number, number] })),
  bonds: [[0, 1, 1], [0, 2, 1], [0, 3, 1], [1, 4, 2], [1, 5, 1], [0, 6, 1]].map(([p, q, type]) => ({ type, atoms: [p, q] as [number, number] })),
};
assert.equal(chem.toInchi(alanine), "InChI=1S/C3H7NO2/c1-2(4)3(5)6/h2H,4H2,1H3,(H,5,6)/t2-/m0/s1");
assert.equal(chem.analyse(alanine)?.[0].formula, "C3H7NO2");
console.log("depth.check: depth still gives a stereocentre its hand ok");

// 3D Clean Up keeps what a structure is. Its SMILES and InChI are the same after one clean-up, after a second, after a
// turn in 3D (Structure Perspective) and after Flatten: each command keeps the wedges reading as they did (cip.ts
// keepHands, as the editor calls it). Before, 42 of 222 test structures read as another stereoisomer after a clean-up.
const { clean3d } = await import("./clean3d.ts");
const { flattenAtoms, tiltAtoms } = await import("./edit.ts");
const { keepHands } = await import("./cip.ts");
const ids = (m: Mol) => m.atoms.map((_, i) => i);
const cleanUp = (m: Mol) => keepHands(m, clean3d(m, ids(m)), ids(m)); // Editor.tsx clean_3d
const KEPT: [string, string][] = [
  ["menthol", "C[C@@H]1CC[C@H]([C@@H](C1)O)C(C)C"], ["an all-axial menthol", "CC(C)[C@@H]1CC[C@H](C)C[C@@H]1O"], ["glucose", "OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O"],
  ["cholesterol", "C[C@H](CCCC(C)C)[C@H]1CC[C@@H]2[C@@]1(CC[C@H]3[C@H]2CC=C4[C@@]3(CC[C@@H](C4)O)C)C"], ["morphine", "CN1CC[C@]23[C@@H]4[C@H]1CC5=C2C(=C(C=C5)O)O[C@H]3[C@H](C=C4)O"],
  ["camphor", "CC1(C)[C@@H]2CC[C@@]1(C)C(=O)C2"], ["artemisinin", "C[C@@H]1CC[C@H]2[C@H](C(=O)O[C@H]3[C@@]24[C@H]1CC[C@](O3)(OO4)C)C"], ["sparteine", "[H][C@@]12CCCCN1C[C@@H]1C[C@H]2CN2CCCC[C@@]12[H]"],
  ["oxycodone", "CN1CC[C@]23[C@@H]4C(=O)CC[C@]2([C@H]1CC5=C3C(=C(C=C5)OC)O4)O"], ["sofosbuvir", "CC(C)OC(=O)[C@H](C)N[P@](=O)(OC[C@H]1O[C@@H](N2C=CC(=O)NC2=O)[C@](C)(F)[C@@H]1O)Oc1ccccc1"],
];
for (const [name, text] of KEPT) {
  const m = chem.fullMol(text), once = cleanUp(m), twice = cleanUp(once), every = new Set(ids(m));
  const middle = [0, 1, 2].map((e) => once.atoms.reduce((t, a) => t + a.location[e], 0) / once.atoms.length) as [number, number, number];
  assert.ok(once.atoms.some((a) => Math.abs(a.location[2]) > 0.2), `${name} has depth`);
  const turned = keepHands(once, tiltAtoms(once, every, middle, 70, 40), every), behind = keepHands(m, tiltAtoms(m, every, middle, 180, 0), every); // Editor.tsx, a Structure Perspective turn
  for (const [what, r] of [["3D Clean Up", once], ["a second 3D Clean Up", twice], ["a turn in 3D", turned], ["a turn of the flat drawing to its back", behind], ["Flatten", flattenAtoms(once, every)]] as const) {
    assert.equal(chem.toSmiles(r), chem.toSmiles(m), `${name} keeps its SMILES after ${what}`);
    assert.equal(chem.toInchi(r), chem.toInchi(m), `${name} keeps its InChI after ${what}`);
  }
}
// Only the structure that is cleaned up or flattened gets its wedges looked at.
{
  const m = chem.fullMol(KEPT[0][1] + ".CCO"), part = m.atoms.map((_, i) => i).filter((i) => i >= m.atoms.length - 3), all3 = cleanUp(m);
  const other = keepHands(all3, clean3d(all3, part), part);
  assert.deepEqual(other.bonds.map((b) => b.stereo), all3.bonds.map((b) => b.stereo), "cleaning up the ethanol leaves the menthol's wedges");
  assert.deepEqual(flattenAtoms(all3, new Set(part)).bonds.map((b) => b.stereo), all3.bonds.map((b) => b.stereo), "flattening the ethanol leaves the menthol's wedges");
}
console.log("depth.check: a structure reads as the same stereoisomer after 3D Clean Up, a turn in 3D and Flatten ok");

// Shapes 3D Clean Up got wrong (12 November 2026), from the drawings their SMILES give.
const span = (m: Mol, e: number) => Math.max(...m.atoms.map((a) => a.location[e])) - Math.min(...m.atoms.map((a) => a.location[e]));
const bondOf = (m: Mol) => { const l = m.bonds.map((b) => Math.hypot(...[0, 1, 2].map((e) => m.atoms[b.atoms[0]].location[e] - m.atoms[b.atoms[1]].location[e]))).sort((a, b) => a - b); return l[l.length >> 1]; };
const cleaned = (text: string) => { const m = chem.fullMol(text); return clean3d(m, ids(m)); };
const near = (m: Mol) => { const n: number[][] = m.atoms.map(() => []); for (const b of m.bonds) { n[b.atoms[0]].push(b.atoms[1]); n[b.atoms[1]].push(b.atoms[0]); } return n; };
const angleAt = (m: Mol, i: number, k: number, j: number) => {
  const [u, v] = [i, j].map((q) => [0, 1, 2].map((e) => m.atoms[q].location[e] - m.atoms[k].location[e]));
  return (Math.acos((u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) / (Math.hypot(...u) * Math.hypot(...v))) * 180) / Math.PI;
};
const angles = (m: Mol) => near(m).flatMap((n, k) => n.flatMap((i, x) => n.slice(x + 1).map((j) => angleAt(m, i, k, j))));
const torsionOf = (m: Mol, i: number, j: number, k: number, l: number) => {
  const v = (a: number, b: number) => [0, 1, 2].map((e) => m.atoms[b].location[e] - m.atoms[a].location[e]), c = (a: number[], b: number[]) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const d = (a: number[], b: number[]) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], [b1, b2, b3] = [v(i, j), v(j, k), v(k, l)], n1 = c(b1, b2), n2 = c(b2, b3);
  return (Math.atan2(d(c(n1, b2.map((q) => q / Math.hypot(...b2))), n2), d(n1, n2)) * 180) / Math.PI;
};
// The saturated six-membered rings of a structure, as atoms in ring order, and whether each is a chair.
const chairs = (m: Mol) => {
  const n = near(m), single = m.atoms.map((_, k) => m.bonds.every((b) => !b.atoms.includes(k) || b.type === 1)), seen = new Set<string>(), out: boolean[] = [];
  const walk = (path: number[]) => {
    if (path.length < 6) { for (const j of n[path[path.length - 1]]) if (single[j] && !path.includes(j)) walk([...path, j]); return; }
    const key = [...path].sort((a, b) => a - b).join();
    if (!n[path[5]].includes(path[0]) || seen.has(key)) return;
    seen.add(key);
    const t = path.map((_, x) => torsionOf(m, path[x], path[(x + 1) % 6], path[(x + 2) % 6], path[(x + 3) % 6]));
    out.push(t.every((q, x) => Math.abs(Math.abs(q) - 56) < 16 && Math.sign(q) !== Math.sign(t[(x + 1) % 6])));
  };
  m.atoms.forEach((_, i) => { if (single[i]) walk([i]); });
  return out;
};
// Sparteine (wedged, with a bridged ring) and quinuclidine (three boats): no angle far from tetrahedral. Before,
// sparteine had angles of 90° and 156°, and quinuclidine 72° and 126°.
for (const [name, text, low, high] of [["sparteine", KEPT[7][1], 100, 126], ["quinuclidine", "C1CN2CCC1CC2", 104, 114]] as const) {
  const a = angles(cleaned(text));
  assert.ok(Math.min(...a) > low && Math.max(...a) < high, `${name}: angles ${Math.min(...a).toFixed(0)}° to ${Math.max(...a).toFixed(0)}°`);
}
// Chairs: sugars with amide and ester groups on them (N-acetylglucosamine, its dimer, a tetraacetate), and menthol.
for (const [name, text, count] of [["N-acetylglucosamine", "CC(=O)N[C@@H]1[C@@H](O)[C@H](O)[C@@H](CO)O[C@H]1O", 1], ["chitobiose", "CC(=O)N[C@@H]1[C@@H](O)[C@H](O[C@@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2NC(C)=O)[C@@H](CO)O[C@H]1O", 2],
  ["methyl glucoside tetraacetate", "CO[C@@H]1O[C@H](COC(C)=O)[C@@H](OC(C)=O)[C@H](OC(C)=O)[C@H]1OC(C)=O", 1], ["menthol", KEPT[0][1], 1]] as const) {
  assert.deepEqual(chairs(cleaned(text)), Array(count).fill(true), `${name}: each ring a chair`);
}
// Flat: porphine, phthalocyanine, benzoic acid, nitrobenzene and an amide come out in the page. Styrene and stilbene
// turn a little (about 20°, as ChemDraw's 3D Clean Up turns styrene), acetanilide's ring more.
for (const [name, text, most] of [["porphine", "C1=CC2=CC3=NC(=CC4=CC=C(N4)C=C5C=CC(=N5)C=C1N2)C=C3", 0], ["phthalocyanine", "c1ccc2c(c1)c1nc2nc2[nH]c(nc3nc(nc4[nH]c(n1)c1ccccc41)c1ccccc31)c1ccccc21", 0],
  ["benzoic acid", "OC(=O)c1ccccc1", 0], ["nitrobenzene", "[O-][N+](=O)c1ccccc1", 0], ["N-methylacetamide", "CC(=O)NC", 0], ["styrene", "C=Cc1ccccc1", 0.5], ["stilbene", "C(=C/c1ccccc1)\\c1ccccc1", 0.5], ["acetanilide", "CC(=O)Nc1ccccc1", 1.1]] as const) {
  const m = cleaned(text);
  assert.ok(span(m, 2) <= most * bondOf(m) + 1e-9, `${name} is ${(span(m, 2) / bondOf(m)).toFixed(2)} bonds deep`);
}
// Crowded groups turn out of the ring's plane, and no angle opens to make room in the plane: a nitro group and a
// methoxy group between two methyl groups (the C–O–C angle was 144° when the ether stayed flat), biphenyl's rings.
for (const [name, text] of [["2,6-dimethylnitrobenzene", "Cc1cccc(C)c1[N+]([O-])=O"], ["2,6-dimethylanisole", "COc1c(C)cccc1C"], ["biphenyl", "c1ccccc1-c1ccccc1"]] as const) {
  const m = cleaned(text), a = angles(m);
  assert.ok(span(m, 2) > 0.4 * bondOf(m), `${name} is ${(span(m, 2) / bondOf(m)).toFixed(2)} bonds deep`);
  assert.ok(Math.max(...a) < 128, `${name}: widest angle ${Math.max(...a).toFixed(0)}°`);
}
// A flat ring drawing turned with Structure Perspective is still cleaned up as a ring: cyclohexane becomes a chair.
{
  const flat = chem.fullMol("C1CCCCC1"), every = new Set(ids(flat)), middle = [0, 1, 2].map((e) => flat.atoms.reduce((t, a) => t + (a.location[e] ?? 0), 0) / 6) as [number, number, number];
  for (const [yaw, pitch] of [[1, 0], [30, 20]]) { const m = tiltAtoms(flat, every, middle, yaw, pitch); assert.deepEqual(chairs(clean3d(m, ids(m))), [true], `cyclohexane turned ${yaw}°, ${pitch}°`); }
}
// A second clean-up keeps the shape of a structure with no free O–H: no distance between two atoms changes by a
// twentieth of a bond (before, 0.14 of a bond in ibuprofen and 0.17 in cholesterol).
for (const [name, text] of [["ibuprofen", "CC(C)Cc1ccc(cc1)C(C)C(O)=O"], ["cholesterol", KEPT[3][1]], ["hexylbenzene", "CCCCCCc1ccccc1"]] as const) {
  const m = cleaned(text), again = clean3d(m, ids(m)), d = (r: Mol, i: number, j: number) => Math.hypot(...[0, 1, 2].map((e) => r.atoms[i].location[e] - r.atoms[j].location[e]));
  let most = 0;
  for (let i = 0; i < m.atoms.length; i++) for (let j = i + 1; j < m.atoms.length; j++) most = Math.max(most, Math.abs(d(m, i, j) - d(again, i, j)));
  assert.ok(most < 0.05 * bondOf(m), `${name} changes by ${(most / bondOf(m)).toFixed(3)} of a bond on a second clean-up`);
}
// A chain of 55 quinuclidines (496 atoms, many contacts) ends within its time: it took 3 s before the work limit.
{
  const m = chem.fullMol("C(C1CN2CCC1CC2)".repeat(55) + "C"), t = performance.now();
  clean3d(m, ids(m));
  assert.ok(performance.now() - t < 4000, `a chain of cages took ${Math.round(performance.now() - t)} ms`);
}
console.log("depth.check: sparteine, sugars, porphine, crowded groups, a turned ring, a second clean-up and a chain of cages ok");
