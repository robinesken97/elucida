// Run: node src/experiment.check.ts. Fails loudly if the Experiment page (discussion #15) stops being a purpose after
// Poster, stops keeping its details as document annotations through CDXML and .oct, stops giving each new reaction
// its stoichiometry grid, or stops turning markup into rich text.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MAX_START, PURPOSES, outlines, pageSize, purposeStyle, readPurposes, styleFor } from "./docstyle.ts";
import { FIELDS, MAX_MARKUP, detailsLayout, detailsOf, experimentPage, markupCaption, markupRuns, newExperiment, newGrids, templateOf, today, withDetails } from "./experiment.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { parse, serialize } from "./file.ts";
import type { Mol } from "./render.ts";
import type { TextRun } from "./richtext.ts";

// The fifth built-in purpose, after Poster: ACS Document 1996 at 100% on A4 portrait, the page its only outline. A
// user whose Paper is on US Letter gets Experiment on US Letter.
{
  assert.deepEqual(Object.keys(PURPOSES), ["paper", "thesis", "slides", "poster", "experiment"]);
  const s = purposeStyle("experiment");
  assert.deepEqual([PURPOSES.experiment.name, s.preset, s.scale, s.page, s.landscape, s.purpose, s.captionSize], ["Experiment", "ACS Document 1996", 1, "A4", false, "experiment", 10]);
  assert.deepEqual(outlines(s, "experiment"), [["A4", 210, 297]]);
  const letter = styleFor({ purposeStyles: { paper: { ...purposeStyle("paper"), page: "Letter" } }, ownPurposes: [] }, "experiment");
  assert.deepEqual([letter.page, letter.landscape, letter.purpose], ["Letter", false, "experiment"]);
  assert.equal(styleFor({ purposeStyles: {}, ownPurposes: [] }, "experiment").page, "A4");
  assert.equal(readPurposes({ purpose: "experiment" }).purpose, "experiment", "⌘N can start an Experiment");
}

// The details are the document's annotations, by keyword; other annotations stay as they were.
const details = { title: "Boc protection of D-glutamic acid", date: "2026-11-04", notebook: "SE-012-034", project: "Peptides", author: "Sam Ellis", temperature: "25 °C", time: "18 h", pressure: "1 atm", solvent: "Water, 1,4-dioxane" };
{
  const kept = [{ keyword: "GUID", content: "0A1B" }];
  const annotations = withDetails(kept, details)!;
  assert.deepEqual(annotations[0], kept[0]);
  assert.deepEqual(annotations.slice(1).map((a) => a.keyword), FIELDS.map(([, name]) => name));
  assert.deepEqual(detailsOf(annotations), details);
  // An emptied field goes; one changed replaces the old, not added again.
  const less = withDetails(annotations, { ...details, pressure: "", title: "Second try" })!;
  assert.deepEqual([less.filter((a) => a.keyword === "Title").length, detailsOf(less).title, detailsOf(less).pressure], [1, "Second try", undefined]);
  assert.equal(withDetails(undefined, {}), undefined);
  // A value from a hostile file: one line, no control characters, 200 characters at most.
  const odd = detailsOf([{ keyword: "Title", content: `a\u0000b\nc${"x".repeat(9000)}` }]);
  assert.equal(odd.title!.length, 200);
  assert.ok(odd.title!.startsWith("a b c"));
  assert.equal(today(new Date(2026, 10, 4)), "4 November 2026", "dates as BRAND.md writes them");
}

// They go through CDXML (ChemDraw's annotation elements, so ChemDraw keeps them) and Octet's own file, with the
// purpose and the page.
{
  const m: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [], annotations: withDetails(undefined, details) };
  const cdxml = toCdxml(m, purposeStyle("experiment"));
  assert.match(cdxml, /<annotation\s+Keyword="Notebook"\s+Content="SE-012-034"\s*\/>/);
  const back = fromCdxml(cdxml);
  assert.deepEqual(detailsOf(back.mol.annotations), details);
  assert.deepEqual([back.style.purpose, back.style.page], ["experiment", "A4"]);
  assert.deepEqual(detailsOf(parse(serialize({ ...m, style: purposeStyle("experiment") })).annotations), details);
}

// An experiment page: the Experiment purpose or a template made from it, or a colleague's template with details.
assert.equal(experimentPage("experiment", "experiment"), true);
assert.equal(experimentPage("paper", "paper", withDetails(undefined, details)), false);
assert.equal(experimentPage(undefined, "u1abc", withDetails(undefined, details)), true);
assert.equal(experimentPage(undefined, "u1abc"), false);
assert.equal(experimentPage(undefined, undefined, withDetails(undefined, details)), false, "a ChemDraw file with annotations is not one");

