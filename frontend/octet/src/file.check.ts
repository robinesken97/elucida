// Run: node src/file.check.ts. Fails loudly if the file format breaks or accepts a bad file.
import assert from "node:assert/strict";
import { addArrow, addCaption, addRing, addShape, EMPTY, setBondSpec, setElement } from "./edit.ts";
import { parse, serialize } from "./file.ts";
import { DEFAULT_STYLE, withScale } from "./docstyle.ts";
import type { Mol } from "./render.ts";

// A drawing survives a save and reopen.
const mol = setBondSpec(setElement(addRing(EMPTY, 6, true, { point: [0, 0] }), 0, "N"), 1, { type: 1, display: "wavy" });
const back = parse(serialize(mol));
assert.deepEqual(back.bonds, mol.bonds);
assert.deepEqual(back.atoms.map((a) => a.label), mol.atoms.map((a) => a.label));
// A hidden warning stays hidden on reopen.
{
  const hid: Mol = { ...mol, atoms: mol.atoms.map((a, i) => (i === 0 ? { ...a, ignoreWarnings: true } : a)), bonds: mol.bonds.map((b, k) => (k === 2 ? { ...b, ignoreWarnings: true } : b)) };
  const again = parse(serialize(hid));
  assert.deepEqual([again.atoms.map((a) => !!a.ignoreWarnings), again.bonds.map((b) => !!b.ignoreWarnings)], [hid.atoms.map((a) => !!a.ignoreWarnings), hid.bonds.map((b) => !!b.ignoreWarnings)]);
}
for (let i = 0; i < mol.atoms.length; i++) assert.ok(Math.abs(back.atoms[i].location[0] - mol.atoms[i].location[0]) < 1e-4);
console.log("file.check: round trip ok");

// Bad files are refused with a message, never half-loaded.
const bad = [
  "not json",
  JSON.stringify({ format: "other" }),
  JSON.stringify({ format: "octet", version: 99, structure: { atoms: [], bonds: [] } }),
  JSON.stringify({ format: "octet", version: 1, structure: { atoms: [{ label: "C", x: 0, y: 0 }], bonds: [{ atoms: [0, 5], type: 1 }] } }),
  JSON.stringify({ format: "octet", version: 1, structure: { atoms: [{ label: "<script>", x: 0, y: 0 }], bonds: [] } }),
  JSON.stringify({ format: "octet", version: 1, structure: { atoms: [{ label: "C", x: 1e400, y: 0 }], bonds: [] } }),
  JSON.stringify({ format: "octet", version: 1, structure: { atoms: [{ label: "C", x: 0, y: 0 }, { label: "C", x: 1, y: 0 }], bonds: [{ atoms: [0, 1], type: 9 }] } }),
];
for (const text of bad) assert.throws(() => parse(text), /Octet|damaged/);
console.log("file.check: bad files refused");

// Captions survive a save and reopen, and bad ones are refused.
{
  const [withCaption] = addCaption(mol, { text: "1", x: 0, y: -2, bold: true, under: [0, 1, 2] });
  const [both] = addCaption(withCaption, { text: "N-oxide\nstep 2", x: 3, y: 1, align: "left", size: 12 });
  const again = parse(serialize(both));
  assert.deepEqual(again.captions, both.captions);
  const base = { format: "octet", version: 1, structure: { atoms: [{ label: "C", x: 0, y: 0 }], bonds: [] } };
  for (const captions of [[{ text: 5, x: 0, y: 0 }], [{ text: "a", x: 0, y: 0, under: [3] }], [{ text: "a", x: 0, y: 0, size: 5000 }], [{ text: "a\u0000", x: 0, y: 0 }], "x"])
    assert.throws(() => parse(JSON.stringify({ ...base, captions })), /damaged/);
  console.log("file.check: captions ok");
}

