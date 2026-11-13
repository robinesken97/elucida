// Run: node src/moreformats.check.ts. Fails loudly if File > More Formats shows while Settings > Pro > More formats is
// off (it is off for a new user), if the switch leaves Settings > Pro, or if a format on the list misses the File menu,
// the command palette or its command.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (p: string) => readFileSync(new URL(p, import.meta.url), "utf8");
const editor = read("Editor.tsx"), settings = read("settings.ts"), window = read("SettingsWindow.tsx"), main = read("../src-tauri/src/main.rs");

// Off for a new user, and on only when the user turned it on.
assert.match(settings, /onlineSearch: true, moreFormats: false,/);
assert.match(settings, /moreFormats: saved\.moreFormats === true,/);

// Settings > Pro holds the switch.
assert.match(window, /\{ id: "pro", name: "Pro", icon: <Toolbox size=\{18\} \/>/);
assert.match(window, /d\("pro", "File menu", "More formats", "[^"]*", <Switch on=\{p\.moreFormats\} label="More formats" onChange=\{p\.onMoreFormats\} \/>\)/);
assert.match(window, /p\.onlineSearch, p\.moreFormats,/, "the switch shows its change");
assert.match(editor, /moreFormats=\{settings\.moreFormats\}\s+onMoreFormats=\{\(moreFormats\) => setSettings\(\(s\) => \(\{ \.\.\.s, moreFormats \}\)\)\}/);

// The page sends the list while the switch is on and nothing while it is off, then reads the menu's commands again
// (for Settings' shortcuts).
assert.match(editor, /invoke\("set_more_formats", \{ formats: settings\.moreFormats \? moreFormats\.map\(\(\[id, name\]\) => \[id, name\]\) : null \}\)\)\s*\.then\(\(\) => invoke<\[string, string, string, string\]\[\]>\("menu_items"\)\)/);
assert.match(editor, /\}, \[settings\.onlineSearch, settings\.moreFormats\]\);/);
// The commands are there only while it is on, and the palette lists a command only while it is there.
assert.match(editor, /\.\.\.\(settings\.moreFormats \? Object\.fromEntries\(moreFormats\.map\(\(\[id, , , run\]\) => \[id, run\]\)\) : \{\}\),/);
assert.match(editor, /\.\.\.Object\.fromEntries\(moreFormats\.map\(\(\[id, name, icon\]\)[^\n]*=> \[id, \[name, "", icon\]\]\)\),/);
assert.match(editor, /Object\.entries\(MENU_NAMES\)\.filter\(\(\[id\]\) => commands\.current\[id\]/);

// File has More Formats, after Save Templates for ChemDraw, only while the page sent a list. Its items are the page's
// commands, with ids "more_" and the format only, so a format never takes a command the menu has already.
assert.match(main, /struct MoreFormats\(Mutex<Option<Vec<\(String, String\)>>>\);/);
assert.match(main, /\.filter\(\|\(id, _\)\| id\.len\(\) <= 60 && id\.starts_with\("more_"\) && id\.chars\(\)\.all\(\|c\| c\.is_ascii_alphanumeric\(\) \|\| c == '_'\)\)\s*\.take\(40\)/);
assert.match(main, /&save_ctp,\n\s+&more,\n/);
assert.match(main, /if more_list\.is_none\(\) \{\n\s+file\.remove\(&more\)\?;/);
assert.match(main, /section\.replace\("File › More Formats"\.into\(\)\);\n\s+let more_items = more_list\.iter\(\)\.flatten\(\)\.map\(\|\(id, name\)\| item\(id, name, ""\)\)/);
assert.match(main, /\.manage\(MoreFormats::default\(\)\)/);
assert.match(main, /generate_handler!\[[^\]]*\bset_more_formats\b/);
assert.ok(!/\b(?:item|check)\("more_/.test(main), "no command of the menu's own starts with more_");

// Each format is one line of the list: an id the menu takes (once), a name that fits, its icon and what it does.
const list = /const moreFormats: \[string, string, React\.ReactNode, \(\) => void\]\[\] = \[([\s\S]*?)\];\n/.exec(editor)?.[1];
assert.ok(list !== undefined, "the list of formats is where this check reads it");
const lines = list.split("\n").filter((l) => l.trim() && !l.trim().startsWith("//"));
assert.ok(lines.length <= 40, "the menu takes 40 formats at most");
const ids = lines.map((l) => {
  const m = /^\s*\["(more_[a-z0-9_]+)", "([^"]{1,60})", <.+>, \(\) => .+\],$/.exec(l);
  assert.ok(m, `one format to a line, as ["more_xyz", "Name…", <Icon size={18} />, () => …]: ${l.trim()}`);
  assert.ok(m[1].length <= 60, `${m[1]}: the menu takes ids of 60 characters at most`);
  return m[1];
});
assert.equal(new Set(ids).size, ids.length, "each format once");
