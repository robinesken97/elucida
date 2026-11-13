// Run: node src/experiment.check.ts. Fails loudly if the Experiment page (discussion #15) stops being a purpose after
// Poster, stops keeping its details as document annotations through CDXML and .oct, stops giving each new reaction
// its stoichiometry grid, or stops turning markup into rich text.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { MAX_START, PURPOSES, outlines, pageSize, purposeStyle, readPurposes, styleFor } from "./docstyle.ts";
import { FIELDS, MAX_MARKUP, detailsOf, experimentPage, growProcedure, growScheme, ROOM, procedureSpan, inSpan, markupCaption, markupRuns, newExperiment, newGrids, nextNumber, detailRuns, withDetailRuns, titleSizeOf, schemeLanding, schemeSpan, slotText, slotsOf, syncDetails, templateOf, today, withDetails, withHeader, type Sheet } from "./experiment.ts";
import { addCaption, deleteGraphics, updateCaption } from "./edit.ts";
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
const details = { title: "Boc protection of D-glutamic acid", number: "SE-012-034", date: "2026-11-04", notebook: "SE-012-034", project: "Peptides", author: "Sam Ellis", temperature: "25 °C", time: "18 h", pressure: "1 atm", solvent: "Water, 1,4-dioxane" };
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
  const page = pageSize(purposeStyle("experiment")), sheet: Sheet = { page, bond: 14.4, size: 10, measure: (t, size) => t.length * size * 0.5 };
  const whole = newExperiment(sheet, undefined, "2026-11-04"), start = { ...whole, captions: whole.captions!.filter((c) => c.text === "Reaction scheme" || c.text === "Procedure") };
  assert.deepEqual(detailsOf(whole.annotations), { date: "2026-11-04" });
  const heading = start.captions!.find((c) => c.text === "Procedure")!, k = 72 / 25.4 / 14.4;
  assert.deepEqual([heading.text, heading.bold, heading.align], ["Procedure", true, "left"]);
  assert.ok(Math.abs(heading.x - (15 - 105) * k) < 1e-9 && heading.y < 0 && heading.y > (-page[1] / 2) * k);
  // Issue 34: a bold heading for the reaction scheme and the procedure, each with an outlined box under it inside the
  // margins, below the details block. They are ordinary text and boxes, so they edit, move and delete as any other.
  assert.deepEqual(start.captions!.map((c) => [c.text, c.bold]), [["Reaction scheme", true], ["Procedure", true]]);
  assert.equal(start.shapes?.length, 2);
  const ids = [...start.captions!, ...start.shapes!].map((x) => x.id);
  assert.equal(new Set(ids).size, ids.length, "every heading and box has its own id");
  const rule = whole.arrows![0].from[1];
  start.shapes!.forEach((box, j) => {
    const h = start.captions![j], [x0, x1] = [Math.min(box.from[0], box.to[0]), Math.max(box.from[0], box.to[0])], [y0, y1] = [Math.min(box.from[1], box.to[1]), Math.max(box.from[1], box.to[1])];
    assert.equal(box.kind, "box");
    assert.ok(Math.abs(x0 - (15 - 105) * k) < 1e-9 && Math.abs(x1 - (105 - 15) * k) < 1e-9, "the box spans the margins");
    assert.ok(h.y > y1 && h.y - y1 < 4 * k, "the heading sits just above its box");
    assert.ok(y1 < rule && y0 >= (15 - page[1] / 2) * k - 1e-9, "below the details, above the bottom margin");
  });
  assert.ok(Math.max(start.shapes![1].from[1], start.shapes![1].to[1]) < Math.min(start.shapes![0].from[1], start.shapes![0].to[1]), "the boxes do not overlap");
  // Saved and opened again, through .oct and CDXML, they come back as text and boxes.
  const page1 = { atoms: [], bonds: [], ...start } as Mol;
  assert.deepEqual(parse(serialize(page1)).shapes?.map((x) => x.kind), ["box", "box"]);
  const read = fromCdxml(toCdxml(page1, purposeStyle("experiment"))).mol;
  assert.deepEqual(read.captions?.map((c) => [c.text, c.bold]).sort(), [["Procedure", true], ["Reaction scheme", true]]);
  assert.deepEqual(read.shapes?.map((x) => x.kind), ["box", "box"]);
  const drawing: Mol = { atoms: [], bonds: [], annotations: withDetails(undefined, details),
    captions: [{ id: 1, text: "Procedure", x: 0, y: 0 }, { id: 2, text: "NaBH4", x: 0, y: 0, on: { arrow: 9, side: "above" } }] };
  const template = parse(serialize(templateOf(drawing)));
  const { date: _, ...undated } = details;
  assert.deepEqual(detailsOf(template.annotations), undated);
  assert.deepEqual(template.captions?.map((c) => c.text), ["Procedure"]);
  // A template from Octet 1.1.1 has no text for its details: a new page from it gets Octet's, with the template's values.
  const again = newExperiment(sheet, template, "2026-12-01");
  assert.deepEqual(detailsOf(again.annotations), { ...details, date: "2026-12-01" });
  assert.deepEqual(again.captions?.filter((c) => !c.field).map((c) => c.text), ["Procedure", ...FIELDS.slice(1).map(([, n]) => n)]);
  assert.deepEqual(Object.fromEntries(again.captions!.filter((c) => c.field).map((c) => [c.field, c.text])), { ...details, date: "2026-12-01" });
  assert.equal(again.shapes, undefined, "a template with no boxes gives none");
  // A template keeps its boxes and tables, not a TLC plate or a picture.
  const boxed = templateOf({ ...drawing, shapes: [{ id: 5, kind: "box", from: [0, 0], to: [4, 3] }, { id: 6, kind: "tlc", from: [0, 0], to: [2, 3] }] });
  assert.deepEqual(newExperiment(sheet, parse(serialize(boxed))).shapes?.map((x) => x.kind), ["box"]);
  // An own template keeps what it starts with, within limits.
  const own = (start: string) => readPurposes({ ownPurposes: [{ id: "u1", name: "My experiment", kind: "experiment", style: purposeStyle("experiment"), start }] }).ownPurposes[0];
  assert.equal(own(serialize(template)).start, serialize(template));
  assert.equal(own(serialize(template)).kind, "experiment");
  assert.equal(own("x".repeat(MAX_START + 1)).start, undefined);
}

