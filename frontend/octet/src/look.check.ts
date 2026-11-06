// Run: node src/look.check.ts. Fails loudly if the app's look or words drift from the brand: British spelling, STE
// messages, Regular icons at the role sizes, the type scale, and the named colour lists.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { elementColours, HIGHLIGHT_COLOURS, RING_FILLS } from "./docstyle.ts";

const src = new URL(".", import.meta.url);
const read = (name: string) => readFileSync(new URL(name, src), "utf8");
const tsx = readdirSync(src).filter((f) => f.endsWith(".tsx")).map((f) => [f, read(f)] as const);
const code = [...tsx, ...readdirSync(src).filter((f) => f.endsWith(".ts") && !f.endsWith(".check.ts") && !["cdxml.ts", "cdx.ts", "cdxtags.ts"].includes(f)).map((f) => [f, read(f)] as const), ["main.rs", read("../src-tauri/src/main.rs")] as const];
// The string literals in a file, without its comments and without the other spellings the command palette finds
// (Editor.tsx WORDS, such as "analyze"), which no user reads.
const strings = (text: string) => text.split("\n").filter((l) => !/^\s*(\/\/|\*|\/\*|const WORDS\b)/.test(l)).join("\n").match(/"[^"\n]*"|`[^`\n]*`/g) ?? [];

