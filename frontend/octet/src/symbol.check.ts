// Run: node src/symbol.check.ts. Fails loudly if Octet reads ChemDraw's Symbol font runs (Greek, arrows and maths
// written as Latin bytes in the Symbol font) as anything but the characters ChemDraw draws, through CDXML and CDX,
// in captions, atom labels, R-group titles and bracket labels, or writes them back as anything but Unicode (issue 21).
import assert from "node:assert/strict";
import { isSymbolFont, symbolText } from "./charset.ts";
import { MAGIC, cdxToXml, xmlToCdx } from "./cdx.ts";
import { fromCdxml, parseXml, toCdxml, type Xml } from "./cdxml.ts";
import { readCdx, writeCdx } from "./oct.ts";
import type { Mol } from "./render.ts";

// A ChemDraw document with Arial (3), Times New Roman (4) and a Symbol font (5) in the given charset.
const doc = (body: string, charset = "iso-8859-1", symbol = "Symbol", root = "") => `<?xml version="1.0" encoding="UTF-8" ?>
<CDXML BondLength="14.4" LabelFont="3" LabelSize="10" CaptionFont="3" CaptionSize="10"${root}><fonttable>
<font id="3" charset="iso-8859-1" name="Arial"/><font id="4" charset="iso-8859-1" name="Times New Roman"/><font id="5" charset="${charset}" name="${symbol}"/>
</fonttable><page id="1" BoundingBox="0 0 540 720">${body}</page></CDXML>`;
const s = (font: number, text: string, more = "") => `<s font="${font}" size="10" face="0"${more}>${text}</s>`;
const caption = (...runs: string[]) => `<t id="9" p="100 100">${runs.join("")}</t>`;
const read = (cdxml: string) => fromCdxml(cdxml);
const textOf = (cdxml: string) => read(cdxml).mol.captions![0].text;

// 1. A Symbol run reads as the characters ChemDraw draws.
assert.equal(textOf(doc(caption(s(3, "h"), s(5, "n")))), "hν");
assert.equal(textOf(doc(caption(s(5, "d"), s(3, "+")))), "δ+");
assert.equal(textOf(doc(caption(s(5, "D"), s(3, "T")))), "ΔT");
assert.equal(textOf(doc(caption(s(5, "b"), s(3, "-D-Glucopyranose")))), "β-D-Glucopyranose");
// All in Symbol, h is η: the issue's control.
assert.equal(textOf(doc(caption(s(5, "hn")))), "ην");
assert.equal(textOf(doc(caption(s(5, "-")))), "−");
assert.equal(textOf(doc(caption(s(5, "abgDWm")))), "αβγΔΩμ");
// The Symbol family by name, and nothing else.
for (const name of ["Symbol", "SymbolMT", "Symbol MT", "symbol", "Standard Symbols PS", "StandardSymL"]) assert.equal(textOf(doc(caption(s(3, "h"), s(5, "n")), "iso-8859-1", name)), "hν", name);
for (const name of ["Symbolic", "Symbol2", "Segoe UI Symbol", "Wingdings"]) assert.equal(textOf(doc(caption(s(3, "h"), s(5, "n")), "iso-8859-1", name)), "hn", name);
assert.equal(isSymbolFont(undefined), false);

// 2. Characters above ASCII map by their byte in the font's charset when it is a Windows charset. Any other charset
// keeps them (ChemDraw on the Mac draws them as they are).
const windows: [string, string][] = [["®", "→"], ["¬", "←"], ["«", "↔"], ["¥", "∞"], ["£", "≤"], ["³", "≥"], ["¹", "≠"], ["Ö", "√"], ["ò", "∫"], ["¶", "∂"], ["°", "°"], ["±", "±"], ["´", "×"], ["¸", "÷"]];
for (const [from, to] of windows) assert.equal(textOf(doc(caption(s(5, from)))), to, from);
assert.equal(textOf(doc(caption(s(5, "Æ")), "x-mac-roman")), "Æ");
assert.equal(textOf(doc(caption(s(5, "π")), "x-mac-roman")), "π");
assert.equal(symbolText("®", 1252).text, "→");
assert.equal(symbolText("Æ", 10000).text, "Æ");
for (const charset of ["Unknown", "x-mac-symbol", ""]) assert.equal(textOf(doc(caption(s(5, "®Æ°")), charset)), "®Æ°", charset);
assert.equal(textOf(doc(caption(s(5, "n®")), "x-mac-symbol")), "ν®");
assert.equal(textOf(doc(caption(s(5, "ą")), "windows-1250")), "≠");

// 3. A character the charset cannot encode is kept. Windows's private-use copy of a Symbol byte is that byte.
assert.equal(textOf(doc(caption(s(5, "ν")))), "ν");
assert.equal(textOf(doc(caption(s(5, "")))), "ν");
assert.equal(textOf(doc(caption(s(5, "")), "x-mac-roman")), "→");

