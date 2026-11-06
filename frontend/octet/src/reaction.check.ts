// Run: node src/reaction.check.ts. A messy two-step scheme (A + B → C → D) is found from either arrow, and Clean Up
// Reaction lays it out as ChemDraw 26.1's does (see reaction.ts): one level line, even gaps, arrows two gaps long or
// as long as their conditions, plus signs where they are missing, conditions above and below, wrapped lines.
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { frameStyle, pageSize, readStyle } from "./docstyle.ts";
import { addArrow, addCaption, addRing, addShape, EMPTY, fragments, pos, wholeGroups } from "./edit.ts";
import { readOct } from "./oct.ts";
import { cleanUpReaction, cleanUpReactions, findReaction, gapFor, reactionClean, roleOf, withStructure, type Layout, type Reaction } from "./reaction.ts";
import { ASCENT, DESCENT, fitArrows, placeCaptions, render, straightArrow, type Arrow, type Box, type Mol } from "./render.ts";

// Structures' boxes from their atoms; a caption's box from its text (0.5 wide a letter, 0.6 high, about its point).
const ink = (mol: Mol) => (atoms: number[]): Box => { const ps = atoms.map((i) => pos(mol, i)); return [Math.min(...ps.map((p) => p[0])), Math.min(...ps.map((p) => p[1])), Math.max(...ps.map((p) => p[0])), Math.max(...ps.map((p) => p[1]))]; };
const capBox = (mol: Mol) => (id: number): Box | undefined => {
  const c = mol.captions?.find((x) => x.id === id);
  if (!c || c.on) return undefined;
  const w = 0.25 * c.text.length;
  return [c.x - w, c.y - 0.15, c.x + w, c.y + 0.45];
};
const gap = gapFor(10, 14.4);
const layout = (mol: Mol, width?: number): Layout => ({ gap, width, captionBox: capBox(mol), plusBox: [-0.25, -0.15, 0.25, 0.45], captionPt: 10, bondPt: 14.4 });
const find = (mol: Mol, id: number) => findReaction(mol, id, mol.arrows!, ink(mol), capBox(mol))!;
const clean = (mol: Mol, r: Reaction, width?: number) => cleanUpReaction(mol, r, mol.arrows!, layout(mol, width));
const middle = (b: Box) => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
const arrowOf = (mol: Mol, id: number) => mol.arrows!.find((a) => a.id === id)!;
const len = (a: Arrow) => Math.hypot(a.to[0] - a.from[0], a.to[1] - a.from[1]);
// The gaps between the parts of a reaction as laid out now, along the row.
const gaps = (mol: Mol, r: Reaction) => r.steps.slice(1).map((s, k) => s.box[0] - r.steps[k].box[2]);

let m: Mol = EMPTY;
m = addRing(m, 6, true, { point: [0, 0.3] });
m = addRing(m, 6, false, { point: [3.4, -0.2] });
m = addRing(m, 5, false, { point: [9.6, 0.4] });
m = addRing(m, 6, true, { point: [16, -0.5] });
const [m1, plus] = addCaption(m, { text: "+", x: 1.7, y: 0, align: "centre" });
const [m2, first] = addArrow(m1, { kind: "reaction", from: [5.2, 0.1], to: [7.9, 0.1] });
const [m3, second] = addArrow(m2, { kind: "reaction", from: [11.2, 0], to: [14.3, -0.1] });
const [mol] = addCaption(m3, { text: "far away", x: 30, y: 10 });

for (const id of [first, second]) {
  const r = find(mol, id);
  assert.deepEqual(r.steps.map((s) => s.kind), ["structure", "plus", "structure", "arrow", "structure", "arrow", "structure"], "the whole scheme, in order");
  assert.deepEqual(r.arrows, [first, second]);
  assert.ok(r.captions.includes(plus) && !r.captions.some((c) => mol.captions?.find((x) => x.id === c)?.text === "far away"));
  assert.equal(reactionClean(mol, r, mol.arrows!, layout(mol)), false);
}
{
  const r = find(mol, first), done = clean(mol, r), again = find(done, first);
  assert.equal(again.steps.length, 7, "still one reaction after clean up");
  assert.equal(done.captions!.length, mol.captions!.length, "no plus sign added where there is one");
  for (const g of gaps(done, again)) assert.ok(Math.abs(g - gap) < 1e-6, `even gaps: ${g}`);
  const level = middle(again.steps[0].box)[1];
  for (const s of again.steps) assert.ok(Math.abs(middle(s.box)[1] - level) < 1e-6, "one level line");
  for (const id of [first, second]) { const a = arrowOf(done, id); assert.ok(Math.abs(len(a) - 2 * gap) < 1e-6 && a.to[0] > a.from[0] && a.from[1] === a.to[1], "arrows level, two gaps long, still to the right"); }
  assert.ok(Math.abs(again.steps[0].box[0] - r.steps[0].box[0]) < 1e-6 && Math.abs(level - (arrowOf(mol, first).from[1] + arrowOf(mol, first).to[1]) / 2) < 1e-6, "the reaction stays where it starts, level with its first arrow");
  assert.ok(reactionClean(done, again, done.arrows!, layout(done)), "clean now");
  assert.equal(fragments(done).length, 4);
}

// Conditions placed by hand (from a ChemDraw file) are laid out by Clean Up Reaction, as ChemDraw's lays them out; a
// reaction with them is not clean until then.
{
  const a = arrowOf(mol, first), [withText, cond] = addCaption(mol, { text: "rt", x: 0, y: 0, on: { arrow: first, side: "above" }, placed: { at: [1, 2], arrow: [a.to[0] - a.from[0], a.to[1] - a.from[1]] } });
  const r = find(withText, first), done = clean(withText, r);
  assert.equal(done.captions!.find((c) => c.id === cond)!.placed, undefined, "laid out from now on");
  assert.ok(reactionClean(done, find(done, first), done.arrows!, layout(done)), "clean now");
  assert.ok(!reactionClean({ ...done, captions: done.captions!.map((c) => (c.id === cond ? { ...c, placed: { at: [1, 2], arrow: [0, 0] } } : c)) }, find(done, first), done.arrows!, layout(done)), "not clean with text placed by hand");
}

