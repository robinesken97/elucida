import { extractSelection } from './edit.ts';
import type { Mol, Caption } from './render.ts';
import type { Reaction } from './reaction.ts';
// Coordinates are y-up. Only the uppermost reaction row is a publication figure.
export function upperReaction(doc: Mol, reaction: (id: number) => Reaction | undefined, at?: (c: Caption) => [number, number] | undefined): Mol | undefined {
 const arrows = (doc.arrows ?? []).filter(a => ['reaction','equilibrium','retro','nogo','resonance'].includes(a.kind))
   // A resonance arrow above the synthesis is no reaction; it only counts if nothing else exists.
   .sort((a,b) => Number(a.kind==='resonance') - Number(b.kind==='resonance') || Math.max(...[b.from[1],b.to[1]]) - Math.max(a.from[1],a.to[1]) || a.from[0]-b.from[0]);
 const r = arrows.map(a => reaction(a.id)).find(x => x?.atoms.length); // stray arrows without structures are skipped
 if (!r) return undefined;
 const part = extractSelection(doc, new Set(r.atoms), new Set([...r.arrows,...r.captions,...r.carried]), at);
 // No workspace tables, spectra or hidden metadata from the rest of the document.
 return {...part, grids: undefined, spectra: undefined, shapes: part.shapes?.filter(s => !s.table)};
}
