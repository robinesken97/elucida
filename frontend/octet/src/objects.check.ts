// Run: node src/objects.check.ts. Fails loudly if an Object menu command breaks (CD-31): Join, as ChemDraw's.
import assert from "node:assert/strict";
import { EMPTY, addRing, fragments, joinSelection, merge, pos } from "./edit.ts";
import type { Mol } from "./render.ts";

const chain = (x: number, y: number, label = "C", dx = 1, dy = 0): Mol => ({ atoms: [{ label: "C", location: [x, y, 0] }, { label, location: [x + dx, y + dy, 0] }], bonds: [{ type: 1, atoms: [0, 1] }] });

// Two atoms, one in each structure: the earlier structure moves onto the later atom, and the two become one.
{
  const m = merge(chain(0, 0), chain(3, 1, "O"), [0, 0]); // atoms 0-1 and 2-3
  const out = joinSelection(m, new Set([1, 2]))!;
  assert.equal(out.atoms.length, 3);
  assert.equal(fragments(out).length, 1);
  assert.deepEqual(pos(out, 1), [3, 1]); // the later structure stays put
  assert.equal(joinSelection(m, new Set([0, 1])), undefined, "two atoms of one structure do not join");
  // A plain carbon joined to a labelled atom takes its label.
  const labelled = joinSelection(merge(chain(0, 0, "N"), chain(3, 0), [0, 0]), new Set([1, 2]))!;
  assert.deepEqual(labelled.atoms.map((a) => a.label).sort(), ["C", "C", "N"]);
  console.log("objects.check: Join two atoms ok");
}

// Three or more atoms: each structure moves so its atom is at the centroid; they become one atom.
{
  const m = merge(merge(chain(0, 0, "C", -1, 0), chain(0, 4, "C", 0, 1), [0, 0]), chain(4, 2, "C", 1, 0), [0, 0]); // atoms 0, 2 and 4 joined
  const out = joinSelection(m, new Set([0, 2, 4]))!;
  assert.equal(out.atoms.length, 4);
  assert.equal(out.bonds.length, 3);
  const centre = out.atoms.findIndex((_, i) => out.bonds.filter((b) => b.atoms.includes(i)).length === 3);
  assert.ok(Math.hypot(pos(out, centre)[0] - 4 / 3, pos(out, centre)[1] - 2) < 1e-9);
  // The first atom picked keeps its label, as ChemDraw keeps the first selected atom.
  const named = { ...m, atoms: m.atoms.map((a, i) => (i === 2 ? { ...a, label: "N" } : i === 4 ? { ...a, label: "O" } : a)) };
  assert.equal(joinSelection(named, new Set([4, 0, 2]))!.atoms.filter((a) => a.label !== "C").map((a) => a.label).join(), "O");
  console.log("objects.check: Join three atoms ok");
}

// Two bonds, one in each structure: they become one shared bond (two benzenes make naphthalene).
{
  const a = addRing(EMPTY, 6, false, { point: [0, 0] }), b = addRing(EMPTY, 6, false, { point: [0, 0] });
  const m = merge(a, b, [5, 3]);
  const [p, q] = a.bonds[0].atoms, [r, s] = b.bonds[2].atoms.map((i) => i + 6);
  const out = joinSelection(m, new Set([p, q, r, s]))!;
  assert.equal(out.atoms.length, 10);
  assert.equal(out.bonds.length, 11);
  assert.equal(fragments(out).length, 1);
  // The later ring stays where it was; the earlier one moved onto it.
  for (let i = 6; i < 12; i++) assert.ok(out.atoms.some((_, k) => Math.hypot(pos(out, k)[0] - pos(m, i)[0], pos(out, k)[1] - pos(m, i)[1]) < 1e-9));
  // Each ring keeps its fill (CD-27): the moved ring's fill takes the atoms it joined.
  const filled = joinSelection({ ...m, fills: [{ atoms: [0, 1, 2, 3, 4, 5], colour: "#2F6FED" }, { atoms: [6, 7, 8, 9, 10, 11], colour: "#E5484D" }] }, new Set([p, q, r, s]))!;
  assert.equal(filled.fills?.length, 2);
  for (const f of filled.fills!) assert.ok(f.atoms.every((i, k) => filled.bonds.some((b) => b.atoms.includes(i) && b.atoms.includes(f.atoms[(k + 1) % 6]))), "each fill is still a closed ring");
  console.log("objects.check: Join two bonds ok");
}

