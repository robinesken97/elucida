---
paths:
  - "elucida/tabs/ir_ea.py"
  - "elucida/tabs/hrms.py"
  - "elucida/formats/opus.py"
  - "elucida/formats/ms_report.py"
  - "elucida/formats/bruker_ms.py"
---

# IR und HRMS: fachliche Regeln (nicht ändern ohne Rückfrage)

- HRMS: calc. = monoisotopisch **mit Elektronenmasse** ([M+H]⁺ = M + 1.007276), calc./found immer 4 Nachkommastellen;
  ppm zur Kontrolle als found − calc (die Massenabteilung gibt das umgekehrte Vorzeichen an). IR: ganze Zahlen,
  absteigend; Bereich standardmäßig der ganze gemessene; mit OPUS-PDF gelten dessen Peakwerte.
  IR-Bild wie der OPUS-Bericht (Nutzerwunsch P10): Labels senkrecht in einer Reihe am Rand, Hilfslinien senkrecht –
  schräg – senkrecht zum Peak (`IRFigure`), ohne Nachkommastellen; %T oben 100 + 2 % (Basislinie sichtbar);
  Farbe des Spektrums wählbar (`ir_color`).
  Basislinie (F3, Haken `ir_base`, Standard aus): konkaves Gummiband wie OPUS-Methode 3 (Patent US 7359815, Amplitude
  Spannweite/2,2 an einem OPUS-8.5-Bericht angepasst, RMS 0,06 %T), BPO/BIO aus dem OPUS-Verlauf, in Absorbanz; nur Bild
  und Peaksuche, nie die Datei; Hinweis, wenn der Verlauf korrigiert und die Datei roh ist. Schwellenlinie (`ir_thr`,
  [ṽ, A], RESET_KEEP): Peaks jenseits der Linie statt Mindesttiefe, Linie nur im Schwellenmodus (nie im Export), mit
  OPUS-PDF gesperrt. Nur OPUS-PDF: Kurve aus den Vektorlinien (`read_ir_pdf_curve`, x stückweise zwischen den Ticks –
  OPUS staucht über 2000 cm⁻¹), unbekanntes Layout ablehnen; Peakwerte bleiben die des PDF.
- HRMS-Tab (seit 1.21) und IR + EA getrennt; `irms`-Zustand alter Projekte: MS-Schlüssel nach `hrms` übernehmen (set_state).
  Spektrum = Linienspektren (Centroide), keine Profilkurve; Isotopenmuster nur zum Vergleich, found bleibt gemessen.
- HRMS aus Bruker-.d (BAF): nur Linienspektren (MS1, ohne Steps); m/z aus Transformator-Blob (Variante int 10,
  112 B): t = Delay + Takt·Index, t = c0 + √(1e12·m'/c1) + c2·m' (Newton), m/z = m' − c6. Geprüft gegen CompassXport
  (eine Messung, alle Peaks auf 4 Nachkommastellen). Unbekannte Varianten **ablehnen**, nicht raten. found = mit der
  Intensität gewichtetes Mittel über den LC-Peak (≥ 50 % des Maximums, zusammenhängend, ± 10 ppm um calc.); Streuung
  immer mit anzeigen. Bericht der Massenabteilung bleibt vorgewählt.
