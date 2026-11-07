import assert from "node:assert/strict";
import { dropClear, panInto, roomOf } from "./reveal.ts";

const ROOM: [number, number, number, number] = [48, 48, 1392, 852];
// In view: no pan.
assert.deepEqual(panInto([100, 100, 300, 200], ROOM), [0, 0]);
// Off to the right (Name to Structure after a wide drawing): the view pans left just far enough.
assert.deepEqual(panInto([1500, 300, 1700, 400], ROOM), [1392 - 1700, 0]);
// Off to the left and under a panel along the bottom.
assert.deepEqual(panInto([-200, 700, -100, 900], [48, 48, 1392, 600]), [248, 600 - 900]);
// Wider than the room: centred across.
assert.deepEqual(panInto([0, 100, 2000, 200], ROOM), [(48 + 1392) / 2 - 1000, 0]);
// The room: the canvas less the tools down the left, the Actions panel down the right and the Spectrum panel along the
// bottom, 48 px clear of each. A structure landing at the right edge ends up left of the Actions panel.
const CANVAS: [number, number, number, number] = [0, 0, 1090, 859], TOOLS: [number, number, number, number] = [16, 16, 58, 631];
const ACTIONS: [number, number, number, number] = [816, 308, 1074, 843], SPECTRUM: [number, number, number, number] = [122, 560, 784, 843];
assert.deepEqual(roomOf(CANVAS, [TOOLS, ACTIONS, SPECTRUM]), [106, 48, 768, 512]);
assert.deepEqual(panInto([900, 100, 1000, 200], roomOf(CANVAS, [TOOLS, ACTIONS])), [768 - 1000, 0]);
// No panels: the window less 48 px. A full-window Spectrum leaves the bottom as it is.
assert.deepEqual(roomOf(CANVAS, []), [48, 48, 1042, 811]);
assert.deepEqual(roomOf(CANVAS, [[16, 16, 1074, 843]]), [48, 48, 1042, 811]);
console.log("reveal.check: ok");

// Add to drawing: a spectrum under ferrocene (its spot, 300 px wide) beside a peptide that reaches under ferrocene.
// Clear: it stays. Over the peptide: it goes down under the peptide, `gap` clear; under a key below that too.
const SPOT: [number, number, number, number] = [0, 100, 300, 180];
assert.equal(dropClear(SPOT, [[-200, -100, -10, 300], [0, -100, 100, 80]], 4, 20), 0, "clear of the structures beside and above it");
assert.equal(dropClear(SPOT, [[200, -50, 600, 150]], 4, 20), 150 + 20 - 100, "under the peptide");
assert.equal(dropClear(SPOT, [[200, -50, 600, 150], [250, 160, 400, 240]], 4, 20), 240 + 20 - 100, "and under the text under it");
assert.equal(dropClear(SPOT, [[300, 0, 400, 300]], 4, 20), 300 + 20 - 100, "touching counts, within the margin");
assert.equal(dropClear(SPOT, [[310, 0, 400, 300]], 4, 20), 0, "past the margin does not");
