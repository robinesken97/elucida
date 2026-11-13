// The library's Organisms, Bugs, Anatomy and BioArt sets: model organisms, insects and spiders, organs, and the parts
// of biology diagrams, in the Lab group's line style (art.mjs path data, 40 units to a bond length, y down). Each is
// built from simple shapes (ovals, arcs and smooth curves) worked out here; every drawing is Octet's own.
import { art, circle, ellipse, fill, fine, ink, rect, seg, solid, subpaths } from "./art.mjs";

const PER = { per: 40 };
const f = (v) => Math.round(v * 100) / 100;
const deg = Math.PI / 180;
const P = (x, y) => `${f(x)} ${f(y)}`;
// An oval turned by a degrees about its middle (cx, cy).
function oval(cx, cy, rx, ry, a = 0) {
  const c = Math.cos(a * deg), s = Math.sin(a * deg), at = (x, y) => P(cx + x * c - y * s, cy + x * s + y * c), k = 0.5523;
  return `M${at(rx, 0)}C${at(rx, ry * k)} ${at(rx * k, ry)} ${at(0, ry)}C${at(-rx * k, ry)} ${at(-rx, ry * k)} ${at(-rx, 0)}C${at(-rx, -ry * k)} ${at(-rx * k, -ry)} ${at(0, -ry)}C${at(rx * k, -ry)} ${at(rx, -ry * k)} ${at(rx, 0)}Z`;
}
// A smooth open curve through points (Catmull-Rom made cubic).
function smooth(ps, closed = false) {
  const n = ps.length, at = (i) => ps[closed ? (i + n) % n : Math.max(0, Math.min(n - 1, i))];
  let d = `M${P(...ps[0])}`;
  for (let i = 0; i < (closed ? n : n - 1); i++) {
    const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
    d += `C${P(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)} ${P(p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)} ${P(...p2)}`;
  }
  return closed ? `${d}Z` : d;
}
// A leg or antenna: a line through its joints.
const limb = (...ps) => `M${ps.map((p) => P(...p)).join("L")}`;
// Both sides of a body drawn on its middle line x = 0 (top views): the right-hand parts and their mirror images.
// (Read as curves first, so an arc's flags are not taken for points.)
function mirrorX(d) {
  const q = (p) => P(-p[0], p[1]);
  return subpaths(d).map(({ points, closed }) => {
    let out = `M${q(points[0].at)}`;
    const step = (a, b) => (a.c2 || b.c1 ? `C${q(a.c2 ?? a.at)} ${q(b.c1 ?? b.at)} ${q(b.at)}` : `L${q(b.at)}`);
    for (let i = 1; i < points.length; i++) out += step(points[i - 1], points[i]);
    return closed ? `${out}${step(points[points.length - 1], points[0])}Z` : out;
  }).join("");
}
const both = (part) => [part, [part[0], mirrorX(part[1]), part[2]]];

