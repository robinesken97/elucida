// Stoichiometry, as ChemDraw's Analyze Stoichiometry grid works it out: for each reactant, what was typed (mass,
// moles, equivalents, volume with density or molarity, purity) gives its moles and the rest; equivalents are relative
// to the limiting reactant; each product's expected amount follows from the limiting reactant times the product's
// equivalents (its coefficient, 1 unless typed, as ChemDraw's product Equivalents row), and a measured mass gives its
// yield. A product's mass typed (its Expected mass) is the mass wanted: with no reactant amount, it sets the scale
// (issue 136). Amounts are kept in base units: g, mol, mL, g/mL, mol/L, and fractions for purity.
// Each reactant has a role: a reactant (as every column of ChemDraw's grid), a catalyst (its equivalents in mol%) or a
// solvent, which is never limiting, never sets the scale and has no equivalents until some are typed or written. The
// solvents give the concentration of the limiting reactant, and a concentration typed gives the volume of the solvent
// with none.

import type { Grid, GridConditions, GridRole } from "./render.ts";
import { oneLine } from "./experiment.ts";
import ABBREVIATIONS from "./abbreviations.json" with { type: "json" };
import { LIQUIDS, type Liquid } from "./liquids.ts";

export type Field = "mass" | "moles" | "equiv" | "volume" | "density" | "molarity" | "purity" | "measured";
export type Typed = Partial<Record<Field, number>>;
// given: the equivalents its text gives ("K2CO3 (2 eq.)"), used when none are typed. coef: its coefficient in the
// scheme (2 in 2 A + B → C), on each part of the equation once one is written there (1 where none is). density: a
// known liquid's listed density (liquids.ts), used when none is typed. role: a reactant's role; unset is a reactant.
// carried: a reactant's moles from the step before (its Measured mass there), used when none of its amounts is typed.
export type Component = { key: string; mw: number; product: boolean; typed: Typed; given?: number; coef?: number; density?: number; role?: GridRole; carried?: number };
// conc: a solvent's, the concentration of the limiting reactant in all the solvents (mol/L).
export type Solved = {
  mass?: number; moles?: number; equiv?: number; volume?: number; density?: number; molarity?: number; purity: number; conc?: number;
  expectedMass?: number; expectedMoles?: number; measured?: number; productMoles?: number; yield?: number;
};

