// HELM and FASTA, in and out (issue 27). Pasted HELM or FASTA opens the Sequence tool's field with the sequence in
// Octet's own words ("peptide: Ac-ACD-NH2", "dna: GATTACA"), so the kind, the ends and Residue labels can be chosen
// before Return draws it. Edit > Copy As > HELM and FASTA write each peptide, RNA or DNA chain in the selection, drawn
// out or as residue labels. ChemDraw's Copy As FASTA gives the letters alone, with X for a residue it does not know (N
// for a nucleotide), and so does Octet's. HELM writes such a residue as SMILES with its two links ([*:1] to the N side
// or 5' side, [*:2] to the other), as HELM does for a monomer of the user's own, so it reads back in other programs.
import type { Mol } from "./render.ts";
import { fragments, pickAtoms } from "./edit.ts";
import { chainResidues } from "./chain.ts";
import { CODES } from "./peptide.ts";
import { labelPath, residueName, sequenceText, type SeqKind } from "./sequence.ts";

// HELM or FASTA as the Sequence tool's text, or why Octet cannot read it (problem). Undefined for any other text.
export function readSequence(pasted: string): { text: string } | { problem: string } | undefined {
  const fasta = fromFasta(pasted);
  return fromHelm(pasted) ?? (fasta ? { text: fasta } : undefined);
}

