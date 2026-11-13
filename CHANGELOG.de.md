[English](CHANGELOG.md) | **Deutsch**

# Änderungen

## 1.1.0 – 2026-11-13

### Neu
- **X-Ray: Vergleich mit einer berechneten Geometrie.** Im Schritt „Auswertung“ wird eine Geometrie aus dem DFT-Tab
  oder einer Datei (xyz, ORCA- oder Gaussian-Ausgabe) der Kristallstruktur nur über das Bindungsnetz zugeordnet
  (gleiche Summenformel, gleiche Verknüpfung der Schweratome, gleich viele H je Atom; nie nach Abstand oder
  Reihenfolge). Unter symmetrisch gleichwertigen Zuordnungen gilt die mit der kleinsten RMSD der Schweratome nach
  Überlagerung, die RMSD wird angezeigt; ergeben gleich gute Zuordnungen verschiedene Werte, werden die Parameter
  genannt. Andere Zusammensetzung oder Verknüpfung wird mit den abweichenden Atomen abgelehnt; bei Lösungsmittel oder
  Gegenionen wird das Fragment gewählt. Die Zuordnung steht als Tabelle da und wird mit der Verbindung gespeichert. Die
  Tabelle der ausgewählten Parameter bekommt eine Spalte mit dem Rechenwert (Bindungslängen 3, Winkel 1
  Nachkommastelle, ohne Standardabweichung), wahlweise Δ = Rechnung − Kristall, in der App, in Excel/CSV und in Word;
  der Kopf nennt die Methode, eine Fußnote die Geometrie (Gasphase oder solvatisiert) und die RMSD.
- **Projektseite: Vergleich.** Beliebig viele benannte Vergleiche über die Verbindungen eines Projekts: CV-Stapel
  (je Verbindung ein Cyclovoltammogramm, Peakpotential am Peak, Struktur neben der Kurve, Scanpfeil je Kurve;
  andere Referenzskalen werden abgelehnt, nie umgerechnet), UV-Vis- und Emissionsspektren in einem Bild und eine
  Eigenschaftstabelle (Werte aus den Tabs, eigene Größen und Zeilen, Gruppenkopf, überschriebene Zellen markiert,
  drehbar; Word, Excel, CSV, Kopieren als formatierter Text). Nichts wird neu ausgewertet: jede Verbindung legt beim
  Speichern einen kleinen Stand ihrer Tabs ab; veraltete oder fehlende Stände werden angezeigt und mit
  „Aktualisieren“ erneuert. Das Beispielprojekt enthält einen Spektrenvergleich und eine Tabelle.
  Vergleiche können in die Gesamt-SI (Abbildung oder Tabelle mit fortlaufender Nummer, Kapitel nach Art oder eigene
  Überschrift); der CV-Stapel zeigt je Verbindung einen der ersten zehn Zyklen (Zahlen am Peak nur beim ausgewerteten);
  die Tabelle übernimmt X-Ray-Parameter, Raumgruppe und Kristallsystem, DFT-Energien und HOMO/LUMO sowie IR-Banden und
  NMR-Verschiebungen am nächsten an einem Ziel innerhalb einer Toleranz; Spektren auch als IR und EPR (Feldachse nur bei
  einer Mikrowellenfrequenz oder auf eine Referenz skaliert, sonst g-Achse); Rückgängig und Wiederholen gelten im
  offenen Vergleich. Im Spektrenvergleich und im CV-Stapel steht die Struktur jeder Verbindung im Bild, als Vorgabe
  in der Farbe ihrer Kurve (abschaltbar, auch schwarz): am höchsten Punkt der eigenen Kurve, gestapelt rechts über der
  eigenen Grundlinie.
- **Strukturen gleich groß:** Mehrere Strukturen in einem Bild (Vergleich, UV-Vis-Overlay) haben immer denselben
  Zeichenmaßstab (gleiche Bindungslänge, unabhängig vom ChemDraw-Stil). Die Größe gilt für die breiteste; das Mausrad
  auf einer Struktur ändert alle.
- **Vergleich:** Normierte UV-Vis-Spektren lassen sich auf eine gewählte Bande normieren (**Normierung [nm]**: das
  Maximum im Bereich wird 1, z. B. die Bande über 400 nm statt der im UV; ohne Bande im Bereich wird die Verbindung
  nicht gezeigt, ein Hinweis sagt das). Der Reiter „Vergleich“ zeigt die Vergleiche als Karten wie
  die Reaktionspfade; ein Klick öffnet den Vergleich in voller Fenstergröße (Abbildung so groß wie in den Tabs der
  Verbindungen), zurück über die Pfadleiste. Spektrenvergleich und CV-Stapel haben den Reiter „SI-Text“ mit der ganzen
  Bildunterschrift zum Kopieren. Im UV-Vis-Overlay gab es den Normierungsbereich schon.
- **Reaktionspfad:** Die Zeichenfläche „Gestalten“ zeigt beim ersten Öffnen eines Pfads mit Rechendaten gleich das
  Energieprofil (vorher leer, auch im Beispielprojekt).
