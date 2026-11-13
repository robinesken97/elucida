// Run: node src/cdx.check.ts. Fails loudly if the CDX reader or writer breaks, loses part of a drawing, or accepts a
// bad file; also checks what Octet keeps from ChemDraw files (pictures, highlights, query bonds, property text and
// polymer brackets) through CDXML, CDX, Octet's own file and editing.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { BASE64_MAGIC, MAGIC, NOT_CDX, cdxToXml, fromBase64, hexToBase64, toBase64, xmlToCdx } from "./cdx.ts";
import { DAMAGED, TOO_BIG, fontCharset, fromCdxml, parseXml, toCdxml, type Xml } from "./cdxml.ts";
import { DEFAULT_STYLE, presetAt, readStyle } from "./docstyle.ts";
import { parse, serialize } from "./file.ts";
import { EMPTY, deleteAtoms, extractSelection, insertMol } from "./edit.ts";
import { isDrawingText, readCdx, readOct, writeCdx } from "./oct.ts";
import type { Mol } from "./render.ts";
import { analyse, fromJcamp, measuredText } from "./measured.ts";
import pkg from "../package.json" with { type: "json" };

// A CDX file by hand: the header, then objects and properties as [tag, bytes] in little-endian order.
const u16 = (v: number) => [v & 0xff, (v >> 8) & 0xff], u32 = (v: number) => [...u16(v & 0xffff), ...u16(v >>> 16)];
const prop = (tag: number, data: number[]) => [...u16(tag), ...u16(data.length), ...data];
const obj = (tag: number, id: number, ...inner: number[][]) => [...u16(tag), ...u32(id), ...inner.flat(), 0, 0];
const ascii = (s: string) => [...s].map((c) => c.charCodeAt(0));
const header = [...ascii(MAGIC), 4, 3, 2, 1, ...new Array(10).fill(0)];
const coord = (v: number) => u32(Math.round(v * 65536) >>> 0);
const file = (...inner: number[][]) => new Uint8Array([...header, ...obj(0x8000, 0, ...inner)]);
const text = (runs: [number, number, number, number, number][], bytes: number[]) => [...u16(runs.length), ...runs.flatMap((r) => r.flatMap(u16)), ...bytes];

