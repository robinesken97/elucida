// GHS hazards from PubChem for the Properties panel's Find hazards (decision 0008): the classification PubChem shows
// first on a compound's page, read from PubChem's JSON as hostile (each value's type checked, texts and lists
// limited). And the nine GHS pictograms, drawn for Octet in the Symbols set's frame (a diamond of half-width 46, y
// down); the Symbols set's four GHS diamonds take theirs from here (tools/library/symbols.mjs).

// Each pictogram's name (as the Symbols set names it) and its parts: ink lines and solid areas, as SVG path data.
export const PICTOGRAMS: Record<string, { name: string; parts: ["ink" | "solid", string][] }> = {
  // A bomb: a ball and the rays of its burst.
  GHS01: { name: "Explosive", parts: [["solid", "M10 12A10 10 0 1 1 -10 12A10 10 0 1 1 10 12Z"], ["ink", "M0 -2L0 -26M8 0L18 -16M-8 0L-18 -16M12 8L28 2M-12 8L-28 2"]] },
  // A flame over a bar. Each flame is an outline that leans and licks up to its tip, with a smaller one inside, filled.
  GHS02: { name: "Flammable", parts: [
    ["ink", "M0 -30C8 -19 17 -13 15 2C14 11 8 16 0 16C-9 16 -16 10 -15 0C-14 -8 -8 -11 -6 -19C-2 -13 0 -15 0 -30Z"],
    ["solid", "M0 -8C4 -2 8 2 7 8C6 13 3 14 0 14C-4 14 -8 11 -7 6C-6 1 -2 -1 0 -8Z"], ["solid", "M-14 22L14 22L14 26L-14 26Z"]] },
  // A flame over a circle.
  GHS03: { name: "Oxidising", parts: [
    ["ink", "M0 -31.5C6 -23.25 12.75 -18.75 11.25 -7.5C10.5 -0.75 6 3 0 3C-6.75 3 -12 -1.5 -11.25 -9C-10.5 -15 -6 -17.25 -4.5 -23.25C-1.5 -18.75 0 -20.25 0 -31.5Z"],
    ["solid", "M0 -15C3 -10.5 6 -7.5 5.25 -3C4.5 0.75 2.25 1.5 0 1.5C-3 1.5 -6 -0.75 -5.25 -4.5C-4.5 -8.25 -1.5 -9.75 0 -15Z"],
    ["ink", "M8 12A8 8 0 1 1 -8 12A8 8 0 1 1 8 12Z"], ["solid", "M-12 25L12 25L12 28L-12 28Z"]] },
  // A gas cylinder on its side.
  GHS04: { name: "Gas under pressure", parts: [["ink", "M-24 6L16 6Q24 6 24 12Q24 18 16 18L-24 18Z"], ["ink", "M24 10L30 10L30 14L24 14"]] },
  // Two test tubes that drip onto two bars and eat into them.
  GHS05: { name: "Corrosive", parts: [
    ["ink", "M-20.66 -14.28L-8.66 -28.28Q-3 -29.5 -3.34 -23.72L-15.34 -9.72M20.66 -14.28L8.66 -28.28Q3 -29.5 3.34 -23.72L15.34 -9.72"],
    ["solid", "M-15.5 -3A2.5 2.5 0 1 1 -20.5 -3A2.5 2.5 0 1 1 -15.5 -3Z"], ["solid", "M20.5 -3A2.5 2.5 0 1 1 15.5 -3A2.5 2.5 0 1 1 20.5 -3Z"],
    ["solid", "M-23 9L-20 9L-18 12L-16 9L-6 9L-6 14L-23 14Z"], ["solid", "M6 9L16 9L18 12L20 9L23 9L23 14L6 14Z"]] },
  // A skull over crossed bones.
  GHS06: { name: "Acute toxicity", parts: [
    ["ink", "M-11 -8C-11 -22 11 -22 11 -8C11 -2 7 0 7 4L-7 4C-7 0 -11 -2 -11 -8Z"],
    ["solid", "M-1.5 -9A3 3 0 1 1 -7.5 -9A3 3 0 1 1 -1.5 -9Z"], ["solid", "M7.5 -9A3 3 0 1 1 1.5 -9A3 3 0 1 1 7.5 -9Z"],
    ["ink", "M-15 8L15 22M15 8L-15 22"]] },
  // An exclamation mark.
  GHS07: { name: "Harmful", parts: [["solid", "M-4 -24L4 -24L2 10L-2 10Z"], ["solid", "M4 20A4 4 0 1 1 -4 20A4 4 0 1 1 4 20Z"]] },
  // A head and shoulders, with a star on the chest.
  GHS08: { name: "Serious health hazard", parts: [
    ["ink", "M7 -18A7 7 0 1 1 -7 -18A7 7 0 1 1 7 -18Z"], ["ink", "M-16 22C-16 4 -10 -6 0 -6C10 -6 16 4 16 22Z"],
    ["solid", "M0 1.5L1.22 6.04L5.3 3.7L2.96 7.78L7.5 9L2.96 10.22L5.3 14.3L1.22 11.96L0 16.5L-1.22 11.96L-5.3 14.3L-2.96 10.22L-7.5 9L-2.96 7.78L-5.3 3.7L-1.22 6.04Z"]] },
  // A bare tree and a dead fish on the ground.
  GHS09: { name: "Hazardous to the environment", parts: [
    ["ink", "M-22 14L22 14M-10 14L-10 -20M-10 -6L-18 -14M-10 -12L-3 -19M-10 0L-3 -5"],
    ["solid", "M15 6A7.5 3.5 0 1 1 0 6A7.5 3.5 0 1 1 15 6Z"], ["solid", "M14 6L21 2L21 10Z"]] },
};

