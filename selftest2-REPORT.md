# Selbsttest Stufe 2 – Bericht (Spur `lane-selftest2`)

**fertig** – Hebel 1–6 umgesetzt und gemessen, letzter Merge `origin/main` = `1ebcaab` (Merge-Commit `acefed6`).
Ungeprüft (Entscheidung der Hauptsitzung, die langen Läufe macht Robin lokal): Einzelläufe der Gruppen `comparison` und
`lanes` nach der letzten `GROUP_NEEDS`-Änderung, voller Lauf mit Fehlerprobe, voller sauberer Lauf auf dem gemergten
Stand (zuletzt grün: `st_split` auf `5eb46de`).

Start-SHA: `35ce4c1` (origin/main zum Zeitpunkt des Probelaufs). Branch `lane-selftest2` aus diesem Stand.

## Phase 0: Container-Probe

### Aufbau (wie Linux-Job in `build.yml`, mit Abweichungen)
| Punkt | CI (linux-x64) | Container |
|---|---|---|
| System | ubuntu-22.04 | Ubuntu 24.04.5, 4 Kerne, 16 GB RAM, ohne Swap |
| Python | 3.12.16 | 3.12.3 (venv) |
| Node | 24.x (setup-node) | 24.11.1 |
| apt-Pakete | wie Schritt „Qt-Bibliotheken (Linux)“ | dieselben; `libasound2` heißt hier `libasound2t64` |
| pip | `--prefer-binary -r requirements.txt` | dasselbe, 5 min, ohne Fehler |
| `tools/build_octet.py` | ok | ok (12 s) |
| Benutzer | `runner` (kein root) | eigener Benutzer `ci` (siehe unten) |
| Schriften | Runner-Schriften | **Arial/Helvetica fehlen** (matplotlib-Warnungen `findfont`) |

- [Certain] Der erste Lauf als root stürzte nach 20 s ab: QtWebEngine verweigert root ohne `--no-sandbox`
  (Segfault in `app/drawing_editor.py:402`). Deshalb läuft der Selbsttest als normaler Benutzer `ci`. Das entspricht
  dem CI-Runner; als root würden außerdem Dateirechte-Prüfungen nichts prüfen. Die App wurde nicht geändert.
- [Likely] Wegen der fehlenden Schriften sind die Abbildungen nur mit Läufen **in diesem Container** vergleichbar,
  nicht mit CI-Bildern. `st_base` ist die Container-Baseline (bleibt liegen, nicht im Repo).
- [Certain] `--selftest-isnet` funktioniert (Bericht: `background: isnet`, das Modell wurde über den Proxy geladen).
- [Certain] Während des Laufs wurde eine Swapdatei mit 16 GB angelegt (siehe Speicher); sie ändert den Test nicht.

### Vollständiger Lauf `st_base`
`QT_QPA_PLATFORM=offscreen PYTHONFAULTHANDLER=1 python Elucida.py --selftest st_base --selftest-isnet`

| Messgröße | Wert |
|---|---|
| Wandzeit | **6410 s = 107 min** (20:04–21:51 UTC) |
| Exit-Code | **1** |
| letzte Zeile | `FAILED: 1 section(s), see above` |
| Abschnitte | 234 Zeilen in `sections.tsv` (233 OK, 1 FAILED), 245 „…: OK“-Zeilen im Bericht |
| Summe der Abschnittszeiten | 6399 s (Rest: Start/Ende) |
| Platte `st_base` | **3,3 GB** (nicht ~6 GB wie angenommen) |
| Spitzen-RSS des Prozesses | **13,1 GB** (`VmHWM`), dazu bis 1,7 GB im Swap; System-RAM belegt bis 15,0 GB |

- [Certain] FAILED: `selftest.py:16608` „Spur A 1.3.0, Punkt 1“ (in CI „Lane A item 1 …“), Zeile 16648
  `AssertionError: Kinetik-CSV nicht im Tab`.
- [Certain] **Ursache (einzeln nachgestellt):** Der Abschnitt nimmt `next((dp_a1 / "S3").glob("data/uvvis-kinetics/*.csv"))`,
  also die **erste Datei in Verzeichnisreihenfolge** (unsortiert). Im Beispielprojekt liegen dort sechs Stabilitätsdateien
  (je 2 Proben) und eine Titrationsdatei (mehr Proben). Im Container liefert `glob` zuerst `S3_titration_NOSbF6.csv`. Nach dem
  Ersetzen der Kopfzeile durch `S3_t0,,S3_t1,,` bleibt eine dritte Probe (`#3`), der Drop fügt also 3 statt 2 Zeilen
  hinzu. Auf dem CI-Runner kam offenbar eine Stabilitätsdatei zuerst. Die App arbeitet richtig.
