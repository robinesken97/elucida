// The library's Photochemistry set: a Jablonski diagram and its transitions, light, a photochemical and a thermal step,
// an excited state, singlet and triplet oxygen, state labels and a sensitiser. Each is made of Octet's own objects
// (lines and arrows, text with subscripts and superscripts, brackets), so every part stays editable. Lines take the
// document's line width and text the document's caption style, with no colour of their own, as the Lab group's
// drawings do. As IUPAC draws a Jablonski diagram, radiative transitions are straight arrows and radiationless ones
// wavy. Bond lengths, y up; each template is centred where it is placed.

// Half the height of a capital in the default style (Arial 10 pt over a 14.4 pt bond): a line of text whose
// baseline is this far below a point is centred on it.
const CAP = 0.25;
// A wavy arrow's wave (0.2 bond lengths long) ends on its axis where the default style's small head starts (8.75 line
// widths back from the tip), so the head sits on the wave: a length of 0.365 and a whole number of half waves. Each
// arrow alone is this long, which also leaves its text room (the page lengthens an arrow its conditions overrun).
const L = 0.365 + 1.8;
const SUB = (text) => ({ text, script: "sub" }), SUP = (text) => ({ text, script: "super" });
// h and ν are quantities, so italic (IUPAC).
const HV = { text: "hν", italic: true };

// A template's objects, each with the next id: text (runs, or one run whose style is the caption's own), lines and
// arrows, and brackets. on: the text is the conditions of that arrow, on the side given (above is left of a steep
// arrow); otherwise it is centred on (x, y), or set by align. Places are kept to 0.0001 bond length (L/2 is 1.0825),
// so the library holds no floating-point noise.
const r4 = (v) => Math.round(v * 1e4) / 1e4 + 0, p4 = (q) => q.map(r4);
function parts() {
  let id = 0;
  const mol = { atoms: [], bonds: [], arrows: [], captions: [], shapes: [] };
  return {
    mol,
    text(runs, x, y, more = {}) {
      const [one] = runs, text = runs.map((r) => r.text).join("");
      const style = runs.length === 1 ? (({ text: _, ...own }) => own)(one) : { runs };
      mol.captions.push({ id: ++id, text, x: r4(x), y: r4(more.on ? y : y - CAP), ...style, ...more });
      return id;
    },
    arrow(kind, from, to, more = {}) { mol.arrows.push({ id: ++id, kind, from: p4(from), to: p4(to), ...more }); return id; },
    shape(kind, from, to, more = {}) { mol.shapes.push({ id: ++id, kind, from: p4(from), to: p4(to), ...more }); return id; },
  };
}
// The parts as a template: lists with nothing in them left out, one group of all of them when asked.
const done = (name, also, { mol }, grouped = false) => {
  const out = Object.fromEntries(Object.entries(mol).filter(([k, v]) => k === "atoms" || k === "bonds" || v.length));
  const items = [...mol.arrows, ...mol.captions, ...mol.shapes].map((x) => x.id).sort((a, b) => a - b);
  return { name, also, mol: grouped ? { ...out, groups: [{ id: items.length + 1, atoms: [], items }] } : out };
};

// An arrow across or up the middle, with its text beside it as its conditions (they move with it): a line with a head
// (a transition) or a reaction arrow (a step).
function transition(name, also, runs, { kind = "line", wavy = false, up = false, down = false } = {}) {
  const p = parts(), steep = up || down, h = L / 2;
  const [from, to] = steep ? [[0, up ? -h : h], [0, up ? h : -h]] : [[-h, 0], [h, 0]];
  const arrow = p.arrow(kind, from, to, { ...(wavy ? { style: "wavy" } : {}), ...(kind === "line" ? { end: "full" } : {}) });
  p.text(runs, 0, 0, { on: { arrow, side: steep ? "below" : "above" } });
  return done(name, also, p);
}
// Text alone, centred.
function label(name, also, runs, more = {}) {
  const p = parts();
  p.text(runs, 0, 0, more);
  return done(name, also, p);
}

// An excited state: X in square brackets with an asterisk at the top right (the brackets' mark).
function excited() {
  const p = parts();
  p.shape("brackets", [-0.5, -0.5], [0.5, 0.5], { mark: "*" });
  p.text([{ text: "X" }], 0, 0);
  return done("Excited state", "[X]*, excited, asterisk, brackets, photochemistry", p, true);
}

