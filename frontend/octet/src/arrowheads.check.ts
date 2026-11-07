// Run: node src/arrowheads.check.ts. Every arrow kind with a head offers the same head options as a reaction arrow
// where they make sense (its heads at the start and end, their shape and size), and keeps them in .oct, CDXML and
// what is drawn. A catalytic cycle's arrows take a shape and size for all of them.
import assert from "node:assert/strict";
import { ALL_ARROW_KINDS, arrowKind, arrowPicks, HEAD_SHAPES, headMenu, arrowShapes, headSize, headsOf, shapesHeads, sizedHead, takesHeads, type Arrow, type ArrowKind, type Mol } from "./render.ts";
import { layoutCycles, type Cycle } from "./cycle.ts";
import { parse, serialize } from "./file.ts";
import { readFileSync } from "node:fs";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";

const pt = 1, S = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };

// Which kinds take which options. Heads at either end: every kind drawn as one shaft (no-go, hash and dipole too).
// Head shape: those, and an equilibrium's half heads. A retrosynthetic arrow's head is angled and a block arrow's is its
// outline by their kind; orbitals and fragmentation cuts have none.
const want: Record<ArrowKind, [boolean, boolean]> = {
  reaction: [true, true], resonance: [true, true], nogo: [true, true], hash: [true, true], dipole: [true, true], curved: [true, true], fishhook: [true, true], double: [true, true],
  line: [true, true], arc: [true, true], curve: [true, true], equilibrium: [false, true], retro: [false, false], block: [false, false], orbital: [false, false], cut: [false, false],
};
for (const kind of ALL_ARROW_KINDS) assert.deepEqual([takesHeads({ kind }), shapesHeads({ kind })], want[kind], kind);
console.log("arrowheads.check: kinds ok");

// Drawn: a no-go, hash or dipole arrow draws a head at its start when given one, and its heads' shape; an
// equilibrium's half heads take a shape too.
const A = (kind: ArrowKind, more: Partial<Arrow> = {}): Arrow => ({ id: 1, kind, from: [0, 0], to: [3, 0], ...more });
const k = S.bond, draw = (a: Arrow) => JSON.stringify(arrowShapes(a, S, k));
for (const kind of ["nogo", "hash", "dipole"] as const) {
  assert.ok(arrowShapes(A(kind, { start: "full" }), S, k).length > arrowShapes(A(kind), S, k).length, `${kind}: a head at the start`);
  assert.notEqual(draw(A(kind, { head: "hollow" })), draw(A(kind)), `${kind}: a hollow head`);
  assert.notEqual(draw(A(kind, { head: "angled" })), draw(A(kind)), `${kind}: an angled head`);
  assert.deepEqual(headsOf(A(kind, { end: "left" })), { start: "none", end: "left" }, `${kind}: a half head`);
}
for (const head of ["hollow", "angled"] as const) assert.notEqual(draw(A("equilibrium", { head })), draw(A("equilibrium")), `equilibrium: ${head} heads`);
// An angled head's barb is a bar from the tip; a hollow one adds its back.
assert.ok(arrowShapes(A("equilibrium", { head: "hollow" }), S, k).length > arrowShapes(A("equilibrium", { head: "angled" }), S, k).length);
console.log("arrowheads.check: drawn ok");

// A cycle's head shape and size reach every arrow drawn from it: its arcs (a reversible step's pair too) and side
// arrows. Small, the default, leaves each kind's own size.
const cycle: Cycle = { id: 50, centre: [0, 0], radius: 3, clockwise: true, nodes: [[], [], []], at: [Math.PI / 2, -Math.PI / 6, (7 * Math.PI) / 6],
  steps: [{ kind: "equilibrium" }, null, null], branches: [{ id: 1, step: 1, in: {}, out: {} }] };
const laid = (c: Cycle) => layoutCycles({ atoms: [], bonds: [], cycles: [c] }, 30, 1, () => undefined).arrows;
const plain = laid(cycle);
assert.ok(plain.length >= 5 && plain.every((a) => a.head === undefined && a.headSize === undefined), "unset: solid, each kind's own size");
const shaped = laid({ ...cycle, head: "angled", arrowSize: "large" });
assert.ok(shaped.some((a) => a.kind === "equilibrium") && shaped.some((a) => a.branch !== undefined), "arcs, a pair and side arrows");
for (const a of shaped) {
  assert.equal(a.head, "angled", `${a.kind}: shape`);
  assert.deepEqual(headSize(a), sizedHead(a, "large"), `${a.kind}: size`);
}
assert.equal(headSize(laid({ ...cycle, arrowSize: "medium" }).find((a) => a.kind === "curved")!).length, 15);
console.log("arrowheads.check: cycles ok");

