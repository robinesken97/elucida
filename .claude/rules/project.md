---
paths:
  - "elucida/app/project.py"
  - "elucida/app/publication*.py"
  - "elucida/app/datapack_dialog.py"
  - "elucida/app/demo.py"
  - "elucida/app/welcome.py"
  - "elucida/app/main_window.py"
  - "elucida/exchange/**"
  - "elucida/si/publication_si.py"
  - "elucida/tabs/other.py"
---

# Projekte, Verbindungen, Publikation, Export: fachliche Regeln (nicht ändern ohne Rückfrage)

- Export: Standard 16 × 11 cm (halbe A4-Seite in Word, zwei Abbildungen pro Seite), minimale Ränder; PDF/SVG
  vektoriell, Text in SVG als Pfade. Exporte überschreiben im Projektordner (siehe nächster Punkt).
- Projektordner (seit 2.1, Nutzerwunsch „nach Ergebnis“): `SI/` (Word, SI-Texte), `figures/` (PDF/SVG/PNG),
  `tables/` (CSV, Excel, xyz, EasySpin-Text), `data/<Analytik>/` (`DATA_SUB`), `structures/` (CDXML + Exporte, Fotos),
  `.elucida/` (Zwischenbilder für Word, Foto-Cache, Backup; unter Windows versteckt). Exportnamen `<Verbindung>_<Tab>`
  (`EXPORT_LABEL`, ε: `<Serie>_UV-Vis`; ohne Verbindung der Ordnername). Tabs schreiben in `PRJ.staging`, `place_exports`
  sortiert nach Art (`export_kind`) – neue Exportdateien dort einordnen (Endung oder `SI_SUFFIXES`). Ordner nur bei
  Bedarf anlegen. Alte Projekte (`data/`, `images/`, `exports/`) **nie umräumen**: gespeicherte Pfade gelten weiter.
- `elucida.json` für Characterization wird nicht mehr erzeugt oder aktualisiert (Robin, 2026-11-04).
  Vorhandene Dateien in Nutzerordnern nie löschen oder verändern. `project.elucida` bleibt die Projektdatei.
- Tab „Weitere“ (F5, `tabs/other.py`, letzter Tab): fremde PDF/SVG/PNG unverändert (PNG direkt, SVG + PNG-Ersatz, PDF
  als SVG mit Text als Pfaden), Seitenverhältnis, Unterschrift + Kapitel (SI-Kapitel oder eigene Überschrift = eigenes
  Kapitel am Ende der Gesamt-SI, `new:<Überschrift>` in den Teilen); nie im Datenpaket. .mnova nie im Datenpaket
  (FB-10), Ablage nur je Verbindung (NMR-Tab, Karte „Mnova“ oben links: Dateiname, ablegen, „In Mnova öffnen“ =
  Standardprogramm; Nutzerwunsch, die Projekt-Ablage entfiel nach 2.4.0, alter Schlüssel `mnova` bleibt nur erhalten).
  Schnellauswertung: internes Projekt `<Datenordner>/Einzelauswertungen` (`quick_dir`), Exporte dort in einen gewählten
  Ordner (`place_exports`, QSettings `quick_export_dir`), nie automatisch löschen.
- Notiz zur Verbindung (`compound.note`): nur intern (Startbildschirm, Titelleiste), nie in SI/Word/
  Datenpaket.
