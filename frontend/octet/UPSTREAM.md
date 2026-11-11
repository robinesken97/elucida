# Octet source snapshot for Elucida

Source: https://github.com/SamChemMan/Octet-Draw
Commit: 934719abf213e0a8c9725256338bcbc0f305cab6.
Version: 1.1.1 (pinned source commit; no automatic tracking of main).
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
for those omitted files. Use npm run test:embed for 94 drawing/embedding checks; seven standalone host/release checks are explicitly excluded in scripts/check-embed.mjs. Native Tauri clipboard assertions are skipped in export.check.ts when its Rust host is absent; the Python host has separate tests.

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
