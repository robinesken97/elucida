# Octet brand rules for Claude Code

Octet is a chemical drawing app (a ChemDraw replacement). Every UI, page, guide and string you write for it must follow this folder.

## Read first
- `BRAND.md` is the brand book. Read it before any UI or copy work.
- `tokens.css` holds every colour, shadow, font, spacing, radius and drawing value as CSS custom properties, with light and dark themes. Import it once at the app root.
- `tokens.json` is the source for `tokens.css`. Change values there, then regenerate the CSS. Never hard-code a hex value, font name or px size that a token already covers.
- `logos/` holds the final marks and lockups (see `logos/README.md`). Use the files as they are. Do not redraw or recolour them.

## Hard rules
- Colours: blue family and neutrals only (`--brand`, `--brand-bright`, `--brand-mist`, `--navy`, neutrals). Do not add other hues. Status colours only for status.
- Fonts: Instrument Sans for all UI text (`--font-sans`), IBM Plex Mono for SMILES, InChI, formulae and coordinates (`--font-mono`). No serif fonts. No Times New Roman. No Geist or Inter.
- Icons: Phosphor Icons only (`@phosphor-icons/react`, Regular weight; 20px tools, 18px rows, 16px chips and buttons, 12px small actions, as BRAND.md Iconography lists). Draw missing chemistry tool icons in Phosphor's style. Record the package in THIRD_PARTY.md when you add it.
- Feel: calm and quiet. One elevation (`--shadow-float`). Motion 150–200 ms ease-out from the motion tokens (`--motion-fast`, `--motion`, `--motion-slow`, `--ease-out`), no bounce (one exception: the toolbar drop, see BRAND.md Motion). No gradients, no shadcn-default look, no template hero sections.
- Canvas: white (`--canvas`). New documents use ACS Document 1996 by the book, including Arial 10 pt atom labels (`--atom-label-font` and the other drawing tokens). Users can change the style. Export matches the page exactly.
- Spelling: British English for all user-facing text (colour, centre, optimise). Chemistry spelling follows IUPAC and the RSC: sulfur, sulfate, aluminium, caesium. Code identifiers keep standard spellings (`color`).
- Guides, help, tooltips, errors and onboarding: ASD-STE100 Simplified Technical English. One instruction per sentence, imperative verbs, active voice, max 20 words per procedural sentence.
- Accessibility: text 4.5:1 contrast in both themes, visible `--shadow-focus` on every control, real buttons and labels.
- Components: one component per job, used everywhere that job appears. Before you build UI, find the component that already does the job and use it. If it can't, extend it. Never make a one-off.
- Menus: every options menu (each tool's menu, the specialist tools, every sub-menu) is `Menu` in `src/Menu.tsx`. Each option is its icon and its full name. Two across by default (more only when the menu would be taller than the window). Groups start a new row under a hairline. The corner grip resizes in whole columns. One small button per option, on hover, for remove or keep. Names fit the cell: shorten the name, never the cell.
- Dialogs: every dialog is `Dialog` in `src/Dialog.tsx` (title, fields one to a row, Cancel and the action; Return acts, Escape cancels). Sliders: `Slider` in `src/Actions.tsx`. Colours chosen freely: `ColourPicker` in `src/ColourPicker.tsx`; never the system colour panel.
