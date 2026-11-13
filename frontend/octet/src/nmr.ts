// NMR prediction: ¹H and ¹³C shifts for a structure, looked up by HOSE code (Bremser 1978: an atom's surroundings,
// sphere by sphere) in a table built from nmrshiftdb2's measured spectra (scripts/nmr-table.ts; the table's licence
// is in data/nmr/, decision 0006), with first-order multiplets for ¹H from typical coupling constants.
// The same code makes the codes when the table is built and when a structure is predicted, so lookups always match.
import type { Graph } from "./naming.ts";
import { aromaticAtoms } from "./rings.ts";
import { isMetal } from "./metals.ts";

export type Nucleus = "1H" | "13C" | "19F" | "31P";
// What Octet needs to know about each nucleus it predicts, in one place: its element, its name as written (¹⁹F), its
// frequency as a share of ¹H's (Ξ, IUPAC 2001: the ¹H frequency × ratio is its frequency on the same magnet), the
// decimals a shift is given to, the spread a good shift stays within (ppm), whether it is drawn as a trace with
// integrals (¹H, ¹⁹F) or as sticks (¹³C, ³¹P), the range shown when nothing is outside it, the padding round the
// signals, whether its spectrum is ¹H-decoupled by default (¹³C{¹H} and ³¹P{¹H}, as most labs run them; ¹⁹F
// coupled, as H–F splitting tells the chemist something), and whether its shifts fall back on codes on kinds (codes();
// not ³¹P, which they made worse on held-out spectra, 14.66 to 14.78 ppm).
export type NucleusInfo = { el: string; name: string; ratio: number; decimals: number; tight: number; trace: boolean; range: [number, number]; pad: number; decouple: boolean; kinds: boolean };
export const NUCLEI: Record<Nucleus, NucleusInfo> = {
  "1H": { el: "H", name: "¹H", ratio: 1, decimals: 2, tight: 0.15, trace: true, range: [0, 10], pad: 0.5, decouple: false, kinds: true },
  "13C": { el: "C", name: "¹³C", ratio: 0.25145020, decimals: 1, tight: 1.5, trace: false, range: [0, 200], pad: 10, decouple: true, kinds: true },
  "19F": { el: "F", name: "¹⁹F", ratio: 0.94094011, decimals: 1, tight: 2, trace: true, range: [-200, 0], pad: 5, decouple: false, kinds: true },
  "31P": { el: "P", name: "³¹P", ratio: 0.40480742, decimals: 1, tight: 3, trace: false, range: [-50, 50], pad: 5, decouple: true, kinds: false },
};
export const NUCLEUS_LIST = Object.keys(NUCLEI) as Nucleus[];
export const isNucleus = (x: unknown): x is Nucleus => typeof x === "string" && x in NUCLEI;
// A nucleus's frequency (MHz) on a magnet where ¹H is at `mhz`, as spectrometers round it (101, 376, 162 at 400).
export const frequency = (nucleus: Nucleus, mhz: number) => mhz * NUCLEI[nucleus].ratio;
// A spectrometer's ¹H frequencies (MHz), to tell from a file's observe frequency which nucleus it measured.
const MAGNETS = [43, 60, 80, 90, 100, 200, 250, 270, 300, 360, 400, 500, 600, 700, 750, 800, 850, 900, 950, 1000, 1100, 1200];
// The nucleus an NMR file measured when it does not say: the one whose frequency at a usual magnet is the observe
// frequency (within 0.4%); else, by the width alone, ¹³C for a range over 40 ppm and ¹H otherwise.
export function guessNucleus(first: number, last: number, mhz?: number): Nucleus {
  if (mhz && mhz > 0) {
    let best: Nucleus | undefined, off = 0.004;
    for (const n of NUCLEUS_LIST) {
      const at = mhz / NUCLEI[n].ratio, near = MAGNETS.reduce((b, f) => (Math.abs(f - at) < Math.abs(b - at) ? f : b));
      if (Math.abs(near - at) / near < off) { off = Math.abs(near - at) / near; best = n; }
    }
    if (best) return best;
  }
  return Math.abs(last - first) > 40 ? "13C" : "1H";
}
// One signal: the atoms it belongs to (graph indices; for ¹H, the heavy atoms whose hydrogens these are), its shift
// (ppm), how many nuclei it counts (¹H: hydrogens; ¹³C: carbons), its couplings to neighbouring hydrogens (¹H: each
// coupling constant in Hz with the number of equivalent hydrogens it couples to), whether it is broad (OH, NH), and
// how sure the prediction is (the spread of the shifts it was based on, in ppm, and how many there were).
// group: what the signal comes from, as chemists name it ("CH3", "2 × CH"); level: how many spheres of the atom's
// surroundings matched the table (0, the atom alone, to 6); each coupling also names the groups it couples to (graph indices).
// solvent: the shift comes from spectra measured in the solvent asked for (unset: from spectra in any solvent).
// code: a hash of the atoms' longest code (their class), the same however the structure is drawn or numbered.
// metal: a ¹⁹F or ³¹P atom bonded to a metal, whose shift the table rarely knows (rated rough).
export type Signal = { atoms: number[]; shift: number; nuclei: number; couplings: { j: number; n: number; with?: number[] }[]; broad?: boolean; sd: number; based: number; group?: string; level?: number; solvent?: string; code?: string; metal?: true };
// decoupled: a ¹³C, ¹⁹F or ³¹P spectrum with its ¹H couplings removed (¹³C{¹H}); unset for ¹H.
export type Prediction = { nucleus: Nucleus; signals: Signal[]; decoupled?: boolean };

export const LEVELS = 6; // spheres in the longest code

// --- The molecule as HOSE codes see it ---------------------------------------------------------------------------

