// Run: node src/nmrhetero.check.ts. ¹⁹F and ³¹P prediction, and couplings to F and P in every nucleus's spectrum:
// shifts near well-known spectra, the typical J values, decoupling, the plot, measured ¹⁹F and ³¹P, and speed.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { hydrogens } from "./render.ts";
import type { Graph } from "./naming.ts";
import { acsText, acsTitle, detailsTable, frequency, guessNucleus, multiplicity, predict, quality, readTables, NUCLEI, NUCLEUS_LIST, type Nucleus, type Signal } from "./nmr.ts";
import { fullRange, solventPeaks, spectrumFigure, spectrumLines } from "./spectrumplot.ts";
import { analyse, fromJcamp, measuredText } from "./measured.ts";

// A graph from elements and bonds ([a, b, order]), with hydrogens filled in and charges by atom.
type B = [number, number, number];
function graph(els: string[], bonds: B[], charge: Record<number, number> = {}): Graph {
  const used = els.map(() => 0);
  for (const [a, b, o] of bonds) { used[a] += o; used[b] += o; }
  return { atoms: els.map((el, i) => ({ el, charge: charge[i] ?? 0, h: el === "H" ? 0 : hydrogens(el, charge[i] ?? 0, used[i]) })), bonds: bonds.map(([a, b, order]) => ({ a, b, order: order as 1 | 2 | 3 })) };
}
const ring = (o: number): B[] => [[o, o + 1, 2], [o + 1, o + 2, 1], [o + 2, o + 3, 2], [o + 3, o + 4, 1], [o + 4, o + 5, 2], [o + 5, o, 1]];
const C6 = Array(6).fill("C"), PH3 = (p: number): B[] => [...ring(p + 1), ...ring(p + 7), ...ring(p + 13), [p, p + 1, 1], [p, p + 7, 1], [p, p + 13, 1]];

const phcf3 = graph([...C6, "C", "F", "F", "F"], [...ring(0), [0, 6, 1], [6, 7, 1], [6, 8, 1], [6, 9, 1]]);
const fluorotoluene = graph([...C6, "C", "F"], [...ring(0), [0, 6, 1], [3, 7, 1]]);
const phf = graph([...C6, "F"], [...ring(0), [0, 6, 1]]);
const tfa = graph(["C", "F", "F", "F", "C", "O", "O"], [[0, 1, 1], [0, 2, 1], [0, 3, 1], [0, 4, 1], [4, 5, 2], [4, 6, 1]]);
const fluoroethane = graph(["C", "C", "F"], [[0, 1, 1], [1, 2, 1]]);
const pph3 = graph(["P", ...C6, ...C6, ...C6], PH3(0));
const ph3po = graph(["P", ...C6, ...C6, ...C6, "O"], [...PH3(0), [0, 19, 2]]);
const ph3poCharged = graph(["P", ...C6, ...C6, ...C6, "O"], [...PH3(0), [0, 19, 1]], { 0: 1, 19: -1 });
const phosphate = graph(["P", "O", "O", "C", "C", "O", "C", "C", "O", "C", "C"], [[0, 1, 2], [0, 2, 1], [2, 3, 1], [3, 4, 1], [0, 5, 1], [5, 6, 1], [6, 7, 1], [0, 8, 1], [8, 9, 1], [9, 10, 1]]);
const phosphite = graph(["P", "O", "C", "O", "C", "O", "C"], [[0, 1, 1], [1, 2, 1], [0, 3, 1], [3, 4, 1], [0, 5, 1], [5, 6, 1]]);
// Diethyl phosphite, (EtO)₂P(O)H: its P–H drawn as an atom, as a phosphorus with four bonds and no charge needs.
const hPhosphonate = graph(["P", "O", "O", "C", "C", "O", "C", "C", "H"], [[0, 1, 2], [0, 2, 1], [2, 3, 1], [3, 4, 1], [0, 5, 1], [5, 6, 1], [6, 7, 1], [0, 8, 1]]);
// PF₆⁻ with its cation, as a salt is drawn: K⁺ PF₆⁻.
const pf6 = graph(["P", "F", "F", "F", "F", "F", "F", "K"], [[0, 1, 1], [0, 2, 1], [0, 3, 1], [0, 4, 1], [0, 5, 1], [0, 6, 1]], { 0: -1, 7: 1 });
const methylPhosphonium = graph(["P", ...C6, ...C6, ...C6, "C"], [...PH3(0), [0, 19, 1]], { 0: 1 });
const pdPhosphine = graph(["P", ...C6, ...C6, ...C6, "Pd", "Cl", "Cl"], [...PH3(0), [0, 19, 1], [19, 20, 1], [19, 21, 1]]);
const benzene = graph(C6, ring(0));