// The limiting reactant: the one set, when it has the Reactant role; else the first with the Reactant role; else the
// first that is not a solvent. A catalyst or a solvent set as limiting (its role changed since) is not.
// One pass, with nothing made: the table is laid out again on every change.
export function limitingOf<T extends { key: string; product: boolean; role?: GridRole }>(components: T[], limiting?: string): T | undefined {
  let reactant: T | undefined, first: T | undefined;
  for (const c of components) {
    if (c.product || c.role === "solvent") continue;
    if ((c.role ?? "reactant") === "reactant") {
      if (c.key === limiting) return c;
      reactant ??= c;
    }
    first ??= c;
  }
  return reactant ?? first;
}
// Each component's amounts. limiting: the reactant the others are measured against (limitingOf). conc: the
// concentration typed (mol/L).
export function solve(components: Component[], limiting?: string, conc?: number): Record<string, Solved> {
  const out: Record<string, Solved> = {};
  const reactants = components.filter((c) => !c.product), lim = limitingOf(components, limiting);
  // Its equivalents: typed, else as its text gives them, else its coefficient over the limiting reactant's (issue 133).
  const ref = lim?.coef ?? 1, given = (c: Component) => c.typed.equiv ?? c.given ?? (c.coef === undefined ? undefined : c.coef / ref);
  // A reactant's moles from what was typed: moles, mass, volume with density, or volume with molarity.
  const own = (c: Component): number | undefined => {
    const t = c.typed, purity = t.purity ?? 1, density = t.density ?? c.density;
    if (t.moles !== undefined) return t.moles;
    if (t.mass !== undefined && c.mw > 0) return (t.mass * purity) / c.mw;
    if (t.volume !== undefined && density !== undefined && c.mw > 0) return (t.volume * density * purity) / c.mw;
    if (t.volume !== undefined && t.molarity !== undefined) return (t.volume / 1000) * t.molarity;
    return c.carried;
  };
  let limMoles = lim ? own(lim) : undefined;
  // With the limiting reactant's amount unknown, another reactant with an amount and equivalents fixes it.
  if (limMoles === undefined) for (const c of reactants) { const m = c.role === "solvent" ? undefined : own(c), e = given(c); if (m !== undefined && e) { limMoles = m / e; break; } }
  // With no reactant amount, a product's mass wanted fixes it.
  if (limMoles === undefined) for (const c of components) { const e = given(c) ?? 1; if (c.product && c.typed.mass !== undefined && c.mw > 0 && e > 0) { limMoles = c.typed.mass / c.mw / e; break; } }
  for (const c of reactants) {
    const t = c.typed, purity = t.purity ?? 1, density = t.density ?? c.density, e = c === lim ? 1 : c.role === "solvent" ? given(c) : given(c) ?? 1;
    let moles = own(c);
    if (moles === undefined && limMoles !== undefined && e !== undefined) moles = limMoles * e;
    const mass = moles !== undefined && c.mw > 0 ? (moles * c.mw) / purity : t.mass;
    const volume = t.volume ?? (mass !== undefined && density ? mass / density : moles !== undefined && t.molarity ? (moles / t.molarity) * 1000 : undefined);
    out[c.key] = { moles, mass, volume, purity, density, molarity: t.molarity, equiv: moles !== undefined && limMoles ? moles / limMoles : given(c) };
  }
  // The solvents: a concentration typed gives the first with no volume the rest of the volume it needs; then the
  // concentration in all of them.
  if (reactants.some((c) => c.role === "solvent")) {
    const solvents = reactants.filter((c) => c.role === "solvent"), volumeOf = () => solvents.reduce((v, c) => v + (out[c.key].volume ?? 0), 0);
    const free = conc !== undefined && limMoles !== undefined ? solvents.find((c) => out[c.key].volume === undefined) : undefined;
    if (free && limMoles !== undefined && conc !== undefined) {
      const o = out[free.key], volume = (limMoles / conc) * 1000 - volumeOf(), mass = o.density ? volume * o.density : undefined, moles = mass !== undefined && free.mw > 0 ? (mass * o.purity) / free.mw : undefined;
      if (volume > 0) out[free.key] = { ...o, volume, mass, moles, equiv: moles !== undefined && limMoles ? moles / limMoles : o.equiv };
    }
    const total = volumeOf();
    for (const c of solvents) out[c.key].conc = limMoles !== undefined && total > 0 ? limMoles / (total / 1000) : undefined;
  }
  for (const c of components.filter((x) => x.product)) {
    const purity = c.typed.purity ?? 1, equiv = given(c) ?? 1, expectedMoles = limMoles !== undefined ? limMoles * equiv : undefined, expectedMass = expectedMoles !== undefined ? expectedMoles * c.mw : undefined;
    const productMoles = c.typed.measured !== undefined && c.mw > 0 ? (c.typed.measured * purity) / c.mw : undefined;
    out[c.key] = { purity, equiv, expectedMoles, expectedMass, measured: c.typed.measured, productMoles, yield: productMoles !== undefined && expectedMoles ? productMoles / expectedMoles : undefined };
  }
  return out;
}

