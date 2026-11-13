// The fast glide's frames (glideplan.ts, decision 0024). React draws the layer once, where the structures start; each
// frame then writes the paths' points and the labels' places straight to the page, with nothing drawn again, so a
// glide of a thousand atoms stays smooth on a slow laptop. The editor hides the structures' own ink meanwhile, and
// shows it again, where they end, when the layer goes.
import { useLayoutEffect, useRef } from "react";
import { tween } from "./motion";
import { slideAt, slidePath, type GlidePart, type PartIn } from "./glideplan";
import { frame as domFrame, type DomTween } from "./domtween";
import type { Label } from "./render";

export function GlideLayer({ plan, dom, ink, text, part, skip, onFrame, onDone }: {
  plan: GlidePart[];
  dom?: DomTween; // everything else on the canvas (domtween.ts), under the structures
  ink: (key: string) => { fill: string; fillOpacity?: number }; // a colour key's fill (glideplan.ts inkKey)
  text: (l: Label) => React.SVGProps<SVGTextElement>; // a label's look, as the editor draws it
  part: (p: PartIn) => React.ReactNode; // a whole structure, as the editor draws it (for a fade)
  skip?: (t: number) => boolean; // a frame left out (the middle of Rotate 180°, every bond squeezed): the last one stays
  onFrame: (t: number) => void;
  onDone: () => void;
}) {
  const under = useRef<SVGGElement>(null), paths = useRef<(SVGPathElement | null)[]>([]), labels = useRef<(SVGTextElement | null)[]>([]), fades = useRef<(SVGElement | null)[]>([]);
  // The copy of the rest of the canvas goes in once; it is the layer's own, so React never draws over it.
  useLayoutEffect(() => {
    const g = under.current, root = dom?.root;
    if (!g || !root) return;
    g.appendChild(root);
    return () => root.remove();
  }, [dom]);
  useLayoutEffect(() => tween((t) => {
    onFrame(t);
    if (t >= 1) return onDone();
    if (skip?.(t)) return;
    if (dom) domFrame(dom, t);
    let p = 0, l = 0, f = 0;
    for (const x of plan) {
      if (x.kind === "fade") {
        fades.current[f++]?.setAttribute("opacity", String(1 - t));
        fades.current[f++]?.setAttribute("opacity", String(t));
        continue;
      }
      for (const g of x.groups) paths.current[p++]?.setAttribute("d", slidePath(g, t));
      for (let k = 0; k < x.fades.length; k++) { fades.current[f++]?.setAttribute("opacity", String(1 - t)); fades.current[f++]?.setAttribute("opacity", String(t)); }
      for (const s of x.labels) {
        const [lx, ly] = slideAt(s.from, s.to, t, s.turn);
        for (const [el, a] of s.was ? [[labels.current[l++], 1 - t], [labels.current[l++], t]] as const : [[labels.current[l++], -1]] as const) {
          el?.setAttribute("x", String(lx));
          el?.setAttribute("y", String(ly));
          if (a >= 0) el?.setAttribute("opacity", String(a));
        }
      }
    }
  }), [plan]); // eslint-disable-line react-hooks/exhaustive-deps
  let p = 0, l = 0, f = 0;
  return (
    <g className="glide-layer" aria-hidden="true">
      <g ref={under} />
      {plan.map((x) => x.kind === "fade" ? (
        <g key={x.id}>
          <g ref={((k) => (el: SVGGElement | null) => { fades.current[k] = el; })(f++)}>{part(x.from)}</g>
          <g ref={((k) => (el: SVGGElement | null) => { fades.current[k] = el; })(f++)} opacity={0}>{part(x.to)}</g>
        </g>
      ) : (
        <g key={x.id}>
          {x.groups.map((g) => { const k = p++; return <path key={g.key} ref={(el) => { paths.current[k] = el; }} d={slidePath(g, 0)} {...ink(g.key)} />; })}
          {x.fades.flatMap((z) => [[z.out, 1], [z.in, 0]] as const).map(([d, a], j) => { const k = f++; return <path key={`f${j}`} ref={(el) => { fades.current[k] = el; }} d={d} opacity={a} {...ink(x.fades[j >> 1].key)} />; })}
          {x.labels.flatMap((s, i) => (s.was ? [[s.was, 1], [s.label, 0]] as const : [[s.label, undefined]] as const).map(([lab, a], j) => {
            const k = l++;
            return <text key={`${i}-${j}`} ref={(el) => { labels.current[k] = el; }} {...text(lab)} x={s.from[0]} y={s.from[1]} opacity={a}>{lab.text}</text>;
          }))}
        </g>
      ))}
    </g>
  );
}
