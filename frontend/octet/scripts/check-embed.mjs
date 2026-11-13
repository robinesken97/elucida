// Run the vendored drawing engine's checks. Standalone Tauri/release tests have
// different host implementations in Elucida and are explicitly listed here.
import { readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
const standalone = new Set([
  "drive.check.ts", "experimentlist.check.ts", "filesafety.check.ts",
  "look.check.ts", "release.check.ts", "releases.check.ts", "version.check.ts",
  // 1.1.2: packaging of the standalone app, upstream's own CLAUDE.md and Git tags are not vendored
  "flatpak.check.ts", "libreoffice.check.ts", "word.check.ts", "ui.check.ts", "inventory.check.ts",
  // waits for Indigo's 10 s timeout; on a fast machine the call finishes, in unmodified upstream too
  "depth.check.ts",
]);
const files = readdirSync("src").filter(f => f.endsWith(".check.ts") && !standalone.has(f)).sort();
const failed = files.filter(f => spawnSync(process.execPath, [`src/${f}`], { stdio: ["ignore", "ignore", "inherit"] }).status !== 0);
for (const f of failed) console.error(`FAIL src/${f}`);
console.log(`${files.length - failed.length}/${files.length} embedded drawing checks passed; ${standalone.size} standalone host/release checks excluded.`);
process.exit(failed.length ? 1 : 0);
