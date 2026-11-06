// Run: node src/chem.check.ts. Fails loudly if a written label can stop the drawing's chemistry or its drawing.
// Every label text (good, bad or random) goes through what the editor works out on each change: label expansion,
// formula and masses, the Properties values, stereo labels, a fragmentation cut, and the structure drawing.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { analyse, chiralFlagOnly, cleanUp, expandWithOrigins, fragmentMasses, importStructure, mapReaction, ready, stereoLabels, structures, toMolfile, toSmiles } = await import("./chem.ts");
const { hydrogens, render } = await import("./render.ts");
const { addSymbol } = await import("./edit.ts");
const { problems } = await import("./check.ts");
type Mol = import("./render.ts").Mol;
await ready;

// A label on its own, and the same label on the end of an ethyl group (CH3–CH2–label).
const alone = (text: string): Mol => ({ atoms: [{ label: "C", text, location: [0, 0, 0] }], bonds: [] });
const onEthyl = (text: string): Mol => ({
  atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [0.866, 0.5, 0] }, { label: "C", text, location: [1.732, 0, 0] }],
  bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }],
});
const box = Array.from({ length: 40 }, (_, i) => [9.6 * (i / 40), -9.5 * ((i * 7) % 40) / 40] as [number, number]);
const S = { bond: 19.2, line: 0.8, bold: 2.67, spacing: 3.46, hash: 3.33, margin: 2.25, size: 13.33 };
const tryAll = (m: Mol) => {
  expandWithOrigins(m);
  analyse(m);
  structures(m);
  stereoLabels(m);
  fragmentMasses(m, m.bonds.map((_, k) => k));
  render(m, S, () => ({ width: 9.6, ascent: 9.5, outline: box }), S.bond);
};

// Labels that once stopped the editor (H2O2 and HO2C made a SMILES Indigo cannot read), and other awkward ones.
const awkward = ["H2O2", "HO2C", "HOOC", "Et3N", "Me3Si", "Ph3P", "(CH2)3", "Me2N", "C0", "C999", "((((", "))", "()", "(", "2", "+", "–", " ", "OO(", "H", "HH", "D2O", "Xx", "*", "[", "]"];
for (const t of awkward) { tryAll(alone(t)); tryAll(onEthyl(t)); }
// Random labels from the characters labels are made of.
let seed = 7;
const rand = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const pieces = ["H", "C", "O", "N", "S", "P", "F", "Cl", "Br", "I", "Si", "B", "Me", "Et", "Ph", "Boc", "TBS", "Ac", "(", ")", "2", "3", "4", "12", "+", "-", "a", "x", " "];
for (let n = 0; n < 400; n++) {
  const t = Array.from({ length: 1 + Math.floor(rand() * 6) }, () => pieces[Math.floor(rand() * pieces.length)]).join("");
  tryAll(alone(t));
  tryAll(onEthyl(t));
}
console.log("chem.check: no label text stops the chemistry or the drawing");

// Labels read right to left count as the group they are: CH3CH2–HO2C is propanoic acid, H2O2 is hydrogen peroxide.
const formula = (m: Mol) => analyse(m)?.[0].formula;
assert.equal(formula(alone("H2O2")), "H2O2");
assert.equal(formula(onEthyl("HO2C")), "C3H6O2");
assert.equal(formula(onEthyl("HOOC")), "C3H6O2");
assert.equal(formula(onEthyl("CO2H")), "C3H6O2");
// A label Indigo cannot read stays one unknown atom.
assert.deepEqual(expandWithOrigins(onEthyl("Xx")).mol.atoms.map((a) => a.label), ["C", "C", "*"]);
// A ligand bonded to a metal has the hydrogens the drawing shows: PPh3 on Pd is P, not PH.
const ph3 = (at: number): Mol["atoms"] => [{ label: "P", location: [at, 1, 0] }, ...[0, 1, 2].flatMap((r) => Array.from({ length: 6 }, (_, k) => ({ label: "C", location: [at + r + Math.cos(k), 2 + Math.sin(k), 0] as [number, number, number] })))];
const pd: Mol = { atoms: [{ label: "Pd", location: [0, 0, 0] }, ...ph3(1), ...ph3(-1)], bonds: [] };
for (const p of [1, 20]) {
  pd.bonds.push({ type: 1, atoms: [0, p] });
  for (let r = 0; r < 3; r++) { const c = p + 1 + 6 * r; pd.bonds.push({ type: 1, atoms: [p, c] }); for (let k = 0; k < 6; k++) pd.bonds.push({ type: k % 2 ? 1 : 2, atoms: [c + k, c + ((k + 1) % 6)] }); }
}
pd.atoms.push({ label: "Cl", location: [0, -1, 0] }, { label: "Cl", location: [0, 1, 0] });
pd.bonds.push({ type: 1, atoms: [0, 39] }, { type: 1, atoms: [0, 40] });
assert.equal(formula(pd), "C36H30Cl2P2Pd");
console.log("chem.check: labels ok");

