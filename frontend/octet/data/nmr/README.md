# NMR shift table

`shifts.bin.gz` is Octet's table of ¹H, ¹³C, ¹⁹F and ³¹P chemical shifts by atom environment. It is built by
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

5 November 2026: codes start at level 0 (the atom alone, with ^ when it is η-bonded to a metal), so every atom gets
a shift. Atoms η-bonded to a metal (Cp and arene rings) are written one way however the molfile draws them (no
charge, the hydrogens of a ring carbon beside the metal, ~ and ^ bonds), so ferrocene's ten carbons are alike. A
¹H spectrum that gives one atom more different shifts than it has hydrogens leaves that atom out. Held-out tenth:
¹³C 2.29 ppm (36,581 shifts, 22 of them only at level 0), ¹H 0.25 ppm (13,189 shifts, 9 at level 0); the shifts
covered before give the same errors as before, within 0.001 ppm.

8 November 2026: version 3 of the format, and ¹⁹F and ³¹P. Each part of the file names itself: "ONMR", 3, the number
of parts, then per part its nucleus (u8: 0 ¹H, 1 ¹³C, 2 ¹⁹F, 3 ³¹P), whether it is a solvent table (u8), its scale
(u16, 100 or 10) and its count (u32), then the parts' tables as before, with shifts and spreads × scale. ¹⁹F and ³¹P use
× 10, so shifts past ±327 ppm keep their value. ¹⁹F shifts outside −300 to +250 ppm are left out, and for ¹⁹F and ³¹P
so are shifts more than four median absolute deviations from their code's median. P⁺–O⁻, P⁺–C⁻ and S⁺–O⁻ are read as
P=O, P=C and S=O, here and when Octet predicts. The held-out tenth is now chosen by the InChIKey's first block, so a
molecule's stereoisomers are held out with it. Held-out tenth: ¹H 0.26 ppm (13,237 shifts), ¹³C 2.35 ppm (37,275),
¹⁹F 6.18 ppm (645; 42% rated good, MAE 1.45), ³¹P 14.66 ppm (1,431; 19% rated good, MAE 3.50; 13.13 ppm with the
nmrshiftdb2 ID hold-out). The ¹H and ¹³C codes in both versions differ by more than 0.01 ppm in 9 and 24 codes of
263,437 and 777,264, all from the charge-separated bonds above. The file grew from 6.30 to 6.64 MB.

11 November 2026: codes on kinds. An atom's kind is its label with its bonds that are not single and what they go to
(S=O=O for a sulfonyl S, C=O, C*C*N beside a pyridine N). For ¹H, ¹³C and ¹⁹F, spheres 1 and 2 also go in as codes on
kinds ("k:" before the code). Octet tries each after the next sphere by labels and before the same sphere by labels,
so a carbon whose second sphere the table lacks still sees a sulfonyl, carbonyl or ring N beside it. ³¹P has no codes
on kinds: they made it worse (14.66 to 14.78 ppm). The codes by labels are as before. Held-out tenth: ¹H 0.261 to
0.250 ppm (13,237 shifts), ¹³C 2.353 to 2.198 (37,275), ¹⁹F 6.18 to 6.06 (645), ³¹P 14.66 (no change). ¹³C beside a
sulfonyl 4.93 to 2.96 ppm (106 shifts), in heteroaromatic rings 2.99 to 2.65 (5,429), in bridged bicyclics 3.40 to
3.11 (1,222), beside a peroxide O 7.50 to 6.89 (6). ¹H beside a sulfonyl 0.94 to 0.79 (32), in heteroaromatic rings
0.33 to 0.32 (1,043), in bridged bicyclics 0.42 to 0.41 (609), beside a peroxide O 0.20 to 0.21 (7). Hydrogens on
O, N and S are now rated rough: 20% of them were rated good, and those were 0.5 ppm out. The file grew from 6.64 to
7.11 MB.
