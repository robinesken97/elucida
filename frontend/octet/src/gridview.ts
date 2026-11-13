// Stoichiometry grids as Octet lays them out (Structure > Analyse Stoichiometry, and every reaction on an experiment
// page): a column under each reactant, each reagent drawn or written above or below an arrow (as ChemDraw's grid takes
// them, as reactants), and each product; text reagents such as H2O or MeOH too, each item of a list such as
// "NaBH4, MeOH" on its own, their molar mass from the formula or the name. The row names on the left, the amounts
// worked out from what was typed (stoich.ts). Hidden rows and columns are left out.
import { isNumber, scaleOf, type Box, type Grid, type GridRole, type Mol } from "./render.ts";
import { sheetSafe } from "./experiment.ts";
import { EMBEDDED } from "./elucida.ts";
import { coefficient, conditionItems, CONDITIONS, formatAmount, inert, keyColumns, limitingOf, liquidNamed, liquidOf, reagentEquiv, reagentName, solve, type Field, type Solved } from "./stoich.ts";
import type { Reaction, Step } from "./reaction.ts";
import type { Part, RoleStep } from "./interpret.ts";
import type { Liquid } from "./liquids.ts";

// The grid's rows, as ChemDraw's: what each component is, then amounts. shown: rows that appear only once one of these
// was typed somewhere; product: rows for products (true) or reactants (false) only. Equivalents are a product's
// coefficient too, as ChemDraw's product column has them. Volume and Density always show for reactants, so a density
// typed gives the volume to measure out (issue 135). A product's Expected mass can be typed, as the mass wanted, kept
// as its mass (issue 136). Role shows once a column is not a reactant, and Concentration once one is a solvent.
export const GRID_ROWS: { id: string; name: string; field?: Field; product?: boolean; shown?: Field[] }[] = [
  { id: "formula", name: "Formula" }, { id: "mw", name: "MW" }, { id: "role", name: "Role", product: false }, { id: "limiting", name: "Limiting?", product: false },
  { id: "equiv", name: "Equivalents", field: "equiv" }, { id: "mass", name: "Mass", field: "mass", product: false }, { id: "moles", name: "Moles", field: "moles", product: false },
  { id: "volume", name: "Volume", field: "volume", product: false }, { id: "density", name: "Density", field: "density", product: false },
  { id: "molarity", name: "Molarity", field: "molarity", product: false, shown: ["molarity"] }, { id: "conc", name: "Concentration", product: false },
  { id: "purity", name: "Purity", field: "purity", shown: ["purity"] },
  { id: "expected", name: "Expected mass", field: "mass", product: true }, { id: "expectedMoles", name: "Expected moles", product: true },
  { id: "measured", name: "Measured mass", field: "measured", product: true }, { id: "yield", name: "Yield", product: true },
];

// The cell next to a cell, as a spreadsheet's arrow keys and Tab move (y is up). Found by where the cells are drawn, so
// it is the same as rows or as columns and with rows hidden: left and right along the cell's line, up and down to the
// nearest cell in the next line. Tab goes on to the next line's first cell, Shift+Tab back. At the edge it stays.
type At = { key: string; row: string; x: number; y: number };
export function gridStep<C extends At>(cells: C[], from: { key: string; row: string }, dir: "left" | "right" | "up" | "down" | "next" | "back"): C | undefined {
  const c = cells.find((x) => x.key === from.key && x.row === from.row);
  if (!c) return undefined;
  const line = (a: At, b: At) => Math.abs(a.y - b.y) < 1e-6;
  if (dir === "next" || dir === "back") {
    const order = [...cells].sort((a, b) => (line(a, b) ? a.x - b.x : b.y - a.y)), k = order.indexOf(c) + (dir === "next" ? 1 : -1);
    return order[k] ?? c;
  }
  const ahead = cells.filter((x) => (dir === "left" ? line(x, c) && x.x < c.x : dir === "right" ? line(x, c) && x.x > c.x : dir === "up" ? x.y > c.y + 1e-6 : x.y < c.y - 1e-6));
  // Nearest line first, then nearest along it.
  const cost = (x: At) => (dir === "up" || dir === "down" ? Math.abs(x.y - c.y) * 1e6 + Math.abs(x.x - c.x) : Math.abs(x.x - c.x));
  return ahead.sort((a, b) => cost(a) - cost(b))[0] ?? c;
}

