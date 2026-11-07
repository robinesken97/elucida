// Run: node src/purpose.check.ts. Fails loudly if a purpose (Paper, Thesis, Slides, Poster or the user's own template)
// stops giving its sizes, page and outlines (IDEA-SIZE-1 to 15), or Quick start stops being the seamless default.
import assert from "node:assert/strict";
import { DEFAULT_STYLE, PAGES, edgeAt, PRESETS, PURPOSES, QUICK, QUICK_STYLE, forPurpose, outlines, pageSize, pickPage, presetOf, purposeOf, purposeStyle, readPurposes, readStyle, styleFor, withScale } from "./docstyle.ts";
import { fromCdxml, toCdxml } from "./cdxml.ts";
import { readFileSync } from "node:fs";

// Each purpose is ACS Document 1996 at its scale, on its page.
{
  const paper = purposeStyle("paper"), slides = purposeStyle("slides"), poster = purposeStyle("poster"), thesis = purposeStyle("thesis");
  assert.deepEqual({ ...paper, purpose: undefined }, { ...DEFAULT_STYLE, purpose: undefined }, "Paper is the default style (brief rule 6)");
  assert.deepEqual([paper.preset, thesis.preset, slides.preset, poster.preset], Array(4).fill("ACS Document 1996"), "every purpose keeps the journal's name");
  assert.deepEqual([slides.bond, slides.line, slides.bold, slides.labelSize, slides.captionSize, slides.scale], [28.8, 1.2, 4, 20, 20, 2]);
  assert.deepEqual([poster.bond, poster.line, poster.labelSize, poster.scale], [43.2, 1.8, 30, 3]);
  assert.deepEqual(pageSize(slides), [338.67, 190.5], "Slides: PowerPoint's 16:9, landscape");
  assert.deepEqual(pageSize(poster), [841, 1189], "Poster: A0 portrait");
  assert.deepEqual(pageSize(thesis), [210, 297], "Thesis: A4");
  for (const kind of Object.keys(PURPOSES) as (keyof typeof PURPOSES)[]) {
    const s = purposeStyle(kind);
    assert.deepEqual(readStyle(JSON.parse(JSON.stringify(s))), s, `${kind} reads back from a file`);
  }
  // A0 at 300% is 55 bond lengths across; a 16:9 slide at 200% is 33; A4 at 100% is 41 (IDEA-SIZE-7).
  const across = (s: typeof paper) => Math.round(pageSize(s)[0] / ((s.bond * 25.4) / 72));
  assert.deepEqual([across(paper), across(slides), across(poster)], [41, 33, 55]);
}

// The new pages, stored portrait, and the CDXML reader finds them in either orientation.
assert.deepEqual([PAGES.A1, PAGES.A0, PAGES.Slide169, PAGES.Slide43], [[594, 841], [841, 1189], [190.5, 338.67], [190.5, 254]]);
{
  const back = fromCdxml(toCdxml({ atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [] }, { ...purposeStyle("slides"), purpose: undefined }));
  assert.deepEqual([back.style.page, back.style.landscape], ["Slide169", true], "a slide page from a file another program wrote");
  const own = fromCdxml(toCdxml({ atoms: [{ label: "C", location: [0, 0, 0] }], bonds: [] }, purposeStyle("poster")));
  assert.deepEqual([own.style.page, own.style.purpose, own.style.scale], ["A0", "poster", 3], "Octet's own file keeps the purpose");
}

// A slide picked from the page list is landscape, and a sheet of paper picked from a slide is portrait. Other picks
// keep the orientation.
assert.deepEqual(pickPage(DEFAULT_STYLE, "Slide169"), { page: "Slide169", landscape: true });
assert.deepEqual(pickPage(purposeStyle("slides"), "A4"), { page: "A4", landscape: false });
assert.deepEqual(pickPage(purposeStyle("slides"), "Slide43"), { page: "Slide43", landscape: true });
assert.deepEqual(pickPage({ ...purposeStyle("slides"), landscape: false }, "Slide43"), { page: "Slide43", landscape: false }, "a portrait slide stays portrait");
assert.deepEqual(pickPage({ ...DEFAULT_STYLE, landscape: true }, "A3"), { page: "A3", landscape: true });

