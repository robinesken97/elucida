// Run: node src/search.check.ts. What Search Reaxys and Search PubChem send for a structure: plain SMILES, or a
// molfile that keeps generic labels.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { ready, parseStructure } = await import("./chem.ts");
const { searchQuery, SEARCHES } = await import("./search.ts");
type Mol = import("./render.ts").Mol;
await ready;

// Aspirin as drawn: SMILES only.
assert.deepEqual(Object.keys(searchQuery(parseStructure("CC(=O)Oc1ccccc1C(=O)O"))), ["smiles"]);
// A label Octet cannot read is a pseudo-atom: the SMILES has no CXSMILES part (|$;;$|) after it.
const ethyl = (text: string): Mol => ({
  atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [0.866, 0.5, 0] }, { label: "C", text, location: [1.732, 0, 0] }],
  bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }],
});
const odd = searchQuery(ethyl("Zz9"));
assert.ok(odd.smiles && !/\s|\|/.test(odd.smiles), odd.smiles);
// Generic labels: a molfile, under the header Reaxys was seen to read. As ChemDraw writes them: A, Q and X as the
// atom symbol; the others as a carbon with the label as its alias.
for (const label of ["A", "AH", "Q", "QH", "M", "MH", "X", "XH"]) {
  const q = searchQuery(ethyl(label));
  assert.equal(q.smiles, undefined);
  const lines = q.molfile!.split("\n"), symbol = ["A", "Q", "X"].includes(label);
  assert.deepEqual(lines.slice(0, 3), ["Octet", "  Octet", ""]);
  assert.match(lines[3], /^\s+3\s+2\s.*V2000$/);
  assert.equal(lines[6].slice(31, 34).trim(), symbol ? label : "C", lines[6]);
  const end = lines.indexOf("M  END");
  if (symbol) assert.ok(!lines.some((l) => l.startsWith("A  ")));
  else assert.deepEqual(lines.slice(end - 2, end), ["A    3", label]);
}
// The alias names the right atom when a label before it (OMe) is written out as atoms.
{
  const m: Mol = { atoms: [{ label: "C", text: "OMe", location: [0, 0, 0] }, { label: "C", location: [0.866, 0.5, 0] }, { label: "C", text: "M", location: [1.732, 0, 0] }], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }] };
  const lines = searchQuery(m).molfile!.split("\n"), alias = lines.findIndex((l) => l.startsWith("A  ")), n = Number(lines[alias].slice(3));
  assert.equal(lines[alias + 1], "M");
  // Atom n (its line is n + 3) is the one drawn as M, at x 1.732: a carbon.
  assert.match(lines[n + 3], /^\s+1\.7320\s+0\.0000\s+0\.0000 C /, lines[n + 3]);
  assert.ok(lines.some((l) => l.slice(31, 34).trim() === "O"), "OMe written out");
}
// Reaxys looks for substructures by default, as ChemDraw does; PubChem for the same structure.
assert.deepEqual(SEARCHES.search_reaxys, ["reaxys", false]);
assert.deepEqual(SEARCHES.search_pubchem, ["pubchem", true]);
// A held key repeats the command: one search a second at most.
{
  const { searchNow } = await import("./search.ts");
  assert.equal(searchNow(10_000), true);
  assert.equal(searchNow(10_030), false, "a key repeat");
  assert.equal(searchNow(10_900), false);
  assert.equal(searchNow(11_000), true, "a second press, a second later");
}
console.log("search.check: ok");
