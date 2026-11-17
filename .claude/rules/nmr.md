---
paths:
  - "elucida/tabs/nmr.py"
  - "elucida/formats/mnova.py"
  - "elucida/formats/topspin.py"
---

# NMR: fachliche Regeln (nicht ändern ohne Rückfrage)

- NMR-Tab: Abbildungen standardmäßig aus Mnova-SVG. Je Spektrum optional eigene Verarbeitung aus Bruker-Rohdaten (fid/ser;
  `formats/bruker_nmr`, `core/nmr_proc`, `core/nmr2d`): Referenz nie aus procs SF/SR, Phase und Referenz gelten erst nach Bestätigung durch
  den Nutzer; nicht belegte Verarbeitungsvarianten werden abgelehnt (TopSpin-1r/2rr mit Meldung), nie geraten. δ in der NMR-Ansicht steil
  (einzige Ausnahme von „Größen kursiv“, wie Mnova). Kern aus der Achse
  („δ ¹H (ppm)“, senkrecht = 2D), sonst von Hand; Reihenfolge ¹H, ¹³C, übrige nach Massenzahl, dann 2D (`sort_key`).
  NMR-Zeile aus dem Mnova-Bericht (alle Kerne in einem Feld), ¹H-Frequenz auf 50 MHz gerundet (501 → 500; nur bis ±5 MHz daneben, 270/360 bleiben, Nutzerwunsch P7); ¹³C auch aus
  den Peaklabels (`svg_peaks`, beschriftetes Lösungsmittelsignal fällt weg). Temperatur 298 K oder aus acqus. Rohdaten
  (Nutzerwunsch 2.1, Reiter „Rohdaten“ neben der Abbildung): TopSpin-Experimente **ganz** (FID/ser, pdata) nach
  `data/nmr/<Art>/<Datensatz>_<Nr.>` (`experiment_kind` aus acqus: 1D = Kern, DEPT/APT, 2D aus dem Pulsprogramm),
  `find_experiments` (Experiment, Datensatz, Ordner mit Datensätzen); genau ein passendes Experiment je Spektrum wird
  zugeordnet (`match_experiment`), sonst von Hand. MNova-Dokument (.mnova, 1.3.0): Die Kopie liegt in `data/nmr/mnova/`. Ist MNova installiert, exportiert MNova headless
  eine Kopie in Elucidas eigenem Temp-Ordner (`formats/mnova_cli.py`, `assets/mnova/elucida_export.qs`; Einblendung beim Start,
  Fortschritt in der Karte MNova). Jede Seite mit Spektrum wird ein Spektrum `data/nmr/mnova/<Dokument>/<Dokument>_<Seite>.svg`;
  `manifest.json` mit allen Berichten bleibt dort. Gleiche Spektrumobjekte einer Seite ergeben eine Zeile (bei Nicht-¹H gehört der
  Peakbericht zur Identität); verschiedene werden genannt und bekommen keinen Bericht. NMR-Zeile nur aus 1D: ¹H nur aus dem
  Multiplettbericht (ohne ihn: Hinweis, keine Zeile); andere Kerne Multipletts vor Peaklabels (`svg_peaks`), je Spektrum umschaltbar
  („SI-Zeile“). Der Multiplettbericht wird unverändert übernommen (kein Lösungsmittelfilter). Je Kern gilt der erste Bericht.
  Vorhandener Text wird nie still ersetzt (Übernehmen/Behalten). Die FIDs des Dokuments hängen als Rohdaten am passenden Spektrum
  (`match_experiment`); die Quelle bleibt MNova. Exportierte Seiten kommen nicht ins Datenpaket. Zusammen mit SVGs abgelegt: kein
  Export, nur FIDs anhängen. Ohne MNova, bei Zeitgrenze, Abbruch oder Komma im Pfad gilt der bisherige Weg (FIDs als eigene
  Spektren) mit dem Grund in der Einblendung. EMF-Spektren:
  Kern aus den EMF-Texten (`emf_info`), keine Vorschau, unverändert nach Word (`_media_ext`), ohne Struktur;
  EMF→SVG-Wandler vorgemerkt (Nutzer: später). Struktur als Vektor ins SVG (`compose_structure`), Lage `auto` = freie
  Stelle über Belegungsmaske (`auto_place`, oben links bevorzugt), ziehbar (`manual`), Größe `struct_w` für alle Spektren
  gleich. Unterschrift „¹H NMR (500 MHz, CDCl₃, 298 K) of **X**.“
