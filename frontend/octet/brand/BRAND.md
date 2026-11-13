# Octet

Octet is a chemical drawing tool built to replace ChemDraw. The brand should feel like a calm, precise instrument: quiet, fast and exact. It should never feel like legacy academic software, and it should never shout.

Octet shares Steps Blue with The Steps Foundation, so the two read as one family, but Octet is all blue and neutral: no warm accents.

## Principles

1. **Free for every individual, near-zero friction.** A hard promise. Octet is a native desktop app (Mac, Windows and Linux) that works fully offline. Download, install, draw: no account, no email wall, no licence key, no watermarks, no export limits, no trial timers. Octet opens to Home, where New drawing is one key away (decision 0003). An account is optional and only adds sync and sharing. Never design a sign-up gate, upsell modal or "Pro" lock in front of an individual feature.
1. **Chill by default.** Soft neutral chrome (`surface`, `hairline`), generous space, one colour family. Nothing flashes, bounces or competes with the drawing.
2. **The structure is the hero.** The canvas is white (`canvas`). Colour in the UI is for state (active tool, selection, focus), not decoration.
3. **Blue only.** `brand` does the work, `brand-bright` marks live interaction, `brand-mist` is the soft tint. Status colours appear only when something needs attention.
4. **Instrument, not paperwork.** No serif faces anywhere in the product, no Times New Roman atom labels, no grey bevelled toolbars. Instrument Sans for the interface, IBM Plex Mono for machine strings.
6. **Crafted, not templated.** Octet must not look like a generic startup template (Geist or Inter, shadcn cards, gradient hero). The type, the eight-membered ring mark and the ACS-correct canvas are what make it ours.
5. **Journal-correct by default.** The `drawing` tokens match the ACS 1996 document style, so an export drops straight into a manuscript.

## Logo

The mark is a regular octagon with a regular hexagon cut out of it (same centre, hexagon point up), in Logo Blue #213C99. The final files and their uses are in `logos/README.md`. Use them as they are; never redraw, recolour, rotate, outline or add effects in code.

