// Run: node src/linear.check.ts. Fails loudly if Clean Up Structure leaves a linear group bent, or its drawing breaks
// a bond, puts a charge sign on one or leaves one between two labels too short to read (Sam, 26 October 2026: methyl
// 2-diazo-2-phenylacetate after Clean Up showed the N+ sign where the N=N bond leaves, and the bond as a dotted line).
// Each structure is laid out from SMILES, cleaned, and drawn as cleaned and as its mirror image, with Arial-like glyphs
// (letters as their ink boxes, + as two bars and the minus as one, from Arial's metrics):
// - the atom between two double bonds, or a triple and a single bond, is straight, to 0.1°;
// - every bond is the bond length, to 0.1%;
// - every bond is drawn, each of its lines as one piece (one polygon per line);
// - no charge sign comes within the label margin of a drawn bond, and no bond is shorter than it is with the charges
//   taken off (their atoms keeping their hydrogens);
// - a bond between two labels shows at least a third of its length, or its margin is at the floor (0.3 of the label
//   margin), and nothing comes closer to a label than that floor; each of its lines starts and ends where the others do;
// - the bonds with an unlabelled end are drawn as long as before that rule (every line's length, summed per structure).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { arialGlyph } from "./cdxml.ts";
import { hydrogens, orderOf, render, type Drawing, type Ink, type Mol } from "./render.ts";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { cleanUp, parseStructure, ready } = await import("./chem.ts");
await ready;

type P = [number, number];
const pt = 4 / 3, deg = 180 / Math.PI;
const S = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
const FLOOR = 0.3 * S.margin, TOL = 0.05;
// Arial-like glyphs: each letter or digit its ink box (cap height, or x-height for short letters), + two bars and the
// en dash one bar, at Arial's advances, ink edges and heights.
const box = (out: P[], x0: number, y0: number, x1: number, y1: number) => { for (let k = 0; k <= 12; k++) { const f = k / 12; out.push([x0 + (x1 - x0) * f, -y0], [x0 + (x1 - x0) * f, -y1], [x0, -y0 - (y1 - y0) * f], [x1, -y0 - (y1 - y0) * f]); } };
const arial = (text: string): Ink => {
  const outline: P[] = [], z = S.size;
  let x = 0, top = 0;
  for (const ch of text) {
    const [w, l, r] = arialGlyph(ch).map((v) => (v * z) / 1000), c = x + (l + r) / 2;
    if (ch === "+") { box(outline, x + l, 0.3125 * z, x + r, 0.3925 * z); box(outline, c - 0.04 * z, 0.116 * z, c + 0.04 * z, 0.589 * z); top = Math.max(top, 0.589 * z); }
    else if (ch === "–") box(outline, x + l, 0.224 * z, x + r, 0.294 * z);
    else { const h = /[acemnorsuvwxz]/.test(ch) ? 0.519 * z : 0.716 * z; box(outline, x + l, 0, x + r, h); top = Math.max(top, h); }
    x += w;
  }
  return { width: x, ascent: top, outline };
};
// Where a drawing puts atom i (px), whether it has a label, and the ink of the labels on the atoms given.
const placeOf = (d: Drawing, mol: Mol, i: number): P => [mol.atoms[i].location[0] * d.scale, -mol.atoms[i].location[1] * d.scale];
const near = (p: P, q: P) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-6;
const labelled = (d: Drawing, mol: Mol, i: number) => d.labelAt.some((q) => near(q, placeOf(d, mol, i)));
const inkOf = (d: Drawing, mol: Mol, atoms: number[]): P[] => d.labels.flatMap((l, j) => (atoms.some((i) => near(d.labelAt[j], placeOf(d, mol, i))) ? arial(l.text).outline.map(([x, y]): P => [l.x + (x * l.size) / S.size, l.y + (y * l.size) / S.size]) : []));
// The least distance from some polygons' edges to some ink.
const gap = (polys: P[][], ink: P[]) => {
  let least = Infinity;
  for (const poly of polys) poly.forEach((p, n) => {
    const q = poly[(n + 1) % poly.length];
    for (let s = 0; s <= 20; s++) { const x = p[0] + ((q[0] - p[0]) * s) / 20, y = p[1] + ((q[1] - p[1]) * s) / 20; for (const r of ink) least = Math.min(least, Math.hypot(r[0] - x, r[1] - y)); }
  });
  return least;
};
// Each polygon's stretch along the bond from atom i to atom j (px from i).
const stretches = (d: Drawing, mol: Mol, i: number, j: number, polys: P[][]): [number, number][] => {
  const X = placeOf(d, mol, i), Y = placeOf(d, mol, j), l = Math.hypot(Y[0] - X[0], Y[1] - X[1]), along = (q: P) => ((q[0] - X[0]) * (Y[0] - X[0]) + (q[1] - X[1]) * (Y[1] - X[1])) / l;
  return polys.map((poly) => [Math.min(...poly.map(along)), Math.max(...poly.map(along))]);
};

