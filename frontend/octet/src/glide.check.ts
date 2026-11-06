// Run: node src/glide.check.ts. Fails loudly if a glide (FEEL-38) goes a wrong way: it must start where the drawing
// was, end where it is, keep what did not move, and leave out a frame that does not draw well.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { between, MOST_GLIDE, moving } from "./glide.ts";
import type { Mol } from "./render.ts";

// Ethanol and a reaction arrow. The clean-up moves the oxygen and the arrow; the first carbon stays.
const a: Mol = {
  atoms: [{ label: "C", location: [0, 0, 0] }, { label: "C", location: [1, 0, 0] }, { label: "O", location: [1.2, 1.3, 0] }],
  bonds: [{ type: 1, atoms: [0, 1] }, { type: 1, atoms: [1, 2] }],
  arrows: [{ id: 7, kind: "reaction", from: [3, 0], to: [5, 0] }],
  captions: [{ id: 8, text: "Ethanol", x: 0, y: -1 }],
};
const b: Mol = {
  ...a,
  atoms: [a.atoms[0], { ...a.atoms[1], location: [0.866, 0.5, 0] }, { ...a.atoms[2], location: [1.732, 0, 0] }],
  arrows: [{ id: 7, kind: "reaction", from: [3, 1], to: [5, 1] }],
};
assert.equal(moving(a, b), 3, "two atoms and the arrow move");
assert.equal(moving(a, { ...a }), 0, "nothing moves");
assert.equal(moving(a, { ...b, atoms: b.atoms.slice(1) }), undefined, "a drawing with an atom less does not glide");
assert.ok(MOST_GLIDE === 300);

const start = between(a, b, 0)!, end = between(a, b, 1)!, mid = between(a, b, 0.5)!;
assert.deepEqual(start.atoms.map((x) => x.location), a.atoms.map((x) => x.location), "it starts where the atoms were");
assert.deepEqual(end.atoms.map((x) => x.location), b.atoms.map((x) => x.location), "it ends where the atoms are");
assert.deepEqual(mid.atoms[2].location, [1.466, 0.65, 0], "half way on a straight line");
assert.deepEqual(mid.arrows![0].from, [3, 0.5], "the arrow glides with the atoms");
assert.equal(mid.atoms[0], b.atoms[0], "an atom that did not move is the same atom, so its drawing is kept");
assert.equal(mid.captions![0], b.captions![0], "a caption that did not move is the same caption");
assert.equal(mid.bonds, b.bonds, "the bonds are the drawing's own");

// Rotate 180° across: every x goes through the middle, so the middle frames squeeze each bond to nothing. They are
// left out; the frames either side draw.
const flat: Mol = { atoms: [{ label: "C", location: [-0.5, 0, 0] }, { label: "C", location: [0.5, 0, 0] }], bonds: [{ type: 2, atoms: [0, 1] }] };
const turned: Mol = { ...flat, atoms: [{ label: "C", location: [0.5, 0, 0] }, { label: "C", location: [-0.5, 0, 0] }] };
assert.equal(between(flat, turned, 0.5), undefined, "a bond squeezed to nothing is left out");
assert.equal(between(flat, turned, 0.45), undefined, "and one squeezed to a tenth");
assert.ok(between(flat, turned, 0.3), "a bond at two fifths of its length draws");
const arrowFlat: Mol = { atoms: [], bonds: [], arrows: [{ id: 1, kind: "reaction", from: [-1, 0], to: [1, 0] }] };
assert.equal(between(arrowFlat, { ...arrowFlat, arrows: [{ id: 1, kind: "reaction", from: [1, 0], to: [-1, 0] }] }, 0.5), undefined, "so is an arrow");
// A catalytic cycle tidied: its circle grows and its break turns round to its new place the short way, with the
// intermediates on it. Its arcs are laid out from where they are, so they glide too. Tidy and Make a cycle glide.
const ring: Mol = { atoms: [{ label: "C", location: [0, 3, 0] }], bonds: [], cycles: [{ id: 3, centre: [0, 0], radius: 3, clockwise: true, nodes: [[0], []], at: [Math.PI / 2, 3] }] };
const tidied: Mol = { ...ring, atoms: [{ label: "C", location: [0, 4, 0] }], cycles: [{ ...ring.cycles![0], radius: 4, at: [Math.PI / 2, -Math.PI / 2] }] };
const half = between(ring, tidied, 0.5)!.cycles![0];
assert.equal(half.radius, 3.5, "the radius glides");
// From 3 rad to -π/2 the short way is up, through 3π/2 - (3π/2 - 3) / 2, not back down through 0.
assert.ok(Math.abs(half.at[1] - (3 + (1.5 * Math.PI - 3) / 2)) < 1e-9, `the break turns the short way: ${half.at[1]}`);
assert.deepEqual(between(ring, tidied, 0.5)!.atoms[0].location, [0, 3.5, 0], "the intermediate glides with it");
assert.ok(Math.abs(Math.sin(between(ring, tidied, 1)!.cycles![0].at[1]) + 1) < 1e-9, "and ends where it is");
const editor = readFileSync(new URL("./Editor.tsx", import.meta.url), "utf8");
assert.match(editor, /what === "tidy"\) return glideTo\(/, "Tidy the cycle glides");
assert.match(editor, /glideTo\(spread\(m, m\.cycles!/, "Make a cycle glides");
assert.match(editor, /m = spread\(m, m\.cycles!\.find\(\(x\) => x\.id === c\.id\)!, d\)/, "Clean Up tidies a picked cycle, inside its glide");
console.log("glide.check: ok");
