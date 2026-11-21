[English](manual.en.md) | **Deutsch** · [Übersicht](../README.de.md)

# Elucida-Handbuch

## Herunterladen und starten

Lade unter **Releases** (rechts auf der Repository-Seite) die Datei für dein System herunter und entpacke sie.

| System | Datei | Starten |
|---|---|---|
| Windows | `Elucida-windows-x64.zip` | `Elucida\Elucida.exe` |
| macOS (Apple Silicon) | `Elucida-macos-arm64.zip` | `Elucida.app` |
| macOS (Intel, ab macOS 14) | `Elucida-macos-x64.zip` | `Elucida.app` |
| Linux (AppImage) | `Elucida-linux-x64.AppImage` | ausführbar machen, dann doppelklicken |
| Linux (Ordner) | `Elucida-linux-x64.tar.gz` | `Elucida/Elucida` |

Die App ist nicht signiert, deshalb warnt das Betriebssystem beim ersten Start:

- **Windows (SmartScreen):** „Weitere Informationen“ → „Trotzdem ausführen“.
- **macOS (Gatekeeper):** `Elucida.app` in „Programme“ ziehen und einmal doppelklicken (wird blockiert).
  Dann Systemeinstellungen → Datenschutz & Sicherheit → ganz unten „Dennoch öffnen“ → mit Passwort/Touch ID
  bestätigen. Ab macOS 15 funktioniert der frühere Weg „Rechtsklick → Öffnen“ nicht mehr. Alternativ im
  Terminal: `xattr -dr com.apple.quarantine /Applications/Elucida.app`. Welcher Mac? Apple-Menü → Über diesen Mac: „Chip Apple M…“ = Apple Silicon,
  „Prozessor Intel…“ = Intel. Die Intel-Version braucht macOS 14 (Sonoma) oder neuer.

**Updates:** Beim Start prüft das Programm einmal am Tag, ob es auf GitHub eine neuere Version gibt,
und bietet an, die Release-Seite zu öffnen (Hilfe → „Nach Updates suchen…“; im Hilfe-Menü abschaltbar).
Zum Aktualisieren die neue Datei herunterladen und die alte App ersetzen; Verbindungen, Projekte und Einstellungen
bleiben erhalten.

**Linux-AppImage:** `chmod +x Elucida-linux-x64.AppImage` (oder Dateieigenschaften → „Als Programm
ausführen“), dann starten. Es braucht `fusermount` (Paket `fuse3`, bei den meisten aktuellen
Distributionen vorinstalliert); ohne startet man mit `./Elucida-linux-x64.AppImage --appimage-extract-and-run`.
Wie beim tar.gz ist eine Distribution mindestens so neu wie Ubuntu 22.04 (glibc 2.35) nötig.

Unter Windows immer den ganzen Ordner `Elucida` zusammenlassen. Die `.exe` funktioniert nicht ohne den Ordner `_internal` daneben.

*Elucida hieß früher **Spectravolt** (davor **UVVisTool**, als es nur UV-Vis-Verdünnungsreihen auswertete).
Verbindungen, Einstellungen und heruntergeladene Daten werden automatisch übernommen. Versionen vor 1.0 (gezählt bis
2.7.1) bieten 1.0 nicht als Update an: einmal von Hand herunterladen.*

## Schnellstart: von der leeren Verbindung zur SI

Elucida kennt zwei Ebenen: Eine **Verbindung** ist ein Ordner mit allen Daten einer Verbindung, ein **Projekt** fasst
die Verbindungen einer Veröffentlichung zusammen (Gesamt-SI, Datensatz; siehe den nächsten Schnellstart). Jede
Verbindung gehört zu einem Projekt: Sie liegt in dessen Ordner.

1. **Verbindung anlegen:** **Neu → Neue Verbindung** auf dem Startbildschirm (oder **Datei → Neue Verbindung…**) fragt erst
   nach dem Projekt (zuletzt geöffnetes, anderes oder neues), dann nach dem Namen; in einem Projekt **Neue Verbindung**
   auf dessen Seite. Alle Dateien, die du lädst, werden hineinkopiert, gespeichert wird automatisch.
2. **Verbindung festlegen:** der Tab **Verbindung** ganz links (eine neue Verbindung öffnet dort): die Nummer, die sie
   in der SI trägt (z. B. 3a), und die Struktur – rechts zeichnen oder mit **Wählen…** eine ChemDraw-Datei (CDXML)
   laden. Summenformel und Molmasse kommen daraus, alles gilt sofort (kein OK). Alle Tabs und die SI folgen dieser
   Verbindung; Nummer und Summenformel stehen am Tab. Lieber in ChemDraw zeichnen? Menü **…** über der Zeichnung →
   **In ChemDraw bearbeiten** öffnet die leere Datei, die jede Verbindung schon hat – speichern, und Elucida übernimmt
   Struktur, Summenformel und Molmasse von selbst (genauso das Reaktionsschema im Synthese-Tab).
3. **Daten laden:** Dateien einfach ins Fenster ziehen – Elucida legt sie in den passenden Tab:
   CIF → **X-Ray**, SVG aus MestReNova → **NMR**, xyz/ORCA/Gaussian/Molden/Cube → **DFT**, MS-Bericht (.docx) oder Bruker-.d →
   **HRMS**, OPUS-Datei → **IR + EA**, UV-Vis-Messdaten (CSV, DSW/BSW) → **UV-Vis (ε)**. CV, SEC, EPR, TD-DFT und
   Fluoreszenz lädst du im Tab über **Dateien hinzufügen…**. Ein leerer Tab zeigt, was er braucht und woher es kommt.
4. **Auswerten:** Links stehen die Einstellungen in Schritten (meist **Daten · Auswertung · Darstellung**; ein Punkt
   am Schritt zeigt, wo etwas vom Standard abweicht), rechts die Abbildung mit den Reitern **Ergebnisse** und
   **SI-Text**. Labels, Strukturen und Insets lassen sich mit der Maus verschieben.
   **Strg+Z** / **⌘Z** macht alles rückgängig.
5. **Exportieren:** Im letzten Tab **Export** (Gruppe „Ausgabe“) wählst du die Formate für alle Abbildungen
   (PDF/SVG/PNG/PPTX, 16 × 11 cm für eine halbe A4-Seite); **Exportieren** je Zeile (eine Zeile je Abbildung bzw.
   Bericht) schreibt genau diese Dateien mit ihren Daten in den Ordner der Verbindung (`figures/`, `tables/`, `SI/`), **Alles exportieren**
   alle auf einmal. **Strg+E** exportiert im offenen Tab dessen Abbildung. **Bearbeiten → Abbildung kopieren (SVG)**
   (**Strg+Umschalt+C** / **⌘⇧C**) legt die Abbildung der rechts sichtbaren Seite genau wie im Export als SVG mit
   PNG-Ersatz in die Zwischenablage (macOS zusätzlich als PDF), z. B. für PowerPoint; auf Seiten ohne Abbildung
   (Tabellen, SI-Text) und für ein zurückgehaltenes NMR-Spektrum kommt nur ein Hinweis. NMR kopiert den Bereich aus dem
   Feld, nicht den Zoom der Vorschau.
6. **SI erstellen:** **Datei → SI-Abschnitt exportieren (Word) …** sammelt alles Fertige in einer Word-Datei: Synthese,
   Charakterisierungsabsatz (m.p., NMR, IR, HR-MS, UV-Vis, Elementaranalyse), Abbildungen zu zweit je Seite,
   Kristalldaten und DFT-Koordinaten. Was noch fehlt, zählt das Programm danach auf.

## Schnellstart: Projekt mit mehreren Verbindungen

1. **Projekt anlegen:** **Neu → Neues Projekt** auf dem Startbildschirm (oder **Datei → Neues Projekt…**) und einen
   Ordner wählen – leer oder einer, in dem schon Verbindungen liegen (die werden automatisch aufgenommen).
2. **Angaben ausfüllen:** Seite **Angaben** (neben Verbindungen und Computerchemie; jedes Feld gilt beim Verlassen) – Titel des Artikels (Titelblatt der SI; kursiv mit `<i>…</i>`), Autoren,
   Adresse, DOI des Datensatzes, zugehörige Publikation, Beschreibungen, Lizenz. Sie landen in `README.txt` des
   Datensatzes und auf dem Titelblatt.
3. **Verbindungen anlegen:** **Neue Verbindung** legt einen Unterordner an (Name = Verbindung, z. B.
   `3b`); ein Klick auf eine Verbindung öffnet sie, gearbeitet wird wie im Schnellstart oben. Der Pfad oben in der
   Werkzeugleiste, **Übersicht › <Projekt> › <Verbindung> ▾**, führt zurück zum Projekt oder zur Übersicht und wechselt
   direkt zu einer anderen Verbindung des Projekts (auch Datei → Zum Projekt, Strg+Umschalt+P; Datei → Zur Übersicht,
   Strg+Umschalt+H). **Neue Gruppe …** gliedert die Verbindungen (z. B.
   Precursor, Salze, NHOs; Rechtsklick auf eine Verbindung → Gruppe, oder in eine Gruppe ziehen); in der Gesamt-SI werden
   die Gruppen zu Unterkapiteln von Synthese und NMR (2.1, 2.2 …). Zeilen ziehen oder **Nach Name sortieren** ändert die
   Reihenfolge – sie gilt für SI und Datensatz. Das Suchfeld oben
   auf dem Startbildschirm findet Verbindungen in allen deinen Projekten (Name/Nummer, Laborkürzel wie AB-1-234,
   Summenformel, Notiz); Strg+F springt dorthin. Jede Verbindung zeigt eine **Checkliste**: Pflicht sind ¹H,
   ¹³C, 2D-NMR, HRMS, IR und m.p.; für im Tab Verbindung als **literaturbekannt** markierte Verbindungen (mit Literatur)
   nur ¹H und ¹³C. **Öl** neben dem Schmelzpunkt ergibt „m.p. <25 °C“.
4. **SI-Texte:** **SI-Texte …** – „Materials and Methods“ (oder die in den Tabs hinterlegten Aufbau-Texte übernehmen) und
   je Kapitel eine optionale Einleitung.
5. **Gesamt-SI:** Im Reiter **Export** der Projektseite wählst du in der Karte **Gesamt-SI (Word)** Vorlage (Gruppe,
   Wiley, ACS, RSC, Nature), Kapitel und Verbindungen; **Gesamt-SI (Word)** oben (blau) oder **Word-Datei schreiben** in
   der Karte legt die Datei in `SI/` des Projekts. Welche Abbildungen einer Verbindung hineinkommen, bestimmt die Spalte
   **SI** in deren Tab **Export**.
6. **Datensatz:** Karte **Datensätze (Zip)** im selben Reiter (Verbindungen, Datenarten, Laborkürzel, Zielordner) –
   **Datensätze schreiben** bzw. **Datenpakete (Zip)** oben: je Verbindung ein Zip, `CompChem.zip`, `README.txt` und Lizenztext in
   `datapack/`, fertig zum Hochladen (z. B. TUDOdata).

Zum Ausprobieren: **Hilfe → Beispielprojekt ansehen** legt ein Projekt mit zwei erfundenen Verbindungen an: eine Vorstufe mit der üblichen Charakterisierung und ihr Produkt mit Daten für alle Tabs, die zueinander passen.

## Anleitungen

Schritt für Schritt durch einen Arbeitsablauf, mit Bildern:

- [Synthese und Charakterisierung bis zur SI](anleitungen/synthese-bis-si.de.md) – Schema, Vorschrift, NMR, IR,
  HRMS, Elementaranalyse, SI-Abschnitt
- [UV-Vis: ε aus einer Verdünnungsreihe](anleitungen/uvvis-epsilon.de.md)
- [Elektrochemie: CV, SEC und H-Zelle](anleitungen/elektrochemie.de.md)
- [EPR: Spektren, Simulation und Fit](anleitungen/epr.de.md)
- [Kristallstruktur und DFT](anleitungen/struktur-dft.de.md)

Zum Ausprobieren ohne eigene Daten: **Hilfe → Beispielverbindung ansehen** legt eine Verbindung mit künstlichen Daten für
alle Tabs an. **Hilfe → Anleitung zu diesem Tab** (F1) öffnet den passenden Abschnitt unten.

Alle Einstellungen der einzelnen Tabs stehen weiter unten zum Nachschlagen.

## Verbindungen, Projekte, Export

Alles passiert im **Ordner der Verbindung** (der Ordner-Knopf in der Werkzeugleiste öffnet ihn im Finder, Explorer bzw.
im Dateimanager des Linux-Desktops):

1. **Datei → Neue Verbindung…** – Projekt wählen, dann den Namen; die Verbindung wird ein Unterordner des Projekts.
   Für eine einzelne Auswertung ohne Projekt: **Neu → Schnellauswertung** auf dem Startbildschirm (internes Projekt
   „Einzelauswertungen“, Exporte fragen nach dem Zielordner; später verschieben).
2. Messdaten, Strukturen, Fotos und TD-DFT-Dateien von beliebigen Orten laden – sie werden **in die
   Verbindung kopiert** (`data/<Analytik>/`, `structures/`; ChemDraw-Exporte mit gleichem Namen wie eine CDXML kommen
   mit). Dateien, die schon in der Verbindung liegen, werden nicht erneut kopiert.
3. Normal arbeiten – die Verbindung wird **automatisch gespeichert**. Beim Öffnen wird jeweils eine Sicherung angelegt
   (`.elucida/project.elucida.bak`). Ordner älterer Versionen (`project.uvvis`) öffnen wie bisher und werden ab dann als
   `project.elucida` gespeichert (der Dateiname bleibt aus Gründen der Verträglichkeit „project“).
4. **Exportieren** (Tab **Export** bzw. **Strg+E** im Tab) schreibt direkt in die Verbindung (vorhandene Dateien werden überschrieben):

```
S2/
  project.elucida        Einstellungen (Pfade relativ zum Ordner)
  SI/                    Word-Dateien und SI-Texte: S2_SI.docx, S2_NMR.docx, S2_UV-Vis_methods.txt …
  figures/               Abbildungen (PDF/SVG/PNG): S2_CV.pdf, S2_X-ray.svg, <Serie>_UV-Vis.png …
  tables/                Tabellen und Datendateien: S2_CV_results.csv, S2_DFT_tables.xlsx, <Serie>_UV-Vis_report.xlsx, xyz …
  data/nmr/ data/cv/ …   Kopien der Messdaten, ein Ordner je Analytik
  structures/            ChemDraw-Strukturen (mit ihren Exporten), Schemata, Fotos
  .elucida/              Zwischenbilder für Word, Cache, Sicherung (versteckt)
```

Dateinamen beginnen mit dem Namen der Verbindung (Tab **Verbindung**; ohne sie der Ordnername). Ordner entstehen erst,
wenn etwas hineinkommt. Ordner aus Versionen vor 2.1 (`data/`, `images/`, `exports/`) öffnen wie bisher; ihre
Dateien bleiben liegen, neue Dateien und Exporte kommen in den neuen Aufbau.

Das Programm startet mit dem Startbildschirm. Verbindungen und Projekte öffnen über **Datei → Öffnen**, **Zuletzt
geöffnet** oder indem man den Ordner ins Fenster zieht. **Datei → Verbindung als Kopie speichern** legt
eine vollständige Kopie an (z. B. als Zwischenstand). **Bearbeiten → Rückgängig / Wiederholen**
(⌘Z / ⌘⇧Z, Strg+Z / Strg+Y) gilt für alle Tabs.

**Nichts wechselt von selbst:** Die Ansicht ändert sich nur auf einen Klick, der sein Ziel nennt. Dateien, die du ins
Fenster ziehst, kommen in ihren Tab (CIF → X-Ray, Messdaten → UV-Vis (ε) bzw. auf dem Tab UV-Vis-Kinetik dorthin), du
bleibst aber im offenen Tab: Eine Einblendung unten rechts nennt den Ziel-Tab mit **Anzeigen**, und der Tab-Knopf trägt
einen blauen Punkt, bis du ihn öffnest (orange am Schritt heißt dagegen: weicht vom Standard ab). Auf dem Tab Fluoreszenz wählst du Absorption bzw. Emission in der Karte Daten. Ändert
eine Karte links eine Seite rechts, die gerade nicht offen ist (z. B. NICS-Abbildung, Lebensdauer, Hyperfein), nennt die
Karte den Reiter, und der Reiter bekommt einen Punkt bis zum Ansehen. In den Tabs einer Verbindung behalten
Standardwerte, Vorlagen, Rückgängig, Sprache und Design den offenen Reiter rechts und die Bildlaufposition links (im
Vergleich noch nicht). **Strg+F** in einer Verbindung zeigt den Filter
ihres Projekts.

**Startbildschirm:** Links stehen die Filter (Alle Verbindungen, Zuletzt, Unvollständig, Substanz übrig) und deine Projekte mit
Fortschritt, rechts die Verbindungen als **Galerie** oder **Liste**. Die Galerie zeigt, welche Pflichtteile noch fehlen; Liste und
Projektseite zeigen sie als Tabelle. Tabs mit Daten sind hell, leere gedimmt.

**Datei → Datenpaket (Zip) exportieren** schreibt die Rohdaten der Verbindung für ein Datenrepositorium (z. B.
TUDOdata), aufgebaut wie veröffentlichte Datensätze: `3b.zip` mit `3b/NMR/1H/10/` (TopSpin-Experimente vollständig),
`NMR/HSQC + HMBC/12/`, `IR/`, `MS/` (Bericht, Bruker-.d), `UV-Vis/`, `Fluorescence/`, `CV/<Lösungsmittel>/`, `SEC/`,
`EPR/`; DFT und die eigenen Abbildungen/SI wahlweise. X-Ray (CCDC) und Synthese gehören nicht hinein. Jede Datei ist
abwählbar, die Auswahl wird je Verbindung gemerkt. **Laborkürzel** wie `AB-1-234` werden automatisch gefunden und ersetzt –
in Datei- und Ordnernamen durch die Verbindung (`3b`), im Inhalt durch „Compound 3b“ (beides änderbar) –, und **Datum
und Uhrzeit werden gelöscht**: in allen Textdateien (CSV, Gamry-DTA, EPR, TopSpin-Parameter, -Titel und -Prüfprotokoll),
im MS-Bericht (Text, Ersteller und Datum der Datei, Beschriftungen der Spektren) und in OPUS-Dateien (auf gleicher
Länge). Die Messwerte (FID, ser, Spektren) bleiben bytegleich. PDF, Mnova und Bruker-.d lassen sich nicht bearbeiten;
steckt dort noch ein Kürzel, nennt das Protokoll die Datei.

Jeder Export aus den Tabs TD-DFT, UV-Vis-Kinetik, Fluoreszenz, CV, SEC und EPR schreibt zusätzlich `…_data.csv` mit genau den
gezeichneten Kurven (ein x/y-Spaltenpaar pro Kurve, Werte ohne Stapelversatz) – für Origin, Excel oder MATLAB.

### Tabellen: Dateien, Excel und Kopieren

Jede Ergebnistabelle einer rechten Seite (Ergebnisse, Zusammenfassungen, Prüfungen) ist auch eine Datei und lässt sich
kopieren. **Für Excel `<Verbindung>_<Tab>_tables.xlsx` öffnen; CSV-Dateien sind für Origin/Python** (in Excel über
**Daten > Aus Text/CSV**: ein deutsches Excel öffnet eine Komma-CSV per Doppelklick als eine Spalte – keine CSV-Form
passt überall).


- **CSV** (`tables/<Verbindung>_<Tab>_<Tabelle>.csv`, z. B. `S3_H-Cell_summary.csv`): eine Form für alle Tabs – Komma als
  Trennzeichen, Punkt als Dezimalzeichen, UTF-8 mit BOM (Excel und Origin öffnen sie direkt), englische Köpfe als
  `Name [Einheit]` (Einheiten als `M^-1 cm^-1`, Indizes und Hochzahlen als `_` und `^`, griechische Buchstaben und Å/°
  bleiben), einfaches Minus, **volle Rohwerte** (gerundet wird nur am Bildschirm, im Bild und in Word).
- **Excel** (`tables/<Verbindung>_<Tab>_tables.xlsx`): ein Blatt je Tabelle mit **genau den Zahlen des Bildschirms**,
  als Zahlen mit passendem Zahlenformat (nicht als Text). Der UV-Vis-(ε)-Bericht `<Serie>_UV-Vis_report.xlsx` bleibt wie
  er ist (seine Spektren stehen dort schon im Blatt „Spektren“); X-Ray schreibt seine Tabellen in sein eigenes `…_tables.xlsx`.
  Dazu stehen die **Kurvendaten** jedes Tabs (`…_data.csv`, Abklingkurve `…_decay.csv`, HRMS `…_sticks.csv`, PXRD
  `…_pxrd_calculated.csv`, NICS-Scan) als Blatt **„data“** in derselben Mappe: dieselben Spalten und Köpfe wie die CSV, volle
  Rohwerte als Zahlen. Ein Tab mit Kurven, aber ohne Ergebnistabelle bekommt die Mappe nur mit diesem Blatt.
- **Kopieren** (Knopf an der Karte, Rechtsklick oder Strg+C in der Tabelle): Word erhält eine formatierte
  Dreilinien-Tabelle (mit typografischem Minus), Excel dieselben Zellen als Zahlen mit Dezimalpunkt – in einem Schritt,
  das Ziel entscheidet.
- **Dateien, die ein Export nicht mehr schreibt** (z. B. `…_results.csv`, nachdem der Kinetik-Tab auf Titration
  umgestellt wurde), wandern nach einem vollständigen Export des Tabs in den **Papierkorb** und stehen in der
  Exportmeldung. Betroffen sind nur Dateien, die Exporte dieser Verbindung selbst geschrieben haben (Liste in
  `.elucida/exports.json`); Dateien älterer Versionen, selbst abgelegte Dateien, einzelne Kacheln des Tabs Export,
  Schnellauswertungen und fehlgeschlagene oder unvollständige Exporte löschen nie etwas.
- Die **Exportmeldung** zählt die Dateien je Ordner (`SI/ 1 · figures/ 3 · tables/ 4`) und bietet **tables/ öffnen**.
  Auch der Tab **Export** schreibt die Tabellen jedes exportierten Tabs.

### Projekte

<p align="center"><img src="screenshots/paths_dark_de.png" alt="Reaktionspfad des Beispielprojekts: Rechendaten und Energieprofil" width="80%"></p>

**Computerchemie (Reaktionspfade):** Ein Reiter des Projekts für Energieprofile und IRCs über mehrere Verbindungen, ohne
diese zu verändern (Rechnungen werden hineinkopiert). **Gestalten** ist eine freie Zeichenfläche (Octet) für Profile,
Moleküle, Text und 3D-/Orbitalansichten (beim ersten Öffnen eines Pfads mit Rechendaten steht das Energieprofil schon
darauf), **Rechendaten** ist das Energiediagramm mit seiner Spalte in drei Schritten
(siehe unten), **3D / Orbitale** die Ansichten; deren Seiten (Ladungen, Energietabelle, SI-Text) stehen in derselben
Reiterzeile. **Profil exportieren** schreibt die Komposition in den Formaten aus „Größe und Formate“ (dazu immer
CDXML/CDX) in den Pfadordner, ohne Octet das Energieprofil bzw. die IRC. Rechnungen kommen über **Daten ▾** hinein; „Aus Verbindungen übernehmen“
öffnet die Auswahl als Karte im Schritt Daten. Unter der Abbildung steht die Bildunterschrift, unter der Zeichenfläche
die SI-Unterschrift mit **Kopieren**; **Zurücksetzen** setzt die Lage der Beschriftungen oder den Stil des Diagramms
zurück (Werte, Lage der Plateaus, Verbinder und Abschnitte bleiben). Pfade
erscheinen als Karten (Rechtsklick: umbenennen, entfernen). Alles bleibt im Hauptfenster, ☰ blendet bei offenem Pfad die Pfadliste ein und aus. Profile sind standardmäßig maßstäblich; eine schematische
Darstellung muss man ausdrücklich wählen, sie steht dann in Abbildung und SI. Energien werden nie bearbeitet, ein
veraltetes Diagramm stoppt den Export bis **Diagramme aktualisieren**. Die Gesamt-SI übernimmt die ganze Komposition.

**Energiediagramm** (Reiter Rechendaten; links Schritte, rechts das Diagramm, das jeder Änderung sofort folgt):
- **Daten:** die Rechnungen als Stufen (Label, Schritt, Pfad), Einzelpunkte, IRC-Kurven. Die Felder unter der Tabelle
  ändern das gewählte Plateau: **Position** (waagerecht in Schritten, z. B. damit Beschriftungen oder senkrechte
  Übergänge nicht kollidieren), **Breite** und **Farbe**; im schematischen Bild auch **Höhe** und „Verbinder
  unterbrechen“. **Plateau automatisch** stellt Lage am Schritt, Standardbreite und Pfadfarbe wieder her. Die Energie
  bleibt dabei unverändert.
- **Pfad:** Die Stufen sind Knoten. Im Bild am Ende eines Plateaus ziehen und auf einem anderen loslassen verknüpft sie;
  damit gehen Verzweigungen und Zusammenführungen. Ohne eigene Verbinder gilt wie bisher: je Pfadbuchstabe in der
  Reihenfolge der Schritte (**Aus Schritt und Pfad** stellt das wieder her). Die Tabelle listet die Verbinder; die Felder
  darunter ändern den gewählten: Linie (gestrichelt, durchgezogen, gepunktet, geschwungen, Wellenlinie, keine),
  Pfeilspitze und ein Text, z. B. „ISC“, „IC“ oder „hν“ wie im Jablonski-Diagramm; die Farbe steht in der Tabelle. Liegen
  zwei Stufen übereinander, läuft der Übergang senkrecht in der Spalte und setzt seitlich an den Linien an, neben den
  Beschriftungen, mehrere nebeneinander; die Linie einer Stufe dazwischen ist am Übergang unterbrochen. Der Text eines
  Verbinders steht neben der Linie, nie auf einem Strich oder einer anderen Beschriftung.
