// Run: node src/namer-locants.check.ts. Show atom numbers numbers a structure's parent chain or ring as its IUPAC
// name does (iupacLocants), not in the order its atoms were drawn (a Reddit user, 2 November 2026).
import assert from "node:assert/strict";
import { iupacLocants } from "./namer.ts";
import type { Graph } from "./naming.ts";

const C = (h: number, el = "C") => ({ el, charge: 0, h });
const bond = (a: number, b: number, order: 1 | 2 | 3 = 1) => ({ a, b, order });

// 3-Methylcyclopent-1-ene: the double bond takes 1 and 2, then the methyl the lowest locant, 3. The methyl's own C has
// none. Drawn with the methyl's carbon first, so drawing order is no help.
const methylcyclopentene: Graph = { atoms: [C(3), C(1), C(1), C(1), C(2), C(2)], bonds: [bond(0, 3), bond(1, 2, 2), bond(2, 3), bond(3, 4), bond(4, 5), bond(5, 1)] };
assert.deepEqual(iupacLocants(methylcyclopentene), [undefined, "1", "2", "3", "4", "5"]);

// Pentan-2-one: the chain from the end nearer the ketone.
const pentanone: Graph = { atoms: [C(3), C(2), C(2), C(0), C(3), C(0, "O")], bonds: [bond(0, 1), bond(1, 2), bond(2, 3), bond(3, 4), bond(3, 5, 2)] };
assert.deepEqual(iupacLocants(pentanone), ["5", "4", "3", "2", "1", undefined]);

// An H drawn as an atom is folded into its carbon and has no locant: ethanol with one H drawn.
const ethanol: Graph = { atoms: [C(2), C(2), C(1, "O"), C(0, "H")], bonds: [bond(0, 1), bond(1, 2), bond(0, 3)] };
assert.deepEqual(iupacLocants(ethanol), ["2", "1", undefined, undefined]);

// Two structures at once have no one numbering.
assert.equal(iupacLocants({ atoms: [C(4), C(4)], bonds: [] }), undefined);
console.log("namer-locants.check: ok");