// Units each field can be typed and shown in, as multiples of its base unit.
const UNITS: Record<Field, Record<string, number>> = {
  mass: { kg: 1000, g: 1, mg: 1e-3, µg: 1e-6, ug: 1e-6 },
  measured: { kg: 1000, g: 1, mg: 1e-3, µg: 1e-6, ug: 1e-6 },
  moles: { mol: 1, mmol: 1e-3, µmol: 1e-6, umol: 1e-6, nmol: 1e-9 },
  volume: { L: 1000, l: 1000, mL: 1, ml: 1, µL: 1e-3, uL: 1e-3, ul: 1e-3 },
  density: { "g/mL": 1, "g/ml": 1, "g/cm3": 1, "kg/L": 1 },
  molarity: { M: 1, "mol/L": 1, mM: 1e-3 },
  equiv: { eq: 1, equiv: 1, "mol%": 0.01, "": 1 },
  purity: { "%": 0.01 },
};
// A typed amount in base units: "250 mg", "1.2 eq", "0.5 mL", "98%". A bare number is taken in the field's usual unit
// (mmol, mL, g/mL, M, eq, %; a mass in g as ChemDraw takes it, or in mg as Settings > Typing can say, issue 134).
// Undefined when it is not a finite number of 0 or more, with a unit the field takes. Greek mu (μ, as \mu types it) is
// the micro sign.
export function parseAmount(text: string, field: Field, mass: "g" | "mg" = "g"): number | undefined {
  const m = /^\s*(\d+(?:\.\d+)?|\.\d+)(?:e([+-]?\d+))?\s*([a-zA-Zµ%/0-9]*)\s*$/.exec(text.replace(",", ".").replace(/\u03bc/g, "µ"));
  if (!m) return undefined;
  const value = Number(m[1]) * 10 ** Number(m[2] ?? 0), unit = m[3], units = UNITS[field];
  const plain: Record<Field, string> = { mass, measured: mass, moles: "mmol", volume: "mL", density: "g/mL", molarity: "M", equiv: "eq", purity: "%" };
  const k = unit === "" ? units[plain[field]] : units[unit];
  return k === undefined || !(value >= 0) || !Number.isFinite(value * k) ? undefined : value * k;
}
// An amount for the grid in the unit that reads best (250 mg, 1.25 mmol, 0.50 mL), three significant figures.
// A catalyst's equivalents ("mol%") in mol%: 0.05 is 5.00 mol%.
export function formatAmount(value: number | undefined, field: Field | "mw" | "yield" | "mol%"): string {
  if (value === undefined || !Number.isFinite(value)) return "";
  const sig = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2));
  if (field === "mw") return value.toFixed(2);
  if (field === "mol%") return `${(value * 100).toFixed(2)} mol%`;
  if (field === "yield" || field === "purity") return `${sig(value * 100)}%`;
  if (field === "equiv") return value.toFixed(2);
  const ladders: Partial<Record<Field, [string, number][]>> = {
    mass: [["kg", 1000], ["g", 1], ["mg", 1e-3], ["µg", 1e-6]], measured: [["kg", 1000], ["g", 1], ["mg", 1e-3], ["µg", 1e-6]],
    moles: [["mol", 1], ["mmol", 1e-3], ["µmol", 1e-6], ["nmol", 1e-9]], volume: [["L", 1000], ["mL", 1], ["µL", 1e-3]],
  };
  const ladder = ladders[field as Field];
  if (!ladder) return `${sig(value)} ${field === "density" ? "g/mL" : "M"}`;
  const [unit, k] = ladder.find(([, f]) => value >= f) ?? ladder[ladder.length - 1];
  return `${sig(value / k)} ${unit}`;
}