- [Certain] Das ist ein Reihenfolge-Fehler **im Test**, nicht im Container begründet: Er trifft jede Maschine, deren
  Dateisystem die Titrationsdatei zuerst liefert. Behoben ist er in dieser Spur nicht (Auftrag: nur berichten). Vorschlag
  für die Hauptspur: eine bestimmte Stabilitätsdatei wählen (z. B. `sorted(...)` mit Namensfilter `stability`). Das ändert
  weder Assertion noch Erwartungswert.
- [Certain] CI auf demselben SHA (Run 44798771010): linux-x64 rot mit 6 FAILED (laut Hauptsitzung 1 echter Fehler, eine
  CV-Tabelle 1 px quer, plus 5 Folgefehler), windows-x64 rot, macOS arm64 grün. Diese 6 sind im Container OK.
  **Abnahme deshalb (Entscheid der Hauptsitzung):** gleiche Titel in gleicher Reihenfolge und dieselbe FAILED-Menge
  wie diese Baseline, bis `main` auf Linux grün ist.

### 15 langsamste Abschnitte (`st_base/sections.tsv`)
| Zeile | s | Titel (gekürzt) |
|---:|---:|---|
| 15218 | 309.8 | Reset display keeps everything scientific (13 tabs of the example) |
| 17331 | 301.8 | Lane A2 item 3a (Export tab: lazy, rows, row export, export all …) |
| 14564 | 271.5 | Compound name with a dot (S3.1): 150 export files of all tabs + SI |
| 17487 | 255.3 | Lane A2 item 3b (SI column saved with the compound …) |
| 17890 | 228.2 | Lane A2 review fixes (B1 … N7) |
| 10813 | 220.4 | F5: Mnova (per compound only …), quick evaluation, home screen, Other tab |
| 13556 | 208.4 | Comparison in the combined SI |
| 17615 | 200.0 | Lane A2 item 3c/v4 (project page Export tab …) |
| 10235 | 193.7 | compound change reaches all tabs |
| 14017 | 189.8 | 1.2.0 review fixes: display round 2 |
| 16816 | 175.2 | Lane A item 3 (one export notice …) |
| 14232 | 154.6 | Round 5: unreadable saved files |
| 16858 | 135.6 | Lane A item 4 (PPTX writer …) |
| 18991 | 130.1 | NMR fix round 1 |
| 13785 | 129.3 | 1.2.0 review fixes: project and DFT |

- [Certain] Die Abschnitte ab Zeile 10813 (101 von 234) brauchen 5306 s = **83 %** der Zeit; im vorderen Teil
  steht kein Aufruf von `open_demo_publication`/`export_publication_si`. 60 Abschnitte dauern > 20 s, 133 < 5 s.
- [Certain] Aufrufe im Quelltext: `open_demo_publication(` 27×, `export_publication_si(` 10×, `export_all_tabs(` 4×
  (Textstellen; wie oft sie zur Laufzeit wirken, wird in Phase 1 gezählt).

### Speicher
- [Certain] Der Prozess wächst über den Lauf auf 13,1 GB RSS; ohne Swap waren 13,8 von 16 GB belegt, als die Swapdatei
  angelegt wurde. Ohne Swap wäre ein Abbruch durch Speichermangel wahrscheinlich gewesen [Likely].
- [Likely] Das Wachstum kommt vom wiederholten Neuaufbau von Fenster, Tabs und Beispielprojekt (CLAUDE.md: ~1,6 GB für eine
  App mit allen Tabs). Ursache wird in Phase 1 benannt, Spitzen-RSS je Lauf vorher/nachher.
- [Guessing] Auf 16-GB-CI-Runnern (Linux, Windows) ist der Lauf damit nahe an der Grenze.

### Eignung des Containers für viele Läufe
- Zeit [Certain]: ein voller Lauf dauert 107 min, so lang wie auf dem CI-Linux-Runner (dort 107 min auf diesem SHA).
  Ein Hintergrundbefehl darf hier höchstens 2 h laufen; der Lauf wird deshalb über ein Skript mit eigenem Prozess
  gestartet (hat 107 min ohne Abbruch überstanden).
- Parallel [Likely]: nicht möglich (je Lauf ~15 GB inkl. Swap). Also ~1 voller Lauf je 2 h; Gruppenläufe kürzer.
- Platte [Certain]: frei 39 GB (davon schon 16 GB Swap abgezogen). Je Lauf 3,3 GB → Platz für ~10 Läufe; ältere
  Läufe außer `st_base` werden nach dem Vergleich gelöscht.
- Netz [Certain]: PyPI, npm, nodejs.org und das isnet-Modell erreichbar; Artefakte der GitHub-Läufe
  (`*.blob.core.windows.net`) sind aus der Cloud-Sitzung gesperrt (403), Job-Logs sind lesbar.
