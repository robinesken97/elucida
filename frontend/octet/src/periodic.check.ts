// Run: node src/periodic.check.ts. Fails loudly if the Text tool's periodic table puts an element in the wrong cell, shows
// the wrong facts for one, or sends an arrow key the wrong way.
import assert from "node:assert/strict";
import { cellOf, elementFacts, stepFrom, SYMBOLS } from "./periodic.ts";

// All 118 elements, each in its own cell, none in the gap row or in the facts box (rows 1 to 3, groups 3 to 12).
assert.equal(SYMBOLS.length, 118);
assert.equal(SYMBOLS[25], "Fe");
const cells = SYMBOLS.map((_, k) => cellOf(k + 1));
assert.equal(new Set(cells.map(String)).size, 118);
for (const [row, col] of cells) {
  assert.ok(row >= 1 && row <= 10 && row !== 8 && col >= 1 && col <= 18, `${row},${col}`);
  assert.ok(!(row <= 3 && col >= 3 && col <= 12), `${row},${col} is in the facts box`);
}
const at = (s: string) => cellOf(SYMBOLS.indexOf(s) + 1);
assert.deepEqual([at("H"), at("He"), at("Li"), at("B"), at("Ne"), at("Na"), at("Al")], [[1, 1], [1, 18], [2, 1], [2, 13], [2, 18], [3, 1], [3, 13]]);
assert.deepEqual([at("K"), at("Sc"), at("Kr"), at("Y"), at("Xe")], [[4, 1], [4, 3], [4, 18], [5, 3], [5, 18]]);
assert.deepEqual([at("Cs"), at("Ba"), at("La"), at("Lu"), at("Hf"), at("Rn")], [[6, 1], [6, 2], [9, 3], [9, 17], [6, 4], [6, 18]]);
assert.deepEqual([at("Fr"), at("Ac"), at("Lr"), at("Rf"), at("Og")], [[7, 1], [10, 3], [10, 17], [7, 4], [7, 18]]);

// Facts: from the names and NIST's isotopes. The weight is the isotopes' mean by abundance, which for some elements is
// a little off IUPAC's standard atomic weight (S is 32.065, not 32.06).
const fe = elementFacts("Fe");
assert.equal(fe.z, 26);
assert.equal(fe.name, "Iron");
assert.equal(fe.weight!.toFixed(3), "55.845");
assert.deepEqual(fe.isotopes, [[54, 5.845], [56, 91.754], [57, 2.119], [58, 0.282]]);
assert.deepEqual(["H", "C", "O", "Cl", "Br"].map((s) => elementFacts(s).weight!.toFixed(3)), ["1.008", "12.011", "15.999", "35.453", "79.904"]);
assert.deepEqual(["Al", "S", "Cs"].map((s) => elementFacts(s).name), ["Aluminium", "Sulfur", "Caesium"]);
assert.deepEqual(elementFacts("F").isotopes, [[19, 100]]);
// No natural isotopes: no weight and no isotopes, but still its number and name.
const tc = elementFacts("Tc");
assert.deepEqual([tc.z, tc.name, tc.weight, tc.isotopes], [43, "Technetium", undefined, []]);
assert.equal(elementFacts("Og").z, 118);

// Arrow keys: left and right along the atomic numbers, up and down to the nearest element there; none past an edge.
const z = (s: string) => SYMBOLS.indexOf(s) + 1, go = (s: string, key: string) => SYMBOLS[stepFrom(z(s), key)! - 1];
assert.deepEqual([go("H", "ArrowRight"), go("He", "ArrowLeft"), go("He", "ArrowRight"), go("Lu", "ArrowRight")], ["He", "H", "Li", "Hf"]);
assert.deepEqual([go("H", "ArrowDown"), go("He", "ArrowDown"), go("B", "ArrowDown"), go("Ne", "ArrowUp"), go("Rf", "ArrowDown"), go("Ce", "ArrowDown")], ["Li", "Ne", "Al", "He", "Ce", "Th"]);
assert.deepEqual([go("Fe", "ArrowDown"), go("Os", "ArrowUp"), go("La", "ArrowUp"), go("Sc", "ArrowUp")], ["Ru", "Ru", "Ra", "Mg"]);
assert.deepEqual([stepFrom(1, "ArrowLeft"), stepFrom(1, "ArrowUp"), stepFrom(118, "ArrowRight"), stepFrom(z("Lr"), "ArrowDown"), stepFrom(1, "Enter")], [undefined, undefined, undefined, undefined, undefined]);

console.log("periodic: ok");
