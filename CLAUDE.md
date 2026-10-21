# CLAUDE.md – Spectravolt (früher UVVisTool)

PySide6-Desktop-App (Windows wichtigste Plattform, dazu macOS arm64, macOS Intel ab 14 und Linux) für UV-Vis-Verdünnungsreihen:
Lambert-Beer-Auswertung (ε bzw. a) und Abbildung im Origin-Stil (Spektren, λ/ε-Labels, Inset mit Regression
und Tabelle, ChemDraw-Struktur, Küvettenfoto). Dazu Tabs für Overlay (gemessen + TD-DFT), Fluoreszenz, CV, SEC, EPR, IR + MS und X-Ray (CIF).
Öffentliches Repo, AGPL-3.0. Maintainer: Robin (Chemiker, kein Softwareentwickler; Git-Einsteiger).

## Zusammenarbeit
- Antworten auf Deutsch, direkt und technisch präzise. Aussagen mit [Certain]/[Likely]/[Guessing] kennzeichnen.
- Keine Zustimmungsfloskeln. Wenn ein Wunsch fachlich fragwürdig ist (z. B. Statistik), das zuerst sagen,
  dann umsetzen.
- Git-Schritte (commit, tag, push, Release) kurz erklären und vor dem Push bestätigen lassen.
- Testdaten des Nutzers sind unveröffentlicht oder gehören Studierenden: **nie** CSV/DSW/BSW/HEIC/CDXML/ORCA-Ausgaben
  committen (siehe `.gitignore`). Keine Probennummern, Verbindungsnamen, Messwerte unveröffentlichter Arbeiten oder
  Namen von Mitarbeitenden in README/CHANGELOG/CLAUDE.md/Code (öffentliches Repo).

## Fachliche Regeln (nicht ändern ohne Rückfrage)
- ε (M⁻¹ cm⁻¹) **nie mit Nachkommastellen** anzeigen; Rundung auf die Genauigkeit des Standardfehlers
  (`core.fmt_ve`, `eps_max_decimals`). Sehr kleine Fehler auf 1 Einheit aufrunden, nie „± 0“.
- Fit: A/d = m·c + b (OLS); ε = m / f_c (f_c: mM 1e-3, µM 1e-6, M 1; mg/mL über die Molmasse; ohne Molmasse
  spezifischer Koeffizient a in L g⁻¹ cm⁻¹). 95-%-KI = t(0,975; n−2)·SE (eigene `t_quantile`).
- Cutoff global (Standard A = 1) und pro Bande; Banden mit R² < `min_r2` (einstellbar, Standard 0,98) stehen in
  Tabelle/CSV/Excel, aber nicht im Bild. Bei 4 Punkten ist R² wenig aussagekräftig, KI zählt.
- Konzentrationsdialog: **keine** vorbelegte Einheit/Startkonzentration (führte früher zu falschem ε).
- ChemDraw-Struktur **unverändert** übernehmen: gleichnamige SVG/PDF/PNG neben der CDXML hat Vorrang; RDKit
  (ACS1996-Modus, keine eigene Bindungslänge) nur als Fallback. Bilder behalten immer ihr Seitenverhältnis
  (gespeichert wird nur die Breite).
- „(sh)“ für Schultern ist abschaltbar; Molmasse aus CDXML inkl. Isotopen.
- TD-DFT: Gauß-Verbreiterung in Energie; Kurve und Sticks teilen **immer einen** Skalierungsfaktor
  (Modi `band` Standard, `max`, `faxis`). ORCA 5/6-Zustandslabels („0-1A -> 1-1A“) nach „->“ splitten; SOC-Tabelle.
  Multiplizität aus dem Label („1-3A“ = Triplett), ORCA 4/5 aus dem TRIPLETS-Block, Gaussian aus „Triplet-A“;
  Tripletts (f = 0) nur als Marken, nie in der Gauß-Kurve; mit SOC keine Multiplizität (gemischte Zustände).
  Kombinieren: Übergänge mehrerer Rechnungen (`sources`, je Gewicht) erst zusammenführen, dann verbreitern.
- CV: Strom wie aufgezeichnet (Gamry IUPAC, anodisch positiv); Paare nur im Fenster (gespeichert in gemessenen
  Potentialen, angezeigt in Achsenskala); i_pc/i_pa nach Nicholson; Referenz E_Fc = E − (E½,ref − E°ref);
  Ac₂Fc-Vorgabe +0,49 V vs. Fc⁺/Fc (ergibt die publizierten −1,10 V für 6m), immer änderbar lassen.
- SEC: Nernst-Fit aus kontinuierlichem Scan nur als „scheinbar“ ausweisen (Nachhinken in der Dünnschichtzelle:
  6m in THF E½ ≈ −0,76 V statt −0,89 V im CV, n ≈ 0,45); CV-Werte haben Vorrang.
