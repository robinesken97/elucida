# CLAUDE.md – Elucida (früher Spectravolt, davor UVVisTool)

PySide6-Desktop-App (Windows wichtigste Plattform, dazu macOS arm64, macOS Intel ab 14 und Linux) für UV-Vis-Verdünnungsreihen:
Lambert-Beer-Auswertung (ε bzw. a) und Abbildung im Origin-Stil (Spektren, λ/ε-Labels, Inset mit Regression
und Tabelle, ChemDraw-Struktur, Küvettenfoto). Dazu Tabs für Synthese (Schema, Vorschrift, Mengenprüfung), NMR (Mnova-SVG), IR + EA, HRMS, Overlay (gemessen + TD-DFT),
Fluoreszenz, CV, SEC, EPR, X-Ray (CIF) und DFT (xyz); SI-Abschnitt als Word-Datei.
Öffentliches Repo, AGPL-3.0. Maintainer: Robin (Chemiker, kein Softwareentwickler; Git-Einsteiger).

## Zusammenarbeit
- Antworten auf Deutsch, direkt und technisch präzise. Aussagen mit [Certain]/[Likely]/[Guessing] kennzeichnen.
- Keine Zustimmungsfloskeln. Wenn ein Wunsch fachlich fragwürdig ist (z. B. Statistik), das zuerst sagen,
  dann umsetzen.
- Git-Schritte (commit, tag, push, Release) kurz erklären und vor dem Push bestätigen lassen.
- Testdaten des Nutzers sind unveröffentlicht oder gehören Studierenden: **nie** CSV/DSW/BSW/HEIC/CDXML/ORCA-Ausgaben
  committen (siehe `.gitignore`). Keine Probennummern, Verbindungsnamen, Messwerte (auch publizierte) oder
  Namen von Mitarbeitenden in README/CHANGELOG/CLAUDE.md/Regeln/Code/Tests (öffentliches Repo); Beispiele sind erfunden.

## Fachliche Regeln
Stehen in `.claude/rules/` (nicht ändern ohne Rückfrage) und laden automatisch, sobald eine passende Datei gelesen oder geändert wird.
Frage oder Aufgabe ohne passende Datei: die Regeldatei selbst lesen. Neue Regeln dorthin, nicht in diese Datei.
`uvvis` · `drawing` (ChemDraw, Octet) · `tddft` (Overlay, ESD) · `electrochem` (CV, SEC) · `epr` · `ir-hrms` · `xray` (auch Moleküldarstellung) ·
`dft` (Orbitale, Energieprofil, NICS) · `cluster` · `nmr` · `synthesis` · `si` (Word, Methodentexte) · `project` (Ordner, Publikation, Export) · `ui` · `architecture`.

Gelten überall:
- ε und λ überall ganzzahlig; dieselbe Zahl in Tabelle, Bild, SI und Excel, nur die CSV behält Rohwerte.
- Nichts erfinden: keine geschätzten Standardabweichungen oder Unsicherheiten, unbekannte Dateivarianten ablehnen statt raten.
- Dateien und Rohdaten des Nutzers nie verändern, Löschen nur in den Papierkorb, alte Projekte nie umräumen.
- Methodentexte nennen nie das Programm.
- **Begriffe (seit 2.3, Nutzerwunsch):** in der Oberfläche/Doku heißt der Ordner einer Verbindung **„Verbindung“**
  (früher „Projekt“), der übergeordnete Ordner **„Projekt“**. Intern bleiben die alten Namen: `project_dir`/`PRJ`/
  `project.elucida` = Verbindung, `publication_dir`/`PUB`/`publication.elucida` = Projekt (Dateinamen nie umbenennen,
  sonst bräuchte jeder vorhandene Ordner eine Migration).
- UI zweisprachig: jeder sichtbare Text über `elucida.app.i18n.T(key)` mit DE **und** EN-Eintrag. Englische Kartentitel in
  Title Case (Nutzerwunsch); Zahlenfelder immer mit Dezimalpunkt (`STYLE._number_locale`, QLocale C), Schreibweise „MNova“.

