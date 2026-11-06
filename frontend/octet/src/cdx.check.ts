// Run: node src/cdx.check.ts. Fails loudly if the CDX reader or writer breaks, loses part of a drawing, or accepts a
// bad file; also checks what Octet keeps from ChemDraw files (pictures, highlights, query bonds, property text and
// polymer brackets) through CDXML, CDX, Octet's own file and editing.
import assert from "node:assert/strict";
import { BASE64_MAGIC, MAGIC, NOT_CDX, cdxToXml, fromBase64, hexToBase64, toBase64, xmlToCdx } from "./cdx.ts";
import { DAMAGED, TOO_BIG, fromCdxml, parseXml, toCdxml, type Xml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { parse, serialize } from "./file.ts";
import { deleteAtoms, extractSelection, insertMol } from "./edit.ts";
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
  // Read back from CDXML, and from CDX as ChemDraw would see it (no Octet data): everything kept, nothing lost.
  for (const read of [fromCdxml(cdxml), fromCdxml(cdxToXml(xmlToCdx(root)))]) {
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
