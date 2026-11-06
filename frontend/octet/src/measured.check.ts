// Run: node src/measured.check.ts. Fails loudly if a measured spectrum's peaks, multiplets, integrals, text line or
// assignments go wrong, or do not survive saving and opening again. The spectra are made here from known lines.
import assert from "node:assert/strict";
import { readJcamp } from "./jcamp.ts";
import { analyse, assignGroups, assignRanges, assignValue, defineGroup, firstOrder, fromJcamp, fromSpectrumObject, keepIds, keyOf, measuredFigure, measuredHead, measuredText, msPeaks, nameOf, nextGroupId, pickPeaks, readMeasured, regroup, spectrumObject, writeMeasured, type Measured } from "./measured.ts";
import { parse, serialize } from "./file.ts";
import { nearest } from "./msanalysis.ts";
import type { Mol } from "./render.ts";

// --- A spectrum from known lines ----------------------------------------------------------------------------------

const MHZ = 400.13, N = 32768, HI = 11, LO = -1;
// Lorentzian lines (ppm, height) 0.5 Hz half width, summed at each point from HI to LO ppm, with a little noise.
function trace(lines: [number, number][], w = 0.5 / MHZ, noise = 0.0005) {
  let seed = 11;
  const rand = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff - 0.5; };
  return Array.from({ length: N }, (_, i) => {
    const x = HI - ((HI - LO) * i) / (N - 1);
    return lines.reduce((s, [p, h]) => s + (h * w * w) / ((x - p) ** 2 + w * w), 0) + noise * rand();
  });
}
// A first-order multiplet's lines: centre (ppm), nuclei, and couplings (Hz, each to n nuclei).
function multiplet(shift: number, nuclei: number, couplings: [number, number][]): [number, number][] {
  let out: [number, number][] = [[shift, nuclei]];
  for (const [j, n] of couplings) {
    const row = [1];
    for (let k = 1; k <= n; k++) row.push((row[k - 1] * (n - k + 1)) / k);
    out = out.flatMap(([p, h]) => row.map((c, i): [number, number] => [p + ((i - n / 2) * j) / MHZ, (h * c) / 2 ** n]));
  }
  return out;
}
// A JCAMP-DX file of a trace, in DIFDUP form at 16 points a line (the form instruments write).
function jdx(ys: number[], more = "") {
  const scale = 1e6 / Math.max(...ys), ints = ys.map((v) => Math.round(v * scale)), out: string[] = [];
  const sqz = (v: number) => { const s = String(Math.abs(v)); return (v < 0 ? "abcdefghi"[+s[0] - 1] : "@ABCDEFGHI"[+s[0]]) + s.slice(1); };
  const dif = (v: number) => { const s = String(Math.abs(v)); return (v < 0 ? "jklmnopqr"[+s[0] - 1] : "%JKLMNOPQR"[+s[0]]) + s.slice(1); };
  const dup = (k: number) => { const s = String(k); return "STUVWXYZs"[+s[0] - 1] + s.slice(1); };
  for (let i = 0; i < ints.length;) {
    const start = out.length ? i - 1 : i, part = ints.slice(start, Math.min(ints.length, start + 17)), d = part.slice(1).map((v, k) => v - part[k]);
    let s = `${start}${sqz(part[0])}`;
    for (let k = 0; k < d.length;) { let run = 1; while (k + run < d.length && d[k + run] === d[k]) run++; s += dif(d[k]) + (run > 1 ? dup(run) : ""); k += run; }
    out.push(s);
    i = start + part.length;
  }
  return `##TITLE= Check compound\n##JCAMP-DX= 5.01\n##DATA TYPE= NMR SPECTRUM\n##.OBSERVE FREQUENCY= ${MHZ}\n##.OBSERVE NUCLEUS= ^1H\n##.SOLVENT NAME= CDCl3\n${more}` +
    `##XUNITS= HZ\n##YUNITS= ARBITRARY UNITS\n##FIRSTX= ${HI * MHZ}\n##LASTX= ${LO * MHZ}\n##YFACTOR= ${1 / scale}\n##NPOINTS= ${N}\n##XYDATA= (X++(Y..Y))\n${out.join("\n")}\n##END=\n`;
}