// CD-29: TLC plates. Lanes added, duplicated, deleted and moved at a lane, the plate growing or shrinking by a lane.
import { addLane, deleteLane, moveLane, restyleSpot } from "./edit.ts";
import { fromCdxml, spotType, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { parse, serialize } from "./file.ts";
import type { Shape } from "./render.ts";
{
  const plate: Shape = { id: 1, kind: "tlc", from: [0, 0], to: [3, 4], tlc: { lanes: 3, spots: [{ lane: 0, rf: 0.2 }, { lane: 1, rf: 0.5 }, { lane: 2, rf: 0.8 }] } };
  const added = addLane(plate, 1);
  assert.deepEqual([added.tlc!.lanes, added.to, added.tlc!.spots.map((s) => s.lane)], [4, [4, 4], [0, 2, 3]]);
  const copied = addLane(plate, 2, 1);
  assert.deepEqual(copied.tlc!.spots.map((s) => [s.lane, s.rf]), [[0, 0.2], [1, 0.5], [3, 0.8], [2, 0.5]], "Duplicate puts the lane's spots in the new lane");
  const gone = deleteLane(plate, 1);
  assert.deepEqual([gone.tlc!.lanes, gone.to, gone.tlc!.spots.map((s) => [s.lane, s.rf])], [2, [2, 4], [[0, 0.2], [1, 0.8]]]);
  assert.equal(deleteLane(deleteLane(gone, 0), 0).tlc!.lanes, 1, "a plate keeps one lane");
  assert.deepEqual(moveLane(plate, 0, 2).tlc!.spots.map((s) => [s.lane, s.rf]), [[2, 0.2], [0, 0.5], [1, 0.8]]);
  // Spot styles go together as ChemDraw's: dashed is hollow and not doubled; filled is not dashed.
  const dashed = restyleSpot({ lane: 0, rf: 0.5, doubled: true }, "dashed");
  assert.deepEqual(dashed, { lane: 0, rf: 0.5, style: "hollow", dashed: true });
  assert.deepEqual(restyleSpot(dashed, "filled"), { lane: 0, rf: 0.5 });
  assert.deepEqual(restyleSpot(restyleSpot({ lane: 0, rf: 0.5 }, "bold"), "doubled"), { lane: 0, rf: 0.5, bold: true, doubled: true });
  assert.deepEqual(restyleSpot({ lane: 0, rf: 0.5, bold: true }, "bold", false), { lane: 0, rf: 0.5 });
  // CDXML: ChemDraw's CurveType (Filled 128, Dashed 2, Bold 4, Doubled 512); no Filled is a hollow spot.
  assert.deepEqual([spotType({ lane: 0, rf: 0 }), spotType({ lane: 0, rf: 0, style: "hollow", dashed: true }), spotType({ lane: 0, rf: 0, bold: true, doubled: true }), spotType({ lane: 0, rf: 0, style: "shaded" })], [128, 2, 644, 384]);
  const chemdraw = fromCdxml(`<CDXML BondLength="14.40"><page><tlcplate id="5" TopLeft="100 100" TopRight="200 100" BottomRight="200 300" BottomLeft="100 300" ShowSideTicks="yes" Transparent="yes"><tlclane id="6">
<tlcspot id="7" Rf="0.2"/><tlcspot id="8" Rf="0.4" CurveType="128"/><tlcspot id="9" Rf="0.6" CurveType="6"/><tlcspot id="10" Rf="0.8" CurveType="640"/></tlclane></tlcplate></page></CDXML>`).mol.shapes![0].tlc!;
  assert.deepEqual([chemdraw.ticks, chemdraw.transparent], [true, true]);
  assert.deepEqual(chemdraw.spots.map((s) => [s.style, s.dashed, s.bold, s.doubled]), [["hollow", undefined, undefined, undefined], [undefined, undefined, undefined, undefined], ["hollow", true, true, undefined], [undefined, undefined, undefined, true]]);
  // Octet's own file keeps every style, and its plate's ticks and transparency.
  const mine: Shape = { id: 2, kind: "tlc", from: [0, 0], to: [3, 4], tlc: { lanes: 2, ticks: true, transparent: true, spots: [{ lane: 0, rf: 0.3 }, { lane: 1, rf: 0.6, style: "hollow", dashed: true, bold: true }, { lane: 1, rf: 0.9, doubled: true, style: "shaded" }] } };
  const back = fromCdxml(toCdxml({ atoms: [], bonds: [], shapes: [mine] }, DEFAULT_STYLE)).mol.shapes![0].tlc!;
  assert.deepEqual({ ...back, spots: back.spots.map((s) => ({ ...s, w: undefined, h: undefined })) }, { ...mine.tlc, spots: mine.tlc!.spots.map((s) => ({ ...s, w: undefined, h: undefined })) });
  // Octet's own file and clipboard keep them too.
  assert.deepEqual(parse(serialize({ atoms: [], bonds: [], shapes: [mine] })).shapes![0].tlc, mine.tlc);
  console.log("objects.check: TLC lanes, spot styles, side ticks and transparency ok");
}

// Issue 96: gels and plasmid maps, laid out from their data. A gel's bands sit by their sizes on a log scale and keep
// their sizes when its range changes; its lane names go with their lanes. A plasmid map puts base pair 1 at the top,
// overlapping regions on tracks of their own, and its names a line apart. Both survive .oct and CDXML.
import { addBands, newGel, setRange, withLadder } from "./edit.ts";
import { bandRf, bandSize, gelScale, namesTurn, plasmidLayout, tlcLayout } from "./render.ts";
{
  const close = (a: number, b: number) => Math.abs(a - b) < 1e-6 * Math.max(1, Math.abs(b));
  const made = { id: 3, ...newGel([0, 0], [6, -6]) } as Shape, t = made.tlc!, sizes = (x: Shape, lane: number) => x.tlc!.spots.filter((s) => s.lane === lane).map((s) => Number(bandSize(x.tlc, s.rf).toPrecision(6)));
  assert.deepEqual([made.kind, t.lanes, t.unit, t.names], ["gel", 5, "kDa", ["M", "1", "2", "3", "4"]]);
  assert.deepEqual(sizes(made, 0), [250, 150, 100, 75, 50, 37, 25, 20, 15, 10], "a new gel's first lane is the protein ladder");
  const lay = tlcLayout(made);
  assert.ok(t.spots.every((s, k) => s.rf > 0 && s.rf < 1 && (k === 0 || lay.at(s.rf) < lay.at(t.spots[k - 1].rf))), "smaller bands run further down");
  assert.ok(close(bandSize(t, bandRf(t, 42)), 42) && lay.at(0) > lay.at(1) && lay.at(0) < lay.y1);
  assert.ok(close(bandSize(t, lay.snap(lay.at(bandRf(t, 63.4)))), 63), "a press gives a size to two figures");
  const loaded = { ...made, tlc: addBands(t, 2, [66, 45, 0, -3]) };
  assert.deepEqual(sizes(loaded, 2), [66, 45], "Add Bands takes only sizes above 0");
  // Set Range: bands keep their sizes; one outside the range is kept, not drawn.
  const narrow = { ...loaded, tlc: setRange(loaded.tlc!, [20, 120]) };
  assert.deepEqual(sizes(narrow, 2), [66, 45]);
  assert.ok(narrow.tlc!.spots.filter((s) => s.lane === 0).some((s) => s.rf < 0) && narrow.tlc!.spots.filter((s) => s.lane === 0).some((s) => s.rf > 1));
  // A very narrow range (or a tiny size) still saves a drawing Octet can open; a band rounded past an end stays drawn.
  const tight = { ...loaded, tlc: addBands(setRange(loaded.tlc!, [100, 101]), 1, [1e-200]) };
  assert.doesNotThrow(() => parse(serialize({ atoms: [], bonds: [], shapes: [tight] })));
  const odd = tlcLayout({ ...made, tlc: setRange(t, [5.55, 400]) });
  assert.ok(odd.snap(odd.front) <= 1 && odd.snap(odd.origin) >= 0);
  const dna = { ...made, tlc: withLadder(made.tlc!, "bp") };
  assert.deepEqual([dna.tlc!.unit, sizes(dna, 0)], ["bp", [10000, 8000, 6000, 5000, 4000, 3000, 2000, 1500, 1000, 500]]);
  // Lane names go with their lanes: a new lane is named by the lanes before it, a copy as its lane.
  assert.deepEqual(addLane(loaded, 5).tlc!.names, ["M", "1", "2", "3", "4", "5"]);
  assert.deepEqual(addLane(loaded, 1, 0).tlc!.names, ["M", "M", "1", "2", "3", "4"]);
  assert.deepEqual(deleteLane(loaded, 1).tlc!.names, ["M", "2", "3", "4"]);
  assert.deepEqual(moveLane(loaded, 0, 4).tlc!.names, ["1", "2", "3", "4", "M"]);
  // The scale names the ladder, thinned to a line apart from the top down; long names turn.
  assert.deepEqual(gelScale(made, 0), [250, 150, 100, 75, 50, 37, 25, 20, 15, 10]);
  const thin = gelScale(made, 0.5);
  assert.ok(thin[0] === 250 && thin.length < 10 && thin.every((n, k) => k === 0 || lay.at(bandRf(t, thin[k - 1])) - lay.at(bandRf(t, n)) >= 0.5));
  assert.deepEqual(gelScale({ ...made, tlc: { ...t, spots: [] } }, 0), [200, 100, 50, 20, 10, 5], "no ladder: 1, 2 and 5 in the range");
  assert.deepEqual([namesTurn(made, (n) => n.length * 0.4), namesTurn(made, (n) => n.length * 2)], [false, true]);
  // The plasmid map: base pair 1 at the top, clockwise; overlapping regions on tracks; one through 1 wraps.
  const map: Shape = { id: 4, kind: "plasmid", from: [0, 0], to: [8, -8], plasmid: { bp: 4000, name: "pX", regions: [{ start: 100, end: 900, name: "a" }, { start: 800, end: 1200, name: "b", dir: "reverse" }, { start: 3800, end: 50, name: "c", dir: "none" }],
    markers: [{ at: 1000, name: "EcoRI" }, { at: 1010, name: "BamHI" }, { at: 1020, name: "XhoI" }] } };
  const m = plasmidLayout(map, 0.8);
  assert.ok(close(m.at(1, 2)[0], 4) && close(m.at(1, 2)[1], -2) && close(m.at(1001, 2)[0], 6), "bp 1 at the top and a quarter of the way on at the right");
  assert.ok(m.regions[1].path.some((q) => Math.hypot(q[0] - m.c[0], q[1] - m.c[1]) > m.R + 0.2), "an overlapping region goes out on a track of its own");
  assert.ok(m.regions[2].path.every((q) => Math.abs(Math.hypot(q[0] - m.c[0], q[1] - m.c[1]) - m.R) < 0.11), "c shares the first track with a, through bp 1");
  const right = m.labels.filter((x) => x.right).sort((a, b) => b.y - a.y);
  assert.equal(right.length, 5);
  assert.ok(right.every((x, k) => k === 0 || right[k - 1].y - x.y >= 0.8 - 1e-9), "names are spread a line apart");
  // Saved and read back, in Octet's own file and in CDXML; a marker past the end is a damaged file.
  const both = { atoms: [], bonds: [], shapes: [loaded, map] };
  assert.deepEqual(parse(serialize(both)).shapes!.map((x) => [x.tlc, x.plasmid]), [[loaded.tlc, undefined], [undefined, map.plasmid]]);
  const read = fromCdxml(toCdxml(both, DEFAULT_STYLE));
  assert.deepEqual([read.lost, read.mol.shapes!.map((x) => [x.kind, x.tlc, x.plasmid])], [{}, [["gel", loaded.tlc, undefined], ["plasmid", undefined, map.plasmid]]]);
  assert.throws(() => parse(serialize({ atoms: [], bonds: [], shapes: [{ ...map, plasmid: { ...map.plasmid!, markers: [{ at: 4001, name: "x" }] } }] })), /damaged/);
  assert.throws(() => parse(serialize({ atoms: [], bonds: [], shapes: [{ id: 5, kind: "tlc", from: [0, 0], to: [1, 1], tlc: { lanes: 1, spots: [], names: ["A"] } }] })), /damaged/, "lane names are a gel's");
  console.log("objects.check: gels and plasmid maps ok");
}

// A gel or plasmid map Octet saves, Octet opens again, whatever was typed, dragged or picked with it; and a file with
// a range no dialog gives is refused, not drawn for ever.
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { oneLine } from "./experiment.ts";
import { readOct, writeOct } from "./oct.ts";
import { isPlate, turns } from "./render.ts";
{
  const gel = { id: 3, ...newGel([0, 0], [6, -6]) } as Shape, t = gel.tlc!;
  const map: Shape = { id: 4, kind: "plasmid", from: [0, 0], to: [8, -8], plasmid: { bp: 4000, regions: [], markers: [] } };
  const opened = (shapes: Shape[]) => { const back = readOct(writeOct({ atoms: [], bonds: [], shapes }, DEFAULT_STYLE), true); return [back.foreign, back.lost, back.mol.shapes?.map((x) => x.kind)]; };
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  // A range whose sizes are so small that a tenth of one is 0: the file is damaged, and the scale of such a gel
  // (run apart, with a time limit) ends at once.
  const tiny: Shape = { ...gel, tlc: { ...t, spots: [], range: [5e-324, 1e-323] } };
  assert.throws(() => parse(serialize({ atoms: [], bonds: [], shapes: [tiny] })), /damaged/, "a range below the dialog's least is refused");
  assert.doesNotThrow(() => parse(serialize({ atoms: [], bonds: [], shapes: [{ ...gel, tlc: { ...t, range: [0.001, 1e9] } }] })), "the dialog's widest range is read");
  const run = spawnSync(process.execPath, ["--input-type=module", "-e", `import { gelScale } from ${JSON.stringify(new URL("render.ts", import.meta.url).href)}; gelScale(${JSON.stringify(tiny)}, 0.2);`], { timeout: 20_000, encoding: "utf8" });
  assert.equal(run.status, 0, `a gel's scale ends for any range: ${run.error?.message ?? run.stderr}`);
  // A name pasted with a tab in it is one line where the dialogs apply it, so the gel and the map are still there
  // when the file is opened again. (A control character in a name is a damaged file.)
  const tab = "WT\tKO", named = (name: string): Shape[] => [{ ...gel, tlc: { ...t, names: t.names!.map((n, k) => (k === 1 ? name : n)) } }, { ...map, plasmid: { bp: 4000, name, regions: [{ start: 1, end: 900, name }], markers: [{ at: 1000, name }] } }];
  assert.equal(oneLine(tab), "WT KO");
  assert.deepEqual(opened(named(oneLine(tab))), [undefined, {}, ["gel", "plasmid"]]);
  assert.throws(() => parse(serialize({ atoms: [], bonds: [], shapes: named(tab) })), /damaged/);
  assert.match(editor, /\(k === dialog\.lane \? oneLine\(dialog\.value\) : /, "the lane name");
  assert.match(editor, /plasmid: \{ \.\.\.pl, bp, name: oneLine\(dialog\.name\) \|\| undefined,/, "the plasmid's name");
  assert.match(editor, / region: Region = \{ start, end, \.\.\.\(name \? \{ name \} : \{\}\),/, "a region's name");
  assert.match(editor, /const marker: Marker = \{ at, name, /, "a marker's name");
  assert.equal(editor.match(/name = oneLine\(dialog\.name\)/g)?.length, 2, "the region and marker dialogs clean the name once each");
  // A gel dragged wider than 40 lanes' worth has 40 lanes, the most a file holds; the TLC plate tool stops there too.
  const wide = { id: 5, ...newGel([0, 0], [50, -6]) } as Shape;
  assert.deepEqual([wide.tlc!.lanes, wide.tlc!.names!.length], [40, 40]);
  assert.deepEqual(opened([wide]), [undefined, {}, ["gel"]]);
  assert.match(editor, /kind: "tlc", from, to, tlc: \{ lanes: Math\.min\(TLC_LANES, Math\.max\(1, /);
  // The shape chips (Box, Oval…) change only shapes that take a kind: a gel or map picked with a box keeps its kind,
  // because an oval that holds gel data is a damaged file. Boxes, ovals, highlights and brackets all take one.
  assert.deepEqual((["box", "rounded", "oval", "highlight", "brackets", "parens", "braces", "tlc", "gel", "plasmid", "table", "picture"] as const).filter((kind) => !turns({ kind })), ["tlc", "gel", "plasmid", "table", "picture"]);
  assert.throws(() => parse(serialize({ atoms: [], bonds: [], shapes: [{ ...gel, kind: "oval" }] })), /damaged/);
  assert.match(editor, /return each\(\(x\) => \(turns\(x\) \? \{ kind: arg as ShapeKind, [^\n]* : \{\}\)\);/);
  // The plate actions change plates only: a plasmid map or box picked with a gel is given no lanes or spots.
  assert.deepEqual([isPlate(gel), isPlate({ kind: "tlc" }), isPlate(map), isPlate({ kind: "box" })], [true, true, false, false]);
  assert.throws(() => parse(serialize({ atoms: [], bonds: [], shapes: [{ ...map, tlc: { rf: true } as never }] })), /damaged/);
  assert.match(editor, /const plates = \(f: \(x: Shape\) => Partial<Shape>\) => each\(\(x\) => \(isPlate\(x\) \? f\(x\) : \{\}\)\);/);
  for (const what of ["lanes", "rf", "hide", "spots"]) assert.match(editor, new RegExp(`if \\(what === "${what}"\\) return plates\\(`), what);
  assert.match(editor, /if \(what === "ticks" \|\| what === "transparent"\) return plates\(/);
  // A double-click on a caption, atom or bond goes to it, also over a gel's lane names or in a plasmid map's box; a
  // map takes the double-click only on a region, a marker or its middle.
  assert.match(editor, /const named = tool !== "erase" && bare \? laneNameAt\(/);
  assert.match(editor, /const map = tool !== "erase" && bare \? plasmidAt\(/);
  assert.match(editor, /const bare = t\.caption === undefined && t\.atom === undefined && t\.bond === undefined;/);
  assert.match(editor, /if \(map && \(part\.region !== undefined \|\| part\.marker !== undefined \|\| part\.centre\)\) return openPart\(map, part\);/);
  console.log("objects.check: gels and plasmid maps stay readable ok");
}

// CD-33: a template keeps the whole selection (its text, arrows, shapes and look) and goes where it is placed.
import { addTemplate, extractSelection, normalise } from "./edit.ts";
import { loadTemplates, newTemplate } from "./templates.ts";
{
  const ring = addRing(EMPTY, 6, false, { point: [0, 0] });
  const drawn = { ...ring, atoms: ring.atoms.map((a, i) => (i === 0 ? { ...a, colour: "#E5484D", label: "N" } : a)), bonds: ring.bonds.map((b, k) => (k === 1 ? { ...b, colour: "#2F6FED" } : b)),
    arrows: [{ id: 10, kind: "reaction" as const, from: [2, 0] as [number, number], to: [4, 0] as [number, number] }], captions: [{ id: 11, text: "heat", x: 3, y: 0.5 }, { id: 12, text: "1", x: 0, y: 0, under: [0, 1, 2, 3, 4, 5] }],
    shapes: [{ id: 13, kind: "box" as const, from: [-2, -2] as [number, number], to: [5, 2] as [number, number] }] };
  const part = extractSelection(drawn, new Set(drawn.atoms.map((_, i) => i)), new Set([10, 11, 13]));
  const saved = newTemplate("Step", part, "Reactions"), [t] = loadTemplates([saved]);
  assert.equal(t.set, "Reactions");
  assert.deepEqual([t.mol.atoms.length, t.mol.arrows?.length, t.mol.captions?.length, t.mol.shapes?.length], [6, 1, 2, 1]);
  // Placed at a point, its middle is there, and everything keeps its place against the ring.
  const placed = addTemplate(EMPTY, t.mol, { point: [10, 10] }), n = placed.atoms.findIndex((a) => a.label === "N");
  assert.deepEqual([placed.atoms[n].colour, placed.bonds.filter((b) => b.colour === "#2F6FED").length, placed.arrows?.length, placed.captions?.length, placed.shapes?.length], ["#E5484D", 1, 1, 2, 1]);
  const dx = placed.arrows![0].from[0] - placed.atoms[n].location[0];
  assert.ok(Math.abs(dx - (2 - drawn.atoms[0].location[0])) < 1e-9, "the arrow keeps its place against the structure");
  assert.deepEqual(placed.captions!.find((c) => c.text === "1")!.under!.length, 6, "a compound number stays under its structure");
  // A template with no structure (an arrow and its text) places at the point, centred.
  const arrowOnly = normalise(extractSelection(drawn, new Set(), new Set([10, 11])));
  assert.equal(loadTemplates([newTemplate("Arrow", arrowOnly)]).length, 1, "a template with no atoms is kept");
  const a = addTemplate(EMPTY, arrowOnly, { point: [5, 5] }).arrows![0];
  assert.ok(Math.abs((a.from[0] + a.to[0]) / 2 - 5) < 1e-9 && a.from[1] < 5);
  // A multi-centre point (a π ligand) names its ring's atoms as they are numbered in the drawing it goes into.
  const cp = { ...ring, atoms: [...ring.atoms, { label: "C", location: [0, 0, 0] as [number, number, number], centre: { atoms: [0, 1, 2, 3, 4, 5] } }, { label: "Fe", location: [0, -1.5, 0] as [number, number, number] }], bonds: [...ring.bonds, { type: 1, atoms: [6, 7] as [number, number] }] };
  const two = addTemplate(addRing(EMPTY, 5, false, { point: [-20, 0] }), normalise(cp), { point: [10, 0] }), point = two.atoms.find((x) => x.centre)!;
  assert.deepEqual(point.centre!.atoms.map((i) => two.atoms[i].location[0] > 5), [true, true, true, true, true, true], "the ligand's atoms are the new ring's");
  console.log("objects.check: templates keep the whole selection ok");
}

// CD-39: the Synthesis and Retrosynthesis tools: a line through bonds makes the reaction that forms (or breaks) them.
import { cutReaction } from "./edit.ts";
{
  const butane: Mol = { atoms: [0, 1, 2, 3].map((k) => ({ label: "C", location: [k * 0.87, k % 2 ? 0.5 : 0, 0] as [number, number, number] })), bonds: [0, 1, 2].map((k) => ({ type: 1, atoms: [k, k + 1] as [number, number] })) };
  const s = cutReaction(butane, [1.3, 1], [1.3, -1], false)!;
  assert.deepEqual([s.cut, s.mol.atoms.length, s.mol.bonds.length, s.mol.arrows?.map((a) => a.kind), s.mol.captions?.map((c) => c.text)], [1, 8, 5, ["reaction"], ["+"]]);
  // Synthesis: the pieces, then the arrow, then the structure, all on one level line.
  const arrow = s.mol.arrows![0], xs = (ids: number[]) => ids.map((i) => s.mol.atoms[i].location[0]);
  assert.ok(Math.max(...xs([0, 1, 2, 3])) < arrow.from[0] && Math.min(...xs([4, 5, 6, 7])) > arrow.to[0]);
  assert.ok(Math.abs(fragments(s.mol).length - 3) === 0);
  // Retrosynthesis: the structure, a retrosynthetic arrow, then the pieces.
  const r = cutReaction(butane, [1.3, 1], [1.3, -1], true)!, ra = r.mol.arrows![0];
  assert.equal(ra.kind, "retro");
  assert.ok(Math.max(...[4, 5, 6, 7].map((i) => r.mol.atoms[i].location[0])) < ra.from[0] && Math.min(...[0, 1, 2, 3].map((i) => r.mol.atoms[i].location[0])) > ra.to[0]);
  // Bonds in aromatic rings stay whole, as in ChemDraw.
  const benzene = addRing(EMPTY, 6, true, { point: [0, 0] }), mid = (k: number) => { const [a, b] = benzene.bonds[k].atoms.map((i) => pos(benzene, i)); return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; };
  const [mx, my] = mid(0), across = cutReaction(benzene, [mx - 0.3, my - 0.3 * (mx || 1)], [mx + 0.3, my + 0.3 * (mx || 1)], false);
  assert.deepEqual(across && [across.cut, across.aromatic], [0, 1]);
  assert.equal(cutReaction(butane, [5, 5], [6, 6], false), undefined, "a line through no bond does nothing");
  console.log("objects.check: Synthesis and Retrosynthesis ok");
}
