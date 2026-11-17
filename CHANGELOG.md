**English** | [Deutsch](CHANGELOG.de.md)

# Changelog

## 1.3.0 – 2026-11-17

### New
- **Copy Figure (SVG).** Edit → Copy Figure (SVG), Ctrl+Shift+C (macOS ⌘⇧C): the figure of the page shown on the right,
  exactly as exported, goes on the clipboard as SVG with a PNG fallback (macOS also PDF). Pages without a figure and
  withheld NMR spectra copy nothing and say why; NMR uses the range from the field, not the zoom.
- **MNova documents through MNova.** If MNova is installed (macOS and Windows; not yet tested on a real Windows installation), a dropped `.mnova`
  is exported by MNova itself in the background from a copy (your file stays unchanged): every page with a spectrum
  becomes a spectrum (`data/nmr/mnova/<document>/<document>_<page>.svg`) and the NMR line comes from MNova's
  reports – ¹H only from the multiplet report, other nuclei from multiplets or the peak labels of the page (switch
  **SI line** per spectrum); 2D never goes into the line. Text already in the field is never replaced silently
  (**Adopt** / **Keep**). The FIDs of the document attach as raw data to the matching spectrum. Progress is shown in
  the MNova card. Without MNova, after the time limit or on an error the document is read as before, and the notice
  says why. Dropped together with SVGs, a document only adds its FIDs.
- **Drop Bruker data like in MNova.** A single file of a TopSpin experiment (fid, ser, acqus, 1r …) or its pdata
  folder can be dropped on the window too; the whole experiment above it is taken.
- **Fonts, lines and colours.** In tabs with curves the card "Fonts and Frames" is now "Fonts and Lines" (with fixed colours: "Fonts, Lines and Colours"). New
  are **Curve width** (factor on all curves, 1 × = as before) and **Axis lines** (width of axes, frame and ticks in pt,
  "auto" = as before); like the fonts they apply to all tabs or, with "This Tab Only", only here, including the UV-Vis
  (ε) tab and the fluorescence decay. Fixed colours without a measurement list can be chosen per figure: SEC (start,
  end), H-Cell (charge, discharge, CE), HRMS (measured, calculated), EPR (fit curves). Applies to preview, export and
  Word alike, is one undo step; "Reset to defaults" resets it. With the defaults all figures stay unchanged. X-ray, DFT
  and Other (molecules, foreign images) do not have these fields.
  A colour button without effect in the figure shown stays visible but greyed out; its tooltip gives the reason.
- **Project page: Export tab.** Complete SI (template, chapters, options, compounds) and datasets (compounds, data
  kinds, lab codes, options, target folder) are cards in the new tab instead of dialogs; every change applies at once and
  is remembered as before. **Complete SI (Word)** at the top stays the main button and writes right away with this
  selection, **Data packages (zip)** likewise; "Change selection …" in the message shows the tab.
- **SI selection per compound.** In the Export tab the column **SI** selects per figure what goes into the SI; the
  selection is saved with the compound (undo works) and applies to the SI section **and** the complete SI (before, the
  complete SI always contained all figures); both messages name what is deselected. A compound without its own selection
  takes the previous selection of this computer. The cards "SI Export (Word)" and "Slides (PPTX)" in the Compound tab
  are gone: parts and font are in the card "SI (Word)" of the Export tab, the slide selection is the column **Slides**.
  Plus grey buttons **SI (Word)** and **Data Package** (no dialog, with the saved selection; "Change selection …" in
  the message opens the file selection).
- **Export tab.** New last tab (group "Output"): formats (PDF, SVG, PNG, PPTX) for all figures of the compound, below
  them one row per figure or report (ε per series, fluorescence/decay, EPR spectra/hyperfine/spin density, TD-DFT/NTO,
  X-ray structure/packing/PXRD/tables, DFT geometry and orbitals per calculation/NICS/report, Other per image;
  otherwise per tab) with **Export** (writes exactly the files of that row) and the tick **Slides** (the same selection as the card "Slides
  (PPTX)"), plus **Slides (PPTX)** and **Export All** (one message for all; tabs that could not be exported are
  named; progress "Exporting 3/15 …" at the bottom right, no undo step, the view stays). The tabs no longer have their own **Export** button or formats (card "Axes and Size"); **Ctrl+E** still
  exports the figure of the open tab. "SI (Word)" moved from the toolbar to File. Older compounds take the saved
  formats of the first tab with data as the default. Comparison, reaction path and project page keep their export
  buttons and formats.
- **EPR: spin density and hyperfine couplings from ORCA.** Besides Gaussian 16, the pages "Spin Density" and
  "Hyperfine" read ORCA outputs of versions 4.0–4.2, 5.0 and 6.0 (layouts checked against real public outputs) and
  6.1 (6.0 layout with a strict check, not yet checked against a real output: the pages show a note); other versions
  are refused with a message. The pages read Mulliken spin populations (Löwdin is kept in the data), A(FC) per nucleus from
  the hyperfine block (`%eprnmr Nuclei = all H {aiso, adip} end`) and A(SD) as dipole principal values for nuclei
  without `aorb`. Without `%eprnmr` only the spin densities are read and the page "Hyperfine" names the missing input.
  With several jobs in one output the level of theory comes from the job with the hyperfine block. The methods text
  names the program and its version.
- **UV-Vis titration.** The UV-Vis kinetics tab takes equivalents per spectrum (new table column, suggested when the
  sample or file name states them unambiguously, e.g. "0.5eq") and shows two new views: the spectra against the
  equivalents of an added reagent (colour gradient in the order of the equivalents, legend with the equivalents) and the
  absorbance at a chosen wavelength against the equivalents. Isosbestic points are marked only where all spectra agree
  within an adjustable tolerance and the change reverses its sign there; otherwise none. Caption with reagent and
  isosbestic points, methods text, both figures in the SI, export `_titration.csv`. No binding constants, no dilution
  correction. The example project (S3) contains an invented titration with an oxidant.
- **Fluorescence: lifetime, photophysical properties and excitation spectrum.** The fluorescence tab reads a decay
  (and optionally an IRF) as a text file (time, counts; header lines, decimal comma and the time unit from the column
  header are recognised; instrument formats are not read yet) and fits one or two exponentials with a constant
  background: with an IRF by reconvolution over the whole decay, without from an adjustable start after the maximum.
  Counts are fitted with Poisson weights and the reduced χ² is given; lifetimes come with 95% intervals from the fit
  covariance. A new page "Decay" shows the decay on a log scale with fit, IRF and residuals, plus the parameters,
  amplitude- and intensity-weighted average lifetimes kept apart. A page "Properties" lists λabs, ε, λem, Φ, τ,
  k_r = Φ/τ and k_nr = (1 − Φ)/τ from what is available (Φ is entered, empty cells stay empty; with two exponentials
  a note names the average lifetime used). An excitation spectrum can be shown with absorption and emission. Second
  SI figure with caption, methods text and export (`_decay` figure and CSV); the example project (S3) contains an
  invented biexponential decay with IRF and an excitation spectrum.
- **SI requirements of the journals.** Compound tab: card **Purity** (¹H/¹³C NMR, qNMR, elemental analysis, HPLC, GC,
  free text) – the characterisation paragraph ends with "Purity was established by …"; a suggestion from the data is
  only offered, never set. Data packages: optional **FID for Publication** zip after the ACS guidelines (one folder per
  compound, one per NMR experiment, MolFile, acquisition parameters). Project page **Details**: labels of the combined
  SI ("Supplementary Figure 1" for Nature journals, also in references in the text) and a **Data Availability
  Statement** for the manuscript (repository, DOI, CCDC numbers of the compounds, FID package). DFT tab: page
  **Charges** with Mulliken/Löwdin charges and spin populations (ORCA, Gaussian Mulliken), SI table on request, CSV.