- Fazit [Likely]: geeignet, aber langsam; Phase 1 misst nach jedem Schritt einen vollen Lauf (~1,5–2 h) oder nur
  die betroffenen Abschnitte, wo das reicht.

### Hinweis zum Commit
Dieser Commit enthält nur diese Datei (keine Codeänderung); der Selbsttest wurde deshalb nicht erneut ausgeführt.

## Phase 1: Hebel 1–3 (gemessen auf `35ce4c1`, Container wie Phase 0)

| Lauf | Inhalt | Wandzeit | Summe Abschnitte | Ergebnis | Spitzen-RSS |
|---|---|---:|---:|---|---|
| `st_base` | Baseline | 107 min | 6399 s | 1 FAILED (Lane A item 1) | 13,1 GB + 1,7 GB Swap |
| `st_check` | Lane-A-Fix + Hebel 1 im Prüfmodus (jeder Bau echt + Vergleich) | 100 min | 5897 s | **OK** | 13,2 GB + 1,8 GB Swap |
| `st_l1` | Lane-A-Fix + Hebel 1 | **75 min** | **4516 s (−29 %)** | **OK, exit 0** | **10,4 GB, kein Swap** |

- [Certain] Titel aller drei Läufe gleich, in gleicher Reihenfolge (Vergleich mit maskierten Messwerten in den Titeln,
  z. B. „tab opened in 0.98 s“; der Titel von Lane A item 1 ist in der Baseline die Kommentarzeile, weil er dort FAILED war).
- [Likely] Rauschen zwischen zwei Läufen ~8 %: `st_check` macht dieselben 27 Bauten wie `st_base` und war trotzdem
  8 % schneller (ISNet-Modell schon geladen, weniger Speicherdruck). Gewinne unter ~5 min sind mit einem Lauf nicht messbar.

### Lane A item 1 (`b4c32ac`)
Feste Stabilitätsdatei (`sorted(...glob("*_stability_day*.csv"))[0]`, zwei Proben) statt der ersten CSV in
Verzeichnisreihenfolge; Erwartung (n + 2) unverändert. In `st_check` und `st_l1` OK.

### Hebel 1: Beispielpublikation einmal bauen (`89ddb28`, `99e5c97`)
Wie die App ein Beispiel bzw. seine Frische erkennt (vor dem Umbau geprüft):
- [Certain] `demo.is_demo(path)`: nur über den **Pfad** (Ordner `Beispielverbindung`/`Beispielprojekt`/`Beispielpublikation`
  im Datenordner). Die Abschnitte bauen in eigene Ordner unter `out/` (nie dort) – die Kopie liegt im selben Ordner wie
  vorher der Bau, `is_demo` ist für beide falsch.
- [Certain] Projektdateien speichern nur relative Pfade (keine absoluten Pfade in den Textdateien der gebauten Publikation).
- [Certain] Vergleich: `comparison.fingerprint` = Hash des Zustands mit **relativen** Pfaden, `compare.json` liegt im
  Projekt – unabhängig von Ort und Dateizeit.
- [Certain] Vorschaubilder/Frische über Dateizeiten nur relativ zueinander (`welcome.write_thumb`: Bild jünger als die
  Struktur; `images` Export gegen CDXML; Export-Tab: das neueste gewinnt); Caches sind auf (Pfad, mtime) geschlüsselt
  (neuer Pfad = kein Treffer, wie beim Bau).
- Kopie: `copytree(copy2)` in den Ordner des Abschnitts, danach alle Dateizeiten um denselben Betrag verschoben (jüngste =
  jetzt). So bleiben alle Abstände (Frische) erhalten und „zuletzt geändert“ ist neu wie nach einem Bau (die Suche/
  Übersicht sortiert nach Stand). Fenster danach wie nach `open_demo_publication`: S2, dann S3 zuletzt benutzt,
  `last_project_dir`, Publikation geöffnet (`open_publication`), Statusmeldung.
- Schlüssel einer Vorlage = alle QSettings außer Pfaden, Zuletzt-Listen, Geometrie und Ansicht (`fold/`, `step/`,
  `welcome/`, `datapack/`) plus Sprache; ein anderer Schlüssel baut neu. `own=True` (baut immer) für die vier Abschnitte,
  die den Bau selbst prüfen: „publication (order, datapack, complete SI)“, „layout items“ (Qt-Wrapper nach dem Bau),
  „Comparison snapshots“ (Stand wird beim Speichern im Bau geschrieben), „Lane A2 item 3b“ (Bau liest die SI-Auswahl
  aus QSettings).
