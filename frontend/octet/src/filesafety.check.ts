// Run: node src/filesafety.check.ts. Fails loudly if Save writes over a file another app changed without asking, or
// if a failure to keep, clear or list the copies for recovery is dropped without a word (issue 2). The Rust side has
// its own tests (main.rs a_file_changed_elsewhere_is_seen, recovery.rs).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const editor = read("Editor.tsx"), main = read("../src-tauri/src/main.rs"), recent = read("../src-tauri/src/recent.rs"), open = read("../src-tauri/src/open.rs");
// A failure names the pattern, not the whole file.
const has = (text: string, pattern: RegExp, what = String(pattern)) => assert.ok(pattern.test(text), what);
const body = (text: string, start: string) => { const i = text.indexOf(start); assert.ok(i >= 0, `found ${start}; update this check`); return text.slice(i, text.indexOf("\n}", i)); };

// Recovery: no call is caught with nothing; a write or a list that fails is logged and said once.
for (const m of editor.matchAll(/"recovery_\w+"[^;]*;/g)) assert.ok(!m[0].includes(".catch(() => {})"), `a recovery failure is dropped: ${m[0]}`);
has(editor, /keep\("recovery_write", [^;]*\.catch\(keepFailed\("[^"]+\."\)\)/);
has(editor, /homeCall<RecoveredEntry\[\]>\("recovery_list"\)\.then\(setRecovered\)\.catch\(keepFailed\("[^"]+\."\)\)/);
const failed = editor.slice(editor.indexOf("const keepFailed = "), editor.indexOf("\n  };", editor.indexOf("const keepFailed = ")));
has(failed, /logError\(/, "recovery failures go to the crash log");
has(failed, /!keeper\.told\) \{ keeper\.told = true; setNotice\(/, "the user hears once");

// Save asks before it writes over a file another app changed, and Save Anyway answers it.
const save = body(editor, "  async function save(");
assert.ok(save.indexOf('invoke<boolean>("file_changed"') > 0 && save.indexOf('invoke<boolean>("file_changed"') < save.indexOf('"save_drawing"'), "Save checks the file before it writes");
has(save, /setDialog\(\{ kind: "changed", done \}\)/);
has(editor, /dialog\?\.kind === "changed" && \(\s*<Dialog title=\{`Another app changed .*`\} action="Save Anyway"/);
has(editor, /onAction=\{\(\) => \{ const d = dialog; setDialog\(undefined\); void save\(false, false, true\)\.then\(d\.done\); \}\}/);
// The lossy question's Replace comes after this question, so it does not ask it again.
has(editor, /label: "Replace", onClick: \(\) => \{ const d = dialog; setDialog\(undefined\); void save\(false, true, true\)/);
// Back in front with no unsaved changes, a changed file opens again, but not over an edit made while Octet looked
// (the click that brought the window to the front can draw).
has(editor, /if \(!TAURI \|\| !fronted \|\| !file\.path \|\| dirty \|\| home \|\| templateEdit\) return;\n\s*const at = doc;\n\s*void invoke<boolean>\("file_changed", \{ path: file\.path \}\)\.then\(\(changed\) => \{ if \(changed && now\.current === at\) revert\(\); \}\)/);

// The Rust side notes each drawing's size and time before it reads it and after it writes it.
has(main, /file_changed,/, "file_changed is a command");
has(body(main, "async fn open_drawing("), /stamp\(&app, &path\);\n\s*let text = read_text_or_cdx/);
has(body(main, "async fn revert_drawing("), /stamp\(&app, &p\);\n\s*read_text_or_cdx/);
has(body(main, "async fn save_drawing("), /write_atomic\(&target, &bytes\)[^\n]*\n\s*stamp\(&app, &target\);/);
has(body(recent, "pub async fn open_recent("), /crate::stamp\(&app, &p\);\n\s*let text = /);
// Export over the drawing's own file is Octet's write too: Save does not then ask about another app.
has(read("../src-tauri/src/export.rs"), /crate::write_atomic\(&path, &bytes\)[^\n]*\n(\s*\/\/[^\n]*\n)?\s*crate::stamp\(&app, &path\);/);
has(open, /if opens \{\n\s*crate::stamp\(&app, &path\);\n\s*\}\n\s*let read = read\(/);

console.log("filesafety: ok");