// What laying a grid out needs from the drawing as drawn. reaction: an arrow's reaction; steps: its parts by role
// (interpret.ts); structure: a structure's formula and molar mass; reagent: a reagent's (stoich.ts reagentFormula);
// captionBox: a caption's box (drawing units, y up); nameWidth: a text's width at a size in pt (drawing units);
// perPt: drawing units in a point; experiment: the drawing is an experiment page; inchi: a structure's standard InChI,
// asked for only when its formula is a listed liquid's (stoich.ts liquidOf). fit: on an experiment page, the right edge
// a table in the Reaction scheme box keeps inside (the box's, a bond length in).
export type GridDeps = {
  reaction: (arrow: number) => Reaction | undefined;
  steps: (r: Reaction) => RoleStep[];
  structure: (atoms: number[]) => { formula: string; weight: number } | undefined;
  reagent: (text: string) => { formula: string; weight: number } | undefined;
  captionBox: (caption: number) => Box | undefined;
  nameWidth: (text: string, sizePt: number, bold?: boolean) => number;
  captionSize: number; perPt: number; experiment: boolean; inchi?: (atoms: number[]) => string | undefined; fit?: number;
};

// What a reagent's text says of itself: its coefficient ("2 HCl"), its text without it, the equivalents it gives, whether
// it is the atmosphere's gas, and its listed liquid. Each text is read once (the table is laid out again on every change).
const items = new Map<string, { n?: number; plain: string; equiv?: number; gas: boolean; liquid?: Liquid }>();
function readItem(item: string) {
  let r = items.get(item);
  if (r) return r;
  if (items.size >= 500) items.clear();
  const n = coefficient(reagentName(item))[1];
  r = { n, plain: n ? coefficient(item)[0] : item, equiv: reagentEquiv(item), gas: inert(item), liquid: liquidNamed(item) };
  items.set(item, r);
  return r;
}

