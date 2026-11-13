// Octet's colour picker: a square for how strong and how light the colour is, a strip for its hue, its hex, and the
// eyedropper. Used wherever a colour is chosen freely (Settings, Colours). There is no system colour panel anywhere in
// Octet. ColourPick, below, is Octet's one colour menu.
import { useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ArrowDown, ArrowUp, Eyedropper, Palette, PencilSimple, Trash, X } from "@phosphor-icons/react";
import { holdCursor } from "./cursor";
import { Exit, useLeaving } from "./motion";
import { ContextMenu, Pick, type MenuItem } from "./Menu";
import { UI } from "./export";
import { ADD, addColour, chosenKey, colourOptions, hexOf, moveColour, ownIndex, PICK, recentColours, rememberColour, type ColourOption } from "./colours";
import type { Swatch } from "./settings";

const TAURI = "__TAURI_INTERNALS__" in window, MAC = navigator.platform.startsWith("Mac");

type HSV = [number, number, number]; // hue 0–360, saturation 0–1, value 0–1

export function hexToHsv(hex: string): HSV {
  const n = parseInt(hex.slice(1), 16), r = ((n >> 16) & 255) / 255, g = ((n >> 8) & 255) / 255, b = (n & 255) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  const h = d === 0 ? 0 : max === r ? 60 * (((g - b) / d) % 6) : max === g ? 60 * ((b - r) / d + 2) : 60 * ((r - g) / d + 4);
  return [(h + 360) % 360, max === 0 ? 0 : d / max, max];
}
export function hsvToHex([h, s, v]: HSV): string {
  const f = (k: number) => { const x = (k + h / 60) % 6; return v - v * s * Math.max(0, Math.min(x, 4 - x, 1)); };
  return "#" + [f(5), f(3), f(1)].map((c) => Math.round(c * 255).toString(16).padStart(2, "0")).join("").toUpperCase();
}

// The eyedropper (Pick from screen): a colour from anywhere on the screen where Octet can read it, else from the window.
// A web view with the EyeDropper API uses it; on macOS the app shows the system's colour sampler. Elsewhere the pointer
// becomes a crosshair over the window, with the colour under it beside it: a click takes the colour of what is drawn
// there (the drawing's own colour, not Octet's marks over it), and a press let go outside the window takes the screen's
// colour there, when the app can read it (Wayland lets no app). Escape cancels. The colour picked joins the recent ones.
let picking = false; // the window's own eyedropper is out: the colour picker by it stays open
export async function pickColour(): Promise<string | undefined> {
  const hex = await pick();
  if (hex) rememberColour(hex);
  return hex;
}
async function pick(): Promise<string | undefined> {
  // It must open in the click that asks for it, so nothing waits before it does.
  if ("EyeDropper" in window) {
    try { return hexOf((await new (window as unknown as { EyeDropper: new () => { open: () => Promise<{ sRGBHex: string }> } }).EyeDropper().open()).sRGBHex); }
    catch (e) { if ((e as DOMException).name === "AbortError") return undefined; }
  }
  if (TAURI && MAC) return (await invoke<string | null>("pick_colour").catch(() => null)) ?? undefined;
  return new Promise((done) => {
    const cover = document.body.appendChild(document.createElement("div")), chip = cover.appendChild(document.createElement("span"));
    cover.className = "eyedropper";
    chip.hidden = true;
    picking = true;
    // Every key is the eyedropper's while it is out.
    const keys = (e: KeyboardEvent) => { e.preventDefault(); e.stopImmediatePropagation(); if (e.key === "Escape") end(); };
    const end = (hex?: string) => { picking = false; cover.remove(); removeEventListener("keydown", keys, true); done(hex); };
    addEventListener("keydown", keys, true);
    cover.onpointermove = (e) => { chip.hidden = false; chip.style.cssText = `left: ${e.clientX}px; top: ${e.clientY}px; background: ${colourAt(e.clientX, e.clientY) ?? "transparent"}`; };
    cover.onpointerdown = (e) => { e.preventDefault(); cover.setPointerCapture(e.pointerId); };
    cover.onpointerup = (e) => {
      if (e.clientX >= 0 && e.clientY >= 0 && e.clientX < innerWidth && e.clientY < innerHeight) return end(colourAt(e.clientX, e.clientY));
      if (!TAURI) return end();
      void invoke<string | null>("pick_colour").then((hex) => end(hex ?? undefined), () => end());
    };
  });
}
// The colour of what is drawn at a point in the window: the outline or the fill the point is on, or a background.
function colourAt(x: number, y: number): string | undefined {
  for (const el of document.elementsFromPoint(x, y)) {
    if (el.closest(`.eyedropper,${UI}`)) continue;
    const s = getComputedStyle(el), shape = el instanceof SVGGeometryElement, m = shape ? el.getScreenCTM()?.inverse() : undefined;
    const hex = (m && (el as SVGGeometryElement).isPointInStroke(new DOMPoint(x, y).matrixTransform(m)) ? hexOf(s.stroke) : undefined) ?? hexOf(shape || el instanceof SVGTextContentElement ? s.fill : s.backgroundColor);
    if (hex) return hex;
  }
}