readTables(gunzipSync(readFileSync(new URL("../data/nmr/shifts.bin.gz", import.meta.url))));
const near = (got: number | undefined, want: number, within: number, what: string) => assert.ok(got !== undefined && Math.abs(got - want) <= within, `${what}: ${got} for ${want}`);
const only = (g: Graph, n: Nucleus, d?: boolean) => { const p = predict(g, n, undefined, d)!; assert.equal(p.signals.length, 1, `one ${n} signal`); return p.signals[0]; };
const js = (s: Signal) => s.couplings.map((c) => c.j);
const on = (g: Graph, n: Nucleus, atom: number) => predict(g, n)!.signals.find((s) => s.atoms.includes(atom))!;

// --- B3.1: one table of nuclei ------------------------------------------------------------------------------------
assert.deepEqual(NUCLEUS_LIST, ["1H", "13C", "19F", "31P"]);
assert.deepEqual(NUCLEUS_LIST.map((n) => Math.round(frequency(n, 400))), [400, 101, 376, 162]);
assert.equal(acsTitle({ nucleus: "19F" }, 400, "CDCl₃"), "¹⁹F NMR (376 MHz, CDCl₃)");
assert.equal(acsTitle({ nucleus: "31P", decoupled: true }, 400, "CDCl₃"), "³¹P{¹H} NMR (162 MHz, CDCl₃)");
assert.equal(acsTitle({ nucleus: "13C", decoupled: true }, 400, "CDCl₃"), "¹³C NMR (101 MHz, CDCl₃)");
// Every function that takes a nucleus works for all four.
for (const n of NUCLEUS_LIST) {
  const g = n === "19F" ? phcf3 : n === "31P" ? ph3po : fluorotoluene, p = predict(g, n)!;
  assert.ok(p && p.nucleus === n, `${n} predicted`);
  const [lo, hi] = fullRange(p, n);
  assert.ok(hi - lo >= 10 && p.signals.every((s) => s.shift > lo && s.shift < hi), `${n} range`);
  assert.ok(spectrumLines(p.signals, n, 400).length >= p.signals.length, `${n} lines`);
  for (const s of p.signals) assert.match(quality(s, n), /^(good|medium|rough)$/);
  assert.equal(detailsTable(p).split("\n").length, p.signals.length + 1);
  assert.match(acsText(p, 400, "CDCl₃"), new RegExp(`^${NUCLEI[n].name}`));
  assert.equal(solventPeaks("CDCl₃", n, 400).length, n === "1H" ? 2 : n === "13C" ? 1 : 0, `${n} solvent peaks`);
}

// --- B3.3: ¹⁹F and ³¹P shifts ---------------------------------------------------------------------------------------
near(only(phcf3, "19F").shift, -63.3, 2, "PhCF₃ ¹⁹F");
near(only(fluorotoluene, "19F").shift, -118.3, 2, "4-fluorotoluene ¹⁹F");
near(only(phf, "19F").shift, -113.5, 2, "PhF ¹⁹F");
near(only(tfa, "19F").shift, -76.5, 2, "TFA ¹⁹F");
near(only(pph3, "31P").shift, -4.7, 3, "PPh₃ ³¹P");
near(only(ph3po, "31P").shift, 27.1, 3, "Ph₃PO ³¹P");
near(only(phosphate, "31P").shift, 0.5, 3, "(EtO)₃PO ³¹P");
near(only(phosphite, "31P").shift, 141, 3, "P(OMe)₃ ³¹P");
near(only(hPhosphonate, "31P").shift, 7.7, 3, "(EtO)₂P(O)H ³¹P");
// P=O and P⁺–O⁻ are one bond drawn two ways.
assert.deepEqual(predict(ph3poCharged, "31P"), predict(ph3po, "31P"));
assert.deepEqual(predict(ph3poCharged, "13C"), predict(ph3po, "13C"));
// A salt comes with its cation: PF₆⁻ beside K⁺ predicts, and its six F are one signal.
assert.equal(only(pf6, "19F").nuclei, 6);
assert.equal(predict(benzene, "19F"), undefined);

