// 3D Clean Up (Structure menu, ⇧⌘D), as ChemDraw's: a quick 3D geometry for structures drawn in 2D, or a better one
// for structures in 3D already (run it again to improve it). Octet's own method, no force field library: an energy
// that is lowest at a sound shape, taken downhill from the drawing until it settles. Its terms: each bond and each
// angle at an atom (from its hybridisation) as a target distance between two atoms; each double bond's cis or trans, as
// drawn; flat double bonds, aromatic rings and sp2 atoms; a pull to flat across a single bond between two sp2 atoms
// (conjugation: firm in an amide, weak between two aromatic rings or to an O or N); and a least distance between atoms three or more
// bonds apart. The hydrogens the drawing leaves out take part (they are what twists biphenyl), and are not added to
// the drawing. A stereocentre keeps the hand its wedges and hashes draw, and a saturated six-membered ring starts as a
// chair (a strained result is tried again from the other chairs). Lengths are in bond lengths: a bond is its real
// length over a C–C single bond, times the structure's median bond.
import { AROMATIC, HBOND, hydrogens, type Mol } from "./render.ts";
import { aromaticAtoms, rings } from "./rings.ts";

export const MOST_3D = 500; // ChemDraw's limit: atoms in one structure

type V = [number, number, number];
const sub = (a: V, b: V): V => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const crossV = (a: V, b: V): V => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const dotV = (a: V, b: V) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const lenV = (a: V) => Math.hypot(a[0], a[1], a[2]);
const unitV = (a: V): V => { const l = lenV(a); return l ? [a[0] / l, a[1] / l, a[2] / l] : [0, 0, 0]; };

// Covalent radii (Å), for a bond's real length (and a ball's size in a 3MF model); a C–C single bond is 1.52 Å.
export const RADIUS: Record<string, number> = { H: 0.31, B: 0.84, C: 0.76, N: 0.71, O: 0.66, F: 0.57, Si: 1.11, P: 1.07, S: 1.05, Cl: 1.02, Br: 1.2, I: 1.39 };
const CC = 1.52;

// How stiff each term is, against a bond's 1, in about a force field's proportions (DREIDING's: Mayo, Olafson and
// Goddard, J. Phys. Chem. 94, 8897). The proportions matter: an sp2 atom must bend out of its plane more easily than
// in it, or a ring of benzene rings stays flat. The shapes these give are held by clean3d.check.ts.
const ANGLE = 0.3, SIDE = 0.15, PLANE = 0.04, SP2 = 0.005, CONJUGATED = 0.006, LINK = 0.012, HAND = 0.3, CONTACT = 0.03;
// The least distance between two atoms: three bonds apart, then further; by how many of the two are hydrogens.
const LEAST = [[1.7, 1.6, 1.5], [2.2, 1.9, 1.58]];
const REACH = 3.2; // contacts are looked for this near, every few steps

// A flat drawing that was turned in 3D (Structure Perspective) is still a flat drawing: its atoms lie in one plane that
// is not the page. It is cleaned up as that drawing seen from its front (the side towards the viewer), and the result
// is turned back the same way. Undefined for a drawing in the page, or one with real depth.
function levelled(m: Mol, ids: number[]): { mol: Mol; back: (r: Mol) => Mol } | undefined {
  const P = ids.map((g): V => [m.atoms[g].location[0], m.atoms[g].location[1], m.atoms[g].location[2] ?? 0]);
  if (P.length < 3 || P.every((q) => Math.abs(q[2]) < 1e-6)) return undefined;
  const c = [0, 1, 2].map((e) => P.reduce((t, q) => t + q[e], 0) / P.length) as V, most = (f: (q: V) => number) => P.reduce((b, q) => (f(q) > f(b) ? q : b));
  const a = sub(most((q) => lenV(sub(q, c))), c), b = sub(most((q) => lenV(crossV(a, sub(q, c)))), c), size = lenV(a);
  let up = crossV(a, b);
  if (lenV(up) < 1e-6 * size * size) return undefined; // every atom on one line
  up = unitV(up);
  if (up[2] < 0) up = [-up[0], -up[1], -up[2]];
  if (P.some((q) => Math.abs(dotV(sub(q, c), up)) > 1e-4 * size)) return undefined;
  // Rodrigues' rotation about the line the plane and the page share, by the angle between them: way 1 into the page,
  // -1 back.
  const axis = unitV(crossV(up, [0, 0, 1])), cos = up[2], sin = Math.sqrt(Math.max(0, 1 - cos * cos));
  const turn = (v: V, way: number): V => { const side = crossV(axis, v), along = dotV(axis, v); return [0, 1, 2].map((e) => v[e] * cos + side[e] * sin * way + axis[e] * along * (1 - cos)) as V; };
  const chosen = new Set(ids), put = (f: (v: V) => V) => (x: Mol): Mol => ({ ...x, atoms: x.atoms.map((q, i) => (chosen.has(i) ? { ...q, location: f([q.location[0], q.location[1], q.location[2] ?? 0]) } : q)) });
  return {
    mol: put((v) => { const r = turn(sub(v, c), 1); return [c[0] + r[0], c[1] + r[1], 0]; })(m),
    back: put((v) => { const r = turn([v[0] - c[0], v[1] - c[1], v[2]], -1); return [c[0] + r[0], c[1] + r[1], c[2] + r[2]]; }),
  };
}

