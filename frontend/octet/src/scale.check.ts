// Run: node src/scale.check.ts. Fails loudly if a document scale or an object's scale stops keeping sizes in
// proportion (decision 0007).
import assert from "node:assert/strict";
import { DEFAULT_STYLE, PRESETS, SIZES, presetAt, presetOf, readStyle, roundPt, sizesAt, withScale } from "./docstyle.ts";
import { fitSizes, fitTable, medianBond, scaleSettings, scaleSizes, sizeTable, transformParts } from "./edit.ts";
import { handlePoint, percentOf, resizeBy, sideAt, SIDES, type Box } from "./resize.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { tableLayout, type Mol, type Shape } from "./render.ts";

// The document scale multiplies every length and text size, keeps bond spacing, and keeps the preset's name.
{
  const big = withScale(DEFAULT_STYLE, 2.5);
  assert.deepEqual([big.bond, big.line, big.bold, big.margin, big.hash, big.labelSize, big.captionSize, big.spacing, big.scale], [36, 1.5, 5, 4, 6.25, 25, 25, 18, 2.5]);
  assert.equal(big.preset, "ACS Document 1996", "the preset's name at 250%");
  assert.deepEqual(withScale(big, 1), { ...DEFAULT_STYLE }, "back to 100% exactly");
  assert.equal(presetOf({ ...big, line: 1.6 }), "Custom", "one value changed by hand");
  assert.deepEqual(presetAt("RSC", 2), { ...PRESETS.RSC, bond: 24.4, line: 0.9, bold: 3.2, margin: 2.5, hash: 3.5, labelSize: 14, captionSize: 14 });
  // Every preset reaches 10% and 1000% in proportion: nothing read back falls to the default.
  for (const name of Object.keys(PRESETS)) for (const f of [0.1, 0.37, 5, 10]) {
    const s = withScale({ ...DEFAULT_STYLE, ...PRESETS[name], preset: name }, f), again = readStyle(JSON.parse(JSON.stringify(s)));
    assert.deepEqual(again, s, `${name} at ${f * 100}% reads back`);
    assert.equal(again.preset, name, `${name} at ${f * 100}% keeps its name`);
  }
  assert.equal(readStyle({ ...DEFAULT_STYLE, scale: 50 }).scale, 1, "a scale past 1000% is not read");
  // Any number of changes leaves a preset's values exact (33.33% once left a hash spacing of 2.5002, and Custom).
  let s = DEFAULT_STYLE;
  for (const f of [0.3333, 0.37, 7.77, 0.123, 1]) s = withScale(s, f);
  assert.deepEqual(s, { ...DEFAULT_STYLE }, "back to 100% exactly after many scales");
  const own = withScale({ ...DEFAULT_STYLE, line: 0.7, preset: "Custom" }, 2);
  assert.deepEqual([own.line, own.bond, own.preset], [1.4, 28.8, "Custom"], "a style of one's own multiplies");
  // A scale that would take a value past its limits stops at them: a 100 pt bond at 1000% fell back to 14.4 pt.
  const long = withScale(readStyle({ ...DEFAULT_STYLE, bond: 100 }), 10);
  assert.deepEqual([long.scale, long.bond, long.line], [7.2, 720, 4.32], "a 100 pt bond stops at 720%");
  assert.deepEqual(readStyle(JSON.parse(JSON.stringify(long))), long, "and reads back as it is");
  const thin = withScale(readStyle({ ...DEFAULT_STYLE, line: 0.05 }), 0.1);
  assert.deepEqual([thin.scale, thin.line], [0.2, 0.01], "a 0.05 pt line stops at 20%");
  assert.deepEqual([withScale(DEFAULT_STYLE, 50).scale, withScale(DEFAULT_STYLE, 0.01).scale], [10, 0.1], "1000% and 10% at most");
  console.log("scale.check: document scale ok");
}

// The size lists are ChemDraw's sizes times the document scale, to the nearest half point.
assert.deepEqual(sizesAt(1), [5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 24, 36]);
assert.deepEqual(sizesAt(2.5), [12.5, 15, 17.5, 20, 22.5, 25, 30, 35, 40, 45, 60, 90]);
// Below 5 pt the sizes go to a tenth, so no two in the list are the same at any scale.
assert.deepEqual(sizesAt(0.1), [0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.2, 1.4, 1.6, 1.8, 2.4, 3.6]);
for (let f = 0.1; f <= 10; f += 0.01) assert.equal(sizesAt(f).length, SIZES.length, `the sizes at ${Math.round(f * 100)}% are all different`);
assert.deepEqual([roundPt(0.04), roundPt(3.33), roundPt(5.2), roundPt(12.3)], [0.1, 3.3, 5, 12.5]);
console.log("scale.check: text sizes ok");

