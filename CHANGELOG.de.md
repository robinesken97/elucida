[English](CHANGELOG.md) | **Deutsch**

# Änderungen

## 1.3.0 – 2026-11-17

### Neu

#### Export und SI
- **Tab „Export“** (letzter Tab, Gruppe „Ausgabe“): Formate PDF, SVG, PNG und neu **PPTX** (eine Folie je Abbildung) für
  alle Abbildungen einer Verbindung; die Spalte **SI** wählt je Abbildung, was in die SI kommt.
- **Projektseite, Reiter „Export“:** Gesamt-SI (Vorlage, Kapitel, Optionen, Verbindungen) und Datensätze an einer Stelle.
- **Anforderungen der Zeitschriften:** Karte **Reinheit** im Tab Verbindung, **FID for Publication**, Bezeichner
  „Supplementary Figure“/„Figure S“ samt umgestellten Verweisen, Data Availability Statement.
- **Abbildung kopieren (SVG)** (Menü Bearbeiten, Strg+Umschalt+C / ⌘⇧C) für die rechts gezeigte Seite.
- **Schrift, Linien und Farben:** Kurvenbreite und Achsenlinien gehören zum Textformat (global oder „Nur dieser Tab“);
  feste Farbrollen (SEC Start/Ende, H-Cell, HRMS, EPR-Fits) je Abbildung wählbar.

#### NMR
- **Eigene Spektren aus Bruker-Rohdaten oder MNova-Dokumenten** (optional, Mnova-SVG bleibt Standard): Verarbeitung,
  Phase, Basislinie, Referenzierung, Integrale, Ausschnitte, Labels, 2D-Spektren; Tasten wirken ohne vorherigen Klick.
- **MNova-Export über ein installiertes MNova** (macOS und Windows; Windows noch nicht an einer echten Installation geprüft).
- Einzelne TopSpin-Dateien (fid, ser, acqus, 1r …) lassen sich wie in MNova ablegen.
- **Prüfungen:** Kernzahl gegen die Summenformel; ¹³C-Signale bei Lösungsmittel- oder Verunreinigungssignalen
  (Fulmer 2010); Verbindungsnummer und Messangaben im Spektrum; Prüfung des Achsenbereichs.

#### UV-Vis, Photophysik, TD-DFT
- **UV-Vis-Titration** im Kinetik-Tab (Äquivalente je Spektrum).
- **Fluoreszenz:** Lebensdauer aus Abklingkurven (1–2 Exponentiale, IRF), Kennwerte, Anregungsspektrum.
- **TD-DFT:** Tabelle der Anregungen und natürliche Übergangsorbitale (NTO).

#### IR, MS, Elementaranalyse
- Berechnetes gegen gemessenes IR (Frequenzen aus ORCA/Gaussian); **Raman**-Spektren.
- Elementaranalyse als Doppelbestimmung mit der 0,4-%-Prüfung; HRMS wie von den Zeitschriften verlangt mit 5 ppm geprüft.

#### CV
- Karte **Messbedingungen** mit dem Aufbau-Text, den die Zeitschriften verlangen.
- Pulsverfahren aus Gamry-Dateien (DPV, Square-Wave).

#### EPR
- Spindichte und berechnete Hyperfeinkopplungen aus Gaussian 16 und ORCA 4–6.1, Zuordnung zu den experimentellen
  Gruppen, **EasySpin-Startskript**.
- Messparameter und Einheit der Kopplungen in der Bildunterschrift; **Spinzählung** gegen eine Kalibrierung.

#### X-Ray
- **Packungsbild** mit Kontakten zwischen Molekülen und Symmetriecodes.
- **Pulverdiffraktogramm (PXRD)** aus der CIF, wahlweise gegen eine Messung.
- **Aromatizität (HOMA)**, auch im DFT-Tab.

#### DFT
- **3D-NICS** und **ACID** (aus der AICD-Ausgabe).
- **NBO-7**-Analyse (Ladungen, Wiberg-Indizes, NRT-Resonanzstrukturen).
- **Energietabelle** mit xyz-Koordinaten wie von den Zeitschriften verlangt; Atomladungen.

### Geändert
- **„Darstellung zurücksetzen“** (vorher „Alles auf Standard“) setzt nur das Aussehen einer Abbildung zurück, nie Daten
  oder Zahlen.
