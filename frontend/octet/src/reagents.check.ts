// Run: node src/reagents.check.ts. Reagents written over an arrow: the reagent table reads each
// as Name to Structure does, after reagentName takes off its amount and form ("conc.", "(cat.)"), so each gets its
// own formula, as a user writes them.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const dir = new URL("./vendor/opsin/", import.meta.url);
if (!existsSync(new URL("opsin.js", dir))) { console.log("reagents.check: skipped (no OPSIN build)"); process.exit(0); }
const g = globalThis as Record<string, unknown>;
g.document = { documentElement: {}, createElement: () => ({ getContext: () => ({}) }) };
g.getComputedStyle = () => ({ getPropertyValue: () => "10" });
g.window = globalThis;
g.self = { location: { origin: "file://" } };
g.fetch = async (u: URL | string) => new Response(readFileSync(new URL(String(u))), { headers: { "content-type": "application/wasm" } });
const pack = readFileSync(new URL("opsin-data.bin", dir)), files = new Map<string, Int8Array>();
for (let p = 0; ; ) {
  const n = pack.readUInt16BE(p); p += 2;
  if (!n) break;
  const name = pack.toString("latin1", p, p + n); p += n;
  const size = pack.readInt32BE(p); p += 4;
  files.set(name, new Int8Array(pack.buffer, pack.byteOffset + p, size)); p += size;
}
(globalThis as { opsinResource?: unknown }).opsinResource = (name: string) => files.get(name) ?? null;
const opsin = await import(new URL("opsin.js", dir).href);
opsin.init();
const { attachOpsin, nameToSmiles } = await import("./names.ts");
const { DRUGS } = await import("./drugs.ts");
const { ready, smilesWeight } = await import("./chem.ts");
const { conditionItems, formulaWeight, inert, reagentFormula, reagentName } = await import("./stoich.ts");
const { labelSmiles } = await import("./labels.ts");
attachOpsin(opsin, readFileSync(new URL("names.txt", dir), "utf8"), JSON.parse(readFileSync(new URL("./nameindex.json", import.meta.url), "utf8")), DRUGS, JSON.parse(readFileSync(new URL("./abbreviations.json", import.meta.url), "utf8")));
await ready;

// reagentName: amounts and forms off, the reagent kept.
for (const [text, want] of [["conc. H2SO4", "H2SO4"], ["Pd(PPh3)4 (5 mol%)", "Pd(PPh3)4"], ["1.2 equiv NaBH4", "NaBH4"], ["2 M HCl", "HCl"], ["aq. NaOH", "NaOH"], ["TsOH (cat.)", "TsOH"], ["H2SO4", "H2SO4"], ["10 mol% CuI", "CuI"], ["dry THF", "THF"]]) assert.equal(reagentName(text), want, text);