- Beleg (`st_check`, `ELUCIDA_SELFTEST_DEMO_CHECK=1`: jeder Aufruf baut echt und vergleicht mit der Vorlage seines
  Schlüssels): 19 Vergleiche, je 7–11 abweichende Dateien, **alle** von drei Arten [Certain]: (1) Vorgabe-Schlüssel mit
  gleichen Werten in `project.elucida`/`compare.json` (je nachdem, welche Tabs im Fenster schon gebaut waren – die
  bekannte Eigenheit „Alte Projekte beim Anschauen“ aus CLAUDE.md), (2) zufällige 8-stellige `uid`, (3) Zeitstempel in
  Zip-Dateien (HRMS-Bericht .docx: Inhalt gleich). Zwei echte Bauten unterscheiden sich also genauso wie Bau und Kopie.
- Ergebnis `st_l1` (`demo_pub.tsv`): 9 echte Bauten (je ~48 s), 18 Kopien (1–12 s). Neue Schlüssel durch: Sprache
  (3×), `si_figs_off`/`si_parts` (2×), `ui/theme`, `pub_si_*` (Gesamt-SI-Auswahl), `pub_dp_fid`.
- Abbildungen (`tools/compare_figures.py st_base st_l1`): 1455 gleich, 21 verschieden, 65 fehlend. Verschieden: 20×
  `.elucida/thumbs/*.png` in den Beispielkopien (Vorschaubilder des Export-Tabs, die der Bau aus dem jeweiligen
  Fensterzustand schreibt; optisch gleich, wenige Pixel Kantenglättung – die Kopie trägt die der Vorlage) und
  `epr_p6.png` (bekannt). Fehlend: Dateien mit zufälliger Kennung im Namen (Reaktionspfad-UUID, `*_<hash>_nmr.png`,
  Vergleichs-IDs), `failed_16608.png` (nur Baseline) und eine Schnellauswertung mit Datum im Ordnernamen. Exportierte
  Abbildungen sind alle gleich [Certain].
- Speicher [Likely]: Die Spitze sinkt von 13,1 auf 10,4 GB, weil weniger Bauten im selben Fenster laufen; das Wachstum
  kam also zu einem großen Teil von den wiederholten Bauten der Beispielpublikation (jeder Bau rendert alle Tabs).

### Hebel 2: Exporte wiederverwenden – keine Stelle
[Certain] Jede Stelle prüft die Export-Aktion selbst oder einen vorher geänderten Stand; gleiche Ausgabe des gleichen
Stands prüfen nie zwei Abschnitte. Deshalb keine Wiederverwendung (Entscheidung nach Brief: Abschnitt, der eine Änderung vor
dem Export prüft, behält seinen Export):
| Abschnitt | Aufruf | warum nicht teilbar |
|---|---|---|
| Cards instead of dialogs | `export_si_dialog` | prüft den Knopf (direkt, ohne Dialog) |
| SI: figures selectable per tab | `export_si` | eigene Abwahl von Abbildungen |
| SI lines + SI section as Word | `export_si` 2× | verschiedene Teile (`parts`) |
| F5: Mnova …, quick evaluation | `export_publication_si` 3× | Vorlagen group/nature/acs, andere Kapitel |
| F1 synthesis | `export_publication_si` | nur `char`, ohne Verzeichnis |
| Comparison in the combined SI | `export_publication_si` 2× | vor/nach Aufnahme der Vergleiche in die SI |
| Purity, FID, SI labels … | `export_publication_si` | Vorlage group, eigene Teile, nach Änderung der Reinheit |
| 1.2.0 review fixes: project and DFT | `write_publication` | Datenpaket mit eigener Auswahl |
| Round 5: unreadable saved files | `export_si_dialog`, `export_publication_si` | nach Unlesbarmachen von Dateien |
| Compound name with a dot | `export_si_dialog` | nach Umbenennen in „S3.1“ |
| Lane A item 3 | `export_si_dialog`, `export_publication_si` | Meldung mit abgewählten Teilen |
| Lane A2 item 3a / review fixes / R7 | `export_all_tabs` 4× | prüft Rückgängig, Ordnerfrage, Auffrischen, Freigabe |
| Lane A2 item 3b | `export_publication_si` | nach Abwahl, ohne Methoden |

### Hebel 3: Bedingungs-Waits (`0e172d4`)
- Messung (`st_l1`, lokaler Messpatch, nicht committet): Zeit in allen `pump*`-Funktionen = **554 s = 12 %** der
  Abschnittszeit, 1686 Aufrufe. Der größte Block („compound change reaches all tabs“, 71 s, 584 Aufrufe) ist schon
  bedingt (wartet, bis Strukturen im Hintergrund geladen sind); „Reset display …“ (57 s) wartet nach jedem Zeichnen aller Tabs.