// Reagents written as text (H2O) stand in the row: Clean up keeps them before the arrow and the product after it.
{
  let t: Mol = EMPTY;
  t = addRing(t, 6, false, { point: [0, 0] });
  const [t1] = addCaption(t, { text: "+", x: 2.2, y: 0, align: "centre" });
  const [t2, water] = addCaption(t1, { text: "H2O", x: 3.6, y: 0.2, align: "centre" });
  const [t3, arrow] = addArrow(t2, { kind: "reaction", from: [5, 0], to: [8, 0] });
  const tm = addRing(t3, 5, false, { point: [10, 0.3] });
  const rr = find(tm, arrow);
  assert.deepEqual(rr.steps.map((s) => s.kind), ["structure", "plus", "text", "arrow", "structure"]);
  const done = clean(tm, rr), a = arrowOf(done, arrow), w = done.captions!.find((c) => c.id === water)!;
  assert.ok(w.x + 0.5 < Math.min(a.from[0], a.to[0]) && Math.max(...fragments(done).map((g) => Math.min(...g.map((i) => pos(done, i)[0])))) > Math.max(a.from[0], a.to[0]), "H2O before the arrow, the product after it");
}

// A plus sign goes between two starting materials (or two products) that have none, as ChemDraw adds them.
{
  let t: Mol = addRing(addRing(EMPTY, 6, false, { point: [0, 0] }), 5, false, { point: [3, 0] });
  let arrow: number;
  [t, arrow] = addArrow(t, { kind: "reaction", from: [5, 0], to: [8, 0] });
  t = addRing(addRing(t, 6, true, { point: [10, 0] }), 4, false, { point: [13, 0] });
  const r = find(t, arrow), done = clean(t, r), pluses = done.captions!.filter((c) => c.text === "+");
  assert.equal(pluses.length, 2, "one plus sign each side");
  const again = find(done, arrow);
  assert.deepEqual(again.steps.map((s) => s.kind), ["structure", "plus", "structure", "arrow", "structure", "plus", "structure"]);
  for (const g of gaps(done, again)) assert.ok(Math.abs(g - gap) < 1e-6, `even gaps with the new plus signs: ${g}`);
}

// Conditions: a structure above the arrow stands centred on it, clear of it, and the arrow is long enough for it with a
// gap each end; text below it is kept on the arrow from now on.
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0] });
  let arrow: number, below: number;
  [t, arrow] = addArrow(t, { kind: "reaction", from: [2, 0], to: [5, 0] });
  t = addRing(t, 6, true, { point: [3.8, 2.2] }); // a reagent drawn above, off centre
  [t, below] = addCaption(t, { text: "reflux", x: 3.5, y: -0.9, align: "centre" });
  t = addRing(t, 5, false, { point: [8, 0.5] });
  const r = find(t, arrow);
  assert.deepEqual(r.steps.map((s) => s.kind), ["structure", "arrow", "structure"], "the reagent is not in the row");
  assert.equal(r.conditions.get(arrow)!.above.length, 1);
  assert.equal(r.conditions.get(arrow)!.below.length, 1);
  const done = clean(t, r), a = arrowOf(done, arrow), reagent = fragments(done)[1], box = ink(done)(reagent);
  assert.ok(Math.abs((box[0] + box[2]) / 2 - (a.from[0] + a.to[0]) / 2) < 1e-6, "centred on the arrow");
  assert.ok(box[1] > a.from[1] && box[1] - a.from[1] < gap, "above it, a little clear");
  assert.ok(len(a) >= box[2] - box[0] + 2 * gap - 1e-6, "the arrow is long enough for it");
  assert.deepEqual(done.captions!.find((c) => c.id === below)!.on, { arrow, side: "below" }, "the text is kept on the arrow");
}

// A reaction drawn right to left stays that way: the product on the left, the arrow pointing at it, and a reagent
// drawn above the arrow stays above it.
{
  let t: Mol = addRing(EMPTY, 5, false, { point: [0, 0.4] });
  let arrow: number;
  [t, arrow] = addArrow(t, { kind: "reaction", from: [6, 0], to: [2.5, 0.3] });
  t = addRing(t, 6, false, { point: [8.5, 0] });
  t = addRing(t, 3, false, { point: [4.2, 1.6] });
  assert.equal(find(t, arrow).conditions.get(arrow)!.above.length, 1, "the reagent is above the arrow");
  const reagent = fragments(t)[2], up = clean(t, find(t, arrow));
  assert.ok(Math.min(...reagent.map((i) => pos(up, i)[1])) > arrowOf(up, arrow).from[1], "and stays above it");
  t = { ...t, atoms: t.atoms.slice(0, reagent[0]), bonds: t.bonds.filter((b) => b.atoms.every((i) => i < reagent[0])) };
  const done = clean(t, find(t, arrow)), a = arrowOf(done, arrow), [product, start] = fragments(done).map((g) => ink(done)(g));
  assert.ok(a.to[0] < a.from[0], "still to the left");
  assert.ok(Math.abs(product[2] - (a.to[0] - gap)) < 1e-6 && Math.abs(start[0] - (a.from[0] + gap)) < 1e-6, "a gap each side, the product at the head");
}