- **Darstellung:** die **Vorlage** (Klassisch, Kurven, Farbig, Minimal, Artikel) setzt den Stil in einem Zug; „Artikel“
  ist ohne Rahmen mit Pfeil an der Seite, kräftigen kurzen Plateaus, Vorzeichen an den Werten und Name und Wert
  fett-kursiv unter dem Plateau. Eine Vorlage setzt nur Felder, die sich danach einzeln ändern lassen: Karte
  **Beschriftung** (Lage von Name und Wert: Wert oben und Name unten, beide darunter oder beide darüber; Schrift;
  **Achsentitel**, „ | “ beginnt eine neue Zeile, `{unit}` steht für die Einheit; **Vorzeichen**), **Plateaubreite**, und Karte **Abschnitte** (Balken
  unter dem Profil mit Text, von–bis in Schritten und Farbe, z. B. für zwei Reaktionswege). Darunter Linienart,
  Strichstärken, Schriftgröße, Rahmen, maßstäblich und Farbe je Pfad. Der Stil gehört zum Diagramm des Pfads.
- Ein Plateau lässt sich im Bild an seiner Linie greifen und waagerecht ziehen (im Raster von 0.05 Schritten; ist
  „maßstäblich“ aus, auch in der Höhe – der Energiewert bleibt der echte). Die Enden eines Plateaus verknüpfen.
- Energien, Namen und Verbinder-Texte lassen sich im Bild mit der Maus verschieben (wenn zwei Stufen eng liegen);
  **Beschriftungen zurücksetzen** stellt sie zurück. Die Energien selbst ändern sich nie.

<p align="center"><img src="screenshots/project_dark_de.png" alt="Projektseite mit den Verbindungen und ihren Checklisten" width="800"></p>

**Datei → Neues Projekt** macht einen Ordner zum Projekt: dem übergeordneten Ordner für alle Verbindungen einer
Veröffentlichung. Die Verbindungen bleiben normale Verbindungsordner in seinen Unterordnern (jede lässt sich weiter allein
öffnen); `publication.elucida` hält ihre Reihenfolge, die Angaben für den Datensatz und die SI-Texte. Die Seite des
Projekts listet die Verbindungen mit Checkliste (Zeilen ziehen zum Umsortieren, **Nach Name sortieren**, Rechtsklick: verschieben, kopieren, herausnehmen), **Neue Verbindung** legt
einen Unterordner an, **Verbindung hinzufügen** verschiebt oder kopiert eine von woanders in das Projekt.

- **Verschieben oder duplizieren:** Rechtsklick auf eine Verbindung (Projektseite oder Übersicht) oder das Menü der
  Verbindung im Pfad oben → **In anderes Projekt verschieben …** verschiebt den Ordner; **In anderes Projekt kopieren …**
  legt eine unabhängige Kopie an, z. B. wenn dieselbe Verbindung in zwei Papern vorkommt. Verbindungen aus älteren
  Versionen ohne Projekt bietet das Programm beim Öffnen zum Zuordnen an (Pfad: „⚠ ohne Projekt“).
- **Suchen:** Das Feld oben auf dem Startbildschirm durchsucht alle Verbindungen aller bekannten Projekte nach
  Name/Nummer, Laborkürzel (z. B. AB-1-234, auch aus Dateinamen und Vorschriften), Summenformel, Notiz, Literatur oder
  Projekt; auf der Projektseite filtert dasselbe Feld die Verbindungen; Strg+F springt dorthin.
- **In den Papierkorb verschieben …** (Rechtsklick in der Übersicht) entfernt eine Verbindung oder ein ganzes Projekt
  nach einer Nachfrage mit Anzahl der Dateien und Größe; aus dem Papierkorb lässt sich alles wiederherstellen.

- **Datenpakete (Zip):** der ganze Datensatz wie auf TUDOdata – je Verbindung ein Zip (wie oben), die DFT-Rechnungen
  aller Verbindungen in `CompChem.zip`, `README.txt` (Titel, Autoren, DOI, Zitat, zugehörige Publikation,
  Beschreibungen, Lizenz; aus den **Angaben**) und der Lizenztext (CC BY 4.0 oder CC0). Laborkürzel gehören zu der
  Verbindung, in deren Dateinamen sie stehen.
- **FID for Publication (ACS):** im Dialog der Datenpakete wahlweise zusätzlich `FID for Publication.zip`: ein Ordner
  je Verbindung (ihre Nummer), darin je NMR-Experiment ein Ordner nach Art (1H, 13C, DEPT135, HSQC …; ein zweites
  gleicher Art `_2`) mit dem ganzen TopSpin-Experiment (fid/ser, Aufnahme- und Prozessierungsparameter), die Struktur
  als MolFile und `NMR_parameters.txt` (Pulsprogramm, Lösungsmittel, Frequenz, Temperatur, Gerät, Probenkopf,
  TopSpin-Version aus acqus). Nur Experimente, die im NMR-Tab (**Rohdaten**) zugeordnet sind; sie werden kopiert,
  Laborkürzel und Datum wie in den Datenpaketen ersetzt.
- **Data Availability Statement** (Seite **Angaben**): Repository und DOI/Link (ohne Link die DOI des Datensatzes),
  CCDC-Nummern aus den X-Ray-Angaben der Verbindungen (jede Nummer einzeln, Standardsatz von CCDC/FIZ), Hinweis auf
  „FID for Publication“, sobald es geschrieben wurde, und Freitext. Das Statement gehört ins Manuskript, nicht in die
  SI; **Kopieren** legt es in die Zwischenablage. Es stehen nur Bausteine darin, die eingetragen sind.
- **Gesamt-SI: Bezeichner** (Seite **Angaben**): „Figure S1 / Table S1“ oder „Supplementary Figure 1 / Supplementary
  Table 1“ (Nature-Zeitschriften), sonst wie die Vorlage. Gilt für Unterschriften und Verweise im Text („see Figure S3“
  wird „see Supplementary Figure 3“; „Figure 3“ des Artikels bleibt).
- **Gesamt-SI (Word):** eine Datei mit Titelseite und Inhaltsverzeichnis, Kapitel wie die SI der Gruppe – 1. Materials
  and Methods, 2. Synthetic Procedures and Characterization Data, 3. NMR Spectra, 4. UV-Vis Spectroscopy, 5. EPR
  Spectroscopy, 6. Cyclic Voltammetry, 7. Spectroelectrochemistry, 8. X-Ray Characterization Data, 9. Computational
  Section (leere Kapitel fallen weg). In jedem Kapitel die Verbindungen in der Reihenfolge des Projekts; Abbildungen
  zwei je Seite und fortlaufend nummeriert, Kristalldaten aller Strukturen in gemeinsamen Tabellen. **SI-Texte** enthält
  „Materials and Methods“ und je Kapitel eine optionale Einleitung.
- **Vorlagen** der Gesamt-SI: Gruppe (wie die Angewandte-SI der Gruppe: „Supplementary Materials for“, Figure S1:),
  Wiley („Supporting Information for“, Figure S1.; Angewandte verlangt ein Inhaltsverzeichnis am Anfang), ACS
  („Supporting Information for“, Figure S1., Seiten S1, S2 …; JOC verlangt ein Inhaltsverzeichnis mit Seitenzahlen), RSC
  („Supplementary Information for“, Fig. S1 wie in RSC-Artikeln), Nature („Supplementary Information for“,
  Supplementary Figure 1 |, eigene Zählung). Für die SI schreiben die Verlage kaum etwas vor; es ändern sich nur
  Titelblatt, Bezeichnungen und Seitenzahlen, Kapitel, Schrift und Seitenaufteilung bleiben wie die SI der Gruppe. Die
  Gesamt-SI hat Seitenzahlen und ein schon ausgefülltes Inhaltsverzeichnis (Seitenzahlen geschätzt; Word aktualisiert
  beim Öffnen, ONLYOFFICE über „Inhaltsverzeichnis aktualisieren“). Die SI einer einzelnen Verbindung bleibt im Stil
  der Gruppe.

## Vergleich (Projekt)

<p align="center"><img src="screenshots/comparison_dark_de.png" alt="Offener Spektrenvergleich mit Strukturen in Kurvenfarbe" width="800"></p>

Der Reiter **Vergleich** der Projektseite stellt Verbindungen des Projekts nebeneinander, beliebig viele benannte
Vergleiche. Der Reiter zeigt sie als Karten wie die Reaktionspfade (Vorschau, Name, Stand); die Karte **Neuer Vergleich …**
legt einen CV-Stapel, einen Spektrenvergleich oder eine Tabelle an, ein Rechtsklick auf eine Karte entfernt den Eintrag
(exportierte Dateien bleiben). Ein Klick auf eine Karte öffnet den Vergleich in voller Fenstergröße; zurück geht es über
die Pfadleiste oben (Projektname), deren letzter Eintrag auch zwischen den Vergleichen wechselt. Links die Schritte wie in den Tabs, rechts Abbildung bzw. Tabelle, **Exportieren** unten
rechts. Gespeichert wird in `publication.elucida`. **Rückgängig/Wiederholen** (Menü Bearbeiten, Strg+Z) gelten im offenen
Vergleich für seine Änderungen (Verbindungen, Reihenfolge, Einstellungen, Zellen, Größen, gezogene Beschriftungen), nie
für die Daten der Verbindungen.

**Nichts wird neu ausgewertet.** Jede Verbindung legt beim Speichern einen kleinen Stand ihrer Auswertungen in
`.elucida/compare.json` ab (Kurven ausgedünnt, Werte als Text genau wie im Tab: λ und ε ganzzahlig wie in der Tabelle des
ε-Tabs, E½ und ΔE_p wie in den CV-Ergebnissen, g mit vier Stellen). Der Vergleich liest nur diese Stände, öffnet also keine
Verbindung. Hat sich eine Verbindung seit ihrem Stand geändert oder fehlt er (z. B. ein Tab, der in der Sitzung nicht
geöffnet war, oder eine Verbindung aus einer älteren Version), steht sie in der Liste als **veraltet** bzw. **fehlt** und
ihre Werte bleiben leer. **Aktualisieren** öffnet diese Verbindungen kurz nacheinander, schreibt den Stand neu und kehrt
zur Seite zurück.

- **CV-Stapel:** je Verbindung ein Cyclovoltammogramm, versetzt übereinander (oben in der Liste = oberste Kurve, Ziehen
  oder Pfeile ordnen um, **Abstand** in Vielfachen der größten Kurvenhöhe). Unter „Gewählte Verbindung“: Messung (Standard:
  die erste sichtbare, im Zyklus des CV-Tabs), Redoxpaar und Beschriftung am Peak (Hinpeak, E_pa, E_pc, E½ oder keine; die
  Zahl aus den Ergebnissen des CV-Tabs). Die Struktur der Verbindung steht neben ihrer Kurve (ziehbar, als Vorgabe in
  Kurvenfarbe, abschaltbar; alle Strukturen im selben Maßstab, **Größe** = Breite der breitesten), ein Pfeil zeigt je Kurve die Messrichtung, die y-Achse hat keine Zahlen. **Normiert** teilt jede Kurve
  durch ihren größten Betrag; die Bildunterschrift sagt das. Verbindungen auf einer anderen Referenzskala als die erste
  werden nicht gezeigt (Hinweis unter dem Bild), nie umgerechnet. Die Bildunterschrift entsteht aus den Angaben der
  Verbindungen (Lösungsmittel, Leitsalz, Konzentration, Vorschub): gleiche einmal, verschiedene je Verbindung.
  **Zyklus** wählt je Verbindung einen anderen Zyklus der Messung (im Stand liegen die ersten zehn Zyklen und der
  ausgewertete). Zahlen am Peak gibt es nur für den Zyklus, den der CV-Tab ausgewertet hat; bei einem anderen bleibt der
  Peak ohne Zahl, ein Hinweis sagt das.
- **Spektren:** UV-Vis als ε (dieselbe Messung und Basislinie wie im TD-DFT-Tab, ohne Konzentration oder Molmasse keine
  Kurve) oder auf das Maximum normiert, Emission normiert wie im Fluoreszenz-Tab, beides zusammen (Emission
  gestrichelt); übereinander oder gestapelt, ein Legendeneintrag je Verbindung. **Strukturen** zeigt je Verbindung ihre Struktur,
  als Vorgabe in der Farbe der Kurve (**Struktur in Kurvenfarbe** aus: schwarz), am höchsten Punkt der eigenen Kurve bzw.
  gestapelt rechts über der eigenen Grundlinie; ziehbar, alle im selben Maßstab (**Größe** = Breite der breitesten).
  **Normierung [nm]** (bei normierter Absorption): das Maximum in diesem Bereich wird 1, etwa die Bande über 400 nm
  statt der im UV; Feld leeren = auto (Maximum der ganzen Messung). Eine Verbindung ohne Bande im Bereich wird nicht
  gezeigt (Hinweis unter dem Bild), die Unterschrift nennt den Bereich. Bei mehreren ε-Serien wählt man die Serie
  je Verbindung. **IR:** Transmission bzw. Absorbanz wie im IR-Tab, Wellenzahl fällt nach rechts; eine Verbindung, deren
  IR-Tab die andere Darstellung zeigt, wird nicht gezeigt (nie umgerechnet). **EPR** (normiert, Standard gestapelt): auf
  der Feldachse nur Spektren mit derselben Mikrowellenfrequenz wie das erste, oder mit **Frequenz angleichen** wie im
  EPR-Tab auf eine Referenzfrequenz skaliert (B·ν_ref/ν); **EPR (g)** trägt gegen g = hν/(µ_B·B) auf. Was nicht passt
  (andere Frequenz, keine Frequenz in der Datei), steht als Hinweis unter dem Bild und wird nicht gezeigt.
- **Tabelle:** Zeilen = Verbindungen in der Reihenfolge des Projekts (im Schritt „Daten“ abwählbar). Im Schritt
  „Tabelle“ stehen links drei Karten:
  - **Größen:** was verglichen wird, als Liste mit Größe, Einheit, Gruppenkopf und Herkunft. **Aus den Tabs** fügt
    einen Wert hinzu, den die Verbindungen selbst liefern (Summenformel, Molmasse, Schmelzpunkt, UV-Vis λ_max/ε/
    Lösungsmittel, Fluoreszenz λ_abs/λ_em/Stokes, CV E½/E_pa/E_pc/ΔE_p je Redoxpaar und Referenz, EPR g, Kopplungen, D
    und |E/D|, X-Ray: jeder ausgewählte Parameter des X-Ray-Tabs mit Standardabweichung aus der CIF – eine Spalte je
    Atomlabels, z. B. „C6–C7 / Å“, gefüllt bei allen Verbindungen mit denselben Labels –, Raumgruppe und Kristallsystem,
    DFT: Eingabezeile, E(el), G, HOMO und LUMO), alle genau wie im Tab; Name und Einheit stehen dann fest.
    **IR: Bande** und **NMR: Verschiebung** brauchen ein **Ziel** und eine **Toleranz** (Felder unter der Liste; Vorgabe
    IR ±15 cm⁻¹, ¹H ±0.5 ppm, andere Kerne ±2 ppm; bei NMR dazu der Kern): die Zelle zeigt die Bande bzw. das Signal
    aus der Liste des Tabs, das dem Ziel am nächsten liegt, sonst bleibt sie leer. Hat eine Verbindung mehrere
    Strukturen oder Rechnungen, wählt man sie im Schritt „Daten“ unter „Gewählte Verbindung“ (Standard: die erste). **Eigene** fügt eine Größe zum Eintippen hinzu (z. B. „IR (CN2)“ und
    „cm-1“, Rechnung, Literatur); der Kopf wird in Normschreibweise „Größe / Einheit“ gesetzt. **Gruppenkopf** setzt
    einen zweiten Kopf über benachbarte Größen (z. B. „Experimental“ / „Computational“).
  - **Weitere Verbindungen:** Zeilen für Verbindungen, die nicht im Projekt liegen (z. B. aus der Literatur); ihre
    Werte tippt man in der Tabelle ein.
  - **Zellen und Anordnung:** **Verbindungen als Spalten** dreht die Tabelle. Zellen bearbeitet man direkt in der
    Tabelle rechts (Doppelklick); ein überschriebener Wert aus einem Tab steht orange, **Wert des Tabs** stellt ihn
    zurück.

  Export als Word (Dreilinien-Tabelle wie in der SI, Namen fett), Excel und CSV; **Kopieren** legt sie als
  formatierten Text in die Zwischenablage.

Abbildungen landen als PDF/SVG/PNG in `comparisons/figures/`, Tabellen als Excel/CSV in `comparisons/tables/` und als
Word in `comparisons/SI/` des Projektordners, Dateiname = Name des Vergleichs. **Gesamt-SI → Aufnehmen** (Standard
aus) nimmt den Vergleich in die Gesamt-SI des Projekts: Abbildungen mit „Figure Sn“, Tabellen mit „Table Sn“, fortlaufend
nummeriert, im gewählten **Kapitel** nach den Verbindungen (Vorgabe: CV-Stapel → Cyclic Voltammetry, Spektren je nach
Inhalt UV-Vis, IR oder EPR, Tabelle → eigene Überschrift am Ende wie im Tab „Weitere“; leer = Name des Vergleichs).
Gezeichnet wird genau, was die Seite zeigt.

## Verbindung

Ein Verbindungsordner steht meist für **eine Verbindung** (oder einen Vergleich). Der Tab **Verbindung** ist der erste in der
Tab-Reihe und trägt ihre Nummer (die der SI, sonst die Laborbuch-Nr.) und ihre Summenformel. Links stehen Bezeichnung,
Summenformel, Molmasse und die Angaben für die SI, rechts die Zeichnung. Es gibt kein OK und kein Abbrechen: Ein Feld gilt,
sobald du es verlässt, die Zeichnung speichert sich selbst, Rückgängig nimmt jede Änderung zurück. Summenformel und Molmasse
folgen der Zeichnung (Isotope wie D inklusive), solange du sie nicht von Hand geändert hast; ein geleertes Feld nimmt wieder
den Wert der Zeichnung. **Wählen…** lädt stattdessen eine vorhandene ChemDraw- oder Bilddatei. Die Summenformel steht
schon im Feld mit tiefgestellten Ziffern. Enthält die Zeichnung mehr als ein Molekül und ist kein Salz, steht darunter ein
Hinweis: Summenformel und Molmasse gelten dann für alle zusammen. Die Probennummer lässt sich immer eintragen, auch ohne
„Substanz übrig“.
Der ε-Tab (Struktur, Molmasse), der Fluoreszenz-Tab, IR + EA und HRMS folgen der Verbindung immer: Wird sie geändert, ersetzt
das auch dort eingetragene Werte; eine ersetzte Molmasse wird eingeblendet, Rückgängig stellt sie wieder her. Im UV-Vis-Tab
gibst du dazu nichts mehr ein: Die Karte **Verbindung** zeigt Summenformel und Molmasse, **Ändern …** öffnet die Verbindung,
**Struktur im Bild** blendet die Struktur für eine Serie aus. Der Name steht im Fenstertitel. Der dort eingetragene Schmelzpunkt beginnt den
Charakterisierungsabsatz im SI-Abschnitt. Die Molmasse wird überall mit zwei Nachkommastellen geführt. Die
**Laborbuch-Nr.** steht neben der Nummer für die SI: Sie erscheint in der Übersicht und wird von der Suche gefunden,
aber nie in SI, Word oder Datenpaket.

**Reinheit:** Die Karte **Reinheit** hält fest, womit die Reinheit belegt ist (¹H-NMR, ¹³C-NMR, qNMR,
Elementaranalyse, HPLC, GC, dazu Freitext). Der Charakterisierungsabsatz der SI endet dann mit „Purity was established by
¹H and ¹³C NMR spectroscopy and elemental analysis.“ (ACS, Angewandte). Ohne Angabe steht dort kein solcher Satz. Ein
Vorschlag aus den Daten (Elementaranalyse innerhalb 0,4 %, sonst die Kerne der NMR-Zeile) wird nur angeboten
(**Vorschlag übernehmen**); ohne diesen Klick wird nichts eingetragen.

**In ChemDraw bearbeiten:** Jeder Verbindungsordner enthält von Anfang an leere ChemDraw-Dateien für Struktur und
Reaktionsschema (`structures/<Name>.cdxml`, `…_scheme.cdxml`, Dokumenteinstellungen ACS 1996). **In ChemDraw
bearbeiten** (Menü **…** über der Zeichnung im Tab Verbindung und im Synthese-Tab) öffnet die Datei in ChemDraw; sobald du dort speicherst, übernimmt Elucida
die Struktur (Formel, Molmasse, Bilder) bzw. das Schema von selbst.

## SI-Abschnitt (Word)

**SI (Word)** im Tab **Export** (oder **Datei → SI-Abschnitt exportieren (Word) …**) exportiert sofort mit der Auswahl
dort: Teile als Chips in der Karte **SI (Word)** (Charakterisierung, NMR-Spektren, Abbildungen, Methodik,
Kristallstruktur, DFT) und die Schriftart – beides gemerkt auf diesem Rechner –, die Abbildungen über die Spalte **SI**
der Tabelle; diese Häkchen werden mit der Verbindung gespeichert (Rückgängig geht) und gelten auch für die Gesamt-SI.
Eine Verbindung ohne eigene Auswahl übernimmt die frühere Auswahl dieses Rechners. Gewählte Teile ohne Daten fallen weg (Hinweis unten rechts). Der Export sammelt alles Fertige zur Verbindung in
`SI/<Verbindung>_SI.docx`, im Stil der SI: ein Charakterisierungsabsatz **m.p. …; IR …; HR-MS …; UV-Vis …;
Elemental analysis …** (Schmelzpunkt aus dem Tab **Verbindung**, UV-Vis-Zeile von der Seite **SI-Zeile** im Tab UV-Vis (ε):
*λ*_max: 350 nm (*ε* = 12000 cm⁻¹ M⁻¹), … mit den Banden wie im Bild, aufsteigend, ε ganzzahlig), danach Kristalldaten-Tabelle, ausgewählte Parameter und Bildunterschriften aus dem
X-Ray-Tab und die DFT-Rechnungen (zweispaltig). Was noch fehlt, wird nach dem Export aufgezählt. Zahl und Einheit sind
durch geschützte Leerzeichen verbunden, Word trennt also nie „298 nm“ oder „ε = 8440“.

**Meldung nach dem Export** (gleich für **Exportieren**, **SI (Word)**, **Gesamt-SI** und **Datenpakete**): Eine
Einblendung unten rechts nennt Ziel und Formate und, was benutzt wurde – bei **SI (Word)** die Teile, die abgewählten
Abbildungen und die Tabellen mit eigenem „In die SI“ (IR-Rechnung, Anregungen, NTO), bei Datenpaketen die Zahl der
Dateien bzw. was je Verbindung abgewählt ist. Ein Klick springt zum Ort der Auswahl (**Formate ändern**, **Auswahl
ändern** = Tab **Export**, der Tab einer Tabelle, **Ordner öffnen**). Abgewählte Abbildungen fehlen in **SI (Word)**
und in der Gesamt-SI; beide Meldungen nennen sie (die Gesamt-SI je Verbindung). Wurden Teile
ausgelassen, weil eine Datei nicht lesbar war, steht die Meldung zuerst als eine Zeile da (z. B. „SI gespeichert –
2 Hinweise“); **Details** klappt sie mit allen Angaben auf, **Schließen** nimmt sie weg.

**Folien (PPTX):** **Folien (PPTX)** im Tab **Export** schreibt die Abbildungen mit Häkchen in der Spalte **Folien**
(eigene Auswahl, unabhängig von der SI) als `figures/<Verbindung>_slides.pptx`: eine Folie je Abbildung, Bild eingepasst im
Seitenverhältnis, darunter die Bildunterschrift als bearbeitbares Textfeld. Mit dem Format **PPTX** im Tab **Export**
kommt außerdem jede einzelne Abbildung beim **Exportieren** als eigene Folie mit.

**Abbildungen:** Die Abbildungen aller Tabs mit Daten (UV-Vis (ε) je Serie, IR, HR-MS, TD-DFT, UV-Vis-Kinetik, Fluoreszenz, CV, SEC,
EPR) und die NMR-Spektren stehen immer **zu zweit auf einer Seite**; passen Bild und Unterschrift nicht, werden beide
Abbildungen der Seite verkleinert (Seitenverhältnis bleibt). Unter einem längeren Text folgt noch eine
Abbildung auf derselben Seite, solange sie mindestens 7 cm hoch bleibt. Unterschriften wie in der SI: UV-Vis „UV-Vis spectra of
**X** in THF, measured in 0.1 cm quartz cuvettes.“ (Lösungsmittel unter „Auswertung“ im ε-Tab); CV, SEC und EPR nehmen
Vorschub, iR-Kompensation, Referenz, Potentialbereich, Band, g und Kopplungen aus den Daten und Konzentration,
Lösungsmittel, Leitsalz bzw. Spezies aus den Feldern im Reiter **SI-Text** des Tabs (Formeln stehen dort schon im Feld mit
tiefgestellten Ziffern; die Texte stehen im Blocksatz, gesetzt wie im Druck). **Kopieren** steht in jeder Karte oben rechts
auf der Titelzeile, auch bei der NMR-, IR-, EA- und HRMS-Zeile. **Aufbau-Text (SI) …** neben „Kopieren“ des Methodentexts speichert den allgemeinen Absatz zu Gerät und Aufbau nur auf diesem Rechner (nicht in der Verbindung,
nicht im Repository); er steht vor den Abbildungen dieses Tabs. Word öffnet die Dateien im normalen Modus (Word 2013+).

**SI-Text zu den Fits:** Jeder Tab, der etwas fittet (UV-Vis (ε), CV, SEC, EPR), hat den Knopf **Kopieren** in der Karte „Methodentext“ (Reiter SI-Text):
ein englischer Methodenabsatz, der genau die benutzten Auswerteschritte mit ihren Einstellungen beschreibt (z. B. ε:
Basislinienfenster, OLS-Modell, Cutoff, SE/95-%-KI; EPR: Basislinienpolynom, Feldkalibrierung, S = ½-Fit, Kinetik), zum
Anhängen an den Aufbau-Absatz des passenden SI-Abschnitts, danach die Ergebnisse. Derselbe Text wird beim Export als
`…_methods.txt` geschrieben, und **SI (Word)** kann alle Texte als Abschnitt „Data processing and fitting“ (ein Absatz je
Technik) hinter die Abbildungen setzen – so ist dokumentiert, wie die Rohdaten verarbeitet wurden.

