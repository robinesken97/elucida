// Run: node src/picture.check.ts. Fails loudly if Octet takes a dropped or pasted picture other than as ChemDraw does:
// by its first bytes (never its name), at 1 pt per pixel, kept through CDXML, CDX and Octet's own file.
import assert from "node:assert/strict";
import { cdxToXml, xmlToCdx } from "./cdx.ts";
import { fromCdxml, parseXml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { insertMol } from "./edit.ts";
import { readCdx, readOct, writeCdx, writeOct } from "./oct.ts";
import { jpegTurned, kindOf, MAX_PICTURE, pictureBytes, pictureMol } from "./picture.ts";

const bytes = (...parts: (string | number[])[]) => new Uint8Array(parts.flatMap((p) => (typeof p === "string" ? [...p].map((c) => c.charCodeAt(0)) : p)));

// The format by its first bytes. A text file that starts like a picture's name ("BMS-986") is not a picture.
assert.equal(kindOf(bytes("\x89PNG\r\n\x1a\n", [0, 0])), "png");
assert.equal(kindOf(bytes([0xff, 0xd8, 0xff, 0xe0])), "jpeg");
assert.equal(kindOf(bytes("GIF89a")), "gif");
assert.equal(kindOf(bytes("BM", new Array(12).fill(0), [40, 0, 0, 0])), "bmp");
assert.equal(kindOf(bytes("BMS-986 from the trial\n  Octet\n\n  2  1  0")), undefined);
assert.equal(kindOf(bytes("II*\0")), "tiff");
assert.equal(kindOf(bytes("MM\0*")), "tiff");
assert.equal(kindOf(bytes("RIFF", [0, 0, 0, 0], "WEBP")), "webp");
assert.equal(kindOf(bytes("<svg xmlns=")), undefined);
assert.equal(kindOf(bytes("\x89PN")), undefined);

// A JPEG whose EXIF orientation turns it (6: a phone held upright) is drawn upright again; 1, none, or damaged data
// is not turned.
const exif = (orientation: number, little: boolean) => {
  const u16 = (v: number) => (little ? [v & 0xff, v >> 8] : [v >> 8, v & 0xff]), u32 = (v: number) => (little ? [...u16(v & 0xffff), ...u16(v >>> 16)] : [...u16(v >>> 16), ...u16(v & 0xffff)]);
  const tiff = [...(little ? [0x49, 0x49] : [0x4d, 0x4d]), ...u16(42), ...u32(8), ...u16(1), ...u16(0x0112), ...u16(3), ...u32(1), ...u16(orientation), 0, 0, ...u32(0)];
  const app1 = [...bytes("Exif\0\0"), ...tiff];
  return bytes([0xff, 0xd8, 0xff, 0xe0, 0, 4, 0, 0, 0xff, 0xe1, (app1.length + 2) >> 8, (app1.length + 2) & 0xff], app1, [0xff, 0xda, 0, 2]);
};
assert.equal(jpegTurned(exif(6, false)), true);
assert.equal(jpegTurned(exif(8, true)), true);
assert.equal(jpegTurned(exif(1, true)), false);
assert.equal(jpegTurned(bytes([0xff, 0xd8, 0xff, 0xda, 0, 2])), false);
assert.equal(jpegTurned(exif(6, false).subarray(0, 30)), false);

// A 144 by 72 pixel picture is 144 by 72 pt (2 by 1 inches at 72 dpi), whatever the bond length.
const png = "89504E470D0A1A0A0000";
for (const bond of [14.4, 10.8]) {
  const m = pictureMol({ PNG: png }, 144, 72, bond), sh = m.shapes![0];
  assert.deepEqual([sh.kind, (sh.to[0] - sh.from[0]) * bond, (sh.to[1] - sh.from[1]) * bond, sh.from[0] + sh.to[0], sh.from[1] + sh.to[1]], ["picture", 144, 72, 0, 0]);
}
assert.equal(pictureBytes(pictureMol({ PNG: png }, 1, 1, 14.4)), 10);
assert.equal(MAX_PICTURE, 12 * 1024 * 1024);

// In a drawing: written to CDXML as ChemDraw's embeddedobject at its size in points, read back from CDXML, from CDX as
// ChemDraw sees it, and from Octet's own .oct and .cdx files, with its data as it came.
{
  const style = DEFAULT_STYLE, mol = insertMol({ atoms: [], bonds: [], style }, pictureMol({ JPEG: "FFD8FFE0" }, 144, 72, style.bond), [3, 1]).mol;
  const cdxml = toCdxml(mol, style), root = parseXml(cdxml);
  const find = (x: typeof root): typeof root | undefined => (x.name === "embeddedobject" ? x : x.kids.map(find).find(Boolean));
  const obj = find(root)!, box = obj.attrs.BoundingBox.split(" ").map(Number);
  assert.equal(obj.attrs.JPEG, "FFD8FFE0");
  assert.deepEqual([Math.round(box[2] - box[0]), Math.round(box[3] - box[1])], [144, 72]);
  const same = (m: typeof mol) => {
    const sh = m.shapes!.find((x) => x.kind === "picture")!;
    assert.deepEqual(sh.picture, { JPEG: "FFD8FFE0" });
    assert.deepEqual([...sh.from, ...sh.to].map((v) => Math.round(v * 1000) / 1000), [...mol.shapes![0].from, ...mol.shapes![0].to].map((v) => Math.round(v * 1000) / 1000));
  };
  for (const read of [fromCdxml(cdxml), fromCdxml(cdxToXml(xmlToCdx(root)))]) {
    assert.deepEqual(read.lost, {});
    same(read.mol);
  }
  same(readOct(writeOct(mol, style)).mol);
  same(readCdx(writeCdx(mol, style)).mol);
}
console.log("picture.check: formats by their bytes, EXIF turns, 1 pt per pixel, kept through CDXML, CDX and .oct ok");
