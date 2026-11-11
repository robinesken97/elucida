// Run: node src/render.check.ts. Fails loudly if the ACS drawing rules break.
import assert from "node:assert/strict";
import { ALL_ARROW_KINDS, SHAPE_KINDS, arrowShapes, blockOutline, ellipseArrow, fitArrows, headOfLength, headSize, lineOffsets, markAt, placeCaptions, render, renderParts, shapeInk, shapePaths, sizeOf, spotPath, tableLayout, tlcLayout, turnedWith, type Arrow, type Atom, type Bond, type Box, type Caption, type Drawing, type Face, type Ink, type Mol, type PartCache, type Shape } from "./render.ts";
import { layoutCycles, type Cycle } from "./cycle.ts";
import { arialGlyph } from "./cdxml.ts";

type P = [number, number];
const pt = 4 / 3;
const S = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
// Every glyph is a 9.6 x 9.5 px box (roughly an Arial capital at 10 pt); its outline is the box edge.
const box: P[] = [];
for (let i = 0; i <= 40; i++) { const f = i / 40; box.push([9.6 * f, 0], [9.6 * f, -9.5], [0, -9.5 * f], [9.6, -9.5 * f]); }
const ink = (): Ink => ({ width: 9.6, ascent: 9.5, outline: box });
const has = (poly: P[], q: P) => poly.some((p) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-6);
const centroid = (poly: P[]) => poly.reduce<P>((c, p) => [c[0] + p[0] / poly.length, c[1] + p[1] / poly.length], [0, 0]);

// Pyridine: N at atom 0, double bonds 0=1, 2=3, 4=5, hexagon of unit bonds.
const hex = [...Array(6)].map((_, i) => [Math.cos((Math.PI / 3) * i + Math.PI / 6), Math.sin((Math.PI / 3) * i + Math.PI / 6), 0] as [number, number, number]);
const pyridine: Mol = {
  atoms: hex.map((location, i) => ({ label: i ? "C" : "N", location })),
  bonds: [0, 1, 2, 3, 4, 5].map((i) => ({ type: i % 2 ? 1 : 2, atoms: [i, (i + 1) % 6] as [number, number] })),
};
const d = render(pyridine, S, ink);
const L = S.bond, at = (i: number): P => [hex[i][0] * L, -hex[i][1] * L];
// Six axis polygons and three inner lines, each inner line inside the ring and shorter than a bond.
assert.equal(d.polygons.length, 9);
const inner = d.polygons.filter((poly) => Math.hypot(...centroid(poly)) < L * Math.cos(Math.PI / 6) - 1);
assert.equal(inner.length, 3, "three inner lines sit inside the ring");
for (const poly of inner) assert.ok(Math.hypot(poly[2][0] - poly[1][0], poly[2][1] - poly[1][1]) < L * 0.85, "inner line is trimmed");
// Carbons meet in a mitred fan through the atom centre: atom 3 is shared by both of its bond polygons.
assert.equal(d.polygons.filter((poly) => has(poly, at(3))).length, 2, "both bonds at C3 pass through its centre");
// Nothing is drawn within the margin of N's glyph box.
const [nx, ny] = at(0), [bx, by] = [nx - 4.8, ny + 4.75];
for (const [x, y] of d.polygons.flat()) {
  const dx = Math.max(bx - x, 0, x - (bx + 9.6)), dy = Math.max(by - 9.5 - y, 0, y - by);
  assert.ok(Math.hypot(dx, dy) > S.margin - 0.01, "bonds stop outside the label margin");
}
assert.equal(d.labels.length, 1);
console.log("render.check: pyridine ok");

// A hashed wedge has round(length / (Hash Spacing + line width)) marks. Where another bond meets its wide end the last mark is left
// out, as ChemDraw draws it, so that bond's line takes its place in the count (issue 7).
{
  const C = (x: number, y: number): Atom => ({ label: "C", location: [x, y, 0] });
  const alone = render({ atoms: [C(0, 0), C(0, -1)], bonds: [{ type: 1, atoms: [0, 1], stereo: 6 }] }, S, ink).polygons.length;
  const joined = render({ atoms: [C(0, 0), C(0, -1), C(0.87, -1.5)], bonds: [{ type: 1, atoms: [0, 1], stereo: 6 }, { type: 1, atoms: [1, 2] }] }, S, ink).polygons.length;
  assert.ok(alone > 2, "a hashed wedge has marks");
  assert.equal(joined, alone, "the last mark is left out where a bond meets the wide end");
  // Hash Spacing is the gap between marks: ChemDraw draws 4 marks, 6 pt apart, on a 30 pt hashed wedge joined at its
  // wide end at 5 pt spacing and 1 pt lines (issue 7).
  const nd = { ...S, bond: 30 * pt, line: pt, bold: 4 * pt, hash: 5 * pt, spacing: 0.12 * 30 * pt };
  const ndAlone = render({ atoms: [C(0, 0), C(0, -1)], bonds: [{ type: 1, atoms: [0, 1], stereo: 6 }] }, nd, ink).polygons;
  const ndJoined = render({ atoms: [C(0, 0), C(0, -1), C(0.87, -1.5)], bonds: [{ type: 1, atoms: [0, 1], stereo: 6 }, { type: 1, atoms: [1, 2] }] }, nd, ink).polygons;
  assert.equal(ndAlone.length, 5, "5 marks on a 30 pt hashed wedge at 5 pt spacing");
  assert.equal(ndJoined.length, 4 + 1, "4 marks where a bond meets the wide end, and that bond");
  const ys = ndAlone.map((poly) => centroid(poly)[1]).sort((a, b) => b - a);
  assert.ok(Math.abs(ys[0] - ys[1] - 6 * pt) < 1e-6, "marks 6 pt apart");
}

// An allene laid out with rounding (Indigo's 0.49999991 for 0.5): its two double bonds meet end to end at the middle
// atom, with nothing drawn far away.
{
  const allene: Mol = {
    atoms: [[-1.7321, 0], [-0.866, -0.5], [0, 0], [0.866025447, 0.49999991], [1.7321, 0]].map(([x, y]) => ({ label: "C", location: [x, y, 0] as [number, number, number] })),
    bonds: [{ type: 1, atoms: [1, 0] }, { type: 2, atoms: [1, 2] }, { type: 2, atoms: [2, 3] }, { type: 1, atoms: [3, 4] }],
  };
  const far = Math.max(...render(allene, S, ink).polygons.flat().map(([x, y]) => Math.hypot(x, y)));
  assert.ok(far < 2.5 * L, `an allene's bonds stay near it (${far.toFixed(0)} px)`);
}

// Isobutane centre: three bonds share the atom-centre vertex.
const iso = render({
  atoms: [{ label: "C", location: [0, 0, 0] }, ...[90, 210, 330].map((a) => ({ label: "C", location: [Math.cos((a * Math.PI) / 180), Math.sin((a * Math.PI) / 180), 0] as [number, number, number] }))],
  bonds: [1, 2, 3].map((j) => ({ type: 1, atoms: [0, j] as [number, number] })),
}, S, ink);
assert.equal(iso.polygons.filter((poly) => has(poly, [0, 0])).length, 3, "fan shares the centre");
console.log("render.check: fan ok");

// Acetone: the centred C=O lines run 0.748 pt past the carbonyl carbon (h · cot 120°).
const acetone = render({
  atoms: [{ label: "C", location: [0, 0, 0] }, { label: "O", location: [0, 1, 0] }, { label: "C", location: [-0.866, -0.5, 0] }, { label: "C", location: [0.866, -0.5, 0] }],
  bonds: [{ type: 2, atoms: [0, 1] }, { type: 1, atoms: [0, 2] }, { type: 1, atoms: [0, 3] }],
}, S, ink);
const co = acetone.polygons.filter((poly) => poly.length === 4 && Math.abs(poly[0][1] - poly[3][1]) > 5);
assert.equal(co.length, 2, "two C=O lines");
for (const poly of co) assert.ok(Math.abs(poly[0][1] - 0.748 * pt) < 0.01, "C=O line starts 0.748 pt past the carbon");
console.log("render.check: carbonyl ok");

// Methylamine drawn left to right: NH2 reads N, H, then a smaller subscript 2, all to the right of the atom.
const amine = render({ atoms: [{ label: "C", location: [0, 0, 0] }, { label: "N", location: [1, 0, 0] }], bonds: [{ type: 1, atoms: [0, 1] }] }, S, ink);
assert.deepEqual(amine.labels.map((l) => l.text), ["N", "H", "2"]);
assert.ok(amine.labels[1].x > amine.labels[0].x && amine.labels[2].x > amine.labels[1].x, "H2 follows N");
assert.ok(amine.labels[2].size < amine.labels[1].size && amine.labels[2].y > amine.labels[1].y, "2 is a subscript");
console.log("render.check: amine ok");

// Nitro group: N+ and O– get their charge signs; neither gets an H.
const nitro = render({
  atoms: [{ label: "C", location: [0, 0, 0] }, { label: "N", location: [1, 0, 0], charge: 1 }, { label: "O", location: [1.5, 0.87, 0] }, { label: "O", location: [1.5, -0.87, 0], charge: -1 }],
  bonds: [{ type: 1, atoms: [0, 1] }, { type: 2, atoms: [1, 2] }, { type: 1, atoms: [1, 3] }],
}, S, ink);
assert.deepEqual(nitro.labels.map((l) => l.text).sort(), ["+", "N", "O", "O", "–"].sort());
console.log("render.check: charges ok");

