// Run: node src/groups.check.ts. Groups through CDXML, .oct files and edits: nested groups keep each level and its
// own Integral, text goes in the group of what it belongs to, and a grouped cycle stays grouped. With Sam's corpus
// on this Mac (~/octet-research/corpus/sam), every file with groups is checked too; elsewhere that part is skipped.
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { fromCdxml, parseXml, toCdxml, type Xml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { addArrow, addCaption, addCycle, addRing, addShape, EMPTY, extractSelection, groupParents, groupSelection, insertMol, wholeGroups } from "./edit.ts";
import { readOct, writeOct } from "./oct.ts";
import type { Arrow, Mol } from "./render.ts";

// The group tree as a list, the same whatever the ids: each group's size, Integral, and depth (0 at the top).
const tree = (m: Mol) => {
  const gs = m.groups ?? [], parents = groupParents(gs);
  const depth = (k: number) => { let d = 0; for (let p = parents[k]; p !== undefined; p = parents[p]) d++; return d; };
  return gs.map((g, k) => `${g.atoms.length}+${g.items.length}${g.integral ? " integral" : ""} at ${depth(k)}`).sort();
};
const groupsIn = (x: Xml, depth = 0): { depth: number; integral: boolean; kids: string[] }[] =>
  x.kids.flatMap((k) => [...(k.name === "group" ? [{ depth, integral: k.attrs.Integral === "yes", kids: k.kids.map((c) => c.name) }] : []), ...groupsIn(k, depth + (k.name === "group" ? 1 : 0))]);

// Two levels, each with its own Integral, written as nested <group> elements and read back the same. A compound
// number under a grouped structure goes inside the group even when the group does not list it (GRP-12).
{
  let m = addRing(addRing(EMPTY, 6, true, { point: [-4, 0] }), 5, false, { point: [4, 0] });
  let x: number, r: number;
  [m, x] = addCaption(m, { text: "x", x: 0, y: -3 });
  [m, r] = addArrow(m, { kind: "reaction", from: [-1, 3], to: [1, 3] });
  [m] = addCaption(m, { text: "1", x: 0, y: 0, bold: true, under: [0, 1, 2, 3, 4, 5] });
  const [one, inner] = groupSelection(m, new Set([0]), new Set([x]))!;
  const [two] = groupSelection({ ...one, groups: one.groups!.map((g) => (g.id === inner ? { ...g, integral: true as const } : g)) }, new Set([0]), new Set([r]))!;
  const text = toCdxml(two, DEFAULT_STYLE), written = groupsIn(parseXml(text));
  assert.deepEqual(written.map((g) => [g.depth, g.integral]), [[0, false], [1, true]]);
  assert.equal(written[1].kids.filter((k) => k === "t").length, 2, "x and the number are in the inner group");
  assert.deepEqual(tree(fromCdxml(text).mol), tree(two));
  // A group that does not list the number (an older drawing): the number is still written inside it.
  const bare = { ...m, groups: [{ id: 90, atoms: [0, 1, 2, 3, 4, 5], items: [x] }] };
  assert.equal(groupsIn(parseXml(toCdxml(bare, DEFAULT_STYLE)))[0].kids.filter((k) => k === "t").length, 2);
  console.log("groups.check: nested groups in CDXML ok");
}

// A catalytic cycle in a group: its arrows are written in the group, and the cycle is in the group again on reading.
{
  let m = addRing(addRing(EMPTY, 6, true, { point: [-4, 0] }), 6, false, { point: [4, 0] }), y: number, box: number;
  [m, y] = addCycle(m, { centre: [0, 0], radius: 4, clockwise: true, nodes: [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11]] });
  [m, box] = addShape(m, { kind: "box", from: [-8, -5], to: [8, 5] });
  const [g] = groupSelection(m, new Set(), new Set([y, box]))!;
  const derived: Arrow[] = [{ id: -1, kind: "curved", from: [-1, 3], to: [1, 3], bend: 0.3, cycle: y, step: 0 } as Arrow, { id: -2, kind: "curved", from: [1, -3], to: [-1, -3], bend: 0.3, cycle: y, step: 1 } as Arrow];
  const text = toCdxml(g, DEFAULT_STYLE, { derived });
  assert.equal(groupsIn(parseXml(text))[0].kids.filter((k) => k === "arrow").length, 2);
  const back = fromCdxml(text).mol;
  assert.deepEqual(back.groups!.map((x) => x.items.sort()), [[y, box].sort()]);
  console.log("groups.check: grouped cycle in CDXML ok");
}

// Conditions that a ChemDraw file keeps in a group of their own, out of the group of their arrow, stay there: opening,
// an edit and a CDXML round trip do not move them into the arrow's group.
{
  let m = addRing(EMPTY, 6, true, { point: [-4, 0] }), r: number, c: number;
  [m, r] = addArrow(m, { kind: "reaction", from: [-1, 0], to: [1, 0] });
  [m, c] = addCaption(m, { text: "DBU", x: 0, y: 1, on: { arrow: r, side: "below" } });
  m = { ...m, groups: [{ id: 90, atoms: [0, 1, 2, 3, 4, 5], items: [r] }, { id: 91, atoms: [], items: [c] }] };
  assert.equal(wholeGroups(m), m, "the group of one text stays");
  const back = fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol;
  assert.deepEqual(tree(back), tree(m));
  assert.equal(wholeGroups(back), back);
  // When the arrow is in no group, the group of one text goes, as other groups of one thing do.
  assert.equal(wholeGroups({ ...m, groups: [m.groups![1]] }).groups?.length ?? 0, 0);
  console.log("groups.check: conditions in a group of their own ok");
}

// Sam's corpus: each file with groups opens with its nested groups and every Integral flag, and keeps them through a
// CDXML round trip, a save and open as .oct, and a copy and paste of the whole drawing.
const CORPUS = join(homedir(), "octet-research/corpus/sam");
if (!existsSync(CORPUS)) console.log("groups.check: no corpus here, corpus part skipped");
else {
  let files = 0, nested = 0;
  for (const name of readdirSync(CORPUS).filter((f) => f.endsWith(".cdxml"))) {
    const text = readFileSync(join(CORPUS, name), "utf8");
    if (!text.includes("<group")) continue;
    files++;
    const read = fromCdxml(text), m = wholeGroups(read.mol), before = tree(m);
    assert.equal(m, read.mol, `${name}: opening keeps the file's groups`);
    const integral = groupsIn(parseXml(text)).filter((g) => g.integral).length;
    assert.equal((m.groups ?? []).filter((g) => g.integral).length, integral, `${name}: every Integral flag is kept`);
    if (before.some((t) => !t.endsWith(" at 0"))) nested++;
    assert.deepEqual(tree(wholeGroups(fromCdxml(toCdxml(m, read.style)).mol)), before, `${name}: CDXML round trip`);
    assert.deepEqual(tree(readOct(writeOct(m, read.style)).mol), before, `${name}: .oct save and open`);
    const all = { atoms: new Set(m.atoms.map((_, i) => i)), items: new Set([...(m.captions ?? []), ...(m.arrows ?? []), ...(m.shapes ?? []), ...(m.cycles ?? [])].map((x) => x.id)) };
    const pasted = wholeGroups(insertMol(m, extractSelection(m, all.atoms, all.items), [50, 0]).mol);
    assert.deepEqual(tree(pasted), [...before, ...before].sort(), `${name}: copy and paste`);
  }
  assert.ok(nested > 0, "some corpus files have nested groups");
  console.log(`groups.check: ${files} corpus files with groups (${nested} nested) ok`);
}
