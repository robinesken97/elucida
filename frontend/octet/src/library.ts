// Octet's template library, built by tools/library/build.mjs: structures from their names (amino acids, sugars,
// heterocycles, ligands and more), each drawn at bond length 1 and centred; structures drawn in perspective
// (conformers, hexoses, paddlewheels, tools/library/perspective.mjs) and with π ligands (Cp and arene rings,
// metallocenes, tools/library/organometallics.mjs), kept whole as mol; and drawings (the Lab group, Lab equipment,
// Biomolecules, Cells and more: pen curves and lines in one integral group, tools/library/lab.mjs and art.mjs). A template's variant name in the Ring tool's list
// is "lib:" and its name. also: more words the library search finds it by. icon: the part of a Lab item its 20 px icon
// draws.
import data from "./library.json" with { type: "json" };
import type { Arrow, Group, Mol } from "./render.ts";

export type LibraryItem = { kind: string; name: string; category: string; mol: Mol; also?: string; icon?: Mol };
type Raw = { name: string; items: { name: string; also?: string; atoms?: (string | number)[][]; bonds?: number[][]; arrows?: Arrow[]; groups?: Group[]; icon?: number[]; mol?: Mol }[] }[];

type Set = { name: string; items: LibraryItem[] };
const read = (c: Raw[number]): Set => ({
  name: c.name,
  items: c.items.map((t) => ({
    kind: `lib:${t.name}`, name: t.name, category: c.name, ...(t.also ? { also: t.also } : {}),
    ...(t.icon && t.arrows ? { icon: { atoms: [], bonds: [], arrows: t.arrows.filter((a) => t.icon!.includes(a.id)) } } : {}),
    mol: t.mol ?? {
      atoms: (t.atoms ?? []).map(([label, x, y, charge, radical]) => ({ label: label as string, location: [x as number, y as number, 0] as [number, number, number], ...(charge ? { charge: charge as number } : {}), ...(radical ? { radical: radical as number } : {}) })),
      bonds: (t.bonds ?? []).map(([a, b, type, stereo]) => ({ atoms: [a, b] as [number, number], type, ...(stereo ? { stereo } : {}) })),
      ...(t.arrows ? { arrows: t.arrows } : {}), ...(t.groups ? { groups: t.groups } : {}),
    },
  })),
});
// The sets Octet reads as it starts. The rest (library-more.json, about three times as large) load once the window is
// idle, or at once when the library opens, so starting is no slower than with 1.1's library; loadMore adds them here.
export const LIBRARY: Set[] = (data as Raw).map(read);
// Templates renamed to the abbreviations common.ts cites, under their old names too, so one kept in the Ring strip stays.
const RENAMED: Record<string, string> = { bipy: "bpy", terpy: "tpy", pybox: "PyBOX" };
// Clip art: a template with no atoms (Lab, Cells, Symbols and the other drawn sets), as against a structure. A set is
// clip art when all its templates are (ART_SETS, by name). The library, View > Templates and the command palette keep
// the two apart.
// The Photochemistry set has no atoms either, but it is notation for schemes (light and heat on an arrow, state labels,
// a Jablonski diagram), so it shows with the structures.
const NOTATION_SETS = new Set(["Photochemistry"]), notation = new Set<string>();
export const isArt = (t: LibraryItem) => !t.mol.atoms.length && !notation.has(t.kind);
export const ART_SETS = new Set<string>();
const byKind = new Map<string, LibraryItem>();
const index = () => {
  for (const c of LIBRARY) for (const t of c.items) byKind.set(t.kind, t);
  for (const [from, to] of Object.entries(RENAMED)) { const t = byKind.get(`lib:${to}`); if (t) byKind.set(`lib:${from}`, t); }
  notation.clear();
  for (const c of LIBRARY) if (NOTATION_SETS.has(c.name)) for (const t of c.items) notation.add(t.kind);
  ART_SETS.clear();
  for (const c of LIBRARY) if (c.items.every(isArt)) ART_SETS.add(c.name);
};
index();
export const libraryItem = (kind: string) => byKind.get(kind);

// The later sets: each new set in its place in the order the build gives, and a set Octet has already (Lab) grown by
// its later items. The promise is kept, so the file is fetched and read once.
let more: Promise<void> | undefined;
export function loadMore(): Promise<void> {
  more ??= import("./library-more.ts").then(({ default: later }) => {
    const { order, sets } = later as { order: string[]; sets: Raw };
    for (const raw of sets) {
      const set = read(raw), have = LIBRARY.find((c) => c.name === set.name);
      if (have) { have.items.push(...set.items); continue; }
      const after = order.slice(0, order.indexOf(set.name)).reverse().find((n) => LIBRARY.some((c) => c.name === n));
      LIBRARY.splice(after ? LIBRARY.findIndex((c) => c.name === after) + 1 : 0, 0, set);
    }
    index();
  });
  return more;
}
// In the app, once the window is idle after starting (a template kept in the Ring strip from a later set then draws).
// WebKit has no requestIdleCallback everywhere: then 1.5 s after starting.
if (typeof window !== "undefined" && typeof window.requestAnimationFrame === "function") {
  const later = () => void loadMore();
  if (typeof window.requestIdleCallback === "function") window.requestIdleCallback(later, { timeout: 3000 });
  else setTimeout(later, 1500);
}