// Arrows and their conditions survive a save and reopen.
{
  const [withArrow, arrow] = addArrow(mol, { kind: "reaction", from: [3, 0], to: [6, 0] });
  const [curvedToo] = addArrow(withArrow, { kind: "fishhook", from: [0, 0], to: [1, 1], bend: 0.3 });
  const [conditions] = addCaption(curvedToo, { text: "hν, 4CzIPN", x: 0, y: 0, on: { arrow, side: "above" } });
  const again = parse(serialize(conditions));
  assert.deepEqual(again.arrows?.map((a) => [a.kind, a.from, a.to, a.bend]), conditions.arrows?.map((a) => [a.kind, a.from, a.to, a.bend]));
  const cond = again.captions?.find((c) => c.on);
  assert.equal(again.arrows?.find((a) => a.id === cond?.on?.arrow)?.kind, "reaction", "conditions stay on their arrow");
  const base = { format: "octet", version: 1, structure: { atoms: [], bonds: [] } };
  for (const bad of [{ arrows: [{ kind: "teleport", x1: 0, y1: 0, x2: 1, y2: 0 }] }, { arrows: [{ kind: "reaction", x1: 0, y1: 0, x2: "a", y2: 0 }] }, { arrows: [], captions: [{ text: "a", x: 0, y: 0, on: { arrow: 0, side: "above" } }] }])
    assert.throws(() => parse(JSON.stringify({ ...base, ...bad })), /damaged/);
  console.log("file.check: arrows ok");
}

// Radicals, lone pairs, circled and partial charges survive a save and reopen; bad values are refused.
{
  const marked = { ...mol, atoms: mol.atoms.map((a, i) => (i === 0 ? { ...a, charge: 1, circled: true, pairs: 1 } : i === 1 ? { ...a, radical: 1, partial: "-" as const } : a)) };
  const again = parse(serialize(marked));
  const { hmark, attach, bead } = parse(serialize({ ...mol, atoms: mol.atoms.map((a, i) => (i === 2 ? { ...a, hmark: "dot" as const, attach: true, bead: true } : a)) })).atoms[2];
  assert.deepEqual({ hmark, attach, bead }, { hmark: "dot", attach: true, bead: true });
  assert.deepEqual(again.atoms.slice(0, 2).map(({ charge, circled, pairs, radical, partial }) => ({ charge, circled, pairs, radical, partial })),
    [{ charge: 1, circled: true, pairs: 1, radical: undefined, partial: undefined }, { charge: undefined, circled: undefined, pairs: undefined, radical: 1, partial: "-" }]);
  assert.equal(parse(serialize({ ...mol, atoms: mol.atoms.map((a, i) => (i === 1 ? { ...a, enhanced: "or1" } : a)) })).atoms[1].enhanced, "or1");
  // Colours on atoms, bonds and arrows survive a save; a bad colour is refused.
  const coloured = parse(serialize({ ...mol, atoms: mol.atoms.map((a, i) => (i === 0 ? { ...a, colour: "#B42323" } : a)), bonds: mol.bonds.map((b, i) => (i === 0 ? { ...b, colour: "#213C99" } : b)),
    arrows: [{ id: 50, kind: "orbital" as const, from: [0, 0] as [number, number], to: [0, 1] as [number, number], orbital: { shape: "p" as const, phase: "filled" as const }, colour: "#22775B" }] }));
  assert.deepEqual([coloured.atoms[0].colour, coloured.bonds[0].colour, coloured.arrows?.[0].colour], ["#B42323", "#213C99", "#22775B"]);
  // Isotopes and singlet radicals (Atom Properties) save and load.
  const iso = parse(serialize({ ...mol, atoms: mol.atoms.map((a, i) => (i === 0 ? { ...a, isotope: 13, radical: 3 } : a)) })).atoms[0];
  assert.deepEqual([iso.isotope, iso.radical], [13, 3]);
  for (const bad of [{ radical: 4 }, { isotope: 0 }, { isotope: 2.5 }, { pairs: 9 }, { circled: "yes" }, { partial: "x" }, { enhanced: "rac" }, { colour: "red" }])
    assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [{ label: "C", x: 0, y: 0, ...bad }], bonds: [] } })), /damaged/);
  console.log("file.check: atom marks ok");
}

// Shapes keep their kind, corners, dashes, colour and order.
{
  const [one] = addShape(mol, { kind: "highlight", from: [0, 0], to: [2, 1] });
  const [two] = addShape(one, { kind: "brackets", from: [-1, -1], to: [3, 2], dashed: true, colour: "#213C99" });
  const again = parse(serialize(two));
  assert.deepEqual(again.shapes?.map(({ id: _, ...x }) => x), two.shapes?.map(({ id: _, ...x }) => x));
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "star", x1: 0, y1: 0, x2: 1, y2: 1 }] })), /damaged/);
  console.log("file.check: shapes ok");
}

