[English](CHANGELOG.md) | **Deutsch**

# Änderungen

## Unveröffentlicht

### Neu
- Neuer Tab **X-Ray**: CIF-Dateien lesen (mehrere Strukturen/`data_`-Blöcke), drehbare **ORTEP-Abbildung im
  Mercury-Stil** (schattierte Ellipsoide mit einstellbarer Wahrscheinlichkeit und Hauptachsen-Ellipsen, Farben je
  Element frei änderbar, verschiebbare Labels; flacher Olex2-Stil wählbar), Atome und Labels je Atom schaltbar
  (Doppelklick schaltet ein Label um), Molekül über die Symmetrie vervollständigt (C1ⁱ mit Fußnote), Fehlordnung (standardmäßig
  Hauptteil), H-Atome und getrennte Fragmente ausblendbar.
- X-Ray: sperrige Gruppen als **Drahtmodell** (Bindung zum Substituenten wählen, z. B. N–C_ipso; auch Ringsysteme
  hinter einem Spiro-Atom), Schalter **Lösungsmittel** / **Gegenionen ausblenden** (erkannt über die Summenformel; ein
  zweites unabhängiges Molekül bleibt), Labels nur für Heteroatome, Startansicht mit möglichst wenig Überdeckung und
  ein **Vorschlag für die Bildunterschrift**, der sich nach dem Ausgeblendeten und dem Drahtmodell richtet (mit
  ausgewählten Parametern und Symmetriecodes).
- Abstände, Winkel und Diederwinkel **per Klick auf Atome**, Standardabweichungen genau aus der CIF; in der CIF
  fehlende Werte (Diederwinkel ohne CONF) werden ohne Standardabweichung berechnet und markiert.
- SI-Tabellen: **Kristalldaten und Strukturverfeinerung** (eine Spalte je Verbindung) und **ausgewählte Parameter**;
  Kopieren mit Formatierung für Word, CSV und Excel.

### Behoben
- Selbsttest: wartet auf die im Hintergrund geladenen Strukturen statt einer festen Zeit (scheiterte auf langsamen
  Rechnern).

## 1.18.1 – 21.10.2026

### Behoben
- macOS Intel: Build und Selbsttest mit der dort älteren RDKit (Verbindung aus dem MS-Bericht übernimmt Formel
  und Molmasse; die Ersatzzeichnung braucht eine neuere RDKit).

## 1.18.0 – 21.10.2026

### Neu
- **Verbindung des Projekts** (Name, ChemDraw, Formel, Molmasse) als Vorgabe für alle Tabs (Werkzeugleiste
  **Verbindung …**); Tabs mit eigener Struktur behalten diese.
- Neuer Tab **IR + MS**: IR-Peakliste aus Bruker OPUS (Datei oder PDF-Ausdruck, optional w/m/s/br) und die HRMS-Zeile
  aus dem Word-Bericht der Massenabteilung, fertig für die SI (Kopieren mit Formatierung für Word).
- HRMS: Abgleich der Formel mit dem im Bericht eingebetteten ChemDraw-Objekt; die Verbindung des Projekts lässt sich
  daraus übernehmen.
- HRMS aus **Bruker-Rohdaten** (`.d`, z. B. timsTOF) ohne Bruker-Software: Linienspektren direkt gelesen, Ion über den
  LC-Peak gemittelt (automatisch oder gewählter RT-Bereich) mit Anzahl der Scans und Streuung.

## 1.17.0 – 21.10.2026

### Neu
- CV: **Referenz je Messung** (eigener interner Standard – auch das Fc/Ac₂Fc-Paar in derselben Datei – oder eigene
  Verschiebung), z. B. für den Lösungsmittelvergleich, jedes gegen seinen eigenen Standard; die Fenster der Redoxpaare
  folgen der jeweiligen Referenz.
