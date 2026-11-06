// Run: node src/proprows.check.ts. Fails loudly if Decimals or the properties report go wrong.
import assert from "node:assert/strict";
import type { Structure } from "./chem.ts";
import { PROPERTY_ROWS, propertyReport, propertyValues } from "./proprows.ts";

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
assert.equal(lines[1], "Calculated by Octet on 18 October 2026. These values are estimates.");
assert.ok(lines.includes("Structure 1") && lines.includes("Structure 2"));
assert.ok(lines.includes("Formula\tC9H8O4") && lines.includes("Formula\tC2H6O"));
assert.ok(lines.includes("Exact mass\t46.0419"));
const methods = lines.slice(lines.indexOf("Methods") + 1);
assert.equal(methods.filter((l) => l.startsWith("logP: ")).length, 1);
assert.ok(methods.some((l) => l.startsWith("logP: Wildman–Crippen")));
// A single structure is not numbered.
assert.ok(propertyReport(propertyValues([aspirin])).split("\n").includes("Structure"));
console.log("proprows.check: ok");
