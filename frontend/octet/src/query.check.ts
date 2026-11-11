// Run: node src/query.check.ts. Fails loudly if a query or Markush feature (CH-16 to CH-19) is read wrongly, or is
// lost on a round trip through Octet's file, CDXML (Octet's own and as ChemDraw keeps it) or MOL V3000.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { deleteAtoms, extractSelection, fragments, insertMol, merge, subset } from "./edit.ts";
import { parse, serialize } from "./file.ts";
import { isQueryMolfile, readV3000, writeV3000 } from "./molv3.ts";
import { expandGeneric, layoutGrid } from "./expand.ts";
import {
  altGroup, atomIndicator, bondIndicator, stepSubstituents, elementList, enclosed, GENERICS, hasQuery, isGeneric, linkNode, massText, placeAttachments, polymerLabel, polymerTags, queryLabel, repeatCount, rgroupMembers,
} from "./query.ts";
import { labelSmiles } from "./labels.ts";
import { messy, problems } from "./check.ts";
import type { Atom, Bond, Mol, Shape } from "./render.ts";

const A = (label: string, x: number, y: number, more: Partial<Atom> = {}): Atom => ({ label, location: [x, y, 0], ...more });
const b = (i: number, j: number, more: Partial<Bond> = {}): Bond => ({ type: 1, atoms: [i, j], ...more });

// Labels: ChemDraw's 43 generic labels, R numbers, element and NOT lists, link nodes and anonymous alternative groups.
assert.equal(GENERICS.length, 43);
for (const g of ["A", "Q", "M", "X", "R", "R1", "R12", "R'", "G*", "GH*", "CYC", "ALK", "CXH"]) assert.ok(isGeneric(g), g);
for (const g of ["R0", "R100", "Ph", "C", "Cy"]) assert.ok(!isGeneric(g), g);
assert.equal(labelSmiles("CYC"), undefined, "a generic label is never read as atoms (not C–Y–C)");
assert.equal(labelSmiles("CHC"), undefined);
assert.deepEqual(elementList("[Cl, Br, I]"), { not: false, elements: ["Cl", "Br", "I"] });
assert.deepEqual(elementList("Cl,Br"), { not: false, elements: ["Cl", "Br"] }, "brackets are optional");
assert.deepEqual(elementList("[NOT O, S]"), { not: true, elements: ["O", "S"] });
assert.deepEqual(elementList("[-N]"), { not: true, elements: ["N"] }, "a minus sign for NOT");
assert.equal(elementList("[Cl]"), undefined, "one element is an element, not a list");
assert.equal(elementList("[CH3, OMe]"), undefined);
assert.deepEqual(altGroup("[CH3, CH2OH, Ph]"), ["CH3", "CH2OH", "Ph"]);
assert.deepEqual(linkNode("[CH2]3-7"), { element: "C", h: 2, low: 3, high: 7 });
assert.deepEqual(linkNode("O1-3"), { element: "O", h: 0, low: 1, high: 3 });
assert.deepEqual(linkNode("(CH2)2-4"), { element: "C", h: 2, low: 2, high: 4 });
assert.equal(linkNode("[CH2]5-3"), undefined, "the range must rise");
assert.deepEqual(["R1", "[Cl,Br]", "[CH2]1-5", "[OMe, Ph]", "OMe", undefined].map(queryLabel), ["generic", "list", "link", "alt", undefined, undefined]);
console.log("query.check: labels ok");

// Indicators, as ChemDraw draws them.
assert.equal(atomIndicator({ subst: { kind: "free", n: 2 } }), "*2");
assert.equal(atomIndicator({ subst: { kind: "upto", n: 3 }, noH: true, rings: "simple", unsat: "present", change: true, stereo: "inversion", translation: "broad" }), "U3HRSCTL");
assert.equal(atomIndicator({ subst: { kind: "exactly", n: 1 }, valence: true, abundance: "natural" }), "X1", "abnormal valence and abundance have none");
assert.equal(bondIndicator({ query: "sd", topology: "ring", rxn: "makebreak" }), "S/D Rng Rxn");
assert.equal(bondIndicator({ query: "any", topology: "either" }), "Any R/C");
// Polymer labels and counts.
assert.deepEqual([polymerLabel({ usage: "sru" }), polymerLabel({ usage: "sru", label: "m" }), polymerLabel({ usage: "mult", label: "3" }), polymerLabel({ usage: "c", order: 2 }), polymerLabel({ usage: "co" }), polymerLabel({ usage: "gen" })],
  ["n", "m", "3", "c2", "co", ""]);