// A reaction down the page stays down the page.
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0] });
  let arrow: number;
  [t, arrow] = addArrow(t, { kind: "reaction", from: [0.2, -1.5], to: [0, -4.5] });
  t = addRing(t, 6, false, { point: [0.4, -6] });
  const done = clean(t, find(t, arrow)), a = arrowOf(done, arrow), [top, bottom] = fragments(done).map((g) => ink(done)(g));
  assert.ok(a.from[0] === a.to[0] && a.to[1] < a.from[1], "a straight arrow down");
  assert.ok(Math.abs(top[1] - (a.from[1] + gap)) < 1e-6 && Math.abs(bottom[3] - (a.to[1] - gap)) < 1e-6, "a gap above and below it");
  assert.ok(Math.abs((top[0] + top[2]) / 2 - a.from[0]) < 1e-6 && Math.abs((bottom[0] + bottom[2]) / 2 - a.from[0]) < 1e-6, "centred on its line");
}

// Too wide for the page: the reaction wraps onto lines, each starting with an arrow, each below the one before and
// centred under the first.
{
  let t: Mol = EMPTY, x = 0;
  const ids: number[] = [];
  for (let k = 0; k < 5; k++) {
    t = addRing(t, 6, false, { point: [x, 0] });
    x += 3;
    if (k < 4) { let id: number; [t, id] = addArrow(t, { kind: "reaction", from: [x - 1.4, 0], to: [x + 1.4, 0] }); ids.push(id); x += 3; }
  }
  const r = find(t, ids[0]), done = clean(t, r, 12);
  const rings = fragments(done).map((g) => ink(done)(g)), heads = ids.map((id) => arrowOf(done, id));
  const levels = [...new Set(rings.map((b) => Math.round(middle(b)[1] * 100) / 100))];
  assert.ok(levels.length >= 2, `more than one line: ${levels}`);
  const lineOf = (y: number) => levels.indexOf(Math.round(y * 100) / 100);
  const parts = [...rings, ...heads.map((a): Box => [Math.min(a.from[0], a.to[0]), a.from[1], Math.max(a.from[0], a.to[0]), a.from[1]])];
  for (const y of levels) {
    const on = parts.filter((b) => lineOf(middle(b)[1]) === lineOf(y));
    assert.ok(Math.max(...on.map((b) => b[2])) - Math.min(...on.map((b) => b[0])) <= 12 + 1e-6, "each line fits the page");
  }
  for (let k = 0; k < 4; k++) {
    const after = rings[k + 1], before = rings[k];
    if (lineOf(middle(after)[1]) !== lineOf(middle(before)[1])) assert.equal(lineOf(heads[k].from[1]), lineOf(middle(after)[1]), "a new line starts with its arrow");
  }
  assert.ok(levels.every((y, k) => !k || y < levels[k - 1]), "each line below the one before");
}

// Two reactions that share a structure (C ← A → B): laid out one after the other, A stays where the first put it.
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0] });
  let left: number, right: number;
  [t, left] = addArrow(t, { kind: "reaction", from: [-1.6, 0.2], to: [-4.5, 0.4] });
  [t, right] = addArrow(t, { kind: "reaction", from: [1.8, -0.2], to: [4.8, 0.3] });
  t = addRing(addRing(t, 5, false, { point: [-6, 0.5] }), 5, false, { point: [6.5, -0.4] });
  const r1 = find(t, left), a = cleanUpReaction(t, r1, t.arrows!, layout(t)), fixed = new Set(r1.atoms);
  const r2 = find(a, right), b = cleanUpReaction(a, r2, a.arrows!, layout(a), fixed);
  for (const i of fragments(t)[0]) assert.deepEqual(pos(b, i), pos(a, i), "the shared structure stays put");
  assert.ok(Math.abs(arrowOf(b, right).from[1] - arrowOf(b, left).from[1]) < 1e-6, "both arrows on one level");
}
// What goes with the parts of a reaction moves with them as it is drawn: text that clings to a structure (a partial
// charge), a number written under it, a reagent its curved arrow comes from; a structure in a box beside the reaction
// (a catalyst) is not a product; an arrow that points the other way ends the row.
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0.6] }); // off the level line, so it moves
  let arrow: number, delta: number, number: number, back: number, push: number;
  [t, delta] = addCaption(t, { text: "δ+", x: 1.25, y: 0.6, align: "left" }); // clings to the ring's right edge
  [t, number] = addCaption(t, { text: "1", x: 0, y: -1.3, align: "centre" }); // a number under it
  [t, arrow] = addArrow(t, { kind: "reaction", from: [3, 0], to: [6, 0] });
  t = addRing(t, 5, false, { point: [8, 0] });
  const hydroxide = t.atoms.length;
  t = addRing(t, 3, false, { point: [8, -2.3] }); // a reagent below the product, pushed in by a curved arrow
  [t, push] = addArrow(t, { kind: "curved", from: [8, -1.9], to: [8, -0.9], bend: 0.2 });
  t = addRing(t, 6, true, { point: [13, 0] });
  [t] = addShape(t, { kind: "box", from: [11.5, -1.5], to: [14.5, 1.5] }); // a catalyst in a box beside it
  [t, back] = addArrow(t, { kind: "reaction", from: [-2, 0], to: [-5, 0] }); // another reaction, to the left
  t = addRing(t, 6, false, { point: [-7, 0] });
  const r = find(t, arrow);
  assert.deepEqual(r.steps.map((s) => s.kind), ["structure", "arrow", "structure"], "δ+, the boxed catalyst and the other reaction are not in the row");
  const done = clean(t, r), moved = (id: number) => done.captions!.find((c) => c.id === id)!;
  const ring = fragments(t)[0], dy = pos(done, ring[0])[1] - pos(t, ring[0])[1];
  assert.ok(Math.abs(dy) > 0.1, "the ring moves to the level line");
  for (const id of [delta, number]) assert.ok(Math.abs(moved(id).y - t.captions!.find((c) => c.id === id)!.y - dy) < 1e-9, "its text goes with it");
  const before = pos(t, hydroxide), after = pos(done, hydroxide), product = fragments(t)[1][0];
  assert.deepEqual([after[0] - before[0], after[1] - before[1]].map((v) => Math.round(v * 1e6)), [pos(done, product)[0] - pos(t, product)[0], pos(done, product)[1] - pos(t, product)[1]].map((v) => Math.round(v * 1e6)), "the reagent goes with the product");
  assert.ok(Math.abs(arrowOf(done, push).from[0] - arrowOf(t, push).from[0] - (pos(done, product)[0] - pos(t, product)[0])) < 1e-9, "and so does the curved arrow");
  assert.deepEqual(arrowOf(done, back), arrowOf(t, back), "the other reaction is left alone");
  assert.equal(done.captions!.filter((c) => c.text === "+").length, 0, "no plus sign before the boxed catalyst");
}