// A compound with a dd (J 10.0, 4.0 Hz), a quartet, a singlet, a triplet, a dt and a crowded multiplet, with
// CDCl₃'s residual peak and TMS.
const lines = [
  ...multiplet(7.4, 5, [[7.6, 2], [1.3, 1], [0.9, 2]]).map(([p, h], k): [number, number] => [p + ((k % 3) - 1) * 0.004, h]),
  [7.26, 0.4] as [number, number],
  ...multiplet(6.5, 1, [[10, 1], [4, 1]]),
  ...multiplet(5.8, 1, [[11, 1], [3.2, 2]]),
  ...multiplet(4.12, 2, [[7.1, 3]]),
  ...multiplet(2.05, 3, []),
  ...multiplet(1.26, 3, [[7.1, 2]]),
  [0, 0.3] as [number, number],
];
const text = jdx(trace(lines));
const [read] = readJcamp(text);
assert.equal(read.y.length, N);
const m = fromJcamp(read, 1);
assert.equal(keyOf(m), "1H");
assert.equal(nameOf(keyOf(m)), "¹H NMR");
assert.equal(m.solvent, "CDCl₃");

// Every line is a peak; nothing comes from the noise.
const peaks = pickPeaks(m);
assert.ok(peaks.length >= 30 && peaks.length <= 60, `${peaks.length} peaks`);
assert.ok(peaks.every((p) => lines.some(([x]) => Math.abs(x - p.x) < 0.003)), "a peak from noise");
// The quartet's lines, at their places to 0.1 Hz.
for (const [x] of multiplet(4.12, 2, [[7.1, 3]])) assert.ok(peaks.some((p) => Math.abs(p.x - x) * MHZ < 0.1), `quartet line ${x}`);

// The multiplets, their names, Js and integrals; the solvent and TMS found and left out.
const a = analyse(m);
const q0 = a.groups.find((g) => Math.abs(g.shift - 4.12) < 0.02)!.id;
const at = (shift: number) => a.groups.find((g) => Math.abs(g.shift - shift) < 0.02)!;
assert.equal(at(6.5).name, "dd");
assert.deepEqual(at(6.5).js.map((j) => j.toFixed(1)), ["10.0", "4.0"]);
assert.equal(at(5.8).name, "dt");
assert.deepEqual(at(5.8).js.map((j) => j.toFixed(1)), ["11.0", "3.2"]);
assert.equal(at(4.12).name, "q");
assert.equal(at(4.12).js[0].toFixed(1), "7.1");
assert.equal(at(2.05).name, "s");
assert.equal(at(1.26).name, "t");
assert.equal(at(7.4).name, "m");
assert.equal(at(7.26)?.other, "CDCl₃");
assert.equal(at(0).other, "TMS");
for (const [shift, n] of [[6.5, 1], [4.12, 2], [2.05, 3], [1.26, 3], [7.4, 5]]) assert.ok(Math.abs(at(shift).n - n) < 0.15, `${shift}: ${at(shift).n.toFixed(2)}H, not ${n}H`);

// The text line, high to low, the multiplet m by its range.
const line = measuredText(m, a);
assert.match(line, /^¹H NMR \(400 MHz, CDCl₃\) δ 7\.4\d–7\.3\d \(m, 5H\), 6\.50 \(dd, J = 10\.0, 4\.0 Hz, 1H\), 5\.80 \(dt, J = 11\.0, 3\.2 Hz, 1H\), 4\.12 \(q, J = 7\.1 Hz, 2H\), 2\.05 \(s, 3H\), 1\.26 \(t, J = 7\.1 Hz, 3H\)\.$/, line);
// The user's count for one multiplet sets the rest.
const per = analyse({ ...m, per: at(2.05).area / 6 });
assert.ok(Math.abs(per.groups.find((g) => g.id === at(1.26).id)!.n - 6) < 0.3);

