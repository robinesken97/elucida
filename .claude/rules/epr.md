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
- Aus der Literaturprüfung 2026-11-12 (Rechnungen gegen Lehrbuch/CODATA, alle Konstanten und Linienformen stimmten):
  (1) Rampen-Zerfall im Zeit-Modus: ∫exp(−E_a/RT)dt mit linear interpolierter Temperatur zwischen den Spektren
  (`DECAY_SUB` Teilschritte; Trapez nur über die Messpunkte ergab bei 10 K Abstand E_a +1,4 %); „wie Skript“ bleibt wie
  das Skript. (2) Ein Fit gehört zu seiner Feldachse (`fit["dB"]`, `fit["mw"]`, `fit_ok`): nach Änderung von Referenz,
  g_lit oder Referenzfrequenz wird sein g nicht mehr berichtet (Unterschrift, Methodentext), die Fit-Anzeige verlangt
  einen neuen Fit. (3) a in MHz = a[mT]·(µ_B/h)·g mit dem gefitteten g (`MU_B_H`; EasySpins `mt2mhz` nimmt g_e).
  Konventionen, die so bleiben: Pseudo-Voigt (Summe, keine Faltung), nur erste Ordnung, keine Isotopologen-Gewichtung.
- Stellen wie berichtet (Nutzerwunsch 2026-11-11 „wissenschaftliche Konvention“, IUPAC 1989 Pure Appl. Chem. 61, 2195):
  g-Faktor (nicht „g-Wert“) überall **vier** Nachkommastellen (`g_text`; maßgeblich ist die Messgenauigkeit, X-Band mit
  Frequenzzähler und Feldkalibrierung ≈ ±0.0001–0.0002, nicht die Präzision des Fits), Aufspaltung a in mT drei, Kopplung
  in MHz zwei (`hfc_texts`), ΔBpp drei; dieselbe Zahl in Fit-Anzeige, Bildunterschrift und Methodentext. Ohne
  Feldkalibrierung nennt der Methodentext das (Methode der g-Bestimmung gehört in die Angaben).
- EPR S = ½: nur isotrop, erste Ordnung; Fit = Grobsuche (Lage, Kopplungsfaktor) + LM; Amplitude linear. Mehrere
  Komponenten je Messung immer gemeinsam linear skalieren. Kalibrierung: ΔB = B(g_fit, ν_ref) − B(g_lit, ν_ref),
  von allen Messungen außer der Referenz abziehen.
- Mehrere S = ½-Spezies an einer Messung (F7, Nutzerwunsch 2026-11-12): „Gemeinsam fitten“ (`fit_joint` →
  `fit_iso_joint`) optimiert g, Kopplungen, Linienbreite (und Lorentz-Anteil) aller zugeordneten eigenen Simulationen
  gleichzeitig, je Spezies eine lineare Amplitude, **keine** geteilten Parameter, **keine** Grobsuche (sie setzte jede
  Spezies auf das stärkste Signal; Startwerte = aktuelle Werte), keine Unsicherheiten. Der Einzelfit läuft über dieselbe
  Schleife (`fit_iso` = Grobsuche + `fit_iso_joint` mit einer Spezies). Der Methodentext nennt den gemeinsamen Fit.
  Geprüft nur an künstlichen Spektren (es gibt keine Messung mit zwei überlagerten Spezies).
- Isotherme Zerfälle (F7, 2026-11-12; wie die SI der Gruppe): Intensität gegen Zeit mit „Zerfall fitten“ → je
  Temperatur I(t) = I0·exp(−k·t), kleinste Quadrate auf den Intensitäten, I0 linear, 95-%-Intervall s²(JᵀJ)⁻¹ mit
  n − 2 und t-Quantil (`fit_first_order`); weniger als drei Punkte: kein Fit, Hinweis. Serie = Messungen mit gleicher
  auf 1 K gerundeter Temperatur **aus der Messdatei** (`ISO_T_STEP`; nie aus Namen). „Fit bis Verlust“ (`kin_loss`,
  Standard 100 %): nur Punkte, bis die Intensität erstmals um diesen Anteil unter dem ersten Punkt liegt. Ansicht
  „1/T (Arrhenius)“ (`int_x` „arr“): ln k gegen 1/T, ungewichtete Gerade (`fit_arrhenius` über `core.linfit`), ein
  Punkt je Temperatur, Intervall aus der Streuung erst ab drei Temperaturen (bei zwei ausdrücklich keines). Mit echten
  Daten nur der Fit einer 100-K-Serie geprüft (k ≈ 0); eine echte Messreihe über mehrere Temperaturen fehlt.
  Bedienung (Nutzerwunsch 2026-11-12 „intuitiv, leicht zu finden“): **eine** Ansichtswahl oben in der Karte
  „Intensität und Kinetik“ (`cmb_view`: Spektren · gegen Zeit · gegen Temperatur · Arrhenius · gegen Nr.; Zustand
  bleibt `mode` + `int_x`), die Karte klappt beim Wählen auf, nur die Felder der Ansicht sind sichtbar (`_view_fields`),
  „Zerfall fitten“ ist ein Schalter (Zielfunktion nur bei der Rampe), Arrhenius schaltet ihn ein. Kein Feld „Ansicht“
  mehr in „Darstellung“. Unter dem grauen Knopf „Gemeinsam fitten“ steht, was fehlt.
