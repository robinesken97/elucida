# Characterization → Elucida: Daten selbst umwandeln

Für ein Skript (z. B. von Claude Code geschrieben), das eine Characterization-Datenbank in Elucida-Ordner umwandelt.
Elucida hat dafür **keinen** Import-Knopf. Stand: Elucida 2.4.

## Grundsatz: Elucida selbst laden lassen, `project.elucida` nie von Hand schreiben

`project.elucida` (YAML) ist ein internes Format. Viele Schlüssel gehören zu einzelnen Tabs, werden beim Laden einer
Datei aus ihr berechnet (Kern, Vorschub, Feldachse, Atome …) und können sich mit jeder Version ändern. Falsche oder
fehlende Schlüssel werden meist still ignoriert. Darum steuert das Skript Elucida **ohne Fenster** (`offscreen`) und
ruft dieselben Lade-Funktionen auf, die auch die Knöpfe benutzen. Vorlage dafür ist `elucida/app/demo.py`
(`load_data`, `open_demo`, `open_demo_publication`): so entsteht das Beispielprojekt.

Voraussetzungen: Elucida-Quellcode (dieses Repo, gleiche Version wie die installierte App), Python 3.12,
`pip install -r requirements.txt`, Umgebungsvariable `QT_QPA_PLATFORM=offscreen`. Liegt das Skript außerhalb des Repos:
`PYTHONPATH=<Repo-Wurzel>` setzen (sonst `ModuleNotFoundError: elucida`). Im Offscreen-Modus erscheinen keine
Dialoge; Fehler gehen nur über `w.log_signal` – das Skript muss sie mitschreiben.

## Ordner

```
<Projekt>/                     ein Characterization-Projekt bzw. Paper
    publication.elucida        PUB.create / PUB.add_compound
    <Verbindung>/              je Molekül, Ordnername = Name
        project.elucida        w.save_project()
        data/<Analytik>/ …     Kopien der Messdaten (macht Elucida)
        structures/ …          CDXML, Fotos
```

Elucida **kopiert** alle Dateien in den Verbindungsordner (Netzlaufwerk-Pfade sind danach nicht mehr nötig).
Die Characterization-Datenbank und die Originaldateien werden nur gelesen.

## Ablauf je Projekt

```python
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from PySide6.QtWidgets import QApplication
from elucida.app import main_window as MW, project as PRJ, publication as PUB

MW.SETTINGS_FILE = Path("convert_settings.ini")   # optional: Einstellungen/„Zuletzt geöffnet“ des Nutzers nicht ändern
app = QApplication.instance() or QApplication(sys.argv[:1])
w = MW.MainWindow()
log = []
w.log_signal.connect(log.append)

pub = Path("/Ziel/Mein Paper")
PUB.create(pub)
data = PUB.load(pub)
data.update(paper_title="…", authors="…", doi="…")       # Felder: PUB.FIELDS
PUB.save(pub, data)

for mol in molecules:                                  # aus der SQLite-Datenbank (nur lesen)
    cdir = pub / mol.name
    assert w.create_project(cdir)
    w.set_compound({"name": mol.name, "structure": cdxml, **MW.compound_from_structure(cdxml)})   # siehe „Verbindung“
    ...                                                 # Analytik, siehe Tabelle
    w.save_project()
    w._load_state_into_ui(PRJ.load(cdir))               # Zustand auf die Kopien im Projekt umstellen
    PUB.add_compound(pub, cdir)
    if mol.group:
        PUB.set_group(pub, cdir, mol.group)             # optional: Gruppe im Projekt (z. B. „Precursors“)
```

## Verbindung (`w.set_compound`)

Alle Felder optional, Text wie in der SI:

| Schlüssel | Inhalt |
|---|---|
| `name` | Name/Nummer (auch Ordnername und Exportname) |
| `structure` | Pfad zur CDXML (wird nach `structures/` kopiert) |
| `formula`, `mw` | Summenformel (ohne Leerzeichen), Molmasse (Zahl); mit CDXML über `MW.compound_from_structure(cdxml)` – `set_compound` berechnet sie **nicht** selbst |
| `mp` | Schmelzpunkt als Text, z. B. `"112–114 °C"` |
| `oil` | `True` = Öl („m.p. < 25 °C“) |
| `known`, `lit` | bekannte Verbindung + Literaturstelle (dann nur ¹H/¹³C Pflicht) |
| `sample`, `sample_no` | Substanz übrig + Probennummer (nur intern) |
| `note` | Notiz (nur intern, nie in der SI) |

