// Run: node src/perspective.check.ts. Fails loudly if structures turned in 3D (Structure Perspective) stop drawing as
// ChemDraw draws them, lose their depth, or stop taking new atoms at their depth.
import assert from "node:assert/strict";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { DEFAULT_STYLE } from "./docstyle.ts";
import { parse, serialize } from "./file.ts";
import { messy, problems } from "./check.ts";
import { atomAt, bondAt, bondTo, carryDepth, flattenAtoms, hingeOf, insertMol, tiltAtoms, turnAboutBond } from "./edit.ts";
import { depthRange, render, shadeAt, type Atom, type Bond, type Ink, type Mol } from "./render.ts";

const pt = 1;
// As the app's style: the margin is the label clearance, 1.69 pt for ACS 1996's 1.6 pt Margin Width.
const S = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
const M = 1.6 * pt; // Margin Width
const box: [number, number][] = [[-4.8, -9.5], [4.8, -9.5], [4.8, 0], [-4.8, 0]];
const ink = (): Ink => ({ width: 9.6, ascent: 9.5, outline: box });
const A = (label: string, x: number, y: number, z = 0, more: Partial<Atom> = {}): Atom => ({ label, location: [x, y, z], ...more });
const b = (i: number, j: number, more: Partial<Bond> = {}): Bond => ({ type: 1, atoms: [i, j], ...more });
const xs = (poly: [number, number][]) => poly.map((q) => q[0]), ys = (poly: [number, number][]) => poly.map((q) => q[1]);
const flat = (m: Mol): Mol => ({ ...m, atoms: m.atoms.map((a) => ({ ...a, location: [a.location[0], a.location[1], 0] as [number, number, number] })) });

// A structure turned in 3D is drawn as the same structure drawn flat: every bond style (a dashed double bond, a wedge,
// a dashed bond, a dative bond) at the document's widths, in full ink. Its depth only decides crossings.
{
  const m: Mol = {
    atoms: [A("Rh", 0, 0, 0.4), A("C", 0, -1.2, -0.3), A("C", 1, 0.5, 0.8), A("C", -1, 0.5, -0.8), A("O", 0.9, -1.7, 0.1), A("N", -0.9, -1.7, -0.6)],
    bonds: [b(0, 1, { type: 2, display: "dashed", position: "centre" }), b(0, 2, { stereo: 1 }), b(0, 3, { display: "dashed" }), b(1, 4), b(5, 0, { display: "dative" })],
  };
  const d = render(m, S, ink), f = render(flat(m), S, ink);
  assert.deepEqual(d.polygons, f.polygons, "the same lines as drawn flat");
  assert.ok(d.alphas.every((a) => a === 1) && d.labels.every((l) => l.alpha === undefined), "full ink without depth shading");
  // Depth shading (Structure > Structure Perspective): the same lines, further ones paler, labels too, as ChemDraw
  // fades them: from full at the front of the drawing's depth range to a quarter at the back.
  const shaded = render({ ...m, atoms: m.atoms.map((a) => ({ ...a, shade: true as const })) }, S, ink);
  assert.deepEqual(shaded.polygons, d.polygons, "depth shading keeps the lines");
  assert.ok(shaded.alphas.some((a) => a < 1) && Math.max(...shaded.alphas) <= 1, "further bonds are fainter");
  const rh = shaded.labels.find((l) => l.text === "Rh")!, n = shaded.labels.find((l) => l.text === "N")!;
  assert.ok((n.alpha ?? 1) < (rh.alpha ?? 1), "a label further back is fainter");
  assert.deepEqual(depthRange(m), [-0.8, 0.8]);
  assert.deepEqual([shadeAt(0.8, [-0.8, 0.8]), shadeAt(0, [-0.8, 0.8]), shadeAt(-0.8, [-0.8, 0.8]), shadeAt(-5, [-0.8, 0.8])], [1, 0.62, 0.25, 0.25]);
  assert.equal(depthRange({ ...m, atoms: m.atoms.map((a) => ({ ...a, location: [a.location[0], a.location[1], a.location[2] * 0.2] as [number, number, number] })) }), null, "no shading over 5 pt of depth or less");
}
console.log("perspective.check: 3D structures draw every bond style ok");

