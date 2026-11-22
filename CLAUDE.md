# CLAUDE.md – Elucida (früher Spectravolt, davor UVVisTool)

PySide6-Desktop-App (Windows wichtigste Plattform, dazu macOS arm64, macOS Intel ab 14 und Linux) für UV-Vis-Verdünnungsreihen:
Lambert-Beer-Auswertung (ε bzw. a) und Abbildung im Origin-Stil (Spektren, λ/ε-Labels, Inset mit Regression
und Tabelle, ChemDraw-Struktur, Küvettenfoto). Dazu Tabs für Synthese (Schema, Vorschrift, Mengenprüfung), NMR (MNova-SVG), IR + EA, HRMS, Overlay (gemessen + TD-DFT),
UV-Vis-Kinetik, Fluoreszenz, CV, SEC, H-Cell (Laden/Entladen), EPR, X-Ray (CIF) und DFT (xyz); SI-Abschnitt als Word-Datei.
Öffentliches Repo, AGPL-3.0. Maintainer: Robin (Chemiker, kein Softwareentwickler; Git-Einsteiger).

## Zusammenarbeit
- Antworten auf Deutsch, direkt und technisch präzise. Aussagen mit [Fact]/[Likely]/[Hypothesis] kennzeichnen.
- Keine Zustimmungsfloskeln. Wenn ein Wunsch fachlich fragwürdig ist (z. B. Statistik), das zuerst sagen, dann umsetzen.
- Git-Schritte (commit, tag, push, Release) kurz erklären. Pushen und Releases nur nach Robins ausdrücklicher Freigabe,
  und nur in dem Umfang, den er nennt.
- Testdaten des Nutzers sind unveröffentlicht oder gehören Studierenden: **nie** CSV/DSW/BSW/HEIC/CDXML/ORCA-Ausgaben
  committen (siehe `.gitignore`). Keine Probennummern, Verbindungsnamen, Messwerte (auch publizierte) oder
  Namen von Mitarbeitenden in README/CHANGELOG/CLAUDE.md/Regeln/Code/Tests (öffentliches Repo); Beispiele sind erfunden.

