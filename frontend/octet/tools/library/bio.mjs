// The library's Biomolecules and Cells sets: membranes, proteins, nucleic acids, organelles, cells and microbes, in
// the Lab group's line style (art.mjs path data, 40 units to a bond length, y down). Every drawing here is Octet's own,
// worked out from simple geometry.
import { art, circle, ellipse, fill, fine, ink, membrane, rect, seg, solid } from "./art.mjs";

const PER = { per: 40 };
const f = (v) => Math.round(v * 100) / 100;
const deg = Math.PI / 180;
// A point at angle a (degrees) and radius r about (cx, cy).
const polar = (cx, cy, r, a) => [f(cx + r * Math.cos(a * deg)), f(cy + r * Math.sin(a * deg))];

// A phospholipid at (x, y): its head (a circle of radius h) and two tails of length t, pointing the way dir (1 down,
// -1 up), or one tail (a detergent, as in a micelle). Each tail is a gentle wave.
const tail = (x0, y0, ux, uy, t) => { const nx = -uy, ny = ux, w = 1.4; let d = `M${f(x0)} ${f(y0)}`; for (let k = 1; k <= 4; k++) { const s = (t * k) / 4, side = k % 2 ? w : -w; d += `L${f(x0 + ux * s + nx * side)} ${f(y0 + uy * s + ny * side)}`; } return d; };
function lipid(x, y, angle, { h = 4.2, t = 20, tails = 2 } = {}) {
  const ux = Math.cos(angle * deg), uy = Math.sin(angle * deg), nx = -uy, ny = ux, base = [x + ux * h, y + uy * h];
  const ends = tails === 2 ? [[-1.8, 0], [1.8, 0]] : [[0, 0]];
  return [fill(circle(f(x), f(y), h), "light"), ink(circle(f(x), f(y), h)), ...ends.map(([o]) => fine(ink(tail(base[0] + nx * o, base[1] + ny * o, ux, uy, t))))];
}
// Membranes: lines and curves in Octet's Membrane style, with lipid()'s lipids, nine a side to two bond lengths. A drag
// on an end or a point makes one longer or bends it, and its lipids keep their size.
function lipidBilayer() { return art("Lipid bilayer", "membrane, phospholipid bilayer, cell membrane", PER, [membrane(seg(-40, 0, 40, 0))]); }
function curvedMembrane() { return art("Curved membrane", "membrane arc, curved bilayer, lipid bilayer", PER, [membrane("M-60 16A75 75 0 0 1 60 16")]); }
function cellMembrane() { return art("Cell membrane", "plasma membrane, membrane ellipse, closed bilayer, vesicle", PER, [membrane(ellipse(0, 0, 80, 60))]); }
function phospholipid() {
  return art("Phospholipid", "lipid, amphiphile, head group, fatty acid tails", PER, [fill(circle(0, -22, 8), "light"), ink(circle(0, -22, 8)), ink(tail(-3, -14, 0, 1, 40)), ink(tail(3, -14, 0, 1, 40))]);
}
function micelle() {
  const parts = [];
  for (let k = 0; k < 18; k++) { const a = k * 20, [x, y] = polar(0, 0, 30, a); parts.push(...lipid(x, y, a + 180, { h: 4.2, t: 22, tails: 1 })); }
  return art("Micelle", "surfactant, detergent, SDS", PER, parts);
}
function liposome() {
  const parts = [];
  for (let k = 0; k < 28; k++) { const a = k * (360 / 28), [x, y] = polar(0, 0, 54, a); parts.push(...lipid(x, y, a + 180, { t: 10 })); }
  for (let k = 0; k < 18; k++) { const a = k * 20 + 10, [x, y] = polar(0, 0, 30, a); parts.push(...lipid(x, y, a, { t: 10 })); }
  return art("Liposome", "vesicle, lipid bilayer, drug delivery", PER, parts);
}
// A membrane protein with a membrane each side, which a drag on its outer end makes longer.
const inMembrane = (x0, x1, protein) => [membrane(seg(-x1, 0, -x0, 0)), membrane(seg(x0, 0, x1, 0)), ...protein];
function ionChannel() {
  return art("Ion channel", "channel, pore, membrane protein, transport", PER, inMembrane(34, 64, [
    ink(`M-24 -36Q-28 -30 -26 0Q-28 30 -24 36L-8 36Q-4 30 -6 0Q-4 -30 -8 -36Z`),
    ink(`M24 -36Q28 -30 26 0Q28 30 24 36L8 36Q4 30 6 0Q4 -30 8 -36Z`),
    fill(circle(0, -48, 4), "blue"), ink(circle(0, -48, 4)), fill(circle(0, 0, 4), "blue"), ink(circle(0, 0, 4)), fine(ink(`M0 14L0 30M-4 25L0 30L4 25`)),
  ]));
}
// A receptor with seven helices across the membrane, its loops above and below (a G protein-coupled receptor).
function receptor() {
  const parts = [];
  for (let k = 0; k < 7; k++) { const x = -42 + k * 14; parts.push(ink(rect(x - 5, -26, 10, 52, 5))); }
  for (let k = 0; k < 6; k++) { const x = -42 + k * 14, y = k % 2 ? 26 : -26, d = k % 2 ? 8 : -8; parts.push(ink(`M${x} ${y}Q${x + 7} ${y + 2 * d} ${x + 14} ${y}`)); }
  parts.push(ink(`M-42 -26Q-48 -40 -38 -48`), ink(`M42 26Q48 38 40 46`));
  return art("Receptor", "GPCR, seven-transmembrane, G protein-coupled receptor, membrane protein", PER, inMembrane(56, 86, parts));
}
// Antibody: two heavy chains and two light chains in a Y, with the binding sites at the tips of the arms.
function antibody() {
  const arm = (s) => {
    const t = (x, y) => `${f(s * x)} ${f(y)}`;
    return [
      ink(`M${t(4, 4)}L${t(30, -22)}Q${t(34, -26)} ${t(38, -22)}L${t(40, -20)}Q${t(44, -16)} ${t(40, -12)}L${t(14, 14)}Z`),
      fill(`M${t(22, -30)}L${t(44, -52)}Q${t(48, -56)} ${t(52, -52)}L${t(54, -50)}Q${t(58, -46)} ${t(54, -42)}L${t(32, -20)}Z`, "light"), ink(`M${t(22, -30)}L${t(44, -52)}Q${t(48, -56)} ${t(52, -52)}L${t(54, -50)}Q${t(58, -46)} ${t(54, -42)}L${t(32, -20)}Z`),
    ];
  };
  return art("Antibody", "immunoglobulin, IgG, Y-shaped, heavy chain, light chain", PER, [
    ...arm(1), ...arm(-1), ink(rect(-10, 4, 20, 50, 6)), fine(ink(seg(0, 4, 0, 54))), fine(ink(`M-4 10L4 10M-4 14L4 14`)),
  ]);
}
// Enzyme and substrate: an enzyme with its active site and the substrate that fits it, lifted out.
function enzyme() {
  return art("Enzyme and substrate", "lock and key, active site, induced fit, catalysis", PER, [
        ink(`M-40 10C-46 -16 -26 -34 -8 -30L-8 -18Q-8 -10 0 -10Q8 -10 8 -18L8 -30C28 -34 46 -16 40 10C36 34 -36 34 -40 10Z`),
    fill(`M-7 -54L7 -54L7 -42Q7 -36 0 -36Q-7 -36 -7 -42Z`, "blue"), ink(`M-7 -54L7 -54L7 -42Q7 -36 0 -36Q-7 -36 -7 -42Z`),
  ]);
}
// DNA double helix: two strands winding about one axis, their base pairs as rungs.
function dnaHelix() {
  const N = 120, len = 150, r = 22, turns = 1.5, strand = (phase) => {
    let d = "";
    for (let k = 0; k <= N; k++) { const y = -len / 2 + (len * k) / N, x = r * Math.sin(phase + (2 * Math.PI * turns * k) / N); d += `${k ? "L" : "M"}${f(x)} ${f(y)}`; }
    return d;
  };
  const rungs = [];
  for (let k = 3; k < N; k += 6) { const y = -len / 2 + (len * k) / N, t = (2 * Math.PI * turns * k) / N, a = r * Math.sin(t), b = r * Math.sin(t + 2.2); if (Math.abs(a - b) > 6) rungs.push(fine(ink(seg(f(a), f(y), f(b), f(y))))); }
  return art("DNA double helix", "double helix, B-DNA, nucleic acid", PER, [...rungs, ink(strand(0)), ink(strand(2.2))]);
}
// Alpha helix (a coil seen a little from the side, so each turn shows as a loop) and beta strand (a broad arrow).
function alphaHelix() {
  let d = "";
  const N = 140, len = 120, r = 14, turns = 4;
  for (let k = 0; k <= N; k++) { const t = (2 * Math.PI * turns * k) / N, y = -len / 2 + (len * k) / N + 3.5 * Math.cos(t); d += `${k ? "L" : "M"}${f(r * Math.sin(t))} ${f(y)}`; }
  return art("Alpha helix", "α-helix, protein, secondary structure", PER, [ink(d)]);
}
function betaStrand() {
  return art("Beta strand", "β-sheet, β-strand, protein, secondary structure", PER, [fill(`M-60 -8L30 -8L30 -18L60 0L30 18L30 8L-60 8Z`, "light"), ink(`M-60 -8L30 -8L30 -18L60 0L30 18L30 8L-60 8Z`)]);
}
// Chromosome: two sister chromatids joined at the centromere, with bands.
function chromosome() {
  const chromatid = (s) => `M${s * 2} -4Q${s * 6} -18 ${s * 4} -48Q${s * 4} -58 ${s * 12} -58Q${s * 20} -58 ${s * 20} -48Q${s * 20} -18 ${s * 8} 0Q${s * 20} 18 ${s * 20} 48Q${s * 20} 58 ${s * 12} 58Q${s * 4} 58 ${s * 4} 48Q${s * 6} 18 ${s * 2} 4Z`;
  return art("Chromosome", "chromatid, centromere, mitosis, karyotype", PER, [
    ink(chromatid(1)), ink(chromatid(-1)),
    ...[-40, -26, 26, 40].flatMap((y) => [fine(ink(seg(5, y, 19, y))), fine(ink(seg(-5, y, -19, y)))]),
  ]);
}
// ——— Cells ———
function nucleusDrawing(cx, cy, r, pores = true) {
  const parts = [ink(circle(cx, cy, r)), fine(ink(circle(cx, cy, r - 3))), fill(circle(cx + r * 0.25, cy - r * 0.1, r * 0.3), "light"), ink(circle(cx + r * 0.25, cy - r * 0.1, r * 0.3))];
  if (pores) for (let k = 0; k < 8; k++) { const [x, y] = polar(cx, cy, r - 1.5, k * 45 + 20); parts.push(solid(circle(x, y, 1.6))); }
  return parts;
}
function mitochondrionDrawing(cx, cy, w, h, turn = 0) {
  const rot = (x, y) => { const c = Math.cos(turn * deg), s = Math.sin(turn * deg); return `${f(cx + x * c - y * s)} ${f(cy + x * s + y * c)}`; };
  // The cristae: folds of the inner membrane, from the top and the bottom in turn, each a narrow U into the middle.
  const cristae = [];
  for (let k = 0, n = 5; k < n; k++) {
    const x = -w * 0.62 + (1.24 * w * k) / (n - 1), up = k % 2 ? 1 : -1, edge = up * (h * Math.sqrt(Math.max(0, 1 - (x / w) ** 2)) - 3), tip = -up * h * 0.25;
    cristae.push(`M${rot(x - 2, edge)}L${rot(x - 2, tip + up * 2)}Q${rot(x, tip - up * 1)} ${rot(x + 2, tip + up * 2)}L${rot(x + 2, edge)}`);
  }
  const outline = (a, b) => `M${rot(-a, 0)}C${rot(-a, -b * 1.33)} ${rot(a, -b * 1.33)} ${rot(a, 0)}C${rot(a, b * 1.33)} ${rot(-a, b * 1.33)} ${rot(-a, 0)}Z`;
  return [fill(outline(w, h), "light"), ink(outline(w, h)), ...cristae.map((d) => fine(ink(d)))];
}
function nucleus() { return art("Nucleus", "cell nucleus, nucleolus, nuclear envelope, organelle", PER, nucleusDrawing(0, 0, 40)); }
function mitochondrion() { return art("Mitochondrion", "mitochondria, cristae, organelle, ATP", PER, mitochondrionDrawing(0, 0, 50, 22)); }
function chloroplast() {
  const grana = [];
  for (const [x, y] of [[-26, 2], [-6, -6], [14, 4], [32, -4]]) for (let k = 0; k < 4; k++) grana.push(fine(ink(rect(x - 6, y - 8 + k * 4, 12, 3, 1.5))));
  return art("Chloroplast", "thylakoid, grana, photosynthesis, organelle", PER, [
    fill(ellipse(0, 0, 52, 24), "light"), ink(ellipse(0, 0, 52, 24)), fine(ink(ellipse(0, 0, 48, 20))), ...grana, fine(ink(`M-20 -4L-12 -2M0 0L8 0M20 2L26 0`)),
  ]);
}
function golgi() {
  const parts = [];
  for (let k = 0; k < 5; k++) { const y = -20 + k * 10, w = 40 - Math.abs(k - 2) * 4; parts.push(fill(`M${-w} ${y}Q0 ${y - 10} ${w} ${y}Q${w + 4} ${y + 4} ${w} ${y + 5}Q0 ${y - 5} ${-w} ${y + 5}Q${-w - 4} ${y + 4} ${-w} ${y}Z`, "light"), ink(`M${-w} ${y}Q0 ${y - 10} ${w} ${y}Q${w + 4} ${y + 4} ${w} ${y + 5}Q0 ${y - 5} ${-w} ${y + 5}Q${-w - 4} ${y + 4} ${-w} ${y}Z`)); }
  for (const [x, y, r] of [[48, -10, 4], [52, 6, 3.5], [-48, 14, 4], [44, 22, 3]]) parts.push(ink(circle(x, y, r)));
  return art("Golgi apparatus", "Golgi body, cisternae, organelle", PER, parts);
}
function roughER() {
  const sheet = (y) => `M-50 ${y}C-36 ${y - 10} -24 ${y + 10} -10 ${y}C4 ${y - 10} 16 ${y + 10} 30 ${y}C40 ${y - 6} 48 ${y - 2} 50 ${y + 4}`;
  const parts = [];
  for (const y of [-18, 0, 18]) { parts.push(ink(sheet(y)), ink(sheet(y + 6))); for (let x = -46; x <= 46; x += 8) { const t = (x + 50) / 100; parts.push(solid(circle(x, y - 3 + 4 * Math.sin(t * 9), 1.6))); } }
  return art("Rough endoplasmic reticulum", "rough ER, ribosomes, organelle", PER, parts);
}
function smoothER() {
  return art("Smooth endoplasmic reticulum", "smooth ER, organelle", PER, [
    ink(`M-50 -10C-40 -30 -20 -30 -10 -12C0 6 20 6 30 -12C38 -26 48 -20 50 -10`), ink(`M-50 0C-40 -20 -20 -20 -10 -2C0 16 20 16 30 -2C38 -16 48 -10 50 0`),
    ink(`M-40 20C-30 8 -10 10 -4 24C2 36 22 36 30 24`), ink(`M-40 30C-30 18 -10 20 -4 34C2 46 22 46 30 34`),
  ]);
}
function ribosome() {
  return art("Ribosome", "translation, mRNA, protein synthesis", PER, [
    fill(`M-30 0C-34 -26 34 -26 30 0Z`, "light"), ink(`M-30 0C-34 -26 34 -26 30 0Z`), ink(`M-34 4C-38 34 38 34 34 4Z`),
    ink(`M-60 2L60 2`), fine(ink(`M2 -14Q10 -30 4 -44Q0 -52 8 -58`)),
  ]);
}
function vesicle() { return art("Vesicle", "vesicle, lysosome, endosome, organelle", PER, [ink(circle(0, 0, 24)), fine(ink(circle(0, 0, 20)))]); }
function centrioles() {
  const barrel = (x, y, w, h) => [ink(rect(x, y, w, h, 3)), ...[1, 2, 3, 4].map((k) => fine(ink(seg(x + (w * k) / 5, y, x + (w * k) / 5, y + h))))];
  return art("Centrioles", "centrosome, microtubules, organelle", PER, [...barrel(-30, -12, 30, 24), ...barrel(4, -30, 18, 40)]);
}
function animalCell() {
  return art("Animal cell", "cell, eukaryote, organelles", { per: 40 }, [
        ink(`M-80 -10C-84 -50 -40 -68 0 -64C44 -62 84 -44 82 0C80 44 40 66 -4 64C-50 62 -78 34 -80 -10Z`),
    ...nucleusDrawing(-6, -4, 24), ...mitochondrionDrawing(46, -26, 18, 8, 20), ...mitochondrionDrawing(-44, 26, 14, 6, -30), ...mitochondrionDrawing(40, 34, 15, 7, 70),
    fine(ink(`M-48 -40C-40 -48 -30 -44 -24 -38M-52 -32C-44 -40 -34 -36 -28 -30`)), ink(circle(18, 44, 5)), ink(circle(-34, -10, 4)), ink(circle(60, 4, 4)),
  ]);
}
function plantCell() {
  const plastid = (x, y, t) => mitochondrionDrawing(x, y, 14, 6, t).map((p) => (p[0] === "fill" ? [p[0], p[1], { tint: "blue" }] : p));
  return art("Plant cell", "cell, cell wall, vacuole, chloroplast, eukaryote", { per: 40 }, [
    ink(rect(-80, -60, 160, 120, 10)), ink(rect(-74, -54, 148, 108, 8)),
    fine(ink(`M-30 -36L46 -36Q60 -36 60 -22L60 24Q60 40 44 40L-24 40Q-36 40 -36 26L-36 -30Q-36 -36 -30 -36Z`)),
    ...nucleusDrawing(-56, -26, 14, false), ...plastid(-56, 18, 70), ...plastid(-56, 42, 10), ...plastid(26, 48, 0), ...plastid(-10, -46, 0), ...plastid(40, -46, 0),
  ]);
}
function bacterium() {
  return art("Bacterium", "bacteria, bacillus, rod, prokaryote, E. coli", PER, [
    ink(rect(-50, -20, 100, 40, 20)), fine(ink(rect(-46, -16, 92, 32, 16))),
    fine(ink(`M-24 0C-20 -10 -10 10 -4 0C2 -10 10 8 16 -2C20 -8 26 4 28 0`)), ink(`M50 0C60 -8 66 8 76 0C84 -6 90 6 98 0`), ...[-30, 0, 30].map((x) => fine(ink(`M${x} -20L${x - 3} -27M${x} 20L${x + 3} 27`))),
  ]);
}
function cocci() {
  return art("Cocci", "bacteria, coccus, Staphylococcus, prokaryote", PER, [[-22, -10], [0, -16], [-10, 10], [14, 4], [30, -12], [8, 26]].flatMap(([x, y]) => [ink(circle(x, y, 11))]));
}
function virus() {
  const parts = [], R = 30;
  const hex = Array.from({ length: 6 }, (_, k) => polar(0, 0, R, k * 60 + 30));
  parts.push(fill(`M${hex.map((p) => p.join(" ")).join("L")}Z`, "light"), ink(`M${hex.map((p) => p.join(" ")).join("L")}Z`));
  parts.push(fine(ink(`M${hex[0].join(" ")}L0 0L${hex[2].join(" ")}M0 0L${hex[4].join(" ")}`)));
  for (let k = 0; k < 6; k++) { const [x0, y0] = polar(0, 0, R, k * 60 + 30), [x1, y1] = polar(0, 0, R + 12, k * 60 + 30); parts.push(ink(seg(x0, y0, x1, y1)), ink(circle(...polar(0, 0, R + 15, k * 60 + 30), 3))); }
  return art("Virus", "virion, icosahedral virus, capsid, adenovirus", PER, parts);
}
function envelopedVirus() {
  const parts = [ink(circle(0, 0, 30)), fine(ink(circle(0, 0, 26))), fine(ink(`M-12 -4C-6 -14 4 6 10 -4C14 -10 18 0 14 6`))];
  for (let k = 0; k < 14; k++) { const a = k * (360 / 14), [x0, y0] = polar(0, 0, 30, a), [x1, y1] = polar(0, 0, 38, a), [cx, cy] = polar(0, 0, 41, a); parts.push(ink(seg(x0, y0, x1, y1)), fill(circle(cx, cy, 3.5), "blue"), ink(circle(cx, cy, 3.5))); }
  return art("Enveloped virus", "coronavirus, influenza, spike protein, virion, envelope", PER, parts);
}
function bacteriophage() {
  const hex = Array.from({ length: 6 }, (_, k) => polar(0, -40, 18, k * 60 + 30)).map((p) => p.join(" ")).join("L");
  return art("Bacteriophage", "phage, T4, virus, tail fibres", PER, [
    fill(`M${hex}Z`, "light"), ink(`M${hex}Z`), ink(rect(-4, -22, 8, 36, 2)), ...[-14, -8, -2, 4, 10].map((y) => fine(ink(seg(-4, y, 4, y)))), ink(`M-12 14L12 14`),
    ink(`M-10 14L-26 30L-30 46M10 14L26 30L30 46M-4 14L-12 32L-12 46M4 14L12 32L12 46`),
  ]);
}
function yeast() {
  return art("Yeast", "Saccharomyces, budding yeast, fungus", PER, [
    ink(ellipse(-8, 6, 32, 26)), ink(`M22 -12A14 12 0 1 1 30 -8`), ...nucleusDrawing(-12, 8, 9, false), ink(circle(8, 18, 4)),
  ]);
}
function neuron() {
  return art("Neuron", "nerve cell, axon, dendrites, synapse", PER, [
        ink(`M-56 -8C-58 -22 -44 -30 -34 -22C-26 -16 -26 0 -34 6C-44 14 -54 8 -56 -8Z`), ink(circle(-43, -8, 5)),
    ink(`M-50 -22L-60 -40L-70 -44M-60 -40L-58 -52M-56 4L-70 18L-76 14M-70 18L-72 30M-40 -26L-34 -44L-26 -48M-34 -44L-40 -54`),
    ink(`M-28 -6L50 -6M-28 -2L50 -2`), ...[-16, 2, 20, 38].map((x) => ink(rect(x, -10, 12, 12, 6))),
    ink(`M50 -4L62 -16L70 -16M62 -16L66 -24M50 -4L62 8L72 8M62 8L64 18`),
  ]);
}
function redBloodCell() {
  return art("Red blood cell", "erythrocyte, blood, RBC", PER, [
    fill(ellipse(0, 0, 40, 40), "light"), ink(ellipse(0, 0, 40, 40)), fine(ink(ellipse(0, 0, 22, 22))), fine(ink(`M-14 -14Q0 -22 14 -14`)),
  ]);
}

export const BIOMOLECULES = [lipidBilayer(), curvedMembrane(), cellMembrane(), phospholipid(), micelle(), liposome(), ionChannel(), receptor(), antibody(), enzyme(), dnaHelix(), alphaHelix(),
  betaStrand(), chromosome(), ribosome()];
export const CELLS = [animalCell(), plantCell(), nucleus(), mitochondrion(), chloroplast(), golgi(), roughER(), smoothER(), vesicle(), centrioles(),
  bacterium(), cocci(), virus(), envelopedVirus(), bacteriophage(), yeast(), neuron(), redBloodCell()];
