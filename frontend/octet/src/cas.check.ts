// Run: node src/cas.check.ts. Fails loudly if the Properties panel's CAS row goes wrong: each structure's number from
// the dictionary (data/names/dictionary.tsv.gz) by its InChIKey as drawn, E and Z apart, the same number for a
// structure moved, none for one the dictionary does not have, and the row after the formula only when there is a
// number. Also the time a lookup takes once a structure's InChIKey is kept: the panel must never wait.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { drawnInchiKey, parseStructure, ready, structures } = await import("./chem.ts");
const { attachDictionary, dictionaryCas } = await import("./dictionary.ts");
const { PROPERTY_ROWS, propertyReport, propertyValues, rowLabel, withCas } = await import("./proprows.ts");
type Mol = import("./render.ts").Mol;
await ready;

const table = new URL("../data/names/dictionary.tsv.gz", import.meta.url);
if (!existsSync(table)) { console.log("cas.check: skipped (no dictionary)"); process.exit(0); }
// Before the dictionary has loaded there is no number, and nothing fails.
assert.equal(dictionaryCas("BSYNRYMUTXBXSQ-UHFFFAOYSA-N"), undefined);
await attachDictionary(gunzipSync(readFileSync(table)).toString("utf8"));
const cas = (m: Mol) => { const key = drawnInchiKey(m); return key && dictionaryCas(key); };

// Aspirin as Octet lays it out, and moved across the page: the same number.
const aspirin = parseStructure("CC(=O)Oc1ccccc1C(=O)O");
assert.equal(drawnInchiKey(aspirin), "BSYNRYMUTXBXSQ-UHFFFAOYSA-N");
assert.equal(cas(aspirin), "50-78-2");
const moved: Mol = { ...aspirin, atoms: aspirin.atoms.map((a) => ({ ...a, location: [a.location[0] + 7.5, a.location[1] - 3.25, a.location[2] ?? 0] })) };
assert.equal(cas(moved), "50-78-2");
assert.equal(cas(parseStructure("Cn1cnc2c1c(=O)n(C)c(=O)n2C")), "58-08-2", "caffeine");

// Maleic and fumaric acid drawn by hand: one carboxylic acid on the same side of the double bond as the other, then
// moved across. The stereo comes from where the atoms are, so the number follows it.
const butenedioic = (y: number): Mol => ({
  atoms: [[0, 0], [1, 0], [-0.5, 0.866], [1.5, y], [-1.5, 0.866], [0, 1.732], [2.5, y], [1, y + Math.sign(y) * 0.866]].map(([x, yy], i) => ({ label: i < 4 ? "C" : "O", location: [x, yy, 0] as [number, number, number] })),
  bonds: [[0, 1, 2], [0, 2, 1], [1, 3, 1], [2, 4, 1], [2, 5, 2], [3, 6, 1], [3, 7, 2]].map(([a, b, type]) => ({ type, atoms: [a, b] as [number, number] })),
});
assert.equal(cas(butenedioic(0.866)), "110-16-7", "maleic acid (Z)");
assert.equal(cas(butenedioic(-0.866)), "110-17-8", "fumaric acid (E)");

// Two numbers for one compound (the dictionary lists both); none for a structure it does not have.
assert.equal(dictionaryCas("CKLJMWTZIZZHCS-REOHCLBHSA-N"), "56-84-8, 25608-40-6", "L-aspartic acid");
assert.equal(cas(parseStructure("FC(F)(Cl)C(Br)(I)C(Cl)(Br)C(F)(I)C#CC(Br)(Cl)I")), undefined);
assert.equal(dictionaryCas("AAAAAAAAAAAAAA-UHFFFAOYSA-N"), undefined);

// A structure's InChIKey is worked out once: a lookup after that is a table's, well inside a frame.
let t0 = performance.now();
for (let i = 0; i < 1000; i++) cas(moved);
const keptMs = (performance.now() - t0) / 1000;
assert.ok(keptMs < 0.5, `a kept lookup takes ${keptMs.toFixed(3)} ms`);
// The panel's structures keep the rest of the drawing (subset). A 1 MB picture and a caption there change nothing.
const busy: Mol = { ...moved, captions: [{ id: 1, text: "Scheme 1", x: 3, y: 4 }], shapes: [{ id: 2, kind: "picture", from: [0, 0], to: [9, 9], picture: { png: "89".repeat(500_000) } }] };
assert.equal(cas(busy), "50-78-2");
t0 = performance.now();
for (let i = 0; i < 20; i++) cas({ ...busy, captions: [{ id: 1, text: "Scheme 1", x: i, y: 4 }] });
const busyMs = (performance.now() - t0) / 20;
assert.ok(busyMs < 0.5, `a kept lookup in a drawing with a picture takes ${busyMs.toFixed(3)} ms`);

// The row: after the formula, with each structure's number, not marked predicted; no row when no structure has one.
const [s] = structures(aspirin)!;
const values = propertyValues([s!, s!]);
assert.equal(withCas(values, [undefined, undefined]), values, "no number, no row");
assert.equal(withCas(values, []), values);
const shown = withCas(values, ["50-78-2", undefined, "64-17-5"]);
assert.deepEqual(shown[0].map((r) => r.key), ["formula", "cas", ...values[0].slice(1).map((r) => r.key)]);
assert.deepEqual(shown[0][1].values, ["50-78-2", undefined], "one number for each structure shown");
assert.equal(rowLabel(shown[0][1]), "CAS number");
assert.deepEqual(shown.slice(1), values.slice(1));
assert.equal(PROPERTY_ROWS[0][1].key, "cas", "the row goes after the formula");
const report = propertyReport(withCas(propertyValues([s!]), ["50-78-2"])).split("\n");
assert.ok(report.includes("CAS number\t50-78-2"));
assert.ok(report.some((l) => l.startsWith("CAS number: Looked up by the structure's standard InChIKey")));

// The panel asks PubChem only with Online search on, not while a glide runs, and never for a polymer.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
for (const [rule, what] of [[/const online = TAURI && settings\.onlineSearch\b/, "online only"], [/const ask = online \? keys\.find/, "asks only online"],
  [/if \(glidingNow\.current\) \{ timer = window\.setTimeout\(look, 100\); return; \}/, "waits for a glide"], [/performance\.now\(\) - t0 < 8\)/, "8 ms at a time"],
  [/parts: kept\.map\(\(x\) => \(x\.s!\.repeat \? undefined : x\.g\)\)/, "no polymer"]] as const) assert.ok(rule.test(editor), `Editor.tsx: the CAS lookup ${what}`);
console.log(`cas.check: ok (a kept lookup ${keptMs.toFixed(3)} ms)`);
