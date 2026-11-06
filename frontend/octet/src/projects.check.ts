// Run: node src/projects.check.ts. Fails loudly if Home's projects store loses or mixes up a project, keeps a drawing
// twice, takes a drawing with a project that goes, leaves a thumbnail file behind, reads a damaged or newer store as
// anything but empty, keeps a colour that is not #RRGGBB, or takes a picture for a thumbnail that is too large; if a
// drawing's project dots move or lose the projects it is in; if Home's sections lose one, read back wrong or stop
// pairing New and Templates; or if Home's keys, tooltips or menus change.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  addDrawings, cleanName, colourOf, createProject, deleteProject, drawingName, emptyStore, folderOf, folderTones, forget, freeName, lastUsed, MAX_IN_PROJECT, MAX_NAME,
  MAX_PROJECTS, PROJECT_COLOUR, projectOf, projectsWith, readStore, relocate, removeDrawing, renameProject, resetPicture, setPicture, setProjectColour,
  setProjectThumb, STORE_VERSION, thumbIds, tilde, UNTITLED, writeStore, type HomeStore,
} from "./projects.ts";
import { moveSection, readLayout, rowsOf, SECTIONS } from "./homeLayout.ts";
import { cover, inputProblem, INPUT_TOO_LARGE, MAX_INPUT, sizeProblem, THUMB_H, THUMB_W } from "./thumbs.ts";
import { NOT_PICTURE, TOO_MANY_PIXELS } from "./picture.ts";
import { tileTo } from "./keys.ts";

const T1 = "0123456789abcdef", T2 = "fedcba9876543210", T3 = "00000000000000aa", T4 = "00000000000000bb";
const A = "/Users/sam/Thesis/aspirin.oct", B = "/Users/sam/Thesis/scheme 1.cdxml", C = "C:\\Users\\sam\\cycle.cdx";

// ——— Create and rename ———
let s: HomeStore = emptyStore();
s = createProject(s, "  Thesis\tchapter 2 ", "p1", 100);
assert.deepEqual(s.projects, [{ id: "p1", name: "Thesis chapter 2", made: 100, drawings: [] }], "a name is tidied");
s = createProject(s, "", "p2", 101);
assert.equal(projectOf(s, "p2")!.name, UNTITLED, "no name: Untitled project");
s = createProject(s, "untitled FOLDER", "p3", 102);
assert.equal(projectOf(s, "p3")!.name, "untitled FOLDER 2", "a name another project has (letter case aside) takes the next number");
assert.equal(createProject(s, "Again", "p1", 103), s, "an id in use makes nothing");
assert.deepEqual(s.projects.map((p) => p.id), ["p1", "p2", "p3"], "new projects go after the others");
assert.equal(freeName(s, "x".repeat(200)).length, MAX_NAME);
assert.equal(cleanName("a\u0000b\nc"), "a b c");
s = renameProject(s, "p2", "Group meeting");
assert.equal(projectOf(s, "p2")!.name, "Group meeting");
assert.equal(renameProject(s, "p2", "   "), s, "an empty name changes nothing");
assert.equal(renameProject(s, "p2", "Group meeting"), s, "the same name changes nothing");
assert.equal(projectOf(renameProject(s, "p3", "thesis chapter 2"), "p3")!.name, "thesis chapter 2 2", "a name another project has takes the next number");
assert.equal(renameProject(s, "nope", "x"), s);
let many = emptyStore();
for (let k = 0; k < MAX_PROJECTS + 5; k++) many = createProject(many, `P${k}`, `m${k}`, k);
assert.equal(many.projects.length, MAX_PROJECTS, "projects stop at the most Octet keeps");

