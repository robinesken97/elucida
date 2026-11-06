// What's new in this version (releases.ts): once after an update, and from About Octet Draw. Earlier versions' notes
// are on GitHub.
import { invoke } from "@tauri-apps/api/core";
import { Dialog } from "./Dialog";
import type { Release } from "./releases";

export function WhatsNew({ release, onClose }: { release: Release; onClose: () => void }) {
  return (
    <Dialog title={`What’s new in Octet Draw ${release.version}`} onClose={onClose} alt={{ label: "All versions", onClick: () => void invoke("open_link", { name: "releases" }).catch(() => undefined) }}>
      <div className="notes" tabIndex={0} role="region" aria-label="Release notes">
        <p>{release.intro}</p>
        {release.sections.map((s) => (
          <section key={s.title}>
            <h3>{s.title}</h3>
            <ul>{s.items.map((item) => <li key={item}>{item}</li>)}</ul>
          </section>
        ))}
        <p>{release.thanks}</p>
      </div>
    </Dialog>
  );
}
