"""elucida/core/nmr_impurities.py - Restsignale deuterierter Lösungsmittel und häufiger Verunreinigungen (¹H, ¹³C) nach
G. R. Fulmer, A. J. M. Miller, N. H. Sherden, H. E. Gottlieb, A. Nudelman, B. M. Stoltz, J. E. Bercaw, K. I. Goldberg,
Organometallics 2010, 29, 2176–2179, DOI 10.1021/om100106e: Tabelle 1 (¹H, δ in ppm, mit Multiplizität) und Tabelle 2
(¹³C{¹H}, δ in ppm), je Spalte ein Lösungsmittel. Literaturkonstanten (wie die Bondi-Radien), keine Messwerte.

Abschrift: zwei unabhängige Abschriften aus dem Verlags-PDF, 1753 Werte (Tabelle 1: 845, Tabelle 2: 908), Werte und
Reihenfolge identisch; Tabelle 2 zusätzlich gegen Tabelle S2 der Supporting Information der Arbeit geprüft (jeder Wert
kommt dort vor). Ein Erratum gibt es nicht (Crossref ohne „update-to“, Stand 2026-11-14); der Abschnitt „Corrections“ der
SI betrifft die ältere Arbeit von Gottlieb et al. (1997), deren korrigierte Werte hier schon stehen.

Form wie gedruckt: eine Textzeile je Druckzeile, Spalten durch „|“ getrennt (Stoff | Gruppe | Multiplizität | 12
Lösungsmittel); leere Zelle = kein Wert. Mehrere Restsignale eines Lösungsmittels stehen untereinander in eigenen Zeilen
(Druckreihenfolge). Bereiche bleiben Text („0.85-0.91“). Fußnoten als „^Buchstabe“ hinter Stoff, Multiplizität oder Wert
(Buchstaben der Fußnoten der Arbeit; Tabelle 1: a–h, Tabelle 2: a–e); `rows` liefert sie getrennt in `note`
(„compound:f“, „shift:b“).
"""
from __future__ import annotations

import re

SOURCE = "Fulmer 2010"
DOI = "10.1021/om100106e"
SOLVENTS = ("THF-d8", "CD2Cl2", "CDCl3", "toluene-d8", "C6D6", "C6D5Cl", "(CD3)2CO", "(CD3)2SO", "CD3CN", "TFE-d3",
            "CD3OD", "D2O")
