// Run: node src/stoich.check.ts. Fails loudly if the stoichiometry sums break.
import assert from "node:assert/strict";
import { keyColumns, readGrid, formatAmount, formulaWeight, parseAmount, solve } from "./stoich.ts";

const near = (a: number | undefined, b: number, what: string) => assert.ok(a !== undefined && Math.abs(a - b) < 1e-6 * Math.max(1, Math.abs(b)), `${what}: ${a} for ${b}`);
// Benzaldehyde (106.12) 1.06 g is 10 mmol and limiting; NaBH4 (37.83) at 1.5 eq is 15 mmol, 567 mg; benzyl alcohol
// (108.14) expected 10 mmol, 1.081 g; 0.973 g measured is a 90% yield.
const s = solve([
  { key: "a", mw: 106.12, product: false, typed: { mass: 1.0612 } },
  { key: "b", mw: 37.83, product: false, typed: { equiv: 1.5 } },
  { key: "p", mw: 108.14, product: true, typed: { measured: 0.97326 } },
]);
near(s.a.moles, 0.01, "limiting moles");
near(s.b.moles, 0.015, "NaBH4 moles");
near(s.b.mass, 0.015 * 37.83, "NaBH4 mass");
near(s.p.expectedMass, 1.0814, "expected mass");
near(s.p.yield, 0.9, "yield");
// A liquid by volume and density; purity counts.
const l = solve([{ key: "x", mw: 100, product: false, typed: { volume: 2, density: 0.8, purity: 0.5 } }]);
near(l.x.moles, 0.008, "moles from volume, density and purity");
// A solution by volume and molarity.
near(solve([{ key: "y", mw: 50, product: false, typed: { volume: 5, molarity: 2 } }]).y.moles, 0.01, "moles from molarity");
// Typing units, and showing them.
near(parseAmount("250 mg", "mass"), 0.25, "mg");
near(parseAmount("250", "mass"), 0.25, "bare mass is mg");
near(parseAmount("1.2", "equiv"), 1.2, "eq");
near(parseAmount("98%", "purity"), 0.98, "%");
assert.equal(parseAmount("lots", "mass"), undefined);
assert.equal(parseAmount("5 mL", "mass"), undefined, "a volume is not a mass");
assert.equal(parseAmount("1e999", "mass"), undefined, "an amount too large to be a number");
assert.equal(formatAmount(0.25, "mass"), "250 mg");
assert.equal(formatAmount(0.0125, "moles"), "12.5 mmol");
assert.equal(formatAmount(0.9, "yield"), "90.0%");
// Formulas written as text.
near(formulaWeight("H2O"), 18.015, "water");
near(formulaWeight("NaBH₄"), 22.99 + 10.81 + 4 * 1.008, "subscript digits");
near(formulaWeight("Ca(OH)2"), 40.078 + 2 * (15.999 + 1.008), "brackets");
// Each part after a dot has its own number (issue 2): CuSO4·5H2O·NH3 is CuSO4 + 5 H2O + NH3.
const cuso4 = 63.546 + 32.06 + 4 * 15.999, water = 2 * 1.008 + 15.999, ammonia = 14.007 + 3 * 1.008;
near(formulaWeight("CuSO4·5H2O"), cuso4 + 5 * water, "a hydrate");
near(formulaWeight("CuSO4.5H2O"), cuso4 + 5 * water, "a hydrate with a full stop");
near(formulaWeight("CuSO4·5H2O·NH3"), cuso4 + 5 * water + ammonia, "two dots");
near(formulaWeight("CuSO4·5H2O"), 63.546 + 32.06 + 4 * 15.999 + 5 * 18.015, "hydrate");
assert.equal(formulaWeight("THF"), undefined, "an abbreviation is not a formula");
// A product's equivalents are its coefficient: two moles of product for each mole of the limiting reactant.
{
  const two = solve([{ key: "r", mw: 100, product: false, typed: { moles: 0.01 } }, { key: "p", mw: 50, product: true, typed: { equiv: 2, measured: 0.5 } }]);
  near(two.p.expectedMoles, 0.02, "two equivalents of product");
  near(two.p.expectedMass, 1, "their mass");
  near(two.p.yield, 0.5, "the yield against them");
}
// Columns keyed by compound (CH-22): typed values stay with their compound when a structure is added in front, follow
// by order a compound that was redrawn, and come from a grid saved with "r0", "p0" keys.
{
  const col = (product: boolean, what: string) => ({ product, what });
  const first = keyColumns([col(false, "C7H6O"), col(false, '"NaBH4"'), col(true, "C7H8O")], { "r:C7H6O": { mass: 1 }, 'r:"NaBH4"': { equiv: 1.5 } }, "r:C7H6O");
  assert.deepEqual(first.cols.map((c) => c.key), ["r:C7H6O", 'r:"NaBH4"', "p:C7H8O"]);
  const added = keyColumns([col(false, "C2H6"), col(false, "C7H6O"), col(false, '"NaBH4"'), col(true, "C7H8O")], { "r:C7H6O": { mass: 1 }, 'r:"NaBH4"': { equiv: 1.5 } }, "r:C7H6O");
  assert.deepEqual(added.cols.map((c) => c.typed), [{}, { mass: 1 }, { equiv: 1.5 }, {}], "a structure added in front takes nothing");
  assert.equal(added.limiting, "r:C7H6O");
  const redrawn = keyColumns([col(false, "C8H8O"), col(false, '"NaBH4"'), col(true, "C8H10O")], { "r:C7H6O": { mass: 1 }, 'r:"NaBH4"': { equiv: 1.5 }, "p:C7H8O": { measured: 0.9 } }, "r:C7H6O");
  assert.deepEqual(redrawn.cols.map((c) => c.typed), [{ mass: 1 }, { equiv: 1.5 }, { measured: 0.9 }], "a redrawn compound keeps its values by order");
  assert.equal(redrawn.limiting, "r:C8H8O");
  const old = keyColumns([col(false, "C7H6O"), col(false, "BH4Na"), col(true, "C7H8O")], { r0: { mass: 1 }, r1: { equiv: 1.5 }, p0: { measured: 0.9 } }, "r1");
  assert.deepEqual(old.cols.map((c) => c.typed), [{ mass: 1 }, { equiv: 1.5 }, { measured: 0.9 }], "a grid from before keys named compounds");
  assert.equal(old.limiting, "r:BH4Na");
  const twins = keyColumns([col(false, "C7H6O"), col(false, "C7H6O")], {});
  assert.deepEqual(twins.cols.map((c) => c.key), ["r:C7H6O", "r:C7H6O#2"]);
  // A saved grid read as a hostile file is.
  assert.ok(readGrid({ typed: { "r:C7H6O": { mass: 1 } }, limiting: "r:C7H6O", hidden: { rows: ["mw", "bogus"], cols: ["p:C7H8O"] }, colour: "#213C99" }, 3));
  assert.deepEqual(readGrid({ typed: {}, hidden: { rows: ["mw", "bogus"] } }, 3)?.hidden, { rows: ["mw"] });
  assert.equal(readGrid({ typed: { "r:x": { mass: -1 } } }, 3), undefined, "a negative amount");
  assert.equal(readGrid({ typed: { "x\ny": { mass: 1 } } }, 3), undefined, "a key with a line break");
  assert.equal(readGrid({ typed: {}, limiting: "p:C7H8O" }, 3), undefined, "a product cannot be limiting");
}
console.log("stoich.check: ok");