- Umgestellt (nur eindeutig: etwas muss eintreten): 15 Stellen direkt nach `undo()`/`redo()`, deren Prüfung nur den
  wiederhergestellten Zustand liest: `_until(lambda: not w._restoring, pump…)` (höchstens 10 s) statt fester 0,2–1,5 s.
  `_restoring` wird in `_restore` sofort gesetzt und 200 ms später von `_end_restore` gelöscht [Certain].
- Nicht umgestellt: Waits vor „nichts passiert“-Prüfungen (kein Rückgängig-Schritt, nicht gespeichert, keine Datei) –
  die brauchen die volle Zeit; Waits ohne eindeutiges Ereignis (Neuzeichnen, Layout).
- Gewinn [Likely]: lokal ~4–5 s, in CI etwas mehr (`pump()` wartet dort 2,5-mal so lange) – unter dem Laufrauschen,
  deshalb kein eigener Messlauf; geprüft im vollen Lauf nach dem Merge (Entscheidung: Nachtzeit für Hebel 4–6).
- Hinweis [Certain]: `pump()` multipliziert unter `CI` mit 2,5; meine Läufe setzen `CI` nicht (Baseline auch nicht).

## Merge `origin/main` vor Hebel 4 (`f3becf9`, main = `10cc795`)
- Voller Lauf `st_m` auf dem gemergten Baum: **OK, exit 0**, 80 min, Spitzen-RSS 11,2 GB, kein Swap, 236 Abschnitte.
- Titel = `st_l1` plus die zwei neuen Abschnitte von main („FitGrid fills 300..800 px …“, „Tables (decision 170) …“),
  sonst identisch und in gleicher Reihenfolge. **Das ist die neue Basis-Titelliste** für Hebel 4–6 (Datei
  `st_m/sections.tsv`, Abbildungen `st_m/` als Vergleichsbasis).
- Die 15 umgestellten Waits aus Hebel 3 laufen darin grün.

## Hebel 4/5: Rauchtest-Gruppe und build.yml (`9cd191f`)
Ohne das Aufteilen nutzbar: `--selftest-group smoke` (oder `main` = alles andere). Nicht gewählte Gruppen stehen als
eine Zeile `SKIPPED` in `sections.tsv`, oben als „skipped n group(s): …“ und in der Schlusszeile – nie als OK.
Die Stufe-1-Selbstprüfung zählt die Zeilen weiter exakt (`len(tsv) == len(rows) + 1`) und prüft zusätzlich an einem
Wegwerf-Lauf, dass eine übersprungene Gruppe genau eine SKIPPED-Zeile ergibt, oben gezählt und nie unter den
langsamsten steht (verschärft, nicht gelockert).

Rauchtest (`elucida/selftest_smoke.py`, 6 Abschnitte „smoke: …“), im vollen Lauf als erste Gruppe, mit eigenem Fenster,
eigener Einstellungsdatei und Unterordner `smoke/` (die übrigen Abschnitte sehen davon nichts):
1. jedes `--hidden-import`/`--collect-all` aus `tools/build.py` (Liste wird dort gelesen; macOS-Zusätze nur unter
   darwin) und jedes eigene Modul (`--collect-submodules elucida`, außer `__main__`) importieren. `tools/build.py`
   legt die Datei dafür jetzt per `--add-data` in die gebaute App.
2. Repo-Dateien über `elucida.ROOT` (`resource_path` = ROOT): Symbole, Lizenztexte, Octet (`embedded.html`,
   `bridge.js`, Lizenzen, Skripte), Mnova-Skript, Handbuch-Verweise (Online-Fassung; `docs/` liegt nicht in der App).
3. Start, UV-Vis-Projekt: rdkit (CDXML → Molmasse), HEIC-Foto mit ISNet/onnxruntime (bzw. GrabCut ohne Download),
   PDF/SVG/PNG-Export, MuPDF-Rendern, openpyxl.
4. Beispielprojekt: alle 17 Tabs gebaut, 13 Abbildungen gezeichnet.
5. Octet-Zeichner (WebEngine) bereit.
6. ein Export (CV), eine Word-SI, eine PPTX.

| Lauf | Ergebnis | Zeit |
|---|---|---|
| Rauchtest allein, aus dem Quellcode (`st_smoke`) | OK, exit 0, „skipped 1 group(s): main“ | 149 s |
| Rauchtest allein, **gebaute App** (PyInstaller im Container, `dist/Elucida/Elucida`) | OK, exit 0 (109 eigene Module gefunden, build.py mitgeliefert) | 150 s |
| voller Lauf mit Rauchtest (`st_45`) | **OK, exit 0**; Titel = `st_m` + die 6 Rauchtest-Titel vorn, Spitzen-RSS 11,3 GB | 87 min (Summe +426 s: Rauchtest ~150 s, Rest Rauschen) |