- **TD-DFT: natural transition orbitals (NTO).** Card "Transition Orbitals (NTO)" and page "NTO" beside
  "Excitations": per excitation the hole → particle pairs of the calculation as images with their weights. ORCA
  (`%tddft DoNTO true end`): the .nto file of the state converted to Molden with orca_2mkl; pairs and weights are taken
  from the NTO block of the TD-DFT output (matched to the state by its energy, never guessed), pairs from an adjustable
  weight (default 10%, at most four). Or two cube files of one pair (orca_plot, Gaussian cubegen): weight from the
  NTO block if the orbital numbers form a pair there, otherwise entered by hand or left out. Drawn like the orbitals of
  the DFT tab, the same view and scale for hole and particle, isovalue adjustable (default: 80% of the density);
  elongated molecules put the hole above the particle. Caption with state, energy, λ, f, weights, isovalue and level of
  theory; SI figure and export. Nothing is calculated. The example project shows S1 of S3 (invented cubes).
- **X-ray and DFT: aromaticity (HOMA).** Card "Aromaticity (HOMA)" and page "HOMA": HOMA per planar 5- to 7-membered
  ring from the bond lengths, with the parameters of Krygowski 1993 (CC, CN, CO, CP, CS, NN, NO) or, selectable, HOMAc
  (Arpa et al. 2025; CC, CN, NN, CO); EN and GEO for rings with a single bond type. Rings with a bond type without
  parameters get no value but the missing bond. Value at the ring centre on request (draggable), SI table with formula
  and citations, CSV in the export. In the DFT tab NICS(0)/NICS(1)/NICS(1)zz of the same ring from the NICS page stand
  in the same row. No s.u. for crystal structures. The example project shows both rings of S3.
- **EPR: spin density and calculated hyperfine couplings.** The EPR tab reads a Gaussian 16 output of an open-shell
  calculation (card "Calculation (DFT)" in the Data step): Mulliken spin populations per atom, isotropic Fermi contact
  couplings (MHz, G) and anisotropic dipole couplings. Two new pages beside the figure:
  "Spin Density" shows the spin density or the SOMO on the molecule (from a Molden or cube file of the same geometry,
  rendered like the orbitals of the DFT tab) with the spin populations in percent at the atoms. Percent = population /
  sum over all atoms × 100, with sign, so all atoms add up to 100%; the figure shows values from an adjustable
  threshold on, the table lists every atom. "Hyperfine" shows the calculated couplings at the nuclei next to the
  experimental ones of an own S = ½ simulation ("x MHz (exp. y MHz)"): select a group of the simulation, then click its
  nuclei in the figure. Nuclei assigned to one group are averaged with their signs and marked "avg."; the values
  stand around the molecule with an arrow to the nucleus (one arrow per methyl group), as absolute values like the
  experimental ones unless "Signs" is switched on; nothing is
  assigned automatically, and a different number of nuclei than in the simulation is pointed out. Unit MHz, G or mT;
  surface, isovalue, opacity, colours, threshold and the nuclei shown are adjustable. Both figures go into the SI
  with a caption that names isovalue and level of theory, into the export (figure plus a CSV with all atoms), and the
  methods text describes where the values come from. Other programs are refused for now, as are orbital files whose
  atoms or coordinates differ from the calculation. The example project (S3) contains an invented calculation with
  an assignment.
- **NMR: nucleus count check.** Under the signal table the NMR tab compares the NMR lines with the molecular formula
  of the compound: for ¹H the sum of the H counts, for other nuclei the number of signals against the atoms of the
  element. Fewer H (exchangeable protons) or fewer signals (symmetry, overlap) are named as possible; more than the
  formula allows, or a nucleus that the formula does not contain, is marked in the warning colour, in a small table
  and as tiles in the tab row. A note only, nothing is changed.
- **DFT: 3D NICS.** The NICS page joins Gaussian NMR outputs whose ghost atoms form a regular grid (also spread over
  many partial calculations) into one grid and shows the molecule as a ball-and-stick model with two isosurfaces,
  deshielded (default +5 ppm, red) and shielded (default −15 ppm, blue); isovalues, colours and opacity are adjustable
  and the figure can be rotated. Incomplete grids and parts with different geometries are refused. The figure goes
  into the SI with a caption naming both isovalues, the grid spacing and the level of theory; the export adds the grid
  as a cube file. The example project contains an invented grid.
- **DFT: ACID.** New page "ACID" in the DFT tab, built like 3D NICS. It shows what the AICD program (Herges) wrote:
  `Isoober.inc` and `Molekuel.inc` from the `<name>.d` folder of a run with `--povrayinput -c` (e.g.
  `AICD --povrayinput -c -m 2 -s -b 0 0 1 calc.log`). The isosurface comes from the mesh in the file and the current
  density arrows are drawn on it (green shaft, red head, as in AICD); arrow size and density (thinning, nothing is
  recomputed) and the colours are adjustable. A symbol shows the direction of the magnetic field; its tooltip explains
  how to read the direction of a ring current. The isovalue is taken from the file. Alternatively a cube file with the
  ACID scalar field gives the isosurface (default isovalue 0.045, yellow; no arrows). The Gaussian output of the CSGT
  calculation (NMR=CSGT with IOp(10/93)) adds method and basis set to the caption; IOp(10/93=2) is named as "selected
  orbitals". Other layouts of the AICD files, cubes with negative values and outputs without CSGT/IOp(10/93) are
  refused. The AICD reader was checked against one public AICD 3.0.4 output. Figure in export and SI with isovalue,
  level of theory and the ACID references. The example project contains an invented AICD output.
- **DFT: data the journals require (ACS, Org. Lett., Angew. Chem.).** New page "Energy Table" in the DFT tab: one
  row per calculation with the number of imaginary frequencies, E_el, the nuclear repulsion energy, H, G, the thermal
  correction to H and the entropy correction −TS in Hartree, all exactly as printed in the output (a value the output
  does not print stays a dash, nothing is calculated; ORCA prints no H correction, Gaussian no −TS in Hartree), plus the
  program version (ORCA "Program Version", Gaussian revision such as "16 Rev. C.01"). The table goes into the Word SI
  (full width after the two-column structures) and the export (`…_energies.csv`). All structures of the tab are also
  written to ONE machine-readable xyz file (`…_structures.xyz`: atom count, name and E_el in the comment line, then
  "El x y z" in Å) in the export and the data package (`DFT/structures.xyz`). Input files with the same name next to an
  output (`.inp`, `.gjf`, `.com`) are copied into the compound on import and go into the data package; a missing one is
  pointed out on the page. The TD-DFT tab export adds `…_transitions.csv` with the TD-DFT transitions (state,
  energy, wavelength, oscillator strength, multiplicity) as read.

- **CV: details the journals require with the voltammogram.** New card "Measurement Conditions" (Data step):
  working and counter electrode, purge gas, instrument and polishing, entered once and remembered for new compounds.
  From the Gamry file the tab reads the starting potential and direction of the scan and whether iR compensation was
  on. The caption stays short: iR compensation and the plotting convention (IUPAC or polarographic) appear there only
  if the project's chapter paragraph does not state them or the measurement deviates, starting potential and direction
  only with the chip "Start and direction". The setup (instrument, working electrode with area and polishing, counter
  and reference electrode, atmosphere, iR compensation, convention) is
  collected in one opening text instead of every caption: in a project it is entered once on the project page
  (Details, card "Cyclic Voltammetry: Setup") and opens the chapter "Cyclic Voltammetry" of the combined SI as a
  running text in full sentences (empty fields drop their part, a free field takes further sentences), and the
  CV tab only refers to it; without a project it opens the methods text of the compound. Empty fields add nothing.
  The card names what ACS and Angewandte still expect (solvent, electrolyte, concentrations, electrodes, gas,
  instrument, area, polishing).

- **Elemental analysis and HRMS checked like the journals do.** IR + EA: a second set of values (duplicate
  analysis, as Angewandte asks) is optional; with it the SI line gives both sets and the average, and the average is
  checked against 0.4 %. A small table per element (checked value, Δ, status) and a tile "EA" show deviations in the
  warning colour. New field "No EA, because": without found values, its text goes into the SI as "Elemental
  analysis: …". HRMS: table with ion, calc., found, deviation and status against 5 ppm, plus a tile with the
  deviation. Without a second set everything stays as before. The example project shows both cases (S3 within the
  limits, S2 with an average 0.43 % too low and an HRMS value 7.4 ppm off).