// ChemDraw 26.1's pads: every preset is distinct, sans serif, and inside the limits at any scale.
{
  const names = Object.keys(PRESETS);
  for (const name of names) {
    assert.equal(presetOf({ ...DEFAULT_STYLE, ...PRESETS[name] }), name, `${name} is found by its values`);
    assert.ok(!/Times|Georgia|Cambria/.test(PRESETS[name].labelFont + PRESETS[name].captionFont), `${name} uses no serif font`);
    for (const f of [0.1, 3, 10]) assert.equal(readStyle(withScale({ ...DEFAULT_STYLE, ...PRESETS[name], preset: name }, f)).preset, name, `${name} at ${f * 100}%`);
  }
  for (const pad of ["J. Chin. Chem. Soc.", "J. Het. Chem.", "Phytomedicine", "Science of Synthesis", "New Document (ChemDraw)", "New Slide (ChemDraw)"]) assert.ok(pad in PRESETS, pad);
}

// Outlines (IDEA-SIZE-6): the page, then what the purpose needs.
{
  const names = (o: [string, number, number][]) => o.map((x) => x[0]);
  assert.deepEqual(names(outlines(purposeStyle("paper"), "paper")), ["A4", "ACS 1-column", "ACS 2-column"]);
  assert.deepEqual(names(outlines({ ...purposeStyle("paper"), ...PRESETS.Nature }, "paper")), ["A4", "Nature 1-column", "Nature 2-column"]);
  assert.deepEqual(outlines(purposeStyle("thesis"), "thesis"), [["A4", 210, 297], ["Text block", 150, 257]]);
  assert.deepEqual(names(outlines(purposeStyle("slides"), "slides")), ["Slide 16:9"]);
  assert.deepEqual(outlines(purposeStyle("poster"), "poster"), [["A0", 841, 1189], ["A1", 594, 841]]);
  assert.deepEqual(names(outlines(DEFAULT_STYLE)), ["A4", "A3", "A2"], "no purpose: the page's series, as before");
  assert.deepEqual(names(outlines({ ...DEFAULT_STYLE, page: "Letter" })), ["Letter", "Legal", "Tabloid"]);
  assert.deepEqual(names(outlines({ ...DEFAULT_STYLE, page: "Custom", custom: [100, 50] })), ["100 × 50 mm"]);
  // Settings > Page edges > Page only: the page's edge alone, for every purpose.
  assert.deepEqual(names(outlines(purposeStyle("paper"), "paper", false)), ["A4"], "Page only hides the ACS columns");
  assert.deepEqual(outlines(purposeStyle("poster"), "poster", false), [["A0", 841, 1189]]);
  assert.deepEqual(names(outlines(DEFAULT_STYLE, undefined, false)), ["A4"]);
  // An edge takes a click (it fits that page) only where it shows: near the A4 edge or a column's with All sizes, the
  // A4 edge alone with Page only, and nothing with None.
  const all = outlines(purposeStyle("paper"), "paper"), acs1 = all[1][1] / 2;
  assert.equal(edgeAt(all, [105, 0], 1)?.[0], "A4");
  assert.equal(edgeAt(all, [acs1 + 0.5, 0], 1)?.[0], "ACS 1-column");
  assert.equal(edgeAt(outlines(purposeStyle("paper"), "paper", false), [acs1, 0], 1), undefined, "Page only: a hidden column takes no click");
  assert.equal(edgeAt([], [105, 0], 1), undefined, "None: no edge takes a click");
  assert.equal(edgeAt(all, [0, 0], 1), undefined, "the middle of the page is no edge");
  // Page only is Octet's, for every drawing: a template being made keeps its own Page edges switch, as with Ruler units.
  const edges = /d\("document", "Page", "Page edges", "[^"]*", (.*)\n/.exec(readFileSync(new URL("SettingsWindow.tsx", import.meta.url), "utf8"))?.[1];
  assert.match(edges ?? "", /^p\.template \? <Switch on=\{style\.edges\}/, "a template being made shows its own Page edges switch");
  assert.match(readFileSync(new URL("SettingsWindow.tsx", import.meta.url), "utf8"), /<Select label="Page edges" [^\n]*\[\["all", "All sizes"\], \["page", "Page only"\], \["none", "None"\]\]/, "the choices name what shows");
}

