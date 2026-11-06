# NMR shift table

`shifts.bin.gz` is Octet's table of ¹H and ¹³C chemical shifts by atom environment. It is built by
`scripts/nmr-table.ts` from the measured spectra in nmrshiftdb2's `nmrshiftdb2withsignals.sd`
(downloaded 16 October 2026 from https://sourceforge.net/projects/nmrshiftdb2/files/data/). Spectra the file marks
as predicted are left out.

Contains information from nmrshiftdb2 (www.nmrshiftdb.org), which is made available here under the
[nmrshiftdb2 Database License](https://nmrshiftdb.nmr.uni-koeln.de/nmrshiftdbhtml/nmrshiftdb2datalicense.txt).
A copy of the licence is in `LICENCE.txt`. This table is a derivative database under that licence, so it is shared
under the same licence. Octet's code is Apache-2.0 (an OSI-approved licence, as section 4.5 requires).

Format: "ONMR", version 2 and the four table sizes, then for ¹³C and then ¹H the code hashes (u32), median shifts
(i16, ppm × 100), standard deviations (u16, ppm × 100) and counts (u16), little-endian, sorted by hash. Then the same
for the solvent tables, ¹³C and ¹H: codes as measured in one of the Spectrum panel's solvents (from the file's Solvent
field), kept where their shifts there differ from those in every solvent. The ¹H solvent table is empty: on the
held-out tenth it made ¹H shifts worse. Version 1 files have no solvent tables.

Rebuild: `node scripts/nmr-table.ts <path to nmrshiftdb2withsignals.sd>`. Add `--test` to measure accuracy on one
molecule in ten held out (16 October 2026: ¹³C mean absolute error 2.27 ppm, median 0.90; ¹H 0.25 ppm, median 0.09.
18 October 2026: for ¹³C shifts measured in a known solvent, 2.12 ppm from every solvent and 2.08 with the solvent
table).
