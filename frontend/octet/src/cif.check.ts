// Run: node src/cif.check.ts. Fails loudly if the CIF and mmCIF reader misplaces an atom, bonds the wrong atoms, gives
// a bond the wrong order or a structure the wrong hand, keeps a polymer, water or second place in an mmCIF file, or
// opens a damaged or oversized file. Every file here is written by the check itself.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { isCif, readCif } from "./cif.ts";
import type { Mol } from "./render.ts";

type V = [number, number, number];
const deg = Math.PI / 180;

// --- Writing the files ----------------------------------------------------------------------------------------------

// A triclinic cell, so every term of the conversion counts.
const CELL = { a: 11.2, b: 7.9, c: 13.4, al: 85, be: 104, ga: 95 };
// Cartesian (Å) to fractional, for CELL: the inverse of the reader's conversion (a along x, b in the xy plane).
function frac([X, Y, Z]: V): V {
  const { a, b, c } = CELL, [ca, cb, cg, sg] = [Math.cos(CELL.al * deg), Math.cos(CELL.be * deg), Math.cos(CELL.ga * deg), Math.sin(CELL.ga * deg)];
  const v = Math.sqrt(1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg), z = Z / ((c * v) / sg), y = (Y - (c * (ca - cb * cg) * z) / sg) / (b * sg);
  return [(X - b * cg * y - c * cb * z) / a, y, z];
}
// A small-molecule CIF block: atoms as [label, type symbol (or none), Cartesian position, disorder group].
function block(name: string, atoms: [string, string | null, V, string?][], symbols = true) {
  const rows = atoms.map(([label, el, p, group]) => {
    const [x, y, z] = frac([p[0] + 3, p[1] + 2, p[2] + 4]).map((f, k) => (k === 0 ? `${f.toFixed(6)}(4)` : f.toFixed(6)));
    return `${label}${symbols ? ` ${el}` : ""} ${x} ${y} ${z} ${group ?? "."}`;
  });
  return [`data_${name}`, `_cell_length_a ${CELL.a}(2)`, `_cell_length_b ${CELL.b}`, `_cell_length_c ${CELL.c}`, `_cell_angle_alpha ${CELL.al}`, `_cell_angle_beta ${CELL.be}(1)`, `_cell_angle_gamma ${CELL.ga}`,
    "loop_", "_atom_site_label", ...(symbols ? ["_atom_site_type_symbol"] : []), "_atom_site_fract_x", "_atom_site_fract_y", "_atom_site_fract_z", "_atom_site_disorder_group", ...rows, ""].join("\n");
}
const at = (r: number, a: number, z = 0): V => [r * Math.cos(a * deg), r * Math.sin(a * deg), z];
const plus = (p: V, q: V): V => [p[0] + q[0], p[1] + q[1], p[2] + q[2]];

