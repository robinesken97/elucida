// Run: node src/ligand.check.ts. Fails loudly if ChemDraw's j and Shift+J π ligands, or the multi-centre points they
// are joined through, stop working: drawing, deleting, copying, CDXML and chemistry.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { EMPTY, addGroupAt, bondTo, clickBond, deleteAtoms, dragBond, extractSelection, fragments, insertMol, moveAtoms, neighbours, placeCentres, pos, sandwich, sprout, toFront } from "./edit.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { parse, serialize } from "./file.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { ligandEllipse, render, type Ink, type Mol } from "./render.ts";

const iron: Mol = { atoms: [{ label: "Fe", location: [0, 0, 0] }], bonds: [] };
const centres = (m: Mol) => m.atoms.flatMap((a, i) => (a.centre ? [i] : []));

// j on a lone metal: a Cp ring below it, joined through a multi-centre point; the hotspot stays on the metal.
let [m, hot] = addGroupAt(iron, 0, "cpLigand");
assert.equal(hot, 0);
assert.equal(centres(m).length, 1);
const p = centres(m)[0], ring = m.atoms[p].centre!.atoms;
assert.equal(ring.length, 5);
assert.ok(pos(m, p)[1] < 0, "below the metal");
assert.deepEqual(neighbours(m, p), [0], "the metal is bonded to the point");
const ringBonds = m.bonds.filter((b) => ring.includes(b.atoms[0]) && ring.includes(b.atoms[1]));
assert.equal(ringBonds.length, 5);
assert.ok(ringBonds.every((b) => b.type === 4), "delocalised ring bonds");
assert.equal(ringBonds.filter((b) => b.stereo === 1).length, 2, "the front atom between two wedges");
// The wedges are wide at the front atom, the lowest one.
const front = ring.reduce((a, b) => (pos(m, a)[1] < pos(m, b)[1] ? a : b));
assert.ok(ringBonds.filter((b) => b.stereo === 1).every((b) => b.atoms[1] === front));
// The point is the middle of its ring.
const mid = [0, 1].map((k) => ring.reduce((s, i) => s + pos(m, i)[k], 0) / 5);
assert.ok(Math.hypot(mid[0] - pos(m, p)[0], mid[1] - pos(m, p)[1]) < 1e-9);
// j again: a staggered Cp above (a bold front bond); a third time the metal has two bonds and nothing happens.
[m, hot] = addGroupAt(m, 0, "cpLigand");
assert.equal(centres(m).length, 2);
const upper = m.atoms[centres(m)[1]].centre!.atoms;
assert.ok(pos(m, centres(m)[1])[1] > 0, "above the metal");
assert.equal(m.bonds.filter((b) => upper.includes(b.atoms[0]) && upper.includes(b.atoms[1]) && b.display === "bold").length, 1);
assert.equal(addGroupAt(m, 0, "cpLigand")[0], m);
const ferrocene = m;
// Ferrocene is one structure.
assert.equal(fragments(ferrocene).length, 1);
console.log("ligand.check: Cp on a metal ok");

// Shift+J on a chain end: the end atom becomes the point of a phenyl ring; the hotspot moves to the other end.
const ethane = sprout(EMPTY, [0, 0]);
const [arene, next] = addGroupAt(ethane, 1, "phenylLigand");
assert.equal(next, 0);
assert.equal(arene.atoms[1].centre?.atoms.length, 6);
assert.equal(arene.bonds.filter((b) => b.display === "bold").length, 1);
assert.equal(arene.bonds.filter((b) => b.stereo === 1).length, 2);
// Not on an atom with two bonds.
const propane = sprout(ethane, 1);
assert.equal(addGroupAt(propane, 1, "phenylLigand")[0], propane);
console.log("ligand.check: phenyl on a chain end ok");

