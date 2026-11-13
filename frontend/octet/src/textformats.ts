// Text forms of a drawing's molecules that Indigo does not write, for File > More Formats: ChemDraw's connection table
// (.ct, issue 105), written and read, and SLN, Sybyl Line Notation (issue 120), written. Written labels are expanded
// first, as ChemDraw expands them when it saves a connection table.
import { expandLabels } from "./chem.ts";
import { cipLabels } from "./cip.ts";
import { axialLabels } from "./axial.ts";
import { ELEMENTS } from "./labels.ts";
import { AROMATIC, HBOND, hydrogens, orderOf, type Mol } from "./render.ts";

// What neither format can hold: an atom that is no element (a generic group, a label Octet cannot read), or a bond that
// is not single, double, triple or aromatic (a quadruple or query bond). Hydrogen bonds are left out.
const unwritable = (mol: Mol) => mol.atoms.some((a) => !ELEMENTS.has(a.label)) || mol.bonds.some((b) => b.type !== HBOND && !(b.type >= 1 && b.type <= AROMATIC));

// A connection table: the title, the counts, a line for each atom (x, y and z, as a molfile has them, and its element),
// then one for each bond (its two atoms, its order, and ChemDraw's bond type, 0 for a plain bond). It keeps no
// charges, isotopes, radicals or wedges. Undefined when it cannot hold the drawing.
export function toCt(drawn: Mol, title = ""): string | undefined {
  const mol = expandLabels(drawn), bonds = mol.bonds.filter((b) => b.type !== HBOND);
  if (!mol.atoms.length || unwritable(mol)) return undefined;
  const xyz = (q: number[]) => [0, 1, 2].map((k) => ` ${(Math.round((q[k] ?? 0) * 1e4) / 1e4 || 0).toFixed(4).padStart(9)}`).join("");
  return [title.replace(/[\u0000-\u001f\u007f]/g, " ").slice(0, 80), ` ${mol.atoms.length} ${bonds.length}`,
    ...mol.atoms.map((a) => `${xyz(a.location)} ${a.label}`),
    ...bonds.map((b) => [b.atoms[0] + 1, b.atoms[1] + 1, b.type, 0].map((n) => String(n).padStart(3)).join(" ")), ""].join("\n");
}

// A connection table as KET, which Import reads as it reads any structure file (chem.ts importStructure). The text is
// hostile: at most 999 atoms and 999 bonds, each atom an element within 100,000 of the origin (as in a V2000
// molfile), each bond between two of its atoms with an order from 1 to 4 (4 aromatic). Each line is split into those
// fields only, so a long line costs nothing. The bond type column is not read. Throws otherwise.
export function fromCt(text: string): string {
  const bad = new Error("It is not a connection table.");
  const lines = text.split(/\r\n?|\n/, 2000), [na, nb] = (lines[1] ?? "").trim().split(/\s+/, 2).map(Number);
  if (!(Number.isInteger(na) && Number.isInteger(nb) && na >= 1 && na <= 999 && nb >= 0 && nb <= 999) || lines.length < 2 + na + nb) throw bad;
  const atoms = lines.slice(2, 2 + na).map((line) => {
    const [x, y, z, symbol = ""] = line.trim().split(/\s+/, 4), label = symbol.charAt(0).toUpperCase() + symbol.slice(1).toLowerCase(), at = [x, y, z].map(Number);
    if (!ELEMENTS.has(label) || !at.every((v) => Math.abs(v) < 1e5)) throw bad;
    return { label, location: at };
  });
  const bonds = lines.slice(2 + na, 2 + na + nb).map((line) => {
    const [i, j, order] = line.trim().split(/\s+/, 3).map(Number);
    if (![i, j].every((k) => Number.isInteger(k) && k >= 1 && k <= na) || i === j || ![1, 2, 3, 4].includes(order)) throw bad;
    return { type: order, atoms: [i - 1, j - 1] };
  });
  return JSON.stringify({ root: { nodes: [{ $ref: "mol0" }] }, mol0: { type: "molecule", atoms, bonds } });
}

