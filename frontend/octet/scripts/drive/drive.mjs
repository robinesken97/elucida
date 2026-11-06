// Drives Octet on Windows and Linux as a person would: its window (through tauri-driver and WebDriver), its menus
// and keys (through the system: AT-SPI and xdotool on Linux, the mouse and SendKeys on Windows), and the system
// clipboard (xclip, or .NET's Clipboard). .github/workflows/platforms.yml runs it on GitHub's machines, after
// `npm run tauri build -- --debug --no-bundle`; on Linux inside dbus-run-session and xvfb-run. Writes its log and
// screenshots to drive-out/. No dependencies: Node's fetch speaks WebDriver.
//
//   node scripts/drive/drive.mjs           drive Octet (Windows or Linux)
//   node scripts/drive/drive.mjs --dry     print the steps, the commands each platform runs, the WebDriver calls that
//                                          change window and what each step waits for, and run nothing
import { execFileSync, spawn } from "node:child_process";
import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const VERSION = JSON.parse(readFileSync(new URL("../../package.json", import.meta.url), "utf8")).version;

const DRY = process.argv.includes("--dry");
const WIN = process.platform === "win32";
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve("drive-out");
const APP = path.resolve("src-tauri/target/debug", WIN ? "octet.exe" : "octet");
const PORT = 4444;
mkdirSync(OUT, { recursive: true });
const log = (s) => { console.log(s); writeFileSync(path.join(OUT, "log.txt"), s + "\n", { flag: "a" }); };
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
// On GitHub's machines, a failure is also an error on the run's page, titled with the step that failed.
const esc = (s) => s.replace(/%/g, "%25").replace(/\r/g, "%0D").replace(/\n/g, "%0A");
const fail = (title, message) => {
  log(`   FAILED: ${message}`);
  if (process.env.GITHUB_ACTIONS) console.log(`::error title=${esc(title).replace(/:/g, "%3A").replace(/,/g, "%2C")}::${esc(message)}`);
};

// What Copy puts on each system's clipboard with Settings as they start (src-tauri/src/clipboard.rs).
const FORMATS = WIN
  ? ["EnhancedMetafile", "DeviceIndependentBitmap", "ChemDraw Interchange Format", "CDXML", "MDLCT", "SMILES", "application/x-octet+json"]
  : ["image/png", "image/svg+xml", "chemical/x-cdx", "chemical/x-cdxml", "chemical/x-mdl-molfile", "chemical/x-daylight-smiles", "application/x-octet+json"];
const SMILES = WIN ? "SMILES" : "chemical/x-daylight-smiles";
const OCTET = "application/x-octet+json";

// ---- The system: commands run outside the window ----

// A command's output (a Buffer). In a dry run, the command is printed and nothing runs.
function run(cmd, args, input, timeout = 30_000) {
  if (DRY) { log(`    $ ${cmd} ${args.map((a) => (/\s/.test(a) ? JSON.stringify(a) : a)).join(" ")}`); return Buffer.alloc(0); }
  return execFileSync(cmd, args, { input, timeout, maxBuffer: 64 << 20 });
}
const PS = ["-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File", path.join(HERE, "windows.ps1")];
const ps = (...args) => run("powershell.exe", [...PS, ...args]);