// Crossing bonds, as ChemDraw decides them: the bond whose middle is nearer is in front, whatever their order (Bring
// to Front does nothing there); at the same depth the later bond is. The bond behind has a gap: the front bond's width
// and the Margin Width each side.
{
  // A horizontal bond whose right end is near (z 1), crossed at three quarters of its length by a vertical bond at
  // depth 0.6. At the crossing the horizontal bond is nearer (0.75), but ChemDraw takes each bond's middle: 0.5 against
  // 0.6, so the vertical bond is in front.
  const m: Mol = { atoms: [A("C", -1, 0, 0), A("C", 1, 0, 1), A("C", 0.5, -1, 0.6), A("C", 0.5, 1, 0.6), A("C", 1.5, 1.5, 0.6)], bonds: [b(2, 3), b(0, 1), b(3, 4)] };
  const vertical = (d: { polygons: [number, number][][] }) => d.polygons.filter((p) => Math.max(...xs(p)) - Math.min(...xs(p)) < 1);
  const horizontal = (d: { polygons: [number, number][][] }) => d.polygons.filter((p) => Math.max(...ys(p)) - Math.min(...ys(p)) < 1);
  const deep = render(m, S, ink, S.bond);
  assert.equal(horizontal(deep).length, 2, "the horizontal bond (middle further back) is cut in two");
  assert.equal(vertical(deep).length, 1, "the vertical bond (middle nearer) is whole");
  const swapped = render({ ...m, bonds: [m.bonds[1], m.bonds[0], m.bonds[2]] }, S, ink, S.bond);
  assert.equal(horizontal(swapped).length, 2, "Bring to Front does nothing where the bonds have depth");
  const level = render(flat(m), S, ink, S.bond);
  assert.equal(vertical(level).length, 2, "flat, the later (horizontal) bond is in front");
  const tie = render({ ...m, atoms: m.atoms.map((a, i) => (i < 2 ? { ...a, location: [a.location[0], a.location[1], i ? 1.2 : 0] as [number, number, number] } : a)) }, S, ink, S.bond);
  assert.equal(vertical(tie).length, 2, "middles at the same depth: the later bond is in front");
  // The gap: half the front bond's line width and the Margin Width each side, its edges along the front bond.
  const gap = (polys: [number, number][][], at: number) => Math.min(...polys.map((p) => Math.min(...xs(p).map((x) => Math.abs(x - at)))));
  assert.ok(Math.abs(gap(horizontal(deep), 0.5 * S.bond) - (S.line / 2 + M)) < 1e-9, "a single bond in front: 0.3 + 1.6 pt each side");
  // A double bond in front: its spacing and the margin, round the middle of its two lines; a wedge: the line width at
  // its narrow end, 1.5 bold widths at its wide end.
  const two = render({ ...flat(m), bonds: [b(0, 1), b(2, 3, { type: 2, position: "right" })] }, S, ink, S.bond);
  const pieces = horizontal(two).filter((p) => Math.max(...ys(p)) - Math.min(...ys(p)) < 1 && Math.abs(Math.max(...ys(p))) < 1);
  const [left, right] = [Math.max(...pieces.flatMap((p) => xs(p).filter((x) => x < 0.5 * S.bond))), Math.min(...pieces.flatMap((p) => xs(p).filter((x) => x > 0.5 * S.bond)))];
  assert.ok(Math.abs(right - left - (S.spacing + 2 * M)) < 1e-9, `double bond gap ${right - left}`);
  // A bond whose end only nearly meets a bond in front is cut too: its end stops the margin and half the line width
  // from the front bond.
  const nearly: Mol = { atoms: [A("C", 0, -1), A("C", 0, 1), A("C", 0.05, 0.3), A("C", 1.5, 0.3)], bonds: [b(2, 3), b(0, 1)] };
  const stub = render(nearly, S, ink, S.bond).polygons.filter((p) => Math.max(...ys(p)) - Math.min(...ys(p)) < 1);
  assert.ok(Math.abs(Math.min(...stub.flatMap(xs)) - (S.line / 2 + M)) < 1e-9, "a near miss is cut");
}
console.log("perspective.check: crossings by depth ok");