// The details are text at the top of the page (Octet 1.1.2): a bold name for each with its value after it, two to a
// row, the title above them, and a rule under them, all inside the page. Every one is ordinary text.
{
  const measure = (t: string, size: number) => t.length * size * 0.5, page: [number, number] = [210, 297], k = 72 / 25.4 / 14.4, sheet: Sheet = { page, bond: 14.4, size: 10, measure };
  const old: Mol = { atoms: [], bonds: [], annotations: withDetails(undefined, details) }, m = withHeader(old, sheet), caps = m.captions!;
  assert.equal(m.fields, true);
  assert.deepEqual(caps.filter((c) => !c.field).map((c) => [c.text, c.bold]), FIELDS.slice(1).map(([, n]) => [n, true]));
  assert.deepEqual(Object.fromEntries(caps.filter((c) => c.field).map((c) => [c.field, c.text])), details);
  assert.ok(caps.every((c) => c.chemical === false && c.align === "left"), "never read as chemistry: a solvent is not an atom label");
  const title = caps.find((c) => c.field === "title")!, date = caps.find((c) => c.text === "Date")!, num = caps.find((c) => c.text === "Exp. number")!, dateValue = caps.find((c) => c.field === "date")!;
  assert.deepEqual([title.bold, title.size], [true, 14]);
  assert.ok(date.y === num.y && date.x > num.x && dateValue.y === date.y && dateValue.x > date.x, "Exp. number and Date share a row, as the lab book has them, each value after its name");
  assert.ok(title.y > date.y && caps.every((c) => c.x >= (15 - 105) * k - 1e-9 && c.y <= (page[1] / 2 - 15) * k));
  assert.deepEqual([m.arrows!.length, m.arrows![0].kind], [1, "line"]);
  assert.ok(m.arrows![0].from[1] < Math.min(...caps.map((c) => c.y)), "the rule is under them");
  // Saved and opened again through .oct and CDXML, each value is still its detail, and the page still says its details
  // are text. Octet 1.1.1 drew the details itself: its page has no such text, and gets it once.
  for (const back of [parse(serialize(m)), fromCdxml(toCdxml(m, purposeStyle("experiment"))).mol]) {
    assert.equal(back.fields, true);
    assert.deepEqual(Object.fromEntries(back.captions!.filter((c) => c.field).map((c) => [c.field, c.text])), details);
  }
  assert.equal(parse(serialize(old)).fields, undefined);
  assert.equal(parse(serialize(m).replace('"field": "date"', '"field": "<b>"')).captions!.some((c) => c.field === "date"), false, "a field is a short lower-case name, or it is left out");

  // Octet 1.1.1 saves the page with its text and drops what says the text is a detail. Opened again, the page gets no
  // second set of names: each text that says a detail's value is that detail's again.
  const by111: Mol = { ...m, fields: undefined, captions: caps.map(({ field: _, ...c }) => c) }, healed = withHeader(by111, sheet);
  assert.equal(healed.captions!.length, caps.length);
  assert.deepEqual(Object.fromEntries(healed.captions!.filter((c) => c.field).map((c) => [c.field, c.text])), details);
  assert.deepEqual([healed.fields, healed.arrows!.length], [true, 1]);

  // Each detail's place: its box holds its value's start and runs to the next name on the line or the right margin.
  // Values of names that start at the same x start at the same x.
  const slots = slotsOf(m, sheet), slot = (f: string) => slots.find((x) => x.field === f)!;
  assert.deepEqual(slots.map((x) => x.field), FIELDS.map(([f]) => f));
  assert.ok(slots.every((x) => x.caption === caps.find((c) => c.field === x.field)!.id && inSpan(x.box, x.at)));
  assert.ok(slot("number").box[2] < date.x && Math.abs(slot("date").box[2] - (105 - 15) * k) < 1 && slot("date").at[0] === slot("temperature").at[0]);
  // With no value, the place is after the name: a click there starts text that is the detail. The title, with no name
  // of its own, goes above the top name, larger and bold; with a Title name on the page it goes after that, as the rest.
  const bare = withHeader({ atoms: [], bonds: [] }, sheet, true), empty = slotsOf(bare, sheet);
  assert.deepEqual(empty.map((x) => [x.field, x.caption]), FIELDS.map(([f]) => [f, undefined]));
  const at = (f: string) => empty.find((x) => x.field === f)!;
  assert.ok(at("date").at[0] === slot("date").at[0] && at("date").at[1] === slot("date").at[1], "a new page keeps a row for the title");
  assert.ok(Math.abs(at("title").at[1] - at("date").at[1] - 2 * 10 / 14.4) < 1e-9 && at("title").at[0] === bare.captions![0].x);
  assert.deepEqual([slotText(bare, at("title"), sheet).size, slotText(bare, at("title"), sheet).bold, slotText(bare, at("date"), sheet).size], [14, true, undefined]);
  const named = addCaption(bare, { text: "title:", x: -5, y: -3 })[0], own = slotsOf(named, sheet).find((x) => x.field === "title")!;
  assert.ok(own.at[1] === -3 && own.at[0] > -5 && slotText(named, own, sheet).size === undefined, "any text that says a detail's name is its name");
  // A name deleted: its detail has no place. A value moved away keeps a box round its own text.
  const gone = deleteGraphics(bare, new Set([bare.captions!.find((c) => c.text === "Pressure")!.id]));
  assert.equal(slotsOf(gone, sheet).some((x) => x.field === "pressure"), false);
  const moved = updateCaption(m, dateValue.id, { x: 3, y: -9 }), far = slotsOf(moved, sheet).find((x) => x.field === "date")!;
  assert.ok(inSpan(far.box, [3.1, -9]) && !inSpan(far.box, slot("date").at) && far.caption === dateValue.id);

  // Experiment details as rich text (DetailsSheet): each value's runs with its caption's own style folded in, the
  // title bold at its size. Saved, a run's style stays its own: bold taken off one word stays off, a colour and a
  // superscript stay, the title keeps its size, an emptied value goes, and a value with no text on the page goes in
  // its place. Nothing changed gives the same drawing.
  {
    const runs = detailRuns(m);
    assert.deepEqual(runs.title, [{ text: details.title, bold: true, size: titleSizeOf(sheet) }]);
    assert.deepEqual(runs.date, [{ text: details.date }]);
    assert.equal(withDetailRuns(m, runs, sheet), m);
    const styledTitle: TextRun[] = [{ text: "Boc ", bold: true }, { text: "protection", colour: "#B3261E" }, { text: " of D-glutamic acid", bold: true }];
    const saved = withDetailRuns(m, { title: styledTitle, temperature: [{ text: "25 °C" }, { text: "a", script: "super" }], pressure: [] }, sheet);
    const t = saved.captions!.find((c) => c.field === "title")!;
    assert.deepEqual([t.text, t.bold, t.size, t.runs!.map((r) => [r.text, r.bold, r.colour, r.size])], [details.title, undefined, undefined,
      [["Boc ", true, undefined, 14], ["protection", undefined, "#B3261E", 14], [" of D-glutamic acid", true, undefined, 14]]]);
    assert.equal(saved.captions!.find((c) => c.field === "temperature")!.runs![1].script, "super");
    assert.equal(saved.captions!.some((c) => c.field === "pressure"), false, "an emptied value goes");
    const filled = withDetailRuns(bare, { project: [{ text: "  Biaryls  " }] }, sheet), proj = filled.captions!.find((c) => c.field === "project")!;
    assert.deepEqual([proj.text, proj.x, proj.y], ["Biaryls", at("project").at[0], at("project").at[1]], "trimmed, in its place");
    // A page with no place for the detail (an older page with no Exp. number name): the annotation only.
    const noName = deleteGraphics(bare, new Set([bare.captions!.find((c) => c.text === "Exp. number")!.id]));
    const kept = withDetailRuns(noName, { number: [{ text: "SE-1" }] }, sheet);
    assert.deepEqual([detailsOf(kept.annotations).number, kept.captions!.some((c) => c.field === "number")], ["SE-1", false]);
    // Hostile: one line, 200 characters at most, no control characters.
    const long = withDetailRuns(bare, { solvent: [{ text: `a\u0000b${"x".repeat(900)}` }] }, sheet).captions!.find((c) => c.field === "solvent")!;
    assert.ok(long.text.length === 200 && !/[\u0000-\u001f]/.test(long.text));
  }
  // Each new experiment page has the next experiment number: the last run of digits counts up, as wide as it was.
  assert.deepEqual([nextNumber(), nextNumber("SE-A1-009"), nextNumber("042"), nextNumber("SE-A1-001a"), nextNumber("Batch"), nextNumber("99")], ["001", "SE-A1-010", "043", "SE-A1-002a", "Batch-2", "100"]);
  assert.equal(detailsOf(newExperiment(sheet, undefined, "2026-11-12", undefined, "SE-007").annotations).number, "SE-007");

  // The details and their text agree after each edit. A value typed on the page is the detail.
  const typed = addCaption(bare, { ...slotText(bare, at("project"), sheet), text: "Biaryls" })[0], synced = syncDetails(bare, typed, sheet);
  assert.deepEqual(detailsOf(synced.annotations), { project: "Biaryls" });
  assert.equal(syncDetails(synced, synced, sheet), synced, "nothing to do: the same drawing");
  // Changed where it was moved to, it is still the detail; deleted, the detail goes.
  const project = synced.captions!.find((c) => c.field === "project")!.id, away = updateCaption(synced, project, { x: 2, y: -20, text: "Peptides" });
  assert.deepEqual(detailsOf(syncDetails(synced, away, sheet).annotations), { project: "Peptides" });
  assert.deepEqual(detailsOf(syncDetails(synced, deleteGraphics(synced, new Set([project])), sheet).annotations), {});
  // A detail set another way (Experiment details…, a table's conditions) changes its text, adds it in its place, or
  // deletes it. With no place on the page (its name deleted), the detail has no text.
  const set = (from: Mol, d: Parameters<typeof withDetails>[1]) => syncDetails(from, { ...from, annotations: withDetails(from.annotations, d) }, sheet);
  const changed = set(synced, { project: "Dyes", time: "2 h" });
  assert.deepEqual(Object.fromEntries(changed.captions!.filter((c) => c.field).map((c) => [c.field, c.text])), { project: "Dyes", time: "2 h" });
  assert.deepEqual(changed.captions!.find((c) => c.field === "time")!.x, at("time").at[0]);
  assert.equal(set(changed, { time: "2 h" }).captions!.some((c) => c.field === "project"), false);
  const hidden = set(gone, { pressure: "1 atm" });
  assert.deepEqual([detailsOf(hidden.annotations).pressure, hidden.captions!.some((c) => c.field === "pressure")], ["1 atm", false]);

  // A template made from the page keeps the names, the values but the Date, and the rule. A new page from it has
  // today's date after the Date name, and no second set of names. With the Date name deleted, it shows no date.
  const template = parse(serialize(templateOf(changed))), next = newExperiment(sheet, template, "2026-12-01", "Sam");
  assert.deepEqual([template.fields, template.arrows?.length, template.captions!.some((c) => c.field === "date")], [true, 1, false]);
  assert.deepEqual(Object.fromEntries(next.captions!.filter((c) => c.field).map((c) => [c.field, c.text])), { project: "Dyes", time: "2 h", date: "2026-12-01", author: "Sam" });
  assert.equal(next.captions!.filter((c) => c.text === "Date").length, 1);
  // Use for new documents keeps that template as Experiment's start (within the limit an own template has). A new page
  // from it makes the same template again, so Settings shows the page as the default.
  const kept = serialize(templateOf(changed));
  assert.equal(serialize(templateOf({ atoms: [], bonds: [], ...newExperiment(sheet, parse(kept), "2026-12-02") })), kept);
  assert.equal(readPurposes({ experimentStart: kept }).experimentStart, kept);
  assert.equal(readPurposes({ experimentStart: "x".repeat(MAX_START + 1) }).experimentStart, undefined);
  const undated = newExperiment(sheet, parse(serialize(templateOf(deleteGraphics(changed, new Set([changed.captions!.find((c) => c.text === "Date")!.id]))))), "2026-12-01");
  assert.equal(undated.captions!.some((c) => c.field === "date" || c.text === "Date"), false);
}