// ——— Organisms (side views face right, top views head up) ———
function rodent(name, also, { length, ear, tail }) {
  const L = length, body = smooth([[-L, 8], [-L + 8, -14], [-L * 0.2, -22], [L * 0.45, -16], [L * 0.8, -6], [L + 6, 4], [L * 0.8, 10], [L * 0.2, 12], [-L * 0.5, 13]], true);
  return art(name, also, PER, [
    ink(body), ink(circle(L * 0.48, -18, ear)), solid(circle(L * 0.78, -5, 1.8)),
    ink(smooth([[-L + 2, 6], [-L - 16, 10], [-L - 30, 0], [-L - 30 - tail, -6]])),
    ...[[-L * 0.55, 12], [-L * 0.2, 13], [L * 0.3, 11], [L * 0.55, 9]].map(([x, y]) => ink(limb([x, y], [x - 2, y + 7], [x + 3, y + 7]))),
    ...[-4, 0, 4].map((dy) => fine(ink(limb([L + 4, 3], [L + 16, 1 + dy * 1.5])))),
  ]);
}
const mouse = () => rodent("Mouse", "lab mouse, Mus musculus, rodent, model organism", { length: 26, ear: 8, tail: 22 });
const rat = () => rodent("Rat", "lab rat, Rattus norvegicus, rodent, model organism", { length: 36, ear: 6.5, tail: 34 });
function rabbit() {
  const body = smooth([[-34, 14], [-36, -6], [-20, -20], [4, -18], [18, -10], [22, 2], [20, 14], [0, 18], [-20, 18]], true), head = oval(28, -16, 13, 11, -10);
  return art("Rabbit", "Oryctolagus cuniculus, model organism", PER, [
    ink(body), ink(head), ink(oval(20, -40, 4.5, 15, -15)), ink(oval(27, -42, 4.5, 15, 5)), ink(circle(-38, 4, 6)),
    solid(circle(34, -18, 1.8)), ink(limb([10, 18], [16, 22], [26, 22])), ink(limb([-16, 18], [-30, 22], [-10, 22])),
  ]);
}
function zebrafish() {
  const body = smooth([[-34, 0], [-18, -10], [6, -12], [26, -8], [40, 0], [26, 8], [6, 11], [-18, 9]], true);
  return art("Zebrafish", "Danio rerio, fish, model organism", PER, [
    ink(body), ink(`M-34 0L-50 -12Q-46 0 -50 12Z`), ink(smooth([[-4, -11], [0, -20], [10, -12]])), ink(smooth([[-10, 9], [-6, 17], [4, 10]])),
    ...[-4, 0, 4].map((y) => fine(ink(smooth([[-30, y * 0.6], [-10, y], [12, y * 1.1], [28, y * 0.7]])))), solid(circle(30, -3, 2.2)), fine(ink(`M22 -6Q20 0 22 6`)),
  ]);
}
function nematode() {
  // A worm on an S curve, its head end rounded and its tail tapering to a point; a dot for the mouth. Its width eases in
  // and out (a straight ramp put a corner in its outline where the ramp ended).
  const N = 24, mid = (t) => [-56 + 112 * t, 14 * Math.sin(t * 2 * Math.PI)], ease = (x) => x * x * (3 - 2 * x), width = (t) => 3.2 * ease(Math.min(1, 6 * t, 4 * (1 - t))) + 0.3;
  const side = (s) => Array.from({ length: N + 1 }, (_, k) => {
    const t = k / N, [x, y] = mid(t), [x2, y2] = mid(Math.min(1, t + 1e-3)), [x1, y1] = mid(Math.max(0, t - 1e-3)), dx = x2 - x1, dy = y2 - y1, l = Math.hypot(dx, dy);
    return [x - (dy / l) * width(t) * s, y + (dx / l) * width(t) * s];
  });
  const outline = smooth([...side(1), ...side(-1).reverse()], true);
  return art("Nematode", "C. elegans, Caenorhabditis elegans, worm, roundworm, model organism", PER, [ink(outline), fine(ink(circle(...mid(0.1), 1.2)))]);
}
function frog() {
  // Seen from above: one outline for head and body, eyes bulging at the top, front legs reaching forward and the hind
  // legs folded beside the body, each foot spread.
  const body = smooth([[0, -30], [11, -27], [16, -16], [18, 4], [14, 22], [0, 30], [-14, 22], [-18, 4], [-16, -16], [-11, -27]], true);
  const foot = (x, y, a) => [-30, 0, 30].map((d) => ink(limb([x, y], [x + 7 * Math.cos((a + d) * deg), y + 7 * Math.sin((a + d) * deg)])));
  const side = [ink(limb([15, -8], [26, -14], [30, -24])), ...foot(30, -24, -80), ink(smooth([[14, 16], [30, 22], [34, 4], [26, -2]])), ink(limb([34, 6], [40, 30])), ...foot(40, 30, 80)];
  return art("Frog", "Xenopus, amphibian, model organism", PER, [
    ink(body), ...both(ink(circle(9, -24, 5))), ...both(solid(circle(9, -24, 1.8))), ...side.flatMap((part) => both(part)),
  ]);
}
function plant() {
  // A rosette of leaves fanning out from the base, and a flowering stem.
  const leaf = (a, l) => { const d = [Math.cos(a * deg), Math.sin(a * deg)]; return oval(d[0] * l, 40 + d[1] * l, l, l * 0.38, a); };
  const leaves = [[-170, 14], [-145, 12], [-35, 12], [-10, 14], [-120, 9], [-60, 9]].flatMap(([a, l]) => [ink(leaf(a, l))]);
  return art("Plant", "Arabidopsis thaliana, rosette, model organism, thale cress", PER, [
    ...leaves, ink(smooth([[0, 38], [2, 10], [-2, -20], [0, -40]])), ink(smooth([[1, 0], [12, -12], [16, -22]])), ink(smooth([[-1, -14], [-12, -24], [-14, -32]])),
    ...[[0, -43], [17, -25], [-15, -35]].map(([x, y]) => ink(circle(x, y, 3))), ink(`M-30 44L30 44`),
  ]);
}

