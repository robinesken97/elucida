// Run: node src/release.check.ts. Feedback is for testers (REL-8): every build has it, except the public release,
// which the release workflow builds from a tag with OCTET_FEEDBACK=0. The page (vite.config.ts) and the app
// (src-tauri/build.rs) must read the variable the same way.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (f: string) => readFileSync(new URL(`../${f}`, import.meta.url), "utf8");
assert.match(read("vite.config.ts"), /__FEEDBACK__: JSON\.stringify\(process\.env\.OCTET_FEEDBACK !== "0"\)/);
assert.match(read("src-tauri/build.rs"), /std::env::var\("OCTET_FEEDBACK"\)\.as_deref\(\) != Ok\("0"\)/);
// A tag (push) builds with 0; only Run workflow, with its box ticked, builds with 1.
assert.match(read(".github/workflows/release.yml"), /OCTET_FEEDBACK: \$\{\{ github\.event_name == 'workflow_dispatch' && inputs\.feedback && '1' \|\| '0' \}\}/);
console.log("release.check: ok");
