// Run: node src/flatpak.check.ts. The Flatpak for testers on Linux (issue 37) stays in step with the app and its build:
// its id is the app's identifier (a second launch finds the first on D-Bus by that name, and Flatpak shows only the
// files named for it), it copies the files by the names Tauri gives them in the .deb, release.yml builds it on the
// runtime's own GNOME version, and it asks for no file access, as files come through the system's portal.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const conf = JSON.parse(read("../src-tauri/tauri.conf.json"));
const manifest = read(`../src-tauri/linux/${conf.identifier}.yml`), release = read("../.github/workflows/release.yml");
const key = (k: string) => manifest.match(new RegExp(`^${k}: "?([^"\\n]+)"?$`, "m"))?.[1];

assert.equal(key("id"), conf.identifier);
assert.equal(key("command"), read("../src-tauri/Cargo.toml").match(/^name = "(.+)"$/m)?.[1], "the command is the program Cargo builds");
for (const file of [`usr/bin/${key("command")} `, `"usr/lib/${conf.productName}"`, `"usr/share/applications/${conf.productName}.desktop"`]) {
  assert.ok(manifest.includes(file), `the manifest copies ${file}`);
}
assert.equal(key("runtime"), "org.gnome.Platform", "the GNOME runtime has WebKitGTK");
assert.ok(release.includes(`flatpak-github-actions:gnome-${key("runtime-version")}@sha256:`), "the build image has the runtime's GNOME version");
assert.ok(release.includes(`manifest-path: src-tauri/linux/${conf.identifier}.yml`) && release.includes("path: src-tauri/linux/deb\n"), "release.yml builds the manifest with the .deb beside it");
// The window, the graphics card and the network, and nothing more.
assert.deepEqual([...manifest.matchAll(/^ {2}- (--\S+)/gm)].map((m) => m[1]), ["--socket=wayland", "--socket=fallback-x11", "--share=ipc", "--device=dri", "--share=network"]);

console.log("flatpak: ok");
