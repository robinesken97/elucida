[English](README.md) | **Deutsch** · [Änderungen](CHANGELOG.de.md)

# Spectravolt – Spektroskopie und Elektrochemie für Photo- und Redoxchemie

*Früher **UVVisTool**. Projekte, Einstellungen und heruntergeladene Daten werden automatisch übernommen.*

Spectravolt wertet UV-Vis-Verdünnungsreihen aus, legt gemessene und TD-DFT-Spektren übereinander und analysiert
Fluoreszenz, Cyclovoltammetrie, Spektroelektrochemie (SEC) und CW-EPR – jeweils mit publikationsfertigen Abbildungen.

Im ε-Tab bestimmt Spectravolt molare Absorptionskoeffizienten (ε) aus UV-Vis-Verdünnungsreihen
(Lambert-Beer: A/d gegen c) und erzeugt publikationsfertige Abbildungen im gewohnten Origin-Stil:
Spektren, λ/ε-Labels an den Banden, ein Inset mit den linearen Regressionen und R², die Struktur
(CDXML/SVG/PDF) und ein freigestelltes Foto der Küvette. Die Oberfläche gibt es auf Deutsch und
Englisch.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/eps_dark_de.png">
    <img src="docs/screenshots/eps_light_de.png" alt="Spectravolt – ε-Auswertung" width="900">
  </picture>
</p>

### Auf einen Blick

| Tab | Was er macht |
|---|---|
| **ε-Auswertung** | Lambert-Beer-Fit von Verdünnungsreihen → ε (bzw. a) mit Konfidenzintervall; Abbildung im Origin-Stil mit Struktur und Küvettenfoto; Excel-Report |
| **Overlay** | Gemessene Spektren, TD-DFT (ORCA/Gaussian, SOC, Tripletts) und SEC-Serien in einer Abbildung, normiert oder als ε |
| **Fluoreszenz** | Absorption und Emission, Stokes-Verschiebung, Fotos bei Tageslicht und unter UV |
| **CV** | Gamry-Dateien, E½/ΔE_p, Nicholson-Verhältnis, Randles-Ševčík, Bezug auf Fc⁺/Fc |
| **SEC** | Spektrenserie mit Potential vom Potentiostaten, Differenzspektren, scheinbarer Nernst-Fit |
| **EPR** | Bruker BES3T, Dunkelspektrum, Basislinie, S = ½-Fit, EasySpin-Import, Kinetik und thermischer Zerfall |

Alle Exporte: PDF/SVG (vektoriell) und PNG, standardmäßig 16 × 11 cm (halbe A4-Seite in Word). Helles und dunkles
Erscheinungsbild; Deutsch und Englisch.

<table>
<tr><td width="50%" valign="top"><img src="docs/screenshots/overlay_light_de.png" alt="Overlay – gemessen, TD-DFT und SEC"><br><sub>Overlay – gemessen, TD-DFT und SEC</sub></td><td width="50%" valign="top"><img src="docs/screenshots/fluorescence_light_de.png" alt="Fluoreszenz"><br><sub>Fluoreszenz</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/cv_light_de.png" alt="Cyclovoltammetrie"><br><sub>Cyclovoltammetrie</sub></td><td width="50%" valign="top"><img src="docs/screenshots/sec_light_de.png" alt="Spektroelektrochemie"><br><sub>Spektroelektrochemie</sub></td></tr>
<tr><td width="50%" valign="top"><img src="docs/screenshots/epr_light_de.png" alt="CW-EPR"><br><sub>CW-EPR</sub></td></tr>
</table>

## Herunterladen und starten

Lade unter **Releases** (rechts auf der Repository-Seite) die Datei für dein System herunter und entpacke sie.

| System | Datei | Starten |
|---|---|---|
| Windows | `Spectravolt-windows-x64.zip` | `Spectravolt\Spectravolt.exe` |
| macOS (Apple Silicon) | `Spectravolt-macos-arm64.zip` | `Spectravolt.app` |
| macOS (Intel, ab macOS 14) | `Spectravolt-macos-x64.zip` | `Spectravolt.app` |
| Linux (AppImage) | `Spectravolt-linux-x64.AppImage` | ausführbar machen, dann doppelklicken |
| Linux (Ordner) | `Spectravolt-linux-x64.tar.gz` | `Spectravolt/Spectravolt` |

Die App ist nicht signiert, deshalb warnt das Betriebssystem beim ersten Start:

