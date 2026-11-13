// Run: node src/glideplan.check.ts. Fails loudly if the fast glide (glideplan.ts, decision 0024) does not start where
// the drawing was and end exactly where the editor draws it, or slides two drawings that do not match point for point.
import assert from "node:assert/strict";
import { glidePlan, inkKey, slideAt, slidePath, type PartIn } from "./glideplan.ts";
import type { Drawing } from "./render.ts";

type P = [number, number];
// The editor's own path for polygons (Editor.tsx toPath) and its grouping by colour (structurePaths).
const toPath = (polys: P[][]) => polys.map((poly) => "M" + poly.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join("L") + "Z").join("");
const editorPaths = (d: Drawing) => {
  const groups = new Map<string, P[][]>();
  d.polygons.forEach((poly, i) => { const k = inkKey(d, i); groups.set(k, [...(groups.get(k) ?? []), poly]); });
  return [...groups].map(([k, polys]) => [k, toPath(polys)]);
};
const drawing = (polygons: P[][], colours: (string | undefined)[], labels: Drawing["labels"] = []): Drawing => ({
  polygons, colours, alphas: polygons.map(() => 1), labels, box: [0, 0, 0, 0], ink: [], label: [], scale: 1, electrons: [], beads: [], labelAt: labels.map((l) => [l.x, l.y]), maps: [],
});
const part = (ids: number[], d: Drawing, at: P = [0, 0]): PartIn => ({ ids, drawing: d, at, k: 1, turn: 0 });

// A bond and a red one, and an O label, moved by Clean Up.
const a = drawing([[[0, 0], [10, 0], [10, 1], [0, 1]], [[10, 0], [20, 5], [20, 6]]], [undefined, "#FF0000"], [{ text: "O", x: 20, y: 6, size: 10 }]);
const b = drawing([[[0, 0], [12, 4], [12, 5], [0, 1]], [[12, 4], [24, 4], [24, 5]]], [undefined, "#ff0000"], [{ text: "O", x: 24, y: 5, size: 10 }]);
const plan = glidePlan([part([0, 1, 2], a)], [part([0, 1, 2], b)])!;
assert.equal(plan.length, 1);
const slide = plan[0];
assert.equal(slide.kind, "slide", "drawings that match point for point slide");
if (slide.kind === "slide") {
  // The same shapes as the editor's paths: the same numbers, to a hundredth of a pixel.
  const numbers = (d: string) => (d.match(/-?\d+(\.\d+)?/g) ?? []).map(Number).map((x) => Math.round(x * 100));
  assert.deepEqual(slide.groups.map((g) => [g.key, numbers(slidePath(g, 0))]), editorPaths(a).map(([k, d]) => [k, numbers(d)]), "the first frame is the drawing where it starts");
  assert.deepEqual(slide.groups.map((g) => [g.key, numbers(slidePath(g, 1))]), editorPaths(b).map(([k, d]) => [k, numbers(d)]), "the last frame is the editor's own drawing where it ends");
  assert.deepEqual(slideAt(slide.labels[0].from, slide.labels[0].to, 0.5), [22, 5.5], "a label slides half way");
}
// A structure drawn moved (its at) slides from where it is on the page.
const moved = glidePlan([part([0, 1, 2], a, [100, 0])], [part([0, 1, 2], b)])!;
if (moved[0].kind === "slide") assert.ok(slidePath(moved[0].groups[0], 0).startsWith("M100 0L"), "a moved drawing starts where it is shown");
else assert.fail("a moved drawing with the same labels slides");

// A hashed wedge drawn with one more stripe does not match point for point: that bond fades, and every other bond
// still slides (render.ts owners: what drew each polygon).
const owned = (d: Drawing, owners: number[]): Drawing => ({ ...d, owners });
const before = owned(drawing([[[0, 0], [10, 0], [10, 1], [0, 1]], [[20, 0], [21, 0], [21, 1]], [[22, 0], [23, 0], [23, 1]]], [undefined, undefined, undefined]), [0, 1, 1]);
const after = owned(drawing([[[0, 0], [12, 4], [12, 5], [0, 1]], [[20, 0], [21, 0], [21, 1]], [[22, 0], [23, 0], [23, 1]], [[24, 0], [25, 0], [25, 1]]], [undefined, undefined, undefined, undefined]), [0, 1, 1, 1]);
const wedge = glidePlan([part([0, 1], before)], [part([0, 1], after)])![0];
assert.ok(wedge.kind === "slide", "a structure with one bond that does not match still slides");
if (wedge.kind === "slide") {
  assert.equal(wedge.groups[0].sizes.length, 1, "the bond that matches slides");
  assert.equal(wedge.fades.length, 1, "the wedge with a stripe more fades");
  assert.ok(wedge.fades[0].out.split("M").length - 1 === 2 && wedge.fades[0].in.split("M").length - 1 === 3, "its old stripes fade out and its new ones in");
}
const relabelled = drawing(b.polygons, b.colours, [{ text: "S", x: 24, y: 5, size: 10 }]);
const swapped = glidePlan([part([0, 1, 2], a)], [part([0, 1, 2], relabelled)])![0];
assert.ok(swapped.kind === "slide" && swapped.labels[0].was?.text === "O" && swapped.labels[0].label.text === "S", "a label whose text changed (OH to HO) still slides, the old text fading out");
// Other structures (atoms added or taken away): no fast glide at all.
assert.equal(glidePlan([part([0, 1, 2], a)], [part([0, 1], b)]), undefined, "a structure that is not the same atoms: no plan");
assert.equal(glidePlan([part([0, 1, 2], a)], [part([0, 1, 2], b), part([3], b)]), undefined, "a structure more: no plan");

// A turn goes round its centre: half way through a turn of 90°, a point is on the arc, not on the chord across it.
const square = drawing([[[10, 0], [11, 0], [11, 1], [10, 1]]], [undefined]);
const turned = drawing([[[0, 10], [0, 11], [-1, 11], [-1, 10]]], [undefined]);
const turning = glidePlan([part([0], square)], [part([0], turned)], { centre: [0, 0], angle: Math.PI / 2 })![0];
if (turning.kind === "slide") {
  const [x, y] = (slidePath(turning.groups[0], 0.5).match(/-?[\d.]+/g) ?? []).map(Number);
  assert.ok(Math.abs(Math.hypot(x, y) - 10) < 0.01, `half way round, the first point is still 10 from the centre (${Math.hypot(x, y).toFixed(2)})`);
  assert.deepEqual((slidePath(turning.groups[0], 1).match(/-?[\d.]+/g) ?? []).map(Number).map((v) => Math.round(v)), [0, 10, 0, 11, -1, 11, -1, 10], "and it ends where the turned drawing is");
} else assert.fail("a turned drawing slides");
// A thousand atoms' ink, a frame: well under a millisecond's work for each structure's paths.
const big = (shift: number) => drawing(Array.from({ length: 3000 }, (_, i): P[] => [[i + shift, 0], [i + 1, shift], [i + 1, 1], [i, 1]]), Array.from({ length: 3000 }, () => undefined));
const heavy = glidePlan([part([0], big(0))], [part([0], big(1))])!;
const t0 = performance.now();
for (let f = 0; f < 60; f++) for (const x of heavy) if (x.kind === "slide") for (const g of x.groups) slidePath(g, f / 60);
const each = (performance.now() - t0) / 60;
assert.ok(each < 8, `a frame of 3,000 polygons takes ${each.toFixed(2)} ms (under 8)`);
console.log(`glideplan.check: ok (a frame of 3,000 polygons: ${each.toFixed(2)} ms)`);