assert.equal(polymerTags({ usage: "sru", pattern: "hh", flip: "flip" }), "hh flip");
assert.deepEqual([repeatCount({ usage: "mult" }), repeatCount({ usage: "mult", label: "2.5" }), repeatCount({ usage: "param", label: "3-5" }), repeatCount({ usage: "param", mw: 200 }, 78.11), repeatCount({ usage: "sru" })],
  [2, 2.5, 4, 200 / 78.11, undefined]);
assert.equal(massText({ weight: 58.12, exact: 58.08, repeat: { label: "n", weight: 28.05, exact: 28.03, ends: { weight: 30.07, exact: 30.05 } } }, "weight", 2), "30.07 + (28.05)n");
// The free-site, up-to and exactly keys step an atom's substituent count.
{
  let m: Mol = { atoms: [A("C", 0, 0)], bonds: [] };
  m = stepSubstituents(stepSubstituents(m, 0, "free"), 0, "free");
  assert.deepEqual(m.atoms[0].query, { subst: { kind: "free", n: 2 } });
  assert.deepEqual(stepSubstituents(m, 0, "upto").atoms[0].query, { subst: { kind: "upto", n: 1 } }, "another kind starts at 1");
  for (let k = 0; k < 12; k++) m = stepSubstituents(m, 0, "free");
  assert.equal(m.atoms[0].query?.subst?.n, 9, "free sites go up to 9");
  for (let k = 0; k < 10; k++) m = stepSubstituents(m, 0, "lower");
  assert.equal(m.atoms[0].query, undefined, "lowered below 0, the count is unset");
}
console.log("query.check: indicators and polymer labels ok");

// A query drawing with every CH-16 to CH-19 feature: a scaffold with query atoms and bonds, an R1, an element list, a
// link node, an anonymous alternative group, a variable attachment on a ring, ferrocene's multi-centre attachments, an
// R-group definition with two fragments and R-Logic, and polyethylene in SRU brackets.
const ring = (cx: number, cy: number, n: number, r = 1) => Array.from({ length: n }, (_, k) => A("C", cx + r * Math.cos((2 * Math.PI * k) / n), cy + r * Math.sin((2 * Math.PI * k) / n)));
const atoms: Atom[] = [
  A("C", 0, 0, { query: { subst: { kind: "exactly", n: 3 }, noH: true, rings: "simple", unsat: "present", change: true, stereo: "retention", translation: "narrow", abundance: "enriched", valence: true } }), // 0
  A("N", 1, 0, { query: { subst: { kind: "free", n: 0 } } }), // 1
  A("C", 2, 0.5, { text: "R1" }), // 2
  A("C", 2, -0.5, { text: "[Cl,Br,I]" }), // 3
  A("C", -1, 0.5, { text: "[CH2]1-3", query: { subst: { kind: "upto", n: 2 } } }), // 4
  A("C", -2, 0, { text: "[OMe, Ph]" }), // 5
  ...ring(0, -4, 6), // 6–11: benzene for the variable attachment
  A("C", 0, -4, { centre: { atoms: [6, 7, 8], variable: true } }), // 12
  A("Br", 1.5, -2.5), // 13
  ...ring(8, 1.5, 5, 0.85), // 14–18: a Cp ring
  ...ring(8, -1.5, 5, 0.85), // 19–23: the other
  A("C", 8, 1.5, { centre: { atoms: [14, 15, 16, 17, 18] } }), // 24
  A("C", 8, -1.5, { centre: { atoms: [19, 20, 21, 22, 23] } }), // 25
  A("Fe", 8, 0), // 26
  // R1's definition: a methyl (attached by a mark) and a chlorine (attached by itself).
  A("C", 15, 1), A("C", 14, 1, { attach: true }), A("Cl", 15, -0.5), // 27–29
  // Polyethylene: open ends and two CH2 in SRU brackets.
  A("C", 0, -9), A("C", 1, -9), A("C", 2, -9), A("C", 3, -9), // 30–33
];
const bonds: Bond[] = [
  b(0, 1, { query: "sd", topology: "ring", rxn: "makebreak" }), b(1, 2, { query: "any", rxn: "nochange" }), b(1, 3, { query: "da", type: 2, topology: "chain" }), b(0, 4, { query: "sa" }), b(4, 5),
  b(6, 7, { type: 2 }), b(7, 8), b(8, 9, { type: 2 }), b(9, 10), b(10, 11, { type: 2 }), b(11, 6), b(12, 13),
  b(14, 15), b(15, 16), b(16, 17), b(17, 18), b(18, 14), b(19, 20), b(20, 21), b(21, 22), b(22, 23), b(23, 19), b(24, 26), b(25, 26),
  b(27, 28),
  b(30, 31), b(31, 32), b(32, 33),
];
const shapes: Shape[] = [
  { id: 1, kind: "box", from: [13, 2], to: [16.5, -1.5], rgroup: { name: "R1", occur: "1-3", restH: true }, dashed: true, width: 1.2 },
  { id: 2, kind: "brackets", from: [0.5, -8.4], to: [2.5, -9.6], polymer: { usage: "sru", pattern: "hh" } },
];
const drawing: Mol = { atoms, bonds, shapes };
assert.ok(hasQuery(drawing));
assert.ok(!hasQuery({ atoms: [A("C", 0, 0)], bonds: [] }));
// Ferrocene is one structure; the R-group's fragments are found in its box; the SRU encloses the middle two carbons.
const frags = fragments(drawing);
assert.ok(frags.some((f) => [14, 19, 24, 25, 26].every((i) => f.includes(i))), "ferrocene is one structure");
assert.deepEqual(rgroupMembers(drawing, frags)[0].members.map((f) => [...f].sort((p, q) => p - q)), [[27, 28], [29]]);
assert.deepEqual(enclosed(drawing, shapes[1]), { atoms: [31, 32], crossing: [25, 27] });
console.log("query.check: drawing ok");