- EPR-Zerfall (Nachbau des MATLAB-Skripts der Arbeitsgruppe): Gauß+Gerade, Zentrum nur innerhalb der Messpunkte (sonst beliebige
  Amplitude bei Spektren ohne Signal); Fit-Start per Raster über E_a mit ln A aus T₅₀ (direkter Start scheitert an der
  Korrelation ≈ 1; ohne Halbwert aus dem Stand am Ende). Standard (Nutzerwunsch P6 R1 „akkurat und physikalisch
  sinnvoll“): kleinste Quadrate auf den gemessenen Intensitäten **ohne Min-Max**, Startintensität I0 linear mitgefittet,
  Integral über die Messzeit (beliebiges Temperaturprogramm, auch Haltephasen; Min-Max verschob E_a bei unvollständigem
  Zerfall um bis zu 40 %, 95-%-Intervall traf bei Rauschen nur 23 %), Intervall s²(JᵀJ)⁻¹ mit n − 3 und t-Quantil, Band
  aus der Kovarianz, Kurve an den Messpunkten; „wie Skript“ (Min-Max, konstante Heizrate, √|r|) nur zum Vergleich – hängt
  stark vom Optimierer und von Spektren ohne Signal ab.
- Gestapelt liegt eine Simulation auf der Ebene ihrer Messung; `sim_below` (Nutzerwunsch 2026-11-13) legt sie auf eine
  eigene Ebene direkt darunter, unabhängig von der Listenreihenfolge; Abstand `sim_gap` × Stapelabstand.
- Messreihen (Zeit, Temperatur; Nutzerwunsch 2026-11-10): gestapelt stehen die Namen rechts neben jeder Kurve
  (`cfg["right_ticks"]`), sonst Legende, nie über den Kurven (ohne freie Stelle neben der Achse, `legend_beside`). Beschriftung
  `trace_label`: Name (umbenennbar per Doppelklick in der Liste), Zeit seit dem frühesten Spektrum [min] oder Temperatur [K],
  beide **nur aus der Messdatei** (BES3T DATE/TIME, STMP; nie aus dem Dateinamen, nie geschätzt), fehlt die Angabe: Namen +
  Hinweis. Farbverlauf `ramp` (aus/Viridis/Plasma/Turbo) in Listenreihenfolge, Standard aus; „Umkehren“ dreht die ganze Liste.
  Basislinie rechnet über den gültigen Bereich (NaN-Ränder bei schmalerem Dunkelspektrum, sonst fiel sie still weg).
- Textdateien ohne Feldeinheit im Kopf (Nutzerauftrag 2026-11-12, „was wird geraten?“): die Einheit wird weiter angenommen
  (Median > 1500 -> G, damit gespeicherte Auswertungen gleich bleiben), aber nie stillschweigend: `meta["unit_src"]`
  = `assumed` steht als Hinweis bei der Messung, „Feldeinheit der Datei“ (`field_unit` je Messung, `funit_changed`)
  bestätigt oder ändert sie und verwirft Fits an dieser Messung; eine Einheit im Kopf geht immer vor. Kerntabelle
  `NUCLEAR_SPIN`: nur Kernspins (erste Ordnung braucht kein γ), Spin auch als `I=3/2`; unbekannte Einträge melden.
- Unterschrift der Intensitätsansichten (`intensity_caption`, 2026-11-13): Größe, Feldfenster, Normierung, I·T,
  Temperaturen aus der Datei; nur gezeigte Fits (k, t½ je Temperatur; E_a/A der Rampe; Arrhenius E_a und ln A), ohne
  Intervalle; nie „EPR spectra of …“ für diese Ansichten.