// An attachment point (wavy, diamond or star) is not an atom: it counts in no formula, mass or analysis, and its bond
// still takes up its neighbour's valence. C–O–C–N–C with both ends as attachment points is CH3NO (–O–CH2–NH–).
{
  const chain = (ends: Partial<Mol["atoms"][number]>): Mol => ({
    atoms: ["C", "O", "C", "N", "C"].map((label, k) => ({ label, location: [k, 0, 0] as [number, number, number], ...(k % 4 ? {} : ends) })),
    bonds: [0, 1, 2, 3].map((k) => ({ type: 1, atoms: [k, k + 1] as [number, number] })),
  });
  assert.equal(formula(chain({})), "C3H9NO");
  for (const attach of [true, "diamond", "star"] as const) {
    const a = analyse(chain({ attach }))?.[0], s = structures(chain({ attach }))?.[0];
    assert.equal(a?.formula, "CH3NO", String(attach));
    assert.ok(Math.abs((a?.weight ?? 0) - 45.04) < 0.01, "its mass");
    assert.ok(!/C 4|C 3\d/.test(s?.composition ?? ""), "its elemental analysis has one carbon: " + s?.composition);
  }
  assert.equal(formula(chain({ bead: true })), "CH3NO", "a polymer bead is not an atom either");
}
console.log("chem.check: attachment points ok");

// IDEA-SCALE-7: Clean Up keeps a structure's own scale: its bonds come out at its scale (the median of its atoms'),
// not at one bond length.
{
  const big: Mol = { atoms: ([[0, 0], [2.1, 0.3], [3.9, -0.2], [6, 0.4]] as const).map(([x, y]) => ({ label: "C", location: [x, y, 0] as [number, number, number], scale: 2 })),
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }, { type: 1, atoms: [2, 3] }] };
  const done = cleanUp(big), lengths = done.bonds.map((b) => Math.hypot(done.atoms[b.atoms[1]].location[0] - done.atoms[b.atoms[0]].location[0], done.atoms[b.atoms[1]].location[1] - done.atoms[b.atoms[0]].location[1]));
  assert.ok(Math.abs([...lengths].sort((a, b) => a - b)[1] - 2) < 1e-9 && lengths.every((l) => Math.abs(l - 2) < 0.04), `bonds at 200%: ${lengths}`);
  console.log("chem.check: clean up keeps the scale");
}

// The formula and masses come one entry per structure, in the drawing's order (a lone label and a lone carbon too),
// up to the number asked for. Each structure's values are kept by its content: moving it gives the same values, and
// a change to a label gives new ones.
{
  const drawn: Mol = {
    atoms: [{ label: "P", text: "PF6", charge: -1, location: [0, 0, 0] }, { label: "C", location: [2, 0, 0] }, { label: "C", location: [2.87, 0.5, 0] }, { label: "O", location: [3.73, 0, 0] }, { label: "C", location: [6, 0, 0] }],
    bonds: [{ type: 1, atoms: [1, 2] }, { type: 1, atoms: [2, 3] }],
  };
  assert.deepEqual(analyse(drawn)?.map((a) => a.formula), ["F6P", "C2H6O", "CH4"]);
  assert.deepEqual(analyse(drawn, 2)?.map((a) => a.formula), ["F6P", "C2H6O"]);
  assert.deepEqual(analyse(drawn), analyse(drawn));
  const moved = { ...drawn, atoms: drawn.atoms.map((a) => ({ ...a, location: [a.location[0] + 5, a.location[1] - 3, 0] as [number, number, number] })) };
  assert.deepEqual(analyse(moved), analyse(drawn));
  const relabelled = { ...drawn, atoms: drawn.atoms.map((a, i) => (i === 3 ? { ...a, text: "OMe" } : a)) };
  assert.deepEqual(analyse(relabelled)?.map((a) => a.formula), ["F6P", "C3H8O", "CH4"]);
  assert.equal(structures(drawn)?.[1]?.formula, "C2H6O");
  assert.equal(structures(relabelled)?.[1]?.formula, "C3H8O");
  // A label's group is read once and kept; a change to one expansion does not change the next.
  const first = expandWithOrigins(onEthyl("CO2Me")).mol;
  first.atoms[3].label = "Xx";
  assert.notEqual(expandWithOrigins(onEthyl("CO2Me")).mol.atoms[3].label, "Xx");
  console.log("chem.check: analysis by structure ok");
}

