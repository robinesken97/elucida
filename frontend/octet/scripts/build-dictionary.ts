// Builds data/names/dictionary.tsv.gz, Name to Structure's dictionary of common, trivial and trade names, CAS registry
// numbers and InChIKeys, from Wikidata (CC0). The compounds are the ones chemists name: those with a SMILES (P233 or
// P2017) and an article in one of the larger Wikipedias. For each: its English and German labels and aliases (ChemDraw
// reads German names), the English label of each brand with it as its one active ingredient (P3781: Tylenol), its CAS
// numbers (P231) and the InChIKey of its structure.
// A name OPSIN reads as the same compound needs no entry (OPSIN is asked first), nor does one in common.ts or drugs.ts.
// PubChem referees: a name two compounds share is kept for the one PubChem gives for it, and likewise a CAS number; a
// name OPSIN reads as another compound is read from the dictionary first where PubChem agrees with Wikidata; and a
// name easily meant as something else (a short code, an English word: "TEN", "salt", "beans") is kept only where
// PubChem gives the same compound for it.
// Run: node scripts/build-dictionary.ts <cache directory> [--check 200]
// The cache directory keeps every Wikidata and PubChem answer, so a second run asks neither again. Put it outside the
// repository. --check compares that many random names with PubChem's structure for each and reports the agreement.
// English words come from /usr/share/dict/words (macOS, and Linux's wamerican package).
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { COMMON, commonKey } from "../src/common.ts";
import { DRUGS } from "../src/drugs.ts";
import { looksLikeSmiles } from "../src/names.ts";
import { ELEMENTS } from "../src/labels.ts";
import { NONMETAL } from "../src/render.ts";
import { casValid } from "../src/dictionary.ts";

const [cacheDir, flag, count] = process.argv.slice(2);
if (!cacheDir) throw new Error("Usage: node scripts/build-dictionary.ts <cache directory> [--check 200]");
mkdirSync(cacheDir, { recursive: true });
const cached = (name: string) => `${cacheDir}/${name}`;
const AGENT = "OctetDictionaryBuild/1.0 (https://github.com/SamChemMan/Octet-Draw)";
const WIKIS = ["en", "de", "fr", "ja", "es", "it", "ru", "zh", "pl", "nl"];
const WORDS = new Set(readFileSync("/usr/share/dict/words", "utf8").split("\n").map((w) => w.trim().toLowerCase()).filter(Boolean));

// ——— Wikidata ———
// One SPARQL query, by POST, as CSV rows. Each answer is kept in the cache.
async function sparql(file: string, query: string): Promise<string[][]> {
  if (!existsSync(cached(file))) {
    for (let attempt = 1; ; attempt++) {
      const r = await fetch("https://query.wikidata.org/sparql", { method: "POST", headers: { "User-Agent": AGENT, Accept: "text/csv", "Content-Type": "application/x-www-form-urlencoded" }, body: `query=${encodeURIComponent(query)}` });
      const text = await r.text();
      // The service sends a timeout as a Java stack trace after the rows.
      if (r.ok && !/TimeoutException|at com\.bigdata/.test(text)) { writeFileSync(cached(file), text); break; }
      if (attempt === 4) throw new Error(`Wikidata: ${file} failed (${r.status})`);
      await new Promise((ok) => setTimeout(ok, 5000 * attempt));
    }
  }
  return csv(readFileSync(cached(file), "utf8")).slice(1);
}
function csv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field.replace(/\r$/, "")); rows.push(row); row = []; field = ""; }
    else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}
const ENTITY = /^http:\/\/www\.wikidata\.org\/entity\/(Q\d+)$/;
const qid = (uri: string) => ENTITY.exec(uri)?.[1];