// ——— Add and remove drawings: one folder at a time ———
let r = addDrawings(s, "p1", [{ path: A }, { path: B, name: "Scheme 1" }, { path: A }], 200);
assert.equal(r.added, 2, "a drawing goes in once");
assert.equal(r.moved, 0);
s = r.store;
assert.deepEqual(projectOf(s, "p1")!.drawings, [{ path: A, name: "aspirin", added: 200 }, { path: B, name: "Scheme 1", added: 200 }]);
assert.equal(projectOf(s, "p1")!.used, 200, "a project with a drawing just put in is used");
r = addDrawings(s, "p1", [{ path: A }], 201);
assert.equal(r.added, 0);
assert.equal(r.store, s, "a drawing in the project already changes nothing");
r = addDrawings(s, "p2", [{ path: A }, { path: C }], 202);
s = r.store;
assert.deepEqual([r.added, r.moved], [2, 1], "A moved from Thesis; C was in no folder");
assert.deepEqual(projectsWith(s, A).map((p) => p.id), ["p2"], "one folder at a time: putting a drawing in a folder takes it out of the other");
assert.deepEqual(projectOf(s, "p1")!.drawings.map((x) => x.path), [B], "the folder it left keeps its other drawings");
assert.equal(projectOf(s, "p1")!.used, 202, "the folder it left counts as used");
assert.equal(folderOf(s, A)!.id, "p2");
assert.equal(folderOf(s, "/not/in/any.oct"), undefined);
assert.equal(drawingName(C), "cycle");
assert.equal(addDrawings(s, "p1", [{ path: "" }, { path: "x".repeat(5000) }], 1).added, 0, "no empty or overlong paths");
assert.equal(addDrawings(s, "nope", [{ path: A }], 1).added, 0);
assert.equal(addDrawings(s, "nope", [{ path: A }], 1).store, s, "no such folder: the drawing stays where it is");
const full = addDrawings(emptyStore(), "x", [], 0);
assert.equal(full.added, 0);
let big = createProject(emptyStore(), "Big", "big", 0);
big = addDrawings(big, "big", Array.from({ length: MAX_IN_PROJECT + 10 }, (_, k) => ({ path: `/d/${k}.oct` })), 0).store;
assert.equal(projectOf(big, "big")!.drawings.length, MAX_IN_PROJECT, "a project stops at the most Octet keeps");

// Automatic pictures: a copy for each drawing in a folder. A move keeps it; out of its folder, the copy goes.
s = setPicture(s, A, "auto", T1).store;
s = setPicture(s, C, "auto", T2).store;
const back = addDrawings(s, "p1", [{ path: A }], 210).store;
assert.equal(back.pictures[A].auto, T1, "moved to another folder: the picture stays");
assert.deepEqual(projectsWith(back, A).map((p) => p.id), ["p1"]);
let d = removeDrawing(s, "p2", A);
assert.deepEqual(d.drop, [T1], "in no folder: its picture goes");
assert.equal(d.store.pictures[A], undefined);
assert.deepEqual(projectOf(d.store, "p2")!.drawings.map((x) => x.path), [C], "the other drawings stay");
assert.equal(projectOf(removeDrawing(s, "p2", A, 300).store, "p2")!.used, 300, "taking a drawing out uses the project too");
assert.equal(removeDrawing(s, "p3", A, 300).store, s, "a drawing not in the project: nothing changes");

// Delete a project: no drawing goes with it, only thumbnails nothing else uses.
s = setProjectThumb(s, "p2", T3).store;
const del = deleteProject(s, "p2");
assert.deepEqual(del.store.projects.map((p) => p.id), ["p1", "p3"]);
assert.deepEqual(del.drop.sort(), [T1, T2, T3].sort(), "its own thumbnail, and the pictures of its drawings (in no other folder now)");
assert.equal(del.store.pictures[A], undefined);
assert.equal(del.store.pictures[C], undefined);
assert.deepEqual(deleteProject(s, "nope"), { store: s, drop: [] });

// ——— Missing files: Locate… moves a drawing in its folder, with its thumbnails ———
const moved = "/Users/sam/Archive/aspirin.oct";
s = setPicture(s, A, "own", T4).store;
const loc = relocate(s, A, moved);
assert.ok(loc.store.projects.every((p) => !p.drawings.some((x) => x.path === A)));
assert.deepEqual(projectsWith(loc.store, moved).map((p) => p.id), ["p2"]);
assert.equal(projectOf(loc.store, "p2")!.drawings[0].path, moved, "it keeps its place in the folder");
assert.deepEqual(loc.store.pictures[moved], { own: T4, auto: T1 });
assert.equal(loc.store.pictures[A], undefined);
assert.deepEqual(loc.drop, []);
// Located onto a drawing another folder has already: it stays in one, the folder used last (the first on a tie).
const onto = relocate(s, A, B);
assert.deepEqual(projectOf(onto.store, "p1")!.drawings.map((x) => x.path), [B]);
assert.deepEqual(projectOf(onto.store, "p2")!.drawings.map((x) => x.path), [C]);
assert.equal(relocate(s, A, A).store, s);
// A store from before one folder at a time: each drawing stays in the folder used last; others keep their drawings.
const old = readStore(JSON.stringify({ version: 1, projects: [
  { id: "a", name: "A", made: 5, used: 20, drawings: [{ path: A }, { path: "/d/x.oct" }] },
  { id: "b", name: "B", made: 1, used: 90, drawings: [{ path: A }] },
  { id: "c", name: "C", made: 30, drawings: [{ path: A }, { path: "/d/y.oct" }] },
] })).store;
assert.deepEqual(old.projects.map((p) => p.drawings.map((x) => x.path)), [["/d/x.oct"], [A], ["/d/y.oct"]], "as home.rs does (one_folder)");
assert.equal(lastUsed(old.projects[2]), 30, "made, when it was never used");

