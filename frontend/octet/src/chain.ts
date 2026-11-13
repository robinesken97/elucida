// Peptides and oligonucleotides laid out along a straight backbone (issues 27 and 99), as chemists draw them: the
// backbone a level zigzag, a peptide's side chains above and below it by turns, and the sugars and bases of RNA or
// DNA all on one side. Clean Up Structure lays a chain out this way (chem.ts cleanUp), and so does the Sequence tool
// (chem.ts fullMol). Each side chain, sugar and base keeps the shape it had; only where it sits changes.
import type { Mol } from "./render.ts";
import { bondedTo, ringBonds } from "./edit.ts";

type P = [number, number];
// The fewest residues that make a chain: three amino acids (a dipeptide such as aspartame stays a small molecule), or
// two nucleotides.
const LEAST_PEPTIDE = 3, LEAST_NUCLEIC = 2;
const ZIG = Math.sqrt(3) / 2;

// The backbone of the longest peptide or oligonucleotide chain in a structure (frag: its atoms), in order, and the
// backbone bonds drawn level (by the index of the first atom): the bond from a nucleotide's O3' to its P. bases: each
// nucleotide's C1' and the N of its base. Undefined when there is no chain long enough.
type Backbone = { path: number[]; flat: Set<number>; bases: [number, number][] };
function backbone(m: Mol, frag: number[], at: number[][], order: (i: number, j: number) => number): Backbone | undefined {
  const el = (i: number) => (m.atoms[i].inner ? "" : m.atoms[i].label);
  // The longest run of units, each followed by exactly one other.
  const longest = <T>(units: T[], next: (u: T) => T[]): T[] => {
    const after = units.map((u) => { const n = next(u); return n.length === 1 ? n[0] : undefined; });
    let best: T[] = [];
    for (const u of units.filter((u) => !after.includes(u))) {
      const run: T[] = [];
      for (let v: T | undefined = u; v !== undefined && !run.includes(v); v = after[units.indexOf(v)]) run.push(v);
      if (run.length > best.length) best = run;
    }
    return best;
  };
  // A peptide: residues N–Cα–C(=O), each C bonded to the next residue's N.
  const residues: number[][] = [];
  for (const c of frag) {
    if (el(c) !== "C" || !at[c].some((o) => el(o) === "O" && order(c, o) === 2 && at[o].length === 1)) continue;
    for (const a of at[c]) if (el(a) === "C" && order(a, c) === 1) for (const n of at[a]) if (el(n) === "N" && order(n, a) === 1) residues.push([n, a, c]);
  }
  const peptide = longest(residues, ([, , c]) => residues.filter(([n]) => order(c, n) === 1));
  if (peptide.length >= LEAST_PEPTIDE) return { path: peptide.flat(), flat: new Set(), bases: [] };
  // A nucleic acid: furanoses O4'–C1'(base N)–C2'–C3'(O3')–C4'(C5'–O5'), each O3' bonded through a P to the next O5'.
  const units: { o5: number; c5: number; c4: number; c3: number; o3: number; c1: number; n: number }[] = [];
  const out = (i: number, ring: number[], label: string) => at[i].find((j) => !ring.includes(j) && el(j) === label && order(i, j) === 1);
  for (const o4 of frag) {
    if (el(o4) !== "O" || at[o4].length !== 2) continue;
    for (const [c1, c4] of [at[o4], [...at[o4]].reverse()]) for (const c2 of at[c1]) for (const c3 of at[c2]) {
      const ring = [o4, c1, c2, c3, c4];
      if (new Set(ring).size !== 5 || !ring.slice(1).every((i) => el(i) === "C") || !at[c3].includes(c4) || out(c1, ring, "N") === undefined) continue;
      const c5 = out(c4, ring, "C"), o5 = c5 === undefined ? undefined : at[c5].find((j) => j !== c4 && el(j) === "O"), o3 = out(c3, ring, "O");
      if (c5 !== undefined && o5 !== undefined && o3 !== undefined) units.push({ o5, c5, c4, c3, o3, c1, n: out(c1, ring, "N")! });
    }
  }
  const link = (o3: number, o5: number) => at[o3].find((p) => el(p) === "P" && at[p].includes(o5));
  const chain = longest(units, (u) => units.filter((v) => link(u.o3, v.o5) !== undefined));
  if (chain.length < LEAST_NUCLEIC) return undefined;
  // A phosphate on either end is backbone too.
  const end = (o: number) => at[o].filter((p) => el(p) === "P").slice(0, 1);
  const path = end(chain[0].o5), flat = new Set<number>();
  chain.forEach((u, k) => {
    if (k) { flat.add(path.length - 1); path.push(link(chain[k - 1].o3, u.o5)!); }
    path.push(u.o5, u.c5, u.c4, u.c3, u.o3);
  });
  path.push(...end(chain[chain.length - 1].o3));
  return { path, flat, bases: chain.map((u): [number, number] => [u.c1, u.n]) };
}

