---
paths:
  - "elucida/tabs/epr.py"
  - "elucida/formats/epr.py"
---

# EPR: fachliche Regeln (nicht ändern ohne Rückfrage)

- EPR: Reihenfolge hell − k·dunkel → Basislinie → Ausblenden → Glätten → Normieren; Simulation mit dem
  Normierungsfaktor ihrer Messung (Verhältnis bleibt). Triplett-Simulation nicht selbst rechnen (EasySpin), nur
  importieren. Projekte kopieren BES3T-Partnerdateien (.dsc/.DTA/.YGF/.xml) mit.
- Basislinie (Nutzerwunsch 2026-11-12 „alle gängigen und sinnvollen“; `bl_method`, Auswahl in der Karte Verarbeitung,
  Felder folgen dem Verfahren): **Polynom** (Ränder oder signalfreie Bereiche), **Glatt** (`smooth_baseline`:
  Whittaker-Glätter nach Eilers 2003 auf Abschnittsmitteln + **genau ein** robuster Schritt mit symmetrischen
  Bisquare-Gewichten; bis zur Konvergenz iteriert läuft es bei stark gekrümmtem Untergrund davon, gemessen; Wert
  `bl_width` = Periode mit halbem Durchlass), **Spline** (natürlicher kubischer Spline durch die Mittel der Bereiche,
  ohne zwei Bereiche keine Basislinie + Hinweis, nie Stützstellen raten). Bewusst **nicht**: asymmetrische Verfahren
  (AsLS, airPLS, arPLS) – sie setzen einseitige Peaks voraus, Spektren in erster Ableitung gehen nach oben und unten.
  „aus“ bleibt `bl_order` −1 bei jedem Verfahren (ältere Stände lesen das weiter). Der Methodentext nennt Verfahren,
  Breite und Literaturstelle; „Dunkelspektrum für alle“ blendet das Dunkelspektrum selbst aus (es wird nicht
  korrigiert und bestimmte sonst das Bild; t = 0 und Abzug bleiben).
- Stellen wie berichtet (Nutzerwunsch 2026-11-11 „wissenschaftliche Konvention“, IUPAC 1989 Pure Appl. Chem. 61, 2195):
  g-Faktor (nicht „g-Wert“) überall **vier** Nachkommastellen (`g_text`; maßgeblich ist die Messgenauigkeit, X-Band mit
  Frequenzzähler und Feldkalibrierung ≈ ±0.0001–0.0002, nicht die Präzision des Fits), Aufspaltung a in mT drei, Kopplung
  in MHz zwei (`hfc_texts`), ΔBpp drei; dieselbe Zahl in Fit-Anzeige, Bildunterschrift und Methodentext. Ohne
  Feldkalibrierung nennt der Methodentext das (Methode der g-Bestimmung gehört in die Angaben).
- EPR S = ½: nur isotrop, erste Ordnung; Fit = Grobsuche (Lage, Kopplungsfaktor) + LM; Amplitude linear. Mehrere
  Komponenten je Messung immer gemeinsam linear skalieren. Kalibrierung: ΔB = B(g_fit, ν_ref) − B(g_lit, ν_ref),
  von allen Messungen außer der Referenz abziehen.
- EPR-Zerfall (Nachbau des MATLAB-Skripts der Arbeitsgruppe): Gauß+Gerade, Zentrum nur innerhalb der Messpunkte (sonst beliebige
  Amplitude bei Spektren ohne Signal); Fit-Start per Raster über E_a mit ln A aus T₅₀ (direkter Start scheitert an der
  Korrelation ≈ 1; ohne Halbwert aus dem Stand am Ende). Standard (Nutzerwunsch P6 R1 „akkurat und physikalisch
  sinnvoll“): kleinste Quadrate auf den gemessenen Intensitäten **ohne Min-Max**, Startintensität I0 linear mitgefittet,
  Integral über die Messzeit (beliebiges Temperaturprogramm, auch Haltephasen; Min-Max verschob E_a bei unvollständigem
  Zerfall um bis zu 40 %, 95-%-Intervall traf bei Rauschen nur 23 %), Intervall s²(JᵀJ)⁻¹ mit n − 3 und t-Quantil, Band
  aus der Kovarianz, Kurve an den Messpunkten; „wie Skript“ (Min-Max, konstante Heizrate, √|r|) nur zum Vergleich – hängt
  stark vom Optimierer und von Spektren ohne Signal ab.
- Messreihen (Zeit, Temperatur; Nutzerwunsch 2026-11-10): gestapelt stehen die Namen rechts neben jeder Kurve
  (`cfg["right_ticks"]`), sonst Legende, nie über den Kurven (ohne freie Stelle neben der Achse, `legend_beside`). Beschriftung
  `trace_label`: Name (umbenennbar per Doppelklick in der Liste), Zeit seit dem frühesten Spektrum [min] oder Temperatur [K],
  beide **nur aus der Messdatei** (BES3T DATE/TIME, STMP; nie aus dem Dateinamen, nie geschätzt), fehlt die Angabe: Namen +
  Hinweis. Farbverlauf `ramp` (aus/Viridis/Plasma/Turbo) in Listenreihenfolge, Standard aus; „Umkehren“ dreht die ganze Liste.
  Basislinie rechnet über den gültigen Bereich (NaN-Ränder bei schmalerem Dunkelspektrum, sonst fiel sie still weg).