Nicht im Container geprüft: AppImage (kein `appimagetool` hier), Windows- und macOS-Builds – das zeigt erst die CI.

build.yml:
- Quellcode: voller Selbsttest wie bisher auf Windows, Linux, macOS arm64.
- Gebaute App (Windows, macOS, Linux) und AppImage: nur `--selftest-group smoke` (Timeouts 30 bzw. 45 min statt 180/320).
- macOS Intel (nur gebaute App): bis zum Aufteilen nur der Rauchtest; nach dem Aufteilen zusätzlich die plattformnahen
  Gruppen (siehe Hebel 6).

## Hebel 6: Selbsttest in Gruppen (`8acc5db`, `e80a1df`, CI `5eb46de`)
Aufbau (Commit oben auf 1–5; 1–5 bleiben ohne ihn nutzbar):
- `selftest()` ruft nach dem Rauchtest 14 Gruppenfunktionen `_g_<name>(ctx)` in der alten Reihenfolge auf:
  `start` (Fenster, Projekt, Eingaben) · `uvvis` (ε, Overlay, TD-DFT, Fluoreszenz) · `electrochem` (CV, SEC, H-Cell) ·
  `epr_kinetics` (EPR, UV-Vis-Kinetik, Titration) · `ui` · `ir_hrms` · `xray` · `dft` · `nmr_synthesis` · `project_si`
  (SI, Projekt, Datenpaket, Undo, Beispielprojekt) · `publication` (Projektseite, Beispielpublikation, Layout,
  Selbstprüfung) · `comparison` · `lanes` (spätere Spuren) · `nmr_own` (eigene NMR-Verarbeitung, Tabellen, Quit).
- Erzeugt aus den Abschnittsgrenzen (Generator im Bericht beschrieben, nicht im Repo): der Code jedes Abschnitts bleibt
  Zeile für Zeile gleich und gleich eingerückt (Gruppenkörper in `try/finally`, nichts umgerückt – 176 mehrzeilige
  Strings im Selbsttest). Geändert ist nur: die drei Hilfen `pump`, `free_win_`, `wait_path_` stehen jetzt in `start`
  (vorher in einem uvvis-Abschnitt), und Module, die eine Gruppe aus dem Import einer früheren nutzte, importiert sie
  selbst (gleiches Modulobjekt).
- Namen fließen über ein Wörterbuch `ctx`: jede Gruppe bindet die Namen, die sie vor eigener Zuweisung liest, aus `ctx`
  (nur wenn vorhanden – fehlt einer, scheitert genau der Abschnitt mit NameError wie früher), am Ende gehen alle ihre
  lokalen Namen zurück in `ctx`. Statische Prüfung: keine Closure einer Gruppe wird später benutzt, während ein von ihr
  gelesener Name dort neu gebunden wird; kein `nonlocal`/`global`.
- `--selftest-group a[,b…]`: gewählte Gruppen laufen mit Titeln; frühere Gruppen, die sie brauchen (`GROUP_NEEDS`),
  laufen still als **Fixture** (Titel nicht gezählt, eine Zeile `FIXTURE`, bei einem Fehler darin `FAILED` und Exit 1);
  alle anderen sind `SKIPPED`. Ohne Option: alles wie bisher. Unbekannte Gruppe: Meldung, Exit 2.
- `GROUP_NEEDS` aus zwei Quellen: Namensanalyse (Dateien/Variablen früherer Gruppen: dft ← xray; project_si ← ir_hrms,
  dft; publication ← electrochem, dft, project_si) und Einzelläufe (Zustand des Fensters, den Namen nicht zeigen):
  - electrochem ← uvvis (erster CV-Abschnitt erwartet den Rückgängig-Verlauf, allein `IndexError` auf `w._undo[-2]`)
  - project_si ← uvvis (Overlay-Einträge)
  - ui, comparison, lanes ← **alle früheren Gruppen** (konservativ: Klappbereiche/Tab/Daten bzw. Vergleichsseite,
    verborgene NTO-Seite, Dateien aus xray, Reaktionspfad – mehrere Ursachen, keine eindeutige)
- Stufe-1-Selbstprüfung: zählt weiter exakt, `SKIPPED`- und `FIXTURE`-Zeilen müssen genau den übersprungenen bzw.
  still gelaufenen Gruppen entsprechen.

