// Drawings for the library's illustration sets, written as SVG path data (a 100-unit box, y down) and turned into
// Octet's pen curves and lines here: each subpath one curve (lines that meet end to end one curve), every arc and
// quadratic made a cubic Bézier. Every drawing in these sets is Octet's own, drawn for this file; nothing comes from
// another program's files.
import { item, join, LIQUID, LIQUID_LIGHT, reverse } from "./lab.mjs";

// The tints a drawing may fill with: the Lab group's two at the logo's hue. Only small parts are filled (a liquid, an
// organelle, a head group), so a drawing still reads on a dark page, where its lines are light.
export const TINT = { blue: LIQUID, light: LIQUID_LIGHT };

// SVG path data as subpaths of points in Octet's curve form ({ at, c1, c2 }), still in the drawing's units, y down.
export function subpaths(d) {
  const tokens = d.match(/[a-zA-Z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?/g) ?? [];
  const out = [];
  let i = 0, cmd = "", cur = [0, 0], start = [0, 0], last = null, prev = "", path = null;
  const num = () => Number(tokens[i++]);
  const more = () => i < tokens.length && !/^[a-zA-Z]$/.test(tokens[i]);
  const begin = (p) => { path = { points: [{ at: p }], closed: false }; out.push(path); start = p; };
  const cubic = (c1, c2, p) => { path.points[path.points.length - 1].c2 = c1; path.points.push({ at: p, c1: c2 }); last = c2; };
  const lineTo = (p) => { path.points.push({ at: p }); last = null; };
  while (i < tokens.length) {
    if (/^[a-zA-Z]$/.test(tokens[i])) cmd = tokens[i++];
    const rel = cmd === cmd.toLowerCase(), C = cmd.toUpperCase(), o = rel ? cur : [0, 0];
    const pt = () => { const x = num(), y = num(); return [o[0] + x, o[1] + y]; };
    if (C === "M") { const p = pt(); begin(p); cur = p; cmd = rel ? "l" : "L"; prev = "M"; continue; }
    if (C === "Z") { path.closed = true; const f = path.points[0].at, l = path.points[path.points.length - 1];
      if (path.points.length > 1 && Math.hypot(l.at[0] - f[0], l.at[1] - f[1]) < 1e-6) { path.points[0].c1 = l.c1; path.points.pop(); }
      cur = start; last = null; prev = "Z"; if (more()) cmd = "L"; continue; }
    if (C === "L") { const p = pt(); lineTo(p); cur = p; }
    else if (C === "H") { const x = num(); const p = [rel ? cur[0] + x : x, cur[1]]; lineTo(p); cur = p; }
    else if (C === "V") { const y = num(); const p = [cur[0], rel ? cur[1] + y : y]; lineTo(p); cur = p; }
    else if (C === "C") { const a = pt(), b = pt(), p = pt(); cubic(a, b, p); cur = p; }
    else if (C === "S") { const a = last && "CS".includes(prev) ? [2 * cur[0] - last[0], 2 * cur[1] - last[1]] : cur, b = pt(), p = pt(); cubic(a, b, p); cur = p; }
    else if (C === "Q") { const q = pt(), p = pt(); cubic([cur[0] + (2 / 3) * (q[0] - cur[0]), cur[1] + (2 / 3) * (q[1] - cur[1])], [p[0] + (2 / 3) * (q[0] - p[0]), p[1] + (2 / 3) * (q[1] - p[1])], p); cur = p; }
    else if (C === "A") {
      const rx = num(), ry = num(), rot = num(), large = num(), sweep = num(), p = pt();
      for (const [a, b, q] of arc(cur, rx, ry, rot, large, sweep, p)) cubic(a, b, q);
      cur = p;
    } else throw new Error(`path command ${cmd}`);
    prev = C;
  }
  return out;
}
// An elliptical arc (SVG's endpoint form) as cubic Béziers of a quarter turn or less.
function arc(p0, rx, ry, rotDeg, large, sweep, p1) {
  const phi = (rotDeg * Math.PI) / 180, cs = Math.cos(phi), sn = Math.sin(phi);
  const dx = (p0[0] - p1[0]) / 2, dy = (p0[1] - p1[1]) / 2, x1 = cs * dx + sn * dy, y1 = -sn * dx + cs * dy;
  rx = Math.abs(rx); ry = Math.abs(ry);
  const lam = (x1 * x1) / (rx * rx) + (y1 * y1) / (ry * ry);
  if (lam > 1) { rx *= Math.sqrt(lam); ry *= Math.sqrt(lam); }
  const sign = large === sweep ? -1 : 1, num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1;
  const k = sign * Math.sqrt(Math.max(0, num / (rx * rx * y1 * y1 + ry * ry * x1 * x1)));
  const cxp = (k * rx * y1) / ry, cyp = (-k * ry * x1) / rx, cx = cs * cxp - sn * cyp + (p0[0] + p1[0]) / 2, cy = sn * cxp + cs * cyp + (p0[1] + p1[1]) / 2;
  const ang = (ux, uy, vx, vy) => Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy);
  const t0 = ang(1, 0, (x1 - cxp) / rx, (y1 - cyp) / ry);
  let dt = ang((x1 - cxp) / rx, (y1 - cyp) / ry, (-x1 - cxp) / rx, (-y1 - cyp) / ry);
  if (!sweep && dt > 0) dt -= 2 * Math.PI; else if (sweep && dt < 0) dt += 2 * Math.PI;
  const n = Math.max(1, Math.ceil(Math.abs(dt) / (Math.PI / 2) - 1e-9)), step = dt / n, kk = (4 / 3) * Math.tan(step / 4);
  const at = (t) => [cx + rx * Math.cos(t) * cs - ry * Math.sin(t) * sn, cy + rx * Math.cos(t) * sn + ry * Math.sin(t) * cs];
  const d = (t) => [-rx * Math.sin(t) * cs - ry * Math.cos(t) * sn, -rx * Math.sin(t) * sn + ry * Math.cos(t) * cs];
  const out = [];
  for (let j = 0; j < n; j++) {
    const a = t0 + j * step, b = a + step, pa = at(a), pb = at(b), da = d(a), db = d(b);
    out.push([[pa[0] + kk * da[0], pa[1] + kk * da[1]], [pb[0] - kk * db[0], pb[1] - kk * db[1]], j === n - 1 ? p1 : pb]);
  }
  return out;
}

