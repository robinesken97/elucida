// Run: node src/export.check.ts. Fails loudly if Octet's own marks on the canvas get into an exported or copied
// picture.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { CARRY_CDXML, dpiFor, pictureAs, pixelsAt, tooLarge, UI, withBackground, withMargin } from "./export.ts";
import { EMPTY, extractSelection, sprout } from "./edit.ts";

// Export, Copy and Print take the canvas, less the layers UI names. An aria-hidden element on the canvas is one of
// Octet's own (the page, the selection's frame and handles, pen points, reaction interpretation and the rest), so it
// has a class in UI.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), ui = new Set(UI.split(",").map((c) => c.slice(1)));
const hidden = editor.split("\n").filter((l) => /<(g|path|rect|circle|line|text|polygon|polyline)\b[^>]*\baria-hidden\b/.test(l));
assert.ok(hidden.length >= 10, `found only ${hidden.length} of Octet's own layers; update this check`);
for (const l of hidden) {
  const c = /<(?:g|path|rect|circle|line|text|polygon|polyline)\b[^>]*?className="([^"]+)"/.exec(l)?.[1];
  assert.ok(c?.split(" ").some((x) => ui.has(x)), `not in UI, so it shows in exported pictures: ${l.trim().slice(0, 100)}`);
}

