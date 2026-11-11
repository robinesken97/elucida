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
  Basislinie (Standard an): Gerade durch den Vorlauf des Hinpeaks (bis 0,15 V davor **und** vor dem Anstieg der Welle,
  2 % der Peakhöhe – sonst überkorrigiert sie breite Wellen), Rückbasislinie = dieselbe minus
  Ladestromsprung am Umkehrpunkt (2·C·v); Nicholson auf die korrigierten Ströme, **keine** zusätzliche extrapolierte
  Rückbasislinie (doppelt korrigiert); Peakpotentiale aus dem Rohstrom. Regressionen gegen v je Gruppe, mit 95-%-KI.
  Nicholson nur ohne weiteren Prozess zwischen Hinpeak und Umkehrpotential (Strom steigt um > 10 % der Peakhöhe wieder
  an → „–“). E½ im Bild und alle Mittelwerte je Gruppe, nie über Lösungsmittel gemittelt.
  Ac₂Fc-Vorgabe +0,49 V vs. Fc⁺/Fc, immer änderbar lassen.
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