// ——— Bugs (top views, head up) ———
// Six legs from a thorax at height y0: forward, out and back on each side.
const sixLegs = (y0) => [[[4, y0 - 4], [16, y0 - 14], [22, y0 - 24]], [[4, y0], [20, y0], [28, y0 + 6]], [[4, y0 + 4], [16, y0 + 14], [20, y0 + 28]]]
  .flatMap((ps) => both(ink(limb(...ps))));
function fly() {
  return art("Fruit fly", "Drosophila melanogaster, fly, insect, model organism", PER, [
    ...both(ink(oval(14, 2, 18, 7, -25))), ink(circle(0, -16, 6)), ...both(fill(oval(5, -18, 3.2, 4), "blue")), ...both(ink(oval(5, -18, 3.2, 4))),
    ink(oval(0, -2, 8, 9)), ink(oval(0, 16, 7, 11)), ...[12, 17, 22].map((y) => fine(ink(seg(-6, y, 6, y)))), ...sixLegs(-2),
  ]);
}
function mosquito() {
  return art("Mosquito", "Anopheles, Aedes, insect, malaria", PER, [
    ...both(ink(oval(10, -2, 16, 4.5, -18))), ink(circle(0, -16, 4.5)), ink(limb([0, -20], [0, -34])), ...both(fine(ink(limb([1.5, -19], [6, -30])))),
    ink(oval(0, -4, 4.5, 7)), ink(oval(0, 18, 3.5, 16)),
    ...both(ink(limb([3, -6], [20, -18], [32, -38]))), ...both(ink(limb([3, -3], [24, 4], [36, 0]))), ...both(ink(limb([3, 0], [18, 20], [28, 42]))),
  ]);
}
function bee() {
  return art("Bee", "honeybee, Apis mellifera, insect, pollinator", PER, [
    ...both(ink(oval(14, -8, 14, 8, -30))), ink(circle(0, -18, 6)), ...both(ink(smooth([[2, -23], [6, -32], [10, -34]]))), ink(oval(0, -4, 8, 8)),
    ink(oval(0, 16, 10, 14)), ...[8, 14, 20].map((y) => solid(rect(-9, y, 18, 3, 1.5))), ink(limb([0, 30], [0, 34])),
    ...both(ink(limb([7, -6], [18, -14]))), ...both(ink(limb([8, -2], [20, 4]))), ...both(ink(limb([7, 2], [16, 14]))),
  ]);
}
function ant() {
  return art("Ant", "insect, colony, Formicidae", PER, [
    ink(oval(0, -20, 6, 6)), ink(oval(0, -6, 4, 7)), ink(oval(0, 16, 8, 12)), ...both(ink(limb([3, -25], [10, -32], [16, -30]))),
    ...both(ink(limb([3, -9], [16, -16], [22, -26]))), ...both(ink(limb([4, -5], [18, -2], [26, 4]))), ...both(ink(limb([3, -1], [14, 10], [18, 26]))),
  ]);
}
function beetle() {
  const shell = `M0 -8C14 -8 18 4 18 16C18 32 8 40 0 40C-8 40 -18 32 -18 16C-18 4 -14 -8 0 -8Z`;
  return art("Beetle", "insect, Coleoptera, flour beetle, Tribolium", PER, [
    ink(shell), ink(`M0 -8L0 40`), ink(oval(0, -14, 10, 6)), ink(oval(0, -24, 5, 4)), ...both(ink(limb([3, -27], [8, -34], [10, -40]))),
    ...both(ink(limb([9, -14], [20, -22], [24, -30]))), ...both(ink(limb([16, 4], [26, 4], [32, 10]))), ...both(ink(limb([16, 20], [24, 30], [26, 40]))),
  ]);
}
function butterfly() {
  const upper = smooth([[2, -6], [14, -30], [36, -34], [40, -18], [28, -4]]), lower = smooth([[2, 2], [20, 4], [30, 18], [20, 32], [6, 22]]);
  return art("Butterfly", "insect, Lepidoptera, moth", PER, [
    ...both(ink(`${upper}Z`)), ...both(ink(`${lower}Z`)),
    ...both(fine(ink(circle(24, -20, 4)))), ink(oval(0, 4, 2.5, 18)), ink(circle(0, -16, 3)), ...both(ink(smooth([[1, -18], [5, -30], [10, -38]]))),
  ]);
}
function spider() {
  const leg = (a, b, c) => ink(limb([4, a], [b[0], b[1]], [c[0], c[1]]));
  return art("Spider", "arachnid, Araneae", PER, [
    ink(circle(0, -10, 8)), ink(oval(0, 12, 12, 15)),
    ...both(leg(-14, [20, -26], [28, -14])), ...both(leg(-11, [24, -14], [34, -4])), ...both(leg(-8, [22, -2], [32, 12])), ...both(leg(-6, [18, 6], [24, 26])),
    ...both(ink(limb([2, -17], [3, -21]))),
  ]);
}
function tick() {
  return art("Tick", "Ixodes, arachnid, parasite, Lyme disease", PER, [
    ink(oval(0, 6, 16, 20)), fine(ink(oval(0, -2, 10, 10))), ink(`M-4 -14L-3 -22L3 -22L4 -14`),
    ...[-8, -2, 4, 10].flatMap((y, k) => both(ink(limb([14, y], [24, y - 6 + k * 4], [30, y + k * 3])))),
  ]);
}