// Attachments keep their atoms through edits: deleting, copying and pasting renumber them; an attachment left with
// fewer than two atoms goes; it stays at the centre of its atoms.
const gone = deleteAtoms(drawing, new Set([0]));
assert.deepEqual(gone.atoms.find((a) => a.centre?.variable)!.centre!.atoms, [5, 6, 7]);
const noRing = deleteAtoms(drawing, new Set([14, 15, 16, 17]));
assert.equal(noRing.atoms.filter((a) => a.centre).length, 2, "the Cp attachment goes with its ring");
assert.equal(deleteAtoms({ atoms: [A("C", 0, 0), A("C", 1, 0), A("C", 0.5, 0, { centre: { atoms: [0, 1] } })], bonds: [b(0, 1)] }, new Set()).atoms.length, 3, "an attachment with no bond stays");
const copy = extractSelection(drawing, new Set([6, 7, 8, 9, 10, 11, 12, 13]), new Set());
assert.deepEqual(copy.atoms[6].centre!.atoms, [0, 1, 2]);
assert.deepEqual(merge(drawing, copy, [0, 0]).atoms[drawing.atoms.length + 6].centre!.atoms, [34, 35, 36]);
assert.deepEqual(insertMol(drawing, copy, [5, 5]).mol.atoms[drawing.atoms.length + 6].centre!.atoms, [34, 35, 36]);
assert.deepEqual(subset(drawing, new Set([12, 13])).atoms.map((a) => a.label), ["Br"], "an attachment without its atoms is not copied");
const moved = placeAttachments({ ...drawing, atoms: drawing.atoms.map((a, i) => (i >= 14 && i <= 18 ? { ...a, location: [a.location[0] + 1, a.location[1], 0] } : a)) });
assert.deepEqual(moved.atoms[24].location.slice(0, 2).map((v) => +v.toFixed(6)), [9, 1.5]);
// Warnings: an attachment sits among its atoms and its bonds cross its ring by design, an R-group fragment's
// attachment mark is not a carbon, and Abnormal Valence allowed turns the valence warning off.
{
  const placed = placeAttachments(drawing);
  assert.equal(messy(placed), false);
  const found = problems(placed);
  assert.ok(!found.some((p) => p.atom !== undefined && placed.atoms[p.atom].centre), "no warning on an attachment");
  assert.ok(!found.some((p) => p.type === "isolated"), "an attachment mark's bond is not ethane");
  const five: Mol = { atoms: [A("C", 0, 0, { query: { valence: true } }), ...[0, 1, 2, 3, 4].map((k) => A("C", Math.cos(k), Math.sin(k)))], bonds: [1, 2, 3, 4, 5].map((j) => b(0, j)) };
  assert.ok(!problems(five).some((p) => p.type === "valence"));
  assert.ok(problems({ ...five, atoms: [A("C", 0, 0), ...five.atoms.slice(1)] }).some((p) => p.type === "valence"));
}
console.log("query.check: attachments through edits ok");

