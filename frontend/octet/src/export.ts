// Modified for Elucida (Apache-2.0 §4b): see frontend/octet/UPSTREAM.md for the changes to this file.
import { EMBEDDED, host } from "./elucida.ts";
// Export and the Office clipboard (src-tauri/src/export.rs and clipboard.rs). standaloneSvg turns the drawing on a
// canvas into a standalone SVG at true size; the app makes a PDF or PNG of it, puts it on the clipboard with the
// structure, and reads structures back on paste.

import { invoke } from "@tauri-apps/api/core";

// Octet's own layers, not part of the drawing: page marks and grid, selection (its frame and resize handles too),
// hover, reaction interpretation, NMR shifts, problems, handles, guides, the rubber band, the eraser and the rest.
export const UI = [
  "pages", "grid", "selection-marks", "frame-marks", "nmr-marks", "nmr-shift", "problem-mark", "mark", "arrow-mark", "suggested",
  "ghost", "pen-points", "mapping", "handle", "turn-handle", "turn-centre", "turn-angle", "box", "trail", "erase-marks", "brush",
  "count", "guide", "snap-point", "spot-picked", "lane-picked", "group-frame", "grid-pick", "interpretation",
].map((c) => `.${c}`).join(",");

// Inherited properties: written where an element's value differs from its parent's.
const INHERITED = [
  "fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-opacity", "stroke-dasharray", "stroke-dashoffset",
  "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "paint-order", "font-family", "font-size", "font-style",
  "font-weight", "text-anchor", "letter-spacing", "word-spacing", "visibility",
];
// The rest: written where they differ from the default (as WebKit or Chromium reports it).
const OWN: [string, string[]][] = [
  ["opacity", ["1"]], ["stop-color", ["rgb(0, 0, 0)"]], ["stop-opacity", ["1"]], ["dominant-baseline", ["auto"]],
  ["baseline-shift", ["baseline", "0px"]], ["text-decoration-line", ["none"]], ["filter", ["none"]], ["clip-path", ["none"]], ["mask", ["none"]],
];

// url("http://localhost/#shade3") as a standalone SVG needs it: url(#shade3).
const local = (v: string) => v.replace(/url\(\s*(["']?)[^#"')]*#([^"')]+)\1\s*\)/g, "url(#$2)");

// The drawing on `canvas` (an <svg> whose first <g> holds the drawing in px at 100%, as the editor's canvas does)
// as a standalone SVG: only what is inside `bounds` (px, in that <g>'s frame), at true size with 1 user unit = 1 pt
// (`ptPerPx` points per px), its edges rounded outward to whole points. Octet's own layers are left out. Colours
// are written out as on white paper (the light theme's ink and paper), so CSS variables and classes are no longer
// needed. Everything in the canvas inside the bounds is drawn: for a part of the drawing, pass a canvas showing
// only that part.
export function standaloneSvg(canvas: SVGSVGElement, bounds: [number, number, number, number], ptPerPx: number): string {
  const [x0, y0] = [Math.floor(bounds[0] * ptPerPx), Math.floor(bounds[1] * ptPerPx)];
  const [w, h] = [Math.max(1, Math.ceil(bounds[2] * ptPerPx) - x0), Math.max(1, Math.ceil(bounds[3] * ptPerPx) - y0)];
  // The light theme for a moment: nothing is painted before the attributes go back. The colours go back through
  // element.style, as the CSP allows no style attribute.
  const saved = ["data-theme", "class"].map((a) => [a, canvas.getAttribute(a)] as const);
  const colours = ["--ink", "--canvas"].map((k) => [k, canvas.style.getPropertyValue(k)] as const);
  canvas.setAttribute("data-theme", "light");
  canvas.setAttribute("class", "canvas");
  canvas.style.removeProperty("--ink");
  canvas.style.removeProperty("--canvas");
  try {
    const copy = canvas.cloneNode(true) as SVGSVGElement;
    const live = [canvas, ...canvas.querySelectorAll("*")], out = [copy, ...copy.querySelectorAll("*")];
    const styles = new Map<Element, CSSStyleDeclaration>();
    const css = (el: Element) => styles.get(el) ?? styles.set(el, getComputedStyle(el)).get(el)!;
    const drop: Element[] = [];
    live.forEach((el, i) => {
      const to = out[i], ui = el === canvas ? null : el.closest(UI);
      if ((ui && canvas.contains(ui)) || /^(script|foreignObject)$/i.test(el.localName)) return void drop.push(to);
      const s = css(el), parent = el === canvas ? undefined : css(el.parentElement!);
      for (const k of INHERITED) {
        const v = s.getPropertyValue(k);
        if (v && v !== parent?.getPropertyValue(k)) to.setAttribute(k, local(v));
      }
      for (const [k, initial] of OWN) {
        const v = s.getPropertyValue(k);
        if (v && !initial.includes(v)) to.setAttribute(k === "text-decoration-line" ? "text-decoration" : k, local(v));
      }
      if (s.whiteSpace.startsWith("pre")) to.setAttributeNS("http://www.w3.org/XML/1998/namespace", "xml:space", "preserve");
      for (const a of [...to.attributes]) if (/^(style|class|role|tabindex|aria-|data-|on)/i.test(a.name)) to.removeAttribute(a.name);
    });
    if (EMBEDDED) live.forEach((el, i) => {
      if (el.localName !== "text" || !el.querySelector("tspan") || el.closest(UI)) return;
      // MuPDF/Office do not consistently lay out nested, centred tspans with dy
      // (e.g. K₂CO₃). Freeze each text run at the browser's measured baseline.
      const text = el as SVGTextElement, to = out[i], runs: Element[] = [];
      const walker = document.createTreeWalker(text, NodeFilter.SHOW_TEXT);
      let index = 0, node: Node | null;
      while ((node = walker.nextNode())) {
        const value = node.textContent ?? "";
        if (!value.length) continue;
        const point = text.getStartPositionOfChar(index);
        const span = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
        span.setAttribute("x", String(point.x));
        span.setAttribute("y", String(point.y));
        const style = css(node.parentElement!);
        for (const key of INHERITED) {
          if (key === "text-anchor") continue;
          const value = style.getPropertyValue(key);
          if (value) span.setAttribute(key, local(value));
        }
        const decoration = style.getPropertyValue("text-decoration-line");
        if (decoration && decoration !== "none") span.setAttribute("text-decoration", decoration);
        span.setAttributeNS("http://www.w3.org/XML/1998/namespace", "xml:space", "preserve");
        span.textContent = value;
        runs.push(span);
        index += value.length;
      }
      to.replaceChildren(...runs);
      to.setAttribute("text-anchor", "start");
    });
    for (const el of drop) el.remove();
    // Groups that held only Octet's own layers (a hover mark's, for one) go too, innermost first.
    for (const g of [...copy.querySelectorAll("g")].reverse()) if (!g.firstElementChild) g.remove();
    // The view's pan and zoom give way to px → pt.
    copy.querySelector(":scope > g")?.setAttribute("transform", `scale(${+ptPerPx.toFixed(6)})`);
    copy.setAttribute("width", `${w}pt`);
    copy.setAttribute("height", `${h}pt`);
    copy.setAttribute("viewBox", `${x0} ${y0} ${w} ${h}`);
    return new XMLSerializer().serializeToString(copy);
  } finally {
    for (const [a, v] of saved) if (v === null) canvas.removeAttribute(a); else canvas.setAttribute(a, v);
    for (const [k, v] of colours) if (v) canvas.style.setProperty(k, v);
  }
}

