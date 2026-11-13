// Run: node src/inventory.check.ts. Fails loudly if this commit takes away something users had in the last release
// (decision 0024): a menu item or its shortcut, an Actions panel command, a setting, a template, an animation, an
// overlay's exit motion, or a glide. Each is read from the source of the last release tag (git) and of this tree.
// Something may go only when docs/removals.md names it (`inventory:<kind>:<name>`) with the reason and "Approved by
// Sam". Set OCTET_BASE and OCTET_HEAD to compare two tags (OCTET_BASE=v1.1.0 OCTET_HEAD=v1.1.1).
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync } from "node:fs";

const root = new URL("..", import.meta.url);
const git = (...a: string[]) => execFileSync("git", a, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], maxBuffer: 1 << 28 }).trim();
const head = process.env.OCTET_HEAD;

// The last release before this tree: the newest v* tag that is an ancestor of HEAD (not HEAD's own, for a clean tree).
let base = process.env.OCTET_BASE;
try {
  if (!base) {
    // A tree with changes is newer than a tag on its commit, so that tag is the last release.
    const at = git("rev-parse", `${head ?? "HEAD"}^{commit}`), changed = !head && git("status", "--porcelain", "--untracked-files=no") !== "";
    base = git("tag", "--list", "v*", "--sort=-v:refname").split("\n").filter(Boolean).find((t) => {
      const c = git("rev-parse", `${t}^{commit}`);
      if (c === at) return changed;
      try { git("merge-base", "--is-ancestor", c, at); return true; } catch { return false; }
    });
  }
} catch { base = undefined; }
if (!base) {
  // CI must have the tags (fetch-depth: 0); elsewhere a clone without them is told so.
  assert.ok(!process.env.CI, "inventory.check: no release tag to compare with; fetch the tags (fetch-depth: 0)");
  console.log("inventory.check: skipped, no release tag (git fetch --tags)");
  process.exit(0);
}

type Read = (path: string) => string | undefined;
const fromTree: Read = (p) => (existsSync(new URL(p, root)) ? readFileSync(new URL(p, root), "utf8") : undefined);
const fromRef = (ref: string): Read => (p) => { try { return git("show", `${ref}:${p}`); } catch { return undefined; } };
const listRef = (ref: string | undefined, dir: string) => (ref ? git("ls-tree", "--name-only", `${ref}:${dir}`).split("\n") : readdirSync(new URL(dir, root)));

function inventory(read: Read, ref?: string) {
  const items = new Map<string, Set<string>>();
  const add = (kind: string, name: string) => { if (!items.has(kind)) items.set(kind, new Set()); items.get(kind)!.add(name); };
  const sources = listRef(ref, "src").filter((f) => /\.(tsx?|css)$/.test(f) && !f.includes(".check.")).map((f) => [f, read(`src/${f}`) ?? ""] as const);
  const code = sources.filter(([f]) => !f.endsWith(".css")).map(([, t]) => t).join("\n"), css = sources.filter(([f]) => f.endsWith(".css")).map(([, t]) => t).join("\n");
  // The menus, with each item's shortcut (src-tauri/src/main.rs).
  const menus = read("src-tauri/src/main.rs") ?? "";
  // Each item("id", label, "shortcut") and check(…): its brackets matched, so a label made in code (1.2's
  // `&object.map_or("Save".into(), …)`) is read too. The shortcut is the call's last text.
  for (const m of menus.matchAll(/\b(?:item|check)\("([\w:.-]+)",/g)) {
    let depth = 1, k = m.index! + m[0].length, inText = false;
    for (; k < menus.length && depth; k++) {
      const c = menus[k];
      if (inText) { if (c === "\\") k++; else if (c === '"') inText = false; }
      else if (c === '"') inText = true;
      else if (c === "(") depth++;
      else if (c === ")") depth--;
    }
    const texts = [...menus.slice(m.index! + m[0].length, k - 1).matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((t) => t[1]);
    add("menu", m[1]);
    const key = texts.length >= 2 ? texts[texts.length - 1] : "";
    if (key) add("shortcut", `${m[1]}=${key}`);
  }
  // The Actions panel's commands.
  for (const m of (read("src/Actions.tsx") ?? "").matchAll(/\bit\(<[^>]*\/?>(?:[^<]*<\/\w+>)?, "[^"]*", "([\w:.-]+)"/g)) add("action", m[1]);
  // Settings: each field of the Settings type.
  const type = /export type Settings = \{([\s\S]*?)\n\};/.exec(read("src/settings.ts") ?? "")?.[1] ?? "";
  for (const m of type.replace(/\/\/.*$/gm, "").matchAll(/(?:^|[;{\n])\s*(\w+)\??:/g)) add("setting", m[1]);
  // The template library.
  const library = JSON.parse(read("src/library.json") ?? "[]") as { name: string; items: { name: string }[] }[];
  for (const set of library) for (const t of set.items ?? []) add("template", `${set.name}/${t.name}`);
  // Motion: every animation in the style sheets, every overlay that leaves with a motion, and the glides (counted).
  for (const m of css.matchAll(/@keyframes ([\w-]+)/g)) add("animation", m[1]);
  for (const m of code.matchAll(/<Exit>\{[^&\n]*&&\s*<(\w+)/g)) add("exit", m[1]);
  const glides = (code.match(/\bglideTo\(/g) ?? []).length;
  add("glide-calls", String(glides));
  return { items, glides };
}

const before = inventory(fromRef(base), base), after = inventory(head ? fromRef(head) : fromTree, head);
// Only the lines under "## Approved" count: the format lines above it are examples.
const removals = (fromTree("docs/removals.md") ?? "").split("## Approved")[1] ?? "";
const approved = (key: string) => removals.split("\n").some((l) => l.includes(`\`${key}\``) && /Approved by Sam/i.test(l));
const gone: string[] = [];
for (const [kind, names] of before.items) {
  if (kind === "glide-calls") continue;
  for (const name of names) if (!after.items.get(kind)?.has(name) && !approved(`inventory:${kind}:${name}`)) gone.push(`inventory:${kind}:${name}`);
}
if (after.glides < before.glides && !approved(`inventory:glide-calls:${before.glides}`)) gone.push(`inventory:glide-calls:${before.glides} (now ${after.glides})`);
// The lists must find things, or a change of layout would empty them and pass.
for (const kind of ["menu", "shortcut", "action", "setting", "template", "animation", "exit"]) assert.ok((after.items.get(kind)?.size ?? 0) > 3, `inventory.check found no ${kind} in this tree: fix the reader`);
assert.ok(after.glides >= 5, "inventory.check found no glides in this tree: fix the reader");

if (gone.length) {
  console.error(`inventory.check: ${gone.length} thing(s) users had in ${base} are gone from ${head ?? "this tree"}:\n${gone.map((g) => `  ${g}`).join("\n")}\n` +
    "Put each back, or ask Sam to approve it in docs/removals.md (decision 0024).");
  process.exit(1);
}
const count = [...after.items.values()].reduce((n, s) => n + s.size, 0);
console.log(`inventory.check: ok (${count} things, none gone since ${base})`);