// Expand Generic Structure: each combination of the sites' choices, as its own structure.
{
  // The variable bromine (3 places) on a ring with R1 (a methyl or a chlorine) and [Cl,Br] in two of its places.
  const m: Mol = { atoms: [...drawing.atoms.slice(0, 14), ...drawing.atoms.slice(27, 30)], bonds: [], shapes: [shapes[0]] };
  m.atoms[12] = { ...m.atoms[12], centre: { atoms: [6, 7, 8], variable: true } };
  m.atoms[9] = { ...m.atoms[9], text: "R1" };
  m.atoms[10] = { ...m.atoms[10], text: "[Cl,Br]" };
  m.bonds = [b(6, 7, { type: 2 }), b(7, 8), b(8, 9), b(9, 10), b(10, 11), b(11, 6), b(12, 13), b(14, 15)];
  const { mols, total } = expandGeneric(m, [6, 7, 8, 9, 10, 11, 12, 13]);
  assert.equal(total, 12, "3 places × 2 R1 fragments × 2 elements");
  assert.equal(mols.length, 12);
  const labels = (x: Mol) => x.atoms.map((a) => a.text ?? a.label).sort().join(" ");
  assert.deepEqual([...new Set(mols.map(labels))].sort(), ["Br Br C C C C C", "Br Br C C C C Cl", "Br C C C C C Cl", "Br C C C C Cl Cl"]);
  assert.ok(mols.every((x) => !x.atoms.some((a) => a.centre || a.attach || a.text)), "no attachments, marks or query labels left");
  // The attached bromine has one bond, to a ring carbon, in each structure; the three places all occur.
  const degree = (x: Mol, i: number) => x.bonds.filter((y) => y.atoms.includes(i)).length;
  assert.ok(mols.every((x) => x.atoms.filter((a, i) => a.label === "Br" && degree(x, i) === 1).length === 1));
  assert.equal(new Set(mols.map((x) => { const i = x.atoms.findIndex((a, k) => a.label === "Br" && degree(x, k) === 1), bond = x.bonds.find((y) => y.atoms.includes(i))!; return bond.atoms.find((k) => k !== i); })).size, 3);
  assert.equal(layoutGrid(mols).atoms.length, mols.reduce((n, x) => n + x.atoms.length, 0));
  // A joined fragment keeps a zigzag: CH2OH (drawn with no mark) and an ethyl drawn with its mark meet the ring at 120°.
  {
    const r: Mol = { atoms: [A("C", 0, 0), A("C", 1, 0, { text: "R1" }), A("C", 5, 0), A("O", 6, 0), A("C", 5, -2), A("C", 5.87, -2.5), A("C", 4.13, -2.5, { attach: true })],
      bonds: [b(0, 1), b(2, 3), b(4, 5), b(4, 6)], shapes: [{ id: 1, kind: "box", from: [3.5, 1], to: [7, -3.5], rgroup: { name: "R1" } }] };
    const angle = (x: Mol, i: number) => { const ns = x.bonds.filter((y) => y.atoms.includes(i)).map((y) => x.atoms[y.atoms[0] === i ? y.atoms[1] : y.atoms[0]].location), c = x.atoms[i].location;
      const [u, v] = ns.map((q) => Math.atan2(q[1] - c[1], q[0] - c[0])); return Math.round((Math.abs(Math.atan2(Math.sin(u - v), Math.cos(u - v))) * 180) / Math.PI); };
    const out = expandGeneric(r, [0, 1]).mols;
    assert.deepEqual(out.map((x) => x.atoms.map((a) => a.label).join("")), ["CCO", "CCC"]);
    assert.deepEqual(out.map((x) => angle(x, 1)), [120, 120], "not a straight line at the joining atom");
  }
  // A wavy bond stands for a wedge and a hash.
  const wavy = expandGeneric({ atoms: [A("C", 0, 0), A("C", 1, 0), A("O", 1.5, 0.866), A("N", 1.5, -0.866), A("C", 2, 0)], bonds: [b(0, 1), b(1, 2), b(1, 3), b(1, 4, { display: "wavy" })] }, [0]);
  assert.deepEqual(wavy.mols.map((x) => x.bonds[3].stereo), [1, 6]);
}
console.log("query.check: expand generic structure ok");

// What a round trip must keep: each atom's label, query and attachment, each bond's query, the shapes' meanings.
const facts = (m: Mol) => ({
  atoms: m.atoms.map((a) => [a.label, a.text, a.query, a.centre, a.attach]),
  bonds: m.bonds.map((x) => [x.atoms, x.type, x.query, x.topology, x.rxn]),
  shapes: (m.shapes ?? []).map((s) => [s.kind, s.rgroup, s.polymer, s.dashed, s.width]),
});
const same = (a: Mol, z: Mol, what: string) => assert.deepEqual(facts(a), facts(z), what);

// Octet's own file (JSON) keeps everything.
same(parse(serialize(drawing)), drawing, "Octet's file");
assert.throws(() => parse(serialize(drawing).replace('"atoms": [\n     6', '"atoms": [\n     99')), /damaged/, "an attachment to an atom the file does not have");