// What Find hazards shows for a compound: its PubChem CID, the source PubChem names for the classification, the
// pictograms by code (GHS01 to GHS09), the signal word, the hazard statements (each with its code, and its share of
// reports when the source gives one) and the precautionary statement codes.
export type Ghs = { cid: number; source?: string; pictograms: string[]; signal?: string; hazards: string[]; precautions: string[] };

type Section = { TOCHeading?: unknown; Section?: unknown; Information?: unknown; RecordNumber?: unknown; Reference?: unknown };
type Info = { ReferenceNumber?: unknown; Name?: unknown; Value?: { StringWithMarkup?: unknown } };
const list = <T>(v: unknown): T[] => (Array.isArray(v) ? v : []);
const text = (v: unknown, most = 400) => (typeof v === "string" && v.length <= most ? v.trim() || undefined : undefined);
const MOST = 60; // statements kept from one list

// PubChem's JSON for a compound's GHS Classification (PUG View, under Safety and Hazards): the first source's
// classification, as PubChem's own page shows it. Undefined when the text is not that JSON.
export function ghsOf(json: string): Ghs | undefined {
  let record: Section | undefined;
  try { record = (JSON.parse(json) as { Record?: Section } | null)?.Record; } catch { return undefined; }
  const cid = record?.RecordNumber;
  if (typeof cid !== "number" || !Number.isSafeInteger(cid) || cid < 1) return undefined;
  // The answer holds only the way down to the one section: Safety and Hazards, Hazards Identification, then it.
  let section: Section | undefined = record;
  for (let depth = 0; section && section.TOCHeading !== "GHS Classification" && depth < 4; depth++) section = list<Section>(section.Section)[0];
  if (section?.TOCHeading !== "GHS Classification") return undefined;
  const all = list<Info>(section.Information), ref = all[0]?.ReferenceNumber, first = all.filter((i) => i?.ReferenceNumber === ref);
  const strings = (name: string) => first.filter((i) => i?.Name === name).flatMap((i) => list<{ String?: unknown; Markup?: unknown }>(i.Value?.StringWithMarkup)).slice(0, MOST);
  const pictograms = [...new Set(strings("Pictogram(s)").flatMap((s) => list<{ URL?: unknown }>(s?.Markup)).map((m) => /\/(GHS0[1-9])\.svg$/.exec(text(m?.URL) ?? "")?.[1]).filter((c) => c !== undefined))];
  const signal = strings("Signal").map((s) => text(s?.String, 20)).find(Boolean);
  // Each statement with its code, without the class and category PubChem puts after it in brackets.
  const lines = strings("GHS Hazard Statements").map((s) => text(s?.String)).filter((s) => s !== undefined);
  const hazards = lines.filter((s) => /^(?:EUH|H)\d{3}/.test(s)).map((s) => s.replace(/\s*\[[^\]]*\]$/, ""));
  if (!hazards.length && lines.some((s) => /^not classified$/i.test(s))) hazards.push("Not classified");
  const codes = strings("Precautionary Statement Codes").map((s) => text(s?.String, 2000) ?? "").join(" ");
  const precautions = [...new Set(codes.match(/P\d{3}(?:\+P\d{3})*/g) ?? [])].slice(0, MOST);
  const source = text(list<{ ReferenceNumber?: unknown; SourceName?: unknown }>(record?.Reference).find((r) => r?.ReferenceNumber === ref)?.SourceName, 200);
  return { cid, ...(source ? { source } : {}), pictograms, ...(signal ? { signal } : {}), hazards, precautions };
}