// A chain and the groups off its backbone: their atoms, the backbone atoms they bond to (ends, by place on the
// backbone) and their atoms that do (via). A ring fused onto the backbone (proline's, a sugar) has its bond drawn level.
// Undefined when there is no chain, or when a group bonds back to the backbone further along (a disulfide, a cyclic
// peptide).
type Group = { atoms: number[]; ends: number[]; via: number[] };
function chainOf(m: Mol, frag: number[]) {
  const at = bondedTo(m), orders = new Map<number, number>(), n = m.atoms.length;
  for (const b of m.bonds) { orders.set(b.atoms[0] * n + b.atoms[1], b.type); orders.set(b.atoms[1] * n + b.atoms[0], b.type); }
  const order = (i: number, j: number) => orders.get(i * n + j) ?? 0;
  const bb = backbone(m, frag, at, order);
  if (!bb) return undefined;
  const onPath = new Map(bb.path.map((i, k) => [i, k])), groups: Group[] = [], seen = new Set<number>();
  for (const s of frag) {
    if (onPath.has(s) || seen.has(s)) continue;
    const g: Group = { atoms: [s], ends: [], via: [] };
    seen.add(s);
    for (let k = 0; k < g.atoms.length; k++) for (const j of at[g.atoms[k]]) {
      if (onPath.has(j)) { g.ends.push(onPath.get(j)!); g.via.push(g.atoms[k]); } else if (!seen.has(j)) { seen.add(j); g.atoms.push(j); }
    }
    g.ends = [...new Set(g.ends)].sort((p, q) => p - q);
    if (g.ends.length === 2 && g.ends[1] === g.ends[0] + 1) bb.flat.add(g.ends[0]);
    else if (g.ends.length !== 1) return undefined;
    groups.push(g);
  }
  return { ...bb, groups, at, order, onPath, seen };
}

// The residues of a peptide or oligonucleotide (frag: one structure's atoms), in order, for HELM and FASTA: each
// residue's atoms (a nucleic acid's phosphates are residues of their own), and the groups on a peptide's ends (an
// acetyl on the N, an NH2 or OH on the C=O). Undefined when it is not one.
export function chainResidues(m: Mol, frag: number[]): { nucleic: boolean; residues: number[][]; start: number[]; end: number[] } | undefined {
  const c = chainOf(m, frag);
  if (!c) return undefined;
  const { path, groups, bases } = c, own = (ks: number[]) => [...ks.map((k) => path[k]), ...groups.filter((g) => g.ends.every((e) => ks.includes(e))).flatMap((g) => g.atoms)];
  if (bases.length) {
    const residues: number[][] = [];
    for (let k = 0; k < path.length; k += m.atoms[path[k]].label === "P" ? 1 : 5) residues.push(own(m.atoms[path[k]].label === "P" ? [k] : [k, k + 1, k + 2, k + 3, k + 4]));
    return { nucleic: true, residues, start: [], end: [] };
  }
  const last = path.length - 1, cap = (k: number) => groups.filter((g) => g.ends[0] === k && g.ends.length === 1 && !(k === last && g.atoms.length === 1 && c.order(g.via[0], path[k]) === 2)).flatMap((g) => g.atoms);
  const start = cap(0), end = cap(last), capped = new Set([...start, ...end]);
  const residues = Array.from({ length: path.length / 3 }, (_, r) => own([3 * r, 3 * r + 1, 3 * r + 2]).filter((i) => !capped.has(i)));
  return { nucleic: false, residues, start, end };
}