// CDXML, Octet's own file: everything comes back exactly.
const text = toCdxml(drawing, DEFAULT_STYLE);
same(fromCdxml(text).mol, drawing, "CDXML read back");
assert.deepEqual(fromCdxml(text).lost, {});
// What ChemDraw reads: the query attributes, query bond orders, node types and the polymer and R-group objects.
for (const want of [/SubstituentsExactly="3"/, /ImplicitHydrogens="yes"/, /RingBondCount="SimpleRing"/, /UnsaturatedBonds="MustBePresent"/, /RxnChange="yes"/, /RxnStereo="Retention"/,
  /Translation="Narrow"/, /IsotopicAbundance="Enriched"/, /AbnormalValence="yes"/, /FreeSites="0"/, /SubstituentsUpTo="2"/, /Order="1 2"/, /Order="any"/, /Order="2 1.5"/, /Order="1 1.5"/,
  /Topology="Ring"/, /Topology="Chain"/, /RxnParticipation="MakeOrBreak"/, /RxnParticipation="NoChange"/, /NodeType="NamedAlternativeGroup"/, /NodeType="ElementList"\s[^>]*ElementList="17 35 53"/,
  /NodeType="LinkNode"\s[^>]*LinkCountLow="1"\s+LinkCountHigh="3"/, /NodeType="AnonymousAlternativeGroup"/, /NodeType="VariableAttachment"/, /NodeType="MultiAttachment"/, /<altgroup\s[^>]*Valence="1"/,
  /<rlogicitem\s[^>]*RLogicGroup="R1"\s+RLogicOccurrence="1-3"\s+RLogicIfThenGroup=""\s+RLogicRestH="yes"/, /BracketUsage="SRU"\s+PolymerRepeatPattern="HeadToHead"/, /Name="bracketusage"/, /Name="polymerrepeat"/,
  /<bracketedgroup\s[^>]*BracketUsage="SRU"/, /<crossingbond/]) assert.match(text, want);
assert.doesNotMatch(text, /RectangleType/, "an R-group box is its alternative group, not a rectangle");
// The same file with Octet's own data gone, as after ChemDraw saves it: the meaning comes back from ChemDraw's fields.
const bare = fromCdxml(text.replace(/ Octet="[^"]*"/g, "").replace(/\n Octet='[^']*'/g, "").replace(/CreationProgram="[^"]*"/, ""));
const chemdraw = bare.mol;
assert.deepEqual(chemdraw.atoms.slice(0, 6).map((a) => [a.text, a.query]), atoms.slice(0, 6).map((a) => [a.text, a.query]));
assert.deepEqual(chemdraw.atoms.filter((a) => a.centre).map((a) => a.centre), atoms.filter((a) => a.centre).map((a) => a.centre));
// (Bonds come back in their drawing order (Z); the bond to the chlorine's connection point, which ChemDraw keeps, is left out.)
assert.deepEqual(chemdraw.bonds.filter((x) => !x.atoms.some((i) => chemdraw.atoms[i].attach)).slice(0, 4).map((x) => [x.query, x.topology, x.rxn, x.type]), bonds.slice(0, 4).map((x) => [x.query, x.topology, x.rxn, x.type]));
assert.deepEqual(chemdraw.shapes?.map((s) => [s.rgroup, s.polymer]), shapes.map((s) => [s.rgroup, s.polymer]));
// ChemDraw writes every R-Logic field: RLogicRestH="no" is Rest H off.
assert.deepEqual(fromCdxml(text.replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, "").replace('RLogicRestH="yes"', 'RLogicRestH="no"')).mol.shapes?.find((s) => s.rgroup)?.rgroup, { name: "R1", occur: "1-3" });
// ChemDraw keeps the connection point Octet wrote for the chlorine: it comes back as the chlorine's attachment mark.
assert.equal(chemdraw.atoms.length, atoms.length + 1);
const cl = chemdraw.atoms.findIndex((a) => a.label === "Cl");
assert.ok(chemdraw.bonds.some((x) => x.atoms.includes(cl) && chemdraw.atoms[x.atoms[0] === cl ? x.atoms[1] : x.atoms[0]].attach));
console.log("query.check: CDXML ok");

