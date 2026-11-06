// Builds data/nmr/shifts.bin.gz, Octet's NMR shift table, from nmrshiftdb2's SD file of assigned spectra
// (nmrshiftdb2withsignals.sd, which is not in this repository). Only measured spectra go in: the spectra the file
// marks as predicted (in its Program and NMRProgram fields) are left out. Spectra whose solvent the file names (one
// of the Spectrum panel's) also go in that solvent's table, where their shifts differ from the shifts in every solvent.
// Run: node scripts/nmr-table.ts <nmrshiftdb2withsignals.sd> [--test]
// --test builds the table from nine molecules in ten and reports how well it predicts the tenth; nothing is written.
import { createReadStream, mkdirSync, writeFileSync } from "node:fs";
import { createInterface } from "node:readline";
import { gzipSync } from "node:zlib";
import { hydrogens } from "../src/render.ts";
import type { Graph } from "../src/naming.ts";
import { codeHash, environment, heavy, hose, lookup, solventCode, useTables, writeTables, type Nucleus, type Table } from "../src/nmr.ts";

const [file, flag] = process.argv.slice(2), test = flag === "--test";
if (!file) throw new Error("Usage: node scripts/nmr-table.ts <nmrshiftdb2withsignals.sd> [--test]");

type Peak = { shift: number; atom: number };
type Molecule = { id: number; graph: Graph; spectra: { nucleus: Nucleus; peaks: Peak[]; solvent?: string }[] };
// nmrshiftdb2's names for the Spectrum panel's solvents (spectrumplot.ts).
const SOLVENT: Record<string, string> = {
  "Chloroform-D1 (CDCl3)": "CDCl₃", "CDCL3,TMS": "CDCl₃", "Dimethylsulphoxide-D6 (DMSO-D6, C2D6SO)": "DMSO-d₆", "DMSO": "DMSO-d₆", "(CD3)2SO": "DMSO-d₆",
  "Methanol-D4 (CD3OD)": "CD₃OD", "Deuteriumoxide (D2O)": "D₂O", "Benzene-D6 (C6D6)": "C₆D₆", "Acetone-D6 ((CD3)2CO)": "Acetone-d₆", "Acetonitrile-D3 (CD3CN)": "CD₃CN",
};
// A solvent's codes go in its table when it has at least two shifts for them, and their median there differs from
// the median in every solvent by at least this much (ppm). The difference is shrunk towards the median in every
// solvent as n / (n + 3) for n shifts in the solvent, so a few shifts move a prediction only a little. ¹H has no
// solvent table: on the held-out tenth (18 October 2026) it made ¹H shifts in a known solvent worse (MAE 0.238 to
// 0.240 ppm, 1,730 shifts; on O, N and S 1.23 to 1.27 ppm, 67 shifts), and ¹³C better (2.118 to 2.078 ppm, 6,147).
const SOLVENT_DIFF: Record<Nucleus, number> = { "13C": 0.5, "1H": Infinity }, SHRINK = 3;
const CHARGE: Record<number, number> = { 1: 3, 2: 2, 3: 1, 5: -1, 6: -2, 7: -3 };

