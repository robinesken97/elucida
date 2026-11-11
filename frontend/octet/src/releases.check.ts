// What's new: the app's notes and GitHub's (docs/release-notes) say the same, in short plain sentences (brand/CLAUDE.md:
// STE, no em dashes), and the notes show once after an update and from About.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { RELEASES } from "./releases.ts";

for (const r of RELEASES) {
  const md = readFileSync(new URL(`../docs/release-notes/${r.version}.md`, import.meta.url), "utf8").replace(/\\([*_])/g, "$1");
  for (const text of [r.intro, ...(r.summary ?? []), ...(r.summary ? [r.thanks] : []), ...r.sections.flatMap((s) => s.items)]) {
    assert.ok(md.includes(text), `${r.version}: GitHub's notes have "${text}"`);
    assert.doesNotMatch(text, /—/, "no em dash");
    for (const sentence of text.split(/(?<=\.) /)) assert.ok(sentence.split(/\s+/).length <= 22, `short sentence: "${sentence}"`);
  }
  assert.ok(md.includes(`# Octet Draw ${r.version}`));
  if (r.summary) assert.ok(r.summary.length <= 6 && md.includes("## Highlights"), `${r.version}: a short summary at the top`);
}
assert.deepEqual(RELEASES.map((r) => r.version), [...RELEASES.map((r) => r.version)].sort((a, b) => b.localeCompare(a, undefined, { numeric: true })), "newest first");
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /settings\.seenNotes === version/, "the notes show once after an update");
assert.match(editor, /userName, seenNotes: version/, "someone new does not get them");
assert.match(editor, /onWhatsNew=\{ownNotes && /, "About offers them");
console.log("releases.check: ok");