SOLVENT_ROW = {"1": "solvent residual signals", "2": "solvent signals"}    # Zeile der Lösungsmittelsignale (wie gedruckt)
TABLE_1H = """\
compound | group | mult | THF-d8 | CD2Cl2 | CDCl3 | toluene-d8 | C6D6 | C6D5Cl | (CD3)2CO | (CD3)2SO | CD3CN | TFE-d3 | CD3OD | D2O
solvent residual signals |  |  | 1.72 | 5.32 | 7.26 | 2.08 | 7.16 | 6.96 | 2.05 | 2.50 | 1.94 | 5.02 | 3.31 | 4.79
solvent residual signals |  |  | 3.58 |  |  | 6.97 |  | 6.99 |  |  |  | 3.88 |  |
solvent residual signals |  |  |  |  |  | 7.01 |  | 7.14 |  |  |  |  |  |
solvent residual signals |  |  |  |  |  | 7.09 |  |  |  |  |  |  |  |
water | OH | s | 2.46 | 1.52 | 1.56 | 0.43 | 0.40 | 1.03 | 2.84^b | 3.33^b | 2.13 | 3.66 | 4.87 |
acetic acid | CH3 | s | 1.89 | 2.06 | 2.10 | 1.57 | 1.52 | 1.76 | 1.96 | 1.91 | 1.96 | 2.06 | 1.99 | 2.08
acetone | CH3 | s | 2.05 | 2.12 | 2.17 | 1.57 | 1.55 | 1.77 | 2.09 | 2.09 | 2.08 | 2.19 | 2.15 | 2.22
acetonitrile | CH3 | s | 1.95 | 1.97 | 2.10 | 0.69 | 0.58 | 1.21 | 2.05 | 2.07 | 1.96 | 1.95 | 2.03 | 2.06
benzene | CH | s | 7.31 | 7.35 | 7.36 | 7.12 | 7.15 | 7.20 | 7.36 | 7.37 | 7.37 | 7.36 | 7.33 |
tert-butyl alcohol | CH3 | s | 1.15 | 1.24 | 1.28 | 1.03 | 1.05 | 1.12 | 1.18 | 1.11 | 1.16 | 1.28 | 1.40 | 1.24
tert-butyl alcohol | OH | s^c | 3.16 |  |  | 0.58 | 0.63 | 1.30 |  | 4.19 | 2.18 | 2.20 |  |
chloroform | CH | s | 7.89 | 7.32 | 7.26 | 6.10 | 6.15 | 6.74 | 8.02 | 8.32 | 7.58 | 7.33 | 7.90 |
18-crown-6 | CH2 | s | 3.57 | 3.59 | 3.67 | 3.36 | 3.39 | 3.41 | 3.59 | 3.51 | 3.51 | 3.64 | 3.64 | 3.80
cyclohexane | CH2 | s | 1.44 | 1.44 | 1.43 | 1.40 | 1.40 | 1.37 | 1.43 | 1.40 | 1.44 | 1.47 | 1.45 |
1,2-dichloroethane | CH2 | s | 3.77 | 3.76 | 3.73 | 2.91 | 2.90 | 3.26 | 3.87 | 3.90 | 3.81 | 3.71 | 3.78 |
dichloromethane | CH2 | s | 5.51 | 5.33 | 5.30 | 4.32 | 4.27 | 4.77 | 5.63 | 5.76 | 5.44 | 5.24 | 5.49 |
diethyl ether | CH3 | t, 7 | 1.12 | 1.15 | 1.21 | 1.10 | 1.11 | 1.10 | 1.11 | 1.09 | 1.12 | 1.20 | 1.18 | 1.17
diethyl ether | CH2 | q, 7 | 3.38 | 3.43 | 3.48 | 3.25 | 3.26 | 3.31 | 3.41 | 3.38 | 3.42 | 3.58 | 3.49 | 3.56
diglyme | CH2 | m | 3.43 | 3.57 | 3.65 | 3.43 | 3.46 | 3.49 | 3.56 | 3.51 | 3.53 | 3.67 | 3.61 | 3.67
diglyme | CH2 | m | 3.53 | 3.50 | 3.57 | 3.31 | 3.34 | 3.37 | 3.47 | 3.38 | 3.45 | 3.62 | 3.58 | 3.61
diglyme | OCH3 | s | 3.28 | 3.33 | 3.39 | 3.12 | 3.11 | 3.16 | 3.28 | 3.24 | 3.29 | 3.41 | 3.35 | 3.37
dimethylformamide | CH | s | 7.91 | 7.96 | 8.02 | 7.57 | 7.63 | 7.73 | 7.96 | 7.95 | 7.92 | 7.86 | 7.97 | 7.92
dimethylformamide | CH3 | s | 2.88 | 2.91 | 2.96 | 2.37 | 2.36 | 2.51 | 2.94 | 2.89 | 2.89 | 2.98 | 2.99 | 3.01
dimethylformamide | CH3 | s | 2.76 | 2.82 | 2.88 | 1.96 | 1.86 | 2.30 | 2.78 | 2.73 | 2.77 | 2.88 | 2.86 | 2.85
1,4-dioxane | CH2 | s | 3.56 | 3.65 | 3.71 | 3.33 | 3.35 | 3.45 | 3.59 | 3.57 | 3.60 | 3.76 | 3.66 | 3.75
DME | CH3 | s | 3.28 | 3.34 | 3.40 | 3.12 | 3.12 | 3.17 | 3.28 | 3.24 | 3.28 | 3.40 | 3.35 | 3.37
DME | CH2 | s | 3.43 | 3.49 | 3.55 | 3.31 | 3.33 | 3.37 | 3.46 | 3.43 | 3.45 | 3.61 | 3.52 | 3.60
ethane | CH3 | s | 0.85 | 0.85 | 0.87 | 0.81 | 0.80 | 0.79 | 0.83 | 0.82 | 0.85 | 0.85 | 0.85 | 0.82
ethanol | CH3 | t, 7 | 1.10 | 1.19 | 1.25 | 0.97 | 0.96 | 1.06 | 1.12 | 1.06 | 1.12 | 1.22 | 1.19 | 1.17
ethanol | CH2 | q, 7^d | 3.51 | 3.66 | 3.72 | 3.36 | 3.34 | 3.51 | 3.57 | 3.44 | 3.54 | 3.71 | 3.60 | 3.65
ethanol | OH | s^c,d | 3.30 | 1.33 | 1.32 | 0.83 | 0.50 | 1.39 | 3.39 | 4.63 | 2.47 |  |  |
ethyl acetate | CH3CO | s | 1.94 | 2.00 | 2.05 | 1.69 | 1.65 | 1.78 | 1.97 | 1.99 | 1.97 | 2.03 | 2.01 | 2.07
ethyl acetate | CH2CH3 | q, 7 | 4.04 | 4.08 | 4.12 | 3.87 | 3.89 | 3.96 | 4.05 | 4.03 | 4.06 | 4.14 | 4.09 | 4.14
ethyl acetate | CH2CH3 | t, 7 | 1.19 | 1.23 | 1.26 | 0.94 | 0.92 | 1.04 | 1.20 | 1.17 | 1.20 | 1.26 | 1.24 | 1.24
ethylene | CH2 | s | 5.36 | 5.40 | 5.40 | 5.25 | 5.25 | 5.29 | 5.38 | 5.41 | 5.41 | 5.40 | 5.39 | 5.44
ethylene glycol | CH2 | s^e | 3.48 | 3.66 | 3.76 | 3.36 | 3.41 | 3.58 | 3.28 | 3.34 | 3.51 | 3.72 | 3.59 | 3.65
H grease^f | CH3 | m | 0.85-0.91 | 0.84-0.90 | 0.84-0.87 | 0.89-0.96 | 0.90-0.98 | 0.86-0.92 | 0.90 | 0.82-0.88 |  | 0.88-0.94 | 0.86-0.93 |
H grease | CH2 | br s | 1.29 | 1.27 | 1.25 | 1.33 | 1.32 | 1.30 | 1.29 | 1.24 |  | 1.33 | 1.29 |
hexamethylbenzene | CH3 | s | 2.18 | 2.20 | 2.24 | 2.10 | 2.13 | 2.10 | 2.17 | 2.14 | 2.19 | 2.24 | 2.19 |
n-hexane | CH3 | t, 7 | 0.89 | 0.89 | 0.88 | 0.88 | 0.89 | 0.85 | 0.88 | 0.86 | 0.89 | 0.91 | 0.90 |
n-hexane | CH2 | m | 1.29 | 1.27 | 1.26 | 1.22 | 1.24 | 1.19 | 1.28 | 1.25 | 1.28 | 1.31 | 1.29 |
HMDSO | CH3 | s | 0.07 | 0.07 | 0.07 | 0.10 | 0.12 | 0.10 | 0.07 | 0.06 | 0.07 | 0.08 | 0.07 | 0.28
HMPA | CH3 | d,9.5 | 2.58 | 2.60 | 2.65 | 2.42 | 2.40 | 2.47 | 2.59 | 2.53 | 2.57 | 2.63 | 2.64 | 2.61
hydrogen | H2 | s | 4.55 | 4.59 | 4.62 | 4.50 | 4.47 | 4.49 | 4.54 | 4.61 | 4.57 | 4.53 | 4.56 |
imidazole | CH(2) | s | 7.48 | 7.63 | 7.67 | 7.30 | 7.33 | 7.53 | 7.62 | 7.63 | 7.57 | 7.61 | 7.67 | 7.78
imidazole | CH(4,5) | s | 6.94 | 7.07 | 7.10 | 6.86 | 6.90 | 7.01 | 7.04 | 7.01 | 7.01 | 7.03 | 7.05 | 7.14
methane | CH4 | s | 0.19 | 0.21 | 0.22 | 0.17 | 0.16 | 0.15 | 0.17 | 0.20 | 0.20 | 0.18 | 0.20 | 0.18
methanol | CH3 | s^g | 3.27 | 3.42 | 3.49 | 3.03 | 3.07 | 3.25 | 3.31 | 3.16 | 3.28 | 3.44 | 3.34 | 3.34
methanol | OH | s^c,g | 3.02 | 1.09 | 1.09 |  |  | 1.30 | 3.12 | 4.01 | 2.16 |  |  |
nitromethane | CH3 | s | 4.31 | 4.31 | 4.33 | 3.01 | 2.94 | 3.59 | 4.43 | 4.42 | 4.31 | 4.28 | 4.34 | 4.40
n-pentane | CH3 | t, 7 | 0.89 | 0.89 | 0.88 | 0.87 | 0.87 | 0.84 | 0.88 | 0.86 | 0.89 | 0.90 | 0.90 |
n-pentane | CH2 | m | 1.31 | 1.30 | 1.27 | 1.25 | 1.23 | 1.23 | 1.27 | 1.27 | 1.29 | 1.33 | 1.29 |
propane | CH3 | t, 7.3 | 0.90 | 0.90 | 0.90 | 0.89 | 0.86 | 0.84 | 0.88 | 0.87 | 0.90 | 0.90 | 0.91 | 0.88
propane | CH2 | sept, 7.3 | 1.33 | 1.32 | 1.32 | 1.32 | 1.26 | 1.26 | 1.31 | 1.29 | 1.33 | 1.33 | 1.34 | 1.30
2-propanol | CH3 | d, 6 | 1.08 | 1.17 | 1.22 | 0.95 | 0.95 | 1.04 | 1.10 | 1.04 | 1.09 | 1.20 | 1.50 | 1.17
2-propanol | CH | sept, 6 | 3.82 | 3.97 | 4.04 | 3.65 | 3.67 | 3.82 | 3.90 | 3.78 | 3.87 | 4.05 | 3.92 | 4.02
propylene | CH3 | dt, 6.4, 1.5 | 1.69 | 1.71 | 1.73 | 1.55 | 1.55 | 1.58 | 1.68 | 1.68 | 1.70 | 1.70 | 1.70 | 1.70
propylene | CH2(1) | dm, 10 | 4.89 | 4.93 | 4.94 | 4.92 | 4.95 | 4.91 | 4.90 | 4.94 | 4.93 | 4.93 | 4.91 | 4.95
propylene | CH2(2) | dm, 17 | 4.99 | 5.03 | 5.03 | 4.98 | 5.01 | 4.98 | 5.00 | 5.03 | 5.04 | 5.03 | 5.01 | 5.06
propylene | CH | m | 5.79 | 5.84 | 5.83 | 5.70 | 5.72 | 5.72 | 5.81 | 5.80 | 5.85 | 5.87 | 5.82 | 5.90
pyridine | CH(2,6) | m | 8.54 | 8.59 | 8.62 | 8.47 | 8.53 | 8.51 | 8.58 | 8.58 | 8.57 | 8.45 | 8.53 | 8.52
pyridine | CH(3,5) | m | 7.25 | 7.28 | 7.29 | 6.67 | 6.66 | 6.90 | 7.35 | 7.39 | 7.33 | 7.40 | 7.44 | 7.45
pyridine | CH(4) | m | 7.65 | 7.68 | 7.68 | 6.99 | 6.98 | 7.25 | 7.76 | 7.79 | 7.73 | 7.82 | 7.85 | 7.87
pyrrole | NH | br t | 9.96 | 8.69 | 8.40 | 7.71 | 7.80 | 8.61 | 10.02 | 10.75 | 9.27 |  |  |
pyrrole | CH(2,5) | m | 6.66 | 6.79 | 6.83 | 6.43 | 6.48 | 6.62 | 6.77 | 6.73 | 6.75 | 6.84 | 6.72 | 6.93
pyrrole | CH(3,4) | m | 6.02 | 6.19 | 6.26 | 6.27 | 6.37 | 6.27 | 6.07 | 6.01 | 6.10 | 6.24 | 6.08 | 6.26
pyrrolidine^h | CH2(2,5) | m | 2.75 | 2.82 | 2.87 | 2.54 | 2.54 | 2.64 |  | 2.67 | 2.75 | 3.11 | 2.80 | 3.07
pyrrolidine | CH2(3,4) | m | 1.59 | 1.67 | 1.68 | 1.36 | 1.33 | 1.43 |  | 1.55 | 1.61 | 1.93 | 1.72 | 1.87
silicone grease | CH3 | s | 0.11 | 0.09 | 0.07 | 0.26 | 0.29 | 0.14 | 0.13 | -0.06 | 0.08 | 0.16 | 0.10 |
tetrahydrofuran | CH2(2,5) | m | 3.62 | 3.69 | 3.76 | 3.54 | 3.57 | 3.59 | 3.63 | 3.60 | 3.64 | 3.78 | 3.71 | 3.74
tetrahydrofuran | CH2(3,4) | m | 1.79 | 1.82 | 1.85 | 1.43 | 1.40 | 1.55 | 1.79 | 1.76 | 1.80 | 1.91 | 1.87 | 1.88
toluene | CH3 | s | 2.31 | 2.34 | 2.36 | 2.11 | 2.11 | 2.16 | 2.32 | 2.30 | 2.33 | 2.33 | 2.32 |
toluene | CH(2,4,6) | m | 7.10 | 7.15 | 7.17 | 6.96-7.01 | 7.02 | 7.01-7.08 | 7.10-7.20 | 7.18 | 7.10-7.30 | 7.10-7.30 | 7.16 |
toluene | CH(3,5) | m | 7.19 | 7.24 | 7.25 | 7.09 | 7.13 | 7.10-7.17 | 7.10-7.20 | 7.25 | 7.10-7.30 | 7.10-7.30 | 7.16 |
triethylamine | CH3 | t, 7 | 0.97 | 0.99 | 1.03 | 0.95 | 0.96 | 0.93 | 0.96 | 0.93 | 0.96 | 1.31 | 1.05 | 0.99
triethylamine | CH2 | q,7 | 2.46 | 2.48 | 2.53 | 2.39 | 2.40 | 2.39 | 2.45 | 2.43 | 2.45 | 3.12 | 2.58 | 2.57
"""

