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
const CDX = WIN ? "ChemDraw Interchange Format" : "chemical/x-cdx";
const CDXML = WIN ? "CDXML" : "chemical/x-cdxml";
const OCTET = "application/x-octet+json";
// File > Close Window: on Windows the system's item, which muda names Close (Alt+F4); on Linux Octet's own.
const CLOSE = WIN ? "Close" : "Close Window";

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
      setText: (text) => run("powershell.exe", [...PS, "clip-set"], text),
      setData: (format, bytes) => ps("clip-set-data", format, Buffer.from(bytes).toString("base64")),
      formats: () => ps("clip-formats").toString().split(/\r?\n/).filter(Boolean),
      read: (format) => Buffer.from(ps("clip-get", format).toString().trim(), "base64"),
      menu: (...names) => ps("menu", ...names),
      key: (keys) => ps("keys", { "ctrl+v": "^v", Left: "{LEFT}" }[keys] ?? keys),
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
      setData: (format, bytes) => {
        if (DRY) return void run("xclip", ["-selection", "clipboard", "-t", format, "-i"]);
        const x = spawn("xclip", ["-selection", "clipboard", "-t", format, "-i"], { stdio: ["pipe", "ignore", "ignore"], detached: true });
        x.stdin.end(Buffer.from(bytes));
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
// A CDX as ChemDraw for Windows copies a caption: Arial "h", Symbol "n", Arial ", ", Symbol "d", Arial "+", in the
// legacy text only. ChemDraw draws it as hν, δ+ (issue 21).
function symbolCdx() {
  const le = (...v) => v.flatMap((x) => [x & 0xff, (x >> 8) & 0xff]), ascii = (s) => [...s].map((c) => c.charCodeAt(0));
  const prop = (tag, data) => [...le(tag, data.length), ...data];
  const obj = (tag, id, ...inner) => [...le(tag, id & 0xffff, id >>> 16), ...inner.flat(), 0, 0];
  const fonts = [[3, "Arial"], [5, "Symbol"]].flatMap(([id, name]) => [...le(id, 1252, name.length), ...ascii(name)]);
  const runs = [[0, 3], [1, 5], [2, 3], [4, 5], [5, 3]].flatMap(([start, font]) => le(start, font, 0, 200, 3));
  const at = le(0, 100, 0, 100); // 100 pt across and down, in 16.16 fixed point
  return new Uint8Array([...ascii("VjCD0100"), 4, 3, 2, 1, ...new Array(10).fill(0),
    ...obj(0x8000, 0, prop(0x0100, [...le(1, 2), ...fonts]), obj(0x8001, 1, obj(0x8006, 2, prop(0x0200, at), prop(0x0700, [...le(5), ...runs, ...ascii("hn, d+")]))))]);
}
const canvasText = () => page("return [...document.querySelectorAll('svg.canvas text')].map((t) => t.textContent).join('')");
const clipText = () => system.read(WIN ? "UnicodeText" : "UTF8_STRING").toString("utf8").replace(/\0+$/, "");
// A label on the page (the first caption whose text starts with `start`): the middle of its box in the window (CSS
// pixels), and whether the canvas is what is there (no panel over it).
const labelAt = (start) => page(`const t = [...document.querySelectorAll("svg.canvas text.caption")].find((e) => e.textContent.startsWith(arguments[0]));
  if (!t) return null;
  const r = t.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  return [x, y, !!document.elementFromPoint(x, y)?.closest("svg.canvas")]`, start);
// How many captions on the page have this text.
const labels = (text) => page(`return [...document.querySelectorAll("svg.canvas text.caption")].filter((e) => e.textContent === arguments[0]).length`, text);
// A double-click with the mouse at a point in the window (CSS pixels), through WebDriver's actions.
const doubleClick = ([x, y]) => wd("POST", `/session/${session}/actions`, { actions: [{ type: "pointer", id: "mouse", parameters: { pointerType: "mouse" }, actions: [
  { type: "pointerMove", duration: 0, origin: "viewport", x: Math.round(x), y: Math.round(y) },
  ...[1, 2].flatMap(() => [{ type: "pointerDown", button: 0 }, { type: "pointerUp", button: 0 }])] }] });
// A click, and a drag with the button held through 20 steps, with the mouse at points in the window (CSS pixels).
const click = ([x, y]) => wd("POST", `/session/${session}/actions`, { actions: [{ type: "pointer", id: "mouse", parameters: { pointerType: "mouse" }, actions: [
  { type: "pointerMove", duration: 0, origin: "viewport", x: Math.round(x), y: Math.round(y) }, { type: "pointerDown", button: 0 }, { type: "pointerUp", button: 0 }] }] });
const drag = ([x, y], [x2, y2]) => wd("POST", `/session/${session}/actions`, { actions: [{ type: "pointer", id: "mouse", parameters: { pointerType: "mouse" }, actions: [
  { type: "pointerMove", duration: 0, origin: "viewport", x: Math.round(x), y: Math.round(y) }, { type: "pointerDown", button: 0 },
  ...Array.from({ length: 20 }, (_, k) => ({ type: "pointerMove", duration: 25, origin: "viewport", x: Math.round(x + ((x2 - x) * (k + 1)) / 20), y: Math.round(y + ((y2 - y) * (k + 1)) / 20) })),
  { type: "pointerUp", button: 0 }] }] });
// Edit > Copy, and Octet's own copy it put on the clipboard (the drawing as a .oct file holds it). The clipboard is
// cleared first, so the copy read is the new one.
async function copied() {
  system.setText("-");
  await sleep(500);
  system.menu("Edit", "Copy");
  await until(`${OCTET} on the clipboard`, () => system.formats().includes(OCTET), 10_000);
  return DRY ? { structure: { atoms: [] }, captions: [{ text: "", x: 0 }], groups: [{ items: [] }] } : JSON.parse(system.read(OCTET).toString("utf8"));
}
const check = (ok, message) => { if (!DRY && !ok) throw new Error(message); };

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
  // Issue 38: New gave nothing while the first drawing was untouched (a blank page in place of a blank page).
  ["On the untouched first drawing, File > New opens another window, and Close Window there leaves the first", async () => {
    const before = await handles();
    system.menu("File", "New*");
    const next = await opened(before, "Untitled");
    await toWindow(next);
    await until("the new drawing", () => page("return !document.querySelector('main.home') && !!document.querySelector('svg.canvas')"));
    system.menu("File", CLOSE);
    await until("the new window to close", async () => (await handles()).length === before.length);
    await toWindow(drawing);
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
  ["Edit > Paste reads ChemDraw's CDX with Greek in the Symbol font as hν, δ+, and Edit > Undo takes it back", async () => {
    system.setData(CDX, symbolCdx());
    await sleep(500);
    system.menu("Edit", "Paste");
    await until("hν, δ+ in the drawing", async () => (await canvasText()).includes("hν, δ+"));
    system.menu("Edit", "Undo");
    await until("the caption gone", async () => !(await canvasText()).includes("δ"));
    await pasted(2);
  }],
  // Issue 23: a clipboard with only a type Octet cannot read (as Word's copy of a ChemDraw picture has OLE types).
  ["Edit > Paste of a clipboard Octet cannot read says so and pastes nothing", async () => {
    system.setData(WIN ? "Object Descriptor" : "application/x-octet-unreadable", [1, 2, 3, 4]);
    await sleep(500);
    system.menu("Edit", "Paste");
    const said = "Octet cannot read what is on the clipboard.";
    await until("the notice", () => page("return document.querySelector('.notice-text')?.textContent === arguments[0]", said));
    await pasted(2);
    await page("document.querySelector('.notice-close')?.click()");
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
    await page("document.querySelector(arguments[0]).dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))", nameField);
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
  // A page spectrum is a plain group of lines, curves and captions (Add to drawing > Spectrum): a double-click picks one
  // part, which takes the arrow keys, its text and a colour as any caption does, and the edits are kept in a copy as
  // Octet's own (a .oct file's) and as CDXML. Octane-3,5-dione's ¹H quartet at 2.42 is the label.
  ["Each part of a page spectrum can be picked alone, nudged, typed over and coloured, and the edits are kept as .oct and CDXML", async () => {
    const LABEL = "2.40 (q, 2H)", RED = "#B42323", PT = 1 / 14.4;
    system.setText("CCCC(=O)CC(=O)CC");
    await sleep(500);
    system.menu("Edit", "Paste");
    await until("octane-3,5-dione in the drawing", async () => (await oxygens()) === 2);
    system.menu("Structure", "Predict*");
    const add = `document.querySelector('section.spectrum button[aria-label="Add to drawing"]')`, item = `document.querySelector('[role=menu] [data-item="spectrum"]')`;
    await until("the predicted spectrum", () => page(`return !!${add} && !${add}.disabled`), 60_000);
    await page(`${add}.click()`);
    await until("Add to drawing's menu", () => page(`return !!${item}`));
    await page(`${item}.click()`);
    await until("the spectrum on the page", async () => !!(await labelAt("2.42")));
    // Add to drawing > Shifts beside atoms puts the panel's numbers on the page, each once, and the panel then draws no
    // second copy. Undo takes them off, and the panel shows them again.
    const overlay = () => page(`return [...document.querySelectorAll("svg.canvas text.nmr-shift")].map((e) => e.textContent)`);
    const shifts = DRY ? [] : await overlay(), texts = [...new Set(shifts)], had = await Promise.all(texts.map(labels));
    await page(`${add}.click()`);
    await until("Add to drawing's menu", () => page(`return !!${item}`));
    await page(`document.querySelector('[role=menu] [data-item="shifts"]').click()`);
    await until("the shifts on the page", async () => (await overlay()).length === 0);
    const has = await Promise.all(texts.map(labels));
    check(shifts.length > 0 && texts.every((t, k) => has[k] === had[k] + shifts.filter((s) => s === t).length), `shifts ${JSON.stringify(shifts)}: ${JSON.stringify(had)} on the page before, ${JSON.stringify(has)} after`);
    system.menu("Edit", "Undo");
    await until("the shifts in the panel again", async () => (await overlay()).length === shifts.length);
    await page(`document.querySelector('button[aria-label="Close spectrum"]').click()`);
    await until("the panel closed", () => page("return !document.querySelector('section.spectrum')"));
    // Select's double-click picks a part of a group. With a drawing tool (the Bond tool is in hand in a new drawing), a
    // double-click on a caption opens its text at once.
    await page(`document.querySelector('button[aria-label="Select"]').click()`);
    await until("the Select tool", () => page(`return document.querySelector('button[aria-label="Select"]').getAttribute("aria-pressed") === "true"`));
    const at = DRY ? [0, 0, true] : await labelAt("2.42");
    check(at[2], "something is over the label 2.42");
    // A click picks the whole spectrum; a double-click picks the one label.
    await doubleClick(at);
    let got = await copied();
    check(got.captions?.length === 1 && !got.arrows && !got.structure.atoms.length && got.captions[0].text.startsWith("2.42"), `picked: ${JSON.stringify(got.captions?.map((c) => c.text))}, ${got.arrows?.length ?? 0} lines and curves`);
    const x0 = got.captions[0].x;
    // Left moves it 1 pt.
    system.key("Left");
    got = await copied();
    check(Math.abs(x0 - got.captions[0].x - PT) < 0.001, `Left moved the label from x ${x0} to ${got.captions[0].x}`);
    const x1 = got.captions[0].x;
    // A second double-click opens its text, typed over here.
    await doubleClick(at);
    await until("the label's text box", () => page("return !!document.activeElement?.matches('.caption-box')"));
    await page(`const el = document.activeElement, r = document.createRange(); r.selectNodeContents(el); getSelection().removeAllRanges(); getSelection().addRange(r);
      document.execCommand("insertText", false, arguments[0])`, LABEL);
    await page("document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))");
    await until("the text box closed", () => page("return !document.querySelector('.caption-box')"));
    system.menu("Colour", "Red");
    got = await copied();
    check(got.captions?.length === 1 && got.captions[0].text === LABEL && got.captions[0].colour === RED && Math.abs(got.captions[0].x - x1) < 0.001, `the label: ${JSON.stringify(got.captions)}`);
    // The spectrum alone, picked by a click, and its frame's right handle dragged 200 px: the plot grows, every caption
    // keeps the document's size, and the edited label keeps its text and colour. Undo takes it back in one step.
    await page("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))");
    await click(at);
    const handle = DRY ? [0, 0] : await page(`const hs = [...document.querySelectorAll("svg.canvas rect.resize-handle")].map((e) => e.getBoundingClientRect());
      const ys = hs.map((r) => r.top + r.height / 2), mid = (Math.min(...ys) + Math.max(...ys)) / 2;
      const r = hs.filter((r) => Math.abs(r.top + r.height / 2 - mid) < 2).sort((p, q) => q.left - p.left)[0];
      return r && [r.left + r.width / 2, r.top + r.height / 2]`);
    check(handle, "no right handle on the spectrum's frame");
    const spectrumOf = (all) => { const g = all.groups?.find((x) => x.items.length > 10), axis = (all.arrows ?? []).find((a) => a.role?.role === "axis"); return { g, axis: axis && axis.x2 - axis.x1 }; };
    system.menu("Edit", "Select All");
    const was = spectrumOf(await copied());
    await page(`window.__frames = []; const f = (t) => { if (window.__frames) { window.__frames.push(t); requestAnimationFrame(f); } }; requestAnimationFrame(f)`);
    await page("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))");
    await click(at);
    await drag(handle, [handle[0] + 200, handle[1]]);
    const gaps = DRY ? [] : await page("const f = window.__frames; window.__frames = undefined; return f.slice(1).map((t, k) => t - f[k]).sort((a, b) => a - b)");
    if (gaps.length) log(`    frames during the resize: median ${gaps[gaps.length >> 1].toFixed(1)} ms, slowest ${gaps[gaps.length - 1].toFixed(1)} ms`);
    system.menu("Edit", "Select All");
    const grown = await copied(), now = spectrumOf(grown), red = (grown.captions ?? []).filter((c) => c.text === LABEL);
    check(was.axis > 0 && now.axis > was.axis + 5 && now.g?.plot?.frame[0] > was.g?.plot?.frame[0], `the axis from ${was.axis} to ${now.axis} bond lengths`);
    check((grown.captions ?? []).every((c) => c.size === undefined) && red.length === 1 && red[0].colour === RED, `captions: ${JSON.stringify(grown.captions?.filter((c) => c.size || c.text === LABEL))}`);
    system.menu("Edit", "Undo");
    system.menu("Edit", "Select All");
    const undone = spectrumOf(await copied());
    check(Math.abs(undone.axis - was.axis) < 0.001, `Undo: the axis is ${undone.axis} bond lengths, not ${was.axis}`);
    // The whole drawing, copied as Octet's own and as CDXML, and pasted back from each: every copy has the label as
    // edited, and the spectrum in a plain group with every part.
    system.menu("Edit", "Select All");
    const all = await copied(), parts = all.groups?.[0]?.items.length, cdxml = DRY ? "" : system.read(CDXML).toString("utf8").replace(/\0+$/, "");
    check(all.groups?.length === 1 && !all.groups[0].integral && parts > 10, `groups: ${JSON.stringify(all.groups?.map((g) => [g.items.length, !!g.integral]))}`);
    system.menu("Edit", "Paste");
    await until("the copy pasted", async () => (await labels(LABEL)) === 2);
    system.setText(cdxml);
    await sleep(500);
    system.menu("Edit", "Paste");
    await until("the CDXML pasted", async () => (await labels(LABEL)) === 3);
    system.menu("Edit", "Select All");
    const back = await copied(), edited = (back.captions ?? []).filter((c) => c.text === LABEL);
    check(edited.length === 3 && edited.every((c) => c.colour === RED), `the labels: ${JSON.stringify(edited)}`);
    check(back.groups?.length === 3 && back.groups.every((g) => !g.integral && g.items.length === parts), `groups: ${JSON.stringify(back.groups?.map((g) => [g.items.length, !!g.integral]))}`);
    // The window closes without saving; the first drawing stays.
    const before = await handles();
    system.menu("File", CLOSE);
    const dontSave = "[...document.querySelectorAll('button')].find((b) => /Don.t Save/.test(b.textContent))";
    await until("the question", () => page(`return !!${dontSave}`));
    await page(`${dontSave}.click()`);
    await until("the window to close", async () => (await handles()).length === before.length - 1);
    await toWindow(drawing);
  }],
  // Issue 38: closing the drawing in Home's window left Octet running with no window.
  ["File > Close Window on the first drawing shows Home in its window, and Quick start opens a drawing there again", async () => {
    const before = await handles();
    system.menu("File", CLOSE);
    const dontSave = "[...document.querySelectorAll('button')].find((b) => /Don.t Save/.test(b.textContent))";
    await until("the question", () => page(`return !!${dontSave}`));
    await page(`${dontSave}.click()`);
    await until("Home in the first drawing's window", () => page("return !!document.querySelector('main.home .home-tile.new')"));
    if (!DRY && (await handles()).length !== before.length) throw new Error("Close Window closed Home's window");
    await page("document.querySelector('main.home .home-tile.new').click()");
    await until("the drawing", () => page("return !document.querySelector('main.home') && !!document.querySelector('svg.canvas')"));
    system.setText("CCO");
    await sleep(500);
    system.menu("Edit", "Paste");
    await pasted(1);
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
