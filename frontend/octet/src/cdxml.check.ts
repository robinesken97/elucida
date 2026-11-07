// Run: node src/cdxml.check.ts. Fails loudly if the CDXML writer or reader breaks, loses part of a drawing, or
// accepts a bad file.
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { DAMAGED, NOT_CDXML, TOO_BIG, arialGlyph, fmt, fmtAngle, fmtColour, fmtSize, fromCdxml, parseXml, toCdxml, type Xml } from "./cdxml.ts";
import { cdxToXml, xmlToCdx } from "./cdx.ts";
import { readCdx, readOct, writeCdx, writeOct } from "./oct.ts";
import { DEFAULT_STYLE, PRESETS, readStyle, withScale, type DocStyle } from "./docstyle.ts";
import { parse, serialize } from "./file.ts";
import { addCaption, contractLabel, deleteAtoms, deleteChosen, deleteGraphics, duplicateSelection, expandLabel, extractSelection, fitSizes, insertMol, setLabel } from "./edit.ts";
import { HIGHLIGHT, bendPoint, ellipseArrow, fitArrows, headOfLength, headsOf, placeCaptions, placedAt, render, takesHeads, shapesHeads, tlcLayout, type Arrow, type Atom, type Bond, type Caption, type Ink, type Mol, type Placed, type Shape } from "./render.ts";
import { layoutCycles, migrateCycles } from "./cycle.ts";
import { analyse, fromJcamp, measuredText, type Measured } from "./measured.ts";

// Numbers as ChemDraw writes them (spec 1.2).
assert.deepEqual([fmt(30), fmt(14.4), fmt(0.6), fmt(-0.001), fmt(523.2756), fmt(2)], ["30", "14.40", "0.60", "0", "523.28", "2"]);
assert.deepEqual([fmtColour(0), fmtColour(1), fmtColour(0.6), fmtColour(0.63529)], ["0", "1", "0.6000", "0.6353"]);
assert.deepEqual([fmtAngle(-120), fmtAngle(44.63), fmtAngle(-0.01), fmtAngle(270)], ["-120", "44.6", "0", "270"]);
assert.deepEqual([fmtSize(7.5), fmtSize(10), fmtSize(9.65)], ["7.5", "10", "9.65"]);
console.log("cdxml.check: numbers ok");

// A drawing with every kind of object Octet has (coordinates in bond lengths, y up).
const A = (label: string, x: number, y: number, more: Partial<Atom> = {}): Atom => ({ label, location: [x, y, 0], ...more });
const atoms: Atom[] = [
  A("N", 0, 0, { charge: 1 }), A("C", 0.866, 0.5), A("C", 1.732, 0, { charge: -1 }), A("O", 2.598, 0.5, { radical: 1, pairs: 2, colour: "#B42323", halo: "#DCEFE6" }),
  A("O", 3.464, 0, { text: "OMe" }), A("C", 0.866, 1.5, { charge: 1, circled: true }), A("C", 0, -1, { partial: "+", hmark: "dot", map: 1, enhanced: "&1", cip: true }),
  A("C", -0.866, -1.5, { attach: true }), A("C", 0.866, -1.5, { bead: true }),
  // A second structure, the reaction's product.
  A("C", 8, 0, { map: 1, enhanced: "abs", cip: true }), A("C", 8.866, 0.5, { shade: true }), A("Cl", 9.732, 0), A("C", 8, -1, { text: "Ph" }), A("D", 8.866, -1.5),
  A("C", 7.134, 0.5, { text: "R1" }), A("C", 8.866, 1.5, { text: "CO2Et", hmark: "dash", enhanced: "or2" }),
  // A ring for the catalytic cycle and the bond styles.
  A("C", 20, 1), A("C", 20.866, 0.5), A("C", 20.866, -0.5), A("C", 20, -1), A("C", 19.134, -0.5), A("C", 19.134, 0.5),
  // Lone atoms: water, methane and an amide anion.
  A("O", 0, -8), A("C", 3, -8), A("N", 6, -8, { charge: -1 }),
];
atoms[10].location[2] = 0.5;
const b = (i: number, j: number, more: Partial<Bond> = {}): Bond => ({ type: 1, atoms: [i, j], ...more });
const bonds: Bond[] = [
  b(0, 1), b(1, 2, { type: 2, position: "left" }), b(2, 3, { stereo: 1 }), b(3, 4), b(1, 5, { colour: "#213C99" }), b(0, 6, { stereo: 6 }), b(6, 7, { display: "wavy" }), b(6, 8, { display: "bold" }),
  b(9, 10, { type: 2, display: "bold" }), b(10, 11, { display: "dashed" }), b(9, 12, { display: "hashed" }), b(12, 13), b(9, 14, { display: "dative" }), b(10, 15, { type: 2, display: "either" }),
  b(16, 17, { display: "hollow" }), b(17, 18, { type: 3 }), b(18, 19, { type: 2, position: "right" }), b(19, 20, { type: 2, position: "centre", display: "dashed" }), b(20, 21, { ignoreWarnings: true }), b(21, 16, { type: 2, colour: "#22775B" }),
];
const captions: Caption[] = [
  { id: 1, text: "Plain caption", x: 0, y: 4 },
  { id: 2, text: "Line one\nLine two", x: -2, y: 6, bold: true, italic: true, underline: true, size: 12, colour: "#213C99", font: "Times New Roman", align: "left", lineHeight: 18 },
  {
    id: 3, text: "K2CO3, H2O (aq)+", x: 4, y: 5, runs: [{ text: "K" }, { text: "2", script: "sub" }, { text: "CO" }, { text: "3", script: "sub" }, { text: ", " }, { text: "H", bold: true },
      { text: "2", script: "sub", bold: true }, { text: "O (aq)", italic: true, colour: "#B42323", font: "Georgia", size: 8 }, { text: "+", script: "super" }],
  },
  { id: 4, text: "1", x: 0, y: 0, bold: true, under: [9, 10, 11] },
  { id: 5, text: "hν", x: 0, y: 0, on: { arrow: 101, side: "above" } },
  { id: 6, text: "DMF, 80 °C\n12 h", x: 0, y: 0, on: { arrow: 101, side: "below" }, lineHeight: "variable" },
  { id: 7, text: "ArB(OH)2", x: 23, y: 3, cycle: { cycle: 300, step: 0, side: "in" } },
  { id: 8, text: `a < b & "c" 'd' > e`, x: 2, y: -6, align: "right" },
  { id: 10, text: "Turned text", x: 6, y: -6, angle: 30, align: "left" }, // CD-19
  { id: 9, text: "A caption with a width, justified", x: 10, y: -8, align: "justify", width: 4 },
];
const arrow = (id: number, kind: Arrow["kind"], from: [number, number], to: [number, number], more: Partial<Arrow> = {}): Arrow => ({ id, kind, from, to, ...more });
const arrows: Arrow[] = [
  arrow(101, "reaction", [4.5, 0], [6.5, 0]), arrow(102, "equilibrium", [0, -4], [3, -4]), arrow(103, "resonance", [4, -4], [7, -4]), arrow(104, "retro", [8, -4], [11, -4]),
  arrow(105, "nogo", [12, -4], [15, -4]), arrow(106, "curved", [0, -12], [2, -12], { bend: 0.3 }), arrow(107, "fishhook", [3, -12], [5, -12], { bend: -0.4 }),
  arrow(108, "fishhook", [6, -12], [8, -12], { bend: 0.25, end: "right" }), arrow(109, "double", [9, -12], [11, -12], { bend: 0.5, colour: "#8B4E18" }),
  arrow(110, "line", [12, -12], [14, -11], { start: "full", end: "left", style: "dashed", head: "hollow", colour: "#3F6BFF" }), arrow(111, "arc", [15, -12], [17, -12], { bend: -0.2, style: "wavy" }),
  arrow(112, "orbital", [0, -16], [0.8, -16], { orbital: { shape: "p", phase: "filled" } }), arrow(113, "orbital", [2, -16], [2.8, -16], { orbital: { shape: "hybrid", phase: "phased" } }),
  arrow(114, "orbital", [4, -16], [4, -15.2], { orbital: { shape: "dz2", phase: "plain" } }), arrow(115, "orbital", [6, -16], [6.8, -16], { orbital: { shape: "s", phase: "shaded" } }),
  arrow(116, "orbital", [8, -16], [8.8, -16.4], { orbital: { shape: "d", phase: "filled" }, colour: "#B42323" }), arrow(117, "orbital", [10, -16], [10.8, -16], { orbital: { shape: "oval", phase: "plain" } }),
  arrow(118, "cut", [12, -16], [12, -14]),
  arrow(119, "curve", [0, -20], [3, -20], { curve: { points: [{ at: [0, -20], c2: [1, -19] }, { at: [2, -21], c1: [1.5, -21.5], c2: [2.5, -20.5] }, { at: [3, -20] }] }, end: "full", start: "left", style: "bold" }),
  arrow(120, "curve", [4, -20], [4.5, -19], { curve: { points: [{ at: [4, -20] }, { at: [5, -20] }, { at: [4.5, -19] }], closed: true }, fill: "solid", colour: "#22775B" }),
  arrow(121, "curve", [6, -20], [6.5, -19], { curve: { points: [{ at: [6, -20], c1: [5.8, -20.5], c2: [6.2, -19.5] }, { at: [7, -20] }, { at: [6.5, -19] }], closed: true }, fill: "shaded", style: "dashed" }),
  arrow(122, "curve", [8, -20], [8.5, -19], { curve: { points: [{ at: [8, -20] }, { at: [9, -20] }, { at: [8.5, -19] }], closed: true }, fill: "faded", style: "doubled" }),
  arrow(123, "curve", [10, -20], [11, -20], { curve: { points: [{ at: [10, -20] }, { at: [11, -20] }] }, style: "wavy", end: "full", head: "angled" }),
  arrow(124, "reaction", [12, -20], [15, -20], { style: "bold" }), arrow(125, "curved", [16, -20], [18, -20]), arrow(126, "reaction", [19, -20], [21, -20], { start: "full", end: "none" }),
  // ChemDraw's sizes and kinds (CD-14, CD-15): a large head, an unbalanced medium equilibrium, the hashed no-go, a dipole,
  // block arrows (medium and shaded; faded), a straight arrow given a point and bent (CD-16), and an elliptical arc.
  arrow(127, "reaction", [0, -24], [3, -24], { headSize: headOfLength(22.5) }), arrow(128, "equilibrium", [4, -24], [7, -24], { ratio: 3, headSize: headOfLength(15) }),
  arrow(129, "hash", [8, -24], [11, -24]), arrow(130, "dipole", [12, -24], [15, -24], { colour: "#1D49A7" }),
  arrow(131, "block", [16, -24], [19, -24], { headSize: headOfLength(6, true), fill: "shaded" }), arrow(132, "block", [20, -24], [23, -24], { fill: "faded", shaft: 8 }),
  arrow(133, "reaction", [24, -24], [27, -24], { point: true, bend: 0.25 }), { ...ellipseArrow([28, -24], [28.6, -22.8], true), id: 134 } as Arrow,
  arrow(135, "orbital", [30, -24], [30.8, -24], { orbital: { shape: "p", phase: "plain" }, style: "dashed" }),
  arrow(136, "orbital", [32, -24], [32.8, -24], { orbital: { shape: "s", phase: "plain" }, style: "bold" }),
  arrow(137, "reaction", [22, -20], [25, -20], { width: 1.5 }), arrow(138, "curve", [26, -20], [27, -20], { curve: { points: [{ at: [26, -20] }, { at: [27, -20] }] }, width: 0.3 }),
  // A Mass Spec Analysis line with corners: a curve of straight runs, kept as a fragmentation line.
  arrow(139, "cut", [14, -16], [17, -16], { curve: { points: [{ at: [14, -16] }, { at: [15, -14] }, { at: [16, -14] }, { at: [17, -16] }] } }),
];
const shapes: Shape[] = [
  { id: 201, kind: "highlight", from: [-1, -1], to: [3.5, 1.5] },
  { id: 202, kind: "box", from: [30, 0], to: [32, 2], dashed: true },
  { id: 203, kind: "rounded", from: [33, 2], to: [36, 0], fill: "shaded", shadow: true, shade: { depth: 0.2, blur: 0.1, opacity: 0.5 } },
  { id: 204, kind: "oval", from: [37, 0], to: [39, 2], fill: "solid", colour: "#213C99" },
  { id: 205, kind: "oval", from: [40, 0], to: [43, 1.5], shadow: true },
  { id: 206, kind: "brackets", from: [30, -6], to: [33, -3], mark: "‡", dashed: true, colour: "#B42323" },
  { id: 207, kind: "parens", from: [34, -6], to: [36, -3], side: "left" },
  { id: 208, kind: "braces", from: [37, -6], to: [39.5, -3], side: "right", mark: "n" },
  {
    id: 209, kind: "tlc", from: [30, -16], to: [34, -10], colour: "#3F6BFF", tlc: {
      lanes: 3, rf: true, origin: 0.2, front: 0.15, hide: ["front"],
      spots: [{ lane: 2, rf: 0.7, colour: "#B42323" }, { lane: 0, rf: 0.3, style: "hollow", w: 0.3, h: 0.2 }, { lane: 1, rf: 0.5, style: "shaded", tail: 0.4, showRf: true }, { lane: 0, rf: 0.9 }],
    },
  },
  { id: 210, kind: "tlc", from: [35, -16], to: [37, -10], tlc: { lanes: 1, spots: [{ lane: 0, rf: 0.5 }] } },
  { id: 211, kind: "table", from: [40, -16], to: [46, -12], dashed: true, colour: "#213C99", table: { cells: [["Entry", "Yield"], ["1", "72%"], ["2", "n.d."]], lines: ["top", "header", "bottom", "cols"], align: ["left", "right"], widths: [2.5, 3], heights: [1, 1.2, 1], weight: 0.8 } },
  { id: 212, kind: "highlight", from: [7, -2], to: [10, 2], colour: "#DCEFE6" },
  { id: 213, kind: "box", from: [40, 3], to: [42, 5], fill: "solid", colour: "#FFFFFF" },
  // CD-18: turned, bold and faded shapes, a filled one, and turned brackets.
  { id: 220, kind: "box", from: [44, 3], to: [47, 5], angle: 30, boldLine: true },
  { id: 221, kind: "oval", from: [48, 3], to: [51, 5], fill: "faded", angle: -60 },
  { id: 222, kind: "brackets", from: [44, -11], to: [47, -8], angle: 90, mark: "n" },
  { id: 223, kind: "parens", from: [48, -11], to: [50, -8], side: "right", angle: 45 },
  { id: 224, kind: "rounded", from: [52, 3], to: [54, 5], fill: "solid", colour: "#DCE4F5" },
  // Turned shapes and line widths (UI-7, CD-3, UI-42): a box, an oval, a pair of brackets and one bracket alone.
  { id: 214, kind: "box", from: [44, 0], to: [47, 2], angle: 30, width: 1.2 },
  { id: 215, kind: "oval", from: [48, 0], to: [51, 2], angle: -45, dashed: true },
  { id: 216, kind: "brackets", from: [44, -6], to: [47, -3], angle: 90, ignoreWarnings: true },
  { id: 217, kind: "parens", from: [48, -6], to: [49, -3], side: "left", angle: 30, width: 2 },
  { id: 218, kind: "tlc", from: [52, -16], to: [54, -10], width: 0.8, tlc: { lanes: 1, spots: [] }, size: 9, italic: true },
  { id: 219, kind: "table", from: [56, -16], to: [62, -12], table: { cells: [["Entry", "Yield"], ["1", "72%"]] }, font: "Georgia", size: 12, bold: true, underline: true },
];
const drawing: Mol = {
  atoms, bonds, captions, arrows, shapes,
  cycles: [{ id: 300, centre: [20, 0], radius: 3, clockwise: false, nodes: [[16, 17], [18], [19, 20]], colour: "#8B4E18", width: 1.4 }],
  groups: [{ id: 400, atoms: [9, 10, 11, 12, 13, 14, 15], items: [4, 5, 106] }, { id: 401, atoms: [], items: [202, 203], integral: true }],
};

// What a drawing means, written the same way whatever form it was set in: corners as low and high, heads and
// spot sizes that equal the defaults left unset, explicit black as the default ink, centred as unset, groups by id.
function canon(m: Mol): Mol {
  m = migrateCycles(m);
  const ink = (c?: string) => (c && c.toUpperCase() !== "#000000" ? c.toUpperCase() : undefined);
  const strip = <T extends object>(o: T): T => JSON.parse(JSON.stringify(o));
  return strip({
    atoms: m.atoms.map((a) => ({ ...a, colour: ink(a.colour), halo: ink(a.halo) })),
    bonds: m.bonds.map((x) => ({ ...x, colour: ink(x.colour) })),
    captions: [...(m.captions ?? [])].sort((p, q) => p.id - q.id).map((c) => ({ ...c, align: c.align === "centre" ? undefined : c.align, colour: ink(c.colour) })),
    arrows: [...(m.arrows ?? [])].sort((p, q) => p.id - q.id).map((a) => {
      const own = headsOf({ kind: a.kind, bend: a.bend }), heads = takesHeads(a);
      return { ...a, colour: ink(a.colour), start: heads && a.start !== own.start ? a.start : undefined, end: heads && a.end !== own.end ? a.end : undefined, head: shapesHeads(a) && a.head !== "solid" ? a.head : undefined };
    }),
    shapes: (m.shapes ?? []).map((s) => {
      const t = s.tlc && tlcLayout(s);
      return {
        ...s, from: [Math.min(s.from[0], s.to[0]), Math.min(s.from[1], s.to[1])], to: [Math.max(s.from[0], s.to[0]), Math.max(s.from[1], s.to[1])],
        colour: s.kind === "highlight" && s.colour === HIGHLIGHT ? undefined : ink(s.colour),
        tlc: s.tlc && { ...s.tlc, hide: s.tlc.hide && [...s.tlc.hide].sort(), spots: s.tlc.spots.map((x) => ({ ...x, w: x.w === t!.size({ lane: x.lane, rf: x.rf }).rx ? undefined : x.w })) },
      };
    }),
    cycles: m.cycles ?? [], groups: [...(m.groups ?? [])].sort((p, q) => p.id - q.id).map((g) => ({ ...g, atoms: [...g.atoms].sort((p, q) => p - q), items: [...g.items].sort((p, q) => p - q) })),
  });
}
// Paths where two drawings differ; numbers agree to 0.0015 bond lengths (CDXML holds 0.01 pt).
function differences(a: unknown, b: unknown, path = "", out: string[] = []): string[] {
  if (typeof a === "number" && typeof b === "number") { if (Math.abs(a - b) > 1.5e-3) out.push(`${path}: ${a} vs ${b}`); }
  else if (Array.isArray(a) && Array.isArray(b) && a.length === b.length) a.forEach((x, k) => differences(x, b[k], `${path}[${k}]`, out));
  else if (a && b && typeof a === "object" && typeof b === "object" && !Array.isArray(a) && !Array.isArray(b)) {
    for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) differences((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k], `${path}.${k}`, out);
  } else if (JSON.stringify(a) !== JSON.stringify(b)) out.push(`${path}: ${JSON.stringify(a)} vs ${JSON.stringify(b)}`);
  return out;
}
const same = (a: Mol, b: Mol, what: string) => { const d = differences(canon(a), canon(b)); assert.equal(d.length, 0, `${what}:\n${d.slice(0, 20).join("\n")}`); };