- **Energiediagramm:** Plateaus lassen sich im Bild mit der Maus waagerecht ziehen (im schematischen Bild auch in der
  Höhe; der Energiewert bleibt der echte). Neue Vorlage „Artikel“: ohne Rahmen mit Pfeil, kräftige kurze
  Plateaus, gestrichelte Verbinder, Vorzeichen, Name und Wert fett-kursiv unter dem Plateau. Alles daran ist einzeln
  einstellbar: Lage und Schrift der Beschriftung, Vorzeichen, Achsentitel (auch mehrzeilig), Plateaubreite; dazu
  Abschnitte als Balken mit Text unter dem Profil. Die Einheit ist wählbar (kcal mol⁻¹, kJ mol⁻¹, eV): Werte, Achse
  und Bildunterschrift werden umgerechnet. Die Vorlagen stehen jetzt in einer Auswahlliste.
- **Verbindungsliste:** Die Punkte der Methoden stehen alle im selben Abstand (vorher eine breitere Lücke nach „m.p.“).
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
- **EPR: Simulation unter der Messung.** Gestapelt liegt eine Simulation bisher auf ihrer Messung; der neue Schalter
  in der Karte „Simulationen“ zeichnet sie auf einer eigenen Ebene direkt darunter (gemessen oben, simuliert unten); der Abstand der beiden ist einstellbar.
- **Neuer Tab H-Cell (Laden und Entladen).** Liest Gamry-Dateien „Cyclic Charge Discharge“ mit ihren
  Schrittdateien aus CHARGE_DISCHARGE: Kapazität je Zyklus (Laden, Entladen, Anteil der theoretischen Kapazität aus der
  Datei oder je Messung eingegeben) mit Coulomb-Effizienz auf zweiter Achse, mehrere Messungen in einem Bild; oder
  Potential gegen die echte Zeit für gewählte Zyklen mit unterbrochener Zeitachse. Ergebnisse je Zyklus, Erhalt und
  mittlere Effizienz als Kacheln, Bildunterschrift und Methodentext für die SI, CSV der Zyklustabelle.
- **Neuer Tab „UV-Vis-Kinetik“.** Spektren einer Lösung über die Zeit (Stabilität über Tage oder eine Reaktion) aus
  einer oder mehreren Cary-Dateien: Aufnahmezeiten aus der Datei, je Spektrum eine Reihe, Spektren im Farbverlauf der
  Zeit oder Absorbanz bei λ gegen die Zeit (wahlweise Maximum im Bereich ± n nm, relativ zum ersten Spektrum), Fit
  erster Ordnung mit k, 95-%-Intervall und Halbwertszeit.
- **Energieprofil mit Multireferenz-Plateaus.** CASSCF-/NEVPT2-/SORCI-Rechnungen (Einzelpunkt oder die Rechnung selbst)
  fallen nicht mehr heraus: je Plateau wählen **Methode** und **Zustand** die Zustandsenergie (Vorgabe: höchste Theorie
  der Datei, Wurzel 0); die Unterschrift nennt Methode und Wurzel. Ohne eigene Frequenzrechnung zeigt das Plateau seine
  elektronische Energie, mit Hinweis.
- **Overlay: SORCI-Spektren** sind wie die anderen Methoden angeregter Zustände wählbar, wenn die Ausgabe für den
  abschließenden DDCI3-Schritt eine Absorptionstabelle druckt.
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
  zykelt um dasselbe E½ wie das CV); die README-Bilder zeigen die Tabs mit diesen Daten. Dazu jetzt ein Reaktionspfad
  (vier Spezies mit Übergangszustand) unter Computerchemie und eine CASSCF-/NEVPT2-Rechnung des Produkts für die
  DFT-Seite „Multireferenz“.
- **CV:** Die Kurven laufen nicht mehr bis an den Rahmen: bei automatischem Bereich bleibt links und rechts ein
  schmaler Rand (im CV-Tab und im CV-Stapel).
- **Einheitliche Oberfläche:** Listen von Messungen verteilen ihre Spaltenbreiten nach Inhalt (kein abgeschnittener
  Name neben einer leeren Spalte, keine Zahl an Zahl); die ausgewählten Parameter im X-Ray-Tab und die Abbildungen unter
  „Weitere“ sind Tabellen wie überall; mehrzeilige Textfelder rücken ihren Text so weit ein wie einzeilige. Symbole in Knöpfen
  stehen nicht mehr dicht am Text (8 statt 4 px).
- **Einheitliche Tabellen:** Ergebnistabellen (UV-Vis, CV, UV-Vis-Kinetik, H-Cell) füllen die Seite ohne Leerraum
  rechts und schneiden nichts ab. Was bisher als Textzeilen unter der Tabelle stand, ist eine zweite Tabelle: beim CV
  die Scanraten-Analyse (Steigung, Achsenabschnitt, R², log-log-Steigung, D), bei der Kinetik Verlauf und Zerfall je
  Reihe, bei der H-Cell die Zusammenfassung je Messung, im EPR-Tab die isothermen Zerfälle je Temperatur; Referenz und Warnungen stehen getrennt darunter. Die
  DFT-Vorschau „Rechnung für die SI“ zeigt Konvergenz, Energien und Koordinaten als Tabellen im selben Stil (die
  kopierte Fassung und der Word-Export bleiben, wie sie waren).
