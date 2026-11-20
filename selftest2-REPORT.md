# Selbsttest Stufe 2 – Bericht (Spur `lane-selftest2`)

**Stand: Phase 0 abgeschlossen (Probelauf im Container). Warte auf „GO <sha>“.**

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

## Phase 1+
Noch nicht begonnen. Zusätzlich vereinbart (Hauptsitzung, 21:12 UTC):
- Phase 1–3 gegen `st_base` auf `35ce4c1` messen, `origin/main` erst am Ende mergen.
- Spitzen-RSS je Lauf vorher/nachher und Ursache des Wachstums.
- Der Wächter `faulthandler.dump_traceback_later(600, repeat=True)` in `_Section.__enter__` darf den Lauf nie abbrechen
  (auf einem langsamen Windows-Runner brach er nach > 600 s in „Reset display …“ mit einer Zugriffsverletzung ab).
