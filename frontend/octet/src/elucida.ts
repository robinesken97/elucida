// Elucida embedding adapter. Native privileges are restricted by the Qt host.
export const EMBEDDED = new URLSearchParams(globalThis.location?.search ?? "").has("elucida");
export const DE = new URLSearchParams(globalThis.location?.search ?? "").get("lang") !== "en";
export const tr = (de: string, en: string) => DE ? de : en;
export type AssetRef = {shapeId:number; key:string; kind:"profile"|"orbital"};
export type FigureBundle = {cdxml:string; cdx:string; svg:string};
export type Bundle = { si?: FigureBundle | null; tables?: unknown[]; assets?: AssetRef[]; cdxml: string; cdx: string; svg: string; reagents: {id: number; text: string; substance: string; equiv?: number}[] };
declare global {
 interface Window {
  elucida?: {load: (text: string, name: string) => Record<string, number>; snapshot: () => Bundle; command: (id: string) => void; markSaved: () => void; dirty: boolean; theme: (dark:boolean) => void;
    putAsset: (asset: import("./elucida-assets.ts").AssetInput, target?:number) => number;
    assets: () => AssetRef[]; selectedAsset: () => AssetRef|undefined};
  elucidaHost?: {call: (method: string, args: string, cb: (result: string) => void) => void; state: (dirty: boolean) => void};
 }
}
export function host<T>(method: string, args: unknown = {}): Promise<T> {
 return new Promise((resolve, reject) => {
  if (!window.elucidaHost) return reject(new Error("Elucida bridge is not ready"));
  window.elucidaHost.call(method, JSON.stringify(args), (raw) => {
   try { const r = JSON.parse(raw); if (r.error) reject(new Error(r.error)); else resolve(r.value as T); } catch(e) { reject(e); }
  });
 });
}
// Split at list separators only outside brackets; decimal commas stay part of a number.
export function reagentLabels(text: string): {text: string; substance: string; equiv?: number}[] {
 const parts: string[] = []; let depth = 0, start = 0;
 for (let i=0;i<text.length;i++) {
  const c=text[i]; if (c==='(' || c==='[') depth++; else if(c===')' || c===']') depth=Math.max(0,depth-1);
  if (depth===0 && (c===';' || c==='\n' || (c===',' && !( /\d/.test(text[i-1]??'') && /\d/.test(text[i+1]??''))))) {parts.push(text.slice(start,i));start=i+1;}
 }
 parts.push(text.slice(start));
 return parts.map(p=>p.trim()).filter(Boolean).map(text=> {
  const m=/\s*\(\s*(\d+(?:[.,]\d+)?)\s*(eq\.?|equiv\.?|Äq\.?|mol\s*%)\s*\)\s*$/i.exec(text);
  return {text, substance: m ? text.slice(0,m.index).trim() : text, ...(m ? {equiv: Number(m[1].replace(',','.')) * (/mol/i.test(m[2]) ? .01 : 1)} : {})};
 });
}
