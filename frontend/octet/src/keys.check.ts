// Run: node src/keys.check.ts. Fails loudly if shortcut lookup breaks.
import assert from "node:assert/strict";
import { actionFor, clashes, controlTakes, feedbackChord, keyOf, keymap, menuRuns, textEntry, textKey, tileTo } from "./keys.ts";

const press = (key: string, mods: Partial<{ shiftKey: boolean; altKey: boolean; metaKey: boolean; ctrlKey: boolean }> = {}) =>
  keyOf({ key, shiftKey: false, altKey: false, metaKey: false, ctrlKey: false, ...mods });
assert.equal(press("N", { shiftKey: true }), "shift+n");
assert.equal(press("+", { shiftKey: true }), "+");
assert.equal(press("Backspace"), "backspace");
assert.equal(press("Shift"), undefined);

const map = keymap();
// The same key means different things over an atom and over a bond.
assert.equal(actionFor(map, "h", "atom"), "element.H");
assert.equal(actionFor(map, "h", "bond"), "bond.hashwedge");
assert.equal(actionFor(map, "w", "bond"), "bond.wedge");
assert.equal(actionFor(map, "shift+w", "bond"), "bond.hashwedge");
assert.equal(actionFor(map, "w", "atom"), "element.N");
// Hollow wedge and dative take a key but have none by default, as in ChemDraw.
assert.ok(!map["bond.hollow"]?.length && !map["bond.dative"]?.length);
assert.equal(actionFor(keymap({ "bond.hollow": ["shift+v"] }), "shift+v", "bond"), "bond.hollow");
assert.equal(actionFor(keymap({ "bond.dative": ["shift+v"] }), "shift+v", "bond"), "bond.dative");
// ChemDraw: b is bromine over an atom and bold over a bond; Shift+B is boron.
assert.equal(actionFor(map, "b", "atom"), "element.Br");
assert.equal(actionFor(map, "b", "bond"), "bond.bold");
assert.equal(actionFor(map, "shift+b", "atom"), "element.B");
assert.equal(actionFor(map, "space", "none"), "tool.select");
assert.equal(press("ArrowUp", { altKey: true }), "alt+arrowup");
assert.equal(press("ArrowUp", { shiftKey: true }), "shift+arrowup");
// Keys that work anywhere still work over an atom when the atom has no use for them.
assert.equal(actionFor(map, "]", "atom"), "eraser.bigger");
assert.equal(actionFor(map, "n", "none"), undefined);
// A user change replaces the default, and clashes are found in the same place only.
const mine = keymap({ "element.N": ["m"] });
assert.equal(actionFor(mine, "m", "atom"), "element.N");
assert.equal(actionFor(mine, "n", "atom"), undefined);
assert.deepEqual(clashes(map, "element.N", "o"), ["element.O"]);
assert.deepEqual(clashes(map, "element.N", "2"), ["group.acetyl"]);
assert.deepEqual(clashes(map, "bond.double", "n"), []);
// Issue #10: every bond kind can take a key over a bond (Settings), the hollow wedge and dative bond too, with no
// default key, as in ChemDraw. w and h (and Shift+W) are the wedge keys.
import { BONDS } from "./kinds.ts";
assert.deepEqual(Object.keys(BONDS).filter((k) => !ACTIONS.some((a) => a.id === `bond.${k}` && a.place === "bond")), []);
assert.deepEqual([map["bond.hollow"], map["bond.dative"]], [[], []]);
assert.equal(actionFor(keymap({ "bond.hollow": ["shift+w"], "bond.hashwedge": ["h"] }), "shift+w", "bond"), "bond.hollow");
assert.deepEqual(["w", "h", "shift+w"].map((k) => actionFor(map, k, "bond")), ["bond.wedge", "bond.hashwedge", "bond.hashwedge"]);
// A bond key over a bond, on a selection and as an Actions panel style chip (which shows that key) all go through
// keyBond, so Wedge on a wedge turns it round in each.
import { readFileSync } from "node:fs";
const bondKeys = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8").match(/\w+\([^()]*BONDS\[arg as BondKind\]\.spec/g) ?? [];
assert.ok(bondKeys.length >= 3 && bondKeys.every((s) => s.startsWith("keyBond(")), bondKeys.join("\n"));
// Every Actions panel action can take a key (CD-34): none has one by default, as in ChemDraw, and a key set for one
// runs it anywhere.
import { ACTIONS, registerMenu } from "./keys.ts";
const panelActions = ACTIONS.filter((a) => a.id.startsWith("action."));
assert.ok(panelActions.length > 30 && panelActions.every((a) => !map[a.id]?.length));
assert.equal(new Set(ACTIONS.map((a) => a.id)).size, ACTIONS.length, "action ids are unique");
assert.equal(actionFor(keymap({ "action.cycle.reverse": ["shift+r"] }), "shift+r", "atom"), "action.cycle.reverse");
// A key saved for Remove the cycle under its old id (cycle.ungroup) still removes it.
assert.equal(actionFor(keymap({ "action.cycle.ungroup": ["shift+u"] }), "shift+u", "none"), "action.cycle.remove");
import { label } from "./keys.ts";
assert.equal(label("+"), "+");
assert.ok(["↩", "Enter"].includes(label("enter")));
// ChemDraw's ! and > over an atom (type a label; add a bond and type its label), and Shift+Option+arrows.
assert.equal(actionFor(map, press("!", { shiftKey: true }) ?? "", "atom"), "atom.newlabel");
assert.equal(actionFor(map, press(">", { shiftKey: true }) ?? "", "atom"), "atom.sproutlabel");
assert.equal(press("ArrowLeft", { altKey: true, shiftKey: true }), "alt+shift+arrowleft");
assert.equal(actionFor(map, "alt+shift+arrowleft", "none"), "tilt.left");
assert.equal(actionFor(map, "alt+arrowup", "none"), "rotate.ccw15");
// Shift with Command (Ctrl) and a symbol key records the physical key and keeps Shift, as a menu shortcut is
// written: ⇧⌘- (Reduce) is mod+shift+-, though the key types _. ⌘; and Option with a symbol are their keys too.
const held = (key: string, code: string, shift = false) => keyOf({ key, code, shiftKey: shift, altKey: false, metaKey: true, ctrlKey: false });
assert.equal(held("_", "Minus", true), "mod+shift+-");
assert.equal(held("+", "Equal", true), "mod+shift+=");
assert.equal(held(";", "Semicolon"), "mod+;");
assert.equal(held("!", "Digit1", true), "mod+shift+1");
assert.equal(keyOf({ key: "≠", code: "Equal", shiftKey: false, altKey: true, metaKey: false, ctrlKey: false }), "alt+=");
// View > Magnify (⇧⌘+) and Reduce (⇧⌘-): the keys pressed find the menu's commands, so the page runs them when the
// menu does not (registerMenu below puts the menu back as other checks need it).
registerMenu([["zoom_in", "Magnify", "View", "CmdOrCtrl+Shift+="], ["zoom_out", "Reduce", "View", "CmdOrCtrl+Shift+-"]]);
assert.equal(actionFor(keymap({}), held("+", "Equal", true)!, "none"), "menu.zoom_in");
assert.equal(actionFor(keymap({}), held("_", "Minus", true)!, "none"), "menu.zoom_out");
// The menu's commands join the list; one no longer in the menu (Online search off removes the Search menu) leaves it.

