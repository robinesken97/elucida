// The fast glide (decision 0024): a glide that moves only structures draws its frames without drawing the structures
// again. Each structure is drawn once where it starts and once where it ends (render.ts renderParts); every frame
// then slides each point of its ink and each label from one to the other, and writes the paths straight to the page
// (GlideLayer.tsx). A frame costs about a millisecond for a thousand atoms, so a glide stays smooth on a slow laptop.
// A structure whose two drawings do not match point for point (a hashed wedge drawn with more stripes, a double bond's
// second line moved to its other side) fades from one drawing to the other instead.
import type { Drawing, Label } from "./render.ts";

type P = [number, number];
export type PartIn = { ids: number[]; drawing: Drawing; at: P; k: number; turn: number };
// One colour of a structure's ink: its points at the start and at the end (x, y, x, y, …), and how many points each
// polygon has, in the order the editor draws them (structurePaths), so the last frame is the editor's own path.
export type Group = { key: string; from: Float64Array; to: Float64Array; sizes: number[]; turn?: Turn };
// A turn (Turn 15°, Rotate…): the points go round the centre (px) by the angle (radians, as on the page), so the
// structure keeps its shape on the way; whatever the turned drawing differs by from the new one is added in as it goes.
export type Turn = { centre: P; angle: number };
// A label slides from where it was to where it is; one whose text changed (OH turned to HO by Rotate 180°) slides as
// two, the old text fading out and the new one in (was). fades: ink that does not match point for point (a hashed
// wedge drawn with one stripe more), as paths for each colour key, the old fading out and the new in.
export type Slide = { kind: "slide"; id: number; groups: Group[]; labels: { label: Label; was?: Label; from: P; to: P; turn?: Turn }[]; fades: { key: string; out: string; in: string }[] };
export type Fade = { kind: "fade"; id: number; from: PartIn; to: PartIn };
export type GlidePart = Slide | Fade;

// A polygon's colour and strength, as the editor groups ink (Editor.tsx structurePaths): one path for each.
export const inkKey = (d: Drawing, i: number) => `${d.colours[i]?.toLowerCase() ?? ""}|${(Math.round(d.alphas[i] * 20) / 20).toFixed(2)}`;
// A part's points on the page: moved, turned and scaled as the editor's transform (Editor.tsx moveBy) does.
const placed = (p: PartIn, poly: P[]): P[] => {
  if (!p.turn && p.k === 1 && !p.at[0] && !p.at[1]) return poly;
  const c = Math.cos((p.turn * Math.PI) / 180) * p.k, s = Math.sin((p.turn * Math.PI) / 180) * p.k;
  return poly.map(([x, y]): P => [x * c - y * s + p.at[0], x * s + y * c + p.at[1]]);
};
const level = (p: PartIn) => !p.turn && p.k === 1;

const path = (polys: P[][]) => polys.map((poly) => "M" + poly.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join("L") + "Z").join("");
function slideOf(a: PartIn, b: PartIn, turn?: Turn): Slide | undefined {
  const da = a.drawing, db = b.drawing;
  if (da.labels.length !== db.labels.length) return undefined;
  // The polygons by what drew them (render.ts owners): each bond, ring circle, ellipse or symbol slides if its
  // polygons match point for point in the same colours, else fades. With no owners, the whole drawing is one.
  const ownersA = da.owners ?? da.polygons.map(() => 0), ownersB = db.owners ?? db.polygons.map(() => 0);
  const by = (owners: number[]) => { const m = new Map<number, number[]>(); owners.forEach((o, i) => m.set(o, [...(m.get(o) ?? []), i])); return m; };
  const inA = by(ownersA), inB = by(ownersB);
  const groups = new Map<string, { from: number[]; to: number[]; sizes: number[] }>(), out = new Map<string, P[][]>(), into = new Map<string, P[][]>();
  const push = (m: Map<string, P[][]>, key: string, poly: P[]) => m.set(key, [...(m.get(key) ?? []), poly]);
  for (const [owner, ib] of inB) {
    const ia = inA.get(owner) ?? [];
    const match = ia.length === ib.length && ib.every((j, k) => da.polygons[ia[k]].length === db.polygons[j].length && inkKey(da, ia[k]) === inkKey(db, j));
    if (!match) {
      for (const i of ia) push(out, inkKey(da, i), placed(a, da.polygons[i]));
      for (const j of ib) push(into, inkKey(db, j), placed(b, db.polygons[j]));
      continue;
    }
    ib.forEach((j, k) => {
      const key = inkKey(db, j);
      let g = groups.get(key);
      if (!g) groups.set(key, (g = { from: [], to: [], sizes: [] }));
      for (const [x, y] of placed(a, da.polygons[ia[k]])) g.from.push(x, y);
      for (const [x, y] of placed(b, db.polygons[j])) g.to.push(x, y);
      g.sizes.push(db.polygons[j].length);
    });
  }
  for (const [owner, ia] of inA) if (!inB.has(owner)) for (const i of ia) push(out, inkKey(da, i), placed(a, da.polygons[i]));
  // Labels slide by their place, level, in a structure neither turned nor scaled (moved is fine: the label moves with it).
  const labels: Slide["labels"] = [];
  for (let i = 0; i < db.labels.length; i++) {
    const la = da.labels[i], lb = db.labels[i];
    if (la.angle || lb.angle || !level(a) || !level(b)) return undefined;
    const same = la.text === lb.text && la.size === lb.size && la.colour === lb.colour && la.bold === lb.bold && la.italic === lb.italic && la.font === lb.font;
    labels.push({ label: lb, ...(same ? {} : { was: la }), from: [la.x + a.at[0], la.y + a.at[1]], to: [lb.x + b.at[0], lb.y + b.at[1]], turn });
  }
  const keys = [...new Set([...out.keys(), ...into.keys()])];
  return {
    kind: "slide", id: b.ids[0], labels,
    groups: [...groups].map(([key, g]) => ({ key, from: Float64Array.from(g.from), to: Float64Array.from(g.to), sizes: g.sizes, turn })),
    fades: keys.map((key) => ({ key, out: path(out.get(key) ?? []), in: path(into.get(key) ?? []) })),
  };
}