// British English in every word a user reads (code identifiers keep standard spellings; cdxml.ts, cdx.ts and cdxtags.ts
// write ChemDraw's own attribute names and values, so they are left out).
for (const [file, text] of code) {
  for (const s of strings(text)) assert.ok(!/\b(Analyz|analyz|Color\b|Colors\b|Center\b|Gray\b|Favorite|Optimiz|Organiz)/.test(s), `${file}: US spelling in ${s}`);
}
// STE messages: "Select", never "Pick", for what to select first; "cannot", never a contraction or "could not". The
// app's Rust errors reach the notice too.
const rust = readdirSync(new URL("../src-tauri/src/", src)).filter((f) => f.endsWith(".rs")).map((f) => [f, read(`../src-tauri/src/${f}`)] as const);
for (const [file, text] of [...code, ...rust]) {
  for (const s of strings(text)) {
    assert.ok(!/\b(can't|couldn't|won't|doesn't|isn't|don't|didn't|could not)\b/i.test(s), `${file}: contraction or "could not" in ${s}`);
  }
  assert.ok(!/setNotice\(["`]Pick /.test(text), `${file}: a notice says Pick, not Select`);
}
// Phosphor icons: Regular weight only, at a role size (BRAND.md Iconography): 20 tools, 18 rows, 16 chips and buttons,
// 12 small actions. Page thumbnails and the mark draw at their own sizes.
for (const [file, text] of tsx) {
  assert.ok(!/<[A-Z]\w*[^>]*\sweight=/.test(text), `${file}: an icon with a weight other than Regular`);
  for (const line of text.split("\n")) {
    for (const m of line.matchAll(/<([A-Z]\w*)[^<>]*?\ssize=\{(\d+)\}/g)) {
      if (["PageThumb", "Mark"].includes(m[1]) || (m[1] === "Plus" && line.includes("home-thumb"))) continue;
      assert.ok([12, 16, 18, 20].includes(Number(m[2])), `${file}: <${m[1]}> at ${m[2]} px`);
    }
  }
}
// Every close button in a panel header says Close.
for (const [file, text] of tsx) {
  for (const m of text.matchAll(/className="actions-close"[^>]*aria-label="([^"]+)"/g)) assert.ok(/^(Close|Full screen)/.test(m[1]), `${file}: close button "${m[1]}"`);
}
// One icon for one action (BRAND.md Iconography): across the Actions panel, the menu commands and the palette's own
// rows, an icon stands for one command. Three pairs share an icon but never show together: Copy (a mixed selection) and
// Copy as SMILES (structures), Reverse (arrows) and Point the other way (bonds), and a plate's Rf values and a spot's Rf.
const shared = [["copy", "copy_smiles"], ["arrow.reverse", "bond.flip"], ["shape.rf", "spot.rf"]];
const actionsTsx = read("Actions.tsx"), editorTsx = read("Editor.tsx");
const uses: [string, string][] = [];
// A glyph with a letter (SearchGlyph) is a different icon for each letter.
for (const m of actionsTsx.matchAll(/it\(<(\w+(?: letter="\w+")?)[^>]*\/>,\s*[^,]*?(?:"[^"]*"\s*:\s*)?"[^"]*",\s*"([^"]+)"/g)) uses.push([m[1], m[2]]);
for (const m of actionsTsx.matchAll(/it\(<span className="glyph-text">([^<]+)<\/span>,\s*[^,]*?(?:"[^"]*"\s*:\s*)?"[^"]*",\s*"([^"]+)"/g)) uses.push([`text ${m[1]}`, m[2]]);
for (const m of actionsTsx.matchAll(/\["(\w+)", "[^"]+", <(\w+) size=\{18\} \/>\]/g)) uses.push([m[2], m[1]]);
for (const m of actionsTsx.matchAll(/\{ icon: <(\w+) size=\{18\} \/>, name: [^,]+, command: "([^"]+)"/g)) uses.push([m[1], m[2]]);
const menuBlock = editorTsx.slice(editorTsx.indexOf("const MENU_NAMES"), editorTsx.indexOf("const paletteCommands")).split(/\b(\w+): \[/);
for (let k = 1; k < menuBlock.length; k += 2) {
  const icon = [...menuBlock[k + 1].matchAll(/(?:<(\w+) size=\{18\} \/>|<span className="glyph-text">([^<]+)<\/span>)\]/g)].pop();
  if (icon) uses.push([icon[1] ?? `text ${icon[2]}`, menuBlock[k]]);
}
const paletteBlock = editorTsx.slice(editorTsx.indexOf("const paletteCommands"), editorTsx.indexOf("const drawCommand"));
for (const m of paletteBlock.matchAll(/id: "([^"]+)", name: "[^"]*"[^}]*?icon: <(\w+) size=\{18\} \/>/g)) uses.push([m[2], m[1]]);
for (const m of paletteBlock.matchAll(/\["(\w+)", "[^"]+", <(\w+) size=\{18\} \/>\]/g)) uses.push([m[2], `settings:${m[1]}`]);
// The tools' own glyphs (a bond, a ring, a lone pair): an action does not borrow them.
for (const m of paletteBlock.matchAll(/variants\("(\w+)", "\w+",[^\n]*?<(\w+Glyph)\b/g)) uses.push([m[2], `tool:${m[1]}`]);
assert.ok(uses.length > 120, `look.check found only ${uses.length} icons; update its patterns`);
// An icon imported under a second name (Angle as AngleIcon) is the same icon.
const iconImports = [actionsTsx, editorTsx].map((t) => /import \{([^}]*)\} from "@phosphor-icons\/react"/.exec(t)?.[1] ?? "").join(",");
const alias = new Map([...iconImports.matchAll(/\b(\w+) as (\w+)\b/g)].map((m) => [m[2], m[1]]));
const commandsOf = new Map<string, Set<string>>();
for (const [name, command] of uses) { const icon = alias.get(name) ?? name; commandsOf.set(icon, (commandsOf.get(icon) ?? new Set()).add(command)); }
for (const [icon, commands] of commandsOf) {
  const list = [...commands].sort();
  assert.ok(list.length === 1 || shared.some((pair) => pair.join() === list.join()), `${icon} stands for ${list.join(", ")}`);
}

// UI text sizes on the type scale (tokens.json): 11, 13, 15, 20, 32, 64 px. The wordmark and the drawing's NMR shift
// labels (drawing units, not UI type) are the only exceptions.
const css = read("editor.css");
let selector = "";
for (const line of css.split("\n")) {
  if (line.includes("{")) selector = line;
  const m = /font(?:-size)?:\s*(?:\d00\s+)?(\d+)px/.exec(line);
  if (!m || /\.home-wordmark|\.nmr-shift/.test(selector)) continue;
  assert.ok([11, 13, 15, 20, 32, 64].includes(Number(m[1])), `editor.css: ${selector.trim()} uses ${m[1]} px`);
}

// One list of highlight colours (and ring fills after them), each with its own name and colour.
assert.equal(new Set(RING_FILLS.map(([n]) => n)).size, RING_FILLS.length);
assert.equal(new Set(RING_FILLS.map(([, h]) => h.toLowerCase())).size, RING_FILLS.length);
assert.ok(RING_FILLS.every(([n, h]) => /^[A-Z][a-z]+$/.test(n) && /^#[0-9A-F]{6}$/.test(h)));
assert.deepEqual(RING_FILLS.slice(0, HIGHLIGHT_COLOURS.length), HIGHLIGHT_COLOURS);
// Colour by element reads the atom-* tokens: nitrogen, oxygen, sulfur (and selenium), phosphorus, fluorine and chlorine,
// bromine, iodine, boron, silicon and the metals. Carbon, hydrogen and abbreviations such as Ph or Pr keep the ink colour.
const by = elementColours((name) => `token:${name}`);
assert.equal(by.N, "token:n");
assert.equal(by.O, "token:o");
assert.equal(by.S, "token:s");
assert.equal(by.Se, "token:s");
assert.equal(by.P, "token:p");
for (const e of ["F", "Cl"]) assert.equal(by[e], "token:halogen");
for (const e of ["Br", "I", "B", "Si"]) assert.equal(by[e], `token:${e.toLowerCase()}`);
for (const e of ["Pd", "Fe", "Li", "Na", "Pt", "Rh", "Bi"]) assert.equal(by[e], "token:metal");
for (const e of ["C", "H", "Ph", "Pr", "Ac", "Me"]) assert.equal(by[e], undefined);
// The tokens are there to read, in both themes.
const tokens = read("../brand/tokens.css");
for (const name of ["n", "o", "s", "p", "halogen", "br", "i", "b", "si", "metal"]) assert.equal(tokens.match(new RegExp(`--atom-${name}:`, "g"))?.length, 3);

console.log("look: ok");