// Every object kind survives a write and a read, the result passes Octet's own file checks, and once saved a
// drawing saves to the same file every time (coordinates settle on CDXML's 0.01 pt grid and stay there).
const style: DocStyle = readStyle({ ...DEFAULT_STYLE, ...PRESETS.RSC, page: "Letter", landscape: true, edges: false, grid: 5, background: "dark", colour: "#0F172A" });
const text = toCdxml(drawing, style, { name: "check.cdxml" });
const back = fromCdxml(text);
same(drawing, back.mol, "round trip");
// A cycle's steps, side arrows (a structure's by its atoms), scale and order.
{
  const rich: Mol = { ...drawing, cycles: [{ ...drawing.cycles![0], at: [1, 3, 5], scale: 1.5, order: 2, steps: [{ kind: "equilibrium", ratio: 3 }, null, { lead: 4, hidden: true }],
    branches: [{ id: 4, step: 1, meet: 0.3, in: { atoms: [9, 10] }, out: { along: 2, reach: -1 }, heads: ["left", "full"], colour: "#B42323" }] }] };
  const y = fromCdxml(toCdxml(rich, DEFAULT_STYLE)).mol.cycles![0];
  assert.deepEqual([y.scale, y.order, y.steps, y.branches?.find((b) => b.id === 4)], [1.5, 2, rich.cycles![0].steps, rich.cycles![0].branches![0]]);
}
// The reagent's text saved with no branch (as Octet 1.0.29 did) reads back as a side arrow of its own, coming in.
assert.deepEqual([back.mol.cycles![0].branches, back.mol.captions!.find((c) => c.text === "ArB(OH)2")!.cycle], [[{ id: 1, step: 0, in: {} }], { cycle: 300, step: 0, side: "in", branch: 1 }]);
assert.deepEqual(back.style, style);
assert.deepEqual(back.lost, {});
parse(serialize(back.mol));
const second = toCdxml(back.mol, back.style, { name: "check.cdxml" }), third = fromCdxml(second);
assert.equal(toCdxml(third.mol, third.style, { name: "check.cdxml" }), second, "after one save, saving again changes nothing");
// Line spacing and a caption's width, as ChemDraw writes them on a text: LineHeight auto or pt, Variable as the caption
// style's (CaptionLineHeight), WordWrapWidth in pt with decimals.
assert.ok(/<t\s[^>]*\sLineHeight="18"/.test(text) && /<t\s[^>]*\sCaptionLineHeight="variable"/.test(text) && !/\sLineHeight="variable"/.test(text), "line spacing");
{
  const wrapped = fromCdxml('<CDXML BondLength="14.4"><page><t p="0 0" WordWrapWidth="57.6" CaptionLineHeight="variable"><s font="3" size="10">a b</s></t></page></CDXML>');
  assert.deepEqual([wrapped.mol.captions?.[0].width, wrapped.mol.captions?.[0].lineHeight], [57.6 / wrapped.style.bond, "variable"]);
}
console.log("cdxml.check: every object kind round trips");

// The file is laid out as ChemDraw writes it: the two header lines, the root's ACS settings, tables, then the page.
{
  const acs = toCdxml(drawing, DEFAULT_STYLE);
  assert.ok(acs.startsWith('<?xml version="1.0" encoding="UTF-8" ?>\n<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n<CDXML\n CreationProgram='));
  for (const a of ['BondLength="14.40"', 'LineWidth="0.60"', 'BoldWidth="2"', 'HashSpacing="2.50"', 'MarginWidth="1.60"', 'BondSpacing="18"', 'LabelFace="96"', 'WindowSize="0 0"', 'ChemPropHenry="Henry&apos;s Law: "'])
    assert.ok(acs.includes(a), a);
  assert.ok(/><colortable>\n<color r="1" g="1" b="1"\/>\n<color r="0" g="0" b="0"\/>\n<color r="1" g="0" b="0"\/>/.test(acs), "ChemDraw's colour table start");
  assert.ok(acs.indexOf("<fonttable>") < acs.indexOf("<page"), "fonts before the page");
  const root = parseXml(acs), all: Xml[] = [];
  const walk = (x: Xml) => { all.push(x); x.kids.forEach(walk); };
  walk(root);
  const ids = all.filter((x) => x.name !== "font").map((x) => x.attrs.id).filter(Boolean);
  assert.equal(new Set(ids).size, ids.length, "ids are unique (font ids are their own)");
  // Every arrow has its legacy copy, and every step names the copy (spec 11).
  const legacy = all.filter((x) => x.attrs.SupersededBy);
  assert.equal(legacy.length, all.filter((x) => x.name === "arrow").length);
  for (const s of all.filter((x) => x.name === "step")) assert.ok(legacy.some((g) => g.attrs.id === s.attrs.ReactionStepArrows));
  // The reaction: drawing 1 to drawing 2 over arrow 101, with its conditions and the mapped atoms.
  const step = all.find((x) => x.name === "step" && x.attrs.ReactionStepReactants)!;
  assert.ok(step.attrs.ReactionStepProducts && step.attrs.ReactionStepObjectsAboveArrow === "5" && step.attrs.ReactionStepObjectsBelowArrow === "6" && step.attrs.ReactionStepAtomMapManual);
  console.log("cdxml.check: layout ok");
}

