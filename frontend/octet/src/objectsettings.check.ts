// Run: node src/objectsettings.check.ts. Fails loudly if Settings > Pro > Selection (ChemDraw's Object Settings, issue
// 76) stops reading or setting an object's own bond length, widths and text, or if a bond's own widths stop being
// drawn, saved, or written for ChemDraw.
import assert from "node:assert/strict";
import { DEFAULT_STYLE, frameStyle } from "./docstyle.ts";
import { fitSizes, objectSettings, scaleSizes, withObjectSettings } from "./edit.ts";
import { render, type Ink, type Mol } from "./render.ts";
import { parse, serialize } from "./file.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";

const s = DEFAULT_STYLE, all = (m: Mol) => new Set(m.atoms.map((_, i) => i));
// Ethane twice: one at the document's size, one at two thirds (an inset), with a caption and an arrow.
const mol: Mol = {
  atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [1, 0, 0] }, { label: "O", location: [5, 0, 0], scale: 2 / 3 }, { label: "C", location: [5.667, 0, 0], scale: 2 / 3 }],
  bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [2, 3] }],
  captions: [{ id: 1, text: "1", x: 0, y: -1 }],
  arrows: [{ id: 2, kind: "reaction", from: [2, 0], to: [4, 0] }],
};

// What the rows show: the first selected thing's values as drawn; nothing for what is not selected.
{
  const doc = objectSettings(mol, s, new Set([0, 1]), new Set());
  assert.deepEqual(doc, { bond: 14.4, line: 0.6, bold: 2, labelFont: "Arial", labelSize: 10 });
  const inset = objectSettings(mol, s, new Set([2, 3]), new Set([1]));
  assert.deepEqual(inset, { bond: 9.6, line: 0.4, bold: 1.3333, labelFont: "Arial", labelSize: 6.6667, captionFont: "Arial", captionSize: 10 });
  assert.deepEqual(objectSettings(mol, s, new Set(), new Set([2])), { bond: 14.4, line: 0.6 }, "an arrow: its size and line width");
  console.log("objectsettings.check: read ok");
}

// Setting them: each value is the one drawn, kept over the scale; the document's value is no value of its own.
{
  const set = withObjectSettings(mol, s, new Set([2, 3]), new Set([1, 2]), { line: 0.3, bold: 4 / 3, labelFont: "Helvetica", labelSize: 8, captionFont: "Calibri", captionSize: 12 });
  assert.deepEqual([set.bonds[1].line, set.bonds[1].bold], [0.45, undefined], "0.3 pt drawn at 2/3 is 0.45 of its own; 4/3 pt bold drawn is the document's");
  assert.equal(set.bonds[0], mol.bonds[0], "a bond not selected is left alone");
  assert.deepEqual([set.atoms[2].font, set.atoms[2].size, set.atoms[0].font], ["Helvetica", 12, undefined]);
  assert.deepEqual([set.captions![0].font, set.captions![0].size, set.arrows![0].width], ["Calibri", 12, 0.3]);
  assert.deepEqual(objectSettings(set, s, new Set([2, 3]), new Set([1])), { bond: 9.6, line: 0.3, bold: 1.3333, labelFont: "Helvetica", labelSize: 8, captionFont: "Calibri", captionSize: 12 }, "read back as set");
  // Reset to document (null): no settings of their own are left.
  const reset = { line: null, bold: null, labelFont: null, labelSize: null, captionFont: null, captionSize: null };
  const back = withObjectSettings(set, s, new Set([2, 3]), new Set([1, 2]), reset);
  assert.deepEqual([back.bonds[1].line, back.atoms[2].font, back.atoms[2].size, back.captions![0].font, back.captions![0].size, back.arrows![0].width], [undefined, undefined, undefined, undefined, undefined, undefined]);
  // A filled pen curve's outline is a hairline of its own; its default leaves it with none, and so does Reset.
  const curve: Mol = { atoms: [], bonds: [], arrows: [{ id: 1, kind: "curve", from: [0, 0], to: [1, 0], curve: { points: [{ at: [0, 0] }, { at: [1, 0] }, { at: [0, 1] }], closed: true }, fill: "solid", width: 1 }] };
  assert.equal(withObjectSettings(curve, s, new Set(), new Set([1]), { line: 0.05 }).arrows![0].width, undefined);
  assert.equal(withObjectSettings(curve, s, new Set(), new Set([1]), reset).arrows![0].width, undefined);
  // Widths kept over a small or large scale stay within what Octet's file takes, so the drawing opens again.
  const small: Mol = { atoms: [{ label: "C", location: [0, 0, 0], scale: 0.25 }, { label: "C", location: [1, 0, 0], scale: 0.25 }], bonds: [{ type: 1, atoms: [0, 1] }], arrows: [{ id: 1, kind: "reaction", from: [2, 0], to: [4, 0], scale: 0.25 }] };
  const wide = withObjectSettings(small, s, new Set([0, 1]), new Set([1]), { line: 60, bold: 120, labelSize: 999 });
  assert.deepEqual([wide.bonds[0].line, wide.bonds[0].bold, wide.arrows![0].width, wide.atoms[0].size], [200, 200, 200, 999]);
  assert.doesNotThrow(() => parse(serialize(wide)));
  const large: Mol = { ...small, atoms: small.atoms.map((a) => ({ ...a, scale: 4 })) };
  assert.equal(withObjectSettings(large, s, new Set([0, 1]), new Set(), { line: 0.01 }).bonds[0].line, 0.005);
  console.log("objectsettings.check: set ok");
}

