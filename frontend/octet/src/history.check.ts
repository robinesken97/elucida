// Run: node src/history.check.ts. Fails loudly if the undo history can grow without end (issue 2): it keeps 1000 steps
// at most, fewer on a drawing so large that they would hold more than 2,000,000 objects, and never fewer than 200.
import assert from "node:assert/strict";
import { FEWEST_STEPS, history, MOST_OBJECTS, MOST_STEPS, type History } from "./history.ts";
import type { Mol } from "./render.ts";

const drawing = (atoms: number, n: number): Mol => ({ atoms: Array.from({ length: atoms }, (_, i) => ({ label: "C", location: [i + n, 0, 0] })), bonds: [] });
// count edits, each a new drawing, after the drawing make(0).
const run = (make: (n: number) => Mol, count: number) => {
  let h: History = { stack: [make(0)], at: 0 };
  for (let n = 1; n <= count; n++) h = history(h, { type: "set", mol: make(n) });
  return h;
};

// A long session on a small drawing: the oldest steps go, the newest stay, and the drawing is the last edit.
const small = run((n) => drawing(1, n), 1500);
assert.equal(small.stack.length, MOST_STEPS);
assert.equal(small.at, MOST_STEPS - 1);
assert.equal(small.stack[small.at].atoms[0].location[0], 1500);
assert.equal(small.stack[0].atoms[0].location[0], 1500 - MOST_STEPS + 1, "the oldest steps go first");
// Undo still goes back step by step, and redo comes forward again.
let back = small;
for (let k = 0; k < 5; k++) back = history(back, { type: "undo" });
assert.equal(back.stack[back.at].atoms[0].location[0], 1495);
assert.equal(history(back, { type: "redo" }).stack[back.at + 1].atoms[0].location[0], 1496);
// An edit after undo drops the steps it replaces, as before.
const branched = history(back, { type: "set", mol: drawing(1, -1) });
assert.equal(branched.at, branched.stack.length - 1);
assert.equal(branched.stack.length, back.at + 2);

// A large drawing: fewer steps, by the objects they hold, but never fewer than 200. Its steps share one list of atoms
// here, so the check itself stays small; each step is told apart by its annotation.
const sized = (atoms: Mol["atoms"]) => (n: number): Mol => ({ atoms, bonds: [], annotations: [{ keyword: String(n), content: "" }] });
const big = 5000, large = run(sized(drawing(big, 0).atoms), 600);
assert.ok(large.stack.length < MOST_STEPS && large.stack.length >= FEWEST_STEPS, `kept ${large.stack.length} steps`);
assert.ok(large.stack.length * big <= MOST_OBJECTS, "the steps hold 2,000,000 objects at most");
assert.equal(large.stack[large.at].annotations![0].keyword, "600");
const huge = run(sized(drawing(50_000, 0).atoms), 260);
assert.equal(huge.stack.length, FEWEST_STEPS, "200 steps always stay");
assert.equal(huge.at, FEWEST_STEPS - 1);

// A dragged slider is still one step, however long the drag.
let dragged: History = { stack: [drawing(1, 0), drawing(1, 1)], at: 1 };
for (let n = 0; n < 2000; n++) dragged = history(dragged, { type: "set", mol: drawing(1, n), merge: "slider" });
assert.equal(dragged.stack.length, 3);

// An amend changes the step just made, with no step of its own: Undo goes back past both (an experiment page's box
// grown for a table, Editor.tsx).
{
  let h: History = { stack: [{ atoms: [], bonds: [] }], at: 0 };
  h = history(h, { type: "set", mol: { atoms: [], bonds: [], captions: [] } });
  const amended: Mol = { atoms: [], bonds: [], shapes: [] };
  h = history(h, { type: "amend", mol: amended });
  assert.deepEqual([h.stack.length, h.at, h.stack[1]], [2, 1, amended]);
  assert.equal(history(h, { type: "undo" }).at, 0);
}

console.log("history: ok");
