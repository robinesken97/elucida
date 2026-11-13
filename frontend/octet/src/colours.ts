// Octet's one colour system (Sam, 11 November 2026): every colour menu lists the same parts in the same order
// (colourOptions), and the recent colours are shared by every menu, document and window. ColourPicker.tsx draws them.
import { COLOURS, RING_FILLS, TINTS } from "./docstyle.ts";
import type { Swatch } from "./settings.ts";

export const OWN_MOST = 100; // the user's own colours
export const RECENT_MOST = 8;
export const PICK = "\u0000pick", ADD = "\u0000add"; // Pick from screen and Add colour…
export type ColourOption = { key: string; name: string; hex?: string };

// The recent colours, newest first, kept on this computer as the recent characters are (CharMap.tsx). Another window's
// change reaches this one as a storage event.
const RECENT = "octet.colours.recent", HEX = /^#[0-9a-f]{6}$/i;
let recent: string[] | undefined;
export function recentColours(): string[] {
  if (recent) return recent;
  try {
    const v = JSON.parse(localStorage.getItem(RECENT) ?? "[]");
    recent = Array.isArray(v) ? v.filter((h) => typeof h === "string" && HEX.test(h)).slice(0, RECENT_MOST) : [];
  } catch {
    recent = [];
  }
  return recent;
}
export function rememberColour(hex: string) {
  if (!HEX.test(hex)) return;
  recent = [hex, ...recentColours().filter((h) => h.toLowerCase() !== hex.toLowerCase())].slice(0, RECENT_MOST);
  try { localStorage.setItem(RECENT, JSON.stringify(recent)); } catch { /* storage is optional */ }
}
if (typeof addEventListener === "function") addEventListener("storage", (e) => { if (e.key === RECENT) recent = undefined; });

// A colour menu's options, in groups: the recent colours, then None (where it applies), the preset colours and the
// colour chosen now when it is none of them (Custom), then the user's own colours (with the drawing's after them),
// then Pick from screen and Add colour…. Each key is its own (r3, o3), so only one option shows as chosen (chosenKey).
// A recent colour has its name from this menu, the user's colours or Octet's other lists, else its hex.
export function colourOptions(presets: [string, string][], own: Swatch[], value?: string, none = false, latest = recentColours()): ColourOption[][] {
  const same = (a: string, b?: string) => a.toLowerCase() === b?.toLowerCase();
  const named = (hex: string) => presets.find(([, h]) => same(h, hex))?.[0] ?? own.find((c) => same(c.hex, hex))?.name ?? [...COLOURS, ...TINTS, ...RING_FILLS].find(([, h]) => same(h, hex))?.[0] ?? hex.toUpperCase();
  const known = value === "none" || !value || latest.some((h) => same(h, value)) || presets.some(([, h]) => same(h, value)) || own.some((c) => same(c.hex, value));
  return [
    latest.map((hex, k) => ({ key: `r${k}`, name: named(hex), hex })),
    [...(none ? [{ key: "none", name: "None" }] : []), ...presets.map(([name, hex]) => ({ key: hex, name, hex })), ...(known ? [] : [{ key: value!, name: "Custom", hex: value }])],
    own.map((c, k) => ({ key: `o${k}`, name: c.name, hex: c.hex })),
    [{ key: PICK, name: "Pick from screen" }, { key: ADD, name: "Add colour…" }],
  ];
}
// The option shown as chosen: the first with the colour chosen now (None for "none").
export const chosenKey = (groups: ColourOption[][], value?: string) =>
  groups.flat().find((o) => (o.hex ? o.hex.toLowerCase() === value?.toLowerCase() : o.key === "none" && value === "none"))?.key;
// The user's own colour an option is (o3), or -1.
export const ownIndex = (key: string | undefined, own: Swatch[]) => { const k = /^o(\d+)$/.exec(key ?? "") ? Number(key!.slice(1)) : -1; return k < own.length ? k : -1; };

// The user's own colours with one moved from one place to another, and with a colour added (once, at the end).
export const moveColour = (own: Swatch[], from: number, to: number) => { const next = own.filter((_, k) => k !== from); next.splice(to, 0, own[from]); return next; };
export const addColour = (own: Swatch[], hex: string) =>
  own.some((c) => c.hex.toLowerCase() === hex.toLowerCase()) || own.length >= OWN_MOST ? own : [...own, { name: `Colour ${own.length + 1}`, hex }];

// A colour as the browser computes it (rgb(r, g, b), rgba(…) or #rrggbb) as #RRGGBB; undefined for none, a clear
// colour or a gradient.
export function hexOf(css: string): string | undefined {
  const m = /^rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)(?:[,\s/]+([\d.]+)(%?))?\)$/.exec(css.trim());
  if (m) return m[4] !== undefined && Number(m[4]) === 0 ? undefined : `#${m.slice(1, 4).map((v) => Math.min(255, Number(v)).toString(16).padStart(2, "0")).join("").toUpperCase()}`;
  return HEX.test(css.trim()) ? css.trim().toUpperCase() : undefined;
}
// Colour by Element is a toggle: whether every heteroatom among these atoms (scope: their indices) has its element's
// colour already, so the command puts them back in the document's ink. by: each element's colour. False with none.
export function elementColoursOn(atoms: { label: string; colour?: string }[], scope: Set<number>, by: Record<string, string>): boolean {
  const own = atoms.filter((a, i) => scope.has(i) && by[a.label]);
  return own.length > 0 && own.every((a) => a.colour?.toLowerCase() === by[a.label].toLowerCase());
}
