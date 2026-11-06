// Run: node src/makeelement.check.ts. Fails loudly if captions stop counting as chemistry the way ChemDraw counts them
// (Sam, 21 October 2026): a caption typed as Rh or CH3OH stays a caption, but with Interpret chemically on (the
// document's and its own) it counts in the formula, the mass, SMILES and the warnings. Make element (or a bond tool)
// makes a caption that reads as a label an atom, in the caption's style and in its groups. ChemDraw's CDXML keeps
// both switches: InterpretChemically on the document and on the text.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fromCdxml, parseXml, toCdxml } from "./cdxml.ts";
import { cdxToXml, xmlToCdx } from "./cdx.ts";
import { onCaptions } from "./check.ts";
import { DEFAULT_STYLE, readStyle } from "./docstyle.ts";
import { addCaption, captionAtom, captionsToAtoms, chemicalCaption, labelable, labelWords, sprout, withCaptionAtoms } from "./edit.ts";
import { parse, serialize } from "./file.ts";
import type { Caption, Mol } from "./render.ts";

const cap = (text: string, more: Partial<Caption> = {}): Caption => ({ id: 1, text, x: 0, y: 0, ...more });
// Elements, labels and formulas read as chemistry; words, numbers and text tied to a structure, an arrow or a cycle do not.
for (const t of ["Rh", "Bi", "K", "Na", "I", "C", "OMe", "NH2", "CH3OH", "MeOH", "NaOCl", "Et3N", "Ph", " Rh "]) assert.ok(labelable(cap(t)), `${t} reads as chemistry`);
for (const t of ["rh", "Rhodium", "reflux", "rt", "1", "2a", "A", "R", "", "Rh Bi", "CH3\nOH"]) assert.ok(!labelable(cap(t)), `${t} is text`);
assert.ok(!labelable(cap("Rh", { under: [0] })) && !labelable(cap("Rh", { on: { arrow: 2, side: "above" } })) && !labelable(cap("Rh", { cycle: { cycle: 3, step: 0, side: "in" } })), "tied text is text");
// It counts as chemistry when the document's Interpret chemically is on and its own is not off.
assert.ok(chemicalCaption(cap("Rh"), true), "Rh counts");
assert.ok(!chemicalCaption(cap("Rh"), false), "not with the document's off");
assert.ok(!chemicalCaption(cap("Rh", { chemical: false }), true), "not with its own off");
assert.ok(!chemicalCaption(cap("reflux"), true), "not text that is not chemistry");

// The chemistry: each chemical caption as a lone atom after the drawing's atoms, at its place. One element symbol is
// that element with no hydrogens; other text is a label.
let d: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [] };
let rhId: number, biId: number, wordId: number, offId: number;
[d, rhId] = addCaption(d, { text: "Rh", x: 2, y: 1 });
[d, wordId] = addCaption(d, { text: "reflux", x: 3, y: 1 });
[d, biId] = addCaption(d, { text: "Bi", x: 4, y: 1 });
[d, offId] = addCaption(d, { text: "CH3OH", x: 5, y: 1, chemical: false });
const read = withCaptionAtoms(d, true);
assert.deepEqual(read.captions, [rhId, biId], "Rh and Bi count; the word and the caption turned off do not");
assert.deepEqual(read.mol.atoms.slice(1), [{ label: "Rh", location: [2, 1, 0], implicitHCount: 0 }, { label: "Bi", location: [4, 1, 0], implicitHCount: 0 }], "Rh and Bi as atoms with no hydrogens");
assert.equal(read.mol.captions, d.captions, "the captions stay");
assert.equal(withCaptionAtoms(d, false).mol, d, "nothing counts with the document's off");
assert.deepEqual(withCaptionAtoms({ ...d, captions: d.captions!.map((c) => (c.id === offId ? { ...c, chemical: undefined } : c)) }, true).mol.atoms[3], { label: "C", location: [5, 1, 0], text: "CH3OH" }, "CH3OH as a label");
void wordId;
// A problem on a caption's atom goes on the caption.
assert.deepEqual(onCaptions([{ type: "valence", atom: 0, message: "x" }, { type: "valence", atom: 2, message: "y" }, { type: "misc", bond: 0, message: "z" }], 1, [rhId, biId]),
  [{ type: "valence", atom: 0, message: "x" }, { type: "valence", caption: biId, message: "y" }, { type: "misc", bond: 0, message: "z" }], "a problem on Bi's atom is on the Bi caption");

// The switches go into CDXML as ChemDraw writes them, and come back: InterpretChemically on the document ("yes" for a
// new document) and "no" on a caption that has its own off. A file without them is on (the spec's default).
const style = { ...DEFAULT_STYLE };
assert.equal(style.interpret, true, "on for new documents");
const xml = toCdxml(d, style);
assert.match(xml, /<CDXML\s[^>]*InterpretChemically="yes"/, "the document's switch");
assert.equal((xml.match(/InterpretChemically="no"/g) ?? []).length, 1, "the caption's own switch, on that caption only");
const back = fromCdxml(xml);
assert.equal(back.style.interpret, true);
assert.deepEqual(back.mol.captions?.map((c) => [c.text, c.chemical]), [["Rh", undefined], ["reflux", undefined], ["Bi", undefined], ["CH3OH", false]], "the caption's switch comes back");
const offXml = toCdxml(d, { ...style, interpret: false });
assert.match(offXml, /<CDXML\s[^>]*InterpretChemically="no"/, "the document's switch off");
assert.equal(fromCdxml(offXml).style.interpret, false, "and back");
assert.equal(fromCdxml(offXml.replace(/(<CDXML\s[^>]*?)\sInterpretChemically="no"/, "$1")).style.interpret, true, "a file that does not say is on");
// Through CDX (decision 0009) too.
const viaCdx = fromCdxml(cdxToXml(xmlToCdx(parseXml(offXml))));
assert.equal(viaCdx.style.interpret, false, "the document's switch through CDX");
assert.deepEqual(viaCdx.mol.captions?.map((c) => c.chemical), [undefined, undefined, undefined, false], "the caption's switch through CDX");
// And in Octet's own file.
const saved = parse(serialize({ ...d, style: { ...style, interpret: false } }));
assert.equal(saved.captions?.find((c) => c.text === "CH3OH")?.chemical, false, "the caption's switch in Octet's file");
assert.equal(readStyle(saved.style).interpret, false, "the document's switch in Octet's file");
assert.equal(readStyle({}).interpret, true, "a style that does not say is on");