- Publikation (seit 2.3, `app/publication.py`, Oberfläche `app/publication_view.py`): Ordner mit `publication.elucida`
  (Angaben für README, Reihenfolge `compounds` relativ, `excluded`, `si_texts`) über den Verbindungsprojekten; Projekte
  bleiben eigenständig und kennen die Publikation nicht (`publication_of` = Elternordner). Unterordner mit Projekt werden
  beim `sync` angefügt (natürlich sortiert), herausgenommene als `excluded` vermerkt. Name einer Verbindung = `compound.name`
  des Projekts. Datensatz (`datapack.write_publication`) wie TUDOdata: `<Name>.zip` je Verbindung, DFT aller in
  `CompChem.zip` (`CompChem/<Name>/…`), README.txt nach der Vorlage des Datensatzes der Gruppe (`readme_text`; Felder
  TITLE … LICENSE), Lizenztext aus `assets/licenses` (CC-Texte selbst CC0); Kürzel → Verbindung über Dateinamen
  (`assign_codes`), Einzelauswahl aus QSettings (`saved_selection`) gilt weiter. Gesamt-SI (`si/publication_si.py`)
  **in der Kapitelfolge der SI der Gruppe** (Methods, Synthesis/Characterization, NMR, [IR/MS nur auf Wunsch], UV-Vis inkl.
  Overlay/Fluoreszenz, EPR, CV, SEC, X-Ray, Computational), leere Kapitel weg, Nummern rücken nach; Titelseite +
  Inhaltsverzeichnis (TOC-Feld, `updateFields`), Kapitel = Überschrift 1 mit Seitenumbruch; je Kapitel erst Text aus
  `si_texts`, dann die Verbindungen in Reihenfolge (Auswertungstexte je Verbindung vor ihren Abbildungen); Kristalldaten
  aller Strukturen gemeinsam (`merge_crystal`, ≤ 3 je Tabelle). Erzeugt durch kurzes Öffnen jeder Verbindung
  (`MainWindow.export_publication_si` → `si_compound_parts`), danach die vorher offene wieder. Vorlagen (`SI.TEMPLATES`:
  group/wiley/acs/rsc/nature, abgeglichen mit den Autorenrichtlinien: Wiley SI beginnt mit Inhaltsverzeichnis, ACS
  Verzeichnis mit Seitenzahlen „S1“, Nature „Supplementary Figure 1“ eigene Zählung, RSC „Fig. S1“) ändern nur Titelblatt,
  Bezeichnungen und Seitenpräfix, nur für die Gesamt-SI (`set_template(…, page_numbers=True)`, danach zurück). Gesamt-SI:
  Seitenzahl in der Fußzeile, Verzeichnis schon gefüllt (`toc_entries` schätzt die Seiten wie `two_per_page`, mit
  ONLYOFFICE geprüft: alle Kapitel exakt; Word aktualisiert beim Öffnen). `two_per_page`: bleibt neben langem Text
  weniger als `MIN_FIG_CM` je Bild, kommen die Bilder auf die nächste Seite (sonst briefmarkengroß). Prüfen ohne Word:
  ONLYOFFICE-Konverter `x2t` mit Parameter-XML (`m_sAllFontsPath` aus dem App-Datenordner). Titelblatt = `paper_title` (wie die Gruppen-SI: 18 pt Kopf, Rest 11 pt); Datensatztitel
  sonst „Electronic supplement to …“. Checkliste (`checklist`, Nutzerwunsch): Pflicht ¹H, ¹³C, 2D, HRMS, IR, m.p.;
  `compound.known` (+ `lit`) nur ¹H/¹³C; `compound.oil` = „m.p. <25 °C“ (zählt als m.p.). Zurück: `btn_pub` in der
  Tab-Leiste.
- Tabs folgen **immer** der Verbindung (`compound`; Nutzerwunsch 2026-11-10, vorher nur Vorgabe): Jede Änderung der
  Verbindung (Tab Verbindung, gespeicherte Zeichnung, Übernahme aus dem MS-Bericht) erreicht sofort alle gebauten Tabs
  (`set_compound` → `compound_changed`) und ersetzt Molmasse und Struktur aller ε-Serien und die Struktur im Fluoreszenz-Tab,
  auch eigene oder von Hand eingetragene Werte (`apply_compound_defaults`). Eine ersetzte abweichende Molmasse wird
  eingeblendet (ε der Serie ändert sich), ein Rückgängig-Schritt stellt alles wieder her. Nennt die Verbindung keinen Wert,
  bleibt der des Tabs. Beim Laden von Messdaten und beim Öffnen einer gespeicherten Verbindung werden nur leere Werte
  gefüllt (`only_empty`): gespeicherte Auswertungen ändern sich erst, wenn die Verbindung geändert wird. Folge: mehrere
  Verbindungen mit verschiedener Molmasse in einem Verbindungsordner gehen nicht mehr (eigene Ordner anlegen).
  Im ε-Tab wird dazu nichts mehr eingegeben (Nutzerwunsch 2026-11-10): Die Karte „Verbindung“ zeigt Summenformel und Molmasse
  als Angabe (`lbl_formula`, `lbl_mw` = die Zahl, mit der die Serie rechnet) mit „Ändern …“ (zeigt den Tab Verbindung);
  `ed_mw`/`lbl_struct` bleiben nur verborgen als Träger der Serienwerte. Weicht eine gespeicherte Serie von der Verbindung ab,
  steht das als Hinweis darunter. „Struktur im Bild“ (`no_structure` je Serie, gespeichert) lässt die Struktur der
  Verbindung in einer Serie weg und bleibt auch nach Änderungen der Verbindung und nach dem Öffnen abgewählt.
- Molmasse überall mit 2 Nachkommastellen, auch gespeichert (Nutzerwunsch 2026-11-10; nur die exakte Masse der HRMS hat
  mehr): Rechnung, Feld, Methodentext und Excel benutzen dieselbe Zahl. Schon gespeicherte Werte alter Verbindungen nicht
  nachträglich runden (ε könnte sich in der letzten Stelle ändern).
