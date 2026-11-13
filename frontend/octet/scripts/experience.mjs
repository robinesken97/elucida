// The experience check (decision 0024): nothing a user had in the last release gets worse in this one. It builds the
// last release and this commit on the same computer, opens each in headless Chrome, runs the scenarios in
// scripts/experience.json, and fails if a glide that should show does not, or if a command is slower than it was.
// Each scenario runs as it is and with the computer 4 times slower (Chrome's CPU throttling), as many users have a
// slower computer than the one that builds Octet: 1.1.1's Clean Up took its glide away on those (FEEL-38).
//
//   node scripts/experience.mjs                     this commit against the last release before it
//   node scripts/experience.mjs --base v1.1.0 --head v1.1.1   two releases (the check would have stopped 1.1.1)
//
// A result that is allowed to be worse names its scenario in docs/removals.md, with the reason and Sam's approval.
// Needs git with the release tags (fetch-depth 0 in CI) and Chrome (CHROME=path, or found below). No dependencies.
import { execFileSync, spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { extname, join, normalize, resolve } from "node:path";

const arg = (name) => { const i = process.argv.indexOf(`--${name}`); return i > 0 ? process.argv[i + 1] : undefined; };
const repo = resolve(new URL("..", import.meta.url).pathname);
const git = (...a) => execFileSync("git", a, { cwd: repo, encoding: "utf8" }).trim();
const plan = JSON.parse(readFileSync(join(repo, "scripts/experience.json"), "utf8"));
// --only <name,…> runs those scenarios, and --runs <n> sets the runs of each (for a quick look; CI runs them all).
if (arg("only")) plan.scenarios = plan.scenarios.filter((x) => arg("only").split(",").includes(x.name));
if (arg("runs")) plan.runs = +arg("runs");
const work = mkdtempSync(join(tmpdir(), "octet-experience-"));
const out = arg("out") ?? join(work, "report");
mkdirSync(out, { recursive: true });

// ——— The two builds ———
// The base is the newest release tag that is an ancestor of the head and not the head itself (unless the tree has
// changes), so a release is compared with the release before it.
const head = arg("head");
const headCommit = git("rev-parse", `${head ?? "HEAD"}^{commit}`);
const tags = git("tag", "--list", "v*", "--sort=-v:refname").split("\n").filter(Boolean);
// A tree with changes is newer than a tag on its commit, so that tag is the last release.
const changed = !head && git("status", "--porcelain", "--untracked-files=no") !== "";
const base = arg("base") ?? tags.find((t) => {
  const c = git("rev-parse", `${t}^{commit}`);
  if (c === headCommit) return changed;
  try { execFileSync("git", ["merge-base", "--is-ancestor", c, headCommit], { cwd: repo }); return true; } catch { return false; }
});
if (!base) throw new Error("no release tag to compare with: fetch the tags (git fetch --tags, or fetch-depth: 0 in CI)");
const build = (ref, name) => {
  const dir = join(work, name), dist = join(work, `${name}-dist`);
  if (ref) {
    execFileSync("git", ["worktree", "add", "--detach", dir, ref], { cwd: repo, stdio: "ignore" });
    execFileSync("npm", ["ci", "--no-audit", "--no-fund"], { cwd: dir, stdio: "ignore" });
  }
  execFileSync("npx", ["vite", "build", "--outDir", dist, "--emptyOutDir", "--logLevel", "error"], { cwd: ref ? dir : repo, stdio: ["ignore", "ignore", "inherit"] });
  return dist;
};
console.log(`Experience check: ${head ?? "this commit"} against ${base}`);
const dists = { base: build(base, "base"), head: build(head, "head") };
const cleanup = () => { for (const n of ["base", "head"]) try { execFileSync("git", ["worktree", "remove", "--force", join(work, n)], { cwd: repo, stdio: "ignore" }); } catch {} };

// ——— A static server for each build ———
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".wasm": "application/wasm", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf" };
const serve = (root) => new Promise((done) => {
  const server = createServer((req, res) => {
    const path = normalize(decodeURIComponent(new URL(req.url, "http://x").pathname)).replace(/^(\.\.[/\\])+/, "");
    let file = join(root, path);
    if (!existsSync(file) || statSync(file).isDirectory()) file = join(root, "index.html");
    res.writeHead(200, { "content-type": TYPES[extname(file)] ?? "application/octet-stream" });
    res.end(readFileSync(file));
  }).listen(0, "127.0.0.1", () => done({ server, url: `http://127.0.0.1:${server.address().port}/?editor` }));
});

// ——— The drawings, made with Octet's own code: each atom moved up to 0.3 bond lengths, the same each run ———
const g = globalThis;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({ measureText: (t) => ({ width: t.length * 6 }) }) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
const realFetch = g.fetch;
g.fetch = async (u) => (String(u).startsWith("file:") ? new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } }) : realFetch(u));
const chem = await import(join(repo, "src/chem.ts"));
await chem.ready;
const { serialize } = await import(join(repo, "src/file.ts"));
const jitter = (i) => Math.sin(i * 12.9898) * 0.3;
const drawing = (s) => {
  const mol = s.startsWith("chain:")
    ? { atoms: Array.from({ length: +s.slice(6) }, (_, i) => ({ label: "C", location: [i * 0.87, (i % 2) * 0.5, 0] })), bonds: Array.from({ length: +s.slice(6) - 1 }, (_, i) => ({ type: 1, atoms: [i, i + 1] })) }
    : chem.parseStructure(s);
  return serialize({ ...mol, atoms: mol.atoms.map((a, i) => ({ ...a, location: [a.location[0] + jitter(i), a.location[1] + jitter(i + 999), 0] })) });
};