// ——— Anatomy ———
function person() {
  const figure = smooth([[0, -62], [8, -60], [10, -52], [6, -44], [20, -40], [26, -28], [30, 0], [26, 2], [20, -24], [18, -2], [16, 30], [14, 64], [6, 64], [4, 30], [0, 6],
    [-4, 30], [-6, 64], [-14, 64], [-16, 30], [-18, -2], [-20, -24], [-26, 2], [-30, 0], [-26, -28], [-20, -40], [-6, -44], [-10, -52], [-8, -60]], true);
  return art("Person", "human body, body outline, figure, patient", PER, [ink(figure)]);
}
function lungs() {
  const lobe = smooth([[4, -18], [14, -30], [26, -24], [32, 4], [30, 30], [18, 34], [8, 26], [6, 8]], true);
  return art("Lungs", "respiratory, organ, trachea, bronchi", PER, [
    ...both(ink(lobe)), ink(`M-3 -46L-3 -22M3 -46L3 -22`), ...both(ink(smooth([[2, -22], [10, -16], [14, -6]]))), ...both(fine(ink(smooth([[10, -16], [18, -4], [20, 10]])))),
  ]);
}
function kidney() {
  const bean = smooth([[0, -32], [16, -26], [20, 0], [16, 26], [0, 32], [-10, 22], [-8, 8], [-4, 0], [-8, -8], [-10, -22]], true);
  return art("Kidney", "renal, organ, urinary, nephron", PER, [
    ink(bean), fine(ink(smooth([[4, -16], [10, 0], [4, 16]]))), ink(smooth([[-5, 4], [-16, 14], [-18, 40]])), ink(limb([-6, -2], [-24, -4])), ink(limb([-6, 2], [-24, 6])),
  ]);
}
function liver() {
  const outline = smooth([[-40, -10], [-20, -22], [16, -20], [38, -14], [34, -4], [10, 8], [-16, 22], [-34, 18]], true);
  return art("Liver", "hepatic, organ, gallbladder", PER, [ink(outline), fine(ink(smooth([[-2, -20], [0, -6], [-4, 10]]))), ink(oval(4, 12, 4, 7, 20))]);
}
function eye() {
  return art("Eye", "eyeball, retina, lens, cornea, organ, vision", PER, [
    ink(circle(0, 0, 30)), fine(ink(circle(0, 0, 26))), ink(`M-26 -15A17 17 0 0 0 -26 15`), ink(oval(-19, 0, 4, 10)),
    ink(limb([-24, -10], [-24, -14])), ink(limb([-24, 10], [-24, 14])), ink(`M28 -4L42 -6M28 4L42 6`),
  ]);
}
function tooth() {
  const outline = smooth([[-16, -24], [-8, -30], [0, -26], [8, -30], [16, -24], [16, -6], [12, 8], [10, 30], [4, 34], [2, 14], [-2, 14], [-4, 34], [-10, 30], [-12, 8], [-16, -6]], true);
  return art("Tooth", "molar, dental, enamel", PER, [ink(outline), fine(ink(smooth([[-14, -6], [0, -8], [14, -6]])))]);
}
function bone() {
  const end = (y, s) => `M-10 ${y}C-22 ${y - s * 2} -20 ${y - s * 16} -10 ${y - s * 12}C-6 ${y - s * 20} 6 ${y - s * 20} 10 ${y - s * 12}C20 ${y - s * 16} 22 ${y - s * 2} 10 ${y}`;
  return art("Bone", "long bone, femur, skeleton", PER, [ink(end(-32, 1)), ink(end(32, -1)), ink(`M-10 -32L-8 32M10 -32L8 32`)]);
}

