// Run: node src/windowmenu.check.ts. The Window menu lists the open drawings (issue 73). The Mac lists the windows
// itself; on Windows and Linux Octet lists them (src-tauri/src/windows.rs, whose cargo test checks each item).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (f: string) => readFileSync(new URL(f, import.meta.url), "utf8");
const main = read("../src-tauri/src/main.rs"), windows = read("../src-tauri/src/windows.rs"), editor = read("Editor.tsx");

// Every platform has the Window menu, and Windows and Linux put the list in it.
assert.match(main, /if !cfg!\(target_os = "macos"\) \{\s*windows::list\(app, &window\)\?;\s*\}/);
assert.match(main, /items\.push\(&window\);\s*items\.push\(&help\);/, "Linux has a Window menu too");
assert.match(main, /window\.set_as_windows_menu_for_nsapp\(\)/, "the Mac's system lists the windows");
// A drawing chosen there comes to the front, and the page does not get it as a command.
assert.match(main, /if let Some\(label\) = id\.strip_prefix\("window_"\) \{\s*tauri::async_runtime::spawn\(windows::window_show\(app\.clone\(\), label\.to_string\(\)\)\);\s*return;\s*\}/);
assert.ok(main.indexOf('strip_prefix("window_")') < main.indexOf('app.emit_to(label, "menu", id)'));
assert.match(windows, /format!\("window_\{\}", i\.label\)/);
// The list follows the drawings as they open, close and are renamed (changed), and the tick follows the window in front.
assert.match(windows, /fn changed\(app: &AppHandle\) \{[^}]*\n\s*menus\(app\);\n\}/);
assert.match(windows, /\*LAST\.lock\(\)\.unwrap\(\) = label\.into\(\);\s*menus\(app\);/);
assert.match(main, /windows::focused\(window\.app_handle\(\), window\.label\(\)\);/);
assert.match(windows, /focused\(&app, &label\);/, "a window chosen from the menu or Home is ticked");
// The lists are made on the main thread, one at a time.
assert.match(windows, /pub fn menus\(app: &AppHandle\) \{[\s\S]*?app\.run_on_main_thread\(move \|\| \{/);
// Each item says what its window's title says.
assert.match(editor, /dirty \? `\$\{name\} \(edited\)` : name/);
assert.match(windows, /if i\.edited \{ format!\("\{\} \(edited\)", i\.name\) \}/);

console.log("window menu: ok");
