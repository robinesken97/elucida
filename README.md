**English** | [Deutsch](README.de.md) · [Changelog](CHANGELOG.md)

# Elucida – from synthesis to SI

*Formerly **Spectravolt** (and before that **UVVisTool**). Projects, settings and downloaded data are taken over automatically.*

<p align="center"><img src="assets/icon.png" alt="Elucida" width="96"></p>

**From synthesis to SI:** evaluation and publication-ready figures for UV-Vis, NMR, IR, HRMS, fluorescence, CV, SEC,
EPR, X-ray and DFT – exported as a complete SI section in Word (synthesis with an editable ChemDraw scheme,
characterisation paragraph, spectra two per page, crystal data and DFT coordinates).

In the ε tab, Elucida determines molar absorption coefficients (ε) from UV-Vis dilution series
(Beer–Lambert: A/d vs. c) and produces publication-ready figures in the classic Origin style:
spectra, λ/ε labels at the bands, an inset with the linear regressions and R², the chemical
structure (CDXML/SVG/PDF) and a photo of the cuvette with the background removed.
The user interface is available in German and English.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/eps_dark_en.png">
    <img src="docs/screenshots/eps_light_en.png" alt="Elucida – UV-Vis (ε) tab" width="900">
  </picture>
</p>

### At a glance

| Tab | What it does |
|---|---|
| **Synthesis** | "Synthesis of …" with the ChemDraw scheme (editable ChemDraw object in Word), procedure with formatting, amount check (mmol/eq./yield against the reagent table) |
| **NMR** | Spectra from MestReNova (SVG), nucleus from the axis, NMR line from the Mnova report with assignments, structure placed automatically, Bruker parameters, two spectra per page in Word |
| **UV-Vis (ε)** | Beer–Lambert fit of dilution series → ε (or a) with confidence interval; Origin-style figure with structure and cuvette photo; Excel report; UV-Vis line for the SI |
| **UV-Vis overlay** | Measured spectra, TD-DFT (ORCA/Gaussian, SOC, triplets) and SEC series in one figure, normalised or as ε |
| **Fluorescence** | Absorption and emission, Stokes shift, photos in daylight and under UV |
| **CV** | Gamry files, E½/ΔE_p, baseline, Nicholson ratio, Randles–Ševčík with CI, reference to Fc⁺/Fc, SI text |
| **SEC** | Spectra series with potential from the potentiostat, difference spectra, apparent Nernst fit |
| **EPR** | Bruker BES3T, dark spectrum, baseline, S = ½ fit, EasySpin import, kinetics and thermal decay |
| **HRMS** | HRMS line from the mass-spectrometry report or Bruker raw data (.d): chromatogram with selectable LC range, averaged spectrum, peak by click, calculated isotope pattern |
| **IR + EA** | IR peak list from Bruker OPUS (file or PDF) and the elemental-analysis line, ready for the SI |
| **X-Ray** | CIF → rotatable ORTEP figure in the Mercury style (shaded ellipsoids, labels per atom), bond lengths/angles/torsions by click with s.u. from the CIF, crystal-data table for the SI |
| **DFT** | xyz, ORCA 6 and Gaussian outputs: renumber atoms by click or like a template (other geometry or CIF), SI block with coordinates, energies and convergence (Word, two columns) |

The tabs are ordered as in the SI: Synthesis · NMR · IR + EA · HRMS · UV-Vis (ε) · overlay · fluorescence · CV · SEC ·
EPR · X-Ray · DFT.