# Aceton in TFE-d3 (CO 32.35, CH3 214.98): so gedruckt, auch in Tabelle S2 und der nach δ sortierten TFE-d3-Tabelle der
# SI; vermutlich sind CO und CH3 vertauscht. Bewusst nicht korrigiert: der Hinweis nennt nur den Stoff, nicht die Gruppe.
TABLE_13C = """\
compound | group | mult | THF-d8 | CD2Cl2 | CDCl3 | toluene-d8 | C6D6 | C6D5Cl | (CD3)2CO | (CD3)2SO | CD3CN | TFE-d3 | CD3OD | D2O
solvent signals |  |  | 67.21 | 53.84 | 77.16 | 137.48 | 128.06 | 134.19 | 29.84 | 39.52 | 1.32 | 61.50 | 49.00 |
solvent signals |  |  | 25.31 |  |  | 128.87 |  | 129.26 | 206.26 |  | 118.26 | 126.28 |  |
solvent signals |  |  |  |  |  | 127.96 |  | 128.25 |  |  |  |  |  |
solvent signals |  |  |  |  |  | 125.13 |  | 125.96 |  |  |  |  |  |
solvent signals |  |  |  |  |  | 20.43 |  |  |  |  |  |  |  |
acetic acid | CO |  | 171.69 | 175.85 | 175.99 | 175.30 | 175.82 | 175.67 | 172.31 | 171.93 | 173.21 | 177.96 | 175.11 | 177.21
acetic acid | CH3 |  | 20.13 | 20.91 | 20.81 | 20.27 | 20.37 | 20.40 | 20.51 | 20.95 | 20.73 | 20.91 | 20.56 | 21.03
acetone | CO |  | 204.19 | 206.78 | 207.07 | 204.00 | 204.43 | 204.83 | 205.87 | 206.31 | 207.43 | 32.35 | 209.67 | 215.94
acetone | CH3 |  | 30.17 | 31.00 | 30.92 | 30.03 | 30.14 | 30.12 | 30.60 | 30.56 | 30.91 | 214.98 | 30.67 | 30.89
acetonitrile | CN |  | 116.79 | 116.92 | 116.43 | 115.76 | 116.02 | 115.93 | 117.60 | 117.91 | 118.26 | 118.95 | 118.06 | 119.68
acetonitrile | CH3 |  | 0.45 | 2.03 | 1.89 | 0.03 | 0.20 | 0.63 | 1.12 | 1.03 | 1.79 | 1.00 | 0.85 | 1.47
benzene | CH |  | 128.84 | 128.68 | 128.37 | 128.57 | 128.62 | 128.38 | 129.15 | 128.30 | 129.32 | 129.84 | 129.34 |
tert-butyl alcohol | (CH3)3C |  | 67.50 | 69.11 | 69.15 | 68.12 | 68.19 | 68.19 | 68.13 | 66.88 | 68.74 | 72.35 | 69.40 | 70.36
tert-butyl alcohol | (CH3)3C |  | 30.57 | 31.46 | 31.25 | 30.49 | 30.47 | 31.13 | 30.72 | 30.38 | 30.68 | 31.07 | 30.91 | 30.29
carbon dioxide | CO2 |  | 125.69 | 125.26 | 124.99 | 124.86 | 124.76 | 126.08 | 125.81 | 124.21 | 125.89 | 126.92 | 126.31 |
carbon disulfide | CS2 |  | 193.37 | 192.95 | 192.83 | 192.71 | 192.69 | 192.49 | 193.58 | 192.63 | 193.60 | 196.26 | 193.82 | 197.25
carbon tetrachloride | CCl4 |  | 96.89 | 96.52 | 96.34 | 96.57 | 96.44 | 96.38 | 96.65 | 95.44 | 96.68 | 97.74 | 97.21 | 96.73
chloroform | CH |  | 79.24 | 77.99 | 77.36 | 77.89 | 77.79 | 77.67 | 79.19 | 79.16 | 79.17 | 78.83 | 79.44 |
18-crown-6 | CH2 |  | 71.34 | 70.47 | 70.55 | 70.86 | 70.59 | 70.55 | 71.25 | 69.85 | 71.22 | 70.80 | 71.47 | 70.14
cyclohexane | CH2 |  | 27.58 | 27.38 | 26.94 | 27.31 | 27.23 | 26.99 | 27.51 | 26.33 | 27.63 | 28.34 | 27.96 |
1,2-dichloroethane | CH2 |  | 44.64 | 44.35 | 43.50 | 43.40 | 43.59 | 43.60 | 45.25 | 45.02 | 45.54 | 45.28 | 45.11 |
dichloromethane | CH2 |  | 54.67 | 54.24 | 53.52 | 53.47 | 53.46 | 53.54 | 54.95 | 54.84 | 55.32 | 54.46 | 54.78 |
diethyl ether | CH3 |  | 15.49 | 15.44 | 15.20 | 15.47 | 15.46 | 15.35 | 15.78 | 15.12 | 15.63 | 15.33 | 15.46 | 14.77
diethyl ether | CH2 |  | 66.14 | 66.11 | 65.91 | 65.94 | 65.94 | 65.79 | 66.12 | 62.05 | 66.32 | 67.55 | 66.88 | 66.42
diglyme | CH3 |  | 58.72 | 58.95 | 59.01 | 58.62 | 58.66 | 58.42 | 58.77 | 57.98 | 58.90 | 59.40 | 59.06 | 58.67
diglyme | CH2 |  | 71.17 | 70.70 | 70.51 | 70.92 | 70.87 | 70.56 | 71.03 | 69.54 | 70.99 | 73.05 | 71.33 | 70.05
diglyme | CH2 |  | 72.72 | 72.25 | 71.90 | 72.39 | 72.35 | 72.07 | 72.63 | 71.25 | 72.63 | 71.33 | 72.92 | 71.63
dimethylformamide | CH |  | 161.96 | 162.57 | 162.62 | 161.93 | 162.13 | 162.01 | 162.79 | 162.29 | 163.31 | 166.01 | 164.73 | 165.53
dimethylformamide | CH3 |  | 35.65 | 36.56 | 36.50 | 35.22 | 35.25 | 35.45 | 36.15 | 35.73 | 36.57 | 37.76 | 36.89 | 37.54
dimethylformamide | CH3 |  | 30.70 | 31.39 | 31.45 | 30.64 | 30.72 | 30.71 | 31.03 | 30.73 | 31.32 | 30.96 | 31.61 | 32.03
1,4-dioxane | CH2 |  | 67.65 | 67.47 | 67.14 | 67.17 | 67.16 | 66.95 | 67.60 | 66.36 | 67.72 | 68.52 | 68.11 | 67.19
DME | CH3 |  | 58.72 | 59.02 | 59.08 | 58.63 | 58.68 | 58.31 | 58.45 | 58.03 | 58.89 | 59.52 | 59.06 | 58.67
DME | CH2 |  | 72.58 | 72.24 | 71.84 | 72.25 | 72.21 | 71.81 | 72.47 | 71.17 | 72.47 | 72.87 | 72.72 | 71.49
ethane | CH3 |  | 6.79 | 6.91 | 6.89 | 6.94 | 6.96 | 6.91 | 6.88 | 6.61 | 6.99 | 7.01 | 6.98 |
ethanol | CH3 |  | 18.90 | 18.69 | 18.41 | 18.78 | 18.72 | 18.55 | 18.89 | 18.51 | 18.80 | 18.11 | 18.40 | 17.47
ethanol | CH2 |  | 57.60 | 58.57 | 58.28 | 57.81 | 57.86 | 57.63 | 57.72 | 56.07 | 57.96 | 59.68 | 58.26 | 58.05
ethyl acetate | CH3CO |  | 20.45 | 21.15 | 21.04 | 20.46 | 20.56 | 20.50 | 20.83 | 20.68 | 21.16 | 21.18 | 20.88 | 21.15
ethyl acetate | CO |  | 170.32 | 171.24 | 171.36 | 170.02 | 170.44 | 170.20 | 170.96 | 170.31 | 171.68 | 175.55 | 172.89 | 175.26
ethyl acetate | CH2 |  | 60.30 | 60.63 | 60.49 | 60.08 | 60.21 | 60.06 | 60.56 | 59.74 | 60.98 | 62.70 | 61.50 | 62.32
ethyl acetate | CH3 |  | 14.37 | 14.37 | 14.19 | 14.23 | 14.19 | 14.07 | 14.50 | 14.40 | 14.54 | 14.36 | 14.49 | 13.92
ethylene | CH2 |  | 123.09 | 123.20 | 123.13 | 122.92 | 122.96 | 122.95 | 123.47 | 123.52 | 123.69 | 124.08 | 123.46 |
ethylene glycol | CH2 |  | 64.35 | 64.08 | 63.79 | 64.29 | 64.34 | 64.03 | 64.26 | 62.76 | 64.22 | 64.87 | 64.30 | 63.17
H grease^b | CH2 |  | 30.45 | 30.14 | 29.71 | 30.31 | 30.22 | 30.11 |  |  |  |  |  |
hexamethylbenzene | C |  | 131.88 | 132.09 | 132.21 | 131.72 | 131.79 | 131.54 | 132.22 | 131.10 | 132.61 | 134.04 | 132.53 |
hexamethylbenzene | CH3 |  | 16.71 | 16.93 | 16.98 | 16.84 | 16.95 | 16.68 | 16.86 | 16.60 | 16.94 | 17.04 | 16.90 |
n-hexane | CH3 |  | 14.22 | 14.28 | 14.14 | 14.34 | 14.32 | 14.18 | 14.34 | 13.88 | 14.43 | 14.63 | 14.45 |
n-hexane | CH2(2,5) |  | 23.33 | 23.07 | 22.70 | 23.12 | 23.04 | 22.86 | 23.28 | 22.05 | 23.40 | 24.06 | 23.68 |
n-hexane | CH2(3,4) |  | 32.34 | 32.01 | 31.64 | 32.06 | 31.96 | 31.77 | 32.30 | 30.95 | 32.36 | 33.17 | 32.73 |
HMDSO | CH3 |  | 1.83 | 1.96 | 1.97 | 1.99 | 2.05 | 1.92 | 2.01 | 1.96 | 2.07 | 2.09 | 1.99 | 2.31
HMPA^c | CH3 |  | 36.89 | 36.99 | 36.87 | 36.80 | 36.88 | 36.64 | 37.04 | 36.42 | 37.10 | 37.21 | 37.00 | 36.46
imidazole | CH(2) |  | 135.72 | 135.76 | 135.38 | 135.57 | 135.76 | 135.50 | 135.89 | 135.15 | 136.33 | 136.58 | 136.31 | 136.65
imidazole | CH(4,5) |  | 122.20 | 122.16 | 122.00 | 122.13 | 122.16 | 121.96 | 122.31 | 121.55 | 122.78 | 122.93 | 122.60 | 122.43
methane | CH4 |  | -4.90 | -4.33 | -4.63 | -4.34 | -4.29 | -4.33 | -5.33 | -4.01 | -4.61 | -5.88 | -4.90 |
methanol | CH3 |  | 49.64 | 50.45 | 50.41 | 49.90 | 49.97 | 49.66 | 49.77 | 48.59 | 49.90 | 50.67 | 49.86 | 49.50^d
nitromethane | CH3 |  | 62.49 | 63.03 | 62.50 | 61.14 | 61.16 | 61.68 | 63.21 | 63.28 | 63.66 | 63.17 | 63.08 | 63.22
n-pentane | CH3 |  | 14.18 | 14.24 | 14.08 | 14.27 | 14.25 | 14.10 | 14.29 | 13.28 | 14.37 | 14.54 | 14.39 |
n-pentane | CH2(2,4) |  | 23.00 | 22.77 | 22.38 | 22.79 | 22.72 | 22.54 | 22.98 | 21.70 | 23.08 | 23.75 | 23.38 |
n-pentane | CH2(3) |  | 34.87 | 34.57 | 34.16 | 34.54 | 34.45 | 34.26 | 34.83 | 33.48 | 34.89 | 35.76 | 35.30 |
propane | CH3 |  | 16.60 | 16.63 | 16.63 | 16.65 | 16.66 | 16.56 | 16.68 | 16.34 | 16.73 | 16.93 | 16.80 |
propane | CH2 |  | 16.82 | 16.63 | 16.37 | 16.63 | 16.60 | 16.48 | 16.78 | 15.67 | 16.91 | 17.46 | 17.19 |
2-propanol | CH3 |  | 25.70 | 25.43 | 25.14 | 25.24 | 25.18 | 25.14 | 25.67 | 25.43 | 25.55 | 25.21 | 25.27 | 24.38
2-propanol | CH |  | 66.14 | 64.67 | 64.50 | 64.12 | 64.23 | 64.18 | 63.85 | 64.92 | 64.30 | 66.69 | 64.71 | 64.88
propylene | CH3 |  | 19.27 | 19.47 | 19.50 | 19.32 | 19.38 | 19.32 | 19.42 | 19.20 | 19.48 | 19.63 | 19.50 |
propylene | CH2 |  | 115.74 | 115.70 | 115.74 | 115.89 | 115.92 | 115.86 | 116.03 | 116.07 | 116.12 | 116.38 | 116.04 |
propylene | CH |  | 134.02 | 134.21 | 133.91 | 133.61 | 133.69 | 133.57 | 134.34 | 133.55 | 134.78 | 136.00 | 134.61 |
pyridine | CH(2,6) |  | 150.57 | 150.27 | 149.90 | 150.25 | 150.27 | 149.93 | 150.67 | 149.58 | 150.76 | 149.76 | 150.07 | 149.18
pyridine | CH(3,5) |  | 124.08 | 124.06 | 123.75 | 123.46 | 123.58 | 123.49 | 124.57 | 123.84 | 127.76 | 126.27 | 125.53 | 125.12
pyridine | CH(4) |  | 135.99 | 136.16 | 135.96 | 135.17 | 135.28 | 135.32 | 136.56 | 136.05 | 136.89 | 139.62 | 138.35 | 138.27
pyrrole | CH(2,5) |  | 118.03 | 117.93 | 117.77 | 117.61 | 117.78 | 117.65 | 117.98 | 117.32 | 118.47 | 119.61 | 118.28 | 119.06
pyrrole | CH(3,4) |  | 107.74 | 108.02 | 107.98 | 108.15 | 108.21 | 108.03 | 108.04 | 107.07 | 108.31 | 108.85 | 108.11 | 107.83
pyrrolidine^e | CH2(2,5) |  | 45.82 | 47.02 | 46.93 | 47.12 | 46.86 | 46.75 |  | 46.51 | 47.57 | 47.43 | 47.23 | 46.83
pyrrolidine | CH2(3,4) |  | 26.17 | 25.83 | 25.56 | 25.75 | 25.65 | 25.59 |  | 25.26 | 26.34 | 25.73 | 26.29 | 25.86
silicone grease | CH3 |  | 1.20 | 1.22 | 1.19 | 1.37 | 1.38 | 1.09 | 1.40 |  |  | 2.87 | 2.10 |
tetrahydrofuran | CH2(2,5) |  | 68.03 | 68.16 | 67.97 | 67.75 | 67.80 | 67.64 | 68.07 | 67.03 | 68.33 | 69.53 | 68.83 | 68.68
tetrahydrofuran | CH2(3,4) |  | 26.19 | 25.98 | 25.62 | 25.79 | 25.72 | 25.68 | 26.15 | 25.14 | 26.27 | 26.69 | 26.48 | 25.67
toluene | CH3 |  | 21.29 | 21.53 | 21.46 | 21.37 | 21.10 | 21.23 | 21.46 | 20.99 | 21.50 | 21.62 | 21.50 |
toluene | C(1) |  | 138.24 | 138.36 | 137.89 | 137.84 | 137.91 | 137.65 | 138.48 | 137.35 | 138.90 | 139.92 | 138.85 |
toluene | CH(2,6) |  | 129.47 | 129.35 | 129.07 | 129.33 | 129.33 | 129.12 | 129.76 | 128.88 | 129.94 | 130.58 | 129.91 |
toluene | CH(3,5) |  | 128.71 | 128.54 | 128.26 | 128.51 | 128.56 | 128.31 | 129.03 | 128.18 | 129.23 | 129.79 | 129.20 |
toluene | CH(4) |  | 125.84 | 125.62 | 125.33 | 125.66 | 125.68 | 125.43 | 126.12 | 125.29 | 126.28 | 126.82 | 126.29 |
triethylamine | CH3 |  | 12.51 | 12.12 | 11.61 | 12.39 | 12.35 | 11.87 | 12.49 | 11.74 | 12.38 | 9.51 | 11.09 | 9.07
triethylamine | CH2 |  | 47.18 | 46.75 | 46.25 | 46.82 | 46.77 | 46.36 | 47.07 | 45.74 | 47.10 | 48.45 | 46.96 | 47.19
"""