**Schriftart der Word-Exporte:** in der Karte **SI (Word)** im Tab **Export** wählbar (Standard Arial wie die SI der Gruppe), gilt für alle
Word-Exporte. Die Größe bleibt 11 pt, weil „zwei Abbildungen je Seite“ mit dieser Zeilenhöhe rechnet.

## Synthese-Tab

„Synthesis of **Name**“ (der Name der Verbindung aus dem Tab „Verbindung“, sonst der Ordner; Namen werden nur dort vergeben), Reaktionsschema und Vorschrift,
als eigene Word-Datei oder im SI-Abschnitt.

- **Eingebauter Zeicheneditor (Octet Draw):** Das Schema entsteht direkt im Tab; Änderungen werden nach einer Sekunde
  gespeichert, frühere Stände bleiben in `structures/.editor-backups/`. Strukturprüfung, Clean-up und Name-zu-Struktur
  arbeiten offline; ChemDraw-Kürzel und Kopieren/Einfügen bleiben, Dateiaktionen stehen im ⋯-Menü. Beschriftungen wie
  `NaBH4 (1,5 Äq.)` oder `Pd(PPh3)4 (5 mol%)` zählen als Äquivalente, ausdrückliche Mengen haben Vorrang. **Aus
  Octet-Tabelle übernehmen** kopiert die Stöchiometrietabelle des Editors auf Klick in die Reagenzientabelle (keine
  Live-Kopplung; gleiche Formeln werden nur nach Spalte zugeordnet, also prüfen). In die SI kommt nur die **oberste
  Reaktion mit ihren Bedingungen**, im Vorschaubild wie in der eingebetteten CDX; die ganze Zeichnung bleibt im Projekt.
  Word-Exporte schreiben zusätzlich `<Name>_structures/` mit CDX/CDXML-Momentaufnahmen zum Öffnen in ChemDraw auf jedem
  System (Bearbeiten per Doppelklick in Word bietet ChemDraw nur unter Windows). Der Tab Verbindung hat denselben
  Editor: Die Zeichnung speichert sich selbst, Formel und Masse folgen ihr, solange du sie nicht von Hand korrigiert hast.
- **Schema:** **In ChemDraw bearbeiten** öffnet die leere Schemadatei der Verbindung (Speichern wird automatisch
  übernommen), oder eine vorhandene CDXML wählen. Daneben (gleicher Name, gleicher Ordner) kann man aus ChemDraw speichern: **SVG/PDF**
  (Bild unverändert übernommen), **.cdx** (das Schema wird in Word ein bearbeitbares ChemDraw-Objekt – Doppelklick
  öffnet ChemDraw; mit einer CDXML kann Word das nicht) und **.emf** (scharfe Vektorvorschau dieses Objekts). Ohne
  SVG/PDF wird das Schema aus den CDXML-Koordinaten gezeichnet, mit Pfeil und Bedingungen.
- **Vorschrift** mit fett, kursiv, tief- und hochgestellt. **GP ▾** wählt eine allgemeine Vorschrift des Projekts
  („according to **GP A**“); in der Gesamt-SI steht sie einmal vor der ersten Verbindung, die sie benutzt.
- Mengen dürfen eine Einheit in der Zelle tragen („1.03 g“, „150 µL“, „800 mM“), n ist eintragbar; mit einer
  ChemDraw-Reagenzientabelle im Schema übernimmt **Aus Schema** deren Werte.
- **Mengenprüfung:** Angaben wie „(1.03 g, 5.00 mmol, 1.0 eq.)“, „(99%)“ werden mit der Reagenzientabelle verglichen
  (M oder Summenformel, Masse, Volumen, Konzentration, Dichte); Abweichungen jenseits der Rundung der angegebenen Stellen
  werden markiert. **Aus Schema** füllt die Tabelle mit den Edukten (erstes = Bezug 1.0 eq.), den Reagenzien über/unter
  dem Pfeil (z. B. K2CO3), Lösungsmitteln und dem Produkt; **Klammer einfügen** setzt die berechnete Klammer der gewählten
  Zeile an der Schreibmarke ein.

## NMR-Tab

- **Spektren:** SVG-Exporte aus MestReNova (Drag & Drop). Der Kern kommt aus der Achsenbeschriftung („δ ¹H (ppm)“);
  fehlt sie, von Hand eintragen. Reihenfolge: ¹H, ¹³C, übrige Kerne nach Massenzahl, dann 2D (COSY, HSQC, HMBC,
  NOESY …).
- **Struktur** in jedem Spektrum als Vektorgrafik: automatisch an einer freien Stelle (nichts verdeckt), oder oben
  links/mittig/rechts, oder in der Vorschau gezogen; das Mausrad über der Struktur ändert die Größe, für alle Spektren
  gleich. Unter der Struktur stehen die **Nummer** der Verbindung (fett) und die **Messangaben** (Kern, Frequenz,
  Lösungsmittel), wie ACS und Angewandte es für jedes Spektrum verlangen; beides lässt sich mit den zwei Chips
  abschalten. Die Tabelle der Spektren zeigt den beschrifteten **Bereich** der Achse: üblich sind mindestens −1…10 ppm
  (¹H) und 0…200 ppm (¹³C, Angewandte −10…200); reicht die Beschriftung nicht bis 0 bzw. 10/200 oder liegt ein Signal
  der NMR-Zeile außerhalb der Beschriftung („Signal δ … außerhalb des Bildbereichs“, auch unter der Vorschau), steht ein
  ⚠ (nur ein Hinweis, das Spektrum selbst kommt aus MestReNova).
- **NMR-Zeile:** den Mnova-Multiplettbericht einfügen („Multiplets → Copy“, Journal-Format) – alle Kerne in das eine
  Feld, je Kern eine Zeile. **Zeile aus Peaklabels** baut die ¹³C-Zeile (oder andere) aus den beschrifteten Peaks des
  gewählten Spektrums; ein mit Namen beschriftetes Lösungsmittelsignal („77.16 CDCl3“) fällt weg. Zuordnungen je Signal
  in der Tabelle (*kursiv*, _{tief}, ^{hoch}). Darunter steht als kleine Tabelle der Vergleich mit der Summenformel der
  Verbindung: bei ¹H die Summe der H-Zahlen, bei anderen Kernen die Zahl der Signale gegen die Atome des Elements
  (✓ passt oder ist möglich, ⚠ mehr als die Formel erlaubt oder Kern nicht in der Formel). Nur ein Hinweis.
- **Verunreinigungen** (Chip, Vorgabe an): eine zweite Tabelle nennt ¹³C-Signale, die bis auf 0.02 ppm (plus die halbe
  letzte angegebene Stelle) einem Restsignal des Lösungsmittels oder einer häufigen Verunreinigung im Lösungsmittel der
  Zeile entsprechen (Fulmer et al., Organometallics 2010, 29, 2176), mit Tabellenwert und Stoff. Ein Stoff mit mehreren
  C zählt erst, wenn alle seine C mit H passen. Ist das Lösungsmittelsignal im ¹³C-SVG beschriftet („77.00 CDCl3“), wird
  der Abgleich um den Abstand zur Tabelle verschoben (ein Satz unter der Tabelle nennt ihn; mehr als 0.5 ppm: kein
  Abgleich); ohne solches Label kein Versatz. Erkannt werden Namen wie CDCl3, Chloroform-d, DMSO-d6, (CD3)2SO, C6D6,
  CD3CN, CD3OD, D2O, THF-d8, Toluol-d8, C6D5Cl, TFE-d3; andere Namen ergeben keinen Hinweis. ¹H: verglichen werden nur
  freie Peaks, also Peaks außerhalb aller Multipletts der ¹H-Zeile (Mitte ± halbe Breite erster Ordnung aus
  Multiplizität und J, bei „m“ der Bereich, dazu 0.01 ppm); die Signale der Zeile werden nie markiert. Die Peaks kommen
  nur aus MNovas Peakbericht (exportiertes Dokument); ein eigenes Spektrum hat keinen ¹H-Abgleich (automatische Peaks
  trafen richtige und falsche Lösungsmittelspalte gleich oft). Ohne Peakliste sagt das ein Satz unter der Tabelle. Ein
  Stoff mit mehreren Signalen zählt erst, wenn jedes einen eigenen freien Peak trifft (Warnfarbe); Stoffe mit einem
  Signal (Wasser, Aceton …), das Restsignal und das undeuterierte Lösungsmittel selbst (Toluol in Toluol-d8) stehen grau
  als „möglich“. Kein Referenzversatz für ¹H. Nur ein Hinweis.
- **Temperatur** standardmäßig 298 K, oder aus dem Bruker-Experimentordner (acqus, mit Übersicht der Parameter wie
  Frequenz, O1P, Pulsprogramm, Scans).
- **Rohdaten** (Reiter neben der Abbildung): **TopSpin-Daten …** nimmt ein Experiment, einen Datensatz (10, 11, …) oder
  einen Ordner mit mehreren Datensätzen – auch per Ziehen ins Fenster, wie in MNova auch eine einzelne Datei des
  Experiments (fid, ser, acqus …) oder seinen pdata-Ordner – und übernimmt jedes Experiment vollständig in
  die Verbindung, nach Art sortiert (`data/nmr/1H`, `13C`, `DEPT135`, `HSQC` …). Passt genau ein Experiment zu einem Spektrum,
  wird es automatisch zugeordnet (Parameter, Temperatur).