// With something selected, Export and Quick export take the selection alone (issue #8), in every picture format: the
// part is a drawing of its own with only what is selected and the text that belongs to it.
{
  const two = sprout(sprout(sprout(EMPTY, [0, 0]), 1), [10, 0]);
  const m = { ...two, arrows: [{ id: 10, kind: "reaction" as const, from: [3, 0] as [number, number], to: [6, 0] as [number, number] }],
    captions: [{ id: 11, text: "1", x: 0, y: 0, under: [0, 1, 2] }, { id: 12, text: "note", x: 0, y: 5 }],
    shapes: [{ id: 13, kind: "box" as const, from: [8, 1] as [number, number], to: [12, -1] as [number, number] }],
    grids: [{ arrow: 10, typed: {} }, { arrow: 99, typed: {} }] };
  const part = extractSelection(m, new Set([0, 1, 2]), new Set([10]));
  assert.equal(part.atoms.length, 3, "only the selected structure");
  assert.deepEqual(part.captions?.map((c) => c.text), ["1"], "its number comes; free text left out");
  assert.deepEqual(part.arrows?.map((a) => a.id), [10]);
  assert.deepEqual(part.shapes, [], "unpicked shapes left out");
  assert.deepEqual(part.grids?.map((g) => g.arrow), [10], "the selected reaction's grid comes with it");
}
// A selection's picture draws its reaction's grid: the grids are read from the part being exported, not the drawing.
const grids = editor.slice(editor.indexOf("const gridViews = useMemo("), editor.indexOf("type GridView ="));
assert.match(grids, /const m = exporting \?\? doc;/, "grids come from the exported part");
assert.doesNotMatch(grids, /exporting === doc|\bdoc\.(grids|captions|arrows)|\((doc|reactionOf)\b/, "nothing in a grid is read from the whole drawing");
// The export paths keep to the selection, and the Export button says Quick export saves it.
const body = (name: string) => editor.slice(editor.indexOf(`function ${name}(`), editor.indexOf("\n  }\n", editor.indexOf(`function ${name}(`)));
assert.match(body("quickExport"), /selectedPart\(\) \?\? doc/, "Quick export takes the selection when there is one");
assert.match(body("openExport"), /selection: sel && pictureOf\(sel\)/, "Export… offers the selection's picture");
const dialog = readFileSync(new URL("ExportDialog.tsx", import.meta.url), "utf8");
assert.match(dialog, /useState<"all" \| "selection">\(pictures\.selection \? "selection" : "all"\)/, "Export… starts on the selection");
assert.match(dialog, /Quick export \$\{selected \? "selection " : ""\}as/, "Quick export's item names the selection");
assert.match(editor, /<ExportButton [^>]*selected=\{!!\(selection\.size \|\| picked\.size\)\}/, "the Export button knows when something is selected");

// Raster size (Sam: "change the dpi and stuff"). Pixels across are counted as export.rs counts them: a part pixel
// counts, a rounding error does not. A width or height typed in pixels sets the dpi that gives exactly it, within
// 36 to 2400 dpi.
assert.equal(pixelsAt(86, 300), 359, "86 pt at 300 dpi, as the PNG test in export.rs");
assert.equal(pixelsAt(144, 300), 600, "an exact size has no extra pixel");
assert.equal(pixelsAt(72, 72), 72);
for (const [pt, px] of [[86, 1000], [65, 777], [123.4, 3210], [10, 300]]) assert.equal(pixelsAt(pt, dpiFor(px, pt)), px, `${px} px across ${pt} pt`);
assert.equal(dpiFor(1, 100), 36, "no lower than 36 dpi");
assert.equal(dpiFor(1e6, 100), 2400, "no higher than 2400 dpi");
// At most 100 million pixels and 20,000 on a side, as draw in export.rs refuses.
assert.ok(!tooLarge(10000, 10000) && tooLarge(10001, 10000) && tooLarge(20001, 10) && !tooLarge(20000, 10));
assert.ok(tooLarge(pixelsAt(400, 2400), pixelsAt(400, 2400)), "a 400 pt square at 2400 dpi is too large");
// The background: transparent where the format has it, white, or the page's own colour filling the margin too.
{
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt" viewBox="3 4 20 10"><g/></svg>';
  assert.equal(withBackground(withMargin(svg, 2), "#FFEEDD"), '<svg xmlns="http://www.w3.org/2000/svg" width="24pt" height="14pt" viewBox="1 2 24 14"><rect x="1" y="2" width="24" height="14" fill="#FFEEDD"/><g/></svg>');
  assert.equal(withBackground(svg, "red\" onload=\"x"), svg, "only a #rrggbb colour goes in");
  const as = (format: "png" | "jpg" | "pdf", background: "white" | "transparent" | "page", page?: string) => pictureAs(svg, { format, margin: 0, background }, page);
  assert.equal(as("png", "transparent").transparent, true);
  assert.equal(as("jpg", "transparent").transparent, false, "JPEG has no transparency");
  assert.equal(as("png", "white").transparent, false);
  assert.match(as("png", "page", "#FFEEDD").svg, /<rect [^>]*fill="#FFEEDD"/);
  assert.match(as("jpg", "page", "#FFEEDD").svg, /<rect [^>]*fill="#FFEEDD"/, "JPEG takes the page colour too");
  assert.deepEqual(as("png", "page"), { svg, transparent: false }, "white for a drawing with no page colour");
  assert.doesNotMatch(as("pdf", "page", "#FFEEDD").svg, /<rect/, "vector formats keep their own page");
}
// One resolution control in Export… and Settings: any dpi typed, with the usual ones beside it. Export… also takes
// a size in pixels, refuses a picture too large, and offers the page colour and JPEG quality. Copy's PNG and bitmap
// (Windows and Linux) take the export dpi, as ChemDraw's Copy As PNG takes its Save As PNG resolution.
const settingsWindow = readFileSync(new URL("SettingsWindow.tsx", import.meta.url), "utf8");
for (const [name, src] of [["Export…", dialog], ["Settings", settingsWindow]]) {
  assert.match(src, /<DpiField value=\{(prefs|files)\.dpi\}/, `${name} has the resolution field`);
  assert.doesNotMatch(src, /<Select label="Resolution"/, `${name} has no second resolution control`);
}
assert.match(settingsWindow, /<Select label="Background" value=\{files\.background\} options=\{BACKDROPS\}/);
assert.match(settingsWindow, /label="JPEG quality"/);
assert.match(dialog, /label="Width" unit="px"/);
assert.match(dialog, /disabled=\{!ok \|\| big\}/, "Export… is off for a picture too large");
assert.match(editor, /copyToClipboard\(\{ dpi: settings\.files\.dpi,/, "Copy's picture takes the export dpi");
assert.match(editor, /page=\{pageColour\(style\)\}/);
assert.equal((editor.match(/quality: f\.quality/g) ?? []).length, 2, "Export… and Quick export pass the JPEG quality");
// A typed size leaves a dpi like 289.1566…: the list beside the field names it as the field shows it. Rust reads the
// JPEG quality as a whole number, so a saved one that is not takes the default.
assert.match(dialog, /<Pick label="Resolutions" value=\{String\(shown\)\}/);
assert.match(readFileSync(new URL("settings.ts", import.meta.url), "utf8"), /Number\.isInteger\(saved\.files\?\.quality\) && inRange\(saved\.files\.quality, 1, 100\)/);
const rustPath = new URL("../src-tauri/src/clipboard.rs", import.meta.url);
if (existsSync(rustPath)) {
  const rust = readFileSync(rustPath, "utf8");
  assert.match(rust, /copy_to_clipboard\([^)]*dpi: Option<f32>/);
} else console.log("export.check: native Tauri clipboard omitted in Elucida; host clipboard has separate tests");
// A picture pasted into Word and copied back out, or saved and opened again, is the drawing again: the clipboard's
// picture on every system (PDF, EMF, PNG) carries the CDXML whenever there is a picture, not only on the Mac or with the
// CDXML type on, and Export and Quick export put it in a PDF, PNG and EMF (src-tauri/src/export.rs reads it back).
assert.deepEqual(CARRY_CDXML, ["pdf", "png", "emf"]);
assert.match(editor, /cdxml: ask\(on\.cdxml \|\| on\.pdf, "cdxml"\)/, "the clipboard's picture carries the CDXML on every system");
assert.match(body("exportPart"), /cdxml: make\("cdxml", "cdxml", \.\.\.CARRY_CDXML\)/, "Export puts the CDXML in the pictures that carry it");
assert.match(body("quickExport"), /cdxml: CARRY_CDXML\.includes\(format\)/, "Quick export puts the CDXML in the pictures that carry it");
// Octet's PNG dropped on a tile on Home is the tile's thumbnail, a picture: the app is told it went on a tile.
assert.match(editor, /"take_opened", \{ insert, project: into && "project" in into \}/, "a picture dropped on any tile is a thumbnail");
console.log("export.check: ok");