// First-order patterns by Hoye's method, and what is not first order.
const fo = (hz: number[], hs: number[]) => firstOrder(hz.map((x, i) => ({ hz: x, h: hs[i] })), 0.3);
assert.deepEqual(fo([0], [1]), []);
assert.deepEqual(fo([0, 7, 14], [1, 2, 1]), [{ j: 7, n: 2 }]);
assert.deepEqual(fo([0, 5, 10, 15], [1, 1, 1, 1]), [{ j: 10, n: 1 }, { j: 5, n: 1 }]);
assert.deepEqual(fo([0, 2, 9, 11, 18, 20], [1, 1, 2, 2, 1, 1]), [{ j: 9, n: 2 }, { j: 2, n: 1 }]);
assert.equal(fo([0, 3, 9], [1, 1, 1]), undefined); // not symmetrical
assert.equal(fo([0, 4, 8], [1, 1, 1]), undefined); // three components
// Roofing: heights leaning one way still give a doublet.
assert.deepEqual(fo([0, 8], [0.8, 1.2]), [{ j: 8, n: 1 }]);

// A higher threshold keeps the ids of the multiplets it keeps; a range the user drew takes the first id it covers.
const ids = new Map(a.groups.map((g) => [Math.round(g.shift * 100), g.id]));
const high = regroup(m, 0.2, nextGroupId([m]));
assert.ok(high.groups.length < m.groups.length && high.groups.length >= 3);
for (const g of analyse(high).groups) if (ids.has(Math.round(g.shift * 100))) assert.equal(g.id, ids.get(Math.round(g.shift * 100)));
// The same spectrum opened again keeps its multiplets' ids.
const again = keepIds(fromJcamp(read, 500), m, 600);
assert.deepEqual(again.groups.map((g) => g.id), m.groups.map((g) => g.id));
const drawn = defineGroup(m, 1.2, 1.32, 99);
assert.ok(drawn.groups.some((g) => g.manual && g.id === at(1.26).id));
assert.equal(drawn.groups.length, m.groups.length);

// --- Saved and opened again ---------------------------------------------------------------------------------------

// Two carbons whose hydrogens are the quartet and the triplet, linked to them; the drawing saves and opens with the
// spectrum, its multiplets and the links, and gives the same text line.
const q = q0, t = at(1.26).id;
const doc: Mol = { atoms: [{ label: "C", location: [0, 0, 0], peaks: [q] }, { label: "C", location: [1, 0, 0], peaks: [t] }], bonds: [{ type: 1, atoms: [0, 1], peaks: [q, t] }], spectra: [m] };
const back = parse(serialize(doc));
assert.deepEqual(back.atoms.map((x) => x.peaks), [[q], [t]]);
// A bond keeps its links as an atom does (an IR band linked to its C=O).
assert.deepEqual(back.bonds[0].peaks, [q, t]);
assert.deepEqual(back.spectra![0].groups, m.groups);
assert.deepEqual([...back.spectra![0].y], [...m.y]);
assert.equal(measuredText(back.spectra![0], analyse(back.spectra![0])), line);
// And again: nothing drifts.
assert.equal(serialize(parse(serialize(back))), serialize(back));
// A copy pasted without its spectrum keeps no links; a link to a multiplet the drawing does not have is dropped.
assert.equal(parse(serialize({ ...doc, spectra: undefined })).atoms[0].peaks, undefined);
assert.equal(parse(serialize({ ...doc, spectra: undefined })).bonds[0].peaks, undefined);
const saved = JSON.parse(serialize(doc));
saved.structure.atoms[0].peaks = [q, 12345];
saved.structure.bonds[0].peaks = [12345, t];
assert.deepEqual(parse(JSON.stringify(saved)).atoms[0].peaks, [q]);
assert.deepEqual(parse(JSON.stringify(saved)).bonds[0].peaks, [t]);
// A damaged spectrum is refused as the whole drawing is: a short trace, a bad kind, ids twice, too many spectra.
const damaged = (change: (s: Record<string, unknown>) => void) => { const d = JSON.parse(serialize(doc)); change(d.spectra[0]); return () => parse(JSON.stringify(d)); };
assert.throws(damaged((s) => { s.y = (s.y as string).slice(0, 100); }), /damaged/);
assert.throws(damaged((s) => { s.kind = "xray"; }), /damaged/);
assert.throws(damaged((s) => { s.n = 1e9; }), /damaged/);
assert.throws(damaged((s) => { (s.groups as unknown[]).push((s.groups as unknown[])[0]); }), /damaged/);
assert.throws(damaged((s) => { s.title = "a\u0000b"; }), /damaged/);
assert.throws(() => { const d = JSON.parse(serialize(doc)); d.spectra = Array(17).fill(d.spectra[0]); parse(JSON.stringify(d)); }, /damaged/);
assert.throws(() => readMeasured({ ...writeMeasured(m), lo: 5, hi: 5 }), /damaged/);

