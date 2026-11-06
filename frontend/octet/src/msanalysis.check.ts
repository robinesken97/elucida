// Run: node src/msanalysis.check.ts. Fails loudly if Mass Spec Analysis gets an exact mass, an adduct's m/z, the
// electron, an isotope pattern, a fragment set or the HRMS line wrong. Reference masses: PubChem's monoisotopic
// masses (read 27 October 2026) and NIST's isotope masses; each m/z worked out by hand beside it.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

// chem.ts loads Indigo's wasm as a browser does; these stand in for the browser (as chem.check.ts).
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const { expandWithOrigins, importStructure, ready } = await import("./chem.ts");
const { subset } = await import("./edit.ts");
const ms = await import("./msanalysis.ts");
type Mol = import("./render.ts").Mol;
await ready;

const near = (a: number | undefined, b: number, tol = 1e-6, what = "") => assert.ok(a !== undefined && Math.abs(a - b) <= tol, `${what}: ${a} is not ${b}`);
// A structure from SMILES, as the panel takes it: all its atoms, and cuts through the given bonds (each cut a short
// line across the bond's middle).
function load(smiles: string, cutBonds: number[][] = []) {
  const mol: Mol = importStructure(smiles), ids = mol.atoms.map((_, i) => i);
  const cuts = cutBonds.map((bonds): [number, number][] => bonds.map((k) => {
    const [a, b] = mol.bonds[k].atoms.map((i) => mol.atoms[i].location), m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], d = [b[0] - a[0], b[1] - a[1]];
    return [[m[0] - d[1] * 0.3, m[1] + d[0] * 0.3], [m[0] + d[1] * 0.3, m[1] - d[0] * 0.3]];
  })[0]);
  const s = ms.structureOf(mol, ids, expandWithOrigins(subset(mol, new Set(ids))), cuts);
  return { mol, s, frags: (mode: import("./msanalysis.ts").Mode = "simultaneous") => ms.fragmentsOf({ ...s, mode }) };
}
const bondBetween = (m: Mol, a: string, b: string) => m.bonds.findIndex((x) => { const l = x.atoms.map((i) => m.atoms[i].label).sort().join(); return l === [a, b].sort().join(); });

// The electron: CODATA 2022. A hydrogen atom less an electron is a proton (CODATA 2022: 1.007 276 466 5789 u) to
// within the atom's 13.6 eV binding energy (1.5 × 10⁻⁸ u).
near(ms.ELECTRON, 0.000548579909, 1e-12, "electron");
near(1.00782503223 - ms.ELECTRON, 1.0072764665789, 2e-8, "proton");

// Monoisotopic masses against PubChem's.
for (const [smiles, formula, mono] of [
  ["Cn1cnc2c1c(=O)n(C)c(=O)n2C", "C8H10N4O2", 194.08037557], // caffeine
  ["CC(=O)Nc1ccc(O)cc1", "C8H9NO2", 151.06332853], // paracetamol
  ["COc1cc(CC=C)ccc1O", "C10H12O2", 164.083729621], // eugenol
  ["CC(=O)c1ccccc1", "C8H8O", 120.057514874], // acetophenone
  ["C[Si](C)(C)C", "C4H12Si", 88.070826917], // tetramethylsilane
  ["BrCCBr", "C2H4Br2", 185.86798], // 1,2-dibromoethane: 79Br and 81Br are about as abundant; 79Br is the more
] as const) {
  const f = load(smiles).frags()[0];
  assert.equal(ms.hill(f.counts), formula);
  near(ms.monoisotopic(f.counts), mono, 2e-5, formula);
}
// Deuterium counts as D (CD3OH: 12 + 3 × 2.01410177812 + 1.00782503223 + 15.99491461957).
const cd3 = load("[2H]C([2H])([2H])O").frags()[0];
assert.equal(ms.hill(cd3.counts), "CHD3O");
near(ms.monoisotopic(cd3.counts), 35.04504498616, 1e-9, "CD3OH");