- EPR: Reihenfolge hell − k·dunkel → Basislinie → Ausblenden → Glätten → Normieren; Simulation mit dem
  Normierungsfaktor ihrer Messung (Verhältnis bleibt). Triplett-Simulation nicht selbst rechnen (EasySpin), nur
  importieren. Projekte kopieren BES3T-Partnerdateien (.dsc/.DTA/.YGF/.xml) mit.
- EPR S = ½: nur isotrop, erste Ordnung; Fit = Grobsuche (Lage, Kopplungsfaktor) + LM; Amplitude linear. Mehrere
  Komponenten je Messung immer gemeinsam linear skalieren. Kalibrierung: ΔB = B(g_fit, ν_ref) − B(g_lit, ν_ref),
  von allen Messungen außer der Referenz abziehen (MS400-Beispiel: +3,41 mT, 6m•+ danach g ≈ 2,0026).
- EPR-Zerfall (Nachbau des MATLAB-Skripts der Arbeitsgruppe): Gauß+Gerade, Zentrum nur innerhalb der Messpunkte (sonst beliebige
  Amplitude bei Spektren ohne Signal); Min-Max-Normierung; Fit-Start per Raster über E_a mit ln A aus T₅₀ (direkter
  Start scheitert an der Korrelation ≈ 1). Standard: kleinste Quadrate (belastbares Intervall, t-Quantil); „wie Skript“
  (√|r|) nur zum Vergleich – hängt stark vom Optimierer und von Spektren ohne Signal ab.
- Export: Standard 16 × 11 cm (halbe A4-Seite in Word, zwei Abbildungen pro Seite), minimale Ränder; PDF/SVG
  vektoriell, Text in SVG als Pfade. Exporte überschreiben im Projektordner unter `exports/…`.
- HRMS: calc. = monoisotopisch **mit Elektronenmasse** ([M+H]⁺ = M + 1.007276), calc./found immer 4 Nachkommastellen;
  ppm zur Kontrolle als found − calc (die Massenabteilung gibt das umgekehrte Vorzeichen an). IR: ganze Zahlen,
  absteigend; Bereich standardmäßig der ganze gemessene; mit OPUS-PDF gelten dessen Peakwerte.