- **Windows (SmartScreen):** „Weitere Informationen“ → „Trotzdem ausführen“.
- **macOS (Gatekeeper):** `Spectravolt.app` in „Programme“ ziehen und einmal doppelklicken (wird blockiert).
  Dann Systemeinstellungen → Datenschutz & Sicherheit → ganz unten „Dennoch öffnen“ → mit Passwort/Touch ID
  bestätigen. Ab macOS 15 funktioniert der frühere Weg „Rechtsklick → Öffnen“ nicht mehr. Alternativ im
  Terminal: `xattr -dr com.apple.quarantine /Applications/Spectravolt.app`. Welcher Mac? Apple-Menü → Über diesen Mac: „Chip Apple M…“ = Apple Silicon,
  „Prozessor Intel…“ = Intel. Die Intel-Version braucht macOS 14 (Sonoma) oder neuer.

**Updates:** Beim Start prüft das Programm einmal am Tag, ob es auf GitHub eine neuere Version gibt,
und bietet an, die Release-Seite zu öffnen (Hilfe → „Nach Updates suchen…“; im Hilfe-Menü abschaltbar).
Zum Aktualisieren die neue Datei herunterladen und die alte App ersetzen; Projekte und Einstellungen
bleiben erhalten.

**Linux-AppImage:** `chmod +x Spectravolt-linux-x64.AppImage` (oder Dateieigenschaften → „Als Programm
ausführen“), dann starten. Es braucht `fusermount` (Paket `fuse3`, bei den meisten aktuellen
Distributionen vorinstalliert); ohne startet man mit `./Spectravolt-linux-x64.AppImage --appimage-extract-and-run`.
Wie beim tar.gz ist eine Distribution mindestens so neu wie Ubuntu 22.04 (glibc 2.35) nötig.

Unter Windows immer den ganzen Ordner `Spectravolt` zusammenlassen. Die `.exe` funktioniert nicht ohne den Ordner `_internal` daneben.

## Ablauf

1. **Daten öffnen:** Datei → Messdaten öffnen, oder Dateien ins Fenster ziehen. Unterstützt werden
   Cary-CSV/TXT-Exporte und die gerätenahen **.DSW/.BSW**-Dateien. **Mehrere Dateien auf einmal**
   (z. B. jede Konzentration einzeln gemessen) werden zu einem Datensatz zusammengeführt.
2. **Konzentrationen:** Die Konzentrationen werden aus den Probennamen gelesen, z. B.
   `ABC-1-0p5mgml_THF` → Serie `ABC-1`, 0,5 mg/mL. Erkannt werden
   `mgml`/`mg_ml`/`mg/ml`, `mM`, `uM`/`µM`; `p` steht für das Dezimalkomma.
   - Stehen keine Konzentrationen im Namen (z. B. `c0` … `c4`), öffnet sich eine Tabelle zum Eintragen.
     Die **Einheit** (mM, µM, mg/mL, M) muss ausdrücklich gewählt werden, es ist nichts vorbelegt.
   - „Verdünnungsreihe ausfüllen“ setzt in die markierten Zeilen (oder alle) von oben nach unten Start, Start/Faktor, … ein.
     Der Startwert gehört immer zur **obersten** markierten Zeile (meist die Stammlösung).
   - Proben ohne Wert, z. B. eine Blindprobe, werden ignoriert.
   - Über die Spalte „Serie“ lassen sich mehrere Verbindungen in einer Datei trennen.
   - Später ändern geht über den Knopf **Konzentrationen…**.
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
   automatisch gefundenen“ behält beide), und **„Schultern automatisch suchen“** ergänzt Schultern
   (in der Abbildung optional mit „(sh)“ markiert). In der Ergebnistabelle entscheidet das Häkchen bei λ, ob eine Bande im Bild
   erscheint, und ein Doppelklick auf **„Cutoff A“** setzt einen eigenen Cutoff für diese Bande
   (z. B. um einen Punkt knapp über A = 1 mitzunehmen). Banden mit eigenem Cutoff sind farbig
   hinterlegt; optional zeigt das Inset ausgeschlossene Punkte als offene Symbole.
