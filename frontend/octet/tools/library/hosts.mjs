// Macrocyclic hosts Indigo's flat layout draws badly (rings over their own OH groups): calixarenes and pillar[5]arene
// drawn flat as papers draw them (each ring pointing out round a square or a pentagon), and [2.2]paracyclophane in
// perspective (each atom at its place in 3D, kept as depth, decision 0012), its two rings face to face. The 3D one is
// built from rings placed by simple geometry, then relaxed so every bond is one bond length and every angle near its
// ideal (120° at an aromatic atom, 109.5° otherwise), with atoms that are not bonded kept apart, and seen from the
// clearest side. Nothing comes from another program's files.
import { Drawing } from "./perspective.mjs";

const deg = Math.PI / 180;
const add = (a, b) => a.map((v, k) => v + b[k]), sub = (a, b) => a.map((v, k) => v - b[k]), mul = (a, s) => a.map((v) => v * s);
const len = (a) => Math.hypot(...a);
const rotX = ([x, y, z], t) => [x, y * Math.cos(t) - z * Math.sin(t), y * Math.sin(t) + z * Math.cos(t)];
const rotY = ([x, y, z], t) => [x * Math.cos(t) + z * Math.sin(t), y, -x * Math.sin(t) + z * Math.cos(t)];

// A molecule being built: atoms ([label, place]) and bonds ([a, b, order]).
export class Build {
  constructor() { this.atoms = []; this.bonds = []; }
  atom(label, at) { this.atoms.push({ label, at }); return this.atoms.length - 1; }
  bond(a, b, order = 1) { this.bonds.push([a, b, order]); return this; }
  // A benzene ring about centre c in the plane of the unit vectors u and t (its first atom at c - u, the ring going
  // round towards t), Kekulé double bonds from its first atom. Returns its six atoms.
  ring(c, u, t) {
    const at = Array.from({ length: 6 }, (_, k) => { const a = (k * 60) * deg; return this.atom("C", add(c, add(mul(u, -Math.cos(a)), mul(t, Math.sin(a))))); });
    for (let k = 0; k < 6; k++) this.bond(at[k], at[(k + 1) % 6], k % 2 ? 1 : 2);
    return at;
  }
  // Relaxed: bonds to one bond length, angles to their ideal (as the distance across them), non-bonded atoms at least
  // 1.6 bond lengths apart, by small steps. more: [a, b, distance] for pairs with a distance of their own.
  relax(steps = 4000, more = []) {
    const n = this.atoms.length, nb = Array.from({ length: n }, () => []);
    for (const [a, b, o] of this.bonds) { nb[a].push([b, o]); nb[b].push([a, o]); }
    const flat = (i) => nb[i].some(([, o]) => o === 2); // an aromatic (Kekulé) or double-bonded atom
    const pairs = new Map(), key = (a, b) => (a < b ? `${a},${b}` : `${b},${a}`);
    for (const [a, b] of this.bonds) pairs.set(key(a, b), 1);
    for (let i = 0; i < n; i++) for (const [a] of nb[i]) for (const [b] of nb[i]) if (a < b && !pairs.has(key(a, b))) pairs.set(key(a, b), flat(i) ? Math.sqrt(3) : 1.633);
    for (const [a, b, d] of more) pairs.set(key(a, b), d);
    const list = [...pairs].map(([k, d]) => [...k.split(",").map(Number), d]);
    const p = this.atoms.map((a) => [...a.at]);
    for (let s = 0; s < steps; s++) {
      const f = p.map(() => [0, 0, 0]);
      for (const [a, b, d] of list) { const v = sub(p[b], p[a]), l = len(v) || 1e-6, k = (l - d) / l * 0.5; f[a] = add(f[a], mul(v, k)); f[b] = add(f[b], mul(v, -k)); }
      if (s % 10 === 0) for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) {
        if (pairs.has(key(a, b))) continue;
        const v = sub(p[b], p[a]), l = len(v);
        if (l < 1.6) { const k = ((l - 1.6) / (l || 1e-6)) * 0.5; f[a] = add(f[a], mul(v, k)); f[b] = add(f[b], mul(v, -k)); }
      }
      for (let a = 0; a < n; a++) p[a] = add(p[a], mul(f[a], 0.25));
    }
    this.atoms.forEach((a, i) => { a.at = p[i]; });
    return this;
  }
  // The clearest view seen from above (tilted 10° to 60°, turned to any side): no bond seen nearly end on (Octet
  // would draw its back atom as a Newman circle), and the atoms that are not bonded as far apart on the page as they go.
  view() {
    const n = this.atoms.length, bonded = new Set(this.bonds.map(([a, b]) => `${Math.min(a, b)},${Math.max(a, b)}`));
    let best = [0, 30], most = -Infinity;
    for (let turn = 0; turn < 360; turn += 4) for (let tilt = 10; tilt <= 60; tilt += 4) {
      const q = this.atoms.map((a) => rotX(rotY(a.at, turn * deg), tilt * deg));
      const shortest = Math.min(...this.bonds.map(([a, b]) => Math.hypot(q[a][0] - q[b][0], q[a][1] - q[b][1])));
      if (shortest < 0.45) continue;
      let near = Infinity;
      for (let a = 0; a < n; a++) for (let b = a + 1; b < n; b++) if (!bonded.has(`${a},${b}`)) near = Math.min(near, Math.hypot(q[a][0] - q[b][0], q[a][1] - q[b][1]));
      if (near > most) { most = near; best = [turn, tilt]; }
    }
    return best;
  }
  // As a library drawing, seen turned about the page's y axis then tilted about its x axis (degrees); the clearest
  // view when none is given.
  drawing(turn, tilt) {
    if (turn === undefined) [turn, tilt] = this.view();
    const d = new Drawing(), at = this.atoms.map((a) => d.atom(a.label, rotX(rotY(a.at, turn * deg), tilt * deg)));
    for (const [a, b, o] of this.bonds) d.bond(at[a], at[b], o);
    return d.done();
  }
  // The longest bond's and the shortest bond's lengths, to check the relaxing.
  lengths() { const ls = this.bonds.map(([a, b]) => len(sub(this.atoms[a].at, this.atoms[b].at))); return [Math.min(...ls), Math.max(...ls)]; }
}

