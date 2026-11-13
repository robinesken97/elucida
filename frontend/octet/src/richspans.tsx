// Rich text as SVG: a caption's runs, on the canvas and in the library's thumbnails.
import { fontStack } from "./docstyle";
import type { TextRun } from "./richtext";

// A colour as drawn on the paper: black ink is white on dark paper.
export const inkOn = (dark: boolean, c: string) => (dark && /^#(000000|0f172a)$/i.test(c) ? "#FFFFFF" : c);
// A line of rich text as tspans: each run in its style, a subscript 0.212 em down and a superscript 0.33 em up at
// 75% size (as atom labels), each run starting from where the last one left the baseline. A run's own colour draws as
// the rest of the drawing does on dark paper (inkOn).
export function richSpans(runs: TextRun[], size: number, PT: number, dark: boolean) {
  let shift = 0;
  return runs.map((r, k) => {
    const to = r.script === "sub" ? 0.212 * size : r.script === "super" ? -0.33 * size : 0, dy = to - shift;
    shift = to;
    const px = r.size ? r.size * PT : size;
    return (
      <tspan key={k} dy={dy || undefined} fill={r.colour && inkOn(dark, r.colour)} style={{ fontSize: r.script ? px * 0.75 : px, fontWeight: r.bold ? "bold" : undefined, fontStyle: r.italic ? "italic" : undefined, fontFamily: r.font ? fontStack(r.font) : undefined, textDecoration: r.underline ? "underline" : undefined }}>
        {r.text}
      </tspan>
    );
  });
}
