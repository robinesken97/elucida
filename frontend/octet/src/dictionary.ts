// Name to Structure beyond OPSIN and Octet's own tables (names.ts asks this after them): the dictionary of common,
// trivial and trade names, CAS registry numbers and InChIKeys (data/names/dictionary.tsv.gz, built from Wikidata by
// scripts/build-dictionary.ts), condensed formulas (condensed.ts), and lists of names.
import { commonKey } from "./common.ts";
import { condensedSmiles } from "./condensed.ts";

// Each compound's SMILES, and the compound for each name key, CAS number and InChIKey. beforeOpsin: names OPSIN reads
// as another compound than the one Wikidata and PubChem give (tropicamide), marked "!" in the table.
let smiles: string[] = [];
let byName = new Map<string, number>(), beforeOpsin = new Map<string, number>(), byCas = new Map<string, number>(), byKey = new Map<string, number>();
// The names as written and in lower case, each one's compound, and the names with each trigram (for completion,
// search and spelling mistakes), by index.
let written: string[] = [], lower: string[] = [], compound: number[] = [];
let grams = new Map<string, number[]>();

// Loads the table (once), gzipped next to the app. names.ts starts it with OPSIN.
let loading: Promise<void> | undefined;
export function loadDictionary(): Promise<void> {
  loading ??= (async () => {
    const raw = new Uint8Array(await (await fetch(new URL("../data/names/dictionary.tsv.gz", import.meta.url))).arrayBuffer());
    // A server may have unzipped it already.
    const zipped = raw[0] === 0x1f && raw[1] === 0x8b;
    const text = zipped ? await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).text() : new TextDecoder().decode(raw);
    await attachDictionary(text, true);
  })().catch((e) => { loading = undefined; throw e; });
  return loading;
}

// The table: a compound a line, its SMILES, names (| between), CAS numbers (| between), InChIKey, and names OPSIN
// reads (for suggestions only), tab-separated.
// sliced: read 2,000 lines at a time with a pause between, so typing and drawing never wait. The checks read it whole.
export async function attachDictionary(text: string, sliced = false) {
  const next: string[] = [], names = new Map<string, number>(), first = new Map<string, number>(), cas = new Map<string, number>(), keys = new Map<string, number>();
  const shown = new Map<string, [string, number]>(), show = (name: string, n: number) => { const l = name.toLowerCase(); if (!shown.has(l)) shown.set(l, [name, n]); };
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    if (sliced && i % 2000 === 1999) await pause();
    const [s, ns, cs, key, read] = lines[i].split("\t");
    if (!s || s.length > 4000) continue;
    const n = next.push(s) - 1;
    for (const raw of ns ? ns.split("|") : []) {
      const name = raw.replace(/^!/, ""), k = commonKey(name);
      if (raw !== name) first.set(k, n);
      if (k && !names.has(k)) { names.set(k, n); show(name, n); }
    }
    for (const c of cs ? cs.split("|") : []) if (!cas.has(c)) cas.set(c, n);
    if (key && !keys.has(key)) keys.set(key, n);
    for (const name of read ? read.split("|") : []) show(name, n);
  }
  const index = new Map<string, number[]>(), l: string[] = [], w: string[] = [], c: number[] = [];
  for (const [low, [name, n]] of shown) {
    const i = l.push(low) - 1;
    w.push(name);
    c.push(n);
    if (sliced && i % 3000 === 2999) await pause();
    for (const g of trigrams(low)) { const list = index.get(g); if (list) list.push(i); else index.set(g, [i]); }
  }
  [smiles, byName, beforeOpsin, byCas, byKey, grams, lower, written, compound] = [next, names, first, cas, keys, index, l, w, c];
}
const pause = () => new Promise((ok) => setTimeout(ok, 0));

// SMILES for a name OPSIN misreads (names.ts asks this before OPSIN).
export function beforeOpsinSmiles(text: string): string | undefined {
  const i = text.length <= 200 ? beforeOpsin.get(commonKey(text)) : undefined;
  return i === undefined ? undefined : smiles[i];
}

