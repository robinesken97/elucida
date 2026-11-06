// Run: node src/access.check.ts. The canvas for screen readers and the keyboard (access.ts): what each object is called
// (a structure by its checked name, else its formula and rings; a reaction step as a sentence; arrows, text, shapes and
// spectra), the reading order Tab takes, what the hotspot says on each atom and bond and where each arrow key takes it,
// that its keys clash with no key Octet has, what an edit says, the focus ring on every page colour, and the time on a
// drawing of 500 atoms.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import type { Box, Mol } from "./render.ts";

// chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
const gl = globalThis as Record<string, unknown>;
gl.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
gl.getComputedStyle = () => ({ getPropertyValue: () => "10" });
gl.window = globalThis;
gl.self = { location: { origin: "file://" } };
gl.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const chem = await import("./chem.ts");
await chem.ready;
const { FOCUS, atomText, bondText, changeText, contrast, describe, readingOrder, ringOn } = await import("./access.ts");
const { addArrow, addCaption, addShape, deleteAtom, flipAtoms, fragments, groupSelection, insertMol, jumpHot, moveAtoms, rotateAtoms, setBondSpec, setElement, subset, walkHot } = await import("./edit.ts");
const { findReaction } = await import("./reaction.ts");
const { ACTIONS, actionFor, DEFAULT_KEYS, keymap, keyOf } = await import("./keys.ts");

// The names engine (OPSIN), when it is built: Structure to Name as the editor runs it (Editor.tsx namedPart).
const dir = new URL("./vendor/opsin/", import.meta.url);
let nameOf: ((m: Mol) => string | undefined) | undefined;
if (existsSync(new URL("opsin.js", dir))) {
  const pack = readFileSync(new URL("opsin-data.bin", dir)), files = new Map<string, Int8Array>();
  for (let p = 0; ; ) {
    const n = pack.readUInt16BE(p); p += 2;
    if (!n) break;
    const name = pack.toString("latin1", p, p + n); p += n;
    const size = pack.readInt32BE(p); p += 4;
    files.set(name, new Int8Array(pack.buffer, pack.byteOffset + p, size)); p += size;
  }
  gl.opsinResource = (name: string) => files.get(name) ?? null;
  const opsin = await import(new URL("opsin.js", dir).href);
  opsin.init();
  const json = (file: string) => JSON.parse(readFileSync(new URL(file, import.meta.url), "utf8"));
  const { DRUGS } = await import("./drugs.ts");
  const { abbreviationOf, attachOpsin, knownName, nameToSmiles } = await import("./names.ts");
  attachOpsin(opsin, readFileSync(new URL("names.txt", dir), "utf8"), json("./nameindex.json"), DRUGS, json("./abbreviations.json"));
  const { checkedName, setNamer, withAbbreviation } = await import("./naming.ts");
  setNamer((await import("./namer.ts")).iupacName);
  const inchiOf = (s: Mol | string) => { try { return chem.toInchi(typeof s === "string" ? chem.parseStructure(s, false) : s); } catch { return undefined; } };
  nameOf = (m) => { const bare = checkedName(m, chem.expandLabels(m), nameToSmiles, inchiOf, chem.cipOf, knownName); return bare && withAbbreviation(bare, abbreviationOf(inchiOf(m))); };
} else console.log("access.check: names skipped (no OPSIN build)");

