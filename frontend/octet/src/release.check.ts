// Run: node src/release.check.ts. Feedback is for testers (REL-8): every build has it, except the public release,
// which the release workflow builds from a tag with OCTET_FEEDBACK=0. The page (vite.config.ts) and the app
// (src-tauri/build.rs) must read the variable the same way.
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join } from "node:path";

const read = (f: string) => readFileSync(new URL(`../${f}`, import.meta.url), "utf8");
assert.match(read("vite.config.ts"), /__FEEDBACK__: JSON\.stringify\(process\.env\.OCTET_FEEDBACK !== "0"\)/);
assert.match(read("src-tauri/build.rs"), /std::env::var\("OCTET_FEEDBACK"\)\.as_deref\(\) != Ok\("0"\)/);
// A tag (push) builds with 0; only Run workflow, with its box ticked, builds with 1.
const yml = read(".github/workflows/release.yml");
assert.match(yml, /OCTET_FEEDBACK: \$\{\{ github\.event_name == 'workflow_dispatch' && inputs\.feedback && '1' \|\| '0' \}\}/);

// Windows signing with Certum (REL-6) is one secret, WINDOWS_CERTUM. Its step and the Build settings script run here as
// the runner runs them, with a stand-in for cargo. Without the secret the build goes on unsigned and the log says so.
// The updater key gives the updater files with or without Windows signing (REL-10).
assert.match(yml, /if: runner\.os == 'Windows'\n +shell: bash\n +env:\n +WINDOWS_CERTUM: \$\{\{ secrets\.WINDOWS_CERTUM \}\}\n/);
const script = (step: string) => {
  const [, indent, body] = yml.slice(yml.indexOf(`- name: ${step}\n`)).match(/\n( +)run: \|\n((?:\1 .*\n|\n)*)/)!;
  return body.replace(new RegExp(`^${indent}  `, "gm"), "");
};
const tmp = mkdtempSync(join(tmpdir(), "octet-release-"));
writeFileSync(join(tmp, "cargo"), '#!/bin/sh\necho "cargo $*"\n', { mode: 0o755 });
const certum = (secret: string) => {
  const env = join(tmp, "env");
  writeFileSync(env, "");
  const run = spawnSync("bash", ["--noprofile", "--norc", "-eo", "pipefail", "-c", script("Windows certificate (Certum SimplySign)")],
    { encoding: "utf8", env: { PATH: `${tmp}:${process.env.PATH}`, GITHUB_ENV: env, WINDOWS_CERTUM: secret } });
  return { status: run.status, out: run.stdout, env: readFileSync(env, "utf8") };
};
const settings = (vars: Record<string, string>) => {
  const run = spawnSync(process.execPath, ["-e", script("Build settings").match(/node -e '([^']*)'/)![1]], { cwd: tmp, encoding: "utf8", env: { RUNNER_OS: "Windows", ...vars } });
  return { out: run.stdout, bundle: JSON.parse(readFileSync(join(tmp, "ci-build.conf.json"), "utf8")).bundle };
};
try {
  let step = certum("");
  assert.equal(step.status, 0);
  assert.equal(step.out, "WINDOWS_CERTUM is not set.\n");
  assert.equal(step.env, "");
  const link = "otpauth://totp/Certum:me@example.com?secret=GEZDGNBVGY3TQOJQ&issuer=Certum";
  step = certum(`me@example.com ${link}`);
  assert.equal(step.status, 0);
  assert.equal(step.env, `CERTUM_EMAIL=me@example.com\nCERTUM_OTP=${link}\n`);
  assert.ok(step.out.includes(`::add-mask::me@example.com\n::add-mask::${link}\n`));
  assert.match(step.out, /^cargo install ssign --version \d+\.\d+\.\d+ --locked$/m);
  step = certum("me@example.com");
  assert.equal(step.status, 1);
  assert.match(step.out, /^::error::WINDOWS_CERTUM must be/);
  assert.equal(step.env, "");

  let build = settings({ TAURI_SIGNING_PRIVATE_KEY: "key" });
  assert.deepEqual(build.bundle, { createUpdaterArtifacts: true });
  assert.match(build.out, /^::notice::No Windows signing secret is set/);
  build = settings({ TAURI_SIGNING_PRIVATE_KEY: "key", CERTUM_EMAIL: "me@example.com" });
  assert.deepEqual(build.bundle, { createUpdaterArtifacts: true, windows: { signCommand: { cmd: "ssign", args: ["-n", "Octet Draw", "%1"] } } });
  assert.equal(build.out, "");
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
console.log("release.check: ok");
