// Run: node src/cycletool.check.ts. The Cycle tool: a drawn circle is one arc, a click breaks it into steps, a
// structure on the circle joins it (taking a break's place), a deleted intermediate leaves a break, reagents and
// products keep their steps, and all of it survives a save.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { addBranch, addSide, addStop, attachBeside, breakAt, clearAt, cycleAtoms, dragEnd, dragMeet, dropOnCycle, endFor, followArcs, labelEnd, layoutCycles, migrateCycles, pullBranch, removeEnd, removeStop, resizeCycle, roleFor, setBranch, setEnd, setEnds, setStep, sideChoices, stepAt, stepFor, swapBranch, withEnd, type Cycle, type CycleText, type OldText } from "./cycle.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { addCaption, addCycle, addRing, deleteAtoms, deleteGraphics, EMPTY, extractSelection, fragments, insertMol, transformParts } from "./edit.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { parse, serialize } from "./file.ts";
import { readOct, writeOct } from "./oct.ts";
import { arrowPath, bendPoint, placeCaptions, type Box, type Caption, type Mol } from "./render.ts";

// Ink: each atom's position as a box a third of a bond across (px, y down).
const L = 30, ink = (m: Mol) => (atoms: number[]): Box | undefined => {
  const ps = atoms.map((i) => m.atoms[i].location);
  return ps.length ? [Math.min(...ps.map((p) => p[0])) * L - 5, -Math.max(...ps.map((p) => p[1])) * L - 5, Math.max(...ps.map((p) => p[0])) * L + 5, -Math.min(...ps.map((p) => p[1])) * L + 5] : undefined;
};
const arcs = (m: Mol) => layoutCycles(m, L, 1, ink(m)).arrows.filter((a) => a.branch === undefined);
const right = 0, top = Math.PI / 2, left = Math.PI, bottom = -Math.PI / 2;

// A new circle with no nodes is one arc, nearly all the way round.
let [m, id] = addCycle(EMPTY, { centre: [0, 0], radius: 3, clockwise: true, nodes: [], at: [] });
assert.equal(arcs(m).length, 1);

// Clicks break it: two breaks are two steps, and a click on a break joins it up again.
m = addStop(m, id, right, []);
m = addStop(m, id, left, []);
assert.equal(m.cycles![0].nodes.length, 2);
assert.equal(arcs(m).length, 2);
const c = () => m.cycles![0];
assert.equal(breakAt(m, c(), left + 0.02, 0.1), 1);
assert.equal(breakAt(m, c(), top, 0.1), undefined);

// Clockwise from the right-hand break, the bottom is step 0 and the top is step 1.
assert.equal(stepAt(m, c(), bottom), 0);
assert.equal(stepAt(m, c(), top), 1);

// A reagent on the top step stays on it when a break goes in on the bottom step, and moves on one when it goes in
// before it.
let h2: number;
[m, h2] = addCaption(m, { text: "H2", x: 0, y: 0, cycle: { cycle: id, step: 1, side: "in" } });
m = labelEnd(m, h2);
m = addStop(m, id, bottom, []);
assert.equal(m.captions![0].cycle!.step, 2);
m = removeStop(m, id, 1);
assert.equal(m.captions![0].cycle!.step, 1);
assert.equal(c().nodes.length, 2);

// A ring drawn on the circle near a break takes its place; one drawn on the circle elsewhere is a new node; one well
// inside the circle stays out.
m = addRing(m, 6, true, { point: [-3, 0] });
m = addRing(m, 6, true, { point: [0, 3] });
m = addRing(m, 6, true, { point: [0.5, 0.5] });
m = dropOnCycle(m, fragments(m));
const [ringLeft, ringTop, ringIn] = fragments(m);
assert.equal(c().nodes.length, 3);
assert.ok(c().nodes.some((n) => n.length && n.every((i) => ringLeft.includes(i))));
assert.ok(c().nodes.some((n) => n.length && n.every((i) => ringTop.includes(i))));
assert.ok(!c().nodes.flat().some((i) => ringIn.includes(i)));
assert.equal(c().nodes.filter((n) => !n.length).length, 1);

// After an edit, only what moved or is new joins.
let n = addRing(m, 6, true, { point: [3, 0.2] });
assert.equal(dropOnCycle(n, fragments(n), n).cycles![0].nodes.length, 3);
n = dropOnCycle(n, fragments(n), m);
assert.equal(n.cycles![0].nodes.length, 3); // it lands on the right-hand break

// Deleting an intermediate leaves a break where it was.
const before = c().nodes.length;
m = deleteAtoms(m, new Set(ringTop));
assert.equal(c().nodes.length, before);
assert.equal(c().nodes.filter((x) => !x.length).length, 2);
assert.ok(Math.abs(c().at![c().nodes.findIndex((x, k) => !x.length && Math.abs(c().at![k] - top) < 0.2)] - top) < 0.2);

// Saved and opened again: the breaks, their angles and the reagent's step.
const back = readOct(writeOct(m, DEFAULT_STYLE)).mol, y = back.cycles![0];
assert.equal(y.nodes.length, c().nodes.length);
assert.deepEqual(y.nodes.map((x) => x.length), c().nodes.map((x) => x.length));
y.at!.forEach((a, k) => assert.ok(Math.abs(a - c().at![k]) < 1e-3));
assert.equal(back.captions!.find((x) => x.cycle)?.cycle?.step, 1);

// An empty circle is saved and opened as one.
const empty = readOct(writeOct(addCycle(EMPTY, { centre: [1, 1], radius: 2, clockwise: false, nodes: [], at: [] })[0], DEFAULT_STYLE)).mol;
assert.equal(empty.cycles?.[0]?.nodes.length, 0);

// A side arrow's end: unset, THROUGH bond lengths round from where it meets the arc and 1.1 out. A drag to its end
// reads back as the same place (inside the circle too). The text goes beyond that end.
{
  let s: Mol, sid: number, cap: number;
  [s, sid] = addCycle(EMPTY, { centre: [0, 0], radius: 3, clockwise: true, nodes: [], at: [] });
  s = addStop(addStop(s, sid, right, []), sid, left, []);
  [s, cap] = addCaption(s, { text: "H2", x: 0, y: 0, cycle: { cycle: sid, step: 1, side: "in" } });
  s = labelEnd(s, cap);
  const lay = (x: Mol) => layoutCycles(x, L, 1, ink(x)), br = (x: Mol) => x.cycles![0].branches![0];
  const end = (x: Mol): [number, number] => { const a = lay(x).arrows.find((y) => y.caption === cap)!; return [a.from[0] * L, -a.from[1] * L]; };
  assert.deepEqual(endFor(lay(s), sid, br(s), "in", end(s), L), { along: -1.3, reach: 1.1 });
  for (const want of [{ along: -0.5, reach: 2 }, { along: -2, reach: -1 }, { along: -1, reach: 0.6 }]) {
    const moved = setEnd(s, sid, br(s).id, "in", want), got = endFor(lay(moved), sid, br(moved), "in", end(moved), L)!;
    assert.ok(Math.abs(got.along - want.along) < 0.02 && Math.abs(got.reach - want.reach) < 0.02, JSON.stringify({ want, got }));
    // Inside, the text anchor is nearer the middle than the arrow's end.
    const anchor = lay(moved).anchors.get(cap)!, r = Math.hypot(anchor.x, anchor.y), e = Math.hypot(...end(moved));
    assert.ok(want.reach < 0 ? r < e : r > e);
  }
}

// A reagent alone runs into the arc with no head; a bare other end goes out with a head, and where it meets the arc can
// move. A product written on the same step is the same side arrow: it leaves the arc where the reagent meets it, with a
// head. A step's name sits half way along its step, outside, with no arrow of its own.
{
  let s: Mol, sid: number, rid: number, pid: number, nid: number;
  [s, sid] = addCycle(EMPTY, { centre: [0, 0], radius: 3, clockwise: true, nodes: [], at: [] });
  s = addStop(addStop(s, sid, right, []), sid, left, []);
  const lay = (x: Mol) => layoutCycles(x, L, 1, ink(x)), r = (q: [number, number]) => Math.hypot(...q), mine = (x: Mol, id: number) => lay(x).arrows.filter((a) => a.caption === id || a.captionEnd === id);
  [s, rid] = addCaption(s, { text: "ArX", x: 0, y: 0, cycle: { cycle: sid, step: 1, side: "in" } });
  s = labelEnd(s, rid);
  const [a] = mine(s, rid), h = lay(s).branches[0], T = (x: Mol) => lay(x).branches[0].T;
  assert.ok(r(a.from) > 3.5 && Math.abs(r(a.to) - 3) < 0.05 && a.end === "none" && !a.start, "a reagent runs into the arc");
  assert.ok(h.in && !h.out && h.T);
  assert.ok(Math.hypot(T(setBranch(s, sid, 1, { meet: 0.7 }))[0] - h.T[0], T(setBranch(s, sid, 1, { meet: 0.7 }))[1] - h.T[1]) > 0.5);
  const tailed = withEnd(s, sid, 1, "out"), tail = lay(tailed).arrows.find((x) => x.part === "out")!;
  assert.ok(lay(tailed).branches[0].out && r(tail.to) > 3.5 && tail.end === undefined, "a bare end going out, with the head");
  assert.ok(Math.hypot(T(tailed)[0] - h.T[0], T(tailed)[1] - h.T[1]) < 1e-9, "an end added keeps where it meets the arc");
  [s, pid] = addCaption(s, { text: "MX", x: 0, y: 0, cycle: { cycle: sid, step: 1, side: "out" } });
  s = labelEnd(s, pid);
  const halves = lay(s).arrows.filter((x) => x.branch === 1);
  assert.equal(s.cycles![0].branches!.length, 1);
  assert.ok(halves.length === 2 && Math.hypot(halves[0].to[0] - halves[1].from[0], halves[0].to[1] - halves[1].from[1]) < 1e-9 && halves[0].caption === rid && halves[1].captionEnd === pid);
  [s, nid] = addCaption(s, { text: "oxidative addition", x: 0, y: 0, cycle: { cycle: sid, step: 0, side: "name" } });
  const n = lay(s).anchors.get(nid)!;
  assert.ok(Math.hypot(n.x, n.y) > 3 * L && n.y > 0, JSON.stringify(n)); // the bottom step, outside
  assert.equal(mine(s, nid).length, 0);
}

