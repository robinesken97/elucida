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
  λ überall ganzzahlig, kaufmännisch gerundet (`core.fmt_lam`, Nutzerwunsch P8 R3).
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