// ChemDraw's own bracket meaning: a multiple group with its count in a tag, a parameterizable bracket, a component.
const cdxml = (inner: string) => `<?xml version="1.0"?><CDXML BondLength="14.4"><page id="1" BoundingBox="0 0 540 720"><fragment id="2"><n id="3" p="100 100"/><n id="4" p="114 100"/><b id="5" B="3" E="4"/></fragment>${inner}</page></CDXML>`;
const pair = (attrs: string, kids: string) => `<graphic id="10" BoundingBox="95 110 95 90" GraphicType="Bracket" BracketType="Square"${attrs}>${kids}</graphic><graphic id="11" BoundingBox="119 90 119 110" GraphicType="Bracket" BracketType="Square"/>`;
const tag = (name: string, t: string) => `<objecttag id="7" TagType="Unknown" Name="${name}"><t p="0 0"><s font="3" size="7.5">${t}</s></t></objecttag>`;
assert.deepEqual(fromCdxml(cdxml(pair(' BracketUsage="MultipleGroup"', tag("bracketusage", "3")))).mol.shapes?.[0].polymer, { usage: "mult", label: "3" });
assert.deepEqual(fromCdxml(cdxml(pair(' BracketUsage="MultipleGroup"', tag("parameterizedBracketLabel", "2-4") + tag("molecularWeightOverride", "200")))).mol.shapes?.[0].polymer, { usage: "param", label: "2-4", mw: 200 });
assert.deepEqual(fromCdxml(cdxml(pair(' BracketUsage="Component"', tag("bracketusage", "c2")))).mol.shapes?.[0].polymer, { usage: "c", order: 2 });
assert.deepEqual(fromCdxml(cdxml(pair(' BracketUsage="CopolymerAlternating" PolymerFlipType="Flip"', ""))).mol.shapes?.[0].polymer, { usage: "alt", flip: "flip" });
// A bracketed group with no usage (ChemDraw's Unspecified) stays on its brackets and is written back round the atoms
// inside; brackets with no group stay plain.
const unspecified = fromCdxml(cdxml(pair("", "") + '<bracketedgroup id="12" BracketedObjectIDs="3 4"><bracketattachment id="13" GraphicID="10"/><bracketattachment id="14" GraphicID="11"/></bracketedgroup>'));
assert.deepEqual([unspecified.lost, unspecified.mol.shapes?.map((s) => [s.bracketed, s.polymer])], [{}, [[true, undefined]]]);
const unspecifiedText = toCdxml(unspecified.mol, unspecified.style);
assert.match(unspecifiedText, /<bracketedgroup\s+id="\d+"\s+BracketedObjectIDs="\d+ \d+"\s*>/);
assert.equal(fromCdxml(unspecifiedText).mol.shapes?.[0].bracketed, true);
assert.equal(parse(serialize(unspecified.mol)).shapes?.[0].bracketed, true);
assert.equal(fromCdxml(cdxml(pair("", ""))).mol.shapes?.[0].bracketed, undefined);
// The corpus's own bracketed group (a multiple group of 1) reads with its count, and is no longer reported lost.
const corpus = `${process.env.HOME}/octet-research/corpus/sam/R+D figure 1 copy.cdxml`;
try {
  const r = fromCdxml(readFileSync(corpus, "utf8"));
  assert.ok(!("bracket meaning" in r.lost));
  assert.deepEqual(r.mol.shapes?.filter((s) => s.polymer).map((s) => s.polymer), [{ usage: "param", label: "n" }], "a multiple group with a parameterized label is parameterizable");
} catch (e) { if ((e as { code?: string }).code !== "ENOENT") throw e; }
console.log("query.check: ChemDraw bracket meanings ok");

// MOL V3000: written by Octet, and read back by Octet with every MDL query feature kept.
const mol = writeV3000(drawing);
assert.ok(isQueryMolfile(mol));
for (const want of [/^M {2}V30 1 C [-\d.]+ [-\d.]+ [-\d.]+ 0 HCOUNT=-1 SUBST=3 RBCNT=2 UNSAT=1 EXACHG=1 INVRET=2$/m, / SUBST=-2/, /^M {2}V30 \d+ R# .* RGROUPS=\(1 1\)/m, /^M {2}V30 \d+ \[Cl,Br,I\] /m,
  /^M {2}V30 \d+ 5 1 2 TOPO=1 RXCTR=4$/m, /^M {2}V30 \d+ 8 2 3 RXCTR=2$/m, /^M {2}V30 \d+ 7 2 4 TOPO=2$/m, /^M {2}V30 \d+ 6 1 5$/m, /ENDPTS=\(3 7 8 9\) ATTACH=ANY/, /ENDPTS=\(5 15 16 17 18 19\) ATTACH=ALL/,
  /^M {2}V30 LINKNODE 1 3 2 5 1 5 6$/m, /^M {2}V30 1 SRU 0 ATOMS=\(2 \d+ \d+\) XBONDS=\(2 \d+ \d+\) BRKXYZ=/m, /CONNECT=HH/, /^M {2}V30 BEGIN RGROUP 1$/m, /^M {2}V30 RLOGIC 0 1 1-3$/m,
  /^M {2}V30 BEGIN RGROUP 2$/m, /ATTCHPT=1/]) assert.match(mol.replace(/-\nM {2}V30 /g, ""), want);