- CV: **Gruppe** je Messung (z. B. Lösungsmittel) und **gestapelte** CVs mit **E½ an jeder Kurve** neben ihrem
  anodischen Peak (E¹½, E²½); y-Achse mit Zahlen, ohne Zahlen oder ausgeblendet.
- CV: Auftragungen gegen die Scanrate – **Reversibilität** (ΔE_p gegen v), **Randles-Ševčík** (i_pa und i_pc gegen √v
  mit Ausgleichsgerade) und **Trumpet-Plot** (E_pa/E_pc gegen log v, ohne k⁰-Auswertung), eine Datenreihe je Gruppe.
- CV: **E_pa/E_pc als Zahl an den Peaks** (z. B. Probe und Ac₂Fc in einer Messung), **Struktur je Messung**; die
  iR-Kompensation der Gamry-Datei (z. B. Positive Feedback 800 Ω) steht in der Ergebnis-CSV.
- Release Notes auf GitHub werden aus den Changelogs erzeugt.

### Geändert
- Ziehen von Inset, Bildern, Labels und Legende ist deutlich flüssiger (nur das gezogene Element wird neu gezeichnet).

### Behoben
- CV: Ein Fenster ohne echtes Redoxpaar (E_pa unter E_pc) wird markiert, statt ein negatives ΔE_p auszugeben.

## 1.16.0 – 21.10.2026

### Geändert
- **Neuer Name: Spectravolt** (früher UVVisTool) – das Programm kann inzwischen deutlich mehr als UV-Vis. Einstellungen
  (zuletzt geöffnete Projekte, Sprache, Erscheinungsbild) und der Datenordner werden beim ersten Start übernommen;
  Projekte öffnen sich wie bisher. Die Release-Pakete heißen jetzt `Spectravolt-…`.

### Neu
- Overlay: **SEC-Spektren** aus dem SEC-Tab, ausgewählt nach Potential – als **Serie** (alle Spektren oder Anfang und
  Ende, mit einem gemeinsamen Faktor auf das Startspektrum normiert, Intensitätsverhältnisse und isosbestische Punkte
  bleiben) oder als einzelne Spektren. SEC wird nie als ε gezeigt (Dünnschichtzelle).

## 1.15.1 – 21.10.2026

1.15.0 wurde getaggt, aber nicht veröffentlicht (ein Selbsttest unter Linux war zu streng); die Änderungen sind hier
enthalten.

### Geändert
- Farben des hellen und dunklen Erscheinungsbilds: dunkler, wärmere Grautöne, dezentere Ränder.

### Behoben
- Selbsttest der Hover-Anzeige: Toleranz richtet sich nach der tatsächlichen Auflösung der Vorschau.

## 1.15.0 – 21.10.2026 (nicht veröffentlicht)

### Geändert
- **Neues Aussehen:** einheitlicher Stil unter Windows, macOS und Linux mit hellem und dunklem Erscheinungsbild;
  standardmäßig wie das System, umschaltbar unter **Format → Erscheinungsbild**. Abbildungen und Exporte bleiben
  unverändert.
- Alle Tabs: ausgerichtete Formulare, die linke Spalte wird nicht mehr abgeschnitten, **Exportieren** bleibt unten
  sichtbar, ein leerer Tab zeigt einen klaren Hinweis statt einer weißen Abbildung.
- ε-Tab: Gruppen als Karten; selten gebrauchte Optionen (Bildgrößen, min. Punkte/R², Schultern, Inset, Formate)
  sind einklappbar und werden mit **„(geändert)“** markiert, wenn sie vom Standard abweichen.
- Werkzeugleiste (Projekt neu/öffnen/speichern, Rückgängig/Wiederholen), Symbole in Menüs und Listenknöpfen.

## 1.14.0 – 20.10.2026

### Neu
- EPR: **thermischer Zerfall bei konstanter Heizrate** – Arrhenius-Fit von E_a und A an die Intensität gegen die
  Temperatur (Nachbau des MATLAB-Skripts der Gruppe); kleinste Quadrate mit belastbarem 95-%-Intervall (Standard) oder
  „wie Skript“.
