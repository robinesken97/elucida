// Run: node src/picturedata.check.ts. Fails loudly if a picture whose data is base64 (as a ChemDraw 21 file from
// Windows holds it) does not open, if damaged data loses more than its picture, or if any writer gives other bytes
// than it read (issue 22). Octet keeps and writes picture data as uppercase hex, as ChemDraw on the Mac refuses a file
// with base64 picture data.
import assert from "node:assert/strict";
import { randomFillSync } from "node:crypto";
import { deflateSync, inflateSync } from "node:zlib";
import { cdxToXml, hexToBase64, toBase64, xmlToCdx } from "./cdx.ts";
import { TOO_BIG, fromCdxml, parseXml, pictureHex, toCdxml, type Xml } from "./cdxml.ts";
import { parse, serialize } from "./file.ts";
import { readOct, writeCdx, writeOct } from "./oct.ts";
import { readTemplateFile, writeTemplateFile } from "./ctp.ts";
import { pictureBytes } from "./picture.ts";
import type { Mol } from "./render.ts";

const hexOf = (b: Uint8Array) => Buffer.from(b).toString("hex").toUpperCase();
const b64Of = (b: Uint8Array) => Buffer.from(b).toString("base64");
const wrap = (s: string, n = 72, br = "&#13;&#10;") => s.match(new RegExp(`.{1,${n}}`, "g"))!.join(br);
// A document with one atom and one embedded object with these attributes.
const doc = (attrs: string, extra = "") => `<?xml version="1.0" encoding="UTF-8"?>\n<CDXML><page id="1"><fragment id="2"><n id="3" p="10 10"/></fragment><embeddedobject id="4" BoundingBox="20 20 120 80" Z="7" ${attrs}/>${extra}</page></CDXML>`;
const read = (attrs: string) => fromCdxml(doc(attrs));
const pictureOf = (m: Mol) => m.shapes!.find((s) => s.kind === "picture")!;
const find = (x: Xml, name: string): Xml | undefined => x.name === name ? x : x.kids.map((k) => find(k, name)).find(Boolean);

// A 128-byte EMF made here: a header record (type 1) with " EMF" at offset 40, deflated as ChemDraw compresses it.
const emf = new Uint8Array(128);
emf.set([1, 0, 0, 0, 128, 0, 0, 0]);
emf.set([0x20, 0x45, 0x4d, 0x46], 40);
for (let i = 44; i < 128; i++) emf[i] = (i * 37) & 0xff;
const deflated = new Uint8Array(deflateSync(emf));
const emfB64 = b64Of(deflated);

// R1, R4, R5 (T1): base64 wrapped at 72 characters with CR LF, as the issue's file holds it.
{
  const r = read(`CompressedEnhancedMetafile="${wrap(emfB64)}" UncompressedEnhancedMetafileSize="128"`);
  assert.deepEqual(r.lost, {}, "T1: nothing lost");
  assert.equal(r.mol.atoms.length, 1, "T1: the atom reads");
  const p = pictureOf(r.mol);
  assert.deepEqual(p.picture, { CompressedEnhancedMetafile: hexOf(deflated), UncompressedEnhancedMetafileSize: "128" }, "T1: kept as uppercase hex of the same bytes");
  const h = pictureOf(read(`PNG="ABCD"`).mol);
  assert.deepEqual([p.from, p.to], [h.from, h.to], "T1: at its BoundingBox, as a hex picture");
  // CDXML writes the same bytes, as hex.
  const again = find(parseXml(toCdxml(r.mol, r.style)), "embeddedobject")!;
  assert.equal(again.attrs.CompressedEnhancedMetafile, hexOf(deflated), "T1: CDXML writes hex");
  // CDX holds the bytes, and they inflate to the EMF.
  const back = find(cdxToXml(xmlToCdx(parseXml(toCdxml(r.mol, r.style)))), "embeddedobject")!;
  assert.equal(back.attrs.CompressedEnhancedMetafile, hexOf(deflated), "T1: CDX holds the deflated bytes");
  assert.deepEqual(new Uint8Array(inflateSync(Buffer.from(back.attrs.CompressedEnhancedMetafile, "hex"))), emf, "T1: they inflate to the EMF");
  // xmlToCdx given base64 itself (any CDXML) writes the bytes too.
  const direct = find(cdxToXml(xmlToCdx(parseXml(doc(`CompressedEnhancedMetafile="${wrap(emfB64)}"`)))), "embeddedobject")!;
  assert.equal(direct.attrs.CompressedEnhancedMetafile, hexOf(deflated), "R5: xmlToCdx decodes base64");
}