// A page with a fragment (N bonded to C, a charge on N), a caption in Mac Roman ("•") and in UTF-8, and a curve.
const doc = file(
  prop(0x0805, coord(14.4)), // BondLength
  prop(0x0100, [...u16(1), ...u16(1), ...u16(3), ...u16(10000), ...u16(5), ...ascii("Arial")]), // font table
  prop(0x0300, [...u16(2), ...u16(0xffff), ...u16(0xffff), ...u16(0xffff), ...u16(0), ...u16(0), ...u16(0)]), // colours
  obj(0x8001, 1, prop(0x0204, [...coord(0), ...coord(0), ...coord(720), ...coord(540)]),
    obj(0x8003, 2,
      obj(0x8004, 3, prop(0x0200, [...coord(100), ...coord(100)]), prop(0x0402, u16(7)), prop(0x0421, [1])),
      obj(0x8004, 4, prop(0x0200, [...coord(100), ...coord(114.4)])),
      obj(0x8005, 5, prop(0x0604, u32(3)), prop(0x0605, u32(4)), prop(0x0600, u16(3)), prop(0x0308, u16(2))),
    ),
    obj(0x8006, 6, prop(0x0200, [...coord(200), ...coord(50)]), prop(0x0700, text([[0, 3, 0, 200, 3]], [0xa5, ...ascii(" mac")]))),
    obj(0x8006, 7, prop(0x0200, [...coord(220), ...coord(50)]), prop(0x0700, text([[0, 3, 0, 200, 3]], ascii("old"))), prop(0x0709, text([[0, 3, 1, 240, 3]], [0xe2, 0x86, 0x92, ...ascii(" new")]))),
    obj(0x8008, 8, prop(0x0a23, [...u16(6), ...[10, 20, 10, 20, 10, 20, 30, 40, 30, 40, 30, 40].flatMap(coord)]), prop(0x0a39, [])),
  ),
);
{
  const x = cdxToXml(doc), page = x.kids.find((k) => k.name === "page")!;
  assert.equal(x.attrs.BondLength, "14.40");
  assert.deepEqual(x.kids.map((k) => k.name), ["fonttable", "colortable", "page"]);
  assert.deepEqual({ ...x.kids[0].kids[0].attrs }, { id: "3", charset: "x-mac-roman", name: "Arial" });
  const [frag, mac, utf, curve] = page.kids;
  assert.deepEqual(frag.kids.map((k) => k.name), ["n", "n", "b"]);
  assert.deepEqual({ ...frag.kids[0].attrs }, { id: "3", p: "100 100", Element: "7", Charge: "1" });
  // Order 3 is single or double (a query bond); colour 2 is the table's first row.
  assert.deepEqual([frag.kids[2].attrs.Order, frag.kids[2].attrs.highlightColor], ["1 2", "2"]);
  // Mac Roman 0xA5 is a bullet; UTF-8 (0x0709) wins over the legacy copy, its run's size in points.
  assert.deepEqual([mac.kids[0].text, mac.kids[0].attrs.size], ["• mac", "10"]);
  assert.deepEqual([utf.kids.length, utf.kids[0].text, utf.kids[0].attrs.face, utf.kids[0].attrs.size], [1, "→ new", "1", "12"]);
  assert.deepEqual([curve.attrs.CurvePoints, curve.attrs.Closed], ["20 10 20 10 20 10 40 30 40 30 40 30", "yes"]);
  // Octet reads it as it reads the CDXML: N+ bonded to a carbon by a query bond, highlighted, and the two captions.
  const r = fromCdxml(x);
  assert.deepEqual(r.mol.atoms.map((a) => [a.label, a.charge]), [["N", 1], ["C", undefined]]);
  assert.deepEqual(r.mol.bonds.map((b) => [b.type, b.query, b.halo]), [[1, "sd", "#FFFFFF"]]);
  assert.deepEqual(r.mol.captions!.map((c) => c.text), ["• mac", "→ new"]);
  assert.deepEqual(r.lost, {});
  // Written back, the tree reads the same; the legacy copy stops where Mac Roman has no character (→), the UTF-8
  // copy keeps all of it.
  const again = xmlToCdx(x), y = cdxToXml(again);
  assert.deepEqual(y, x);
  const t = cdxToXml(xmlToCdx(parseXml('<CDXML><page><t p="0 0"><s font="3" size="10">A → B</s></t></page></CDXML>')));
  assert.equal(t.kids[0].kids[0].kids[0].text, "A → B");
  const bytes = xmlToCdx(parseXml('<CDXML><page><t p="0 0"><s font="3" size="10">A → B</s></t></page></CDXML>'));
  assert.ok(Buffer.from(bytes).includes(Buffer.from("A ")) && !Buffer.from(bytes).includes(Buffer.from("A â")));
  // Big-endian files (early Mac ChemDraw) and files whose writer left the document's tag out (Indigo) read too.
  const big = new Uint8Array([...ascii(MAGIC), 1, 2, 3, 4, ...new Array(10).fill(0), 0x80, 0, 0, 0, 0, 0, 0x08, 0x05, 0, 4, ...coord(20).reverse(), 0, 0]);
  assert.equal(cdxToXml(big).attrs.BondLength, "20");
  const indigo = new Uint8Array([...ascii(MAGIC), 4, 3, 2, 1, ...new Array(16).fill(0), ...prop(0x0805, coord(30)), 0, 0]);
  assert.equal(cdxToXml(indigo).attrs.BondLength, "30");
  console.log("cdx.check: reading and writing ok");
}

// Hostile files: refused with a message, never a crash or a hang.
{
  const refuse = (b: Uint8Array, msg: string) => assert.throws(() => cdxToXml(b), (e: Error) => e.message === msg);
  refuse(new Uint8Array(ascii("VjCD0100")), NOT_CDX);
  refuse(new Uint8Array([...ascii("VjCD0101"), 4, 3, 2, 1, ...new Array(20).fill(0)]), NOT_CDX);
  refuse(doc.subarray(0, doc.length - 7), DAMAGED); // cut short
  const long = new Uint8Array(doc);
  long.set(u16(0xfff0), 30); // the first property's length runs past the end
  refuse(long, DAMAGED);
  // Nesting past 64 levels.
  let deep: number[] = [];
  for (let k = 0; k < 80; k++) deep = obj(0x8002, k + 1, deep);
  refuse(file(deep), TOO_BIG);
  // A property that does not read as its tag says is left out, not misread: a 3-byte Point2D, a short colour table.
  const odd = cdxToXml(file(obj(0x8001, 1, obj(0x8004, 2, prop(0x0200, [1, 2, 3]))), prop(0x0300, [9, 0, 1])));
  assert.equal(odd.kids[0].kids[0].attrs.p, undefined);
  assert.ok(!odd.kids.some((k) => k.name === "colortable"));
  // Random bytes after a sound header never hang the reader.
  for (let k = 0; k < 300; k++) {
    const b = new Uint8Array(header.length + 6 + ((k * 37) % 200));
    b.set(header);
    b.set([0, 0x80, 0, 0, 0, 0], header.length);
    for (let i = header.length + 6; i < b.length; i++) b[i] = (i * 7919 + k * 104729) % 256;
    try { cdxToXml(b); } catch (e) { assert.ok([DAMAGED, TOO_BIG].includes((e as Error).message), (e as Error).message); }
  }
  assert.throws(() => fromBase64("A".repeat(90_000_000)), (e: Error) => e.message === TOO_BIG);
  console.log("cdx.check: hostile files refused or read safely");
}

