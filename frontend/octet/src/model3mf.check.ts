// Run: node src/model3mf.check.ts. Fails loudly if File > More Formats > Export 3MF… stops making a model a printer
// can use (every ball and stick a closed surface facing out, in millimetres at a print size, each stereocentre's hand
// kept), or if Export BMP… stops being a picture on white, or if either leaves File > More Formats.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { model3mf } from "./model3mf.ts";
import { pictureAs, RASTERS } from "./export.ts";
import { EMPTY, addRing } from "./edit.ts";
import { HBOND, type Mol } from "./render.ts";

type V = number[];
// The model's vertices (mm) and triangles. Every edge has one triangle each way, so each surface is closed and its
// triangles agree on which side is out. The surfaces in the order they were made (balls, then sticks), each with its
// vertices' middle and its volume (positive: the triangles face out).
function read(xml: string) {
  assert.match(xml, /^<\?xml version="1\.0" encoding="UTF-8"\?>\n<model unit="millimeter" xml:lang="en-GB" xmlns="http:\/\/schemas\.microsoft\.com\/3dmanufacturing\/core\/2015\/02">/);
  assert.match(xml, /<object id="1" type="model">[\s\S]*<build>\n<item objectid="1"\/>\n<\/build>\n<\/model>\n$/);
  const v: V[] = [...xml.matchAll(/<vertex x="([\d.]+)" y="([\d.]+)" z="([\d.]+)"\/>/g)].map((m) => [+m[1], +m[2], +m[3]]);
  const t = [...xml.matchAll(/<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"\/>/g)].map((m) => [+m[1], +m[2], +m[3]]);
  assert.equal(v.length, (xml.match(/<vertex /g) ?? []).length, "every coordinate in mm from the origin");
  const edges = new Map<string, number>();
  for (const [a, b, c] of t) for (const [x, y] of [[a, b], [b, c], [c, a]]) edges.set(`${x},${y}`, (edges.get(`${x},${y}`) ?? 0) + 1);
  for (const [e, n] of edges) assert.ok(n === 1 && edges.get(e.split(",").reverse().join(",")) === 1, `edge ${e}: closed, one triangle each way`);
  const top = v.map((_, i) => i), find = (i: number): number => (top[i] === i ? i : (top[i] = find(top[i])));
  for (const [a, b, c] of t) { top[find(b)] = find(a); top[find(c)] = find(a); }
  const shells = new Map<number, { middle: V; n: number; volume: number }>();
  v.forEach((q, i) => { const s = shells.get(find(i)) ?? shells.set(find(i), { middle: [0, 0, 0], n: 0, volume: 0 }).get(find(i))!; s.n++; s.middle = s.middle.map((x, k) => x + q[k]); });
  for (const [a, b, c] of t) {
    const [p, q, r] = [v[a], v[b], v[c]];
    shells.get(find(a))!.volume += (p[0] * (q[1] * r[2] - q[2] * r[1]) - p[1] * (q[0] * r[2] - q[2] * r[0]) + p[2] * (q[0] * r[1] - q[1] * r[0])) / 6;
  }
  const list = [...shells.values()].map((s) => ({ middle: s.middle.map((x) => x / s.n), volume: s.volume }));
  for (const s of list) assert.ok(s.volume > 0, "each surface faces out");
  return { v, list };
}
const dist = (a: V, b: V) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const vol = (o: V, a: V, b: V, d: V) => { const [u, w, x] = [a, b, d].map((q) => q.map((c, k) => c - o[k])); return u[0] * (w[1] * x[2] - w[2] * x[1]) - u[1] * (w[0] * x[2] - w[2] * x[0]) + u[2] * (w[0] * x[1] - w[1] * x[0]); };

// Cyclohexane drawn flat: six balls and six sticks, a chair (3D Clean Up's shape), bonds 20 mm, from the origin.
{
  const ring = addRing(EMPTY, 6, false, { point: [0, 0] }), { v, list } = read(model3mf(ring)!);
  assert.equal(list.length, 12);
  const balls = list.slice(0, 6).map((s) => s.middle);
  for (const b of ring.bonds) assert.ok(Math.abs(dist(balls[b.atoms[0]], balls[b.atoms[1]]) - 20) < 0.5, "a bond is 20 mm");
  assert.ok(Math.max(...balls.map((b) => b[2])) - Math.min(...balls.map((b) => b[2])) > 3, "a chair, not flat");
  assert.equal(Math.min(...v.map((q) => Math.min(...q))), 0, "the model starts at the origin");
  assert.ok(Math.max(...v.flat()) < 60, "a hand-sized model");
  assert.ok(ring.atoms.every((a) => !a.location[2]), "the drawing does not change");
}
// A stereocentre keeps the hand its wedge draws (as clean3d.check: N up, O wedged down right, C down left), and the
// hashed one the other hand.
{
  const h = Math.sqrt(3) / 2;
  const centre: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "N", location: [0, 1, 0] }, { label: "O", location: [h, -0.5, 0] }, { label: "C", location: [-h, -0.5, 0] }, { label: "C", location: [-h, 0.5, 0] }],
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [0, 2], stereo: 1 }, { type: 1, atoms: [0, 3] }, { type: 1, atoms: [3, 4] }] };
  const hand = (m: Mol) => { const b = read(model3mf(m)!).list.map((s) => s.middle); return Math.sign(vol(b[0], b[1], b[2], b[3])); };
  assert.equal(hand(centre), -1, "the hand its wedge draws");
  assert.equal(hand({ ...centre, bonds: centre.bonds.map((b, k) => (k === 1 ? { ...b, stereo: 6 } : b)) }), 1, "a hash: the other hand");
}
// A structure in 3D already keeps its shape: a right angle stays one. A hydrogen bond has no stick.
{
  const bent: Mol = { atoms: [{ label: "C", location: [0, 0, 0.1] }, { label: "C", location: [1, 0, 0.1] }, { label: "O", location: [1, 1, 0.1] }, { label: "H", location: [3, 1, 0.1] }],
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }, { type: HBOND, atoms: [2, 3] }] };
  const { list } = read(model3mf(bent)!), [a, b, c] = list.map((s) => s.middle);
  assert.equal(list.length, 6, "four balls and two sticks");
  assert.ok(Math.abs(dist(a, c) - 20 * Math.SQRT2) < 0.05, "the right angle as it was");
}
// A long structure is made smaller to fit 150 mm; more than 500 atoms is refused; no atoms, no model.
{
  let chain = addRing(EMPTY, 6, false, { point: [0, 0] });
  for (let k = 1; k < 8; k++) chain = addRing(chain, 6, false, { point: [k * 3, 0] });
  const joined = { ...chain, bonds: [...chain.bonds, ...Array.from({ length: 7 }, (_, k) => ({ type: 1, atoms: [k * 6 + 1, k * 6 + 6] as [number, number] }))] };
  const { v } = read(model3mf(joined)!);
  assert.ok(Math.abs(Math.max(...v.flat()) - 150) < 0.01, `150 mm on its longest side: ${Math.max(...v.flat())}`);
  let big = EMPTY;
  for (let k = 0; k < 84; k++) big = addRing(big, 6, false, { point: [k * 3, 0] });
  assert.throws(() => model3mf(big), /^Error: Octet cannot export more than 500 atoms as a 3D model\.$/);
  assert.equal(model3mf(EMPTY), undefined);
}