All exports: PDF/SVG (vector) and PNG, 16 × 11 cm by default (half an A4 page in Word). Light and dark theme;
German and English.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/synthesis_light_en.png" alt="Synthesis – scheme, procedure, amount check (invented example)"><br><sub>Synthesis – scheme, procedure, amount check (invented example)</sub></td><td width="50%" valign="top"><img src="docs/screenshots/nmr_light_en.png" alt="NMR – Mnova SVG with structure (synthetic spectrum)"><br><sub>NMR – Mnova SVG with structure (synthetic spectrum)</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/overlay_light_en.png" alt="UV-Vis overlay – measured, TD-DFT and SEC"><br><sub>UV-Vis overlay – measured, TD-DFT and SEC</sub></td><td width="50%" valign="top"><img src="docs/screenshots/fluorescence_light_en.png" alt="Fluorescence"><br><sub>Fluorescence</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/cv_light_en.png" alt="Cyclic voltammetry"><br><sub>Cyclic voltammetry</sub></td><td width="50%" valign="top"><img src="docs/screenshots/sec_light_en.png" alt="Spectroelectrochemistry – neutral, radical cation, dication"><br><sub>Spectroelectrochemistry – neutral, radical cation, dication</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/epr_light_en.png" alt="CW EPR – S = ½ fit"><br><sub>CW EPR – S = ½ fit</sub></td><td width="50%" valign="top"><img src="docs/screenshots/xray_light_en.png" alt="X-Ray – ORTEP from CIF (synthetic test structure)"><br><sub>X-Ray – ORTEP from CIF (synthetic test structure)</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/dft_light_en.png" alt="DFT – geometry and SI block (synthetic ORCA output)"><br><sub>DFT – geometry and SI block (synthetic ORCA output)</sub></td></tr>
</table>

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
download the new file and replace the old app; projects and settings are kept.

**Linux AppImage:** `chmod +x Elucida-linux-x64.AppImage` (or file properties → "Allow executing"),
then start it. It needs `fusermount` (package `fuse3`, preinstalled on most current distributions);
without it, start with `./Elucida-linux-x64.AppImage --appimage-extract-and-run`. Requires a
distribution at least as new as Ubuntu 22.04 (glibc 2.35), as does the tar.gz.

On Windows, always keep the whole `Elucida` folder together. The `.exe` does not work without the `_internal` folder next to it.

## Workflow

1. **Open data:** File → Open measurement data, or drag files onto the window. Cary CSV/TXT exports and the
   instrument's own **.DSW/.BSW** files are supported. **Several files at once** (e.g. each
   concentration measured separately) are combined into one data set.
2. **Concentrations:** Concentrations are read from the sample names, e.g.
   `ABC-1-0p5mgml_THF` → series `ABC-1`, 0.5 mg/mL. Recognised units are
   `mgml`/`mg_ml`/`mg/ml`, `mM`, `uM`/`µM`; `p` stands for the decimal point.
   - If the names contain no concentrations (e.g. `c0` … `c4`), a table opens where you enter them.
     Choose the **unit** explicitly (mM, µM, mg/mL, M) – nothing is pre-selected.
   - "Fill dilution series" fills the selected rows (or all of them) with start, start/factor, … from top to bottom.
     The start value always belongs to the **top** selected row (usually the stock solution).
   - Samples without a value, e.g. a blank, are ignored.
   - The "Series" column lets you split several compounds within one file.
   - You can change the values later with the **Concentrations…** button.
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
   **"Find shoulders automatically"** adds shoulders (in the figure optionally marked "(sh)").
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
     "Reset display to defaults" next to "Reset view" (style, ellipsoids, bond thickness, labels, hidden atoms …).
   - **Hover** over the spectra: the status bar shows λ and A of the nearest data point (and its
     concentration), marked with a red circle in the preview only – handy to check the data.
     **Double-click** a point to add its wavelength as a band; double-click it again to remove it.
     The overlay and fluorescence tabs show λ and the plotted value the same way.
6. **Export:** File → Export (or the button). This writes the chosen formats (PDF/SVG/PNG),
   `<series>_results.csv` and the Excel report for **all** series into the project (see below).

## Appearance

The program follows the system's light or dark mode; **Format → Appearance** switches to light or dark permanently.
Rarely used options in the ε tab are collapsed; a section header in bold with **"(changed)"** means that a value
there differs from the default (e.g. min. R² for the figure). The figures are not affected by the theme.

## Compound of the project

A project usually stands for **one compound** (or one comparison). **Compound …** in the toolbar sets its name/sample
number, the ChemDraw file, formula and molar mass (taken from the CDXML, isotopes such as D included, editable). This is
the default for the ε tab (structure, molar mass), the fluorescence tab and IR + MS; tabs that already have their own
structure or molar mass keep it. The name appears in the window title. The melting point entered there starts the
characterisation paragraph of the SI section.

## Synthesis tab

"Synthesis of **Name**" (the name defaults to the compound or project), the reaction scheme and the procedure, exported
to Word or as part of the SI section.