// --- B3.5: couplings to F and P -------------------------------------------------------------------------------------
// PhCF₃ ¹³C: CF₃ q 272, ipso q 32, ortho q 3.8.
for (const [atom, j, within] of [[6, 272, 5], [0, 32, 2], [1, 3.8, 0.5]] as const) {
  const s = on(phcf3, "13C", atom);
  assert.equal(multiplicity(s), "q", `PhCF₃ C${atom}`);
  near(s.couplings[0].j, j, within, `PhCF₃ C${atom} J`);
}
// PhF ¹³C: d 246, 21, 8 and 3 Hz from ipso to para.
for (const [atom, j] of [[0, 246], [1, 21], [2, 8], [3, 3]] as const) { const s = on(phf, "13C", atom); assert.equal(multiplicity(s), "d"); near(s.couplings[0].j, j, 2, `PhF C${atom}`); }
// Fluoroethane ¹H: CH₂ dq (47, 7), CH₃ dt (24, 7).
const ch2f = on(fluoroethane, "1H", 1), ch3 = on(fluoroethane, "1H", 0);
assert.equal(multiplicity(ch2f), "dq");
near(js(ch2f)[0], 47, 2, "²J(H,F)");
assert.equal(multiplicity(ch3), "dt");
// (EtO)₂P(O)H: the P–H is a d of about 690 Hz in ¹H, and its OCH₂ couples to P.
const ph = predict(hPhosphonate, "1H")!.signals.find((s) => s.group === "PH")!;
assert.equal(multiplicity(ph), "d");
near(ph.couplings[0].j, 690, 30, "¹J(P,H)");
assert.ok(js(on(hPhosphonate, "1H", 3)).some((j) => Math.abs(j - 8) < 1), "³J(P,O,C,H)");
// PF₆⁻: ³¹P a septet of 710 Hz, ¹⁹F a doublet of 710 Hz.
const p6 = only(pf6, "31P"), f6 = only(pf6, "19F");
assert.equal(multiplicity(p6), "sept");
near(p6.couplings[0].j, 710, 1, "¹J(P,F)");
assert.equal(multiplicity(f6), "d");
near(f6.couplings[0].j, 710, 1, "¹J(F,P)");
// Every coupling is reciprocal: J from H to F seen from ¹H is J from F to H seen from ¹⁹F, and likewise P.
for (const g of [phf, fluoroethane, fluorotoluene, phcf3, hPhosphonate, pf6]) {
  for (const [a, b] of [["1H", "19F"], ["1H", "31P"], ["19F", "31P"]] as [Nucleus, Nucleus][]) {
    const pa = predict(g, a, undefined, false), pb = predict(g, b, undefined, false);
    if (!pa || !pb) continue;
    for (const s of pa.signals) for (const c of s.couplings) for (const atom of c.with ?? []) {
      const t = pb.signals.find((x) => x.atoms.includes(atom));
      if (t) assert.ok(t.couplings.some((d) => Math.abs(d.j - c.j) < 0.01 && d.with!.some((w) => s.atoms.includes(w))), `${a}–${b} J ${c.j} both ways`);
    }
  }
}

// --- B3.9: decoupling -----------------------------------------------------------------------------------------------
// ¹⁹F is coupled by default: 4-fluorotoluene's F is a tt (9, 5.5); decoupled, a singlet, and the title says {¹H}.
const tt = predict(fluorotoluene, "19F")!, s19 = predict(fluorotoluene, "19F", undefined, true)!;
assert.equal(tt.decoupled, false);
assert.equal(multiplicity(tt.signals[0]), "tt");
assert.deepEqual(js(tt.signals[0]), [9, 5.5]);
assert.equal(multiplicity(s19.signals[0]), "s");
assert.match(acsText(tt, 400, "CDCl₃"), /^¹⁹F NMR \(376 MHz, CDCl₃\) δ −118\.\d \(tt, J = 9\.0, 5\.5 Hz, 1F\)\.$/);
assert.match(acsText(s19, 400, "CDCl₃"), /^¹⁹F\{¹H\} NMR/);
// ³¹P is ¹H-decoupled by default; coupled, Ph₃PO's P is split by the aromatic hydrogens.
assert.equal(predict(ph3po, "31P")!.decoupled, true);
assert.equal(multiplicity(only(ph3po, "31P")), "s");
assert.notEqual(multiplicity(only(ph3po, "31P", false)), "s");
assert.match(acsText(predict(ph3po, "31P")!, 400, "CDCl₃"), /^³¹P\{¹H\} NMR \(162 MHz, CDCl₃\) δ 2\d\.\d\.$/);
// ¹³C is always ¹H-decoupled.
assert.equal(predict(phcf3, "13C", undefined, false)!.decoupled, true);

// --- B3.10: every nucleus for every structure -----------------------------------------------------------------------
// A structure with no F or P predicts no ¹⁹F or ³¹P signals, so the panel shows the nucleus's range with nothing on it.
assert.equal(predict(benzene, "19F"), undefined);
assert.equal(predict(phcf3, "31P"), undefined);
assert.deepEqual(fullRange(undefined, "19F"), NUCLEI["19F"].range);
assert.deepEqual(fullRange(undefined, "31P"), NUCLEI["31P"].range);