- **EPR: acquisition parameters and coupling unit in the caption.** On the SI Text page a chip puts microwave
  frequency, modulation amplitude, power, number of scans (newly read from BES3T: `NbScansDone`, else `AVGS`) and
  temperature from the files into the caption, only values that all shown measurements contain and share. "Couplings
  in" switches the hyperfine couplings of the caption between MHz, mT and G (G also in the methods text). The example
  project's EPR spectrum is now a BES3T file with invented parameters.
- **CV: pulse voltammetry files from Gamry (DPV, square wave).** A Gamry file whose curve table names the columns
  "Vstep" and "Idif" is read as one curve, difference current against the staircase potential; the caption says
  "Differential pulse voltammograms" or "Square-wave voltammograms" and gives step, pulse amplitude, pulse time or
  frequency from the file, the axis shows ΔI. Checked with a real Gamry square-wave file; no real DPV file was
  available, so a DPV file is read if its table names the same columns and refused otherwise (columns are never
  taken by position). Peak pairs and scan-rate analyses do not apply to these curves.
- **NMR: compound number and conditions on the spectrum, range check.** Below the structure in every spectrum the
  compound number (bold) and nucleus, frequency and solvent are drawn, in the preview, the SVG and the Word export
  (two chips switch them off); the free spot for the structure takes the lines into account. The table of spectra
  shows the labelled range of the axis and marks spectra whose labels do not reach 0 and 10 ppm (¹H) or 0 and 200 ppm
  (¹³C), the ranges ACS and Angewandte ask for. A note only.
- **TD-DFT: table of excitations.** New page "Excitations" beside the figure: state, E (eV), λ (nm, integer), oscillator
  strength f and the main contributions (orbital → orbital with weight in %, one row each, names relative to HOMO/LUMO
  from the occupations in the output). Card "TD-DFT Table" (Evaluation step): f threshold (default 0.01, "off" = all
  states), contribution threshold (default 10%), optionally only the λ range of the figure, and whether the table goes
  into the SI. Weights: ORCA as printed in the composition of the states; Gaussian 2c² from the printed coefficients
  (closed shell) or c² per spin (open shell); de-excitations ("<-") never count. Without a composition in the output
  (old table, SOC, spin flip, multireference) the columns are left out. Word: "Table Sn: TD-DFT excitations of X."
  after the figures (overall SI: computational chapter), with the selection and the weight rule as a note.
  `…_transitions.csv` gains all printed contributions without threshold and the weight rule. The example project's
  TD-DFT output now contains a composition and a dark state.
- **IR + EA: calculated against measured IR.** Card "IR Calculation" (step IR): an ORCA or Gaussian frequency
  calculation (the reader of the DFT tab, now also with the IR intensities: ORCA 5/6 "IR SPECTRUM" in km/mol,
  Gaussian "IR Inten"; other layouts are refused) is drawn over the measured spectrum as a line spectrum or with
  Lorentzian broadening (adjustable FWHM, default 15 cm⁻¹), its strongest band as deep as the measured one. In
  transmittance the calculated spectrum is converted (T = 100·10^−A), never the measurement. Scaling factor default
  1.000 – it depends on the level of theory and is entered by the user, nothing is taken from tables. New page
  "IR Calculation": assigned bands (measured, calculated scaled, Δṽ = measured − calculated, intensity, how) – only
  bands assigned by hand (fields "Band"/"Mode") or unique within an adjustable tolerance (exactly one calculated mode
  from 5% of the strongest, and it lies at no other band); tile with the number of assigned bands. Word: caption with
  level of theory, scaling and broadening, and "Table Sn: Measured and calculated IR bands of X." The example project
  contains an invented frequency calculation with one ambiguous band assigned by hand.
- **IR + EA: Raman.** New card "Raman" (step IR): a Raman spectrum as a text file (columns Raman shift and intensity;
  header lines are skipped, tab, semicolon, comma or decimal comma; instrument binary formats are refused – export
  them as text), own peak search (maxima, adjustable threshold), table to untick bands and the SI line
  "Raman (λexc = 785 nm): ṽ = 2217, 1608, … cm-1" (excitation wavelength as a field), which joins the characterisation
  paragraph after the IR line. Field "Figure": IR, Raman (axis "Raman shift [cm⁻¹]", intensity without numbers,
  "arb. u.") or IR and Raman stacked on a common wavenumber axis; caption accordingly. If the frequency calculation of
  the card "IR Calculation" contains Raman activities (ORCA "RAMAN SPECTRUM", Gaussian "Raman Activ"), the Raman figure
  shows the calculated activities with the same scaling and broadening as the IR; without activities there is no
  calculated Raman spectrum (note). The example project contains an invented Raman spectrum and activities.
- **X-Ray: packing figure with intermolecular distances.** Card "Packing" (first card of the Display step): figure
  "Molecule" or "Packing (unit cell)" – the unit cell with edges and the axes *a*, *b*, *c*, filled by symmetry from the
  completed molecule (whole molecules whose centroid lies in the cell, or all touching it), viewed along *a*, *b* or *c*
  (or rotated freely with the mouse), H atoms on/off, same ellipsoid style as the molecule figure; polymers keep the
  existing truncation. Card "Distances in the Packing" (Evaluation step): suggestions per molecule pair – the shortest
  atom···atom contact below the sum of the van der Waals radii (Bondi, J. Phys. Chem. 1964) plus a tolerance
  (optionally non-H atoms only), ring centroid distances Cg···Cg with slip, and interplanar distances of planar rings
  only when the planes are parallel within an adjustable angle (otherwise the angle is given); tick what goes into the
  figure, or pick two atoms of different molecules in the figure. Distances appear as dashed lines with the value in Å
  (three decimals, calculated from the coordinates, no s.u.); page "Distances" with symmetry codes; caption names
  view, molecules shown and the distances (more than eight: a table in the SI). The packing figure goes into the SI and
  the export after the molecule figure ("In the SI"). Example project: S3 with a stacked pair (view along *b*).
- **EPR: spin counting against a calibration.** New view "Spin counting (against concentration)": measurements with
  a known concentration are the references, their double integral against the concentration gives the calibration
  (line with intercept from three concentrations, through the origin with one or two); the other measurements are
  samples whose spin concentration is read off. Table on the Results page, caption and methods text name the result;
  no uncertainties, no corrections for different conditions (a note appears if modulation, power or temperature
  differ). The example project contains three invented reference spectra.
- **X-Ray: powder pattern (PXRD) from the CIF.** Card "Powder Pattern (PXRD)" (Evaluation step) and page "PXRD": the
  powder pattern calculated from the single-crystal structure (positions from the cell; |F|²·Lp of every reflection
  from all atoms of the unit cell with occupancies and isotropic/anisotropic displacement; Cromer–Mann scattering
  factors from the International Tables Vol. C, without anomalous dispersion; pseudo-Voigt profile with adjustable
  FWHM and η; Cu, Mo, Co, Fe, Cr or Ag Kα, Kα2 on/off) against a measured pattern (`.xy`, `.xye` or text columns).
  No Rietveld fit: only scaling to the strongest maximum and an entered zero point; the card names the temperature
  of the structure determination and says that cell expansion and preferred orientation are not corrected. Figure
  stacked (measured above) or overlaid, reflection ticks; caption, SI (figure, caption, methods sentence with the
  source of the scattering factors) and export with a CSV of the reflections. Example project: S3 with an invented
  room-temperature pattern.
- Raman spectra and the IR calculation file are now copied with the compound like the other data files (relative
  paths), and the Raman file goes into the data package.
