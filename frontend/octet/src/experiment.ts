// Experiment pages (discussion #15): a page for one experiment in a lab notebook. Its details (title, date, notebook
// reference and the rest) are the document's annotations, keyword and content pairs, as ChemDraw keeps File >
// Document Annotations: ChemDraw shows and keeps them, and the CDXML and .oct readers already check them as hostile
// input. The page has them as text at its top (withHeader): a name for each and its value, which the user clicks to
// type, moves and deletes as any text (slotsOf, syncDetails). Each reaction drawn on the page gets its stoichiometry
// grid at once (newGrids), and text typed on it turns its markup into rich text (markupRuns).
import { straightArrow, type Annotation, type Caption, type Grid, type Mol, type Shape } from "./render.ts";
import { addArrow, addCaption, deleteGraphics, updateCaption } from "./edit.ts";
import { normalise, plainOf, runsOf, styled, styleOf, type RunStyle, type TextRun } from "./richtext.ts";
import { ESCAPES } from "./escapes.ts";
import { ELEMENTS } from "./metals.ts";

// The details, each kept as an annotation whose keyword is its name here.
export const FIELDS = [
  ["title", "Title"], ["number", "Exp. number"], ["date", "Date"], ["notebook", "Notebook"], ["project", "Project"], ["author", "Author"],
  ["temperature", "Temperature"], ["time", "Time"], ["pressure", "Pressure"], ["solvent", "Solvent"],
] as const;
export type Field = (typeof FIELDS)[number][0];
export type Details = Partial<Record<Field, string>>;
// The document's properties (Settings > Document > Properties), kept as annotations in the same way, so its Title and
// Author are an experiment page's. A PDF export writes them in its document information too.
export const PROPERTIES = [["title", "Title"], ["author", "Author"], ["keywords", "Keywords"]] as const;
export type Properties = Partial<Record<(typeof PROPERTIES)[number][0], string>>;
type Fields = readonly (readonly [string, string])[];
export const MAX_VALUE = 200;
// A value as the page keeps it: one line, no control characters, MAX_VALUE characters at most. A grid's conditions too.
export const oneLine = (v: string) => v.replace(/[\u0000-\u001f\u007f]+/g, " ").trim().slice(0, MAX_VALUE).trim();