// Draw order (Bring to Front, Send to Back) survives a save and reopen on every kind; a bad order is left out.
{
  const [one] = addShape(mol, { kind: "box", from: [0, 0], to: [2, 1], order: -1 });
  const m = { ...one, atoms: one.atoms.map((a) => ({ ...a, order: 2 })), captions: [{ id: 90, text: "A", x: 0, y: 0, order: 3 }], arrows: [{ id: 91, kind: "reaction" as const, from: [0, 0] as [number, number], to: [1, 0] as [number, number], order: 4 }] };
  const again = parse(serialize(m));
  assert.deepEqual([again.shapes![0].order, again.atoms[0].order, again.captions![0].order, again.arrows![0].order], [-1, 2, 3, 4]);
  const bad = parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [{ label: "C", x: 0, y: 0, order: 0.5 }], bonds: [] } }));
  assert.equal(bad.atoms[0].order, undefined);
  console.log("file.check: draw order ok");
}

// Lines, arcs, dashed arrows and orbitals survive a save and reopen.
{
  let m = mol;
  for (const a of [
    { kind: "line" as const, from: [0, 0] as [number, number], to: [2, 0] as [number, number], style: "wavy" as const },
    { kind: "arc" as const, from: [0, 0] as [number, number], to: [2, 0] as [number, number], bend: 0.5, style: "dashed" as const },
    { kind: "reaction" as const, from: [0, 1] as [number, number], to: [3, 1] as [number, number], style: "dashed" as const },
    { kind: "orbital" as const, from: [0, 0] as [number, number], to: [0, 1] as [number, number], orbital: { shape: "p" as const, phase: "phased" as const } },
    // ChemDraw's sizes and kinds, and a straight arrow's point and bend.
    { kind: "equilibrium" as const, from: [0, 2] as [number, number], to: [3, 2] as [number, number], ratio: 3, headSize: { length: 15, centre: 13.125, width: 3.75 } },
    { kind: "block" as const, from: [0, 3] as [number, number], to: [3, 3] as [number, number], shaft: 8, fill: "faded" as const },
    { kind: "hash" as const, from: [0, 4] as [number, number], to: [3, 4] as [number, number] }, { kind: "dipole" as const, from: [0, 5] as [number, number], to: [3, 5] as [number, number] },
    { kind: "reaction" as const, from: [0, 6] as [number, number], to: [3, 6] as [number, number], point: true as const, bend: 0.2 },
  ]) m = addArrow(m, a)[0];
  const again = parse(serialize(m));
  assert.deepEqual(again.arrows?.map(({ id: _, ...a }) => a), m.arrows?.map(({ id: _, ...a }) => a));
  for (const bad of [{ headSize: { length: 0, centre: 1, width: 1 } }, { ratio: -1 }, { shaft: "wide" }, { point: 1 }])
    assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, arrows: [{ kind: "reaction", x1: 0, y1: 0, x2: 1, y2: 0, ...bad }] })), /damaged/);
  console.log("file.check: lines and orbitals ok");
}

