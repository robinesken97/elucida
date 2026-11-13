// What's new: the app's notes and GitHub's (docs/release-notes) say the same, in short plain sentences (brand/CLAUDE.md:
// STE, no em dashes), and the notes show once after an update and from About.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { RELEASES } from "./releases.ts";

for (const r of RELEASES) {
  const md = readFileSync(new URL(`../docs/release-notes/${r.version}.md`, import.meta.url), "utf8").replace(/\\([*_])/g, "$1");
  const top = r.highlights ?? r.summary;
  for (const h of r.highlights ?? []) assert.ok(md.includes(`- **${h.title}.** ${h.text}`), `${r.version}: GitHub's notes have the highlight "${h.title}"`);
  for (const text of [r.intro, ...(r.highlights?.flatMap((h) => [h.title, h.text]) ?? r.summary ?? []), ...(r.signoff ?? []), ...(top ? [r.thanks] : []), ...r.sections.flatMap((s) => [...(s.note ? [s.note] : []), ...s.items])]) {
    assert.ok(md.includes(text), `${r.version}: GitHub's notes have "${text}"`);
    // Notes Sam wrote himself (heading) go in as he wrote them (13 November 2026: "bar-for-bar").
    if (r.heading) continue;
    assert.doesNotMatch(text, /—/, "no em dash");
    for (const sentence of text.split(/(?<=\.) /)) assert.ok(sentence.split(/\s+/).length <= 22, `short sentence: "${sentence}"`);
  }
  assert.ok(md.includes(`# ${r.heading ?? `Octet Draw ${r.version}`}`));
  if (top) assert.ok((r.heading || top.length <= 6) && md.includes("## Highlights"), `${r.version}: a short summary at the top`);
}
assert.deepEqual(RELEASES.map((r) => r.version), [...RELEASES.map((r) => r.version)].sort((a, b) => b.localeCompare(a, undefined, { numeric: true })), "newest first");
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /settings\.seenNotes === version/, "the notes show once after an update");
assert.match(editor, /userName, seenNotes: version/, "someone new does not get them");
assert.match(editor, /onWhatsNew=\{ownNotes && /, "About offers them");
// The notes start with one line and a Donate button, above the highlights. It opens Sam's own link and nothing else
// (src-tauri open_link).
const whatsNew = readFileSync(new URL("WhatsNew.tsx", import.meta.url), "utf8"), native = readFileSync(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8");
assert.match(whatsNew, /Octet Draw is free\. If you want to help, you can donate\./);
assert.match(whatsNew, /invoke\("open_link", \{ name: "donate" \}\)[^\n]*> Donate<\/button>/, "a Donate button");
assert.ok(whatsNew.indexOf("notes-donate") > whatsNew.indexOf("{release.intro}") && whatsNew.indexOf("notes-donate") < whatsNew.indexOf("notes-highlights"), "Donate is at the top, under the first line");
// The highlights show in full. Every other section is folded to its name and the number of its changes, with the
// Actions panel's fold (Fold in Actions.tsx): a click opens it.
assert.match(whatsNew, /className="fold-title" aria-expanded=\{open\.includes\(s\.title\)\}/);
assert.match(whatsNew, /className="fold-body" data-open=/);
assert.match(native, /"donate" => "https:\/\/buymeacoffee\.com\/chemmansam"\.to_string\(\)/, "the donation link is the one fixed address");
console.log("releases.check: ok");
