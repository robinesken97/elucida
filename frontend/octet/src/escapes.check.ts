// Run: node src/escapes.check.ts. Fails loudly if typing \delta stops giving δ, if a name that is not exactly one of
// LaTeX's is changed, if a place text is typed misses the names, or if the Character Map loses a character or its
// way to type into the text (issue 25, PR 42).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ESCAPES, expandEscapes, expandRuns, keptText } from "./escapes.ts";
import { markupRuns } from "./experiment.ts";
import { CHAR_GROUPS, charName } from "./chars.ts";

// Names, exactly as LaTeX's.
for (const [typed, kept] of [
  ["\\delta+", "δ+"], ["h\\nu", "hν"], ["\\Delta G\\ddagger", "Δ G‡"], ["\\lambda_max", "λ_max"], ["A \\to B", "A → B"], ["\\alpha-D-glucose", "α-D-glucose"],
  ["\\leq", "≤"], ["x \\leq 5", "x ≤ 5"], ["\\neq", "≠"], ["\\geq", "≥"], ["\\cdots", "⋯"], ["\\pm", "±"], ["\\mu", "μ"], ["\\AA", "Å"], ["25 \\degree C", "25 ° C"],
  ["\\Delta T", "Δ T"], ["\\Delta{}T", "ΔT"], ["\\sum", "∑"], ["\\Sigma", "Σ"],
  // Stays as typed: not a name (exactly), a path, a doubled backslash.
  ["\\DeltaT", "\\DeltaT"], ["\\leqq", "\\leqq"], ["\\number", "\\number"], ["C:\\new\\data", "C:\\new\\data"], ["\\temp\\pictures", "\\temp\\pictures"],
  ["\\\\delta", "\\\\delta"], ["\\", "\\"], ["\\constructor", "\\constructor"], ["\\toString", "\\toString"], ["no backslash", "no backslash"],
] as const) assert.equal(expandEscapes(typed), kept, typed);
// Case, as LaTeX: \delta is δ and \Delta is Δ.
assert.notEqual(ESCAPES.delta, ESCAPES.Delta);
// Each is one real character, never a Latin letter (the Symbol font's trick).
for (const [name, ch] of Object.entries(ESCAPES)) {
  assert.ok(/^[A-Za-z]+$/.test(name), name);
  assert.ok([...ch].length === 1 && ch.codePointAt(0)! > 127, `${name} is one character that is not ASCII`);
}
assert.equal(ESCAPES.minus, "\u2212", "the real minus");

// Rich text: a name keeps the style of its backslash, and may cross runs.
assert.deepEqual(expandRuns([{ text: "h" }, { text: "\\nu", italic: true }]), [{ text: "h" }, { text: "ν", italic: true }]);
assert.deepEqual(expandRuns([{ text: "\\del", bold: true }, { text: "ta+" }]), [{ text: "δ", bold: true }, { text: "+" }]);
const plain = [{ text: "C:\\new" }];
assert.equal(expandRuns(plain), plain, "nothing to change: the same runs");

// Text the box opened with, and text pasted into it, are never expanded: as many of each name as they hold stay, from
// the left. A name typed after them is.
assert.equal(expandEscapes("C:\\temp\\pi", "C:\\temp\\pi"), "C:\\temp\\pi", "a pasted path");
assert.equal(expandEscapes("\\alpha and \\alpha", "\\alpha"), "\\alpha and α", "one kept, one typed");
assert.equal(expandEscapes("\\beta", "\\alpha"), "β");
assert.deepEqual(expandRuns([{ text: "\\pi", bold: true }], "x \\pi"), [{ text: "\\pi", bold: true }]);
assert.equal(keptText("a"), "a", "no paste outside a page");
// Typing stays quick on long text.
const long = "\\alpha ".repeat(5000), t0 = performance.now();
assert.equal(expandEscapes(long, "\\alpha ".repeat(1000)).split("α").length - 1, 4000, "all but the 1000 kept");
assert.ok(performance.now() - t0 < 200, "long text expands quickly");

// The experiment page's markup reads the same names: one table.
assert.deepEqual(markupRuns([{ text: "$\\Delta$G" }]).map((r) => r.text).join(""), "ΔG");
assert.deepEqual(markupRuns([{ text: "\\leq" }]).map((r) => r.text).join(""), "≤");
assert.match(readFileSync(new URL("experiment.ts", import.meta.url), "utf8"), /const SYMBOLS = ESCAPES;/);