- EPR: Intensität per **Gauß + Gerade an ein Merkmal**; Feld auf eine Referenzfrequenz skaliert; Temperaturkorrektur.

## 1.13.0 – 20.10.2026

### Neu
- EPR: **mehrere Spezies** – einer Messung zugeordnete Simulationen werden gemeinsam skaliert (lineare kleinste
  Quadrate), Anteile per Doppelintegral, optional Summe und Rest.
- EPR: **eigene isotrope S = ½-Simulation mit Fit** (g, Hyperfeinkopplungen äquivalenter Kerne, Linienbreite,
  Lorentz-Anteil; Grobsuche + Levenberg-Marquardt).
- EPR: **Feldkalibrierung** mit einer gefitteten Referenz wie TEMPO (g_lit = 2,0055); die Feldkorrektur gilt für alle
  übrigen Messungen.
- EPR: **Intensität gegen Zeit oder Temperatur** (Doppelintegral oder Peak-zu-Peak im Feldfenster, optional × T,
  normiert), z. B. für Belichtungskinetik und thermischen Zerfall; „Dunkelspektrum für alle Messungen übernehmen“.
- EPR: Jede Messung wird zusätzlich als **EasySpin-fertige Textdatei** exportiert (verarbeitet, volle Auflösung,
  dokumentierter Kopf); die Intensitätsreihe als CSV.
- Alle Abbildungs-Tabs: Der Export schreibt zusätzlich **`…_data.csv` mit den gezeichneten Kurven**.

## 1.11.0 – 20.10.2026

### Neu
- Neuer **EPR-Tab** (CW-EPR): Bruker BES3T (ESR5000/ESRStudio, Elexsys) und MS400-Textdateien; Abziehen des vor dem
  Bestrahlen gemessenen Dunkelspektrums; Polynom-Basislinie, ausgeblendete Feldbereiche, Glätten; EasySpin-Simulationen
  (zweispaltiger Text) an eine Messung angepasst, mit EasySpin-Parameterdatei (D, |E| in cm⁻¹); überlagert oder
  gestapelt, mT oder G, freie Labels; beim Überfahren B, g und Intensität.
- Neuer **SEC-Tab** für Spektroelektrochemie: BWSpec-Spektrenserie + Gamry-Potential (Zuordnung über die Uhrzeit,
  Versatz einstellbar); Spektrenserie mit hervorgehobenem erstem/letztem Spektrum oder Potential-Farbverlauf,
  Differenzspektren, farbige λ-Labels; A bei λ gegen E mit scheinbarem Nernst-Fit; Referenzierung wie im CV-Tab.

### Korrigiert
- Kurvennamen, die mit „_“ beginnen, fehlten in Legenden.
- Referenzelektroden mit Index (Ag/AgNO₃) werden in Achsenbeschriftungen korrekt gesetzt.

## 1.9.0 – 20.10.2026

### Neu
- Neuer **CV-Tab** für Cyclovoltammetrie: Gamry-.DTA-Dateien, Überlagerung mehrerer Messungen (Scanraten-Serie
  mit Farbverlauf, Pfeil für die Scanrichtung, E½-Label), Redoxpaare in änderbaren Fenstern (E_pa, E_pc, E½,
  ΔE_p, i_pa, i_pc, Peakverhältnis nach Nicholson), Randles-Ševčík-Fit, Referenzierung gegen Fc⁺/Fc (intern
  Fc/Ac₂Fc, von Hand), Ergebnisse als CSV.

### Korrigiert
- Die automatische Label-Platzierung funktioniert jetzt auch bei Kurven mit nicht monotonen x-Werten (z. B. CV).

## 1.8.0 – 20.10.2026