const ids = new Set<string>();
for (const wiki of WIKIS) {
  // The query takes up to a minute for the larger Wikipedias. One that keeps failing is left out (but not English).
  const rows = await sparql(`ids-${wiki}.csv`, `SELECT DISTINCT ?item WHERE { { ?item wdt:P233 ?s } UNION { ?item wdt:P2017 ?s } ?a schema:about ?item ; schema:isPartOf <https://${wiki}.wikipedia.org/> . }`)
    .catch((e) => { if (wiki === "en") throw e; console.log(`${wiki}: left out (${e.message})`); return []; });
  for (const [item] of rows) { const q = qid(item ?? ""); if (q) ids.add(q); }
  console.log(`${wiki}: ${rows.length} compounds, ${ids.size} in all`);
}
type Item = { id: string; label?: string; aliases: string[]; german: string[]; canonical: string[]; isomeric: string[]; cas: string[]; keys: string[] };
const items = new Map<string, Item>();
const all = [...ids].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1)));
const BATCH = 1000;
for (let b = 0; b * BATCH < all.length; b++) {
  const part = all.slice(b * BATCH, (b + 1) * BATCH);
  const rows = await sparql(`batch-${b}-${part.length}.csv`, `SELECT ?item ?kind ?v WHERE { VALUES ?item { ${part.map((q) => `wd:${q}`).join(" ")} }
    { ?item rdfs:label ?v . FILTER(LANG(?v) = "en") BIND("l" AS ?kind) } UNION { ?item skos:altLabel ?v . FILTER(LANG(?v) = "en") BIND("a" AS ?kind) }
    UNION { ?item wdt:P233 ?v . BIND("c" AS ?kind) } UNION { ?item wdt:P2017 ?v . BIND("i" AS ?kind) }
    UNION { ?item wdt:P231 ?v . BIND("r" AS ?kind) } UNION { ?item wdt:P235 ?v . BIND("k" AS ?kind) } }`);
  for (const [uri, kind, v] of rows) {
    const id = qid(uri ?? "");
    if (!id || !v) continue;
    const it = items.get(id) ?? { id, aliases: [], german: [], canonical: [], isomeric: [], cas: [], keys: [] };
    items.set(id, it);
    if (kind === "l") it.label = v;
    else ({ a: it.aliases, c: it.canonical, i: it.isomeric, r: it.cas, k: it.keys } as Record<string, string[]>)[kind]?.push(v);
  }
  process.stdout.write(`\rWikidata: ${Math.min(all.length, (b + 1) * BATCH)} of ${all.length}`);
}
console.log();
// German labels and aliases: ChemDraw reads many German names (Essigsäure, Kochsalz).
for (let b = 0; b * BATCH < all.length; b++) {
  const part = all.slice(b * BATCH, (b + 1) * BATCH);
  const rows = await sparql(`german-${b}-${part.length}.csv`, `SELECT ?item ?v WHERE { VALUES ?item { ${part.map((q) => `wd:${q}`).join(" ")} }
    { ?item rdfs:label ?v } UNION { ?item skos:altLabel ?v } FILTER(LANG(?v) = "de") }`);
  for (const [uri, v] of rows) { const it = items.get(qid(uri ?? "") ?? ""); if (it && v) it.german.push(v); }
  process.stdout.write(`\rWikidata, German names: ${Math.min(all.length, (b + 1) * BATCH)} of ${all.length}`);
}
console.log();
// Brands with one active ingredient: the brand's name is a name of the ingredient.
const brands = new Map<string, { label: string; ingredients: Set<string> }>();
for (const [brand, label, ingredient] of await sparql("brands.csv", `SELECT ?brand ?label ?ingredient WHERE { ?brand wdt:P3781 ?ingredient . ?brand rdfs:label ?label . FILTER(LANG(?label) = "en") }`)) {
  const b = qid(brand ?? ""), i = qid(ingredient ?? "");
  if (!b || !i || !label) continue;
  const x = brands.get(b) ?? { label, ingredients: new Set<string>() };
  brands.set(b, x);
  x.ingredients.add(i);
}
let branded = 0;
for (const { label, ingredients } of brands.values()) {
  const it = ingredients.size === 1 ? items.get([...ingredients][0]) : undefined;
  if (it && label !== it.label) { it.aliases.push(label); branded++; }
}
console.log(`brands: ${branded} brand names of one active ingredient`);

// ——— OPSIN and Indigo ———
const dir = new URL("../src/vendor/opsin/", import.meta.url);
const pack = readFileSync(new URL("opsin-data.bin", dir));
const files = new Map<string, Int8Array>();
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
const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();
function convert(s: string, format: string): string | undefined {
  const o = new indigo.MapStringString();
  try { return indigo.convert(s, format, o).trim() || undefined; } catch { return undefined; } finally { o.delete(); }
}
const opsinSmiles = (name: string): string | undefined => { try { return opsin.parseToSmiles(name) ?? undefined; } catch { return undefined; } };
// The first block of the InChIKey (the bonds) of a structure's largest part: a salt and its parent share it.
const skeleton = (smiles: string) => convert(smiles.split(".").sort((a, b) => b.length - a.length)[0], "inchi-key")?.slice(0, 14);