// Copy: the picture (standaloneSvg of the selection, with the selection's CDXML hidden in it: on the Mac a PDF, on
// Windows an EMF, on Linux a PNG), then CDX, the CDXML as its own type (cdxmlType), its molfile, SMILES and Octet's
// JSON, on the clipboard as ChemDraw puts them on each system (src-tauri/src/clipboard.rs). Each left out is not put
// on. Call it from the copy event after preventDefault(), and set nothing on clipboardData: plain text would make
// ChemDraw paste a caption. With `text`, only that text goes on (Edit > Copy As).
// dpi: the export resolution, which the PNG and bitmap on Windows and Linux take (as ChemDraw's Copy As PNG takes
// its Save As PNG resolution), at most 16 million pixels.
export const copyToClipboard = (c: { dpi?: number; svg?: string; cdxml?: string; cdxmlType?: boolean; cdx?: string; molfile?: string; smiles?: string; octetJson?: string; text?: string }) =>
  EMBEDDED ? host<void>("copy", c) : invoke<void>("copy_to_clipboard", c);

// What paste can use from the clipboard, each null when absent: Octet's JSON; CDXML (ChemDraw's CDXML type, or
// hidden in a pasted picture: Octet's, ChemDraw's, or either copied back out of Word); ChemDraw's CDX as base64;
// a molfile or RXN file; SMILES. All of it comes from another program: read it as a hostile file.
export type Clipboard = { octet: string | null; cdxml: string | null; cdx: string | null; molfile: string | null; smiles: string | null; text: string | null; picture: string | null; spectrum?: [string, string] | null };
export const readClipboard = () => EMBEDDED ? host<Clipboard>("paste") : invoke<Clipboard>("read_clipboard");

