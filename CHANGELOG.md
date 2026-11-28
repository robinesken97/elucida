**English** | [Deutsch](CHANGELOG.de.md)

# Changelog

## 1.5.0 – 2026-11-28

### New

#### Comparison
- **Comparison complete:** new kinds **H-Cell** and **UV-Vis kinetics** (first-order fits as an option, off by default),
  **SEC** and **TD-DFT** in the spectra comparison, **HRMS** and **yield** as table values, several measurements of one compound.
- **Quick comparison** of loose files: drop area, kind read from the file, unrecognised files listed with the reason.

#### Figures and labels
- **Every fixed text in a figure is editable:** axis titles, secondary axes, legend, colour scale, inset heads and axes,
  table heads, in all tabs; in preview, export and Word SI. Card **Figure Labels** grouped and collapsible; **Own text**
  uses the text editor of the synthesis tab (bold, italic, sub-/superscript buttons, no syntax).
- **Own text in Figure Labels:** a typed `$` stays a `$`; sub- and superscripts stay upright, only text you made italic is
  italic; sub-/superscript also works on a single character; the field applies 0.6 s after the last change and on
  leaving it; the row list shows the text instead of markup; **Reset All** acts on the shown view only.
- **Figure Labels for own NMR spectra** (1D and 2D: axis titles, spectrum title; trace names keep their own field) in
  preview, SI and comparison; the energy profile lists its y axis.
- **Font sizes** for axis titles, tick numbers and legend (card Fonts and Lines, globally or **This Tab Only**; empty =
  automatic, derived from the figure size); in preview, export and Word SI.

#### CV
- **Electron count n per wave** against an internal one-electron standard (Fc, Ac2Fc) in the same voltammogram
  (ratio of forward peak currents, Randles–Ševčík); D and concentrations only as entered. **Coulometry** n = Q/(F·N).
  A reason instead of a number when n cannot be given; "apparent" for an irreversible standard wave; hint when n differs
  from the entered n. Card in step Evaluation, results table, `_electrons.csv`, workbook sheet, methods text.

#### TD-DFT and 3D views
- **NTO structures rotatable:** dragging turns hole and particle together; the own view is stored per state and used in
  export and SI. **Reset view** in NTO, NBO, ACID, 3D NICS and the EPR calculation.
- **3D views stay usable:** NTO, NBO, ACID, 3D NICS and EPR spin density compute their image in the background after
  a drag or **Reset view**; an outdated computation is cancelled. Export, SI and Word still wait for the full image.
- **3D views on the graphics card** (Format menu, on by default): orbital surfaces render on the GPU in the preview and
  stay at full resolution while dragging; export, SI, Word and thumbnails are computed as before and unchanged. After a
  failed graphics start the program uses the processor.
- **NTO:** the arrangement of hole and particle stays that of the automatic view while rotating; **Reset view** sits in
  the display card and is greyed out at the start view, as in NBO, ACID, 3D NICS and the EPR calculation.

### Changed
- **Quieter interface:** export tiles without blue (grey check mark, deselected tiles faded); chips with a grey area when
  on; selected table rows grey with a thin accent bar at the edge; step bar without number circle for a single step;
  quieter hints, stronger contrast for disabled controls; sentence case for English buttons; light theme with stronger
  control borders and flat disabled buttons; dashed frame for **New compound** and the quick-comparison drop area;
  NMR empty state.
- **TD-DFT tab** no longer jumps to the project page or shows the big comparison: a tab shows only what it compares or
  evaluates itself.
- **Example project** opened from the library is always built fresh and says so (changes are discarded); a failed build
  shows an error instead of staying at 96 %.
- **Dark canvas:** photos (cuvette photo, fluorescence photo pair) keep their original colours in the preview; axes, text,
  curves, structures and the arrow between the photos follow the dark canvas. Export and Word SI unchanged.
