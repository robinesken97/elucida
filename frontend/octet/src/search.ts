// The online searches (decision 0008): the commands, and the structure the page gives the app to search.
import { toInchiKey, toQueryMolfile, toSmiles } from "./chem.ts";
import type { Mol } from "./render.ts";

export type Site = "reaxys" | "pubchem" | "scifinder" | "scholar" | "patents";
// Each search: the site, and whether it looks for the same structure. Search Reaxys looks for substructures, as
// ChemDraw's Search Reaxys does; Search PubChem and Search Google Patents for the same structure. SciFinder and
// Google Scholar choose for themselves.
export const SEARCHES: Record<string, [Site, boolean]> = {
  search_reaxys: ["reaxys", false], search_reaxys_exact: ["reaxys", true], search_pubchem: ["pubchem", true], search_pubchem_sub: ["pubchem", false],
  search_scifinder: ["scifinder", false], search_scholar: ["scholar", true], search_patents: ["patents", true],
};

// One search a second at most. A held key repeats its menu command, and each search opens a browser tab and asks the
// site again (decision 0008: never a search in a loop).
let last = -Infinity;
export function searchNow(now = Date.now()): boolean {
  if (now - last < 1000) return false;
  last = now;
  return true;
}

// A molfile when the structure has generic labels (a query: always a substructure search). Otherwise SMILES,
// without the CXSMILES part after a space, which the sites do not read.
export function searchQuery(part: Mol): { smiles?: string; molfile?: string } {
  const molfile = toQueryMolfile(part);
  return molfile ? { molfile } : { smiles: toSmiles(part).split(/\s/)[0] };
}

// Google Scholar finds words, not structures: each structure's name as a phrase, or its InChIKey where Octet has no
// name for it.
export const scholarText = (named: { bare?: string; mol: Mol }[]): string => named.map((n) => `"${n.bare ?? toInchiKey(n.mol)}"`).join(" ");