// Atoms drawn onto a turned structure take the depth of the atom they are drawn from; a pasted 3D structure keeps its
// own; a new flat structure stays flat.
{
  const m: Mol = { atoms: [A("C", 0, 0, 1.5), A("C", 1, 0, -0.5)], bonds: [b(0, 1)] };
  const drawn = carryDepth(m, bondTo(m, 0, [-0.5, 0.87]));
  assert.equal(drawn.atoms[2].location[2], 1.5, "a bond drawn from an atom lies at its depth");
  const ring: Mol = { ...m, atoms: [...m.atoms, A("C", 1.2, 1, 0), A("C", 0.2, 1.2, 0)], bonds: [...m.bonds, b(1, 2), b(2, 3), b(3, 0)] };
  const fused = carryDepth(m, ring);
  assert.deepEqual(fused.atoms.slice(2).map((a) => a.location[2]), [-0.5, 1.5], "a ring fused on a bond: each new atom at its neighbour's depth");
  const chain: Mol = { ...m, atoms: [...m.atoms, A("C", -1, 0, 0), A("C", -2, 0, 0)], bonds: [...m.bonds, b(0, 2), b(2, 3)] };
  assert.deepEqual(carryDepth(m, chain).atoms.slice(2).map((a) => a.location[2]), [1.5, 1.5], "a chain carries the depth along");
  const pasted = insertMol(m, { atoms: [A("C", 5, 0, 0), A("C", 6, 0, 2)], bonds: [b(0, 1)] }).mol;
  assert.deepEqual(carryDepth(m, pasted).atoms.slice(2).map((a) => a.location[2]), [0, 2], "a pasted structure keeps its depth");
  const flatOnly: Mol = { atoms: [A("C", 0, 0), A("C", 1, 0)], bonds: [b(0, 1)] };
  const plain = bondTo(flatOnly, 1, [1.5, 0.87]);
  assert.equal(carryDepth(flatOnly, plain), plain, "a flat drawing is left as it is");
}
console.log("perspective.check: new atoms take the structure's depth ok");

// Turning part of a structure: a ligand bridging two atoms (a carboxylate on a Rh–Rh bond) turns about the line
// through them, keeping its bond lengths; a 90° turn takes it out of the page.
{
  const m: Mol = {
    atoms: [A("Rh", 0, 1), A("Rh", 0, -1), A("O", 1.5, 0.9), A("O", 1.5, -0.9), A("C", 2.05, 0), A("C", 3.05, 0)],
    bonds: [b(0, 1), b(0, 2), b(1, 3), b(2, 4), b(3, 4), b(4, 5)],
  };
  const part = new Set([2, 3, 4, 5]), axis = hingeOf(m, part)!;
  assert.deepEqual([...axis].sort(), [0, 1], "the axis is the Rh–Rh line");
  const t = turnAboutBond(m, part, axis[1], axis[0], 90);
  const dist = (x: Mol, i: number, j: number) => Math.hypot(...[0, 1, 2].map((k) => (x.atoms[i].location[k] ?? 0) - (x.atoms[j].location[k] ?? 0)));
  for (const [i, j] of m.bonds.map((x) => x.atoms)) assert.ok(Math.abs(dist(t, i, j) - dist(m, i, j)) < 1e-9, "bond lengths kept");
  assert.ok(Math.abs(t.atoms[5].location[0]) < 1e-9 && Math.abs(Math.abs(t.atoms[5].location[2]) - 3.05) < 1e-9, "the R group now points out of the page");
  assert.equal(hingeOf(m, new Set([0, 2, 3, 4, 5])), undefined, "joined to the rest through one atom by two bonds: no axis");
  // A whole structure turned twice keeps its depth, and Flatten takes it away (depth shading stays set, as in ChemDraw).
  const all = new Set(m.atoms.map((_, i) => i)), twice = tiltAtoms(tiltAtoms(m, all, [0, 0, 0], 30, 0), all, [0, 0, 0], 0, 20);
  assert.ok(twice.atoms.some((a) => Math.abs(a.location[2]) > 0.1), "turned twice, still in 3D");
  const gone = flattenAtoms({ ...twice, atoms: twice.atoms.map((a) => ({ ...a, shade: true as const })) }, all);
  assert.ok(gone.atoms.every((a) => a.location[2] === 0 && a.shade), "Flatten drops the depth");
}
console.log("perspective.check: turns about a bridging ligand ok");

