// File > More Formats > Export LaTeX (chemfig)…: the structures as code for LaTeX's chemfig package, as the page draws
// them (issue 59). Each bond takes its angle and length from the page, so any layout comes out as drawn, and a ring
// closes with a hook (?[1] on the atom written first, ?[1] again on the other). Labels read as the page reads them (OH,
// HO, MeO, an indole's NH stacked), each bond meets the label's own atom, wedges are narrow at the stereocentre, and a
// double bond's second line is on the page's side. Separate structures keep their places: each hangs off the first by
// a bond chemfig does not draw. Charges are kept; other marks, colours, arrows, text and shapes are not.
import { AROMATIC, H_FIRST, HBOND, QUADRUPLE, hydrogens, orderOf, render, type Atom, type Bond, type Face, type Ink, type Mol, type Style } from "./render.ts";
import { pieces, units } from "./labels.ts";

// Text from a file goes into LaTeX: only letters, digits and these signs are kept, so it can hold no command.
const clean = (t: string) => t.replace(/[^A-Za-z0-9'()+.,*-]/g, "");
const sub = (n: string) => (n.length > 1 ? `_{${n}}` : `_${n}`);
// One chemfig atom: an element or group as it is (Cl, Me, H_2), anything else in braces, which chemfig does not split.
const one = (t: string) => (/^[A-Z][a-z0-9'_{}]*$/.test(t) ? t : `{${t}}`);
const num = (x: number, places: number) => `${+x.toFixed(places)}`;
const sign = (a: Atom) => {
  const c = a.charge ?? 0, n = Math.abs(c) > 1 ? Math.abs(c) : "";
  return c ? `${n}${a.circled ? (c > 0 ? "\\oplus" : "\\ominus") : c > 0 ? "+" : "-"}` : "";
};

// The structures in mol as one \chemfig{…}, or "" when there are none. s and measure: the page's, for render.
export function toChemfig(mol: Mol, s: Style, measure: (text: string, face?: Face) => Ink): string {
  const d = render(mol, s, measure), atoms = mol.atoms, f = d.scale / s.bond, at = (i: number) => atoms[i].location;
  // The bonds drawn round each atom shown: not a hydrogen bond, nor one to an H that Toggle Hydrogen Display hides.
  const nbrs = atoms.map((): { to: number; k: number }[] => []);
  mol.bonds.forEach((b, k) => {
    const [i, j] = b.atoms;
    if (b.type !== HBOND && !atoms[i].hidden && !atoms[j].hidden) { nbrs[i].push({ to: j, k }); nbrs[j].push({ to: i, k }); }
  });
  const toward = (i: number, j: number): [number, number] => { const x = at(j)[0] - at(i)[0], y = at(j)[1] - at(i)[1], l = Math.hypot(x, y) || 1; return [x / l, y / l]; };
  const degrees = (i: number, j: number) => { const [x, y] = toward(i, j); return (Math.atan2(y, x) * 180) / Math.PI; };

  // Each atom as chemfig atoms (its label's parts, in the order the page reads them), the part its bonds meet, and its
  // charge after the last part.
  const labels = atoms.map((a, i) => {
    const deg = nbrs[i].length, end = sign(a) && `^{${sign(a)}}`;
    if (!d.label[i] || a.attach) {
      // No label: chemfig's empty atom, with a charge beside it in the widest gap between its bonds (up and right
      // first), or where it was moved by hand, as the page puts it.
      if (!end) return { parts: [""], anchor: 0, end: "" };
      const ts = nbrs[i].map((n) => degrees(i, n.to)), gap = (t: number) => Math.min(...ts.map((b) => Math.abs(((t - b + 540) % 360) - 180)));
      const t = a.angles?.charge ?? [45, 135, -45, -135, 90, 0, -90, 180].reduce((best, c) => (gap(c) > gap(best) + 0.5 ? c : best));
      return { parts: [`\\charge{${num(t, 0)}:4pt=$\\scriptstyle ${sign(a)}$}{}`], anchor: 0, end: "" };
    }
    // Which way the label reads, as on the page: away from bonds on its right (within 70° of level), or as aligned by
    // hand. Steep bonds on both sides stack the H above or below.
    const v = nbrs[i].reduce<[number, number]>((p, n) => { const [x, y] = toward(i, n.to); return [p[0] + x, p[1] + y]; }, [0, 0]);
    const steep = Math.hypot(...v) > 1e-6 && Math.abs(v[1]) > Math.abs(v[0]) * Math.tan((70 * Math.PI) / 180);
    const rtl = a.align ? a.align === "right" : deg > 0 && !steep && v[0] > 1e-6;
    if (a.text) {
      const us = units(clean(a.text)).map((u) => one(pieces(u).map((p) => p.text + (p.count ? sub(p.count) : "")).join("")));
      return rtl ? { parts: us.reverse(), anchor: us.length - 1, end } : { parts: us, anchor: 0, end };
    }
    const used = nbrs[i].reduce((n, { k }) => n + orderOf(mol.bonds[k].type), 0);
    const h = s.hideH ? 0 : a.implicitHCount ?? hydrogens(a.label, a.charge ?? 0, used, a.radical === 3 ? 2 : a.radical);
    const el = one(`${a.isotope ? `^{${a.isotope}}` : ""}${clean(a.label)}`), hs = h ? `H${h > 1 ? sub(String(h)) : ""}` : "";
    const stack = a.align === "above" || a.align === "below" ? a.align : !a.align && steep && deg > 1 ? (v[1] < 0 ? "above" : "below") : undefined;
    if (hs && stack) return { parts: [`\\chem${stack}{${el}}{${hs}}`], anchor: 0, end };
    // H goes first read right to left (HO, H2N), and on a lone atom written that way (H2O, HCl).
    const back = rtl || (!a.align && !deg && H_FIRST.has(a.label));
    return { parts: !hs ? [el] : back ? [hs, el] : [el, hs], anchor: hs && back ? 1 : 0, end };
  });

  // A bond's character, looking from its atom `from`: wedges narrow at Octet's stereocentre (atoms[0]), and a double
  // bond's second line on the page's side (sides: -1 left of atoms[0] to atoms[1], chemfig's =^ that way round).
  const look = (b: Bond, k: number, from: number) => {
    const forward = b.atoms[0] === from, wedge = b.stereo === 1 ? "" : b.stereo === 6 ? ":" : b.display === "hollow" ? "|" : undefined;
    if ((b.type === 1 || b.type === AROMATIC) && wedge !== undefined) return (forward ? "<" : ">") + wedge;
    if (b.type === 2) return d.sides?.[k] ? ((d.sides[k] < 0) === forward ? "=^" : "=_") : "=";
    return b.type === 3 || b.type === QUADRUPLE ? "~" : "-";
  };
  // Bond k from atom i to atom j as chemfig writes it: its angle, its length where it is not one bond length, and the
  // part of each label it meets where the label has more than one. No k: a bond chemfig does not draw.
  const bond = (i: number, j: number, k?: number) => {
    const l = Math.hypot(at(j)[0] - at(i)[0], at(j)[1] - at(i)[1]) * f;
    const fields = [`:${num(degrees(i, j), 1)}`, Math.abs(l - 1) > 0.02 ? num(l, 2) : "", ...[i, j].map((n) => (labels[n].parts.length > 1 ? String(labels[n].anchor + 1) : "")), k === undefined ? "draw=none" : ""];
    return `${k === undefined ? "-" : look(mol.bonds[k], k, i)}[${fields.join(",").replace(/,+$/, "")}]`;
  };

  // Each structure as a tree from its leftmost atom (a walk with no recursion, so a long chain is safe). A bond back to
  // an atom on the path closes a ring: that atom is written first, and chemfig draws the hook's bond from it. The walk
  // takes double bonds first, so a ring closes on a single bond: chemfig reads no side (=^, =_) on a hook.
  const seen = atoms.map(() => false), kids: number[][] = atoms.map(() => []), via: number[] = [], hooks = atoms.map(() => "");
  const done = new Set<number>(), order: number[] = [], roots: number[] = [];
  let named = 0;
  const shown = atoms.map((_, i) => i).filter((i) => !atoms[i].hidden).sort((i, j) => at(i)[0] - at(j)[0] || at(j)[1] - at(i)[1]);
  for (const r of shown) {
    if (seen[r]) continue;
    seen[r] = true;
    roots.push(r);
    order.push(r);
    for (const path = [r]; path.length; ) {
      const u = path[path.length - 1], e = nbrs[u].find((n) => !done.has(n.k) && mol.bonds[n.k].type === 2) ?? nbrs[u].find((n) => !done.has(n.k));
      if (!e) { path.pop(); continue; }
      done.add(e.k);
      if (seen[e.to]) {
        const c = look(mol.bonds[e.k], e.k, e.to);
        hooks[e.to] += `?[${++named}]`;
        hooks[u] += `?[${named}${c === "-" ? "" : `,{${c}}`}]`;
      } else { seen[e.to] = true; via[e.to] = e.k; kids[u].push(e.to); order.push(e.to); path.push(e.to); }
    }
  }
  if (!roots.length) return "";
  // The largest subtree runs on as the main chain and the rest are branches, so branches nest at most log2(atoms) deep.
  const size = atoms.map(() => 1);
  for (let n = order.length - 1; n >= 0; n--) for (const c of kids[order[n]]) size[order[n]] += size[c];
  const code = (i: number) => {
    const { parts, anchor, end } = labels[i];
    return parts.map((p, n) => (n && !/^[A-Z]/.test(p) ? "|" : "") + p + (n === parts.length - 1 ? end : "") + (n === anchor ? hooks[i] : "")).join("");
  };
  const write = (u: number, more = ""): string => {
    let out = "";
    for (let i: number | undefined = u; i !== undefined; more = "") {
      out += code(i) + more;
      const main: number | undefined = kids[i].reduce<number | undefined>((m, c) => (m === undefined || size[c] >= size[m] ? c : m), undefined);
      for (const c of kids[i]) if (c !== main) out += `(${bond(i, c, via[c])}${write(c)})`;
      if (main !== undefined) out += bond(i, main, via[main]);
      i = main;
    }
    return out;
  };
  const [first, ...rest] = roots;
  return `\\chemfig{${write(first, rest.map((r) => `(${bond(first, r)}${write(r)})`).join(""))}}`;
}