// Hydrogens drawn as atoms become counts on the atoms they are bonded to. `from` gives each heavy atom's index in
// the graph it came from. Atoms η-bonded to a metal (hapto) are written one way, however they were drawn: no charge,
// and a carbon has the hydrogens of a ring or alkene carbon beside the metal (CH in a Cp or arene ring), so a Cp ring
// drawn with two double bonds, as its anion, or with a bond to the metal from each atom, gives the same codes.
export function heavy(g: Graph): { g: Graph; from: number[] } {
  const keep = g.atoms.map((a) => a.el !== "H"), to: number[] = [], from: number[] = [];
  g.atoms.forEach((_, i) => { if (keep[i]) { to[i] = from.length; from.push(i); } });
  const atoms = from.map((i) => ({ ...g.atoms[i] }));
  const bonds: Graph["bonds"] = [];
  for (const b of g.bonds) {
    if (keep[b.a] && keep[b.b]) bonds.push({ ...b, a: to[b.a], b: to[b.b] });
    else if (keep[b.a] !== keep[b.b]) atoms[to[keep[b.a] ? b.a : b.b]].h += 1;
  }
  // P⁺–O⁻, P⁺–C⁻ and S⁺–O⁻ are one bond drawn two ways: read as P=O, P=C and S=O, so both give the same codes.
  for (const b of bonds) {
    if (b.order !== 1) continue;
    const [p, q] = atoms[b.a].charge === 1 ? [atoms[b.a], atoms[b.b]] : [atoms[b.b], atoms[b.a]];
    if (p.charge === 1 && q.charge === -1 && ((p.el === "P" && (q.el === "O" || q.el === "C")) || (p.el === "S" && q.el === "O"))) { b.order = 2; p.charge = q.charge = 0; }
  }
  const out = { atoms, bonds }, eta = hapto(out);
  if (eta.some((m) => m >= 0)) atoms.forEach((a, i) => {
    if (eta[i] < 0) return;
    a.charge = 0;
    if (a.el !== "C") return;
    // A carbon beside the metal: four bonds, one of them to the metal, then one to each η neighbour and its other bonds.
    let used = 1;
    for (const b of bonds) if (b.a === i || b.b === i) { const o = b.a === i ? b.b : b.a; if (!metalLike(atoms[o].el)) used += eta[o] === eta[i] ? 1 : b.order; }
    a.h = Math.max(0, 4 - used);
  });
  return { g: out, from };
}

// Atoms that hold η ligands: metals, and "*" (a template's M).
const metalLike = (el: string) => el === "*" || isMetal(el);
// Each atom's metal when it is η-bonded to one (hapto: bonded to the metal and to another atom bonded to it, as a Cp
// or arene ring's atoms or an alkene's are), else -1.
export function hapto(g: Graph): number[] {
  const out = g.atoms.map(() => -1), metalOf = new Map<number, number[]>();
  g.bonds.forEach((b) => {
    for (const [m, x] of [[b.a, b.b], [b.b, b.a]]) if (metalLike(g.atoms[m].el) && !metalLike(g.atoms[x].el) && g.atoms[x].el !== "H") metalOf.set(x, [...(metalOf.get(x) ?? []), m]);
  });
  if (!metalOf.size) return out;
  for (const b of g.bonds) {
    const shared = metalOf.get(b.a)?.find((m) => metalOf.get(b.b)?.includes(m));
    if (shared !== undefined) out[b.a] = out[b.b] = shared;
  }
  return out;
}

type Edge = { to: number; bond: string };
// eta: each atom's metal when it is η-bonded to one (hapto), else -1. kind: each atom's kind (kinds()), once made.
export type Env = { g: Graph; edges: Edge[][]; label: string[]; cls: number[]; aromatic: boolean[]; eta: number[]; kind?: string[] };

// Bonds in no ring (bridges), by Tarjan's method, without recursion.
function bridges(n: number, adj: { to: number; k: number }[][]): Set<number> {
  const order = new Array<number>(n).fill(-1), low = new Array<number>(n).fill(0), out = new Set<number>();
  let t = 0;
  for (let s = 0; s < n; s++) {
    if (order[s] >= 0) continue;
    const stack: { v: number; via: number; i: number }[] = [{ v: s, via: -1, i: 0 }];
    order[s] = low[s] = t++;
    while (stack.length) {
      const top = stack[stack.length - 1];
      if (top.i < adj[top.v].length) {
        const { to, k } = adj[top.v][top.i++];
        if (k === top.via) continue;
        if (order[to] < 0) { order[to] = low[to] = t++; stack.push({ v: to, via: k, i: 0 }); }
        else low[top.v] = Math.min(low[top.v], order[to]);
      } else {
        stack.pop();
        const up = stack[stack.length - 1];
        if (up) { low[up.v] = Math.min(low[up.v], low[top.v]); if (low[top.v] > order[up.v]) out.add(top.via); }
      }
    }
  }
  return out;
}

// Each atom's neighbours with their bond (= double, % triple, * aromatic, ~ between atoms η-bonded to one metal, ^
// from such an atom to its metal, nothing for single), its label (element and charge), and its symmetry class: atoms
// in one class are equivalent in the graph (refined Morgan invariants). An η ring is not aromatic here, whichever
// Kekulé form or charges it was drawn with, so all five atoms of a Cp ring are alike.
export function environment(g: Graph): Env {
  const n = g.atoms.length, adj: { to: number; k: number }[][] = g.atoms.map(() => []);
  g.bonds.forEach((b, k) => { adj[b.a].push({ to: b.b, k }); adj[b.b].push({ to: b.a, k }); });
  const eta = hapto(g), aromatic = aromaticAtoms(g).map((x, i) => x && eta[i] < 0), bridge = bridges(n, adj);
  const sym = (k: number) => {
    const b = g.bonds[k];
    if (eta[b.a] >= 0 && eta[b.a] === eta[b.b]) return "~";
    if (eta[b.a] === b.b || eta[b.b] === b.a) return "^";
    return aromatic[b.a] && aromatic[b.b] && !bridge.has(k) ? "*" : b.order === 2 ? "=" : b.order === 3 ? "%" : "";
  };
  const edges = adj.map((list) => list.map(({ to, k }) => ({ to, bond: sym(k) })));
  const label = g.atoms.map((a) => `${a.el}${a.charge > 0 ? "+" : a.charge < 0 ? "-" : ""}`);
  // Classes: start from what each atom is, then split by what its neighbours are until nothing more splits.
  const rank = (keys: string[]) => { const sorted = [...new Set(keys)].sort(); return keys.map((k) => sorted.indexOf(k)); };
  let cls = rank(g.atoms.map((a, i) => `${label[i]}|${a.h}|${aromatic[i] ? 1 : 0}|${edges[i].length}`)), count = new Set(cls).size;
  for (let round = 0; round < n; round++) {
    const next = rank(cls.map((c, i) => `${c}|${edges[i].map((e) => `${e.bond}${cls[e.to]}`).sort().join(",")}`)), more = new Set(next).size;
    cls = next;
    if (more === count) break;
    count = more;
  }
  return { g, edges, label, cls, aromatic, eta };
}