def rows(table):
    """Druckzeilen -> [dict(compound, group, mult, solvent, shift, note)] je Zelle mit Wert, in Druckreihenfolge (Zeile für
    Zeile, darin nach Lösungsmittel)."""
    out = []
    for line in table.splitlines()[1:]:
        f = [x.strip() for x in line.split("|")]
        f += [""] * (3 + len(SOLVENTS) - len(f))
        comp, cn = (f[0].split("^") + [""])[:2]
        mult, mn = (f[2].split("^") + [""])[:2]
        for solv, cell in zip(SOLVENTS, f[3:]):
            if cell:
                val, sn = (cell.split("^") + [""])[:2]
                note = ";".join(f"{k}:{v}" for k, v in (("compound", cn), ("mult", mn), ("shift", sn)) if v)
                out.append(dict(compound=comp, group=f[1], mult=mult, solvent=solv, shift=val, note=note))
    return out


H1, C13 = rows(TABLE_1H), rows(TABLE_13C)

# Schreibweisen des Lösungsmittels (klein, ohne Leerzeichen) -> Spalte; nur eindeutig deuterierte Namen (Mnova,
# TopSpin-Kurznamen DMSO/MeOD, Summenformeln). Alles andere -> kein Hinweis.
ALIASES = {
    "CDCl3": ("cdcl3", "chloroform-d", "chloroform-d1", "deuterochloroform"),
    "CD2Cl2": ("cd2cl2", "dichloromethane-d2", "methylenechloride-d2", "dichlormethan-d2"),
    "(CD3)2CO": ("(cd3)2co", "acetone-d6", "aceton-d6", "cd3cocd3"),
    "(CD3)2SO": ("(cd3)2so", "dmso-d6", "dmso", "dimethylsulfoxide-d6", "dimethylsulfoxid-d6", "cd3socd3"),
    "C6D6": ("c6d6", "benzene-d6", "benzol-d6"),
    "CD3CN": ("cd3cn", "acetonitrile-d3", "acetonitril-d3"),
    "CD3OD": ("cd3od", "methanol-d4", "meod", "meod-d4"),
    "D2O": ("d2o", "deuteriumoxide", "deuteriumoxid", "water-d2"),
    "THF-d8": ("thf-d8", "tetrahydrofuran-d8", "c4d8o"),
    "toluene-d8": ("toluene-d8", "toluol-d8", "c7d8", "c6d5cd3"),
    "C6D5Cl": ("c6d5cl", "chlorobenzene-d5", "chlorbenzol-d5"),
    "TFE-d3": ("tfe-d3", "cf3cd2od", "trifluoroethanol-d3", "2,2,2-trifluoroethanol-d3", "trifluorethanol-d3"),
}
_ALIAS = {a: k for k, v in ALIASES.items() for a in v}
_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉‐‑–", "0123456789---")