// 4-Nitrobenzoic acid, flat, with its hydrogens: a ring, a carboxylic acid (C=O shorter than C–OH) and a nitro group.
// O9 is a second place of O1 (disorder group 2), which the reader leaves out.
const C7: V = at(2.87, 90), O3: V = at(2.86, 270);
const nitrobenzoic: [string, string | null, V, string?][] = [
  ...[0, 1, 2, 3, 4, 5].map((k): [string, string, V] => [`C${k + 1}`, "C", at(1.39, 90 + 60 * k)]),
  ...[1, 2, 4, 5].map((k): [string, string, V] => [`H${k + 1}`, "H", at(2.47, 90 + 60 * k)]),
  ["C7", "C", C7], ["O1", "O", plus(C7, at(1.22, 150))], ["O2", "O", plus(C7, at(1.31, 30))], ["H8", "H", plus(plus(C7, at(1.31, 30)), at(0.97, 90))],
  ["N1", "N", O3], ["O3", "O", plus(O3, at(1.22, 210))], ["O4", "O", plus(O3, at(1.22, 330))], ["O9", "O", plus(C7, at(1.25, 160)), "2"],
];
// Acetonitrile: a triple bond.
const tetra = (r: number, k: number): V => [-r * Math.cos(70.5 * deg), r * Math.sin(70.5 * deg) * Math.cos(120 * k * deg), r * Math.sin(70.5 * deg) * Math.sin(120 * k * deg)];
const acetonitrile: [string, string, V][] = [["C1", "C", [0, 0, 0]], ["C2", "C", [1.46, 0, 0]], ["N1", "N", [2.62, 0, 0]], ...[0, 1, 2].map((k): [string, string, V] => [`H1${"ABC"[k]}`, "H", tetra(1.09, k)])];
// Bromochlorofluoromethane, in 3D, with no type symbols (the elements come from the labels): its hand must stay.
const dir: V[] = [[0, 0, 1], [0.943, 0, -0.333], [-0.471, 0.816, -0.333], [-0.471, -0.816, -0.333]];
const chiral: [string, null, V][] = [["C1", null, [0, 0, 0]], ...(["H1", "F1", "Cl1", "Br1"] as const).map((l, k): [string, null, V] => [l, null, dir[k].map((x) => x * [1.09, 1.35, 1.77, 1.94][k]) as V])];
// Dimethyl sulfoxide: S=O.
const dmso: [string, string, V][] = [["S1", "S", [0, 0, 0]], ["O1", "O", [0, 0, 1.5]], ["C1", "C", [1.66, 0, -0.6]], ["C2", "C", [-0.5, 1.58, -0.6]]];

const SMALL = [
  "#\\#CIF_1.1", "# Written for Octet's checks", "", "data_global", "_publ_contact_author_name 'O'Brien, A.'", "_publ_section_title",
  ";", "A text field with CIF in it, which the reader keeps as text:", "loop_", "_atom_site_label", "X1 9 9 9", ";",
  block("nitrobenzoic", nitrobenzoic), block("acetonitrile", acetonitrile), block("chiral", chiral, false), block("dmso", dmso),
].join("\n");

// --- Reading them ---------------------------------------------------------------------------------------------------

const formula = (m: Mol, atoms: number[]) => atoms.map((i) => m.atoms[i].label).sort().join("");
const bondOf = (m: Mol, a: string, b: string, from = 0) => m.bonds.find((x) => [a, b].every((n) => x.atoms.some((i) => i >= from && m.atoms[i].hiddenNumber === n)) && x.atoms.every((i) => i >= from));
const len = (m: Mol, i: number, j: number) => Math.hypot(...[0, 1, 2].map((k) => m.atoms[i].location[k] - m.atoms[j].location[k]));