// An open drawing given a purpose takes its sizes and page, and keeps its own background and label choices.
{
  const mine = { ...purposeStyle("paper"), ...PRESETS.RSC, background: "dark" as const, hideH: true, grid: 10 };
  const poster = forPurpose(readStyle(mine), purposeStyle("poster"));
  assert.deepEqual([poster.bond, poster.labelSize, poster.page, poster.purpose, poster.preset], [43.2, 30, "A0", "poster", "ACS Document 1996"]);
  assert.deepEqual([poster.background, poster.hideH, poster.grid], ["dark", true, 10]);
}

// Quick start: ACS Document 1996 at 100% with no purpose, so no outlines, and its page edges off: a seamless canvas.
{
  assert.deepEqual({ ...QUICK_STYLE, edges: true }, DEFAULT_STYLE);
  assert.equal(QUICK_STYLE.edges, false);
  assert.equal(QUICK_STYLE.purpose, undefined);
  assert.deepEqual(readStyle(JSON.parse(JSON.stringify(QUICK_STYLE))), QUICK_STYLE, "Quick start reads back from a file");
}

// Settings: the purpose ⌘N starts (Quick start at first), each purpose's own style, and the user's purposes.
{
  const none = readPurposes({});
  assert.deepEqual(none, { purpose: QUICK, purposeStyles: {}, ownPurposes: [] });
  assert.deepEqual(styleFor(none, QUICK), QUICK_STYLE);
  assert.deepEqual(styleFor(none, "slides"), purposeStyle("slides"));
  assert.deepEqual(styleFor(none, "u-gone"), QUICK_STYLE, "an unknown purpose is Quick start");
  // Use for new documents on Quick start keeps its style, with no purpose.
  const quick = readPurposes({ purpose: "slides", purposeStyles: { quick: { ...QUICK_STYLE, ...PRESETS.RSC, purpose: "paper" } } });
  assert.equal(quick.purpose, "slides");
  assert.equal(styleFor(quick, QUICK).preset, "RSC");
  assert.equal(styleFor(quick, QUICK).purpose, undefined);
  assert.equal(styleFor(quick, QUICK).edges, false);
  assert.equal(readPurposes({ purpose: QUICK }).purpose, QUICK);
  // A default style saved before purposes becomes Paper's; the default itself is not kept.
  const rsc = readPurposes({ docStyle: { ...DEFAULT_STYLE, ...PRESETS.RSC } });
  assert.equal(styleFor(rsc, "paper").preset, "RSC");
  assert.equal(styleFor(rsc, "paper").purpose, "paper");
  assert.deepEqual(readPurposes({ docStyle: DEFAULT_STYLE }).purposeStyles, {});
  // The user's own purposes: sound ones only, 12 at most; the purpose Return starts must exist.
  const own = { id: "uabc", name: " Group talk ", kind: "slides", style: purposeStyle("slides") };
  const read = readPurposes({ purpose: "uabc", ownPurposes: [own, { id: "x y", name: "Bad", kind: "slides", style: {} }, { id: "udef", name: "", kind: "paper" }, { id: "ughi", name: "Odd", kind: "talk" }] });
  assert.deepEqual(read.ownPurposes.map((p) => [p.id, p.name, p.kind, p.style.purpose]), [["uabc", "Group talk", "slides", "uabc"]]);
  assert.equal(read.purpose, "uabc");
  assert.deepEqual(purposeOf(read, "uabc"), read.ownPurposes[0]);
  assert.deepEqual(purposeOf(read, "poster"), { name: "Poster", kind: "poster" });
  assert.equal(readPurposes({ purpose: "unot" }).purpose, QUICK);
  assert.equal(readPurposes({ ownPurposes: Array.from({ length: 20 }, (_, k) => ({ ...own, id: `u${k}` })) }).ownPurposes.length, 12);
}
console.log("purpose.check: ok");