// R1 (T2): one line, and both paddings.
for (const n of [128, 127, 126]) {
  const bytes = emf.subarray(0, n), b64 = b64Of(bytes);
  assert.equal((b64.match(/=+$/)?.[0] ?? "").length, (3 - (n % 3)) % 3, "T2: the padding under test");
  const r = read(`EnhancedMetafile="${b64}"`);
  assert.deepEqual([r.lost, pictureOf(r.mol).picture!.EnhancedMetafile], [{}, hexOf(bytes)], `T2: ${n} bytes`);
}

// R3 (T3, T4): damaged data loses that picture only, and nothing throws.
for (const bad of [`${emfB64.slice(0, 8)}*${emfB64.slice(9)}`, "ab-_cdef", "AB=CDEFG", "ABCDE===", emfB64.slice(1), "89504E4", " &#10; ", "QUJD&#160;"]) {
  const r = read(`PNG="${bad}"`);
  assert.deepEqual(r.lost, { picture: 1 }, `T3: ${bad.slice(0, 12)}`);
  assert.equal(r.mol.atoms.length, 1, "T3: the atom reads");
}
assert.equal(pictureHex("AAAA="), undefined, "unpadded or over-padded base64 is not sound");
assert.equal(pictureHex("AAA"), undefined, "unpadded base64 is not sound");

// R2 (T5): a value that is both hex and base64 is hex; hex with whitespace reads, lowercase hex is kept as uppercase.
{
  const r = read(`PNG="ABCD"`);
  assert.equal(pictureOf(r.mol).picture!.PNG, "ABCD", "T5: hex wins a tie");
  const cdx = find(cdxToXml(xmlToCdx(parseXml(toCdxml(r.mol, r.style)))), "embeddedobject")!;
  assert.equal(cdx.attrs.PNG, "ABCD", "T5: the CDX holds AB CD");
  assert.equal(pictureOf(read(`PNG="89 50&#10;4e\t47"`).mol).picture!.PNG, "89504E47", "R2: hex with whitespace, lowercase");
  assert.equal(pictureHex("89504E47"), "89504E47");
}

// R2, R6 (T6, T8): hex and base64 in one element are judged on their own; the raster draws from the same bytes.
const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3, 4]);
{
  const pdf = new TextEncoder().encode("%PDF-1.4 made here");
  const r = read(`PNG="${hexOf(png)}" PDF="${wrap(b64Of(pdf), 8, "&#10;")}"`);
  assert.deepEqual(pictureOf(r.mol).picture, { PNG: hexOf(png), PDF: hexOf(pdf) }, "T6: both kept");
  const b = read(`PNG="${wrap(b64Of(png), 8)}"`);
  assert.equal(hexToBase64(pictureOf(b.mol).picture!.PNG), b64Of(png), "T8: a base64 PNG draws from its own bytes");
}

// R7 (T9): the size is the bytes of the data, not its sizes or turn.
{
  const bytes = new Uint8Array(300).map((_, i) => i);
  const r = read(`PNG="${b64Of(bytes)}" RotationAngle="11796480"`);
  assert.equal(pictureBytes(r.mol), 300, "T9");
}