// Text on the circle is an intermediate: it takes a break's place (or makes a node), the arcs stop short of it, and
// deleted it leaves a break. A wider gap leaves more space round it.
{
  let s: Mol, sid: number, tid: number;
  [s, sid] = addCycle(EMPTY, { centre: [0, 0], radius: 3, clockwise: true, nodes: [], at: [] });
  s = addStop(addStop(s, sid, right, []), sid, left, []);
  [s, tid] = addCaption(s, { text: "Pd(OAc)2", x: 0, y: 3 });
  s = dropOnCycle(s, fragments(s));
  assert.deepEqual(s.captions!.find((c) => c.id === tid)!.cycle, { cycle: sid, step: 2, side: "node" }); // clockwise: right, left, then the top
  assert.equal(s.cycles![0].nodes.length, 3);
  // One near a break takes its place.
  let t2: number;
  const was = s;
  [s, t2] = addCaption(s, { text: "LPd", x: -3.1, y: 0.1 });
  s = dropOnCycle(s, fragments(s), was);
  assert.equal(s.cycles![0].nodes.length, 3);
  assert.equal(s.captions!.find((c) => c.id === t2)!.cycle!.step, 1);
  // The text's ink: a box two bond lengths wide round it. The arcs stop short of it.
  const box = (x: Mol) => (id: number) => { const c = x.captions!.find((y) => y.id === id)!; return [c.x * L - L, -c.y * L - 8, c.x * L + L, -c.y * L + 4] as Box; };
  const spans = (x: Mol) => layoutCycles(x, L, 1, ink(x), box(x)).spans;
  const into = spans(s).find((p) => p.step === 1)!; // from the left-hand text to the top text
  const wide = spans({ ...s, cycles: s.cycles!.map((c) => ({ ...c, gap: 20 })) }).find((p) => p.step === 1)!;
  assert.ok(wide.to < into.to && wide.from > into.from);
  // Not a break: a click there does not join the circle up.
  assert.equal(breakAt(s, s.cycles![0], top, 0.2), undefined);
  // Deleted, it leaves a break where it was.
  const gone = deleteGraphics(s, new Set([tid]));
  assert.equal(gone.cycles![0].nodes.length, 3);
  assert.equal(breakAt(gone, gone.cycles![0], top, 0.2), 2);
  // The cycle deleted, the text stays as text.
  assert.ok(!deleteGraphics(s, new Set([sid])).captions!.find((c) => c.id === tid)!.cycle);
  // Saved and opened again.
  const kept = readOct(writeOct({ ...s, cycles: s.cycles!.map((c) => ({ ...c, gap: 9 })) }, DEFAULT_STYLE)).mol;
  assert.equal(kept.cycles![0].gap, 9);
  assert.equal(kept.captions!.find((c) => c.text === "Pd(OAc)2")!.cycle!.side, "node");
}

console.log("cycle tool ok");

// Tobias, 2 November 2026: a structure as a reagent or product (saved as sides by Octet 1.0.29, now a side arrow). Its
// arrow runs between the arc and the structure, on the step beside it, and follows it. It survives a save, and
// deleting the structure leaves a bare end.
{
  // Two intermediates (top and bottom of a circle of radius 3), a reagent structure outside the right-hand step.
  const atom = (x: number, y: number, label = "C") => ({ label, location: [x, y, 0] as [number, number, number] });
  let x: Mol = { atoms: [atom(0, 3, "Pd"), atom(0, -3, "Pd"), atom(5, 0.5), atom(5.8, 0.5)], bonds: [{ atoms: [2, 3], type: 1 }] };
  [x] = addCycle(x, { centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1]], at: [top, bottom], sides: [{ atoms: [2, 3], side: "in" }] });
  x = migrateCycles(x);
  const lay = (y: Mol) => layoutCycles(y, L, 1, ink(y)).arrows;
  const side = lay(x).find((a) => a.end === "none")!;
  assert.ok(side && side.step === 0, "the reagent's arrow is on the step beside it, with no head");
  assert.ok(side.from[0] > 3 && side.from[0] < 5, "it starts just outside the structure, towards the arc");
  const out = swapBranch(x, x.cycles![0].id, 1);
  assert.ok(lay(out).some((a) => a.to[0] > 3 && a.end !== "none" && a.step === 0), "a product's arrow leaves the arc for it");
  const back = readOct(writeOct(x, DEFAULT_STYLE)).mol;
  assert.deepEqual(back.cycles![0].branches, x.cycles![0].branches, "saved");
  assert.deepEqual(deleteAtoms(x, new Set([2, 3])).cycles![0].branches![0].in, {}, "a bare end when its structure goes");
}

// One remap (resplice): a node taken out joins its two steps, a node added splits one, and whatever is on a step stays
// where it is round the circle.
{
  // Where a place on a step is round the circle: an angle (drawing units).
  const turn = (a: number) => ((a % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  const where = (x: Mol, step: number, g: number) => {
    const c = x.cycles![0], n = c.nodes.length, a0 = n ? c.at[step] : Math.PI / 2, len = n < 2 ? 2 * Math.PI : turn(a0 - c.at[(step + 1) % n]) || 2 * Math.PI;
    return turn(a0 - g * len);
  };
  const near = (a: number, b: number) => Math.min(turn(a - b), turn(b - a)) < 1e-9;
  for (const n of [2, 3, 4]) for (const j of [0, 1, n - 1]) {
    let s: Mol, sid: number;
    [s, sid] = addCycle(EMPTY, { centre: [0, 0], radius: 3, clockwise: true, nodes: [], at: [] });
    for (let k = 0; k < n; k++) s = addStop(s, sid, top - (2 * Math.PI * k) / n, []);
    s = { ...s, cycles: [{ ...s.cycles![0], steps: s.cycles![0].nodes.map((_, k) => ({ lead: k + 1, trail: 10 + k, ...(k % 2 ? {} : { kind: "equilibrium" as const }) })), branches: s.cycles![0].nodes.map((_, k) => ({ id: k + 1, step: k, meet: 0.3, in: {} })) }] };
    for (let k = 0; k < n; k++) s = addCaption(s, { text: `n${k}`, x: 0, y: 0, cycle: { cycle: sid, step: k, side: "name", at: 0.6 } })[0];
    const was = s.cycles![0].branches!.map((b) => where(s, b.step, b.meet!)), names = s.captions!.map((t) => where(s, t.cycle!.step, t.cycle!.at!));
    const after = removeStop(s, sid, j), y = after.cycles![0], joined = n <= 2 ? 0 : j === 0 ? n - 2 : j - 1, a = (j - 1 + n) % n;
    assert.equal(y.nodes.length, n - 1);
    y.branches!.forEach((b, k) => assert.ok(near(where(after, b.step, b.meet ?? 0.4), was[k]), `n ${n} j ${j} branch ${k}`));
    after.captions!.forEach((t, k) => assert.ok(near(where(after, t.cycle!.step, t.cycle!.at!), names[k]), `n ${n} j ${j} name ${k}`));
    for (const k of [a, j]) assert.equal(y.branches![k].step, joined);
    // The joined step: reversible only if both were, the first one's lead, the second one's trail.
    if (n > 1) assert.deepEqual(y.steps?.[joined], { ...(a % 2 || j % 2 ? {} : { kind: "equilibrium" }), lead: a + 1, trail: 10 + j });
  }
  // A step split under a side arrow on its second half: the arrow is on the new step, and nothing moves.
  let s: Mol, sid: number;
  [s, sid] = addCycle(EMPTY, { centre: [0, 0], radius: 3, clockwise: true, nodes: [], at: [], gap: 0 });
  s = addStop(addStop(s, sid, right, []), sid, left, []);
  s = { ...s, cycles: [{ ...s.cycles![0], branches: [{ id: 1, step: 0, meet: 0.8, in: { along: -0.7, reach: 1.4 }, out: { along: 1, reach: -0.8 } }] }] };
  const points = (x: Mol) => layoutCycles(x, L, 1, ink(x)).arrows.filter((a) => a.branch === 1).flatMap((a) => [a.from, a.to]);
  const split = addStop(s, sid, bottom, []);
  assert.equal(split.cycles![0].branches![0].step, 1);
  points(split).forEach((q, k) => assert.ok(Math.hypot(q[0] - points(s)[k][0], q[1] - points(s)[k][1]) < 1e-6, `point ${k}`));
}

// A cycle made with Make a catalytic cycle (no angles saved): an intermediate deleted leaves a break, and side arrows
// and names stay on their steps.
{
  let x = addRing(addRing(addRing(EMPTY, 6, true, { point: [0, 3] }), 6, true, { point: [3, -2] }), 6, true, { point: [-3, -2] }), sid: number;
  const rings = fragments(x);
  [x, sid] = addCycle(x, { centre: [0, 0], radius: 3, clockwise: true, nodes: rings } as Omit<Cycle, "id">);
  x = migrateCycles(x);
  x = { ...x, cycles: [{ ...x.cycles![0], branches: [{ id: 1, step: 2, in: {} }] }] };
  x = addCaption(x, { text: "step", x: 0, y: 0, cycle: { cycle: sid, step: 1, side: "name" } })[0];
  const gone = deleteAtoms(x, new Set(rings[1])), y = gone.cycles![0];
  assert.deepEqual([y.nodes.length, y.nodes[1].length, y.branches![0].step, gone.captions![0].cycle!.step], [3, 0, 2, 1]);
}

// Octet 1.0.29's reagents, products and structures as side arrows (migrateCycles).
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const base: Mol = { atoms: [atom(0, 3), atom(0, -3), atom(5, 0.5)], bonds: [] };
  const old = (captions: OldText[], extra: Partial<Cycle> = {}): Mol => ({ ...base, cycles: [{ id: 50, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1]], at: [top, bottom], ...extra }], captions: captions.map((cycle, k) => ({ id: k + 1, text: `t${k}`, x: 0, y: 0, cycle })) });
  // A reagent and a product on a step, through unset: one arrow with both ends, at their old places.
  let y = migrateCycles(old([{ cycle: 50, step: 0, side: "in", at: 0.2 }, { cycle: 50, step: 0, side: "out", reach: 2 }]));
  assert.deepEqual(y.cycles![0].branches, [{ id: 1, step: 0, in: { along: (0.2 - 0.5) * 3 * Math.PI }, out: { reach: 2 } }]);
  assert.deepEqual(y.captions!.map((c) => c.cycle), [{ cycle: 50, step: 0, side: "in", branch: 1 }, { cycle: 50, step: 0, side: "out", branch: 1 }]);
  // Kept apart: two.
  y = migrateCycles(old([{ cycle: 50, step: 0, side: "in" }, { cycle: 50, step: 0, side: "out", through: false }]));
  assert.deepEqual(y.cycles![0].branches, [{ id: 1, step: 0, in: {} }, { id: 2, step: 0, out: {} }]);
  // Alone, passing through to a tail: a bare end there.
  y = migrateCycles(old([{ cycle: 50, step: 1, side: "in", through: true, tail: [0.9, 1.5] }]));
  assert.deepEqual(y.cycles![0].branches, [{ id: 1, step: 1, meet: 0.4, in: {}, out: { along: 0.5 * 3 * Math.PI, reach: 1.5 } }]);
  // A structure: on the step its middle is beside, meeting the arc back from where it is level with it by as far as it
  // is clear of the arc and half a bond length more, so its arrow swoops out along the arc.
  y = migrateCycles(old([], { sides: [{ atoms: [2], side: "out" }] }));
  const b = y.cycles![0].branches![0];
  assert.ok(b.step === 0 && b.out!.atoms![0] === 2 && Math.abs(b.meet! - ((Math.PI / 2 - Math.atan2(0.5, 5)) / Math.PI - (Math.hypot(5, 0.5) - 3 + 0.5) / (3 * Math.PI))) < 1e-3 && !y.cycles![0].sides, JSON.stringify(b));
  // No angles: each node's angle from where its structure is.
  const { at: _, ...bare } = old([]).cycles![0];
  assert.deepEqual(migrateCycles({ ...base, cycles: [bare as Cycle] }).cycles![0].at, [top, bottom]);
  // Twice is once.
  const all = old([{ cycle: 50, step: 0, side: "in", at: 0.3 }, { cycle: 50, step: 0, side: "out" }, { cycle: 50, step: 1, side: "out", through: true }], { sides: [{ atoms: [2], side: "in" }] });
  assert.deepEqual(migrateCycles(migrateCycles(all)), migrateCycles(all));
}