### Neu
- ε-Tab: optional **vorhergesagte Farbe in Lösung** unter dem Küvettenfoto, aus dem Spektrum berechnet
  (Transmission unter Tageslicht, CIE-1931-Farbmetrik → sRGB). Konzentration und Schichtdicke wählbar
  (Lambert-Beer). Nur Anzeige, nicht in der Abbildung.

## 1.7.0 – 14.10.2026

### Neu
- Overlay: **Triplett-Zustände** aus TD-DFT-Rechnungen (formal spinverboten, f = 0) lassen sich als
  gestrichelte Marken fester Höhe anzeigen („Triplett-Zustände markieren“); sie tragen nicht zur
  verbreiterten Kurve bei. Gelesen aus den ORCA-6-Zustandsbezeichnungen, dem Triplett-Block von ORCA 4/5
  und Gaussian („Triplet-A“).
- Overlay: TD-DFT-Rechnungen **kombinieren** – zwei oder mehr markieren (Strg/Shift-Klick) und
  „Kombinieren“ drücken: Die Übergänge werden zuerst zusammengeführt und dann gemeinsam verbreitert.
  Ein Gewicht pro Rechnung (Standard 1 = Summe; z. B. 0,7/0,3 für Konformere). Warnung, wenn die
  Rechnungen gleiche Zustände enthalten.

### Geändert
- Overlay: Die Normierung ist ein Häkchen („Normieren“); aus zeigt wie bisher ε [10³ M⁻¹ cm⁻¹].

## 1.6.0 – 13.10.2026

### Neu
- **Werte anzeigen:** Mit der Maus über den Spektren zeigt die Statusleiste λ und die Absorbanz des
  nächsten Messpunkts (mit Konzentration), in der Vorschau markiert (nie im Export). Im Overlay- und
  Fluoreszenz-Tab erscheint der gezeichnete Wert (Overlay: ohne Stapelversatz).
- **Banden picken:** Doppelklick auf einen Messpunkt im ε-Tab fügt seine Wellenlänge als Bande hinzu;
  erneuter Doppelklick (±2 nm) entfernt sie.

## 1.5.2 – 12.10.2026

### Korrigiert
- Der Selbsttest (`--selftest`) schreibt nicht mehr in die Benutzereinstellungen (zuletzt geöffnete
  Projekte, letzter Ordner, Sprache); er nutzt eine eigene Einstellungsdatei im Ausgabeordner.

## 1.5.1 – 12.10.2026

### Korrigiert
- macOS: Die App zeigt im Finder ihre Version (bisher 0.0.0).

## 1.5.0 – 11.10.2026

### Neu
- Overlay: **gestapelte** Darstellung wie in Papern – Kurven in Listenreihenfolge um einen gemeinsamen
  Abstand versetzt; „Gleiche Stapelebene wie die Kurve darüber“ (z. B. TD-DFT mit ihrer Messung).
- Overlay: **y-Achse** mit Zahlen, ohne Zahlen und Teilstriche (Standard beim Stapeln) oder ausgeblendet.
- Overlay: Namen **direkt an den Kurven** statt Legende; optional gestrichelte Nulllinie je Ebene.
- Fluoreszenz: **Stokes-Verschiebung** Δν̃ = 1/λabs − 1/λem in cm⁻¹ (auf 10 cm⁻¹ gerundet) und nm
  unter den Daten; optional auch am Emissionslabel im Bild.
- Fluoreszenz: Absorbanz bei λex mit Warnung ab A = 0,1 (Innenfiltereffekt – relevant, wenn Absorption
  und Emission von derselben Lösung stammen).

- Linux: zusätzlich als **AppImage** (`UVVisTool-linux-x64.AppImage`, eine einzelne Datei); das tar.gz bleibt.

### Geändert
- Fluoreszenz: Das Absorptionslabel heißt λabs (einheitlich mit λem).

## 1.4.0 – 11.10.2026

