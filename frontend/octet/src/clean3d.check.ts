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

// Benzene: flat, and the size it was drawn (its bonds are all of one kind, so they keep their length), however many
// times it is cleaned up.
{
  const ring = addRing(EMPTY, 6, true, { point: [0, 0] }), m = clean3d(ring, all(ring));
  const z = m.atoms.map((a) => a.location[2]), mean = z.reduce((s, x) => s + x, 0) / 6;
  assert.ok(z.every((x) => Math.abs(x - mean) < 0.03), "benzene stays flat");
  const twice = clean3d(clean3d(m, all(m)), all(m));
  for (const b of m.bonds) assert.ok(Math.abs(dist(m, b.atoms[0], b.atoms[1]) - 1) < 0.01 && Math.abs(dist(twice, b.atoms[0], b.atoms[1]) - 1) < 0.01, "benzene keeps its size");
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

// Biphenyl drawn flat: its rings twist (the hydrogens the drawing leaves out are in the way), 44° as a gas. Naphthalene
// drawn flat stays in the page exactly.
{
  const hex = (cx: number, turn = 0) => [0, 1, 2, 3, 4, 5].map((k) => ({ label: "C", location: [cx + Math.cos(turn + (k * Math.PI) / 3), Math.sin(turn + (k * Math.PI) / 3), 0] as [number, number, number] }));
  const ringBonds = (o: number) => [0, 1, 2, 3, 4, 5].map((k) => ({ type: k % 2 ? 1 : 2, atoms: [o + k, o + ((k + 1) % 6)] as [number, number] }));
  const biphenyl: Mol = { atoms: [...hex(0), ...hex(3)], bonds: [...ringBonds(0), ...ringBonds(6), { type: 1, atoms: [0, 9] }] };
  const twist = Math.abs(torsion(clean3d(biphenyl, all(biphenyl)), 1, 0, 9, 8));
  assert.ok(twist > 25 && twist < 50, `biphenyl twists: ${twist.toFixed(0)}°`);
  const h = Math.sqrt(3) / 2, second = [0, 1, 2, 3].map((k) => ({ label: "C", location: [2 * h + Math.cos(-Math.PI / 2 + (k * Math.PI) / 3), Math.sin(-Math.PI / 2 + (k * Math.PI) / 3), 0] as [number, number, number] }));
  const naphthalene: Mol = { atoms: [...hex(0, Math.PI / 6), ...second], bonds: [[0, 1, 2], [1, 2, 1], [2, 3, 2], [3, 4, 1], [4, 5, 2], [5, 0, 1], [5, 6, 1], [6, 7, 2], [7, 8, 1], [8, 9, 2], [9, 0, 1]].map(([a, b, type]) => ({ type, atoms: [a, b] as [number, number] })) };
  assert.ok(clean3d(naphthalene, all(naphthalene)).atoms.every((a) => a.location[2] === 0), "naphthalene stays in the page");
  console.log("clean3d.check: biphenyl and naphthalene ok");
}

// A wedged group on a cyclohexane ring keeps the hand its wedge draws, whichever chair the ring takes: both isomers of
// 1,4-dimethylcyclohexane, each centre with the sign its page gives (the wedge end near, the rest in the page). The
// cis isomer has one methyl axial; the trans isomer, drawn with a wedge and a hash, has none.
{
  const ring = addRing(EMPTY, 6, false, { point: [0, 0] });
  const out = (k: number): [number, number, number] => [at(ring, k)[0] * 2, at(ring, k)[1] * 2, 0];
  const volume = (m: Mol, o: number, a: number, b: number, c: number, depth?: number) => {
    const p = [o, a, b, c].map((i) => [...at(m, i)]);
    if (depth !== undefined) p[3][2] = depth;
    const [u, v, w] = [1, 2, 3].map((i) => [0, 1, 2].map((e) => p[i][e] - p[0][e]));
    return u[0] * (v[1] * w[2] - v[2] * w[1]) - u[1] * (v[0] * w[2] - v[2] * w[0]) + u[2] * (v[0] * w[1] - v[1] * w[0]);
  };
  for (const second of [1, 6]) {
    const m: Mol = { atoms: [...ring.atoms, { label: "C", location: out(0) }, { label: "C", location: out(3) }], bonds: [...ring.bonds, { type: 1, atoms: [0, 6], stereo: 1 }, { type: 1, atoms: [3, 7], stereo: second }] };
    const done = clean3d(m, all(m));
    for (const [k, methyl, stereo] of [[0, 6, 1], [3, 7, second]]) {
      const [a, b] = [(k + 5) % 6, (k + 1) % 6];
      assert.equal(Math.sign(volume(done, k, a, b, methyl)), Math.sign(volume(m, k, a, b, methyl, stereo === 1 ? 0.8 : -0.8)), `the methyl on atom ${k} keeps its side (${second === 1 ? "cis" : "trans"})`);
    }
    // Axial: the bond to the methyl is near the ring's axis (the normal of the plane of atoms 1, 3 and 5).
    const axis = [1, 2].map((i) => [0, 1, 2].map((e) => at(done, 1 + 2 * i)[e] - at(done, 1)[e])), n = [axis[0][1] * axis[1][2] - axis[0][2] * axis[1][1], axis[0][2] * axis[1][0] - axis[0][0] * axis[1][2], axis[0][0] * axis[1][1] - axis[0][1] * axis[1][0]];
    const axial = [[0, 6], [3, 7]].filter(([k, c]) => { const v = [0, 1, 2].map((e) => at(done, c)[e] - at(done, k)[e]); return Math.abs(v[0] * n[0] + v[1] * n[1] + v[2] * n[2]) / (Math.hypot(...v) * Math.hypot(...n)) > 0.8; }).length;
    assert.equal(axial, second === 1 ? 1 : 0, `${second === 1 ? "cis: one methyl axial" : "trans: both equatorial"}`);
  }
  console.log("clean3d.check: wedged groups on a chair ok");
}

// An allene and a ketene drawn bent come out straight at the middle atom. Propane drawn with its hydrogens keeps a
// tetrahedral angle (a drawn hydrogen is a hydrogen, not a heavy atom).
{
  const h = Math.sqrt(3) / 2, A = (label: string, x: number, y: number) => ({ label, location: [x, y, 0] as [number, number, number] });
  for (const end of ["C", "O"]) {
    const m: Mol = { atoms: [A("C", 0, 0), A("C", h, 0.5), A("C", 2 * h, 0), A(end, 3 * h, 0.5)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 2, atoms: [1, 2] }, { type: 2, atoms: [2, 3] }] };
    const bend = angle(clean3d(m, all(m)), 1, 2, 3);
    assert.ok(bend > 175, `C=C=${end} is straight: ${bend.toFixed(0)}°`);
  }
  const propane: Mol = { atoms: [A("C", 0, 0), A("C", h, 0.5), A("C", 2 * h, 0), A("H", h, 1.5), A("H", h + 0.6, 1.1)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }, { type: 1, atoms: [1, 3] }, { type: 1, atoms: [1, 4] }] };
  const ccc = angle(clean3d(propane, all(propane)), 0, 1, 2);
  assert.ok(Math.abs(ccc - 111) < 4, `propane with drawn hydrogens: ${ccc.toFixed(0)}°`);
  console.log("clean3d.check: cumulenes and drawn hydrogens ok");
}

