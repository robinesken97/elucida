// Run: node src/oct.check.ts. Fails loudly if a .oct file stops coming back exactly, or trusts a changed one.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { addArrow, addCaption, addRing, EMPTY } from "./edit.ts";
import { toCdxml } from "./cdxml.ts";
import { parse, serialize } from "./file.ts";
import { isDrawingText, lostText, readOct, writeOct } from "./oct.ts";

let mol = addRing(EMPTY, 6, false, { point: [0, 0] });
[mol] = addCaption(mol, { text: "Café 5 °C -- über", x: 0, y: -3 });
[mol] = addArrow(mol, { kind: "reaction", from: [3, 0], to: [6, 0] });
mol = { ...mol, atoms: mol.atoms.map((a, i) => (i === 0 ? { ...a, isotope: 13, location: [a.location[0] + 0.123456, a.location[1], 0] } : a)) };
const style = { ...DEFAULT_STYLE, labelSize: 12 };
const file = writeOct(mol, style);
// Export reuses the CDXML it made for CDXML or PDF: the file is the same.
assert.equal(writeOct(mol, style, {}, toCdxml(mol, style)), file);
// ChemDraw reads the CDXML part; Octet gets its own drawing back exactly, coordinates and all.
assert.match(file, /^<\?xml[^]*<\/CDXML>\n<!--Octet 1 [0-9a-f]{16} [A-Za-z0-9+/=]+-->\n$/);
const back = readOct(file);
assert.equal(serialize(back.mol), serialize(parse(serialize({ ...mol, style }))));
assert.deepEqual(back.lost, {});
// Another program changed the CDXML (here a label size): Octet reads the CDXML, not its stale copy.
const edited = readOct(file.replace('LabelSize="12"', 'LabelSize="14"'));
assert.equal(edited.mol.style?.labelSize, 14);
// A damaged copy falls back to the CDXML; an old .octet file is the JSON alone.
assert.equal(readOct(file.replace(/ ([A-Za-z0-9+/=]{8})/, " AAAA$1")).mol.atoms.length, 6);
assert.equal(readOct(serialize(mol)).mol.atoms.length, 6);
// The copy kept for recovery (REL-1) is that JSON with the style: it comes back as the .oct does.
assert.equal(serialize(readOct(serialize({ ...mol, style })).mol), serialize(back.mol));
// A ChemDraw file with a picture Octet cannot hold: it is counted, so Save asks before it writes over the file (REL-11).
const picture = readOct(writeOct(mol, style).replace(/<!--Octet[^]*$/, "").replace("</page>", '<embeddedobject id="9001" BoundingBox="0 0 10 10"/></page>'));
assert.deepEqual(picture.lost, { picture: 1 });
assert.equal(picture.foreign, true);
assert.equal(lostText(picture.lost), "1 picture");
assert.equal(lostText({ annotation: 6, "rotated shape": 1, "bond highlight": 2 }), "6 annotations, 1 rotated shape and 2 bond highlights");
assert.equal(lostText({}), "");
// Files opened from Finder or dropped on the window: drawings go to readOct, structure files to Indigo.
assert.ok(isDrawingText(file) && isDrawingText('{"atoms":[],"bonds":[]}') && isDrawingText('<?xml version="1.0"?>\n<CDXML>'));
assert.ok(!isDrawingText("\n  Octet\n\n  1  0  0  0  0  0  0  0  0  0999 V2000\nM  END\n") && !isDrawingText("CCO") && !isDrawingText("c1ccccc1 benzene <CDXMLX>"));
// What the window showed (View > Show Grid, Show Rulers, Show Crosshair) comes back with the drawing.
const guides = { rulers: true as const, crosshair: [1, -0.5] as [number, number] };
assert.deepEqual(readOct(writeOct({ ...mol, guides }, style)).mol.guides, guides);
assert.equal(readOct(file).mol.guides, undefined);
// Issue 19: ChemDraw 25.5 for Windows drops Octet's comment and Octet="…" attributes when it saves, and writes its own
// CreationProgram. A .oct file, or a file with Octet's comment still in it, that ChemDraw saved last says so once.
const chemDraw = (t: string) => t.replace(/<!--Octet[^]*$/, "").replace(/ Octet="[^"]*"/g, "").replace(/CreationProgram="[^"]*"/, 'CreationProgram="ChemDraw 25.5.0.5789"');
const resaved = chemDraw(file);
assert.equal(readOct(resaved, true).resaved, true, "a .oct that ChemDraw saved");
assert.equal(readOct(resaved, true).mol.atoms.length, 6, "it still opens, from the CDXML");
assert.equal(readOct(resaved).resaved, undefined, "a .cdxml with no trace of Octet is ChemDraw's own file");
assert.equal(readOct(`${resaved}${file.slice(file.lastIndexOf("<!--Octet"))}`).resaved, true, "Octet's comment kept, the CDXML changed by ChemDraw");
assert.equal(readOct(file, true).resaved, undefined, "Octet's own file, unchanged");
assert.equal(readOct(file.replace('LabelSize="12"', 'LabelSize="14"'), true).resaved, undefined, "changed by a program other than ChemDraw");
assert.equal(readOct(toCdxml(mol, style), true).resaved, undefined, "a .oct with no comment that Octet saved last");
assert.equal(readOct(file.replace(/\n/g, "\r\n"), true).resaved, undefined, "line ends changed, so the hash does not match, by a program other than ChemDraw");
assert.equal(readOct(resaved.replace(' CreationProgram="ChemDraw 25.5.0.5789"', "").replace("<CDXML\n", '<CDXML\t\n Foo="1"\n CreationProgram="ChemDraw 26.1.0.12"\n'), true).resaved, true, "the program in any place in the CDXML element");
// The program is read from the CDXML element only, and fast on a hostile file.
assert.equal(readOct(resaved.replace('CreationProgram="ChemDraw 25.5.0.5789"', 'CreationProgram="Octet"').replace("</CDXML>", '<t CreationProgram="ChemDraw"/></CDXML>'), true).resaved, undefined);
const t0 = performance.now();
try { readOct(`<CDXML ${' CreationProgram="'.repeat(4000)}`, true); } catch { /* not a drawing */ }
assert.ok(performance.now() - t0 < 1000);
// The editor reads the file's name and says it once, as it opens the file.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /read = readOct\(text, \/\\\.oct\$\/i\.test\(path \?\? ""\)\)/);
assert.match(editor, /if \(read\.resaved\) setNotice\(`ChemDraw saved this file last and did not keep Octet's own extras\./);
// With things Octet left out, it stays an error, as sayLost's notice is.
assert.match(editor, /extras\.\$\{left \? ` Octet left out \$\{lostText\(lost\)\}\.` : ""\}`, left \? "error" : "info"\)/);
console.log("oct.check: ok");