// A drawing by an arrow's conditions (a lamp drawn beside them) keeps the conditions as drawn: they move with the
// arrow, which grows to reach a gap past them. Text that starts with a plus sign needs no plus sign before it.
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0] });
  let arrow: number, text: number, water: number;
  [t, arrow] = addArrow(t, { kind: "reaction", from: [2, 0], to: [9, 0] });
  [t, text] = addCaption(t, { text: "hv", x: 4, y: 0.6, align: "left" });
  const [t1, lamp] = addArrow(t, { kind: "curve", from: [6, 0.4], to: [6.6, 0.4], curve: { points: [{ at: [6, 0.4] }, { at: [6.3, 1.2] }, { at: [6.6, 0.4] }], closed: true } });
  t = addRing(t1, 5, false, { point: [11, 0] });
  [t, water] = addCaption(t, { text: "+H2O", x: 13.5, y: 0, align: "centre" });
  const r = find(t, arrow), done = clean(t, r), a = arrowOf(done, arrow);
  assert.deepEqual(r.steps.map((s) => s.kind), ["structure", "arrow", "structure", "text"]);
  const d = (a.from[0] + a.to[0]) / 2 - (arrowOf(t, arrow).from[0] + arrowOf(t, arrow).to[0]) / 2, c = done.captions!.find((x) => x.id === text)!;
  assert.ok(Math.abs(c.x - 4 - d) < 1e-9 && !c.on, "the text keeps its place by the arrow");
  assert.ok(Math.abs(arrowOf(done, lamp).from[0] - 6 - d) < 1e-9, "the lamp too");
  assert.ok(Math.min(a.from[0], a.to[0]) <= 4 + d - gap + 1e-6 && Math.max(a.from[0], a.to[0]) >= 6.6 + d + gap - 1e-6, "the arrow reaches past them");
  assert.equal(done.captions!.filter((x) => x.text === "+").length, 0, "+H2O has its plus sign");
  assert.ok(done.captions!.find((x) => x.id === water));
}

// Clean up with nothing picked lays out only a reaction with a structure in its row. Arrows among text alone (a
// spectrum's labels) and a lone atom used as a word are not a reaction to lay out.
{
  let t: Mol = EMPTY, arrow: number;
  [t] = addCaption(t, { text: "Ru(bpy)3", x: -1, y: 0, align: "centre" });
  [t, arrow] = addArrow(t, { kind: "reaction", from: [1.5, 0], to: [4.5, 0] });
  [t] = addCaption(t, { text: "Eosin Y", x: 6, y: 0, align: "centre" });
  [t] = addCaption(t, { text: "visible light", x: 3, y: 0.6, align: "centre" });
  const words = find(t, arrow);
  assert.deepEqual(words.steps.map((s) => s.kind), ["text", "arrow", "text"]);
  assert.ok(!withStructure(words), "text alone");
  const word: Mol = { ...t, atoms: [{ label: "C", text: "Direct", location: [0, 0, 0] }], captions: t.captions!.filter((c) => c.text !== "Ru(bpy)3") };
  assert.ok(!withStructure(find(word, arrow)), "a lone atom used as a word");
  const real = addRing(t, 6, false, { point: [-5.5, 0] });
  assert.deepEqual(find(real, arrow).steps.map((s) => s.kind), ["structure", "text", "arrow", "text"]);
  assert.ok(withStructure(find(real, arrow)), "a ring before the arrow");
}

// A name under a structure, wider than it, goes with it: the structure does not move away from its name. The name takes
// room in the row, so nothing beside it runs into it. A second clean-up changes nothing.
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0.4] }); // above the arrow's line, so it moves
  let arrow: number, name: number;
  [t, name] = addCaption(t, { text: "compound name", x: 0, y: -1.6, align: "centre" });
  [t, arrow] = addArrow(t, { kind: "reaction", from: [3, 0], to: [6, 0] });
  t = addRing(t, 6, false, { point: [8.5, 0] });
  const done = clean(t, find(t, arrow)), ring = fragments(t)[0], a = arrowOf(done, arrow);
  const dv = [0, 1].map((k) => pos(done, ring[0])[k] - pos(t, ring[0])[k]), was = t.captions!.find((c) => c.id === name)!, now = done.captions!.find((c) => c.id === name)!;
  assert.ok(Math.abs(dv[1]) > 0.1, "the ring moves to the level line");
  assert.ok(Math.abs(now.x - was.x - dv[0]) < 1e-9 && Math.abs(now.y - was.y - dv[1]) < 1e-9, "its name goes with it");
  assert.ok(Math.abs(Math.min(a.from[0], a.to[0]) - capBox(done)(name)![2] - gap) < 1e-6, "the arrow is a gap after the name");
  assert.deepEqual(clean(done, find(done, arrow)), done, "a second clean-up changes nothing");
}