- Beispielprojekt (`app/demo.py`, Nutzerwunsch 2026-11-10 „zusammenpassende Beispieldaten“, 2026-11-12 „für jeden
  einzelnen Tab“): zwei **erfundene** Verbindungen, S2 (Vorstufe: Synthese, NMR, IR, EA, HRMS, UV-Vis, X-Ray) und S3
  (Produkt, **jeder** Tab: auch HRMS-Bericht + Bruker-.d mit demselben found, HOMO/LUMO-Cubes und NICS-Scan auf der
  ORCA-Geometrie, Abbildung unter „Weitere“, H-Zelle um das E½ des CV); alle Daten einer Verbindung gehören zu demselben
  Molekül und passen zueinander (`COMPOUNDS`, Generatoren `uvvis_csv`, `tddft_out`, `cv_cycles`, `make_cif`, `make_orca`,
  `make_bruker_d` …; Geometrie aus RDKit mit festem Startwert). Der Selbsttest prüft die Zusammenhänge (HRMS ≤ 5 ppm,
  EA ≤ 0.4, Hauptbande ±2 nm in ε/Overlay/SEC/Kinetik, E½ im SEC- und H-Zellen-Bereich, EPR-Kerne in der Formel).
  Dateinamen tragen den Verbindungsnamen. Neue Tabs/Formate dort mit passenden Daten für S3 ergänzen, nie Fixtures des
  Selbsttests (`make_selftest_inputs`, `make_test_cif`, `make_test_orca`) wiederverwenden und nie echte Messwerte. Die
  README-Bilder (`tools/make_screenshots.py`) zeigen S3 mit diesen Daten.
- Laborbuchnummer (`compound.labbook`): nur intern (Übersicht, Suche), nie in SI/Word/Datenpaket.
- Vergleich (Projektseite, Nutzerauftrag 2026-11-12; `app/comparison.py`, Reiter vor „Angaben“): benannte Vergleiche in
  `publication.elucida` unter `comparisons` (uid, name, kind cv/spectra/table, st = Zustand des `FigureTab` samt
  `members`/`table`), Bedienung als `FigureTab` im Gastgeber `CompareHost` (Schritte, Karten, Export unten rechts, keine
  Popups). **Nichts wird neu ausgewertet:** `autosave` → `write_snapshot` schreibt `.elucida/compare.json` (Version 1;
  Kurven ≤ `MAX_POINTS`; Werte als Text genau wie im Tab: `fmt_lam`/`fmt_ve` mit dem Filter von `uvvis_line`,
  `CV._fmt_e`, ΔE_p in mV, `g_text`, `hfc_texts`, D und |E/D| wie `zfs_summary`). Neu ausgelesen wird nur ein gebauter
  Tab mit geändertem Fingerabdruck (`fingerprint`: Zustand mit relativen Pfaden); ein Fehler darin stört das Speichern
  nie. Ein Eintrag, dessen Fingerabdruck nicht zur Projektdatei passt, gilt als veraltet und liefert keinen Wert;
  „Aktualisieren“ (nur sichtbar, wenn nötig) öffnet die Verbindung kurz und speichert sie. Strukturen im Vergleich (CV-Stapel, Spektren;
  Nutzerwunsch 2026-11-13): je Verbindung eine, Vorgabe in Kurvenfarbe (`structures`, `struct_color`, `struct_w`), alle im
  selben Zeichenmaßstab über `FigureTab.structure_images` (Breite in Bindungslängen aus der CDXML, `IMG.structure_units`;
  die breiteste = `struct_w`, Mausrad auf einer ändert `struct_w`, kein Einzelschrumpfen; gilt auch im UV-Vis-Overlay).
  Spektren: am höchsten Punkt der eigenen Kurve, gestapelt rechts über der eigenen Grundlinie (`between`: Platzsuche
  sperrt dann nur die Kurvenlinien, nicht die Fläche unter der Hülle). CV-Stapel: eine andere
  Referenzskala als die erste Kurve wird abgelehnt, nie umgerechnet; Peak am Fensterrand ergibt keine Zahl; Unterschrift
  nur aus den `cap_*` der Verbindungen (gleiche Angaben einmal, verschiedene je Verbindung), normiert = Satz in der
  Unterschrift. Spektren: ε wie im Overlay (`eps_linked`, gleiche Basislinie); ohne Konzentration oder Molmasse keine
  Kurve. Tabelle (Nutzerwunsch „übersichtlich“): Karten „Größen“ (Liste als Tabelle; „Aus den Tabs“ = Menü der Werte,
  „Eigene“ = frei; Name/Einheit der Tab-Werte stehen fest), „Weitere Verbindungen“ (Zeilen außerhalb des Projekts),
  „Zellen und Anordnung“; kein Schritt „Darstellung“. Tab-Werte leer, wenn sie fehlen; von Hand überschriebene Zellen
  markiert und rücksetzbar; Kopf „Größe / Einheit“ als Markup, Ausgabe englisch, Namen fett; die Linie unter einem
  Gruppenkopf steht nur unter seinen Spalten (`GroupRule`, wie im Word-Export). Exporte nach `<Projekt>/comparisons/`
  (figures/tables/SI), Name = Name des Vergleichs. „Entfernen“ nimmt nur den Eintrag aus der Projektdatei.
  Gesamt-SI (Nutzerauftrag 2026-11-13): je Vergleich `item["si"]` = {on, chapter, heading}, Standard aus; Kapitel wie im
  Tab „Weitere“ (`other.CHAPTERS`), Vorgabe nach Art (`default_chapter`: CV-Stapel → cv, Spektren nach Inhalt
  uvvis/irms/epr, Tabelle → `new:<Überschrift>`, leer = Name). `CMP.si_blocks` zeichnet auf einer nie gezeigten
  `ComparePage` mit denselben Ständen (nichts neu ausgewertet), `assemble(comparisons=…)` setzt sie je Kapitel nach die
  Verbindungen (Abbildungen über `two_per_page`, Tabelle als `tabcap` + `params` mit `fit`). Stand: zusätzlich irms
  (Banden der Liste, Kurve wie im Bild), xray (ausgewählte Parameter mit `param_label`, Raumgruppe, Kristallsystem), dft
  (Eingabezeile, E(el), G, HOMO/LUMO), nmr (Signale aus dem Multiplettbericht); CV zusätzlich die Zyklen 1–`MAX_CYCLES`
  je Messung; Zahlen am Peak nur im ausgewerteten Zyklus. Tabelle: X-Ray-Spalte = Atomlabels in beiden Richtungen
  (`xr_key`); IR/NMR-Spalte mit Ziel und Toleranz (IR 15 cm⁻¹, ¹H 0.5 ppm, sonst 2 ppm), Zelle = nächster Eintrag der
  Liste des Tabs innerhalb der Toleranz, sonst leer. Spektren: IR wie der IR-Tab (andere Darstellung abgelehnt), EPR
  normiert und gestapelt, Feldachse nur bei gleicher Frequenz (`EPR_NU_TOL`) oder auf `ref_freq` skaliert wie der
  EPR-Tab, sonst g-Achse; ohne Frequenz abgelehnt, nie still gemischt. Rückgängig: eigener Verlauf je offenem Vergleich
  (`ComparePage.history`, wie `PathHost`), `MainWindow.undo/redo` leiten über `active_comparison` dorthin; nie die Daten
  der Verbindungen. Listen des Tabs (Vergleiche, Verbindungen, Größen): Spalten gleich breit, nur die Häkchenspalte
  schmal (Nutzerwunsch 2026-11-13).