// ——— Thumbnails: set, replace and reset ———
let t = setPicture(s, B, "own", T1);
assert.deepEqual(t.drop, []);
t = setPicture(t.store, B, "own", T2);
assert.deepEqual(t.drop, [T1], "a new thumbnail takes the old one's place, and the old file goes");
t = resetPicture(t.store, B);
assert.deepEqual(t.drop, [T2], "Use Automatic Thumbnail");
assert.equal(t.store.pictures[B], undefined);
assert.deepEqual(resetPicture(t.store, B), { store: t.store, drop: [] }, "no thumbnail of its own: nothing to reset");
assert.equal(setPicture(s, B, "own", "../../x").store, s, "a thumbnail is named by 16 hex digits only");
let pt = setProjectThumb(s, "p1", T1);
pt = setProjectThumb(pt.store, "p1", undefined);
assert.deepEqual(pt.drop, [T1], "Use automatic thumbnail: the folder goes back to plain");
assert.equal(projectOf(pt.store, "p1")!.thumb, undefined);
assert.deepEqual(new Set(thumbIds(setProjectThumb(s, "p1", T2).store)), new Set([T1, T2, T3, T4]), "every thumbnail the store uses, to load");
// Remove from Home: a drawing in no project takes its thumbnails with it.
const lone = setPicture(emptyStore(), "/d/lone.oct", "own", T3).store;
assert.deepEqual(forget(lone, "/d/lone.oct"), { store: { ...lone, pictures: {} }, drop: [T3] });
assert.deepEqual(forget(s, A).drop, [], "in a project: it keeps them");
assert.equal(projectOf(setProjectThumb(setProjectColour(s, "p1", "#22775B"), "p1", T2).store, "p1")!.colour, "#22775B", "a new thumbnail keeps the colour");

// ——— Colours: a project's folder and dots ———
assert.equal(colourOf(projectOf(s, "p1")!), PROJECT_COLOUR, "no colour: Octet Blue");
let c = setProjectColour(s, "p1", "#b42323");
assert.equal(projectOf(c, "p1")!.colour, "#B42323", "kept in capitals");
assert.equal(setProjectColour(c, "p1", "#B42323"), c, "the same colour changes nothing");
assert.equal(projectOf(setProjectColour(c, "p1", PROJECT_COLOUR), "p1")!.colour, undefined, "Octet Blue goes back to no colour");
for (const bad of ["red", "#FFF", "#21 C99", "#213C99;x", "url(x)", "#GGGGGG", ""]) assert.equal(setProjectColour(s, "p1", bad), s, bad);
assert.equal(setProjectColour(s, "nope", "#000000"), s);
c = readStore(writeStore(c)).store;
assert.equal(projectOf(c, "p1")!.colour, "#B42323", "a colour reads back");
const odd = readStore(JSON.stringify({ version: 1, projects: [{ id: "a", name: "A", colour: "#0f172a", drawings: [] }, { id: "b", name: "B", colour: "red; background:url(x)", drawings: [] }, { id: "c", name: "C", colour: 7, drawings: [] }] }));
assert.deepEqual(odd.store.projects.map((p) => p.colour), ["#0F172A", undefined, undefined], "only #RRGGBB is read; anything else is Octet Blue");
// A folder near black has a lighter back, so its two parts show; others a darker one.
assert.deepEqual(folderTones("#000000"), { front: "#000000", back: "#383838", lip: "#525252", dark: true });
assert.equal(folderTones("#213C99").dark, false);
assert.ok(parseInt(folderTones("#213C99").back.slice(1), 16) < parseInt("213C99", 16), "Octet Blue's back is darker");
assert.equal(folderTones("nonsense").front, PROJECT_COLOUR);

// ——— A drawing's place in its tooltip: the home folder as ~ ———
assert.equal(tilde("/Users/sam/Documents/a.oct", "/Users/sam"), "~/Documents/a.oct");
assert.equal(tilde("/Users/sam/Documents/a.oct", "/Users/sam/"), "~/Documents/a.oct");
assert.equal(tilde("/Users/samuel/a.oct", "/Users/sam"), "/Users/samuel/a.oct", "only the home folder itself");
assert.equal(tilde("/Users/Shared/a.oct", "/Users/sam"), "/Users/Shared/a.oct");
assert.equal(tilde("C:\\Users\\sam\\a.oct", "C:\\Users\\sam"), "C:\\Users\\sam\\a.oct", "Windows keeps the full place");
assert.equal(tilde("/Users/sam/a.oct"), "/Users/sam/a.oct", "no home folder known");