// A small structure drawn over a larger one (a substituent's bond drawn apart from its ring) goes with it, and the
// larger one stays in the row, wherever the small one starts. A second clean-up changes nothing.
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0] });
  let arrow: number;
  [t, arrow] = addArrow(t, { kind: "reaction", from: [2, 0], to: [5, 0] });
  t = addRing(t, 6, false, { point: [8, 0] }); // from 7.13 to 8.87 across the page
  const n = t.atoms.length;
  t = { ...t, atoms: [...t.atoms, { label: "C", location: [6.5, -0.3, 0] }, { label: "C", location: [7.6, -0.3, 0] }], bonds: [...t.bonds, { type: 1, atoms: [n, n + 1] }] };
  const r = find(t, arrow);
  assert.deepEqual(r.steps.map((s) => (s.kind === "structure" ? s.atoms.length : s.kind)), [6, "arrow", 6], "the product ring is in the row, not the bond");
  assert.deepEqual((r.steps[2] as { carry?: { atoms: number[] } }).carry?.atoms, [n, n + 1], "the ring carries the bond");
  const done = clean(t, r);
  assert.deepEqual(clean(done, find(done, arrow)), done, "a second clean-up changes nothing");
}

// Clean Up Reaction on the whole drawing as the editor runs it (Editor.tsx cleanReactions): structures drawn, arrows
// grown to fit their text, and captions placed and measured as the renderer places them. Node has no fonts, so text is
// measured roughly here (0.55 of its size a letter, labels 0.6); the editor measures it in its font.
const L = 19.2, toDoc = (b: Box): Box => [b[0] / L, -b[3] / L, b[2] / L, -b[1] / L];
const drawn = (m: Mol) => {
  const style = readStyle(m.style ?? {}), frame = frameStyle(style, L), pt = (4 / 3) * frame.k;
  const measure = (text: string) => { const s = frame.size, w = 0.6 * s * text.length; return { width: w, ascent: 0.72 * s, outline: [[0, -0.72 * s], [w, -0.72 * s], [w, 0.2 * s], [0, 0.2 * s]] as [number, number][] }; };
  const width = (text: string, c: { size?: number }) => 0.55 * (c.size ?? style.captionSize) * pt * text.length;
  const drawing = render(m, frame, measure, L), arrows = fitArrows(m, L, (c) => Math.max(...c.text.split("\n").map((x) => width(x, c))), pt);
  const placed = placeCaptions(m, drawing, width, arrows, pt, style.captionSize);
  const captionBox = (id: number) => { const c = placed.find((x) => x.id === id); return c && toDoc(c.box); };
  const inkOf = (mol: Mol) => {
    const d = mol === m ? drawing : render(mol, frame, measure, L);
    return (atoms: number[]): Box | undefined => { const bs = atoms.flatMap((i) => (d.ink[i] ? [d.ink[i]] : [])); return bs.length ? toDoc([Math.min(...bs.map((b) => b[0])), Math.min(...bs.map((b) => b[1])), Math.max(...bs.map((b) => b[2])), Math.max(...bs.map((b) => b[3]))]) : undefined; };
  };
  const size = (style.captionSize * pt) / L, w = width("+", {}) / L;
  const o: Layout = { gap: gapFor(style.captionSize, style.bond), width: ((pageSize(style)[0] * 72) / 25.4 - 72) / style.bond, captionBox, plusBox: [-w / 2, -DESCENT * size, w / 2, ASCENT * size], captionPt: style.captionSize, bondPt: style.bond };
  return { arrows, captionBox, ink: inkOf(m), inkOf, o };
};
const cleanAll = (m: Mol, pick: (r: Reaction) => boolean) => { const d = drawn(m); return cleanUpReactions(m, d.arrows, d.inkOf, d.o, pick); };
const points = (m: Mol) => [
  ...m.atoms.map((a) => a.location.slice(0, 2)), ...(m.captions ?? []).map((c) => [c.x, c.y]), ...(m.shapes ?? []).flatMap((x) => [x.from, x.to]),
  ...(m.arrows ?? []).flatMap((a) => [a.from, a.to, ...(a.curve?.points.map((q) => q.at) ?? [])]),
];
// Everything as drawn after a clean-up: each structure's ink, each caption's box and each straight arrow's shaft.
const laidOut = (m: Mol) => {
  const d = drawn(m), arrows = d.arrows.filter((a) => straightArrow(a));
  const boxes: [string, Box][] = [
    ...fragments(m).map((g, k): [string, Box] => [`structure ${k}`, d.ink(g)!]),
    ...(m.captions ?? []).map((c): [string, Box] => [c.text, d.captionBox(c.id)!]),
    ...arrows.map((a): [string, Box] => [`arrow ${a.id}`, [Math.min(a.from[0], a.to[0]), Math.min(a.from[1], a.to[1]) - 0.05, Math.max(a.from[0], a.to[0]), Math.max(a.from[1], a.to[1]) + 0.05]]),
  ];
  return { d, arrows, boxes };
};
const overlaps = (boxes: [string, Box][]) => boxes.flatMap(([p, a], k) => boxes.slice(k + 1).flatMap(([q, b]) => (a[0] < b[2] - 1e-6 && b[0] < a[2] - 1e-6 && a[1] < b[3] - 1e-6 && b[1] < a[3] - 1e-6 ? [`${p} / ${q}`] : [])));
const widthOf = (b: Box) => b[2] - b[0];
const midOf = (b: Box) => (b[0] + b[2]) / 2;

