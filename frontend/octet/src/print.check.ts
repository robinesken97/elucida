// Run: node src/print.check.ts. Fails loudly if Print picks the wrong pages for a drawing (CH-37), or if its preview
// on Linux (issue 119) goes.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
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
// How many pages across, for Print's preview on Linux (issue 119): it lays the pages out in rows of this many.
assert.equal(pagesOver([-40, -90, 40, 90], 100, 200).cols, 1);
assert.equal(pagesOver([-40, -90, 160, 120], 100, 200).cols, 3);
assert.equal(pagesOver([-140, -150, 10, 10], 100, 200).cols, 2);
// The preview is for Linux alone: the Mac's and Windows' print dialogs show the pages themselves.
const editor = readFileSync(new URL("./Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /const LINUX = navigator\.platform\.startsWith\("Linux"\);/);
assert.match(editor, /if \(LINUX\) return setDialog\(\{ kind: "print", srcs, \.\.\.size, cols: across, page \}\);\n\s+await printPages\(\{ srcs, \.\.\.size \}\);/);
assert.match(editor, /<Dialog title="Print" action="Print…"[^\n]*onAction=\{\(\) => \{ setDialog\(undefined\); void printPages\(dialog\); \}\}>/);
console.log("print.check: ok");