- **Scheme:** choose the CDXML. Next to it (same name, same folder) you can save from ChemDraw: **SVG/PDF** (picture
  taken unchanged), **.cdx** (the scheme becomes an editable ChemDraw object in Word – double-click opens ChemDraw; Word
  cannot do this with a CDXML) and **.emf** (sharp vector preview of that object). Without an SVG/PDF the scheme is drawn
  from the CDXML coordinates, including arrow and conditions.
- **Procedure** with bold, italic, sub- and superscript.
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
- **Word:** two spectra per page, "Figure Sn: ¹H NMR (500 MHz, CDCl₃, 298 K) of **Name**."

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
- Old projects: the MS data of the former IR + MS tab are taken over automatically.

## IR + EA tab

- **IR:** load a Bruker **OPUS** file (`*.0`, spectrum) and/or the **OPUS PDF** print-out (peak labels). With the PDF the
  values are exactly the OPUS peak list; with the file alone Elucida picks the bands itself (adjustable
  sensitivity). Range freely selectable (default: the whole measured range); untick bands that should not be listed;
  intensities w/m/s/br optional. Output: **IR** [cm⁻¹]: ṽ = 2961, 2866, … (integers, descending).
- **HRMS:** load the **Word report** of the mass-spectrometry department; formula, ionisation, polarity and the measured
  m/z (from the embedded spectra) are read out. The formula comes from the project's compound (warning if the report
  says something else), the ion is selectable ([M+H]⁺, [M+Na]⁺, [M]⁺, [M−H]⁻ …), and the closest measured m/z is
  preselected. calc. includes the electron mass; four decimals: **HR-MS-ESI(+)** calc. C₁₈H₂₁N₂⁺ [M+H]⁺ 265.1699;
  found 265.1703. The deviation in ppm is shown for checking (found − calc). The formula is checked against the
  **ChemDraw object embedded in the report**; without a project compound, **Take the compound from the MS report**
  sets name, formula and molar mass from it (the drawing is then an RDKit substitute – use your own CDXML for figures).
- **HRMS from raw data:** alternatively (or in addition) load the Bruker **measurement folder** (`.d`, e.g. timsTOF;
  button or drag & drop). Elucida reads the instrument's line spectra itself (no Bruker software needed, also on
  macOS) and averages the ion over the **LC peak** (automatic: contiguous scans with ≥ 50 % of the maximum, or a
  chosen RT range). found = intensity-weighted mean; the number of scans, the range of the single scans and their
  scatter (± mDa/ppm) are shown, because single scans can differ in the 4th decimal. With a report loaded its value
  stays preselected and the raw-data mean is selectable. Only `analysis.baf` and `analysis.sqlite` are copied into the
  project.
- **Elemental analysis:** formula from the project's compound, optionally plus a solvate (`0.5 CH2Cl2`, several
  separated by commas); calculated values with conventional mean atomic masses, enter the found C/H/N/S values.
  Deviations above 0.4 % are flagged (the usual limit of the journals). Output: **Elemental analysis** calcd (%) for
  C₁₈H₂₀N₂: C 81.78, H 7.63, N 10.60; found: C 81.52, H 7.70, N 10.41.
- **Copy to clipboard** keeps bold, sub- and superscripts when pasting into Word. Export writes the spectrum figure
  and `…_SI.txt` with all lines.

## SI section (Word)

**SI (Word)** in the toolbar (or **File → Export SI section (Word) …**) asks which parts to include
(characterisation, NMR spectra, figures of all tabs, X-ray, DFT) and collects everything that is ready for the project's compound into
`exports/si/<compound>_SI.docx`, in the style of the SI: one characterisation paragraph **m.p. …; IR …; HR-MS …;
UV-Vis …; Elemental analysis …** (melting point from **Compound …**, UV-Vis line from the **SI line** page of the
UV-Vis (ε) tab: *λ*_max: 331 nm (*ε* = 8440 cm⁻¹ M⁻¹), … with bands as in the figure, ascending, ε rounded to the
precision of its standard error), followed by the crystal-data table, the selected parameters and the captions of the
X-Ray tab and the DFT calculations (two columns). Parts that are still missing are listed after the export. Numbers
and units are joined by non-breaking spaces, so Word never separates "298 nm" or "ε = 8440".

