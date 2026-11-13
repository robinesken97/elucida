// Run: node src/gridview.check.ts. The reagent table's keys move from cell to cell as a spreadsheet's do (gridStep).
import assert from "node:assert/strict";
import { gridStep } from "./gridview.ts";

// As columns: three rows of two cells (y is up). As rows: a line's cells are not in line with the next line's.
const cols = [0, 1, 2].flatMap((r) => ["a", "b"].map((k, i) => ({ key: k, row: `r${r}`, x: i * 2, y: -r })));
const at = (key: string, row: string) => ({ key, row });
const to = (c?: { key: string; row: string }) => c && `${c.key} ${c.row}`;
assert.equal(to(gridStep(cols, at("a", "r0"), "right")), "b r0");
assert.equal(to(gridStep(cols, at("b", "r0"), "right")), "b r0", "stays at the edge");
assert.equal(to(gridStep(cols, at("b", "r0"), "down")), "b r1");
assert.equal(to(gridStep(cols, at("b", "r2"), "down")), "b r2");
assert.equal(to(gridStep(cols, at("a", "r1"), "up")), "a r0");
assert.equal(to(gridStep(cols, at("b", "r0"), "next")), "a r1", "Tab goes on to the next line");
assert.equal(to(gridStep(cols, at("a", "r1"), "back")), "b r0");
assert.equal(to(gridStep(cols, at("b", "r2"), "next")), "b r2");
const rows = [{ key: "a", row: "name", x: 0, y: 0 }, { key: "a", row: "mass", x: 3, y: 0 }, { key: "b", row: "name", x: 0.4, y: -1 }, { key: "b", row: "mass", x: 2.6, y: -1 }];
assert.equal(to(gridStep(rows, at("a", "mass"), "down")), "b mass", "down goes to the nearest cell in the next line");
assert.equal(to(gridStep(rows, at("b", "name"), "up")), "a name");
assert.equal(gridStep(rows, at("c", "mass"), "down"), undefined);
console.log("gridview.check: ok");