// ——— BioArt: the parts of biology diagrams ———
function tRNA() {
  const rungs = (x0, y0, x1, y1) => Array.from({ length: 4 }, (_, k) => { const t = (k + 1) / 5, x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t, h = x1 === x0; return fine(ink(h ? seg(x - 2.5, y, x + 2.5, y) : seg(x, y - 2.5, x, y + 2.5))); });
  return art("tRNA", "transfer RNA, cloverleaf, anticodon", PER, [
    ink(seg(-2.5, -40, -2.5, -8)), ink(seg(2.5, -46, 2.5, -8)), ...rungs(0, -40, 0, -8),
    ink(seg(-2.5, -5.5, -22, -5.5)), ink(seg(-2.5, -0.5, -22, -0.5)), ...rungs(-2.5, -3, -22, -3), ink(circle(-29, -3, 7)),
    ink(seg(2.5, -5.5, 22, -5.5)), ink(seg(2.5, -0.5, 22, -0.5)), ...rungs(2.5, -3, 22, -3), ink(circle(29, -3, 7)),
    ink(seg(-2.5, 0, -2.5, 22)), ink(seg(2.5, 0, 2.5, 22)), ...rungs(0, 0, 0, 22), ink(`M-2.5 22A7 7 0 1 0 2.5 22`), ...[-4, 0, 4].map((x) => solid(circle(x, 34, 1.2))),
  ]);
}
function mRNA() {
  const N = 20, y = (x) => 6 * Math.sin(x / 9);
  const strand = smooth(Array.from({ length: N + 1 }, (_, k) => { const x = -60 + (120 * k) / N; return [x, y(x)]; }));
  return art("mRNA", "messenger RNA, transcript, strand, codons", PER, [ink(strand), ...Array.from({ length: 15 }, (_, k) => { const x = -56 + k * 8; return fine(ink(seg(x, y(x), x, y(x) - 7))); }), ink(`M60 ${f(y(60))}L66 ${f(y(60))}`)]);
}
function plasmid() {
  const arc = (a0, a1, r) => `M${P(r * Math.cos(a0 * deg), r * Math.sin(a0 * deg))}A${r} ${r} 0 0 1 ${P(r * Math.cos(a1 * deg), r * Math.sin(a1 * deg))}`;
  const head = (a, r) => { const p = [r * Math.cos(a * deg), r * Math.sin(a * deg)], t = [-Math.sin(a * deg), Math.cos(a * deg)], n = [Math.cos(a * deg), Math.sin(a * deg)]; return `M${P(p[0] - t[0] * 6 + n[0] * 5, p[1] - t[1] * 6 + n[1] * 5)}L${P(...p)}L${P(p[0] - t[0] * 6 - n[0] * 5, p[1] - t[1] * 6 - n[1] * 5)}`; };
  return art("Plasmid", "vector, circular DNA, gene, cloning", PER, [
    ink(circle(0, 0, 32)), fine(ink(circle(0, 0, 28))), ink(arc(-60, 40, 38)), ink(head(40, 38)), ink(arc(120, 200, 38)), ink(head(200, 38)), solid(rect(-34, -4, 8, 8, 1)),
  ]);
}
function gene() {
  return art("Gene", "promoter, coding sequence, transcription start, DNA", PER, [
    ink(seg(-60, 0, 60, 0)), ink(rect(-14, -8, 52, 16, 2)), ink(`M-24 0L-24 -18L-10 -18M-15 -22L-10 -18L-15 -14`),
  ]);
}
function coil() {
  return art("Protein coil", "random coil, loop, polypeptide, protein", PER, [ink(smooth([[-50, 10], [-36, -12], [-20, 6], [-10, -20], [6, -8], [0, 12], [18, 18], [26, -6], [44, -2], [50, 16]]))]);
}
function inhibition() {
  return art("Inhibition", "inhibits, blocks, T-bar, pathway, signalling", PER, [ink(seg(-40, 0, 36, 0)), ink(seg(38, -10, 38, 10))]);
}
function ligandBinding() {
  return art("Receptor and ligand", "binding site, ligand, receptor, signalling, cup", PER, [
    ink(`M-4 40L-4 0Q-4 -2 -6 -2Q-22 -2 -22 -18L-22 -26M4 40L4 0Q4 -2 6 -2Q22 -2 22 -18L22 -26M-14 -26Q-14 -10 0 -10Q14 -10 14 -26`),
    ink(`M-22 -26L-14 -26M14 -26L22 -26`), fill(circle(0, -24, 9), "blue"), ink(circle(0, -24, 9)),
  ]);
}
function proteinComplex() {
  return art("Protein complex", "proteins, subunits, complex, dimer, oligomer", PER, [
    ...[[-14, 4, 18, 14, -10], [14, 6, 16, 13, 15], [0, -14, 15, 11, 0]].flatMap(([x, y, a, b, t]) => [ink(oval(x, y, a, b, t))]),
  ]);
}

export const ORGANISMS = [mouse(), rat(), rabbit(), zebrafish(), frog(), nematode(), plant()];
export const BUGS = [fly(), mosquito(), bee(), ant(), beetle(), butterfly(), spider(), tick()];
export const ANATOMY = [person(), lungs(), kidney(), liver(), eye(), tooth(), bone()];
export const BIOART = [tRNA(), mRNA(), plasmid(), gene(), coil(), inhibition(), ligandBinding(), proteinComplex()];
