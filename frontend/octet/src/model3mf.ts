// File > More Formats > Export 3MF…: structures as a ball-and-stick model to 3D print (ChemDraw's 3D Manufacturing
// Format for Printing, Ball and Stick). This makes the model part of the 3MF file (3D/3dmodel.model; export.rs packs
// it), in millimetres: a ball for each atom and a stick for each bond, each a closed surface whose triangles face out.
// 3MF fills overlapping surfaces as one solid (its positive fill rule), so each structure prints as one piece.
// A structure drawn flat takes 3D Clean Up's shape (the drawing does not change); one in 3D already keeps its shape.
// The drawing's x, y and z (nearer the viewer) stay the model's, so it lies on the printer's bed as drawn and each
// stereocentre keeps its hand. A bond is 20 mm (about 13 mm to the ångström), less when the model would be more than
// 150 mm on a side.
import { clean3d, crossV, lenV, MOST_3D, RADIUS } from "./clean3d.ts";
import { fragments } from "./edit.ts";
import { HBOND, type Mol } from "./render.ts";

type V = [number, number, number];
const BOND_MM = 20, MOST_MM = 150;

// The model, or undefined for a drawing with no atoms. A hydrogen bond has no stick.
export function model3mf(m: Mol): string | undefined {
  if (!m.atoms.length) return undefined;
  if (m.atoms.length > MOST_3D) throw new Error(`Octet cannot export more than ${MOST_3D} atoms as a 3D model.`);
  const flat = (g: number[]) => g.every((i) => !m.atoms[i].location[2]);
  const p = fragments(m).reduce((d, g) => (g.length > 1 && flat(g) ? clean3d(d, g) : d), m).atoms.map((a): V => [a.location[0], a.location[1], a.location[2] ?? 0]);
  const sticks = m.bonds.filter((b) => b.type !== HBOND).map((b) => b.atoms);
  const towards = (i: number, j: number): V => [p[j][0] - p[i][0], p[j][1] - p[i][1], p[j][2] - p[i][2]];
  // Sizes in bond lengths (the drawing's median bond): a stick's radius, and a ball's, which grows with its element's
  // covalent radius (carbon 0.27, hydrogen 0.18).
  const lengths = sticks.map(([i, j]) => lenV(towards(i, j))).sort((x, y) => x - y), unit = lengths[lengths.length >> 1] || 1;
  const ball = m.atoms.map((a) => (0.12 + 0.2 * (RADIUS[a.label] ?? RADIUS.C)) * unit), stick = 0.12 * unit;
  // Millimetres, from the model's corner nearest the origin.
  const lo = [0, 1, 2].map((x) => Math.min(...p.map((q, i) => q[x] - ball[i]))), hi = [0, 1, 2].map((x) => Math.max(...p.map((q, i) => q[x] + ball[i])));
  const mm = Math.min(BOND_MM / unit, MOST_MM / Math.max(...hi.map((h, x) => h - lo[x])));
  const vertices: string[] = [], triangles: string[] = [];
  const vertex = (q: V) => vertices.push(`<vertex x="${+((q[0] - lo[0]) * mm).toFixed(3)}" y="${+((q[1] - lo[1]) * mm).toFixed(3)}" z="${+((q[2] - lo[2]) * mm).toFixed(3)}"/>`) - 1;
  const triangle = (a: number, b: number, c: number) => triangles.push(`<triangle v1="${a}" v2="${b}" v3="${c}"/>`);
  // A closed surface turned about the line from c along u (a unit vector), in n steps: its profile runs from one pole
  // to the other, each point a height along u and a radius (0 at a pole).
  const lathe = (c: V, u: V, profile: [number, number][], n: number) => {
    const s = crossV(u, Math.abs(u[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]), e1 = s.map((x) => x / lenV(s)) as V, e2 = crossV(u, e1);
    const rings = profile.map(([h, r]) => Array.from({ length: r ? n : 1 }, (_, j) => {
      const a = (2 * Math.PI * j) / n, at = (x: number) => c[x] + h * u[x] + r * (Math.cos(a) * e1[x] + Math.sin(a) * e2[x]);
      return vertex([at(0), at(1), at(2)]);
    }));
    for (let i = 1; i < rings.length; i++) for (let j = 0; j < n; j++) {
      const [a, b] = [rings[i - 1], rings[i]], at = (ring: number[], k: number) => ring[k % ring.length];
      if (b.length > 1) triangle(at(a, j), at(b, j), at(b, j + 1));
      if (a.length > 1) triangle(at(a, j), at(b, j + 1), at(a, j + 1));
    }
  };
  p.forEach((c, i) => lathe(c, [0, 0, 1], Array.from({ length: 13 }, (_, k) => [ball[i] * Math.cos((Math.PI * k) / 12), k % 12 ? ball[i] * Math.sin((Math.PI * k) / 12) : 0]), 24));
  for (const [i, j] of sticks) {
    const v = towards(i, j), d = lenV(v);
    if (d > 1e-6 * unit) lathe(p[i], v.map((x) => x / d) as V, [[d, 0], [d, stick], [0, stick], [0, 0]], 16);
  }
  return `<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-GB" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
<resources>
<object id="1" type="model">
<mesh>
<vertices>
${vertices.join("\n")}
</vertices>
<triangles>
${triangles.join("\n")}
</triangles>
</mesh>
</object>
</resources>
<build>
<item objectid="1"/>
</build>
</model>
`;
}