// What Octet keeps from ChemDraw files, through CDXML, CDX, Octet's own JSON and editing (REL-15, CH-11, CH-12).
const A = (label: string, x: number, y: number) => ({ label, location: [x, y, 0] as [number, number, number] });
const kept: Mol = {
  atoms: [A("C", 0, 0), A("C", 1, 0), A("O", 2, 0), A("C", 6, 0), A("C", 7, 0), A("C", 8, 0)],
  bonds: [{ type: 1, atoms: [0, 1], query: "sd" }, { type: 2, atoms: [1, 2], halo: "#FFD966" }, { type: 1, atoms: [3, 4] }, { type: 1, atoms: [4, 5] }],
  captions: [{ id: 1, text: "Ethanal", x: 1, y: -2, property: { attrs: { ChemicalPropertyType: "1" }, atoms: [0, 1, 2] } }],
  shapes: [
    { id: 2, kind: "picture", from: [0, 5], to: [4, 3], picture: { PNG: "89504E470D0A1A0A", RotationAngle: "11796480" } },
    { id: 3, kind: "brackets", from: [5.5, -1], to: [7.5, 1], polymer: { usage: "mult", label: "3" } },
  ],
};
{
  const cdxml = toCdxml(kept, DEFAULT_STYLE), root = parseXml(cdxml), names: string[] = [];
  const walk = (x: Xml) => { names.push(x.name); x.kids.forEach(walk); };
  walk(root);
  for (const n of ["embeddedobject", "chemicalproperty", "bracketedgroup", "bracketattachment", "crossingbond"]) assert.ok(names.includes(n), n);
  assert.match(cdxml, /Order="1 2"/);
  assert.match(cdxml, /highlightColor=/);
  // Read back from CDXML, from CDX, and from CDX as ChemDraw saves it (no Octet data): everything kept, nothing lost.
  const bare = (x: Xml): Xml => ({ ...x, attrs: Object.fromEntries(Object.entries(x.attrs).filter(([k]) => k !== "Octet")), kids: x.kids.map(bare) });
  for (const read of [fromCdxml(cdxml), fromCdxml(cdxToXml(xmlToCdx(root))), fromCdxml(cdxToXml(xmlToCdx(bare(root))))]) {
    const m = read.mol;
    assert.deepEqual(read.lost, {});
    assert.deepEqual(m.bonds.map((b) => [b.type, b.query, b.halo]), [[1, "sd", undefined], [2, undefined, "#FFD966"], [1, undefined, undefined], [1, undefined, undefined]]);
    assert.deepEqual(m.captions![0].property, { attrs: { ChemicalPropertyType: "1" }, atoms: [0, 1, 2] });
    const [picture, brackets] = m.shapes!;
    assert.deepEqual([picture.kind, picture.picture], ["picture", { PNG: "89504E470D0A1A0A", RotationAngle: "11796480" }]);
    assert.deepEqual(brackets.polymer, { usage: "mult", label: "3" });
  }
  // A query bond in a ChemDraw file is drawn single, never as a double bond (CH-11), and keeps its query (CH-16). Orders
  // that ChemDraw's Bond Properties do not offer are drawn single and reported.
  const q = fromCdxml('<CDXML><page><fragment><n id="1" p="0 0"/><n id="2" p="14.4 0" RingBondCount="AsDrawn"/><b B="1" E="2" Order="1 2" Topology="Ring"/></fragment></page></CDXML>');
  assert.deepEqual([q.mol.bonds[0].type, q.mol.bonds[0].query, q.mol.bonds[0].topology, q.mol.atoms[1].query, q.lost], [1, "sd", "ring", { rings: "drawn" }, {}]);
  const odd = fromCdxml('<CDXML><page><fragment><n id="1" p="0 0"/><n id="2" p="14.4 0"/><b B="1" E="2" Order="1 3"/></fragment></page></CDXML>');
  assert.deepEqual([odd.mol.bonds[0].type, odd.mol.bonds[0].query, odd.lost], [1, undefined, { "bond query": 1 }]);
  // Octet's own file keeps them all, and refuses a damaged picture or kept data that names atoms it lacks.
  const json = serialize(kept);
  assert.deepEqual(parse(json), kept);
  assert.throws(() => parse(json.replace('"89504E470D0A1A0A"', '"89504E47ZZ"')));
  const bad = JSON.parse(json);
  bad.captions[0].property.atoms = [0, 40];
  assert.throws(() => parse(JSON.stringify(bad)));
  // Editing: kept data follows its atoms, and goes with them. A bracket pair's meaning stays on the brackets.
  const less = deleteAtoms(kept, new Set([0]));
  assert.deepEqual(less.captions![0].property?.atoms, [0, 1]);
  assert.deepEqual(less.shapes![1].polymer, { usage: "mult", label: "3" });
  assert.equal(deleteAtoms(kept, new Set([0, 1, 2])).captions![0].property, undefined);
  // A copy keeps kept data only with all its atoms; pasting renumbers them.
  assert.equal(extractSelection(kept, new Set([0, 1]), new Set([1])).captions![0].property, undefined);
  const part = extractSelection(kept, new Set([0, 1, 2]), new Set([1, 3]));
  assert.deepEqual(part.captions![0].property?.atoms, [0, 1, 2]);
  assert.deepEqual(part.shapes![0].polymer, { usage: "mult", label: "3" });
  assert.deepEqual(insertMol(kept, part).mol.captions![1].property?.atoms, [6, 7, 8]);
  // A picture's bytes as an image the webview draws.
  assert.equal(hexToBase64("89504E47"), "iVBORw==");
  assert.equal(hexToBase64("8950ZZ"), undefined);
  console.log("cdx.check: pictures, highlights, query bonds and kept data ok");
}

