// Run: node src/cip.check.ts. Fails loudly if Octet's CIP labels (src/cip.ts) go wrong: centres and double bonds
// drawn by hand whose labels are worked out here by hand, structures OPSIN builds from names that carry their own
// descriptors, the cases Indigo (Octet's labeller before) gets wrong, labels that must not change when a drawing is
// renumbered or turned, and the time a labelling takes.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { cipOf, importStructure, parseStructure, ready, stereoFacts, stereoLabels } = await import("./chem.ts");
const { problems } = await import("./check.ts");
const { cipLabels } = await import("./cip.ts");
const { DRUGS } = await import("./drugs.ts");
const { renumberCentre } = await import("./edit.ts");
type Mol = import("./render.ts").Mol;
type Bond = Mol["bonds"][number];
await ready;

// ---- Drawn by hand ----
// Atoms at angles (degrees, anticlockwise from the right) round a centre at the origin, one bond length out. In each
// case the label is worked out by hand: with the lowest ligand away from the viewer, 1 → 2 → 3 clockwise is R.
const at = (deg: number, r = 1, o: [number, number] = [0, 0]): [number, number, number] => [o[0] + r * Math.cos((deg * Math.PI) / 180), o[1] + r * Math.sin((deg * Math.PI) / 180), 0];
const atom = (label: string, location: [number, number, number], extra: Partial<Mol["atoms"][number]> = {}) => ({ label, location, ...extra });
const bond = (a: number, b: number, extra: Partial<Bond> = {}): Bond => ({ type: 1, atoms: [a, b], ...extra });
const labels = (m: Mol) => cipLabels(m).atoms;

// CHFClBr: Br > Cl > F > H. F up (towards the viewer on a wedge), Cl at 8 o'clock, Br at 4: Br → Cl → F turns clockwise.
const halo = (wedge: Partial<Bond>): Mol => ({ atoms: [atom("C", at(0, 0)), atom("F", at(90)), atom("Cl", at(210)), atom("Br", at(330))], bonds: [bond(0, 1, wedge), bond(0, 2), bond(0, 3)] });
assert.equal(labels(halo({ stereo: 1 }))[0], "R");
assert.equal(labels(halo({ stereo: 6 }))[0], "S");
// Butan-2-ol: O > CH2CH3 > CH3 > H, the O up, the ethyl at 4 o'clock and the methyl at 8.
const butanol = (wedge: Partial<Bond>, reversed = false): Mol => ({
  atoms: [atom("C", at(0, 0)), atom("O", at(90)), atom("C", at(330)), atom("C", at(30, 1, at(330) as [number, number])), atom("C", at(210))],
  bonds: [reversed ? bond(1, 0, wedge) : bond(0, 1, wedge), bond(0, 2), bond(2, 3), bond(0, 4)],
});
assert.equal(labels(butanol({ stereo: 1 }))[0], "R");
assert.equal(labels(butanol({ stereo: 6 }))[0], "S");
// ChemDraw's other stereo bonds: a wedge whose wide end is on the centre puts the O behind it; a plain hashed or
// dashed bond puts it behind, a bold bond in front.
assert.equal(labels(butanol({ stereo: 1 }, true))[0], "S");
assert.equal(labels(butanol({ display: "hashed" }))[0], "S");
assert.equal(labels(butanol({ display: "dashed" }))[0], "S");
assert.equal(labels(butanol({ display: "bold" }))[0], "R");
// No stereo bond, or a wavy one: no label.
assert.equal(labels(butanol({}))[0], undefined);
assert.equal(labels(butanol({ display: "wavy" }))[0], undefined);
// An explicit H drawn on a hash, the O plain: the same centre as the O on a wedge.
const withH: Mol = { atoms: [...butanol({}).atoms, atom("H", at(150, 0.7))], bonds: [...butanol({}).bonds, bond(0, 5, { stereo: 6 })] };
assert.equal(labels(withH)[0], "R");
// Isotopes (rule 2). CH3–CHDT: CH3 > T > D > H; the methyl at 8 o'clock, T up on a wedge, D at 4 o'clock: R.
const chdt: Mol = { atoms: [atom("C", at(0, 0)), atom("C", at(210)), atom("H", at(90), { isotope: 3 }), atom("D", at(330))], bonds: [bond(0, 1), bond(0, 2, { stereo: 1 }), bond(0, 3)] };
assert.equal(labels(chdt)[0], "R");
// Ethanol-1-d: O > CH3 > D > H, O up on a wedge, the methyl at 8 o'clock, D at 4: O → CH3 → D turns anticlockwise, S.
// With the D as plain H: none.
const ethanolD = (iso?: number): Mol => ({ atoms: [atom("C", at(0, 0)), atom("O", at(90)), atom("C", at(210)), atom("H", at(330), iso ? { isotope: iso } : {})], bonds: [bond(0, 1, { stereo: 1 }), bond(0, 2), bond(0, 3)] });
assert.equal(labels(ethanolD(2))[0], "S");
assert.equal(labels(ethanolD())[0], undefined);
// A sulfoxide (lone pair lowest): O > phenyl C > methyl C. O up, the methyl at 8 o'clock, the phenyl at 4 on a
// wedge, so the lone pair is behind: O → Ph → CH3 turns clockwise, R.
const sulfoxide: Mol = {
  atoms: [atom("S", at(0, 0)), atom("O", at(90)), atom("C", at(210)), atom("C", at(330)), ...[0, 60, 120, 180, 240].map((d) => atom("C", at(d - 30, 1, at(330, 2) as [number, number])))],
  bonds: [bond(0, 1, { type: 2 }), bond(0, 2), bond(0, 3, { stereo: 1 }), bond(3, 4, { type: 2 }), bond(4, 5), bond(5, 6, { type: 2 }), bond(6, 7), bond(7, 8, { type: 2 }), bond(8, 3)],
};
assert.equal(labels(sulfoxide)[0], "R");

