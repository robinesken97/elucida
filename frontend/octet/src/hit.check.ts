// Run: node src/hit.check.ts. Fails loudly if hit testing against kept paths differs from testing every path.
import assert from "node:assert/strict";
import { arrowTrace, distToPath, kept, lobesOf, nearTrace, shapeTrace } from "./hit.ts";
import { arrowPath, orbitalPaths, shapePaths, type Arrow, type Shape } from "./render.ts";

type P = [number, number];
let seed = 7;
const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
const at = (): P => [rand() * 8 - 4, rand() * 8 - 4];
const L = 19.2;

// Arrows of every path kind: straight, bent, and pen curves with handles.
const arrows: Arrow[] = [];
for (let i = 0; i < 60; i++) {
  const kind = (["reaction", "curved", "arc", "line", "curve"] as const)[i % 5];
  const pts = [at(), at(), at()].map((q, k) => ({ at: q, ...(k % 2 ? { c1: at(), c2: at() } : {}) }));
  arrows.push({ id: i, kind, from: at(), to: at(), ...(kind === "curved" || kind === "arc" ? { bend: rand() - 0.5 } : {}), ...(kind === "curve" ? { curve: { points: pts, closed: i % 2 === 0 } } : {}) });
}
const shapes: Shape[] = (["box", "rounded", "oval", "brackets", "parens", "braces", "highlight"] as const).flatMap((kind, i) =>
  [undefined, "left", "right"].map((side, j) => ({ id: 100 + i * 3 + j, kind, from: at(), to: at(), ...(side ? { side: side as "left" | "right" } : {}) })));

// The kept test gives the same answer as measuring every path, for points near and far.
for (const r of [2, 6, 15, 40]) {
  for (let n = 0; n < 400; n++) {
    const q: P = [rand() * 200 - 100, rand() * 200 - 100];
    for (const a of arrows) assert.equal(nearTrace(q, arrowTrace(a, L), r), distToPath(q, arrowPath(a, L)) < r, `arrow ${a.id} at ${q} within ${r}`);
    for (const sh of shapes) assert.equal(nearTrace(q, shapeTrace(sh, L, L), r), shapePaths(sh, L, L).some((path) => distToPath(q, path) < r), `shape ${sh.id} at ${q} within ${r}`);
  }
}
// Points on the paths themselves are hits.
for (const a of arrows) for (const q of arrowPath(a, L)) assert.ok(nearTrace(q, arrowTrace(a, L), 0.01));

// A path is made once per object and scale, and again for a new object or scale.
assert.equal(arrowTrace(arrows[0], L), arrowTrace(arrows[0], L));
assert.notEqual(arrowTrace(arrows[0], L), arrowTrace({ ...arrows[0] }, L));
assert.notEqual(arrowTrace(arrows[0], L), arrowTrace(arrows[0], 2 * L));
assert.equal(shapeTrace(shapes[0], L, L), shapeTrace(shapes[0], L, L));
assert.notEqual(shapeTrace(shapes[0], L, L), shapeTrace(shapes[0], L, 2 * L));
const orbital: Arrow = { id: 1, kind: "orbital", from: [0, 0], to: [1, 1], orbital: { shape: "p", phase: "shaded" } };
assert.deepEqual(lobesOf(orbital, L), orbitalPaths(orbital, L));
assert.equal(lobesOf(orbital, L), lobesOf(orbital, L));
// A p orbital's lobes reach past its nucleus, outside the line from the nucleus to the tip, so the box round a
// selection takes the lobes (CD-3: the rotation handle and the centre a turn goes about).
{
  const ps = lobesOf(orbital, L).flatMap((l) => l.path), line = arrowTrace(orbital, L).box;
  assert.ok(Math.min(...ps.map((q) => q[0])) < line[0] - 0.5 * L && Math.max(...ps.map((q) => q[1])) > line[3] + 0.5 * L);
}
let made = 0;
const cache = new WeakMap<object, [unknown, number]>(), key = {};
kept(cache, key, 1, () => ++made); kept(cache, key, 1, () => ++made);
assert.equal(made, 1, "kept makes a value once");
assert.equal(kept(cache, key, 2, () => ++made), 2, "and again for another scale");
console.log("hit.check: ok");
