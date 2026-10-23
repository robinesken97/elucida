**English** | [Deutsch](struktur-dft.de.md) · [back to the overview](../../README.md#guides)

# Crystal structure and DFT

**What you get:** an ORTEP figure in Mercury style (or ball and stick), selected bond lengths and angles with standard
deviations exactly from the CIF, the crystal data table for the SI and, for DFT calculations, an SI block with
coordinates, energies and convergence.

**What you need:** the CIF (e.g. from Olex2 or the CCDC); for DFT xyz files or outputs of ORCA 6 (.out) or Gaussian
(.log).

![X-ray tab with example data](../screenshots/xray_light_en.png)

## 1. Load the CIF

Drag the CIF into the window or use **Add CIF …** in the **X-Ray** tab. Every `data_` block with atoms becomes an entry.
The molecule is completed by symmetry; with disorder the default shows the main part.

## 2. View

**Dragging rotates**, the right button pans, the wheel zooms. Under **Display** choose style, ellipsoids (50 %), labels
and background. Solvents and counter-ions can be hidden, single atoms under **Atoms and fragments**, bulky groups shown
as wireframe. **Orientation** turns a bond downwards or a plane to the front.

## 3. Bonds and angles

Click atoms: 2 = distance, 3 = angle, 4 = torsion. Values with standard deviation come **exactly from the CIF** (e.g.
1.392(3)); if a value is missing it is calculated and marked without a standard deviation. Chosen values go into the
caption or – more than eight – into a table.

## 4. Tables and caption

The **Caption** and **Tables** tabs next to the figure show the suggested caption and the crystal data table. Enter the
internal reference and the CCDC number in the structure list. **Copy** keeps italics and super-/subscripts in Word.

## 5. DFT

In the **DFT** tab add the xyz or output file. Rotate and measure as in the X-ray tab. To renumber press **Number
atoms** and click the atoms in order, then **Apply** – or take the numbering **like template** from another geometry or
the CIF. **Save xyz** writes a new file (lines unchanged, only reordered).

**Orbitals:** in the **Orbitals** card add a Molden file (ORCA: `orca_2mkl name -molden`) or a cube (ORCA:
`orca_plot`). If it matches the selected geometry it is attached there. HOMO and LUMO are added, further MOs via
**From Molden** and **+**. Drawn as in IboView (isosurface enclosing 80% of the orbital density); the export writes
one figure per orbital.

## 6. SI

The **Calculation for the SI** tab shows the block with charge, multiplicity, point group, coordinates and E_el/H/G.
**SI (Word)** puts the crystal structure and the DFT calculations (two columns) into the SI section.
