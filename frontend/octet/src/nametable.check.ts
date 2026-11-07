// Run: node src/nametable.check.ts. The dictionary's small tables (src/nametable.ts): they give what a table of strings
// gives (a Map for each name key, CAS number and InChIKey, the first one kept; names marked "!" last; each name once in
// lower case for suggestions, with its trigrams), on hand-made lines and on the real dictionary, and they read the real
// dictionary in less than half the time the strings take, measured in the same run.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { commonKey } from "./common.ts";
import { NameTable } from "./nametable.ts";

// The tables as strings, as Octet 1.1.0 kept them.
function strings(text: string) {
  const smiles: string[] = [], names = new Map<string, number>(), first = new Map<string, number>(), cas = new Map<string, number>(), keys = new Map<string, number>();
  const shown = new Map<string, [string, number]>(), show = (name: string, n: number) => { const l = name.toLowerCase(); if (!shown.has(l)) shown.set(l, [name, n]); };
  for (const line of text.split("\n")) {
    const [s, ns, cs, key, read] = line.split("\t");
    if (!s || s.length > 4000) continue;
    const n = smiles.push(s) - 1;
    for (const raw of ns ? ns.split("|") : []) {
      const name = raw.replace(/^!/, ""), k = commonKey(name);
      if (raw !== name) first.set(k, n);
      if (k && !names.has(k)) { names.set(k, n); show(name, n); }
    }
    for (const c of cs ? cs.split("|") : []) if (!cas.has(c)) cas.set(c, n);
    if (key && !keys.has(key)) keys.set(key, n);
    for (const name of read ? read.split("|") : []) show(name, n);
  }
  const grams = new Map<string, number[]>(), lower: string[] = [];
  for (const [low] of shown) {
    const i = lower.push(low) - 1, t = ` ${low} `;
    for (let j = 0; j + 3 <= t.length; j++) { const g = t.slice(j, j + 3), l = grams.get(g); if (l) l.push(i); else grams.set(g, [i]); }
  }
  return { smiles, names, first, cas, keys, shown: [...shown.values()], lower, grams };
}

// Every name, CAS number, InChIKey and trigram gives the same answer.
async function same(text: string, what: string) {
  const s = strings(text), t = await NameTable.read(new TextEncoder().encode(text), false);
  await t.suggested;
  for (const [k, n] of s.names) assert.equal(t.smiles(t.nameCompound(k)), s.smiles[n], `${what}: name ${k}`);
  for (const [k, n] of s.first) if (k) assert.equal(t.smiles(t.nameCompound(k, true)), s.smiles[n], `${what}: marked ${k}`);
  for (const [k, n] of s.cas) assert.equal(t.smiles(t.casCompound(k)), s.smiles[n], `${what}: CAS ${k}`);
  for (const [k, n] of s.keys) assert.equal(t.smiles(t.keyCompound(k)), s.smiles[n], `${what}: InChIKey ${k}`);
  assert.equal(t.size, s.shown.length, `${what}: names for suggestions`);
  s.shown.forEach(([name, n], i) => { assert.equal(t.written(i), name); assert.equal(t.lower(i), s.lower[i]); assert.equal(t.compound(i), n); });
  for (const [g, list] of s.grams) assert.deepEqual([...t.withGram(g)], list, `${what}: trigram "${g}"`);
  return t;
}

// Hand-made lines: the first compound keeps a name, a CAS number and an InChIKey; a name marked "!" goes to the last
// one; spaces, hyphens, apostrophes and case do not count, and a full stop is "·"; accents and Greek are read as
// strings; a line with no SMILES is left out; a name has a trigram twice; names far apart give a long varint gap.
const many = Array.from({ length: 20000 }, (_, i) => `C${"C".repeat(i % 5)}\tfiller ${i}\t\t\t`).join("\n");
const lines = [
  "CCO\tEthanol|ethyl alcohol|!grain spirit\t64-17-5\tLFQSCWFLJHTTHZ-UHFFFAOYSA-N\tethanol|hydroxyethane",
  "CC(C)O\tisopropanol|Ethanol\t67-63-0|64-17-5\tKFZMGEQAYNKOFK-UHFFFAOYSA-N\t",
  "\tno smiles\t1-1-1\t\t",
  "CN\tmethyl amine|N-methyl-amine|Et3N.HCl|!grain spirit\t74-89-5\tBAVYZALUXZFZLV-UHFFFAOYSA-N\tbanana banana",
  "O=C=O\tcarbon dioxide|β-carotène|Ålesund's gas\t124-38-9\tCURLTUGMZLYLDI-UHFFFAOYSA-N\t",
  many,
  "C1CC1\tcyclopropane|BANANA\t75-19-4\t\tcyclopropane",
].join("\n");
const t = await same(lines, "hand-made");
assert.equal(t.smiles(t.nameCompound(commonKey("ETHANOL"))), "CCO", "the first compound keeps a name");
assert.equal(t.smiles(t.nameCompound(commonKey("Grain Spirit"), true)), "CN", "a marked name goes to the last line that marks it");
assert.equal(t.smiles(t.nameCompound(commonKey("methylamine"))), "CN", "spaces and hyphens do not count");
assert.equal(t.smiles(t.nameCompound(commonKey("Et3N·HCl"))), "CN", "a full stop is ·");
assert.equal(t.smiles(t.nameCompound(commonKey("β-CAROTÈNE"))), "O=C=O");
assert.equal(t.smiles(t.casCompound("64-17-5")), "CCO", "the first compound keeps a CAS number");
assert.equal(t.casCompound("1-1-1"), -1, "a line with no SMILES is left out");
assert.equal(t.nameCompound(commonKey("no such name")), -1);
assert.equal(t.nameCompound(""), -1);
assert.equal([...t.withGram(" ba")].length, 3, "banana banana has the trigram twice, BANANA once");

// The real dictionary: the same answers as strings, and read in less than half their time (both measured now).
const file = new URL("../data/names/dictionary.tsv.gz", import.meta.url);
if (existsSync(file)) {
  const text = gunzipSync(readFileSync(file)).toString("utf8"), bytes = new TextEncoder().encode(text);
  await same(text, "dictionary");
  const time = (f: () => unknown) => { const t0 = performance.now(); f(); return performance.now() - t0; };
  const old: number[] = [], now: number[] = [];
  for (let k = 0; k < 3; k++) {
    old.push(time(() => strings(text)));
    const t0 = performance.now();
    await NameTable.read(bytes, false);
    now.push(performance.now() - t0);
  }
  const median = (a: number[]) => a.sort((x, y) => x - y)[1];
  assert.ok(median(now) < median(old) / 2, `the small tables read in ${Math.round(median(now))} ms, the strings in ${Math.round(median(old))} ms`);
  console.log(`nametable.check: ok (the dictionary in ${Math.round(median(now))} ms; as strings ${Math.round(median(old))} ms)`);
} else console.log("nametable.check: ok (no dictionary)");