// [2.2]Paracyclophane: two benzene rings face to face, each para pair joined by CH2CH2.
function paracyclophane() {
  const m = new Build(), rings = [-1.3, 1.3].map((y) => m.ring([0, y, 0], [1, 0, 0], [0, 0, 1]));
  for (const k of [0, 3]) {
    const s = k ? -1 : 1, a = m.atom("C", [-s * 1.45, -0.55, 0]), b = m.atom("C", [-s * 1.45, 0.55, 0]);
    m.bond(rings[0][k], a).bond(a, b).bond(b, rings[1][k]);
  }
  return m.relax();
}

// Calix[4]arene flat, as it is drawn in papers: the four phenols round a square, each ring pointing out, its OH in to
// the middle, the CH2 bridges at the corners (their bonds 1.3 bond lengths, so the four OH clear each other).
function flatCalixarene(tBu) {
  const d = new Drawing(), D = 3, rings = [];
  for (let i = 0; i < 4; i++) {
    const a = i * 90 * deg, out = [Math.cos(a), Math.sin(a)], t = [-Math.sin(a), Math.cos(a)];
    // Ring atoms from C1 (inner, with the OH) round: C1 at D - 1, C4 at D + 1 along out.
    const at = Array.from({ length: 6 }, (_, k) => { const w = (k * 60) * deg, r = -Math.cos(w), s = Math.sin(w); return d.atom("C", [out[0] * (D + r) + t[0] * s, out[1] * (D + r) + t[1] * s, 0]); });
    for (let k = 0; k < 6; k++) d.bond(at[k], at[(k + 1) % 6], k % 2 ? 1 : 2);
    d.bond(at[0], d.atom("O", [out[0] * (D - 2), out[1] * (D - 2), 0]));
    if (tBu) {
      const q = d.atom("C", [out[0] * (D + 2), out[1] * (D + 2), 0]);
      d.bond(at[3], q);
      for (const w of [-60, 0, 60]) { const c = Math.cos(w * deg), sn = Math.sin(w * deg); d.bond(q, d.atom("C", [out[0] * (D + 2) + (out[0] * c - out[1] * sn), out[1] * (D + 2) + (out[0] * sn + out[1] * c), 0])); }
    }
    rings.push(at);
  }
  for (let i = 0; i < 4; i++) {
    const a = (i * 90 + 45) * deg, c = d.atom("C", [2.1 * Math.SQRT2 * Math.cos(a), 2.1 * Math.SQRT2 * Math.sin(a), 0]);
    d.bond(rings[i][1], c).bond(c, rings[(i + 1) % 4][5]);
  }
  return d.done();
}