// An atom's codes, one per level (sphere 1 to `levels`), in the spirit of HOSE codes: the centre's label and
// hydrogens, then each sphere's atoms. Each atom is described by its label, the bonds and descriptions of the atoms
// in the sphere before that reach it, and its bonds to atoms in its own sphere (& where a ring closes). Every list is
// sorted, so the codes are the same whatever order the atoms were drawn in. There is always one code per level.
// label: env.label, or each atom's kind (kinds()) for codes on kinds.
export function hose(env: Env, centre: number, levels = LEVELS, label = env.label): string[] {
  const { edges } = env, dist = new Map([[centre, 0]]), spheres: string[] = [], out: string[] = [];
  const head = `${label[centre]}H${env.g.atoms[centre].h}`;
  let desc = new Map([[centre, head]]);
  for (let level = 1; level <= levels; level++) {
    const reached = new Map<number, string[]>();
    for (const [p, d] of desc) for (const e of edges[p]) {
      const at = dist.get(e.to);
      if (at !== undefined && at !== level) continue;
      dist.set(e.to, level);
      reached.set(e.to, [...(reached.get(e.to) ?? []), `${e.bond}${d}`]);
    }
    // Past the end of the molecule the spheres are empty: "nothing more" is part of the code, so toluene's ipso
    // carbon does not match a para-substituted one.
    const next = new Map<number, string>();
    for (const [v, from] of reached) {
      const ring = edges[v].filter((e) => dist.get(e.to) === level).map((e) => `${e.bond}&`).sort().join("");
      next.set(v, short(`${label[v]}(${from.sort().join(",")})${ring}`));
    }
    spheres.push([...next.values()].sort().join(","));
    out.push(`${head}(${spheres.join("/")})`);
    desc = next;
  }
  return out;
}
// Each atom's kind: its label with its bonds that are not single and what they go to: S=O=O in a sulfonyl, C=O, C%N,
// C*C*N beside the N of a pyridine. Made once per structure, the first time an atom needs codes on kinds.
const kinds = (env: Env) => (env.kind ??= env.label.map((l, i) => `${l}${env.edges[i].filter((e) => e.bond).map((e) => e.bond + env.label[e.to]).sort().join("")}`));
// An atom's codes from the most it tells to the least, each with the spheres it matches. Spheres 1 and 2 also come as
// codes on kinds (k:), after the next sphere by labels and before the same sphere by labels: when the table has no atom
// with the same next sphere, a code on kinds still tells a sulfonyl or carbonyl neighbour from a sulfide or ether one,
// and a ring atom beside a ring N from one that is not. They are made only when asked for, so the many atoms that
// match three spheres or more never make them; a nucleus without kinds (NUCLEI) has none. Level 0 is the atom alone:
// its label, its hydrogens and whether it is η-bonded to a metal (^), so a Cp or arene ring on a metal the table has
// never seen gets the shifts of such rings on other metals. It is the last resort, so every atom gets a shift, rated
// rough when it comes from it.
export function* codes(env: Env, centre: number, nucleus: Nucleus): Generator<[string, number]> {
  const plain = hose(env, centre);
  for (let level = LEVELS; level > 2; level--) yield [plain[level - 1], level];
  const kind = NUCLEI[nucleus].kinds ? hose(env, centre, 2, kinds(env)) : [];
  for (let level = 2; level > 0; level--) {
    if (kind.length) yield [`k:${kind[level - 1]}`, level];
    yield [plain[level - 1], level];
  }
  yield [`${env.label[centre]}H${env.g.atoms[centre].h}${env.eta[centre] >= 0 ? "^" : ""}`, 0];
}
// A description as 8 hex digits, so codes stay short however deep they go.
const short = (s: string) => codeHash("1H", s).toString(16).padStart(8, "0");

// --- The shift table ---------------------------------------------------------------------------------------------

// 32-bit FNV-1a of a nucleus's code at a level.
export function codeHash(nucleus: Nucleus, code: string): number {
  let h = 0x811c9dc5;
  const s = `${nucleus}:${code}`;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h >>> 0;
}

// A table: sorted code hashes, each with the median shift, the spread (standard deviation) and how many measured
// shifts it holds; shifts and spreads are stored × scale (100 for ¹H and ¹³C, 10 for ¹⁹F and ³¹P, whose shifts run
// past ±327 ppm). Version 1 of the file holds the ¹³C table, then the ¹H one: "ONMR", version, the two counts, then
// per table the hashes (u32), shifts (i16, ppm × 100), spreads (u16, ppm × 100) and counts (u16). Version 2 adds the
// solvent tables, ¹³C then ¹H (four counts, four tables): codes measured in one solvent (solventCode) whose shifts
// there differ from the shifts in every solvent. Version 3 names its parts: "ONMR", 3, the number of parts, then for
// each part its nucleus (u8, NUCLEUS_LIST's order), whether it is a solvent table (u8), its scale (u16) and its count
// (u32), then the parts' tables as before.
export type Table = { hash: Uint32Array; shift: Int16Array; sd: Uint16Array; n: Uint16Array; scale?: number };
export type Tables = Partial<Record<Nucleus, Table>> & { solvent?: Partial<Record<Nucleus, Table>> };
const tables: Partial<Record<Nucleus, Table>> = {}, solventTables: Partial<Record<Nucleus, Table>> = {};
const MAX_PARTS = 32;