// Make element: the atom takes the caption's text, colour, font, size and style; a size or font the same as the
// labels' stays unset.
const s = { ...DEFAULT_STYLE, labelFont: "Arial", labelSize: 10, captionFont: "Arial", captionSize: 10 };
const atomOf = (...args: Parameters<typeof captionAtom>) => JSON.parse(JSON.stringify(captionAtom(...args))); // unset keys left out
const rh = atomOf({ id: 1, text: "Rh", x: 0, y: 0, colour: "#3F6BFF", bold: true }, [1, 2, 0], s);
assert.deepEqual(rh, { label: "Rh", location: [1, 2, 0], colour: "#3F6BFF", bold: true }, "Rh in its caption's colour and weight");
assert.deepEqual(atomOf({ id: 1, text: "Bi", x: 0, y: 0, font: "Helvetica", size: 12, italic: true, underline: true }, [0, 0, 0], s),
  { label: "Bi", location: [0, 0, 0], font: "Helvetica", size: 12, italic: true, underline: true }, "Bi in its caption's font and size");
// A style all of its runs share counts as the caption's own.
assert.deepEqual(atomOf({ id: 1, text: "Pd", x: 0, y: 0, runs: [{ text: "Pd", bold: true, colour: "#213C99", font: "Helvetica" }] }, [0, 0, 0], s),
  { label: "Pd", location: [0, 0, 0], bold: true, colour: "#213C99", font: "Helvetica" }, "Pd in its runs' style");
// A label that is not one element keeps its text, on the element it joins through.
assert.deepEqual(atomOf({ id: 1, text: "OMe", x: 0, y: 0 }, [0, 0, 0], s), { label: "O", location: [0, 0, 0], text: "OMe" }, "OMe as a label");
assert.equal(labelWords({ atoms: [captionAtom({ id: 1, text: "Rh", x: 0, y: 0 }, [0, 0, 0], s)], bonds: [] }, 0), "Rh", "a lone Rh shows Rh");

// The captions go and their atoms come last; an atom goes into each group its caption was in.
let m: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [] };
let a: number, b: number;
[m, a] = addCaption(m, { text: "Bi", x: 2, y: 0 });
[m, b] = addCaption(m, { text: "Rh", x: 4, y: 0 });
m = { ...m, groups: [{ id: 99, atoms: [0], items: [a] }] };
const out = captionsToAtoms(m, [{ id: a, atom: { label: "Bi", location: [2, 0, 0] } }, { id: b, atom: { label: "Rh", location: [4, 0, 0] } }]);
assert.equal(out.captions?.length ?? 0, 0, "the captions go");
assert.deepEqual(out.atoms.map((x) => x.label), ["C", "Bi", "Rh"], "the atoms come after the drawing's");
assert.deepEqual(out.groups, [{ id: 99, atoms: [0, 1], items: [] }], "Bi takes its caption's place in the group");
// A bond joins the two new atoms as it joins any atoms (the Bi-Rh bond Sam could not draw).
const bonded = sprout(out, 1, { type: 1 });
assert.equal(bonded.bonds.length, 1, "a bond from Bi");

// With Indigo: the formula, mass, SMILES and warnings of chemical captions, as for any structure. chem.ts loads
// Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { analyse, ready, toSmiles } = await import("./chem.ts");
const { problems } = await import("./check.ts");
await ready;
const lone = (...texts: string[]) => withCaptionAtoms({ atoms: [], bonds: [], captions: texts.map((text, k) => ({ id: k + 1, text, x: 2 * k, y: 0 })) }, true);
const values = (t: string) => analyse(lone(t).mol)?.map((x) => [x.formula, Math.round(x.weight * 100) / 100]);
assert.deepEqual(values("Rh"), [["Rh", 102.91]], "rhodium");
assert.deepEqual(values("Bi"), [["Bi", 208.98]], "bismuth, with no hydrogens");
assert.deepEqual(values("K"), [["K", 39.1]], "potassium");
assert.deepEqual(values("CH3OH"), [["CH4O", 32.04]], "methanol");
assert.deepEqual(values("NaOCl"), [["ClNaO", 74.44]], "sodium hypochlorite");
assert.deepEqual(analyse(lone("Bi", "Rh").mol)?.map((x) => x.formula), ["Bi", "Rh"], "a row for each caption");
assert.equal(toSmiles(lone("CH3OH").mol), "CO", "SMILES of a formula");
assert.equal(toSmiles(lone("Rh").mol), "[Rh]", "SMILES of an element");
// A caption whose valence is wrong has a valence warning, on the caption.
const bad = lone("CH5", "Rh");
assert.deepEqual(onCaptions(problems(bad.mol), 0, bad.captions).map((p) => [p.type, p.caption]), [["valence", 1]], "CH5 has a valence warning; Rh has none");

console.log("makeelement ok");
