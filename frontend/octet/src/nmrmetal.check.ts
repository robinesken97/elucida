// Run: node src/nmrmetal.check.ts. Fails loudly if NMR prediction stops working on the library's metallocenes and
// arene complexes, drawn as the editor draws them (rings joined to the metal through multi-centre points): every Cp
// and arene carbon gets a shift, a ring's alike atoms share one signal, and the shifts go on the drawn ring atoms.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { expandWithOrigins, ready } = await import("./chem.ts");
const { fragments, subset } = await import("./edit.ts");
const { graphOf } = await import("./naming.ts");
const { multiplicity, predict, quality, readTables } = await import("./nmr.ts");
const { libraryItem } = await import("./library.ts");
type Mol = import("./render.ts").Mol;
await ready;
readTables(gunzipSync(readFileSync(new URL("../data/nmr/shifts.bin.gz", import.meta.url))));

// As the Spectrum panel predicts: the largest structure, its labels expanded with each η ring bonded to its metal,
// and each signal's atoms as drawn atoms.
function spectrum(doc: Mol, nucleus: "1H" | "13C") {
  const ids = [...fragments(doc)].sort((a, b) => b.length - a.length)[0].sort((a, b) => a - b);
  const { mol, from } = expandWithOrigins(subset(doc, new Set(ids)), true), gr = graphOf(mol);
  assert.ok(gr, "the structure has a graph");
  const p = predict(gr, nucleus);
  assert.ok(p, `a ${nucleus} prediction`);
  return p.signals.map((s) => ({ ...s, drawn: [...new Set(s.atoms.map((k) => ids[from[k]]))].sort((a, b) => a - b) }));
}
const template = (name: string) => libraryItem(`lib:${name}`)!.mol;
const ringAtoms = (m: Mol) => m.atoms.flatMap((a) => a.centre?.atoms ?? []).sort((a, b) => a - b);

// Ferrocene: one ¹H singlet of 10H at 4.16 and one ¹³C signal at 67.8, both on the ten ring atoms (not the
// multi-centre points), rated good.
const fc = template("Ferrocene"), ring = ringAtoms(fc);
const [h] = spectrum(fc, "1H"), [c] = spectrum(fc, "13C");
assert.equal(spectrum(fc, "1H").length, 1);
assert.equal(spectrum(fc, "13C").length, 1);
assert.equal(h.nuclei, 10);
assert.equal(multiplicity(h), "s");
assert.ok(Math.abs(h.shift - 4.16) <= 0.1, `ferrocene ¹H ${h.shift}`);
assert.ok(Math.abs(c.shift - 67.8) <= 1.5, `ferrocene ¹³C ${c.shift}`);
assert.deepEqual(h.drawn, ring);
assert.deepEqual(c.drawn, ring);
assert.equal(quality(h, "1H"), "good");
assert.equal(quality(c, "13C"), "good");
// The chemistry elsewhere still takes a metallocene as its ions (names, InChI): no bond to the metal.
const ions = expandWithOrigins(fc).mol, iron = ions.atoms.findIndex((a) => a.label === "Fe");
assert.equal(ions.atoms[iron].charge, 2);
assert.ok(!ions.bonds.some((b) => b.atoms.includes(iron)));

// Acetylferrocene: the ferrocene template with an acetyl group on one ring atom.
const at = ring[0], [x, y] = [fc.atoms[at].location[0], fc.atoms[at].location[1]], n = fc.atoms.length;
const acetyl: Mol = {
  ...fc,
  atoms: [...fc.atoms, { label: "C", location: [x, y - 1, 0] }, { label: "O", location: [x + 0.87, y - 1.5, 0] }, { label: "C", location: [x - 0.87, y - 1.5, 0] }],
  bonds: [...fc.bonds, { type: 1, atoms: [at, n] }, { type: 2, atoms: [n, n + 1] }, { type: 1, atoms: [n, n + 2] }],
};
const ac = spectrum(acetyl, "13C"), acOn = (i: number) => ac.find((s) => s.drawn.includes(i))!;
assert.equal(ac.length, 6);
assert.ok(Math.abs(acOn(n).shift - 202.0) <= 1.5, "C=O");
assert.ok(Math.abs(acOn(at).shift - 79.2) <= 1.5, "ipso");
const bare = fc.atoms.find((a) => a.centre && !a.centre.atoms.includes(at))!.centre!.atoms;
assert.deepEqual(acOn(bare[0]).drawn, [...bare].sort((a, b) => a - b), "the bare ring is one signal");
const ah = spectrum(acetyl, "1H");
assert.deepEqual(ah.map((s) => s.nuclei).sort(), [2, 2, 3, 5]);
assert.ok(Math.abs(ah.find((s) => s.nuclei === 5)!.shift - 4.2) <= 0.1, "bare ring ¹H");

// Cp2ZrCl2, (benzene)Cr(CO)3, decamethylferrocene and ruthenocene: every ring carbon in one signal per ring kind, and
// each signal on drawn ring atoms. Where nmrshiftdb2 has nothing like them the shifts are rated rough.
for (const [name, rough] of [["Cp2ZrCl2", true], ["(Benzene)Cr(CO)3", true], ["Decamethylferrocene", false], ["Ruthenocene", true]] as const) {
  const m = template(name), r = ringAtoms(m), cs = spectrum(m, "13C"), onRing = cs.filter((s) => s.drawn.every((i) => r.includes(i)));
  assert.deepEqual(onRing.flatMap((s) => s.drawn).sort((a, b) => a - b), r, `${name}: every ring carbon`);
  assert.equal(onRing.length, 1, `${name}: the ring carbons are one signal`);
  if (rough) assert.equal(quality(onRing[0], "13C"), "rough", `${name} rated rough`);
}
const cr = spectrum(template("(Benzene)Cr(CO)3"), "1H");
assert.deepEqual(cr.map((s) => [s.nuclei, multiplicity(s)]), [[6, "s"]]);

console.log("nmrmetal.check: ok");