export function readTables(bytes: Uint8Array) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength), version = bytes.length >= 8 ? view.getUint32(4, true) : 0;
  if (bytes.length < 12 || String.fromCharCode(...bytes.slice(0, 4)) !== "ONMR" || version < 1 || version > 3) throw new Error("Not a shift table");
  // Each part: its nucleus, solvent table or not, scale and count.
  const parts: { nucleus: Nucleus; solvent: boolean; scale: number; count: number }[] = [];
  let head: number;
  if (version === 3) {
    const k = view.getUint32(8, true);
    head = 12 + 8 * k;
    if (k > MAX_PARTS || bytes.length < head) throw new Error("Shift table is cut short");
    for (let i = 0; i < k; i++) {
      const at = 12 + 8 * i, nucleus = NUCLEUS_LIST[bytes[at]], solvent = bytes[at + 1], scale = view.getUint16(at + 2, true);
      if (!nucleus || solvent > 1 || (scale !== 10 && scale !== 100)) throw new Error("Not a shift table");
      parts.push({ nucleus, solvent: solvent === 1, scale, count: view.getUint32(at + 4, true) });
    }
  } else {
    const k = version === 2 ? 4 : 2;
    head = 8 + 4 * k;
    if (bytes.length < head) throw new Error("Shift table is cut short");
    for (let i = 0; i < k; i++) parts.push({ nucleus: i % 2 ? "1H" : "13C", solvent: i >= 2, scale: 100, count: view.getUint32(8 + 4 * i, true) });
  }
  let at = head;
  const read: [Partial<Record<Nucleus, Table>>, Partial<Record<Nucleus, Table>>] = [{}, {}];
  for (const { nucleus, solvent, scale, count } of parts) {
    if (count > (bytes.length - at) / 10) throw new Error("Shift table is cut short");
    const copy = <T>(make: (b: ArrayBuffer) => T, size: number) => { const b = new Uint8Array(bytes.subarray(at, at + count * size)).buffer; at += count * size; return make(b); };
    read[solvent ? 1 : 0][nucleus] = { hash: copy((b) => new Uint32Array(b), 4), shift: copy((b) => new Int16Array(b), 2), sd: copy((b) => new Uint16Array(b), 2), n: copy((b) => new Uint16Array(b), 2), scale };
  }
  for (const n of NUCLEUS_LIST) { delete tables[n]; delete solventTables[n]; }
  Object.assign(tables, read[0]);
  Object.assign(solventTables, read[1]);
}
export function writeTables(t: Tables): Uint8Array {
  const parts = [...NUCLEUS_LIST.flatMap((n) => (t[n] ? [{ n, solvent: 0, table: t[n]! }] : [])), ...NUCLEUS_LIST.flatMap((n) => (t.solvent?.[n] ? [{ n, solvent: 1, table: t.solvent[n]! }] : []))];
  const head = 12 + 8 * parts.length, out = new Uint8Array(head + parts.reduce((s, p) => s + p.table.hash.length * 10, 0)), view = new DataView(out.buffer);
  out.set([..."ONMR"].map((c) => c.charCodeAt(0)));
  view.setUint32(4, 3, true);
  view.setUint32(8, parts.length, true);
  parts.forEach((p, k) => {
    out[12 + 8 * k] = NUCLEUS_LIST.indexOf(p.n);
    out[13 + 8 * k] = p.solvent;
    view.setUint16(14 + 8 * k, p.table.scale ?? 100, true);
    view.setUint32(16 + 8 * k, p.table.hash.length, true);
  });
  let at = head;
  for (const { table: p } of parts) for (const arr of [p.hash, p.shift, p.sd, p.n]) { out.set(new Uint8Array(arr.buffer, arr.byteOffset, arr.byteLength), at); at += arr.byteLength; }
  return out;
}
export const useTables = (t: Tables) => { for (const n of NUCLEUS_LIST) { if (t[n]) tables[n] = t[n]; if (t.solvent?.[n]) solventTables[n] = t.solvent[n]; } };
// A code as measured in one solvent: the solvent's name (as SOLVENTS in spectrumplot.ts lists it) before it.
export const solventCode = (solvent: string, code: string) => `${solvent}|${code}`;

function find(t: Table, h: number) {
  let lo = 0, hi = t.hash.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1, v = t.hash[mid];
    if (v === h) return mid;
    if (v < h) lo = mid + 1; else hi = mid - 1;
  }
  return -1;
}
// An atom's shift: from its most telling code the table has (level 0 at the least), as measured in `solvent` where the
// solvent table has that code; level: the spheres that code matches; code: the hash of its longest code (its class, as
// Signal has it). Undefined when not even the atom alone is there.
export function lookup(env: Env, nucleus: Nucleus, atom: number, solvent?: string): { shift: number; sd: number; based: number; level: number; solvent?: string; code: string } | undefined {
  const t = tables[nucleus], st = solvent ? solventTables[nucleus] : undefined;
  if (!t) return undefined;
  let longest: string | undefined;
  for (const [code, level] of codes(env, atom, nucleus)) {
    const h = codeHash(nucleus, code), i = find(t, h);
    longest ??= h.toString(36);
    if (i < 0) continue;
    const j = st ? find(st, codeHash(nucleus, solventCode(solvent!, code))) : -1;
    if (j >= 0) { const k = st!.scale ?? 100; return { shift: st!.shift[j] / k, sd: st!.sd[j] / k, based: st!.n[j], level, solvent, code: longest }; }
    const k = t.scale ?? 100;
    return { shift: t.shift[i] / k, sd: t.sd[i] / k, based: t.n[i], level, code: longest };
  }
  return undefined;
}

