// Run: node src/numbering.check.ts. Fails loudly if compound numbers stop taking roman numerals (issue 34), if Octet
// stops counting them as compound numbers, or if an experiment page stops numbering its compounds in reading order.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fromRoman, nextCompound, numberValue, renumber, romanNumbers, setRoman, toRoman } from "./numbering.ts";
import { isNumber, type Caption, type Mol } from "./render.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { parse, serialize } from "./file.ts";
import { purposeStyle } from "./docstyle.ts";

// Roman numerals both ways, 1 to 3999, and only the usual spellings.
for (const [n, r] of [[1, "I"], [4, "IV"], [9, "IX"], [14, "XIV"], [40, "XL"], [90, "XC"], [400, "CD"], [1994, "MCMXCIV"], [3999, "MMMCMXCIX"]] as const) {
  assert.equal(toRoman(n), r);
  assert.equal(fromRoman(r), n);
}
for (let n = 1; n <= 3999; n++) assert.equal(fromRoman(toRoman(n)), n);
for (const bad of ["", "IIII", "VX", "IC", "MMMM", "iv", "I V", "X".repeat(40)]) assert.equal(fromRoman(bad), undefined, bad);
assert.equal(toRoman(0), "0");
assert.equal(numberValue("12"), 12);
assert.equal(numberValue("XII"), 12);
assert.equal(numberValue("3a"), undefined, "a number with a letter is not a plain number");

// Three structures in a row, A then B then C from the left, and a second row under them.
const at = (x: number, y = 0) => ({ label: "C", location: [x, y, 0] as [number, number, number] });
const atoms = [at(0), at(1), at(10), at(11), at(20), at(0, -8)];
const num = (id: number, text: string, under: number[]): Caption => ({ id, text, bold: true, under, x: 0, y: 0 });
const drawing = (...captions: Caption[]): Mol => ({ atoms, bonds: [{ atoms: [0, 1], type: 1 }, { atoms: [2, 3], type: 1 }] as Mol["bonds"], captions });

// A roman numeral under a structure is a compound number (placed first under it, written as one); the same text as
// free bold text is not.
assert.ok(isNumber(num(1, "IV", [0])) && isNumber(num(1, "IIa", [0])) && isNumber(num(1, "4", [0])));
assert.ok(!isNumber({ id: 1, text: "C", bold: true, x: 0, y: 0 }), "a bold C heading is not 100");
assert.ok(!isNumber(num(1, "Procedure", [0])));

// The style follows the numbers: all roman is roman, any arabic is arabic, none is arabic.
assert.equal(romanNumbers(drawing(num(1, "I", [0]), num(2, "II", [2]))), true);
assert.equal(romanNumbers(drawing(num(1, "I", [0]), num(2, "2", [2]))), false);
assert.equal(romanNumbers(drawing()), false);
assert.equal(nextCompound(drawing()), "1");
assert.equal(nextCompound(drawing(num(1, "I", [0]), num(2, "II", [2]))), "III");
assert.equal(nextCompound(drawing(num(1, "1", [0]), num(2, "2a", [2]))), "3");
assert.equal(nextCompound(drawing(num(1, "1", [0]), { id: 2, text: "C", bold: true, x: 0, y: 0 })), "2", "a bold heading does not count");

// Use roman numerals and back: plain numbers change, 3a and other text stay.
{
  const m = drawing(num(1, "1", [0]), num(2, "2", [2]), num(3, "3a", [4]), { id: 4, text: "Procedure", bold: true, x: 0, y: 0 });
  const roman = setRoman(m, true);
  assert.deepEqual(roman.captions!.map((c) => c.text), ["I", "II", "3a", "Procedure"]);
  assert.equal(romanNumbers(roman), true);
  assert.deepEqual(setRoman(roman, false).captions!.map((c) => c.text), ["1", "2", "3a", "Procedure"]);
  assert.equal(setRoman(drawing(), true).captions?.length, 0);
}

// On an experiment page the numbers Octet gave (Number these compounds: auto) follow the compounds in reading order:
// the row at the top from the left, then the next row. Moving a compound renumbers; a drawing already in order comes
// back as it was.
const auto = (id: number, text: string, under: number[]): Caption => ({ ...num(id, text, under), auto: true });
{
  const m = drawing(auto(1, "2", [0, 1]), auto(2, "1", [2, 3]), auto(3, "4", [5]), auto(4, "3", [4]), num(5, "1a", [4]));
  const next = renumber(m);
  assert.deepEqual(next.captions!.map((c) => c.text), ["1", "2", "4", "3", "1a"]);
  assert.equal(renumber(next), next, "nothing to change: the same drawing");
  const roman = renumber(setRoman(m, true));
  assert.deepEqual(roman.captions!.map((c) => c.text), ["I", "II", "IV", "III", "1a"]);
  // The first structure moved to the right of the others: it is numbered last of its row.
  const moved = renumber({ ...next, atoms: next.atoms.map((a, i) => (i < 2 ? { ...a, location: [a.location[0] + 30, a.location[1], 0] as [number, number, number] } : a)) });
  assert.deepEqual(moved.captions!.map((c) => c.text), ["3", "1", "4", "2", "1a"]);
}