// Carbocation: no C label, just the + beside the vertex, and the carbon still joins its bonds in a fan.
const cation = render({
  atoms: [{ label: "C", location: [0, 0, 0], charge: 1 }, ...[90, 210, 330].map((a) => ({ label: "C", location: [Math.cos((a * Math.PI) / 180), Math.sin((a * Math.PI) / 180), 0] as [number, number, number] }))],
  bonds: [1, 2, 3].map((j) => ({ type: 1, atoms: [0, j] as [number, number] })),
}, S, ink);
assert.deepEqual(cation.labels.map((l) => l.text), ["+"]);
assert.equal(cation.polygons.filter((poly) => has(poly, [0, 0])).length, 3, "charged carbon keeps its fan");
console.log("render.check: carbocation ok");

// Written labels read away from their bond: OMe on a bond from the left reads OMe; from the right, MeO.
const methoxy = (fromRight: boolean) => render({
  atoms: [{ label: "C", location: [fromRight ? 1 : 0, 0, 0] }, { label: "O", text: "OMe", location: [fromRight ? 0 : 1, 0, 0] }],
  bonds: [{ type: 1, atoms: [0, 1] }],
}, S, ink);
assert.deepEqual(methoxy(false).labels.map((l) => l.text), ["O", "Me"]);
assert.deepEqual(methoxy(true).labels.map((l) => l.text), ["Me", "O"]);
// CO2Et from the right reads EtO2C, with the 2 as a subscript.
const ester = render({
  atoms: [{ label: "C", location: [1, 0, 0] }, { label: "C", text: "CO2Et", location: [0, 0, 0] }],
  bonds: [{ type: 1, atoms: [0, 1] }],
}, S, ink);
assert.deepEqual(ester.labels.map((l) => l.text), ["Et", "O", "2", "C"]);
assert.ok(ester.labels[2].size < ester.labels[1].size, "2 is a subscript");
console.log("render.check: written labels ok");