// A doublet beside CDCl₃'s line stays a doublet: the solvent's line is a group of its own, left out of the text.
const near = fromJcamp(readJcamp(jdx(trace([...multiplet(7.24, 2, [[8.2, 1]]), [7.26, 0.6], ...multiplet(2.05, 3, [])])))[0], 1), an = analyse(near);
assert.equal(an.groups.find((g) => Math.abs(g.shift - 7.24) < 0.01)?.name, "d");
assert.equal(an.groups.find((g) => Math.abs(g.shift - 7.26) < 0.003)?.other, "CDCl₃");
assert.match(measuredText(near, an), /δ 7\.24 \(d, J = 8\.2 Hz, 2H\), 2\.05 \(s, 3H\)\.$/);

// The figure for the page: one curve of at most 1000 points (a pen curve's limit) inside its box, each multiplet's
// label in its colour above it, the solvent in grey, and the unit under the axis.
const fig = measuredFigure({ m, a, range: [-0.5, 8], colour: (id) => (id === q0 ? "#2F6FED" : undefined), width: 14, height: 3.5, em: 0.55 });
assert.equal(fig.curves.length, 1);
assert.ok(fig.curves[0].points.length <= 1000 && fig.curves[0].points.length > 400);
assert.ok(fig.curves[0].points.every(([px, py]) => px >= 0 && px <= 14 && py <= 3.5 + 1e-9));
assert.equal(fig.texts.find((t) => t.text === "4.12")?.colour, "#2F6FED");
assert.ok(fig.texts.some((t) => t.text === "q, 2H") && fig.texts.some((t) => t.text === "TMS" && t.grey) && fig.texts.some((t) => t.text === "ppm"));
assert.ok(fig.texts.find((t) => t.text === "4.12")!.at[0] < fig.texts.find((t) => t.text === "1.26")!.at[0]);
assert.equal(measuredHead(m), "¹H NMR (400 MHz, CDCl₃)");

// --- ¹³C, IR and MS ----------------------------------------------------------------------------------------------

const c13: Measured = fromJcamp({ title: "c", kind: "nmr", nucleus: "13C", mhz: 100.6, solvent: "CDCl₃", xUnit: "ppm", yUnit: "", first: 220, last: -10,
  y: Float64Array.from({ length: 16384 }, (_, i) => { const x = 220 - (230 * i) / 16383; return [[171.1, 0.5], [60.5, 1], [21.0, 0.9], [14.2, 1], [77.48, 0.6], [77.16, 0.6], [76.84, 0.6]].reduce((s, [p, h]) => s + (h * 0.0004) / ((x - p) ** 2 + 0.0004), 0); }) }, 1);