## Befehle
```bash
pip install -r requirements.txt                       # Python 3.12 (wie CI)
python Elucida.py                                     # App starten (oder python -m elucida)
QT_QPA_PLATFORM=offscreen python Elucida.py --selftest selftest_out   # MUSS vor jedem Commit „OK“ melden
python tools/build.py                                 # PyInstaller-Build (braucht: pip install pyinstaller)
python tools/compare_figures.py vorher nachher        # Abbildungen zweier Selbsttest-Läufe pixelgenau (UI-Änderungen)
python tools/make_screenshots.py                       # README-Screenshots (docs/screenshots): Cover = Startbildschirm mit Beispielprojekt, Tabs leer mit Anleitung; alles nur dunkel (Nutzerwunsch)
```
- README kurz halten (Überblick, Abläufe, Download); alle Tab-Details in `docs/manual.de.md`/`docs/manual.en.md` (App-Links, Überschriften prüft der Selbsttest).
- Neue Funktion → eigener Abschnitt `with section:` im `selftest()` (`elucida/selftest.py`, Muster: `report.append("…: OK")` am Ende). Ein Fehler stoppt nur den Abschnitt, spätere können als Folge scheitern: den ersten FAILED zuerst lesen.
- Der Selbsttest läuft in CI auch mit der **fertig gebauten** App auf allen drei Systemen.

## Release-Ablauf
1. `APP_VERSION` in `elucida/__init__.py` erhöhen.
2. `CHANGELOG.md` **und** `CHANGELOG.de.md` ergänzen; bei sichtbaren Änderungen `docs/manual.en.md` **und** `docs/manual.de.md` (README nur für Neues von Gewicht).
3. Selbsttest, commit, push, dann **ein** Lauf: `gh workflow run build.yml --ref main -f release=vX.Y.Z` (Nutzerwunsch
   2.3.2: kein Testbuild + Tag mehr; der Release-Job hat `needs: build` und legt Tag und Release nur an, wenn alle vier
   Builds grün sind). Zufällige Fehler (PySide-Event-Filter unter Windows, ETIMEDOUT beim Artefakt-Upload) mit
   `gh run rerun <id> --failed` wiederholen. Alternativ `git tag vX.Y.Z && git push --tags` → GitHub Actions baut und
   erstellt das Release; Titel und Notes erzeugt `tools/release_notes.py` aus den Changelogs (also beide Changelogs vollständig pflegen).
   Ohne lokales Tag (z. B. aus einer Cloud-Sitzung, die nur ihren Branch pushen darf): nach dem Merge auf `main` unter
   Actions → „Build Elucida“ → Run workflow (Branch `main`, Eingabe `release` = `vX.Y.Z`); der Release-Job legt das
   Tag selbst an. Der Job bricht ab, wenn das Tag nicht zu `APP_VERSION` passt.

## Bekannte Fallen
- **Umbenennungen (1.16 UVVisTool → Spectravolt, 2.0 → Elucida):** Programm heißt Elucida, Repo
  `robinesken97/elucida`. Seit 2.1 liegen die Module im Paket `elucida/` (vorher `uvvis_*.py` flach im Repo);
  Projektdatei seit 2.1 `project.elucida` (`PRJ.PROJECT_FILE`); alte `project.uvvis` (`OLD_PROJECT_FILES`) wird gelesen,
  beim Speichern entsteht der neue Name und die alte Datei wandert nach `.elucida/project.uvvis.old` (Elucida ≤ 2.0
  erkennt solche Projekte nicht mehr). Der Cache-Name `.uvvis_cache` (ohne Projekt) bleibt. Alte Einstellungen (`OLD_APP_NAMES`:
  zuerst `QSettings("Spectravolt")`, dann `"UVVisTool"`, `migrate_settings`) und der Datenordner (`app_data_dir`:
  `…/Spectravolt`, sonst `…/UVVisTool`) werden beim ersten Start übernommen. Alte Versionen fragen die GitHub-API unter
  den alten Repo-Namen ab (GitHub leitet um) – Repo **nie** neu unter `spectravolt` oder `uvvis-tool` anlegen. Der
  Updater sucht Pakete nur über die Systemkennung (`windows-x64` …), nicht über den Programmnamen. Icon: Quelle
  `assets/icon-light.svg` (Windows/Linux/README, `.ico`) und `assets/icon-dark.svg` (macOS, `.icns`, Fenster unter
  macOS, Startbildschirm im dunklen Theme); alle PNG/ICO/ICNS mit `python tools/make_icon.py` (ICNS nur auf macOS).