// One grid for each reaction (an experiment page gives each new arrow one), laid out under it. When the reaction has
// grids for its steps (Grid.step: Analyse stoichiometry on a scheme of several arrows, or One table for each step),
// one table for each step instead, in the scheme's order, each under the one before; a grid of the whole reaction is
// then not drawn, and an arrow added to the scheme since (an experiment page gives it a grid) is a step with its grid.
// A table moved on its own (Grid.at) is laid out as before, then put with its corner that far from its arrow's tail.
export function gridViews(m: Mol, d: GridDeps) {
  const seen = new Set<number>(), out: GridView[] = [];
  for (const g of m.grids ?? []) {
    const r = d.reaction(g.arrow);
    if (!r || seen.has(r.arrows[0])) continue;
    seen.add(r.arrows[0]);
    const steps = d.steps(r);
    if (!steps.length) continue;
    const own = (m.grids ?? []).filter((x) => r.arrows.includes(x.arrow));
    if (!own.some((x) => x.step)) { const v = layGrid(m, d, g, r, steps, out.length === 0); if (v) out.push(fitted(placed(m, g, v), d.fit)); continue; }
    let before: GridView | undefined;
    for (const st of steps) {
      const sg = own.find((x) => x.arrow === st.arrow && x.step) ?? own.find((x) => x.arrow === st.arrow), v = sg && layGrid(m, d, sg, r, steps, out.length === 0, { own: st, before });
      if (v) out.push(fitted(placed(m, sg, v), d.fit));
      before = v;
    }
  }
  return out;
}
// A grid laid out: its columns, sums and cells. step: a table for one step (own), under the step before's table
// (before), whose product's Measured mass a reactant of this step takes as its amount when nothing typed sets it.
function layGrid(m: Mol, d: GridDeps, g: Grid, r: Reaction, steps: RoleStep[], first: boolean, step?: { own: RoleStep; before?: { solved: Record<string, Solved>; bottom: number } }) {
  // Coefficients (issue 133): a plain number just before a structure or text in the row (2 A + B → C), or one a
  // structure carries just on its left, is that part's coefficient and has no column of its own. A compound number
  // (bold) is not one.
  const coefs = new Map<Step, number>(), counted = new Set<Step>();
  const alone = (id: number) => { const c = m.captions?.find((x) => x.id === id); if (!c || isNumber(c)) return undefined; const [rest, v] = coefficient(c.text.trim()); return rest ? undefined : v; };
  r.steps.forEach((s, k) => {
    const next = r.steps[k + 1], v = s.kind === "text" ? alone(s.id) : undefined;
    if (v && (next?.kind === "structure" || next?.kind === "text")) { coefs.set(next, v); counted.add(s); }
    if (s.kind === "structure") for (const id of s.carry?.captions ?? []) {
      const b = d.captionBox(id), mid = (s.box[1] + s.box[3]) / 2, w = alone(id);
      if (w && b && (b[0] + b[2]) / 2 < s.box[0] && b[1] < mid && b[3] > mid) coefs.set(s, w);
    }
  });
  // label: what names it in a table of rows, its compound number or the text it is written as. given: the
  // equivalents its text gives ("K2CO3 (2 eq.)"), shown plain until a value is typed. coef: its coefficient, for
  // a part of the equation; side: written over or under an arrow, where a number in front ("2 HCl") gives its
  // equivalents. density: a reactant's listed density when it is a known liquid (liquids.ts); solvent: and a solvent
  // written or drawn over or under the arrow (benzene or acetone drawn in the equation is what reacts).
  // role: a reactant's, as the grid sets it; a column it does not list is a reactant, or in a table made with roles
  // (every table Octet makes now) a solvent when it is a known one.
  // carried: a step's reactant made by the step before, its moles from that step's Measured mass. atoms: a structure's,
  // for its name, CAS number and hazards (riskassess.ts).
  const parts: { product: boolean; what: string; formula: string; mw: number; x: number; low: number; label?: string; given?: number; coef?: number; side: boolean; density?: number; solvent?: boolean; role?: GridRole; carried?: number; atoms?: number[] }[] = [];
  // conditions: only text with a molar mass makes a column ("0 °C", "2 h" and "reflux" do not).
  const add = (p: Part, product: boolean, conditions = false) => {
    const x = (p.box[0] + p.box[2]) / 2, low = p.box[1];
    if (p.kind === "structure") {
      const a = d.structure(p.atoms), n = m.captions?.find((c) => isNumber(c) && c.under?.some((i) => p.atoms.includes(i)))?.text, liquid = a && !product && d.inchi ? liquidOf(a.formula, () => d.inchi!(p.atoms)) : undefined;
      parts.push({ product, what: a?.formula ?? "?", formula: a?.formula ?? "", mw: a?.weight ?? 0, x, low, atoms: p.atoms, label: n, coef: coefs.get(p), side: conditions, density: liquid?.density, solvent: conditions && liquid?.solvent });
      return;
    }
    if (counted.has(p)) return;
    const text = m.captions?.find((c) => c.id === p.id)?.text ?? "", items = conditions ? conditionItems(text) : [text.trim()];
    items.forEach((item, k) => {
      const { n, plain, equiv, gas, liquid } = readItem(item), got = d.reagent(item);
      // The atmosphere's gas (N2, Ar, air) is not a reagent: it has no column.
      if (conditions && (!got || gas)) return;
      parts.push({ product, what: `"${item}"`, formula: got?.formula ?? "", mw: got?.weight ?? 0, x: x + k * 0.01, low, label: plain, given: equiv ?? (conditions ? n : undefined), coef: conditions ? undefined : coefs.get(p) ?? n, side: conditions, density: product ? undefined : liquid?.density, solvent: conditions && liquid?.solvent });
    });
  };
  // A step's table: what stands before its arrow, its conditions and what stands after it.
  (step ? step.own : steps[0]).reactants.forEach((p) => add(p, false));
  for (const st of step ? [step.own] : steps) for (const p of [...st.above, ...st.below]) add(p, false, true);
  (step ? step.own : steps[steps.length - 1]).products.forEach((p) => add(p, true));
  if (!parts.length) return undefined;
  // Once a coefficient is written, each part of the equation has one.
  if (parts.some((p) => p.coef)) for (const p of parts) if (!p.side) p.coef ??= 1;
  const keyed = keyColumns(parts, g.typed, g.limiting), all = keyed.cols, hidden = g.hidden ?? {};
  // Roles and marks follow a compound redrawn, as its typed values do.
  const rekey = <T>(x?: Record<string, T>) => (x && keyed.moved.size ? Object.fromEntries(Object.entries(x).map(([k, y]) => [keyed.moved.get(k) ?? k, y])) : x);
  const roles = rekey(g.roles), taken = rekey(g.taken);
  for (const c of all) if (!c.product) c.role = roles?.[c.key] ?? (roles && c.solvent ? "solvent" : "reactant");
  // A reactant the step before made, with a Measured mass there: its moles from that, shown as worked out; it is the
  // limiting reactant unless another is set.
  const made = step?.before;
  if (made) for (const c of all) { const moles = c.product ? undefined : made.solved[`p${c.key.slice(1)}`]?.productMoles; if (moles !== undefined) c.carried = moles; }
  const limiting = limitingOf(all, keyed.limiting ?? all.find((c) => c.carried !== undefined)?.key)?.key, solved = solve(all, limiting, g.conc);
  // The grid takes its arrow's scale (decision 0007). Columns stand under what they are, a column's width apart.
  const f = scaleOf(m.arrows?.find((a) => a.id === g.arrow) ?? {}), width = 3.4 * f;
  const cols = all.filter((c) => !hidden.cols?.includes(c.key)).sort((p, q) => p.x - q.x).map((c) => ({ ...c }));
  cols.forEach((c, k) => { if (k && c.x < cols[k - 1].x + width) c.x = cols[k - 1].x + width; });
  if (!cols.length) return undefined;
  const used = (fd: Field) => cols.some((c) => c.typed[fd] !== undefined), products = cols.some((c) => c.product);
  // As rows, Molarity and Purity show only when used, on an experiment page too, so the table fits the page.
  const roled = (r: GridRole) => cols.some((c) => !c.product && c.role === r);
  const rows = GRID_ROWS.filter((row) => !hidden.rows?.includes(row.id) && (row.id === "role" ? roled("catalyst") || roled("solvent") : row.id === "conc" ? roled("solvent")
    : row.product ? products : EMBEDDED && row.id === "molarity" ? true : row.shown && (!d.experiment || g.layout === "rows") ? row.shown.some(used) : true));
  // Below the components and the numbers under them.
  const under = (m.captions ?? []).filter((c) => c.under?.some((i) => r.atoms.includes(i))).map((c) => d.captionBox(c.id)?.[1]).filter((y): y is number => y !== undefined);
  // A step's table goes under the one before it.
  const rh = d.captionSize * d.perPt * 0.9 * 1.6 * f, top = Math.min(...cols.map((c) => c.low), ...under, made ? made.bottom - 0.5 * rh + 0.9 * f : Infinity) - 0.9 * f;
  // The row names end a little before the first column; the rules start at the longest name.
  const left = Math.min(...cols.map((c) => c.x)) - width / 2 - 0.3 * f, size = d.captionSize * 0.9 * f;
  const names = Math.max(...rows.map((row) => d.nameWidth(row.name, size)));
  // Every cell: its component and row, its middle, top and width, for picking and typing in it. As rows (Grid.layout),
  // the reagents each take a row and the products a section of their own under them, each section with its title and
  // the names of its columns; the first column names each component by its compound number or its text.
  type Cell = { key: string; row: string; x: number; y: number; w: number; product: boolean };
  type Text = { text: string; x: number; y: number; anchor: "start" | "middle"; bold?: true; formula?: true };
  let cells: Cell[] = [], texts: Text[] | undefined, rules: [number, number, number][] | undefined, sections: { title: string; fields: GridRow[]; comps: typeof cols }[] | undefined;
  if (g.layout === "rows") {
    const wide = (t: string, bold = false) => d.nameWidth(t, size, bold);
    // A product's row: what it is, its expected mass, the mass measured and the yield; its equivalents only when typed.
    const ownEquiv = cols.some((c) => c.product && c.typed.equiv !== undefined), fits = (row: (typeof rows)[number], product: boolean) => row.product !== !product && !(product && (row.id === "expectedMoles" || (row.id === "equiv" && !ownEquiv)));
    sections = ([[false, "Reagents"], [true, "Products"]] as const).map(([product, title]) => ({ product, title, fields: rows.filter((row) => fits(row, product)), comps: cols.filter((c) => c.product === product) })).filter((sec) => sec.comps.length && sec.fields.length);
    const x0 = Math.min(...cols.map((c) => c.x)) - width / 2, nameW = Math.max(...sections.flatMap((sec) => [wide(sec.title, true), ...sec.comps.map((c) => wide(c.label ?? ""))])) + 0.4 * f;
    let y = top;
    texts = []; rules = [];
    for (const sec of sections) {
      let x = x0 + nameW;
      const at = sec.fields.map((row) => { const w = Math.max(width, wide(row.name) + 0.4 * f); x += w; return [x - w / 2, w]; });
      rules.push([x0, x, y]);
      texts.push({ text: sec.title, x: x0, y, anchor: "start", bold: true }, ...sec.fields.map((row, j) => ({ text: row.name, x: at[j][0], y, anchor: "middle" as const })));
      y -= rh;
      rules.push([x0, x, y]);
      for (const c of sec.comps) {
        texts.push({ text: c.label ?? "", x: x0, y, anchor: "start", formula: true });
        cells.push({ key: c.key, row: "name", x: x0 + nameW / 2, y, w: nameW, product: c.product }, ...sec.fields.map((row, j) => ({ key: c.key, row: row.id, x: at[j][0], y, w: at[j][1], product: c.product })));
        y -= rh;
      }
      rules.push([x0, x, y]);
      y -= 0.5 * rh;
    }
  } else cells = rows.flatMap((row, k) => cols.map((c) => ({ key: c.key, row: row.id, x: c.x, y: top - k * rh, w: width, product: c.product })));
  // The conditions block, right of the table: a line for each condition with a value (Temperature, Time, Atmosphere,
  // Other), its name and then its value. On an experiment page the first table's Temperature and Time are the page's
  // own (its details block), so they show once, there.
  const page = d.experiment && first, right = rules ? Math.max(...rules.map((r) => r[1])) : Math.max(...cols.map((c) => c.x)) + width / 2;
  const lines = CONDITIONS.filter(([k]) => g.conditions?.[k] && !(page && (k === "temperature" || k === "time"))).map(([k, name], j) => ({ key: k, name, value: g.conditions![k]!, y: top - j * rh }));
  const at = right + 0.6 * f, valueAt = at + Math.max(0, ...lines.map((l) => d.nameWidth(l.name, size))) + 0.4 * f;
  const block = lines.length ? { lines, at, valueAt, right: valueAt + Math.max(...lines.map((l) => d.nameWidth(l.value, size))) } : undefined;
  // The table's foot: its last rule (as rows), or its last row; or the block's last line when that is lower.
  const bottom = Math.min(rules ? rules[rules.length - 1]?.[2] ?? top : top - rows.length * rh, ...lines.map((l) => l.y - rh));
  return { arrow: g.arrow, all, cols, rows, solved, limiting, conc: g.conc, roles, taken, block, page, top, bottom, rh, left, width, start: left - names - 0.2 * f, f, colour: g.colour, hiding: !!(hidden.rows?.length || hidden.cols?.length), cells, texts, rules, sections };
}

