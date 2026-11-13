// More of the Lab group: flasks, funnels, condensers, adapters and apparatus, drawn in the Lab group's line style
// (art.mjs path data, 40 units to a bond length, y down). Each shape is worked out here from simple geometry.
import { art, circle, ellipse, fill, fine, ink, rect, seg, solid } from "./art.mjs";

const PER = { per: 40 };
const LIP = 3.6; // the outward turn at the top of an open neck, as lab.mjs's
const f = (v) => Math.round(v * 100) / 100;
const P = (x, y) => `${f(x)} ${f(y)}`;
const deg = Math.PI / 180;

// A neck's wall from (x, y0) up to top, turning out at its lip (dir 1 to the right, -1 to the left).
const wallUp = (x, y0, top, dir) => `M${P(x, y0)}L${P(x, top + LIP)}Q${P(x, top)} ${P(x + dir * LIP, top)}`;
// A neck at angle a (degrees from straight up, positive to the right) from a sphere of radius R at (cx, cy): its two
// walls, half-width w, from the sphere out to length s1 along its axis, each ending in its lip.
function sideNeck(cx, cy, R, a, w, s1) {
  const u = [Math.sin(a * deg), -Math.cos(a * deg)], n = [Math.cos(a * deg), Math.sin(a * deg)], s0 = Math.sqrt(R * R - w * w);
  const at = (s, t) => [cx + s * u[0] + t * n[0], cy + s * u[1] + t * n[1]];
  const wall = (t) => { const a0 = at(s0, t), a1 = at(s1 - LIP, t), c = at(s1, t), e = at(s1, t + Math.sign(t) * LIP); return `M${P(...a0)}L${P(...a1)}Q${P(...c)} ${P(...e)}`; };
  return { left: wall(-w), right: wall(w), joinLeft: at(s0, -w), joinRight: at(s0, w) };
}
// A round flask's body with necks at the given angles: the sphere's outline in arcs between the necks, and the
// necks' walls. The liquid fills the sphere below level (y, from its centre).
function roundFlask(R, necks, level) {
  const parts = necks.map(([a, w, len]) => sideNeck(0, 0, R, a, w, len)).sort((p, q) => p.joinLeft[0] - q.joinLeft[0]);
  const arcTo = (p, large) => `A${R} ${R} 0 ${large} 1 ${P(...p)}`;
  // Round the bottom: from the leftmost neck's left wall, the long way round (anticlockwise on screen), to the
  // rightmost neck's right wall; then between each pair of necks over the top.
  const first = parts[0], last = parts[parts.length - 1];
  const out = [`M${P(...first.joinLeft)}A${R} ${R} 0 1 0 ${P(...last.joinRight)}`];
  for (let k = 0; k + 1 < parts.length; k++) out.push(`M${P(...parts[k].joinRight)}${arcTo(parts[k + 1].joinLeft, 0)}`);
  const walls = parts.flatMap((p) => [p.left, p.right]);
  const x = Math.sqrt(R * R - level * level);
  return { glass: [...out, ...walls].join(""), liquid: `M${P(-x, level)}A${R} ${R} 0 ${level < 0 ? 1 : 0} 0 ${P(x, level)}Z` };
}