// Shape styles, single brackets with a mark, and a TLC plate's spots survive a save and reopen.
{
  let m = mol;
  for (const sh of [
    { kind: "oval" as const, from: [0, 0] as [number, number], to: [1, 1] as [number, number], fill: "shaded" as const },
    { kind: "box" as const, from: [0, 0] as [number, number], to: [2, 1] as [number, number], shadow: true },
    { kind: "brackets" as const, from: [0, 0] as [number, number], to: [2, 2] as [number, number], side: "left" as const, mark: "‡" },
    { kind: "rounded" as const, from: [0, 0] as [number, number], to: [2, 1] as [number, number], fill: "faded" as const, boldLine: true as const, angle: 30, order: 2 },
    { kind: "brackets" as const, from: [0, 0] as [number, number], to: [2, 2] as [number, number], ignoreWarnings: true as const },
    { kind: "tlc" as const, from: [0, 0] as [number, number], to: [3, 4] as [number, number], tlc: { lanes: 3, spots: [{ lane: 0, rf: 0.42 }, { lane: 2, rf: 0.7 }], rf: true } },
    { kind: "table" as const, from: [0, 3] as [number, number], to: [6, 0] as [number, number], table: { cells: [["Entry", "Solvent", "Yield (%)"], ["1", "THF", "72"]], grid: true } },
    { kind: "table" as const, from: [0, 3] as [number, number], to: [6, 0] as [number, number], dashed: true,
      table: { cells: [["a", "b"], ["c", "d"]], widths: [2, 3.5], heights: [1, 1.2], lines: ["top" as const, "rows" as const, "cols" as const], align: ["left" as const, "right" as const], weight: 0.8 } },
    // A turned box with its own line width, and a table and plate with their text styles (UI-7, UI-41, UI-42).
    { kind: "box" as const, from: [0, 0] as [number, number], to: [2, 1] as [number, number], angle: 30, width: 1.5 },
    { kind: "table" as const, from: [0, 3] as [number, number], to: [6, 0] as [number, number], table: { cells: [["a"]] }, font: "Times New Roman", size: 12, bold: true as const, italic: true as const, underline: true as const },
    { kind: "tlc" as const, from: [0, 0] as [number, number], to: [3, 4] as [number, number], tlc: { lanes: 1, spots: [] }, size: 9, width: 0.4 },
  ]) m = addShape(m, sh)[0];
  const again = parse(serialize(m));
  assert.deepEqual(again.shapes?.map(({ id: _, ...x }) => x), m.shapes?.map(({ id: _, ...x }) => x));
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "tlc", x1: 0, y1: 0, x2: 1, y2: 1, tlc: { lanes: 2, spots: [{ lane: 5, rf: 0.5 }] } }] })), /damaged/);
  // Widths reach 200 pt and sizes 0.1 to 999 pt, so a document scaled 10% to 1000% keeps them (decision 0007).
  for (const bad of [{ angle: 1e7 }, { angle: "30" }, { width: 0 }, { width: 999 }, { size: 0.01 }, { size: 2000 }, { font: "x".repeat(300) }, { bold: 1 }, { angle: "up" }, { angle: 1e4 }, { boldLine: 1 }, { fill: "glow" }])
    assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "box", x1: 0, y1: 0, x2: 1, y2: 1, ...bad }] })), /damaged/, JSON.stringify(bad));
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, arrows: [{ kind: "reaction", x1: 0, y1: 0, x2: 1, y2: 1, width: -1 }] })), /damaged/);
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "table", x1: 0, y1: 0, x2: 1, y2: 1, table: { cells: [[1]] } }] })), /damaged/);
  for (const bad of [{ widths: [0] }, { heights: [1e9] }, { lines: ["diagonal"] }, { align: ["middle"] }, { weight: -1 }])
    assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "table", x1: 0, y1: 0, x2: 1, y2: 1, table: { cells: [["a"]], ...bad } }] })), /damaged/, JSON.stringify(bad));
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "curve", x1: 0, y1: 0, x2: 1, y2: 1, curve: { points: [{ at: [0, 0] }, { at: [1, "x"] }] } }] })), /damaged/);
  // Pen curves are lines with points, heads and a fill; a curve saved as a shape (before they were lines) opens as a line.
  const pen = { id: 90, kind: "curve" as const, from: [0, 0] as [number, number], to: [4, 0] as [number, number], start: "left" as const, end: "full" as const, head: "hollow" as const, style: "doubled" as const, fill: "faded" as const,
    curve: { points: [{ at: [0, 0] as [number, number] }, { at: [2, 2] as [number, number], c1: [1, 2] as [number, number], c2: [3, 2] as [number, number] }, { at: [4, 0] as [number, number] }], closed: true } };
  const back = parse(serialize({ ...mol, arrows: [pen] })).arrows![0];
  assert.deepEqual({ ...back, id: 90 }, pen);
  // A curve of one anchor (ChemDraw's clip art has them, and the CDXML reader keeps them) saves and opens again.
  const dot = { ...pen, to: [0, 0] as [number, number], curve: { points: [{ at: [0, 0] as [number, number], c2: [0.1, 0.1] as [number, number] }], closed: true } };
  assert.deepEqual({ ...parse(serialize({ ...mol, arrows: [dot] })).arrows![0], id: 90 }, dot);
  assert.throws(() => parse(serialize({ ...mol, arrows: [{ ...dot, curve: { points: [] } }] })), /damaged/);
  const legacy = parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "box", x1: 0, y1: 0, x2: 1, y2: 1 }, { kind: "curve", x1: 0, y1: 0, x2: 2, y2: 1, dashed: true, curve: { points: [{ at: [0, 0] }, { at: [2, 1] }] } }] }));
  assert.equal(legacy.shapes?.length, 1);
  assert.equal(legacy.arrows?.[0].kind, "curve");
  assert.equal(legacy.arrows?.[0].style, "dashed");
  console.log("file.check: shape styles, TLC, tables and curves ok");
}