// One SD record: the molfile (V2000) as a graph with hydrogen counts, and its measured ¹H and ¹³C spectra.
function read(lines: string[]): Molecule | undefined {
  const na = Number(lines[3]?.slice(0, 3)), nb = Number(lines[3]?.slice(3, 6));
  if (!(na > 0) || !(nb >= 0) || lines.length < 4 + na + nb) return undefined;
  const atoms = lines.slice(4, 4 + na).map((l) => ({ el: l.slice(31, 34).trim(), charge: CHARGE[Number(l.slice(36, 39))] ?? 0, h: 0 }));
  const bonds: Graph["bonds"] = [];
  for (const l of lines.slice(4 + na, 4 + na + nb)) {
    const a = Number(l.slice(0, 3)) - 1, b = Number(l.slice(3, 6)) - 1, type = Number(l.slice(6, 9));
    if (!(type >= 1 && type <= 3) && type !== 6) return undefined;
    bonds.push({ a, b, order: (type === 6 ? 1 : type) as 1 | 2 | 3 });
  }
  const fields = new Map<string, string>();
  let name: string | undefined;
  for (const l of lines.slice(4 + na + nb)) {
    if (l.startsWith("M  CHG")) for (let k = 0, n = Number(l.slice(6, 9)); k < n; k++) atoms[Number(l.slice(10 + 8 * k, 13 + 8 * k)) - 1].charge = Number(l.slice(14 + 8 * k, 17 + 8 * k));
    const m = /^> *<(.+)>/.exec(l);
    if (m) { name = m[1]; fields.set(name, ""); continue; }
    if (name && l.trim()) fields.set(name, fields.get(name)! + l.trim());
  }
  const used = atoms.map(() => 0);
  for (const b of bonds) { used[b.a] += b.order; used[b.b] += b.order; }
  atoms.forEach((a, i) => { a.h = hydrogens(a.el, a.charge, used[i]); });
  // Spectra a program predicted, by their number ("1:ACD/Labs … 2:HOSE code …").
  const predicted = new Set<string>();
  for (const key of ["Program", "NMRProgram"]) for (const m of (fields.get(key) ?? "").matchAll(/(\d+):(\S[^:]*?)(?=\s+\d+:|$)/g)) predicted.add(m[1]);
  // Each spectrum's solvent, by its number ("0:Chloroform-D1 (CDCl3) 1:Unreported").
  const solvents = new Map<string, string>();
  for (const m of (fields.get("Solvent") ?? "").matchAll(/(\d+):(\S[^:]*?)(?=\s+\d+:|$)/g)) if (SOLVENT[m[2].trim()]) solvents.set(m[1], SOLVENT[m[2].trim()]);
  const spectra: Molecule["spectra"] = [];
  for (const [key, value] of fields) {
    const m = /^Spectrum (1H|13C) (\d+)$/.exec(key);
    if (!m || predicted.has(m[2])) continue;
    const peaks = value.split("|").filter(Boolean).map((p) => { const [s, , at] = p.split(";"); return { shift: Number(s), atom: Number(at) }; })
      .filter((p) => Number.isFinite(p.shift) && Number.isInteger(p.atom) && p.atom >= 0 && p.atom < na);
    if (peaks.length) spectra.push({ nucleus: m[1] as Nucleus, peaks, solvent: solvents.get(m[2]) });
  }
  return { id: Number(fields.get("nmrshiftdb2 ID")), graph: { atoms, bonds }, spectra };
}

// Each molecule's measured shifts as (heavy atom, shift) pairs on its heavy-atom graph: ¹³C on carbons; ¹H on the
// atom carrying the hydrogen, averaged within a spectrum.
function observations(mol: Molecule) {
  const { g, from } = heavy(mol.graph), to = new Map(from.map((old, k) => [old, k])), out: { nucleus: Nucleus; atom: number; shift: number; solvent?: string }[] = [];
  const carrier = (i: number) => (mol.graph.atoms[i].el === "H" ? mol.graph.bonds.find((b) => b.a === i || b.b === i) : undefined);
  for (const s of mol.spectra) {
    const byAtom = new Map<number, number[]>();
    for (const p of s.peaks) {
      let at = p.atom;
      if (mol.graph.atoms[at].el === "H") { if (s.nucleus === "13C") continue; const b = carrier(at); if (!b) continue; at = b.a === at ? b.b : b.a; }
      const k = to.get(at);
      if (k === undefined || (s.nucleus === "13C" ? g.atoms[k].el !== "C" : g.atoms[k].h === 0)) continue;
      byAtom.set(k, [...(byAtom.get(k) ?? []), p.shift]);
    }
    for (const [atom, shifts] of byAtom) out.push({ nucleus: s.nucleus, atom, shift: shifts.reduce((a, b) => a + b, 0) / shifts.length, solvent: s.solvent });
  }
  return { g, out };
}

const molecules: Molecule[] = [];
let record: string[] = [];
for await (const line of createInterface({ input: createReadStream(file, { encoding: "utf8" }), crlfDelay: Infinity })) {
  if (line.startsWith("$$$$")) { const m = read(record); if (m?.spectra.length) molecules.push(m); record = []; } else record.push(line);
}
console.log(`${molecules.length} molecules with measured spectra`);