**Figures:** the figures of all tabs with data (UV-Vis (ε) per series, IR, HR-MS, overlay, fluorescence, CV, SEC, EPR)
and the NMR spectra always come **two per page**; where figure and caption would not fit, both figures of the page are
scaled down (aspect ratio kept). Captions follow the SI: UV-Vis "UV-Vis spectra of **X** in THF, measured in 0.1 cm
quartz cuvettes." (solvent under Analysis in the ε tab); CV, SEC and EPR take scan rate, iR compensation, reference,
potential range, band, g and couplings from the data and concentration, solvent, electrolyte or species from the
**Figure caption (SI export)** box of the tab. **Setup text (SI) …** next to "Copy SI text" stores your general
instrument/setup paragraph on this computer only (not in the project, not in the repository); it is placed before the
figures of that tab. Word files open in normal mode (Word 2013+).

**SI text on the fits:** every tab that fits something (UV-Vis (ε), CV, SEC, EPR) has a **Copy SI text** button: an
English methods paragraph describing exactly the evaluation steps used, with their settings (e.g. ε: baseline window,
OLS model, cut-off, SE/95% CI; EPR: baseline polynomial, field calibration, S = 1/2 fit, kinetics), to append to the
setup paragraph of the matching SI section, followed by the results. The same text is written as `…_methods.txt` on
export, and **SI (Word)** can add all of them as a section "Data processing and fitting" (one paragraph per technique)
behind the figures – so it is documented how the raw data were processed.

