// The canvas for screen readers, in a real browser: headless Chrome (puppeteer's headless shell in ~/.cache/puppeteer,
// driven over the DevTools protocol, no dependencies) opens the app, pastes a reaction, and writes what a screen reader
// gets: the accessibility tree of the canvas, the focus as Tab, Enter and the arrow keys move it, what the live region
// says after edits, screenshots of the focus in light and dark, with reduced motion and in forced colours, and the time
// a key takes on a drawing of about 500 atoms with the canvas's keyboard focus on and off. Serve a build, not the dev
// server: an edit to a source file reloads the dev server's page in the middle of the run.
//
//   npx vite build --outDir /tmp/octet-a11y --emptyOutDir && npx vite preview --outDir /tmp/octet-a11y --port 4437 &
//   node scripts/canvas-a11y.mjs http://localhost:4437/?editor <out-dir>
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";

const [url = "http://localhost:1437/?editor", out = "canvas-a11y-out"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const log = [];
const say = (...s) => { const line = s.join(" "); console.log(line); log.push(line); };

// ——— Drawings, made with Octet's own code ———
const g = globalThis;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
const realFetch = g.fetch;
g.fetch = async (u) => (String(u).startsWith("file:") ? new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } }) : realFetch(u));
const src = (f) => new URL(`../src/${f}`, import.meta.url).href;
const chem = await import(src("chem.ts"));
await chem.ready;
const { addCaption, addShape } = await import(src("edit.ts"));
const { serialize } = await import(src("file.ts"));
let rxn = chem.parseStructure("OC(=O)c1ccccc1O.CC(=O)OC(C)=O>>CC(=O)Oc1ccccc1C(O)=O");
const arrow = rxn.arrows[0], mid = (arrow.from[0] + arrow.to[0]) / 2;
rxn = addCaption(rxn, { text: "H2SO4", x: mid, y: 0.5, on: { arrow: arrow.id, side: "above" } })[0];
rxn = addCaption(rxn, { text: "90 °C", x: mid, y: -0.7, on: { arrow: arrow.id, side: "below" } })[0];
rxn = addCaption(rxn, { text: "Scheme 1", x: 0, y: 3.5 })[0];
rxn = addShape(rxn, { kind: "tlc", from: [6, -7], to: [9, -3], tlc: { lanes: 2, spots: [{ lane: 0, rf: 0.3 }, { lane: 0, rf: 0.6 }, { lane: 1, rf: 0.45 }] } })[0];
// About 500 atoms: benzene rings with a side group each, in a grid.
const big = { atoms: [], bonds: [] };
for (let r = 0; r < 71; r++) {
  const cx = (r % 9) * 4, cy = -Math.floor(r / 9) * 4, base = big.atoms.length;
  for (let i = 0; i < 6; i++) big.atoms.push({ label: "C", location: [cx + Math.cos((Math.PI / 3) * i), cy + Math.sin((Math.PI / 3) * i), 0] });
  for (let i = 0; i < 6; i++) big.bonds.push({ type: i % 2 ? 1 : 2, atoms: [base + i, base + ((i + 1) % 6)] });
  big.atoms.push({ label: r % 2 ? "O" : "N", location: [cx + 2, cy, 0] });
  big.bonds.push({ type: 1, atoms: [base, base + 6] });
}