- **DFT: NBO analysis (new page "NBO").** The DFT tab reads ORCA 6 outputs with an NBO 7.0 analysis (card "NBO
  Calculations" in the Data step) and shows what the output contains, without computing anything: natural charges and
  populations (NPA), the NBO list with occupancy, energy and hybrids as printed (sp^λ, polarisation per centre), the
  second-order perturbation energies E(2) from an adjustable threshold (default 5 kcal mol-1, donor and acceptor
  written like "LP(1) N5 → BD*(1) C4–C6"), and the natural resonance theory (resonance weights, total/covalent/ionic
  natural bond orders, valencies). The figure shows the molecule with natural charges at the atoms and NRT bond orders
  at the bonds (threshold, decimals, elements, H on/off, colours; labels can be dragged). If the CML file written by
  NRTCML lies next to the output and matches it (same atoms and coordinates, first structure with the weight of RS 1),
  the leading resonance structures are drawn with their weights and formal charges; otherwise only the table. With
  BNDIDX in the NBOKEYLIST the Wiberg bond indices in the NAO basis are read as well (layout of the NBO 7.0 manual,
  checked against public real outputs of ORCA 6.1.1/5.0.4 with NBO 7.0 and of GenNBO 7.0.10, read strictly, refused
  with a message otherwise): bonds can be labelled with "Wiberg index (NBO, NAO basis)" instead of the NRT bond order,
  a sub-page "Wiberg" lists the bonds from the threshold and the totals by atom, the CSV contains the full matrix.
  These names keep both apart from the IAO Wiberg bond orders of the orbital view (Molden), which stay unchanged.
  Open-shell doublets (radicals, radical cations) are read too: natural charges and natural spin densities (NPA),
  Wiberg total/α/β, NBO list and E(2) per spin; a "Spin" field (total/α/β) appears only for open-shell outputs, and the
  figure can label atoms with the natural spin density (with sign; not the Mulliken spin population of the EPR tab).
  Checked: NPA with spin density and the total Wiberg matrix against a public ORCA 6.1.1 + NBO 7.0 doublet output;
  NBO list and E(2) per spin only against the NBO 6 layout (the page says so). Open-shell NRT, multiplicities above 2
  and Gaussian outputs are still refused. SI:
  figures with captions, tables and a methods sentence with program, NBO version and the citations printed in the
  output; export writes all tables as CSV. Other NBO versions, Gaussian/GENNBO outputs and open-shell analyses are
  refused with a message. The example project (S3) contains an invented NBO/NRT calculation.
- **NMR: ¹³C signals at solvent or impurity signals.** Below the nucleus count, a second table lists ¹³C signals that
  match a residual solvent signal or a common impurity in the same solvent according to Fulmer et al.
  (Organometallics 2010, 29, 2176; tables 1 and 2 are included as published), e.g. "29.7 · 29.71 · Apiezon H grease"
  in CDCl₃. Tolerance 0.02 ppm plus half the last given digit; a substance with several carbons counts only when all
  its carbons bearing H match. If the Mnova SVG labels the solvent signal (e.g. "77.00 CDCl3"), the comparison uses
  the difference to the table (here +0.16 ppm) and says so below the table; spectrum, NMR line and SI stay unchanged.
  Without a labelled solvent signal there is no offset; more than 0.5 ppm apart means no comparison. Chip **Impurities** (on by default). A note only: nothing is changed or removed from
  the NMR line or the SI. Unknown solvent names give no note. The example compound S2 shows the case.
  **¹H** only at free peaks: peaks of the spectrum outside every multiplet of the ¹H line (multiplet = centre ± half
  the first-order width from multiplicity and J, or the given range for "m", plus 0.01 ppm), so the signals of the
  line are never marked (on a published SI almost every ¹H line hit a table value). Peaks come only from MNova's peak
  report of an exported document (own spectra: no ¹H comparison, automatic peaks hit the right and a wrong solvent
  column equally often); without a peak list a sentence says there is no ¹H comparison. A substance with several
  signals counts only when each of them hits its own free peak (warning colour); substances with one signal (water,
  acetone …), the residual solvent signal and the undeuterated solvent itself (toluene in toluene-d8) appear as
  "possible" in grey. No reference offset for ¹H.
- **EPR: EasySpin start script from the calculated couplings.** Step **Evaluation**, card **Hyperfine Assignment**:
  "Save EasySpin script …" writes a MATLAB script for `garlic` (isotropic solution spectrum): `Sys.Nucs`, `Sys.n`
  and `Sys.A` in MHz (as calculated, no conversion) of the assigned groups (mean with signs over the assigned nuclei;
  without assignment the nuclei shown individually in the figure), `Sys.g` from the valid fit of the S = ½ simulation,
  `Exp.mwFreq`/`Exp.Range` from its measurement. Anything missing stays a commented placeholder (garlic requires g,
  no value is guessed); the line width is always a placeholder. Isotropic couplings only, anisotropic tensors are not
  written. Export includes the script under a name MATLAB can run (letters, digits, underscores, starting with a
  letter, e.g. `S3_1_EPR_easyspin.m` for compound S3.1); if the script cannot be generated, the export leaves out only
  the script and names it in its message. Not yet run in MATLAB/EasySpin.
- **Figures as PowerPoint slides (PPTX).** "PPTX" is a further format in the "Axes, Size and Formats" card of every tab
  with the common card and in the formats of UV-Vis (ε): "Export" then also writes `<compound>_<tab>.pptx` with one
  slide per figure (UV-Vis (ε): per series). The new card "Slides (PPTX)" in the Compound tab exports several figures at
  once (`<compound>_slides.pptx` in `figures/`), with its own figure chips (remembered on this computer, independent of
  the SI). Each slide holds the figure as in Word (PNG with SVG), fitted with the same aspect ratio, and below it the
  caption as an editable text box (bold, italic, sub- and superscripts kept; without "Figure Sn:"). The file is written
  without an extra package; X-Ray and DFT have their own format field and no PPTX there yet (their figures are on the
  slides of the card).

- **NMR: own spectra from Bruker raw data (optional, Mnova SVG stays the default).** "Raw data …" in the card
  "Spectra" (or "As spectrum" on the page "Raw Data", or "Source" of a spectrum with a linked experiment) shows a TopSpin
  1D experiment in its own spectrum view with the Mnova keys: Fourier transform from the FID (reader and transform
  checked against TopSpin on 201 real data sets), phase from procs, automatic baseline, axis without TopSpin's
  calibration. Phase and reference stay "not confirmed" until confirmed: the reference is suggested from the solvent
  residual signal (Fulmer 2010) or set by clicking a peak (R) with a target δ; the phase can be suggested (ACME) or
  dragged (Shift+P). Variants without a checked processing are shown as TopSpin's 1r with a message, never guessed.
  Processing, reference and display are saved with the compound. The example project (S3) has invented ¹H raw data
  next to its Mnova spectrum.
  **Evaluation:** integrals (I) with the user's normalisation, multiplets suggested (first order after Hoye, otherwise
  "m") or picked with J; a user pattern (class + J) is searched in the range and its lines are drawn above the spectrum,
  so a wrong suggestion is visible. Every signal is confirmed on its own (no "confirm all"); a coupling whose lines are
  not resolved is printed only via "Take J", or "Without this J" fits the pattern again without it (dd → d). Unconfirmed
  signals print as range + m.
  **SI:** per nucleus the Mnova line and figure stay until "Use own processing in SI" is chosen for an own spectrum (at most one per
  nucleus) and its phase and reference are confirmed (every nucleus, ¹⁹F included); one definition of what is printed
  feeds the SI line, signal table, nucleus count, tiles, Word and the comparison table; untouched suggestions are never
  printed (the tab counts them), a taken J shows "J taken"; the own figure labels only confirmed signals and peaks.
  Then the NMR line of that nucleus comes from the evaluation (only confirmed δ and J; a signal that cannot be written
  is named, the line stays), the figure is drawn like the Mnova template (16 × 11 cm, structure with number and conditions,
  insets avoid the structure and the spectrum, marks explained in the caption) and goes into Word like the Mnova spectra
  (page "SI Figure" shows it).
  **2D:** a 2D experiment from raw data is processed from ser where its class is checked (otherwise TopSpin's 2rr with
  the reason) and drawn as contours with sign colours, projections, rectangle zoom and wheel threshold; F2/F1 are
  referenced via a confirmed own 1D spectrum of the same nucleus and magnet, otherwise marked uncalibrated. Unsplit NOAH
  sets show "phase pending". The figure goes into the SI like a Mnova 2D spectrum.
  **X nuclei** (¹⁹F, ³¹P, ¹¹B, ²⁹Si, ¹⁵N): the axis stays nominal (not calibrated on the sample) by default; "Unified
  scale (¹H)" references it via the own ¹H spectrum of the same sample on the same magnet with a confirmed reference
  (Ξ after Harris 2001, only values copied twice independently; ¹⁵N against MeNO2 or NH3 as chosen), as a suggestion
  to be confirmed.