// A shadow's depth, softness and opacity survive a save; an opacity over 1 is refused.
{
  const box = { id: 7, kind: "box" as const, from: [0, 1] as [number, number], to: [2, 0] as [number, number], shadow: true, shade: { depth: 0.3, blur: 0.2, opacity: 0.6 } };
  assert.deepEqual(parse(serialize({ ...mol, shapes: [box] })).shapes?.[0].shade, box.shade);
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, shapes: [{ kind: "box", x1: 0, y1: 0, x2: 1, y2: 1, shade: { depth: 0.1, blur: 0, opacity: 3 } }] })), /damaged/);
  console.log("file.check: shadows ok");
}

// Rich captions: runs and a font survive a save; runs that do not spell the caption's text are refused.
{
  const cap = { id: 3, text: "H2O", x: 0, y: 0, font: "Georgia", runs: [{ text: "H" }, { text: "2", script: "sub" as const }, { text: "O", bold: true as const }] };
  const back = parse(serialize({ ...mol, captions: [cap] })).captions![0];
  assert.deepEqual({ font: back.font, runs: back.runs }, { font: cap.font, runs: cap.runs });
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, captions: [{ text: "H2O", x: 0, y: 0, runs: [{ text: "CO2" }] }] })), /damaged/);
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, captions: [{ text: "H", x: 0, y: 0, runs: [{ text: "H", onclick: "x" }] }] })), /damaged/);
  // A turned caption keeps its turn (CD-19); a turn that is not a number is refused.
  assert.equal(parse(serialize({ ...mol, captions: [{ id: 4, text: "x", x: 0, y: 0, angle: -54 }] })).captions![0].angle, -54);
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, captions: [{ text: "x", x: 0, y: 0, angle: "up" }] })), /damaged/);
  console.log("file.check: rich text ok");
}

// Groups survive a save: their atoms, and their other objects by kind and place; a group naming a missing object is refused.
{
  const m = { ...mol, arrows: [{ id: 40, kind: "reaction" as const, from: [0, 0] as [number, number], to: [3, 0] as [number, number] }], captions: [{ id: 41, text: "1", x: 0, y: -2 }],
    groups: [{ id: 50, atoms: [0, 1], items: [40, 41], integral: true as const }] };
  const back = parse(serialize(m));
  const g = back.groups![0];
  assert.deepEqual(g.atoms, [0, 1]);
  assert.deepEqual(g.items.map((id) => back.arrows?.some((a) => a.id === id) ? "arrow" : back.captions?.some((c) => c.id === id) ? "caption" : "?"), ["arrow", "caption"]);
  assert.equal(g.integral, true);
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, groups: [{ atoms: [], items: [["a", 3]] }] })), /damaged/);
  // Nested groups keep both levels and each its own Integral.
  const nested = parse(serialize({ ...m, groups: [{ id: 50, atoms: [0, 1, 2, 3, 4, 5], items: [40, 41] }, { id: 51, atoms: [], items: [40, 41], integral: true as const }] }));
  assert.deepEqual(nested.groups!.map((x) => [x.atoms.length, x.items.length, !!x.integral]), [[6, 2, false], [0, 2, true]]);
  // Read as an edit leaves groups (GRP-11): an atom twice is listed once, a group of one thing goes.
  const one = parse(JSON.stringify({ format: "octet", version: 1, structure: JSON.parse(serialize(mol)).structure, arrows: [{ kind: "reaction", x1: 0, y1: 0, x2: 3, y2: 0 }],
    groups: [{ atoms: [0], items: [] }, { atoms: [0, 0, 1], items: [["a", 0]] }] }));
  assert.deepEqual(one.groups!.map((x) => [x.atoms, x.items.length]), [[[0, 1], 1]]);
  console.log("file.check: groups ok");
}