// A pseudoasymmetric centre (rule 5, P-92.5.3): pentane-2,3,4-triol drawn as a zigzag, C3 at the origin with its OH
// up, C2 at 8 o'clock and C4 at 4, each with its OH down. C2 is S with its OH on a wedge (O → C3 → C1 turns
// anticlockwise) and R on a hash; C4, the mirror image, is R on a wedge and S on a hash. In the meso form (2R,4S) the
// R branch ranks above the S one, so with the OH of C3 on a wedge, OH → C2 → C4 turns anticlockwise: s.
function triol(c2: number, c3: number, c4: number): Mol {
  const p2 = at(210) as [number, number], p4 = at(330) as [number, number];
  return {
    atoms: [atom("C", at(0, 0)), atom("O", at(90)), atom("C", at(210)), atom("O", at(270, 1, p2)), atom("C", at(150, 1, p2)), atom("C", at(330)), atom("O", at(270, 1, p4)), atom("C", at(30, 1, p4))],
    bonds: [bond(0, 1, { stereo: c3 }), bond(0, 2), bond(2, 3, { stereo: c2 }), bond(2, 4), bond(0, 5), bond(5, 6, { stereo: c4 }), bond(5, 7)],
  };
}
assert.deepEqual([2, 0, 5].map((i) => labels(triol(6, 1, 6))[i]), ["R", "s", "S"]);
assert.deepEqual([2, 0, 5].map((i) => labels(triol(6, 6, 6))[i]), ["R", "r", "S"]);
// (2R,4R): C3 has two like branches and is no stereocentre.
assert.deepEqual([2, 0, 5].map((i) => labels(triol(6, 1, 1))[i]), ["R", undefined, "R"]);
// Rule 4b (P-92.5.2.2): like pairs (RR, SS) rank above unlike ones (RS, SR). A CH(OH) between two CHCl–CHCl–CH3 arms,
// the OH up, arm A at 8 o'clock, arm B at 4. Arm A is (R,R) with both Cl on wedges; arm B (R,S) with the first Cl
// on a hash and the second on a wedge (worked out as for the triol). OH → A → B turns anticlockwise: S. Swapping the
// arms' pairs swaps the ranking: R.
function arms(a1: number, a2: number, b1: number, b2: number): Mol {
  const pa = at(210) as [number, number], pb = at(330) as [number, number], qa = at(150, 1, pa) as [number, number], qb = at(30, 1, pb) as [number, number];
  return {
    atoms: [atom("C", at(0, 0)), atom("O", at(90)), atom("C", pa), atom("Cl", at(270, 1, pa)), atom("C", qa), atom("Cl", at(90, 1, qa)), atom("C", at(210, 1, qa)),
      atom("C", pb), atom("Cl", at(270, 1, pb)), atom("C", qb), atom("Cl", at(90, 1, qb)), atom("C", at(330, 1, qb))],
    bonds: [bond(0, 1, { stereo: 1 }), bond(0, 2), bond(2, 3, { stereo: a1 }), bond(2, 4), bond(4, 5, { stereo: a2 }), bond(4, 6), bond(0, 7), bond(7, 8, { stereo: b1 }), bond(7, 9), bond(9, 10, { stereo: b2 }), bond(9, 11)],
  };
}
assert.deepEqual([2, 4, 7, 9, 0].map((i) => labels(arms(1, 1, 6, 1))[i]), ["R", "R", "R", "S", "S"]);
assert.deepEqual([2, 4, 7, 9, 0].map((i) => labels(arms(1, 6, 6, 6))[i]), ["R", "S", "R", "R", "R"]);

