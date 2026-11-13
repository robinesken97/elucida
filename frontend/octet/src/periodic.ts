// The Text tool's periodic table (PeriodicTable.tsx, issue 71): where each element sits, what it shows for one, and
// where the arrow keys go. Names are metals.ts's (IUPAC's, British), masses and abundances NIST's (isotopes.ts).
import { ISOTOPES } from "./isotopes.ts";
import { atomMass } from "./mass.ts";
import { ELEMENTS } from "./metals.ts";

// Every element in order of atomic number, as metals.ts lists them.
export const SYMBOLS = [...ELEMENTS.keys()];

// Element z's cell as [row, column] in the 18-column table: periods 1 to 7 in rows 1 to 7, and La to Lu and Ac to Lr in
// rows 9 and 10 under groups 3 to 17 (row 8 is the gap over them). Group 3 of periods 6 and 7 stays empty.
const STARTS = [3, 11, 19, 37, 55, 87]; // the first element of periods 2 to 7
export function cellOf(z: number): [number, number] {
  if (z <= 2) return [1, z === 1 ? 1 : 18];
  let p = 0;
  while (z >= STARTS[p + 1]) p++;
  const period = p + 2, i = z - STARTS[p];
  if (period <= 3) return [period, i < 2 ? i + 1 : i + 11];
  if (period <= 5 || i < 2) return [period, i + 1];
  return i < 17 ? [period + 3, i + 1] : [period, i - 13];
}

// What the table shows for an element: its number, name, atomic weight (its isotopes' masses averaged by abundance)
// and its isotopes as [mass number, abundance in %]. An element with no natural isotopes has neither.
export function elementFacts(symbol: string) {
  const name = ELEMENTS.get(symbol) ?? symbol;
  return {
    z: SYMBOLS.indexOf(symbol) + 1, name: name[0].toUpperCase() + name.slice(1), weight: atomMass(symbol),
    isotopes: (ISOTOPES[symbol] ?? []).map(([m, a]) => [Math.round(m), a] as [number, number]),
  };
}

// Where an arrow key goes from element z: left and right along the atomic numbers, up and down to the nearest element
// in the next row that has one. Undefined at an edge, or for any other key.
export function stepFrom(z: number, key: string): number | undefined {
  if (key === "ArrowLeft" || key === "ArrowRight") {
    const n = z + (key === "ArrowLeft" ? -1 : 1);
    return n >= 1 && n <= SYMBOLS.length ? n : undefined;
  }
  const d = key === "ArrowUp" ? -1 : key === "ArrowDown" ? 1 : 0, [row, col] = cellOf(z);
  for (let r = row + d; d && r >= 1 && r <= 10; r += d) {
    const there = SYMBOLS.map((_, k) => k + 1).filter((n) => cellOf(n)[0] === r);
    if (there.length) return there.reduce((a, b) => (Math.abs(cellOf(b)[1] - col) < Math.abs(cellOf(a)[1] - col) ? b : a));
  }
  return undefined;
}
