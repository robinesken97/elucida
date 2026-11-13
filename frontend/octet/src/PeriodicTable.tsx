// The Text tool's menu (issue 71): Text, then the periodic table. An element chosen here is the Text tool's to put on
// atoms, as with ChemDraw's Periodic Table window. Pointing at an element, or moving to it with the arrow keys, shows its
// number, name, atomic weight and isotopes in the table's gap over groups 3 to 12 (periodic.ts has the facts).
import { useId, useState } from "react";
import { TextT } from "@phosphor-icons/react";
import { Menu } from "./Menu";
import { cellOf, elementFacts, stepFrom, SYMBOLS } from "./periodic.ts";

export function PeriodicTable({ current, onChoose, onRelease }: { current?: string; onChoose: (el?: string) => void; onRelease: (el?: string) => void }) {
  const [shown, setShown] = useState<string>(), info = useId(), el = shown ?? current, f = el && elementFacts(el);
  // The arrow keys move through the table, Home and End go to its ends. The drawing takes no keys from it, but Escape
  // goes on to close the menu, and the menu keys go on.
  const keys = (e: React.KeyboardEvent) => {
    if (e.key !== "Escape" && !e.metaKey && !e.ctrlKey) e.stopPropagation();
    const at = SYMBOLS.indexOf((e.target as HTMLElement).dataset.item ?? "") + 1;
    const to = e.key === "Home" ? 1 : e.key === "End" ? SYMBOLS.length : at ? stepFrom(at, e.key) : undefined;
    if (!to) return;
    e.preventDefault();
    e.currentTarget.querySelector<HTMLElement>(`[data-item="${SYMBOLS[to - 1]}"]`)?.focus();
  };
  return (
    <Menu label="Text options" columns={3} groups={[[{ key: "text", name: "Text", icon: <TextT size={20} />, checked: !current }]]} onChoose={() => onChoose()} onRelease={() => onRelease()}
      extra={
        <div className="periodic" onKeyDown={keys} onPointerLeave={() => setShown(undefined)}>
          {SYMBOLS.map((s, k) => {
            const [row, col] = cellOf(k + 1);
            return (
              <button key={s} role="menuitemradio" aria-checked={s === current} className="chip" data-item={s} tabIndex={s === (current ?? "H") ? 0 : -1}
                aria-label={`${s}, ${elementFacts(s).name}`} aria-describedby={info} style={{ gridRow: row, gridColumn: col }}
                onPointerEnter={() => setShown(s)} onFocus={() => setShown(s)} onClick={() => onChoose(s)} onPointerUp={() => onRelease(s)}>
                {s}
              </button>
            );
          })}
          <div id={info} className="element-facts">
            {f && <>
              <p className="element-tile"><span>{f.z}</span><b>{el}</b><span>{f.name}</span>{f.weight && <span>{f.weight.toFixed(3)}</span>}</p>
              <ul className="element-isotopes">{f.isotopes.map(([n, a]) => <li key={n}><sup>{n}</sup>{el} {a}%</li>)}</ul>
            </>}
          </div>
        </div>
      } />
  );
}
