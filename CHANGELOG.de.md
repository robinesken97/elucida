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
- **CV: Diffusionskoeffizient** aus der Randles-Ševčík-Steigung (mit Elektronenzahl, Elektrodenfläche, Konzentration
  und Temperatur; Intervall aus der Unsicherheit der Steigung).
- **EPR: gemeinsamer Fit mehrerer S = ½-Spezies.** „Gemeinsam fitten“ verfeinert alle Simulationen einer Messung
  gleichzeitig.
- **Neuer Tab H-Cell (Laden und Entladen).** Liest Gamry-Dateien „Cyclic Charge Discharge“ mit ihren
  Schrittdateien aus CHARGE_DISCHARGE: Kapazität je Zyklus (Laden, Entladen, Anteil der theoretischen Kapazität aus der
  Datei oder je Messung eingegeben) mit Coulomb-Effizienz auf zweiter Achse, mehrere Messungen in einem Bild; oder
  Potential gegen die echte Zeit für gewählte Zyklen mit unterbrochener Zeitachse. Ergebnisse je Zyklus, Erhalt und
  mittlere Effizienz als Kacheln, Bildunterschrift und Methodentext für die SI, CSV der Zyklustabelle.
- **Neuer Tab „UV-Vis-Kinetik“.** Spektren einer Lösung über die Zeit (Stabilität über Tage oder eine Reaktion) aus
  einer oder mehreren Cary-Dateien: Aufnahmezeiten aus der Datei, je Spektrum eine Reihe, Spektren im Farbverlauf der
  Zeit oder Absorbanz bei λ gegen die Zeit (wahlweise Maximum im Bereich ± n nm, relativ zum ersten Spektrum), Fit
  erster Ordnung mit k, 95-%-Intervall und Halbwertszeit.
- **SEC: Ansicht „Heatmap“.** Die ganze Spektrenserie in einem Bild: Wellenlänge gegen Spektrenfolge, Absorbanz oder
  ΔA zum ersten Spektrum als Farbe mit Farbskala; die y-Achse zeigt das Potential, ohne Potentiale die Zeit oder die
  Nummer.

### Geändert
- Felder mit „auto“ oder „aus“ (alle Tabs): ein Symbol im Feld stellt mit einem Klick zurück; ein geleertes Feld gilt
  ebenfalls als „auto“/„aus“.
- **CV-Basislinie** endet in neuen Verbindungen 0,20 V vor dem Peak statt 0,15 V: Der Peakstrom ideal reversibler Wellen
  fällt damit höchstens 1 % zu klein aus (vorher 1–3 %). Gespeicherte Verbindungen behalten ihren Wert.
- **CV-Stromdichte** nimmt die eingetragene Elektrodenfläche; ohne Eintrag die der Messdatei, mit Hinweis.
- **Mengenprüfung (Synthese)** lässt über die Rundung hinaus nur noch 0,01 % Spielraum (vorher 0,5 %).
- **Kristalldaten-Tabelle** in Normschreibweise („Density (calc.) / g cm⁻³“, „Formula weight / g mol⁻¹“).
- EPR: Ansicht und Einstellungen der Intensitätsauswertung stehen in einer Karte mit einer Ansichtswahl.
- EPR: „Dunkelspektrum für alle Messungen übernehmen“ blendet das Dunkelspektrum selbst im Bild aus; das Häkchen in
  der Liste zeigt es wieder.
- Beispielprojekt: Das Produkt füllt jeden Tab mit zusammenpassenden erfundenen Daten (jetzt auch HRMS-Rohdaten mit
  Spektrum und Chromatogramm, HOMO/LUMO und ein NICS-Scan im DFT-Tab, eine Abbildung unter „Weitere“; die H-Zelle
  zykelt um dasselbe E½ wie das CV); die README-Bilder zeigen die Tabs mit diesen Daten.

### Behoben
Aus einer Prüfung aller Rechnungen gegen die Literatur (Formeln, Konstanten und Statistik stimmten; diese Punkte nicht):
- **EPR, Feldeinheit von Textdateien:** Stand die Einheit nicht im Kopf, wurde sie stillschweigend geraten (Feldwerte
  über 1500 = Gauß); W-Band-Daten in mT oder ein Tieffeld-Ausschnitt in G lagen damit um den Faktor 10 daneben. Die
  Annahme steht jetzt bei der Messung und lässt sich unter „Feldeinheit der Datei“ bestätigen oder ändern.
- **EPR, Kerne:** ⁶Li, ⁷Li, ⁹Be, ¹⁰B, ¹¹B, ²³Na, ²⁷Al und weitere Isotope bis ²⁰⁹Bi fehlten in der Tabelle; „I=3/2“
  (Spin als Bruch) wird jetzt gelesen.
- **Tab „Verbindung“:** Die Chips „Abbildungen von“ blieben nach einem Sprachwechsel leer.
- **EPR, Zerfall unter einer Temperaturrampe:** Das Integral wurde nur an den Messpunkten ausgewertet; bei wenigen
  Spektren (10 K Abstand) lag E_a dadurch etwa 1,4 % zu hoch. Jetzt wird die Temperatur zwischen den Spektren
  interpoliert. Werte aus eng gemessenen Rampen ändern sich praktisch nicht.
- **EPR, g nach geänderter Feldkalibrierung:** Ein vor der Kalibrierung gefittetes g wird nicht mehr berichtet, bis neu
  gefittet ist (0,1 mT Verschiebung entsprechen 6 · 10⁻⁴ in g).
- **EPR:** Kopplungen in MHz mit µ_B/h statt einem gerundeten Faktor (wirkt erst ab etwa 400 MHz in der 2. Stelle).
- **CV:** Der Ladestromsprung am Umkehrpunkt hängt nicht mehr davon ab, zu welchem Ast der Messpunkt am Umkehrpunkt zählt.
- **DFT, Gaussian:** Bei MP2, Doppelhybriden und CCSD(T) wird die Gesamtenergie mit Korrelationsanteil gelesen, nicht
  nur der SCF-Anteil. ORCA war nicht betroffen.
- **Molmasse:** Zeichnung, Schema und MS-Bericht rechnen jetzt mit denselben Atommassen (IUPAC 2021) wie
  Elementaranalyse und eingetippte Formeln; vorher konnte sich die zweite Nachkommastelle unterscheiden.
- **Rundung:** ε, Äquivalente und Ausbeuten runden bei genau 5 an der letzten Stelle kaufmännisch wie λ und Excel.
- **Excel-Report:** Ein Fehler unter einer halben Einheit zeigt wie in der App „1“, nicht „0“.
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