- **NMR: insets, labels and export notice like the Mnova workflow.** X dragged inside an inset cuts that range out of
  the inset (parts with a "//" break, one undo step per cut); the labels of an inset stand in groups above their part;
  labels that do not fit the width give a note only. Peak labels start at the template size (4 pt) and can only be made
  larger; multiplet labels are readable in the view (at least 12 px, their leader lines run below all labels), the SI
  figure keeps the template. Axis numbers never overlap: the division gets coarser where numbers would not fit between
  their ticks, and at a break the number next to it on the narrower side is left out. The range of the
  own SI figure comes only from the new field "Range" ("auto" −1…11 / −10…220 ppm), no longer from the last zoom. The
  view keeps its page, scroll position and zoom over language, theme and undo. The export notice (Ctrl+E) lists withheld
  own figures in one line with "Details" instead of a message box; the nucleus count says "n suggestions open" when H
  are missing because suggestions are open. A dropped 1D folder without a matching Mnova spectrum becomes an own
  spectrum. Own 2D spectra get the page "SI Figure"; the field
  "Nuclei" shows ¹H/¹³C.
- **NMR core (reader, processing, evaluation, 2D, view).** Bruker reader (fid/ser/1r/2rr, little and big endian,
  int32/float64, XDIM sub-matrices) with a list of checked variants, everything else refused with a message; 1D
  processing checked against TopSpin; baseline, ACME phase suggestion, solvent reference suggestion (Fulmer 2010),
  integrals, first-order multiplets and pattern fit with a status (suggestion, confirmed, not measured) up to the SI line;
  2D processing from ser for the checked classes; a spectrum view with the Mnova keys. A coupling whose lines the fit
  merges (< 0.5 Hz) counts as not measured.
- **NMR: MNova documents open as own spectra.** "MNova document …" in the card MNova (or drag & drop) keeps the
  `.mnova` file unchanged in the compound as before and turns every readable 1D spectrum with its FID into an own
  spectrum (source "Raw data from MNova document"), processed like a Bruker experiment. MNova's referencing is only a
  suggestion to confirm. 2D spectra and unchecked MNova versions are not read; a notice and a line in the card name
  them (no dialog). The rebuilt experiments do not go into data packages; the document stays the raw data. The card
  "Spectra (SVG/EMF from MNova)" is now called "Spectra".
- **NMR: baseline choice and keys without a click.** The card "Processing" offers the fifth-order polynomial (default,
  unchanged), a third-order Bernstein polynomial (MNova's "Advised" setting; the signal-free points are chosen by
  Elucida, not by MNova) or no baseline correction. The spectrum view takes the keyboard focus when the NMR tab opens
  and when the mouse is over it, so the MNova keys work without a click; a field being typed in keeps the focus.
- **NMR: fewer ¹³C peak suggestions with a confirmed phase.** "Suggest peaks" then offers only the highest maximum
  within 1 Hz; the card names how many further maxima were left out (pick them in mode K). Without a confirmed phase
  nothing changes.
### Changed
- **λ labels just above their band.** In the UV-Vis (ε), SEC and fluorescence figures a λ label without a
  dragged position now sits just above its own maximum (gap 0.4 label heights, also to the next label) if there is
  room there; inset, table, structure and photo stay exactly where they were. Labels without room keep the row at the
  top as before. If the labels would then no longer run left to right by λ, would cover the legend, or legend or arrow
  would find no free spot, the whole figure stays as before. Dragged labels are kept.
- **CV: the scan-direction arrow sits above the voltammogram.** Without a dragged position it no longer starts on
  the first measured point (on the curve) but in free space just above the curves near the start of the scan, clear
  of labels, legend and structures; in the comparison's CV stack each arrow sits above its own curve. Without a free
  spot it stays at the first point. Dragged positions are kept.
- **"Reset all to defaults" is now "Reset display" and resets only the look of the figure** (X-Ray/DFT: "Defaults" →
  "Reset display"). Everything that changes a printed number, a table, a tile, the methods text, the SI or the data
  that go into the analysis stays: ranges and windows of the analysis, baseline, fit model, thresholds, selections,
  disorder, hidden atoms and fragments, calculation columns, and which quantity or SI figure is printed (R², ± σ, peak
  labels, m/z, spin density/SOMO, IR/Raman, CV plot). Before, the button switched e.g. the fluorescence fit from
  bi- to monoexponential, turned off the kinetics fit and changed the EPR baseline. Where the axis range also limits
  the analysis (UV-Vis peak search, UV-Vis kinetics without a chosen λ, Raman peaks, TD-DFT table "only in range"), the
  axis range stays too. A caption sentence that only describes the figure (ellipsoid probability, hidden H atoms,
  isovalue, colours) follows the figure. Presets save and load the same display settings only (including
  the display of NBO, NICS and ACID, without their files).
- **The tab "UV-Vis overlay" is now called "TD-DFT"** and compares the measured spectra of one compound with its
  calculation (TD-DFT, ESD); several measurements of the same compound (solvent, concentration, before/after a
  reaction) stay possible. Comparing different compounds moved to the project (project page → Comparison: normalised
  to one band, structures in curve colour, combined SI): the structure per spectrum is gone from the tab, a row
  "Comparison" in step Data leads to the project. Older figures with a structure per spectrum stay exactly as they
  were (figure, SI and saved project), with a note in the tab. Stacking (with y axis, names at the curves, zero line
  per level and "level as above") stays for spectra of the same compound.
- Orbitals, spin densities and NICS surfaces look smoother while rotating: the preview during the drag is computed at
  one third instead of one quarter of the resolution and scaled up softly instead of in blocks; after releasing, the
  figure is redrawn at full resolution as before.
- Result tabs on the right: pages without data (NICS, ACID, NBO, HOMA, charges, excitations, NTO, IR calculation, spin
  density, hyperfine, decay, distances) no longer appear as tabs; the figure comes first and the SI pages last (DFT:
  the SI page is now called "SI Text"); what does not fit goes into "More ▾" instead of a scroll arrow. ACID arrows
  default to 2.5 ×, the NMR spectrum sits in a card like the other figures, EPR spin percentages are whole numbers as
  in the figure, the IRF shift is given in ps, and the example project shows the Raman spectrum.
- Faster: switching to another compound no longer rebuilds every tab opened before (example project 3–4 s → under
  1 s), hidden figures and result pages (NTO, ACID) are computed when shown instead of with every redraw (TD-DFT tab
  1.8 s → 0.3 s), figures are no longer drawn several times while the window settles (EPR hyperfine 3.2 s → 1.4 s),
  zooming orbitals and surfaces uses the coarse preview like rotating, and project files are read with the C YAML
  reader (start screen and project page).
- Example project: the precursor S2 shows a small EPR spin count; the packing figure (X-Ray) and the spin density
  (EPR) fill the figure in their default view (packing turned in the image plane where that fills better).
- Tab bar: in the group "UV-Vis & photophysics" the tabs are labelled "TD-DFT" and "Kinetics" (full name in the
  tooltip), so the bar fits at 1200 px.
- **TD-DFT tab, caption:** "Experimental and calculated (TD-DFT) UV-Vis spectra of …" instead of "Comparison of UV-Vis
  spectra of …"; with only measured spectra "UV-Vis spectra of …", with only calculations "Calculated (TD-DFT) …". The
  caption follows the visible entries and is not saved, so existing projects get it too.