// Pillar[5]arene flat: five dimethoxybenzenes round a pentagon, each ring's 2 and 5 positions on the pentagon's side
// (joined by the CH2 bridges at its corners), one OMe out and one in.
function flatPillararene() {
  const d = new Drawing(), n = 5, D = 3.6, rings = [];
  for (let i = 0; i < n; i++) {
    const a = (90 + (360 / n) * i) * deg, out = [Math.cos(a), Math.sin(a)], t = [-Math.sin(a), Math.cos(a)];
    // C1 to C6 at 120°, 180°, 240°, 300°, 0° and 60° about the ring's middle, measured from t towards out.
    const at = [120, 180, 240, 300, 0, 60].map((w) => d.atom("C", [out[0] * D + t[0] * Math.cos(w * deg) + out[0] * Math.sin(w * deg), out[1] * D + t[1] * Math.cos(w * deg) + out[1] * Math.sin(w * deg), 0]));
    for (let k = 0; k < 6; k++) d.bond(at[k], at[(k + 1) % 6], k % 2 ? 1 : 2);
    for (const [k, w] of [[0, 120], [3, 300]]) {
      const dir = [t[0] * Math.cos(w * deg) + out[0] * Math.sin(w * deg), t[1] * Math.cos(w * deg) + out[1] * Math.sin(w * deg)], [x, y] = d.atoms[at[k]].location;
      const o = d.atom("O", [x + dir[0], y + dir[1], 0]), turn = (k ? -60 : 60) * deg;
      d.bond(at[k], o).bond(o, d.atom("C", [x + dir[0] + dir[0] * Math.cos(turn) - dir[1] * Math.sin(turn), y + dir[1] + dir[0] * Math.sin(turn) + dir[1] * Math.cos(turn), 0]));
    }
    rings.push(at);
  }
  for (let i = 0; i < n; i++) {
    const [p, q] = [d.atoms[rings[i][4]].location, d.atoms[rings[(i + 1) % n][1]].location], m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2], l = Math.hypot(...m);
    const c = d.atom("C", [m[0] * (l + 0.45) / l, m[1] * (l + 0.45) / l, 0]);
    d.bond(rings[i][4], c).bond(c, rings[(i + 1) % n][1]);
  }
  return d.done();
}

const entry = (name, also, mol) => ({ name, ...(also ? { also } : {}), mol });
export const HOSTS = [
  entry("Calix[4]arene", "calixarene", flatCalixarene(false)),
  entry("p-tert-Butylcalix[4]arene", "calixarene", flatCalixarene(true)),
  entry("Pillar[5]arene", "pillararene, dimethoxypillar[5]arene", flatPillararene()),
  entry("[2.2]Paracyclophane", "cyclophane", paracyclophane().drawing()),
];
// The relaxed paracyclophane's shortest and longest bonds, for the build's check.
export const hostLengths = () => paracyclophane().lengths();
