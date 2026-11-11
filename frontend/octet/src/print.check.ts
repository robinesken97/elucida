// Run: node src/print.check.ts. Fails loudly if Print picks the wrong pages for a drawing (CH-37).
import assert from "node:assert/strict";
import { MAX_PRINT_PAGES, pagesOver } from "./docstyle.ts";

// Pages 100 wide and 200 tall, the first centred on the origin (y down).
const on = (box: [number, number, number, number]) => pagesOver(box, 100, 200).pages;
// A drawing on the page: that page alone. Nothing drawn: that page too.
assert.deepEqual(on([-40, -90, 40, 90]), [[0, 0]]);
assert.deepEqual(on([0, 0, 0, 0]), [[0, 0]]);
// Ink a hair over the edge stays on the page.
assert.deepEqual(on([-50.5, -100.5, 50.5, 100.5]), [[0, 0]]);
// Past the right edge: the page to the right too. Past the bottom: the row under it. Row by row from the top.
assert.deepEqual(on([-40, -90, 60, 90]), [[0, 0], [1, 0]]);
assert.deepEqual(on([-40, -90, 60, 120]), [[0, 0], [1, 0], [0, 1], [1, 1]]);
// Above and to the left: negative pages, first.
assert.deepEqual(on([-140, -150, 10, 10]), [[-1, -1], [0, -1], [-1, 0], [0, 0]]);
// Far away: counted, not listed.
const far = pagesOver([0, 0, 5000, 5000], 100, 200);
assert.ok(far.count > MAX_PRINT_PAGES && far.pages.length === 0);
console.log("print.check: ok");