- HRMS aus Bruker-.d (BAF): nur Linienspektren (MS1, ohne Steps); m/z aus Transformator-Blob (Variante int 10,
  112 B): t = Delay + Takt·Index, t = c0 + √(1e12·m'/c1) + c2·m' (Newton), m/z = m' − c6. Geprüft gegen CompassXport
  (eine Messung, alle Peaks auf 4 Nachkommastellen). Unbekannte Varianten **ablehnen**, nicht raten. found = mit der
  Intensität gewichtetes Mittel über den LC-Peak (≥ 50 % des Maximums, zusammenhängend, ± 10 ppm um calc.); Streuung
  immer mit anzeigen. Bericht der Massenabteilung bleibt vorgewählt.
- X-Ray: Standardabweichungen **nur aus der CIF** (`_geom_bond/_angle/_torsion`, Text unverändert, z. B. „1.392(3)“),
  **nie schätzen**; fehlt ein Wert, selbst rechnen und ohne esd markieren (Torsion: Hinweis „CONF setzen“).
  Symmetrie: Molekül über Bindungen × Symmetrieoperationen vervollständigen; Abgleich mit geom-Einträgen über
  Transformationen (gesucht G mit T_k = G∘S_k, auch rückwärts), Codes `n_klm` (555 = keine Translation, „n“ allein
  ebenso). Erzeugte Atome mit römischer Hochzahl je Operation + Fußnote. Fehlordnung Standard: PART 0 + je
  `disorder_assembly` der Teil mit der größten Besetzung. Ellipsoide: k = √χ²₃(p) (50 % → 1.5382), Umriss = 2×2-Block
  von R·U·Rᵀ. Tabellen englisch beschriftet, Zahlen exakt wie in der CIF, echtes Minus (U+2212).
- Verbindung des Projekts (`compound`) ist nur Vorgabe: Tabs mit eigener Struktur/Molmasse behalten diese.
- UI zweisprachig: jeder sichtbare Text über `uvvis_i18n.T(key)` mit DE **und** EN-Eintrag.

## Architektur
| Datei | Inhalt |
|---|---|
| `uvvis_gui.py` | Hauptfenster, ε-Tab, Projektlogik, Undo/Redo (JSON-Snapshots von `get_state`), Autosave, `selftest()`. `APP_VERSION` steht hier. |
| `uvvis_core.py` | `DEFAULTS`, Reader (Cary CSV, DSW/BSW/FBSW via `parseuv_lite`, Eclipse CSV), Basislinie, Peak-/Schultersuche, `linfit`, `evaluate`, `Figure` (Platzierung über FreeSpace-Raster, gespeicherte Positionen zuerst reservieren), Export, `Dragger`. |
| `uvvis_tabs.py` | `CanvasHost` (Vorschau maßstabsgetreu, dynamische DPI), Overlay- und Fluoreszenz-Tab. |
| `uvvis_extra.py` | TD-DFT-Parser (ORCA/Gaussian), Verbreiterung, `SimpleFigure`, Fotopaar mit Pfeil. |
| `uvvis_images.py` | Bilder laden (HEIC, EXIF), Hintergrund entfernen (ISNet-ONNX → GrabCut → Rand), Struktur-Rendering (PyMuPDF), Vektor-Overlay in PDF/SVG. |
| `uvvis_chem.py` | CDXML über RDKit: Formel, Molmasse, Ersatzzeichnung. |
| `uvvis_project.py` | Projektordner (`project.uvvis`, `data/`, `exports/`), relative Pfade, Backup. |
| `uvvis_report.py` | Excel-Report (openpyxl): Werte blau, Kontrollformeln schwarz, native Diagramme; Sprache = Programmsprache. |
| `uvvis_cv.py` | Cyclovoltammetrie: Gamry-.DTA-Leser (CURVEn oder CURVE+Cycle), `analyze_couple` (E_pa/E_pc/E½/ΔE_p, Nicholson), `suggest_couples`, Randles-Ševčík, `CVTab`. |
| `uvvis_sec.py` | Spektroelektrochemie: BWSpec-Leser (λ aus coefs_a0…a3), Potential je Spektrum über Uhrzeit (Gamry DATE/TIME + T), scheinbarer Nernst-Fit (Raster E½/n), `SECTab`. |
| `uvvis_epr.py` | CW-EPR: BES3T-Leser (.dsc/.DTA, LIT/BIG, D/F/I, 2D+YGF), ASCII (MS400, EasySpin), EasySpin-Parameter (`Sys.D` MHz → cm⁻¹), Dunkelspektrum, Basislinie, Ausblenden, Glätten, `fit_scale`, `EPRTab`. Felder intern in mT. |
| `uvvis_color.py` | Farbe der Lösung: T = 10^(−A) × Planck 6504 K, CIE-1931-Kurven (Näherung Wyman 2013), Bradford → sRGB; Kanäle > 1 gemeinsam skalieren. |
| `uvvis_update.py` | Update-Prüfung: neuestes GitHub-Release (API), Versionsvergleich, Paketname je System. Automatisch max. 1×/Tag, im Selbsttest ohne Netz. |
| `uvvis_irms.py` | IR + MS: OPUS-Leser (Blockverzeichnis, T als Anteil → %), OPUS-PDF-Peaks, Peaksuche (Parabel, w/m/s/br), MS-Bericht (docx: Text + EMF-Beschriftungen, CDX-Objekt), Bruker-.d-Leser (BAF-Linienspektren, eigene Kalibrierung), `lc_found`, Ionenmassen, SI-Zeilen, `IRMSTab`. |
| `uvvis_xray.py` | X-Ray: eigener CIF-Leser (`Block`, Werte als Text), `Structure` (Zelle, U_kart, Symmetrie, geom-Tabellen), `Molecule` (Vervollständigung, Fehlordnung, Fragmente), `measure`, `project`/`pick` (ORTEP-Projektion), Tabellen-Markup (`runs` → HTML/Unicode/openpyxl), `XrayFigure`, `XrayMouse` (Drehen mit Blitting), `XrayTab`, `make_test_cif`. |
| `uvvis_style.py` | Erscheinungsbild: Fusion + eigene Palette (hell/dunkel/System, Menü Format), zentrales Stylesheet, Karten (`card`), SVG-Symbole (`icon`). Betrifft alle Tabs, nicht die Abbildungen. |
| `release_notes.py` | Release-Titel/-Notes für GitHub aus `CHANGELOG.md` + `CHANGELOG.de.md` (Release-Job in `build.yml`; fehlt die Version, scheitert das Release). |
| `uvvis_i18n.py` | Texte DE/EN; `T(_key, **kw)` (Parameter heißt `_key`, damit `key=` als Format-Argument geht). |
| `parseuv_lite/` | Vendorte parseuv-1.0.4-Version (BSD-3), angepasst. |

## Befehle
```bash
pip install -r requirements.txt                       # Python 3.12 (wie CI)
python uvvis_gui.py                                   # App starten
QT_QPA_PLATFORM=offscreen python uvvis_gui.py --selftest selftest_out   # MUSS vor jedem Commit „OK“ melden
python build.py                                       # PyInstaller-Build (braucht: pip install pyinstaller)
```
- Neue Funktion → eigener Abschnitt im `selftest()` (Muster: `report.append("…: OK")`).
- Der Selbsttest läuft in CI auch mit der **fertig gebauten** App auf allen drei Systemen.

## Release-Ablauf
1. `APP_VERSION` in `uvvis_gui.py` erhöhen.
2. `CHANGELOG.md` **und** `CHANGELOG.de.md` ergänzen; bei sichtbaren Änderungen `README.md` **und** `README.de.md`.
3. Selbsttest, commit, dann `git tag vX.Y.Z && git push && git push --tags` → GitHub Actions baut und erstellt
   das Release; Titel und Notes erzeugt `release_notes.py` aus den Changelogs (also beide Changelogs vollständig pflegen).

## Bekannte Fallen
- **Umbenennung (1.16):** Programm heißt Spectravolt, Repo `robinesken97/spectravolt`. Intern bleiben
  `uvvis_*.py` und `project.uvvis`. Alte Einstellungen (`QSettings("UVVisTool")`, `migrate_settings`) und der
  Datenordner `…/UVVisTool` (`app_data_dir`) werden beim ersten Start übernommen. Alte Versionen fragen die
  GitHub-API unter dem alten Repo-Namen ab (GitHub leitet um) – Repo nie neu unter altem Namen anlegen.
- **Windows-Zeilenenden:** CSVs in Tests mit `newline=""` schreiben; Reader überspringt leere Zeilen
  (früher Windows-CI-Abbruch durch `\r\r\n`).
- **AppImage (Linux):** in CI aus dem PyInstaller-Ordner gebaut; appimagetool und type2-Runtime mit fester
  Version und SHA-256 in `build.yml` – bei Updates beide Prüfsummen neu eintragen.
- **Windows-Konsole (cp1252):** Selbsttest-Meldungen nur mit ASCII/cp1252-Zeichen (kein λ, ε); die
  Ausgabe ersetzt sonst Zeichen, früher brach CI am `print` ab.
- **PyInstaller:** neue Imports, die nur lazy geladen werden, als `--hidden-import` in `build.py` eintragen.
- **MuPDF:** ignoriert SVG-Clip-Pfade → Kurven geometrisch clippen (`clip_polyline`); Rechtecke mit Breite 0
  fallen bei `|=` weg → Koordinaten-Union; Alpha ist premultipliziert → beim Einfärben un-premultiplizieren.
- **Label-Kollisionen:** gespeicherte Positionen von Labels, Inset und Bildern vor neuen Elementen reservieren.
- **Mausereignisse (matplotlib):** `LocationEvent` rundet x/y auf ganze Pixel; Messpunkte liegen in der Vorschau
  < 1 px auseinander. Tests mit simulierten Klicks/Hover nur auf ±1 Messpunkt prüfen und dann, dass die Anzeige
  genau den getroffenen Punkt zeigt (CI-Systeme treffen sonst unterschiedliche Nachbarn).
- **Undo:** während `set_state` greift `_restoring`; Änderungen über `QTimer` verzögert erfassen.
- **macOS-Version:** `build.py` liest `APP_VERSION` und schreibt sie nach dem Build in die `Info.plist`,
  danach `codesign --force --deep --sign -` (Signatur schließt die Info.plist ein).
- macOS-Build ist unsigniert (Gatekeeper: Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“).
  Trackpad-Zoom und HiDPI-Vorschau auf echter Mac-Hardware sind noch nicht verifiziert.
- **macOS Intel** (`macos-15-intel`-Runner): rdkit nur bis 2025.9.3, onnxruntime nur bis 1.23.2 als
  x86_64-Wheel (pip wählt sie automatisch); numpy/PySide6/opencv verlangen macOS 14. Der Runner ist
  befristet – fällt er weg, Intel-Build aus der Matrix nehmen.

## Offene Punkte
- X-Ray nur mit künstlicher CIF und einer Olex2-CIF ohne Fehlordnung/Symmetrieerzeugung geprüft; Polymere werden
  abgebrochen (`max_factor`). Stufe 3 (Vergleich mit DFT-Geometrie, ORCA-xyz) vorbereitet: `measure` arbeitet nur
  mit Atom-Schlüsseln (Label|Operation) und `param_label`; ein xyz-Molekül mit denselben Labels kann eine eigene
  Spalte liefern (Zuordnung der Atome noch offen).
- BSW-Datei mit Sprung in Spektrum 60 (CSV-Export zum Vergleich fehlt).
- Echte Gaussian-TD-DFT-Ausgabe noch nicht getestet (nur ORCA inkl. SOC).