// The details in a document's annotations (the first annotation with each keyword). fields: the keywords read
// (PROPERTIES for the document's properties).
export function detailsOf<F extends Fields = typeof FIELDS>(annotations?: Annotation[], fields: F = FIELDS as Fields as F): Partial<Record<F[number][0], string>> {
  const out: Record<string, string> = {};
  for (const [k, name] of fields) {
    const a = annotations?.find((x) => x.keyword === name), v = a && oneLine(a.content);
    if (v) out[k] = v;
  }
  return out as Partial<Record<F[number][0], string>>;
}
// The annotations with these details: every annotation with a detail's keyword is replaced, the others stay first in
// their order. An empty value leaves its keyword out. Undefined when there are none.
export function withDetails<F extends Fields = typeof FIELDS>(annotations: Annotation[] | undefined, details: Partial<Record<F[number][0], string>>, fields: F = FIELDS as Fields as F): Annotation[] | undefined {
  const names = new Set<string>(fields.map(([, name]) => name)), values: Record<string, string | undefined> = details;
  const out = [...(annotations ?? []).filter((a) => !names.has(a.keyword)), ...fields.flatMap(([k, keyword]) => { const v = oneLine(values[k] ?? ""); return v ? [{ keyword, content: v }] : []; })];
  return out.length ? out : undefined;
}
// Today as the Date field takes it: 4 November 2026.
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export const today = (d = new Date()) => `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
// A Date as it sorts: 4 November 2026 (or 4 Nov 2026) as 2026-11-04. Any other text stays as it is.
export function dateKey(date: string): string {
  const m = /^\s*(\d{1,2}) ([A-Za-z]+)\.? (\d{4})\s*$/.exec(date), month = m ? MONTHS.findIndex((n) => n.toLowerCase().startsWith(m[2].toLowerCase()) && m[2].length >= 3) : -1;
  return m && month >= 0 ? `${m[3]}-${String(month + 1).padStart(2, "0")}-${m[1].padStart(2, "0")}` : date;
}

// Whether a drawing is an experiment page: its purpose is Experiment or a template made from it, or it names a
// template this computer does not have (a colleague's) and has experiment details. Title and Author do not count: any
// drawing can have them (PROPERTIES), and a new drawing has an Author.
export const experimentPage = (kind: string | undefined, purpose: string | undefined, annotations?: Annotation[]) =>
  kind === "experiment" || (kind === undefined && !!purpose && Object.keys(detailsOf(annotations)).some((k) => !PROPERTIES.some(([p]) => p === k)));

// A new experiment page: its details from the template (Date today, and the author when the template names none), as
// text at the top of the page, and the template's text and boxes (an own template's, else HEADINGS: each a bold
// heading at the left margin with an outlined box under it, both ordinary text and an ordinary box the user can edit,
// move or delete; issue 34). A template from Octet 1.1.1 has no text for its details and gets Octet's. The reaction's
// table of reagents and products is drawn under the reaction, so the scheme's box has room for both.
export const MARGIN = 15; // mm
// Each heading and how far down the page its box starts and ends, in mm.
export const HEADINGS: [string, number, number][] = [["Reaction scheme", 60, 200], ["Procedure", 212, 282]];
const perMm = (bond: number) => 72 / 25.4 / bond; // drawing units (bond lengths) in a mm
// The page a header is laid out on: its size in mm, its bond length and text size in pt, and a text's width in pt.
export type Sheet = { page: [number, number]; bond: number; size: number; measure: (text: string, size: number, bold: boolean) => number };
// The experiment number after this one: its last run of digits counts up, as wide as it was (SE-A1-009 gives
// SE-A1-010), and a number with no digits gets -2. The first experiment is 001.
export function nextNumber(last?: string): string {
  const v = last && oneLine(last);
  if (!v) return "001";
  const m = /(\d+)(\D*)$/.exec(v);
  if (!m) return `${v}-2`;
  const n = String(Number(m[1]) + 1).padStart(m[1].length, "0");
  return v.slice(0, m.index) + n + m[2];
}
export function newExperiment(s: Sheet, template?: Mol, date = today(), author?: string, number?: string): Pick<Mol, "annotations" | "captions" | "shapes" | "arrows" | "fields"> {
  const k = perMm(s.bond), left = (MARGIN - s.page[0] / 2) * k, right = (s.page[0] / 2 - MARGIN) * k, down = (mm: number) => (s.page[1] / 2 - mm) * k;
  const base: Mol = template ? { atoms: [], bonds: [], captions: template.captions, shapes: template.shapes, arrows: template.arrows, annotations: template.annotations, fields: template.fields } : {
    atoms: [], bonds: [],
    captions: HEADINGS.map(([text, top], j) => ({ id: 2 * j, text, bold: true, align: "left" as const, x: left, y: down(top - 2) })),
    shapes: HEADINGS.map(([, top, bottom], j) => ({ id: 2 * j + 1, kind: "box" as const, from: [left, down(top)] as [number, number], to: [right, down(bottom)] as [number, number] })),
  };
  const had = detailsOf(base.annotations), dated = { ...base, annotations: withDetails(base.annotations, { ...had, date, ...(number ? { number } : {}), ...(author && !had.author ? { author } : {}) }) };
  const { annotations, captions, shapes, arrows, fields } = base.fields ? syncDetails(base, dated, s) : withHeader(dated, s, true);
  return { annotations, ...(captions?.length ? { captions } : {}), ...(shapes?.length ? { shapes } : {}), ...(arrows?.length ? { arrows } : {}), ...(fields ? { fields } : {}) };
}
// The Reaction scheme box: the box (or rounded box) under the Reaction scheme heading, the nearest below it that spans
// the heading's start. As [left, bottom, right, top] in drawing units; undefined with no such heading or box (any
// other page, or a template without them).
const spanOf = (x: Shape): [number, number, number, number] => [Math.min(x.from[0], x.to[0]), Math.min(x.from[1], x.to[1]), Math.max(x.from[0], x.to[0]), Math.max(x.from[1], x.to[1])];
function schemeShape(m: Mol, heading = /^reaction scheme$/i): Shape | undefined {
  const h = (m.captions ?? []).find((c) => !c.under && !c.on && !c.cycle && heading.test(c.text.trim()));
  if (!h) return undefined;
  const near = (m.shapes ?? []).filter((x) => (x.kind === "box" || x.kind === "rounded") && !x.angle).filter((x) => { const b = spanOf(x); return b[3] <= h.y + 1e-6 && b[0] <= h.x + 1e-6 && b[2] > h.x; });
  return near.sort((p, q) => spanOf(q)[3] - spanOf(p)[3])[0];
}
export const schemeSpan = (m: Mol) => { const x = schemeShape(m); return x && spanOf(x); };
// The Procedure box, found as the Reaction scheme box is.
export const procedureSpan = (m: Mol) => { const x = schemeShape(m, /^procedure$/i); return x && spanOf(x); };
export const inSpan = (b: number[] | undefined, p: [number, number]) => !!b && p[0] >= b[0] && p[0] <= b[2] && p[1] >= b[1] && p[1] <= b[3];
// Where a structure or reaction inserted on an experiment page goes (issue 34): inside the Reaction scheme box, a bond
// length (pad) under its top, or under whatever is in the box already (taken: its ink and tables), centred across the
// box (from its left when wider than the box). The offset to move `ink` by; undefined with no box.
export function schemeLanding(m: Mol, ink: number[], taken: number[][], pad = 1): [number, number] | undefined {
  const b = schemeSpan(m);
  if (!b) return undefined;
  const there = taken.filter((t) => t[0] < b[2] && t[2] > b[0] && t[1] < b[3] && t[3] > b[1]);
  const top = Math.min(b[3], ...there.map((t) => t[1])) - pad, w = ink[2] - ink[0];
  const x = w > b[2] - b[0] - 2 * pad ? b[0] + pad - ink[0] : (b[0] + b[2]) / 2 - (ink[0] + ink[2]) / 2;
  return [x, top - ink[3]];
}
// The Reaction scheme box grown down to hold what reaches `bottom` (a reagent table, a scheme), a bond length (pad)
// clear. Free text and boxes under it (the Procedure heading and box) move down as far, so nothing overlaps. The same
// drawing when it fits already, or with no box.
export function growScheme(m: Mol, bottom: number, pad = 1, heading?: RegExp): Mol {
  const s = schemeShape(m, heading), b = s && spanOf(s);
  if (!s || !b) return m;
  const d = b[1] - (bottom - pad);
  if (d <= 1e-6) return m;
  // A risk assessment keeps its place on its own page. The Procedure box under a growing scheme gives up its own
  // height first, down to PROCEDURE_MIN, so it stays on the first page while it can.
  const risk = new Set((m.groups ?? []).flatMap((g) => (g.risk ? g.items : []))), proc = heading ? undefined : schemeShape(m, /^procedure$/i);
  const move = (p: [number, number], by: number): [number, number] => [p[0], p[1] - by];
  const shapes = m.shapes!.map((x) => {
    if (x === s) return { ...x, ...(x.from[1] < x.to[1] ? { from: move(x.from, d) } : { to: move(x.to, d) }) };
    if (risk.has(x.id) || spanOf(x)[3] >= b[1] + 1e-6) return x;
    if (x !== proc) return { ...x, from: move(x.from, d), to: move(x.to, d) };
    const [, lo, , hi] = spanOf(x), keep = d - Math.max(0, Math.min(d, hi - lo - PROCEDURE_MIN));
    return { ...x, ...(x.from[1] > x.to[1] ? { from: move(x.from, d), to: move(x.to, keep) } : { to: move(x.to, d), from: move(x.from, keep) }) };
  });
  const captions = m.captions?.map((c) => (!c.under && !c.on && !c.cycle && c.y < b[1] && !risk.has(c.id) ? { ...c, y: c.y - d } : c));
  return { ...m, shapes, ...(captions ? { captions } : {}) };
}
// The least the Procedure box keeps when the scheme above it grows (bond lengths: twice ROOM, about eight lines).
const PROCEDURE_MIN = 7;

// What an own template made from an experiment page keeps: its details but the date, its free text (the details'
// names and values, headings, a procedure to start from), its plain boxes and tables, and its plain lines (the rule
// under the details). Structures, arrows and text tied to them stay with the drawing.
export const templateOf = (m: Mol): Mol => {
  // A risk assessment stays with the drawing: its substances are this experiment's.
  const { date: _, ...kept } = detailsOf(m.annotations), annotations = withDetails(undefined, kept), risk = new Set((m.groups ?? []).flatMap((g) => (g.risk ? g.items : [])));
  const captions = (m.captions ?? []).filter((c) => free(c) && c.field !== "date" && !risk.has(c.id));
  const shapes = (m.shapes ?? []).filter((x) => (x.kind === "box" || x.kind === "rounded" || x.kind === "table") && !risk.has(x.id));
  const arrows = (m.arrows ?? []).filter((a) => a.kind === "line" && !risk.has(a.id));
  return { atoms: [], bonds: [], ...(captions.length ? { captions } : {}), ...(shapes.length ? { shapes } : {}), ...(arrows.length ? { arrows } : {}), ...(annotations ? { annotations } : {}), ...(m.fields ? { fields: true } : {}) };
};

// The Procedure box grown down to keep ROOM free under the text in it (bond lengths, about four lines of text), so
// there is always space to write on; a long procedure goes on past the first page.
export const ROOM = 3.5;
export const growProcedure = (m: Mol, bottom: number) => growScheme(m, bottom, ROOM, /^procedure$/i);

// The details as text at the top of the page (Octet 1.1.2; Octet 1.1.1 drew them itself, from the annotations): the
// title in bold, larger, then the other details two to a row, each name in bold with its value after it, and a rule
// under them. Every one is ordinary text, and the rule an ordinary line, so the user edits, moves, restyles and deletes
// them as anything else on the page. A value's text is its detail (Caption.field), and a text that says a detail's
// name (Date, Notebook:) is that detail's name: the place after it takes the value (slotsOf).
const TITLE = 1.4, GAP = 0.8; // the title's size, and the space between a name and its value, in text sizes
const titleSize = (s: Sheet) => Math.round(TITLE * s.size * 100) / 100;
export const titleSizeOf = titleSize;
const free = (c: Caption) => !c.under && !c.on && !c.cycle && !c.property && !c.role;
const NAMES = new Map<string, Field>(FIELDS.map(([key, name]) => [name.toLowerCase(), key]));
const nameOf = (c: Caption) => (free(c) && !c.field ? NAMES.get(c.text.trim().replace(/:$/, "").toLowerCase()) : undefined);
const valueOf = (m: Mol, key: Field) => m.captions?.find((c) => c.field === key && free(c));
// A value's text in a place: left-aligned and never read as chemistry (a solvent, THF, is not an atom label).
const valueText = (key: Field, at: [number, number], text: string, s: Sheet, big = key === "title"): Omit<Caption, "id"> =>
  ({ text, x: at[0], y: at[1], align: "left", chemical: false, field: key, ...(big ? { bold: true, size: titleSize(s) } : {}) });
// Where Octet puts each detail (drawing units, y up): the title's row only with title.
function headerLayout(s: Sheet, title: boolean) {
  const k = perMm(s.bond), u = (pt: number) => pt / s.bond, left = (MARGIN - s.page[0] / 2) * k, right = (s.page[0] / 2 - MARGIN) * k, cell = (right - left) / 2;
  const rest = FIELDS.slice(1), name = Math.max(...rest.map(([, n]) => s.measure(n, s.size, true))) + GAP * s.size, at: Partial<Record<Field, { name?: [number, number]; value: [number, number] }>> = {};
  let y = (s.page[1] / 2 - MARGIN) * k;
  if (title) { y -= u(titleSize(s)); at.title = { value: [left, y] }; y -= u(0.5 * s.size); }
  rest.forEach(([key], j) => {
    if (j % 2 === 0) y -= u(1.5 * s.size);
    const x = left + (j % 2) * cell;
    at[key] = { name: [x, y], value: [x + u(name), y] };
  });
  return { at, rule: [left, right, y - u(GAP * s.size)] };
}
// The page with its details as text. A page from Octet 1.1.1 gets them where 1.1.1 drew them (a row for the title only
// when it has one); title: a new page keeps a row for the title.
// A page that has a detail's name on it already was saved by Octet 1.1.1 (or ChemDraw) after 1.1.2 made it: they keep
// the text and drop what says it is a detail. Nothing is added: each text that says a detail's value is that detail's
// again.
export function withHeader(m: Mol, s: Sheet, title = false): Mol {
  const d = detailsOf(m.annotations), lay = headerLayout(s, title || !!d.title);
  if (m.captions?.some(nameOf)) {
    const value = new Map<number, Field>();
    for (const [key] of FIELDS) {
      const c = m.captions.find((x) => free(x) && !x.field && !nameOf(x) && !value.has(x.id) && oneLine(x.text) === d[key]);
      if (c) value.set(c.id, key);
    }
    return { ...m, fields: true, captions: m.captions.map((c) => (value.has(c.id) ? { ...c, field: value.get(c.id) } : c)) };
  }
  let out: Mol = { ...m, fields: true };
  for (const [key, name] of FIELDS) {
    const p = lay.at[key];
    if (p?.name) [out] = addCaption(out, { text: name, bold: true, align: "left", chemical: false, x: p.name[0], y: p.name[1] });
    if (p && d[key]) [out] = addCaption(out, valueText(key, p.value, d[key]!, s));
  }
  return addArrow(out, { kind: "line", from: [lay.rule[0], lay.rule[2]], to: [lay.rule[1], lay.rule[2]] })[0];
}
// Each detail's place on the page: where its value's text starts (at) and the box a click types in ([left, bottom,
// right, top]), with the value's text when it has one (caption). A detail has a place after its name: values of names
// that start at the same x start at the same x, and the box ends before the next name on the line, or at the right
// margin. The title's place, with no name of its own, is above the top name. A value moved away from its name keeps a
// box round its text. A detail with no name and no value has no place. A risk assessment's places (riskassess.ts) are
// slots too, each with the text a click there starts (text).
export type Slot = { field: string; at: [number, number]; box: [number, number, number, number]; caption?: number; text?: Omit<Caption, "id"> };
export function slotsOf(m: Mol, s: Sheet): Slot[] {
  const line = s.size / s.bond, pad = 0.3 * line, right = (s.page[0] / 2 - MARGIN) * perMm(s.bond), names = new Map<Field, Caption>();
  const span = (c: Caption): Slot["box"] => {
    const size = (c.size ?? s.size) / s.bond, lines = c.text.split("\n"), w = Math.max(...lines.map((t) => s.measure(t, c.size ?? s.size, !!c.bold))) / s.bond, x = c.x - (c.align === "right" ? w : c.align === "centre" ? w / 2 : 0);
    return [x, c.y - (lines.length - 0.75) * 1.2 * size, x + w, c.y + 0.75 * size];
  };
  for (const c of m.captions ?? []) { const key = nameOf(c); if (key && !names.has(key)) names.set(key, c); }
  const spans = [...names.values()].map(span), out: Slot[] = [];
  for (const [key] of FIELDS) {
    const n = names.get(key), v = valueOf(m, key);
    let at: Slot["at"] | undefined, box: Slot["box"] | undefined;
    if (n) {
      const b = span(n), x = Math.max(...spans.filter((o) => Math.abs(o[0] - b[0]) < line / 2).map((o) => o[2])) + GAP * line;
      const end = Math.min(Math.max(right, x + 6 * line), ...spans.filter((o) => o[0] > b[2] && Math.abs(o[3] - b[3]) < line).map((o) => o[0] - GAP * line));
      at = [x, n.y]; box = [x - pad, n.y - 0.45 * line, Math.max(end, x + 3 * line), n.y + line];
    } else if (key === "title" && spans.length) {
      const top = [...names.values()].sort((p, q) => q.y - p.y || p.x - q.x)[0], x = span(top)[0], big = titleSize(s) / s.bond;
      at = [x, top.y + 2 * line]; box = [x - pad, at[1] - 0.45 * big, Math.max(right, x + 6 * line), at[1] + big];
    }
    if (v) {
      const b = span(v), there = box && at && v.x >= box[0] - line && v.x <= box[2] && Math.abs(v.y - at[1]) < line;
      box = there ? [Math.min(box![0], b[0] - pad), Math.min(box![1], b[1] - pad), Math.max(box![2], b[2] + pad), Math.max(box![3], b[3] + pad)] : [b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad];
      at = [v.x, v.y];
    }
    if (at && box) out.push({ field: key, at, box, ...(v ? { caption: v.id } : {}) });
  }
  return out;
}
// What a click in a detail's empty place starts: its value's text there (the title's larger and bold, where it has no
// name before it).
export const slotText = (m: Mol, slot: Slot, s: Sheet): Omit<Caption, "id"> =>
  slot.text ?? valueText(slot.field as Field, slot.at, "", s, slot.field === "title" && !(m.captions ?? []).some((c) => nameOf(c) === "title"));
// Each detail's value as rich text for Experiment details: its runs, each with the caption's own style folded in
// (the title's bold and size too), so a style taken off one run stays off. A detail with no text on the page has its
// annotation's text (the title bold).
export function detailRuns(m: Mol): Record<Field, TextRun[]> {
  const d = detailsOf(m.annotations), keys = ["bold", "italic", "underline", "font", "size", "colour"] as const;
  return Object.fromEntries(FIELDS.map(([key]) => {
    const c = valueOf(m, key);
    if (!c) return [key, d[key] ? [{ text: d[key]!, ...(key === "title" ? { bold: true as const } : {}) }] : []];
    const own = Object.fromEntries(keys.filter((k) => c[k] !== undefined).map((k) => [k, c[k]])) as RunStyle;
    return [key, normalise(runsOf(c).map((r) => ({ ...own, ...r })))];
  })) as Record<Field, TextRun[]>;
}
// The page with the values Experiment details saved: a value's text takes its runs (the caption's own style moves
// into them; the title keeps its size where a run has none), an emptied value goes, and a new one goes in its place
// on the page, else into the annotations only (a page with no place for it). syncDetails, run as the edit is set,
// makes the annotations agree. The same drawing when nothing changed.
export function withDetailRuns(m: Mol, values: Partial<Record<Field, TextRun[]>>, s: Sheet): Mol {
  const was = detailRuns(m), plainStyle = { bold: undefined, italic: undefined, underline: undefined, font: undefined, size: undefined, colour: undefined };
  let out = m, details: Details | undefined, slots: Slot[] | undefined;
  for (const [key] of FIELDS) {
    const raw = values[key];
    if (!raw || JSON.stringify(normalise(raw)) === JSON.stringify(was[key])) continue;
    const runs = trimRuns(key === "title" ? raw.map((r) => ({ ...r, size: r.size ?? titleSize(s) })) : raw), text = plainOf(runs), c = valueOf(out, key);
    const rich = { text, runs: styled(runs) ? runs : undefined };
    if (c) { out = text ? updateCaption(out, c.id, { ...plainStyle, ...rich }) : deleteGraphics(out, new Set([c.id])); continue; }
    if (!text) continue;
    const slot = (slots ??= slotsOf(m, s)).find((x) => x.field === key);
    if (slot) [out] = addCaption(out, { ...slotText(m, slot, s), ...plainStyle, ...rich });
    else (details ??= { ...detailsOf(out.annotations) })[key] = text;
  }
  return details ? { ...out, annotations: withDetails(out.annotations, details) } : out;
}
// A value's runs on one line, with no space at either end and MAX_VALUE characters at most.
function trimRuns(runs: TextRun[]): TextRun[] {
  const text = plainOf(runs), start = text.length - text.trimStart().length, end = Math.min(text.trimEnd().length, start + MAX_VALUE);
  const out: TextRun[] = [];
  let at = 0;
  for (const r of runs) {
    const a = Math.max(start, at), b = Math.min(end, at + r.text.length);
    if (b > a) out.push({ ...r, text: r.text.slice(a - at, b - at).replace(/[\u0000-\u001f\u007f]/g, " ") });
    at += r.text.length;
  }
  return normalise(out);
}
// After an edit of an experiment page, its details and their text agree. A value typed, changed or deleted on the page
// sets or removes the document's annotation, which Home's Experiments list, a table's conditions and ChemDraw read. An
// annotation the edit changed (Experiment details…, a table's conditions, the document's properties) changes its text,
// deletes it when the detail is now empty, or adds it in the detail's place when the page has one. The same drawing
// when they agree already.
// ponytail: two texts for one detail (a copy of a value): the first counts. Clear the copy's field if it confuses.
export function syncDetails(before: Mol, after: Mol, s: Sheet): Mol {
  const was = detailsOf(before.annotations), now = detailsOf(after.annotations), details: Details = { ...now };
  let out = after, slots: Slot[] | undefined;
  for (const [key] of FIELDS) {
    const v0 = valueOf(before, key), v = valueOf(after, key), text = v && oneLine(v.text);
    if (text !== (v0 && oneLine(v0.text))) { if (text) details[key] = text; else delete details[key]; continue; }
    if (now[key] === was[key] || now[key] === text) continue;
    if (v) out = now[key] ? updateCaption(out, v.id, { text: now[key]!, runs: undefined }) : deleteGraphics(out, new Set([v.id]));
    else {
      const slot = (slots ??= slotsOf(after, s)).find((x) => x.field === key);
      if (slot) [out] = addCaption(out, { ...slotText(after, slot, s), text: now[key]! });
    }
  }
  const annotations = withDetails(out.annotations, details);
  return JSON.stringify(annotations) === JSON.stringify(out.annotations) ? out : { ...out, annotations };
}

// Each new reaction arrow an edit draws (one whose id was not in the drawing before) gets a stoichiometry grid, as
// Analyse Stoichiometry gives it, unless its reaction has one already. A grid on an arrow of the same reaction shows
// once (the editor draws one grid for each reaction). No more than MAX_GRIDS on the drawing's arrows, as a file holds.
export const MAX_GRIDS = 100; // file.ts
export function newGrids(before: Mol, after: Mol): Mol {
  const had = new Set((before.arrows ?? []).map((a) => a.id)), gridded = new Set((after.grids ?? []).map((g) => g.arrow));
  const live = (after.arrows ?? []).filter((a) => gridded.has(a.id)).length;
  const add: Grid[] = (after.arrows ?? []).filter((a) => straightArrow(a) && !had.has(a.id) && !gridded.has(a.id)).slice(0, Math.max(0, MAX_GRIDS - live)).map((a) => ({ arrow: a.id, typed: {}, roles: {} }));
  return add.length ? { ...after, grids: [...(after.grids ?? []), ...add] } : after;
}

// Markup typed as text, turned into rich text: *italic*, **bold**, LaTeX's \textit{…}, \emph{…}, \textbf{…},
// \underline{…}, \textsuperscript{…}, \textsubscript{…}, and math between dollars: $^{13}$C or $^2$ a superscript,
// $_3$ or $_{2}$ a subscript, letters in italic ($J$, $R_f$) unless in \mathrm{…} or \text{…}, and \alpha, \delta,
// \circ, \pm, \times and the like as their symbols (in text too). \$, \*, \_, \%, \&, \#, \{ and \} are the
// characters themselves. Stars and dollars pair within a line. A star that opens has a letter or digit after it and
// none before it, and one that closes has no space before it and no letter or digit after it, so (1R*,2S*) stays as it
// is; dollars hold no space at either end, so "$5 and $10" stays as it is. Anything
// unpaired stays as it is. Each character keeps its own style, with the markup's over it. Text over MAX_MARKUP
// characters comes back unchanged.
const COMMANDS: Record<string, RunStyle> = {
  textit: { italic: true }, emph: { italic: true }, textbf: { bold: true }, underline: { underline: true }, textsuperscript: { script: "super" }, textsubscript: { script: "sub" },
  mathit: { italic: true }, mathbf: { bold: true }, mathrm: {}, text: {}, textrm: {}, textup: {}, mbox: {},
};
const ROMAN = new Set(["mathrm", "mathbf", "text", "textrm", "textup", "mbox"]);
const has = (o: object, k: string) => Object.prototype.hasOwnProperty.call(o, k);
const SYMBOLS = ESCAPES; // escapes.ts: the names typed anywhere in Octet
const ESCAPED = "$*_%&#{}";
export const MAX_MARKUP = 20_000;
type Ch = { ch: string; s: RunStyle };
export function markupRuns(runs: TextRun[]): TextRun[] {
  const chars: Ch[] = runs.flatMap((r) => Array.from(r.text, (ch) => ({ ch, s: styleOf(r) })));
  if (chars.length > MAX_MARKUP) return runs;
  return normalise(formulaWords(walk(chars, false, false, 0)).map((c) => ({ ...c.s, text: c.ch })));
}

// A formula written plainly in the text, as a procedure has them: its counts go down (CO2, Na2SO4, (NH4)2S2O8, CDCl3,
// NEt3), and a mass number before NMR goes up (1H NMR, 13C NMR). A word is a formula when it is element symbols (D and
// common groups such as Me and Et too) with counts, two symbols at least (H2, O2, N2, Cl2 and the like alone), so F254,
// A1, 14/23 and mL stay as they are. A character already raised or lowered stays as it is.
const GROUPS = new Set(["Me", "Et", "Pr", "Bu", "Ph", "Ac", "Bn", "Ts", "Tf", "Ms", "Cy"]);
const PAIRS = new Set(["H2", "D2", "N2", "O2", "O3", "F2", "Cl2", "Br2", "I2"]);
const NUCLEI = new Set(["H", "D", "B", "C", "N", "O", "F", "Si", "P", "Se", "Sn", "Pt", "Li", "Na", "Al", "Cd", "Hg", "Rh", "W", "Y", "Xe"]);
// Plain text with its formula words' subscripts (Et3N, CH2Cl2) and nothing else of the markup: a substance's name.
export const formulaRuns = (runs: TextRun[]): TextRun[] =>
  normalise(formulaWords(runs.flatMap((r) => Array.from(r.text, (ch) => ({ ch, s: styleOf(r) })))).map((c) => ({ ...c.s, text: c.ch })));
function formulaWords(cs: Ch[]): Ch[] {
  const out = cs.map((c) => ({ ...c })), text = cs.map((c) => c.ch).join("");
  for (const m of text.matchAll(/[A-Za-z0-9()[\]]+/g)) {
    const w = m[0], at = m.index!, next = /^\s*NMR\b/.test(text.slice(at + w.length));
    const free = (i: number) => !cs[at + i].s.script;
    const iso = /^(\d{1,3})([A-Z][a-z]?)$/.exec(w);
    if (iso && next && NUCLEI.has(iso[2])) { for (let i = 0; i < iso[1].length; i++) if (free(i)) out[at + i].s = { ...out[at + i].s, script: "super" }; continue; }
    const parts = formulaParts(w);
    if (!parts) continue;
    for (const i of parts) if (free(i)) out[at + i].s = { ...out[at + i].s, script: "sub" };
  }
  return out;
}
// The places of a formula word's counts; undefined when the word is not a formula.
function formulaParts(w: string): number[] | undefined {
  if (!/\d/.test(w) || !/^[([]*[A-Z]/.test(w)) return undefined;
  let depth = 0, symbols = 0, i = 0;
  const counts: number[] = [];
  while (i < w.length) {
    const c = w[i];
    if (c === "(" || c === "[") { depth++; i++; continue; }
    if (c === ")" || c === "]") {
      if (--depth < 0) return undefined;
      i++;
      while (/\d/.test(w[i] ?? "")) counts.push(i++);
      continue;
    }
    const sym = /^[A-Z][a-z]?/.exec(w.slice(i))?.[0];
    if (!sym || !(ELEMENTS.has(sym) || sym === "D" || GROUPS.has(sym))) return undefined;
    symbols++;
    i += sym.length;
    while (/\d/.test(w[i] ?? "")) counts.push(i++);
  }
  if (depth !== 0 || !counts.length) return undefined;
  return symbols >= 2 || PAIRS.has(w) ? counts : undefined;
}
const over = (cs: Ch[], s: RunStyle) => cs.map((c) => ({ ch: c.ch, s: { ...c.s, ...s } }));
const word = (cs: Ch[], i: number) => /^[A-Za-z]+/.exec(cs.slice(i, i + 40).map((x) => x.ch).join(""))?.[0];
// A scan from place j steps over a backslash and the character after it, so it goes from j to step(j). A scan that
// goes on for more than LOOK places finishes with a table of where a scan from each place stops, worked out once for the
// whole text from its end back, so markup stays quick however many marks are left unpaired. Kept with each text, as
// walk takes slices of it.
const LOOK = 64;
const step = (cs: Ch[], j: number) => j + (cs[j].ch === "\\" ? 2 : 1);
const tables = new WeakMap<Ch[], Map<string, Int32Array>>();
function table(cs: Ch[], key: string, stop: (j: number, after: Int32Array) => number) {
  let m = tables.get(cs);
  if (!m) tables.set(cs, (m = new Map()));
  let at = m.get(key);
  if (!at) {
    m.set(key, (at = new Int32Array(cs.length + 2).fill(-1)));
    for (let j = cs.length - 1; j >= 0; j--) at[j] = stop(j, at);
  }
  return at;
}
// The place of the brace that closes the one at i, or -1. In the table: the first unmatched "}" from each place.
function closing(cs: Ch[], i: number): number {
  let depth = 0, j = i + 1;
  for (let k = 0; j < cs.length; k++, j = step(cs, j)) {
    if (k === LOOK) {
      const braces = table(cs, "}", (q, at) => { const c = cs[q].ch, r = step(cs, q); return c === "}" ? q : c !== "{" ? at[r] : at[r] < 0 ? -1 : at[at[r] + 1]; });
      let at = braces[j];
      for (; at >= 0 && depth > 0; depth--) at = braces[at + 1];
      return at;
    }
    if (cs[j].ch === "{") depth++;
    else if (cs[j].ch === "}" && depth-- === 0) return j;
  }
  return -1;
}
// The place where the mark (*, ** or $) that opens at i closes on the same line, or -1. In the table: the first line
// break or place that could close the mark, from each place.
function pair(cs: Ch[], i: number, mark: string): number {
  const n = mark.length, star = mark[0] === "*", space = (j: number) => !cs[j] || /\s/.test(cs[j].ch);
  const alnum = (j: number) => !!cs[j] && /[\p{L}\p{N}]/u.test(cs[j].ch);
  // A star pair inside one word on both sides (a*b*c) stays as typed; one side is fine (*t*BuOK, 1*H*-indole).
  const inWord = star && alnum(i - 1);
  if (space(i + n) || (star && (cs[i + n].ch === "*" || !alnum(i + n)))) return -1;
  const closes = (j: number) => cs[j].ch === mark[0] && !(n === 2 && cs[j + 1].ch !== mark[1]) && !space(j - 1) && !(inWord && alnum(j + n)) &&
    !(n === 1 && star && (cs[j + 1]?.ch === "*" || cs[j - 1].ch === "*"));
  for (let j = i + n + 1, k = 0; j <= cs.length - n; k++, j = step(cs, j)) {
    if (k === LOOK) {
      const end = table(cs, mark + inWord, (q, at) => (q > cs.length - n ? -1 : cs[q].ch === "\n" || closes(q) ? q : at[step(cs, q)]))[j];
      return end >= 0 && cs[end].ch !== "\n" ? end : -1;
    }
    if (cs[j].ch === "\n") return -1;
    if (closes(j)) return j;
  }
  return -1;
}
// roman: math letters stay upright (\mathrm{…}).
function walk(cs: Ch[], math: boolean, roman: boolean, depth: number): Ch[] {
  if (depth > 16) return cs;
  const out: Ch[] = [];
  for (let i = 0; i < cs.length; i++) {
    const c = cs[i].ch;
    if (c === "\\") {
      const next = cs[i + 1]?.ch, name = word(cs, i + 1);
      if (next !== undefined && ESCAPED.includes(next)) { out.push(cs[i + 1]); i++; continue; }
      if (next === ",") { out.push({ ch: "\u2009", s: cs[i].s }); i++; continue; }
      if (name && has(COMMANDS, name) && cs[i + 1 + name.length]?.ch === "{") {
        const open = i + 1 + name.length, end = closing(cs, open);
        if (end > 0) { out.push(...over(walk(cs.slice(open + 1, end), math, roman || ROMAN.has(name), depth + 1), COMMANDS[name])); i = end; continue; }
      }
      if (name && has(SYMBOLS, name)) {
        out.push({ ch: SYMBOLS[name], s: cs[i].s });
        i += name.length;
        if (cs[i + 1]?.ch === "{" && cs[i + 2]?.ch === "}") i += 2; // \circ{} and \AA{}
        continue;
      }
    }
    if (!math && c === "*") {
      const n = cs[i + 1]?.ch === "*" ? 2 : 1, end = pair(cs, i, "*".repeat(n));
      if (end > 0) { out.push(...over(walk(cs.slice(i + n, end), false, false, depth + 1), n === 2 ? { bold: true } : { italic: true })); i = end + n - 1; continue; }
    }
    if (!math && c === "$" && cs[i + 1]?.ch !== "$") {
      const end = pair(cs, i, "$");
      if (end > 0) { out.push(...walk(cs.slice(i + 1, end), true, false, depth + 1)); i = end; continue; }
    }
    if (math && (c === "^" || c === "_") && i + 1 < cs.length) {
      const script: RunStyle = { script: c === "^" ? "super" : "sub" }, end = cs[i + 1].ch === "{" ? closing(cs, i + 1) : -1;
      if (end > 0) { out.push(...over(walk(cs.slice(i + 2, end), true, roman, depth + 1), script)); i = end; continue; }
      if (cs[i + 1].ch !== "{") {
        // One character, or one symbol (\circ).
        const name = cs[i + 1].ch === "\\" ? word(cs, i + 2) : undefined, one = cs.slice(i + 1, i + 2 + (name && has(SYMBOLS, name) ? name.length : 0));
        out.push(...over(walk(one, true, roman, depth + 1), script));
        i += one.length;
        continue;
      }
    }
    if (math && c === "{") {
      const end = closing(cs, i);
      if (end > 0) { out.push(...walk(cs.slice(i + 1, end), true, roman, depth + 1)); i = end; continue; }
    }
    out.push(math && !roman && /[A-Za-z]/.test(c) ? { ch: c, s: { ...cs[i].s, italic: true } } : cs[i]);
  }
  return out;
}
// A caption with its markup turned into rich text; undefined when it has none (or is a live property text).
export function markupCaption(c: Caption): Caption | undefined {
  if (c.property) return undefined;
  const runs = runsOf(c), next = markupRuns(runs);
  if (plainOf(next) === c.text && JSON.stringify(next) === JSON.stringify(normalise(runs))) return undefined;
  return { ...c, text: plainOf(next), runs: styled(next) ? next : undefined };
}

// Home's Experiments list (src-tauri/src/recent.rs keeps it): each drawing with experiment details, as it was last
// opened or saved, with the yield of its first reaction's first product (a fraction: 0.85 is 85%).
export type ExperimentEntry = { path: string; name: string; at: number; found: boolean; details: Details; yield?: number };
export type ExperimentSort = { by: "date" | "title"; down: boolean };
// The entries with every word of the search in their details or file name, sorted by Date (else by when the drawing
// was last saved) or by Title (else the file name).
export function experimentRows(list: ExperimentEntry[], search: string, sort: ExperimentSort): ExperimentEntry[] {
  const words = search.toLowerCase().split(/\s+/).filter(Boolean);
  const text = (e: ExperimentEntry) => [e.name, ...FIELDS.map(([k]) => e.details[k] ?? "")].join("\n").toLowerCase();
  const key = (e: ExperimentEntry) => (sort.by === "title" ? e.details.title ?? e.name : dateKey(e.details.date ?? ""));
  const order = (a: ExperimentEntry, b: ExperimentEntry) => key(a).localeCompare(key(b), "en-GB", { numeric: true, sensitivity: "base" }) || a.at - b.at;
  return list.filter((e) => words.every((w) => text(e).includes(w))).sort((a, b) => (sort.down ? order(b, a) : order(a, b)));
}
// A value a spreadsheet would run as a formula, with an apostrophe in front; a minus with a number ("-78 °C") stays as
// it is. For text from files anyone can make, pasted or saved into a spreadsheet (the CSV below, Copy table).
export const sheetSafe = (v: string) => (/^[=+@\t\r]/.test(v) || (v.startsWith("-") && !/^-[\d.]+[\s°%A-Za-zµ]*$/.test(v)) ? `'${v}` : v);
// The list as CSV: a row of names, then a row for each experiment (its details, Yield in %, and the file), each value
// sheetSafe.
export function experimentsCsv(list: ExperimentEntry[]): string {
  const cell = (v: string) => {
    const s = sheetSafe(v);
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const rows = [[...FIELDS.map(([, name]) => name), "Yield (%)", "File"], ...list.map((e) => [...FIELDS.map(([k]) => e.details[k] ?? ""), e.yield == null ? "" : (e.yield * 100).toFixed(1), e.path])];
  // A byte-order mark, so Excel reads it as UTF-8 (°C, µL, accents).
  return "\uFEFF" + rows.map((r) => r.map(cell).join(",")).join("\r\n") + "\r\n";
}
