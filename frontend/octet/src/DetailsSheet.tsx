// Experiment details (experiment.ts), as a sheet laid out as the page's header: the title large and bold, then each
// detail's name and value in the page's two columns, at the page's sizes. Each value is rich text, styled with the
// same controls as text on the canvas (bold, italic, underline, subscript, superscript, formula, font, size, colour,
// the character map). A style goes on the text selected in a value, or on the whole value with only a caret in it.
// Return saves, Tab goes to the next value. Nothing changes the drawing until Save.
import { useEffect, useRef, useState } from "react";
import { TextB, TextItalic, TextSubscript, TextSuperscript, TextUnderline } from "@phosphor-icons/react";
import { Dialog } from "./Dialog";
import { RichBox, type RichApi } from "./RichBox";
import { FontPick, SizeButton } from "./Actions";
import { ColourPick } from "./ColourPicker";
import { COLOURS, fontStack } from "./docstyle";
import type { Swatch } from "./settings";
import { formulaRuns } from "./labels";
import { common, normalise, plainOf, styleRange, type RunStyle, type TextRun } from "./richtext";
import type { Field } from "./experiment";

// runs: the value's text, each run with its whole style (the caption's own bold, size and the rest folded in).
export type SheetField = { key: Field; name: string; runs: TextRun[] };
type Props = {
  fields: SheetField[]; focus?: Field;
  font: string; size: number; titleSize: number; // the page's text font and size (pt), and the title's size
  fonts: string[]; sizes: number[];
  colours: { own: Swatch[]; drawing: Swatch[]; onOwn: (own: Swatch[]) => void };
  onCharMap: () => void;
  onSave: (values: Partial<Record<Field, TextRun[]>>) => void; onClose: () => void;
};
// Points to pixels in the sheet: the page at 100 %.
const PX = 96 / 72;
const MAX = 200; // a value's length, as the page keeps it (experiment.ts MAX_VALUE)