// Sam's scheme (29 Oct 2026): two reactants with a plus sign, a CAS number and a price under the second, two lines of
// conditions above a straight arrow and four below, each a caption of its own, one product and its yield beside it (or
// under it). Clean up lays it out as Sam laid it out by hand: the arrow as long as its widest line with a gap each end,
// the lines centred on it in the order drawn, the text under a structure kept under it and spaced round, the yield
// kept with the product (no plus sign before it), everything level on the arrow's line, nothing overlapping.
for (const under of [false, true]) {
  let t: Mol = addRing(EMPTY, 6, true, { point: [0, 0.2] });
  let arrow: number, cas: number, price: number, yld: number;
  [t] = addCaption(t, { text: "+", x: 2.3, y: -0.3, align: "centre" });
  t = addRing(t, 6, false, { point: [4.4, 0.5] });
  [t, cas] = addCaption(t, { text: "CAS 100-63-0", x: 4.6, y: -1.9, align: "centre" });
  [t, price] = addCaption(t, { text: "£24 / 10g", x: 4.4, y: -2.75, align: "centre" });
  [t, arrow] = addArrow(t, { kind: "reaction", from: [7.4, 0.1], to: [17, 0] });
  const above = ["[PdCl(allyl)]2 (1 mol%)", "t-BuXPhos (4 mol%)"], below = ["Cs2CO3 (2 eq.)", "H2O (2 eq.)", "DME, 90°C, 15h", "O2 (1 atm)"];
  const lines: number[] = [];
  for (const [k, text] of above.entries()) { let id: number; [t, id] = addCaption(t, { text, x: 12.4 - 0.4 * k, y: 1.5 - 0.85 * k, align: "centre" }); lines.push(id); }
  for (const [k, text] of below.entries()) { let id: number; [t, id] = addCaption(t, { text, x: 11.9 + 0.3 * (k % 2), y: -0.9 - 0.85 * k, align: "centre" }); lines.push(id); }
  t = addRing(t, 6, true, { point: [19.6, -0.3] });
  [t, yld] = addCaption(t, { text: "35%", ...(under ? { x: 19.6, y: -2.2 } : { x: 21.5, y: -0.4 }), align: "centre" });
  const how = under ? "yield under" : "yield beside";
  const r = findReaction(t, arrow, drawn(t).arrows, drawn(t).ink, drawn(t).captionBox)!;
  assert.deepEqual(r.steps.map((s) => s.kind), ["structure", "plus", "structure", "arrow", "structure"], `${how}: the yield is not a product`);
  assert.deepEqual([r.conditions.get(arrow)!.above.length, r.conditions.get(arrow)!.below.length], [2, 4], `${how}: two lines above, four below`);
  const done = cleanAll(t, withStructure);
  assert.equal(done.count, 1, `${how}: one reaction laid out`);
  const out = done.mol, { d, boxes } = laidOut(out), a = d.arrows.find((x) => x.id === arrow)!, g = gapFor(10, 14.4);
  assert.deepEqual(overlaps(boxes), [], `${how}: nothing overlaps`);
  assert.equal(out.captions!.filter((c) => c.text === "+").length, 1, `${how}: no plus sign before the yield`);
  // The conditions: kept on the arrow, centred on it, in the order drawn, and the arrow long enough for the widest.
  const box = (id: number) => d.captionBox(id)!, byText = (text: string) => out.captions!.find((c) => c.text === text)!;
  for (const id of lines) assert.ok(out.captions!.find((c) => c.id === id)!.on?.arrow === arrow, `${how}: each line is kept on the arrow`);
  const mid = (a.from[0] + a.to[0]) / 2, widest = Math.max(...lines.map((id) => widthOf(box(id))));
  for (const id of lines) assert.ok(Math.abs(midOf(box(id)) - mid) < 1e-6, `${how}: each line centred on the arrow`);
  assert.ok(Math.abs(a.to[0] - a.from[0]) >= widest + 2 * g - 1e-6 && a.from[1] === a.to[1], `${how}: the arrow is level and reaches a gap past its widest line`);
  const ys = (texts: string[]) => texts.map((x) => box(byText(x).id)[1]);
  assert.ok(ys(above).every((y, k, all) => !k || y < all[k - 1]) && ys(above).every((y) => y > a.from[1]), `${how}: the lines above, in the order drawn`);
  assert.ok(ys(below).every((y, k, all) => !k || y < all[k - 1]) && ys(below).every((y) => y < a.from[1]), `${how}: the lines below, in the order drawn`);
  // The structures: level on the arrow's line, with what goes under or beside them moved with them.
  const [, second, product] = fragments(t), shift = (atoms: number[]) => [0, 1].map((k) => pos(out, atoms[0])[k] - pos(t, atoms[0])[k]);
  for (const s of fragments(out)) assert.ok(Math.abs((d.ink(s)![1] + d.ink(s)![3]) / 2 - a.from[1]) < 1e-6, `${how}: each structure centred on the arrow's line`);
  const moved = (id: number) => { const p = t.captions!.find((c) => c.id === id)!, q = out.captions!.find((c) => c.id === id)!; return [q.x - p.x, q.y - p.y]; };
  for (const id of [cas, price]) {
    assert.ok(moved(id).every((v, k) => Math.abs(v - shift(second)[k]) < 1e-9), `${how}: ${t.captions!.find((c) => c.id === id)!.text} moves with its structure`);
    assert.ok(box(id)[3] < d.ink(second)![1] && midOf(box(id)) > d.ink(second)![0] && midOf(box(id)) < d.ink(second)![2], `${how}: and stays under it`);
  }
  assert.ok(moved(yld).every((v, k) => Math.abs(v - shift(product)[k]) < 1e-9), `${how}: the yield moves with the product`);
  const again = cleanAll(out, withStructure).mol, p = points(out), q = points(again);
  assert.ok(p.length === q.length && p.every((x, k) => Math.hypot(x[0] - q[k][0], x[1] - q[k][1]) < 1e-6), `${how}: a second clean-up moves nothing`);
}
// Sam's scheme as a friend drew it before tidying (29 Oct 2026): the arrow shorter than its conditions and more than
// REACH from the reactants, the product drawn so far left that its box runs under the arrowhead, and the CAS number
// and price 1.7 bond lengths under their structure. The whole row is still found, and the text under the structure
// goes with it.
{
  let t: Mol = addRing(EMPTY, 6, true, { point: [0, 0.2] });
  let arrow: number, cas: number, price: number;
  [t] = addCaption(t, { text: "+", x: 2.3, y: 0, align: "centre" });
  t = addRing(t, 6, false, { point: [4.4, 0.3] });
  [t, cas] = addCaption(t, { text: "CAS 100-63-0", x: 4.4, y: -2.4, align: "centre" });
  [t, price] = addCaption(t, { text: "£24 / 10g", x: 4.4, y: -3.3, align: "centre" });
  [t, arrow] = addArrow(t, { kind: "reaction", from: [10.6, 0], to: [13.8, 0] });
  for (const [k, text] of ["[PdCl(allyl)]2 (1 mol%)", "t-BuXPhos (4 mol%)"].entries()) [t] = addCaption(t, { text, x: 12.2, y: 1.4 - 0.85 * k, align: "centre" });
  for (const [k, text] of ["Cs2CO3 (2 eq.)", "H2O (2 eq.)", "DME, 90°C, 15h", "O2 (1 atm)"].entries()) [t] = addCaption(t, { text, x: 12.2, y: -0.9 - 0.85 * k, align: "centre" });
  t = addRing(t, 6, true, { point: [14.1, -0.6] });
  const r = findReaction(t, arrow, drawn(t).arrows, drawn(t).ink, drawn(t).captionBox)!;
  assert.deepEqual(r.steps.map((s) => s.kind), ["structure", "plus", "structure", "arrow", "structure"], "drawn before tidying: the whole row");
  const done = cleanAll(t, withStructure), out = done.mol, { d, boxes } = laidOut(out), second = fragments(out)[1];
  assert.deepEqual(overlaps(boxes), [], "drawn before tidying: nothing overlaps");
  for (const id of [cas, price]) assert.ok(d.captionBox(id)![3] < d.ink(second)![1] && Math.abs(midOf(d.captionBox(id)!) - midOf(d.ink(second)!)) < 0.3, "drawn before tidying: the CAS number and price stay under their structure");
}
// The same scheme typed as one caption for each block (lines kept in one text): laid out the same way.
{
  let t: Mol = addRing(EMPTY, 6, true, { point: [0, 0.2] });
  let arrow: number, note: number, up: number, down: number;
  [t] = addCaption(t, { text: "+", x: 2.3, y: -0.3, align: "centre" });
  t = addRing(t, 6, false, { point: [4.4, 0.5] });
  [t, note] = addCaption(t, { text: "CAS 100-63-0\n£24 / 10g", x: 4.6, y: -1.9, align: "centre" });
  [t, arrow] = addArrow(t, { kind: "reaction", from: [7.4, 0.1], to: [14.4, 0] });
  [t, up] = addCaption(t, { text: "[PdCl(allyl)]2 (1 mol%)\nt-BuXPhos (4 mol%)", x: 10.4, y: 1.4, align: "centre" });
  [t, down] = addCaption(t, { text: "Cs2CO3 (2 eq.)\nH2O (2 eq.)\nDME, 90°C, 15h\nO2 (1 atm)", x: 9.4, y: -0.9, align: "centre" });
  t = addRing(t, 6, true, { point: [16.6, -0.3] });
  [t] = addCaption(t, { text: "35%", x: 18.5, y: -0.4, align: "centre" });
  const done = cleanAll(t, withStructure), out = done.mol, { d, boxes } = laidOut(out), a = d.arrows.find((x) => x.id === arrow)!, mid = (a.from[0] + a.to[0]) / 2;
  assert.equal(done.count, 1, "one caption a block: laid out");
  assert.deepEqual(overlaps(boxes), [], "one caption a block: nothing overlaps");
  assert.deepEqual([up, down].map((id) => out.captions!.find((c) => c.id === id)!.on?.side), ["above", "below"], "one caption a block: kept on the arrow");
  for (const id of [up, down]) assert.ok(Math.abs(midOf(d.captionBox(id)!) - mid) < 1e-6, "one caption a block: centred on the arrow");
  assert.ok(Math.abs(a.to[0] - a.from[0]) >= Math.max(widthOf(d.captionBox(up)!), widthOf(d.captionBox(down)!)) + 2 * gapFor(10, 14.4) - 1e-6, "one caption a block: the arrow reaches a gap past its widest line");
  const second = d.ink(fragments(out)[1])!;
  assert.ok(d.captionBox(note)![3] < second[1] && Math.abs(midOf(d.captionBox(note)!) - midOf(second)) < 0.3, "one caption a block: the note stays under its structure");
  assert.equal(out.captions!.filter((c) => c.text === "+").length, 1, "one caption a block: no plus sign before the yield");
}