- Der Tab **„UV-Vis-Overlay“ heißt jetzt „TD-DFT“**; in der Tab-Leiste „TD-DFT“ und „Kinetik“.
- λ-Labels stehen knapp über ihrer Bande; der Pfeil der CV-Messrichtung steht über dem Voltammogramm.
- **Nichts wechselt von selbst:** abgelegte Dateien und Messdaten aus einem anderen Tab bleiben im offenen Tab, mit
  Einblendung und Punkt am Ziel-Tab.
- **Eine Meldung nach jedem Export** (Exportieren, SI, Gesamt-SI, Datenpakete).
- **Reaktionspfad** im Rahmen der Tabs (eine Reiterzeile, Aktionen daneben).
- **Schneller:** beim Wechsel der Verbindung werden die zuvor geöffneten Tabs nicht mehr alle neu gebaut; Orbitale und
  Flächen drehen ruhiger.
- Einheiten im Tabellenkopf statt in den Zellen; CV-Potentiale und Kinetik wie in Abbildung und Methodentext.
- Ergebnisseiten ohne Daten sind ausgeblendet.

### Behoben
- **Laden einer Vorlage löschte Daten** (Rechnungen und Auswerteeinstellungen wurden mitgetragen).
- **Verbindungsnamen mit Punkt** („S3.1“) ergaben Exporte namens „S3.pdf“.
- **Reaktionspfad:** Profil in PNG/PDF verschoben; ein vor dem Einsetzen des Profils geschlossener Pfad blieb leer.
- **Strengere Leser:** abgeschnittene oder beschädigte Dateien (ORCA/Gaussian, Gamry, BWSpec, Cary, EPR-Text, Cube)
  werden mit klarer Meldung abgelehnt statt verkürzt oder falsch gelesen; alte Projekte mit solchen Dateien öffnen weiter.
- **Datenpaket und Verschieben von Ordnern:** neue Rechnungs- und Messdateien (IR-Rechnung, EPR, ACID, NBO, Raman) fehlten.
- **SI und Word:** DFT- und EPR-Teile mit und ohne Messspektren, Abwahl von Abbildungen, Verweise, Unterschriften.
- **Zahlen:** kein „−0.000“ mehr; HRMS-ppm, Fluoreszenz- und CV-Werte gerundet wie in den Tabellen.
- Viele Details in EPR, X-Ray-Packung/PXRD, NMR, NTO/NICS/NBO und der Oberfläche (Beschriftungen, ausgegraute Karten,
  dunkles Design).

## 1.1.0 – 2026-11-13

### Neu
- **Neue Tabs:** H-Cell (Laden und Entladen) und UV-Vis-Kinetik.
- **Projektseite: Vergleich** mehrerer Verbindungen (CV-Stapel, UV-Vis-Overlay, Eigenschaftstabelle; Normierung auf eine
  Bande).
- **X-Ray:** Vergleich mit einer berechneten Geometrie.
- **EPR:** Basislinie nach Wahl, isotherme Zerfälle und Arrhenius, gemeinsamer Fit mehrerer S = ½-Spezies, Simulation
  unter der Messung.
- **CV:** Diffusionskoeffizient aus der Randles-Ševčík-Steigung.
- **Energieprofil** mit Multireferenz-Plateaus (CASSCF, NEVPT2, SORCI); Plateaus lassen sich ziehen.
- **SEC:** Ansicht „Heatmap“; **Overlay:** SORCI-Spektren.
- Mehrere Strukturen in einem Bild haben denselben Maßstab.

### Geändert
- Felder mit „auto“ oder „aus“ lassen sich mit einem Klick zurückstellen.
- CV: Basislinie endet 0,20 V vor dem Peak; die Stromdichte nimmt die eingetragene Elektrodenfläche.
- Mengenprüfung erlaubt über die Rundung hinaus nur 0,01 %; Kristalldaten-Tabelle in Normschreibweise.
- Einheitliche Tabellen und Listen in allen Tabs; Octet Draw 1.1.2.

### Behoben
- EPR: Feldeinheit von Textdateien wird nicht mehr geraten; fehlende Kerne ergänzt; Unterschriften, Rampen und g nach
  der Kalibrierung.
- Einheitliche Atommassen (IUPAC 2021) und kaufmännische Rundung überall, auch im Excel-Report.
- Mindestbreite des Fensters, Seitenaufbau in Word und mehrere Details im Layout.

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
