// Runs every check file (src/*.check.ts) one after another: `npm test` (and CI) runs it after the type check. The
// files that fail are named at the end.
import { readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";

const files = readdirSync("src").filter((f) => f.endsWith(".check.ts")).sort();
const failed = files.filter((f) => spawnSync(process.execPath, [`src/${f}`], { stdio: ["ignore", "ignore", "inherit"] }).status !== 0);
for (const f of failed) console.error(`FAIL src/${f}`);
console.log(`${files.length - failed.length} of ${files.length} check files pass.`);
process.exit(failed.length ? 1 : 0);
