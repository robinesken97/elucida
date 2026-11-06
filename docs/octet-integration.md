# Octet in Elucida

Octet-Snapshot: `f11487e97ee3970c1dc5678a5adbcd610144c04e`, Version 1.1.0,
Apache-2.0. Quellen, ursprüngliche Copyright-Hinweise und Lizenztexte stehen unter
`frontend/octet`. Das bestehende Elucida bleibt AGPL-3.0.

## Starten

Octet ist seit 2.6 Standard; `ELUCIDA_OCTET=0` schaltet es ab (Fehlersuche). Aus dem Quellcode: `python tools/build_octet.py`
(braucht Node.js, getestet 24) einmal ausführen; `tools/build.py` baut die Web-Assets mit. Fertige Apps brauchen kein Node.

## Was implementiert ist

- Octets React-Zeichner wird mit Qt WebEngine und einer schmalen QWebChannel-Brücke eingebettet.
  Der Editor erscheint rechts im Synthesetab und direkt neben den vertikal zentrierten
  Compound-Feldern. CDXML-Strukturen sind dort zugleich Vorschau und editierbare Zeichnung.
  Der Dialog startet mit 980 × 600 px, besitzt einen Größenanfasser unten rechts
  und merkt sich Größenänderungen. Octets Zoom ist verfügbar; das Formular ist scrollbar.
  Im Compound-Dialog speichert Autosave in eine temporäre Kopie; erst OK schreibt die
  Projektstruktur. Abbrechen lässt das Original unverändert. Bilddateien behalten ihre
  statische Vorschau. Formel und Molmasse aktualisieren sich aus der Zeichnung; die
  Pfade von Entwurf und Speicherereignis werden dafür einheitlich aufgelöst (macOS:
  `/var` und `/private/var`). Manuelle Korrekturen nach dem letzten Autosave bleiben bei OK erhalten.
  Der Hilfetext beschreibt diesen Workflow und steht zentriert; Statusmeldungen unter
  beiden Editoren sind jeweils auf die Breite ihrer Zeichenfläche zentriert.
  Seitenrahmen, Raster und Hilfslinien werden im Embedded-Modus ausgeblendet.
  Die Qt-Leiste bietet Strukturprüfung, Clean-up, Name-to-Structure und ein ⋯-Dateimenü.
  Zeichnungen werden nach einer Sekunde ohne Änderung automatisch gespeichert;
  die bisherigen Schaltflächen Übernehmen und Vergrößern entfallen.
  Octets Tastaturbehandlung und Zeichenwerkzeuge bleiben erhalten. Das Layout ist ein erster
  funktionaler Einbau. Die linke Spalte orientiert sich am Mockup: kompakter Titel,
  Vorschrift und Reagenzien direkt untereinander. Standardmäßig zeigt die Tabelle Name,
  mmol und Äquivalente; über ⋮ wird die Rolle geändert, über „Weitere Mengenfelder“
  werden Masse, Volumen, Konzentration und Molmasse eingeblendet. Die redundante
  ChemDraw-Dateikarte entfällt; ihre Aktionen stehen im ⋯-Menü des Schemas.
  Octets Werkzeugleiste rechts ist noch nicht pixelgenau wie im Mockup.
- Die Brücke akzeptiert Speichern und Clipboard, keine vom JavaScript gewählten Dateipfade.
  Assets laufen auf einem lokalen Loopback-Port. Netzwerkzugriffe auf andere Hosts sind gesperrt.
  Name-to-Structure nutzt die mitgelieferten Offline-Daten/OPSIN; PubChem-Onlinesuche ist nicht angebunden.
- Speichern erzeugt CDXML (inklusive Octet-Metadaten), CDX, SVG sowie eine kleine Reagenz-Metadatendatei.
  Vorversionen liegen in `structures/.editor-backups/`. Einzeldateien werden atomar ersetzt,
  CDXML zuletzt. Bei normalen Schreibfehlern werden bereits ersetzte Dateien zurückgesetzt.
  Ein Prozessabbruch zwischen Dateiersetzungen ist keine atomare Mehrdatei-Transaktion;
  hierfür bleibt die vollständige Vorversion in der Sicherung.
  Externe CDXML-Änderungen werden per SHA-256 erkannt und nicht überschrieben.
