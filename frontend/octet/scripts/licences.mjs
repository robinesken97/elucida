// Writes src-tauri/licences/third-party.txt, the licence notices of everything the app ships (REL-12): the Rust
// crates in the binary on the Mac, Windows and Linux, the npm packages in the page, the libraries inside Indigo's
// WASM (src-tauri/licences/indigo-wasm.txt, written by hand), and OPSIN's, nmrshiftdb2's, Wikidata's and PubChem's notices. The app bundles the file and About > Licences opens it. Run it after a dependency changes:
//   node scripts/licences.mjs
// It needs cargo, and the crates' sources (cargo downloads them).
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const PLATFORMS = ["aarch64-apple-darwin", "x86_64-apple-darwin", "x86_64-pc-windows-msvc", "x86_64-unknown-linux-gnu"];
// Of a choice of licences ("MIT OR Apache-2.0"), Octet takes the first of these it can, so the notice is short.
const PREFER = ["MIT", "BSD-3-Clause", "BSD-2-Clause", "ISC", "Zlib", "0BSD", "Unlicense", "Apache-2.0", "Unicode-3.0", "MPL-2.0"];
const FILE = /^(licen[cs]e|copying|notice)/i;
// The licence a file name is for (LICENSE-MIT, LICENSE-APACHE, license-mit.md).
const FOR = [[/mit/i, "MIT"], [/apache/i, "Apache-2.0"], [/bsd/i, "BSD"], [/zlib/i, "Zlib"], [/isc/i, "ISC"], [/unicode/i, "Unicode-3.0"], [/mpl|mozilla/i, "MPL-2.0"]];

const read = (p) => readFileSync(p, "utf8").replace(/\r\n/g, "\n").trim();
// The licences Octet takes from an SPDX expression: one of each choice, all of an AND.
const chosen = (spdx = "") => spdx.split(/\s+AND\s+/).map((term) => {
  const options = term.replace(/[()]/g, "").split(/\s+OR\s+|\//).map((s) => s.trim());
  return PREFER.find((p) => options.includes(p)) ?? options[0];
});
// A package's licence and notice files. Of files named for one licence each (LICENSE-MIT, LICENSE-APACHE), only
// those of the licences chosen.
function texts(dir, spdx, licenseFile) {
  const files = readdirSync(dir).filter((f) => FILE.test(f)).sort();
  if (licenseFile && !files.includes(licenseFile)) files.push(licenseFile);
  const take = chosen(spdx), kind = (f) => FOR.find(([re]) => re.test(f.replace(/^licen[cs]e/i, "")))?.[1];
  const keep = files.filter((f) => !kind(f) || take.some((c) => c.startsWith(kind(f))));
  return (keep.length ? keep : files).map((f) => read(join(dir, f))).filter(Boolean);
}

// Rust: every crate the octet binary uses on the three platforms, through normal dependencies (not build tools,
// not procedural macros, which run only while Octet compiles).
const meta = JSON.parse(execFileSync("cargo", ["metadata", "--format-version", "1", "--manifest-path", join(root, "src-tauri/Cargo.toml"), ...PLATFORMS.flatMap((p) => ["--filter-platform", p])], { encoding: "utf8", maxBuffer: 1 << 28 }));
const byId = new Map(meta.packages.map((p) => [p.id, p])), nodes = new Map(meta.resolve.nodes.map((n) => [n.id, n]));
const used = new Set(), todo = [meta.resolve.root];
while (todo.length) {
  const id = todo.pop();
  if (used.has(id)) continue;
  used.add(id);
  for (const d of nodes.get(id).deps) if (d.dep_kinds.some((k) => k.kind === null)) todo.push(d.pkg);
}
const parts = [];
for (const id of used) {
  const p = byId.get(id);
  if (!p.source || p.targets.some((t) => t.kind.includes("proc-macro"))) continue;
  parts.push({ name: `${p.name} ${p.version}`, licence: p.license ?? "see the text", authors: p.authors, texts: texts(dirname(p.manifest_path), p.license, p.license_file) });
}
// npm: the packages in the page (package-lock.json, not the build tools).
const lock = JSON.parse(readFileSync(join(root, "package-lock.json"), "utf8"));
for (const [path, p] of Object.entries(lock.packages)) {
  if (!path || p.dev || p.devOptional) continue;
  const dir = join(root, path);
  parts.push({ name: `${path.replace(/^.*node_modules\//, "")} ${p.version}`, licence: p.license, texts: existsSync(dir) ? texts(dir, p.license) : [] });
}
parts.sort((a, b) => a.name.localeCompare(b.name));
// A package with no licence file, under a licence whose text names no author (MPL-2.0 must ship with its text), takes
// the text from another package under that licence alone. Of a choice, that licence is taken.
for (const id of ["MPL-2.0", "Apache-2.0"]) {
  const text = parts.find((p) => p.licence === id && p.texts.length === 1)?.texts;
  for (const p of parts) if (text && !p.texts.length && p.licence?.split(/\s+AND\s+/).every((term) => term.includes(id))) p.texts = text;
}

// MIT and BSD-3-Clause texts name the copyright holders, and the notice must ship. A package with no licence file
// under one of them gets the standard text, with the authors its manifest lists.
const MIT = (who) => `Copyright (c) ${who}

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.`;
const BSD3 = (who) => `Copyright (c) ${who}

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
   disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
   disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
   products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.`;
for (const p of parts) {
  const standard = { MIT, "BSD-3-Clause": BSD3 }[p.licence];
  if (!p.texts.length && standard) p.texts = [standard(p.authors?.length ? p.authors.join(", ") : `the authors of ${p.name.split(" ")[0]}`)];
}

// One copy of each text, after the names of the parts that use it.
const groups = new Map();
for (const p of parts) {
  const key = p.texts.join("\n\n") || `(${p.licence}: the package has no licence file)`;
  groups.set(key, [...(groups.get(key) ?? []), p]);
}
const rule = "=".repeat(80);
let out = `Octet includes the software and data below. Each part keeps its own licence.\nOctet itself is under the Apache License 2.0.\n` +
  `The source code of each Rust crate is on crates.io, and of each npm package on npmjs.com.\n\n`;
for (const [text, list] of groups) out += `${rule}\n${list.map((p) => `${p.name} (${p.licence})`).join("\n")}\n${rule}\n\n${text}\n\n`;
for (const [name, file] of [["The libraries inside Indigo's WASM", "src-tauri/licences/indigo-wasm.txt"], ["OPSIN and the libraries in its build", "src/vendor/opsin/NOTICES.txt"], ["nmrshiftdb2 data", "data/nmr/LICENCE.txt"], ["Wikidata data", "data/names/NOTICE.txt"], ["PubChem data", "src-tauri/licences/pubchem.txt"]])
  out += `${rule}\n${name}\n${rule}\n\n${read(join(root, file))}\n\n`;
writeFileSync(join(root, "src-tauri/licences/third-party.txt"), out);
console.log(`${parts.length} packages, ${groups.size} texts, ${(out.length / 1024).toFixed(0)} KB`);