### Neu
- Update-Prüfung: Beim Start (höchstens einmal am Tag) fragt das Programm bei GitHub nach, ob es eine
  neuere Version gibt, und bietet an, die Release-Seite zu öffnen – mit der passenden Datei für dein
  System. Hilfe → „Nach Updates suchen…“ prüft sofort; Hilfe → „Beim Start automatisch nach Updates
  suchen“ schaltet die automatische Prüfung ab. Es wird nur die öffentliche GitHub-API abgefragt und
  nichts außer der Programmversion übertragen. Ohne Internetverbindung passiert nichts.
- Release-Builds für Intel-Macs (ab macOS 14): `UVVisTool-macos-x64.zip`.

## 1.3.0 – 10.10.2026

### Neu
- Neues Menü Format → „Schrift und Rahmen…“ (gilt für alle Tabs, wird im Projekt gespeichert):
  - Textschrift und Symbolschrift wählbar (Standard Arial und Times New Roman).
  - Bandenlabels: Schriftgröße (Standard automatisch), fett, kursiv und Farbe.
  - Optional geschlossener Rahmen um den Plot (Linie auch oben und rechts).
  - Optional abgerundeter Rahmen um die Strukturformel; er wandert mit der Struktur, und die
    automatische Platzierung hält Labels und Inset davon frei.

### Geändert
- Griechische Buchstaben (λ, ε) stehen standardmäßig in der Symbolschrift – in den Labels, der
  Inset-Tabelle, der Overlay-Achse und bei λem im Fluoreszenz-Tab. Abschaltbar im Format-Dialog.

## 1.2.4 – 08.10.2026

### Neu
- Das minimale R², ab dem eine Bande im Bild erscheint, ist einstellbar (Auswertung → „min. R² fürs
  Bild“, Standard 0,98; 0 = alle Banden mit Fit zeigen). Banden unter der Schwelle bleiben in
  Ergebnistabelle, CSV und Excel-Report; ihre R²-Zelle ist rot markiert (mit Tooltip). Der Wert wird im
  Projekt gespeichert.

## 1.2.3 – 06.10.2026

### Korrigiert
- Bei mehreren Banden konnten zwei Labels exakt übereinander liegen: Ein neu hinzugekommenes
  Bandenlabel (z. B. weil die Bande nach einer Cutoff-Änderung genug Fitpunkte hatte) wurde platziert,
  bevor die gespeicherten Positionen der anderen Labels berücksichtigt waren. Gespeicherte Positionen
  von Labels, Inset und Bildern werden jetzt zuerst reserviert. Labels, die in einem gespeicherten
  Projekt bereits übereinanderliegen, bleiben dort – eines wegziehen oder „Layout zurücksetzen“.

## 1.2.2 – 06.10.2026

### Geändert
- Die Vorschau füllt in allen Tabs den verfügbaren Platz und wächst mit dem Fenster; sie bleibt
  maßstabsgetreu (nur die Anzeigegröße ändert sich, die exportierte Abbildung bleibt gleich).

### Korrigiert
- Sehr kleine Fehler von ε wurden als „± 0“ angezeigt (z. B. 51 ± 0 bei SE = 0,65); sie werden jetzt
  aufgerundet („51 ± 1“).

## 1.2.1 – 06.10.2026

### Neu
- **Overlay:** Struktur pro Spektrum, optional in der Kurvenfarbe (SVG/CDXML als Vektorgrafik,
  PNG/PDF als Bild).

### Geändert
- **TD-DFT-Normierung:** Kurve und Striche haben jetzt immer denselben Skalierungsfaktor (jeder Strich =
  Höhe seiner eigenen Gaußbande, die Kurve ist deren Summe). Bezug „Kurvenmaximum = 1“ (neuer Standard)
  oder „stärkster Übergang = 1“; alternativ Striche als Oszillatorstärke f auf rechter Achse. In 1.2.0
  wurden die Striche im Modus „stärkster Strich = Bandenmaximum“ unabhängig von der Kurve skaliert.

