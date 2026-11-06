// Atom labels beyond a single element: abbreviations (Ph, Boc), condensed formulas (OMe, CO2Et, NHBoc).
// A label is read as units: an element or group, then an optional count (a subscript), or a bracketed part.
// Drawn left to right from the attached atom; when the bond comes from the right, the units are reversed
// (OMe becomes MeO, CO2Et becomes EtO2C), as ChemDraw does in its ACS 1996 output.

const SYMBOLS = (
  "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr " +
  "Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt " +
  "Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og D T"
).split(" "); // D and T: deuterium and tritium, hydrogen's isotopes written as elements
export const ELEMENTS = new Set(SYMBOLS);

// Groups, as SMILES whose first atom is the attachment point. Names a chemist types as one word.
export const GROUPS: Record<string, string> = {
  Me: "C", Et: "CC", Pr: "CCC", iPr: "C(C)C", nPr: "CCC", Bu: "CCCC", nBu: "CCCC", iBu: "CC(C)C", sBu: "C(C)CC", tBu: "C(C)(C)C",
  Ph: "c1ccccc1", Bn: "Cc1ccccc1", Ar: "c1ccccc1", Ac: "C(C)=O", Bz: "C(=O)c1ccccc1", Piv: "C(=O)C(C)(C)C",
  Boc: "C(=O)OC(C)(C)C", Cbz: "C(=O)OCc1ccccc1", Fmoc: "C(=O)OCC1c2ccccc2-c2ccccc21", Alloc: "C(=O)OCC=C", Troc: "C(=O)OCC(Cl)(Cl)Cl",
  Ts: "S(=O)(=O)c1ccc(C)cc1", Ms: "S(C)(=O)=O", Tf: "S(=O)(=O)C(F)(F)F", Ns: "S(=O)(=O)c1ccc([N+](=O)[O-])cc1",
  TMS: "[Si](C)(C)C", TES: "[Si](CC)(CC)CC", TBS: "[Si](C)(C)C(C)(C)C", TBDMS: "[Si](C)(C)C(C)(C)C",
  TIPS: "[Si](C(C)C)(C(C)C)C(C)C", TBDPS: "[Si](c1ccccc1)(c1ccccc1)C(C)(C)C",
  PMB: "Cc1ccc(OC)cc1", PMP: "c1ccc(OC)cc1", MOM: "COC", THP: "C1CCCCO1", Tr: "C(c1ccccc1)(c1ccccc1)c1ccccc1",
  Cp: "C1C=CC=C1", Cy: "C1CCCCC1", Mes: "c1c(C)cc(C)cc1C", Tol: "c1ccc(C)cc1",
};
const GROUP_NAMES = Object.keys(GROUPS).sort((a, b) => b.length - a.length);

// ChemDraw's generic labels (Insert Generic Label): A, M, Q, X and R, then the 38 Reaxys classes, each with what it
// stands for. Y, and R with a number (R1 to R99) and primes (R', R''), are generic too. A generic label is a query
// atom: it is never read as atoms (CYC is not C–Y–C).
export const GENERICS: [string, string][] = [
  ["A", "Any atom but H"], ["M", "Metal"], ["Q", "Any atom but C or H"], ["X", "Halogen"], ["R", "Any group"],
  ["AH", "Any atom or H"], ["MH", "Metal or H"], ["QH", "Any atom but C, or H"], ["XH", "Halogen or H"], ["G", "Any group"], ["GH", "Any group or H"],
  ["G*", "Any group, closes rings"], ["GH*", "Any group or H, closes rings"], ["ACY", "Acyclic"], ["ACH", "Acyclic or H"],
  ["ABC", "Carbacyclic"], ["ABH", "Carbacyclic or H"], ["AYL", "Alkynyl"], ["AYH", "Alkynyl or H"], ["ALK", "Alkyl"], ["ALH", "Alkyl or H"],
  ["AEL", "Alkenyl"], ["AEH", "Alkenyl or H"], ["AHC", "Hetero acyclic"], ["AHH", "Hetero acyclic or H"], ["AOX", "Alkoxy"], ["AOH", "Alkoxy or H"],
  ["CYC", "Cyclic"], ["CYH", "Cyclic or H"], ["CBC", "Carbocyclic"], ["CBH", "Carbocyclic or H"], ["ARY", "Aryl"], ["ARH", "Aryl or H"],
  ["CAL", "Cycloalkyl"], ["CAH", "Cycloalkyl or H"], ["CEL", "Cycloalkenyl"], ["CEH", "Cycloalkenyl or H"], ["CHC", "Heterocyclic"], ["CHH", "Heterocyclic or H"],
  ["HAR", "Heteroaryl"], ["HAH", "Heteroaryl or H"], ["CXX", "No carbon"], ["CXH", "No carbon or H"],
];
const GENERIC_NAMES = new Set([...GENERICS.map(([g]) => g), "Y"]);
export const isGeneric = (label: string) => GENERIC_NAMES.has(label) || /^R([1-9]\d?)?'{0,2}$/.test(label);

