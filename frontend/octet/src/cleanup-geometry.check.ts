// Run: node src/cleanup-geometry.check.ts. Fails loudly if Clean Up Structure leaves a bond a little bent (Sam, 21
// October 2026: a biphenyl came out with the inter-ring bond a tiny bit off the ring axes). Each structure is drawn
// neatly (laid out, then turned 7°) and by hand (each atom moved up to 0.2 bond lengths), cleaned, and measured:
// - every bond is the document's bond length (times the structure's own scale), to 0.01%;
// - every ring is a regular polygon (120° in a six-membered ring, 108° in a five-membered one, 135° in cyclooctyne),
//   to 0.01°;
// - the bonds round an atom with only six-membered rings (or none) are 120° apart, to 0.01°;
// - an atom outside a ring between a triple and a single bond, or two double bonds, is straight, to 0.01°, and so is
//   one in an arylene-ethynylene macrocycle;
// - a bond out of a six-membered ring lies on the line from the ring's centre (a biaryl's rings and the bond between
//   them on one straight line), to 0.01°;
// - every bond of a six-membered ring or a chain lies at a multiple of 30° to the page, to 0.01°;
// - the structure stays centred where it was, and a second Clean Up moves no atom (1e-6 bond lengths).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type { Mol } from "./render.ts";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { cleanUp, parseStructure, ready } = await import("./chem.ts");
await ready;

// A macrocycle (more than 8 atoms) is checked drawn neatly only: drawn by hand, Clean Up leaves its bonds uneven.
const structures: [string, string, "neatly"?][] = [
  ["biphenyl", "c1ccc(cc1)-c1ccccc1"],
  ["4-bromobiphenyl", "Brc1ccc(cc1)-c1ccccc1"],
  ["biphenyl-4-carboxylic acid", "OC(=O)c1ccc(cc1)-c1ccccc1"],
  ["p-terphenyl", "c1ccc(cc1)-c1ccc(cc1)-c1ccccc1"],
  ["2,2'-dimethylbiphenyl", "Cc1ccccc1-c1ccccc1C"],
  ["2-phenylpyridine", "c1ccnc(c1)-c1ccccc1"],
  ["naphthalene", "c1ccc2ccccc2c1"],
  ["anthracene", "c1ccc2cc3ccccc3cc2c1"],
  ["phenanthrene", "c1ccc2c(c1)ccc1ccccc12"],
  ["octane", "CCCCCCCC"],
  ["diphenylacetylene", "c1ccccc1C#Cc1ccccc1"],
  ["methylcyclohexane", "CC1CCCCC1"],
  ["1,4-dimethylcyclohexane", "CC1CCC(C)CC1"],
  ["indane", "c1ccc2CCCc2c1"],
  ["caffeine", "Cn1cnc2c1c(=O)n(C)c(=O)n2C"],
  // Issue #11: an alkyne or allene in a ring keeps the ring regular, as in ChemDraw; outside a ring it is straight.
  ["cyclopropyne", "C1#CC1"],
  ["cyclobutyne", "C1#CCC1"],
  ["cyclopentyne", "C1#CCCC1"],
  ["cyclohexyne", "C1#CCCCC1"],
  ["cycloheptyne", "C1#CCCCCC1"],
  ["cyclooctyne", "C1#CCCCCCC1"],
  ["cyclononyne", "C1#CCCCCCCC1"],
  ["cyclodecyne", "C1#CCCCCCCCC1"],
  ["cycloocta-1,2-diene", "C1=C=CCCCCC1"],
  ["cyclohexadeca-1,8-diyne", "C1#CCCCCC#CCCCCCCCC1", "neatly"],
  ["ethynylcyclohexane", "C#CC1CCCCC1"],
  ["4-cyclohexylbuta-1,2-diene", "C=C=CCC1CCCCC1"],
  ["dibenzocyclooctyne", "C1Cc2ccccc2C#Cc2ccccc21"],
  // In a ring of more than 8 atoms with others fused to it, an alkyne stays straight.
  ["tribenzo[12]annulene", "c1ccc2c(c1)C#Cc1ccccc1C#Cc1ccccc1C#C2"],
  // A structure that is one straight chain is still straightened.
  ["2-butyne", "CC#CC"],
  ["acetonitrile", "CC#N"],
  ["hexa-2,4-diyne", "CC#CC#CC"],
];