// Saved and opened again (.oct): steps, side arrows (bare ends, heads, colour), scale, order and the centre label's
// place. The file still holds each text's step and side, and structure ends as sides, for Octet 1.0.29. Out of bounds
// is damaged.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const x: Mol = { atoms: [atom(0, 3), atom(0, -3), atom(5, 0.5)], bonds: [],
    cycles: [{ id: 9, centre: [0, 0], radius: 3, clockwise: false, nodes: [[0], [1]], at: [1.5708, -1.5708], scale: 1.5, order: 2, steps: [{ kind: "equilibrium", ratio: 3, bow: 0.5 }, null],
      branches: [{ id: 3, step: 1, meet: 0.2, in: { atoms: [2] }, out: {}, heads: ["left", "none"], colour: "#B42323" }, { id: 7, step: 0, out: { along: 2, reach: -1 } }] }],
    captions: [{ id: 10, text: "H2O", x: 0, y: 0, cycle: { cycle: 9, step: 0, side: "out", branch: 7 } }, { id: 11, text: "Pd", x: 0, y: 0, cycle: { cycle: 9, step: 0, side: "centre", off: [0.5, -1] } }] };
  const back = parse(serialize(x));
  assert.deepEqual([back.cycles![0], back.captions!.map((c) => c.cycle)], [{ ...x.cycles![0], id: back.cycles![0].id }, x.captions!.map((c) => ({ ...c.cycle!, cycle: back.cycles![0].id }))]);
  const json = JSON.parse(serialize(x));
  assert.deepEqual([json.cycles[0].sides, json.captions[0].cycle.side, json.captions[0].cycle.step], [[{ atoms: [2], side: "in" }], "out", 0]);
  const damaged = (change: (d: { cycles: Record<string, unknown>[]; captions: Record<string, unknown>[] }) => void) => { const d = JSON.parse(serialize(x)); change(d); assert.throws(() => parse(JSON.stringify(d)), /damaged/); };
  damaged((d) => { d.cycles[0].branches = Array.from({ length: 65 }, (_, k) => ({ id: k, step: 0, in: {} })); });
  damaged((d) => { (d.captions[0].cycle as Record<string, unknown>).branch = 3; });
  damaged((d) => { d.cycles[0].steps = [{ ratio: 0 }]; });
}
console.log("cycle model ok");