// A label reads the same distance off its atom either way. Read left to right, its first glyph sits centred on the
// atom. Read right to left, a label that ends with that glyph (HO, MeO, F3C, ⁻O) keeps it centred; one that does not
// (Br, Ph, R₁) ends its ink as far right of the atom as it starts left of it the other way. Bonds stop at the glyph
// they meet, or at the label's box where that glyph changes with the reading direction, so a bond into a label from
// the left and its mirror image from the right show the same length. A charge goes before a label read right to left,
// away from its bonds. A subscript or raised mass number on the bond's side (R₁ read right to left, ¹³CH₃ read left to
// right) still stops that bond early: those pairs are not compared. Glyphs here have Arial's advances and ink edges,
// capitals and tall letters at the cap height and short letters (r, e) at the x-height, each outline its ink box.
{
  const cap = 0.716 * S.size, xh = 0.519 * S.size;
  const metrics = (ch: string) => arialGlyph(ch).map((v) => (v * S.size) / 1000);
  const height = (ch: string): [number, number] => (/[gjpqy]/.test(ch) ? [-0.21 * S.size, xh] : /[acemnorsuvwxz]/.test(ch) ? [0, xh] : ch === "+" ? [0.11 * S.size, 0.58 * S.size] : ch === "–" ? [0.22 * S.size, 0.3 * S.size] : [0, cap]);
  const arial = (text: string): Ink => {
    const outline: P[] = [];
    let x = 0, top = 0;
    for (const ch of text) {
      const [w, l, r] = metrics(ch), [lo, hi] = height(ch);
      for (let k = 0; k <= 20; k++) { const f = k / 20; outline.push([x + l + (r - l) * f, -lo], [x + l + (r - l) * f, -hi], [x + l, -lo - (hi - lo) * f], [x + r, -lo - (hi - lo) * f]); }
      x += w; top = Math.max(top, hi);
    }
    return { width: x, ascent: top, outline };
  };
  type Run = Drawing["labels"][number];
  const k = (l: Run) => l.size / S.size, advance = (l: Run) => [...l.text].reduce((w, ch) => w + metrics(ch)[0], 0) * k(l);
  const inkLeft = (l: Run) => l.x + metrics(l.text[0])[1] * k(l), inkRight = (l: Run) => l.x + advance(l) - (metrics(l.text.slice(-1))[0] - metrics(l.text.slice(-1))[2]) * k(l);
  // The visible length of the bond from labelled atom X to atom Y: its polygon, along the bond.
  const shows = (d: Drawing, X: P, Y: P) => {
    const l = Math.hypot(Y[0] - X[0], Y[1] - X[1]), u: P = [(Y[0] - X[0]) / l, (Y[1] - X[1]) / l];
    const along = (q: P) => (q[0] - X[0]) * u[0] + (q[1] - X[1]) * u[1], across = (q: P) => Math.abs((q[0] - X[0]) * u[1] - (q[1] - X[1]) * u[0]);
    const a = d.polygons.find((poly) => poly.every((q) => across(q) < 1.5 && along(q) > -1 && along(q) < l + 2))!.map(along);
    return Math.min(l, Math.max(...a)) - Math.min(...a);
  };
  // Each label, how it reads on the left of its bond, and whether it ends with the glyph it starts with read the other way.
  const cases: [string, Partial<Atom> & { label: string }, string, boolean][] = [
    ["Br", { label: "Br" }, "Br", false], ["Cl", { label: "Cl" }, "Cl", false], ["Ph", { label: "C", text: "Ph" }, "Ph", false], ["Me", { label: "C", text: "Me" }, "Me", false],
    ["TMS", { label: "Si", text: "TMS" }, "TMS", false], ["SiMe3", { label: "Si", text: "SiMe3" }, "Me3Si", false], ["R1", { label: "C", text: "R1" }, "R1", false],
    ["Et", { label: "C", text: "Et" }, "Et", false], ["Ts", { label: "S", text: "Ts" }, "Ts", false],
    ["CF3", { label: "C", text: "CF3" }, "F3C", true], ["OMe", { label: "O", text: "OMe" }, "MeO", true], ["OH", { label: "O" }, "HO", true], ["NH2", { label: "N" }, "H2N", true],
    ["CO2Me", { label: "C", text: "CO2Me" }, "MeO2C", true], ["O–", { label: "O", charge: -1 }, "–O", true], ["NH3+", { label: "N", charge: 1 }, "+H3N", true],
    ["O2–", { label: "O", charge: -2 }, "2–O", true], ["13CH3", { label: "C", isotope: 13 }, "H313C", true], ["F", { label: "F" }, "F", true],
  ];
  let mirrored = 0;
  const compared = new Map<string, number>();
  for (const [name, atom, shown, same] of cases) for (const deg of [0, 30, 60, -30, -60]) {
    // Two carbons, the label on each end, its bond deg above the horizontal: the left label reads right to left.
    const t = (deg * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t);
    const mol: Mol = { atoms: [{ label: "C", location: [-0.5, 0, 0] }, { label: "C", location: [0.5, 0, 0] }, { ...atom, location: [-0.5 - c, s, 0] }, { ...atom, location: [0.5 + c, s, 0] }], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [0, 2] }, { type: 1, atoms: [1, 3] }] };
    const d = render(mol, S, arial), at = (i: number): P => [mol.atoms[i].location[0] * L, -mol.atoms[i].location[1] * L];
    const runs = (i: number) => d.labels.filter((_, j) => Math.hypot(d.labelAt[j][0] - at(i)[0], d.labelAt[j][1] - at(i)[1]) < 1e-9).sort((p, q) => p.x - q.x);
    const [left, right] = [runs(2), runs(3)], label = `${name} at ${deg}°`;
    assert.equal(left.map((l) => l.text).join(""), shown, `${name} on the left reads ${shown}`);
    for (const rs of [left, right]) rs.slice(1).forEach((l, j) => assert.ok(l.x >= rs[j].x + advance(rs[j]) - 1e-9, `${label}: ${l.text} clear of ${rs[j].text}`));
    // The line: the runs on the attaching baseline and their subscripts, not a raised charge or mass number.
    const line = (rs: Run[]) => { const base = rs.find((l) => l.size === S.size)!.y; return rs.filter((l) => l.size === S.size || l.y > base); };
    if (same) {
      // The glyph a bond meets is the same both ways, and stays centred on its atom.
      const end = line(left).filter((l) => l.size === S.size).pop()!, start = line(right).find((l) => l.size === S.size)!;
      assert.ok(end.text.length === 1 && Math.abs(end.x + advance(end) / 2 - at(2)[0]) < 1e-9, `${label}: its ${end.text} centred on the left`);
      assert.ok(Math.abs(start.x + metrics(start.text[0])[0] * k(start) / 2 - at(3)[0]) < 1e-9, `${label}: its ${start.text[0]} centred on the right`);
    } else {
      const ends = Math.max(...line(left).map(inkRight)) - at(2)[0], starts = at(3)[0] - Math.min(...line(right).map(inkLeft));
      assert.ok(Math.abs(ends - starts) < 1e-9, `${label}: its ink starts as far from the atom on each side (${(ends / pt).toFixed(3)} and ${(starts / pt).toFixed(3)} pt)`);
    }
    // A subscript or raised sign on the bond's side of either atom stops that bond early: those are not mirrors.
    const small = (rs: Run[], i: number, side: number) => rs.some((l) => l.size < S.size && (side > 0 ? inkRight(l) > at(i)[0] : inkLeft(l) < at(i)[0]));
    if (small(left, 2, 1) || small(right, 3, -1)) continue;
    const [l, r] = [shows(d, at(2), at(0)), shows(d, at(3), at(1))];
    assert.ok(l < L - 1 && Math.abs(l - r) < 0.01 * pt, `${label}: both bonds show the same length (${(l / pt).toFixed(3)} and ${(r / pt).toFixed(3)} pt)`);
    mirrored++;
    compared.set(name, (compared.get(name) ?? 0) + 1);
  }
  assert.ok(mirrored >= 80, `${mirrored} mirrored pairs compared`);
  for (const name of ["Br", "Ph", "Me", "Cl", "SiMe3", "OH", "OMe", "NH2", "CO2Me", "CF3", "O–", "O2–", "NH3+"]) assert.equal(compared.get(name), 5, `${name} compared at every angle`);
  // The user's 1,3-dibromo-2,2-dimethylpropane, a zigzag with Br at both ends: both C–Br bonds show the same length
  // (10.19 and 9.17 pt in Arial before).
  const zig: [number, number][] = [[0, 0], [0.866, 0.5], [1.732, 0], [2.598, 0.5], [3.464, 0], [1.232, -0.866], [2.232, -0.866]];
  const dibromo = render({ atoms: zig.map(([x, y], k) => ({ label: k === 0 || k === 4 ? "Br" : "C", location: [x, y, 0] as [number, number, number] })), bonds: [[0, 1], [1, 2], [2, 3], [3, 4], [2, 5], [2, 6]].map((atoms) => ({ type: 1, atoms: atoms as [number, number] })) }, S, arial);
  const z = (i: number): P => [zig[i][0] * L, -zig[i][1] * L], [l, r] = [shows(dibromo, z(0), z(1)), shows(dibromo, z(4), z(3))];
  assert.ok(l < L - 1 && Math.abs(l - r) < 0.01 * pt, `both C–Br bonds show the same length (${(l / pt).toFixed(3)} and ${(r / pt).toFixed(3)} pt)`);
  console.log(`render.check: label symmetry ok (${mirrored} mirrored bonds)`);

  // A label of more than one line (ChemDraw's Option-Return in a label, as Sam's "Direct,\nNo ISC"): the attaching line
  // sits on the atom as that line alone would start (its first glyph centred), the next line 1.2 em below (a caption's
  // automatic spacing), each line read as typed. Bonds stop at the box round each line, so a bond down from the atom
  // stops below the second line. Right to left the lines end together, the attaching line's last glyph centred on the
  // atom; centred, each line is centred on it; stacked above, the last line is the attaching one.
  const lined = (text: string, to: P, more: Partial<Atom> = {}) => {
    const m: Mol = { atoms: [{ label: "C", text, location: [0, 0, 0], ...more }, { label: "C", location: [to[0], to[1], 0] }], bonds: [{ type: 1, atoms: [0, 1] }] };
    const dd = render(m, S, arial), runs = dd.labels.filter((_, j) => Math.hypot(dd.labelAt[j][0], dd.labelAt[j][1]) < 1e-9);
    const rows = [...new Set(runs.filter((l) => l.size === S.size).map((l) => l.y))].sort((p, q) => p - q).map((y) => runs.filter((l) => Math.abs(l.y - y) < 1e-9 || (l.size < S.size && l.y > y && l.y - y < 0.3 * S.size)).sort((p, q) => p.x - q.x));
    return { d: dd, rows, text: rows.map((r) => r.map((l) => l.text).join("")) };
  };
  const left = lined("Direct,\nNo ISC", [0, -1]);
  assert.deepEqual(left.text, ["Direct,", "No ISC"]);
  assert.ok(Math.abs(left.rows[0][0].x + metrics("D")[0] / 2) < 1e-9, "the first glyph centred on the atom");
  assert.ok(Math.abs(left.rows[1][0].x - left.rows[0][0].x) < 1e-9, "the second line starts where the first does");
  assert.ok(Math.abs(left.rows[1][0].y - left.rows[0][0].y - 1.2 * S.size) < 1e-9, "the second line 1.2 em below");
  const lowest = Math.max(...left.rows[1].map((l) => l.y));
  const bondTop = Math.min(...left.d.polygons.flat().map((q) => q[1]));
  assert.ok(bondTop > lowest + S.margin - 0.01, `the bond down from the atom stops below the second line (${bondTop.toFixed(2)} px, line at ${lowest.toFixed(2)})`);
  assert.deepEqual(left.d.label[0]![3] >= lowest - 1e-9 && left.d.label[0]![1] < left.rows[0][0].y - 0.7 * S.size, true, "the label's box holds both lines");
  // Counts are subscripts on every line.
  assert.deepEqual(lined("OMe\nCH2Cl2", [0, -1]).rows[1].map((l) => [l.text, l.size < S.size]), [["C", false], ["H", false], ["2", true], ["Cl", false], ["2", true]]);
  const right = lined("Ab\nCde", [1, 0]), end = (row: Run[]) => row[row.length - 1].x + advance(row[row.length - 1]);
  assert.deepEqual(right.text, ["Ab", "Cde"], "never reversed");
  assert.ok(Math.abs(end(right.rows[0]) - metrics("b")[0] / 2) < 1e-9 && Math.abs(end(right.rows[1]) - end(right.rows[0])) < 1e-9, "right to left, the lines end together");
  const mid = lined("Ab\nCde", [1, 0], { align: "centre" });
  for (const row of mid.rows) assert.ok(Math.abs(row[0].x + end(row) - 0) < 1e-9, "centred lines");
  const up = lined("Ab\nCde", [0, -1], { align: "above" });
  assert.ok(Math.abs(up.rows[1][0].y - (up.rows[0][0].y + 1.2 * S.size)) < 1e-9 && up.text[1] === "Cde" && up.rows[1][0].y > 0, "stacked above, the last line on the atom");
  // A charge goes after the attaching line.
  const charged = lined("NMe3\nsalt", [-1, 0], { label: "N", charge: 1 });
  assert.ok(charged.d.labels.some((l) => l.text === "+" && l.y < charged.rows[0][0].y && l.x > charged.rows[0][0].x), "the sign by the first line");
  console.log("render.check: labels of more than one line ok");

  // A stacked H sits 8.35 pt from the N, baseline to baseline, in Arial 10 pt: ChemDraw 22.2's stacked NH, above and
  // below, in Sam's CDXML files (8.35, 8.36 and 8.35 pt). Indole's NH stacks under the N, NH2 stacked by hand puts H2
  // under it, NH stacked above puts the H over it, and a written label stacked (OMe) puts Me under the O.
  {
    const gap = (atom: Partial<Atom> & { label: string }, nbrs: P[], first: string, next: string) => {
      const m: Mol = { atoms: [{ ...atom, location: [0, 0, 0] }, ...nbrs.map(([x, y]): Atom => ({ label: "C", location: [x, y, 0] }))], bonds: nbrs.map((_, k) => ({ type: 1, atoms: [0, k + 1] as [number, number] })) };
      const runs = render(m, S, arial).labels;
      return (runs.find((l) => l.text === next)!.y - runs.find((l) => l.text === first)!.y) / pt;
    };
    const ring: P[] = [[-0.866, 0.5], [0.866, 0.5]];
    for (const [name, g] of [
      ["indole NH", gap({ label: "N" }, ring, "N", "H")],
      ["NH2 stacked below", gap({ label: "N", align: "below" }, [[0, 1]], "N", "H")],
      ["NH stacked above", -gap({ label: "N", align: "above" }, ring, "N", "H")],
      ["OMe stacked below", gap({ label: "O", text: "OMe", align: "below" }, [[0, 1]], "O", "Me")],
    ] as const) assert.ok(Math.abs(g - 8.35) < 0.01, `${name}: stacked 8.35 pt apart (${g.toFixed(3)} pt)`);
    assert.ok(Math.abs(gap({ label: "N", align: "below" }, [[0, 1]], "H", "2") - 0.212 * 10) < 1e-9, "the 2 of a stacked NH2 is a subscript on the H");
  }
  console.log("render.check: stacked H ok");

  // A written label with some characters bold (its runs, styled as it is typed): each piece is drawn in its own style
  // and measured in it (bold here is 10% wider), so what follows a bold piece moves along by its bold width. Read right
  // to left (MeO), each unit keeps its own style, and the O still sits on the atom. On two lines, the same.
  const wider = (text: string, face?: Face): Ink => { const m = arial(text), f = face?.bold ? 1.1 : 1; return { width: m.width * f, ascent: m.ascent, outline: m.outline.map(([px, py]): P => [px * f, py]) }; };
  const styledAt = (text: string, to: P, runs: Atom["runs"]) => {
    const dd = render({ atoms: [{ label: "O", text, runs, location: [0, 0, 0] }, { label: "C", location: [to[0], to[1], 0] }], bonds: [{ type: 1, atoms: [0, 1] }] }, S, wider);
    return dd.labels.filter((_, j) => Math.hypot(dd.labelAt[j][0], dd.labelAt[j][1]) < 1e-9).sort((p, q) => p.y - q.y || p.x - q.x);
  };
  const ltr = styledAt("OMe", [-1, 0], [{ text: "O", bold: true }, { text: "Me" }]);
  assert.deepEqual(ltr.map((l) => [l.text, !!l.bold]), [["O", true], ["Me", false]]);
  assert.ok(Math.abs(ltr[1].x - ltr[0].x - 1.1 * metrics("O")[0]) < 1e-9, "Me starts after the bold O's bold width");
  const rtl = styledAt("OMe", [1, 0], [{ text: "O", bold: true }, { text: "Me" }]);
  assert.deepEqual(rtl.map((l) => [l.text, !!l.bold]), [["Me", false], ["O", true]]);
  assert.ok(Math.abs(rtl[1].x + (1.1 * metrics("O")[0]) / 2) < 1e-9, "the bold O centred on the atom");
  // Inside a unit (Me with only the e bold) the unit is drawn in two pieces.
  assert.deepEqual(styledAt("OMe", [-1, 0], [{ text: "OM" }, { text: "e", bold: true }]).map((l) => [l.text, !!l.bold]), [["O", false], ["M", false], ["e", true]]);
  // Runs that do not spell the text (left from an older edit) are not used.
  assert.deepEqual(styledAt("OMe", [-1, 0], [{ text: "OH", bold: true }]).map((l) => [l.text, !!l.bold]), [["O", false], ["Me", false]]);
  const two = styledAt("OMe\nCH2Cl2", [-1, 0], [{ text: "OMe\n" }, { text: "CH2", bold: true }, { text: "Cl2" }]);
  assert.deepEqual(two.filter((l) => l.bold).map((l) => l.text).sort(), ["2", "C", "H"], "C, H and the first 2 bold on the second line");
  console.log("render.check: labels with styled characters ok");
}