const system = WIN
  ? {
      setText: (text) => ps("clip-set", text),
      formats: () => ps("clip-formats").toString().split(/\r?\n/).filter(Boolean),
      read: (format) => Buffer.from(ps("clip-get", format).toString().trim(), "base64"),
      menu: (...names) => ps("menu", ...names),
      key: (keys) => ps("keys", { "ctrl+v": "^v" }[keys] ?? keys),
      running: () => ps("running").toString().trim() === "yes",
      front: () => ps("front").toString().trim(),
      menuNames: () => ps("menu-names").toString().split(/\r?\n/).filter(Boolean),
      uiaMenu: () => ps("uia-menu").toString().split(/\r?\n/).filter(Boolean),
      // Each menu opens and closes in turn: up to about 3 s a menu.
      uiaOpen: () => run("powershell.exe", [...PS, "uia-open"], undefined, 90_000).toString().split(/\r?\n/).filter(Boolean),
    }
  : {
      // xclip stays to serve the clipboard, so it is not waited for.
      setText: (text) => {
        if (DRY) return void run("xclip", ["-selection", "clipboard", "-i"]);
        const x = spawn("xclip", ["-selection", "clipboard", "-i"], { stdio: ["pipe", "ignore", "ignore"], detached: true });
        x.stdin.end(text);
        x.unref();
      },
      formats: () => run("xclip", ["-selection", "clipboard", "-o", "-t", "TARGETS"]).toString().split("\n").filter(Boolean),
      read: (format) => run("xclip", ["-selection", "clipboard", "-o", "-t", format]),
      menu: (...names) => run("python3", [path.join(HERE, "linux-menu.py"), pid(), ...names]),
      // Real key presses (XTEST), to the window in front: the drawing's (Quick start checks that it is).
      key: (keys) => run("xdotool", ["key", "--clearmodifiers", keys]),
      running: () => pid() !== "",
      front: () => run("python3", [path.join(HERE, "linux-menu.py"), pid()]).toString().trim(),
    };
// Octet's process on Linux ("" when there is none).
function pid() {
  if (DRY) return "PID";
  try { return execFileSync("pgrep", ["-f", "target/debug/octet"]).toString().split("\n")[0].trim(); } catch { return ""; }
}

// ---- WebDriver (tauri-driver on port 4444) ----