// A new document scale multiplies the sizes the drawing holds in points; Scale… with Labels and lines multiplies the
// chosen objects' scales and the sizes of their text.
{
  const m: Mol = {
    atoms: [{ label: "O", location: [0, 0, 0], size: 14 }, { label: "C", location: [1, 0, 0] }, { label: "N", location: [5, 0, 0], scale: 2 }],
    bonds: [{ type: 1, atoms: [0, 1] }],
    captions: [{ id: 1, text: "1", x: 0, y: 0, under: [0, 1] }, { id: 2, text: "ab", x: 0, y: 3, size: 12, runs: [{ text: "a", size: 8 }, { text: "b" }] }, { id: 3, text: "x", x: 3, y: 0, on: { arrow: 4, side: "above" } }],
    arrows: [{ id: 4, kind: "reaction", from: [2, 0], to: [4, 0] }],
    shapes: [{ id: 5, kind: "table", from: [0, 5], to: [3, 4], table: { cells: [["a"]], weight: 0.5 } }],
    cycles: [{ id: 6, centre: [0, 0], radius: 2, clockwise: true, nodes: [[0], [2]] }],
  };
  const r = scaleSizes(m, 2);
  assert.deepEqual([r.atoms[0].size, r.atoms[1].size, r.captions![0].size, r.captions![1].size, r.captions![1].runs, r.shapes![0].table!.weight], [28, undefined, undefined, 24, [{ text: "a", size: 16 }, { text: "b" }], 1]);
  assert.equal(scaleSizes(m, 1), m, "no change at the same scale");
  const s = scaleSettings(m, new Set([0, 1]), new Set([4, 6]), 2, 10);
  assert.deepEqual(s.atoms.map((a) => a.scale), [2, 2, 2], "the chosen atoms' scales (the third keeps its own)");
  assert.deepEqual([s.arrows![0].scale, s.shapes![0].scale, s.cycles![0].scale], [2, undefined, 2]);
  assert.deepEqual(s.captions!.map((c) => c.size), [20, 12, 20], "text under the atoms and on the arrow takes its size; other text keeps its own");
  const back = scaleSettings(s, new Set([0, 1]), new Set([4, 6]), 0.5, 10);
  assert.deepEqual([back.atoms[0].scale, back.atoms[1].scale, back.arrows![0].scale, "scale" in back.atoms[0]], [undefined, undefined, undefined, false], "back to 1: the scale is left unset");
  console.log("scale.check: sizes and object scales ok");
}

// A table's least sizes follow its scale: Size To Fit Contents and a dragged border.
{
  const sh: Shape = { id: 1, kind: "table", from: [0, 0.16], to: [1, 0], scale: 0.1, table: { cells: [["a"], ["b"]] } };
  const fit = { ...sh, ...fitTable(sh, (x) => x.length * 0.3) }, t = tableLayout(fit, (x) => x.length * 0.3);
  assert.ok(Math.abs(fit.from[1] - fit.to[1] - (t.y1 - t.y0)) < 1e-9 && Math.abs(t.h - 0.08) < 1e-9, "fitted rows are the least height at the table's scale");
  const dragged = sizeTable(sh, { heights: [0.1, 0.08] });
  assert.deepEqual(dragged.table!.heights, [0.1, 0.08], "a row of a small table keeps the height it is dragged to");
  console.log("scale.check: tables ok");
}

// An atom with no bonds (a counter-ion, a label on its own) keeps its scale in ChemDraw's copy too, from its LineWidth.
{
  const m: Mol = { atoms: [{ label: "P", text: "PF6", location: [0, 0, 0], charge: -1, scale: 2 }, { label: "C", location: [3, 0, 0], scale: 2 }, { label: "C", location: [4, 0, 0], scale: 2 }], bonds: [{ type: 1, atoms: [1, 2] }] };
  const text = toCdxml(m, DEFAULT_STYLE);
  const chemdraw = fromCdxml(text.replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, ""));
  assert.deepEqual(chemdraw.mol.atoms.map((a) => [a.scale, a.size]), [[2, undefined], [2, undefined], [2, undefined]]);
  // A structure whose settings do not agree keeps them on the bonds that carry them, as they came (REL-15).
  const two = fromCdxml(`<CDXML BondLength="14.40" LineWidth="0.60" BoldWidth="2" HashSpacing="2.50" MarginWidth="1.60" BondSpacing="18"><page><fragment>
<n id="1" p="100 100"/><n id="2" p="114.4 100"/><n id="3" p="128.8 100"/><b id="4" B="1" E="2" HashSpacing="2.70"/><b id="5" B="2" E="3"/></fragment></page></CDXML>`);
  assert.deepEqual([two.lost, two.mol.bonds.map((b) => b.own)], [{}, [{ HashSpacing: "2.70" }, undefined]]);
  console.log("scale.check: atoms on their own ok");
}