// Deleting the ring takes the point (and with it the bond to the metal); deleting one ring atom keeps it.
const lower = ferrocene.atoms[centres(ferrocene)[0]].centre!.atoms;
const gone = deleteAtoms(ferrocene, new Set(lower));
assert.equal(centres(gone).length, 1);
assert.equal(gone.atoms.length, ferrocene.atoms.length - 6);
const one = deleteAtoms(ferrocene, new Set([lower[0]]));
assert.equal(one.atoms[centres(one)[0]].centre!.atoms.length, 4);
// Moving a ring moves its point (as the editor keeps it).
const moved = placeCentres(moveAtoms(ferrocene, new Set(lower), [3, 0]));
assert.ok(Math.abs(pos(moved, centres(moved)[0])[0] - 3) < 1e-9);
// Its ellipse keeps the ring's flattening, though the bond to the metal now leans (issue 6).
const axes = (x: Mol) => { const c = centres(x)[0], r = x.atoms[c].centre!.atoms, q = (i: number) => pos(x, i) as [number, number]; return ligandEllipse(r.map(q), q(c), q(neighbours(x, c)[0]), 0.18); };
const [was, now] = [axes(ferrocene), axes(moved)];
assert.ok(Math.abs(Math.abs(was.along[0] * now.along[0] + was.along[1] * now.along[1]) - 1) < 1e-9 && Math.abs(was.rb - now.rb) < 1e-9, "the ellipse moves with its ring");
// Copy and paste keep the point on the copied ring.
const copy = extractSelection(ferrocene, new Set(ferrocene.atoms.map((_, i) => i)), new Set());
const twice = insertMol(ferrocene, copy, [10, 0]).mol;
assert.equal(centres(twice).length, 4);
assert.ok(centres(twice).slice(2).every((i) => twice.atoms[i].centre!.atoms.every((j) => j >= ferrocene.atoms.length)));
console.log("ligand.check: delete, move and copy ok");

// CDXML: a MultiAttachment node with its Attachments, and the ring's 1.5 bonds with their styles, read back the same.
const xml = toCdxml(ferrocene, DEFAULT_STYLE);
assert.equal((xml.match(/NodeType="MultiAttachment"/g) ?? []).length, 2);
const back = fromCdxml(xml);
assert.equal(back.lost.MultiAttachment, undefined, JSON.stringify(back.lost));
assert.equal(centres(back.mol).length, 2);
assert.deepEqual(back.mol.atoms.map((a) => a.centre?.atoms.length ?? 0).filter(Boolean), [5, 5]);
const style = (x: Mol) => x.bonds.map((b) => `${b.type}${b.stereo ?? ""}${b.display ?? ""}`).sort().join(" ");
assert.equal(style(back.mol), style(ferrocene));
// ChemDraw does not draw a ligand's ellipse itself, so it is written as an oval; reading it back drops it again.
assert.equal((xml.match(/GraphicType="Oval"/g) ?? []).length, 2);
assert.equal(back.mol.shapes?.length ?? 0, 0);
const second = toCdxml(back.mol, back.style);
assert.equal(toCdxml(fromCdxml(second).mol, back.style), second, "saving again changes nothing");
// A closed curve inside a ligand's ring (ChemDraw's own Cp ligands have one) is the ellipse Octet draws.
const curve = xml.replace("</fragment>", `<curve id="9999" Closed="yes" CurvePoints="${(() => {
  const c = /<n\s+id="\d+"\s+p="([\d.]+) ([\d.]+)"[^>]*NodeType="MultiAttachment"/.exec(xml)!, [x, y] = [Number(c[1]), Number(c[2])];
  return [[-5, 0], [0, 2], [5, 0], [0, -2]].flatMap(([dx, dy]) => [x + dx, y + dy, x + dx, y + dy, x + dx, y + dy]).join(" ");
})()}"/></fragment>`);
assert.equal(fromCdxml(curve).mol.arrows?.filter((a) => a.kind === "curve").length ?? 0, 0);
console.log("ligand.check: CDXML ok");

// Octet's own JSON (the clipboard between Octet windows, templates and the copy inside .oct files) keeps the points
// and the ring's delocalised bonds, and refuses a point that stands for itself, a missing atom, one atom or a point.
const json = parse(serialize(ferrocene));
assert.deepEqual(json.atoms.map((a) => a.centre), ferrocene.atoms.map((a) => a.centre));
assert.equal(style(json), style(ferrocene));
const raw = JSON.parse(serialize(ferrocene)), point = centres(ferrocene)[0];
for (const bad of [[point, 2], [2, 999], [2], [2, centres(ferrocene)[1]], "2 3"]) {
  raw.structure.atoms[point].centre = bad;
  assert.throws(() => parse(JSON.stringify(raw)), /damaged/);
}
console.log("ligand.check: Octet JSON ok");