## Analytik je Tab

| Daten | Aufruf | Hinweis |
|---|---|---|
| NMR-Spektrum (Mnova-SVG/-EMF) | `w.nmr_tab.load_svg(p)` | Kern aus der Achse |
| NMR-Rohdaten (TopSpin-Experiment oder Datensatz-Ordner) | `w.nmr_tab.import_topspin(p)` | ganzer Ordner, ordnet sich den Spektren zu |
| Mnova-Dokument | `w.nmr_tab.add_mnova_file(p)` | nur abgelegt |
| NMR-Zeile (Text des Mnova-Berichts) | `w.nmr_state["text"] = "1H NMR (…) δ …"` | |
| IR (OPUS `.0`, OPUS-PDF) | `w.irms_tab.load_ir(p)` | PDF nach dem Spektrum laden |
| Elementaranalyse | `w.irms_state["ea_found"] = {"C": "81.88", "H": "6.07", "N": "11.86"}` | |
| HRMS (Bericht `.docx` der Massenabteilung) | `w.hrms_tab.load_ms(p)` | |
| UV-Vis (Cary-CSV, DSW/BSW) | `w.open_csv(p, ask=False)` | Konzentrationen **nicht** raten – trägt der Nutzer in Elucida ein |
| CV (Gamry `.DTA`) | wie `CVTab.add_files`: `p = w.import_file(p, PRJ.data_sub("cv"))`, dann `w.cv_state.setdefault("files", []).append({"file": p, "uid": uuid.uuid4().hex[:8], "visible": True, "color": "#000000", "label": "100 mV/s"})` (Liste fehlt, solange der Tab nicht gebaut ist) | |
| X-Ray (CIF) | `w.xray_tab.load_cif(p)` | |
| DFT (xyz, ORCA-6-/Gaussian-Ausgabe, Cube, Molden) | `w.dft_tab.load_xyz(p)` | |
| Syntheseschema (CDXML/CDX) | `w.syn_tab.set_scheme(p)` | |
| Vorschrift | `w.syn_state["proc"] = "…"` | HTML erlaubt (`<b>`, `<sub>`, `<sup>`) |
| Fremde Abbildung (PDF/SVG/PNG) | `w.other_tab.load_files([p])` | |

Nicht abgedeckte Fälle (EPR, SEC, Overlay, Fluoreszenz): siehe `demo.py` `load_data`; im Zweifel weglassen und in
Elucida von Hand laden.

## Was nicht übernommen wird

- **SI-Absätze aus Characterization:** Elucida erzeugt die Charakterisierungszeile (m.p., IR, HR-MS, UV-Vis, EA) selbst
  aus den Tabs. Alte Absätze nicht in `note` schreiben; nur im Bericht des Skripts auflisten, damit der Nutzer vergleichen
  kann. Ausnahme: die Synthesevorschrift → `syn_state["proc"]`.
- **Status „vorhanden/fehlt“:** berechnet Elucida aus den geladenen Daten (Checkliste auf der Projektseite).

## Prüfen

Geprüft (Elucida 2.4, künstliche Daten): zwei Verbindungen mit Struktur, NMR, IR, EA, HRMS, UV-Vis, CV, X-Ray, DFT,
Vorschrift und Gruppe; nach dem Löschen der Quelldateien öffnen beide vollständig, alle Pfade liegen im Projekt.


1. Je Verbindung die Zeilen in `log` mit „Fehler“/„Error“ ausgeben; Dateien, die nicht geladen wurden, im Bericht nennen.
2. In Elucida das Projekt öffnen: Checkliste auf der Projektseite, je Verbindung die Tabs ansehen.
3. Zuerst mit 2–3 Molekülen testen, dann alle.