// A reaction arrow drawn on the page gets a grid; an arrow already there, a curly arrow or a line does not, and no
// arrow gets two.
{
  const before: Mol = { atoms: [], bonds: [], arrows: [{ id: 1, kind: "reaction", from: [0, 0], to: [2, 0] }] };
  const after: Mol = { ...before, arrows: [...before.arrows!, { id: 2, kind: "reaction", from: [4, 0], to: [6, 0] }, { id: 3, kind: "line", from: [0, 2], to: [2, 2] }, { id: 4, kind: "curved", from: [0, 3], to: [1, 3], bend: 60 }] };
  assert.deepEqual(newGrids(before, after).grids, [{ arrow: 2, typed: {}, roles: {} }], "a new table has roles: known solvents start as solvents");
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
  // A formula written plainly has its counts lowered, and a mass number before NMR is raised; F254, 14/23, d1, A1 and
  // a lone S2 or C3 stay as typed.
  const scripts = (text: string) => m(text).map((r) => (r.script === "sub" ? `_${r.text}` : r.script === "super" ? `^${r.text}` : r.text)).join("");
  assert.equal(scripts("(NH4)2S2O8 and CO2, then Na2SO4 and NaHCO3"), "(NH_4)_2S_2O_8 and CO_2, then Na_2SO_4 and NaHCO_3");
  assert.equal(scripts("CDCl3, 1H NMR, 13C NMR; NMe2, Et3N, H2O, O2"), "CDCl_3, ^1H NMR, ^13C NMR; NMe_2, Et_3N, H_2O, O_2");
  assert.equal(scripts("Pd(PPh3)4, [Cu(MeCN)4]PF6"), "Pd(PPh_3)_4, [Cu(MeCN)_4]PF_6");
  for (const text of ["silica F254", "RBF (14/23)", "d1 = 10 s", "SE-A1-001a", "SI p. S2", "the C3 position", "[M+H]+ 223.1077", "1H-indole", "(3H)"]) assert.equal(scripts(text), text, text);
  // Each character keeps its own style, with the markup's over it.
  const styled: TextRun[] = [{ text: "*sp", colour: "#213C99" }, { text: "3*" }];
  assert.deepEqual(markupRuns(styled), [{ text: "sp", colour: "#213C99", italic: true }, { text: "3", italic: true }]);
  // Hostile text: deep nesting and long text stay quick and whole.
  const deep = "\\textit{".repeat(5000) + "x" + "}".repeat(5000);
  assert.ok(markupRuns([{ text: deep }]).map((r) => r.text).join("").includes("x"));
  const long = "*a ".repeat(MAX_MARKUP);
  assert.equal(markupRuns([{ text: long }])[0].text, long);
  // Unpaired marks and braces are the worst case: each looks ahead to the end of its line or text. The look-ahead is
  // worked out once for the whole text, so the work grows in step with the length. Timed against itself in the same
  // run, so a busy machine does not fail it: the whole cap takes about 4 times as long as a quarter of it (linear),
  // never 16 (square). Median of 5, the two sizes in turn.
  const worsts: [string, string][] = [["*a ", "unpaired stars"], ["**a ", "unpaired double stars"], ["$a $", "unpaired dollars"], ["\\textit{a", "unclosed commands"], ["$^{a", "unclosed braces in math"], ["*a\\", "stars before escapes"]];
  for (const [unit, what] of worsts) {
    const worst = (n: number) => [{ text: unit.repeat(Math.floor(n / unit.length) - 1) }];
    const quarter: number[] = [], whole: number[] = [];
    for (let k = 0; k < 5; k++) for (const [n, out] of [[MAX_MARKUP / 4, quarter], [MAX_MARKUP, whole]] as const) {
      const t0 = performance.now();
      markupRuns(worst(n));
      out.push(performance.now() - t0);
    }
    const median = (xs: number[]) => xs.sort((p, q) => p - q)[2], ratio = median(whole) / median(quarter);
    assert.ok(ratio < 8, `markup over long text with ${what}: ${median(whole).toFixed(0)} ms, ${ratio.toFixed(1)} times as long as a quarter of the text (linear)`);
  }
  // A caption: its text and runs, or nothing to do.
  assert.deepEqual(markupCaption({ id: 1, text: "H$_2$O", x: 0, y: 0 }), { id: 1, text: "H2O", x: 0, y: 0, runs: [{ text: "H" }, { text: "2", script: "sub" }, { text: "O" }] });
  assert.equal(markupCaption({ id: 1, text: "plain text", x: 0, y: 0 }), undefined);
  assert.equal(markupCaption({ id: 1, text: "*x*", x: 0, y: 0, property: { kind: "name" } as never }), undefined);
}