- Projektseite, Raster (Nutzerwunsch 2026-11-12): Kopf, Reiter und alle Seiten rücken selbst um `IN` (= `COL_PAD`) ein,
  die Reiterseite ist um `IN` breiter (`PAGE_MARGINS`) – so stehen die Karten des eingebetteten Vergleichs auf der Kante
  des Titels. Keine Linie über den Reitern (`projectTabs`); `center_corner` erst nach den Reitern (sonst Höhe 0, Knöpfe
  unsichtbar). Senkrecht: Untertitel – Fortschritt – Reiter je 16 sichtbar, Reiter – Seitenkopf – erste Überschrift
  je ~24, Überschrift – Tabelle 8, Tabelle – nächste Überschrift 20 (`HEAD_GAP`). Ein Hauptknopf (blau): mit offenem
  Vergleich dessen „Exportieren“, sonst „Gesamt-SI“ (`sync_main_button`). Verbindungsliste als Matrix (`WEL.fit_more`,
  Nutzerwunsch „stimmig“): links die Verbindung (Nummer, Bild, Name) linksbündig wie ein Zeilenkopf, rechts ein einziges
  Raster mittiger Spalten – Pflichtteile, dann **jede weitere Methode als eigene Spalte** (`MORE`, Kurzname `SHORT_MORE`,
  Haken = Daten, feiner Punkt = keine), „Geändert“. Spaltenbreite in Kopf und Zeilen gleich, wächst mit dem Fenster bis
  `CHECK_W_MAX`; passen die Spalten nicht (Name behielte weniger als `NAME_MIN`), steht stattdessen der gekürzte Text
  „Weitere Analytik“. Neue Tabs mit Abzeichen in `MORE` und `SHORT_MORE` eintragen. Word-Tabelle des Vergleichs: Spaltenbreiten nach Inhalt (`SI.fit_widths`).