// Octet's .cdx file: its own drawing back exactly while the file is unchanged; after another program changes it,
// the CDX is read as ChemDraw's drawing.
{
  const bytes = writeCdx(kept, DEFAULT_STYLE), text = toBase64(bytes);
  assert.ok(text.startsWith(BASE64_MAGIC) && isDrawingText(text));
  assert.deepEqual(readOct(text).mol, { ...kept, style: DEFAULT_STYLE });
  assert.equal(readCdx(bytes).foreign, undefined);
  // A changed byte (the program's name, say) makes the hash fail: ChemDraw's drawing is read, with nothing lost.
  const edited = new Uint8Array(bytes), at = Buffer.from(bytes).lastIndexOf(`Octet ${pkg.version}`);
  assert.ok(at >= 0);
  edited[at + 6] ^= 1;
  const foreign = readCdx(edited);
  assert.equal(foreign.foreign, true);
  assert.equal(foreign.mol.atoms.length, kept.atoms.length);
  // A large drawing's JSON takes the long length form.
  const big: Mol = { atoms: Array.from({ length: 3000 }, (_, i) => A("C", i % 60, Math.floor(i / 60))), bonds: [] };
  assert.equal(readCdx(writeCdx(big, DEFAULT_STYLE)).mol.atoms.length, 3000);
  // ChemDraw's clip art has curves of one anchor: a drawing with one comes back as Octet's own, not as a foreign read.
  const clip = fromCdxml(`<CDXML><page id="1"><curve id="2" CurvePoints="10 10 10 10 12 12" Closed="yes" FillType="Solid"/></page></CDXML>`).mol;
  assert.equal(clip.arrows?.[0].curve?.points.length, 1);
  assert.equal(readCdx(writeCdx(clip, DEFAULT_STYLE)).foreign, undefined);
  console.log("cdx.check: Octet's .cdx files ok");
}