- Reagenztexte behalten ihre sichtbaren Äquivalente. „Aus Schema“ erkennt z. B. `NaBH4 (1,5 Äq.)`,
  `K2CO3 (1.2 eq.)` und `Pd(PPh3)4 (5 mol%)`. Chemische Klammern bleiben erhalten.
  Explizite Massen/Volumina/Stoffmengen haben Vorrang vor dem aus dem Label abgeleiteten Wert.
  Auch Octets eigene Stöchiometrietabelle verwendet die Äquivalente aus dem Label;
  explizite Eingaben in der Tabelle haben Vorrang. Dichte, Volumen und Konzentration
  sind im eingebetteten Modus sichtbar. „Übernehmen aus … → Octet-Tabelle“ kopiert
  bzw. aktualisiert die berechneten Werte ausdrücklich auf Nutzeraktion. Stabile
  Octets Spaltenschlüssel verhindern Duplikate bei wiederholter Übernahme derselben Tabelle;
  unabhängig angelegte Elucida-Zeilen bleiben
  erhalten. Keine automatische bidirektionale Synchronisierung.
  Der Import ist ausschließlich im Tabellenbereich erreichbar, nicht zusätzlich im ⋯-Menü.
- Neben dem globalen Hell/Dunkel-Schalter steht „Canvas dunkel“. Die Einstellung gilt
  für alle Diagrammflächen, Strukturvorschauen und Octet-Editoren, auch später geöffnete
  Tabs. Weiß wird zu reinem Schwarz (#000000), Farben und Moleküle werden für die
  Anzeige angepasst. Qt invertiert ausschließlich die gerenderte Darstellung; Octet
  verwendet einen schwarzen Bildschirmhintergrund mit angepasster Zeichenfarbe.
  Quelldaten, Matplotlib-Figuren und exportierte CDXML/CDX/SVG/PNG bleiben unverändert.
  Unter Format → Canvas lässt sich zusätzlich „App-Design folgen“ auswählen.
- Native Clipboard-Adapter für macOS (PyObjC) und Windows (Qt-Clipboardformate), mit CDX/CDXML,
  Octet-JSON, Molfile und SVG/PDF. ChemDraw-/Word-Interoperabilität muss auf beiden Systemen
  mit echten Anwendungen geprüft werden; Windows-EMF ist noch nicht implementiert.
- Die SI enthält ausschließlich die oberste Reaktionsgleichung: Auswahl über den
  obersten Reaktionspfeil und Octets zugehörige Reaktionserkennung. Zugehörige Bedingungen
  bleiben enthalten, Stöchiometrietabellen und untere Reaktionen werden ausgeschlossen.
  Das gilt für das Vorschaubild UND die eingebettete CDX, nicht nur einen Bildausschnitt.
  Ohne erkannte Reaktion wird mit Hinweis abgebrochen. Die vollständige Arbeitszeichnung
  bleibt in der normalen CDXML/CDX erhalten.
  Der bestehende SI-OLE-Export bleibt erhalten und verwendet die gefilterte CDX.
  Tiefgestellte Zahlen in zentrierten Pfeiltexten bekommen für SVG explizite, vom Browser
  gemessene Positionen: MuPDF verschob zuvor verschachtelte `tspan`-Elemente. Außerdem
  berücksichtigt die Darstellungsmemoisierung jetzt den temporären Exportausschnitt.
  Metadatenversion 3 erzwingt beim nächsten SI-Export die Erneuerung alter Vorschaubilder.
  Ein kleiner Rand verhindert abgeschnittene Linien/Glyphen am Bildrand.
  Der Test prüft zusätzlich zum CDX-Payload die tatsächlich gerenderte SVG-Vorschau.
- **Word auf macOS:** ChemDraw unterstützt laut Hersteller die Bearbeitung per Doppelklick
  nur unter Windows ([Revvity, S. 7](https://revvitysignals.com/sites/default/files/2024-11/rs-e-book-every-chemist-can-draw-with-chemdraw%20-%20.pdf)).
  Deshalb erzeugt jeder Word-Export mit ChemDraw-Objekten zusätzlich den Ordner
  `<Word-Dateiname>_structures` mit `drawing_001.cdx`, gegebenenfalls `drawing_001.cdxml`
  usw., in Dokumentreihenfolge. Die Dateien enthalten genau die exportierten Reaktionen;
  der CDX-Inhalt ist identisch zur OLE-Einbettung. Der Ordner bleibt bei Projekt- und
  Schnellexporten neben der DOCX. Auf dem Mac direkt in ChemDraw öffnen, bearbeiten
  und zurück nach Word kopieren. Die Begleitdateien sind Momentaufnahmen und aktualisieren
  Word/Elucida nicht automatisch. README listet die Dateien des aktuellen Exports;
  alte zusätzliche bzw. fremde Dateien werden im Ordner nicht gelöscht.
- IR: „Linienbreite“ ist unter den IR-Einstellungen frei numerisch einstellbar
  (0,05–20 pt) und wird im Projekt gespeichert. Dieselbe Breite gilt in Vorschau und
  Export. Die dreieckigen Peakmarker entfallen; Peakwerte und Beschriftungen bleiben.
- DFT-Energieprofil: neue Strukturspalte je Plateau mit Dateiimport, Zeichnen/Bearbeiten
  im Octet-Fenster und Entfernen der Zuordnung. Zugeordnete Moleküle stehen über dem
  Plateau und erscheinen in PDF/SVG/PNG/SI; PDF/SVG verwenden den bestehenden Vektorexport.
  Die Zeichnung wird explizit zugeordnet, nicht aus der 3D-Rechnung geraten. Energien
  und Rechenmethoden bleiben unverändert. Zuordnungen sind Teil des Projektzustands
  und werden bei Projektkopien mitgenommen. Der separate Zeichner speichert automatisch;
  „Schließen“ beendet die Bearbeitung, es gibt dort keinen Entwurfs-/Abbrechenmodus.
  Energieprofil und NICS verwenden nun CanvasHost: nach Neuzeichnen und Größenwechsel
  stimmen Qt-Pixelmaße und Matplotlib-Renderer einschließlich HiDPI überein.

### Compound-Fehler: Ursache und Korrektur am 4. November

Der normale `.command`-Start übernahm nach QApplication die deutsche numerische
Locale. RDKit las die CDXML-Koordinaten mit Dezimalpunkten dann falsch; die Vorschau
warf `Cannot normalize a zero length vector`. `compound_from_structure` verwarf
wegen dieser Ausnahme auch die bereits berechneten Eigenschaften. Nachweis: dieselbe
lokale Datei scheiterte mit `de_DE.UTF-8`, funktionierte aber mit `LC_NUMERIC=C`.
`MainWindow` setzt deshalb vor dem Laden/Starten von Workern die native numerische
Locale auf C (Qt-Empfehlung); Qt-Lokalisierung und Komma-Eingaben bleiben erhalten.
`CHEM.load_cdxml(render=False)` liefert außerdem Eigenschaften ohne Vorschau und
verwendet einen getrennten Cache-Schlüssel. Fehler werden im Teststarter lokal unter
`.octet-preview/drawing-diagnostics.log` protokolliert, ohne Zeichnungsinhalte.

Geprüft: echte Launcher-Projektkopie, modaler Dialog, vorhandene Struktur, Löschen,
Neuzeichnen, OK, Speichern und erneutes Öffnen. Ein dauerhafter Test verwendet dafür
nur synthetische Daten (`tools/test_compound_launcher.py`). Der Nutzer bestätigte
anschließend, dass die Werte im normalen `.command`-Ablauf wieder erscheinen.
Der frühere Pfadfix und die synchrone Speicherbenachrichtigung bleiben erhalten;
manuelle Korrekturen nach Autosave dürfen nicht durch OK überschrieben werden.

### Octet aktualisieren

Der Stand 1.1.0 ist lokal integriert, fest auf den oben genannten Commit gepinnt.
`tools/update_octet.py` führt einen Dreiwegevergleich aus: bisheriger Upstream,
lokale Elucida-Dateien, neuer Upstream. Es schreibt **nur einen neuen Staging-Ordner**
und daneben einen Mergebericht; weder Arbeitskopie noch Nutzerprojekte werden geändert.
Es lädt keine Updates automatisch herunter und startet keine Builds selbst.
Beispiel (aus dem Repository, mit vorhandenem vollständigen Octet-Git-Klon):

```text
.venv/bin/python tools/update_octet.py --upstream /ABS/PFAD/Octet-Draw --ref GEPRUEFTER_COMMIT --output /ABS/PFAD/octet-staging
```

Konflikte im Staging auflösen, Diff zum neuen Upstream prüfen und anschließend die
geprüften Quelldateien nach `frontend/octet` übernehmen. Vorher den bisherigen
Quellstand sichern; `node_modules` nicht auswechseln. Danach `tools/build_octet.py`
für reproduzierbare Abhängigkeiten, Build und Lizenzkopien ausführen, anschließend
`npm run test:embed --prefix frontend/octet` und die GUI-Tests unten. `UPSTREAM.md`
und diese Notizen aktualisieren. Ohne Konflikte sind trotzdem Funktionstests nötig.
Beim Update 1.0.29 → 1.1.0 waren Editor.tsx und export.ts manuell abzugleichen.
Ein Rollback des Quellstands ist kein automatisches Downgrade bereits gespeicherter
Zeichnungen; daher neue Stände zunächst mit Projektkopien testen.

1.1 enthält die Upstream-Korrekturen am Zeichnen, Clean-up, Name → Struktur und
chemischen Warnungen. Tauri-native Änderungen (z. B. Windows-EMF-Zwischenablage)
werden nicht automatisch in den Qt-Host übertragen. Der eingebettete Cursor verwendet
ein 24-Pixel-Bitmap statt der doppelt skalierten Retina-Variante. Der Nutzer bestätigte
die normale Cursorgröße. Die Exportfarben bleiben unabhängig von der Canvasansicht.

## Grenzen

Die Zeichen-Engine enthält noch Upstream-Analysecode
und den NMR-Datensatz; die Analysebefehle sind im Embedded-Modus deaktiviert und aus dem
kontextbezogenen Aktionsmenü gefiltert. Vollständiges Entfernen der ungenutzten UI/Daten und
einheitliche deutsche Beschriftungen stehen aus.

Die Zeichnung besitzt ihren eigenen Octet-Undo-Verlauf. Elucidas Projekt-Undo stellt keine
historischen Versionen der extern gespeicherten Zeichnungsdatei wieder her. Bei einem
externen Dateikonflikt bleibt der Editor offen; ⋯ → Als CDXML/CDX exportieren sichert eine
separate Kopie, ohne zuerst das widersprüchliche Original überschreiben zu müssen.
Meldet Octet beim Import nicht unterstützte Inhalte, wird das Überschreiben des Originals
ebenfalls gesperrt; die separate Kopie bleibt möglich. Autosave-Fehler erscheinen im Editorstatus;
bei einem anschließenden expliziten Speicherversuch zusätzlich als Dialog.

Manuell prüfen (zunächst nur das künstliche Testprojekt):

1. Zeichnen, Texte mit Äquivalenten ergänzen, Strukturprüfung und Clean-up ausführen.
2. Name-to-Structure mit einem einfachen Namen testen; Copy/Paste nach und aus ChemDraw.
3. Autosave, Compound-Dialog, Projektwechsel und erneutes Öffnen testen; Canvas-Schalter
   in allen Tabs prüfen und Exporte mit hellem/dunklem Bildschirm vergleichen.
4. „Übernehmen aus …“ für Schema und Octet-Tabelle aufrufen; Referenzstoffmenge,
   Äquivalente, Dichte/Volumen und wiederholtes Aktualisieren prüfen.
5. SI nach Word exportieren. Unter Windows OLE-Objekt doppelklicken, ändern, speichern
   und erneut öffnen. Unter macOS CDX/CDXML aus dem Begleitordner in ChemDraw öffnen,
   ändern und nach Word kopieren; keine OLE-Aktivierung auf macOS erwarten.
6. Stereochemie, Abkürzungen, Pfeile und Textformatierung mit repräsentativen Zeichnungen vergleichen.

## Automatisierte Prüfungen

```text
python -m unittest discover -s tests -v
npm run test:embed --prefix frontend/octet
npm run build:embed --prefix frontend/octet
python Elucida.py --selftest selftest_octet
python tools/test_drawing_host.py
python tools/test_drawing_features.py
python tools/test_compound_drawing.py
python tools/test_compound_new_drawing.py
LANG=de_DE.UTF-8 python tools/test_compound_launcher.py
python tools/test_dft_profile.py
QT_QPA_PLATFORM=offscreen python tools/test_canvas_theme.py
python tools/run_octet_preview.py --smoke-keys
```

Die WebEngine-Tests brauchen eine GUI und einen lokalen TCP-Port. Sie erzeugen ausschließlich künstliche
Daten und haben Zeitlimits. Ohne GUI kann der normale App-Selbsttest mit
`QT_QPA_PLATFORM=offscreen` laufen; damit wird die eingebettete Oberfläche nicht geprüft.

## Prüfstand

Prüfergebnisse dieses Arbeitsstands:
- TypeScript-Prüfung und Vite-Frontend-Build: bestanden.
- Zehn Python-Integrationstests: bestanden (inklusive bearbeitbarer Word-Begleitdateien
  und deren Übernahme in Projekt-/Schnellexportordner).
- Vollständiger Elucida-Selbsttest: `selftest_octet_final_nov4/selftest_report.txt`
  endet mit `OK`, inklusive IR-Linienbreite in Vorschau/Export und fehlender Dreiecksmarker.
  Frühere Wiederholung in einem bereits benutzten Ausgabeordner scheiterte am bestehenden
  TopSpin-Testverzeichnis; für Wiederholungen einen frischen Ausgabeordner verwenden.
- Nach der DFT-Erweiterung: `selftest_octet_dft_nov4/selftest_report.txt` endet mit `OK`.
  Plateau-Zuordnung, unveränderte Energien, Projektkopie, PDF/SVG/PNG/SI und Größenwechsel
  wurden zusätzlich mit `tools/test_dft_profile.py` geprüft. Auch Zeichnen eines neuen
  Benzols direkt aus einer Plateau-Zeile und anschließendes Schließen wurden ausgeführt.
- Upstream `node src/cdx.check.ts`: bestanden.
- GUI-Roundtrip mit echter Qt-WebEngine auf diesem Mac: bestanden (CDXML/CDX/SVG,
  identischer CDX-Inhalt nach erneutem Laden mit demselben Dokumentnamen).
- Vollständiges Elucida-Fenster über `tools/run_octet_preview.py --smoke`: gestartet,
  eingebettete Synthesezeichnung gespeichert, gefilterten SI-CDX-Payload geprüft und Screenshot erzeugt.
- GUI-Funktionstest mit zwei künstlichen Reaktionen und einer Stöchiometrietabelle:
  nur obere Reaktion in SI, Äquivalente aus Beschriftung, Dichte/Volumen, Tabellenkopie,
  Autosave und identische Exportdaten bei hellem/dunklem Canvas geprüft.
- Anzeigeeffekt für Matplotlib und Bildvorschauen: schwarzer Pixel #000000,
  unverändertes Quellbild und bytegleicher PNG-Export geprüft.
- Compound-GUI: sichtbarer direkter Editor, Formel/Molmasse nach Laden und Autosave,
  Entwurfs-Autosave, Cancel erhält Original,
  OK publiziert CDXML/CDX und erhält nachträgliche manuelle Molmassenkorrekturen.
  macOS-Titel bleibt nach Titeländerung ausgeblendet.
- Native ChemDraw 23.1.2 auf macOS: künstliche CDX und CDXML aus dem neuen Word-
  Begleitordner erfolgreich geöffnet und visuell geprüft, einschließlich tiefgestellter
  Pfeilbeschriftung. Das prüft keinen Word-OLE-Roundtrip und keine Windows-Installation.
- Projektimport und Speichern unter neuem Projekt nehmen CDX, EMF und Octet-Metadaten mit.
  Home/Projektwechsel/Verschieben/Löschen brechen bei einem Zeichnungsspeicherfehler ab.
- GUI: Hilfslinien ausgeblendet, separate Exportkopie trotz externem Konflikt möglich,
  nicht vollständig unterstützte Originaldatei gegen Überschreiben geschützt.
- Bei einem Compound-Testlauf erreichte WebEngine einmal das Ladezeitlimit (macOS-
  Prozessmeldungen im Log); der isolierte Wiederholungslauf und der anschließende
  kompakte Dialogtest bestanden. Ursache nicht abschließend geklärt; Start/Lebenszyklus
  bei der unabhängigen Prüfung mit mehreren geöffneten Editoren berücksichtigen.
- Die vollständige Upstream-Testsammlung enthält zusätzlich Tauri-/Release-Prüfungen, deren
  Quelldateien nicht mitgeliefert sind (erster Lauf: 83/90). Der dabei gefundene Node-Importfehler
  in export.ts ist behoben; dessen Test besteht jetzt. Für diesen Snapshot `test:embed` nutzen.
- Zwei reproduzierte WebEngine-Probleme sind behoben: Mac-Roman-TextDecoder blockierte den
  CDX-Export; eine feste Zeichentabelle ersetzt ihn. Globale Python-Eventfilter verursachten
  unter PySide 6.12/macOS einen nativen Absturz; im Embedded-Modus wird der Mausradfilter
  in `style.py` deshalb nur an Formularfeldern angebracht. Diese Anpassung mitprüfen.

### Tastaturfokus im Zeicheneditor

Beim Betreten der Zeichenfläche übernimmt WebEngine den Fokus von Navigationsknöpfen;
ein aktives Text-/Zahlenfeld behält ihn. So betätigt die Leertaste nicht versehentlich
„Übersicht“. Solange der Fokus im Editor liegt, setzt `DrawingShortcutScope` die
Tastenkombinationen der umgebenden Qt-Aktionen vorübergehend aus (die Menüaktionen
bleiben anklickbar). Beim Verlassen werden sie wiederhergestellt. Octets Tastaturtabelle
bleibt unverändert. Keine globalen Python-Eventfilter auf WebEngine-internen Objekten.

Geprüft mit `python tools/run_octet_preview.py --smoke-keys` in einem temporären Projekt:
Leertaste aktiviert Octets Auswahlwerkzeug; das kollidierende Übersicht-Kürzel bleibt
im Editor; Vorschrift-Fokus bleibt beim Überfahren erhalten; Host-Kürzel kehren außerhalb
zurück. Der Test liefert den Qt-Enter-Event explizit, weil macOS native Cursorbewegungen
in nicht aktivierten Testfenstern zusammenfassen kann. Upstream `keys.check.ts` besteht.

Prüfung des 1.1-Stands: 93/93 verfügbare Zeichnerchecks bestanden, sieben Checks der
separaten Tauri-App/Release-Infrastruktur sind ausdrücklich ausgeschlossen. 11 Python-
Grenztests bestanden, ebenso der echte SI-/Stöchiometrie-/Farben-/Autosave-Test.
Windows wurde in dieser Sitzung nicht ausgeführt.

Abschlussprüfung am 4. November: vollständiger App-Selbsttest in
`selftest_octet_1_1_locale/selftest_report.txt` endet mit OK. Der dauerhafte deutsche
Launcher-Test und `--smoke-keys` bestanden (einschließlich integriertem Speichern/SI).
Der Updatehelfer wurde zusätzlich gegen denselben Commit ausgeführt: alle lokalen
Integrationsdateien bleiben bytegenau erhalten, keine Konflikte. Anschließend wird der
geprüfte Stand als lokaler Commit mit dem oben genannten Checkpoint-Tag gesichert; kein Push.