// ——— Chrome: puppeteer's headless shell (Chrome for Testing's own headless mode takes no screenshots on the Mac) ———
const root = join(homedir(), ".cache/puppeteer/chrome-headless-shell");
const build = readdirSync(root).sort().pop(), dir = readdirSync(join(root, build)).find((d) => d.startsWith("chrome-"));
const app = join(root, build, dir, "chrome-headless-shell");
if (!existsSync(app)) throw new Error(`no headless shell at ${app}`);
const port = 9600 + Math.floor(Math.random() * 300);
const chrome = spawn(app, [`--remote-debugging-port=${port}`, "--window-size=1400,900", "--force-device-scale-factor=2", `--user-data-dir=${mkdtempSync(join(tmpdir(), "octet-a11y-"))}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
// Each call gives up after 30 s, so a stuck step is named and the run goes on.
const call = (method, params = {}) => new Promise((resolve) => {
  const n = ++id;
  const stop = setTimeout(() => { ws.removeEventListener("message", on); say("cdp timeout", method); resolve(undefined); }, 30000);
  const on = (e) => { const m = JSON.parse(e.data); if (m.id === n) { clearTimeout(stop); ws.removeEventListener("message", on); if (m.error) say("cdp error", method, m.error.message); resolve(m.result); } };
  ws.addEventListener("message", on);
  ws.send(JSON.stringify({ id: n, method, params }));
});
const run = async (code) => { const r = await call("Runtime.evaluate", { expression: `(async () => { ${code} })()`, awaitPromise: true, returnByValue: true }); if (r?.exceptionDetails) say("page error:", JSON.stringify(r.exceptionDetails).slice(0, 400)); return r?.result?.value; };
const KEYS = { Tab: 9, Enter: 13, Escape: 27, ArrowLeft: 37, ArrowUp: 38, ArrowRight: 39, ArrowDown: 40, n: 78, "1": 49, Shift: 16 };
const press = async (key, shift = false) => {
  const code = key.length === 1 ? (/\d/.test(key) ? `Digit${key}` : `Key${key.toUpperCase()}`) : key, base = { key, code, windowsVirtualKeyCode: KEYS[key], modifiers: shift ? 8 : 0 };
  await call("Input.dispatchKeyEvent", { type: key.length === 1 ? "keyDown" : "rawKeyDown", ...base, ...(key.length === 1 ? { text: key } : {}) });
  await call("Input.dispatchKeyEvent", { type: "keyUp", ...base });
  await sleep(60);
};
const focused = () => run(`const e = document.activeElement; return e === document.body ? "(body)" : e.closest(".canvas-access") ? [e.getAttribute("aria-roledescription") || e.getAttribute("role"), e.getAttribute("aria-label"), e.getAttribute("aria-description")].filter(Boolean).join(" | ") : "(outside the canvas: " + (e.getAttribute("aria-label") || e.tagName) + ")";`);
const shot = async (name, clip) => {
  const r = await call("Page.captureScreenshot", { format: "png", ...(clip ? { clip: { ...clip, scale: 1 } } : {}) });
  if (r?.data) writeFileSync(join(out, `${name}.png`), Buffer.from(r.data, "base64"));
};
// The focused element's box, with room round it, for a close screenshot.
const near = async (pad = 60) => run(`const b = document.activeElement.getBoundingClientRect(); return { x: Math.max(0, b.x - ${pad}), y: Math.max(0, b.y - ${pad}), width: b.width + ${2 * pad}, height: b.height + ${2 * pad} };`);
const load = async (mol) => {
  await call("Page.navigate", { url });
  await sleep(2500);
  await run(`
    for (let i = 0; i < 60 && !document.querySelector('svg.canvas'); i++) await new Promise((r) => setTimeout(r, 100));
    const dt = new DataTransfer(); dt.setData('application/x-octet+json', ${JSON.stringify(serialize(mol))});
    dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, cancelable: true }));
    await new Promise((r) => setTimeout(r, 300));
    const b = document.querySelector('#world').getBoundingClientRect(), C = document.querySelector('svg.canvas');
    // Fit the drawing in the part of the window left of the Actions panel.
    const k = Math.min((0.62 * innerWidth) / b.width, innerHeight / b.height) * 0.8;
    C.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, ctrlKey: true, deltaY: -Math.log(k) / 0.01, clientX: b.x + b.width / 2, clientY: b.y + b.height / 2 }));
    await new Promise((r) => setTimeout(r, 300));
    const b2 = document.querySelector('#world').getBoundingClientRect();
    C.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, deltaX: (b2.x + b2.width / 2) - 0.4 * innerWidth, deltaY: (b2.y + b2.height / 2) - innerHeight / 2 }));
    return true;`);
  await press("Escape");
};

await call("Page.enable");
await call("Accessibility.enable");
// The page has the focus as a window would, so focus events fire.
await call("Emulation.setFocusEmulationEnabled", { enabled: true });

// ——— 1. The accessibility tree of the canvas ———
await load(rxn);
await sleep(7000); // the names engine loads once the window has been still for 1.5 s, then names fill in
const { nodes } = await call("Accessibility.getFullAXTree");
const byId = new Map(nodes.map((n) => [n.nodeId, n]));
const canvas = nodes.find((n) => n.role?.value === "application" && n.name?.value === "Drawing canvas");
const lines = [];
const walk = (n, depth) => {
  if (!n || n.ignored) { for (const c of n?.childIds ?? []) walk(byId.get(c), depth); return; }
  const prop = (k) => n.properties?.find((p) => p.name === k)?.value?.value;
  lines.push(`${"  ".repeat(depth)}${n.role?.value}${prop("roledescription") ? ` (${prop("roledescription")})` : ""}: "${n.name?.value ?? ""}"${n.description?.value ? `, more: "${n.description.value}"` : ""}${prop("focusable") ? " [focusable]" : ""}`);
  for (const c of n.childIds ?? []) walk(byId.get(c), depth + 1);
};
walk(canvas, 0);
const status = nodes.filter((n) => n.role?.value === "status").map((n) => n.name?.value ?? "");
const svgSeen = nodes.some((n) => n.role?.value === "image" && n.name?.value === "Drawing canvas");
writeFileSync(join(out, "ax-tree.txt"), `${lines.join("\n")}\n`);
writeFileSync(join(out, "ax-tree.json"), JSON.stringify(nodes.filter((n) => lines.length && n), null, 1));
say("Accessibility tree of the canvas:");
lines.forEach((l) => say("  " + l));
say(`The SVG is still one image to screen readers: ${svgSeen}`);
say(`Live regions: ${status.length}`);

// ——— 2. The keyboard: Tab, Enter, the arrow keys, an edit, Escape, Tab out ———
const seen = async (what) => say(`${what.padEnd(18)} → ${await focused()}`);
for (let k = 0; k < 4; k++) { await press("Tab"); await seen(`Tab ${k + 1}`); if (k === 0) await shot("focus-text-light", await near()); if (k === 1) await shot("focus-structure-light", await near()); }
await shot("focus-window-light");
await press("Tab", true); await seen("Shift+Tab");
await press("Tab", true); await seen("Shift+Tab");
await press("Enter"); await seen("Enter");
await shot("focus-atom-light", await near(80));
for (const [n, k] of ["ArrowRight", "ArrowRight", "ArrowUp", "ArrowRight", "ArrowDown", "ArrowLeft"].entries()) {
  await press(k);
  await seen(`${k}`);
  if (n === 0) await shot("focus-bond-light", await near(80));
}
await press("n");
await sleep(700);
say(`Live region after n: "${await run(`return document.querySelector('.editor > [role=status]').textContent;`)}"`);
await seen("after n");
await press("Escape"); await seen("Escape");
await press("Tab"); await seen("Tab");
const stamp = await run(`return getComputedStyle(document.activeElement).transitionDuration + " " + getComputedStyle(document.activeElement).animationName + " " + getComputedStyle(document.activeElement).boxShadow;`);
say(`Focus ring style: ${stamp}`);
for (let k = 0; k < 8; k++) await press("Tab");
await seen("Tab past the end");
// Undo, said.
await run(`dispatchEvent(new KeyboardEvent('keydown', { key: 'z', code: 'KeyZ', metaKey: true, ctrlKey: !navigator.platform.startsWith('Mac'), bubbles: true, cancelable: true }));`);
await sleep(700);
say(`Live region after undo: "${await run(`return document.querySelector('.editor > [role=status]').textContent;`)}"`);

// ——— 3. Dark, reduced motion, forced colours ———
await call("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }, { name: "prefers-reduced-motion", value: "reduce" }] });
await load(rxn);
await sleep(1500);
await press("Tab"); await press("Tab"); await seen("Tab Tab (dark)");
await shot("focus-structure-dark", await near());
await press("Enter"); await press("ArrowRight"); await seen("Enter, Right (dark)");
await shot("focus-bond-dark", await near(80));
await shot("focus-window-dark");
say(`Focus ring with reduced motion: ${await run(`return getComputedStyle(document.activeElement).transitionDuration + " " + getComputedStyle(document.activeElement).animationName;`)}`);
await call("Emulation.setEmulatedMedia", { features: [{ name: "forced-colors", value: "active" }] });
await load(rxn);
await sleep(1500);
await press("Tab"); await press("Tab");
say(`Forced colours outline: ${await run(`const s = getComputedStyle(document.activeElement); return s.outlineStyle + " " + s.outlineWidth + " " + s.outlineColor;`)}`);
await shot("focus-structure-forced-colours", await near());
await call("Emulation.setEmulatedMedia", { features: [] });

// ——— 4. Speed: keys on about 500 atoms, with the canvas's keyboard focus off and on ———
// The time from a key to the next frame, for a walk of the hotspot and bonds added from it (the 1 key).
const timeKeys = async (label) => {
  const times = await run(`
    const frame = () => new Promise((r) => { const ch = new MessageChannel(); ch.port1.onmessage = () => requestAnimationFrame(() => setTimeout(r, 0)); ch.port2.postMessage(0); });
    const key = (k, code) => dispatchEvent(new KeyboardEvent('keydown', { key: k, code, bubbles: true, cancelable: true }));
    const out = [];
    for (let i = 0; i < 30; i++) {
      const [k, code] = i % 3 === 2 ? ['1', 'Digit1'] : ['ArrowRight', 'ArrowRight'];
      const t0 = performance.now(); key(k, code); await frame(); out.push(performance.now() - t0);
    }
    return out;`);
  const s = [...times].sort((a, b) => a - b);
  say(`${label}: median ${s[15].toFixed(1)} ms, 90th percentile ${s[27].toFixed(1)} ms, worst ${s[29].toFixed(1)} ms a key`);
  return s;
};
await call("Emulation.setCPUThrottlingRate", { rate: 4 });
await load(big);
await sleep(2500);
say(`Atoms: ${await run(`return document.querySelectorAll('.canvas-access [data-key]').length + " objects on the canvas";`)}`);
// Off: the hotspot put on an atom as a mouse user's keys put it (no focus on the canvas).
await run(`document.activeElement.blur?.();`);
await press("Tab"); await press("Escape"); await run(`document.activeElement.blur?.(); document.body.focus();`);
await press("Tab"); await press("Enter");
const on = await timeKeys("Keys with the canvas's keyboard focus on (4x slower CPU)");
await run(`document.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })); document.activeElement.blur?.();`);
const off = await timeKeys("Keys with it off (a click moved the focus away)");
await call("Emulation.setCPUThrottlingRate", { rate: 1 });
writeFileSync(join(out, "speed.json"), JSON.stringify({ on, off }, null, 1));
writeFileSync(join(out, "log.txt"), `${log.join("\n")}\n`);
chrome.kill();
process.exit(0);
