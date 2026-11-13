// Run: node src/photochem.check.ts. The library's Photochemistry set (tools/library/photochem.mjs): Octet's own
// arrows, text and brackets in the Lab group's style (the document's line width and caption style, no colour of their
// own), radiative transitions straight and radiationless ones wavy, and each template placed whole and back the same
// from CDXML, CDX and a .oct file.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { addRing, addTemplate, EMPTY, withCaptionAtoms } from "./edit.ts";
import { readCdx, readOct, writeCdx, writeOct } from "./oct.ts";
import type { Arrow, Caption, Mol } from "./render.ts";

const more: { sets: { name: string; items: { name: string; also?: string; mol: Mol }[] }[] } = JSON.parse(readFileSync(new URL("./library-more.json", import.meta.url), "utf8"));
const set = more.sets.find((c) => c.name === "Photochemistry")!.items;
assert.deepEqual(set.map((t) => t.name), ["Jablonski diagram", "Light", "Photochemical step", "Thermal step", "Absorption", "Fluorescence", "Phosphorescence",
  "Intersystem crossing", "Internal conversion", "Excited state", "Singlet oxygen", "Triplet oxygen", "Ground state", "Singlet excited state",
  "Triplet excited state", "Sensitiser", "Excited sensitiser"]);
const item = (name: string) => set.find((t) => t.name === name)!.mol;
const len = (a: Arrow) => Math.hypot(a.to[0] - a.from[0], a.to[1] - a.from[1]);
const plain = (c: Caption) => (c.runs ?? [{ text: c.text }]).map((r) => `${"script" in r && r.script === "sub" ? "_" : "script" in r && r.script === "super" ? "^" : ""}${r.text}`).join("");

for (const { name, mol } of set) {
  // The Lab group's style: nothing sets its own line width, size, colour or font, so each follows the document.
  assert.equal(mol.atoms.length + mol.bonds.length, 0, name);
  assert.ok([...mol.arrows ?? [], ...mol.shapes ?? []].every((x) => x.width === undefined && x.scale === undefined && x.colour === undefined), name);
  assert.ok((mol.captions ?? []).every((c) => c.size === undefined && c.font === undefined && c.colour === undefined && !c.bold), name);
  // Centred where it is placed: its lines' box, or its one line of text.
  const ends = [...(mol.arrows ?? []).flatMap((a) => [a.from, a.to]), ...(mol.shapes ?? []).flatMap((x) => [x.from, x.to])];
  if (ends.length) {
    const xs = ends.map((q) => q[0]), ys = ends.map((q) => q[1]);
    assert.ok(Math.abs(Math.min(...xs) + Math.max(...xs)) < 0.01 && Math.abs(Math.min(...ys) + Math.max(...ys)) < 0.01, `${name} is centred`);
  } else assert.deepEqual(mol.captions!.map((c) => [c.x, c.y]), [[0, -0.25]], `${name} is centred`);
  // Conditions are on an arrow of the template.
  for (const c of mol.captions ?? []) if (c.on) assert.ok(mol.arrows?.some((a) => a.id === c.on!.arrow), name);
}
// Radiative transitions straight, radiationless ones wavy (IUPAC); each lone arrow the same length, its wave ending on
// the axis where the default style's head starts (0.365 bond lengths and a whole number of half waves).
const arrow = (name: string) => item(name).arrows![0];
for (const name of ["Absorption", "Fluorescence", "Phosphorescence"]) assert.equal(arrow(name).style, undefined, name);
for (const name of ["Light", "Intersystem crossing", "Internal conversion"]) assert.equal(arrow(name).style, "wavy", name);
for (const name of ["Light", "Photochemical step", "Thermal step", "Absorption", "Fluorescence", "Phosphorescence", "Intersystem crossing", "Internal conversion"]) {
  const halves = (len(arrow(name)) - 0.365) / 0.1;
  assert.ok(Math.abs(halves - Math.round(halves)) < 0.01, `${name}: ${len(arrow(name))} bond lengths`);
}
assert.ok(arrow("Absorption").to[1] > arrow("Absorption").from[1] && arrow("Fluorescence").to[1] < arrow("Fluorescence").from[1], "absorption up, emission down");
assert.deepEqual(["Photochemical step", "Thermal step"].map((n) => [arrow(n).kind, plain(item(n).captions![0])]), [["reaction", "hν"], ["reaction", "Δ"]]);
assert.ok(item("Light").captions![0].italic, "h and ν are quantities: italic");
// The Jablonski diagram: three levels and two vibrational levels each, absorption, fluorescence, phosphorescence and a
// wavy intersystem crossing, each labelled, in one group that is not integral (a double-click picks a part).
const jab = item("Jablonski diagram"), heads = jab.arrows!.filter((a) => a.end === "full");
assert.equal(jab.arrows!.length - heads.length, 9);
assert.deepEqual(heads.map((a) => [a.style ?? "", plain(jab.captions!.find((c) => c.on?.arrow === a.id)!)]), [["", "hν_A"], ["", "hν_F"], ["wavy", "ISC"], ["", "hν_P"]]);
assert.deepEqual(jab.captions!.filter((c) => !c.on).map(plain), ["S_0", "S_1", "T_1"]);
assert.deepEqual(jab.groups?.map((g) => [g.items.length, !!g.integral]), [[jab.arrows!.length + jab.captions!.length, false]]);
assert.deepEqual(item("Excited state").shapes!.map((x) => [x.kind, x.mark]), [["brackets", "*"]]);
assert.deepEqual(["Singlet oxygen", "Triplet oxygen"].map((n) => plain(item(n).captions![0])), ["^1O_2", "^3O_2"]);
// State labels are text, not chemistry: S1 is no sulfur and T1 no tritium in the formula, the mass or the warnings.
assert.equal(withCaptionAtoms(set.reduce((m, t, k) => addTemplate(m, t.mol, { point: [0, -4 * k] }), EMPTY), true).mol.atoms.length, 0);