// Conditions only below an arrow, and only above the next, in a scheme of two steps (A → B → C), each line a caption of
// its own: each arrow fits its own lines, which are centred on it in the order drawn, and nothing overlaps.
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0] });
  let first: number, second: number;
  [t, first] = addArrow(t, { kind: "reaction", from: [2, 0.2], to: [5, 0] });
  const [t1, nah] = addCaption(t, { text: "NaH, THF", x: 3.4, y: -0.9, align: "centre" });
  const [t2, temp] = addCaption(t1, { text: "0 °C to rt, 2 h", x: 3.7, y: -1.75, align: "centre" });
  t = addRing(t2, 5, false, { point: [8, 0.4] });
  [t, second] = addArrow(t, { kind: "reaction", from: [10, 0], to: [13, 0.1] });
  const [t3, h2] = addCaption(t, { text: "H2, Pd/C", x: 11.6, y: 0.7, align: "centre" });
  t = addRing(t3, 6, true, { point: [15.5, -0.2] });
  const done = cleanAll(t, withStructure), out = done.mol, { d, boxes } = laidOut(out), g = gapFor(10, 14.4);
  assert.equal(done.count, 1, "one scheme of two steps");
  assert.deepEqual(overlaps(boxes), [], "nothing overlaps");
  for (const [arrow, ids, side] of [[first, [nah, temp], "below"], [second, [h2], "above"]] as const) {
    const a = d.arrows.find((x) => x.id === arrow)!, mid = (a.from[0] + a.to[0]) / 2;
    for (const id of ids) {
      assert.deepEqual(out.captions!.find((c) => c.id === id)!.on, { arrow, side }, "kept on its arrow, on its side");
      assert.ok(Math.abs(midOf(d.captionBox(id)!) - mid) < 1e-6, "centred on it");
    }
    assert.ok(Math.abs(a.to[0] - a.from[0]) >= Math.max(...ids.map((id) => widthOf(d.captionBox(id)!))) + 2 * g - 1e-6, "the arrow reaches a gap past its text");
    for (const s of fragments(out)) assert.ok(Math.abs((d.ink(s)![1] + d.ink(s)![3]) / 2 - a.from[1]) < 1e-6, "one level line");
  }
  assert.ok(d.captionBox(nah)![1] > d.captionBox(temp)![1], "the lines below in the order drawn");
}

