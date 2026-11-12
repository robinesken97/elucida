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