// Another page and style, and only part of a drawing (the clipboard).
{
  const custom = readStyle({ ...DEFAULT_STYLE, page: "Custom", custom: [180.5, 120.25] });
  assert.deepEqual(fromCdxml(toCdxml({ atoms: [], bonds: [] }, custom)).style, custom);
  const part = fromCdxml(toCdxml(drawing, DEFAULT_STYLE, { selection: { atoms: [0, 1, 2, 9], items: [1, 5, 101, 106] } })).mol;
  assert.deepEqual([part.atoms.length, part.bonds.length, part.captions?.map((c) => c.id), part.arrows?.map((a) => a.id)], [4, 2, [1, 5], [101, 106]]);
  assert.equal(part.captions?.[1].on?.arrow, 101);
  // Arrows Octet derives (a cycle's) are written for ChemDraw and skipped when Octet reads its own file.
  const derived: Arrow = { id: -5, kind: "curved", from: [17, 0], to: [20, 3], bend: 0.2 };
  const withDerived = toCdxml(drawing, DEFAULT_STYLE, { derived: [derived] });
  const count = (xml: string) => xml.split("<arrow\n").length - 1;
  assert.equal(count(withDerived), count(toCdxml(drawing, DEFAULT_STYLE)) + 1);
  same(drawing, fromCdxml(withDerived).mol, "derived arrows");
  // A cycle's arrows take its line width (UI-42), so ChemDraw draws them as wide as Octet does.
  const arcs = layoutCycles(drawing, 1, 1, () => undefined).arrows;
  assert.ok(arcs.length && arcs.every((a) => a.width === 1.4));
  assert.ok(toCdxml(drawing, DEFAULT_STYLE, { derived: arcs }).includes('LineWidth="1.40"'));
  // Each arc follows the cycle's circle: its middle is on the circle, not bent in towards the centre.
  const fromCentre = (q: [number, number]) => Math.hypot(q[0] - 20, q[1]);
  const onCircle = arcs.filter((a) => Math.abs(fromCentre(a.from) - 3) < 1e-6 && Math.abs(fromCentre(a.to) - 3) < 1e-6);
  assert.ok(onCircle.length === 3 && onCircle.every((a) => Math.abs(fromCentre(bendPoint(a)) - 3) < 1e-6));
  // A reversible step goes out as ChemDraw's curved equilibrium (HalfLeft at both ends, the shaft spacing, an arc), and
  // ChemDraw reads that back as one. A hidden step writes no arrow. A side arrow's half writes no head where it has
  // none, and Full on a product's outer end.
  {
    const cyc = { ...drawing.cycles![0], at: [1, 3, 5], steps: [{ kind: "equilibrium" as const, ratio: 3 }, { hidden: true as const }, null], branches: [{ id: 1, step: 2, in: {}, out: {} }] };
    const m: Mol = { ...drawing, cycles: [cyc] }, xml = toCdxml(m, DEFAULT_STYLE, { derived: layoutCycles(m, 30, 1, () => undefined).arrows }), all: Xml[] = [];
    const walk = (x: Xml) => { all.push(x); x.kids.forEach(walk); };
    walk(parseXml(xml));
    const ours = all.filter((x) => x.name === "arrow" && x.attrs.Octet?.includes('"cycle":300')), sides = ours.filter((x) => x.attrs.Octet.includes('"branch"')), steps = ours.filter((x) => !sides.includes(x));
    assert.equal(steps.length, 2, "a hidden step writes no arrow");
    const eq = steps.find((x) => x.attrs.ArrowheadTail === "HalfLeft")!;
    assert.ok(eq && eq.attrs.ArrowheadHead === "HalfLeft" && Number(eq.attrs.ArrowShaftSpacing) > 0 && Number(eq.attrs.AngularSize) !== 0 && eq.attrs.ArrowEquilibriumRatio === "300" && eq.attrs.Center3D);
    assert.deepEqual(sides.map((x) => x.attrs.ArrowheadHead), [undefined, "Full"]);
    assert.ok(sides.every((x) => x.attrs.ArrowheadTail === undefined));
    const chemdraw = fromCdxml(xml.replace(/ Octet="\{&quot;d&quot;:1[^"]*"/g, "")).mol.arrows!.find((a) => a.kind === "equilibrium" && a.point);
    assert.ok(chemdraw && chemdraw.point && chemdraw.bend && chemdraw.ratio === 3, JSON.stringify(chemdraw));
  }
  // Issue 30: a part writes only the arrows of its own cycles. The editor gives every cycle's arrows; a copy of one
  // cycle carries that cycle's arrows, and a copy of a structure carries none.
  {
    const one = drawing.cycles![0], two = { ...one, id: 301, centre: [30, 0] as [number, number] }, m: Mol = { ...drawing, cycles: [one, two] };
    const all = layoutCycles(m, 30, 1, () => undefined).arrows, mine = all.filter((a) => a.cycle === two.id).length;
    // The arrows written from a cycle (Octet's "d" mark), and the cycles written (their ids in this file).
    const of = (xml: string) => {
      const arrows: string[] = [], walk = (x: Xml) => { if (x.name === "arrow" && x.attrs.Octet?.includes('"d":1')) arrows.push(x.attrs.Octet); x.kids.forEach(walk); };
      walk(parseXml(xml));
      return arrows;
    };
    assert.ok(mine && mine < all.length);
    const copied = of(toCdxml({ ...m, cycles: [two] }, DEFAULT_STYLE, { derived: all }));
    assert.equal(copied.length, mine, "only the copied cycle's arrows");
    assert.ok(copied.every((o) => o.includes('"cycle":')), "each names its cycle");
    assert.deepEqual(of(toCdxml(m, DEFAULT_STYLE, { derived: all, selection: { atoms: [0, 1, 2], items: [] } })), [], "a structure alone has no cycle arrows");
    assert.equal(of(toCdxml(m, DEFAULT_STYLE, { derived: all })).length, all.length, "the whole drawing has both cycles' arrows");
  }
  // A label Octet can expand goes to ChemDraw as an abbreviation with its own atoms; Octet keeps the label.
  const phenyl: Mol = { atoms: [0, 1, 2, 3, 4, 5].map((k) => A("C", Math.cos((k * Math.PI) / 3), Math.sin((k * Math.PI) / 3))), bonds: [0, 1, 2, 3, 4, 5].map((k) => b(k, (k + 1) % 6, { type: k % 2 ? 1 : 2 })) };
  const expanded = toCdxml(drawing, DEFAULT_STYLE, { expand: (t) => (t === "Ph" ? phenyl : undefined) });
  assert.ok(expanded.includes('NodeType="Fragment"') && expanded.includes('NodeType="ExternalConnectionPoint"'));
  same(drawing, fromCdxml(expanded).mol, "expanded labels");
  console.log("cdxml.check: selection, derived arrows and abbreviations ok");
}

// A file in ChemDraw's own form (written here by hand): legacy copies skipped for their arrows, legacy graphics on
// their own read as arrows, abbreviations, charges and radicals as symbols, groups, steps and formula text.
{
  const file = `<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >
<CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2" MarginWidth="1.60" HashSpacing="2.50" BondSpacing="18" LabelFont="3" LabelSize="10" LabelFace="96" CaptionFont="3" CaptionSize="10" color="0" bgcolor="1"
><colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/><color r="1" g="0" b="0"/></colortable
><fonttable><font id="3" charset="x-mac-roman" name="Arial"/><font id="4" charset="x-mac-roman" name="Arial Bold Italic"/></fonttable
><page id="1" BoundingBox="0 0 540 720" WidthPages="1" HeightPages="1"
><group id="2" Z="20"><fragment id="3" Z="10"
><n id="4" p="270 360" Z="1"/><n id="5" p="282.47 367.2" Z="2" Element="7" NumHydrogens="3" Charge="1"><t p="278.86 370.78" LabelJustification="Left"><s font="3" size="10" face="96">NH3+</s></t></n
><n id="6" p="257.53 367.2" Z="3" NodeType="Nickname"><fragment id="7"><n id="8" p="257.53 367.2"/><n id="9" p="270 360" NodeType="ExternalConnectionPoint"/><b id="10" B="9" E="8"/></fragment
><t p="261.42 370.78" LabelJustification="Right" Justification="Right"><s font="3" size="10" face="96">Me</s></t></n
><n id="11" p="270 345.6" Z="4" Element="8" Radical="Doublet"><t p="266.11 349.24" LabelJustification="Left"><s font="3" size="10" face="96">O</s></t></n
><b id="12" Z="5" B="4" E="5"/><b id="13" Z="6" B="4" E="6" Display="WedgeEnd"/><b id="14" Z="7" B="4" E="11" Order="2"/><b id="40" B="4" E="99"/>
<graphic id="15" BoundingBox="276 338 268.5 338" Z="8" GraphicType="Symbol" SymbolType="Electron"><represent attribute="Radical" object="11"/></graphic
><graphic id="16" BoundingBox="290 360 282.5 360" Z="9" GraphicType="Symbol" SymbolType="CirclePlus"><represent attribute="Charge" object="5"/></graphic
><graphic id="17" BoundingBox="262 340 254.5 340" GraphicType="Symbol" SymbolType="LonePair"/></fragment
><t id="18" p="270 400" Z="11" CaptionJustification="Center" Justification="Center"><s font="4" size="10" face="3">1</s></t></group
><t id="19" p="340 350" Z="12" CaptionJustification="Center" Justification="Center"><s font="3" size="10" face="96">CH2Cl2</s></t
><t id="20" p="340 375" Z="13">text outside runs is dropped<s font="3" size="10">rt, </s><s font="3" size="10" color="4">24&#10;h</s></t
><t id="21" p="0 0" Visible="no"><s font="3" size="10">hidden</s></t
><graphic id="22" SupersededBy="23" BoundingBox="380 360 300 360" Z="14" GraphicType="Line" ArrowType="FullHead"/>
<graphic id="24" BoundingBox="200 300 180 300" Z="15" GraphicType="Line" ArrowType="Equilibrium"/>
<graphic id="25" BoundingBox="400 200 380 200" Z="16" GraphicType="Arc" ArrowType="FullHead" AngularSize="-90"/>
<graphic id="26" BoundingBox="100 100 50 60" Z="17" GraphicType="Rectangle" RectangleType="RoundEdge Shadow" CornerRadius="600" ShadowSize="400"/>
<graphic id="27" BoundingBox="150 100 130 100" Z="18" GraphicType="Oval" OvalType="Circle Filled" color="4"/>
<graphic id="28" BoundingBox="200 140 200 100" Z="19" GraphicType="Bracket" BracketType="Square"/>
<graphic id="29" BoundingBox="240 100 240 140" Z="20" GraphicType="Bracket" BracketType="Square"/>
<graphic id="30" BoundingBox="310 420 300 420" Z="21" GraphicType="Orbital" OrbitalType="pShaded"/>
<curve id="31" Z="22" FillType="Solid" CurveType="129" ArrowheadType="Solid" Closed="yes" CurvePoints="10 10 10 10 20 10 30 10 30 10 30 10 30 30 30 30 30 30"/>
<embeddedobject id="32" BoundingBox="0 0 10 10" PNG="89504E47"/>
<arrow id="23" Z="14" FillType="None" ArrowheadHead="Full" ArrowheadType="Solid" HeadSize="1000" ArrowheadCenterSize="875" ArrowheadWidth="250" Head3D="380 360 0" Tail3D="300 360 0" Center3D="300 360 0" MajorAxisEnd3D="380 360 0" MinorAxisEnd3D="300 440 0"/>
<arrow id="33" Z="23" ArrowheadHead="Full" ArrowheadType="Solid" AngularSize="90" Head3D="450 280 0" Tail3D="470 300 0" Center3D="450 300 0" MajorAxisEnd3D="470 300 0" MinorAxisEnd3D="450 320 0"/>
<scheme id="34"><step id="35" ReactionStepReactants="3" ReactionStepArrows="22" ReactionStepObjectsAboveArrow="19" ReactionStepObjectsBelowArrow="20"/></scheme>
</page></CDXML>`;
  const { mol, style: s, lost } = fromCdxml(file);
  assert.equal(s.page, "Letter");
  assert.deepEqual(lost, { "hidden object": 1, bond: 1 });
  assert.deepEqual(mol.atoms.map((a) => [a.label, a.text, a.charge, a.radical, a.pairs, a.circled]), [["C", undefined, undefined, undefined, undefined, undefined], ["N", undefined, 1, undefined, undefined, true], ["C", "Me", undefined, undefined, undefined, undefined], ["O", undefined, undefined, 1, 1, undefined]]);
  assert.deepEqual(mol.atoms[0].location, [0, 0, 0]);
  assert.deepEqual(mol.bonds.map((x) => [x.type, x.atoms, x.stereo]), [[1, [0, 1], undefined], [1, [2, 0], 1], [2, [0, 3], undefined]]);
  const [one, solvent, conditions] = mol.captions!;
  assert.deepEqual([one.text, one.bold, one.italic, one.font, one.align], ["1", true, true, undefined, undefined]);
  assert.deepEqual(solvent.runs?.map((r) => [r.text, r.script]), [["CH", undefined], ["2", "sub"], ["Cl", undefined], ["2", "sub"]]);
  assert.deepEqual([conditions.text, conditions.align, conditions.runs?.[1]], ["rt, 24\nh", "left", { text: "24\nh", colour: "#FF0000" }]);
  // Arrows in drawing order: the orbital and the filled curve (Octet draws them behind the structures), then by Z the
  // reaction arrow, the legacy graphics on their own and the arc.
  assert.deepEqual(mol.arrows!.map((a) => a.kind), ["orbital", "curve", "reaction", "equilibrium", "curved", "curved"]);
  const [orbital, curve, reaction, equilibrium, legacyArc, arc] = mol.arrows!;
  assert.deepEqual([solvent.on, conditions.on], [{ arrow: reaction.id, side: "above" }, { arrow: reaction.id, side: "below" }]);
  assert.deepEqual([reaction.from, reaction.to], [[30 / 14.4, 0], [110 / 14.4, 0]]);
  assert.deepEqual([equilibrium.from, equilibrium.to].map((p) => p.map((v) => +v.toFixed(3))), [[-90 / 14.4, 60 / 14.4].map((v) => +v.toFixed(3)), [-70 / 14.4, 60 / 14.4].map((v) => +v.toFixed(3))]);
  // The legacy arc's tail is its head turned back by its sweep; both arcs bow to the outside of their circle.
  assert.ok(Math.hypot(legacyArc.from[0] - 110 / 14.4, legacyArc.from[1] - 180 / 14.4) < 1e-9 && legacyArc.bend! > 0 && arc.bend! < 0 && Math.abs(Math.abs(arc.bend!) - 0.2071) < 1e-3);
  assert.deepEqual(orbital.orbital, { shape: "p", phase: "shaded" });
  assert.deepEqual([curve.curve!.points.length, curve.curve!.closed, curve.fill, !!curve.curve!.points[0].c2, !!curve.curve!.points[1].c1], [3, true, "solid", true, false]);
  assert.deepEqual(mol.shapes!.map((x) => [x.kind, x.fill, x.shadow, x.side, x.colour]), [["picture", undefined, undefined, undefined, undefined], ["rounded", undefined, true, undefined, undefined], ["oval", "solid", undefined, undefined, "#FF0000"], ["brackets", undefined, undefined, undefined, undefined]]);
  assert.deepEqual(mol.shapes![0].picture, { PNG: "89504E47" }); // a picture is kept as it came, at the back as it has no Z (REL-15)
  assert.deepEqual(mol.groups!.map((g) => [g.atoms, g.items]), [[[0, 1, 2, 3], [one.id]]]);
  parse(serialize(mol));
  console.log("cdxml.check: ChemDraw's form read");
}

// ChemDraw's arrow sizes and kinds as its own files hold them (CD-14, CD-15): a bold arrow's doubled head (its own
// size, so left unset), a medium head, an unbalanced equilibrium, a hashed no-go, a dipole, a hollow block arrow as
// Sam's files hold it, and a 270° elliptical arc read as a curve on that ellipse.
{
  const head = (id: number, more: string) => `<arrow id="${id}" Z="${id}" FillType="None" ArrowheadType="Solid" ${more}/>`;
  const file = `<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2"><page id="1" BoundingBox="0 0 540 720">
${head(2, 'LineType="Bold" ArrowheadHead="Full" HeadSize="2000" ArrowheadCenterSize="1750" ArrowheadWidth="500" Head3D="100 100 0" Tail3D="40 100 0"')}
${head(3, 'ArrowheadHead="Full" HeadSize="1500" ArrowheadCenterSize="1313" ArrowheadWidth="375" Head3D="100 130 0" Tail3D="40 130 0"')}
${head(4, 'ArrowheadHead="HalfLeft" ArrowheadTail="HalfLeft" ArrowShaftSpacing="300" ArrowEquilibriumRatio="300" HeadSize="1000" Head3D="100 160 0" Tail3D="40 160 0"')}
${head(5, 'ArrowheadHead="Full" NoGo="Hash" HeadSize="1000" Head3D="100 190 0" Tail3D="40 190 0"')}
${head(6, 'ArrowheadHead="Full" Dipole="yes" HeadSize="1000" Head3D="100 220 0" Tail3D="40 220 0"')}
<arrow id="7" Z="7" FillType="None" ArrowheadHead="Full" ArrowheadType="Hollow" HeadSize="1200" ArrowheadCenterSize="1200" ArrowheadWidth="300" ArrowShaftSpacing="1200" Head3D="446.56 569.80 0" Tail3D="84.33 569.80 0" Center3D="84.33 569.80 0" MajorAxisEnd3D="117.79 569.80 0" MinorAxisEnd3D="84.33 576.16 0"/>
${head(8, 'ArrowheadHead="Full" AngularSize="-270" HeadSize="800" ArrowheadCenterSize="700" ArrowheadWidth="200" Head3D="220 300 0" Tail3D="200 350 0" Center3D="200 300 0" MajorAxisEnd3D="200 350 0" MinorAxisEnd3D="220 300 0"')}
</page></CDXML>`;
  const { mol } = fromCdxml(file);
  assert.deepEqual(mol.arrows!.map((a) => a.kind), ["reaction", "reaction", "equilibrium", "hash", "dipole", "block", "curve"]);
  const [bold, medium, unbalanced, , , block, ellipse] = mol.arrows!;
  assert.deepEqual([bold.style, bold.headSize, medium.headSize, unbalanced.ratio, block.headSize, block.shaft], ["bold", undefined, headOfLength(15), 3, undefined, undefined]);
  // The ellipse: centre (200, 300), long half-axis 50 down the page, short 20 across; the arc runs 270° from the tail
  // at the end of the long axis to the head at the end of the short one, every point on the ellipse.
  const pts = ellipse.curve!.points, c = pts.map((q) => [q.at[0] * 14.4, -q.at[1] * 14.4]), [cx, cy] = [c[0][0], c[0][1] - 50];
  assert.ok(pts.length === 4 && c.every(([x, y]) => Math.abs(((x - cx) / 20) ** 2 + ((y - cy) / 50) ** 2 - 1) < 1e-6) && Math.abs(c[3][0] - c[0][0] - 20) < 1e-6 && Math.abs(c[3][1] - c[0][1] + 50) < 1e-6);
  assert.deepEqual([ellipse.end, ellipse.headSize], ["full", headOfLength(8)]);
  // Octet writes them back as ChemDraw holds them.
  const out = toCdxml(mol, DEFAULT_STYLE);
  const written = [...out.matchAll(/<arrow\b[^>]*>/g)].map((m) => m[0].replace(/\s+/g, " "));
  for (const attrs of ['ArrowEquilibriumRatio="300"', 'NoGo="Hash"', 'Dipole="yes"', 'ArrowheadType="Hollow" HeadSize="1200" ArrowheadCenterSize="1200" ArrowheadWidth="300" ArrowShaftSpacing="1200"', 'HeadSize="2000" ArrowheadCenterSize="1750" ArrowheadWidth="500"', 'HeadSize="1500" ArrowheadCenterSize="1313" ArrowheadWidth="375"'])
    assert.ok(written.some((w) => w.includes(attrs)), attrs);
  parse(serialize(mol));
  // A retrosynthetic arrow's size (it has no barb handle, only the palette's sizes) comes back too.
  const retro: Arrow = { id: 1, kind: "retro", from: [0, 0], to: [3, 0], headSize: headOfLength(22.5) };
  assert.deepEqual(fromCdxml(toCdxml({ atoms: [], bonds: [], arrows: [retro] }, DEFAULT_STYLE)).mol.arrows![0].headSize, headOfLength(22.5));
  // A bent equilibrium is ChemDraw's curved one: an arc with two half heads and a shaft spacing. It comes back as an
  // equilibrium with its point and bend, from Octet's file and from one without Octet's data (as ChemDraw writes it).
  const curvedEq: Arrow = { id: 1, kind: "equilibrium", from: [0, 0], to: [3, 0], point: true, bend: 0.3, ratio: 3 };
  const eqOut = toCdxml({ atoms: [], bonds: [], arrows: [curvedEq] }, DEFAULT_STYLE);
  assert.ok(/<arrow\b[^>]*AngularSize=[^>]*ArrowShaftSpacing|<arrow\b[^>]*ArrowShaftSpacing=[^>]*AngularSize/.test(eqOut), "written as an arc");
  for (const text of [eqOut, eqOut.replace(/ Octet="[^"]*"/g, "")]) {
    const back = fromCdxml(text).mol.arrows![0];
    assert.deepEqual([back.kind, back.point, Math.abs(back.bend! - 0.3) < 1e-3, back.ratio], ["equilibrium", true, true, 3]);
  }
  console.log("cdxml.check: ChemDraw's arrow sizes and kinds read and written");
}

// ChemDraw's turned and bold shapes (CD-18): a box turned 30° (its frame's axes turned, clockwise on the page with y
// down), a bold oval behind the structure, and a filled box above it, which Bring to Front's draw order puts in front.
{
  const c = [200, 300], [cs, sn] = [Math.cos(Math.PI / 6), Math.sin(Math.PI / 6)], f = (v: number) => v.toFixed(2);
  const file = `<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2"><page id="1" BoundingBox="0 0 540 720">
<graphic id="2" Z="2" BoundingBox="130 100 100 100" GraphicType="Oval" OvalType="Bold Dashed" Center3D="100 100 0" MajorAxisEnd3D="130 100 0" MinorAxisEnd3D="100 115 0"/>
<fragment id="3" Z="5"><n id="4" p="300 300"/></fragment>
<graphic id="5" Z="10" BoundingBox="0 0 1 1" GraphicType="Rectangle" RectangleType="Filled" Center3D="${f(c[0])} ${f(c[1])} 0" MajorAxisEnd3D="${f(c[0] + 40 * cs)} ${f(c[1] - 40 * sn)} 0" MinorAxisEnd3D="${f(c[0] + 20 * sn)} ${f(c[1] + 20 * cs)} 0"/>
</page></CDXML>`;
  const { mol, lost } = fromCdxml(file);
  assert.deepEqual(lost, {});
  const [oval, box] = mol.shapes!;
  assert.deepEqual([oval.kind, oval.boldLine, oval.dashed, oval.order, box.kind, box.fill, box.order], ["oval", true, true, undefined, "box", "solid", 1]);
  assert.ok(Math.abs(box.angle! - 30) < 0.05 && Math.abs(Math.abs(box.to[0] - box.from[0]) - 80 / 14.4) < 2e-3 && Math.abs(Math.abs(box.to[1] - box.from[1]) - 40 / 14.4) < 2e-3);
  console.log("cdxml.check: ChemDraw's turned, bold and front shapes read");
}

// ChemDraw's turned text (CD-19): RotationAngle is degrees clockwise on the page times 65536, as in its samples (KMnO4
// on a bond at 54°); Octet turns anticlockwise, so it reads -54, and writes it back the same.
{
  const file = `<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40" CaptionFont="3" CaptionSize="10"><fonttable><font id="3" name="Arial"/></fonttable><page id="1" BoundingBox="0 0 540 720">
<t id="2" p="345.14 363.88" RotationAngle="3538944"><s font="3" size="10">KMnO4</s></t></page></CDXML>`;
  const { mol, lost } = fromCdxml(file);
  assert.deepEqual([lost, mol.captions![0].angle], [{}, -54]);
  assert.ok(/RotationAngle="3538944"/.test(toCdxml(mol, DEFAULT_STYLE)));
  // Turned conditions in a reaction step stay where ChemDraw put them (Octet lays conditions out level); level ones
  // become the arrow's conditions.
  const step = `<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40" CaptionFont="3" CaptionSize="10"><fonttable><font id="3" name="Arial"/></fonttable><page id="1" BoundingBox="0 0 540 720">
<arrow id="10" Z="1" BoundingBox="300 295 400 305" ArrowheadHead="Full" ArrowheadType="Solid" HeadSize="1000" Head3D="400 300 0" Tail3D="300 300 0"/>
<t id="11" p="330 290" RotationAngle="3538944"><s font="3" size="10">KMnO4</s></t><t id="12" p="330 315"><s font="3" size="10">H2O</s></t>
<scheme id="20"><step id="21" ReactionStepArrows="10" ReactionStepObjectsAboveArrow="11" ReactionStepObjectsBelowArrow="12"/></scheme></page></CDXML>`;
  const [turned, level] = fromCdxml(step).mol.captions!;
  assert.deepEqual([turned.text, turned.angle, turned.on, level.text, level.on?.side], ["KMnO4", -54, undefined, "H2O", "below"]);
  console.log("cdxml.check: ChemDraw's turned text read and written");
}

// Delete takes only what is selected (issue 12). A file that repeats a text's id or leaves it out still gives every
// object an id of its own, and a step that lists text far from its arrow does not take that text with the arrow.
{
  const t = (id: string, p: string, s: string) => `<t${id} p="${p}"><s font="3" size="10">${s}</s></t>`;
  const body = `<fonttable><font id="3" name="Arial"/></fonttable><page id="1" BoundingBox="0 0 540 720">
${t(' id="10"', "100 100", "A")}${t(' id="10"', "100 130", "B")}${t("", "100 160", "C")}${t("", "100 190", "D")}${t(' id="11"', "320 90", "far")}
<arrow id="20" Z="1" ArrowheadHead="Full" ArrowheadType="Solid" HeadSize="1000" Head3D="400 300 0" Tail3D="300 300 0"/>
<scheme id="30"><step id="31" ReactionStepArrows="20" ReactionStepObjectsAboveArrow="11"/></scheme></page></CDXML>`;
  for (const root of ['<CDXML BondLength="14.40">', `<CDXML BondLength="14.40" Octet='{"v":1}'>`]) {
    const m = fromCdxml(`<?xml version="1.0" encoding="UTF-8" ?>${root}${body}`).mol, texts = m.captions!;
    const ids = [...texts, ...m.arrows!].map((x) => x.id);
    assert.deepEqual([texts.map((c) => c.text).sort(), new Set(ids).size], [["A", "B", "C", "D", "far"], 6], "every object has an id of its own");
    for (const c of texts) assert.deepEqual(deleteGraphics(deleteAtoms(m, new Set()), new Set([c.id])).captions!.map((x) => x.text), texts.filter((x) => x !== c).map((x) => x.text));
    const far = texts.find((c) => c.text === "far")!, at = placedAt(far, m.arrows) ?? [far.x, far.y];
    assert.ok(far.on, "the step puts the text on the arrow");
    const left = deleteGraphics(m, new Set([m.arrows![0].id])).captions!, kept = left.find((c) => c.text === "far");
    assert.deepEqual([left.length, kept?.on, kept?.placed, kept?.x, kept?.y], [5, undefined, undefined, at[0], at[1]], "the arrow's text stays where it is");
  }
  console.log("cdxml.check: Delete takes only what is selected (issue 12) ok");
}

// Turned shapes in ChemDraw's form: a box turned 30° by its axes, with its own line width; one bracket lying down
// (as in Sam's files) and a pair lying down, facing each other.
{
  const r = Math.PI / 6, f = (v: number) => v.toFixed(2);
  const file = `<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40" LineWidth="0.60"><page id="1" BoundingBox="0 0 540 720">
<graphic id="2" BoundingBox="290 350 250 370" GraphicType="Rectangle" RectangleType="Plain" LineWidth="1.5" Center3D="270 360 0" MajorAxisEnd3D="${f(270 + 20 * Math.cos(r))} ${f(360 - 20 * Math.sin(r))} 0" MinorAxisEnd3D="${f(270 + 10 * Math.sin(r))} ${f(360 + 10 * Math.cos(r))} 0"/>
<graphic id="3" BoundingBox="442.02 313.74 403.76 313.74" GraphicType="Bracket" BracketType="Square"/>
<graphic id="4" BoundingBox="440 420 400 420" GraphicType="Bracket" BracketType="Round"/>
<graphic id="5" BoundingBox="400 380 440 380" GraphicType="Bracket" BracketType="Round"/>
</page></CDXML>`;
  const { mol, lost } = fromCdxml(file);
  assert.deepEqual(lost, {});
  const [box, one, pair] = mol.shapes!, size = (sh: Shape) => [Math.abs(sh.to[0] - sh.from[0]), Math.abs(sh.to[1] - sh.from[1])].map((v) => +v.toFixed(2));
  assert.deepEqual([box.kind, Math.round(box.angle! * 10) / 10, box.width, size(box)], ["box", 30, 1.5, [+(40 / 14.4).toFixed(2), +(20 / 14.4).toFixed(2)]]);
  assert.deepEqual([one.kind, one.side, one.angle], ["brackets", "left", 90], "a bracket lying with its lips up is a left bracket turned a quarter");
  assert.deepEqual([pair.kind, pair.side, pair.angle, size(pair)], ["parens", undefined, 90, [+(40 / 14.4).toFixed(2), +(40 / 14.4).toFixed(2)]]);
  // Upright boxes whose axes run left, or down the page (as in Sam's files), read with their corners low and high, so
  // they read back the same once Octet has written them.
  const upright = fromCdxml(`<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40" LineWidth="0.60"><page id="1" BoundingBox="0 0 540 720">
<graphic id="2" BoundingBox="47 467 214 252" GraphicType="Rectangle" RectangleType="Shadow" Center3D="130.5 359.5 0" MajorAxisEnd3D="47 359.5 0" MinorAxisEnd3D="130.5 467 0"/>
<graphic id="3" BoundingBox="34 538 224 490" GraphicType="Rectangle" RectangleType="RoundEdge" Center3D="129 514 0" MajorAxisEnd3D="129 538 0" MinorAxisEnd3D="34 514 0"/>
</page></CDXML>`).mol;
  assert.deepEqual(upright.shapes!.map((sh) => [sh.angle, sh.from[0] < sh.to[0], sh.from[1] < sh.to[1], size(sh)]), [[undefined, true, true, [+(167 / 14.4).toFixed(2), +(215 / 14.4).toFixed(2)]], [undefined, true, true, [+(190 / 14.4).toFixed(2), +(48 / 14.4).toFixed(2)]]]);
  const again = fromCdxml(toCdxml(upright, DEFAULT_STYLE)).mol;
  assert.deepEqual(again.shapes!.map((sh) => [sh.from, sh.to].flat().map((v) => +v.toFixed(3))), upright.shapes!.map((sh) => [sh.from, sh.to].flat().map((v) => +v.toFixed(3))));
  console.log("cdxml.check: turned shapes read");
}

// Hostile files are refused with a message, or read with the bad parts left out; nothing is expanded or fetched.
{
  const refused: [string, string][] = [
    ["not a drawing", NOT_CDXML], ['{"format":"octet"}', NOT_CDXML], ['<?xml version="1.0"?><svg/>', NOT_CDXML], ["<!-- <CDXML --><svg/>", NOT_CDXML],
    ["<CDXML><page></CDXML>", DAMAGED], ['<CDXML a="1" a="2"/>', DAMAGED], [`<CDXML>${"<group>".repeat(80)}${"</group>".repeat(80)}</CDXML>`, DAMAGED],
    ['<CDXML><page><t p="0 0"><s font="3">&#0;</s></t></page></CDXML>', DAMAGED], ['<CDXML><page><t p="0 0"><s>a & b</s></t></page></CDXML>', DAMAGED],
    ["<CDXML><!-- open", DAMAGED], ["<CDXML/>junk", DAMAGED], ["<CDXML/><CDXML/>", DAMAGED], ['<CDXML><page id="1></page></CDXML>', DAMAGED], ["<CDXML><page", DAMAGED],
    [`<CDXML>${" ".repeat(64 * 1024 * 1024)}</CDXML>`, TOO_BIG], [`<CDXML><page><fragment>${'<n p="0 0"/>'.repeat(100_001)}</fragment></page></CDXML>`, TOO_BIG],
  ];
  for (const [file, message] of refused) assert.throws(() => fromCdxml(file), (e: Error) => e.message === message, file.slice(0, 60));
  // Entity tricks: declared entities are never expanded, external ones never fetched.
  const laughs = `<?xml version="1.0"?><!DOCTYPE CDXML [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;"><!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;"><!ENTITY x SYSTEM "file:///etc/passwd">]>
<CDXML __proto__="x" constructor="y"><page><t p="0 0"><s font="3" size="10">&c;&x;ok</s></t></page></CDXML>`;
  const read = fromCdxml(laughs);
  assert.equal(read.mol.captions?.[0].text, "ok");
  assert.equal(({} as Record<string, unknown>).x, undefined);
  // Bad numbers, ids and references: those objects are dropped and counted, the rest read.
  const bad = fromCdxml(`<CDXML><page><fragment><n id="1" p="NaN 0"/><n id="2" p="1e999 0"/><n id="3" p="10 10" Charge="99" Element="999"/><n id="4" p="20 10"/><b B="3" E="7"/><b B="3" E="3"/><b B="3" E="4"/><b B="4" E="3"/></fragment>
<t p="0 0"><s font="3" size="5000">a\u0001b\tc</s></t><arrow id="9" Head3D="x"/><curve CurvePoints="1 2 3"/><graphic GraphicType="Rectangle" BoundingBox="0 0"/><unknownthing/></page></CDXML>`);
  assert.deepEqual([bad.mol.atoms.length, bad.mol.bonds.length, bad.mol.atoms[0].label, bad.mol.atoms[0].charge], [2, 1, "C", undefined]);
  assert.deepEqual(bad.mol.captions?.map((c) => [c.text, c.size]), [["ab c", 999]]);
  assert.deepEqual(bad.lost, { atom: 2, charge: 1, bond: 3, arrow: 1, curve: 1, graphic: 1, unknownthing: 1 });
  parse(serialize(bad.mol));
  // Octet's own data is checked like the rest: wrong kinds, types and sizes are ignored.
  const forged = fromCdxml(`<CDXML Octet='{"v":1,"page":"Moon","custom":"x","cycles":[{"id":"x"},{"id":7,"centre":[0,0],"radius":-1,"nodes":[[1],[2]]}]}'><page>
<fragment><n id="1" p="0 0" Octet='{"map":-5,"hmark":"evil","partial":7,"depth":true}'/><n id="2" p="14 0"/></fragment>
<t id="3" p="0 0" Octet='{"under":[1e99,"x"],"xy":["a",1],"cycle":{"cycle":7,"step":99}}'><s font="1" size="10">x</s></t>
<arrow id="4" Head3D="1 1 0" Tail3D="0 0 0" Center3D="0 0 0" Octet='{"kind":"teleport","style":"glitter"}'/>
<graphic id="5" GraphicType="Orbital" BoundingBox="1 1 0 0" Octet='{"orbital":{"shape":"z","phase":"q"}}'/>
<graphic id="6" GraphicType="Rectangle" BoundingBox="0 0 10 10" Octet='{"shade":{"depth":99,"blur":0,"opacity":1},"kind":"highlight"}'/>
<group id="8" BoundingBox="0 0 10 10" Octet='{"kind":"table","table":{"cells":"x"}}'/>
<graphic id="9" GraphicType="Bracket" BracketType="Square" BoundingBox="0 10 0 0" Octet='{"mark":"far too long a mark","span":[1e99,0]}'/>
</page></CDXML>`);
  // (Its page is A4, Octet's own, as the one it names is not a page: 0,0 is the middle of that page.)
  assert.deepEqual(forged.mol.atoms[0], { label: "C", location: [-261.64 / 14.4, 384.95 / 14.4, 0] });
  assert.equal(forged.mol.cycles, undefined);
  assert.deepEqual([forged.mol.arrows?.map((a) => a.kind), forged.mol.shapes?.map((x) => x.kind)], [["orbital", "line"], ["highlight", "brackets"]]);
  assert.deepEqual([forged.mol.captions?.[0].under, forged.mol.captions?.[0].cycle, forged.style.page], [undefined, undefined, "A4"]);
  assert.deepEqual(forged.lost, { table: 1 });
  parse(serialize(forged.mol));
  // A cycle's steps and side arrows out of bounds are left out; the cycle stays.
  const bounds = fromCdxml(`<CDXML Octet='{"v":1,"cycles":[{"id":9,"centre":[0,0],"radius":3,"nodes":[[1],[2]],"steps":[{"ratio":0}],"branches":[{"id":1,"step":5,"in":{}},{"id":2,"step":0,"in":{"atoms":[99]}}]}]}'><page>
<fragment><n id="1" p="0 0"/><n id="2" p="14 0"/></fragment><t id="3" p="0 0" Octet='{"cycle":{"cycle":9,"step":0,"side":"in","branch":"x"}}'><s font="1" size="10">x</s></t></page></CDXML>`).mol;
  assert.deepEqual([bounds.cycles?.[0].steps, bounds.cycles?.[0].branches, bounds.captions?.[0].cycle?.branch], [undefined, [{ id: 1, step: 0, in: {} }], 1]);
  parse(serialize(bounds));
  console.log("cdxml.check: hostile files refused or read safely");
}

// Atom Properties and the newer marks: an isotope, a singlet radical (a carbene), aromatic circles and a reaction's
// stoichiometry grid come back from Octet's own CDXML.
{
  const ring = [0, 1, 2, 3, 4, 5].map((k) => A("C", Math.cos((k * Math.PI) / 3), Math.sin((k * Math.PI) / 3), { circle: true }));
  const m: Mol = {
    atoms: [...ring, A("C", 2, 0, { isotope: 13 }), A("C", 6, 0, { radical: 3 }), A("N", 3, -3, { isotope: 15, charge: 1 })],
    bonds: [...ring.map((_, k) => b(k, (k + 1) % 6, { type: k % 2 ? 1 : 2 })), b(0, 6)],
    arrows: [{ id: 40, kind: "reaction", from: [3, 0], to: [5, 0] }],
    grids: [{ arrow: 40, typed: { r0: { mass: 1.06, purity: 0.98 }, p0: { measured: 0.9 } }, limiting: "r0" }],
  };
  const back = fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol;
  assert.deepEqual(back.atoms.map((a) => [a.label, a.isotope, a.radical, a.circle, a.charge]),
    m.atoms.map((a) => [a.label, a.isotope, a.radical, a.circle, a.charge]), "isotope, singlet radical and ring circles");
  assert.equal(back.atoms[7].pairs, undefined, "a singlet's pair is its radical, not a lone pair");
  assert.deepEqual(back.grids, [{ arrow: back.arrows![0].id, typed: m.grids![0].typed, limiting: "r0" }], "stoichiometry grid");
  // ChemDraw's form of an isotope: Isotope on the node and the mass number in the label's text.
  const cd = `<?xml version="1.0" encoding="UTF-8" ?><CDXML><page id="1"><fragment id="2"><n id="3" p="100 100" Element="6" Isotope="14" NumHydrogens="4"><t p="96 104"><s font="3" size="10" face="96">14CH4</s></t></n></fragment></page></CDXML>`;
  const r = fromCdxml(cd);
  assert.deepEqual([r.mol.atoms[0].label, r.mol.atoms[0].isotope, r.mol.atoms[0].text, r.lost], ["C", 14, undefined, {}], "ChemDraw's ¹⁴CH₄");
  // A singlet's pair is the renderer's pair0, so a pair moved by hand goes out where the page has it, and as a bar
  // when the atom's pairs are bars. ChemDraw's bar for a singlet, and where it put each pair, come back.
  const carbene = (more: Partial<Atom>): Mol => ({ atoms: [A("C", 0, 0), A("C", 0.866, 0.5, { radical: 3, ...more }), A("C", 1.732, 0)], bonds: [b(0, 1), b(1, 2)] });
  const symbolOf = (x: string) => x.match(/<graphic[^>]*SymbolType="LonePair[^"]*"[^>]*>/)![0];
  assert.notEqual(symbolOf(toCdxml(carbene({ angles: { pair0: 0 } }), DEFAULT_STYLE)).match(/BoundingBox="[^"]+"/)![0], symbolOf(toCdxml(carbene({}), DEFAULT_STYLE)).match(/BoundingBox="[^"]+"/)![0], "a moved carbene pair");
  assert.match(symbolOf(toCdxml(carbene({ bars: true }), DEFAULT_STYLE)), /SymbolType="LonePairBar"/);
  const nitrene = `<?xml version="1.0" encoding="UTF-8" ?><CDXML><page id="1"><fragment id="2"><n id="3" p="100 100"/><n id="4" p="114.4 100" Element="7" Radical="Singlet" NumHydrogens="0"/><b id="5" B="3" E="4"/></fragment>`
    + `<graphic id="6" BoundingBox="114.4 92 107 92" GraphicType="Symbol" SymbolType="LonePairBar"><represent attribute="Radical" object="4"/></graphic><graphic id="7" BoundingBox="122 100 122 107" GraphicType="Symbol" SymbolType="LonePairBar"/></page></CDXML>`;
  const nb = fromCdxml(nitrene).mol.atoms[1];
  assert.deepEqual([nb.radical, nb.pairs, nb.bars, Object.keys(nb.angles ?? {}).sort()], [3, 1, true, ["pair0", "pair1"]], "ChemDraw's singlet nitrene");
  console.log("cdxml.check: isotopes, singlet radicals, ring circles and grids ok");
}

// Atom numbers and the document's label options, and ChemDraw's CH3 labels read back as plain carbons.
{
  const m: Mol = { atoms: [A("C", 0, 0, { number: "1" }), A("C", 0.866, 0.5, { number: "2" }), A("O", 1.732, 0)], bonds: [b(0, 1), b(1, 2)] };
  const s = { ...DEFAULT_STYLE, terminalLabels: true, carbonLabels: false, hideH: false };
  const text = toCdxml(m, s);
  assert.match(text, /ShowTerminalCarbonLabels="yes"/);
  assert.match(text, />CH3</, "the terminal carbon's label is written");
  const back = fromCdxml(text);
  assert.deepEqual(back.mol.atoms.map((a) => [a.label, a.text, a.number]), [["C", undefined, "1"], ["C", undefined, "2"], ["O", undefined, undefined]]);
  assert.deepEqual([back.style.terminalLabels, back.style.carbonLabels, back.style.hideH, back.lost], [true, false, false, {}]);
  console.log("cdxml.check: atom numbers and label options ok");
}

// ChemDraw's delocalised rings (bonds of order 1.5, a circle oval inside the ring) and its DoubleDashed bond (order 1.5,
// second line dashed), written and read.
{
  // A ring of n atoms at the origin, bond length 14.4 pt, with optional labels and hydrogens, as ChemDraw writes it.
  const ring = (n: number, labels: Record<number, [number, number?]> = {}, circle = true, extra = "") => {
    const R = 14.4 / (2 * Math.sin(Math.PI / n)), nodes = Array.from({ length: n }, (_, k) => {
      const [el, h] = labels[k] ?? [6];
      return `<n id="${k + 1}" p="${(200 + R * Math.cos((2 * Math.PI * k) / n)).toFixed(2)} ${(200 + R * Math.sin((2 * Math.PI * k) / n)).toFixed(2)}"${el !== 6 ? ` Element="${el}"` : ""}${h !== undefined ? ` NumHydrogens="${h}"` : ""}/>`;
    }).join("");
    const bonds = Array.from({ length: n }, (_, k) => `<b id="${100 + k}" B="${k + 1}" E="${((k + 1) % n) + 1}" Order="1.5"/>`).join("");
    const oval = circle ? `<graphic id="300" BoundingBox="${(200 + 0.62 * R).toFixed(2)} 200 200 200" GraphicType="Oval" OvalType="Circle" Center3D="200 200 0" MajorAxisEnd3D="${(200 + 0.62 * R).toFixed(2)} 200 0" MinorAxisEnd3D="200 ${(200 + 0.62 * R).toFixed(2)} 0"/>` : "";
    return `<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40"><page id="1"><fragment id="2">${nodes}${bonds}${oval}${extra}</fragment></page></CDXML>`;
  };
  const doubles = (m: Mol) => m.bonds.filter((x) => x.type === 2).length;
  const benzene = fromCdxml(ring(6)).mol;
  assert.deepEqual([doubles(benzene), benzene.atoms.every((a) => a.circle), benzene.shapes, benzene.atoms.every((_, i) => benzene.bonds.filter((x) => x.type === 2 && x.atoms.includes(i)).length === 1)], [3, true, undefined, true], "benzene with its circle");
  assert.equal(doubles(fromCdxml(ring(6, { 0: [7] })).mol), 3, "pyridine");
  const pyrrole = fromCdxml(ring(5, { 0: [7, 1] })).mol;
  assert.deepEqual([doubles(pyrrole), pyrrole.bonds.some((x) => x.type === 2 && x.atoms.includes(0))], [2, false], "pyrrole: the NH takes no double bond");
  assert.equal(doubles(fromCdxml(ring(6, {}, false)).mol), 3, "a ring of 1.5 bonds with no circle is still made Kekulé");
  // Octet writes its circled rings and dashed doubles in ChemDraw's form, and reads its own back exactly.
  const m = { ...benzene, bonds: [...benzene.bonds], atoms: [...benzene.atoms, A("C", 3, 0), A("C", 4, 0.5)] };
  m.bonds.push(b(6, 7, { type: 2, display: "dashed" }));
  const text = toCdxml(m, DEFAULT_STYLE);
  assert.equal((text.match(/Order="1.5"/g) ?? []).length, 7, "six ring bonds and the dashed double");
  assert.match(text, /Order="1.5"\s+Display2="Dash"/);
  const oval = /<graphic[^>]*GraphicType="Oval"[^>]*OvalType="Circle"[^>]*\/>/.exec(text)?.[0] ?? "";
  const c = oval.match(/Center3D="([\d.]+) ([\d.]+)/)!, e = oval.match(/MajorAxisEnd3D="([\d.]+) ([\d.]+)/)!;
  // ChemDraw's radius for a six-membered ring at 18% bond spacing: 14.4 × (√3/2 − 0.18 × 4/3) = 9.02 pt.
  assert.ok(Math.abs(Number(e[1]) - Number(c[1]) - 14.4 * (Math.sqrt(3) / 2 - 0.18 * 4 / 3)) < 0.02, `circle radius: ${oval}`);
  const again = fromCdxml(text).mol;
  assert.deepEqual(again.bonds.map((x) => [x.type, x.display]), m.bonds.map((x) => [x.type, x.display]), "Kekulé bonds and the dashed double come back");
  assert.deepEqual([again.atoms.slice(0, 6).every((a) => a.circle), again.shapes], [true, undefined]);
  // ChemDraw's copy (Octet's own data dropped): the same drawing, the ring made Kekulé again.
  const plain = fromCdxml(text.replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "")).mol;
  assert.deepEqual([doubles(plain), plain.atoms.slice(0, 6).every((a) => a.circle), plain.shapes, plain.bonds[6].display], [4, true, undefined, "dashed"]);
  // The Aromatic double (both lines dashed): order 1.5 with Display and Display2 dashed, both ways; and ChemDraw reads
  // order 2 with a dashed Display as Aromatic too.
  const ar = { atoms: [A("C", 0, 0), A("C", 1, 0)], bonds: [b(0, 1, { type: 2, display: "aromatic" })] } as Mol;
  const arText = toCdxml(ar, DEFAULT_STYLE);
  assert.match(arText, /Order="1.5"\s+Display="Dash"\s+Display2="Dash"/);
  assert.deepEqual([fromCdxml(arText).mol.bonds[0].type, fromCdxml(arText).mol.bonds[0].display], [2, "aromatic"]);
  assert.equal(fromCdxml(arText.replace('Order="1.5"', 'Order="2"').replace(/\s+Display2="Dash"/, "")).mol.bonds[0].display, "aromatic");
  console.log("cdxml.check: delocalised rings, dashed and aromatic doubles ok");
}

// A shown carbon (ChemDraw's c key): its label goes out with its hydrogens and comes back as a shown carbon, so its
// hydrogens stay right when a bond is added. A hidden carbon stays hidden.
{
  const m = { atoms: [A("C", 0, 0, { shown: true }), A("C", 0.866, 0.5), A("C", 1.732, 0)], bonds: [b(0, 1), b(1, 2)] } as Mol;
  const text = toCdxml(m, DEFAULT_STYLE), again = fromCdxml(text).mol;
  assert.match(text, /NumHydrogens="3"/);
  assert.deepEqual(again.atoms.map((a) => [a.shown, a.text]), [[true, undefined], [undefined, undefined], [undefined, undefined]]);
  assert.equal(parse(serialize(m)).atoms[0].shown, true);
  console.log("cdxml.check: shown carbons ok");
}

// The document's chain angle goes out as ChemDraw's ChainAngle and comes back.
{
  const m = { atoms: [A("C", 0, 0), A("C", 1, 0)], bonds: [b(0, 1)] } as Mol;
  const text = toCdxml(m, readStyle({ ...DEFAULT_STYLE, chainAngle: 110 }));
  assert.match(text, /ChainAngle="110"/);
  assert.equal(fromCdxml(text).style.chainAngle, 110);
  assert.equal(fromCdxml(text.replace('ChainAngle="110"', "")).style.chainAngle, 120);
  console.log("cdxml.check: chain angle ok");
}

// Bonds come in in the order ChemDraw draws them (Z), so a bond brought to the front stays in front.
{
  const m = { atoms: [A("C", 0, -1), A("C", 0, 1), A("C", -1, 0), A("C", 1, 0)], bonds: [b(0, 1), b(2, 3)] } as Mol;
  const text = toCdxml(m, DEFAULT_STYLE), zs = [...text.matchAll(/<b\s+id="\d+"\s+Z="(\d+)"/g)].map((x) => x[1]);
  assert.equal(zs.length, 2);
  const swapped = text.replace(new RegExp(`Z="${zs[0]}"`), 'Z="ZA"').replace(new RegExp(`Z="${zs[1]}"`), `Z="${zs[0]}"`).replace('Z="ZA"', `Z="${zs[1]}"`);
  assert.deepEqual(fromCdxml(swapped.replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "")).mol.bonds.map((x) => x.atoms), [[2, 3], [0, 1]], "ChemDraw's file: by Z");
  console.log("cdxml.check: bond order ok");
}