// IDEA-SCALE-4: a caption scales about its middle, wherever its anchor is. With Labels and lines its text grows with
// it (scaleSettings); without, it keeps its size and its middle.
{
  const m: Mol = { atoms: [], bonds: [], captions: [{ id: 1, text: "left text", x: 10, y: 5, align: "left" }] };
  const middle = new Map([[1, [12, 5.3] as [number, number]]]), about = ([x, y]: [number, number]): [number, number] => [12 + (x - 12) * 2, 5.3 + (y - 5.3) * 2];
  const on = transformParts(m, new Set(), new Set([1]), about, [2, 2], middle, 2).captions![0];
  assert.deepEqual([on.x, on.y], [8, 4.7], "the anchor moves away from the middle as the text grows");
  const off = transformParts(m, new Set(), new Set([1]), about, [2, 2], middle, 1).captions![0];
  assert.deepEqual([off.x, off.y], [10, 5], "the text keeps its size and its middle");
  const grown = scaleSettings(m, new Set(), new Set([1]), 2, 10).captions![0];
  assert.equal(grown.size, 20, "its size doubles from the document's");
  // A turn turns a caption about its middle, as ChemDraw turns text with the selection (CD-19): a lone caption keeps
  // its middle, and its anchor goes round it.
  const turned = transformParts(m, new Set(), new Set([1]), ([x, y]) => [12 - (y - 5.3), 5.3 + (x - 12)], [1, 1], middle).captions![0];
  assert.ok(Math.abs(turned.x - 12.3) < 1e-9 && Math.abs(turned.y - 3.3) < 1e-9 && turned.angle === 90, `${turned.x} ${turned.y} ${turned.angle}`);
  console.log("scale.check: captions ok");
}

// A flip goes through the same transform as a scale or a turn, and turns the objects over: a curved arrow bends and a
// half head points the other way, a single bracket faces the other way (across only), and a cycle runs the other way.
// The atoms are not moved again (flipAtoms turned them over first).
{
  const m: Mol = {
    atoms: [{ label: "C", location: [1, 0, 0] }], bonds: [],
    arrows: [{ id: 1, kind: "arrow", from: [0, 0], to: [2, 0], bend: 0.5, start: "left", end: "full" }],
    shapes: [{ id: 2, kind: "bracket", from: [0, 0], to: [1, 2], side: "left" }],
    cycles: [{ id: 3, centre: [0, 0], radius: 3, clockwise: true, nodes: [] }],
  };
  const across = ([x, y]: [number, number]): [number, number] => [4 - x, y], items = new Set([1, 2, 3]);
  const a = transformParts(m, new Set(), items, across, [1, 1], undefined, 1, "across");
  assert.deepEqual(a.atoms[0].location, [1, 0, 0], "the atoms stay as flipAtoms left them");
  assert.deepEqual([a.arrows![0].from, a.arrows![0].to, a.arrows![0].bend, a.arrows![0].start, a.arrows![0].end], [[4, 0], [2, 0], -0.5, "right", "full"]);
  assert.deepEqual([a.shapes![0].from, a.shapes![0].to, a.shapes![0].side], [[3, 0], [4, 2], "right"]);
  assert.deepEqual([a.cycles![0].centre, a.cycles![0].clockwise], [[4, 0], false]);
  const d = transformParts(m, new Set(), items, ([x, y]) => [x, -y], [1, 1], undefined, 1, "down");
  assert.equal(d.shapes![0].side, "left", "a bracket flipped down still faces the same way");
  assert.equal(transformParts(m, new Set(), items, across).arrows![0].bend, 0.5, "a move that is not a flip keeps the bend");
  console.log("scale.check: flips ok");
}

// IDEA-SCALE-5: the median bond counts only bonds with both atoms chosen; none gives undefined.
{
  const m: Mol = { atoms: [0, 1, 3, 6].map((x) => ({ label: "C", location: [x, 0, 0] as [number, number, number] })), bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }, { type: 1, atoms: [2, 3] }] };
  assert.equal(medianBond(m, new Set([0, 1, 2, 3])), 2);
  assert.equal(medianBond(m, new Set([2, 3])), 3);
  assert.equal(medianBond(m, new Set([0, 2])), undefined);
  console.log("scale.check: median bond ok");
}