registerMenu([["clean_up", "Clean Up Structure", "Structure", "CmdOrCtrl+Shift+K"], ["search_reaxys", "Search Reaxys", "Search", "Alt+CmdOrCtrl+F"]]);
assert.ok(ACTIONS.some((a) => a.id === "menu.search_reaxys") && ACTIONS.some((a) => a.id === "menu.clean_up"));
assert.equal(actionFor(keymap({}), "mod+alt+f", "none"), "menu.search_reaxys");
registerMenu([["clean_up", "Clean Up Structure", "Structure", "CmdOrCtrl+Shift+K"]]);
assert.ok(!ACTIONS.some((a) => a.id === "menu.search_reaxys") && ACTIONS.some((a) => a.id === "menu.clean_up"));
assert.equal(actionFor(keymap({}), "mod+alt+f", "none"), undefined);
// View > Show Grid (⌘'), Show Rulers (⌘;) and Show Crosshair (⌥⌘X): their keys read as the page writes them.
registerMenu([["grid", "Show Grid", "View", "CmdOrCtrl+'"], ["rulers", "Show Rulers", "View", "CmdOrCtrl+;"], ["crosshair", "Show Crosshair", "View", "Alt+CmdOrCtrl+X"]]);
assert.deepEqual(["menu.grid", "menu.rulers", "menu.crosshair"].map((id) => keymap({})[id]), [["mod+'"], ["mod+;"], ["mod+alt+x"]]);
assert.equal(actionFor(keymap({}), "mod+;", "none"), "menu.rulers");
// Feedback's keys: 1, 2 and 3 with ⌘ held, all within 400 ms, in any order. No key-up is needed.
{
  const p = new Map<string, number>();
  assert.equal(feedbackChord(p, "1", 1000), false);
  assert.equal(feedbackChord(p, "3", 1100), false);
  assert.equal(feedbackChord(p, "2", 1350), true);
  assert.equal(p.size, 0, "complete keys start again");
  // Too slow: 1 at 0 ms, 3 at 500 ms. A new 1 makes them complete.
  assert.equal(feedbackChord(p, "1", 0), false);
  assert.equal(feedbackChord(p, "2", 300), false);
  assert.equal(feedbackChord(p, "3", 500), false);
  assert.equal(feedbackChord(p, "1", 600), true);
  // The same digit again is not a second digit.
  const q = new Map<string, number>();
  for (const at of [0, 50, 100]) assert.equal(feedbackChord(q, "1", at), false);
}
console.log("keys.check: ok");