// ——— PubChem, the referee ———
// PubChem's first compound for a name or CAS number: its InChIKey and SMILES. Undefined where PubChem has none.
let lastAsk = 0;
type Answer = { key: string; smiles: string } | undefined;
async function pubchem(text: string): Promise<Answer> {
  const file = cached(`pubchem/${encodeURIComponent(text).slice(0, 200)}.json`);
  if (!existsSync(file)) {
    mkdirSync(cached("pubchem"), { recursive: true });
    // PubChem asks for no more than five requests a second.
    const at = Math.max(Date.now(), lastAsk + 220);
    lastAsk = at;
    if (at > Date.now()) await new Promise((ok) => setTimeout(ok, at - Date.now()));
    let body: string | undefined;
    for (let attempt = 1; attempt <= 3 && body === undefined; attempt++) {
      try {
        const r = await fetch("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/property/InChIKey,SMILES/JSON", { method: "POST", headers: { "User-Agent": AGENT, "Content-Type": "application/x-www-form-urlencoded" }, body: `name=${encodeURIComponent(text)}` });
        body = r.ok ? await r.text() : r.status === 404 ? "{}" : undefined;
      } catch { body = undefined; }
      if (body === undefined) await new Promise((ok) => setTimeout(ok, 3000 * attempt));
    }
    if (body === undefined) return undefined;
    writeFileSync(file, body);
  }
  const first = (JSON.parse(readFileSync(file, "utf8")) as { PropertyTable?: { Properties?: { InChIKey?: string; SMILES?: string }[] } }).PropertyTable?.Properties?.[0];
  return first?.InChIKey && first.SMILES ? { key: first.InChIKey, smiles: first.SMILES } : undefined;
}
// PubChem's answers for many names, four at a time (each still waits its turn above).
async function pubchemAll(texts: string[], progress: (done: number) => void): Promise<Answer[]> {
  const out: Answer[] = new Array(texts.length);
  let next = 0, done = 0;
  await Promise.all(Array.from({ length: 4 }, async () => {
    while (next < texts.length) { const i = next++; out[i] = await pubchem(texts[i]); if (++done % 50 === 0) progress(done); }
  }));
  return out;
}
// Whether PubChem's compound for a name is this one, or its salt or parent.
const agrees = (a: Answer, e: Entry) => !!a && (a.key.slice(0, 14) === e.key.slice(0, 14) || skeleton(a.smiles) === skeleton(e.smiles));

// ——— Each compound's structure ———
// The isomeric SMILES where there is one, else the canonical. Where Wikidata gives an InChIKey, the SMILES whose key
// matches it; where none matches, one with the same connectivity (the key's first block). No key and two different
// structures: the compound is left out.
type Entry = { id: string; smiles: string; key: string; names: string[]; cas: string[]; suggest: string[] };
const entries: Entry[] = [];
let noStructure = 0, conflicting = 0;
for (const it of items.values()) {
  const tried = [...new Set([...it.isomeric, ...it.canonical])].map((s) => s.trim()).filter((s) => s.length <= 2000 && !/\s/.test(s)).map((s) => ({ s, key: convert(s, "inchi-key") })).filter((t) => t.key);
  if (!tried.length) { noStructure++; continue; }
  const wanted = it.keys.filter((k) => /^[A-Z]{14}-[A-Z]{10}-[A-Z]$/.test(k));
  let pick = wanted.length ? tried.find((t) => wanted.includes(t.key!)) ?? tried.find((t) => wanted.some((k) => k.slice(0, 14) === t.key!.slice(0, 14))) : tried[0];
  if (!wanted.length && new Set(tried.map((t) => t.key!.slice(0, 14))).size > 1) pick = undefined;
  if (!pick) { conflicting++; continue; }
  // Wikidata's own SMILES, which Indigo has read. Plain SMILES only: Name to Structure joins structures with "." (a
  // salt, a list), so a CXSMILES part (" |c:13|") cannot go in.
  const smiles = pick.s.trim();
  if (/\s/.test(smiles)) { noStructure++; continue; }
  entries.push({ id: it.id, smiles, key: pick.key!, names: [it.label ?? "", ...it.aliases, ...it.german].filter(Boolean), cas: [...new Set(it.cas.filter(casValid))], suggest: [] });
}
console.log(`structures: ${entries.length} (${noStructure} unreadable, ${conflicting} with SMILES that disagree with their InChIKey)`);

