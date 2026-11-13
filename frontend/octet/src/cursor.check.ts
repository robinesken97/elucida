// Run: node src/cursor.check.ts. Fails loudly if a cursor can go missing (issue #14: on Windows the canvas cursors
// were the page's colour). The canvas and the crosshair panels use Octet's own cursors, never the system's crosshair
// or I-beam, which Windows draws by inverting the page. Every cursor value ends in a keyword cursor. Each cursor,
// in black and in white, shows against light, dark, mid-grey and coloured pages: its glyph or its edge is 3:1 or more
// from the page (WCAG's non-text contrast), and Automatic's glyph alone is on white, dark and Engineering paper.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { contrast } from "./access.ts";
import { CURSOR_INKS, CURSORS, cursorColour, cursorPaint, cursorSvg, cursorValue, type CursorName } from "./cursor.ts";

const css = readFileSync(new URL("editor.css", import.meta.url), "utf8");
const KEYWORDS = /^(auto|default|none|context-menu|help|pointer|progress|wait|cell|crosshair|text|vertical-text|alias|copy|move|no-drop|not-allowed|grab|grabbing|(n|e|s|w|ne|nw|se|sw|ew|ns|nesw|nwse|col|row)-resize|all-scroll|zoom-in|zoom-out)$/;

// Every cursor value in editor.css with a picture or one of Octet's cursors has a keyword after it.
for (const [, value] of css.matchAll(/cursor:\s*([^;]+);/g)) {
  const v = value.replace(/\s*!important$/, "").trim();
  if (v === "var(--drag-cursor)") continue; // holds the cursor a drag started with, already one of these
  const own = /^var\(--cursor-(\w+),\s*([\w-]+)\)$/.exec(v);
  if (own) assert.ok(own[1] in CURSORS && KEYWORDS.test(own[2]), `${v} is one of Octet's cursors with a keyword fallback`);
  else if (/url\(|image-set|var\(/.test(v)) assert.fail(`${v} has no keyword fallback`);
  else assert.ok(KEYWORDS.test(v), `${v} is a keyword cursor`);
}
// The canvas tools and the crosshair panels use Octet's crosshair, I-beam and arrow.
const rule = (selector: string) => new RegExp(`${selector.replace(/[.[\]"]/g, "\\$&")} \\{[^}]*cursor: ([^;]+);`).exec(css)?.[1];
assert.equal(rule(".canvas"), "var(--cursor-cross, crosshair)");
assert.equal(rule('.canvas[data-tool="select"]'), "var(--cursor-select, default)");
assert.equal(rule('.canvas[data-tool="text"]'), "var(--cursor-text, text)");
assert.equal(rule(".picker-square"), "var(--cursor-cross, crosshair)");
assert.equal(rule(".spectrum-plot"), "var(--cursor-cross, crosshair)");
assert.equal(rule(".eyedropper"), "var(--cursor-cross, crosshair)");
// The boxes a label, a caption or a table cell is typed in, on the page, take the Text tool's I-beam.
for (const box of [".label-box", ".caption-box", ".cell-box"]) assert.equal(rule(box), "var(--cursor-text, text)", `${box} uses Octet's I-beam`);

// The values cursor.ts makes: a picture at its hotspot, then its keyword.
for (const name of Object.keys(CURSORS) as CursorName[]) {
  assert.equal(cursorValue(name, "one", "two", true), `url("one") ${CURSORS[name].hot.join(" ")}, ${CURSORS[name].fallback}`, "Qt host uses one native-sized bitmap");
  const v = cursorValue(name, "data:image/png;base64,AA==", "data:image/png;base64,AA==");
  const [x, y] = CURSORS[name].hot;
  assert.ok(x >= 0 && x < 24 && y >= 0 && y < 24, `${name}'s hotspot is in its 24 px box`);
  assert.ok(v.endsWith(`) ${x} ${y}, ${CURSORS[name].fallback}`) && KEYWORDS.test(CURSORS[name].fallback), `${name}: ${v}`);
}

// Black and white: each has its glyph and its edge in the two colours, far apart.
const INK = "#0F172A"; // the light theme's --ink
const tokens = readFileSync(new URL("../brand/tokens.css", import.meta.url), "utf8");
assert.match(tokens.slice(0, tokens.indexOf("}")), new RegExp(`--ink: ${INK};`), "the cursors' black is the light theme's ink");
const PAGES = { white: "#FFFFFF", dark: "#000B24", "Engineering paper": "#1D4B86", "mid grey": "#808080", "light grey": "#C0C0C0", "dark grey": "#404040", red: "#FF0000", yellow: "#FFFF00", blue: "#0000FF", green: "#00A000" };
for (const [colour] of CURSOR_INKS.filter(([c]) => c !== "auto") as ["black" | "white", string][]) {
  const [glyph, edge] = cursorPaint(colour, INK);
  assert.ok(contrast(glyph, edge) >= 7, `${colour}: the glyph and its edge are far apart`);
  for (const name of Object.keys(CURSORS) as CursorName[]) {
    const svg = cursorSvg(name, glyph, edge, ["M0 0h256v256H0z"]);
    assert.ok(svg.includes(`"${glyph}"`) && svg.includes(`"${edge}"`), `${colour} ${name} draws its glyph and its edge`);
    assert.match(svg, /^<svg xmlns="http:\/\/www.w3.org\/2000\/svg" width="24" height="24" viewBox="0 0 24 24">/, `${name} is 24 px square`);
  }
  for (const [page, hex] of Object.entries(PAGES))
    assert.ok(Math.max(contrast(glyph, hex), contrast(edge, hex)) >= 3, `the ${colour} cursor shows on a ${page} page`);
}
// Automatic: black on a light page, white on a dark one, so the glyph itself stands out.
assert.equal(cursorColour("auto", false), "black");
assert.equal(cursorColour("auto", true), "white");
assert.equal(cursorColour("black", true), "black");
assert.equal(cursorColour("white", false), "white");
for (const [page, dark] of [["white", false], ["dark", true], ["Engineering paper", true]] as const)
  assert.ok(contrast(cursorPaint(cursorColour("auto", dark), INK)[0], PAGES[page]) >= 4.5, `Automatic's glyph stands out on a ${page} page`);

// The cursors are drawn when cursor.ts loads: called from an effect, flushSync cannot draw the Phosphor glyphs, and
// Select's square and the rotation arrow came out blank.
assert.match(readFileSync(new URL("cursor.ts", import.meta.url), "utf8"), /\nif \(typeof document !== "undefined"\) drawCursors\(\);\n/);
// The canvas takes the cursors for its page, and the Settings choice reaches it.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /const cursor = cursors\?\.\[cursorColour\(settings\.cursor, darkPaper\)\];/);
assert.match(editor, /\[`--cursor-\$\{name\}`, value\]/);
assert.match(editor, /cursor=\{settings\.cursor\} onCursor=/);

console.log("cursor: ok");
