// The fast glide for everything that is not a structure's ink (decision 0024): arrows, text, shapes, ring fills, halos,
// the selection and other marks. The canvas as it was (copied just before the command) and as it is now are paired
// element by element; each number that changes in an attribute (a path's points, a caption's place, a transform)
// slides from the old value to the new one each frame, written straight to a copy of the canvas, with nothing drawn
// again. An element that has no partner, or whose text or form changed, fades from the old one to the new one.
// Structures' ink and labels are left out here (data-glide="structure"): glideplan.ts slides them.
const NUMBER = /-?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?/gi;
type Slider = { el: Element; attr: string; text: string[]; from: number[]; to: number[] };
export type DomTween = { root: SVGGElement; sliders: Slider[]; fades: { el: Element; from: number; to: number; base: number }[] };

const left = (el: Element) => el.getAttribute("data-glide") === "structure" || el.classList.contains("glide-layer") || el.classList.contains("glide-dom");
// What an element is, for pairing: its tag and class, and for a shape with no children, whether it has text. A group
// pairs whatever its children: they are paired one by one, so one mark more does not make the whole group fade.
const kind = (el: Element) => `${el.tagName}|${el.getAttribute("class") ?? ""}|${el.childElementCount ? "" : el.textContent ? "t" : ""}`;
const split = (v: string) => ({ text: v.split(NUMBER), numbers: (v.match(NUMBER) ?? []).map(Number) });

// A copy of a layer's children (structures left out), in a group of its own.
export function copyOf(layer: Element): SVGGElement {
  const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
  for (const child of [...layer.children]) if (!left(child)) g.appendChild(child.cloneNode(true));
  for (const el of [...g.querySelectorAll("[data-glide='structure'], .glide-layer, .glide-dom")]) el.remove();
  return g;
}

// The tween from `from` (a copy of the canvas before) to the canvas now (`to`, copied here): the copy of now, set to
// where everything was, to be moved on by frame().
export function domTween(from: SVGGElement, to: Element): DomTween {
  const root = copyOf(to);
  root.setAttribute("class", "glide-dom");
  root.setAttribute("aria-hidden", "true");
  const tween: DomTween = { root, sliders: [], fades: [] };
  const fadeOut = (a: Element, before: Element | null, parent: Element) => {
    const copy = a.cloneNode(true) as Element;
    parent.insertBefore(copy, before);
    tween.fades.push({ el: copy, from: 1, to: 0, base: Number(copy.getAttribute("opacity") ?? 1) });
  };
  const fadeIn = (b: Element) => tween.fades.push({ el: b, from: 0, to: 1, base: Number(b.getAttribute("opacity") ?? 1) });
  const pair = (a: Element, b: Element) => {
    // Text that changed, or an attribute whose form changed (a path with another number of points): it fades.
    const changed = () => { fadeOut(a, b, b.parentNode as Element); fadeIn(b); };
    if (!b.childElementCount && a.textContent !== b.textContent) return changed();
    const sliders: Slider[] = [];
    for (const name of b.getAttributeNames()) {
      const va = a.getAttribute(name), vb = b.getAttribute(name)!;
      if (va === vb || va === null) continue;
      const sa = split(va), sb = split(vb);
      if (sa.numbers.length !== sb.numbers.length || sa.text.join("|") !== sb.text.join("|")) return changed();
      sliders.push({ el: b, attr: name, text: sb.text, from: sa.numbers, to: sb.numbers });
    }
    tween.sliders.push(...sliders);
    // The children, paired in order by kind; one with no partner fades out or in where it is.
    const ca = [...a.children], cb = [...b.children];
    let i = 0, j = 0;
    while (i < ca.length || j < cb.length) {
      if (i < ca.length && j < cb.length && kind(ca[i]) === kind(cb[j])) { pair(ca[i++], cb[j++]); continue; }
      const ahead = j < cb.length ? cb.slice(j, j + 8).findIndex((x) => i < ca.length && kind(x) === kind(ca[i])) : -1;
      if (ahead > 0) { for (let k = 0; k < ahead; k++) fadeIn(cb[j++]); continue; }
      if (i < ca.length) fadeOut(ca[i++], cb[j] ?? null, b);
      else fadeIn(cb[j++]);
    }
  };
  pair(from, root);
  frame(tween, 0);
  return tween;
}

// The tween t (0 to 1) of the way.
export function frame(tween: DomTween, t: number) {
  for (const s of tween.sliders) {
    let out = s.text[0];
    for (let k = 0; k < s.to.length; k++) out += Math.round((s.from[k] + (s.to[k] - s.from[k]) * t) * 100) / 100 + s.text[k + 1];
    s.el.setAttribute(s.attr, out);
  }
  for (const f of tween.fades) f.el.setAttribute("opacity", String(f.base * (f.from + (f.to - f.from) * t)));
}