- **Units in the table header instead of the cells:** EPR couplings ("experimental [MHz]", "calculated [MHz]"), spin
  count ("c (known) [mM]"), DFT energy table (E_el, H, G, E_nuc, H_corr, −TS in [Eₕ]; the separate sentence is gone),
  intercept of the ε table ([cm⁻¹]).
- CV: the result table, tile and project comparison show E½, Epa and Epc with two decimals like figure, methods text and
  Word (before three). SEC: the tile shows the potentials of the spectra with two decimals like legend and caption.
- Kinetics (UV-Vis, EPR decays): k and its interval in the result table are written like the methods text
  ("3.90 × 10⁻²" instead of "0.039").
- **Reaction path in the frame of the tabs:** one tab row (Compose · Calculation Data · 3D / Orbitals · Charges · Energy
  Table · SI Text) instead of a second row inside "3D / Orbitals"; one blue main button, "Export profile"; the button
  "Export" of the DFT part stays grey, and without calculations "Data ▾" (or the button of
  the guide) is the main button. Messages of the DFT part (copied, saved, reset, atom under the cursor) now appear as a
  notice in the main window. Calculation Data: no header line above both columns (the steps no longer shift by 40 px
  when changing tabs), "Import from compounds" opens as a card in step Data, footers left (Reset: label positions or
  "Style to defaults", which keeps values, plateau positions, scaled/schematic, connectors and sections) and right
  (caption of the figure) as in the tabs, the view zoom moved to step Display (card Size), a grey placeholder instead of
  text in the figure without calculations, the calculation table as high as its rows without the clipped button at its
  edge, the IRC list as a table. Compose: tool buttons as high as the other bar buttons, the SI caption with "Copy" (the
  finished caption, own or from the inserted profiles), the embedded orbital view as a form without its own blue button.
  The composition export writes the formats chosen under "Size and Formats" (default PDF, SVG, PNG as before; CDXML and
  CDX always). Figures, energies, captions and stamps of inserted profiles are unchanged.
- **Nothing switches by itself.** Dropping files or opening measurement data from another tab no longer switches the
  tab: a notice names the target tab with "Show" and the tab button carries a dot until it is opened. A card on the left
  that changes a result page that is not open (NICS, ACID, NBO, HOMA, packing distances, PXRD, comparison with
  calculation, lifetime, EPR calculation, NTO) names that tab, and the tab gets a dot until it is viewed. This dot is
  blue (accent colour); the orange dot at a step still means "differs from the default". In the tabs of
  a compound, defaults, presets, undo, language and theme keep the open result tab and the scroll position of the left
  column (before: back to "Figure" and to the top; measured in CV); defaults, presets and undo keep the open tab of a
  comparison and the tab and column scroll position of a reaction path as well; with an open reaction path the language/theme switch keeps its tab and
  the scroll position of its column, and an open comparison stays open.
  Ctrl+F in a compound shows the filter of its project instead of the overview.
- **One message after every export.** Export, SI (Word), complete SI and data packages report the same way, as a notice
  instead of a dialog: target and formats, and what was used – for SI (Word) the parts, the deselected figures (before:
  not mentioned) and the tables with their own "In the SI"; for data packages the number of files or the files
  deselected per compound. Links jump to where the selection is made ("Change formats", the SI Export card, the tab of a
  table, "Open folder"). The complete SI follows each compound's SI selection (column **SI** in the Export tab). Ctrl+E in
  Synthesis and NMR reports the same way. If parts were left out (unreadable),
  the notice starts collapsed as one line over the figure ("SI saved – 2 notes") with "Details" to expand it and
  "Close"; before, the full notice covered the figure until it was closed.

### Fixed
- **NMR raw data with extreme filter values:** an infinite group delay (GRPDLY) no longer crashes the processing check,
  it is refused with a message, and a non-integer DECIM is refused instead of cut to a whole number. All checked real
  data sets process exactly as before.
- **Reaction path: profile shifted in PNG/PDF.** In the exported composition (PNG, PDF), its Word image and the
  card preview the energy profile sat with its top-left corner at the centre of the canvas, small and cut off on the
  right (since 1.1.0): the renderer ignored the position of the embedded profile. It is now placed as on the canvas;
  the SVG export is unchanged.
- **Loading a preset deleted data.** Presets carried calculations and analysis settings along (TD-DFT NTOs, the EPR
  calculation, NICS/ACID/NBO files, the energy profile, HOMA selection), and loading a preset removed them from the tab
  or put the files of another compound into it. Presets now contain only display settings; when loading, older presets
  are filtered the same way, so files, assignments and analysis settings of the open compound stay.
- **Compound name with a dot** (e.g. "S3.1"): the exports of all tabs were named "S3.pdf", "S3.xyz" … instead of
  "S3.1_CV.pdf", and the tabs overwrote each other's figures without a message (only the last export remained). Every
  file now keeps the full name `<compound>_<tab>`; the same applies to comparisons and reaction paths whose name
  contains a dot, and to a file name typed without extension when saving an xyz file or a drawing. Files written
  under the wrong name before stay in the folder.
- **Old projects with a file the stricter readers now reject** (truncated calculation, measurement file without values,
  damaged MS report or Mnova SVG): export, SI (Word) and project SI leave out only the affected part and name the file
  and the reason in the final message, instead of silently losing figures, tables or methods texts or aborting
  altogether. Before, for example, the EPR export aborted when the calculation (spin density/hyperfine) was unreadable,
  and a project SI silently dropped a whole compound. The HRMS, NMR, DFT and fluorescence tabs open again with such a
  file (before, the tab was missing until a restart) and show the reason; an unreadable ε measurement file no longer
  aborts opening the compound and stays unchanged in the project file together with its series.
  If a level of a reaction path is unreadable, its energy profile is not drawn (without the level the reference and the
  values would change) and this is reported; the project SI keeps the other paths instead of aborting. If the MS report
  is unreadable, the line says "found –" instead of silently using the mean of the raw data.
- **EPR, couplings from a calculation:** the assignment of calculated nuclei to an experimental group is now checked
  against the element of the group; after the simulation's nuclei changed, a value of another element no longer
  appears under "(exp. …)" – the group stays unlabelled and the card says so. Labels no longer show "−0.00";
  percentages are rounded half up like everywhere else.
- **EPR, spin counting:** number of scans, receiver gain and conversion time (BES3T `RCAG`, `SPTP`/`ConvTime`) and the
  microwave frequency are compared as well; if they differ, a clear warning says the concentrations are wrong by that
  ratio unless the spectra are normalised (nothing is converted). Samples outside the calibration range or with a
  negative concentration are marked (tab, caption, methods text). "All spectra processed identically" only when a
  dark spectrum is subtracted from all or none.
- **NMR, nucleus count:** ²H NMR is checked against D of the formula (also `[2H]`), ³H against T. Several H counts in
  one signal ("2H, 3H") are kept in the NMR line and reported as ambiguous instead of counting only the last.
- **Raman:** without an entry the excitation wavelength is "not given" and λexc is left out of SI line and caption
  (no default of 785 nm).
- **CV:** the reference electrode of the setup has its own field ("Reference"); the reference of the axis is no
  longer written as "… as reference electrode" unless it was entered (its default is no statement about the setup).
  The current convention appears in the caption only if the project names one and the figure differs, or if the
  currents are inverted; a Gamry file with a different `CONVENTION` gives a note. Pure DPV/SWV series get their own
  sentence instead of the CV sentences (E1/2, Nicholson). An empty curve no longer stops the notes.
- **EPR, isothermal fit with rising intensity (k < 0):** tab, caption and methods text say "intensity increased; no
  half-life" instead of describing a decay. Result lines of the EPR and UV-Vis kinetics methods texts write negative
  rate constants with a true minus like the caption.
- **X-ray packing: molecules on symmetry elements.** For a molecule on an inversion centre, mirror plane or twofold
  axis (Z′ < 1) the suggestions listed contacts of the molecule with itself (d = 0.000 Å) and every neighbour twice. A
  neighbour is now defined by its atoms (after symmetry and translation), not by the operation: symmetry-equivalent
  pairs appear once, images of the molecule itself never; each ring pair once also for self-inverse operations.