// Where atoms or bonds lie over each other as seen, the pointer takes the one in front: the nearer atom, the bond
// whose middle is nearer, or (flat) the bond drawn later.
{
  const m: Mol = { atoms: [A("O", 0, 0, -1), A("O", 0.01, 0, 1), A("C", -1, 0.5, 0), A("C", 1, 0.5, 0), A("C", 0, -0.5, 0), A("C", 0, 1.5, 0)], bonds: [b(2, 3), b(4, 5)] };
  assert.equal(atomAt(m, [0, 0]), 1, "the atom in front");
  assert.equal(atomAt(flat(m), [0, 0]), 0, "flat, the nearest");
  assert.equal(bondAt(flat(m), [0, 0.5]), 1, "flat bonds crossing: the later");
  assert.equal(bondAt({ ...m, atoms: m.atoms.map((x, i) => (i === 2 ? { ...x, location: [-1, 0.5, 1] as [number, number, number] } : x)) }, [0, 0.5]), 0, "the bond in front");
}
console.log("perspective.check: the pointer takes what is in front ok");

// A structure in perspective is not messy (its short and crossing bonds are by design), and an atom that is in line
// with a bond only as seen (far behind it) is not very close to it.
{
  const near: Mol = { atoms: [A("C", 0, 0), A("C", 1, 0), A("C", 0.5, 0.1, 1), A("C", 0.5, 1.1, 1)], bonds: [b(0, 1), b(2, 3)] };
  assert.ok(!problems(near).some((p) => p.type === "near"), "behind the bond, not near it");
  assert.ok(problems(flat(near)).some((p) => p.type === "near"), "flat, it is near");
  const cross: Mol = { atoms: [A("C", -0.5, 0, 0), A("C", 0.5, 0, 0.6), A("C", 0, -0.5, 0.3), A("C", 0, 0.5, 0.3)], bonds: [b(0, 1), b(2, 3), b(1, 3)] };
  assert.ok(!messy(cross) && messy(flat(cross)), "crossing bonds are messy only when flat");
}
console.log("perspective.check: warnings in perspective ok");