export type Unit = { text: string; count?: string; kind: "element" | "group" | "bracket" | "other" };

// Splits a label into units. Groups win over elements where both fit (so "Bu" is butyl, not boron-u).
export function units(label: string): Unit[] {
  const out: Unit[] = [];
  let i = 0;
  const digits = () => { const m = /^\d+/.exec(label.slice(i)); if (m) i += m[0].length; return m?.[0]; };
  while (i < label.length) {
    const rest = label.slice(i);
    if (rest[0] === "(") {
      const close = rest.indexOf(")");
      const inner = close > 0 ? rest.slice(0, close + 1) : rest;
      i += inner.length;
      out.push({ text: inner, count: digits(), kind: "bracket" });
      continue;
    }
    const group = GROUP_NAMES.find((g) => rest.startsWith(g) && !/[a-z]/.test(rest[g.length] ?? ""));
    const two = rest.slice(0, 2), one = rest[0];
    const token = group ?? (ELEMENTS.has(two) && /^[A-Z][a-z]$/.test(two) ? two : one);
    i += token.length;
    out.push({ text: token, count: digits(), kind: group ? "group" : ELEMENTS.has(token) ? "element" : "other" });
  }
  return out;
}

// The element a label attaches through: the first element of the first unit (O for OMe, C for CO2Et).
// Undefined for a label that starts with a group (Ph, Boc).
export function anchorElement(label: string): string | undefined {
  const first = units(label)[0];
  return first?.kind === "element" ? first.text : undefined;
}

// A label is a plain element when it is one element symbol and nothing else.
export const isElement = (label: string) => ELEMENTS.has(label);
// An element with its oxidation state written after it, Os(II), Fe(0): the element and the state.
const ROMAN = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
export function writtenOxidation(label: string): { el: string; ox: number } | undefined {
  const x = /^([A-Z][a-z]?)\((0|I{1,3}|IV|VI{0,3}|IX|X)\)$/.exec(label);
  return x && ELEMENTS.has(x[1]) ? { el: x[1], ox: ROMAN.indexOf(x[2]) } : undefined;
}

// Formulas whose bonding a left-to-right reading gets wrong (CN is a nitrile, not an amine).
const FORMULAS: Record<string, string> = {
  CN: "C#N", NC: "[N+]#[C-]", CHO: "C=O", CO2H: "C(=O)O", COOH: "C(=O)O", CO2: "C(=O)[O-]", NO2: "[N+](=O)[O-]", NO: "N=O",
  N3: "N=[N+]=[N-]", SO3H: "S(=O)(=O)O", SO2: "S(=O)=O", SO2Ph: "S(=O)(=O)c1ccccc1", COMe: "C(C)=O", COPh: "C(=O)c1ccccc1",
  CONH2: "C(N)=O", OCN: "OC#N", SCN: "SC#N", NCO: "N=C=O", NCS: "N=C=S",
};