// R4, R8 (T7, T10): Octet's own file, its CDXML alone, and .cdx with Octet's copy give the same bytes.
{
  const r = read(`CompressedEnhancedMetafile="${wrap(emfB64)}" UncompressedEnhancedMetafileSize="128" PNG="${b64Of(png)}"`);
  const want = { CompressedEnhancedMetafile: hexOf(deflated), UncompressedEnhancedMetafileSize: "128", PNG: hexOf(png) };
  const oct = writeOct(r.mol, r.style);
  assert.deepEqual(pictureOf(readOct(oct).mol).picture, want, "T7: .oct");
  assert.deepEqual(pictureOf(readOct(oct.replace(/<!--Octet[^]*$/, "")).mol).picture, want, "T7: .oct without Octet's comment");
  const cdx = readOct(toBase64(writeCdx(r.mol, r.style)));
  assert.deepEqual([cdx.foreign, pictureOf(cdx.mol).picture], [undefined, want], "T7: .cdx with Octet's copy");
  // Octet's JSON (its own file, the clipboard, templates) reads base64 by the same rule, and refuses damaged data.
  const json = JSON.parse(serialize(r.mol));
  const shape = json.shapes.find((s: { kind: string }) => s.kind === "picture");
  shape.picture.PNG = wrap(b64Of(png), 8, "\n");
  assert.equal(pictureOf(parse(JSON.stringify(json))).picture!.PNG, hexOf(png), "T10: JSON keeps a base64 picture");
  shape.picture.PNG = "AB=CDEFG";
  assert.throws(() => parse(JSON.stringify(json)), { message: "This drawing is damaged." }, "T10: damaged base64");
}

// R8 (T11): a ChemDraw template file with a base64 picture, and Octet's set written from it.
{
  const pane = `<page id="10"><fragment id="11"><n id="12" p="10 10"/></fragment><embeddedobject id="13" BoundingBox="20 20 60 60" PNG="${wrap(b64Of(png), 8)}"/></page>`;
  const ctp = `<?xml version="1.0"?>\n<CDXML><templategrid NumRows="1" NumColumns="1" extent="2.75 2.75"/>${pane}</CDXML>`;
  const t = readTemplateFile(ctp, "Pictures.ctp");
  assert.equal(t.templates.length, 1, "T11: the pane reads");
  assert.equal(pictureOf(t.templates[0].mol).picture!.PNG, hexOf(png), "T11: its picture");
  const written = find(cdxToXml(writeTemplateFile(t.templates, "Pictures").bytes), "embeddedobject")!;
  assert.equal(written.attrs.PNG, hexOf(png), "T11: the set holds the bytes");
}

// R9 (T13): a file of nearly 64 M characters with one base64 picture reads in good time; a larger one is refused.
{
  const bytes = randomFillSync(new Uint8Array(42 * 1024 * 1024));
  const big = doc(`PNG="${wrap(b64Of(bytes))}"`);
  assert.ok(big.length > 63 * 1024 * 1024 && big.length < 64 * 1024 * 1024, `T13: ${big.length} characters`);
  // About 0.8 s on an M-series Mac. The best of up to three reads, so a busy machine does not fail it; a real slowdown
  // fails all three.
  let t0 = performance.now(), r = fromCdxml(big), ms = performance.now() - t0;
  for (let k = 1; k < 3 && ms >= 2000; k++) { t0 = performance.now(); r = fromCdxml(big); ms = Math.min(ms, performance.now() - t0); }
  assert.deepEqual(r.lost, {}, "T13: nothing lost");
  assert.equal(pictureBytes(r.mol), bytes.length, "T13: every byte");
  assert.ok(ms < 2000, `T13: read in ${Math.round(ms)} ms`);
  assert.throws(() => fromCdxml(doc(`PNG="${"A".repeat(64 * 1024 * 1024)}"`)), { message: TOO_BIG }, "T13: over 64 M characters");
}

console.log("picturedata.check: base64 pictures read, and every writer gives the same bytes");