## Fachliche Regeln
Stehen in `.claude/rules/` (nicht ändern ohne Rückfrage) und laden automatisch, sobald eine passende Datei gelesen oder geändert wird.
Frage oder Aufgabe ohne passende Datei: die Regeldatei selbst lesen. Neue Regeln dorthin, nicht in diese Datei. Was an welchen Dateien geprüft
ist (echt, öffentlich, erfunden), steht in der passenden Regeldatei.
`uvvis` · `drawing` (ChemDraw, Octet) · `tddft` (Overlay, ESD) · `electrochem` (CV, SEC) · `epr` · `ir-hrms` · `xray` (auch Moleküldarstellung) ·
`dft` (Orbitale, Energieprofil, NICS) · `cluster` · `nmr` · `synthesis` · `si` (Word, Methodentexte) · `project` (Ordner, Publikation, Export) · `ui` ·
`new-views` (Abnahme neuer Ansichten, Reiter, Tabellen) · `architecture` (auch Tempo-Messwerte) · `build` (PyInstaller, CI, Plattformen).

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
python tools/make_screenshots.py                       # README-Screenshots (docs/screenshots): Cover = Startbildschirm mit Beispielprojekt, jeder Tab mit den Daten von S3 (Beispielprojekt); alles nur dunkel (Nutzerwunsch)
```
- README kurz halten (Überblick, Abläufe, Download); alle Tab-Details in `docs/manual.de.md`/`docs/manual.en.md` (App-Links, Überschriften prüft der Selbsttest).
- Neue Funktion → eigener Abschnitt `with section:` im `selftest()` (`elucida/selftest.py`, Muster: `report.append("…: OK")` am Ende). Ein Fehler stoppt nur den Abschnitt, spätere können als Folge scheitern: den ersten FAILED zuerst lesen.
- In CI läuft der volle Selbsttest aus dem Quelltext (Linux, Windows, macOS arm64); die **fertig gebaute** App und das AppImage laufen als Rauchtest (`--selftest-group smoke`: Start, alle Importe der gebauten App, jeder Tab, ein Export, Word-SI). macOS Intel prüft nur die gebaute App: Rauchtest plus plattformnahe Abschnitte (Entscheidung 185).

## Release-Ablauf
Versionszählung seit 2026-11 neu: 1.0.0 ist die erste stabile Version; die Vorversionen (bis 2.7.1) und ihre Releases/Tags sind entfernt.
Installierte Vorversionen erkennen 1.0.x nicht als Update (Versionsvergleich), das ist bekannt und so gewollt. Versionsangaben in Kommentaren, Regeln und Selbsttest wie
„seit 2.3“ oder „bis 2.7.1“ meinen die alte Zählung (vor 1.0.0); „1.2.0“ meint den nie veröffentlichten Zwischenstand, der in 1.3.0 aufging.
1. `APP_VERSION` in `elucida/__init__.py` erhöhen.
2. `CHANGELOG.md` **und** `CHANGELOG.de.md` ergänzen (Titel und Notes erzeugt `tools/release_notes.py` daraus); bei sichtbaren
   Änderungen `docs/manual.en.md` **und** `docs/manual.de.md` (README nur für Neues von Gewicht).
3. Selbsttest, commit, push, dann **ein** Lauf: `gh workflow run build.yml --ref main -f release=vX.Y.Z`. Der Release-Job legt Tag und
   Release nur an, wenn alle vier Builds grün sind, und bricht ab, wenn das Tag nicht zu `APP_VERSION` passt. Zufällige Fehler
   (PySide-Event-Filter unter Windows, ETIMEDOUT beim Artefakt-Upload) mit `gh run rerun <id> --failed` wiederholen.
   Alternativ `git tag vX.Y.Z && git push --tags`. Ohne lokales Tag (z. B. Cloud-Sitzung): nach dem Merge auf `main` Actions → „Build Elucida“ →
   Run workflow mit `release` = `vX.Y.Z`. CI rot: Plattform- und Runner-Details in `.claude/rules/build.md` lesen.

## Bekannte Fallen
- **Umbenennungen (UVVisTool → Spectravolt → Elucida):** Repo `robinesken97/elucida`, Module seit 2.1 im Paket `elucida/`.
  Projektdatei `project.elucida` (`PRJ.PROJECT_FILE`); alte `project.uvvis` (`OLD_PROJECT_FILES`) wird gelesen und beim Speichern nach
  `.elucida/project.uvvis.old` verschoben. Cache-Name `.uvvis_cache` bleibt. Alte Einstellungen (`OLD_APP_NAMES`: zuerst `QSettings("Spectravolt")`, dann `"UVVisTool"`,
  `migrate_settings`) und der Datenordner (`app_data_dir`: `…/Spectravolt`, sonst `…/UVVisTool`) werden beim ersten Start übernommen. Alte Versionen fragen die GitHub-API unter den alten Repo-Namen ab
  (GitHub leitet um) – Repo **nie** neu unter `spectravolt` oder `uvvis-tool` anlegen. Der Updater sucht Pakete nur über die
  Systemkennung (`windows-x64` …), nicht über den Programmnamen. Icon-Quellen `assets/icon-light.svg`/`icon-dark.svg`,
  alle PNG/ICO/ICNS mit `python tools/make_icon.py` (ICNS nur auf macOS).
- **Windows-Zeilenenden:** CSVs in Tests mit `newline=""` schreiben; Reader überspringt leere Zeilen (früher `\r\r\n`).
- **Windows-Konsole (cp1252):** Selbsttest-Meldungen nur mit ASCII/cp1252-Zeichen (kein λ, ε); früher brach CI am `print` ab.
- **PyInstaller:** eigene Module kommen über `--collect-submodules elucida`; lazy geladene **fremde** Pakete als
  `--hidden-import` in `tools/build.py` eintragen. Pfade zu Repo-Dateien nur über `elucida.ROOT`, nie `__file__`.
- **MuPDF:** ignoriert SVG-Clip-Pfade → Kurven geometrisch clippen (`clip_polyline`); Rechtecke mit Breite 0
  fallen bei `|=` weg → Koordinaten-Union; Alpha ist premultipliziert → beim Einfärben un-premultiplizieren.
- **pymupdf:** `get_pixmap(dpi=…)` nur mit ganzen Zahlen (die Windows-Version wirft sonst TypeError; lokal unbemerkt).
- **Label-Kollisionen:** gespeicherte Positionen von Labels, Inset und Bildern vor neuen Elementen reservieren.
- **Platzierung (Nutzerwunsch 2.3):** Inset nie über Kurven – ohne freie Stelle rechts neben die schmalere Achse
  (`_make_room_right`/`_put_beside`, ohne Tabelle, nicht ins Layout gespeichert). Bandenlabels geordnet
  (`_place_labels_ordered`): Reihe mit gleicher Oberkante, sonst linksbündiger Block nach λ, erst dann einzeln.
- **macOS, natives Fenster:** Der erste Zeicheneditor (WebEngine) lässt Qt das NSWindow neu anlegen, Titelleiste und NSToolbar
  sind dann weg. `MainWindow.event` richtet sie bei `WinIdChange` neu ein (`_restore_title_bar`).
- **`layout.itemAt` nie direkt, immer `STYLE.item_at`:** PySide hält den Wrapper des Elements am Layout fest, Qt löscht das
  Element aber still (z. B. mit seinem Widget). Der tote Eintrag bleibt in PySides Adresstabelle; ein später an derselben
  Adresse angelegtes Python-Qt-Objekt stürzt ab (`SignalManager::retrieveMetaObject`, Adresse 0; zufällig je nach
  Allokator). Selbsttest „layout items“ prüft, dass keine solchen Wrapper bleiben.
- **Mausereignisse (matplotlib):** `LocationEvent` rundet x/y auf ganze Pixel; Messpunkte liegen in der Vorschau
  < 1 px auseinander. Tests mit simulierten Klicks/Hover nur auf ±1 Messpunkt prüfen und dann, dass die Anzeige
  genau den getroffenen Punkt zeigt (CI-Systeme treffen sonst unterschiedliche Nachbarn).
- **Undo:** während `set_state` greift `_restoring`; Änderungen über `QTimer` verzögert erfassen.
  `save_project` speichert trotzdem (`autosave(force=True)`), sonst blieb das Beispielprojekt leer.
  Rückgängig bleibt im offenen Tab bzw. zeigt den Tab der Änderung (`_restore`, Nutzerwunsch P9 R1); ein Schnappschuss,
  der sich nur im Tab unterscheidet, ist kein eigener Schritt. Ziehen speichert nur bewegte Elemente
  (`Dragger.moved`, ein Klick ins Bild hält die automatische Platzierung nicht fest).
- **Alte Projekte beim Anschauen (bekannt, nicht behoben):** ein Tab trägt beim ersten Zeigen fehlende Vorgabe-Schlüssel ein
  (`setdefault` in `FigureTab.__init__`, weitere beim ersten Zeichnen); das erste `render` → `push_undo` macht daraus
  Rückgängig-Schritte ohne sichtbare Änderung, das Autosave schreibt die Vorgaben in die Projektdatei. Werte bleiben gleich;
  Abhilfe nur über `push_undo`/Speichern des offenen Tabs (riskant).
- **Tempo:** `build_ui` nur beim Start, Sprach-/Theme-Wechsel. Öffnen und Rückgängig/Wiederholen über
  `set_state(partial=True)`/`_changed_parts`: nur geänderte Tabs ersetzen (`replace_tab`, feste `_TAB_BUILD_ORDER`, DFT
  liest X-Ray), ε nachziehen (`apply_globals`); Verbindung/Textformat geändert -> alle Tabs ersetzen, Fenster bleibt.
  Tabs werden **bei Bedarf gebaut** (`_lazy`, `__getattr__` auf `self.<x>_tab`, `_tab_shown`): nie `hasattr(self,
  "<x>_tab")` (baut), sondern `_built(key)`; Schleifen über alle Tabs nur über gebaute. Neue Tabs in `_tab_spec`/
  `_TAB_ORDER`/`_TAB_BUILD_ORDER`. `open_project` macht verborgene, schon gebaute Tabs wieder zu Platzhaltern (`_relazy`):
  Code darf Vorgabe-Schlüssel im Zustand eines ungebauten Tabs nicht voraussetzen (immer `.get`). Verborgene Tabs und
  Seiten zeichnen erst beim Anzeigen (`_first_render`; `CanvasHost` zeichnet erst sichtbar und in fester Größe;
  Rechenseiten wie NTO/ACID über `TABS.ShowHook`); `ensure_rendered()` vor Zugriff auf `F`. Projektdateien lesen mit
  `PRJ.read_yaml` (libyaml, falls vorhanden). PNG-Ersatz für Word mit `png_fast` (compress_level 1). Messwerte: `architecture`.
