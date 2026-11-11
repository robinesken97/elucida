// Where a structure's labels run into each other or into a bond, as the app draws it: Octet's renderer at the default
// document style (ACS 1996, at true size), with Arial's advances and ink (each glyph's ink box at the cap or x-height,
// as src/render.check.ts measures). Two labels clash when their ink overlaps; a bond clashes with a label when one of
// its lines runs through it, but a bond of the label's own atom (which stops at it) never does. A label's box is taken
// 0.3 px in from its ink, so a line that only grazes it passes. Each bond is drawn in a colour of its own, so its lines
// are known. The library's build places substituents by it, and src/templates.check.ts checks every template with it.
import { render } from "../../src/render.ts";
import { frameStyle, DEFAULT_STYLE } from "../../src/docstyle.ts";
import { arialGlyph } from "../../src/cdxml.ts";

export const STYLE = frameStyle(DEFAULT_STYLE, (DEFAULT_STYLE.bond * 4) / 3);
export function arial(text) {
  const s = STYLE.size, glyph = (ch) => arialGlyph(ch).map((v) => (v * s) / 1000), cap = 0.716 * s, xh = 0.519 * s;
  const height = (ch) => (/[gjpqy]/.test(ch) ? [-0.21 * s, xh] : /[acemnorsuvwxz]/.test(ch) ? [0, xh] : ch === "+" ? [0.11 * s, 0.58 * s] : ch === "–" ? [0.22 * s, 0.3 * s] : [0, cap]);
  const outline = [];
  let x = 0, top = 0;
  for (const ch of text) {
    const [w, l, r] = glyph(ch), [lo, hi] = height(ch);
    for (let k = 0; k <= 8; k++) { const f = k / 8; outline.push([x + l + (r - l) * f, -lo], [x + l + (r - l) * f, -hi], [x + l, -lo - (hi - lo) * f], [x + r, -lo - (hi - lo) * f]); }
    x += w; top = Math.max(top, hi);
  }
  return { width: x, ascent: top, outline };
}

// An atom shows a label: not a skeletal carbon (a Newman projection's back carbon is a circle, not a label), nor a
// multi-centre point.
const shown = (a) => !a.centre && (a.label !== "C" || !!a.text || !!a.shown);
const inside = (p, b) => p[0] > b[0] && p[0] < b[2] && p[1] > b[1] && p[1] < b[3];
const cross = (p, q, r, s) => { const o = (a, c, e) => Math.sign((c[0] - a[0]) * (e[1] - a[1]) - (c[1] - a[1]) * (e[0] - a[0])); return o(p, q, r) * o(p, q, s) < 0 && o(r, s, p) * o(r, s, q) < 0; };
const through = (p, q, b) => inside(p, b) || inside(q, b) || [[[b[0], b[1]], [b[2], b[1]]], [[b[2], b[1]], [b[2], b[3]]], [[b[2], b[3]], [b[0], b[3]]], [[b[0], b[3]], [b[0], b[1]]]].some(([r, s]) => cross(p, q, r, s));

// The clashes, as words (empty when the labels are clear).
export function clashes(m) {
  const coloured = { ...m, bonds: m.bonds.map((b, k) => ({ ...b, colour: `#${(k + 1).toString(16).padStart(6, "0")}` })) };
  const d = render(coloured, STYLE, arial, STYLE.bond), out = [];
  const name = (i) => `${m.atoms[i].text ?? m.atoms[i].label}${i}`;
  const boxes = m.atoms.map((a, i) => (shown(a) && d.label[i] ? [d.label[i][0] + 0.3, d.label[i][1] + 0.3, d.label[i][2] - 0.3, d.label[i][3] - 0.3] : undefined));
  boxes.forEach((b, i) => boxes.forEach((o, j) => {
    if (j > i && b && o && Math.min(b[2], o[2]) > Math.max(b[0], o[0]) && Math.min(b[3], o[3]) > Math.max(b[1], o[1])) out.push(`labels ${name(i)} and ${name(j)} overlap`);
  }));
  const hit = new Set();
  d.polygons.forEach((poly, n) => {
    const k = parseInt((d.colours[n] ?? "#0").slice(1), 16) - 1, bond = m.bonds[k];
    if (!bond) return;
    boxes.forEach((b, c) => {
      if (!b || bond.atoms.includes(c) || hit.has(`${k} ${c}`)) return;
      if (poly.some((p, e) => through(p, poly[(e + 1) % poly.length], b))) { hit.add(`${k} ${c}`); out.push(`bond ${name(bond.atoms[0])}-${name(bond.atoms[1])} runs through label ${name(c)}`); }
    });
  });
  return out;
}