5. **Layout:**
   - **Mit der Maus ziehen:** Inset, Struktur, Küvette und jedes λ/ε-Label lassen sich verschieben.
   - **Mausrad bzw. Trackpad** über Inset oder Bild ändert die Größe. Alternativ die Felder „Größe [% Plotbreite]“ nutzen.
   - **Maus über den Spektren:** Die Statusleiste zeigt λ und A des nächsten Messpunkts (und seine
     Konzentration), in der Vorschau mit rotem Kreis markiert (nicht im Export) – praktisch zum Prüfen der
     Daten. **Doppelklick** auf einen Punkt fügt seine Wellenlänge als Bande hinzu, erneuter Doppelklick
     entfernt sie. Overlay- und Fluoreszenz-Tab zeigen λ und den gezeichneten Wert genauso an.
   - „Layout zurücksetzen“ stellt die automatische Anordnung wieder her.
6. **Exportieren:** Datei → Exportieren (oder der Knopf). Das schreibt die gewählten Formate (PDF/SVG/PNG),
   `<Serie>_results.csv` und den Excel-Report für **alle** Serien ins Projekt (siehe unten).

## Erscheinungsbild

Das Programm folgt dem hellen oder dunklen Modus des Systems; unter **Format → Erscheinungsbild** lässt sich dauerhaft
hell oder dunkel wählen. Selten gebrauchte Optionen im ε-Tab sind eingeklappt; ein fetter Abschnittstitel mit
**„(geändert)“** bedeutet, dass dort ein Wert vom Standard abweicht (z. B. min. R² fürs Bild). Die Abbildungen sind
vom Erscheinungsbild nicht betroffen.

## Projekte, Export, Rückgängig

Jeder Export aus den Tabs Overlay, Fluoreszenz, CV, SEC und EPR schreibt zusätzlich `…_data.csv` mit genau den
gezeichneten Kurven (ein x/y-Spaltenpaar pro Kurve, Werte ohne Stapelversatz) – für Origin, Excel oder MATLAB.

Alles passiert in einem **Projektordner**:

1. **Datei → Neues Projekt…** – einen Ordner wählen oder im Dialog neu anlegen.
2. Messdaten, Strukturen, Fotos und TD-DFT-Dateien von beliebigen Orten laden – sie werden **ins
   Projekt kopiert** (`data/`, `images/`; ChemDraw-Exporte mit gleichem Namen wie eine CDXML kommen
   mit). Dateien, die schon im Projekt liegen, werden nicht erneut kopiert.
3. Normal arbeiten – das Projekt wird **automatisch gespeichert**. Beim Öffnen eines Projekts wird
   jeweils eine Sicherung `project.uvvis.bak` angelegt.
4. **Exportieren** schreibt direkt ins Projekt (vorhandene Dateien werden überschrieben):

```
MeinProjekt/
  project.uvvis               Einstellungen (Pfade relativ zum Ordner)
  data/  images/              Kopien aller Eingabedateien
  exports/epsilon/<Serie>/    Abbildungen (PDF/SVG/PNG), <Serie>_results.csv, <Serie>_report.xlsx
  exports/overlay/            <Projekt>_overlay.*
  exports/fluorescence/       <Projekt>_fluorescence.*
```

Das Programm startet ohne Projekt. Projekte öffnen über **Datei → Projekt öffnen**, **Zuletzt
geöffnet** oder indem man den Ordner ins Fenster zieht. **Datei → Projekt als Kopie speichern** legt
eine vollständige Kopie an (z. B. als Zwischenstand). **Bearbeiten → Rückgängig / Wiederholen**
(⌘Z / ⌘⇧Z, Strg+Z / Strg+Y) gilt für alle Tabs.

## Excel-Report

Für jede Serie enthält `<Serie>_report.xlsx`:

- **Übersicht:** Parameter (Einheit, Molmasse, Schichtdicke, Cutoffs, Basislinienfenster und Offsets
  je Probe), Ergebnisse aller Banden (Steigung, Achsenabschnitt, Standardfehler, R², ε ± SE,
  **95 %-Konfidenzintervall** über die t-Verteilung) und die Methodik mit allen Formeln.
- **Spektren:** A(λ) aller Proben, basislinienkorrigiert und roh, mit Diagramm.
- **Ein Blatt pro Bande:** Messpunkte, Kennzeichen „im Fit“ (1/0, änderbar), die vollständige Regression
  als **Excel-Formeln** (x̄, ȳ, Sxx, Sxy, m, b, RSS, s, SE, R², ε, t, KI) neben den Werten des Tools
  samt Abweichung, Residuen und Diagramm (A/d gegen c mit Regressionsgerade).