// Drawn: a bond's own line width (times its scale) on the canvas and in every export, which use the same drawing.
{
  const S = frameStyle(s, 40), box: [number, number][] = [[0, 0], [9.6, -9.5]], ink = (): Ink => ({ width: 9.6, ascent: 9.5, outline: box });
  const width = (b: Partial<Mol["bonds"][number]>, scale?: number) => {
    const ys = render({ atoms: [{ label: "C", location: [0, 0, 0], scale }, { label: "C", location: [1, 0, 0], scale }], bonds: [{ type: 1, atoms: [0, 1], ...b }] }, S, ink).polygons.flat().map((p) => p[1]);
    return Math.max(...ys) - Math.min(...ys);
  };
  const plain = width({});
  assert.ok(Math.abs(width({ line: 1.2 }) / plain - 2) < 1e-9, "1.2 pt is twice the document's 0.6 pt");
  assert.ok(Math.abs(width({ line: 1.2 }, 0.5) / plain - 1) < 1e-9, "the scale multiplies it");
  assert.ok(Math.abs(width({ display: "bold", bold: 4 }) / width({ display: "bold" }) - 2) < 1e-9, "a bold bond at its own bold width");
  // A ring's circle and a π ligand's ellipse in the ring bonds' own line width (each bar is two half widths across).
  const ring = (line?: number): Mol => {
    const atoms: Mol["atoms"] = Array.from({ length: 6 }, (_, k) => ({ label: "C", location: [Math.cos((k * Math.PI) / 3), Math.sin((k * Math.PI) / 3), 0], circle: true }));
    return { atoms: [...atoms, { label: "C", location: [0, 0, 0], centre: { atoms: [0, 1, 2, 3, 4, 5] } }], bonds: atoms.map((_, k) => ({ type: 1 + (k % 2), atoms: [k, (k + 1) % 6], ...(line ? { line } : {}) })) };
  };
  const bars = (m: Mol, owner: (o: number) => boolean) => {
    const d = render(m, S, ink), k = d.owners!.findIndex(owner), [p, q] = d.polygons[k];
    return Math.hypot(p[0] - q[0], p[1] - q[1]);
  };
  const circle = (m: Mol) => ({ ...m, atoms: m.atoms.slice(0, 6), bonds: m.bonds });
  assert.ok(Math.abs(bars(circle(ring(1.2)), (o) => o === -1) / bars(circle(ring()), (o) => o === -1) - 2) < 1e-9, "a ring's circle");
  const ligand = (m: Mol) => ({ ...m, bonds: m.bonds.map((b) => ({ ...b, type: 4 })), atoms: m.atoms.map((a) => ({ ...a, circle: undefined })) });
  assert.ok(Math.abs(bars(ligand(ring(1.2)), (o) => o === -100006) / bars(ligand(ring()), (o) => o === -100006) - 2) < 1e-9, "a π ligand's ellipse");
  console.log("objectsettings.check: drawn ok");
}

// Saved: Octet's file keeps the widths; CDXML gives ChemDraw every setting of the bond (so it draws it as Octet does)
// and gives them back to Octet exactly. ChemDraw's copy (Octet's data dropped) does not take them for a scale.
{
  const own = withObjectSettings(mol, s, new Set([0, 1, 2, 3]), new Set(), { line: 0.3 });
  assert.deepEqual(parse(serialize(own)).bonds.map((b) => [b.line, b.bold]), [[0.3, undefined], [0.45, undefined]]);
  assert.throws(() => parse(serialize(own).replace('"line": 0.3', '"line": 1e9')), /damaged/);
  const text = toCdxml(own, s), first = text.match(/<b\s[^>]*\/>/)![0];
  for (const a of ['LineWidth="0.30"', 'BoldWidth="2"', 'BondLength="14.40"', 'HashSpacing="2.50"', 'MarginWidth="1.60"']) assert.ok(first.includes(a), `written: ${a} in ${first}`);
  const back = fromCdxml(text).mol;
  assert.deepEqual([back.bonds.map((b) => b.line), back.bonds.map((b) => b.own), back.atoms.map((a) => a.scale)], [[0.3, 0.45], [undefined, undefined], [undefined, undefined, 2 / 3, 2 / 3]]);
  const chemdraw = fromCdxml(text.replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "")).mol;
  assert.deepEqual([chemdraw.atoms[0].scale, chemdraw.bonds[0].line, chemdraw.bonds[0].own?.LineWidth], [undefined, undefined, "0.30"]);
  // Without widths of their own, bonds are written as before.
  assert.doesNotMatch(toCdxml(mol, s).match(/<b\s[^>]*\/>/)![0], /LineWidth/);
  console.log("objectsettings.check: saved ok");
}

// Sizes in points follow the document's scale and a paste into a drawing of another bond length, as an arrow's do.
{
  const own = withObjectSettings(mol, s, new Set([0, 1]), new Set(), { line: 0.3, bold: 1 });
  assert.deepEqual([scaleSizes(own, 2).bonds[0].line, scaleSizes(own, 2).bonds[0].bold], [0.6, 2]);
  assert.equal(fitSizes(own, s, { ...s, bond: 28.8 }).bonds[0].line, 0.6);
  console.log("objectsettings.check: sizes ok");
}
