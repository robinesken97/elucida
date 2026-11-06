// Run: node src/bondsatoms.check.ts. Fails loudly if the bond and atom options taken from ChemDraw 26.1 break:
// quadruple and hydrogen bonds, crossing bonds, label alignment, hidden hydrogens and placed symbols, and their CDXML.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fromCdxml, parseXml, toCdxml } from "./cdxml.ts";
import { cdxToXml, xmlToCdx } from "./cdx.ts";
import { DEFAULT_STYLE, darkColour, readStyle } from "./docstyle.ts";
import { parse, serialize } from "./file.ts";
import { problems, showWarnedHydrogens } from "./check.ts";
import { addSymbol, markNear, moveMark, lowerBond, atomAt, bondAt, bondOrders, cycleBond, deleteAtoms, flipAtoms, interpretLabels, labelWords, rotateAtoms, toFront, setBondSpec, setPosition, toggleHydrogens, toggleLonePairs } from "./edit.ts";
import { HBOND, QUADRUPLE, render, type Atom, type Bond, type Ink, type Mol } from "./render.ts";

type P = [number, number];
const pt = 4 / 3;
const S = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
const box: P[] = [];
for (let i = 0; i <= 40; i++) { const f = i / 40; box.push([9.6 * f, 0], [9.6 * f, -9.5], [0, -9.5 * f], [9.6, -9.5 * f]); }
const ink = (): Ink => ({ width: 9.6, ascent: 9.5, outline: box });
const A = (label: string, x: number, y: number, more: Partial<Atom> = {}): Atom => ({ label, location: [x, y, 0], ...more });
const b = (i: number, j: number, more: Partial<Bond> = {}): Bond => ({ type: 1, atoms: [i, j], ...more });
const roundTrip = (m: Mol) => fromCdxml(toCdxml(m, DEFAULT_STYLE).replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "")).mol;

// CD-8. A quadruple bond is four lines one spacing apart, centred; it counts 4 towards valence.
{
  const m: Mol = { atoms: [A("Re", 0, 0), A("Re", 1, 0)], bonds: [b(0, 1, { type: QUADRUPLE })] };
  const d = render({ ...m, atoms: [A("C", 0, 0), A("C", 1, 0)] }, S, ink);
  assert.equal(d.polygons.length, 4, "four lines");
  const ys = d.polygons.map((poly) => poly.reduce((s, q) => s + q[1], 0) / poly.length).sort((x, y) => x - y);
  assert.ok(ys.every((y, k) => Math.abs(y - (k - 1.5) * S.spacing) < 1e-6), `offsets ${ys}`);
  assert.deepEqual(bondOrders(m), [4, 4]);
  const text = toCdxml(m, DEFAULT_STYLE);
  assert.match(text, /<b\s[^>]*Order="4"/);
  assert.equal(roundTrip(m).bonds[0].type, QUADRUPLE);
  assert.equal(cycleBond(m, 0).bonds[0].type, 1, "a click with the single bond tool makes it single");
}
// A hydrogen bond is dotted, adds nothing to valence, and is ChemDraw 26's DottedHydrogen display.
{
  const m: Mol = { atoms: [A("O", 0, 0), A("H", 1, 0), A("N", 2, 0)], bonds: [b(0, 1), b(1, 2, { type: HBOND })] };
  assert.deepEqual(bondOrders(m), [1, 1, 0]);
  const dots = render({ ...m, atoms: [A("C", 0, 0), A("C", 1, 0), A("C", 2, 0)] }, S, ink).polygons.slice(1);
  assert.equal(dots.length, Math.round(S.bond / (S.hash / 2)) + 1, "one dot every half hash spacing");
  const text = toCdxml(m, DEFAULT_STYLE);
  assert.match(text, /<b\s[^>]*Display="DottedHydrogen"/);
  assert.doesNotMatch(text, /Order="hydrogen"/);
  assert.equal(roundTrip(m).bonds[1].type, HBOND);
  // The spec's hydrogen order and an older dotted bond read as hydrogen bonds too.
  assert.equal(fromCdxml(text.replace('Display="DottedHydrogen"', 'Order="hydrogen"')).mol.bonds[1].type, HBOND);
  assert.equal(fromCdxml(text.replace('Display="DottedHydrogen"', 'Display="Dot"')).mol.bonds[1].type, HBOND);
  assert.equal(cycleBond(m, 1).bonds[1].type, HBOND, "a hydrogen bond stays one");
  // No bond becomes a hydrogen bond (ChemDraw's tool only joins two atoms); a hydrogen bond can become another bond.
  assert.equal(setBondSpec(m, 0, { type: HBOND }), m);
  assert.equal(setBondSpec(m, 1, { type: 1 }).bonds[1].type, 1);
  assert.equal(problems(m).length, 0, "H to N is a sound hydrogen bond");
  const wrong: Mol = { ...m, bonds: [b(0, 1), b(0, 2, { type: HBOND })] };
  assert.match(problems(wrong)[0]?.message ?? "", /^The hydrogen bond at O1 does not join an H atom to an acceptor\./);
  assert.deepEqual(parse(serialize(m)).bonds.map((x) => x.type), [1, HBOND]);
  assert.deepEqual(parse(serialize({ ...m, bonds: [b(0, 1, { type: QUADRUPLE })] })).bonds.map((x) => x.type), [QUADRUPLE]);
}
console.log("bondsatoms.check: quadruple and hydrogen bonds ok");