// Each structure, with its bonds with an unlabelled end drawn as long as before label-to-label bonds kept a third of
// their length (pt, summed; the same mirrored).
const structures: [string, string, number][] = [
  ["methyl 2-diazo-2-phenylacetate", "COC(=O)C(=[N+]=[N-])c1ccccc1", 202.94],
  ["ethyl diazoacetate", "CCOC(=O)C=[N+]=[N-]", 82.06],
  ["phenyl azide", "[N-]=[N+]=Nc1ccccc1", 131.91],
  ["benzonitrile oxide", "[O-][N+]#Cc1ccccc1", 165.43],
  ["phenyl isocyanate", "O=C=Nc1ccccc1", 163.84],
  ["phenyl isothiocyanate", "S=C=Nc1ccccc1", 163.87],
  ["dimethylketene", "CC(C)=C=O", 77.38],
  ["penta-2,3-diene", "CC=C=CC", 87.9],
  ["carbon dioxide", "O=C=O", 35.89], // cleaned exactly straight, so its double bonds are centred
  ["dicyclohexylcarbodiimide", "C1CCC(CC1)N=C=NC1CCCCC1", 227.32],
  ["benzonitrile", "N#Cc1ccccc1", 165.43],
  ["1-phenylpropyne", "CC#Cc1ccccc1", 194.35],
  ["benzenediazonium", "N#[N+]c1ccccc1", 131.91],
  ["azobenzene", "c1ccc(cc1)/N=N/c1ccccc1", 263.83],
  ["hydrazine", "NN", 0],
  ["di-tert-butyl peroxide", "CC(C)(C)OOC(C)(C)C", 102.67],
  ["dimethyl disulfide", "CSSC", 17.56],
];
let straight = 0, signs = 0, between = 0;
for (const [name, smiles, unlabelled] of structures) {
  const cleaned = cleanUp(parseStructure(smiles));
  for (const [how, mol] of [["cleaned", cleaned], ["mirrored", { ...cleaned, atoms: cleaned.atoms.map((a) => ({ ...a, location: [-a.location[0], a.location[1], 0] as [number, number, number] })) }]] as [string, Mol][]) {
    const what = `${name}, ${how}`, at = (i: number) => mol.atoms[i].location;
    const nbrs = mol.atoms.map((_, i) => mol.bonds.filter((b) => b.atoms.includes(i)));
    // Straight: an atom with two double bonds, or a triple and a single bond.
    mol.atoms.forEach((_, i) => {
      const orders = nbrs[i].map((b) => b.type).sort().join();
      if (orders !== "2,2" && orders !== "1,3") return;
      const [p, q] = nbrs[i].map((b) => at(b.atoms[0] === i ? b.atoms[1] : b.atoms[0])), u = [p[0] - at(i)[0], p[1] - at(i)[1]], v = [q[0] - at(i)[0], q[1] - at(i)[1]];
      const angle = Math.abs(Math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])) * deg;
      assert.ok(Math.abs(angle - 180) < 0.1, `${what}: ${mol.atoms[i].label}${i} is straight (${angle.toFixed(3)}°)`);
      straight++;
    });
    for (const b of mol.bonds) {
      const l = Math.hypot(at(b.atoms[1])[0] - at(b.atoms[0])[0], at(b.atoms[1])[1] - at(b.atoms[0])[1]);
      assert.ok(Math.abs(l - 1) < 1e-3, `${what}: every bond is the bond length (${l.toFixed(5)})`);
    }
    // Each bond in its own colour, so its polygons can be told apart.
    const colour = (k: number) => `#0000${k.toString(16).padStart(2, "0")}`, coloured = { ...mol, bonds: mol.bonds.map((b, k) => ({ ...b, colour: colour(k) })) };
    const d = render(coloured, S, arial), polys = (dr: Drawing, k: number) => dr.polygons.filter((_, n) => dr.colours[n] === colour(k));
    // How long each bond is drawn: its longest line, along the bond.
    const drawn = (dr: Drawing, k: number) => Math.max(0, ...stretches(dr, mol, ...mol.bonds[k].atoms, polys(dr, k)).map(([p, q]) => q - p));
    const used = mol.atoms.map((_, i) => nbrs[i].reduce((n, b) => n + orderOf(b.type), 0));
    const neutral = render({ ...coloured, atoms: mol.atoms.map((a, i) => (a.charge ? { ...a, charge: undefined, implicitHCount: hydrogens(a.label, a.charge, used[i]) } : a)) }, S, arial);
    let rest = 0;
    mol.bonds.forEach((b, k) => {
      const pieces = polys(d, k).length, kind = b.type === 3 ? "triple" : b.type === 2 ? "double" : "single";
      assert.equal(pieces, b.type === 3 ? 3 : b.type === 2 ? 2 : 1, `${what}: bond ${k} (${kind}) drawn as one piece per line`);
      assert.ok(drawn(d, k) >= drawn(neutral, k) - 0.01, `${what}: bond ${k} drawn ${(drawn(d, k) / pt).toFixed(2)} pt, as long as without its charges (${(drawn(neutral, k) / pt).toFixed(2)} pt)`);
      if (!labelled(d, mol, b.atoms[0]) || !labelled(d, mol, b.atoms[1])) { rest += stretches(d, mol, ...b.atoms, polys(d, k)).reduce((s, [p, q]) => s + q - p, 0); return; }
      // Between two labels: a third of the bond shows, or the margin is at the floor; no closer than the floor; every
      // line over the same stretch.
      const shown = drawn(d, k), closest = gap(polys(d, k), inkOf(d, mol, b.atoms)), lines = stretches(d, mol, ...b.atoms, polys(d, k));
      assert.ok(closest >= FLOOR - TOL, `${what}: ${kind} bond ${k} between labels ${(closest / pt).toFixed(2)} pt from their ink (floor ${(FLOOR / pt).toFixed(2)} pt)`);
      assert.ok(shown >= S.bond / 3 - TOL || closest <= FLOOR + S.line + TOL, `${what}: ${kind} bond ${k} between labels shows ${(shown / pt).toFixed(2)} pt (a third is ${(S.bond / 3 / pt).toFixed(2)} pt), its margin above the floor`);
      for (const [p, q] of lines) assert.ok(Math.abs(p - lines[0][0]) < 0.01 && Math.abs(q - lines[0][1]) < 0.01, `${what}: every line of bond ${k} over the same stretch`);
      between++;
    });
    assert.ok(Math.abs(rest / pt - unlabelled) < 0.006, `${what}: the bonds with an unlabelled end drawn as before (${(rest / pt).toFixed(2)} pt, was ${unlabelled})`);
    // A sign's ink (where the label is drawn) stays the margin clear of every bond polygon's edges.
    for (const l of d.labels.filter((x) => /^\d*[+–]$/.test(x.text))) {
      const k = l.size / S.size, ink = arial(l.text).outline.map(([x, y]): P => [l.x + x * k, l.y + y * k]);
      const xs = ink.map((q) => q[0]), ys = ink.map((q) => q[1]), b = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
      let least = Infinity;
      d.polygons.forEach((poly, j) => {
        if (!d.colours[j]) return; // a mark, not a bond
        poly.forEach((p, n) => {
          const q = poly[(n + 1) % poly.length];
          for (let s = 0; s <= 40; s++) {
            const x = p[0] + ((q[0] - p[0]) * s) / 40, y = p[1] + ((q[1] - p[1]) * s) / 40;
            least = Math.min(least, Math.hypot(Math.max(b[0] - x, 0, x - b[2]), Math.max(b[1] - y, 0, y - b[3])));
          }
        });
      });
      assert.ok(least >= S.margin - TOL, `${what}: its ${l.text} sign is ${(least / pt).toFixed(2)} pt from the nearest bond (margin ${(S.margin / pt).toFixed(2)} pt)`);
      signs++;
    }
  }
}
console.log(`linear.check: ${structures.length} structures and their mirror images, ${straight} straight atoms, ${signs} charge signs clear of their bonds, ${between} bonds between labels readable`);

