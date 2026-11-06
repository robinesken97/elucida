// Run: node src/textcolour.check.ts. Fails loudly if a colour chosen while typing is lost when the text box closes, or
// on save and open (.oct, CDXML with a colour on each <s> run, CDX).
import assert from "node:assert/strict";
import { fromCdxml, parseXml, toCdxml } from "./cdxml.ts";
import { cdxToXml, xmlToCdx } from "./cdx.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { parse, serialize } from "./file.ts";
import { readCdx, readOct, writeCdx, writeOct } from "./oct.ts";
import { common, edited, normalise, runsOf, shareColour, styleRange, type TextRun } from "./richtext.ts";
import type { Caption, Mol } from "./render.ts";

const RED = "#B42323", BLUE = "#3F6BFF", INK = "#000000";
const red = (s: object) => ({ ...s, colour: RED });

// While typing: the characters selected take the colour (a run of their own), and the panel reads it back.
const typed: TextRun[] = [{ text: "Part red here" }];
const part = styleRange(typed, 5, 8, red);
assert.deepEqual(part, [{ text: "Part " }, { text: "red", colour: RED }, { text: " here" }]);
assert.equal(common(part, 5, 8).colour, RED);
assert.equal(common(part, 0, 13).colour, undefined, "mixed colours show none");
// Nothing selected: the colour waits for the next characters typed (pending), as Bold does.
assert.deepEqual(edited([{ text: "Next " }], "Next red", { colour: RED }), [{ text: "Next " }, { text: "red", colour: RED }]);
// Colour on styled text keeps its bold, italic and subscript.
const formula = styleRange([{ text: "H" }, { text: "2", script: "sub" }, { text: "O and " }, { text: "CO2", italic: true }], 0, 3, red);
assert.deepEqual(formula.slice(0, 3), [{ text: "H", colour: RED }, { text: "2", script: "sub", colour: RED }, { text: "O", colour: RED }]);
assert.deepEqual(formula.at(-1), { text: "CO2", italic: true });

// When the box closes (shareColour): a colour all the text has becomes the caption's own colour, so it is the same as
// a colour chosen for the whole picked caption.
assert.deepEqual(shareColour(styleRange(typed, 0, 13, red), undefined, INK), { colour: RED, runs: undefined });
assert.deepEqual(shareColour(edited([{ text: "" }], "All red", { colour: RED }), undefined, INK), { colour: RED, runs: undefined });
// Other styles stay in the runs.
assert.deepEqual(shareColour([{ text: "H", colour: RED }, { text: "2", script: "sub", colour: RED }], undefined, INK), { colour: RED, runs: [{ text: "H" }, { text: "2", script: "sub" }] });
// A part in another colour stays on its run; the caption keeps its own colour.
assert.deepEqual(shareColour(part, undefined, INK), { colour: undefined, runs: part });
assert.deepEqual(shareColour([{ text: "a" }, { text: "b", colour: INK }], RED, INK), { colour: RED, runs: [{ text: "a" }, { text: "b", colour: INK }] });
// Every run back in the ink: no colour at all.
assert.deepEqual(shareColour([{ text: "a", colour: INK }, { text: "b", colour: INK }], RED, INK), { colour: undefined, runs: undefined });
// The caption's own colour, with runs that have none of their own, is kept as it is.
assert.deepEqual(shareColour([{ text: "a" }, { text: "b", bold: true }], BLUE, INK), { colour: BLUE, runs: [{ text: "a" }, { text: "b", bold: true }] });
assert.deepEqual(shareColour(undefined, BLUE, INK), { colour: BLUE, runs: undefined });
console.log("textcolour.check: typing ok");

// Save and open: .oct (Octet's JSON and its CDXML), CDXML and CDX keep each run's colour and the caption's.
const captions: Caption[] = [
  { id: 1, text: "Part red here", x: 0, y: 2, align: "left", runs: part },
  { id: 2, text: "Whole red", x: 0, y: 0, align: "left", colour: RED },
  { id: 3, text: "H2O and CO2", x: 0, y: -2, align: "left", runs: [{ text: "H", colour: RED }, { text: "2", script: "sub", colour: RED }, { text: "O and " }, { text: "CO2", italic: true, colour: BLUE }] },
  // A red caption with a black word: the word keeps its black.
  { id: 4, text: "red black", x: 0, y: -4, align: "left", colour: RED, runs: [{ text: "red " }, { text: "black", colour: INK }] },
];
const mol: Mol = { atoms: [], bonds: [], captions };
const look = (m: Mol) => (m.captions ?? []).map((c) => ({ text: c.text, colour: c.colour, runs: c.runs }));
const want = look(mol);
assert.deepEqual(look(parse(serialize(mol))), want, ".oct JSON");
const cdxml = toCdxml(mol, DEFAULT_STYLE, { name: "check.cdxml" });
// Each run carries its colour on its <s> (ChemDraw's per-character colour): red is in the colour table.
const reds = [...cdxml.matchAll(/<color r="([\d.]+)" g="([\d.]+)" b="([\d.]+)"\/>/g)].findIndex((m) => m[1] === "0.7059" && m[2] === "0.1373" && m[3] === "0.1373") + 2;
assert.ok(reds > 2, "red in the colour table");
assert.ok(new RegExp(`<s [^>]*color="${reds}"[^>]*>red</s>`).test(cdxml), "a red run");
assert.ok(/<s [^>]*color="0"[^>]*>black<\/s>/.test(cdxml), "a black run in a red caption");
assert.deepEqual(look(fromCdxml(cdxml).mol), want, "CDXML");
assert.deepEqual(look(readOct(writeOct(mol, DEFAULT_STYLE)).mol), want, ".oct");
assert.deepEqual(look(readCdx(writeCdx(mol, DEFAULT_STYLE)).mol), want, "Octet's .cdx");
// ChemDraw's CDX alone keeps each character's colour; a colour all the runs do not share is kept on the runs.
const inks = (m: Mol) => (m.captions ?? []).map((c) => normalise(runsOf(c).map((r) => ({ text: r.text, colour: (r.colour ?? c.colour ?? INK).toUpperCase() }))));
assert.deepEqual(inks(fromCdxml(cdxToXml(xmlToCdx(parseXml(cdxml)))).mol), inks(mol), "CDX");
// The .oct's CDXML alone (as after ChemDraw saves over it): the colours are read from the runs.
assert.deepEqual(look(readOct(cdxml).mol), want, ".oct as CDXML");
console.log("textcolour.check: files ok");