assert.ok(isCif(SMALL), "a CIF file is a CIF file");
assert.ok(!isCif("benzene\n  Octet\n\n  6  6  0  0  0  0  0  0  0  0999 V2000\n"), "a MOL file is not");
assert.ok(!isCif("data_x\n_cell_length_a 10\n"), "a CIF file with no atoms is not");
const small = readCif(SMALL), s = small.atoms;
// Four structures, in a row: 17 + 6 + 5 + 4 atoms (O9 left out), each atom named as in the file and shaded by depth.
assert.equal(s.length, 32);
assert.ok(s.every((a) => a.shade && a.hiddenNumber), "every atom has depth shading and its name");
assert.equal(s.filter((a) => a.hiddenNumber === "O9").length, 0, "a second place (disorder group 2) is left out");
const parts = [[0, 17], [17, 23], [23, 28], [28, 32]].map(([p, q]) => Array.from({ length: q - p }, (_, k) => p + k));
assert.deepEqual(parts.map((g) => formula(small, g)), ["CCCCCCCHHHHHNOOOO", "CCHHHN", "BrCClFH", "CCOS"]);
for (let k = 1; k < parts.length; k++) {
  const right = Math.max(...parts[k - 1].map((i) => s[i].location[0])), left = Math.min(...parts[k].map((i) => s[i].location[0]));
  assert.ok(Math.abs(left - right - 2) < 1e-9, "each structure is two bond lengths to the right of the one before");
}
// Every distance as it was in the file, over the median bond between atoms other than H: the cell's conversion and the
// turn to the page keep the shape.
const unit = 1.39;
nitrobenzoic.filter((a) => a[3] !== "2").forEach(([, , p], i) => nitrobenzoic.filter((a) => a[3] !== "2").forEach(([, , q], j) => {
  assert.ok(Math.abs(len(small, i, j) - Math.hypot(...[0, 1, 2].map((k) => p[k] - q[k])) / unit) < 1e-4, `the distance from atom ${i} to atom ${j} stays`);
}));
// A flat structure faces the page: no depth.
assert.ok(parts[0].every((i) => s[i].location[2] === 0), "a flat structure lies in the page");
// The bonds: the ring Kekulé, C=O on the shorter C–O, a nitro group N+(=O)O−, C≡N, and S=O.
const order = (a: string, b: string, from = 0) => bondOf(small, a, b, from)?.type;
assert.equal(small.bonds.filter((b) => b.atoms[0] < 17).length, 17, "4-nitrobenzoic acid has 17 bonds");
assert.equal([1, 2, 3, 4, 5, 6].filter((k) => order(`C${k}`, `C${(k % 6) + 1}`) === 2).length, 3, "the ring has three double bonds");
assert.equal(order("C7", "O1"), 2);
assert.equal(order("C7", "O2"), 1);
assert.equal(order("C1", "C7"), 1);
assert.equal(order("N1", "O4"), 2);
assert.equal(order("N1", "O3"), 1);
assert.equal(order("C2", "N1", 17), 3, "acetonitrile's C≡N");
assert.equal(order("C1", "C2", 17), 1);
assert.equal(order("S1", "O1", 28), 2, "dimethyl sulfoxide's S=O");
assert.deepEqual(s.flatMap((a) => (a.charge ? [`${a.hiddenNumber} ${a.charge}`] : [])), ["N1 1", "O3 -1"], "only the nitro group is charged");
// The hand stays: the sign of F, Cl and Br's turn about C, as in the file.
const vol = (p: V[]) => { const [c, f, cl, br] = p, u = [f, cl, br].map((q) => [0, 1, 2].map((k) => q[k] - c[k])); return u[0][0] * (u[1][1] * u[2][2] - u[1][2] * u[2][1]) - u[0][1] * (u[1][0] * u[2][2] - u[1][2] * u[2][0]) + u[0][2] * (u[1][0] * u[2][1] - u[1][1] * u[2][0]); };
const named = (n: string) => s[parts[2].find((i) => s[i].hiddenNumber === n)!].location;
assert.equal(Math.sign(vol(["C1", "F1", "Cl1", "Br1"].map(named))), Math.sign(vol([chiral[0][2], chiral[2][2], chiral[3][2], chiral[4][2]])), "bromochlorofluoromethane keeps its hand");
assert.ok(parts[2].some((i) => Math.abs(s[i].location[2]) > 0.3), "a 3D structure keeps its depth");

// --- A macromolecule (mmCIF) ----------------------------------------------------------------------------------------

// A protein's atoms (entity 1), a selenomethionine in the chain (HETATM, but the polymer's), a ligand with no hydrogens
// (entity 2, benzoic acid) with one atom at two places, a magnesium ion (entity 3), waters, and a second model.
const ring = [0, 1, 2, 3, 4, 5].map((k) => at(1.39, 90 + 60 * k)), cx: V = at(2.87, 90);
const ligand: [string, string, V, string][] = [...ring.map((p, k): [string, string, V, string] => [`C${k + 1}`, "C", p, "."]), ["C7", "C", cx, "."], ["O1", "O", plus(cx, at(1.22, 150)), "A"], ["O1", "O", plus(cx, at(1.4, 160)), "B"], ["O2", "O", plus(cx, at(1.31, 30)), "."]];
const site = (group: string, el: string, name: string, comp: string, asym: string, entity: string, p: V, alt = ".", model = 1) =>
  `${group} ${el} ${name} ${alt} ${comp} ${asym} ${entity} ${p.map((x) => (x + 20).toFixed(3)).join(" ")} ${model}`;
