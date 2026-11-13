// Run: node src/indigo.check.ts. Fails if failed Indigo calls can stop the chemistry, or the editor. Each Indigo call
// that fails leaks a little of Indigo's memory: in Octet 1.1.1, after about 1,270 of them in one session, every call
// failed, and the formula and mass in the Actions panel stopped the editor. One call can also damage Indigo (the InChI
// of a large fused ring system overflows its stack). chem.ts loads a fresh Indigo for both.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
type Mol = import("./render.ts").Mol;
await chem.ready;
const pause = () => new Promise((r) => setTimeout(r, 20));
const chain = (n: number): Mol => ({ atoms: Array.from({ length: n }, (_, k) => ({ label: "C", location: [k * 0.87, k % 2 ? 0.5 : 0, 0] as [number, number, number] })), bonds: Array.from({ length: n - 1 }, (_, k) => ({ type: 1, atoms: [k, k + 1] as [number, number] })) });

// 1,400 failed calls, 100 at a time with a pause between, as edits come. After each 100, a new structure's formula.
for (let k = 0, n = 0; k < 14; k++) {
  for (let j = 0; j < 100; j++) assert.equal(chem.toInchi(`C(C${n++}`), undefined);
  assert.equal(chem.analyse(chain(k + 2))?.[0].formula, `C${k + 2}H${2 * k + 6}`, `the formula after ${n} failed calls`);
  await pause();
}
console.log("indigo.check: the formula comes after 1,400 failed calls");

// A grid of 16 by 16 fused rings: its InChI overflows Indigo's stack, which damages Indigo. Until a fresh Indigo is in,
// the values are not there (as while Indigo loads at start), and no value throws.
const grid: Mol = { atoms: [], bonds: [] };
for (let i = 0; i <= 16; i++) for (let j = 0; j <= 16; j++) {
  grid.atoms.push({ label: "C", location: [i, j, 0] });
  if (i) grid.bonds.push({ type: 1, atoms: [17 * (i - 1) + j, 17 * i + j] });
  if (j) grid.bonds.push({ type: 1, atoms: [17 * i + j - 1, 17 * i + j] });
}
// 2-Methylbutane with a wedge to a methyl written as a label (Me): no stereocentre. Read while Indigo is not there, the
// label is an unknown atom and the carbon an S centre; that reading is not kept.
const methyl: Mol = {
  atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [-0.87, 0.5, 0] }, { label: "C", location: [0.87, 0.5, 0] }, { label: "C", location: [1.73, 0, 0] }, { label: "C", text: "Me", location: [0, -1, 0] }],
  bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [0, 2] }, { type: 1, atoms: [2, 3] }, { type: 1, atoms: [0, 4], stereo: 1 }],
};
assert.equal(chem.toInchi(grid), undefined);
for (const m of [chain(5), grid, methyl]) {
  assert.doesNotThrow(() => chem.analyse(m, 3, () => undefined));
  assert.doesNotThrow(() => chem.structures(m));
  assert.doesNotThrow(() => chem.stereoLabels(m));
}
await chem.ready;
assert.equal(chem.analyse(chain(7))?.[0].formula, "C7H16");
assert.equal(chem.structures(chain(8))?.[0]?.formula, "C8H18");
assert.equal(chem.analyse(grid)?.[0].formula, "C289H68", "the grid's formula, with no InChI");
assert.equal(chem.stereoLabels(methyl), undefined, "no stereocentre once Indigo reads the label");
console.log("indigo.check: a damaged Indigo is replaced, and no value throws meanwhile");

// The Actions panel asks for an abbreviation (by InChI) only for a structure of up to 120 atoms (MOST_NAMED), as for a
// selection of several structures. Above that, a fused ring system's InChI can take seconds, overflow (the grid above,
// or one of 170 atoms after 500 failed calls) or never end, and InChI fails above 1,023 atoms.
const asked: (string | undefined)[] = [];
const cite = (inchi: string | undefined) => { asked.push(inchi); return undefined; };
chem.analyse(chain(30), 3, cite);
assert.equal(asked.length, 1);
chem.analyse(chain(121), 3, cite);
assert.equal(asked.length, 1, "no InChI for 121 atoms");
// Hydrogens drawn as atoms do not count: 40 carbons with their 82 hydrogens (122 atoms) are asked for.
const drawnH = chain(40);
drawnH.atoms.slice().forEach((_, k) => { for (let n = k % 39 ? 2 : 3; n--; ) { drawnH.bonds.push({ type: 1, atoms: [k, drawnH.atoms.length] }); drawnH.atoms.push({ label: "H", location: [k * 0.87, 2 + n, 0] }); } });
chem.analyse(drawnH, 3, cite);
assert.equal(asked.length, 2, "an InChI for 40 carbons with their hydrogens drawn");
console.log("indigo.check: no InChI for the panel's large structures");

// The stereo warnings keep Indigo's reading of a structure by its shape, not by where it is, so a structure moved is
// not read again (wedges that conflict make failed calls). The shape still counts: two wedges on next bonds conflict,
// on opposite bonds they set the centre. Moved, each is read with Indigo set aside (after a call its binding refuses, as
// after damage): only what was kept can answer.
const centre = (angles: number[], dx: number): Mol => ({
  atoms: [{ label: "C", location: [dx, 0, 0] }, ...["C", "N", "O", "F"].map((label, k) => ({ label, location: [dx + Math.cos((angles[k] * Math.PI) / 180), Math.sin((angles[k] * Math.PI) / 180), 0] as [number, number, number] }))],
  bonds: [0, 1, 2, 3].map((k) => ({ type: 1, atoms: [0, k + 1] as [number, number], ...(k < 2 ? { stereo: 1 } : {}) })),
});
for (const dx of [0, 7.3]) {
  if (dx) chem.smilesWeight(0 as unknown as string);
  assert.deepEqual([...chem.stereoFacts(centre([0, 90, 180, 270], dx)).conflict], [0]);
  assert.deepEqual([...chem.stereoFacts(centre([0, 180, 90, 270], dx)).conflict], []);
}
console.log("indigo.check: the stereo warnings read a structure moved as it was");