// Every place text is typed takes the names when it is kept: a caption (and a cycle's step name, which is a caption),
// an atom label (and one turned into a structure), a table cell, a stoichiometry grid cell and the experiment details.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
const body = (name: string) => { const at = editor.indexOf(`function ${name}(`); return editor.slice(at, editor.indexOf("\n  }\n", at)); };
assert.match(body("commitWriting"), /const typed = expandRuns\(w\.runs \?\? \[\{ text: w\.value \}\], keptText\(doc\.captions\?\.find\(\(c\) => c\.id === w\.id\)\?\.text\)\), text = plainOf\(typed\)/);
assert.match(body("commitCell"), /setTableCell\(cur, w\.r, w\.c, value,/);
assert.match(body("commitCell"), /const value = expandEscapes\(w\.value, keptText\(sh\.table\.cells\[w\.r\]\?\.\[w\.c\]\)\)/);
assert.match(body("commitGridCell"), /text = expandEscapes\(typed, keptText\(gridEdit\?\.value\)\)/);
assert.match(editor, /const typed = trimLines\(expandRuns\(editing\.runs \?\? \[\{ text: editing\.value \}\], keptText\(a\.text\)\)\)/);
assert.match(editor, /set\(setLabel\(doc, editing\.atom, expandEscapes\(editing\.value, keptText\(doc\.atoms\[editing\.atom\]\.text\)\)\)\)/);
assert.match(editor, /withDetails\(doc\.annotations, Object\.fromEntries\(Object\.entries\(dialog\.values\)\.map\(\(\[k, v\]\) => \[k, v && expandEscapes\(v, keptText\(detailsOf\(doc\.annotations\)\[k as keyof Details\]\)\)\]\)\)\)/);
assert.match(editor, /openWriting\(\{ value: "", cycle: \{ cycle: id, step, side: "name" \}/, "a step name is typed as a caption");

// The Character Map: the characters Sam listed, each with a name for screen readers, none twice in a group.
const all = CHAR_GROUPS.flatMap(([, cs]) => cs);
for (const ch of "αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ→←↑↓⇌±×÷≤≥≠≈∞°′″‰√∂∫∑⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻₀₁₂₃₄₅₆₇₈₉₊₋‡•✱") assert.ok(all.includes(ch), `${ch} is in the map`);
for (const [group, cs] of CHAR_GROUPS) {
  assert.equal(new Set(cs).size, cs.length, `${group}: each character once`);
  for (const ch of cs) assert.ok(charName(ch) !== ch && charName(ch).length > 2, `${ch} has a name`);
}
assert.equal(charName("δ"), "Greek delta");
assert.equal(charName("Δ"), "Greek capital delta");
assert.equal(charName("₂"), "Subscript two");
// It types where the caret is: the press keeps the focus in the text, the browser types the character, and focus
// moved into the map keeps every text box open (a caption or label's box, a table cell, a grid cell).
const map = readFileSync(new URL("CharMap.tsx", import.meta.url), "utf8");
assert.match(map, /onMouseDown=\{\(e\) => e\.preventDefault\(\)\}/);
assert.match(map, /document\.execCommand\("insertText", false, ch\)/);
assert.match(map, /aria-label=\{charName\(ch\)\}/);
assert.match(map, /const groups: \[string, string\[\]\]\[\] = \[\["Recent", recent\], \.\.\.CHAR_GROUPS\]/, "Recent keeps its row, so the map does not move under the pointer");
assert.match(readFileSync(new URL("RichBox.tsx", import.meta.url), "utf8"), /onBlur=\{\(e\) => \{ if \(!inMap\(e\.relatedTarget\)\) p\.onBlur\(\); \}\}/);
assert.match(editor, /onBlur=\{\(e\) => \{ if \(!inMap\(e\.relatedTarget\)\) commitGridCell\(e\.currentTarget\.value\); \}\}/);
assert.match(editor, /onBlur=\{\(e\) => \{ if \(!inMap\(e\.relatedTarget\)\) commitCell\(\); \}\}/);
// Reached from Text > Character Map, the caption's and the label's options, and the command palette, and with the
// keyboard from any text box: ⇧⌘Space (Ctrl+Shift+Space on Windows and Linux), shown in the Text menu. The Mac's own
// ⌃⌘Space stays the system's Emoji & Symbols. The key is free: no other command or drawing key has it.
const mainRs = readFileSync(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8");
assert.match(mainRs, /&item\("char_map", "Character Map", "CmdOrCtrl\+Shift\+Space"\)\?/);
{
  const { ACTIONS, clashes, keymap, registerMenu } = await import("./keys.ts");
  const items = [...mainRs.matchAll(/(?:item|check)\("(\w+)", "([^"]*)", "([^"]*)"\)/g)].map((m): [string, string, string, string] => [m[1], m[2], "", m[3]]);
  registerMenu(items);
  const map = keymap({});
  assert.deepEqual(map["menu.char_map"], ["mod+shift+space"]);
  assert.deepEqual(clashes(map, "menu.char_map", "mod+shift+space"), [], "no command in the same place has the key");
  assert.deepEqual(ACTIONS.filter((a) => map[a.id]?.includes("mod+shift+space")).map((a) => a.id), ["menu.char_map"], "no drawing key has it either");
}
// While typing, the key moves the focus into a map already open; otherwise it opens or closes the map. The map takes
// the focus when it opens over text being typed with its key, and Escape gives it back with the caret where it was (back). A
// character clicked leaves the focus in the text, so typing goes on there; one typed with Return keeps it in the map.
assert.match(editor, /if \(first && typing\(\) && byKey\) return first\.focus\(\);\s+charFocus\.current = byKey;\s+setCharMap\(\(o\) => !o\);/);
// Opened from the menu with the mouse, the map leaves the caret in the text; with its key, it takes the focus.
assert.match(editor, /<CharMap focus=\{charFocus\.current\}/);
assert.match(editor, /char_map: \[charMap \? "Hide character map" : "Character map", `⇧\$\{MOD\}Space`/);
assert.match(map, /if \(field\.current && focus\) box\.current\?\.querySelector<HTMLElement>\("\.char\[tabindex='0'\]"\)\?\.focus\(\{ preventScroll: true \}\)/);
assert.match(map, /onClick=\{\(e\) => type\(ch, e\.detail === 0\)\}/);
assert.match(map, /if \(keyboard && inMap\(from\)\)/);
assert.equal(readFileSync(new URL("Actions.tsx", import.meta.url), "utf8").match(/onClick=\{\(\) => run\("char_map"\)\}/g)?.length, 2);

console.log("escapes: ok");