def solvent_key(name):
    """Lösungsmittel wie im NMR-Text oder Feld („CDCl3“, „Chloroform-d“, „DMSO-d₆“) -> Spalte der Tabellen, sonst None."""
    return _ALIAS.get(re.sub(r"\s+", "", (name or "").translate(_SUB)).lower())


TOL = 0.02          # ppm, dazu die halbe letzte Stelle des Signals (29.7 steht für 29.65…29.75); Wahl gemessen, siehe `hits`


def _span(shift):
    """„29.70“, „−0.55“, „128.5 – 128.3“, „0.84-0.87“ (Tabelle 1) -> (untere, obere Grenze, halbe letzte Stelle) in
    10⁻⁴ ppm, sonst None. Ein Strich direkt hinter einer Ziffer trennt einen Bereich, ist kein Minus."""
    vals = re.findall(r"(?<![\d.])-?\d+(?:\.\d*)?", (shift or "").replace("−", "-"))
    if not vals or len(vals) > 2:
        return None
    e4 = [round(float(v) * 10000) for v in vals]
    dec = max(len(v.partition(".")[2]) for v in vals)
    return min(e4), max(e4), 5 * 10 ** (3 - dec) if dec <= 3 else 0


def hits(solvent, shifts, tol=TOL, offset=0.0):
    """¹³C-Signale (Texte wie im NMR-Text) gegen Tabelle 2 im selben Lösungsmittel -> [(Index des Signals, Zeile)].
    Ein Lösungsmittelsignal zählt einzeln; ein anderer Stoff nur, wenn jedes seiner C mit H (Gruppe enthält „H“) ein
    Signal innerhalb `tol` + halbe letzte Stelle hat (quartäre C sind schwach und fehlen oft; ein Stoff nur aus quartären C
    wie CO2 braucht diese). Gemessen an einer veröffentlichten SI: Einzelvergleich traf in 30 % der Zeilen gereinigter
    Verbindungen etwas, die Regel in 9 %. `offset` (ppm, aus `ref_offset`) wird nur für den Vergleich zu jedem Signal
    addiert. Unbekanntes Lösungsmittel -> []."""
    key = solvent_key(solvent)
    if key is None:
        return []
    sig = [_span(s) for s in shifts]
    t4, o4 = round(tol * 10000), round(offset * 10000)

    def near(v):
        v = round(float(v) * 10000)
        return [i for i, sp in enumerate(sig) if sp and sp[0] + o4 - t4 - sp[2] <= v <= sp[1] + o4 + t4 + sp[2]]

    groups = {}
    for k, r in enumerate(r for r in C13 if r["solvent"] == key):
        groups.setdefault(r["compound"] if r["compound"] != SOLVENT_ROW["2"] else k, []).append(r)
    out = []
    for rs in groups.values():
        found = [near(r["shift"]) for r in rs]
        need = [f for r, f in zip(rs, found) if "H" in r["group"]] or found
        if all(need):
            out += [(i, r) for r, f in zip(rs, found) for i in f]
    return sorted(out, key=lambda x: (x[0], x[1]["compound"]))