// New places for the atoms of a peptide or oligonucleotide (frag: one structure's atoms), in bond lengths, or undefined
// when it is not one (chainOf). Each backbone atom is a level zigzag's. A ring fused onto the backbone sits on its
// level bond, on the outside. Every other group off the backbone points away from it, a chain in it as a zigzag.
export function chainLayout(m: Mol, frag: number[]): Map<number, P> | undefined {
  const bb = chainOf(m, frag);
  if (!bb) return undefined;
  const { path, flat, groups, at, order, onPath, seen } = bb;
  // A proline ring lies on the side of the residue before it, so that residue's Cα–C bond is level too: the ring then
  // lies on the other side from its side chain.
  if (!bb.bases.length) for (const k of [...flat]) if (k >= 3 && !flat.has(k - 3)) flat.add(k - 2);
  // The backbone: a peptide's first N low, so its first side chain points up; a nucleic acid's sugars all up.
  const level = [0], xy: P[] = [[0, 0]];
  for (let k = 1; k < path.length; k++) {
    level.push(flat.has(k - 1) ? level[k - 1] : 1 - level[k - 1]);
    xy.push([xy[k - 1][0] + (flat.has(k - 1) ? 1 : ZIG), 0]);
  }
  const sugar = groups.find((g) => g.ends.length === 2);
  if (bb.bases.length && sugar && !level[sugar.ends[0]]) level.forEach((v, k) => (level[k] = 1 - v));
  level.forEach((v, k) => (xy[k][1] = v / 2));
  const placed = new Map<number, P>(path.map((i, k) => [i, xy[k]]));
  // The old drawing, in bond lengths.
  const old = (i: number): P => [m.atoms[i].location[0], m.atoms[i].location[1]];
  const angle = (p: P, q: P) => Math.atan2(q[1] - p[1], q[0] - p[0]);
  const lengths = m.bonds.filter((b) => onPath.has(b.atoms[0]) || seen.has(b.atoms[0])).map((b) => Math.hypot(old(b.atoms[0])[0] - old(b.atoms[1])[0], old(b.atoms[0])[1] - old(b.atoms[1])[1])).sort((p, q) => p - q);
  const unit = lengths[lengths.length >> 1] || 1;
  // A group moved whole: its old point from goes to to, and the rest turns by turn, mirrored first (across the line at
  // the angle mirror through from) when given.
  const move = (atoms: number[], from: P, to: P, turn: number, mirror?: number) => {
    for (const i of atoms) {
      let [dx, dy] = [(old(i)[0] - from[0]) / unit, (old(i)[1] - from[1]) / unit];
      if (mirror !== undefined) [dx, dy] = [dx * Math.cos(2 * mirror) + dy * Math.sin(2 * mirror), dx * Math.sin(2 * mirror) - dy * Math.cos(2 * mirror)];
      placed.set(i, [to[0] + dx * Math.cos(turn) - dy * Math.sin(turn), to[1] + dx * Math.sin(turn) + dy * Math.cos(turn)]);
    }
  };
  const outward = (k: number) => (level[k] ? Math.PI / 2 : -Math.PI / 2);
  const side = (get: (i: number) => P, u: number, v: number, w: number) => { const p = get(u), q = get(v), r = get(w); return Math.sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])); };
  const now = (i: number) => placed.get(i)!;
  // A group bonded by one atom (a, to the placed atom from, going out at dir): a chain as a zigzag that goes on from
  // the backbone's, so a side chain's first step is toward the end of the backbone (away from the C=O before it). At a
  // branch the larger part goes on along the zigzag, and a lone C=O oxygen goes to the other side; two parts alike (a
  // threonine's OH and CH3) keep their sides, so Clean Up again changes nothing. A double bond keeps its side (E or Z).
  // A ring, with all beyond it, moves whole, its bond to from on the zigzag. turn: the side of the next step (1
  // anticlockwise), or for a ring, the side its middle lies on, each atom other than carbon counted twice, so each ring
  // of a kind (an indole, a purine, a thymine, near symmetrical as it is) faces the same way every time. A ring whose
  // middle lies on its bond (a phenyl) keeps its side.
  const rings = ringBonds(m), ringed = new Set(m.bonds.flatMap((b, k) => (rings[k] ? b.atoms : [])));
  const grow = (a: number, from: number, dir: number, group: Set<number>, turn: number) => {
    const to: P = [now(from)[0] + Math.cos(dir), now(from)[1] + Math.sin(dir)];
    if (ringed.has(a)) {
      const whole = [a], into = new Set(whole);
      for (let q = 0; q < whole.length; q++) for (const j of at[whole[q]]) if (j !== from && group.has(j) && !into.has(j)) { into.add(j); whole.push(j); }
      const was = angle(old(from), old(a));
      move(whole, old(a), to, dir - was);
      const weight = (j: number) => (m.atoms[j].label === "C" ? 1 : 2), total = whole.reduce((sum, j) => sum + weight(j), 0);
      const mid = [0, 1].map((d) => whole.reduce((sum, j) => sum + weight(j) * now(j)[d], 0) / total);
      if (turn * (Math.cos(dir) * (mid[1] - to[1]) - Math.sin(dir) * (mid[0] - to[0])) < -0.05) move(whole, old(a), to, dir - was, was);
      return;
    }
    placed.set(a, to);
    const was = angle(old(from), old(a)), rel = (c: number) => { const t = angle(old(a), old(c)) - was; return Math.atan2(Math.sin(t), Math.cos(t)); };
    const kids = at[a].filter((c) => c !== from && group.has(c)).sort((p, q) => rel(p) - rel(q));
    const size = (c: number) => { const part = [c]; for (let q = 0; q < part.length; q++) for (const j of at[part[q]]) if (j !== a && group.has(j) && !part.includes(j)) part.push(j); return part.length; };
    if (kids.length === 2) {
      const rank = (c: number) => 2 * size(c) + (order(a, c) >= 2 ? 0 : 1);
      kids.sort((p, q) => rank(q) - rank(p) || turn * (rel(q) - rel(p)));
      kids.forEach((c, s) => grow(c, a, dir + (s ? -turn : turn) * (Math.PI / 3), group, s ? turn : -turn));
      return;
    }
    if (kids.length === 1) {
      let t = turn;
      const before = at[from].find((j) => j !== a && placed.has(j)), c = kids[0];
      if (order(from, a) === 2 && before !== undefined) {
        const at60 = (s: number): P => [to[0] + Math.cos(dir + s * (Math.PI / 3)), to[1] + Math.sin(dir + s * (Math.PI / 3))];
        if (side(old, from, a, before) * side(old, from, a, c) !== side((x) => (x === c ? at60(t) : now(x)), from, a, before) * side((x) => (x === c ? at60(t) : now(x)), from, a, c)) t = -t;
      }
      return grow(c, a, dir + t * (Math.PI / 3), group, -t);
    }
    const spread = kids.map((_, s) => (s - (kids.length - 1) / 2) * ((2 * Math.PI) / (kids.length + 1)));
    kids.forEach((c, s) => grow(c, a, dir + spread[s], group, spread[s] ? -Math.sign(spread[s]) : turn));
  };
  // Rings fused onto the backbone first, so the groups after them keep clear of them.
  for (const [k, i] of path.entries()) {
    // A ring fused onto the bond to the next atom: on that bond, mirrored across it if it would lie inside.
    for (const g of groups.filter((g) => g.ends.length === 2 && g.ends[0] === k)) {
      const was = angle(old(i), old(path[k + 1])), turn = angle(xy[k], xy[k + 1]) - was;
      move(g.atoms, old(i), xy[k], turn);
      const high = g.atoms.reduce((sum, a) => sum + placed.get(a)![1], 0) / g.atoms.length > xy[k][1];
      if (high !== !!level[k]) move(g.atoms, old(i), xy[k], turn, was);
      // A sugar's base points straight out from it, so the bases stand side by side.
      for (const [c1, base] of bb.bases.filter(([c1]) => g.atoms.includes(c1))) {
        const atoms = new Set(g.atoms);
        atoms.delete(c1);
        grow(base, c1, angle([(xy[k][0] + xy[k + 1][0]) / 2, xy[k][1]], now(c1)), atoms, -1);
      }
    }
  }
  // How close a group comes to the atoms placed before it.
  const crowding = (atoms: number[]) => {
    const mine = new Set(atoms);
    let sum = 0;
    for (const a of atoms) for (const [j, q] of placed) if (Math.abs(now(a)[0] - q[0]) < 1.2 && !mine.has(j)) sum += Math.max(0, 1.2 - Math.hypot(now(a)[0] - q[0], now(a)[1] - q[1])) ** 2;
    return sum;
  };
  for (const [k, i] of path.entries()) {
    const own = groups.filter((g) => g.ends.length === 1 && g.ends[0] === k);
    if (!own.length) continue;
    // The directions free at this atom: the widest gap between the bonds placed at it (the backbone's, and a ring's
    // fused onto it, as at an α-methylproline), or at an end, the next step of the zigzag and then straight out.
    const bonds = [k - 1, k + 1].filter((j) => j >= 0 && j < path.length).map((j) => angle(xy[k], xy[j]));
    let slots: number[];
    if (bonds.length === 1) {
      slots = own.length <= 2 ? [Math.PI - bonds[0], outward(k)] : own.map((_, s) => bonds[0] + Math.PI + (s - (own.length - 1) / 2) * ((2 * Math.PI) / (own.length + 1)));
      // A double-bonded atom (C=O) goes straight out, and the largest other group on along the zigzag.
      const double = (g: (typeof own)[number]) => (g.via.length === 1 && order(g.via[0], i) >= 2 ? 1 : 0);
      if (own.length <= 2) own.sort((p, q) => double(p) - double(q) || q.atoms.length - p.atoms.length);
    } else {
      const taken = at[i].filter((j) => placed.has(j)).map((j) => angle(xy[k], now(j))).sort((p, q) => p - q);
      const [from, gap] = taken.map((t, s) => [t, (taken[s + 1] ?? taken[0] + 2 * Math.PI) - t]).reduce((p, q) => (q[1] > p[1] ? q : p));
      slots = own.map((_, s) => from + gap / 2 + (s - (own.length - 1) / 2) * (Math.PI / 3));
    }
    // The zigzag goes on: the next step turns back the other way from this one.
    const into = angle(xy[k > 0 ? k - 1 : 1], xy[k]);
    own.forEach((g, s) => {
      // A chain whose zigzag would run into a group placed before it (a proline ring) starts the other way.
      const turn = Math.sin(slots[s] - into) > 0 ? -1 : 1, start = (t: number) => { grow(g.via[0], i, slots[s], new Set(g.atoms), t); return crowding(g.atoms); };
      if (g.via.length === 1) return void (start(turn) > start(-turn) || start(turn));
      // Bonded by more than one atom (a spiro ring): moved whole, its middle out.
      const mid: P = [0, 1].map((d) => g.atoms.reduce((sum, a) => sum + old(a)[d], 0) / g.atoms.length) as P;
      move(g.atoms, old(i), xy[k], slots[s] - angle(old(i), mid));
    });
  }
  // A double bond keeps its side (E or Z); a layout that would turn one round is not used.
  for (const b of m.bonds) {
    const [u, v] = b.atoms, nu = at[u].find((j) => j !== v), nv = at[v].find((j) => j !== u);
    if (b.type === 2 && placed.has(u) && nu !== undefined && nv !== undefined && side(old, u, v, nu) * side(old, u, v, nv) * side(now, u, v, nu) * side(now, u, v, nv) < 0) return undefined;
  }
  // Nor is one that puts an atom on another (a side chain on the next residue's N, an N-methyl on a phenyl before it),
  // as the drawing would read as another compound.
  const xs = [...placed.values()].sort((p, q) => p[0] - q[0]);
  for (let k = 0; k < xs.length; k++) for (let j = k + 1; j < xs.length && xs[j][0] - xs[k][0] < 0.3; j++) if (Math.hypot(xs[j][0] - xs[k][0], xs[j][1] - xs[k][1]) < 0.3) return undefined;
  return placed;
}