// Double bonds. But-2-ene: the methyls on one side, Z; on opposite sides, E.
const butene = (cis: boolean): Mol => ({ atoms: [atom("C", [0, 0, 0]), atom("C", [1, 0, 0]), atom("C", at(cis ? 120 : 240)), atom("C", at(60, 1, [1, 0]))], bonds: [bond(0, 1, { type: 2 }), bond(0, 2), bond(1, 3)] });
assert.equal(cipLabels(butene(true)).bonds[0], "Z");
assert.equal(cipLabels(butene(false)).bonds[0], "E");
// Crossed (either) or with a wavy bond on it: none.
assert.equal(cipLabels({ ...butene(true), bonds: butene(true).bonds.map((b, k) => (k ? b : { ...b, display: "either" })) }).bonds[0], undefined);
assert.equal(cipLabels({ ...butene(true), bonds: butene(true).bonds.map((b, k) => (k === 1 ? { ...b, display: "wavy" } : b)) }).bonds[0], undefined);
// C=N: acetaldehyde oxime, CH3 > H on C and OH > lone pair on N. CH3 and OH on opposite sides: E.
const oxime: Mol = { atoms: [atom("C", [0, 0, 0]), atom("N", [1, 0, 0]), atom("C", at(120)), atom("O", at(300, 1, [1, 0]))], bonds: [bond(0, 1, { type: 2 }), bond(0, 2), bond(1, 3)] };
assert.equal(cipLabels(oxime).bonds[0], "E");
// A cumulene with three double bonds (hexa-2,3,4-triene) is E or Z like a double bond, on its middle bond; with two
// (an allene) it has an axis instead (axial.ts).
const triene = (cis: boolean): Mol => ({ atoms: [0, 1, 2, 3].map((x) => atom("C", [x, 0, 0])).concat([atom("C", at(120)), atom("C", at(cis ? 60 : 300, 1, [3, 0]))]), bonds: [bond(0, 1, { type: 2 }), bond(1, 2, { type: 2 }), bond(2, 3, { type: 2 }), bond(0, 4), bond(3, 5)] });
assert.deepEqual(cipLabels(triene(true)).bonds, [undefined, "Z", undefined, undefined, undefined]);
assert.deepEqual(cipLabels(triene(false)).bonds, [undefined, "E", undefined, undefined, undefined]);
const allene: Mol = { atoms: [0, 1, 2].map((x) => atom("C", [x, 0, 0])).concat([atom("C", at(120)), atom("C", at(60, 1, [2, 0]))]), bonds: [bond(0, 1, { type: 2 }), bond(1, 2, { type: 2 }), bond(0, 3), bond(2, 4)] };
assert.ok(!cipLabels(allene).bonds.some(Boolean));
// A double bond in a ring under 8 atoms has no label (1,2-dimethylcyclohexene); in cyclooctene it has.
const ring = (n: number): Mol => {
  const atoms = Array.from({ length: n }, (_, k) => atom("C", at((360 * k) / n, 1 / (2 * Math.sin(Math.PI / n)))));
  return { atoms, bonds: atoms.map((_, k) => bond(k, (k + 1) % n, k ? {} : { type: 2 })) };
};
assert.equal(cipLabels(ring(6)).bonds[0], undefined);
assert.equal(cipLabels(ring(8)).bonds[0], "Z");
// An R group ranks above H, as ChemDraw ranks it: R–CH=CH–CHO with R and CHO on opposite sides is E.
const generic: Mol = { atoms: [atom("C", [0, 0, 0]), atom("C", [1, 0, 0]), atom("C", at(120), { text: "R" }), atom("C", at(300, 1, [1, 0])), atom("O", at(0, 1, at(300, 1, [1, 0]) as [number, number]))], bonds: [bond(0, 1, { type: 2 }), bond(0, 2), bond(1, 3), bond(3, 4, { type: 2 })] };
assert.equal(stereoLabels(generic)?.bonds[0], "E");