assert.ok(mol.split("\n").every((l) => l.length <= 80), "no line over 80 characters");
const back = readV3000(mol);
// The anonymous alternative group came back as an R-group of its own (MOL has none); the rest as drawn.
assert.equal(back.atoms[5].text, "R2");
assert.deepEqual(back.atoms.slice(0, 5).map((a) => [a.label, a.text]), atoms.slice(0, 5).map((a) => [a.label, a.text]));
assert.deepEqual(back.atoms[0].query, { subst: { kind: "exactly", n: 3 }, noH: true, rings: "simple", unsat: "present", change: true, stereo: "retention" }, "what MDL can hold of atom 0");
assert.deepEqual(back.atoms[1].query, { subst: { kind: "free", n: 0 } });
assert.deepEqual(back.bonds.slice(0, 4).map((x) => [x.query, x.topology, x.rxn, x.type]), bonds.slice(0, 4).map((x) => [x.query, x.topology, x.rxn, x.type]));
assert.deepEqual(back.atoms.filter((a) => a.centre).map((a) => a.centre), atoms.filter((a) => a.centre).map((a) => a.centre));
assert.deepEqual(back.shapes?.filter((s) => s.polymer).map((s) => s.polymer), [{ usage: "sru", pattern: "hh" }]);
assert.deepEqual(back.shapes?.filter((s) => s.rgroup).map((s) => s.rgroup), [{ name: "R1", occur: "1-3", restH: true }, { name: "R2" }]);
// Read back, the drawing writes the same molfile again (the R-groups' fragments laid out afresh).
const placeless = (t: string) => t.replace(/-\nM {2}V30 /g, "").replace(/^(M {2}V30 \d+ \S+) [-\d.]+ [-\d.]+ [-\d.]+/gm, "$1").replace(/BRKXYZ=\([^)]*\)/g, "");
assert.equal(placeless(writeV3000(back)), placeless(mol), "a second round trip is stable");
console.log("query.check: MOL V3000 ok");