// Boxes as the editor gives them (drawing units, y up): the atoms with a margin, text by its anchor, arrows and shapes
// by their ends.
type B = [number, number, number, number];
const boxIn = (m: Mol) => {
  const caps = new Map((m.captions ?? []).map((c) => [c.id, c])), arrows = new Map((m.arrows ?? []).map((a) => [a.id, a])), shapes = new Map((m.shapes ?? []).map((sh) => [sh.id, sh]));
  return (atoms: number[], items: number[]): Box | undefined => {
  const ps: number[][] = atoms.map((i) => m.atoms[i].location);
  for (const id of items) {
    const c = caps.get(id), a = arrows.get(id), sh = shapes.get(id);
    if (c) ps.push([c.x - 0.2 * c.text.length, c.y - 0.2], [c.x + 0.2 * c.text.length, c.y + 0.4]);
    for (const x of [a, sh]) if (x) ps.push(x.from, x.to);
  }
  if (!ps.length) return undefined;
  const xs = ps.map((p) => p[0]), ys = ps.map((p) => p[1]);
  return [Math.min(...xs) - 0.3, Math.min(...ys) - 0.3, Math.max(...xs) + 0.3, Math.max(...ys) + 0.3] as B;
  };
};
const sources = (m: Mol, o: { names?: boolean; formulas?: boolean } = {}) => {
  const box = boxIn(m);
  return { box,
    formula: o.formulas === false ? undefined : (atoms: number[]) => chem.analyse(subset(m, new Set(atoms)), 1)?.[0]?.formula,
    name: o.names && nameOf ? (atoms: number[]) => nameOf!(subset(m, new Set(atoms))) : undefined,
    reaction: (id: number) => findReaction(m, id, m.arrows ?? [], (a) => box(a, []), (c) => box([], [c])),
  };
};
const said = (m: Mol, o?: { names?: boolean; formulas?: boolean }) => describe(m, sources(m, o)).map((x) => [x.role, x.name, ...(x.more ? [x.more] : [])]);
const row = (...parts: [Mol, number][]) => parts.reduce((m, [add, x]) => insertMol(m, add, [x, 0]).mol, { atoms: [], bonds: [] } as Mol);
const smiles = (s: string) => chem.parseStructure(s);

// ——— Structures: the checked name with formula and rings after it, else formula and rings ———
const aspirin = smiles("CC(=O)Oc1ccccc1C(O)=O");
assert.deepEqual(said(aspirin), [["structure", "C9H8O4, one ring"]]);
assert.deepEqual(said(aspirin, { formulas: false }), [["structure", "13 atoms, one ring"]], "before Indigo has the formula");
assert.deepEqual(said(smiles("c1ccc2ccccc2c1")), [["structure", "C10H8, two rings"]]);
assert.deepEqual(said(smiles("C1C2CC3CC1CC(C2)C3")), [["structure", "C10H16, three rings"]], "adamantane");
assert.deepEqual(said(smiles("CCO")), [["structure", "C2H6O, no rings"]]);
if (nameOf) {
  assert.deepEqual(said(aspirin, { names: true }), [["structure", "2-(acetyloxy)benzoic acid", "C9H8O4, one ring"]]);
  assert.deepEqual(said(smiles("NCCN(CCN)CCN"), { names: true }), [["structure", "N1,N1-bis(2-aminoethyl)ethane-1,2-diamine (TREN)", "C6H18N4, no rings"]], "an abbreviation after the name");
}

