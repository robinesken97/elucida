**English** | [Deutsch](synthese-bis-si.de.md) · [back to the overview](../../README.md#guides)

# Synthesis and characterisation to the SI

**What you get:** the SI section of one compound as a Word file – "Synthesis of **X**" with an editable ChemDraw scheme
and the procedure, the characterisation paragraph (m.p.; NMR; IR; HR-MS; UV-Vis; elemental analysis) and the spectra
two per page.

**What you need:** the reaction scheme as CDXML (plus a `.cdx` with the same name from ChemDraw so it stays editable
in Word), the NMR spectra as SVG from MestReNova, the IR file from OPUS (or the OPUS PDF printout), the HRMS report of
the mass spectrometry service (.docx) and the elemental analysis values.

![Synthesis tab with example data](../screenshots/synthesis_light_en.png)

## 1. Project and compound

**File → New project…**, then **Compound …** in the toolbar: name (e.g. the sample number) and the compound's CDXML.
Formula and molar mass for all tabs come from it. Enter the melting point there as well.

## 2. Synthesis

In the **Synthesis** tab: choose the scheme (CDXML), then write the procedure. Amounts like
"(1.03 g, 5.00 mmol, 1.0 eq.)" are checked against the reagent table – **From scheme** fills it with starting
materials, reagents and product, **Insert amounts** puts the calculated bracket at the cursor. Deviations beyond the
rounding of the given digits are marked.

## 3. NMR

In the **NMR** tab add the SVG exports from MestReNova or drag them into the window. Nucleus and order (¹H, ¹³C, …,
2D) are recognised. The structure comes from the project's compound and is placed at a free spot; you can drag it in
the preview. Paste the Mnova multiplet report under **NMR line** (all nuclei in one field); the ¹³C line can also be
built with **Line from peak labels**.

## 4. IR and elemental analysis

In the **IR + EA** tab choose the OPUS file or the OPUS PDF printout. With the PDF the OPUS peaks are used exactly,
otherwise bands are searched (peak threshold). Untick bands that should not be listed. For the elemental analysis enter
the found C/H/N/S values, a solvate if needed (`0.5 CH2Cl2`); deviations above 0.4 % are marked.

## 5. HRMS

In the **HRMS** tab choose the report of the mass spectrometry service or drag it into the window. Check formula and
ion; found is the value from the report. With the Bruker raw data (.d) you also get the chromatogram, the averaged
spectrum and the calculated isotope pattern, and you can click a peak.

## 6. UV-Vis and further figures

The UV-Vis line comes from the **UV-Vis (ε)** tab (see [UV-Vis guide](uvvis-epsilon.en.md)). Figures of the overlay,
fluorescence, CV, SEC and EPR tabs go into the SI automatically as soon as those tabs have data.

## 7. Create the SI

**SI (Word)** in the toolbar: choose the parts and export. The file is in `SI/`. Afterwards the program lists
what is still missing (e.g. no melting point). The Word file follows the style of the group's SI (Arial 11, justified,
figure numbers as fields).