// The table: every level of every observed atom's code, with the shifts seen there; and in its solvent's table too,
// with the hash of the code in every solvent.
const seen: Record<Nucleus, Map<number, number[]>> = { "13C": new Map(), "1H": new Map() };
const seenIn: Record<Nucleus, Map<number, { all: number; shifts: number[] }>> = { "13C": new Map(), "1H": new Map() };
const held: { mol: Molecule; g: Graph; out: ReturnType<typeof observations>["out"] }[] = [];
for (const mol of molecules) {
  const { g, out } = observations(mol);
  if (!out.length) continue;
  if (test && mol.id % 10 === 0) { held.push({ mol, g, out }); continue; }
  let env;
  try { env = environment(g); } catch { continue; }
  for (const o of out) for (const code of hose(env, o.atom)) {
    const h = codeHash(o.nucleus, code), list = seen[o.nucleus].get(h);
    if (list) list.push(o.shift); else seen[o.nucleus].set(h, [o.shift]);
    if (!o.solvent) continue;
    const hs = codeHash(o.nucleus, solventCode(o.solvent, code)), there = seenIn[o.nucleus].get(hs);
    if (there) there.shifts.push(o.shift); else seenIn[o.nucleus].set(hs, { all: h, shifts: [o.shift] });
  }
}
const table = (m: Map<number, number[]>): Table => {
  const keys = [...m.keys()].sort((a, b) => a - b), t = { hash: new Uint32Array(keys), shift: new Int16Array(keys.length), sd: new Uint16Array(keys.length), n: new Uint16Array(keys.length) };
  keys.forEach((k, i) => {
    const v = m.get(k)!.sort((a, b) => a - b), mid = v.length >> 1, median = v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
    const mean = v.reduce((a, b) => a + b, 0) / v.length, sd = Math.sqrt(v.reduce((a, b) => a + (b - mean) ** 2, 0) / v.length);
    t.shift[i] = Math.round(Math.max(-327, Math.min(327, median)) * 100);
    t.sd[i] = Math.round(Math.min(655, sd) * 100);
    t.n[i] = Math.min(65535, v.length);
  });
  return t;
};
const median = (v: number[]) => { const w = [...v].sort((a, b) => a - b), mid = w.length >> 1; return w.length % 2 ? w[mid] : (w[mid - 1] + w[mid]) / 2; };
// A solvent's codes that have enough shifts there, and whose shifts there differ from those in every solvent.
const differing = (nucleus: Nucleus) => new Map([...seenIn[nucleus]].flatMap(([h, x]): [number, number[]][] => {
  const all = median(seen[nucleus].get(x.all)!), d = median(x.shifts) - all;
  if (x.shifts.length < 2 || Math.abs(d) < SOLVENT_DIFF[nucleus]) return [];
  // The shrunk shift, as many times as there were shifts (table() keeps their median and count).
  return [[h, x.shifts.map(() => all + (d * x.shifts.length) / (x.shifts.length + SHRINK))]];
}));
const tables = { "13C": table(seen["13C"]), "1H": table(seen["1H"]), solvent: { "13C": table(differing("13C")), "1H": table(differing("1H")) } };
console.log(`¹³C codes: ${tables["13C"].hash.length}, ¹H codes: ${tables["1H"].hash.length}; in one solvent: ¹³C ${tables.solvent["13C"].hash.length}, ¹H ${tables.solvent["1H"].hash.length}`);

if (test) {
  useTables(tables);
  for (const nucleus of ["13C", "1H"] as Nucleus[]) {
    const errors: number[] = [], levels = new Array(7).fill(0);
    // Shifts measured in a known solvent, predicted from every solvent and from that solvent's table: all of them, and
    // those of hydrogens on O, N and S.
    const known = { any: [] as number[], own: [] as number[], anyX: [] as number[], ownX: [] as number[] };
    let missed = 0;
    for (const { g, out } of held) {
      let env;
      try { env = environment(g); } catch { continue; }
      for (const o of out.filter((x) => x.nucleus === nucleus)) {
        const p = lookup(env, nucleus, o.atom);
        if (!p) { missed++; continue; }
        errors.push(Math.abs(p.shift - o.shift));
        levels[p.level]++;
        if (!o.solvent) continue;
        const q = lookup(env, nucleus, o.atom, o.solvent)!, x = ["O", "N", "S"].includes(g.atoms[o.atom].el);
        known.any.push(Math.abs(p.shift - o.shift)); known.own.push(Math.abs(q.shift - o.shift));
        if (x) { known.anyX.push(Math.abs(p.shift - o.shift)); known.ownX.push(Math.abs(q.shift - o.shift)); }
      }
    }
    errors.sort((a, b) => a - b);
    const mae = errors.reduce((a, b) => a + b, 0) / errors.length, mean = (v: number[]) => (v.length ? (v.reduce((a, b) => a + b, 0) / v.length).toFixed(3) : "–");
    console.log(`${nucleus}: ${errors.length} shifts, MAE ${mae.toFixed(2)} ppm, median ${errors[errors.length >> 1].toFixed(2)}, 90% within ${errors[Math.floor(errors.length * 0.9)].toFixed(2)}, not covered ${missed}, by level ${levels.slice(1).join("/")}`);
    console.log(`  in a known solvent: ${known.any.length} shifts, MAE ${mean(known.any)} from every solvent, ${mean(known.own)} with the solvent's table; on O, N and S: ${known.anyX.length}, ${mean(known.anyX)} and ${mean(known.ownX)}`);
  }
} else {
  const bytes = gzipSync(writeTables(tables), { level: 9 }), dir = new URL("../data/nmr/", import.meta.url);
  mkdirSync(dir, { recursive: true });
  writeFileSync(new URL("shifts.bin.gz", dir), bytes);
  console.log(`wrote data/nmr/shifts.bin.gz, ${(bytes.length / 1e6).toFixed(1)} MB`);
}
