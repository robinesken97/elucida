**English** | [Deutsch](manual.de.md) · [Overview](../README.md)

# Elucida manual

## Download and start

Download the file for your system from **Releases** (right-hand side of the repository page) and unzip it.

| System | File | Start |
|---|---|---|
| Windows | `Elucida-windows-x64.zip` | `Elucida\Elucida.exe` |
| macOS (Apple Silicon) | `Elucida-macos-arm64.zip` | `Elucida.app` |
| macOS (Intel, macOS 14 or newer) | `Elucida-macos-x64.zip` | `Elucida.app` |
| Linux (AppImage) | `Elucida-linux-x64.AppImage` | make executable, then double-click |
| Linux (folder) | `Elucida-linux-x64.tar.gz` | `Elucida/Elucida` |

The app is not code-signed, so the operating system will warn you on first launch:

- **Windows (SmartScreen):** "More info" → "Run anyway".
- **macOS (Gatekeeper):** drag `Elucida.app` to Applications and double-click it once (it gets blocked).
  Then System Settings → Privacy & Security → at the bottom "Open Anyway" → confirm with password/Touch ID.
  Since macOS 15 the old "right-click → Open" route no longer works. Alternatively in Terminal:
  `xattr -dr com.apple.quarantine /Applications/Elucida.app`. Not sure which Mac you have? Apple menu → About This Mac: "Chip Apple M…" = Apple Silicon,
  "Processor Intel…" = Intel. The Intel version needs macOS 14 (Sonoma) or newer.

**Updates:** on startup the app checks once a day whether a newer version is on GitHub and offers to
open the release page (Help → "Check for updates…"; can be switched off in the Help menu). To update,
download the new file and replace the old app; compounds, projects and settings are kept.

**Linux AppImage:** `chmod +x Elucida-linux-x64.AppImage` (or file properties → "Allow executing"),
then start it. It needs `fusermount` (package `fuse3`, preinstalled on most current distributions);
without it, start with `./Elucida-linux-x64.AppImage --appimage-extract-and-run`. Requires a
distribution at least as new as Ubuntu 22.04 (glibc 2.35), as does the tar.gz.

On Windows, always keep the whole `Elucida` folder together. The `.exe` does not work without the `_internal` folder next to it.

*Elucida was called **Spectravolt** before (and **UVVisTool** before that, when it only evaluated UV-Vis dilution
series). Compounds, settings and downloaded data are taken over automatically. Versions before 1.0 (numbered up to
2.7.1) do not offer 1.0 as an update: download it once by hand.*

## Quick start: from an empty compound to the SI

Elucida has two levels: a **compound** is a folder with all data of one compound, a **project** groups the compounds of
a paper (complete SI, dataset; see the next quick start). Every compound belongs to a project: it lives in the
project folder.

1. **Create a compound:** **New → New compound** on the welcome page (or **File → New compound…**) first asks for the project
   (a recent one, another one or a new one), then for the name; inside a project **New compound** on its page. All
   files you load are copied into it; it is saved automatically.
2. **Set the compound:** the **Compound** tab on the far left (a new compound opens there): the number it carries in
   the SI (e.g. 3a) and the structure – draw it on the right or load a ChemDraw file (CDXML) with **Choose…**. Formula
   and molar mass are taken from it, and everything applies at once (no OK). All tabs and the SI follow this compound;
   number and formula are shown on the tab. Prefer drawing in ChemDraw? Menu **…** above the drawing → **Edit in
   ChemDraw** opens the empty file that every compound already has – save, and Elucida takes over the structure with
   formula and molar mass by itself (the same for the reaction scheme in the synthesis tab).
3. **Load data:** simply drag files into the window – Elucida puts them into the right tab: CIF → **X-Ray**, SVG from
   MestReNova → **NMR**, xyz/ORCA/Gaussian/Molden/cube → **DFT**, MS report (.docx) or Bruker .d → **HRMS**, OPUS file →
   **IR + EA**, UV-Vis measurement data (CSV, DSW/BSW) → **UV-Vis (ε)**. For CV, SEC, EPR, overlay and fluorescence use
   **Add files…** in the tab. An empty tab shows what it needs and where it comes from.
4. **Evaluate:** settings on the left in steps (usually **Data · Evaluation · Display**; a dot on a step shows where
   something differs from the default), the figure on the right with the **Results** and **SI Text** tabs. Labels, structures and insets can be dragged with the mouse.
   **Ctrl+Z** / **⌘Z** undoes everything.
5. **Export:** **Export** at the bottom of the tab writes the figure (PDF/SVG/PNG, 16 × 11 cm for half an A4 page) and
   the data into the compound folder (`figures/`, `tables/`, `SI/`).
6. **Create the SI:** **SI (Word)** in the toolbar collects everything that is ready in one Word file: synthesis,
   characterisation paragraph (m.p., NMR, IR, HR-MS, UV-Vis, elemental analysis), figures two per page, crystal data
   and DFT coordinates. Afterwards the program lists what is still missing.

## Quick start: a project with several compounds

1. **Create a project:** **New → New project** on the welcome page (or **File → New project…**) and choose a
   folder – empty, or one that already contains compounds (they are added automatically).
2. **Fill in the details:** page **Details** (next to Compounds and Computational chemistry; each field applies when you leave it) – title of the paper (title page of the SI; italics with `<i>…</i>`), authors,
   affiliation, DOI of the dataset, related publication, descriptions, license. They end up in `README.txt` of the
   dataset and on the title page.
3. **Add compounds:** **New compound** creates a subfolder (name = compound, e.g. `3b`); click a
   compound to open it and work as in the quick start above. The path at the top in the toolbar,
   **Overview › <project> › <compound> ▾**, leads back to the project or the overview and switches directly to another
   compound of the project (also File → Back to project, Ctrl+Shift+P; File → Back to overview, Ctrl+Shift+H).
   **New group …** organises the compounds (e.g. precursors, salts, NHOs; right-click a compound → Group, or drag it
   into a group); in the complete SI the groups become sub-chapters of synthesis and NMR (2.1, 2.2 …).
   Drag the rows or use **Sort by name** to change the order – it is the order in the SI and in the dataset. The
   search field at the top of the welcome page finds compounds in all your projects (name/number, lab code such as
   AB-1-234, formula, note); Ctrl+F jumps there. Each compound shows a **checklist**: ¹H, ¹³C, 2D NMR, HRMS, IR and
   m.p. are required; for compounds marked **known from the literature** in the Compound tab (with the reference)
   only ¹H and ¹³C. **Oil** next to the melting point gives "m.p. <25 °C".
4. **SI texts:** **SI texts …** – "Materials and Methods" (or insert the setup texts stored in the tabs) and an
   optional introduction for each chapter.
5. **Complete SI:** **Complete SI (Word) …** – choose chapters, compounds and template (group, Wiley, ACS, RSC, Nature);
   the Word file lands in `SI/` of the project.
6. **Dataset:** **Data packages (zip) …** – one zip per compound, `CompChem.zip`, `README.txt` and license text in
   `datapack/`, ready for the upload (e.g. TUDOdata).

To try it: **Help → Open example project** creates a project with two invented compounds: a precursor with the usual characterisation and its product with matching data for all tabs.

## Guides

Step by step through one workflow, with pictures:

- [Synthesis and characterisation to the SI](anleitungen/synthese-bis-si.en.md) – scheme, procedure, NMR, IR,
  HRMS, elemental analysis, SI section
- [UV-Vis: ε from a dilution series](anleitungen/uvvis-epsilon.en.md)
- [Electrochemistry: CV, SEC and H-cell](anleitungen/elektrochemie.en.md)
- [EPR: spectra, simulation and fit](anleitungen/epr.en.md)
- [Crystal structure and DFT](anleitungen/struktur-dft.en.md)

To try it without your own data: **Help → Open example compound** creates a compound with artificial data for all tabs.
**Help → Guide for this tab** (F1) opens the matching section below.

All settings of the individual tabs are described further down for reference.

## Compounds, projects, export

Everything happens in the **compound folder** (the folder button in the toolbar opens it in Finder, Explorer or the file
manager of your Linux desktop):