// Stereo labels are worked out structure by structure and kept: each copy of a structure gets its own labels, a
// moved copy keeps them, and a wedge turned to a hash gives the other label.
{
  const at = (x: number, y: number): [number, number, number] => [x, y, 0];
  const centre = (dx: number, stereo: number): Mol => ({
    atoms: [{ label: "C", location: at(dx, 0) }, { label: "F", location: at(dx + 0.866, 0.5) }, { label: "Cl", location: at(dx - 0.866, 0.5) }, { label: "Br", location: at(dx, -1) }],
    bonds: [{ type: 1, atoms: [0, 1], stereo }, { type: 1, atoms: [0, 2] }, { type: 1, atoms: [0, 3] }],
  });
  const join = (a: Mol, b: Mol): Mol => ({ atoms: [...a.atoms, ...b.atoms], bonds: [...a.bonds, ...b.bonds.map((x) => ({ ...x, atoms: x.atoms.map((i) => i + a.atoms.length) as [number, number] }))] });
  const two = join(centre(0, 1), centre(5, 1)), moved = join(centre(0, 1), centre(9, 1)), other = join(centre(0, 1), centre(5, 6));
  assert.deepEqual(analyse(two)?.map((a) => a.formula), ["CHBrClF", "CHBrClF"]);
  const label = (m: Mol) => stereoLabels(m)?.atoms;
  assert.ok(label(two)?.[0] && label(two)?.[0] === label(two)?.[4], "both copies labelled the same");
  assert.deepEqual(label(moved), label(two), "a moved copy keeps its label");
  assert.notEqual(label(other)?.[4], label(other)?.[0], "a hash gives the other label");
  console.log("chem.check: kept stereo labels ok");
}

// A label Indigo cannot read, alone, has no entry. A structure Indigo reads as a bad valence (a pyridine N bonded to
// Ru) keeps its formula and weight. Each exact mass is the structure's own monoisotopic mass.
{
  const lone: Mol = { atoms: [{ label: "C", text: "S0", location: [0, 0, 0] }, { label: "C", location: [3, 0, 0] }, { label: "O", location: [3.87, 0.5, 0] }], bonds: [{ type: 1, atoms: [1, 2] }] };
  assert.deepEqual(analyse(lone)?.map((a) => [a.formula, a.exact.toFixed(4)]), [["CH4O", "32.0262"]]);
  const ring = [0, 1, 2, 3, 4, 5].map((k) => ({ label: k ? "C" : "N", location: [Math.cos((k * Math.PI) / 3), Math.sin((k * Math.PI) / 3), 0] as [number, number, number] }));
  const bound: Mol = { atoms: [...ring, { label: "Ru", location: [2, 0, 0] }], bonds: [...ring.map((_, k) => ({ type: k % 2 ? 1 : 2, atoms: [k, (k + 1) % 6] as [number, number] })), { type: 1, atoms: [0, 6] }] };
  const [a] = analyse(bound) ?? [];
  assert.equal(a?.formula, "C5H5NRu");
  assert.ok(Number.isFinite(a?.weight));
  // Wedges Indigo rejects (three wedges on one carbon) do not take away the formula, the masses or the properties.
  const wedged: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [0.866, 0.5, 0] }, { label: "C", location: [1.732, 0, 0] }, { label: "O", location: [0.866, 1.5, 0] }],
    bonds: [{ type: 1, atoms: [1, 0], stereo: 1 }, { type: 1, atoms: [1, 2], stereo: 1 }, { type: 1, atoms: [1, 3], stereo: 6 }] };
  assert.equal(analyse(wedged)?.[0].formula, "C3H8O");
  assert.equal(structures(wedged)?.[0]?.formula, "C3H8O");
  console.log("chem.check: unreadable structures ok");
}

