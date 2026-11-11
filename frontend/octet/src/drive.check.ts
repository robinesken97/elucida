// Run: node src/drive.check.ts. The CI drive (scripts/drive/drive.mjs), as its dry run prints it: the first drawing is
// in Home's window and each later one has a window of its own, so the drive moves WebDriver to a drawing's window before it
// looks in that drawing.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const drive = fileURLToPath(new URL("../scripts/drive/drive.mjs", import.meta.url));
const cwd = mkdtempSync(path.join(tmpdir(), "drive-")); // the dry run writes drive-out/ here
let out: string;
try { out = execFileSync(process.execPath, [drive, "--dry"], { cwd }).toString(); } finally { rmSync(cwd, { recursive: true, force: true }); }

// Each step's lines, by the start of its name.
const steps = out.split(/^(?=\d+\. )/m);
const step = (name: string) => {
  const s = steps.find((t) => t.replace(/^\d+\. /, "").startsWith(name));
  assert.ok(s, `no step ${name}`);
  return s.split("\n").map((l) => l.trim());
};
const at = (lines: string[], line: string) => {
  const k = lines.indexOf(line);
  assert.ok(k >= 0, `no "${line}" in:\n${lines.join("\n")}`);
  return k;
};
const SWITCH = "WebDriver: POST /session/SESSION/window", NEW = "wait for a new window", FRONT = "wait for the new window in front, named Untitled";

