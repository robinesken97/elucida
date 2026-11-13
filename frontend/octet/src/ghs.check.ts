// Run: node src/ghs.check.ts. Fails loudly if Find hazards reads PubChem's GHS answer wrongly, lets a hostile answer
// through, shows the wrong rows, draws a pictogram it has no art for, or asks PubChem without the user's press.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type { Structure } from "./chem.ts";
import { ghsOf, PICTOGRAMS } from "./ghs.ts";
import { propertyReport, propertyValues } from "./proprows.ts";

// An answer in the shape PubChem gives (PUG View, heading GHS Classification): two sources, the first shown.
const swm = (...strings: string[]) => ({ StringWithMarkup: strings.map((String) => ({ String })) });
const icons = (...codes: string[]) => ({ StringWithMarkup: [{ String: "  ", Markup: codes.map((c) => ({ URL: `https://pubchem.ncbi.nlm.nih.gov/images/ghs/${c}.svg`, Type: "Icon" })) }] });
const answer = (info: object[], ref: object[] = [{ ReferenceNumber: 7, SourceName: "Regulation (EC) No 1272/2008" }]) => JSON.stringify({ Record: { RecordType: "CID", RecordNumber: 702, Section: [
  { TOCHeading: "Safety and Hazards", Section: [{ TOCHeading: "Hazards Identification", Section: [{ TOCHeading: "GHS Classification", Information: info }] }] }], Reference: ref } });
const ethanol = ghsOf(answer([
  { ReferenceNumber: 7, Name: "Pictogram(s)", Value: icons("GHS02") },
  { ReferenceNumber: 7, Name: "Signal", Value: swm("Danger") },
  { ReferenceNumber: 7, Name: "GHS Hazard Statements", Value: swm("H225: Highly Flammable liquid and vapor [Danger Flammable liquids]") },
  { ReferenceNumber: 7, Name: "Precautionary Statement Codes", Value: swm("P210, P233, P303+P361+P353, P210 and P501 (click each P-code to see the statement)") },
  { ReferenceNumber: 9, Name: "Pictogram(s)", Value: icons("GHS02", "GHS07") },
  { ReferenceNumber: 9, Name: "GHS Hazard Statements", Value: swm("H319 (37.7%): Causes serious eye irritation [Warning Serious eye damage/eye irritation]") },
]));
assert.deepEqual(ethanol, { cid: 702, source: "Regulation (EC) No 1272/2008", pictograms: ["GHS02"], signal: "Danger", hazards: ["H225: Highly Flammable liquid and vapor"], precautions: ["P210", "P233", "P303+P361+P353", "P501"] });
// A source with shares of reports keeps them; one that classifies nothing says so.
assert.deepEqual(ghsOf(answer([{ ReferenceNumber: 3, Name: "GHS Hazard Statements", Value: swm("H302 (95.6%): Harmful if swallowed [Warning Acute toxicity, oral]", "EUH066: Repeated exposure may cause skin dryness or cracking", "Reported by 3 companies.") }]))?.hazards,
  ["H302 (95.6%): Harmful if swallowed", "EUH066: Repeated exposure may cause skin dryness or cracking"]);
assert.deepEqual(ghsOf(answer([{ ReferenceNumber: 3, Name: "GHS Hazard Statements", Value: swm("Not Classified", "Reported as not meeting GHS hazard criteria.") }]))?.hazards, ["Not classified"]);
// A statement can hold a semicolon (H360FD): it stays one statement.
assert.deepEqual(ghsOf(answer([{ ReferenceNumber: 3, Name: "GHS Hazard Statements", Value: swm("H360FD: May damage fertility; May damage the unborn child [Danger Reproductive toxicity]") }]))?.hazards,
  ["H360FD: May damage fertility; May damage the unborn child"]);

// A hostile or broken answer reads as nothing, and never throws.
for (const bad of ["", "<html>", "null", "[]", '{"Record":null}', '{"Record":{"RecordNumber":"702"}}', '{"Record":{"RecordNumber":-1}}', '{"Record":{"RecordNumber":702,"Section":5}}'])
  assert.equal(ghsOf(bad), undefined, bad);
const odd = ghsOf(answer([null, 5, { ReferenceNumber: undefined, Name: "Signal", Value: { StringWithMarkup: [{ String: "x".repeat(5000) }, null, { String: 7 }] } },
  { Name: "Pictogram(s)", Value: { StringWithMarkup: [{ Markup: [{ URL: "https://example.com/GHS10.svg" }, { URL: "javascript:GHS05.svg" }, null, { URL: "/images/ghs/GHS06.svg" }] }] } }] as object[], [null as unknown as object]));
