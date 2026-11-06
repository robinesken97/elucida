// Run: node src/fills.check.ts. Fails loudly if ring fills or bond highlights (CD-27) are lost or mixed up: fused rings
// keep their own fills through edits, saves, older files and CDXML.
import assert from "node:assert/strict";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { deleteAtoms, extractSelection, insertMol } from "./edit.ts";
import { parse, serialize } from "./file.ts";
import type { Atom, Mol } from "./render.ts";

// Naphthalene: atoms 0-5 the left ring, 4-9 the right one (4 and 5 shared), a fill on each and a highlighted bond.
const at = (x: number, y: number): Atom => ({ label: "C", location: [x, y, 0] });
const h = Math.sqrt(3) / 2;
const naphthalene: Mol = {
  atoms: [at(-h, 0.5), at(-2 * h, 0), at(-2 * h, -1), at(-h, -1.5), at(0, -1), at(0, 0), at(h, 0.5), at(2 * h, 0), at(2 * h, -1), at(h, -1.5)],
  bonds: [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0], [5, 6], [6, 7], [7, 8], [8, 9], [9, 4]].map(([a, b]) => ({ type: 1, atoms: [a, b] as [number, number] })),
  fills: [{ atoms: [0, 1, 2, 3, 4, 5], colour: "#2F6FED" }, { atoms: [5, 6, 7, 8, 9, 4], colour: "#E5484D" }],
};
naphthalene.bonds[7].halo = "#2BA84A";

// Edits: an atom of the right ring deleted takes its fill away and keeps the left one, renumbered.
{
  const out = deleteAtoms(naphthalene, new Set([7]));
  assert.deepEqual(out.fills, [{ atoms: [0, 1, 2, 3, 4, 5], colour: "#2F6FED" }]);
  const gone = deleteAtoms(naphthalene, new Set([0]));
  assert.deepEqual(gone.fills, [{ atoms: [4, 5, 6, 7, 8, 3], colour: "#E5484D" }]);
  // Copy keeps the fills wholly copied; paste moves them to the new atoms.
  const part = extractSelection(naphthalene, new Set([4, 5, 6, 7, 8, 9]), new Set());
  assert.deepEqual(part.fills, [{ atoms: [1, 2, 3, 4, 5, 0], colour: "#E5484D" }]);
  const pasted = insertMol(naphthalene, part).mol;
  assert.deepEqual(pasted.fills?.at(-1), { atoms: [11, 12, 13, 14, 15, 10], colour: "#E5484D" });
  console.log("fills.check: edits keep each ring's fill");
}

// Saves: fills and bond highlights come back; an older file's atom fills become a fill for each ring whose atoms all
// had the same one (so fused rings filled alike stay filled).
{
  const back = parse(serialize(naphthalene));
  assert.deepEqual(back.fills, naphthalene.fills);
  assert.equal(back.bonds[7].halo, "#2BA84A");
  const old = JSON.parse(serialize({ atoms: naphthalene.atoms, bonds: naphthalene.bonds }));
  old.structure.atoms.forEach((a: Record<string, unknown>, i: number) => { if (i < 6) a.fill = "#2F6FED"; });
  const migrated = parse(JSON.stringify(old));
  assert.equal(migrated.fills?.length, 1);
  assert.deepEqual([...migrated.fills![0].atoms].sort(), [0, 1, 2, 3, 4, 5]);
  for (const fills of [[{ atoms: [0, 1], colour: "#2F6FED" }], [{ atoms: [0, 1, 99], colour: "#2F6FED" }], [{ atoms: [0, 1, 2], colour: "red" }], [{ atoms: [0, 0, 1], colour: "#2F6FED" }]])
    assert.throws(() => parse(JSON.stringify({ ...JSON.parse(serialize(naphthalene)), fills })), /damaged/);
  console.log("fills.check: saved and older files ok");
}

// CDXML: each fill is a ColoredMolecularArea in its fragment (its colour and its ring's bonds), each bond highlight a
// highlightColor, as ChemDraw writes them; both are read back from a file ChemDraw wrote.
{
  const text = toCdxml(naphthalene, DEFAULT_STYLE, { name: "fills.cdxml" });
  assert.equal(text.match(/<ColoredMolecularArea\s/g)?.length, 2);
  assert.match(text, /<b\s[^>]*highlightColor="\d+"/);
  // As ChemDraw would give it back: no Octet data in it.
  const foreign = text.replace(/ Octet="[^"]*"/g, "");
  const read = fromCdxml(foreign);
  assert.equal(read.lost["ring fill"], undefined);
  const key = (r: number[]) => [...r].sort((p, q) => p - q).join(",");
  assert.deepEqual(read.mol.fills?.map((f) => [key(f.atoms), f.colour]).sort(), naphthalene.fills!.map((f) => [key(f.atoms), f.colour]).sort());
  assert.equal(read.mol.bonds.filter((b) => b.halo === "#2BA84A").length, 1);
  // A ring fill whose bonds do not close a ring is lost, and counted.
  const broken = foreign.replace(/(<ColoredMolecularArea\s[^>]*BasisObjects=")(\d+) /, "$1");
  assert.equal(fromCdxml(broken).lost["ring fill"], 1);
  console.log("fills.check: CDXML ok");
}