// Side arrows' shape (layoutCycles). Each half is an arc of a circle that touches the cycle at T, so a reagent comes in
// and a product leaves along the arc (a pass-through has no corner at T). Heads: one on the way out unless set. A step
// too short for an arc and a structure touching the arc still get their arrows.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  // Clockwise, top and bottom: step 0 runs down the right-hand side. With both ends, T is at (3, 0).
  const two = (extra: Partial<Cycle>, atoms = [atom(0, 3), atom(0, -3)]): Mol => ({ atoms, bonds: [], cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1]], at: [top, bottom], ...extra }] });
  const halves = (x: Mol) => layoutCycles(x, L, 1, ink(x)).arrows.filter((a) => a.branch !== undefined);
  type A = ReturnType<typeof halves>[number];
  // The circle through an arrow's ends and its bend point, and its way at an end (drawing units).
  const way = (a: A, end: "from" | "to"): [number, number] => {
    const m = bendPoint(a), [p, q, r] = [a.from, m, a.to], d = 2 * (p[0] * (q[1] - r[1]) + q[0] * (r[1] - p[1]) + r[0] * (p[1] - q[1]));
    const sq = (v: number[]) => v[0] ** 2 + v[1] ** 2, C = [(sq(p) * (q[1] - r[1]) + sq(q) * (r[1] - p[1]) + sq(r) * (p[1] - q[1])) / d, (sq(p) * (r[0] - q[0]) + sq(q) * (p[0] - r[0]) + sq(r) * (q[0] - p[0])) / d];
    const P = a[end], v = [-(P[1] - C[1]), P[0] - C[0]], l = Math.hypot(v[0], v[1]), s = Math.sign(end === "to" ? v[0] * (P[0] - m[0]) + v[1] * (P[1] - m[1]) : v[0] * (m[0] - P[0]) + v[1] * (m[1] - P[1]));
    return [(s * v[0]) / l, (s * v[1]) / l];
  };
  // Along the cycle at T, clockwise.
  const along = (a: A, end: "from" | "to") => { const w = way(a, end), T = a[end], r = Math.hypot(...T); assert.ok(Math.abs(w[0] - T[1] / r) < 1e-3 && Math.abs(w[1] + T[0] / r) < 1e-3, JSON.stringify({ a, w })); };
  for (const reach of [1.1, -0.8]) {
    const [i, o] = halves(two({ branches: [{ id: 1, step: 0, in: { along: -1.5, reach }, out: { along: 1, reach } }] }));
    assert.ok(i.part === "in" && o.part === "out" && Math.hypot(i.to[0] - 3, i.to[1]) < 1e-6 && Math.hypot(o.from[0] - 3, o.from[1]) < 1e-6);
    // Through E: the end set by along and reach.
    assert.ok(Math.abs(Math.hypot(...i.from) - (3 + reach)) < 1e-6 && Math.abs(Math.hypot(...o.to) - (3 + reach)) < 1e-6);
    along(i, "to");
    along(o, "from");
    for (const part of ["in", "out"] as const) {
      const [one] = halves(two({ branches: [{ id: 1, step: 0, [part]: { reach } }] }));
      along(one, part === "in" ? "to" : "from");
    }
  }
  // Heads: none coming in, a full head going out (on its outer end); set heads go on the path's first and last points.
  const [i, o] = halves(two({ branches: [{ id: 1, step: 0, in: {}, out: {} }] }));
  assert.deepEqual([i.start, i.end, o.start, o.end], [undefined, "none", undefined, undefined]);
  assert.deepEqual([halves(two({ branches: [{ id: 1, step: 0, in: {} }] }))[0].end, halves(two({ branches: [{ id: 1, step: 0, out: {} }] }))[0].end], ["none", undefined]);
  const [si, so] = halves(two({ branches: [{ id: 1, step: 0, in: {}, out: {}, heads: ["left", "none"] }] }));
  assert.deepEqual([si.start, si.end, so.start, so.end], ["left", "none", undefined, "none"]);
  assert.deepEqual((({ start, end }) => [start, end])(halves(two({ branches: [{ id: 1, step: 0, in: {}, heads: ["full", "full"] }] }))[0]), ["full", undefined]);
  // Ends kept to their side: a reagent's end after T and a product's before it come back to a quarter bond length.
  const at = (x: Mol) => halves(x).map((a) => (a.part === "in" ? a.from : a.to));
  assert.deepEqual(at(two({ branches: [{ id: 1, step: 0, in: { along: 1 } }] })), at(two({ branches: [{ id: 1, step: 0, in: { along: -0.25 } }] })));
  assert.deepEqual(at(two({ branches: [{ id: 1, step: 0, out: { along: -1 } }] })), at(two({ branches: [{ id: 1, step: 0, out: { along: 0.25 } }] })));
  // A structure level with T along the arc: its end goes out to 0.15 b from the arc.
  const level = halves(two({ branches: [{ id: 1, step: 0, meet: 0.5, out: { atoms: [2] } }] }, [atom(0, 3), atom(0, -3), atom(3, -2)]))[0];
  assert.ok(Math.abs(level.to[0] - 3.15) < 1e-6 && level.to[1] < 0 && level.to[1] > -2, JSON.stringify(level.to));
  // A structure on the arc at T still has its arrow, at least 0.3 b long.
  for (const [x, y] of [[3, 0], [3.2, 0.1]]) {
    const [on] = halves(two({ branches: [{ id: 1, step: 0, in: { atoms: [2] } }] }, [atom(0, 3), atom(0, -3), atom(x, y)]));
    assert.ok(on && Math.hypot(on.from[0] - on.to[0], on.from[1] - on.to[1]) >= 0.3 - 1e-6, JSON.stringify(on));
  }
  // Two intermediates too close for an arc between them: no arc, but the step is still there for its side arrow and name.
  const close: Mol = { ...two({ nodes: [[0], [2], [1]], at: [top, top - 0.1, bottom], branches: [{ id: 1, step: 0, out: {} }] }, [atom(0, 3), atom(0, -3), atom(3 * Math.cos(top - 0.1), 3 * Math.sin(top - 0.1))]), captions: [{ id: 5, text: "fast", x: 0, y: 0, cycle: { cycle: 1, step: 0, side: "name" } }] };
  const lay = layoutCycles(close, L, 1, ink(close)), span = lay.spans.find((s) => s.step === 0)!;
  assert.ok(span && span.from === span.to);
  assert.equal(lay.arrows.filter((a) => a.step === 0 && a.branch === undefined).length, 0);
  assert.equal(lay.arrows.filter((a) => a.branch === 1).length, 1);
  assert.ok(lay.anchors.has(5));
  // A reversible step: the same arc as a pair, its ratio passed on. Its side arrow meets the half facing its ends.
  const plain = arcs(two({}))[0], pair = arcs(two({ steps: [{ kind: "equilibrium", ratio: 3 }] }))[0];
  assert.deepEqual([pair.kind, pair.point, pair.ratio, pair.from, pair.to, pair.bend], ["equilibrium", true, 3, plain.from, plain.to, plain.bend]);
  assert.equal(arcs(two({ steps: [null, { kind: "equilibrium" }] }))[1].ratio, undefined);
  assert.equal(arcs(two({ steps: [{ hidden: true }] })).filter((a) => a.step === 0).length, 0);
  for (const [reach, x] of [[1.1, 3.11], [-0.8, 2.89]]) {
    const [i, o] = halves(two({ steps: [{ kind: "equilibrium" }], branches: [{ id: 1, step: 0, in: { reach }, out: { reach } }] }));
    assert.ok(Math.hypot(i.to[0] - x, i.to[1]) < 1e-6 && Math.hypot(o.from[0] - x, o.from[1]) < 1e-6, JSON.stringify([i.to, o.from]));
  }
  // Made forward again, a step keeps no ratio; with nothing left, the cycle keeps no steps.
  const toggled = setStep(two({ steps: [{ kind: "equilibrium", ratio: 3 }, { lead: 2 }] }), 1, 0, { kind: undefined });
  assert.deepEqual(toggled.cycles![0].steps, [null, { lead: 2 }]);
  assert.equal(setStep(two({ steps: [{ kind: "equilibrium" }] }), 1, 0, { kind: undefined }).cycles![0].steps, undefined);
  assert.deepEqual(setStep(two({}), 1, 1, { kind: "equilibrium", ratio: 1 }).cycles![0].steps, [null, { kind: "equilibrium" }]);
  assert.equal(setStep(two({}), 1, 5, { kind: "equilibrium" }).cycles![0].steps, undefined);

  // Space: a lead of 12 pt moves only the arc's start, 12 pt round. A lead goes back no further than the gap (into the
  // clear space, never the ink), and lead and trail together leave the arc 0.8 b, shared as they were set.
  const sp = (x: Mol) => layoutCycles(x, L, 1, ink(x)).spans.find((y) => y.step === 0)!, flat = sp(two({})), led = sp(two({ steps: [{ lead: 12 }] })), R = 3 * L;
  assert.ok(Math.abs(led.from - flat.from - 12 / R) < 1e-9 && led.to === flat.to && led.from0 === flat.from);
  assert.ok(Math.abs(sp(two({ steps: [{ lead: -72 }] })).from - (flat.from - 6 / R)) < 1e-9);
  const tight = sp(two({ steps: [{ lead: 200, trail: 100 }] })), room = flat.to - flat.from - (0.8 * L) / R;
  assert.ok(Math.abs(tight.to - tight.from - (0.8 * L) / R) < 1e-9 && Math.abs(tight.from - flat.from - (room * 2) / 3) < 1e-9);
  // The handles set what they are dragged to: whole points, none within the snap; Option on a lead or trail, a ratio.
  const lay2 = layoutCycles(two({}), L, 1, ink(two({}))), cy = two({}).cycles![0], round = (a: number, r = R): [number, number] => [r * Math.cos(a), r * Math.sin(a)];
  const a0 = lay2.spans[0].a0, ang = (x: number) => a0 + x; // clockwise on screen is up in px angle
  assert.deepEqual(stepFor(lay2, cy, 0, "lead", round(ang(flat.from0 + 12.4 / R)), L, 1, 4), { lead: 12 });
  assert.deepEqual(stepFor(lay2, cy, 0, "lead", round(ang(flat.from0 + 3 / R)), L, 1, 4), { lead: undefined });
  assert.deepEqual(stepFor(lay2, cy, 0, "trail", round(ang(flat.to0 - 20 / R)), L, 1, 4), { trail: 20 });
  assert.deepEqual(stepFor(lay2, cy, 0, "lead", round(ang(flat.from0 - 50 / R)), L, 1, 4), { lead: -6 });
  // The bow handle sits 0.35 b inside the arc's middle, so the arc there is free to pull a side arrow from.
  assert.ok(Math.abs(Math.hypot(...lay2.spans[0].bow) * L - (R - 0.35 * L)) < 1e-9);
  assert.deepEqual(stepFor(lay2, cy, 0, "bow", round(ang(1), R + 0.15 * L), L, 1, 6), { bow: 0.5 });
  assert.deepEqual(stepFor(lay2, cy, 0, "bow", round(ang(1), R - 0.35 * L + 5), L, 1, 6), { bow: undefined });
  const half = (flat.to - flat.from) / 2, middle = flat.from + half;
  assert.deepEqual(stepFor(lay2, cy, 0, "trail", round(ang(middle + half / 2)), L, 1, 4, true), { ratio: 0.5 });
  assert.deepEqual(stepFor(lay2, cy, 0, "lead", round(ang(middle - half / 4)), L, 1, 4, true), { ratio: 4 });
  assert.deepEqual(stepFor(lay2, cy, 0, "lead", round(ang(flat.from)), L, 1, 4, true), { ratio: undefined });

  // Bow: 0.5 puts the arc's middle 0.5 b out. A side arrow on a bowed arc meets it on the arc and along it, and its
  // ends read back where they were set. An arc bowed in past straight turns the other way.
  const circle = (p: number[], q: number[], r: number[]) => {
    const d = 2 * (p[0] * (q[1] - r[1]) + q[0] * (r[1] - p[1]) + r[0] * (p[1] - q[1])), sq = (v: number[]) => v[0] ** 2 + v[1] ** 2;
    return [(sq(p) * (q[1] - r[1]) + sq(q) * (r[1] - p[1]) + sq(r) * (p[1] - q[1])) / d, (sq(p) * (r[0] - q[0]) + sq(q) * (p[0] - r[0]) + sq(r) * (q[0] - p[0])) / d];
  };
  const four = (bow: number, br: Cycle["branches"]): Mol => ({ atoms: [atom(0, 3), atom(3, 0), atom(0, -3), atom(-3, 0)], bonds: [], cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1], [2], [3]], at: [top, right, bottom, left], steps: [{ bow }], branches: br }] });
  for (const x of [two({ steps: [{ bow: 0.5 }] }), four(0.5, undefined), four(-1, undefined)]) {
    const bow = x.cycles![0].steps![0]!.bow!;
    for (const reach of [1.1, -0.6]) {
      const br = { id: 1, step: 0, meet: 0.3, in: { along: -1.5, reach }, out: { along: 1.2, reach } }, m2: Mol = { ...x, cycles: [{ ...x.cycles![0], branches: [br] }] };
      const lay = layoutCycles(m2, L, 1, ink(m2)), arc = lay.arrows.find((a) => a.step === 0 && a.branch === undefined)!, [i, o] = lay.arrows.filter((a) => a.branch === 1), C = circle(arc.from, bendPoint(arc), arc.to);
      assert.ok(Math.abs(Math.hypot(...bendPoint(arc)) - (3 + bow)) < 1e-6, JSON.stringify(bendPoint(arc)));
      assert.ok(Math.abs(Math.hypot(i.to[0] - C[0], i.to[1] - C[1]) - Math.hypot(arc.from[0] - C[0], arc.from[1] - C[1])) < 1e-6 && Math.abs(Math.hypot(...i.to) - 3) > 0.05, JSON.stringify([bow, i.to, C]));
      const w = way(i, "to"), w2 = way(o, "from");
      assert.ok(Math.abs(w[0] * (i.to[0] - C[0]) + w[1] * (i.to[1] - C[1])) < 1e-6 && Math.abs(w[0] - w2[0]) < 1e-3 && Math.abs(w[1] - w2[1]) < 1e-3);
      assert.deepEqual(endFor(lay, 1, br, "in", [i.from[0] * L, -i.from[1] * L], L), { along: -1.5, reach });
      assert.deepEqual(endFor(lay, 1, br, "out", [o.to[0] * L, -o.to[1] * L], L), { along: 1.2, reach });
    }
  }
  assert.equal(layoutCycles(four(-1, undefined), L, 1, ink(four(-1, undefined))).spans[0].o, -1);
}
console.log("cycle layout ok");