export type GridView = NonNullable<ReturnType<typeof layGrid>>;
// Grid.at: the table's corner (where its row names start, and its top) from its arrow's tail, in the arrow's scale. So
// it stays where it was put while the reaction's structures change, and goes with the arrow when the reaction moves.
export const anchorOf = (m: Mol, arrow: number) => m.arrows?.find((a) => a.id === arrow)?.from;
function placed(m: Mol, g: Grid, v: GridView): GridView {
  const a = g.at && anchorOf(m, g.arrow);
  return a ? shiftView(v, [a[0] + g.at![0] * v.f - v.start, a[1] + g.at![1] * v.f - v.top]) : v;
}
// The table's Grid.at once moved by d (drawing units) from where it is drawn.
export const movedAt = (m: Mol, v: GridView, d: [number, number]): [number, number] | undefined => {
  const a = anchorOf(m, v.arrow);
  return a && [(v.start + d[0] - a[0]) / v.f, (v.top + d[1] - a[1]) / v.f];
};
// A conditions block that would pass the right edge the table keeps inside (fit) goes under the table, from its left,
// half a row clear.
function fitted(v: GridView, fit?: number): GridView {
  const b = v.block, left = v.rules?.[0]?.[0] ?? v.start;
  if (fit === undefined || !b || b.right <= fit || left >= fit) return v;
  const foot = v.rules ? v.rules[v.rules.length - 1]?.[2] ?? v.top : v.top - v.rows.length * v.rh, lines = b.lines.map((l, j) => ({ ...l, y: foot - (0.5 + j) * v.rh }));
  return { ...v, block: { lines, at: left, valueAt: left + b.valueAt - b.at, right: left + b.right - b.at }, bottom: Math.min(foot, lines[lines.length - 1].y - v.rh) };
}
// A table drawn d (drawing units) from where it was laid out.
export function shiftView(v: GridView, [dx, dy]: [number, number]): GridView {
  if (!dx && !dy) return v;
  const xy = <T extends { x: number; y: number }>(c: T) => ({ ...c, x: c.x + dx, y: c.y + dy });
  return { ...v, cols: v.cols.map((c) => ({ ...c, x: c.x + dx })), cells: v.cells.map(xy), texts: v.texts?.map(xy), rules: v.rules?.map(([a, b, h]): [number, number, number] => [a + dx, b + dx, h + dy]),
    block: v.block && { ...v.block, at: v.block.at + dx, valueAt: v.block.valueAt + dx, right: v.block.right + dx, lines: v.block.lines.map((l) => ({ ...l, y: l.y + dy })) },
    top: v.top + dy, bottom: v.bottom + dy, left: v.left + dx, start: v.start + dx };
}
export const ROLE_NAMES: Record<GridRole, string> = { reactant: "Reactant", catalyst: "Catalyst", solvent: "Solvent" };
// A column's role set: kept by its key. A table from an older Octet (no roles) first keeps each known solvent as a
// reactant, so only the column the user changed changes.
export function setRole(g: Grid, v: GridView, key: string, role: GridRole): Partial<Grid> {
  const roles: Record<string, GridRole> = g.roles ?? Object.fromEntries(v.all.filter((c) => !c.product && c.solvent).map((c) => [c.key, "reactant" as const]));
  return { roles: { ...roles, [key]: role }, ...(role === "solvent" && v.limiting === key ? { limiting: undefined } : {}) };
}
// A grid as the editor changes it: what was typed, the roles and the marks, each by the keys of the columns it has now
// (keyColumns), so values matched by order are kept by key and nothing grows past what readGrid reads.
export function keptGrid(g: Grid, v: GridView): Grid {
  const keys = new Set(v.all.map((c) => c.key)), own = <T>(r: Record<string, T>) => Object.fromEntries(Object.entries(r).filter(([k]) => keys.has(k)));
  return { ...g, typed: Object.fromEntries(v.all.filter((c) => Object.keys(c.typed).length).map((c) => [c.key, c.typed])), limiting: v.limiting,
    ...(v.roles ? { roles: own(v.roles) } : {}), ...(v.taken ? { taken: own(v.taken) } : {}) };
}
type GridRow = (typeof GRID_ROWS)[number];
// A cell's text, and whether it was typed (typed values show bold, worked-out ones plain, as ChemDraw's grid does).
// taken: the amount measured out, a reactant's Mass or Volume (Grid.taken), drawn red and underlined.
export function cellText(v: GridView, c: GridView["cols"][number], row: GridRow): { text: string; typed?: boolean; taken?: true } {
  const s = v.solved[c.key];
  const fd = row.id === "mass" || row.id === "volume" ? row.id : undefined;
  if (fd && !c.product && v.taken?.[c.key] === fd) return { text: formatAmount(s?.[fd], fd), typed: c.typed[fd] !== undefined, taken: true };
  if (row.id === "formula") return { text: c.formula };
  if (row.id === "role") return { text: c.product ? "Product" : ROLE_NAMES[c.role ?? "reactant"] };
  if (row.id === "mw") return { text: c.mw ? formatAmount(c.mw, "mw") : "" };
  if (row.id === "limiting") return { text: c.product ? "" : v.limiting === c.key ? "Yes" : "" };
  if (row.product !== c.product && row.product !== undefined) return { text: "" };
  if (row.id === "expected") return { text: formatAmount(s?.expectedMass, "mass"), typed: c.typed.mass !== undefined };
  if (row.id === "expectedMoles") return { text: formatAmount(s?.expectedMoles, "moles") };
  if (row.id === "yield") return { text: formatAmount(s?.yield, "yield") };
  // Concentration: the one typed, bold, until amounts give it; worked out (plain) when every solvent's amount is typed.
  if (row.id === "conc") return c.role === "solvent" ? { text: formatAmount(s?.conc ?? v.conc, "molarity"), typed: v.conc !== undefined && (s?.conc === undefined || Math.abs(s.conc / v.conc - 1) < 1e-9) } : { text: "" };
  if (row.id === "equiv" && c.role === "catalyst") return { text: formatAmount(s?.equiv, "mol%"), typed: c.typed.equiv !== undefined };
  if (!row.field || (c.product && !["purity", "measured", "equiv"].includes(row.field))) return { text: "" };
  return { text: formatAmount(s?.[row.field as keyof typeof s] as number | undefined, row.field), typed: c.typed[row.field] !== undefined };
}
// Copy table: the table as shown, as tab-separated text for a spreadsheet or a document. In columns, a row naming the
// components (compound number, text or formula), then a row for each row shown; as rows, each section's title and
// quantities, then a row for each component. Then the conditions, a line each (lines: name and value). Hidden rows and
// columns are left out. Each value is one line, sheetSafe.
export function gridTsv(v: GridView, lines: [string, string][] = v.block?.lines.map((l) => [l.name, l.value]) ?? []): string {
  const name = (c: GridView["cols"][number]) => c.label ?? c.formula;
  const table = v.sections
    ? v.sections.flatMap((sec, k) => [...(k ? [[]] : []), [sec.title, ...sec.fields.map((row) => row.name)], ...sec.comps.map((c) => [name(c), ...sec.fields.map((row) => cellText(v, c, row).text)])])
    : [["", ...v.cols.map(name)], ...v.rows.map((row) => [row.name, ...v.cols.map((c) => cellText(v, c, row).text)])];
  const all: string[][] = [...table, ...(lines.length ? [[], ...lines] : [])];
  return all.map((r) => r.map((x) => sheetSafe(x.replace(/[\t\r\n]+/g, " "))).join("\t")).join("\n") + "\n";
}
// Hide empty rows: the rows shown with no value in any column shown.
export const emptyRows = (v: GridView) => v.rows.filter((row) => !v.cols.some((c) => cellText(v, c, row).text)).map((row) => row.id);

