// Run: node src/panels.check.ts. The spectrum and Mass spec panels minimise to a pill beside their structure (plan
// B1, Sam 4 and 7 November 2026), take turns with the Actions panel, and close as one undo step; every panel has the
// same controls (PanelControls); Mass spec analysis sits with the NMR predictions and Properties.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path: string) => readFileSync(new URL(path, import.meta.url), "utf8");
const editor = read("./Editor.tsx"), css = read("./editor.css"), actions = read("./Actions.tsx"), menu = read("../src-tauri/src/main.rs");
const controls = read("./PanelControls.tsx");

// B1.4 and B1.23: one set of controls on every panel, in Octet's style on every platform (no platform branches).
for (const file of ["Spectrum.tsx", "MassSpec.tsx", "Properties.tsx", "Actions.tsx"]) assert.match(read(`./${file}`), /<PanelControls /, `${file} uses PanelControls`);
assert.match(read("./Spectrum.tsx"), /<PanelControls minimise=\{p\.onMinimise\} full=\{[^}]+\}\} close=\{p\.onClose\} \/>/);
assert.match(read("./MassSpec.tsx"), /<PanelControls minimise=\{p\.onMinimise\} full=\{[^}]+\}\} close=\{p\.onClose\} \/>/);
assert.match(read("./Properties.tsx"), /<PanelControls close=\{onClose\} \/>/);
assert.match(actions, /<PanelControls minimise=\{\(\) => onOpen\(false\)\} \/>/, "the Actions panel's control is Minimise: it becomes its pill");
assert.doesNotMatch(controls, /isMac|IS_MAC|navigator|userAgent/, "the same controls on Mac, Windows and Linux");
for (const name of ['"Minimise"', '"Full screen"', '"Leave full screen"', '"Close"']) assert.ok(controls.includes(name), name);