// A structure with a quadruple bond (Re2Cl8 drawn as Cl–Re≣Re–Cl) and one with a hydrogen bond keep a formula.
{
  const at = (label: string, x: number) => ({ label, location: [x, 0, 0] as [number, number, number] });
  const quad: Mol = { atoms: [at("Cl", 0), at("Re", 1), at("Re", 2), at("Cl", 3)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 14, atoms: [1, 2] }, { type: 1, atoms: [2, 3] }] };
  assert.deepEqual(analyse(quad)?.map((a) => a.formula), ["Cl2Re2"]);
  const dimer: Mol = { atoms: [at("O", 0), at("H", 1), at("O", 2)], bonds: [{ type: 1, atoms: [0, 1] }, { type: 10, atoms: [1, 2] }] };
  assert.deepEqual(analyse(dimer)?.map((a) => a.formula), ["H4O2"]);
  // A molfile has the hydrogen bond as bond type 10 and the quadruple bond as single, as ChemDraw writes them.
  const bondLines = (m: Mol) => toMolfile(m, true).split("\n").filter((l) => /^\s*\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s*$/.test(l)).map((l) => l.trim().split(/\s+/).slice(0, 3).join(" "));
  assert.deepEqual(bondLines(dimer), ["1 2 1", "2 3 10"]);
  assert.deepEqual(bondLines(quad), ["1 2 1", "2 3 1", "3 4 1"]);
  // The molfile keeps its three header lines (the first, its name, is blank), so it reads back, hydrogen bond and all.
  assert.match(toMolfile(dimer, true).split("\n")[3], /V2000$/);
  assert.deepEqual(importStructure(toMolfile(dimer, true)).bonds.map((b) => b.type), [1, 10]);
  // V3000 (ChemDraw 26.1's MOL) keeps the hydrogen bond too.
  assert.match(toMolfile(dimer), /V3000/);
  assert.deepEqual(importStructure(toMolfile(dimer)).bonds.map((b) => b.type), [1, 10]);
  console.log("chem.check: quadruple and hydrogen bonds ok");
  // A label with Interpret Chemically off is text, not chemistry: it adds nothing to the formula.
  const amine: Mol = { atoms: [{ ...at("N", 0), text: "NH2", chemical: false }, at("C", 1)], bonds: [{ type: 1, atoms: [0, 1] }] };
  assert.deepEqual(analyse(amine)?.map((a) => a.formula), ["CH3"]);
  assert.deepEqual(analyse({ ...amine, atoms: [{ ...at("N", 0), text: "NH2" }, at("C", 1)] })?.map((a) => a.formula), ["CH5N"]);
  console.log("chem.check: labels that are not chemistry ok");
}

// A molfile keeps its blank first line (the name), so it reads back, in Octet and in other programs.
{
  const molfile = toMolfile(onEthyl("OH"));
  assert.match(molfile, /^\n {2}-INDIGO-/);
  assert.deepEqual(importStructure(molfile).atoms.map((a) => a.label), ["C", "C", "O"]);
  // An atom bonded to a metal goes out with its valence, not a hydrogen count: in a drawing with an R group (a query)
  // that would be a query feature (M  MRV SMA) in the molfile.
  const query: Mol = { atoms: [{ label: "Pd", location: [0, 0, 0] }, { label: "N", location: [1, 0, 0] }, { label: "C", location: [2, 0, 0] }, { label: "*", location: [3, 0, 0] }],
    bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }, { type: 1, atoms: [2, 3] }] };
  assert.doesNotMatch(toMolfile(query), /MRV SMA/);
  console.log("chem.check: molfile ok");
}

// Settings (CH-34). Automatic reaction mapping keeps the pairs mapped by hand (Indigo's keep mode) and maps the rest.
{
  const chain = (maps: (number | undefined)[]): Mol => ({ atoms: ["C", "C", "C", "O"].map((label, i) => ({ label, location: [i * 0.866, i % 2 ? 0.5 : 0, 0] as [number, number, number], ...(maps[i] ? { map: maps[i] } : {}) })),
    bonds: [0, 1, 2].map((i) => ({ type: 1, atoms: [i, i + 1] as [number, number] })) });
  const kept = mapReaction([chain([undefined, undefined, undefined, 7])], [chain([undefined, undefined, undefined, 7])], true)!;
  assert.equal(kept.reactants[0][3], 7);
  assert.equal(kept.products[0][3], 7);
  assert.deepEqual(kept.reactants[0].slice(0, 3), kept.products[0].slice(0, 3));
  assert.ok(kept.reactants[0].slice(0, 3).every((n) => n !== undefined && n !== 7));
  // An MDL file's chiral flag alone (no V3000 stereo collections) is what Stereo flags from the chiral flag hides.
  assert.ok(chiralFlagOnly("\n  Octet\n\n  1  0  0  0  1  0  0  0  0  0999 V2000\n"));
  assert.ok(!chiralFlagOnly("M  V30 BEGIN COLLECTION\nM  V30 MDLV30/STERAC1 ATOMS=(1 2)\nM  V30 END COLLECTION\n V3000"));
  assert.ok(!chiralFlagOnly("CC(O)CC"));
  console.log("chem.check: settings ok");
}

