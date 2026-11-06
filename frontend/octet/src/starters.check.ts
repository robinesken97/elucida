// Run: node src/starters.check.ts. Fails loudly if a Home starter drawing no longer opens, or its picture is unsafe.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parse } from "./file.ts";

for (const name of ["structure", "reaction", "cycle"]) {
  const mol = parse(readFileSync(new URL(`./starters/${name}.json`, import.meta.url), "utf8"));
  assert.ok(mol.atoms.length > 0, `${name} has atoms`);
  const svg = readFileSync(new URL(`./starters/${name}.svg`, import.meta.url), "utf8");
  assert.ok(svg.startsWith("<svg") && !/<script|foreignObject|href=/i.test(svg), `${name}'s picture is a plain SVG`);
}
const reaction = parse(readFileSync(new URL("./starters/reaction.json", import.meta.url), "utf8"));
assert.equal(reaction.arrows?.length, 1, "the reaction has its arrow");
assert.equal(reaction.captions?.filter((c) => c.on).length, 2, "and its conditions on the arrow");
const cycle = parse(readFileSync(new URL("./starters/cycle.json", import.meta.url), "utf8"));
assert.equal(cycle.cycles?.[0].nodes.length, 3, "the cycle has three intermediates");
console.log("starters.check: ok");