// Standard atomic weights (IUPAC 2021, abridged), for reagents written as formulas (H2O, NaBH4, Sc(OTf)3).
const WEIGHT: Record<string, number> = {
  H: 1.008, Li: 6.94, B: 10.81, C: 12.011, N: 14.007, O: 15.999, F: 18.998, Na: 22.99, Mg: 24.305, Al: 26.982, Si: 28.085,
  P: 30.974, S: 32.06, Cl: 35.45, K: 39.098, Ca: 40.078, Ti: 47.867, Cr: 51.996, Mn: 54.938, Fe: 55.845, Co: 58.933,
  Ni: 58.693, Cu: 63.546, Zn: 65.38, Se: 78.971, Br: 79.904, Rb: 85.468, Ru: 101.07, Rh: 102.91, Pd: 106.42, Ag: 107.87,
  Sn: 118.71, I: 126.9, Cs: 132.91, Ir: 192.22, Pt: 195.08, Au: 196.97, Hg: 200.59, Pb: 207.2, Os: 190.23, W: 183.84,
  Be: 9.0122, Sc: 44.956, V: 50.942, Ga: 69.723, Ge: 72.63, As: 74.922, Sr: 87.62, Y: 88.906, Zr: 91.224, Nb: 92.906,
  Mo: 95.95, Cd: 112.41, In: 114.82, Sb: 121.76, Te: 127.6, Ba: 137.33, La: 138.91, Ce: 140.12, Sm: 150.36, Eu: 151.96,
  Gd: 157.25, Yb: 173.05, Hf: 178.49, Ta: 180.95, Re: 186.21, Tl: 204.38, Bi: 208.98,
};
// A reagent as text over an arrow, as the reagent table reads it: without an amount before it ("1.2 equiv", "10 mol%",
// "2 M"), a word for its form or use ("conc.", "aq.", "sat.", "dil.", "dry", "glacial", "fuming", "cat.", "excess",
// "then"), or an amount, "cat." or a note in brackets after it, so "conc. H2SO4", "Pd(PPh3)4 (5 mol%)" and "nBuLi (2.5 M
// in hexanes)" read as H2SO4, Pd(PPh3)4 and nBuLi. A formula's own brackets stay (Ca(OH)2).
export function reagentName(text: string): string {
  let t = text.trim();
  for (let k = 0; k < 4; k++) {
    const was = t;
    t = t.replace(/^\d+(?:\.\d+)?\s*(?:equiv\.?|eq\.?|mol\s?%|M|N|mmol|mol|mg|g|mL|ml|µL|uL)\s+(?=\S)/i, "").replace(/^(?:conc\.?|concd\.?|concentrated|aq\.?|aqueous|sat\.?|satd\.?|saturated|dil\.?|dilute|dry|anhydrous|abs\.?|absolute|glacial|fuming|neat|cat\.?|catalytic|excess|xs\.?|then|fresh(?:ly distilled)?)\s+(?=\S)/i, "");
    t = t.replace(/\s*\((?:\d+(?:\.\d+)?\s*(?:equiv\.?|eq\.?|mol\s?%|M|N|mmol|mol|mg|g|mL|ml)|cat\.?|catalytic|conc\.?|aq\.?|excess|xs\.?)\)\s*$|\s+\([^()]*\)$/i, "").trim();
    if (t === was) break;
  }
  return t;
}
// A number in front of a reagent's name ("2 HCl", "0.5 H2", "1/2 O2", "½ O2") or on its own ("2", before a structure
// in a scheme): the text after it and the number, as a coefficient (issue 133). The text and undefined when there is
// none.
const FRACTIONS: Record<string, number> = { "½": 1 / 2, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 1 / 4, "¾": 3 / 4 };
export function coefficient(text: string): [string, number | undefined] {
  const m = /^(?:(\d{1,3})\s*\/\s*(\d{1,3})|(\d+(?:\.\d+)?)|([½⅓⅔¼¾]))(?:\s+(?=\S)|\s*$)/.exec(text);
  if (!m) return [text, undefined];
  const v = m[4] ? FRACTIONS[m[4]] : m[1] ? Number(m[1]) / Number(m[2]) : Number(m[3]);
  return [text.slice(m[0].length), v > 0 && v < Infinity ? v : undefined];
}
// The equivalents a reagent's text gives: "K2CO3 (2 eq.)", "1.5 equiv NaBH4", "Pd(PPh3)4 (5 mol%)". Undefined if none.
export function reagentEquiv(text: string): number | undefined {
  const m = /\b(\d+(?:[.,]\d+)?)\s*(eq(?:uiv)?\.?|Äq\.?|mol\s?%)/i.exec(text); // Elucida: "Äq.", decimal comma
  return m ? Number(m[1].replace(",", ".")) * (m[2].endsWith("%") ? 0.01 : 1) : undefined;
}
// A line of conditions as its items: split at commas, semicolons and line breaks outside brackets, so
// "toluene/EtOH/H2O (4:1:1, 30 mL)" stays one item.
export function conditionItems(text: string): string[] {
  const out: string[] = [];
  let depth = 0, item = "";
  for (const ch of text) {
    if ("([{".includes(ch)) depth++;
    else if (")]}".includes(ch)) depth = Math.max(0, depth - 1);
    if (!depth && /[,;\n]/.test(ch)) { out.push(item.trim()); item = ""; } else item += ch;
  }
  out.push(item.trim());
  return out.filter(Boolean);
}
// The gas a reaction runs under (N2, Ar, air): not a reagent, so it has no column in the table.
export const inert = (text: string) => /^(?:under\s+)?(?:N2|N₂|Ar|argon|nitrogen|He|helium|air)(?:\s*\(?(?:atm|balloon)\)?)?$/i.test(text.trim());
// Groups a condensed formula is written with, as formulas, so "Pd(PPh3)4", "NH4OAc" and "Et3N" weigh what they are.
// One pass, longest first (OAc before Ac): the table is laid out again on every change.
const GROUPS: Record<string, string> = {
  OAc: "(C2H3O2)", OTf: "(CF3SO3)", OTs: "(C7H7SO3)", OMe: "(OCH3)", OEt: "(OC2H5)", tBu: "(C4H9)", iPr: "(C3H7)", nBu: "(C4H9)", Bu: "(C4H9)",
  Ph: "(C6H5)", Bn: "(C7H7)", Bz: "(C7H5O)", Ts: "(C7H7SO2)", Tf: "(CF3SO2)", Cp: "(C5H5)", Ac: "(C2H3O)", Me: "(CH3)", Et: "(C2H5)", Pr: "(C3H7)",
};
const GROUP = new RegExp(Object.keys(GROUPS).join("|"), "g");
// Octet's reagent abbreviations (src/abbreviations.json) by name, each to its standard InChI.
let abbreviated: Map<string, string> | undefined;
const abbreviation = (name: string) => (abbreviated ??= new Map(Object.entries(ABBREVIATIONS as Record<string, string>).map(([inchi, n]) => [n, inchi]))).get(name);
// Octet's listed liquids (liquids.ts): by standard InChI, by name in lower case, and the formulas they have.
let liquids: { inchi: Map<string, Liquid>; name: Map<string, Liquid>; formulas: Set<string> } | undefined;
const listed = () => (liquids ??= { inchi: new Map(LIQUIDS.map((l) => [l.inchi, l])), name: new Map(LIQUIDS.flatMap((l) => l.names.map((n) => [n.toLowerCase(), l] as const))), formulas: new Set(LIQUIDS.map((l) => l.inchi.split("/")[1])) });
// A drawn structure's listed liquid: by its formula first, then by its standard InChI, asked for only then, so a
// structure with THF's formula (butanone, butanal) is never THF.
export const liquidOf = (formula: string, inchi: () => string | undefined): Liquid | undefined => {
  const l = listed();
  if (!l.formulas.has(formula)) return undefined;
  const i = inchi();
  return i === undefined ? undefined : l.inchi.get(i);
};
// A reagent written as text: by a name the list gives it ("THF", "dry THF", "tetrahydrofuran"), else by Octet's
// abbreviation's InChI. Undefined when it is not a listed liquid. The table reads each text once (gridview.ts readItem).
export function liquidNamed(text: string): Liquid | undefined {
  const plain = coefficient(reagentName(text))[0].trim(), l = listed(), inchi = l.name.has(plain.toLowerCase()) ? undefined : abbreviation(plain);
  return l.name.get(plain.toLowerCase()) ?? (inchi === undefined ? undefined : l.inchi.get(inchi));
}
// Words for what a formula says (issue 132). A Map, so "constructor" is not one.
const WORDS = new Map([["proton", "H+"], ["hydroxide", "OH−"], ["hydronium", "H3O+"], ["hydride", "H−"], ["water", "H2O"]]);
// A formula and the charge at its end, raised: H+ is H and ⁺, OH− is OH and ⁻, SO4 2− and SO42− are SO4 and ²⁻, Fe³⁺
// is Fe and ³⁺ (issue 132). Digits before the sign are the charge's when set apart or raised, after one element (Cu2+)
// or after another digit (SO42−), else the formula's (NH4+, H3O+). With no charge, the text and "". The gap and the
// digits are short, so long text takes no longer than its length.
const RAISED: Record<string, string> = { 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹", "+": "⁺", "-": "⁻", "−": "⁻" };
function charged(text: string): [string, string] {
  const m = /^(.+?)(\s?\^?)(\d{0,3}|[⁰¹²³⁴⁵⁶⁷⁸⁹]{0,3})([+\-−⁺⁻])$/.exec(text);
  if (!m) return [text, ""];
  const [, base, gap, n, sign] = m, own = !gap && /^\d+$/.test(n) && !/^[A-Z][a-z]?$/.test(base) ? n.slice(0, n.length > 1 ? -1 : undefined) : "";
  return [base + own, [...n.slice(own.length) + sign].map((ch) => RAISED[ch] ?? ch).join("")];
}
// Words for how a reaction is run, never a reagent's name.
const CONDITION_WORDS = /^(?:reflux|rt|r\.t\.|room temp(?:erature)?|overnight|o\/n|heat|heating|light|dark|stir|stirring|sonication|ultrasound|microwave|MW|hν|hv|Δ|then|workup|work-up|quench|filter|filtration)$/i;
// What a reader (Name to Structure) made of each name. It takes a few ms a name, and the table is laid out again on
// every change, so each name is read once. Kept for the last reader given: Editor.tsx gives a new one when Octet's
// names load or the user's own names change. A word for how the reaction is run is never read. Short text is read
// (D2O, CD3OD and HF·py are names): once read, it costs nothing.
let reader: ((name: string) => string | undefined) | undefined, readings = new Map<string, string | undefined>();
function readName(name: string, read: (name: string) => string | undefined): string | undefined {
  if (CONDITION_WORDS.test(name)) return undefined;
  if (read !== reader || readings.size >= 500) [reader, readings] = [read, new Map()];
  if (!readings.has(name)) readings.set(name, read(name));
  return readings.get(name);
}
// A reagent's formula and molar mass as the reagent table takes it (Editor.tsx gridViews): an acronym (NBS,
// DMF, THF: capitals, no digits) as Octet's abbreviations or Name to Structure read it; else the formula as written,
// its groups written out, with any charge (H+, OH−; its mass the formula's); else the abbreviations' or Name to
// Structure's reading; else an atom label's, so THF is never read as tritium fluoride. Proton, hydroxide, hydronium,
// hydride and water read as their formulas. read: a name to SMILES; label: a label to SMILES; weigh: SMILES or InChI
// to its formula and weight. Undefined when none reads it.
export function reagentFormula(text: string, read: (name: string) => string | undefined, label: (text: string) => string | undefined, weigh: (smiles: string) => { formula: string; weight: number } | undefined): { formula: string; weight: number } | undefined {
  const said = coefficient(reagentName(text))[0], plain = WORDS.get(said.toLowerCase()) ?? said, named = () => { const s = abbreviation(plain) ?? readName(plain, read); return s ? weigh(s) : undefined; };
  // A mixture (toluene/EtOH/H2O) is not one compound: it has no formula of its own.
  if (/[\w)]\s*\/\s*[\w(]/.test(plain)) return undefined;
  if (/^[A-Z]{2,6}$/.test(plain)) { const n = named(); if (n) return n; }
  const [body, charge] = charged(plain), written = /^[A-Za-z0-9()[\]·.\s]+$/.test(body) ? body.replace(GROUP, (g) => GROUPS[g]) : undefined, w = written ? formulaWeight(written) : undefined;
  if (w !== undefined) return { formula: body.replace(/\s+/g, "") + charge, weight: w };
  const n = named();
  if (n) return n;
  const s = label(plain);
  return s ? weigh(s) : undefined;
}
// A formula's molar mass, brackets and dots allowed ("Cu(OAc)2" is not a formula; "Pd(PPh3)4" needs its groups
// written out). Undefined if it has anything unknown.
export function formulaWeight(text: string): number | undefined {
  const s = text.replace(/\s+/g, "").replace(/[₀-₉]/g, (d) => String("₀₁₂₃₄₅₆₇₈₉".indexOf(d)));
  let i = 0;
  const dot = () => s[i] === "·" || s[i] === ".";
  // part: one part after a dot (the 5H2O of CuSO4·5H2O·NH3), so its number counts it alone.
  const group = (part = false): number | undefined => {
    let total = 0;
    while (i < s.length && s[i] !== ")" && !(part && dot())) {
      if (dot()) { i++; const k = /^\d+/.exec(s.slice(i))?.[0]; if (k) i += k.length; const w = group(true); if (w === undefined) return undefined; total += (k ? Number(k) : 1) * w; continue; }
      let w: number | undefined;
      if (s[i] === "(") { i++; w = group(); if (s[i] !== ")") return undefined; i++; }
      else { const el = /^[A-Z][a-z]?/.exec(s.slice(i))?.[0]; if (!el || WEIGHT[el] === undefined) return undefined; i += el.length; w = WEIGHT[el]; }
      const n = /^\d+/.exec(s.slice(i))?.[0];
      if (n) i += n.length;
      if (w === undefined) return undefined;
      total += w * (n ? Number(n) : 1);
    }
    return total;
  };
  const w = group();
  return w !== undefined && i === s.length && w > 0 ? w : undefined;
}

// A saved grid read as a hostile file is: typed amounts finite and not negative under known fields, keys short, at most
// 60 components and the rows Octet has, and a layout only when it is "rows"; undefined when it is damaged. The fields
// added after 1.1.2 are each checked alone, and one that is wrong is left out with the grid kept: roles and taken at
// most 60, each a reactant's key with a value from its list; conc a number above 0 and at most 1000 mol/L; conditions
// the four names only, each one line of at most 200 characters (experiment.ts oneLine); step only true.
const FIELDS = ["mass", "moles", "equiv", "volume", "density", "molarity", "purity", "measured"];
const KEY = /^(?:[rp]\d{1,2}|[rp]:[^\n\r]{1,80})$/;
export const GRID_ROW_IDS = ["formula", "mw", "role", "limiting", "equiv", "mass", "moles", "volume", "density", "molarity", "conc", "purity", "expected", "expectedMoles", "measured", "yield"];
export const ROLES: GridRole[] = ["reactant", "catalyst", "solvent"];
export const CONDITIONS = [["temperature", "Temperature"], ["time", "Time"], ["atmosphere", "Atmosphere"], ["other", "Other"]] as const;
const reactantKeyed = <T extends string>(x: unknown, values: readonly T[]): Record<string, T> | undefined => {
  if (!x || typeof x !== "object" || Array.isArray(x)) return undefined;
  const list = Object.entries(x);
  return list.length <= 60 && list.every(([k, v]) => KEY.test(k) && k[0] === "r" && values.includes(v)) ? Object.fromEntries(list) : undefined;
};
function readConditions(x: unknown): GridConditions | undefined {
  if (!x || typeof x !== "object" || Array.isArray(x)) return undefined;
  const list = Object.entries(x);
  if (!list.every(([k, v]) => CONDITIONS.some(([name]) => name === k) && typeof v === "string")) return undefined;
  const kept = list.map(([k, v]) => [k, oneLine(v as string)]).filter(([, v]) => v);
  return kept.length ? Object.fromEntries(kept) : undefined;
}
export function readGrid(raw: unknown, arrow: number): Grid | undefined {
  const g = raw as Record<string, unknown> | undefined, typed = g?.typed as Record<string, Record<string, unknown>> | undefined;
  if (!g || typeof typed !== "object" || !typed || Array.isArray(typed) || Object.keys(typed).length > 60) return undefined;
  if (!Object.entries(typed).every(([k, v]) => KEY.test(k) && typeof v === "object" && v && !Array.isArray(v) && Object.entries(v).every(([f, x]) => FIELDS.includes(f) && typeof x === "number" && Number.isFinite(x) && x >= 0 && x < 1e9))) return undefined;
  if (g.limiting !== undefined && !(typeof g.limiting === "string" && KEY.test(g.limiting) && g.limiting.startsWith("r"))) return undefined;
  const h = g.hidden as { rows?: unknown; cols?: unknown } | undefined;
  const rows = Array.isArray(h?.rows) ? (h!.rows as unknown[]).filter((x): x is string => typeof x === "string" && GRID_ROW_IDS.includes(x)).slice(0, 20) : [];
  const cols = Array.isArray(h?.cols) ? (h!.cols as unknown[]).filter((x): x is string => typeof x === "string" && KEY.test(x)).slice(0, 60) : [];
  const colour = typeof g.colour === "string" && /^#[0-9a-f]{6}$/i.test(g.colour) ? g.colour : undefined;
  const roles = reactantKeyed(g.roles, ROLES), taken = reactantKeyed(g.taken, ["mass", "volume"] as const), conditions = readConditions(g.conditions);
  const conc = typeof g.conc === "number" && Number.isFinite(g.conc) && g.conc > 0 && g.conc <= 1000 ? g.conc : undefined;
  const at = Array.isArray(g.at) && g.at.length === 2 && g.at.every((x) => typeof x === "number" && Number.isFinite(x) && Math.abs(x) < 1e4) ? [g.at[0], g.at[1]] as [number, number] : undefined;
  return { arrow, typed: typed as Grid["typed"], ...(g.limiting ? { limiting: g.limiting as string } : {}), ...(rows.length || cols.length ? { hidden: { ...(rows.length ? { rows } : {}), ...(cols.length ? { cols } : {}) } } : {}), ...(colour ? { colour } : {}), ...(g.layout === "rows" ? { layout: "rows" as const } : {}),
    ...(roles ? { roles } : {}), ...(taken && Object.keys(taken).length ? { taken } : {}), ...(conc ? { conc } : {}), ...(conditions ? { conditions } : {}), ...(g.step === true ? { step: true as const } : {}), ...(at ? { at } : {}) };
}

// Each grid column's key (its side and what it is: "r:C7H8O", 'r:"NaBH4"', and "#2" on the next one the same) and what
// was typed for it: by its key, or else, for typed values whose key names no column (a compound redrawn, or a grid
// from before keys named compounds, "r0"), by order: the first column on the same side with nothing of its own. The
// limiting reactant follows its values. moved: each key whose values went to another column, and that column's key.
export function keyColumns<T extends { product: boolean; what: string }>(cols: T[], typed: Grid["typed"], limiting?: string): { cols: (T & { key: string; typed: Typed })[]; limiting?: string; moved: Map<string, string> } {
  const count = new Map<string, number>();
  const keyed = cols.map((c) => { const base = `${c.product ? "p" : "r"}:${c.what}`, n = (count.get(base) ?? 0) + 1; count.set(base, n); return { ...c, key: n > 1 ? `${base}#${n}` : base, typed: typed[n > 1 ? `${base}#${n}` : base] ?? {} }; });
  const keys = new Set(keyed.map((c) => c.key)), moved = new Map<string, string>();
  const old = (k: string) => /^[rp]\d+$/.test(k);
  const orphans = Object.keys(typed).filter((k) => !keys.has(k)).sort((a, b) => (old(a) && old(b) ? Number(a.slice(1)) - Number(b.slice(1)) : Number(old(b)) - Number(old(a))));
  for (const k of orphans) {
    const c = keyed.find((x) => (x.product ? "p" : "r") === k[0] && !Object.keys(x.typed).length && ![...moved.values()].includes(x.key));
    if (!c || !Object.keys(typed[k]).length) continue;
    c.typed = typed[k];
    moved.set(k, c.key);
  }
  const lim = limiting && (keys.has(limiting) ? limiting : moved.get(limiting) ?? (old(limiting) ? keyed.filter((c) => !c.product)[Number(limiting.slice(1))]?.key : undefined));
  return { cols: keyed, limiting: lim, moved };
}
