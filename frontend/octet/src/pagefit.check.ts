// Run: node src/pagefit.check.ts. Fails loudly if a page edge stops fitting its page with a tool. With every tool, the
// pointer on a page's edge (clear of the drawing) highlights the page and shows the zoom-in cursor, and a click there
// fits that page in the window, centred. Commit 5ac3bbc limited this to Select; Sam uses it with every tool.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
const edgePage = /const edgePage = \(p: P, t: Hover\) => (.*);\n/.exec(editor)?.[1];
assert.ok(edgePage, "found edgePage in Editor.tsx; update this check");
// The edge test reads no tool.
assert.ok(!/\btool\b/.test(edgePage), `edgePage reads the tool: ${edgePage}`);
// A press on the edge fits the page before a tool acts on the press.
const down = editor.slice(editor.indexOf("function onPointerDown("), editor.indexOf("function onPointerMove("));
const fit = down.indexOf("const page = edgePage(p, t);\n    if (page) return fitPage(page);");
assert.ok(fit > 0, "onPointerDown fits the page from edgePage with no other test");
assert.ok(fit < down.indexOf("return pressSelect("), "onPointerDown fits the page before the Select press");
// The hover marks the page from the same test, and the marked page gives the zoom-in cursor.
const move = editor.slice(editor.indexOf("function onPointerMove("));
assert.match(move.slice(0, move.indexOf("switch (drag.kind)")), /\bpage: edgePage\(p, t\)\?\.\[0\],/);
assert.match(editor, /pageHover && !drag \? \{ cursor: "zoom-in" \}/);
assert.match(editor, /className=\{pageHover === name \? "page hovered" : "page"\}/);

console.log("pagefit: ok");