// Adducts and charge states, with the electron counted.
const eugenol = load("COc1cc(CC=C)ccc1O").frags()[0];
const mh = ms.ionOf(eugenol, eugenol, "M+H", 1)!;
assert.equal(mh.label, "[M+H]+");
assert.equal(mh.formula, "C10H13O2");
near(mh.mono, 164.083729621 + 1.00782503223 - 0.000548579909, 1e-6, "[M+H]+");
assert.equal(mh.mono!.toFixed(4), "165.0910");
assert.equal(mh.radical, false);
const glucose = load("OCC1OC(O)C(O)C(O)C1O").frags()[0];
near(ms.ionOf(glucose, glucose, "M+Na", 1)!.mono, 180.0633881 + 22.989769282 - 0.000548579909, 1e-6, "[M+Na]+");
near(ms.ionOf(glucose, glucose, "M+K", 1)!.mono, 180.0633881 + 38.9637064864 - 0.000548579909, 1e-6, "[M+K]+");
near(ms.ionOf(glucose, glucose, "M+NH4", 1)!.mono, 180.0633881 + 14.00307400443 + 4 * 1.00782503223 - 0.000548579909, 1e-6, "[M+NH4]+");
assert.equal(ms.ionOf(glucose, glucose, "M+NH4", 1)!.mono!.toFixed(4), "198.0972");
near(ms.ionOf(glucose, glucose, "M+Cl", 1)!.mono, 180.0633881 + 34.968852682 + 0.000548579909, 1e-6, "[M+Cl]-");
assert.equal(ms.ionOf(glucose, glucose, "M+Cl", 1)!.label, "[M+Cl]−");
const benzoic = load("OC(=O)c1ccccc1").frags()[0], mmh = ms.ionOf(benzoic, benzoic, "M-H", 1)!;
near(mmh.mono, 122.03677943 - 1.00782503223 + 0.000548579909, 1e-6, "[M-H]-");
assert.equal(mmh.mono!.toFixed(4), "121.0295");
assert.equal(mmh.label, "[M−H]−");
// Charge states 2 to 4: n adducts and m/z over n.
const caffeine = load("Cn1cnc2c1c(=O)n(C)c(=O)n2C").frags()[0];
for (const z of [2, 3, 4]) near(ms.ionOf(caffeine, caffeine, "M+H", z)!.mono, (194.08037557 + z * (1.00782503223 - 0.000548579909)) / z, 1e-6, `[M+${z}H]${z}+`);
assert.equal(ms.ionOf(caffeine, caffeine, "M+H", 2)!.label, "[M+2H]2+");
assert.equal(ms.ionName("M-H", 2), "[M−2H]2−");
assert.equal(ms.ionName("M.+", 1), "[M]+•");
// A loss the formula cannot make (a chloride from caffeine) is no ion.
assert.equal(ms.ionOf(caffeine, caffeine, "M-Cl", 1), undefined);

// EI: the radical cation and its fragments. Acetophenone cut between the methyl and the carbonyl: the benzoyl
// cation (PhCO+, 105.0335) and the methyl cation; the molecule's ion is a radical, the benzoyl one is not.
const aceto = load("CC(=O)c1ccccc1", [[0]]), af = aceto.frags();
assert.deepEqual(af.map((f) => ms.hill(f.counts)), ["C8H8O", "C7H5O", "CH3"]);
const mdot = ms.ionOf(af[0], af[0], "M.+", 1)!;
assert.equal(mdot.label, "[M]+•");
assert.equal(mdot.radical, true);
near(mdot.mono, 120.057514874 - 0.000548579909, 1e-6, "[M]+.");
const benzoyl = ms.ionOf(af[1], af[0], "M.+", 1)!;
assert.equal(benzoyl.label, "[M−CH3]+");
assert.equal(benzoyl.radical, false);
assert.equal(benzoyl.mono!.toFixed(4), "105.0335");
assert.equal(ms.ionOf(af[2], af[0], "M.+", 1)!.label, "[CH3]+");
// With an adduct, the fragment's label keeps it: [M+H−CH3]+.
assert.equal(ms.ionOf(af[1], af[0], "M+H", 1)!.label, "[M+H−CH3]+•");

