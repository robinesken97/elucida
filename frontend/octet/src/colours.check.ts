// Run: node src/colours.check.ts. Fails if Octet's colours stop being one system: every colour menu with the same parts
// in the same order (recent colours at the top), the user's own colours moved and added right, the eyedropper's colours
// read right, and every place that offers colours using the one menu.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ADD, addColour, chosenKey, colourOptions, elementColoursOn, hexOf, moveColour, OWN_MOST, ownIndex, PICK, RECENT_MOST, recentColours, rememberColour } from "./colours.ts";
import { COLOURS, HIGHLIGHT_COLOURS } from "./docstyle.ts";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const own = [{ name: "Lab red", hex: "#C0392B" }, { name: "Paper teal", hex: "#127A7A" }];

// The parts, in order: recent colours, None (where it applies), the presets, the user's own, then the eyedropper and the
// picker. Recent colours take their names from the presets and the user's colours.
const groups = colourOptions(HIGHLIGHT_COLOURS, own, "none", true, ["#127a7a", "#2F6FED", "#ABCDEF"]);
assert.equal(groups.length, 4);
assert.deepEqual(groups[0].map((o) => o.name), ["Paper teal", "Blue", "#ABCDEF"], "recent colours first, by name");
assert.equal(colourOptions(HIGHLIGHT_COLOURS, [], "none", true, ["#B42323"])[0][0].name, "Red", "named from Octet's ink colours in the Highlight menu too");
assert.deepEqual(groups[1][0], { key: "none", name: "None" });
assert.deepEqual(groups[1].slice(1).map((o) => o.hex), HIGHLIGHT_COLOURS.map(([, h]) => h));
assert.deepEqual(groups[2].map((o) => o.name), ["Lab red", "Paper teal"]);
assert.deepEqual(groups[3].map((o) => [o.key, o.name]), [[PICK, "Pick from screen"], [ADD, "Add colour…"]]);
assert.equal(new Set(groups.flat().map((o) => o.key)).size, groups.flat().length, "every option has its own key");
assert.equal(chosenKey(groups, "none"), "none");
// Ink colours have no None. The colour chosen now is ticked once, at its first place; one in no list shows as Custom.
const ink = colourOptions(COLOURS, own, "#127A7A", false, ["#127A7A"]);
assert.ok(!ink[1].some((o) => o.key === "none"));
assert.equal(chosenKey(ink, "#127a7a"), "r0");
const odd = colourOptions(COLOURS, own, "#123456", false, []);
assert.deepEqual(odd[1].at(-1), { key: "#123456", name: "Custom", hex: "#123456" });
assert.equal(chosenKey(odd, "#123456"), "#123456");
assert.ok(!colourOptions(COLOURS, own, "#000000", false, []).flat().some((o) => o.name === "Custom"), "a preset is not Custom");

// The user's own colours: an option's place in them, moved, and a colour added once, up to OWN_MOST.
assert.equal(ownIndex("o1", own), 1);
assert.equal(ownIndex("o2", own), -1, "the drawing's colours after the user's are not theirs to change");
assert.equal(ownIndex("r0", own), -1);
assert.deepEqual(moveColour([...own, { name: "C", hex: "#000001" }], 2, 0).map((c) => c.name), ["C", "Lab red", "Paper teal"]);
assert.deepEqual(moveColour(own, 0, 1).map((c) => c.name), ["Paper teal", "Lab red"]);
assert.equal(addColour(own, "#c0392b"), own, "a colour the user has already is not added again");
assert.deepEqual(addColour(own, "#010203").at(-1), { name: "Colour 3", hex: "#010203" });
const full = Array.from({ length: OWN_MOST }, (_, k) => ({ name: `C${k}`, hex: `#${k.toString(16).padStart(6, "0")}` }));
assert.equal(addColour(full, "#FFFFFF").length, OWN_MOST);
// Fifty and more of the user's own colours stay one list, in their order, after the presets.
assert.deepEqual(colourOptions(COLOURS, full, "#000000", false, [])[2].map((o) => o.name), full.map((c) => c.name));

// Recent colours: newest first, each once whatever its case, RECENT_MOST at most (storage is optional, so this works
// with none).
for (let k = 0; k < RECENT_MOST + 2; k++) rememberColour(`#00000${k}`);
rememberColour("#000003");
rememberColour("not a colour");
assert.equal(recentColours().length, RECENT_MOST);
assert.equal(recentColours()[0], "#000003");
assert.equal(recentColours().filter((h) => h.toLowerCase() === "#000003").length, 1);

// The colours the eyedropper reads from the page, as #RRGGBB; nothing for none, a clear colour or a gradient.
assert.equal(hexOf("rgb(255, 0, 16)"), "#FF0010");
assert.equal(hexOf("rgba(18, 52, 86, 0.4)"), "#123456");
assert.equal(hexOf("rgb(18 52 86 / 0.5)"), "#123456");
assert.equal(hexOf("rgba(0, 0, 0, 0)"), undefined);
assert.equal(hexOf("none"), undefined);
assert.equal(hexOf('url("#shade3")'), undefined);
assert.equal(hexOf("#abcdef"), "#ABCDEF");