// ——— Chrome over the DevTools protocol ———
const chromePath = process.env.CHROME ?? ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/opt/pw-browsers/chromium/chrome-linux64/chrome",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "C:/Program Files/Google/Chrome/Application/chrome.exe"].find(existsSync);
if (!chromePath) throw new Error("no Chrome: set CHROME to its path");
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(chromePath, ["--headless=new", `--remote-debugging-port=${port}`, "--window-size=1400,900", "--no-first-run", "--no-default-browser-check",
  "--no-sandbox", `--user-data-dir=${mkdtempSync(join(tmpdir(), "octet-experience-chrome-"))}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 100 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {} }
if (!target) throw new Error("Chrome did not start");
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const call = (method, params = {}) => new Promise((done, fail) => {
  const n = ++id, stop = setTimeout(() => fail(new Error(`${method} took over 60 s`)), 60000);
  const on = (e) => { const m = JSON.parse(e.data); if (m.id !== n) return; clearTimeout(stop); ws.removeEventListener("message", on); m.error ? fail(new Error(`${method}: ${m.error.message}`)) : done(m.result); };
  ws.addEventListener("message", on);
  ws.send(JSON.stringify({ id: n, method, params }));
});
const run = async (code) => {
  const r = await call("Runtime.evaluate", { expression: `(async () => { ${code} })()`, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
  return r.result.value;
};

// One run: open the build, paste the drawing (it stays selected), press the button, and note each frame for 2.5 s:
// whether the canvas changed in it (a MutationObserver, so the noting costs the page almost nothing).
const once = async (url, scenario, rate) => {
  await call("Emulation.setCPUThrottlingRate", { rate: 1 });
  await call("Page.navigate", { url });
  await run(`for (let i = 0; i < 200 && !document.querySelector('svg.canvas'); i++) await new Promise((r) => setTimeout(r, 50));`);
  await sleep(2500); // Indigo and the fonts
  await run(`
    const dt = new DataTransfer(); dt.setData('application/x-octet+json', ${JSON.stringify(drawing(scenario.drawing))});
    dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, cancelable: true }));
    await new Promise((r) => setTimeout(r, 1500));`);
  const at = await run(`
    const name = ${JSON.stringify(scenario.button)};
    const button = document.querySelector('[aria-label="' + name + '"]') ?? [...document.querySelectorAll('button')].find((b) => b.textContent.trim().startsWith(name));
    if (!button) return undefined;
    const b = button.getBoundingClientRect();
    return { x: b.x + b.width / 2, y: b.y + b.height / 2 };`);
  if (!at) return { missing: true };
  // A real click, as a user's: the browser runs it at the start of a frame, which is where 1.1.1 lost its glides
  // (button.click() from a script runs between frames, and hid the loss).
  await call("Input.dispatchMouseEvent", { type: "mouseMoved", x: at.x, y: at.y });
  await sleep(400);
  await call("Emulation.setCPUThrottlingRate", { rate });
  await run(`
    const canvas = document.querySelector('svg.canvas');
    let changed = false;
    const seen = new MutationObserver(() => { changed = true; });
    seen.observe(canvas, { subtree: true, childList: true, attributes: true, characterData: true });
    const frames = [];
    let t0;
    addEventListener('pointerdown', () => { t0 = performance.now(); changed = false; }, { capture: true, once: true });
    window.__frames = new Promise((done) => {
      const tick = () => {
        if (t0 !== undefined) frames.push([Math.round(performance.now() - t0), changed]);
        changed = false;
        t0 === undefined || performance.now() - t0 < 2500 ? requestAnimationFrame(tick) : (seen.disconnect(), done(frames));
      };
      requestAnimationFrame(tick);
    });`);
  // clicks: the button pressed again that soon after (gap ms), as a key held down repeats it.
  for (let k = 0; k < (scenario.clicks ?? 1); k++) {
    if (k) await sleep(scenario.gap ?? 60);
    for (const type of ["mousePressed", "mouseReleased"]) await call("Input.dispatchMouseEvent", { type, x: at.x, y: at.y, button: "left", clickCount: 1 });
  }
  return run(`
    const frames = await window.__frames;
    // The answer is the first frame that changed; the glide is the changed frames that follow it (a frame or two
    // the same in between is a slow frame, not the end).
    const first = frames.findIndex((f) => f[1]);
    if (first < 0) return { latency: undefined, frames: 0, span: 0 };
    let last = first;
    for (let k = first + 1, gap = 0; k < frames.length && gap <= 2; k++) frames[k][1] ? ((last = k), (gap = 0)) : gap++;
    const moving = frames.slice(first, last + 1).filter((f) => f[1]);
    // Jitter: the longest frame of the glide against its median frame (frames of uneven length read as stutter).
    const gaps = frames.slice(first + 1, last + 1).map((f, k) => f[0] - frames[first + k][0]).sort((a, b) => a - b);
    const jitter = gaps.length >= 3 ? Math.round(gaps[gaps.length - 1] - gaps[gaps.length >> 1]) : 0;
    return { latency: frames[first][0], frames: moving.length, span: frames[last][0] - frames[first][0], jitter, longest: gaps[gaps.length - 1] ?? 0 };`);
};
const median = (xs) => { const s = xs.filter((x) => x !== undefined).sort((a, b) => a - b); return s.length ? s[Math.floor(s.length / 2)] : undefined; };
const measure = async (url, scenario, rate) => {
  const runs = [];
  for (let k = 0; k < plan.runs; k++) runs.push(await once(url, scenario, rate));
  if (runs.some((r) => r.missing)) return { missing: true };
  return { latency: median(runs.map((r) => r.latency)), frames: median(runs.map((r) => r.frames)), span: median(runs.map((r) => r.span)), jitter: median(runs.map((r) => r.jitter)), longest: median(runs.map((r) => r.longest)) };
};

// ——— The rules ———
// Approved exceptions: docs/removals.md lines naming `experience:<scenario>:<rate>x:<rule>` and "Approved by Sam".
// Only the lines under "## Approved" count: the format lines above it are examples.
const removals = (existsSync(join(repo, "docs/removals.md")) ? readFileSync(join(repo, "docs/removals.md"), "utf8") : "").split("## Approved")[1] ?? "";
const approved = (key) => removals.split("\n").some((l) => l.includes(`\`${key}\``) && /Approved by Sam/i.test(l));
const failures = [], rows = [];
const servers = { base: await serve(dists.base), head: await serve(dists.head) };
try {
  for (const scenario of plan.scenarios) for (const rate of plan.rates) {
    const was = await measure(servers.base.url, scenario, rate), now = await measure(servers.head.url, scenario, rate);
    const key = (rule) => `experience:${scenario.name}:${rate}x:${rule}`;
    const fail = (rule, why) => { if (!approved(key(rule))) failures.push(`${key(rule)}: ${why}`); };
    rows.push({ scenario: scenario.name, rate, was, now });
    if (now.missing) { if (!was.missing) fail("gone", `"${scenario.button}" was there in ${base} and is not now`); continue; }
    if (now.latency === undefined) { fail("nothing", "the button changed nothing on the canvas"); continue; }
    if (scenario.glide) {
      const least = plan.glide.frames[rate] ?? 2;
      if (now.span < plan.glide.span || now.frames < least) fail("glide", `the glide showed ${now.frames} frames over ${now.span} ms (at least ${least} over ${plan.glide.span} ms)`);
      // Smooth on a cheap laptop: frames a second over the glide (decision 0024: 60 is smooth, under about 12 jerks).
      const fps = now.span ? (1000 * now.frames) / now.span : 0, floor = plan.glide.fps?.[rate];
      if (floor && now.span >= plan.glide.span && fps < floor) fail("smooth", `the glide ran at ${Math.round(fps)} frames a second (at least ${floor})`);
      // Even: no frame of the glide much longer than its others (a hitch reads as stutter, however fast the rest).
      const jitter = plan.glide.jitter?.[rate];
      if (jitter !== undefined && now.jitter > jitter) fail("even", `a frame of the glide took ${now.jitter} ms longer than its median frame (at most ${jitter})`);
    }
    if (!was.missing && was.latency !== undefined && now.latency > was.latency * plan.slower.ratio + plan.slower.ms)
      fail("speed", `the canvas answered in ${now.latency} ms, ${base} in ${was.latency} ms (allowed: ${Math.round(was.latency * plan.slower.ratio + plan.slower.ms)} ms)`);
  }
} finally {
  ws.close(); chrome.kill(); servers.base.server.close(); servers.head.server.close(); cleanup();
}

const cell = (r) => (r.missing ? "missing" : `${r.latency ?? "-"} ms, ${r.frames} frames over ${r.span} ms, longest frame ${Math.round(r.longest ?? 0)} ms`);
const table = [`| Scenario | CPU | ${base} | ${head ?? "this commit"} |`, "| --- | --- | --- | --- |", ...rows.map((r) => `| ${r.scenario} | ${r.rate}x | ${cell(r.was)} | ${cell(r.now)} |`)].join("\n");
writeFileSync(join(out, "experience.md"), `${table}\n\n${failures.length ? failures.map((f) => `- ${f}`).join("\n") : "Nothing is worse."}\n`);
writeFileSync(join(out, "experience.json"), JSON.stringify({ base, head: head ?? "HEAD", rows, failures }, null, 1));
console.log(table);
if (failures.length) {
  console.error(`\n${failures.length} thing(s) are worse than in ${base}:\n${failures.map((f) => `  ${f}`).join("\n")}\nFix them, or ask Sam to approve each in docs/removals.md.`);
  process.exit(1);
}
console.log(`\nNothing is worse than in ${base}. Report: ${out}`);
process.exit(0);