// ---- The stereochemistry warnings agree ----
// With Show Stereochemistry on, a centre set by a plain hashed bond is labelled and gets no "no wedge or hash"
// warning (Indigo, which the warnings come from, does not read that bond).
const shown = (m: Mol): Mol => ({ ...m, atoms: m.atoms.map((a) => ({ ...a, cip: true as const })) });
const hashed = shown(butanol({ display: "hashed" }));
assert.equal(stereoLabels(hashed)?.atoms[0], "S");
assert.ok(!stereoFacts(hashed).unset.has(0));
assert.ok(!problems(hashed, stereoFacts(hashed)).some((p) => p.type === "unspecified" || p.type === "ambiguous"));
// With no stereo bond the warning stays.
assert.ok(problems(shown(butanol({})), stereoFacts(shown(butanol({})))).some((p) => p.type === "unspecified"));

// ---- Written labels ----
// Butan-2-ol with its ethyl written as a label (Et) and its OH as OH: the centre is labelled, nothing inside a label is.
const written: Mol = { atoms: [atom("C", at(0, 0)), atom("O", at(90), { text: "OH" }), atom("C", at(330), { text: "Et" }), atom("C", at(210))], bonds: [bond(0, 1, { stereo: 1 }), bond(0, 2), bond(0, 3)] };
assert.deepEqual(stereoLabels(written)?.atoms, ["R", undefined, undefined, undefined]);
assert.deepEqual(cipOf(written).atoms, ["R", undefined, undefined, undefined]);

// ---- Drawings that must not change the labels ----
// Renumbered atoms, the drawing turned half a turn, the other Kekulé form of a ring: the same labels. A mirror image
// (x made -x) turns R into S and keeps E and Z.
const shuffle = (m: Mol, order: number[]): Mol => {
  const to = new Map(order.map((i, k) => [i, k]));
  return { atoms: order.map((i) => renumberCentre(m.atoms[i], to)), bonds: m.bonds.map((b) => ({ ...b, atoms: b.atoms.map((i) => to.get(i)!) as [number, number] })) };
};
const turned = (m: Mol, sx: number, sy: number): Mol => ({ ...m, atoms: m.atoms.map((a) => ({ ...a, location: [sx * a.location[0], sy * a.location[1], 0] as [number, number, number] })) });
const mirrorLabel = (c?: string) => (c === "R" ? "S" : c === "S" ? "R" : c === "r" ? "s" : c === "s" ? "r" : c);
for (const [name, smiles] of Object.entries(DRUGS).filter(([, s]) => s.includes("@") && !s.startsWith("=")).slice(0, 40)) {
  const m = parseStructure(smiles), want = cipLabels(m), n = m.atoms.length;
  assert.ok(want.atoms.some(Boolean), name);
  const order = Array.from({ length: n }, (_, k) => (k * 7 + 3) % n).filter((v, k, all) => all.indexOf(v) === k);
  if (order.length === n) assert.deepEqual(cipLabels(shuffle(m, order)).atoms, order.map((i) => want.atoms[i]), `${name}: renumbered`);
  assert.deepEqual(cipLabels(turned(m, -1, -1)), want, `${name}: turned`);
  assert.deepEqual(cipLabels(turned(m, -1, 1)).atoms, want.atoms.map(mirrorLabel), `${name}: mirror`);
}
// Toluene-ring Kekulé forms in 1-phenylethanol: the labels do not depend on which form is drawn.
const kekule = (smiles: string) => { const m = parseStructure(smiles); return cipLabels(m).atoms.filter(Boolean); };
assert.deepEqual(kekule("C[C@@H](O)C1=CC=C(C)C=C1"), kekule("C[C@@H](O)C1C=CC(C)=CC=1"));