function twoNeck() {
  const b = roundFlask(38, [[0, 8, 72], [42, 7, 66]], 12);
  return art("Two-neck flask", "two-necked round-bottom flask", PER, [fill(b.liquid), ink(b.glass)]);
}
function threeNeck() {
  const b = roundFlask(40, [[-44, 7, 68], [0, 8, 76], [44, 7, 68]], 14);
  return art("Three-neck flask", "three-necked round-bottom flask", PER, [fill(b.liquid), ink(b.glass)]);
}
// Pear-shaped flask: a teardrop narrowing to a pointed bottom.
function pearFlask() {
  const glass = `M-7 -46L-7 -26C-7 -18 -30 -6 -26 14C-23 30 -6 38 0 40C6 38 23 30 26 14C30 -6 7 -18 7 -26L7 -46`;
  return art("Pear-shaped flask", "pear flask, rotary evaporator", PER, [
    fill(`M-24.2 16C-20 30 -6 37 0 39C6 37 20 30 24.2 16Z`), ink(`${wallUp(-7, -26, -50, -1)}${glass.replace("M-7 -46L-7 -26", "M-7 -26").replace(/L7 -46$/, "")}${wallUp(7, -26, -50, 1)}`),
  ]);
}
// Volumetric flask: a long narrow neck with its fill mark, a bulb and a flat bottom.
function volumetricFlask() {
  const half = (s) => `M0 40L${s * 22} 40Q${s * 30} 40 ${s * 30} 30C${s * 30} 12 ${s * 4.5} 6 ${s * 4.5} -8L${s * 4.5} ${-84 + LIP}Q${s * 4.5} -84 ${s * (4.5 + LIP)} -84`;
  return art("Volumetric flask", "graduated flask, standard solution", PER, [
    fill(`M-29.2 22C-29.8 26 -30 28 -30 30Q-30 40 -22 40L22 40Q30 40 30 30C30 28 29.8 26 29.2 22Z`), ink(half(-1) + half(1)), fine(ink(seg(-6.5, -56, 6.5, -56))),
  ]);
}
// Büchner (filter) flask: a conical flask with a hose barb on its neck.
function buchnerFlask() {
  const half = (s) => `M0 40L${s * 30} 40Q${s * 36} 40 ${s * 34} 34L${s * 10} -24L${s * 10} ${-52 + LIP}Q${s * 10} -52 ${s * (10 + LIP)} -52`;
  return art("Büchner flask", "filter flask, suction flask, vacuum filtration", PER, [
    fill(`M-28.6 25L28.6 25L34 34Q36 40 30 40L-30 40Q-36 40 -34 34Z`), ink(half(-1) + half(1)),
    ink(`M10 -40L24 -40L24 -37L28 -36L28 -32L24 -31L24 -28L10 -28`),
  ]);
}
// Büchner funnel: a wide cylinder with a perforated plate, a cone and a stem.
function buchnerFunnel() {
  return art("Büchner funnel", "filter funnel, vacuum filtration, porcelain", PER, [
    ink(`M-30 -32L-30 -2Q-30 4 -24 8L-6 18L-6 46M30 -32L30 -2Q30 4 24 8L6 18L6 46`),
    ink(`M-30 -32L30 -32`), fine(ink(`M-30 -8L30 -8`)), ...[-20, -10, 0, 10, 20].map((x) => fine(ink(`M${x} -11L${x} -5`))),
  ]);
}
// Filter funnel: a cone with a long stem.
function filterFunnel() {
  return art("Filter funnel", "funnel, gravity filtration", PER, [
    ink(`M-30 -36L${-30 - 1} ${-36 - LIP}M-30 -36L-4 4L-4 44M30 -36L${30 + 1} ${-36 - LIP}M30 -36L4 4L4 44`),
    
  ]);
}
// Dropping funnel: a cylinder with a pressure-equalising arm, a tap and a stem with a joint.
function droppingFunnel() {
  return art("Dropping funnel", "addition funnel, pressure-equalising", PER, [
    fill(`M-12 -6L12 -6L12 18Q12 26 4 30L-4 30Q-12 26 -12 18Z`, "light"),
    ink(`${wallUp(-5, -52, -62, -1)}M-5 -52Q-12 -48 -12 -40L-12 18Q-12 26 -4 30L-4 50M5 -52Q12 -48 12 -40L12 18Q12 26 4 30L4 50${wallUp(5, -52, -62, 1)}`),
    ink(`M12 -44L22 -44L22 58L4 58M12 -38L18 -38L18 54L4 54`),
    ink(rect(-12, 36, 24, 6, 2)), ink(`M-12 39L-16 39`),
    ink(`M-4 50L-4 66L-6 76M4 50L4 66L6 76`),
  ]);
}
// A hose nozzle at height y on a jacket's wall x across from the middle (s 1 on the right, -1 on the left).
export const nozzle = (x, y, s) => `M${s * x} ${y - 4}L${s * (x + 9)} ${y - 4}L${s * (x + 9)} ${y - 2}L${s * (x + 13)} ${y - 1.5}L${s * (x + 13)} ${y + 1.5}L${s * (x + 9)} ${y + 2}L${s * (x + 9)} ${y + 4}L${s * x} ${y + 4}`;
// Liebig condenser: an inner tube in a water jacket with two hose nozzles.
function liebigCondenser() {
  return art("Liebig condenser", "condenser, distillation, water jacket", PER, [
        ink(`M-4 -78L-4 82M4 -78L4 82`),
    ink(`M-4 -60L-11 -54L-11 54L-4 60M4 -60L11 -54L11 54L4 60`),
    ink(nozzle(11, -40, 1)), ink(nozzle(11, 40, -1)),
    ink(`M-4 -78L-7 -82M4 -78L7 -82`),
  ]);
}
// Vigreux column: a tube with rows of indentations pointing in.
function vigreux() {
  const dents = [];
  for (let y = -48; y <= 48; y += 16) dents.push(`M-7 ${y - 4}L-2 ${y}L-7 ${y + 4}`, `M7 ${y + 4}L2 ${y + 8}L7 ${y + 12}`);
  return art("Vigreux column", "fractional distillation, fractionating column", PER, [
    ink(`${wallUp(-7, 60, -66, -1)}${wallUp(7, 60, -66, 1)}M-7 60L-5 74M7 60L5 74`), ...dents.map((d) => fine(ink(d))),
  ]);
}
// Dean-Stark trap: a vertical tube with a graduated trap, a side arm up to the condenser and a tap at the foot.
function deanStark() {
  const marks = [-10, 0, 10, 20].map((y) => fine(ink(seg(22, y, 28, y))));
  return art("Dean-Stark trap", "Dean-Stark apparatus, azeotropic distillation, water removal", PER, [
    fill(`M18 8L32 8L32 32Q32 38 25 38Q18 38 18 32Z`, "light"), fill(`M18 26L32 26L32 32Q32 38 25 38Q18 38 18 32Z`),
    ink(`${wallUp(-6, 60, -60, -1)}M6 -60L6 -36L32 -36L32 32Q32 38 25 38Q18 38 18 32L18 -24L6 -24L6 60`),
    ink(`M6 -60Q6 -64 ${6 + LIP} -64M-6 60L-4 72M6 60L4 72`),
    ink(`M25 38L25 46`), ink(rect(20, 46, 10, 5, 1.5)), ink(`M25 51L25 58`),
    ...marks,
  ]);
}
// Distillation head: a vertical joint for the thermometer, a sloping side arm to the condenser, and a joint below.
function distillationHead() {
  const a = 70 * deg, ux = Math.sin(a), uy = Math.cos(a);
  return art("Distillation head", "still head, short path, three-way adapter", PER, [
    ink(`${wallUp(-7, 44, -50, -1)}${wallUp(7, -20, -50, 1)}M7 -6L7 44`),
    ink(`M7 -20L${P(7 + 56 * ux, -20 + 56 * uy)}M7 -6L${P(7 + 52 * ux, -6 + 52 * uy)}`),
    ink(`M-7 44L-5 56M7 44L5 56`),
  ]);
}
// Claisen adapter: one joint below, two above (one straight, one offset), as on a reflux with addition.
function claisen() {
  return art("Claisen adapter", "two-neck adapter", PER, [
    ink(`M-6 48L-6 0Q-6 -10 -16 -14L-16 ${-52 + LIP}Q-16 -52 ${-16 - LIP} -52M6 48L6 -6Q6 -14 14 -16L14 ${-52 + LIP}Q14 -52 ${14 + LIP} -52`),
    ink(`M-4 -16Q2 -18 2 -24L2 ${-52 + LIP}Q2 -52 ${2 + LIP} -52M-4 -16L-4 ${-52 + LIP}Q-4 -52 ${-4 - LIP} -52`),
    ink(`M-6 48L-4 60M6 48L4 60`),
  ]);
}
// Receiver adapter: a bent tube from the condenser down to the receiving flask, with a vacuum nipple.
function receiverAdapter() {
  return art("Receiver adapter", "vacuum adapter, distillation, bent adapter", PER, [
    ink(`M-40 -40L-12 -12Q-6 -6 -6 4L-6 40M-30 -50L-2 -22Q6 -14 6 0L6 40`),
    ink(`M-40 -40L${P(-43, -43)}M-30 -50L${P(-27, -53)}`),
    ink(`M6 -8L20 -8L20 -6L25 -5L25 -1L20 0L20 2L6 2`),
    ink(`M-6 40L-4 52M6 40L4 52`),
  ]);
}
// Thermometer: a long tube, a bulb and its liquid.
function thermometer() {
  const marks = [-60, -48, -36, -24, -12, 0, 12, 24].map((y, k) => fine(ink(seg(3.5, y, k % 2 ? 6 : 8, y))));
  return art("Thermometer", "temperature", PER, [
    fill(`M-1.5 -20L1.5 -20L1.5 52L-1.5 52Z`), fill(circle(0, 58, 6)),
    ink(`M-3.5 53.2L-3.5 -76Q-3.5 -80 0 -80Q3.5 -80 3.5 -76L3.5 53.2A7 7 0 1 1 -3.5 53.2Z`), ...marks,
  ]);
}
// Measuring cylinder: a tall tube with a spout, a foot and its marks.
function measuringCylinder() {
  const marks = [-50, -40, -30, -20, -10, 0, 10, 20, 30].map((y, k) => fine(ink(seg(-10, y, k % 2 ? -4 : 0, y))));
  return art("Measuring cylinder", "graduated cylinder", PER, [
    fill(`M-12 6L12 6L12 44L-12 44Z`),
    ink(`M-15 -64Q-12 -62 -12 -58L-12 44M12 -62L12 44`), ink(`M12 -62Q12 -64 ${12 + LIP} -64`),
    ink(`M-22 44L22 44L22 52L-22 52Z`), ...marks,
  ]);
}
// Burette: a long graduated tube, a tap and a tip.
function burette() {
  const marks = [];
  for (let y = -70; y <= 40; y += 10) marks.push(fine(ink(seg(-5, y, (y / 10) % 2 ? -1.5 : 1, y))));
  return art("Burette", "titration, buret", PER, [
    fill(`M-5 -30L5 -30L5 50L-5 50Z`),
    ink(`M-5 -84L-5 50Q-5 54 -2 56L-2 60M5 -84L5 50Q5 54 2 56L2 60`), ink(rect(-6, 60, 12, 6, 2)), ink(`M-6 63L-12 63`),
    ink(`M-2 66L-2 74L-0.8 82M2 66L2 74L0.8 82`), ...marks,
  ]);
}
// Pasteur pipette: a rubber bulb and a long glass tip.
function pasteur() {
  return art("Pasteur pipette", "dropper, pipette, glass pipette", PER, [
        ink(`M-6 -82Q0 -88 6 -82L7 -56L-7 -56Z`), ink(`M-5 -56L-5 -10L-1.2 50M5 -56L5 -10L1.2 50`), fine(ink(`M-1.2 50L1.2 50`)),
  ]);
}
// Drying tube: a bulb of drying agent on a bent tube.
function dryingTube() {
  const grains = [[-8, -36], [0, -40], [8, -36], [-4, -30], [5, -28], [-8, -22], [2, -20], [9, -18], [-3, -12]].map(([x, y]) => fine(solid(circle(x, y, 1.6))));
  return art("Drying tube", "calcium chloride tube, guard tube, moisture", PER, [
    ink(`M-3 -60L-3 -50Q-14 -48 -14 -36L-14 -14Q-14 -4 -3 -2L-3 10Q-3 16 -9 20L-30 34M3 -60L3 -50Q14 -48 14 -36L14 -14Q14 -4 3 -2L3 10Q3 20 -5 26L-26 40`),
    fine(ink(`M-11 -44L11 -44M-11 -8L11 -8`)), ...grains,
  ]);
}
// Balloon: a balloon of gas on a needle, for an inert atmosphere or hydrogen.
function balloon() {
  return art("Balloon", "nitrogen balloon, argon, hydrogen, inert atmosphere", PER, [
    fill(`M0 18C-24 14 -30 -12 -28 -26C-25 -46 -12 -56 0 -56C12 -56 25 -46 28 -26C30 -12 24 14 0 18Z`, "light"),
    ink(`M0 18C-24 14 -30 -12 -28 -26C-25 -46 -12 -56 0 -56C12 -56 25 -46 28 -26C30 -12 24 14 0 18Z`),
    ink(`M-4 24L0 18L4 24Z`), ink(`M-3 24L-3 36M3 24L3 36`), ink(rect(-5, 36, 10, 10, 1.5)), ink(`M0 46L0 78`),
    fine(ink(`M-16 -40Q-20 -32 -20 -24`)),
  ]);
}
// Oil bubbler: gas in through a tube dipping under oil, out at the side.
function bubbler() {
  return art("Bubbler", "oil bubbler, gas outlet, Schlenk line", PER, [
    fill(`M-16 10L16 10L16 28Q16 40 0 40Q-16 40 -16 28Z`, "light"),
    ink(`M-16 -30L-16 28Q-16 40 0 40Q16 40 16 28L16 -30Q16 -34 12 -34L-12 -34Q-16 -34 -16 -30Z`),
    ink(`M-3 -60L-3 30M3 -60L3 30`), ink(`M16 -22L30 -22M16 -14L30 -14`),
    fine(ink(circle(0, 34, 2))),
  ]);
}
// Watch glass, crystallising dish and an ice bath.
function watchGlass() {
  return art("Watch glass", "evaporating, cover", PER, [ink(`M-40 -6Q0 22 40 -6`), ink(`M-40 -6Q0 16 40 -6`)]);
}
function crystallisingDish() {
  return art("Crystallising dish", "crystallizing dish, evaporating dish", PER, [
    fill(`M-36 0L36 0L36 12Q36 18 30 18L-30 18Q-36 18 -36 12Z`, "light"), ink(`M-36 -18L-36 12Q-36 18 -30 18L30 18Q36 18 36 12L36 -18`),
    ink(`M-36 -18Q-36 -21 ${-36 - LIP} -21M36 -18Q36 -21 ${36 + LIP} -21`),
  ]);
}
function iceBath() {
  const cubes = [[-26, -4, 8], [-12, 0, 9], [6, -6, 8], [20, -2, 9]].map(([x, y, s]) => fine(ink(rect(x, y, s, s, 1.5))));
  return art("Ice bath", "cooling bath, cold bath, 0 °C", PER, [
    ink(`M-36 -24L-36 12Q-36 18 -30 18L30 18Q36 18 36 12L36 -24`),
    ink(`M-36 -24Q-36 -27 ${-36 - LIP} -27M36 -24Q36 -27 ${36 + LIP} -27`), ...cubes,
  ]);
}
// Desiccator: a heavy dish with a lid and a knob, a perforated plate over the drying agent.
function desiccator() {
  return art("Desiccator", "dessicator, drying, vacuum desiccator", PER, [
    fill(`M-30 22L30 22L28 34Q26 40 18 40L-18 40Q-26 40 -28 34Z`, "light"),
    ink(`M-36 -2L-30 22L-28 34Q-26 40 -18 40L18 40Q26 40 28 34L30 22L36 -2`), ink(`M-40 -2L40 -2`),
    ink(`M-40 -6Q-40 -34 0 -38Q40 -34 40 -6Z`), ink(rect(-6, -46, 12, 8, 3)),
    ink(`M-33 12L33 12`),
  ]);
}
// Retort stand with a clamp: a base, a rod, a boss and a clamp's jaws.
function retortStand() {
  return art("Retort stand", "clamp stand, ring stand, clamp, boss", PER, [
    ink(rect(-30, 76, 60, 8, 2)), ink(`M-24 76L-24 -84M-20 76L-20 -84M-24 -84L-20 -84`),
    ink(rect(-28, -42, 12, 10, 2)), ink(`M-16 -39L18 -39M-16 -35L18 -35`),
    ink(`M18 -44Q30 -44 30 -37Q30 -30 18 -30M18 -44L18 -30`), ink(`M22 -46L22 -28`),
  ]);
}
// Bunsen burner: a base, a barrel with its air collar, and a flame.
function bunsen() {
  return art("Bunsen burner", "burner, flame, heating", PER, [
    fill(`M0 -78C-8 -64 -10 -52 -6 -40L6 -40C10 -52 8 -64 0 -78Z`, "light"), fill(`M0 -60C-4 -52 -4 -46 -3 -40L3 -40C4 -46 4 -52 0 -60Z`),
    ink(`M0 -78C-8 -64 -10 -52 -6 -40M0 -78C8 -64 10 -52 6 -40`),
    ink(`M-6 -40L-6 30M6 -40L6 30`), ink(rect(-8, 6, 16, 10, 2)), ink(`M-24 30L24 30L28 40L-28 40Z`), ink(`M24 35L40 35`),
  ]);
}
// NMR tube and cuvette.
function nmrTube() {
  return art("NMR tube", "nuclear magnetic resonance, sample tube", PER, [
    fill(`M-3 20L3 20L3 74Q3 77 0 77Q-3 77 -3 74Z`), ink(`M-3 -66L-3 74Q-3 77 0 77Q3 77 3 74L3 -66`), ink(rect(-4.5, -82, 9, 16, 2)),
  ]);
}
function cuvette() {
  return art("Cuvette", "cell, UV-Vis, spectrophotometry", PER, [
    fill(`M-10 -2L10 -2L10 36L-10 36Z`), ink(`M-10 -36L-10 36L10 36L10 -36`), ink(`M-12 -36L12 -36`),
    fine(ink(`M-10 -24L10 -24`)),
  ]);
}
// Schlenk line: a double manifold (vacuum above, inert gas below) with four taps, each to a hose barb below; the
// vacuum leaves at the left end (to the trap and pump), the gas at the right (to the bubbler).
function schlenkLine() {
  const taps = [-60, -20, 20, 60], gaps = [-92, ...taps.flatMap((x) => [x - 6, x + 6]), 92];
  const walls = [];
  for (let k = 0; k < gaps.length; k += 2) for (const y of [-36, -28, -16, -8]) walls.push(`M${gaps[k]} ${y}L${gaps[k + 1]} ${y}`);
  const barb = (x) => `M${x - 3} 2L${x - 3} 16L${x - 5} 22M${x + 3} 2L${x + 3} 16L${x + 5} 22`;
  return art("Schlenk line", "inert-gas manifold, double manifold, vacuum line, nitrogen line, argon line", PER, [
    ink(walls.join("")), ink(`M92 -36A4 4 0 0 1 92 -28M-92 -16A4 4 0 0 0 -92 -8`),
    ink(nozzle(92, -32, -1)), ink(nozzle(92, -12, 1)),
    ...taps.flatMap((x) => [ink(rect(x - 6, -42, 12, 44, 3)), fine(ink(barb(x))), fine(ink(`M${x} -42L${x} -48M${x - 5} -48L${x + 5} -48`)), fine(ink(`M${x - 2.5} -30L${x + 2.5} -12`))]),
  ]);
}
// Photoreactor: an immersion well (a lamp in a double-walled cooling jacket, water in and out at its head) through
// the lid of a reaction vessel, and the lamp's light through the solution.
function photoreactor() {
  const rays = [-20, 0, 20].flatMap((a) => [-1, 1].map((s) => fine(ink(`M${P(s * 21 * Math.cos(a * deg), 4 + 21 * Math.sin(a * deg))}L${P(s * 30 * Math.cos(a * deg), 4 + 30 * Math.sin(a * deg))}`))));
  return art("Photoreactor", "immersion well, photochemistry, mercury lamp, UV lamp, irradiation", PER, [
    fill(`M-34 -30L-34 40A34 34 0 0 0 34 40L34 -30L16 -30L16 44A16 16 0 0 1 -16 44L-16 -30Z`), fill(`M-5 -100L-5 32A5 5 0 0 0 5 32L5 -100Z`, "light"),
    ink(`M-34 -56L-34 40A34 34 0 0 0 34 40L34 -56`), ink(rect(-40, -62, 80, 6, 2)),
    ink(`M-16 -56L-16 44A16 16 0 0 0 16 44L16 -56M-16 -62L-16 -88L-10 -88L-10 -62M16 -62L16 -88L10 -88L10 -62`),
    ink(`M-10 -56L-10 44A10 10 0 0 0 10 44L10 -56`), ink(nozzle(16, -80, 1)), ink(nozzle(16, -70, -1)),
    ink(`M-5 -100L-5 32A5 5 0 0 0 5 32L5 -100`), ink(rect(-7, -108, 14, 8, 2)), ...rays,
  ]);
}

export const GLASSWARE = [twoNeck(), threeNeck(), pearFlask(), volumetricFlask(), buchnerFlask(), buchnerFunnel(), filterFunnel(),
  droppingFunnel(), liebigCondenser(), vigreux(), deanStark(), distillationHead(), claisen(), receiverAdapter(), thermometer(),
  measuringCylinder(), burette(), pasteur(), dryingTube(), balloon(), bubbler(), watchGlass(), crystallisingDish(), iceBath(),
  desiccator(), retortStand(), bunsen(), nmrTube(), cuvette(), schlenkLine(), photoreactor()];