// Octet's own data through CDX: a drawing exported as CDX and opened again is the drawing its CDXML gives. Each
// compound number keeps its structure, a caption gains no font or size, and a table and a TLC plate come back whole.
// The data is under a user-defined tag (0x4F44) that ChemDraw 22.2 reads past and leaves out when it saves.
{
  const m: Mol = {
    atoms: [A("C", 0, 0), A("C", 1, 0), A("O", 2, 0), A("C", 6, 0), A("C", 7, 0), A("O", 8, 0)],
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }, { type: 1, atoms: [3, 4] }, { type: 2, atoms: [4, 5] }],
    arrows: [{ id: 1, kind: "reaction", from: [3, 0], to: [5, 0] }],
    captions: [{ id: 2, text: "1", x: 0, y: 0, bold: true, under: [0, 1, 2] }, { id: 3, text: "2", x: 0, y: 0, bold: true, under: [3, 4, 5] }, { id: 4, text: "25 °C → Ω", x: 4, y: 3, align: "left", italic: true }],
    shapes: [
      { id: 5, kind: "table", from: [0, -4], to: [4, -6], table: { cells: [["Entry", "Yield"], ["1", "85 % at 25 °C, Ω"]] } },
      { id: 6, kind: "tlc", from: [10, 0], to: [13, 4], tlc: { lanes: 2, spots: [{ lane: 0, rf: 0.3, w: 0.3, h: 0.2 }, { lane: 1, rf: 0.6, tail: 0.4 }] } },
    ],
  };
  const xml = toCdxml(m, DEFAULT_STYLE), tree = parseXml(xml), bytes = xmlToCdx(tree), direct = fromCdxml(xml), back = fromCdxml(cdxToXml(bytes));
  assert.deepEqual(direct.mol.captions!.map((c) => c.under), [[0, 1, 2], [3, 4, 5], undefined]);
  assert.deepEqual(back.mol.captions!.map((c) => c.under), [[0, 1, 2], [3, 4, 5], undefined], "each number keeps its structure as CDX");
  assert.deepEqual(back.mol.captions!.map((c) => [c.font, c.size]), [[undefined, undefined], [undefined, undefined], [undefined, undefined]], "no font or size of the document's on a caption");
  assert.deepEqual(back, direct, "CDX gives the drawing CDXML gives");
  assert.equal(back.mol.shapes!.find((s) => s.kind === "table")!.table!.cells[1][1], "85 % at 25 °C, Ω");
  // The tree itself: the same Octet data on every object, and no style part the CDXML did not give.
  const every = (x: Xml): Xml[] => [x, ...x.kids.flatMap(every)], data = (x: Xml) => every(x).map((k) => k.attrs.Octet);
  const read = cdxToXml(bytes), parts = (x: Xml) => every(x).filter((k) => k.name === "t" || k.name === "CDXML").map((k) => Object.keys(k.attrs).filter((a) => /^(Label|Caption)(Font|Face|Size|Color)$/.test(a)).sort());
  assert.deepEqual(data(read), data(tree));
  assert.deepEqual(parts(read), parts(tree));
  // As ChemDraw saves it (the tags gone): its own drawing, with nothing lost, and no tie Octet did not read.
  const bare = (x: Xml): Xml => ({ ...x, attrs: Object.fromEntries(Object.entries(x.attrs).filter(([k]) => k !== "Octet")), kids: x.kids.map(bare) });
  const saved = fromCdxml(cdxToXml(xmlToCdx(bare(tree))));
  assert.deepEqual(saved.lost, {});
  assert.ok(saved.mol.captions!.every((c) => !c.under));
  // A TLC spot's size is whole 1/65536 pt in CDX as in CDXML: the same spots from both, with Octet's data and without.
  const spots = (r: { mol: Mol }) => r.mol.shapes!.find((s) => s.kind === "tlc")!.tlc!.spots;
  assert.deepEqual(spots(saved), spots(fromCdxml(bare(tree))));
  assert.ok(Math.abs(spots(saved)[0].w! - 0.3) < 1e-3 && Math.abs(spots(saved)[0].h! - 0.2) < 1e-3);
  // Hostile data under Octet's tags: bytes that are not UTF-8 are left out, text that is not Octet's JSON is ignored,
  // forged values are checked as CDXML's are, and a marker of the wrong length does nothing.
  const forged = file(prop(0x4f44, ascii('{"v":1}')), prop(0x0805, coord(14.4)), obj(0x8001, 1,
    obj(0x8003, 2, obj(0x8004, 3, prop(0x0200, [...coord(100), ...coord(100)])), obj(0x8004, 4, prop(0x0200, [...coord(100), ...coord(114.4)]))),
    obj(0x8006, 5, prop(0x0200, [...coord(150), ...coord(100)]), prop(0x4f44, ascii('{"under":[1e99,"x",3,99],"xy":["a",1],"cycle":{"cycle":7,"step":99}}')), prop(0x4f45, [1, 2]), prop(0x0700, text([], ascii("1")))),
    obj(0x8006, 6, prop(0x0200, [...coord(170), ...coord(100)]), prop(0x4f44, [0xff, 0xfe, 0x7b]), prop(0x0700, text([], ascii("2")))),
    obj(0x8006, 7, prop(0x0200, [...coord(190), ...coord(100)]), prop(0x4f44, ascii("[1,2] not JSON")), prop(0x4f45, [0]), prop(0x0700, text([], ascii("3"))))));
  const ft = cdxToXml(forged), fm = fromCdxml(ft).mol;
  assert.deepEqual(every(ft).filter((x) => x.name === "t").map((x) => x.attrs.Octet), ['{"under":[1e99,"x",3,99],"xy":["a",1],"cycle":{"cycle":7,"step":99}}', undefined, "[1,2] not JSON"]);
  assert.deepEqual(fm.captions!.map((c) => [c.text, c.under, c.cycle]), [["1", [0], undefined], ["2", undefined, undefined], ["3", undefined, undefined]]);
  assert.ok(fm.captions!.every((c) => Number.isFinite(c.x) && Number.isFinite(c.y)));
  console.log("cdx.check: Octet's own data as CDX ok");
}