// ---- A configuration ChemDraw keeps (Geometry and BondOrdering in CDXML) ----
// Butan-2-ol with no stereo bond: its centre's bonds in order (to O, the methyl, the ethyl; 0 the hydrogen) turn
// clockwise seen with the hydrogen away, but are drawn anticlockwise (O up, the methyl at 8 o'clock, the ethyl at 4),
// so the hydrogen is towards the viewer: O → ethyl → methyl turns clockwise from the front, which makes it S.
const { fromCdxml, toCdxml } = await import("./cdxml.ts");
const { DEFAULT_STYLE } = await import("./docstyle.ts");
const xml = `<?xml version="1.0" encoding="UTF-8" ?><CDXML><page><fragment>
<n id="1" p="100 100" Geometry="Tetrahedral" BondOrdering="11 12 13 0"/><n id="2" p="100 85.6" Element="8"/>
<n id="3" p="87.53 107.2"/><n id="4" p="112.47 107.2"/><n id="5" p="124.94 100"/>
<b id="11" B="1" E="2"/><b id="12" B="1" E="3"/><b id="13" B="1" E="4"/><b id="14" B="4" E="5"/></fragment></page></CDXML>`;
const keptMol = fromCdxml(xml).mol;
assert.equal(stereoLabels(keptMol)?.atoms[0], "S");
// It survives renumbering and saving (written back as ChemDraw stores it).
assert.equal(cipLabels(shuffle(keptMol, [4, 2, 0, 3, 1])).atoms[2], "S");
const saved = toCdxml(keptMol, DEFAULT_STYLE);
assert.ok(/Geometry="Tetrahedral"/.test(saved) && /BondOrdering=/.test(saved));
assert.equal(stereoLabels(fromCdxml(saved).mol)?.atoms[0], "S");
// Flip Horizontal keeps it, as it keeps a wedge's centre (a turn in 3D); a mirror inverts it, as it inverts a wedge's.
const { flipAtoms } = await import("./edit.ts");
const everything = new Set(keptMol.atoms.map((_, i) => i));
assert.equal(stereoLabels(flipAtoms(keptMol, everything, "horizontal"))?.atoms[0], "S");
assert.equal(stereoLabels(flipAtoms(keptMol, everything, "horizontal", true))?.atoms[0], "R");
// A stereo bond drawn at the centre afterwards replaces it: the O on a wedge is R, and nothing is kept on saving.
const edited: Mol = { ...keptMol, bonds: keptMol.bonds.map((b) => (b.atoms.includes(0) && b.atoms.includes(1) ? { ...b, atoms: [0, 1] as [number, number], stereo: 1 } : b)) };
assert.equal(stereoLabels(edited)?.atoms[0], "R");
assert.ok(!/Geometry="Tetrahedral"/.test(toCdxml(edited, DEFAULT_STYLE)));

