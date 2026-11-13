// The library's Symbols set: shapes the Shape tool does not draw (stars, polygons, a burst, a tick and a cross, a bolt,
// the sex symbols, a target) and safety signs (warning triangles, the radiation trefoil and GHS hazard diamonds), in
// the Lab group's line style (art.mjs path data, 40 units to a bond length, y down). Each is worked out here from
// simple geometry.
import { PICTOGRAMS } from "../../src/ghs.ts";
import { art, circle, fine, ink, solid } from "./art.mjs";

const PER = { per: 40 };
const f = (v) => Math.round(v * 100) / 100;
const deg = Math.PI / 180;
const pt = (r, a) => `${f(r * Math.cos(a * deg))} ${f(r * Math.sin(a * deg))}`;
// A closed polygon through points at radii rs (in turn) and even angles, the first straight up.
const polygon = (n, rs, start = -90) => `M${Array.from({ length: n }, (_, k) => pt(rs[k % rs.length], start + (360 / n) * k)).join("L")}Z`;

const star = () => art("Star", "five-pointed star, shape", PER, [ink(polygon(10, [40, 16]))]);
const hexagon = () => art("Hexagon", "polygon, shape", PER, [ink(polygon(6, [36], -90))]);
const octagon = () => art("Octagon", "polygon, stop, shape", PER, [ink(polygon(8, [36], -112.5))]);
const pentagon = () => art("Pentagon", "polygon, shape", PER, [ink(polygon(5, [36]))]);
const burst = () => art("Burst", "starburst, explosion, flash, shape", PER, [ink(polygon(24, [40, 28, 36, 26]))]);
const tick = () => art("Tick mark", "check mark, tick, correct, yes", PER, [ink(`M-34 0L-22 -12L-8 2L22 -30L34 -18L-8 24Z`)]);
const cross = () => art("Cross", "X, wrong, no", PER, [ink(`M-28 -36L0 -8L28 -36L36 -28L8 0L36 28L28 36L0 8L-28 36L-36 28L-8 0L-36 -28Z`)]);
const bolt = () => art("Lightning bolt", "electricity, high voltage, energy, flash", PER, [ink(`M6 -44L-18 4L-2 4L-10 44L20 -8L4 -8L14 -44Z`)]);
const male = () => art("Male symbol", "male, Mars, ♂", PER, [ink(circle(-8, 8, 22)), ink(`M8 -8L30 -30M14 -30L30 -30L30 -14`)]);
const female = () => art("Female symbol", "female, Venus, ♀", PER, [ink(circle(0, -10, 22)), ink(`M0 12L0 42M-12 30L12 30`)]);
const target = () => art("Target", "crosshair, bullseye, aim", PER, [ink(circle(0, 0, 36)), ink(circle(0, 0, 18)), ink(`M0 -44L0 -26M0 26L0 44M-44 0L-26 0M26 0L44 0`), solid(circle(0, 0, 3))]);

// Warning triangle with rounded corners, and what it holds.
const triangle = (inner) => [ink(`M-6 -40Q0 -48 6 -40L44 26Q48 34 40 34L-40 34Q-48 34 -44 26Z`), ...inner];
const warning = () => art("Warning sign", "caution, danger, exclamation, hazard", PER, triangle([solid(`M-3 -16L3 -16L2 12L-2 12Z`), solid(circle(0, 21, 3))]));
const highVoltage = () => art("High voltage sign", "electrical hazard, danger, lightning", PER, triangle([solid(`M4 -18L-10 8L-1 8L-6 26L10 -2L1 -2L7 -18Z`)]));
// Radiation trefoil: a circle in the middle and three blades, each a sixth of a ring, 120° apart.
function radiation() {
  const r0 = 8, r1 = 14, r2 = 40, blade = (a) => `M${pt(r1, a - 30)}L${pt(r2, a - 30)}A${r2} ${r2} 0 0 1 ${pt(r2, a + 30)}L${pt(r1, a + 30)}A${r1} ${r1} 0 0 0 ${pt(r1, a - 30)}Z`;
  return art("Radiation symbol", "trefoil, radioactive, ionising radiation, hazard", PER, [solid(circle(0, 0, r0)), ...[-90, 30, 150].map((a) => solid(blade(a))), ink(circle(0, 0, 46))]);
}
// GHS hazard diamonds (a square on its point) and their pictograms, which the Properties panel draws too (src/ghs.ts).
const ghs = (code, also) => art(`${PICTOGRAMS[code].name} (${code})`, `${also}, GHS, hazard pictogram`, PER,
  [ink(`M0 -46L46 0L0 46L-46 0Z`), ...PICTOGRAMS[code].parts.map(([kind, d]) => (kind === "ink" ? ink(d) : solid(d)))]);
const ghsFlame = () => ghs("GHS02", "flame, flammable");
const ghsOxidiser = () => ghs("GHS03", "flame over circle, oxidiser, oxidizer");
const ghsGas = () => ghs("GHS04", "gas cylinder, compressed gas");
const ghsHarmful = () => ghs("GHS07", "exclamation mark, irritant, harmful");

export const SYMBOLS = [star(), pentagon(), hexagon(), octagon(), burst(), tick(), cross(), bolt(), male(), female(), target(), warning(), highVoltage(), radiation(),
  ghsFlame(), ghsOxidiser(), ghsGas(), ghsHarmful()];
