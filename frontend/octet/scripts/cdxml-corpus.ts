// Run: node scripts/cdxml-corpus.ts [folder]. Reads every ChemDraw CDXML file in the folder (Sam's corpus by
// default; it stays on Sam's Mac and never enters this repository), writes each back with Octet's writer, reads
// that again, and reports per file what came in, what Octet could not hold, and anything the second pass lost.
// It also writes each drawing as CDX (decision 0009) and reads that back, as ChemDraw's file and as Octet's own.
import { readdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { fromCdxml, parseXml, toCdxml, type Xml } from "../src/cdxml.ts";
import { cdxToXml, xmlToCdx } from "../src/cdx.ts";
import { readCdx, writeCdx } from "../src/oct.ts";
import { parse, serialize } from "../src/file.ts";
import type { Mol } from "../src/render.ts";

const dir = process.argv[2] ?? join(homedir(), "octet-research/corpus/sam");

// Objects in the file as ChemDraw stores them: atoms outside abbreviations, bonds, text that is not an atom label,
// arrows (not their legacy copies), other graphics, curves and groups.
function census(root: Xml) {
  const n = { atoms: 0, bonds: 0, text: 0, arrows: 0, graphics: 0, curves: 0, groups: 0, steps: 0 };
  const walk = (x: Xml, inLabel: boolean) => {
    if (x.name === "n" && !inLabel) n.atoms++;
    if (x.name === "b" && !inLabel) n.bonds++;
    if (x.name === "t" && !inLabel) n.text++;
    if (x.name === "arrow") n.arrows++;
    if (x.name === "graphic" && !x.attrs.SupersededBy && !inLabel) n.graphics++;
    if (x.name === "curve") n.curves++;
    if (x.name === "group") n.groups++;
    if (x.name === "step") n.steps++;
    for (const k of x.kids) walk(k, inLabel || x.name === "n" || x.name === "objecttag");
  };
  walk(root, false);
  return n;
}

// Paths where two drawings differ, numbers compared to 0.002 bond lengths.
function diff(a: unknown, b: unknown, path = "", out: string[] = []): string[] {
  if (typeof a === "number" && typeof b === "number") { if (Math.abs(a - b) > 2e-3) out.push(`${path}: ${a} vs ${b}`); return out; }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) out.push(`${path}: ${a.length} items vs ${b.length}`);
    else a.forEach((x, k) => diff(x, b[k], `${path}[${k}]`, out));
    return out;
  }
  if (a && b && typeof a === "object" && typeof b === "object") {
    for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) diff((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k], `${path}.${k}`, out);
    return out;
  }
  if (a !== b) out.push(`${path}: ${JSON.stringify(a)} vs ${JSON.stringify(b)}`);
  return out;
}
// Groups in id order, and no groups as none: the list's order is not drawn (Octet writes groups in draw order).
const grouped = (m: Mol): Mol => ({ ...m, groups: m.groups?.length ? [...m.groups].sort((p, q) => p.id - q.id) : undefined });
const counts = (m: Mol) => `${m.atoms.length} atoms, ${m.bonds.length} bonds, ${m.captions?.length ?? 0} captions, ${m.arrows?.length ?? 0} arrows, ${m.shapes?.length ?? 0} shapes, ${m.groups?.length ?? 0} groups`;

// The tree without Octet's own data, as ChemDraw keeps it.
const foreign = (x: Xml): Xml => ({ ...x, attrs: Object.fromEntries(Object.entries(x.attrs).filter(([k]) => k !== "Octet")), kids: x.kids.map(foreign) });

let clean = 0, files = 0, cdxSame = 0;
for (const name of readdirSync(dir).filter((f) => f.endsWith(".cdxml")).sort()) {
  files++;
  const text = readFileSync(join(dir, name), "utf8"), started = performance.now();
  try {
    const first = fromCdxml(text), ms = performance.now() - started, c = census(parseXml(text));
    parse(serialize(first.mol)); // Octet's own file checks accept what was read
    const again = fromCdxml(toCdxml(first.mol, first.style, { name }));
    const changes = diff(grouped(first.mol), grouped(again.mol)), lost = Object.entries(first.lost).map(([k, v]) => `${v} ${k}`).join(", ");
    if (!changes.length && !Object.keys(again.lost).length) clean++;
    console.log(`\n${name}  (${ms.toFixed(0)} ms)`);
    console.log(`  file: ${c.atoms} atoms, ${c.bonds} bonds, ${c.text} texts, ${c.arrows} arrows, ${c.graphics} graphics, ${c.curves} curves, ${c.groups} groups, ${c.steps} steps`);
    console.log(`  read: ${counts(first.mol)}`);
    console.log(`  not held: ${lost || "nothing"}`);
    console.log(`  written and read again: ${changes.length ? `${changes.length} differences` : "the same"}${Object.keys(again.lost).length ? `, lost ${JSON.stringify(again.lost)}` : ""}`);
    for (const d of changes.slice(0, 8)) console.log(`    ${d}`);
    // As CDX: what ChemDraw sees (read as a foreign file, against the same CDXML read as one), and Octet's own .cdx.
    const tree = foreign(parseXml(toCdxml(first.mol, first.style, { name })));
    const viaCdxml = fromCdxml(tree), viaCdx = fromCdxml(cdxToXml(xmlToCdx(tree))), own = readCdx(writeCdx(first.mol, first.style, { name }));
    // Octet's own .cdx holds its file's JSON, which numbers objects afresh as .oct does.
    const cdxChanges = [...diff(viaCdxml.mol, viaCdx.mol), ...diff(parse(serialize({ ...first.mol, style: first.style })), own.mol)];
    if (!cdxChanges.length && JSON.stringify(viaCdx.lost) === JSON.stringify(viaCdxml.lost)) cdxSame++;
    console.log(`  as CDX: ${cdxChanges.length ? `${cdxChanges.length} differences` : "the same"}`);
    for (const d of cdxChanges.slice(0, 8)) console.log(`    ${d}`);
  } catch (e) {
    console.log(`\n${name}\n  FAILED: ${(e as Error).message}`);
  }
}
console.log(`\n${clean} of ${files} files write and read back unchanged; ${cdxSame} of ${files} read back the same as CDX.`);