// Captions: centred on the structure's ink box, baseline 15 pt below it; a second caption stacks one line down.
{
  const one = (w: number) => () => w;
  const withCaptions: Mol = { ...pyridine, captions: [{ id: 2, text: "pyridine", x: 0, y: 0, under: [0, 1, 2, 3, 4, 5] }, { id: 1, text: "1", x: 0, y: 0, bold: true, under: [0, 1, 2, 3, 4, 5] }] };
  const dc = render(withCaptions, S, ink);
  const [placedNumber, placedName] = placeCaptions(withCaptions, dc, one(30));
  const xs = dc.ink.flatMap((b) => [b[0], b[2]]), ys = dc.ink.flatMap((b) => [b[1], b[3]]);
  const centre = (Math.min(...xs) + Math.max(...xs)) / 2, bottom = Math.max(...ys);
  assert.equal(placedNumber.id, 1, "captions stack in id order");
  assert.ok(Math.abs(placedNumber.lines[0].x - centre) < 1e-9 && placedNumber.anchor === "middle", "centred on the ink box");
  assert.ok(Math.abs(placedNumber.lines[0].y - bottom - 15 * pt) < 1e-9, "baseline 15 pt below the ink box");
  assert.ok(Math.abs(placedName.lines[0].y - placedNumber.lines[0].y - 1.2 * 10 * pt) < 1e-9, "the next caption is one line down");
  // A free caption stays where it was put, in drawing units.
  const [free] = placeCaptions({ ...pyridine, captions: [{ id: 1, text: "a\nb", x: 2, y: -1, align: "left" }] }, dc, one(10));
  assert.deepEqual([free.lines[0].x, free.lines[0].y, free.lines.length, free.anchor], [2 * dc.scale, dc.scale, 2, "start"]);
  console.log("render.check: captions ok");
}

// Arrows: a reaction arrow is a shaft and a head; conditions wider than the arrow lengthen it about its middle.
{
  const a = { id: 1, kind: "reaction" as const, from: [0, 0] as [number, number], to: [2, 0] as [number, number] };
  assert.equal(arrowShapes(a, S, S.bond).length, 2, "shaft and head");
  assert.equal(arrowShapes({ ...a, kind: "equilibrium" }, S, S.bond).length, 4, "two shafts, two half heads");
  const [fitted] = fitArrows({ atoms: [], bonds: [], arrows: [a], captions: [{ id: 2, text: "x", x: 0, y: 0, on: { arrow: 1, side: "above" } }] }, S.bond, () => 200);
  assert.ok(fitted.from[0] < 0 && fitted.to[0] > 2 && Math.abs(fitted.from[0] + fitted.to[0] - 2) < 1e-9, "lengthened about its middle");
  console.log("render.check: arrows ok");
}

// ChemDraw's head sizes and arrow kinds (CD-14, CD-15). Arrows run along +x at k = S.bond px per bond length.
{
  const a = { id: 1, kind: "reaction" as const, from: [0, 0] as [number, number], to: [4, 0] as [number, number] }, k = S.bond, lw = S.line;
  const ys = (polys: [number, number][][]) => polys.flat().map((q) => q[1]), xs = (polys: [number, number][][]) => polys.flat().map((q) => q[0]);
  const head = (more: Partial<Arrow>) => { const p = arrowShapes({ ...a, ...more }, S, k); return p[p.length - 1]; };
  // The head: tip, barb its length back and its width off the shaft, notch between. Large is 22.5, 19.6875 and 5.625.
  const [tip, barb, notch] = head({ headSize: headOfLength(22.5) });
  assert.ok(Math.abs(tip[0] - 4 * k) < 1e-9 && Math.abs(barb[0] - (4 * k - 22.5 * lw)) < 1e-9 && Math.abs(Math.abs(barb[1]) - 5.625 * lw) < 1e-9 && Math.abs(notch[0] - (4 * k - 19.6875 * lw)) < 1e-9, "large head");
  assert.deepEqual([sizeOf({ kind: "reaction" }), sizeOf({ kind: "reaction", headSize: headOfLength(15) }), sizeOf({ kind: "reaction", headSize: { length: 9, centre: 8, width: 2 } })], ["small", "medium", undefined]);
  // A bold arrow's own heads are twice the size, as ChemDraw draws them. Arc arrows' heads are 8 line widths (their
  // Small), as ChemDraw's palette and every arc in Sam's files have them; elliptical ones too.
  assert.equal(headSize({ kind: "reaction", style: "bold" }).length, 20);
  assert.deepEqual([headSize({ kind: "curved" }), headSize({ kind: "fishhook", style: "bold" }).length, sizeOf({ kind: "double" }), ellipseArrow([0, 0], [0.6, 1.2], true).headSize], [headOfLength(8), 16, "small", headOfLength(8)]);
  // A head is kept to two thirds of a short arrow.
  const short = arrowShapes({ ...a, to: [0.3, 0] }, S, k), shortHead = short[short.length - 1];
  assert.ok(Math.abs(shortHead[1][0] - (0.3 * k) / 3) < 1e-9, "head two thirds of the arrow");
  // No-go: a cross 2 head widths each way on the middle; hash: two slashes there; dipole: a bar across at the notch.
  const nogo = arrowShapes({ ...a, kind: "nogo" }, S, k), hash = arrowShapes({ ...a, kind: "hash" }, S, k), dipole = arrowShapes({ ...a, kind: "dipole" }, S, k);
  assert.deepEqual([nogo.length, hash.length, dipole.length], [4, 4, 3]);
  const reach = 5 * lw + (lw / 2) * Math.SQRT1_2;
  assert.ok(Math.abs(Math.max(...xs(nogo.slice(2))) - (2 * k + reach)) < 1e-9 && Math.abs(Math.max(...ys(nogo.slice(2))) - reach) < 1e-9, "the cross");
  assert.ok(Math.abs(Math.min(...xs(dipole.slice(2))) - (8.75 * lw - lw / 2)) < 1e-9 && Math.abs(Math.max(...ys(dipole.slice(2))) - 2.5 * lw) < 1e-9, "the dipole bar");
  // An unbalanced equilibrium (ratio 3): the back arrow is its notch plus a third of the rest, about the middle.
  const eq = arrowShapes({ ...a, kind: "equilibrium", ratio: 3 }, S, k), back = eq[2].map((q) => q[0]), want = 8.75 * lw + (4 * k - 8.75 * lw) / 3;
  assert.ok(Math.abs(Math.max(...back) - Math.min(...back) - want) < 1e-6 && Math.abs(Math.max(...back) + Math.min(...back) - 4 * k) < 1e-6, "short back arrow");
  // A bent equilibrium (a point, then its middle dragged): two arcs beside its own, each with its half head; with a
  // ratio of 3 the back arc sweeps a third of the forward one.
  const bentEq = arrowShapes({ ...a, kind: "equilibrium", point: true, bend: 0.3 }, S, k), bentShort = arrowShapes({ ...a, kind: "equilibrium", point: true, bend: 0.3, ratio: 3 }, S, k);
  assert.ok(Math.min(...ys(bentEq)) < -0.3 * 4 * k + 0.2 * k && bentShort.length < bentEq.length, "curved equilibrium");
  // A block arrow: shaft 12 line widths wide, barbs 12 off the axis and 12 back from the tip.
  const o = blockOutline({ ...a, kind: "block" }, S, k);
  const X = (4 * k) / lw, round = (v: number) => Math.round(v * 1e6) / 1e6 + 0;
  assert.deepEqual(o.map(([x, y]) => [round(x / lw), round(y / lw)]), [[0, 6], [X - 12, 6], [X - 12, 12], [X, 0], [X - 12, -12], [X - 12, -6], [0, -6]].map(([x, y]) => [round(x), round(y)]));
  // An elliptical arrow: from the tail 270° round to the head, every point on one ellipse whose short axis is 0.4 of
  // its long one.
  const e = ellipseArrow([0, 0], [0.5, 1.2], true), pts = e.curve!.points.map((q) => q.at);
  assert.ok(pts.length === 4 && Math.hypot(pts[0][0], pts[0][1]) < 1e-9 && Math.hypot(pts[3][0] - 0.5, pts[3][1] - 1.2) < 1e-9 && e.end === "full");
  const c = [(pts[0][0] + pts[2][0]) / 2, (pts[0][1] + pts[2][1]) / 2], long = Math.hypot(pts[0][0] - c[0], pts[0][1] - c[1]), shortAxis = Math.hypot(pts[3][0] - c[0], pts[3][1] - c[1]);
  assert.ok(Math.abs(shortAxis / long - 0.4) < 1e-9, "axes 0.4");
  // A closed pen curve (it ends where it starts) is still drawn.
  assert.equal(arrowShapes({ id: 2, kind: "curve", from: [0, 0], to: [0, 0], curve: { points: [{ at: [0, 0] }, { at: [1, 0] }, { at: [0, 1] }], closed: true } }, S, k).length, 3);
  // A pen curve whose ends are close together (a loop) keeps its whole head: only straight arrows are kept to two thirds.
  const loop = arrowShapes({ id: 3, kind: "curve", from: [0, 0], to: [0.3, 0], end: "full", curve: { points: [{ at: [0, 0], c2: [-2, 2] }, { at: [0.3, 0], c1: [2.3, 2] }] } }, S, k);
  const loopHead = loop[loop.length - 1];
  assert.ok(Math.abs(Math.hypot(loopHead[2][0] - loopHead[0][0], loopHead[2][1] - loopHead[0][1]) - 8.75 * lw) < 1e-6, "a curve's whole head");
  // Every polygon winds the same way, so a head over its shaft, or over an arrow joined at its tip, leaves no hole.
  const area = (p: [number, number][]) => p.reduce((s, q, i) => s + q[0] * p[(i + 1) % p.length][1] - p[(i + 1) % p.length][0] * q[1], 0);
  for (const more of [{}, { headSize: headOfLength(22.5) }, { style: "bold" }, { kind: "equilibrium" }, { kind: "resonance" }, { end: "right" }, { start: "left" }, { kind: "nogo" }, { kind: "block" }] as Partial<Arrow>[])
    assert.ok(arrowShapes({ ...a, ...more }, S, k).every((p) => area(p) < 0), `winding: ${JSON.stringify(more)}`);
  console.log("render.check: arrow sizes and kinds ok");
}