MAX_OFFSET = 0.5    # ppm: größerer Versatz zwischen beschriftetem Lösungsmittelsignal und Tabelle = kein Abgleich


def ref_offset(solvent, label):
    """Referenzversatz aus dem beschrifteten Lösungsmittelsignal des Spektrums (`label` = (Wert als Text, Name) aus
    `formats.mnova.svg_peak_labels`, z. B. („77.00“, „CDCl3“)) -> (Versatz in ppm, Tabellenwert). Versatz = nächstes
    ¹³C-Lösungsmittelsignal der Tabelle − beschrifteter Wert; nur für den Vergleich, nie für Spektrum oder Zeile.
    (None, None): kein Label, unbekanntes oder anderes Lösungsmittel als in der Zeile (kein Raten); (None, Wert):
    |Versatz| > `MAX_OFFSET` (dann kein Abgleich)."""
    key = solvent_key(solvent)
    if key is None or not label or solvent_key(label[1]) not in (None, key):
        return None, None
    try:
        v = float(str(label[0]).replace("−", "-"))
    except ValueError:
        return None, None
    refs = [float(r["shift"]) for r in C13 if r["solvent"] == key and r["compound"] == SOLVENT_ROW["2"]]
    ref = min(refs, key=lambda x: abs(x - v))
    d = round(ref - v, 4)
    return (d if abs(d) <= MAX_OFFSET else None), ref


