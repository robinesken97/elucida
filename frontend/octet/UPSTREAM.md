# Octet source snapshot for Elucida

Source: https://github.com/SamChemMan/Octet-Draw
Commit: 6395bd582d2c5ba9404e9ddaf175e52e2a9f387c.
Version: 1.1.2 (pinned source commit; no automatic tracking of main).
License: Apache-2.0; copyright Sam Ellis and contributors. See LICENSE and THIRD_PARTY.md.

This directory contains a source snapshot, not an independent git repository.
Elucida additions: elucida.ts, elucida-si.ts, elucida-assets.ts, elucida-assets.check.ts, embedded-main.tsx, embedded.css, embedded.html, public/bridge.js,
vite.embed.config.ts; integration changes in Editor.tsx and export.ts.
The upstream drawing engine, file serializers and keyboard handling remain in use.
Analysis commands are disabled in embedded mode; their source is retained to minimize fork divergence.

Additional changes: Actions.tsx filters analysis commands; cdx.ts uses an explicit Mac Roman
character table to avoid a reproduced Qt WebEngine legacy TextDecoder stall on macOS.
The embedding build is unminified to make review and browser diagnostics easier.
Editor.tsx also exposes theme-neutral snapshots, the uppermost reaction for SI export,
stoichiometry table snapshots and label equivalents. Density/volume/concentration rows
remain visible in embedded tables. The display-only dark canvas uses pure black.
Embedded CSS hides page frames and guide lines. Import reports unsupported objects
to the host so that it can protect the original and offer export to a separate copy.
The Tauri application and upstream release tooling are not vendored; npm test includes checks
for those omitted files. Use npm run test:embed for the drawing/embedding checks (140 at 1.1.2); 13 standalone host/release checks are explicitly excluded in scripts/check-embed.mjs. Native Tauri clipboard assertions are skipped in export.check.ts when its Rust host is absent; the Python host has separate tests.

November 4 fixes: include `exporting` in the displayed drawing's memo dependencies so
the SI SVG shows the same filtered reaction as CDX/CDXML. Embedded SVG exports position
rich-text runs at browser-measured baselines to avoid MuPDF's overlapping centred
subscripts, use black default ink on light paper, and include a small clipping margin.

Update on November 4: merged 1.0.29 -> 1.1.0 with tools/update_octet.py. Conflicts in
Editor.tsx and export.ts were resolved to retain Qt saving/clipboard, SI filtering,
black display-only canvases, reagent equivalents and density/volume rows. Upstream
now also includes the exporting dependency and filters grid rendering for exports.
Cursor.ts uses one 24 px bitmap in the Qt host to avoid an oversized Retina cursor;
cursor.check.ts covers that boundary. The user confirmed normal size on this Mac.
Upstream tools/names/index.mjs and tools/library/clashes.mjs are retained for engine
checks. scripts/check-embed.mjs is an Elucida addition. Updates are staged, reviewed
and tested; upstream native Tauri features do not automatically apply to the Qt host.

Reaction-path composition: picture shapes retain an Elucida asset reference and
sanitized SVG in native JSON (file.ts/render.ts); the standard CDX/CDXML picture is
a PNG fallback. Editor.tsx exposes insert/update/selection APIs and emits an edit
request on double-click. Updates use Octet's normal undo stack and preserve the
shape frame. Display inversion never enters exported SVG. canvasInk uses a shared
screen-coordinate frame for nested SVG viewports and excludes glyph definitions;
otherwise pan/zoom can corrupt the exported bounds. The Python host keeps immutable
asset revisions and independent orbital settings in its project. Review this bridge,
sanitizer and native roundtrip when updating upstream.

Update on November 7: merged 1.1.0 -> 1.1.1 with tools/update_octet.py. Upstream moved the legacy
decoders to charset.ts; the explicit Mac Roman table moved there with them. Conflicts in Editor.tsx,
export.ts and export.check.ts were resolved to retain Qt clipboard, screen-frame canvasInk, reagent
equivalents (reagentLabels replaces conditionItems) and density/volume/molarity rows. The host does
not report `filled`, so an unreadable clipboard stays silent in Elucida.
src-tauri/src/main.rs is vendored unused: the upstream checks of 1.1.1 read the native menu text from it.

Update on November 13: merged 1.1.1 -> 1.1.2 with tools/update_octet.py. Upstream moved the reagent table out of
Editor.tsx into gridview.ts and now reads equivalents from the reagent text itself (stoich.ts reagentEquiv), so the
Elucida block in Editor.tsx is gone; two small changes remain there: reagentEquiv also accepts "Äq." and a decimal
comma, and gridview.ts keeps the Molarity row visible when embedded (Volume and Density are always shown upstream now).
Conflicts in Editor.tsx, export.ts and export.check.ts were resolved to retain the Qt clipboard, the export margin and
the hidden Export button; the new `oct` clipboard field and Word object windows (`office`) are Tauri-only.
src-tauri/src/*.rs and tauri.conf.json are vendored unused because the upstream checks read them. Excluded in
scripts/check-embed.mjs: flatpak, libreoffice, word (packaging), ui (reads upstream's CLAUDE.md), inventory (needs
upstream Git tags) and depth (depends on machine speed, fails in unmodified upstream on a fast Mac).

Local change on November 21 (ChemDraw paste, Windows report): ChemDraw's DoublePosition Right is the left of B->E as
drawn (y down), Left the right; checked in ChemDraw 23.1.2 with invented rings (CDXML and CDX, user and automatic
values). Octet read and wrote the opposite, so ChemDraw's own placed sides in a CDX copy (0x0001/0x0002, which
ChemDraw writes to CDX but not to CDXML) came out of the ring. cdxml.ts now reads and writes ChemDraw's sense and marks
its files `sides: 1` at the top; files without the mark (older Octet) keep Octet's old sense. render.ts raises a charge
minus (en dash) until its ink's middle is level with a plus's, and draws a free written label's trailing sign (BF4-) as a
charge sign (bonded labels such as SO3- keep the sign in the text, since labelOf measures it there); a count before the sign is a charge only for a monatomic ion
(metal cation Fe2+, chalcogenide O2-) or after a space (SO4 2-), else a count (NH4+, SO42-, I3-) (writtenCharge); signAt in cdxml.ts follows. Upstream has neither; offer them upstream.

Local change on November 22: a double bond in a ring of more than nine atoms still counts as a ring bond. When
ringsThrough (which stops at nine atoms) finds no ring, render.ts takes the smallest ring found breadth first
(shortestRing), so a macrocycle's double bond goes inside it instead of taking a chain's side. The own drawer
(elucida/formats/cdxml.py) searches rings of any size too.

Elucida 1.5.0 (local, not upstream; report to upstream, drop when upstream ships an equivalent): chem.ts `analyse`
gives each single-piece entry (and a salt with an abbreviation, ferrocene-like merges) its net atom charge as
`charge`; Actions.tsx writes it after the formula ("Whole drawing": C4H12N+, Cl- instead of C4H12N, Cl), also in
the copied text. Formula strings themselves stay Indigo's (counts, stoichiometry and contract-label text unchanged).
Pieces joined only by a hydrogen bond keep entries without a charge. Check: chem.check.ts (invented salt).
The host (drawing_clipboard.py) now reports `filled` like the Tauri host, so an unreadable clipboard is no longer
silent (see the November 7 note above).