const deg = 180 / Math.PI, BOND = 1e-4, ANGLE = 0.01, STILL = 1e-6;
let seed = 11;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) * 2 - 1;
const turned = (m: Mol, t: number): Mol => ({ ...m, atoms: m.atoms.map((a) => ({ ...a, location: [a.location[0] * Math.cos(t) - a.location[1] * Math.sin(t), a.location[0] * Math.sin(t) + a.location[1] * Math.cos(t), 0] })) });
const byHand = (m: Mol): Mol => ({ ...m, atoms: m.atoms.map((a) => ({ ...a, location: [a.location[0] + rnd() * 0.2, a.location[1] + rnd() * 0.2, 0] })) });
const scaled = (m: Mol, k: number): Mol => ({ ...m, atoms: m.atoms.map((a) => ({ ...a, scale: k, location: [a.location[0] * k, a.location[1] * k, 0] })) });
const centre = (m: Mol) => [0, 1].map((k) => m.atoms.reduce((s, a) => s + a.location[k], 0) / m.atoms.length);

// The smallest ring through each ring bond (up to 16 atoms), as atom lists.
function ringsOf(m: Mol, nei: number[][]): number[][] {
  const out = new Map<string, number[]>();
  for (const { atoms: [s, t] } of m.bonds) {
    const prev = new Map<number, number>([[s, -1]]), queue = [s];
    while (queue.length && !prev.has(t)) {
      const v = queue.shift()!;
      for (const w of nei[v]) if (!prev.has(w) && !(v === s && w === t)) { prev.set(w, v); queue.push(w); }
    }
    if (!prev.has(t)) continue;
    const path: number[] = [];
    for (let v = t; v !== -1; v = prev.get(v)!) path.push(v);
    if (path.length <= 16) out.set([...path].sort((a, b) => a - b).join(), path);
  }
  return [...out.values()];
}

// The geometry's faults, each the worst found: bond length (fraction), ring angle, angle round an atom, axis and grid
// (degrees).
function faults(m: Mol, length: number) {
  const p = (i: number) => m.atoms[i].location, nei: number[][] = m.atoms.map(() => []);
  m.bonds.forEach((b) => { nei[b.atoms[0]].push(b.atoms[1]); nei[b.atoms[1]].push(b.atoms[0]); });
  const turn = (u: number[], v: number[]) => Math.abs(Math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])) * deg;
  const vec = (a: number, b: number) => [p(b)[0] - p(a)[0], p(b)[1] - p(a)[1]];
  const out = { bond: 0, ring: 0, around: 0, axis: 0, grid: 0 };
  for (const b of m.bonds) out.bond = Math.max(out.bond, Math.abs(Math.hypot(...vec(b.atoms[0], b.atoms[1])) / length - 1));
  const rings = ringsOf(m, nei), sizes = m.atoms.map(() => new Set<number>());
  // An alkyne or allene atom is straight outside a ring, and in a ring of more than 8 atoms fused to others (an
  // arylene-ethynylene macrocycle), which is then not regular.
  const lone = (r: number[]) => r.every((i) => rings.filter((q) => q.includes(i)).length === 1);
  const straight = (i: number) => nei[i].length === 2 && m.bonds.reduce((s, b) => s + (b.atoms.includes(i) ? b.type : 0), 0) === 4 && rings.every((r) => !r.includes(i) || (r.length > 8 && !lone(r)));
  for (const r of rings) r.forEach((i, k) => {
    sizes[i].add(r.length);
    if (!r.some(straight)) out.ring = Math.max(out.ring, Math.abs(turn(vec(i, r[(k + r.length - 1) % r.length]), vec(i, r[(k + 1) % r.length])) - (180 - 360 / r.length)));
  });
  const hexagonal = (i: number) => [...sizes[i]].every((n) => n === 6);
  m.atoms.forEach((_, i) => {
    const linear = straight(i);
    if (!linear && (!hexagonal(i) || nei[i].length < 2 || nei[i].length > 3)) return;
    const dirs = nei[i].map((j) => Math.atan2(p(j)[1] - p(i)[1], p(j)[0] - p(i)[0]) * deg).sort((a, b) => a - b);
    dirs.forEach((d, k) => {
      const gap = ((dirs[(k + 1) % dirs.length] - d + 360) % 360) || 360;
      if (dirs.length === 2) out.around = Math.max(out.around, Math.abs(Math.min(gap, 360 - gap) - (linear ? 180 : 120)));
      else out.around = Math.max(out.around, Math.abs(gap - 120));
    });
  });
  for (const r of rings) {
    if (r.length !== 6) continue;
    const c = [0, 1].map((k) => r.reduce((s, i) => s + p(i)[k], 0) / 6);
    for (const i of r) for (const j of nei[i]) if (!rings.some((q) => q.includes(i) && q.includes(j))) out.axis = Math.max(out.axis, turn([p(i)[0] - c[0], p(i)[1] - c[1]], vec(i, j)));
  }
  for (const b of m.bonds) {
    if (!hexagonal(b.atoms[0]) || !hexagonal(b.atoms[1])) continue;
    const a = ((Math.atan2(...(vec(b.atoms[0], b.atoms[1]).reverse() as [number, number])) * deg % 30) + 30) % 30;
    out.grid = Math.max(out.grid, Math.min(a, 30 - a));
  }
  return out;
}

