// The chemistry engine (Indigo) and the drawing style, shared by the editor and the dev gallery.
import Indigo from "indigo-ketcher/binaryWasmNoRender";
import { HBOND, hydrogens, NONMETAL, orderOf, QUADRUPLE, type Face, type Ink, type Mol } from "./render.ts";
import { fontStack } from "./docstyle.ts";
import { labelSmiles, writtenOxidation } from "./labels.ts";
import { bondedTo, fragments, insertMol, labelPlacer, levelTurn, pickAtoms, renumberCentre, subset } from "./edit.ts";
import { graphOf, type Graph } from "./naming.ts";
import { clean2d } from "./clean2d.ts";
import { counts } from "./mass.ts";
import { hasQuery, polymerBrackets, polymerLabel, repeatCount } from "./query.ts";
import { isQueryMolfile, readV3000, RXCTR, writeV3000 } from "./molv3.ts";
import { axialLabels } from "./axial.ts";
import { cipLabels } from "./cip.ts";
import type { StereoFacts } from "./check.ts";

type IndigoModule = Awaited<ReturnType<typeof Indigo>>;
let indigo: IndigoModule | undefined;
export const ready: Promise<void> = Indigo().then((m: IndigoModule) => { indigo = m; });

// Drawing sizes come from brand/tokens.css (ACS 1996).
const token = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name);
const pt = (name: string) => (parseFloat(token(name)) * 4) / 3; // pt to px
const BOND = pt("--bond-length");
export const STYLE = {
  bond: BOND,
  line: pt("--bond-width"),
  bold: pt("--bond-bold"),
  spacing: (parseFloat(token("--bond-spacing")) / 100) * BOND,
  hash: pt("--hash-spacing"),
  // ChemDraw's bonds clear the glyph outlines by 1.69 pt for a 1.6 pt margin (measured).
  margin: (pt("--margin-width") * 1.69) / 1.6,
  size: pt("--atom-label-size"),
};

// Text measured once and kept by its key. When a store holds `most`, the one used longest ago goes, so a long session
// with many different labels and captions does not fill the memory (issue 2).
function lastUsed<T>(store: Map<string, T>, most: number, key: string, make: () => T): T {
  const hit = store.get(key);
  if (hit !== undefined) { store.delete(key); store.set(key, hit); return hit; }
  const value = make();
  store.set(key, value);
  if (store.size > most) store.delete(store.keys().next().value!);
  return value;
}

// Glyph metrics and outlines. The outline is the edge pixels of the text drawn 8x larger, scaled back.
const FONT = token("--atom-label-font");
const SCALE = 8;
const inks = new Map<string, Ink>();
// Label metrics for a font and size (px), plain or bold or italic. Each text is measured once per font, size and face.
export const measurer = (font: string, size: number, bold = false, italic = false) => (text: string): Ink => {
  const face = `${italic ? "italic " : ""}${bold ? "bold " : ""}`;
  return lastUsed(inks, 2000, `${font}|${size}|${bold}|${italic}|${text}`, () => {
    const canvas = document.createElement("canvas");
    const g = canvas.getContext("2d", { willReadFrequently: true })!;
    g.font = `${face}${size}px ${font}`;
    const m = g.measureText(text);
    const pad = 2, baseline = size * 1.2;
    const w = (canvas.width = Math.ceil((m.width + 2 * pad) * SCALE)), h = (canvas.height = Math.ceil(size * 1.6 * SCALE));
    g.font = `${face}${size * SCALE}px ${font}`;
    g.fillText(text, pad * SCALE, baseline * SCALE);
    const alpha = g.getImageData(0, 0, w, h).data;
    const on = (x: number, y: number) => x >= 0 && y >= 0 && x < w && y < h && alpha[(y * w + x) * 4 + 3] > 127;
    const outline: [number, number][] = [];
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++)
        if (on(x, y) && !(on(x - 1, y) && on(x + 1, y) && on(x, y - 1) && on(x, y + 1)))
          outline.push([(x + 0.5) / SCALE - pad, (y + 0.5) / SCALE - baseline]);
    return { width: m.width, ascent: m.actualBoundingBoxAscent, outline };
  });
};
const plain = measurer(FONT, STYLE.size);
// A label's metrics in its own face (an atom's label can have its own font, bold and italic).
export const measure = (text: string, face?: Face): Ink =>
  face ? measurer(face.font ? fontStack(face.font) : FONT, STYLE.size, !!face.bold, !!face.italic)(text) : plain(text);

// A caption line's advance width in px, in the caption font. A width grows with the size (to within 0.04 px up to
// 40 px), so each text is measured once, at 100 px, for every size: a scale drag measures nothing again.
const CAPTION_FONT = token("--caption-font");
const widths = new Map<string, number>();
const meter = document.createElement("canvas").getContext("2d")!;
export function textWidth(text: string, size: number, bold?: boolean, italic?: boolean, family = CAPTION_FONT): number {
  const face = `${italic ? "italic " : ""}${bold ? "bold " : ""}`, key = `${face}${family}|${text}`;
  return lastUsed(widths, 10_000, key, () => { meter.font = `${face}100px ${family}`; return meter.measureText(text).width / 100; }) * size;
}
// How far a piece of caption text reaches above and below its baseline in px: its tallest character and its lowest
// descender, as drawn (Variable line spacing).
const extents = new Map<string, [number, number]>();
export function textExtent(text: string, size: number, bold?: boolean, italic?: boolean, family = CAPTION_FONT): [number, number] {
  const font = `${italic ? "italic " : ""}${bold ? "bold " : ""}${size}px ${family}`, key = `${font}|${text}`;
  return lastUsed(extents, 10_000, key, (): [number, number] => { meter.font = font; const m = meter.measureText(text); return [m.actualBoundingBoxAscent, m.actualBoundingBoxDescent]; });
}
export { CAPTION_FONT };

function engine() {
  if (!indigo) throw new Error("Indigo is not loaded yet");
  return indigo;
}

// A KET atom as Octet's: KET radicals 2 and 3 are one and two unpaired electrons. A map number and an enhanced
// stereo flag (abs, &n, orn) are kept.
type KetAtom = { label: string; location: [number, number, number]; charge?: number; radical?: number; isotope?: number; mapping?: number; stereoLabel?: string };
const atomOfKet = (a: KetAtom): Mol["atoms"][number] =>
  ({ label: a.label, location: a.location, charge: a.charge, ...(a.radical ? { radical: a.radical === 1 ? 3 : a.radical - 1 } : {}), ...(a.isotope ? { isotope: a.isotope } : {}),
    ...(Number.isInteger(a.mapping) && a.mapping! > 0 && a.mapping! <= 9999 ? { map: a.mapping } : {}),
    ...(/^(abs|&[1-9]\d?|or[1-9]\d?)$/.test(a.stereoLabel ?? "") ? { enhanced: a.stereoLabel } : {}) });

// Pasted, typed and imported text can stop the editor, as Indigo runs on the main thread: it reads very long text
// slowly, and its layout can tidy a crowded structure (a ring atom with five phenyls, a dense dendrimer) for minutes.
// So Octet reads at most 20,000 characters of SMILES and 300,000 of a file (a 1,000-atom KET file is 250,000), lays
// out at most 1,000 atoms, and caps the layout's rounds of tidying. 50 rounds is the fewest that lays out every real
// structure tried as no cap does (Pd(PPh3)4 needs 50). Each round costs more on a bigger structure, so the cap falls
// to 10 rounds at 400 atoms (a 100-residue peptide needs 10). The slowest structure tried takes half a second, and a
// 300,000-character file that is not chemistry takes under a second to refuse (src/layout.check.ts).
const MOST_CHARACTERS = 300_000, MOST_SMILES = 20_000, MOST_ATOMS = 1000;
// The reason to show for text over a limit.
const over = (most: number, what: string) => new RangeError(`It has more than ${most.toLocaleString("en-GB")} ${what}.`);
// Atoms in a SMILES (bracket atoms and the organic subset), up to the first space (CXSMILES and names come after it).
const smilesAtoms = (smiles: string) => smiles.split(/\s/)[0].match(/\[[^\]]*\]|Br|Cl|[BCNOPSFIbcnops*]/g)?.length ?? 0;