// REL-15: as CDX too, turned text keeps its turn (RotationAngle), a Bold rectangle stays Bold, and a bond keeps its
// own spacing and settings, when ChemDraw (or another program) reads Octet's CDX without Octet's own data.
{
  const m: Mol = {
    atoms: [A("C", 0, 0), A("C", 1, 0)], bonds: [{ type: 2, atoms: [0, 1], spacing: 12, own: { BondLength: "30", HashSpacing: "2.70" } }],
    captions: [{ id: 1, text: "turned", x: 0, y: 2, align: "left", angle: -90 }], shapes: [{ id: 2, kind: "box", from: [0, 5], to: [3, 4], width: 2 }],
  };
  const tree = parseXml(toCdxml(m, DEFAULT_STYLE)), strip = (x: Xml): Xml => ({ ...x, attrs: Object.fromEntries(Object.entries(x.attrs).filter(([k]) => k !== "Octet")), kids: x.kids.map(strip) });
  const read = fromCdxml(cdxToXml(xmlToCdx(strip(tree))));
  assert.deepEqual(read.lost, {});
  assert.deepEqual([read.mol.captions?.[0].angle, read.mol.shapes?.[0].width, read.mol.bonds[0].spacing, read.mol.bonds[0].own], [-90, 2, 12, { BondLength: "30", HashSpacing: "2.70" }]);
  // A turned, centred label, and conditions placed by hand, keep their turn, alignment and place as CDX.
  const placed: Mol = {
    atoms: [{ ...A("Os", 0, 0), align: "centre" as const, labelAngle: 30 }, A("C", -1, 0), A("C", 1, 0)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [0, 2] }],
    arrows: [{ id: 1, kind: "reaction", from: [3, 0], to: [6, 0] }], captions: [{ id: 2, text: "rt", x: 0, y: 0, align: "left", on: { arrow: 1, side: "above" }, placed: { at: [-1, 0.5], arrow: [3, 0] } }],
  };
  for (const back of [fromCdxml(cdxToXml(xmlToCdx(parseXml(toCdxml(placed, DEFAULT_STYLE))))), fromCdxml(cdxToXml(xmlToCdx(strip(parseXml(toCdxml(placed, DEFAULT_STYLE))))))]) {
    assert.deepEqual([back.mol.atoms[0].labelAngle, back.mol.atoms[0].align], [30, "centre"]);
    assert.deepEqual(back.mol.captions![0].placed!.at.map((v) => +v.toFixed(3)), [-1, 0.5]);
  }
  console.log("cdx.check: turned text, bold shapes and a bond's own settings ok");
}

// A measured spectrum and its assignment as CDX (decision 0016): a spectrum object (0x8010) with its values in full as
// 64-bit floats (YScale and YLow applied), the assignment tags (0x8011) on the atoms and the spectrum, and back as the
// same spectrum with the same links, as ChemDraw reads Octet's CDX and as Octet reads ChemDraw's.
{
  const y = Float64Array.from({ length: 2000 }, (_, i) => { const x = 4000 - 1.8 * i; return 100 - (80 * 100) / ((x - 1740) ** 2 + 100) - (30 * 100) / ((x - 2980) ** 2 + 100); });
  const ir = fromJcamp({ title: "Acetone", kind: "ir", xUnit: "cm⁻¹", yUnit: "%T", first: 4000, last: 4000 - 1.8 * 1999, y }, 1);
  const band = ir.groups.find((g) => g.lo < 1740 && 1740 < g.hi)!.id;
  const m: Mol = { atoms: [{ ...A("C", 0, 0), peaks: [band] }, { ...A("O", 1, 0), peaks: [band] }], bonds: [{ type: 2, atoms: [0, 1], peaks: [band] }], spectra: [ir] };
  const strip = (x: Xml): Xml => ({ ...x, attrs: Object.fromEntries(Object.entries(x.attrs).filter(([k]) => k !== "Octet")), kids: x.kids.map(strip) });
  const tree = cdxToXml(xmlToCdx(strip(parseXml(toCdxml(m, DEFAULT_STYLE)))));
  const every = (x: Xml): Xml[] => [x, ...x.kids.flatMap(every)], sp = every(tree).find((x) => x.name === "spectrum")!;
  // The values are the trace itself, low x first; CDX holds no YLow or YScale for them.
  const values = sp.text.split(" ").map(Number);
  assert.equal(values.length, 2000);
  assert.ok(values.every((v, k) => Math.abs(v - ir.y[1999 - k]) < 1e-3), "the values in full");
  assert.deepEqual([sp.attrs.YLow, sp.attrs.YScale, sp.attrs.Class, sp.attrs.XType, sp.attrs.YType], [undefined, undefined, "Infrared", "Wavenumbers", "PercentTransmittance"]);
  const tags = (x: Xml) => x.kids.filter((k) => k.name === "objecttag" && k.attrs.Name === "/CS/CD/assign").map((k) => [k.attrs.TagType, k.attrs.Value]);
  const nodes = every(tree).filter((x) => x.name === "n");
  assert.deepEqual(tags(nodes[0]), tags(sp));
  assert.deepEqual(tags(nodes[1]), tags(sp));
  assert.deepEqual(tags(every(tree).find((x) => x.name === "b")!), tags(sp));
  const back = fromCdxml(tree), s = back.mol.spectra![0];
  assert.deepEqual(back.lost, {});
  assert.deepEqual([s.title, s.kind, s.xUnit, s.yUnit, s.y.length], ["Acetone", "ir", "cm⁻¹", "%T", 2000]);
  const ranges = (x: typeof ir) => x.groups.map((g) => [g.lo, g.hi].map((v) => v.toFixed(6))).sort();
  assert.deepEqual(ranges(s), ranges(ir));
  const id = s.groups.find((g) => g.lo < 1740 && 1740 < g.hi)!.id;
  assert.deepEqual([...back.mol.atoms, ...back.mol.bonds].map((a) => a.peaks), [[id], [id], [id]]);
  assert.equal(measuredText(s, analyse(s)), measuredText(ir, analyse(ir)));
  // ChemDraw's CDX read and written again keeps its values.
  assert.equal(every(cdxToXml(xmlToCdx(tree))).find((x) => x.name === "spectrum")!.text, sp.text);
  console.log("cdx.check: spectra as ChemDraw's spectrum object ok");
}