// Shorthands for a drawing's parts: [kind, SVG path data, options]. ink: lines at the document's width (open or
// closed as the path is). fill: a closed area in a tint, behind the lines. solid: a closed area in the ink colour.
// A part marked fine is left out of the 20 px icon (fine parts would run together there).
export const ink = (d, more = {}) => ["ink", d, more];
export const fill = (d, tint = "blue", more = {}) => ["fill", d, { ...more, tint }];
export const solid = (d, more = {}) => ["solid", d, more];
export const fine = (part) => [part[0], part[1], { ...part[2], fine: true }];
// A membrane: a line or curve drawn as a lipid bilayer (Octet's Membrane style), its lipids the same size however long it is.
export const membrane = (d) => ["ink", d, { style: "membrane" }];
// Common SVG shapes as path data.
export const circle = (cx, cy, r) => `M${cx + r} ${cy}A${r} ${r} 0 1 1 ${cx - r} ${cy}A${r} ${r} 0 1 1 ${cx + r} ${cy}Z`;
export const ellipse = (cx, cy, rx, ry) => `M${cx + rx} ${cy}A${rx} ${ry} 0 1 1 ${cx - rx} ${cy}A${rx} ${ry} 0 1 1 ${cx + rx} ${cy}Z`;
export const rect = (x, y, w, h, r = 0) => (r ? `M${x + r} ${y}H${x + w - r}A${r} ${r} 0 0 1 ${x + w} ${y + r}V${y + h - r}A${r} ${r} 0 0 1 ${x + w - r} ${y + h}H${x + r}A${r} ${r} 0 0 1 ${x} ${y + h - r}V${y + r}A${r} ${r} 0 0 1 ${x + r} ${y}Z` : `M${x} ${y}H${x + w}V${y + h}H${x}Z`);
export const seg = (x0, y0, x1, y1) => `M${x0} ${y0}L${x1} ${y1}`;

// A curve with its stretch from point i to the next cut at its middle (de Casteljau): the new point comes after i.
const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
function halve(ps, i) {
  const a = ps[i], b = ps[i + 1];
  if (!a.c2 && !b.c1) return [...ps.slice(0, i + 1), { at: mid(a.at, b.at) }, ...ps.slice(i + 1)];
  const p1 = a.c2 ?? a.at, p2 = b.c1 ?? b.at, q0 = mid(a.at, p1), q1 = mid(p1, p2), q2 = mid(p2, b.at), r0 = mid(q0, q1), r1 = mid(q1, q2);
  return [...ps.slice(0, i), { ...a, c2: q0 }, { at: mid(r0, r1), c1: r0, c2: r1 }, { ...b, c1: q2 }, ...ps.slice(i + 2)];
}