Einzelläufe (Container, `--selftest-isnet`; Zeit = ganzer Prozess):
| Gruppe | Runde 1 | Runde 2 (nach `GROUP_NEEDS`) | eigene Abschnitte | Fixtures |
|---|---|---|---|---|
| smoke | OK, 148 s | | 6 / 144 s | – |
| start | OK, 7 s | | 1 / 6 s | – |
| uvvis | OK, 68 s | | 29 / 61 s | start |
| electrochem | 3 FAILED | **OK, 134 s** | 15 / 65 s | start, uvvis |
| epr_kinetics | OK, 133 s | | 16 / 126 s | start |
| ui | 2 FAILED | **OK, 329 s** | 7 / 68 s | start…epr_kinetics |
| ir_hrms | OK, 26 s | | 13 / 19 s | start |
| xray | OK, 43 s | | 8 / 36 s | start |
| dft | OK, 160 s | | 23 / 116 s | start, xray |
| nmr_synthesis | OK, 18 s | | 6 / 12 s | start |
| project_si | 5 FAILED | **OK, 937 s** | 18 / 685 s | start, uvvis, ir_hrms, xray, dft |
| publication | 2 FAILED (nur Fixtures) | **OK, 1383 s** | 26 / 387 s | 7 Gruppen |
| comparison | 2 FAILED | **nicht gelaufen** (ungeprüft, s. u.) | 17 | alle früheren |
| lanes | 12 FAILED | **nicht gelaufen** (ungeprüft, s. u.) | 39 | alle früheren |
| nmr_own | OK, 415 s | | 18 / 408 s | start |

Voller Lauf nach dem Aufteilen (`st_split`, Stand `5eb46de`): **OK, exit 0**, 242 Abschnitte, Titel und Reihenfolge
gleich `st_45` (0 Abweichungen mit maskierten Zahlen; = `st_m` + 6 Rauchtest-Titel), 90 min (Summe der Abschnitte
5371 s gegen 5203 s, +3 % – im Rauschen von ~8 %), Spitzen-RSS 11,5 GB, kein Swap. Das Aufteilen spart keine Zeit
und soll es nicht; es macht die Gruppen einzeln aufrufbar.
Abbildungen (`compare_figures.py st_m st_split`): 1747 gleich, 2 verschieden, 71 fehlend. Verschieden:
`a2_pub/S3/.elucida/thumbs/eps.png` (Vorschaubild der Beispielkopie, Art wie unter Hebel 1) und `epr_p6.png` (bekannt).
Fehlend: Dateien mit zufälliger Kennung (Reaktionspfad-UUID, `*_<hash>_nmr.png`) und zwei Export-Tab-Vorschaubilder in
`a2x_pub` (`dft_3`, `xray_2`): [Likely] zeitabhängig (Vorschauen nur innerhalb des Zeitbudgets aus Entscheidung 103) –
schon `st_base` und `st_m` unterscheiden sich dort (`st_base` ohne `dft_3`). Exportierte Abbildungen alle gleich [Certain].

Rauchtest + Intel-Gruppen zusammen (`--selftest-group smoke,uvvis,epr_kinetics,ir_hrms,xray,dft,nmr_synthesis`): **OK, exit 0**, 554 s (ganzer Prozess),
101 Abschnitte OK, 1 FIXTURE (start), 7 SKIPPED. Auf dem Intel-Runner [Guessing] ×2,7 wie bisher beobachtet ≈ 25 min
statt ~204 min für den ganzen Selbsttest der gebauten App.

### Was auf macOS Intel nicht mehr läuft
Intel lief bisher den ganzen Selbsttest der gebauten App (~204 min). Jetzt Rauchtest + uvvis, epr_kinetics, ir_hrms,
xray, dft, nmr_synthesis (+ start als Fixture). Nicht mehr auf Intel (laufen weiter aus dem Quellcode auf Linux,
Windows, macOS arm64): electrochem (CV, SEC, H-Cell), ui (Oberfläche, Layout, Erscheinungsbild), project_si (SI-Word,
Projektordner, Datenpaket, Undo, Beispielprojekt), publication (Projektseite, Gesamt-SI, Papierkorb, Layout-Wrapper,
Zwischenablage in „processing chain card“), comparison (Vergleiche, Zwischenablage), lanes (spätere Spuren, Export-Tab,
PPTX, Zwischenablage „Copy Figure“), nmr_own (eigene NMR-Verarbeitung, Tabellen-Dateien). Papierkorb und Zwischenablage
werden damit auf Intel nur noch über den Rauchtest (Word/PPTX/Export) und gar nicht direkt geprüft – wenn das wichtig
ist, `publication` dazunehmen (+~25 min im Container ×2,7). **Entscheidung (Robin über die Hauptsitzung):** Intel bleibt
wie in `5eb46de`, ohne `publication`; keine eigenen CI-Jobs je Gruppe vorerst.

### Fehlerprobe (lokal, nie committet)
Zwei absichtlich falsche Prüfungen (`assert False`, Skript außerhalb des Repos, nach jedem Lauf zurückgesetzt):
im Rauchtest nach dem Öffnen des Beispielprojekts (`selftest_smoke.py`, Abschnitt „example project“) und in
„Entscheidung 130“ (Gruppe `nmr_own`) direkt nach `demo_pub(w, out / "l130_pub")`, also in einem Abschnitt mit gemeinsam
gebauter Beispielpublikation (Kopie der Vorlage aus Hebel 1).