// ids: the atoms to clean up (whole structures). Returns the drawing with those atoms in 3D, with depth shading on
// (as ChemDraw turns it on after 3D Clean Up). An atom keeps an opacity set by hand.
export function clean3d(m: Mol, ids: number[]): Mol {
  const n = ids.length, local = new Map(ids.map((g, k) => [g, k]));
  if (n < 2) return m;
  const turned = levelled(m, ids);
  if (turned) return turned.back(clean3d(turned.mol, ids));
  const bonds = m.bonds.filter((b) => b.type !== HBOND && local.has(b.atoms[0]) && local.has(b.atoms[1])).map((b) => ({ a: local.get(b.atoms[0])!, b: local.get(b.atoms[1])!, type: b.type, stereo: b.stereo, from: b.atoms[0] }));
  const nei: number[][] = ids.map(() => []);
  for (const b of bonds) { nei[b.a].push(b.b); nei[b.b].push(b.a); }
  const el = ids.map((g) => (m.atoms[g].text ? "C" : m.atoms[g].label));
  const p2 = ids.map((g): V => [m.atoms[g].location[0], m.atoms[g].location[1], m.atoms[g].location[2] ?? 0]);

  // Each atom's hybridisation: sp (a triple bond, or two double bonds), sp2 (a double or aromatic bond, an aromatic
  // ring, N or O next to one: amides, anilines, esters; or boron with three neighbours), or sp3; and its ideal angle.
  // Sulfur, phosphorus and heavier atoms out of an aromatic ring are tetrahedral whatever their bonds (a sulfoxide, a
  // sulfone, a phosphate).
  const used = ids.map(() => 0);
  for (const b of bonds) { const o = b.type === AROMATIC ? 1.5 : b.type === 2 || b.type === 3 ? b.type : 1; used[b.a] += o; used[b.b] += o; }
  const graph = { atoms: ids.map((g, k) => ({ el: el[k], charge: m.atoms[g].charge ?? 0, h: m.atoms[g].implicitHCount ?? hydrogens(el[k], m.atoms[g].charge ?? 0, used[k]) })), bonds: bonds.map((b) => ({ a: b.a, b: b.b, order: (b.type === 2 || b.type === 3 ? b.type : 1) as 1 | 2 | 3 })) };
  const aromatic = aromaticAtoms(graph), cycles = rings(graph).filter((r) => r.length <= 8); // not a ring of rings
  for (const b of bonds) if (b.type === AROMATIC) aromatic[b.a] = aromatic[b.b] = true; // rings drawn with delocalised bonds
  const hyb = ids.map((_, k) => {
    const mine = bonds.filter((b) => b.a === k || b.b === k);
    if (!aromatic[k] && !"C N O B".split(" ").includes(el[k])) return 3;
    if (mine.some((b) => b.type === 3) || mine.filter((b) => b.type === 2).length > 1) return 1;
    if (mine.some((b) => b.type === 2 || b.type === AROMATIC) || aromatic[k] || (el[k] === "B" && mine.length <= 3)) return 2;
    return 3;
  });
  for (let k = 0; k < n; k++) if (hyb[k] === 3 && (el[k] === "N" || el[k] === "O") && nei[k].some((j) => hyb[j] === 2) && nei[k].length <= 3) hyb[k] = 2;
  const ideal = (k: number) => (hyb[k] === 1 ? Math.PI : hyb[k] === 2 ? (2 * Math.PI) / 3 : Math.acos(-1 / 3));

  // A pair of atoms as one number (a structure has at most five atoms for each drawn one, with its hydrogens).
  const M = 5 * n + 1, key = (i: number, j: number) => (i < j ? i * M + j : j * M + i);
  const inRing = new Set(cycles.flatMap((r) => r.map((k, x) => key(k, r[(x + 1) % r.length]))));
  // A bond's real length over a C–C single bond's. The unit every length is in: the drawing's median bond over that
  // ratio. So the structure comes out the size it went in, however many times it is cleaned up (a drawing of mostly
  // aromatic rings keeps the rings' size, and its single bonds come out a little longer than drawn).
  const ratio = (b: (typeof bonds)[number]) => {
    const ring = aromatic[b.a] && aromatic[b.b] && (b.type === 1 || b.type === 2) && inRing.has(key(b.a, b.b)), f = b.type === AROMATIC || ring ? 0.91 : b.type === 3 ? 0.78 : b.type === 2 ? 0.87 : hyb[b.a] === 2 && hyb[b.b] === 2 ? 0.97 : 1;
    return (((RADIUS[el[b.a]] ?? 0.76) + (RADIUS[el[b.b]] ?? 0.76)) * f) / CC;
  };
  const flat = p2.every((q) => Math.abs(q[2]) < 1e-6);
  const drawn = bonds.map((b) => lenV(sub(p2[b.a], p2[b.b])) / ratio(b)).sort((x, y) => x - y);
  const unit = drawn[Math.floor(drawn.length / 2)] || 1;

  // A stereocentre's hand as the page draws it: the centre and its neighbours in the page, and only the far ends of its
  // own wedges and hashes out of it (a wedge that starts at a neighbour is that neighbour's). The side of its first
  // three neighbours' plane that the centre is on (with four, the side the fourth is on).
  // Also for a centre drawn flat on a structure that has depth elsewhere (a group drawn onto a cleaned-up structure).
  const drawnHand = (k: number) => {
    if (hyb[k] !== 3 || nei[k].length < 3 || (!flat && nei[k].some((j) => Math.abs(p2[j][2] - p2[k][2]) > 1e-6))) return 0;
    const own = new Map<number, number>();
    for (const b of bonds) if ((b.stereo === 1 || b.stereo === 6) && b.from === ids[k] && (b.a === k || b.b === k)) own.set(b.a === k ? b.b : b.a, b.stereo === 1 ? 0.8 : -0.8);
    if (!own.size) return 0;
    const ref = (j: number): V => [p2[j][0] / unit, p2[j][1] / unit, own.get(j) ?? 0], [a, b, c] = nei[k], o = ref(a);
    const v = dotV(sub(ref(nei[k].length > 3 ? nei[k][3] : k), o), crossV(sub(ref(b), o), sub(ref(c), o)));
    return Math.abs(v) < 1e-6 ? 0 : Math.sign(v);
  };
  const drawnHands = ids.map((_, k) => drawnHand(k));

  // The terms. pair: i, j, a target distance and a stiffness. quad: four atoms, a stiffness and a hand; the volume
  // they span goes to zero (they lie flat, hand 0), or keeps its sign (a stereocentre, hand ±1).
  const pair: number[] = [], quad: number[] = [], bondLength = new Map<number, number>(), double = new Set<number>();
  for (const b of bonds) {
    bondLength.set(key(b.a, b.b), ratio(b));
    pair.push(b.a, b.b, ratio(b), 1);
    if (b.type === 2) double.add(key(b.a, b.b));
  }
  // The hydrogens the drawing leaves out take part: [their atom, how many]. start places them.
  const heavy = nei.map((x) => x.length), left: [number, number][] = [];
  for (let k = 0; k < n; k++) {
    const count = m.atoms[ids[k]].text ? 0 : Math.min(4, graph.atoms[k].h), d = (RADIUS.H + (RADIUS[el[k]] ?? 0.76)) / CC;
    if (count) left.push([k, count]);
    for (let h = 0; h < count; h++) { const j = el.length; el.push("H"); nei.push([k]); nei[k].push(j); bondLength.set(key(k, j), d); pair.push(k, j, d, 1); }
  }
  const all = el.length, bl = (i: number, j: number) => bondLength.get(key(i, j)) ?? 1;

  // A start, in bond lengths: as drawn, or for a flat drawing, with depth from the wedges and hashes (a wedge's far
  // end nearer, a hash's further), each saturated six-membered ring as a chair, and a little depth on every atom, so no
  // saturated part stays flat and a flat shape with strain in it (a ring of benzene rings) can leave the page.
  // chair: the chairs as chosen here (1), each ring's other chair (-1), or no chairs (0).
  const chairs = cycles.filter((r) => r.length === 6 && r.every((k) => hyb[k] === 3));
  const start = (chair: number) => {
  const p = p2.map((q): V => [q[0] / unit, q[1] / unit, q[2] / unit]);
  if (flat) {
    for (const b of bonds) if (b.stereo === 1 || b.stereo === 6) { const [s, e] = b.from === ids[b.a] ? [b.a, b.b] : [b.b, b.a]; p[e][2] = p[s][2] + (b.stereo === 1 ? 0.8 : -0.8); }
    for (const r of chairs) {
      // Of the two chairs, the one with more of the ring's wedged and hashed groups equatorial: a group drawn up is
      // equatorial on a ring atom that is down (a drawn hydrogen counts for the group across from it).
      let up = 0;
      r.forEach((k, x) => { for (const b of bonds) { const e = b.a === k ? b.b : b.a; if ((b.stereo === 1 || b.stereo === 6) && b.from === ids[k] && (b.a === k || b.b === k) && !r.includes(e)) up += (b.stereo === 1 ? 1 : -1) * (x % 2 ? 1 : -1) * (el[e] === "H" ? -1 : 1); } });
      r.forEach((k, x) => { if (Math.abs(p[k][2]) < 1e-6) p[k][2] = chair * (up > 0 ? -1 : 1) * (x % 2 ? 0.25 : -0.25); });
    }
    // Ring systems joined by a single bond between two sp2 atoms (biphenyl, binaphthyl, a ring of benzene rings) start
    // turned a little about the line through those bonds, each the other way from the one before it. They then settle
    // twisted in turn, as they are in crystals, and not each to a side of its own.
    const system = ids.map(() => -1);
    cycles.forEach((r, c) => { const old = new Set(r.map((k) => system[k]).filter((s) => s >= 0)); system.forEach((s, k) => { if (old.has(s) || r.includes(k)) system[k] = c; }); });
    const links = bonds.filter((b) => b.type === 1 && hyb[b.a] === 2 && hyb[b.b] === 2 && system[b.a] >= 0 && system[b.b] >= 0 && system[b.a] !== system[b.b]), way = new Map<number, number>();
    for (const first of links) {
      if (!way.has(system[first.a])) way.set(system[first.a], 1);
      for (let more = true; more;) { more = false; for (const b of links) for (const [s, t] of [[system[b.a], system[b.b]], [system[b.b], system[b.a]]]) if (way.has(s) && !way.has(t)) { way.set(t, -way.get(s)!); more = true; } }
    }
    for (const [s, turn] of way) {
      const mine = ids.flatMap((_, k) => (system[k] === s ? [k] : [])), ends = mine.filter((k) => links.some((b) => b.a === k || b.b === k)), e = p[ends[0]];
      // The line: from one joined atom to the furthest other one, or with only one, to the middle of the rings.
      const to = ends.length > 1 ? ends.map((k) => p[k]).reduce((f, q) => (lenV(sub(q, e)) > lenV(sub(f, e)) ? q : f)) : [0, 1, 2].map((c) => mine.reduce((t, k) => t + p[k][c], 0) / mine.length) as V;
      const line = unitV(sub(to, e));
      for (const k of mine) p[k][2] += turn * 0.3 * (line[0] * (p[k][1] - e[1]) - line[1] * (p[k][0] - e[0]));
    }
    p.forEach((q, k) => { q[2] += Math.sin(k * 12.9898 + 4.1) * 0.05; });
    // A stereocentre starts on its own side of its neighbours' plane (a chair may have put it on the other), so that
    // its hydrogen starts on the right side too.
    drawnHands.forEach((want, k) => {
      if (!want) return;
      const [a, b, c] = nei[k].map((j) => p[j]), nn = crossV(sub(b, a), sub(c, a)), nl = lenV(nn) || 1, off = dotV(sub(p[k], a), nn) / nl;
      if (Math.sign(off) !== want || Math.abs(off) < 0.3) for (let e = 0; e < 3; e++) p[k][e] += (nn[e] / nl) * (want * 0.35 - off);
    });
  }

  // The hydrogens the drawing leaves out, each on the open side of its atom: one straight out; two either side in the
  // plane (sp2) or above and below it (sp3); more round a cone. In a structure that is in 3D already, those of a
  // methyl group go staggered to its neighbour's other atoms, and those of an sp2 atom with one neighbour in their
  // plane (an O–H towards a C=O): where they settled, so a second clean-up starts near where the first ended. Not on
  // a flat drawing: hydrogens placed in the page kept crowded rings flat and cost chairs.
  for (const [k, count] of left) {
    const to = nei[k].slice(0, heavy[k]).map((j) => unitV(sub(p[k], p[j])));
    let out = unitV(to.reduce((s, v): V => [s[0] + v[0], s[1] + v[1], s[2] + v[2]], [0, 0, 0]));
    if (lenV(out) < 1e-6) out = to.length ? unitV(crossV(to[0], [0, 0, k % 2 ? -1 : 1])) : [1, 0, 0]; // a straight chain: to alternate sides
    const j = nei[k][0], syn = to.length === 1 && hyb[k] === 2 && count === 1 ? nei[j].find((q) => q !== k && double.has(key(j, q))) : undefined;
    const far = !flat && to.length === 1 && (hyb[k] === 2 || (hyb[k] === 3 && count === 3)) ? syn ?? nei[j].find((q) => q !== k && q < p.length) : undefined;
    let up: V = far !== undefined ? sub(p[j], p[far]) : to.length > 1 ? unitV(crossV(to[0], to[1])) : [0, 0, 1], lone = far !== undefined;
    if (lenV(crossV(up, out)) < 1e-3) { up = Math.abs(out[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0]; lone = false; }
    const side = unitV(crossV(up, out)), d = bl(k, nei[k][heavy[k]]);
    up = crossV(out, side);
    const [c, s] = lone ? (hyb[k] === 2 ? [0.5, 0.866] : [1 / 3, 0.94]) : count === 1 ? [1, 0] : count === 2 ? (hyb[k] === 2 ? [0.5, 0.866] : [0.58, 0.82]) : [1 / 3, 0.94];
    for (let h = 0; h < count; h++) {
      const turn = !lone ? (2 * Math.PI * h) / count + (hyb[k] === 2 ? Math.PI / 2 : 0) : hyb[k] === 2 ? Math.PI * (h + (syn === undefined ? 0 : 1)) : (2 * Math.PI * (h + (count === 2 ? 1 : 0))) / 3;
      p.push([0, 1, 2].map((x) => p[k][x] + (out[x] * c + (up[x] * Math.cos(turn) + side[x] * Math.sin(turn)) * s) * d) as V);
    }
  }
  return p;
  };
  const p = start(1);
  // close: atoms one or two bonds apart (and across a double bond), which keep no least distance. third: three apart.
  const close = new Set(bondLength.keys()), third = new Set<number>();
  // The angle wanted at j between its neighbours i and k: its hybridisation's, but in a small ring the ring's own (60°
  // and 90° in rings of three and four, 104° at a saturated atom in a ring of five, a regular polygon's in a ring of
  // five, or in a ring of up to seven sp2 atoms), and at an sp2 atom of such a ring the rest of 360° outside it.
  const inside = (j: number, i: number, k: number) => {
    const r = cycles.find((c) => c.includes(i) && c.includes(j) && c.includes(k));
    if (!r || (r.length > 5 && !(r.length <= 7 && r.every((q) => hyb[q] === 2)))) return undefined;
    return r.length === 5 && hyb[j] === 3 ? (104 * Math.PI) / 180 : Math.PI - (2 * Math.PI) / r.length;
  };
  const corner = (j: number, i: number, k: number) => {
    const own = inside(j, i, k);
    if (own !== undefined || hyb[j] !== 2 || nei[j].length !== 3) return own ?? ideal(j);
    let count = 0, sum = 0;
    for (let x = 0; x < 3; x++) for (let y = x + 1; y < 3; y++) { const t = inside(j, nei[j][x], nei[j][y]); if (t !== undefined) { count++; sum += t; } }
    return count ? (2 * Math.PI - sum) / (3 - count) : ideal(j);
  };
  for (let j = 0; j < n; j++) for (let x = 0; x < nei[j].length; x++) for (let y = x + 1; y < nei[j].length; y++) {
    const [i, k] = [nei[j][x], nei[j][y]], [a, c] = [bl(i, j), bl(j, k)];
    pair.push(i, k, Math.sqrt(a * a + c * c - 2 * a * c * Math.cos(corner(j, i, k))), ANGLE);
    close.add(key(i, k));
  }
  // Atoms joined by a hydrogen bond stay as near as one holds them.
  for (const b of m.bonds) if (b.type === HBOND && local.has(b.atoms[0]) && local.has(b.atoms[1])) {
    const [i, j] = [local.get(b.atoms[0])!, local.get(b.atoms[1])!];
    pair.push(i, j, (el[i] === "H" || el[j] === "H" ? 1.9 : 2.8) / CC, CONTACT);
    close.add(key(i, j));
  }
  for (const b of bonds) {
    const both = hyb[b.a] === 2 && hyb[b.b] === 2, d = bl(b.a, b.b);
    // Flat for good: a double bond, a bond of an aromatic ring, and an amide's bond (from an N to a C=O, C=N or C=S).
    // A weak pull to flat: the bond between two aromatic rings (biphenyl's), and a bond to an O or N (an aryl ether's,
    // a nitro group's: they turn when they are crowded). A pull between the two: a bond between two carbon atoms
    // (styrene's, butadiene's, a ketone's to its ring), an ester's or an acid's bond from its O to its C=O (firmer, it
    // made twist-boats of acetylated sugars), and an amide N's other bond (an anilide's).
    const amide = (q: number, c: number) => (el[q] === "N" || el[q] === "O") && !aromatic[q] && el[c] === "C" && !aromatic[c] && nei[c].some((o) => el[o] !== "C" && double.has(key(c, o)));
    const anilide = (q: number) => el[q] === "N" && nei[q].some((c) => amide(q, c));
    const weak = (aromatic[b.a] && aromatic[b.b]) || ((el[b.a] !== "C" || el[b.b] !== "C") && !anilide(b.a) && !anilide(b.b) && !amide(b.a, b.b) && !amide(b.b, b.a));
    const firm = b.type === 2 || b.type === AROMATIC || (aromatic[b.a] && aromatic[b.b] && inRing.has(key(b.a, b.b)));
    const page = (q: number): V => (flat ? [p[q][0], p[q][1], 0] : p[q]), line = sub(page(b.b), page(b.a)), off = (q: number, from: number) => crossV(line, sub(page(q), page(from)));
    const ring = cycles.find((r) => r.length < 8 && r.includes(b.a) && r.includes(b.b));
    for (const i of nei[b.a]) for (const l of nei[b.b]) {
      if (i === b.b || l === b.a || i === l) continue;
      if (both) quad.push(i, b.a, b.b, l, firm ? PLANE : weak ? CONJUGATED : LINK, 0);
      if (b.type === 2) {
        // Across a double bond, each pair of substituents stays cis or trans, in the plane, at the angles wanted at
        // its two atoms (so past an sp atom, as in an allene, the far atom is in line). In a ring of up to seven: cis
        // when both are in the ring, or neither (however the ring is drawn; a ring squashed to show it edge-on has
        // no sides to read). Else as it is drawn: cis when the two point the same way off the bond's line. A flat
        // drawing is read in the page (a wedge's depth is not a side); a structure in 3D, in 3D.
        if (close.has(key(i, l))) continue;
        const cis = ring ? ring.includes(i) === ring.includes(l) : dotV(off(i, b.a), off(l, b.b)) > 0, [a, c] = [bl(i, b.a), bl(b.b, l)], [A, B] = [corner(b.a, i, b.b), corner(b.b, b.a, l)];
        pair.push(i, l, Math.hypot(d - a * Math.cos(A) - c * Math.cos(B), (cis ? c : -c) * Math.sin(B) - a * Math.sin(A)), SIDE);
        close.add(key(i, l));
      } else third.add(key(i, l));
    }
  }
  // An sp2 atom with three neighbours lies in their plane.
  for (let k = 0; k < n; k++) if (hyb[k] === 2 && nei[k].length === 3) quad.push(k, nei[k][0], nei[k][1], nei[k][2], SP2, 0);
  // Stereocentres: an sp3 atom with a wedge or hash and three or more drawn neighbours; its hand is the page's
  // (drawnHand), or for a structure in 3D already, the side of the plane of its first three neighbours it is on.
  const volume = (o: V, a: V, b: V, c: V) => dotV(sub(a, o), crossV(sub(b, o), sub(c, o)));
  for (let k = 0; k < n; k++) {
    if (hyb[k] !== 3 || heavy[k] < 3 || !bonds.some((b) => (b.stereo === 1 || b.stereo === 6) && (b.a === k || b.b === k) && b.from === ids[k])) continue;
    const [a, b, c] = nei[k];
    quad.push(a, k, b, c, HAND, drawnHands[k] || Math.sign(volume(p[a], p[k], p[b], p[c])) || 1);
  }

  // Positions and the slope of the energy at them, as flat lists.
  const x = new Float64Array(all * 3), g = new Float64Array(all * 3), v = new Float64Array(all * 3), seen = new Float64Array(all * 3);
  let contact: number[] = [], energy = 0;
  // Hydrogens (drawn ones too), and what can make a hydrogen bond: N, O and a hydrogen on one.
  const light = el.map((e) => e === "H"), polar = el.map((e, k) => e === "N" || e === "O" || (light[k] && nei[k].length > 0 && (el[nei[k][0]] === "N" || el[nei[k][0]] === "O")));
  // The pairs near enough to touch soon: not close ones, with the least distance each keeps. Looked for again when an
  // atom has moved half of the room REACH leaves beyond the largest least distance.
  const look = () => {
    contact = [];
    seen.set(x);
    for (let i = 0; i < all; i++) for (let j = i + 1; j < all; j++) {
      const dx = x[i * 3] - x[j * 3], dy = x[i * 3 + 1] - x[j * 3 + 1], dz = x[i * 3 + 2] - x[j * 3 + 2];
      if (dx * dx + dy * dy + dz * dz > REACH * REACH) continue;
      const kk = i * M + j;
      if (close.has(kk)) continue;
      // Two of N and O, or one and a hydrogen on another, may come as near as a hydrogen bond brings them (so
      // salicylic acid and 2-nitrophenol stay flat), and two hydrogens on N or O to 2.0 Å (the two N–H inside a
      // porphyrin). Any other hydrogen may come to 2.4 Å of an N or O (so nitrobenzene and benzoic acid stay flat).
      const hs = (light[i] ? 1 : 0) + (light[j] ? 1 : 0), far = !third.has(kk), bonding = polar[i] && polar[j];
      contact.push(i, j, !far ? LEAST[0][hs] : bonding ? [1.7, 1.2, 1.3][hs] : hs === 1 && (polar[i] || polar[j]) && (light[i] ? !polar[i] : !polar[j]) ? 1.55 : LEAST[1][hs]);
    }
  };
  const spring = (i: number, j: number, d: number, w: number, least: boolean) => {
    const dx = x[i * 3] - x[j * 3], dy = x[i * 3 + 1] - x[j * 3 + 1], dz = x[i * 3 + 2] - x[j * 3 + 2], rr = dx * dx + dy * dy + dz * dz;
    if (least && rr >= d * d) return;
    const r = Math.sqrt(rr) || 1e-9, f = (2 * w * (r - d)) / r;
    energy += w * (r - d) * (r - d);
    g[i * 3] += f * dx; g[i * 3 + 1] += f * dy; g[i * 3 + 2] += f * dz;
    g[j * 3] -= f * dx; g[j * 3 + 1] -= f * dy; g[j * 3 + 2] -= f * dz;
  };
  const at = (k: number): V => [x[k * 3], x[k * 3 + 1], x[k * 3 + 2]];
  const slope = () => {
    g.fill(0);
    energy = 0;
    for (let t = 0; t < pair.length; t += 4) spring(pair[t], pair[t + 1], pair[t + 2], pair[t + 3], false);
    for (let t = 0; t < contact.length; t += 3) spring(contact[t], contact[t + 1], contact[t + 2], CONTACT, true);
    for (let t = 0; t < quad.length; t += 6) {
      // Flat: the volume goes to zero. A hand: only a volume under 0.5 of its own sign is pushed (a tetrahedral centre
      // has 0.77). In plain numbers: this runs for every term at every step.
      const o = quad[t] * 3, a = quad[t + 1] * 3, b = quad[t + 2] * 3, c = quad[t + 3] * 3, hand = quad[t + 5];
      const ax = x[a] - x[o], ay = x[a + 1] - x[o + 1], az = x[a + 2] - x[o + 2], bx = x[b] - x[o], by = x[b + 1] - x[o + 1], bz = x[b + 2] - x[o + 2], cx = x[c] - x[o], cy = x[c + 1] - x[o + 1], cz = x[c + 2] - x[o + 2];
      const gax = by * cz - bz * cy, gay = bz * cx - bx * cz, gaz = bx * cy - by * cx, gbx = cy * az - cz * ay, gby = cz * ax - cx * az, gbz = cx * ay - cy * ax, gcx = ay * bz - az * by, gcy = az * bx - ax * bz, gcz = ax * by - ay * bx;
      const vol = ax * gax + ay * gay + az * gaz, miss = hand ? Math.min(0, hand * vol - 0.5) * hand : vol, f = 2 * quad[t + 4] * miss;
      if (!f) continue;
      energy += quad[t + 4] * miss * miss;
      g[a] += f * gax; g[b] += f * gbx; g[c] += f * gcx; g[o] -= f * (gax + gbx + gcx);
      g[a + 1] += f * gay; g[b + 1] += f * gby; g[c + 1] += f * gcy; g[o + 1] -= f * (gay + gby + gcy);
      g[a + 2] += f * gaz; g[b + 2] += f * gbz; g[c + 2] += f * gcz; g[o + 2] -= f * (gaz + gbz + gcz);
    }
  };
  // Downhill with momentum (FIRE: Bitzek et al., Phys. Rev. Lett. 97, 170201): the step grows while the atoms keep
  // moving downhill, and they stop and the step halves when they overshoot. It ends when no atom is pushed any more,
  // after 4,000 steps, or (past 400 steps) after 20 million terms worked out: that keeps the largest structure within
  // its time, however many contacts it has (a chain of cages has five times a chain's). share: the part of that to use.
  const settle = (share = 1) => {
    v.fill(0);
    let dt = 0.05, mix = 0.1, good = 0, work = 0;
    for (let step = 0, moved = Infinity; step < 4000 * share && (work < 2e7 * share || step < 400 * share); step++) {
      if (moved > 0.25) look();
      work += pair.length / 4 + quad.length / 6 + contact.length / 3;
      slope();
      let power = 0, gg = 0, vv = 0, most = 0;
      for (let k = 0; k < g.length; k++) { power -= g[k] * v[k]; gg += g[k] * g[k]; vv += v[k] * v[k]; most = Math.max(most, Math.abs(g[k])); }
      if (most < 1e-6 && step > 20) break;
      if (power > 0) {
        const s = mix * Math.sqrt(vv / gg);
        for (let k = 0; k < g.length; k++) v[k] = (1 - mix) * v[k] - s * g[k];
        if (++good > 5) { dt = Math.min(dt * 1.1, 0.25); mix *= 0.99; }
      } else { v.fill(0); dt *= 0.5; mix = 0.1; good = 0; }
      moved = 0;
      for (let k = 0; k < g.length; k += 3) {
        for (let e = k; e < k + 3; e++) { v[e] -= dt * g[e]; x[e] += dt * v[e]; }
        moved = Math.max(moved, (x[k] - seen[k]) ** 2 + (x[k + 1] - seen[k + 1]) ** 2 + (x[k + 2] - seen[k + 2]) ** 2);
      }
    }
  };
  // One clean-up from a start. Returns the energy it ends at.
  const run = (from: V[], share = 1) => {
  from.forEach((q, k) => x.set(q, k * 3));
  settle(share);
  // A saturated atom with three drawn neighbours (and its one hydrogen, if it has one) that settled flat among them (a bridgehead, when the
  // rings folded onto the side its hydrogen started on) goes out of their plane, away from the atoms round it, with
  // its hydrogen beyond it. Then the shape settles again.
  let pressed = false;
  for (let k = 0; k < n; k++) {
    if (hyb[k] !== 3 || heavy[k] !== 3 || nei[k].length > 4 || drawnHands[k]) continue;
    const [a, b, c] = nei[k].map((j) => at(j)), o = at(k), turn = (q: V, r: V) => Math.acos(Math.max(-1, Math.min(1, dotV(unitV(sub(q, o)), unitV(sub(r, o))))));
    if (turn(a, b) + turn(b, c) + turn(a, c) < 6) continue; // 344°: a tetrahedral atom has 328°, a flat one 360°
    const near: V = [0, 0, 0];
    let count = 0;
    for (let j = 0; j < n; j++) { const q = at(j); if (j !== k && lenV(sub(q, o)) < 3) { count++; for (let e = 0; e < 3; e++) near[e] += q[e]; } }
    const up = unitV(crossV(sub(b, a), sub(c, a))), side = dotV(sub(o, near.map((t) => t / count) as V), up) < 0 ? -1 : 1, h = nei[k][3], off = dotV(sub(o, a), up);
    for (let e = 0; e < 3; e++) { x[k * 3 + e] += up[e] * (side * 0.35 - off); if (h !== undefined) x[h * 3 + e] = x[k * 3 + e] + up[e] * side * bl(k, h); }
    pressed = true;
  }
  if (pressed) settle(share / 2);
  slope();
  return energy;
  };
  let lowest = run(p);
  // A flat drawing with saturated six-membered rings that ends strained (a bond or an angle's far side a fifth of a
  // bond off: sparteine, whose bridge the chairs put on the wrong side; quinuclidine, whose rings are boats) is cleaned
  // up again from each ring's other chair, and from no chairs: for a quarter of the steps, and to the end only when
  // that is clearly better already. The shape with the least energy stays, unless it turns a stereocentre over. Only
  // for a structure of up to 200 atoms with its hydrogens: a larger one would take up to three times as long.
  const strained = () => { for (let t = 0; t < pair.length; t += 4) if (pair[t + 3] >= SIDE && Math.abs(lenV(sub(at(pair[t]), at(pair[t + 1]))) - pair[t + 2]) > 0.2) return true; return false; };
  // The stereocentres with the wrong hand: by the side of its first three neighbours' plane the fourth is on, where a
  // centre has four (the centre itself can be on the right side of a shape that is turned over), else the centre.
  const wrong = () => {
    let c = 0;
    for (let t = 0; t < quad.length; t += 6) { const k = quad[t + 1]; if (quad[t + 5] && quad[t + 5] * volume(at(quad[t]), at(heavy[k] > 3 ? nei[k][3] : k), at(quad[t + 2]), at(quad[t + 3])) <= 0) c++; }
    return c;
  };
  if (flat && chairs.length && all <= 200 && strained()) for (const chair of [-1, 0]) {
    const kept = x.slice(), hands = wrong();
    if (run(start(chair), 0.25) > 0.95 * lowest) { x.set(kept); continue; }
    settle();
    slope();
    if (wrong() > hands) x.set(kept); else lowest = energy;
  }

  // A flat drawing that comes out flat (benzene, naphthalene) lies in the page exactly, as it was drawn: when its atoms
  // are all within 0.05 of one plane that leans less than 9° from the page (the start's little depth can lean it).
  let level = flat;
  if (flat) {
    let [sx, sy, sz, xx, xy, yy, xz, yz] = [0, 0, 0, 0, 0, 0, 0, 0];
    for (let k = 0; k < n; k++) { sx += x[k * 3]; sy += x[k * 3 + 1]; sz += x[k * 3 + 2]; }
    for (let k = 0; k < n; k++) { const [dx, dy, dz] = [x[k * 3] - sx / n, x[k * 3 + 1] - sy / n, x[k * 3 + 2] - sz / n]; xx += dx * dx; xy += dx * dy; yy += dy * dy; xz += dx * dz; yz += dy * dz; }
    const det = xx * yy - xy * xy, [a, b] = Math.abs(det) > 1e-9 ? [(xz * yy - yz * xy) / det, (yz * xx - xz * xy) / det] : [0, 0];
    for (let k = 0; k < n && level; k++) level = Math.abs(x[k * 3 + 2] - sz / n - a * (x[k * 3] - sx / n) - b * (x[k * 3 + 1] - sy / n)) < 0.05;
    level &&= Math.hypot(a, b) < 0.15;
  }
  // The structure stays where it was drawn: its middle on the drawing's middle.
  // And the size it was drawn: its median bond comes out as it went in, so a second clean-up changes no size.
  const size = bonds.map((b) => lenV(sub(at(b.a), at(b.b))) / ratio(b)).sort((a, b) => a - b)[Math.floor(bonds.length / 2)] || 1, scale = unit / size;
  const mid = (e: number) => { let s = 0; for (let k = 0; k < n; k++) s += x[k * 3 + e]; return (s / n) * scale; };
  const was = [0, 1].map((e) => p2.reduce((s, q) => s + q[e], 0) / n), shift: V = [was[0] - mid(0), was[1] - mid(1), -mid(2)];
  return {
    ...m,
    atoms: m.atoms.map((a, i) => {
      const k = local.get(i);
      if (k === undefined) return a;
      return { ...a, shade: a.shade || true, location: [x[k * 3] * scale + shift[0], x[k * 3 + 1] * scale + shift[1], level ? 0 : x[k * 3 + 2] * scale + shift[2]] as V };
    }),
  };
}