// ——— Reactions: each arrow reads its step as a sentence, with its conditions ———
let rxn = smiles("OC(=O)c1ccccc1O.CC(=O)OC(C)=O>>CC(=O)Oc1ccccc1C(O)=O");
const arrow = rxn.arrows![0], mid = (arrow.from[0] + arrow.to[0]) / 2;
rxn = addCaption(rxn, { text: "H2SO4", x: mid, y: 0.5, on: { arrow: arrow.id, side: "above" } })[0];
rxn = addCaption(rxn, { text: "90 °C", x: mid, y: -0.7, on: { arrow: arrow.id, side: "below" } })[0];
assert.deepEqual(said(rxn), [
  ["structure", "C7H6O3, one ring"], ["text", "Plus sign"], ["structure", "C4H6O3, no rings"],
  ["reaction arrow", "C7H6O3 plus C4H6O3 gives C9H8O4, conditions: H2SO4, 90 °C"], ["text", "H2SO4"], ["text", "90 °C"],
  ["structure", "C9H8O4, one ring"],
], "the conditions kept on the arrow follow it, above first");
if (nameOf) assert.equal(said(rxn, { names: true })[3][1], "2-hydroxybenzoic acid plus acetic anhydride (Ac2O) gives 2-(acetyloxy)benzoic acid, conditions: H2SO4, 90 °C");
// Two steps: each arrow reads its own. An equilibrium and a retrosynthetic arrow say what they mean.
let steps = row([smiles("CCO"), 0], [smiles("CC=O"), 5], [smiles("CC(O)=O"), 10]);
const xs = (atoms: number[]) => atoms.map((i) => steps.atoms[i].location[0]);
const [e1, e2] = fragments(steps).map((f) => [Math.min(...xs(f)), Math.max(...xs(f))]);
steps = addArrow(steps, { kind: "reaction", from: [e1[1] + 0.6, 0], to: [e1[1] + 2.2, 0] })[0];
steps = addArrow(steps, { kind: "equilibrium", from: [e2[1] + 0.6, 0], to: [e2[1] + 2.2, 0] })[0];
assert.deepEqual(said(steps).filter(([role]) => role.endsWith("arrow")), [["reaction arrow", "C2H6O gives C2H4O"], ["equilibrium arrow", "C2H4O is in equilibrium with C2H4O2"]]);
const ester = smiles("CC(=O)OCC"), right = Math.max(...ester.atoms.map((a) => a.location[0]));
const retro = addArrow(row([ester, 0], [smiles("CC(O)=O"), right + 4]), { kind: "retro", from: [right + 0.8, 0], to: [right + 2.6, 0] })[0];
assert.equal(said(retro).find(([role]) => role === "retrosynthetic arrow")?.[1], "C4H8O2 is made from C2H4O2");
// An arrow with nothing round it.
assert.deepEqual(said(addArrow({ atoms: [], bonds: [] }, { kind: "reaction", from: [0, 0], to: [2, 0] })[0]), [["arrow", "Reaction"]]);

// ——— Other objects ———
// Formaldehyde: C1 at the origin, O1 one bond to the right, and a curved arrow from O1's lone pair to the C=O bond.
const ch2o: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "O", location: [1, 0, 0] }], bonds: [{ type: 2, atoms: [0, 1] }] };
assert.deepEqual(said(addArrow(ch2o, { kind: "curved", from: [1.3, 0.3], to: [0.5, 0.05], bend: 0.4 })[0], { formulas: false }).slice(1), [["curved arrow", "From oxygen 1 to the bond between carbon 1 and oxygen 1"]]);
assert.deepEqual(said(addArrow(ch2o, { kind: "fishhook", from: [5, 5], to: [6, 5] })[0], { formulas: false }).filter(([role]) => role !== "structure"), [["fishhook arrow", "Fishhook"]]);
assert.deepEqual(said(addArrow({ atoms: [], bonds: [] }, { kind: "line", from: [0, 0], to: [2, 0], style: "dashed" })[0]), [["shape", "Dashed line"]]);
assert.deepEqual(said(addArrow({ atoms: [], bonds: [] }, { kind: "orbital", from: [0, 0], to: [1, 0], orbital: { shape: "p", phase: "shaded" } })[0]), [["shape", "p orbital, shaded"]]);
const plate = addShape({ atoms: [], bonds: [] }, { kind: "tlc", from: [0, 0], to: [3, 4], tlc: { lanes: 2, spots: [{ lane: 0, rf: 0.6 }, { lane: 0, rf: 0.3 }, { lane: 1, rf: 0.45 }] } })[0];
assert.deepEqual(said(plate), [["shape", "TLC plate, two lanes, three spots", "Lane 1: Rf 0.3, 0.6. Lane 2: Rf 0.45"]]);
const table = addShape({ atoms: [], bonds: [] }, { kind: "table", from: [0, 0], to: [4, 2], table: { cells: [["Entry", "Yield"], ["1", "85%"]] } })[0];
assert.deepEqual(said(table), [["shape", "Table, two rows, two columns", "Entry, Yield; 1, 85%"]]);
assert.deepEqual(said(addShape({ atoms: [], bonds: [] }, { kind: "brackets", from: [0, 0], to: [2, 2], polymer: { usage: "sru" } })[0]), [["shape", "Brackets, SRU n"]]);
assert.deepEqual(said(addShape({ atoms: [], bonds: [] }, { kind: "oval", from: [0, 0], to: [2, 2], dashed: true })[0]), [["shape", "Oval, dashed"]]);
assert.deepEqual(said(addCaption({ atoms: [], bonds: [] }, { text: "Scheme 1\nSynthesis of aspirin", x: 0, y: 0 })[0]), [["text", "Scheme 1, Synthesis of aspirin"]]);
// A spectrum added to the drawing (Editor.tsx addSpectrum) is one integral group, read by its title.
let spectrum: Mol = { atoms: [], bonds: [] };
const parts: number[] = [];
for (const add of [
  (m: Mol) => addArrow(m, { kind: "line", from: [0, 0], to: [14, 0] }),
  (m: Mol) => addArrow(m, { kind: "curve", from: [0, 0], to: [14, 0], curve: { points: [{ at: [0, 0] }, { at: [7, 3] }, { at: [14, 0] }] } }),
  (m: Mol) => addCaption(m, { text: "¹H NMR (400 MHz, CDCl3), predicted", x: 0, y: 4 }),
]) { const [m, id] = add(spectrum); spectrum = m; parts.push(id); }
const [grouped, gid] = groupSelection(spectrum, new Set(), new Set(parts))!;
spectrum = { ...grouped, groups: grouped.groups!.map((g) => (g.id === gid ? { ...g, integral: true as const } : g)) };
assert.deepEqual(said(spectrum), [["spectrum", "¹H NMR (400 MHz, CDCl3), predicted"]]);

