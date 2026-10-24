**English** | [Deutsch](CHANGELOG.de.md)

# Changelog

## 2.3.1 – 2026-10-24

### Changed
- **Every compound belongs to a project:** New compound first asks for the project; compounds without a project
  (older versions) are offered for assignment when opened. **Move** a compound to another project or **copy** it into
  one (the same compound in two papers); Add compound moves or copies into the project.
- Elemental analysis is always optional and built like the HR-MS line: "Elemental analysis (%) calc. …; found …".
- **Navigation:** a path at the left of the tab bar – **⌂ Overview › project › compound ▾** – leads back to the project
  or the overview with one click and switches directly to another compound of the project; the project page has
  "⌂ Overview" above its title; File → Back to overview (Ctrl+Shift+H). Before, a compound without a project had no
  visible way back to the overview.
- The example project and the example compound no longer appear in the overview after looking at them; the example
  compounds now have artificial data for everything on the checklist (2D NMR, HRMS, IR, m.p., elemental analysis).
- README: screenshot of the project page.

### New
- **Move to trash** from the overview (right-click on a compound or project): with a question naming the folder, the
  number of files and the size (for a project also the compounds inside it); never deleted permanently.

### Fixed
- Closing a compound could log an error from the NMR tab.

## 2.3.0 – 2026-10-24

### New
- **Projects:** a parent folder for all compounds of a paper (File → New project). The compounds
  stay as they are (each can still be opened on its own); the project keeps their order, the details for the
  dataset (title, authors, DOI, license, descriptions) and the SI texts. Shown on the welcome page with its compounds;
  recent compounds show which project they belong to.
- **Data packages for the whole project** like the group's datasets on TUDOdata: one zip per compound,
  DFT calculations of all compounds in `CompChem.zip`, `README.txt` from the details and the license text
  (CC BY 4.0 or CC0). Lab codes are assigned to their compound and replaced everywhere, dates removed – as for the
  single package.