// B1.5: minimised, a panel stays (hidden), so it comes back as it was, and it does not draw again while hidden.
for (const file of ["Spectrum.tsx", "MassSpec.tsx"]) {
  const src = read(`./${file}`);
  assert.match(src, /memo\(Panel, \(a, b\) => !!a\.hidden && !!b\.hidden\)/, `${file}: no redraw while minimised`);
  assert.match(src, /p\.hidden && "minimised"/);
  assert.match(src, /inert=\{leaving \|\| p\.hidden\}/, `${file}: a hidden panel takes no keys`);
  assert.match(src, /e\.key === "Escape"[^\n]+p\.onMinimise\(true\)/, `${file}: Escape in the panel minimises it`);
}
assert.match(css, /\.spectrum\.minimised \{\n  display: none;/);

// B1.2: the strip runs from the toolbar to the window's right edge, above the Actions pill; full screen to the bottom.
assert.match(css, /\.spectrum \{\n  position: absolute;\n  left: var\(--strip-left, calc\(var\(--space-4\) \* 2 \+ 48px\)\);\n  right: var\(--space-4\);\n  bottom: calc\(var\(--space-4\) \* 2 \+ 32px\);/);
assert.match(css, /\.spectrum\.expanded \{\n  top: var\(--space-4\);\n  bottom: var\(--space-4\);/);

// B1.7: the pill sits in a layer the view moves (no React render on pan or zoom), is not scaled by the zoom, and
// is not part of the drawing.
assert.match(controls, /useLayoutEffect\(\(\) => views\.subscribe\(\(\) => place\.current\(\)\), \[views\]\);/, "a pan or zoom places the pills with no React render");
assert.match(controls, /pill\.style\.left = `\$\{Math\.max\(72, Math\.min\(room\.width - pill\.offsetWidth - 16, x\)\)\}px`;/, "a pill stays in view");
assert.match(controls, /pill\.style\.top = `\$\{Math\.max\(16, Math\.min\(room\.height - dock - 40, y\)\)\}px`;/);
assert.match(css, /:is\(\.pill, \.spectrum-tab\):is\(:hover, :focus-within\) \.close-x \{\n  display: grid;/);
assert.match(css, /@media \(hover: none\), \(pointer: coarse\) \{\n  \.close-x,\n  \.segmented button\.close-x \{\n    display: grid;/, "the X always shows for touch and pen");
for (const file of ["export.ts", "file.ts", "cdxml.ts"]) assert.doesNotMatch(read(`./${file}`), /pill/i, `${file} knows nothing of pills`);
assert.match(controls, /e\.key === "Delete" \|\| e\.key === "Backspace"/, "Delete on a focused pill closes it");

// B1.1 and B1.6: the panel and Actions take turns, and settings.actions is not changed by a panel opening.
assert.match(editor, /open=\{settings\.actions && !actionsYield\}/);
assert.match(editor, /onOpen=\{openActions\}/);
assert.match(editor, /const actionsYield = settings\.actions && \(showing\("nmr"\) \|\| showing\("ms"\)\);/, "Actions is a pill while a panel shows in the strip");
assert.match(editor, /if \(open\) \{ minimisePanel\("nmr"\); minimisePanel\("ms"\); \}/, "opening Actions minimises the strip");

// B1.10 and B1.11: Close is one undo step that does not change the drawing; Redo closes again.
assert.match(editor, /closedPanel\.current = \{ kind, was, mol: doc, at: h\.at \};/);
assert.match(editor, /if \(c && c\.mol === h\.stack\[h\.at\] && c\.at === h\.at && !!c\.undone === redo\)/);
assert.doesNotMatch(editor.slice(editor.indexOf("function closePanel"), editor.indexOf("function letGoOfPanel")), /\bset\(|dispatch\(/, "closing a panel is not an edit");

// B1.12: only the shown panel predicts; minimised, no shifts show beside the atoms.
assert.match(editor, /if \(nmrView === "open"\) nmrDocKept\.current = \{ doc, target: cur \? sessionMols\.get\(cur\.id\)/);
assert.match(editor, /\}, \[nucleusOpen, loaded, nmrDoc, nmrTarget, nmrTables, nmrSolvent, settings\.nmrDecouple\]\);/);
assert.match(editor, /if \(nmrView !== "open"\) \{ \/\* minimised: no shifts beside the atoms \*\/ \}/);

// B1.14 and B1.16: View > Show or Hide Spectrum, focus to the pill after a keyboard minimise, and the live region.
assert.match(menu, /item\("toggle_spectrum", "Show or Hide Spectrum", ""\)/);
assert.match(editor, /pillEl\(kind\)\?\.querySelector<HTMLElement>\("\.pill-open"\)\?\.focus\(\)/);
for (const said of ["minimised", "closed", "open"]) assert.ok(editor.includes(`say(\`\${panelName(kind)} ${said}\`)`), `says "${said}"`);
assert.match(read("./Spectrum.tsx"), /role="region" aria-label=\{p\.label\}/);

// B1.17: motion from the tokens, opacity only with reduced motion, none from the keyboard.
assert.match(controls, /if \(!panel \|\| keyboard\) return done\?\.\(\);/);
assert.match(controls, /reduced\(\) \? \[\{ opacity: 1 \}, \{ opacity: 0 \}\]/);
assert.match(controls, /timing\(way === "in" \? "--motion" : "--motion-slow"\)/);

// Mass spec analysis next to the NMR predictions and Properties (Sam, 7 November 2026), in the Actions panel's
// Analysis set, the Structure menu under the NMR items, the command palette and the MCP. The tool stays.
assert.match(actions, /predict_31p: "analysis", mass_spec: "analysis"/);
assert.match(actions, /"Predict ³¹P-NMR shifts", "predict_31p"\)\), small\(it\(<MassSpecGlyph \/>, "Mass spec analysis", "mass_spec"\)\)/, "Mass spec comes after the NMR predictions");
{
  const gap = menu.slice(menu.indexOf('item("predict_13c"'), menu.indexOf('&item("mass_spec", "Show Mass Spec Analysis", "")'));
  assert.ok(gap.length > 0 && gap.split("\n").slice(1).every((line) => /^\s*(\/\/.*|&item\("predict_\w+", "Predict [^"]+", ""\)\?,)?$/.test(line)), "Mass spec comes right after the NMR predictions");
}
assert.match(editor, /mass_spec: \(\) => massSpecOf\(\),/);
assert.match(editor, /mass_spec: \["Mass spec analysis", "", <MassSpecGlyph \/>\]/);
assert.match(read("./tools.tsx"), /const SPECIAL: Tool\[\] = \[[^\]]*"massspec"/, "the Mass spec analysis tool stays in the toolbar");
for (const command of ["mass_spec", "toggle_spectrum", "spectrum_full_screen", "spectrum_close"]) {
  assert.match(editor, new RegExp(`\\n    ${command}: `), `Editor runs ${command}`);
}

// B1.3: the strip's height by its top edge, kept in settings, with the canvas keeping 96 px.
assert.match(controls, /role="separator" aria-orientation="horizontal"/);
assert.match(controls, /ArrowUp: height \+ step, ArrowDown: height - step, Home: min, End: max/);
assert.match(controls, /if \(h0 \+ y0 - u\.clientY < min - 48\) onMinimise\(false\);/, "a drag well under the least height minimises");
assert.match(controls, /onDoubleClick=\{onReset\}/);
assert.match(read("./settings.ts"), /stripHeight\?: number;/);
assert.match(editor, /stripDefault = Math\.round\(Math\.min\(400, Math\.max\(200, 0\.35 \* innerHeight\)\)\)/);
assert.match(css, /\.spectrum\.sized \{\n  max-height: calc\(100% - 96px - var\(--space-4\) \* 3 - 32px\);/);
for (const file of ["Spectrum.tsx", "MassSpec.tsx"]) assert.match(read(`./${file}`), /\{!expanded && <ResizeEdge sizing=\{p\.sizing\} onMinimise=\{p\.onMinimise\} \/>\}/, `${file}: the top edge`);

// B1.8: a session's spectra as tabs, each closable, and + to add a kind that applies.
const spectrum = read("./Spectrum.tsx");
assert.match(spectrum, /role="tablist" aria-label="Spectra"/);
assert.match(spectrum, /if \(closable && \(e\.key === "Delete" \|\| e\.key === "Backspace"\)\) \{ e\.preventDefault\(\); e\.stopPropagation\(\); onClose\(k\); \}/);
// A tab has a close button only when there are two or more (one alone closes with the panel), in room of its own so it
// never covers the name; + is the last segment of the same control, outside the tab list.
assert.match(spectrum, /const closable = keys\.length > 1;/);
assert.match(spectrum, /\{closable && <CloseX name=\{keyName\(k\)\} onClose=\{\(\) => onClose\(k\)\} \/>\}/);
// One close X for a pill and a spectrum tab: one component (CloseX) and one rule (.close-x), the panel controls' look
// (no fill, muted, sunken under the pointer) at 18 px. The tab's X sits in the tab's own room, 4 px clear of the name.
assert.match(controls, /<CloseX name=\{p\.name\} onClose=\{p\.onClose\} \/>/);
assert.match(controls, /className="close-x" tabIndex=\{-1\} aria-label=\{`Close \$\{name\}`\} data-tip="Close" onClick=\{\(\) => onClose\(\)\}><X size=\{12\} \/><\/button>/);
assert.doesNotMatch(css + controls + spectrum, /pill-close|tab-close/, "no second close X");
assert.match(css, /\n\.close-x,\n\.segmented button\.close-x \{\n  display: none;\n  place-items: center;\n  width: var\(--size-action\);\n  min-width: 0;\n  height: var\(--size-action\);\n  padding: 0;\n  border: 0;\n  border-radius: var\(--radius-sm\);\n  background: transparent;\n  color: var\(--ink-muted\);\n\}/);
for (const m of css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/\n([^{}\n]*close-x[^{}]*)\{([^}]*)\}/g)) {
  if (/\b(width|height|background|border-radius|color):/.test(m[2])) assert.ok(/^\.close-x,\n\.segmented button\.close-x $|close-x:hover/.test(m[1].trim() + " "), `one look for the close X: ${m[1].trim()}`);
}
{
  // The tab's room is the X (--size-action, 18 px), the 4 px clear of the name (--space-1) and the X's own 2 px from the edge.
  // The same room is on the name's left, so the name stays in the middle of its tab.
  const calc = /\.spectrum-tab\.closable button\[role="tab"\] \{\n  padding: 0 calc\(var\(--size-action\) \+ var\(--space-1\) \+ (\d+)px\);/.exec(css);
  const room = 18 + 4 + Number(calc?.[1]);
  const right = Number(/\.spectrum-tab \.close-x \{\n  position: absolute;\n  top: 0;\n  bottom: 0;\n  right: (\d+)px;\n  margin: auto 0;\n\}/.exec(css)?.[1]);
  assert.equal(room - right - 18, 4, "the tab's X is 4 px clear of the name");
}
// Every X that closes something has the panel controls' corners (.actions-close, the brand's 6 px for controls): the
// pill's and tab's X (18 px), and the X on a notice and on a floating template palette, which are a panel's Close.
{
  const radius = (sel: string) => new RegExp(`\\n${sel} \\{[^}]*\\n  border-radius: ([^;]+);`).exec(css)?.[1];
  assert.equal(radius("\\.actions-close"), "var(--radius-sm)");
  assert.equal(radius("\\.close-x,\\n\\.segmented button\\.close-x"), radius("\\.actions-close"), "a pill's or tab's X has the panel controls' corners");
  assert.match(read("./NoticeBar.tsx"), /<button className="actions-close" aria-label="Close" data-tip="Close" onClick=\{onGone\}><X size=\{12\} \/><\/button>/);
  assert.match(read("./TemplateLibrary.tsx"), /<button className="actions-close" aria-label=\{`Close \$\{palette\.set\}`\} data-tip="Close" onClick=\{onClose\}>/);
  assert.match(css, /\n\.floating-size \{[^}]*\n  width: var\(--size-control-sm\);\n  height: var\(--size-control-sm\);\n  padding: 0;\n  border: 0;\n  border-radius: var\(--radius-sm\);/, "the palette's size button matches its X");
  assert.doesNotMatch(css + read("./NoticeBar.tsx") + read("./TemplateLibrary.tsx"), /notice-close|floating-close/, "no second panel X");
}
// The + that adds a spectrum is a small action at the brand's 12 px, as the X beside it.
assert.match(spectrum, /<Plus size=\{12\} aria-hidden \/>\n            <\/Pick>/);
assert.match(spectrum, /<\/span>\n    \{children\}\n    <\/span>/);
assert.match(spectrum, /<Pick label="Add spectrum" value="" className="tab-add"/);
// The tab shown and a button that is on keep their tint under the pointer, as a segmented control's choice does.
assert.match(read("editor.css"), /\.segmented button:hover:not\(\[aria-checked="true"\], \[aria-selected="true"\]\)/);
assert.match(read("editor.css"), /\.spectrum-button:hover:not\(:disabled, \[aria-pressed\]\)/);
// Mass spec's HRMS line and ion table show each formula with its subscripts, from the Actions panel's formula helper;
// what is copied or added to the drawing stays plain text (a caption makes its own subscripts).
{
  const ms = read("./MassSpec.tsx");
  assert.match(ms, /<p className="spectrum-text">\{hrms && hrmsLine\(\{ \.\.\.hrms, formula: formula\(hrms\.formula\) \}\)\}<\/p>/);
  assert.match(ms, /<td className="formula">\{formula\(r\.ion\.formula\)\}<\/td>/);
  assert.match(ms, /const line = hrms \? hrmsLine\(hrms\) : "";/);
  // The helper itself: only a count (after an element, ")" or "]") is a subscript.
  const helper = new Function(`${/const SUBSCRIPT = [^\n]+/.exec(actions)![0]}\nreturn ${/export const formula = \(f: string\) => ([^\n]+);/.exec(actions)![0].replace("export const formula = (f: string) => ", "(f) => ").replace(/;$/, "")};`)() as (f: string) => string;
  assert.equal(helper("C7H7O3"), "C₇H₇O₃");
  assert.equal(helper("C10H13O2"), "C₁₀H₁₃O₂");
  assert.equal(helper("Fe2(SO4)3"), "Fe₂(SO₄)₃");
  assert.equal(helper("C5[13C]H6"), "C₅[13C]H₆", "an isotope's mass number is no count");
  assert.equal(helper("CuSO4·5H2O"), "CuSO₄·5H₂O");
}
// The header's formula has its subscripts, as the Actions panel's has; an abbreviation keeps its digits (2-MeTHF).
assert.match(editor, /text: a \? a\.abbreviation \?\? subscripts\(a\.formula\) : "", formula: !!a && !a\.abbreviation \}/);
// The header shows a formula in the formula's font (IBM Plex Mono, weight 500), as the Actions panel shows it.
assert.match(spectrum, /p\.formulaTitle \? <span className="formula">\{p\.title\}<\/span> : p\.title/);
assert.match(css, /\n\.facts \.formula,\n\.prop-value\.formula,\n\.spectrum h2 \.formula \{\n  font: 500 13px\/18px var\(--font-mono\);/);
assert.match(editor, /addable=\{\[\.\.\.new Set\(\[\.\.\.PREDICTED, \.\.\.\(doc\.spectra \?\? \[\]\)\.map\(spectrumKeyOf\)\]\)\]\.filter\(\(k\) => !x\.keys\.includes\(k\)\)\}/);
assert.match(editor, /keys: x\.keys\.includes\(key\) \? x\.keys : \[\.\.\.x\.keys, key\], key/, "Predict for a kind already open shows its tab");
assert.match(editor, /count: x\.keys\.length > 1 \? x\.keys\.length : undefined/, "the pill counts the spectra");

// B1.9 and B1.12: one session for each structure, marked on its atoms, found again after an undo by its atoms'
// places, and joined when its structure joins another's. Marks are never saved, copied or duplicated.
assert.match(read("./render.ts"), /session\?: number;/);
assert.match(read("./edit.ts"), /add\.atoms\.map\(\(\{ session: _, \.\.\.a \}\)/, "a pasted or duplicated structure is in no session");
assert.doesNotMatch(read("./file.ts"), /session/, "the file never saves a session");
assert.match(editor, /if \(file\.saved === doc\) setFile\(\(f\) => \(\{ \.\.\.f, saved: marked \}\)\);\n    dispatch\(\{ type: "amend", mol: marked \}\);/, "marks are no undo step and no unsaved change");
assert.match(editor, /if \(best < 0 && s\.at\.length\)/, "no marks: the structure by its atoms' places");
assert.match(editor, /if \(first\) merged\.set\(x\.id, first\.id\); else owner\.set\(g, x\);/, "joined structures join their sessions");
assert.match(editor, /if \(x\.id !== shownId\) \{ const kept = sessionProps\.current\.get\(x\.id\); return kept \? <SpectrumPanel \{\.\.\.kept\} hidden \/> : null; \}/, "each session's panel keeps what it showed");
assert.match(spectrum, /\{p\.noStructure && <span className="spectrum-none" role="status">No structure<\/span>\}/);

// B1.14: the strip's controls come last in its tab order.
for (const file of ["Spectrum.tsx", "MassSpec.tsx"]) {
  const src = read(`./${file}`);
  assert.ok(src.lastIndexOf("<PanelControls") > src.lastIndexOf("<footer"), `${file}: the controls come last`);
}

// B1.15: the peaks by keyboard, named as a chemist reads them.
assert.match(spectrum, /role="listbox" aria-label="Peaks"/);
assert.match(spectrum, /ppm, \$\{word\}\$\{c\.length \? `, J \$\{c\.map\(\(x\) => x\.j\.toFixed\(1\)\)\.join\(", "\)\} Hz` : ""\}, \$\{s0\.nuclei\} \$\{element\}/);
assert.match(spectrum, /if \(e\.key === "Enter"\) \{ e\.preventDefault\(\); q\.choose\(\); return; \}/);

// B1.19 and B1.20: the notice, the tutorial card and Fit to Window keep clear of the strip; Add to drawing says so.
assert.match(css, /\.notice \{\n  position: absolute;\n  bottom: calc\(var\(--space-6\) \+ var\(--dock, 0px\)\);/);
assert.match(css, /\.coach\.low \{\n  top: auto;\n  bottom: calc\(var\(--space-4\) \+ var\(--dock, 0px\)\);/);
assert.match(editor, /free = \[innerWidth - 160, innerHeight - 120 - below\]/);
assert.match(editor, /say\("Spectrum added"\);/);

// ¹⁹F and ³¹P in the UI (plan B3, 8 November 2026): drawn by kind (trace or sticks) with no test of one nucleus,
// with Decouple ¹H, in the Actions panel, the palette and the MCP. Offered for every structure, as ¹H and ¹³C are
// (Sam, 11 November 2026): one with no F or P opens the panel on an empty spectrum, with no notice.
assert.match(spectrum, /const nucleus: Nucleus \| undefined = isNucleus\(p\.spectrumKey\) \? p\.spectrumKey : undefined;/);
assert.match(spectrum, /const traced = !!nucleus && NUCLEI\[nucleus\]\.trace;/);
assert.doesNotMatch(spectrum, /nucleus === "1H"/, "no ¹H-only branches in the panel");
assert.match(spectrum, /split\.map\(\(ls, k\) => shown\(signals\[k\]\) && ls\.map\(\(l, i\) => <line/, "one stick for each line of a split signal");
assert.match(spectrum, /aria-pressed=\{p\.decoupled\} onClick=\{\(\) => p\.onDecouple\(!p\.decoupled\)\}/, "Decouple ¹H shows its setting with no prediction too");
assert.match(spectrum, />Decouple ¹H<\/button>/);
assert.match(editor, /decoupled=\{!!nucleusOpen && \(settings\.nmrDecouple\?\.\[nucleusOpen\] \?\? NUCLEI\[nucleusOpen\]\.decouple\)\}/);
assert.match(spectrum, /\{v\.toFixed\(places\)\.replace\("-", "−"\)\}/, "a minus sign on the axis");
assert.match(editor, /const PREDICTED: string\[\] = NUCLEUS_LIST;/);
assert.doesNotMatch(editor.match(/\n  function openSpectrum\([^]*?\n  \}\n/)![0], /return|setNotice/, "Predict refuses no structure");
assert.match(editor, /predict\(g, nucleusOpen, nmrSolvent, settings\.nmrDecouple\?\.\[nucleusOpen\]\)/);
assert.match(editor, /const mhz = first\.mhz \/ NUCLEI\[key\]\.ratio/);
for (const id of ["predict_19f", "predict_31p"]) {
  assert.match(editor, new RegExp(`\\n    ${id}: \\(\\) => openSpectrum\\("${id === "predict_19f" ? "19F" : "31P"}"\\),`));
  assert.ok(actions.includes(`"${id}"`) && menu.includes(`item("${id}"`), id);
}
assert.match(actions, /"predict_13c"\)\), small\(it\(<span className="glyph-text">¹⁹F<\/span>, "Predict ¹⁹F-NMR shifts", "predict_19f"\)\), small\(it\(<span className="glyph-text">³¹P<\/span>, "Predict ³¹P-NMR shifts", "predict_31p"\)\)/, "the Actions panel offers ¹⁹F and ³¹P for every structure");
assert.doesNotMatch(actions, /nuclei\?/);

// The Actions panel's titled sections (Fold): the caret turns by the open state, on hover too, so a section open on
// hover shows as open. One click on its title closes it and keeps it folded until the pointer leaves and comes back.
assert.match(actions, /const open = !folded \|\| peek;/);
assert.match(actions, /<button className="fold-title" aria-expanded=\{open\}/);
assert.match(css, /\.fold-title\[aria-expanded="false"\] \.fold-caret \{\n  transform: rotate\(-90deg\);/, "the caret turns by the open state");
assert.doesNotMatch(css, /\.fold\[data-folded\]/, "the caret does not turn by the folded setting alone");
assert.match(actions, /quiet\.current = pointer && open;\n    folds\.peeks\.delete\(id\);\n    setPeek\(false\);\n    if \(!folded \|\| !peek\) onFold\(id, !folded\);/, "a click on a section open on hover closes it and does not pin it open");
assert.match(actions, /aria-controls=\{body\} onPointerDown=\{\(\) => clearTimeout\(timer\.current\)\} onClick=\{toggle\}>/, "a press before it opens on hover stops it opening, so a tap opens it");
console.log("panels.check: ok");