// CD-9. Two bonds that cross in a flat drawing: the one behind has a gap where the front one passes, as wide as the
// front bond and clear of it by a margin. The later bond is in front; in a structure with depth, the nearer one
// (perspective.check.ts has more).
{
  // One structure: a horizontal bond, a vertical bond across it, and a bond joining their ends.
  const cross: Mol = { atoms: [A("C", -0.5, 0), A("C", 0.5, 0), A("C", 0, -0.5), A("C", 0, 0.5)], bonds: [b(0, 1), b(2, 3), b(1, 3)] };
  const pieces = (m: Mol) => render(m, S, ink).polygons;
  const xs = (poly: P[]) => poly.map((q) => q[0]), ys = (poly: P[]) => poly.map((q) => q[1]);
  const flat = pieces(cross);
  assert.equal(flat.length, 4, "the first bond is cut in two, the others are whole");
  const horiz = flat.filter((poly) => Math.max(...ys(poly)) - Math.min(...ys(poly)) < 1);
  assert.equal(horiz.length, 2, "the horizontal bond (behind) is in two pieces");
  const gap = Math.min(...horiz.map((poly) => Math.min(...xs(poly).map(Math.abs))));
  // As ChemDraw cuts it: half the front bond's width and the Margin Width (S.margin is the label clearance, 1.69/1.6 of it).
  assert.ok(Math.abs(gap - (S.line / 2 + (S.margin * 1.6) / 1.69)) < 1e-6, `gap half-width ${gap}`);
  const front = pieces({ ...cross, bonds: [b(2, 3), b(0, 1), b(1, 3)] });
  assert.equal(front.filter((poly) => Math.max(...xs(poly)) - Math.min(...xs(poly)) < 1).length, 2, "the later bond is in front");
  const raised = pieces({ ...cross, atoms: cross.atoms.map((a, i) => ({ ...a, location: [a.location[0], a.location[1], i < 2 ? 0.2 : 0] })) });
  assert.equal(raised.filter((poly) => Math.max(...xs(poly)) - Math.min(...xs(poly)) < 1).length, 2, "with depth, the nearer bond is in front");
  // A double bond in front cuts a gap as wide as both its lines.
  const dbl = pieces({ ...cross, bonds: [b(0, 1), b(2, 3, { type: 2, position: "left" }), b(1, 3)] }).filter((poly) => Math.max(...ys(poly)) - Math.min(...ys(poly)) < 1);
  assert.equal(dbl.length, 2);
  // Bonds that share an atom never cut each other.
  assert.equal(pieces({ atoms: [A("C", 0, 0), A("C", 1, 0), A("C", 0.5, 0.8)], bonds: [b(0, 1), b(1, 2), b(2, 0)] }).length, 3);
  // f (toFront) brings a bond to the front and keeps the rest in order; CDXML keeps the order through Z.
  const fronted = toFront(cross, new Set([0, 1]));
  assert.deepEqual(fronted.bonds.map((x) => x.atoms), [[2, 3], [1, 3], [0, 1]]);
  const back = roundTrip(fronted);
  assert.equal(pieces(back).filter((poly) => Math.max(...xs(poly)) - Math.min(...xs(poly)) < 1).length, 2, "the first bond is still in front");
  assert.deepEqual(parse(serialize(fronted)).bonds.map((x) => x.atoms), [[2, 3], [1, 3], [0, 1]]);
  // Automatic position: a set side can be taken off again.
  assert.equal(setPosition(setPosition(cross, 0, "left"), 0).bonds[0].position, undefined);
  // Bond Properties (setBondSpec) on a bond brought to the front: it stays in front, with its colour and highlight;
  // a quadruple bond in front still cuts the bond behind.
  const red = { ...fronted, bonds: fronted.bonds.map((x, k) => (k === 2 ? { ...x, colour: "#FF0000", halo: "#00FF00" } : x)) };
  for (const type of [2, 3, QUADRUPLE]) {
    const set = setBondSpec(red, 2, { type });
    assert.deepEqual(set.bonds.map((x) => x.atoms), [[2, 3], [1, 3], [0, 1]], "its place where bonds cross");
    assert.deepEqual([set.bonds[2].type, set.bonds[2].colour, set.bonds[2].halo], [type, "#FF0000", "#00FF00"]);
    assert.equal(pieces(set).filter((poly) => Math.max(...xs(poly)) - Math.min(...xs(poly)) < 1).length, 2, "the bond behind keeps its gap");
  }
  assert.equal(setBondSpec(red, 2, { type: 1, stereo: 1 }).bonds[2].colour, "#FF0000", "a wedge keeps the colour too");
}
console.log("bondsatoms.check: crossing bonds and bond order ok");