// --- B3.11: the plot ------------------------------------------------------------------------------------------------
// The range fits the signals, at least 20 ppm wide; ¹⁹F's shifts are negative, written with a true minus.
const [flo, fhi] = fullRange(tt, "19F");
assert.ok(fhi - flo >= 20 && flo < -118.3 && fhi > -118.3, `¹⁹F range ${flo} to ${fhi}`);
const fig = spectrumFigure({ prediction: tt, nucleus: "19F", mhz: 400, solvent: "CDCl₃", solventPeaks: true, range: [flo, fhi], colours: [], width: 10, height: 3, em: 0.55 });
assert.ok(fig.curves.some((c) => c.role === "trace"), "¹⁹F is a trace");
assert.ok(fig.texts.some((t) => t.role.startsWith("tick:") && t.text.startsWith("−")), "ticks use U+2212");
assert.ok(!fig.texts.some((t) => t.role.startsWith("solvent:")), "no solvent peaks in ¹⁹F");
assert.ok(fig.texts.some((t) => /tt, 1F/.test(t.text)), "the label gives the multiplet and 1F");
// ³¹P is sticks: PF₆⁻'s septet is seven of them.
const pfig = spectrumFigure({ prediction: predict(pf6, "31P")!, nucleus: "31P", mhz: 400, solvent: "CDCl₃", solventPeaks: true, range: fullRange(predict(pf6, "31P"), "31P"), colours: [], width: 10, height: 3, em: 0.55 });
assert.equal(pfig.lines.filter((l) => l.role.startsWith("trace:")).length, 7);
assert.equal(pfig.curves.length, 0);
// The table for a spreadsheet keeps a hyphen-minus.
assert.match(detailsTable(tt), /\t-118\.\d\t/);

// --- B3.13: quality ---------------------------------------------------------------------------------------------------
assert.equal(quality(only(methylPhosphonium, "31P"), "31P"), "rough");
const pd = only(pdPhosphine, "31P");
assert.equal(pd.metal, true);
assert.equal(quality(pd, "31P"), "rough");
assert.equal(quality(only(phcf3, "19F"), "19F"), "good");
// ¹H and ¹³C keep their metal-free rule: a ferrocene ring is not rough for being on iron (nmrmetal.check).
assert.equal(predict(pdPhosphine, "13C")!.signals.some((s) => s.metal), false);

// --- B3.14: measured ¹⁹F and ³¹P ------------------------------------------------------------------------------------
// A file that does not name its nucleus is read by its observe frequency, then by its width.
assert.equal(guessNucleus(0, -200, 376.5), "19F");
assert.equal(guessNucleus(50, -50, 161.98), "31P");
assert.equal(guessNucleus(220, -10, 100.6), "13C");
assert.equal(guessNucleus(12, -1, 400.13), "1H");
assert.equal(guessNucleus(220, -10), "13C");
assert.equal(guessNucleus(12, -1), "1H");
// A measured ¹⁹F tt (9, 5.5 Hz) at 376 MHz is one multiplet, named as ¹H's are, with no solvent marks.
const F = 376.5, lineAt = (x: number, p: number) => (0.25 / F) ** 2 / ((x - p) ** 2 + (0.25 / F) ** 2);
const ttLines: number[] = [];
for (const a of [-1, 0, 1]) for (const b of [-1, 0, 1]) ttLines.push(-118.3 + (a * 9 + b * 5.5) / F);
const weights = ttLines.map((_, k) => [1, 2, 1][Math.floor(k / 3)] * [1, 2, 1][k % 3]);
const f19 = fromJcamp({ title: "f", kind: "nmr", nucleus: "19F", mhz: F, solvent: "CDCl₃", xUnit: "ppm", yUnit: "", first: -110, last: -126,
  y: Float64Array.from({ length: 32768 }, (_, i) => { const x = -110 - (16 * i) / 32767; return ttLines.reduce((s, p, k) => s + weights[k] * lineAt(x, p), 0); }) }, 1);
const fa = analyse(f19);
assert.equal(fa.groups.length, 1, "one multiplet");
assert.match(measuredText(f19, fa), /^¹⁹F NMR \(377 MHz, CDCl₃\) δ −118\.3 \(tt, J = 9\.0, 5\.5 Hz, 1F\)\.$/);

// --- B3.15: speed -----------------------------------------------------------------------------------------------------
// A 211-atom structure (a chain of 35 fluorinated phenyl phosphonates) predicts each nucleus well under 100 ms.
{
  const els: string[] = [], bonds: B[] = [];
  for (let k = 0; k < 35 && els.length < 211; k++) {
    const o = els.length;
    els.push(...C6, "F");
    bonds.push(...ring(o), [o + 3, o + 6, 1]);
    if (k) bonds.push([o - 1, o, 1]);
  }
  const g = graph(els, bonds), times: Record<string, number> = {};
  for (const n of NUCLEUS_LIST) { const t = performance.now(); predict(g, n); times[n] = performance.now() - t; }
  for (const n of NUCLEUS_LIST) assert.ok(times[n] < 100, `${n} took ${times[n].toFixed(1)} ms at ${els.length} atoms`);
}
console.log("nmrhetero.check: ok");