Blaue Zahlen sind Messwerte bzw. Tool-Ergebnisse, schwarze Zellen sind Formeln. Ändert man ein
Kennzeichen in „im Fit“, rechnet Excel die Bande neu.

## Overlay-Tab

Mehrere Spektren in einer Abbildung vergleichen, gemessen und berechnet:

- **Messung…** fügt Spektren aus CSV/TXT/DSW/BSW-Dateien hinzu (ein Eintrag pro Probe);
  **TD-DFT…** fügt Ausgabedateien von ORCA (4–6) oder Gaussian hinzu.
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
- **y-Achse** (Häkchen „Normieren“): *normiert auf Bande* – jedes Spektrum wird auf sein Maximum im Normierungsbereich
  skaliert (global oder pro Spektrum, z. B. wenn die berechnete Bande verschoben ist), oder
  **ε [10³ M⁻¹ cm⁻¹]** – gemessene Spektren brauchen dann Konzentration (bei mg/mL auch Molmasse)
  und Schichtdicke.
- Pro Spektrum: Farbe, Name, **Linienart und -stärke**, **Skalierungsfaktor und vertikaler Versatz**
  (z. B. für gestapelte Spektren); **Reihenfolge** mit ↑/↓ (auch die der Legende).
- ORCA-Rechnungen mit **Spin-Bahn-Kopplung**: pro Rechnung „mit SOC“ oder „ohne SOC“ wählbar.
- **Triplett-Zustände** (ohne SOC, f = 0) lassen sich als gestrichelte Marken fester Höhe anzeigen; sie
  tragen nicht zur Kurve bei (ORCA 4–6, Gaussian).
- Rechnungen **kombinieren**: zwei oder mehr TD-DFT-Einträge markieren (Strg/Shift-Klick) → „Kombinieren“.
  Die Übergänge werden zusammengeführt und dann gemeinsam verbreitert; ein Gewicht pro Rechnung (Standard
  1 = Summe, z. B. 0,7/0,3 für Konformere). Die Rechnungen sollten auf demselben Theorieniveau sein; gleiche
  Zustände in beiden Rechnungen lösen eine Warnung aus (sie würden doppelt zählen).
- **TD-DFT-Normierung:** Kurve und Striche haben immer denselben Skalierungsfaktor (jeder Strich ist
  die Höhe seiner eigenen Gaußbande, die Kurve ist deren Summe). Bezug: „Kurvenmaximum = 1“ oder
  „stärkster Übergang = 1“; alternativ zeigen die Striche die Oszillatorstärke f auf einer rechten Achse.
- Eine **Struktur pro Spektrum**, optional in der Kurvenfarbe.
- Struktur mit einstellbarer Größe; die Legende wird in freie Fläche gesetzt und lässt sich verschieben.
- **Gestapelt** (wie in Papern üblich): Die Kurven werden in Listenreihenfolge um einen gemeinsamen
  Abstand senkrecht versetzt (oben in der Liste = oberste Kurve). „Gleiche Stapelebene wie die Kurve
  darüber“ hält z. B. eine TD-DFT-Kurve auf der Ebene ihrer Messung. Die **y-Achse** lässt sich mit
  Zahlen, ohne Zahlen und Teilstriche (Standard beim Stapeln – bei versetzten Kurven wären die Zahlen
  irreführend) oder gar nicht anzeigen. Optional stehen die **Namen direkt an den Kurven** statt in einer
  Legende, und eine gestrichelte Nulllinie markiert jede Ebene.

## CV-Tab (Cyclovoltammetrie)

- Liest **Gamry-.DTA**-Dateien (Framework 6/7, beide Tabellenvarianten); Scanrate, Elektrodenfläche und
  Zyklen kommen aus der Datei. Mehrere Messungen (z. B. eine Scanraten-Serie) werden überlagert, optional mit
  Farbverlauf blau → rot nach Scanrate, Pfeil für die Scanrichtung und E½ im Bild.
- **Redoxpaare** werden in Potentialfenstern ausgewertet („Vorschlag“ schlägt sie vor, die Fenster sind
  änderbar): E_pa (Strommaximum im Hinlauf), E_pc (Minimum im Rücklauf), E½, ΔE_p, i_pa, i_pc und das
  Peakstromverhältnis nach **Nicholson** (berücksichtigt den abklingenden Strom des Hinlaufs; ≈ 1 = chemisch
  reversibel). Peaks am Fensterrand werden rot markiert. Ab 3 Scanraten wird die **Randles-Ševčík**-Auftragung
  (i_pa gegen √v) gefittet.