// Charsets (issue #18). The font table says iso-8859-1 on Windows and Linux and x-mac-roman on the Mac, as ChemDraw
// for each system writes it, and the CDX's legacy text is in that charset: the degree sign is 0xB0 in iso-8859-1
// (Windows code page 1252) and 0xA1 in Mac Roman, é 0xE9 and 0x8E. Neither has α, so the legacy copy stops there.
{
  assert.deepEqual(["Win32", "Linux x86_64", "MacIntel", ""].map(fontCharset), ["iso-8859-1", "iso-8859-1", "x-mac-roman", "x-mac-roman"]);
  const has = (b: Uint8Array, seq: number[]) => Buffer.from(b).includes(Buffer.from(seq));
  const words = "25 °C, café α-D";
  for (const [cs, deg, e] of [["iso-8859-1", 0xb0, 0xe9], ["x-mac-roman", 0xa1, 0x8e]] as const) {
    // The second text has no font: it takes the document's caption font's charset.
    const b = xmlToCdx(parseXml(`<CDXML CaptionFont="3"><fonttable><font id="3" charset="${cs}" name="Arial"/></fonttable><page><t p="0 0"><s font="3" size="10">${words}</s></t><t p="0 20"><s size="10">°é</s></t></page></CDXML>`));
    assert.ok(has(b, [...ascii("25 "), deg, ...ascii("C, caf"), e, 0x20]) && !has(b, [...ascii("C, caf"), e, 0x20, 0xce]), cs);
    assert.ok(has(b, [3, 0, deg, e]), `${cs}: the run with no font`);
    const back = cdxToXml(b).kids.find((k) => k.name === "page")!.kids.map((t) => t.kids[0].text);
    assert.deepEqual(back, [words, "°é"]);
  }
  // A Windows ChemDraw file's legacy text, read in iso-8859-1, and written back in it.
  const win = file(prop(0x0100, [...u16(1), ...u16(1), ...u16(3), ...u16(1252), ...u16(5), ...ascii("Arial")]),
    obj(0x8001, 1, obj(0x8006, 2, prop(0x0200, [...coord(0), ...coord(0)]), prop(0x0700, text([[0, 3, 0, 200, 3]], [...ascii("25 "), 0xb0, ...ascii("C caf"), 0xe9])))));
  const x = cdxToXml(win);
  assert.equal(x.kids[0].kids[0].attrs.charset, "iso-8859-1");
  assert.equal(x.kids[1].kids[0].kids[0].text, "25 °C café");
  assert.ok(has(xmlToCdx(x), [...ascii("25 "), 0xb0, ...ascii("C caf"), 0xe9]));
  // Octet's own drawing through CDXML and CDX: the charset is this system's, and the text comes back whole.
  const mol: Mol = { atoms: [], bonds: [], captions: [{ id: 1, text: words + ", Ω µ ±", x: 0, y: 0, align: "left" }] };
  const cdxml = toCdxml(mol, DEFAULT_STYLE);
  assert.ok(cdxml.includes(`charset="${fontCharset(navigator.platform)}"`) && !cdxml.includes(`charset="${fontCharset(navigator.platform.startsWith("Mac") ? "Win32" : "MacIntel")}"`));
  assert.equal(fromCdxml(cdxml).mol.captions![0].text, words + ", Ω µ ±");
  assert.equal(fromCdxml(cdxToXml(xmlToCdx(parseXml(cdxml)))).mol.captions![0].text, words + ", Ω µ ±");
  console.log("cdx.check: charsets ok");
}