### Korrigiert
- Strukturen (CDXML, SVG, PDF) wurden zu knapp zugeschnitten: exakt senkrechte oder waagerechte
  Bindungen am Rand (z. B. =CH₂, CH₃) fehlten in Abbildungen und Exporten.
- Strukturen wurden verzerrt, wenn sich ihr Seitenverhältnis oder die Achsengröße änderte (z. B. f-Achse
  zugeschaltet); gespeichert wird jetzt nur die Breite, die Höhe folgt immer aus dem Bild. Bestehende
  Projekte werden automatisch korrigiert.
- Aus CDXML ohne Export gezeichnete Strukturen hatten zu dünne Linien und zu kleine Beschriftungen.
- Eingefärbte Strukturen hatten dunkle Kanten.

## 1.2.0 – 06.10.2026

### Neu
- **Projektordner:** zuerst Ordner wählen oder anlegen; jede geladene Datei wird hineinkopiert, das
  Projekt wird automatisch gespeichert (Sicherung `project.uvvis.bak` beim Öffnen), und Exporte landen
  direkt in `exports/epsilon/<Serie>/`, `exports/overlay/`, `exports/fluorescence/`. Datei → Neu /
  Öffnen / Zuletzt geöffnet / Projekt als Kopie speichern / Projektordner anzeigen. Das Programm
  startet ohne Projekt.
- **Excel-Report** pro Serie: Parameter, alle Ergebnisse inkl. 95 %-Konfidenzintervall, Methodik mit
  Formeln, Spektren und je Bande ein Blatt mit der vollständigen Regression als Excel-Formeln neben
  den Tool-Werten, Residuen und nativen Diagrammen.
- **Rückgängig / Wiederholen** (⌘Z / ⌘⇧Z, Strg+Z / Strg+Y) über alle Tabs.
- **Overlay:** Linienart und -stärke, Skalierungsfaktor und vertikaler Versatz pro Spektrum,
  Reihenfolge (↑/↓), Strukturgröße in %, Legende in freier Fläche.
- **TD-DFT-Striche:** „stärkster Strich = Bandenmaximum“ (Standard), „Höhe der Einzelbande“ oder
  Oszillatorstärke f auf eigener rechter Achse.
- ORCA-Spektren mit **Spin-Bahn-Kopplung**; „mit SOC“ / „ohne SOC“ pro Rechnung wählbar.
- ε-Tab: Regressions-Inset abschaltbar (zusätzlich zu seiner Tabelle).
- Fluoreszenz-Tab: Größenfelder für Struktur und Fotos.
- Kennzeichnung „(sh)“ an Schultern in der Abbildung ist optional (standardmäßig aus); Tabelle und Excel-Report behalten sie.

### Geändert
- Die Ergebnis-CSV hat eine zusätzliche Spalte `ci95` (95 %-Konfidenzintervall von ε).
- Einstellungen werden nicht mehr als `.uvvis.yaml` neben den Messdateien gespeichert, und Overlay-/
  Fluoreszenz-Tab werden beim Start nicht mehr automatisch wiederhergestellt – dafür gibt es Projektordner.

### Korrigiert
- ORCA-Ausgaben mit Spin-Bahn-Kopplung wurden falsch gelesen (Zustandsnamen wie „0-1.0A“ wurden als
  Zahlen interpretiert, mit falschen Energien und Oszillatorstärken). Solche Rechnungen bitte neu laden.

## 1.1.0 – 05.10.2026

**Bitte prüfen:** Konzentrationen, die mit 1.0.0 über den Konzentrationsdialog eingegeben wurden,
können in mM gespeichert sein, ohne dass jemand diese Einheit gewählt hat. Datei öffnen und unter
**Konzentrationen…** kontrollieren.