- **CV:** D, Q and N italic in the cards; the electron-count heading fits one line.
- **EPR:** species field with format buttons; X-Ray and DFT fields with tooltips (PXRD, IRC, NICS scan).
- **HRMS:** the label at the assigned peak shows the found value, like table and SI.
- **Word SI:** the colon after "Figure Sn" and "Table Sn" is never bold; *ε* italic in the UV-Vis line; "cm-1" never
  breaks at the line end; the footer names the part being written and the window repaints between parts.
- **Drawing:** the Actions list shows ions with their charge (C4H12N+, Cl-).
- **Export tab:** the four export buttons have the same width. **File menu:** the UV-Vis (ε) submenu appears only in the
  UV-Vis (ε) tab.

### Fixed
- **TD-DFT:** the own normalisation window of the selected spectrum can be set again; arrows and typed values no longer
  jump back to "auto"; without an own window the fields show "auto".
- **UV-Vis Excel report:** the A/d chart now shows its points and regression lines also in Protected View (it read
  formulas that Excel had not calculated yet, so all points sat at y = 0); the chart shows the state at export.
- **CV:** the scan direction arrow can be grabbed a little beside its line and tip, like a label.
- **NMR:** spectra from MNova SVG no longer lose the end labels of the ppm axis (10.0, 0.0); preview and Word use a copy
  with a margin, the file itself is unchanged.
- **ChemDraw paste** reads the clipboard as Octet itself does; when nothing on it can be read, a message says so.
- **Example project:** the first build stays on the start page until the project page opens (no jump); the cuvette
  photo has a natural white cap.
- Dark drawing canvas no longer flashes white while loading.
- Switching the language twice in a row no longer raises an error from the cluster view.
- Saving a file no longer fails on Windows when another program holds it for a moment (short retry).
- Tab **Other** opens with a project state that has no entries.
- **3D views at 100 % display scaling (Windows):** the image while rotating is drawn at full size again (dark canvas;
  it was half size in the top-left corner). After **Reset view**, ACID, 3D NICS and EPR spin density show a coarse image
  of the new view until the sharp one is ready, never the molecule and the surface in different rotations.

## 1.4.0 – 2026-11-22

### New

#### Figures and labels
- **Figure Labels in every tab with a figure** (UV-Vis, fluorescence, HRMS, IR, CV, SEC, H-Cell, EPR, TD-DFT, kinetics,
  comparison stacks): own text, hide and reset per label (card and right-click menu). **Own extra labels:** right-click an
  empty spot, **Add Label Here**; drag, hide, remove (**Remove Own Labels**). Never in captions or methods text.

#### Export and tables
- **Tables per tab:** one CSV format (comma, decimal point, UTF-8, headers "name [unit]", raw values), a workbook
  `<compound>_<Tab>_tables.xlsx` with the on-screen numbers as numeric cells, **Copy** on every result table (Word and Excel).