// Loads the shift tables (once, on first use), gzipped next to the app.
let loading: Promise<void> | undefined;
export function nmrReady(): Promise<void> {
  loading ??= (async () => {
    const raw = new Uint8Array(await (await fetch(new URL("../data/nmr/shifts.bin.gz", import.meta.url))).arrayBuffer());
    // A server may have unzipped it already.
    const zipped = raw[0] === 0x1f && raw[1] === 0x8b;
    readTables(zipped ? new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer()) : raw);
  })().catch((e) => { loading = undefined; throw e; });
  return loading;
}

// --- Prediction --------------------------------------------------------------------------------------------------

// Typical ¹H–¹H couplings (Hz) between hydrogens on neighbouring atoms: aromatic ortho, vinylic (cis and trans
// averaged; Octet's graph has no geometry), next to an aldehyde, and otherwise vicinal sp³. Meta coupling on a ring
// is 2 Hz. Round a ring η-bonded to a metal: 2.5 Hz in a Cp ring, 6.5 Hz in an arene's. Hydrogens on O, N and S
// exchange and do not couple.
function vicinal(env: Env, a: number, b: number): number {
  const e = env.edges[a].find((x) => x.to === b)!;
  if (e.bond === "~") {
    const ring = new Set([a]);
    for (const i of ring) for (const x of env.edges[i]) if (x.bond === "~") ring.add(x.to);
    return ring.size === 5 ? 2.5 : 6.5;
  }
  if (e.bond === "*") return 8;
  if (e.bond === "=") return 12;
  const sp2 = (i: number) => env.edges[i].some((x) => x.bond === "=" || x.bond === "*");
  const aldehyde = (i: number) => env.edges[i].some((x) => x.bond === "=" && env.label[x.to] === "O");
  if (aldehyde(a) || aldehyde(b)) return 2.5;
  return sp2(a) || sp2(b) ? 7.5 : 7;
}

// --- Couplings to ¹⁹F and ³¹P ---------------------------------------------------------------------------------
// Typical coupling constants (Hz, magnitudes) by the bonds between the two nuclei and what lies on that path. The
// values are the usual ones of the literature: H–F and F–F from Dolbier, Guide to Fluorine NMR for Organic Chemists
// (2nd ed., Wiley 2016); C–F, C–P and P–H from Berger, Braun and Kalinowski, NMR Spectroscopy of the Non-Metallic
// Elements (Wiley 1997); checked against Pretsch, Bühlmann and Badertscher, Structure Determination of Organic
// Compounds (4th ed., Springer 2009). Each is the typical value for its kind of path; a real molecule can differ by a
// few Hz. Octet's graph has no geometry, so cis and trans across a double bond are averaged, as for ¹H–¹H.

// Bonds from one atom to every atom up to `most` bonds away (−1 past that); with `ring`, only along aromatic bonds.
function distances(env: Env, from: number, most: number, ring = false): Int8Array {
  const d = new Int8Array(env.g.atoms.length).fill(-1);
  d[from] = 0;
  let edge = [from];
  for (let k = 1; k <= most && edge.length; k++) {
    const next: number[] = [];
    for (const v of edge) for (const e of env.edges[v]) if (d[e.to] < 0 && (!ring || e.bond === "*")) { d[e.to] = k; next.push(e.to); }
    edge = next;
  }
  return d;
}
// What kind of phosphorus an atom is, as its couplings go: a phosphine (PR₃), phosphine oxide or sulfide (R₃P=O),
// phosphonium (R₄P⁺, or an ylide R₃P=C), phosphonate or phosphinate (P=O with one or two OR), phosphate ((RO)₃P=O),
// phosphite (P(OR)₃).
type PKind = "phosphine" | "oxide" | "phosphonium" | "phosphonate" | "phosphate" | "phosphite";
function pKind(env: Env, p: number): PKind {
  const g = env.g, by = (el: string, bond: string) => env.edges[p].filter((e) => g.atoms[e.to].el === el && e.bond === bond).length;
  if (g.atoms[p].charge > 0 || by("C", "=")) return "phosphonium";
  const ors = by("O", "");
  if (by("O", "=") || by("S", "=") || by("Se", "=")) return ors >= 3 ? "phosphate" : ors >= 1 ? "phosphonate" : "oxide";
  return ors ? "phosphite" : "phosphine";
}
type Spins = { env: Env; dist: (a: number) => Int8Array; ring: (a: number) => Int8Array; kinds: Map<number, PKind> };
function spins(env: Env): Spins {
  const near = new Map<number, Int8Array>(), around = new Map<number, Int8Array>(), kinds = new Map<number, PKind>();
  env.g.atoms.forEach((a, i) => { if (a.el === "P") kinds.set(i, pKind(env, i)); });
  return {
    env, kinds,
    dist: (a) => { let d = near.get(a); if (!d) near.set(a, (d = distances(env, a, 5))); return d; },
    ring: (a) => { let d = around.get(a); if (!d) around.set(a, (d = distances(env, a, 4, true))); return d; },
  };
}
const fluorines = (env: Env, c: number) => env.edges[c].filter((e) => env.g.atoms[e.to].el === "F").length;
const hasDouble = (env: Env, c: number, el?: string) => env.edges[c].some((e) => e.bond === "=" && (!el || env.g.atoms[e.to].el === el));
// The atom next to `to` on a shortest path from `from` (d bonds long).
const nextTo = (s: Spins, from: number, to: number, d: number) => s.env.edges[to].map((e) => e.to).find((m) => s.dist(from)[m] === d - 1);