// CD-21. A label's alignment set by hand: OMe with its bond on the right reads MeO by itself; Flush Left keeps OMe,
// Centred puts the whole label on the atom, Stacked Above puts Me over O. NH2 Flush Right is H2N.
{
  const ome = (align?: Atom["align"]): Mol => ({ atoms: [A("O", 0, 0, { text: "OMe", ...(align ? { align } : {}) }), A("C", 1, 0)], bonds: [b(0, 1)] });
  const runs = (m: Mol) => render(m, S, ink).labels.map((l) => [l.text, Math.round(l.x * 10) / 10, Math.round(l.y * 10) / 10] as const);
  const o = (m: Mol) => runs(m).find((r) => r[0] === "O")!, me = (m: Mol) => runs(m).find((r) => r[0] === "Me")!;
  assert.ok(me(ome())[1] < o(ome())[1], "automatic: MeO");
  assert.ok(me(ome("left"))[1] > o(ome("left"))[1], "flush left: OMe");
  assert.deepEqual(o(ome("right")), o(ome()), "flush right is MeO, as automatic is here");
  const centre = runs(ome("centre")), wide = 9.6 * 2; // every text measures 9.6 here
  assert.ok(Math.abs(centre.find((r) => r[0] === "O")![1] + wide / 2) < 0.1, "centred: the label's middle on the atom");
  const above = me(ome("above"));
  assert.ok(above[2] < o(ome("above"))[2] && Math.abs(above[1] + 4.8) < 0.1, "stacked above: Me over O, centred");
  const nh2 = (align?: Atom["align"]): Mol => ({ atoms: [A("N", 0, 0, align ? { align } : {}), A("C", -1, 0)], bonds: [b(0, 1)] });
  const h = (m: Mol) => render(m, S, ink).labels.find((l) => l.text === "H")!.x;
  assert.ok(h(nh2()) > 0 && h(nh2("right")) < 0, "NH2 by itself; H2N flush right");
  // CDXML: the node's LabelDisplay says the alignment was set by hand; a label left automatic has none.
  const text = toCdxml(ome("above"), DEFAULT_STYLE);
  assert.match(text, /LabelDisplay="Above"/);
  assert.match(text, /LabelAlignment="Above"/);
  assert.doesNotMatch(toCdxml(ome(), DEFAULT_STYLE), /LabelDisplay/);
  for (const align of ["left", "centre", "right", "above", "below"] as const) assert.equal(roundTrip(ome(align)).atoms[0].align, align);
  assert.equal(roundTrip(ome()).atoms[0].align, undefined);
  assert.equal(parse(serialize(ome("centre"))).atoms[0].align, "centre");
}
console.log("bondsatoms.check: label alignment ok");

