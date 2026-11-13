// Run: node src/dialog.check.ts. Return in a dialog (Dialog.tsx): on a button that is not a field (Cancel, Don't
// Save, About's links), Return presses that button, not the action (issue 129). On a field (a text box, a list or a
// choice) Return does the action, and only a field has the focus when the dialog opens.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const dialog = read("./Dialog.tsx");
// Each <button …>…</button> in a file.
const buttons = (src: string) => src.split("<button").slice(1).map((b) => b.slice(0, b.indexOf("</button>")));

assert.match(dialog, /const FIELD = "button\[role\], button\[aria-haspopup\]";/);
assert.match(dialog, /if \(t instanceof HTMLButtonElement && card\.current\?\.contains\(t\) && !t\.matches\(FIELD\)\) t\.click\(\);\s*else if \(!disabled\) onAction\(\);/, "Return presses the button that has the focus");
assert.match(dialog, /querySelector<HTMLElement>\(`textarea, input, select, \.dialog-body :is\(\$\{FIELD\}\):not\(\[tabindex='-1'\]\)`\)/, "only a field has the focus when a dialog opens");

// The fields' buttons have a role or open a list: Segmented's choices, Switch, and Select and every Pick.
const fields = buttons(read("./Fields.tsx"));
assert.ok(fields.some((b) => / role="radio"/.test(b)) && fields.some((b) => / role="switch"/.test(b)), "Segmented and Switch");
assert.ok(buttons(read("./Menu.tsx")).some((b) => /^ ref=\{button\}[^>]* aria-haspopup="menu"/.test(b)), "Pick");
// Cancel, the action, the third choice, About's links and What's new's section names are not fields.
for (const file of ["./Dialog.tsx", "./About.tsx", "./WhatsNew.tsx"]) {
  const all = buttons(read(file));
  assert.ok(all.length, file);
  for (const b of all) assert.doesNotMatch(b, /role=|aria-haspopup/, `${file}: a button that is not a field`);
}