- **Windows-Zeilenenden:** CSVs in Tests mit `newline=""` schreiben; Reader überspringt leere Zeilen
  (früher Windows-CI-Abbruch durch `\r\r\n`).
- **AppImage (Linux):** in CI aus dem PyInstaller-Ordner gebaut; appimagetool und type2-Runtime mit fester
  Version und SHA-256 in `build.yml` – bei Updates beide Prüfsummen neu eintragen.
- **Windows-Konsole (cp1252):** Selbsttest-Meldungen nur mit ASCII/cp1252-Zeichen (kein λ, ε); die
  Ausgabe ersetzt sonst Zeichen, früher brach CI am `print` ab.
- **PyInstaller:** eigene Module kommen über `--collect-submodules elucida`; lazy geladene **fremde** Pakete als
  `--hidden-import` in `tools/build.py` eintragen. Pfade zu Repo-Dateien nur über `elucida.ROOT`, nie `__file__`.
- **MuPDF:** ignoriert SVG-Clip-Pfade → Kurven geometrisch clippen (`clip_polyline`); Rechtecke mit Breite 0
  fallen bei `|=` weg → Koordinaten-Union; Alpha ist premultipliziert → beim Einfärben un-premultiplizieren.
- **Label-Kollisionen:** gespeicherte Positionen von Labels, Inset und Bildern vor neuen Elementen reservieren.
- **Platzierung (Nutzerwunsch 2.3):** Inset nie über Kurven – ohne freie Stelle rechts neben die schmalere Achse
  (`_make_room_right`/`_put_beside`, ohne Tabelle, nicht ins Layout gespeichert). Bandenlabels geordnet
  (`_place_labels_ordered`): Reihe mit gleicher Oberkante, sonst linksbündiger Block nach λ, erst dann einzeln.
- **macOS, natives Fenster:** Der erste Zeicheneditor (WebEngine) lässt Qt das NSWindow neu anlegen, Titelleiste und NSToolbar
  sind dann weg. `MainWindow.event` richtet sie bei `WinIdChange` neu ein (`_restore_title_bar`).
- **`layout.itemAt` nie direkt, immer `STYLE.item_at`:** PySide hält den Wrapper des Elements am Layout fest, Qt löscht das
  Element aber still (z. B. mit seinem Widget). Der tote Eintrag bleibt in PySides Adresstabelle; ein später an derselben
  Adresse angelegtes Python-Qt-Objekt stürzt ab (`SignalManager::retrieveMetaObject`, Adresse 0; zufällig je nach
  Allokator, 2.6 traf es `CanvasInvert` auf macOS). Selbsttest „layout items“ prüft, dass keine solchen Wrapper bleiben.
- **Mausereignisse (matplotlib):** `LocationEvent` rundet x/y auf ganze Pixel; Messpunkte liegen in der Vorschau
  < 1 px auseinander. Tests mit simulierten Klicks/Hover nur auf ±1 Messpunkt prüfen und dann, dass die Anzeige
  genau den getroffenen Punkt zeigt (CI-Systeme treffen sonst unterschiedliche Nachbarn).
- **Undo:** während `set_state` greift `_restoring`; Änderungen über `QTimer` verzögert erfassen.
  `save_project` speichert trotzdem (`autosave(force=True)`), sonst blieb das Beispielprojekt leer.
  Rückgängig bleibt im offenen Tab bzw. zeigt den Tab der Änderung (`_restore`, Nutzerwunsch P9 R1); ein Schnappschuss,
  der sich nur im Tab unterscheidet, ist kein eigener Schritt. Ziehen speichert nur bewegte Elemente
  (`Dragger.moved`, ein Klick ins Bild hält die automatische Platzierung nicht fest).