// CD-21. Interpret Chemically off: the label is its text (an N with two H stays NH2), saved as an Unspecified node
// whose label is InterpretChemically="no", as ChemDraw saves it. On again, a label that reads as its element with its
// usual H goes back to the element.
{
  const m: Mol = { atoms: [A("N", 0, 0), A("C", 1, 0)], bonds: [b(0, 1)] };
  const off = interpretLabels(m, [0], false);
  assert.deepEqual([off.atoms[0].text, off.atoms[0].chemical], ["NH2", false]);
  assert.deepEqual(interpretLabels(off, [0], true).atoms[0], m.atoms[0], "back to the element");
  const ome = interpretLabels({ ...m, atoms: [A("O", 0, 0, { text: "OMe" }), A("C", 1, 0)] }, [0], false);
  assert.equal(interpretLabels(ome, [0], true).atoms[0].text, "OMe", "a written label keeps its text");
  assert.equal(labelWords({ atoms: [A("O", 0, 0)], bonds: [] }, 0), "H2O", "a lone O reads H2O, as Octet draws it");
  assert.equal(labelWords(m, 0, true), "N", "no H where the document hides them");
  const text = toCdxml(off, DEFAULT_STYLE);
  assert.match(text, /<n\s[^>]*NodeType="Unspecified"/);
  assert.match(text, /<t\s[^>]*InterpretChemically="no"/);
  assert.doesNotMatch(toCdxml(m, DEFAULT_STYLE), /InterpretChemically="no"/);
  const back = roundTrip(off).atoms[0];
  assert.deepEqual([back.text, back.chemical], ["NH2", false]);
  assert.equal(parse(serialize(off)).atoms[0].chemical, false);
}
console.log("bondsatoms.check: interpret chemically ok");

// CD-35. Toggle Hydrogen Display hides explicit H on carbon and keeps an H that means something: on a heteroatom,
// charged, an isotope, on a stereo bond or a stereocentre. A hidden H is not drawn nor hit, still counts towards
// valence, and is saved as Visible="no".
{
  const m: Mol = {
    atoms: [A("C", 0, 0), A("H", 0, 1), A("O", 1, 0), A("H", 1.8, 0.5), A("H", -1, 0, { isotope: 2 }), A("C", 0, -1), A("H", 0.5, -1.8), A("C", -1, -1.5)],
    bonds: [b(0, 1), b(0, 2), b(2, 3), b(0, 4), b(0, 5), b(5, 6, { stereo: 1 }), b(5, 7)],
  };
  const t = toggleHydrogens(m, m.atoms.map((_, i) => i));
  assert.deepEqual(t.atoms.map((a, i) => (a.hidden ? i : -1)).filter((i) => i >= 0), [1], "only the plain H on C1 hides");
  assert.equal(toggleHydrogens(t, [1]).atoms[1].hidden, undefined, "again shows it");
  const d = render(t, S, ink), plain = render({ ...t, atoms: t.atoms.map(({ hidden: _, ...a }) => a) }, S, ink);
  assert.equal(d.labels.filter((l) => l.text === "H").length, plain.labels.filter((l) => l.text === "H").length - 1, "its label is not drawn");
  assert.ok(d.polygons.length < plain.polygons.length, "nor its bond");
  assert.equal(atomAt(t, [0, 1]), undefined);
  assert.equal(bondAt(t, [0, 0.5]), undefined);
  assert.deepEqual(bondOrders(t)[0], bondOrders(m)[0], "its bond still counts");
  const text = toCdxml(t, DEFAULT_STYLE);
  assert.equal((text.match(/Visible="no"/g) ?? []).length, 2, "the H and its bond");
  assert.equal(roundTrip(t).atoms[1].hidden, true);
  assert.equal(parse(serialize(t)).atoms[1].hidden, true);
  // Deleting its carbon takes a hidden H with it. A valence warning on its carbon shows it again, as in ChemDraw.
  assert.ok(!deleteAtoms(t, new Set([0])).atoms.some((a) => a.hidden), "no hidden H left alone");
  assert.equal(showWarnedHydrogens(t), t, "no warning, nothing changes");
  const crowded = { ...t, atoms: [...t.atoms, A("C", -0.8, 0.6)], bonds: [...t.bonds, b(0, 8)] };
  assert.equal(showWarnedHydrogens(crowded).atoms[1].hidden, undefined, "five bonds at C1 show its H");
}
// Methane with its four H drawn. As in ChemDraw, Toggle Hydrogen Display does nothing to it alone: no bond would stay
// in view. With a structure that keeps a bond in view in the selection, its H hide too, and its carbon then shows as
// a lone carbon does (CH4): a hidden H does not count as a bond in the drawing.
{
  const methane: Mol = { atoms: [A("C", 0, 0), A("H", 0, 1), A("H", 1, 0), A("H", 0, -1), A("H", -1, 0)], bonds: [b(0, 1), b(0, 2), b(0, 3), b(0, 4)] };
  assert.equal(toggleHydrogens(methane, [0, 1, 2, 3, 4]), methane, "methane alone stays");
  const ethane: Mol = { atoms: [A("C", 5, 0), A("C", 6, 0), A("H", 5, 1)], bonds: [b(0, 1), b(0, 2)] };
  const both: Mol = { atoms: [...methane.atoms, ...ethane.atoms], bonds: [...methane.bonds, ...ethane.bonds.map((x) => b(x.atoms[0] + 5, x.atoms[1] + 5))] };
  const t = toggleHydrogens(both, both.atoms.map((_, i) => i));
  assert.deepEqual(t.atoms.map((a, i) => (a.hidden ? i : -1)).filter((i) => i >= 0), [1, 2, 3, 4, 7], "with ethane, methane's H hide too");
  const near = (d: ReturnType<typeof render>, x: number) => d.labels.filter((l) => Math.abs(l.x - x * S.bond) < 1.5 * S.bond).map((l) => l.text).join("");
  assert.equal(near(render(t, S, ink), 0), "CH4", "the carbon shows, with its hidden H in its label");
  assert.equal(near(render(t, S, ink), 5), "", "a carbon with a bond in view stays a skeletal carbon");
}
console.log("bondsatoms.check: hidden hydrogens ok");

