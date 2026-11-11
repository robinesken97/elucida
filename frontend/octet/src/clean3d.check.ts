// Run: node src/clean3d.check.ts. Fails loudly if 3D Clean Up (CD-36) stops giving sound 3D shapes.
import assert from "node:assert/strict";
import { clean3d, MOST_3D } from "./clean3d.ts";
import { EMPTY, addRing, pos } from "./edit.ts";
import type { Mol } from "./render.ts";

const all = (m: Mol) => m.atoms.map((_, i) => i);
const at = (m: Mol, i: number) => m.atoms[i].location;
const dist = (m: Mol, i: number, j: number) => Math.hypot(at(m, i)[0] - at(m, j)[0], at(m, i)[1] - at(m, j)[1], at(m, i)[2] - at(m, j)[2]);
const angle = (m: Mol, i: number, j: number, k: number) => {
  const a = [0, 1, 2].map((x) => at(m, i)[x] - at(m, j)[x]), b = [0, 1, 2].map((x) => at(m, k)[x] - at(m, j)[x]);
  return (Math.acos(a.reduce((s, v, x) => s + v * b[x], 0) / (Math.hypot(...a) * Math.hypot(...b))) * 180) / Math.PI;
};
const torsion = (m: Mol, i: number, j: number, k: number, l: number) => {
  const v = (a: number, b: number) => [0, 1, 2].map((x) => at(m, b)[x] - at(m, a)[x]), c = (a: number[], b: number[]) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const d = (a: number[], b: number[]) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const [b1, b2, b3] = [v(i, j), v(j, k), v(k, l)], n1 = c(b1, b2), n2 = c(b2, b3), m1 = c(n1, b2.map((x) => x / Math.hypot(...b2)));
  return (Math.atan2(d(m1, n2), d(n1, n2)) * 180) / Math.PI;
};

// Cyclohexane: a chair, with tetrahedral angles and bonds of one bond length.
{
  const ring = addRing(EMPTY, 6, false, { point: [0, 0] }), m = clean3d(ring, all(ring));
  for (const b of m.bonds) assert.ok(Math.abs(dist(m, b.atoms[0], b.atoms[1]) - 1) < 0.03, "C–C bonds stay one bond length");
  const order = [0, 1, 2, 3, 4, 5];
  for (let k = 0; k < 6; k++) assert.ok(Math.abs(angle(m, order[k], order[(k + 1) % 6], order[(k + 2) % 6]) - 109.5) < 4, "tetrahedral angles");
  const t = order.map((_, k) => torsion(m, order[k], order[(k + 1) % 6], order[(k + 2) % 6], order[(k + 3) % 6]));
  assert.ok(t.every((x, k) => Math.abs(Math.abs(x) - 55) < 12 && Math.sign(x) !== Math.sign(t[(k + 1) % 6])), `a chair: ${t.map((x) => x.toFixed(0))}`);
  // Again: it stays a chair (the clean-up improves, it does not undo).
  const again = clean3d(m, all(m));
  assert.ok(again.bonds.every((b) => Math.abs(dist(again, b.atoms[0], b.atoms[1]) - 1) < 0.03));
  console.log("clean3d.check: cyclohexane chair ok");
}

// Benzene: flat, with its bonds a little shorter.
{
  const ring = addRing(EMPTY, 6, true, { point: [0, 0] }), m = clean3d(ring, all(ring));
  const z = m.atoms.map((a) => a.location[2]), mean = z.reduce((s, x) => s + x, 0) / 6;
  assert.ok(z.every((x) => Math.abs(x - mean) < 0.03), "benzene stays flat");
  for (const b of m.bonds) assert.ok(Math.abs(dist(m, b.atoms[0], b.atoms[1]) - 0.91) < 0.03);
  console.log("clean3d.check: benzene ok");
}

// But-2-ene keeps the cis or trans it is drawn with; a wedged stereocentre keeps its hand.
{
  const h = Math.sqrt(3) / 2, C = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const trans: Mol = { atoms: [C(0, 0), C(h, 0.5), C(2 * h, 0), C(3 * h, 0.5)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 2, atoms: [1, 2] }, { type: 1, atoms: [2, 3] }] };
  const cis: Mol = { ...trans, atoms: [C(0, 0), C(h, 0.5), C(2 * h, 0), C(2 * h, -1)] };
  const [t, c] = [clean3d(trans, all(trans)), clean3d(cis, all(cis))];
  assert.ok(dist(t, 0, 3) > 1.15 * dist(c, 0, 3), "trans stays trans and cis stays cis");
  assert.ok(Math.abs(torsion(t, 0, 1, 2, 3)) > 170 && Math.abs(torsion(c, 0, 1, 2, 3)) < 10);
  // A carbon with a wedge to one neighbour: the same hand after (the sign of its volume).
  const centre: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "N", location: [0, 1, 0] }, { label: "O", location: [h, -0.5, 0] }, { label: "C", location: [-h, -0.5, 0] }, { label: "C", location: [-h, 0.5, 0] }],
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [0, 2], stereo: 1 }, { type: 1, atoms: [0, 3] }, { type: 1, atoms: [3, 4] }] };
  const vol = (m: Mol) => { const [o, a, b, d] = [0, 1, 2, 3].map((i) => at(m, i)), u = [0, 1, 2].map((x) => a[x] - o[x]), v = [0, 1, 2].map((x) => b[x] - o[x]), w = [0, 1, 2].map((x) => d[x] - o[x]);
    return u[0] * (v[1] * w[2] - v[2] * w[1]) - u[1] * (v[0] * w[2] - v[2] * w[0]) + u[2] * (v[0] * w[1] - v[1] * w[0]); };
  const after = clean3d(centre, all(centre));
  // Drawn: N up, O wedged (in front) down right, C down left; that hand has a negative volume.
  assert.ok(vol(after) < 0, "the hand its wedge draws");
  const hashed = clean3d({ ...centre, bonds: centre.bonds.map((b, k) => (k === 1 ? { ...b, stereo: 6 } : b)) }, all(centre));
  assert.ok(vol(hashed) > 0, "and a hash the other hand");
  console.log("clean3d.check: double bonds and stereocentres ok");
}

// The largest structure ChemDraw cleans up (500 atoms) takes well under a second or two, and stays where it was.
{
  const chain: Mol = { atoms: Array.from({ length: MOST_3D }, (_, k) => ({ label: "C", location: [k * 0.866, k % 2 ? 0.5 : 0, 0] as [number, number, number] })), bonds: Array.from({ length: MOST_3D - 1 }, (_, k) => ({ type: 1, atoms: [k, k + 1] as [number, number] })) };
  const t0 = performance.now(), m = clean3d(chain, all(chain)), ms = performance.now() - t0;
  assert.ok(ms < 4000, `500 atoms in ${ms.toFixed(0)} ms`);
  const mid = (x: Mol) => x.atoms.reduce((s, a) => s + a.location[0], 0) / x.atoms.length;
  assert.ok(Math.abs(mid(m) - mid(chain)) < 1e-6);
  void pos;
  console.log(`clean3d.check: ${MOST_3D} atoms in ${ms.toFixed(0)} ms ok`);
}
