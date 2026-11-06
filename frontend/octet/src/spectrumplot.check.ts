// Run: node src/spectrumplot.check.ts. Fails loudly if the spectrum figure (Add to drawing > Spectrum) goes wrong.
import assert from "node:assert/strict";
import type { Prediction } from "./nmr.ts";
import { fullRange, lines, solventPeaks, spectrumFigure, spread, ticks } from "./spectrumplot.ts";

// Ethyl acetate's ¹H prediction, roughly: a quartet, a singlet and a triplet.
const h1: Prediction = { nucleus: "1H", signals: [
  { atoms: [1], shift: 4.12, nuclei: 2, couplings: [{ j: 7, n: 3 }], sd: 0.05, based: 20, level: 5 },
  { atoms: [3], shift: 2.05, nuclei: 3, couplings: [], sd: 0.03, based: 40, level: 6 },
  { atoms: [0], shift: 1.26, nuclei: 3, couplings: [{ j: 7, n: 2 }], sd: 0.04, based: 30, level: 5 },
] };
const fig = spectrumFigure({ prediction: h1, nucleus: "1H", mhz: 400, solvent: "CDCl₃", solventPeaks: true, range: fullRange(h1, "1H"), colours: [undefined, "#2F6FED", undefined], width: 14, height: 3.5, em: 0.55 });
// The axis first, along y = 0 for the whole width.
assert.deepEqual(fig.lines[0], { from: [0, 0], to: [14, 0] });
// One trace for the compound and one, grey, for the solvent; every point inside the box, the tallest at the top.
assert.equal(fig.curves.length, 2);
const trace = fig.curves.find((c) => !c.grey)!;
assert.equal(trace.points.length, 601);
assert.ok(trace.points.every(([x, y]) => x >= 0 && x <= 14 && y >= 0 && y <= 3.5 + 1e-9));
assert.ok(Math.abs(Math.max(...fig.curves.flatMap((c) => c.points.map((q) => q[1]))) - 3.5) < 1e-9);
// High shifts on the left: the quartet's label is left of the triplet's.
const label = (t: string) => fig.texts.find((x) => x.text === t)!;
assert.ok(label("4.12").at[0] < label("1.26").at[0]);
assert.equal(label("q, 2H").at[0], label("4.12").at[0]);
// A coloured peak keeps its colour in its label; the solvent is named in grey; ppm sits at the right end.
assert.equal(label("2.05").colour, "#2F6FED");
assert.equal(label("CDCl₃").grey, true);
assert.equal(label("ppm").align, "right");
// Labels clear of each other, and above the tallest peak.
const shifts = ["4.12", "2.05", "1.26"].map(label);
assert.ok(shifts.every((t) => t.at[1] > 3.5));
// Ticks every whole ppm from 0 to 10 (none outside the range).
const tickTexts = fig.texts.filter((t) => t.size === 0.9 && t.text !== "ppm").map((t) => Number(t.text));
assert.ok(tickTexts.length >= 5 && tickTexts.every((v) => v >= 0 && v <= 10.5));

// ¹³C: sticks, no curve; a narrowed range leaves out the peaks outside it.
const c13: Prediction = { nucleus: "13C", signals: [{ atoms: [2], shift: 171, nuclei: 1, couplings: [], sd: 1, based: 9, level: 4 }, { atoms: [0], shift: 14.2, nuclei: 1, couplings: [], sd: 1, based: 9, level: 4 }] };
const narrow = spectrumFigure({ prediction: c13, nucleus: "13C", mhz: 400, solvent: "CDCl₃", solventPeaks: false, range: [0, 100], colours: [], width: 10, height: 3, em: 0.5 });
assert.equal(narrow.curves.length, 0);
assert.ok(narrow.texts.some((t) => t.text === "14.2") && !narrow.texts.some((t) => t.text === "171.0"));
assert.equal(narrow.lines.filter((l) => l.from[1] === 0 && l.to[1] === 3).length, 1);

// The panel's helpers moved here unchanged: a triplet's lines, the solvent's quintet, ticks and spread labels.
assert.deepEqual(lines(h1.signals[2], 400).map((l) => l.h), [0.75, 1.5, 0.75]);
assert.equal(solventPeaks("DMSO-d₆", "1H", 400)[0].lines.length, 5);
assert.deepEqual(ticks(0, 10, 640).out, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
// An IR range (4000 to 400 cm⁻¹) on a 480 px panel: 500 apart.
assert.deepEqual(ticks(400, 4000, 480).out, [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]);
assert.deepEqual(spread([10, 10, 10], 4, 100), [10, 14, 18]);
assert.deepEqual(spread([98, 99], 4, 100), [94, 98]);
console.log("spectrumplot.check: ok");
