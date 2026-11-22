// Run: node src/chemfig.check.ts. Fails loudly if File > More Formats > Export LaTeX (chemfig)… (src/chemfig.ts) stops
// writing the chemfig code for these structures: bonds at the page's angles and lengths, rings closed by hooks, double
// bonds on the page's side, triple bonds, wedges narrow at the stereocentre, charges, and labels read as the page reads
// them and met at their own atom. It compiles nothing: it checks the code.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { toChemfig } from "./chemfig.ts";
import type { Atom, Bond, Ink } from "./render.ts";

type P = [number, number];
const pt = 4 / 3;
const S = { bond: 14.4 * pt, line: 0.6 * pt, bold: 2 * pt, spacing: 0.18 * 14.4 * pt, hash: 2.5 * pt, margin: 1.69 * pt, size: 10 * pt };
// Every glyph is a box about an Arial capital's size, as in render.check.ts.
const box: P[] = [];
for (let i = 0; i <= 10; i++) { const f = i / 10; box.push([9.6 * f, 0], [9.6 * f, -9.5], [0, -9.5 * f], [9.6, -9.5 * f]); }
const ink = (): Ink => ({ width: 9.6, ascent: 9.5, outline: box });
const c30 = Math.cos(Math.PI / 6), s30 = 0.5;
const A = (label: string, x: number, y: number, more: Partial<Atom> = {}): Atom => ({ label, location: [x, y, 0], ...more });
const B = (a: number, b: number, type = 1, more: Partial<Bond> = {}): Bond => ({ type, atoms: [a, b], ...more });
const cf = (atoms: Atom[], bonds: Bond[]) => toChemfig({ atoms, bonds }, S, ink);

// Ethanol as a zigzag: skeletal carbons are empty atoms, each bond at its angle, and OH met at its O.
assert.equal(cf([A("C", 0, 0), A("C", c30, s30), A("O", 2 * c30, 0)], [B(0, 1), B(1, 2)]), "\\chemfig{-[:30]-[:-30,,,1]OH}");
// Drawn the other way, the label reads HO, as on the page, and the bond leaves its O.
assert.equal(cf([A("O", 0, 0), A("C", c30, s30), A("C", 2 * c30, 0)], [B(0, 1), B(1, 2)]), "\\chemfig{HO-[:30,,2]-[:-30]}");
// A bond straight down from NH2, and into H2N.
assert.equal(cf([A("C", 0, 0), A("N", 0, 1)], [B(0, 1)]), "\\chemfig{NH_2-[:-90,,1]}");
assert.equal(cf([A("N", 0, 0), A("C", c30, -s30)], [B(0, 1)]), "\\chemfig{H_2N-[:-30,,2]}");
// A bond longer than the drawing's bond length (its median bond, as the page draws it) gives its length.
assert.equal(cf([A("C", 0, 0), A("C", 1, 0), A("C", 2, 0), A("C", 2, 1.5)], [B(0, 1), B(1, 2), B(2, 3)]), "\\chemfig{-[:0]-[:0]-[:90,1.5]}");

// Benzene: a hook closes the ring on a single bond (chemfig reads no side on a hook), and each double bond's second
// line is inside it (=^ on the left going round anticlockwise).
const hex = Array.from({ length: 6 }, (_, k) => A("C", Math.cos(((30 + 60 * k) * Math.PI) / 180), Math.sin(((30 + 60 * k) * Math.PI) / 180)));
const kekule = [0, 1, 2, 3, 4, 5].map((k) => B(k, (k + 1) % 6, k % 2 ? 1 : 2));
assert.equal(cf(hex, kekule), "\\chemfig{?[1]=^[:-90]-[:-30]=^[:30]-[:90]=^[:150]?[1]}");
// Pyridine: the hook goes on the N, after its label.
assert.equal(cf(hex.map((a, k) => (k === 2 ? { ...a, label: "N" } : a)), kekule), "\\chemfig{N?[1]=^[:-90]-[:-30]=^[:30]-[:90]=^[:150]?[1]}");
// A double bond in a chain goes on the page's side; a terminal C=O is centred.
assert.equal(cf([A("C", 0, 0), A("C", c30, s30), A("C", 2 * c30, 0), A("C", 3 * c30, s30)], [B(0, 1), B(1, 2, 2), B(2, 3)]), "\\chemfig{-[:30]=_[:-30]-[:30]}");
assert.equal(cf([A("C", 0, 0), A("C", c30, s30), A("O", c30, 1 + s30), A("O", 2 * c30, 0)], [B(0, 1), B(1, 2, 2), B(1, 3)]), "\\chemfig{-[:30](=[:90]O)-[:-30,,,1]OH}");

// Triple bonds; a quadruple bond, which chemfig has no character for, as a triple.
assert.equal(cf([A("C", 0, 0), A("N", 1, 0)], [B(0, 1, 3)]), "\\chemfig{~[:0]N}");
assert.equal(cf([A("Mo", 0, 0), A("Mo", 1, 0)], [B(0, 1, 14)]), "\\chemfig{Mo~[:0]Mo}");
// Wedges: chemfig's < is narrow at the atom it leaves, Octet's wedge at atoms[0], the stereocentre.
const wedge = (b: Bond) => cf([A("C", 0, 0), A("C", 1, 0)], [b]);
assert.equal(wedge(B(0, 1, 1, { stereo: 1 })), "\\chemfig{<[:0]}");
assert.equal(wedge(B(1, 0, 1, { stereo: 1 })), "\\chemfig{>[:0]}");
assert.equal(wedge(B(0, 1, 1, { stereo: 6 })), "\\chemfig{<:[:0]}");
assert.equal(wedge(B(1, 0, 1, { display: "hollow" })), "\\chemfig{>|[:0]}");
// A wedge that closes a ring is written on the hook, the way round its bond is drawn (from the atom written first).
assert.match(cf(hex, [...kekule.slice(0, 2), B(3, 2, 1, { stereo: 1 }), ...kekule.slice(3)]), /^\\chemfig\{\?\[1\][^?]*\?\[1,\{>\}\]\}$/);