// Quick start: the first drawing in Home's own window, so no new window; WebDriver keeps that window as the drawing's.
const quick = step("Home's Quick start");
assert.ok(!quick.includes(NEW) && !quick.includes(FRONT), "Quick start waits for no new window");
assert.ok(at(quick, "wait for the drawing") < at(quick, "WebDriver: GET /session/SESSION/window"));
// File > New on the untouched first drawing opens a window too (issue 38), which closes with no question.
const untouched = step("On the untouched first drawing");
assert.ok(at(untouched, NEW) < at(untouched, FRONT) && at(untouched, FRONT) < at(untouched, "wait for the new drawing"));
assert.ok(at(untouched, "wait for the new drawing") < at(untouched, "wait for the new window to close") && !untouched.includes("wait for the question"));
// File > New opens a new window, in front, and the command that reads the window in front runs before the wait for its name.
const fresh = step("File > New");
const front = fresh.findIndex((l) => /^\$ (powershell.*windows\.ps1.* front|python3 .*linux-menu\.py PID)$/.test(l));
assert.ok(at(fresh, NEW) < at(fresh, FRONT) && front > at(fresh, NEW) && front < at(fresh, FRONT), `no front command in:\n${fresh.join("\n")}`);
// The first drawing keeps its two ethanol, and the new one has none.
assert.ok(at(fresh, FRONT) < at(fresh, "wait for 2 ethanol in the drawing") && at(fresh, "wait for 2 ethanol in the drawing") < at(fresh, SWITCH));
assert.ok(at(fresh, SWITCH) < at(fresh, "wait for 0 ethanol in the drawing"));
// A page spectrum (in the second window): the dione pasted and predicted, its spectrum added, the panel closed and
// Select in hand before the mouse double-clicks a label; the label is copied after each edit (picked alone, Left, typed
// over, Colour > Red); the drawing goes through Octet's own copy and CDXML; the window closes and WebDriver goes back to
// the first drawing.
const spectrum = step("Each part of a page spectrum");
const ACTIONS = "WebDriver: POST /session/SESSION/actions", COPY = "wait for application/x-octet+json on the clipboard";
const menu = (name: string) => spectrum.findIndex((l) => l.startsWith("$ ") && l.endsWith(name));
const after = (from: number, line: string) => { const k = spectrum.indexOf(line, from + 1); assert.ok(k > from, `no "${line}" after line ${from} in:\n${spectrum.join("\n")}`); return k; };
const pasted = at(spectrum, "wait for octane-3,5-dione in the drawing"), predicted = after(pasted, "wait for the predicted spectrum");
assert.ok(menu("Edit Paste") < pasted && pasted < menu("Structure Predict*") && menu("Structure Predict*") < predicted);
const closed = after(predicted, "wait for the panel closed"), select = after(closed, "wait for the Select tool"), first = after(select, ACTIONS), picked = after(first, COPY);
const left = spectrum.findIndex((l) => /^\$ (xdotool key --clearmodifiers Left|powershell.*windows\.ps1.* keys \{LEFT\})$/.test(l));
const nudged = after(left, COPY), second = after(nudged, ACTIONS), typing = after(second, "wait for the label's text box"), typed = after(typing, "wait for the text box closed");
assert.ok(after(predicted, "wait for the spectrum on the page") < closed && picked < left && menu("Colour Red") > typed && after(menu("Colour Red"), COPY) > 0);
// Shifts beside atoms goes on the page, and Undo takes it off, before the panel closes.
const onPage = after(after(predicted, "wait for the spectrum on the page"), "wait for the shifts on the page");
assert.ok(onPage < menu("Edit Undo") && menu("Edit Undo") < after(onPage, "wait for the shifts in the panel again") && after(onPage, "wait for the shifts in the panel again") < closed);
const copy = after(menu('Edit "Select All"'), COPY), own = after(copy, "wait for the copy pasted"), cdxml = after(own, "wait for the CDXML pasted");
assert.ok(menu('Edit "Select All"') > menu("Colour Red") && cdxml > own);
// After the label's edits, the spectrum alone is clicked and its frame's handle dragged, the drawing copied, and Undo
// takes the resize back, all before the copies go round.
const red = menu("Colour Red"), mouse = spectrum.flatMap((l, k) => (k > red && k < own && l === ACTIONS ? [k] : []));
const undo = spectrum.findIndex((l, k) => k > red && l.startsWith("$ ") && l.endsWith("Edit Undo"));
assert.ok(mouse.length === 3 && after(mouse[2], COPY) < undo && undo < own, `the resize in:\n${spectrum.join("\n")}`);
const question = after(cdxml, "wait for the question");
assert.ok(menu('File "Close Window"') > cdxml && menu('File "Close Window"') < question && after(question, "wait for the window to close") < after(question, SWITCH));
// Close Window on the first drawing (issue 38): Home in the same window, then Quick start and a paste there, so Exit asks.
const back = step("File > Close Window on the first drawing");
assert.ok(at(back, "wait for the question") < at(back, "wait for Home in the first drawing's window") && at(back, "wait for Home in the first drawing's window") < at(back, "wait for the drawing"));
assert.ok(at(back, "wait for the drawing") < at(back, "wait for 1 ethanol in the drawing") && !back.includes(SWITCH));
// File > Exit: the first drawing asks, so WebDriver moves back to it for Don't Save.
const exit = step("File > Exit");
assert.ok(at(exit, SWITCH) < at(exit, "wait for the question") && at(exit, "wait for the question") < at(exit, "wait for Octet to end"));
// Keys go to the window in front: nothing moves the focus to the first window the process has, which can be Home.
assert.ok(!/windowfocus|xdotool search/.test(out));
// On Windows File > Close Window is the system's item, which muda names Close (src-tauri/src/main.rs), so the drive asks
// for it by that name there.
const { readFileSync } = await import("node:fs");
const source = (f: string) => readFileSync(fileURLToPath(new URL(f, import.meta.url)), "utf8");
assert.match(source("../src-tauri/src/main.rs"), /PredefinedMenuItem::close_window\(app, None\)/);
assert.match(source("../scripts/drive/drive.mjs"), /const CLOSE = WIN \? "Close" : "Close Window";/);
assert.ok(!/system\.menu\("File", "Close Window"\)/.test(source("../scripts/drive/drive.mjs")), "every Close Window goes by the platform's name");
// Close Window (and the close button) with Home showing closes the window, also in one window (Settings > Windows off),
// so a window always closes in the end and never only shows Home again.
assert.match(source("./Editor.tsx"), /const closeDrawing = \(\) => MAC \|\| home \? closeWindow\(\) : DRAW_WINDOW \?/);
console.log("drive checks pass");