// The label as SMILES with its attachment point first, for chemistry (SMILES export, formulas).
// Groups and the formulas above are looked up. Other condensed formulas are read left to right: each heavy
// atom joins the chain, H and counts are left to valence, a repeated element (CF3) and any group or bracket
// hang off the atom before them, and CO2R or COOR becomes an ester. Undefined if Octet cannot read it.
// A label written right to left (HO2C, OHC, MeO, Et3N) is read from its end, as ChemDraw reads a label it shows
// reversed: when its reverse is a formula above, or when it starts with a group and ends with one heavy atom.
export function labelSmiles(label: string): string | undefined {
  if (GROUPS[label]) return GROUPS[label];
  if (isGeneric(label)) return undefined;
  // An element with its oxidation state, Os(II): the element alone ((II) is not two iodine atoms, and no charge).
  const ox = writtenOxidation(label);
  if (ox) return `[${ox.el}]`;
  if (FORMULAS[label]) return FORMULAS[label];
  let us = units(label);
  if (!us.length) return undefined;
  const back = [...us].reverse(), last = back[0];
  const reverse = back.map((u) => u.text + (u.count ?? "")).join("");
  if (FORMULAS[reverse]) return FORMULAS[reverse];
  if (us.length > 1 && us[0].kind === "group" && last.kind === "element" && last.text !== "H" && !last.count) us = back;
  let smiles = "";
  const atom = (sym: string) => (["B", "C", "N", "O", "P", "S", "F", "Cl", "Br", "I"].includes(sym) ? sym : `[${sym}]`);
  // The first heavy atom or group starts the chain (never a bare branch, which is not SMILES: H2O2 is OO).
  for (const u of us) {
    const n = Number(u.count ?? 1);
    if (!(n >= 1 && n <= 99)) return undefined;
    if (u.kind === "element") {
      if (u.text === "H") continue;
      smiles += smiles && n > 1 ? `(${atom(u.text)})`.repeat(n) : atom(u.text).repeat(n);
    } else if (u.kind === "group") {
      smiles += smiles ? `(${GROUPS[u.text]})`.repeat(n) : GROUPS[u.text] + `(${GROUPS[u.text]})`.repeat(n - 1);
    } else if (u.kind === "bracket") {
      const inner = labelSmiles(u.text.slice(1, -1));
      if (!inner) return undefined;
      smiles += smiles ? `(${inner})`.repeat(n) : inner + `(${inner})`.repeat(n - 1);
    } else return undefined;
  }
  if (crowded(smiles)) return undefined;
  // Esters and acids written CO2R or COOR: one O double-bonded to the carbon.
  return smiles.replace(/^C\(O\)\(O\)/, "C(=O)O").replace(/^COO/, "C(=O)O") || undefined;
}
// A label Indigo cannot lay out in good time is not read, as the layout can run for minutes and stop the editor:
// more than 120 atoms, an atom with more than eight neighbours (CCl99) or more than four groups with a ring on it
// (CPh5), or a ring atom with more than four neighbours (Ph4, CyPh4Cl). Ph3, BPh4, Pd(PPh3)4, W(CO)6 and PF6 are read.
function crowded(smiles: string): boolean {
  type At = { near: number; rings: number; ring: boolean };
  const bad = (a?: At) => !!a && (a.near > 8 || a.rings > 4 || (a.ring && a.near > 4));
  let atoms = 0, bracket = false;
  // The chain's last atom at each depth, and whether each open branch has a ring in it.
  const chain: (At | undefined)[] = [undefined], ringy: boolean[] = [];
  for (const ch of smiles) {
    const last = chain[chain.length - 1];
    if (bracket) { bracket = ch !== "]"; continue; }
    if (ch === "(") { if (last) last.near++; chain.push(undefined); ringy.push(false); }
    else if (ch === ")") {
      if (!ringy.length || bad(chain.pop())) return true;
      const at = chain[chain.length - 1];
      if (ringy.pop() && at) at.rings++;
      if (bad(at)) return true;
    } else if (/\d/.test(ch)) {
      if (last) { last.near++; last.ring = true; }
      ringy.fill(true);
    } else if (ch === "[" || /[A-Zbcnops]/.test(ch)) {
      // A new atom: bonded to the last one (the first atom, to the drawing).
      if (++atoms > 120) return true;
      if (last) { last.near++; if (bad(last)) return true; }
      chain[chain.length - 1] = { near: 1, rings: 0, ring: false };
      bracket = ch === "[";
    }
  }
  return chain.some(bad);
}

// Chemical formulas in running text: a count straight after an element, a group or a closing bracket is a
// subscript (K2CO3, Pd(PPh3)4, Et3N, CH2Cl2, DMSO-d6). Numbers on their own (72, 1,4-dioxane, 12 h), counts after
// anything else (L1) and method names (B3LYP, SN2) stay as typed. Subscripts print 75% size, 0.212 em down.
const COUNTED = new Set([...SYMBOLS, ...Object.keys(GROUPS), "pin", "dba", "cod", "acac", "d"]);
const NOT_FORMULA = /^(B3LYP|B2PLYP|MP[2-4]|S[NE][12]|E[12]|E1cB)$/;
export type Run = { text: string; sub?: true };
export function formulaRuns(text: string): Run[] {
  const out: Run[] = [];
  const push = (t: string, sub?: true) => {
    if (!t) return;
    const last = out[out.length - 1];
    if (last && !!last.sub === !!sub) last.text += t;
    else out.push(sub ? { text: t, sub } : { text: t });
  };
  let at = 0;
  for (const m of text.matchAll(/\d+/g)) {
    const before = text.slice(0, m.index), word = /\S*$/.exec(before)![0] + /^\S*/.exec(text.slice(m.index))![0];
    const letters = /[A-Za-z]{1,5}$/.exec(before)?.[0] ?? "";
    const counted = !NOT_FORMULA.test(word) && /[A-Za-z]/.test(word)
      && (/[A-Za-z0-9][)\]]$/.test(before) || Array.from({ length: letters.length }, (_, k) => letters.slice(k)).some((s) => COUNTED.has(s)));
    if (!counted) continue;
    push(text.slice(at, m.index));
    push(m[0], true);
    at = m.index! + m[0].length;
  }
  push(text.slice(at));
  return out;
}