- **Referenzierung:** wie gemessen (Referenzelektrode, z. B. Ag/AgNO₃), **intern** (Fc- oder Ac₂Fc-Paar in einer
  der Messungen; E½ der Referenz gegen Fc⁺/Fc ist änderbar – Vorgabe Ac₂Fc +0,49 V, mit eurer Literatur abgleichen)
  oder Verschiebung von Hand. Die Achse heißt dann „E [V vs. Fc⁰/⁺]“.
- **Referenz je Messung** („Referenz der ausgewählten Messung“): eigener interner Standard (auch das Fc/Ac₂Fc-Paar in
  derselben Datei, z. B. „mit Ac₂Fc“) oder eigene Verschiebung – nötig beim Lösungsmittelvergleich, jedes gegen seinen
  eigenen Standard. Die Fenster der Redoxpaare folgen der Referenz der jeweiligen Messung.
- **Gruppe** je Messung (z. B. das Lösungsmittel): Datenreihe in den Auftragungen gegen die Scanrate.
- **Gestapelte** CVs (Listenreihenfolge von oben nach unten, Abstand einstellbar, y-Achse ohne Zahlen) mit **E½ an jeder
  Kurve** neben ihrem anodischen Peak (E¹½, E²½ bei mehreren Paaren).
- **Auftragung:** Cyclovoltammogramm, **Reversibilität** (ΔE_p gegen v), **Randles-Ševčík** (i_pa und i_pc gegen √v mit
  Ausgleichsgerade ab 3 Scanraten) oder **Trumpet-Plot** (E_pa und E_pc gegen log v), eine Datenreihe je Gruppe.
  Hinweis: ΔE_p enthält auch den iR-Abfall (v. a. in THF); der Trumpet-Plot wird ohne k⁰-Auswertung gezeichnet, dafür
  wären mehrere Dekaden Scanrate nötig.
- Strom wie aufgezeichnet (Gamry: IUPAC, anodisch positiv) oder invertiert; optional als Stromdichte.
- Export: Abbildung (PDF/SVG/PNG) und `…_results.csv` mit allen Werten (inkl. Gruppe, Referenzverschiebung und dem
  iR-Kompensations-Eintrag der Gamry-Datei, falls vorhanden).

## SEC-Tab (Spektroelektrochemie)

- Liest eine **Spektrenserie aus B&W-Tek-BWSpec**-Textexporten (Wellenlängen aus den Kalibrierkoeffizienten der
  Datei) und die **Gamry-.DTA**-Datei des Potentialscans. Jedes Spektrum bekommt sein Potential über die Uhrzeit
  (Spektrumzeit − Start der Gamry-Messung, plus einstellbarer Zeitversatz).
- **Spektrenserie:** erstes und letztes Spektrum hervorgehoben (blau/rot), die übrigen grau – oder Farbverlauf nach
  Potential; optional Differenzspektren (ΔA gegen das erste Spektrum) und Nullpunkt (Mittel 780–820 nm); λ-Labels in
  der Farbe des passenden Spektrums. Spektrenbereich wählbar (z. B. nur die erste Welle).
- **A bei λ gegen E** mit scheinbarem Nernst-Fit (E½, n). Bei kontinuierlichem Scan hinkt die Elektrolyse in der
  Dünnschichtzelle nach (E½ verschoben, n < 1); echte Nernst-Werte brauchen Potentialstufen im Gleichgewicht –
  CV-Werte haben Vorrang.
- Potentialachse wie gemessen, um E(Fc⁺/Fc) verschoben oder mit der Referenzierung des CV-Tabs.

## EPR-Tab (CW-EPR)

- Liest **Bruker BES3T** (.dsc + .DTA, z. B. Magnettech ESR5000/ESRStudio, Elexsys; 2D-Dateien ergeben ein Spektrum pro
  Zeile) und **zweispaltigen Text** (Magnettech-MS400-Export; Mikrowellenfrequenz aus Dateinamen wie `…-9p404368-…`).
  Frequenz, Temperatur, Modulation und Leistung werden pro Spektrum angezeigt.