export function DetailsSheet(p: Props) {
  const [values, setValues] = useState(() => Object.fromEntries(p.fields.map((f) => [f.key, f.runs])) as Record<Field, TextRun[]>);
  const [versions, setVersions] = useState<Partial<Record<Field, number>>>({}), [carets, setCarets] = useState<Partial<Record<Field, [number, number]>>>({});
  const apis = useRef<Partial<Record<Field, React.MutableRefObject<RichApi | undefined>>>>({});
  // The value last typed in, and where its selection was: a control pressed outside the value acts there.
  const last = useRef<{ key: Field; range: [number, number] }>(undefined), [, redraw] = useState(0);
  const apiOf = (k: Field) => (apis.current[k] ??= { current: undefined });
  useEffect(() => {
    const note = () => {
      for (const f of p.fields) {
        const r = apis.current[f.key]?.current?.range();
        if (r) { last.current = { key: f.key, range: r }; redraw((n) => n + 1); return; }
      }
    };
    document.addEventListener("selectionchange", note);
    return () => document.removeEventListener("selectionchange", note);
  }, [p.fields]);
  // The first value open: the one clicked on the page, else the title.
  useEffect(() => { const k = p.focus ?? p.fields[0]?.key; if (k) setVersions((v) => ({ ...v, [k]: (v[k] ?? 0) + 1 })); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const at = last.current, runs = at ? values[at.key] : undefined, n = runs ? plainOf(runs).length : 0;
  const [a, b] = at && at.range[0] < at.range[1] ? at.range : [0, n];
  const now: RunStyle = runs && n ? common(runs, a, b) : {};
  const baseSize = (k: Field) => (k === "title" ? p.titleSize : p.size);
  const put = (k: Field, next: TextRun[], caret: [number, number]) => {
    setValues((v) => ({ ...v, [k]: normalise(next) }));
    setCarets((c) => ({ ...c, [k]: caret }));
    setVersions((v) => ({ ...v, [k]: (v[k] ?? 0) + 1 }));
  };
  // A style on the selection, or on the whole value with only a caret in it.
  const restyle = (patch: (s: RunStyle) => RunStyle) => {
    if (!at || !runs || !n) return;
    put(at.key, styleRange(runs, a, b, patch), at.range);
  };
  const toggle = (k: "bold" | "italic" | "underline") => restyle((s) => ({ ...s, [k]: now[k] ? undefined : true }));
  const script = (v: "sub" | "super") => restyle((s) => ({ ...s, script: now.script === v ? undefined : v }));
  // Formula: in the text chosen, each count after an element or a bracket becomes a subscript (H2O, Ca(OH)2).
  const formula = () => {
    if (!at || !runs || !n) return;
    let out = styleRange(runs, a, b, (s) => ({ ...s, script: undefined })), i = a;
    for (const r of formulaRuns(plainOf(runs).slice(a, b))) { if (r.sub) out = styleRange(out, i, i + r.text.length, (s) => ({ ...s, script: "sub" })); i += r.text.length; }
    put(at.key, out, at.range);
  };
  // A press on a control keeps the caret in the value.
  const keep = (e: React.PointerEvent) => e.preventDefault();
  const chip = (name: string, icon: React.ReactNode, on: boolean, run: () => void) => (
    <button key={name} className="chip" aria-pressed={on} aria-label={name} data-tip={name} disabled={!at} onPointerDown={keep} onClick={run}>{icon}</button>
  );
  const sizeOf = (k: Field) => now.size ?? baseSize(k);
  const look = (k: Field) => (r: RunStyle): React.CSSProperties => ({
    fontWeight: r.bold ? "bold" : "normal", fontStyle: r.italic ? "italic" : "", textDecoration: r.underline ? "underline" : "",
    verticalAlign: r.script === "sub" ? "sub" : r.script === "super" ? "super" : "", fontSize: r.script ? "75%" : (r.size ?? baseSize(k)) * PX,
    fontFamily: r.font ? fontStack(r.font) : "", color: r.colour ?? "",
  });
  const order = p.fields.map((f) => f.key), title = p.fields.find((f) => f.key === "title"), rest = p.fields.filter((f) => f.key !== "title");
  const box = (f: SheetField) => (
    <RichBox
      key={f.key}
      className={f.key === "title" ? "sheet-value sheet-title" : "sheet-value"}
      label={f.name}
      runs={values[f.key]}
      version={versions[f.key] ?? 0}
      caret={carets[f.key]}
      // Typed into an empty title, the text is bold, as the page's title is.
      pending={f.key === "title" && !plainOf(values.title).length ? { bold: true } : undefined}
      api={apiOf(f.key)}
      look={look(f.key)}
      style={{ fontFamily: fontStack(p.font), fontSize: baseSize(f.key) * PX }}
      onRuns={(next, rebuild) => {
        // A value is one line, MAX characters at most, as the page keeps it.
        const one = normalise(next.map((r) => ({ ...r, text: r.text.replace(/\n/g, " ") })));
        if (plainOf(one).length > MAX) return put(f.key, values[f.key], apiOf(f.key).current?.range() ?? [0, 0]);
        setValues((v) => ({ ...v, [f.key]: one }));
        if (rebuild) { setCarets((c) => ({ ...c, [f.key]: rebuild })); setVersions((v) => ({ ...v, [f.key]: (v[f.key] ?? 0) + 1 })); }
      }}
      onKeyDown={(e) => {
        if (e.key !== "Tab") return;
        e.preventDefault();
        const k = order[(order.indexOf(f.key) + (e.shiftKey ? order.length - 1 : 1)) % order.length], len = plainOf(values[k]).length;
        setCarets((c) => ({ ...c, [k]: [0, len] }));
        setVersions((v) => ({ ...v, [k]: (v[k] ?? 0) + 1 }));
      }}
      onBlur={() => {}}
    />
  );
  return (
    <Dialog title="Experiment details" action="Save" wide onClose={p.onClose} onAction={() => p.onSave(values)}>
      <div className="chips sheet-tools" role="group" aria-label="Style">
        {chip("Bold", <TextB size={16} />, !!now.bold, () => toggle("bold"))}
        {chip("Italic", <TextItalic size={16} />, !!now.italic, () => toggle("italic"))}
        {chip("Underline", <TextUnderline size={16} />, !!now.underline, () => toggle("underline"))}
        {chip("Subscript", <TextSubscript size={16} />, now.script === "sub", () => script("sub"))}
        {chip("Superscript", <TextSuperscript size={16} />, now.script === "super", () => script("super"))}
        <button className="chip" aria-label="Formula" data-tip="Formula: counts become subscripts" disabled={!at} onPointerDown={keep} onClick={formula}><span className="glyph-text">H<sub>2</sub>O</span></button>
        <button className="chip" aria-label="Character map" data-tip="Character map" disabled={!at} onPointerDown={keep} onClick={p.onCharMap}><span className="glyph-text">αβ</span></button>
        <div className="size font"><FontPick label="Font" font={now.font ?? p.font} fonts={p.fonts} onPick={(font) => restyle((s) => ({ ...s, font: font === p.font ? undefined : font }))} /></div>
        <SizeButton size={at ? sizeOf(at.key) : p.size} sizes={p.sizes} run={(c) => { const pt = Number(c.slice("caption.size.".length)); if (at && pt > 0) restyle((s) => ({ ...s, size: pt === baseSize(at.key) ? undefined : pt })); }} />
        <div className="sheet-colour"><ColourPick label="Colour" value={now.colour ?? "#000000"} presets={COLOURS} {...p.colours} onPick={(hex) => restyle((s) => ({ ...s, colour: hex === "#000000" ? undefined : hex }))} /></div>
      </div>
      <div className="sheet-page">
        {title && box(title)}
        <div className="sheet-grid">
          {rest.map((f) => (
            <div key={f.key} className="sheet-row">
              <span className="sheet-name" style={{ fontFamily: fontStack(p.font), fontSize: p.size * PX }}>{f.name}</span>
              {box(f)}
            </div>
          ))}
        </div>
      </div>
    </Dialog>
  );
}