// Shapes (CD-18): a turned box's outline is the level one turned about its middle (anticlockwise on the page), a bold
// one's lines are the bold width, and a bracket's mark turns with it.
{
  const box = { id: 1, kind: "box" as const, from: [0, 0] as [number, number], to: [2, 1] as [number, number] }, k = S.bond;
  const level = shapePaths(box, k)[0], turned = shapePaths({ ...box, angle: 90 }, k)[0];
  // Turned a quarter: (x, y) about the middle (1, 0.5) goes to (1 - (y - 0.5), 0.5 + (x - 1)); px have y down.
  level.forEach(([x, y], i) => { const X = x / k, Y = -y / k, want = [1 - (Y - 0.5), 0.5 + (X - 1)]; assert.ok(Math.abs(turned[i][0] / k - want[0]) < 1e-9 && Math.abs(-turned[i][1] / k - want[1]) < 1e-9, "turned box"); });
  const width = (polys: [number, number][][]) => Math.hypot(polys[0][1][0] - polys[0][0][0], polys[0][1][1] - polys[0][0][1]);
  assert.ok(Math.abs(width(shapeInk({ ...box, boldLine: true }, S, k)) - S.bold) < 1e-9 && Math.abs(width(shapeInk(box, S, k)) - S.line) < 1e-9, "bold lines");
  const m = markAt({ id: 2, kind: "brackets", from: [0, 0], to: [2, 2], angle: 180 }, k);
  assert.ok(Math.abs(m.x / k - (2 - 2.08)) < 1e-9 && Math.abs(-m.y / k - (2 - 1.9)) < 1e-9, "mark turns with the brackets");
  assert.deepEqual(turnedWith({ kind: "tlc", from: [0, 0], to: [2, 2], angle: 90 }, [0, 0]), [0, 0], "a TLC plate stays level");
  console.log("render.check: turned and bold shapes ok");
}

// A turned caption (CD-19) turns about its anchor on the first baseline: its frame is the level box, and its box is
// the box round the frame turned (a quarter turn anticlockwise puts its width up the page).
{
  const mol: Mol = { atoms: [], bonds: [], captions: [{ id: 1, text: "Turned", x: 0, y: 0, align: "left", angle: 90 }] };
  const [c] = placeCaptions(mol, { ink: [], scale: S.bond }, () => 50);
  assert.ok(Math.hypot(...c.pivot!) === 0);
  const f = c.frame!, b = c.box;
  assert.ok(Math.abs(b[0] - f[1]) < 1e-9 && Math.abs(b[1] - -f[2]) < 1e-9 && Math.abs(b[2] - f[3]) < 1e-9 && Math.abs(b[3] - -f[0]) < 1e-9, "box round the turned frame");
  console.log("render.check: turned captions ok");
}

// Document label options: terminal carbons labelled (CH3), every carbon labelled, and implicit H hidden.
{
  const propane: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [0.866, 0.5, 0] }, { label: "C", location: [1.732, 0, 0] }, { label: "O", location: [2.598, 0.5, 0] }],
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }, { type: 1, atoms: [2, 3] }] };
  const text = (s: typeof S & { terminal?: boolean; carbons?: boolean; hideH?: boolean }) => render(propane, s, ink).labels.map((l) => l.text).join("");
  assert.equal(text(S), "OH");
  assert.equal(text({ ...S, terminal: true }), "CH3OH");
  assert.equal(text({ ...S, terminal: true, carbons: true }), "CH3CH2CH2OH");
  assert.equal(text({ ...S, terminal: true, hideH: true }), "CO");
  console.log("render.check: label options ok");
}