// ——— Home's sections: all four once, in the order saved; New and Templates side by side when next to each other ———
assert.deepEqual(SECTIONS, ["new", "templates", "recent", "projects"], "New, Templates, Recent, then Projects for a new user");
assert.deepEqual(readLayout(undefined, undefined), { order: [...SECTIONS], folded: [] });
assert.deepEqual(readLayout(["projects", "recent"], ["templates"]), { order: ["projects", "recent", "new", "templates"], folded: ["templates"] }, "sections the save does not name follow in Octet's order");
assert.deepEqual(readLayout(["recent", "recent", "bogus", 7, null, "new"], "templates"), { order: ["recent", "new", "templates", "projects"], folded: [] }, "duplicates and unknown names go");
assert.deepEqual(readLayout({ length: 2 }, [["new"]]), readLayout([], []), "not a list: Octet's order");
assert.deepEqual(moveSection([...SECTIONS], "recent", -1, true), ["new", "recent", "templates", "projects"]);
assert.deepEqual(moveSection([...SECTIONS], "projects", 1, true), [...SECTIONS], "the last cannot go down");
assert.deepEqual(moveSection([...SECTIONS], "new", -1, true), [...SECTIONS], "the first cannot go up");
assert.deepEqual(moveSection([...SECTIONS], "projects", 0), ["projects", "new", "templates", "recent"], "a drag drops it in a place");
assert.deepEqual(rowsOf([...SECTIONS], []), [["new", "templates"], ["recent"], ["projects"]]);
assert.deepEqual(rowsOf(["templates", "new", "recent", "projects"], []), [["templates", "new"], ["recent"], ["projects"]]);
assert.deepEqual(rowsOf(["new", "recent", "templates", "projects"], []), [["new"], ["recent"], ["templates"], ["projects"]]);
assert.deepEqual(rowsOf([...SECTIONS], ["templates"]), [["new"], ["templates"], ["recent"], ["projects"]], "a folded section has its own row");

// ——— Reading and writing: version, damage ———
const text = writeStore(s);
assert.equal(JSON.parse(text).version, STORE_VERSION);
assert.deepEqual(readStore(text), { store: s }, "a store reads back as it was written");
assert.deepEqual(readStore(null), { store: emptyStore() }, "no file: no projects, and no notice");
assert.deepEqual(readStore(""), { store: emptyStore() });
for (const bad of ["{", "[]", "null", "42", '{"projects":[]}', '{"version":"1","projects":[]}', '{"version":1,"projects":{}}'])
  assert.deepEqual(readStore(bad), { store: emptyStore(), problem: "damaged" }, bad);
assert.deepEqual(readStore(JSON.stringify({ ...JSON.parse(text), version: STORE_VERSION + 1 })), { store: emptyStore(), problem: "newer" }, "a later Octet's store is not read");
// One bad entry loses only that entry.
const mixed = readStore(JSON.stringify({
  version: 1,
  projects: [
    { id: "ok", name: "Fine", made: 5, thumb: T1, drawings: [{ path: A, name: "aspirin", added: 1 }, { path: A }, { path: 7 }, "junk", { path: B }] },
    { id: "ok", name: "Same id", drawings: [] },
    { id: "../x", name: "Bad id", drawings: [] },
    { id: "blank", name: "   ", drawings: [] },
    { id: "nothumb", name: "No thumb", made: -4, thumb: "../../etc/passwd", drawings: "nope" },
    "junk",
  ],
  pictures: { [A]: { own: T2, auto: "x" }, [B]: { own: 5 }, [""]: { own: T3 }, [C]: "nope" },
  extra: true,
}));
assert.equal(mixed.problem, undefined);
assert.deepEqual(mixed.store.projects, [
  { id: "ok", name: "Fine", made: 5, thumb: T1, drawings: [{ path: A, name: "aspirin", added: 1 }, { path: B, name: "scheme 1", added: 0 }] },
  { id: "nothumb", name: "No thumb", made: 0, drawings: [] },
]);
assert.deepEqual(mixed.store.pictures, { [A]: { own: T2 } });