// A drawing as a library item: its parts in order (fills first is up to the drawing), size the larger side of its
// box in bond lengths, or { per } the drawing's units in one bond length (so a set's items keep their sizes to each
// other). Lines take the document's width; fills are closed curves in one of the tints.
export function art(name, also, size, parts) {
  let all = parts.flatMap(([kind, d, more]) => subpaths(d).map((p) => [kind, p, more]));
  // Open lines that meet end to end (two ends at a point, no more) are one line, so the join turns as a line does
  // (a flask's neck into its sphere, a leg at its knee) where two ends side by side left a notch.
  const same = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-6, ends = (x) => [x[1].points[0].at, x[1].points[x[1].points.length - 1].at];
  const alike = (a, b) => a !== b && JSON.stringify(a[2]) === JSON.stringify(b[2]);
  for (let joined = true; joined; ) {
    joined = false;
    const open = all.filter((x) => x[0] === "ink" && !x[1].closed), at = open.flatMap(ends);
    for (const a of open) for (const b of open) {
      const p = !joined && alike(a, b) && ends(a).find((q) => ends(b).some((r) => same(q, r)) && at.filter((r) => same(q, r)).length === 2);
      if (!p) continue;
      a[1].points = join(same(ends(a)[1], p) ? a[1].points : reverse(a[1].points), same(ends(b)[0], p) ? b[1].points : reverse(b[1].points));
      all = all.filter((x) => x !== b);
      joined = true;
    }
  }
  // A line that comes back to its start (three points or more) is closed, so it has no ends there.
  const open = all.filter((x) => x[0] === "ink" && !x[1].closed);
  for (const x of open) {
    const q = x[1].points, [s, e] = ends(x), l = q[q.length - 1];
    if (q.length > 3 && same(s, e) && open.flatMap(ends).filter((p) => same(p, s)).length === 2) x[1] = { points: [{ at: q[0].at, ...(l.c1 ? { c1: l.c1 } : {}), ...(q[0].c2 ? { c2: q[0].c2 } : {}) }, ...q.slice(1, -1)], closed: true };
  }
  // A drawing of one line is drawn as two that meet (a group of one object does not come back from a CDXML file, and
  // every drawing is one group), cut in the middle of a stretch, where the two halves run on as one line. A line that
  // comes back to its start starts there too, so neither join is at a corner.
  if (all.length === 1 && all[0][0] === "ink" && !all[0][2].style) {
    const [kind, { points, closed }, more] = all[0];
    const loop = closed ? [...points, { ...points[0], c2: undefined }] : same(...ends(all[0])) ? points : null, r = loop && halve(loop, 0);
    const line = r ? [r[1], ...r.slice(2, -1), { ...r[r.length - 1], c2: r[0].c2 }, { at: r[1].at, c1: r[1].c1 }] : points;
    const m = Math.floor((line.length - 1) / 2), cut = halve(line, m);
    const half = (ps) => ps.map((q, i) => ({ at: q.at, ...(i > 0 && q.c1 ? { c1: q.c1 } : {}), ...(i < ps.length - 1 && q.c2 ? { c2: q.c2 } : {}) }));
    all = [[kind, { points: half(cut.slice(0, m + 2)), closed: false }, more], [kind, { points: half(cut.slice(m + 1)), closed: false }, more]];
  }
  const xs = all.flatMap(([, p]) => p.points.map((q) => q.at[0])), ys = all.flatMap(([, p]) => p.points.map((q) => q.at[1]));
  const k = typeof size === "object" ? 1 / size.per : size / Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
  // Kept to 0.001 bond length (item rounds them), as a handle a few hundredths long needs: at 0.01 the handles either
  // side of a smooth point no longer lined up, and a smooth curve drew with a kink at every point.
  const map = (q) => [q[0] * k, -q[1] * k];
  const conv = (p) => p.points.map((q) => ({ at: map(q.at), ...(q.c1 ? { c1: map(q.c1) } : {}), ...(q.c2 ? { c2: map(q.c2) } : {}) }));
  return item(name, also, all.map(([kind, p, more]) => {
    const ps = conv(p);
    // A closed curve runs from its last point back to its first (the last's c2 and the first's c1 shape that stretch).
    if (kind === "fill") return ["fill", ps, { fill: "solid", colour: TINT[more.tint] ?? more.tint }];
    if (kind === "solid") return ["fill", ps, { fill: "solid" }];
    const own = more.style ? { style: more.style } : {};
    if (!p.closed && ps.length === 2 && !ps[0].c2 && !ps[1].c1) return ["line", ps, own, more.fine];
    return [p.closed ? "closed" : "open", ps, own, more.fine];
  }));
}
