---
paths:
  - "elucida/core/uvvis.py"
  - "elucida/app/main_window.py"
  - "elucida/si/excel.py"
  - "elucida/si/lines.py"
---

# UV-Vis (ε): fachliche Regeln (nicht ändern ohne Rückfrage)

- ε (M⁻¹ cm⁻¹) **immer ganzzahlig**, Wert und Fehler (Nutzerwunsch P1, wie in den Publikationen: „7264 ± 318“, nicht
  auf die SE-Genauigkeit „7300 ± 300“; `core.fmt_ve`/`ve_decimals`, `eps_max_decimals`); spezifisches a weiter auf die
  Genauigkeit des SE. Sehr kleine Fehler auf 1 Einheit aufrunden, nie „± 0“. Dieselbe Zahl überall (Nutzerwunsch):
  Tabelle, Bild, SI-Zeile, Methodentext und Excel-Zahlenformat (`excel._coef_fmts`); nur die CSV behält Rohwerte.
  λ überall ganzzahlig, kaufmännisch gerundet (`core.fmt_lam`, Nutzerwunsch P8 R3); seit der Literaturprüfung
  2026-11-12 runden auch ε/a und ihre Fehler kaufmännisch (`core.round_half_up`, nie Pythons `round`), ebenso
  Äquivalente und Ausbeuten; Molmassen aus Zeichnungen über `chem.mol_weight` (dieselbe Tabelle `SI.AVG` wie EA).
- Fit: A/d = m·c + b (OLS); ε = m / f_c (f_c: mM 1e-3, µM 1e-6, M 1; mg/mL über die Molmasse; ohne Molmasse
  spezifischer Koeffizient a in L g⁻¹ cm⁻¹). 95-%-KI = t(0,975; n−2)·SE (eigene `t_quantile`).
- R² überall mit derselben Stellenzahl (`core.r2_text`, `core.R2_DIGITS`; Nutzerwunsch 2026-11-11: Standard **2**,
  wählbar je Verbindung im ε-Tab → Erweitert → „R²-Stellen“, `glob["r2_digits"]`, gilt auch für CV, SEC, EPR); nie ein
  eigenes Format an der Stelle. CSV, Excel und Protokoll behalten den vollen Wert.
- Cutoff global (Standard A = 1) und pro Bande; Banden mit R² < `min_r2` (einstellbar, Standard 0,98) stehen in
  Tabelle/CSV/Excel, aber nicht im Bild. Bei 4 Punkten ist R² wenig aussagekräftig, KI zählt.
- Konzentrationsdialog: **keine** vorbelegte Einheit/Startkonzentration (führte früher zu falschem ε). Probennamen mit führender Null
  („05mgml“: 0,5 oder aufgefüllte 5?) gelten als unbekannt, der Dialog fragt (ergab sonst negative ε, wie „p5mM“).
- Messungen je Konzentration abwählbar (`conc`-Eintrag `off`, Liste „Messungen“): fallen aus Fit und Bild (`group_samples`), der
  Methodentext erwähnt das bewusst nicht (Robin: im Bild sichtbar).
- „(sh)“ für Schultern ist abschaltbar; Indizes λ₁/ε₁ … (`label_index`, Standard aus, aufsteigend nach λ, nur Banden
  im Bild; SI-Zeile ohne Indizes); Molmasse aus CDXML inkl. Isotopen.
- UV-Vis-Kinetik (`tabs/uvkin.py`, Nutzerauftrag 2026-11-12): Aufnahmezeit nur aus der Messdatei (Cary-CSV „Collection
  Time“, Blöcke nach **Reihenfolge** der Spalten, nie nach Namen; US-Form mit AM/PM per Regex statt strptime-%p,
  deutsche Form; sonst None), nie Dateiname/Dateidatum; .DSW/.BSW ohne Zeit (parseuv kennt nur die Methodenzeit).
  Gerätebasislinien nie als Spektren. Reihe nur vorbelegt, wenn `parse_sample_name` eine Konzentration eindeutig nennt;
  ohne Reihe keine Auswertung (Hinweis). Absorbanz wie gemessen (keine Schichtdicken-/Konzentrationskorrektur), bei λ
  linear interpoliert oder Maximum in λ ± n nm; Zeit relativ zum ersten Spektrum der Reihe; Zerfall über
  `EPR.fit_first_order` auf den gemessenen Werten, k und t½ in der gewählten Zeiteinheit, k < 0 = keine Halbwertszeit.
  Spektren ohne Zeit nur in „Spektren über die Zeit“ (Hinweis in der anderen Ansicht). Gesättigte Spektren nicht
  automatisch erkennen. Durchgehende Kinetik des Cary-Kinetikprogramms (eine Wellenlänge gegen Zeit) wird nicht
  gelesen (kein Beispiel).
- Fluoreszenz, zeitaufgelöst (`tabs/fluo_tau.py`, `core/lifetime.py`, Leser `formats/decay.py`; Auftrag 2026-11-13,
  SI-Lückenanalyse Punkt 5): Abklingkurve/IRF nur als allgemeiner Text (Spalte 1 Zeit, 2 Intensität; mehr Spalten mit
  Hinweis), kein Herstellerformat ohne echte Beispieldatei. Modell Σ A_i·exp(−t/τ_i) + B (1 oder 2 Exponentiale); mit
  IRF Faltung (Fläche 1, Verschiebung gefittet) über die ganze Kurve, sonst Schwanzfit ab Start nach dem Maximum
  (Methodentext sagt „ohne Entfaltung“). Poisson-Gewichte und χ²_red nur bei ganzzahligen Werten, sonst ungewichtet und
  kein χ². 95-%-Intervall nur für τ_i (s²(JᵀWJ)⁻¹, t(0,975; n − p)); mittlere Lebensdauern (amplituden- und
  intensitätsgewichtet getrennt) ohne Intervall und nur bei positiven Amplituden. Φ ist eine Angabe des Nutzers (0 < Φ ≤ 1),
  k_r/k_nr nur mit Φ und τ, bei zwei Exponentialen mit Hinweis auf die gewählte mittlere Lebensdauer (Standard
  amplitudengewichtet). Fehlende Kennwerte bleiben leer, nie geschätzt.
- UV-Vis-Titration im Kinetik-Tab (Auftrag 2026-11-13, SI-Lückenanalyse Punkt 8): Äquivalente je Zeile (`entries[i]["eq"]`,
  Spalte „Äq.“), vorgeschlagen nur bei genau einem Treffer im Probennamen (bei einer Probe je Datei auch im Dateinamen),
  `eq_from_name`; solche Zeilen brauchen keine Reihe. Ansichten `titr` (Schar, Farbverlauf nach Äquivalenten) und
  `titr_trace` (A bei λ gegen Äq.). Isosbestische Punkte (`isosbestic`): ab drei Spektren, nur wo alle Spektren innerhalb
  der Toleranz (Spannweite) liegen und Δ(letztes − erstes) beiderseits deutlich (> 3·Toleranz) mit Vorzeichenwechsel ist;
  sonst keiner, nie interpoliert oder geschätzt. Markiert als Kreis ohne Text (λ in Unterschrift, Tabelle, Kachel).
  Keine Verdünnungskorrektur, keine Bindungskonstanten. SI: beide Titrationsbilder, wenn eine Titrationsansicht gewählt ist.

## Prüfstand (aus CLAUDE.md)
- BSW-Datei mit Sprung in Spektrum 60 (CSV-Export zum Vergleich fehlt).
