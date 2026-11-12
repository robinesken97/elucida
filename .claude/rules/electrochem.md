---
paths:
  - "elucida/tabs/cv.py"
  - "elucida/tabs/sec.py"
  - "elucida/formats/gamry.py"
  - "elucida/formats/bwspec.py"
---

# CV und SEC: fachliche Regeln (nicht ändern ohne Rückfrage)

- CV: Strom wie aufgezeichnet (Gamry IUPAC, anodisch positiv); Paare nur im Fenster (gespeichert in gemessenen
  Potentialen, angezeigt in Achsenskala); i_pc/i_pa nach Nicholson; Referenz E_Fc = E − (E½,ref − E°ref);
  Basislinie (Standard an): Gerade durch den Vorlauf des Hinpeaks (bis 0,20 V davor – seit 1.1, Nutzerentscheidung 2026-11-12 „das wissenschaftlich Korrekte“: i_p-Fehler < 1 % an ideal
  reversiblen Wellen, vorher 0,15 V mit 1–3 %; gespeicherte Verbindungen behalten ihren Wert; reicht der Vorlauf nicht, Rückfall auf 0,15 V mit Kennzeichnung `bl_short`
  (i_p bis ~6 % zu klein) statt gar keiner Basislinie – **und** vor dem Anstieg der Welle,
  2 % der Peakhöhe – sonst überkorrigiert sie breite Wellen), Rückbasislinie = dieselbe minus
  Ladestromsprung am Umkehrpunkt (2·C·v); Nicholson auf die korrigierten Ströme, **keine** zusätzliche extrapolierte
  Rückbasislinie (doppelt korrigiert); Peakpotentiale aus dem Rohstrom. Regressionen gegen v je Gruppe, mit 95-%-KI.
  Nicholson nur ohne weiteren Prozess zwischen Hinpeak und Umkehrpotential (Strom steigt um > 10 % der Peakhöhe wieder
  an → „–“). E½ im Bild und alle Mittelwerte je Gruppe, nie über Lösungsmittel gemittelt.
  Ac₂Fc-Vorgabe +0,49 V vs. Fc⁺/Fc, immer änderbar lassen.
- Diffusionskoeffizient (F8, Nutzerauftrag 2026-11-12; `diffusion_coefficient`, `CVTab.diffusion`): aus der
  Randles–Ševčík-Steigung **des Hinpeaks** (nie des Rückpeaks: gegen die verschobene Hin-Basislinie gemessen ergäbe er
  ein um ~40 % zu kleines D, Literaturprüfung 2026-11) für ein reversibles, frei diffundierendes Paar, i_p = 0,4463·n·F·A·c·√(n·F·v·D/RT); Angaben
  `rs_n`, `rs_area`, `rs_conc`, `rs_temp` (Karte „Diffusionskoeffizient“, bleiben bei „Alles auf Standard“). Fläche und
  Konzentration sind **nie** vorbelegt und die Fläche kommt nie aus der Gamry-Datei (dort steht oft die Vorgabe 1 cm²):
  ohne beide kein D. Das 95-%-Intervall trägt nur die Unsicherheit der Steigung; Ergebniszeile und Methodentext sagen das.
- Umkehrpunkt (Literaturprüfung 2026-11-12): der Messpunkt am Umkehrpunkt zählt zu keiner der beiden Geraden für den
  Ladestromsprung (ob er zum Hin- oder Rücklauf gehört, steht in keiner Datei). Stromdichte: eingetragene Fläche (`rs_area`) vor der
  Fläche der Gamry-Datei, die nur mit Hinweis unter der Vorschau benutzt wird. Ac₂Fc +0,49 V ist ein CH₂Cl₂-Wert
  (Connelly & Geiger 1996).
- H-Zelle (Tab „H-Cell“, `tabs/hcell.py`, Leser `formats/gamry_cycling.py`, Nutzerauftrag 2026-11-12): Gamry „Cyclic
  Charge Discharge“ (TAG `PWR800_CYCLICCHARGEDISCHARGE`) + Schrittdateien nur `CHARGE_#n`/`DISCHARGE_#n.DTA` aus
  `CHARGE_DISCHARGE/` daneben (andere Dateien dort = andere Experimente). Kopfwerte/Spalten nach Namen; andere TAGs,
  fehlende Tabellen, unbekannte Type-Werte und doppelte Halbzyklen werden abgelehnt. Kapazität = Spalte Charge
  (C/3,6 → mAh), % nur mit Q_theo **je Messung** (Kopf CAPACITY oder eingegebener Wert `entries[].q_theo`, gilt nur für
  die gewählte Messung). CE = Q_dis/Q_ch desselben Zyklus; Zyklen mit nur einer Hälfte zählen nicht. Keine Glättung,
  keine Fits, keine Unsicherheiten. Kapazität gegen Zyklus: alle sichtbaren Messungen in einem Bild (Nutzerwunsch
  „Overlay wie Panel B“); eine Messung ohne eigene Farbe im Stil der SI (Quadrat schwarz, Kreis rot, Dreieck blau),
  sonst Farbe je Messung (Laden gefüllter Kreis, Entladen offener Kreis, CE Dreieck), Legende als Block je Messung, nie
  auf den Punkten. Potential gegen Zeit: nur die gewählte Messung, echte Zeit = `STARTTIMEOFFSET` + T, Achse zwischen
  nicht benachbarten Zyklen unterbrochen; fehlende Schrittdatei → Hinweis, nie rekonstruieren. Messungen liegen je in
  `data/hcell/<Name>/` (+ `CHARGE_DISCHARGE/`), damit die Paarung bleibt. Geprüft mit einer echten Messung (150 Zyklen);
  andere Gamry-Varianten und der Word-Export des SI-Kapitels ungeprüft.
- SEC-Farben wie die SI: Start blau, Zwischenstufen (`mid`, Potential in Achsenskala → nächstes gezeigtes Spektrum, ohne
  Potentiale Nummer) grün/`MID_COLORS`, Ende rot; Unterschrift nennt nur Farben, die im Bild vorkommen (`cap_mid`, „;“).
- SEC: Nernst-Fit aus kontinuierlichem Scan nur als „scheinbar“ ausweisen (Nachhinken in der Dünnschichtzelle:
  E½ und n weichen deutlich vom CV ab); CV-Werte haben Vorrang.
- SEC ohne Zeitstempel (Zweispaltenexport „Merged spectral data“, Nutzerauftrag 2.6): Messgröße aus dem Dateinamen
  (`.Abs8`/`.Raw8`, sonst Nachfrage), Abs und Raw nie in einer Serie, keine Blankkorrektur oder Glättung, Rohsignal nie
  ins Overlay und ohne Nernst-Fit. Potential nur aus bestätigter Zuordnung (`map_mode` interval/time/potential + `map_ok`,
  `assign_potentials`): nie Dateizeiten, nie gleichmäßig über die Laufzeit; außerhalb der Messung kein Potential (fällt
  weg statt Klemmen). Dateizeiten nur als Warnung beim Import (`_file_warnings`). Intervall zählt über die Dateinummer
  (Lücken verschieben nichts); Herkunft in Unterschrift/Methodentext (`map_sentence`). Nernst-Fit erst ab 5 Potentialen.
  Geräte nicht aus Endung/Wellenlänge ableiten. `LAM_RANGE` gilt nur für BWSpec.