// ——— Thumbnail pictures: hostile files are refused before they are decoded ———
const png = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0]);
assert.equal(inputProblem(png), undefined);
assert.equal(inputProblem(new TextEncoder().encode("<svg onload=alert(1)>")), NOT_PICTURE, "by its bytes, never its name");
const huge = new Uint8Array(MAX_INPUT + 1);
huge.set(png);
assert.equal(inputProblem(huge), INPUT_TOO_LARGE);
assert.equal(sizeProblem(0, 10), NOT_PICTURE);
assert.equal(sizeProblem(20000, 10), TOO_MANY_PIXELS);
assert.equal(sizeProblem(8000, 8000), TOO_MANY_PIXELS, "64 million pixels");
assert.equal(sizeProblem(4032, 3024), undefined, "a phone photo");
// Cut to the tile's 4:3 from the middle.
assert.equal(THUMB_W / THUMB_H, 4 / 3);
assert.deepEqual(cover(4000, 3000), { sx: 0, sy: 0, sw: 4000, sh: 3000 });
assert.deepEqual(cover(1600, 900), { sx: 200, sy: 0, sw: 1200, sh: 900 }, "wide: its middle");
assert.deepEqual(cover(900, 1600), { sx: 0, sy: 462.5, sw: 900, sh: 675 }, "tall: its middle");

// ——— Home: its sections, each a landmark with its heading, and its keys ———
const home = readFileSync(new URL("./Home.tsx", import.meta.url), "utf8");
assert.match(home, /const bodies: Record<SectionId,/, "every section has its tiles");
assert.match(home, /TITLES: Record<SectionId, string> = \{ new: "New", templates: "Templates", recent: "Recent", projects: "Folders" \}/);
assert.match(home, /<section className=\{cls\} data-section=\{id\} aria-labelledby=\{`\$\{id\}-title`\}>/, "each section is a <section> named by its heading, so screen readers list it as a region");
assert.match(home, /aria-expanded=\{!heading\.folded\}/, "a heading says whether its section is open");
assert.match(home, /e\.key === "Enter" && at < 0/, "Return starts Quick start (decision 0003), wherever New is");
assert.match(home, /querySelector<HTMLElement>\('\[data-tile="new"\]'\)\?\.focus\(\{ preventScroll: true \}\)/, "Quick start has the focus when Home opens");
assert.match(home, /roving/, "one Tab stop for each section's tiles");
assert.ok(!/<Menu\b|className="strip|role="menu"/.test(home.replace(/import[^;]+;/g, "")), "Home's menus are ContextMenu (src/Menu.tsx), not menus of its own");
assert.match(home, /ContextMenu/);
assert.match(home, /<ColourPop /, "Custom colour… is the colour picker the Actions panel uses (src/ColourPicker.tsx)");
// A tile's id is data-tile: data-key is a control's shortcut, which the tooltip shows as a key (src/Tooltip.tsx).
assert.ok(!/data-key|dataset\.key/.test(home.replace("data-key={p.back.key}", "")), "no data-key on Home but the back button's Esc");
// Home opened over a drawing goes back to it: a button in the head, and Escape.
assert.match(home, /e\.key === "Escape" && p\.back/, "Escape goes back to the drawing");
assert.match(home, /data-tip=\{tilde\(d\.path, lib\.home\)\}/, "a drawing's tooltip is its place");
// Under each tile, real buttons with words, always on show: Add to folder and Change thumbnail under a drawing,
// Thumbnail, Colour and Rename under a folder. No project dots any more.
for (const name of [">Add to folder<", ">Change thumbnail<", ">Thumbnail<", "Colour\n", ">Rename<"]) assert.ok(home.includes(name), name);
assert.ok(!/home-dot|dotsFor/.test(home), "no project dots");
assert.match(home, /b\.closest\(".home-slot"\) === stop\.closest\(".home-slot"\) \? 0 : -1/, "only the Tab stop tile's buttons are Tab stops");
assert.match(home, /TITLES: Record<SectionId, string> = \{[^}]*projects: "Folders" \}/);
// The arrow keys move between tiles across sections: the New row, then a section of four wide tiles under it.
const rect = (x: number, y: number, w = 150, h = 140) => ({ x, y, width: w, height: h });
const tiles = [rect(0, 0), rect(200, 0), rect(350, 0), rect(500, 0), rect(0, 300, 230, 200), rect(250, 300, 230, 200), rect(500, 300, 230, 200), rect(0, 600, 230, 200)];
assert.equal(tileTo("ArrowDown", 0, tiles), 4, "down from New into Recent");
assert.equal(tileTo("ArrowDown", 1, tiles), 5, "to the nearest tile in the row below");
assert.equal(tileTo("ArrowDown", 5, tiles), 7, "down from Recent into Projects");
assert.equal(tileTo("ArrowUp", 7, tiles), 4);
console.log("projects.check: ok");