// ——— Reading order: rows from the top, each from the left; a compound number follows its structure ———
let page = row([smiles("CCO"), 0], [smiles("CC=O"), 6]);
const first = fragments(page)[0];
page = addCaption(page, { text: "Notes", x: 0, y: -5 })[0];
page = addCaption(page, { text: "1", x: 0.8, y: -1.4, under: first })[0];
page = addCaption(page, { text: "Title", x: 3, y: 4 })[0];
assert.deepEqual(said(page).map(([, name]) => name), ["Title", "C2H6O, no rings", "1", "C2H4O, no rings", "Notes"]);
assert.deepEqual(readingOrder([[0, 0, 1, 1], undefined, [2, 0.2, 3, 0.8], [0, -3, 1, -2]]), [0, 2, 3, 1], "a box level with a row joins it; one with no box goes last");
assert.deepEqual(readingOrder([[4, -1, 6, 1.2], [0, -1, 2, 1], [2.5, 0, 3.5, 0]]), [1, 2, 0], "a level arrow, with no height, joins the row it is in");
assert.deepEqual(readingOrder([[0, -1, 2, 1], [0, -2, 2, -2]]), [0, 1], "a flat box under a row starts its own");

// ——— The hotspot: what it says, and where each arrow key takes it (edit.ts walkHot, as ChemDraw's) ———
// Ethanol drawn as a zig-zag: carbon 1 at the origin, carbon 2 up and right, oxygen 1 down and right.
const etoh: Mol = { atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [0.866, 0.5, 0] }, { label: "O", location: [1.732, 0, 0] }], bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }] };
const R: [number, number] = [1, 0], Lf: [number, number] = [-1, 0], U: [number, number] = [0, 1], D: [number, number] = [0, -1];
// Right, Right, Right, Right walks carbon 1, the C-C bond, carbon 2, the C-O bond, oxygen 1. An end atom has one bond,
// and any arrow key takes the hotspot onto it (ChemDraw's). Up from carbon 2 has no bond that way, so the hotspot stays
// (the editor says "No bond that way").
const walk = (from: { atom?: number; bond?: number }, keys: [number, number][]) => keys.reduce<{ atom?: number; bond?: number }[]>((all, k) => [...all, walkHot(etoh, all[all.length - 1], k)], [from]);
assert.deepEqual(walk({ atom: 0 }, [R, R, R, R, R]), [{ atom: 0 }, { bond: 0 }, { atom: 1 }, { bond: 1 }, { atom: 2 }, { bond: 1 }]);
assert.deepEqual(walk({ atom: 2 }, [Lf, Lf, Lf, Lf]), [{ atom: 2 }, { bond: 1 }, { atom: 1 }, { bond: 0 }, { atom: 0 }]);
assert.deepEqual(walk({ atom: 1 }, [U]), [{ atom: 1 }, { atom: 1 }]);
assert.deepEqual(walk({ atom: 1 }, [D]), [{ atom: 1 }, { atom: 1 }], "both bonds point down as much: the hotspot stays");
assert.deepEqual(walk({ bond: 0 }, [U, R]), [{ bond: 0 }, { atom: 1 }, { bond: 1 }], "from a bond, the end that lies that way");
assert.equal(atomText(etoh, 0), "Carbon 1, three hydrogens. Single bond to carbon 2 at 2 o'clock.");
assert.equal(atomText(etoh, 1), "Carbon 2, two hydrogens. Single bond to oxygen 1 at 4 o'clock; single bond to carbon 1 at 8 o'clock.");
assert.equal(atomText(etoh, 2), "Oxygen 1, one hydrogen. Single bond to carbon 2 at 10 o'clock.");
assert.equal(bondText(etoh, 1), "Single bond, carbon 2 to oxygen 1.");
// Shift+arrow jumps about three bonds along the structure.
assert.deepEqual(jumpHot(etoh, { atom: 0 }, R), { atom: 2 });
// Rings, charges, labels, wedges and double bonds.
const benzoate = smiles("[O-]C(=O)c1ccccc1"), ring = benzoate.atoms.findIndex((a, i) => a.label === "C" && benzoate.bonds.filter((b) => b.atoms.includes(i)).length === 3 && i > 1);
assert.match(atomText(benzoate, 0), /^Oxygen 1, negative charge, no hydrogens\. Single bond to carbon 1 at \d+ o'clock\.$/);
assert.match(atomText(benzoate, ring), /^Carbon \d, no hydrogens, in a 6-membered ring\. /);
assert.match(bondText(benzoate, benzoate.bonds.findIndex((b) => b.type === 2 && b.atoms.includes(1))), /^Double bond, carbon 1 to oxygen 2\.$|^Double bond, oxygen 2 to carbon 1\.$/);
const wedge: Mol = { ...etoh, atoms: [...etoh.atoms, { label: "C", text: "OMe", location: [0.866, 1.5, 0] }], bonds: [...etoh.bonds, { type: 1, stereo: 1, atoms: [1, 3] }] };
assert.equal(atomText(wedge, 1), "Carbon 2, one hydrogen. Wedge bond to label OMe at 12 o'clock, narrow end here; single bond to oxygen 1 at 4 o'clock; single bond to carbon 1 at 8 o'clock.");
assert.equal(atomText(wedge, 3), "Label OMe. Wedge bond to carbon 2 at 6 o'clock.");
assert.equal(bondText(wedge, 2), "Wedge bond, carbon 2 to label OMe, narrow end at carbon 2.");

// ——— Keys: Tab is free on the canvas, and the hotspot's keys are ChemDraw's ———
const map = keymap();
for (const place of ["none", "atom", "bond"] as const) for (const k of ["tab", "shift+tab"]) assert.equal(actionFor(map, k, place), undefined, `${k} is free (${place})`);
assert.ok(!Object.values(DEFAULT_KEYS).flat().some((k) => k.endsWith("tab")), "no default key uses Tab");
assert.equal(keyOf({ key: "Tab", shiftKey: true, altKey: false, metaKey: false, ctrlKey: false }), "shift+tab");
for (const [key, id] of [["arrowleft", "nudge.left"], ["arrowright", "nudge.right"], ["arrowup", "nudge.up"], ["arrowdown", "nudge.down"], ["shift+arrowright", "nudge.right10"]] as const) assert.equal(actionFor(map, key, "atom"), id);
assert.equal(actionFor(map, "enter", "atom"), "atom.label");
assert.ok(ACTIONS.some((a) => a.id === "select.here"));

// ——— What an edit says ———
const grow: Mol = { atoms: [...etoh.atoms, { label: "C", location: [2.598, 0.5, 0] }], bonds: [...etoh.bonds, { type: 1, atoms: [2, 3] }] };
assert.equal(changeText(etoh, grow), "Added a single bond, oxygen to carbon.");
assert.equal(changeText(grow, etoh), "Deleted one atom and one bond.");
assert.equal(changeText(etoh, setElement(etoh, 0, "N")), "Carbon changed to nitrogen.");
assert.equal(changeText(etoh, { ...etoh, atoms: etoh.atoms.map((a, i) => (i === 2 ? { ...a, charge: 1 } : a)) }), "Oxygen now has a positive charge.");
assert.equal(changeText(etoh, setBondSpec(etoh, 0, { type: 2 })), "Changed to a double bond.");
assert.equal(changeText(etoh, setBondSpec(etoh, 0, { type: 1, stereo: 6 })), "Changed to a hashed wedge bond.");
const all = new Set([0, 1, 2]);
assert.equal(changeText(etoh, moveAtoms(etoh, all, [1 / 14.4, 0])), "Moved 1 pt right.");
assert.equal(changeText(etoh, moveAtoms(etoh, all, [-10 / 14.4, 10 / 14.4])), "Moved 10 pt left and 10 pt up.");
assert.equal(changeText(etoh, { ...etoh, atoms: etoh.atoms.map((a, i) => ({ ...a, location: [a.location[0] * 1.1, a.location[1] + i * 0.1, 0] })) }), "Moved two atoms.", "a clean up moves atoms by different amounts");
assert.equal(changeText(etoh, rotateAtoms(etoh, all, 15)), "Turned 15° anticlockwise.", "Option+Up");
assert.equal(changeText(etoh, rotateAtoms(etoh, all, -1)), "Turned 1° clockwise.", "Option+Right");
assert.equal(changeText(etoh, flipAtoms(etoh, all, "horizontal")), "Turned over.", "Rotate 180° horizontal");
assert.equal(changeText(etoh, deleteAtom(etoh, 2)), "Deleted one atom and one bond.");
const [arrowed, aid] = addArrow(etoh, { kind: "reaction", from: [3, 0], to: [5, 0] });
assert.equal(changeText(etoh, arrowed), "Added a reaction arrow.");
assert.equal(changeText(arrowed, etoh), "Deleted a reaction arrow.");
const [texted, tid] = addCaption(etoh, { text: "THF", x: 0, y: -2 });
assert.equal(changeText(etoh, texted), "Added text THF.");
assert.equal(changeText(etoh, addCaption(etoh, { text: "+", x: 3, y: 0 })[0]), "Added a plus sign.");
assert.equal(changeText(etoh, addCaption(arrowed, { text: "+", x: 3, y: 0 })[0]), "Added two objects.", "a paste of several objects counts them");
assert.equal(changeText(texted, { ...texted, captions: texted.captions!.map((c) => (c.id === tid ? { ...c, text: "THF, 0 °C" } : c)) }), "Text now reads THF, 0 °C.");
assert.equal(changeText(arrowed, { ...arrowed, arrows: arrowed.arrows!.map((a) => (a.id === aid ? { ...a, from: [3, 1], to: [5, 1] } : a)) }), "Moved 14.4 pt up.");
assert.equal(changeText(etoh, etoh), "");

// ——— The focus ring: 3 to 1 on every page colour ———
assert.equal(ringOn("#FFFFFF"), undefined, "Octet's focus blue on white paper");
assert.equal(ringOn("#000B24"), undefined, "and on dark paper");
assert.equal(ringOn("#1D4B86"), "#FFFFFF", "white on engineering paper");
for (let r = 0; r <= 255; r += 51) for (let g = 0; g <= 255; g += 51) for (let b = 0; b <= 255; b += 51) {
  const page = `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`, ring = ringOn(page) ?? FOCUS;
  assert.ok(contrast(ring, page) >= 3, `the focus ring on ${page} is ${contrast(ring, page).toFixed(2)}:1`);
}
// The ring on the canvas is the brand's focus ring, shows in forced colours, and does not move or fade in.
const css = readFileSync(new URL("./editor.css", import.meta.url), "utf8"), rule = /\.canvas-access \[data-object\]:focus \{([^}]*)\}/.exec(css)?.[1] ?? "";
assert.match(rule, /box-shadow: var\(--shadow-focus\)/);
assert.match(rule, /outline: 2px solid transparent/);
assert.ok(!/canvas-access[^{]*\{[^}]*(transition|animation)/.test(css), "no motion on the canvas's focus");
// The names given after each edit read a name's structure only for its InChI, so it is Indigo's layout, untidied.
assert.match(readFileSync(new URL("./Editor.tsx", import.meta.url), "utf8"), /const inchiOf = \(s: Mol \| string\) => \{ try \{ return toInchi\(typeof s === "string" \? parseStructure\(s, false\) : s\)/);

// ——— Speed: a drawing of about 500 atoms ———
// n benzene rings in a grid, each with a side group, a caption under every fourth and an arrow between every fifth pair.
function large(n: number): Mol {
  let m: Mol = { atoms: [], bonds: [] };
  const cols = Math.ceil(Math.sqrt(n));
  for (let r = 0; r < n; r++) {
    const cx = (r % cols) * 4, cy = -Math.floor(r / cols) * 4, base = m.atoms.length;
    for (let i = 0; i < 6; i++) m.atoms.push({ label: "C", location: [cx + Math.cos((Math.PI / 3) * i), cy + Math.sin((Math.PI / 3) * i), 0] });
    for (let i = 0; i < 6; i++) m.bonds.push({ type: i % 2 ? 1 : 2, atoms: [base + i, base + ((i + 1) % 6)] });
    m.atoms.push({ label: r % 2 ? "O" : "N", location: [cx + 2, cy, 0] });
    m.bonds.push({ type: 1, atoms: [base, base + 6] });
    if (r % 4 === 0) m = addCaption(m, { text: String(r + 1), x: cx, y: cy - 1.6, under: [base] })[0];
    if (r % 5 === 0) m = addArrow(m, { kind: "reaction", from: [cx + 2.4, cy], to: [cx + 3.4, cy] })[0];
  }
  return m;
}
function time(f: () => unknown): number {
  f();
  let best = Infinity;
  for (let k = 0; k < 3; k++) {
    let n = 0;
    const t0 = performance.now();
    do { f(); n++; } while (performance.now() - t0 < 15);
    best = Math.min(best, (performance.now() - t0) / n);
  }
  return best;
}
const big = large(71), bigger = large(284), fast = (m: Mol) => ({ ...sources(m, { formulas: false }), reaction: undefined });
assert.ok(big.atoms.length >= 497, `${big.atoms.length} atoms`);
const nudged = moveAtoms(big, new Set(big.atoms.map((_, i) => i)), [1 / 14.4, 0]);
const budgets: [string, () => unknown, () => unknown, number][] = [
  ["every object named and ordered", () => describe(big, fast(big)), () => describe(bigger, fast(bigger)), 60],
  ["what the hotspot says", () => atomText(big, 200), () => atomText(bigger, 800), 10],
  ["what a nudge of everything says", () => changeText(big, nudged), () => changeText(bigger, moveAtoms(bigger, new Set(bigger.atoms.map((_, i) => i)), [1 / 14.4, 0])), 30],
];
for (const [what, small, four, budget] of budgets) {
  const t = time(small), t4 = time(four);
  assert.ok(t < budget, `${what}: ${t.toFixed(2)} ms on ${big.atoms.length} atoms, over the budget of ${budget} ms`);
  assert.ok(t4 < 10 * Math.max(t, 0.05), `${what}: ${t4.toFixed(2)} ms on four times the drawing, ${(t4 / t).toFixed(1)} times as long`);
}
console.log("access.check: ok");
