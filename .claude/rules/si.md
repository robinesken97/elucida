---
paths:
  - "elucida/si/**"
  - "elucida/tabs/*.py"
---

# SI-Export und Methodentexte: fachliche Regeln (nicht ändern ohne Rückfrage)

- SI-Export (Werkzeugleiste „SI (Word)“ und Menü): Teile wählbar (Charakterisierung, NMR, Abbildungen aller Tabs,
  X-Ray, DFT; Auswahl in QSettings `si_parts`); DFT zweispaltig über fortlaufenden Abschnittswechsel (`("columns", 2)`
  in `write_docx`). Ohne Charakterisierung nur der Name als Überschrift. `settings.xml` mit compatibilityMode 15
  (sonst Kompatibilitätsmodus).
- SI-Abbildungen (Nutzerwunsch): **immer zwei je Seite** (`SI.two_per_page`: Text vor Abbildungen beginnt eine Seite und
  zählt mit; Bilder im Seitenverhältnis verkleinern, bis Bild + Unterschrift passen – 16 × 11 cm mit zweizeiliger
  Unterschrift sind zu zweit zu hoch; keine Abbildung mit Unterschrift über die halbe Seite). Nach Text (`_fig_capacity`,
  Nutzerwunsch 2026-11-12): so viele (höchstens zwei), wie mit ≥ `MIN_FIG_CM` je Bild Platz haben – also auch **eine** allein,
  wo zwei zu klein würden (vorher blieb der Rest der Seite leer); sonst beginnen die Abbildungen die nächste Seite.
  Ein Energieprofil mit nur einer Stufe kommt nicht in die SI (`dft_pages.si_figures`). Reihenfolge `figure_tabs` (IR, HRMS, ε je Serie, Overlay, Fluoreszenz, CV, SEC,
  EPR). Unterschriften je Tab (`si_caption`): ε „UV-Vis spectra of **X** in THF, measured in 0.1 cm quartz cuvettes.“
  (Lösungsmittel je Serie im Abschnitt Auswertung); CV/SEC/EPR wie die SI der Gruppe aus den Daten (Vorschub,
  iR-Kompensation nur wenn für alle gleich, interne Referenz, Start-/Endpotential, Band aus ν, g/ΔBpp/Kopplungen nur aus
  eigenen S = ½-Fits) plus Felder `cap_*` (`CAP_FIELDS`, Leitsalz gemerkt); `chem_html` stellt Formeln tief, „-1“ hoch (nur Tokens aus
  Elementsymbolen/Abkürzungen: B3LYP, def2-SVP, Figure S12, S1 bleiben; P8).
  Aufbau-Texte (Geräte) nur in QSettings `si_setup/<Tab>` (lokal, nie im Code/Projekt), im Export vor den Abbildungen.
- Geschützte Leerzeichen (`SI.nbsp`, U+00A0) zentral in `write_docx` (Absätze, Unterschriften, Text) und `copy_rich`:
  Zahl ↔ Einheit, um „=“/„±“, in zusammengesetzten Einheiten (cm-1 M-1), Elementaranalyse „C 77.67“, „m.p.“.
  Nicht in Tabellen und Koordinaten (Festbreite). Neue Einheiten in `_UNITS` ergänzen.
- SI-Methodentexte („SI-Text kopieren“, beim Export `…_methods.txt`): jeder Tab, der fittet (ε, CV, SEC, EPR), beschreibt
  englisch **nur die tatsächlich benutzten** Schritte mit den aktuellen Parametern, dann die Ergebnisse; Aufbau/Geräte
  stehen in der SI der Gruppe und nicht im Code. Keine Unsicherheiten erfinden (EPR-S = ½-Fit: ausdrücklich keine).
  Neue Fits → Satz in `methods_text` des Tabs ergänzen. Nie das Programm nennen (Nutzerwunsch: nur die Mathematik).
  Referenz in CV/SEC-Texten und -Unterschriften wie die Achse „Fc0/+“; interner Standard (Ac₂Fc mit E½) nur als
  Hilfsmittel nennen. Exponenten als „-1“ wie in der SI. Im Word-Export als Teil
  `methods` („Data processing and fitting“, `si_methods_blocks`, `SI.methods_html`; neue Fit-Tabs dort eintragen).
- SI-Stil (aus den SI der Gruppe): Absatz „m.p. …; IR …; HR-MS …; UV-Vis: λmax: 350 nm (ε = 12000 cm-1 M-1), …“, durch
  „; “ getrennt, Punkt am Ende. UV-Vis-Zeile nur mit den Banden des Bildes, aufsteigend, ε wie in der Tabelle gerundet
  (ohne ±). EA (Nutzerwunsch 2.3.1, wie die HR-MS-Zeile): „Elemental analysis (%) calc. …: C …; found C …“, 2 Nachkommastellen,
  Warnung > 0.4 %; immer optional (nie als fehlend melden, auch nicht in der Checkliste).
  Word-Export exakt wie die SI-PDF der Gruppe: A4, Ränder 2.5 cm, Arial 11 (Schriftart wählbar über `SI.set_font`/QSettings
  `si_font`, Größe fest wegen `two_per_page`), Blocksatz, 1.5-zeilig; „Synthesis of **Name**“,
  Absatz mit fettem **m.p.**/**IR**/**HR-MS-ESI(+)**/**UV-Vis**/**λ**max, Exponenten als „-1“; „**Figure Sn**: X-ray solid state
  structure of **Name**. Thermal ellipsoids are shown with 50% probability.“ (Besetzung bei Fehlordnung „60% (A) and 40% (B)“);
  ≤ 8 ausgewählte Werte in der Unterschrift, sonst „**Table Sn:** Selected bond lengths/angles for **Name**.“ (Atom | … |
  Length / Å); Kristalldaten mit zentrierter erster Spalte, „a / Å“ usw.; Nummern als Word-SEQ-Felder (fortlaufend).