// The user's own numbers are never changed: typed numbers (23 and 24 to match a thesis) stay, and Octet's numbers go
// round them. Octet's numbers after the user's start one past the user's numbers before them.
{
  const m = drawing(num(1, "24", [0, 1]), num(2, "23", [2, 3]));
  assert.equal(renumber(m), m, "the user's numbers stay as typed");
  const mixed = drawing(num(1, "24", [0, 1]), num(2, "23", [2, 3]), auto(3, "26", [5]), auto(4, "25", [4]));
  assert.deepEqual(renumber(mixed).captions!.map((c) => c.text), ["24", "23", "26", "25"], "Octet's follow on from the user's, in reading order");
  // Octet's numbers with none of the user's before them start at 1 and skip the number the user holds (2). 3a stays.
  const round = drawing(auto(1, "3", [0, 1]), num(2, "2", [2, 3]), auto(3, "1", [4]), num(4, "3a", [5]));
  assert.deepEqual(renumber(round).captions!.map((c) => c.text), ["1", "2", "3", "3a"]);
}

// A file from Octet 1.1.0 has no mark on its numbers, so they are all the user's: an edit leaves them as they were.
{
  const old = '{"format":"octet","version":1,"app":"1.1.0","structure":{"atoms":[{"label":"C","x":0,"y":0},{"label":"C","x":10,"y":0}],"bonds":[]},' +
    '"captions":[{"text":"2","x":0,"y":-1,"bold":true,"under":[0]},{"text":"1","x":10,"y":-1,"bold":true,"under":[1]}]}';
  const m = parse(old);
  assert.equal(renumber(m), m, "a 1.1.0 file keeps its numbers");
  assert.ok(m.captions!.every((c) => !c.auto));
}

// Octet's mark survives saving: .oct and CDXML give it back, so the numbers keep following the compounds.
{
  const m = drawing(auto(1, "1", [0, 1]), num(2, "7", [2, 3]));
  assert.deepEqual(parse(serialize(m)).captions!.map((c) => [c.text, !!c.auto]), [["1", true], ["7", false]]);
  const back = fromCdxml(toCdxml(m, purposeStyle("experiment"))).mol;
  assert.deepEqual(back.captions!.map((c) => [c.text, !!c.auto]).sort(), [["1", true], ["7", false]]);
}

// Compounds labelled with letters (A, B, C, D) keep them: C and D are letters there, not 100 and 500.
{
  const m = drawing(num(1, "A", [0, 1]), num(2, "B", [2, 3]), num(3, "C", [4]), num(4, "D", [5]));
  assert.equal(renumber(m), m, "letters are not renumbered");
  assert.equal(romanNumbers(m), false);
  assert.equal(nextCompound(m), "1");
  assert.equal(setRoman(m, true), m);
  assert.equal(nextCompound(drawing(num(1, "C", [0]))), "CI", "a C alone is still a numeral");
}

// The numbers are ordinary text, so every format keeps them: .oct and CDXML give the roman numerals back under their
// structures.
{
  const m = setRoman(drawing(num(1, "1", [0, 1]), num(2, "2", [2, 3])), true);
  assert.deepEqual(parse(serialize(m)).captions!.map((c) => [c.text, c.under]), [["I", [0, 1]], ["II", [2, 3]]]);
  const back = fromCdxml(toCdxml(m, purposeStyle("experiment"))).mol;
  assert.deepEqual(back.captions!.map((c) => c.text).sort(), ["I", "II"]);
  assert.equal(romanNumbers(back), true);
}

// The editor numbers new compounds with nextCompound, renumbers an experiment page as it changes, and offers the
// numerals where Number these compounds is.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), actions = readFileSync(new URL("Actions.tsx", import.meta.url), "utf8");
assert.match(editor, /text: nextCompound\(m\), x: 0, y: 0, bold: true, under: g, auto: true/);
// A number edited by hand becomes the user's: committing new text drops Octet's mark.
assert.match(editor, /updateCaption\(doc, w\.id, \{ text, \.\.\.st, runs, \.\.\.\(text !== old\.text \? \{ auto: undefined \} : \{\}\) \}\)/);
assert.match(editor, /expPage && mol\.style === doc\.style \? renumber\(newGrids\(doc, ordered\)\) : ordered/);
assert.match(editor, /command === "numbers\.roman"\) return set\(setRoman\(doc, !romanNumbers\(doc\)\), true\)/);
assert.equal(actions.match(/\.\.\.numerals\(context\.roman\)/g)?.length, 2, "on a structure and on a reaction");

console.log("numbering: ok");
