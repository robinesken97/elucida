**English** | [Deutsch](CHANGELOG.de.md)

# Changelog

## 1.1.0 – 2026-11-12

### New
- **X-ray: comparison with a calculated geometry.** In the step "Evaluation", a geometry from the DFT tab or a file
  (xyz, ORCA or Gaussian output) is assigned to the crystal structure via the bond network only (same formula, same
  connectivity of the heavy atoms, same number of H per atom; never by distance or order). Among symmetry-equivalent
  assignments the one with the smallest heavy-atom RMSD after superposition is used and the RMSD is shown; if equally
  good assignments give different values, the parameters are named. Different composition or connectivity is refused
  with the atoms that do not match; with solvent or counter-ions the fragment is chosen. The assignment is shown as a
  table and stored with the compound. The table of selected parameters gets a column with the calculated value (bond
  lengths 3, angles 1 decimal, no s.u.), optionally Δ = calc. − X-ray, in the app, Excel/CSV and Word; the header names
  the level of theory, a note states the geometry (gas phase or solvated) and the RMSD.
- **Project page: Comparison.** Any number of named comparisons across the compounds of a project: a CV stack (one
  voltammogram per compound, peak potential at the peak, structure beside the curve, scan arrow per curve; other
  reference scales are refused, never converted), UV-Vis and emission spectra in one figure, and a property table
  (values from the tabs, own quantities and further compounds, group headers, overwritten cells marked, transposable; Word, Excel,
  CSV, rich-text copy). Nothing is evaluated again: each compound writes a small snapshot of its tabs on saving;
  outdated or missing snapshots are shown and renewed with "Refresh". The example project contains a spectra
  comparison and a table.
  Comparisons can go into the combined SI (figure or table with continued numbering, chapter by kind or an own
  heading); the CV stack shows any of the first ten cycles per compound (peak numbers only for the evaluated one); the
  table takes X-ray parameters, space group and crystal system, DFT energies and HOMO/LUMO, and IR bands or NMR shifts
  nearest a target within a tolerance; spectra include IR and EPR (field axis only at one microwave frequency or scaled
  to a reference, or a g axis); undo and redo work in the open comparison. The spectra comparison and the CV stack
  show the structure of each compound in the figure, by default in the colour of its curve (can be switched off, or
  black): at the highest point of its own curve, stacked on the right above its own baseline.
- **Structures at equal size:** several structures in one figure (comparison, UV-Vis overlay) always share the same
  drawing scale (equal bond length, whatever the ChemDraw style). The size applies to the widest one; the mouse wheel
  on one structure changes all.
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
- **Energy profile with multireference levels.** CASSCF/NEVPT2/SORCI calculations (single point or the calculation
  itself) are no longer left out: per level, **Method** and **State** choose the state energy (default: highest level
  of theory in the file, root 0); the caption names method and root. Without an own frequency calculation the level
  shows its electronic energy, with a note.
- **Overlay: SORCI spectra** can be chosen like the other excited-state methods, if the output prints an absorption
  table for the final DDCI3 step.
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
  the CV); the README screenshots show the tabs with these data. The project now also contains a reaction path
  (four species with a transition state) under Computational Chemistry and a CASSCF/NEVPT2 calculation of the product
  for the DFT page "Multireference".
- **CV:** curves no longer run into the frame: with an automatic range a narrow margin stays left and right (CV tab
  and CV stack).
- **Consistent interface:** lists of measurements size their columns by content (no clipped name next to an empty
  column, no number touching the next); the selected parameters in X-Ray and the figures in "Other" are tables like
  everywhere else; multi-line text fields indent their text like single-line fields. Icons in buttons no longer
  sit tight against the text (8 px instead of 4).
- **Uniform tables:** result tables (UV-Vis, CV, UV-Vis kinetics, H-Cell) fill the page without empty space on the
  right and never clip. What used to be lines of text below the table is a second table: the scan-rate analysis in CV
  (slope, intercept, R², log–log slope, D), course and decay per series in the kinetics tab, the summary per
  measurement in H-Cell, the isothermal decays per temperature in the EPR tab; reference and warnings stand separately below. The DFT preview "Calculation for the SI" shows
  convergence, energies and coordinates as tables in the same style (the copied text and the Word export are
  unchanged).
- **Word export:** methods texts typeset powers of ten and t½ correctly (previously literal "10^-2" and "t1/2" for
  UV-Vis kinetics, EPR decays and the diffusion coefficient, "cm2" without superscript); the caption of the energy
  profile writes kcal mol⁻¹ with a superscript. The property table of a comparison fills the page again.

### Fixed
From a check of all calculations against the literature (formulas, constants and statistics were correct; these points
were not):
- **EPR, field unit of text files:** if the header did not state the unit, it was guessed silently (field values
  above 1500 = gauss); W-band data in mT or a low-field section in G were off by a factor of 10. The assumption is
  now shown with the measurement and can be confirmed or changed under "Field unit of the file".
- **EPR, nuclei:** ⁶Li, ⁷Li, ⁹Be, ¹⁰B, ¹¹B, ²³Na, ²⁷Al and further isotopes up to ²⁰⁹Bi were missing from the table;
  "I=3/2" (spin as a fraction) is read now.
- **EPR captions** of the views intensity against time/temperature/number and Arrhenius said "EPR spectra of …";
  they now say what is plotted and give only values of the fits shown.
- **NICS caption:** a scan along the normal of the ring plane was described as a path at one height above the plane;
  the geometry is now taken from the ghost-atom coordinates (in-plane, along the normal, or neutral "along the scan
  path"). The side of a point (above/below, for the average of pairs) no longer depends on the arbitrary sign of the
  local plane normal.
- **Overlay:** an absorption table printed after a SORCI step was read as a TD-DFT spectrum.
- **Compound tab:** the chips "Figures from" stayed empty after a language switch.
- **Project page:** the buttons "SI texts …", "General procedures" and "Show in folder" next to the tabs were invisible
  (height 0); the line above the tabs was broken and offset at that position and is gone. Header, tabs and all pages
  now start at the same left and right edge, the vertical distances follow one grid. The compound list shows every further method
  (UV-Vis, kinetics, fluorescence, CV, SEC, H-cell, EPR, X-ray, DFT) as its own column with a dot instead of a
  truncated text; all columns are centred in one grid.
- **Window width:** the tab bar with now 16 tabs forced a minimum window width (on Windows wider than a laptop
  screen). It may now be narrower than its content: an arrow at the edge and the mouse wheel scroll it, the selected
  tab stays visible.
- **Word export:** below a longer methods text there is now one more figure as long as it stays at least 7 cm high
  (the rest of the page stayed empty before). An energy profile with a single calculation (one line at 0) is no longer
  part of the SI.
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
- Fields in the UV-Vis tab and in comparisons were 2 to 4 pixels lower than in the other tabs.
- CV: without an internal reference the card "Referencing" showed a lone dash.
- Project → Details: the German label of the dataset description was cut off.
- UV-Vis kinetics, HRMS, X-Ray: single rows were off the grid (a button alone in a row, a narrower pair of fields, a
  label in a different colour); the card "Align" had an empty strip at the bottom.

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
