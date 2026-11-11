// Elucida-generated figures are ordinary movable pictures with a PNG fallback
// for ChemDraw and a vector representation retained in Octet's own payload.
import type { Mol, Shape } from "./render.ts";
import { readPictureData } from "./cdxml.ts";

export type ElucidaAsset = { key: string; kind: "profile" | "orbital"; svg?: string };
export type AssetInput = ElucidaAsset & { png: string; width: number; height: number };

export function readAsset(value: unknown): ElucidaAsset | undefined {
  if (!value || typeof value !== "object") return undefined;
  const a = value as Record<string, unknown>;
  if (typeof a.key !== "string" || !/^[a-zA-Z0-9_-]{1,80}$/.test(a.key) || !["profile", "orbital"].includes(a.kind as string)
      || (a.svg !== undefined && (typeof a.svg !== "string" || a.svg.length > 8_000_000))) return undefined;
  return { key: a.key, kind: a.kind as ElucidaAsset["kind"], ...(a.svg ? { svg: a.svg as string } : {}) };
}

export function putAsset(doc: Mol, input: AssetInput, bond: number, target?: number): { mol: Mol; id: number } {
  const asset = readAsset(input), picture = readPictureData({ PNG: input.png });
  if (!asset || !picture || ![input.width, input.height, bond].every(x => Number.isFinite(x) && x > 0 && x <= 10000))
    throw new Error("Invalid figure");
  const shapes = [...(doc.shapes ?? [])], i = target === undefined ? -1 : shapes.findIndex(s => s.id === target && s.elucida);
  if (target !== undefined && i < 0) throw new Error("The selected figure no longer exists");
  const id = i >= 0 ? shapes[i].id : Math.max(0, ...(doc.captions ?? []).map(x => x.id), ...(doc.arrows ?? []).map(x => x.id),
    ...shapes.map(x => x.id), ...(doc.cycles ?? []).map(x => x.id)) + 1;
  // Updating a figure preserves its frame, draw order and rotation. New figures
  // start at the origin and can be placed anywhere with Octet's normal tools.
  const sh: Shape = i >= 0 ? { ...shapes[i], elucida: asset, picture: { ...picture,
    ...(shapes[i].picture?.RotationAngle ? { RotationAngle: shapes[i].picture!.RotationAngle } : {}) } }
    : { id, kind: "picture", from: [-input.width / bond / 2, -input.height / bond / 2],
        to: [input.width / bond / 2, input.height / bond / 2], picture, elucida: asset };
  if (i >= 0) shapes[i] = sh; else shapes.push(sh);
  return { mol: { ...doc, shapes }, id };
}

// Project files are untrusted. Only inert SVG geometry and local references
// reach React. Prefix every ID so two Matplotlib figures cannot share clip IDs.
const TAGS = new Set(["svg", "g", "defs", "path", "rect", "line", "polyline", "polygon", "circle", "ellipse",
  "use", "clipPath", "text", "tspan", "image"]);
const ATTRS = new Set(["id", "d", "x", "y", "x1", "x2", "y1", "y2", "width", "height", "viewBox", "points", "cx", "cy", "r", "rx", "ry",
  "transform", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity",
  "fill-opacity", "fill-rule", "opacity", "clip-path", "clip-rule", "clipPathUnits", "preserveAspectRatio", "font-size", "font-family", "text-anchor", "style"]);
const vectorCache = new WeakMap<ElucidaAsset, Map<number, { body: string; viewBox: string } | undefined>>();
export function vectorOf(asset: ElucidaAsset, id: number): { body: string; viewBox: string } | undefined {
  let cache = vectorCache.get(asset);
  if (!cache) vectorCache.set(asset, cache = new Map());
  if (cache.has(id)) return cache.get(id);
  cache.set(id, undefined);
  if (!asset.svg || /<!ENTITY/i.test(asset.svg)) return undefined;
  const parsed = new DOMParser().parseFromString(asset.svg, "image/svg+xml"), root = parsed.documentElement;
  if (root.localName !== "svg" || parsed.querySelector("parsererror")) return undefined;
  const box = (root.getAttribute("viewBox") ?? "").trim().split(/[ ,]+/).map(Number);
  if (box.length !== 4 || !box.every(Number.isFinite) || box[2] <= 0 || box[3] <= 0) return undefined;
  const all = [root, ...root.querySelectorAll("*")];
  if (all.length > 40000) return undefined;
  const prefix = `elucida_${id}_`, ids = new Map<string, string>();
  for (const el of all) if (el.id) ids.set(el.id, prefix + el.id.replace(/[^a-zA-Z0-9_-]/g, "_"));
  const reference = (s: string) => s.replace(/url\(\s*['"]?#([\w:.-]+)['"]?\s*\)/g, (_, key) => `url(#${ids.get(key) ?? "missing"})`);
  for (const el of all) {
    if (el.namespaceURI !== 'http://www.w3.org/2000/svg' || !TAGS.has(el.localName)) { el.remove(); continue; }
    for (const attr of [...el.attributes]) {
      const k = attr.localName, v = attr.value;
      if (k === "href") {
        const url = v.startsWith("#") ? "#" + (ids.get(v.slice(1)) ?? "missing")
          : el.localName === "image" && /^data:image\/png;base64,[a-zA-Z0-9+/=]+$/.test(v) ? v : undefined;
        if (url) el.setAttributeNS(attr.namespaceURI, attr.name, url); else el.removeAttributeNode(attr);
      } else if (!ATTRS.has(k) || /[\\<>]|(?:javascript|expression|@import|https?:|data:)/i.test(v)
                 || /url\(/i.test(v.replace(/url\(\s*['"]?#[\w:.-]+['"]?\s*\)/g, ""))) el.removeAttributeNode(attr);
      else if (k === 'style') {
        // Presentation properties only: no CSS navigation, resource loading or
        // positioning rules inherited from an imported document.
        el.setAttribute('style', reference(v.split(';').filter(rule => {
          const prop = rule.split(':', 1)[0].trim();
          return prop !== 'style' && ATTRS.has(prop);
        }).join(';')));
      } else el.setAttribute(attr.name, k === "id" ? ids.get(v)! : reference(v));
    }
  }
  // innerHTML serialises as XML but React re-parses as HTML, where a kept PI or comment becomes real markup.
  const walker = parsed.createTreeWalker(root, NodeFilter.SHOW_COMMENT | NodeFilter.SHOW_PROCESSING_INSTRUCTION | NodeFilter.SHOW_CDATA_SECTION), stray: Node[] = [];
  while (walker.nextNode()) stray.push(walker.currentNode);
  for (const node of stray) node.parentNode?.removeChild(node);
  // Each nested <use> multiplies the instances; figures never need that, a shared file could hang the renderer.
  const target = (u: Element) => parsed.getElementById((u.getAttributeNS("http://www.w3.org/1999/xlink", "href") ?? u.getAttribute("href") ?? "").slice(1));
  if ([...root.querySelectorAll("use")].some(u => { const t = target(u); return t?.localName === "use" || t?.querySelector("use"); })) return undefined;
  const out = { body: root.innerHTML, viewBox: box.join(" ") };
  cache.set(id, out);
  return out;
}