// Saved: .oct and CDXML keep every arrow's heads and shape, and a cycle's. An equilibrium with hollow heads stays an
// equilibrium in CDXML (ChemDraw's block arrow is also hollow with a shaft spacing).
const drawing: Mol = {
  atoms: [], bonds: [],
  arrows: [
    A("nogo", { id: 1, start: "full", head: "hollow" }), A("hash", { id: 2, from: [0, 2], to: [3, 2], end: "right", head: "angled" }), A("dipole", { id: 3, from: [0, 4], to: [3, 4], start: "left", head: "hollow" }),
    A("equilibrium", { id: 4, from: [0, 6], to: [3, 6], head: "hollow" }), A("equilibrium", { id: 5, from: [0, 8], to: [3, 8], head: "angled" }),
    A("reaction", { id: 6, from: [0, 10], to: [3, 10], head: "angled", start: "left" }),
  ],
  cycles: [{ ...cycle, id: 60, centre: [10, 0], head: "hollow", arrowSize: "medium" }],
};
const keep = (m: Mol) => ({ arrows: m.arrows!.map((a) => [a.kind, headsOf(a), a.head]), cycles: m.cycles!.map((c) => [c.head, c.arrowSize]) });
assert.deepEqual(keep(parse(serialize(drawing))), keep(drawing), ".oct");
const derived = layoutCycles(drawing, 30, 1, () => undefined).arrows;
const xml = toCdxml(drawing, DEFAULT_STYLE, { derived }), back = fromCdxml(xml).mol;
assert.deepEqual(keep(back), keep(drawing), "CDXML");
// ChemDraw sees the heads as drawn: an equilibrium's ArrowheadType, and a cycle's arrows' type and size.
assert.ok(/ArrowheadHead="HalfLeft"[^>]*ArrowheadTail="HalfLeft"[^>]*ArrowheadType="Hollow"/.test(xml), "an equilibrium's hollow heads");
const cycleArrows = [...xml.matchAll(/<arrow\n[^>]*/g)].map((x) => x[0]).filter((x) => x.includes("&quot;cycle&quot;"));
assert.ok(cycleArrows.length === derived.length && cycleArrows.every((x) => x.includes('ArrowheadType="Hollow"')), "the cycle's arrows are hollow");
assert.ok(cycleArrows.some((x) => x.includes('HeadSize="1500"')), "and medium");
// ChemDraw's own file (no Octet data) reads the same: the kind from the heads and spacing, then the heads.
const plainXml = toCdxml({ ...drawing, cycles: undefined }, DEFAULT_STYLE).replace(/ Octet="[^"]*"/g, "");
assert.deepEqual(keep({ ...fromCdxml(plainXml).mol, cycles: [] }).arrows, keep(drawing).arrows, "ChemDraw's CDXML");
// A damaged cycle head is left out, not trusted.
const bad = JSON.parse(serialize(drawing));
bad.cycles[0].head = "<script>";
bad.cycles[0].arrowSize = 9;
assert.deepEqual([parse(JSON.stringify(bad)).cycles![0].head, parse(JSON.stringify(bad)).cycles![0].arrowSize], [undefined, undefined]);
console.log("arrowheads.check: saved ok");

