# Selbsttest Stufe 2 – Bericht (Spur `lane-selftest2`)

**Stand: Hebel 1–5 fertig und gemessen; Hebel 6 (Aufteilen) in Arbeit.**

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

## Vereinbarungen mit der Hauptsitzung
- Phase 1–3 gegen `st_base` auf `35ce4c1`; vor Hebel 4 `origin/main` mergen und voll laufen lassen (neue Titelliste);
  das Aufteilen (Hebel 6) als eigene Commits oben drauf; am Ende `origin/main` noch einmal mergen.
- Watchdog (`faulthandler` in `_Section.__enter__`) übernimmt die Hauptsitzung auf `main` (win32 ausgenommen); in
  dieser Spur nicht angefasst.