// HELM: one PEPTIDE or RNA polymer of natural monomers, with Pistoia's [ac] and [am] ends on a peptide and a phosphate
// on either end of RNA or DNA ([dR] sugars).
function fromHelm(helm: string): { text: string } | { problem: string } | undefined {
  const s = helm.trim();
  if (!/^(PEPTIDE|RNA|CHEM|BLOB)\d+\{/.test(s)) return undefined;
  const [polymers, links = ""] = s.split("$"), m = /^(PEPTIDE|RNA)\d+\{([^{}]*)\}$/.exec(polymers);
  if (!m || links.trim()) return { problem: "Octet reads HELM of one peptide, RNA or DNA chain, with no links." };
  // The monomers, split at each dot outside brackets (a monomer's own SMILES has brackets and dots of its own).
  const units = [""];
  let depth = 0;
  for (const ch of m[2]) {
    depth += "[(".includes(ch) ? 1 : ")]".includes(ch) ? -1 : 0;
    if (ch === "." && !depth) units.push(""); else units[units.length - 1] += ch;
  }
  const odd = (u: string) => ({ problem: `Octet does not know the HELM monomer ${u}.` });
  if (m[1] === "PEPTIDE") {
    const start = units[0] === "[ac]", end = units.length > 1 && units[units.length - 1] === "[am]", codes = units.slice(start ? 1 : 0, end ? -1 : undefined);
    const bad = codes.find((u) => !CODES[u]);
    return bad ? odd(bad) : { text: sequenceText({ kind: "peptide", codes: codes.join(""), start, end }).text };
  }
  const start = units[0] === "P", body = units.slice(start ? 1 : 0), read = body.map((u) => /^(R|\[dR\])\(([ACGTU])\)(P?)$/.exec(u));
  // R(T) and [dR](U) are other nucleosides (ribothymidine, deoxyuridine): the Sequence tool would draw rU and dT.
  const bad = body.find((_, k) => !read[k] || read[k]![2] === (read[k]![1] === "R" ? "T" : "U") || (!read[k]![3] && k < body.length - 1));
  if (bad) return odd(bad);
  const dna = read.every((r) => r![1] === "[dR]");
  if (!dna && read.some((r) => r![1] === "[dR]")) return { problem: "Octet reads HELM of RNA or DNA, not both in one chain." };
  return { text: sequenceText({ kind: dna ? "dna" : "rna", codes: read.map((r) => r![2]).join(""), start, end: !!read[read.length - 1]?.[3] }).text };
}

// A FASTA record (">" and a description, then the sequence over one line or more) as the Sequence tool's text: RNA
// when its letters are all bases and one is U, DNA when they are all bases, else a peptide. The first record only.
function fromFasta(fasta: string): string | undefined {
  const m = /^\s*>[^\r\n]*\r?\n([^>]*)/.exec(fasta), codes = m?.[1].replace(/[\s\d*]/g, "").toUpperCase();
  if (!codes || !/^[A-Z]+$/.test(codes)) return undefined;
  const kind: SeqKind = /^[ACGTUN]+$/.test(codes) ? (codes.includes("U") ? "rna" : "dna") : "peptide";
  return sequenceText({ kind, codes, start: false, end: false }).text;
}

// Each peptide, RNA or DNA chain in a drawing: its residues' names (sequence.ts residueTexts: Ala, rA, dA, P), with
// the atoms of each one Octet does not know, and a peptide's ends. inchi reads a drawn residue (residueName).
// earlier: whether an atom is of a residue before the unit (or of the start) or after it.
type Chain = { nucleic: boolean; units: { name?: string; atoms: number[]; earlier?: (i: number) => boolean }[]; ac: boolean; amide: boolean };
function chains(m: Mol, inchi: (x: Mol | string) => string | undefined): Chain[] {
  const out: Chain[] = [];
  for (const frag of fragments(m)) {
    // As residue labels: H–Ala–Cys–OH, Ac–…–NH2, rA–P–rC.
    const labels = labelPath(m, frag)?.map((i) => m.atoms[i].text ?? "H");
    if (labels) {
      const names = labels.filter((t) => !["H", "OH", "Ac", "NH2"].includes(t));
      out.push({ nucleic: !names.some((t) => Object.values(CODES).includes(t)), units: names.map((name) => ({ name, atoms: [] })), ac: labels.includes("Ac"), amide: labels.includes("NH2") });
      continue;
    }
    // Drawn out: each residue read from its atoms. An end Octet does not know (an ester) joins its residue.
    const c = chainResidues(m, frag);
    if (!c) continue;
    const ac = c.start.length === 3 && c.start.map((i) => m.atoms[i].label).sort().join() === "C,C,O", amide = c.end.length === 1 && m.atoms[c.end[0]].label === "N";
    const free = c.end.length === 1 && m.atoms[c.end[0]].label === "O";
    if (c.start.length && !ac) c.residues[0].push(...c.start);
    if (c.end.length && !amide && !free) c.residues[c.residues.length - 1].push(...c.end);
    const where = new Map([...c.residues.flatMap((r, k) => r.map((i): [number, number] => [i, k])), ...c.start.map((i): [number, number] => [i, -1])]);
    out.push({ nucleic: c.nucleic, units: c.residues.map((atoms, k) => ({ name: residueName(m, new Set(atoms), inchi), atoms, earlier: (i: number) => (where.get(i) ?? Infinity) < k })), ac, amide });
  }
  return out;
}
const letter = (name?: string) => Object.keys(CODES).find((k) => CODES[k] === name);

// Edit > Copy As > FASTA: each chain's one-letter codes, a line each. Undefined when there is none.
export function toFasta(m: Mol, inchi: (x: Mol | string) => string | undefined): string | undefined {
  const lines = chains(m, inchi).map((c) => c.units.filter((u) => u.name !== "P").map((u) => (c.nucleic ? /^[rd]([ACGTU])$/.exec(u.name ?? "")?.[1] ?? "N" : letter(u.name) ?? "X")).join(""));
  return lines.length ? lines.join("\n") : undefined;
}

// Edit > Copy As > HELM (HELM 2): PEPTIDE1{[ac].A.C.D.[am]}, RNA1{P.R(A)P.[dR](T)}, each chain a polymer. smiles writes
// a residue Octet does not know. Undefined when there is no chain, or a nucleotide is not one of the ten.
export function toHelm(m: Mol, inchi: (x: Mol | string) => string | undefined, smiles: (x: Mol) => string): string | undefined {
  const count = { PEPTIDE: 0, RNA: 0 }, polymers: string[] = [];
  for (const c of chains(m, inchi)) {
    const kind = c.nucleic ? "RNA" : "PEPTIDE", units: string[] = [];
    if (c.nucleic) for (const u of c.units) {
      const n = /^([rd])([ACGTU])$/.exec(u.name ?? "");
      if (u.name === "P") { if (units.length) units[units.length - 1] += "P"; else units.push("P"); } else if (n) units.push(`${n[1] === "d" ? "[dR]" : "R"}(${n[2]})`); else return undefined;
    }
    else units.push(...(c.ac ? ["[ac]"] : []), ...c.units.map((u) => letter(u.name) ?? `[${linked(m, u.atoms, u.earlier!, smiles)}]`), ...(c.amide ? ["[am]"] : []));
    polymers.push(`${kind}${++count[kind]}{${units.join(".")}}`);
  }
  return polymers.length ? `${polymers.join("|")}$$$$V2.0` : undefined;
}
// A residue as SMILES with its links as HELM writes them: [*:1] where the residue before it bonds, [*:2] where the
// next does. Each link is written as a neon atom marked 1 or 2 first, so the SMILES keeps each stereocentre as it is.
function linked(m: Mol, atoms: number[], earlier: (i: number) => boolean, smiles: (x: Mol) => string): string {
  const inside = new Set(atoms), sorted = [...atoms].sort((p, q) => p - q), part = pickAtoms(m, atoms), links: Mol["atoms"] = [], bonds: Mol["bonds"] = [];
  for (const b of m.bonds) {
    const k = b.atoms.findIndex((i) => inside.has(i)), j = b.atoms[1 - k];
    if (k < 0 || inside.has(j)) continue;
    links.push({ label: "Ne", location: m.atoms[j].location, isotope: earlier(j) ? 1 : 2 });
    bonds.push({ type: 1, atoms: [sorted.indexOf(b.atoms[k]), part.atoms.length + links.length - 1] });
  }
  return smiles({ ...part, atoms: [...part.atoms, ...links], bonds: [...part.bonds, ...bonds] }).replace(/\[([12])Ne\]/g, "[*:$1]");
}
