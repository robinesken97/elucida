// Run: node src/export.check.ts. Fails loudly if Octet's own marks on the canvas get into an exported or copied
// picture.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { apartShapes, type Drawing } from "./render.ts";
import { CARRY_CDXML, dpiFor, frameOf, glyphInk, inkOfText, pasteRefused, pictureAs, pixelsAt, tooLarge, UI, withBackground, withMargin } from "./export.ts";
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
// Issue 20: a picture's frame fits its ink, as ChemDraw's does (within 0.2 pt): rounded outward to hundredths of a
// point, and a label counts by its glyphs' ink.
assert.deepEqual(frameOf([-44.13, -28.72, 30.81, 20.0], 0.75), [-33.1, -21.54, 56.21, 36.54]);
assert.deepEqual(frameOf([0, 0, 100, 40], 0.75), [0, 0, 75, 30], "an exact size stays exact");
assert.deepEqual(frameOf([5, 5, 5, 5], 0.75), [3.75, 3.75, 0.01, 0.01], "at least a hundredth across");
assert.match(editor, /const t = el instanceof SVGTextElement \? inkOfText\(el, glyphInk\) : undefined;/, "Copy and Export measure labels by their ink");
{
  // Issue 55: Word reads the bounds of an EMF with text in it at 96 dpi, so the EMF's reference device is 96 dpi and
  // a device px is a whole number of its 1/20 pt logical units (src-tauri/src/vector.rs; its tests read the header).
  const vector = readFileSync(new URL("../src-tauri/src/vector.rs", import.meta.url), "utf8");
  const emf = Object.fromEntries([...vector.matchAll(/^const (UNIT|PER_PX|DEVICE|DEVICE_MM): [^=]+= \(?([^)]+?)\)?;$/gm)].map((m) => [m[1], m[2].split(", ").map((v) => Number(v.replaceAll("_", "")))]));
  assert.deepEqual(emf.DEVICE.map((px, i) => (px * 254) / (emf.DEVICE_MM[i] * 10)), [96, 96], "the reference device is 96 dpi");
  assert.equal(emf.PER_PX[0] * 96, emf.UNIT[0] * 72, "a device px is 15 logical units");
}
{
  // A text as the browser lays it out: characters in text nodes (some in a tspan), each at a start position.
  type Fake = { nodeType: number; nodeValue?: string; childNodes: Fake[] };
  const node = (kids: (string | Fake)[]): Fake => ({ nodeType: 1, childNodes: kids.map((k) => (typeof k === "string" ? { nodeType: 3, nodeValue: k, childNodes: [] } : k)) });
  const text = (kids: (string | Fake)[], at: [number, number][], turned = -1, count = at.length) =>
    Object.assign(node(kids), { getNumberOfChars: () => count, getRotationOfChar: (i: number) => (i === turned ? 30 : 0), getStartPositionOfChar: (i: number) => ({ x: at[i][0], y: at[i][1] }) }) as unknown as SVGTextElement;
  // Capitals 9.55 px above the baseline, 1 px in from each side of their 9.63 px advance; a smaller subscript 3.
  const sub = node(["3"]);
  const glyph = (ch: string, el: Element): [number, number, number, number] => ((el as unknown) === sub ? [0.5, -7.2, 5, 0.1] : ch === "O" ? [0.6, -9.8, 9.8, 0.2] : [1, -9.55, 8.63, 0]);
  const ink = (t: SVGTextElement) => inkOfText(t, glyph)?.map((v) => +v.toFixed(6));
  assert.deepEqual(ink(text(["NH"], [[10, 20], [19.63, 20]])), [11, 10.45, 28.26, 20], "NH: from the N's stem to the H's, cap height to baseline");
  assert.deepEqual(ink(text(["CH", sub], [[0, 20], [9.63, 20], [19.26, 22.83]])), [1, 10.45, 24.26, 22.93], "the subscript where it sits");
  assert.deepEqual(ink(text(["O H"], [[0, 20], [10.7, 20], [14.4, 20]])), [0.6, 10.2, 23.03, 20.2], "a space has no ink");
  assert.equal(inkOfText(text(["NH"], [[10, 20], [19.63, 20]], 1), glyph), undefined, "a turned character: getBBox");
  assert.equal(inkOfText(text(["N  H"], [[10, 20], [19.63, 20], [22, 20]], -1, 3), glyph), undefined, "collapsed spaces: getBBox");
  assert.equal(inkOfText(text(["NH"], [[10, 20], [19.63, 20]]), () => undefined), undefined, "text with a line under it: getBBox");
}
{
  // glyphInk in a stand-in browser: an atom's number or R and S on the middle baseline, which Chromium's
  // getStartPositionOfChar does not move to, and underlined text count by getBBox; plain text by measureText.
  type Style = Record<string, string>;
  const g = globalThis as unknown as { document: unknown; getComputedStyle: (el: { style: Style }) => Style };
  g.document = { createElement: () => ({ getContext: () => ({ font: "", measureText: () => ({ actualBoundingBoxLeft: -1, actualBoundingBoxAscent: 9.55, actualBoundingBoxRight: 8.63, actualBoundingBoxDescent: 0 }) }) }) };
  g.getComputedStyle = (el) => ({ textDecorationLine: "none", dominantBaseline: "auto", alignmentBaseline: "auto", ...el.style });
  const el = (style: Style) => ({ style, closest: () => null }) as unknown as Element;
  assert.deepEqual(glyphInk("N", el({})), [1, -9.55, 8.63, 0]);
  assert.deepEqual(glyphInk("N", el({ dominantBaseline: "alphabetic" })), [1, -9.55, 8.63, 0]);
  for (const style of [{ dominantBaseline: "middle" }, { dominantBaseline: "central" }, { alignmentBaseline: "middle" }, { textDecorationLine: "underline" }]) assert.equal(glyphInk("R", el(style)), undefined, JSON.stringify(style));
}
assert.equal(withMargin('<svg width="56.21pt" height="36.55pt" viewBox="-33.1 -21.54 56.21 36.55"><g/></svg>', 7.2), '<svg width="70.61pt" height="50.95pt" viewBox="-40.3 -28.74 70.61 50.95"><g/></svg>', "no rounding noise");
// Issue 23: a paste that finds nothing it can use says so when the clipboard holds something (a ChemDraw picture
// copied back out of Word on Windows: an EMF with no CDXML and OLE formats), and nothing for an empty clipboard. Text
// that is not a structure keeps its own reason. The app's paste calls it after every other route fails.
assert.equal(pasteRefused({ filled: true }, undefined, "why"), "Octet cannot read what is on the clipboard.");
assert.equal(pasteRefused({ filled: false }, undefined, "why"), undefined);
assert.equal(pasteRefused({}, " ", "why"), undefined);
assert.equal(pasteRefused({ filled: true }, "xyzzy", "Paste a name."), "Octet cannot read this structure. Paste a name.");
assert.match(editor, /if \(picture\) return pastePicture\(picture\);\s+const say = pasteRefused\(clip, text, why\);\s+if \(say\) setNotice\(say\);/);
// The size of an export comes from what is drawn, never from what only shapes it: a shadowed box's mask is a square
// 200,000 px wide, and measured it made an A4 drawing 52,919 mm across.
{
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  const ink = /function canvasInk\([\s\S]*?\n  \}\n/.exec(editor)?.[0] ?? "";
  assert.match(ink, /el\.closest\("defs, mask, clipPath, pattern, marker, symbol, filter"\)\) continue;/, "canvasInk leaves out defs and masks");
}
// A picture that leaves Octet (Copy, Export) draws each line of a bond, ring circle, symbol and arrow as a path of its own, as
// ChemDraw's PDF does, so Inkscape and Illustrator can move each one. The canvas keeps one path per colour.
{
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /function structurePaths\(d: Drawing, apart = false\): \[string, string\]\[\] \{\n  if \(apart && d\.owners\) \{\n    return apartShapes\(d\)/, "structurePaths uses apartShapes");
  // A double bond (owner 0) gives two paths; a ring circle (owner -1) keeps its hole, listed before the circle.
  const sq = (x: number, y: number, w: number, h: number): [number, number][] => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
  const shapes = apartShapes({ polygons: [sq(0, 0, 10, 1), sq(1, 3, 8, 1), sq(23, 3, 4, 4), sq(20, 0, 10, 10)], colours: [undefined, undefined, undefined, undefined], alphas: [1, 1, 1, 1], owners: [0, 0, -1, -1] } as unknown as Drawing);
  assert.deepEqual(shapes.map(([key, polys]) => [key, polys.length]), [["|1.00|0|0", 1], ["|1.00|0|1", 1], ["|1.00|-1|3", 2]], "each line apart, the hole with its circle");
  assert.match(editor, /const structureInk = useMemo\([^\n]*structurePaths\(d, !!exporting\)[^\n]*\[drawing, exporting\]\)/, "structures apart when exporting");
  assert.match(editor, /if \(exporting\) each\.push\(\[key, path\]\);/, "arrows apart when exporting");
}
console.log("export.check: ok");