// CD-26. A mark moved round its atom keeps its angle; lone pairs can be bars; an attachment point can be ChemDraw's
// diamond or star, and the bond stops at it.
{
  const water = (more: Partial<Atom> = {}): Mol => ({ atoms: [A("O", 0, 0, { pairs: 2, ...more }), A("C", 1, 0)], bonds: [b(0, 1)] });
  const at = (m: Mol, key: string) => { const e = render(m, S, ink).electrons.find((x) => x.key === key)!; return Math.round((Math.atan2(-e.at[1], e.at[0]) * 180) / Math.PI); };
  assert.equal(at(water({ angles: { pair0: 90 } }), "pair0"), 90, "pair0 straight up");
  assert.notEqual(at(water({ angles: { pair0: 90 } }), "pair1"), 90, "pair1 goes elsewhere");
  const dots = render(water(), S, ink).polygons.length, bars = render(water({ bars: true }), S, ink).polygons.length;
  assert.equal(dots - bars, 2, "two bars for four dots");
  assert.deepEqual([addSymbol(water(), 0, "pair", true).atoms[0].bars, addSymbol(water({ bars: true }), 0, "pair", true).atoms[0].bars], [true, undefined], "Option-click switches the lone pairs' style");
  // Settings > Drawing > Lone pairs as bars: the first pair is a bar, and Option-click still switches it to dots.
  const bare = water({ pairs: undefined }), barred = addSymbol(bare, 0, "pair", false, true);
  assert.deepEqual([barred.atoms[0].pairs, barred.atoms[0].bars, addSymbol(barred, 0, "pair", false, true).atoms[0].bars, addSymbol(barred, 0, "pair", true, true).atoms[0].bars], [1, true, true, undefined]);
  assert.equal(addSymbol(bare, 0, "pair").atoms[0].bars, undefined, "dots by default");
  assert.deepEqual([toggleLonePairs(bare, [0], true).atoms[0].bars, toggleLonePairs(bare, [0]).atoms[0].bars], [true, undefined], "Show lone pairs takes the style too");
  // Delete or Backspace over a bond takes a line off: triple to double to single, aromatic to single, keeping its
  // colour; a single bond goes (lowerBond gives nothing, so Delete removes it).
  const pair = (type: number, more: Partial<Bond> = {}): Mol => ({ atoms: [A("C", 0, 0), A("C", 1, 0)], bonds: [{ ...b(0, 1), type, ...more }] });
  assert.equal(lowerBond(pair(2), 0)!.bonds[0].type, 1);
  assert.equal(lowerBond(pair(3), 0)!.bonds[0].type, 2);
  assert.equal(lowerBond(pair(QUADRUPLE), 0)!.bonds[0].type, 3);
  assert.equal(lowerBond(pair(4), 0)!.bonds[0].type, 1);
  assert.equal(lowerBond(pair(2, { display: "dashed", colour: "#c00" }), 0)!.bonds[0].display, undefined);
  assert.equal(lowerBond(pair(2, { colour: "#c00" }), 0)!.bonds[0].colour, "#c00");
  assert.equal(lowerBond(pair(1), 0), undefined);
  assert.equal(lowerBond(pair(HBOND), 0), undefined);
  // Circled negative clicked twice: a circled 2− (Sam's imidophosphorane, 31 October 2026). The ring holds the
  // number and sign as text; a circled 1− keeps its drawn bar and no text.
  const nitrogen = (): Mol => ({ atoms: [A("N", 0, 0), A("C", 1, 0)], bonds: [b(0, 1)] });
  const twice = addSymbol(addSymbol(nitrogen(), 0, "circledMinus"), 0, "circledMinus");
  assert.deepEqual([twice.atoms[0].charge, twice.atoms[0].circled], [-2, true]);
  assert.ok(render(twice, S, ink).labels.some((l) => l.text === "2−"), "2− inside the ring");
  assert.ok(!render(addSymbol(nitrogen(), 0, "circledMinus"), S, ink).labels.some((l) => /−/.test(l.text)), "a circled 1− has no text");
  // Diamond and star: the bond stops at the shape, which is drawn as an outline.
  const point = (attach: Atom["attach"]): Mol => ({ atoms: [A("C", 0, 0), A("C", 1, 0, { attach })], bonds: [b(0, 1)] });
  const reach = (m: Mol) => Math.max(...render(m, S, ink).polygons[0].map((q) => q[0]));
  assert.ok(reach(point("diamond")) < S.bond - (0.75 * S.size + 2 * S.line) / 2 + 0.5, "the bond stops at the diamond");
  assert.ok(reach(point(true)) > S.bond - 1, "a wavy point does not cut the bond");
  assert.deepEqual([addSymbol(point(true), 1, "attachStar").atoms[1].attach, addSymbol(point("star"), 1, "attachStar").atoms[1].attach], ["star", undefined]);
  for (const attach of [true, "diamond", "star"] as const) assert.equal(roundTrip(point(attach)).atoms[1].attach, attach);
  assert.match(toCdxml(point("diamond"), DEFAULT_STYLE), /ExternalConnectionType="Diamond"/);
  // As ChemDraw writes one (spec: ExternalConnectionType is for nodes of type ExternalConnectionPoint): no element,
  // no H count and no label, so ChemDraw reads no carbon there.
  for (const [attach, type] of [[true, "Wavy"], ["diamond", "Diamond"], ["star", "Star"]] as const) {
    const n = /<n\b[^>]*NodeType="ExternalConnectionPoint"[^>]*>/.exec(toCdxml(point(attach), DEFAULT_STYLE))?.[0] ?? "";
    assert.match(n, new RegExp(`ExternalConnectionType="${type}"`));
    assert.doesNotMatch(n, /Element=|NumHydrogens=|\/>\s*<t\b/, type);
  }
  // CDXML: bars are LonePairBar symbols; angles go back exactly in Octet's files and from the symbols' places in
  // ChemDraw's.
  const moved = water({ bars: true, angles: { pair0: 90 } }), text = toCdxml(moved, DEFAULT_STYLE);
  assert.equal((text.match(/SymbolType="LonePairBar"/g) ?? []).length, 2);
  assert.deepEqual(fromCdxml(text).mol.atoms[0].angles, { pair0: 90 });
  const foreign = roundTrip(moved).atoms[0];
  assert.equal(foreign.bars, true);
  assert.equal(foreign.angles?.pair0, 90, "ChemDraw's copy: the symbol's place gives the angle");
  assert.deepEqual(parse(serialize(moved)).atoms[0].angles, { pair0: 90 });
  assert.equal(parse(serialize(point("star"))).atoms[1].attach, "star");
  // A placed mark turns and flips with its atom.
  const all = new Set([0, 1]);
  assert.deepEqual(rotateAtoms(moved, all, 90).atoms[0].angles, { pair0: -180 });
  assert.deepEqual(flipAtoms(water({ angles: { pair0: 30 } }), all, "horizontal").atoms[0].angles, { pair0: 150 });
  assert.deepEqual(flipAtoms(water({ angles: { pair0: 30 } }), all, "vertical", true).atoms[0].angles, { pair0: -30 });
  assert.deepEqual(rotateAtoms(moved, new Set([1]), 90).atoms[0].angles, { pair0: 90 }, "an atom not turned keeps its marks");
}
console.log("bondsatoms.check: placed and styled symbols ok");