- **Dunkelspektrum:** Die Messung vor dem Bestrahlen lässt sich von jedem Spektrum abziehen (hell − k·dunkel, auf
  dasselbe Feldraster interpoliert); Warnung, wenn Frequenz, Modulation oder Leistung abweichen.
- **Verarbeitung:** Polynom-Basislinie (Grad 0–5) aus den Rändern des Sweeps oder aus gewählten signalfreien Bereichen,
  Feldbereiche ausblenden (z. B. das scharfe Radikalsignal), Glätten per gleitendem Mittelwert.
- **EasySpin-Simulationen** als zweispaltiger Text (B in mT, Intensität), z. B. `writematrix([B(:) spc(:)], 'sim.txt',
  'Delimiter', '\t')`; per kleinsten Quadraten an eine Messung angepasst (oder von Hand skaliert) und im Feld
  verschiebbar; gestrichelt auf derselben Ebene. Eine **Parameterdatei** (die MATLAB-Zeilen `Sys.D = [D E]; …`) wird
  angezeigt, D und |E| in cm⁻¹ umgerechnet, optional im Bild.
- Darstellung in mT oder G, überlagert oder gestapelt, normiert, y-Achse standardmäßig ohne Zahlen, freie Labels wie
  `Z⁻@122, Y⁺@400`. Beim Überfahren: B, g-Wert und Intensität.
- **Mehrere Spezies:** Alle einer Messung zugeordneten Simulationen (EasySpin oder eigene S = ½) werden *gemeinsam* per
  linearen kleinsten Quadraten skaliert; die Anteile (Doppelintegral) werden angezeigt, optional die Summe und der Rest
  (Messung − Summe) – also die Subtraktion einzelner Spezies. Nichtlineare Parameter (g, A, D/E, Linienbreiten von
  Pulverspektren) werden in EasySpin gefittet; das Tool bestimmt nur die Anteile.
- **Eigene isotrope S = ½-Simulation mit Fit** (Lösung, erste Ordnung): g, Gruppen äquivalenter Kerne (z. B.
  `2 14N 0.65; 4 1H 0.32`, a in mT), Peak-zu-Peak-Linienbreite und Lorentz-Anteil; „Fitten“ verfeinert g, a und ΔB_pp
  (Levenberg-Marquardt nach einer Grobsuche, Amplitude linear).
- **Feldkalibrierung mit TEMPO** (oder einer anderen Referenz): Referenz mit einer S = ½-Simulation fitten, als
  Kalibrierung mit ihrem Literatur-g wählen (Vorgabe 2,0055, TEMPO in MeCN); ΔB = B(g_fit) − B(g_lit) wird von allen
  anderen Messungen abgezogen, deren Fits dann kalibrierte g-Werte liefern.
- **Intensität gegen Zeit oder Temperatur** (z. B. Belichtungskinetik, thermischer Zerfall): Doppelintegral oder
  Peak-zu-Peak in einem Feldfenster für jede sichtbare Messung (nach Dunkelspektrum und Basislinie), optional × T
  (Curie), normiert; die Zeit zählt ab dem frühesten Spektrum im Tab (z. B. dem Dunkelspektrum). „Dunkelspektrum für
  alle Messungen übernehmen“ setzt den Hintergrund für eine ganze Serie auf einmal.
- **Thermischer Zerfall bei konstanter Heizrate** (Nachbau des MATLAB-Skripts der Gruppe): Intensität je Spektrum als
  Peak-zu-Peak, Doppelintegral oder **Gauß + Gerade an ein Merkmal** (z. B. das X-Merkmal bei 487 mT), × T, Feld auf eine
  Referenzfrequenz skaliert (z. B. 9,3 GHz) und Temperaturkorrektur (z. B. −1,5 K); dann **E_a und A** aus
  I(T) = exp(−A·∫exp(−E_a/RT)/β dT), β aus dem mittleren Temperatur- und Zeitschritt. Zielfunktion kleinste Quadrate (Standard;
  belastbares 95-%-Intervall mit t-Quantil) oder „wie Skript“ (√|r|, zum Vergleich mit alten Zahlen – empfindlich
  gegenüber dem Optimierer, ihr Intervall unterschätzt die Unsicherheit stark). E_a und ln A sind fast vollständig korreliert.
