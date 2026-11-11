// Run: node src/nmr.check.ts. Fails loudly if NMR prediction breaks: codes that depend on drawing order, or shifts
// far from well-known spectra.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { hydrogens } from "./render.ts";
import type { Graph } from "./naming.ts";
import { acsText, codes, detailsTable, environment, heavy, hose, multiplicity, predict, quality, readTables, writeTables } from "./nmr.ts";

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
// η ligands (Cp and arene rings on a metal). However a ring is drawn, its atoms give the same codes: with two double
// bonds or the other two, as the anion, or with the hydrogens counted as nmrshiftdb2's molfiles count them (the bonds to
// the metal taking up the carbons' valence). The metal keeps its charge (a cobaltocenium ion's Co+). Fe is atom 0;
// the rings are 1-5 and 6-10.
const ring5 = (s: number, shift = 0): [number, number, number][] => [0, 1, 2, 3, 4].map((k) => [s + k, s + ((k + 1) % 5), (k + shift) % 5 === 1 || (k + shift) % 5 === 3 ? 2 : 1]);
const onMetal = (s: number, n: number): [number, number, number][] => Array.from({ length: n }, (_, k) => [0, s + k, 1]);
// Hydrogens as Octet counts them for an η ring (expandWithOrigins): each ring atom as if its bond to the metal (atom
// 0) were not there.
function eta(els: string[], bonds: [number, number, number][], ring: number[], charges: Record<number, number> = {}): Graph {
  const g = graph(els, bonds), free = graph(els, bonds.filter(([a, b]) => !(a === 0 && ring.includes(b))));
  return { atoms: g.atoms.map((a, i) => ({ ...a, charge: charges[i] ?? 0, h: ring.includes(i) ? free.atoms[i].h : a.h })), bonds: g.bonds };
}
const tenRing = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
const fc = ["Fe", ...Array(10).fill("C")], fcBonds = [...ring5(1), ...ring5(6), ...onMetal(1, 10)];
const ferrocene = eta(fc, fcBonds, tenRing);
const sameCodes = (a: Graph, b: Graph, what: string) => {
  const ea = environment(heavy(a).g), eb = environment(heavy(b).g);
  for (let i = 1; i <= 10; i++) assert.deepEqual(codes(ea, i), codes(eb, i), `${what}: atom ${i}`);
};
sameCodes(ferrocene, eta(fc, [...ring5(1, 2), ...ring5(6, 1), ...onMetal(1, 10)], tenRing), "the other Kekulé forms");
sameCodes(ferrocene, eta(fc, fcBonds, tenRing, { 1: -1, 6: -1 }), "each ring drawn as the anion");
sameCodes(ferrocene, graph(fc, fcBonds), "hydrogens counted with the bonds to the metal");
// Ferrocene, measured (CDCl3): ¹H 4.16 (s, 10H); ¹³C 67.8. One signal each, from all ten carbons.
const fh = predict(ferrocene, "1H")!, fcc = predict(ferrocene, "13C")!;
assert.equal(fh.signals.length, 1);
assert.equal(fh.signals[0].nuclei, 10);
assert.equal(multiplicity(fh.signals[0]), "s");
near(fh.signals[0].shift, 4.16, 0.1, "ferrocene H");
assert.equal(quality(fh.signals[0], "1H"), "good");
assert.equal(fcc.signals.length, 1);
assert.deepEqual(fcc.signals[0].atoms.sort((a, b) => a - b), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
near(fcc.signals[0].shift, 67.8, 1.5, "ferrocene C");
// Acetylferrocene (C1 bears the acetyl: C11, O12, C13), measured (CDCl3): ¹H 4.77 (2H), 4.50 (2H), 4.20 (s, 5H),
// 2.40 (s, 3H); ¹³C 202.0, 79.2, 72.3, 69.8, 69.5, 27.4. nmrshiftdb2 has its ¹³C spectrum, so those are good; it has
// no ¹H of the substituted ring, so those are not.
const acetyl = eta([...fc, "C", "O", "C"], [...fcBonds, [1, 11, 1], [11, 12, 2], [11, 13, 1]], tenRing);
const ac = predict(acetyl, "13C")!, acAt = (atom: number) => ac.signals.find((s) => s.atoms.includes(atom))!;
assert.equal(ac.signals.length, 6);
for (const [atom, want] of [[11, 202.0], [1, 79.2], [2, 72.3], [3, 69.8], [6, 69.5], [13, 27.4]]) { near(acAt(atom).shift, want, 1.5, `acetylferrocene C${atom}`); assert.equal(quality(acAt(atom), "13C"), "good"); }
assert.equal(acAt(6).nuclei, 5);
const ah = predict(acetyl, "1H")!, ahAt = (atom: number) => ah.signals.find((s) => s.atoms.includes(atom))!;
assert.deepEqual(ah.signals.map((s) => s.nuclei).sort(), [2, 2, 3, 5]);
near(ahAt(6).shift, 4.20, 0.1, "acetylferrocene Cp H");
assert.equal(multiplicity(ahAt(6)), "s");
near(ahAt(13).shift, 2.40, 0.15, "acetylferrocene CH3");
for (const atom of [2, 3]) { assert.equal(multiplicity(ahAt(atom)), "d"); assert.equal(ahAt(atom).couplings[0].j, 2.5); assert.notEqual(quality(ahAt(atom), "1H"), "good"); }
// Cp2ZrCl2 (Zr 0, Cl 11 and 12) and (benzene)Cr(CO)3 (Cr 0, ring 1-6, CO 7-12): nmrshiftdb2 has little or nothing
// like them, so each Cp, arene and carbonyl carbon still gets one shift, rated rough (measured: Cp2ZrCl2 ¹H 6.47,
// ¹³C 115.9; (C6H6)Cr(CO)3 ¹H 5.30, ¹³C 93.0 and 233).
const zr = eta(["Zr", ...Array(10).fill("C"), "Cl", "Cl"], [...fcBonds, [0, 11, 1], [0, 12, 1]], tenRing);
const cr = eta(["Cr", ...Array(6).fill("C"), "C", "O", "C", "O", "C", "O"], [
  [1, 2, 2], [2, 3, 1], [3, 4, 2], [4, 5, 1], [5, 6, 2], [6, 1, 1], ...onMetal(1, 6), [0, 7, 2], [7, 8, 2], [0, 9, 2], [9, 10, 2], [0, 11, 2], [11, 12, 2]], [1, 2, 3, 4, 5, 6]);
for (const [what, g, h, c] of [["Cp2ZrCl2", zr, [10], [10]], ["(benzene)Cr(CO)3", cr, [6], [3, 6]]] as const) {
  const ph = predict(g, "1H")!, pc = predict(g, "13C")!;
  assert.deepEqual(ph.signals.map((s) => s.nuclei), h, `${what} ¹H`);
  assert.equal(multiplicity(ph.signals[0]), "s");
  assert.deepEqual(pc.signals.map((s) => s.nuclei).sort((a, b) => a - b), c, `${what} ¹³C`);
  for (const s of ph.signals) assert.equal(quality(s, "1H"), "rough", `${what} ¹H rated rough`);
  for (const s of pc.signals) assert.equal(quality(s, "13C"), "rough", `${what} ¹³C rated rough`);
}
// An atom whose surroundings the table has never seen still gets a shift, from the atom alone (level 0), rated rough.
const carbonyl = predict(cr, "13C")!.signals.find((s) => s.atoms.includes(7))!;
assert.equal(carbonyl.level, 0);
assert.match(detailsTable(predict(cr, "13C")!), /\t0\t/);

// A version 1 table (no solvent tables) still reads; the version 2 file is read again after.
const one = { hash: new Uint32Array([5]), shift: new Int16Array([100]), sd: new Uint16Array([1]), n: new Uint16Array([1]) };
const v1 = writeTables({ "13C": one, "1H": one });
assert.equal(new DataView(v1.buffer).getUint32(4, true), 1);
readTables(v1);
readTables(gunzipSync(readFileSync(new URL("../data/nmr/shifts.bin.gz", import.meta.url))));
assert.throws(() => readTables(v1.slice(0, 20)));
console.log("nmr.check: ok");
