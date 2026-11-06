// Run: node src/version.check.ts. Octet's version is in package.json only (REL-9): tauri.conf.json reads it,
// Cargo.toml has none, and CDXML's CreationProgram is made from it.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (f: string) => readFileSync(new URL(`../${f}`, import.meta.url), "utf8");
const version = JSON.parse(read("package.json")).version;
assert.equal(JSON.parse(read("src-tauri/tauri.conf.json")).version, "../package.json");
assert.equal(JSON.parse(read("package-lock.json")).version, version, "package-lock.json has the same version");
const cargo = read("src-tauri/Cargo.toml"), pkg = cargo.slice(cargo.indexOf("[package]"), cargo.indexOf("\n[", cargo.indexOf("[package]")));
assert.ok(!/^version\s*=/m.test(pkg), "Cargo.toml has no version");
assert.match(read("src/cdxml.ts"), /PROGRAM = `Octet \$\{pkg\.version\}`/);
console.log("version.check: ok");