H1_MARGIN = 0.01    # ppm um jedes Multiplett (Linienbreite, gerundetes J); wie die Messung an veröffentlichten Berichten


def free_peaks(peaks, signals, freq):
    """Indizes der Peaks (Texte, z. B. aus MNovas Peakbericht), die in keinem Multiplett der ¹H-Zeile liegen. Bereich
    eines Multipletts = Mitte ± halbe Breite erster Ordnung (Σ nₖ·Jₖ aus Multiplizität und J, `nmr_analysis`; „br“
    entfällt, unbekannte Klasse mit J: 6·ΣJ) / `freq` (MHz), bei „m“ der angegebene Bereich, dazu `H1_MARGIN` und die halbe letzte Stelle von Mitte und Peak. Ein Signal
    ohne lesbare Lage schließt nichts aus; ein Peak ohne lesbare Lage ist nie frei."""
    from elucida.core.nmr_analysis import class_letters, first_order_width
    win = []
    for g in signals:
        sp = _span(g.get("shift"))
        if sp is None:
            continue
        js = [float(j) for j in re.findall(r"\d+(?:\.\d+)?", str(g.get("J") or ""))]
        mult = re.sub(r"\bbr\.?\s*|\bb(?=[sdtq]\b)|\s*\bbr\.?$", "", (g.get("mult") or "").strip())   # „br d“ -> „d“
        lets = class_letters(mult)
        # unbekannte Klasse mit J („h“ …): wie lauter Septetts, lieber zu breit als Multiplettlinien als „frei“
        w = first_order_width(mult, js) if lets and len(lets) == len(js) else 6 * sum(js)
        half = round(w / 2 / freq * 10000) + round(H1_MARGIN * 10000) + sp[2]
        win.append((sp[0] - half, sp[1] + half))
    out = []
    for i, p in enumerate(peaks):
        sp = _span(p)
        if sp and not any(lo - sp[2] <= sp[1] and sp[0] <= hi + sp[2] for lo, hi in win):
            out.append(i)
    return out