- Kernzahl gegen die Summenformel (1.2.0, Nutzerwunsch 2026-11-13; `count_check`, Tabelle `tbl_count` unter der
  Signaltabelle, als `STYLE.summary_grid`, nie als Textzeile): ¹H = Summe der H-Zahlen gegen H der Formel, andere
  Kerne = Zahl der Signale gegen die Atome des Elements. Weniger H (austauschbar) oder weniger Signale (Symmetrie,
  Überlagerung) gelten als möglich, mehr oder ein Kern ohne Element in der Formel wird markiert. Nur ein Hinweis:
  nichts wird geändert, abgelehnt oder in die SI geschrieben; ohne lesbare Summenformel keine Tabelle.
- Nummer und Messangaben im Spektrum (1.2.0, Lückenanalyse ACS/Angew.: Strukturbild **und Verbindungsnummer** auf jedem
  Spektrum, Lösungsmittel, Frequenz): unter der Struktur, mittig, Nummer fett (`compound_name`), darunter „¹H NMR
  (500 MHz, CDCl₃)“ wie die Unterschrift ohne Temperatur (`label_lines`). Als Umrisse gezeichnet (`label_shapes` über
  matplotlib `TextPath`, wie Text in allen Abbildungen): Vorschau (QPainterPath), SVG (`label_svg`, absolute
  Koordinaten: MuPDF braucht keine Transformationen) und Word sehen gleich aus. Nur zusammen mit der Struktur; zwei
  Chips (`label_no`, `label_info`, je Tab, Vorgabe an – auch für alte Verbindungen, weil die Richtlinien es
  verlangen); die freie Stelle (`auto_place`) rechnet die Zeilen mit. Schrifthöhe `LABEL_F` × Bildbreite.
- Bereichsprüfung (`svg_axis_range`, `range_check`, Spalte „Bereich [ppm]“ der Spektrentabelle): kleinste und größte
  Zahl der waagerechten Achsenbeschriftung (längste Zahlenreihe einer Textzeile) gegen `AXIS_MIN` (¹H 0…10, ¹³C 0…200:
  die Beschriftung muss diese Werte erreichen; verlangt sind −1…10 bzw. −10/0…200 ppm). Nur 1D, nur ¹H/¹³C, nur ein
  Hinweis (⚠ in der Warnfarbe); nie das Spektrum ändern.
- Auswertung eigener Spektren (`core/nmr_analysis`, `core/nmr_report`): automatisch gefundene Multipletts sind Vorschläge, bestätigt wird
  je Signal mit eingezeichneten Fit-Linien (kein „alle bestätigen“). Die SI-Zeile druckt nur bestätigte δ und J; Unbestätigtes als Bereich +
  „m“ ohne J. Ein J, dessen Linien im Fit verschmelzen, gilt nie als gemessen und kommt nur über „J übernehmen“ in die Zeile. Fehlt ein Wert
  einem Objekt, gilt er als unbestätigt (fail closed). X-Kerne: Achse nominell; Unified Scale nur über ein bestätigtes ¹H derselben Probe am
  selben Magneten und nur mit doppelt abgeschriebenen Ξ-Werten (Harris 2001).
- Bereich der eigenen SI-Abbildung nur aus dem Feld „Bereich“, nie aus dem Zoom; Multiplett-Labels in der Ansicht ≥ 12 px, die SI-Abbildung
  behält die Vorlage (Nutzerwunsch 2026-11-15).
