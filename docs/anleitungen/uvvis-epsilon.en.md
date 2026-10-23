**English** | [Deutsch](uvvis-epsilon.de.md) · [back to the overview](../../README.md#guides)

# UV-Vis: ε from a dilution series

**What you get:** a figure in Origin style (spectra, λ/ε at the bands, inset with the regressions, structure and
cuvette photo), ε per band with standard error and 95 % confidence interval, the UV-Vis line for the SI
("UV-Vis: λmax: 331 nm (ε = 8440 cm-1 M-1), …") and an Excel report to recalculate everything.

**What you need:**

- a dilution series, ideally 4–6 concentrations, all measured in the same cuvette
- the data as Cary CSV/TXT or as DSW/BSW files straight from the instrument (one file per concentration is fine)
- the structure as CDXML (for the picture and the molar mass), optionally a photo of the cuvette (HEIC from an iPhone
  works)

![UV-Vis (ε) with example data](../screenshots/eps_light_en.png)

## 1. Project and compound

**File → New project…**, then **Compound …** in the toolbar with name and CDXML. The molar mass comes from the CDXML.
It is only needed when the concentrations are given in mg/mL.

## 2. Load the data

Drag the files into the window or use **Open measurement data…** in the **UV-Vis (ε)** tab. Several files at once are
merged into one data set.

**Concentrations:** Elucida reads them from the sample names, e.g. `ABC-1-0p5mgml_THF` → series `ABC-1`, 0.5 mg/mL
(`p` is the decimal point; mg/mL, mM and µM are recognised). Without concentrations in the names a table opens. **You
have to choose the unit there explicitly**, so that no wrong ε can come out. "Fill dilution series" puts start,
start/factor, … into the selected rows.

## 3. Check the compound in the tab

Under **Compound** you see structure and molar mass from the project. If the structure should look exactly as in
ChemDraw, also save it there as SVG or PDF with the same name next to the CDXML. A cuvette photo is cut out
automatically.

## 4. Set up the evaluation

- **Path length** of the cuvette (e.g. 1 cm or 0.1 cm).
- **Fit cutoff A** (default 1): points with a higher absorbance are left out of the fit because the detector is no
  longer linear there.
- **Bands:** found automatically; enter shoulders as a list (e.g. `350, 660`) or let them be searched.
- **Baseline:** default "automatic (series)" – only the concentration-independent offset is subtracted.

## 5. Check the results

The **Results** tab next to the figure shows ε with its error, the intercept, R² and notes for every band. Watch out for:

- **At least 3 points** below the cutoff, otherwise there is no fit (note in the table).
- **R² below 0.98:** the band is in the table and the export but not in the figure. With only 4 points R² says little;
  the confidence interval is more meaningful.
- A significant **intercept** points to baseline or linearity problems.
- The tick at λ decides whether a band appears in the figure; double-clicking "Cutoff A" sets an own cutoff for that
  band.

## 6. Arrange the figure

Drag inset, structure, cuvette and every λ/ε label with the mouse; the mouse wheel over inset or picture changes the
size. Optional: indices λ₁/ε₁ …, "(sh)" at shoulders, R² in the figure. **Reset ▾** restores the automatic layout.

## 7. Export and into the SI

**Export** writes the figure (PDF/SVG/PNG), `<series>_results.csv` and the Excel report for all series to
`exports/epsilon/`. The UV-Vis line is under **SI line** and goes into the characterisation paragraph with
**SI (Word)**; the figure with its caption ("UV-Vis spectra of **X** in THF, measured in 0.1 cm quartz cuvettes.") goes
into the figure part. Enter the solvent for that under **Analysis**.

**Copy SI text** gives an English paragraph describing exactly the evaluation steps used (baseline, model, cutoff,
errors) – to append to the methods section.
