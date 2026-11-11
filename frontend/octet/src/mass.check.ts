// Run: node src/mass.check.ts. Fails loudly if isotope patterns or elemental analyses break.
import assert from "node:assert/strict";
import { counts, elementalAnalysis, isotopePattern } from "./mass.ts";

assert.deepEqual(counts("C8 H9 N O2"), { C: 8, H: 9, N: 1, O: 2 });
assert.equal(counts("C8H9NO2+"), undefined);
// Paracetamol: 151.06 (100), 152.07 (about 9.7 %), 153.07 (about 0.9 %).
const para = isotopePattern("C8H9NO2")!;
assert.equal(para[0].mz.toFixed(2), "151.06");
assert.equal(para[0].rel, 100);
assert.ok(Math.abs(para[1].rel - 9.4) < 0.4 && para[1].mz.toFixed(2) === "152.07", JSON.stringify(para));
// Chlorobenzene: the 37Cl peak is about a third of the 35Cl one.
const ph = isotopePattern("C6H5Cl")!;
assert.deepEqual(ph.map((p) => Math.round(p.mz)), [112, 113, 114, 115]);
assert.ok(Math.abs(ph[2].rel - 32.5) < 1, JSON.stringify(ph));
// Dibromide: 1:2:1.
const br = isotopePattern("CH2Br2")!.filter((p) => p.rel > 10);
assert.deepEqual(br.map((p) => Math.round(p.rel / 10)), [5, 10, 5]);
// Every element with a natural abundance has a pattern (mercury's seven isotopes); one with none (technetium) has none.
assert.equal(isotopePattern("C2H6Hg")!.filter((p) => p.rel > 30).length, 5);
assert.equal(isotopePattern("C2H6Tc"), undefined);
// D and T, and a bracketed isotope, count as the pure isotope.
assert.equal(isotopePattern({ C: 1, D: 3, H: 1, O: 1 })![0].mz.toFixed(4), "35.0450");
assert.equal(isotopePattern({ "[13C]": 1, H: 4 })![0].mz.toFixed(4), "17.0347");
assert.equal(elementalAnalysis("C 63.56 H 6.00 N 9.27 O 21.17"), "C, 63.56; H, 6.00; N, 9.27; O, 21.17");
console.log("mass.check: ok");