def hits_1h(solvent, peaks, free, tol=TOL):
    """Freie ¹H-Peaks (`free_peaks`) gegen Tabelle 1 im selben Lösungsmittel -> [(Index des Peaks, Zeile, sicher)].
    Ein Stoff mit mehreren Zeilen in der Spalte zählt (sicher) nur, wenn jede Zeile einen freien Peak innerhalb `tol`
    + halbe letzte Stelle trifft (Bereichswerte wie „0.84-0.87“ als Bereich); ein Stoff mit nur einer Zeile (Wasser,
    Aceton …) und jedes Restsignal des Lösungsmittels sind nur „möglich“ (sicher = False): ein einzelner Wert trifft in
    ¹H zu leicht. Sicher braucht je Zeile einen eigenen Peak (ein Peak zwischen zwei nahen Zeilen zählt nur einmal).
    Der undeuterierte Stoff des Lösungsmittels (`parent`, Toluol in Toluol-d8) ist nie sicher: seine Zeilen liegen auf
    den Restsignalen. Kein Referenzversatz. Unbekanntes Lösungsmittel -> []."""
    key = solvent_key(solvent)
    if key is None:
        return []
    t4 = round(tol * 10000)
    sig = {i: _span(peaks[i]) for i in free}

    def near(v):
        r = _span(v)
        return [i for i, sp in sig.items() if sp and r and sp[0] - t4 - sp[2] <= r[1] and r[0] <= sp[1] + t4 + sp[2]]

    groups = {}
    for k, r in enumerate(r for r in H1 if r["solvent"] == key):
        groups.setdefault(r["compound"] if r["compound"] != SOLVENT_ROW["1"] else k, []).append(r)
    out = []
    for rs in groups.values():
        found = [near(r["shift"]) for r in rs]
        if all(found):
            ok = len(rs) > 1 and rs[0]["compound"] not in parent(key) and _one_each(found)
            out += [(i, r, ok) for r, f in zip(rs, found) for i in f]
    return sorted(out, key=lambda x: (x[0], not x[2], x[1]["compound"]))


def parent(key):
    """Undeuterierte Stoffe zur Spalte `key` (aus den Namen in `ALIASES`, „toluene-d8“ -> toluene), soweit in Tabelle 1."""
    return {re.sub(r"-d\d*$", "", a) for a in ALIASES.get(key, ())} & {r["compound"] for r in H1}


def _one_each(found):
    """Gibt es je Zeile einen anderen Peak? found = Peak-Indizes je Zeile; Zuordnung mit Augmentationspfaden (Kuhn)."""
    own = {}

    def take(k, seen):
        for i in found[k]:
            if i not in seen:
                seen.add(i)
                if i not in own or take(own[i], seen):
                    own[i] = k
                    return True
        return False
    return all(take(k, set()) for k in range(len(found)))
