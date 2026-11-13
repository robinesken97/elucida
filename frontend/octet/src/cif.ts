// CIF and mmCIF files (issue 79): a crystal structure from its unit cell and fractional coordinates, the ligands of a
// macromolecule from its atom_site records (ChemDraw opens only those), or a ligand's own file from the PDB's Chemical
// Component Dictionary (chem_comp_atom, with its bonds from chem_comp_bond). Each data block, and each ligand, opens as
// a structure of its own, in a row. Where the file gives no bonds, two atoms closer than their covalent radii and 0.4 Å
// are bonded, and the bond orders come from the hydrogens found and the bond lengths. The 3D coordinates stay as depth,
// with depth shading on, as 3D Clean Up leaves a structure. Every file is hostile: the atoms and rows read are limited,
// and a damaged file is refused, never half read.
import { hydrogens, NONMETAL, QUADRUPLE, type Mol } from "./render.ts";
import { ELEMENTS } from "./labels.ts";
import { kekulise } from "./rings.ts";
import { crossV, dotV } from "./clean3d.ts";

type V = [number, number, number];
type Row = Record<string, string>;
type Block = { items: Map<string, string>; tables: Row[][] };
// An atom as read: its element, position (Å), name in the file (C12, O2', H1A) and charge.
type Site = { el: string; p: V; name: string; charge: number };
// A structure as read: its atoms, and its bonds as [atom, atom, order] when the file gives them.
type Group = { sites: Site[]; bonds?: [number, number, number][] };