const look = (m: Mol) => ({
  arrows: (m.arrows ?? []).map((a) => [a.kind, a.style ?? "", a.end ?? "", a.from.map((v) => Math.round(v * 100)), a.to.map((v) => Math.round(v * 100))]).sort(),
  captions: (m.captions ?? []).map((c) => [plain(c), !!c.italic, c.align ?? "centre", c.on?.side ?? "", c.chemical ?? true, c.on ? "" : `${Math.round(c.x * 100)} ${Math.round(c.y * 100)}`,
    c.on ? (({ kind, from }) => `${kind} ${from.map((v) => Math.round(v * 100))}`)(m.arrows!.find((a) => a.id === c.on!.arrow)!) : ""]).sort(),
  shapes: (m.shapes ?? []).map((x) => [x.kind, x.mark ?? "", x.from.map((v) => Math.round(v * 100)), x.to.map((v) => Math.round(v * 100))]),
  groups: (m.groups ?? []).map((g) => [g.items.length, !!g.integral]),
});
for (const { name, mol } of set) {
  // Placed at a point beside a ring: all of it, moved there, with new ids (conditions on the new arrows).
  const ring = addRing(EMPTY, 6, false, { point: [-6, 0] }), placed = addTemplate(ring, mol, { point: [10, 5] });
  const moved = { ...mol, arrows: mol.arrows?.map((a) => ({ ...a, from: [a.from[0] + 10, a.from[1] + 5], to: [a.to[0] + 10, a.to[1] + 5] })) as Arrow[],
    captions: mol.captions?.map((c) => ({ ...c, x: c.x + 10, y: c.y + 5 })), shapes: mol.shapes?.map((x) => ({ ...x, from: [x.from[0] + 10, x.from[1] + 5], to: [x.to[0] + 10, x.to[1] + 5] })) } as Mol;
  assert.deepEqual(look(placed), look(moved), `${name} is placed whole`);
  // CDXML (as ChemDraw reads it), CDX and a .oct file give it back: arrows and their heads and waves, text in its runs
  // and style, conditions on their arrows, the brackets' mark and the group.
  const cdxml = fromCdxml(toCdxml(placed, DEFAULT_STYLE));
  assert.deepEqual(cdxml.lost, {}, name);
  assert.deepEqual(look(cdxml.mol), look(placed), `${name} through CDXML`);
  assert.deepEqual(look(readCdx(writeCdx(placed, DEFAULT_STYLE)).mol), look(placed), `${name} through CDX`);
  assert.deepEqual(look(readOct(writeOct(placed, DEFAULT_STYLE)).mol), look(placed), `${name} through .oct`);
}
console.log(`photochem.check: ${set.length} Photochemistry templates in the document's style, placed whole and back the same from CDXML, CDX and .oct ok`);