// A lone pair on a carbon with two bonds makes a singlet carbene, as ChemDraw reads a lone pair on a carbon: the
// pair takes the carbon's two hydrogens, in the formula, SMILES and molfile. Two radical dots make a triplet. On an
// amine's N the first pair is its own and the next makes a nitrene; on an ether's O pairs never take anything.
{
  const chain = (label: string, n = 2): Mol => ({ atoms: [{ label: "C", location: [0, 0, 0] }, { label, location: [0.866, 0.5, 0] }, ...(n > 1 ? [{ label: "C", location: [1.732, 0, 0] as [number, number, number] }] : [])],
    bonds: [{ type: 1, atoms: [0, 1] }, ...(n > 1 ? [{ type: 1, atoms: [1, 2] as [number, number] }] : [])] });
  const formula = (m: Mol) => analyse(m)![0].formula;
  const carbene = addSymbol(chain("C"), 1, "pair");
  assert.deepEqual([carbene.atoms[1].radical, carbene.atoms[1].pairs], [3, undefined], "the pair is the carbene's");
  assert.equal(formula(carbene), "C3H6");
  assert.equal(toSmiles(carbene), "C[C]C |^3:1|");
  assert.match(toMolfile(carbene, true), /M {2}RAD {2}1 {3}2 {3}1/);
  assert.deepEqual(problems(carbene), []);
  assert.equal(addSymbol(carbene, 1, "pair").atoms[1].radical, undefined, "the next click clears it");
  const once = addSymbol(chain("C"), 1, "radical"), triplet = addSymbol(once, 1, "radical");
  assert.deepEqual([once.atoms[1].radical, triplet.atoms[1].radical, addSymbol(triplet, 1, "radical").atoms[1].radical], [1, 2, undefined]);
  assert.equal(toSmiles(triplet), "C[C]C |^4:1|");
  assert.equal(formula(triplet), "C3H6");
  const amine = addSymbol(chain("N", 1), 1, "pair"), nitrene = addSymbol(amine, 1, "pair");
  assert.deepEqual([amine.atoms[1].pairs, amine.atoms[1].radical, formula(amine)], [1, undefined, "CH5N"]);
  assert.deepEqual([nitrene.atoms[1].pairs, nitrene.atoms[1].radical, formula(nitrene)], [1, 3, "CH3N"]);
  assert.deepEqual(problems(nitrene), [], "a singlet nitrene has its two pairs");
  const marks = (m: Mol) => [m.atoms[1].pairs, m.atoms[1].radical];
  assert.deepEqual(marks(addSymbol(nitrene, 1, "pair")), [undefined, undefined]);
  let ether = chain("O");
  for (const k of [1, 2]) { ether = addSymbol(ether, 1, "pair"); assert.deepEqual([ether.atoms[1].pairs, ether.atoms[1].radical, formula(ether)], [k, undefined, "C2H6O"]); }
  assert.deepEqual(marks(addSymbol(ether, 1, "pair")), [undefined, undefined]);
  // Option-click, and Lone pairs as bars, draw the carbene's pair as a bar; Option-click on a carbene turns it back to dots.
  const barred = addSymbol(chain("C"), 1, "pair", true);
  assert.deepEqual([barred.atoms[1].radical, barred.atoms[1].pairs, barred.atoms[1].bars], [3, undefined, true], "Option-click makes a carbene");
  assert.deepEqual([addSymbol(chain("C"), 1, "pair", false, true).atoms[1].bars, addSymbol(barred, 1, "pair", true).atoms[1].bars], [true, undefined]);
  assert.deepEqual(problems(addSymbol(barred, 1, "pair", true)), []);
  // Methylene on its own keeps two hydrogens (a singlet is one pair, not three electrons).
  assert.equal(hydrogens("C", 0, 0, 3), 2);
  console.log("chem.check: carbenes and nitrenes ok");
}