// Charges, radicals and lone pairs moved by hand (Sam's feedback, November 2026): a drag with Select on a mark moves it
// round its atom in 15° steps (free without Fixed Angles or with Option); it stays with the atom and keeps its place
// in .oct, Octet's CDXML and ChemDraw's (the symbol's place round the atom).
{
  const L = S.bond;
  const doc = (p: P) => [p[0] / L, -p[1] / L] as P;
  const water: Mol = { atoms: [A("O", 0, 0, { pairs: 2 }), A("C", 1, 0)], bonds: [b(0, 1)] };
  const e = render(water, S, ink).electrons.find((x) => x.key === "pair0")!;
  assert.deepEqual(markNear(render(water, S, ink).electrons, water, doc(e.at), L), { atom: 0, mark: "pair0" }, "a press on the pair takes the pair");
  assert.equal(markNear(render(water, S, ink).electrons, water, [0, 0], L), undefined, "a press on the atom takes the atom");
  assert.equal(moveMark(water, 0, "pair0", [0.1, 1], true).atoms[0].angles?.pair0, 90, "15° steps");
  assert.equal(moveMark(water, 0, "pair0", [0.1, 1], false).atoms[0].angles?.pair0, 84, "free");
  const at = (m: Mol, key: string) => { const d = render(m, S, ink), x = d.electrons.find((y) => y.key === key)!, o = d.labelAt[0]; return Math.round((Math.atan2(o[1] - x.at[1], x.at[0] - o[0]) * 180) / Math.PI); };
  // A carbocation's sign (a skeletal carbon's charge) moves too, and so do a circled charge and a radical.
  const cation: Mol = { atoms: [A("C", 0, 0, { charge: 1 }), A("C", 1, 0), A("C", -0.5, 0.87)], bonds: [b(0, 1), b(0, 2)] };
  assert.ok(markNear(render(cation, S, ink).electrons, cation, doc(render(cation, S, ink).electrons.find((x) => x.key === "charge")!.at), L), "the sign is a mark");
  const up = moveMark(cation, 0, "charge", [0, -1], true);
  assert.equal(at(up, "charge"), -90, "the sign goes below");
  const marked = (more: Partial<Atom>): Mol => ({ atoms: [A("N", 0, 0, more), A("C", 1, 0)], bonds: [b(0, 1)] });
  for (const [m, key, deg] of [[up, "charge", -90], [marked({ charge: 1, circled: true, angles: { charge: 180 } }), "charge", 180], [marked({ radical: 1, angles: { radical0: -135 } }), "radical0", -135], [marked({ pairs: 1, angles: { pair0: 45 } }), "pair0", 45]] as const) {
    assert.equal(at(m, key), deg, `${key} drawn where it was put`);
    assert.equal(parse(serialize(m)).atoms[0].angles?.[key], deg, `${key} in .oct`);
    assert.equal(fromCdxml(toCdxml(m, DEFAULT_STYLE)).mol.atoms[0].angles?.[key], deg, `${key} in Octet's CDXML`);
    assert.equal(roundTrip(m).atoms[0].angles?.[key], deg, `${key} from ChemDraw's symbol place`);
    const plain = toCdxml(m, DEFAULT_STYLE).replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "");
    assert.equal(fromCdxml(cdxToXml(xmlToCdx(parseXml(plain)))).mol.atoms[0].angles?.[key], deg, `${key} in CDX`);
    // It goes with its atom: moved, the mark keeps its angle beside it.
    const moved: Mol = { ...m, atoms: m.atoms.map((a) => ({ ...a, location: [a.location[0] + 3, a.location[1] - 2, 0] })) };
    assert.equal(at(moved, key), deg, `${key} follows its atom`);
  }
  // A singlet (carbene) pair is pair0 and the atom's lone pairs come after it, in the file as on the page.
  const nitrene = marked({ radical: 3, pairs: 1, angles: { pair0: 90, pair1: -90 } });
  assert.deepEqual(roundTrip(nitrene).atoms[0].angles, { pair0: 90, pair1: -90 });
  // The same with the singlet's symbol after the lone pair in the file, as another program may write it.
  const pairs = toCdxml(nitrene, DEFAULT_STYLE).replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "").match(/<graphic[^>]*SymbolType="LonePair"[^>]*?(\/>|>.*?<\/graphic>)/g)!;
  const swapped = toCdxml(nitrene, DEFAULT_STYLE).replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "").replace(pairs[0] + pairs[1], pairs[1] + pairs[0]);
  assert.ok(pairs.length === 2 && swapped.indexOf(pairs[1]) < swapped.indexOf(pairs[0]));
  assert.deepEqual(fromCdxml(swapped).mol.atoms[0].angles, { pair0: 90, pair1: -90 }, "the singlet's pair is pair0 wherever it comes");
  // Every mark on one atom at once keeps its own place.
  const all = marked({ charge: 1, circled: true, radical: 1, pairs: 1, angles: { charge: 150, radical0: -30, pair0: 60 } });
  assert.deepEqual(roundTrip(all).atoms[0].angles, { charge: 150, radical0: -30, pair0: 60 });
}
// A curved arrow drawn from a lone pair or radical starts on it (electronAt): a press there with Select picks the
// arrow, and a picked arrow's handle comes before the mark, as in 1.0.29.
{
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
  assert.match(editor, /const end = mark && arrowEndAt\(p\);\s*if \(end !== undefined\) return \{ arrow: end \};\s*if \(mark && !selection\.has\(mark\.atom\)\) return mark;/);
  const down = editor.slice(editor.indexOf("const handle = tool !== \"erase\" ? handleAt(p) : undefined;"));
  assert.ok(down.indexOf("handle && handle.which !== \"add\" ? undefined") > 0 && down.indexOf("handle && handle.which !== \"add\" ? undefined") < down.indexOf("setDrag({ kind: \"mark\""), "the handle before the mark");
  assert.match(editor, /arrowEndAt\(p\) === undefined \? markNear\(/);
}
console.log("bondsatoms.check: marks moved by hand ok");

// CD-28. The named palette is saved with the document, in Octet's data and in the CDXML colour table (ChemDraw's
// document palette); Octet reads the names back. So is a background colour of the user's own.
{
  const palette = [{ name: "Catalyst", hex: "#12A594" }, { name: "Product", hex: "#8E4EC6" }];
  const style = { ...DEFAULT_STYLE, palette }, m: Mol = { atoms: [A("C", 0, 0), A("O", 1, 0)], bonds: [b(0, 1)] };
  const text = toCdxml(m, style);
  assert.match(text, /<colortable>[\s\S]*r="0.0706" g="0.6471" b="0.5804"[\s\S]*<\/colortable>/, "the colours are in the colour table");
  assert.deepEqual(fromCdxml(text).style.palette, palette);
  assert.equal(fromCdxml(text.replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "")).style.palette, undefined, "a ChemDraw copy has the colours, not the names");
  assert.deepEqual(parse(serialize({ ...m, style })).style?.palette, palette);
  assert.equal(readStyle({ palette: [{ name: "x", hex: "red" }, { name: 3, hex: "#000000" }] }).palette, undefined, "bad entries are left out");
  // A page background of the user's own colour is ChemDraw's document bgcolor; Octet reads it from both kinds of file.
  const tinted = { ...DEFAULT_STYLE, background: "#FFF4D6" as const }, page = toCdxml(m, tinted), strip = (t: string) => t.replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "");
  assert.notEqual(/<CDXML\s[^>]*bgcolor="(\d+)"/.exec(page)?.[1], "1");
  assert.equal(fromCdxml(page).style.background.toUpperCase(), "#FFF4D6");
  assert.equal(fromCdxml(strip(page)).style.background.toUpperCase(), "#FFF4D6");
  assert.equal(fromCdxml(strip(text)).style.background, "white", "a white page stays white");
  assert.equal(readStyle({ background: "#FFF4D" }).background, "white");
  assert.deepEqual([darkColour("#1D4B86"), darkColour("#FFF4D6"), darkColour("#808080")], [true, false, false]);
}
console.log("bondsatoms.check: document palette and background ok");
