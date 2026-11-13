// Run: node src/attachments.check.ts. Add multi-centre attachment and Add variable attachment have their own icons
// (a ring with an η bond from a dot, and a ring with a bond to its centre and a dashed arc), drawn in Phosphor's style
// at 18 px, the same in the Actions panel, its right-click menu and the command palette. The panel's small buttons
// wrap with its width, but these two stay side by side.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const tools = read("./tools.tsx"), actions = read("./Actions.tsx"), editor = read("./Editor.tsx"), css = read("./editor.css");

// The icons: one ring and bond at 18 px with Phosphor's 16-unit round stroke, then a dot or a dashed arc.
assert.match(tools, /function Icon\(\{ children, size = 20 \}[^\n]*\n\s*return \(\n\s*<svg width=\{size\} height=\{size\} viewBox="0 0 256 256" fill="none" stroke="currentColor" strokeWidth=\{16\} strokeLinecap="round" strokeLinejoin="round"/);
assert.match(tools, /const AttachmentRing = [^\n]*\n\s*<Icon size=\{18\}>\n\s*<polygon [^\n]*\n\s*<line [^\n]*\n\s*\{children\}/);
assert.match(tools, /export const MultiAttachmentGlyph = \(\) => <AttachmentRing><circle [^>]*fill="currentColor"[^>]*\/><\/AttachmentRing>;/);
assert.match(tools, /export const VariableAttachmentGlyph = \(\) => <AttachmentRing><path [^>]*strokeDasharray="[^"]+" \/><\/AttachmentRing>;/);

// The same icons wherever the commands show: the Actions panel (and so its right-click menu and the palette's Actions
// rows) and the palette's menu commands. The two Phosphor asterisks are gone.
assert.match(actions, /small\(it\(<MultiAttachmentGlyph \/>, "Add multi-centre attachment", "add_multicentre"\)\), small\(it\(<VariableAttachmentGlyph \/>, "Add variable attachment", "add_variable"\)\)/);
assert.match(editor, /add_multicentre: \["Add multi-centre attachment", "", <MultiAttachmentGlyph \/>\], add_variable: \["Add variable attachment", "", <VariableAttachmentGlyph \/>\]/);
for (const [file, text] of [["Actions.tsx", actions], ["Editor.tsx", editor]]) assert.doesNotMatch(text, /\bAsterisk(Simple)?\b/, `${file} uses a Phosphor asterisk`);

// Side by side in the panel: both are one kind, so their set keeps them in order with nothing between them, and the
// tray draws them as one pair that does not wrap.
const kinds = actions.slice(actions.indexOf("const KIND_OF"), actions.indexOf("const kindOf"));
const kindOf = (command: string) => new RegExp(`\\b${command}: "(\\w+)"`).exec(kinds)?.[1] ?? "other";
assert.equal(kindOf("add_multicentre"), kindOf("add_variable"), "the two attachments are one kind");
assert.match(actions, /const paired = \(k: number\) => set\[k\]\?\.command === "add_multicentre" && set\[k \+ 1\]\?\.command === "add_variable";/);
assert.match(actions, /\{set\.map\(\(i, k\) => paired\(k - 1\) \? null : paired\(k\) \? <span key=\{i\.command\} className="tray-pair">\{button\(i\)\}\{button\(set\[k \+ 1\]\)\}<\/span> : button\(i\)\)\}/);
const pair = /\n\.tray-pair \{([^}]*)\}/.exec(css)?.[1] ?? "";
assert.match(pair, /display: flex;/, "the pair is one row");
assert.doesNotMatch(pair, /wrap/, "the pair does not wrap");
console.log("attachments.check: ok");
