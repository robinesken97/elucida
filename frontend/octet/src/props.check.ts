// Run: node src/props.check.ts. Fails loudly if a property calculator drifts from its reference.
// References, computed once and kept here as numbers: RDKit 2026.09.1 (TPSA, NumRotatableBonds, aromatic atoms,
// Crippen logP and MolWt), thermo 0.6.1 Joback (Tb, Tm, Tc, Pc, Vc, ΔHf, ΔGf; benzaldehyde from thermo's own
// formulas with its groups, as thermo's aldehyde pattern misses an aldehyde on a ring) and Dimorphite-DL 2.1.0 sites.
import assert from "node:assert/strict";
import type { Graph } from "./naming.ts";
import { aromaticAtoms, logS, properties } from "./props.ts";

// A graph from atom symbols ("N+", "O-") and Kekulé bonds ("0-1", "1=2", "2#3"), with H counts from usual valences.
const VALENCE: Record<string, number[]> = { H: [1], C: [4], N: [3], O: [2], S: [2, 4, 6], P: [3, 5], F: [1], Cl: [1], Br: [1], I: [1] };
function mol(atoms: string, bonds: string): Graph {
  const g: Graph = {
    atoms: atoms.split(" ").map((t) => { const [, el, q] = /^([A-Z][a-z]?|\*)([+-]*)$/.exec(t)!; return { el, charge: q.length * (q[0] === "-" ? -1 : 1), h: 0 }; }),
    bonds: bonds.split(" ").filter(Boolean).map((t) => { const [, a, o, b] = /^(\d+)([-=#])(\d+)$/.exec(t)!; return { a: +a, b: +b, order: ("-=#".indexOf(o) + 1) as 1 | 2 | 3 }; }),
  };
  g.atoms.forEach((a, i) => {
    const used = g.bonds.reduce((s, b) => s + (b.a === i || b.b === i ? b.order : 0), 0);
    const v = a.el === "C" ? 4 - Math.abs(a.charge) : (VALENCE[a.el] ?? [4]).map((x) => x + a.charge).find((x) => x >= used) ?? 0;
    a.h = Math.max(0, v - used);
  });
  return g;
}

// Name, atoms, bonds, RDKit TPSA (Å²), RDKit rotatable bonds, RDKit aromatic atoms, thermo Joback [Tb K, Tm K, Tc K,
// Pc bar, Vc cm³/mol, ΔHf kJ/mol, ΔGf kJ/mol] (null where thermo gives none), Dimorphite sites [atom, kind, pKa].
type Row = [string, string, string, number, number, number[], number[] | null, [number, string, number][]];
const MOLECULES: Row[] = [
  ["ethanol", "C C O", "0-1 1-2", 20.23, 0, [], [337.54, 173.12, 499.407, 57.5664, 166.5, -236.84, -170.86], [[2, "alcohol", 14.7804]]],
  ["acetic acid", "C C O O", "0-1 1=2 1-3", 37.3, 0, [], [390.87, 272.9, 587.552, 57.3052, 171.5, -434.88, -377.95], [[3, "carboxylic acid", 3.4567]]],
  ["benzene", "C C C C C C", "0-1 1=2 2-3 3=4 4-5 5=0", 0, 0, [0, 1, 2, 3, 4, 5], [358.58, 171.28, 570.028, 47.6939, 263.5, 80.83, 121.68], []],
  ["toluene", "C C C C C C C", "0-1 1=2 2-3 3=4 4-5 5=6 6-1", 0, 0, [1, 2, 3, 4, 5, 6], [386.44, 195.07, 598.061, 41.1441, 319.5, 48.72, 120.47], []],
  ["phenol", "O C C C C C C", "0-1 1=2 2-3 3=4 4-5 5=6 6-1", 20.23, 0, [1, 2, 3, 4, 5, 6], [439.2, 283, 671.317, 59.2627, 229.5, -96.48, -32.94], [[0, "phenol", 10.0857]]],
  ["aniline", "N C C C C C C", "0-1 1=2 2-3 3=4 4-5 5=6 6-1", 26.02, 0, [1, 2, 3, 4, 5, 6], [436.09, 267.06, 666.317, 50.5859, 292.5, 103.15, 178.5], [[0, "aniline", 3.8993]]],
  ["pyridine", "C C C N C C", "0=1 1-2 2=3 3-4 4=5 5-0", 12.89, 0, [0, 1, 2, 3, 4, 5], [389.4, 231.55, 618.766, 54.7885, 256.5, 134.26, 190.31], [[3, "aromatic N", 4.3535]]],
  ["pyrrole", "C C C N C", "0-1 1=2 2-3 3-4 4=0", 15.79, 0, [0, 1, 2, 3, 4], [357.94, 256.53, 571.698, 59.9066, 210.5, 108.3, 174.69], [[3, "pyrrole NH", 14.5288]]],
  ["imidazole", "C C N C N", "0=1 1-2 2-3 3=4 4-0", 28.68, 0, [0, 1, 2, 3, 4], [388.76, 316.8, 620.664, 70.0268, 203.5, 161.73, 243.32], [[4, "aromatic N", 4.3535], [2, "azole NH", 12.234]]],
  ["furan", "C C C O C", "0-1 1=2 2-3 3-4 4=0", 13.14, 0, [0, 1, 2, 3, 4], [336.34, 178.07, 539.617, 56.8739, 194.5, -61.51, 0.86], []],
  ["thiophene", "C C C S C", "0-1 1=2 2-3 3-4 4=0", 0, 0, [0, 1, 2, 3, 4], [357.22, 234.95, 579.638, 57.1321, 219.5, 115.75, 126.84], []],
  ["naphthalene", "C C C C C C C C C C", "0=1 1-2 2=3 3-4 4=5 5-6 6=7 7-8 8=9 9-0 8-3", 0, 0, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [474.06, 261.58, 711.77, 38.965, 409.5, 177.87, 252.38], []],
  ["indole", "C C C C N C C C C", "0=1 1-2 2=3 3-4 4-5 5=6 6-7 7=8 8-0 7-3", 15.79, 0, [0, 1, 2, 3, 4, 5, 6, 7, 8], [473.42, 346.83, 713.651, 47.8259, 356.5, 205.34, 305.39], [[4, "pyrrole NH", 14.5288]]],
  ["quinoline", "C C C C N C C C C C", "0=1 1-2 2=3 3-4 4=5 5-6 6=7 7-8 8=9 9-0 8-3", 12.89, 0, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [504.88, 321.85, 757.78, 44.1496, 402.5, 231.3, 321.01], [[4, "aromatic N", 4.3535]]],
  ["purine", "C N C C N C N C N", "0=1 1-2 2=3 3-4 4-5 5=6 6-7 7=8 8-0 7-3", 54.46, 0, [0, 1, 2, 3, 4, 5, 6, 7, 8], [565.88, 527.64, 852.124, 74.9611, 335.5, 365.63, 511.28], [[1, "diazine N", 1.7671], [8, "diazine N", 1.7671], [6, "aromatic N", 4.3535], [4, "azole NH", 12.234]]],
  ["azulene", "C C C C C C C C C C", "0=1 1-2 2=3 3-4 4=5 5-6 6=7 7-8 8=9 9-0 8-2", 0, 0, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [474.06, 261.58, 711.77, 38.965, 409.5, 177.87, 252.38], []],
  ["2-pyridone", "O C C C C C N", "0=1 1-2 2=3 3-4 4=5 5-6 6-1", 32.86, 0, [1, 2, 3, 4, 5, 6], [452.91, 332.5, 696.68, 56.7027, 265.5, -56.2, 48.42], [[6, "aromatic NH", 7.17]]],
  ["caffeine", "C N C N C C C O N C C O N C", "0-1 1-2 2=3 3-4 4=5 5-6 6=7 6-8 8-9 8-10 10=11 10-12 12-13 5-1 12-4", 61.82, 0, [1, 2, 3, 4, 5, 6, 8, 10, 12], [640.4, 556.23, 872.233, 41.4627, 488.5, 30.43, 358.27], [[8, "aromatic N", 4.3535], [3, "aromatic N", 4.3535], [1, "aromatic N", 4.3535], [12, "aromatic N", 4.3535]]],
  ["aspirin", "C C O O C C C C C C C O O", "0-1 1=2 1-3 3-4 4=5 5-6 6=7 7-8 8=9 9-10 10=11 10-12 9-4", 63.6, 2, [4, 5, 6, 7, 8, 9], [640.91, 433.06, 867.832, 35.7707, 481.5, -671.58, -526.6], [[12, "carboxylic acid", 3.4634]]],
  ["ibuprofen", "C C C C C C C C C C C C C O O", "0-1 1-2 1-3 3-4 4-5 5=6 6-7 7=8 8-9 7-10 10-11 10-12 12=13 12-14 9=4", 37.3, 4, [4, 5, 6, 7, 8, 9], [673.33, 405.81, 891.471, 23.9119, 667.5, -447.42, -187.43], [[14, "carboxylic acid", 3.4567]]],
  ["paracetamol", "C C O N C C C C O C C", "0-1 1=2 1-3 3-4 4-5 5=6 6-7 7-8 7=9 9-10 10=4", 49.33, 1, [4, 5, 6, 7, 9, 10], [593.98, 420.65, 828.117, 48.9021, 382.5, -208.34, -65.26], [[8, "phenol", 7.0654], [3, "amide", 15.1]]],
  ["nicotine", "C N C C C C C C C C N C", "0-1 1-2 2-3 3-4 4-5 5-6 6=7 7-8 8=9 9-10 10=11 5-1 11-6", 16.13, 1, [6, 7, 8, 9, 10, 11], [532.23, 347.31, 769.449, 34.8888, 503.5, 153.76, 382.21], [[10, "aromatic N", 4.3535], [1, "tertiary amine", 9.402]]],
  ["glycine", "N C C O O", "0-1 1-2 2=3 2-4", 63.32, 1, [], [463.4, 356.16, 674.466, 62.5901, 200.5, -401.09, -311.5], [[4, "carboxylic acid", 3.4567], [0, "primary amine", 8.1591]]],
  ["glycine zwitterion", "N+ C C O O-", "0-1 1-2 2=3 2-4", 67.77, 1, [], null, [[4, "carboxylic acid", 3.4567], [0, "primary amine", 8.1591]]],
  ["nitrobenzene", "O- N+ O C C C C C C", "0-1 1=2 1-3 3=4 4-5 5=6 6-7 7=8 8-3", 43.14, 1, [3, 4, 5, 6, 7, 8], [515.4, 327.41, 769.559, 47.4969, 345.5, 58.6, 147.6], []],
  ["acetonitrile", "C C N", "0-1 1#2", 23.79, 0, [], [347.44, 177.29, 541.679, 48.562, 173.5, 80.27, 99.14], []],
  ["DMSO", "C S C O", "0-1 1-2 1=3", 17.07, 0, [], null, []],
  ["cyclohexane", "C C C C C C", "0-1 1-2 2-3 3-4 4-5 5-0", 0, 0, [], [361.1, 169, 565.721, 41.3029, 305.5, -92.51, 31.8], []],
  ["hexane", "C C C C C C", "0-1 1-2 2-3 3-4 4-5", 0, 3, [], [336.88, 157.38, 500.273, 31.071, 371.5, -167.17, -0.36], []],
  ["benzoic acid", "O C O C C C C C C", "0-1 1=2 1-3 3=4 4-5 5=6 6-7 7=8 8-3", 37.3, 1, [3, 4, 5, 6, 7, 8], [531.95, 355.67, 764.7, 46.277, 343.5, -301.55, -223.44], [[0, "carboxylic acid", 3.4634]]],
  ["morpholine", "C C O C C N", "0-1 1-2 2-3 3-4 4-5 5-0", 21.26, 0, [], [390.84, 278.06, 610.06, 55.0326, 251.5, -145.42, 16.55], [[5, "secondary amine", 8.1591]]],
  ["acetone", "C C C O", "0-1 1-2 1=3", 17.07, 0, [], [322.11, 173.5, 500.559, 48.025, 209.5, -217.83, -154.54], []],
  ["2-methylphenol", "C C C C C C C O", "0-1 1=2 2-3 3=4 4-5 5=6 6-7 6-1", 20.23, 0, [1, 2, 3, 4, 5, 6], [467.06, 306.79, 696.982, 50.2993, 285.5, -128.59, -34.15], [[7, "phenol", 10.0857]]],
  ["aziridine", "C C N", "0-1 1-2 2-0", 21.94, 0, [], [305.32, 239.51, 496.652, 66.9665, 142.5, 46.34, 122.13], [[2, "secondary amine", 8.1591]]],
  ["oxirane", "C C O", "0-1 1-2 2-0", 12.53, 0, [], [283.72, 161.05, 463.694, 63.39, 126.5, -123.47, -51.7], []],
  ["sulfanilamide", "N C C C C C C S N O O", "0-1 1-2 2=3 3-4 4=5 5-6 4-7 7-8 7=9 7=10 6=1", 86.18, 1, [1, 2, 3, 4, 5, 6], null, [[8, "sulfonamide", 7.916], [0, "aniline", 3.8993]]],
  ["5-methyltetrazole", "C C N N N N", "0-1 1=2 2-3 3=4 4-5 5-1", 54.46, 0, [1, 2, 3, 4, 5], [478.26, 461.13, 742.544, 80.8706, 245.5, 236.48, 379.37], [[5, "tetrazole", 5.18]]],
  ["guanidine", "N C N N", "0-1 1-2 1=3", 75.89, 0, [], null, [[3, "guanidine", 12.0253]]],
  ["benzamidine", "N C N C C C C C C", "0-1 1=2 1-3 3=4 4-5 5=6 6-7 7=8 8-3", 49.87, 1, [3, 4, 5, 6, 7, 8], null, [[2, "amidine", 12.06]]],
  ["methanesulfonic acid", "C S O O O", "0-1 1=2 1=3 1-4", 54.37, 0, [], null, [[4, "sulfonic acid", -1.8185]]],
  ["methylphosphonic acid", "C P O O O", "0-1 1=2 1-3 1-4", 57.53, 0, [], null, [[3, "phosphonic acid", 1.8836], [4, "phosphonic acid", 7.2473]]],
  ["acetohydroxamic acid", "C C O N O", "0-1 1=2 1-3 3-4", 49.33, 0, [], [441.58, 275.71, 621.937, 64.8271, 207.5, -295.95, -210.39], [[4, "hydroxamic acid", 9.3019]]],
  ["succinimide", "O C C C C O N", "0=1 1-2 2-3 3-4 4=5 4-6 6-1", 46.17, 0, [], [495.26, 391.45, 747.457, 59.7216, 252.5, -282.66, -130.41], [[6, "imide", 8.6817]]],
  ["ethanethiol", "C C S", "0-1 1-2", 0, 0, [], [308.22, 148.76, 499.115, 55.1963, 201.5, -46.13, -4.65], [[2, "thiol", 10.814]]],
  ["triethylamine", "C C N C C C C", "0-1 1-2 2-3 3-4 2-5 5-6", 3.24, 3, [], [349.32, 189.85, 511.891, 31.0018, 389.5, -99.64, 110.42], [[2, "tertiary amine", 10.28]]],
  ["benzaldehyde", "O C C C C C C C", "0=1 1-2 2=3 3-4 4=5 5-6 6=7 7-2", 17.07, 1, [2, 3, 4, 5, 6, 7], [435.1, 237.07, 654.038, 45.3468, 336.5, -36.86, 20.95], []],
  ["ethyl acetate", "C C O C C O", "0-1 1-2 2-3 3-4 3=5", 26.3, 1, [], [349.34, 177.17, 523.901, 39.2094, 285.5, -443.17, -327.57], []],
  ["N-methylacetamide", "C C O N C", "0-1 1=2 1-3 3-4", 29.1, 0, [], [372.28, 226.16, 557.98, 48.9021, 244.5, -164.36, -65.15], [[3, "amide", 15.1]]],
  ["trifluorotoluene", "F C F F C C C C C C", "0-1 1-2 1-3 1-4 4=5 5-6 6=7 7-8 8=9 9-4", 0, 0, [4, 5, 6, 7, 8, 9], [381.02, 199.26, 571.345, 35.6427, 362.5, -548.36, -461.12], []],
  ["tert-butylbenzene", "C C C C C C C C C C", "0-1 1-2 1-3 1-4 4=5 5-6 6=7 7-8 8=9 9-4", 0, 0, [4, 5, 6, 7, 8, 9], [451.85, 231.3, 670.628, 29.9259, 476.5, -21.95, 148.57], []],
];

const near = (got: number, want: number, tol: number, what: string) => assert.ok(Math.abs(got - want) <= tol, `${what}: ${got} vs ${want}`);
for (const [name, atoms, bonds, tpsa, rotatable, aromatic, joback, sites] of MOLECULES) {
  const g = mol(atoms, bonds), p = properties(g);
  near(p.tpsa, tpsa, 0.01, `${name} tPSA`);
  assert.equal(p.rotatable, rotatable, `${name} rotatable bonds`);
  assert.deepEqual(aromaticAtoms(g).flatMap((a, i) => (a ? [i] : [])), aromatic, `${name} aromatic atoms`);
  near(p.aromaticProportion, aromatic.length / g.atoms.length, 1e-9, `${name} aromatic proportion`);
  if (!joback) assert.equal(p.joback, undefined, `${name} has no Joback estimate`);
  else {
    const j = p.joback!, got = [j.tb, j.tm, j.tc, j.pc, j.vc, j.hf, j.gf];
    joback.forEach((v, k) => near(got[k], v, Math.max(0.005 * Math.abs(v), 0.01), `${name} Joback ${"tb tm tc pc vc hf gf".split(" ")[k]}`));
  }
  const key = (s: [number, string, number][]) => s.map(([a, k]) => `${a} ${k}`).sort();
  assert.deepEqual(key(p.pka.map((s) => [s.atom, s.kind, s.pka])), key(sites), `${name} pKa sites`);
  for (const [a, k, v] of sites) near(p.pka.find((s) => s.atom === a && s.kind === k)!.pka, v, 0.005, `${name} pKa of atom ${a}`);
}

// Joback's worked example in thermo's documentation: acetone, Tb 322.11 K, Tm 173.5 K, Tc 500.56 K, ΔHf −217.83 kJ/mol.
const acetone = properties(mol("C C C O", "0-1 1-2 1=3")).joback!;
near(acetone.tb, 322.11, 0.005, "acetone Tb");
near(acetone.tc, 500.559, 0.005, "acetone Tc");

// ESOL against Walters' coefficients with RDKit's Crippen logP and weight: name, logP, weight, logS.
for (const [name, logP, weight, want] of [
  ["aspirin", 1.3101, 180.159, -2.0918],
  ["ibuprofen", 3.0732, 206.285, -3.5391],
  ["naphthalene", 2.8398, 128.174, -3.1190],
  ["paracetamol", 1.3506, 151.165, -1.9693],
] as [string, number, number, number][]) {
  const row = MOLECULES.find((m) => m[0] === name)!;
  near(logS(logP, weight, properties(mol(row[1], row[2]))), want, 0.001, `${name} logS`);
}

// Drawn H atoms count as the hydrogens of their neighbour, and results keep the drawing's atom numbers.
const drawn = mol("H C C O H", "0-1 1-2 2-3 3-4");
drawn.atoms[1].h = 2;
const ethanol = properties(drawn);
near(ethanol.tpsa, 20.23, 0.01, "ethanol with drawn H, tPSA");
assert.deepEqual(ethanol.pka.map((s) => [s.atom, s.kind]), [[3, "alcohol"]]);
assert.equal(aromaticAtoms(drawn).length, 5);
// Charged and pentavalent nitro groups are the same group.
assert.deepEqual(properties(mol("O N C C C C C C O", "0=1 1-2 2=3 3-4 4=5 5-6 6=7 7-2 1=8")).joback, properties(mol("O- N+ C C C C C C O", "0-1 1-2 2=3 3-4 4=5 5-6 6=7 7-2 1=8")).joback);
// An element Joback has no group for, or a label Octet could not read ("*"), gives no Joback estimate.
assert.equal(properties(mol("C Si", "0-1")).joback, undefined);
assert.equal(properties(mol("C C *", "0-1 1-2")).joback, undefined);
console.log("props.check: ok");
