// Run: node src/grid.check.ts. Fails loudly if the grid draws too many lines, the wrong lines, or snaps wrongly.
import assert from "node:assert/strict";
import { gridLines, gridNudge, gridOf, MAX_LINES, rulerTicks, shownStep, snapToGrid } from "./grid.ts";
import { readStyle } from "./docstyle.ts";

const mm = 1 / 5.08; // bond lengths per mm on ACS Document 1996 (a 14.4 pt bond)
const corner: [number, number] = [-105 * mm, 148.5 * mm]; // A4 portrait's top-left corner

// A bond-length grid: a line each bond length, a lighter one at each half, from the origin.
{
  const g = gridOf("bond", mm, [0, 0]), lines = gridLines(g, [-1.2, -1.2, 1.2, 1.2], 40);
  assert.deepEqual(lines.x, [[-1, true], [-0.5, false], [0, true], [0.5, false], [1, true]]);
  assert.deepEqual(lines.y, lines.x);
  // Zoomed out: the halves come closer than 8 px and go; the bond lines stay until they too are closer than 8 px.
  assert.equal(shownStep(g, 16), 0.5);
  assert.equal(shownStep(g, 15), 1);
  assert.deepEqual(gridLines(g, [-1.2, -1.2, 1.2, 1.2], 10).x, [[-1, true], [0, true], [1, true]]);
  assert.equal(shownStep(g, 7), undefined);
  assert.deepEqual(gridLines(g, [-1.2, -1.2, 1.2, 1.2], 7), { x: [], y: [] });
}

// A 5 mm grid from the page's corner: a heavier line every 25 mm, and the lines meet the page's edges.
{
  const g = gridOf(5, mm, corner), lines = gridLines(g, [corner[0], -corner[1], -corner[0], corner[1]], 20);
  assert.equal(lines.x.length, 43); // 0 to 210 mm
  assert.equal(lines.y.length, 60); // 0 to 297 mm
  assert.ok(Math.abs(lines.x[0][0] - corner[0]) < 1e-9 && lines.x[0][1]);
  assert.deepEqual(lines.x.slice(0, 6).map(([, major]) => major), [true, false, false, false, false, true]);
  assert.ok(Math.abs(lines.y[lines.y.length - 1][0] - corner[1]) < 1e-9);
}

// A grid in inches: a heavier line at each inch (8, 4 or 2 steps), as the rulers in inches count.
{
  assert.deepEqual([3.175, 6.35, 12.7].map((step) => gridOf(step, mm, corner).every), [8, 4, 2]);
  const g = gridOf(6.35, mm, [0, 0]), lines = gridLines(g, [0, 0, 25.4 * mm, 0], 40);
  assert.deepEqual(lines.x.map(([, major]) => major), [true, false, false, false, true]);
}

// Never more than MAX_LINES, whatever the window or the step: a huge window, a tiny step, a bad scale.
{
  assert.ok(gridLines(gridOf(1, mm, [0, 0]), [-1e6, -1e6, 1e6, 1e6], 1000).x.length <= MAX_LINES);
  assert.deepEqual(gridLines(gridOf(1e-20, mm, [0, 0]), [-10, -10, 10, 10], 1e25), { x: [], y: [] });
  assert.deepEqual(gridLines(gridOf(5, mm, [0, 0]), [-10, -10, 10, 10], Infinity), { x: [], y: [] });
  assert.deepEqual(gridLines(gridOf(-1, mm, [0, 0]), [-10, -10, 10, 10], 40), { x: [], y: [] });
  assert.deepEqual(gridLines(gridOf(5, mm, [Infinity, 0]), [-10, -10, 10, 10], 40), { x: [], y: [] });
}

// A file's grid step: only the steps Settings offers; anything else (a hang in waiting) is the bond length.
for (const grid of [1e-20, 0.001, -1, 7, 0, 1e9, "5", null, NaN]) assert.equal(readStyle({ grid }).grid, "bond", String(grid));
for (const grid of ["bond", 1, 2, 5, 10, 20, 3.175, 6.35, 12.7]) assert.equal(readStyle({ grid }).grid, grid);

// Snapping: to the nearest shown line on each axis, within the tolerance, and to nothing when no lines show.
{
  const g = gridOf("bond", mm, [0, 0]);
  assert.deepEqual(snapToGrid(g, [0.53, 0.8], 40, 6), [0.5, undefined]);
  assert.deepEqual(snapToGrid(g, [0.97, -0.04], 40, 6), [1, 0]);
  assert.deepEqual(snapToGrid(g, [0.53, 0.97], 10, 6), [1, 1]); // the halves do not show at 10 px per bond
  assert.deepEqual(snapToGrid(g, [0.01, 0.01], 5, 6), [undefined, undefined]);
}
console.log("grid.check: ok");

// Snap to Grid on a move: the nearest of the moving points lands on a line, on each axis it can.
{
  const g = gridOf("bond", mm, [0, 0]);
  assert.deepEqual(gridNudge(g, [[0.46, 0.2], [1.1, 0.9]], 40, 6).map((v) => v && +v.toFixed(6)), [0.04, 0.1]);
  assert.deepEqual(gridNudge(g, [[0.25, 0.25]], 40, 6), [undefined, undefined]);
}

// Ruler marks: a number every 48 px or more, smaller marks 6 px or more apart, halves marked larger.
{
  const mmTicks = rulerTicks(0, 50, 3.78, false); // 1 mm is 3.78 px at 100% on ACS
  assert.deepEqual(mmTicks.filter((t) => t.label).map((t) => t.label), ["0", "20", "40"]);
  assert.equal(mmTicks[1].at, 2); // marks every 2 mm (7.6 px)
  assert.deepEqual(mmTicks.slice(0, 6).map((t) => t.size), [2, 0, 0, 0, 0, 1]);
  const inches = rulerTicks(-1, 2, 96, true);
  assert.deepEqual(inches.filter((t) => t.label).map((t) => t.label), ["−1", "−0.5", "0", "0.5", "1", "1.5", "2"]);
  assert.equal(inches[1].at - inches[0].at, 1 / 16);
  assert.ok(rulerTicks(-1e9, 1e9, 1e-9, false).length <= 2001);
  assert.deepEqual(rulerTicks(0, 10, NaN, false), []);
}
console.log("grid.check: ruler ok");