// One side arrow (Sam, 3 November 2026): pulled out of the arc, it comes in or goes out the way the pointer goes. Its
// ends drag and read back where they were set; one dragged past where the arrow meets the arc turns round, or takes that
// point with it. Where it meets the arc slides on to the next step. Ends come off one at a time and are picked as In,
// Out, or both.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  // Clockwise, top and bottom: step 0 runs down the right-hand side, where the arc's way on is down (px, y down).
  const two = (branches: Cycle["branches"], captions: Mol["captions"] = []): Mol => ({ atoms: [atom(0, 3), atom(0, -3)], bonds: [], captions, cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1]], at: [top, bottom], branches }] });
  const lay = (x: Mol) => layoutCycles(x, L, 1, ink(x)), br = (x: Mol) => x.cycles![0].branches?.[0], px = (q: number[]): [number, number] => [q[0] * L, -q[1] * L];
  const near = (p: number[], q: number[], d = 0.05) => Math.hypot(p[0] - q[0], p[1] - q[1]) < d;
  // 36. Ahead of where it meets the arc is out, behind is in.
  assert.equal(roleFor([90, 0], [0, 1], [100, 20]), "out");
  assert.equal(roleFor([90, 0], [0, 1], [100, -20]), "in");
  // 19. Ends read back where they were set, outside and inside.
  const set2 = two([{ id: 1, step: 0, in: { along: -1.2, reach: 1 }, out: { along: 1, reach: -0.7 } }]), h = lay(set2).branches[0];
  assert.deepEqual(endFor(lay(set2), 1, br(set2)!, "in", px(h.in!), L), { along: -1.2, reach: 1 });
  assert.deepEqual(endFor(lay(set2), 1, br(set2)!, "out", px(h.out!), L), { along: 1, reach: -0.7 });
  // Pulled out of the arc: going down it is a product, going up a reagent; let go near the arc, nothing.
  const bare = two(undefined), out = pullBranch(bare, lay(bare), 1, 0, 0.5, px([3.8, -1.5]), L)!, inn = pullBranch(bare, lay(bare), 1, 0, 0.5, px([3.8, 1.5]), L)!;
  assert.deepEqual([out.part, br(out.m)!.meet, near(lay(out.m).branches[0].out!, [3.8, -1.5]), inn.part, br(inn.m)!.meet], ["out", 0.5, true, "in", 0.5]);
  assert.equal(pullBranch(bare, lay(bare), 1, 0, 0.5, px([3.1, -0.5]), L), undefined);
  // Pulled out next to a one-ended arrow missing that end: its other end.
  const joined = pullBranch(inn.m, lay(inn.m), 1, 0, 0.55, px([3.8, -1.5]), L)!;
  assert.deepEqual([joined.branch, joined.m.cycles![0].branches!.length, !!br(joined.m)!.in, !!br(joined.m)!.out], [br(inn.m)!.id, 1, true, true]);
  // Pulled straight out, where it meets the arc moves back, so the product's swoop turns a quarter of the way round to
  // its end under the pointer, not a hook.
  const straight = pullBranch(bare, lay(bare), 1, 0, 0.5, px([4.5, -0.1]), L)!, sb = lay(straight.m).branches[0], sa = lay(straight.m).arrows.find((a) => a.branch !== undefined)!;
  assert.ok(straight.part === "out" && br(straight.m)!.meet! < 0.4 && Math.abs(br(straight.m)!.out!.along! - br(straight.m)!.out!.reach!) < 0.02 && near(sb.out!, [4.5, -0.1]) && Math.abs(sa.bend!) < 0.25, JSON.stringify([br(straight.m), sa.bend]));
  // 20. A reagent alone dragged past where it meets the arc turns round: a product there, its end under the pointer.
  // Nearer along the arc than out from it, where it meets the arc moves back to keep the swoop to a quarter turn.
  const lone = two([{ id: 1, step: 0, in: {} }]), T0 = lay(lone).branches[0].T, turned = dragEnd(lone, lay(lone), 1, 1, "in", px([4.2, -0.5]), L);
  assert.deepEqual([turned.part, !!br(turned.m)!.in, !!br(turned.m)!.out], ["out", false, true]);
  assert.ok(lay(turned.m).branches[0].T[1] > T0[1] && near(lay(turned.m).branches[0].out!, [4.2, -0.5]));
  const far = dragEnd(lone, lay(lone), 1, 1, "in", px([4.2, -2]), L);
  assert.ok(near(lay(far.m).branches[0].T, T0, 1e-9) && near(lay(far.m).branches[0].out!, [4.2, -2])); // further round, it stays
  assert.equal(lay(turned.m).arrows.find((a) => a.branch === 1)!.end, undefined); // the head goes with it, at the end
  // With a product too, where it meets the arc goes along, ahead of the reagent's end.
  const pair = two([{ id: 1, step: 0, in: {}, out: {} }]), slid = dragEnd(pair, lay(pair), 1, 1, "in", px([3.8, -1]), L);
  const after = lay(slid.m).branches[0];
  assert.ok(slid.part === "in" && br(slid.m)!.in!.along === -0.25 && br(slid.m)!.meet! > 0.5 && after.T[1] < -1 && near(after.in!, [3.8, -1]), JSON.stringify(after));
  // 21. Dragged past an intermediate, a side arrow goes on to the next step, keeping its ends and its text's step.
  const four: Mol = { atoms: [atom(0, 3), atom(3, 0), atom(0, -3), atom(-3, 0)], bonds: [], captions: [{ id: 9, text: "H2", x: 0, y: 0, cycle: { cycle: 1, step: 0, side: "in", branch: 1 } }],
    cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1], [2], [3]], at: [top, right, bottom, left], branches: [{ id: 1, step: 0, in: { along: -1, reach: 1.2 } }] }] };
  const moved = dragMeet(four, lay(four), 1, 1, px([3 * Math.cos(-Math.PI / 4), 3 * Math.sin(-Math.PI / 4)]), L);
  assert.deepEqual([br(moved)!.step, br(moved)!.in, moved.captions![0].cycle!.step], [1, { along: -1, reach: 1.2 }, 1]);
  assert.ok(Math.abs(br(moved)!.meet! - 0.5) < 0.05);
  // Pulled well off the arc, a one-ended arrow gets its other end there.
  const grown = dragMeet(lone, lay(lone), 1, 1, px([4.2, -1.5]), L);
  assert.ok(br(grown)!.in && br(grown)!.out && near(lay(grown).branches[0].T, T0, 1e-9));
  // 22. A pass-through's product taken off: a reagent alone, meeting the arc where it did. The last end takes the arrow.
  const Tp = lay(pair).branches[0].T, half = removeEnd(pair, 1, 1, "out");
  assert.ok(br(half)!.in && !br(half)!.out && near(lay(half).branches[0].T, Tp, 1e-9));
  assert.equal(removeEnd(half, 1, 1, "in").cycles![0].branches, undefined);
  // Its text goes with it.
  const labelled = two([{ id: 1, step: 0, in: {}, out: {} }], [{ id: 9, text: "H2O", x: 0, y: 0, cycle: { cycle: 1, step: 0, side: "out", branch: 1 } }]);
  assert.equal(removeEnd(labelled, 1, 1, "out").captions!.length, 0);
  // 23. An end whose structure is deleted is a bare end (the structure block above). Swapped alone, it meets the arc
  // where it did.
  assert.ok(near(lay(swapBranch(lone, 1, 1)).branches[0].T, T0, 1e-9));
  // 24. Ends: Reagent, then Product, then Reagent and product, is the arrow as it was.
  const shape = (x: Mol) => lay(x).arrows.filter((a) => a.branch !== undefined).map((a) => [a.from, a.to, a.bend, a.start, a.end]);
  const round = setEnds(setEnds(setEnds(pair, 1, 1, "in"), 1, 1, "out"), 1, 1, "both");
  assert.deepEqual(shape(round), shape(pair));
  assert.deepEqual([!!br(setEnds(pair, 1, 1, "in"))!.out, !!br(setEnds(pair, 1, 1, "out"))!.in], [false, false]);
}
console.log("cycle ends ok");