// One word above the arrow, as Clean Up Reaction laid it out before text under structures and stacks of lines were
// read (to 1e-6 bond lengths).
{
  let t: Mol = addRing(EMPTY, 6, false, { point: [0, 0.3] });
  let arrow: number;
  [t, arrow] = addArrow(t, { kind: "reaction", from: [2.2, 0], to: [5.6, 0.2] });
  [t] = addCaption(t, { text: "heat", x: 4.1, y: 0.7, align: "centre" });
  t = addRing(t, 5, false, { point: [8, -0.3] });
  const done = cleanAll(t, withStructure).mol, round = (v: number) => Math.round(v * 1e6) / 1e6 + 0;
  const a = done.arrows!.find((x) => x.id === arrow)!;
  const ONE_WORD = { arrow: [1.928525, 0.1, 5.539637, 0.1], atoms: [[0, 1.1], [-0.866025, 0.6], [-0.866025, -0.4], [0, -0.9], [0.866025, -0.4], [0.866025, 0.6], [7.414811, 0.866962], [6.605794, 0.279177], [6.914811, -0.67188], [7.914811, -0.67188], [8.223828, 0.279177]] };
  assert.deepEqual([...a.from, ...a.to].map(round), ONE_WORD.arrow, "the arrow as before");
  assert.deepEqual(done.atoms.map((x) => [round(x.location[0]), round(x.location[1])]), ONE_WORD.atoms, "the structures as before");
  assert.deepEqual(done.captions!.map((c) => [c.text, c.on?.side ?? ""]), [["heat", "above"]], "the word kept on the arrow, above it");
}

// Sam's corpus (on this Mac only): Clean Up Reaction on the whole drawing, as the editor runs it, is a fixed point. On
// each file with a straight arrow, a second clean-up changes no coordinate, with nothing selected (reactions with a
// structure) and with everything selected (every reaction, a spectrum's arrows and labels too).
const CORPUS = join(homedir(), "octet-research/corpus/sam");
if (!existsSync(CORPUS)) console.log("reaction.check: no corpus here, corpus part skipped");
else {
  let files = 0, laid = 0;
  for (const f of readdirSync(CORPUS).filter((x) => x.endsWith(".cdxml")).sort()) {
    const start = wholeGroups(readOct(readFileSync(join(CORPUS, f), "utf8")).mol);
    if (!(start.arrows ?? []).some((a) => straightArrow(a))) continue;
    files++;
    for (const [pick, how] of [[withStructure, "nothing selected"], [() => true, "everything selected"]] as const) {
      const once = cleanAll(start, pick), twice = cleanAll(once.mol, pick);
      if (once.count && pick === withStructure) laid++;
      const p = points(once.mol), q = points(twice.mol);
      assert.equal(q.length, p.length, `${f}, ${how}: the second clean-up adds nothing`);
      const moved = p.flatMap((x, k) => { const d = Math.hypot(x[0] - q[k][0], x[1] - q[k][1]); return d > 1e-6 ? [d] : []; });
      assert.equal(moved.length, 0, `${f}, ${how}: the second clean-up moves ${moved.length} points, up to ${Math.max(0, ...moved).toFixed(3)} bond lengths`);
    }
  }
  assert.ok(laid > 10, `the corpus has reactions to lay out (${laid})`);
  console.log(`reaction.check: ${files} corpus files with a straight arrow (${laid} laid out), a second clean-up moves nothing`);
}

// Search Reaxys: a structure's part in the scheme A + B → C → D, or none for one in no reaction.
{
  const [a, b, c, d] = fragments(mol), all = [find(mol, first)];
  assert.equal(roleOf(all, [a]), "starting_material");
  assert.equal(roleOf(all, [a, b]), "starting_material", "both starting materials");
  assert.equal(roleOf(all, [c]), "all_reactions", "between two arrows: made in one step, used in the next");
  assert.equal(roleOf(all, [d]), "product");
  assert.equal(roleOf(all, [a, d]), "mixed", "both sides: a reaction search");
  assert.equal(roleOf([], [a]), undefined, "in no reaction: a substance search");
  assert.equal(roleOf([], [a, b]), undefined);
}
console.log("reaction.check: ok");