const MOST = 1000; // atoms in one structure (a data block, or a ligand); MOST_ROWS limits the file
const MOST_ROWS = 20_000, MOST_TAGS = 100, MOST_BLOCKS = 1000; // rows kept from the tables Octet reads, tags in one, data blocks
// The tables Octet reads, by one tag each: the others are only checked.
const READ = new Set(["_atom_site_fract_x", "_atom_site_cartn_x", "_chem_comp_atom_atom_id", "_chem_comp_bond_atom_id_1", "_entity_type"]);
const WATER = new Set(["HOH", "DOD", "WAT", "H2O"]);
const ORDER: Record<string, number> = { SING: 1, DOUB: 2, TRIP: 3, QUAD: QUADRUPLE };
// An atom number Octet keeps in its files (as the CDXML reader takes AtomNumber).
const NUMBER = /^[\w'′*-]{1,8}$/;
// Atoms that take a double bond to a terminal O or S for each bond over their valence (sulfones, phosphates).
const HYPER = new Set(["P", "As", "S", "Se", "Te", "Cl", "Br", "I"]);

// Covalent radii (Å, Cordero et al. 2008; Mn, Fe and Co high spin) in hundredths, H to Cm by atomic number.
const RADII = ("31 28 128 96 84 76 71 66 57 58 166 141 121 111 107 105 102 106 203 176 170 160 153 139 161 152 150 124 132 122 122 120 119 120 " +
  "120 116 220 195 190 175 164 154 147 146 142 139 145 144 142 139 139 138 139 140 244 215 207 204 203 201 199 198 198 196 194 192 192 189 190 " +
  "187 187 175 170 162 151 144 141 136 136 132 145 146 148 140 150 150 260 221 215 206 200 196 190 187 180 169").split(" ");
const radius = new Map([...[...ELEMENTS].slice(0, RADII.length).map((el, k): [string, number] => [el, +RADII[k] / 100]), ["D", 0.31]]);

const fail = (why: string): never => { throw new Error(`This CIF file is damaged: ${why}.`); };
// A number as CIF writes it, with its standard uncertainty in brackets (1.2345(6)); NaN for ? and . (unknown).
const num = (s?: string) => (s ? Number(s.replace(/\(\d+\)$/, "")) : NaN);
const dist = (p: V, q: V) => Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
// The element a type symbol (C, Fe3+, CL) or, in a site's label (C12A, Cl1), its letters name.
const element = (s = "", label = false) => {
  const two = /^[a-z][a-z]/i.test(s) && (!label || /[a-z]/.test(s[1])) ? s[0].toUpperCase() + s[1].toLowerCase() : "", one = s.slice(0, 1).toUpperCase();
  return radius.has(two) ? two : radius.has(one) ? one : undefined;
};

// A CIF file: comments and blank lines, then its first data block, and atoms in an atom_site or chem_comp_atom table.
export const isCif = (text: string) =>
  /^﻿?(?:[ \t]*(?:#[^\n]*)?\r?\n)*[ \t]*data_\S/i.test(text) && /^[ \t]*_(?:atom_site[._](?:fract|cartn)_x|chem_comp_atom[._]atom_id)\s/im.test(text);

// The file's data blocks: each block's single items, and the rows of the tables Octet reads, each row by its tags.
// Tags are compared in lower case, with a DDL2 tag's first dot as an underscore (_atom_site.Cartn_x is
// _atom_site_cartn_x). A macromolecule's polymer atoms (ATOM) and waters are left out as they are read.
function blocks(text: string): Block[] {
  const out: Block[] = [], n = text.length, space = (c: number) => c === 32 || c === 9 || c === 10 || c === 13;
  let i = 0, block: Block | undefined, tag: string | undefined, tags: string[] = [], rows: Row[] | undefined, row: string[] = [], col = 0, kept = 0, pdb = -1, comp = -1;
  let loop = 0; // 0 no table, 1 a table's tags, 2 its values
  const end = () => {
    if (tag) fail(`${tag} has no value`);
    if (col) fail("a table's last row is short");
    loop = 0;
  };
  while (i < n) {
    const c = text.charCodeAt(i);
    if (space(c)) { i++; continue; }
    if (c === 35) { const e = text.indexOf("\n", i); i = e < 0 ? n : e; continue; }
    let value: string, word = false;
    if (c === 59 && (i === 0 || text[i - 1] === "\n" || text[i - 1] === "\r")) {
      // A text field: from a ; at the start of a line to the next.
      const e = text.indexOf("\n;", i);
      if (e < 0) fail("a text field has no end");
      value = text.slice(i + 1, e);
      i = e + 2;
    } else if (c === 39 || c === 34) {
      // A quoted value ends at its quote mark before a space or the end, on its own line.
      const line = text.indexOf("\n", i), stop = line < 0 ? n : line;
      let e = i;
      do e = text.indexOf(text[i], e + 1); while (e >= 0 && e < stop && e + 1 < n && !space(text.charCodeAt(e + 1)));
      if (e < 0 || e >= stop) fail("a quoted value has no end");
      value = text.slice(i + 1, e);
      i = e + 1;
    } else {
      let e = i;
      while (e < n && !space(text.charCodeAt(e))) e++;
      value = text.slice(i, e);
      i = e;
      word = true;
    }
    if (word) {
      const low = value.toLowerCase();
      if (low.startsWith("data_")) {
        end();
        if (out.length === MOST_BLOCKS) throw new RangeError(`It has more than ${MOST_BLOCKS.toLocaleString("en-GB")} data blocks.`);
        block = { items: new Map(), tables: [] };
        out.push(block);
        continue;
      }
      if (low === "loop_") { end(); loop = 1; tags = []; continue; }
      if (low.startsWith("save_") || low === "global_" || low === "stop_") { end(); continue; }
      if (value[0] === "_") {
        const t = low.replace(".", "_");
        if (loop === 1) tags.push(t);
        else { end(); tag = t; }
        continue;
      }
    }
    if (!block) return fail("a value comes before the first data block");
    if (tag) { block.items.set(tag, value); tag = undefined; continue; }
    if (loop === 1) {
      if (!tags.length) fail("a table has no tags");
      loop = 2;
      rows = tags.some((t) => READ.has(t)) ? [] : undefined;
      if (rows && tags.length > MOST_TAGS) fail(`a table has more than ${MOST_TAGS} tags`);
      if (rows) block.tables.push(rows);
      [pdb, comp] = [tags.indexOf("_atom_site_group_pdb"), tags.indexOf("_atom_site_label_comp_id")];
    }
    if (loop !== 2) fail(`the value ${value.slice(0, 20)} has no tag`);
    if (rows) row.push(value);
    if (++col < tags.length) continue;
    col = 0;
    if (!rows) continue;
    const r = row;
    row = [];
    if (r[pdb] === "ATOM" || WATER.has(r[comp])) continue;
    if (++kept > MOST_ROWS) throw new RangeError(`It has more than ${MOST_ROWS.toLocaleString("en-GB")} atoms and bonds.`);
    rows.push(Object.fromEntries(tags.map((t, k) => [t, r[k]])));
  }
  end();
  return out;
}

// A table's rows: its loop, or its one row written as single items.
const table = (b: Block, tag: string): Row[] => b.tables.find((t) => t[0]?.[tag] !== undefined) ?? (b.items.has(tag) ? [Object.fromEntries(b.items)] : []);

// The structures in a data block.
function groupsOf(b: Block): Group[] {
  const known = (s: Site) => !!s.el && s.p.every(Number.isFinite);
  // A ligand's own file: its ideal coordinates (else the model's), its charges and its bonds.
  const comp = table(b, "_chem_comp_atom_atom_id");
  if (comp.length) {
    const ideal = comp.every((r) => Number.isFinite(num(r._chem_comp_atom_pdbx_model_cartn_x_ideal))), xyz = ideal ? "_chem_comp_atom_pdbx_model_cartn_" : "_chem_comp_atom_model_cartn_";
    const sites = comp.map((r): Site => {
      const q = num(r._chem_comp_atom_charge);
      return { el: element(r._chem_comp_atom_type_symbol) ?? "", p: (["x", "y", "z"] as const).map((c) => num(r[`${xyz}${c}${ideal ? "_ideal" : ""}`])) as V, name: r._chem_comp_atom_atom_id ?? "", charge: Number.isInteger(q) && Math.abs(q) <= 8 ? q : 0 };
    }).filter(known);
    const at = new Map(sites.map((s, k) => [s.name, k])), given = table(b, "_chem_comp_bond_atom_id_1");
    const bonds = given.flatMap((r): [number, number, number][] => {
      const i = at.get(r._chem_comp_bond_atom_id_1), j = at.get(r._chem_comp_bond_atom_id_2);
      return i === undefined || j === undefined || i === j ? [] : [[i, j, ORDER[(r._chem_comp_bond_value_order ?? "").toUpperCase()] ?? 1]];
    });
    return [{ sites, bonds: given.length ? bonds : undefined }];
  }
  let rows = table(b, "_atom_site_fract_x");
  const fract = rows.length > 0;
  if (!fract) rows = table(b, "_atom_site_cartn_x");
  if (!rows.length) return [];
  let at = (r: Row): V => (["x", "y", "z"] as const).map((c) => num(r[`_atom_site_cartn_${c}`])) as V;
  if (fract) {
    // Fractional coordinates to Cartesian (Å): a along x, b in the xy plane.
    const [a, bb, c, al, be, ga] = ["length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma"].map((k) => num(b.items.get(`_cell_${k}`)));
    const [ca, cb, cg, sg] = [Math.cos((al * Math.PI) / 180), Math.cos((be * Math.PI) / 180), Math.cos((ga * Math.PI) / 180), Math.sin((ga * Math.PI) / 180)];
    const v = Math.sqrt(1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg);
    if (![a, bb, c].every((x) => x > 0.5 && x < 1000) || ![al, be, ga].every((x) => x > 5 && x < 175) || !(v > 0.01)) fail("its unit cell is missing or impossible");
    at = (r) => {
      const [x, y, z] = (["x", "y", "z"] as const).map((k) => num(r[`_atom_site_fract_${k}`]));
      return [a * x + bb * cg * y + c * cb * z, bb * sg * y + (c * (ca - cb * cg) * z) / sg, (c * v * z) / sg];
    };
  }
  // A macromolecule: its ligands only, as ChemDraw opens it. These are the atoms of entities that are not polymer or
  // water (with no entity table, the HETATM records that are not water), in the first model, at the first of an atom's
  // other places. Each ligand is a structure of its own. A crystal structure leaves out its disorder groups after the
  // first, and its dummy atoms.
  const types = new Map(table(b, "_entity_type").map((r) => [r._entity_id, r._entity_type?.toLowerCase()]));
  const model = rows[0]._atom_site_pdbx_pdb_model_num, alts = rows.map((r) => r._atom_site_label_alt_id).filter((x) => x && x !== "." && x !== "?");
  const groups = new Map<string, Site[]>();
  for (const r of rows) {
    const type = types.get(r._atom_site_label_entity_id), alt = r._atom_site_label_alt_id;
    if (type === "polymer" || type === "water" || r._atom_site_pdbx_pdb_model_num !== model || (alt && alt !== "." && alt !== "?" && alt !== alts[0]) || num(r._atom_site_disorder_group) > 1 || r._atom_site_calc_flag === "dum") continue;
    const name = r._atom_site_label ?? r._atom_site_label_atom_id ?? "", site = { el: element(r._atom_site_type_symbol) ?? element(name, true) ?? "", p: at(r), name, charge: 0 };
    if (!known(site)) continue;
    const key = r._atom_site_label_asym_id ?? "";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(site);
  }
  return [...groups.values()].map((sites) => ({ sites }));
}

// Bonds by distance: two atoms closer than their covalent radii and 0.4 Å, and not on one place. Two hydrogens are
// never bonded.
function near(s: Site[]): [number, number, number][] {
  const out: [number, number, number][] = [], r = s.map((x) => radius.get(x.el)!), h = s.map((x) => x.el === "H" || x.el === "D");
  for (let i = 0; i < s.length; i++) for (let j = i + 1; j < s.length; j++) {
    if (h[i] && h[j]) continue;
    const d = dist(s[i].p, s[j].p);
    if (d > 0.4 && d < r[i] + r[j] + 0.4) out.push([i, j, 1]);
  }
  return out;
}

// Bond orders for bonds by distance, from the hydrogens found and the bond lengths. A bond to a metal leaves an atom's
// valence as it was (it is dative). In turn: an N on three or more atoms, one of them an O on nothing else, is an N
// oxide or a nitro group's N (N+ and O−). An atom with more bonds than its valence (S, P, Cl) takes a double bond to a
// terminal O or S for each bond over, shortest first. Two atoms each with room for two more bonds, close, take a triple
// bond. Then atoms with room take double bonds, as many as fit, on the shortest bonds first (as Kekulé structures are
// made). An N with room only as N+ (pyridinium, amidinium), and in a structure with no hydrogens found an N on one atom
// (NH2), takes one only where the other atoms cannot all have one: caffeine's N-methyls and adenine's NH2 stay as they
// are. A bond longer than 0.96 of its single bond is never double, in case a hydrogen was not found. Last, an N or P
// with four bonds is N+ or P+, a halogen on nothing is a halide (Cl−), and in a structure with its hydrogens found, an
// O with one bond and no H is O−.
function orders(s: Site[], bonds: [number, number, number][]) {
  const metal = (i: number) => !NONMETAL.has(s[i].el), all = s.map(() => 0), on: [number, number, number][][] = s.map(() => []);
  for (const b of bonds) {
    all[b[0]]++; all[b[1]]++;
    if (!metal(b[0]) && !metal(b[1])) { on[b[0]].push(b); on[b[1]].push(b); }
  }
  const other = (b: number[], i: number) => (b[0] === i ? b[1] : b[0]), used = (i: number) => on[i].reduce((t, b) => t + b[2], 0);
  const room = (i: number) => hydrogens(s[i].el, s[i].charge, used(i)), lone = (i: number) => all[i] === 1;
  const ratio = (b: number[]) => dist(s[b[0]].p, s[b[1]].p) / (radius.get(s[b[0]].el)! + radius.get(s[b[1]].el)!);
  const short = bonds.filter((b) => on[b[0]].includes(b)).sort((p, q) => ratio(p) - ratio(q));
  s.forEach((x, i) => {
    const o = x.el === "N" && on[i].length >= 3 ? on[i].map((b) => other(b, i)).find((j) => s[j].el === "O" && lone(j)) : undefined;
    if (o !== undefined) { x.charge = 1; s[o].charge = -1; }
    let over = HYPER.has(x.el) ? on[i].length - hydrogens(x.el, 0, 0) : 0;
    for (const b of short) if (over > 0 && b.includes(i) && b[2] === 1 && /^(O|S|Se)$/.test(s[other(b, i)].el) && lone(other(b, i))) { b[2] = 2; over--; }
  });
  for (const b of short) if (b[2] === 1 && ratio(b) < 0.85 && room(b[0]) >= 2 && room(b[1]) >= 2) b[2] = 3;
  const found = s.some((x) => x.el === "H" || x.el === "D");
  const late = (i: number) => room(i) < 1 && s[i].el === "N" && !s[i].charge && used(i) === 3, can = (i: number) => room(i) >= 1 || late(i);
  const last = (i: number) => late(i) || (!found && s[i].el === "N" && on[i].length === 1);
  const edges = short.filter((b) => b[2] === 1 && ratio(b) < 0.96 && can(b[0]) && can(b[1]));
  // As many double bonds as fit on these edges, and how many atoms that are not last they take.
  const pairs = (e: typeof edges) => {
    const rank = (i: number) => (last(i) ? 2 : s[i].el === "C" ? 0 : 1), order = [...new Set(e.flatMap((b) => [b[0], b[1]]))].sort((p, q) => rank(p) - rank(q) || p - q);
    const taken = kekulise(e.map((b): [number, number] => [b[0], b[1]]), order).flatMap((yes, k) => (yes ? [e[k]] : []));
    return { taken, reach: taken.reduce((t, b) => t + Number(!last(b[0])) + Number(!last(b[1])), 0) };
  };
  const sure = edges.filter((b) => !last(b[0]) && !last(b[1])), first = pairs(sure), more = sure.length < edges.length ? pairs(edges) : first;
  for (const b of (more.reach > first.reach ? more : first).taken) b[2] = 2;
  s.forEach((x, i) => {
    if (x.charge) return;
    if ((x.el === "N" || x.el === "P") && used(i) === 4) x.charge = 1;
    else if ((found && x.el === "O" && lone(i) && used(i) === 1) || (/^(F|Cl|Br|I)$/.test(x.el) && !all[i])) x.charge = -1;
  });
}

// Positions (Å) turned to face the page: the widest spread across it (x), the next up it (y) and the least in depth
// (z), the principal axes by power iteration on the atoms' spread. z is x × y, so the structure keeps its hand.
function face(ps: V[]): V[] {
  const mid = [0, 1, 2].map((k) => ps.reduce((t, p) => t + p[k], 0) / ps.length), q = ps.map((p) => p.map((x, k) => x - mid[k]) as V);
  const spread = [0, 1, 2].map((a) => [0, 1, 2].map((b) => q.reduce((t, p) => t + p[a] * p[b], 0)) as V);
  const axes: V[] = [];
  for (let v of [[1, 0.5, 0.25], [0.25, 1, 0.5]] as V[]) {
    for (let k = 0; k < 100; k++) {
      let w = k ? (spread.map((row) => dotV(row, v)) as V) : v;
      for (const a of axes) { const d = dotV(w, a); w = w.map((x, j) => x - d * a[j]) as V; }
      const l = Math.hypot(...w);
      if (l < 1e-9) break;
      v = w.map((x) => x / l) as V;
    }
    axes.push(v);
  }
  const [x, y] = axes, z = crossV(x, y);
  return q.map((p) => [dotV(p, x), dotV(p, y), dotV(p, z)]);
}

// A CIF or mmCIF file as a drawing: its median bond between atoms other than H is one bond length (X-ray C–H bonds are
// short), and each structure is in a row from left to right, two bond lengths apart. Each atom keeps its name in the
// file as its atom number, not shown (Show Atom Number shows it). Throws a RangeError, with the reason to show, for a
// file over Octet's limits.
export function readCif(text: string): Mol {
  const groups = blocks(text).flatMap(groupsOf).filter((g) => g.sites.length);
  if (groups.some((g) => g.sites.length > MOST)) throw new RangeError(`It has a structure of more than ${MOST.toLocaleString("en-GB")} atoms.`);
  for (const g of groups) if (!g.bonds) { g.bonds = near(g.sites); orders(g.sites, g.bonds); }
  const heavy = (x: Site) => x.el !== "H" && x.el !== "D";
  const lengths = groups.flatMap((g) => g.bonds!.flatMap(([i, j]) => (heavy(g.sites[i]) && heavy(g.sites[j]) ? [dist(g.sites[i].p, g.sites[j].p)] : []))).sort((p, q) => p - q), unit = lengths[lengths.length >> 1] || 1.5;
  const mol: Mol = { atoms: [], bonds: [] };
  let left = 0;
  for (const g of groups) {
    const ps = face(g.sites.map((t) => t.p)).map((p) => p.map((x) => x / unit) as V), xs = ps.map((p) => p[0]), ys = ps.map((p) => p[1]);
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)], base = mol.atoms.length;
    g.sites.forEach((t, k) => mol.atoms.push({ label: t.el, location: [ps[k][0] - x0 + left, ps[k][1] - (y0 + y1) / 2, Math.abs(ps[k][2]) < 1e-6 ? 0 : ps[k][2]], shade: true, ...(t.charge ? { charge: t.charge } : {}), ...(NUMBER.test(t.name) ? { hiddenNumber: t.name } : {}) }));
    for (const [i, j, o] of g.bonds!) mol.bonds.push({ type: o, atoms: [base + i, base + j] });
    left += x1 - x0 + 2;
  }
  return mol;
}