// Dropped on a cycle (dropOnCycle): what moved or is new joins the circle it is on or beside, the nearest one, and the
// drag shows what letting go does. ⌘ held, nothing joins.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] }), polar = (a: number, r = 3): [number, number] => [r * Math.cos(a), r * Math.sin(a)];
  // Clockwise from the top: top, right, bottom, left. Step 0 runs from the top round to the right.
  const four = (nodes: number[][] = [[0], [1], [2], [3]], more: Partial<Cycle> = {}): Mol => ({ atoms: [atom(0, 3), atom(3, 0), atom(0, -3), atom(-3, 0)], bonds: [], captions: [], cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes, at: [top, right, bottom, left], ...more }] });
  const plus = (x: Mol, p: [number, number]): Mol => ({ ...x, atoms: [...x.atoms, atom(...p)] }), to = (x: Mol, i: number, p: [number, number]): Mol => ({ ...x, atoms: x.atoms.map((a, k) => (k === i ? atom(...p) : a)) });
  const drop = (x: Mol, was?: Mol, o = {}) => dropOnCycle(x, fragments(x), was, o), cy = (x: Mol, k = 0) => x.cycles![k];
  // A new atom brought in from well away to p: the drawing before and after.
  const brought = (x: Mol, p: [number, number]): [Mol, Mol] => { const was = plus(x, [20, 20]); return [to(was, x.atoms.length, p), was]; };
  // 35. What a drag shows is what letting go does: dropped again, nothing changes.
  const same = (x: Mol, was: Mol) => { const r = drop(x, was); assert.deepEqual(drop(r, was), r); return r; };
  // 25. On the circle near a break, a structure takes its place; elsewhere on it, it is a node of its own.
  const broken = four([[0], [1], [2], []]), took = same(plus(broken, polar(left + 0.3)), broken);
  assert.deepEqual([cy(took).nodes.length, cy(took).nodes[3]], [4, [4]]);
  assert.ok(Math.abs(Math.cos(cy(took).at[3] - (left + 0.3)) - 1) < 1e-9);
  assert.deepEqual(cy(same(plus(broken, polar(-Math.PI / 4, 3.3)), broken)).nodes, [[0], [1], [4], [2], []]);
  // 26. Text on the circle is a node, measured from its box's middle, and the circle's band is as wide as its scale.
  const text = (x: Mol, p: [number, number]): Mol => ({ ...x, captions: [{ id: 50, text: "Pd", x: p[0], y: p[1] }] }), side = (x: Mol) => x.captions![0].cycle;
  const off = text(four(), polar(Math.PI / 4, 4)), away = text(four(), [20, 20]);
  assert.deepEqual(side(same(off, away)), { cycle: 1, step: 0, side: "out", branch: 1 }); // a product beside the arc
  assert.deepEqual(side(drop({ ...off, cycles: [{ ...cy(off), scale: 2 }] }, away))?.side, "node");
  assert.deepEqual(side(drop(off, away, { box: (c: Caption): Box => [c.x - 0.5, c.y - 1.5, c.x + 0.5, c.y - 0.5] }))?.side, "node");
  // Written there (new), it stays free text; written on the circle, it is an intermediate.
  assert.equal(side(drop(off, four())), undefined);
  assert.equal(side(drop(text(four(), polar(Math.PI / 4)), four()))?.side, "node");
  // A reagent's new text, written from the panel (no place yet), labels its end and stays off the circle.
  const fresh: Mol = { ...four(), captions: [{ id: 50, text: "H2", x: 0, y: 3, cycle: { cycle: 1, step: 0, side: "in", branch: 1 } }], cycles: [{ ...cy(four()), branches: [{ id: 1, step: 0, in: {} }] }] };
  assert.deepEqual([cy(drop(fresh, four())).nodes.length, side(drop(fresh, four()))], [4, { cycle: 1, step: 0, side: "in", branch: 1 }]);
  // A product's text stays about where it was dropped: its end is there, or the quarter bond length on that an end
  // keeps from where its arrow meets the arc.
  const label = same(off, away), E = layoutCycles(label, L, 1, ink(label)).branches[0].out!;
  assert.ok(Math.hypot(E[0] - polar(Math.PI / 4, 4)[0], E[1] - polar(Math.PI / 4, 4)[1]) < 0.35, JSON.stringify(E));
  // 27. Beside a step's arc, a structure on its first half comes in, on its second half goes out.
  const inn = same(...brought(four(), polar((3 * Math.PI) / 8, 4.5))), outt = same(...brought(four(), polar(Math.PI / 8, 4.5)));
  assert.deepEqual([cy(inn).branches![0].step, cy(inn).branches![0].in, cy(inn).branches![0].out], [0, { atoms: [4] }, undefined]);
  assert.deepEqual([cy(outt).branches![0].step, cy(outt).branches![0].out, cy(outt).branches![0].in], [0, { atoms: [4] }, undefined]);
  assert.equal(cy(drop(...brought(four(), polar(Math.PI / 8, 7.5)))).branches, undefined); // too far out
  assert.equal(cy(drop(plus(four(), polar(Math.PI / 8, 4.5)), four())).branches, undefined); // drawn there (new), it stays free
  // Its arrow meets the arc on from it (a reagent) or back from it (a product), so it swoops in along the arc.
  const meet = (x: Mol) => cy(x).branches![0].meet!, g = (a: number) => (top - a - 0.6 / 3) / (Math.PI / 2 - 1.2 / 3); // about: ink and gap at each end
  assert.ok(meet(inn) > g((3 * Math.PI) / 8) + 0.3 && meet(outt) < g(Math.PI / 8) - 0.3, JSON.stringify([meet(inn), meet(outt)]));
  // Moved by exactly one atom's place on to where another was, it still counts as moved.
  const hop: Mol = { ...plus(plus(four(), polar(Math.PI / 8, 7.5)), polar(Math.PI / 8, 8.5)), bonds: [{ atoms: [4, 5], order: 1 }] as Mol["bonds"] };
  assert.equal(cy(drop(to(to(hop, 4, polar(Math.PI / 8, 6.5)), 5, polar(Math.PI / 8, 7.5)), hop)).branches, undefined);
  assert.equal(cy(drop(to(to(hop, 4, polar(Math.PI / 8, 4.5)), 5, polar(Math.PI / 8, 5.5)), to(to(hop, 4, polar(Math.PI / 8, 5.5)), 5, polar(Math.PI / 8, 6.5)))).branches!.length, 1);
  // 28. Near a bare end, it labels that end.
  const bare = four(undefined, { branches: [{ id: 1, step: 0, in: {} }] }), Ein = layoutCycles(bare, L, 1, ink(bare)).branches[0].in!;
  assert.deepEqual(cy(same(...brought(bare, [Ein[0] + 0.2, Ein[1]]))).branches, [{ id: 1, step: 0, in: { atoms: [4] } }]);
  // 29. Beside a side arrow with only a reagent, a product is its other end, not an arrow of its own.
  const one = four(undefined, { branches: [{ id: 1, step: 0, in: { along: -1, reach: 1 } }] }), done = same(...brought(one, polar(Math.PI / 8, 4.5)));
  assert.deepEqual(cy(done).branches, [{ id: 1, step: 0, meet: 0.4, in: { along: -1, reach: 1 }, out: { atoms: [4] } }]);
  // 30. A product's structure put on the circle is an intermediate, and its arrow goes.
  const prod = plus(four(undefined, { branches: [{ id: 1, step: 0, out: { atoms: [4] } }] }), polar(Math.PI / 8, 4.5)), into = same(to(prod, 4, polar(Math.PI / 8)), prod);
  assert.deepEqual([cy(into).nodes, cy(into).branches], [[[0], [4], [1], [2], [3]], undefined]);
  // 31. An intermediate taken well off the circle leaves a break where it was; beside an arc, it is a reagent there.
  const gone = same(to(four(), 1, [9, 0]), four());
  assert.deepEqual([cy(gone).nodes, cy(gone).at[1]], [[[0], [], [2], [3]], right]);
  const beside = same(to(four(), 1, [4.5, -1]), four());
  assert.deepEqual([cy(beside).nodes[1], cy(beside).branches![0].step, cy(beside).branches![0].in], [[], 1, { atoms: [1] }]);
  assert.deepEqual(cy(same(to(four(), 1, [3.8, 0]), four())).nodes, [[0], [1], [2], [3]]); // just off, it stays
  // 32. One moved round past the next goes in where it is now; moved along without passing one, the order stays.
  assert.deepEqual(cy(same(to(four(), 0, polar(-Math.PI / 4)), four())).nodes, [[1], [0], [2], [3]]);
  assert.deepEqual(cy(same(to(four(), 0, polar(top - 0.3)), four())).nodes, [[0], [1], [2], [3]]);
  // 33. Where two circles' bands cross, the nearer circle wins (not the first).
  const pair: Mol = { atoms: [], bonds: [], captions: [], cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [], at: [] }, { id: 2, centre: [6.5, 0], radius: 3, clockwise: true, nodes: [], at: [] }] }, won = same(plus(pair, [3.4, 0]), pair);
  assert.deepEqual([cy(won, 0).nodes, cy(won, 1).nodes], [[], [[0]]]);
  // 34. With ⌘ held, nothing joins.
  const [held, before] = brought(four(), polar(Math.PI / 8, 4.5));
  assert.equal(drop(held, before, { skip: true }), held);
  // Turned or cleaned up beside an arc, a structure stays out; moved there in one piece, it joins.
  const stick: Mol = { ...plus(plus(four(), polar(Math.PI / 8, 4.5)), polar(Math.PI / 8, 5.5)), bonds: [{ atoms: [4, 5], order: 1 }] as Mol["bonds"] };
  assert.equal(cy(drop(to(to(stick, 4, polar(0.5, 4.5)), 5, polar(0.3, 5.5)), stick)).branches, undefined);
  assert.equal(cy(drop({ ...stick, atoms: stick.atoms.map((a, k) => (k > 3 ? atom(a.location[0] + 0.1, a.location[1]) : a)) }, stick)).branches!.length, 1);
  // Nothing moved, nothing changes; atoms drawn on to a reagent are part of it.
  assert.equal(drop(inn, inn), inn);
  const grown: Mol = { ...plus(inn, polar((3 * Math.PI) / 8, 5.5)), bonds: [{ atoms: [4, 5], order: 1 }] as Mol["bonds"] };
  assert.deepEqual(cy(drop(grown, inn)).branches![0].in, { atoms: [4, 5] });
}
console.log("cycle drop ok");

// Select and the Cycle tool on a whole cycle: what a pick of it takes, where a click may break it, and its radius.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const two: Mol = { atoms: [atom(0, 3), atom(0, -3), atom(4.5, 1)], bonds: [], captions: [{ id: 9, text: "Pd", x: -3, y: 0, cycle: { cycle: 1, step: 1, side: "node" } }],
    cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1], []], at: [top, bottom, left], branches: [{ id: 1, step: 0, out: { atoms: [2] } }] }] };
  // A pick of a cycle takes its side arrows' structures as well as its intermediates (bug 31).
  assert.deepEqual(cycleAtoms(two.cycles![0]), [0, 1, 2]);
  // 37. A click on the circle inside an intermediate's ink, or the gap round it, makes no break there; on an arc it can.
  const lay = layoutCycles(two, L, 1, ink(two));
  assert.equal(clearAt(lay, 1, top), false);
  assert.equal(clearAt(lay, 1, top - 0.1), false);
  assert.equal(clearAt(lay, 1, right), true);
  assert.equal(clearAt(lay, 2, right), false);
  // Shift-drag on the circle: a new radius about the same centre, with its intermediates, side arrows' structures and
  // text intermediates moved straight out with it; a break keeps its angle.
  const big = resizeCycle(two, 1, 4);
  assert.equal(big.cycles![0].radius, 4);
  const r = (v: number) => Math.round(v * 1e6) / 1e6, u = Math.hypot(4.5, 1);
  assert.deepEqual(big.atoms.map((a) => a.location.map(r)), [[0, 4, 0], [0, -4, 0], [r(4.5 + 4.5 / u), r(1 + 1 / u), 0]]);
  assert.deepEqual([big.captions![0].x, big.captions![0].y].map(r), [-4, 0]);
  assert.deepEqual(big.cycles![0].at, two.cycles![0].at);
  assert.equal(resizeCycle(two, 1, 3), two);
}
console.log("cycle select ok");