// ChemDraw's three modes on hexane cut at bonds 1 and 3 (C1–C2 and C3–C4): all at once makes three pieces; each on
// its own makes two each; every combination adds the middle piece to those.
const hex = load("CCCCCC", [[1], [3]]);
const sizes = (mode: import("./msanalysis.ts").Mode) => hex.frags(mode).map((f) => f.atoms.length);
assert.deepEqual(sizes("simultaneous"), [6, 2, 2, 2]);
assert.deepEqual(sizes("sequential"), [6, 4, 4, 2, 2]);
assert.deepEqual(sizes("combinatorial"), [6, 4, 4, 2, 2, 2]);
assert.deepEqual(hex.frags("combinatorial").find((f) => f.atoms.join() === "2,3")!.lines, [0, 1]);
// Tab on an atom (ChemDraw's): its fragments smallest first, the molecule last, round again; Shift+Tab goes back. On a
// bond, the fragments with both its atoms.
const comb = hex.frags("combinatorial");
const tabs = [0, 1, 2, 3].map((n) => comb[ms.fragmentWith(comb, [2], n)!].atoms.join());
assert.deepEqual(tabs, ["2,3", "2,3,4,5", "0,1,2,3", "0,1,2,3,4,5"]);
assert.equal(ms.fragmentWith(comb, [2], 4), ms.fragmentWith(comb, [2], 0));
assert.equal(ms.fragmentWith(comb, [2], -1), 0);
assert.deepEqual([0, 1].map((n) => comb[ms.fragmentWith(comb, [1, 2], n)!].atoms.join()), ["0,1,2,3", "0,1,2,3,4,5"]);
assert.equal(ms.fragmentWith(comb, [9], 0), undefined);
assert.equal(ms.fragmentWith(comb, [], 0), undefined);
// A line with corners (the panel takes each line's points) cuts every bond it crosses: hexane's bonds 1 and 3 by one
// line that goes across, along and back, as two straight lines would.
{
  const m = hex.mol, mid = (k: number) => { const [a, b] = m.bonds[k].atoms.map((i) => m.atoms[i].location); return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; };
  const [p, q] = [mid(1), mid(3)], top = Math.max(...m.atoms.map((a) => a.location[1])) + 1;
  const bent: [number, number][] = [[p[0], p[1] - 0.5], [p[0], top], [q[0], top], [q[0], q[1] - 0.5]];
  const s = ms.structureOf(m, m.atoms.map((_, i) => i), expandWithOrigins(subset(m, new Set(m.atoms.map((_, i) => i)))), [bent]);
  assert.deepEqual(s.lines, [[1, 3]]);
  assert.deepEqual(ms.fragmentsOf({ ...s, mode: "simultaneous" }).map((f) => f.atoms.length), sizes("simultaneous"));
}
// A cut through one ring bond alone leaves the molecule whole: only the molecule.
assert.equal(load("C1CCCCC1", [[0]]).frags().length, 1);

// Isotope patterns. Dichloromethane: M, M+2, M+4 about 100 : 64 : 10 (0.7576² : 2 × 0.7576 × 0.2424 : 0.2424²).
const dcm = ms.ionOf(load("ClCCl").frags()[0], load("ClCCl").frags()[0], "M.+", 1)!.pattern!.filter((p) => p.rel > 5);
assert.deepEqual(dcm.map((p) => Math.round(p.mz)), [84, 86, 88]);
near(dcm[1].rel, 64.0, 0.6, "Cl2 M+2");
near(dcm[2].rel, 10.3, 0.3, "Cl2 M+4");
// 1,2-Dibromoethane: 1 : 2 : 1, the mixed isotopologue tallest.
const dbe = load("BrCCBr").frags()[0], br = ms.ionOf(dbe, dbe, "M.+", 1)!.pattern!.filter((p) => p.rel > 5);
assert.deepEqual(br.map((p) => Math.round(p.rel)), [51, 100, 49]);
// [Ru(bpy)3]2+ as drawn (PubChem: C30H24N6Ru, 570.110585): its peaks half a unit apart, the monoisotopic one (102Ru)
// at (570.110585 − 2 electrons) / 2, and the 96Ru to 104Ru cluster.
const ru = load("[Ru+2]123(n4ccccc4-c4ccccn41)(n1ccccc1-c1ccccn12)n1ccccc1-c1ccccn13").frags()[0];
assert.equal(ms.hill(ru.counts), "C30H24N6Ru");
assert.equal(ru.charge, 2);
const ruIon = ms.ionOf(ru, ru, "M", 1)!;
assert.equal(ruIon.label, "[M]2+");
near(ruIon.mono, (570.110585 - 2 * 0.000548579909) / 2, 2e-5, "[Ru(bpy)3]2+");
const steps = ruIon.pattern!.slice(1).map((p, k) => p.mz - ruIon.pattern![k].mz);
assert.ok(steps.every((d) => Math.abs(d - 0.5) < 0.01), JSON.stringify(steps));
assert.equal(Math.round(ruIon.top! * 2), 570);
assert.ok(ruIon.pattern!.some((p) => Math.round(p.mz * 2) === 564 && p.rel > 10 && p.rel < 25), "96Ru peak");
// PdCl2(PPh3)2 (PubChem: 700.02346 with 106Pd) as [M−Cl]+.
const pd = load("Cl[Pd](Cl)([P](c1ccccc1)(c1ccccc1)c1ccccc1)[P](c1ccccc1)(c1ccccc1)c1ccccc1").frags()[0];
near(ms.monoisotopic(pd.counts), 700.02346, 1e-4, "PdCl2(PPh3)2");
const pdIon = ms.ionOf(pd, pd, "M-Cl", 1)!;
assert.equal(pdIon.label, "[M−Cl]+");
near(pdIon.mono, 700.02346 - 34.968852682 - 0.000548579909, 1e-4, "[M-Cl]+");
// Osmium, iridium, platinum and rhodium have patterns; rhodium has one isotope.
for (const [smiles, n] of [["O=[Os](=O)(=O)=O", 4], ["Cl[Ir]", 2], ["N[Pt](N)(Cl)Cl", 4], ["Cl[Rh]", 2]] as const) {
  const f = load(smiles).frags()[0];
  assert.equal(ms.ionOf(f, f, "M.+", 1)!.pattern!.filter((p) => p.rel > 5).length >= n, true, smiles);
}