- **Tempo:** `build_ui` nur beim Start, Sprach-/Theme-Wechsel. Öffnen und Rückgängig/Wiederholen über
  `set_state(partial=True)`/`_changed_parts`: nur geänderte Tabs ersetzen (`replace_tab`, feste `_TAB_BUILD_ORDER`, DFT
  liest X-Ray), ε nachziehen (`apply_globals`); Verbindung/Textformat geändert -> alle Tabs ersetzen, Fenster bleibt.
  Tabs werden **bei Bedarf gebaut** (`_lazy`, `__getattr__` auf `self.<x>_tab`, `_tab_shown`): nie `hasattr(self,
  "<x>_tab")` (baut), sondern `_built(key)`; Schleifen über alle Tabs nur über gebaute. Neue Tabs in `_tab_spec`/
  `_TAB_ORDER`/`_TAB_BUILD_ORDER`. Beispielprojekt: Öffnen 0,2 s, Rückgängig 0,1 s, erster Klick auf einen Tab ~0,2 s. Verborgene Tabs zeichnen erst beim Anzeigen (`_first_render`;
  `ensure_rendered()` vor Zugriff auf `F`). PNG-Ersatz für Word mit `png_fast` (compress_level 1).
- **macOS-Version:** `tools/build.py` liest `APP_VERSION` und schreibt sie nach dem Build in die `Info.plist`,
  danach `codesign --force --deep --sign -` (Signatur schließt die Info.plist ein).
- **pymupdf:** `get_pixmap(dpi=…)` nur mit ganzen Zahlen (die Windows-Version wirft sonst TypeError; lokal unbemerkt).
- macOS-Build ist unsigniert (Gatekeeper: Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“).
  Trackpad-Zoom und HiDPI-Vorschau auf echter Mac-Hardware sind noch nicht verifiziert.
- **macOS arm64:** seit 2.4.0 auf `macos-15` (GitHub schaltet `macos-14` am 2026-11-02 ab, vorher Brownouts =
  Job sofort „cancelled“ ohne Runner; Ursache steht in den Annotations des Jobs).
- **macOS Intel** (`macos-15-intel`-Runner): rdkit nur bis 2025.9.3, onnxruntime nur bis 1.23.2 als
  x86_64-Wheel (pip wählt sie automatisch); numpy/PySide6/opencv verlangen macOS 14. Der Runner ist
  befristet – fällt er weg, Intel-Build aus der Matrix nehmen.

## Offene Punkte
- CV geprüft mit echten Gamry-Serien; bei hohem Vorschub in schlecht leitendem Medium iR-dominiert: „Vorschlag“ findet dort zu Recht kein Paar.
- X-Ray geprüft mit künstlicher CIF, einer Olex2-CIF und einer CCDC-CIF mit Fehlordnung und Lösungsmittel; Symmetrieerzeugung
  nur künstlich; Polymere werden
  abgebrochen (`max_factor`). Stufe 3 (Vergleich mit DFT-Geometrie, ORCA-xyz) vorbereitet: `measure` arbeitet nur
  mit Atom-Schlüsseln (Label|Operation) und `param_label`; ein xyz-Molekül mit denselben Labels kann eine eigene
  Spalte liefern (Zuordnung der Atome noch offen).
- BSW-Datei mit Sprung in Spektrum 60 (CSV-Export zum Vergleich fehlt).
- Echte Gaussian-TD-DFT-Ausgabe noch nicht getestet (nur ORCA inkl. SOC); DFT-Tab: Gaussian-Leser mit einer Opt+Freq geprüft.
- DFT-Tab: IboView wird bewusst nicht angesteuert (eigenes Rendering, Orbitale wie IboView). Orbitale: echte ORCA-Molden-
  Datei und ORCA-Cube noch nicht gegen orca_plot geprüft (PySCF-Molden ja, inkl. g). MR-Ausgaben (ORCA 6 CASSCF/SC-NEVPT2/QD-SC-NEVPT2,
  `formats/multireference.py`) gegen synthetische Layouts und eine öffentliche ORCA-6.1.1-Ausgabe (CASSCF + DLPNO-NEVPT2) geprüft;
  SORCI (nur der DDCI3-Schritt, Energie = gedruckter STATE-Wert inkl. Davidson-Korrektur wie in der Übergangstabelle, CI-Energie daneben) gegen eine echte
  H2-Ausgabe (ORCA 6.0.1) geprüft: ohne innere Orbitale, ohne Symmetrie, ohne Spektren; im Overlay nicht wählbar. Orbitale, die beim Einlesen nicht
  orthogonal waren (`redoing schmidt`, > `MAX_SCHMIDT`), gibt der Parser als Warnung aus: ORCA endet trotzdem normal.
  Vergleichsmodus mit echter CIF noch ungeprüft (nur künstliche CIF und echte DFT-Paare).