// Curves > Solid, Hollow and Angled Arrowhead (ChemDraw's arrow menu has them; Octet's Curves menu has them too, after
// the half heads): on for arrows whose heads take a shape and for catalytic cycles (and a cycle's side-arrow text),
// with the selection's shape ticked; off for anything else.
assert.deepEqual(HEAD_SHAPES, ["solid", "hollow", "angled"]);
assert.deepEqual(headMenu({ kind: "arrow", shaped: true, head: "hollow" }), { head: "hollow" });
assert.deepEqual(headMenu({ kind: "arrow", shaped: false, head: "solid" }), {}, "a retrosynthetic or block arrow, an orbital, a cut");
// A line or arrow with no head at either end has no shape to choose: off, as the Actions panel has no Heads then. An
// equilibrium's heads come with its kind, so it always has them.
assert.deepEqual(headMenu({ kind: "arrow", shaped: true, heads: true, start: "none", end: "none", head: "solid" }), {}, "no heads: off");
assert.deepEqual(headMenu({ kind: "arrow", shaped: true, heads: true, start: "none", end: "full", head: "angled" }), { head: "angled" }, "a head at the end: on");
assert.deepEqual(headMenu({ kind: "arrow", shaped: true, heads: true, start: "left", end: "none", head: "solid" }), { head: "solid" }, "a half head at the start: on");
assert.deepEqual(headMenu({ kind: "arrow", shaped: true, heads: false, start: "none", end: "none", head: "hollow" }), { head: "hollow" }, "an equilibrium: on");
const actionsTsx = readFileSync(new URL("Actions.tsx", import.meta.url), "utf8"), renderTs = readFileSync(new URL("render.ts", import.meta.url), "utf8");
assert.match(renderTs, /if \(headShaped\(c\)\) picks\.push\(\{ label: "Heads"/, "the panel and the Curves menu ask the same question");
// One name for each shape everywhere, ChemDraw's: Solid, Hollow and Angled (the Curves menu adds "Arrowhead").
assert.match(renderTs, /\[\["solid", "Solid"\], \["hollow", "Hollow"\], \["angled", "Angled"\]\]/);
const { RELEASES } = await import("./releases.ts");
for (const r of RELEASES) for (const sec of r.sections) for (const item of sec.items) assert.doesNotMatch(item, /open heads?\b/i, `${r.version}: "angled", not "open"`);
assert.deepEqual(headMenu({ kind: "cycle", head: "angled" }), { head: "angled", cycle: true });
assert.deepEqual(headMenu({ kind: "caption", cycleSide: { head: "solid" } }), { head: "solid", cycle: true });
for (const c of [undefined, { kind: "caption" }, { kind: "shape" }, { kind: "empty" }, { kind: "atom" }]) assert.deepEqual(headMenu(c), {});
const mainRs = readFileSync(new URL("../src-tauri/src/main.rs", import.meta.url), "utf8");
assert.match(mainRs, /\[\("solid", "Solid Arrowhead"\), \("hollow", "Hollow Arrowhead"\), \("angled", "Angled Arrowhead"\)\][^;]*check\(&format!\("curves_head_\{id\}"\), name, ""\)\.and_then\(\|c\| c\.set_enabled\(false\)/, "tickable, and off until the page says");
assert.match(mainRs, /&item\("curves_end_right", "Half Arrowhead at End, Right", ""\)\?,\n\s+&sep\(\)\?,\n\s+&heads\[0\],\n\s+&heads\[1\],\n\s+&heads\[2\],\n\s+&sep\(\)\?,\n\s+&item\("curves_closed"/, "after the half heads, before Closed");
assert.match(mainRs, /checks\.extend\(heads\.iter\(\)\.cloned\(\)\);/, "the page can tick them");
assert.match(mainRs, /fn set_check\(checks: State<'_, Checks>, id: String, checked: bool, enabled: Option<bool>\)/);
assert.match(mainRs, /let _ = c\.set_enabled\(on\.unwrap_or\(true\)\);/, "a rebuilt menu keeps them on or off");
const editorTsx = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
assert.match(editorTsx, /HEAD_SHAPES\.map\(\(h\) => \[`curves_head_\$\{h\}`, \(\) => \{ const m = headMenu\(contextOf\(\)\); if \(m\.head\) runAction\(`\$\{m\.cycle \? "cycle" : "arrow"\}\.head\.\$\{h\}`\); \}\]\)/);
assert.match(editorTsx, /invoke\("set_check", \{ id: `curves_head_\$\{h\}`, checked: heads\.head === h, enabled: !!heads\.head \}\)/);
assert.match(editorTsx, /const heads = headMenu\(panelContext\);/);
console.log("arrowheads.check: Curves menu ok");
// Right-click an arrow, a catalytic cycle or its side arrow's text: the menu offers the Actions panel's picks (ChemDraw's
// arrow menu has the line, the heads at each end, the fill and the kind), from the same lists (arrowPicks, arrowKind).
const arrow = { kind: "arrow", arrow: "reaction", ratio: 1, heads: true, shaped: true, curved: false, fillable: false, size: "small", style: "plain", start: "none", end: "full", head: "hollow", fill: "none" };
const labels = (c: unknown) => arrowPicks(c as { kind: string }).map((g) => [g.label, g.picks.map((p) => p.label)]);
assert.deepEqual(labels(arrow), [["Line and arrowheads", ["Line", "Start", "End", "Heads", "Size"]]]);
const picks = arrowPicks(arrow).flatMap((g) => g.picks), pick = (l: string) => picks.find((p) => p.label === l)!;
assert.deepEqual([pick("Line").value, pick("Start").value, pick("End").value, pick("Heads").value, pick("Size").value], ["plain", "none", "full", "hollow", "small"], "the arrow's own, ticked");
assert.deepEqual(pick("Line").options.map(([id]) => id), ["plain", "dashed", "bold", "doubled", "wavy"]);
assert.deepEqual(pick("End").options.map(([id]) => id), ["none", "full", "left", "right"], "half heads too");
assert.deepEqual(pick("Heads").options.map(([, n]) => n), ["Solid", "Hollow", "Angled"]);
assert.equal(pick("End").head, "hollow", "the ends drawn in the arrow's head shape");
assert.equal(arrowKind(arrow), "reaction");
assert.equal(arrowKind({ ...arrow, arrow: "equilibrium", ratio: 3 }), "unbalanced");
assert.equal(arrowKind({ ...arrow, arrow: "equilibrium", ratio: 1 }), "equilibrium");
for (const k of ["line", "arc", "curve", "orbital"]) assert.equal(arrowKind({ ...arrow, arrow: k }), undefined, `${k}: no kinds`);
for (const c of [undefined, { kind: "shape" }, { kind: "caption" }, { kind: "empty" }]) { assert.equal(arrowKind(c), undefined); assert.deepEqual(arrowPicks(c), []); }
// A block arrow: Large and Medium; a size set by hand shows as Own size. A closed curve: Fill. A curved arrow: Curve.
const block = arrowPicks({ ...arrow, arrow: "block", heads: false, shaped: false, fillable: true, size: "own" } as { kind: string }).flatMap((g) => g.picks);
assert.deepEqual(block.map((p) => p.label), ["Size", "Fill"]);
assert.deepEqual(block[0].options.map(([id]) => id), ["large", "medium", "own"]);
assert.deepEqual(block[1].options.map(([, n]) => n), ["None", "Filled", "Shaded", "Faded"]);
assert.deepEqual(labels({ ...arrow, arrow: "curved", curved: true, sweep: 180 }), [["Line and arrowheads", ["Line", "Start", "End", "Heads", "Curve", "Size"]]]);
assert.equal(arrowPicks({ ...arrow, arrow: "curved", curved: true, sweep: 180 } as { kind: string })[0].picks.find((p) => p.label === "Curve")!.value, "180");
// An orbital: Line is plain, dashed or bold. No heads at either end: no Heads.
assert.deepEqual(arrowPicks({ ...arrow, arrow: "orbital", heads: false, shaped: false, size: undefined } as { kind: string })[0].picks[0].options.map(([id]) => id), ["plain", "dashed", "bold"]);
assert.ok(!labels({ ...arrow, end: "none" })[0][1].includes("Heads"));
// A cycle with a side arrow and a reversible step picked; a side arrow's text.
const side = { ends: "both", start: "none", end: "full", head: "angled", size: "medium" };
assert.deepEqual(labels({ kind: "cycle", side, head: "angled", size: "medium", step: true, reversible: true, balance: "forward" }), [["Side arrow", ["Ends", "Start", "End"]], ["Arrowheads", ["Heads", "Size"]], ["Step", ["Balance"]]]);
assert.deepEqual(labels({ kind: "cycle", head: "solid", size: "small", step: false, reversible: false, balance: "equal" }), [["Arrowheads", ["Heads", "Size"]]]);
assert.deepEqual(labels({ kind: "caption", cycleSide: side }), [["Side arrow", ["Ends", "Start", "End"]], ["Arrowheads", ["Heads", "Size"]]]);
assert.deepEqual(arrowPicks({ kind: "caption", cycleSide: side } as { kind: string }).flatMap((g) => g.picks).map((p) => `${p.command}=${p.value}`),
  ["cycle.side.ends=both", "cycle.side.start=none", "cycle.side.end=full", "cycle.head=angled", "cycle.size=medium"]);
// Every command a pick runs is one the editor handles.
for (const what of ["kind", "style", "start", "end", "head", "sweep", "size", "fill"]) assert.match(editorTsx, new RegExp(`if \\(what === "${what}"|what === "start" \\|\\| what === "end"`), `arrow.${what}`);
for (const what of ["side.ends.", "side.start.", "head.", "size.", "step.balance."]) assert.ok(editorTsx.includes(`"${what}"`) || editorTsx.includes(`what.startsWith("${what}")`), `cycle.${what}`);
// The panel and the menu both draw them from arrowPicks and arrowKind, with the same choices (choices, kindChoices).
assert.match(actionsTsx, /\{arrowPicks\(context\)\.map\(\(g\) => \(/);
assert.match(actionsTsx, /<PickButton key=\{p\.command\} label=\{p\.label\} value=\{p\.value\} onPick=\{\(v\) => run\(`\$\{p\.command\}\.\$\{v\}`\)\} options=\{choices\(p, context\)\} \/>/);
assert.match(actionsTsx, /const kind = arrowKind\(context\), picks = arrowPicks\(context\)\.flatMap\(\(g\) => g\.picks\), kinds = kind \? kindChoices\(context\) : \[\];/);
assert.match(actionsTsx, /if \(p\) return \{ label: p\.label, groups: \[choices\(p, context\)\.map\(\(o\) => \(\{ key: `\$\{p\.command\}\.\$\{o\.id\}`, name: o\.name, icon: o\.glyph, checked: p\.value === o\.id \}\)\)\] \};/);
assert.match(actionsTsx, /if \(key === "pick:arrow\.kind"\) return \{ label: "Kind", groups: \[kinds\.map\(\(o\) => \(\{ key: `arrow\.kind\.\$\{o\.id\}`/);
assert.match(actionsTsx, /\{kindChoices\(context\)\.map\(\(o\) => \(/);
console.log("arrowheads.check: right-click menu ok");