- **Complete SI as one Word file** with title page and table of contents, chapters as in the group's SI
  (Materials and Methods, Synthetic Procedures and Characterization Data, NMR Spectra, UV-Vis, EPR, CV, SEC, X-ray,
  Computational); compounds in the order of the project, figures numbered throughout, crystal data of all
  structures in common tables. "Materials and Methods" and an introduction per chapter are edited once for the
  project (SI texts). Title page with the title of the paper as in the group's SI; page numbers in the footer;
  the table of contents is filled in already (page numbers estimated, Word updates them when opening). Templates
  group (as the own Angewandte SI), Wiley, ACS (pages S1, S2 …), RSC and Nature (title page and figure/table
  labels; checked against the publishers' author guidelines).
- **Checklist per compound** on the project page: ✓/✗ for ¹H, ¹³C, 2D NMR, HRMS, IR and m.p. (compounds marked
  **known from the literature** in the Compound dialog, with a field for the reference: only ¹H and ¹³C); further data
  (EA, UV-Vis, X-ray) in grey, summary of what is missing at the top.
- **Back to the project** with one click: button at the left of the tab bar while a compound of a project is
  open (also File menu, Ctrl+Shift+P).
- Compound dialog: **Oil** next to the melting point – the SI then reads "m.p. <25 °C".
- **Example project** (Help menu, welcome page) with two compounds and artificial data; quick start for
  projects in the README.
- **Note for the compound** (dialog Compound), e.g. "radical cation of 6m" next to the lab number: shown on the
  welcome page and in the title bar, searchable, passed to Characterization (`elucida.json`) – never into the SI,
  Word export or data package.

### Changed
- **Figures:** the inset (linear regression) is never drawn over the spectra – if there is no free space, it moves
  next to the plot (without its table, R² in the legend). Peak labels are arranged in order: in one row at the same
  height, otherwise as a left-aligned block sorted by wavelength.
- **Captions:** fluorescence names absorption and emission (colours, λex), solvent, concentration and cuvette (new
  caption fields); CV says the potentials are referenced against Fc0/+ with diacetylferrocene (and its E½) as
  internal standard, as on the axis; CV/SEC texts use Fc0/+ throughout. X-ray: no symmetry-code footnote in the
  figure and caption any more (the codes stay in the parameter tables).
- Data processing texts describe only the mathematics – no reference to the program.
- README reorganised: short introduction for the whole program, the welcome page with an example project as cover,
  sections in the order of the tabs, overview of all supported files; all pictures in dark mode.
- **New terms:** what used to be a "project" (folder of one compound) is now called a **compound**; **project** now
  means the folder with all compounds of a paper. Only the wording changes – folders and files (`project.elucida`)
  stay as they are, nothing has to be converted.

## 2.2.3 – 2026-10-24

### New
- **Welcome page with a real overview of recent projects:** structure of the compound, which techniques the project
  contains, when it was last changed; search, right-click to show in folder or remove from the list; up to 20
  projects. The structure picture is saved with the project, so the page stays fast.

## 2.2.2 – 2026-10-24

### New
- Line drawing (DFT): option **Atoms in element colours** – balls filled in their element colour, outlines and
  hollow sticks stay.

### Changed
- **Opening a project is much faster** (example project: 2.1 s -> 0.2 s): the window is no longer rebuilt, and each
  tab is built only when it is first shown or needed (first click on a tab ~0.2 s).
- ChemDraw structures are read only once per session.

### Fixed
- Line drawing (DFT): bonds pointing towards the viewer now come out of the ball instead of from behind it, and the
  outlines of the sticks are as thin as those of the balls.

## 2.2.1 – 2026-10-24

### Changed
- **Undo/redo is much faster:** only the tab that changed is rebuilt instead of the whole window (example project:
  1.5 s -> 0.1 s); the same for "Reset all" and loading a preset in a tab.
- **Opening a project is faster:** hidden tabs draw their figure only when they are shown; the SI export packs the
  fallback images for Word faster.
- File readers moved into their own modules (`elucida/formats/`: Gamry, BWSpec, EPR, OPUS, MS report, Bruker .d,
  TopSpin, Mnova, CIF, xyz/ORCA/Gaussian, cube/Molden) – no visible change.

### Fixed
- The example project was saved empty (opened again it showed no data).

## 2.2.0 – 2026-10-24

### New
- **Data package (zip) per compound** (File → Export data package): the raw data for a data repository such as
  TUDOdata, laid out like published datasets – `6m.zip` with `6m/NMR/1H/10/` (complete TopSpin experiments),
  `NMR/HSQC + HMBC/12/`, `IR/`, `MS/` (report, Bruker .d), `UV-Vis/`, `Fluorescence/`, `CV/<solvent>/`, `SEC/`, `EPR/`;
  DFT and Elucida's own figures/SI optional, X-ray and synthesis not included. Every file can be deselected, the
  choice is remembered per project.
- **Lab codes and dates removed:** codes such as `RE-3-150` are found automatically and replaced – in names by the
  compound, in the contents by „Compound 6m“ – and dates and times are deleted: in text files (CSV, Gamry DTA, EPR,
  TopSpin parameters, title and audit trail), in the MS report (text, file author and dates, labels in its spectra)
  and in OPUS files. The measured values stay byte-identical; codes left in files that cannot be edited (PDF, Mnova,
  Bruker .d) are listed in the log.

### Changed
- Check boxes in lists show the partly-checked state of a group.

## 2.1.0 – 2026-10-24

### New
- **Orbitals in the DFT tab, looking like IboView:** isosurfaces of molecular orbitals over the structure. Input as
  Molden file (ORCA: `orca_2mkl name -molden`; all MOs, HOMO and LUMO are added, further MOs from a list) or as
  Gaussian cube (ORCA: `orca_plot`, Gaussian: `cubegen`). Isosurface as in IboView enclosing 80% of the orbital
  density (adjustable, or a fixed isovalue), IboView colours per orbital, translucent with more opaque edges,
  lighting and depth fading as in IboView; atoms are drawn as in IboView (tapered sticks, element letters, double and
  partial bonds from the wave function like IboView's IAO bond orders). Checked side by side against IboView itself.
- **NMR raw data:** TopSpin experiments (also whole datasets or several at once, by drag & drop too) are copied into
  the project completely and sorted by kind (`data/nmr/1H`, `13C`, `DEPT135`, `HSQC` …), shown in a new **Raw data** tab
  next to the figure and assigned to the matching spectrum automatically (parameters, temperature). Mnova documents
  (`.mnova`) can be added as well.
- NMR spectra can also be **EMF** files from Mnova; they go into Word unchanged.
- The IboView look is also available as a style for any structure in the DFT tab, with or without orbitals.
- HOMO/LUMO names and orbital energies from the Molden file or the ORCA/Gaussian output of the geometry.
- Export: one figure per orbital (PDF/SVG with the orbital embedded as a 300 dpi image, atoms and labels stay
  vector); Word SI: orbital figures with caption below each calculation.
- Molden files are checked: the basis-function convention (standard or ORCA) is taken from the orthonormality of the
  orbitals; files that fit no known convention are rejected.
- **elucida.json** in the project folder: a summary for the Characterization program (compound with SMILES/InChIKey,
  which analytics exist and where their files are, HR-MS and elemental analysis values, the SI lines and paragraph,
  the SI Word file and the latest figures). Written when saving, after exports and shortly after autosave;
  Characterization only reads it.

### Changed
- **Clearer project folder:** exports are sorted by kind – `SI/` (Word files, SI texts), `figures/` (PDF/SVG/PNG) and
  `tables/` (CSV, Excel, xyz) – and named after the compound (e.g. `S2_CV.pdf`, `S2_SI.docx`; UV-Vis per series
  `<series>_UV-Vis.pdf`). Measurement data go to `data/<technique>/` (nmr, ir, hrms, uvvis, cv …), structures, schemes
  and photos to `structures/`. Intermediate images for Word, the photo cache and the backup are in the hidden folder
  `.elucida/`. Folders appear only when something goes into them.
- The project file is now called **`project.elucida`**. Projects from older versions (`project.uvvis`) open as
  before; when saved, the new file is written and the old one is kept as a backup in `.elucida/`. Elucida 2.0 and
  older cannot open projects saved with 2.1.
- Projects from older versions open as before; their files stay where they are, only new files and exports use the
  new layout.
- Source code reorganised into the package `elucida/` (app, core, tabs, formats, si, exchange); start from source with
  `python Elucida.py`. No change for users of the installed app.

## 2.0.3 – 2026-10-23

### New
- **Line drawing** style in the DFT tab, like classic journal figures: white balls with outline, hollow sticks,
  atoms in front slightly larger.
- **Label colour** in X-ray and DFT: black or like the atom (light colours darkened so they stay readable).
- X-ray and DFT: **Shift + drag a box** to hide or show the labels of several atoms at once.

### Changed
- **Ball and stick** in the DFT tab looks like the figures in the ORCA 6 manual (colours, lighting, soft highlight,
  proportions); the IboView-like style was removed. X-ray offers only Mercury and Olex2; projects with an older style
  open with the closest one.
- **Result tabs alike in every tab:** the card fills the page, tables use the full height, buttons sit at the bottom
  right with the main one in blue. UV-Vis (ε) shows Results and SI line next to the figure instead of below it, so
  the figure is larger; the log is under Help → Log.
- Empty-tab guides look the same everywhere (also Synthesis and NMR) and sit in the middle of the area.
- Messages appear as a small box at the bottom right; the empty status strip below the footers is gone.

### Fixed
- Opening a project could show the error "Internal C++ object already deleted".
- macOS Intel: the example project could not be created (older RDKit).
- A figure could stay too small after being hidden behind another tab.

## 2.0.2 – 2026-10-23

### New
- **Welcome page** without a project: what the program does, New project / Open project / Open example project and
  the recently opened projects.
- **Example project** with artificial data for all tabs (Help → Open example project) – to try everything out.
- **Help menu:** guide for the current tab (F1), quick start, example project, log.
- **README:** quick start in six steps and step-by-step guides (German and English) for synthesis to the SI, UV-Vis ε,
  CV and SEC, EPR, crystal structure and DFT.
- After an export, the message offers **Open folder**; synthesis and NMR have the same footer with **Export** as the
  other tabs.

### Changed
- The **left column always fits its content** – nothing is cut off at the right edge, also on smaller laptop screens
  and with wider fonts (Windows); the rest of the width goes to the figure.
- Buttons are only active when they can do something ("Combine" from two selected TD-DFT entries, "From scheme" with a
  scheme).

### Fixed
- UV-Vis (ε) tab: the left column could be cut off on a MacBook ("Concentrations…", "g/mol", "Remove").

## 2.0.1 – 2026-10-23

### New
- **Clearer, calmer interface:** the twelve tabs are grouped like the SI in a bar on top (synthesis & analysis,
  UV-Vis & photophysics, electrochemistry & EPR, structure & computation); **SI (Word)** is the main button in the
  toolbar. The figure keeps its full size – the new bar costs height, not width.
- **Tidy left column in every tab:** rarely used cards are collapsed (axes, size and formats; figure caption; CV
  referencing; SEC highlighting; EPR intensity and kinetics; X-ray atoms, alignment and colours …). A collapsed card
  shows **"(changed)"** when a setting inside differs from the default. Results, tables and SI text sit in tabs next to the
  figure (CV results, X-ray caption and tables, DFT SI text). Even spacing, all number fields the same width and
  right-aligned, labels level with their fields.
- **Guides in empty tabs:** what the tab produces, which files it needs and where they come from, four steps, a link to
  the matching README section and an "Add files…" button.
- **Warnings where they happen:** e.g. when the overlay leaves out a curve (no concentration for ε), the reason is shown
  below the preview; **Help → Log…** shows the log of all tabs.
- **X-ray and DFT:** selectable **background** (white, transparent, colour) for preview, PDF/SVG/PNG and Word.
- **Overlay:** predicted **colour in solution** for TD-DFT spectra (A = ε·c·d, default 1 mM in 1 cm; qualitative).
- **UV-Vis (ε):** optional **λ₁/ε₁ … indices** on the band labels.
- **New icon:** spectrum with a pyridine ring.

### Changed
- **Ball and stick (X-ray, DFT):** atom radius and bond thickness now apply, relative to the defaults (the defaults keep
  the previous look).
- **Faster rotation** in the ball-and-stick styles (about 20 ms instead of 140 ms per step at 80 atoms); figures and
  exports are pixel-identical.
- The mouse wheel scrolls the left column and only changes a field after it has been clicked.
- Clearer names and tooltips throughout ("Save preset…" instead of "Save…", "Peak threshold", distinct copy buttons,
  ε-only commands in File → UV-Vis (ε), "Export (current tab)" …).

### Fixed
- After dragging a label or picture the figure is redrawn completely, so nothing disappears until the next click.
- CV: "as above" for the reference of a measurement pointed to a setting further down.

## 2.0.0 – 2026-10-22

### New
- **DFT tab: measure and align** like the X-Ray tab – distance, angle and dihedral by clicking 2/3/4 atoms (values
  from the geometry), bond direction, plane face-on, step rotation, flip and ChemDraw template. Both tabs share the
  same code, so they behave identically.
- **New structure styles** in the X-Ray and DFT tabs (preview, PDF/SVG/PNG, Word): **ball and stick, glossy** (like
  IboView: shiny spheres with shadow rim and highlight, thin rods coloured by atom with a highlight streak) and **ball and
  stick with depth** (matte spheres, thick rods, atoms further back lighter).

### Changed
- **Mercury style** now looks like Mercury figures: black bonds and bold labels; default bond thickness 0.12 Å
  (existing projects keep their setting). Element colours unchanged.
- **New name: Elucida** (formerly Spectravolt). The program has grown from UV-Vis and electrochemistry into a full
  characterization suite (synthesis, NMR, IR, HRMS, UV-Vis, fluorescence, CV, SEC, EPR, X-ray, DFT). Settings, recent
  projects and the data folder (e.g. the background-removal model) are taken over automatically on the first start;
  projects open as before. The repository is now `robinesken97/elucida`; old links and the update check of older
  versions are redirected by GitHub.
- New icon: the visible spectrum stays, a benzene ring replaces the lightning bolt.
- Downloads are now called `Elucida-<system>.zip` (Windows/macOS), `.AppImage` and `.tar.gz` (Linux). On macOS the app
  is `Elucida.app`; the old `Spectravolt.app` can be deleted after the first start.

## 1.25.1 – 2026-10-22

### New
- Toolbar button **Show project folder**: opens the project folder in Finder (macOS), Explorer (Windows) or the default
  file manager (Linux, e.g. Dolphin or Nautilus); disabled without a project.

## 1.25.0 – 2026-10-22

### New
- **Reset all to defaults:** the "Reset" button (bottom left of every tab with a figure, including UV-Vis (ε)) has a menu:
  "Reset layout" as before, or "Reset all to defaults" for all settings of the tab (display and analysis). Data and
  measurement details stay: files, reference and calibration (CV, SEC, EPR), path length, entered values (ε, λex,
  adduct, removed IR peaks), captions and export size. Undo brings everything back.
- **X-Ray and DFT:** "Reset display to defaults" next to "Reset view": style, ellipsoids/radii, bond thickness, labels,
  label size, disorder, H atoms and – for the selected structure – view, hidden atoms/fragments, labels per atom and
  wireframe. CIF/xyz files, names, numbering and selected parameters stay.

## 1.24.1 – 2026-10-22

### New
- **SEC: highlight intermediate species.** Besides the first (blue) and last spectrum (red), one or more intermediate
  spectra can be highlighted in green (further ones orange, purple, teal), e.g. for the radical cation. Selected by
  potential (axis scale; the spectrum with the nearest potential is used) or, without a potential file, by spectrum
  number. Potential label as for start/end; λ labels take the colour of the highlighted spectrum with the largest
  absorbance. Caption field "Intermediate species": "Color coding: **neutral** (blue), **radical cation** (green),
  **dication** (red)." – only colours that appear in the figure. Without input everything stays as before.
- **SI (Word): data processing and fitting.** New selectable part: the methods texts of all tabs that fit (UV-Vis (ε),
  CV, SEC, EPR – the same text as "Copy SI text": only the steps used, current parameters, then the results) as a
  section "Data processing and fitting" behind the figures.
- **Font of the Word exports** selectable in the SI (Word) dialog (default Arial); the size stays 11 pt.

### Changed
- Synthesis tab: only the reaction scheme is shown on a white background (and only when a scheme is loaded); the
  preview text follows the light/dark theme again.
- README: new screenshots of all tabs (including Synthesis and NMR), created with `tools/make_screenshots.py` from
  synthetic data only.
- Checkboxes with their own border and an accent-coloured tick (unchecked boxes were almost invisible in dark mode).

### Fixed
- UV-Vis (ε): structure hints (formula, "drawn from the CDXML coordinates", warnings) now follow a language switch.
- CV: with the colour gradient by scan rate, the colour fields in the list show the colours of the figure and are
  locked (they used to show colours that were not used).

## 1.24.0 – 2026-10-22

### New
- **Synthesis tab:** "Synthesis of **Name**", reaction scheme from ChemDraw and the procedure with formatting (bold,
  italic, sub-/superscript). With a `.cdx` of the same name next to the CDXML, the scheme becomes an **editable ChemDraw
  object** in Word (double-click opens ChemDraw; an `.emf` from ChemDraw gives a sharp preview). **Amount check:**
  "(1.03 g, 5.00 mmol, 1.0 eq.)" and yields in the procedure are checked against the reagent table, taking
  the rounding of the given digits into account. Reagent table from the scheme (reactants, reagents above/below the
  arrow such as K2CO3, solvents, product).
- **NMR tab:** SVG exports from MestReNova; nucleus from the axis label (or entered by hand), order ¹H, ¹³C, other
  nuclei by mass number, then 2D (HSQC, HMBC …). Mnova multiplet report → NMR line in the style of the SI, with
  assignments per signal; ¹³C line also from the peak labels of the spectrum. Temperature 298 K or from the Bruker
  folder (acqus) with a parameter overview. The structure is placed in a free spot automatically (no signal, label or
  integral covered), can be dragged, and its size (mouse wheel) is the same in all spectra. Word: two spectra per page,
  "Figure Sn: ¹H NMR (500 MHz, CDCl₃, 298 K) of **Name**."
- **SI (Word) with all figures:** UV-Vis (ε), IR, HR-MS, overlay, fluorescence, CV, SEC, EPR and NMR – always two per
  page (scaled to fit if needed), with captions in the style of the SI. CV, SEC and EPR fill their captions from the
  data (scan rate, iR compensation, reference, potential range, band, g and couplings) plus a few fields
  (concentration, solvent, electrolyte, species). UV-Vis: "… in THF, measured in 0.1 cm quartz cuvettes."
- **Setup text (SI)** per tab (CV, SEC, EPR): paste your instrument/setup paragraph once; it is stored on your computer
  only and placed before the figures of that tab.
- **Fonts and frames per tab:** Format → "Fonts and frames…" applies to all tabs or only to the open one, and shows only
  what that tab has in its figure.
- Structures without a ChemDraw export are now **drawn from the CDXML coordinates** (abbreviations such as TMS or Dipp
  stay, arrows and conditions in schemes); RDKit only as a fallback.

### Changed
- New app icon (spectrum in the colours of the visible range with a bolt) and new short description "From synthesis to SI".
- Tab order as in the SI: Synthesis · NMR · IR + EA · HRMS · UV-Vis (ε) · overlay · fluorescence · CV · SEC · EPR ·
  X-Ray · DFT. The open tab is remembered by name.
- Closed frame around the plot is now the default (as in the Origin figures of the SI); existing projects keep their
  setting.
- UV-Vis (ε): solvent field moved to "Analysis" (next to the path length).

### Fixed
- Word files no longer open in compatibility mode.

## 1.23.0 – 2026-10-22

### New
- **DFT tab:** load xyz files and outputs of **ORCA 6** and **Gaussian** (UTF-16 files from a PowerShell redirect are
  recognised); rotatable figure in the style of the X-Ray tab.
- DFT: **renumber atoms by clicking** them in the desired order; the remaining atoms keep their order (optionally H
  atoms right after their atom). The xyz is saved as a new file with the lines unchanged (only reordered, all frames
  of a trajectory); ORCA counting from 0 optional.
- DFT: **number like a template** – take over the numbering of another geometry or of a crystal structure from the
  X-Ray tab (then with the atom names of the CIF). Matching by connectivity and, for symmetric molecules, by geometry;
  equivalent assignments are reported, never chosen silently.
- DFT: **SI block** per calculation as in the group's SI: name, figure, charge/multiplicity/point group, Cartesian
  coordinates, table E_el/H/G (ZPE optional); method line (per structure or once as "Computational details"),
  convergence table and frequency result can be switched on and off. Values exactly as in the output. Warnings for
  aborted runs, non-converged optimisations and imaginary frequencies. Word file in two columns.
- **SI (Word)** button in the toolbar: choose the parts (characterisation, X-ray, DFT) for the SI section.
- Label size adjustable in the X-Ray and DFT tabs.
- SI texts (Word and copy) with **non-breaking spaces** between number and unit, around "=" and "±", within
  composite units and in the elemental analysis.

### Fixed
- X-Ray: SI figures without labels were cropped at the edge.

## 1.22.1 – 2026-10-22

### Fixed
- CV baseline: now also ends before the wave rises (2% of the peak height). For broad waves (iR drop, ΔE_p > 100 mV,
  e.g. in THF) it previously lay in the foot of the wave and made i_pa up to 36% too small.
- CV: no Nicholson ratio if another process lies between the forward peak and the switching potential (e.g. Ac₂Fc or
  a second wave) – the formula does not apply then; shown as "–", left out of the i_r/i_f plot.
- CV: E½ in the figure per group (previously averaged over all groups, e.g. solvents).
- SI text: scan rates rounded (Gamry stores e.g. 499.999 mV/s).

## 1.22.0 – 2026-10-21

### New
- CV: **baseline correction** of the peak currents (on by default): straight line through the current before the
  forward peak, shifted by the charging-current step at the switching potential for the reverse peak; Nicholson ratio
  from the corrected currents. Baselines optionally in the figure.
- CV: new plots **log i_p vs. log v** (diffusion/adsorption) and **i_r/i_f vs. v** (chemical reversibility).
- CV: regressions against scan rate with a **95% confidence interval** for slope and intercept.
- **Copy SI text** in every tab that fits (UV-Vis (ε), CV, SEC, EPR): English methods paragraph with exactly the
  evaluation steps and settings used, followed by the results; written as `…_methods.txt` on export.

### Changed
- CV: i_pa, i_pc and i_r/i_f change in existing projects because of the baseline (can be switched off); peak
  potentials and E½ stay the same. The result line now evaluates per group (previously groups, e.g. solvents, were
  mixed in one Randles–Ševčík regression).
- CV results table: column "i_r/i_f" instead of "i_pc/i_pa" (reverse/forward peak, correctly named for a cathodic start).

## 1.21.0 – 2026-10-21

### Added
- New tab **HRMS** (MS part of the former IR + MS tab): with Bruker raw data a chromatogram (TIC and ion current) with
  a range selectable by dragging, the averaged spectrum over the LC range, peak picking by click as *found*, and the
  calculated isotope pattern of the ion (mirrored) with measured/calculated isotope ratios.
- X-Ray **orientation**: bond (first → second atom) pointing down/up/left/right, plane through ≥ 3 atoms face-on,
  rotation in steps about x/y/z, view from behind, and **orientation like a ChemDraw drawing** (CDXML of the project
  compound; atoms matched by elements and connectivity).

### Changed
- The tab IR + MS + EA is now **IR + EA**; old projects take their MS data over into the HRMS tab.

## 1.20.0 – 2026-10-21

### Added
- **Elemental analysis** in the tab now called **IR + MS + EA**: calculated from the project formula (optionally with a
  solvate such as 0.5 CH2Cl2), found values entered, deviations > 0.4 % flagged; line for the SI.
- **UV-Vis line for the SI** (page *SI line* in the ε tab, optional solvent): λmax with ε as in the figure, ascending.
- **File → Export SI section (Word)**: characterisation paragraph (m.p.; IR; HR-MS; UV-Vis; elemental analysis) plus
  the X-Ray part as a .docx laid out like the group's SI (Arial 11, 1.5 lines; ORTEP figure as vector graphic, cropped;
  “Figure Sn: X-ray solid state structure of …” with occupancy of disordered parts; selected parameters in the caption
  or, if more than 8, as “Table Sn: Selected bond lengths/angles for …”; crystal-data table with the column widths of
  the SI; numbers as Word fields).
- Melting point in **Compound …**.

### Changed
- Tabs renamed: **UV-Vis (ε)** (formerly ε analysis) and **UV-Vis overlay** (formerly Overlay).
- X-Ray: caption and crystal-data labels in the style of the SI (“Thermal ellipsoids are shown with 50% probability”,
  “*a* / Å”); selected parameters in the atom order of the CIF.

### Fixed
- X-Ray: labels no longer touch bonds (exact collision test); stored label positions that land on a bond or atom
  after rotating are placed anew.

## 1.19.0 – 2026-10-21

### Added
- New tab **X-Ray**: read CIF files (several structures/`data_` blocks), rotatable **ORTEP figure in the Mercury
  style** (shaded ellipsoids at adjustable probability with principal ellipses, colours freely changeable per element,
  draggable labels; flat Olex2 style optional), atoms and labels switchable per atom (double-click toggles a label),
  molecule completed by symmetry (C1ⁱ with footnote), disorder (major part by default), H atoms and separate
  fragments can be hidden.
- X-Ray: bulky groups as **wireframe** (select the bond to the substituent, e.g. N–C_ipso; ring systems behind a
  spiro atom as well), switches **hide solvent** / **hide counterions** (recognised from the formula; a second
  independent molecule stays), labels for heteroatoms only, start view with the least overlap, and a **caption
  suggestion** that follows what is hidden or shown as wireframe (plus selected parameters and symmetry codes).
- Distances, angles and torsion angles **by clicking atoms**, with s.u. taken exactly from the CIF; values missing in
  the CIF (torsions without CONF) are calculated without s.u. and marked.
- SI tables: **crystal data and structure refinement** (one column per compound) and **selected parameters**; copy
  with formatting for Word, CSV and Excel.

### Fixed
- Self-test: wait for the structures loaded in the background instead of a fixed time (failed on slow machines).

## 1.18.1 – 2026-10-21

### Fixed
- macOS Intel: build and self-test with the older RDKit there (taking the compound from the MS report sets
  formula and molar mass; the substitute drawing needs a newer RDKit).

## 1.18.0 – 2026-10-21

### Added
- **Compound of the project** (name, ChemDraw, formula, molar mass) as default for all tabs (toolbar
  **Compound …**); tabs with their own structure keep it.
- New tab **IR + MS**: IR peak list from Bruker OPUS (file or PDF print-out, optional w/m/s/br) and the HRMS line
  from the Word report of the mass-spectrometry department, ready for the SI (copy with formatting for Word).
- HRMS: formula check against the ChemDraw object embedded in the report; the project compound can be taken from it.
- HRMS from **Bruker raw data** (`.d`, e.g. timsTOF) without Bruker software: line spectra read directly, ion averaged
  over the LC peak (automatic or chosen RT range) with number of scans and scatter.

## 1.17.0 – 2026-10-21

### Added
- CV: **reference per measurement** (own internal standard – also the Fc/Ac₂Fc couple in the same file – or own
  shift), e.g. for comparing solvents, each against its own standard; the couple windows follow each reference.
- CV: **group** per measurement (e.g. solvent) and **stacked** CVs with **E½ at every curve** next to its anodic
  peak (E¹½, E²½); y axis with numbers, without numbers or hidden.
- CV: plots against scan rate – **reversibility** (ΔE_p vs. v), **Randles–Ševčík** (i_pa and i_pc vs. √v with fit
  lines) and **trumpet plot** (E_pa/E_pc vs. log v, without k⁰ analysis), one series per group.
- CV: **E_pa/E_pc as numbers at the peaks** (e.g. sample and Ac₂Fc in one measurement), **structure per
  measurement**; the iR compensation of the Gamry file (e.g. positive feedback 800 Ω) is listed in the results CSV.
- Release notes on GitHub are generated from the changelogs.

### Changed
- Dragging inset, images, labels and legend is much smoother (only the dragged element is redrawn).

### Fixed
- CV: a window without a real redox couple (E_pa below E_pc) is flagged instead of giving a negative ΔE_p.

## 1.16.0 – 2026-10-21

### Changed
- **New name: Spectravolt** (formerly UVVisTool) – the program does much more than UV-Vis by now. Settings (recent
  projects, language, theme) and the data folder are taken over on the first start; projects open as before.
  Release packages are now called `Spectravolt-…`.

### Added
- Overlay: **SEC spectra** from the SEC tab, chosen by potential – as a **series** (all spectra or start and end,
  normalised with one common factor to the start spectrum, so intensity ratios and isosbestic points are kept) or as
  single spectra. SEC is never shown as ε (thin-layer cell).

## 1.15.1 – 2026-10-21

1.15.0 was tagged but not released (a self-test on Linux was too strict); its changes are included here.

### Changed
- Colours of the light and dark theme: darker, warmer greys and subtler borders.

### Fixed
- Self-test of the hover readout: tolerance follows the actual preview resolution.

## 1.15.0 – 2026-10-21 (not released)

### Changed
- **New look:** uniform style on Windows, macOS and Linux with a light and a dark theme; by default it follows the
  system, switch under **Format → Appearance**. The figures and exports are unchanged.
- All tabs: aligned forms, the left column is no longer cut off, **Export** stays visible at the bottom, and an
  empty tab shows a clear placeholder instead of a blank figure.
- ε tab: groups as cards; rarely used options (image sizes, min. points/R², shoulders, inset, formats) are
  collapsible and marked **"(changed)"** when they differ from the default.
- Toolbar (new/open/save project, undo/redo), icons in menus and list buttons.

## 1.14.0 – 2026-10-20

### Added
- EPR: **thermal decay at constant heating rate** – Arrhenius fit of E_a and A to the intensity vs. temperature
  (port of the group's MATLAB script); least squares with a reliable 95 % interval (default) or "as script".
- EPR: intensity by **Gaussian + line fitted to a feature**; field scaled to a reference frequency; temperature
  correction.

## 1.13.0 – 2026-10-20

### Added
- EPR: **several species** – simulations assigned to a measurement are scaled together (linear least squares),
  fractions by double integral, optional sum and residual.
- EPR: **own isotropic S = ½ simulation and fit** (g, hyperfine couplings of equivalent nuclei, linewidth,
  Lorentzian fraction; coarse grid search + Levenberg–Marquardt).
- EPR: **field calibration** with a fitted reference such as TEMPO (g_lit = 2.0055); the field correction is applied
  to all other measurements.
- EPR: **intensity vs. time or temperature** (double integral or peak-to-peak in a field window, optionally × T,
  normalised), e.g. for illumination kinetics and thermal decay; "Use this dark spectrum for all measurements".
- EPR: every measurement is exported as an **EasySpin-ready text file** (processed, full resolution, documented
  header); the intensity series as CSV.
- All figure tabs: export also writes **`…_data.csv` with the plotted curves**.

## 1.11.0 – 2026-10-20

### Added
- New **EPR tab** (CW EPR): Bruker BES3T (ESR5000/ESRStudio, Elexsys) and MS400 text files; subtraction of the dark
  spectrum recorded before irradiation; polynomial baseline, hidden field ranges, smoothing; EasySpin simulations
  (two-column text) scaled to a measurement, with the EasySpin parameter file (D, |E| in cm⁻¹); overlaid or stacked,
  mT or G, free labels; hover shows B, g and intensity.
- New **SEC tab** for spectroelectrochemistry: BWSpec spectral series + Gamry potential (assigned via clock time,
  adjustable offset); spectral series with highlighted first/last spectrum or potential gradient, difference spectra,
  coloured λ labels; A at λ vs. E with apparent Nernst fit; referencing as in the CV tab.

### Fixed
- Curve names starting with "_" were missing from legends.
- Reference electrodes with subscripts (Ag/AgNO₃) are typeset correctly in axis labels.

## 1.9.0 – 2026-10-20

### Added
- New **CV tab** for cyclic voltammetry: Gamry .DTA files, overlay of several measurements (scan-rate series
  with colour gradient, scan-direction arrow, E½ label), redox couples in editable windows (E_pa, E_pc, E½,
  ΔE_p, i_pa, i_pc, Nicholson peak ratio), Randles–Ševčík fit, referencing vs. Fc⁺/Fc (internal Fc/Ac₂Fc,
  manual), results as CSV.

### Fixed
- Automatic label placement now also works for curves whose x values are not monotonic (e.g. CVs).

## 1.8.0 – 2026-10-20

### Added
- ε tab: optional **predicted colour in solution** below the cuvette photo, calculated from the spectrum
  (transmission under daylight, CIE 1931 colorimetry → sRGB). Concentration and path length can be chosen
  (Beer–Lambert). Display only, not part of the figure.

## 1.7.0 – 2026-10-14

### Added
- Overlay: **triplet states** of TD-DFT calculations (formally spin-forbidden, f = 0) can be marked as
  dashed marks of fixed height ("Mark triplet states"); they do not contribute to the broadened curve.
  Read from ORCA 6 state labels, the ORCA 4/5 triplet block and Gaussian ("Triplet-A").
- Overlay: **combine** TD-DFT calculations – select two or more (Ctrl/Shift click) and press "Combine":
  the transitions are merged first and then broadened together. One weight per calculation (default 1 =
  sum; e.g. 0.7/0.3 for conformers). A warning appears if the calculations share identical states.

### Changed
- Overlay: normalisation is a checkbox ("Normalise"); off shows ε [10³ M⁻¹ cm⁻¹] as before.

## 1.6.0 – 2026-10-13

### Added
- **Hover readout:** moving the mouse over the spectra shows λ and the absorbance of the nearest data
  point (with its concentration) in the status bar and marks it in the preview (never in exports).
  In the overlay and fluorescence tabs the plotted value is shown (overlay: without stacking offset).
- **Picking bands:** double-click a data point in the ε tab to add its wavelength as a band;
  double-click again (±2 nm) to remove it.

## 1.5.2 – 2026-10-12

### Fixed
- The self-test (`--selftest`) no longer writes into the user's settings (recent projects, last
  folder, language); it uses its own settings file in the output folder.

## 1.5.1 – 2026-10-12

### Fixed
- macOS: the app shows its version in the Finder (was 0.0.0).

## 1.5.0 – 2026-10-11

### Added
- Overlay: **stacked** display as usual in papers – curves offset by a common spacing in list order;
  "Same stacking level as the curve above" (e.g. TD-DFT with its measurement).
- Overlay: **y axis** with numbers, without numbers and ticks (default when stacked) or hidden.
- Overlay: names **at the curves** instead of a legend; optional dashed zero line per level.
- Fluorescence: **Stokes shift** Δν̃ = 1/λabs − 1/λem in cm⁻¹ (rounded to 10 cm⁻¹) and nm below the
  data; optionally also at the emission label in the figure.
- Fluorescence: absorbance at λex with a warning above A = 0.1 (inner-filter effect – relevant if
  absorption and emission were measured on the same solution).

- Linux: additionally as **AppImage** (`UVVisTool-linux-x64.AppImage`, single file); the tar.gz stays.

### Changed
- Fluorescence: the absorption label reads λabs (consistent with λem).

## 1.4.0 – 2026-10-11

### Added
- Update check: on startup (at most once a day) the app asks GitHub whether a newer release exists
  and offers to open the release page, naming the right file for your system. Help → "Check for
  updates…" checks immediately; Help → "Check for updates on startup" switches the automatic check
  off. Only the public GitHub API is contacted; nothing is sent except the program version. Without
  an internet connection nothing happens.
- Release builds for Intel Macs (macOS 14 or newer): `UVVisTool-macos-x64.zip`.

## 1.3.0 – 2026-10-10

### Added
- New menu Format → "Fonts and frames…" (applies to all tabs, saved with the project):
  - Text font and symbol font are selectable (default Arial and Times New Roman).
  - Band labels: font size (default automatic), bold, italic and colour.
  - Optional closed frame around the plot (line on the top and right as well).
  - Optional rounded frame around the chemical structure; it moves with the structure, and the
    automatic placement keeps labels and inset clear of it.

### Changed
- Greek letters (λ, ε) are set in the symbol font by default – in the labels, the inset table,
  the overlay axis and λem in the fluorescence tab. This can be switched off in the Format dialog.

## 1.2.4 – 2026-10-08

### Added
- The minimum R² for showing a band in the figure is adjustable (Analysis → "min. R² for figure",
  default 0.98; 0 = show all bands with a fit). Bands below the threshold stay in the results table,
  CSV and Excel report; their R² cell is marked red with a tooltip. The value is saved with the project.

## 1.2.3 – 2026-10-06

### Fixed
- With several bands, two labels could end up exactly on top of each other: a newly added band label
  (e.g. after a cutoff change gave it enough fit points) was placed before the stored positions of
  the other labels were taken into account. Stored positions of labels, inset and images are now
  reserved first. Labels that already overlap in a saved project stay where they are – drag one away
  or use "Reset layout".

## 1.2.2 – 2026-10-06

### Changed
- The preview fills the available space in all tabs and grows with the window; it stays true to
  scale (only the display size changes, the exported figure is unchanged).

### Fixed
- Very small errors of ε were shown as "± 0" (e.g. 51 ± 0 for SE = 0.65); they are now rounded up
  ("51 ± 1").

## 1.2.1 – 2026-10-06

### Added
- **Overlay:** a structure per spectrum, optionally drawn in the curve colour (SVG/CDXML as vector
  graphics, PNG/PDF as image).

### Changed
- **TD-DFT normalisation:** curve and sticks now always share one scale factor (each stick = height of
  its own Gaussian, the curve is their sum). Reference "curve maximum = 1" (new default) or "strongest
  transition = 1"; alternatively sticks as oscillator strength f on a right axis. In 1.2.0, the
  sticks were scaled independently of the curve in "strongest stick = band maximum" mode.

### Fixed
- Structures (CDXML, SVG, PDF) were cropped too tightly: bonds running exactly vertically or
  horizontally at the edge (e.g. =CH₂, CH₃) were cut off in figures and exports.
- Structures were distorted when their aspect ratio or the axes size changed (e.g. f axis switched on);
  only the width is stored now, the height always follows the image. Existing projects are corrected
  automatically.
- Structures drawn from CDXML without an export had too thin lines and too small labels.
- Coloured structures had dark edges.

## 1.2.0 – 2026-10-06

### Added
- **Project folders:** choose or create a folder first; every loaded file is copied into it, the project
  is saved automatically (backup `project.uvvis.bak` on opening), and exports go directly to
  `exports/epsilon/<series>/`, `exports/overlay/`, `exports/fluorescence/`. File → New / Open / Recent
  projects / Save project copy / Show project folder. The program starts without a project.
- **Excel report** per series: parameters, all results incl. 95 % confidence interval, method with
  equations, spectra, and one sheet per band with the full regression as Excel formulas next to the
  tool's values, residuals and native charts.
- **Undo / Redo** (⌘Z / ⌘⇧Z, Ctrl+Z / Ctrl+Y) across all tabs.
- **Overlay:** line style and width, scale factor and vertical offset per spectrum, order (↑/↓),
  structure size in %, legend placed in free space.
- **TD-DFT sticks:** "strongest stick = band maximum" (default), "height of individual band", or
  oscillator strength f on a separate right axis.
- ORCA **spin–orbit coupling** spectra; "with SOC" / "without SOC" selectable per calculation.
- ε tab: regression inset can be switched off (in addition to its table).
- Fluorescence tab: size fields for structure and photos.
- "(sh)" marking of shoulders in the figure is optional (off by default); table and Excel report keep it.

### Changed
- Results CSV has an additional column `ci95` (95 % confidence interval of ε).
- Settings are no longer stored as `.uvvis.yaml` files next to the measurement files, and the overlay/
  fluorescence tabs are no longer restored automatically at start – use project folders instead.

### Fixed
- ORCA output with spin–orbit coupling was read incorrectly (state labels such as "0-1.0A" were taken
  as numbers, giving wrong energies and oscillator strengths). Please reload such calculations.

## 1.1.0 – 2026-10-05

**Please check:** concentrations entered with 1.0.0 via the concentration dialog may have been
saved in mM without anyone choosing that unit. Open the file and check **Concentrations…**.

### Added
- **Overlay tab:** several measured spectra and TD-DFT spectra (ORCA 4–6, Gaussian) in one figure,
  in individual colours; normalised to a band of interest (globally or per spectrum) or as
  ε [10³ M⁻¹ cm⁻¹]. TD-DFT: Gaussian broadening (FWHM, energy shift), optional sticks.
- **Fluorescence tab:** absorption and emission normalised in one figure, with λ/ε and λem labels,
  optional masking of scattered light, and a daylight/UV photo pair with arrow and excitation
  wavelength. Set-ups of both new tabs are kept between sessions and can be saved/loaded.
- Reading of Cary WinUV **.DSW/.BSW** files and Cary Eclipse **.FBSW** files (parser from parseuv,
  BSD-3-Clause) and of Cary Eclipse CSV exports; λex is taken from the metadata.
- **Several data files at once** (e.g. each concentration measured separately) form one data set,
  also via drag & drop.
- Structure drawing **unchanged from ChemDraw**: an SVG/PDF/PNG export with the same name next to
  the CDXML is used for the drawing, the CDXML for the molar mass.
- **Shoulders:** optional automatic search (marked "(sh)"); manually entered bands can be added to
  the automatically found ones.
- **Per band:** own fit cutoff (e.g. to include a point just above A = 1) and choice whether the
  band appears in the figure – both in the results table. Excluded points can be shown as open
  symbols in the inset.
- **File → Start over** discards all saved inputs for the current file.
- Missing molar mass for concentrations in mg/mL is highlighted in red; a note explains when the
  molar mass is not used (mM/µM).

### Changed
- ε (M⁻¹ cm⁻¹) is never displayed with decimals.
- R² appears in the inset legend only if the inset table is not shown (the table already lists it).
- The molecular formula shows isotopes (e.g. D for deuterium); the molar mass already included them.

### Fixed
- Concentration dialog: unit and start value are no longer pre-filled (previously mM and 1.0).
- Spectra without signal in the normalisation range are skipped with a note instead of being
  scaled up from noise.

## 1.0.0 – 2026-10-04

First release.

- Import of Cary multi-sample CSV exports. Concentrations from sample names or entered in a table
  (with dilution-series helper).
- Automatic baseline correction, band search, Beer–Lambert fits with ε ± standard error, R²
  and warnings.
- Figures in Origin style with inset (regressions, R²), structure (CDXML/SVG/PDF; molar mass
  from CDXML) and cuvette photo (HEIC/JPG/PNG, automatic background removal).
- Inset, images and labels can be moved with the mouse and resized with the scroll wheel or
  size fields. Selectable wavelength range.
- Export as PDF/SVG (structure as vector graphics) and PNG. Fixed size for Word
  (16 × 11 cm = two figures per A4 page).
- User interface in German and English. Apps for Windows, macOS and Linux.
