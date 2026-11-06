// Run: node src/nmr.check.ts. Fails loudly if NMR prediction breaks: codes that depend on drawing order, or shifts
// far from well-known spectra.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { hydrogens } from "./render.ts";
import type { Graph } from "./naming.ts";
import { acsText, detailsTable, environment, hose, multiplicity, predict, readTables, writeTables } from "./nmr.ts";

// A graph from elements and bonds ([a, b, order]), with hydrogens filled in.
function graph(els: string[], bonds: [number, number, number][]): Graph {
  const used = els.map(() => 0);
  for (const [a, b, o] of bonds) { used[a] += o; used[b] += o; }
  return { atoms: els.map((el, i) => ({ el, charge: 0, h: hydrogens(el, 0, used[i]) })), bonds: bonds.map(([a, b, order]) => ({ a, b, order: order as 1 | 2 | 3 })) };
}
// The same graph with its atoms in another order.
function shuffled(g: Graph, order: number[]): Graph {
  const to = order.map((_, i) => order.indexOf(i));
  return { atoms: order.map((i) => g.atoms[i]), bonds: g.bonds.map((b) => ({ ...b, a: to[b.a], b: to[b.b] })) };
}

// Ethyl acetate: CH3-C(=O)-O-CH2-CH3.
const ester = graph(["C", "C", "O", "O", "C", "C"], [[0, 1, 1], [1, 2, 2], [1, 3, 1], [3, 4, 1], [4, 5, 1]]);
// Toluene, Kekulé.
const toluene = graph(["C", "C", "C", "C", "C", "C", "C"], [[0, 1, 2], [1, 2, 1], [2, 3, 2], [3, 4, 1], [4, 5, 2], [5, 0, 1], [0, 6, 1]]);

// Codes do not depend on the order atoms were drawn in, or on which Kekulé form was drawn.
const order = [5, 3, 0, 4, 2, 1];
assert.deepEqual(hose(environment(ester), 4), hose(environment(shuffled(ester, order)), order.indexOf(4)));
const other = graph(["C", "C", "C", "C", "C", "C", "C"], [[0, 1, 1], [1, 2, 2], [2, 3, 1], [3, 4, 2], [4, 5, 1], [5, 0, 2], [0, 6, 1]]);
assert.deepEqual(hose(environment(toluene), 6), hose(environment(other), 6));
assert.deepEqual(hose(environment(toluene), 2), hose(environment(other), 2));

readTables(gunzipSync(readFileSync(new URL("../data/nmr/shifts.bin.gz", import.meta.url))));
const near = (got: number | undefined, want: number, within: number, what: string) => assert.ok(got !== undefined && Math.abs(got - want) <= within, `${what}: ${got} for ${want}`);

// Ethyl acetate, measured (CDCl3): ¹H 4.12 (q, 2H), 2.05 (s, 3H), 1.26 (t, 3H); ¹³C 171.1, 60.4, 21.0, 14.2.
const h = predict(ester, "1H")!;
const at = (atom: number) => h.signals.find((s) => s.atoms.includes(atom))!;
near(at(4).shift, 4.12, 0.15, "OCH2");
near(at(0).shift, 2.05, 0.1, "acetyl CH3");
near(at(5).shift, 1.26, 0.1, "ester CH3");
assert.equal(multiplicity(at(4)), "q");
assert.equal(multiplicity(at(5)), "t");
assert.equal(multiplicity(at(0)), "s");
assert.deepEqual(h.signals.map((s) => s.nuclei), [2, 3, 3]);
const c = predict(ester, "13C")!;
for (const [atom, want] of [[1, 171.1], [4, 60.4], [0, 21.0], [5, 14.2]]) near(c.signals.find((s) => s.atoms.includes(atom))?.shift, want, 1.5, `C${atom}`);
assert.match(acsText(h, 400, "CDCl₃"), /^¹H NMR \(400 MHz, CDCl₃\) δ \d\.\d\d \(q, J = 7\.0 Hz, 2H\), \d\.\d\d \(s, 3H\), \d\.\d\d \(t, J = 7\.0 Hz, 3H\)\.$/);

// Toluene: five ring carbons in four kinds (ipso, ortho, meta, para) plus the methyl; ¹H methyl at 2.35.
const tc = predict(toluene, "13C")!;
assert.deepEqual(tc.signals.map((s) => s.nuclei).sort(), [1, 1, 1, 2, 2]);
near(tc.signals.find((s) => s.atoms.includes(6))?.shift, 21.4, 1.5, "toluene CH3");
near(tc.signals.find((s) => s.atoms.includes(0))?.shift, 137.9, 2, "toluene ipso");
near(predict(toluene, "1H")!.signals.find((s) => s.atoms.includes(6))?.shift, 2.35, 0.1, "toluene CH3 H");
// Solvents (CH-28). OH, NH and SH hydrogens exchange with D₂O and CD₃OD, so they give no ¹H peak there.
const ethanol = graph(["C", "C", "O"], [[0, 1, 1], [1, 2, 1]]);
assert.deepEqual(predict(ethanol, "1H", "D₂O")!.signals.map((s) => s.group), ["CH2", "CH3"]);
assert.deepEqual(predict(ethanol, "1H", "CD₃OD")!.signals.map((s) => s.group), ["CH2", "CH3"]);
assert.deepEqual(predict(ethanol, "1H", "CDCl₃")!.signals.map((s) => s.group), ["CH2", "OH", "CH3"]);
// ¹³C shifts measured in the solvent asked for, where the table has them; none without a solvent. ¹H has no solvent
// table (it made ¹H worse on held-out spectra).
const phenol = graph(["C", "C", "C", "C", "C", "C", "O"], [[0, 1, 2], [1, 2, 1], [2, 3, 2], [3, 4, 1], [4, 5, 2], [5, 0, 1], [0, 6, 1]]);
const inWater = predict(phenol, "13C", "D₂O")!;
assert.ok(inWater.signals.some((s) => s.solvent === "D₂O"));
assert.ok(predict(phenol, "13C")!.signals.every((s) => !s.solvent));
assert.ok(predict(phenol, "1H", "DMSO-d₆")!.signals.every((s) => !s.solvent));
assert.match(detailsTable(inWater), /\tD₂O\t/);
assert.match(detailsTable(predict(phenol, "13C")!), /\tany solvent\t/);
// A version 1 table (no solvent tables) still reads; the version 2 file is read again after.
const one = { hash: new Uint32Array([5]), shift: new Int16Array([100]), sd: new Uint16Array([1]), n: new Uint16Array([1]) };
const v1 = writeTables({ "13C": one, "1H": one });
assert.equal(new DataView(v1.buffer).getUint32(4, true), 1);
readTables(v1);
readTables(gunzipSync(readFileSync(new URL("../data/nmr/shifts.bin.gz", import.meta.url))));
assert.throws(() => readTables(v1.slice(0, 20)));
console.log("nmr.check: ok");