- **X-ray packing: symmetry codes.** The code of the partner now includes how its atoms or ring were generated in the
  molecule, and a contact between two copies picked by hand is coded relative to the first one (Ga⁻¹∘Gb instead of Gb
  alone; distances were already right). The first partner stands at the position of the CIF atoms. One numbering for
  the molecule figure, the list, the caption and the SI: the codes of the generated atoms keep their numerals, codes of
  partners follow them. Symmetry-equivalent rings of a molecule share one Cg number; a ring on a symmetry element names
  its generated atoms. Translations such as 1/3 and 1/6 are stored exactly (old projects with 0.3333 are read as 1/3).
- **PXRD: missing displacement parameters.** Atoms without U_iso/U_ij in the CIF no longer get an assumed
  0.02 Å² silently (U = 0 from the CIF was replaced as well): they are calculated without a temperature factor, and the
  card (in the warning colour) and the methods text name them.
- **SI references.** With the "Supplementary Figure" or "Figure S" labels, references in the text are converted also
  in the plural ("Figures S1 and S2"), as ranges ("Figure S1–S3" → "Supplementary Figures 1–3"), with panel letters
  ("Figure S1a"), as "Fig S4" and "Figure S 3"; "Figure 3" (the article) stays.
- **Elemental analysis, duplicate determination.** If an element has only one value, the line says so ("N determined
  once") and averages only elements with two values; an element only in the second set is no longer dropped.
- German placeholders of the CV details of a project start with "z. B.".
- **Project comparison, fluorescence:** since the excitation spectrum was added, the comparison (and
  `.elucida/compare.json`) took the excitation spectrum as the emission. The emission is now marked as such in the
  tab; saved comparison data of compounds with an excitation spectrum count as outdated and are rebuilt with
  "Update" (no other file is changed).
- **Moving a compound folder:** the ACID files (log, cube, AICD `.inc`) and the NBO outputs with their NRT CML were
  saved with absolute paths and were lost after moving the folder; they are now saved relative to the folder and
  missing ones are reported.
- **Data package:** new calculation and measurement files were missing without a note: IR frequency calculation, EPR
  calculation and orbital/spin-density file, NTO cubes/Molden, ACID (log, cube, AICD folder), NBO output and CML, the
  geometry for the X-ray comparison and PXRD measurements (new group "PXRD"); missing files are listed. In
  CompChem.zip the AICD folder is kept.
- **FID for Publication:** respects what was deselected in the data package dialog, and names the compounds as in
  the zip (replaced lab codes) in `NMR_parameters.txt` and in the Data Availability Statement.
- **SI, DFT:** one condition for "DFT has data" in the compound SI and the project SI: NBO alone, ACID from an AICD
  output (without cube), NICS or IRC now reach the compound SI as well.
- **DFT, "Reset all":** no longer empties loaded NICS, ACID and energy profile data; only the display is reset.
- **NBO:** the caption no longer says "α-spin Wiberg …" for a closed-shell output (spin choice is reset on loading
  one); an NBO output without a geometry block no longer stops the DFT export and SI: tables and CSV as printed, no
  figure, with a note.
- **DFT energy table:** the note now says why *H*_corr is "–" for ORCA (ORCA prints no H − E_el; its "thermal
  enthalpy correction" is only k_B·T, checked against real ORCA 6 Opt+Freq outputs).
- **NICS:** a file with 200 or more Bq along a path (long straight or bent scan) is a scan, not part of a 3D grid;
  Bq that all lie in one plane are refused with that reason instead of "points missing".
- **NTO cubes without MO number:** hole and particle are no longer guessed from the order of selection (only from
  "hole"/"particle" in the file name, otherwise a message); the weight from the output also compares the spin (α/β).
- **DFT tab of a compound:** with two or more Opt/Freq calculations, an energy profile that the tab no longer shows went
  into the compound and project SI and into the export (with mixed molecules or methods the values were meaningless).
  The profile belongs to the reaction path; in a compound only an already saved profile (older projects) is used.
- **SI, EPR calculation without measured spectra:** its figures came without the methods text; the methods text now
  follows the same condition as the figures.
- **Numbers near zero:** no more "−0.000"/"−0.0" (CV E½ near the reference, HR-MS deviation, ε of a band without
  absorption, HOMA, NICS columns, EA Δ).
- **HR-MS:** the ≤ 5 ppm status is judged on the printed deviation (+5.0 ppm is always "≤ 5 ppm", as in the
  elemental analysis); the export no longer writes an empty `_data.csv` (the line spectrum is in `_sticks.csv`).
- **Fluorescence:** figure, tile and project comparison round λabs, λem and ε like the properties table (half up,
  452.5 → 453; before the figure gave 452 and 12344 for ε = 12344.5); the lifetime tile uses the unit of the tables (µs
  from 1000 ns).
- **Word:** names in table captions are written as entered ("S3_opt_freq", not "S3\\_opt\\_freq").
- **NMR, axis range check:** a row of integrals below the spectrum with more numbers than the axis labels could be
  taken for the axis; only evenly stepped labels count now.
- **SEC, BWSpec files:** a file with fewer data rows than the pixel range in its header (truncated) is refused with a
  message instead of being read silently with part of the spectrum.
- **Gaussian orbital energies** of an output with CR-only line endings no longer take the numbers after the
  eigenvalue lines as further orbitals.
- **CV result CSV** no longer depends on the language: the column `reference` holds the scale ("Fc0/+" or the reference
  electrode) instead of the hint text.
- **Truncated calculations:** X-ray comparison with a calculation and IR calculation vs. measurement refuse an output
  that did not terminate normally (geometry or modes may be incomplete).
- Small things: elemental analysis in duplicate with one element measured once shows that value in the column
  "average or single value"; the CV guideline check names the reference electrode of the setup; NBO: a note when the
  CML lacks lone pairs (no formal charges); the overall SI has no empty "Synthesis of X" for compounds without
  synthesis or data; the default series name "probe" is shown as "sample" in English and in the methods text (the
  saved key stays); EPR methods text "from a calculation at the … level of theory" (no "a M06-2X"); EasySpin export
  omits parameters without a value ("T [K]: None"); synthesis table rounds yield and equivalents half up like the SI
  line.
- Example project: the EPR hyperfine assignment belongs to the S = ½ simulation again (page "Hyperfine" shows
  "(exp. …)" and the calculated averages); the ¹H spectrum of S3 is labelled 0–10 ppm (no range note; S2 keeps the
  short axis 1–9 ppm as the warning case); the ε series name their solvent (THF), so caption and SI line are complete.
- **ORCA/Gaussian outputs with several jobs** (ORCA `$new_job`/Compound, Gaussian `--Link1--` with its own route):
  charge, multiplicity and method came from the first job, energy, geometry and frequencies from the last. Now
  everything comes from the last complete job; steps that Gaussian adds itself (opt freq) still count as one job.
- **Truncated ORCA/Gaussian outputs:** a coordinate block cut off in the middle gave a partial geometry; now the last
  complete block is used (the output is marked as not terminated normally).
- **Files that ended early or contained unreadable lines were read silently shortened or wrong; they are now refused
  with a message:** TD-DFT table of ORCA (fosc now taken from its column header), ORCA ESD spectrum (truncated or
  corrupt line, with line number), Cary .DSW (fewer spectra or a shorter last spectrum), Gamry H-cell files
  (row count from the table header of the step files; main file with fewer half-cycles than CYCLES and no stop
  reason), EPR text files (mixed decimal separators, merged numbers such as
  "330.37-6.92", overflow "****", with line number), cube files with too few or too many values.
- **EPR text files:** the field unit is taken only from the header of the field column ("Amt" or a sample name
  containing "mt" no longer means mT); without a unit there the unit is assumed and can be chosen as before.
- **Cary CSV re-saved by Excel (German):** with the sample names directly above the data and ";" plus decimal comma,
  only one sample was read; the separator now follows the structure of all rows.
- **Cary Eclipse CSV with a "Z Axis" column (one wavelength column, one intensity column per sample):** only the first
  sample was read (ε, fluorescence); now all samples are read with their names. A layout that matches neither the
  paired export nor this one is refused with a message instead of being read shortened. A Cary CSV with a named sample
  without data columns is refused as well (that sample was left out silently).
- **Text files for Raman, PXRD and decay curves:** the Z-axis index row of such an export (",1,2" below the sample
  names) was taken as a data point; a decay curve with it was refused. The time unit of a decay curve comes from the
  time column of the column header, also above rows of sample names, and never from metadata above it
  ("Resolution [ns]" above "Time,Counts" gave ns).
- **Clear messages instead of Python error texts** for Gamry and BWSpec files with decimal comma, cube files in
  UTF-16 (now read), empty or truncated cube and Molden files, damaged MS report (.docx) and empty OPUS PDF.
- **X-ray: "Copy" of the caption** copied the molecule caption while the page showed the packing caption; it
  now copies the caption on screen.
- **SEC: reference "from CV tab".** The field "E(Fc⁺/Fc) measured" showed 0.0 while the CV tab's value was used;
  it is now named after the reference chosen in the CV tab and shows its E½ against the electrode ("E½ Fc (CV)",
  "Reference E½ (CV)" for a custom reference); with a manual shift or without a reference found it is called
  "Shift (CV)" and shows the shift used (locked, your own value returns without the chip). The axis uses E½ minus
  the value of the reference vs. Fc⁺/Fc. A missing CV reference is named in the results instead of being dropped, and
  "No results yet" stays above the reference note; without an Fc reference the axis names this tab's electrode instead
  of the CV tab's; the preview follows a changed CV reference when the tab is shown again (export and SI already did).
- **EPR › hyperfine assignment:** the hint sent you to the "Hyperfine" page without a way there; the page name is now
  a link that shows it. Choosing a group still switches nothing by itself. Viewing the "Hyperfine" page no longer
  creates an undo step without a visible change.
- **Choices that act out of sight now say so:** the DFT pages "Charges" and "Multireference" name their
  calculation (with a link to the structures table; their "In the SI" chips apply per calculation); X-ray "Distances
  in the Packing" notes that its ticks act only on the packing figure (link to the figure choice) while the molecule is
  shown; the NICS figure choice notes that export and SI contain scan and 3D; in the reaction path "Insert › 3D/orbital
  view" names the chosen 3D source.
- **Reaction path follow-ups:** the page "Charges" is there as soon as a path opens (it appeared only after the first
  visit of "3D / Orbitals"); a path with only an IRC shows one blue button ("Export profile"), not also the guide's;
  inserting an IRC whose output lists geometric parameters no longer fails (stamp); "Style to defaults" keeps your axis
  title and the signs (+18.9, ±0.0: they change printed values); the path list (☰) is a table with a header (preview and
  name left-aligned); closing a path without changes no longer rewrites its project file and preview; a path redraws
  with the window's text format when shown again (after a language or theme switch inside a compound with its own format
  it kept that format); "Copy" of your own composition caption works even when an inserted profile is outdated; the
  embedded orbital view keeps its button grey without a Python event filter.
- **Reaction path, Compose:** "Edit figure …" names where a profile is edited ("Calculation Data", then "Update
  profiles"), in its tooltip and in the message when the page changes; the tooltip of "Reset" names both entries.
- **Dropping files no longer replaces UV-Vis (ε) data unnoticed.** Measurement files dropped on the UV-Vis kinetics tab
  are added there; on the fluorescence tab the app asks to choose absorption or emission in the Data card and loads
  nothing. Measurement data without concentrations that replace the ε data are now one undo step (before, undo could
  not bring the previous ε evaluation back).
- **Whole SI:** the setup text of the H-cell tab appears in "Materials and Methods" like those of the other tabs.
- **SI (Word):** deselecting "DFT" under "Figures" also leaves out the orbital, NBO and resonance-structure images of
  the calculations (the geometry image and the tables stay with the part "DFT").
- **Project page and overview:** "Export (current tab)", "Export SI section", "Export data package" and "Fonts and frames" are
  disabled there (they acted on a hidden tab or asked for a new compound); in an open comparison Ctrl+E exports the
  comparison.
- The tooltip of "Presets ▾ › Save preset" no longer refers to a save button in the toolbar.
- **UV-Vis (ε): new measurement data keep the settings of a series** that still exists in them (photo, solvent,
  background removal, solution colour, "structure in the figure"); before, loading or dropping new data reset them, and
  the next save made the loss permanent. Label positions and per-band cutoffs start anew (they belong to the old bands).
- **Further, SI text tab:** shows the caption of the displayed figure (and in the footer); before, it said "No caption
  yet" although the figure had one.
- **EPR, Results tab:** the S = ½ fits (g, ΔBpp, couplings, R²) are listed in a table with the same numbers as the
  caption; before, the page said "No results yet" although a fit existed.
- **NMR with MNova-SVG source:** the cards of the Display step stay visible but greyed out (tooltip gives the reason)
  instead of leaving the step empty; in the Evaluation step the hint names the cards it applies to.
- **NMR, Raw data:** the folder icon of "TopSpin data …" is visible in the light theme.
- **DFT orbitals (also reaction path):** the threshold field shows only the needed digits ("80 %", not "80.0000 %").
- **NMR (English):** the structure position "auto (free space)" is no longer cut off.
- **Dark theme:** colour buttons have a light border, so a black line colour no longer looks like an empty button.
- **X-Ray/DFT:** the button that resets the look is called "Auf Standard" in German (was just "Darstellung").
- **NMR preview:** the structure is scaled down smoothly before drawing; thin bonds no longer drop out.

## 1.1.0 – 2026-11-13

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
- **Comparison:** normalized UV-Vis spectra can be normalized to a chosen band (**Normalisation [nm]**: the maximum
  within the range becomes 1, e.g. the band above 400 nm instead of the UV band; a compound without a band in the
  range is not shown, and a note says so). The "Comparison" tab shows the comparisons as cards like the
  reaction paths; a click opens the comparison at full window size (figure as large as in the compound tabs), back
  via the breadcrumb. The spectra comparison and the CV stack have the "SI Text" tab with the whole caption to copy. The UV-Vis overlay already had the normalisation range.
- **Reaction path:** the "Design" canvas shows the energy profile right away when a path with calculation data is
  opened for the first time (it used to be empty, also in the example project).
- **Energy diagram:** levels can be dragged sideways with the mouse (in the schematic diagram also in height; the
  energy value stays the real one). New preset "Article": no frame but an arrow, heavy short levels,
  dashed connectors, signed values, name and value in bold italics below the level. Each of these can be set on its
  own: position and font of the labels, signs, axis title (also several lines), level width; plus sections as bars
  with a text below the profile. The unit can be chosen (kcal mol⁻¹, kJ mol⁻¹, eV): values, axis and caption are
  converted. The presets are now a drop-down list.
- **Compound list:** the method dots are all equally spaced (there used to be one wider gap after "m.p.").
- **EPR: choice of baseline.** Besides the polynomial there are "Smooth" (follows a broad background, keeps narrow
  lines, needs no dark spectrum; the only value is the width) and "Spline" (through the means of the signal-free
  ranges). The methods text and the exported spectra state the method.
- **EPR: isothermal decays and Arrhenius.** Against time, a first-order decay is fitted per temperature (k with 95 %
  interval, optionally only the initial phase via "Fit up to loss"); the view "1/T (Arrhenius)" gives E_a and ln A.
  Temperatures are read from the measurement file.
- **CV: diffusion coefficient** from the Randles–Ševčík slope (with number of electrons, electrode area, concentration
  and temperature; interval from the uncertainty of the slope).
- **EPR: joint fit of several S = ½ species.** "Fit together" refines all simulations of one measurement at once.
- **EPR: simulation below the measurement.** When stacked, a simulation used to lie on its measurement; the new switch
  in the card "Simulations" draws it on a level of its own directly below (measured on top, simulated underneath); the distance between the two is adjustable.
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
- **Octet Draw 1.1.2** (was 1.1.1) as the drawing editor: among other things the reagent table reads equivalents
  from the text above the arrow and can be dragged from anywhere on it.

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
