// Run: node src/proprows.check.ts. Fails loudly if Decimals or the properties report go wrong.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type { Structure } from "./chem.ts";
import { LIVE_ATTRS, PROPERTY_ATTRS, fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { addCaption, addTemplate, erase } from "./edit.ts";
import { parse, serialize } from "./file.ts";
import { PROPERTY_ROWS, liveValues, propertyReport, propertyRuns, propertyValues } from "./proprows.ts";
import type { Caption, Mol } from "./render.ts";
import { plainOf } from "./richtext.ts";

// Aspirin's values as Indigo gives them.
const aspirin: Structure = { formula: "C9H8O4", weight: 180.1574, exact: 180.0423, composition: "C 60.00; H 4.48; O 35.53", logP: 1.31, mr: 44.71 };
const row = (values: ReturnType<typeof propertyValues>, key: string) => values.flat().find((r) => r.key === key)?.values;

// Standard places: 4 for the exact mass, 2 for the molecular weight and m/z.
const standard = propertyValues([aspirin]);
assert.deepEqual(row(standard, "exact"), ["180.0423"]);
assert.deepEqual(row(standard, "weight"), ["180.16"]);
assert.match(row(standard, "mz")![0]!, /^180\.04 \(100\.0%\)/);
// Decimals sets all three (ChemDraw: Exact Mass, Molecular Weight and m/z only); the rest keep their places.
const three = propertyValues([aspirin], undefined, 3);
assert.deepEqual(row(three, "exact"), ["180.042"]);
assert.deepEqual(row(three, "weight"), ["180.157"]);
assert.match(row(three, "mz")![0]!, /^180\.042 \(100\.0%\)/);
assert.deepEqual(row(three, "logp"), ["1.31"]);
assert.deepEqual(row(propertyValues([aspirin], undefined, 0), "weight"), ["180"]);

// Every row says how its value is found.
for (const r of PROPERTY_ROWS.flat()) assert.ok(r.method.length > 10, `${r.key} has a method`);

// The report: each structure's values (a tab between name and value), then each method once.
const report = propertyReport(propertyValues([aspirin, { ...aspirin, formula: "C2H6O", weight: 46.07, exact: 46.0419 }]), new Date(2026, 9, 18));
const lines = report.split("\n");
assert.equal(lines[0], "Chemical properties");
assert.equal(lines[1], "Calculated by Octet on 18 October 2026. Values marked (predicted) come from a model. They are not measured.");
// A predicted value is never shown or copied as a plain one: the report, Copy, Add to drawing and the panel's heading.
assert.ok(lines.includes("logP (predicted)\t1.31") && lines.includes("Formula\tC9H8O4"));
const predicted = PROPERTY_ROWS.flat().filter((r) => r.predicted).map((r) => r.key);
assert.deepEqual(predicted, ["tb", "tm", "tc", "pc", "vc", "hf", "gf", "henry", "logp", "mr", "logs", "pka"]);
assert.ok(PROPERTY_ROWS.every((g) => g.every((r) => r.predicted) || g.every((r) => !r.predicted)), "each group is all predicted or none");
const panel = readFileSync(new URL("Properties.tsx", import.meta.url), "utf8");
assert.match(panel, /g\.every\(\(r\) => r\.predicted\) && <h3 className="prop-heading">Predicted<\/h3>/);
assert.match(panel, /onCopy\(`\$\{rowLabel\(row\)\}: /);
assert.equal(plainOf(propertyRuns(standard, ["formula", "logp"], 0)), "Formula: C9H8O4\nlogP (predicted): 1.31");
assert.ok(lines.includes("Structure 1") && lines.includes("Structure 2"));
assert.ok(lines.includes("Formula\tC9H8O4") && lines.includes("Formula\tC2H6O"));
assert.ok(lines.includes("Exact mass\t46.0419"));
const methods = lines.slice(lines.indexOf("Methods") + 1);
assert.equal(methods.filter((l) => l.startsWith("logP (predicted): ")).length, 1);
assert.ok(methods.some((l) => l.startsWith("logP (predicted): Wildman–Crippen")));
// A single structure is not numbered.
assert.ok(propertyReport(propertyValues([aspirin])).split("\n").includes("Structure"));

// Live values (Add to drawing): a caption that follows its structure. An alkane stands in for Indigo: CnH2n+2 and its
// weight from the atoms given, so the check sees which atoms each caption is worked out for.
const alkane = (atoms: number[], places?: number) => {
  const n = atoms.length, weight = 12.011 * n + 1.008 * (2 * n + 2);
  return propertyValues([{ formula: `C${n}H${2 * n + 2}`, weight, exact: weight, composition: "" }], undefined, places);
};
const C = (x: number, y = 0) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
const ethane: Mol = { atoms: [C(0), C(1), C(5)], bonds: [{ type: 1, atoms: [0, 1] }] };
const live = (attrs: Record<string, string>): Omit<Caption, "id"> => ({ text: "", x: 0, y: 0, under: [0, 1], property: { attrs, atoms: [0, 1] } });
let [m, id] = addCaption(ethane, live({ rows: "formula weight" }));
const at = (x: Mol) => x.captions!.find((c) => c.id === id)!;
m = liveValues(m, alkane);
assert.equal(at(m).text, "Formula: C2H6\nMolecular weight: 30.07");
assert.deepEqual(at(m).runs?.filter((r) => r.script).map((r) => r.text), ["2", "6"]);
// Nothing to change: the same drawing, so the editor makes no change of its own.
assert.equal(liveValues(m, alkane), m);
// A carbon drawn on counts (the lone carbon apart does not), and the caption keeps the atoms it is for now.
const grown: Mol = { ...m, atoms: [...m.atoms, C(2)], bonds: [...m.bonds, { type: 1, atoms: [1, 3] }] };
const after = liveValues(grown, alkane);
assert.equal(at(after).text, "Formula: C3H8\nMolecular weight: 44.10");
assert.deepEqual(at(after).property, { attrs: { rows: "formula weight" }, atoms: [0, 1, 3] });
// Bold on all of it stays bold; a ChemDraw property text (no rows) is never changed.
const bold = { ...m, atoms: grown.atoms, bonds: grown.bonds, captions: m.captions!.map((c) => ({ ...c, runs: c.runs!.map((r) => ({ ...r, bold: true as const })) })) };
assert.ok(at(liveValues(bold, alkane)).runs!.every((r) => r.bold));
const theirs: Mol = { ...grown, captions: [{ id: 9, text: "Ethane", x: 0, y: 0, property: { attrs: { ChemicalPropertyType: "1" }, atoms: [0, 1] } }] };
assert.equal(liveValues(theirs, alkane), theirs);
// Its decimals; one a file gives that is not 0 to 8 is not used.
assert.equal(plainOf(propertyRuns(alkane([0, 1], 3), ["weight"])), "Molecular weight: 30.070");
[m, id] = addCaption(ethane, live({ rows: "weight", places: "3" }));
assert.equal(at(liveValues(m, alkane)).text, "Molecular weight: 30.070");
[m, id] = addCaption(ethane, live({ rows: "weight", places: "200" }));
assert.equal(at(liveValues(m, alkane)).text, "Molecular weight: 30.07");
// A carbon taken off counts too. Values for several structures are separated by semicolons, as the panel shows them.
m = liveValues(addCaption({ ...grown, captions: undefined }, live({ rows: "formula" }))[0], alkane);
id = m.captions![0].id;
assert.equal(at(liveValues(erase(m, new Set([1]), new Set()), alkane)).text, "Formula: C2H6");
assert.equal(plainOf(propertyRuns(propertyValues([aspirin, { ...aspirin, formula: "C2H6O" }]), ["formula"])), "Formula: C9H8O4; C2H6O");
// Kept in Octet's files and in CDXML (Octet's own data, as ChemDraw has no type for it), with its atoms.
const want = at(m).property;
assert.deepEqual(at(parse(serialize(m))).property, want);
const xml = toCdxml(m, DEFAULT_STYLE);
assert.ok(!xml.includes("chemicalproperty"));
const read = fromCdxml(xml).mol;
assert.deepEqual(read.captions![0].property, want);
// Opened again, its values are up to date: no change, so the drawing is not marked edited.
assert.equal(liveValues(read, alkane), read);
// Placed from My templates (kept as Octet's files), it is for the template's atoms, not the drawing's first atoms.
assert.equal(liveValues(addTemplate(ethane, parse(serialize(m)), { point: [0, 9] }), alkane).captions!.at(-1)!.text, "Formula: C3H8");
assert.deepEqual(LIVE_ATTRS.filter((k) => PROPERTY_ATTRS.includes(k)), []);
console.log("proprows.check: ok");
