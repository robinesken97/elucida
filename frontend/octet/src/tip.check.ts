// Run: node src/tip.check.ts. Fails loudly if a tooltip goes past the window or covers its control.
import assert from "node:assert/strict";
import { placeTip, showsWords, TIP_EDGE, TIP_GAP } from "./tip.ts";

const view = { width: 1100, height: 700 };
// Above and centred.
assert.deepEqual(placeTip({ left: 500, top: 300, right: 532, bottom: 332 }, 60, 20, view), { left: 486, top: 300 - TIP_GAP - 20 });
// Near the right edge it moves in by its own width: "Contract label" ended at 1101.8 px in a 1100 px window.
const right = placeTip({ left: 1060, top: 600, right: 1088, bottom: 628 }, 110, 20, view);
assert.equal(right.left + 110, view.width - TIP_EDGE);
// Near the left edge too.
assert.equal(placeTip({ left: 2, top: 300, right: 30, bottom: 330 }, 80, 20, view).left, TIP_EDGE);
// No room above: below.
assert.equal(placeTip({ left: 500, top: 10, right: 532, bottom: 42 }, 60, 20, view).top, 42 + TIP_GAP);
// The toolbar's tips go beside it, level with the tool, and above when there is no room on the right.
assert.deepEqual(placeTip({ left: 16, top: 100, right: 48, bottom: 132 }, 70, 20, view, "right"), { left: 48 + TIP_GAP, top: 106 });
assert.equal(placeTip({ left: 1060, top: 100, right: 1092, bottom: 132 }, 70, 20, view, "right").top, 100 - TIP_GAP - 20);
// Beside a tool at the bottom of the window, it stays in the window.
assert.equal(placeTip({ left: 16, top: 680, right: 48, bottom: 712 }, 70, 20, view, "right").top, view.height - TIP_EDGE - 20);

// A control that shows words needs no tip of its name; atom labels drawn in its icon are not words.
const text = (s: string) => ({ nodeType: 3, nodeName: "#text", textContent: s, childNodes: [] });
const el = (nodeName: string, ...childNodes: ReturnType<typeof text>[]) => ({ nodeType: 1, nodeName, textContent: null, childNodes });
assert.equal(showsWords(el("BUTTON", el("SPAN", text("Settings")))), true);
assert.equal(showsWords(el("BUTTON", el("SPAN", el("svg", el("text", text("N")), el("text", text("O")))))), false, "a structure icon (the Template tool)");
assert.equal(showsWords(el("BUTTON", el("svg"), text("  "))), false);
console.log("tip.check: ok");