// A ring of benzene rings ([n]cycloparaphenylene) drawn flat: a hoop, as in its crystal structure. Each benzene ring
// stands along the hoop's axis, tilted to one side and the next to the other; the hoop is as wide as the measured one
// (11.0 Å for 8 rings, 16.5 Å for 12); a second clean-up changes nothing. The same from a drawing with the rings
// squashed to show them edge-on, as the hoop comes from a SMILES.
{
  type P = number[];
  const minus = (a: P, b: P) => a.map((v, k) => v - b[k]), cross = (a: P, b: P) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const dot = (a: P, b: P) => a.reduce((t, v, k) => t + v * b[k], 0), one = (a: P) => a.map((v) => v / Math.hypot(...a));
  const hoop = (n: number, squash: number): Mol => {
    const atoms: Mol["atoms"] = [], bonds: Mol["bonds"] = [], R = 3 / (2 * Math.sin(Math.PI / n));
    for (let r = 0; r < n; r++) {
      const th = (2 * Math.PI * r) / n, mid = R * Math.cos(Math.PI / n), along = [-Math.sin(th), Math.cos(th)], out = [Math.cos(th), Math.sin(th)];
      for (const [a, b] of [[-1, 0], [-0.5, 0.866], [0.5, 0.866], [1, 0], [0.5, -0.866], [-0.5, -0.866]]) atoms.push({ label: "C", location: [mid * out[0] + a * along[0] + b * squash * out[0], mid * out[1] + a * along[1] + b * squash * out[1], 0] });
      for (let k = 0; k < 6; k++) bonds.push({ type: k % 2 ? 1 : 2, atoms: [r * 6 + k, r * 6 + ((k + 1) % 6)] });
      bonds.push({ type: 1, atoms: [r * 6 + 3, ((r + 1) % n) * 6] });
    }
    return { atoms, bonds };
  };
  for (const [n, wide, squash] of [[8, 11.0, 1], [12, 16.5, 1], [8, 11.0, 0.3]]) {
    const m = clean3d(hoop(n, squash), all(hoop(n, squash))), p = m.atoms.map((a) => [...a.location]);
    const middles = Array.from({ length: n }, (_, r) => [0, 1, 2].map((e) => p.slice(r * 6, r * 6 + 6).reduce((t, q) => t + q[e], 0) / 6)), centre = [0, 1, 2].map((e) => middles.reduce((t, q) => t + q[e], 0) / n);
    const axis = one(middles.reduce((t, q, r) => t.map((v, e) => v + cross(minus(q, centre), minus(middles[(r + 1) % n], centre))[e]), [0, 0, 0]));
    // Each ring's lean: the angle from the hoop's axis to the ring's plane, signed by the side it leans to.
    const lean = middles.map((q, r) => { const normal = one(cross(minus(p[r * 6 + 2], p[r * 6]), minus(p[r * 6 + 4], p[r * 6]))), side = Math.sign(dot(normal, minus(q, centre))); return (Math.asin(dot(normal, axis)) * side * 180) / Math.PI; });
    assert.ok(lean.every((t, r) => Math.abs(t) > 8 && Math.abs(t) < 30 && Math.sign(t) !== Math.sign(lean[(r + 1) % n])), `${n} rings stand, leaning in turn: ${lean.map((t) => t.toFixed(0))}`);
    for (let r = 0; r < n; r++) { const normal = one(cross(minus(p[r * 6 + 2], p[r * 6]), minus(p[r * 6 + 4], p[r * 6]))); assert.ok(p.slice(r * 6, r * 6 + 6).every((q) => Math.abs(dot(minus(q, middles[r]), normal)) < 0.25), "each benzene ring stays near flat"); }
    const single = dist(m, 3, 6), across = (2 * middles.reduce((t, q) => t + Math.hypot(...minus(q, centre)), 0)) / n / single * 1.52;
    assert.ok(Math.abs(across - wide) < 0.05 * wide, `the hoop of ${n} is ${across.toFixed(1)} Å wide (measured ${wide})`);
    const again = clean3d(m, all(m));
    assert.ok(again.atoms.every((a, k) => Math.hypot(...minus(a.location, m.atoms[k].location)) < 0.05), "a second clean-up changes nothing");
  }
  console.log("clean3d.check: rings of benzene rings ok");
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
