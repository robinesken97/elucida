**English** | [Deutsch](CHANGELOG.de.md)

# Changelog

## 1.1.0 – 2026-11-12

### New
- **EPR: choice of baseline.** Besides the polynomial there are "Smooth" (follows a broad background, keeps narrow
  lines, needs no dark spectrum; the only value is the width) and "Spline" (through the means of the signal-free
  ranges). The methods text and the exported spectra state the method.
- **EPR: isothermal decays and Arrhenius.** Against time, a first-order decay is fitted per temperature (k with 95 %
  interval, optionally only the initial phase via "Fit up to loss"); the view "1/T (Arrhenius)" gives E_a and ln A.
  Temperatures are read from the measurement file.
- **EPR: joint fit of several S = ½ species.** "Fit together" refines all simulations of one measurement at once.

### Changed
- Fields with "auto" or "off" (all tabs): a symbol in the field resets with one click; a cleared field counts as
  "auto"/"off" too.
- EPR: view and settings of the intensity evaluation sit in one card with a single view selector.
- EPR: "Use this dark spectrum for all measurements" hides the dark spectrum itself in the figure; its check box in
  the list shows it again.

### Fixed
- With very dense, noisy curves the legend was placed on top of the curves; it now moves beside the axis as intended.

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