// A structure drawn above a reaction arrow goes out as one of its step's objects above the arrow.
{
  const m = {
    atoms: [A("C", 0, 0), A("C", 1, 0), A("C", 6, 0), A("C", 7, 0), A("C", 3, 1.5), A("C", 4, 1.5)],
    bonds: [b(0, 1), b(2, 3), b(4, 5)],
    arrows: [{ id: 50, kind: "reaction", from: [2, 0], to: [5, 0] }],
  } as Mol;
  const text = toCdxml(m, DEFAULT_STYLE), frags = [...text.matchAll(/<fragment\s+id="(\d+)"/g)].map((x) => x[1]);
  assert.match(text, new RegExp(`ReactionStepObjectsAboveArrow="${frags[2]}"`));
  console.log("cdxml.check: structures above the arrow ok");
}

// REL-28: ChemDraw's annotations (GUIDs, Document Annotations) on the page and on groups are kept and written back,
// and are not reported as lost. One inside a fragment, which Octet cannot place, is.
{
  const chemdraw = `<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >
<CDXML BondLength="14.40"><page id="1" BoundingBox="0 0 540 720"><group id="2"><fragment id="3"><n id="4" p="100 100"/><n id="5" p="114.4 100"/><b id="6" B="4" E="5"/><annotation Keyword="Inner" Content="x"/></fragment><t id="7" p="100 130"><s font="3" size="10">Label</s></t><annotation Keyword="GUID" Content="0A1B-2C &amp; &quot;3&quot;"/></group><annotation Keyword="Fragment Label" Content="[II]"/><annotation Keyword="Name" Content="G-Protein (2)&#10;second line"/></page></CDXML>`;
  const read = fromCdxml(chemdraw);
  assert.deepEqual(read.lost, { annotation: 1 });
  assert.deepEqual(read.mol.annotations, [{ keyword: "Fragment Label", content: "[II]" }, { keyword: "Name", content: "G-Protein (2)\nsecond line" }]);
  assert.deepEqual(read.mol.groups?.[0].annotations, [{ keyword: "GUID", content: '0A1B-2C & "3"' }]);
  const text = toCdxml(read.mol, DEFAULT_STYLE);
  assert.match(text, /<annotation\s+Keyword="GUID"\s+Content="0A1B-2C &amp; &quot;3&quot;"\s+\/><\/group>/);
  assert.match(text, /<annotation\s+Keyword="Name"\s+Content="G-Protein \(2\)&#10;second line"\s+\/><\/page>/);
  const again = fromCdxml(text);
  assert.deepEqual([again.lost, again.mol.annotations, again.mol.groups?.[0].annotations], [{}, read.mol.annotations, read.mol.groups?.[0].annotations]);
  // Octet's own file keeps them too.
  const saved = parse(serialize(read.mol));
  assert.deepEqual([saved.annotations, saved.groups?.[0].annotations], [read.mol.annotations, read.mol.groups?.[0].annotations]);
  // Too long to hold: counted, not cut short.
  assert.deepEqual(fromCdxml(chemdraw.replace('Content="[II]"', `Content="${"x".repeat(10_001)}"`)).lost, { annotation: 2 });
  console.log("cdxml.check: annotations ok");
}

// Decision 0007: a structure, an arrow and a box at 200%, in a document at 250%. ChemDraw sees each object's own
// settings and the document's true sizes; Octet reads its own scales back exactly, and another program's from
// LineWidth when every width agrees with it.
{
  const m: Mol = {
    atoms: [A("C", 0, 0, { scale: 2 }), A("O", 1.732, 1, { scale: 2, size: 12 }), A("N", 3.464, 0, { scale: 2 }), A("C", 0, -3), A("C", 1, -3)],
    bonds: [b(0, 1), b(1, 2, { type: 2 }), b(3, 4)],
    arrows: [{ id: 1, kind: "reaction", from: [5, 0], to: [8, 0], scale: 2 }],
    shapes: [{ id: 2, kind: "box", from: [0, 4], to: [3, 2], scale: 2 }],
  };
  const text = toCdxml(m, DEFAULT_STYLE), bondsXml = text.match(/<b\s[^>]*\/>/g)!;
  for (const x of bondsXml.slice(0, 2)) assert.match(x, /BondLength="28.80"\s+LineWidth="1.20"\s+BoldWidth="4"\s+HashSpacing="5"\s+MarginWidth="3.20"/, "a scaled bond's own settings");
  assert.doesNotMatch(bondsXml[2], /LineWidth/, "a bond at 100% has none");
  assert.match(text, /<n\s[^>]*LabelSize="24"[^>]*><t\s[^>]*><s [^>]*size="24"[^>]*>O</, "the O label at its own 12 pt times 2");
  assert.match(text, /<arrow\s[^>]*LineWidth="1.20"\s+BoldWidth="4"/);
  assert.match(text, /<graphic\s[^>]*GraphicType="Rectangle"[^>]*LineWidth="1.20"\s+BoldWidth="4"/);
  const same = (x: Mol) => [x.atoms.map((a) => [a.scale, a.size]), x.arrows?.map((a) => a.scale), x.shapes?.map((s) => s.scale)];
  const want = [[[2, undefined], [2, 12], [2, undefined], [undefined, undefined], [undefined, undefined]], [2], [2]];
  assert.deepEqual(same(fromCdxml(text).mol), want, "Octet's own file: scales and the own label size back exactly");
  const chemdraw = fromCdxml(text.replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, ""));
  assert.deepEqual(same(chemdraw.mol), want, "ChemDraw's copy: scales from LineWidth");
  assert.deepEqual(chemdraw.lost, {});
  // The document's scale: true sizes for ChemDraw, the scale and the preset's name for Octet.
  const poster = withScale(DEFAULT_STYLE, 2.5), posterText = toCdxml(m, poster);
  assert.match(posterText, /LabelSize="25"[^>]*CaptionSize="25"\s+HashSpacing="6.25"\s+MarginWidth="4"\s+LineWidth="1.50"\s+BoldWidth="5"\s+BondLength="36"/);
  assert.deepEqual([fromCdxml(posterText).style.scale, fromCdxml(posterText).style.preset], [2.5, "ACS Document 1996"]);
  // Bonds whose settings do not give one scale keep 1, and keep the settings as they came, written back (REL-15): a
  // bond with only HashSpacing (Sam's files have them) and widths that disagree. A bond's own spacing is kept and drawn.
  const one = (attrs: string) => fromCdxml(`<CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2" HashSpacing="2.50" MarginWidth="1.60" BondSpacing="18"><page><fragment>
<n id="1" p="100 100"/><n id="2" p="114.4 100"/><b id="3" B="1" E="2" ${attrs}/></fragment></page></CDXML>`);
  const hashOnly = one(`BondLength="30" HashSpacing="2.70" BondSpacing="12"`);
  assert.deepEqual([hashOnly.mol.atoms.map((a) => a.scale), hashOnly.lost, hashOnly.mol.bonds[0].spacing, hashOnly.mol.bonds[0].own], [[undefined, undefined], {}, 12, { BondLength: "30", HashSpacing: "2.70" }]);
  const hashBack = toCdxml(hashOnly.mol, hashOnly.style).match(/<b\s[^>]*\/>/)![0];
  for (const a of ['BondLength="30"', 'HashSpacing="2.70"', 'BondSpacing="12"']) assert.ok(hashBack.includes(a), `written back: ${a}`);
  assert.deepEqual(parse(serialize(hashOnly.mol)).bonds[0], hashOnly.mol.bonds[0], "Octet's own file keeps them");
  const disagree = one(`LineWidth="1.20" BoldWidth="2"`);
  assert.deepEqual([disagree.lost, disagree.mol.bonds[0].own], [{}, { LineWidth: "1.20", BoldWidth: "2" }]);
  // A scaled structure writes its own settings from its scale, not the ones it came with.
  assert.doesNotMatch(toCdxml({ ...hashOnly.mol, atoms: hashOnly.mol.atoms.map((a) => ({ ...a, scale: 2 })) }, hashOnly.style), /HashSpacing="2.70"|BondLength="30"/);
  assert.deepEqual(one(`LineWidth="0.90" BoldWidth="3.02" HashSpacing="3.75"`).mol.atoms.map((a) => a.scale), [1.5, 1.5], "agreeing within 2%");
  // A TLC plate's widths: its scale from them, or listed once when they disagree (it was counted twice).
  const plate = (attrs: string) => fromCdxml(`<CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2"><page><tlcplate id="5" TopLeft="100 100" TopRight="200 100"
 BottomRight="200 300" BottomLeft="100 300" ${attrs}><tlclane id="6"><tlcspot id="7" Rf="0.5"/></tlclane></tlcplate></page></CDXML>`);
  assert.deepEqual([plate(`LineWidth="1.20" BoldWidth="4"`).mol.shapes?.[0].scale, plate(`LineWidth="1.20" BoldWidth="2"`).lost], [2, { "line settings": 1 }]);
  console.log("cdxml.check: scaled objects and the document scale ok");
}