// The HRMS line, the found value and its error in ppm.
assert.equal(ms.hrmsLine({ source: "ESI", label: "[M+H]+", formula: "C10H13O2", calcd: mh.mono!, found: 165.0912 }), "HRMS (ESI) m/z: [M+H]+ calcd for C10H13O2 165.0910; found 165.0912.");
assert.equal(ms.hrmsLine({ source: "EI", label: mdot.label, formula: mdot.formula, calcd: mdot.mono! }), "HRMS (EI) m/z: [M]+• calcd for C8H8O 120.0570.");
near(ms.ppm(165.0912, mh.mono!), 1.18, 0.01, "ppm");
// As a caption: the charge a superscript, a formula's counts subscripts, and a count of adducts left as it is.
assert.deepEqual(ms.chemRuns("[M−C10H8N2]2+"), [{ text: "[M−C" }, { text: "10", script: "sub" }, { text: "H" }, { text: "8", script: "sub" }, { text: "N" }, { text: "2", script: "sub" }, { text: "]" }, { text: "2+", script: "super" }]);
assert.deepEqual(ms.chemRuns("[M+2H]2+"), [{ text: "[M+2H" }, { text: "]" }, { text: "2+", script: "super" }]);
assert.equal(ms.chemRuns("HRMS (ESI) m/z: [M+H]+ calcd for C10H13O2 165.0910.").filter((r) => r.script).map((r) => `${r.script}:${r.text}`).join(" "), "super:+ sub:10 sub:13 sub:2");

// Peak lists: one to a line with words and headers skipped, JCAMP-DX pairs, scaled to 100.
assert.deepEqual(ms.parsePeaks("m/z  intensity\n165.0912\t2000\n166.0945 220\nnoise\n"), [{ mz: 165.0912, i: 100 }, { mz: 166.0945, i: 11 }]);
assert.deepEqual(ms.parsePeaks("##TITLE=x\n##PEAK TABLE=(XY..XY)\n105.03,50 120.06,100\n##END="), [{ mz: 105.03, i: 50 }, { mz: 120.06, i: 100 }]);
assert.deepEqual(ms.parsePeaks("165.0912"), [{ mz: 165.0912, i: 100 }]);
assert.equal(ms.parsePeaks("1e400 5\n-3 4").length, 0);
// Matching within a tolerance: 165.0912 is 1.2 ppm from [M+H]+, inside 5 ppm and outside 1 ppm (0.5 Da finds it too).
const peaks = ms.parsePeaks("165.0912 100\n166.0945 11.1\n167.0975 1.0");
assert.equal(ms.nearest(peaks, mh.mono!, "5ppm")?.mz, 165.0912);
assert.equal(ms.nearest(peaks, mh.mono!, "0.5Da")?.mz, 165.0912);
assert.equal(ms.nearest(peaks, mh.mono! + 0.01, "5ppm"), undefined);
assert.ok(ms.patternMatch(peaks, mh.pattern!, "5ppm")! > 90);

// Saved choices are checked; anything else falls back to the default.
assert.deepEqual(ms.readMsPrefs({ mode: "sequential", ion: "M+Na", z: 2, source: "EI", calc: "top", tolerance: "0.1Da" }), { mode: "sequential", ion: "M+Na", z: 2, source: "EI", calc: "top", tolerance: "0.1Da" });
assert.deepEqual(ms.readMsPrefs({ mode: "x", ion: "<b>", z: 9, source: 3, tolerance: "1e9ppm" }), ms.MS_DEFAULTS);
console.log("msanalysis.check: ok");