// ⁿJ(H,F): hydrogens on heavy atom x, F atom f.
function jHF(s: Spins, x: number, f: number): number {
  const { env } = s, r = env.edges[f][0]?.to, d = s.dist(x)[f];
  if (r === undefined || env.g.atoms[r].el !== "C" || d < 1) return 0;
  if (d === 1) return hasDouble(env, x) ? 80 : fluorines(env, x) >= 2 ? 56 : 47; // H–C–F
  if (d === 2) {
    const bond = env.edges[x].find((e) => e.to === r)?.bond;
    if (bond === undefined) return 0;
    if (bond === "*") return 9; // aromatic ortho
    if (bond === "=") return 35; // H–C=C–F, cis and trans averaged
    return [0, 24, 16, 9][fluorines(env, r)] ?? 9; // H–C–C–F, by the F on that carbon
  }
  if (d === 3 && env.aromatic[x] && env.aromatic[r] && s.ring(x)[r] === 2) return 5.5; // aromatic meta
  return 0;
}
// ⁿJ(C,F): carbon c, F atom f.
function jCF(s: Spins, c: number, f: number): number {
  const { env } = s, r = env.edges[f][0]?.to, d = s.dist(c)[f], g = env.g;
  if (r === undefined || g.atoms[r].el !== "C" || d < 1) return 0;
  const nf = fluorines(env, r), aryl = env.aromatic[r];
  if (d === 1) {
    if (aryl) return 245;
    if (hasDouble(env, r)) return hasDouble(env, r, "O") ? 360 : 260;
    if (nf === 1) return 165;
    if (nf === 2) return 240;
    const on = env.edges[r].find((e) => g.atoms[e.to].el !== "F")?.to;
    return on === undefined ? 260 : env.aromatic[on] ? 272 : g.atoms[on].el === "S" ? 320 : hasDouble(env, on, "O") ? 284 : 278;
  }
  if (d === 2) {
    if (aryl) return env.aromatic[c] ? 21 : 0;
    if (nf === 3) return env.aromatic[c] ? 32 : hasDouble(env, c, "O") ? 42 : 34;
    return nf === 2 ? 24 : 20;
  }
  if (d === 3) {
    if (aryl) return env.aromatic[c] && s.ring(r)[c] === 2 ? 8 : 0;
    if (nf === 3) return env.aromatic[c] ? 3.8 : 3;
    return nf === 2 ? 5 : 6;
  }
  if (d === 4 && aryl && env.aromatic[c] && s.ring(r)[c] === 3) return 3.2; // para
  return 0;
}
// ⁿJ(C,P): carbon c, phosphorus p.
function jCP(s: Spins, c: number, p: number): number {
  const { env } = s, d = s.dist(c)[p], kind = s.kinds.get(p)!, aryl = env.aromatic[c];
  if (d === 1) return { phosphine: aryl ? 11 : 14, oxide: aryl ? 104 : 72, phosphonium: aryl ? 89 : 55, phosphonate: aryl ? 188 : 142, phosphate: 142, phosphite: 142 }[kind];
  if (d !== 2 && d !== 3 && d !== 4) return 0;
  const m = nextTo(s, c, p, d), viaO = m !== undefined && env.g.atoms[m].el === "O";
  if (d === 2) {
    if (viaO) return kind === "phosphite" ? 10 : kind === "phosphate" ? 6 : 6.5; // P–O–C
    if (aryl && m !== undefined && env.aromatic[m]) return kind === "phosphine" ? 20 : 10; // ortho
    return kind === "phosphine" ? 12 : kind === "phosphonate" ? 5 : 4;
  }
  if (d === 3) {
    if (viaO) return kind === "phosphite" ? 5 : kind === "phosphate" ? 7 : 6; // P–O–C–C
    if (aryl && m !== undefined && env.aromatic[m]) return { phosphine: 7, oxide: 12, phosphonium: 13, phosphonate: 15, phosphate: 0, phosphite: 0 }[kind]; // meta
    return kind === "phosphine" ? 10 : 15;
  }
  return aryl && m !== undefined && env.aromatic[m] && kind !== "phosphine" ? 3 : 0; // para
}
// ⁿJ(H,P): hydrogens on heavy atom x (x = p for hydrogens on the phosphorus), phosphorus p.
function jHP(s: Spins, x: number, p: number): number {
  const { env } = s, d = s.dist(x)[p], kind = s.kinds.get(p)!;
  if (d === 0) {
    if (kind === "phosphonium") return 500;
    if (kind === "phosphine" || kind === "phosphite") return 200;
    return [470, 560, 690][Math.min(2, env.edges[p].filter((e) => env.g.atoms[e.to].el === "O" && e.bond === "").length)];
  }
  if (d === 1) return { phosphine: 3, oxide: 13, phosphonium: 14, phosphonate: 17, phosphate: 0, phosphite: 0 }[kind]; // H–C–P
  const m = nextTo(s, x, p, d);
  if (m === undefined) return 0;
  if (d === 2) {
    if (env.g.atoms[m].el === "O") return kind === "phosphite" ? 10 : 8; // H–C–O–P
    if (env.aromatic[x] && env.aromatic[m]) return { phosphine: 7, oxide: 12, phosphonium: 13, phosphonate: 13, phosphate: 0, phosphite: 0 }[kind]; // ortho
    return { phosphine: 14, oxide: 17, phosphonium: 18, phosphonate: 20, phosphate: 0, phosphite: 0 }[kind]; // H–C–C–P
  }
  if (d === 3 && env.aromatic[x] && env.aromatic[m] && kind !== "phosphine") return 3; // meta
  return 0;
}
// ¹J(P,F): only F on the phosphorus (PF₆⁻, a P–F bond).
function jPF(s: Spins, p: number, f: number): number {
  const { env } = s;
  if (s.dist(p)[f] !== 1) return 0;
  return env.edges[p].length >= 6 ? 710 : hasDouble(env, p) ? 1000 : 1200;
}
// ⁿJ(F,F) between F atoms on an aromatic ring: ortho, meta and para.
function jFF(s: Spins, a: number, b: number): number {
  const { env } = s, ra = env.edges[a][0]?.to, rb = env.edges[b][0]?.to;
  if (ra === undefined || rb === undefined || ra === rb || !env.aromatic[ra] || !env.aromatic[rb]) return 0;
  return [0, 20, 3, 13][s.ring(ra)[rb]] ?? 0;
}