// A button the keyboard moved to takes Space and Return; after a click, Space stays the Select key.
const button = { tagName: "BUTTON" }, slider = { tagName: "INPUT", type: "range" };
assert.equal(controlTakes(" ", button, true), true);
assert.equal(controlTakes("Enter", button, true), true);
assert.equal(controlTakes(" ", button, false), false);
assert.equal(controlTakes(" ", { tagName: "DIV" }, true), false);
assert.equal(controlTakes("e", button, true), false);
// A slider the keyboard moved to takes its arrow keys; after a click (as when Line width is dragged) the drawing has them.
assert.equal(controlTakes("ArrowLeft", slider, true), true);
assert.equal(controlTakes("ArrowLeft", slider, false), false);
assert.equal(controlTakes("h", slider, true), false);
// Only fields that take typed text take the drawing's keys away: text, search, number, email, url, text areas and
// rich text boxes. A slider, tick box, radio button, colour well or button does not.
for (const type of ["text", "search", "number", "email", "url"]) assert.equal(textEntry({ tagName: "INPUT", type }), true, type);
for (const type of ["range", "checkbox", "radio", "button", "color", "submit"]) assert.equal(textEntry({ tagName: "INPUT", type }), false, type);
assert.equal(textEntry({ tagName: "TEXTAREA" }), true);
assert.equal(textEntry({ tagName: "DIV", isContentEditable: true }), true);
assert.equal(textEntry({ tagName: "DIV", isContentEditable: false }), false);
// ChemDraw's text keys in a caption or label box (⌘B, ⌘I, ⌘U, ⌘T and so on): a label takes the style keys, as a
// caption does, but not Formula, Subscript or Superscript (its counts are subscripts already); ⇧⌘N in either.
for (const [key, command] of [["b", "caption.bold"], ["I", "caption.italic"], ["u", "caption.underline"], ["t", "caption.plain"]]) {
  assert.equal(textKey({ key, shiftKey: false }, true), command, key);
  assert.equal(textKey({ key, shiftKey: false }, false), command, key);
}
for (const [key, command] of [["f", "caption.formula"], ["-", "caption.sub"], ["=", "caption.super"], ["+", "caption.super"]]) {
  assert.equal(textKey({ key, shiftKey: false }, false), command, key);
  assert.equal(textKey({ key, shiftKey: false }, true), undefined, key);
}
assert.deepEqual([textKey({ key: "N", shiftKey: true }, true), textKey({ key: "n", shiftKey: true }, false), textKey({ key: "c", shiftKey: false }, false)], ["name_to_structure", "name_to_structure", undefined]);
assert.equal(textEntry({ tagName: "BUTTON" }), false);
assert.equal(textEntry(null), false);
// Home's tiles: the New row (six narrow tiles) over the recent drawings (four wide tiles to a row, ten in all, so the
// last row has two). Up and Down go to the tile in the next row whose middle is nearest across, not by reading order.
const newRow = [0, 1, 2, 3, 4, 5].map((k) => ({ x: k * 166, y: 100, width: 150, height: 130 }));
const recent = [...Array(10).keys()].map((k) => ({ x: (k % 4) * 240, y: 300 + Math.floor(k / 4) * 224 + (k % 2), width: 220, height: 200 }));
const home = [...newRow, ...recent];
// Down from the fourth New tile (middle 573) goes to the third recent drawing (middle 590), not the fourth.
assert.equal(tileTo("ArrowDown", 3, home), 8);
assert.equal(tileTo("ArrowDown", 0, home), 6);
assert.equal(tileTo("ArrowDown", 5, home), 9);
// Up from a recent drawing goes to the nearest New tile; up from the New row stays.
assert.equal(tileTo("ArrowUp", 9, home), 5);
assert.equal(tileTo("ArrowUp", 7, home), 2);
assert.equal(tileTo("ArrowUp", 2, home), 2);
// Down a recent row, and down to the short last row with nothing under: its nearest tile. Down from the last row stays.
assert.equal(tileTo("ArrowDown", 7, home), 11);
assert.equal(tileTo("ArrowDown", 13, home), 15);
assert.equal(tileTo("ArrowDown", 15, home), 15);
// Left and Right go in reading order, from the end of the New row to the first recent drawing; the ends stay.
assert.equal(tileTo("ArrowRight", 5, home), 6);
assert.equal(tileTo("ArrowLeft", 6, home), 5);
assert.equal(tileTo("ArrowLeft", 0, home), 0);
assert.equal(tileTo("ArrowRight", 15, home), 15);
// No tile with the focus: any arrow goes to the first. Other keys, or no tiles, do nothing.
assert.equal(tileTo("ArrowDown", -1, home), 0);
assert.equal(tileTo("Enter", 3, home), undefined);
assert.equal(tileTo("ArrowDown", -1, []), undefined);
// Home blocks the drawing's menu commands as a dialog does. New (and New For), Open, Settings, About and the tutorial
// still run; Undo, Redo and Select All run on the text of the name box.
const onHome = { home: true, modal: false, typing: false };
for (const id of ["select_all", "flip_h", "mirror_v", "clean_up", "zoom_in", "export", "save", "import", "command_palette", "colour_0"]) assert.equal(menuRuns(id, onHome), false, id);
for (const id of ["new", "new_quick", "new_paper", "new_own_0", "open", "settings", "about", "tutorial", "home", "recent_0", "recent_clear", "check_updates", "quit"]) assert.equal(menuRuns(id, onHome), true, id);
// Quit and Close Window ask about unsaved changes over any dialog (the Dock's Quit too).
for (const id of ["quit", "close"]) assert.equal(menuRuns(id, { home: false, modal: true, typing: false }), true, id);
// Cut, Copy and Paste (Octet's own on Linux) run everywhere: on a field's text, or on the drawing, which takes them only
// when nothing covers it.
for (const id of ["cut", "copy", "paste"]) for (const over of [onHome, { home: false, modal: true, typing: true }, { home: false, modal: false, typing: false }]) assert.equal(menuRuns(id, over), true, id);
assert.equal(menuRuns("select_all", { ...onHome, typing: true }), true);
assert.equal(menuRuns("flip_h", { ...onHome, typing: true }), false);
// A dialog blocks every command but the text ones; with no dialog and no Home, every command runs.
assert.equal(menuRuns("new", { home: false, modal: true, typing: false }), false);
assert.equal(menuRuns("undo", { home: false, modal: true, typing: true }), true);
assert.equal(menuRuns("flip_h", { home: false, modal: false, typing: false }), true);
assert.equal(menuRuns("text_bold", { home: false, modal: false, typing: true }), true);