// SLN: each atom with its hydrogens (CH3), single bonds left out, = # and : for double, triple and aromatic bonds,
// branches in brackets, a ring opened at an atom's number (C[1]) and closed by @1, and the structures apart with a full
// stop. An atom's attributes go in square brackets after it, after its ring number (C[1:+]): its charge (+, -2),
// isotope (I=13), radical (* for one unpaired electron, spin=t or spin=s for two) and R or S (s=R). A double bond's E or
// Z goes after it (=[s=E]).
// Undefined for what SLN cannot hold as Octet writes it: an atom or bond neither format holds, more than 1,000 atoms
// (where Octet works out no R or S), a pseudo-asymmetric centre (r or s), a stereo axis, or an and or or group.
export function toSln(drawn: Mol): string | undefined {
  const mol = expandLabels(drawn), n = mol.atoms.length;
  if (!n || n > 1000 || unwritable(mol)) return undefined;
  const cip = cipLabels(mol), axial = axialLabels(mol);
  if (cip.atoms.some((c, i) => c === "r" || c === "s" || (c && /^(&|or)/.test(mol.atoms[i].enhanced ?? ""))) || [...axial.atoms, ...axial.bonds].some(Boolean)) return undefined;
  const near: [number, number][][] = mol.atoms.map(() => []), used = mol.atoms.map(() => 0);
  mol.bonds.forEach((b, k) => {
    if (b.type === HBOND) return;
    near[b.atoms[0]].push([b.atoms[1], k]);
    near[b.atoms[1]].push([b.atoms[0], k]);
    for (const i of b.atoms) used[i] += orderOf(b.type);
  });
  // A hydrogen drawn as an atom goes into its atom's count where it is plain: no isotope, charge or radical, and one
  // single bond to an atom that is not a hydrogen.
  const isH = (i: number) => /^[HDT]$/.test(mol.atoms[i].label);
  const folded = mol.atoms.map((a, i) => a.label === "H" && !a.isotope && !a.charge && !a.radical && near[i].length === 1 && mol.bonds[near[i][0][1]].type === 1 && !isH(near[i][0][0]));
  const hs = mol.atoms.map((a, i) => (isH(i) ? 0 : a.implicitHCount ?? hydrogens(a.label, a.charge ?? 0, used[i], a.radical)) + near[i].filter(([j]) => folded[j]).length);
  // Depth first from each structure's first atom: the bonds walked make the chain and its branches; each other bond
  // closes a ring, back to an atom written earlier, which takes a number.
  const seen = mol.atoms.map(() => -1), walked = new Set<number>(), closes: [number, number][][] = mol.atoms.map(() => []), id = mol.atoms.map(() => 0);
  let order = 0, rings = 0;
  const walk = (i: number) => {
    seen[i] = order++;
    for (const [j, k] of near[i]) {
      if (folded[j] || walked.has(k)) continue;
      if (seen[j] < 0) { walked.add(k); walk(j); } else if (!closes[j].some(([kk]) => kk === k)) { id[j] ||= ++rings; closes[i].push([k, j]); }
    }
  };
  // A single bond is written out before an atom whose symbol starts with H, so CH-H[I=2] and C-Hg do not read as
  // hydrogens on the atom before.
  const symbol = (i: number) => (isH(i) ? "H" : mol.atoms[i].label);
  const bond = (k: number, j?: number) => {
    const b = mol.bonds[k];
    return (b.type === 1 ? (j !== undefined && symbol(j).startsWith("H") ? "-" : "") : ["", "", "=", "#", ":"][b.type]) + (cip.bonds[k] ? `[s=${cip.bonds[k]}]` : "");
  };
  const atom = (i: number) => {
    const a = mol.atoms[i], q = a.charge ?? 0, iso = a.isotope ?? (a.label === "D" ? 2 : a.label === "T" ? 3 : 0);
    const marks = [q ? `${q > 0 ? "+" : "-"}${Math.abs(q) > 1 ? Math.abs(q) : ""}` : "", iso ? `I=${iso}` : "", ["", "*", "spin=t", "spin=s"][a.radical ?? 0] ?? "", cip.atoms[i] ? `s=${cip.atoms[i]}` : ""].filter(Boolean).join(";");
    const inside = [id[i] ? String(id[i]) : "", marks].filter(Boolean).join(":");
    return `${symbol(i)}${inside && `[${inside}]`}${hs[i] ? `H${hs[i] > 1 ? hs[i] : ""}` : ""}`;
  };
  const write = (i: number): string => {
    const next = near[i].filter(([j, k]) => walked.has(k) && seen[j] > seen[i]);
    return atom(i) + closes[i].map(([k, j]) => `${bond(k)}@${id[j]}`).join("")
      + next.map(([j, k], m) => (m < next.length - 1 ? `(${bond(k, j)}${write(j)})` : `${bond(k, j)}${write(j)}`)).join("");
  };
  const starts: number[] = [];
  mol.atoms.forEach((_, i) => { if (!folded[i] && seen[i] < 0) { starts.push(i); walk(i); } });
  return starts.map(write).join(".");
}