// A new page: Date today and the Procedure heading at the left margin, inside the page. A template made from a page
// keeps its details but the date, and its free text; a new page from it gets today's date.
{
  const page = pageSize(purposeStyle("experiment")), start = newExperiment(page, 14.4, undefined, "2026-11-04");
  assert.deepEqual(detailsOf(start.annotations), { date: "2026-11-04" });
  const heading = start.captions![0], k = 72 / 25.4 / 14.4;
  assert.deepEqual([heading.text, heading.bold, heading.align], ["Procedure", true, "left"]);
  assert.ok(Math.abs(heading.x - (15 - 105) * k) < 1e-9 && heading.y < 0 && heading.y > (-page[1] / 2) * k);
  const drawing: Mol = { atoms: [], bonds: [], annotations: withDetails(undefined, details),
    captions: [{ id: 1, text: "Procedure", x: 0, y: 0 }, { id: 2, text: "NaBH4", x: 0, y: 0, on: { arrow: 9, side: "above" } }] };
  const template = parse(serialize(templateOf(drawing)));
  const { date: _, ...undated } = details;
  assert.deepEqual(detailsOf(template.annotations), undated);
  assert.deepEqual(template.captions?.map((c) => c.text), ["Procedure"]);
  const again = newExperiment(page, 14.4, template, "2026-12-01");
  assert.deepEqual(detailsOf(again.annotations), { ...details, date: "2026-12-01" });
  assert.deepEqual(again.captions?.map((c) => c.text), ["Procedure"]);
  // An own template keeps what it starts with, within limits.
  const own = (start: string) => readPurposes({ ownPurposes: [{ id: "u1", name: "My experiment", kind: "experiment", style: purposeStyle("experiment"), start }] }).ownPurposes[0];
  assert.equal(own(serialize(template)).start, serialize(template));
  assert.equal(own(serialize(template)).kind, "experiment");
  assert.equal(own("x".repeat(MAX_START + 1)).start, undefined);
}

// The block: the title in bold and larger, then the details two to a row, inside the page's margins.
{
  const measure = (t: string, size: number) => t.length * size * 0.5;
  const page: [number, number] = [210, 297], k = 72 / 25.4 / 14.4;
  const b = detailsLayout({ ...details, solvent: "w".repeat(200) }, page, 14.4, 10, measure);
  assert.deepEqual([b.texts[0].text, b.texts[0].bold, b.texts[0].size], [details.title, true, 14]);
  assert.deepEqual(b.texts.filter((t) => t.bold).map((t) => t.text), [details.title, ...FIELDS.slice(1).map(([, n]) => n)]);
  const date = b.texts.find((t) => t.text === "Date")!, note = b.texts.find((t) => t.text === "Notebook")!;
  assert.equal(date.y, note.y, "Date and Notebook share a row");
  assert.ok(note.x > date.x);
  const long = b.texts.find((t) => t.text.startsWith("www"))!;
  assert.ok(long.text.endsWith("…") && long.x + (measure(long.text, 10) / 14.4) <= (page[0] / 2 - 15) * k + 1e-9, "a long value is cut to its column");
  assert.ok(b.box[0] >= (-page[0] / 2) * k && b.box[2] <= (page[0] / 2) * k && b.box[3] <= (page[1] / 2) * k && b.box[1] < b.box[3]);
  // With no title, the details start the block.
  assert.equal(detailsLayout({}, page, 14.4, 10, measure).texts[0].text, "Date");
}

// A reaction arrow drawn on the page gets a grid; an arrow already there, a curly arrow or a line does not, and no
// arrow gets two.
{
  const before: Mol = { atoms: [], bonds: [], arrows: [{ id: 1, kind: "reaction", from: [0, 0], to: [2, 0] }] };
  const after: Mol = { ...before, arrows: [...before.arrows!, { id: 2, kind: "reaction", from: [4, 0], to: [6, 0] }, { id: 3, kind: "line", from: [0, 2], to: [2, 2] }, { id: 4, kind: "curved", from: [0, 3], to: [1, 3], bend: 60 }] };
  assert.deepEqual(newGrids(before, after).grids, [{ arrow: 2, typed: {} }]);
  const had = { ...after, grids: [{ arrow: 2, typed: { "r:CH4": { mass: 1 } } }] };
  assert.equal(newGrids(before, had), had);
  assert.equal(newGrids(after, after), after);
  // No more grids than an .oct file reads back (file.ts takes 100), so the drawing still opens once saved.
  const many: Mol = { atoms: [], bonds: [], arrows: Array.from({ length: 120 }, (_, k) => ({ id: k + 1, kind: "reaction" as const, from: [0, k] as [number, number], to: [2, k] as [number, number] })) };
  const gridded = newGrids({ atoms: [], bonds: [] }, many);
  assert.equal(gridded.grids!.length, 100);
  assert.doesNotThrow(() => parse(serialize(gridded)));
  assert.equal(newGrids(many, { ...gridded, arrows: [...gridded.arrows!, { id: 500, kind: "reaction", from: [0, 0], to: [1, 0] }] }).grids!.length, 100);
}