// 4. The mapped run takes the font of the text around it, and keeps its own face, size and colour.
{
  const c = read(doc(caption(s(4, "h"), s(5, "n")))).mol.captions![0];
  assert.deepEqual([c.text, c.font, c.runs], ["hν", "Times New Roman", undefined]);
  const a = read(doc(caption(s(3, "h"), s(5, "n")))).mol.captions![0];
  assert.deepEqual([a.text, a.font, a.runs], ["hν", undefined, undefined]);
  // A first run takes the next run's font.
  const first = read(doc(caption(s(5, "D"), s(4, "T")))).mol.captions![0];
  assert.deepEqual([first.text, first.font, first.runs], ["ΔT", "Times New Roman", undefined]);
  // An only run takes its text's own caption font, else the document's.
  const own = read(doc(`<t id="9" p="100 100" CaptionFont="4">${s(5, "a")}</t>`)).mol.captions![0];
  assert.deepEqual([own.text, own.font, own.runs], ["α", "Times New Roman", undefined]);
  const alone = read(doc(caption(s(5, "a")))).mol.captions![0];
  assert.deepEqual([alone.text, alone.font, alone.runs], ["α", undefined, undefined]);
  // Runs between two Symbol runs: each takes the plain run before it.
  const mixed = read(doc(caption(s(4, "h"), s(5, "n"), s(3, ", "), s(5, "d"), s(3, "+")))).mol.captions![0];
  assert.deepEqual([mixed.text, mixed.runs?.map((r) => [r.text, r.font])], ["hν, δ+", [["hν", "Times New Roman"], [", δ+", undefined]]]);
  // Bold, size and subscript stay on the mapped run.
  const styled = read(doc(caption(s(3, "h"), `<s font="5" size="14" face="33">n</s>`))).mol.captions![0];
  assert.deepEqual(styled.runs, [{ text: "h" }, { text: "ν", bold: true, size: 14, script: "sub" }]);
}

// 5. An atom label with a Symbol run keeps its chemistry: Cα is carbon, not calcium.
const label = (runs: string) => doc(`<fragment id="1"><n id="2" p="200 200"><t p="196 204" LabelJustification="Left">${runs}</t></n><n id="3" p="214 200"/><b id="4" B="2" E="3"/></fragment>`);
{
  const r = read(label(s(3, "C") + s(5, "a"))), unicode = read(label(s(3, "Cα")));
  assert.deepEqual([r.mol.atoms[0].label, r.mol.atoms[0].text], ["C", "Cα"]);
  assert.deepEqual(r.mol.atoms, unicode.mol.atoms);
  assert.deepEqual(r.lost, {});
}
// An R-group title and a bracket label with a Symbol run.
{
  const r = read(doc(`<altgroup id="20" GroupFrame="50 50 150 150"><t p="55 60">${s(3, "R")}${s(5, "1")}</t></altgroup>`));
  assert.deepEqual([r.mol.shapes?.[0]?.rgroup?.name, r.lost], ["R1", {}]);
  // An SRU bracket pair whose label is "n" in Symbol: ChemDraw draws ν.
  const mol: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [], shapes: [{ id: 1, kind: "brackets", from: [-1, 1], to: [1, -1], polymer: { usage: "sru", label: "m" } }] };
  const tree = parseXml(toCdxml(mol, read(doc("")).style));
  const strip = (x: Xml) => { delete x.attrs.Octet; x.kids.forEach(strip); };
  strip(tree);
  const fonts = tree.kids.find((k) => k.name === "fonttable")!;
  fonts.kids.push({ name: "font", attrs: { id: "99", charset: "iso-8859-1", name: "Symbol" }, kids: [], text: "" });
  const runs: Xml[] = [];
  const find = (x: Xml) => { if (x.name === "objecttag" && x.attrs.Name === "bracketusage") runs.push(...x.kids[0].kids); x.kids.forEach(find); };
  find(tree);
  assert.equal(runs.length, 1);
  runs[0].attrs.font = "99";
  runs[0].text = "n";
  const b = fromCdxml(tree);
  assert.deepEqual([b.mol.shapes?.find((x) => x.polymer)?.polymer?.label, b.lost], ["ν", {}]);
}