// Edge cases: a structure level with where its arrow meets the arc, an unbalanced reversible step, a step split or
// joined, the most side arrows a cycle has, a flip, and a structure inside.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] }), lay = (x: Mol) => layoutCycles(x, L, 1, ink(x));
  const two = (more: Partial<Cycle> = {}, atoms = [atom(5, 0)]): Mol => ({ atoms: [atom(0, 3), atom(0, -3), ...atoms], bonds: [], captions: [], cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1]], at: [top, bottom], ...more }] });
  // Level with T, or a little the wrong side of it, a structure's arrow is a half circle round the right way, never
  // straight (bend 0) or the wrong way round.
  for (const [y, part] of [[0, "out"], [0.01, "out"], [-0.01, "in"], [0, "in"]] as const) {
    const x = two({ branches: [{ id: 1, step: 0, meet: 0.5, [part]: { atoms: [2] } }] }, [atom(5, y)]), a = lay(x).arrows.find((b) => b.branch === 1)!;
    assert.ok(Math.abs(Math.abs(a.bend!) - 0.5) < 0.01, JSON.stringify([y, part, a.bend]));
    // The half circle leaves T the way the arc runs (down the right-hand side) for a product, so it bulges below T; a
    // reagent's comes in that way, from above.
    const mid = bendPoint(a), T = part === "out" ? a.from : a.to;
    assert.ok(part === "out" ? mid[1] < T[1] : mid[1] > T[1], JSON.stringify([y, part, mid, T]));
  }
  // On an unbalanced reversible step, a side arrow facing the shorter half meets it where it is drawn.
  const Tq = (ratio: number, meet: number) => lay(two({ steps: [{ kind: "equilibrium", ratio }], branches: [{ id: 1, step: 0, meet, out: {} }] }, [])).branches[0].T;
  const Te = (meet: number) => lay(two({ steps: [{ kind: "equilibrium" }], branches: [{ id: 1, step: 0, meet, out: {} }] }, [])).branches[0].T;
  const short = [3, 1 / 3].find((r) => Math.hypot(Tq(r, 0.9)[0] - Te(0.9)[0], Tq(r, 0.9)[1] - Te(0.9)[1]) > 0.1)!;
  assert.ok(short && Math.hypot(Tq(short, 0.9)[0] - Te((1 + 1 / 3) / 2)[0], Tq(short, 0.9)[1] - Te((1 + 1 / 3) / 2)[1]) < 1e-9 && Math.hypot(Tq(short, 0.5)[0] - Te(0.5)[0], Tq(short, 0.5)[1] - Te(0.5)[1]) < 1e-9);
  // A break added or taken away, laid out, leaves a side arrow and a name where they were along the arc as drawn.
  const big: Mol = { atoms: [atom(-1, 3), atom(0, 3), atom(1, 3), atom(-1, -3), atom(0, -3), atom(1, -3)], bonds: [], captions: [{ id: 9, text: "x", x: 0, y: 0, cycle: { cycle: 1, step: 0, side: "name", at: 0.3, reach: 0.6 } }],
    cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0, 1, 2], [3, 4, 5]], at: [top, bottom], branches: [{ id: 1, step: 0, meet: 0.8, out: {} }] }] };
  const named = (x: Mol) => layoutCycles(x, L, 1, ink(x)).anchors.get(9)!, split = addStop(big, 1, -0.3, [], lay), back = removeStop(split, 1, 1, lay);
  for (const x of [split, back]) {
    assert.ok(Math.hypot(lay(x).branches[0].T[0] - lay(big).branches[0].T[0], lay(x).branches[0].T[1] - lay(big).branches[0].T[1]) < 1e-9);
    assert.ok(Math.hypot(named(x).x - named(big).x, named(x).y - named(big).y) < 1e-6);
  }
  assert.equal(split.cycles![0].branches![0].step, 1);
  // The most side arrows a cycle has is 64 (what the readers take); an end goes no further than 50 bond lengths.
  let many = two({}, []);
  for (let k = 0; k < 64; k++) many = addBranch(many, 1, 0)[0];
  assert.deepEqual([many.cycles![0].branches!.length, addBranch(many, 1, 0)[1], pullBranch(many, lay(many), 1, 1, 0.5, [8 * L, 1 * L], L)], [64, undefined, undefined]);
  const wide = two({ radius: 30, scale: 0.5, nodes: [], at: [] }, []), wb = { id: 1, step: 0, out: {} };
  assert.deepEqual(endFor(lay(wide), 1, wb, "out", [-0.3 * L, -60 * L], L, 0.5)!.along, 50);
  // Flipped, a cycle's side arrows swap their half heads.
  const halves = two({ branches: [{ id: 1, step: 0, out: {}, heads: ["left", "right"] }] }, []), flipped = transformParts(halves, new Set(), new Set([1]), (q) => [-q[0], q[1]], [1, 1], undefined, 1, "across");
  assert.deepEqual(flipped.cycles![0].branches![0].heads, ["right", "left"]);
  // A structure inside the circle counts as inside for where a step's name goes: outside, then.
  const inner = { ...two({ branches: [{ id: 1, step: 0, out: { atoms: [2] } }] }, [atom(1.5, -0.5)]), captions: [{ id: 9, text: "x", x: 0, y: 0, cycle: { cycle: 1, step: 0, side: "name" as const } }] };
  assert.ok(named(inner).x > 3 * L, JSON.stringify(named(inner)));
}
console.log("cycle edges ok");

// Delete takes exactly what is picked. A whole cycle picked (a click on it, ⌘A, a lasso round it) is its intermediates,
// its side arrows' structures and all its text: Delete or Cut takes all of it, and Paste brings it back once. The cycle
// alone deleted (Remove the cycle, its last arc erased) leaves its structures, and its labels as free text where and as
// they are drawn.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const whole: Mol = { atoms: [atom(0, 3), atom(0, -3), atom(4.5, 1)], bonds: [],
    captions: [{ id: 7, text: "CO", x: 0, y: 0, cycle: { cycle: 1, step: 0, side: "in", branch: 2 } }, { id: 8, text: "Pd", x: -3, y: 0, cycle: { cycle: 1, step: 2, side: "node" } }, { id: 9, text: "cat.", x: 0, y: 0, cycle: { cycle: 1, step: 0, side: "centre" } }],
    cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1], []], at: [top, bottom, left], branches: [{ id: 1, step: 0, out: { atoms: [2] } }, { id: 2, step: 1, in: {} }] }] };
  const c = whole.cycles![0], atoms = new Set(cycleAtoms(c)), items = new Set([c.id, ...whole.captions!.map((t) => t.id)]);
  const gone = deleteGraphics(deleteAtoms(whole, atoms), items);
  assert.deepEqual([gone.atoms.length, gone.captions!.length, gone.cycles!.length], [0, 0, 0]);
  // Cut (what Copy takes, then deleted), then Paste: one cycle with all of it, as it was.
  const clip = extractSelection(whole, atoms, items), cut = deleteGraphics(deleteAtoms(whole, atoms), new Set([...items, ...clip.captions!.map((t) => t.id)]));
  const back = insertMol(cut, clip).mol;
  assert.deepEqual([back.atoms.length, back.captions!.length, back.cycles!.length], [3, 3, 1]);
  assert.deepEqual(back.cycles![0].branches, c.branches);
  assert.ok(back.captions!.every((t) => t.cycle?.cycle === back.cycles![0].id));
  // An intermediate taken out of the pick: Copy and Cut take the cycle with a break there, as Delete leaves it.
  const part = extractSelection(whole, new Set([0, 2]), items);
  assert.deepEqual(part.cycles![0].nodes, [[0], [], []]);
  assert.ok(Math.abs(Math.sin(part.cycles![0].at[1]) + 1) < 1e-9);
  assert.equal(part.captions!.length, 3);
  // The cycle alone: its structures stay, and its labels stay where and as they are drawn, as free text.
  const drawn = (t: Caption): [number, number] | undefined => (t.id === 7 ? [1.5, 2] : t.id === 9 ? [0, 0.2] : undefined);
  const lined = (t: Caption): Caption["align"] => (t.id === 7 ? "right" : t.id === 9 ? "centre" : undefined);
  const free = deleteGraphics(whole, new Set([1]), drawn, lined);
  assert.equal(free.atoms.length, 3);
  assert.deepEqual(free.captions!.map((t) => [t.text, t.x, t.y, t.align, t.cycle]), [["CO", 1.5, 2, "right", undefined], ["Pd", -3, 0, undefined, undefined], ["cat.", 0, 0.2, "centre", undefined]]);
  // A label copied (or cut, or Option-dragged) on its own comes as free text where and as it is drawn.
  assert.deepEqual(extractSelection(whole, new Set(), new Set([9]), drawn, lined).captions!.map((t) => [t.text, t.x, t.y, t.align]), [["cat.", 0, 0.2, "centre"]]);
  // Only a step or a side arrow picked (the cycle with none of its structures or text): Cut takes that alone, as Delete
  // does, and Copy has nothing to copy.
  const editor = readFileSync(new URL("./Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /if \(partPick\) return Promise\.resolve\(false\);/);
  assert.match(editor, /if \(partPick\) return run\("edit\.delete"\);/);
}
console.log("cycle delete ok");

// Placed where the pointer aims (a template or ring stamped, a file dropped, a structure named at the pointer), a new
// structure joins a cycle as one dragged there does: beside an arc, a reagent or product. ⌘ (skip) keeps it free, and
// one added any other way (drawn, pasted) only joins a circle it is on.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const four: Mol = { atoms: [atom(0, 3), atom(3, 0), atom(0, -3), atom(-3, 0)], bonds: [], captions: [], cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1], [2], [3]], at: [top, right, bottom, left] }] };
  const p: [number, number] = [4.5 * Math.cos(Math.PI / 8), 4.5 * Math.sin(Math.PI / 8)], stamped: Mol = { ...four, atoms: [...four.atoms, atom(...p)] };
  const drop = (o = {}) => dropOnCycle(stamped, fragments(stamped), four, o).cycles![0];
  assert.deepEqual(drop({ placed: true }).branches, [{ id: 1, step: 0, meet: drop({ placed: true }).branches![0].meet, out: { atoms: [4] } }]);
  assert.equal(drop().branches, undefined);
  assert.equal(drop({ placed: true, skip: true }).branches, undefined);
  // On the circle it is an intermediate, as before.
  const on: Mol = { ...four, atoms: [...four.atoms, atom(3 * Math.cos(Math.PI / 4), 3 * Math.sin(Math.PI / 4))] };
  assert.equal(dropOnCycle(on, fragments(on), four, { placed: true }).cycles![0].nodes.length, 5);
  // Inside the circle, placed within half the radius of an arc it joins; nearer the middle it stays free (a catalyst).
  const inside = (r: number) => { const x: Mol = { ...four, atoms: [...four.atoms, atom(r * Math.cos(Math.PI / 8), r * Math.sin(Math.PI / 8))] }; return dropOnCycle(x, fragments(x), four, { placed: true }).cycles![0].branches?.length ?? 0; };
  assert.deepEqual([inside(2), inside(1.2)], [1, 0]);
}
console.log("cycle placed ok");