// A catalytic cycle keeps its own line width (UI-42); a bad width is refused.
{
  const m = { ...mol, cycles: [{ id: 60, centre: [0, 0] as [number, number], radius: 3, clockwise: true, nodes: [[0, 1], [3, 4]], width: 1.2 }] };
  assert.equal(parse(serialize(m)).cycles?.[0].width, 1.2);
  const structure = JSON.parse(serialize(mol)).structure;
  assert.throws(() => parse(JSON.stringify({ format: "octet", version: 1, structure, cycles: [{ x: 0, y: 0, radius: 3, nodes: [[0], [3]], width: 0 }] })), /damaged/);
  console.log("file.check: cycle line width ok");
}

// Annotations from ChemDraw (keyword and content pairs) come back; a bad one makes the file damaged.
{
  const notes = { atoms: [], bonds: [], annotations: [{ keyword: "GUID", content: "5B5C3FE0" }, { keyword: "Name", content: "two\nlines" }] };
  assert.deepEqual(parse(serialize(notes)).annotations, notes.annotations);
  const bad = (annotations: unknown) => () => parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [], bonds: [] }, annotations }));
  assert.throws(bad([{ keyword: "GUID" }]), /damaged/);
  assert.throws(bad([{ keyword: "a\u0001", content: "" }]), /damaged/);
  assert.throws(bad({ keyword: "x", content: "y" }), /damaged/);
  assert.throws(bad(Array(1001).fill({ keyword: "k", content: "c" })), /damaged/);
  console.log("file.check: annotations ok");
}

// Decision 0007: each object's scale and the document's scale survive a save and reopen; a bad scale is refused.
{
  const m: Mol = {
    atoms: [{ label: "C", location: [0, 0, 0], scale: 2 }, { label: "O", location: [2, 0, 0], scale: 2, size: 12 }], bonds: [{ type: 1, atoms: [0, 1] }],
    arrows: [{ id: 1, kind: "reaction", from: [3, 0], to: [6, 0], scale: 1.5 }], shapes: [{ id: 2, kind: "table", from: [0, 3], to: [2, 2], scale: 3, table: { cells: [["a"]], widths: [60], weight: 0.05 } }],
    cycles: [{ id: 3, centre: [1, 0], radius: 2, clockwise: true, nodes: [[0], [1]], scale: 0.5 }], style: withScale(DEFAULT_STYLE, 4),
  };
  const again = parse(serialize(m));
  assert.deepEqual([again.atoms.map((a) => [a.scale, a.size]), again.arrows?.[0].scale, again.shapes?.[0].scale, again.shapes?.[0].table, again.cycles?.[0].scale, again.style], [[[2, undefined], [2, 12]], 1.5, 3, m.shapes![0].table, 0.5, m.style]);
  const base = { format: "octet", version: 1, structure: { atoms: [{ label: "C", x: 0, y: 0, scale: 0 }], bonds: [] } };
  assert.throws(() => parse(JSON.stringify(base)), /damaged/);
  assert.throws(() => parse(JSON.stringify({ ...base, structure: { atoms: [{ label: "C", x: 0, y: 0, scale: "2" }], bonds: [] } })), /damaged/);
  console.log("file.check: scales ok");
}

// The grid: only the steps Settings offers (1e-20 mm once hung Octet as it drew a line per step), and what the
// window shows, checked like the rest of the file.
{
  const base = { format: "octet", version: 1, structure: { atoms: [], bonds: [] } };
  for (const grid of [1e-20, 0.001, -1, 7, "5"]) assert.equal(parse(JSON.stringify({ ...base, style: { grid } })).style?.grid, "bond", String(grid));
  assert.equal(parse(JSON.stringify({ ...base, style: { grid: 20 } })).style?.grid, 20);
  const guides = { grid: true as const, rulers: true as const, crosshair: [0.5, -1] as [number, number] };
  assert.deepEqual(parse(serialize({ ...mol, guides })).guides, guides);
  assert.deepEqual(parse(serialize({ ...mol, guides: {} })).guides, {});
  assert.equal(parse(serialize(mol)).guides, undefined);
  assert.deepEqual(parse(JSON.stringify({ ...base, guides: { grid: 1, crosshair: [NaN, 0], rulers: "y" } })).guides, {});
  console.log("file.check: grid and guides ok");
}