// ——— Names ———
// Kept: names a chemist types. Left out: names over 80 characters, molecular formulas (C6H6 has more than one
// structure), formulas with charges or subscripts (Zn2+, As₂O₃), atomic numbers with symbols (11Na), SMILES, InChI,
// InChIKeys, CAS and EC numbers, registry codes (UNII), and bare numbers. Greek letters also go spelt out (α-pinene,
// alpha-pinene), and ® and ™ go.
const GREEK: Record<string, string> = { α: "alpha", β: "beta", γ: "gamma", δ: "delta", ε: "epsilon", κ: "kappa", λ: "lambda", μ: "mu", ω: "omega" };
const formula = (s: string) => /^(?:[A-Z][a-z]?\d*)+$/.test(s) && [...s.matchAll(/[A-Z][a-z]?/g)].every(([e]) => ELEMENTS.has(e));
function usable(raw: string): string[] {
  const s = raw.replace(/[®™]/g, "").replace(/−/g, "-").replace(/\s+/g, " ").trim();
  if (s.length < 3 || s.length > 80 || formula(s.replace(/[·.]/g, "")) || looksLikeSmiles(s) || /^InChI=/i.test(s) || /^[A-Z]{14}-[A-Z]{10}-[A-Z]$/.test(s)) return [];
  if (/^\d{2,7}-\d\d-\d$/.test(s) || /^\d{3}-\d{3}-\d$/.test(s) || /^\d[\d\s.,-]*$/.test(s) || (/^[A-Z0-9]{10}$/.test(s) && /\d/.test(s) && /[A-Z]/.test(s))) return [];
  if (/[<>{}|\t\n\\!]|https?:|[₀-₉⁰-⁹¹²³]/.test(s) || /^\d+[A-Z][a-z]?$/.test(s) || /^[A-Z][a-z]?\d*[+-]+$/.test(s)) return [];
  // Spelt without Greek letters or umlauts too (Essigsaeure), as a keyboard types it.
  const spelt = s.replace(/[αβγδεκλμω]/g, (g) => GREEK[g]), plain = spelt.replace(/[äöüÄÖÜß]/g, (u) => UMLAUT[u]);
  return [...new Set([s, spelt, plain])];
}
const UMLAUT: Record<string, string> = { ä: "ae", ö: "oe", ü: "ue", Ä: "Ae", Ö: "Oe", Ü: "Ue", ß: "ss" };
// A name easily meant as something else: a short code ("TEN", "5-APA"), or an English word or its plural ("salt",
// "beans", "spirits").
function risky(name: string): boolean {
  const lower = name.toLowerCase(), last = lower.split(" ").pop()!;
  if (name.length <= 5 || (/^[A-Z0-9-]+$/.test(name) && name.length <= 8)) return true;
  if (!/^[a-z ]+$/.test(lower)) return false;
  return WORDS.has(lower) || (last.endsWith("s") && (WORDS.has(last.slice(0, -1)) || (last.endsWith("ies") && WORDS.has(`${last.slice(0, -3)}y`))));
}
// Octet's own names, asked before the dictionary.
const own = new Set([...Object.keys(COMMON), ...Object.keys(DRUGS)].map(commonKey));
let opsinSame = 0, opsinStereo = 0, ownShadow = 0;
// Names OPSIN reads as a compound with other bonds than Wikidata's (tropicamide as an amide of tropic acid), and names
// that may mean something else.
const differs: { name: string; e: Entry; opsin: string }[] = [], doubtful: { name: string; e: Entry }[] = [];
for (const e of entries) {
  const kept: string[] = [], label = e.names[0];
  for (const name of e.names.flatMap(usable)) {
    const k = commonKey(name);
    if (own.has(k)) { ownShadow++; continue; }
    if (kept.some((n) => commonKey(n) === k)) continue;
    const read = opsinSmiles(name);
    if (read) {
      const key = convert(read, "inchi-key") ?? "";
      if (key === e.key) opsinSame++;
      else if (key.slice(0, 14) === e.key.slice(0, 14)) opsinStereo++;
      else differs.push({ name, e, opsin: key });
      // The compound's own name, and a short name without locants, when OPSIN reads it as this compound, is kept for
      // suggestions only ("benzaldehide" to benzaldehyde, "acetylsalicilic acid" to acetylsalicylic acid).
      if ((name === label && name.length <= 40) || (key === e.key && name.length <= 30 && !/[\d(),[\]]/.test(name))) e.suggest.push(name);
      continue;
    }
    if (risky(name)) { doubtful.push({ name, e }); continue; }
    kept.push(name);
  }
  e.names = kept;
}
console.log(`names: ${opsinSame} read by OPSIN as the same structure, ${opsinStereo} the same but for stereo or charge (OPSIN reads what the name says), ${differs.length} as another; ${doubtful.length} to confirm; ${ownShadow} in common.ts or drugs.ts`);
// Where OPSIN reads a name as another compound, PubChem decides. Where PubChem's compound has Wikidata's bonds and
// not OPSIN's, the name is read from the dictionary before OPSIN ("!" before it in the table). Otherwise OPSIN keeps it.
// A compound with a metal, or with an atom Wikidata draws bare in brackets (a radical, or a hydride without its H:
// pinacolborane as [B]), is not overruled: OPSIN draws it as Octet draws such compounds (sec-butyllithium bonded, not
// as ions), which is a drawing of the same compound.
const metal = (smiles: string) => [...smiles.matchAll(/\[([A-Z][a-z]?)/g)].some(([, el]) => !NONMETAL.has(el)) || /\[(B|C|N|O|Si|P|S)\]/.test(smiles);
const overruled: string[] = [];
const differAnswers = await pubchemAll(differs.map((d) => d.name), (n) => process.stdout.write(`\rOPSIN's other readings: ${n} of ${differs.length} asked`));
for (const [i, d] of differs.entries()) {
  const a = differAnswers[i];
  if (a && agrees(a, d.e) && a.key.slice(0, 14) !== d.opsin.slice(0, 14) && !metal(d.e.smiles)) {
    d.e.names.push(`!${d.name}`);
    overruled.push(`${d.name}\t${d.e.id}\twikidata ${d.e.key}\tpubchem ${a.key}\topsin ${d.opsin}`);
  }
}
writeFileSync(cached("opsin-overruled.tsv"), overruled.join("\n") + "\n");
console.log(`\rOPSIN's other readings: ${overruled.length} of ${differs.length} overruled (PubChem has Wikidata's compound)`);
let confirmed = 0;
const doubtAnswers = await pubchemAll(doubtful.map((d) => d.name), (n) => process.stdout.write(`\rnames to confirm: ${n} of ${doubtful.length} asked`));
for (const [i, d] of doubtful.entries()) if (agrees(doubtAnswers[i], d.e)) { d.e.names.push(d.name); confirmed++; }
console.log(`\rnames to confirm: ${confirmed} of ${doubtful.length} confirmed by PubChem`);

// A name two compounds share: kept for the one PubChem gives for it (or its salt or parent), if PubChem gives one.
const nameOf = (n: string) => n.replace(/^!/, "");
const byName = new Map<string, Set<Entry>>();
for (const e of entries) for (const n of e.names) byName.set(commonKey(nameOf(n)), (byName.get(commonKey(nameOf(n))) ?? new Set()).add(e));
const clashes = [...byName].filter(([, set]) => new Set([...set].map((e) => e.key)).size > 1);
let resolved = 0;
for (const [i, [k, set]] of clashes.entries()) {
  const options = [...set], name = nameOf(options[0].names.find((n) => commonKey(nameOf(n)) === k)!), a = await pubchem(name);
  const winner = a && (options.find((e) => e.key === a.key) ?? options.find((e) => e.key.slice(0, 14) === a.key.slice(0, 14)));
  for (const e of options) if (e !== winner) e.names = e.names.filter((n) => commonKey(nameOf(n)) !== k);
  if (winner) resolved++;
  if (i % 50 === 0) process.stdout.write(`\rshared names: ${i} of ${clashes.length} asked`);
}
console.log(`\rshared names: ${resolved} of ${clashes.length} kept for PubChem's compound`);
const byCas = new Map<string, Entry[]>();
for (const e of entries) for (const c of e.cas) byCas.set(c, [...(byCas.get(c) ?? []), e]);
const casClashes = [...byCas].filter(([, es]) => new Set(es.map((e) => e.key)).size > 1);
let casResolved = 0;
for (const [c, options] of casClashes) {
  const a = await pubchem(c), winner = a && options.find((e) => e.key === a.key);
  for (const e of options) if (e !== winner) e.cas = e.cas.filter((x) => x !== c);
  if (winner) casResolved++;
}
console.log(`shared CAS numbers: ${casResolved} of ${casClashes.length} kept for PubChem's compound`);

// ——— The table ———
// One compound a line: SMILES, names (| between; "!" before a name read before OPSIN), CAS numbers (| between),
// InChIKey, and names OPSIN reads (for suggestions only), tab-separated. Two compounds with one structure are one line.
const lines = new Map<string, Entry>();
for (const e of entries) {
  const same = lines.get(e.key);
  if (same) for (const f of ["names", "cas", "suggest"] as const) same[f] = [...new Set([...same[f], ...e[f]])];
  else lines.set(e.key, e);
}
const kept = [...lines.values()].sort((a, b) => Number(a.id.slice(1)) - Number(b.id.slice(1)));
const text = kept.map((e) => [e.smiles, e.names.join("|"), e.cas.join("|"), e.key, e.suggest.join("|")].join("\t").trimEnd()).join("\n") + "\n";
const out = new URL("../data/names/", import.meta.url);
mkdirSync(out, { recursive: true });
const zipped = gzipSync(text, { level: 9 });
writeFileSync(new URL("dictionary.tsv.gz", out), zipped);
const nameCount = kept.reduce((n, e) => n + e.names.length, 0), casCount = kept.reduce((n, e) => n + e.cas.length, 0), first = kept.reduce((n, e) => n + e.names.filter((x) => x.startsWith("!")).length, 0);
console.log(`dictionary: ${kept.length} compounds, ${nameCount} names (${first} read before OPSIN), ${casCount} CAS numbers; ${(text.length / 1e6).toFixed(2)} MB, ${(zipped.length / 1e6).toFixed(2)} MB gzipped`);

// ——— The check against PubChem ———
// Random names from the table (the same ones each run) until PubChem knows that many, each with PubChem's structure for
// the name: the same InChIKey, the same bonds but other stereo or isotopes, the same compound but as a salt or its
// parent (the largest part is the same), or another compound.
if (flag === "--check") {
  const n = Number(count ?? 200), named = kept.flatMap((e) => e.names.map((name) => ({ name: nameOf(name), e })));
  let seed = 7;
  const random = () => { seed = (seed * 1103515245 + 12345) % 2 ** 31; return seed / 2 ** 31; };
  let whole = 0, stereo = 0, salt = 0, asked = 0, missing = 0;
  const differ: string[] = [], seen = new Set<number>();
  while (asked < n && seen.size < named.length && seen.size < 10 * n) {
    const i = Math.floor(random() * named.length);
    if (seen.has(i)) continue;
    seen.add(i);
    const { name, e } = named[i], a = await pubchem(name);
    if (!a) { missing++; continue; }
    asked++;
    if (a.key === e.key) whole++;
    else if (a.key.slice(0, 14) === e.key.slice(0, 14)) { stereo++; differ.push(`stereo\t${name}\t${e.id}\t${e.smiles}\tpubchem ${a.smiles}`); }
    else if (skeleton(a.smiles) === skeleton(e.smiles)) { salt++; differ.push(`salt\t${name}\t${e.id}\t${e.smiles}\tpubchem ${a.smiles}`); }
    else differ.push(`other\t${name}\t${e.id}\t${e.smiles}\tpubchem ${a.smiles}`);
  }
  writeFileSync(cached("check-differs.tsv"), differ.join("\n") + "\n");
  console.log(`check: ${asked} random names PubChem knows (${missing} it does not): ${whole} the same structure, ${stereo} the same but for stereo or isotopes, ${salt} a salt where the other has the parent (or the reverse), ${asked - whole - stereo - salt} another compound (see check-differs.tsv)`);
}