- **Export tab:** one card per figure and table; the selection drives **Images**, **Tables**, **PPTX** and **SI (Word)**
  from four equal buttons; **All**/**None**; disabled buttons say why. **Export All** writes tables too.
- **Example project** is built once per version: opening it again takes about 0.2 s instead of 19 s; the first build shows progress.

#### NMR
- **Comparison of own 1D spectra** (one nucleus, one solvent): **Single**, **Overlaid** or **Stacked**; exportable with a
  comparison subchapter in the SI. Caption with temperature range and a free sentence; withheld until phase and reference
  of every trace are confirmed.
- **Octet prediction lane** on click (view only, never in any output); auto range ¹H 9..0, ¹³C 200..0 widened by the signals.
- Example project: invented temperature series in S3.

#### HRMS
- **PDF reports:** Bruker SmartFormula layout read automatically (found from the report, calc always computed here, warning
  when the report's calc differs, instrument spectrum image selectable); header data (path, operator, sample) never taken over.
- **Unknown PDFs:** candidate list (line, ppm against calc), nothing preselected, taken over by a click; **text recognition
  (OCR)** for scans, also for IR peak values. Manual found field always available.
- **More adducts** (MeOH, MeCN, H2O, 2M, 2+, formate) and a free own ion.
- **Contaminants and Reagents:** hints for peaks matching known contaminants, reagents or fragments (5 ppm, adjustable);
  on screen only, never in SI or exports; **Own Contaminants** per computer.

#### CV
- **Reference by click:** column Fc, **Set Reference** snaps to the standard's peaks (Esc cancels); the standard's
  structure sits above its wave, in the reference colour or black.
- **D and k0 per couple** in their own table; k0 only from at least three scan rates, as a range from dEp, marked apparent
  without iR compensation; D only for reversible couples; new `<name>_rate_fits.csv`.
- Dropped `.DTA` files are routed by content: Gamry CV to CV, cyclic charge-discharge to H-Cell, Bruker BES3T to EPR.

#### Interface
- **Tab reset menu: Clear Tab (Data and Settings)** in every tab (one undo step, files stay in the folder; the compound keeps its name, its drawing file is never changed).
- **Format menu, Interface Size** 100/110/125/150 % per computer; **Restart Now** reopens the same compound and tab, or the project page.

#### Structures and salts
- **Counter-ions:** common abbreviations are resolved in labels and formulas (PF6, SbF6, AsF6, BF4, ClO4, OTf, NTf2,
  BArF, BPh4, OAc, NO3, HSO4, I3, SO4, N3); the charge is read from the label (a single-digit charge only on a monatomic
  ion such as Fe2+, "SO4 2-" with a space). Ambiguous labels such as SO42- and unbalanced charges get a hint instead of a guess.
- **HRMS, Ion of the Salt:** cation [M]+, anion [M]- or 2+/2-; default is the carbon-containing part, projects with an
  evaluated report keep the whole salt.
- **ChemDraw import:** rings pasted from ChemDraw keep their double bonds inside; a minus charge sits level with a plus.
- **Octet and own structure drawer:** double bonds in rings of any size (macrocycles too) go inside the ring; centred double-bond lines (e.g. C=O) run to the axis of the neighbouring bond.

### Changed
- **Light/dark switch** recolours the open window in place instead of rebuilding it, so it is faster.
- **Interface review:** tables, lists and trees with rounded corners like the fields; the tab bar tightens before it
  scrolls (fits at 1200 px); notices sit in the footer in one line (Details grows upward); result tables tighten cells,
  then use two-line headers before scrolling; empty non-input columns are hidden on screen (files keep them); HRMS raw
  data and isotopes as tables.
- Methods texts and captions typeset quantities in italics in Word and in the preview; IR/Raman peaks are integers everywhere.
- Consistent capitalisation of chips, placeholders, table headers, hints, drop-down items and cell values (symbols, units and abbreviations unchanged); synthesis column header "eq. / %"; MNova spelling.
- Export tiles: names on two lines, symbols scaled to the preview card; DFT multireference evaluation is a card in the left column; spacing on the details page; lone colour swatches.
- Left column equally wide in every tab; NMR acquisition parameters as a table; X-Ray/DFT atom labels keep apart;
  UV-Vis/CV label gaps grow with the label font size.
- IR: a PDF counts as an OPUS printout only by its layout; other PDFs offer their values as candidates.
- HRMS figure page: one sentence instead of the guide when a report or raw data has no spectrum.
- Two-wave guard in CV: a window holding two couples is flagged like an edge peak; suggested windows end halfway to the neighbour.
- Tables use less cell padding before they scroll sideways; no bold header on selection.
- Closing or creating a compound turns hidden tabs into placeholders instead of rebuilding them.
- CV: reference-only measurements leave the scan-rate analysis; scan arrow top left.
- Result pages: the UV-Vis results table sits on top with **Copy** in its title row; X-Ray tables stack in a narrow
  window; DFT energy tables share the name column; file lists are as high as their rows.
- Typography: "arb. u." for arbitrary units, thin spaces in n × nucleus, Fc⁰/⁺ written the same everywhere, -ize spelling
  in English texts; the Raman laser wavelength is shown as an integer.

### Fixed
- UV-Vis tab stayed empty after a light/dark switch.
- Octet: an empty drawing clears structure file, formula and mass instead of "no structure found".
- Reset All in the label card brought back the old text; IR tab lost the elemental analysis values (EA sentence missing in the SI).
- Window title bar above the screen edge at 150 % scaling (startup geometry clamped).
- MNova SVGs with "MS Shell Dlg 2" or no font family render with Arial in PDF and Word.
- Dark canvas colours: no whitish dark blues/greens; crash at quit from WebEngine pages; crash at exit from the clipboard.
- Distinct NBO captions and file names for two calculations; E1/2 mean consistent between figure and methods text.
- Left column keeps its scroll position after a rebuild even when the first render is slow.
- Crash when drawing structures RDKit cannot sanitize; importing files failed when the compound was opened through a symlink.
- Wide fonts (Windows): footer notice, NMR parameter column and typeset cells shorten cleanly.
- CV methods text was cut off in its card; 3D atom labels in the reaction path overlapped.

## 1.3.0 – 2026-11-17

### New

#### Export and SI
- **Export tab** (last tab, group "Output"): formats PDF, SVG, PNG and the new **PPTX** (one slide per figure) for all
  figures of a compound; column **SI** selects per figure what goes into the SI.
- **Project page, tab "Export":** complete SI (template, chapters, options, compounds) and datasets in one place.
- **Journal requirements:** card **Purity** in the Compound tab, **FID for Publication**, "Supplementary Figure"/"Figure S"
  labels with converted references, Data Availability Statement.
- **Copy Figure (SVG)** (Edit menu, Ctrl+Shift+C / ⌘⇧C) for the page shown on the right.
- **Fonts, lines and colours:** line width and axis lines belong to the text format (global or "This tab only"); fixed
  colour roles (SEC start/end, H-Cell, HRMS, EPR fits) can be chosen per figure.

#### NMR
- **Own spectra from Bruker raw data or MNova documents** (optional; the MNova SVG stays the default): processing,
  phase, baseline, referencing, integrals, insets, labels, 2D spectra; keys work without a click first.
- **MNova export through an installed MNova** (macOS and Windows; Windows not yet tested on a real installation).
- Single TopSpin files (fid, ser, acqus, 1r …) can be dropped like in MNova.
- **Checks:** nucleus count against the molecular formula; ¹³C signals at solvent or impurity shifts (Fulmer 2010);
  compound number and conditions on the spectrum; axis range check.

#### UV-Vis, photophysics, TD-DFT
- **UV-Vis titration** in the kinetics tab (equivalents per spectrum).
- **Fluorescence:** lifetime from decay curves (1–2 exponentials, IRF), photophysical properties, excitation spectrum.
- **TD-DFT:** table of excitations and natural transition orbitals (NTO).

#### IR, MS, elemental analysis
- Calculated against measured IR (ORCA/Gaussian frequencies); **Raman** spectra.
- Elemental analysis in duplicate with the 0.4 % check; HRMS judged at 5 ppm like the journals do.

#### CV
- Card **Measurement Conditions** with the setup text the journals ask for.
- Gamry pulse voltammetry files (DPV, square wave).

#### EPR
- Spin density and calculated hyperfine couplings from Gaussian 16 and ORCA 4–6.1, assignment to the experimental
  groups, **EasySpin start script**.
- Acquisition parameters and coupling unit in the caption; **spin counting** against a calibration.

#### X-Ray
- **Packing figure** with intermolecular contacts and symmetry codes.
- **Powder pattern (PXRD)** calculated from the CIF, optionally against a measurement.
- **Aromaticity (HOMA)**, also in the DFT tab.

#### DFT
- **3D NICS** and **ACID** (from AICD output).
- **NBO 7** analysis (charges, Wiberg indices, NRT resonance structures).
- **Energy table** with xyz coordinates as the journals require; atomic charges.

### Changed
- **"Reset display"** (was "Reset all to defaults") resets only the look of a figure, never data or numbers.
- The tab **"UV-Vis overlay" is now "TD-DFT"**; the tab bar says "TD-DFT" and "Kinetics".
- λ labels sit just above their band; the CV scan-direction arrow sits above the voltammogram.
- **Nothing switches by itself:** dropped files and data opened from another tab stay in the open tab, with a notice
  and a dot on the target tab.
- **One message after every export** (Export, SI, complete SI, data packages).
- **Reaction path** in the frame of the tabs (one tab row, actions beside it).
- **Faster:** switching compounds no longer rebuilds every tab opened before; smoother rotating of orbitals and surfaces.
- Units in table headers instead of cells; CV potentials and kinetics written like figure and methods text.
- Result pages without data are hidden.

### Fixed
- **Loading a preset deleted data** (calculations and analysis settings were carried along).
- **Compound names with a dot** ("S3.1") gave exports named "S3.pdf".
- **Reaction path:** profile shifted in PNG/PDF; a path closed before the profile went in stayed empty.
- **Stricter readers:** truncated or damaged files (ORCA/Gaussian, Gamry, BWSpec, Cary, EPR text, cube) are refused
  with a clear message instead of being read short or wrong; old projects with such a file still open.
- **Data package and moving folders:** new calculation and measurement files (IR calculation, EPR, ACID, NBO, Raman)
  were missing.
- **SI and Word:** DFT and EPR parts with or without measured spectra, figure deselection, references, captions.
- **Numbers:** no more "−0.000"; HRMS ppm, fluorescence and CV values rounded like the tables.
- Many details in EPR, X-Ray packing/PXRD, NMR, NTO/NICS/NBO and the interface (labels, greyed cards, dark theme).

## 1.1.0 – 2026-11-13

### New
- **New tabs:** H-Cell (charge–discharge cycling) and UV-Vis Kinetics.
- **Project page: Comparison** of several compounds (CV stack, UV-Vis overlay, property table; normalisation to a band).
- **X-Ray:** comparison with a calculated geometry.
- **EPR:** choice of baseline, isothermal decays and Arrhenius, joint fit of several S = ½ species, simulation below the
  measurement.
- **CV:** diffusion coefficient from the Randles–Ševčík slope.
- **Energy profile** with multireference levels (CASSCF, NEVPT2, SORCI); levels can be dragged.
- **SEC:** heatmap view; **Overlay:** SORCI spectra.
- Several structures in one figure share the same scale.

### Changed
- Fields with "auto" or "off" reset with one click.
- CV: baseline ends 0.20 V before the peak; current density uses the entered electrode area.
- Amount check allows only 0.01 % beyond rounding; crystal-data table in standard notation.
- Uniform tables and lists across all tabs; Octet Draw 1.1.2.

### Fixed
- EPR: field unit of text files no longer guessed; missing nuclei added; captions, ramps and g after calibration.
- Consistent atomic weights (IUPAC 2021) and rounding half up everywhere, also in the Excel report.
- Minimum window width, Word page layout and several layout details.

## 1.0.0 – 2026-11-11

First stable version.

### What Elucida does
- **One compound, all data:** tabs in the order of the SI – Compound (name, formula, drawing), Synthesis (scheme,
  procedure, amount check), NMR (MNova), IR + EA, HRMS, UV-Vis (ε from dilution series), UV-Vis overlay with TD-DFT,
  Fluorescence, CV, SEC, EPR, X-ray (CIF), DFT (geometries, orbitals, energy profile, NICS, multireference) and
  external figures.
- **Publication-ready figures:** PDF, SVG and PNG at a fixed size, with structure, labels and caption; the preview is
  true to scale.
- **SI at the push of a button:** Word section per compound and a complete SI for the whole project, methods texts of
  the analyses, data packages for the repository.
- **Projects:** overview with a checklist per compound, search, reaction paths across compounds, connection to the
  compute cluster.
- **Drawing inside the program** with Octet Draw; ChemDraw files are taken over unchanged.
- German and English, light and dark design, Windows, macOS and Linux.