let worst = { bond: 0, ring: 0, around: 0, axis: 0, grid: 0 };
for (const [name, smiles, only] of structures) {
  const laid = parseStructure(smiles) as Mol;
  for (const [how, drawn, length] of [["neatly", turned(laid, 0.122), 1], ["by hand", byHand(laid), 1], ["by hand at 200%", scaled(byHand(laid), 2), 2]] as [string, Mol, number][]) {
    if (only && how !== only) continue;
    const once = cleanUp(drawn), twice = cleanUp(once), f = faults(once, length), what = `${name}, drawn ${how}`;
    assert.ok(f.bond < BOND, `${what}: every bond is the bond length (${(f.bond * 100).toFixed(4)}% out)`);
    assert.ok(f.ring < ANGLE, `${what}: every ring is regular (${f.ring.toFixed(4)}° out)`);
    assert.ok(f.around < ANGLE, `${what}: bonds 120° apart (${f.around.toFixed(4)}° out)`);
    assert.ok(f.axis < ANGLE, `${what}: bonds out of a ring on its axis (${f.axis.toFixed(4)}° out)`);
    assert.ok(f.grid < ANGLE, `${what}: bonds at a multiple of 30° (${f.grid.toFixed(4)}° out)`);
    const [c0, c1] = [centre(drawn), centre(once)];
    assert.ok(Math.hypot(c0[0] - c1[0], c0[1] - c1[1]) < 1e-9, `${what}: stays centred where it was`);
    const moved = Math.max(...once.atoms.map((a, i) => Math.hypot(a.location[0] - twice.atoms[i].location[0], a.location[1] - twice.atoms[i].location[1])));
    assert.ok(moved < STILL * length, `${what}: a second Clean Up moves nothing (${moved.toExponential(1)} bond lengths)`);
    worst = Object.fromEntries(Object.entries(worst).map(([k, v]) => [k, Math.max(v, f[k as keyof typeof f])])) as typeof worst;
  }
}
// A straight chain drawn with its ends on one point is left as drawn, not dropped onto that point.
{
  const m = parseStructure("CC#CC") as Mol, drawn = [[0, 0], [0, 1], [1, 1], [0, 0]];
  const out = cleanUp({ ...m, atoms: m.atoms.map((a, i) => ({ ...a, location: [drawn[i][0], drawn[i][1], 0] })) });
  assert.ok(out.atoms.every((a, i) => Math.hypot(a.location[0] - drawn[i][0], a.location[1] - drawn[i][1]) < 1e-9), "2-butyne with its ends on one point: left as drawn");
}
console.log(`cleanup-geometry.check: ${structures.length} structures, each drawn up to 3 ways, cleaned exactly: bonds within ${(worst.bond * 100).toExponential(1)}%, ` +
  `rings ${worst.ring.toExponential(1)}°, angles ${worst.around.toExponential(1)}°, axes ${worst.axis.toExponential(1)}°, 30° grid ${worst.grid.toExponential(1)}°`);