// Every place that offers colours uses the one menu: the Actions panel (Colour, Highlight, Ring fill) and its
// right-click menu, Settings' text colour and a folder on Home. The picker has the eyedropper.
const actions = read("./Actions.tsx"), settings = read("./SettingsWindow.tsx"), home = read("./Home.tsx"), picker = read("./ColourPicker.tsx");
for (const label of ["Colour", "Highlight", "Ring fill"]) assert.match(actions, new RegExp(`<ColourPick label="${label}"`), label);
assert.match(actions, /colourItems\(colourOptions\(/, "the right-click menu's Colour");
// In Settings it is drawn as the fields beside it, with the colour's name where a select shows its value.
assert.match(settings, /<ColourPick field label="Text colour"/);
assert.match(picker, /className=\{field \? "select-field" : "chip pick-button"\}/);
// A swatch shows the colour as it is (no fading), and None is the same size as a colour.
assert.doesNotMatch(read("./editor.css"), /\.pick-swatch \{[^}]*opacity/);
assert.doesNotMatch(read("./editor.css"), /\.pick-swatch\.none \{[^}]*border/);
// In a menu a swatch stands in an icon's room, so its name lines up with Pick from screen and Add colour…; and the
// name of one of the user's colours keeps clear of its remove button.
assert.match(read("./editor.css"), /\.variant > \.pick-swatch \{\n  margin: 0 2px;/);
assert.match(read("./editor.css"), /\.strip\.list \.variant-cell:has\(> \.variant-action\) > \.variant \{\n  padding-right: calc\(var\(--size-action\) \+ var\(--space-2\)\);/);
assert.match(home, /colourItems\(colourOptions\(COLOURS/);
assert.ok(!/className="swatches small"|"\\u0000custom"|Custom colour…/.test(actions + home), "no colour row or Custom colour… of its own");
assert.match(picker, /aria-label="Pick from screen"[^\n]+pickColour\(\)/, "the picker's eyedropper");
// Every colour command stays, and the user's colours all have one (colour_user_N), in the app's Colour menu too.
const editor = read("./Editor.tsx"), menu = read("../src-tauri/src/main.rs");
for (const command of ["colour_${k}", "colour_user_${k}", "highlight_${k}", "ringfill_${k}", "colour_pick: ", "colours_add: ", "colour_other: "]) assert.ok(editor.includes(command), command);
assert.match(editor, /length: OWN_MOST \+ 24 \}, \(_, k\) => \[`colour_user_\$\{k\}`/);
assert.ok(menu.includes(`names.into_iter().take(${OWN_MOST + 24})`), "main.rs lists every user colour and the drawing's 24");
assert.match(menu, /item\("colour_pick", "Pick from Screen", ""\)/);
assert.match(menu, /eyedropper::pick_colour/);
// A colour changed in the picker is one step to undo, for ink as for highlights and ring fills.
assert.match(editor, /const \[hex, drag\] = command\.slice\(7\)\.split\("\."\)/);
assert.match(actions, /run\(`colour\.\$\{hex\}\$\{live \? "\.drag" : ""\}`\)/);
// A colour chosen in any colour menu joins the recent ones. The window's eyedropper takes the keys first, so Escape
// does not close Settings or a dialog under it. A long right-click colour list scrolls. Saved files take the user's
// first 20 colours, as before OWN_MOST, so a drawing's own palette keeps its room. Off X11 the screen is not read.
assert.match(picker, /rememberColour\(hex\);\s*onPick\(hex\);/);
const menus = read("./Menu.tsx");
assert.match(menus, /listOpen = \(\) => [^\n]*\.eyedropper/);
assert.match(menus, /addEventListener\("wheel", away, true\)/);
assert.match(editor, /const mine = settings\.palette\.slice\(0, 20\)/);
assert.match(read("../src-tauri/src/eyedropper.rs"), /type_\(\)\.name\(\) != "GdkX11Display"/);

// Colour by Element is a toggle (docs/plans/charts.md, H1): on only when every heteroatom in scope has its element's
// colour. A carbon's own colour does not count, and neither does an atom outside the selection.
{
  const by = { N: "#2F6FED", O: "#E5484D" }, all = new Set([0, 1, 2, 3]);
  const atoms = [{ label: "C", colour: "#123456" }, { label: "N" }, { label: "O" }, { label: "C" }];
  assert.equal(elementColoursOn(atoms, all, by), false, "nothing coloured yet");
  assert.equal(elementColoursOn([atoms[0], { label: "N", colour: "#2f6fed" }, { label: "O", colour: "#E5484D" }, atoms[3]], all, by), true, "every heteroatom has its colour, in any case of letters");
  assert.equal(elementColoursOn([atoms[0], { label: "N", colour: "#2F6FED" }, { label: "O", colour: "#00FF00" }, atoms[3]], all, by), false, "one in another colour");
  assert.equal(elementColoursOn([atoms[0], { label: "N", colour: "#2F6FED" }, { label: "O" }, atoms[3]], new Set([0, 1]), by), true, "only the selection counts");
  assert.equal(elementColoursOn(atoms, new Set([0, 3]), by), false, "no heteroatom in scope");
  assert.match(editor, /on = elementColoursOn\(doc\.atoms, atoms, by\)/);
}