// ——— CAS registry numbers ———
// Two to seven digits, two digits and a check digit, with hyphens: 64-17-5. Typed with "CAS", "CAS RN" or "CAS No."
// before it, or in square brackets, it is the same number.
const CAS = /^(?:CAS(?:\s*(?:RN|No\.?|number|registry number))?\s*[:#]?\s*)?\[?(\d{2,7})-(\d{2})-(\d)\]?$/i;
const casParts = (text: string) => CAS.exec(text.trim());
// The check digit: the other digits from the right, times 1, 2, 3 and so on, added, modulo 10.
const checkDigit = (digits: string) => [...digits].reverse().reduce((sum, d, i) => sum + Number(d) * (i + 1), 0) % 10;
export function casValid(text: string): boolean {
  const m = casParts(text);
  return !!m && checkDigit(m[1] + m[2]) === Number(m[3]);
}
// The reason a CAS number is refused: its check digit is wrong. Undefined for text that is not a CAS number, or one
// that is right.
export function casProblem(text: string): string | undefined {
  const m = casParts(text);
  if (!m || checkDigit(m[1] + m[2]) === Number(m[3])) return undefined;
  return `Not a CAS number. The last digit must be ${checkDigit(m[1] + m[2])}.`;
}
// The number as the table keeps it (no leading zeros), or undefined.
function casNumber(text: string): string | undefined {
  const m = casParts(text);
  return m && checkDigit(m[1] + m[2]) === Number(m[3]) ? `${Number(m[1])}-${m[2]}-${m[3]}` : undefined;
}

// ——— InChIKeys ———
const INCHIKEY = /^(?:InChIKey=)?([A-Z]{14}-[A-Z]{10}-[A-Z])$/i;
export const inchiKeyOf = (text: string): string | undefined => INCHIKEY.exec(text.trim())?.[1].toUpperCase();

// SMILES for a name from the dictionary, a CAS number, an InChIKey the dictionary has, a condensed formula (PhCH2OH),
// a peptide sequence (Ala-Gly-Ser) or an amino acid written "alpha alanine". Undefined for anything else. read: OPSIN,
// for the systematic name of a peptide.
export function dictionarySmiles(text: string, read?: (name: string) => string | undefined): string | undefined {
  const s = text.trim();
  if (!s || s.length > 200) return undefined;
  const at = (i: number | undefined) => (i === undefined ? undefined : smiles[i]);
  if (casParts(s)) return at(byCas.get(casNumber(s) ?? ""));
  const key = inchiKeyOf(s);
  if (key) return at(byKey.get(key));
  const systematic = read && peptideName(s);
  return at(byName.get(commonKey(s))) ?? condensedSmiles(s) ?? (systematic ? read(systematic) : undefined);
}

// ——— Peptides and amino acids ———
// Each residue's three-letter code, its name as an acyl group and as the amino acid, and whether it has an L form.
const RESIDUES: Record<string, [string, string, boolean]> = {
  Ala: ["alanyl", "alanine", true], Arg: ["arginyl", "arginine", true], Asn: ["asparaginyl", "asparagine", true],
  Asp: ["alpha-aspartyl", "aspartic acid", true], Cys: ["cysteinyl", "cysteine", true], Gln: ["glutaminyl", "glutamine", true],
  Glu: ["alpha-glutamyl", "glutamic acid", true], Gly: ["glycyl", "glycine", false], His: ["histidyl", "histidine", true],
  Ile: ["isoleucyl", "isoleucine", true], Leu: ["leucyl", "leucine", true], Lys: ["lysyl", "lysine", true],
  Met: ["methionyl", "methionine", true], Phe: ["phenylalanyl", "phenylalanine", true], Pro: ["prolyl", "proline", true],
  Ser: ["seryl", "serine", true], Thr: ["threonyl", "threonine", true], Trp: ["tryptophyl", "tryptophan", true],
  Tyr: ["tyrosyl", "tyrosine", true], Val: ["valyl", "valine", true],
};
// The systematic name of a peptide written as a sequence of three-letter codes ("Ala-Gly-Ser", "H-Ala-D-Phe-OH",
// "Ac-Ala-Gly-NH2"), each residue L unless D- comes before it; or of an amino acid written "alpha alanine" or
// "beta alanine". Undefined for anything else.
export function peptideName(text: string): string | undefined {
  const greek = /^(alpha|beta|gamma)[\s-]+([a-z]+)$/i.exec(text);
  if (greek) return greek[1].toLowerCase() === "alpha" ? greek[2] : `${greek[1].toLowerCase()}-${greek[2]}`;
  const parts = text.split("-");
  if (parts.length > 60) return undefined;
  const acetyl = /^Ac$/i.test(parts[0]), capped = acetyl || /^H$/i.test(parts[0]);
  if (capped) parts.shift();
  const end = parts[parts.length - 1], amide = /^NH2$/i.test(end);
  if (amide || /^OH$/i.test(end)) parts.pop();
  const residues: [string, string, boolean, string][] = [];
  for (let i = 0; i < parts.length; i++) {
    const hand = /^[DL]$/i.test(parts[i]) ? parts[i++].toUpperCase() : "L";
    const code = parts[i] ? parts[i][0].toUpperCase() + parts[i].slice(1).toLowerCase() : "";
    if (!RESIDUES[code]) return undefined;
    residues.push([...RESIDUES[code], hand]);
  }
  if (residues.length < (capped || amide ? 1 : 2)) return undefined;
  const named = residues.map(([acyl, acid, chiral, hand], i) => {
    const last = i === residues.length - 1, word = last ? (amide ? (acid.endsWith("ine") ? `${acid.slice(0, -1)}amide` : acid.endsWith("an") ? `${acid}amide` : "") : acid) : acyl;
    return word && (chiral ? `${hand}-${word}` : word);
  });
  return named.every(Boolean) ? `${acetyl ? "N-acetyl-" : ""}${named.join("-")}` : undefined;
}

// ——— Lists of names ———
// A list of names, one a line or with semicolons or commas between ("benzaldehyde, aniline; acetic acid"): the
// structure (SMILES) of each name, when there are 2 to 20 and each one reads. A comma inside a name
// ("2,4-dinitrophenol") has no space after it, so it does not split the name. read: Name to Structure for one name.
export function nameList(text: string, read: (name: string) => string | undefined): string[] | undefined {
  if (text.length > 4000 || !/[\n;]|,\s/.test(text)) return undefined;
  const names = text.split(/\s*[\n;]\s*|,\s+/).map((n) => n.trim()).filter(Boolean);
  if (names.length < 2 || names.length > 20) return undefined;
  const out: string[] = [];
  for (const n of names) { const s = read(n); if (!s) return undefined; out.push(s); }
  return out;
}

// ——— Suggestions ———
// The shortest dictionary name that starts with what was typed (lower case).
// The names that start with it all start with its first trigram (a space and its first two letters).
export function completeName(typed: string): string | undefined {
  let best: string | undefined;
  if (typed.length >= 2) for (const i of grams.get(` ${typed.slice(0, 2)}`) ?? []) if (lower[i].startsWith(typed) && (!best || lower[i].length < best.length)) best = lower[i];
  return best;
}
// Dictionary names, as written, that begin as typed (compared as keys are, so "acetyl salicylic" finds acetylsalicylic
// acid): one for each compound, the shortest first. At most most. For the template library's search and the command
// palette, after Octet's own names (names.ts namesStarting).
export function dictionaryStarting(typed: string, most: number): string[] {
  const q = commonKey(typed.trim()), head = typed.trim().toLowerCase().slice(0, 2);
  if (q.length < 2 || head.length < 2 || most <= 0) return [];
  const found = (grams.get(` ${head}`) ?? []).filter((i) => commonKey(lower[i]).startsWith(q)).sort((a, b) => lower[a].length - lower[b].length || (lower[a] < lower[b] ? -1 : 1));
  const seen = new Set<number>(), out: string[] = [];
  for (const i of found) {
    if (seen.has(compound[i])) continue;
    seen.add(compound[i]);
    out.push(written[i]);
    if (out.length >= most) break;
  }
  return out;
}
// Dictionary names that could be what was typed (lower case) with up to `most` mistakes: those sharing enough of its
// trigrams. A mistake changes at most three trigrams.
export function nearNames(typed: string, most: number): string[] {
  const mine = trigrams(typed), need = Math.max(1, mine.length - 3 * most), touched: number[] = [], out: string[] = [];
  if (counts.length < lower.length) counts = new Uint8Array(lower.length);
  for (const g of new Set(mine)) for (const i of grams.get(g) ?? []) if (counts[i]++ === 0) touched.push(i);
  for (const i of touched) {
    if (counts[i] >= need && Math.abs(lower[i].length - typed.length) <= most) out.push(lower[i]);
    counts[i] = 0;
  }
  return out;
}
// Shared trigram counts for nearNames, back to zero after each use.
let counts = new Uint8Array(0);
function trigrams(s: string): string[] {
  const t = ` ${s} `, out: string[] = [];
  for (let i = 0; i + 3 <= t.length; i++) out.push(t.slice(i, i + 3));
  return out;
}