// Tidy the cycle: a side arrow's structure goes with the middle of its step's arc.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const two: Mol = { atoms: [atom(0, 3), atom(0, -3), atom(4.5, 0)], bonds: [], cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1]], at: [top, bottom], branches: [{ id: 1, step: 0, out: { atoms: [2] } }] }] };
  const moved = followArcs(two, two.cycles![0], [top, bottom], 4).atoms;
  assert.ok(Math.hypot(moved[2].location[0] - 5.5, moved[2].location[1]) < 1e-9, JSON.stringify(moved[2]));
  assert.deepEqual(moved[0].location, [0, 3, 0]);
}
console.log("cycle tidy ok");

// The Side arrow tool. A click on a step asks Reagent, Product or Reagent and product, the likely one first: the end a
// one-ended side arrow on the step is missing, else a reagent on the step's first half and a product on its second.
{
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const four = (more: Partial<Cycle> = {}): Mol => ({ atoms: [atom(0, 3), atom(3, 0), atom(0, -3), atom(-3, 0)], bonds: [], captions: [], cycles: [{ id: 1, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], [1], [2], [3]], at: [top, right, bottom, left], ...more }] });
  const cy = (x: Mol) => x.cycles![0];
  assert.deepEqual(sideChoices(cy(four()), 0, 0.2), ["in", "out", "both"]);
  assert.deepEqual(sideChoices(cy(four()), 0, 0.7), ["out", "in", "both"]);
  assert.deepEqual(sideChoices(cy(four({ branches: [{ id: 1, step: 0, in: {} }] })), 0, 0.2), ["out", "in", "both"]);
  assert.deepEqual(sideChoices(cy(four({ branches: [{ id: 1, step: 0, in: {}, out: {} }] })), 0, 0.2), ["in", "out", "both"]);
  assert.deepEqual(sideChoices(cy(four({ branches: [{ id: 1, step: 1, out: {} }] })), 0, 0.7), ["out", "in", "both"]); // another step's
  // A new side arrow meets the step where the click was (kept off its ends); one missing the end chosen gets it.
  const [a, b1] = addSide(four(), 1, 0, 0.3, "in");
  assert.deepEqual([cy(a).branches, b1], [[{ id: 1, step: 0, meet: 0.3, in: {} }], 1]);
  assert.deepEqual(addSide(four(), 1, 2, 0.98, "both")[0].cycles![0].branches, [{ id: 1, step: 2, meet: 0.85, in: {}, out: {} }]);
  const [b, b2] = addSide(a, 1, 0, 0.8, "out");
  assert.deepEqual([cy(b).branches, b2], [[{ id: 1, step: 0, meet: 0.3, in: {}, out: {} }], 1]);
  assert.equal(addSide(b, 1, 0, 0.8, "out")[0].cycles![0].branches!.length, 2);
  const many = four({ branches: Array.from({ length: 64 }, (_, i) => ({ id: i + 1, step: 1, in: {}, out: {} })) });
  assert.deepEqual(addSide(many, 1, 0, 0.5, "in"), [many, undefined]);
  // A step the cycle no longer has (the menu was open over an Undo): nothing goes on, so the file stays readable.
  assert.deepEqual(addSide(four(), 1, 4, 0.5, "in"), [four(), undefined]);
  // It is drawn as a side arrow, and saved and read back (.oct and CDXML).
  assert.ok(layoutCycles(b, L, 1, ink(b)).arrows.some((x) => x.branch === 1 && x.part === "out"));
  assert.deepEqual(readOct(writeOct(b, DEFAULT_STYLE)).mol.cycles![0].branches, cy(b).branches);
  assert.deepEqual(fromCdxml(toCdxml(b, DEFAULT_STYLE)).mol.cycles![0].branches, cy(b).branches);
  // A click on a structure beside a step: it is the step's reagent (first half) or product (second half). Far away, or
  // a click on free text there, likewise.
  const near = (r: number, ang: number): Mol => ({ ...four(), atoms: [...four().atoms, atom(r * Math.cos(ang), r * Math.sin(ang))] });
  assert.deepEqual(cy(attachBeside(near(4.5, (3 * Math.PI) / 8), { atoms: [4] })).branches?.map((x) => [x.step, x.in, x.out]), [[0, { atoms: [4] }, undefined]]);
  assert.deepEqual(cy(attachBeside(near(4.5, Math.PI / 8), { atoms: [4] })).branches?.map((x) => [x.step, x.in, x.out]), [[0, undefined, { atoms: [4] }]]);
  assert.equal(cy(attachBeside(near(12, Math.PI / 8), { atoms: [4] })).branches, undefined);
  // Inside the circle: within half the radius of the arc it goes on; a catalyst in the middle stays free.
  assert.deepEqual([cy(attachBeside(near(2, Math.PI / 8), { atoms: [4] })).branches?.length, cy(attachBeside(near(1, Math.PI / 8), { atoms: [4] })).branches], [1, undefined]);
  const said: Mol = { ...four(), captions: [{ id: 50, text: "H2", x: 4 * Math.cos(Math.PI / 8), y: 4 * Math.sin(Math.PI / 8) }] };
  assert.deepEqual(attachBeside(said, { text: 50 }).captions![0].cycle, { cycle: 1, step: 0, side: "out", branch: 1 });
}
console.log("cycle side arrow tool ok");

// Step names placed clear (the Suzuki cycle from the MCP test): three intermediates, side arrows with text on every
// step and long names, so the names go inside where they fit, else outside. No name overlaps another, the centre
// label, a side arrow or its text or an intermediate, and none crosses the circle. Text is half an em per character, as Arial is near enough.
{
  const pt = L / 14.4, wide = (t: string, c: Caption) => t.length * 0.5 * (c.size ?? 10) * pt, d = { ink: [], scale: L };
  const atom = (x: number, y: number) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
  const at = (a: number, r = 4): [number, number] => [r * Math.cos(a), r * Math.sin(a)], [rx, ry] = at(-Math.PI / 6), [lx, ly] = at((-5 * Math.PI) / 6);
  // Pd at the top; Ph–Pd–Br lower right; Ph–Pd–Ph lower left, its right ring reaching towards the bottom.
  const atoms = [atom(0, 4), atom(rx - 1.5, ry - 0.9), atom(rx + 1.5, ry + 0.9), atom(lx - 2.8, ly - 0.9), atom(lx + 2.8, ly + 0.9)];
  const cap = (id: number, text: string, step: number, side: CycleText["side"], branch?: number): Caption => ({ id, text, x: 0, y: 0, cycle: { cycle: 1, step, side, ...(branch ? { branch } : {}) } });
  const suzuki: Mol = { atoms, bonds: [], cycles: [{ id: 1, centre: [0, 0], radius: 4, clockwise: true, nodes: [[0], [1, 2], [3, 4]], branches: [{ id: 1, step: 0, in: {} }, { id: 2, step: 1, in: {}, out: {} }, { id: 3, step: 2, out: {} }] }],
    captions: [cap(10, "Pd(PPh3)4", 0, "centre"), cap(11, "PhBr", 0, "in", 1), cap(12, "PhB(OH)2, base", 1, "in", 2), cap(13, "BrB(OH)2", 1, "out", 2), cap(14, "Ph–Ph", 2, "out", 3),
      cap(20, "oxidative addition", 0, "name"), cap(21, "transmetalation", 1, "name"), cap(22, "reductive elimination", 2, "name")] };
  const frame = (id: number, anchor: "start" | "middle" | "end", wrap?: number) => placeCaptions({ ...suzuki, captions: suzuki.captions!.filter((c) => c.id === id) }, d, wide, [], pt, 10, new Map([[id, { x: 0, y: 0, anchor, wrap }]]), wide)[0]?.box;
  const lay = layoutCycles(suzuki, L, pt, ink(suzuki), () => undefined, frame), drawn = placeCaptions(suzuki, d, wide, [], pt, 10, lay.anchors, wide);
  const swoops = lay.arrows.filter((a) => a.branch !== undefined).flatMap((a) => arrowPath(a, L)), box = (id: number) => drawn.find((p) => p.id === id)!.box, meet = (p: Box, q: Box) => p[0] < q[2] && q[0] < p[2] && p[1] < q[3] && q[1] < p[3];
  const others: [string, Box][] = [...[10, 11, 12, 13, 14].map((id): [string, Box] => [`text ${id}`, box(id)]), ...suzuki.cycles![0].nodes.map((n, j): [string, Box] => [`node ${j}`, ink(suzuki)(n)!])];
  for (const id of [20, 21, 22]) {
    const b = box(id);
    for (const [what, o] of [...others, ...[20, 21, 22].filter((x) => x !== id).map((x): [string, Box] => [`name ${x}`, box(x)])]) assert.ok(!meet(b, o), `name ${id} meets ${what}: ${JSON.stringify([b, o])}`);
    const far = Math.max(...[[b[0], b[1]], [b[2], b[1]], [b[0], b[3]], [b[2], b[3]]].map(([x, y]) => Math.hypot(x, y))), near = Math.hypot(Math.max(b[0], 0, -b[2]), Math.max(b[1], 0, -b[3]));
    assert.ok(far < 4 * L || near > 4 * L, `name ${id} crosses the circle`);
    assert.ok(!swoops.some(([x, y]) => x > b[0] && x < b[2] && y > b[1] && y < b[3]), `name ${id} crosses a side arrow`);
  }
  // A name dragged into place keeps it; one with no frame to measure by keeps the place it always had.
  const moved = { ...suzuki, captions: suzuki.captions!.map((c) => (c.id === 20 ? { ...c, cycle: { ...c.cycle!, at: 0.5, reach: -0.6 } } : c)) };
  assert.deepEqual(layoutCycles(moved, L, pt, ink(moved), () => undefined, frame).anchors.get(20), layoutCycles(suzuki, L, pt, ink(suzuki)).anchors.get(20));
}
console.log("cycle step names ok");
