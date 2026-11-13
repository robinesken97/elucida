// The body of an async function that scripts/look/webkit.swift runs in the app's page. It goes through the app (Home, a
// drawing, the Structure panel, the spectrum panel with two tabs, the template library, a caption with the paste
// offer, every Settings page, the command palette) and lets the app's own watch (src/lookwatch.ts) measure each one.
// It returns JSON: the places it reached, and every "look:" line the watch wrote. Add a place here when the app gets
// a new panel, dialog or page.
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const until = async (find, ms = 10000) => { const t = Date.now(); while (Date.now() - t < ms) { const v = find(); if (v) return v; await wait(100); } return null; };
const out = { engine: navigator.userAgent.replace(/^.*\) /, ""), reached: [], missed: [] };
// The watch measures a moment after each click and key: give it one, and the time to settle.
const measure = async (place, there = true) => {
  if (!there) { out.missed.push(place); return; }
  window.dispatchEvent(new PointerEvent("pointerup", { bubbles: true }));
  await wait(1300);
  out.reached.push(place);
};
const key = (init) => { for (const t of [document.activeElement, document.body, window]) t?.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, cancelable: true, ...init })); };
const button = (text) => [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === text);
const labelled = (label) => document.querySelector(`[aria-label="${label}"]`);

await until(() => document.querySelector(".home, .editor"));
await wait(1200);
if (button("Skip")) await measure("the welcome page"); // the first run only
button("Skip")?.click();
await wait(900);
await measure("Home", !!document.querySelector(".home"));
document.querySelector(".home-tile.new")?.click();
await measure("a new drawing", !!(await until(() => document.querySelector(".actions .action"))));
[...document.querySelectorAll(".coach button")].find((b) => /skip/i.test(b.textContent))?.click();
await wait(400);

// A structure by name, so the panels have something to show.
[...document.querySelectorAll(".action")].find((b) => /name to structure/i.test(b.textContent))?.click();
const name = await until(() => document.querySelector("input.name-field"));
await measure("the name field", !!name);
if (name) {
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(name, "aspirin");
  name.dispatchEvent(new Event("input", { bubbles: true }));
  await wait(2000);
  name.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true, cancelable: true }));
  await wait(2500);
}
if (!labelled("Add a caption")) key({ key: "a", code: "KeyA", metaKey: true });
await measure("the Structure panel", !!(await until(() => labelled("Add a caption"), 4000)));

// The spectrum panel: one tab, then two (each with its X, and the + after them).
labelled("Predict ¹³C-NMR shifts")?.click();
await measure("the spectrum panel", !!(await until(() => document.querySelector(".spectrum-controls"), 6000)));
document.querySelector(".tab-add")?.click();
const second = await until(() => document.querySelector(".strip .variant"), 3000);
second?.click();
await wait(1200);
await measure("two spectrum tabs", !!second && document.querySelectorAll(".spectrum-tab").length === 2);
[...document.querySelectorAll(".spectrum .panel-controls button")].find((b) => b.getAttribute("aria-label") === "Minimise")?.click();
await wait(900);
await measure("a minimised panel's pill", !!document.querySelector(".pill"));

// The template library, from the ring tool's menu.
const ring = [...document.querySelectorAll(".tool")].find((t) => /benzene|ring/i.test(t.getAttribute("aria-label") ?? ""));
ring?.click(); await wait(500); ring?.click();
const templates = await until(() => document.querySelector('.variant[aria-haspopup="dialog"]'), 3000);
await measure("a tool's menu", !!templates);
templates?.click();
await measure("the template library", !!(await until(() => document.querySelector(".segmented.library-kind"), 4000)));
key({ key: "Escape" });
await wait(600);

// A caption, and the offer that comes when a reference is pasted into it with its formatting.
key({ key: "a", code: "KeyA", metaKey: true });
await wait(800);
labelled("Add a caption")?.click();
const caption = await until(() => document.querySelector(".caption-box"), 4000);
if (caption) {
  caption.focus(); getSelection().selectAllChildren(caption); getSelection().collapseToEnd();
  const data = new DataTransfer();
  data.setData("text/plain", "Smith, J. et al. J. Am. Chem. Soc. 2021, 143, 1234.");
  data.setData("text/html", "Smith, J. et al. <i>J. Am. Chem. Soc.</i> <b>2021</b>, <i>143</i>, 1234.");
  caption.dispatchEvent(new ClipboardEvent("paste", { bubbles: true, cancelable: true, clipboardData: data }));
}
await measure("the paste offer", !!(await until(() => document.querySelector(".paste-offer"), 4000)));
key({ key: "Escape" });
await wait(600);

// Every Settings page.
document.querySelector(".actions-reopen")?.click();
await wait(600);
document.querySelector(".actions-settings")?.click();
await wait(1000);
const pages = [...document.querySelectorAll(".module")];
await measure("Settings", pages.length > 0);
for (const page of pages) { page.click(); await wait(500); await measure(`Settings, ${page.textContent.trim()}`); }
document.querySelector(".settings-window .actions-close")?.click();
await wait(600);

// The command palette (this key opens it in a browser; the app has it in a menu).
key({ key: "a", code: "KeyA", metaKey: true, shiftKey: true });
await measure("the command palette", !!(await until(() => document.querySelector(".command-palette"), 3000)));

out.look = window.__look;
out.errors = window.__errors.slice(0, 10);
return JSON.stringify(out);
