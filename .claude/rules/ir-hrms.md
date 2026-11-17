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
- Prüfung nach den Richtlinien (1.2.0, Auftrag 2026-11-13; ACS: EA ≤ 0.4 %, Angew.: Doppelbestimmung mit beiden Sätzen
  und Mittel, HRMS-Genauigkeit 5 ppm): `SI.ea_check` (Werte wie gedruckt, Mittel exakt kaufmännisch auf 0.01) prüft den
  einen Wert bzw. das Mittel; `ea_found2` optional, ohne ihn bleibt die Zeile unverändert, mit ihm „found … and …
  (average …)“. `ea_reason` nur ohne gefundene Werte → „Elemental analysis: <Text>“ (`SI.ea_reason_line`). Tabelle
  `tbl_ea` (Element, Wert/Mittel, Δ, Status) und `tbl_ms` (Ion, calc., found, Δ ppm, Status) über `summary_grid`,
  Abweichung in `WARN_COLOR`, Kacheln über `kpis()` (drittes Element = Warnfarbe). Nur Hinweise, nichts wird abgelehnt.
- IR berechnet gegen gemessen (Paket B 1.2.0, Karte „IR-Rechnung“, `irc_*`): Moden über `CALC.read_ir_modes` (Frequenzen
  wie der DFT-Tab, Intensitäten ORCA „IR SPECTRUM“ nur mit km/mol-Spalte, Gaussian „IR Inten“ des letzten Frequenzjobs;
  sonst ablehnen). Skalierung Vorgabe 1.000, nur vom Nutzer (kein Faktor aus Tabellen). Bild: `calc_ir_profile`
  (Lorentz, gemeinsame FWHM; aus = Linien) normiert, `calc_ir_display` setzt die stärkste Bande auf die Spannweite der
  gemessenen Absorbanz, Grundlinie auf der gemessenen; %T: nur das berechnete Spektrum umgerechnet. Zuordnung
  `assign_bands`: von Hand (`irc_pairs` [ṽ gerundet, Modenindex]) immer, automatisch nur eindeutig (eine Mode ab
  `IRC_MIN_REL` in ±Toleranz und diese Mode bei keiner anderen freien Bande). Δṽ = gemessen − berechnet, ganzzahlig.
  SI: Tabelle über `si_calc_tables` (Einzel-SI nach den Abbildungen, Gesamt-SI Kapitel Rechnungen), Unterschrift mit
  `level_of_theory`, Skalierung, Verbreiterung, nie das Programm.

- Raman (1.2.0, Karte „Raman“, `ram_*`): Datei nur als Textspalten (`formats/xy.read_xy`: erste zwei Zahlenspalten,
  Kopfzeilen übersprungen, Binärdateien abgelehnt – lokal lag keine Gerätedatei, deshalb kein Geräteleser). Peaks =
  Maxima auf 0–1 normiert (`pick_peaks(..., "A")`, Schwelle `ram_prom`), ohne w/m/s. SI-Zeile `raman_line`:
  „Raman (λexc = … nm): ṽ = …, … cm-1“ (ganze Zahlen, absteigend), im Absatz hinter IR (`si_char_parts` nimmt „Raman“
  als Art ir). Abbildung `ram_view`: ir | raman (x steigend, „Raman shift [cm⁻¹]“, y ohne Zahlen „intensity [arb. u.]“)
  | stack (IR oben, Raman unten, je auf 0–1 der gezeigten Spanne, x fallend wie IR, keine Peaklabels). Berechnetes Raman
  nur aus Aktivitäten derselben Rechnung (`read_ir_modes()["raman"]`: ORCA „RAMAN SPECTRUM“ Spalte Activity, Gaussian
  „Raman Activ“; fehlen sie oder passen nicht zu den Frequenzen -> None, kein Bild), Profil wie IR (`calc_ir_profile`,
  `irc_scale`/`irc_fwhm`), stärkste Bande = gemessene Spannweite; Aktivitäten werden nicht in Intensitäten umgerechnet
  (Unterschrift sagt „calculated Raman activities“).