// The plan: for each structure where it ends, how it gets there. undefined when the two drawings do not have the same
// structures (atoms added or taken away), so the editor glides the slow way.
export function glidePlan(from: PartIn[], to: PartIn[], turn?: Turn): GlidePart[] | undefined {
  if (from.length !== to.length) return undefined;
  const was = new Map(from.map((p) => [p.ids.join(","), p]));
  const plan: GlidePart[] = [];
  for (const b of to) {
    const a = was.get(b.ids.join(","));
    if (!a) return undefined;
    plan.push(slideOf(a, b, turn && pageTurn(a, b, turn)) ?? { kind: "fade", id: b.ids[0], from: a, to: b });
  }
  return plan;
}

// The way round a turn goes on the page: the drawing's y runs down the page, so a turn's sign is the one that takes the
// old drawing's points nearest the new one's.
function pageTurn(a: PartIn, b: PartIn, turn: Turn): Turn {
  const pa = a.drawing.polygons.flatMap((poly) => placed(a, poly)).slice(0, 12), pb = b.drawing.polygons.flatMap((poly) => placed(b, poly)).slice(0, 12);
  const miss = (angle: number) => pa.reduce((sum, q, k) => { const r = round(q, turn.centre, angle); return sum + (pb[k] ? Math.hypot(r[0] - pb[k][0], r[1] - pb[k][1]) : 0); }, 0);
  return miss(turn.angle) <= miss(-turn.angle) ? turn : { ...turn, angle: -turn.angle };
}
const round = ([x, y]: readonly number[], [cx, cy]: P, angle: number): P => {
  const c = Math.cos(angle), s = Math.sin(angle);
  return [cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c];
};
// A point t of the way: on a straight line, or round a turn's centre with the difference from the new drawing added in.
const along = (fx: number, fy: number, tx: number, ty: number, t: number, turn?: Turn): P => {
  if (!turn) return [fx + (tx - fx) * t, fy + (ty - fy) * t];
  const [ex, ey] = round([fx, fy], turn.centre, turn.angle), [rx, ry] = round([fx, fy], turn.centre, turn.angle * t);
  return [rx + (tx - ex) * t, ry + (ty - ey) * t];
};
// A group's path t (0 to 1) of the way, in the editor's form (Editor.tsx toPath): at 0 and 1 the same shapes.
export function slidePath(g: Group, t: number): string {
  let out = "", k = 0;
  for (const n of g.sizes) {
    out += "M";
    for (let j = 0; j < n; j++, k += 2) {
      // Rounded to a hundredth of a pixel, as the editor's own paths are (toFixed(2) is several times slower).
      let x: number, y: number;
      if (g.turn) [x, y] = along(g.from[k], g.from[k + 1], g.to[k], g.to[k + 1], t, g.turn);
      else { x = g.from[k] + (g.to[k] - g.from[k]) * t; y = g.from[k + 1] + (g.to[k + 1] - g.from[k + 1]) * t; }
      out += (j ? "L" : "") + Math.round(x * 100) / 100 + " " + Math.round(y * 100) / 100;
    }
    out += "Z";
  }
  return out;
}
export const slideAt = (from: P, to: P, t: number, turn?: Turn): P => along(from[0], from[1], to[0], to[1], t, turn);