// Drawing structure by structure gives the same drawing as drawing them all at once, and a structure whose atoms and
// bonds are the same objects is not drawn again. Two structures in perspective crossing each other are drawn as one.
// While a drag moves a structure, its drawing moves as it is; when the drag stops, it is drawn again where it is.
{
  const shift = (m: Mol, dx: number): Mol => ({ atoms: m.atoms.map((a) => ({ ...a, location: [a.location[0] + dx, a.location[1], a.location[2]] as [number, number, number] })), bonds: m.bonds });
  const join = (...ms: Mol[]): Mol => ms.reduce((all, m) => ({ atoms: [...all.atoms, ...m.atoms], bonds: [...all.bonds, ...m.bonds.map((b) => ({ ...b, atoms: [b.atoms[0] + all.atoms.length, b.atoms[1] + all.atoms.length] as [number, number] }))] }), { atoms: [], bonds: [] } as Mol);
  const lone: Mol = { atoms: [{ label: "O", text: "H2O2", location: [9, 3, 0] }], bonds: [] };
  const crossing: Mol = { atoms: [{ label: "C", location: [0, -5, 0] }, { label: "C", location: [2, -5, 1] }, { label: "C", location: [1, -4, 0] }, { label: "C", location: [1, -6, 1] }], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [2, 3] }] };
  const nitroMol: Mol = {
    atoms: [{ label: "C", location: [6, 0, 0] }, { label: "N", location: [7, 0, 0], charge: 1 }, { label: "O", location: [7.5, 0.87, 0] }, { label: "O", location: [7.5, -0.87, 0], charge: -1, pairs: 3 }],
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 2, atoms: [1, 2] }, { type: 1, atoms: [1, 3] }],
  };
  const m = join(pyridine, shift(pyridine, 4), lone, crossing, nitroMol);
  const whole = render(m, S, ink, S.bond), cache: PartCache = { parts: new WeakMap(), last: new Map() }, parts = renderParts(m, S, ink, S.bond, cache);
  const sorted = <T,>(xs: T[]) => xs.map((x) => JSON.stringify(x)).sort();
  const polys = (d: Drawing) => d.polygons.map((p, i) => [p, d.colours[i], d.alphas[i]]);
  assert.deepEqual(parts.ink, whole.ink, "each atom's ink box");
  assert.deepEqual(parts.label, whole.label, "each atom's label box");
  assert.deepEqual(parts.box, whole.box, "the drawing's box");
  assert.deepEqual(sorted(parts.parts.flatMap((p) => polys(p.drawing))), sorted(polys(whole)), "the same polygons");
  assert.deepEqual(sorted(parts.parts.flatMap((p) => p.drawing.labels)), sorted(whole.labels), "the same labels");
  assert.deepEqual(parts.parts.map((p) => p.ids.length), [6, 6, 1, 4, 4], "two pyridines, H2O2, the two bonds in perspective as one, nitro");
  // Move the second pyridine: only it is drawn again.
  const move = (dx: number, dy: number): Mol => ({ ...m, atoms: m.atoms.map((a, i) => (i >= 6 && i < 12 ? { ...a, location: [a.location[0] + dx, a.location[1] + dy, a.location[2]] as [number, number, number] } : a)) });
  // (Left, clear of the nitro group: a bond end that comes within the margin and widths of another bond counts as
  // crossing it, as in ChemDraw, and joins their drawings.)
  const moved = move(-1, 0.5), again = renderParts(moved, S, ink, S.bond, cache);
  assert.equal(again.parts[0].drawing, parts.parts[0].drawing, "the first pyridine is not drawn again");
  assert.notEqual(again.parts[1].drawing, parts.parts[1].drawing, "the moved pyridine is drawn again");
  const near = (a: Box[], b: Box[]) => a.every((x, i) => x.every((v, j) => Math.abs(v - b[i][j]) < 1e-9));
  assert.ok(near(again.ink, render(moved, S, ink, S.bond).ink), "ink boxes where the atoms are");
  // The same move during a drag: the pyridine's drawing moves as it is, and is drawn again once it is still.
  const drag: PartCache = { parts: new WeakMap(), last: new Map() };
  const before = renderParts(m, S, ink, S.bond, drag, false), during = renderParts(moved, S, ink, S.bond, drag, false);
  assert.equal(during.parts[1].drawing, before.parts[1].drawing, "moved, not drawn again");
  assert.ok(Math.abs(during.parts[1].at[0] + S.bond) < 1e-9 && Math.abs(during.parts[1].at[1] + 0.5 * S.bond) < 1e-9, "moved by the drag (y down)");
  assert.ok(near(during.ink, again.ink) && near([during.box], [again.box]), "ink boxes and box where the atoms are");
  const dropped = renderParts(moved, S, ink, S.bond, drag, true);
  assert.notEqual(dropped.parts[1].drawing, before.parts[1].drawing, "drawn again when still");
  assert.deepEqual(dropped.parts[1].at, [0, 0]);
  // When still, the moved drawing's own points are where a new drawing puts them.
  const fresh = again.parts[1].drawing, got = dropped.parts[1].drawing, close = (a: number, b: number) => Math.abs(a - b) < 1e-9;
  assert.ok(got.polygons.length === fresh.polygons.length && got.polygons.every((p, i) => p.every((q, j) => close(q[0], fresh.polygons[i][j][0]) && close(q[1], fresh.polygons[i][j][1]))), "polygons where a new drawing puts them");
  assert.ok(got.labels.every((l, i) => l.text === fresh.labels[i].text && close(l.x, fresh.labels[i].x) && close(l.y, fresh.labels[i].y)), "labels where a new drawing puts them");
  assert.ok(near(got.ink, fresh.ink) && near([got.box], [fresh.box]) && near(dropped.ink, again.ink), "ink boxes where a new drawing puts them");
  assert.equal(dropped.parts[0].drawing, before.parts[0].drawing, "the rest is not drawn again");
  // A scale during a drag (positions and atoms' scales together, IDEA-SCALE-3): the drawing is kept, scaled by k and
  // moved; once still, it is drawn again. (About its own middle, so it stays clear of the nitro group.)
  const grow = (k: number): Mol => ({ ...m, atoms: m.atoms.map((a, i) => (i >= 6 && i < 12 ? { ...a, scale: k, location: [4 + (a.location[0] - 4) * k, (a.location[1] ?? 0) * k, (a.location[2] ?? 0) * k] as [number, number, number] } : a)) });
  const scaling: PartCache = { parts: new WeakMap(), last: new Map() }, start = renderParts(m, S, ink, S.bond, scaling, false), big = renderParts(grow(2), S, ink, S.bond, scaling, false);
  assert.equal(big.parts[1].drawing, start.parts[1].drawing, "scaled, not drawn again");
  assert.equal(big.parts[1].k, 2);
  assert.ok(near(big.ink.slice(6, 12), render(grow(2), S, ink, S.bond).ink.slice(6, 12)), "ink boxes where a new drawing puts them");
  const flat = renderParts({ ...grow(2), atoms: grow(2).atoms.map((a, i) => (i >= 6 && i < 12 ? { ...a, scale: undefined } : a)) }, S, ink, S.bond, scaling, false);
  assert.equal(flat.parts[1].k, 1, "positions alone are not a scale of the drawing");
  const still = renderParts(grow(2), S, ink, S.bond, scaling, true);
  assert.notEqual(still.parts[1].drawing, start.parts[1].drawing, "drawn again when still");
  assert.equal(still.parts[1].k, 1);
  // A turn during a drag (the rotation handle): the drawing is kept and turned, each label's atom is where the turn puts
  // it, and the ink boxes hold where a new drawing puts the ink. Once still, it is drawn again. A change of shape is no
  // turn.
  const turn = (deg: number, c: P = [5, 1]): Mol => {
    const r = (deg * Math.PI) / 180, [cs, sn] = [Math.cos(r), Math.sin(r)];
    return { ...m, atoms: m.atoms.map((a, i) => (i >= 6 && i < 12 ? { ...a, location: [c[0] + (a.location[0] - c[0]) * cs - (a.location[1] - c[1]) * sn, c[1] + (a.location[0] - c[0]) * sn + (a.location[1] - c[1]) * cs, a.location[2]] as [number, number, number] } : a)) };
  };
  const turning: PartCache = { parts: new WeakMap(), last: new Map() }, flatOut = renderParts(m, S, ink, S.bond, turning, false), turned = renderParts(turn(30), S, ink, S.bond, turning, false);
  assert.equal(turned.parts[1].drawing, flatOut.parts[1].drawing, "turned, not drawn again");
  assert.ok(Math.abs(turned.parts[1].turn + 30) < 1e-9 && turned.parts[1].k === 1, "30° anticlockwise on the page is rotate(-30) in px");
  const p = turned.parts[1], a = (p.turn * Math.PI) / 180, at = (q: P): P => [q[0] * Math.cos(a) - q[1] * Math.sin(a) + p.at[0], q[0] * Math.sin(a) + q[1] * Math.cos(a) + p.at[1]];
  const nAtom = turn(30).atoms.findIndex((x, i) => i >= 6 && x.label === "N"), nAt = at(p.drawing.labelAt[p.drawing.labels.findIndex((l) => l.text === "N")]);
  assert.ok(Math.abs(nAt[0] - turn(30).atoms[nAtom].location[0] * S.bond) < 1e-6 && Math.abs(nAt[1] + turn(30).atoms[nAtom].location[1] * S.bond) < 1e-6, "the N label keeps to its atom");
  const real = render(turn(30), S, ink, S.bond).ink.slice(6, 12), held = turned.ink.slice(6, 12);
  assert.ok(held.every((b, i) => b[0] <= real[i][0] + 1e-6 && b[1] <= real[i][1] + 1e-6 && b[2] >= real[i][2] - 1e-6 && b[3] >= real[i][3] - 1e-6), "each ink box holds the atom's ink");
  assert.equal(turned.parts[0].drawing, flatOut.parts[0].drawing, "the first pyridine is not turned");
  const bent = turn(30), wrong = { ...bent, atoms: bent.atoms.map((x, i) => (i === 6 ? { ...x, location: [x.location[0] + 0.2, x.location[1], 0] as [number, number, number] } : x)) };
  assert.notEqual(renderParts(wrong, S, ink, S.bond, turning, false).parts[1].drawing, flatOut.parts[1].drawing, "a change of shape is drawn again");
  const settled = renderParts(turn(30), S, ink, S.bond, turning, true);
  assert.ok(settled.parts[1].drawing !== flatOut.parts[1].drawing && settled.parts[1].turn === 0, "drawn again when still");
  console.log("render.check: structure by structure ok");
}

// Label cuts: a bond into a label of one glyph stops where every point of the glyph's outline, and of the outline
// turned over about the middle of the glyph, is a margin clear of it (the largest a + √(m² − d²) over the points, a
// along the bond and d across it), whichever way the bond comes in, however the points are grouped to pass over the
// far ones.
{
  // An O-like outline: two rings of points, 900 in all, off-centre so no two ways in are alike.
  const ring = (r: number, n: number, cx: number): P[] => Array.from({ length: n }, (_, k) => [cx + r * Math.cos((2 * Math.PI * k) / n), -4.75 + 1.2 * r * Math.sin((2 * Math.PI * k) / n)]);
  const oInk = (): Ink => ({ width: 9.6, ascent: 9.5, outline: [...ring(4.6, 500, 5.3), ...ring(2.9, 400, 5.3)] });
  for (let deg = 0; deg < 360; deg += 7.5) {
    const t = (deg * Math.PI) / 180, from: [number, number, number] = [Math.cos(t), Math.sin(t), 0];
    const d = render({ atoms: [{ label: "C", location: from }, { label: "O", location: [0, 0, 0], implicitHCount: 0 }], bonds: [{ type: 1, atoms: [0, 1] }] }, S, oInk, S.bond);
    const X: P = [0, 0], u: P = [Math.cos(t), -Math.sin(t)], n: P = [-u[1], u[0]], m = S.margin + S.line / 2, first = oInk();
    const x0 = -first.width / 2, y0 = first.ascent / 2;
    let cut = 0;
    for (const [px, py] of [...first.outline, ...first.outline.map(([px, py]): P => [first.width - px, py])]) {
      const q: P = [x0 + px, y0 + py], a = (q[0] - X[0]) * u[0] + (q[1] - X[1]) * u[1], c = (q[0] - X[0]) * n[0] + (q[1] - X[1]) * n[1];
      if (Math.abs(c) < m) cut = Math.max(cut, a + Math.sqrt(m * m - c * c));
    }
    const reach = Math.min(...d.polygons[0].map((q) => q[0] * u[0] + q[1] * u[1]));
    assert.ok(Math.abs(reach - cut) < 1e-9, `bond from ${deg}° stops at the cut`);
  }
  console.log("render.check: label cuts ok");
}