- **Primary:** `octet-mark.svg` on `canvas`, `surface` or cream. `octet-mark-small.svg` only under 20 px.
- **White:** `octet-mark-white.svg`, only on navy (#000E2F) or Octet Blue.
- **Ink:** `octet-mark-ink.svg`, one colour (`ink`).
- **Wordmark:** "octet", Instrument Sans Medium (500), −0.03em, `ink`, outlined in `octet-lockup.svg` and `octet-lockup-white.svg`.
- **App icon:** cream tile #F3F0E9 with a black (#000000) stroke inside the tile edge, 1% of the icon (never under 1 px), for contrast on light backgrounds; no shadow. Full-bleed squares (Icon Composer, Apple touch icon, maskable PWA icon) have no stroke, because the system cuts their edge off. Cream is for the app icon only, never the app UI. `src-tauri/icons/` holds the drop-in Tauri set (never regenerate it with `tauri icon`: it overwrites the hand-drawn small sizes); `app-icon.svg` is the macOS master. `src-tauri/icons/Octet.icon` is the Icon Composer file for macOS 26 and later: add it to the asset catalog when the Mac build is signed, or macOS 26 shows the `.icns` in a grey frame. Platform sets are in `brand/app-icon/`, website icons in `brand/web/`.
- **Clear space:** at least half the mark height on every side.
- **Minimum size:** 16px for the mark. Under 20px, use `octet-mark-small.svg` (a smaller hexagon keeps the ring whole).


## Colour

| Token | Light | Dark | Role |
| --- | --- | --- | --- |
| `brand` | #213C99 | #7299FF | Primary actions, active tool, brand text. Light is Logo Blue |
| `brand-hover` | #1A317F | #89ABFF | Hover and pressed brand fills |
| `brand-bright` | #3F6BFF | #3F6BFF | Focus, selection handles, snap guides |
| `brand-mist` | #DCE4F6 | #24335A | Selected tool, active row, soft tint |
| `on-brand` | #FFFFFF | #000E2F | Text and icons on brand fills |
| `navy` | #000E2F | #000E2F | Footers, ground for the white mark |
| `canvas` | #FFFFFF | #000B24 | Drawing area |
| `surface` | #F8FAFC | #0D1D40 | App chrome and page ground |
| `ink` | #0F172A | #ECF0F8 | Text and bonds |

Rules:

- **One family.** Every accent is a blue from the `brand` set. Each one has the logo's hue (OKLCH 266.6°); only lightness and chroma change. Do not add a second hue to "liven things up".
- **Navy is depth, not a background.** Use it for footers and behind the white mark. Do not flood a section with it.
- **Status needs a second signal.** `warning` and `error` always come with an icon or text, never colour alone.
- **Element colouring is optional.** The `atom-*` tokens colour heteroatom labels when the user turns it on. Carbon stays `ink`. Default export is all `ink`, as journals expect.

## Typography

**Instrument Sans** (UI and display) and **IBM Plex Mono** (machine strings). Both are under the SIL Open Font License 1.1: free for commercial use, embedding in the app and redistribution. Load them from Google Fonts on the web, or bundle the official release files in the desktop app (keep the OFL licence file with them).

Why Instrument Sans: it is a clean, precise grotesque with the polish of San Francisco but a little more character, and it is not the default face of every startup template. IBM Plex Mono brings quiet scientific credibility to SMILES, InChI and formulae without looking like a code editor.

- App UI runs at 13px (`ui`), the same as macOS system UI.
- Headlines use weight 600 and negative tracking. Never use 800 or 900.
- Atom labels and captions on the canvas follow the document style. The default is ACS Document 1996, by the book: Arial at 10 pt (`atom-label-font`, `atom-label-size`). Export matches the page exactly. Subscripts at 70% size, dropped 0.25em.
- SMILES, InChI, formulae and coordinates use IBM Plex Mono (`smiles`, `formula`).
- The system stack (`-apple-system`, SF Pro) is the fallback, so the app still looks native before the fonts load.

## Space, shape and depth

- 4px base grid. Toolbars use `space-2` gaps, panels `space-4` padding.
- Controls use `radius-sm` (6px). Buttons and popovers `radius-md`. Panels and dialogs `radius-lg`.
- One elevation only: `shadow-float`, for floating palettes and menus. Panels sit flat, divided by `hairline`.
  A knob (switch, slider, colour picker) has `shadow-knob` under it, so it shows on any fill.
- Every control shows `shadow-focus` on keyboard focus.
- Motion is short and soft: 150–200ms ease-out fades and slides. No bounce, no spring overshoot. Use the motion
  tokens (`motion-fast`, `motion`, `motion-slow`, `ease-out`), never a duration or curve typed by hand. Whatever
  opens with a motion closes with one, a little faster.
  One exception, from Sam (16 October 2026): dragging an option onto the toolbar. The item settles into
  its slot and the other icons ripple a 2px bounce. It gives toolbar customising some character; it
  never touches the drawing. Reduced motion turns it off.

## Controls

Each kind of control has one look, on every page and in every panel. The values are tokens (`tokens.json`: `size`, `state`, `layer`, `radius`, `spacing`). `src/ui.check.ts` fails the test run if a value is typed by hand.

### Size

| Token | Height | Use |
| --- | --- | --- |
| `size-action` | 18px | A small action on an item: the X of a pill, a tab or a chip, the remove and keep badges |
| `size-control-sm` | 24px | A panel's Minimise, Full screen and Close, a button in a notice or a table row, a pill |
| `size-control` | 28px | Every button with text, field, select and segmented control |
| `size-row` | 30px | A row in a list (Actions, Settings' sidebar, a list menu), and the chips in the Actions panel |
| `size-tool` | 32px | Toolbar tools, the Actions panel's icon buttons, the pills on the canvas (Export, Feedback, Actions) |
| `size-cell` | 36px | A menu option and a command palette row |

Controls in one row have one height. A new control takes the height of its kind from this table.

The segments of one segmented control have one width: the width of the widest segment. Tabs are segments. The + at the end of the tabs is a segment too, as wide as a tab.

### Shape, spacing and layers

- Corners are a `radius` token. Marks under 12px use `radius-2xs`.
- Every gap, padding and margin is a `space` token. 1px and 2px are lines and can be typed.
- A `z-index` is a `z-` token (`layer` in `tokens.json`, low to high). Inside one component, a small number puts a part in front of or behind its siblings.

### Fill

- A field is a well: `canvas` fill, `hairline` edge. Fields are selects, number fields, search fields and segmented controls.
- A button with an edge has the `surface-raised` fill.
- A button with no edge is clear.

### States

| State | Look |
| --- | --- |
| Hover | `surface-sunken` fill and `ink` text. On a sunken ground the fill is `hairline`. The rule is inside `@media (hover: hover) and (pointer: fine)` |
| Press | The control scales to `press` (0.97). A control of 24px or less uses `press-small` (0.92). A full-width row or a tile uses `press-large` (0.98) |
| Focus | `shadow-focus` |
| Selected, on, current | `brand-mist` fill and `link` text. A switch and a tick box are on with the `brand` fill |
| Disabled | Opacity `disabled` (0.45). Nothing else changes |

Hover, press and a change of state fade over `motion-fast` on every button. A row in a list or a menu has the press only, so its highlight follows the pointer with no delay.

A toggle that sits beside fields and segmented controls (the Spectrum and Mass spec panels) is a segmented control of one: a well, with a `brand-mist` segment inside it when it is on. Chips, tools, rows and menu options fill their whole shape when they are on.

A tab that can close has the same room on each side of its name. The X shows in the room on the right when the pointer or the focus is on the tab. The name stays in the middle and the X never covers it.

### Small actions

- A panel's own controls (Minimise, Full screen, Close) are 24px, clear, with `radius-sm` corners.
- A small action in a row (forget a name, hide a problem, the X of a pill or a tab) is 18px, clear, with `radius-sm` corners.
- A small action on a tile, a key or a menu option (remove, keep) is an 18px circle with the `surface-raised` fill and a `hairline` edge, so it shows on any content.
- The button that clears a search field is a 16px filled circle.

### Shortcuts

A shortcut beside a command is plain 11px text in `ink-faint`. Only the tutorial card draws a key cap, because it shows a key to push.

### How overlays come and go

- An overlay comes in from scale 0.97 and from 4px away at most. It goes out to 0.98.
- A glyph that pops (the Select tool, a carried option, a tick) starts at 0.85.
- Menus, lists and panels use `motion-fast`. Bars and panes use `motion`. Dialogs, Settings and the tutorial card use `motion-slow`. Everything goes out on `motion-fast`.
- Motion uses `transform`, `translate` and `opacity`. `src/ui.check.ts` lists the few controls that change layout as they move, each with its reason.

### Before you add or change a control

1. Find the control that does the same job. Use its component or its class.
2. Take every size, corner, space, colour, shadow and time from a token.
3. Run the app. Measure the new control and the controls beside it: height, width of each segment, corners, font, icon size. They must be equal. In development the app measures its own controls (`src/lookwatch.ts`). Read the console: an error that starts with `look:` is a control that does not match.
4. Look at hover, press, focus, selected and disabled, in the light theme and the dark theme.
5. Run `npm test`.
6. On a Mac, run `npm run look` with the dev server running. It loads the app in WebKit (the engine the Mac app runs in), goes through its panels, dialogs and pages, and fails if a control does not match. A browser preview is a different engine: it is not enough alone. When you add a panel, a dialog or a page, add it to `scripts/look/sweep.js`.
7. Tell Sam what you measured. Do not give Sam a list of things you did not check: check them first.

## Iconography

Every icon comes from [Phosphor Icons](https://phosphoricons.com) (MIT), Regular weight. One size per role:

| Size | Role |
| --- | --- |
| 20px | Toolbar tools |
| 18px | Panel rows, menu options, command palette rows |
| 16px | Icons in chips, in buttons with text and in fields |
| 12px | Small actions: close, remove, add, carets, checks, pins |

Give each action its own icon, at least within one panel and in the command palette. Chemistry tools Phosphor lacks (bond types, rings, curly and fishhook arrows) are drawn in Phosphor's style: 256-unit grid, 16-unit stroke, round caps and joins. Icons are drawn in `ink-muted`, and `brand` when active. No other icon sets. Chemistry tools draw the real object: the bond tool is a bond, the ring tool is a hexagon, the arrow tool is a curly arrow. No filled glyphs, no emoji, no clip-art flasks.

## Voice

Short, relaxed, chemist-to-chemist. Use the real terms (wedge, hashed bond, curly arrow, Kekulé) and skip the hype.

- Yes: "Paste a name, SMILES or InChI." / "Valence error on N3."
- No: "Unleash your molecular creativity!"

### Rule: British English, everywhere

Every word a user reads is British English: UI, guides, errors, marketing, emails, the website. No exceptions.

- **-our:** colour, behaviour, favourite. Never color, behavior.
- **-ise / -isation:** optimise, organise, recognise, customisation.
- **-re:** centre, metre (not center, meter).
- **Chemistry follows IUPAC and the RSC:** sulfur, sulfate, sulfide, sulfonyl (always "f", never "ph"), with aluminium and caesium kept British, as the RSC does. Chemical names, units and symbols follow current IUPAC recommendations, in the UI and in every export.
- **Other:** licence (noun) / license (verb), grey, analyse, catalogue, programme (except computer program), modelling, labelled, travelled.
- **Dates and units:** 14 October 2026, 24-hour time, SI units, °C.

Code is the one exception: CSS properties, API fields and token names keep their standard spellings (`color`, `center`), because the language requires them. Labels that show those values to users are still British.

### Guides, help and UI text: ASD-STE100

All guides, help pages, tooltips, error messages and onboarding follow **ASD-STE100 Simplified Technical English**. Marketing headlines can be looser, but anything that tells a user how to do something is STE.

- **One instruction per sentence.** Procedures: 20 words maximum. Descriptions: 25 words maximum.
- **Start procedural steps with a verb** in the imperative: "Select the bond tool." Not "You can select the bond tool."
- **Active voice only.** "Octet calculates the formula." Not "The formula is calculated."
- **Use one word for one meaning.** A "bond" is always a bond, never a "line" or "link". A "ring" is always a ring, never a "cycle" in UI text.
- **Use simple approved verbs:** use, select, push, move, set, make sure. Not utilise, leverage, navigate, configure.
- **No -ing forms for actions** and no phrasal verbs where a single verb works ("remove", not "take off").
- **Put warnings before the step** they apply to, never after.
- **Name the exact UI element** in bold: **Export**, **Bond length**, **Clean structure**.

Example, a guide step:

> 1. Select the **Ring** tool.
> 2. Click the canvas. Octet adds a benzene ring.
> 3. To fuse a second ring, click a bond on the first ring.

Example, an error:

> N3 has five bonds. Nitrogen has a maximum of four. Remove one bond or add a positive charge.