// ---- Drawn in 3D ----
// A centre with depth round it is read from its atoms' places, whatever its wedges say: butan-2-ol with its O in front
// (towards the viewer) and no stereo bond is R, as with the O on a wedge. A flat drawing turned in 3D (its four
// ligands in one plane) is read from its wedges. An amine N is no centre by its places alone.
const deep = (m: Mol, z: Record<number, number>): Mol => ({ ...m, atoms: m.atoms.map((a, i) => ({ ...a, location: [a.location[0], a.location[1], z[i] ?? 0] as [number, number, number] })) });
assert.equal(labels(deep(butanol({}), { 1: 0.8, 2: -0.3, 4: -0.3 }))[0], "R");
assert.equal(labels(deep(butanol({ stereo: 6 }), { 1: 0.8, 2: -0.3, 4: -0.3 }))[0], "R");
const tilted = (m: Mol): Mol => ({ ...m, atoms: m.atoms.map((a) => ({ ...a, location: [a.location[0] * 0.6, a.location[1], a.location[0] * 0.8] as [number, number, number] })) });
assert.equal(labels(tilted(butanol({ stereo: 1 })))[0], "R");
const amine: Mol = { ...butanol({}), atoms: butanol({}).atoms.map((a, i) => (i === 0 ? { ...a, label: "N" } : a)) };
assert.equal(labels(deep(amine, { 1: 0.8, 2: -0.3, 4: -0.3 }))[0], undefined);
// A 3D molfile (as PubChem's 3D SD files are) keeps its depth, and is labelled from it with no wedge: L-alanine, its
// N, carboxyl C, methyl C and H at alternate corners of a cube round the centre, is S, with its H drawn or not.
const corner = (x: number, y: number, z: number, el: string) => `${x.toFixed(4).padStart(10)}${y.toFixed(4).padStart(10)}${z.toFixed(4).padStart(10)} ${el.padEnd(3)} 0  0  0  0  0  0  0  0  0  0  0  0`;
const link = (a: number, b: number, t: number) => `${String(a).padStart(3)}${String(b).padStart(3)}${String(t).padStart(3)}  0  0  0  0`;
for (const h of [true, false]) {
  const atoms = [corner(0, 0, 0, "C"), corner(0.87, 0.87, 0.87, "N"), corner(0.87, -0.87, -0.87, "C"), corner(-0.87, 0.87, -0.87, "C"), corner(0.6, -2.1, -0.9, "O"), corner(1.9, -0.4, -1.4, "O"), ...(h ? [corner(-0.63, -0.63, 0.63, "H")] : [])];
  const bonds = [link(1, 2, 1), link(1, 3, 1), link(1, 4, 1), link(3, 5, 2), link(3, 6, 1), ...(h ? [link(1, 7, 1)] : [])];
  const file = ["alanine", "  Octet         3D", "", `${String(atoms.length).padStart(3)}${String(bonds.length).padStart(3)}  0  0  0  0  0  0  0  0999 V2000`, ...atoms, ...bonds, "M  END", ""].join("\n");
  const m = importStructure(file);
  assert.ok(m.atoms.some((a) => a.location[2]) && !m.bonds.some((b) => b.stereo));
  assert.equal(stereoLabels(m)?.atoms[0], "S");
}