// IDEA-SCALE-3: the resize handles. A corner scales in proportion about the opposite corner; Shift stretches it freely;
// Option scales about the middle; a side stretches one way; the soft stops hold near 100% and the bond stop.
{
  const b: Box = [0, 0, 4, 2];
  assert.deepEqual(handlePoint(b, "ne"), [4, 2]);
  assert.deepEqual(resizeBy(b, "ne", [8, 4], {}), { size: [2, 2], anchor: [0, 0] });
  assert.deepEqual(resizeBy(b, "ne", [8, 2], { shift: true }), { size: [2, 1], anchor: [0, 0] }, "Shift: across only");
  assert.deepEqual(resizeBy(b, "sw", [-2, -1], { alt: true }), { size: [2, 2], anchor: [2, 1] }, "Option: about the middle");
  assert.deepEqual(resizeBy(b, "ne", [7, 3], { about: [1, 1] }), { size: [2, 2], anchor: [1, 1] }, "about a moved centre mark");
  assert.deepEqual(resizeBy(b, "ne", [6, 3], { about: [1, 1], alt: true }).anchor, [2, 1], "Option still scales about the middle");
  assert.deepEqual(resizeBy(b, "e", [6, 9], {}), { size: [1.5, 1], anchor: [0, 1] }, "a side stretches across only");
  assert.deepEqual(resizeBy(b, "n", [9, 3], { shift: true }).size, [1.5, 1.5], "Shift on a side keeps proportion");
  assert.deepEqual(resizeBy(b, "ne", [4.1, 2.05], {}, [1, 1.25], 0.2).size, [1, 1], "the 100% stop holds");
  assert.deepEqual(resizeBy(b, "ne", [5.05, 2.5], {}, [1, 1.25], 0.2).size, [1.25, 1.25], "the bond stop holds");
  assert.deepEqual(resizeBy(b, "ne", [-5, -5], {}).size, [0.05, 0.05], "never flips");
  assert.deepEqual([percentOf([1.5, 1.5]), percentOf([1.2345, 1])], ["150%", "123.5% × 100%"]);
  // A handle takes the pointer near it, but not inside what the frame holds: a press on the top atom of a ring moves it.
  const held: Box = [0.2, 0.2, 3.8, 1.8];
  assert.equal(sideAt(b, SIDES, [2, 2.15], 0.3, held), "n");
  assert.equal(sideAt(b, SIDES, [2, 1.75], 0.3, held), undefined, "inside what the frame holds");
  assert.equal(sideAt(b, SIDES, [2, 1.75], 0.3), "n");
  assert.equal(sideAt(b, SIDES, [3, 2.1], 0.3, held), undefined, "not near a handle");
  console.log("scale.check: resize handles ok");
}

// IDEA-SCALE-10 and IDEA-SIZE-10: a paste from a drawing of other sizes. Captions go by the ratio of bond lengths
// (24 pt beside 30 pt bonds becomes 11.52 pt beside 14.4 pt bonds), own label sizes by the ratio of label sizes
// (8 pt in a 16 pt drawing becomes 7 pt in a 14 pt one).
{
  const m: Mol = { atoms: [{ label: "N", location: [0, 0, 0], size: 8 }, { label: "C", location: [1, 0, 0] }], bonds: [],
    captions: [{ id: 1, text: "a", x: 0, y: 0, size: 24 }, { id: 2, text: "b", x: 0, y: 0 }, { id: 3, text: "c", x: 0, y: 0, runs: [{ text: "c", size: 30 }] }],
    shapes: [{ id: 4, kind: "table", from: [0, 0], to: [1, 1], table: { cells: [["x"]], weight: 1 } }] };
  const from = { bond: 30, labelSize: 16, captionSize: 20.8333 }, to = { bond: 14.4, labelSize: 14, captionSize: 10 };
  const fit = fitSizes(m, from, to);
  assert.deepEqual([fit.atoms[0].size, fit.atoms[1].size], [7, undefined]);
  assert.deepEqual(fit.captions!.map((c) => c.size), [11.52, undefined, undefined], "the source's caption size lands on this drawing's, so it is left unset");
  assert.deepEqual([fit.captions![2].runs![0].size, fit.shapes![0].table!.weight], [14.4, 0.48]);
  assert.equal(fitSizes(m, to, to), m, "the same sizes change nothing");
  console.log("scale.check: paste sizes ok");
}

// A catalytic cycle's own line width (UI-42) is a size in points, so it goes with the document scale and a paste.
{
  const m: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [4, 0, 0] }], bonds: [], cycles: [{ id: 1, centre: [2, 0], radius: 2, clockwise: true, nodes: [[0], [1]], width: 1.2 }] };
  assert.equal(scaleSizes(m, 2).cycles![0].width, 2.4);
  assert.equal(fitSizes(m, { bond: 30, labelSize: 10, captionSize: 10 }, { bond: 15, labelSize: 10, captionSize: 10 }).cycles![0].width, 0.6);
  console.log("scale.check: cycle line width ok");
}
