[English](struktur-dft.en.md) | **Deutsch** · [zurück zur Übersicht](../../README.de.md#anleitungen)

# Kristallstruktur und DFT

**Was herauskommt:** eine ORTEP-Abbildung im Mercury-Stil (oder Kugel-Stab), ausgewählte Bindungslängen und Winkel
mit Standardabweichungen genau aus der CIF, die Kristalldatentabelle für die SI und für DFT-Rechnungen ein SI-Block mit
Koordinaten, Energien und Konvergenz.

**Was du brauchst:** die CIF (z. B. aus Olex2 oder vom CCDC); für DFT xyz-Dateien oder Ausgaben von ORCA 6 (.out) bzw.
Gaussian (.log).

![X-Ray-Tab mit Beispieldaten](../screenshots/xray_light_de.png)

## 1. CIF laden

Die CIF ins Fenster ziehen oder im Tab **X-Ray** über **CIF hinzufügen …**. Jeder `data_`-Block mit Atomen wird ein
Eintrag. Das Molekül wird über die Symmetrie vervollständigt; bei Fehlordnung zeigt der Standard den Hauptteil.

## 2. Ansicht

**Ziehen dreht**, rechte Maustaste verschiebt, Mausrad zoomt. Unter **Darstellung** wählst du Stil, Ellipsoide (50 %),
Labels und Hintergrund. Lösungsmittel und Gegenionen lassen sich ausblenden, einzelne Atome unter **Atome und
Fragmente**, sperrige Gruppen als Drahtmodell. **Ausrichten** dreht eine Bindung nach unten oder eine Ebene nach vorn.

## 3. Bindungen und Winkel

Atome anklicken: 2 = Abstand, 3 = Winkel, 4 = Diederwinkel. Die Werte mit Standardabweichung kommen **genau aus der
CIF** (z. B. 1.392(3)); fehlt ein Wert, wird er berechnet und ohne Standardabweichung markiert. Gewählte Werte landen
in der Bildunterschrift oder – bei mehr als acht – in einer Tabelle.

## 4. Tabellen und Bildunterschrift

Die Reiter **Bildunterschrift** und **Tabellen** neben der Abbildung zeigen den Vorschlag für die Unterschrift und die
Kristalldatentabelle. Interne Referenz und CCDC-Nummer trägst du in der Strukturliste ein. **Kopieren** behält
Kursivschrift und Hoch-/Tiefstellung in Word.

## 5. DFT

Im Tab **DFT** die xyz- oder Ausgabedatei hinzufügen. Drehen und Messen wie bei X-Ray. Zum Umnummerieren
**Nummerieren** drücken und die Atome der Reihe nach anklicken, dann **Übernehmen** – oder die Nummerierung **wie
Vorlage** von einer anderen Geometrie oder der CIF übernehmen. **xyz speichern** schreibt eine neue Datei (Zeilen
unverändert, nur umsortiert).

**Orbitale:** in der Karte **Orbitale** eine Molden-Datei (ORCA: `orca_2mkl name -molden`) oder einen Cube (ORCA:
`orca_plot`) hinzufügen. Passt sie zur gewählten Geometrie, hängt sie dort an. HOMO und LUMO werden angelegt, weitere
MOs über **Aus Molden** und **+**. Gezeichnet wird wie in IboView (Isofläche mit 80 % der Orbitaldichte); im Export
entsteht je Orbital eine eigene Abbildung.

## 6. SI

Der Reiter **Rechnung für die SI** zeigt den Block mit Ladung, Multiplizität, Punktgruppe, Koordinaten und
E_el/H/G. **SI (Word)** setzt Kristallstruktur und DFT-Rechnungen (zweispaltig) in den SI-Abschnitt.
