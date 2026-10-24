**English** | [Deutsch](elektrochemie.de.md) · [back to the overview](../../README.md#guides)

# Electrochemistry: CV and SEC

**What you get:** cyclic voltammograms with E½, ΔEₚ and peak current ratio (Nicholson), the analysis versus scan rate
(Randles–Ševčík with confidence interval), referencing against Fc⁺/Fc and from that the figures with SI caption and a
methods paragraph. In the SEC tab the spectrum series during the potential scan.

**What you need:** Gamry .DTA files (e.g. a scan-rate series), ideally one measurement with an internal standard (Fc
or Ac₂Fc). For SEC the spectrum series from B&W Tek BWSpec (text export) and the .DTA of the potential scan.

![CV tab](../screenshots/cv_dark_en.png)

## 1. Load the measurements (CV)

In the **CV** tab add one or more .DTA files with **Measurement…**. Scan rate and electrode area come from the file.
The **group** per measurement (e.g. the solvent) separates the data series in the plots against scan rate.

## 2. Redox couples

**Suggest** finds the couples; you can adjust the windows (from–to, on the scale of the x axis). Values marked red in
the results mean: peak at the window edge – widen the window. The **baseline** (on by default) subtracts the charging
current before the peak; the peak potentials stay unchanged.

## 3. Referencing

Under **Referencing** choose: as measured, internal (Fc or Ac₂Fc couple in one of the measurements; default Ac₂Fc
+0.49 V vs. Fc⁺/Fc, please check against your literature) or a fixed shift. When comparing several solvents every
measurement gets its own standard (click the measurement → reference of the selected measurement).

## 4. Results and plots

The **Results** tab next to the figure shows E_pa, E_pc, E½, ΔEₚ, i_pa, i_pc and i_r/i_f per measurement and couple.
Under **Plot** you can choose, besides the CV, ΔEₚ vs. v, Randles–Ševčík, log i vs. log v, chemical reversibility or the
trumpet plot. Note: ΔEₚ also contains the iR drop (especially in THF).

## 5. Spectroelectrochemistry (SEC)

In the **SEC** tab choose the spectrum series and the potential file. Every spectrum gets its potential from the clock
time (set a **time offset** if needed). **View:** spectrum series, difference spectra or A at λ versus E with an
apparent Nernst fit – with a continuous scan the thin-layer cell lags behind, the CV values take precedence. Highlight
intermediate species by their potential.

## 6. Export and SI

**Export** writes the figure, the results (CSV) and the methods paragraph. Fill in the **figure caption** fields
(concentration, solvent, electrolyte) – the caption then reads like the group's SI. **Copy SI text** gives the English
paragraph on the analysis.