const MM = [
  "data_1ABC", "#", "loop_", "_entity.id", "_entity.type", "1 polymer", "2 non-polymer", "3 non-polymer", "4 water", "#",
  "loop_", ...["group_PDB", "type_symbol", "label_atom_id", "label_alt_id", "label_comp_id", "label_asym_id", "label_entity_id", "Cartn_x", "Cartn_y", "Cartn_z", "pdbx_PDB_model_num"].map((t) => `_atom_site.${t}`),
  site("ATOM", "N", "N", "GLY", "A", "1", [0, 0, 9]), site("ATOM", "C", "CA", "GLY", "A", "1", [1.45, 0, 9]), site("HETATM", "SE", "SE", "MSE", "A", "1", [3, 0, 9]),
  ...ligand.map(([name, el, p, alt]) => site("HETATM", el, name, "BEZ", "B", "2", p, alt)),
  site("HETATM", "MG", "MG", "MG", "C", "3", [0, -9, 0]), site("HETATM", "O", "O", "HOH", "D", "4", [5, 5, 5]), site("HETATM", "O", "O", "HOH", "D", "4", [7, 5, 5]),
  ...ligand.map(([name, el, p, alt]) => site("HETATM", el, name, "BEZ", "B", "2", p, alt, 2)), "#", "",
].join("\n");
assert.ok(isCif(MM));
const mm = readCif(MM);
assert.deepEqual(mm.atoms.map((a) => a.hiddenNumber), ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "O1", "O2", "MG"], "the ligands only, in the first model, at their first place");
assert.ok(Math.abs(len(mm, 6, 7) - 1.22 / 1.39) < 0.01, "O1 at its first place (A)");
assert.equal(mm.atoms[9].label, "Mg");
assert.equal(mm.bonds.filter((b) => b.type === 2).length, 4, "with no hydrogens, the ring is Kekulé and C=O is on the shorter C–O");
assert.equal(mm.bonds.find((b) => b.atoms.includes(6) && b.atoms.includes(7))?.type, 2);
assert.ok(mm.atoms.every((a) => !a.charge), "no charges without hydrogens");
assert.ok(mm.atoms[9].location[0] - Math.max(...mm.atoms.slice(0, 9).map((a) => a.location[0])) > 1.99, "each ligand is a structure of its own, in a row");

// --- A ligand's own file (chem_comp) --------------------------------------------------------------------------------

// Acetate as the PDB's dictionary writes it: ideal coordinates, a charge and the bonds' orders, which the reader keeps.
const ACT = [
  "data_ACT", "_chem_comp.id ACT", "loop_", ...["comp_id", "atom_id", "type_symbol", "charge", "model_Cartn_x", "model_Cartn_y", "model_Cartn_z", "pdbx_model_Cartn_x_ideal", "pdbx_model_Cartn_y_ideal", "pdbx_model_Cartn_z_ideal"].map((t) => `_chem_comp_atom.${t}`),
  "ACT C C 0 ? ? ? 0.000 0.000 0.000", "ACT O O 0 ? ? ? 1.250 0.000 0.000", "ACT OXT O -1 ? ? ? -0.625 1.083 0.000", "ACT CH3 C 0 ? ? ? -0.760 -1.317 0.000",
  "loop_", "_chem_comp_bond.comp_id", "_chem_comp_bond.atom_id_1", "_chem_comp_bond.atom_id_2", "_chem_comp_bond.value_order", "ACT C O DOUB", "ACT C OXT SING", "ACT C CH3 SING", "",
].join("\n");
const act = readCif(ACT);
assert.deepEqual(act.atoms.map((a) => [a.label, a.charge ?? 0]), [["C", 0], ["O", 0], ["O", -1], ["C", 0]]);
assert.deepEqual(act.bonds.map((b) => b.type), [2, 1, 1], "the bonds' orders as the file gives them");

// --- Bond orders at real bond lengths -------------------------------------------------------------------------------