1. **File → New compound…** – choose the project, then the name; the compound becomes a subfolder of the project.
   For a single evaluation without a project: **New → Quick evaluation** on the start screen (internal project "Quick
   evaluations", exports ask for the target folder; move it later).
2. Load measurements, structures, photos and TD-DFT files from anywhere – they are **copied into the
   compound** (`data/<technique>/`, `structures/`; ChemDraw exports with the same name as a CDXML come along).
   Files that are already inside the compound are not copied again.
3. Work as usual – the compound is **saved automatically**. A backup (`.elucida/project.elucida.bak`) is made
   each time it is opened. Folders from older versions (`project.uvvis`) open as before and are saved as
   `project.elucida` from then on (the file name keeps "project" for compatibility).
4. **Export** writes directly into the compound folder (existing files are overwritten):

```
S2/
  project.elucida        settings (paths relative to the folder)
  SI/                    Word files and SI texts: S2_SI.docx, S2_NMR.docx, S2_UV-Vis_methods.txt …
  figures/               figures (PDF/SVG/PNG): S2_CV.pdf, S2_X-ray.svg, <series>_UV-Vis.png …
  tables/                tables and data files: S2_CV_results.csv, <series>_UV-Vis_report.xlsx, xyz …
  data/nmr/ data/cv/ …   copies of the measurement data, one folder per technique
  structures/            ChemDraw structures (with their exports), schemes, photos
  .elucida/              intermediate images for Word, cache, backup (hidden)
```

File names start with the name of the compound (**Compound** tab; without one, the folder name). Folders appear only when
something goes into them. Folders from versions before 2.1 (`data/`, `images/`, `exports/`) open as before; their
files stay where they are, new files and exports use the new layout.

The program starts with the welcome page. Open compounds and projects via **File → Open**, **Recently opened**
or by dragging the folder onto the window. **File → Save compound copy** writes a complete copy (e.g.
an intermediate state). **Edit → Undo / Redo** (⌘Z / ⌘⇧Z, Ctrl+Z / Ctrl+Y) covers all tabs.

**Start screen:** on the left are the filters (All compounds, Recent, Incomplete, Sample left) and your projects with their progress;
on the right the compounds as a **Gallery** or **List**. The gallery says which required parts are missing; the list and the project
page show them as a table. Tabs that hold data are bright, empty ones dimmed.

**File → Export data package (zip)** writes the raw data of the compound for a data repository (e.g. TUDOdata), laid
out like published datasets: `3b.zip` with `3b/NMR/1H/10/` (complete TopSpin experiments), `NMR/HSQC + HMBC/12/`,
`IR/`, `MS/` (report, Bruker .d), `UV-Vis/`, `Fluorescence/`, `CV/<solvent>/`, `SEC/`, `EPR/`; DFT and Elucida's own
figures/SI optional. X-ray (CCDC) and synthesis are not included. Every file can be deselected; the choice is
remembered per compound. **Lab codes** such as `AB-1-234` are found automatically and replaced – in file and folder
names by the compound (`3b`), in the contents by „Compound 3b“ (both editable) – and **dates and times are deleted**:
in all text files (CSV, Gamry DTA, EPR, TopSpin parameters, title and audit trail), in the MS report (text, file
author and dates, labels in its spectra) and in OPUS files (same length). The measured values (FID, ser, spectra) stay
byte-identical. PDF, Mnova and Bruker .d cannot be edited; if a code remains in one of them, the log names it.

Every export from the Overlay, UV-Vis Kinetics, Fluorescence, CV, SEC and EPR tabs also writes `…_data.csv` with exactly the
plotted curves (one x/y column pair per curve, values without stacking offset) – for Origin, Excel or MATLAB.

### Projects

<p align="center"><img src="screenshots/project_dark_en.png" alt="Project page with the compounds and their checklists" width="800"></p>

**File → New project** turns a folder into a project: the parent folder for all compounds of a paper. The compounds
stay ordinary compound folders in its subfolders (each can still be opened on its own); `publication.elucida` keeps
their order, the details for the dataset and the SI texts. The project page lists the compounds with a checklist
(drag rows to reorder, **Sort by name**, right-click: move, copy, remove), **New compound** creates a subfolder, **Add compound** moves or copies one from
elsewhere into the project.

- **Move or duplicate:** right-click on a compound (project page or overview) or the menu of the compound in the path
  at the top → **Move to another project …** moves the folder; **Copy to another project …** makes an independent copy,
  e.g. when the same compound appears in two papers. Compounds from older versions without a project are offered for
  assignment when they are opened (path: "⚠ no project").
- **Search:** the field at the top of the welcome page searches all compounds of all known projects by name/number,
  lab code (e.g. AB-1-234, also from file names and procedures), formula, note, reference or project; on the project page
  the same field filters the compounds; Ctrl+F jumps there.
- **Move to trash …** (right-click in the overview) removes a compound or a whole project after a question with the
  number of files and the size; it can be restored from the trash.

<p align="center"><img src="screenshots/paths_dark_en.png" alt="Reaction path with the free canvas" width="80%"></p>

- **Computational Chemistry (reaction paths):** a tab of the project for energy profiles and IRCs across several
  compounds, without touching them: calculations are copied in. **Design** is a free canvas (Octet) for profiles,
  molecules, text and 3D/orbital views; **Calculation data** is the energy diagram with its column in three steps (see below); **3D / Orbitals** the views. Paths appear
  as cards (right-click to rename or remove). All of it stays in the main window; with a path open, the ☰ button shows or hides the path list. Profiles are true to scale by default; a schematic
  layout must be chosen explicitly and then says so in the figure and SI. Energies are never edited, and a stale diagram
  stops the export until **Update diagrams**. The complete SI includes the whole composition.
  **Energy diagram** (Calculation data tab; steps on the left, the diagram on the right follows every change at once):
  **Data** – the calculations as levels (label, step, path), single points, IRC curves; the fields below the table
  change the selected level: **Position** (horizontal, in steps, e.g. so that labels or vertical transitions do not
  collide), **Width** and **Colour**, in the schematic diagram also **Height** and "Break connector"; **Automatic
  level** restores the position at its step, the default width and the path colour. The energy never changes. **Path** – the levels are nodes:
  drag from the end of a plateau onto another one in the figure to connect them, which allows branches and merges; without
  own connectors the old rule applies (per path letter in the order of the steps, **From step and path** restores it).
  The table lists the connectors; the fields below it change the selected one: line (dashed, solid, dotted, curved, wavy,
  none), arrowhead and a text such as "ISC", "IC" or "hν" as in a Jablonski diagram; the colour sits in the table. Levels
  on top of each other get a vertical transition inside the column that attaches at the side of the lines, beside the
  labels, several next to each other; the line of a level in between is interrupted where the transition passes. The text
  of a connector stands beside its line, never on a stroke or another label. **Display** – four presets
  (Classic, Curves, Colour, Minimal) set the style in one go; below them line style, widths, font size, frame, to scale
  and colour per path. The style belongs to the diagram of the path. Energies, names and connector texts can be dragged in
  the figure (when two levels are close); **Reset labels** puts them back. The energies themselves never change.
- **Data packages (zip):** the whole dataset as on TUDOdata – one zip per compound (as above), the DFT calculations of
  all compounds in `CompChem.zip`, `README.txt` (title, authors, DOI, citation, related publication, descriptions,
  license; generated from **Details**) and the license text (CC BY 4.0 or CC0). Lab codes are assigned to the compound
  whose file names contain them.
- **Complete SI (Word):** one file with title page and table of contents, chapters as in the group's SI – 1. Materials
  and Methods, 2. Synthetic Procedures and Characterization Data, 3. NMR Spectra, 4. UV-Vis Spectroscopy, 5. EPR
  Spectroscopy, 6. Cyclic Voltammetry, 7. Spectroelectrochemistry, 8. X-Ray Characterization Data, 9. Computational
  Section (empty chapters are left out). Within each chapter the compounds follow the order of the project;
  figures two per page and numbered throughout, crystal data of all structures in common tables. **SI texts** holds
  "Materials and Methods" and an optional introduction per chapter.
- **Templates** for the complete SI: group (as the group's Angewandte SI: "Supplementary Materials for",
  Figure S1:), Wiley ("Supporting Information for", Figure S1.; Angewandte requires the SI to start with a table of
  contents), ACS ("Supporting Information for", Figure S1., pages S1, S2 …; JOC asks for a table of contents with page
  numbers), RSC ("Supplementary Information for", Fig. S1 as in RSC articles), Nature ("Supplementary Information
  for", Supplementary Figure 1 |, numbered separately from the article). Publishers hardly prescribe a layout for the
  SI, so only the title page, labels and page numbers change; chapters, font and page layout stay as in the group's
  SI. The complete SI has page numbers and a table of contents that is already filled in (estimated page numbers;
  Word updates them when opening, ONLYOFFICE via "Update table of contents"). The SI of a single compound keeps the
  group's style.

## Compound

A compound folder usually stands for **one compound** (or one comparison). The **Compound** tab is the first in the tab row
and carries its number (the one used in the SI, otherwise the lab notebook no.) and formula. On the left are the name, formula, molar mass and the
details for the SI, on the right the drawing. There is no OK and no Cancel: a field applies as soon as you leave it, the
drawing saves itself, and undo takes every change back. Formula and molar mass follow the drawing (isotopes such as D
included) unless you changed them by hand; a cleared field takes the drawn value again. **Choose…** loads an existing
ChemDraw or image file instead. The formula shows subscript digits already in the field. If the drawing contains more
than one molecule and is not a salt, a hint below says so: formula and molar mass then refer to all of them together. The
sample number can always be entered, also without "Sample left". This is
what the ε tab (structure, molar mass), the fluorescence tab, IR + EA and HRMS always follow: changing the compound also
replaces values entered there; a replaced molar mass is shown as a message and undo restores it. Nothing is entered for this in
the UV-Vis tab any more: the **Compound** card shows formula and molar mass, **Edit …** opens the compound, **Structure in
figure** hides the structure for one series. The name appears in the window title. The melting point entered there starts the
characterisation paragraph of the SI section. The molar mass is kept with two decimals everywhere. The **Lab notebook
no.** sits next to the number used in the SI: it is shown in the overview and found by the search, but never appears in
the SI, Word or the data package.

**Edit in ChemDraw:** every compound folder already contains empty ChemDraw files for the structure and the reaction
scheme (`structures/<name>.cdxml`, `…_scheme.cdxml`, document settings ACS 1996). **Edit in ChemDraw** (menu **…** above the
drawing in the Compound tab and the synthesis tab) opens the file in ChemDraw; as soon as you save there, Elucida takes over the structure (formula, molar
mass, pictures) or the scheme by itself.

## SI section (Word)

**SI (Word)** in the toolbar (or **File → Export SI section (Word) …**) exports right away with the selection of the
card **SI Export (Word)** in the **Compound** tab: parts as chips (characterisation, NMR spectra, figures, methods,
crystal structure, DFT), below them the figures per tab with data and the font; the selection is remembered and applies
to all compounds. Selected parts without data are left out (note at the bottom right). The export collects everything that is ready for the compound into
`SI/<compound>_SI.docx`, in the style of the SI: one characterisation paragraph **m.p. …; IR …; HR-MS …;
UV-Vis …; Elemental analysis …** (melting point from the **Compound** tab, UV-Vis line from the **SI line** page of the
UV-Vis (ε) tab: *λ*_max: 350 nm (*ε* = 12000 cm⁻¹ M⁻¹), … with bands as in the figure, ascending, ε as an integer), followed by the crystal-data table, the selected parameters and the captions of the
X-Ray tab and the DFT calculations (two columns). Parts that are still missing are listed after the export. Numbers
and units are joined by non-breaking spaces, so Word never separates "298 nm" or "ε = 8440".

**Figures:** the figures of all tabs with data (UV-Vis (ε) per series, IR, HR-MS, overlay, UV-Vis kinetics, fluorescence, CV, SEC, EPR)
and the NMR spectra always come **two per page**; where figure and caption would not fit, both figures of the page are
scaled down (aspect ratio kept). Captions follow the SI: UV-Vis "UV-Vis spectra of **X** in THF, measured in 0.1 cm
quartz cuvettes." (solvent under Analysis in the ε tab); CV, SEC and EPR take scan rate, iR compensation, reference,
potential range, band, g and couplings from the data and concentration, solvent, electrolyte or species from the
fields on the **SI Text** tab (formulas show subscript digits already in the field; the texts are justified and typeset as
in print). **Copy** sits at the top right of every card on its title line, also for the NMR, IR, EA and HRMS lines.
**Setup text (SI) …** next to "Copy" of the methods text stores your general
instrument/setup paragraph on this computer only (not in the compound, not in the repository); it is placed before the
figures of that tab. Word files open in normal mode (Word 2013+).

**SI text on the fits:** every tab that fits something (UV-Vis (ε), CV, SEC, EPR) has a **Copy** in the Methods Text card (SI Text tab) button: an
English methods paragraph describing exactly the evaluation steps used, with their settings (e.g. ε: baseline window,
OLS model, cut-off, SE/95% CI; EPR: baseline polynomial, field calibration, S = 1/2 fit, kinetics), to append to the
setup paragraph of the matching SI section, followed by the results. The same text is written as `…_methods.txt` on
export, and **SI (Word)** can add all of them as a section "Data processing and fitting" (one paragraph per technique)
behind the figures – so it is documented how the raw data were processed.

**Font of the Word exports:** selectable in the card **SI Export (Word)** of the Compound tab (default Arial as in the group's SI) and used for all
Word exports. The size stays 11 pt, because "two figures per page" is calculated with this line height.

## Synthesis tab

"Synthesis of **Name**" (the compound's name from the Compound tab, otherwise the folder; names are assigned only there), the reaction scheme and the procedure, exported
to Word or as part of the SI section.

- **Built-in drawing editor (Octet Draw):** the scheme is drawn right in the tab; changes are saved automatically after
  a second and earlier versions stay in `structures/.editor-backups/`. Structure check, clean-up and name-to-structure
  work offline; ChemDraw shortcuts and copy/paste stay available, file actions sit in the ⋯ menu. Labels such as
  `NaBH4 (1.5 eq.)` or `Pd(PPh3)4 (5 mol%)` count as equivalents, explicit amounts win. **Take from Octet table** copies
  the editor's stoichiometry table into the reagent table on request (no live sync; identical formulas are matched by
  column only, so check them). Only the **topmost reaction with its conditions** goes into the SI, in the preview as well
  as in the embedded CDX; the full drawing stays in the project. Word exports also write `<name>_structures/` with
  CDX/CDXML snapshots to open in ChemDraw on any system (double-click editing inside Word is a Windows feature of
  ChemDraw). The Compound tab has the same editor: the drawing saves itself, formula and mass follow it unless you
  corrected them by hand.
- **Scheme:** **Edit in ChemDraw** opens the empty scheme file of the compound (saving is taken over automatically), or
  choose an existing CDXML. Next to it (same name, same folder) you can save from ChemDraw: **SVG/PDF** (picture
  taken unchanged), **.cdx** (the scheme becomes an editable ChemDraw object in Word – double-click opens ChemDraw; Word
  cannot do this with a CDXML) and **.emf** (sharp vector preview of that object). Without an SVG/PDF the scheme is drawn
  from the CDXML coordinates, including arrow and conditions.
- **Procedure** with bold, italic, sub- and superscript. **GP ▾** chooses a general procedure of the project
  ("according to **GP A**"); in the full SI it appears once before the first compound that uses it.
- Amounts may carry a unit in the cell ("1.03 g", "150 µL", "800 mM"), n can be entered; with a ChemDraw reagent
  table in the scheme, **From scheme** takes its values.
- **Amount check:** amounts written as "(1.03 g, 5.00 mmol, 1.0 eq.)", "(99%)" are compared with the reagent table
  (M or formula, mass, volume, concentration, density); deviations beyond the rounding of the given digits are flagged.
  **From scheme** fills the table with the reactants (first = reference 1.0 eq.), reagents above/below the arrow (e.g.
  K2CO3), solvents and the product; **Insert amounts** inserts the calculated bracket of the selected row at the cursor.

## NMR tab

- **Spectra:** SVG exports from MestReNova (drag and drop). The nucleus is read from the axis label ("δ ¹H (ppm)");
  if it is missing, enter it. Order: ¹H, ¹³C, other nuclei by mass number, then 2D (COSY, HSQC, HMBC, NOESY …).
- **Structure** in every spectrum as vector graphics: placed automatically in a free spot (nothing covered), or top
  left/centre/right, or dragged in the preview; the mouse wheel over the structure changes its size, the same for all
  spectra.
- **NMR line:** paste the Mnova multiplet report ("Multiplets → Copy", journal format) – all nuclei into the one
  field, one line per nucleus. **Line from peak labels** builds the ¹³C (or other) line from the labelled peaks of the
  selected spectrum; a solvent signal labelled with its name ("77.16 CDCl3") is dropped. Assignments per signal in the
  table (*italic*, _{sub}, ^{sup}).
- **Temperature** 298 K by default, or from the Bruker experiment folder (acqus, with an overview of the parameters
  such as frequency, O1P, pulse program, scans).
- **Raw data** (tab next to the figure): **TopSpin data …** takes an experiment, a dataset (10, 11, …) or a folder with
  several datasets – also by drag & drop – and copies each experiment completely into the compound, sorted by kind
  (`data/nmr/1H`, `13C`, `DEPT135`, `HSQC` …). If exactly one experiment fits a spectrum, it is assigned automatically
  (parameters, temperature).
- **Mnova documents** (`.mnova`): card at the top of the left column – store them (kept in `data/nmr/mnova`) and
  open them in Mnova.
- Spectra can also be **EMF** from Mnova: they go into Word unchanged (vector, without the inserted structure); for the
  preview and the structure use SVG.
- **Word:** two spectra per page, "Figure Sn: ¹H NMR (500 MHz, CDCl₃, 298 K) of **Name**."

## IR + EA tab

- **IR:** load a Bruker **OPUS** file (`*.0`, spectrum) and/or the **OPUS PDF** print-out (peak labels). With the PDF the
  values are exactly the OPUS peak list; with the file alone Elucida picks the bands itself (adjustable
  sensitivity). Range freely selectable (default: the whole measured range); untick bands that should not be listed;
  intensities w/m/s/br optional (relative to the strongest band: s from 60 %, m from 30 %, otherwise w; br from a
  full width at half maximum of 120 cm⁻¹). Output: **IR** [cm⁻¹]: ṽ = 2961, 2866, … (integers, descending).
  **Correct baseline (as in OPUS)** subtracts the baseline like OPUS (figure and peak search only); **Set threshold**:
  click points into the figure, peaks beyond the line. With only the OPUS PDF the spectrum is read from the PDF.
- **HRMS:** load the **Word report** of the mass-spectrometry department; formula, ionisation, polarity and the measured
  m/z (from the embedded spectra) are read out. The formula comes from the compound (warning if the report
  says something else), the ion is selectable ([M+H]⁺, [M+Na]⁺, [M]⁺, [M−H]⁻ …), and the closest measured m/z is
  preselected. calc. includes the electron mass; four decimals: **HR-MS-ESI(+)** calc. C₁₈H₁₉N₂O⁺ [M+H]⁺ 279.1492;
  found 279.1496. The deviation in ppm is shown for checking (found − calc). The formula is checked against the
  **ChemDraw object embedded in the report**; without a compound set, **Take the compound from the MS report**
  sets name, formula and molar mass from it (the drawing is then an RDKit substitute – use your own CDXML for figures).
- **HRMS from raw data:** alternatively (or in addition) load the Bruker **measurement folder** (`.d`, e.g. timsTOF;
  button or drag & drop). Elucida reads the instrument's line spectra itself (no Bruker software needed, also on
  macOS) and averages the ion over the **LC peak** (automatic: contiguous scans with ≥ 50 % of the maximum, or a
  chosen RT range). found = intensity-weighted mean; the number of scans, the range of the single scans and their
  scatter (± mDa/ppm) are shown, because single scans can differ in the 4th decimal. With a report loaded its value
  stays preselected and the raw-data mean is selectable. Only `analysis.baf` and `analysis.sqlite` are copied into the
  compound.
- **Elemental analysis:** formula from the compound, optionally plus a solvate (`0.5 CH2Cl2`, several
  separated by commas); calculated values with conventional mean atomic masses, enter the found C/H/N/S values.
  Deviations above 0.4 % are flagged (the usual limit of the journals). Output, built like the HR-MS line: **Elemental analysis**
  (%) calc. C₁₈H₁₈N₂O: C 77.67, H 6.52, N 10.06; found C 77.41, H 6.59, N 9.87. The elemental analysis is always
  optional (not reported as missing).
- **Copy to clipboard** keeps bold, sub- and superscripts when pasting into Word. Export writes the spectrum figure
  and `…_SI.txt` with all lines.

## HRMS tab

- Load the **Word report** of the mass-spectrometry department and/or the Bruker **measurement folder** (`.d`); see
  the bullet points below for what is read from each. With raw data the tab shows:
  - a **chromatogram** (total ion current grey, ion current of the target ion red, ± 10 ppm); the blue band is the
    LC range used for the spectrum – **drag with the mouse** to choose another range;
  - the **averaged spectrum** over this range (mean of the instrument's line spectra) with m/z at the largest peaks
    and the **calculated isotope pattern** of the ion mirrored below (red; fine structure that the TOF does not
    resolve, e.g. ¹³C/¹⁵N, merged); the measured/calculated isotope ratios (M+1, M+2 …) are listed;
  - **click a peak** to use it as *found* (besides the report value and the LC-peak mean).
- Export: spectrum figure (PDF/SVG/PNG), `…_sticks.csv` (measured and calculated) and `…_SI.txt`.
- Older compounds: the MS data of the former IR + MS tab are taken over automatically.

## UV-Vis (ε) tab

Molar absorption coefficients (ε) from UV-Vis dilution series (Beer–Lambert: A/d vs. c) with standard error and 95 %
confidence interval, and a figure in the Origin style: spectra, λ/ε labels at the bands, an inset with the linear
regressions and R², the structure and a photo of the cuvette with the background removed.

1. **Open data:** File → Open measurement data, or drag files onto the window. Cary CSV/TXT exports and the
   instrument's own **.DSW/.BSW** files are supported. **Several files at once** (e.g. each
   concentration measured separately) are combined into one data set.
2. **Concentrations:** Concentrations are read from the sample names, e.g.
   `ABC-1-0p5mgml_THF` → series `ABC-1`, 0.5 mg/mL. Recognised units are
   `mgml`/`mg_ml`/`mg/ml`, `mM`, `uM`/`µM`; `p` stands for the decimal point.
   - If the names contain no concentrations (e.g. `c0` … `c4`) or the number is unclear (leading zero as in `05mgml`), the **Enter concentrations** section opens in the **Data** card (no separate window).
     Choose the **unit** explicitly (mM, µM, mg mL⁻¹, M) – nothing is pre-selected.
   - Under **Measurements** each concentration can be unticked: it then counts nowhere (figure, fit, tables, SI), the file stays unchanged.
   - "Fill dilution series" fills the selected rows (or all of them) with start, start/factor, … from top to bottom.
     The start value always belongs to the **top** selected row (usually the stock solution).
   - Samples without a value, e.g. a blank, are ignored.
   - The "Series" column lets you split several compounds within one file.
   - To change the values later, open the same section.
3. **Compound (per series):**
   - **Structure:** CDXML, SVG, PDF or an image file. With CDXML the **molar mass is calculated**
     automatically (isotopes such as D included); the formula is shown for checking. For the
     drawing to look **exactly as in ChemDraw**, also save the structure from ChemDraw as SVG, PDF
     or PNG with the same name next to the CDXML (e.g. `6g.cdxml` + `6g.svg`): the drawing is then
     taken unchanged from that file and the molar mass from the CDXML. Without such a file the
     drawing is regenerated (ACS 1996 style) and may differ from ChemDraw.
   - **Cuvette photo:** HEIC (iPhone), JPG, PNG and more. The background is removed automatically.
   - **Colour in solution (prediction, optional):** calculated from the spectrum – transmission 10^(−A)
     under daylight, CIE 1931 colorimetry, shown as a colour patch below the photo. Concentration and
     path length can be chosen (Beer–Lambert; default: highest measured concentration in 1 cm).
     Fluorescence and scattering are ignored, screens are not calibrated; display only, not in the figure.
     On first use the app offers a one-time download (~180 MB) of the AI model.
   - **Molar mass:** only needed for concentrations in mg/mL. Filled in automatically from CDXML,
     otherwise enter it by hand. Without it the tool reports the specific absorption coefficient
     *a* in L g⁻¹ cm⁻¹ instead of ε, and the field is marked red. For mM/µM the molar mass is not used.
4. **Analysis:** set path length and fit cutoff. Bands are found automatically; additional bands
   (e.g. shoulders) can be entered as a list ("in addition to automatically found" keeps both), and
   **"Find shoulders automatically"** adds shoulders (in the figure optionally marked "(sh)"); the labels can carry
   indices **λ₁/ε₁ …**.
   In the results table, the tick next to λ decides whether a band appears in the figure, and a
   double-click on **"Cutoff A"** sets an own cutoff for that band (e.g. to include a point just
   above A = 1). Bands with an own cutoff are highlighted; optionally, excluded points are shown as
   open symbols in the inset.
5. **Layout:**
   - **Drag** the inset, structure, cuvette and every λ/ε label with the mouse.
   - **Scroll** over the inset or an image to resize it, or use the "Size [% of plot width]" fields.
   - **Reset ▾** → "Reset layout" restores the automatic arrangement; "Reset all to defaults" sets all settings of
     the tab (display and analysis) back to the defaults – data and measurement details (files, reference/calibration,
     path length, entered values, caption, export size) stay, and Undo brings everything back. X-Ray and DFT also have
     "Defaults" next to "Reset view" (style, ellipsoids, bond thickness, labels, hidden atoms …).
   - **Hover** over the spectra: a box at the bottom right shows λ and A of the nearest data point (and its
     concentration), marked with a red circle in the preview only – handy to check the data.
     **Double-click** a point to add its wavelength as a band; double-click it again to remove it.
     The overlay and fluorescence tabs show λ and the plotted value the same way.
6. **Export:** File → Export (or the button). This writes the chosen formats (PDF/SVG/PNG),
   `<series>_results.csv` and the Excel report for **all** series into the compound (see below).

### What happens automatically during the analysis

- **Baseline** ("automatic (series)", default): the window is placed where the most concentrated
  sample absorbs least. Only the part of the window value that does *not* scale with concentration
  (instrument/cuvette offset) is subtracted. A residual proportional to c is treated as real
  absorption and kept. "automatic (simple)" subtracts the full window value. The baseline always
  uses the full data range, independent of the displayed λ range.
- **Fit cutoff:** points above the cutoff (default A = 1.0) are excluded from the fit.
- **Bands:** found automatically within the displayed λ range, or entered as a list.
- **Rounding:** ε (M⁻¹ cm⁻¹) and its errors are shown as integers (e.g. 7264 ± 318), the same in the table,
  figure, SI line, methods text and Excel report; the specific coefficient a is rounded to the precision of its
  standard error. The results CSV keeps the full values.
- **Conventions:** rounding is half up (7264.5 → 7265). R² refers to the mean also for a fit through the origin
  (1 − RSS/SST); Excel's LINEST without a constant reports a different, larger value there.
- **Warnings** (results table and log): fewer than 4 fit points, significant intercept (> t(0.975; n−2)·SE),
  R² below the threshold (default 0.98, adjustable under Analysis → "min. R² for figure"; 0 = show
  all; the band stays in the table – R² cell marked red –, CSV and Excel report but is not shown in the
  figure), fewer than 3 points (then no ε at all). With 4 points, R² alone says little: check the
  95 % confidence interval in the Excel report before lowering the threshold.
  R² is given with two decimals everywhere; the number of decimals can be chosen under Analysis → Advanced →
  "R² decimals" (applies to all tabs of the compound; CSV and Excel report keep the full value).

### Excel report

For every series, `<series>_report.xlsx` is written with three sheets:

- **Results:** one table as in the app (λ, ε ± SE, 95 % confidence interval, R², n, notes). Next to it, ε once more,
  recalculated independently with Excel formulas. Below, two charts in the style of the figure (spectra with the same
  colours, axes and ranges; A/d vs c with regression lines) and the details of the measurement (unit, path length,
  molar mass, model, cutoff, baseline window, measurement files).
- **Calculation:** all bands side by side. On top the data points (A, A/d, "in fit"), below the regression as
  **Excel formulas**: first the result (n, m, b, R², ε, SE, confidence interval), in grey below the intermediate
  values (x̄, ȳ, Sxx, Sxy, RSS, s, SE(m), SE(b), t). The yellow "in fit" cells (1 or 0) can be changed; Excel
  recalculates the band and the chart.
- **Spectra:** A(λ) of all samples, baseline-corrected and raw, with the offset subtracted per sample.

The cells hold the full value; only the number format rounds as in the app.

## UV-Vis overlay tab

Compare several spectra in one figure, measured and calculated:

- **Measurement…** adds spectra from CSV/TXT/DSW/BSW files (one entry per sample);
  **TD-DFT…** adds ORCA (4–6) or Gaussian output files; **ESD…** adds ORCA ESD(ABS) spectra (`.spectrum`, normalised
  only; x unit from `%ESD UNIT` of the input next to it or from the value range, changeable).
- **From tabs ▾** takes ε series of the ε tab (linked, measurement selectable) and TD-DFT calculations of the DFT tab.
- **SEC…** takes spectra from the SEC tab, e.g. to compare a reduction or oxidation with the isolated UV-Vis
  spectrum and TD-DFT. As a **series** (all spectra or only start and end, range by potential) everything is
  normalised with **one common factor** to the start spectrum, so intensity ratios and isosbestic points are kept;
  intermediate spectra grey, start blue, end red, legend with the potentials. **Single spectra** are normalised each on
  their own (shape comparison). SEC is never shown as ε: path length and converted concentration in the thin-layer
  cell are not known exactly.
- TD-DFT transitions are broadened with Gaussians in energy (FWHM and an empirical energy shift
  can be set per calculation, default 0.3 eV); ε follows from the oscillator strengths
  (ε(ν̃) = 1.306·10⁸ · Σ f/σ · exp(−((ν̃−ν̃ᵢ)/σ)²), as in GaussView). Transitions can be shown as sticks.
- **y quantity**: *normalised* – every spectrum is scaled to its maximum within the normalisation range (globally,
  or per spectrum with its own range, e.g. if the calculated band is shifted), **ε [10³ M⁻¹ cm⁻¹]** – measured
  spectra then need concentration (and molar mass for mg/mL) and path length, or **absorbance** as measured
  (measurements and SEC, without TD-DFT). The automatic y range always contains every curve.
- Per spectrum: colour, name, **line style and width**, **scale factor and vertical offset**
  (e.g. for stacked spectra); **order** with ↑/↓ (also the legend order).
- ORCA calculations with **spin–orbit coupling**: choose "with SOC" or "without SOC" per calculation.
- **Colour in solution** per TD-DFT calculation (entry details): A = ε·c·d with the chosen broadening, default
  1 mM in 1 cm – qualitative only, TD-DFT energies are often off by 0.2–0.3 eV.
- **Triplet states** (without SOC, f = 0) can be marked as dashed marks of fixed height; they do not
  contribute to the curve (ORCA 4–6, Gaussian).
- **Combine** calculations: select two or more TD-DFT entries (Ctrl/Shift click) → "Combine". The
  transitions are merged and then broadened together; one weight per calculation (default 1 = sum,
  e.g. 0.7/0.3 for conformers). Calculations should be at the same level of theory; identical states in
  both calculations trigger a warning (they would be counted twice).
- **TD-DFT normalisation:** curve and sticks always share one scale factor (each stick is the height
  of its own Gaussian, the curve is their sum). Reference: "curve maximum = 1" or "strongest
  transition = 1"; "curve maximum = 1, f on the right axis" adds the oscillator strength as a second scale for
  the same sticks (left out with a note if the calculations use different scales).
- A **structure per spectrum**, optionally drawn in the curve colour.
- Structure with adjustable size; the legend is placed in free space and can be dragged.
- **Stacked** (as usual in papers): curves are offset vertically by a common spacing in list order
  (top of the list = top curve). "Same stacking level as the curve above" keeps e.g. a TD-DFT curve
  on the level of its measurement. The **y axis** can be shown with numbers, without numbers and
  ticks (default when stacked – offset curves make the numbers misleading) or hidden. Optionally
  the **names are written at the curves** instead of a legend, and a dashed zero line marks each level.

## UV-Vis kinetics tab

How the spectra of one solution change over time – stability over days, or a reaction:

- **Add files** (several at once, more later, e.g. one file per day): each spectrum becomes a row with name
  (renamable), **series** and **acquisition time**. The time comes only from the measurement file (Cary CSV: “Collection
  Time” per sample, assigned by the order of the columns; US and German date format), never from the file name or the
  file date. .DSW/.BSW contain no time per spectrum: they appear only in the view “Spectra over time”, with their name.
  Instrument baselines (“Baseline 100%T/0%T”) are not offered.
- The **series** (e.g. the concentration) is prefilled only when the sample name states a concentration unambiguously
  (“…-20uM”); otherwise enter it – in the table, or for several selected rows at once under “Selection”. Rows without a
  series are not evaluated (hint). Saturated spectra are not detected: uncheck them.
- **View** (Evaluation step): “Spectra over time” shows one series coloured along time, labelled with the time since its
  first spectrum. “Absorbance against time” shows for each series the absorbance at the **wavelength** (integer; auto =
  maximum of the first spectrum) against the time since its first spectrum; with **Maximum ±** the maximum within
  λ ± n nm instead of the value exactly at λ. y axis as measured or relative to the first spectrum in %, time unit
  min/h/d or auto (by duration).
- **Fit decay**: per series A(t) = A0·exp(−k·t) fitted to the measured absorbances (least squares, as for the
  isothermal EPR decays) with the 95% interval of k and the half-life t½ = ln 2/k; from three points. If a series rises,
  k < 0 and there is no half-life.
- No correction for path length or concentration: absorbance as measured.
- Right: figure, **Results** (table per data point, summary per series: first and last value, remaining %, duration,
  k and t½), SI text. Export: figure and `…_kinetics.csv` (series, name, time, A, relative).

## Fluorescence tab

Absorption and emission in one figure, as commonly shown in papers:

- Absorption (any UV-Vis file) and emission (Cary Eclipse CSV or .FBSW), both normalised to 1;
  λex is filled in automatically from the emission file;
  the absorption to the maximum within the "band of interest".
- Labels with λabs of the absorption maximum (plus ε, if entered) and λem of the emission maximum.
- **Stokes shift** Δν̃ = 1/λabs − 1/λem in cm⁻¹ (rounded to 10 cm⁻¹, peak positions from ~1 nm data
  are not more precise) and in nm; optionally also in the figure at the emission label.
- **Absorbance at λex** with a warning above A = 0.1: the inner-filter effect then distorts the
  emission spectrum and lowers quantum yields (only relevant if both were measured on the same solution).
- Optionally hide scattered light at λex and 2·λex.
- Two cuvette photos (daylight and under UV) are combined with an arrow and the excitation
  wavelength; for the UV photo background removal is off by default (dark background stays).
- Structure as in the ε tab.


## CV tab (cyclic voltammetry)

- Reads **Gamry .DTA** files (Framework 6/7, both table variants); scan rate, electrode area and cycles
  come from the file. Several measurements (e.g. a scan-rate series) are overlaid, optionally with a
  blue → red colour gradient by scan rate, an arrow for the scan direction and E½ in the figure.
- **Redox couples** are analysed in potential windows ("Suggest" proposes them, the windows can be
  edited): E_pa (current maximum in the forward scan), E_pc (minimum in the reverse scan), E½, ΔE_p,
  i_pa, i_pc and the peak-current ratio after **Nicholson** (accounts for the decaying forward current;
  ≈ 1 = chemically reversible). Peaks at the window edge are marked red.
- **Baseline** (on by default): i_p against a straight line through the current before the forward peak (charging
  current + background), extrapolated beneath the peak; for the reverse peak shifted by the step of the charging current
  at the switching potential (2·C·v), the decaying forward current is corrected by Nicholson. Distance to the peak is
  adjustable (default 0.20 V; compounds created before version 1.1 keep 0.15 V), baselines optionally in the figure. Peak potentials are unchanged. If the window has too
  little current before the peak, this is flagged and the measurement is left out of the regressions.
- From 3 scan rates per group and couple: regression of **i_p vs. √v** (Randles–Ševčík) and **log i_p vs. log v**
  (slope 0.5 = diffusion-controlled, 1 = adsorbed), each with a **95% confidence interval**.
- **Diffusion coefficient** (evaluation step, card "Diffusion Coefficient"): with the number of electrons n, the area
  A of the working electrode, the concentration c and the temperature, the program calculates D from the
  Randles–Ševčík slope of the forward peak (i_p = 0.4463·n·F·A·c·√(n·F·v·D/RT), reversible, freely diffusing couple). Without area or
  concentration there is no D; the area is never taken from the measurement file. The interval carries only the
  uncertainty of the slope, not that of area and concentration. The result appears on the Results tab and in the
  methods text.
- **Conventions of the CV calculation:** the Nicholson ratio uses baseline-corrected currents (the original uses the
  zero-current axis) and scatters by about ±3 % even for ideally reversible couples, depending on the switching
  potential. The baseline ends 0.20 V before the peak; for an ideally reversible wave about 0.3 % of the peak current
  is still present there, so i_p comes out at most 1 % too small (with the former 0.15 V it was 1–3 %, D accordingly
  2–6 %). If the range before the wave is too short for that, the baseline ends 0.15 V before the peak as before; the
  program says so, and i_p can then be up to about 6 % too small. The default Ac₂Fc +0.49 V is a
  value for CH₂Cl₂ (Connelly, Geiger, Chem. Rev. 1996, 96, 877); enter your own value for other solvents. E½ equals
  the formal potential only if both forms have the same diffusion coefficient.
- **Copy** (Methods Text card on the SI Text tab): English paragraph on the data evaluation (referencing, peak determination, baseline, Nicholson,
  regressions) to append to the setup paragraph "Cyclic Voltammetry" of the SI, plus the results per redox couple.
- **Referencing:** as measured (reference electrode, e.g. Ag/AgNO₃), **internal** (Fc or Ac₂Fc couple in one
  of the measurements; E½ of the reference vs. Fc⁺/Fc is editable – default Ac₂Fc +0.49 V, check against your
  literature) or a manual shift. The axis then reads "E [V vs. Fc⁰/⁺]".
- **Reference per measurement** ("Reference of the selected measurement"): own internal standard (also the
  Fc/Ac₂Fc couple in the same file, e.g. "with Ac₂Fc") or own shift – needed when comparing solvents, each against
  its own standard. The couple windows follow each measurement's reference.
- **Group** per measurement (e.g. the solvent): data series in the plots against scan rate.
- **Structure per measurement** (optionally in the curve colour) and **labels** either E½ per couple or **E_pa/E_pc as
  numbers at the peaks** (e.g. sample and Ac₂Fc in one measurement); y axis with numbers, without or hidden.
- **Stacked** CVs (list order from top to bottom, adjustable gap, y axis without numbers) with **E½ at every curve**
  next to its anodic peak (E¹½, E²½ for several couples).
- **Plot:** cyclic voltammogram, **electrochemical reversibility** (ΔE_p vs. v), **Randles–Ševčík** (i_pa and i_pc vs.
  √v or vs. v, with fit lines from 3 scan rates), **diffusion** (log |i_p| vs. log v), **chemical reversibility** (i_r/i_f after
  Nicholson vs. v, line at 1) or **trumpet plot** (E_pa and E_pc vs. log v), one series per group. Note: ΔE_p also
  contains the iR drop (especially in THF); the trumpet plot is drawn without a k⁰ analysis, which would need
  several decades of scan rate.
- The **scan-direction arrow** can be dragged in the figure; its place is saved.
- Current as recorded (Gamry: IUPAC, anodic positive) or inverted; optionally as current density.
- Export: figure (PDF/SVG/PNG), `…_results.csv` with all values (incl. group, reference offset, the iR
  compensation entry of the Gamry file, currents with/without baseline and the charging-current step) and
  `…_methods.txt` (SI text).

## SEC tab (spectroelectrochemistry)

- Reads a **spectral series from B&W Tek BWSpec** text exports (wavelengths from the calibration coefficients
  in the file) and the **Gamry .DTA** file of the potential scan. Each spectrum gets its potential via the
  clock time (spectrum time − start of the Gamry run, plus an adjustable time offset).
- **Merged UV/Vis/NIR exports** (`Merged spectral data`, two columns: `*.Abs8.txt`, `*.Raw8.txt`): the whole range is
  shown, in file order; absorbance and raw signal are never mixed in a series, and neither is corrected or smoothed.
  These files contain **no times**, so at first the series runs by number, without potentials and without A(E) or
  Nernst evaluation. A potential comes only from what you confirm under **Potential Assignment**: start + interval on
  the time axis of the potentiostat file, a table number → time, or a table number → potential (for held steps, e.g.
  `1-31; 0.95`). Spectra outside the measurement are left out rather than given the end potential, and the source of the
  assignment is stated in the caption and methods text. Gaps in the numbering and jumps in the file times are reported;
  file times never set a potential.
- **Spectral series:** first and last spectrum highlighted (blue/red), the others grey – or a colour gradient
  by potential; optionally difference spectra (ΔA vs. the first spectrum) and a zero point (mean 780–820 nm);
  λ labels in the colour of the matching spectrum. Spectrum range selectable (e.g. only the first wave).
- **Intermediate species:** one or more spectra in between can be highlighted in green (further ones orange, purple,
  teal), e.g. the radical cation between neutral (blue) and dication (red) – entered as potential (axis scale, nearest
  spectrum) or, without a potential file, as spectrum number. The caption then reads "Color coding: **neutral** (blue),
  **radical cation** (green), **dication** (red)." (species names from the caption fields).
- **A at λ vs. E** with an apparent Nernst fit (E½, n). In a continuous scan the electrolysis in the thin-layer
  cell lags behind (E½ shifted, n < 1); true Nernst values need potential steps at equilibrium – CV values take
  precedence.
- **Heatmap:** the whole series in one picture – x = wavelength (range as for the spectral series), y = spectra in the
  order of acquisition from bottom to top, colour = absorbance as measured or the difference to the first spectrum shown
  (ΔA, diverging colour map with 0 in the middle). The y axis stays the order; it is labelled with the potential (also
  when it goes up and comes back), without potentials with the time since the first spectrum from the files, otherwise
  with the number. Colour map selectable (viridis, cividis, magma or RdBu, PuOr, coolwarm), upper end "auto" or fixed.
  Raw-signal series are called "raw signal" here as well. The mouse shows λ, spectrum and value; the CSV export holds
  the matrix (rows = spectra, columns = λ).
- Potential axis as measured, shifted by E(Fc⁺/Fc) or with the referencing of the CV tab.

## H-Cell tab (charge–discharge cycling)

- Reads **Gamry "Cyclic Charge Discharge" files** (main file with the capacity table) and the step files
  `CHARGE_#n.DTA`/`DISCHARGE_#n.DTA` from the folder `CHARGE_DISCHARGE` next to it. Other files in that folder belong
  to other experiments and are not imported; other Gamry types are rejected with a message. Each measurement gets its
  own folder in the project (`data/hcell/<name>/`) so the step files stay together.
- **Capacity vs. cycle:** charge and discharge capacity per cycle (column "Charge" of the file, C → mAh) on the left,
  in % of the theoretical capacity or in mAh; Coulombic efficiency (discharge/charge of the same cycle) on the right,
  can be switched off. One measurement: black squares, red circles, blue triangles as in the group's SI. Several visible
  measurements share one figure, one colour each from the list (charge filled circle, discharge open circle, efficiency
  triangle); the legend has one block per measurement.
- **Theoretical capacity:** from the file (CAPACITY, set in the instrument); your own value applies only to the
  measurement selected in the list, so cells with different capacities can be compared in %.
- **Potential vs. time:** charge (black) and discharge curves (red) of the selected cycles over the true time in h; the
  time axis is broken between non-adjacent cycles (break marks, numbers = true time), each cycle is labelled "#n".
  Empty "Cycles" field = first, second and evenly spaced up to the last (at most five). A missing step file is noted
  under the preview; only what exists is drawn. The selected measurement is shown. Optional reference for the axis,
  e.g. `Ag0/+`.
- **Results:** table per cycle of the selected measurement (Q_charge, Q_discharge, capacity in %, efficiency) and, for
  every visible measurement, first/last discharge capacity, retention (last/first), mean efficiency and duration;
  retention and mean efficiency as tiles. No smoothing, no fits, no uncertainties.
- **Export:** figure and the cycle table as CSV (`…_cycles.csv`); caption (concentration, electrolyte) and methods text
  in the SI Text tab.

## EPR tab (CW EPR)

- Reads **Bruker BES3T** (.dsc + .DTA, e.g. Magnettech ESR5000/ESRStudio, Elexsys; 2D files give one spectrum
  per row) and **two-column text** (Magnettech MS400 export; microwave frequency from file names like
  `…-9p412345-…`). Frequency, temperature, modulation and power are shown per spectrum. If a text file does not
  state the field unit (no "[mT]" or "[G]" in the header), the unit is assumed (field values above 1500 count as G)
  and this is shown with the measurement; **Field unit of the file** confirms or changes it (needed e.g. for W-band
  data in mT).
- **Dark spectrum:** the measurement before irradiation can be subtracted from each spectrum (light − k·dark,
  interpolated onto the same field grid); a warning appears if frequency, modulation or power differ.
- **Processing:** a baseline of your choice, then hide field ranges (e.g. the sharp radical signal) and
  moving-average smoothing. Baseline methods:
  - **Polynomial** (order 0–5) from the outer edges of the sweep or from chosen signal-free ranges: for weakly
    curved baselines.
  - **Smooth:** follows a broad background (e.g. the resonator in wide sweeps) and keeps narrow lines; no dark
    spectrum is needed and the noise stays that of the single measurement. The only value is the **width**:
    narrower features stay as signal, broader ones are subtracted as background. It must be larger than the
    broadest real line, otherwise broad parts of the spectrum vanish too; one-sided lines lose some height, depending on
    line shape and noise (at one twelfth of the width: Gaussian line up to about 4 %, Lorentzian line up to about 10 %). Calculation: Whittaker smoother (least squares with a penalty on the second
    differences) with one robust reweighting step; the methods text states method, width and reference.
  - **Spline:** natural cubic spline through the means of the signal-free ranges (at least two, keep them short),
    like the baseline with set points in instrument software.
  - A **dark spectrum** remains the choice when the background is about as narrow as the signal; it doubles the
    noise power (factor √2 in the noise), though, and removes whatever signal the dark spectrum already contains.
- **EasySpin simulations** as two-column text (B in mT, intensity), e.g. `writematrix([B(:) spc(:)], 'sim.txt',
  'Delimiter', '\t')`; scaled by least squares to a measurement (or by hand) and shifted in field; drawn dashed on
  the same level. A **parameter file** (the MATLAB lines `Sys.D = [D E]; …`) is shown with D and |E| converted to
  cm⁻¹ and can be written into the figure.
- Display in mT or G, overlaid or stacked, normalised, y axis without numbers by default, free labels such as
  `Z⁻@122, Y⁺@400`. Hover shows B, the g-factor and the intensity.
- **Series (time, temperature):** when stacked, the name stands to the right of each trace instead of in a legend;
  double-click a name in the list to rename it. **Trace labels** shows time or temperature from the measurement file,
  **Colour gradient** colours the traces in list order, **Reverse** flips the whole list.
- **Several species:** all simulations assigned to a measurement (EasySpin or own S = ½) are scaled *together* by
  linear least squares; the fractions (double integral) are shown, optionally the sum and the residual
  (measured − sum) – i.e. subtraction of individual species. Non-linear parameters (g, A, D/E, linewidths of
  powder spectra) are fitted in EasySpin; Elucida only determines the fractions.
- **Own isotropic S = ½ simulation and fit** (solution, first order): g, groups of equivalent nuclei (e.g.
  `2 14N 0.65; 4 1H 0.32`, a in mT; isotopes from ¹H to ²⁰⁹Bi, e.g. ¹¹B, ⁷Li, ²³Na, ²⁷Al, or the nuclear spin
  directly as `I=3/2`), peak-to-peak linewidth and Lorentzian fraction; "Fit" refines g, a and
  ΔB_pp (Levenberg–Marquardt after a coarse grid search, amplitude linear). If several S = ½ species overlap in
  one measurement, **Fit together** fits all simulations assigned to it at once (one linear amplitude per species).
  Start values are the current values and there is no coarse search: set each species roughly or fit it on its own
  first. The fit reports no uncertainties.
- **Conventions of the EPR calculation:** couplings in MHz = a [mT] · (µ_B/h) · g with the fitted g (EasySpin uses
  g_e; the difference is g/g_e). Line shape pseudo-Voigt: sum of a Gaussian and a Lorentzian derivative of equal
  ΔB_pp, no convolution; the Lorentzian fraction is not comparable with EasySpin widths. Hyperfine patterns to first
  order only (for large couplings, e.g. ⁵¹V, ⁵⁵Mn, Cu, g and a shift), no weighting of isotopologues. A g fitted
  before the field calibration or reference frequency was changed is reported again only after a new fit.
- **Field calibration with TEMPO** (or another reference): fit the reference with an S = ½ simulation, choose it as
  calibration with its literature g (default 2.0055, TEMPO in MeCN); ΔB = B(g_fit) − B(g_lit) is subtracted from all
  other measurements, whose fits then give calibrated g-factors.
- **Intensity vs. time or temperature** (e.g. illumination kinetics, thermal decay): double integral or
  peak-to-peak in a field window for every visible measurement (after dark spectrum and baseline), optionally
  × T (Curie), normalised; time counts from the earliest spectrum in the tab (e.g. the dark spectrum). "Use this
  dark spectrum for all measurements" sets the background for a whole series at once and hides the dark spectrum
  itself in the figure (its check box in the list shows it again).
- **Thermal decay at constant heating rate** (port of the group's MATLAB script): intensity per spectrum as
  peak-to-peak, double integral or **Gaussian + line fitted to a feature** (e.g. the X feature at 487 mT), × T,
  field scaled to a reference frequency (e.g. 9.3 GHz) and a temperature correction (e.g. −1.5 K); then
  **E_a and A** from I(T) = exp(−A·∫exp(−E_a/RT)/β dT) with β from the mean temperature and time steps.
  Objective least squares (default; reliable 95 % interval with t quantile) or "as script" (√|r|, for comparison
  with old numbers – sensitive to the optimiser, its interval strongly underestimates the uncertainty). E_a and ln A are almost fully correlated.
- **Where:** step **Evaluation**, card **Intensity and Kinetics**. The field **View** chooses what the figure
  shows: spectra, intensity against time, against temperature, Arrhenius or against the number. The fields below
  belong to the chosen view; the others are hidden.
- **Isothermal decays and Arrhenius:** the view "Intensity against time" with **Fit decay** fits a first-order decay per
  temperature, I(t) = I₀·exp(−k·t) (least squares on the intensities, 95 % interval of k with the t quantile). A
  series consists of the measurements whose temperature **from the measurement file** agrees after rounding to 1 K;
  fitting starts at three spectra, otherwise a note appears. **Fit up to loss** restricts the fit to the start of
  each series (e.g. 15 %: until the intensity is 15 % below the first point). The view "Arrhenius" plots ln k
  against 1000/T and gives E_a and ln A from an unweighted straight-line fit, one point per temperature; a 95 %
  interval exists only from three temperatures on. The bars at the points are the intervals of k. Peak-to-peak
  underestimates k once the signal disappears in the noise; use the double integral or "Fit up to loss" then.
- **Export for EasySpin:** besides the figure, every measurement is written as a two-column text file (B in mT,
  intensity) in full resolution after dark spectrum, baseline and smoothing – without normalisation or hidden
  ranges – with `%` header lines documenting frequency, temperature and processing (`load(...)` in MATLAB, ready
  for `esfit`). The intensity series is saved as `…_intensity.csv`.

## X-Ray tab

- Load one or more **CIF** files (button or drag & drop); each `data_` block with atoms becomes one entry (one
  column in the tables). Elucida reads the CIF itself (cell, coordinates, U_iso/U_ij, occupancy, PART, symmetry
  operations, `_geom_bond`/`_geom_angle`/`_geom_torsion`); no extra software needed.
- **ORTEP figure in the Mercury style:** shaded displacement ellipsoids at 50 % probability (adjustable), projected
  exactly, with the principal ellipses; black bonds, bold labels (draggable), H atoms as small shaded spheres. Further style (also in PDF/SVG/PNG and Word): flat Olex2 style. Single atoms (e.g. individual H) can be hidden and labels switched **per atom**
  (atom list, double-click on the atom, or **Shift + drag a box** for several atoms); label colour black or like the atom. **Drag to rotate**,
  right button to pan, mouse wheel to zoom; the view is stored per structure, **Reset view** goes back to the
  default orientation (least overlap of the atoms). Atom colours per element are freely selectable (Olex2
  colours by default).
- The molecule is **completed by symmetry** (e.g. a molecule on an inversion centre); generated atoms carry a
  superscript (C1ⁱ) and the operation is given as a footnote. **Disorder:** major part only (default), all parts or
  the minor part. Separate fragments (solvent, counter-ions) and H atoms can be hidden; **Hide solvent** / **Hide
  counterions** recognise common ones from the formula (THF, Et₂O, CH₂Cl₂, toluene …; OTf⁻, BF₄⁻, PF₆⁻, BArF⁻ …).
- **Wireframe** for bulky groups (e.g. Dipp): click the bond to the substituent (core atom first, e.g. N then
  C_ipso) and press **As wireframe** – everything behind it is drawn as thin lines in the element colours, without
  H atoms and labels. If the bond is part of a ring (spiro atom), the ring system behind the first atom is used. The
  start view avoids overlapping atoms; labels optionally for heteroatoms only.
- **Caption suggestion** (English), e.g. „… Displacement ellipsoids are drawn at the 50 % probability level;
  co-crystallised THF omitted, Dipp groups shown as wireframe without hydrogen atoms for clarity. …“, with the
  selected parameters and symmetry codes; copied with one click and written to `…_captions.txt` on export.
- **Click atoms** (the front-most one wins): 2 = distance, 3 = angle, 4 = torsion angle. Values with s.u. are taken
  **exactly from the CIF** (e.g. 1.392(3)); Elucida never estimates an s.u. itself. If a value is missing (torsion
  angles without `CONF`), it is calculated from the coordinates, shown **without** s.u. and marked – set `CONF` in
  Olex2/SHELXL and refine again to get torsion angles with s.u.
- **Tables for the SI:** crystal data and structure refinement (one column per compound; numbers exactly as in the
  CIF, space group in italics with subscripts, diff. peak/hole with a true minus sign; internal reference and CCDC
  number editable) and selected bond lengths, angles and torsion angles (same atom names side by side). **Copy**
  keeps italics and sub-/superscripts in Word; export also writes CSV and Excel. Table labels are in English
  (as usual for an SI).
- Export: one figure per structure (PDF/SVG vector, PNG) plus `…_crystal_data.csv`, `…_parameters.csv` and
  `…_tables.xlsx`. The label size can be set per tab and the **background** chosen (white, transparent, colour; also
  for Word).

## DFT tab

- Load **xyz** files (also trajectories; the last frame is shown) or outputs of **ORCA 6** (`.out`) and **Gaussian**
  (`.log`). Files written by a PowerShell redirect (UTF-16) are recognised. Styles: Mercury, Olex2, **ball and stick like the ORCA
  manual**, **IboView** and a **line drawing** (white balls, hollow sticks, as in classic journal figures); mouse as in the X-Ray tab.
- **Measure and align** as in the X-Ray tab: click 2/3/4 atoms for distance, angle or dihedral (values from the
  geometry, 3 or 1 decimals); bond pointing down/up/left/right, plane face-on, step rotation, flip, ChemDraw template.
- **Renumber:** press **Number atoms** and click the atoms in the desired order; **Apply** puts them in front, the
  remaining atoms keep their order (optionally H atoms right after their atom). **Save xyz** writes a new file with the
  lines unchanged (only reordered); the loaded file is never overwritten. Counting from 0 (ORCA) can be shown. Atom
  radius and bond thickness also apply in the ball-and-stick styles (relative to the default); the background is
  selectable as in the X-Ray tab.
- **Like template:** takes over the numbering of another geometry in the tab or of a crystal structure in the X-Ray
  tab (then with the CIF atom names, e.g. C1, H3A). Heavy atoms are matched by connectivity, symmetric molecules by
  the smallest deviation after superposition; an equally good alternative is reported with the atoms concerned, H
  atoms follow their neighbour atom.
- **Calculation for the SI** (ORCA 6, Gaussian): name, figure, charge/multiplicity/point group, Cartesian coordinates
  and E_el/H/G (ZPE column optional), optionally the input line (per structure or once as "Computational details"),
  the convergence table of the last cycle and the frequency result. All values exactly as in the output. The program
  warns about aborted runs, non-converged optimisations and imaginary frequencies; with CPCM only the dielectric
  contribution is given (a solvation energy needs the gas-phase calculation). **Copy**, **Save Word** (two
  columns) or via the SI section.
- **Isosurface like IboView:** threshold type "density" (fraction of |ψ|², default 80%) or "absolute" (±ψ, default
  0.01), decimals and step as in IboView.
- **Energy profile:** an energy profile compares several compounds and therefore belongs to a reaction path of the
  project (Computational Chemistry, see above); it can be edited only there, the page no longer exists in the DFT tab of a
  compound (profile data saved there earlier stay in the project file). Species = the opt/freq calculations, each with label, step
  and path(s) A, B …; optional **single points** (e.g. DLPNO-CCSD(T)), matched by identical atoms and coordinates (never by
  file name): G = E(SP) + (G − E_el). Levels with dashed connectors, ΔG/ΔH/ΔE in kcal mol⁻¹ with one decimal, caption
  "… calculated at the <single point>//<geometry> level of theory".
  **IRC** (ORCA): output + `<name>_IRC_Full_trj.xyz`, x = reaction coordinate in Å (sum of the Cartesian displacements, not mass-weighted; TS = 0) or a bond length, several
  IRCs in a row, barriers at the transition state.
- **NICS** (page): Gaussian NMR outputs with ghost atoms (Bq, e.g. from py.Aroma): NICS and NICSzz (along the ring-plane
  normal) per point, average above/below; scans as a curve over the path length (NICS black, NICSzz red).

- **Multireference (ORCA 6):** CASSCF, SC-NEVPT2, QD-SC-NEVPT2 and SORCI results are offered per block, with energies,
  configuration weights and occupations as printed. The SI takes a block only on explicit choice. ΔE_ST between a chosen
  singlet and triplet of the same block, with the equation shown. The diradical indicator is y₀ = n(LUNO), and only for
  natural orbitals of one converged singlet state. Incomplete or aborted outputs are flagged. In the overlay, MR spectra
  are selectable by method and block.

## Cluster connection

In the project under **Computational Chemistry**, the cluster view sits next to the reaction paths and shows running and finished
calculations. With a path open, the status card in the path list (☰) leads there. The connection is not tied to one cluster: it works with any Linux server you can log in to with an
SSH key.

**Requirements**

- Server: Linux, login with an SSH key. A second factor on every login does not work, because Elucida checks in the background.
- Job list: Slurm with `squeue` and `sacct`. Without Slurm (or without accounting) the check reports an error. **Show folder** and
  **Fetch results** still work, you then enter the folder by hand.
- Your computer: OpenSSH. macOS and Linux include it, on Windows 10/11 it is an optional feature ("OpenSSH Client"). Elucida does not
  use PuTTY or Pageant, a PuTTY key (`.ppk`) must be converted to the OpenSSH format first.

**One-time setup**

1. Create a key if you have none (with a passphrase):

   ```bash
   ssh-keygen -t ed25519
   ```

2. Add the **public** key (`~/.ssh/id_ed25519.pub`) on the server the way your computing centre asks for: through its portal or
   application form, otherwise with `ssh-copy-id user@host`. The private key stays on your computer.
3. Log in once in a terminal and confirm the server's fingerprint. Elucida never accepts an unknown server by itself.

   ```bash
   ssh user@host
   ```

4. Load the key into the agent so that no passphrase is asked for:
   - macOS: `ssh-add --apple-use-keychain ~/.ssh/id_ed25519`, and so that this survives a restart, in `~/.ssh/config`:

     ```
     Host *
       UseKeychain yes
       AddKeysToAgent yes
     ```

   - Windows: PowerShell as administrator, then `ssh-add` as your normal user:

     ```powershell
     Get-Service ssh-agent | Set-Service -StartupType Automatic
     Start-Service ssh-agent
     ```

   - Linux: `ssh-add` in the desktop session you start Elucida from.
5. Check. If this prints two Slurm versions without asking anything, it also works from Elucida:

   ```bash
   ssh -o BatchMode=yes user@host "squeue --version && sacct --version"
   ```

6. In Elucida, open the cluster view and enter host and user under **Access**. If the server needs a VPN, the VPN must be running.

The host can also be a name from `~/.ssh/config`, which then holds for example `Port`, `IdentityFile` or `ProxyJump`.

**Use**

While the app is open it checks every 2 minutes (Windows: every 15 minutes) and reports finished jobs, in other tabs too. **Refresh** checks at once. When Elucida is not in the foreground,
a system notification follows (can be turned off under **Access**). Pick a job, tick files, choose the **Target** (compound or
reaction path), **Fetch results**: outputs and xyz are added there as calculations, everything else goes to `data/dft`. `.gbw` and
`.hess` are not offered.

**What Elucida may do**

Elucida only calls your system's `ssh` and reads neither keys nor passwords. On the server it runs only `squeue`, `sacct`, `find` and
`cat`: jobs cannot be started or cancelled, and there are no free commands. Host, user and folder stay in the local settings, never
in the project. On macOS and Linux the connection stays open for 3 minutes after the last check (`~/.ssh/elucida-…`), which spares
the login node. On Windows every check is a new login, hence the longer interval. `sacct` only runs at start, on **Refresh** and when the job list changes.

**If it does not work**

The message from `ssh` is shown at the bottom of the cluster view. If the server refuses the login, Elucida pauses the automatic
checks, because some computing centres block an IP after a few failed attempts. After fixing it, continue with **Refresh**.

| Message | Cause and fix |
|---|---|
| `Host key verification failed` | Server not confirmed yet: step 3. If its key changed, ask the computing centre first, then `ssh-keygen -R host`. |
| `Permission denied (publickey)` | Key not in the agent (`ssh-add -l` does not list it: step 4) or not added on the server. |
| Timeout, `Could not resolve hostname` | Server not reachable: check VPN or network. |
| `command not found` for `squeue` or `sacct` | No Slurm on the server: enter the folder by hand. |
| Files missing while the job runs | The job works in a local folder of the compute node (`/scratch`). Elucida only sees shared folders, so results appear once the job has copied them back. |
| `find: -printf …` | No GNU `find` on the server, so it is not a Linux system. |

## Other tab

Figures from other programs (PDF, SVG, PNG) go into the SI **unchanged**: each with a caption and a chapter – an
existing SI chapter or a heading of your own (in the full SI an own chapter at the end). The aspect ratio is kept, two
figures per page like all others; not in the data package.

## Appearance

The program follows the system's light or dark mode; **Format → Appearance** switches to light or dark permanently, as
does the moon/sun button in the toolbar (the icon shows the current state).
The left column of every tab is split into steps (usually **Data · Evaluation · Display**): the bar at the top switches the step, a dot on it marks changed values, **Next: …** at the bottom leads to the next one. Lists with several entries (spectra, measurements, structures) are reordered with the arrow buttons or by dragging a row.
In the evaluation step the **Processing Chain** card shows which steps of the calculation are in use. To the right of the tabs the most important results appear as tiles; the **SI Text** tab holds the caption with its fields and the methods text, each ready to copy. Quantities are typeset properly: symbols in italics, indices as subscripts, units upright and with negative exponents (mg mL⁻¹, mV s⁻¹); names and formulas with subscript numbers and italic locants. Drop-down lists and chips cannot do this and stay upright. Switches are **chips**: clicking a pill turns it on (blue) or off; the tooltip gives the long form. A field that shows **"off"** switches its function on with the first step up (with the value used last) and off again at the lower end. Ranges that show **"auto"** cover all data: a click into the field sets your own limits, a cleared field switches back to automatic. Every field with "auto" or "off" shows a small reset arrow while it holds a value of its own: one click returns to "auto"/"off", and so does clearing the field and leaving it or pressing Enter.
Rarely used cards of the left column are collapsed (click the title to open them); a title with **"(changed)"** means
that a value there differs from the default. Results, tables and SI texts sit in tabs next to the figure. The mouse
wheel scrolls the column and only changes a field after it has been clicked. Notes while drawing (e.g. curves left out)
appear below the preview, **Help → Log…** shows all messages. **Export** sits at the bottom right below the figure, next to the caption. **Presets ▾** at the bottom left saves a tab's settings for
other compounds. The figures are not affected by the theme.

**Canvas dark / Canvas light** in the toolbar (moon = dark, sun = light; also Format → Canvas) switches; dark shows all plots, previews and editors on pure black. Hues stay (red stays
red), dark colours are lightened so that they remain legible. This changes the screen only, never exports, stored
files or the SI.

## Figure size for Word

Under "Plot" → "Size":

- **Word: half A4 page (16 × 11 cm)** (default). The figure is built at exactly this size, with fonts,
  lines and layout scaled to match. Two figures with one-line captions fit on one A4 page with
  Word's default margins.
- **Custom:** width and height in cm, e.g. if your template uses different margins.
- **Standard:** larger format, tightly cropped.

In Word: Insert → Pictures → choose the SVG, then right-click → Insert Caption.
SVG works in Word 2019, 2021 and Microsoft 365. For older versions use the PNG (600 dpi).

In PDF and SVG the structure remains vector graphics. Text in the SVG is stored as paths, so it
looks identical everywhere but cannot be edited in Word.

## Fonts and frames

Fold card **Fonts and Frames**, the last card of the step **Display** in every tab with a figure (Format → "Fonts and
frames…" shows it in the open tab). Every change applies at once to **all tabs** (default); with the chip **This Tab
Only** the tab gets its own format (starts as a copy of the default; deselected, the default applies again). Everything
is saved with the compound and can be undone; the card shows only what the tab has in its figure (e.g. no symbol font in
CV, no frames in X-Ray). **Reset to defaults** restores the defaults:

- **Text font** and **symbol font**. By default λ and ε are set in the symbol font (Times New Roman),
  as in Origin; this can be switched off.
- **Band labels:** font size (automatic by default), bold, italic, colour.
- **Frames:** closed frame around the plot (top and right too; default since 1.24, like the Origin figures) and a
  rounded frame around the chemical structure.

## Notes on CDXML

- Exact ChemDraw appearance: put an SVG/PDF/PNG export with the same name next to the CDXML (see
  above). It is only used while it is not older than the CDXML – after editing in ChemDraw an old export would show the
  old drawing, so Elucida then draws from the CDXML and says so (export again for the exact picture). Otherwise Elucida draws the structure itself from the CDXML coordinates: bonds, labels as written
  (abbreviations such as TMS or Dipp stay), arrows and texts of reaction schemes; the font is Helvetica (same metrics
  as Arial). Only if the file contains something this drawing cannot show (embedded pictures, brackets, curved
  arrows …) RDKit redraws it, with a note.
- Molar mass = sum of all fragments (counter-ions are included).
- If abbreviations such as Dipp or Mes cannot be resolved, **no** molar mass is set and a warning is
  shown. Please enter it by hand in that case.
- Structures are read from `.cdxml` (save binary `.cdx` files as `.cdxml` in ChemDraw); a `.cdx` next to a synthesis scheme is only used for the editable object in Word.

## Supported data

| Tab | Files |
|---|---|
| Compound, structures | ChemDraw **CDXML** (formula and molar mass), with an SVG/PDF/PNG export of the same name for the exact ChemDraw drawing; photos as HEIC, JPG, PNG |
| Synthesis | Scheme as CDXML (+ SVG/PDF), **.cdx** next to it for an editable ChemDraw object in Word, **.emf** for a sharp preview |
| NMR | MestReNova **SVG** or **EMF** exports, Mnova report (text), **TopSpin** experiments/datasets (folder), **.mnova** documents |
| IR + EA | Bruker **OPUS** (`.0`, `.1` …) and the OPUS **PDF** with peak labels |
| HRMS | Report of the mass-spectrometry department (**.docx**), Bruker raw data (**.d** with analysis.baf) |
| UV-Vis (ε) | **Cary** CSV/TXT exports, Cary WinUV **.DSW/.BSW** (parser from [parseuv](https://pypi.org/project/parseuv/)); several files form one data set |
| Overlay | The UV-Vis formats above, TD-DFT outputs of **ORCA** (4–6, incl. SOC) and **Gaussian**, SEC series |
| Fluorescence | Cary **Eclipse** CSV and .FBSW (excitation wavelength from the metadata) |
| CV, SEC | **Gamry** .DTA; SEC spectra from **B&W Tek BWSpec** |
| EPR | Bruker **BES3T** (.dsc/.DTA, also 2D), Magnettech MS400 text, **EasySpin** simulations |
| X-Ray | **CIF** (Olex2/SHELXL, CCDC; several `data_` blocks per file) |
| DFT | **xyz** (also trajectories), **ORCA 6** outputs (`.out`, also UTF-16), **Gaussian** `.log`, orbitals from **Molden** and **cube** files |

## Troubleshooting

- **Crash:** the details are written to `crash.log`:
  - Windows: `%LOCALAPPDATA%\Elucida`
  - macOS: `~/Library/Application Support/Elucida`
  - Linux: `~/.local/share/Elucida`

  (up to version 1.25 the folder was called `Spectravolt`, up to 1.15 `UVVisTool`; it is renamed automatically on the
  first start)
- **Self-test:** `Elucida --selftest <folder>` checks all tabs (reading, analysis, figures, SI and data export),
  and writes `selftest_report.txt`.

---

## For maintainers: building and releasing

The apps are built by GitHub Actions (`.github/workflows/build.yml`) for Windows, macOS and Linux.
After each build the finished app runs a self-test on every system.

**New version via the web interface:**

1. Upload the changed files: "Add file" → "Upload files" → "Commit changes".
2. Click **Releases** → "Create a new release" → "Choose a tag" and type e.g. `v1.0.0` → "Create new tag" → "Publish release".
3. After about 20–40 minutes the three app files are attached to the release.

**Test build without a release:** Actions → "Build Elucida" → "Run workflow". The results appear
at the bottom of the run under "Artifacts", which are deleted after 90 days.

**Local:** the build needs Node.js as well (the drawing editor is built by `tools/build_octet.py`).


```
pip install -r requirements.txt pyinstaller
python Elucida.py                      # start directly from source (or: python -m elucida)
python Elucida.py --selftest out       # self-test
python tools/build.py                  # build the app → dist/
```

**Without a GUI:** `python -m elucida.core.uvvis measurement.csv` runs the analysis with default settings.

**Files:**

| File | Content |
|---|---|
| `Elucida.py` | Start file (also the PyInstaller entry) |
| `elucida/app/` | Main window and UV-Vis (ε) tab, compound and project folders, texts, style, update check, examples |
| `elucida/core/` | UV-Vis analysis and figures, TD-DFT, solution colour, images, CDXML via RDKit |
| `elucida/tabs/` | One module per tab (synthesis, NMR, IR + EA, HRMS, CV, SEC, EPR, X-ray, DFT, overlay, fluorescence) |
| `elucida/formats/` | ChemDraw drawing, OLE objects for Word, reader for Cary .DSW/.BSW/.FBSW (from parseuv, BSD-3-Clause) |
| `elucida/si/` | SI lines and Word writer, Excel report |
| `elucida/exchange/` | Measurement data packages (ZIP) |
| `elucida/selftest.py` | Self-test (also runs in the built app) |
| `tools/` | Build, release notes, icon, README screenshots |

**Data protection:** `.gitignore` excludes CSV, HEIC and CDXML files so that no unpublished
measurement data ends up in the repository.

## License

Elucida is licensed under the **GNU Affero General Public License v3.0** (see `LICENSE`).
It comes without any warranty.

The app bundles the following libraries under their own licenses:
PySide6/Qt (LGPL-3.0), PyMuPDF (AGPL-3.0), RDKit (BSD-3-Clause), matplotlib (Matplotlib License),
NumPy (BSD-3-Clause), Pillow (MIT-CMU), pillow-heif (BSD-3-Clause, contains libheif, LGPL-3.0),
OpenCV (Apache-2.0), ONNX Runtime (MIT), PyYAML (MIT), olefile (BSD-2-Clause), openpyxl (MIT), PyObjC on macOS (MIT).
The drawing editor is [Octet Draw](https://github.com/SamChemMan/Octet-Draw) (© Sam Ellis and contributors, Apache-2.0,
modified, see `frontend/octet/UPSTREAM.md`) with OPSIN (MIT), Indigo (Apache-2.0) and further components listed in
`frontend/octet/THIRD_PARTY.md` and `frontend/octet/licenses/`; it runs in Qt WebEngine/Chromium (LGPL-3.0 and others).
The reader for .DSW/.BSW files in `parseuv_lite/` is taken from parseuv 1.0.4
(© 2026 Ricardo J. Fernández-Terán, BSD-3-Clause, see `parseuv_lite/LICENSE`).
The ISNet model for background removal (Apache-2.0) is downloaded on first use from the
rembg project and is not part of this repository.