**Font of the Word exports:** selectable in the SI (Word) dialog (default Arial as in the group's SI) and used for all
Word exports. The size stays 11 pt, because "two figures per page" is calculated with this line height.

## X-Ray tab

- Load one or more **CIF** files (button or drag & drop); each `data_` block with atoms becomes one entry (one
  column in the tables). Elucida reads the CIF itself (cell, coordinates, U_iso/U_ij, occupancy, PART, symmetry
  operations, `_geom_bond`/`_geom_angle`/`_geom_torsion`); no extra software needed.
- **ORTEP figure in the Mercury style:** shaded displacement ellipsoids at 50 % probability (adjustable), projected
  exactly, with the principal ellipses; H atoms as small shaded spheres, plain labels (draggable). Alternatively a
  flat Olex2 style with bold labels. Single atoms (e.g. individual H) can be hidden and labels switched **per atom**
  (atom list or double-click on the atom). **Drag to rotate**,
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
  `…_tables.xlsx`. The label size can be set per tab.

## DFT tab

- Load **xyz** files (also trajectories; the last frame is shown) or outputs of **ORCA 6** (`.out`) and **Gaussian**
  (`.log`). Files written by a PowerShell redirect (UTF-16) are recognised. Figure and mouse as in the X-Ray tab.
- **Renumber:** press **Number atoms** and click the atoms in the desired order; **Apply** puts them in front, the
  remaining atoms keep their order (optionally H atoms right after their atom). **Save xyz** writes a new file with the
  lines unchanged (only reordered); the loaded file is never overwritten. Counting from 0 (ORCA) can be shown.
- **Like template:** takes over the numbering of another geometry in the tab or of a crystal structure in the X-Ray
  tab (then with the CIF atom names, e.g. C1, H3A). Heavy atoms are matched by connectivity, symmetric molecules by
  the smallest deviation after superposition; an equally good alternative is reported with the atoms concerned, H
  atoms follow their neighbour atom.
- **Calculation for the SI** (ORCA 6, Gaussian): name, figure, charge/multiplicity/point group, Cartesian coordinates
  and E_el/H/G (ZPE column optional), optionally the input line (per structure or once as "Computational details"),
  the convergence table of the last cycle and the frequency result. All values exactly as in the output. The program
  warns about aborted runs, non-converged optimisations and imaginary frequencies; with CPCM only the dielectric
  contribution is given (a solvation energy needs the gas-phase calculation). **Copy SI text**, **Save Word** (two
  columns) or via the SI section.

## Projects, export, undo

Every export from the Overlay, Fluorescence, CV, SEC and EPR tabs also writes `…_data.csv` with exactly the
plotted curves (one x/y column pair per curve, values without stacking offset) – for Origin, Excel or MATLAB.

Everything happens in a **project folder** (the folder button in the toolbar opens it in Finder, Explorer or the file
manager of your Linux desktop):

1. **File → New project…** – choose a folder or create a new one in the dialog.
2. Load measurements, structures, photos and TD-DFT files from anywhere – they are **copied into the
   project** (`data/`, `images/`; ChemDraw exports with the same name as a CDXML come along).
   Files that are already inside the project are not copied again.
3. Work as usual – the project is **saved automatically**. A backup `project.uvvis.bak` is made each
   time a project is opened.
4. **Export** writes directly into the project (existing files are overwritten):

```
MyProject/
  project.uvvis               settings (paths relative to the folder)
  data/  images/              copies of all input files
  exports/epsilon/<series>/   figures (PDF/SVG/PNG), <series>_results.csv, <series>_report.xlsx
  exports/overlay/            <project>_overlay.*
  exports/fluorescence/       <project>_fluorescence.*
```

The program starts without a project. Open projects via **File → Open project**, **Recent projects**
or by dragging the folder onto the window. **File → Save project copy** writes a complete copy (e.g.
an intermediate state). **Edit → Undo / Redo** (⌘Z / ⌘⇧Z, Ctrl+Z / Ctrl+Y) covers all tabs.

## Excel report

For every series, `<series>_report.xlsx` contains:

- **Summary:** parameters (unit, molar mass, path length, cutoffs, baseline window and per-sample
  offsets), results of all bands (slope, intercept, standard errors, R², ε ± SE, **95 % confidence
  interval** from the t-distribution) and the method with all equations.
- **Spectra:** A(λ) of all samples, baseline-corrected and raw, with chart.
- **One sheet per band:** data points, "in fit" flag (1/0, editable), the complete regression as
  **Excel formulas** (x̄, ȳ, Sxx, Sxy, m, b, RSS, s, SE, R², ε, t, CI) next to the tool's values with
  their difference, residuals and a chart (A/d vs c with regression line).

Blue numbers are measured values or tool results, black cells are formulas. Changing a flag in "in
fit" recalculates the band in Excel.

## UV-Vis overlay tab

Compare several spectra in one figure, measured and calculated:

- **Measurement…** adds spectra from CSV/TXT/DSW/BSW files (one entry per sample);
  **TD-DFT…** adds ORCA (4–6) or Gaussian output files.
- **SEC…** takes spectra from the SEC tab, e.g. to compare a reduction or oxidation with the isolated UV-Vis
  spectrum and TD-DFT. As a **series** (all spectra or only start and end, range by potential) everything is
  normalised with **one common factor** to the start spectrum, so intensity ratios and isosbestic points are kept;
  intermediate spectra grey, start blue, end red, legend with the potentials. **Single spectra** are normalised each on
  their own (shape comparison). SEC is never shown as ε: path length and converted concentration in the thin-layer
  cell are not known exactly.
- TD-DFT transitions are broadened with Gaussians in energy (FWHM and an empirical energy shift
  can be set per calculation, default 0.3 eV); ε follows from the oscillator strengths
  (ε(ν̃) = 1.306·10⁸ · Σ f/σ · exp(−((ν̃−ν̃ᵢ)/σ)²), as in GaussView). Transitions can be shown as sticks.
- **y axis** ("Normalise" checkbox): *normalised to band* – every spectrum is scaled to its maximum within the
  normalisation range (globally or per spectrum, e.g. if the calculated band is shifted), or
  **ε [10³ M⁻¹ cm⁻¹]** – measured spectra then need concentration (and molar mass for mg/mL) and
  path length.
- Per spectrum: colour, name, **line style and width**, **scale factor and vertical offset**
  (e.g. for stacked spectra); **order** with ↑/↓ (also the legend order).
- ORCA calculations with **spin–orbit coupling**: choose "with SOC" or "without SOC" per calculation.
- **Triplet states** (without SOC, f = 0) can be marked as dashed marks of fixed height; they do not
  contribute to the curve (ORCA 4–6, Gaussian).
- **Combine** calculations: select two or more TD-DFT entries (Ctrl/Shift click) → "Combine". The
  transitions are merged and then broadened together; one weight per calculation (default 1 = sum,
  e.g. 0.7/0.3 for conformers). Calculations should be at the same level of theory; identical states in
  both calculations trigger a warning (they would be counted twice).
- **TD-DFT normalisation:** curve and sticks always share one scale factor (each stick is the height
  of its own Gaussian, the curve is their sum). Reference: "curve maximum = 1" or "strongest
  transition = 1"; alternatively the sticks show the oscillator strength f on a right axis.
- A **structure per spectrum**, optionally drawn in the curve colour.
- Structure with adjustable size; the legend is placed in free space and can be dragged.
- **Stacked** (as usual in papers): curves are offset vertically by a common spacing in list order
  (top of the list = top curve). "Same stacking level as the curve above" keeps e.g. a TD-DFT curve
  on the level of its measurement. The **y axis** can be shown with numbers, without numbers and
  ticks (default when stacked – offset curves make the numbers misleading) or hidden. Optionally
  the **names are written at the curves** instead of a legend, and a dashed zero line marks each level.

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
  adjustable (default 0.15 V), baselines optionally in the figure. Peak potentials are unchanged. If the window has too
  little current before the peak, this is flagged and the measurement is left out of the regressions.
- From 3 scan rates per group and couple: regression of **i_p vs. √v** (Randles–Ševčík) and **log i_p vs. log v**
  (slope 0.5 = diffusion-controlled, 1 = adsorbed), each with a **95% confidence interval**.
- **Copy SI text:** English paragraph on the data evaluation (referencing, peak determination, baseline, Nicholson,
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
  √v with fit lines from 3 scan rates), **diffusion** (log |i_p| vs. log v), **chemical reversibility** (i_r/i_f after
  Nicholson vs. v, line at 1) or **trumpet plot** (E_pa and E_pc vs. log v), one series per group. Note: ΔE_p also
  contains the iR drop (especially in THF); the trumpet plot is drawn without a k⁰ analysis, which would need
  several decades of scan rate.
- Current as recorded (Gamry: IUPAC, anodic positive) or inverted; optionally as current density.
- Export: figure (PDF/SVG/PNG), `…_results.csv` with all values (incl. group, reference offset, the iR
  compensation entry of the Gamry file, currents with/without baseline and the charging-current step) and
  `…_methods.txt` (SI text).

## SEC tab (spectroelectrochemistry)

- Reads a **spectral series from B&W Tek BWSpec** text exports (wavelengths from the calibration coefficients
  in the file) and the **Gamry .DTA** file of the potential scan. Each spectrum gets its potential via the
  clock time (spectrum time − start of the Gamry run, plus an adjustable time offset).
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
- Potential axis as measured, shifted by E(Fc⁺/Fc) or with the referencing of the CV tab.

## EPR tab (CW EPR)

- Reads **Bruker BES3T** (.dsc + .DTA, e.g. Magnettech ESR5000/ESRStudio, Elexsys; 2D files give one spectrum
  per row) and **two-column text** (Magnettech MS400 export; microwave frequency from file names like
  `…-9p404368-…`). Frequency, temperature, modulation and power are shown per spectrum.
- **Dark spectrum:** the measurement before irradiation can be subtracted from each spectrum (light − k·dark,
  interpolated onto the same field grid); a warning appears if frequency, modulation or power differ.
- **Processing:** polynomial baseline (order 0–5) from the outer edges of the sweep or from chosen signal-free
  ranges, hide field ranges (e.g. the sharp radical signal), moving-average smoothing.
- **EasySpin simulations** as two-column text (B in mT, intensity), e.g. `writematrix([B(:) spc(:)], 'sim.txt',
  'Delimiter', '\t')`; scaled by least squares to a measurement (or by hand) and shifted in field; drawn dashed on
  the same level. A **parameter file** (the MATLAB lines `Sys.D = [D E]; …`) is shown with D and |E| converted to
  cm⁻¹ and can be written into the figure.
- Display in mT or G, overlaid or stacked, normalised, y axis without numbers by default, free labels such as
  `Z⁻@122, Y⁺@400`. Hover shows B, the g value and the intensity.
- **Several species:** all simulations assigned to a measurement (EasySpin or own S = ½) are scaled *together* by
  linear least squares; the fractions (double integral) are shown, optionally the sum and the residual
  (measured − sum) – i.e. subtraction of individual species. Non-linear parameters (g, A, D/E, linewidths of
  powder spectra) are fitted in EasySpin; the tool only determines the fractions.
- **Own isotropic S = ½ simulation and fit** (solution, first order): g, groups of equivalent nuclei (e.g.
  `2 14N 0.65; 4 1H 0.32`, a in mT), peak-to-peak linewidth and Lorentzian fraction; "Fit" refines g, a and
  ΔB_pp (Levenberg–Marquardt after a coarse grid search, amplitude linear).
- **Field calibration with TEMPO** (or another reference): fit the reference with an S = ½ simulation, choose it as
  calibration with its literature g (default 2.0055, TEMPO in MeCN); ΔB = B(g_fit) − B(g_lit) is subtracted from all
  other measurements, whose fits then give calibrated g values.
- **Intensity vs. time or temperature** (e.g. illumination kinetics, thermal decay): double integral or
  peak-to-peak in a field window for every visible measurement (after dark spectrum and baseline), optionally
  × T (Curie), normalised; time counts from the earliest spectrum in the tab (e.g. the dark spectrum). "Use this
  dark spectrum for all measurements" sets the background for a whole series at once.
- **Thermal decay at constant heating rate** (port of the group's MATLAB script): intensity per spectrum as
  peak-to-peak, double integral or **Gaussian + line fitted to a feature** (e.g. the X feature at 487 mT), × T,
  field scaled to a reference frequency (e.g. 9.3 GHz) and a temperature correction (e.g. −1.5 K); then
  **E_a and A** from I(T) = exp(−A·∫exp(−E_a/RT)/β dT) with β from the mean temperature and time steps.
  Objective least squares (default; reliable 95 % interval with t quantile) or "as script" (√|r|, for comparison
  with old numbers – sensitive to the optimiser, its interval strongly underestimates the uncertainty). E_a and ln A are almost fully correlated.
- **Export for EasySpin:** besides the figure, every measurement is written as a two-column text file (B in mT,
  intensity) in full resolution after dark spectrum, baseline and smoothing – without normalisation or hidden
  ranges – with `%` header lines documenting frequency, temperature and processing (`load(...)` in MATLAB, ready
  for `esfit`). The intensity series is saved as `…_intensity.csv`.

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

Format → "Fonts and frames…" applies to **all tabs** (default) or **only to the open tab** ("Applies to"), is saved
with the project and shows only what the open tab has in its figure (e.g. no symbol font in CV, no frames in X-Ray):

- **Text font** and **symbol font**. By default λ and ε are set in the symbol font (Times New Roman),
  as in Origin; this can be switched off.
- **Band labels:** font size (automatic by default), bold, italic, colour.
- **Frames:** closed frame around the plot (top and right too; default since 1.24, like the Origin figures) and a
  rounded frame around the chemical structure.

## What happens automatically during the analysis

- **Baseline** ("automatic (series)", default): the window is placed where the most concentrated
  sample absorbs least. Only the part of the window value that does *not* scale with concentration
  (instrument/cuvette offset) is subtracted. A residual proportional to c is treated as real
  absorption and kept. "automatic (simple)" subtracts the full window value. The baseline always
  uses the full data range, independent of the displayed λ range.
- **Fit cutoff:** points above the cutoff (default A = 1.0) are excluded from the fit.
- **Bands:** found automatically within the displayed λ range, or entered as a list.
- **Rounding:** ε (M⁻¹ cm⁻¹) is never shown with decimals; it is rounded to the precision its
  standard error supports. The results CSV keeps the full values.
- **Warnings** (results table and log): fewer than 4 fit points, significant intercept (> 2σ),
  R² below the threshold (default 0.98, adjustable under Analysis → "min. R² for figure"; 0 = show
  all; the band stays in the table – R² cell marked red –, CSV and Excel report but is not shown in the
  figure), fewer than 3 points (then no ε at all). With 4 points, R² alone says little: check the
  95 % confidence interval in the Excel report before lowering the threshold.

## Notes on CDXML

- Exact ChemDraw appearance: put an SVG/PDF/PNG export with the same name next to the CDXML (see
  above). Otherwise Elucida draws the structure itself from the CDXML coordinates: bonds, labels as written
  (abbreviations such as TMS or Dipp stay), arrows and texts of reaction schemes; the font is Helvetica (same metrics
  as Arial). Only if the file contains something this drawing cannot show (embedded pictures, brackets, curved
  arrows …) RDKit redraws it, with a note.
- Molar mass = sum of all fragments (counter-ions are included).
- If abbreviations such as Dipp or Mes cannot be resolved, **no** molar mass is set and a warning is
  shown. Please enter it by hand in that case.
- Binary `.cdx` files are not supported. Save them as `.cdxml` in ChemDraw.

## Supported data

- **Cary CSV/TXT exports** (Agilent Cary 60 and others): first row = sample names, second row =
  `Wavelength (nm),Abs` per sample, followed by the data. Decimal comma and point are both
  recognised, and the instrument metadata at the end of the file is ignored. Simple two-column
  files work too; the file name is then used as the sample name.
- **Cary WinUV .DSW / .BSW** (binary files from the instrument software), read with the parser
  from the open-source project [parseuv](https://pypi.org/project/parseuv/). Instrument baseline
  records ("Baseline 100%T/0%T") in batch files are skipped.
- **Cary Eclipse** fluorescence data: CSV export and .FBSW files. The excitation wavelength is
  taken from the file's metadata.
- **CIF** (crystal structures, e.g. from Olex2/SHELXL): own reader, several `data_` blocks per file.
- **xyz**, **ORCA 6** outputs (`.out`, also UTF-16) and **Gaussian** outputs (`.log`) for the DFT tab.
- **Several files** can be opened together; they form one data set.

## Troubleshooting

- **Crash:** the details are written to `crash.log`:
  - Windows: `%LOCALAPPDATA%\Elucida`
  - macOS: `~/Library/Application Support/Elucida`
  - Linux: `~/.local/share/Elucida`

  (up to version 1.25 the folder was called `Spectravolt`, up to 1.15 `UVVisTool`; it is renamed automatically on the
  first start)
- **Self-test:** `Elucida --selftest <folder>` checks reading, CDXML, background removal and export,
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

**Local:**

```
pip install -r requirements.txt pyinstaller
python uvvis_gui.py                    # start directly from source
python uvvis_gui.py --selftest out     # self-test
python build.py                        # build the app -> dist/
```

**Without a GUI:** `python uvvis_core.py measurement.csv` runs the analysis with default settings.

**Files:**

| File | Content |
|---|---|
| `uvvis_gui.py` | User interface (PySide6), self-test |
| `uvvis_core.py` | Import, baseline, band search, fits, plot layout, export |
| `uvvis_images.py` | Images, HEIC, background removal (ISNet/ONNX, GrabCut), SVG/PDF embedding |
| `uvvis_chem.py` | CDXML: drawing and molar mass (RDKit) |
| `uvvis_i18n.py` | German/English texts |
| `uvvis_tabs.py` | Overlay and fluorescence tabs |
| `uvvis_extra.py` | TD-DFT reading/broadening, photo pair, figure for the extra tabs |
| `uvvis_project.py` | Project folders (save/load, copying input files) |
| `uvvis_report.py` | Excel report (openpyxl) |
| `parseuv_lite/` | Reader for Cary .DSW/.BSW/.FBSW (from parseuv, BSD-3-Clause) |

**Data protection:** `.gitignore` excludes CSV, HEIC and CDXML files so that no unpublished
measurement data ends up in the repository.

## License

Elucida is licensed under the **GNU Affero General Public License v3.0** (see `LICENSE`).
It comes without any warranty.

The app bundles the following libraries under their own licenses:
PySide6/Qt (LGPL-3.0), PyMuPDF (AGPL-3.0), RDKit (BSD-3-Clause), matplotlib (Matplotlib License),
NumPy (BSD-3-Clause), Pillow (MIT-CMU), pillow-heif (BSD-3-Clause, contains libheif, LGPL-3.0),
OpenCV (Apache-2.0), ONNX Runtime (MIT), PyYAML (MIT), olefile (BSD-2-Clause), openpyxl (MIT).
The reader for .DSW/.BSW files in `parseuv_lite/` is taken from parseuv 1.0.4
(© 2026 Ricardo J. Fernández-Terán, BSD-3-Clause, see `parseuv_lite/LICENSE`).
The ISNet model for background removal (Apache-2.0) is downloaded on first use from the
rembg project and is not part of this repository.