// Markup becomes rich text.
{
  const m = (text: string) => markupRuns([{ text }]);
  assert.deepEqual(m("a *very* **good** yield"), [{ text: "a " }, { text: "very", italic: true }, { text: " " }, { text: "good", bold: true }, { text: " yield" }]);
  assert.deepEqual(m("\\textit{tert}-butyl and \\textbf{1}"), [{ text: "tert", italic: true }, { text: "-butyl and " }, { text: "1", bold: true }]);
  assert.deepEqual(m("$^{13}$C, CDCl$_3$, 10$^2$"), [{ text: "13", script: "super" }, { text: "C, CDCl" }, { text: "3", script: "sub" }, { text: ", 10" }, { text: "2", script: "super" }]);
  assert.deepEqual(m("$J$ = 7.2 Hz, $R_f$ 0.3, $\\mathrm{pH}$ 3"), [{ text: "J", italic: true }, { text: " = 7.2 Hz, " }, { text: "R", italic: true }, { text: "f", italic: true, script: "sub" }, { text: " 0.3, pH 3" }]);
  assert.deepEqual(m("25 $^\\circ$C, \\delta 7.26, 98\\% ee"), [{ text: "25 " }, { text: "°", script: "super" }, { text: "C, δ 7.26, 98% ee" }]);
  assert.deepEqual(m("\\emph{\\textbf{both}}"), [{ text: "both", italic: true, bold: true }]);
  // Left as typed: unpaired marks, stars with spaces, prices, a pair across lines, and escapes.
  for (const text of ["2 * 3 * 4", "a *b", "costs $5 and $10", "*a\nb*", "**", "$$", "\\unknown{x}"]) assert.deepEqual(m(text), [{ text }], text);
  assert.deepEqual(m("\\*not italic\\*"), [{ text: "*not italic*" }]);
  // Relative stereodescriptors keep their stars.
  for (const text of ["rel-(1R*,2S*)-2-methylcyclohexanol", "the (R*,S*)-diol", "(R*)-x and (S*)-y", "a*b*c"]) assert.deepEqual(m(text), [{ text }], text);
  assert.deepEqual(m("*t*BuOK, 1*H*-indole, *p*TsOH"), [{ text: "t", italic: true }, { text: "BuOK, 1" }, { text: "H", italic: true }, { text: "-indole, " }, { text: "p", italic: true }, { text: "TsOH" }]);
  assert.deepEqual(m("*n*-BuLi, *N*,*N*-dimethyl"), [{ text: "n", italic: true }, { text: "-BuLi, " }, { text: "N", italic: true }, { text: "," }, { text: "N", italic: true }, { text: "-dimethyl" }]);
  // Each character keeps its own style, with the markup's over it.
  const styled: TextRun[] = [{ text: "*sp", colour: "#213C99" }, { text: "3*" }];
  assert.deepEqual(markupRuns(styled), [{ text: "sp", colour: "#213C99", italic: true }, { text: "3", italic: true }]);
  // Hostile text: deep nesting and long text stay quick and whole.
  const deep = "\\textit{".repeat(5000) + "x" + "}".repeat(5000);
  assert.ok(markupRuns([{ text: deep }]).map((r) => r.text).join("").includes("x"));
  const long = "*a ".repeat(MAX_MARKUP);
  assert.equal(markupRuns([{ text: long }])[0].text, long);
  const t0 = performance.now();
  markupRuns([{ text: "*a *".repeat(MAX_MARKUP / 4 - 1) }]);
  assert.ok(performance.now() - t0 < 2000, "markup over long text is quick");
  // A caption: its text and runs, or nothing to do.
  assert.deepEqual(markupCaption({ id: 1, text: "H$_2$O", x: 0, y: 0 }), { id: 1, text: "H2O", x: 0, y: 0, runs: [{ text: "H" }, { text: "2", script: "sub" }, { text: "O" }] });
  assert.equal(markupCaption({ id: 1, text: "plain text", x: 0, y: 0 }), undefined);
  assert.equal(markupCaption({ id: 1, text: "*x*", x: 0, y: 0, property: { kind: "name" } as never }), undefined);
}

// In the editor: removing a grid takes off every grid of its reaction, as a reaction of two steps drawn on the page has
// one on each arrow (one shows). Only Select opens the details with a double-click, as other tools draw on the page.
{
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /if \(what === "remove"\) \{ const r = reactionOf\(arrow\)\?\.arrows \?\? \[arrow\]; return set\(\{ \.\.\.doc, grids: doc\.grids\?\.filter\(\(g\) => !r\.includes\(g\.arrow\)\) \}, true\); \}/);
  assert.match(editor, /if \(tool === "select" && t\.atom === undefined && [^\n]*detailsAt\(/);
  // Markup kept as typed (an escape, or Undo of the change) stays as typed when the caption is edited again.
  assert.match(editor, /if \(!\(expPage && markupCaption\(old\)\)\) marked\(m, w\.id\);/);
}
