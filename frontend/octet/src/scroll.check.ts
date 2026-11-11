// Run: node src/scroll.check.ts. Fails loudly if the canvas's navigation goes wrong: the scroll bars' sums
// (scroll.ts), Centre in Window's (reveal.ts), and how they are wired to the menu, the Actions panel and the pointer.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { bar, dragShift, GAP, LEAST, pageShift } from "./scroll.ts";
import { centreIn } from "./reveal.ts";

const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 1e-9, `${what}: ${a} is not ${b}`);

// A drawing that fits in the window, GAP clear: no bar.
assert.equal(bar([100, 900], [0, 1000], 988), undefined);
// Only just over the edge (less than 1 px of range to scroll): still no bar.
assert.equal(bar([GAP, 1000 - GAP + 0.5], [0, 1000], 988), undefined);

// A drawing twice the window's width, its left end GAP in from the window's left: the thumb starts the track and is
// half of it; one px of thumb moves the view one px of range over one px of free track.
{
  const b = bar([GAP, GAP + 2000 - 2 * GAP], [0, 1000], 1000)!;
  near(b.at, 0, "thumb at the start");
  near(b.size, 500, "thumb half the track");
  near(b.per, 1000 / 500, "px of view per px of thumb");
}
// The view panned to the far end: the thumb ends the track.
{
  const b = bar([-1000 + GAP, 1000 - GAP], [0, 1000], 1000)!;
  near(b.at + b.size, 1000, "thumb at the end");
}
// The view panned off the drawing to the right: the range takes in what the window shows, so the thumb is at the end
// and smaller than it was.
{
  const b = bar([-3000, -1000], [0, 1000], 1000)!;
  near(b.at + b.size, 1000, "thumb at the end");
  assert.ok(b.size < 1000 * (1000 / (2000 + 2 * GAP)) + 1e-9, "a smaller thumb");
}
// A huge drawing: the thumb is never shorter than LEAST.
assert.equal(bar([0, 1e7], [0, 1000], 1000)!.size, LEAST);

// The track: one window less GAP each press, no further than the range's end.
assert.equal(pageShift([-5000, 5000], [0, 1000], 1), 1000 - GAP);
assert.equal(pageShift([-5000, 5000], [0, 1000], -1), -(1000 - GAP));
assert.equal(pageShift([0, 1200], [0, 1000], 1), 1200 + GAP - 1000);
assert.equal(pageShift([0, 1200], [0, 1000], -1), -GAP);

// Dragging the thumb: the view moves `per` px for each px, and the thumb stops at the ends of its track.
{
  const b = bar([GAP, 2000 - GAP], [0, 1000], 1000)!;
  near(dragShift(b, 1000, 100), 100 * b.per, "drag along");
  near(dragShift(b, 1000, 5000), (1000 - b.size) * b.per, "stops at the end");
  near(dragShift(b, 1000, -50), 0, "stops at the start");
}

// Centre in Window: the box's middle goes to the room's middle; a box already there does not move.
assert.deepEqual(centreIn([100, 100, 300, 200], [0, 0, 1000, 800]), [300, 250]);
assert.deepEqual(centreIn([400, 300, 600, 500], [0, 0, 1000, 800]), [0, 0]);
// A box bigger than the room is centred too.
assert.deepEqual(centreIn([-500, 0, 1500, 800], [0, 0, 1000, 800]), [0, 0]);

// Wiring. View > Centre in Window has ⌥⌘/ (Alt+Ctrl+/ off the Mac), next to Fit to Window; the editor runs it and lists
// it in the command palette with that key.
const read = (name: string) => readFileSync(new URL(name, import.meta.url), "utf8");
const main = read("../src-tauri/src/main.rs"), editor = read("Editor.tsx"), actions = read("Actions.tsx");
assert.match(main, /item\("zoom_fit", "Fit to Window", "CmdOrCtrl\+\/"\)\?,\n(\s*\/\/.*\n)*\s*&item\("centre_view", "Centre in Window", "Alt\+CmdOrCtrl\+\/"\)\?/);
assert.equal(main.match(/"Alt\+CmdOrCtrl\+\/"/g)?.length, 1, "⌥⌘/ is not taken twice");
assert.match(editor, /centre_view: \(\) => \{/);
assert.match(editor, /centre_view: \["Centre in window", `⌥\$\{MOD\}\/`/);
// From a key the view moves at once; from the pointer it glides (moveView).
assert.match(editor, /if \(performance\.now\(\) - keyAt\.current > 500\) return moveView\(to\);/);
// Every Actions panel that has Centre on Page, and the atom, bond, grid and spot ones, offer Centre in Window too.
assert.equal(actions.match(/\bcentre, inWindow\b|\binWindow, centre\b/g)?.length, 5); // the object list, the drawing, captions and both shape panels
assert.equal(actions.match(/whole, inWindow, keep/g)?.length, 2);
assert.match(actions, /"grid\.layout"\), inWindow, del\)/);
assert.match(actions, /"spot\.rf"\), inWindow, del\)/);
assert.match(actions, /centre_view: "view"/);
// The pointer: Shift and a mouse wheel scroll across; the middle button drags the view with every tool; the scroll
// bars show over the canvas but not on Home.
assert.match(editor, /across = e\.shiftKey && !zooming && !e\.deltaX/);
assert.match(editor, /if \(e\.button === 1\) \{/);
assert.match(editor, /\{!home && \(\n\s*<Scrollbars views=\{views\}/);
// The bars follow the view from its store, with no React render for each pan or zoom step.
assert.match(read("Scrollbars.tsx"), /const off = views\.subscribe\(draw\);/);
console.log("scroll.check: ok");
