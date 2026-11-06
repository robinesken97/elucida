import assert from "node:assert/strict";
import { putAsset, readAsset } from "./elucida-assets.ts";
import { EMPTY } from "./edit.ts";
import { readOct, writeOct, readCdx, writeCdx } from "./oct.ts";
import { DEFAULT_STYLE as ACS1996 } from "./docstyle.ts";

const asset = {key:"synthetic-profile", kind:"profile" as const, png:"89504E470D0A1A0A", width:300, height:200,
  svg:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200"><path d="M0 0L300 200"/></svg>'};
const added = putAsset(EMPTY, asset, 14.4);
const before = structuredClone(added.mol);
const changed = putAsset(added.mol, {...asset, key:"revision2", width:500}, 14.4, added.id);
assert.deepEqual(added.mol, before);
assert.deepEqual(changed.mol.shapes![0].from, added.mol.shapes![0].from);
assert.deepEqual(changed.mol.shapes![0].to, added.mol.shapes![0].to);
assert.equal(changed.mol.shapes!.length,1);
for (const restored of [readOct(writeOct(changed.mol, ACS1996)), readCdx(writeCdx(changed.mol, ACS1996))]) {
  assert.equal(restored.mol.shapes![0].elucida?.key,"revision2");
  assert.equal(restored.mol.shapes![0].elucida?.svg,asset.svg);
  assert.deepEqual(restored.lost,{});
}
assert.equal(readAsset({key:"../../secret",kind:"orbital"}),undefined);
assert.throws(()=>putAsset(EMPTY,asset,14.4,1));
assert.throws(()=>putAsset(EMPTY,{...asset,width:NaN},14.4));
console.log("elucida-assets.check: placement, update, portable vector payload and fallback ok");