// Charges and isotopes: H2O with its H first, NH4+, 13CH4, a circled charge, and a skeletal carbocation's + beside its
// carbon, in the gap between its bonds.
assert.equal(cf([A("O", 0, 0)], []), "\\chemfig{H_2O}");
assert.equal(cf([A("N", 0, 0, { charge: 1 })], []), "\\chemfig{NH_4^{+}}");
assert.equal(cf([A("C", 0, 0, { isotope: 13 })], []), "\\chemfig{{^{13}C}H_4}");
assert.equal(cf([A("O", 0, 0, { charge: -2, circled: true })], []), "\\chemfig{O^{2\\ominus}}");
assert.equal(cf([A("C", 0, 0), A("C", c30, s30, { charge: 1 }), A("C", 2 * c30, 0)], [B(0, 1), B(1, 2)]), "\\chemfig{-[:30]\\charge{90:4pt=$\\scriptstyle +$}{}-[:-30]}");
assert.equal(cf([A("C", 0, 0), A("C", c30, s30, { charge: -1, angles: { charge: 200 } }), A("C", 2 * c30, 0)], [B(0, 1), B(1, 2)]), "\\chemfig{-[:30]\\charge{200:4pt=$\\scriptstyle -$}{}-[:-30]}");

// Written labels: OMe reads MeO from the right and its bond meets the O; CO2Et either way; text chemfig would read as
// code goes in braces, a chemfig atom of its own.
assert.equal(cf([A("O", 0, 0, { text: "OMe" }), A("C", 1, 0)], [B(0, 1)]), "\\chemfig{MeO-[:0,,2]}");
assert.equal(cf([A("C", 0, 0), A("C", 1, 0, { text: "CO2Et" })], [B(0, 1)]), "\\chemfig{-[:0,,,1]CO_2Et}");
assert.equal(cf([A("C", 0, 0, { text: "CO2Et" }), A("C", 1, 0)], [B(0, 1)]), "\\chemfig{EtO_2C-[:0,,3]}");
assert.equal(cf([A("C", 0, 0), A("C", 1, 0, { text: "C(CH3)3" })], [B(0, 1)]), "\\chemfig{-[:0,,,1]C|{(CH_3)_3}}");
// An N between steep bonds stacks its H, as an indole's NH; a hidden H is not written, but counts in the label.
assert.equal(cf([A("N", 0, 0), A("C", c30, s30), A("C", -c30, s30)], [B(0, 1), B(0, 2)]), "\\chemfig{-[:-30]\\chembelow{N}{H}-[:30]}");
assert.equal(cf([A("C", 0, 0), A("H", 1, 0, { hidden: true })], [B(0, 1)]), "\\chemfig{CH_4}");
// A label from a file can hold no LaTeX: only letters, digits and a few signs are written.
assert.equal(cf([A("C", 0, 0), A("C", 1, 0, { text: "}\\input{x}$#%&~^_" })], [B(0, 1)]), "\\chemfig{-[:0,,,1]{i}|{n}|{p}|{u}|{t}|{x}}");

// Separate structures keep their places: the second hangs off the first by a bond chemfig does not draw.
assert.equal(cf([A("Na", 0, 0, { charge: 1 }), A("Cl", 2, 0, { charge: -1 })], []), "\\chemfig{Na^{+}(-[:0,2,,,draw=none]Cl^{-})}");
assert.equal(cf([], []), "");
// A long chain with a branch on every carbon is written with branches one deep, so no walk runs out of stack.
{
  const n = 3000, atoms = Array.from({ length: 2 * n }, (_, k) => A("C", Math.floor(k / 2) * c30, k % 2 ? 1 + (k % 4 === 1 ? s30 : 0) : k % 4 ? 0 : s30));
  const bonds = Array.from({ length: n }, (_, k) => B(2 * k, 2 * k + 1)).concat(Array.from({ length: n - 1 }, (_, k) => B(2 * k, 2 * k + 2)));
  let depth = 0, deepest = 0;
  for (const ch of cf(atoms, bonds)) { depth += ch === "(" ? 1 : ch === ")" ? -1 : 0; deepest = Math.max(deepest, depth); }
  assert.equal(deepest, 1, "branches one deep");
}

// The command is in File > More Formats, and the app saves its code as a .tex file.
const editor = readFileSync(new URL("Editor.tsx", import.meta.url), "utf8"), rust = readFileSync(new URL("../src-tauri/src/export.rs", import.meta.url), "utf8");
assert.match(editor, /\["more_chemfig", "Export LaTeX \(chemfig\)…", <BracketsCurly size=\{18\} \/>, \(\) => checkFirst\(\(\) => void exportChemfig\(\)\)\],/);
assert.match(editor, /tex = toChemfig\(part, frame, measure\);[\s\S]{0,200}exportFile\(\{ name, format: "tex", tex \}\)/);
assert.match(rust, /\("tex", "LaTeX \(chemfig\)", &\["tex"\]\)/);
assert.match(rust, /"tex" => e\.tex\.is_some\(\),/);
assert.match(rust, /"tex" => format!\("\{\}\\n", e\.tex\.as_deref\(\)\.unwrap_or_default\(\)\.trim\(\)\)\.into_bytes\(\),/);