assert.equal(measuredText(c13, analyse(c13)), "¹³C NMR (101 MHz, CDCl₃) δ 171.1, 60.5, 21.0, 14.2.");
// CDCl₃'s triplet is one group, named once.
assert.equal(analyse(c13).groups.filter((g) => g.other === "CDCl₃").length, 1);
const msm = fromJcamp(readJcamp(`##TITLE=Ethyl acetate\n##DATA TYPE=MASS SPECTRUM\n##XUNITS=M/Z\n##YUNITS=RELATIVE ABUNDANCE\n##PEAK TABLE=(XY..XY)\n43,100 45,18\n61,15 88,8 29,1\n##END=`)[0], 1);
assert.equal(measuredText(msm, analyse(msm)), "MS m/z 88 (8), 61 (15), 45 (18), 43 (100).");
// A measured mass spectrum as Mass Spec Analysis's peak list: its sticks over the threshold, the tallest 100, so an
// ion finds its peak. A profile spectrum gives its picked peaks, each where its top is.
const list = msPeaks(msm);
assert.deepEqual(list.map((p) => [p.mz, Math.round(p.i)]), [[43, 100], [45, 18], [61, 15], [88, 8]]);
assert.equal(nearest(list, 88.05, "0.1Da")?.mz, 88);
const profile = fromJcamp({ title: "", kind: "ms", xUnit: "m/z", yUnit: "", first: 300, last: 304, y: Float64Array.from({ length: 40001 }, (_, i) => { const x = 300 + i / 10000; return [[301.1412, 100], [302.1446, 18]].reduce((s, [p, h]) => s + (h * 1e-6) / ((x - p) ** 2 + 1e-6), 0); }) }, 1);
const found = msPeaks(profile);
assert.deepEqual(found.map((p) => Math.round(p.i)), [100, 18]);
assert.ok(nearest(found, 301.1412, "5ppm") && nearest(found, 302.1446, "5ppm"), found.map((p) => p.mz).join(", "));
// IR in transmittance: the dips are the peaks.
const irm = fromJcamp({ title: "ir", kind: "ir", xUnit: "cm⁻¹", yUnit: "%T", first: 4000, last: 400, y: Float64Array.from({ length: 3601 }, (_, i) => { const x = 4000 - i; return 100 - [[1740, 80], [1240, 60], [2980, 20]].reduce((s, [p, h]) => s + (h * 100) / ((x - p) ** 2 + 100), 0); }) }, 1);
assert.equal(measuredText(irm, analyse(irm)), "IR ν̃ 2980, 1740, 1240 cm⁻¹.");

// --- ChemDraw's spectrum object ------------------------------------------------------------------------------------

// Assignment tags' values: ChemDraw's "lo-hi," pairs, negative shifts and exponents too; anything else is skipped.
assert.deepEqual(assignRanges("7.3-7.2,1.25-1.27,"), [[7.2, 7.3], [1.25, 1.27]]);
assert.deepEqual(assignRanges("-0.5--0.3,1e-05-2e-05,"), [[-0.5, -0.3], [1e-5, 2e-5]]);
assert.deepEqual(assignRanges("x-1,1-,,7"), []);
// A mass spectrum's sticks go on a 0.1 grid (ChemDraw's own step) and come back as sticks; a link made to a stick
// that moved onto the grid finds it within half a bin.
const mso = spectrumObject(msm), back88 = fromSpectrumObject(mso.attrs, mso.text, mso.own, 1);
assert.deepEqual([mso.attrs.Class, mso.attrs.XType, mso.attrs.XSpacing, mso.attrs.XLow], ["MassSpectrum", "MassUnits", "0.1", "29"]);
assert.deepEqual([back88.sticks, [...back88.xs!].map((x) => Math.round(x * 10) / 10), back88.title], [true, [29, 43, 45, 61, 88], "Ethyl acetate"]);
assert.equal(measuredText(back88, analyse(back88)), measuredText(msm, analyse(msm)));
const hrms = fromJcamp({ title: "", kind: "ms", xUnit: "m/z", yUnit: "", first: 301.1412, last: 302.1446, y: Float64Array.of(100, 18), xs: Float64Array.of(301.1412, 302.1446), sticks: true }, 1);
const ho = spectrumObject(hrms), hb = fromSpectrumObject(ho.attrs, ho.text, ho.own, 1);
const linked = assignGroups(hb, assignRanges(assignValue(hrms, hrms.groups[0])), 9);
assert.deepEqual([linked.ids.length, linked.m.groups.length], [1, 2]);
assert.ok(Math.abs(hb.groups.find((g) => g.id === linked.ids[0])!.lo - 301.1) < 0.06);
// A range over no multiplet becomes one drawn by hand; one over a multiplet takes it.
const own = assignGroups(m, [[9.5, 9.6], [4.11, 4.13]], 900);
assert.deepEqual(own.ids, [900, q0]);
assert.ok(own.m.groups.some((g) => g.id === 900 && g.manual));
// Where ChemDraw had the spectrum is saved with the drawing; a bad place is refused.
assert.deepEqual(readMeasured(writeMeasured({ ...m, box: [1, -8, 16, -2] })).box, [1, -8, 16, -2]);
assert.throws(() => readMeasured({ ...writeMeasured(m), box: [1, 2, 3] }), /damaged/);
console.log("measured.check: ok");