### Neu
- **Overlay-Tab:** mehrere gemessene Spektren und TD-DFT-Spektren (ORCA 4–6, Gaussian) in einer
  Abbildung, in eigenen Farben; normiert auf eine Bande von Interesse (global oder pro Spektrum)
  oder als ε [10³ M⁻¹ cm⁻¹]. TD-DFT: Gauß-Verbreiterung (FWHM, Energieverschiebung), optional Striche.
- **Fluoreszenz-Tab:** Absorption und Emission normiert in einer Abbildung, mit λ/ε- und
  λem-Labels, optionalem Ausblenden von Streulicht und einem Fotopaar Tageslicht/UV mit Pfeil und
  Anregungswellenlänge. Die Einstellungen beider neuen Tabs bleiben zwischen Sitzungen erhalten und
  lassen sich speichern/laden.
- Einlesen von Cary-WinUV-Dateien **.DSW/.BSW** und Cary-Eclipse-Dateien **.FBSW** (Parser aus
  parseuv, BSD-3-Clause) sowie von Cary-Eclipse-CSV-Exporten; λex wird aus den Metadaten übernommen.
- **Mehrere Messdateien auf einmal** (z. B. jede Konzentration einzeln gemessen) bilden einen
  Datensatz, auch per Drag & Drop.
- Strukturzeichnung **unverändert aus ChemDraw**: Ein gleichnamiger SVG/PDF/PNG-Export neben der
  CDXML wird für die Zeichnung verwendet, die CDXML für die Molmasse.
- **Schultern:** optionale automatische Suche (markiert mit „(sh)“); manuell eingetragene Banden
  lassen sich zusätzlich zu den automatisch gefundenen auswerten.
- **Pro Bande:** eigener Fit-Cutoff (z. B. um einen Punkt knapp über A = 1 mitzunehmen) und Auswahl,
  ob die Bande im Bild erscheint – beides in der Ergebnistabelle. Ausgeschlossene Punkte lassen sich
  im Inset als offene Symbole zeigen.
- **Datei → Neu beginnen** verwirft alle gespeicherten Eingaben zur aktuellen Datei.
- Fehlende Molmasse bei Konzentrationen in mg/mL wird rot markiert; ein Hinweis erklärt, wenn die
  Molmasse nicht verwendet wird (mM/µM).

### Geändert
- ε (M⁻¹ cm⁻¹) wird nie mit Nachkommastellen angezeigt.
- R² steht nur dann in der Inset-Legende, wenn die Inset-Tabelle nicht angezeigt wird (dort steht es bereits).
- Die Summenformel zeigt Isotope (z. B. D für Deuterium); die Molmasse hat sie bereits berücksichtigt.

### Korrigiert
- Konzentrationsdialog: Einheit und Startwert sind nicht mehr vorbelegt (bisher mM und 1,0).
- Spektren ohne Signal im Normierungsbereich werden mit Hinweis ausgelassen, statt aus Rauschen
  hochskaliert zu werden.

## 1.0.0 – 04.10.2026

Erste Version.

- Einlesen von Cary-Mehrproben-CSV-Exporten. Konzentrationen aus den Probennamen oder per Tabelle
  (mit Hilfe für Verdünnungsreihen).
- Automatische Basislinienkorrektur, Bandensuche, Lambert-Beer-Fits mit ε ± Standardfehler, R²
  und Warnungen.
- Abbildungen im Origin-Stil mit Inset (Regressionen, R²), Struktur (CDXML/SVG/PDF; Molmasse aus
  CDXML) und Küvettenfoto (HEIC/JPG/PNG, automatische Freistellung).
- Inset, Bilder und Labels mit der Maus verschiebbar, Größe per Mausrad oder Größenfeld.
  Wählbarer Wellenlängenbereich.
- Export als PDF/SVG (Struktur als Vektorgrafik) und PNG. Feste Größe für Word
  (16 × 11 cm = zwei Abbildungen pro A4-Seite).
- Oberfläche auf Deutsch und Englisch. Apps für Windows, macOS und Linux.