export function ColourPicker({ value, onChange }: { value: string; onChange: (hex: string) => void }) {
  const [hsv, setHsv] = useState<HSV>(() => hexToHsv(value));
  const [text, setText] = useState(value.toUpperCase());
  // A colour set from outside (another row picked) resets the picker; its own changes do not move the hue.
  const own = useRef(value);
  useEffect(() => { if (value !== own.current) { own.current = value; setHsv(hexToHsv(value)); setText(value.toUpperCase()); } }, [value]);
  const set = (next: HSV) => { setHsv(next); const hex = hsvToHex(next); own.current = hex; setText(hex); onChange(hex); };
  const take = (hex: string) => { own.current = hex; setHsv(hexToHsv(hex)); setText(hex); onChange(hex); };
  // Dragging in the square or along the strip: the pointer is followed until it is let go.
  const track = (e: React.PointerEvent<HTMLDivElement>, at: (x: number, y: number) => void) => {
    const box = e.currentTarget.getBoundingClientRect();
    const go = (ev: { clientX: number; clientY: number }) => at(Math.min(1, Math.max(0, (ev.clientX - box.left) / box.width)), Math.min(1, Math.max(0, (ev.clientY - box.top) / box.height)));
    go(e);
    e.currentTarget.setPointerCapture(e.pointerId);
    holdCursor(e.currentTarget);
    const move = (ev: PointerEvent) => go(ev), up = () => { removeEventListener("pointermove", move); removeEventListener("pointerup", up); };
    addEventListener("pointermove", move);
    addEventListener("pointerup", up);
  };
  const [h, s, v] = hsv;
  return (
    <div className="colour-picker">
      <div className="picker-square" style={{ backgroundColor: `hsl(${h} 100% 50%)` }} role="slider" aria-label="Strength and lightness" aria-valuetext={text} tabIndex={0}
        onPointerDown={(e) => track(e, (x, y) => set([h, x, 1 - y]))}
        onKeyDown={(e) => {
          const d = e.shiftKey ? 0.1 : 0.02, k = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, d], ArrowDown: [0, -d] }[e.key];
          if (k) { e.preventDefault(); set([h, Math.min(1, Math.max(0, s + k[0])), Math.min(1, Math.max(0, v + k[1]))]); }
        }}>
        <span className="picker-knob" style={{ left: `${s * 100}%`, top: `${(1 - v) * 100}%`, background: text }} />
      </div>
      <div className="picker-hue" role="slider" aria-label="Hue" aria-valuemin={0} aria-valuemax={360} aria-valuenow={Math.round(h)} tabIndex={0}
        onPointerDown={(e) => track(e, (x) => set([x * 360, s, v]))}
        onKeyDown={(e) => {
          const d = (e.shiftKey ? 10 : 2) * (e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0);
          if (d) { e.preventDefault(); set([(h + d + 360) % 360, s, v]); }
        }}>
        <span className="picker-knob" style={{ left: `${(h / 360) * 100}%`, top: "50%", background: `hsl(${h} 100% 50%)` }} />
      </div>
      <div className="picker-row">
        <input className="picker-hex" aria-label="Hex" spellCheck={false} value={text}
          onChange={(e) => {
            const t = e.target.value.toUpperCase().replace(/[^#0-9A-F]/g, "");
            setText(t);
            const hex = (t.startsWith("#") ? t : `#${t}`).slice(0, 7);
            if (/^#[0-9A-F]{6}$/.test(hex)) take(hex);
          }}
          onBlur={() => setText(hsvToHex(hsv))} />
        <button className="text-button" aria-label="Pick from screen" data-tip="Pick from screen" onClick={() => void pickColour().then((hex) => hex && take(hex))}><Eyedropper size={16} /></button>
      </div>
    </div>
  );
}

// The colour picker in a small window by the button that opens it (anchor: the button's box): under the button, or
// over it when there is no room below. A click outside it (but on keep, the button) or Escape closes it. Wrap it in
// Exit: it leaves with a motion, and takes no clicks or keys on its way out.
export function ColourPop({ anchor, keep, label, value, onChange, onClose }: { anchor: DOMRect; keep?: HTMLElement | null; label: string; value: string; onChange: (hex: string) => void; onClose: () => void }) {
  const box = useRef<HTMLDivElement>(null), close = useRef(onClose), leaving = useLeaving();
  close.current = onClose;
  useEffect(() => {
    if (leaving) return;
    // The eyedropper's clicks and its Escape are its own.
    const away = (e: PointerEvent) => { if (!picking && !box.current?.contains(e.target as Node) && !keep?.contains(e.target as Node)) close.current(); };
    // Escape closes this only, not the window it is in (Settings), whichever listener comes first (listOpen).
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape" && !picking) { e.preventDefault(); e.stopImmediatePropagation(); close.current(); keep?.focus(); } };
    addEventListener("pointerdown", away, true);
    addEventListener("keydown", esc, true);
    return () => { removeEventListener("pointerdown", away, true); removeEventListener("keydown", esc, true); };
  }, [keep, leaving]);
  const above = anchor.bottom + 260 > innerHeight - 8 && anchor.top - 260 > 8;
  return (
    <div ref={box} className={["page-menu colour-pop", above && "above", leaving && "leaving"].filter(Boolean).join(" ")} role="dialog" aria-label={label} inert={leaving}
      style={{ left: Math.max(8, Math.min(anchor.right - 208, innerWidth - 216)), top: above ? anchor.top - 6 : anchor.bottom + 6 }}>
      <ColourPicker value={value} onChange={onChange} />
    </div>
  );
}

// A colour menu's options as the menu's options: each colour as its swatch, None as an empty one. key: an option's key
// in that menu; value: the colour chosen now, ticked.
export const colourItems = (groups: ColourOption[][], key = (o: ColourOption) => o.key, value?: string): MenuItem[][] => {
  const chosen = value === undefined ? undefined : chosenKey(groups, value);
  return groups.map((g) => g.map((o) => ({ key: key(o), name: o.name, checked: chosen !== undefined && o.key === chosen,
    icon: o.key === PICK ? <Eyedropper size={18} /> : o.key === ADD ? <Palette size={18} /> : <span className={o.hex ? "pick-swatch" : "pick-swatch none"} style={o.hex ? { background: o.hex } : undefined} /> })));
};

// Octet's one colour menu (Sam, 11 November 2026): a button with its name and the colour chosen now, and the colours
// as a list from it (colourOptions), the same wherever a colour is chosen. Pick from screen takes a colour from the
// screen. Add colour… opens the picker by the button: the colour changes as the picker does, and joins the user's own
// colours as the picker closes. The user's own colours drag into a new order and have a remove button; a right-click
// on one renames, moves or removes it. A press keeps the focus where it is, so text being typed takes the colour.
// field: drawn as the fields beside it (a Settings row, which names it), with the colour's name where a select shows its
// value.
export function ColourPick({ label, value, presets, none, own, drawing = [], onPick, onOwn, field }: {
  label: string; value: string; // the colour chosen now (#RRGGBB), or "none"
  presets: [string, string][]; none?: boolean; // the preset colours, after None where it applies (Highlight, Ring fill)
  field?: boolean;
  own: Swatch[]; drawing?: Swatch[]; onOwn: (own: Swatch[]) => void; // the user's own colours, and the drawing's after them
  onPick: (hex: string, live?: boolean) => void; // live: a change in the picker while it is open (one step to undo)
}) {
  const box = useRef<HTMLDivElement>(null), held = useRef({ own, onOwn });
  held.current = { own, onOwn };
  const [adding, setAdding] = useState<{ anchor: DOMRect; from: string; hex: string }>(), [renaming, setRenaming] = useState<string>();
  const [manage, setManage] = useState<{ key: string; at: { x: number; y: number }; keyboard: boolean }>();
  // The lists are made again only when a colour in them changes: the drawing's colours come new with every edit.
  const latest = recentColours(), drawn = drawing.map((c) => c.name + c.hex).join("\n");
  const options = useMemo(() => colourOptions(presets, [...own, ...drawing], value, none, latest), [presets, own, drawn, value, none, latest]); // eslint-disable-line react-hooks/exhaustive-deps
  const items = useMemo(() => colourItems(options).map((g) => g.map((i): MenuItem => {
    const k = ownIndex(i.key, own);
    if (k < 0) return i;
    const rename = renaming === i.key ? (name: string) => { setRenaming(undefined); if (name.trim()) held.current.onOwn(own.map((c, j) => (j === k ? { ...c, name: name.trim() } : c))); } : undefined;
    return { ...i, rename, action: { icon: <X size={12} />, label: `Remove ${i.name}`, onClick: () => held.current.onOwn(own.filter((_, j) => j !== k)) } };
  })), [options, own, renaming]);
  const chosen = chosenKey(options, value), current = options.flat().find((o) => o.key === chosen);
  const choose = (key: string) => {
    if (key === PICK) return void pickColour().then((hex) => hex && onPick(hex));
    if (key === ADD) { const from = /^#[0-9a-f]{6}$/i.test(value) ? value : "#3F6BFF"; return setAdding({ anchor: box.current!.getBoundingClientRect(), from, hex: from }); }
    // The colour chosen joins the recent ones wherever the menu is (Settings' text colour too); None does not.
    const hex = options.flat().find((o) => o.key === key)?.hex ?? "none";
    rememberColour(hex);
    onPick(hex);
  };
  // A press on one of the user's own colours that moves is a drag: the colour moves along the list as the pointer passes
  // the others, and the click it ends with chooses nothing.
  const press = (e: React.PointerEvent, key: string) => {
    let list = held.current.own, at = ownIndex(key, list), moved = false;
    if (at < 0 || e.button !== 0) return;
    const y = e.clientY;
    const move = (ev: PointerEvent) => {
      moved ||= Math.abs(ev.clientY - y) > 4;
      const to = moved ? ownIndex(document.elementFromPoint(ev.clientX, ev.clientY)?.closest<HTMLElement>("[data-item]")?.dataset.item, list) : -1;
      if (to >= 0 && to !== at) { list = moveColour(list, at, to); at = to; held.current.onOwn(list); }
    };
    const up = () => {
      removeEventListener("pointermove", move);
      removeEventListener("pointerup", up);
      if (!moved) return;
      const swallow = (ev: Event) => ev.stopPropagation();
      addEventListener("click", swallow, true);
      setTimeout(() => removeEventListener("click", swallow, true));
    };
    addEventListener("pointermove", move);
    addEventListener("pointerup", up);
  };
  const at = manage ? ownIndex(manage.key, own) : -1;
  return (
    <div className="pick" ref={box} onMouseDown={(e) => { if (!(e.target as Element).closest("input, .colour-pop")) e.preventDefault(); }}>
      <Pick label={label} value={chosen ?? value} groups={items} onPick={choose} onPress={press} onItemMenu={(key, where, keyboard) => { if (ownIndex(key, own) >= 0) setManage({ key, at: where, keyboard }); }}
        className={field ? "select-field" : "chip pick-button"} title={`${label}: ${current?.name ?? value}`}>
        <span className={field ? undefined : "pick-label"} aria-hidden>{field ? current?.name ?? value : label}</span>
        <span className={current?.hex ? "pick-swatch" : "pick-swatch none"} style={current?.hex ? { background: current.hex } : undefined} />
      </Pick>
      <Exit>{adding && <ColourPop anchor={adding.anchor} keep={box.current} label={`${label} colour`} value={adding.hex} onChange={(hex) => { setAdding((a) => a && { ...a, hex }); onPick(hex, true); }}
        onClose={() => { setAdding(undefined); if (adding.hex !== adding.from) { rememberColour(adding.hex); onOwn(addColour(own, adding.hex)); } }} />}</Exit>
      {manage && at >= 0 && (
        <ContextMenu label={own[at].name} at={manage.at} keyboard={manage.keyboard} sub={() => undefined} onClose={() => setManage(undefined)}
          groups={[[{ key: "rename", name: "Rename", icon: <PencilSimple size={18} /> }, ...(at > 0 ? [{ key: "up", name: "Move up", icon: <ArrowUp size={18} /> }] : []),
            ...(at < own.length - 1 ? [{ key: "down", name: "Move down", icon: <ArrowDown size={18} /> }] : [])], [{ key: "remove", name: "Remove", icon: <Trash size={18} /> }]]}
          onChoose={(k) => (k === "rename" ? setRenaming(manage.key) : onOwn(k === "remove" ? own.filter((_, j) => j !== at) : moveColour(own, at, at + (k === "up" ? -1 : 1))))} />
      )}
    </div>
  );
}
