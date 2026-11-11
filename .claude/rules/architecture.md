---
paths:
  - "elucida/**"
  - "tools/**"
  - "tests/**"
  - "Elucida.py"
---

# Architektur

Module im Paket `elucida/` (Pfade in der Tabelle relativ dazu, außer `Elucida.py` und `tools/`); Importe absolut
(`from elucida.tabs import cv as CV`).

| Datei | Inhalt |
|---|---|
| `Elucida.py` | Startdatei (`python Elucida.py`, auch `python -m elucida`); Einstieg für PyInstaller. |
| `elucida/__init__.py` | `APP_NAME`, `APP_VERSION` (nur hier pflegen), `ROOT` (Repo-Wurzel; gebaut `sys._MEIPASS`). |
| `app/main_window.py` | Hauptfenster, ε-Tab, Projektlogik, Undo/Redo (JSON-Snapshots von `get_state`), Autosave, `si_char_parts` (Zeilen mit Art). |
| `selftest.py` | `selftest()`, `make_selftest_inputs` (nur Selbsttest; das Beispielprojekt erzeugt seine Daten selbst in `app/demo.py`). Neue Funktion → eigener Abschnitt. |
| `core/uvvis.py` | `DEFAULTS`, Reader (Cary CSV, DSW/BSW/FBSW via `parseuv_lite`, Eclipse CSV), Basislinie, Peak-/Schultersuche, `linfit`, `evaluate`, `Figure` (Platzierung über FreeSpace-Raster, gespeicherte Positionen zuerst reservieren), Export, `Dragger`. |
| `tabs/base.py` | `CanvasHost` (Vorschau maßstabsgetreu, dynamische DPI), `FigureTab` (Basis inkl. `methods_text`/`methods_button`, Export `_methods.txt`), Overlay- und Fluoreszenz-Tab. |
| `core/tddft.py` | TD-DFT-Parser (ORCA/Gaussian), Verbreiterung, `SimpleFigure`, Fotopaar mit Pfeil. |
| `core/images.py` | Bilder laden (HEIC, EXIF), Hintergrund entfernen (ISNet-ONNX → GrabCut → Rand), Struktur-Rendering (PyMuPDF), Vektor-Overlay in PDF/SVG. |
| `core/chem.py` | CDXML über RDKit: Formel, Molmasse, Ersatzzeichnung. |
| `app/project.py` | Projektordner (siehe `project.md`): `data_sub`, `STRUCTURES`, Exporte über `staging` → `place_exports` (Art nach `export_kind`), Namen `export_stem`, `work_dir` (.elucida), relative Pfade, Backup. |
| `app/demo.py` | Beispielprojekt (Hilfe-Menü, künstliche Daten). |
| `si/excel.py` | Excel-Report (openpyxl, neu aufgebaut 1.0, Nutzerwunsch „übersichtlich“): drei Blätter – Ergebnisse (Tabelle wie in der App, ε aus Excel-Formeln zur Kontrolle, zwei Diagramme im Stil der Abbildung: Farben/Achsen/Bereiche aus `cfg`), Rechnung (alle Banden nebeneinander, „im Fit“ änderbar, Regression als Formeln, Zwischenwerte grau), Spektren (Daten). Kein Gitter, Aussehen nur über die Konstanten oben im Modul; Diagrammdaten in verborgenen Spalten (`visible_cells_only = False`); alle Regressionsgeraden als **eine** Reihe (Excel blendet einzelne Legendeneinträge nicht aus, geprüft). Sprache = Programmsprache. In Excel prüfen: Datei öffnen, Formelwerte gegen die App. |
| `tabs/cv.py` | Cyclovoltammetrie: Gamry-.DTA-Leser (CURVEn oder CURVE+Cycle), `analyze_couple` (E_pa/E_pc/E½/ΔE_p, Nicholson), `suggest_couples`, Randles-Ševčík, `CVTab`. |
| `tabs/sec.py` | Spektroelektrochemie: BWSpec-Leser (λ aus coefs_a0…a3), Potential je Spektrum über Uhrzeit (Gamry DATE/TIME + T), scheinbarer Nernst-Fit (Raster E½/n), `SECTab`. |
| `tabs/epr.py` | CW-EPR: BES3T-Leser (.dsc/.DTA, LIT/BIG, D/F/I, 2D+YGF), ASCII (MS400, EasySpin), EasySpin-Parameter (`Sys.D` MHz → cm⁻¹), Dunkelspektrum, Basislinie, Ausblenden, Glätten, `fit_scale`, `EPRTab`. Felder intern in mT. |
| `core/color.py` | Farbe der Lösung: T = 10^(−A) × Planck 6504 K, CIE-1931-Kurven (Näherung Wyman 2013), Bradford → sRGB; Kanäle > 1 gemeinsam skalieren. |
| `app/update.py` | Update-Prüfung: neuestes GitHub-Release (API), Versionsvergleich, Paketname je System. Automatisch max. 1×/Tag, im Selbsttest ohne Netz. |
| `tabs/ir_ea.py` | IR + MS: OPUS-Leser (Blockverzeichnis, T als Anteil → %), OPUS-PDF-Peaks, Peaksuche (Parabel, w/m/s/br), MS-Bericht (docx: Text + EMF-Beschriftungen, CDX-Objekt), Bruker-.d-Leser (BAF-Linienspektren, eigene Kalibrierung), `lc_found`, Ionenmassen, SI-Zeilen, `IRMSTab`. |
| `tabs/xray.py` | X-Ray: eigener CIF-Leser (`Block`, Werte als Text), `Structure` (Zelle, U_kart, Symmetrie, geom-Tabellen), `Molecule` (Vervollständigung, Fehlordnung, Fragmente), `measure`, `project`/`pick` (ORTEP-Projektion), Tabellen-Markup (`runs` → HTML/Unicode/openpyxl), `XrayFigure`, `XrayMouse` (Drehen mit Blitting), `XrayTab`, `make_test_cif`. Tabellen als Excel im Stil des UV-Vis-Reports (`_sheet` nutzt die Helfer aus `si/excel.py`). |
| `tabs/hrms.py` | Tab HRMS: Chromatogramm (TIC/XIC, LC-Bereich per `SpanSelector`), gemitteltes Linienspektrum (`averaged_spectrum`, 5 ppm), Peak per Klick, Isotopenmuster (`isotope_pattern`, Isotope aus RDKit, Feinstruktur bis m/20000 zusammengefasst). Leser/Ionenmassen in `tabs/ir_ea.py`. |
| `tabs/dft.py` | Tab DFT: xyz-Leser (mehrere Bilder, Ordnungszahlen), `read_text` (UTF-16), `parse_orca`/`parse_gaussian`/`read_calc`, `si_parts`/`computational_details` (SI-Block, englisch), `match_reference`/`kabsch` (Vergleichsmodus), `bonds_of` (kovalente Radien wie X-Ray), `XyzMolecule`, `renumber`, `write_xyz`, `DFTTab` (Klick-Nummerierung, SI kopieren, Word), `make_test_xyz`/`make_test_orca`/`make_test_gaussian`. Zuschnitt der SI-Bilder: `XRAY.save_tight`. |
| `tabs/nmr.py` | Tab NMR: `svg_info`/`svg_peaks` (Mnova-SVG), Bruker `acq_params`, `parse_mnova`/`nmr_line`, `caption_html`, Strukturplatzierung (`occupancy`, `auto_place`, `compose_structure`), `NMRTab`, `make_test_svg`/`make_test_acqus`. |
| `tabs/dft_pages.py` | DFT-Reiter Energieprofil (Stufen, Einzelpunkte, IRC) und NICS: `level_of_theory`, `species_energies`, `profile_rows`, `irc_curve`, `nics_points`/`nics_pairs`, `DftPages` (Oberfläche, Abbildungen, Export, SI). Leser `parse_irc`/`parse_nics` in `formats/calc.py`. |
| `tabs/other.py` | Tab „Weitere“: fremde Abbildungen (`render_rgba`, `natural_cm`, `word_image`), `OtherTab` (Kapitel/Überschrift, `chapter_blocks`). |
| `tabs/compound.py` | Tab „Verbindung“ (früher Dialog): `CompoundTab` – Felder → `main.set_compound`, Zeichner auf der CDXML der Verbindung, Bilddatei als Vorschau. `compound_from_structure` bleibt in `app/main_window.py`. |
| `tabs/synthesis.py` | Tab Synthese: `parse_amounts`/`check_amounts` (Rundung), `row_amounts`/`amount_text`, `scheme_files`/`scheme_molecules`/`scheme_drawing`, `doc_to_html`, `SynthTab`. |
| `formats/` (Leser) | Dateiformate ohne Qt/Tabs (nur `i18n` für Fehlertexte), seit 2.2 aus den Tabs herausgelöst; die Tab-Module leiten die alten Namen weiter (`CVMOD.read_gamry` usw. bleibt gültig): `gamry.py` (.DTA), `bwspec.py` (SEC-Spektren), `epr.py` (BES3T, ASCII, EasySpin), `opus.py` (OPUS + PDF), `ms_report.py` (MS-Bericht .docx, EMF-Texte, CDX), `bruker_ms.py` (Bruker .d/BAF), `topspin.py` (acqus, Experimentart), `mnova.py` (SVG/EMF), `cif.py` (`Block`, `num`), `calc.py` (xyz, ORCA, Gaussian), `orbital_files.py` (Cube, Molden), `elements.py` (`ELEMENTS`, `BOHR`, `COV`, `element_of`). Neue Leser hierher, nicht in die Tabs. Cary/DSW/Eclipse bleiben in `core/uvvis.py` (Meldungen über `core.LOG`). |
| `formats/cdxml.py` | CDXML selbst zeichnen (`render_svg`: Bindungen, Labels, Formelstil, Pfeile, Texte; Labels für CDXML ohne `<t>`), `scheme_texts`/`scheme_reagents`. |
| `formats/ole.py` | OLE-Container (CFB v3) für bearbeitbare ChemDraw-Objekte in Word (`chemdraw_streams`, `write_cfb`). |
| `si/lines.py` | SI-Zeilen: Elementaranalyse (mittlere Atommassen, Solvat, Grenze 0.4 %), UV-Vis-Zeile aus den ε-Ergebnissen, Absatz (`join_lines`) und eigener docx-Schreiber (`write_docx`, ohne Zusatzpaket; Dreilinien-Tabellen, OLE, Seitenumbruch), `two_per_page`, `chem_html`. |
| `app/macos.py` | macOS ohne Titelleiste (Qt `ExpandedClientAreaHint`, Titel aus + leere kompakte NSToolbar per ctypes, Ampelknöpfe auf der Werkzeugleiste, Einzug `INSET`, im Vollbild NSToolbar aus), `TitleDrag` (freie Stellen ziehen/Doppelklick); nur mit Cocoa (`enabled()`, nie offscreen). Windows/Linux bewusst normal (rahmenlos hieße Snap nachbauen). |
| `app/style.py` | Erscheinungsbild: Fusion + eigene Palette (hell/dunkel/System, Menü Format), zentrales Stylesheet, Karten (`card`), SVG-Symbole (`icon`), Maße des Entwurfs (`LABEL_W`, `COL_PAD`, `CARD_PAD`, `ROW_GAP`, `BAR_H` …, siehe `ui.md`), `tidy` (linke Spalte: Raster, Abstände, Listenknöpfe), `ColumnFit` (feste Spaltenbreite `COLUMN_W`), `hint_when_disabled` (Detailkarte erst nach Auswahl). Betrifft alle Tabs, nicht die Abbildungen. |
| `tools/release_notes.py` | Release-Titel/-Notes für GitHub aus `CHANGELOG.md` + `CHANGELOG.de.md` (Release-Job in `build.yml`; fehlt die Version, scheitert das Release). |
| `app/i18n.py` | Texte DE/EN; `T(_key, **kw)` (Parameter heißt `_key`, damit `key=` als Format-Argument geht). |
| `formats/parseuv_lite/` | Vendorte parseuv-1.0.4-Version (BSD-3), angepasst. |
| `exchange/datapack.py` | Datenpaket je Verbindung (Zip wie die TUDOdata-Datensätze der Gruppe: `<Name>/NMR/1H/10`, `NMR/HSQC + HMBC/12`, IR, MS, UV-Vis, Fluorescence, CV/<Lösungsmittel>, SEC, EPR; DFT/Elucida-Ergebnisse Standard aus; nie X-Ray/Synthese): `collect` nur aus Zustandspfaden, `find_codes` (Laborkürzel `CODE_RE`), `write_zip` (Nutzerwunsch: „ausschließlich Compound XX und sonst unveränderte Rohdaten, Datum überall weg“: Namen immer ersetzen; Inhalt wahlweise, Standard an – Textdateien = keine Nullbytes inkl. TopSpin-Parameter/Titel/audita; Datum (`DATE_RE`) → 1980-01-01 **im selben
Format**, Uhrzeit bleibt (Nutzerwunsch P8 R2: Dateien lesbar, kein Projektverlauf; Hinweis `SCRUB_NOTE` im README),
`##$DATE=` → 0; Nutzer-/Kontonamen (`find_users`: ##OWNER, user@host, audita, BES3T OPER, Benutzerpfade, OPUS CNM)
→ „user“ (R1); Zip-Zeitstempel fest 1980; im Dateinamen wird das Datum gelöscht; PDF nur Eigenschaften auf gleicher
Länge (Datum, Autor); MS-Bericht `scrub_docx` (Absätze über Runs hinweg, docProps-Personen/-Daten, EMF gleiche Länge); OPUS `scrub_binary_strings` gleiche Länge; Messwerte bytegleich; PDF/Mnova/.d nicht bearbeitbar, Kürzel darin im Bericht `kept`). Dialog `app/datapack_dialog.py` (Auswahl je Projekt in QSettings). |
| `app/publication.py` / `app/publication_view.py` | Publikation: Index `publication.elucida`, `sync`/`add_compound`/`move_compound`/`remove_compound`, `publication_of`, `readme_text`/`license_file`; Seite `PublicationPage` (Zentrum Index 2), `PublicationRow` (Startbildschirm), Seite „Angaben“ (`PublicationInfoPage`, früher Dialog), Dialoge SI-Texte/Datenpakete/Gesamt-SI. |
| `si/publication_si.py` | Gesamt-SI: `SECTIONS` (Kapitelfolge der Gruppen-SI), `assemble`, `merge_crystal`; Blöcke `title`/`toc`/`section` in `write_docx`. |
| `app/drawing_editor.py`, `app/drawing_clipboard.py`, `app/drawing_data.py`, `app/canvas_theme.py` | Octet im Qt-Host: WebEngine + Brücke, `save_bundle` (CDXML/CDX/SVG, Backups), Zwischenablage, Übernahme der Stöchiometrietabelle, dunkler Canvas (nur Anzeige). |
| `app/reaction_paths.py`, `app/path_composition.py`, `tabs/diagram_layout.py`, `tabs/profile_*.py` | Projektweite Reaktionspfade: eigener Projektordner je Pfad, freie Komposition, Diagrammlayout (maßstäblich/schematisch), Bildanker, Orbitalansichten. |
| `formats/multireference.py`, `tabs/multireference.py` | ORCA-6-CASSCF/NEVPT2-Ergebnisse (Text wie in der Ausgabe), Auswahl, SI-Zeilen. |
| `formats/reagent_labels.py` | Mengenzusätze in Reagenzbeschriftungen; chemische Klammern bleiben. |
| `frontend/octet/` | Octet-Draw-Quellstand (Apache-2.0) + Elucida-Anpassungen, siehe `UPSTREAM.md`; `tools/build_octet.py` baut nach `assets/octet/`, `tools/update_octet.py` staget neue Upstream-Stände. |
| `tools/build.py` | PyInstaller-Build (wechselt selbst in die Repo-Wurzel; `--collect-submodules elucida`). |
| `core/orbitals.py` | Orbitale (DFT-Tab): Cube-Leser/-Schreiber, Molden-Leser + `Basis` (Überlappung Obara–Saika, Konventionsprüfung, Auswertung), `molden_grid`, Orbitalenergien ORCA/Gaussian, `iso_for_fraction`, `Volume`, `render` (Raycasting), `occluder_depth`, `OrbitalImage`, IboView-Konstanten, `make_test_cube`/`make_test_molden`. |
| `core/minao.py` | Minimalbasis MINAO (Daten aus PySCF, Apache-2.0) für IAO-Bindungsordnungen im Orbitalbild. |
