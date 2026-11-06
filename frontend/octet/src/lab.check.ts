// Run: node src/lab.check.ts. The library's Lab group (tools/library/lab.mjs): each lamp and piece of glassware is one
// integral group of pen curves and lines that goes where it is placed, takes the document's line width, and comes
// back whole from CDXML and from a .oct file.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { addRing, addTemplate, EMPTY } from "./edit.ts";
import { readOct, writeOct } from "./oct.ts";
import type { Arrow, Group, Mol } from "./render.ts";

type Item = { name: string; also?: string; atoms: unknown[]; bonds: unknown[]; arrows: Arrow[]; groups: Group[]; icon: number[]; mol?: Mol };
const library: { name: string; items: Item[] }[] = JSON.parse(readFileSync(new URL("./library.json", import.meta.url), "utf8"));
const all = library.find((c) => c.name === "Lab")!;
assert.deepEqual(all.items.map((t) => t.name), ["Light bulb", "LED", "Round-bottom flask", "Beaker", "Conical flask", "Reflux condenser", "Separatory funnel", "Test tube",
  "Schlenk flask", "Vial", "Syringe", "Chromatography column", "Heating mantle", "Hotplate stirrer", "Stirrer bar", "TLC plate"]);
// The TLC plate is Octet's own TLC object (the TLC tool's), so its lanes and spots stay editable.
const plate = all.items.find((t) => t.name === "TLC plate")!.mol!;
assert.deepEqual(plate.shapes?.map((x) => [x.kind, x.tlc?.lanes]), [["tlc", 3]]);
assert.equal(plate.atoms.length + (plate.arrows?.length ?? 0), 0);
const lab = { items: all.items.filter((t) => !t.mol) };

