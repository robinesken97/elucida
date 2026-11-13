// What's new in this version (releases.ts): once after an update, and from About Octet Draw. Earlier versions' notes
// are on GitHub. Under the first line, one line and a Donate button (Sam, 11 November 2026: "a small but clear 'donate
// to help if you want' button", then "move donate to the top"). Then the few big changes, each a name and one line.
// Every other section is folded to its name and the number of its changes (Sam, 12 November 2026: "so hard to digest
// as there is just so much"), with the Actions panel's fold: a click on a name opens that section.
import { invoke } from "@tauri-apps/api/core";
import { useId, useState } from "react";
import { CaretDown, Heart } from "@phosphor-icons/react";
import { Dialog } from "./Dialog";
import type { Release } from "./releases";

export function WhatsNew({ release, onClose }: { release: Release; onClose: () => void }) {
  const highlights = release.highlights ?? release.summary?.map((text) => ({ title: "", text }));
  const [open, setOpen] = useState<string[]>([]);
  const id = useId();
  const toggle = (title: string) => setOpen((o) => (o.includes(title) ? o.filter((t) => t !== title) : [...o, title]));
  return (
    <Dialog title={release.heading ?? `What’s new in Octet Draw ${release.version}`} onClose={onClose} alt={{ label: "All versions", onClick: () => void invoke("open_link", { name: "releases" }).catch(() => undefined) }}>
      <div className="notes" tabIndex={0} role="region" aria-label="Release notes">
        {release.intro && <p>{release.intro}</p>}
        {/* Octet Draw is free for everyone, and stays free. A donation is only for those who want to help: one line and
            a small button at the top of the notes, never a window of its own. */}
        <p className="notes-donate">
          <span>Octet Draw is free. If you want to help, you can donate.</span>
          <button type="button" className="dialog-button" onClick={() => void invoke("open_link", { name: "donate" }).catch(() => undefined)}><Heart size={16} aria-hidden /> Donate</button>
        </p>
        {highlights && release.heading && <h3 className="notes-more">Highlights</h3>}
        {highlights && (
          <ul className="notes-highlights" aria-label="Highlights">
            {highlights.map((h) => (
              <li key={h.text}>
                {h.title && <strong>{h.title}</strong>}
                <span>{h.text}</span>
              </li>
            ))}
          </ul>
        )}
        {release.signoff?.map((line) => <p key={line}>{line}</p>)}
        <h3 className="notes-more">More changes</h3>
        {release.sections.map((s, i) => (
          <section key={s.title} className="notes-fold">
            <button type="button" className="fold-title" aria-expanded={open.includes(s.title)} aria-controls={`${id}-${i}`} onClick={() => toggle(s.title)}>
              {s.title}
              <CaretDown size={12} className="fold-caret" aria-hidden />
              <span className="notes-count" aria-label={`${s.items.length} changes`}>{s.items.length}</span>
            </button>
            <div id={`${id}-${i}`} className="fold-body" data-open={open.includes(s.title) || undefined} inert={!open.includes(s.title)}>
              <div>{s.note && <p className="notes-note">{s.note}</p>}<ul>{s.items.map((item) => <li key={item}>{item}</li>)}</ul></div>
            </div>
          </section>
        ))}
        <p className="notes-thanks">{release.thanks}</p>
      </div>
    </Dialog>
  );
}
