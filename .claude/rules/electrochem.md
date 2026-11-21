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
- Zwei Wellen im Paarfenster (Prominenz wie der Vorschlag, 3 % von max|I|): Zeile ungültig wie ein Randpeak (nicht in Regressionen, Beschriftung, E½-Mittel, Vergleich). Der Vorschlag endet jedes Fenster höchstens auf halbem Weg zur Nachbarwelle. Schultern ohne Senke werden nicht erkannt.
- D nur als Ergebnis, wenn ΔEp bei jeder Scanrate höchstens 10 mV über ΔEp der internen Referenz liegt (Referenz derselben Messung, oder eigene Messung nur bei gleicher Scanrate), sonst über 2,22·RT/(nF); sonst „scheinbares D“ mit den Scanraten in Tabelle, CSV und Methodentext. n nie aus ΔEp, ΔEp nie mit Ru korrigieren.
- k⁰ aus ΔEp je Scanrate (D_O = D_R = eingegebenes D, sonst Randles–Ševčík-D des Paars), n·ΔEp auf 25 °C skaliert: unter 66 mV kein Wert; 66–160 mV Nicholson-ψ nach Lavagnini; darüber Klingler–Kochi nur mit eingegebenem α (nie vorbelegt). Nur als Bereich über die Scanraten, nie ±, erst ab 3 Scanraten. „Scheinbar“ bei unbekannter iR-Kompensation, Referenz-ΔEp über der D-Schwelle oder D aus einem nicht reversiblen Paar. Fällt k⁰ mit v unter 75 % des ersten Werts: Warnung (iR). Methodentext nennt Verfahren, Quellen und α.
- Referenz per Klick: Häkchen „Fc“ je Messung, „Referenz setzen“, zwei Klicks rasten im Bereich ±80 mV auf das Extremum, E½ = Mittel; gespeichert wie ein eingetipptes Fenster, ein Rückgängig-Schritt, Esc bricht ab. Struktur des Standards (Fc, Ac₂Fc; feste Octet-SVG in `assets/standards`) über seiner Oxidationswelle (Chip „Struktur des Standards“, Vorgabe an); Farbe wählbar: schwarz (Vorgabe; auf dunkler Zeichenfläche weiß, in Grafik/SI immer schwarz) oder Farbe der Referenzmessung; kein Satz dazu in der Unterschrift. Messungen, die anderen Messungen als interne Referenz dienen, zählen nur als Referenz: nicht in Randles–Ševčík, D, k⁰, CSV und Methodentext; fehlt dadurch eine Scanrate, nennt ein Hinweis sie. Eine Messung, die nur sich selbst referenziert, bleibt in der Reihe.
- Ergebnisseite: Peaktabelle (Scanrate im Namen) · Scanraten-Regression · D/k⁰ je Paar · Warnungen eine Zeile je Art, Einzelheiten im Tooltip; bei 1200 px kein Querrollen. CSV: Komma, Dezimalpunkt, Köpfe „Name [Einheit]“, Rohwerte.
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
- SEC-Heatmap (Ansicht `mode` „heatmap“, Nutzerauftrag 2026-11-12; `_heatmap`, `SECFigure`, `HeatHover`): x = λ wie die
  Spektrenserie, y = Reihenfolge der gezeigten Spektren (erstes unten), nie E oder t als Achse (Hin- und Rückscan).
  Beschriftung der y-Teilstriche: E nur aus `series()` (Zeitstempel oder bestätigte Zuordnung), sonst Zeit seit dem
  ersten gezeigten Spektrum aus den Dateien, sonst Nummer – nie erfunden. Farbe = gemessene Größe oder Differenz zum
  ersten gezeigten Spektrum (Schlüssel `diff`, wie der Chip); ΔA divergierend und symmetrisch um 0 (`hm_cmap_d`), A
  sequentiell (`hm_cmap`), `hm_cmax` 0 = auto. Das Bild liegt genau im Datenbereich [x0, x1] × [0.5, n + 0.5] (MuPDF
  ignoriert Clip-Pfade), linear auf ein gleichmäßiges λ-Raster gebracht (Methodentext nennt es); Hover und CSV nehmen
  die Messwerte. Keine Labels, Legende oder Bilder; das Layout der anderen Ansichten bleibt. Rohsignal heißt „raw signal“.
- CV-Abbildung und CV-Stapel: bei automatischem E-Bereich bleibt links und rechts `CV.X_PAD` (3 % der Spanne) Rand; die
  Kurven liefen sonst bis an den Rahmen (Nutzerhinweis 2026-11-13). Ein eingegebener Bereich gilt unverändert.
- Messrichtungspfeil standardmäßig oben links über den Kurven, Richtung aus der ersten Kurve, gezogene Lage bleibt.
- Angaben der Richtlinien zum Voltammogramm (1.2.0, Auftrag 2026-11-13; ACS Research Data Guidelines „Electrochemistry“,
  Angew. Anhang E; Karte „Messbedingungen“, `ACS_FIELDS`, `scan_facts`, `setup_sentence`): Start und Richtung aus dem
  ersten Messpunkt bzw. den ersten Schritten des ersten Zyklus (`scan_start`, Achsenskala der Messung, nur wenn für alle
  gezeigten Messungen gleich), iR-Kompensation aus `IRCOMP` (with/without nur, wenn alle gleich). Elektroden, Spülgas,
  Gerät, Politur gibt der Nutzer ein (für neue Verbindungen gemerkt in QSettings `cv_acs/<Feld>`, vorbelegt nur ohne
  Messungen). Referenzelektrode des Aufbaus ist ein eigenes Feld (`acs_ref`); die Achsenreferenz `ref_electrode` erscheint
  im Aufbau-Text nur, wenn der Nutzer sie geändert hat (≠ Vorgabe) und Elektroden eingetragen sind: eine Vorgabe ist
  keine Angabe über den Aufbau (Nutzerentscheidung 2026-11-14, „vorgabe folgen“, nach der Code-Sichtung vor 1.2.0).
  Methodentext: Gerät, Arbeitselektrode mit Fläche (`rs_area`) und Politur, Gegen-/Referenzelektrode. Leere Angaben
  erscheinen nicht.