// 6. CDX gives what CDXML gives, for each charset ChemDraw might give Symbol, from the legacy text alone and with
// the UTF-8 copy.
// A CDX file with its UTF-8 text (0x0709) taken out, as a ChemDraw that writes only the legacy copy makes it.
function legacyOnly(b: Uint8Array): Uint8Array {
  const out: number[] = [...b.subarray(0, 28)], d = new DataView(b.buffer, b.byteOffset, b.byteLength);
  let at = 28;
  while (at < b.length) {
    const tag = d.getUint16(at, true);
    if (tag === 0 || tag & 0x8000) { const n = tag ? 6 : 2; out.push(...b.subarray(at, at + n)); at += n; continue; }
    let len = d.getUint16(at + 2, true), head = 4;
    if (len === 0xffff) { len = d.getUint32(at + 4, true); head = 8; }
    if (tag !== 0x0709) out.push(...b.subarray(at, at + head + len));
    at += head + len;
  }
  return new Uint8Array(out);
}
const texts = (r: { mol: Mol; lost: Record<string, number> }) => ({ captions: r.mol.captions?.map((c) => [c.text, c.font, c.runs]), atoms: r.mol.atoms.map((a) => [a.label, a.text]), lost: r.lost });
{
  const cases = [caption(s(3, "h"), s(5, "n"), s(3, ", "), s(5, "d"), s(3, "+")), caption(s(4, "h"), s(5, "n")), caption(s(5, "D"), s(3, "T")), caption(s(5, "b"), s(3, "-D-Glucopyranose")),
    caption(s(5, "hn")), caption(s(5, "®")), caption(s(3, "x"), s(5, "°")), `<fragment id="1"><n id="2" p="200 200"><t p="196 204">${s(3, "C")}${s(5, "a")}</t></n></fragment>`];
  for (const charset of ["Unknown", "iso-8859-1", "x-mac-roman", "x-mac-symbol"]) for (const body of cases) {
    const cdxml = doc(body, charset), want = texts(read(cdxml)), cdx = xmlToCdx(parseXml(cdxml));
    assert.equal(new TextDecoder().decode(cdx.subarray(0, 8)), MAGIC);
    assert.deepEqual(texts(fromCdxml(cdxToXml(cdx))), want, `${charset} with UTF-8: ${body}`);
    assert.deepEqual(texts(fromCdxml(cdxToXml(legacyOnly(cdx)))), want, `${charset} legacy only: ${body}`);
    assert.deepEqual(texts(readCdx(cdx)), want);
  }
  // Stefan's caption from a CDX: hν, δ+ and nothing lost.
  const r = fromCdxml(cdxToXml(legacyOnly(xmlToCdx(parseXml(doc(cases[0]))))));
  assert.deepEqual([r.mol.captions![0].text, r.lost], ["hν, δ+", {}]);
}

// 7. No lost-font notice for Symbol. A byte with no Symbol glyph keeps its character and counts once a text.
assert.deepEqual(read(doc(caption(s(3, "h"), s(5, "n"), s(3, ", "), s(5, "d"), s(3, "+")))).lost, {});
{
  const one = read(doc(caption(s(3, "x"), s(5, "&#x90;")))), two = read(doc(caption(s(5, "&#x90;&#x90;")) + `<t id="10" p="100 200">${s(5, "€")}</t>`, "iso-8859-1"));
  assert.deepEqual([one.mol.captions![0].text, one.lost], ["x\u0090", { character: 1 }]);
  assert.deepEqual(two.lost, { character: 2 });
  // Mac Roman's 0x90 is ê.
  assert.deepEqual(read(doc(caption(s(5, "ê")), "x-mac-roman")).lost, {});
  assert.deepEqual(read(doc(caption(s(5, "")), "x-mac-roman")).lost, { character: 1 });
}

// 8. Writing back gives Unicode in the run's font, and no Symbol font.
{
  const first = read(doc(caption(s(4, "h"), s(5, "n"), s(3, ", "), s(5, "d"), s(3, "+"))));
  const again = toCdxml(first.mol, first.style);
  assert.ok(!/name="Symbol/.test(again));
  assert.match(again, /<s font="\d+"[^>]*>hν<\/s>/);
  const second = fromCdxml(again);
  assert.deepEqual(texts(second).captions, texts(first).captions);
  const cdx = writeCdx(first.mol, first.style);
  assert.deepEqual(texts(readCdx(cdx)).captions, texts(first).captions);
  // ChemDraw's legacy copy cuts each run at the first character its charset lacks (ν and δ), as before.
  assert.equal(fromCdxml(cdxToXml(legacyOnly(cdx))).mol.captions![0].text, "h, ");
}

// Speed: 100,000 Symbol runs add well under a second to a read.
{
  const body = Array.from({ length: 1000 }, (_, k) => `<t id="${100 + k}" p="100 ${k}">${Array.from({ length: 50 }, () => s(3, "h") + s(5, "n")).join("")}</t>`).join("");
  const time = (cdxml: string) => { const tree = parseXml(cdxml), t0 = performance.now(); fromCdxml(tree); return performance.now() - t0; };
  const plain = time(doc(body.replaceAll('font="5"', 'font="4"'))), symbol = time(doc(body));
  assert.ok(symbol - plain < 1000, `${Math.round(symbol - plain)} ms more`);
}

console.log("symbol: ok");
