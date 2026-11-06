// Run: node src/experimentlist.check.ts. Fails loudly if Home's Experiments list (discussion #15) stops finding and
// sorting experiment pages, stops exporting them as safe CSV, or the app and the page stop agreeing on what a record
// holds.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { FIELDS, MAX_VALUE, dateKey, experimentRows, experimentsCsv, type ExperimentEntry } from "./experiment.ts";

const source = (f: string) => readFileSync(new URL(f, import.meta.url), "utf8");
const list: ExperimentEntry[] = [
  { path: "/lab/boc.oct", name: "boc", at: 30, found: true, details: { title: "Boc protection", date: "2026-11-01", project: "Peptides", notebook: "SE-012-034" }, yield: 0.913 },
  { path: "/lab/suzuki.oct", name: "suzuki", at: 20, found: true, details: { title: "suzuki coupling", date: "3 November 2026", project: "Biaryls", author: "Sam" }, yield: 0.82 },
  { path: "/lab/old.oct", name: "old prep", at: 50, found: false, details: { notebook: "SE-010-007" } },
  { path: "/lab/grignard.oct", name: "grignard", at: 10, found: true, details: { title: "Grignard, -78 °C", date: "2026-10-22", project: "Biaryls" } },
];
const paths = (rows: ExperimentEntry[]) => rows.map((r) => r.name);

// Sorted by Date, newest first (no date last), or by Title (else the file name), either way round.
{
  assert.deepEqual(paths(experimentRows(list, "", { by: "date", down: true })), ["suzuki", "boc", "grignard", "old prep"]);
  assert.deepEqual(paths(experimentRows(list, "", { by: "date", down: false })), ["old prep", "grignard", "boc", "suzuki"]);
  assert.deepEqual(paths(experimentRows(list, "", { by: "title", down: false })), ["boc", "grignard", "old prep", "suzuki"], "case is ignored");
  assert.equal(experimentRows(list, "", { by: "date", down: true })[0], list[1], "the entries themselves");
  assert.equal(list[0].name, "boc", "the list is left as it was");
  assert.equal(dateKey("4 November 2026"), "2026-11-04");
  assert.equal(dateKey("22 Oct 2026"), "2026-10-22");
  assert.equal(dateKey("2026-11-04"), "2026-11-04");
  assert.equal(dateKey("last Tuesday"), "last Tuesday");
}

// The search finds every word in any detail or the file name, in any case.
{
  const find = (q: string) => paths(experimentRows(list, q, { by: "title", down: false }));
  assert.deepEqual(find("biaryls"), ["grignard", "suzuki"]);
  assert.deepEqual(find("  BIARYLS   sam "), ["suzuki"]);
  assert.deepEqual(find("SE-010"), ["old prep"]);
  assert.deepEqual(find("old"), ["old prep"]);
  assert.deepEqual(find("2026-11"), ["boc"]);
  assert.deepEqual(find("november"), ["suzuki"]);
  assert.deepEqual(find("nothing like it"), []);
}

// CSV: the details in their order, Yield in %, and the file; quotes doubled, and a value a spreadsheet would run as a
// formula made text. A minus with a number stays as it is.
{
  const csv = experimentsCsv(list);
  assert.ok(csv.startsWith("\uFEFF"), "a byte-order mark, so Excel reads °C as UTF-8");
  const lines = csv.slice(1).split("\r\n");
  assert.equal(lines[0], "Title,Date,Notebook,Project,Author,Temperature,Time,Pressure,Solvent,Yield (%),File");
  assert.equal(lines[1], "Boc protection,2026-11-01,SE-012-034,Peptides,,,,,,91.3,/lab/boc.oct");
  assert.equal(lines[3], ",,SE-010-007,,,,,,,,/lab/old.oct", "no yield, no title");
  assert.equal(lines[4], '"Grignard, -78 °C",2026-10-22,,Biaryls,,,,,,,/lab/grignard.oct');
  assert.equal(lines.length, list.length + 2, "a line for each, and the file ends with a line break");
  // The app sends "yield": null for an experiment with no yield; it is an empty cell, not 0.0.
  assert.equal(experimentsCsv(JSON.parse('[{"path":"/a.oct","name":"a","at":0,"found":true,"details":{"title":"T"},"yield":null}]')).split("\r\n")[1], "T,,,,,,,,,,/a.oct");
  const hostile = experimentsCsv([{ path: "/x.oct", name: "x", at: 0, found: true, details: { title: '=HYPERLINK("http://x","y")', notebook: "+1+1", project: "@SUM(A1)", author: "-1+cmd|' /C calc'!A0", temperature: "-78 °C", time: "-2 h", solvent: 'say "hi"' } }]).split("\r\n")[1];
  assert.equal(hostile, `"'=HYPERLINK(""http://x"",""y"")",,'+1+1,'@SUM(A1),'-1+cmd|' /C calc'!A0,-78 °C,-2 h,,"say ""hi""",,/x.oct`);
  assert.equal(experimentsCsv([]), "\uFEFFTitle,Date,Notebook,Project,Author,Temperature,Time,Pressure,Solvent,Yield (%),File\r\n");
}

// The app keeps the same details the page has (src-tauri/src/recent.rs), with the same limit, checks each record, and
// lets Home open a drawing on the list. Export… writes CSV.
{
  const rs = source("../src-tauri/src/recent.rs");
  const keys = /const DETAILS: \[&str; \d+\] = \[([^\]]*)\]/.exec(rs)?.[1].match(/"(\w+)"/g)?.map((k) => k.slice(1, -1));
  assert.deepEqual(keys, FIELDS.map(([k]) => k));
  assert.equal(Number(/const MAX_VALUE: usize = (\d+)/.exec(rs)?.[1]), MAX_VALUE);
  assert.match(rs, /fn experiment_note\(app: AppHandle, path: String, experiment: Option<Experiment>\)[\s\S]*?with_list\(&app, \|list\| list\.iter\(\)\.find\(\|r\| r\.path == path\)/, "only a drawing on the recent list goes in");
  assert.match(rs, /!with_experiments\(&app, \|list\| list\.iter\(\)\.any\(\|e\| e\.path == path\)\)/, "a drawing on the Experiments list opens from Home");
  const main = source("../src-tauri/src/main.rs");
  for (const cmd of ["experiment_note", "experiment_list", "experiment_remove"]) assert.match(main, new RegExp(`recent::${cmd}\\b`), cmd);
  assert.match(main, /\.manage\(recent::Experiments::default\(\)\)/);
  assert.match(source("../src-tauri/src/export.rs"), /\("csv", "CSV", &\["csv"\]\)/);
}

// Each drawing opened or saved tells the list what it is: an experiment page with its details and first yield, or
// none. Home lists them, and Export CSV… exports what the list shows.
{
  const editor = source("Editor.tsx"), home = source("Home.tsx");
  assert.match(editor, /invoke\("experiment_note", \{ path: file\.path, experiment: page \? \{ details, /);
  assert.match(editor, /\}, \[file, loaded\]\);/);
  assert.match(editor, /homeCall<ExperimentEntry\[\]>\("experiment_list"\)\.then\(setExperiments\)/);
  assert.match(editor, /exportFile\(\{ name: "Experiments", format: "csv", csv: experimentsCsv\(list\) \}\)\s*\.then\(\(path\) => \{ if \(path\) saved\(path\); \}/, "Show in Finder, as every export has");
  assert.match(home, /p\.experiments\.length > 0 && <button className="home-open" data-experiments onClick=\{openLab\}>/);
  assert.match(home, /onClick=\{\(\) => p\.onExportExperiments\(rows\)\}/);
}