// IDEA-SCALE-10: a ChemDraw drawing pasted or imported into one of other sizes keeps its text in proportion. A 24 pt
// caption beside 30 pt bonds lands at 11.52 pt beside 14.4 pt bonds (and the source's 12 pt default at 5.76 pt); an
// 8 pt label in a 16 pt-label drawing lands at 7 pt in a 14 pt one.
{
  const r = fromCdxml(`<CDXML BondLength="30" LabelSize="16" CaptionSize="12" LineWidth="1" BoldWidth="2" HashSpacing="2.50" MarginWidth="1.60" BondSpacing="18"><fonttable><font id="3" charset="iso-8859-1" name="Arial"/></fonttable><page><fragment>
<n id="1" p="100 100" Element="7"><t p="96 104"><s font="3" size="8" face="96">N</s></t></n><n id="2" p="130 100"/><b id="3" B="1" E="2"/></fragment>
<t id="4" p="100 160"><s font="3" size="24" face="0">Big caption</s></t><t id="5" p="100 200"><s font="3" size="12" face="0">Default caption</s></t></page></CDXML>`);
  const fit = fitSizes(r.mol, r.style, { ...DEFAULT_STYLE, labelSize: 14 });
  assert.deepEqual([fit.atoms.map((a) => a.size), fit.captions!.map((c) => c.size)], [[7, undefined], [11.52, 5.76]]);
  console.log("cdxml.check: paste sizes ok");
}

// REL-15: text ChemDraw turned (RotationAngle, clockwise on the page about p) keeps its turn, as degrees
// anticlockwise, and is written back as it came; a Bold rectangle or oval has its bold line (boldLine), written back
// as Bold.
{
  const chemdraw = `<CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2"><fonttable><font id="3" charset="iso-8859-1" name="Arial"/></fonttable><page>
<t id="1" p="74.30 410.83" RotationAngle="5898240"><s font="3" size="16.95" face="0">:</s></t><t id="2" p="200 200" RotationAngle="23527424"><s font="3" size="10" face="0">Os</s></t>
<graphic id="3" BoundingBox="321.60 349.48 396.92 327.34" GraphicType="Rectangle" RectangleType="RoundEdge Dashed Bold" Center3D="359.26 338.41 0" MajorAxisEnd3D="396.92 338.41 0" MinorAxisEnd3D="359.26 349.48 0"/>
<graphic id="4" BoundingBox="150 150 130 150" GraphicType="Oval" OvalType="Circle Bold" Center3D="130 150 0" MajorAxisEnd3D="150 150 0" MinorAxisEnd3D="130 170 0"/></page></CDXML>`;
  const r = fromCdxml(chemdraw);
  assert.deepEqual(r.lost, {});
  assert.deepEqual(r.mol.captions!.map((c) => c.angle), [-90, 1]);
  assert.deepEqual(r.mol.shapes!.map((s) => [s.kind, s.dashed, s.boldLine]), [["rounded", true, true], ["oval", undefined, true]]);
  const text = toCdxml(r.mol, r.style), ts = text.match(/<t\s[^>]*>/g)!;
  assert.match(ts[0], /RotationAngle="5898240"/);
  assert.match(ts[1], /RotationAngle="23527424"/);
  // The colon turned a quarter turn lies along the line: its box is wider than it is tall, and hangs from p.
  const [x0, y0, x1, y1] = ts[0].match(/BoundingBox="([^"]+)"/)![1].split(" ").map(Number);
  assert.ok(x1 - x0 > y1 - y0 && Math.abs(y0 - 410.83) < 0.01 && x0 < 74.3 && x1 > 80, "the box round the turned text");
  assert.match(text, /RectangleType="RoundEdge Dashed Bold"/);
  assert.match(text, /OvalType="Circle Bold"/);
  assert.doesNotMatch(text, /GraphicType="(Rectangle|Oval)"[^>]*LineWidth/, "Bold, not a line width");
  const again = fromCdxml(text);
  assert.deepEqual([again.lost, again.mol.captions!.map((c) => c.angle), again.mol.shapes!.map((s) => s.boldLine)], [{}, [-90, 1], [true, true]]);
  // Octet's own file keeps the turn; a turn past a whole turn makes the file damaged.
  assert.deepEqual(parse(serialize(r.mol)).captions!.map((c) => c.angle), [-90, 1]);
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, captions: [{ text: "a", x: 0, y: 0, angle: 400 }] })), /damaged/);
  // A plain line set to another width stays a line width.
  assert.match(toCdxml({ ...r.mol, shapes: r.mol.shapes!.map((s) => ({ ...s, boldLine: undefined, width: 1.5 })) }, r.style), /RectangleType="RoundEdge Dashed"[^>]*LineWidth="1.50"/);
  // A Bold shape with a bold width of its own that makes no scale keeps that width as its line width.
  const own = fromCdxml(chemdraw.replace('RectangleType="RoundEdge Dashed Bold"', 'RectangleType="RoundEdge Dashed Bold" LineWidth="0.60" BoldWidth="3"')).mol.shapes![0];
  assert.deepEqual([own.boldLine, own.width], [undefined, 3]);
  console.log("cdxml.check: turned text and bold shapes ok");
}

// REL-15: a rounded box's corner and a shadow's depth (ChemDraw's CornerRadius and ShadowSize, hundredths of the
// shape's line width: ChemDraw's CDGraphicRectangle draws ratio × line width) are kept, drawn and written back. Octet's
// own values stay unset. Conditions are written where Octet draws them: centred over a level arrow, one above the
// other, and their own alignment comes back in Octet.
{
  const chemdraw = `<CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2"><page>
<graphic id="1" BoundingBox="100 100 160 140" GraphicType="Rectangle" RectangleType="RoundEdge Shadow" CornerRadius="600" ShadowSize="400" Center3D="130 120 0" MajorAxisEnd3D="160 120 0" MinorAxisEnd3D="130 140 0"/>
<graphic id="2" BoundingBox="200 100 260 140" GraphicType="Rectangle" RectangleType="RoundEdge Shadow" CornerRadius="720" ShadowSize="288" Center3D="230 120 0" MajorAxisEnd3D="260 120 0" MinorAxisEnd3D="230 140 0"/>
<graphic id="3" BoundingBox="300 100 360 140" GraphicType="Rectangle" RectangleType="RoundEdge" CornerRadius="300" LineWidth="1.20" Center3D="330 120 0" MajorAxisEnd3D="360 120 0" MinorAxisEnd3D="330 140 0"/></page></CDXML>`;
  const r = fromCdxml(chemdraw), [own, octet, wide] = r.mol.shapes!;
  assert.deepEqual([own.radius, Math.round(own.shade!.depth * 1e4) / 1e4, octet.radius, octet.shade, wide.radius, wide.width], [0.25, 0.1667, undefined, undefined, 0.25, 1.2]);
  const back = toCdxml(r.mol, r.style), boxes = back.match(/<graphic\s[^>]*GraphicType="Rectangle"[^>]*>/g)!;
  assert.match(boxes[0], /CornerRadius="600"[^>]*ShadowSize="400"/);
  assert.match(boxes[1], /CornerRadius="720"[^>]*ShadowSize="288"/);
  assert.match(boxes[2], /CornerRadius="300"/);
  assert.deepEqual(parse(serialize(r.mol)).shapes!.map((s) => s.radius), [0.25, undefined, 0.25], "Octet's own file keeps the radius");
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "rounded", x1: 0, y1: 0, x2: 1, y2: 1, radius: -1 }] })), /damaged/);

  // Two conditions above a level arrow and one beside a steep arrow, as ChemDraw keeps them: left-justified.
  const steps = `<CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2" CaptionSize="10"><page>
<arrow id="10" ArrowheadHead="Full" ArrowheadType="Solid" Head3D="300 200 0" Tail3D="200 200 0"/>
<arrow id="11" ArrowheadHead="Full" ArrowheadType="Solid" Head3D="400 300 0" Tail3D="400 200 0"/>
<t id="12" p="210 190"><s size="10">first</s></t><t id="13" p="210 180"><s size="10">second</s></t><t id="14" p="380 250"><s size="10">steep</s></t>
<scheme id="20"><step id="21" ReactionStepArrows="10" ReactionStepObjectsAboveArrow="12 13"/><step id="22" ReactionStepArrows="11" ReactionStepObjectsAboveArrow="14"/></scheme></page></CDXML>`;
  const s = fromCdxml(steps), texts = (x: string) => x.match(/<t\s[^>]*>/g)!;
  assert.deepEqual(s.mol.captions!.map((c) => [c.on?.side, c.align]), [["above", "left"], ["above", "left"], ["above", "left"]]);
  const at = (t: string) => t.match(/ p="([^"]+)"/)![1].split(" ").map(Number), just = (t: string) => t.match(/ Justification="([^"]+)"/)?.[1];
  // ChemDraw placed them by hand: they keep their places and alignment through Octet, and in Octet's own file.
  const kept = toCdxml(s.mol, s.style);
  assert.deepEqual(texts(kept).map(at), [[210, 190], [210, 180], [380, 250]], "each where ChemDraw put it");
  assert.deepEqual(texts(kept).map(just), [undefined, undefined, undefined], "left-justified, as in the file");
  assert.deepEqual(fromCdxml(kept).mol.captions, s.mol.captions, "read back the same, still placed by hand");
  const four = (c: Caption) => c.placed && [...c.placed.at, ...c.placed.arrow].map((v) => Math.round(v * 1e4) / 1e4 + 0);
  assert.deepEqual(parse(serialize(s.mol)).captions!.map(four), s.mol.captions!.map(four), "Octet's own file keeps them");
  // Moved with their arrows, they keep their places by them.
  const moved = { ...s.mol, arrows: s.mol.arrows!.map((a) => ({ ...a, from: [a.from[0] + 1, a.from[1] - 2] as [number, number], to: [a.to[0] + 1, a.to[1] - 2] as [number, number] })) };
  assert.deepEqual(texts(toCdxml(moved, s.style)).map(at), [[224.4, 218.8], [224.4, 208.8], [394.4, 278.8]], "they go with their arrows");
  // Lengthened or turned, the arrows lay their conditions out as Octet draws them.
  const grown = { ...s.mol, arrows: s.mol.arrows!.map((a) => ({ ...a, to: [a.to[0] + 0.5 * Math.sign(a.to[0] - a.from[0]), a.to[1] - 0.5 * Math.sign(a.from[1] - a.to[1])] as [number, number] })) };
  const ts = texts(toCdxml(grown, s.style)), [first, second, steep] = ts.map(at);
  assert.deepEqual([first[0], second[0], ts.slice(0, 2).map(just)], [253.6, 253.6, ["Center", "Center"]], "centred over the level arrow's middle");
  assert.ok(second[1] < first[1] - 10, "the second sits a line above the first");
  assert.ok(steep[0] < 400 && just(ts[2]) === "Right" && Math.abs(steep[1] - 253.6) < 5, "ends left of the steep arrow, level with its middle");
  const again = fromCdxml(toCdxml(grown, s.style)).mol.captions!;
  assert.deepEqual([again.map((c) => c.align), again.map((c) => c.placed)], [["left", "left", "left"], [undefined, undefined, undefined]], "the conditions' own alignment comes back, laid out");
  // A new condition on the level arrow stacks past the two placed above it; one below starts at the arrow.
  const added = { ...s.mol, captions: [...s.mol.captions!, { id: 30, text: "new", x: 0, y: 0, on: { arrow: s.mol.arrows![0].id, side: "above" as const } }, { id: 31, text: "under", x: 0, y: 0, on: { arrow: s.mol.arrows![0].id, side: "below" as const } }] };
  const [, , , above, under] = texts(toCdxml(added, s.style)).map(at);
  assert.ok(above[0] === 250 && above[1] < 180 - 10 && under[1] > 200, "new text clears the text placed by hand");
  // Placed beside its arrow (render.ts placeCaptions): at its own place and alignment, and the arrow keeps its length.
  const one = (t: string) => t.length * 5, [drawn] = placeCaptions(s.mol, { ink: [], scale: 14.4 }, one, s.mol.arrows, 1, 10);
  assert.deepEqual([drawn.anchor, drawn.lines[0].x, drawn.lines[0].y].map((v) => (typeof v === "number" ? +v.toFixed(6) : v)), ["start", 210 - 270, 190 - 360]);
  const long = { ...s.mol, captions: [{ ...s.mol.captions![0], text: "a much longer line of conditions than the arrow" }] };
  assert.deepEqual(fitArrows(long, 14.4, (c) => c.text.length * 5, 1), long.arrows, "text placed by hand does not lengthen its arrow");
  assert.equal(placedAt(s.mol.captions![0], grown.arrows), undefined);
  console.log("cdxml.check: rounded corners, shadow depths and conditions as drawn ok");
}

// The grid: a file's grid step is one Settings offers, or the bond length (1e-20 mm once hung Octet, drawing a line
// per step); what the window shows (grid, rulers, crosshair) comes back from Octet's own data, checked as the rest is.
{
  const page = (octet: string) => fromCdxml(`<CDXML BondLength="14.4" Octet='${octet}'><page BoundingBox="0 0 540 720"/></CDXML>`);
  for (const grid of ["1e-20", "0.001", "-1", "7", "1e400", '"x"', "null"]) assert.equal(page(`{"v":1,"grid":${grid}}`).style.grid, "bond", grid);
  assert.equal(page('{"v":1,"grid":5}').style.grid, 5);
  assert.equal(page('{"v":1,"grid":6.35}').style.grid, 6.35);
  assert.deepEqual(page('{"v":1,"guides":{"grid":true,"rulers":true,"crosshair":[1.5,-2]}}').mol.guides, { grid: true, rulers: true, crosshair: [1.5, -2] });
  assert.deepEqual(page('{"v":1,"guides":{"grid":"yes","rulers":1,"crosshair":[1e99,0],"x":1}}').mol.guides, {});
  assert.equal(page('{"v":1}').mol.guides, undefined); // saved without them: the user's own choice applies
  assert.equal(page('{"v":2,"guides":{"grid":true}}').mol.guides, undefined); // not Octet's own data
  const shown = { grid: true as const, crosshair: [2, 3] as [number, number] };
  assert.deepEqual(fromCdxml(toCdxml({ atoms: [], bonds: [], guides: shown }, { ...DEFAULT_STYLE, grid: 10 })).mol.guides, shown);
  assert.deepEqual(fromCdxml(toCdxml({ atoms: [], bonds: [], guides: {} }, DEFAULT_STYLE)).mol.guides, {});
  console.log("cdxml.check: grid and guides ok");
}