- **Export für EasySpin:** Neben der Abbildung wird jede Messung als zweispaltige Textdatei (B in mT, Intensität) in
  voller Auflösung nach Dunkelspektrum, Basislinie und Glättung geschrieben – ohne Normierung und ohne ausgeblendete
  Bereiche – mit `%`-Kopfzeilen zu Frequenz, Temperatur und Verarbeitung (`load(...)` in MATLAB, direkt für `esfit`).
  Die Intensitätsreihe wird als `…_intensity.csv` gespeichert.

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

Format → „Schrift und Rahmen…“ gilt für alle Tabs und wird im Projekt gespeichert:

- **Textschrift** und **Symbolschrift**. λ und ε stehen standardmäßig in der Symbolschrift
  (Times New Roman), wie in Origin; abschaltbar.
- **Bandenlabels:** Schriftgröße (standardmäßig automatisch), fett, kursiv, Farbe.
- **Rahmen:** geschlossener Rahmen um den Plot (auch oben und rechts) und abgerundeter Rahmen um die
  Strukturformel.

## Was bei der Auswertung automatisch passiert

- **Basislinie** („automatisch (Reihe)“, Standard): Das Fenster liegt dort, wo die konzentrierteste
  Probe am wenigsten absorbiert. Abgezogen wird nur der Teil des Fensterwerts, der *nicht* mit der
  Konzentration skaliert (Geräte- bzw. Küvettenoffset). Ein zu c proportionaler Rest gilt als echte
  Absorption und bleibt erhalten. „automatisch (einfach)“ zieht den kompletten Fensterwert ab.
  Die Basislinie nutzt immer den vollen Datenbereich, unabhängig vom dargestellten λ-Bereich.
- **Fit-Cutoff:** Punkte oberhalb des Cutoffs (Standard A = 1,0) gehen nicht in den Fit ein.
- **Banden:** automatisch im dargestellten λ-Bereich gesucht oder als Liste vorgegeben.
- **Rundung:** ε (M⁻¹ cm⁻¹) erscheint nie mit Nachkommastellen; gerundet wird auf die Genauigkeit,
  die sein Standardfehler hergibt. Die Ergebnis-CSV enthält die vollen Werte.
- **Warnungen** (Ergebnistabelle und Protokoll): weniger als 4 Fitpunkte, signifikanter
  Achsenabschnitt (> 2σ), R² unter der Schwelle (Standard 0,98, einstellbar unter Auswertung →
  „min. R² fürs Bild“; 0 = alle zeigen; die Bande bleibt in Tabelle – R²-Zelle rot markiert –, CSV und
  Excel-Report, erscheint aber nicht im Bild), weniger als 3 Punkte (dann gar kein ε). Bei 4 Punkten
  sagt R² allein wenig: vor dem Absenken der Schwelle das 95-%-Konfidenzintervall im Excel-Report prüfen.

## Hinweise zu CDXML

- Exaktes ChemDraw-Aussehen: einen SVG/PDF/PNG-Export mit gleichem Namen neben die CDXML legen
  (siehe oben). Sonst wird die Struktur über RDKit neu gezeichnet. Die Orientierung bleibt, Labels
  wie CD₃ oder N₂ können aber anders aussehen (z. B. als einzelne Atome).
- Molmasse = Summe aller Fragmente (Gegenionen zählen mit).
- Lassen sich Abkürzungen wie Dipp oder Mes nicht auflösen, wird **keine** Molmasse gesetzt und eine
  Warnung angezeigt. Dann bitte die Molmasse von Hand eintragen.
- Binäre `.cdx`-Dateien werden nicht gelesen. In ChemDraw als `.cdxml` speichern.

## Unterstützte Daten

- **Cary-CSV/TXT-Exporte** (Agilent Cary 60 u. a.): erste Zeile = Probennamen, zweite Zeile =
  `Wavelength (nm),Abs` je Probe, danach die Daten. Dezimalkomma und -punkt werden beide erkannt,
  die Gerätemetadaten am Dateiende werden ignoriert. Einfache zweispaltige Dateien gehen auch; dann
  dient der Dateiname als Probenname.
