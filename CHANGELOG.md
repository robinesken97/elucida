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
- **CV: diffusion coefficient** from the Randles–Ševčík slope (with number of electrons, electrode area, concentration
  and temperature; interval from the uncertainty of the slope).
- **EPR: joint fit of several S = ½ species.** "Fit together" refines all simulations of one measurement at once.

### Changed
- Fields with "auto" or "off" (all tabs): a symbol in the field resets with one click; a cleared field counts as
  "auto"/"off" too.
- EPR: view and settings of the intensity evaluation sit in one card with a single view selector.
- EPR: "Use this dark spectrum for all measurements" hides the dark spectrum itself in the figure; its check box in
  the list shows it again.

### Fixed
From a check of all calculations against the literature (formulas, constants and statistics were correct; these points
were not):
- **EPR, decay under a temperature ramp:** the integral was evaluated at the measured points only; with few spectra
  (10 K apart) E_a came out about 1.4 % too high. The temperature is now interpolated between the spectra. Values from
  densely measured ramps practically do not change.
- **EPR, g after a changed field calibration:** a g fitted before the calibration is no longer reported until it is
  fitted again (a shift of 0.1 mT corresponds to 6 · 10⁻⁴ in g).
- **EPR:** couplings in MHz with µ_B/h instead of a rounded factor (matters only from about 400 MHz in the 2nd decimal).
- **CV:** the charging-current step at the switching point no longer depends on which branch the vertex sample belongs to.
- **DFT, Gaussian:** for MP2, double hybrids and CCSD(T) the total energy including correlation is read, not only the
  SCF part. ORCA was not affected.
- **Molar mass:** drawing, scheme and MS report now use the same atomic weights (IUPAC 2021) as elemental analysis and
  typed formulas; the second decimal could differ before.
- **Rounding:** ε, equivalents and yields round half up at an exact 5 in the last place, like λ and Excel.
- **Excel report:** an error below half a unit shows "1" as in the app, not "0".
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