// In the editor: removing a grid takes off every grid of its reaction, as a reaction of two steps drawn on the page has
// one on each arrow (one shows).
{
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /if \(what === "remove"\) \{ const r = reactionOf\(arrow\)\?\.arrows \?\? \[arrow\]; return set\(\{ \.\.\.doc, grids: doc\.grids\?\.filter\(\(g\) => !r\.includes\(g\.arrow\)\) \}, true\); \}/);
  // A click on a detail's text or in its box with Select opens Experiment details at that detail (Sam, 12 November
  // 2026), and types it with the Text tool and every other tool but the Eraser; a press in an empty box is that
  // click; the details agree with their text after each edit; a page from Octet 1.1.1 gets the text when it opens; and
  // the boxes are on screen only.
  assert.match(editor, /const slot = tool !== "erase" && !alt && !mods\?\.shift && !mods\?\.alt \? slotAt\(at, t\) : undefined;\n    const detail = slot && DETAILS\.find\(\(\[k\]\) => k === slot\.field\)\?\.\[0\];\n    if \(detail && tool !== "text"\) \{ setSelection\(new Set\(\)\); setPicked\(new Set\(\)\); return setDialog\(\{ kind: "details", focus: detail \}\); \}\n    if \(slot\) return typeField\(slot\);/);
  assert.match(editor, /if \(tool !== "erase" && !e\.shiftKey && !e\.altKey && t\.caption === undefined && slotAt\(p, t\)\) return setDrag\(\{ kind: "click", /);
  assert.match(editor, /next = expPage && mol\.style === doc\.style \? syncDetails\(doc, renumber\(newGrids\(doc, ordered\)\), sheetOf\(style\)\) : ordered;/);
  assert.match(editor, /const mol = withFields\(wholeGroups\(asOpened\(/);
  assert.match(editor, /\{!exporting && slots\.length > 0 && \(\n\s+<g className="fields">/);
  // Markup kept as typed (an escape, or Undo of the change) stays as typed when the caption is edited again.
  assert.match(editor, /if \(!\(expPage && markupCaption\(old\)\)\) marked\(m, w\.id\);/);
}

// A reaction inserted on a new page (Name to Structure, paste, import) lands inside the Reaction scheme box, at its top
// and centred across it, wherever the pointer was. One inserted after it goes under it and its table. The box grows
// to hold a table that runs past its bottom, and the Procedure heading and box move down with it; a table that fits
// leaves the page as it was. A page with no Reaction scheme heading (any other page) gets nothing from these.
{
  const page = pageSize(purposeStyle("experiment")), start = { atoms: [], bonds: [], ...newExperiment({ page, bond: 14.4, size: 10, measure: (t, size) => t.length * size * 0.5 }, undefined, "2026-11-05") } as Mol;
  const box = schemeSpan(start)!, inside = (b: number[]) => b[0] >= box[0] && b[2] <= box[2] && b[1] >= box[1] && b[3] <= box[3];
  assert.ok(box && box[3] > box[1]);
  // A reaction 14 bond lengths wide and 3 high, about to land in the middle of a view scrolled off the page.
  const ink = [43, -31.5, 57, -28.5];
  assert.ok(!inside(ink), "the middle of the view is not in the box");
  const off = schemeLanding(start, ink, [])!, landed = [ink[0] + off[0], ink[1] + off[1], ink[2] + off[0], ink[3] + off[1]];
  assert.ok(inside(landed), "it lands inside the box");
  assert.ok(Math.abs((landed[0] + landed[2]) / 2 - (box[0] + box[2]) / 2) < 1e-9, "centred across the box");
  assert.ok(box[3] - landed[3] > 0 && box[3] - landed[3] <= 1.5, "at the top of the box");
  // Its table, under it: the reagent table runs 40 bond lengths down, past the bottom of the box.
  const table = [landed[0], landed[1] - 40.5, landed[2], landed[1] - 0.5];
  assert.ok(table[1] < box[1], "the table runs past the bottom of the box");
  const procedure = start.captions!.find((c) => c.text === "Procedure")!, lower = start.shapes!.find((x) => x.id !== start.shapes![0].id)!;
  const grown = growScheme(start, table[1]), after = schemeSpan(grown)!;
  assert.ok(after[1] < table[1], "the box holds the table");
  assert.deepEqual([after[0], after[2], after[3]], [box[0], box[2], box[3]], "only the bottom moves");
  const drop = box[1] - after[1], moved = grown.captions!.find((c) => c.id === procedure.id)!, movedBox = grown.shapes!.find((x) => x.id === lower.id)!;
  assert.ok(Math.abs(procedure.y - moved.y - drop) < 1e-9, "the Procedure heading moves down as far");
  // The Procedure box's top moves down as far; its bottom stays while the box keeps 7 bond lengths, so it stays on the
  // first page while it can (and the risk assessment keeps page 2).
  const [lo0, hi0] = [Math.min(lower.from[1], lower.to[1]), Math.max(lower.from[1], lower.to[1])], [lo1, hi1] = [Math.min(movedBox.from[1], movedBox.to[1]), Math.max(movedBox.from[1], movedBox.to[1])];
  assert.ok(Math.abs(hi0 - hi1 - drop) < 1e-9, "its box's top moves down as far");
  assert.ok(Math.abs(lo0 - lo1 - (drop - Math.min(drop, hi0 - lo0 - 7))) < 1e-9, "and its bottom only as far as it must");
  assert.ok(hi1 - lo1 >= Math.min(7, hi0 - lo0) - 1e-9, "the Procedure box keeps room to write");
  assert.equal(grown.captions!.find((c) => c.text === "Reaction scheme")!.y, start.captions!.find((c) => c.text === "Reaction scheme")!.y);
  assert.equal(growScheme(start, box[1] + 5), start, "a table that fits changes nothing");
  // The next reaction goes under the first and its table.
  const next = schemeLanding(grown, ink, [landed, table])!;
  assert.ok(ink[3] + next[1] < table[1], "under the table");
  // The Procedure box keeps ROOM under the text in it: text that reaches its bottom grows it down, and text with room
  // to spare changes nothing.
  const proc = procedureSpan(start)!;
  const tall = growProcedure(start, proc[1] + 1), after2 = procedureSpan(tall)!;
  assert.ok(Math.abs(after2[1] - (proc[1] + 1 - ROOM)) < 1e-9, "the box ends ROOM under the text");
  assert.deepEqual([after2[0], after2[2], after2[3]], [proc[0], proc[2], proc[3]], "only its bottom moves");
  assert.equal(growProcedure(start, proc[1] + ROOM + 1), start, "text with room under it changes nothing");
  assert.deepEqual(schemeSpan(tall), schemeSpan(start), "the Reaction scheme box stays as it is");
  // Any other page: nothing.
  const plain: Mol = { atoms: [], bonds: [], shapes: [{ id: 1, kind: "box", from: [-10, 10], to: [10, -10] }], captions: [{ id: 2, text: "Notes", bold: true, x: -10, y: 11 }] };
  assert.equal(schemeLanding(plain, ink, []), undefined);
  assert.equal(growScheme(plain, -50), plain);
  // The editor puts inserted structures and reactions in the box on an experiment page, and grows it for a table in
  // the same undo step as the edit (amend).
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /const schemeAt = \(frag: Mol, base: Mol, at\?: P\) => \(expPage && !\(at && inSpan\(schemeSpan\(base\), at\)\) \? schemeLanding\(base, /);
  assert.match(editor, /const scheme = schemeAt\(frag, base, at\);/);
  // Name to Structure's preview lands where the insert does: in the box, not after the drawing.
  assert.match(editor, /const ghost = useMemo\(\(\) => shownNamed && shownNamed\.atoms\.length \? render\(moveAtoms\(shownNamed, .*, schemeAt\(shownNamed, doc, namingAt\.current\) \?\? landing\(shownNamed, namingAt\.current\)\)/);
  assert.match(editor, /dispatch\(\{ type: "amend", mol: grown \}\)/);
}

// A new experiment page has its risk assessment on page 2 (Sam, 13 November 2026) unless Settings > Document says no,
// a switch that is on at first. The first time, a notice says so and how to remove it, before the notice about Use for
// new documents. Its substances follow the reagent tables after each edit, in the edit's undo step, with hazards
// from PubChem for new ones when Online search is on. A click with Select picks one part of it and Delete removes that
// part; Remove risk assessment removes all of it. A new page compared with the page (Settings' isDefault) does not use
// up an experiment number, so Settings on an experiment page opens.
{
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), prefs = readFileSync(new URL("settings.ts", import.meta.url), "utf8"), window = readFileSync(new URL("SettingsWindow.tsx", import.meta.url), "utf8");
  assert.match(prefs, /riskNew: true, riskNoted: false/);
  assert.match(prefs, /riskNew: saved\.riskNew !== false,\n\s+riskNoted: saved\.riskNoted === true,/);
  assert.match(window, /d\("document", "For", "Add a risk assessment to new experiment pages", [^\n]*<Switch on=\{p\.drawing\.riskNew\} label="Add a risk assessment to new experiment pages" onChange=\{\(on\) => p\.onDrawing\(\{ riskNew: on \}\)\} \/>\)/);
  assert.match(editor, /return settings\.riskNew \? addRisk\(page, riskPlace\(sheetOf\(style\), 0\), sheetOf\(style\), \[\], true\) : page;/);
  assert.match(editor, /if \(!peek\) setSettings\(\(s\) => \(\{ \.\.\.s, lastNumber: number \}\)\);/);
  assert.match(editor, /serialize\(templateOf\(freshFor\(id, true\)\)\)/);
  assert.match(editor, /const riskFirst = expPage && !home && !settings\.riskNoted && !!riskGroup\(doc\)\?\.risk\.auto;/);
  assert.match(editor, /setNotice\("Octet adds a risk assessment on page 2\. To remove it, select it and choose Remove risk assessment\.", "info", \{ label: "Open Settings", run: \(\) => setSettingsOpen\("document"\) \}\);\n\s+setSettings\(\(s\) => \(\{ \.\.\.s, riskNoted: true \}\)\);/);
  assert.match(editor, /if \(!expPage \|\| home \|\| settings\.experimentNoted \|\| notice \|\| riskFirst\) return;/);
  assert.ok(editor.indexOf("const riskFirst") < editor.indexOf("settings.experimentNoted || notice"), "the risk notice first");
  assert.match(editor, /const next = withRiskCas\(withSubstances\(m, list\.map\(\(\{ inchi: _, \.\.\.x \}\) => x\), s\), offlineCas\(list\), s\), fresh = list\.filter\(\(x\) => !had\.has\(x\.key\)\);\n\s+lastSet\.current = next;\n\s+dispatch\(\{ type: "amend", mol: next \}\);\n\s+if \(TAURI && settings\.onlineSearch && fresh\.length\) void riskOnline\(true, fresh, true\);/);
  assert.match(editor, /const part = !shift && selectKind !== "perspective" && riskLay && its\.some\(\(x\) => riskItems\.has\(x\)\) \? partAt\(riskLay, p\) : undefined;/);
  assert.match(editor, /if \(id === "edit\.delete"\) \{\n\s+if \(riskDelete\(\)\) return;/);
  assert.match(editor, /if \(command === "delete" && riskDelete\(\)\) return;/);
  assert.match(editor, /"risk\.remove": \(\) => \{ const g = riskGroup\(doc\); if \(g\) set\(deleteGraphics\(doc, new Set\(g\.items\)\)\); \},/);
}
