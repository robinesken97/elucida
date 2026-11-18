**English** | [Deutsch](CHANGELOG.de.md)

# Changelog

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