// A structure file (MOL, SDF, RXN, RDF, CDXML, KET, SMILES), keeping the file's own drawing where it has one.
// Coordinates are scaled so the median bond is one bond length; SMILES (no drawing) is laid out. A reaction keeps its
// arrows and plus signs; an RD file's reactions stand one under another.
// Throws a RangeError, with the reason to show, for text over Octet's limits.
// An MDL file (MOL, SDF, RXN, RDF) whose only enhanced stereochemistry is its chiral flag: no V3000 stereo collections.
// Indigo reads the flag as abs (1) or &1 (0) on every stereocentre.
export const chiralFlagOnly = (text: string) => /V2000|V3000/.test(text) && !/MDLV30\/STE(ABS|RAC|REL)/.test(text);
export function importStructure(text: string): Mol {
  if (text.length > MOST_CHARACTERS) throw over(MOST_CHARACTERS, "characters");
  const ind = engine(), opts = new ind.MapStringString();
  try {
    opts.set("output-content-type", "application/json");
    opts.set("dearomatize-on-load", "true");
    const hasDrawing = /V2000|V3000|<CDXML|"root"|<cml[\s>]/i.test(text);
    if (!hasDrawing) return parseStructure(text);
    if (/^\s*\$RDFILE/.test(text)) return readRdf(text);
    // A query or Markush molfile: read by Octet, so its query data is kept (molv3.ts). A V2000 one (R-groups, atom
    // lists, substitution counts, S-groups) is made V3000 by Indigo first.
    const reaction = /^\s*\$RXN/.test(text);
    const v2000 = !reaction && /V2000/.test(text) && /^M {2}(RGP|ALS|SUB|UNS|RBC|LIN|STY|LOG)|^\$RGP|^(?:.{31})(R#|L |A |Q )|^.{6}  [5-8] /m.test(text);
    const v3000 = v2000 ? (() => { try { return convert(text, "molfile", { "molfile-saving-mode": "3000" }); } catch { return ""; } })() : text;
    if (!reaction && isQueryMolfile(v3000)) {
      const mol = readV3000(v3000);
      const lengths = mol.bonds.map((b) => Math.hypot(mol.atoms[b.atoms[1]].location[0] - mol.atoms[b.atoms[0]].location[0], mol.atoms[b.atoms[1]].location[1] - mol.atoms[b.atoms[0]].location[1])).sort((a, b) => a - b);
      const k = 1 / (lengths[Math.floor(lengths.length / 2)] || 1), at = (q: [number, number]): [number, number] => [q[0] * k, q[1] * k];
      return { ...mol, atoms: mol.atoms.map((a) => ({ ...a, location: [a.location[0] * k, a.location[1] * k, (a.location[2] ?? 0) * k] })), ...(mol.shapes ? { shapes: mol.shapes.map((sh) => ({ ...sh, from: at(sh.from), to: at(sh.to) })) } : {}) };
    }
    return scaled(fromKet(JSON.parse(JSON.parse(ind.convert(text, "ket", opts)).struct), /^\$\$\$\$/m.test(text)));
  } finally {
    opts.delete();
  }
}
// A drawing with its median bond one bond length long.
function scaled(mol: Mol): Mol {
  const lengths = mol.bonds.map((b) => Math.hypot(mol.atoms[b.atoms[1]].location[0] - mol.atoms[b.atoms[0]].location[0], mol.atoms[b.atoms[1]].location[1] - mol.atoms[b.atoms[0]].location[1])).sort((a, b) => a - b);
  const k = 1 / (lengths[Math.floor(lengths.length / 2)] || 1), at = (q: [number, number]): [number, number] => [q[0] * k, q[1] * k];
  return {
    ...mol, atoms: mol.atoms.map((a) => ({ ...a, location: [a.location[0] * k, a.location[1] * k, (a.location[2] ?? 0) * k] })),
    ...(mol.arrows ? { arrows: mol.arrows.map((a) => ({ ...a, from: at(a.from), to: at(a.to) })) } : {}),
    // A plus sign's point is its middle; its caption's point is its baseline, a quarter of a bond length lower.
    ...(mol.captions ? { captions: mol.captions.map((c) => ({ ...c, x: c.x * k, y: c.y * k - 0.25 })) } : {}),
  };
}
// Indigo's KET as a drawing: its molecules, with their map numbers and enhanced stereo, and a reaction's arrows and
// plus signs (Octet's reaction arrows and "+" captions). apart: the molecules are an SD file's records, which other
// programs often draw at one place; when two overlap, they are set in a row.
function fromKet(ket: Record<string, unknown> & { root: { nodes: Record<string, unknown>[] } }, apart = false): Mol {
  const mol: Mol = { atoms: [], bonds: [] }, arrows: NonNullable<Mol["arrows"]> = [], captions: NonNullable<Mol["captions"]> = [];
  let id = 1;
  for (const node of ket.root.nodes) {
    const frag = typeof node.$ref === "string" ? ket[node.$ref] as { type?: string; atoms: KetAtom[]; bonds: Mol["bonds"] } : undefined;
    if (frag?.type === "molecule") {
      const base = mol.atoms.length;
      mol.atoms.push(...frag.atoms.map(atomOfKet));
      // A bond's reacting centre (KET "center", the MDL code) is its Rxn mark.
      const rxnOf = (b: { center?: number }) => Object.keys(RXCTR).find((k) => RXCTR[k] === b.center) as Mol["bonds"][number]["rxn"];
      mol.bonds.push(...frag.bonds.map((b) => { const rxn = rxnOf(b as { center?: number }); return { type: b.type, atoms: [b.atoms[0] + base, b.atoms[1] + base] as [number, number], stereo: b.stereo, ...(rxn ? { rxn } : {}) }; }));
    } else if (node.type === "plus" && Array.isArray(node.location)) {
      const [x, y] = (node.location as number[]).map(Number);
      if (Number.isFinite(x) && Number.isFinite(y)) captions.push({ id: id++, text: "+", x, y, align: "centre" });
    } else if (node.type === "arrow") {
      const d = node.data as { mode?: string; pos?: { x: number; y: number }[] } | undefined, [p, q] = d?.pos ?? [];
      if (!p || !q || ![p.x, p.y, q.x, q.y].every(Number.isFinite)) continue;
      const mode = String(d?.mode ?? "");
      const kind = /equilibrium/.test(mode) ? "equilibrium" : /retrosynthetic/.test(mode) ? "retro" : /failed/.test(mode) ? "nogo" : /both-ends/.test(mode) ? "resonance" : "reaction";
      arrows.push({ id: id++, kind, from: [p.x, p.y], to: [q.x, q.y], ...(/dashed/.test(mode) ? { style: "dashed" as const } : {}) });
    }
  }
  if (apart) {
    const groups = fragments(mol), box = (g: number[]) => [0, 1].flatMap((k) => [Math.min(...g.map((i) => mol.atoms[i].location[k])), Math.max(...g.map((i) => mol.atoms[i].location[k]))]);
    const boxes = groups.map(box), touch = (p: number[], q: number[]) => p[0] <= q[1] && q[0] <= p[1] && p[2] <= q[3] && q[2] <= p[3];
    if (boxes.some((p, k) => boxes.slice(k + 1).some((q) => touch(p, q)))) {
      const lengths = mol.bonds.map((b) => Math.hypot(...[0, 1].map((k) => mol.atoms[b.atoms[1]].location[k] - mol.atoms[b.atoms[0]].location[k]))).sort((x, y) => x - y);
      const gap = 2 * (lengths[Math.floor(lengths.length / 2)] || 1);
      let x = 0;
      groups.forEach((g, k) => {
        const [x0, x1, y0, y1] = boxes[k], dx = x - x0, dy = -(y0 + y1) / 2;
        for (const i of g) mol.atoms[i] = { ...mol.atoms[i], location: [mol.atoms[i].location[0] + dx, mol.atoms[i].location[1] + dy, mol.atoms[i].location[2]] };
        x += x1 - x0 + gap;
      });
    }
  }
  return { ...mol, ...(arrows.length ? { arrows } : {}), ...(captions.length ? { captions } : {}) };
}
// An RD file: each reaction (and molecule) record read on its own, one under another, so no two overlap.
function readRdf(text: string): Mol {
  const records = text.replace(/\r\n?/g, "\n").split(/^\$[RM]FMT[^\n]*\n/m).slice(1).slice(0, 200)
    .map((r) => r.replace(/^\$(RIREG|REREG|MIREG|MEREG)[^\n]*\n/, "").split(/^\$DTYPE/m)[0].trimEnd()).filter((r) => r.trim());
  if (!records.length) throw new Error("This RD file has no reactions.");
  let out: Mol = { atoms: [], bonds: [] }, top = 0;
  for (const r of records) {
    const part = importStructure(r.startsWith("$RXN") ? r : `${r}\n`), ys = [...part.atoms.map((a) => a.location[1]), ...(part.arrows ?? []).flatMap((a) => [a.from[1], a.to[1]])];
    if (!ys.length) continue;
    const dy = top - Math.max(...ys);
    out = insertMol(out, part, [0, dy]).mol;
    top += Math.min(...ys) - Math.max(...ys) - 3;
  }
  return out;
}

// SMILES (or a MOL file) to a laid-out molecule with Kekulé bonds and stereo wedges. All fragments are kept.
// Throws a RangeError, with the reason to show, for text over Octet's limits. tidy false: Indigo's layout only, for
// a structure that is read and not drawn (its InChI).
export function parseStructure(text: string, tidy = true): Mol {
  // SMILES is one line, counted as written (Indigo reads a long SMILES slowly); a MOL file or other file, through Indigo.
  const file = /^[{<]|[\r\n]/.test(text.trim()), most = file ? MOST_CHARACTERS : MOST_SMILES;
  if (text.length > most) throw over(most, "characters");
  // An RD file (pasted as text) is read record by record, as Import reads it: Indigo reads only one of its reactions.
  if (/^\s*\$RDFILE/.test(text)) return readRdf(text);
  const atoms = smilesAtoms(file ? convert(text, "smiles") : text);
  if (atoms > MOST_ATOMS) throw over(MOST_ATOMS, "atoms");
  // SMILES sets each stereocentre absolutely, and Indigo flags each one abs. Like a structure drawn by hand, it then
  // shows no flags, as in ChemDraw. Flags stay where the SMILES also sets and or or groups (CXSMILES).
  const lay = (smart: boolean) => {
    const m = indigoLayout(text, atoms, smart);
    return file || m.atoms.some((a) => /^(&|or)/.test(a.enhanced ?? "")) ? m : { ...m, atoms: m.atoms.map((a) => (a.enhanced ? (({ enhanced: _, ...rest }) => rest)(a) : a)) };
  };
  let out = lay(false);
  if (tidy && !out.arrows && out.atoms.length <= MOST_TIDIED) out = tidied(out, () => lay(true), text);
  return out.captions ? { ...out, captions: out.captions.map((c) => ({ ...c, y: c.y - 0.25 })) } : out;
}
// Indigo's own layout of a SMILES or file of so many atoms, its rounds of tidying capped for the size (MOST_ATOMS
// above). smart: with Indigo's ring templates. A reaction (reactants>agents>products) keeps its arrow and plus signs.
export function indigoLayout(text: string, atoms = smilesAtoms(text), smart = false): Mol {
  const ind = engine(), opts = new ind.MapStringString();
  try {
    opts.set("output-content-type", "application/json");
    opts.set("dearomatize-on-load", "true");
    opts.set("layout-max-iterations", String(Math.min(50, Math.max(10, Math.round(4000 / atoms)))));
    if (smart) opts.set("smart-layout", "true");
    return fromKet(JSON.parse(JSON.parse(ind.layout(text, "ket", opts)).struct));
  } finally {
    opts.delete();
  }
}

// Indigo's layout of a cage or bridged ring system (taxol, morphine, adamantane) can put an atom on a bond or two atoms
// on top of each other. Such a layout is laid out again with Indigo's ring templates, and each is cleaned up. The
// drawings are tried from the fewest atoms on bonds or on each other, then the fewest crossing bonds: the wedges go
// where ChemDraw puts them (placeWedges), and the first drawing that still reads as the same stereoisomer as the text
// (same standard InChI) is kept. If none does, Indigo's own is.
const MOST_TIDIED = 100;
function tidied(first: Mol, smart: () => Mol, text: string): Mol {
  const wedged = first.bonds.some((b) => b.stereo === 1 || b.stereo === 6), crowd = crowded(first, 0.15, 0.35);
  if (!crowd && !wedged) return first;
  // A metal complex drawn by Octet can read differently from its SMILES (Indigo reads Pd(PPh3)4's SMILES with
  // charges on the metal), so a drawing that reads as Indigo's own drawing does is kept too.
  const refs = new Set([toInchi(text), toInchi(first)]);
  refs.delete(undefined);
  if (!refs.size) return first;
  const tries = [{ m: first, from: first, rank: [crowded(first, 0.3, 0.5), crossings(first)] }];
  if (crowd) {
    let other: Mol | undefined;
    const clean = (m: Mol) => cleanUp(m, undefined, 500), at = bondedTo(first);
    // Indigo's templates are for ring systems: only a structure with an atom in three rings tries them.
    const fused = at.some((n, i) => n.filter((j) => inRing(at, i, j)).length >= 3);
    for (const make of [() => [clean(first), first], ...(fused ? [() => [other = smart(), other], () => [clean(other!), other!]] : [])]) {
      let m: Mol, from: Mol;
      // Indigo's templates fail on some structures ("refinement: too small edge").
      try { [m, from] = make(); } catch { continue; }
      tries.push({ m, from, rank: [crowded(m, 0.3, 0.5), crossings(m)] });
      if (!tries[tries.length - 1].rank.some(Boolean)) break;
    }
    tries.sort((p, q) => p.rank[0] - q.rank[0] || p.rank[1] - q.rank[1]);
  }
  for (const { m, from } of tries) {
    const out = wedged ? placeWedges(m, wedgeHands(from)) : m;
    if (refs.has(toInchi(out))) return out;
  }
  return first;
}
// How many atoms lie within near of a bond they are not part of, or within close of another atom, plus the atoms
// between two single bonds in a straight line (the structure check's warnings: an atom drawn so it cannot be seen).
function crowded(m: Mol, near: number, close: number): number {
  const xy = m.atoms.map((a) => a.location), bonded = bondedTo(m);
  let n = 0;
  xy.forEach((p, i) => {
    if (m.bonds.some((b) => {
      if (b.atoms.includes(i)) return false;
      const [s, t] = [xy[b.atoms[0]], xy[b.atoms[1]]], dx = t[0] - s[0], dy = t[1] - s[1];
      const f = Math.max(0, Math.min(1, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / (dx * dx + dy * dy || 1)));
      return Math.hypot(s[0] + f * dx - p[0], s[1] + f * dy - p[1]) < near;
    })) n++;
    for (let j = i + 1; j < xy.length; j++) if (Math.hypot(xy[j][0] - p[0], xy[j][1] - p[1]) < close) n++;
    const [q, r] = bonded[i];
    if (bonded[i].length === 2 && m.bonds.every((b) => !b.atoms.includes(i) || b.type === 1)) {
      const u = [xy[q][0] - p[0], xy[q][1] - p[1]], v = [xy[r][0] - p[0], xy[r][1] - p[1]];
      if ((u[0] * v[0] + u[1] * v[1]) / (Math.hypot(u[0], u[1]) * Math.hypot(v[0], v[1]) || 1) < Math.cos((175 * Math.PI) / 180)) n++;
    }
  });
  return n;
}
// Pairs of bonds that cross (and share no atom).
function crossings(m: Mol): number {
  const xy = m.atoms.map((a) => a.location), side = (p: number[], q: number[], r: number[]) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
  let n = 0;
  m.bonds.forEach((b, k) => {
    const [p, q] = [xy[b.atoms[0]], xy[b.atoms[1]]];
    for (const c of m.bonds.slice(k + 1)) {
      if (c.atoms.some((i) => b.atoms.includes(i))) continue;
      const [r, s] = [xy[c.atoms[0]], xy[c.atoms[1]]];
      if (side(p, q, r) * side(p, q, s) < 0 && side(r, s, p) * side(r, s, q) < 0) n++;
    }
  });
  return n;
}

// Is the bond from i to j in a ring (its ends joined without it)? at: each atom's neighbours.
function inRing(at: number[][], i: number, j: number): boolean {
  const next = at[i].filter((k) => k !== j), seen = new Set([i, ...next]);
  while (next.length) {
    const k = next.pop()!;
    if (k === j) return true;
    for (const l of at[k]) if (!seen.has(l)) { seen.add(l); next.push(l); }
  }
  return false;
}
// The handedness a drawing gives a tetrahedral centre: the signed volume its neighbours make, in atom order (with the
// centre itself in place of an implicit H, which lies on the same side of the other three), each raised by z: a
// bond length towards the viewer at a wedge's wide end, away at a hash's. Near 0 when the drawing does not set it.
function handed(m: Mol, c: number, around: number[], z: (j: number) => number): number {
  const [a, b, d, e] = (around.length === 3 ? [...around, c] : around).map((j) => [m.atoms[j].location[0], m.atoms[j].location[1], j === c ? 0 : z(j)]);
  const [u, v, w] = [b, d, e].map((p) => [p[0] - a[0], p[1] - a[1], p[2] - a[2]]);
  return u[0] * (v[1] * w[2] - v[2] * w[1]) - u[1] * (v[0] * w[2] - v[2] * w[0]) + u[2] * (v[0] * w[1] - v[1] * w[0]);
}
// A centre whose wedges placeWedges may move: single bonds to three or four atoms, and a wedge or hash that starts at it.
const tetrahedral = (c: number, bonds: Mol["bonds"]) => bonds.length >= 3 && bonds.length <= 4 && bonds.every((b) => b.type === 1) && bonds.some((b) => b.atoms[0] === c && (b.stereo === 1 || b.stereo === 6));
// Each such centre's handedness as its wedges and hashes draw it (1 or -1), by atom.
function wedgeHands(m: Mol): Map<number, number> {
  const out = new Map<number, number>(), at = bondedTo(m);
  m.atoms.forEach((_, c) => {
    const bonds = m.bonds.filter((b) => b.atoms.includes(c));
    if (!tetrahedral(c, bonds)) return;
    const z = (j: number) => { const b = bonds.find((x) => x.atoms[0] === c && x.atoms[1] === j); return b?.stereo === 1 ? 1 : b?.stereo === 6 ? -1 : 0; };
    const h = handed(m, c, [...at[c]].sort((p, q) => p - q), z);
    if (Math.abs(h) > 1e-6) out.set(c, Math.sign(h));
  });
  return out;
}
// Room for a new atom at q bonded to c: no atom within half a bond of it (a labelled atom, 0.7 of a bond), no bond
// within 0.4 of a bond of it (its H label would sit on the bond), and its bond near no other atom and across no bond.
function roomy(atoms: Mol["atoms"], bonds: Mol["bonds"], c: number, q: number[]): boolean {
  const p = atoms[c].location, side = (a: number[], b: number[], r: number[]) => (b[0] - a[0]) * (r[1] - a[1]) - (b[1] - a[1]) * (r[0] - a[0]);
  // The distance from r to the segment from a to b.
  const gap = (r: number[], a = p, b = q) => { const dx = b[0] - a[0], dy = b[1] - a[1], f = Math.max(0, Math.min(1, ((r[0] - a[0]) * dx + (r[1] - a[1]) * dy) / (dx * dx + dy * dy || 1))); return Math.hypot(a[0] + f * dx - r[0], a[1] + f * dy - r[1]); };
  return atoms.every((a, i) => i === c || (Math.hypot(a.location[0] - q[0], a.location[1] - q[1]) >= (a.label === "C" && !a.text ? 0.5 : 0.7) && gap(a.location) >= 0.3))
    && bonds.every((b) => { const [r, s] = b.atoms.map((i) => atoms[i].location); return b.atoms.includes(c) || (gap(q, r, s) >= 0.4 && !(side(p, q, r) * side(p, q, s) < 0 && side(r, s, p) * side(r, s, q) < 0)); });
}
// One wedge or hash for each centre, where ChemDraw puts it: on a bond out of the rings to an atom that is not a
// stereocentre, else on an H drawn on the centre (the centre's own), else on a ring bond to an atom that is not a
// stereocentre. Only where there is no other choice does it join two stereocentres, which does not show which one it
// sets. Its narrow end is always at the centre, and it draws the hand the centre had (hands, by atom).
function placeWedges(m: Mol, hands: Map<number, number>): Mol {
  if (!hands.size) return m;
  const atoms = [...m.atoms], at = bondedTo(m), stereo = new Set([...hands.keys(), ...stereoFacts(m).centres]);
  const own = (b: Mol["bonds"][number]) => hands.has(b.atoms[0]) && (b.stereo === 1 || b.stereo === 6);
  const bonds = m.bonds.map((b) => (own(b) ? { ...b, stereo: undefined } : b));
  const taken = new Set(bonds.filter((b) => b.stereo).flatMap((b) => [b.atoms.join(), [...b.atoms].reverse().join()]));
  const ring = (i: number, j: number) => inRing(at, i, j);
  const xy = (i: number) => atoms[i].location;
  // The centres bonded only to other centres choose first, as they have the fewest choices.
  const free = (c: number) => at[c].filter((j) => !stereo.has(j)).length;
  for (const [c, hand] of [...hands].sort((p, q) => free(p[0]) - free(q[0]) || p[0] - q[0])) {
    const around = [...at[c]].sort((p, q) => p - q), kept = m.bonds.filter((b) => b.atoms[0] === c && own(b));
    // Indigo's own wedge stays where it is one ChemDraw would draw.
    if (kept.length === 1 && !stereo.has(kept[0].atoms[1]) && !ring(c, kept[0].atoms[1])) { bonds[m.bonds.indexOf(kept[0])] = kept[0]; continue; }
    const options = around.filter((j) => !taken.has(`${c},${j}`)).map((j) => ({ j, rank: stereo.has(j) ? 3 : ring(c, j) ? 2 : 0, ends: at[j].length }));
    // The H goes out into the widest gap between the centre's bonds that has room for it (no atom near it, and its bond
    // near no atom and across no bond), shorter where it needs to be. With no room, there is no H.
    let h: [number, number, number] | undefined;
    if (around.length === 3) {
      const turns = around.map((j) => Math.atan2(xy(j)[1] - xy(c)[1], xy(j)[0] - xy(c)[0])).sort((p, q) => p - q);
      const ways = turns.map((t, k) => [(k < 2 ? turns[k + 1] : turns[0] + 2 * Math.PI) - t, t]).sort((p, q) => q[0] - p[0]);
      h = ways.flatMap(([gap, t]) => [0.8, 0.6].map((r): [number, number, number] => [xy(c)[0] + r * Math.cos(t + gap / 2), xy(c)[1] + r * Math.sin(t + gap / 2), 0])).find((q) => roomy(atoms, bonds, c, q));
      if (h) options.push({ j: atoms.length, rank: 1, ends: 1 });
    }
    options.sort((p, q) => p.rank - q.rank || p.ends - q.ends);
    const set = options.some(({ j }) => {
      const added = j === atoms.length;
      if (added) atoms.push({ label: "H", location: h! });
      const v = handed({ ...m, atoms }, c, added ? [...around, j] : around, (k) => (k === j ? 1 : 0));
      if (Math.abs(v) < 0.1) { if (added) atoms.pop(); return false; }
      if (added) bonds.push({ type: 1, atoms: [c, j] });
      const k = added ? bonds.length - 1 : bonds.findIndex((b) => b.atoms.includes(c) && b.atoms.includes(j));
      bonds[k] = { ...bonds[k], atoms: [c, j], stereo: Math.sign(v) === hand ? 1 : 6 };
      taken.add(`${c},${j}`).add(`${j},${c}`);
      return true;
    });
    // No bond sets the centre clearly: Indigo's wedges stay.
    if (!set) for (const b of kept) bonds[m.bonds.indexOf(b)] = b;
  }
  return { ...m, atoms, bonds };
}

// Each label's group as Indigo reads it, kept by the label's text, so each label is read once. Not kept while Indigo
// is loading. Cleared when it grows large.
const labelGroups = new Map<string, Mol | undefined>();
function labelGroup(text: string): Mol | undefined {
  if (labelGroups.has(text)) return labelGroups.get(text);
  let frag: Mol | undefined;
  try { const smiles = labelSmiles(text); frag = smiles ? parseStructure(smiles) : undefined; } catch { frag = undefined; }
  if (!indigo) return frag;
  if (labelGroups.size >= 1000) labelGroups.clear();
  labelGroups.set(text, frag);
  return frag;
}
// Written labels (OMe, CO2Et, Ph) as real atoms, for chemistry. Each label's group is read by Indigo and joined
// where the label atom was. A label Octet cannot read (or Indigo cannot) stays as a pseudo-atom ("*"), so no label
// text can stop the drawing's chemistry.
export const expandLabels = (mol: Mol): Mol => expandWithOrigins(mol).mol;
// The same, with the drawn atom each expanded atom came from (a label's atoms all come from the label).
export function expandWithOrigins(mol: Mol): { mol: Mol; from: number[] } {
  let out: Mol = { atoms: mol.atoms.map((a) => ({ ...a })), bonds: mol.bonds.map((b) => ({ ...b })) };
  const origin = mol.atoms.map((_, i) => i), replaced = new Map<number, number>();
  // A multi-centre attachment (an η bond) is left out of the chemistry, with its bonds. A variable attachment's
  // substituent is joined to the first of its atoms: every positional isomer has the same formula.
  mol.atoms.forEach((a, i) => {
    if (!a.centre) return;
    const to = a.centre.variable ? a.centre.atoms.find((j) => mol.atoms[j] && !mol.atoms[j].centre) : undefined;
    out.bonds = out.bonds.flatMap((b) => (!b.atoms.includes(i) ? [b] : to === undefined ? [] : [{ ...b, atoms: b.atoms.map((k) => (k === i ? to : k)) as [number, number] }]));
    out.atoms[i] = { ...out.atoms[i], label: "*", text: undefined, centre: undefined, removed: true } as Mol["atoms"][number];
  });
  mol.atoms.forEach((a, i) => {
    // A multi-centre point (an η ligand's) is not an atom: it and its bond are left out.
    if (a.centre) { out.atoms[i] = { ...out.atoms[i], removed: true } as Mol["atoms"][number]; return; }
    // An attachment point (wavy, diamond or star) or a polymer bead is not an atom either, but its bond takes up its
    // neighbour's valence: it is a pseudo-atom ("*"), which counts in no formula, mass or analysis.
    if (a.attach || a.bead) { out.atoms[i] = { ...out.atoms[i], label: "*", text: undefined, isotope: undefined, charge: undefined }; return; }
    if (!a.text) return;
    const frag = a.chemical === false ? undefined : labelGroup(a.text);
    if (!frag?.atoms.length) { out.atoms[i] = { ...out.atoms[i], label: "*", text: undefined }; return; }
    const base = out.atoms.length, place = labelPlacer(mol, i, frag);
    replaced.set(i, base);
    origin.push(...frag.atoms.map(() => i));
    // The group's first atom takes the label atom's place: bonds to the label atom move to it, and the group points
    // away from the rest as Expand Label draws it, so a wedge beside a label reads right. The kept group's atoms are
    // copied, so no change to the result can change it.
    out = {
      atoms: [...out.atoms, ...frag.atoms.map((x) => ({ ...x, location: place(x.location) }))],
      bonds: [
        ...out.bonds.map((b) => ({ ...b, atoms: b.atoms.map((k) => (k === i ? base : k)) as [number, number] })),
        ...frag.bonds.map((b) => ({ ...b, atoms: [b.atoms[0] + base, b.atoms[1] + base] as [number, number] })),
      ],
    };
    out.atoms[base] = { ...out.atoms[base], charge: (out.atoms[base].charge ?? 0) + (a.charge ?? 0) || undefined };
    // A label of one element and its hydrogens (NH3, H2O) bonded to a metal keeps the hydrogens it shows: counted by
    // valence, the bond to the metal would leave NH2 and OH, where the drawing shows ammine and aqua ligands.
    const hx = /^(?:([A-Z][a-z]?)H(\d*)|H(\d*)([A-Z][a-z]?))$/.exec(a.text);
    if (hx && frag.atoms.length === 1 && frag.atoms[0].label === (hx[1] ?? hx[4]) && mol.bonds.some((b) => b.atoms.includes(i) && !NONMETAL.has(mol.atoms[b.atoms[0] === i ? b.atoms[1] : b.atoms[0]].label)))
      out.atoms[base] = { ...out.atoms[base], implicitHCount: Number((hx[2] ?? hx[3]) || 1) };
    // A label with an oxidation state, Os(II), is the element; the state goes with the atom for its name.
    const ox = writtenOxidation(a.text);
    if (ox && frag.atoms.length === 1) out.atoms[base] = { ...out.atoms[base], ox: ox.ox };
    out.atoms[i] = { ...out.atoms[i], label: "*", text: undefined, removed: true } as Mol["atoms"][number];
  });
  // Drop the label atoms that were replaced, renumbering bonds (and a kept stereo configuration's neighbours: a label's
  // is its group's first atom).
  const keep = out.atoms.map((a) => !(a as { removed?: boolean }).removed), map: number[] = [];
  let next = 0;
  out.atoms.forEach((_, k) => { if (keep[k]) map[k] = next++; });
  const to = (j: number) => map[replaced.get(j) ?? j];
  return {
    mol: { atoms: out.atoms.filter((_, k) => keep[k]).map((a) => (a.kept ? renumberCentre(a, to) : a)), bonds: out.bonds.filter((b) => keep[b.atoms[0]] && keep[b.atoms[1]]).map((b) => ({ ...b, atoms: [map[b.atoms[0]], map[b.atoms[1]]] as [number, number] })) },
    from: origin.filter((_, k) => keep[k]),
  };
}

// The drawing as SMILES. Throws if Indigo can't read it (for example, a valence it rejects).
// A drawing as KET, with labels expanded into atoms. KET has no bond display styles (bold, wavy and so on).
// Hydrogen bonds are left out (they are not chemistry Indigo works out), unless hbonds asks for them; a quadruple
// bond, which Indigo has no type for, goes as a single bond. Without wedges (wedges false), Indigo also reads a
// drawing whose wedges it rejects: formulas and masses do not need them. keep: each atom's map number and enhanced
// stereo flag, and each bond's Rxn mark, go too, for MDL and reaction files. mol: the molecule with its labels
// expanded already.
type KetOptions = { wedges?: boolean; keep?: boolean; hbonds?: boolean; mol?: Mol };
function ketOf(drawn: Mol, { wedges = true, keep = false, hbonds = false, mol }: KetOptions = {}): string {
  const expanded = mol ?? expandLabels(hbonds || !drawn.bonds.some((b) => b.type === HBOND) ? drawn : { ...drawn, bonds: drawn.bonds.filter((b) => b.type !== HBOND) });
  return JSON.stringify({ root: { nodes: [{ $ref: "mol0" }] }, mol0: ketMol(expanded, wedges, keep) });
}
function ketMol(mol: Mol, wedges: boolean, keep: boolean) {
  const bonds = mol.bonds.map(({ type, atoms, stereo, rxn }) => ({ type: type === QUADRUPLE ? 1 : type, atoms, ...(stereo && wedges ? { stereo } : {}), ...(keep && rxn && RXCTR[rxn] !== undefined ? { center: RXCTR[rxn] } : {}) }));
  // An atom bonded to a metal keeps the hydrogens Octet draws on it (as render.ts counts them): Indigo would count the P
  // of a PPh3 bonded to Pd as PH (valence 5), where the drawing shows P. It goes to Indigo as the atom's valence: as a
  // hydrogen count, a drawing with an R group (a query) would write it into a molfile as a query feature.
  const used = mol.atoms.map(() => 0), metalled = mol.atoms.map(() => false);
  for (const b of mol.bonds) for (const [i, j] of [b.atoms, [b.atoms[1], b.atoms[0]]]) { used[i] += orderOf(b.type); if (b.type !== HBOND && !NONMETAL.has(mol.atoms[j].label)) metalled[i] = true; }
  const valence = (i: number, a: Mol["atoms"][number]) => Math.round(used[i]) + (a.implicitHCount ?? hydrogens(a.label, a.charge ?? 0, used[i], a.radical === 3 ? 2 : a.radical));
  // KET radicals: 1 a singlet, 2 one unpaired electron (doublet), 3 two (triplet). KET's stereo labels are Octet's
  // flags ("abs", "&1", "or1"). An atom with its hydrogens set (a caption read as an element, edit.ts withCaptionAtoms)
  // goes with its valence too, so Bi stays Bi and is not BiH3.
  const atoms = mol.atoms.map((a, i) => ({ label: a.label, location: a.location, ...(a.charge ? { charge: a.charge } : {}), ...(a.radical ? { radical: a.radical === 3 ? 1 : a.radical + 1 } : {}), ...(a.isotope ? { isotope: a.isotope } : {}),
    ...((metalled[i] && NONMETAL.has(a.label)) || a.implicitHCount !== undefined ? { explicitValence: valence(i, a) } : {}),
    ...(keep && a.map ? { mapping: a.map } : {}), ...(keep && /^(abs|&\d+|or\d+)$/.test(a.enhanced ?? "") ? { stereoLabel: a.enhanced } : {}) }));
  return { type: "molecule", atoms, bonds };
}
// Only the end is trimmed: a molfile's first line (its name) is blank, and without it no program reads the file.
function convert(input: string, format: string, options: Record<string, string> = {}): string {
  const ind = engine(), opts = new ind.MapStringString();
  try {
    for (const [k, v] of Object.entries(options)) opts.set(k, v);
    return ind.convert(input, format, opts).trimEnd();
  } finally {
    opts.delete();
  }
}
export const toSmiles = (drawn: Mol): string => convert(ketOf(drawn), "smiles");
// The drawing's molecules as a molfile: V3000, as ChemDraw 26.1 saves it and Edit > Copy As MOL Text gives it, or
// V2000 (as ChemDraw puts it on the clipboard). A hydrogen bond is bond type 10 and a quadruple bond single, as
// ChemDraw writes them. Map numbers and enhanced stereo go too; V2000 has no enhanced stereo. A query or Markush structure is
// written as V3000 by Octet itself (molv3.ts), with its written labels drawn out as Indigo reads them; its V2000 is
// Indigo's, read from that.
export function toMolfile(drawn: Mol, v2000 = false): string {
  const mode = { "molfile-saving-mode": v2000 ? "2000" : "3000" };
  if (!hasQuery(drawn)) return convert(ketOf(drawn, { keep: true, hbonds: true }), "molfile", mode);
  const v3 = writeV3000(drawn, labelGroup);
  return v2000 ? convert(v3, "molfile", mode) : v3;
}
export const toInchiKey = (drawn: Mol): string => convert(ketOf(drawn), "inchi-key");
// An SD file: one record for each structure, as ChemDraw saves one. A drawing with R-group definitions is one record,
// so its definitions stay with it. A lone atom (methane, a label such as MeOH) is a record too; polymer brackets go
// with each record, where they enclose its atoms.
export function toSdf(drawn: Mol, v2000 = false): string {
  const parts = drawn.shapes?.some((sh) => sh.rgroup) ? [drawn] : fragments(drawn).map((g) => ({ ...pickAtoms(drawn, g), ...(drawn.shapes ? { shapes: drawn.shapes } : {}) }));
  return parts.map((p) => `${toMolfile(p, v2000)}\n$$$$\n`).join("");
}

// One step of a reaction, for RXN, RDF and reaction SMILES: its reactants, its products, and its agents (the structures
// drawn above and below its arrow), each a structure's atoms.
export type RxnStep = { reactants: number[][]; products: number[][]; agents: number[][] };
// A step as a KET reaction for Indigo: each structure keeps its own drawing, set in a row with plus signs between, the
// arrow after the reactants with the agents over it, then the products, so Indigo reads each part as the step says.
function reactionKet(drawn: Mol, step: RxnStep): string {
  const out: Record<string, unknown> = {}, nodes: unknown[] = [];
  let x = 0, k = 0;
  // A structure at x (its left edge), its middle at y; returns its width.
  const put = (atoms: number[], at: number, y = 0) => {
    const m = ketMol(expandLabels(pickAtoms(drawn, atoms)), true, true), xs = m.atoms.map((a) => a.location[0]), ys = m.atoms.map((a) => a.location[1]);
    const dx = at - Math.min(...xs), dy = y - (Math.min(...ys) + Math.max(...ys)) / 2;
    m.atoms = m.atoms.map((a) => ({ ...a, location: [a.location[0] + dx, a.location[1] + dy, 0] as [number, number, number] }));
    out[`mol${k}`] = m;
    nodes.push({ $ref: `mol${k++}` });
    return Math.max(...xs) - Math.min(...xs);
  };
  const row = (list: number[][]) => list.forEach((atoms, j) => { if (j) { nodes.push({ type: "plus", location: [x + 0.75, 0, 0] }); x += 1.5; } x += put(atoms, x) + 1.5; });
  row(step.reactants);
  const widths = step.agents.map((atoms) => { const xs = atoms.map((i) => drawn.atoms[i].location[0]); return Math.max(...xs) - Math.min(...xs); });
  const span = Math.max(3, widths.reduce((s, w) => s + w + 1, 1));
  let ax = x + (span - widths.reduce((s, w) => s + w + 1, -1)) / 2;
  step.agents.forEach((atoms, j) => { put(atoms, ax, 1.5); ax += widths[j] + 1; });
  nodes.push({ type: "arrow", data: { mode: "open-angle", pos: [{ x, y: 0, z: 0 }, { x: x + span, y: 0, z: 0 }] } });
  x += span + 1.5;
  row(step.products);
  return JSON.stringify({ root: { nodes }, ...out });
}
// Reactions as an RXN file (the first step), an RD file (every step, one record each) or reaction SMILES (one line
// for each step), with their map numbers. RXN and RD files are V3000, as ChemDraw 26.1 saves them, or V2000.
export function toReaction(drawn: Mol, steps: RxnStep[], kind: "rxn" | "rdf" | "smiles", v2000 = false): string {
  const mode = { "molfile-saving-mode": v2000 ? "2000" : "3000" };
  if (kind === "smiles") return steps.map((s) => convert(reactionKet(drawn, s), "smiles")).join("\n");
  if (kind === "rxn") return convert(reactionKet(drawn, steps[0]), "rxnfile", mode);
  const d = new Date(), two = (n: number) => String(n).padStart(2, "0");
  const date = `${two(d.getMonth() + 1)}/${two(d.getDate())}/${two(d.getFullYear() % 100)} ${two(d.getHours())}:${two(d.getMinutes())}`;
  return [`$RDFILE 1`, `$DATM    ${date}`, ...steps.flatMap((s) => ["$RFMT", convert(reactionKet(drawn, s), "rxnfile", mode)])].join("\n") + "\n";
}
// Generic labels as query atoms (any atom A, heteroatom Q, metal M, halogen X, and each with H, as ChemDraw's).
// SMILES cannot keep them; a molfile can, for a Reaxys search. undefined when the drawing has none.
// As ChemDraw 26.1 writes a molfile (CoreChemistry IsAcceptableGeneric): A, Q and X go as the atom symbol; the
// others go as a carbon with the label as its alias ("A  n" and the label on the next line).
const GENERIC = new Set(["A", "AH", "Q", "QH", "M", "MH", "X", "XH"]), SYMBOL = new Set(["A", "Q", "X"]);
export function toQueryMolfile(drawn: Mol): string | undefined {
  if (!drawn.atoms.some((a) => a.text && GENERIC.has(a.text))) return undefined;
  const generic = (a: Mol["atoms"][number]) => !!a.text && GENERIC.has(a.text);
  const query = { ...drawn, atoms: drawn.atoms.map((a) => (generic(a) ? { ...a, label: SYMBOL.has(a.text!) ? a.text! : "C", text: undefined } : a)) };
  const { mol, from } = expandWithOrigins(query);
  const aliases = drawn.atoms.flatMap((a, i) => (generic(a) && !SYMBOL.has(a.text!) ? [`A  ${String(from.indexOf(i) + 1).padStart(3)}`, a.text!] : []));
  // From the counts line on, under the header Reaxys was seen to read: a name, the program, a blank line.
  // (A V3000 molfile, for 1000 atoms or more, goes whole: no search link can hold it, and the app says so.)
  const lines = convert(ketOf(query, { hbonds: true, mol }), "molfile").split("\n"), at = lines.findIndex((l) => l.endsWith("V2000")), end = lines.lastIndexOf("M  END");
  return ["Octet", "  Octet", "", ...lines.slice(Math.max(0, at), end), ...aliases, ...lines.slice(end), ""].join("\n");
}
// CIP labels for a drawing's stereocentres (R, S, r, s) and double bonds (E, Z), in its atom and bond order, from
// Octet's own labeller (src/cip.ts). The namer takes these.
export function cipOf(drawn: Mol): Labels {
  const { mol, from } = expandWithOrigins(drawn);
  return onDrawing(drawn, mol, from, cipLabels(mol));
}
// Labels of a structure with its written labels expanded, on the drawn atoms and bonds. Atoms and bonds inside a
// written label (OMe, CO2Et) have no drawn place and are left out, and so is a double bond to a label.
function onDrawing(part: Mol, expanded: Mol, from: number[], labels: Labels, into?: Labels): Labels {
  const out = into ?? { atoms: part.atoms.map(() => undefined), bonds: part.bonds.map(() => undefined) };
  const drawn = (i: number) => !!part.atoms[i] && !part.atoms[i].text;
  labels.atoms.forEach((c, k) => { if (c && drawn(from[k])) out.atoms[from[k]] = c; });
  if (!labels.bonds.some(Boolean)) return out;
  const index = new Map(part.bonds.map((b, j) => [`${Math.min(...b.atoms)} ${Math.max(...b.atoms)}`, j]));
  labels.bonds.forEach((c, k) => {
    const [p, q] = expanded.bonds[k].atoms.map((i) => from[i]), j = index.get(`${Math.min(p, q)} ${Math.max(p, q)}`);
    if (c && j !== undefined && p !== q && drawn(p) && drawn(q)) out.bonds[j] = c;
  });
  return out;
}
// The structures (connected atoms) of a drawing, each with its atoms in order, its bonds, and a key for what its
// stereo labels depend on: its atoms (element, label, charge, radical, isotope, hydrogens set by hand, how the label
// reads, a configuration kept from ChemDraw, and place relative to its first atom) and bonds (with their stereo and display: a wavy bond or a crossed
// double bond has no label). Two structures with one key give the same labels, so labels kept by key are worked out
// again only for the structures an edit changes, wherever they are on the page.
function keyed(mol: Mol): { ids: number[]; bonds: number[]; key: string; part: () => Mol }[] {
  const groups = fragments(mol).map((g) => g.sort((a, b) => a - b)), of: number[] = [];
  groups.forEach((g, k) => g.forEach((i) => { of[i] = k; }));
  const bonds: number[][] = groups.map(() => []);
  mol.bonds.forEach((b, k) => bonds[of[b.atoms[0]]]?.push(k));
  return groups.map((ids, k) => {
    const local = new Map(ids.map((i, n) => [i, n])), o = mol.atoms[ids[0]].location;
    const atoms = ids.map((i) => {
      const a = mol.atoms[i];
      return [a.label, a.text ?? "", a.charge ?? 0, a.radical ?? 0, a.isotope ?? 0, a.implicitHCount ?? "", a.chemical === false ? 0 : 1, a.attach || a.bead ? 1 : 0, a.kept ? `${a.kept.atoms.map((j) => local.get(j) ?? j).join("/")}/${a.kept.marks}` : "", ...[0, 1, 2].map((d) => Math.round(((a.location[d] ?? 0) - (o[d] ?? 0)) * 1e4))].join(" ");
    });
    const bs = bonds[k].map((n) => { const b = mol.bonds[n]; return [b.type, b.stereo ?? 0, b.display ?? "", local.get(b.atoms[0]), local.get(b.atoms[1])].join(" "); });
    const part = (): Mol => ({ atoms: ids.map((i) => renumberCentre(mol.atoms[i], local)), bonds: bonds[k].map((n) => ({ ...mol.bonds[n], atoms: mol.bonds[n].atoms.map((i) => local.get(i)!) as [number, number] })) });
    return { ids, bonds: bonds[k], key: `${atoms.join(",")};${bs.join(",")}`, part };
  });
}
// Show Stereochemistry's labels, in the drawing's own atom and bond order: R, S (and r, s) on stereocentres, E, Z on
// double bonds (src/cip.ts), and M, P on the middle atom of an allene and on a biaryl's axis bond (src/axial.ts). Each
// structure is labelled on its own, and only once while it does not change. Written labels (OMe, CO2Et) are expanded
// first; stereocentres inside a label have no drawn atom and are left out.
type Labels = { atoms: (string | undefined)[]; bonds: (string | undefined)[] };
const labelled = new Map<string, Labels | null>(), STEREO_DISPLAYS = new Set(["hashed", "dashed", "bold", "hollow"]);
export function stereoLabels(drawn: Mol): Labels | undefined {
  const atoms: (string | undefined)[] = drawn.atoms.map(() => undefined), bonds: (string | undefined)[] = drawn.bonds.map(() => undefined);
  for (const { ids, bonds: own, key, part } of keyed(drawn)) {
    // A structure with no stereo bond (a wedge or hash, or a hashed, dashed or bold bond), double bond, depth or kept
    // configuration (from a ChemDraw file) has no R, S, E or Z.
    if (ids.length < 3 || !(own.some((k) => drawn.bonds[k].stereo || drawn.bonds[k].type === 2 || STEREO_DISPLAYS.has(drawn.bonds[k].display ?? "")) || ids.some((i) => drawn.atoms[i].kept || drawn.atoms[i].location[2]))) continue;
    const found = remembered(labelled, key, () => labelsOf(part()));
    found?.atoms.forEach((c, n) => { atoms[ids[n]] = c; });
    found?.bonds.forEach((c, n) => { bonds[own[n]] = c; });
  }
  return atoms.some(Boolean) || bonds.some(Boolean) ? { atoms, bonds } : undefined;
}
// One structure's labels, in its own atom and bond order.
function labelsOf(part: Mol): Labels | null {
  try {
    const { mol: expanded, from } = expandWithOrigins(part);
    const out = onDrawing(part, expanded, from, cipLabels(expanded), onDrawing(part, expanded, from, axialLabels(expanded)));
    return out.atoms.some(Boolean) || out.bonds.some(Boolean) ? out : null;
  } catch {
    return null;
  }
}
// Standard InChI, for telling whether two structures are the same. Undefined if Indigo cannot make one.
export function toInchi(drawn: Mol | string): string | undefined {
  try {
    return convert(typeof drawn === "string" ? drawn : ketOf(drawn), "inchi") || undefined;
  } catch {
    return undefined;
  }
}
// Standard InChI and, on the next line, its AuxInfo (/N: InChI's atoms by the drawing's), for complexes.ts.
export function toInchiAux(drawn: Mol): string | undefined {
  try {
    return convert(ketOf(drawn), "inchi-aux") || undefined;
  } catch {
    return undefined;
  }
}

// A bond's type for a layout: a hydrogen or quadruple bond as a single bond, as Indigo has no type for them.
const shapeType = (type: number) => (type === HBOND || type === QUADRUPLE ? 1 : Math.min(type, 3));
// What Indigo knows of a drawing's stereocentres, for the stereochemistry warnings (check.ts), by drawn atom: the atoms
// that can be stereocentres (read with no wedges), those whose configuration the wedges and hashes do not set, and
// those whose wedges conflict (Indigo cannot read them). A wedge that starts at an atom that cannot be a stereocentre
// is left out of the second reading, as Indigo then lists no atoms. Only structures with a wedge or hash, Show
// Stereochemistry on, or an enhanced stereo flag are read. With `chiral`, structures with an and or or flag are also
// tested for chirality: one whose mirror image (each wedge made a hash) has the same InChI is not chiral. Each
// structure's answer is kept by its atoms and bonds, so an edit reads again only the structures it changed.
type Facts = { centres: number[]; unset: number[]; conflict: number[]; achiral: boolean };
const factsKept = new Map<string, Facts>();
export function stereoFacts(drawn: Mol, chiral = false): StereoFacts {
  const out: StereoFacts = { centres: new Set(), unset: new Set(), conflict: new Set(), achiral: new Set() };
  const wedge = (b: Mol["bonds"][number]) => b.stereo === 1 || b.stereo === 6, wedged = new Set(drawn.bonds.filter(wedge).flatMap((b) => b.atoms));
  const groups = fragments(drawn), groupOf = new Int32Array(drawn.atoms.length), bondsOf: Mol["bonds"][] = groups.map(() => []);
  groups.forEach((g, k) => { for (const i of g) groupOf[i] = k; });
  for (const b of drawn.bonds) bondsOf[groupOf[b.atoms[0]]].push(b);
  groups.forEach((group, k) => {
    if (!group.some((i) => wedged.has(i) || drawn.atoms[i].cip || drawn.atoms[i].enhanced)) return;
    const flagged = chiral && group.some((i) => /^(&|or)/.test(drawn.atoms[i].enhanced ?? ""));
    // The structure on its own (atoms in drawing order), and its key: what Indigo's answer depends on.
    const ids = [...group].sort((a, b) => a - b), local = new Map(ids.map((d, j) => [d, j]));
    const part: Mol = { atoms: ids.map((i) => renumberCentre(drawn.atoms[i], local)), bonds: bondsOf[k].map((b) => ({ ...b, atoms: [local.get(b.atoms[0])!, local.get(b.atoms[1])!] as [number, number] })) };
    const key = JSON.stringify([part.atoms.map((a) => [a.label, a.text, a.charge, a.isotope, a.radical, a.location[0], a.location[1]]), part.bonds.map((b) => [b.type, b.atoms, b.stereo]), flagged]);
    let f = factsKept.get(key);
    if (!f) {
      // Read with labels expanded; kept by the structure's own atoms (an atom inside a label is left out).
      const { mol, from } = expandWithOrigins(part), read = readFacts(mol, flagged);
      const own = (list: number[]) => list.flatMap((j) => (part.atoms[from[j]] && !part.atoms[from[j]].text ? [from[j]] : []));
      f = { centres: own(read.centres), unset: own(read.unset), conflict: own(read.conflict), achiral: read.achiral };
      if (factsKept.size > 500) factsKept.clear();
      factsKept.set(key, f);
    }
    for (const [list, set] of [[f.centres, out.centres], [f.unset, out.unset], [f.conflict, out.conflict]] as const) for (const j of list) set.add(ids[j]);
    if (f.achiral) for (const i of ids) out.achiral.add(i);
  });
  // A centre Show Stereochemistry labels is not unset or conflicting, whatever Indigo reads: Octet's labeller also
  // reads ChemDraw's other stereo bonds (a hashed, dashed or bold bond, a wedge's wide end; src/cip.ts).
  if ([...out.unset, ...out.conflict].some((i) => drawn.atoms[i]?.cip)) {
    const shown = stereoLabels(drawn);
    for (const set of [out.unset, out.conflict]) for (const i of set) if (drawn.atoms[i].cip && shown?.atoms[i]) set.delete(i);
  }
  return out;
}
function readFacts(mol: Mol, chiral: boolean): Facts {
  const ind = engine();
  // The atoms Indigo lists as stereocentres with no set configuration. Throws when the wedges conflict.
  const unsetOf = (m: Mol): number[] => {
    const opts = new ind.MapStringString();
    try {
      const said = JSON.parse(ind.check(ketOf(m), "stereo", opts)).stereo as string | undefined, list = said && /\(([\d,\s]+)\)/.exec(said);
      return list ? list[1].split(",").map(Number) : [];
    } finally {
      opts.delete();
    }
  };
  let centres: number[] = [];
  try { centres = unsetOf({ ...mol, bonds: mol.bonds.map((b) => ({ ...b, stereo: undefined })) }); } catch { /* no centres read */ }
  // Indigo also lists a planar N (an amide's, an aniline's, a nucleoside base's: N with a multiple bond, or next to an
  // atom with one), which is no stereocentre, so a wedge from a carbon to it gave a false "between" warning (issue #9).
  const multiple = (i: number) => mol.bonds.some((b) => b.atoms.includes(i) && orderOf(b.type) > 1);
  const planar = (i: number) => mol.atoms[i].label === "N" && mol.bonds.some((b) => b.atoms.includes(i) && (orderOf(b.type) > 1 || multiple(b.atoms[0] === i ? b.atoms[1] : b.atoms[0])));
  // A neutral amine N with three bonds inverts quickly, so it is no stereocentre either (LSD's N6, a tropane's N-methyl,
  // a ring fusion such as an indolizidine's), unless it is the bridgehead of a bridged ring system and cannot invert
  // (strychnine's N4, quinine's N1, Tröger's base). At a bridgehead, each two of its neighbours stay joined with the
  // third removed; at a ring fusion, the shared neighbour is the only way between the other two.
  const near = (i: number) => mol.bonds.flatMap((b) => (b.atoms.includes(i) ? [b.atoms[0] === i ? b.atoms[1] : b.atoms[0]] : []));
  const joined = (a: number, c: number, not: number[]) => {
    const seen = new Set([a, ...not]), next = [a];
    for (let x = next.pop(); x !== undefined; x = next.pop()) for (const y of near(x)) if (!seen.has(y)) { if (y === c) return true; seen.add(y); next.push(y); }
    return false;
  };
  const amine = (i: number) => mol.atoms[i].label === "N" && !mol.atoms[i].charge && near(i).length === 3;
  const bridgehead = (i: number) => near(i).every((b, _, nb) => { const [a, c] = nb.filter((x) => x !== b); return joined(a, c, [i, b]); });
  // A bridgehead N next to an aryl ring (Tröger's base) is still pyramidal; next to C=O (strychnine's lactam N1) it is not.
  const amide = (i: number) => multiple(i) || near(i).some((j) => mol.bonds.some((b) => b.atoms.includes(j) && orderOf(b.type) > 1 && mol.atoms[b.atoms[0] === j ? b.atoms[1] : b.atoms[0]].label !== "C"));
  centres = centres.filter((i) => (amine(i) ? bridgehead(i) && !amide(i) : !planar(i)));
  const can = new Set(centres), conflict: number[] = [];
  let kept: Mol = { ...mol, bonds: mol.bonds.map((b) => ((b.stereo === 1 || b.stereo === 6) && !can.has(b.atoms[0]) ? { ...b, stereo: undefined } : b)) }, unset: number[] = [];
  for (let k = 0; k < 8; k++) {
    try { unset = unsetOf(kept); break; } catch (err) {
      // "stereocenters: all 3 bonds up near stereoatom 0", "one bond up, one bond down -- indefinite case near atom 0"
      const at = /near (?:stereo)?atom (\d+)/.exec(String(err));
      if (!at) { unset = []; break; }
      const i = Number(at[1]);
      conflict.push(i);
      kept = { ...kept, bonds: kept.bonds.map((b) => (b.atoms[0] === i ? { ...b, stereo: undefined } : b)) };
    }
  }
  const mirror = (m: Mol): Mol => ({ ...m, bonds: m.bonds.map((b) => (b.stereo === 1 ? { ...b, stereo: 6 } : b.stereo === 6 ? { ...b, stereo: 1 } : b)) });
  const inchi = chiral ? toInchi(kept) : undefined;
  return { centres, unset: unset.filter((i) => can.has(i)), conflict, achiral: !!inchi && inchi === toInchi(mirror(kept)) };
}

// Clean Up's time. Indigo's clean-up (two passes of up to 1,000 rounds) costs about N^3 a round, from 0.27 s at 120
// atoms to 3 to 5 minutes at 1,000, and Indigo stops a pass only after 2 s. So Octet runs its own port of it
// (src/clean2d.ts): the same rounds at about N a round. Structures of up to about 40 atoms are cleaned as Indigo cleans
// them with no time limit, in under 0.1 s. Each pass of a larger structure stops after PASS ms, and several structures
// share 2 × PASS ms a pass. A large structure drawn by hand may come out rougher than Indigo's would, and Clean Up again
// tidies it further, as in ChemDraw. A structure of more than MOST_CLEAN atoms is left as drawn (src/cleanup.check.ts).
const PASS = 100;
export const MOST_CLEAN = MOST_ATOMS;

// Clean Up Structure: bond lengths and angles straightened, structure by structure. Each structure the selection
// touches (or every structure, with nothing selected) is cleaned whole, scaled to one bond length per bond at the
// structure's own scale (the median of its atoms' scales, decision 0007), and kept centred where it was. A structure
// of more than MOST_CLEAN atoms is left as drawn.
// pass: the ms each of the two passes may take for one structure.
export function cleanUp(mol: Mol, ids?: Set<number>, pass = PASS): Mol {
  const atoms = mol.atoms.map((a) => ({ ...a }));
  // Structures joined by bonds alone; one with a multi-centre or variable attachment keeps its place (the attachment
  // sits at the centre of its atoms), and so does its ring (a π ligand drawn in perspective, not bonded to the point),
  // and so does one drawn in perspective (with depth: a chair, a Newman projection, a paddlewheel), as it is never
  // messy (check.ts). Flatten first to clean one up.
  const pi = new Set(mol.atoms.flatMap((a) => a.centre?.atoms ?? []));
  const groups = fragments(mol, false).filter((frag) => frag.length > 1 && frag.length <= MOST_CLEAN && (!ids?.size || frag.some((i) => ids.has(i))) && !frag.some((i) => mol.atoms[i].centre || mol.atoms[i].location[2] || pi.has(i)));
  for (const frag of groups) {
    const local = new Map(frag.map((i, k) => [i, k]));
    const bonds = mol.bonds.filter((b) => local.has(b.atoms[0]) && local.has(b.atoms[1]));
    const out = clean2d(frag.map((i) => mol.atoms[i].location), bonds.map((b) => ({ atoms: [local.get(b.atoms[0])!, local.get(b.atoms[1])!], order: shapeType(b.type) })), pass * Math.min(1, 2 / groups.length));
    const lengths = bonds.map((b) => {
      const [p, q] = [out[local.get(b.atoms[0])!], out[local.get(b.atoms[1])!]];
      return Math.hypot(q[0] - p[0], q[1] - p[1]);
    }).sort((a, b) => a - b);
    const own = frag.map((i) => mol.atoms[i].scale ?? 1).sort((a, b) => a - b)[Math.floor(frag.length / 2)];
    const scale = own / (lengths[Math.floor(lengths.length / 2)] || 1);
    const centre = (pts: readonly (readonly number[])[]) => [0, 1].map((k) => pts.reduce((sum, p) => sum + p[k], 0) / pts.length);
    const [ox, oy] = centre(frag.map((i) => mol.atoms[i].location)), [nx, ny] = centre(out);
    frag.forEach((i, k) => {
      const [x, y] = out[k];
      atoms[i] = { ...atoms[i], location: [ox + (x - nx) * scale, oy + (y - ny) * scale, 0] };
    });
    // As ChemDraw's clean up leaves it: a ring structure turned so its bottom ring bond is level, and a structure
    // without rings turned so the most bonds lie at a multiple of 30°.
    const turn = levelTurn({ ...mol, atoms }, frag);
    if (turn) {
      const c = Math.cos((turn * Math.PI) / 180), s = Math.sin((turn * Math.PI) / 180);
      frag.forEach((i) => { const [x, y] = atoms[i].location; atoms[i] = { ...atoms[i], location: [ox + (x - ox) * c - (y - oy) * s, oy + (x - ox) * s + (y - oy) * c, 0] }; });
    }
  }
  return { ...mol, atoms };
}

// The pieces a mass-fragmentation cut makes: the cut bonds are taken out and every atom keeps the hydrogens it had
// in the whole molecule (a homolytic cleavage). Each piece that a cut bond touched, with its formula and exact mass.
export function fragmentMasses(mol: Mol, cut: number[]): { atoms: number[]; formula: string; exact: number }[] | undefined {
  if (!indigo || !cut.length) return undefined;
  const ind = indigo, full = expandLabels(mol), cutSet = new Set(cut);
  const used = full.atoms.map(() => 0);
  full.bonds.forEach((b) => b.atoms.forEach((i) => (used[i] += orderOf(b.type))));
  const h = full.atoms.map((a, i) => a.implicitHCount ?? hydrogens(a.label, a.charge ?? 0, used[i], a.radical));
  // Pieces: atoms joined by the bonds that are not cut.
  const root = full.atoms.map((_, i) => i), find = (i: number): number => (root[i] === i ? i : (root[i] = find(root[i])));
  full.bonds.forEach((b, k) => { if (!cutSet.has(k)) root[find(b.atoms[0])] = find(b.atoms[1]); });
  const touched = new Set(cut.flatMap((k) => full.bonds[k] ? full.bonds[k].atoms.map(find) : []));
  const out: { atoms: number[]; formula: string; exact: number }[] = [];
  for (const r of touched) {
    const atoms = full.atoms.map((_, i) => i).filter((i) => find(i) === r), local = new Map(atoms.map((i, k) => [i, k]));
    const ket = JSON.stringify({ root: { nodes: [{ $ref: "mol0" }] }, mol0: { type: "molecule",
      atoms: atoms.map((i) => ({ label: full.atoms[i].label, location: full.atoms[i].location, implicitHCount: h[i], ...(full.atoms[i].charge ? { charge: full.atoms[i].charge } : {}) })),
      bonds: full.bonds.filter((b, k) => !cutSet.has(k) && local.has(b.atoms[0]) && local.has(b.atoms[1])).map((b) => ({ type: b.type === QUADRUPLE ? 1 : b.type, atoms: [local.get(b.atoms[0]), local.get(b.atoms[1])] })) } });
    const opts = new ind.MapStringString(), sel = new ind.VectorInt();
    try {
      const res = JSON.parse(ind.calculate(ket, opts, sel));
      out.push({ atoms: atoms.filter((i) => i < mol.atoms.length), formula: String(res["gross-formula"]).replace(/\s+/g, ""), exact: Number(res["monoisotopic-mass"]) });
    } catch {
      return undefined;
    } finally {
      opts.delete();
      sel.delete();
    }
  }
  return out;
}

// Atom map numbers for one reaction step, from Indigo's automapper: for each reactant and product (in order), each
// atom's number, or undefined where an atom has no partner. Written labels count as the element they attach by.
// keep: the atoms' map numbers (pairs mapped by hand) stay, and only the rest are mapped (Indigo's keep mode).
export function mapReaction(reactants: Mol[], products: Mol[], keep = false): { reactants: (number | undefined)[][]; products: (number | undefined)[][] } | undefined {
  if (!indigo || !reactants.length || !products.length) return undefined;
  const ind = indigo, opts = new ind.MapStringString();
  try {
    // A molfile keeps its first (name) line, so it is not trimmed.
    const molfile = (m: Mol) => {
      const o = new ind.MapStringString();
      try {
        return ind.convert(JSON.stringify({ root: { nodes: [{ $ref: "mol0" }] }, mol0: { type: "molecule",
          atoms: m.atoms.map((a) => ({ label: /^[A-Z][a-z]?$/.test(a.label) ? a.label : "C", location: a.location, ...(a.charge ? { charge: a.charge } : {}), ...(keep && a.map ? { mapping: a.map } : {}) })),
          bonds: m.bonds.filter((b) => b.type !== HBOND).map((b) => ({ type: shapeType(b.type), atoms: b.atoms })) } }), "molfile", o).replace(/\s+$/, "");
      } finally { o.delete(); }
    };
    const rxn = ["$RXN", "", "  Octet", "", `${String(reactants.length).padStart(3)}${String(products.length).padStart(3)}`, ...[...reactants, ...products].flatMap((m) => ["$MOL", molfile(m)])].join("\n");
    opts.set("output-content-type", "application/json");
    const ket = JSON.parse(JSON.parse(ind.automap(rxn, keep ? "keep" : "discard", "ket", opts)).struct);
    const mols = (ket.root.nodes as { $ref?: string }[]).flatMap((n) => (n.$ref && ket[n.$ref]?.type === "molecule" ? [ket[n.$ref].atoms.map((a: { mapping?: number }) => a.mapping)] : []));
    if (mols.length !== reactants.length + products.length) return undefined;
    return { reactants: mols.slice(0, reactants.length), products: mols.slice(reactants.length) };
  } catch {
    return undefined;
  } finally {
    opts.delete();
  }
}

// The Chemical Properties panel's values for each structure in a drawing (or a selection): formula, masses and
// composition from Indigo; Wildman–Crippen logP and molar refractivity from Indigo, one structure at a time (it adds
// a mixture's together); and the structure's graph for Octet's own calculators (props.ts).
export type Structure = { formula: string; weight: number; exact: number; composition: string; logP?: number; mr?: number; graph?: Graph; repeat?: Repeat };
const structured = new Map<string, Structure | undefined>();
export function structures(mol: Mol, groups = fragments(mol)): (Structure | undefined)[] | undefined {
  if (!indigo || !mol.atoms.length) return undefined;
  const ind = indigo, opts = new ind.MapStringString(), sel = new ind.VectorInt(), out: (Structure | undefined)[] = [];
  // Indigo reports a failed logP or MR as -1.
  const num = (s: string) => (s.trim() === "-1.000000" ? undefined : Number(s));
  try {
    for (const ids of groups.slice(0, 12)) {
      const part = subset(mol, new Set(ids));
      // A polymer: its repeat units counted as its brackets say (no logP or properties for a polymer).
      const polymer = polymerValues(part);
      if (polymer) { out.push(polymer); continue; }
      out.push(remembered(structured, contentOf(part), () => {
        try {
          const ket = ketOf(part, { wedges: false }), calc = JSON.parse(ind.calculate(ket, opts, sel));
          const heavy = expandLabels(part).atoms.filter((a) => a.label !== "H").length;
          // Ferrocene's pieces (its multi-centre attachments are left out of the chemistry) as one compound.
          const one = summed(calc);
          return {
            formula: one.formula, weight: one.weight, exact: one.exact, composition: one.composition,
            // ChemDraw stops at 150 heavy atoms for logP and 1,000 atoms for the rest; so does Octet.
            ...(heavy <= 150 ? { logP: num(ind.logp(ket, opts)), mr: num(ind.molarRefractivity(ket, opts)) } : {}),
            graph: heavy <= 1000 ? graphOf(expandLabels(part)) : undefined,
          };
        } catch { return undefined; } // a structure Indigo cannot read has no values
      }));
    }
    return out.some(Boolean) ? out : undefined;
  } finally {
    opts.delete();
    sel.delete();
  }
}

// Formula and masses for the drawing or a selection, one entry for each structure in it (the first limit of them),
// with written labels counted as their atoms. Each structure is worked out on its own and kept by its content.
// Undefined while Indigo is loading or if it cannot read any structure. cite: the abbreviation for a structure's
// standard InChI (names.ts abbreviationOf), given as each structure's abbreviation (TREN).
export type Analysis = { formula: string; weight: number; exact: number; repeat?: Repeat; abbreviation?: string }[];
const analysed = new Map<string, Analysis | undefined>(), inchis = new Map<string, string | undefined>();
export function analyse(mol: Mol, limit = Infinity, cite?: (inchi: string | undefined) => string | undefined): Analysis | undefined {
  if (!indigo || !mol.atoms.length) return undefined;
  const out: Analysis = [], parts = pieces(mol);
  // Pieces that are one compound together, as a salt ([Ru(bpy)3]Cl2), a complex with its ligands apart (Ni(cod)2) or
  // ferrocene's ions (dppf), are one entry when they are all there is and have an abbreviation.
  if (cite && parts.length > 1 && parts.length <= 12 && mol.atoms.length <= 300 && !mol.shapes?.some((sh) => sh.polymer)) {
    const abbreviation = cite(remembered(inchis, contentOf(mol), () => toInchi(mol)));
    const entries = abbreviation ? parts.flatMap((part) => remembered(analysed, contentOf(part), () => analyseAll(part)) ?? []) : [];
    if (abbreviation && entries.length) {
      const total: Record<string, number> = {};
      for (const e of entries) for (const [el, n] of Object.entries(counts(e.formula) ?? {})) total[el] = (total[el] ?? 0) + n;
      return [{ formula: hill(total), weight: entries.reduce((t, e) => t + e.weight, 0), exact: entries.reduce((t, e) => t + e.exact, 0), abbreviation }];
    }
  }
  for (const part of parts) {
    if (out.length >= limit) break;
    const polymer = mol.shapes?.some((sh) => sh.polymer) ? polymerValues({ ...part, shapes: mol.shapes }) : undefined;
    if (polymer) { out.push(polymer); continue; }
    const entries = remembered(analysed, contentOf(part), () => analyseAll(part)) ?? [];
    const abbreviation = cite && entries.length === 1 ? cite(remembered(inchis, contentOf(part), () => toInchi(part))) : undefined;
    // A structure held together by multi-centre attachments (ferrocene) is one compound, not its pieces.
    if (entries.length > 1 && part.atoms.some((a) => a.centre)) {
      const total: Record<string, number> = {};
      for (const e of entries) for (const [el, n] of Object.entries(counts(e.formula) ?? {})) total[el] = (total[el] ?? 0) + n;
      out.push({ formula: hill(total), weight: entries.reduce((t, e) => t + e.weight, 0), exact: entries.reduce((t, e) => t + e.exact, 0) });
    } else out.push(...(abbreviation ? [{ ...entries[0], abbreviation }] : entries));
  }
  return out.length ? out.slice(0, limit) : undefined;
}
// Indigo's values for a molecule as one compound: its pieces ("C5 H5; C5 H5; Fe") added together.
function summed(calc: Record<string, unknown>): { formula: string; weight: number; exact: number; composition: string } {
  const split = (key: string) => String(calc[key]).split(";").map((v) => v.trim());
  const formulas = split("gross-formula");
  if (formulas.length === 1) return { formula: formulas[0].replace(/\s+/g, ""), weight: Number(calc["molecular-weight"]), exact: Number(calc["monoisotopic-mass"]), composition: String(calc["mass-composition"]) };
  const weights = split("molecular-weight").map(Number), counts: Record<string, number> = {}, masses: Record<string, number> = {};
  for (const f of formulas) for (const [el, n] of Object.entries(formulaCounts(f) ?? {})) counts[el] = (counts[el] ?? 0) + n;
  split("mass-composition").forEach((c, j) => { const t = c.split(/\s+/); for (let k = 0; k + 1 < t.length; k += 2) masses[t[k]] = (masses[t[k]] ?? 0) + (Number(t[k + 1]) * weights[j]) / 100; });
  const weight = weights.reduce((a, b) => a + b, 0);
  return { formula: hill(counts), weight, exact: split("monoisotopic-mass").map(Number).reduce((a, b) => a + b, 0), composition: Object.entries(masses).map(([el, w]) => `${el} ${((100 * w) / (weight || 1)).toFixed(2)}`).join(" ") };
}

// A polymer's formula and masses (ChemDraw's Bracket Properties): a multiple group's or parameterizable bracket's atoms
// counted as many times as it repeats (a parameterizable bracket's Mw sets its count), and an SRU's repeat unit apart
// from the end groups, as C2H6(C2H4)n. Where a bond crosses an SRU's bracket to a bare carbon with no other bond, the
// chain goes on: that carbon is not an end group (polyethylene drawn as –[CH2CH2]n– is (C2H4)n, not C4H10).
// Undefined for a structure with no such brackets. Each atom keeps the hydrogens it has in the whole structure.
export type Repeat = { label: string; weight: number; exact: number; ends?: { weight: number; exact: number } };
type Values = { formula: string; weight: number; exact: number; composition: string; repeat?: Repeat };
function polymerValues(part: Mol): Values | undefined {
  const brackets = polymerBrackets(part).filter((b) => ["sru", "mult", "param"].includes(b.sh.polymer!.usage));
  if (!brackets.length || !indigo) return undefined;
  const ind = indigo, { mol: x, from } = expandWithOrigins(part), used = x.atoms.map(() => 0), deg = part.atoms.map(() => 0);
  x.bonds.forEach((b) => b.atoms.forEach((i) => (used[i] += orderOf(b.type))));
  part.bonds.forEach((b) => b.atoms.forEach((i) => deg[i]++));
  const h = x.atoms.map((a, i) => a.implicitHCount ?? hydrogens(a.label, a.charge ?? 0, used[i], a.radical === 3 ? 2 : a.radical));
  const inOf = new Map<number, number>();
  brackets.forEach((b, k) => b.atoms.forEach((i) => { if (!inOf.has(i)) inOf.set(i, k); }));
  // Open ends: only at a repeat with no number (an SRU's n); a multiple group's end carbons are methyl groups.
  const numbered = brackets.map((b) => b.sh.polymer!.usage === "param" && !!b.sh.polymer!.mw || repeatCount(b.sh.polymer!) !== undefined);
  const open = new Set(part.atoms.flatMap((a, i) => (!inOf.has(i) && a.label === "C" && !a.text && !a.charge && !a.isotope && deg[i] === 1
    && part.bonds.some((b) => { const j = b.atoms[0] === i ? b.atoms[1] : b.atoms[0]; return b.atoms.includes(i) && inOf.has(j) && !numbered[inOf.get(j)!]; }) ? [i] : [])));
  // Formula, masses and composition of some of the expanded atoms, from Indigo.
  const calc = (atoms: number[]) => {
    if (!atoms.length) return { counts: {} as Record<string, number>, weight: 0, exact: 0, masses: {} as Record<string, number> };
    const local = new Map(atoms.map((i, k) => [i, k]));
    const ket = JSON.stringify({ root: { nodes: [{ $ref: "mol0" }] }, mol0: { type: "molecule",
      atoms: atoms.map((i) => ({ label: x.atoms[i].label, location: x.atoms[i].location, implicitHCount: h[i], ...(x.atoms[i].charge ? { charge: x.atoms[i].charge } : {}), ...(x.atoms[i].isotope ? { isotope: x.atoms[i].isotope } : {}) })),
      bonds: x.bonds.filter((b) => local.has(b.atoms[0]) && local.has(b.atoms[1])).map((b) => ({ type: Math.min(3, b.type), atoms: [local.get(b.atoms[0]), local.get(b.atoms[1])] })) } });
    const opts = new ind.MapStringString(), sel = new ind.VectorInt();
    try {
      // Indigo gives each piece apart ("C H3; C H3"): their sums.
      const r = JSON.parse(ind.calculate(ket, opts, sel)), split = (key: string) => String(r[key]).split(";").map((v) => v.trim());
      const weights = split("molecular-weight").map(Number), exacts = split("monoisotopic-mass").map(Number), masses: Record<string, number> = {}, counts: Record<string, number> = {};
      split("mass-composition").forEach((c, j) => { const t = c.split(/\s+/); for (let k = 0; k + 1 < t.length; k += 2) masses[t[k]] = (masses[t[k]] ?? 0) + (Number(t[k + 1]) * weights[j]) / 100; });
      for (const f of split("gross-formula")) { const c = formulaCounts(f); if (!c) return undefined; for (const [el, n] of Object.entries(c)) counts[el] = (counts[el] ?? 0) + n; }
      const weight = weights.reduce((a, b) => a + b, 0), exact = exacts.reduce((a, b) => a + b, 0);
      return Number.isFinite(weight) ? { counts, weight, exact, masses } : undefined;
    } catch { return undefined; } finally { opts.delete(); sel.delete(); }
  };
  const ends = calc(x.atoms.map((_, j) => j).filter((j) => !inOf.has(from[j]) && !open.has(from[j])));
  const units = brackets.map((b, k) => ({ p: b.sh.polymer!, v: calc(x.atoms.map((_, j) => j).filter((j) => inOf.get(from[j]) === k)) }));
  if (!ends || units.some((u) => !u.v)) return undefined;
  // Numbered repeats are counted into the rest; the first SRU or label repeat stays as its unit and label.
  const rest = { counts: { ...ends.counts }, weight: ends.weight, exact: ends.exact, masses: { ...ends.masses } };
  let symbolic: { label: string; v: NonNullable<ReturnType<typeof calc>> } | undefined, more = "";
  for (const u of units) {
    const k = repeatCount(u.p, u.v!.weight);
    if (k === undefined) {
      const label = polymerLabel(u.p) || "n";
      if (!symbolic) symbolic = { label, v: u.v! }; else more += `(${hill(u.v!.counts)})${label}`;
      continue;
    }
    for (const [el, c] of Object.entries(u.v!.counts)) rest.counts[el] = (rest.counts[el] ?? 0) + k * c;
    for (const [el, w] of Object.entries(u.v!.masses)) rest.masses[el] = (rest.masses[el] ?? 0) + k * w;
    rest.weight += k * u.v!.weight;
    rest.exact += k * u.v!.exact;
  }
  const compose = (masses: Record<string, number>, weight: number) => Object.entries(masses).map(([el, w]) => `${el} ${((100 * w) / (weight || 1)).toFixed(2)}`).join(" ");
  if (!symbolic) return { formula: hill(rest.counts), weight: rest.weight, exact: rest.exact, composition: compose(rest.masses, rest.weight) };
  const hasRest = Object.keys(rest.counts).length > 0;
  return {
    formula: `${hasRest ? hill(rest.counts) : ""}(${hill(symbolic.v.counts)})${symbolic.label}${more}`, weight: rest.weight + symbolic.v.weight, exact: rest.exact + symbolic.v.exact,
    composition: compose(symbolic.v.masses, symbolic.v.weight),
    repeat: { label: symbolic.label, weight: symbolic.v.weight, exact: symbolic.v.exact, ...(hasRest ? { ends: { weight: rest.weight, exact: rest.exact } } : {}) },
  };
}
// "C2 H4" as element counts.
function formulaCounts(f: string): Record<string, number> | undefined {
  const out: Record<string, number> = {};
  for (const t of f.trim().split(/\s+/)) {
    const m = /^([A-Z][a-z]?)(\d*)$/.exec(t);
    if (!m) return t ? undefined : out;
    out[m[1]] = (out[m[1]] ?? 0) + (m[2] ? Number(m[2]) : 1);
  }
  return out;
}
// Element counts in Hill order (C, H, then by symbol; by symbol alone with no carbon), fractional counts to 2 places.
function hill(counts: Record<string, number>): string {
  const els = Object.keys(counts).filter((el) => counts[el] > 1e-9).sort((a, b) => a.localeCompare(b, "en"));
  const order = counts.C ? ["C", ...(counts.H ? ["H"] : []), ...els.filter((e) => e !== "C" && e !== "H")] : els;
  return order.map((el) => { const n = counts[el], t = Math.abs(n - Math.round(n)) < 1e-9 ? String(Math.round(n)) : String(+n.toFixed(2)); return el + (t === "1" ? "" : t); }).join("");
}
// Each structure (atoms joined by bonds) on its own, in the drawing's order, with no atom left out.
function pieces(mol: Mol): Mol[] {
  const at: [number, number][] = [];
  const groups = fragments(mol).map((group, k) => {
    const ids = [...group].sort((a, b) => a - b);
    ids.forEach((i, j) => { at[i] = [k, j]; });
    return ids;
  });
  // A multi-centre or variable attachment's atoms, by their number in the piece.
  const parts = groups.map((ids, k) => ({ atoms: ids.map((i) => renumberCentre(mol.atoms[i], (j) => (at[j]?.[0] === k ? at[j][1] : undefined))), bonds: [] as Mol["bonds"] }));
  for (const b of mol.bonds) {
    const [p, q] = [at[b.atoms[0]], at[b.atoms[1]]];
    if (p && q) parts[p[0]].bonds.push({ ...b, atoms: [p[1], q[1]] });
  }
  return parts;
}
// A structure's content as text: what its formula, masses and properties come from (not where it is drawn).
const contentOf = (m: Mol) => JSON.stringify([m.atoms.map((a) => [a.label, a.text, a.charge, a.isotope, a.radical, a.implicitHCount, a.chemical, a.attach, a.bead, a.centre]), m.bonds.map((b) => [b.type, b.stereo, b.atoms])]);
// A value kept by its key, so it is worked out only once. The store is cleared when it grows large.
function remembered<T>(store: Map<string, T>, key: string, make: () => T): T {
  if (store.has(key)) return store.get(key) as T;
  if (store.size >= 500) store.clear();
  const value = make();
  store.set(key, value);
  return value;
}
// Formula and masses for each structure Indigo finds in a molecule, in one call. A structure with no formula or no
// weight (a label Indigo cannot read, alone) has no entry. Indigo gives no exact mass for a structure it reads as a
// bad valence: its exact mass is then not a number.
function analyseAll(mol: Mol): Analysis | undefined {
  const ind = engine(), opts = new ind.MapStringString(), sel = new ind.VectorInt();
  try {
    // A hydrogen bond goes too, so two molecules joined by one are one structure, as drawn.
    const ket = ketOf(mol, { wedges: false, hbonds: true });
    // Indigo reports each structure separately ("C8 H9 N O2; C4 H12 N"): one entry per structure.
    const out = JSON.parse(ind.calculate(ket, opts, sel));
    const split = (key: string) => String(out[key]).split(";").map((x) => x.trim());
    const formulas = split("gross-formula").map((f) => f.replace(/\s+/g, "")), weights = split("molecular-weight").map(Number), exacts = split("monoisotopic-mass").map(Number);
    return formulas.map((formula, k) => ({ formula, weight: weights[k], exact: exacts[k] })).filter((a) => a.formula && Number.isFinite(a.weight));
  } catch {
    return undefined;
  } finally {
    opts.delete();
    sel.delete();
  }
}

// A reagent's formula and molar mass from its SMILES (a reagent written as an abbreviation, such as MeOH or Et3N, read
// by labels.ts), kept by the SMILES. Undefined while Indigo is loading or if it cannot read it.
const reagents = new Map<string, { formula: string; weight: number } | undefined>();
export function smilesWeight(smiles: string): { formula: string; weight: number } | undefined {
  if (!indigo) return undefined;
  const ind = indigo;
  return remembered(reagents, smiles, () => {
    const opts = new ind.MapStringString(), sel = new ind.VectorInt();
    try { const one = summed(JSON.parse(ind.calculate(smiles, opts, sel))); return Number.isFinite(one.weight) && one.weight > 0 ? { formula: one.formula, weight: one.weight } : undefined; } catch { return undefined; } finally { opts.delete(); sel.delete(); }
  });
}