// A bond seen end on (a Newman projection): not drawn, and the atom behind is a circle 0.4 bond lengths across that its
// other bonds start from. The front and back bonds meet at the middle but do not cut each other.
{
  const r = 1.25, out = (t: number, z: number): [number, number, number] => [r * Math.sin((t * Math.PI) / 180), r * Math.cos((t * Math.PI) / 180), z];
  const m: Mol = { atoms: [A("C", 0, 0, 0.5), A("C", 0, 0, -0.5), ...[0, 120, 240].map((t) => ({ label: "C", location: out(t, 0.85) })), ...[60, 180, 300].map((t) => ({ label: "C", location: out(t, -0.85) }))],
    bonds: [b(0, 1), b(0, 2), b(0, 3), b(0, 4), b(1, 5), b(1, 6), b(1, 7)] };
  const d = render(m, S, ink), all = d.polygons.flat();
  assert.ok(all.every(([x, y]) => Number.isFinite(x) && Number.isFinite(y)), "no point is lost");
  // Ink all the way round at the circle's radius (every 10° of it).
  const ring = all.filter(([x, y]) => Math.abs(Math.hypot(x, y) - 0.4 * S.bond) <= S.line / 2 + 0.05);
  assert.equal(new Set(ring.map(([x, y]) => Math.floor(((Math.atan2(y, x) * 180) / Math.PI + 360) / 10) % 36)).size, 36, "the back carbon is a circle");
  // A back bond starts at the circle: nothing drawn along it nearer the middle than the circle's inner edge.
  const along = (t: number) => [Math.sin((t * Math.PI) / 180), -Math.cos((t * Math.PI) / 180)];
  const [ux, uy] = along(180), near = all.filter(([x, y]) => Math.abs(x * uy - y * ux) < 0.2 && x * ux + y * uy > 0.5 && x * ux + y * uy < 0.4 * S.bond - S.line);
  assert.equal(near.length, 0, "the back bond starts at the circle");
  // Turned a little away from end on, it is an ordinary bond again.
  const tilted = { ...m, atoms: m.atoms.map((a, i) => (i === 1 ? { ...a, location: [0.4, 0, -0.5] as [number, number, number] } : a)) };
  assert.ok(render(tilted, S, ink).polygons.length < d.polygons.length - 40, "no circle (its 48 pieces)");
}
console.log("perspective.check: Newman projections ok");

// Files keep depth and depth shading: Octet's own, and CDXML as ChemDraw writes it (xyz on atoms with depth, its z
// pointing away from the viewer; ShowPerspective on the shaded atoms and bonds). Older Octet CDXML wrote Octet's z.
{
  const m: Mol = { atoms: [A("C", 0, 0, 0, { shade: true }), A("C", 1, 0, 0.5, { shade: true }), A("O", 2, 0, 0, { shade: true }), A("C", 5, 0), A("C", 6, 0)], bonds: [b(0, 1), b(1, 2), b(3, 4)] };
  const back = parse(serialize(m));
  assert.deepEqual(back.atoms.map((a) => [a.location[2], a.shade]), [[0, true], [0.5, true], [0, true], [0, undefined], [0, undefined]]);
  assert.equal(parse(JSON.stringify({ format: "octet", version: 1, structure: { atoms: [{ label: "C", x: 0, y: 0, z: 1, depth: false }], bonds: [] } })).atoms[0].shade, undefined, "older files' depth: false reads");
  const xml = toCdxml(m, DEFAULT_STYLE);
  assert.deepEqual(xml.match(/xyz="[^"]*"/g)?.map((x) => x.split(" ").pop()), ["-7.20\""], "xyz on the atom with depth, nearer is negative");
  assert.equal((xml.match(/ShowPerspective="yes"/g) ?? []).length, 5, "on the three shaded atoms and their two bonds");
  const zs = (x: string) => fromCdxml(x).mol.atoms.map((a) => [Math.round(a.location[2] * 1e3) / 1e3, a.shade]);
  assert.deepEqual(zs(xml), [[0, true], [0.5, true], [0, true], [0, undefined], [0, undefined]]);
  const older = xml.replace("&quot;xyz&quot;:1,", "").replace(/(xyz="[^"]*) -7.20"/, "$1 7.20\"");
  assert.equal(zs(older)[1][0], 0.5, "an older Octet file keeps its depth");
  const chemdraw = xml.replace(/ Octet='[^']*'/g, "").replace(/ Octet="[^"]*"/g, "");
  assert.equal(zs(chemdraw)[1][0], 0.5, "ChemDraw's negative z is nearer");
}
console.log("perspective.check: files keep depth and shading ok");
