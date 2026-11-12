[English](CHANGELOG.md) | **Deutsch**

# Änderungen

## 1.1.0 – 2026-11-12

### Neu
- **EPR: Basislinie nach Wahl.** Neben dem Polynom gibt es „Glatt“ (folgt breitem Untergrund, lässt schmale Linien
  stehen, kommt ohne Dunkelspektrum aus; einziger Wert ist die Breite) und „Spline“ (durch die Mittel der
  signalfreien Bereiche). Methodentext und exportierte Spektren nennen das Verfahren.
- **EPR: isotherme Zerfälle und Arrhenius.** Gegen die Zeit wird je Temperatur ein Zerfall erster Ordnung gefittet
  (k mit 95-%-Intervall, wahlweise nur die Anfangsphase über „Fit bis Verlust“); die Ansicht „1/T (Arrhenius)“ liefert
  E_a und ln A. Temperaturen kommen aus der Messdatei.
- **EPR: gemeinsamer Fit mehrerer S = ½-Spezies.** „Gemeinsam fitten“ verfeinert alle Simulationen einer Messung
  gleichzeitig.

### Geändert
- Felder mit „auto“ oder „aus“ (alle Tabs): ein Symbol im Feld stellt mit einem Klick zurück; ein geleertes Feld gilt
  ebenfalls als „auto“/„aus“.
- EPR: Ansicht und Einstellungen der Intensitätsauswertung stehen in einer Karte mit einer Ansichtswahl.
- EPR: „Dunkelspektrum für alle Messungen übernehmen“ blendet das Dunkelspektrum selbst im Bild aus; das Häkchen in
  der Liste zeigt es wieder.

### Behoben
- Die Legende lag bei sehr dichten, verrauschten Kurven über den Kurven; sie rückt jetzt wie vorgesehen neben die Achse.

## 1.0.0 – 2026-11-11

Erste stabile Version.

### Was Elucida kann
- **Eine Verbindung, alle Daten:** Tabs in der Reihenfolge der SI – Verbindung (Name, Formel, Zeichnung), Synthese
  (Schema, Vorschrift, Mengenprüfung), NMR (MNova), IR + EA, HRMS, UV-Vis (ε aus Verdünnungsreihen), UV-Vis-Overlay mit
  TD-DFT, Fluoreszenz, CV, SEC, EPR, X-Ray (CIF), DFT (Geometrien, Orbitale, Energieprofil, NICS, Multireferenz) und
  fremde Abbildungen.
- **Abbildungen wie für die Publikation:** PDF, SVG und PNG in fester Größe, mit Struktur, Beschriftungen und
  Bildunterschrift; Vorschau maßstabsgetreu.
- **SI auf Knopfdruck:** Word-Abschnitt je Verbindung und Gesamt-SI für das ganze Projekt, Methodentexte der Auswertungen,
  Datenpakete für das Repositorium.
- **Projekte:** Übersicht mit Checkliste je Verbindung, Suche, Reaktionspfade über mehrere Verbindungen, Anbindung an den
  Rechencluster.
- **Zeichnen im Programm** mit Octet Draw; ChemDraw-Dateien werden unverändert übernommen.
- Deutsch und Englisch, helles und dunkles Design, Windows, macOS und Linux.
