// Octet's CIP labels (src/cip.ts) against the CIP validation suite of Hanson, Mayfield, Vainio, Yerin, Musacchio and
// Redkin (J. Chem. Inf. Model. 2018; github.com/CIPValidationSuite/ValidationSuite). The suite has no licence, so it
// is not in this repository: keep compounds_2d.sdf in ~/octet-research/data/cip-validation-suite (or name the file
// in CIP_SUITE). The script skips when the file is missing.
// Run: node scripts/cip-suite.ts [--list]. Prints the cases passed by sequence rule, and with --list each failure.
// Helical and axial labels (M, P) are left out: Octet gives those in src/axial.ts, not here.
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { cipLabels } from "../src/cip.ts";
import type { Mol } from "../src/render.ts";

const file = process.env.CIP_SUITE ?? `${homedir()}/octet-research/data/cip-validation-suite/compounds_2d.sdf`;
if (!existsSync(file)) { console.log("cip-suite: skipped (no suite file)"); process.exit(0); }
const list = process.argv.includes("--list");

// A V2000 record as drawn: atoms, charges, isotopes, bonds with their wedges (1 wedge, 6 hash; 4 wavy).
function read(record: string): { id: string; mol: Mol; fields: Record<string, string> } {
  const lines = record.split("\n"), na = Number(lines[3].slice(0, 3)), nb = Number(lines[3].slice(3, 6));
  const mol: Mol = { atoms: [], bonds: [] };
  for (let i = 0; i < na; i++) {
    const l = lines[4 + i];
    mol.atoms.push({ label: l.slice(31, 34).trim(), location: [Number(l.slice(0, 10)), Number(l.slice(10, 20)), Number(l.slice(20, 30))] });
  }
  for (let i = 0; i < nb; i++) {
    const l = lines[4 + na + i], a = Number(l.slice(0, 3)) - 1, b = Number(l.slice(3, 6)) - 1, type = Number(l.slice(6, 9)), st = Number(l.slice(9, 12));
    mol.bonds.push({ type, atoms: [a, b], ...(type === 1 && (st === 1 || st === 6) ? { stereo: st } : {}), ...(type === 1 && st === 4 ? { display: "wavy" as const } : {}), ...(type === 2 && st === 3 ? { display: "either" as const } : {}) });
  }
  for (const l of lines) {
    const m = /^M {2}(CHG|ISO)(.*)$/.exec(l);
    if (!m) continue;
    const v = m[2].trim().split(/\s+/).map(Number);
    for (let k = 1; k + 1 < v.length; k += 2) { const a = mol.atoms[v[k] - 1]; if (m[1] === "CHG") a.charge = v[k + 1]; else a.isotope = v[k + 1]; }
  }
  const fields: Record<string, string> = {};
  for (const m of record.matchAll(/^>\s*<(\w+)>\n([^\n]*)/gm)) fields[m[1]] = m[2].trim();
  return { id: lines[0].trim(), mol, fields };
}

const byRule = new Map<string, [number, number]>(), fails: string[] = [];
let pass = 0, total = 0, time = 0;
for (const record of readFileSync(file, "utf8").split("$$$$\n").filter((r) => r.trim())) {
  const { id, mol, fields } = read(record);
  const want = new Set((fields.CIP_LABELS ?? "").split(/\s+/).filter((x) => x && !/[MPmp]$/.test(x)).map((x) => x.replace(/[ez]$/, (c) => c.toUpperCase())));
  const t = performance.now(), cip = cipLabels(mol);
  time += performance.now() - t;
  const got = new Set<string>();
  cip.atoms.forEach((c, i) => { if (c) got.add(`${i + 1}${c}`); });
  // The suite labels a double bond on its two atoms, and a cumulene (labelled on its middle bond) on its two ends.
  const cumulated = (i: number) => { const bs = mol.bonds.filter((b) => b.atoms.includes(i)); return bs.length === 2 && bs.every((b) => b.type === 2); };
  const end = (i: number, from: number) => {
    for (let guard = 0; cumulated(i) && guard < mol.atoms.length; guard++) { const b = mol.bonds.find((x) => x.atoms.includes(i) && !x.atoms.includes(from))!; from = i; i = b.atoms[0] === i ? b.atoms[1] : b.atoms[0]; }
    return i;
  };
  cip.bonds.forEach((c, k) => { if (c) { const [a, b] = mol.bonds[k].atoms; for (const i of [end(a, b), end(b, a)]) got.add(`${i + 1}${c}`); } });
  const ok = got.size === want.size && [...want].every((x) => got.has(x));
  total++;
  if (ok) pass++;
  const rules = (fields.SEQUENCE_RULES ?? "").split(",").filter(Boolean);
  for (const r of rules.length ? rules : ["none"]) { const e = byRule.get(r) ?? [0, 0]; e[1]++; if (ok) e[0]++; byRule.set(r, e); }
  if (!ok) fails.push(`${id} [${fields.SEQUENCE_RULES ?? ""}] want ${[...want].sort().join(" ") || "-"} got ${[...got].sort().join(" ") || "-"}`);
}
console.log(`cip-suite: ${pass} of ${total} cases pass (${time.toFixed(0)} ms)`);
for (const [r, [p, n]] of [...byRule].sort()) console.log(`  rule ${r.padEnd(4)} ${p} of ${n}`);
if (list) for (const f of fails) console.log(f);