export type ExportFormat = "oct" | "pdf" | "svg" | "png" | "emf" | "eps" | "tif" | "jpg" | "gif" | "cdxml" | "cdx" | "mol" | "mol2000" | "sdf" | "sdf2000" | "rxn" | "rxn2000" | "rdf" | "rdf2000" | "smi" | "inchi";
// The pictures: vector (PDF, SVG, EMF, EPS) and pixels at a resolution (PNG, TIFF, JPEG, GIF; JPEG is always on white).
export const PICTURES: ExportFormat[] = ["pdf", "png", "svg", "emf", "eps", "tif", "jpg", "gif"];
export const RASTERS: ExportFormat[] = ["png", "tif", "jpg", "gif"];
// The pictures that carry the drawing's CDXML (the PDF as ChemDraw's does, the EMF in a comment, the PNG in a chunk), so
// they open, drop and paste back into Octet as the drawing, from a file or copied back out of Word.
export const CARRY_CDXML: ExportFormat[] = ["pdf", "png", "emf"];
// A picture format's short name, as Quick export's menu item says it.
export const shortName = (f: ExportFormat) => (f === "tif" ? "TIFF" : f === "jpg" ? "JPEG" : f.toUpperCase());
// The MDL formats, each V3000 (as ChemDraw 26.1 saves them) and V2000, as ChemDraw lists them.
export const MDL: ExportFormat[] = ["mol", "mol2000", "sdf", "sdf2000", "rxn", "rxn2000", "rdf", "rdf2000"];
// Every format, with its name in Export and Settings.
export const EXPORT_FORMATS: [ExportFormat, string][] = [["oct", "Octet drawing (.oct)"], ["pdf", "PDF"], ["png", "PNG"], ["svg", "SVG"], ["emf", "EMF (Windows Office)"], ["eps", "EPS"],
  ["tif", "TIFF"], ["jpg", "JPEG"], ["gif", "GIF"], ["cdxml", "CDXML (ChemDraw)"], ["cdx", "CDX (ChemDraw)"], ["mol", "MOL"], ["mol2000", "MOL V2000"],
  ["sdf", "SDF"], ["sdf2000", "SDF V2000"], ["rxn", "RXN"], ["rxn2000", "RXN V2000"], ["rdf", "RDF"], ["rdf2000", "RDF V2000"], ["smi", "SMILES"], ["inchi", "InChI"]];
// A picture from standaloneSvg with a margin of `pt` all round: its size and view box grow by that much.
export function withMargin(svg: string, pt: number): string {
  const m = Math.max(0, Math.min(72, pt));
  return svg.replace(/^(<svg[^>]*?)\swidth="([\d.]+)pt"\sheight="([\d.]+)pt"\sviewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"/, (_, head, w, h, x, y, vw, vh) =>
    `${head} width="${+w + 2 * m}pt" height="${+h + 2 * m}pt" viewBox="${+x - m} ${+y - m} ${+vw + 2 * m} ${+vh + 2 * m}"`);
}
// Raster resolution: any dpi from 36 to 2400 (Rust clamps to the same), with these as quick picks (1440 is ChemDraw's
// highest). A picture has at most 100 million pixels and 20,000 on a side (draw in src-tauri/src/export.rs).
export const DPI_MIN = 36, DPI_MAX = 2400, MAX_PIXELS = 100e6, MAX_SIDE = 20000;
export const DPIS = [72, 150, 300, 350, 600, 1200, 1440];
// Pixels across `pt` points at `dpi`, as export.rs counts them (a part pixel counts, a rounding error does not).
export const pixelsAt = (pt: number, dpi: number) => Math.max(1, Math.ceil((pt * dpi) / 72 - 0.01));
// The dpi that makes `pt` points `px` pixels across, kept in range.
export const dpiFor = (px: number, pt: number) => Math.max(DPI_MIN, Math.min(DPI_MAX, (px * 72) / pt));
export const tooLarge = (w: number, h: number) => w > MAX_SIDE || h > MAX_SIDE || w * h > MAX_PIXELS;
// A picture from withMargin on a background colour (#rrggbb), the whole view box filled behind the drawing.
export function withBackground(svg: string, hex: string): string {
  if (!/^#[0-9a-f]{6}$/i.test(hex)) return svg;
  const box = /^<svg[^>]*?\sviewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"[^>]*>/.exec(svg);
  return box ? `${box[0]}<rect x="${box[1]}" y="${box[2]}" width="${box[3]}" height="${box[4]}" fill="${hex}"/>${svg.slice(box[0].length)}` : svg;
}
// A picture as a format saves it: with the margin, and for a raster format its background. Transparent only where the
// format has it (JPEG has none); "page" is the drawing's own page colour (`page`), and white when it has none.
export function pictureAs(svg: string, f: { format: ExportFormat; margin: number; background: "white" | "transparent" | "page" }, page?: string): { svg: string; transparent: boolean } {
  const m = withMargin(svg, f.margin), raster = RASTERS.includes(f.format);
  if (raster && f.background === "page" && page) return { svg: withBackground(m, page), transparent: false };
  return { svg: m, transparent: raster && f.format !== "jpg" && f.background === "transparent" };
}
// File > Export…: the drawing in every form the page has (svg from standaloneSvg). The app asks where to save,
// offering those formats (or only `format`), and writes the one the file name's extension asks for. The PDF, PNG
// and EMF carry the CDXML (CARRY_CDXML), as on the clipboard. PNG at `dpi` of true size (300 if not given), white unless
// `transparent`; JPEG at `quality` (1 to 100, 95 if not given). mdl: the text of the MDL format asked for; csv: Home's
// Experiments list. Resolves to the path written, or null if cancelled.
export type ExportRequest = {
  name: string; format?: ExportFormat | "csv"; csv?: string; oct?: string; svg?: string; cdxml?: string; cdx?: string; mdl?: string; smiles?: string; inchi?: string;
  dpi?: number; transparent?: boolean; quality?: number;
};
export const exportFile = (request: ExportRequest) => invoke<string | null>("export_file", { export: request });