// ---- Names that carry their descriptors (OPSIN builds the structure) ----
const dir = new URL("./vendor/opsin/", import.meta.url);
if (existsSync(new URL("opsin.js", dir))) {
  const pack = readFileSync(new URL("opsin-data.bin", dir)), files = new Map<string, Int8Array>();
  for (let p = 0; ; ) {
    const n = pack.readUInt16BE(p); p += 2;
    if (!n) break;
    const name = pack.toString("latin1", p, p + n); p += n;
    const size = pack.readInt32BE(p); p += 4;
    files.set(name, new Int8Array(pack.buffer, pack.byteOffset + p, size)); p += size;
  }
  (globalThis as { opsinResource?: unknown }).opsinResource = (name: string) => files.get(name) ?? null;
  const opsin = await import(new URL("opsin.js", dir).href);
  opsin.init();
  // The descriptors a name gives (R, S, E, Z), sorted, against those Octet gives OPSIN's structure.
  const given = (name: string) => [...name.matchAll(/[(,[]\s*(?:\d+[a-zA-Z']*)?([RSEZ])(?=[,)\]])/g)].map((x) => x[1]).sort().join("");
  const NAMES = [
    // 17-ethynyl steroids: 17R (Indigo gives levonorgestrel's drawing 17S).
    "(8R,9S,13S,14S,17R)-17-ethynyl-13-methyl-7,8,9,11,12,14,15,16-octahydro-6H-cyclopenta[a]phenanthrene-3,17-diol",
    "(8R,9S,10R,13S,14S,17R)-17-ethynyl-17-hydroxy-13-methyl-1,2,6,7,8,9,10,11,12,14,15,16-dodecahydrocyclopenta[a]phenanthren-3-one",
    "(8R,9S,10R,13S,14S,17R)-13-ethyl-17-ethynyl-17-hydroxy-1,2,6,7,8,9,10,11,12,14,15,16-dodecahydrocyclopenta[a]phenanthren-3-one",
    // Sugars.
    "(2R,3S,4R,5R)-2,3,4,5,6-pentahydroxyhexanal", "(2R,3R,4S,5S,6R)-6-(hydroxymethyl)oxane-2,3,4,5-tetrol",
    "(2R,3R,4S,5S,6R)-2-[(2S,3S,4S,5R)-3,4-dihydroxy-2,5-bis(hydroxymethyl)oxolan-2-yl]oxy-6-(hydroxymethyl)oxane-3,4,5-triol",
    // Amino acids (cysteine is R).
    "(2S)-2-aminopropanoic acid", "(2R)-2-amino-3-sulfanylpropanoic acid", "(2S,3R)-2-amino-3-hydroxybutanoic acid", "(2S,3S)-2-amino-3-methylpentanoic acid",
    // Sulfoxides (armodafinil, esomeprazole).
    "2-[(R)-benzhydrylsulfinyl]acetamide", "6-methoxy-2-[(S)-(4-methoxy-3,5-dimethylpyridin-2-yl)methylsulfinyl]-1H-benzimidazole",
    // Meso and chiral pairs, deuterium.
    "(2R,3S)-2,3-dibromobutane", "(2R,3R)-2,3-dihydroxybutanedioic acid", "(2R,3S)-2,3-dihydroxybutanedioic acid", "(1S)-1-deuterio-1-phenylethanol", "(1R)-1-deuterioethan-1-ol",
    // E and Z: C=C, C=N, beside a ring, in an 8-ring.
    "(E)-but-2-enoic acid", "(Z)-but-2-enedioic acid", "(E)-N-hydroxyethanimine", "(Z)-N-hydroxyethanimine", "(2E)-2-ethylidenecyclohexan-1-one", "(2Z)-2-ethylidenecyclohexan-1-one", "(Z)-cyclooctene",
  ];
  for (const name of NAMES) {
    const m = parseStructure(opsin.parseToSmiles(name)), c = cipLabels(m);
    assert.equal([...c.atoms, ...c.bonds].filter(Boolean).sort().join(""), given(name), name);
  }
}

// ---- Where Indigo was wrong ----
// The 17-ethynyl steroids drawn from Octet's drug list: C17 (the carbon with the OH and the ethynyl) is R. Indigo gives
// levonorgestrel's drawing 17S, and norethisterone 17S from its SMILES.
for (const name of ["ethinylestradiol", "norethisterone", "levonorgestrel"]) {
  const m = parseStructure(DRUGS[name]), c17 = m.atoms.findIndex((_, i) => {
    const near = m.bonds.filter((b) => b.atoms.includes(i)).map((b) => ({ j: b.atoms[0] === i ? b.atoms[1] : b.atoms[0], b }));
    return near.some(({ j }) => m.atoms[j].label === "O") && near.some(({ j }) => m.bonds.some((b) => b.type === 3 && b.atoms.includes(j)));
  });
  assert.equal(cipLabels(m).atoms[c17], "R", name);
}

// ---- Rule 6, and allenes as auxiliary descriptors ----
// Rule 6 (Hanson et al.'s proposal) settles the most symmetric centres, with the validation suite's labels (by SMILES
// atom): spiro[4.4]nonane-1,6-dione and its mirror image, a spiro ketal, and a dichlorinated spiro[3.3]heptane.
for (const [smiles, want] of [["O=C1[C@@]2(CCCC2=O)CCC1", "3S"], ["O=C1[C@]2(CCCC2=O)CCC1", "3R"], ["C1[C@@]2(OCC1)OCCC2", "2R"], ["Cl[C@H]1C[C@]2(C1)C[C@H](C2)Cl", "2R 4S 7R"]]) {
  const got = cipLabels(parseStructure(smiles)).atoms.flatMap((x, i) => (x ? [`${i + 1}${x}`] : []));
  assert.equal(got.join(" "), want, smiles);
}
// An allene's M or P counts as an auxiliary descriptor. The ring CH of 1-ethyl-4-(prop-1-en-1-ylidene)cyclohexane is
// pseudoasymmetric: its two ring branches differ only in how they see the allene (the suite's VS231, drawn as the
// suite draws it, the allene's CH3 on a hash and its H implied). With the ethyl turned from a hash to a wedge: r.
const ylidene = (wedge: number): Mol => {
  const xy = [[2.4093, -0.3335], [-2.5511, 1.0926], [-0.0662, 1.0888], [-0.0767, -0.34], [-0.8912, 1.0948], [-0.9016, -0.334], [1.1668, 0.3756], [1.9927, 0.3797], [-2.1347, 0.3794], [0.341, 0.3714], [-1.3088, 0.3835]];
  return {
    atoms: xy.map(([x, y]) => atom("C", [x, y, 0])),
    bonds: [bond(9, 2), bond(9, 3), bond(9, 6, { type: 2 }), bond(2, 4), bond(3, 5), bond(4, 10), bond(5, 10), bond(6, 7, { type: 2 }), bond(7, 0, { stereo: 6 }), bond(8, 1), bond(10, 8, { stereo: wedge })],
  };
};
assert.equal(labels(ylidene(6))[10], "s");
assert.equal(labels(ylidene(1))[10], "r");

// ---- Drawings from a hostile file ----
// A bond to a missing atom, a place that is not a number, a centre between two equal 450-carbon arms: no label where
// nothing can be read, and no hang.
assert.deepEqual(cipLabels({ atoms: [atom("C", [0, 0, 0])], bonds: [bond(0, 5, { stereo: 1 }), bond(0, 0, { type: 2 })] }).atoms, [undefined]);
const lost = butanol({ stereo: 1 });
lost.atoms[1] = { ...lost.atoms[1], location: [NaN, NaN, 0] };
assert.equal(labels(lost)[0], undefined);
const arm = (side: number) => Array.from({ length: 450 }, (_, k) => atom("C", [side * (k + 1) * 0.87, k % 2 ? 0 : -0.5, 0]));
const long: Mol = { atoms: [atom("C", [0, 0, 0]), atom("O", [0, 1, 0]), ...arm(-1), ...arm(1)], bonds: [bond(0, 1, { stereo: 1 }), bond(0, 2), bond(0, 452)] };
for (let k = 0; k < 449; k++) long.bonds.push(bond(2 + k, 3 + k), bond(452 + k, 453 + k));
const t0 = performance.now();
assert.equal(labels(long)[0], undefined);
assert.ok(performance.now() - t0 < 500, "two long equal arms");

// ---- Time ----
// Paclitaxel (62 atoms, 11 centres) in well under 5 ms; a wedge on every CH of dodecahedrane (nothing is a centre,
// and every digraph is a cage) ends with no labels, without stalling.
const time = (m: Mol, runs: number) => { cipLabels(m); const t = performance.now(); for (let k = 0; k < runs; k++) cipLabels(m); return (performance.now() - t) / runs; };
const taxol = parseStructure(DRUGS.paclitaxel);
assert.equal(cipLabels(taxol).atoms.filter(Boolean).length, 11);
assert.ok(time(taxol, 20) < 5, "paclitaxel under 5 ms");
const cage = parseStructure("[C@H]12[C@H]3[C@H]4[C@H]5[C@H]1[C@H]6[C@H]7[C@H]2[C@H]8[C@H]3[C@H]9[C@H]4[C@H]%10[C@H]5[C@H]6[C@H]%11[C@H]7[C@H]8[C@H]9[C@H]%10%11");
assert.ok(time(cage, 2) < 500, "dodecahedrane under 0.5 s");
assert.ok(!cipLabels(cage).atoms.some(Boolean));
console.log("cip.check: ok");