// ChemDraw rounds an A4 page to 523 by 770 pt. Octet writes A4 exactly (523.28 by 769.89), and everything keeps its
// place from the page's top left corner.
{
  const a4 = fromCdxml(`<CDXML BondLength="14.40"><page BoundingBox="0 0 523 770"><fragment id="1"><n id="2" p="100 100"/><n id="3" p="114.40 100"/><b id="4" B="2" E="3"/></fragment></page></CDXML>`);
  const out = toCdxml(a4.mol, a4.style);
  assert.equal(a4.style.page, "A4");
  assert.match(out, /<page\s+id="\d+"\s+BoundingBox="0 0 523.28 769.89"/);
  assert.deepEqual([...out.matchAll(/<n\s+id="\d+"\s+p="([^"]+)"/g)].map((m) => m[1]), ["100 100", "114.40 100"]);
  console.log("cdxml.check: an A4 page's objects keep their places ok");
}

// Label anchors where Octet draws them. A label that reads right to left (here, its bond from the right) and has more
// than one glyph is right-justified, its p the right end of the label as Octet draws it: its ink ends as far right of
// the atom as it starts left of it read left to right, then any charge sign. One glyph stays Left, centred. Drawn
// here with Arial's advances and ink edges, the p written (to 0.01 pt) and the label drawn agree.
{
  // The labelled node's text p less its own p, and the label's justification.
  const anchor = (text: string): [number, string] => {
    const all = (x: Xml): Xml[] => [x, ...x.kids.flatMap(all)];
    const n = all(parseXml(text)).find((x) => x.name === "n" && x.kids.some((k) => k.name === "t"))!;
    const t = n.kids.find((k) => k.name === "t")!, p = n.attrs.p.split(" ").map(Number), q = t.attrs.p.split(" ").map(Number);
    return [q[0] - p[0], t.attrs.LabelJustification];
  };
  const PT = 4 / 3, S = { bond: 14.4 * PT, line: 0.6 * PT, bold: 2 * PT, spacing: 0.18 * 14.4 * PT, hash: 2.5 * PT, margin: 1.69 * PT, size: 10 * PT };
  const glyph = (ch: string) => arialGlyph(ch).map((v) => (v * S.size) / 1000);
  const arial = (text: string): Ink => {
    const outline: [number, number][] = [];
    let x = 0;
    for (const ch of text) { const [w, l, r] = glyph(ch); for (let k = 0; k <= 4; k++) outline.push([x + l + ((r - l) * k) / 4, 0], [x + l + ((r - l) * k) / 4, -0.716 * S.size]); x += w; }
    return { width: x, ascent: 0.716 * S.size, outline };
  };
  const cases: [Partial<Atom> & { label: string }, string][] = [
    [{ label: "Br" }, "Right"], [{ label: "Cl" }, "Right"], [{ label: "C", text: "Ph" }, "Right"], [{ label: "C", text: "Me" }, "Right"],
    [{ label: "Si", text: "TMS" }, "Right"], [{ label: "Si", text: "SiMe3" }, "Right"], [{ label: "C", text: "R1" }, "Right"], [{ label: "C", text: "CF3" }, "Right"],
    [{ label: "O", text: "OMe" }, "Right"], [{ label: "O" }, "Right"], [{ label: "N" }, "Right"], [{ label: "C", text: "CO2Me" }, "Right"],
    [{ label: "O", charge: -1 }, "Left"], [{ label: "C", isotope: 13 }, "Right"], [{ label: "C", text: "[N,O]" }, "Right"], [{ label: "O", implicitHCount: 0 }, "Left"],
  ];
  for (const [atom, just] of cases) {
    const mol: Mol = { atoms: [A(atom.label, 0, 0, atom), A("C", 1, 0)], bonds: [b(0, 1)] };
    const [dx, j] = anchor(toCdxml(mol, DEFAULT_STYLE)), name = `${atom.text ?? atom.label}${atom.charge ? "-" : ""}`;
    // Octet's drawing: the label's runs (the charge sign apart, as ChemDraw sizes its own), in pt from the atom.
    const runs = render(mol, S, arial).labels.filter((l) => !/^\d*[+–]$/.test(l.text) || !atom.charge);
    const sign = atom.charge ? (333 * 7.5) / 1000 : 0;
    const drawn = just === "Right" ? Math.max(...runs.map((l) => l.x + [...l.text].reduce((w, ch) => w + glyph(ch)[0], 0) * (l.size / S.size))) / PT + sign : Math.min(...runs.map((l) => l.x)) / PT;
    assert.ok(Math.abs(dx - drawn) <= 0.0051 && j === just, `${name}: ${just} at ${drawn.toFixed(3)} as drawn (${j} at ${dx.toFixed(3)})`);
  }
  // ChemDraw's right-justified Br opens on its atom, and goes back right-justified where Octet draws it.
  const cd = fromCdxml(`<CDXML BondLength="14.40"><page BoundingBox="0 0 540 720"><fragment id="1"><n id="2" p="200 200" Element="35"><t p="201.66 203.58" LabelJustification="Right" Justification="Right"><s font="3" size="10" face="96">Br</s></t></n><n id="3" p="212.47 192.8"/><b id="4" B="2" E="3"/></fragment></page></CDXML>`);
  assert.ok(Math.abs(cd.mol.atoms[0].location[0] - (200 - 270) / 14.4) < 1e-9 && Math.abs(cd.mol.atoms[0].location[1] - (360 - 200) / 14.4) < 1e-9, "the Br sits at its node");
  const [dx, j] = anchor(toCdxml(cd.mol, cd.style)), want = (667 / 2 - arialGlyph("B")[1] + 333 - arialGlyph("r")[2]) / 100;
  assert.ok(Math.abs(dx - want) <= 0.0051 && j === "Right", `and goes back right-justified at ${want.toFixed(3)} pt (${dx.toFixed(3)})`);
  console.log("cdxml.check: label anchors ok");

  // ChemDraw's own justification wins where Octet's automatic one would draw the label another way: a centred Mn
  // between bonds both sides, Ph left-justified on a bond from the right, OH right-justified (HO) on a steep bond, NH
  // stacked above on bonds going up. Where both draw it alike it stays automatic: a lone N, OMe read left to right,
  // H3C (its H first either way), and NH stacked below its bonds as Octet stacks it.
  const label = (id: number, x: number, y: number, more: string, text: string, just: string, stack = "") =>
    `<n id="${id}" p="${x} ${y}" ${more}><t p="${x} ${y}" LabelJustification="${just}"${stack && ` LabelAlignment="${stack}"`}><s font="3" size="10" face="96">${text}</s></t></n>`;
  const node = (id: number, x: number, y: number) => `<n id="${id}" p="${x} ${y}"/>`, bond = (id: number, p: number, q: number) => `<b id="${id}" B="${p}" E="${q}"/>`;
  const justified = fromCdxml(`<CDXML BondLength="14.40"><page BoundingBox="0 0 540 720"><fragment id="1">
${label(2, 100, 100, 'Element="25" NumHydrogens="0"', "Mn", "Center")}${node(3, 85.6, 100)}${node(4, 114.4, 100)}${bond(5, 2, 3)}${bond(6, 2, 4)}
${label(7, 200, 100, "", "Ph", "Left", "Left")}${node(8, 214.4, 100)}${bond(9, 7, 8)}
${label(10, 300, 100, 'Element="8" NumHydrogens="1"', "OH", "Right", "Right")}${node(11, 303, 114.1)}${bond(12, 10, 11)}
${label(13, 400, 100, 'Element="7" NumHydrogens="1"', "NH", "Left", "Above")}${node(14, 387.5, 92.8)}${node(15, 412.5, 92.8)}${bond(16, 13, 14)}${bond(17, 13, 15)}
${label(18, 100, 200, 'Element="7" NumHydrogens="2"', "N", "Left")}${node(19, 114.4, 200)}${bond(20, 18, 19)}
${label(21, 200, 200, "", "OMe", "Left")}${node(22, 185.6, 200)}${bond(23, 21, 22)}
${label(24, 300, 200, 'NumHydrogens="3"', "H3C", "Left")}${node(25, 314.4, 200)}${bond(26, 24, 25)}
${label(27, 400, 200, 'Element="7" NumHydrogens="1"', "NH", "Left", "Below")}${node(28, 387.5, 192.8)}${node(29, 412.5, 192.8)}${bond(30, 27, 28)}${bond(31, 27, 29)}
</fragment></page></CDXML>`);
  const aligned = (m: Mol) => m.atoms.map((a, i) => [a.text ?? a.label, a.align]).filter((_, i) => [0, 3, 5, 7, 10, 12, 14, 16].includes(i));
  assert.deepEqual(aligned(justified.mol), [["Mn", "centre"], ["Ph", "left"], ["O", "right"], ["N", "above"], ["N", undefined], ["OMe", undefined], ["C", undefined], ["N", undefined]]);
  const written = toCdxml(justified.mol, justified.style), back = fromCdxml(written);
  assert.deepEqual(aligned(back.mol), aligned(justified.mol), "kept through Octet's file");
  assert.match(written, /LabelDisplay="Center"[^>]*>[^]*?LabelJustification="Center"/);
  // Drawn centred: the Mn's two letters sit either side of its atom.
  const drawn = render(justified.mol, S, arial), mn = drawn.labels.find((l) => l.text === "Mn")!;
  assert.ok(Math.abs(mn.x + arial("Mn").width / 2 - drawn.labelAt[drawn.labels.indexOf(mn)][0]) < 1e-9, "Mn centred on its atom");
  console.log("cdxml.check: label justification from ChemDraw ok");

  // A turned label (RotationAngle, 359° clockwise: 1° anticlockwise) keeps its turn: read, drawn turned about its
  // anchor, written back and kept in Octet's own file.
  const turnedFile = fromCdxml(`<CDXML BondLength="14.40"><page BoundingBox="0 0 540 720"><fragment id="1">
<n id="2" p="100 100" Element="76" NumHydrogens="0"><t p="100.06 103.58" LabelJustification="Center" RotationAngle="23527424"><s font="3" size="10" face="96">Os</s></t></n>${node(3, 85.6, 100)}${node(4, 114.4, 100)}${bond(5, 2, 3)}${bond(6, 2, 4)}
</fragment></page></CDXML>`);
  assert.deepEqual([turnedFile.mol.atoms[0].labelAngle, turnedFile.mol.atoms[0].align], [1, "centre"]);
  const os = toCdxml(turnedFile.mol, turnedFile.style);
  assert.match(os, /RotationAngle="23527424"/);
  assert.equal(fromCdxml(os).mol.atoms[0].labelAngle, 1);
  assert.equal(parse(serialize(turnedFile.mol)).atoms[0].labelAngle, 1);
  const turnedDrawing = render(turnedFile.mol, S, arial), osLabel = turnedDrawing.labels.find((l) => l.text === "Os")!;
  assert.ok(osLabel.angle === 1 && Math.abs(osLabel.pivot![0] - turnedDrawing.labelAt[turnedDrawing.labels.indexOf(osLabel)][0]) < 1e-9, "drawn turned about the middle of its line");
  assert.equal(render({ ...turnedFile.mol, atoms: turnedFile.mol.atoms.map((a) => ({ ...a, labelAngle: undefined })) }, S, arial).labels.find((l) => l.text === "Os")!.angle, undefined);
  console.log("cdxml.check: label turns ok");
}

// A label's charge sign that Octet draws anywhere but after the label goes to ChemDraw as a Plus or Minus symbol linked
// to its atom, where Octet draws it, and the label's text has no sign (spec 9.10): a diazo group's N+ whose N=N bond
// leaves through the place after the N (Octet draws ⁺N), and an O⁻ read right to left (⁻O). A sign with room after the
// label stays in the text (the N⁻). Each reads back as the same charges.
{
  const all = (x: Xml): Xml[] => [x, ...x.kids.flatMap(all)];
  const written = (mol: Mol) => {
    const root = parseXml(toCdxml(mol, DEFAULT_STYLE)), nodes = all(root).filter((x) => x.name === "n");
    const text = (n: Xml) => all(n.kids.find((k) => k.name === "t")!).map((k) => k.text ?? "").join("");
    const symbols = all(root).filter((x) => x.name === "graphic" && x.attrs.GraphicType === "Symbol").map((g) => ({ type: g.attrs.SymbolType, at: g.attrs.BoundingBox.split(" ").slice(0, 2).map(Number), node: nodes.find((n) => n.attrs.id === g.kids.find((k) => k.name === "represent" && k.attrs.attribute === "Charge")?.attrs.object) }));
    return { nodes, text, symbols, back: fromCdxml(toCdxml(mol, DEFAULT_STYLE)).mol };
  };
  // C=N+=N- going up and to the right at 60°, as Clean Up leaves Sam's diazo ester.
  const diazo: Mol = { atoms: [A("C", 0, 0), A("N", 0.5, 0.866, { charge: 1 }), A("N", 1, 1.732, { charge: -1 }), A("C", -1, 0), A("C", 0.5, -0.866)], bonds: [b(0, 1, { type: 2 }), b(1, 2, { type: 2 }), b(0, 3), b(0, 4)] };
  const w = written(diazo), [plus, minus] = [w.nodes[1], w.nodes[2]], p = plus.attrs.p.split(" ").map(Number);
  assert.deepEqual([w.text(plus), w.text(minus)], ["N", "N-"], "N+ keeps no sign in its text; N- keeps its own");
  assert.equal(w.symbols.length, 1);
  assert.ok(w.symbols[0].type === "Plus" && w.symbols[0].node === plus && w.symbols[0].at[0] < p[0] && w.symbols[0].at[1] < p[1], "a Plus symbol for the N+, at its upper left");
  assert.deepEqual(w.back.atoms.map((a) => a.charge), [undefined, 1, -1, undefined, undefined], "the charges read back");
  // O- on a bond from the right reads right to left: its sign goes before it, as a Minus symbol at its upper left.
  const oxide = written({ atoms: [A("O", 0, 0, { charge: -1 }), A("C", 1, 0)], bonds: [b(0, 1)] }), o = oxide.nodes[0].attrs.p.split(" ").map(Number);
  assert.ok(oxide.text(oxide.nodes[0]) === "O" && oxide.symbols.length === 1 && oxide.symbols[0].type === "Minus" && oxide.symbols[0].at[0] < o[0] && oxide.symbols[0].at[1] < o[1], "-O: a Minus symbol at its upper left");
  assert.equal(oxide.back.atoms[0].charge, -1);
  const after = written({ atoms: [A("C", 0, 0), A("O", 1, 0, { charge: -1 })], bonds: [b(0, 1)] });
  assert.ok(after.text(after.nodes[1]) === "O-" && !after.symbols.length, "O- read left to right keeps its sign in the text");
  console.log("cdxml.check: moved charge signs ok");
}

// Measured spectra as ChemDraw's spectrum object (decision 0016): written as ChemDraw 26.1 writes one, read back when
// ChemDraw has saved over the file, and read from ChemDraw's own, with its spectrum-structure assignments.
{
  const N = 4000, lorentz = (x: number, lines: number[][], w: number) => lines.reduce((s, [p, h]) => s + (h * w * w) / ((x - p) ** 2 + w * w), 0);
  const y = Float64Array.from({ length: N }, (_, i) => lorentz(10 - (12 * i) / (N - 1), [[7.26, 0.3], [4.12, 1], [1.26, 1.5]], 0.01));
  const h1 = fromJcamp({ title: "Ethyl ester", kind: "nmr", nucleus: "1H", mhz: 400.13, solvent: "CDCl₃", xUnit: "ppm", yUnit: "", first: 10, last: -2, y }, 1);
  const near = (m: Measured, at: number) => m.groups.find((g) => g.lo <= at && at <= g.hi)!.id;
  const doc: Mol = { atoms: [A("C", 0, 0, { peaks: [near(h1, 4.12)] }), A("C", 1, 0, { peaks: [near(h1, 1.26)] }), A("O", 2, 0)], bonds: [b(0, 1), b(0, 2, { peaks: [near(h1, 4.12)] })], spectra: [h1] };
  const text = toCdxml(doc, DEFAULT_STYLE), root = parseXml(text);
  const every = (x: Xml): Xml[] => [x, ...x.kids.flatMap(every)];
  const sp = every(root).find((x) => x.name === "spectrum")!, values = sp.text.trim().split(/\s+/).map(Number), lines = sp.text.trim().split("\n");
  // An even grid low to high (the trace ran high to low), in the units and class ChemDraw names, 16 values a line.
  assert.deepEqual([sp.attrs.XLow, sp.attrs.Class, sp.attrs.XType, sp.attrs.YType], ["-2", "NMR", "PartsPerMillion", "ArbitraryUnits"]);
  assert.ok(Math.abs(Number(sp.attrs.XSpacing) - 12 / (N - 1)) < 1e-12 && values.length === N && lines.every((l, k) => l.split(" ").length === (k < lines.length - 1 ? 16 : N % 16 || 16)));
  assert.ok(values.every((v) => Number.isInteger(v) && v >= 0 && v <= 65535));
  // Each value times YScale plus YLow is the trace, low x first.
  const scale = Number(sp.attrs.YScale), low = Number(sp.attrs.YLow ?? 0);
  assert.ok(values.every((v, k) => Math.abs(v * scale + low - h1.y[N - 1 - k]) < scale), "the values are the trace");
  // The assignment: a /CS/CD/assign tag with the multiplet's range on the atom and on the spectrum, and Octet's own tag.
  const tags = (x: Xml, name: string) => x.kids.filter((k) => k.name === "objecttag" && k.attrs.Name === name);
  const nodes = every(root).filter((x) => x.name === "n"), quartet = h1.groups.find((g) => g.id === near(h1, 4.12))!;
  assert.deepEqual(tags(nodes[0], "/CS/CD/assign").map((t) => [t.attrs.TagType, t.attrs.Value]), [["String", `${+quartet.lo.toPrecision(12)}-${+quartet.hi.toPrecision(12)},`]]);
  assert.equal(tags(nodes[2], "/CS/CD/assign").length, 0);
  // A bond linked to a multiplet carries the same tag (as ChemDraw puts one on each atom and bond selected).
  const bondsOut = every(root).filter((x) => x.name === "b");
  assert.deepEqual([tags(bondsOut[0], "/CS/CD/assign").length, tags(bondsOut[1], "/CS/CD/assign")[0]?.attrs.Value], [0, tags(nodes[0], "/CS/CD/assign")[0].attrs.Value]);
  assert.deepEqual(tags(sp, "/CS/CD/assign").map((t) => t.attrs.Value).sort(), [...nodes.slice(0, 2).map((n) => tags(n, "/CS/CD/assign")[0].attrs.Value)].sort());
  assert.ok(/^[\x20-\x7e]+$/.test(tags(sp, "Octet spectrum")[0].attrs.Value), "Octet's tag is ASCII");
  // ChemDraw saves over it (Octet's attributes gone, its tags kept): the spectrum comes back with its details, its
  // multiplets, its place, and the links.
  const resaved = text.replace(/\n Octet="[^"]*"/g, ""), back = fromCdxml(resaved), m = back.mol.spectra![0];
  assert.deepEqual(back.lost, {});
  assert.deepEqual([m.title, m.kind, m.nucleus, m.mhz, m.solvent, m.xUnit, m.y.length], ["Ethyl ester", "nmr", "1H", 400.13, "CDCl₃", "ppm", N]);
  const ranges = (x: Measured) => x.groups.map((g) => [+g.lo.toFixed(9), +g.hi.toFixed(9)]).sort((p, q) => p[0] - q[0]);
  assert.deepEqual(ranges(m), ranges(h1));
  assert.deepEqual(back.mol.atoms.map((a) => a.peaks?.map((k) => +((m.groups.find((g) => g.id === k)!.lo + m.groups.find((g) => g.id === k)!.hi) / 2).toFixed(1))), [[4.1], [1.3], undefined]);
  assert.deepEqual(back.mol.bonds.map((x) => x.peaks), [undefined, back.mol.atoms[0].peaks]);
  const shifts = (x: Measured) => analyse(x).groups.map((g) => g.shift.toFixed(3)).sort();
  assert.deepEqual(shifts(m), shifts(h1));
  parse(serialize(back.mol));
  // Pasted into another drawing, the file brings no spectrum, so its atoms and bonds keep no links (ids that would
  // name the other drawing's multiplets).
  const pasted = insertMol({ atoms: [], bonds: [], spectra: [h1] }, back.mol).mol;
  assert.ok([...pasted.atoms, ...pasted.bonds].every((x) => !x.peaks) && pasted.spectra?.[0] === h1);
  // Written again, it is where it was, the same object.
  const again = toCdxml(back.mol, DEFAULT_STYLE), sp2 = every(parseXml(again)).find((x) => x.name === "spectrum")!;
  assert.deepEqual([sp2.attrs.BoundingBox, sp2.attrs.XLow, sp2.attrs.XSpacing, sp2.text], [sp.attrs.BoundingBox, sp.attrs.XLow, sp.attrs.XSpacing, sp.text]);

  // ChemDraw's own: an IR spectrum in %T as whole numbers of YScale above YLow (no Octet tag), a carbonyl band assigned
  // to the C=O bond's carbon and oxygen by ChemDraw's peak range.
  const ir = Array.from({ length: 1801 }, (_, i) => 100 - lorentz(400 + 2 * i, [[1740, 80], [2980, 20]], 10));
  const lo = Math.min(...ir), sc = (Math.max(...ir) - lo) / 10000, ints = ir.map((v) => Math.round((v - lo) / sc));
  const rows = Array.from({ length: Math.ceil(ints.length / 16) }, (_, k) => ints.slice(16 * k, 16 * k + 16).join(" ")).join("\n");
  const tag = (v: string) => `<objecttag id="90" TagType="String" Name="/CS/CD/assign" Value="${v}"/>`;
  const cd = `<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40"><page id="1" BoundingBox="0 0 540 720"><fragment id="2"><n id="3" p="100 100">${tag("1738.5-1741.5,")}</n><n id="4" p="114.4 100" Element="8">${tag("1738.5-1741.5,")}</n><b id="5" B="3" E="4" Order="2">${tag("1738.5-1741.5,")}</b></fragment>` +
    `<spectrum id="6" BoundingBox="50 200 350 350" Z="9" XSpacing="2" XLow="400" XType="Wavenumbers" YType="PercentTransmittance" Class="Infrared" YLow="${lo}" YScale="${sc}">${rows}${tag("1738.5-1741.5,")}</spectrum></page></CDXML>`;
  const read = fromCdxml(cd), s = read.mol.spectra![0];
  assert.deepEqual(read.lost, {});
  // ChemDraw's grid runs from 400 up; the dips are the peaks.
  assert.deepEqual([s.kind, s.xUnit, s.yUnit, s.first, s.last, s.y.length], ["ir", "cm⁻¹", "%T", 400, 4000, 1801]);
  assert.equal(measuredText(s, analyse(s)), "IR ν̃ 2980, 1740 cm⁻¹.");
  const band = read.mol.atoms[0].peaks!;
  assert.equal(band.length, 1);
  assert.deepEqual(read.mol.atoms[1].peaks, band);
  assert.deepEqual(read.mol.bonds[0].peaks, band);
  assert.ok(s.groups.some((g) => g.id === band[0] && g.lo < 1740 && 1740 < g.hi && !g.manual), "the band at 1740");
  // Written back, it is where ChemDraw had it.
  assert.equal(every(parseXml(toCdxml(read.mol, read.style))).find((x) => x.name === "spectrum")!.attrs.BoundingBox, "50 200 350 350");

  // Hostile: no grid, a word that is not a number, an endless value, too many points: each spectrum is lost alone.
  const one = (attrs: string, body: string) => fromCdxml(`<CDXML BondLength="14.40"><page id="1" BoundingBox="0 0 540 720"><spectrum id="2" ${attrs}>${body}</spectrum><t id="3" p="10 10"><s font="3" size="10">kept</s></t></page></CDXML>`);
  for (const [attrs, body] of [["XLow=\"0\"", "1 2 3"], ["XLow=\"0\" XSpacing=\"0\"", "1 2 3"], ["XLow=\"0\" XSpacing=\"1\"", "1 two 3"], ["XLow=\"0\" XSpacing=\"1\"", "1 1e999 3"], ["XLow=\"0\" XSpacing=\"1\"", ""], ["XLow=\"0\" XSpacing=\"1\" YScale=\"1e400\"", "1 2 3"]]) {
    const r = one(attrs, body);
    assert.deepEqual([r.lost, r.mol.spectra, r.mol.captions?.[0].text], [{ spectrum: 1 }, undefined, "kept"], `${attrs} ${body}`);
  }
  assert.deepEqual(one("XLow=\"0\" XSpacing=\"1\"", "0 ".repeat((1 << 21) + 1)).lost, { spectrum: 1 });
  // A second spectrum of a kind Octet holds one of is lost; an assignment with no spectrum is lost.
  const two = fromCdxml(`<CDXML BondLength="14.40"><page id="1" BoundingBox="0 0 540 720"><spectrum id="2" XLow="0" XSpacing="1" Class="Infrared">1 2 1</spectrum><spectrum id="3" XLow="0" XSpacing="1" Class="Infrared">1 3 1</spectrum><fragment id="4"><n id="5" p="10 10">${tag("1-2,")}${tag("9000-9001,")}</n></fragment></page></CDXML>`);
  assert.deepEqual([two.mol.spectra!.length, two.lost], [1, { spectrum: 1, "spectrum assignment": 1 }]);
  assert.equal(two.mol.atoms[0].peaks?.length, 1);
  console.log("cdxml.check: spectra as ChemDraw's spectrum object ok");
}

// File fidelity: tritium (T) is hydrogen-3 as D is hydrogen-2; an atom number ChemDraw keeps hidden stays hidden.
{
  const every = (x: Xml): Xml[] => [x, ...x.kids.flatMap(every)];
  const m: Mol = { atoms: [A("C", 0, 0, { number: "1" }), A("T", 1, 0, { hiddenNumber: "2" }), A("D", -1, 0), A("C", 0, 1, { text: "CT3" })], bonds: [b(0, 1), b(0, 2), b(0, 3)] };
  // CT3 drawn out (as Octet expands a label it knows): its carbon and three tritium atoms.
  const ct3: Mol = { atoms: [A("C", 0, 0), A("T", 1, 0), A("T", -1, 0), A("T", 0, 1)], bonds: [b(0, 1), b(0, 2), b(0, 3)] };
  const nodes = every(parseXml(toCdxml(m, DEFAULT_STYLE, { expand: (t) => (t === "CT3" ? ct3 : undefined) }))).filter((x) => x.name === "n" && x.attrs.NodeType !== "ExternalConnectionPoint");
  const text = (n: Xml) => every(n).filter((k) => k.name === "s").map((k) => k.text).join("");
  assert.deepEqual([nodes[1].attrs.Element, nodes[1].attrs.Isotope, text(nodes[1]), nodes[2].attrs.Element, nodes[2].attrs.Isotope], ["1", "3", "T", "1", "2"]);
  assert.deepEqual(nodes.filter((n) => n.attrs.Isotope === "3").length, 4, "T and the CT3 label's three tritium atoms");
  assert.deepEqual([nodes[0].attrs.AtomNumber, nodes[0].attrs.ShowAtomNumber, nodes[1].attrs.AtomNumber, nodes[1].attrs.ShowAtomNumber], ["1", "yes", "2", undefined]);
  const back = fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol;
  assert.deepEqual(back.atoms.slice(0, 3).map((a) => [a.label, a.isotope, a.number, a.hiddenNumber]), [["C", undefined, "1", undefined], ["T", undefined, undefined, "2"], ["D", undefined, undefined, undefined]]);
  assert.equal(back.atoms[3].text, "CT3");
  // ChemDraw's own: a T label on hydrogen-3, and AtomNumber with no ShowAtomNumber (as Name to Structure leaves them).
  const cd = fromCdxml(`<CDXML BondLength="14.40"><page id="1"><fragment id="2"><n id="3" p="100 100" AtomNumber="0"/><n id="4" p="114.4 100" Element="1" Isotope="3" NumHydrogens="0" AtomNumber="1"><t p="111 104"><s font="3" size="10" face="96">T</s></t></n><b id="5" B="3" E="4"/></fragment></page></CDXML>`);
  assert.deepEqual(cd.lost, {});
  assert.deepEqual(cd.mol.atoms.map((a) => [a.label, a.text, a.isotope, a.number, a.hiddenNumber]), [["C", undefined, undefined, undefined, "0"], ["T", undefined, undefined, undefined, "1"]]);
  assert.deepEqual(parse(serialize(cd.mol)).atoms.map((a) => a.hiddenNumber), ["0", "1"]);
  console.log("cdxml.check: tritium and hidden atom numbers ok");
}

// Labels of more than one line (ChemDraw's Option-Return in a label): one text with the line break in it, LineStarts
// where each line ends (as ChemDraw writes "8 14" for "Direct,\nNo ISC"), justified as Octet lines them up, and read
// back with their lines. A charge goes after the attaching line. ChemDraw's own reads the same, and a stacked NH typed
// with a break (N, Option-Return, H) is still N with its hydrogen.
{
  const every = (x: Xml): Xml[] => [x, ...x.kids.flatMap(every)];
  const m: Mol = { atoms: [A("C", 0, 0, { text: "Direct,\nNo ISC", align: "centre" }), A("C", 1, 0), A("N", 3, 0, { text: "NMe3\nsalt", charge: 1 }), A("C", 4, 0), A("C", 6, 0, { text: "Ab\nCd", align: "above" })], bonds: [b(0, 1), b(2, 3)] };
  const xml = toCdxml(m, DEFAULT_STYLE), ts = every(parseXml(xml)).filter((x) => x.name === "n").map((n) => n.kids.find((k) => k.name === "t")!);
  const text = (t: Xml) => t.kids.filter((k) => k.name === "s").map((k) => k.text).join("");
  assert.deepEqual([text(ts[0]), ts[0].attrs.LineStarts, ts[0].attrs.LabelJustification, ts[0].attrs.Justification], ["Direct,\nNo ISC", "8 14", "Center", "Center"]);
  const box = ts[0].attrs.BoundingBox.split(" ").map(Number);
  assert.ok(box[3] - box[1] > 1.2 * 10 + 7, `the box holds both lines (${box[3] - box[1]} pt)`);
  // p is on the first line's baseline, a line above the second.
  assert.ok(Number(ts[0].attrs.p.split(" ")[1]) < box[1] + 10, "p on the first baseline");
  // NMe3, then salt: the bond comes from the right, so the lines end together, right-justified, and the sign Octet
  // draws before the first line is a symbol, as for a one-line label read right to left.
  assert.deepEqual([text(ts[2]), ts[2].attrs.LineStarts, ts[2].attrs.LabelJustification], ["NMe3\nsalt", "5 9", "Right"]);
  // Read left to right, the sign follows the first line in the text.
  const plus = toCdxml({ atoms: [A("N", 3, 0, { text: "NMe3\nsalt", charge: 1 }), A("C", 2, 0)], bonds: [b(0, 1)] }, DEFAULT_STYLE);
  assert.equal(text(every(parseXml(plus)).find((x) => x.name === "t")!), "NMe3+\nsalt");
  assert.deepEqual([fromCdxml(plus).mol.atoms[0].text, fromCdxml(plus).mol.atoms[0].charge], ["NMe3\nsalt", 1]);
  assert.deepEqual([text(ts[4]), ts[4].attrs.LabelAlignment, ts[4].attrs.LabelJustification], ["Ab\nCd", "Above", "Center"]);
  const back = fromCdxml(xml);
  assert.deepEqual(back.lost, {});
  assert.deepEqual([0, 2, 4].map((i) => [back.mol.atoms[i].text, back.mol.atoms[i].align, back.mol.atoms[i].charge]), [["Direct,\nNo ISC", "centre", undefined], ["NMe3\nsalt", undefined, 1], ["Ab\nCd", "above", undefined]]);
  // Through CDX (where a line break is a carriage return) and Octet's own file.
  const viaCdx = fromCdxml(cdxToXml(xmlToCdx(parseXml(xml)))).mol;
  assert.deepEqual([0, 2, 4].map((i) => viaCdx.atoms[i].text), ["Direct,\nNo ISC", "NMe3\nsalt", "Ab\nCd"]);
  assert.deepEqual(parse(serialize(back.mol)).atoms[0].text, "Direct,\nNo ISC");
  const bad = JSON.parse(serialize(back.mol));
  for (const t of ["\nA", "A\n", "A\n\nB", "A\rB"]) { bad.structure.atoms[0].text = t; assert.throws(() => parse(JSON.stringify(bad)), /damaged/, JSON.stringify(t)); }
  // ChemDraw's own: the corpus label's text and runs (two colours), and a stacked NH typed with a break.
  const cd = fromCdxml(`<CDXML BondLength="14.40"><colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/><color r="1" g="0" b="0"/></colortable><page id="1"><fragment id="2"><n id="3" p="221.96 317.74" NodeType="Unspecified" LabelDisplay="Center"><t p="221.96 313.25" LabelJustification="Center" LabelAlignment="Left" LineStarts="8 14"><s font="3" size="10" color="3" face="3">Direct,
No</s><s font="3" size="10" color="4" face="3"> ISC</s></t></n></fragment><fragment id="4"><n id="5" p="300 300" Element="7" NumHydrogens="1"/><n id="6" p="314.4 300"/><n id="7" p="285.6 300"/><b id="8" B="5" E="6"/><b id="9" B="5" E="7"/></fragment></page></CDXML>`.replace('<n id="5" p="300 300" Element="7" NumHydrogens="1"/>', '<n id="5" p="300 300" Element="7" NumHydrogens="1"><t p="297 303" LabelJustification="Left" LabelAlignment="Below"><s font="3" size="10" face="96">N\nH</s></t></n>'));
  assert.deepEqual([cd.mol.atoms[0].text, cd.mol.atoms[0].bold, cd.mol.atoms[0].italic, cd.mol.atoms[0].align], ["Direct,\nNo ISC", true, true, "centre"]);
  assert.deepEqual([cd.mol.atoms[1].label, cd.mol.atoms[1].text], ["N", undefined]);
  const CORPUS = join(homedir(), "octet-research/corpus/sam"), rovis = join(CORPUS, "Rovis catalyst - showing excitation directly to T1 rather than via S1.cdxml");
  if (existsSync(rovis)) {
    const r = fromCdxml(readFileSync(rovis, "utf8")).mol, i = r.atoms.findIndex((a) => a.text?.startsWith("Direct"));
    assert.equal(r.atoms[i]?.text, "Direct,\nNo ISC");
    const again = fromCdxml(toCdxml(r, DEFAULT_STYLE)).mol;
    assert.ok(again.atoms.some((a) => a.text === "Direct,\nNo ISC"), "the corpus label keeps its break through Octet's CDXML");
  }
  console.log("cdxml.check: labels of more than one line ok");
}

// A label with some characters bold, italic or underlined (typed so, or ChemDraw's label runs, as Sam's "OR" with a
// bold R): written as <s> runs with those face bits besides the formula face, read back as the same runs, through CDX
// too. A label's own style stays its own.
{
  const every = (x: Xml): Xml[] => [x, ...x.kids.flatMap(every)];
  const m: Mol = { atoms: [A("O", 0, 0, { text: "OMe", runs: [{ text: "O", bold: true }, { text: "Me" }] }), A("C", 1, 0), A("C", 3, 0, { text: "OMe\nCH3", italic: true, runs: [{ text: "OMe\n" }, { text: "CH3", underline: true }] })], bonds: [b(0, 1)] };
  const xml = toCdxml(m, DEFAULT_STYLE), ts = every(parseXml(xml)).filter((x) => x.name === "t");
  const runs = (t: Xml) => t.kids.filter((k) => k.name === "s").map((k) => [k.text, Number(k.attrs.face)]);
  assert.deepEqual(runs(ts[0]), [["O", 0x61], ["Me", 0x60]]);
  assert.deepEqual(runs(ts[1]), [["OMe\n", 0x62], ["CH3", 0x66]]);
  for (const back of [fromCdxml(xml).mol, fromCdxml(cdxToXml(xmlToCdx(parseXml(xml)))).mol, parse(serialize(fromCdxml(xml).mol))]) {
    assert.deepEqual([back.atoms[0].runs, back.atoms[0].bold], [[{ text: "O", bold: true }, { text: "Me" }], undefined]);
    assert.deepEqual([back.atoms[2].runs, back.atoms[2].italic], [[{ text: "OMe\n" }, { text: "CH3", underline: true }], true]);
  }
  // Runs in Octet's own file must spell the label's text, with only bold, italic and underline.
  const bad = JSON.parse(serialize(m));
  for (const r of [[{ text: "OH", bold: true }], [{ text: "OMe", script: "mid" }], [{ text: "OMe", font: "Georgia" }], [{ text: "OMe", colour: "#ff0000" }]]) { bad.structure.atoms[0].runs = r; assert.throws(() => parse(JSON.stringify(bad)), /damaged/, JSON.stringify(r)); }
  // ChemDraw's own: OR with a bold R, and a label all bold (its own bold, no runs).
  const cd = fromCdxml(`<CDXML BondLength="14.40"><page id="1"><fragment id="2"><n id="3" p="100 100" NodeType="Unspecified"><t p="97 104"><s font="3" size="10" face="96">O</s><s font="3" size="10" face="97">R</s></t></n><n id="4" p="200 100" NodeType="Unspecified"><t p="197 104"><s font="3" size="10" face="97">O</s><s font="3" size="10" face="97">Me</s></t></n></fragment></page></CDXML>`);
  assert.deepEqual(cd.mol.atoms.map((a) => [a.text, a.bold, a.runs]), [["OR", undefined, [{ text: "O" }, { text: "R", bold: true }]], ["OMe", true, undefined]]);
  console.log("cdxml.check: labels with styled characters ok");
}

// A label with part raised or lowered (issue 44, Fe with III raised): written as <s> runs with the superscript face
// (0x40) or subscript face (0x20) in place of Formula, read back as the same runs from CDXML, CDX and .oct. An isotope
// and a charge on an element's label are written as before.
{
  const every = (x: Xml): Xml[] => [x, ...x.kids.flatMap(every)];
  const fe = A("Fe", 0, 0, { text: "FeIII", runs: [{ text: "Fe" }, { text: "III", script: "super" }] }), ome = A("O", 3, 0, { text: "OMea", runs: [{ text: "OMe" }, { text: "a", script: "sub" }] });
  const m: Mol = { atoms: [fe, A("C", 1, 0), ome, A("C", 4, 0), A("C", 6, 0, { isotope: 13 }), A("N", 8, 0, { charge: 1 })], bonds: [b(0, 1), b(2, 3)] };
  const xml = toCdxml(m, DEFAULT_STYLE), ts = every(parseXml(xml)).filter((x) => x.name === "t");
  const runs = (t: Xml) => t.kids.filter((k) => k.name === "s").map((k) => [k.text, Number(k.attrs.face)]);
  assert.deepEqual(runs(ts[0]), [["Fe", 0x60], ["III", 0x40]]);
  assert.deepEqual(runs(ts[1]), [["OMe", 0x60], ["a", 0x20]]);
  assert.deepEqual(runs(ts[2]), [["13", 0x40], ["CH4", 0x60]]);
  assert.deepEqual(runs(ts[3]).map(([, f]) => f), [0x60, 0x40]);
  for (const back of [fromCdxml(xml).mol, fromCdxml(cdxToXml(xmlToCdx(parseXml(xml)))).mol, parse(serialize(fromCdxml(xml).mol)), readOct(writeOct(m, DEFAULT_STYLE)).mol, readCdx(writeCdx(m, DEFAULT_STYLE)).mol]) {
    assert.deepEqual([back.atoms[0].label, back.atoms[0].text, back.atoms[0].runs], ["Fe", "FeIII", fe.runs]);
    assert.deepEqual([back.atoms[2].label, back.atoms[2].text, back.atoms[2].runs], ["O", "OMea", ome.runs]);
    assert.deepEqual([back.atoms[4].isotope, back.atoms[4].text, back.atoms[5].charge, back.atoms[5].text], [13, undefined, 1, undefined]);
  }
  console.log("cdxml.check: labels with superscript and subscript ok");
}

// Sam's corpus (on this Mac only): every text ChemDraw keeps above or below an arrow is written back where it was.
{
  const CORPUS = join(homedir(), "octet-research/corpus/sam");
  if (!existsSync(CORPUS)) console.log("cdxml.check: no corpus here, conditions in the corpus skipped");
  else {
    const plain = (t: Xml) => t.kids.map((k) => k.text).join("").replace(/\s+/g, ""), xy = (t: Xml) => t.attrs.p.split(" ").map(Number);
    const texts = (x: Xml, out: Xml[] = []): Xml[] => { if (x.name === "t") out.push(x); else if (x.name !== "n") x.kids.forEach((k) => texts(k, out)); return out; };
    let n = 0;
    for (const name of readdirSync(CORPUS).filter((f) => f.endsWith(".cdxml"))) {
      const text = readFileSync(join(CORPUS, name), "utf8"), read = fromCdxml(text), theirs = texts(parseXml(text)), ours = texts(parseXml(toCdxml(read.mol, read.style)));
      // Octet's page can sit elsewhere: the shift most texts share.
      const shifts = new Map<string, number>();
      for (const a of theirs) for (const o of ours) if (plain(a) === plain(o)) { const k = xy(o).map((v, j) => (v - xy(a)[j]).toFixed(2)).join(" "); shifts.set(k, (shifts.get(k) ?? 0) + 1); }
      const shift = ([...shifts].sort((p, q) => q[1] - p[1])[0]?.[0] ?? "0 0").split(" ").map(Number);
      for (const c of (read.mol.captions ?? []).filter((x) => x.placed)) {
        const t = ours.find((x) => x.attrs.id === String(c.id))!, p = xy(t);
        assert.ok(theirs.some((x) => plain(x) === plain(t) && xy(x).every((v, k) => Math.abs(v + shift[k] - p[k]) < 0.011)), `${name}: ${c.text} stays where ChemDraw put it`);
        n++;
      }
    }
    assert.ok(n > 0);
    console.log(`cdxml.check: ${n} corpus conditions written where ChemDraw put them`);
  }
}

// Sam's corpus (on this Mac only): for every label ChemDraw right-justified that Octet also writes right-justified on
// the same baseline, how far Octet's p is from ChemDraw's. A report, not a check: Octet places a label so a bond from
// either side meets it at the same distance, which is not where ChemDraw puts it. And a check: every label of more
// than one glyph is written with ChemDraw's justification and stacking, but for an element whose hydrogens come first
// in its text (H3C, H2O), which Octet writes as CH3 right-justified: it reads the same.
{
  const CORPUS = join(homedir(), "octet-research/corpus/sam");
  if (!existsSync(CORPUS)) console.log("cdxml.check: no corpus here, label anchors in the corpus skipped");
  else {
    type L = { p: number[]; d: number[]; text: string; just?: string; stack?: string };
    // Each atom label outside an abbreviation: its node's p, its text p less that, its text and justification.
    const labels = (x: Xml, out: L[] = []): L[] => {
      const t = x.name === "n" ? x.kids.find((k) => k.name === "t") : undefined;
      if (t && x.attrs.p && t.attrs.p) {
        const p = x.attrs.p.split(" ").map(Number), q = t.attrs.p.split(" ").map(Number);
        out.push({ p, d: [q[0] - p[0], q[1] - p[1]], text: t.kids.map((k) => k.text).join(""), just: t.attrs.LabelJustification, stack: t.attrs.LabelAlignment });
      }
      if (x.name !== "n") x.kids.forEach((k) => labels(k, out));
      return out;
    };
    const off = new Map<string, number[]>(), stacked = (l: L) => (l.stack === "Above" || l.stack === "Below" ? l.stack : "");
    let justified = 0;
    for (const name of readdirSync(CORPUS).filter((f) => f.endsWith(".cdxml"))) {
      const text = readFileSync(join(CORPUS, name), "utf8"), read = fromCdxml(text), theirs = labels(parseXml(text)), ours = labels(parseXml(toCdxml(read.mol, read.style)));
      // Octet's page can sit elsewhere: the shift most labels share.
      const shifts = new Map<string, number>();
      for (const a of theirs) for (const o of ours) if (a.text === o.text) { const k = `${(o.p[0] - a.p[0]).toFixed(2)} ${(o.p[1] - a.p[1]).toFixed(2)}`; shifts.set(k, (shifts.get(k) ?? 0) + 1); }
      const [sx, sy] = ([...shifts].sort((p, q) => q[1] - p[1])[0]?.[0] ?? "0 0").split(" ").map(Number);
      for (const a of theirs.filter((l) => l.text.replace(/[+-]$/, "").length > 1)) {
        const o = ours.find((l) => Math.abs(l.p[0] - a.p[0] - sx) < 0.02 && Math.abs(l.p[1] - a.p[1] - sy) < 0.02);
        assert.ok(o, `${name}: ${a.text} is written`);
        const same = a.just === o.just && stacked(a) === stacked(o), hFirst = /^H\d*[A-Z]/.test(a.text) && a.just === "Left" && o.just === "Right";
        assert.ok(same || hFirst, `${name}: ${a.text} keeps ChemDraw's ${a.just} ${stacked(a)} (Octet: ${o.just} ${stacked(o)})`);
        justified++;
      }
      for (const a of theirs.filter((l) => l.just === "Right")) {
        const o = ours.find((l) => Math.abs(l.p[0] - a.p[0] - sx) < 0.02 && Math.abs(l.p[1] - a.p[1] - sy) < 0.02);
        assert.ok(o, `${name}: ${a.text} is written`);
        if (o.just === "Right" && Math.abs(o.d[1] - a.d[1]) <= 0.021) off.set(a.text, [...(off.get(a.text) ?? []), o.d[0] - a.d[0]]);
      }
    }
    const all = [...off.values()].flat(), range = (v: number[]) => `${Math.min(...v).toFixed(2)} to ${Math.max(...v).toFixed(2)}`;
    console.log(`cdxml.check: ${justified} corpus labels of more than one glyph keep ChemDraw's justification`);
    console.log(`cdxml.check: ${all.length} right-justified corpus labels; Octet's p less ChemDraw's (pt): ${[...off].map(([t, v]) => `${t} ${range(v)}`).join(", ")}`);
  }
}

// Tobias, 2 November 2026: contract a group, give it a label of your own, expand it again. The group stays with the
// label (inner), through a CDXML file too, and Expand Label draws it out.
{
  const A = (label: string, x: number, y = 0): Atom => ({ label, location: [x, y, 0] });
  // A propyl ester on a ring carbon: C0-C1(=O2)-O3-C4-C5-C6.
  const m: Mol = { atoms: [A("C", 0), A("C", 1), A("O", 1.5, 0.87), A("O", 1.5, -0.87), A("C", 2.5, -0.87), A("C", 3, 0), A("C", 4, 0)],
    bonds: [[0, 1, 1], [1, 2, 2], [1, 3, 1], [3, 4, 1], [4, 5, 1], [5, 6, 1]].map(([a, b, t]) => ({ atoms: [a, b] as [number, number], type: t })) };
  const contracted = setLabel(contractLabel(m, 1, new Set([1, 2, 3, 4, 5, 6]), "C4H7O2"), 1, "Est");
  assert.deepEqual([contracted.atoms.length, contracted.atoms[1].text, contracted.atoms[1].inner?.atoms.length, contracted.atoms[1].inner?.bonds.length], [2, "Est", 6, 5]);
  const out = expandLabel(contracted, 1, contracted.atoms[1].inner!);
  assert.deepEqual([out.atoms.length, out.bonds.length, out.atoms[1].text, out.atoms[1].inner], [7, 6, undefined, undefined]);
  const read = fromCdxml(toCdxml(contracted, DEFAULT_STYLE, { name: "contract.cdxml" })).mol, label = read.atoms.find((a) => a.text === "Est");
  assert.deepEqual([label?.inner?.atoms.length, label?.inner?.bonds.length, label?.inner?.atoms[0].label], [6, 5, "C"], "the group goes through CDXML");
  assert.equal(setLabel(contracted, 1, "Br").atoms[1].inner, undefined, "an element label leaves the group");
}

// Issue #12: in a drawing from ChemDraw, deleting one thing took text that was not selected. A step's text above and
// below its arrow belongs to the arrow, and went with it. Delete, Clear and the Eraser (deleteChosen) take only what
// they are given; that text stays where it is drawn. Repeated, missing and shared file ids give every object its own id.
{
  const doc = `<CDXML BondLength="14.40" CaptionSize="10"><page>
<fragment id="1"><n id="2" p="100 200"/><n id="3" p="112.47 207.2"/><b id="4" B="2" E="3"/></fragment>
<arrow id="10" ArrowheadHead="Full" ArrowheadType="Solid" Head3D="300 200 0" Tail3D="200 200 0"/>
<arrow id="11" ArrowheadHead="Full" ArrowheadType="Solid" Head3D="500 200 0" Tail3D="400 200 0"/>
<t id="12" p="210 190"><s size="10">above</s></t><t id="12" p="210 215"><s size="10">below</s></t><t p="410 190"><s size="10">no id</s></t><t p="410 215"><s size="10">no id either</s></t>
<group id="30"><t id="31" p="100 300"><s size="10">grouped</s></t><t id="10" p="150 300"><s size="10">arrow's id</s></t></group>
<group id="40" Integral="yes"><t id="41" p="100 400"><s size="10">integral</s></t><t id="42" p="150 400"><s size="10">integral too</s></t></group>
<t id="50" p="300 500"><s size="10">far away</s></t>
<scheme id="60"><step id="61" ReactionStepReactants="1" ReactionStepArrows="10" ReactionStepObjectsAboveArrow="12 50" ReactionStepObjectsBelowArrow="12"/><step id="62" ReactionStepArrows="11" ReactionStepObjectsAboveArrow="12 10 31" ReactionStepObjectsBelowArrow="0 -1"/></scheme></page></CDXML>`;
  const m = fromCdxml(doc).mol, all = (x: Mol) => (x.captions ?? []).map((c) => c.text).sort(), texts = all(m);
  const ids = (x: Mol) => [...(x.captions ?? []), ...(x.arrows ?? []), ...(x.shapes ?? []), ...(x.cycles ?? []), ...(x.groups ?? [])].map((o) => o.id);
  const unique = (x: Mol) => assert.equal(new Set(ids(x)).size, ids(x).length, "every object has its own id");
  assert.equal(texts.length, 9);
  unique(m);
  assert.deepEqual(m.captions!.filter((c) => c.on).map((c) => c.text).sort(), ["above", "far away", "grouped"], "the step's texts are its arrow's");
  const [a10, a11] = m.arrows!.map((a) => a.id), grouped = m.captions!.find((c) => c.text === "grouped")!;
  // The arrow alone goes (the Delete key, Clear, the panel's Delete, an Eraser click or stroke); its text stays, free,
  // where it is drawn, and in its group.
  for (const a of [a10, a11]) {
    const out = deleteChosen(m, new Set(), new Set([a]), undefined, (c) => [c.x + 1, c.y]);
    assert.deepEqual([out.arrows!.length, all(out)], [1, texts], "only the arrow goes");
    assert.ok(out.captions!.every((c) => !c.on || c.on.arrow !== a), "its text is free");
  }
  const freed = deleteChosen(m, new Set(), new Set([a11]), undefined, (c) => [c.x + 1, c.y]), g = freed.captions!.find((c) => c.text === "grouped")!;
  assert.deepEqual([g.x, g.y, g.on, g.placed], [grouped.x + 1, grouped.y, undefined, undefined], "where it is drawn");
  assert.ok(freed.groups!.some((x) => x.items.includes(g.id)), "still in its group");
  const cut = new Set([a10, ...extractSelection(m, new Set(), new Set([a10])).captions!.map((c) => c.id)]);
  assert.equal(deleteGraphics(m, cut).captions!.length, 7, "Cut takes the arrow's text with it, as Copy does");
  // Each text alone: the others stay.
  for (const c of m.captions!) assert.deepEqual(all(deleteChosen(m, new Set(), new Set([c.id]))), texts.filter((t, k) => k !== texts.indexOf(c.text)), `only "${c.text}" goes`);
  // The structure, by its atoms or by its only bond (its bare carbons go with it): no text goes.
  assert.deepEqual([all(deleteChosen(m, new Set([0, 1]), new Set())), all(deleteChosen(m, new Set(), new Set(), new Set([0])))], [texts, texts]);
  assert.equal(deleteChosen(m, new Set(), new Set(), new Set([0])).atoms.length, 0);
  // A compound number under a structure stays when the structure goes.
  const [numbered] = addCaption(m, { text: "1", x: 0, y: -1, under: [0, 1] }), left = deleteChosen(numbered, new Set([0, 1]), new Set());
  assert.ok(left.captions!.some((c) => c.text === "1" && !c.under));
  // Ids stay unique after a paste, a duplicate and a file read back.
  unique(insertMol(m, m).mol);
  unique(duplicateSelection(m, new Set(m.atoms.map((_, i) => i)), new Set(ids(m))).mol);
  unique(fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol);
  unique(parse(serialize(m)));
  // Text freed from its arrow keeps its box, lined up as it is drawn: left-aligned conditions are centred on a level
  // arrow, and a steep arrow's are set beside it.
  const laid: Mol = { atoms: [], bonds: [], arrows: [{ id: 1, from: [0, 0], to: [5, 0] }, { id: 2, from: [10, 0], to: [10, -5] }], captions: [
    { id: 3, text: "NaOH", x: 0, y: 0, on: { arrow: 1, side: "above" } }, { id: 4, text: "THF\n0 °C", x: 0, y: 0, align: "left", on: { arrow: 1, side: "below" } },
    { id: 5, text: "hν", x: 0, y: 0, on: { arrow: 2, side: "above" } }, { id: 6, text: "reflux", x: 0, y: 0, align: "right", on: { arrow: 2, side: "below" } }] };
  const lay = (x: Mol) => placeCaptions(x, { ink: [], scale: 14.4 }, (t) => t.length * 6, x.arrows), drawn = lay(laid);
  const q = (c: Caption) => drawn.find((x) => x.id === c.id)!, anchor = (p: Placed) => (p.anchor === "start" ? p.box[0] : p.anchor === "end" ? p.box[2] : (p.box[0] + p.box[2]) / 2);
  const loose = lay(deleteChosen(laid, new Set(), new Set([1, 2]), undefined, (c) => [anchor(q(c)) / 14.4, -q(c).lines[0].y / 14.4], (c) => ({ start: "left", middle: "centre", end: "right" } as const)[q(c).anchor]));
  assert.deepEqual(loose.map((q) => q.box), drawn.map((q) => q.box), "freed text stays where it is drawn");
  console.log("cdxml.check: deleting one thing leaves the text it was not given ok");
}

// ChemDraw's predicted shifts (Predict 13C-NMR Shifts): each is an assignment tag on the atom's node holding a text at
// its own place, 7.5 pt, coloured. Opened, each number is a caption at that place with its text and style, and nothing
// is lost. A file built here in that shape: octane-3,5-dione with its eight carbon shifts.
{
  const shift = [13.7, 17.1, 45.4, 205.2, 57.9, 204.9, 36.7, 7.7], carbons = shift.map((_, k): [number, number] => [100 + 12.47 * k, k % 2 ? 196.4 : 203.6]);
  const tag = (k: number, value = `${shift[k]}-${shift[k]},`, text: string | null = String(shift[k])) =>
    `<objecttag id="${100 + k}" TagType="String" Name="/CS/CD/assign" Value="${value}">${text === null ? "" : `<t id="${200 + k}" p="${carbons[k][0] + 3} ${carbons[k][1] + (k % 2 ? -5 : 11)}"><s font="3" size="7.5" color="5">${text}</s></t>`}</objecttag>`;
  const nodes = (more: (k: number) => string) => carbons.map(([x, y], k) => `<n id="${10 + k}" p="${x} ${y}">${more(k)}</n>`).join("")
    + `<n id="30" p="${carbons[3][0]} ${carbons[3][1] + 14.4}" Element="8"/><n id="31" p="${carbons[5][0]} ${carbons[5][1] + 14.4}" Element="8"/>`;
  const bonds = carbons.slice(1).map((_, k) => `<b id="${40 + k}" B="${10 + k}" E="${11 + k}"/>`).join("") + `<b id="50" B="13" E="30" Order="2"/><b id="51" B="15" E="31" Order="2"/>`;
  const file = (more: (k: number) => string, extra = "") => `<?xml version="1.0" encoding="UTF-8" ?><CDXML BondLength="14.40" CaptionFont="3" CaptionSize="10"><colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/><color r="1" g="0" b="0"/><color r="0" g="0" b="1"/></colortable><fonttable><font id="3" name="Arial"/></fonttable><page id="1" BoundingBox="0 0 540 720"><fragment id="2">${nodes(more)}${bonds}</fragment>${extra}</page></CDXML>`;
  const read = fromCdxml(file(tag)), caps = read.mol.captions ?? [];
  assert.deepEqual(read.lost, {}, "nothing lost");
  assert.deepEqual(caps.map((c) => c.text), shift.map(String), "every number shows");
  // Where ChemDraw puts it from its atom (its p less the node's p, y down there), as the drawing has the atom.
  caps.forEach((c, k) => { const [x, y] = read.mol.atoms[k].location; assert.ok(Math.abs(c.x - x - 3 / 14.4) < 1e-9 && Math.abs(c.y - y + (k % 2 ? -5 : 11) / 14.4) < 1e-9, `${c.text} at its place`); });
  assert.ok(caps.every((c) => c.size === 7.5 && c.colour === "#0000FF" && c.align === "left"), "in its size and colour");
  assert.ok(read.mol.atoms.every((a) => !a.peaks), "no spectrum, so no links");
  // The same drawing as a CDX file.
  const cdx = fromCdxml(cdxToXml(xmlToCdx(parseXml(file(tag)))));
  assert.deepEqual([cdx.lost, cdx.mol.captions?.map((c) => [c.text, c.size, c.colour])], [{}, shift.map((v) => [String(v), 7.5, "#0000FF"])]);
  // Hidden text stays hidden; a tag with no text gives no caption, and with no spectrum it is lost as before.
  const hidden = fromCdxml(file((k) => (k === 0 ? tag(0).replace("<t ", `<t Visible="no" `) : k === 1 ? tag(1, undefined, null) : "")));
  assert.deepEqual([hidden.mol.captions?.length, hidden.lost], [undefined, { "spectrum assignment": 1 }]);
  // With a measured spectrum in the file: a plain tag of the spectrum's value links the atom to its multiplet, and a text
  // tag whose value no spectrum carries gives a caption and no second link, even inside the spectrum's range.
  const y = Float64Array.from({ length: 2000 }, (_, i) => { const x = 12 - (12 * i) / 1999; return 1 / (1 + ((x - 2.5) / 0.01) ** 2); });
  const ms = fromJcamp({ title: "Dione", kind: "nmr", nucleus: "1H", mhz: 400, solvent: "CDCl₃", xUnit: "ppm", yUnit: "", first: 12, last: 0, y }, 1);
  const g = ms.groups[0], value = `${g.lo}-${g.hi},`;
  const written = parseXml(toCdxml({ atoms: [], bonds: [], spectra: [ms] }, DEFAULT_STYLE)), every = (x: Xml): Xml[] => [x, ...x.kids.flatMap(every)];
  const sp = every(written).find((x) => x.name === "spectrum")!, spText = `<spectrum ${Object.entries(sp.attrs).filter(([k]) => k !== "Octet").map(([k, v]) => `${k}="${v}"`).join(" ")}>${sp.text}<objecttag TagType="String" Name="/CS/CD/assign" Value="${value}"/></spectrum>`;
  const both = fromCdxml(file((k) => (k === 4 ? tag(4, value, null) + tag(4, "2.5-2.5,", "2.50") : ""), spText));
  assert.deepEqual(both.lost, {});
  assert.deepEqual([both.mol.atoms[4].peaks?.length, both.mol.captions?.map((c) => c.text)], [1, ["2.50"]], "one link and one caption");
  assert.equal(both.mol.spectra?.[0].groups.length, ms.groups.length, "the text tag makes no multiplet of its own");
  // A text tag of exactly the spectrum's value is a link too (ChemDraw's own assignment), with its caption.
  const same = fromCdxml(file((k) => (k === 4 ? tag(4, value, "2.50") : ""), spText));
  assert.deepEqual([same.mol.atoms[4].peaks?.length, same.mol.captions?.map((c) => c.text), same.lost], [1, ["2.50"], {}]);
  console.log("cdxml.check: ChemDraw's predicted shifts open as captions ok");
}

// Issue 31: text Octet draws as a formula (conditions on an arrow, a cycle's text) is written as the runs the page
// shows, so ChemDraw shows Pd(PPh₃)₄ too, and Octet reads it back as the plain text it was, editable as typed. A
// caption with runs of its own, and a ChemDraw file's runs, read back unchanged. The same holds through CDX. (A cycle
// with no structures is not kept, so the round trip above checks a cycle's ArB(OH)2.)
{
  const on = (id: number, text: string, more: Partial<Caption> = {}): Caption => ({ id, text, x: 0, y: 0, on: { arrow: 101, side: id % 2 ? "above" : "below" }, ...more });
  const m: Mol = { atoms: [], bonds: [], arrows: [arrow(101, "reaction", [0, 0], [4, 0])], captions: [
    on(1, "Pd(PPh3)4"), on(2, "CH2Cl2"), on(3, "10 mol%"), on(4, "SO4^2-"),
    on(5, "SO42−", { runs: [{ text: "SO" }, { text: "4", script: "sub" }, { text: "2−", script: "super" }] }),
    on(7, "Pd(0)L2"),
    { id: 9, text: "Pd(PPh3)4", x: 0, y: 6 },
  ] };
  const xml = toCdxml(m, DEFAULT_STYLE);
  // Each <t>'s runs as text and face.
  const texts = parseXml(xml).kids.flatMap(function all(k: Xml): Xml[] { return [k, ...k.kids.flatMap(all)]; }).filter((k) => k.name === "t")
    .map((t) => t.kids.filter((s) => s.name === "s").map((s) => `${s.text}${s.attrs.face ? `/${s.attrs.face}` : ""}`).join("|"));
  for (const want of ["Pd(PPh|3/32|)|4/32", "CH|2/32|Cl|2/32", "10 mol%", "SO|4/32|^2-", "SO|4/32|2−/64", "Pd(0)L|2/32", "Pd(PPh3)4"]) assert.ok(texts.includes(want), `${want} is written as the page draws it: ${texts.join(", ")}`);
  // CDX has no place for Octet's own data, so ChemDraw reads the runs; Octet's .cdx and .oct read back as typed.
  const cdxTexts = cdxToXml(xmlToCdx(parseXml(xml))).kids.flatMap(function all(k: Xml): Xml[] { return [k, ...k.kids.flatMap(all)]; }).filter((k) => k.name === "t")
    .map((t) => t.kids.filter((s) => s.name === "s").map((s) => `${s.text}${s.attrs.face ? `/${s.attrs.face}` : ""}`).join("|"));
  assert.ok(cdxTexts.includes("Pd(PPh|3/32|)|4/32"), `CDX: ${cdxTexts.join(", ")}`);
  for (const [what, back] of [["CDXML", fromCdxml(xml)], [".oct", readOct(writeOct(m, DEFAULT_STYLE), true)], ["Octet's .cdx", readCdx(writeCdx(m, DEFAULT_STYLE))]] as const) {
    const read = (id: number) => { const want = m.captions!.find((c) => c.id === id)!; return back.mol.captions!.find((c) => c.text === want.text && !!c.on === !!want.on)!; };
    for (const id of [1, 2, 3, 4, 7, 9]) assert.deepEqual([read(id).text, read(id).runs], [m.captions!.find((c) => c.id === id)!.text, undefined], `${what}: caption ${id} reads back as plain text`);
    assert.deepEqual(read(5).runs, m.captions![4].runs, `${what}: runs of its own stay`);
    assert.deepEqual(back.lost, {});
  }
  // Runs changed elsewhere so they are no longer the formula's stay; a ChemDraw file's runs read unchanged.
  const kept = fromCdxml(xml.replace(/<s font="(\d+)" size="10">Cl<\/s>/, '<s font="$1" size="10" face="1">Cl</s>')).mol.captions!.find((c) => c.text === "CH2Cl2")!;
  assert.deepEqual(kept.runs, [{ text: "CH" }, { text: "2", script: "sub" }, { text: "Cl", bold: true }, { text: "2", script: "sub" }]);
  const chemdraw = fromCdxml('<CDXML BondLength="14.4"><page><t p="0 0"><s font="3" size="10">CH</s><s font="3" size="10" face="32">2</s><s font="3" size="10">Cl</s><s font="3" size="10" face="32">2</s></t></page></CDXML>').mol.captions![0];
  assert.deepEqual(chemdraw.runs, [{ text: "CH" }, { text: "2", script: "sub" }, { text: "Cl" }, { text: "2", script: "sub" }], "ChemDraw's runs read unchanged");
  // Turned conditions read back as free text, which is not drawn as a formula: they keep the runs, so H₂O stays H₂O.
  const turned = fromCdxml(toCdxml({ ...m, captions: [on(1, "H2O", { angle: 30 })] }, DEFAULT_STYLE)).mol.captions![0];
  assert.deepEqual([turned.on, turned.runs], [undefined, [{ text: "H" }, { text: "2", script: "sub" }, { text: "O" }]], "turned conditions keep their subscripts");
  console.log("cdxml.check: formula text written as drawn, read back as typed ok");
}