// Geometries optimised by GFN2-xTB, as "element x y z" (Å); each atom is named by its element and count (C1, C2, N1).
const xyz = (s: string): [string, string, V][] => {
  const n: Record<string, number> = {};
  return s.trim().split(/\s*,\s*/).map((a) => { const [el, ...p] = a.split(" "); return [`${el}${(n[el] = (n[el] ?? 0) + 1)}`, el, p.map(Number) as V]; });
};
const doubles = (m: Mol) => m.bonds.filter((b) => b.type === 2).map((b) => b.atoms.map((i) => m.atoms[i].hiddenNumber).sort().join("=")).sort();
const charged = (m: Mol) => m.atoms.flatMap((a) => (a.charge ? [`${a.hiddenNumber} ${a.charge}`] : []));
// Caffeine, with its hydrogens: its N-methyls stay neutral N (an N on three atoms takes N+ only where it must).
const caffeine = readCif(block("caffeine", xyz(`C -2.414 -0.656 -0.099, N -1.291 0.245 -0.091, C -1.324 1.585 -0.067, N -0.128 2.146 -0.053,
  C 0.732 1.107 -0.068, C 0.039 -0.101 -0.093, C 0.707 -1.360 -0.123, O 0.181 -2.470 -0.150, N 2.091 -1.208 -0.122, C 2.907 -2.414 -0.152,
  C 2.801 -0.017 -0.090, O 4.024 -0.021 -0.090, N 2.091 1.152 -0.069, C 2.793 2.421 -0.025, H -3.065 -0.431 -0.943, H -2.979 -0.557 0.827,
  H -2.038 -1.673 -0.187, H -2.234 2.150 -0.061, H 2.234 -3.264 -0.232, H 3.500 -2.479 0.759, H 3.582 -2.375 -1.005, H 3.682 2.350 -0.649,
  H 3.097 2.646 0.997, H 2.115 3.188 -0.388`)));
assert.deepEqual(doubles(caffeine), ["C2=N2", "C3=C4", "C5=O1", "C7=O2"], "caffeine's Kekulé structure");
assert.deepEqual(charged(caffeine), [], "caffeine has no charges");
// N-Methylpyridinium bromide: the ring's N is N+, as the ring needs its third double bond, and the bromide is Br−.
const pyridinium = readCif(block("pyridinium", xyz(`C -0.018 1.261 -0.147, N 1.424 1.266 -0.096, C 2.089 0.108 -0.057, C 3.467 0.080 0.015,
  C 4.171 1.277 0.050, C 3.459 2.469 0.016, C 2.081 2.428 -0.056, Br 7.714 -0.185 -0.008, H -0.380 2.146 -0.665, H -0.423 1.260 0.866,
  H -0.376 0.373 -0.661, H 1.510 -0.803 -0.085, H 3.997 -0.857 0.042, H 5.248 1.263 0.099, H 3.970 3.416 0.044, H 1.493 3.333 -0.083`)));
assert.equal(doubles(pyridinium).length, 3, "the pyridinium ring has three double bonds");
assert.ok(doubles(pyridinium).some((b) => b.includes("N1")), "one of them on N+");
assert.deepEqual(charged(pyridinium), ["N1 1", "Br1 -1"]);
// 9-Methyladenine as a ligand with no hydrogens (mmCIF): its NH2 (N3) stays NH2, and N9 (N1) stays neutral.
const adenine = readCif(["data_x", "loop_", ...["group_PDB", "type_symbol", "label_atom_id", "Cartn_x", "Cartn_y", "Cartn_z"].map((t) => `_atom_site.${t}`),
  ...xyz(`C -3.102 -1.957 -0.100, N -2.047 -0.979 -0.057, C -2.174 0.375 0.025, N -1.041 1.017 0.061, C -0.084 0.034 0.002, C 1.326 0.042 -0.001,
  N 2.057 1.157 0.060, N 1.957 -1.143 -0.071, C 1.243 -2.255 -0.135, N -0.069 -2.399 -0.142, C -0.709 -1.222 -0.070`).map(([name, el, p]) => `HETATM ${el} ${name} ${p.join(" ")}`), ""].join("\n"));