- **Word-Export:** Methodentexte setzen Zehnerpotenzen und t½ richtig (vorher wörtlich „10^-2“ und „t1/2“ bei
  UV-Vis-Kinetik, EPR-Zerfällen und dem Diffusionskoeffizienten, „cm2“ ohne Hochstellung); die Unterschrift des
  Energieprofils schreibt kcal mol⁻¹ hochgestellt. Die Eigenschaftstabelle im Vergleich füllt wieder die Seite.
- **Octet Draw 1.1.2** (bisher 1.1.1) als Zeichenprogramm: unter anderem liest die Reagenzientabelle Äquivalente
  aus dem Text über dem Pfeil, und sie lässt sich an jeder Stelle greifen und verschieben.

### Behoben
Aus einer Prüfung aller Rechnungen gegen die Literatur (Formeln, Konstanten und Statistik stimmten; diese Punkte nicht):
- **EPR, Feldeinheit von Textdateien:** Stand die Einheit nicht im Kopf, wurde sie stillschweigend geraten (Feldwerte
  über 1500 = Gauß); W-Band-Daten in mT oder ein Tieffeld-Ausschnitt in G lagen damit um den Faktor 10 daneben. Die
  Annahme steht jetzt bei der Messung und lässt sich unter „Feldeinheit der Datei“ bestätigen oder ändern.
- **EPR, Kerne:** ⁶Li, ⁷Li, ⁹Be, ¹⁰B, ¹¹B, ²³Na, ²⁷Al und weitere Isotope bis ²⁰⁹Bi fehlten in der Tabelle; „I=3/2“
  (Spin als Bruch) wird jetzt gelesen.
- **EPR-Bildunterschriften** der Ansichten Intensität gegen Zeit/Temperatur/Nr. und Arrhenius lauteten „EPR spectra
  of …“; sie sagen jetzt, was aufgetragen ist, und nennen nur Werte der gezeigten Fits.
- **NICS-Unterschrift:** Ein Scan entlang der Normalen der Ringebene wurde als Weg in einer Höhe über der Ebene
  beschrieben; die Lage kommt jetzt aus den Koordinaten der Bq (in der Ebene, entlang der Normalen oder neutral „along
  the scan path“). Die Seite eines Punkts (ober-/unterhalb, für das Mittel von Paaren) hängt nicht mehr vom beliebigen
  Vorzeichen der lokalen Ebenennormalen ab.
- **Overlay:** Eine nach einem SORCI-Schritt gedruckte Absorptionstabelle wurde als TD-DFT-Spektrum gelesen.
- **Tab „Verbindung“:** Die Chips „Abbildungen von“ blieben nach einem Sprachwechsel leer.
- **Projektseite:** Die Knöpfe „SI-Texte …“, „Allgemeine Vorschriften“ und „Im Ordner zeigen“ neben den Reitern waren
  unsichtbar (Höhe 0); die Linie über den Reitern war an dieser Stelle gebrochen und versetzt und entfällt. Kopf,
  Reiter und alle Seiten beginnen jetzt auf derselben linken und rechten Kante, die senkrechten Abstände folgen einem
  Raster.
  Die Verbindungsliste zeigt jede weitere Methode (UV-Vis, Kinetik, Fluoreszenz, CV, SEC, H-Cell, EPR, X-Ray, DFT) als
  eigene Spalte mit Punkt statt als abgeschnittenen Text; alle Spalten stehen mittig in einem Raster.
- **Fensterbreite:** Die Tab-Leiste mit jetzt 16 Tabs erzwang eine Mindestbreite des Fensters (unter Windows breiter
  als ein Laptop-Bildschirm). Sie darf jetzt schmaler sein als ihr Inhalt: ein Pfeil am Rand und das Mausrad schieben
  sie, der gewählte Tab bleibt sichtbar.
- **Word-Export:** Unter einem längeren Methodentext steht jetzt noch eine Abbildung, solange sie mindestens 7 cm
  hoch bleibt (vorher blieb der Rest der Seite leer). Ein Energieprofil mit nur einer Rechnung (ein Strich bei 0) kommt nicht
  mehr in die SI.
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
- Felder im UV-Vis-Tab und im Vergleich waren 2 bis 4 Pixel niedriger als in den anderen Tabs.
- CV: Ohne interne Referenz stand in der Karte „Referenzierung“ ein einzelner Strich.
- Projekt → Angaben: Die Beschriftung „Datensatzbeschreibung“ war abgeschnitten.
- UV-Vis-Kinetik, HRMS, X-Ray: einzelne Zeilen lagen außerhalb des Rasters (Knopf allein in einer Zeile, schmaleres
  Feldpaar, Beschriftung in anderer Farbe); die Karte „Ausrichten“ hatte unten einen leeren Streifen.

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