// Export BMP… is a picture in pixels on white, or the page's colour: never transparent.
{
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="20pt" height="10pt" viewBox="3 4 20 10"><g/></svg>';
  assert.ok(RASTERS.includes("bmp"));
  assert.equal(pictureAs(svg, { format: "bmp", margin: 0, background: "transparent" }).transparent, false);
  assert.match(pictureAs(svg, { format: "bmp", margin: 0, background: "page" }, "#FFEEDD").svg, /<rect [^>]*fill="#FFEEDD"/);
}
// Both are in File > More Formats, after Check Structure when it is on, from the selection or the whole drawing, and
// export.rs writes them.
{
  const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), rust = readFileSync(new URL("../src-tauri/src/export.rs", import.meta.url), "utf8");
  assert.match(editor, /\["more_bmp", "Export BMP…", <FileImage size=\{18\} \/>, \(\) => checkFirst\(\(\) => void quickExport\("bmp"\)\)\],/);
  assert.match(editor, /\["more_3mf", "Export 3MF…", <CubeFocus size=\{18\} \/>, \(\) => checkFirst\(\(\) => void exportModel\(\)\)\],/);
  assert.match(editor, /async function quickExport\(format = filePrefs\.quick\) \{\n\s+const part = selectedPart\(\) \?\? doc,/);
  assert.match(editor, /const model = model3mf\(selectedPart\(\) \?\? doc\);[\s\S]{0,200}exportFile\(\{ name, format: "3mf", model \}\)/);
  assert.match(rust, /\("bmp", "Windows Bitmap \(BMP\)", &\["bmp"\]\),\n\s+\("3mf", "3D Manufacturing Format for Printing \(3MF\)", &\["3mf"\]\),/);
  assert.match(rust, /"svg" \| "png" \| "emf" \| "eps" \| "tif" \| "jpg" \| "gif" \| "bmp" => e\.svg\.is_some\(\),/);
  assert.match(rust, /"3mf" => e\.model\.is_some\(\),/);
  assert.match(rust, /"bmp" => make_bmp\(e\.svg\.as_deref\(\)\.unwrap_or_default\(\), e\.dpi\.unwrap_or\(300\.0\)\)\?,\n\s+"3mf" => make_3mf\(e\.model\.as_deref\(\)\.unwrap_or_default\(\)\)\?,/);
}
console.log("model3mf.check: 3MF model and BMP ok");