// Solvents that exchange their deuterium with OH, NH and SH hydrogens, so those hydrogens give no ¹H peak.
const EXCHANGING = ["D₂O", "CD₃OD"];
// Couplings smaller than this (Hz) are left out: they broaden a line rather than split it.
const SMALLEST = 1.5;
// The predicted spectrum, or undefined before the tables are loaded or when no atom is covered. solvent: shifts
// measured in it are used where the table has them (ChemDraw has CDCl₃ and DMSO only). decouple: remove the ¹H
// couplings of a ¹³C, ¹⁹F or ³¹P spectrum (NUCLEI's default when unset); ¹³C is always ¹H-decoupled.
export function predict(drawn: Graph, nucleus: Nucleus, solvent?: string, decouple?: boolean): Prediction | undefined {
  if (!tables[nucleus]) return undefined;
  const { g, from } = heavy(drawn), env = environment(g), done = new Set<number>(), signals: Signal[] = [];
  const exchange = (i: number) => ["O", "N", "S"].includes(g.atoms[i].el), gone = nucleus === "1H" && !!solvent && EXCHANGING.includes(solvent);
  const el = NUCLEI[nucleus].el, decoupled = nucleus === "1H" ? undefined : nucleus === "13C" || (decouple ?? NUCLEI[nucleus].decouple);
  const centres = g.atoms.map((_, i) => i).filter((i) => (nucleus === "1H" ? g.atoms[i].h > 0 && !(gone && exchange(i)) : g.atoms[i].el === el));
  // The molecule's F and P atoms, and their couplings' paths: none at all for most molecules, so they cost nothing.
  const fs = g.atoms.map((_, i) => i).filter((i) => g.atoms[i].el === "F"), ps = g.atoms.map((_, i) => i).filter((i) => g.atoms[i].el === "P");
  const sp = fs.length || ps.length ? spins(env) : undefined;
  const coupled = (x: number) => g.atoms[x].h > 0 && !exchange(x);
  for (const c of centres) {
    if (done.has(env.cls[c])) continue;
    done.add(env.cls[c]);
    const found = lookup(env, nucleus, c, solvent);
    if (!found) continue;
    const members = centres.filter((i) => env.cls[i] === env.cls[c]);
    const nuclei = nucleus === "1H" ? members.reduce((s, i) => s + g.atoms[i].h, 0) : members.length;
    // Couplings: each J with the number of equivalent nuclei it couples to (one entry for J values within 0.6 Hz),
    // none to equivalent nuclei. ¹H: to the hydrogens on each neighbouring heavy atom (vicinal) and meta on aromatic
    // rings, none across O, N and S; then to F and P.
    const couplings: Signal["couplings"] = [];
    const add = (j: number, n: number, to: number) => {
      if (j < SMALLEST) return;
      const same = couplings.find((x) => Math.abs(x.j - j) < 0.6);
      if (same) { same.n += n; same.with!.push(from[to]); } else couplings.push({ j, n, with: [from[to]] });
    };
    const other = (i: number) => env.cls[i] !== env.cls[c];
    if (nucleus === "1H" && !exchange(c)) {
      for (const e of env.edges[c]) if (g.atoms[e.to].h && !exchange(e.to) && other(e.to)) add(vicinal(env, c, e.to), g.atoms[e.to].h, e.to);
      if (env.aromatic[c]) {
        const meta = new Set<number>();
        for (const e of env.edges[c]) if (e.bond === "*") for (const f of env.edges[e.to]) if (f.bond === "*" && f.to !== c && env.edges[c].every((x) => x.to !== f.to)) meta.add(f.to);
        for (const m of meta) if (g.atoms[m].h && other(m)) add(2, g.atoms[m].h, m);
      }
      if (sp) { for (const f of fs) add(jHF(sp, c, f), 1, f); for (const p of ps) add(jHP(sp, c, p), 1, p); }
    } else if (nucleus === "13C" && sp) {
      for (const f of fs) add(jCF(sp, c, f), 1, f);
      for (const p of ps) add(jCP(sp, c, p), 1, p);
    } else if (nucleus === "19F" && sp) {
      if (!decoupled) g.atoms.forEach((_, x) => { if (coupled(x)) add(jHF(sp, x, c), g.atoms[x].h, x); });
      for (const f of fs) if (other(f)) add(jFF(sp, c, f), 1, f);
      for (const p of ps) add(jPF(sp, p, c), 1, p);
    } else if (nucleus === "31P" && sp) {
      if (!decoupled) g.atoms.forEach((_, x) => { if (coupled(x)) add(jHP(sp, x, c), g.atoms[x].h, x); });
      for (const f of fs) add(jPF(sp, c, f), 1, f);
    }
    signals.push({
      atoms: members.map((i) => from[i]), shift: found.shift, nuclei, couplings: couplings.sort((a, b) => b.j - a.j),
      ...(nucleus === "1H" && exchange(c) ? { broad: true } : {}), sd: found.sd, based: found.based, level: found.level, ...(found.solvent ? { solvent: found.solvent } : {}),
      group: groupName(env, c, members, nucleus),
      code: found.code,
      ...((nucleus === "19F" || nucleus === "31P") && env.edges[c].some((e) => metalLike(g.atoms[e.to].el)) ? { metal: true as const } : {}),
    });
  }
  return signals.length ? { nucleus, signals: signals.sort((a, b) => b.shift - a.shift), ...(decoupled !== undefined ? { decoupled } : {}) } : undefined;
}
// What a signal comes from, as chemists name it: "CH3", "2 × CH"; for ¹⁹F the group the fluorines are on ("CF3",
// "CH2F", "ArF" on an aromatic ring, "PF6").
function groupName(env: Env, c: number, members: number[], nucleus: Nucleus): string {
  const g = env.g, h = (i: number) => (g.atoms[i].h ? `H${g.atoms[i].h > 1 ? g.atoms[i].h : ""}` : "");
  if (nucleus === "19F") {
    const on = [...new Set(members.map((i) => env.edges[i][0]?.to).filter((i) => i !== undefined))];
    if (on.length) {
      const r = on[0], nf = fluorines(env, r), name = env.aromatic[r] ? `ArF${nf > 1 ? nf : ""}` : `${g.atoms[r].el}${h(r)}F${nf > 1 ? nf : ""}`;
      return `${on.length > 1 ? `${on.length} × ` : ""}${name}`;
    }
  }
  return `${members.length > 1 ? `${members.length} × ` : ""}${g.atoms[c].el}${h(c)}`;
}