const box = (arrows: Arrow[]) => {
  const qs = arrows.flatMap((a) => (a.curve ? a.curve.points.map((p) => p.at) : [a.from, a.to])), xs = qs.map((q) => q[0]), ys = qs.map((q) => q[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
};
const near = (a: number, b: number, d = 1e-3) => Math.abs(a - b) <= d;
// Two curves are the same when their points (and handles) are within d bond lengths.
const sameArrow = (a: Arrow, b: Arrow, d: number) => {
  assert.equal(b.kind, a.kind);
  assert.equal(!!b.curve?.closed, !!a.curve?.closed);
  assert.equal(b.fill, a.fill);
  assert.equal(b.colour?.toUpperCase(), a.colour?.toUpperCase());
  const qs = (x: Arrow) => (x.curve ? x.curve.points.flatMap((p) => [p.at, p.c1 ?? p.at, p.c2 ?? p.at]) : [x.from, x.to]);
  const [p, q] = [qs(a), qs(b)];
  assert.equal(q.length, p.length);
  p.forEach((v, i) => assert.ok(near(v[0], q[i][0], d) && near(v[1], q[i][1], d), `${a.kind} point ${i}: ${v} came back as ${q[i]}`));
};

for (const t of lab.items) {
  const mol: Mol = { atoms: [], bonds: [], arrows: t.arrows, groups: t.groups };
  // Drawn with Octet's own objects, all in one group, centred like every template.
  assert.equal(t.atoms.length + t.bonds.length, 0, t.name);
  assert.ok(t.arrows.every((a) => a.kind === "curve" || a.kind === "line"), t.name);
  assert.deepEqual(t.groups.map((g) => [g.atoms.length, [...g.items].sort((x, y) => x - y), g.integral]), [[0, t.arrows.map((a) => a.id).sort((x, y) => x - y), true]], t.name);
  const [x0, y0, x1, y1] = box(t.arrows);
  assert.ok(near((x0 + x1) / 2, 0, 0.002) && near((y0 + y1) / 2, 0, 0.002), `${t.name} is centred`);
  // Sized against each other: a flask 2 to 5.5 bond lengths tall, a stirrer bar a third of one across.
  assert.ok(Math.max(x1 - x0, y1 - y0) >= 1.2 && y1 - y0 <= 5.5, `${t.name} is ${x1 - x0} by ${y1 - y0} bond lengths`);
  // One line width: no object sets its own, so every line takes the document's. Fills are closed curves; lines are ink.
  assert.ok(t.arrows.every((a) => a.width === undefined && a.scale === undefined), t.name);
  assert.ok(t.arrows.every((a) => !a.fill || (a.curve?.closed && a.fill === "solid")), t.name);
  assert.ok(t.arrows.filter((a) => !a.fill).every((a) => a.colour === undefined), t.name);
  assert.ok(t.arrows.some((a) => !a.fill), t.name);
  // Its icon draws some of its lines (never a fill), and a detailed item leaves its fine parts out.
  assert.ok(t.icon.length && t.icon.every((id) => t.arrows.some((a) => a.id === id && !a.fill)), t.name);
  if (["Light bulb", "LED", "Reflux condenser"].includes(t.name)) assert.ok(t.icon.length < t.arrows.filter((a) => !a.fill).length, t.name);

  // Placed at a point, its middle is there, with new ids in a new group.
  const placed = addTemplate(addRing(EMPTY, 6, false, { point: [-6, 0] }), mol, { point: [10, 5] });
  const ids = new Set(placed.arrows!.map((a) => a.id));
  const [a0, b0, a1, b1] = box(placed.arrows!);
  assert.ok(near((a0 + a1) / 2, 10, 0.002) && near((b0 + b1) / 2, 5, 0.002), `${t.name} goes where it is placed`);
  // It keeps its way up: every point moves by the same step, so a lamp's rays stay above its glass.
  placed.arrows!.forEach((a, i) => assert.ok(near(a.from[0], t.arrows[i].from[0] + 10) && near(a.from[1], t.arrows[i].from[1] + 5), `${t.name} keeps its way up`));
  assert.equal(placed.groups?.length, 1);
  assert.deepEqual(new Set(placed.groups![0].items), ids);
  // A click on a bond or atom with it in hand puts it at the click, not at the drawing's origin.
  const onBond = addTemplate(placed, mol, { bond: 0, point: [20, -5] }), mine = onBond.arrows!.filter((a) => !ids.has(a.id));
  const [c0, d0, c1, d1] = box(mine);
  assert.ok(near((c0 + c1) / 2, 20, 0.002) && near((d0 + d1) / 2, -5, 0.002), `${t.name} on a bond goes to the click`);

  // CDXML (as ChemDraw reads it): every curve, line, fill and colour, and the group, come back.
  const read = fromCdxml(toCdxml(placed, DEFAULT_STYLE));
  assert.deepEqual(read.lost, {}, t.name);
  assert.equal(read.mol.atoms.length, 6);
  assert.equal(read.mol.arrows?.length, placed.arrows!.length, `${t.name}: every object comes back`);
  // The writer may put the fills first (they draw behind): each object matches the nearest of its kind that came back.
  const first = (a: Arrow) => a.curve?.points[0].at ?? a.from, gap = (a: Arrow, b: Arrow) => Math.hypot(first(a)[0] - first(b)[0], first(a)[1] - first(b)[1]);
  for (const a of placed.arrows!) {
    const like = read.mol.arrows!.filter((b) => b.kind === a.kind && !!b.fill === !!a.fill && (b.curve?.points.length ?? 2) === (a.curve?.points.length ?? 2)).sort((p, q) => gap(a, p) - gap(a, q));
    sameArrow(a, like[0] ?? assert.fail(`${t.name}: a ${a.kind} is lost`), 0.002);
  }
  assert.equal(read.mol.groups?.length, 1, `${t.name}: one group`);
  assert.equal(read.mol.groups![0].items.length, placed.arrows!.length);
  assert.ok(read.mol.groups![0].integral, "a click picks all of it, as ChemDraw's clip art");
  // A .oct file gives it back as it was.
  const oct = readOct(writeOct(placed, DEFAULT_STYLE)).mol;
  assert.equal(oct.arrows?.length, placed.arrows!.length);
  placed.arrows!.forEach((a, i) => { assert.equal(oct.arrows![i].id, a.id); sameArrow(a, oct.arrows![i], 1e-9); });
  assert.deepEqual(oct.groups, placed.groups);
}
// Search words for the names other labs use.
assert.match(lab.items.find((t) => t.name === "Conical flask")!.also ?? "", /Erlenmeyer/);
console.log(`lab.check: ${lab.items.length} lab templates place, keep one line width and round-trip through CDXML and .oct ok`);
