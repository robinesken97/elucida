[English](synthese-bis-si.en.md) | **Deutsch** · [zurück zur Übersicht](../../README.de.md#anleitungen)

# Synthese und Charakterisierung bis zur SI

**Was herauskommt:** der SI-Abschnitt einer Verbindung als Word-Datei – „Synthesis of **X**“ mit bearbeitbarem
ChemDraw-Schema und Vorschrift, der Charakterisierungsabsatz (m.p.; NMR; IR; HR-MS; UV-Vis; Elementaranalyse) und
die Spektren zu zweit je Seite.

**Was du brauchst:** das Reaktionsschema als CDXML (dazu aus ChemDraw gleichnamig eine `.cdx`, damit es in Word
bearbeitbar bleibt), die NMR-Spektren als SVG aus MestReNova, die IR-Datei aus OPUS (oder den OPUS-PDF-Ausdruck), den
HRMS-Bericht der Massenabteilung (.docx) und die Werte der Elementaranalyse.

![Synthese-Tab mit Beispieldaten](../screenshots/synthesis_light_de.png)

## 1. Verbindung anlegen

**Datei → Neue Verbindung…** (oder **Neue Verbindung** auf der Seite eines Projekts), dann **Verbindung …** in der Werkzeugleiste: Name (z. B. die Probennummer) und die
CDXML der Verbindung. Daraus kommen Summenformel und Molmasse für alle Tabs. Den Schmelzpunkt trägst du dort ebenfalls
ein.

## 2. Synthese

Im Tab **Synthese**: **Schema wählen …** (CDXML), dann die Vorschrift schreiben. Mengen wie
„(1.03 g, 5.00 mmol, 1.0 eq.)“ prüft das Programm gegen die Reagenzientabelle – **Aus Schema** füllt sie mit Edukten,
Reagenzien und Produkt, **Klammer einfügen** setzt die berechnete Klammer an der Schreibmarke ein. Abweichungen jenseits
der Rundung der angegebenen Stellen werden markiert.

## 3. NMR

Im Tab **NMR** die SVG-Exporte aus MestReNova hinzufügen oder ins Fenster ziehen. Kern und Reihenfolge (¹H, ¹³C, …,
2D) erkennt das Programm. Die Struktur kommt aus dem Dialog Verbindung und wird an eine freie Stelle gesetzt;
du kannst sie in der Vorschau verschieben. Unter **NMR-Zeile** den Multiplettbericht aus Mnova einfügen (alle Kerne in
ein Feld); die ¹³C-Zeile entsteht auch mit **Zeile aus Peaklabels**.

## 4. IR und Elementaranalyse

Im Tab **IR + EA** die OPUS-Datei oder den OPUS-PDF-Ausdruck wählen. Mit dem PDF gelten genau die OPUS-Peaks, sonst
sucht das Programm die Banden selbst (Peakschwelle). Banden, die nicht in die Liste sollen, abhaken. Für die
Elementaranalyse die gefundenen C/H/N/S-Werte eintragen, ggf. ein Solvat (`0.5 CH2Cl2`); Abweichungen über 0,4 %
werden markiert.

## 5. HRMS

Im Tab **HRMS** den Bericht der Massenabteilung wählen oder ins Fenster ziehen. Formel und Ion prüfen; found ist der
Wert aus dem Bericht. Mit den Bruker-Rohdaten (.d) siehst du zusätzlich Chromatogramm, gemitteltes Spektrum und das
berechnete Isotopenmuster und kannst einen Peak anklicken.

## 6. UV-Vis und weitere Abbildungen

Die UV-Vis-Zeile kommt aus dem Tab **UV-Vis (ε)** (siehe [Anleitung UV-Vis](uvvis-epsilon.de.md)). Abbildungen
aus Overlay, Fluoreszenz, CV, SEC und EPR kommen automatisch in die SI, sobald die Tabs Daten haben.

## 7. SI erstellen

**SI (Word)** in der Werkzeugleiste: Teile auswählen und exportieren. Die Datei liegt unter `SI/`. Danach
zählt das Programm auf, was noch fehlt (z. B. kein Schmelzpunkt). Die Word-Datei hat den Stil der Gruppen-SI (Arial 11,
Blocksatz, Abbildungsnummern als Felder).
