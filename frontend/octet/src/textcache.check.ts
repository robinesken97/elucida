// Run: node src/textcache.check.ts. Fails loudly if the text Octet measures is kept without end (issue 2): label
// outlines (2000 texts), caption widths and caption extents (10,000 texts each) keep the ones used last, and the one
// used longest ago goes first.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts reads the drawing tokens, measures with a canvas and loads Indigo's wasm as a browser does; these stand in
// for the browser. measured counts the texts the canvas measures.
const measured: string[] = [];
const context = { font: "", measureText: (t: string) => { measured.push(t); return { width: t.length, actualBoundingBoxAscent: 7, actualBoundingBoxDescent: 2 }; }, fillText() {}, getImageData: (_x: number, _y: number, w: number, h: number) => ({ data: new Uint8ClampedArray(w * h * 4) }) };
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => context }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { measurer, textExtent, textWidth } = await import("./chem.ts");

// Measures with `measure` the texts "t0" to "t{count - 1}", keeps using "kept", then measures "t0" and "kept" again:
// "kept" is still known, and "t0", used longest ago, is measured again.
function bounded(name: string, count: number, measure: (t: string) => unknown) {
  measure("kept");
  for (let i = 0; i < count; i++) { measure(`t${i}`); if (i % 100 === 0) measure("kept"); }
  measured.length = 0;
  measure("kept");
  assert.deepEqual(measured, [], `${name}: a text used lately is kept`);
  measure("t0");
  assert.deepEqual(measured, ["t0"], `${name}: the text used longest ago goes`);
  measured.length = 0;
  measure(`t${count - 1}`);
  assert.deepEqual(measured, [], `${name}: the newest texts are kept`);
}
bounded("caption widths", 10_000, (t) => textWidth(t, 12));
bounded("caption extents", 10_000, (t) => textExtent(t, 12));
const label = measurer("Arial", 2);
bounded("label outlines", 2000, label);
// A width is the same, kept or not.
assert.equal(textWidth("OMe", 12), textWidth("OMe", 12));
assert.equal(textWidth("OMe", 12), (3 / 100) * 12);

console.log("textcache: ok");
