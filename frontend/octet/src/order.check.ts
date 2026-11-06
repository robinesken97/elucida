// Run: node src/order.check.ts. Fails loudly if Bring to Front or Send to Back breaks.
import assert from "node:assert/strict";
import { toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { EMPTY, fragments, merge, sprout } from "./edit.ts";
import { onTop, reorder } from "./order.ts";
import type { Mol } from "./render.ts";

// Two ethanes, a box, an arrow and a caption.
const two = merge(sprout(EMPTY, [0, 0]), sprout(EMPTY, [0, 0]), [3, 0]);
const m: Mol = { ...two, shapes: [{ id: 1, kind: "box", from: [0, 0], to: [1, 1] }], arrows: [{ id: 2, kind: "reaction", from: [0, 0], to: [1, 0] }], captions: [{ id: 3, text: "A", x: 0, y: 0 }] };

// Nothing selected: nothing moves.
assert.equal(reorder(m, [], new Set(), true), m);

// The box to the front: over everything, so its order is above zero.
const a = reorder(m, [], new Set([1]), true);
assert.equal(a.shapes![0].order, 1);
// Then the first structure to the front: over the box. Every atom of it takes the order.
const b = reorder(a, [[0, 1]], new Set(), true);
assert.deepEqual(b.atoms.map((x) => x.order), [2, 2, undefined, undefined]);
// The arrow and the caption to the back together: under everything, the arrow (drawn first) lowest.
const c = reorder(b, [], new Set([2, 3]), false);
assert.equal(c.arrows![0].order, -2);
assert.equal(c.captions![0].order, -1);
// Again to the front: they keep their order among themselves, over the structure.
const d = reorder(c, [], new Set([2, 3]), true);
assert.deepEqual([d.arrows![0].order, d.captions![0].order], [3, 4]);
// Nothing else changes.
assert.equal(d.bonds, m.bonds);
assert.deepEqual(d.atoms.map((x) => x.location), m.atoms.map((x) => x.location));

// CDXML: the box sent to the back is under every other object (lowest Z); the structure brought to the front is over
// every other object (its fragment and every node and bond in it have the highest Zs).
{
  const e = reorder(reorder(m, [], new Set([1]), false), [[0, 1]], new Set(), true);
  const xml = toCdxml(e, DEFAULT_STYLE, { name: "order.cdxml" });
  const zs = (tag: string) => [...xml.matchAll(new RegExp(`<${tag}\\b[^>]*?\\bZ="(\\d+)"`, "g"))].map((x) => Number(x[1]));
  const all = zs("[a-z]+"), box = zs("graphic").filter((_, k) => k === 0)[0], frags = zs("fragment");
  assert.equal(Math.min(...all), box, "the box is lowest");
  assert.ok(Math.max(...frags) > Math.max(...zs("t"), ...zs("arrow")), "the structure is over the arrow and the text");
  assert.ok(all.every((z) => z > 0 && z <= 32767), "every Z is a 16-bit Z");
}
// A thing added after something was brought to the front goes over it, as a new object does in ChemDraw: a new box, a
// new caption and a new structure take the next order. What was there keeps its order.
{
  const front = reorder(m, [], new Set([1]), true);
  assert.equal(onTop(m, { ...m, shapes: [...m.shapes!, { id: 9, kind: "box", from: [0, 0], to: [1, 1] }] }, fragments).shapes![1].order, undefined, "nothing in front: no change");
  const added = { ...front, shapes: [...front.shapes!, { id: 9, kind: "box" as const, from: [0, 0] as [number, number], to: [1, 1] as [number, number] }], captions: [...front.captions!, { id: 10, text: "B", x: 0, y: 0 }] };
  const bigger = merge(added, sprout(EMPTY, [0, 0]), [6, 0]);
  const top = onTop(front, bigger, fragments);
  assert.deepEqual([top.shapes!.map((x) => x.order), top.captions!.map((x) => x.order)], [[1, 2], [undefined, 2]]);
  assert.deepEqual(top.atoms.map((x) => x.order), [undefined, undefined, undefined, undefined, 2, 2]);
  // An atom added to a structure that was there takes the structure's order, in front or at the back.
  const grown = sprout(front, 0);
  assert.equal(onTop(front, grown, fragments).atoms.every((x) => !x.order), true);
  const back = reorder(m, [[0, 1]], new Set(), false);
  assert.deepEqual(onTop(back, sprout(back, 0), fragments).atoms.map((x) => x.order), [-1, -1, undefined, undefined, -1]);
  // A drawing that keeps nothing of the one before (a file opened) is left as it is.
  const opened = { ...m, atoms: m.atoms.map((a) => ({ ...a })), shapes: m.shapes!.map((x) => ({ ...x })), captions: [], arrows: [] };
  assert.equal(onTop(front, opened, fragments), opened);
}
console.log("order: ok");
