// Run: node src/copyas.check.ts. Fails loudly if Edit > Copy As stops giving ChemDraw's text forms (CH-26): InChI,
// InChIKey, MOL Text in V3000 (ChemDraw 26.1's) and MOL V2000 Text, and InChI files import.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { importStructure, parseStructure, ready, toInchi, toInchiKey, toMolfile } = await import("./chem.ts");
await ready;

const ethanol = parseStructure("CCO");
assert.equal(toInchi(ethanol), "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3");
assert.equal(toInchiKey(ethanol), "LFQSCWFLJHTTHZ-UHFFFAOYSA-N");
const v3000 = toMolfile(ethanol), v2000 = toMolfile(ethanol, true);
assert.match(v3000, /V3000/);
assert.match(v3000, /M {2}V30 COUNTS 3 2/);
assert.match(v2000, / {2}3 {2}2 .*V2000/);
// The header keeps its three lines (the first, the name, is empty), so the counts are on line 4 and the text reads back.
for (const [text, counts] of [[v2000, /V2000$/], [v3000, /V3000$/]] as const) {
  assert.match(text.split("\n")[3], counts);
  assert.equal(importStructure(text).atoms.length, 3);
}
// An InChI file (Import a Structure) reads as its structure, laid out.
assert.equal(importStructure("InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3\n").atoms.length, 3);
// An RXN file brings its reactants and products.
const rxn = `$RXN

  Octet

  1  1
$MOL

  Octet

  2  1  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0
    1.0000    0.0000    0.0000 C   0  0
  1  2  1  0
M  END
$MOL

  Octet

  2  1  0  0  0  0  0  0  0  0999 V2000
    4.0000    0.0000    0.0000 C   0  0
    5.0000    0.0000    0.0000 O   0  0
  1  2  1  0
M  END
`;
assert.deepEqual(importStructure(rxn).atoms.map((a) => a.label), ["C", "C", "C", "O"]);
console.log("copyas.check: InChI, InChIKey, MOL V3000 and V2000, InChI and RXN files ok");