// A Jablonski diagram: S0, S1 and T1, each a level and two vibrational levels above it, with absorption from S0 to
// S1, fluorescence from S1, intersystem crossing to T1 and phosphorescence from T1 to S0. Its parts are in one group
// (not integral), so a click picks all of it and a double-click picks a part to relabel or move.
function jablonski() {
  const p = parts(), G = 0.35, [w, h] = [7.6, 4.6 + 2 * G], at = (x, y) => [x - w / 2, y - h / 2];
  const stack = (x0, x1, y) => [0, 1, 2].forEach((v) => p.arrow("line", at(x0, y + v * G), at(x1, y + v * G)));
  stack(0, w, 0);
  stack(0, 3.4, 4.6);
  stack(5, w, 3.2);
  p.text([{ text: "S" }, SUB("0")], ...at(-0.25, 0), { align: "right", chemical: false });
  p.text([{ text: "S" }, SUB("1")], ...at(-0.25, 4.6), { align: "right", chemical: false });
  p.text([{ text: "T" }, SUB("1")], ...at(w + 0.25, 3.2), { align: "left", chemical: false });
  const on = (from, to, runs, side, more = {}) => p.text(runs, ...at((from[0] + to[0]) / 2, (from[1] + to[1]) / 2), { on: { arrow: p.arrow("line", at(...from), at(...to), { end: "full", ...more }), side } });
  on([0.8, 0], [0.8, 4.6 + 2 * G], [HV, SUB("A")], "above");
  on([2.2, 4.6], [2.2, G], [HV, SUB("F")], "below");
  // Its length a whole number of half waves past the head, as L is.
  on([3.3, 4.6], [5.768, 3.2 + 2 * G], [{ text: "ISC" }], "above", { style: "wavy" });
  on([6.3, 3.2], [6.3, G], [HV, SUB("P")], "above");
  return done("Jablonski diagram", "energy level diagram, state diagram, S0, S1, T1, absorption, fluorescence, phosphorescence, intersystem crossing", p, true);
}

export const PHOTOCHEM = [
  jablonski(),
  transition("Light", "hν, hv, h nu, photon, irradiation, wavy arrow", [HV], { wavy: true }),
  transition("Photochemical step", "hν, hv, h nu, irradiation, photolysis, reaction arrow", [HV], { kind: "reaction" }),
  transition("Thermal step", "Δ, heat, delta, heating, reflux, reaction arrow", [{ text: "Δ" }], { kind: "reaction" }),
  transition("Absorption", "hv, excitation, radiative transition, Jablonski", [HV, SUB("A")], { up: true }),
  transition("Fluorescence", "hv, emission, radiative transition, Jablonski", [HV, SUB("F")], { down: true }),
  transition("Phosphorescence", "hv, emission, radiative transition, Jablonski", [HV, SUB("P")], { down: true }),
  transition("Intersystem crossing", "ISC, radiationless transition, wavy arrow, Jablonski", [{ text: "ISC" }], { wavy: true }),
  transition("Internal conversion", "IC, radiationless transition, wavy arrow, Jablonski", [{ text: "IC" }], { wavy: true, down: true }),
  excited(),
  label("Singlet oxygen", "1O2, ¹O₂, dioxygen, photooxygenation", [SUP("1"), { text: "O" }, SUB("2")]),
  label("Triplet oxygen", "3O2, ³O₂, dioxygen, ground state oxygen", [SUP("3"), { text: "O" }, SUB("2")]),
  label("Ground state", "S0, S₀, singlet, Jablonski", [{ text: "S" }, SUB("0")], { chemical: false }),
  label("Singlet excited state", "S1, S₁, singlet, Jablonski", [{ text: "S" }, SUB("1")], { chemical: false }),
  label("Triplet excited state", "T1, T₁, triplet, Jablonski", [{ text: "T" }, SUB("1")], { chemical: false }),
  label("Sensitiser", "Sens, sensitizer, photosensitiser, photocatalyst", [{ text: "Sens" }]),
  label("Excited sensitiser", "Sens*, sensitizer, photosensitiser, photocatalyst, excited state", [{ text: "Sens*" }]),
];