// Drawing: the point has no label, and each ring has an ellipse inside.
const ink = (): Ink => ({ width: 9.6, ascent: 9.5, outline: [[0, 0], [9.6, -9.5]] });
const S = { bond: 19.2, line: 0.8, bold: 2.67, spacing: 0.18 * 19.2, hash: 3.33, margin: 2.25, size: 13.3 };
const drawn = render(ferrocene, S, ink), plain = render({ ...ferrocene, atoms: ferrocene.atoms.map(({ centre: _, ...a }) => a) }, S, ink);
assert.equal(drawn.labels.filter((l) => l.text !== "Fe").length, 0, "no label on the points");
assert.ok(drawn.polygons.length > plain.polygons.length + 100, "two ellipses");
// Where the bond to the point crosses its ring, the ring's near (bold or wedged) edge is in front of the bond and its
// far edge behind it (issue 6). onTop(x, metal, point, edge): whether the bond from the metal to the point is drawn
// whole where it crosses the level ring edge (atoms edge), the edge being cut round it.
type P = [number, number];
const inside = (poly: P[], q: P) => { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) if ((poly[i][1] > q[1]) !== (poly[j][1] > q[1]) && q[0] < ((poly[j][0] - poly[i][0]) * (q[1] - poly[i][1])) / (poly[j][1] - poly[i][1]) + poly[i][0]) c = !c; return c; };
const onTop = (x: Mol, metal: number, point: number, edge: number[]) => {
  const d = render(x, S, ink, S.bond), covered = (q: P) => d.polygons.some((poly) => inside(poly, q)), at = (i: number): P => [pos(x, i)[0] * S.bond, -pos(x, i)[1] * S.bond];
  const [a, b] = [at(metal), at(point)], y = at(edge[0])[1], t = (y - a[1]) / (b[1] - a[1]), cx = a[0] + t * (b[0] - a[0]), out = Math.sign(y - b[1]);
  assert.ok(Math.abs(at(edge[1])[1] - y) < 1e-6 && t > 0 && t < 1, "the bond crosses the edge");
  // On the bond 2 px outside the edge, and on the edge 1.5 px to the side of the bond: inside the gap cut in the one
  // behind, clear of the one in front.
  const bond = covered([cx, y + 2 * out]), side = covered([cx + 1.5, y]);
  assert.notEqual(bond, side, "one of the two is cut");
  return bond;
};
{
  const [cp] = addGroupAt(iron, 0, "cpLigand"), c = centres(cp)[0], r = cp.atoms[c].centre!.atoms;
  // j on a lone metal: the Cp below it; the bond comes down through the ring's far side.
  const far = r.filter((i) => Math.abs(pos(cp, i)[1] - Math.max(...r.map((j) => pos(cp, j)[1]))) < 1e-9);
  assert.equal(onTop(cp, 0, c, far), true, "the bond is in front of a Cp's far edge");
  // It comes from the bonds' order, so CDXML (bond Z) carries it, and Bring to Front on the far edge changes it.
  assert.equal(onTop(fromCdxml(toCdxml(cp, DEFAULT_STYLE)).mol, 0, c, far), true, "CDXML keeps the order");
  assert.equal(onTop(toFront(cp, new Set(far)), 0, c, far), false, "Bring to Front puts the far edge in front");
  // j again: the Cp above; the bond goes up through its bold near edge.
  const [both] = addGroupAt(cp, 0, "cpLigand"), u = centres(both)[1], ur = both.atoms[u].centre!.atoms;
  assert.equal(onTop(both, 0, u, ur.filter((i) => Math.abs(pos(both, i)[1] - Math.min(...ur.map((j) => pos(both, j)[1]))) < 1e-9)), false, "the bond is behind a Cp's bold edge");
  // Shift+J below a metal, then the metal moved with the lasso to below the ring: the bond crosses the far edge, then
  // the bold near edge.
  const [ph] = addGroupAt(iron, 0, "phenylLigand"), q = centres(ph)[0], pr = ph.atoms[q].centre!.atoms;
  const level = (x: Mol, top: boolean) => { const ys = pr.map((i) => pos(x, i)[1]), y = top ? Math.max(...ys) : Math.min(...ys); return pr.filter((i) => Math.abs(pos(x, i)[1] - y) < 1e-9); };
  assert.equal(onTop(ph, 0, q, level(ph, true)), true, "the bond is in front of a phenyl's far edge");
  const under = moveAtoms(ph, new Set([0]), [0, -2.5]);
  assert.equal(onTop(under, 0, q, level(under, false)), false, "the bond is behind a phenyl's bold edge");
}
{
  // A Cp from Octet 1.0.x: every ring edge after the bond to the point, so the far edge is drawn over the bond. Octet
  // reorders it once when it opens a 1.0.x file (.oct JSON or Octet's CDXML, neither with an app), and only then.
  const [cp] = addGroupAt(iron, 0, "cpLigand"), c = centres(cp)[0], r = cp.atoms[c].centre!.atoms, edge = (b: Mol["bonds"][number]) => r.includes(b.atoms[0]) && r.includes(b.atoms[1]);
  const far = r.filter((i) => Math.abs(pos(cp, i)[1] - Math.max(...r.map((j) => pos(cp, j)[1]))) < 1e-9);
  const old: Mol = { ...cp, bonds: [...cp.bonds.filter((b) => !edge(b)), ...cp.bonds.filter(edge)] }, order = (x: Mol) => x.bonds.map((b) => b.atoms.join(" "));
  assert.equal(onTop(old, 0, c, far), false, "1.0.x drew the far edge over the bond");
  const json = (x: Mol, app: boolean) => { const d = JSON.parse(serialize(x)); assert.ok(d.app); if (!app) delete d.app; return parse(JSON.stringify(d)); };
  assert.equal(onTop(json(old, false), 0, c, far), true, "a 1.0.x .oct opens with the far edge behind the bond");
  assert.deepEqual(order(json(old, true)), order(old), "a 1.1.0 .oct is unchanged");
  // A 1.0.x Cp whose bond to the point the user brought to the front stays as it is.
  const front = { ...old, bonds: [...old.bonds.filter((b) => b.atoms.includes(c) === false), ...old.bonds.filter((b) => b.atoms.includes(c))] };
  assert.deepEqual(order(json(front, false)), order(front), "a Bring to Front is kept");
  const xml = toCdxml(old, DEFAULT_STYLE);
  assert.ok(/&quot;app&quot;:&quot;[^&]+&quot;,/.test(xml));
  assert.equal(onTop(fromCdxml(xml.replace(/&quot;app&quot;:&quot;[^&]+&quot;,/, "")).mol, 0, c, far), true, "Octet 1.0.x CDXML opens with the far edge behind the bond");
  assert.deepEqual(order(fromCdxml(xml).mol), order(old), "Octet 1.1.0 CDXML is unchanged");
  // ChemDraw's file (no Octet attributes) keeps its own order.
  const chemdraw = fromCdxml(xml.replace(/ Octet="[^"]*"/g, "")).mol;
  assert.ok(chemdraw.atoms[c].centre, "ChemDraw's file has the point");
  assert.deepEqual(order(chemdraw), order(old), "a ChemDraw file is unchanged");
}
console.log("ligand.check: drawing ok");

// Chemistry: the points are not atoms; ferrocene is one compound, C10H10Fe, as ChemDraw gives it (chem.ts analyse).
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { analyse, expandLabels, parseStructure, ready, stereoFacts, toInchi, toSmiles } = await import("./chem.ts");
const { problems } = await import("./check.ts");
const { sandwichIons } = await import("./metals.ts");
await ready;
assert.equal(expandLabels(ferrocene).atoms.length, ferrocene.atoms.length - 2);
assert.equal(expandLabels(ferrocene).bonds.length, ferrocene.bonds.length - 2);
const formulas = analyse(ferrocene)?.map((a) => a.formula).sort();
assert.deepEqual(formulas, ["C10H10Fe"]);
console.log("ligand.check: chemistry ok");

// Name to Structure: a metallocene's ions (OPSIN's ferrocene) are drawn as the j key draws it, the same compound.
for (const [smiles, formula] of [["[Fe+2].[cH-]1cccc1.[cH-]1cccc1", "C10H10Fe"], ["[Ni+2].[CH-]1C=CC=C1.[CH-]1C=CC=C1", "C10H10Ni"],
  ["[Fe+2].OC(=O)[c-]1cccc1.[cH-]1cccc1", "C11H10FeO2"], ["[Fe+2].P(c1ccccc1)(c1ccccc1)[c-]1cccc1.P(c1ccccc1)(c1ccccc1)[c-]1cccc1", "C34H28FeP2"]]) {
  const ions = parseStructure(smiles), drawn = sandwich(ions), metal = drawn.atoms.findIndex((a) => a.label === "Fe" || a.label === "Ni");
  assert.equal(centres(drawn).length, 2, smiles);
  assert.deepEqual(neighbours(drawn, metal).sort((x, y) => x - y), centres(drawn), "the metal is bonded to the two points");
  assert.ok(drawn.atoms.every((a) => !a.charge), "no charges");
  assert.equal(fragments(drawn).length, 1);
  assert.deepEqual(analyse(drawn)?.map((a) => a.formula), [formula]);
  assert.equal(toInchi(sandwichIons(drawn)!), toInchi(ions), "named as the same ions");
  // One point above the metal, one below, as the j key puts them.
  assert.deepEqual(centres(drawn).map((c) => Math.sign(pos(drawn, c)[1] - pos(drawn, metal)[1])).sort(), [-1, 1]);
}
// dppf's substituents point away from the metal: no two atoms of different rings' groups closer than a bond.
const dppf = sandwich(parseStructure("[Fe+2].P(c1ccccc1)(c1ccccc1)[c-]1cccc1.P(c1ccccc1)(c1ccccc1)[c-]1cccc1"));
const ps = dppf.atoms.flatMap((a, i) => (a.label === "P" ? [i] : []));
// Each P and what hangs on it, short of its ring.
const ringAtoms = new Set(centres(dppf).flatMap((c) => dppf.atoms[c].centre!.atoms));
const side = (p: number) => { const seen = new Set([p]), todo = [p]; while (todo.length) for (const j of neighbours(dppf, todo.pop()!)) if (!seen.has(j) && !ringAtoms.has(j)) { seen.add(j); todo.push(j); } return [...seen]; };
const [a, b] = ps.map(side);
assert.ok(a.every((i) => b.every((j) => Math.hypot(pos(dppf, i)[0] - pos(dppf, j)[0], pos(dppf, i)[1] - pos(dppf, j)[1]) > 1)), "dppf's phenyl rings apart");
// Left as ions: a lone ring, three rings, other ions (OPSIN's titanocene dichloride), and rings joined to each other
// through another metal (Pd(dppf)Cl2).
for (const smiles of ["[Fe+2].[cH-]1cccc1", "[Fe+2].[cH-]1cccc1.[cH-]1cccc1.[cH-]1cccc1", "[Cl-].[Cl-].[CH-]1C=CC=C1.[CH-]1C=CC=C1.[Ti+2]", "Cl[Pd]1(Cl)P(C2=CC=CC=C2)(C2=CC=CC=C2)[C-]2C=CC=C2.[C-]2(C=CC=C2)P1(C1=CC=CC=C1)C1=CC=CC=C1.[Fe+2]"]) {
  const m = parseStructure(smiles);
  assert.equal(sandwich(m), m, smiles);
}
console.log("ligand.check: metallocene names ok");

// Issue 26: a bond from a metal let go over the middle of a ring (or from the middle of a ring to a metal) joins the
// ring through a new multi-centre point, as Add Multi-Centre Attachment and a bond from it do. A ring here is drawn
// flat, as the Ring tool draws it: n atoms round centre c, bond types in turn.
function flatRing(m: Mol, c: [number, number], types: number[]): Mol {
  const n = types.length, R = 1 / (2 * Math.sin(Math.PI / n)), base = m.atoms.length;
  const atoms = types.map((_, k): Mol["atoms"][number] => ({ label: "C", location: [c[0] + R * Math.cos((2 * Math.PI * k) / n + Math.PI / 2), c[1] + R * Math.sin((2 * Math.PI * k) / n + Math.PI / 2), 0] }));
  return { ...m, atoms: [...m.atoms, ...atoms], bonds: [...m.bonds, ...types.map((t, k) => ({ type: t, atoms: [base + k, base + ((k + 1) % n)] as [number, number] }))] };
}
const CP = [2, 1, 2, 1, 1], BENZENE = [2, 1, 2, 1, 2, 1], CYCLOHEXANE = [1, 1, 1, 1, 1, 1];
{
  // Ferrocene as the issue drew it: Fe, two cyclopentadiene rings, a bond from Fe to the middle of each.
  let fc = flatRing(flatRing(iron, [0, -2], CP), [0, 2], CP);
  fc = dragBond(fc, 0, [0, -2.1]);
  fc = dragBond(fc, [0.1, 2.05], [0.02, 0.03]);
  assert.equal(centres(fc).length, 2, "two multi-centre points");
  assert.deepEqual(centres(fc).map((c) => fc.atoms[c].centre!.atoms.length), [5, 5]);
  assert.deepEqual(neighbours(fc, 0).sort((x, y) => x - y), centres(fc), "the metal is bonded to the two points, no stray atom");
  assert.ok(Math.hypot(...(pos(fc, centres(fc)[0]) as [number, number, number]).slice(0, 2).map((v, k) => v - [0, -2][k])) < 1e-9, "the point is the ring's middle");
  assert.equal(fragments(fc).length, 1);
  assert.deepEqual(analyse(fc)?.map((a) => a.formula), ["C10H10Fe"]);
  // Its SMILES is the ions, as OPSIN and PubChem write it: [Fe+2].[CH-]1C=CC=C1.[CH-]1C=CC=C1.
  assert.ok(toSmiles(fc).startsWith("[Fe+2].") && toSmiles(fc).split("[CH-]").length === 3, toSmiles(fc));
  assert.equal(toInchi(fc), toInchi(parseStructure("[Fe+2].[CH-]1C=CC=C1.[CH-]1C=CC=C1")));
  assert.deepEqual(problems(fc, stereoFacts(fc)), [], "no warnings");
  // The j key's ferrocene reads the same.
  assert.equal(toInchi(ferrocene), toInchi(fc));
  // (η6-benzene)tricarbonylchromium: one compound, the metal bonded to each ring atom, each CH keeping its H.
  let cr: Mol = flatRing({ atoms: [{ label: "Cr", location: [0, 0, 0] }], bonds: [] }, [0, -2], BENZENE);
  cr = dragBond(cr, 0, [0.05, -2]);
  for (const t of [30, 90, 150]) {
    const d: [number, number] = [Math.cos((t * Math.PI) / 180), Math.sin((t * Math.PI) / 180)];
    cr = bondTo(cr, 0, d, { type: 2 });
    cr = bondTo(cr, cr.atoms.length - 1, [2 * d[0], 2 * d[1]], { type: 2 });
    cr = { ...cr, atoms: cr.atoms.map((a, i) => (i === cr.atoms.length - 1 ? { ...a, label: "O" } : a)) };
  }
  assert.equal(centres(cr).length, 1);
  const flat = expandLabels(cr), crIndex = flat.atoms.findIndex((a) => a.label === "Cr");
  assert.equal(flat.bonds.filter((b) => b.atoms.includes(crIndex)).length, 9, "six η bonds and three carbonyls");
  assert.deepEqual(analyse(cr)?.map((a) => a.formula), ["C9H6CrO3"]);
  assert.equal(fragments(cr).length, 1);
  assert.ok(problems(cr, stereoFacts(cr)).every((x) => x.type !== "near"), "no stray atom");
  // The j key's delocalised ring reads the same as the Ring tool's.
  const [jcr] = addGroupAt({ atoms: [{ label: "Cr", location: [0, 0, 0] }], bonds: [] }, 0, "phenylLigand");
  assert.equal(toInchi(jcr), toInchi(parseStructure("[Cr].c1ccccc1")), "C6H6 and Cr, as the standard InChI splits a metal off");
  assert.ok(problems(jcr, stereoFacts(jcr)).length === 0, "the ring's perspective wedges set no stereocentre");
  // Not taken: a bond from a carbon, a bond from a metal to the middle of a saturated ring, a bond from a metal let go
  // away from the middle, and a ring that already has its point (the bond goes to that point, as to any atom).
  const ring = flatRing({ atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [] }, [0, -2], BENZENE);
  assert.equal(centres(dragBond(ring, 0, [0, -2])).length, 0, "a carbon's bond is a bond");
  const cy = flatRing(iron, [0, -2], CYCLOHEXANE);
  assert.equal(centres(dragBond(cy, 0, [0, -2])).length, 0, "no η bond to a saturated ring");
  const cpOnly = flatRing(iron, [0, -2], CP), off = dragBond(cpOnly, 0, [0.5, -1.6]);
  assert.equal(centres(off).length, 0, "away from the middle, an ordinary bond");
  assert.equal(off.atoms.length, cpOnly.atoms.length + 1);
  const again = dragBond(fc, 0, pos(fc, centres(fc)[0]) as unknown as [number, number]);
  assert.equal(centres(again).length, 2, "a point already there takes the bond");
  assert.equal(again, fc, "a drag along the metal's bond to its point changes nothing (no double bond)");
  assert.equal(dragBond(fc, centres(fc)[0], pos(fc, 0) as unknown as [number, number]), fc, "nor from the point to the metal");
  const toPoint = fc.bonds.findIndex((b) => b.atoms.includes(centres(fc)[0]));
  assert.equal(clickBond(fc, toPoint, { type: 1 }, [0, -1]), fc, "a click with the Solid bond tool keeps it single");
  assert.equal(clickBond(fc, toPoint, { type: 2 }, [0, -1]), fc, "and the Double bond tool too");
  assert.equal(clickBond(fc, toPoint, { type: 1, display: "dashed" }, [0, -1]).bonds[toPoint].display, "dashed", "its style still changes");
  // A metal already bonded to one ring atom (or several), dragged to the ring's middle: the ring is η bonded, through
  // a point, and the bonds to its atoms go (issue 26: no second bond on top).
  for (const to of [[1], [1, 2, 3]]) {
    let one = flatRing(iron, [0, -2], CP);
    for (const r of to) one = { ...one, bonds: [...one.bonds, { type: 1, atoms: [0, r] }] };
    const eta = dragBond(one, 0, [0, -2]);
    assert.equal(centres(eta).length, 1, `η from ${to.length} bond`);
    assert.deepEqual(neighbours(eta, 0), centres(eta), "the metal's only bond is to the point");
    assert.equal(eta.bonds.length, 5 + 1);
    assert.equal(toInchi(eta), toInchi(dragBond(flatRing(iron, [0, -2], CP), 0, [0, -2])), "the same as a ring with no bond first");
    // From the middle to the metal, the same.
    assert.deepEqual(neighbours(dragBond(one, [0.02, -2.03], [0, 0.02]), 0).length, 1);
  }
  // A ring turned in 3D: the point is its middle in depth too.
  const deep = flatRing(iron, [0, -2], CP), tilted = { ...deep, atoms: deep.atoms.map((a, i) => (i ? { ...a, location: [a.location[0], a.location[1], 0.5 + 0.1 * i] as [number, number, number] } : a)) };
  const lifted = dragBond(tilted, 0, [0, -2]), point = lifted.atoms[centres(lifted)[0]];
  assert.ok(Math.abs((point.location[2] ?? 0) - (0.5 + 0.1 * 3)) < 1e-9, `the point's depth: ${point.location[2]}`);
}
console.log("ligand.check: bonds to a ring's middle ok");