// Every bond style from a charged label (NH3+) to a carbon, both ways round and every 30°: drawn, each solid line in
// one piece, and the full label margin clear of the label's ink (the margin only narrows between two labels). From
// N+ to O-, every style: drawn, no closer to either label than the floor, a third of the bond showing or the margin at
// the floor, and a dative bond's head the full margin clear of the label it points at.
{
  const styles: [string, Partial<Mol["bonds"][number]>, number][] = [
    ["single", {}, 1], ["double", { type: 2 }, 2], ["triple", { type: 3 }, 3], ["bold", { display: "bold" }, 1], ["wedge", { stereo: 1 }, 1], ["hashed wedge", { stereo: 6 }, 0], ["wavy", { display: "wavy" }, 1],
    ["dashed", { display: "dashed" }, 0], ["dative", { display: "dative" }, 2], ["hollow wedge", { display: "hollow" }, 3], ["hashed", { display: "hashed" }, 0], ["hydrogen bond", { type: 10 }, 0],
  ];
  let bonds = 0;
  for (const [name, more, pieces] of styles) for (let t = 0; t < 360; t += 30) for (const other of ["C", "C back", "O-", "O- back"]) {
    const far = { label: other[0], location: [Math.cos(t / deg), Math.sin(t / deg), 0] as [number, number, number], ...(other[0] === "O" ? { charge: -1 } : {}) };
    const mol: Mol = { atoms: [{ label: "N", charge: 1, location: [0, 0, 0] }, far], bonds: [{ type: 1, atoms: other.endsWith("back") ? [1, 0] : [0, 1], ...more }] };
    const d = render(mol, S, arial), what = `${name} from N+ to ${other} at ${t}°`, two = other[0] === "O";
    assert.ok(d.polygons.length >= Math.max(1, pieces) && (!pieces || d.polygons.length === pieces), `${what}: drawn, its solid lines in one piece each (${d.polygons.length} polygons)`);
    const closest = gap(d.polygons, inkOf(d, mol, [0, 1]));
    if (!two) { assert.ok(closest >= S.margin - TOL, `${what}: ${(closest / pt).toFixed(2)} pt from the label's ink (margin ${(S.margin / pt).toFixed(2)} pt)`); bonds++; continue; }
    const [lo, hi] = stretches(d, mol, 0, 1, d.polygons).reduce(([p, q], [r, s]) => [Math.min(p, r), Math.max(q, s)], [Infinity, -Infinity]);
    assert.ok(closest >= FLOOR - TOL, `${what}: ${(closest / pt).toFixed(2)} pt from the labels' ink (floor ${(FLOOR / pt).toFixed(2)} pt)`);
    assert.ok(hi - lo >= S.bond / 3 - TOL || closest <= FLOOR + S.bold + TOL, `${what}: shows ${((hi - lo) / pt).toFixed(2)} pt, its margin above the floor`);
    if (name === "dative") {
      // The head: the polygon with three corners. It points at the bond's second atom.
      const head = d.polygons.filter((poly) => poly.length === 3), at = mol.bonds[0].atoms[1];
      assert.ok(head.length === 1 && gap(head, inkOf(d, mol, [at])) >= S.margin - TOL, `${what}: its head ${(gap(head, inkOf(d, mol, [at])) / pt).toFixed(2)} pt from the label it points at (margin ${(S.margin / pt).toFixed(2)} pt)`);
    }
    bonds++;
  }
  console.log(`linear.check: ${bonds} bonds in ${styles.length} styles drawn clear of charged labels, solid lines in one piece`);
}
