// Run: node src/stoich.check.ts. Fails loudly if the stoichiometry sums break.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { coefficient, conditionItems, GRID_ROW_IDS, inert, keyColumns, liquidNamed, liquidOf, readGrid, formatAmount, formulaWeight, parseAmount, reagentEquiv, reagentFormula, reagentName, solve } from "./stoich.ts";
import { LIQUIDS } from "./liquids.ts";
import { cellText, emptyRows, gridTsv, gridViews, keptGrid, movedAt, setRole, type GridDeps } from "./gridview.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { parse, serialize } from "./file.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import type { Mol } from "./render.ts";

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
near(parseAmount("250", "mass"), 250, "a bare mass is g (issue 134)");
near(parseAmount("5", "measured"), 5, "a bare measured mass is g");
near(parseAmount("250", "mass", "mg"), 0.25, "or mg, as Settings say");
for (const unit of ["g", "mg"] as const) {
  near(parseAmount("250 mg", "mass", unit), 0.25, "a typed unit wins");
  near(parseAmount("0.25 g", "mass", unit), 0.25, "a typed unit wins");
  near(parseAmount("2 kg", "mass", unit), 2000, "a typed unit wins");
  near(parseAmount("5", "moles", unit), 0.005, "moles stay in mmol");
}
assert.match(readFileSync(new URL("settings.ts", import.meta.url), "utf8"), /aromaticOnOpen: "", massUnit: "g",/, "grams is the default");
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
  // A table of rows (issue 34) is kept; any other layout reads as the columns ChemDraw's grid has.
  assert.equal(readGrid({ typed: {}, layout: "rows" }, 3)?.layout, "rows");
  for (const other of ["columns", "ROWS", 1, {}]) assert.equal(readGrid({ typed: {}, layout: other }, 3)?.layout, undefined, String(other));
  assert.ok(!("layout" in readGrid({ typed: {} }, 3)!));
}
// The layout goes through Octet's own file and through CDXML (Octet's data on the arrow), with what was typed.
{
  const m: Mol = { atoms: [], bonds: [], arrows: [{ id: 4, kind: "reaction", from: [0, 0], to: [3, 0] }], grids: [{ arrow: 4, typed: { "r:C7H6O": { mass: 1.06 } }, layout: "rows" }] };
  const opened = parse(serialize(m));
  assert.deepEqual(opened.grids, [{ arrow: opened.arrows![0].id, typed: { "r:C7H6O": { mass: 1.06 } }, layout: "rows" }]);
  const back = fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol;
  assert.deepEqual(back.grids, [{ arrow: back.arrows![0].id, typed: { "r:C7H6O": { mass: 1.06 } }, layout: "rows" }]);
  assert.equal(fromCdxml(toCdxml({ ...m, grids: [{ arrow: 4, typed: {} }] }, DEFAULT_STYLE)).mol.grids?.[0].layout, undefined, "columns stay the default");
}
// Listed densities (liquids.ts): a drawn structure by its formula, then its InChI (asked for only then); text by a name
// the list gives, or Octet's abbreviation. THF drawn and THF written both take THF's; butanone, with THF's formula,
// takes its own, and butanal none. A typed density wins over the listed one, which shows plain.
{
  const THF = "InChI=1S/C4H8O/c1-2-4-5-3-1/h1-4H2", asked: string[] = [];
  const inchi = (i: string) => () => { asked.push(i); return i; };
  assert.equal(liquidOf("C4H8O", inchi(THF))?.density, 0.8833);
  assert.equal(liquidOf("C4H8O", inchi("InChI=1S/C4H8O/c1-3-4(2)5/h3H2,1-2H3"))?.density, 0.7999, "butanone");
  assert.equal(liquidOf("C4H8O", inchi("InChI=1S/C4H8O/c1-2-3-4-5/h4H,2-3H2,1H3")), undefined, "butanal");
  asked.length = 0;
  assert.equal(liquidOf("C7H6O", inchi("x")), undefined);
  assert.deepEqual(asked, [], "no InChI asked for a formula no liquid has");
  for (const t of ["THF", "dry THF", "anhydrous THF", "tetrahydrofuran", "THF (5 mL)", "thf"]) assert.equal(liquidNamed(t)?.density, 0.8833, t);
  for (const [t, d] of [["CH2Cl2", 1.326], ["DCM", 1.326], ["MeOH", 0.791], ["Et3N", 0.728], ["H2O", 0.998], ["PhMe", 0.867], ["py", 0.982]] as const) assert.equal(liquidNamed(t)?.density, d, t);
  for (const t of ["NaBH4", "K2CO3", "reflux", "toluene/EtOH", "constructor", "__proto__"]) assert.equal(liquidNamed(t), undefined, t);
  // The list: each name names one liquid, each InChI is one, and every density is a liquid's.
  const names = LIQUIDS.flatMap((l) => l.names.map((n) => n.toLowerCase()));
  assert.equal(new Set(names).size, names.length, "a name names one liquid");
  assert.equal(new Set(LIQUIDS.map((l) => l.inchi)).size, LIQUIDS.length);
  assert.ok(LIQUIDS.length >= 40 && LIQUIDS.every((l) => l.density > 0.5 && l.density < 3 && /^InChI=1S\//.test(l.inchi)));
  // 5 mL of THF (72.11) at its listed density is 4.42 g, 61.2 mmol; a density typed wins.
  const thf = (typed: object) => solve([{ key: "r:A", mw: 100, product: false, typed: { moles: 0.001 } }, { key: "r:T", mw: 72.11, product: false, typed: { volume: 5, ...typed }, density: 0.8833 }])["r:T"];
  near(thf({}).mass, 5 * 0.8833, "THF's mass from its listed density");
  near(thf({}).density, 0.8833, "the listed density shows");
  near(thf({ density: 1 }).mass, 5, "a typed density wins");
}
// The fields added after 1.1.2 (roles, taken, conc, conditions, step) are each read alone: a bad one is left out and
// the grid kept. They go through Octet's file and CDXML, and none is inside typed, where Octet 1.1.1 calls a grid
// damaged for a field it does not know (1.1.1 reads the rest of the grid and leaves them out).
{
  const full = { typed: { "r:A": { mass: 1 } }, roles: { 'r:"THF"': "solvent" as const, "r:B": "catalyst" as const }, taken: { "r:A": "mass" as const }, conc: 0.1, conditions: { temperature: "0 °C", atmosphere: "N2" }, step: true as const, at: [1.5, -2.25] as [number, number] };
  assert.deepEqual(readGrid(full, 3), { arrow: 3, ...full });
  assert.deepEqual(readGrid({ typed: {}, roles: {} }, 3)?.roles, {}, "a new table's roles, empty, are kept");
  const many = Object.fromEntries(Array.from({ length: 61 }, (_, k) => [`r${k}`, "reactant"]));
  for (const [field, bad] of [["roles", { "p:C": "solvent" }], ["roles", { "r:A": "oxidant" }], ["roles", ["solvent"]], ["roles", many], ["roles", { __proto__: "solvent" }], ["taken", { "r:A": "moles" }], ["taken", { "p:C": "mass" }],
    ["conc", 0], ["conc", -1], ["conc", 1001], ["conc", Infinity], ["conc", "0.1"], ["conditions", { colour: "red" }], ["conditions", { time: 5 }], ["conditions", "2 h"], ["step", 1], ["step", "true"], ["at", [1]], ["at", [1, "2"]], ["at", [Infinity, 0]], ["at", [1e5, 0]], ["at", "1,2"]] as const) {
    const g = readGrid({ typed: { "r:A": { mass: 1 } }, [field]: field === "roles" && "__proto__" in (bad as object) ? JSON.parse('{"__proto__":"solvent"}') : bad }, 3);
    assert.ok(g && !(field in g), `${field}: ${JSON.stringify(bad)} left out`);
    assert.deepEqual(g.typed, { "r:A": { mass: 1 } }, "and the grid kept");
  }
  assert.deepEqual(readGrid({ typed: {}, conditions: { other: "x".repeat(5000), time: "2\nh" } }, 3)?.conditions, { other: "x".repeat(200), time: "2 h" }, "each condition one line of 200 at most");
  const m: Mol = { atoms: [], bonds: [], arrows: [{ id: 4, kind: "reaction", from: [0, 0], to: [3, 0] }], grids: [{ arrow: 4, ...full }] };
  for (const g of [parse(serialize(m)).grids![0], fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol.grids![0]]) { const { arrow: _, ...rest } = g; assert.deepEqual(rest, full); }
  const saved = JSON.parse(serialize(m)).grids[0] as { typed: Record<string, object> };
  assert.ok(Object.values(saved.typed).every((t) => Object.keys(t).every((f) => ["mass", "moles", "equiv", "volume", "density", "molarity", "purity", "measured"].includes(f))), "typed holds only 1.1.1's fields");
}
// The editor lays out a table of rows from the same sums (solve) as the columns, with the reagents and the products in
// sections of their own, and Hide row hides what shows as a row.
{
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  // The layout itself is gridview.ts, which the editor and a host with no window share.
  const grid = readFileSync(new URL("gridview.ts", import.meta.url), "utf8");
  assert.match(grid, /if \(g\.layout === "rows"\) \{/);
  assert.match(grid, /\[\[false, "Reagents"\], \[true, "Products"\]\]/);
  assert.match(editor, /gridViewsOf\(m, \{/);
  assert.match(editor, /if \(what === "layout"\) return changeGrid\(arrow, \(g\) => \(\{ layout: g\.layout \? undefined : "rows" \}\)\);/);
  assert.match(editor, /hideKey = what === \(rowsLayout \? "hide\.row" : "hide\.col"\)/);
  assert.match(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /context\.rows \? "Show as columns" : "Show as rows", "grid\.layout"/);
  // Hide empty rows (as rows, Hide empty columns): the empty rows join the hidden ones, which Show all brings back.
  assert.match(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /context\.rows \? "Hide empty columns" : "Hide empty rows", "grid\.hide\.empty"/);
  assert.match(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /"Copy table", "grid\.copy"/);
  // Each role from the Actions panel and the right-click menu; a double-click on Role goes to the next one.
  assert.match(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /"Set as reactant", "grid\.role\.reactant"[\s\S]*"Set as catalyst", "grid\.role\.catalyst"[\s\S]*"Set as solvent", "grid\.role\.solvent"/);
  assert.match(editor, /if \(role\) return changeGrid\(arrow, \(g, v\) => setRole\(g, v, key, role\)\);/);
  assert.match(editor, /ROLES\[\(ROLES\.indexOf\(gcol\?\.role \?\? "reactant"\) \+ 1\) % ROLES\.length\]/);
  assert.match(editor, /\{ arrow, typed: \{\}, roles: \{\} \}/, "Analyse stoichiometry makes a table with roles");
  // Typing a reactant's mass or volume marks it (as Reactio Draw does); Mark as measured moves the mark, Clear takes it off.
  assert.match(editor, /if \(field === "mass" \|\| field === "volume"\) return \{ taken: \{ \.\.\.rest, \[w\.key\]: field \} \};/);
  assert.match(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /"Mark as measured", "grid\.taken"[\s\S]*"Clear measured mark", "grid\.untaken"/);
  assert.match(readFileSync(new URL("editor.css", import.meta.url), "utf8"), /\.stoich text\.taken \{\n  fill: var\(--error\);\n\}\n\.stoich line\.taken \{\n  stroke: var\(--error\);\n\}/, "the brand's red, as the page's theme gives it");
  // Conditions…: a dialog of the four, where an experiment page's first table keeps Temperature and Time in the page's details.
  assert.match(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /"Conditions…", "grid\.conditions"/);
  assert.match(editor, /<Dialog title="Conditions" action="Save"/);
  assert.match(editor, /withDetails\(doc\.annotations, \{ \.\.\.detailsOf\(doc\.annotations\), temperature: value\("temperature"\), time: value\("time"\) \}\)/);
  assert.match(editor, /if \(what === "copy"\) \{ const v = gridViews\.find\(\(x\) => x\.arrow === arrow\), c = v && conditionsOf\(v\); return v && copyPlain\(gridTsv\(v, CONDITIONS/, "with the conditions, the page's Temperature and Time too");
  assert.match(editor, /if \(what === "hide\.empty"\) return changeGrid\(arrow, \(g, v\) => \(\{ hidden: \{ \.\.\.g\.hidden, rows: \[\.\.\.\(g\.hidden\?\.rows \?\? \[\]\), \.\.\.emptyRows\(v\)\] \} \}\)\);/);
}
// A line of conditions splits at commas outside brackets; the atmosphere's gas is not a reagent.
assert.deepEqual(conditionItems("toluene/EtOH/H2O (4:1:1, 30 mL), 80 °C; 12 h"), ["toluene/EtOH/H2O (4:1:1, 30 mL)", "80 °C", "12 h"]);
for (const gas of ["N2", "Ar", "argon", "air", "under N2"]) assert.ok(inert(gas), gas);
for (const reagent of ["H2", "O2", "CO", "NH3"]) assert.ok(!inert(reagent), reagent);
// Issue 131: the equivalents a reagent's text gives fill in its Equivalents (plain) until a value is typed.
for (const [text, want] of [["K2CO3 (2 eq.)", 2], ["K2CO3 (2 equiv)", 2], ["1.5 equiv NaBH4", 1.5], ["Pd(PPh3)4 (5 mol%)", 0.05], ["cat. H2SO4", undefined], ["1 M NaOH", undefined], ["K2CO3", undefined]] as const) assert.equal(reagentEquiv(text), want, text);
{
  const r = (key: string, typed: object, given?: number) => ({ key, mw: 100, product: false, typed, given });
  near(solve([r("a", { moles: 0.01 }), r("k", {}, 2)]).k.moles, 0.02, "K2CO3 (2 eq.)");
  near(solve([r("a", { moles: 0.01 }), r("k", {}, 2)]).k.equiv, 2, "its equivalents shown");
  assert.equal(solve([r("a", {}), r("k", {}, 2)]).k.equiv, 2, "shown before any amount is typed");
  near(solve([r("a", { moles: 0.01 }), r("k", { equiv: 3 }, 2)]).k.moles, 0.03, "a value typed wins");
  near(solve([r("a", {}), r("k", { mass: 2 }, 2)]).a.moles, 0.01, "a reagent's amount over its equivalents sets the scale");
}
// Issue 132: a charge at the end of a formula (+, -, −, 2+, raised) is read as a charge, its mass the formula's, and
// the formula shows it raised; proton, hydroxide, hydronium, hydride and water read as their formulas.
{
  const none = () => undefined, read = (t: string) => reagentFormula(t, none, none, none);
  for (const [text, formula, mass] of [["H+", "H⁺", 1.008], ["H⁺", "H⁺", 1.008], ["OH-", "OH⁻", 17.007], ["OH−", "OH⁻", 17.007], ["OH⁻", "OH⁻", 17.007], ["HO-", "HO⁻", 17.007],
    ["H3O+", "H3O⁺", 19.023], ["NH4+", "NH4⁺", 18.039], ["Na+", "Na⁺", 22.99], ["Cl⁻", "Cl⁻", 35.45], ["Cu2+", "Cu²⁺", 63.546], ["Fe³⁺", "Fe³⁺", 55.845], ["SO42−", "SO4²⁻", 96.056],
    ["SO4 2-", "SO4²⁻", 96.056], ["SO4²⁻", "SO4²⁻", 96.056], ["proton", "H⁺", 1.008], ["Proton", "H⁺", 1.008], ["hydroxide", "OH⁻", 17.007], ["hydronium", "H3O⁺", 19.023],
    ["hydride", "H⁻", 1.008], ["water", "H2O", 18.015]] as const) {
    assert.equal(read(text)?.formula, formula, text);
    near(read(text)?.weight, mass, text);
  }
  for (const text of ["+", "2+", "-", "e-"]) assert.equal(read(text), undefined, text);
  assert.equal(read("K2CO3")?.formula, "K2CO3", "a formula with no charge is as written");
  assert.equal(read("SO4^2-")?.formula, "SO4²⁻");
  // Text in a file is hostile: "constructor" is a word like any other, and long text reads in time linear in its length.
  for (const text of ["constructor", "__proto__"]) assert.equal(reagentFormula(text, (t) => t.trim() && undefined, none, none), undefined, text);
  const t0 = performance.now();
  for (const text of [`a${" ".repeat(1998)}x+`, `a${"1".repeat(1998)}x+`, "1".repeat(2000)]) { read(text); reagentEquiv(text); }
  assert.ok(performance.now() - t0 < 150, `long text read in ${performance.now() - t0} ms`);
}
// Issue 133: a coefficient in the scheme sets equivalents, relative to the limiting reactant's coefficient, products
// too; a number on its own before a structure has no column; a value typed wins; over the arrow "2 HCl" is 2 eq.
{
  assert.deepEqual(coefficient("2 HCl"), ["HCl", 2]);
  assert.deepEqual(coefficient("0.5 H2"), ["H2", 0.5]);
  assert.deepEqual(coefficient("2"), ["", 2]);
  for (const t of ["1,4-dioxane", "2a", "H2"]) assert.deepEqual(coefficient(t), [t, undefined], t);
  for (const t of ["1/2 O2", "½ O2", "1 / 2 O2"]) assert.deepEqual(coefficient(t), ["O2", 0.5], t);
  assert.deepEqual(coefficient("¾"), ["", 0.75]);
  assert.deepEqual(coefficient("1/0 O2"), ["O2", undefined], "no number");
  // A row: text and structures (atoms 0, 1, 2...), plus signs and one arrow (id 9); each structure is "S" and its atom.
  type Item = string | number | "+" | "→";
  const grid = (row: Item[], typed: object, limiting?: string, above: string[] = [], carried?: { atom: number; box: number[] }, more: object = {}) => {
    const captions: { id: number; text: string; x: number; y: number }[] = [];
    let x = 0;
    const steps = row.map((it) => {
      const box = [x, -0.5, x + 1, 0.5]; x += 1.5;
      if (it === "→") return { kind: "arrow", id: 9, box };
      if (it === "+") return { kind: "plus", id: 100 + x, box };
      if (typeof it === "number") return { kind: "structure", atoms: [it], box, ...(carried?.atom === it ? { carry: { captions: [50], atoms: [], arrows: [], shapes: [], ends: [], boxes: [] } } : {}) };
      captions.push({ id: captions.length + 1, text: it, x: 0, y: 0 });
      return { kind: "text", id: captions.length, box };
    });
    const conditions = above.map((text, k) => { captions.push({ id: 200 + k, text, x: 0, y: 0 }); return { kind: "text", id: 200 + k, box: [5, 1, 6, 2] }; });
    if (carried) captions.push({ id: 50, text: "2", x: 0, y: 0 });
    const at = steps.findIndex((s) => s.kind === "arrow"), parts = (l: typeof steps) => l.filter((s) => s.kind === "structure" || s.kind === "text");
    const m = { atoms: [], bonds: [], captions, arrows: [{ id: 9, kind: "reaction", from: [0, 0], to: [1, 0] }], grids: [{ arrow: 9, typed, limiting, ...more }] } as unknown as Mol;
    const deps: GridDeps = {
      reaction: () => ({ steps, arrows: [9], atoms: [], captions: [], carried: [], conditions: new Map() }) as never,
      steps: (r) => [{ arrow: 9, reactants: parts(r.steps.slice(0, at)), products: parts(r.steps.slice(at + 1)), above: conditions, below: [] }] as never,
      structure: (atoms) => ({ formula: `S${atoms[0]}`, weight: 100 }), reagent: (t) => (/HCl|H2|THF/.test(t) ? { formula: "X", weight: 36 } : undefined),
      captionBox: (id) => (id === 50 && carried ? carried.box : undefined) as never, nameWidth: (t) => t.length * 0.2, captionSize: 10, perPt: 0.05, experiment: !!(more as { experiment?: boolean }).experiment,
    };
    const v = gridViews(m, deps)[0];
    return { v, keys: v.all.map((c) => c.key), rows: v.rows.map((row) => row.id), at: (key: string) => v.solved[key] };
  };
  // 2 A + B → C, B limiting at 10 mmol: 20 mmol of A at 2 eq., 10 mmol of C. The 2 has no column.
  const bLim = grid(["2", 0, "+", 1, "→", 2], { "r:S1": { moles: 0.01 } }, "r:S1");
  assert.deepEqual(bLim.keys, ["r:S0", "r:S1", "p:S2"]);
  near(bLim.at("r:S0").moles, 0.02, "two of A");
  near(bLim.at("r:S0").equiv, 2, "A at 2 eq.");
  near(bLim.at("p:S2").expectedMoles, 0.01, "one of C");
  // A limiting at 20 mmol: B is 0.5 eq. (10 mmol), C 0.5 eq. (10 mmol).
  const aLim = grid(["2", 0, "+", 1, "→", 2], { "r:S0": { moles: 0.02 } }, "r:S0");
  near(aLim.at("r:S0").equiv, 1, "the limiting reactant is 1 eq.");
  near(aLim.at("r:S1").moles, 0.01, "half as much B");
  near(aLim.at("p:S2").expectedMoles, 0.01, "half as much C");
  // A → 2 B: twice the moles of product.
  near(grid([0, "→", "2", 1], { "r:S0": { moles: 0.01 } }).at("p:S1").expectedMoles, 0.02, "A → 2 B");
  // A value typed wins: A typed at 3 eq.
  near(grid(["2", 0, "+", 1, "→", 2], { "r:S1": { moles: 0.01 }, "r:S0": { equiv: 3 } }, "r:S1").at("r:S0").moles, 0.03, "typed equivalents win");
  // Written in the reagent's text: 2 HCl and 0.5 H2 in the row.
  const text = grid([0, "+", "2 HCl", "+", "0.5 H2", "→", 1], { "r:S0": { moles: 0.01 } });
  near(text.at('r:"2 HCl"').moles, 0.02, "2 HCl");
  near(text.at('r:"0.5 H2"').moles, 0.005, "0.5 H2");
  // Over the arrow, 2 HCl is 2 eq. of the limiting reactant, whatever its coefficient; a reagent there without one is 1 eq.
  const side = grid(["2", 0, "→", 1], { "r:S0": { moles: 0.02 } }, undefined, ["2 HCl", "H2"]);
  near(side.at('r:"2 HCl"').moles, 0.04, "2 HCl over the arrow");
  near(side.at('r:"H2"').moles, 0.02, "H2 over the arrow");
  // A number a structure carries on its left (typed close to it) is its coefficient too.
  near(grid([0, "+", 1, "→", 2], { "r:S1": { moles: 0.01 } }, "r:S1", [], { atom: 0, box: [-0.4, -0.2, -0.1, 0.2] }).at("r:S0").moles, 0.02, "a carried 2");
  // A fraction is a coefficient too: ½ before a structure, 1/2 H2 in the row.
  near(grid(["½", 0, "+", 1, "→", 2], { "r:S1": { moles: 0.01 } }, "r:S1").at("r:S0").moles, 0.005, "½ A");
  near(grid([0, "+", "1/2 H2", "→", 1], { "r:S0": { moles: 0.01 } }).at('r:"1/2 H2"').moles, 0.005, "1/2 H2");
  // A number with a plus sign after it is not a coefficient; with none written, nothing changes.
  assert.ok(grid(["2", "+", 0, "→", 1], {}).keys.includes('r:"2"'), "2 + A");
  assert.equal(grid([0, "+", 1, "→", 2], { "r:S0": { moles: 0.01 } }).at("r:S1").equiv, 1);
  assert.equal(grid([0, "+", 1, "→", 2], {}).at("r:S1").equiv, undefined, "no equivalents shown where none are given");
  // Issue 135: Volume and Density always show for reactants, Molarity and Purity once used; a density typed gives the
  // volume to measure out (B at 2 eq. of 10 mmol, MW 100, 0.8 g/mL: 2 g, 2.5 mL).
  assert.deepEqual(grid([0, "→", 1], {}).rows.filter((id) => ["volume", "density", "molarity", "purity"].includes(id)), ["volume", "density"]);
  assert.ok(grid([0, "→", 1], { "r:S0": { molarity: 1 } }).rows.includes("molarity"));
  const liquid = grid([0, "+", 1, "→", 2], { "r:S0": { moles: 0.01 }, "r:S1": { equiv: 2, density: 0.8 } });
  near(liquid.at("r:S1").mass, 2, "its mass");
  near(liquid.at("r:S1").volume, 2.5, "its volume");
  // Hide empty rows: an empty table keeps Formula, MW and Limiting?, and Equivalents for the product's 1.00 (as
  // ChemDraw's product column has it). Show all brings the rest back (it clears hidden).
  const empty = grid([0, "→", 1], {});
  assert.deepEqual(empty.rows.filter((id) => !emptyRows(empty.v).includes(id)), ["formula", "mw", "limiting", "equiv"]);
  assert.equal(cellText(empty.v, empty.v.cols[1], empty.v.rows.find((row) => row.id === "equiv")!).text, "1.00");
  assert.ok(!emptyRows(liquid.v).includes("volume") && emptyRows(liquid.v).includes("yield"), "a row with a value stays");
  // Roles. A table Octet makes now (roles set, even empty) starts a known solvent as Solvent; an older one (no roles)
  // keeps every column a reactant. Role shows once a column is not a reactant, Concentration once one is a solvent.
  const older = grid([0, "→", 1], { "r:S0": { moles: 0.001 } }, "r:S0", ["THF"]), newer = grid([0, "→", 1], { "r:S0": { moles: 0.001 } }, "r:S0", ["THF"], undefined, { roles: {} });
  assert.equal(older.v.all.find((c) => c.key === 'r:"THF"')!.role, "reactant");
  assert.ok(!older.rows.includes("role") && !older.rows.includes("conc"));
  near(older.at('r:"THF"').moles, 0.001, "an older table's THF is a reactant at 1 eq.");
  assert.equal(newer.v.all.find((c) => c.key === 'r:"THF"')!.role, "solvent");
  assert.deepEqual(newer.rows.filter((id) => id === "role" || id === "conc"), ["role", "conc"]);
  assert.equal(newer.at('r:"THF"').moles, undefined, "a solvent has no equivalents until some are typed");
  const role = (v: typeof newer.v, key: string) => cellText(v, v.cols.find((c) => c.key === key)!, v.rows.find((r) => r.id === "role")!).text;
  assert.deepEqual([role(newer.v, "r:S0"), role(newer.v, 'r:"THF"'), role(newer.v, "p:S1")], ["Reactant", "Solvent", "Product"]);
  // A known solvent starts as one only over or under the arrow: benzene written in the equation is what reacts. Water
  // over the arrow is a solvent.
  const placed = grid(["benzene", "+", 0, "→", 1], { "r:S0": { moles: 0.001 } }, "r:S0", ["H2O"], undefined, { roles: {} });
  assert.deepEqual(placed.v.all.filter((c) => !c.product).map((c) => [c.key, c.role]), [['r:"benzene"', "reactant"], ["r:S0", "reactant"], ['r:"H2O"', "solvent"]]);
  // Set as catalyst on an older table: that column changes, and THF stays a reactant.
  const changed = setRole({ arrow: 9, typed: {} }, older.v, "r:S0", "catalyst");
  assert.deepEqual(changed.roles, { 'r:"THF"': "reactant", "r:S0": "catalyst" });
  // A solvent set as limiting is not: the first reactant is.
  assert.equal(grid([0, "→", 1], {}, 'r:"THF"', ["THF"], undefined, { roles: {} }).v.limiting, "r:S0");
  // Nor is a catalyst (the column was limiting before it was made one): 5 mol% is of the reactant.
  const catLim = grid([0, "+", 1, "→", 2], { "r:S0": { moles: 0.01 }, "r:S1": { equiv: 0.05 } }, "r:S1", [], undefined, { roles: { "r:S1": "catalyst" } });
  assert.equal(catLim.v.limiting, "r:S0");
  near(catLim.at("r:S1").moles, 0.0005, "5 mol% of 10 mmol");
  // A compound redrawn keeps its role and its mark, as it keeps its values (by order: keyColumns).
  const redrawnGrid = { arrow: 9, typed: { "r:S0": { moles: 0.01 }, "r:S7": { mass: 0.1 } }, roles: { "r:S7": "catalyst" as const }, taken: { "r:S7": "mass" as const } };
  const redrawn = grid([0, "+", 1, "→", 2], redrawnGrid.typed, "r:S0", [], undefined, { roles: redrawnGrid.roles, taken: redrawnGrid.taken });
  assert.equal(redrawn.v.all.find((c) => c.key === "r:S1")!.role, "catalyst");
  assert.deepEqual(cellText(redrawn.v, redrawn.v.cols[1], redrawn.v.rows.find((r) => r.id === "mass")!), { text: "100 mg", typed: true, taken: true });
  const keptRedrawn = keptGrid(redrawnGrid, redrawn.v);
  assert.deepEqual([keptRedrawn.roles, keptRedrawn.taken], [{ "r:S1": "catalyst" }, { "r:S1": "mass" }]);
  // 1 mmol in 5 mL of THF is 0.20 M; 0.1 M typed gives 10 mL; a catalyst's 0.05 eq. is 5.00 mol%.
  const conc = (more: object, thf: object = {}) => grid([0, "→", 1], { "r:S0": { moles: 0.001 }, 'r:"THF"': thf }, "r:S0", ["THF"], undefined, { roles: {}, ...more });
  const five = conc({}, { volume: 5 }), thfKey = 'r:"THF"';
  near(five.at(thfKey).conc, 0.2, "1 mmol in 5 mL");
  assert.deepEqual(cellText(five.v, five.v.cols.find((c) => c.key === thfKey)!, five.v.rows.find((r) => r.id === "conc")!), { text: "0.20 M", typed: false });
  const typedConc = conc({ conc: 0.1 });
  near(typedConc.at(thfKey).volume, 10, "0.1 M gives 10 mL");
  near(typedConc.at(thfKey).mass, 10 * 0.8833, "and its mass from THF's density");
  assert.equal(cellText(typedConc.v, typedConc.v.cols.find((c) => c.key === thfKey)!, typedConc.v.rows.find((r) => r.id === "conc")!).typed, true);
  near(conc({ conc: 0.1 }, { volume: 4 }).at(thfKey).conc, 0.25, "with every solvent's volume typed, the concentration is worked out");
  // Bold only while it is the one typed: worked out from every solvent's volume, it is plain; before an amount gives
  // it, the one typed shows.
  const concCell = (g: typeof five) => cellText(g.v, g.v.cols.find((c) => c.key === thfKey)!, g.v.rows.find((r) => r.id === "conc")!);
  assert.deepEqual(concCell(conc({ conc: 0.1 }, { volume: 4 })), { text: "0.25 M", typed: false });
  assert.deepEqual(concCell(grid([0, "→", 1], {}, "r:S0", ["THF"], undefined, { roles: {}, conc: 0.1 })), { text: "0.10 M", typed: true });
  const cat = grid([0, "→", 1], { "r:S0": { moles: 0.01 }, 'r:"HCl"': { equiv: 0.05 } }, "r:S0", ["HCl"], undefined, { roles: { 'r:"HCl"': "catalyst" } });
  assert.deepEqual(cellText(cat.v, cat.v.cols.find((c) => c.key === 'r:"HCl"')!, cat.v.rows.find((r) => r.id === "equiv")!), { text: "5.00 mol%", typed: true });
  near(cat.at('r:"HCl"').moles, 0.0005, "5 mol% of 10 mmol");
  assert.equal(formatAmount(0.05, "mol%"), "5.00 mol%");
  near(parseAmount("5 mol%", "equiv"), 0.05, "mol% typed");
  // The amount measured out (Grid.taken): a reactant's Mass or Volume, drawn red and underlined (Editor.tsx takenLine).
  // A change keeps marks and roles only for the columns the grid has, so neither grows past what readGrid reads.
  const measured = grid([0, "→", 1], { "r:S0": { volume: 2, density: 1 } }, "r:S0", [], undefined, { taken: { "r:S0": "volume", "r:gone": "mass" }, roles: { "r:gone": "solvent" } });
  const cell = (id: string) => cellText(measured.v, measured.v.cols[0], measured.v.rows.find((r) => r.id === id)!);
  assert.deepEqual(cell("volume"), { text: "2.00 mL", typed: true, taken: true });
  assert.deepEqual(cell("mass"), { text: "2.00 g", typed: false });
  const kept = keptGrid({ arrow: 9, typed: { "r:S0": { volume: 2, density: 1 } }, taken: { "r:S0": "volume", "r:gone": "mass" }, roles: { "r:gone": "solvent" } }, measured.v);
  assert.deepEqual([kept.taken, kept.roles], [{ "r:S0": "volume" }, {}]);
  const marked: Mol = { atoms: [], bonds: [], arrows: [{ id: 4, kind: "reaction", from: [0, 0], to: [3, 0] }], grids: [{ arrow: 4, typed: { "r:A": { volume: 2 } }, taken: { "r:A": "volume" } }] };
  for (const g of [parse(serialize(marked)).grids![0], fromCdxml(toCdxml(marked, DEFAULT_STYLE)).mol.grids![0]]) assert.deepEqual(g.taken, { "r:A": "volume" }, "a mark on Volume is kept");
  // The conditions block (T3): right of the table, clear of its last column, a line for each condition with a value,
  // in the order Temperature, Time, Atmosphere, Other. On an experiment page the first table leaves out Temperature and
  // Time (the page's details show them). Copy table puts the lines after the table.
  const conditions = { other: "450 nm", temperature: "0 °C", atmosphere: "N2" };
  const blocked = grid([0, "→", 1], {}, undefined, [], undefined, { conditions }), b = blocked.v.block!;
  assert.deepEqual(b.lines.map((l) => [l.name, l.value]), [["Temperature", "0 °C"], ["Atmosphere", "N2"], ["Other", "450 nm"]]);
  assert.ok(b.at > Math.max(...blocked.v.cells.map((c) => c.x + c.w / 2)), "the block sits clear of the last column");
  assert.ok(b.valueAt > b.at + 0.2 * "Temperature".length && b.right > b.valueAt, "each value after the longest name");
  assert.deepEqual(b.lines.map((l) => l.y), [0, 1, 2].map((k) => blocked.v.top - k * blocked.v.rh), "a line for each row");
  assert.deepEqual(gridTsv(blocked.v).split("\n").slice(-4), ["Temperature\t0 °C", "Atmosphere\tN2", "Other\t450 nm", ""]);
  assert.equal(grid([0, "→", 1], {}).v.block, undefined, "no block with no conditions");
  const onPage = grid([0, "→", 1], {}, undefined, [], undefined, { conditions, experiment: true });
  assert.deepEqual(onPage.v.block!.lines.map((l) => l.key), ["atmosphere", "other"], "an experiment page's first table: Temperature shows once, in the page's details");
  // A listed density (THF over the arrow) shows plain: bold only when typed.
  const listedGrid = grid([0, "→", 1], { "r:S0": { moles: 0.01 } }, "r:S0", ["THF"]), thfCol = listedGrid.v.cols.find((c) => c.key === 'r:"THF"')!;
  assert.deepEqual(cellText(listedGrid.v, thfCol, listedGrid.v.rows.find((r) => r.id === "density")!), { text: "0.88 g/mL", typed: false });
  // Copy table: tab-separated, as shown. In columns, a row naming the components, then each row shown; hidden rows
  // are left out; a value a spreadsheet would run as a formula gets an apostrophe; the conditions follow.
  const named = grid(["=HYPERLINK(1)", "+", 0, "→", 1], { "r:S0": { moles: 0.01 } }, "r:S0", [], undefined, { hidden: { rows: ["density", "volume"] } });
  const tsv = gridTsv(named.v, [["Temperature", "-78 °C"], ["Other", "=1+1"]]).split("\n");
  assert.equal(tsv[0], "\t'=HYPERLINK(1)\tS0\tS1");
  assert.equal(tsv[1], "Formula\t\tS0\tS1");
  assert.equal(tsv.find((l) => l.startsWith("Moles")), "Moles\t10.0 mmol\t10.0 mmol\t");
  assert.ok(!tsv.some((l) => /^(Density|Volume)\t/.test(l)), "hidden rows are left out");
  assert.deepEqual(tsv.slice(-4), ["", "Temperature\t-78 °C", "Other\t'=1+1", ""]);
  // As rows: each section's title and quantities, then a row for each component.
  const rowsTsv = gridTsv(grid([0, "→", 1], { "r:S0": { moles: 0.01 } }, "r:S0", [], undefined, { layout: "rows" }).v).split("\n");
  assert.match(rowsTsv[0], /^Reagents\tFormula\tMW\tLimiting\?\tEquivalents\tMass\tMoles/);
  assert.match(rowsTsv[1], /^S0\tS0\t100\.00\tYes\t1\.00\t1\.00 g\t10\.0 mmol/);
  assert.ok(rowsTsv.includes("") && rowsTsv.some((l) => l.startsWith("Products\t")), "the products in a section of their own");
}
// One table for each step (T6): A → B → C with a grid on each arrow (Grid.step) gives two tables. B is a product in
// the first and a reactant in the second, with values of its own in each; the second goes under the first. B's
// Measured mass in the first gives its amount in the second, shown as worked out, and makes it limiting there. A grid
// with no step covers the whole scheme, as before, and is not drawn once the scheme has step tables.
{
  const box = (k: number) => [3 * k, -0.5, 3 * k + 1, 0.5];
  const row = [{ kind: "structure", atoms: [0], box: box(0) }, { kind: "arrow", id: 9, box: box(1) }, { kind: "structure", atoms: [1], box: box(2) }, { kind: "arrow", id: 10, box: box(3) }, { kind: "structure", atoms: [2], box: box(4) }];
  const steps = [{ arrow: 9, reactants: [row[0]], products: [row[2]], above: [], below: [] }, { arrow: 10, reactants: [row[2]], products: [row[4]], above: [], below: [] }];
  const deps: GridDeps = {
    reaction: () => ({ steps: row, arrows: [9, 10], atoms: [], captions: [], carried: [], conditions: new Map() }) as never, steps: () => steps as never,
    structure: (atoms) => ({ formula: `S${atoms[0]}`, weight: 100 + 10 * atoms[0] }), reagent: () => undefined, captionBox: () => undefined, nameWidth: () => 1, captionSize: 10, perPt: 0.05, experiment: false,
  };
  const views = (grids: Mol["grids"]) => gridViews({ atoms: [], bonds: [], arrows: [{ id: 9, kind: "reaction", from: [3, 0], to: [4, 0] }, { id: 10, kind: "reaction", from: [9, 0], to: [10, 0] }], grids } as Mol, deps);
  const two = views([{ arrow: 10, typed: { "r:S1": { purity: 0.9 } }, step: true }, { arrow: 9, typed: { "r:S0": { mass: 1 }, "p:S1": { measured: 0.55 } }, step: true }]);
  assert.deepEqual(two.map((v) => [v.arrow, v.all.map((c) => c.key)]), [[9, ["r:S0", "p:S1"]], [10, ["r:S1", "p:S2"]]], "in the scheme's order");
  near(two[0].solved["p:S1"].yield, 0.55 / 110 / (1 / 100), "step 1's yield");
  near(two[1].solved["r:S1"].moles, 0.005, "B's moles in step 2 from its Measured mass in step 1");
  near(two[1].solved["r:S1"].mass, 0.55 / 0.9, "its mass with step 2's own purity");
  assert.equal(two[1].limiting, "r:S1");
  assert.equal(cellText(two[1], two[1].cols[0], two[1].rows.find((r) => r.id === "mass")!).typed, false, "shown as worked out");
  near(two[1].solved["p:S2"].expectedMoles, 0.005, "C expected from it");
  assert.ok(two[1].top < two[0].bottom, "step 2's table under step 1's");
  assert.equal(two[0].bottom, two[0].top - two[0].rows.length * two[0].rh, "a table's foot is under its last row");
  const asRows = views([{ arrow: 9, typed: {}, step: true, layout: "rows" }, { arrow: 10, typed: {}, step: true }]);
  assert.equal(asRows[0].bottom, asRows[0].rules!.at(-1)![2], "as rows, its last rule");
  assert.ok(asRows[1].top < asRows[0].bottom);
  const allHidden = views([{ arrow: 9, typed: {}, step: true, layout: "rows", hidden: { rows: GRID_ROW_IDS } }]);
  assert.equal(allHidden[0].bottom, allHidden[0].top, "every row hidden: no rule, and the foot is the top");
  const typedB = views([{ arrow: 9, typed: { "p:S1": { measured: 0.55 } }, step: true }, { arrow: 10, typed: { "r:S1": { mass: 2 } }, step: true }]);
  near(typedB[1].solved["r:S1"].moles, 2 / 110, "a mass typed in step 2 wins");
  const whole = views([{ arrow: 9, typed: { "r:S0": { mass: 1 } } }]);
  assert.deepEqual(whole.map((v) => v.all.map((c) => c.key)), [["r:S0", "p:S2"]], "a grid without step covers the scheme");
  // A table moved on its own (Grid.at): its corner from its arrow's tail. Without at it is where it always was.
  const base = whole[0], d: [number, number] = [1, -2], at = movedAt({ arrows: [{ id: 9, kind: "reaction", from: [3, 0], to: [4, 0] }] } as Mol, base, [0, 0])!;
  assert.deepEqual(views([{ arrow: 9, typed: { "r:S0": { mass: 1 } }, at }])[0], base, "at its own place, the table is drawn as before");
  const moved = views([{ arrow: 9, typed: { "r:S0": { mass: 1 } }, at: movedAt({ arrows: [{ id: 9, kind: "reaction", from: [3, 0], to: [4, 0] }] } as Mol, base, d) }])[0];
  near(moved.start, base.start + 1, "the table moves");
  near(moved.top, base.top - 2);
  moved.cells.forEach((c, k) => { near(c.x, base.cells[k].x + 1, "each cell with it"); near(c.y, base.cells[k].y - 2); });
  assert.deepEqual(moved.solved, base.solved, "and what it says is the same");
  assert.deepEqual(row.map((s) => s.box), [box(0), box(1), box(2), box(3), box(4)], "the reaction stays where it is");
  // The reaction moved (its arrow with it) carries the table; a structure changed does not move it.
  const carriedTo = gridViews({ atoms: [], bonds: [], arrows: [{ id: 9, kind: "reaction", from: [8, 5], to: [9, 5] }, { id: 10, kind: "reaction", from: [14, 5], to: [15, 5] }], grids: [{ arrow: 9, typed: {}, at: [0, -1] }] } as Mol, deps)[0];
  const atFirst = gridViews({ atoms: [], bonds: [], arrows: [{ id: 9, kind: "reaction", from: [3, 0], to: [4, 0] }, { id: 10, kind: "reaction", from: [9, 0], to: [10, 0] }], grids: [{ arrow: 9, typed: {}, at: [0, -1] }] } as Mol, deps)[0];
  near(carriedTo.start, atFirst.start + 5, "with its arrow");
  near(carriedTo.top, atFirst.top + 5);
  const lower = row.map((s) => ({ ...s, box: [s.box[0], s.box[1] - 3, s.box[2], s.box[3]] }));
  const edited = { ...deps, reaction: () => ({ steps: lower, arrows: [9, 10], atoms: [], captions: [], carried: [], conditions: new Map() }) as never, steps: () => [{ arrow: 9, reactants: [lower[0]], products: [lower[2]], above: [], below: [] }, { arrow: 10, reactants: [lower[2]], products: [lower[4]], above: [], below: [] }] as never };
  const at3 = { atoms: [], bonds: [], arrows: [{ id: 9, kind: "reaction", from: [3, 0], to: [4, 0] }, { id: 10, kind: "reaction", from: [9, 0], to: [10, 0] }] };
  near(gridViews({ ...at3, grids: [{ arrow: 9, typed: {}, at: [0, -1] }] } as Mol, edited)[0].top, atFirst.top, "a taller structure leaves a placed table where it is");
  assert.ok(gridViews({ ...at3, grids: [{ arrow: 9, typed: {} }] } as Mol, edited)[0].top < base.top - 2, "and moves one in its own place down");
  // On an experiment page, a conditions block that would pass the Reaction scheme box's right edge goes under the table.
  const withBlock = { ...at3, grids: [{ arrow: 9, typed: {}, conditions: { atmosphere: "N2", other: "stir" } }] } as Mol, beside = gridViews(withBlock, deps)[0];
  assert.deepEqual(gridViews(withBlock, { ...deps, fit: beside.block!.right + 1 })[0], beside, "it fits: beside the table");
  const under = gridViews(withBlock, { ...deps, fit: beside.block!.right - 1 })[0];
  near(under.block!.at, beside.start, "past the edge: under the table, from its left");
  assert.ok(under.block!.right < beside.block!.right && under.block!.lines[0].y < beside.top - beside.rows.length * beside.rh, "and under its last row");
  assert.equal(under.bottom, under.block!.lines[1].y - under.rh, "the table's foot is under the block");
  // With step tables, a grid with no step on a step's arrow is that step's (an arrow drawn or added since: an experiment
  // page gives each new arrow a grid).
  assert.deepEqual(views([{ arrow: 9, typed: {} }, { arrow: 10, typed: {}, step: true }]).map((v) => v.all.map((c) => c.key)), [["r:S0", "p:S1"], ["r:S1", "p:S2"]]);
  assert.deepEqual(views([{ arrow: 9, typed: {}, step: true }, { arrow: 10, typed: { "r:S1": { mass: 2 } } }]).map((v) => v.all.map((c) => c.key)), [["r:S0", "p:S1"], ["r:S1", "p:S2"]]);
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /const made: Grid\[\] = all\.length > 1 \? all\.map\(\(a\) => \(\{ arrow: a, typed: \{\}, roles: \{\}, step: true \}\)\)/, "Analyse stoichiometry gives a scheme of several arrows a table for each step");
  assert.match(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /context\.steps === "split" \? "One table for each step" : "One table for the scheme", "grid\.steps"/);
  assert.match(editor, /steps: doc\.grids\?\.some\(\(g\) => g\.step && all\.includes\(g\.arrow\)\) \? "join" : "split"/, "a scheme with any step table offers One table for the scheme");
  // Only a reactant is set as limiting; a catalyst's 5 or 5% is 5 mol%; a solvent's density leaves the concentration.
  assert.match(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), /context\.role === "reactant" && !context\.limiting \? \[it\(<Target size=\{18\} \/>, "Set as limiting"/);
  assert.match(editor, /if \(gc\.row === "limiting" && gcol\.role === "reactant"\)/);
  assert.match(editor, /role === "catalyst" && field0 === "equiv" \? text\.replace\(\/\^\\s\*\(\[\\d\.,\]\+\(\?:e\[\+-\]\?\\d\+\)\?\)\\s\*%\?\\s\*\$\/i, "\$1 mol%"\)/);
  assert.match(editor, /const open = !\["mass", "moles", "volume", "equiv"\]\.includes\(field\) \|\|/);
}
// Issue 134: a grid keeps each amount in base units, so a file from Octet 1.1.1 opens with the same amounts whatever
// Settings say: 250 mg of ethanol, K2CO3 at 2 eq., 300 mg of ethyl acetate measured.
{
  const old = '{"format":"octet","version":1,"app":"1.1.1","structure":{"atoms":[],"bonds":[]},"arrows":[{"kind":"reaction","x1":0,"y1":0,"x2":3,"y2":0}],"grids":[{"arrow":0,"typed":{"r:C2H6O":{"mass":0.25},"r:\\"K2CO3\\"":{"equiv":2},"p:C4H8O2":{"measured":0.3}},"limiting":"r:C2H6O"}]}';
  const g = parse(old).grids![0];
  assert.deepEqual(g.typed, { "r:C2H6O": { mass: 0.25 }, 'r:"K2CO3"': { equiv: 2 }, "p:C4H8O2": { measured: 0.3 } });
  assert.equal(formatAmount(g.typed["r:C2H6O"].mass, "mass"), "250 mg");
}
// Issue 136: a product's Expected mass typed is the mass wanted, kept as its mass. With no reactant amount it sets the
// scale: 5 g of C (MW 50) is 0.1 mol, so 0.1 mol of A (10 g) and B at 2 eq. (0.8 g/mL: 2 g, 2.5 mL); by A → 2 C,
// 0.05 mol of A. A reactant's amount wins. Octet 1.1.1 reads the grid (a mass on any column) and leaves the target out.
{
  const a = { key: "r:A", mw: 100, product: false, typed: {} }, b = { key: "r:B", mw: 10, product: false, typed: { equiv: 2, density: 0.8 } }, c = { key: "p:C", mw: 50, product: true, typed: { mass: 5 } };
  const s = solve([a, b, c]);
  near(s["r:A"].moles, 0.1, "the limiting reactant's moles");
  near(s["r:A"].mass, 10, "its mass");
  near(s["r:B"].mass, 2, "B's mass");
  near(s["r:B"].volume, 2.5, "B's volume");
  near(s["p:C"].expectedMass, 5, "the mass wanted");
  near(solve([a, { ...c, typed: { mass: 5, equiv: 2 } }])["r:A"].moles, 0.05, "A → 2 C");
  near(solve([{ ...a, coef: 1 }, { ...c, coef: 2 }])["r:A"].moles, 0.05, "A → 2 C, written in the scheme");
  near(solve([{ ...a, typed: { mass: 1 } }, c])["p:C"].expectedMass, 0.5, "a reactant's amount wins");
  const m: Mol = { atoms: [], bonds: [], arrows: [{ id: 4, kind: "reaction", from: [0, 0], to: [3, 0] }], grids: [{ arrow: 4, typed: { "p:C": { mass: 5 } } }] };
  assert.deepEqual(parse(serialize(m)).grids![0].typed, { "p:C": { mass: 5 } }, "kept in Octet's file");
  assert.deepEqual(fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol.grids![0].typed, { "p:C": { mass: 5 } }, "and in CDXML");
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(readFileSync(new URL("gridview.ts", import.meta.url), "utf8"), /if \(row\.id === "expected"\) return \{ text: formatAmount\(s\?\.expectedMass, "mass"\), typed: c\.typed\.mass !== undefined \};/, "shown bold when typed");
  assert.match(editor, /\(gc\.row !== "expected" \|\| gc\.product\)/, "a product's Expected mass can be typed in");
  // One value sets the scale: a mass wanted clears the reactants' amounts and every other product's mass wanted.
  assert.match(editor, /filter\(\(\[fd\]\) => \(k\[0\] === "p" \? fd !== "mass" : !target \|\| !amount\(fd\)\)\)/, "one value sets the scale");
}
// Words and notes a reagent's name is read past: sat., dil., glacial, fuming, excess, xs, then, and a note in brackets
// at the end. A formula's own brackets stay.
for (const [text, want] of [["sat. NaHCO3", "NaHCO3"], ["sat. aq. NH4Cl", "NH4Cl"], ["satd NH4Cl", "NH4Cl"], ["dil. HCl", "HCl"], ["glacial AcOH", "AcOH"], ["fuming HNO3", "HNO3"],
  ["excess MeI", "MeI"], ["xs MeI", "MeI"], ["then HCl", "HCl"], ["nBuLi (2.5 M in hexanes)", "nBuLi"], ["acetic acid (glacial)", "acetic acid"], ["HCl (aq)", "HCl"],
  ["Ca(OH)2", "Ca(OH)2"], ["Pd(PPh3)4 (5 mol%)", "Pd(PPh3)4"], ["Cu(OAc)2", "Cu(OAc)2"]]) assert.equal(reagentName(text), want, text);
// Molybdenum, barium, scandium, cerium, bismuth and the other elements of reagents written as formulas.
{
  const none = () => undefined, weight = (t: string) => reagentFormula(t, none, none, none)?.weight;
  near(weight("MoO3"), 95.95 + 3 * 15.999, "MoO3");
  near(weight("Ba(OH)2"), 137.33 + 2 * 17.007, "Ba(OH)2");
  near(weight("Sc(OTf)3"), 44.956 + 3 * (12.011 + 3 * 18.998 + 32.06 + 3 * 15.999), "Sc(OTf)3");
  near(weight("CeCl3·7H2O"), 140.12 + 3 * 35.45 + 7 * 18.015, "CeCl3·7H2O");
  near(weight("Bi(NO3)3"), 208.98 + 3 * (14.007 + 3 * 15.999), "Bi(NO3)3");
}
// Name to Structure takes a few ms a name, and the table is laid out again on every change: each name is read once
// by a reader, and never for a word for how the reaction is run. Short names (D2O) and CAS numbers are read. The editor
// gives one reader while Octet's names and the user's own stay the same.
{
  const asked: string[] = [], read = (t: string) => void asked.push(t), none = () => undefined;
  const words = ["reflux", "rt", "r.t.", "overnight", "MW", "hν", "Δ", "then workup", "sonication"], names = ["Lindlar", "D2O", "7647-01-0"];
  for (let k = 0; k < 3; k++) for (const t of [...words, ...names]) reagentFormula(t, read, none, none);
  assert.deepEqual(asked, names);
  reagentFormula("Lindlar", (t) => void asked.push(`again ${t}`), none, none);
  assert.equal(asked.at(-1), "again Lindlar", "a new reader reads it again");
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /const readName = useMemo\(\(\) => \(t: string\) => \(namesLoaded \? nameToSmiles\(t\) : undefined\), \[namesLoaded, settings\.dictionary\]\);/);
  assert.match(editor, /reagent: \(item\) => reagentFormula\(item, readName, labelSmiles, smilesWeight\),/);
}
{
  // A reagent table moves when you drag any part of it with Select: a cell, its row names, its lines or a gap (Sam,
  // 13 November 2026). A press on a cell also picks the cell.
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /gridViews\.find\(\(v\) => \{ const \[x0, y0, x1, y1\] = tableSpan\(v\);[^\n]*\n\s*if \(table\) \{\n\s*choose\(\[\], \[\]\);\n\s*setGridPick\(undefined\);\n\s*return setDrag\(\{ kind: "grid", arrow: table\.arrow/);
}
console.log("stoich.check: ok");