// Chemistry (Indigo, as chem.check.ts loads it): polymers count their repeat units, attachments their atoms, and a
// query structure's molfile is Octet's V3000, which reads back as a query.
{
  const g = globalThis as Record<string, unknown>;
  g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
  g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
  g.window = globalThis;
  g.self = { location: { origin: "file://" } };
  g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
  const { analyse, importStructure, ready, structures, toMolfile } = await import("./chem.ts");
  await ready;
  const pe: Mol = { atoms: [A("C", 0, 0), A("C", 1, 0), A("C", 2, 0), A("C", 3, 0)], bonds: [b(0, 1), b(1, 2), b(2, 3)], shapes: [{ id: 1, kind: "brackets", from: [0.5, 0.6], to: [2.5, -0.6], polymer: { usage: "sru" } }] };
  const formula = (m: Mol) => analyse(m)?.map((a) => a.formula);
  assert.deepEqual(formula(pe), ["(C2H4)n"], "polyethylene drawn with open ends is (C2H4)n");
  const a = analyse(pe)![0];
  assert.ok(Math.abs(a.repeat!.weight - 28.05) < 0.01 && !a.repeat!.ends, "its repeat unit's mass");
  assert.equal(massText(a, "weight", 2), "(28.05)n");
  // An end group (OH at one end, the chain going on at the other) is counted apart.
  const ended: Mol = { ...pe, atoms: [...pe.atoms.slice(0, 3), A("O", 3, 0)], bonds: pe.bonds };
  assert.deepEqual(formula(ended), ["HO(C2H4)n"], "–[CH2CH2]n–OH");
  assert.equal(massText(analyse(ended)![0], "weight", 2), "17.01 + (28.05)n");
  // A substituent drawn out past the box (polystyrene's Ph above it) is in the repeat unit, as ChemDraw counts it; so
  // is the Ph of the corpus file's polystyrene, which ChemDraw lists in its bracketed group.
  const ps: Mol = { atoms: [A("C", 0, 0), A("C", 1, 0.5), A("C", 2, 0), A("C", 3, 0.5), A("C", 1, 1.5, { text: "Ph" })], bonds: [b(0, 1), b(1, 2), b(2, 3), b(1, 4)],
    shapes: [{ id: 1, kind: "brackets", from: [0.5, 0.9], to: [2.5, -0.4], polymer: { usage: "sru" } }] };
  assert.deepEqual(enclosed(ps, ps.shapes![0]), { atoms: [1, 2, 4], crossing: [0, 2] });
  assert.deepEqual(formula(ps), ["(C8H8)n"]);
  assert.match(toMolfile(ps).replace(/-\nM {2}V30 /g, ""), /SRU 0 ATOMS=\(8 /, "the SRU holds the Ph's atoms too");
  try { assert.deepEqual(formula(fromCdxml(readFileSync(corpus, "utf8")).mol), ["(C8H8)n"]); } catch (e) { if ((e as { code?: string }).code !== "ENOENT") throw e; }
  // A multiple group of 3 and a parameterizable bracket with an Mw multiply out.
  assert.deepEqual(formula({ ...pe, shapes: [{ ...pe.shapes![0], polymer: { usage: "mult", label: "3" } }] }), ["C8H18"], "CH3(CH2CH2)3CH3");
  const benzene: Mol = { atoms: ring(0, 0, 6), bonds: [b(0, 1, { type: 2 }), b(1, 2), b(2, 3, { type: 2 }), b(3, 4), b(4, 5, { type: 2 }), b(5, 0)], shapes: [{ id: 1, kind: "brackets", from: [-1.5, 1.5], to: [1.5, -1.5], polymer: { usage: "param", mw: 200 } }] };
  const p200 = analyse(benzene)![0];
  assert.ok(Math.abs(p200.weight - 200) < 1e-6 && p200.formula === "C15.36H15.36", `ChemDraw's example: Mw 200 on benzene is C15.36H15.36 (${p200.formula})`);
  assert.equal(structures(pe)?.[0]?.formula, "(C2H4)n", "the Properties panel too");
  // A variable attachment counts as a substituent on its ring (bromobenzene); a multi-centre one is left out.
  assert.deepEqual(formula(subset(drawing, new Set([6, 7, 8, 9, 10, 11, 12, 13]))), ["C6H5Br"]);
  // A query structure's molfile is V3000 by Octet, and pastes back as a query.
  const molfile = toMolfile(subset(drawing, new Set([0, 1, 2, 3, 4, 5])));
  assert.match(molfile, /V3000/);
  assert.match(molfile, /HCOUNT=-1/);
  const pasted = importStructure(molfile);
  assert.deepEqual(pasted.atoms[0].query?.noH, true);
  assert.equal(pasted.bonds[0].query, "sd");
  // Its OMe alternative is drawn out as atoms in its R-group.
  assert.match(molfile, /BEGIN RGROUP 2[\s\S]*M {2}V30 \d+ O [\s\S]*END RGROUP/);
  // A V2000 query molfile (an R-group, an atom list, a substitution count, an S/D bond) keeps its query too.
  const v2000 = ["", "  test", "", "  4  3  0  0  0  0  0  0  0  0999 V2000",
    "    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0", "    1.0000    0.0000    0.0000 R#  0  0  0  0  0  0  0  0  0  0  0  0",
    "    2.0000    0.0000    0.0000 L   0  0  0  0  0  0  0  0  0  0  0  0", "    3.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0",
    "  1  2  1  0  0  0  0", "  2  3  5  0  0  0  0", "  3  4  1  0  0  1  0", "M  RGP  1   2   1", "M  ALS   3  3 F Cl  Br  I   ", "M  SUB  1   1   2", "M  END"].join("\n");
  const q2 = importStructure(v2000);
  assert.deepEqual(q2.atoms.map((a) => a.text ?? a.label), ["C", "R1", "[Cl,Br,I]", "C"]);
  assert.deepEqual([q2.atoms[0].query, q2.bonds[1].query, q2.bonds[2].topology], [{ subst: { kind: "exactly", n: 2 } }, "sd", "ring"]);
  // Octet's V3000 keeps a written label's charge, and a nonmetal on a metal keeps its drawn hydrogens (P on Pd: VAL=4).
  const pd: Mol = { atoms: [A("Pd", 0, 0), A("P", 1, 0), A("C", 2, 0), A("C", 1, 1), A("C", 1, -1), A("C", -1, 0, { text: "R" }), A("O", 3, 3, { text: "O2", charge: -1 })], bonds: [b(0, 1), b(1, 2), b(1, 3), b(1, 4), b(0, 5)] };
  const pdMol = toMolfile(pd);
  assert.match(pdMol, /^M {2}V30 2 P [-\d.]+ [-\d.]+ [-\d.]+ 0 VAL=4$/m);
  assert.match(pdMol, /^M {2}V30 \d+ O [-\d.]+ [-\d.]+ [-\d.]+ 0 CHG=-1$/m);
  // A plain structure's molfile stays Indigo's.
  assert.match(toMolfile({ atoms: [A("C", 0, 0), A("O", 1, 0)], bonds: [b(0, 1)] }), /-INDIGO-/);
  console.log("query.check: chemistry ok");
}