// Crossing bonds (ChemDraw's Bond Crossing): the bond later in the list is in front; the one behind has a gap where
// they cross, as wide as the front bond and clear of it by its margin. Two separate structures that cross draw as one.
{
  const cross: Mol = {
    atoms: [{ label: "C", location: [0, -1, 0] }, { label: "C", location: [0, 1, 0] }, { label: "C", location: [-1, 0, 0] }, { label: "C", location: [1, 0, 0] }],
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [2, 3] }],
  };
  const inside = (poly: P[], q: P) => { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) if ((poly[i][1] > q[1]) !== (poly[j][1] > q[1]) && q[0] < ((poly[j][0] - poly[i][0]) * (q[1] - poly[i][1])) / (poly[j][1] - poly[i][1]) + poly[i][0]) c = !c; return c; };
  const covered = (dr: Drawing, q: P) => dr.polygons.some((poly) => inside(poly, q));
  const dc = render(cross, S, ink, L);
  assert.ok(covered(dc, [0.5, 0]) && covered(dc, [-0.5, 0]), "the front bond (drawn later) runs through the crossing");
  // The gap, as ChemDraw cuts it: half the front bond's width and the Margin Width each side (0.3 + 1.6 pt = 2.53 px).
  assert.ok(!covered(dc, [0, 0.5]) && !covered(dc, [0, -0.5]) && !covered(dc, [0, -2.45]) && covered(dc, [0, -2.65]), "the bond behind has a gap");
  assert.ok(covered(dc, [0, -8]) && covered(dc, [0, 8]), "the bond behind is drawn on both sides of its gap");
  const swapped = render({ ...cross, bonds: [cross.bonds[1], cross.bonds[0]] }, S, ink, L);
  assert.ok(covered(swapped, [0, 0.5]) && !covered(swapped, [2.45, 0]), "Bring to Front swaps them");
  const parts = renderParts(cross, S, ink, L, { parts: new WeakMap(), last: new Map() } as PartCache);
  assert.equal(parts.parts.length, 1, "crossing structures draw together");
  console.log("render.check: crossing bonds ok");
}

// Line spacing: Automatic spaces every line by the caption's largest text, Variable each line by its own, and Fixed
// by the points given.
{
  const two = { text: "a\nb" }, big = { text: "a\nb", runs: [{ text: "a\n" }, { text: "b", size: 20 }] };
  assert.deepEqual(lineOffsets(two, 10, 1), [0, 12]);
  assert.deepEqual(lineOffsets({ ...big }, 10, 1), [0, 24]);
  assert.deepEqual(lineOffsets({ ...two, lineHeight: 15 }, 10, 2), [0, 30]);
  const v = lineOffsets({ ...big, lineHeight: "variable" }, 10, 1);
  assert.ok(v[1] > 12 && v[1] < 24, `variable: between the two sizes' spacing (${v[1]})`);
  // Variable, as ChemDraw's: the line above's lowest descender and this line's tallest character, with no gap. An empty
  // line has no ink, so it takes the ascent and descent of its text size.
  assert.deepEqual(lineOffsets({ ...two, lineHeight: "variable" }, 10, 1, (j) => (j === 0 ? [7, 2] : [8, 0])), [0, 10]);
  const gap = lineOffsets({ text: "a\n\nb", lineHeight: "variable" }, 10, 1, (j) => (j === 1 ? undefined : [7, 2]));
  assert.ok(Math.abs(gap[1] - (2 + 9.05)) < 1e-9 && Math.abs(gap[2] - gap[1] - (2.12 + 7)) < 1e-9, `empty line: ${gap}`);
  // placeCaptions measures each line's runs, a subscript lowered as it is drawn.
  const placed = placeCaptions({ atoms: [], bonds: [], captions: [{ id: 1, text: "H2\nO", x: 0, y: 0, lineHeight: "variable", runs: [{ text: "H" }, { text: "2", script: "sub" }, { text: "\nO" }] }] },
    { ink: [], scale: 19.2 }, (t) => t.length, [], 1, 10, new Map(), undefined, (_, __, r) => (r.script ? [5, 1] : [7, 0]))[0];
  assert.ok(Math.abs(placed.lines[1].y - placed.lines[0].y - (1 + 0.212 * 10 + 7)) < 1e-9, `subscript ink: ${placed.lines.map((l) => l.y)}`);
  console.log("render.check: line spacing ok");
}

// A caption with a width wraps to it, and a justified one fills it on every line but the last.
{
  const pc = (align: Caption["align"]) => placeCaptions({ atoms: [], bonds: [], captions: [{ id: 1, text: "aa bb cc dd", x: 0, y: 0, width: 6 / 19.2, align }] }, { ink: [], scale: 19.2 },
    (t) => t.length, [], 1, 10, new Map(), (t) => t.length)[0];
  const left = pc("left");
  assert.deepEqual(left.lines.map((l) => l.text), ["aa bb", "cc dd"]);
  assert.ok(left.lines.every((l) => !l.spacing));
  const full = pc("justify");
  assert.equal(full.anchor, "start");
  assert.ok(Math.abs(full.lines[0].spacing! - 1) < 1e-9, "the first line's one space takes the one spare px");
  assert.equal(full.lines[1].spacing, undefined, "the last line is not spread");
  console.log("render.check: caption width ok");
}