assert.deepEqual(odd, { cid: 702, pictograms: ["GHS06"], hazards: [], precautions: [] });
// Lists are kept short, so a huge answer cannot fill the panel.
assert.equal(ghsOf(answer([{ ReferenceNumber: 1, Name: "Precautionary Statement Codes", Value: swm(Array.from({ length: 300 }, (_, k) => `P${100 + k}`).join(", ")) }]))?.precautions.length, 60);

// The panel's rows: drawn pictograms named as the Symbols set names them, the statements, the source and the CID;
// "No GHS data" when PubChem has none; no rows before Find hazards.
const aspirin: Structure = { formula: "C9H8O4", weight: 180.1574, exact: 180.0423, composition: "C 60.00; H 4.48; O 35.53" };
const rows = (ghs: Parameters<typeof propertyValues>[3]) => Object.fromEntries(propertyValues([aspirin], undefined, undefined, ghs).flat().map((r) => [r.key, r.values]));
const found = rows([{ ...ethanol!, pictograms: ["GHS02", "GHS07"] }]);
assert.deepEqual(found.ghs, ["Flammable (GHS02), Harmful (GHS07)"]);
assert.deepEqual(found.signal, ["Danger"]);
assert.deepEqual(found.hazards, ["H225: Highly Flammable liquid and vapor"]);
assert.deepEqual(found.precautions, ["P210, P233, P303+P361+P353, P501"]);
assert.deepEqual(found["ghs-source"], ["Regulation (EC) No 1272/2008"]);
assert.deepEqual(found.cid, ["702"]);
assert.deepEqual(rows([null]).hazards, ["No GHS data in PubChem"]);
assert.equal(rows([undefined]).hazards, undefined);
assert.equal(rows([]).signal, undefined);
// Two structures, the second found: the report gives its hazards under Structure 2 and their source in Methods.
const report = propertyReport(propertyValues([aspirin, aspirin], undefined, undefined, [undefined, ethanol])).split("\n");
assert.ok(report.includes("Signal word\tDanger") && report.indexOf("Signal word\tDanger") > report.indexOf("Structure 2"));
assert.ok(report.some((l) => l.startsWith("Hazard statements: GHS classification from PubChem")));

// Every GHS pictogram has its name and art (ink lines and solid areas as SVG path data), and the Symbols set's four
// are named as before.
assert.deepEqual(Object.keys(PICTOGRAMS), ["GHS01", "GHS02", "GHS03", "GHS04", "GHS05", "GHS06", "GHS07", "GHS08", "GHS09"]);
for (const [code, p] of Object.entries(PICTOGRAMS)) {
  assert.ok(p.name && p.parts.length, code);
  for (const [kind, d] of p.parts) assert.ok((kind === "ink" || kind === "solid") && /^M[-\d. MLCQAZ]+$/.test(d), `${code}: ${d}`);
}
assert.deepEqual(["GHS02", "GHS03", "GHS04", "GHS07"].map((c) => PICTOGRAMS[c].name), ["Flammable", "Oxidising", "Gas under pressure", "Harmful"]);

// Octet asks PubChem for hazards only when the user presses Find hazards (decision 0008), and only with Online search on.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), panel = readFileSync(new URL("Properties.tsx", import.meta.url), "utf8");
assert.equal(editor.split('"pubchem_hazards"').length, 2, "one call");
assert.match(editor, /function findHazards\(\) \{[^}]*?TAURI\) return;[\s\S]{0,400}"pubchem_hazards"/);
assert.match(editor, /onHazards=\{findHazards\}/);
assert.match(panel, /\{online && <button className="prop-add" onClick=\{onHazards\}/);
assert.match(editor, /online=\{settings\.onlineSearch\}\s+onHazards/);
assert.match(editor, /settings\.onlineSearch && ghsKeys\?\.structures\[k\] === s/);
// A live caption (Add to drawing) keeps the hazards found for its structure when its values are worked out again.
assert.match(editor, /propertyValues\(found, calc, places, key \? \[ghsFound\.current\.get\(key\)\] : \[\]\)/);
// The panel draws each structure's pictograms and statements from its own value, so a semicolon in a statement does
// not split it as if it were the next structure's.
assert.match(panel, /row\.key === "ghs" \? row\.values\.map[\s\S]*row\.key === "hazards" \? row\.values\.map/);
console.log("ghs.check: ok");