// Each reagent's formula as the reagent table works it out (Editor.tsx gridViews): a formula as written, else Name to
// Structure's reading, else an atom label's.
const weightOf = (text: string) => reagentFormula(text, nameToSmiles, labelSmiles, smilesWeight)?.weight;
const REAGENTS: [string, string][] = [
  ["MeNO2", "CH3NO2"], ["NH4OAc", "C2H7NO2"], ["AcOH", "C2H4O2"], ["Et3N", "C6H15N"], ["Ac2O", "C4H6O3"], ["LiAlH4", "AlH4Li"], ["THF", "C4H8O"],
  ["DMF", "C3H7NO"], ["DMSO", "C2H6OS"], ["MeOH", "CH4O"], ["EtOH", "C2H6O"], ["Et2O", "C4H10O"], ["NaBH4", "BH4Na"], ["K2CO3", "CK2O3"], ["Cs2CO3", "CCs2O3"],
  ["TFA", "C2HF3O2"], ["DIPEA", "C8H19N"], ["DMAP", "C7H10N2"], ["NBS", "C4H4BrNO2"], ["mCPBA", "C7H5ClO3"], ["pyridine", "C5H5N"], ["TsOH", "C7H8O3S"],
  ["Boc2O", "C10H18O5"], ["n-BuLi", "C4H9Li"], ["DCM", "CH2Cl2"], ["CH2Cl2", "CH2Cl2"], ["conc. H2SO4", "H2SO4"], ["Pd(PPh3)4 (5 mol%)", "C72H60P4Pd"],
];
// Compared by molar mass: the table shows a formula as it was written (LiAlH4), and others in Hill order (AlH4Li).
const wrong = REAGENTS.flatMap(([text, want]) => { const got = weightOf(text), w = formulaWeight(want)!; return got !== undefined && Math.abs(got - w) < 0.01 ? [] : [`${text}: ${got?.toFixed(2) ?? "nothing"} (want ${want}, ${w.toFixed(2)})`]; });
assert.deepEqual(wrong, [], "reagents read wrongly");
// Names without three letters in a row, as Name to Structure reads them: deuterated D2O and CD3OD, HF·pyridine.
for (const [text, want] of [["D2O", 20.03], ["CD3OD", 36.07], ["HF·py", 99.11]] as const) assert.ok(Math.abs((weightOf(text) ?? 0) - want) < 0.01, `${text}: ${weightOf(text)}`);
// A mixture is not one compound; a line splits at commas outside brackets; the atmosphere's gas is not a reagent.
for (const mix of ["toluene/EtOH/H2O (4:1:1)", "toluene/EtOH/H2O", "THF/H2O"]) assert.equal(weightOf(mix), undefined, mix);
assert.deepEqual(conditionItems("toluene/EtOH/H2O (4:1:1, 30 mL), 80 °C; 12 h"), ["toluene/EtOH/H2O (4:1:1, 30 mL)", "80 °C", "12 h"]);
for (const gas of ["N2", "Ar", "argon", "air", "under N2"]) assert.ok(inert(gas), gas);
for (const reagent of ["H2", "O2", "CO", "NH3"]) assert.ok(!inert(reagent), reagent);
// Issue 131: before the names engine has loaded (read gives nothing), Octet's abbreviations are read before the label
// reader, so THF is C4H8O and never tritium fluoride. A drawn label still reads T as tritium. AcOH is acetic acid, as
// text and as a drawn label; conditions get no formula.
{
  const early = (text: string) => reagentFormula(text, () => undefined, labelSmiles, smilesWeight);
  for (const [text, want] of [["THF", "C4H8O"], ["DMF", "C3H7NO"], ["DCM", "CH2Cl2"], ["DMAP", "C7H10N2"], ["dry THF", "C4H8O"], ["AcOH", "C2H4O2"], ["K2CO3 (2 eq.)", "K2CO3"], ["cat. H2SO4", "H2SO4"], ["H2SO4 (cat.)", "H2SO4"], ["conc. HCl", "HCl"], ["aq. NaOH", "NaOH"], ["HCl (aq)", "HCl"], ["1 M NaOH", "NaOH"], ["1.5 equiv NaBH4", "NaBH4"]] as const) {
    const got = early(text), w = formulaWeight(want);
    assert.ok(got && w && Math.abs(got.weight - w) < 0.01, `${text}: ${got?.formula ?? "nothing"}`);
  }
  for (const t of ["reflux", "rt", "0 °C", "-78 °C", "2 h", "overnight"]) assert.equal(early(t), undefined, t);
  assert.equal(labelSmiles("THF"), "[T]F", "a drawn label THF still reads T as tritium");
  assert.equal(labelSmiles("CT3"), "C([T])([T])([T])");
  assert.equal(smilesWeight(labelSmiles("AcOH")!)?.formula, "C2H4O2", "a drawn AcOH label");
  assert.equal(smilesWeight(labelSmiles("MeO2CCH2")!)?.formula, "C3H6O2", "a label that ends in CH2 reads as before");
}
// Decision 0024: the reagent table is laid out again on every change, and with words Name to Structure does not know
// written over the arrow it is as quick as in 1.1.1. 1.1.1 read each item as a formula, else as a label. Before this
// check, the table asked Name to Structure for every word again on every layout (0.06 to 0.56 ms, 5 to 44 times
// 1.1.1's). Both are timed here on this computer, in turns, the best of 6 runs of at least 20 ms each: half as long
// again at most, for noise.
{
  const { gridViews } = await import("./gridview.ts");
  const { formulaWeight: weight } = await import("./stoich.ts");
  const then = (item: string) => {
    const plain = item.replace(/^\d+\s+(?=\S)/, ""), w = weight(plain), smiles = w === undefined ? labelSmiles(plain) : undefined;
    return w !== undefined ? { formula: plain.replace(/\s+/g, ""), weight: w } : smiles ? smilesWeight(smiles) : undefined;
  };
  const now = (item: string) => reagentFormula(item, nameToSmiles, labelSmiles, smilesWeight);
  // A + B → C, with the conditions over and under the arrow.
  const steps = [{ kind: "structure", atoms: [0], box: [0, -0.5, 1, 0.5] }, { kind: "structure", atoms: [1], box: [2, -0.5, 3, 0.5] }, { kind: "arrow", id: 9, box: [4, -0.5, 6, 0.5] }, { kind: "structure", atoms: [2], box: [7, -0.5, 8, 0.5] }];
  const above = ["NaBH4, MeOH, 0 °C to rt, 2 h", "reflux, overnight, then workup", "sonication, 30 min, Lindlar, hexanes"], conditions = above.map((_, k) => ({ kind: "text", id: 20 + k, box: [4, 1 + k, 6, 2 + k] }));
  const m = { atoms: [], bonds: [], captions: above.map((text, k) => ({ id: 20 + k, text, x: 0, y: 0 })), arrows: [{ id: 9, kind: "reaction", from: [0, 0], to: [1, 0] }], grids: [{ arrow: 9, typed: { "r:S0": { mass: 1 } } }] } as never;
  const layout = (reagent: (item: string) => { formula: string; weight: number } | undefined) => gridViews(m, {
    reaction: () => ({ steps, arrows: [9] }) as never, steps: () => [{ arrow: 9, reactants: [steps[0], steps[1]], products: [steps[3]], above: conditions, below: [] }] as never,
    structure: (atoms) => ({ formula: `S${atoms[0]}`, weight: 100 }), reagent, captionBox: () => undefined, nameWidth: () => 1, captionSize: 10, perPt: 0.05, experiment: false,
  });
  assert.deepEqual(layout(now)[0].all.map((c) => c.key), ["r:S0", "r:S1", 'r:"NaBH4"', 'r:"MeOH"', "p:S2"], "only reagents have columns");
  // Timed again, up to 3 times, when another program on the computer slowed one of them.
  let was = 0, is = Infinity;
  for (let tries = 0; tries < 3 && !(is < 1.5 * was); tries++) {
    const best = [Infinity, Infinity];
    for (let k = 0; k < 6; k++) for (const [j, reagent] of [then, now].entries()) {
      let n = 0;
      const t0 = performance.now();
      do { layout(reagent); n++; } while (performance.now() - t0 < 20);
      best[j] = Math.min(best[j], (performance.now() - t0) / n);
    }
    [was, is] = best;
  }
  assert.ok(is < 1.5 * was, `a layout takes ${is.toFixed(4)} ms, 1.1.1's way ${was.toFixed(4)} ms`);
}
console.log(`reagents.check: ${REAGENTS.length} reagents read right`);