assert.deepEqual(doubles(adenine), ["C2=N2", "C3=C6", "C4=N4", "C5=N5"], "adenine's Kekulé structure");
assert.deepEqual(charged(adenine), [], "adenine has no charges");

// --- Hostile files --------------------------------------------------------------------------------------------------

const refused = (text: string, why: RegExp) => assert.throws(() => readCif(text), why);
refused("data_x\n_publ_section_title\n;\nno end\n", /text field has no end/);
refused("data_x\n_journal_name 'no end\n_cell_length_a 10\n", /quoted value has no end/);
refused("data_x\nloop_\n_atom_site_label\n_atom_site_cartn_x\n_atom_site_cartn_y\n_atom_site_cartn_z\nC1 0 0 0\nC2 1.5 0\n", /last row is short/);
refused("data_x\nloop_\n_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\nC1 0 0 0\n", /unit cell/);
refused("value\ndata_x\n", /before the first data block/);
refused("data_x\n_cell_length_a\ndata_y\n", /has no value/);
const many = (n: number) => ["data_x", "loop_", "_atom_site_label", "_atom_site_type_symbol", "_atom_site_Cartn_x", "_atom_site_Cartn_y", "_atom_site_Cartn_z", ...Array.from({ length: n }, (_, k) => `C${k} C ${(k % 10) * 1.5} ${Math.floor(k / 10) % 10 * 1.5} ${Math.floor(k / 100) * 1.5}`)].join("\n");
assert.equal(readCif(many(1000)).atoms.length, 1000);
refused(`data_x\nloop_\n${Array.from({ length: 101 }, (_, k) => `_atom_site_cartn_${k ? `t${k}` : "x"}`).join("\n")}\n${"0 ".repeat(101)}\n`, /more than 100 tags/);
assert.throws(() => readCif("data_x\n".repeat(1001)), (e: unknown) => e instanceof RangeError && /more than 1,000 data blocks/.test(e.message));
assert.throws(() => readCif(many(1001)), (e: unknown) => e instanceof RangeError && /more than 1,000 atoms/.test(e.message));
// The limit is for each structure: a file with several (a paper's crystal structures) opens with more in all.
assert.equal(readCif(many(600) + "\n" + many(600).replace("data_x", "data_y")).atoms.length, 1200);
// A large macromolecule: 200,000 polymer atoms are read past, quickly, and its one ligand opens.
const big = ["data_big", "loop_", ...["group_PDB", "type_symbol", "label_atom_id", "label_comp_id", "label_asym_id", "Cartn_x", "Cartn_y", "Cartn_z"].map((t) => `_atom_site.${t}`),
  ...Array.from({ length: 200_000 }, (_, k) => `ATOM C CA ALA A ${(k % 97).toFixed(3)} ${(k % 89).toFixed(3)} ${(k % 83).toFixed(3)}`), "HETATM ZN ZN ZN B 1.000 2.000 3.000", ""].join("\n");
const t0 = performance.now(), zn = readCif(big), ms = performance.now() - t0;
assert.deepEqual(zn.atoms.map((a) => a.label), ["Zn"]);
assert.ok(ms < 3000, `a ${(big.length / 1e6).toFixed(1)} MB mmCIF file reads in ${ms.toFixed(0)} ms`);

// --- Where it opens -------------------------------------------------------------------------------------------------

// Every structure file Octet reads (File > More Formats, a file dropped or opened) reads CIF first, and the command
// is in File > More Formats.
const read = (p: string) => readFileSync(new URL(p, import.meta.url), "utf8");
assert.match(read("chem.ts"), /export function importStructure\(text: string\): Mol \{\n\s+if \(isCif\(text\)\) return readCif\(text\);/);
assert.match(read("Editor.tsx"), /\["more_cif", "Open CIF or mmCIF…", <FolderOpen size=\{18\} \/>, \(\) => void openCif\(\)\],/);
assert.match(read("../src-tauri/src/main.rs"), /generate_handler!\[[^\]]*\bopen_cif\b/);
console.log(`cif.check: all passed (a ${(big.length / 1e6).toFixed(1)} MB mmCIF file in ${ms.toFixed(0)} ms).`);