// How far to trust a shift, as ChemDraw rates its estimates. Good: four or more spheres of the atom's surroundings
// matched, the measured shifts agree (spread up to NUCLEI's tight value: 0.15 ppm for ¹H, 1.5 for ¹³C, 2 for ¹⁹F, 3 for
// ³¹P), and there were two or more of them (one is enough when all six spheres matched). Rough: two spheres or fewer
// matched, the shifts spread more than twice that, a ¹⁹F or ³¹P atom on a metal, or a hydrogen on O, N or S (broad),
// whose shift moves with the solvent and the concentration (ChemDraw rates shifts that depend on the solvent rough;
// on held-out spectra those rated good were 0.5 ppm out). Medium otherwise.
export function quality(s: Signal, nucleus: Nucleus): "good" | "medium" | "rough" {
  const level = s.level ?? 0, tight = NUCLEI[nucleus].tight;
  if (level <= 2 || s.sd > 2 * tight || s.metal || s.broad) return "rough";
  return level >= 4 && s.sd <= tight && (s.based >= 2 || level === 6) ? "good" : "medium";
}
// A shift as text: NUCLEI's decimals, with a true minus sign (U+2212) for print; plain: a hyphen-minus, for a
// spreadsheet.
export const shiftText = (v: number, nucleus: Nucleus, plain = false) => { const t = v.toFixed(NUCLEI[nucleus].decimals); return plain ? t : t.replace("-", "−"); };
// The nuclei a signal counts, as a journal writes them: 2H, 3F, 2C, 1P.
export const countText = (s: Signal, nucleus: Nucleus) => `${s.nuclei}${NUCLEI[nucleus].el}`;
// The details as a table (tab-separated, for a spreadsheet): one row per signal. Multiplicity and J only for a trace
// nucleus, or for sticks that are split (¹³C by F or P, ³¹P by F).
export function detailsTable(p: Prediction): string {
  const n = p.nucleus, split = NUCLEI[n].trace || p.signals.some((s) => s.couplings.length);
  const head = ["Group", "δ (ppm)", ...(split ? ["Multiplicity", "J (Hz)"] : []), NUCLEI[n].trace ? "Integral" : { "13C": "Carbons", "31P": "Phosphorus atoms", "1H": "", "19F": "" }[n], "Spheres matched", "Measured shifts", "Measured in", "Spread (ppm)", "Quality"];
  const rows = [...p.signals].sort((a, b) => b.shift - a.shift).map((s) => [
    s.group ?? "", shiftText(s.shift, n, true), ...(split ? [multiplicity(s), s.couplings.map((c) => c.j.toFixed(1)).join(", ")] : []),
    NUCLEI[n].trace ? countText(s, n) : String(s.nuclei), String(s.level ?? ""), String(s.based), s.solvent ?? "any solvent", s.sd.toFixed(NUCLEI[n].decimals), quality(s, n),
  ]);
  return [head, ...rows].map((r) => r.join("\t")).join("\n");
}

// --- Text --------------------------------------------------------------------------------------------------------

// A signal's multiplicity as chemists write it: s, d, t, q, quint, sext, sept, dd, dt, td, ddd and so on, m when it
// has more than three kinds of coupling, br s for a broad one.
export function multiplicity(s: Signal): string {
  if (s.broad) return "br s";
  const name = ["s", "d", "t", "q", "quint", "sext", "sept"], c = [...s.couplings].sort((a, b) => b.j - a.j);
  if (c.length <= 1) return c.length && c[0].n > 6 ? "m" : name[c[0]?.n ?? 0];
  // Several couplings: each one's pattern, the largest J first (dd, dt, td, ddd); m past three or for big ones.
  return c.length > 3 || c.some((x) => x.n > 3) ? "m" : c.map((x) => name[x.n]).join("");
}

// A spectrum's title as a journal writes it: "¹H NMR (400 MHz, CDCl₃)", "³¹P{¹H} NMR (162 MHz, CDCl₃)". ¹³C keeps
// its plain title. mhz: the ¹H frequency; the nucleus's own is shown, rounded.
export function acsTitle(p: { nucleus: Nucleus; decoupled?: boolean }, mhz: number, solvent: string): string {
  const n = p.nucleus, braces = p.decoupled && n !== "13C" ? "{¹H}" : "";
  return `${NUCLEI[n].name}${braces} NMR (${Math.round(frequency(n, mhz))} MHz, ${solvent})`;
}
// The prediction as a journal's characterisation line (ACS style): "¹H NMR (400 MHz, CDCl₃) δ 7.26 (d, J = 8.0 Hz,
// 2H), …" with shifts from high to low. ¹³C and ³¹P list the shifts alone, with the multiplicity and J of a split
// one ("162.9 (d, J = 245.0 Hz)"); ¹⁹F gives each signal's multiplicity and count, as ¹H does.
export function acsText(p: Prediction, mhz: number, solvent: string): string {
  const n = p.nucleus, signals = [...p.signals].sort((a, b) => b.shift - a.shift);
  const js = (s: Signal) => `J = ${[...s.couplings].sort((a, b) => b.j - a.j).map((c) => c.j.toFixed(1)).join(", ")} Hz`;
  const one = (s: Signal) => {
    const m = multiplicity(s), j = s.couplings.length && m !== "m" && !s.broad ? `, ${js(s)}` : "";
    if (!NUCLEI[n].trace) return s.couplings.length ? `${shiftText(s.shift, n)} (${m}${j})` : shiftText(s.shift, n);
    return `${shiftText(s.shift, n)} (${m}${j}, ${countText(s, n)})`;
  };
  return `${acsTitle(p, mhz, solvent)} δ ${signals.map(one).join(", ")}.`;
}