// Decision 0007: every length an object draws is the document's length times the object's scale. One drawing with
// every kind of object, at scale 1 and again at scale 2 with its positions doubled: every point and size doubles.
// A new kind of object that forgets its scale fails here.
{
  const close = (a: number, b: number) => Math.abs(a - b) < 1e-6 * Math.max(1, Math.abs(b));
  const twice = (a: P[][], b: P[][], what: string) => {
    assert.equal(b.length, a.length, `${what}: as many shapes`);
    a.forEach((poly, i) => { assert.equal(b[i].length, poly.length, what); poly.forEach((q, j) => assert.ok(close(b[i][j][0], 2 * q[0]) && close(b[i][j][1], 2 * q[1]), `${what}: point doubles`)); });
  };
  const two = (q: [number, number]): [number, number] => [2 * q[0], 2 * q[1]];
  // Atoms: labels, a written label, an own label size, charges (skeletal, circled, partial), radicals, lone pairs,
  // H marks, an attachment point, a bead, and a ring drawn with its circle. Bonds: every order and display.
  const A = (label: string, x: number, y: number, more: Partial<Atom> = {}): Atom => ({ label, location: [x, y, 0], ...more });
  const atoms: Atom[] = [
    A("N", 0, 0, { charge: 1, pairs: 1 }), A("C", 0.87, 0.5, { charge: -1 }), A("O", 1.73, 0, { radical: 1, pairs: 2, partial: "+" }), A("O", 2.6, 0.5, { text: "OMe" }),
    A("C", 0.87, 1.5, { charge: 1, circled: true }), A("C", 0, -1, { hmark: "dot" }), A("C", -0.87, -1.5, { attach: true }), A("C", 0.87, -1.5, { bead: true }),
    A("Cl", 1.73, -1, { size: 14 }), A("C", -0.87, 0.5, { hmark: "dash", radical: 3 }), A("C", -1.73, 0, { size: 7, charge: 1 }),
    ...[...Array(6)].map((_, k) => A("C", 6 + Math.cos((Math.PI / 3) * k), Math.sin((Math.PI / 3) * k), { circle: true })),
  ];
  const b = (i: number, j: number, more: Partial<Bond> = {}): Bond => ({ type: 1, atoms: [i, j], ...more });
  const bonds: Bond[] = [
    b(0, 1, { stereo: 1 }), b(1, 2, { type: 2 }), b(2, 3), b(1, 4, { type: 3 }), b(0, 5, { stereo: 6 }), b(5, 6, { display: "wavy" }), b(5, 7, { display: "bold" }), b(5, 8, { display: "dashed" }),
    b(0, 9, { display: "hashed" }), b(9, 10, { display: "dative" }), b(4, 2, { display: "hollow" }), b(8, 7, { type: 2, display: "bold" }), b(6, 9, { type: 2, display: "either" }),
    b(10, 6, { type: 2, display: "dashed" }), b(3, 4, { type: 2, display: "aromatic" }),
    ...[0, 1, 2, 3, 4, 5].map((k) => b(11 + k, 11 + ((k + 1) % 6), { type: k % 2 ? 1 : 2 })),
  ];
  const style = { ...S, labelPt: 10 };
  const small: Mol = { atoms, bonds }, big: Mol = { atoms: atoms.map((a) => ({ ...a, location: [2 * a.location[0], 2 * a.location[1], 0] as [number, number, number], scale: 2 })), bonds };
  const d1 = render(small, style, ink, S.bond), d2 = render(big, style, ink, S.bond);
  twice(d1.polygons, d2.polygons, "structure");
  assert.equal(d2.labels.length, d1.labels.length);
  d1.labels.forEach((l, i) => assert.ok(close(d2.labels[i].x, 2 * l.x) && close(d2.labels[i].y, 2 * l.y) && close(d2.labels[i].size, 2 * l.size), `label ${l.text} doubles`));
  twice([d1.electrons.map((e) => e.at)], [d2.electrons.map((e) => e.at)], "lone pairs and radicals");
  d1.beads.forEach((x, i) => assert.ok(close(d2.beads[i].r, 2 * x.r), "bead"));
  // A structure at its scale beside one at 1: each keeps its own lengths (a bond takes its atoms' scale).
  const far: Mol = { atoms: big.atoms.map((a) => ({ ...a, location: [a.location[0] + 40, a.location[1], 0] as [number, number, number] })), bonds };
  const both = render({ atoms: [...small.atoms, ...far.atoms], bonds: [...bonds, ...bonds.map((x) => ({ ...x, atoms: [x.atoms[0] + atoms.length, x.atoms[1] + atoms.length] as [number, number] }))] }, style, ink, S.bond);
  const keys = (ps: P[][]) => ps.map((poly) => poly.map((q) => q.map((v) => v.toFixed(6)).join(" ")).join(";")).sort();
  assert.deepEqual(keys(both.polygons), keys([...d1.polygons, ...render(far, style, ink, S.bond).polygons]), "two structures, two scales");

  // Arrows and lines of every kind and style, with heads of every shape.
  const curve = { points: [{ at: [0, 0] as [number, number] }, { at: [1, 1] as [number, number], c1: [0.5, 1] as [number, number], c2: [1.5, 1] as [number, number] }, { at: [2, 0] as [number, number] }] };
  const arrows: Arrow[] = ALL_ARROW_KINDS.filter((k) => k !== "orbital").flatMap((kind, n) => [undefined, "dashed", "wavy", "bold", "doubled"].flatMap((style) => [undefined, "hollow", "angled"].map((head): Arrow => ({
    id: n, kind, from: [0, 0], to: kind === "curve" ? [2, 0] : [3, 1], bend: kind === "curved" || kind === "fishhook" || kind === "double" || kind === "arc" ? 0.3 : undefined, ...(kind === "curve" ? { curve } : {}),
    ...(style ? { style: style as Arrow["style"] } : {}), ...(head ? { head: head as Arrow["head"], end: "full" as const } : {}),
  }))));
  for (const a of arrows) {
    const bigger: Arrow = { ...a, from: two(a.from), to: two(a.to), scale: 2, ...(a.curve ? { curve: { points: a.curve.points.map((q) => ({ at: two(q.at), ...(q.c1 ? { c1: two(q.c1) } : {}), ...(q.c2 ? { c2: two(q.c2) } : {}) })) } } : {}) };
    twice(arrowShapes(a, S, S.bond), arrowShapes(bigger, S, S.bond), `${a.kind} ${a.style ?? ""} ${a.head ?? ""} arrow`);
  }
  // Shapes of every kind, plain and dashed, and a bracket's mark; TLC spots; a table's columns, rows and text.
  for (const kind of SHAPE_KINDS) for (const dashed of [false, true]) for (const angle of [undefined, 30]) {
    const sh: Shape = { id: 1, kind, from: [0, 2], to: [3, 0], dashed, mark: "‡", ...(angle ? { angle } : {}) };
    const bigger: Shape = { ...sh, from: two(sh.from), to: two(sh.to), scale: 2 };
    twice(shapeInk(sh, S, S.bond), shapeInk(bigger, S, S.bond), `${kind} shape${angle ? " turned" : ""}`);
    const m1 = markAt(sh, S.bond), m2 = markAt(bigger, S.bond);
    assert.ok(close(m2.x, 2 * m1.x) && close(m2.y, 2 * m1.y), `${kind} mark`);
  }
  const plate: Shape = { id: 1, kind: "tlc", from: [0, 3], to: [2, 0], tlc: { lanes: 2, spots: [{ lane: 0, rf: 0.3 }, { lane: 1, rf: 0.6, w: 0.2, h: 0.1, tail: 0.3 }] } };
  const plate2: Shape = { ...plate, from: two(plate.from), to: two(plate.to), scale: 2 };
  for (const x of plate.tlc!.spots) twice([spotPath(tlcLayout(plate), x)], [spotPath(tlcLayout(plate2), x)], "TLC spot");
  const table: Shape = { id: 1, kind: "table", from: [0, 2], to: [4, 0], table: { cells: [["a", "bb"], ["ccc", ""]], widths: [1.5, 2.5], heights: [0.9, 1.1] } };
  const table2: Shape = { ...table, from: two(table.from), to: two(table.to), scale: 2, table: { ...table.table!, widths: [3, 5], heights: [1.8, 2.2] } };
  const t1 = tableLayout(table, (x) => x.length * 0.3), t2 = tableLayout(table2, (x) => x.length * 0.3);
  assert.ok([...t1.widths, ...t1.heights, ...t1.natural, t1.x1, t1.y0].every((v, i) => close([...t2.widths, ...t2.heights, ...t2.natural, t2.x1, t2.y0][i], 2 * v)), "table columns, rows and text");
  // Captions: under a structure (the gap below it), and conditions on an arrow (the gap beside it).
  const caps = (m: Mol, f: number): Mol => ({ ...m, arrows: [{ id: 50, kind: "reaction", from: [4 * f, -3 * f], to: [7 * f, -3 * f], ...(f !== 1 ? { scale: f } : {}) }],
    captions: [{ id: 51, text: "1", x: 0, y: 0, size: 10 * f, under: [0, 1, 2] }, { id: 52, text: "heat", x: 0, y: 0, size: 10 * f, on: { arrow: 50, side: "above" } }] });
  const width = (t: string, c: { size?: number }) => t.length * (c.size ?? 10) * pt * 0.5;
  const c1 = placeCaptions(caps(small, 1), d1, width), c2 = placeCaptions(caps(big, 2), d2, width);
  twice(c1.map((c) => [[c.box[0], c.box[1]], [c.box[2], c.box[3]]]), c2.map((c) => [[c.box[0], c.box[1]], [c.box[2], c.box[3]]]), "captions");
  twice(fitArrows({ ...caps(small, 1), captions: [{ id: 52, text: "a long reagent", x: 0, y: 0, size: 10, on: { arrow: 50, side: "above" } }] }, S.bond, (c) => width(c.text, c)).map((a) => [a.from, a.to]),
    fitArrows({ ...caps(big, 2), captions: [{ id: 52, text: "a long reagent", x: 0, y: 0, size: 20, on: { arrow: 50, side: "above" } }] }, S.bond, (c) => width(c.text, c)).map((a) => [a.from, a.to]), "arrows grown for their conditions");
  // A catalytic cycle: its arcs and side arrows, and where its text goes.
  const cycleOf = (m: Mol, f: number): Mol => ({ ...m, cycles: [{ id: 60, centre: [6 * f, -6 * f], radius: 3 * f, clockwise: true, nodes: [[0], [1], [2]], ...(f !== 1 ? { scale: f } : {}) } as Cycle],
    atoms: m.atoms.map((a, i) => (i < 3 ? { ...a, location: [(6 + 3 * Math.cos(2 * i)) * f, (-6 + 3 * Math.sin(2 * i)) * f, 0] as [number, number, number] } : a)),
    captions: [{ id: 61, text: "X", x: 0, y: 0, cycle: { cycle: 60, step: 0, side: "in" } }] });
  const inkOf = (m: Mol, f: number) => (ids: number[]): Box => { const [x, y] = [m.atoms[ids[0]].location[0] * S.bond, -m.atoms[ids[0]].location[1] * S.bond], r = 8 * f; return [x - r, y - r, x + r, y + r]; };
  const y1 = cycleOf(small, 1), y2 = cycleOf(big, 2), l1 = layoutCycles(y1, S.bond, pt, inkOf(y1, 1)), l2 = layoutCycles(y2, S.bond, pt, inkOf(y2, 2));
  l1.arrows.forEach((a, i) => { assert.equal(l2.arrows[i].scale, 2, "a cycle's arrows take its scale"); twice([[a.from, a.to]], [[l2.arrows[i].from, l2.arrows[i].to]], "cycle arrows"); });
  twice([[...l1.anchors.values()].map((x) => [x.x, x.y] as P)], [[...l2.anchors.values()].map((x) => [x.x, x.y] as P)], "cycle text");
  console.log("render.check: every object at scale 2 ok");
}

// REL-15: a turned caption turns about its anchor, and its box is the box round the turned text; a bond with its own
// double-bond spacing (ChemDraw's BondSpacing) draws its second line that far from the first.
{
  const one = (w: number) => () => w;
  const d0 = render({ atoms: [], bonds: [] }, S, ink);
  const [upright] = placeCaptions({ atoms: [], bonds: [], captions: [{ id: 1, text: "ab", x: 1, y: 0, align: "left" }] }, d0, one(20));
  const [turned] = placeCaptions({ atoms: [], bonds: [], captions: [{ id: 1, text: "ab", x: 1, y: 0, align: "left", angle: 90 }] }, d0, one(20));
  const ax = d0.scale;
  assert.equal(upright.angle, undefined);
  assert.deepEqual([turned.angle, turned.pivot?.[0], Math.abs(turned.pivot![1]), turned.frame], [90, ax, 0, upright.box]);
  // A quarter turn anticlockwise: the text runs up the page from its anchor, so its box is tall and narrow.
  const [x0, y0, x1, y1] = turned.box;
  assert.ok(Math.abs(y1 - 0) < 1e-9 && Math.abs(y0 + 20) < 1e-9 && x1 - x0 < y1 - y0, "the box round the turned text");
  const height = (spacing?: number) => {
    const m: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [1, 0, 0] }], bonds: [{ type: 2, atoms: [0, 1], position: "centre", ...(spacing !== undefined ? { spacing } : {}) }] };
    const ys = render(m, S, ink).polygons.flat().map((p) => p[1]);
    return Math.max(...ys) - Math.min(...ys);
  };
  assert.ok(Math.abs(height(12) - height() - (0.12 - 0.18) * S.bond) < 1e-6, "the lines 12% of the bond length apart, not 18%");
  console.log("render.check: turned captions and a bond's own spacing ok");
}

// REL-15: a rounded box with its own corner radius (from ChemDraw's CornerRadius) draws it; others keep 0.3 bond lengths.
{
  const corner = (radius?: number) => shapePaths({ id: 1, kind: "rounded", from: [0, 1], to: [4, 0], ...(radius !== undefined ? { radius } : {}) }, 10)[0][0][0];
  assert.deepEqual([corner(), corner(0.25)], [40 - 3, 40 - 2.5]);
  console.log("render.check: a rounded box's own corner ok");
}