let session = DRY ? "SESSION" : undefined;
async function wd(method, url, body) {
  if (DRY) return void log(`    WebDriver: ${method} ${url}`);
  // Two minutes at most, so a page that stops answering fails the step instead of holding the run.
  const r = await fetch(`http://127.0.0.1:${PORT}${url}`, { method, headers: { "content-type": "application/json" }, body: body && JSON.stringify(body), signal: AbortSignal.timeout(120_000) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`${method} ${url}: ${JSON.stringify(j.value ?? j).slice(0, 500)}`);
  return j.value;
}
// A script in the page; its result.
const page = async (script, ...args) => (DRY ? undefined : wd("POST", `/session/${session}/execute/sync`, { script, args }));
async function until(what, test, ms = 20_000) {
  if (DRY) return void log(`    wait for ${what}`);
  const end = Date.now() + ms;
  for (;;) {
    let last;
    try { if (await test()) return; } catch (e) { last = e; }
    if (Date.now() > end) throw new Error(`waited ${ms / 1000} s for ${what}${last ? `: ${last.message}` : ""}`);
    await sleep(250);
  }
}
// Each window has its own page: Home's, and each drawing's (src-tauri/src/windows.rs). WebDriver acts on one at a time.
const handles = () => wd("GET", `/session/${session}/window/handles`);
const toWindow = (handle) => wd("POST", `/session/${session}/window`, { handle });
// The window that opens next (one not in `before`), once it is in front with the drawing's name, as a new window of
// Octet's is. Menu commands and keys go to the window in front.
async function opened(before, title) {
  let handle;
  await until("a new window", async () => (handle = (await handles()).find((h) => !before.includes(h))));
  if (DRY) system.front(); // prints the command the wait below runs
  await until(`the new window in front, named ${title}`, () => system.front() === title);
  return handle;
}
let drawing; // the first drawing's window
async function screenshot(name) {
  if (DRY || !session) return;
  try { writeFileSync(path.join(OUT, `${name}.png`), Buffer.from(await wd("GET", `/session/${session}/screenshot`), "base64")); } catch { /* the window is gone */ }
}

// The O atoms the drawing shows: one per ethanol pasted (each label's text in the canvas).
const oxygens = () => page("return [...document.querySelectorAll('svg.canvas text')].map((t) => t.textContent).join('').split('O').length - 1");
const pasted = (n) => until(`${n} ethanol in the drawing`, async () => (await oxygens()) === n);
const nameField = "input.name-field";
// The name field's value, after its text is set (as typing does) and all of it selected.
const fill = (text) => page(`const el = document.querySelector(arguments[0]); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, arguments[1]);
  el.dispatchEvent(new Event("input", { bubbles: true })); el.focus(); el.select(); return el.value`, nameField, text);
const fieldValue = () => page("return document.querySelector(arguments[0])?.value", nameField);
const clipText = () => system.read(WIN ? "UnicodeText" : "UTF8_STRING").toString("utf8").replace(/\0+$/, "");

// ---- The steps ----

const steps = [
  ["Octet starts and shows Home", async () => {
    await until("the page", () => page("return document.readyState === 'complete' && !!document.querySelector('#root > *')"), 60_000);
    // A new profile asks for a name, offers the tutorial and checks for updates, and someone who has a name sees the
    // version's notes once (What's new): these are set, so Home shows.
    await page(`const k = "octet.settings", s = JSON.parse(localStorage.getItem(k) || "{}");
      localStorage.setItem(k, JSON.stringify({ ...s, userName: "Test", tutorialDone: true, updates: false, seenNotes: arguments[0] })); setTimeout(() => location.reload(), 50);`, VERSION);
    await sleep(1000);
    await until("Home", () => page("return !!document.querySelector('main.home .home-tile.new')"), 30_000);
  }],
  // Narrator and other screen readers find the menu bar through UI Automation: every menu of the window's menu bar
  // must be there, by name, and open when the screen reader opens it.
  ...(WIN ? [["The menu bar and each of its menus are in UI Automation, and each opens, as a screen reader finds them", async () => {
    const menus = system.menuNames(), found = system.uiaMenu();
    log(`    UI Automation: ${found.join(", ")}`);
    if (!DRY && (menus.length < 5 || found.join("|") !== menus.join("|"))) throw new Error(`UI Automation's menu bar has ${found.join(", ") || "nothing"}; the window's menu bar has ${menus.join(", ")}`);
    const opened = system.uiaOpen(), shut = opened.filter((l) => !/ opened /.test(l));
    for (const l of opened) log(`    ${l}`);
    if (!DRY && (shut.length || opened.length !== menus.length)) throw new Error(`through UI Automation: ${shut.join("; ") || `${opened.length} of ${menus.length} menus tried`}`);
  }]] : []),
  // The first drawing opens in Home's own window (decision 0020); File > New, below, gives the next one a window.
  ["Home's Quick start opens the first drawing in Home's own window", async () => {
    const before = await handles();
    await page("document.querySelector('main.home .home-tile.new').click()");
    await until("the drawing", () => page("return !document.querySelector('main.home') && !!document.querySelector('svg.canvas')"));
    if (!DRY && (await handles()).length !== before.length) throw new Error("Quick start opened another window");
    drawing = await wd("GET", `/session/${session}/window`);
    await sleep(5000); // the chemistry engine (WebAssembly) loads
  }],
  ["Edit > Paste pastes SMILES text from the clipboard", async () => {
    system.setText("CCO");
    await sleep(500);
    system.menu("Edit", "Paste");
    await pasted(1);
  }],
  ["Edit > Select All, then Edit > Copy puts Octet's formats on the clipboard", async () => {
    system.menu("Edit", "Select All");
    system.menu("Edit", "Copy");
    await until(`${OCTET} on the clipboard`, () => system.formats().includes(OCTET), 10_000);
    const have = system.formats(), missing = FORMATS.filter((f) => !have.includes(f));
    log(`    clipboard: ${have.join(", ")}`);
    if (!DRY && missing.length) throw new Error(`not on the clipboard: ${missing.join(", ")}`);
    const smiles = system.read(SMILES).toString("latin1").replace(/\0+$/, "");
    if (!DRY && !/^(CCO|OCC)$/.test(smiles.trim())) throw new Error(`SMILES on the clipboard: ${JSON.stringify(smiles)}`);
    if (!DRY) JSON.parse(system.read(OCTET).toString("utf8"));
  }],
  ["Edit > Paste brings Octet's copy back", async () => {
    system.menu("Edit", "Paste");
    await pasted(2);
  }],
  ["Ctrl+V pastes it again", async () => {
    system.key("ctrl+v");
    await pasted(3);
  }],
  ["Edit > Undo takes the last paste back", async () => {
    system.menu("Edit", "Undo");
    await pasted(2);
  }],
  ["Edit > Copy, Cut and Paste work on a text field", async () => {
    system.menu("Structure", "Convert Name to Structure");
    await until("the name field", () => page("return document.activeElement?.matches(arguments[0])", nameField));
    await fill("benzene");
    system.menu("Edit", "Copy");
    await until("the name on the clipboard", () => clipText() === "benzene", 10_000);
    await fill("benzene");
    system.menu("Edit", "Cut");
    await until("the name field empty", async () => (await fieldValue()) === "");
    system.menu("Edit", "Paste");
    await until("the name pasted back", async () => (await fieldValue()) === "benzene");
    await page("document.querySelector(arguments[0]).dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))", nameField);
    await until("the name field closed", async () => !(await page("return !!document.querySelector(arguments[0])", nameField)));
  }],
  ["File > New opens a new drawing in another window, and the drawing stays", async () => {
    const before = await handles();
    system.menu("File", "New*");
    const next = await opened(before, "Untitled");
    await pasted(2);
    await toWindow(next);
    await until("the new drawing", () => page("return !!document.querySelector('svg.canvas')"));
    await pasted(0);
  }],
  ["File > Exit asks about the unsaved drawing, and Don't Save ends Octet", async () => {
    system.menu("File", "Exit");
    await toWindow(drawing);
    const dontSave = "[...document.querySelectorAll('button')].find((b) => /Don.t Save/.test(b.textContent))";
    await until("the question", () => page(`return !!${dontSave}`));
    await page(`${dontSave}.click()`);
    await until("Octet to end", () => !system.running(), 15_000);
    session = undefined;
  }],
];

// ---- Run ----

let driver, failed = 0;
try {
  log(`Octet on ${process.platform}: ${APP}`);
  if (!DRY) {
    const args = ["--port", String(PORT)];
    if (WIN && process.env.OCTET_NATIVE_DRIVER) args.push("--native-driver", process.env.OCTET_NATIVE_DRIVER);
    driver = spawn("tauri-driver", args, { stdio: ["ignore", "inherit", "inherit"] });
    await until("tauri-driver", () => fetch(`http://127.0.0.1:${PORT}/status`).then((r) => r.ok), 30_000);
    session = (await wd("POST", "/session", { capabilities: { alwaysMatch: { browserName: "wry", "tauri:options": { application: APP } } } })).sessionId;
  }
  for (const [k, [name, act]] of steps.entries()) {
    log(`${k + 1}. ${name}`);
    try {
      await act();
      log("   ok");
    } catch (e) {
      failed++;
      fail(`Step ${k + 1} failed: ${name}`, e.message);
      await screenshot(`step-${k + 1}`);
      break; // each step needs the one before
    }
  }
} catch (e) {
  failed++;
  fail("Octet did not start under WebDriver", e.message);
} finally {
  if (session) await wd("DELETE", `/session/${session}`).catch(() => {});
  driver?.kill();
}
log(failed ? "Octet failed on this system." : DRY ? "Dry run: nothing ran." : "Every step passed.");
// Each step and how it went, on the run's page.
const summary = process.env.GITHUB_STEP_SUMMARY;
if (summary) appendFileSync(summary, `### Octet on ${WIN ? "Windows" : "Linux"}\n\n\`\`\`\n${readFileSync(path.join(OUT, "log.txt"), "utf8")}\`\`\`\n`);
process.exit(failed ? 1 : 0);