- CV-Messaufbau gesammelt im Anfangstext (Nutzerentscheidung 2026-11-13, wörtlich „CV-Messbedingungen gehören gesammelt
  in den Anfangstext“, Vorbild: Kapitelanfang „Cyclic Voltammetry“ seiner SI; ersetzt im Punkt darüber „Unterschrift:
  Gas, Elektroden“): Gerät, Arbeitselektrode, Fläche, Politur, Gegen-/Referenzelektrode, Atmosphäre, iR-Kompensation
  stehen **einmal je Projekt** in `publication.elucida` (`cv_setup`, Schlüssel `PUB.CV_SETUP` = `CV.SETUP_KEYS`),
  Eingabe auf der Projektseite → Angaben (Karte „Cyclovoltammetrie: Messaufbau“). `CV.setup_text` bildet daraus einen
  **Fließtext** in ganzen Sätzen (Nutzer: „Wie in der SI mit dem CV Text“; nur der Aufbau seiner SI, nicht ihr
  Wortlaut): Gerät mit iR-Kompensation, Atmosphäre, Dreielektrodenanordnung (Arbeitselektrode mit Fläche und Politur,
  Gegen-, Referenzelektrode), Konvention, dazu das freie Feld „Weitere Angaben“ (`more`) für Sätze, die sich nicht aus
  Feldern bilden lassen. Ein leeres Feld lässt seinen Satzteil weg; Fläche ohne Einheit = cm², „mm2“/„cm2“ werden zu
  mm²/cm². Der Text ist der erste Absatz des Kapitels „Cyclic Voltammetry“ der Gesamt-SI, vor dem freien Kapiteltext
  (`si_texts["cv"]`); derselbe Fließtext eröffnet ohne Projekt den Methodentext der Verbindung. Im
  CV-Tab einer Verbindung im Projekt zeigt die Karte „Messbedingungen“ nur Verweis, Text und die Werte aus den
  Dateien; ihr Methodentext enthält den Aufbau nicht (er stünde in der Gesamt-SI sonst je Verbindung noch einmal).
  Ohne Projekt gelten die Felder der Karte und der Aufbau eröffnet den Methodentext wie zuvor. Nichts umräumen: fehlt
  eine Angabe im Projekt, gilt die der Verbindung (`setup_effective`). Unterschriften bleiben kurz: nur was je Messung
  gilt, nie Elektroden, Gerät, Atmosphäre, Politur. iR-Kompensation und Konvention (`conv`: iupac/polar, Auswahl in den
  Projektangaben) stehen im Kapitelabsatz. Die Unterschrift nennt die Konvention nur, wenn das Projekt eine angibt und das
  Bild davon abweicht oder die Ströme umgekehrt sind (`invert`); ohne Angabe im Projekt nennt sie keine (Nutzerentscheidung
  2026-11-14). Ein `CONVENTION`-Wert ≠ 1 in der Gamry-Datei gibt einen Hinweis. iR-Kompensation nennt die Unterschrift
  nur, wenn das Projekt sie nicht angibt oder die Messung abweicht. Start und Richtung nur mit dem Chip „Start und Richtung“ (`cap_start`, Vorgabe aus: der Pfeil im
  Bild zeigt die Richtung). Nennt das Projekt eine
  iR-Kompensation und eine Messung wurde ohne aufgezeichnet, steht ein Hinweis im Tab (nie still in den Sammeltext).
  Die Regel in `si.md` zu den freien Aufbau-Texten (`si_setup/<Tab>` nur in QSettings) bleibt daneben bestehen.
- Pulsverfahren im CV-Tab (Nutzerauftrag 2026-11-13 „DPV-Leser“; `formats/gamry.read_gamry`): eine Gamry-Tabelle mit
  den **benannten** Spalten „Vstep“ und „Idif“ = eine Kurve E = Vstep, I = Idif (`meta["pulse"]` aus der TAG-Zeile:
  DPV, SQUARE_WAVE → SWV, sonst „pulse“; Pulsparameter STEPSIZE/PULSESIZE/PULSEON/FREQUENCY). Geprüft nur mit einer
  echten Square-Wave-Datei (öffentliche Testdatei, nicht im Repo); eine echte DPV-Datei fehlt – nie Spalten nach
  Position lesen, Tabellen ohne diese Namen ablehnen. Unterschrift: Titel nach Verfahren (gemischt „Voltammograms“),
  Pulsparameter nur, wenn für alle gleich; Achse ΔI. Keine Peakpaar- und Vorschub-Auswertung für Pulskurven (E_p eines
  DPV-Peaks ist nicht E½; eine Umrechnung wäre eine eigene, noch nicht bestellte Auswertung).