- **Eigene Spektren aus Bruker-Rohdaten** (optional; Mnova-SVG bleibt Standard): **Rohdaten …** in der Karte
  „Spektren“, **Als Spektrum** im Reiter „Rohdaten“ oder **Quelle** „Bruker-Rohdaten“ bei einem Spektrum mit
  zugeordnetem Experiment. Elucida rechnet das Spektrum aus dem FID (Phase aus procs, Basislinie automatisch) und zeigt
  es in einer Ansicht mit den Mnova-Tasten (Z, F, H, P, I, K, J, R, C, X, E, Shift+P, Esc; jeder Modus auch als Knopf).
  Die Tasten wirken ohne Klick: Die Ansicht bekommt den Fokus beim Öffnen des Tabs und wenn die Maus darüber steht,
  außer in einem Feld wird gerade getippt. **Basislinie** (Karte „Verarbeitung“): Polynom 5. Grades (Standard, wie
  TopSpin ABSG 5), Bernstein 3. Grades (Mnovas Vorgabe „Advised“; die signalfreien Punkte wählt Elucida selbst) oder aus.
  Die Achse übernimmt nie TopSpins Kalibrierung: **Referenzierung** schlägt das Restsignal des Lösungsmittels vor
  (Fulmer 2010, ¹H und ¹³C); erst „Bestätigen“ oder ein Klick auf die richtige Spitze im Modus R (sie bekommt den
  **Sollwert**) macht die Referenz „bestätigt“. Die **Phase** aus procs ist ebenso „nicht bestätigt“ (TopSpins Phase ist
  bei ¹³C oft schlecht): bestätigen, vorschlagen lassen (ACME, nur ein Vorschlag) oder von Hand ziehen (Shift+P: linke
  Taste 0. Ordnung, rechte 1. Ordnung, Klick = Drehpunkt). Experimente, deren Verarbeitung nicht geprüft ist (z. B.
  anderes Fenster als EM, Linear Prediction), erscheinen als TopSpins 1r mit Meldung. Darstellung (Schritt 3) wie die
  Mnova-Vorlage, alles schaltbar.
  **Auswertung** (Schritt 2): Integrale im Modus I aufziehen, ein Integral oder Signal wählen und **Normierung** setzen
  (erst dann gibt es Kerne). **Multipletts vorschlagen** oder im Modus J einen Bereich aufziehen; für ein gewähltes Signal
  Klasse und J eintragen und **Muster anpassen** – die gefundenen Linien stehen als Striche über dem Spektrum (orange
  Vorschlag, grün bestätigt). Jedes Signal einzeln **bestätigen**; nur bestätigte δ und J kommen in die SI-Zeile, sonst
  Bereich + m. Ist ein J nicht getrennt („J nicht gemessen“), druckt es nur **J übernehmen**; **Ohne dieses J** passt
  das Muster ohne es neu an. ¹³C: **Peaks vorschlagen** (ab 5σ), Überzähliges im Modus K wählen und löschen;
  bei bestätigter Phase wird nur das höchste Maximum in ±1 Hz vorgeschlagen, die Karte nennt, wie viele weitere Maxima
  weggelassen wurden.
  In die SI kommt ein eigenes Spektrum erst mit **Eigene Verarbeitung für die SI** (Chip im ausgewählten Spektrum, je Kern eines) und
  bestätigter Phase und Referenz (bei ¹⁹F u. a. die nominelle Achse bestätigen); bis dahin bleiben Mnova-Zeile und
  -Abbildung, der Satz unter der NMR-Zeile sagt warum. Gedruckt werden nur bestätigte Signale; offene Vorschläge werden
  gezählt. Die NMR-Zeile dieses Kerns ersetzt dann die aus dem Mnova-Text; der Reiter **SI-Abbildung** zeigt das Spektrum wie in
  Word (Struktur, Ausschnitte, Marken mit Bedeutung im Feld „Marken“). Den Bereich legt nur das Feld **Bereich** fest
  (Schritt 3); „auto“ = 9…0 ppm bei ¹H und 200…0 ppm bei ¹³C, so weit erweitert, dass jedes Signal der NMR-Zeile mit
  Rand (¹H 0.5, ¹³C 5 ppm) innen liegt, auf ganze ppm bzw. 10 ppm gerundet (Hydrid bei −8 ppm: 9…−9; Carben bei 250 ppm:
  260…0); freie Peaks, Verunreinigungen und das Lösungsmittel erweitern nie. Ein eigener Bereich bleibt, ein Signal
  außerhalb davon steht als ⚠ in der Spalte „Bereich“ und unter der Ansicht. Zoomen in der Ansicht ändert die Abbildung nie.
  **Ausschnitte** wie Mnova: E + Ziehen = Ausschnitt; X + Ziehen in einem Ausschnitt schneidet diesen Bereich aus dem
  Ausschnitt (Teile mit „//“-Bruch, jeder Schnitt ein Rückgängig-Schritt); Umschalt+E fügt einen Teil an. Die Labels
  eines Ausschnitts stehen gruppiert über ihrem Teil. Passen Labels auch mit kleinster Schrift nicht in die Breite, gibt
  es nur einen Hinweis („Ausschnitt anlegen oder Peaks ausdünnen“); nichts wird geändert. Peak-Labels sind wie die
  Mnova-Vorlage 4 pt groß und nur größer stellbar. In der Ansicht sind Multiplett-Labels mindestens 12 px hoch (die
  SI-Abbildung behält die Größe der Vorlage). Ein abgelegter Bruker-1D-Ordner ohne passendes Mnova-Spektrum wird ein
  eigenes Spektrum (nicht für die SI gewählt); die Exportmeldung nennt zurückgehaltene (nicht freigegebene) eigene
  Abbildungen in einer Zeile mit „Details“.
  **2D aus Rohdaten** (HSQC, HMBC, COSY …): Höhenlinien (positiv blau, negativ rot) mit Projektionen; Rechteck ziehen =
  Zoom, Doppelklick = ganzes Spektrum, Mausrad = Schwelle. Die Achsen gelten erst als referenziert, wenn ein eigenes
  ¹H- bzw. ¹³C-Spektrum desselben Magneten eine bestätigte Referenz hat; der Satz unter dem Bild sagt es.
  **X-Kerne** (¹⁹F, ³¹P …): ohne Lösungsmittelsignal bleibt die Achse nominell. **Unified Scale (¹H)** rechnet sie über
  das eigene ¹H derselben Probe am selben Magneten (Referenz dort bestätigt) auf die IUPAC-Skala um; ¹⁵N wahlweise gegen
  MeNO2 oder NH3. Danach wie jede Referenz bestätigen.
- **Vergleich: Einzeln · Überlagert · Gestapelt** (Leiste über der Abbildung, Vorgabe Einzeln, gespeichert, jeder Wechsel
  ein Rückgängig-Schritt): nur eigene 1D-Spektren (Bruker-FID oder FID aus einem MNova-Dokument) desselben Kerns und
  Lösungsmittels; bei MNova-Bildern ist die Leiste ausgegraut (ein Bild lässt sich nicht überlagern, der Tooltip sagt
  es). Welche Spektren dazugehören, bestimmen die Häkchen in der Spektrentabelle (Spalte erscheint in Überlagert/
  Gestapelt); beim ersten Umschalten kommt das gewählte Spektrum dazu. Die Ansicht zeigt das gewählte Spektrum vorn bzw.
  oben, **Versatz** (20–150 %) rückt die gestapelten Spuren auseinander. Beschriftung je Spur im Bild: eigener Text
  (Karte **NMR-Vergleich**), sonst die Temperatur, wenn sie sich unterscheidet, sonst der Dateiname.
  Unterschrift = fester Teil „¹H NMR (500 MHz, THF-d₈, 193–298 K) of **X**.“ (Temperaturen als Bereich) + ein eigener
  Satz aus der Karte. Export und SI nur, wenn bei jeder Spur Phase und Referenz bestätigt sind (sonst nennt die
  Exportmeldung den Grund): **Exportieren** schreibt `<Verbindung>_NMR_comparison_<Kern>` (SVG/PDF/PNG wie im Tab
  „Export“) nach `figures/`, die Word-Datei des Tabs und „SI (Word)“ setzen die Vergleiche nach den Spektren unter die
  Überschrift aus der Karte (Vorgabe „NMR Comparisons“), die Gesamt-SI als eigenes Unterkapitel am Ende des Kapitels
  NMR. Ein Bereich für alle Spuren (Vereinigung ihrer Bereiche), ohne Struktur und Auswertung. Nicht in den Folien
  (PPTX), wie die übrigen NMR-Abbildungen.
- **Vorhersage** (Chip rechts in der Leiste, nur auf Klick, nicht gespeichert): Octets NMR-Vorhersage für die Struktur der
  Verbindung (CDXML) als eigene Spur unter dem Spektrum, für ¹H und ¹³C, ¹⁹F und ³¹P mit Warnung (Tabellen dort
  dünn). Lösungsmittel wie in der Messung, falls Octet es kennt (sonst Verschiebungen aller Lösungsmittel, mit Hinweis);
  Frequenz des Magneten. Die Vorhersage steht **nie** in einer Ausgabe: nicht in Projektdatei, SI, Word, PPTX,
  Datenpaket, „Abbildung kopieren“ oder SVG/PDF/PNG. Unter der Ansicht steht der Lizenzhinweis von nmrshiftdb2. Ist die
  Referenz eines gezeigten Spektrums nicht bestätigt, sagt ein ⚠, dass die Lage gegenüber Vorhersage bzw. anderen
  Spuren unsicher ist.
- **MNova-Dokumente** (`.mnova`): Karte oben in der linken Spalte – **MNova-Dokument …** oder Ablegen. Die Datei liegt
  unverändert in `data/nmr/mnova`.
  - **Mit installiertem MNova** (macOS und Windows; unter Windows noch nicht an einer echten Installation geprüft) exportiert MNova eine Kopie im Hintergrund; die Karte
    MNova zeigt den Fortschritt. Jede Seite mit Spektrum wird ein Spektrum `<Dokument>_<Seite>.svg` in
    `data/nmr/mnova/<Dokument>/` (MNovas Berichte in `manifest.json`). Gleiche Spektrumobjekte einer Seite
    (Inset, Ausschnitt) sind ein Spektrum; verschiedene werden genannt und ergeben keine Zeile.
  - **NMR-Zeile aus MNovas Berichten:** ¹H nur aus dem Multiplettbericht (eine Seite ohne Multiplettanalyse ist nur
    Abbildung, mit Hinweis); andere Kerne aus den Multipletts, sonst aus den Peaklabels der Seite – wo es beides gibt,
    schaltet **SI-Zeile** (Ausgewähltes Spektrum) zwischen *Multipletts* und *Peaks*. 2D nie in die Zeile; je Kern gilt
    der erste Bericht, weitere werden genannt. Text im Feld wird nie still ersetzt: **Übernehmen** oder **Behalten**.
  - Die FIDs des Dokuments hängen als Rohdaten am einen passenden Spektrum (Quelle bleibt MNova, bis die eigene
    Verarbeitung gewählt wird; MNovas Referenzierung ist dann ein Vorschlag). FIDs ohne eindeutige Zuordnung bleiben als
    Ordner liegen (von Hand über „Bruker-Ordner …“).
  - **Ohne MNova**, nach der Zeitgrenze oder bei einem Fehler (auch ein Pfad mit Komma) wird das Dokument wie bisher
    gelesen: jedes lesbare 1D-Spektrum mit FID wird ein eigenes Spektrum (Quelle „Rohdaten aus MNova-Dokument“,
    verarbeitet wie ein Bruker-Experiment), 2D-Spektren und ungeprüfte MNova-Versionen werden genannt; die Einblendung
    nennt den Grund. Zusammen mit SVG-Dateien abgelegt hängt ein Dokument nur seine FIDs an diese.
  - **In MNova öffnen** öffnet das Dokument in MestReNova.
- Spektren können auch **EMF** aus Mnova sein: Sie gehen unverändert nach Word (Vektor, ohne eingesetzte Struktur); für
  Vorschau und Struktur SVG verwenden.
- **Word:** zwei Spektren je Seite, „Figure Sn: ¹H NMR (500 MHz, CDCl₃, 298 K) of **Name**.“

## IR + EA-Tab

- **IR:** Bruker-**OPUS**-Datei (`*.0`, Spektrum) und/oder den **OPUS-PDF**-Ausdruck (Peakbeschriftung) laden. Mit dem
  PDF sind die Werte genau die OPUS-Peakliste; mit der Datei allein sucht Elucida die Banden selbst
  (Empfindlichkeit einstellbar). Bereich frei wählbar (Standard: der ganze gemessene Bereich); Banden, die nicht in die
  Liste sollen, abhaken; Intensitäten w/m/s/br optional (relativ zur stärksten Bande: s ab 60 %, m ab 30 %, sonst w; br ab einer
  Halbwertsbreite von 120 cm⁻¹). Ausgabe: **IR** [cm⁻¹]: ṽ = 2961, 2866, … (ganze Zahlen,
  absteigend).
  **Basislinie korrigieren (wie OPUS)** zieht die Basislinie wie OPUS ab (nur Bild und Peaksuche); **Schwelle setzen**:
  Punkte ins Bild klicken, Peaks jenseits der Linie. Liegt nur das OPUS-PDF vor, wird das Spektrum aus dem PDF gelesen.
- **HRMS:** den **Word-Bericht** der Massenabteilung laden; Formel, Ionisierung, Polarität und die gemessenen m/z (aus
  den eingebetteten Spektren) werden ausgelesen. Die Formel kommt aus der Verbindung (Warnung, wenn der
  Bericht etwas anderes sagt), das Ion ist wählbar ([M+H]⁺, [M+Na]⁺, [M]⁺, [M−H]⁻ …), vorgewählt ist das nächste
  gemessene m/z. calc. mit Elektronenmasse, vier Nachkommastellen: **HR-MS-ESI(+)** calc. C₁₈H₁₉N₂O⁺ [M+H]⁺ 279.1492;
  found 279.1496. Die Abweichung in ppm steht zur Kontrolle daneben (found − calc). Die Formel wird gegen das im
  Bericht **eingebettete ChemDraw-Objekt** geprüft; ohne festgelegte Verbindung setzt **Verbindung aus dem MS-Bericht
  übernehmen** Name, Formel und Molmasse daraus (die Zeichnung ist dann eine RDKit-Ersatzzeichnung – für Abbildungen
  die eigene CDXML nehmen).
- **HRMS aus Rohdaten:** alternativ (oder zusätzlich) den Bruker-**Messordner** (`.d`, z. B. timsTOF; Knopf oder
  Drag & Drop) laden. Elucida liest die Linienspektren des Geräts selbst (ohne Bruker-Software, auch unter macOS)
  und mittelt das Ion über den **LC-Peak** (automatisch: zusammenhängende Scans mit ≥ 50 % des Maximums, oder ein
  gewählter RT-Bereich). found = intensitätsgewichtetes Mittel; Anzahl der Scans, Bereich der Einzelscans und ihre
  Streuung (± mDa/ppm) stehen dabei, weil Einzelscans in der 4. Nachkommastelle abweichen können. Mit Bericht bleibt
  dessen Wert vorgewählt, das Mittel aus den Rohdaten ist wählbar. In die Verbindung kommen nur `analysis.baf` und
  `analysis.sqlite`.
- **Elementaranalyse:** Formel aus der Verbindung, optional plus Solvat (`0.5 CH2Cl2`, mehrere mit
  Komma); berechnet mit den konventionellen mittleren Atommassen, gefundene C/H/N/S-Werte eintragen. Abweichungen über
  0.4 % werden markiert (übliche Grenze der Journals). Ausgabe, aufgebaut wie die HR-MS-Zeile: **Elemental analysis** (%) calc.
  C₁₈H₁₈N₂O: C 77.67, H 6.52, N 10.06; found C 77.41, H 6.59, N 9.87. Die Elementaranalyse ist immer optional (wird
  nicht als fehlend gemeldet).
  **Doppelbestimmung** (Angewandte verlangt beide Wertesätze und das Mittel): zweiten Satz in der Zeile „2. Messung“
  eintragen; die Zeile nennt dann beide Sätze und „(average …)“, geprüft wird das Mittel. Die Tabelle darunter zeigt je
  Element den geprüften Wert, Δ und den Status (über 0.4 % in der Warnfarbe), die Kachel „EA“ oben rechts das Ergebnis
  auf einen Blick. Ohne EA: „Ohne EA, weil“ ausfüllen (englisch), dann steht „Elemental analysis: …“ in der SI.
- **In Zwischenablage** behält Fettdruck, Hoch- und Tiefstellung beim Einfügen in Word. Der Export schreibt die
  Spektrenabbildung und `…_SI.txt` mit allen Zeilen.
- **IR-Rechnung** (Karte im Schritt IR, Seite „IR-Rechnung“): eine ORCA- (5/6) oder Gaussian-Ausgabe einer
  Frequenzrechnung wählen; sie braucht IR-Intensitäten („IR SPECTRUM“ in km/mol bzw. „IR Inten“). Das berechnete
  Spektrum liegt über dem gemessenen – als Linienspektrum („Verbreiterung: aus“) oder mit Lorentz-Profilen der gewählten
  Halbwertsbreite –, so skaliert, dass seine stärkste Bande im gezeigten Bereich so tief (%T) bzw. hoch (A) ist wie die
  gemessene; in %T wird nur das berechnete Spektrum umgerechnet. **Skalierung** multipliziert die berechneten
  Frequenzen (Vorgabe 1.000 = ungeskaliert): der passende Faktor hängt von Methode und Basis ab, deshalb selbst
  eintragen. **Toleranz**: eine Bande wird nur automatisch zugeordnet, wenn genau eine berechnete Mode (ab 5 % der
  stärksten) innerhalb ± Toleranz liegt und diese Mode bei keiner anderen Bande liegt; „aus“ = nur von Hand.
  **Bande/Mode + Zuordnen** ordnet von Hand zu (gilt vor der automatischen Wahl), **Lösen** entfernt das. Die Seite
  listet die zugeordneten Banden (Δṽ = gemessen − berechnet) mit der mittleren |Δṽ|; mit „In die SI (Word)“ folgt die
  Tabelle nach den Abbildungen (Gesamt-SI: Kapitel Rechnungen), die Unterschrift nennt Rechenniveau, Skalierung und
  Verbreiterung. Imaginäre Frequenzen werden nicht gezeichnet (Hinweis auf der Seite).
- **Raman** (Karte im Schritt IR): ein Raman-Spektrum als **Textdatei** mit den Spalten Raman-Verschiebung [cm⁻¹] und
  Intensität laden (`.txt`, `.csv`, `.dat`, `.xy`; Kopfzeilen werden übersprungen; Tab, Semikolon, Komma oder
  Dezimalkomma). Binärformate von Geräten werden nicht gelesen – das Spektrum als Text exportieren. Elucida sucht die
  Maxima (Schwelle relativ zum stärksten Peak im Bereich); Peaks in der Tabelle abwählen. Die **Anregung** eintragen;
  die SI-Zeile lautet **Raman** (λexc = 785 nm): ṽ = 2217, 1608, … cm⁻¹ und steht im Charakterisierungsabsatz hinter
  der IR-Zeile. **Abbildung** wählt, was das Bild des Tabs zeigt: IR, Raman (Achse „Raman shift [cm⁻¹]“, Intensität in
  willkürlichen Einheiten ohne Zahlen, Beschriftung über „Wellenzahlen im Bild“) oder **IR und Raman übereinander** (IR
  oben, Raman unten, gemeinsame Wellenzahlachse, beide auf ihre Spannweite skaliert). Enthält die IR-Rechnung
  **Raman-Aktivitäten** (ORCA „RAMAN SPECTRUM“, Gaussian `freq=raman` „Raman Activ“), zeigt das Raman-Bild auch das
  berechnete Spektrum („Raman-Rechnung“, gleiche Skalierung und Verbreiterung wie die IR-Rechnung; Aktivitäten, nicht in
  Intensitäten umgerechnet).

## HRMS-Tab

- Den **Word-Bericht** der Massenabteilung und/oder den Bruker-**Messordner** (`.d`) laden; was jeweils gelesen wird, steht
  in den Punkten unten. Mit Rohdaten zeigt der Tab:
  - ein **Chromatogramm** (Gesamt-Ionenstrom grau, Ionenstrom des gesuchten Ions rot, ± 10 ppm); das blaue Band ist der
    LC-Bereich für das Spektrum – mit der **Maus ziehen**, um einen anderen Bereich zu wählen;
  - das **gemittelte Spektrum** über diesen Bereich (Mittel der Linienspektren des Geräts) mit m/z an den größten Peaks
    und dem **berechneten Isotopenmuster** des Ions gespiegelt darunter (rot; Feinstruktur, die das TOF nicht trennt,
    z. B. ¹³C/¹⁵N, zusammengefasst); die gemessenen/berechneten Isotopenverhältnisse (M+1, M+2 …) stehen dabei;
  - **Peak anklicken**, um ihn als *found* zu übernehmen (neben dem Wert aus dem Bericht und dem Mittel über den LC-Peak).
- **PDF-Bericht** (Knopf oder auf den Tab HRMS ziehen): Ein Bruker-„Compound Spectrum SmartFormula Report“ wird
  automatisch gelesen – found ist der Wert der Tabellenzeile mit der Ionenformel des gewählten Ions, calc. rechnet
  Elucida selbst (Warnung, wenn calc. im Bericht abweicht). Aus anderen PDFs mit Textebene erscheinen die Zahlen bis
  ± 2 Da um calc. als **Kandidaten** mit ihrer Textzeile und der Abweichung in ppm; nichts ist vorgewählt, erst ein
  **Klick** übernimmt einen Wert („Aus PDF gewählt“), ein Wert gleich calc. ist markiert. Eingebettete Bilder des PDF
  sind unter **Bild aus PDF** als Abbildung wählbar (unverändert, die Unterschrift sagt „image from the instrument
  report“; ganze Seiten und Logos nie). Kopfdaten (Probe, Pfad, Bearbeiter) werden nie übernommen. PDFs ohne
  Textebene (Scans) werden abgelehnt.
- **Manuell (m/z):** found von Hand, immer verfügbar und als „Manuell“ gekennzeichnet; leeren nimmt den Wert zurück.
- Export: Spektrum als Abbildung (PDF/SVG/PNG; mit Bild aus dem PDF dieses als PNG), `…_sticks.csv` (gemessen und berechnet), `…_check.csv` (Prüftabelle) und `…_SI.txt`.
- **Prüfung gegen 5 ppm** (Angewandte: hohe Auflösung = 5 ppm): eine Tabelle unter *found* zeigt Ion, calc., found,
  Abweichung in ppm und den Status (über 5 ppm in der Warnfarbe); oben rechts stehen *found* und die Abweichung als
  Kacheln.
- Ältere Verbindungen: Die MS-Daten aus dem früheren Tab IR + MS werden automatisch übernommen.

## UV-Vis-(ε)-Tab

Molare Absorptionskoeffizienten (ε) aus UV-Vis-Verdünnungsreihen (Lambert-Beer: A/d gegen c) mit Standardfehler und
95-%-Konfidenzintervall, dazu eine Abbildung im Origin-Stil: Spektren, λ/ε-Labels an den Banden, ein Inset mit den
linearen Regressionen und R², die Struktur und ein freigestelltes Foto der Küvette.

1. **Daten öffnen:** Datei → Messdaten öffnen, oder Dateien ins Fenster ziehen. Unterstützt werden
   Cary-CSV/TXT-Exporte und die gerätenahen **.DSW/.BSW**-Dateien. **Mehrere Dateien auf einmal**
   (z. B. jede Konzentration einzeln gemessen) werden zu einem Datensatz zusammengeführt.
2. **Konzentrationen:** Die Konzentrationen werden aus den Probennamen gelesen, z. B.
   `ABC-1-0p5mgml_THF` → Serie `ABC-1`, 0,5 mg/mL. Erkannt werden
   `mgml`/`mg_ml`/`mg/ml`, `mM`, `uM`/`µM`; `p` steht für das Dezimalkomma.
   - Stehen keine Konzentrationen im Namen (z. B. `c0` … `c4`) oder ist die Zahl unklar (führende Null wie `05mgml`), klappt in der Karte **Daten** der Bereich **Konzentrationen eingeben** auf (kein eigenes Fenster).
     Die **Einheit** (mM, µM, mg mL⁻¹, M) muss ausdrücklich gewählt werden, es ist nichts vorbelegt; die Werte gelten, sobald sie gewählt ist.
   - Unter **Messungen** lässt sich jede Konzentration einzeln abwählen: Sie fehlt dann in Bild, Fit, Tabellen und SI, die Datei bleibt unverändert.
     Das Farbfeld daneben gibt der Kurve eine eigene Farbe (**Farben zurücksetzen** nimmt alle zurück). **Konzentrationen farbig** (Schritt Darstellung)
     färbt die übrigen nach Konzentration; die **Legende** dazu ist ein eigener Schalter und steht nur auf Wunsch im Bild.
   - „Verdünnungsreihe ausfüllen“ setzt in die markierten Zeilen (oder alle) von oben nach unten Start, Start/Faktor, … ein.
     Der Startwert gehört immer zur **obersten** markierten Zeile (meist die Stammlösung).
   - Proben ohne Wert, z. B. eine Blindprobe, werden ignoriert.
   - Über die Spalte „Serie“ lassen sich mehrere Verbindungen in einer Datei trennen.
   - Später ändern: denselben Bereich aufklappen.
3. **Verbindung (je Serie):**
   - **Struktur:** CDXML, SVG, PDF oder eine Bilddatei. Bei CDXML wird die **Molmasse automatisch
     berechnet** (Isotope wie D eingeschlossen), die Summenformel wird zur Kontrolle angezeigt.
     Damit die Zeichnung **exakt wie in ChemDraw** aussieht, die Struktur in ChemDraw zusätzlich
     als SVG, PDF oder PNG mit gleichem Namen neben die CDXML speichern (z. B. `6g.cdxml` +
     `6g.svg`). Die Zeichnung kommt dann unverändert aus dieser Datei, die Molmasse aus der CDXML.
     Ohne eine solche Datei wird die Struktur neu gezeichnet (ACS-1996-Stil) und kann von ChemDraw
     abweichen.
   - **Küvettenfoto:** HEIC (iPhone), JPG, PNG und weitere. Der Hintergrund wird automatisch entfernt.
   - **Farbe in Lösung (Vorhersage, optional):** aus dem Spektrum berechnet – Transmission 10^(−A) unter
     Tageslicht, CIE-1931-Farbmetrik, als Farbfeld unter dem Foto. Konzentration und Schichtdicke sind
     wählbar (Lambert-Beer; Standard: höchste gemessene Konzentration in 1 cm). Fluoreszenz und Streuung
     bleiben unberücksichtigt, Bildschirme sind nicht kalibriert; nur Anzeige, nicht in der Abbildung.
     Beim ersten Mal bietet die App einen einmaligen Download des KI-Modells an (~180 MB).
   - **Molmasse:** nur bei Konzentrationen in mg/mL nötig. Wird aus der CDXML übernommen, sonst von
     Hand eintragen. Ohne Molmasse gibt das Tool den spezifischen Absorptionskoeffizienten *a* in
     L g⁻¹ cm⁻¹ statt ε aus, und das Feld wird rot markiert. Bei mM/µM wird die Molmasse nicht verwendet.
4. **Auswertung:** Schichtdicke und Fit-Cutoff eintragen. Banden werden automatisch gefunden;
   zusätzliche Banden (z. B. Schultern) lassen sich als Liste eintragen („zusätzlich zu den
   automatisch gefundenen“ behält beide), optional mit Indizes **λ₁/ε₁ …** an den Labels, und **„Schultern automatisch suchen“** ergänzt Schultern
   (in der Abbildung optional mit „(sh)“ markiert). In der Ergebnistabelle entscheidet das Häkchen vor λ, ob eine Bande im Bild
   erscheint, und ein Doppelklick auf **„Cutoff A“** setzt einen eigenen Cutoff für diese Bande
   (z. B. um einen Punkt knapp über A = 1 mitzunehmen). Banden mit eigenem Cutoff sind farbig
   hinterlegt; optional zeigt das Inset ausgeschlossene Punkte als offene Symbole.
5. **Layout:**
   - **Mit der Maus ziehen:** Inset, Struktur, Küvette und jedes λ/ε-Label lassen sich verschieben.
   - **Mausrad bzw. Trackpad** über Inset oder Bild ändert die Größe. Alternativ die Felder „Größe [% Plotbreite]“ nutzen.
   - **Maus über den Spektren:** Eine Einblendung unten rechts zeigt λ und A des nächsten Messpunkts (und seine
     Konzentration), in der Vorschau mit rotem Kreis markiert (nicht im Export) – praktisch zum Prüfen der
     Daten. **Doppelklick** auf einen Punkt fügt seine Wellenlänge als Bande hinzu, erneuter Doppelklick
     entfernt sie. TD-DFT- und Fluoreszenz-Tab zeigen λ und den gezeichneten Wert genauso an.
   - **Zurücksetzen ▾** → „Layout zurücksetzen“ stellt die automatische Anordnung wieder her; „Darstellung
     zurücksetzen“ setzt nur das Aussehen der Abbildung auf Standard (Farben, Achsen, Beschriftungen …). Nichts
     Wissenschaftliches ändert sich: Daten, Auswertung (Bereiche, Basislinie, Fit, Schwellen, Auswahl), Angaben zur
     Messung, Bildunterschrift und Exportgröße bleiben, ebenso jede Zahl in Tabellen, Kacheln, Methodentext und SI. Wo
     der Achsenbereich auch die Auswertung begrenzt (hier: Peaksuche nur im gezeigten Bereich), bleibt er ebenfalls.
     Rückgängig holt alles zurück. X-Ray und DFT haben zusätzlich „Auf Standard“ neben „Startansicht“ (Stil, Ellipsoide,
     Bindungsdicke, Labels …; Fehlordnung und ausgeblendete Atome/Fragmente bleiben).
6. **Exportieren:** Datei → Exportieren (Strg+E) oder die Zeile im Tab **Export**. Das schreibt die dort gewählten Formate (PDF/SVG/PNG),
   `<Serie>_results.csv` und den Excel-Report für **alle** Serien in die Verbindung (siehe unten).

Text und Sichtbarkeit einzelner λ/ε-Labels ändert die Karte **Beschriftungen im Bild** (siehe dort); im Bild
ausgeblendete Labels bleiben anders als abgewählte Banden in Tabelle und SI-Zeile.

### Was bei der Auswertung automatisch passiert

- **Basislinie** („automatisch (Reihe)“, Standard): Das Fenster liegt dort, wo die konzentrierteste
  Probe am wenigsten absorbiert. Abgezogen wird nur der Teil des Fensterwerts, der *nicht* mit der
  Konzentration skaliert (Geräte- bzw. Küvettenoffset). Ein zu c proportionaler Rest gilt als echte
  Absorption und bleibt erhalten. „automatisch (einfach)“ zieht den kompletten Fensterwert ab.
  Die Basislinie nutzt immer den vollen Datenbereich, unabhängig vom dargestellten λ-Bereich.
- **Fit-Cutoff:** Punkte oberhalb des Cutoffs (Standard A = 1,0) gehen nicht in den Fit ein.
- **Banden:** automatisch im dargestellten λ-Bereich gesucht oder als Liste vorgegeben.
- **λ-Labels** stehen knapp über ihrer eigenen Bande, wenn dort Platz ist (auch in SEC und Fluoreszenz), sonst in
  einer Reihe oben. Inset, Struktur und Foto liegen wie ohne das; stünden die Labels dann nicht nach λ von links nach
  rechts oder auf der Legende, nimmt die ganze Abbildung die Reihe. Ein gezogenes Label bleibt, wo es ist.
- **Rundung:** ε (M⁻¹ cm⁻¹) und seine Fehler erscheinen ganzzahlig (z. B. 7264 ± 318), gleich in Tabelle, Bild,
  SI-Zeile, Methodentext und Excel-Bericht; der spezifische Koeffizient a wird auf die Genauigkeit seines
  Standardfehlers gerundet. Die Ergebnis-CSV enthält die vollen Werte.
- **Konventionen:** Gerundet wird kaufmännisch (7264,5 → 7265). R² ist auch beim Fit durch den Ursprung auf den
  Mittelwert bezogen (1 − RSS/SST); Excel-LINEST ohne Konstante nennt dort einen anderen, größeren Wert.
- **Warnungen** (Ergebnistabelle und Protokoll): weniger als 4 Fitpunkte, signifikanter
  Achsenabschnitt (> t(0,975; n−2)·SE), R² unter der Schwelle (Standard 0,98, einstellbar unter Auswertung →
  „min. R² fürs Bild“; 0 = alle zeigen; die Bande bleibt in Tabelle – R²-Zelle rot markiert –, CSV und
  Excel-Report, erscheint aber nicht im Bild), weniger als 3 Punkte (dann gar kein ε). Bei 4 Punkten
  sagt R² allein wenig: vor dem Absenken der Schwelle das 95-%-Konfidenzintervall im Excel-Report prüfen.
  R² steht überall mit zwei Nachkommastellen; die Stellenzahl lässt sich unter Auswertung → Erweitert → „R²-Stellen“
  wählen (gilt für alle Tabs der Verbindung; CSV und Excel-Report behalten den vollen Wert).

### Excel-Report

Für jede Serie entsteht `<Serie>_report.xlsx` mit drei Blättern:

- **Ergebnisse:** eine Tabelle wie in der App (λ, ε ± SE, 95-%-Konfidenzintervall, R², n, Hinweise). Daneben steht
  ε noch einmal, unabhängig mit Excel-Formeln nachgerechnet. Darunter zwei Diagramme im Stil der Abbildung (Spektren
  mit denselben Farben, Achsen und Bereichen; A/d gegen c mit Regressionsgeraden) und die Angaben zur Messung
  (Einheit, Schichtdicke, Molmasse, Modell, Cutoff, Basislinienfenster, Messdateien).
- **Rechnung:** alle Banden nebeneinander. Oben die Messpunkte (A, A/d, „im Fit“), darunter die Regression als
  **Excel-Formeln**: zuerst das Ergebnis (n, m, b, R², ε, SE, Konfidenzintervall), grau darunter die Zwischenwerte
  (x̄, ȳ, Sxx, Sxy, RSS, s, SE(m), SE(b), t). Die gelben Zellen „im Fit“ (1 oder 0) lassen sich ändern, Excel rechnet
  die Bande und das Diagramm neu.
- **Spektren:** A(λ) aller Proben, basislinienkorrigiert und roh, mit dem je Probe abgezogenen Offset.

Die Zellen enthalten den vollen Wert; nur das Zahlenformat rundet wie in der App.

## TD-DFT-Tab

Gemessene Spektren einer Verbindung mit ihrer Rechnung (TD-DFT, ESD) in einer Abbildung vergleichen; mehrere
Messungen derselben Verbindung (anderes Lösungsmittel, andere Konzentration, vor und nach einer Reaktion) sind erlaubt.
Spektren **verschiedener Verbindungen** vergleicht das Projekt (Projektseite → **Vergleich**: normiert auf eine Bande,
Strukturen in Kurvenfarbe, auch in der Gesamt-SI); die Zeile „Vergleich“ im Schritt Daten führt dorthin. Bis 1.1 hieß
der Tab „UV-Vis-Overlay“; ältere Abbildungen mit einer Struktur je Spektrum bleiben unverändert erhalten (Hinweis im
Tab), neu einrichten lässt sich das hier nicht mehr. Stapeln bleibt (Spektren derselben Verbindung übereinander).

- **Messung…** fügt Spektren aus CSV/TXT/DSW/BSW-Dateien hinzu (ein Eintrag pro Probe);
  **TD-DFT…** fügt Ausgabedateien von ORCA (4–6) oder Gaussian hinzu; **ESD…** fügt ORCA-ESD(ABS)-Spektren hinzu
  (`.spectrum`, nur normiert; x-Einheit aus `%ESD UNIT` der Eingabe daneben oder aus dem Wertebereich, änderbar).
- **Aus Tabs ▾** übernimmt ε-Serien des ε-Tabs (verknüpft, Messung wählbar) und TD-DFT-Rechnungen des DFT-Tabs.
- **SEC…** übernimmt Spektren aus dem SEC-Tab, z. B. um eine Reduktion oder Oxidation mit dem isolierten UV-Vis-Spektrum
  und TD-DFT zu vergleichen. Als **Serie** (alle Spektren oder nur Anfang und Ende, Bereich nach Potential) wird alles
  mit **einem gemeinsamen Faktor** auf das Startspektrum normiert, Intensitätsverhältnisse und isosbestische Punkte
  bleiben also erhalten; Zwischenspektren grau, Anfang blau, Ende rot, Legende mit den Potentialen. **Einzelne
  Spektren** werden jedes für sich normiert (Formvergleich). SEC wird nie als ε gezeigt: Schichtdicke und umgesetzte
  Konzentration der Dünnschichtzelle sind nicht genau bekannt.
- TD-DFT-Übergänge werden mit Gaußfunktionen in der Energie verbreitert (Breite FWHM und eine
  empirische Energieverschiebung pro Rechnung einstellbar, Standard 0,3 eV); ε folgt aus den
  Oszillatorstärken (ε(ν̃) = 1,306·10⁸ · Σ f/σ · exp(−((ν̃−ν̃ᵢ)/σ)²), wie in GaussView). Übergänge
  lassen sich als Striche anzeigen.
- **y-Größe**: *normiert* – jedes Spektrum wird auf sein Maximum im Normierungsbereich skaliert (global oder pro
  Spektrum mit eigenem Bereich, z. B. wenn die berechnete Bande verschoben ist), **ε [10³ M⁻¹ cm⁻¹]** – gemessene
  Spektren brauchen dann Konzentration (bei mg/mL auch Molmasse) und Schichtdicke, oder **Absorbanz** wie gemessen
  (Messungen und SEC, ohne TD-DFT). Der automatische y-Bereich enthält immer alle Kurven.
- Pro Spektrum: Farbe, Name, **Linienart und -stärke**, **Skalierungsfaktor und vertikaler Versatz**
  (z. B. für gestapelte Spektren); **Reihenfolge** mit ↑/↓ (auch die der Legende).
- ORCA-Rechnungen mit **Spin-Bahn-Kopplung**: pro Rechnung „mit SOC“ oder „ohne SOC“ wählbar.
- **Farbe in Lösung** je TD-DFT-Rechnung (Details des Eintrags): A = ε·c·d mit der eingestellten Verbreiterung,
  Standard 1 mM in 1 cm – nur qualitativ, TD-DFT-Energien liegen oft 0,2–0,3 eV daneben.
- **Triplett-Zustände** (ohne SOC, f = 0) lassen sich als gestrichelte Marken fester Höhe anzeigen; sie
  tragen nicht zur Kurve bei (ORCA 4–6, Gaussian).
- Rechnungen **kombinieren**: zwei oder mehr TD-DFT-Einträge markieren (Strg/Shift-Klick) → „Kombinieren“.
  Die Übergänge werden zusammengeführt und dann gemeinsam verbreitert; ein Gewicht pro Rechnung (Standard
  1 = Summe, z. B. 0,7/0,3 für Konformere). Die Rechnungen sollten auf demselben Theorieniveau sein; gleiche
  Zustände in beiden Rechnungen lösen eine Warnung aus (sie würden doppelt zählen).
- **TD-DFT-Normierung:** Kurve und Striche haben immer denselben Skalierungsfaktor (jeder Strich ist
  die Höhe seiner eigenen Gaußbande, die Kurve ist deren Summe). Bezug: „Kurvenmaximum = 1“ oder
  „stärkster Übergang = 1“; „Kurvenmaximum = 1, rechts zusätzlich f“ zeigt die Oszillatorstärke als zweite Skala
  derselben Striche (entfällt mit Hinweis, wenn die Rechnungen verschiedene Maßstäbe haben).
- Struktur mit einstellbarer Größe; die Legende wird in freie Fläche gesetzt und lässt sich verschieben.
- **Gestapelt** (wie in Papern üblich): Die Kurven werden in Listenreihenfolge um einen gemeinsamen
  Abstand senkrecht versetzt (oben in der Liste = oberste Kurve). „Gleiche Stapelebene wie die Kurve
  darüber“ hält z. B. eine TD-DFT-Kurve auf der Ebene ihrer Messung. Die **y-Achse** lässt sich mit
  Zahlen, ohne Zahlen und Teilstriche (Standard beim Stapeln – bei versetzten Kurven wären die Zahlen
  irreführend) oder gar nicht anzeigen. Optional stehen die **Namen direkt an den Kurven** statt in einer
  Legende, und eine gestrichelte Nulllinie markiert jede Ebene.
- **Bildunterschrift** (SI) nach den sichtbaren Einträgen: „Experimental and calculated (TD-DFT) UV-Vis spectra of …“,
  nur gemessene Spektren „UV-Vis spectra of …“, nur Rechnungen „Calculated (TD-DFT) UV-Vis spectra of …“.
- **Export:** neben Abbildung und Kurven (`…_data.csv`) die TD-DFT-Übergänge maschinenlesbar (`…_transitions.csv`:
  Zustand, E in eV, λ in nm, Oszillatorstärke, Multiplizität, wie gelesen – ohne Verschiebung und Gewicht der Abbildung).
- **Anregungen** (Seite neben der Abbildung, Karte „TD-DFT-Tabelle“ im Schritt Auswertung): Tabelle der TD-DFT-Zustände
  aller sichtbaren Rechnungen – Zustand (S1, T1 … wie gelesen), E in eV, λ in nm (ganzzahlig), f und die Hauptanteile
  (Orbital → Orbital, Gewicht in %, je eine Zeile). Die Namen relativ zu HOMO/LUMO folgen aus den Besetzungen der
  Ausgabe. Gewichte: ORCA wie unter den angeregten Zuständen gedruckt; Gaussian 2c² aus den gedruckten Koeffizienten c
  (geschlossene Schale) bzw. c² je Spin (offene Schale); Abregungen zählen nicht. Ausgaben ohne Zusammensetzung der
  Zustände (alte Tabellen, SOC, Spin-Flip) ergeben die Tabelle ohne Anteile. Einstellbar: Schwelle für f („aus“ = alle
  Zustände), Schwelle der Anteile, nur Zustände, deren Strich im gezeigten λ-Bereich liegt, und „In die SI (Word)“
  (Tabelle nach den Abbildungen, in der Gesamt-SI im Kapitel Rechnungen). Die Werte sind die der Rechnung, ohne die
  Verschiebung der Abbildung. Der Export `…_transitions.csv` enthält zusätzlich alle gedruckten Anteile (ohne Schwelle)
  und die Rechenregel.
- **Natürliche Übergangsorbitale (NTO):** Karte „Übergangsorbitale (NTO)“ (Schritt Auswertung) und Seite **NTO**.
  Einen Zustand der sichtbaren TD-DFT-Rechnungen wählen, dann seine NTO-Datei laden: ORCA schreibt mit
  `%tddft DoNTO true end` je Zustand `name.sN.nto`; mit orca_2mkl (Option `-molden`) in Molden umwandeln. Paare und
  Gewichte kommen aus dem Block „NATURAL TRANSITION ORBITALS FOR STATE N“ der TD-DFT-Ausgabe (Zuordnung über die
  Energie; ohne diesen Block wird die Molden-Datei abgelehnt). Alternativ zwei Cubes eines Paars (Loch = kleinere
  MO-Nummer), z. B. aus orca_plot oder Gaussian cubegen (`Pop=(NTO,SaveNTO)`); das Gewicht steht im NTO-Block, wenn er
  dieses Paar nennt, sonst wie in der Rechnung angegeben eintragen oder leer lassen. „Paare ab“ (Molden), Isowert
  (leer = 80 % der Orbitaldichte) und „In die SI“ (Abbildung je Zustand mit Unterschrift, auch im Export als
  `…_NTO_S1`).

## UV-Vis-Kinetik-Tab

Wie sich die Spektren einer Lösung über die Zeit ändern – Stabilität über Tage oder eine Reaktion:

- **Dateien hinzufügen** (mehrere auf einmal, später weitere, z. B. eine Datei je Tag): jedes Spektrum wird eine
  Zeile mit Name (umbenennbar), **Reihe** und **Aufnahmezeit**. Die Zeit stammt nur aus der Messdatei (Cary-CSV:
  „Collection Time“ je Probe, nach der Reihenfolge der Spalten zugeordnet; amerikanisches und deutsches Datumsformat),
  nie aus dem Dateinamen oder dem Dateidatum. .DSW/.BSW enthalten keine Zeit je Spektrum: sie erscheinen nur in der
  Ansicht „Spektren über die Zeit“, mit ihrem Namen. Gerätebasislinien („Baseline 100%T/0%T“) werden nicht angeboten.
- Die **Reihe** (z. B. die Konzentration) ist nur vorbelegt, wenn der Probenname eine Konzentration eindeutig nennt
  („…-20uM“); sonst trägt man sie ein – in der Tabelle oder für mehrere markierte Zeilen auf einmal unter „Auswahl“.
  Zeilen ohne Reihe werden nicht ausgewertet (Hinweis). Gesättigte Spektren erkennt das Programm nicht: Häkchen
  entfernen.
- **Ansicht** (Schritt Auswertung): „Spektren über die Zeit“ zeigt eine Reihe im Farbverlauf, beschriftet mit der Zeit
  seit ihrem ersten Spektrum. „Absorbanz gegen Zeit“ zeigt für jede Reihe die Absorbanz bei der **Wellenlänge**
  (ganzzahlig; auto = Maximum des ersten Spektrums) gegen die Zeit seit ihrem ersten Spektrum; mit **Maximum ±** das
  Maximum im Bereich λ ± n nm statt des Werts genau bei λ. y-Achse wie gemessen oder relativ zum ersten Spektrum in %,
  Zeiteinheit min/h/d oder auto (nach der Dauer).
- **Zerfall fitten**: je Reihe A(t) = A0·exp(−k·t) an die gemessenen Absorbanzen (kleinste Quadrate, wie die isothermen
  EPR-Zerfälle) mit 95-%-Intervall von k und Halbwertszeit t½ = ln 2/k; ab drei Punkten. Steigt eine Reihe, ist k < 0
  und es gibt keine Halbwertszeit.
- Keine Korrektur für Schichtdicke oder Konzentration: Absorbanz wie gemessen.
- Rechts: Abbildung, **Ergebnisse** (Tabelle je Messpunkt, Zusammenfassung je Reihe: erster und letzter Wert, Rest in
  %, Dauer, k und t½), SI-Text. Export: Abbildung, `…_results.csv` (Reihe, Name, Zeit, A, relativ; bis 1.3 `…_kinetics.csv`) und `…_summary.csv`.

### Titration

Spektren gegen die Äquivalente eines zugegebenen Reagenz (z. B. Oxidationsmittel), im selben Tab:

- Spalte **Äq.** der Tabelle: Äquivalente je Spektrum, von Hand oder beim Laden vorgeschlagen, wenn der Probenname
  (bei einer Datei mit nur einem Spektrum auch der Dateiname) sie eindeutig nennt („…_0.5eq“, „1,5 equiv“, „0p25eq“).
  Zeilen mit Äquivalenten brauchen keine Reihe.
- Ansicht **Titration: Spektren**: alle angehakten Zeilen mit Äquivalenten im Farbverlauf nach den Äquivalenten,
  Legende mit den Äquivalenten. **Isosbestische Punkte** werden nur markiert (Kreis), wo alle Spektren innerhalb der
  Toleranz übereinstimmen (Spannweite der Absorbanz max − min, Standard 0,01) und sich die Änderung zwischen erstem und
  letztem Spektrum dort umkehrt; sonst gibt es keinen (nichts geraten). Ihre Wellenlängen stehen in der Unterschrift,
  der Kachel und den Ergebnissen.
- Ansicht **Titration: Absorbanz gegen Äq.**: Absorbanz bei der Wellenlänge (oder Maximum in λ ± n nm) gegen die
  Äquivalente.
- Absorbanz wie gemessen, keine Verdünnungskorrektur, keine Bindungskonstanten. Feld **Reagenz** der Bildunterschrift
  nennt das Reagenz. Im SI-Export kommen beide Titrationsbilder mit eigener Unterschrift; Export `…_titration.csv`
  (Äquivalente, Name, A).

## Fluoreszenz-Tab

Absorption und Emission in einer Abbildung, wie in Publikationen üblich:

- Absorption (beliebige UV-Vis-Datei) und Emission (Cary-Eclipse-CSV oder .FBSW), λex wird aus der
  Emissionsdatei übernommen; beide auf 1
  normiert; die Absorption auf das Maximum in der „Bande von Interesse“.
- Labels mit λabs des Absorptionsmaximums (plus ε, wenn eingetragen) und λem des Emissionsmaximums.
- **Stokes-Verschiebung** Δν̃ = 1/λabs − 1/λem in cm⁻¹ (auf 10 cm⁻¹ gerundet, genauer sind Peaklagen aus
  Spektren mit ~1 nm Raster nicht) und in nm; optional auch im Bild am Emissionslabel.
- **Absorbanz bei λex** mit Warnung ab A = 0,1: Dann verzerrt der Innenfiltereffekt das Emissionsspektrum
  und senkt Quantenausbeuten (nur relevant, wenn beides an derselben Lösung gemessen wurde).
- Streulicht bei λex und 2·λex optional ausblenden.
- Zwei Küvettenfotos (Tageslicht und unter UV) werden mit Pfeil und Anregungswellenlänge
  kombiniert; beim UV-Foto ist die Freistellung standardmäßig aus (dunkler Hintergrund bleibt).
- Struktur wie im ε-Tab.
- **Anregungsspektrum** (Cary-Eclipse-CSV oder .FBSW) zusätzlich, auf 1 normiert und strichpunktiert in eigener Farbe;
  die Detektionswellenlänge λem trägt man ein (nur für die Bildunterschrift).

### Lebensdauer und Kennwerte

- **Abklingkurve** und optional **IRF** (Karte „Abklingkurve“ im Schritt Daten) als Textdatei: erste Spalte Zeit,
  zweite Intensität; Kopfzeilen werden übersprungen, Trenner Tab, Semikolon, Komma oder Leerzeichen, Dezimalpunkt oder
  -komma. Die Zeiteinheit (ps, ns, µs) wird aus dem Spaltenkopf übernommen, sonst gewählt. Herstellerformate
  (PicoQuant, Edinburgh, Horiba) liest das Programm noch nicht: als Text exportieren. λex und λem der Messung stehen
  in der Bildunterschrift.
- **Fit** (Karte „Lebensdauer“, Schritt Auswertung): I(t) = Σ A_i·exp(−t/τ_i) + B mit ein oder zwei Exponentialen und
  konstantem Untergrund B. Mit IRF wird die IRF (Fläche 1, Verschiebung mitgefittet) über die ganze Kurve mit den
  Exponentialen gefaltet; ohne IRF beginnt der Fit eine wählbare Zeit nach dem Maximum (Schwanzfit, keine Entfaltung –
  der Methodentext sagt das). Sind die Werte ganze Zahlen (Zählraten), wird mit Poisson-Gewichten 1/max(N, 1)
  gefittet und das reduzierte χ² angegeben; sonst ungewichtet und ohne χ². 95-%-Intervalle von τ aus der Kovarianz
  des Fits.
- Reiter **Abklingkurve**: Kurve logarithmisch mit Fit und IRF, darunter die (gewichteten) Residuen; Tabellen je
  Komponente (τ, 95 %, A, Anteil an der Intensität) und mit amplitudengewichteter (ΣA_iτ_i/ΣA_i) und
  intensitätsgewichteter (ΣA_iτ_i²/ΣA_iτ_i) mittlerer Lebensdauer, Untergrund, IRF-Versatz, χ² und Punktzahl. Bei einer
  negativen Amplitude (Anstieg) gibt es keine mittlere Lebensdauer.
- Reiter **Kennwerte**: λabs, ε, λem, Φ, τ, k_r = Φ/τ und k_nr = (1 − Φ)/τ, nur aus vorhandenen Angaben (leere Spalten
  entfallen). Φ trägt man ein (0 < Φ ≤ 1 oder in %); es wird hier nicht bestimmt. Bei zwei Exponentialen wählt man, welche
  mittlere Lebensdauer für k_r/k_nr gilt; ein Hinweis unter der Tabelle nennt sie.
- SI-Export: zweite Abbildung (Abklingkurve mit Residuen) mit eigener Unterschrift; Methodentext mit Modell, Gewichtung,
  Intervallen und Ergebnissen; Export zusätzlich `…_decay` (Bild), `…_decay.csv` (Zeit, Messwert, Fit, Residuum), `…_lifetime_fit.csv`, `…_lifetime_summary.csv` und `…_photophysics.csv`.


## CV-Tab (Cyclovoltammetrie)

- Liest **Gamry-.DTA**-Dateien (Framework 6/7, beide Tabellenvarianten); Scanrate, Elektrodenfläche und
  Zyklen kommen aus der Datei. Mehrere Messungen (z. B. eine Scanraten-Serie) werden überlagert, optional mit
  Farbverlauf blau → rot nach Scanrate, Pfeil für die Scanrichtung und E½ im Bild. Abgelegte .DTA-Dateien werden
  am Inhalt erkannt: Gamry-CV-Dateien gehen in den CV-Tab, Gamry-Lade-/Entladedateien in H-Cell, Bruker-BES3T-Dateien
  (gleiche Endung) in EPR; der offene Tab bleibt, Einblendung mit „Anzeigen“ und Punkt am Ziel-Tab.
- **Redoxpaare** werden in Potentialfenstern ausgewertet („Vorschlag“ schlägt sie vor, die Fenster sind
  änderbar): E_pa (Strommaximum im Hinlauf), E_pc (Minimum im Rücklauf), E½, ΔE_p, i_pa, i_pc und das
  Peakstromverhältnis nach **Nicholson** (berücksichtigt den abklingenden Strom des Hinlaufs; ≈ 1 = chemisch
  reversibel). Peaks am Fensterrand werden rot markiert, ebenso Fenster mit **zwei Wellen** (mehr als ein Maximum im
  Hinlauf oder Minimum im Rücklauf): solche Zeilen zählen nirgends (Regressionen, Beschriftung, Vergleich). „Vorschlag“
  endet deshalb jedes Fenster höchstens auf halbem Weg zur Nachbarwelle (sonst 0,25 V). Als zweite Welle zählt nur, was
  dieselbe Mindesthöhe wie beim Vorschlag hat (3 % des größten Stroms der Kurve); kleine Buckel und Rauschen nicht. In der
  Ergebnistabelle nennt der Name die Scanrate („50 mV s⁻¹“; ein eigener Name ohne sie bekommt sie angehängt), bei wenig
  Platz wird der Name gekürzt (voller Name im Tooltip); die Kacheln E½/ΔE_p zeigen die erste gültige Zeile.
- **Basislinie** (Standard an): i_p gegen eine Gerade durch den Strom vor dem Hinpeak (Ladestrom + Untergrund),
  extrapoliert unter den Peak; für den Rückpeak um den Sprung des Ladestroms am Umkehrpunkt (2·C·v) verschoben, den
  abklingenden Hinlaufstrom korrigiert Nicholson. Abstand zum Peak einstellbar (Standard 0,20 V; vor Version 1.1 angelegte Verbindungen behalten 0,15 V), Basislinien optional im
  Bild. Peakpotentiale bleiben unverändert. Fehlt Vorlauf im Fenster, wird das markiert und die Messung nicht in die
  Regressionen genommen.
- Ab 3 Scanraten je Gruppe und Paar: Regression **i_p gegen √v** (Randles-Ševčík) und **log i_p gegen log v**
  (Steigung 0,5 = diffusionskontrolliert, 1 = adsorbiert), jeweils mit **95-%-Konfidenzintervall**; im Reiter
  „Ergebnisse“ als zweite Tabelle unter den Peakdaten (eine Zeile je Paar und Peak; N = Zahl der Messungen in der
  Regression). D und k⁰ stehen darunter in einer eigenen kleinen Tabelle **je Paar** mit kurzer Bewertung („D: Ergebnis“,
  „k⁰: scheinbar“ …), scheinbare Werte in der Warnfarbe; die Gründe im Einzelnen zeigt der Tooltip der Bewertung.
  Warnungen stehen darunter als eine kurze Zeile je Art mit Anzahl (z. B. „Zwei Wellen im Fenster: 2 Zeile(n) nicht
  ausgewertet“), Einzelheiten im Tooltip der Zeile.
- **Diffusionskoeffizient** (Schritt Auswertung, Karte „Diffusion und k⁰“): mit Elektronenzahl n, Fläche A der
  Arbeitselektrode, Konzentration c und Temperatur rechnet das Programm D aus der Randles-Ševčík-Steigung des Hinpeaks
  (i_p = 0,4463·n·F·A·c·√(n·F·v·D/RT), reversibles, frei diffundierendes Paar). Ohne Fläche oder Konzentration gibt es
  kein D; die Fläche wird nie aus der Messdatei übernommen. Das Intervall trägt nur die Unsicherheit der Steigung,
  nicht die von Fläche und Konzentration. Ergebnis im Reiter Ergebnisse und im Methodentext. D gilt nur als Ergebnis,
  wenn ΔE_p bei **jeder** Scanrate höchstens 10 mV über ΔE_p des internen Standards liegt – aus derselben Messung oder
  aus einer eigenen Messung des Standards **mit derselben Scanrate** (nur dann vergleichbar: ΔE_p wächst mit v durch den
  iR-Abfall). Ohne Standard oder bei anderer Scanrate gilt 2,22·RT/(nF) + 10 mV (57 mV + 10 mV bei 25 °C); der
  Methodentext nennt, bei welchen Scanraten das so war. Sonst ist D nur „scheinbar“, mit den Scanraten, bei denen das Paar
  nicht reversibel ist (Tabelle, CSV, Methodentext).
- **k⁰** (dieselbe Karte): heterogene Standardgeschwindigkeitskonstante aus ΔE_p je Scanrate, mit D_O = D_R = D (das
  eingetragene „D für k⁰“, sonst der Randles-Ševčík-Wert des Paars). Für n·ΔE_p von 66–160 mV Nicholsons ψ in der
  Näherung von Lavagnini (Electroanalysis 2004, 16, 505); darüber Klingler–Kochi (J. Phys. Chem. 1981, 85, 1731), das
  den Durchtrittsfaktor α braucht (Feld „α (Klingler–Kochi)“, nie vorbelegt). Unter 66 mV gibt es keinen Wert (zu nah
  am reversiblen Fall). Angegeben wird nur der Bereich über die Scanraten, nie ±; an simulierten Kurven geprüft:
  −14 bis +17 % (Lavagnini), −7 bis +7 % (Klingler–Kochi). „(scheinbar)“, wenn eine Messung ohne iR-Kompensation
  aufgenommen wurde (Gamry-Datei, sonst Projektangabe), ΔE_p des internen Standards über der D-Schwelle liegt oder D aus
  einem nicht reversiblen Paar stammt; fällt k⁰ mit steigender Scanrate um mehr als 25 %, weist eine Warnung auf
  unkompensierten Widerstand hin.
- **Konventionen der CV-Rechnung:** Das Nicholson-Verhältnis rechnet mit basislinienkorrigierten Strömen (im Original
  gegen die Nulllinie) und streut auch bei ideal reversiblen Paaren um etwa ±3 %, je nach Umkehrpotential. Die
  Basislinie endet 0,20 V vor dem Peak; bei einer ideal reversiblen Welle liegen dort noch etwa 0,3 % des Peakstroms,
  i_p fällt dadurch höchstens 1 % zu klein aus (mit den früheren 0,15 V waren es 1–3 %, D entsprechend 2–6 %). Reicht
  der Vorlauf im Fenster dafür nicht, endet die Basislinie wie früher 0,15 V vor dem Peak; das Programm meldet es, i_p
  kann dann bis etwa 6 % zu klein sein. Die Vorgabe Ac₂Fc +0,49 V ist ein Wert für CH₂Cl₂
  (Connelly, Geiger, Chem. Rev. 1996, 96, 877); in anderen Lösungsmitteln den eigenen Wert eintragen. E½ ist nur bei
  gleichen Diffusionskoeffizienten beider Formen das Formalpotential.
- **Kopieren** (Karte „Methodentext“ im Reiter SI-Text): englischer Absatz zur Auswertung (Referenzierung, Peakbestimmung, Basislinie, Nicholson,
  Regressionen) zum Anhängen an den Aufbau-Absatz „Cyclic Voltammetry“ der SI, dazu die Ergebnisse je Redoxpaar.
- **Referenzierung:** wie gemessen (Referenzelektrode, z. B. Ag/AgNO₃), **intern** (Fc- oder Ac₂Fc-Paar in einer
  der Messungen; E½ der Referenz gegen Fc⁺/Fc ist änderbar – Vorgabe Ac₂Fc +0,49 V, mit eurer Literatur abgleichen)
  oder Verschiebung von Hand. Die Achse heißt dann „E [V vs. Fc⁰/⁺]“.
- **Referenz per Klick:** In der Messungsliste die Messung anhaken, die den Standard enthält (Spalte „Fc“ bzw. „Ac₂Fc“;
  eine je Reihe – mit mehreren Gruppen gilt das Häkchen für alle Messungen seiner Gruppe). Dann in der Karte Referenz
  **Referenz setzen** und in der Vorschau nahe den Oxidations- und den Reduktionspeak des Standards klicken: jeder Klick
  springt auf den Peak in ±80 mV um die Klickstelle (dieselbe Parabel wie bei den Paaren), E½ = Mittelwert, und alle
  Kurven rücken sofort auf die Fc-Skala (E_Fc = E − (E½,Ref − E°Ref)). Gespeichert wird ein Referenzfenster wie ein
  eingetipptes (eingetippte Fenster alter Verbindungen gelten weiter); ein Schritt zum Rückgängigmachen, **Esc** bricht
  ab. Die Referenzmessung muss eingeblendet sein. Im Bild steht über dem Oxidationspeak des Standards seine **Struktur**
  (Ferrocen bzw. 1,1'-Diacetylferrocen als Sandwich, in der Farbe seiner Kurve; Chip „Struktur des Standards“, Vorgabe
  an, aus = keine Markierung); die Bildunterschrift nennt den internen Standard ohnehin. Angehakte Messungen dienen nur
  als Referenz und gehen nicht in die Scanraten-Analyse ein; fehlt dadurch eine Scanrate, sagt das ein Hinweis unter
  den Ergebnissen.
- **Referenz je Messung** („Referenz der ausgewählten Messung“): eigener interner Standard (auch das Fc/Ac₂Fc-Paar in
  derselben Datei, z. B. „mit Ac₂Fc“) oder eigene Verschiebung – nötig beim Lösungsmittelvergleich, jedes gegen seinen
  eigenen Standard. Die Fenster der Redoxpaare folgen der Referenz der jeweiligen Messung.
- **Gruppe** je Messung (z. B. das Lösungsmittel): Datenreihe in den Auftragungen gegen die Scanrate.
- **Struktur je Messung** (optional in Kurvenfarbe) und **Beschriftung** wahlweise E½ je Paar oder **E_pa/E_pc als Zahl
  an den Peaks** (z. B. Probe und Ac₂Fc in einer Messung); y-Achse mit Zahlen, ohne oder ausgeblendet.
- **Gestapelte** CVs (Listenreihenfolge von oben nach unten, Abstand einstellbar, y-Achse ohne Zahlen) mit **E½ an jeder
  Kurve** neben ihrem anodischen Peak (E¹½, E²½ bei mehreren Paaren).
- Der **Pfeil der Messrichtung** steht oben links über den Kurven (Richtung aus der ersten Kurve; im CV-Stapel über der
  eigenen Kurve), lässt sich in der Abbildung ziehen, die Position bleibt gespeichert.
- **Auftragung:** Cyclovoltammogramm, **elektrochemische Reversibilität** (ΔE_p gegen v), **Randles-Ševčík** (i_pa und
  i_pc gegen √v oder v mit Ausgleichsgerade ab 3 Scanraten), **Diffusion** (log |i_p| gegen log v), **chemische Reversibilität**
  (i_r/i_f nach Nicholson gegen v, Linie bei 1) oder **Trumpet-Plot** (E_pa und E_pc gegen log v), eine Datenreihe je Gruppe.
  Hinweis: ΔE_p enthält auch den iR-Abfall (v. a. in THF); der Trumpet-Plot selbst wird nicht gefittet (k⁰ kommt aus
  ΔE_p, siehe oben).
- Strom wie aufgezeichnet (Gamry: IUPAC, anodisch positiv) oder invertiert; optional als Stromdichte.
- **Messbedingungen** (Schritt Daten): Arbeits- und Gegenelektrode, Spülgas, Gerät (Hersteller, Modell) und Politur
  der Arbeitselektrode; einmal eingegeben, für neue Verbindungen vorbelegt. Darunter steht, was aus den Messdateien
  kommt (Startpotential und Richtung des Scans, iR-Kompensation an/aus) und was für die Richtlinien von ACS und
  Angewandte noch fehlt. Die Bildunterschrift bleibt kurz: iR-Kompensation und Konvention der Auftragung (IUPAC oder
  polarographisch, je nach „US-Konvention“) nur, wenn sie nicht schon im Kapitelabsatz des Projekts stehen oder die
  Messung davon abweicht; Start und Richtung des Scans nur mit dem Chip **Start und Richtung** (Vorgabe aus). Der Messaufbau steht gesammelt in
  einem Anfangstext: gehört die Verbindung zu einem Projekt, wird er einmal auf der Projektseite unter **Angaben**
  erfasst (Karte **Cyclovoltammetrie: Messaufbau**: Gerät, Arbeitselektrode, Fläche, Politur, Gegen- und
  Referenzelektrode, Atmosphäre, iR-Kompensation, Konvention, weitere Angaben als freie Sätze) und steht als Fließtext
  in ganzen Sätzen in der Gesamt-SI als erster Absatz des Kapitels „Cyclic Voltammetry“ (leere Felder lassen ihren
  Satzteil weg; Fläche ohne Einheit in cm², „mm2“ wird zu mm²); die Karte im CV-Tab zeigt dann nur den Verweis und den Text. Ohne Projekt gelten die Felder der Karte,
  der Aufbau steht am Anfang des Methodentexts. Leere Felder erscheinen nirgends.
- **Pulsverfahren (DPV, Square-Wave):** Gamry-Dateien, deren Tabelle die Spalten „Vstep“ und „Idif“ nennt, lassen sich
  wie CV-Dateien laden: eine Kurve Differenzstrom gegen Potential, Achse ΔI, Unterschrift mit Verfahren und
  Pulsparametern aus der Datei. Peakpaare und Vorschub-Auswertungen gelten dafür nicht. Geprüft mit einer echten
  Square-Wave-Datei, noch nicht mit einer echten DPV-Datei; andere Tabellen werden abgelehnt.
- Export: Abbildung (PDF/SVG/PNG), `…_results.csv` mit allen Werten (Dateiname, Zyklus, Scanrate, ΔE_p des internen
  Standards, |E_p − E_p/2|, Kennzeichen für Fensterrand, zwei Wellen, kurze Basislinie und ungültiges Verhältnis, Gruppe,
  Referenzverschiebung, iR-Kompensations-Eintrag der Gamry-Datei, Ströme mit/ohne Basislinie, Ladestromsprung, T; leere
  Zelle = kein Wert), `…_rate_fits.csv` (je Paar und Peak: Steigungen und Achsenabschnitte mit Intervallen, R²,
  log-log-Steigung, D mit Grenzen und Status, k⁰-Bereich, Status und Verfahren) und `…_methods.txt` (SI-Text). Beide
  CSV-Dateien sind Maschinenformate: Komma als Trenner, Dezimalpunkt, UTF-8, englische ASCII-Köpfe „Name [Einheit]“
  (z. B. „E_pa [V]“, „v [mV s^-1]“) und volle Rohwerte, nicht die Stellen der Anzeige.

## SEC-Tab (Spektroelektrochemie)

- **Zusammengeführte UV/Vis/NIR-Exporte** (`Merged spectral data`, zwei Spalten: `*.Abs8.txt`, `*.Raw8.txt`): Der ganze
  Bereich wird gezeigt, in Dateireihenfolge; Absorbanz und Rohsignal werden in einer Serie nie gemischt und weder
  korrigiert noch geglättet. Diese Dateien enthalten **keine Zeiten**, die Serie läuft deshalb zunächst nach Nummer,
  ohne Potentiale und ohne A(E)- oder Nernst-Auswertung. Ein Potential gibt es nur aus dem, was du unter
  **Potentialzuordnung** bestätigst: Start + Intervall auf der Zeitachse der Potentiostat-Datei, Tabelle Nr. → Zeit oder
  Tabelle Nr. → Potential (für gehaltene Stufen, z. B. `1-31; 0.95`). Spektren außerhalb der Messung fallen weg, statt
  das Endpotential zu bekommen; die Herkunft der Zuordnung steht in Unterschrift und Methodentext. Lücken in den Nummern
  und Sprünge in den Dateizeiten werden gemeldet; Dateizeiten bestimmen nie ein Potential.
- Liest eine **Spektrenserie aus B&W-Tek-BWSpec**-Textexporten (Wellenlängen aus den Kalibrierkoeffizienten der
  Datei) und die **Gamry-.DTA**-Datei des Potentialscans. Jedes Spektrum bekommt sein Potential über die Uhrzeit
  (Spektrumzeit − Start der Gamry-Messung, plus einstellbarer Zeitversatz).
- **Spektrenserie:** erstes und letztes Spektrum hervorgehoben (blau/rot), die übrigen grau – oder Farbverlauf nach
  Potential; optional Differenzspektren (ΔA gegen das erste Spektrum) und Nullpunkt (Mittel 780–820 nm); λ-Labels in
  der Farbe des passenden Spektrums. Spektrenbereich wählbar (z. B. nur die erste Welle).
- **Zwischenspezies:** Ein oder mehrere Spektren dazwischen lassen sich grün hervorheben (weitere orange, violett,
  türkis), z. B. das Radikalkation zwischen Neutralverbindung (blau) und Dikation (rot) – Eingabe als Potential
  (Achsenskala, nächstliegendes Spektrum) oder ohne Potentialdatei als Nummer des Spektrums. Die Unterschrift lautet dann
  „Color coding: **neutral** (blue), **radical cation** (green), **dication** (red).“ (Namen aus den Feldern der
  Unterschrift).
- **A bei λ gegen E** mit scheinbarem Nernst-Fit (E½, n). Bei kontinuierlichem Scan hinkt die Elektrolyse in der
  Dünnschichtzelle nach (E½ verschoben, n < 1); echte Nernst-Werte brauchen Potentialstufen im Gleichgewicht –
  CV-Werte haben Vorrang.
- **Heatmap:** die ganze Serie in einem Bild – x = Wellenlänge (Bereich wie bei der Spektrenserie), y = Spektren in
  Messreihenfolge von unten nach oben, Farbe = Absorbanz wie gemessen oder Differenz zum ersten gezeigten Spektrum (ΔA,
  divergierende Farbskala mit 0 in der Mitte). Die y-Achse bleibt die Reihenfolge; beschriftet ist sie mit dem Potential
  (auch wenn es hin- und zurückläuft), ohne Potentiale mit der Zeit seit dem ersten Spektrum aus den Dateien, sonst mit
  der Nummer. Farbskala wählbar (viridis, cividis, magma bzw. RdBu, PuOr, coolwarm), oberes Ende „auto“ oder fest.
  Rohsignal-Serien heißen auch hier „raw signal“. Die Maus zeigt λ, Spektrum und Wert; der CSV-Export enthält die
  Matrix (Zeilen = Spektren, Spalten = λ).
- Potentialachse wie gemessen, um E(Fc⁺/Fc) verschoben oder mit der Referenzierung des CV-Tabs (Chip „aus CV-Tab“: das
  Feld heißt nach der Referenz des CV-Tabs und zeigt deren E½, z. B. „E½ Fc (CV)“, bei Verschiebung von Hand „Verschiebung (CV)“; findet der CV-Tab keine Referenz, bleibt die Achse wie gemessen gegen die Elektrode
  dieses Tabs, und die Ergebnisse nennen das).

## H-Cell-Tab (Laden und Entladen)

- Liest **Gamry-Dateien „Cyclic Charge Discharge“** (Hauptdatei mit der Kapazitätstabelle) und die Schrittdateien
  `CHARGE_#n.DTA`/`DISCHARGE_#n.DTA` aus dem Ordner `CHARGE_DISCHARGE` daneben. Andere Dateien in diesem Ordner gehören
  zu anderen Experimenten und werden nicht übernommen; andere Gamry-Arten lehnt der Tab mit einer Meldung ab. Jede
  Messung bekommt im Projekt einen eigenen Ordner (`data/hcell/<Name>/`), damit die Schrittdateien zusammenbleiben.
- **Kapazität gegen Zyklus:** Lade- und Entladekapazität je Zyklus (Spalte „Charge“ der Datei, C → mAh) links, wahlweise
  in % der theoretischen Kapazität oder in mAh; Coulomb-Effizienz (Entladen/Laden desselben Zyklus) rechts, abschaltbar.
  Eine Messung: schwarze Quadrate, rote Kreise, blaue Dreiecke wie in der SI der Gruppe. Mehrere sichtbare Messungen
  liegen in einem Bild, je Messung eine Farbe aus der Liste (Laden gefüllter Kreis, Entladen offener Kreis, Effizienz
  Dreieck), die Legende hat einen Block je Messung.
- **Theoretische Kapazität:** aus der Datei (CAPACITY, im Gerät eingestellt); ein eigener Wert gilt nur für die in der
  Liste gewählte Messung. So lassen sich Zellen mit verschiedener Kapazität in % vergleichen.
- **Potential gegen Zeit:** Lade- (schwarz) und Entladekurven (rot) der gewählten Zyklen über die echte Zeit in h; die
  Zeitachse ist zwischen nicht benachbarten Zyklen unterbrochen (Bruchzeichen, Zahlen = echte Zeit), jeder Zyklus trägt
  „#n“. Leeres Feld „Zyklen“ = erster, zweiter und gleichmäßig verteilt bis zum letzten (höchstens fünf). Fehlt eine
  Schrittdatei, steht das unter der Vorschau; gezeichnet wird nur, was da ist. Gezeigt wird die gewählte Messung.
  Optional die Referenz der Achse, z. B. `Ag0/+`.
- **Ergebnisse:** Tabelle je Zyklus der gewählten Messung (Q_charge, Q_discharge, Kapazität in %, Effizienz) und für
  jede sichtbare Messung erste/letzte Entladekapazität, Erhalt (letzte/erste), mittlere Effizienz und Dauer; Erhalt und
  mittlere Effizienz als Kacheln. Keine Glättung, keine Fits, keine Unsicherheiten.
- **Export:** Abbildung, die Zyklustabelle (`…_cycles.csv`) und die Zusammenfassung (`…_summary.csv`); Bildunterschrift (Konzentration, Elektrolyt) und
  Methodentext im Reiter SI-Text.

## EPR-Tab (CW-EPR)

- Liest **Bruker BES3T** (.dsc + .DTA, z. B. Magnettech ESR5000/ESRStudio, Elexsys; 2D-Dateien ergeben ein Spektrum pro
  Zeile) und **zweispaltigen Text** (Magnettech-MS400-Export; Mikrowellenfrequenz aus Dateinamen wie `…-9p412345-…`).
  Frequenz, Temperatur, Modulation und Leistung werden pro Spektrum angezeigt. Nennt eine Textdatei die Feldeinheit
  nicht (kein „[mT]“ oder „[G]“ im Kopf), wird sie angenommen (Feldwerte über 1500 gelten als G) und das steht bei der
  Messung; unter **Feldeinheit der Datei** lässt sie sich bestätigen oder ändern (nötig z. B. für W-Band in mT).
- **Dunkelspektrum:** Die Messung vor dem Bestrahlen lässt sich von jedem Spektrum abziehen (hell − k·dunkel, auf
  dasselbe Feldraster interpoliert); Warnung, wenn Frequenz, Modulation oder Leistung abweichen.
- **Verarbeitung:** Basislinie nach Wahl, dann Feldbereiche ausblenden (z. B. das scharfe Radikalsignal) und Glätten
  per gleitendem Mittelwert. Verfahren der Basislinie:
  - **Polynom** (Grad 0–5) aus den Rändern des Sweeps oder aus gewählten signalfreien Bereichen: für schwach
    gekrümmte Basislinien.
  - **Glatt:** folgt einem breiten Untergrund (z. B. dem Resonator bei weiten Sweeps) und lässt schmale Linien
    stehen; ein Dunkelspektrum ist nicht nötig, das Rauschen bleibt das der Einzelmessung. Einziger Wert ist die
    **Breite**: was schmaler ist, bleibt Signal, was breiter ist, wird als Untergrund abgezogen. Sie muss größer
    sein als die breiteste echte Linie, sonst verschwinden auch breite Anteile des Spektrums; einseitige Linien
    verlieren etwas Höhe, je nach Linienform und Rauschen (bei einem Zwölftel der Breite: Gauß-Linie bis etwa 4 %,
    Lorentz-Linie bis etwa 10 %). Rechnung: Whittaker-Glätter (kleinste Quadrate mit
    Strafterm auf den zweiten Differenzen) mit einem robusten Gewichtungsschritt; der Methodentext nennt Verfahren,
    Breite und Literaturstelle.
  - **Spline:** natürlicher kubischer Spline durch die Mittel der signalfreien Bereiche (mindestens zwei, kurz
    wählen), wie die Basislinie mit gesetzten Punkten in der Gerätesoftware.
  - Ein **Dunkelspektrum** bleibt die Wahl, wenn der Untergrund ähnlich schmal ist wie das Signal; es verdoppelt
    aber die Rauschleistung (Faktor √2 im Rauschen) und entfernt, was schon im Dunkelspektrum an Signal steckt.
- **EasySpin-Simulationen** als zweispaltiger Text (B in mT, Intensität), z. B. `writematrix([B(:) spc(:)], 'sim.txt',
  'Delimiter', '\t')`; per kleinsten Quadraten an eine Messung angepasst (oder von Hand skaliert) und im Feld
  verschiebbar; gestrichelt auf derselben Ebene. Eine **Parameterdatei** (die MATLAB-Zeilen `Sys.D = [D E]; …`) wird
  angezeigt, D und |E| in cm⁻¹ umgerechnet, optional im Bild.
- Darstellung in mT oder G, überlagert oder gestapelt, normiert, y-Achse standardmäßig ohne Zahlen, freie Labels wie
  `Z⁻@122, Y⁺@400`. Beim Überfahren: B, g-Faktor und Intensität.
- **Messreihen (Zeit, Temperatur):** Gestapelt steht der Name rechts neben jeder Kurve statt in einer Legende; ein
  Doppelklick auf den Namen in der Liste benennt um. **Beschriftung** zeigt wahlweise Zeit oder Temperatur aus der
  Messdatei, **Farbverlauf** färbt die Kurven in Listenreihenfolge, **Umkehren** dreht die ganze Liste.
- **Mehrere Spezies:** Alle einer Messung zugeordneten Simulationen (EasySpin oder eigene S = ½) werden *gemeinsam* per
  linearen kleinsten Quadraten skaliert; die Anteile (Doppelintegral) werden angezeigt, optional die Summe und der Rest
  (Messung − Summe) – also die Subtraktion einzelner Spezies. Nichtlineare Parameter (g, A, D/E, Linienbreiten von
  Pulverspektren) werden in EasySpin gefittet; Elucida bestimmt nur die Anteile. Gestapelt liegt eine Simulation auf
  ihrer Messung; **Simulation unter der Messung** zeichnet sie auf einer eigenen Ebene direkt darunter (Wert = Abstand als
  Vielfaches des Stapelabstands).
- **Eigene isotrope S = ½-Simulation mit Fit** (Lösung, erste Ordnung): g, Gruppen äquivalenter Kerne (z. B.
  `2 14N 0.65; 4 1H 0.32`, a in mT; Isotope von ¹H bis ²⁰⁹Bi, z. B. ¹¹B, ⁷Li, ²³Na, ²⁷Al, oder der Kernspin direkt als
  `I=3/2`), Peak-zu-Peak-Linienbreite und Lorentz-Anteil; „Fitten“ verfeinert g, a und ΔB_pp
  (Levenberg-Marquardt nach einer Grobsuche, Amplitude linear). Überlagern sich mehrere S = ½-Spezies in einer
  Messung, fittet **Gemeinsam fitten** alle ihr zugeordneten Simulationen gleichzeitig (eine lineare Amplitude je
  Spezies). Startwerte sind die aktuellen Werte, eine Grobsuche gibt es dabei nicht: jede Spezies vorher grob
  einstellen oder einzeln fitten. Unsicherheiten gibt der Fit nicht aus.
- **Konventionen der EPR-Rechnung:** Kopplungen in MHz = a [mT] · (µ_B/h) · g mit dem gefitteten g (EasySpin rechnet
  mit g_e; der Unterschied ist g/g_e). Linienform Pseudo-Voigt: Summe aus Gauß- und Lorentz-Ableitung gleicher
  ΔB_pp, keine Faltung; der Lorentz-Anteil ist nicht mit EasySpin-Breiten vergleichbar. Hyperfeinmuster nur in
  erster Ordnung (bei großen Kopplungen, z. B. ⁵¹V, ⁵⁵Mn, Cu, verschieben sich g und a), keine Gewichtung von
  Isotopologen. Ein g, das vor einer Änderung der Feldkalibrierung oder Referenzfrequenz gefittet wurde, wird erst
  nach erneutem Fit wieder berichtet.
- **Feldkalibrierung mit TEMPO** (oder einer anderen Referenz): Referenz mit einer S = ½-Simulation fitten, als
  Kalibrierung mit ihrem Literatur-g wählen (Vorgabe 2,0055, TEMPO in MeCN); ΔB = B(g_fit) − B(g_lit) wird von allen
  anderen Messungen abgezogen, deren Fits dann kalibrierte g-Faktoren liefern.
- **Intensität gegen Zeit oder Temperatur** (z. B. Belichtungskinetik, thermischer Zerfall): Doppelintegral oder
  Peak-zu-Peak in einem Feldfenster für jede sichtbare Messung (nach Dunkelspektrum und Basislinie), optional × T
  (Curie), normiert; die Zeit zählt ab dem frühesten Spektrum im Tab (z. B. dem Dunkelspektrum). „Dunkelspektrum für
  alle Messungen übernehmen“ setzt den Hintergrund für eine ganze Serie auf einmal und blendet das Dunkelspektrum
  selbst im Bild aus (das Häkchen in der Liste zeigt es wieder).
- **Thermischer Zerfall bei konstanter Heizrate** (Nachbau des MATLAB-Skripts der Gruppe): Intensität je Spektrum als
  Peak-zu-Peak, Doppelintegral oder **Gauß + Gerade an ein Merkmal** (z. B. das X-Merkmal bei 487 mT), × T, Feld auf eine
  Referenzfrequenz skaliert (z. B. 9,3 GHz) und Temperaturkorrektur (z. B. −1,5 K); dann **E_a und A** aus
  I(T) = exp(−A·∫exp(−E_a/RT)/β dT), β aus dem mittleren Temperatur- und Zeitschritt. Zielfunktion kleinste Quadrate (Standard;
  belastbares 95-%-Intervall mit t-Quantil) oder „wie Skript“ (√|r|, zum Vergleich mit alten Zahlen – empfindlich
  gegenüber dem Optimierer, ihr Intervall unterschätzt die Unsicherheit stark). E_a und ln A sind fast vollständig korreliert.
- **Wo:** Schritt **Auswertung**, Karte **Intensität und Kinetik**. Das Feld **Ansicht** wählt, was die Abbildung
  zeigt: Spektren, Intensität gegen Zeit, gegen Temperatur, Arrhenius oder gegen die Nummer. Die Felder darunter
  gehören zur gewählten Ansicht; die übrigen sind ausgeblendet.
- **Spinzählung:** Ansicht „Spinzählung (gegen Konzentration)“ in der Karte **Intensität und Kinetik**. Messungen, bei
  denen unter „Ausgewähltes Spektrum“ eine bekannte Konzentration steht (**c (bekannt)**, Einheit daneben), sind die
  Referenzen: ihr Doppelintegral gegen die Konzentration ergibt die Kalibrierung, ab drei verschiedenen Konzentrationen
  als Ausgleichsgerade mit Achsenabschnitt, mit einer oder zwei als Gerade durch den Ursprung. Die übrigen sichtbaren
  Messungen sind Proben, ihre Spinkonzentration wird an der Geraden abgelesen und steht im Reiter Ergebnisse, in der
  Unterschrift und im Methodentext. Referenzen dürfen in der Liste ausgeblendet sein. Es gibt keine Unsicherheiten und
  keine Umrechnung: alle Spektren müssen unter denselben Bedingungen aufgenommen sein (gleiche Modulation, Leistung,
  Temperatur, Füllhöhe, ungesättigt); weichen Modulation, Leistung oder Temperatur laut Messdatei ab, steht ein
  Hinweis. Nur mit dem Doppelintegral, ohne I·T.
- **Isotherme Zerfälle und Arrhenius:** Ansicht „Intensität gegen Zeit“ mit **Zerfall fitten** legt je Temperatur einen Zerfall
  erster Ordnung an, I(t) = I₀·exp(−k·t) (kleinste Quadrate auf den Intensitäten, 95-%-Intervall von k mit
  t-Quantil). Eine Serie sind die Messungen, deren Temperatur **aus der Messdatei** auf 1 K gerundet gleich ist; ab
  drei Spektren wird gefittet, sonst steht ein Hinweis. Die Ergebnisse stehen je Temperatur in einer Tabelle (Reiter Ergebnisse). **Fit bis Verlust** beschränkt den Fit auf den Anfang jeder
  Serie (z. B. 15 %: bis die Intensität 15 % unter dem ersten Punkt liegt). Die Ansicht „Arrhenius“ trägt ln k
  gegen 1000/T auf und liefert E_a und ln A aus einer ungewichteten Ausgleichsgeraden, ein Punkt je Temperatur; ein
  95-%-Intervall gibt es erst ab drei Temperaturen. Die Striche an den Punkten sind die Intervalle von k. Peak-zu-Peak
  unterschätzt k, sobald das Signal im Rauschen verschwindet; dann das Doppelintegral oder „Fit bis Verlust“ nehmen.
  Die Bildunterschrift dieser Ansichten sagt, was aufgetragen ist (Größe, Feldfenster, Normierung, Temperaturen), und
  nennt nur Werte gezeigter Fits (k und Halbwertszeit je Temperatur, E_a und A der Rampe, die Arrhenius-Gerade).
- **Export für EasySpin:** Neben der Abbildung wird jede Messung als zweispaltige Textdatei (B in mT, Intensität) in
  voller Auflösung nach Dunkelspektrum, Basislinie und Glättung geschrieben – ohne Normierung und ohne ausgeblendete
  Bereiche – mit `%`-Kopfzeilen zu Frequenz, Temperatur und Verarbeitung (`load(...)` in MATLAB, direkt für `esfit`).
  Die Intensitätsreihe wird als `…_intensity.csv` gespeichert (Spalte `role`: Referenz, Probe oder Messung; x und y mit Einheiten; Kalibriergerade und Zerfalls-/Arrhenius-Fits als Zeilen mit Parameter, Wert und Intervall).
- **Spindichte und Hyperfeinkopplungen aus einer Rechnung:** Schritt **Daten**, Karte **Rechnung (DFT)**: eine
  Gaussian-16-Ausgabe einer offenschaligen Rechnung wählen (Mulliken-Spinpopulationen und Fermi-Kontakt-Kopplungen
  stehen in jeder solchen Ausgabe, die Dipolkopplungen mit `Prop=EPR`), dazu wahlweise eine Molden- oder Cube-Datei
  derselben Geometrie für die Fläche. Aus einer Molden-Datei werden Spindichte und SOMO gerechnet; ein Cube wird
  gezeigt, wie er ist. Dateien mit anderen Atomen oder Koordinaten (± 0.02 Å) und Ausgaben anderer Programme werden
  abgelehnt.
  **ORCA**-Ausgaben (`.out`) werden aus ORCA 4.0–4.2, 5.0 und 6.0 gelesen (an echten Ausgaben geprüft) sowie aus 6.1
  (mit dem 6.0-Layout, das laut ORCA-6.1-Dokumentation unverändert ist; noch nicht an einer echten Ausgabe geprüft,
  deshalb zeigen beide Reiter einen Hinweis, Werte gegen die Ausgabe vergleichen). Andere Versionen werden mit Meldung
  abgelehnt, ebenso Dateien, deren Nucleus-Zeilen oder Tabellenköpfe nicht genau zum Layout passen. Gelesen werden Spinpopulationen aus dem letzten Block „MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS“,
  die Kopplungen aus dem Hyperfeinblock, den ORCA nur mit einem `%eprnmr`-Block in der Eingabe druckt, je Element eine
  Zeile:

  ```
  %eprnmr
    Nuclei = all H {aiso, adip}
    Nuclei = all N {aiso, adip}
  end
  ```

  Die isotrope Kopplung ist A(FC) (Fermi-Kontakt, wie in der Gaussian-Ausgabe), G aus MHz mit g_e. Die Dipol-Hauptwerte
  kommen aus A(SD) und nur für Kerne ohne `aorb` (mit `aorb` druckt ORCA A(SD) im Achsensystem des Gesamttensors, das
  sind nicht seine Hauptwerte). Bei mehreren Jobs in einer Ausgabe kommt das Rechenniveau aus dem Job, der den
  Hyperfeinblock gedruckt hat. Ohne `%eprnmr` werden nur die Spindichten gelesen; der Reiter **Hyperfein** sagt dann,
  welche Eingabe fehlt. Kerne, für die ORCA nichts druckt, bleiben leer. Molden-Dateien für die Fläche entstehen mit
  `orca_2mkl Name -molden`, Cube-Dateien mit `orca_plot`.
  Reiter **Spindichte**: Fläche auf dem Molekül und die Spinpopulation jedes Atoms in Prozent der Summe aller Atome,
  mit Vorzeichen (alle Atome zusammen 100 %). Im Bild stehen Werte ab der **Schwelle**, die Tabelle darunter zeigt alle
  Atome und die Summe.
  Reiter **Hyperfein**: berechnete isotrope Kopplungen an den Kernen. Mit einer eigenen S = ½-Simulation steht der
  experimentelle Wert daneben: im Schritt **Auswertung**, Karte **Hyperfein-Zuordnung**, eine Gruppe wählen und ihre
  Kerne im Bild anklicken (Shift + Rahmen wählt mehrere, ein zweiter Klick löst einen Kern). Mehrere Kerne einer Gruppe
  werden mit Vorzeichen gemittelt („avg.“); die Werte stehen rings um das Molekül, ein Pfeil zeigt auf den Kern, bei
  Kernen an einem gemeinsamen Atom (Methyl) auf dieses Atom. Im Bild stehen Beträge wie die experimentellen Werte,
  mit dem Chip **Vorzeichen** die Werte mit Vorzeichen; im Bild der Spindichte ganze Prozent. Stimmt die Zahl der Kerne nicht mit
  der Simulation überein, steht ein Hinweis. Experimentelle Werte haben kein Vorzeichen. Nicht zugeordnete Kerne
  stehen einzeln im Bild, ab dem Betrag **Ab Kopplung** und nur für die Elemente unter **Kerne** (leer: die Elemente
  der Simulation, ohne Simulation alle außer C und O). Die Tabelle nennt für jeden Kern die Kopplung in der gewählten Einheit, mit dem Chip
  **Dipolkopplung** auch die Hauptwerte der Dipolkopplung; die CSV enthält immer MHz, G und die Dipolwerte.
  Einstellungen im Schritt **Darstellung**, Karte **Spindichte und Hyperfein**: Fläche (Spindichte, SOMO, keine),
  Isowert, Deckkraft, Farben, Schwelle, Einheit (MHz, G, mT). Labels lassen sich ziehen, das Molekül drehen; die
  Ansicht gilt für beide Abbildungen. Export und SI enthalten beide Abbildungen, die Unterschrift nennt Isowert und
  Rechenniveau.
  **EasySpin-Skript speichern …** (Karte **Hyperfein-Zuordnung**) schreibt ein Startskript für EasySpin `garlic`
  (isotropes Lösungsspektrum, MATLAB-`.m`): Kerne, Anzahl und Kopplungen in MHz der zugeordneten Gruppen (ohne
  Zuordnung die einzeln im Bild stehenden Kerne), g aus dem Fit der S = ½-Simulation sowie Mikrowellenfrequenz und
  Feldbereich aus ihrer Messung. Ohne gültigen Fit bleibt `Sys.g` ein auskommentierter Platzhalter (garlic verlangt g,
  es wird kein Wert geraten), ebenso Frequenz und Bereich ohne Messung; die Linienbreite `Sys.lwpp` ist immer selbst zu
  setzen. Nur isotrope Kopplungen, anisotrope Tensoren werden nicht ausgegeben. Der Export schreibt das Skript mit
  (`…_easyspin.m`, Name nur aus Buchstaben, Ziffern und Unterstrichen, damit MATLAB es ausführt, z. B.
  `S3_1_EPR_easyspin.m`).
- **Bildunterschrift** (Reiter SI-Text): „Kopplungen in“ wählt die Einheit der Hyperfeinkopplungen der S = ½-Fits
  (MHz mit dem gefitteten g, mT oder G als Aufspaltung; G gilt auch im Methodentext). Der Chip **Messparameter** setzt
  Mikrowellenfrequenz, Modulationsamplitude, Leistung, Zahl der Scans und Temperatur aus den Messdateien in die
  Unterschrift („Experimental conditions: …“) – nur, was in allen gezeigten Messungen steht und gleich ist (Bruker
  BES3T; Textdateien enthalten diese Angaben nicht).

## X-Ray-Tab

- Eine oder mehrere **CIF**-Dateien laden (Knopf oder Drag & Drop); jeder `data_`-Block mit Atomen wird ein Eintrag
  (eine Spalte in den Tabellen). Elucida liest die CIF selbst (Zelle, Koordinaten, U_iso/U_ij, Besetzung, PART,
  Symmetrieoperationen, `_geom_bond`/`_geom_angle`/`_geom_torsion`); keine weitere Software nötig.
- **ORTEP-Abbildung im Mercury-Stil:** schattierte Schwingungsellipsoide mit 50 % Aufenthaltswahrscheinlichkeit
  (einstellbar), exakt projiziert, mit den Hauptachsen-Ellipsen; schwarze Bindungen, fette Labels (verschiebbar), H-Atome
  als kleine schattierte Kugeln. Weitere Stile (auch in PDF/SVG/PNG und
  Word): flacher Olex2-Stil. Einzelne Atome (z. B. einzelne H) lassen
  sich ausblenden und Labels **je Atom** an-/abschalten (Atomliste, Doppelklick auf das Atom oder **Shift + Rahmen
  ziehen** für mehrere Atome); Labelfarbe schwarz oder wie das Atom.
  **Ziehen dreht**, rechte Taste verschiebt, Mausrad zoomt; die Ansicht wird je Struktur gespeichert,
  **Startansicht** führt zur Standardansicht (möglichst wenig überdeckte Atome). Atomfarben je Element frei wählbar
  (Standard: Olex2-Farben).
- Das Molekül wird **über die Symmetrie vervollständigt** (z. B. Molekül auf einem Inversionszentrum); erzeugte Atome
  tragen einen Zusatz (C1ⁱ), die Operation steht als Fußnote darunter. **Fehlordnung:** nur Hauptteil (Standard),
  alle Teile oder der Nebenteil. Getrennte Fragmente (Lösungsmittel, Gegenionen) und H-Atome lassen sich ausblenden;
  **Lösungsmittel** / **Gegenionen ausblenden** erkennt die üblichen über die Summenformel (THF, Et₂O, CH₂Cl₂, Toluol …;
  OTf⁻, BF₄⁻, PF₆⁻, BArF⁻ …).
- **Drahtmodell** für sperrige Gruppen (z. B. Dipp): die Bindung zum Substituenten anklicken (Atom am Kern zuerst, z. B.
  N, dann C_ipso) und **Als Drahtmodell** drücken – alles dahinter wird als dünne Linien in den Elementfarben gezeichnet,
  ohne H-Atome und Labels. Liegt die Bindung in einem Ring (Spiro-Atom), gilt das Ringsystem hinter dem ersten Atom.
  Die Startansicht vermeidet überdeckte Atome; Labels wahlweise nur für Heteroatome.
- **Vorschlag für die Bildunterschrift** (Englisch), z. B. „… Displacement ellipsoids are drawn at the 50 % probability
  level; co-crystallised THF omitted, Dipp groups shown as wireframe without hydrogen atoms for clarity. …“, mit den
  ausgewählten Parametern und Symmetriecodes; Kopieren mit einem Klick, beim Export als `…_captions.txt`.
- **Atome anklicken** (das vorderste gewinnt): 2 = Abstand, 3 = Winkel, 4 = Diederwinkel. Werte mit
  Standardabweichung kommen **genau aus der CIF** (z. B. 1.392(3)); Elucida schätzt nie selbst eine
  Standardabweichung. Fehlt ein Wert (Diederwinkel ohne `CONF`), wird er aus den Koordinaten berechnet, **ohne**
  Standardabweichung angezeigt und markiert – für Diederwinkel mit esd `CONF` in Olex2/SHELXL setzen und neu verfeinern.
- **Tabellen für die SI:** Kristalldaten und Strukturverfeinerung (eine Spalte je Verbindung; Zahlen genau wie in der
  CIF, Raumgruppe kursiv mit Tiefstellung, Restelektronendichte mit echtem Minuszeichen; interne Referenz und
  CCDC-Nummer editierbar) und ausgewählte Bindungslängen, Winkel und Diederwinkel (gleichnamige Atome nebeneinander).
  **Kopieren** behält Kursivschrift und Hoch-/Tiefstellung in Word; der Export schreibt zusätzlich CSV und Excel.
  Die Tabellen sind englisch beschriftet (wie in SI üblich).
- **Vergleich mit Rechnung** (Schritt Auswertung): unter **Rechnung** eine Geometrie aus dem DFT-Tab wählen oder über
  **Datei …** eine xyz-Datei bzw. ORCA-/Gaussian-Ausgabe laden. Die Atome werden nur über das Bindungsnetz zugeordnet:
  gleiche Summenformel, gleiche Verknüpfung der Schweratome, gleich viele H an jedem Schweratom. Passt etwas nicht,
  nennt der Hinweis die Stelle (Summenformeln, abweichende Atome) und es gibt keine Zuordnung – nie nach Abstand oder
  Reihenfolge. Enthält der Kristall weitere Moleküle (Lösungsmittel, Gegenionen) oder Fehlordnung, unter **Fragment**
  den Teil wählen, der der Rechnung entspricht, bzw. unter Darstellung → Fehlordnung einen Teil. Bei mehreren
  gleichwertigen Zuordnungen (Symmetrie) gilt die mit der kleinsten RMSD der Schweratome nach Überlagerung; ergeben gleich
  gute Zuordnungen verschiedene Werte, nennt der Hinweis die Parameter. Die **Zuordnung** (CIF-Label ↔ Nummer und Element
  in der Datei der Rechnung) wird mit der Verbindung gespeichert. Die Parametertabelle bekommt die Spalte der Rechnung
  (Kopf = Methode, bei einer reinen xyz „calc.“; Bindungslängen mit 3, Winkel mit 1 Nachkommastelle, ohne
  Standardabweichung), wahlweise **Spalte Δ** (Rechnung − Kristall); dasselbe in Excel/CSV und Word, dort mit einer
  Fußnote zur Geometrie (Gasphase oder solvatisiert, wie die Rechnung angibt) und der RMSD. Mit Rechnung stehen die
  Werte immer in der Tabelle, nicht in der Bildunterschrift.
- Export: je Struktur eine Abbildung (PDF/SVG vektoriell, PNG) sowie `…_crystal_data.csv`, `…_parameters.csv`,
  `…_contacts.csv` (Packung) und `…_tables.xlsx`. Die Labelgröße ist je Tab einstellbar, der **Hintergrund** wählbar (weiß, transparent, Farbe; gilt
  auch für Word).
- **Packung** (Karte im Schritt Darstellung): „Abbildung: Packung (Elementarzelle)“ zeigt die Elementarzelle mit ihrem
  Inhalt – ganze Moleküle, deren Schwerpunkt in der Zelle liegt, oder alle, die mit mindestens einem Atom in ihr liegen –
  mit Blick entlang *a*, *b* oder *c*; Drehen mit der Maus schaltet auf „frei gedreht“. Gezeichnet werden die Zellkanten
  und die Achsen *a*, *b*, *c* (die Achse zum Betrachter bleibt unbeschriftet). H-Atome an/aus, Ellipsoidstil, Farben und
  Hintergrund wie im Molekülbild. **Abstände in der Packung** (Schritt Auswertung) schlägt je Molekülpaar den kürzesten
  Kontakt unter der Summe der van-der-Waals-Radien (Bondi 1964; Elemente ohne Bondi-Radius werden nicht vorgeschlagen)
  plus Toleranz vor, dazu Schwerpunktabstände ebener 5- bis 7-Ringe (Cg···Cg bis zum eingestellten Wert, mit Versatz)
  und Ebenenabstände nur für parallele Ringe (innerhalb „Parallel bis“, sonst der Winkel). Ein Häkchen zeigt den Abstand
  als gestrichelte Linie mit Wert; oder zwei Atome verschiedener Moleküle im Packungsbild anklicken und „Zwei gewählte
  Atome“ drücken. Die Seite **Abstände** listet die gezeigten Abstände mit Symmetriecodes; die Unterschrift nennt
  Blickrichtung, Regel und Abstände (mehr als acht kommen in eine Tabelle). Mit „In die SI (Word)“ folgt das
  Packungsbild dem Molekülbild in der SI und im Export (`…_packing`). Abstände sind aus den Koordinaten gerechnet und
  haben keine Standardabweichung.
- **Pulverdiffraktogramm (PXRD)** (Karte im Schritt Auswertung, Seite „PXRD“): berechnet das Pulverdiffraktogramm der
  gewählten Struktur – eine Rechnung aus der Struktur, **kein Rietveld-Fit**. Reflexlagen aus der Zelle, Intensitäten
  |F|²·Lp jedes einzelnen Reflexes (die Multiplizität ist damit enthalten), F aus allen Atomen der Elementarzelle
  (Symmetrieoperationen der CIF, Besetzung fehlgeordneter Teile, isotrope oder anisotrope Auslenkungsparameter),
  Atomformfaktoren aus den International Tables Vol. C (Cromer–Mann-Koeffizienten), ohne anomale Dispersion;
  Lorentz-Polarisationsfaktor für Bragg–Brentano ohne Monochromator. **Strahlung** Cu (Vorgabe), Mo, Co, Fe, Cr oder Ag
  Kα; **Kα2** (halbe Intensität) an/aus; Profil **Pseudo-Voigt** mit der eingegebenen **Halbwertsbreite** (° 2θ) und
  dem Lorentz-Anteil η; **Bereich** 2θ (auto = Bereich der Messung). Ein **gemessenes** Diffraktogramm als `.xy`/`.xye`
  oder andere Textdatei laden (erste Spalte 2θ in Grad, zweite Intensität). Angepasst wird nichts: das berechnete
  Diffraktogramm wird auf sein stärkstes Maximum skaliert, ein eingegebener **Nullpunkt** verschiebt die berechneten
  Reflexe (die Messung bleibt unverändert). Die Karte nennt die Temperatur der Strukturbestimmung: ein bei
  Raumtemperatur gemessenes Pulver zeigt die Reflexe meist bei etwas kleinerem 2θ (Ausdehnung der Zelle), bevorzugte
  Orientierung ändert Intensitäten – beides wird nicht korrigiert. **PXRD-Abbildung** (Schritt Darstellung): gemessen
  oben und berechnet unten oder überlagert; Reflexmarken (Kα1), Farben, „In die SI (Word)“ (Abbildung, Unterschrift und
  ein Methodensatz mit der Quelle der Formfaktoren nach dem Packungsbild; Export `…_pxrd` mit einer CSV der Reflexe und
  des berechneten Diffraktogramms).
- **Aromatizität (HOMA)** (Karte im Schritt Auswertung, Seite **HOMA**): HOMA je ebenem 5- bis 7-Ring aus den
  Bindungslängen der Atomkoordinaten, HOMA = 1 − (1/*n*) Σ α (*R*opt − *R*i)² mit *R*opt und α je Bindungstyp nach
  Krygowski (J. Chem. Inf. Comput. Sci. 1993; CC, CN, CO, CP, CS, NN, NO) oder wahlweise HOMAc (Arpa, Stafström,
  Durbeej, J. Org. Chem. 2025; nur CC, CN, NN, CO). Für Ringe mit nur einem Bindungstyp stehen EN und GEO daneben
  (HOMA = 1 − EN − GEO, Krygowski & Cyrański 1996). Ein Ring mit einem Bindungstyp ohne Literaturparameter (z. B. C–B,
  C–Si, Metall) bekommt keinen Wert, sondern den Hinweis, welche Bindung fehlt. Für HOMA wird keine Standardabweichung
  angegeben. „Werte im Bild“ setzt den Wert in die Ringmitte (wie ein Label ziehbar); „In die SI“ bringt die Tabelle mit
  Formel und Zitaten in die SI und immer eine `…_HOMA.csv` in den Export (die SI-Pille gilt nur für Word).

## DFT-Tab

- **xyz**-Dateien (auch Trajektorien; gezeigt wird das letzte Bild) oder Ausgaben von **ORCA 6** (`.out`) und
  **Gaussian** (`.log`) laden. Dateien aus einer PowerShell-Umleitung (UTF-16) werden erkannt. Stile: Mercury, Olex2,
  **Kugel-Stab wie im ORCA-Handbuch**, **IboView** und eine **Strichzeichnung** (weiße Kugeln, hohle Stäbe, wie in klassischen
  Zeitschriftenabbildungen); Maus wie im X-Ray-Tab.
- **Messen und Ausrichten** wie im X-Ray-Tab: 2/3/4 Atome anklicken für Abstand, Winkel oder Diederwinkel (Werte aus der
  Geometrie, 3 bzw. 1 Nachkommastelle); Bindung nach unten/oben/links/rechts, Ebene von vorn, schrittweise drehen,
  wenden, ChemDraw-Vorlage.
- **Umnummerieren:** **Nummerieren** drücken und die Atome in der gewünschten Reihenfolge anklicken; **Übernehmen**
  stellt sie nach vorn, die übrigen behalten ihre Reihenfolge (wahlweise H direkt hinter ihrem Atom). **xyz speichern**
  schreibt eine neue Datei mit unveränderten Zeilen (nur umsortiert); die geladene Datei wird nie überschrieben.
  Zählung ab 0 (ORCA) wählbar. Atomradius und Bindungsdicke wirken auch in den Kugel-Stab-Stilen (relativ zum Standard);
  Hintergrund wählbar wie im X-Ray-Tab.
- **Wie Vorlage:** übernimmt die Nummerierung einer anderen Geometrie im Tab oder einer Kristallstruktur im X-Ray-Tab
  (dann mit den Atomnamen der CIF, z. B. C1, H3A). Schweratome über das Bindungsnetz, symmetrische Moleküle über die
  kleinste Abweichung nach Überlagerung; eine gleich gute Alternative wird mit den betroffenen Atomen gemeldet, H folgen
  ihrem Nachbaratom.
- **Ladungen** (Reiter neben der Abbildung): atomare Ladungen und, wo gedruckt, Spinpopulationen der gewählten
  Rechnung – ORCA Mulliken und Löwdin, Gaussian Mulliken (letzter Block = Endgeometrie), je vorhandenem Schema eine
  Spalte, Atome in der Nummerierung des Tabs, drei Nachkommastellen. **In die SI** übernimmt die Tabelle in den
  SI-Export; der Export schreibt `…_charges.csv` mit allen gedruckten Stellen. Hirshfeld wird noch nicht gelesen
  (keine geprüfte Ausgabe).
- **SI-Text** (Karte „Rechnung für die SI“; ORCA 6, Gaussian): Name, Abbildung, Ladung/Multiplizität/Punktgruppe, kartesische Koordinaten
  und E_el/H/G (ZPE-Spalte optional), wahlweise Eingabezeile (je Struktur oder einmal als „Computational details“),
  Konvergenztabelle des letzten Zyklus und Frequenzergebnis. Alle Werte exakt wie in der Ausgabe. Das Programm warnt bei
  abgebrochenen Rechnungen, nicht konvergierter Optimierung und imaginären Frequenzen; bei CPCM steht nur der
  dielektrische Beitrag da (eine Solvatationsenergie braucht die Gasphasenrechnung). **Kopieren**, **Word
  speichern** (zweispaltig) oder über den SI-Abschnitt.
- **Energietabelle** (Reiter, Pflichtangaben von ACS, Org. Lett. und Angew. Chem.): je Rechnung N_imag, E_el,
  Kernabstoßung E_nuc, H, G, thermische Korrektur H_corr und Entropiekorrektur −TS in Hartree, genau wie in der Ausgabe;
  was die Ausgabe nicht druckt, bleibt ein Strich (ORCA: keine H-Korrektur; Gaussian: kein −TS in Hartree). Darunter das
  Rechenprogramm mit Version. In der App stehen Energien und Korrekturen in zwei Tabellen untereinander, die Kachel
  „Eingabe“ in der Reiterzeile zählt die vorhandenen Eingabedateien. Die Tabelle kommt in die Word-SI (über die ganze Breite) und in den Export
  (`…_energies.csv`). **Alle als xyz** bzw. der Export schreiben alle Strukturen in **eine** xyz-Datei
  (`…_structures.xyz`, Name und E_el in der Kommentarzeile) – ACS erkennt Koordinaten nur maschinenlesbar an, nicht als
  Tabelle in der SI; das Datenpaket enthält sie als `DFT/structures.xyz`. Liegt neben einer Ausgabe die Eingabe mit
  gleichem Namen (`.inp`, `.gjf`, `.com`), wird sie mitkopiert und kommt ins Datenpaket; fehlt sie, steht das unter der
  Tabelle.
- **Isofläche wie IboView:** Schwellentyp „Dichte“ (Anteil von |ψ|², Standard 80 %) oder „absolut“ (±ψ, Standard 0.01),
  Stellen und Schrittweite wie in IboView.
- **Energieprofil:** Ein Energieprofil vergleicht mehrere Verbindungen und gehört deshalb in einen Reaktionspfad des
  Projekts (Computerchemie, siehe oben); nur dort lässt es sich bearbeiten, im DFT-Tab einer Verbindung gibt es den Reiter
  nicht mehr (früher dort gespeicherte Profildaten bleiben in der Projektdatei). Spezies = die Opt/Freq-Rechnungen, je mit Label, Schritt und
  Pfad(en) A, B …; optional **Einzelpunkte** (z. B. DLPNO-CCSD(T)), zugeordnet über gleiche Atome und Koordinaten
  (nie über Dateinamen): G = E(SP) + (G − E_el). Stufen mit gestrichelten Verbindungen, ΔG/ΔH/ΔE in kcal mol⁻¹ (unter **Einheit** auch kJ mol⁻¹ oder eV, umgerechnet für Bild,
  Achse und Unterschrift) mit einer
  Nachkommastelle, Unterschrift „… calculated at the <Einzelpunkt>//<Geometrie> level of theory“.
  **Multireferenz-Plateaus** (ORCA 6 CASSCF/NEVPT2/SORCI, als Einzelpunkt oder als Rechnung selbst): die Felder
  **Methode** und **Zustand** unter der Tabelle wählen, welche Zustandsenergie das Plateau zeigt (Vorgabe: höchste Theorie
  der Datei, NEVPT2 vor CASSCF, Wurzel 0). Genommen wird nur die elektronische Gesamtenergie dieses Zustands; G und H
  addieren die thermische Korrektur der eigenen Frequenzrechnung des Plateaus. Fehlt sie, zeigt das Plateau seine
  elektronische Energie, mit Hinweis und Satz in der Unterschrift. Die Unterschrift nennt Methode und Wurzel.
  **IRC** (ORCA): Ausgabe + `<Name>_IRC_Full_trj.xyz`, x = Reaktionskoordinate in Å (Summe der kartesischen Verschiebungen, nicht massengewichtet; TS = 0) oder eine Bindungslänge, mehrere
  IRCs nacheinander, Barrieren am Übergangszustand.
- **NICS** (Reiter): Gaussian-NMR-Ausgaben mit Geisteratomen (Bq, z. B. aus py.Aroma): NICS und NICSzz (entlang der
  Normalen der Ringebene) je Punkt, Mittel ober-/unterhalb; Scans als Kurve über die Weglänge (NICS schwarz, NICSzz rot).
  Die Unterschrift beschreibt den Scan aus den Koordinaten der Bq: parallel zur Molekülebene in einer Höhe, entlang der
  Ebenennormalen (Höhenbereich) oder neutral „along the scan path“.
  **3D-NICS:** Liegen die Bq auf einem regelmäßigen Gitter (ab 200 Bq je Datei, auch über mehrere Teilrechnungen
  verteilt, z. B. `…_3D_NICS_0001.log` bis `…_0016.log`), setzt der Reiter alle Teile zu einem Gitter zusammen und zeigt
  das Molekül als Kugel-Stab-Modell mit zwei Isoflächen: entschirmt (Standard +5 ppm, rot) und abgeschirmt (Standard
  −15 ppm, blau, durchscheinend); jede Fläche hat ihre eigene Deckkraft. Die Dateien stehen links in der Karte **NICS-Rechnungen** (Schritt Daten), Isowerte, Farben und Deckkraft in der Karte
  **NICS-Abbildung** (Schritt Darstellung); das Bild rechts lässt sich drehen. Fehlt eine Teilrechnung
  oder passen die Geometrien nicht zusammen, wird das Gitter abgelehnt und die Zahl der Punkte genannt. Sind Scan und
  Gitter geladen, wählt „Abbildung“ in dieser Karte, was der Reiter zeigt; Export und SI enthalten beide. Der Export schreibt das
  Gitter zusätzlich als Cube-Datei (NICS in ppm).
- **ACID** (Reiter): Isofläche der Anisotropie der induzierten Stromdichte (ACID, Herges/Geuenich) auf dem
  Kugel-Stab-Modell, mit den Stromdichtepfeilen des AICD-Programms. Elucida rechnet nichts davon selbst.
  **Vorgehen:** Gaussian-NMR-Rechnung mit `NMR=CSGT IOp(10/93=1)` (alle Orbitale) oder `IOp(10/93=2)` (ausgewählte
  Orbitale), die Gaussian die Hilfsdatei `….txt` schreiben lässt; dann AICD mit POV-Ray-Eingabe, z. B.
  `AICD --povrayinput -c -m 2 -s -b 0 0 1 rechnung.log` (`-m 2`/`4`: mit Pfeilen, `-b`: Magnetfeldrichtung, `-l`:
  Isowert, `-p`: Gitterpunkte, `-s`: geglättete Fläche, `--maxarrowlength`: lange Pfeile weglassen). Im entstehenden
  Ordner `<Name>.d` liegen `Isoober.inc` (Fläche, Pfeile, Magnetfeld, Aufruf) und `Molekuel.inc` (Atome).
  **Laden:** in der Karte **ACID-Rechnung** (Schritt Daten) `Isoober.inc` hinzufügen, `Molekuel.inc` aus demselben
  Ordner kommt mit; dazu die Gaussian-Ausgabe der CSGT-Rechnung (Methode und Basis für die Unterschrift,
  `IOp(10/93=2)` erscheint als „considering only the selected orbitals“) und die „Geometrie-Methode“ wie bei NICS.
  Gelesen wird nur der Aufbau, den AICD 3.0.4 mit geglätteter Fläche schreibt (Netz aus `smooth_triangle`, Pfeile als
  Zylinder + Kegel); andere Dateien werden abgelehnt. Der Isowert steht im Aufruf in der Datei und wird nur übernommen,
  wenn die Magnetfeldrichtung dort zum Magnetfeldpfeil passt; sonst fehlt er in der Unterschrift.
  **Darstellung:** Karte **ACID-Abbildung** (Farbe, Standard gelb, und Deckkraft der Fläche) und Karte **ACID-Pfeile**
  (Pfeile an/aus und Größe, um ihren Anfang skaliert; Pfeildichte = Anteil der gezeigten Pfeile, ausgedünnt, nichts neu
  berechnet; Farben von Schaft, Spitze und Magnetfeldpfeil; „Magnetfeld B“ zeigt unten links die Richtung von B in
  der aktuellen Ansicht, als Pfeil oder als Kreis mit Punkt (zum Betrachter) bzw. Kreuz (vom Betrachter weg)). Ablesen:
  Zeigt B zum Betrachter, läuft ein diatroper Ringstrom im Uhrzeigersinn, ein paratroper gegen ihn. Elucida ordnet
  das nicht selbst zu.
  **Cube statt AICD:** ein Gaussian-Cube mit dem ACID-Skalarfeld (z. B. aus einem anderen Programm) ergibt die Fläche
  allein, ohne Pfeile; Isowert (Standard 0.045), Farbe und Deckkraft in der Karte ACID-Abbildung. Ein Cube mit
  negativen Werten (Orbital, Spindichte) wird abgelehnt. Sind AICD-Dateien geladen, zeigt der Reiter diese.
  Export und SI enthalten die Abbildung mit Isowert, Rechenniveau und den Zitaten der ACID-Methode.

- **Multireferenz (ORCA 6):** CASSCF-, SC-NEVPT2-, QD-SC-NEVPT2- und SORCI-Ergebnisse stehen je Block zur Auswahl, Energien,
  Konfigurationsgewichte und Besetzungen wie in der Ausgabe. Die SI übernimmt einen Block nur auf ausdrückliche Wahl.
  SORCI: gezeigt wird der abschließende DDCI3-Schritt, die Energien enthalten ORCAs Korrekturen, CI-Energie und Korrektur stehen daneben.
  ΔE_ST zwischen gewähltem Singulett und Triplett desselben Blocks, mit angezeigter Gleichung. Der Diradikalindikator ist
  y₀ = n(LUNO) und nur für natürliche Orbitale eines konvergierten Singulettzustands verfügbar. Unvollständige oder
  abgebrochene Ausgaben werden gemeldet. Im TD-DFT-Tab sind MR-Spektren nach Methode und Block wählbar; SORCI nur, wenn die
  Ausgabe für den abschließenden DDCI3-Schritt eine Absorptionstabelle druckt (Anregungsenergien und Oszillatorstärken wie
  gedruckt, nichts abgeleitet).

- **Aromatizität (HOMA):** wie im X-Ray-Tab, aus der berechneten Geometrie. Liegt auf der Seite NICS eine Rechnung
  derselben Geometrie mit Geisteratomen über einer Ringmitte, stehen NICS(0), NICS(1) und NICS(1)zz dieses Rings in
  derselben Zeile (Mittel beider Seiten).
- **NBO** (Reiter): ORCA-6-Ausgabe mit einer NBO-7.0-Analyse (`! … NBO` und ein `%nbo`-Block mit `NBOKEYLIST`). Was
  erscheint, hängt von den Schlüsselwörtern ab: NPA und NBO-Liste immer, E(2) mit der Standardanalyse zweiter Ordnung,
  die NRT-Seiten mit `NRT`, gezeichnete Resonanzstrukturen mit `NRTCML` (die Datei `<FILE>-nrt.cml` muss neben der
  Ausgabe liegen; sie wird mit in die Verbindung kopiert). Dateien in der Karte **NBO-Rechnungen** (Schritt Daten)
  laden; Beschriftung, Schwelle, Nachkommastellen, Elemente, Farben, die E(2)-Schwelle und die Zahl der gezeichneten
  Strukturen stehen in **NBO-Darstellung** (Schritt Darstellung). Der Reiter zeigt die Abbildung (natürliche Ladungen an
  den Atomen, NRT-Bindungsordnungen gesamt an den Bindungen, Bindungen zu H nur mit „H beschriften“), die
  Resonanzstrukturen, NPA, NBO-Liste (ohne CR/RY), E(2) (größte zuerst), NRT (Gewichte mit den Änderungen gegenüber
  RS 1, Bindungsordnungen ab der Schwelle), Wiberg und den SI-Text. **Wiberg-Indizes** brauchen `BNDIDX` in der
  NBOKEYLIST (z. B. `NBOKEYLIST = "$NBO NBO BNDIDX NRT NRTCML $END"`): dann bietet „Bindungen“ „Wiberg-Index (NBO,
  NAO-Basis)“, der Unterreiter „Wiberg“ zeigt die Bindungen ab der Schwelle und die Summen je Atom, die CSV die volle
  Matrix. Nicht gelesen: offenschalige Analysen, andere NBO-Versionen und Gaussian-/GENNBO-Ausgaben (Ablehnung mit
  Meldung). Weder die NRT-Bindungsordnungen noch die Wiberg-Indizes der NBO-Analyse sind die IAO-Wiberg-Bindungsordnungen,
  die das Orbitalbild aus einer Molden-Datei berechnet. „Darstellung zurücksetzen“ setzt auch die NBO-Darstellung zurück
  (Dateien, Schwellen der Tabellen und der Spin der Wiberg-Tabelle bleiben).
  **Offenschalig** (Dubletts, z. B. Radikalkationen): die NPA-Tabelle bekommt die Spalte „Spindichte (NPA)“, „Atome“
  bietet „natürliche Spindichte (NPA)“ (mit Vorzeichen), und das Feld „Spin“ (gesamt/α/β) wählt, was NBO, E(2) und
  Wiberg zeigen (NBO-Liste und E(2) gibt es nur je Spin; „gesamt“ zeigt α und β untereinander). Nicht gelesen: NRT
  offenschaliger Rechnungen, Multiplizität 3 und höher.

## Cluster-Anbindung

Im Projekt unter **Computerchemie** steht die Cluster-Ansicht neben den Reaktionspfaden und zeigt laufende und fertige Rechnungen.
Bei offenem Pfad führt die Statuskarte in der Pfadliste (☰) dorthin. Die Anbindung gilt nicht für einen bestimmten Cluster: Sie funktioniert mit jedem Linux-Server, auf den du
dich per SSH-Schlüssel einloggen kannst.

**Voraussetzungen**

- Server: Linux, Login per SSH-Schlüssel. Ein zweiter Faktor bei jedem Login geht nicht, weil Elucida im Hintergrund abfragt.
- Jobliste: Slurm mit `squeue` und `sacct`. Ohne Slurm (oder ohne Accounting) meldet die Abfrage einen Fehler. **Ordner zeigen**
  und **Ergebnisse holen** gehen trotzdem, den Ordner trägst du dann von Hand ein.
- Eigener Rechner: OpenSSH. macOS und Linux bringen es mit, unter Windows 10/11 ist es ein optionales Feature („OpenSSH-Client“).
  PuTTY und Pageant nutzt Elucida nicht, ein PuTTY-Schlüssel (`.ppk`) muss erst ins OpenSSH-Format.

**Einmal einrichten**

1. Schlüssel erzeugen, falls du noch keinen hast (mit Passphrase):

   ```bash
   ssh-keygen -t ed25519
   ```

2. Den **öffentlichen** Schlüssel (`~/.ssh/id_ed25519.pub`) auf dem Server hinterlegen, wie es dein Rechenzentrum vorgibt: über
   dessen Portal oder Antrag, sonst mit `ssh-copy-id benutzer@host`. Der private Schlüssel bleibt auf deinem Rechner.
3. Einmal im Terminal einloggen und den Fingerabdruck des Servers bestätigen. Elucida übernimmt unbekannte Server nie von selbst.

   ```bash
   ssh benutzer@host
   ```

4. Schlüssel in den Agenten laden, damit keine Passphrase mehr abgefragt wird:
   - macOS: `ssh-add --apple-use-keychain ~/.ssh/id_ed25519`, und damit das einen Neustart übersteht, in `~/.ssh/config`:

     ```
     Host *
       UseKeychain yes
       AddKeysToAgent yes
     ```

   - Windows: PowerShell als Administrator, danach `ssh-add` als normaler Benutzer:

     ```powershell
     Get-Service ssh-agent | Set-Service -StartupType Automatic
     Start-Service ssh-agent
     ```

   - Linux: `ssh-add` in der Desktop-Sitzung, aus der du Elucida startest.
5. Prüfen. Zeigt der Befehl zwei Slurm-Versionen ohne jede Rückfrage, klappt es auch aus Elucida:

   ```bash
   ssh -o BatchMode=yes benutzer@host "squeue --version && sacct --version"
   ```

6. In Elucida die Cluster-Ansicht öffnen und unter **Zugang** Host und Benutzer eintragen. Muss der Server über VPN erreicht
   werden, muss das VPN laufen.

Als Host geht auch ein Name aus `~/.ssh/config`. Dort stehen dann zum Beispiel `Port`, `IdentityFile` oder `ProxyJump`.

**Benutzung**

Solange die App offen ist, fragt sie alle 2 Minuten ab (Windows: alle 15 Minuten) und meldet fertige Jobs, auch in anderen Tabs. **Aktualisieren** fragt sofort ab. Ist Elucida nicht im
Vordergrund, kommt zusätzlich eine Mitteilung des Systems (abschaltbar unter **Zugang**). Job wählen, Dateien anhaken, **Ziel**
wählen (Verbindung oder Reaktionspfad), **Ergebnisse holen**: Ausgaben und xyz werden dort als Rechnung eingetragen, alles andere
liegt in `data/dft`. `.gbw` und `.hess` werden nicht angeboten.

**Was Elucida darf**

Elucida ruft nur das `ssh` deines Systems auf und liest weder Schlüssel noch Passwörter. Auf dem Server laufen nur `squeue`, `sacct`,
`find` und `cat`: Jobs starten oder abbrechen geht nicht, freie Befehle gibt es nicht. Host, Benutzer und Ordner stehen nur in den
lokalen Einstellungen, nie im Projekt. Unter macOS und Linux bleibt die Verbindung nach der letzten Abfrage 3 Minuten offen
(`~/.ssh/elucida-…`), das entlastet den Login-Knoten. Unter Windows ist jede Abfrage ein neuer Login, deshalb der längere Abstand. `sacct` läuft nur beim Start, bei **Aktualisieren** und wenn sich die Jobliste ändert.

**Wenn es nicht klappt**

Die Meldung von `ssh` steht unten in der Cluster-Ansicht. Lehnt der Server den Login ab, hält Elucida die automatische Abfrage an,
denn manche Rechenzentren sperren die IP nach wenigen Fehlversuchen. Nach dem Beheben geht es mit **Aktualisieren** weiter.

| Meldung | Ursache und Lösung |
|---|---|
| `Host key verification failed` | Server noch nicht bestätigt: Schritt 3. Hat sich sein Schlüssel geändert, erst beim Rechenzentrum nachfragen, dann `ssh-keygen -R host`. |
| `Permission denied (publickey)` | Schlüssel nicht im Agenten (`ssh-add -l` zeigt ihn nicht: Schritt 4) oder nicht auf dem Server hinterlegt. |
| Zeitüberschreitung, `Could not resolve hostname` | Server nicht erreichbar: VPN oder Netz prüfen. |
| `command not found` bei `squeue` oder `sacct` | Kein Slurm auf dem Server: Ordner von Hand eintragen. |
| Dateien fehlen, solange der Job läuft | Der Job rechnet in einem lokalen Ordner des Rechenknotens (`/scratch`). Elucida sieht nur gemeinsame Ordner, die Ergebnisse kommen also erst, wenn der Job sie zurückkopiert hat. |
| `find: -printf …` | Kein GNU-`find` auf dem Server, er ist also kein Linux-System. |

## Weitere-Tab

Abbildungen aus anderen Programmen (PDF, SVG, PNG) kommen **unverändert** in die SI: je Abbildung eine Unterschrift und
ein Kapitel – ein vorhandenes SI-Kapitel oder eine eigene Überschrift (in der Gesamt-SI ein eigenes Kapitel am Ende).
Das Seitenverhältnis bleibt, zwei Abbildungen je Seite wie alle anderen; nicht im Datenpaket.

## Erscheinungsbild

Das Programm folgt dem hellen oder dunklen Modus des Systems; unter **Format → Erscheinungsbild** lässt sich dauerhaft
hell oder dunkel wählen, ebenso mit dem Mond-/Sonnen-Knopf in der Werkzeugleiste (das Symbol zeigt den aktuellen Zustand). Die linke Spalte jedes Tabs ist in Schritte geteilt (meist **Daten · Auswertung · Darstellung**): die Leiste oben wechselt den Schritt, ein Punkt daran zeigt geänderte Werte, **Weiter: …** unten führt zum nächsten. Listen mit mehreren Einträgen (Spektren, Messungen, Strukturen) lassen sich mit den Pfeilknöpfen oder durch Ziehen einer Zeile umsortieren. Im Schritt Auswertung zeigt die Karte **Rechenweg**, welche Schritte der Rechnung gerade benutzt werden. Rechts neben den Reitern stehen die wichtigsten Ergebnisse als Kacheln; der Reiter **SI-Text** enthält die Bildunterschrift mit ihren Feldern und den Methodentext, jeweils zum Kopieren. Größen stehen wie im Satz: Formelzeichen kursiv, Indizes tiefgestellt, Einheiten steil und mit negativem Exponenten (mg mL⁻¹, mV s⁻¹); Namen und Summenformeln mit tiefgestellten Zahlen und kursiven Lokanten. Auswahllisten und Chips können das technisch nicht und bleiben steil. Schalter sind **Chips**: eine Pille anklicken schaltet sie an (blau) oder aus; der Tooltip nennt die Langform. Ein Feld, das **„aus“** zeigt, schaltet seine Funktion mit dem ersten Schritt nach oben ein (mit dem zuletzt benutzten Wert) und am unteren Ende wieder aus. Bereiche, die **„auto“** zeigen, gelten für die ganzen Daten: ein Klick ins Feld setzt eigene Grenzen, ein geleertes Feld stellt wieder auf automatisch. Jedes Feld mit „auto“ oder „aus“ zeigt einen kleinen Rücksetz-Pfeil, solange ein eigener Wert gilt: ein Klick stellt auf „auto“/„aus“ zurück, ebenso ein geleertes Feld beim Verlassen oder mit Enter. Selten gebrauchte Karten der linken Spalte sind eingeklappt (Klick auf den Titel klappt sie
auf); ein Titel mit **„(geändert)“** bedeutet, dass dort ein Wert vom Standard abweicht. Ergebnisse, Tabellen und
SI-Texte stehen als Reiter neben der Abbildung. Das Mausrad scrollt die Spalte; ein Feld ändert es erst, wenn es
angeklickt ist. Hinweise beim Zeichnen (z. B. ausgelassene Kurven) stehen unter der Vorschau, **Hilfe → Protokoll…**
zeigt alle Meldungen. Unten rechts unter der Abbildung steht die Bildunterschrift; exportiert wird im Tab **Export** oder mit **Strg+E**. **Vorlagen ▾** unten links speichert die Darstellung eines Tabs für andere Verbindungen (ohne Dateien, Auswertung und Bildunterschrift; auch ältere Vorlagen ändern beim Laden nur die Darstellung). Die Abbildungen
sind vom Erscheinungsbild nicht betroffen.

**Canvas dunkel / Canvas hell** in der Werkzeugleiste (Mond = dunkel, Sonne = hell; auch Format → Canvas) schaltet um; dunkel zeigt alle Diagramme, Vorschauen und Editoren auf reinem Schwarz. Farbtöne
bleiben (Rot bleibt Rot), dunkle Farben werden aufgehellt, damit sie lesbar sind. Das betrifft nur den Bildschirm, nie
Exporte, gespeicherte Dateien oder die SI.

## Abbildungsgröße für Word

Unter „Darstellung“ → „Größe“:

- **Word: halbe A4-Seite (16 × 11 cm)** (Standard). Die Abbildung wird exakt in dieser Größe gebaut,
  Schrift, Linien und Layout werden passend skaliert. Zwei Abbildungen mit einzeiliger
  Bildunterschrift passen bei Word-Standardrändern auf eine A4-Seite.
- **Benutzerdefiniert:** Breite und Höhe in cm, z. B. wenn eure Vorlage andere Ränder hat.
- **Standard:** größeres Format, eng zugeschnitten.

In Word: Einfügen → Bilder → SVG wählen, dann Rechtsklick → Beschriftung einfügen.
SVG funktioniert in Word 2019, 2021 und Microsoft 365. Bei älteren Versionen das PNG (600 dpi) nehmen.

In PDF und SVG bleibt die Struktur eine Vektorgrafik. Text steht im SVG als Pfade, sieht also
überall gleich aus, lässt sich in Word aber nicht bearbeiten.

## Schrift und Rahmen

Klappkarte **Schrift und Rahmen** als letzte Karte im Schritt **Darstellung** jedes Tabs mit Abbildung (Format → „Schrift
und Rahmen…“ zeigt sie im offenen Tab). Jede Änderung gilt sofort für **alle Tabs** (Standard); mit dem Chip **Nur dieser
Tab** bekommt der Tab ein eigenes Format (beginnt als Kopie des Standards, abgewählt gilt wieder der Standard). Alles wird
in der Verbindung gespeichert, jede Änderung lässt sich rückgängig machen; die Karte zeigt nur, was der Tab im Bild hat
(z. B. keine Symbolschrift in CV, keine Rahmen in X-Ray). **Auf Standard zurücksetzen** stellt die Vorgaben her:

- **Textschrift** und **Symbolschrift**. λ und ε stehen standardmäßig in der Symbolschrift
  (Times New Roman), wie in Origin; abschaltbar.
- **Bandenlabels:** Schriftgröße (standardmäßig automatisch), fett, kursiv, Farbe.
- **Linien** (die Karte heißt in Tabs mit Kurven „Schrift und Linien“, mit den Farben unten „Schrift, Linien und Farben“): **Kurvenbreite** als Faktor auf alle
  Kurven und **Achsenlinien** (Achsen, Rahmen, Striche in pt, „auto“ = wie gezeichnet); wie die Schrift für alle Tabs
  oder mit „Nur dieser Tab“; gilt für Vorschau, Export und Word. Nicht in X-Ray, DFT und Weitere.
- **Farben** (je Abbildung, nur feste Farben ohne Messungsliste): SEC Start/Ende, H-Cell Laden/Entladen/CE, HRMS
  gemessen/berechnet, EPR Fitkurven. Farben je Messung stehen weiter in den Messungslisten. Ein Farbknopf ohne Wirkung
  im gezeigten Bild (z. B. H-Cell mit mehreren Messungen, HRMS ohne Isotopenmuster) ist ausgegraut, der Tooltip nennt den Grund.
- **Rahmen:** geschlossener Rahmen um den Plot (auch oben und rechts; seit 1.24 Standard, wie die Origin-Abbildungen)
  und abgerundeter Rahmen um die Strukturformel.

## Beschriftungen im Bild

Karte **Beschriftungen im Bild** im Schritt **Darstellung** (UV-Vis (ε) je Serie, TD-DFT, Kinetik, Fluoreszenz, HRMS,
IR + EA, CV, SEC, H-Cell, EPR, CV-Stapel und Spektren im Vergleich; NMR, X-Ray, DFT und das Energieprofil noch nicht). Die Tabelle zeigt die Labels der gezeigten Abbildung:

- **Häkchen** = Label im Bild. Abgewählt fehlt nur das Label in der Abbildung (und in allen Exporten); Tabelle,
  SI-Zeile, Excel und Methodentext behalten den Wert. Das ist etwas anderes als eine abgewählte Bande im ε-Tab oder in
  IR, die auch aus der SI-Zeile fällt.
- **Eigener Text:** Zeile wählen, Text im Feld darunter ändern (gilt beim Verlassen des Felds; mehrzeilig wie das Label,
  Formeln wie im Bild zwischen `$…$`). Leer oder gleich dem automatischen Text = kein eigener Text. Eigene Texte
  stehen orange in der Tabelle, der Tooltip zeigt den automatischen Text.
- **Zahl geändert:** trägt das Label eine Zahl und weicht der eigene Text ab, steht unter der Vorschau „Label … weicht
  von Tabelle/SI ab“. Tabelle, SI, Excel und Bildunterschrift benutzen immer die berechneten Werte.
- **Rechtsklick auf ein Label** in der Vorschau: Text bearbeiten (zeigt die Karte), Im Bild ausblenden, Zurücksetzen.
- **Zurücksetzen** / **Alle zurücksetzen:** automatischer Text, wieder im Bild. „Standardwerte“ und Vorlagen lassen
  eigene Texte in Ruhe; jede Änderung ist ein Rückgängig-Schritt.
- Eigene Texte hängen am Label: bei Banden, Peaks und Massen (ε, SEC, IR, HRMS) an seinem Wert – ändert er sich
  (Basislinie, Peaksuche), gehört der alte Text zu keinem Label mehr und wird nicht mehr benutzt. Bei CV-Paaren,
  H-Cell-Zyklen und den Fluoreszenzmaxima bleibt der Text, der Hinweis unter der Vorschau zeigt dann die Abweichung;
  EPR-Labels hängen an Name und Lage aus dem Feld „Labels“.
- **Eigene Labels:** Rechtsklick auf eine freie Stelle der Vorschau → **Label hier einfügen**. Das neue Label steht in der
  Tabelle, sein Text im Feld darunter; ziehen verschiebt es (die Lage gilt für jede Exportgröße), Rechtsklick darauf
  bietet Text bearbeiten, Im Bild ausblenden und Label entfernen; **Zurücksetzen** entfernt das gewählte eigene Label,
  **Eigene Labels entfernen** alle. Eigene Labels stehen in allen Exporten (PDF/SVG/PNG, Word, PowerPoint, Abbildung
  kopieren), nie in Bildunterschrift oder Methodentext; automatische Labels weichen ihnen aus. Einfügen, Text,
  Verschieben und Entfernen sind je ein Rückgängig-Schritt. Eigene Labels gehören zur gezeigten Ansicht (z. B. H-Cell
  Kapazität oder Potential, IR oder Raman); die SEC-Heatmap hat keine Labels.

## Hinweise zu CDXML

- Exaktes ChemDraw-Aussehen: einen SVG/PDF/PNG-Export mit gleichem Namen neben die CDXML legen
  (siehe oben). Er gilt nur, solange er nicht älter ist als die CDXML – nach dem Bearbeiten in ChemDraw zeigte ein alter
  Export die alte Zeichnung; Elucida zeichnet dann aus der CDXML und weist darauf hin (für das exakte Bild neu
  exportieren). Sonst zeichnet Elucida die Struktur selbst aus den CDXML-Koordinaten: Bindungen, Labels wie
  geschrieben (Abkürzungen wie TMS oder Dipp bleiben), Pfeile und Texte von Reaktionsschemata; Schrift Helvetica
  (gleiche Maße wie Arial). Nur wenn die Datei etwas enthält, das diese Zeichnung nicht kann (eingebettete Bilder,
  Klammern, gebogene Pfeile …), zeichnet RDKit neu, mit Hinweis.
- Molmasse = Summe aller Fragmente (Gegenionen zählen mit).
- Lassen sich Abkürzungen wie Dipp oder Mes nicht auflösen, wird **keine** Molmasse gesetzt und eine
  Warnung angezeigt. Dann bitte die Molmasse von Hand eintragen.
- Strukturen werden aus `.cdxml` gelesen (binäre `.cdx` in ChemDraw als `.cdxml` speichern); eine `.cdx` neben einem Syntheseschema dient nur dem bearbeitbaren Objekt in Word.

## Unterstützte Daten

| Tab | Dateien |
|---|---|
| Verbindung, Strukturen | ChemDraw-**CDXML** (Summenformel und Molmasse), mit gleichnamigem SVG/PDF/PNG-Export für die exakte ChemDraw-Zeichnung; Fotos als HEIC, JPG, PNG |
| Synthese | Schema als CDXML (+ SVG/PDF), daneben **.cdx** für ein bearbeitbares ChemDraw-Objekt in Word, **.emf** für eine scharfe Vorschau |
| NMR | MestReNova-Exporte als **SVG** oder **EMF**, Mnova-Bericht (Text), **TopSpin**-Experimente/-Datensätze (Ordner), **.mnova**-Dokumente |
| IR + EA | Bruker **OPUS** (`.0`, `.1` …) und das OPUS-**PDF** mit Peakbeschriftung; Raman als Textdatei (zwei Spalten) |
| HRMS | Bericht der Massenabteilung (**.docx** oder **PDF**), Bruker-Rohdaten (**.d** mit analysis.baf) |
| UV-Vis (ε) | **Cary**-CSV/TXT-Exporte, Cary-WinUV-**.DSW/.BSW** (Leser aus [parseuv](https://pypi.org/project/parseuv/)); mehrere Dateien bilden einen Datensatz |
| TD-DFT | Die UV-Vis-Formate oben, TD-DFT-Ausgaben von **ORCA** (4–6, inkl. SOC) und **Gaussian**, SEC-Serien |
| Fluoreszenz | Cary-**Eclipse**-CSV und .FBSW (Anregungswellenlänge aus den Metadaten) |
| CV, SEC | **Gamry**-.DTA; SEC-Spektren aus **B&W Tek BWSpec** |
| EPR | Bruker **BES3T** (.dsc/.DTA, auch 2D), Magnettech-MS400-Text, **EasySpin**-Simulationen |
| X-Ray | **CIF** (Olex2/SHELXL, CCDC; mehrere `data_`-Blöcke je Datei); gemessene Pulverdiffraktogramme als `.xy`/`.xye`/Text (2θ, Intensität) |
| DFT | **xyz** (auch Trajektorien), **ORCA-6**-Ausgaben (`.out`, auch UTF-16), **Gaussian**-`.log`, Orbitale aus **Molden**- und **Cube**-Dateien |

## Probleme

- **Absturz:** Die Details stehen in `crash.log`:
  - Windows: `%LOCALAPPDATA%\Elucida`
  - macOS: `~/Library/Application Support/Elucida`
  - Linux: `~/.local/share/Elucida`

  (bis Version 1.25 hieß der Ordner `Spectravolt`, bis 1.15 `UVVisTool`; er wird beim ersten Start automatisch
  umbenannt)
- **Selbsttest:** `Elucida --selftest <ordner>` prüft alle Tabs (Einlesen, Auswertung, Abbildungen, SI- und Datenexport) und
  schreibt `selftest_report.txt`.

---

## Für Betreuer: Bauen und veröffentlichen

Die Apps baut GitHub Actions (`.github/workflows/build.yml`) für Windows, macOS und Linux.
Nach jedem Build läuft auf jedem System ein Selbsttest der fertigen App.

**Neue Version über die Weboberfläche:**

1. Geänderte Dateien hochladen: „Add file“ → „Upload files“ → „Commit changes“.
2. **Releases** → „Create a new release“ → bei „Choose a tag“ z. B. `v1.0.0` eintippen → „Create new tag“ → „Publish release“.
3. Nach etwa 20–40 Minuten hängen die drei App-Dateien am Release.

**Testbuild ohne Release:** Actions → „Build Elucida“ → „Run workflow“. Das Ergebnis liegt unten
im Lauf unter „Artifacts“ und wird nach 90 Tagen gelöscht.

**Lokal:**

```
pip install -r requirements.txt pyinstaller
python Elucida.py                      # direkt aus dem Quellcode starten (oder: python -m elucida)
python Elucida.py --selftest out       # Selbsttest
python tools/build.py                  # App bauen → dist/
```

**Ohne GUI:** `python -m elucida.core.uvvis messung.csv` wertet mit Standardeinstellungen aus.

**Dateien:**

| Datei | Inhalt |
|---|---|
| `Elucida.py` | Startdatei (auch Einstieg für PyInstaller) |
| `elucida/app/` | Hauptfenster und UV-Vis-(ε-)Tab, Verbindungs- und Projektordner, Texte, Erscheinungsbild, Update-Prüfung, Beispiele |
| `elucida/core/` | UV-Vis-Auswertung und Abbildungen, TD-DFT, Lösungsfarbe, Bilder, CDXML über RDKit |
| `elucida/tabs/` | Ein Modul je Tab (Synthese, NMR, IR + EA, HRMS, CV, SEC, EPR, X-Ray, DFT, TD-DFT, Fluoreszenz) |
| `elucida/formats/` | ChemDraw-Zeichnung, OLE-Objekte für Word, Leser für Cary .DSW/.BSW/.FBSW (aus parseuv, BSD-3-Clause) |
| `elucida/si/` | SI-Zeilen und Word-Schreiber, Excel-Report |
| `elucida/exchange/` | Messdatenpakete (ZIP) |
| `elucida/selftest.py` | Selbsttest (läuft auch in der gebauten App) |
| `tools/` | Build, Release Notes, Programmsymbol, README-Screenshots |

**Datenschutz:** Die `.gitignore` schließt CSV-, HEIC- und CDXML-Dateien aus, damit keine
unveröffentlichten Messdaten im Repository landen.

## Lizenz

Elucida steht unter der **GNU Affero General Public License v3.0** (siehe `LICENSE`).
Es gibt keine Gewährleistung.

Die App enthält folgende Bibliotheken unter ihren eigenen Lizenzen:
PySide6/Qt (LGPL-3.0), PyMuPDF (AGPL-3.0), RDKit (BSD-3-Clause), matplotlib (Matplotlib License),
NumPy (BSD-3-Clause), Pillow (MIT-CMU), pillow-heif (BSD-3-Clause, enthält libheif, LGPL-3.0),
OpenCV (Apache-2.0), ONNX Runtime (MIT), PyYAML (MIT), olefile (BSD-2-Clause), openpyxl (MIT), PyObjC unter macOS (MIT).
Der Zeicheneditor ist [Octet Draw](https://github.com/SamChemMan/Octet-Draw) (© Sam Ellis und Mitwirkende, Apache-2.0,
verändert, siehe `frontend/octet/UPSTREAM.md`) mit OPSIN (MIT), Indigo (Apache-2.0) und weiteren Bestandteilen, gelistet in
`frontend/octet/THIRD_PARTY.md` und `frontend/octet/licenses/`; er läuft in Qt WebEngine/Chromium (LGPL-3.0 u. a.).
Der Leser für .DSW/.BSW-Dateien in `parseuv_lite/` stammt aus parseuv 1.0.4
(© 2026 Ricardo J. Fernández-Terán, BSD-3-Clause, siehe `parseuv_lite/LICENSE`).
Das ISNet-Modell für die Freistellung (Apache-2.0) wird beim ersten Gebrauch aus dem
rembg-Projekt heruntergeladen und ist nicht Teil dieses Repositorys.