- **Cary WinUV .DSW / .BSW** (Binärdateien der Gerätesoftware), gelesen mit dem Parser aus dem
  Open-Source-Projekt [parseuv](https://pypi.org/project/parseuv/). Gerätebasislinien
  („Baseline 100%T/0%T“) in Batch-Dateien werden übersprungen.
- **Cary Eclipse** Fluoreszenzdaten: CSV-Export und .FBSW-Dateien. Die Anregungswellenlänge wird
  aus den Metadaten der Datei übernommen.
- **Mehrere Dateien** lassen sich zusammen öffnen und bilden einen Datensatz.

## Probleme

- **Absturz:** Die Details stehen in `crash.log`:
  - Windows: `%LOCALAPPDATA%\Spectravolt`
  - macOS: `~/Library/Application Support/Spectravolt`
  - Linux: `~/.local/share/Spectravolt`

  (bis Version 1.15 hieß der Ordner `UVVisTool`; er wird beim ersten Start automatisch umbenannt)
- **Selbsttest:** `Spectravolt --selftest <ordner>` prüft Einlesen, CDXML, Freistellung und Export und
  schreibt `selftest_report.txt`.

---

## Für Betreuer: Bauen und veröffentlichen

Die Apps baut GitHub Actions (`.github/workflows/build.yml`) für Windows, macOS und Linux.
Nach jedem Build läuft auf jedem System ein Selbsttest der fertigen App.

**Neue Version über die Weboberfläche:**

1. Geänderte Dateien hochladen: „Add file“ → „Upload files“ → „Commit changes“.
2. **Releases** → „Create a new release“ → bei „Choose a tag“ z. B. `v1.0.0` eintippen → „Create new tag“ → „Publish release“.
3. Nach etwa 20–40 Minuten hängen die drei App-Dateien am Release.

**Testbuild ohne Release:** Actions → „Build Spectravolt“ → „Run workflow“. Das Ergebnis liegt unten
im Lauf unter „Artifacts“ und wird nach 90 Tagen gelöscht.

**Lokal:**

```
pip install -r requirements.txt pyinstaller
python uvvis_gui.py                    # direkt aus dem Quellcode starten
python uvvis_gui.py --selftest out     # Selbsttest
python build.py                        # App bauen -> dist/
```

**Ohne GUI:** `python uvvis_core.py messung.csv` wertet mit Standardeinstellungen aus.

**Dateien:**

| Datei | Inhalt |
|---|---|
| `uvvis_gui.py` | Oberfläche (PySide6), Selbsttest |
| `uvvis_core.py` | Einlesen, Basislinie, Bandensuche, Fits, Plot-Layout, Export |
| `uvvis_images.py` | Bilder, HEIC, Freistellung (ISNet/ONNX, GrabCut), SVG/PDF-Einbettung |
| `uvvis_chem.py` | CDXML: Zeichnung und Molmasse (RDKit) |
| `uvvis_i18n.py` | Texte Deutsch/Englisch |
| `uvvis_tabs.py` | Overlay- und Fluoreszenz-Tab |
| `uvvis_extra.py` | TD-DFT einlesen/verbreitern, Fotopaar, Abbildung für die Zusatz-Tabs |
| `uvvis_project.py` | Projektordner (Speichern/Laden, Kopieren der Eingabedateien) |
| `uvvis_report.py` | Excel-Report (openpyxl) |
| `parseuv_lite/` | Leser für Cary .DSW/.BSW/.FBSW (aus parseuv, BSD-3-Clause) |

**Datenschutz:** Die `.gitignore` schließt CSV-, HEIC- und CDXML-Dateien aus, damit keine
unveröffentlichten Messdaten im Repository landen.

## Lizenz

Spectravolt steht unter der **GNU Affero General Public License v3.0** (siehe `LICENSE`).
Es gibt keine Gewährleistung.

Die App enthält folgende Bibliotheken unter ihren eigenen Lizenzen:
PySide6/Qt (LGPL-3.0), PyMuPDF (AGPL-3.0), RDKit (BSD-3-Clause), matplotlib (Matplotlib License),
NumPy (BSD-3-Clause), Pillow (MIT-CMU), pillow-heif (BSD-3-Clause, enthält libheif, LGPL-3.0),
OpenCV (Apache-2.0), ONNX Runtime (MIT), PyYAML (MIT), olefile (BSD-2-Clause), openpyxl (MIT).
Der Leser für .DSW/.BSW-Dateien in `parseuv_lite/` stammt aus parseuv 1.0.4
(© 2026 Ricardo J. Fernández-Terán, BSD-3-Clause, siehe `parseuv_lite/LICENSE`).
Das ISNet-Modell für die Freistellung (Apache-2.0) wird beim ersten Gebrauch aus dem
rembg-Projekt heruntergeladen und ist nicht Teil dieses Repositorys.