| Lauf | Ergebnis |
|---|---|
| `smoke,nmr_own` auf `5eb46de` | **FAILED, exit 1**; beide Fehler oben in der Zusammenfassung, `failed_20008.png`; Mangel gefunden: der Rauchtest-Fehler hieß `selftest.py:88`, ohne Titel und ohne Bild |
| `smoke` nach der Korrektur `60fa845` | FAILED, exit 1, `FIRST FAILED: selftest_smoke.py:136 smoke: example project, all tabs`, `failed_selftest_smoke_136.png` (+ 2 Folgefehler, als solche markiert) |
| `smoke,nmr_own` auf dem gemergten Stand `acefed6` | **FAILED, exit 1**, 4 FAILED (erster = Rauchtest, Folgefehler in Octet/Export markiert, `selftest.py:20036` Entscheidung 130), 1 FIXTURE (start), 12 SKIPPED; `sections.tsv` vollständig, `failed_20036.png` und `failed_selftest_smoke_{136,159,166}.png`; 546 s |

Korrektur `60fa845` (Folge der Probe): Zusammenfassung, „slow section“ und Watchdog nennen die Quelldatei
(`selftest_smoke.py:<Zeile>`); Bild bei einem Fehler auch aus dem Rauchtest-Fenster (`failed_selftest_smoke_<Zeile>.png`,
Namen der übrigen Bilder unverändert); die Rauchtest-Abschnitte tragen Titelkommentare, damit ein Abschnitt, der vor
seiner OK-Zeile scheitert, einen Titel hat. Keine Prüfung gelockert.

### Für später: Gruppen auf parallele CI-Jobs verteilen (nicht in dieser Spur)
- Je Job: `--selftest-group` mit einer Teilmenge; Fixtures laufen dort still mit (Zeit zählt doppelt: ui, comparison und
  lanes ziehen heute alle früheren Gruppen nach – vorher echte Fixtures daraus machen).
- Ergebnis zusammenführen: `sections.tsv` je Job; die Titel aller Jobs zusammen = Titelliste des vollen Laufs.
- Beispielpublikation: jeder Job baut seine eigene Vorlage (Hebel 1 wirkt nur innerhalb eines Prozesses).
- Artefakte je Job (`selftest_*/sections.tsv`, `failed_*.png`) und ein Abschlussjob, der alle Berichte liest.

## Letzter Merge `origin/main` (`acefed6`, main = `1ebcaab`)
- Ein Konflikt in `_Section.__enter__`: main ersetzt den `faulthandler`-Watchdog durch eine Zeile aus eigenem Thread
  (alle Systeme); übernommen, nur die Quelldatei aus `60fa845` eingesetzt (`section at selftest_smoke.py:<Zeile> still running`).
- Die zwei Abschnittsänderungen von main (CV-Tabellen bei 1200 px mit ausführlicher Meldung; Spaltenhöhe nach dem
  Umbau) hat Git ohne Konflikt in die Gruppen `electrochem` bzw. `lanes` übernommen – der Abschnittscode ist ja Zeile für
  Zeile gleich geblieben. Der neue lokale Import (`QFont`, `QFontInfo`, `QFontMetrics`) in `electrochem` wird in dieser
  Gruppe nirgends vorher gelesen (kein `UnboundLocalError`), und kein Modul-Import gleichen Namens wird verdeckt.
- Nach dem Merge gelaufen: nur die Fehlerprobe `smoke,nmr_own` (oben). **Kein** sauberer voller Lauf auf `acefed6`
  [Certain] – CLAUDE.md verlangt ihn vor jedem Commit; die Hauptsitzung hat ihn an Robins lokalen Lauf und die CI
  übergeben.

## Vereinbarungen mit der Hauptsitzung
- Phase 1–3 gegen `st_base` auf `35ce4c1`; vor Hebel 4 `origin/main` mergen und voll laufen lassen (neue Titelliste);
  das Aufteilen (Hebel 6) als eigene Commits oben drauf; am Ende `origin/main` noch einmal mergen.
- Watchdog (`faulthandler` in `_Section.__enter__`) übernimmt die Hauptsitzung auf `main` (win32 ausgenommen); in
  dieser Spur nicht angefasst.
- Abschluss (Robin über die Hauptsitzung, 2026-11-21): Stufe 2 verkürzt; Intel bleibt wie in `5eb46de` (ohne
  `publication`), keine eigenen CI-Jobs je Gruppe; vollen Selbsttest und CI startet die Hauptsitzung.