// Style sheets (.cds, issue 74): a CDX file with the document's settings and an empty page. Settings > Document > Save
// to file… writes the style as one (writeCdx of an empty drawing); Apply Settings From File… reads it, or ChemDraw's.
{
  // Octet's own: the whole style back exactly, and ChemDraw (which keeps no Octet data) still reads its settings.
  const own = readStyle({ ...DEFAULT_STYLE, ...presetAt("RSC", 2), scale: 2, page: "Slide169", landscape: true, background: "dark", captionFont: "Helvetica", palette: [{ name: "Lab red", hex: "#B42323" }] });
  const sheet = writeCdx(EMPTY, own);
  assert.deepEqual(readOct(toBase64(sheet)).mol.style, own);
  const chemdraw = readCdx(xmlToCdx(parseXml(toCdxml(EMPTY, own)))).mol.style!;
  for (const k of ["bond", "line", "bold", "margin", "hash", "spacing", "labelFont", "labelSize", "captionFont", "captionSize", "chainAngle"] as const) assert.equal(chemdraw[k], own[k], k);
  // ChemDraw's: an empty page whose box is 0 0 0 0 takes its size from its Width and Height (368.5 by 720.91 pt and
  // an inch of margin), and one of -2 -2 2 2 with neither is ChemDraw's default page, US Letter.
  const pageOf = (...page: number[][]) => readOct(toBase64(file(
    prop(0x0805, coord(17)), prop(0x0807, coord(1)), prop(0x0804, u16(180)),
    prop(0x0100, [...u16(1), ...u16(1), ...u16(3), ...u16(10000), ...u16(5), ...ascii("Arial")]),
    prop(0x080a, [...u16(3), ...u16(0), ...u16(200), ...u16(3)]), prop(0x080b, [...u16(3), ...u16(0), ...u16(240), ...u16(3)]),
    obj(0x8001, 1, ...page),
  ))).mol.style!;
  const old = pageOf(prop(0x0204, [0, 0, 0, 0].flatMap(coord)), prop(0x0812, coord(368.5)), prop(0x0813, coord(720.91)));
  assert.deepEqual([old.bond, old.line, old.spacing, old.labelFont, old.labelSize, old.captionSize], [17, 1, 18, "Arial", 10, 12]);
  assert.deepEqual([old.page, old.custom], ["Custom", [155.4, 279.72]]);
  assert.equal(pageOf(prop(0x0204, [-2, -2, 2, 2].flatMap(coord))).page, "Letter");
  // A page with something on it keeps its own box, however small (a paste from ChemDraw, say).
  assert.deepEqual(fromCdxml('<CDXML><page id="1" BoundingBox="0 0 10 10" Width="540" Height="720"><t p="5 5"><s>x</s></t></page></CDXML>').style.custom, [28.93, 28.93]);
  // Both ends: Apply Settings From File… takes .cds files, Save to file… sends the style sheet as cds, and Export
  // writes it.
  const rust = (f: string) => readFileSync(new URL(`../src-tauri/src/${f}`, import.meta.url), "utf8");
  assert.match(readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), /"export_file", \{ export: \{ name, cds: toBase64\(writeCdx\(EMPTY, savedStyle\(\)\)\) \} \}/);
  assert.match(rust("main.rs"), /const STYLES: [^\n]*"cds"[\s\S]*fn pick_style_file[^}]*add_filter\(STYLES\.0, STYLES\.1\)/);
  assert.match(rust("export.rs"), /\("cds", "ChemDraw Style Sheet \(CDS\)", &\["cds"\]\)[\s\S]*"cds" => e\.cds\.is_some\(\)[\s\S]*"cds" => base64[^\n]*e\.cds/);
  console.log("cdx.check: style sheets ok");
}

// A big-endian file (ChemDraw 4 on the Mac) reads its signed numbers as a little-endian one does: a charge of −1.
{
  const b16 = (v: number) => [(v >> 8) & 0xff, v & 0xff], b32 = (v: number) => [...b16(v >>> 16), ...b16(v & 0xffff)];
  const bprop = (tag: number, data: number[]) => [...b16(tag), ...b16(data.length), ...data];
  const bobj = (tag: number, id: number, ...inner: number[][]) => [...b16(tag), ...b32(id), ...inner.flat(), 0, 0];
  const big = new Uint8Array([...ascii(MAGIC), 1, 2, 3, 4, ...new Array(10).fill(0), ...bobj(0x8000, 0, bobj(0x8001, 1, bobj(0x8003, 2, bobj(0x8004, 3, bprop(0x0421, [0xff])))))]);
  assert.equal(cdxToXml(big).kids.find((k) => k.name === "page")!.kids[0].kids[0].attrs.Charge, "-1");
  console.log("cdx.check: big-endian signs ok");
}
