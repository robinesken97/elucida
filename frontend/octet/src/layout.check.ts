// Run: node src/layout.check.ts. Fails loudly if text from outside (a paste, a typed SMILES, a file) can stop the
// editor. Each crowded structure below ran for minutes in Indigo's layout with no cap; each must now be laid out or
// refused in under two seconds. Real structures must be laid out exactly as Indigo lays them out with no cap (before
// Octet tidies a crowded layout and places the wedges: src/natural.check.ts).
// The structures run in a worker thread, so a layout that never ends stops the check instead of hanging it.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { Worker, isMainThread, parentPort } from "node:worker_threads";

const BOUND = 2000; // ms for each structure
const ph = "c1ccccc1", pph3 = "P(c1ccccc1)(c1ccccc1)c1ccccc1", on = (group: string, n: number) => `(${group})`.repeat(n);
let dendrimer = "C";
for (let k = 0; k < 5; k++) dendrimer = "C" + on(dendrimer, 3);

// Laid out, or refused, in under BOUND ms.
const crowded: [string, string][] = [
  ["a ring atom with five phenyls", "c1ccccc1" + on(ph, 5)],
  ["a cyclohexane atom with five cyclohexyls", "C1CCCCC1" + on("C2CCCCC2", 5)],
  ["a carbon with 50 phenyls", "C" + on(ph, 50)],
  ["a carbon with 99 chlorines next to tBu", "CC(C)(C)C" + on("Cl", 99)],
  ["a carbon with 99 methyls next to trityl", "C(c1ccccc1)(c1ccccc1)(c1ccccc1)C" + on("C", 99)],
  ["a carbon with 33 phenyls (199 atoms)", "C" + on(ph, 33)],
  ["ten rings with five phenyls each", Array(10).fill("c1ccccc1" + on(ph, 5)).join(".")],
  ["a carbon with 99 phenyls (595 atoms)", "C" + on(ph, 99)],
  ["a carbon with 166 phenyls (997 atoms)", "C" + on(ph, 166)],
  ["75 diphenylmethylenes in a chain (977 atoms)", "C" + "C(c1ccccc1)(c1ccccc1)".repeat(75) + "C"],
  ["a branched dendrimer (364 atoms)", dendrimer],
  ["a 1,000-atom chain", "C".repeat(1000)],
  ["20,000 characters on one line that are not chemistry", "x".repeat(20_000)],
  ["a 300,000-character file that is not chemistry", "<" + "abc def\n".repeat(37_500).slice(1)],
];
// Refused before Indigo reads them, with the reason Octet shows.
const tooBig: [string, string, RegExp][] = [
  ["a carbon with 333 phenyls (1,999 atoms)", "C" + on(ph, 333), /more than 1,000 atoms/],
  ["a 1,001-atom chain", "C".repeat(1001), /more than 1,000 atoms/],
  ["a 20,001-character line", "x".repeat(20_001), /more than 20,000 characters/],
  ["a 300,001-character file", "C\n".repeat(150_001).slice(1), /more than 300,000 characters/],
];
// Laid out as Indigo lays them out with no cap.
const real: [string, string][] = [
  ["paracetamol", "CC(=O)Nc1ccc(O)cc1"],
  ["ibuprofen", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"],
  ["morphine", "CN1CC[C@]23c4c5ccc(O)c4O[C@H]2[C@@H](O)C=C[C@H]3[C@H]1C5"],
  ["strychnine", "O=C7N2c1ccccc1[C@@]64[C@@H]2[C@@H]3[C@@H](OC/C=C5\\[C@@H]3C[C@@H]6N(CC4)C5)C7"],
  ["paclitaxel", "CC1=C2[C@@]([C@]([C@H]([C@@H]3[C@]4([C@H](OC4)C[C@@H]([C@]3(C(=O)[C@@H]2OC(=O)C)C)O)OC(=O)C)OC(=O)c5ccccc5)(C[C@@H]1OC(=O)[C@H](O)[C@@H](NC(=O)c6ccccc6)c7ccccc7)O)(C)C"],
  ["vancomycin", "CC1C(C(CC(O1)OC2C(C(C(OC2OC3=C4C=C5C=C3OC6=C(C=C(C=C6)C(C(C(=O)NC(C(=O)NC5C(=O)NC7C8=CC(=C(C=C8)O)C9=C(C=C(C=C9O)O)C(NC(=O)C(C(C1=CC(=C(O4)C=C1)Cl)O)NC7=O)C(=O)O)CC(=O)N)NC(=O)C(CC(C)C)NC)O)Cl)CO)O)O)(C)N)O"],
  ["Pd(PPh3)4", `[Pd](${pph3})(${pph3})(${pph3})${pph3}`],
  ["RhCl(PPh3)3", `Cl[Rh](${pph3})(${pph3})${pph3}`],
  ["Grubbs II", "CC1=CC(C)=C(N2CCN(C3=C(C)C=C(C)C=C3C)C2=[Ru](Cl)(Cl)(=CC4=CC=CC=C4)P(C5CCCCC5)(C6CCCCC6)C7CCCCC7)C(C)=C1"],
  ["BINAP", "c1ccc(cc1)P(c2ccccc2)c3ccc4ccccc4c3-c5c(ccc6ccccc56)P(c7ccccc7)c8ccccc8"],
  ["tetraphenylporphyrin", "c1ccc(cc1)-c2c3ccc(n3)c(-c4ccccc4)c5ccc([nH]5)c(-c6ccccc6)c7ccc(n7)c(-c8ccccc8)c9ccc2[nH]9"],
  ["tetrakis(trityl)methane", "C" + on("C(c1ccccc1)(c1ccccc1)c1ccccc1", 4)],
  ["W(CO)6", "O#C[W](C#O)(C#O)(C#O)(C#O)C#O"],
  ["a 100-residue polyleucine (902 atoms)", "N" + "C(CC(C)C)C(=O)N".repeat(100) + "CC(=O)O"],
];

if (isMainThread) {
  const worker = new Worker(new URL(import.meta.url));
  let timer: ReturnType<typeof setTimeout> | undefined, current = "Loading Indigo";
  const arm = (ms: number) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      console.error(`layout.check: ${current} took more than ${ms} ms`);
      void worker.terminate().then(() => process.exit(1));
    }, ms);
  };
  arm(60_000);
  worker.on("message", (m: { start?: string; done?: string; ms?: number; outcome?: string; end?: true }) => {
    if (m.start) { current = m.start; arm(BOUND); }
    if (m.done) { clearTimeout(timer); console.log(`layout.check: ${m.done}: ${m.ms} ms, ${m.outcome}`); }
    if (m.end) console.log("layout.check: no text stops the editor, and real structures lay out as before");
  });
  worker.on("error", (e) => { clearTimeout(timer); console.error(e); process.exitCode = 1; });
} else {
  // chem.ts reads the drawing tokens and loads Indigo's wasm as a browser does; these stand in for the browser.
  const g = globalThis as Record<string, unknown>;
  g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
  g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
  g.window = globalThis;
  g.self = { location: { origin: "file://" } };
  g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
  const { cipOf, indigoLayout, parseStructure, ready, stereoFacts, toInchi } = await import("./chem.ts");
  const { problems, WARNING_TYPES } = await import("./check.ts");
  const shown = new Set(WARNING_TYPES.filter((w) => w.on).map((w) => w.id));
  // A second Indigo, for the layout with no cap.
  const indigo = await (await import(new URL("../node_modules/indigo-ketcher/indigo-ketcher-norender.js", import.meta.url).href)).default();
  await ready;
  const post = (m: object) => parentPort!.postMessage(m);
  const timed = (name: string, run: () => string) => {
    post({ start: name });
    const t = performance.now(), outcome = run();
    post({ done: name, ms: Math.round(performance.now() - t), outcome });
  };
  const uncapped = (smiles: string): number[][] => {
    const o = new indigo.MapStringString();
    try {
      o.set("output-content-type", "application/json");
      o.set("dearomatize-on-load", "true");
      const ket = JSON.parse(JSON.parse(indigo.layout(smiles, "ket", o)).struct);
      return (ket.root.nodes as { $ref: string }[]).flatMap(({ $ref }) => (ket[$ref]?.type === "molecule" ? ket[$ref].atoms.map((a: { location: number[] }) => a.location) : []));
    } finally {
      o.delete();
    }
  };
  // A molfile with no coordinates, as another program might paste it.
  const molfile = (smiles: string) => { const o = new indigo.MapStringString(); try { return indigo.convert(smiles, "molfile", o); } finally { o.delete(); } };
  const tryParse = (text: string) => {
    try { return `${parseStructure(text).atoms.length} atoms`; } catch (e) { return `not read (${e instanceof Error ? e.message.slice(0, 60) : e})`; }
  };

  for (const [name, smiles] of crowded) timed(name, () => tryParse(smiles));
  timed("a ring atom with five phenyls, as a molfile", () => tryParse(molfile(crowded[0][1])));
  for (const [name, text, why] of tooBig) timed(name, () => { assert.throws(() => parseStructure(text), (e) => e instanceof RangeError && why.test(e.message)); return "refused"; });
  const at = (p: number[]) => p.slice(0, 2).map((v) => v.toFixed(4));
  for (const [name, smiles] of real)
    timed(name, () => { parseStructure(smiles); assert.deepEqual(indigoLayout(smiles).atoms.map((a) => at(a.location)), uncapped(smiles).map(at), name); return "as with no cap"; });
  // Issue #9: Name to Structure's Taxol and strychnine show none of the warnings shown by default (no atom on a
  // bond, no wedge between two stereocentres), and their drawn H atoms keep each stereocentre's configuration.
  const bare = (smiles: string) => { const o = new indigo.MapStringString(); try { o.set("output-content-type", "application/json"); return JSON.parse(JSON.parse(indigo.layout(smiles, "ket", o)).struct); } finally { o.delete(); } };
  for (const [name, smiles] of real.filter(([n]) => n === "strychnine" || n === "paclitaxel"))
    timed(`${name}, warnings`, () => {
      const m = parseStructure(smiles);
      assert.deepEqual(problems(m, stereoFacts(m)).filter((p) => shown.has(p.type)).map((p) => p.message), [], name);
      assert.equal(toInchi(m), toInchi(smiles), name);
      return `${m.atoms.length - bare(smiles).mol0.atoms.length} H drawn, no warnings`;
    });
  // A structure only read for its InChI (screen-reader names, Structure to Name) is Indigo's layout, untidied: the
  // tidy above takes a hundred times as long.
  for (const [name, smiles] of real.filter(([n]) => n === "paclitaxel"))
    timed(`${name}, read only`, () => {
      const m = parseStructure(smiles, false);
      assert.deepEqual(m.atoms.map((a) => at(a.location)), indigoLayout(smiles).atoms.map((a) => at(a.location)), name);
      assert.equal(toInchi(m), toInchi(parseStructure(smiles)), name);
      return "Indigo's layout, same InChI";
    });
  // A wedge from a stereocentre to a planar N (a nucleoside's base, an amide) joins no second stereocentre: no warning,
  // and no H is drawn for it. A steroid's ring-fusion H that has to go inside a ring sits off the ring's centre.
  const planarN: [string, string][] = [
    ["zidovudine", "CC1=CN([C@H]2C[C@H](N=[N+]=[N-])[C@@H](CO)O2)C(=O)NC1=O"],
    ["valsartan", "CCCCC(=O)N(Cc1ccc(cc1)-c1ccccc1-c1nn[nH]n1)[C@@H](C(C)C)C(O)=O"],
  ];
  for (const [name, smiles] of planarN)
    timed(`${name}, warnings`, () => {
      const m = parseStructure(smiles);
      assert.equal(m.atoms.length, bare(smiles).mol0.atoms.length, `${name}: no H drawn`);
      assert.deepEqual(problems(m, stereoFacts(m)).filter((p) => shown.has(p.type)).map((p) => p.message), [], name);
      return "no H drawn, no warnings";
    });
  // An amine N that can invert (LSD's N6, a tropane's N-methyl, a ring fusion's N) is no stereocentre, so a wedge from a
  // carbon to it gives no warning, and the carbons' R and S stay. A bridgehead N that cannot invert (strychnine's N4,
  // quinine's N1, Tröger's base) still is one.
  const amineN: [string, string, string[]][] = [
    ["LSD", "CCN(CC)C(=O)[C@H]1CN([C@@H]2Cc3c[nH]c4c3c(ccc4)C2=C1)C", ["R", "R"]],
    ["atropine", "CN1[C@@H]2CC[C@H]1CC(C2)OC(=O)C(CO)c3ccccc3", ["R", "S"]],
    ["scopolamine", "CN1[C@@H]2C[C@@H](C[C@H]1[C@H]3[C@@H]2O3)OC(=O)[C@H](CO)c4ccccc4", ["R", "r", "S", "S", "R", "S"]],
    ["dextromethorphan", "CN1CC[C@@]23CCCC[C@@H]2[C@@H]1Cc4c3cc(cc4)OC", ["S", "S", "S"]],
    ["physostigmine", "CNC(=O)Oc1ccc2c(c1)[C@]3(C)CCN(C)[C@@H]3N2C", ["S", "R"]],
    ["castanospermine", "O[C@H]1CCN2C[C@H](O)[C@@H](O)[C@H](O)[C@@H]12", ["S", "S", "R", "R", "R"]],
    ["swainsonine", "O[C@@H]1CCN2C[C@@H](O)[C@@H](O)[C@@H]12", ["R", "R", "S", "R"]],
    ["sparteine", "C1CCN2C[C@@H]3C[C@H](C2C1)CN4[C@@H]3CCCC4", ["S", "S", "R"]],
  ];
  for (const [name, smiles, cip] of amineN)
    timed(`${name}, warnings`, () => {
      // Indigo's own drawing has the wedge to the N; Octet's (placeWedges) may move it.
      const raw = indigoLayout(smiles), m = parseStructure(smiles);
      assert.ok(raw.bonds.some((b) => b.stereo && b.atoms.some((i) => raw.atoms[i].label === "N")), `${name}: a wedge to the N`);
      for (const [x, f] of [raw, m].map((x) => [x, stereoFacts(x)] as const)) {
        assert.deepEqual([...f.centres].filter((i) => x.atoms[i].label === "N"), [], `${name}: the N is no stereocentre`);
        assert.deepEqual(problems(x, f).filter((p) => p.type === "between" || p.type === "backwards").map((p) => p.message), [], name);
      }
      assert.deepEqual(cipOf(m).atoms.filter(Boolean), cip, name);
      return "no warnings";
    });
  timed("strychnine, bridgehead N", () => {
    const m = parseStructure(real.find(([n]) => n === "strychnine")![1]);
    assert.equal([...stereoFacts(m).centres].filter((i) => m.atoms[i].label === "N").length, 1, "N4 is a stereocentre");
    return "N4 a stereocentre";
  });
  timed("Tröger's base, bridgehead N", () => {
    const m = parseStructure("Cc1ccc2c(c1)CN1Cc3cc(C)ccc3N(C2)C1");
    for (const a of m.atoms) if (a.label === "N") a.enhanced = "&1";
    const f = stereoFacts(m, true);
    assert.equal([...f.centres].filter((i) => m.atoms[i].label === "N").length, 2, "both N are stereocentres");
    assert.ok(!problems(m, f).some((p) => /not a stereocentre/.test(p.message)), "no flag on a non-stereocentre");
    return "both N stereocentres";
  });
  timed("quinine, wedge to the bridgehead N", () => {
    const smiles = "COc1ccc2nccc([C@@H](O)[C@@H]3C[C@@H]4CCN3C[C@@H]4C=C)c2c1", m = parseStructure(smiles);
    assert.deepEqual(problems(m, stereoFacts(m)).filter((p) => shown.has(p.type)).map((p) => p.message), [], "quinine");
    assert.equal(toInchi(m), toInchi(smiles));
    return `${m.atoms.length - bare(smiles).mol0.atoms.length} H drawn, no warnings`;
  });
  timed("hydrocortisone, ring-fusion H", () => {
    const smiles = "C[C@]12CCC(=O)C=C1CC[C@@H]3[C@@H]2[C@H](C[C@]4([C@H]3CC[C@@]4(C(=O)CO)O)C)O", m = parseStructure(smiles), n = bare(smiles).mol0.atoms.length;
    assert.equal(toInchi(m), toInchi(smiles));
    for (const [h, a] of m.atoms.slice(n).map((a, k) => [n + k, a] as const)) {
      const d = m.atoms.flatMap((o, j) => (j === h || m.bonds.some((b) => b.atoms.includes(h) && b.atoms.includes(j)) ? [] : [Math.hypot(o.location[0] - a.location[0], o.location[1] - a.location[1])]));
      assert.ok(Math.min(...d) > 0.8, `the H is off every atom (${Math.min(...d).toFixed(2)} bond lengths)`);
      assert.ok(d.filter((r) => r < 1.05).length < 4, "the H is off the ring's centre");
    }
    return `${m.atoms.length - n} H drawn`;
  });
  post({ end: true });
}
