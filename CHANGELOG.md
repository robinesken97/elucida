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
- **New tab H-Cell (charge–discharge cycling).** Reads Gamry "Cyclic Charge Discharge" files with their
  CHARGE_DISCHARGE step files: capacity per cycle (charge, discharge, percent of the theoretical capacity from the file
  or entered per measurement) with Coulombic efficiency on a second axis, several measurements in one figure; or
  potential against the true time for selected cycles with a broken time axis. Results per cycle, retention and mean
  efficiency as tiles, caption and methods text for the SI, CSV of the cycle table.
- **New tab "UV-Vis Kinetics".** Spectra of one solution over time (stability over days, or a reaction), from one or
  several Cary files: acquisition times from the file, a series per spectrum, spectra coloured along time or absorbance
  at λ against time (optionally the maximum within ± n nm, relative to the first spectrum), first-order fit with k,
  95 % interval and half-life.
- **SEC: "Heatmap" view.** The whole spectral series in one picture: wavelength against spectrum order, absorbance or
  ΔA to the first spectrum as colour with a colour bar; the y axis shows the potential, without potentials the time or
  the number.

### Changed
- Fields with "auto" or "off" (all tabs): a symbol in the field resets with one click; a cleared field counts as
  "auto"/"off" too.
- **CV baseline** ends 0.20 V before the peak instead of 0.15 V in new compounds: the peak current of ideally reversible
  waves comes out at most 1 % too small (1–3 % before). Saved compounds keep their value.
- **CV current density** uses the entered electrode area; without an entry that of the measurement file, with a note.
- **Amount check (synthesis)** allows only 0.01 % beyond the rounding (0.5 % before).
- **Crystal-data table** in standard notation ("Density (calc.) / g cm⁻³", "Formula weight / g mol⁻¹").
- EPR: view and settings of the intensity evaluation sit in one card with a single view selector.
- EPR: "Use this dark spectrum for all measurements" hides the dark spectrum itself in the figure; its check box in
  the list shows it again.
- Example project: the product fills every tab with coherent invented data (now also HRMS raw data with spectrum
  and chromatogram, HOMO/LUMO and a NICS scan in DFT, a figure in "Other"; H-Cell cycles around the same E½ as
  the CV); the README screenshots show the tabs with these data.

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
