[English](CHANGELOG.md) | **Deutsch**

# Änderungen

## 1.3.0 – 2026-11-17

### Neu
- **Abbildung kopieren (SVG).** Bearbeiten → Abbildung kopieren (SVG), Strg+Umschalt+C (macOS ⌘⇧C): die Abbildung der
  rechts sichtbaren Seite genau wie im Export als SVG mit PNG-Ersatz (macOS zusätzlich PDF) in die Zwischenablage.
  Seiten ohne Abbildung und zurückgehaltene NMR-Spektren kopieren nichts und sagen warum; NMR nimmt den Bereich aus
  dem Feld, nicht den Zoom.
- **MNova-Dokumente über MNova.** Ist MNova installiert (macOS und Windows; unter Windows noch nicht an einer echten Installation geprüft), exportiert MNova ein
  abgelegtes `.mnova` selbst im Hintergrund aus einer Kopie (die eigene Datei bleibt unverändert): jede Seite mit
  Spektrum wird ein Spektrum (`data/nmr/mnova/<Dokument>/<Dokument>_<Seite>.svg`), die NMR-Zeile kommt aus
  MNovas Berichten – ¹H nur aus dem Multiplettbericht, andere Kerne aus den Multipletts oder den Peaklabels der Seite
  (umschaltbar je Spektrum: **SI-Zeile**); 2D nie in die Zeile. Text im Feld wird nie still ersetzt (**Übernehmen** /
  **Behalten**). Die FIDs des Dokuments hängen als Rohdaten am passenden Spektrum. Der Fortschritt steht in der Karte
  MNova. Ohne MNova, nach der Zeitgrenze oder bei einem Fehler wird das Dokument wie bisher gelesen, die Einblendung
  nennt den Grund. Zusammen mit SVGs abgelegt hängt ein Dokument nur seine FIDs an.
- **Bruker-Daten ablegen wie in MNova.** Auch eine einzelne Datei eines TopSpin-Experiments (fid, ser, acqus, 1r …)
  oder sein pdata-Ordner lässt sich ins Fenster ziehen; übernommen wird das ganze Experiment darüber.
- **Schrift, Linien und Farben.** Die Karte „Schrift und Rahmen“ heißt in Tabs mit Kurven „Schrift und Linien“ (mit festen Farben „Schrift, Linien und Farben“).
  Neu sind **Kurvenbreite** (Faktor auf alle Kurven, 1 × = wie bisher) und **Achsenlinien** (Breite von Achsen, Rahmen
  und Strichen in pt, „auto“ = wie bisher); sie gelten wie die Schrift für alle Tabs oder mit „Nur dieser Tab“ nur hier,
  auch im UV-Vis-(ε)-Tab und für die Abklingkurve der Fluoreszenz. Feste Farben ohne Messungsliste sind je Abbildung
  wählbar: SEC (Start, Ende), H-Cell (Laden, Entladen, CE), HRMS (gemessen, berechnet), EPR (Fitkurven). Gilt für
  Vorschau, Export und Word gleich, ist ein Rückgängig-Schritt; „Auf Standard zurücksetzen“ setzt es zurück. Mit den
  Standardwerten bleiben alle Abbildungen unverändert. X-Ray, DFT und Weitere (Moleküle, fremde Bilder) haben die
  Felder nicht.
  Ein Farbknopf ohne Wirkung im gezeigten Bild bleibt sichtbar, aber ausgegraut; der Tooltip nennt den Grund.
- **Projektseite: Reiter „Export“.** Gesamt-SI (Vorlage, Kapitel, Optionen, Verbindungen) und Datensätze (Verbindungen,
  Datenarten, Laborkürzel, Optionen, Zielordner) stehen als Karten im neuen Reiter statt in Dialogen; jede Änderung gilt
  sofort und wird wie bisher gemerkt. **Gesamt-SI (Word)** oben bleibt der Hauptknopf und schreibt direkt mit dieser
  Auswahl, **Datenpakete (Zip)** ebenso; „Auswahl ändern …“ in der Meldung zeigt den Reiter.
- **SI-Auswahl je Verbindung.** Im Tab „Export“ wählt die Spalte **SI** je Abbildung, was in die SI kommt; die Auswahl
  wird mit der Verbindung gespeichert (Rückgängig geht) und gilt für den SI-Abschnitt **und** die Gesamt-SI (vorher
  enthielt die Gesamt-SI immer alle Abbildungen); beide Meldungen nennen Abgewähltes. Eine Verbindung ohne eigene
  Auswahl übernimmt die bisherige Auswahl dieses Rechners. Die Karten „SI-Export (Word)“ und „Folien (PPTX)“ im Tab
  „Verbindung“ entfallen: Teile und Schrift stehen in der Karte „SI (Word)“ im Tab „Export“, die Folien-Auswahl in der
  Spalte **Folien**. Dazu graue Knöpfe **SI (Word)** und **Datenpaket** (ohne Dialog, mit der gespeicherten Auswahl;
  „Auswahl ändern …“ in der Meldung öffnet die Dateiauswahl).
- **Tab „Export“.** Neuer letzter Tab (Gruppe „Ausgabe“): Formate (PDF, SVG, PNG, PPTX) für alle Abbildungen der
  Verbindung, darunter eine Zeile je Abbildung bzw. Bericht (ε je Serie, Fluoreszenz/Abklingkurve, EPR Spektren/Hyperfein/
  Spindichte, TD-DFT/NTO, X-Ray Struktur/Packung/PXRD/Tabellen, DFT Geometrie und Orbitale je Rechnung/NICS/Bericht,
  Weitere je Bild; sonst je Tab) mit **Exportieren** (schreibt genau die Dateien der Zeile) und dem Häkchen **Folien** (dieselbe Auswahl wie die
  Karte „Folien (PPTX)“), dazu **Folien (PPTX)** und **Alles exportieren** (eine Meldung für alle; Tabs, die nicht
  exportiert werden konnten, nennt sie; Fortschritt „Exportiere 3/15 …“ unten rechts, kein Rückgängig-Schritt, die
  Ansicht bleibt). Die Tabs haben keinen eigenen Knopf „Exportieren“ und keine Formate mehr
  (Karte „Achsen und Größe“); **Strg+E** exportiert weiter die Abbildung des offenen Tabs. „SI (Word)“ steht nicht mehr
  in der Werkzeugleiste, sondern unter Datei. Ältere Verbindungen übernehmen die gespeicherten Formate des ersten Tabs
  mit Daten als Vorgabe. Vergleich, Reaktionspfad und Projektseite behalten ihre Exportknöpfe und Formate.
- **EPR: Spindichte und Hyperfeinkopplungen aus ORCA.** Neben Gaussian 16 lesen die Reiter „Spindichte“ und
  „Hyperfein“ ORCA-Ausgaben der Versionen 4.0–4.2, 5.0 und 6.0 (Layouts an echten öffentlichen Ausgaben geprüft) und
  6.1 (6.0-Layout mit strenger Prüfung, noch nicht an einer echten Ausgabe geprüft: die Reiter zeigen einen Hinweis);
  andere Versionen werden mit Meldung abgelehnt. Gelesen werden Mulliken-Spinpopulationen (Löwdin wird im Datensatz mitgeführt),
  A(FC) je Kern aus dem Hyperfeinblock (`%eprnmr Nuclei = all H {aiso, adip} end`) und A(SD) als Dipol-Hauptwerte für
  Kerne ohne `aorb`. Ohne `%eprnmr` werden nur die Spindichten gelesen, der Reiter „Hyperfein“ nennt die fehlende
  Eingabe. Bei mehreren Jobs in einer Ausgabe kommt das Rechenniveau aus dem Job mit dem Hyperfeinblock. Der
  Methodentext nennt Programm und Version.
- **UV-Vis-Titration.** Der Tab UV-Vis-Kinetik nimmt Äquivalente je Spektrum (neue Tabellenspalte, vorgeschlagen, wenn
  Proben- oder Dateiname sie eindeutig nennen, z. B. „0.5eq“) und zeigt zwei neue Ansichten: die Spektren gegen die
  Äquivalente eines zugegebenen Reagenz (Farbverlauf in der Reihenfolge der Äquivalente, Legende mit den Äquivalenten)
  und die Absorbanz bei einer gewählten Wellenlänge gegen die Äquivalente. Isosbestische Punkte werden nur markiert, wo
  alle Spektren innerhalb einer einstellbaren Toleranz übereinstimmen und sich die Änderung dort umkehrt; sonst keiner.
  Bildunterschrift mit Reagenz und isosbestischen Punkten, Methodentext, beide Abbildungen in der SI, Export
  `_titration.csv`. Keine Bindungskonstanten, keine Verdünnungskorrektur. Das Beispielprojekt (S3) enthält eine
  erfundene Titration mit einem Oxidationsmittel.
- **Fluoreszenz: Lebensdauer, Kennwerte und Anregungsspektrum.** Der Fluoreszenz-Tab liest eine Abklingkurve (und
  optional eine IRF) als Textdatei (Zeit, Zählrate; Kopfzeilen, Dezimalkomma und die Zeiteinheit aus dem Spaltenkopf
  werden erkannt; Herstellerformate noch nicht) und fittet ein oder zwei Exponentiale mit konstantem Untergrund: mit
  IRF durch Faltung über die ganze Kurve, ohne ab einem wählbaren Start nach dem Maximum. Zählraten werden
  Poisson-gewichtet gefittet und das reduzierte χ² angegeben; Lebensdauern mit 95-%-Intervall aus der Kovarianz des
  Fits. Ein neuer Reiter „Abklingkurve“ zeigt die Kurve logarithmisch mit Fit, IRF und Residuen, dazu die Parameter,
  amplituden- und intensitätsgewichtete mittlere Lebensdauer getrennt. Ein Reiter „Kennwerte“ nennt λabs, ε, λem, Φ, τ,
  k_r = Φ/τ und k_nr = (1 − Φ)/τ aus den vorhandenen Angaben (Φ trägt man ein, fehlende Zellen bleiben leer; bei zwei
  Exponentialen nennt ein Hinweis die verwendete mittlere Lebensdauer). Ein Anregungsspektrum lässt sich zu Absorption
  und Emission zeigen. Zweite SI-Abbildung mit Unterschrift, Methodentext und Export (`_decay` als Bild und CSV); das
  Beispielprojekt (S3) enthält eine erfundene biexponentielle Abklingkurve mit IRF und ein Anregungsspektrum.
- **SI-Anforderungen der Zeitschriften.** Tab Verbindung: Karte **Reinheit** (¹H/¹³C-NMR, qNMR, Elementaranalyse,
  HPLC, GC, Freitext) – der Charakterisierungsabsatz endet mit „Purity was established by …“; ein Vorschlag aus den
  Daten wird nur angeboten, nie gesetzt. Datenpakete: wahlweise Zip **FID for Publication** nach den ACS-Richtlinien
  (ein Ordner je Verbindung, je NMR-Experiment, MolFile, Messparameter). Projektseite **Angaben**: Bezeichner der
  Gesamt-SI („Supplementary Figure 1“ für Nature-Zeitschriften, auch in Verweisen im Text) und ein **Data Availability
  Statement** für das Manuskript (Repository, DOI, CCDC-Nummern der Verbindungen, FID-Paket). DFT-Tab: Reiter
  **Ladungen** mit Mulliken-/Löwdin-Ladungen und Spinpopulationen (ORCA, Gaussian Mulliken), SI-Tabelle auf Wunsch, CSV.
- **TD-DFT: natürliche Übergangsorbitale (NTO).** Karte „Übergangsorbitale (NTO)“ und Seite „NTO“ neben
  „Anregungen“: je Anregung die Paare Loch → Teilchen der Rechnung als Bilder mit Gewicht. ORCA
  (`%tddft DoNTO true end`): die .nto-Datei des Zustands mit orca_2mkl in Molden umgewandelt; Paare und Gewichte aus dem
  NTO-Block der TD-DFT-Ausgabe (über die Energie dem Zustand zugeordnet, nie geraten), Paare ab einstellbarem Gewicht
  (Vorgabe 10 %, höchstens vier). Oder zwei Cube-Dateien eines Paars (orca_plot, Gaussian cubegen): Gewicht aus dem
  NTO-Block, wenn die Orbitalnummern dort ein Paar sind, sonst von Hand oder ohne. Gezeichnet wie die Orbitale im
  DFT-Tab, gleiche Ansicht und gleicher Maßstab für Loch und Teilchen, Isowert einstellbar (Vorgabe: 80 % der Dichte);
  langgestreckte Moleküle zeigen das Loch über dem Teilchen. Bildunterschrift mit Zustand, Energie, λ, f, Gewichten,
  Isowert und Rechenniveau; SI-Abbildung und Export. Gerechnet wird nichts. Das Beispielprojekt zeigt S1 von S3
  (erfundene Cubes).
- **X-Ray und DFT: Aromatizität (HOMA).** Karte „Aromatizität (HOMA)“ und Seite „HOMA“: HOMA je ebenem 5- bis 7-Ring
  aus den Bindungslängen, mit den Parametern von Krygowski 1993 (CC, CN, CO, CP, CS, NN, NO) oder wahlweise HOMAc
  (Arpa et al. 2025; CC, CN, NN, CO); EN und GEO für Ringe mit nur einem Bindungstyp. Ringe mit einem Bindungstyp ohne
  Parameter bekommen keinen Wert, sondern die fehlende Bindung genannt. Wert auf Wunsch in der Ringmitte (ziehbar),
  SI-Tabelle mit Formel und Zitaten, CSV im Export. Im DFT-Tab stehen NICS(0)/NICS(1)/NICS(1)zz desselben Rings von der
  Seite NICS in derselben Zeile. Bei Kristallstrukturen keine Standardabweichung. Das Beispielprojekt zeigt beide Ringe
  von S3.
- **EPR: Spindichte und berechnete Hyperfeinkopplungen.** Der EPR-Tab liest eine Gaussian-16-Ausgabe einer
  offenschaligen Rechnung (Karte „Rechnung (DFT)“ im Schritt Daten): Mulliken-Spinpopulationen je Atom, isotrope
  Fermi-Kontakt-Kopplungen (MHz, G) und anisotrope Dipolkopplungen. Zwei neue Reiter neben der Abbildung:
  „Spindichte“ zeigt die Spindichte oder das SOMO auf dem Molekül (aus einer Molden- oder Cube-Datei derselben
  Geometrie, gezeichnet wie die Orbitale des DFT-Tabs) mit den Spinpopulationen in Prozent an den Atomen. Prozent =
  Population / Summe aller Atome × 100, mit Vorzeichen, alle Atome zusammen ergeben also 100 %; im Bild stehen Werte ab
  einer einstellbaren Schwelle, die Tabelle zeigt jedes Atom. „Hyperfein“ zeigt die berechneten Kopplungen an den
  Kernen neben den experimentellen einer eigenen S = ½-Simulation („x MHz (exp. y MHz)“): Gruppe der Simulation
  wählen, dann ihre Kerne im Bild anklicken. Kerne einer Gruppe werden mit Vorzeichen gemittelt und mit „avg.“
  gekennzeichnet; die Werte stehen rings um das Molekül mit einem Pfeil zum Kern (ein Pfeil je Methylgruppe), als
  Beträge wie die experimentellen, solange „Vorzeichen“ aus ist; nichts wird automatisch zugeordnet, eine andere Kernzahl als in der Simulation wird gemeldet.
  Einheit MHz, G oder mT; Fläche, Isowert, Deckkraft, Farben, Schwelle und die gezeigten Kerne sind einstellbar.
  Beide Abbildungen kommen in die SI (Unterschrift mit Isowert und Rechenniveau) und in den Export (Abbildung und
  eine CSV mit allen Atomen), der Methodentext nennt die Herkunft der Werte. Andere Programme werden vorerst
  abgelehnt, ebenso Orbitaldateien, deren Atome oder Koordinaten nicht zur Rechnung passen. Das Beispielprojekt (S3)
  enthält eine erfundene Rechnung mit Zuordnung.
- **NMR: Prüfung der Kernzahl.** Unter der Signaltabelle vergleicht der NMR-Tab die NMR-Zeilen mit der Summenformel
  der Verbindung: bei ¹H die Summe der H-Zahlen, bei anderen Kernen die Zahl der Signale gegen die Atome des Elements.
  Weniger H (austauschbare Protonen) oder weniger Signale (Symmetrie, Überlagerung) werden als möglich benannt; mehr,
  als die Formel erlaubt, oder ein Kern, den die Formel nicht enthält, wird in der Warnfarbe markiert, in einer kleinen
  Tabelle und als Kacheln in der Reiterzeile. Nur ein Hinweis, nichts wird geändert.
- **DFT: 3D-NICS.** Der Reiter NICS setzt Gaussian-NMR-Ausgaben, deren Geisteratome ein regelmäßiges Gitter bilden
  (auch über viele Teilrechnungen verteilt), zu einem Gitter zusammen und zeigt das Molekül als Kugel-Stab-Modell mit
  zwei Isoflächen, entschirmt (Standard +5 ppm, rot) und abgeschirmt (Standard −15 ppm, blau); Isowerte, Farben und
  Deckkraft sind einstellbar, das Bild lässt sich drehen. Unvollständige Gitter und Teile mit verschiedenen Geometrien
  werden abgelehnt. Die Abbildung kommt mit beiden Isowerten, Gitterabstand und Rechenniveau in der Unterschrift in
  die SI; der Export legt das Gitter zusätzlich als Cube-Datei ab. Das Beispielprojekt enthält ein erfundenes Gitter.
- **DFT: ACID.** Neuer Reiter „ACID“ im DFT-Tab, aufgebaut wie 3D-NICS. Er zeigt, was das AICD-Programm (Herges)
  geschrieben hat: `Isoober.inc` und `Molekuel.inc` aus dem Ordner `<Name>.d` eines Laufs mit `--povrayinput -c`
  (z. B. `AICD --povrayinput -c -m 2 -s -b 0 0 1 rechnung.log`). Die Isofläche kommt aus dem Dreiecksnetz der Datei,
  die Stromdichtepfeile stehen darauf (grüner Schaft, rote Spitze wie bei AICD); Pfeilgröße, Pfeildichte (ausgedünnt,
  nichts neu berechnet) und Farben sind einstellbar. Ein Symbol zeigt die Richtung des Magnetfelds; sein Tooltip
  erklärt, wie man die Umlaufrichtung eines Ringstroms abliest. Der Isowert kommt aus der Datei. Alternativ liefert
  ein Cube mit dem ACID-Skalarfeld die Isofläche (Standard-Isowert 0.045, gelb; ohne Pfeile). Die Gaussian-Ausgabe der
  CSGT-Rechnung (NMR=CSGT mit IOp(10/93)) liefert Methode und Basis für die Unterschrift; IOp(10/93=2) erscheint dort
  als „selected orbitals“. Andere Aufbauten der AICD-Dateien, Cubes mit negativen Werten und Ausgaben ohne
  CSGT/IOp(10/93) werden abgelehnt. Der AICD-Leser ist an einer öffentlichen Ausgabe von AICD 3.0.4 geprüft. Abbildung in
  Export und SI mit Isowert, Rechenniveau und den ACID-Zitaten. Das Beispielprojekt enthält eine erfundene AICD-Ausgabe.
- **DFT: Pflichtangaben der Zeitschriften (ACS, Org. Lett., Angew. Chem.).** Neuer Reiter „Energietabelle“ im
  DFT-Tab: je Rechnung eine Zeile mit der Zahl imaginärer Frequenzen, E_el, der Kernabstoßungsenergie, H, G, der
  thermischen Korrektur zu H und der Entropiekorrektur −TS in Hartree, alles genau wie in der Ausgabe gedruckt (was die
  Ausgabe nicht druckt, bleibt ein Strich, nichts wird berechnet; ORCA druckt keine H-Korrektur, Gaussian kein −TS in
  Hartree), dazu die Programmversion (ORCA „Program Version“, Gaussian-Revision wie „16 Rev. C.01“). Die Tabelle steht in
  der Word-SI (über die ganze Breite nach den zweispaltigen Strukturen) und im Export (`…_energies.csv`). Alle Strukturen
  des Tabs kommen zusätzlich in EINE maschinenlesbare xyz-Datei (`…_structures.xyz`: Atomzahl, Name und E_el in der
  Kommentarzeile, dann „El x y z“ in Å), im Export und im Datenpaket (`DFT/structures.xyz`). Eingabedateien mit
  gleichem Namen neben einer Ausgabe (`.inp`, `.gjf`, `.com`) werden beim Laden mit in die Verbindung kopiert und kommen
  ins Datenpaket; fehlt eine, sagt das der Reiter. Der Export des TD-DFT-Tabs schreibt zusätzlich
  `…_transitions.csv` mit den TD-DFT-Übergängen (Zustand, Energie, Wellenlänge, Oszillatorstärke, Multiplizität) wie
  gelesen.

- **CV: Angaben, die die Journals zum Voltammogramm verlangen.** Neue Karte „Messbedingungen“ (Schritt Daten):
  Arbeits- und Gegenelektrode, Spülgas, Gerät und Politur, einmal eingegeben und für neue Verbindungen gemerkt. Aus der
  Gamry-Datei liest der Tab Startpotential und Richtung des Scans und ob die iR-Kompensation an war. Die
  Bildunterschrift bleibt kurz: iR-Kompensation und Konvention der Auftragung (IUPAC oder polarographisch) stehen dort
  nur, wenn der Kapitelabsatz des Projekts sie nicht nennt oder die Messung abweicht, Startpotential und Richtung nur
  mit dem Chip „Start und Richtung“. Der Messaufbau (Gerät, Arbeitselektrode mit Fläche und Politur, Gegen- und
  Referenzelektrode, Atmosphäre, iR-Kompensation, Konvention) steht gesammelt
  in einem Anfangstext statt in jeder Unterschrift: in einem Projekt wird er einmal auf der Projektseite erfasst
  (Angaben, Karte „Cyclovoltammetrie: Messaufbau“) und eröffnet das Kapitel „Cyclic Voltammetry“ der Gesamt-SI als
  Fließtext in ganzen Sätzen (leere Felder lassen ihren Satzteil weg, ein freies Feld nimmt weitere Sätze auf), der
  CV-Tab verweist nur darauf; ohne Projekt eröffnet er den Methodentext der Verbindung. Leere Felder fügen nichts
  hinzu. Die Karte nennt, was ACS und Angewandte noch erwarten (Lösungsmittel, Leitsalz, Konzentrationen, Elektroden,
  Gas, Gerät, Fläche, Politur).

- **Elementaranalyse und HRMS geprüft wie von den Journals verlangt.** IR + EA: ein zweiter Wertesatz
  (Doppelbestimmung, wie Angewandte verlangt) ist möglich; dann nennt die SI-Zeile beide Sätze und das Mittel, geprüft
  wird das Mittel gegen 0.4 %. Eine kleine Tabelle je Element (geprüfter Wert, Δ, Status) und die Kachel „EA“ zeigen
  Abweichungen in der Warnfarbe. Neues Feld „Ohne EA, weil“: ohne gefundene Werte steht sein Text als „Elemental
  analysis: …“ in der SI. HRMS: Tabelle mit Ion, calc., found, Abweichung und Status gegen 5 ppm, dazu eine Kachel mit
  der Abweichung. Ohne zweiten Satz bleibt alles wie bisher. Das Beispielprojekt zeigt beide Fälle (S3 innerhalb der
  Grenzen, S2 mit einem Mittel 0.43 % zu tief und einem HRMS-Wert 7.4 ppm daneben).

- **EPR: Messparameter und Einheit der Kopplungen in der Bildunterschrift.** Im Reiter SI-Text setzt ein Chip
  Mikrowellenfrequenz, Modulationsamplitude, Leistung, Zahl der Scans (neu aus BES3T gelesen: `NbScansDone`, sonst
  `AVGS`) und Temperatur aus den Dateien in die Unterschrift, nur Werte, die alle gezeigten Messungen enthalten und
  teilen. „Kopplungen in“ stellt die Hyperfeinkopplungen der Unterschrift auf MHz, mT oder G (G auch im Methodentext).
  Das EPR-Spektrum des Beispielprojekts ist jetzt eine BES3T-Datei mit erfundenen Parametern.
- **CV: Pulsverfahren aus Gamry-Dateien (DPV, Square-Wave).** Eine Gamry-Datei, deren Kurventabelle die Spalten
  „Vstep“ und „Idif“ nennt, wird als eine Kurve gelesen, Differenzstrom gegen das Treppenpotential; die Unterschrift
  nennt „Differential pulse voltammograms“ bzw. „Square-wave voltammograms“ und Schrittweite, Pulshöhe, Pulszeit oder
  Frequenz aus der Datei, die Achse zeigt ΔI. Geprüft mit einer echten Gamry-Square-Wave-Datei; eine echte DPV-Datei
  lag nicht vor, sie wird also gelesen, wenn ihre Tabelle dieselben Spalten nennt, und sonst abgelehnt (Spalten werden
  nie nach Position genommen). Peakpaare und Vorschub-Auswertungen gelten für diese Kurven nicht.
- **NMR: Verbindungsnummer und Messangaben im Spektrum, Bereichsprüfung.** Unter der Struktur stehen in jedem Spektrum
  die Nummer der Verbindung (fett) sowie Kern, Frequenz und Lösungsmittel, in der Vorschau, im SVG und im Word-Export
  (zwei Chips schalten sie ab); die freie Stelle für die Struktur berücksichtigt die Zeilen. Die Tabelle der Spektren
  zeigt den beschrifteten Bereich der Achse und markiert Spektren, deren Beschriftung nicht bis 0 und 10 ppm (¹H) bzw.
  0 und 200 ppm (¹³C) reicht, die Bereiche, die ACS und Angewandte verlangen. Nur ein Hinweis.
- **TD-DFT: Tabelle der Anregungen.** Neue Seite „Anregungen“ neben der Abbildung: Zustand, E (eV), λ (nm, ganzzahlig),
  Oszillatorstärke f und die Hauptanteile (Orbital → Orbital mit Gewicht in %, je eine Zeile, Namen relativ zu
  HOMO/LUMO aus den Besetzungen der Ausgabe). Karte „TD-DFT-Tabelle“ (Schritt Auswertung): Schwelle für f (Vorgabe
  0.01, „aus“ = alle Zustände), Schwelle der Anteile (Vorgabe 10 %), wahlweise nur der λ-Bereich des Bildes und ob die
  Tabelle in die SI kommt. Gewichte: ORCA wie in der Zusammensetzung der Zustände gedruckt; Gaussian 2c² aus den
  gedruckten Koeffizienten (geschlossene Schale) bzw. c² je Spin (offene Schale); Abregungen („<-“) zählen nie. Ohne
  Zusammensetzung in der Ausgabe (alte Tabelle, SOC, Spin-Flip, Multireferenz) entfallen die Spalten. Word: „Table Sn:
  TD-DFT excitations of X.“ nach den Abbildungen (Gesamt-SI: Kapitel Rechnungen), darunter Auswahl und Rechenregel
  der Gewichte. `…_transitions.csv` enthält zusätzlich alle gedruckten Anteile ohne Schwelle und die Rechenregel. Die
  TD-DFT-Ausgabe des Beispielprojekts enthält jetzt eine Zusammensetzung und einen dunklen Zustand.
- **IR + EA: berechnetes gegen gemessenes IR.** Karte „IR-Rechnung“ (Schritt IR): eine Frequenzrechnung von ORCA oder
  Gaussian (Leser des DFT-Tabs, jetzt auch mit den IR-Intensitäten: ORCA 5/6 „IR SPECTRUM“ in km/mol, Gaussian
  „IR Inten“; andere Layouts werden abgelehnt) liegt als Linienspektrum oder Lorentz-verbreitert (Halbwertsbreite
  einstellbar, Vorgabe 15 cm⁻¹) über dem gemessenen Spektrum, die stärkste Bande so tief wie die gemessene. In
  Transmission wird das berechnete Spektrum umgerechnet (T = 100·10^−A), nie die Messung. Skalierungsfaktor Vorgabe
  1.000 – er hängt vom Rechenniveau ab und wird vom Nutzer eingetragen, nichts aus Tabellen. Neue Seite „IR-Rechnung“:
  zugeordnete Banden (gemessen, berechnet skaliert, Δṽ = gemessen − berechnet, Intensität, Art) – nur von Hand
  zugeordnete (Felder „Bande“/„Mode“) oder innerhalb einer einstellbaren Toleranz eindeutige (genau eine berechnete Mode
  ab 5 % der stärksten, und sie liegt bei keiner anderen Bande); Kachel mit der Zahl der zugeordneten Banden. Word:
  Unterschrift mit Rechenniveau, Skalierung und Verbreiterung sowie „Table Sn: Measured and calculated IR bands of X.“
  Das Beispielprojekt enthält eine erfundene Frequenzrechnung mit einer mehrdeutigen, von Hand zugeordneten Bande.
- **IR + EA: Raman.** Neue Karte „Raman“ (Schritt IR): ein Raman-Spektrum als Textdatei (Spalten Raman-Verschiebung
  und Intensität; Kopfzeilen werden übersprungen, Tab, Semikolon, Komma oder Dezimalkomma; Binärformate von Geräten
  werden abgelehnt – als Text exportieren), eigene Peaksuche (Maxima, einstellbare Schwelle), Tabelle zum Abwählen und
  die SI-Zeile „Raman (λexc = 785 nm): ṽ = 2217, 1608, … cm-1“ (Anregungswellenlänge als Feld), die im
  Charakterisierungsabsatz hinter der IR-Zeile steht. Feld „Abbildung“: IR, Raman (Achse „Raman shift [cm⁻¹]“,
  Intensität ohne Zahlen, „arb. u.“) oder IR und Raman übereinander auf gemeinsamer Wellenzahlachse; Unterschrift
  passend. Enthält die Frequenzrechnung der Karte „IR-Rechnung“ Raman-Aktivitäten (ORCA „RAMAN SPECTRUM“, Gaussian
  „Raman Activ“), zeigt das Raman-Bild die berechneten Aktivitäten mit derselben Skalierung und Verbreiterung wie beim
  IR; ohne Aktivitäten gibt es kein berechnetes Raman-Spektrum (Hinweis). Das Beispielprojekt enthält ein erfundenes
  Raman-Spektrum und Aktivitäten.
- **X-Ray: Packungsbild mit Abständen zwischen Molekülen.** Karte „Packung“ (erste Karte im Schritt Darstellung):
  Abbildung „Molekül“ oder „Packung (Elementarzelle)“ – die Elementarzelle mit Kanten und den Achsen *a*, *b*, *c*, über die
  Symmetrie aus dem vervollständigten Molekül gefüllt (ganze Moleküle mit Schwerpunkt in der Zelle oder alle, die sie
  berühren), Blick entlang *a*, *b* oder *c* (oder mit der Maus frei gedreht), H-Atome an/aus, Ellipsoide wie im
  Molekülbild; Polymere behalten den bestehenden Abbruch. Karte „Abstände in der Packung“ (Schritt Auswertung):
  Vorschläge je Molekülpaar – der kürzeste Atom···Atom-Kontakt unter der Summe der van-der-Waals-Radien (Bondi, J. Phys.
  Chem. 1964) plus Toleranz (wahlweise nur Nicht-H-Atome), Ringschwerpunktabstände Cg···Cg mit Versatz und
  Ebenenabstände ebener Ringe nur, wenn die Ebenen innerhalb eines einstellbaren Winkels parallel sind (sonst der
  Winkel); ankreuzen, was ins Bild kommt, oder zwei Atome verschiedener Moleküle im Bild wählen. Abstände als
  gestrichelte Linien mit Wert in Å (drei Nachkommastellen, aus den Koordinaten, ohne Standardabweichung); Seite
  „Abstände“ mit Symmetriecodes; die Unterschrift nennt Blickrichtung, gezeigte Moleküle und Abstände (mehr als acht:
  Tabelle in der SI). Das Packungsbild kommt nach dem Molekülbild in SI und Export („In die SI“). Beispielprojekt: S3 mit
  gestapeltem Paar (Blick entlang *b*).
- **EPR: Spinzählung gegen eine Kalibrierung.** Neue Ansicht „Spinzählung (gegen Konzentration)“: Messungen mit
  bekannter Konzentration sind die Referenzen, ihr Doppelintegral gegen die Konzentration ergibt die Kalibrierung
  (Gerade mit Achsenabschnitt ab drei Konzentrationen, durch den Ursprung mit einer oder zwei); die übrigen Messungen
  sind Proben, deren Spinkonzentration abgelesen wird. Tabelle im Reiter Ergebnisse, Unterschrift und Methodentext
  nennen das Ergebnis; keine Unsicherheiten, keine Umrechnung auf andere Bedingungen (ein Hinweis erscheint, wenn
  Modulation, Leistung oder Temperatur abweichen). Das Beispielprojekt enthält drei erfundene Referenzspektren.
- **X-Ray: Pulverdiffraktogramm (PXRD) aus der CIF.** Karte „Pulverdiffraktogramm (PXRD)“ (Schritt Auswertung) und
  Seite „PXRD“: das aus der Einkristallstruktur berechnete Pulverdiffraktogramm (Lagen aus der Zelle; |F|²·Lp jedes
  Reflexes aus allen Atomen der Elementarzelle mit Besetzung und isotroper/anisotroper Auslenkung; Cromer–Mann-
  Formfaktoren aus den International Tables Vol. C, ohne anomale Dispersion; Pseudo-Voigt-Profil mit einstellbarer
  Halbwertsbreite und η; Cu, Mo, Co, Fe, Cr oder Ag Kα, Kα2 an/aus) gegen ein gemessenes (`.xy`, `.xye` oder
  Textspalten). Kein Rietveld-Fit: nur Skalierung auf das stärkste Maximum und ein eingegebener Nullpunkt; die Karte
  nennt die Temperatur der Strukturbestimmung und sagt, dass Zellausdehnung und bevorzugte Orientierung nicht
  korrigiert werden. Abbildung gestapelt (gemessen oben) oder überlagert, Reflexmarken; Unterschrift, SI (Abbildung,
  Unterschrift, Methodensatz mit der Quelle der Formfaktoren) und Export mit einer CSV der Reflexe. Beispielprojekt:
  S3 mit einer erfundenen Messung bei Raumtemperatur.
- Raman-Spektren und die Datei der IR-Rechnung werden jetzt wie die übrigen Datendateien mit der Verbindung
  mitgeführt (relative Pfade), die Raman-Datei kommt ins Datenpaket.
- **DFT: NBO-Analyse (neuer Reiter „NBO“).** Der DFT-Tab liest ORCA-6-Ausgaben mit einer NBO-7.0-Analyse (Karte
  „NBO-Rechnungen“ im Schritt Daten) und zeigt, was die Ausgabe enthält, ohne etwas zu rechnen: natürliche Ladungen und
  Populationen (NPA), die NBO-Liste mit Besetzung, Energie und Hybriden wie gedruckt (sp^λ, Polarisation je Zentrum),
  die Störungsenergien zweiter Ordnung E(2) ab einer einstellbaren Schwelle (Standard 5 kcal mol-1, Donor und Akzeptor
  lesbar wie „LP(1) N5 → BD*(1) C4–C6“) und die Natural Resonance Theory (Gewichte der Resonanzstrukturen,
  natürliche Bindungsordnungen gesamt/kovalent/ionisch, Valenzen). Die Abbildung zeigt das Molekül mit den natürlichen
  Ladungen an den Atomen und den NRT-Bindungsordnungen an den Bindungen (Schwelle, Nachkommastellen, Elemente, H an/aus,
  Farben; Labels ziehbar). Liegt die CML-Datei von NRTCML neben der Ausgabe und passt sie dazu (gleiche Atome und
  Koordinaten, erste Struktur mit dem Gewicht von RS 1), werden die führenden Resonanzstrukturen mit Gewicht und
  Formalladungen gezeichnet, sonst nur die Tabelle. Mit BNDIDX in der NBOKEYLIST werden auch die Wiberg-Indizes in der
  NAO-Basis gelesen (Layout des NBO-7.0-Handbuchs, geprüft an öffentlichen echten Ausgaben von ORCA 6.1.1/5.0.4 mit
  NBO 7.0 und von GenNBO 7.0.10, streng gelesen, sonst Ablehnung mit Meldung): die Bindungen lassen sich statt mit der
  NRT-Bindungsordnung mit „Wiberg-Index (NBO, NAO-Basis)“ beschriften, ein Unterreiter „Wiberg“ zeigt die Bindungen ab
  der Schwelle und die Summen je Atom, die CSV enthält die volle Matrix. Die Benennung hält beide von der
  IAO-Wiberg-Bindungsordnung des Orbitalbilds (Molden) getrennt; diese bleibt unverändert. Offenschalige Dubletts
  (Radikale, Radikalkationen) werden ebenfalls gelesen: natürliche Ladungen und natürliche Spindichten (NPA), Wiberg
  gesamt/α/β, NBO-Liste und E(2) je Spin; ein Feld „Spin“ (gesamt/α/β) erscheint nur bei offenschaligen Ausgaben, und
  die Abbildung kann die Atome mit der natürlichen Spindichte beschriften (mit Vorzeichen; nicht die
  Mulliken-Spinpopulation des EPR-Tabs). Geprüft: NPA mit Spindichte und die Wiberg-Gesamtmatrix an einer öffentlichen
  ORCA-6.1.1-+-NBO-7.0-Dublett-Ausgabe; NBO-Liste und E(2) je Spin nur am Layout von NBO 6 (der Reiter sagt das).
  Offenschalige NRT, Multiplizitäten über 2 und Gaussian-Ausgaben werden weiter abgelehnt. SI: Abbildungen mit Unterschrift, Tabellen und ein
  Methodensatz mit Programm, NBO-Version und den in der Ausgabe gedruckten Zitaten; der Export schreibt alle Tabellen
  als CSV. Andere NBO-Versionen, Gaussian-/GENNBO-Ausgaben und offenschalige Analysen werden mit Meldung abgelehnt. Das
  Beispielprojekt (S3) enthält eine erfundene NBO/NRT-Rechnung.
- **NMR: ¹³C-Signale bei Lösungsmittel- oder Verunreinigungssignalen.** Unter der Kernzahl listet eine zweite Tabelle
  ¹³C-Signale, die zu einem Restsignal des Lösungsmittels oder einer häufigen Verunreinigung im selben Lösungsmittel
  passen, nach Fulmer et al. (Organometallics 2010, 29, 2176; Tabellen 1 und 2 wie gedruckt enthalten), z. B.
  „29.7 · 29.71 · Schlifffett (Apiezon H)“ in CDCl₃. Toleranz 0.02 ppm plus die halbe letzte angegebene Stelle; ein
  Stoff mit mehreren C zählt erst, wenn alle seine C mit H passen. Beschriftet das Mnova-SVG das Lösungsmittelsignal
  (z. B. „77.00 CDCl3“), rechnet der Abgleich mit dem Abstand zur Tabelle (hier +0.16 ppm) und sagt das unter der
  Tabelle; Spektrum, NMR-Zeile und SI bleiben unverändert. Ohne beschriftetes Lösungsmittelsignal kein Versatz; mehr als
  0.5 ppm daneben heißt kein Abgleich. Chip **Verunreinigungen** (Vorgabe an). Nur ein
  Hinweis: an NMR-Zeile und SI ändert sich nichts. Unbekannte Lösungsmittelnamen ergeben keinen Hinweis. Die
  Beispielverbindung S2 zeigt den Fall. **¹H** nur an freien Peaks: Peaks des Spektrums außerhalb aller Multipletts der
  ¹H-Zeile (Multiplett = Mitte ± halbe Breite erster Ordnung aus Multiplizität und J, bei „m“ der angegebene Bereich,
  dazu 0.01 ppm), die Signale der Zeile werden also nie markiert (an einer veröffentlichten SI traf fast jede ¹H-Zeile
  einen Tabellenwert). Die Peaks kommen nur aus MNovas Peakbericht eines exportierten Dokuments (eigene
  Spektren: kein ¹H-Abgleich, automatische Peaks trafen richtige und falsche Lösungsmittelspalte gleich oft); ohne
  Peakliste sagt ein Satz, dass ¹H nicht abgeglichen wird. Ein Stoff mit mehreren Signalen zählt erst, wenn jedes einen
  eigenen freien Peak trifft (Warnfarbe); Stoffe mit einem Signal (Wasser, Aceton …), das Restsignal und das
  undeuterierte Lösungsmittel selbst (Toluol in Toluol-d8) stehen grau als „möglich“. Kein Referenzversatz für ¹H.
- **EPR: EasySpin-Startskript aus den berechneten Kopplungen.** Schritt **Auswertung**, Karte **Hyperfein-Zuordnung**:
  „EasySpin-Skript speichern …“ schreibt ein MATLAB-Skript für `garlic` (isotropes Lösungsspektrum): `Sys.Nucs`,
  `Sys.n` und `Sys.A` in MHz (wie gerechnet, ohne Umrechnung) der zugeordneten Gruppen (Mittel mit Vorzeichen über die
  zugeordneten Kerne; ohne Zuordnung die einzeln im Bild stehenden Kerne), `Sys.g` aus dem gültigen Fit der
  S = ½-Simulation, `Exp.mwFreq`/`Exp.Range` aus ihrer Messung. Was fehlt, bleibt ein auskommentierter Platzhalter
  (garlic verlangt g, es wird kein Wert geraten); die Linienbreite ist immer ein Platzhalter. Nur isotrope Kopplungen,
  anisotrope Tensoren werden nicht ausgegeben. Der Export schreibt das Skript mit, unter einem Namen, den MATLAB
  ausführen kann (Buchstaben, Ziffern, Unterstriche, vorn ein Buchstabe, z. B. `S3_1_EPR_easyspin.m` für die
  Verbindung S3.1); lässt sich das Skript nicht erzeugen, fehlt nur das Skript und die Exportmeldung nennt es. Noch
  nicht in MATLAB/EasySpin ausgeführt.
- **Abbildungen als PowerPoint-Folien (PPTX).** „PPTX“ ist ein weiteres Format in der Karte „Achsen, Größe und Formate“
  jedes Tabs mit dieser Karte und in den Formaten von UV-Vis (ε): „Exportieren“ schreibt dann zusätzlich
  `<Verbindung>_<Tab>.pptx` mit einer Folie je Abbildung (UV-Vis (ε): je Serie). Die neue Karte „Folien (PPTX)“ im Tab
  Verbindung exportiert mehrere Abbildungen auf einmal (`<Verbindung>_slides.pptx` in `figures/`), mit eigenen
  Abbildungs-Chips (auf diesem Rechner gemerkt, unabhängig von der SI). Jede Folie enthält das Bild wie in Word (PNG mit
  SVG), eingepasst im gleichen Seitenverhältnis, darunter die Bildunterschrift als bearbeitbares Textfeld (fett, kursiv,
  tief- und hochgestellt bleiben; ohne „Figure Sn:“). Die Datei entsteht ohne Zusatzpaket; X-Ray und DFT haben ein
  eigenes Formate-Feld und dort noch kein PPTX (ihre Abbildungen kommen über die Karte auf die Folien).

- **NMR: eigene Spektren aus Bruker-Rohdaten (optional, Mnova-SVG bleibt Standard).** „Rohdaten …“ in der Karte
  „Spektren“ (oder „Als Spektrum“ im Reiter „Rohdaten“, oder „Quelle“ eines Spektrums mit verknüpftem Experiment) zeigt
  ein TopSpin-1D-Experiment in einer eigenen Spektrenansicht mit den Mnova-Tasten: Fourier-Transformation aus dem FID
  (Leser und Transformation an 201 echten Datensätzen gegen TopSpin geprüft), Phase aus procs, automatische Basislinie,
  Achse ohne TopSpins Kalibrierung. Phase und Referenz bleiben „nicht bestätigt“, bis sie bestätigt sind: die Referenz
  wird über das Restsignal des Lösungsmittels vorgeschlagen (Fulmer 2010) oder per Klick auf eine Spitze (R) mit Sollwert
  gesetzt; die Phase lässt sich vorschlagen (ACME) oder ziehen (Shift+P). Varianten ohne geprüfte Verarbeitung erscheinen
  als TopSpins 1r mit Meldung, nie geraten. Verarbeitung, Referenz und Darstellung werden mit der Verbindung gespeichert.
  Das Beispielprojekt (S3) hat erfundene ¹H-Rohdaten neben seinem Mnova-Spektrum.
  **Auswertung:** Integrale (I) mit Normierung durch den Nutzer, Multipletts als Vorschlag (erster Ordnung nach Hoye,
  sonst „m“) oder per J gewählt; ein Muster des Nutzers (Klasse + J) wird im Bereich gesucht und seine Linien stehen über
  dem Spektrum, damit ein falscher Vorschlag sichtbar ist. Jedes Signal wird einzeln bestätigt (kein „alle bestätigen“);
  eine Kopplung, deren Linien nicht getrennt sind, wird nur über „J übernehmen“ gedruckt, oder „Ohne dieses J“ passt das
  Muster ohne sie neu an (dd → d). Unbestätigte Signale erscheinen als Bereich + m.
  **SI:** Je Kern bleiben Mnova-Zeile und -Abbildung, bis für ein eigenes Spektrum „Eigene Verarbeitung für die SI“ gewählt ist (höchstens eines je
  Kern) und Phase und Referenz bestätigt sind (jeder Kern, auch ¹⁹F); eine einzige Definition des Gedruckten speist
  SI-Zeile, Signaltabelle, Kernzahl, Kacheln, Word und Vergleichstabelle; unberührte Vorschläge werden nie gedruckt (der Tab
  zählt sie), ein übernommenes J heißt „J übernommen“; die eigene Abbildung beschriftet nur Bestätigtes.
  Dann kommt die NMR-Zeile dieses Kerns aus der Auswertung (nur bestätigte δ und J; ein nicht schreibbares Signal wird
  genannt, die Zeile bleibt), die Abbildung ist wie die Mnova-Vorlage gezeichnet (16 × 11 cm, Struktur mit Nummer und
  Messangaben, Ausschnitte meiden Struktur und Spektrum, Marken in der Unterschrift erklärt) und geht wie die
  Mnova-Spektren nach Word (Reiter „SI-Abbildung“ zeigt sie).
  **2D:** Ein 2D-Experiment aus Rohdaten wird aus ser verarbeitet, wo seine Klasse geprüft ist (sonst TopSpins 2rr mit
  Grund), und als Höhenlinien mit Vorzeichenfarben, Projektionen, Rechteck-Zoom und Schwelle per Mausrad gezeigt; F2/F1
  werden über ein bestätigtes eigenes 1D desselben Kerns und Magneten referenziert, sonst als unkalibriert markiert.
  Unaufgeteilte NOAH-Sätze zeigen „Phase ausstehend“. Die Abbildung geht wie ein Mnova-2D-Spektrum in die SI.
  **X-Kerne** (¹⁹F, ³¹P, ¹¹B, ²⁹Si, ¹⁵N): Die Achse bleibt standardmäßig nominell (nicht probenkalibriert); „Unified
  Scale (¹H)“ referenziert sie über das eigene ¹H-Spektrum derselben Probe am selben Magneten mit bestätigter Referenz
  (Ξ nach Harris 2001, nur zweifach unabhängig abgeschriebene Werte; ¹⁵N gegen MeNO2 oder NH3 nach Wahl), als
  Vorschlag zum Bestätigen.
- **NMR: Ausschnitte, Labels und Exportmeldung wie der Mnova-Ablauf.** X in einem Ausschnitt aufgezogen schneidet diesen
  Bereich aus dem Ausschnitt (Teile mit „//“-Bruch, je Schnitt ein Rückgängig-Schritt); die Labels eines Ausschnitts
  stehen gruppiert über ihrem Teil; passen Labels nicht in die Breite, gibt es nur einen Hinweis. Peak-Labels beginnen bei
  der Größe der Vorlage (4 pt) und sind nur größer stellbar; Multiplett-Labels sind in der Ansicht lesbar (mindestens
  12 px, ihre Verbindungslinien laufen unter allen Labels), die SI-Abbildung behält die Vorlage. Achsenzahlen überlappen
  nie: wo Zahlen nicht zwischen ihre Striche passen, wird die Teilung gröber, und an einem Bruch fällt die Zahl daneben
  auf der schmaleren Seite weg. Den Bereich der eigenen SI-Abbildung legt nur das neue Feld „Bereich“ fest
  („auto“ −1…11 / −10…220 ppm), nicht mehr der letzte Zoom. Die Ansicht behält Reiter, Bildlauf und Zoom über Sprache,
  Design und Rückgängig. Die Exportmeldung (Strg+E) nennt zurückgehaltene eigene Abbildungen in einer Zeile mit
  „Details“ statt in einem Meldungsfenster; die Kernzahl sagt „n Vorschläge offen“, wenn H fehlen, weil Vorschläge offen
  sind. Ein abgelegter 1D-Ordner ohne passendes
  Mnova-Spektrum wird ein eigenes Spektrum. Eigene 2D-Spektren bekommen den Reiter „SI-Abbildung“; das Feld „Kern(e)“
  zeigt ¹H/¹³C.
- **NMR-Kern (Leser, Verarbeitung, Auswertung, 2D, Ansicht).** Bruker-Leser (fid/ser/1r/2rr, little und big endian,
  int32/float64, XDIM-Untermatrizen) mit einer Liste geprüfter Varianten, alles andere mit Meldung abgelehnt;
  1D-Verarbeitung gegen TopSpin geprüft; Basislinie, ACME-Phasenvorschlag, Referenzvorschlag über das Restsignal
  (Fulmer 2010), Integrale, Multipletts erster Ordnung und Musterfit mit Status (Vorschlag, bestätigt, nicht gemessen) bis
  zur SI-Zeile; 2D-Verarbeitung aus ser für die geprüften Klassen; eine Spektrenansicht mit den Mnova-Tasten. Eine
  Kopplung, deren Linien der Fit zusammenlegt (< 0,5 Hz), gilt als nicht gemessen.
- **NMR: MNova-Dokumente als eigene Spektren.** „MNova-Dokument …“ in der Karte MNova (oder Ablegen) legt die
  `.mnova`-Datei wie bisher unverändert in die Verbindung und macht aus jedem lesbaren 1D-Spektrum mit FID ein eigenes
  Spektrum (Quelle „Rohdaten aus MNova-Dokument“), verarbeitet wie ein Bruker-Experiment. MNovas Referenzierung ist nur
  ein Vorschlag zum Bestätigen. 2D-Spektren und ungeprüfte MNova-Versionen werden nicht gelesen; eine Einblendung und
  eine Zeile in der Karte nennen sie (kein Dialog). Die nachgebauten Experimente kommen nicht in Datenpakete; Rohdatum
  bleibt das Dokument. Die Karte „Spektren (SVG/EMF aus MNova)“ heißt jetzt „Spektren“.
- **NMR: Basislinie wählbar, Tasten ohne Klick.** Die Karte „Verarbeitung“ bietet das Polynom 5. Grades (Standard,
  unverändert), ein Bernstein-Polynom 3. Grades (MNovas Vorgabe „Advised“; die signalfreien Punkte wählt Elucida, nicht
  MNova) oder keine Basislinienkorrektur. Die Spektrumansicht bekommt den Fokus beim Öffnen des NMR-Tabs und wenn die
  Maus darüber steht, die MNova-Tasten wirken also ohne Klick; ein Feld, in dem getippt wird, behält den Fokus.
- **NMR: weniger ¹³C-Peakvorschläge bei bestätigter Phase.** „Peaks vorschlagen“ bietet dann nur das höchste Maximum in
  ±1 Hz an; die Karte nennt, wie viele weitere Maxima weggelassen wurden (im Modus K wählbar). Ohne bestätigte Phase
  ändert sich nichts.
### Geändert
- **λ-Labels knapp über ihrer Bande.** In den Abbildungen UV-Vis (ε), SEC und Fluoreszenz steht ein λ-Label ohne
  gezogene Position jetzt knapp über seinem eigenen Maximum (Abstand 0,4 Labelhöhen, auch zum nächsten Label), wenn
  dort Platz ist; Inset, Tabelle, Struktur und Foto bleiben genau, wo sie waren. Labels ohne Platz bleiben wie bisher
  in der Reihe oben. Stünden die Labels dann nicht mehr nach λ von links nach rechts, lägen sie auf der Legende oder
  fänden Legende oder Pfeil keinen freien Platz, bleibt die ganze Abbildung wie bisher. Gezogene Labels bleiben.
- **CV: Der Pfeil der Messrichtung steht über dem Voltammogramm.** Ohne gezogene Position beginnt er nicht mehr am
  ersten Messpunkt (auf der Kurve), sondern an freier Stelle knapp über den Kurven nahe dem Messbeginn, ohne Labels,
  Legende und Strukturen zu überdecken; im CV-Stapel des Vergleichs steht jeder Pfeil über seiner Kurve. Ohne freie
  Stelle bleibt er am ersten Messpunkt. Gezogene Positionen bleiben.
- **„Alles auf Standard“ heißt jetzt „Darstellung zurücksetzen“ und setzt nur das Aussehen der Abbildung zurück**
  (X-Ray/DFT: „Standardwerte“ → „Darstellung“). Alles, was eine gedruckte Zahl, eine Tabelle, eine Kachel, den
  Methodentext, die SI oder die eingehenden Daten ändert, bleibt: Bereiche und Fenster der Auswertung, Basislinie,
  Fitmodell, Schwellen, Auswahl, Fehlordnung, ausgeblendete Atome und Fragmente, Spalten der Rechnung, und welche Größe
  oder SI-Abbildung gedruckt wird (R², ± σ, Peaklabels, m/z, Spindichte/SOMO, IR/Raman, CV-Auftragung). Vorher schaltete
  der Knopf z. B. den Fluoreszenz-Fit von bi- auf monoexponentiell, den Kinetik-Fit aus und änderte die EPR-Basislinie.
  Wo der Achsenbereich auch die Auswertung begrenzt (Peaksuche UV-Vis, UV-Vis-Kinetik ohne gewählte λ, Raman-Peaks,
  TD-DFT-Tabelle „nur im Bereich“), bleibt auch der Achsenbereich. Ein Satz der Bildunterschrift, der nur das Bild
  beschreibt (Ellipsoid-Wahrscheinlichkeit, ausgeblendete H-Atome, Isowert, Farben), folgt dem Bild. Vorlagen speichern
  und laden nur dieselben Darstellungseinstellungen (auch die Darstellung von NBO, NICS und ACID, ohne deren Dateien).
- **Der Tab „UV-Vis-Overlay“ heißt jetzt „TD-DFT“** und vergleicht die gemessenen Spektren einer Verbindung mit ihrer
  Rechnung (TD-DFT, ESD); mehrere Messungen derselben Verbindung (Lösungsmittel, Konzentration, vor/nach einer
  Reaktion) bleiben möglich. Der Vergleich verschiedener Verbindungen liegt im Projekt (Projektseite → Vergleich:
  normiert auf eine Bande, Strukturen in Kurvenfarbe, Gesamt-SI): die Struktur je Spektrum ist aus dem Tab entfernt,
  eine Zeile „Vergleich“ im Schritt Daten führt ins Projekt. Ältere Abbildungen mit einer Struktur je Spektrum bleiben
  genau wie bisher (Bild, SI und gespeichertes Projekt), mit einem Hinweis im Tab. Stapeln (mit y-Achse, Namen an den
  Kurven, Nulllinie je Ebene und „Ebene wie darüber“) bleibt für Spektren derselben Verbindung.
- Orbitale, Spindichten und NICS-Flächen wirken beim Drehen ruhiger: die Vorschau während des Ziehens wird mit einem
  Drittel statt einem Viertel der Auflösung gerechnet und weich statt in Klötzchen hochskaliert; nach dem Loslassen
  wird wie bisher in voller Auflösung nachgezeichnet.
- Reiter rechts: Seiten ohne Daten (NICS, ACID, NBO, HOMA, Ladungen, Anregungen, NTO, IR-Rechnung, Spindichte,
  Hyperfein, Abklingkurve, Abstände) erscheinen nicht mehr als Reiter; die Abbildung steht vorn, die SI-Seiten hinten
  (DFT: die SI-Seite heißt jetzt „SI-Text“); was nicht passt, steht unter „Mehr ▾“ statt hinter einem Rollpfeil.
  ACID-Pfeile standardmäßig 2.5 ×, das NMR-Spektrum steht in einer Karte wie die übrigen Abbildungen, EPR-Spinanteile
  ganzzahlig wie im Bild, der IRF-Versatz in ps, und das Beispielprojekt zeigt das Raman-Spektrum.
- Schneller: beim Wechsel zu einer anderen Verbindung werden die zuvor geöffneten Tabs nicht mehr alle neu gebaut
  (Beispielprojekt 3–4 s → unter 1 s), verborgene Abbildungen und Ergebnisseiten (NTO, ACID) entstehen erst beim
  Anzeigen statt bei jedem Zeichnen (TD-DFT-Tab 1.8 s → 0.3 s), Abbildungen werden beim Aufbau nicht mehr mehrfach
  gezeichnet (EPR Hyperfein 3.2 s → 1.4 s), Zoomen von Orbitalen und Flächen nutzt die grobe Vorschau wie das Drehen,
  und Projektdateien werden mit dem C-Leser für YAML gelesen (Startbildschirm, Projektseite).
- Beispielprojekt: die Vorstufe S2 zeigt eine kleine EPR-Spinzählung; Packungsbild (X-Ray) und Spindichte (EPR)
  füllen in der Vorgabe-Ansicht die Abbildung (das Packungsbild dafür in der Bildebene gedreht, wo das besser füllt).
- Tab-Leiste: in der Gruppe „UV-Vis & Photophysik“ heißen die Tabs „TD-DFT“ und „Kinetik“ (voller Name im Tooltip),
  damit die Leiste bei 1200 px passt.
- **TD-DFT-Tab, Bildunterschrift:** „Experimental and calculated (TD-DFT) UV-Vis spectra of …“ statt „Comparison of
  UV-Vis spectra of …“; nur gemessene Spektren „UV-Vis spectra of …“, nur Rechnungen „Calculated (TD-DFT) …“. Die
  Unterschrift folgt den sichtbaren Einträgen und wird nicht gespeichert, gilt also auch für bestehende Projekte.
- **Einheiten im Tabellenkopf statt in den Zellen:** EPR-Kopplungen („experimentell [MHz]“, „berechnet [MHz]“),
  Spinzählung („c (bekannt) [mM]“), DFT-Energietabelle (E_el, H, G, E_nuc, H_corr, −TS in [Eₕ]; der eigene Satz
  entfällt), Achsenabschnitt der ε-Tabelle ([cm⁻¹]).
- CV: Ergebnistabelle, Kachel und Projekt-Vergleich zeigen E½, Epa und Epc mit zwei Nachkommastellen wie Bild,
  Methodentext und Word (vorher drei). SEC: die Kachel zeigt die Potentiale der Spektren mit zwei Stellen wie Legende
  und Unterschrift.
- Kinetik (UV-Vis, EPR-Zerfälle): k und sein Intervall stehen in der Ergebnistabelle wie im Methodentext
  („3.90 × 10⁻²“ statt „0.039“).
- **Reaktionspfad im Rahmen der Tabs:** eine Reiterzeile (Gestalten · Rechendaten · 3D / Orbitale · Ladungen ·
  Energietabelle · SI-Text) statt einer zweiten Zeile in „3D / Orbitale“; ein blauer Hauptknopf: „Profil exportieren“,
  „Exportieren“ des DFT-Teils bleibt grau, ohne Rechnungen ist „Daten ▾“ (bzw. der
  Knopf der Anleitung) der Hauptknopf. Meldungen des DFT-Teils (kopiert, gespeichert, zurückgesetzt, Atom unter dem
  Mauszeiger) erscheinen jetzt als Einblendung im Hauptfenster. Rechendaten: keine Kopfzeile über beiden Spalten mehr
  (die Schritte springen beim Reiterwechsel nicht mehr um 40 px), „Aus Verbindungen übernehmen“ öffnet als Karte im
  Schritt Daten, Fußleisten links (Zurücksetzen: Lage der Beschriftungen oder „Stil auf Standard“, das Werte, Lage der
  Plateaus, maßstäblich/schematisch, Verbinder und Abschnitte behält) und rechts (Bildunterschrift) wie in den Tabs, der
  Ansichtszoom steht im Schritt Darstellung (Karte Größe), ohne Rechnungen ein grauer Platzhalter statt Text im Bild,
  die Tabelle der Rechnungen so hoch wie ihre Zeilen und ohne den abgeschnittenen Knopf am Rand, die IRC-Liste als
  Tabelle. Gestalten: Werkzeugknöpfe so hoch wie die übrigen Leistenknöpfe, SI-Unterschrift mit „Kopieren“ (die fertige
  Unterschrift, eigene oder die der eingefügten Profile), die eingebettete Orbitalansicht als Formular ohne eigenen
  blauen Knopf. Der Export der Komposition schreibt die Formate aus „Größe und Formate“ (Vorgabe PDF, SVG, PNG wie
  bisher; CDXML und CDX immer). Abbildungen, Energien, Unterschriften und Stempel eingefügter Profile bleiben gleich.
- **Nichts wechselt von selbst.** Abgelegte Dateien und Messdaten, die aus einem anderen Tab geöffnet werden, wechseln
  den Tab nicht mehr: Eine Einblendung nennt den Ziel-Tab mit „Anzeigen“, der Tab-Knopf trägt einen Punkt bis zum
  Öffnen. Eine Karte links, die eine nicht offene Ergebnisseite ändert (NICS, ACID, NBO, HOMA, Abstände in der Packung,
  PXRD, Vergleich mit Rechnung, Lebensdauer, EPR-Rechnung, NTO), nennt diesen Reiter, und der Reiter bekommt einen Punkt
  bis zum Ansehen. Dieser Punkt ist blau (Akzentfarbe); der orange Punkt am Schritt bedeutet weiter „weicht vom Standard
  ab“. In den Tabs einer Verbindung behalten Standardwerte, Vorlagen, Rückgängig, Sprache und Design den
  offenen Ergebnisreiter und den Bildlauf der linken Spalte (vorher zurück auf „Abbildung“ und nach oben; gemessen im
  CV-Tab); Standardwerte, Vorlagen und Rückgängig behalten ebenso den offenen Reiter eines Vergleichs sowie Reiter und
  Bildlauf der Spalte eines Reaktionspfads; bei offenem Reaktionspfad behält der Sprach-/Designwechsel dessen Reiter und den
  Bildlauf seiner Spalte, ein offener Vergleich bleibt offen. Strg+F in einer Verbindung zeigt den Filter ihres Projekts
  statt der Übersicht.
- **Eine Meldung nach jedem Export.** Exportieren, SI (Word), Gesamt-SI und Datenpakete melden gleich, als Einblendung
  statt Dialog: Ziel und Formate und, was benutzt wurde – bei SI (Word) die Teile, die abgewählten Abbildungen (vorher
  nicht genannt) und die Tabellen mit eigenem „In die SI“; bei Datenpaketen die Zahl der Dateien bzw. die je Verbindung
  abgewählten. Klick-Ziele springen zum Ort der Auswahl („Formate ändern“, Karte SI-Export, Tab der Tabelle, „Ordner
  öffnen“). Die Gesamt-SI folgt der SI-Auswahl jeder Verbindung (Spalte **SI** im Tab „Export“). Strg+E in Synthese
  und NMR meldet genauso. Wurden Teile ausgelassen (nicht lesbar), steht
  die Meldung zugeklappt als eine Zeile über der Abbildung („SI gespeichert – 2 Hinweise“) mit „Details“ zum Aufklappen
  und „Schließen“; vorher verdeckte die volle Meldung die Abbildung bis zum Schließen.

### Behoben
- **NMR-Rohdaten mit extremen Filterwerten:** Eine unendliche Gruppenlaufzeit (GRPDLY) bringt die Prüfung der eigenen
  Verarbeitung nicht mehr zum Absturz, sie wird mit Meldung abgelehnt; ein nicht ganzzahliges DECIM wird abgelehnt statt
  auf eine ganze Zahl gekürzt. Alle geprüften echten Datensätze rechnen genau wie bisher.
- **Reaktionspfad: Profil in PNG/PDF verschoben.** In der exportierten Komposition (PNG, PDF), ihrem Word-Bild und
  der Kartenvorschau stand das Energieprofil mit seiner linken oberen Ecke in der Mitte der Fläche, klein und rechts
  abgeschnitten (seit 1.1.0): der Renderer ignorierte die Lage des eingebetteten Profils. Es steht jetzt wie auf der
  Fläche; der SVG-Export bleibt unverändert.
- **Laden einer Vorlage löschte Daten.** Vorlagen trugen Rechnungen und Auswerteeinstellungen mit (TD-DFT-NTOs, die
  EPR-Rechnung, NICS-/ACID-/NBO-Dateien, das Energieprofil, die HOMA-Auswahl), und das Laden einer Vorlage entfernte sie
  aus dem Tab oder setzte die Dateien einer anderen Verbindung hinein. Vorlagen enthalten jetzt nur Darstellung; beim
  Laden werden ältere Vorlagen genauso gefiltert, Dateien, Zuordnungen und Auswertung der offenen Verbindung bleiben.
- **Verbindungsname mit Punkt** (z. B. „S3.1“): Die Exporte aller Tabs hießen „S3.pdf“, „S3.xyz“ … statt
  „S3.1_CV.pdf“, und die Tabs überschrieben sich die Abbildungen gegenseitig ohne Meldung (nur der letzte Export
  blieb). Jede Datei behält jetzt den vollen Namen `<Verbindung>_<Tab>`; ebenso Vergleiche und Reaktionspfade mit
  Punkt im Namen und ein ohne Endung eingegebener Dateiname beim Speichern einer xyz-Datei oder Zeichnung. Früher
  unter falschem Namen geschriebene Dateien bleiben im Ordner.
- **Alte Projekte mit einer Datei, die die strengeren Leser jetzt ablehnen** (abgeschnittene Rechnung, Messdatei ohne
  Werte, beschädigter MS-Bericht oder Mnova-SVG): Export, SI (Word) und Gesamt-SI lassen nur den betroffenen Teil weg
  und nennen Datei und Grund in der Abschlussmeldung, statt still Abbildungen, Tabellen oder Methodentexte zu verlieren
  oder ganz abzubrechen. Vorher brach z. B. der EPR-Export ab, wenn die Rechnung (Spindichte/Hyperfein) nicht lesbar
  war, und eine Gesamt-SI ließ eine ganze Verbindung still weg. Die Tabs HRMS, NMR, DFT und Fluoreszenz öffnen sich auch
  mit so einer Datei wieder (vorher fehlte der Tab bis zum Neustart) und zeigen den Grund; eine nicht lesbare
  ε-Messdatei bricht das Öffnen der Verbindung nicht mehr ab und bleibt mit ihren Serien unverändert in der Projektdatei.
  Ist eine Stufe eines Reaktionspfads nicht lesbar, wird sein Energieprofil nicht gezeichnet (ohne die Stufe änderten
  sich Bezug und Werte) und gemeldet; die Gesamt-SI enthält die übrigen Pfade statt ganz abzubrechen. Ist der MS-Bericht
  nicht lesbar, steht „found –“ statt still das Mittel aus den Rohdaten.
- **EPR, Kopplungen aus einer Rechnung:** die Zuordnung berechneter Kerne zu einer experimentellen Gruppe wird gegen
  das Element der Gruppe geprüft; nach Änderung der Kerne der Simulation steht kein Wert eines anderen Elements mehr
  unter „(exp. …)“ – die Gruppe bleibt ohne Beschriftung, die Karte sagt es. Keine „−0.00“ mehr in den Beschriftungen;
  Prozente kaufmännisch gerundet wie überall.
- **EPR, Spinzählung:** Zahl der Scans, Empfängerverstärkung und Konversionszeit (BES3T `RCAG`, `SPTP`/`ConvTime`) und
  die Mikrowellenfrequenz werden mit verglichen; weichen sie ab, warnt ein deutlicher Hinweis, dass die
  Konzentrationen um dieses Verhältnis falsch sind, wenn die Spektren nicht normiert sind (nichts wird umgerechnet).
  Proben außerhalb der Kalibrierung oder mit negativer Konzentration sind gekennzeichnet (Tab, Unterschrift,
  Methodentext). „All spectra processed identically“ nur, wenn ein Dunkelspektrum bei allen oder keiner abgezogen wird.
- **NMR, Kernzahl:** ²H-NMR wird gegen D der Formel geprüft (auch `[2H]`), ³H gegen T. Mehrere H-Zahlen in einem
  Signal („2H, 3H“) bleiben in der NMR-Zeile stehen und gelten als mehrdeutig, statt nur die letzte zu zählen.
- **Raman:** ohne Eingabe ist die Anregungswellenlänge „nicht angegeben“ und λexc entfällt in SI-Zeile und
  Unterschrift (keine Vorgabe 785 nm).
- **CV:** die Referenzelektrode des Aufbaus hat ein eigenes Feld („Referenz“); die Referenz der Achse steht nicht mehr
  als „… as reference electrode“ im Text, wenn sie nicht eingetragen wurde (ihre Vorgabe ist keine Angabe zum
  Aufbau). Die Stromkonvention steht nur in der Unterschrift, wenn das Projekt eine nennt und das Bild abweicht oder
  die Ströme umgekehrt sind; eine Gamry-Datei mit anderer `CONVENTION` gibt einen Hinweis. Reine DPV/SWV-Serien
  bekommen einen eigenen Satz statt der CV-Sätze (E1/2, Nicholson). Eine leere Kurve hält die Hinweise nicht mehr an.
- **EPR, isothermer Fit bei steigender Intensität (k < 0):** Tab, Unterschrift und Methodentext nennen „Intensität
  steigt, keine Halbwertszeit“ statt eines Zerfalls. Die Ergebniszeilen der Methodentexte von EPR und UV-Kinetik
  schreiben negative Geschwindigkeitskonstanten mit echtem Minus wie die Unterschrift.
- **X-Ray-Packung: Moleküle auf Symmetrieelementen.** Bei einem Molekül auf einem Inversionszentrum, einer Spiegelebene
  oder einer zweizähligen Achse (Z′ < 1) nannten die Vorschläge Kontakte des Moleküls mit sich selbst (d = 0.000 Å) und
  jeden Nachbarn doppelt. Ein Nachbar ist jetzt durch seine Atome bestimmt (nach Symmetrie und Translation), nicht durch
  die Operation: symmetrisch gleiche Paare stehen einmal da, Bilder des Moleküls selbst nie; jedes Ringpaar auch bei
  selbstinversen Operationen nur einmal.
- **X-Ray-Packung: Symmetriecodes.** Der Code des Partners berücksichtigt jetzt, wie seine Atome bzw. sein Ring im Molekül
  erzeugt wurden, und ein von Hand gewählter Kontakt zwischen zwei Kopien wird relativ zur ersten codiert (Ga⁻¹∘Gb statt
  nur Gb; die Abstände stimmten schon). Der erste Partner steht an der Lage der CIF-Atome. Eine Nummerierung für
  Molekülbild, Liste, Unterschrift und SI: die Codes der erzeugten Atome behalten ihre Ziffern, Codes der Partner folgen
  danach. Symmetrisch gleiche Ringe eines Moleküls teilen eine Cg-Nummer; ein Ring auf einem Symmetrieelement nennt seine
  erzeugten Atome. Translationen wie 1/3 und 1/6 werden exakt gespeichert (alte Projekte mit 0.3333 gelten als 1/3).
- **PXRD: fehlende Auslenkungsparameter.** Atome ohne U_iso/U_ij in der CIF bekommen nicht mehr still angenommene
  0.02 Å² (auch U = 0 aus der CIF wurde ersetzt): sie werden ohne Temperaturfaktor gerechnet, Karte (in der Warnfarbe)
  und Methodentext nennen sie.
- **SI-Verweise.** Mit den Bezeichnern „Supplementary Figure“ oder „Figure S“ werden Verweise im Text auch in der
  Mehrzahl („Figures S1 and S2“), als Bereich („Figure S1–S3“ → „Supplementary Figures 1–3“), mit Teilbild („Figure S1a“),
  als „Fig S4“ und „Figure S 3“ umgestellt; „Figure 3“ (der Artikel) bleibt.
- **Elementaranalyse, Doppelbestimmung.** Hat ein Element nur einen Wert, sagt die Zeile das („N determined once“) und
  mittelt nur Elemente mit zwei Werten; ein Element nur im zweiten Satz fällt nicht mehr weg.
- Deutsche Platzhalter der CV-Angaben eines Projekts beginnen mit „z. B.“.
- **Projekt-Vergleich, Fluoreszenz:** seit dem Anregungsspektrum nahm der Vergleich (und `.elucida/compare.json`) das
  Anregungsspektrum als Emission. Die Emission ist im Tab jetzt eindeutig gekennzeichnet; gespeicherte
  Vergleichsdaten von Verbindungen mit Anregungsspektrum gelten als veraltet und werden mit „Aktualisieren“ neu
  gebildet (keine andere Datei wird verändert).
- **Verbindungsordner verschieben:** ACID-Dateien (Log, Cube, AICD-`.inc`) und NBO-Ausgaben mit ihrer NRT-CML wurden
  mit absoluten Pfaden gespeichert und fehlten nach dem Verschieben; jetzt relativ zum Ordner, fehlende werden gemeldet.
- **Datenpaket:** neue Rechnungs- und Messdateien fehlten ohne Hinweis: IR-Frequenzrechnung, EPR-Rechnung und
  Orbital-/Spindichtedatei, NTO-Cubes/-Molden, ACID (Log, Cube, AICD-Ordner), NBO-Ausgabe und CML, Geometrie des
  X-Ray-Vergleichs und PXRD-Messungen (neue Gruppe „PXRD“); fehlende Dateien werden genannt. In CompChem.zip bleibt
  der AICD-Ordner erhalten.
- **FID for Publication:** beachtet die Abwahl im Datenpaket-Dialog und nennt die Verbindungen wie im Zip (ersetzte
  Laborkürzel) in `NMR_parameters.txt` und im Data Availability Statement.
- **SI, DFT:** eine Bedingung „DFT hat Daten“ für Einzel- und Gesamt-SI: auch nur NBO, ACID aus einer AICD-Ausgabe
  (ohne Cube), NICS oder IRC kommen jetzt in die Einzel-SI.
- **DFT, „Alles auf Standard“:** leert geladene NICS-, ACID- und Energieprofildaten nicht mehr, nur die Darstellung.
- **NBO:** die Unterschrift nennt bei geschlossenschaliger Ausgabe kein „α-spin Wiberg …“ mehr (die Spinwahl wird beim
  Laden zurückgesetzt); eine NBO-Ausgabe ohne Geometrieblock bricht DFT-Export und SI nicht mehr ab: Tabellen und CSV
  wie gedruckt, keine Abbildung, mit Hinweis.
- **DFT-Energietabelle:** die Notiz sagt jetzt, warum *H*_corr bei ORCA „–“ ist (ORCA druckt H − E_el nicht; seine
  „Thermal Enthalpy correction“ ist nur k_B·T, geprüft an echten ORCA-6-Opt+Freq-Ausgaben).
- **NICS:** eine Datei mit 200 oder mehr Bq entlang eines Wegs (langer gerader oder geknickter Scan) ist ein Scan, kein
  Teil eines 3D-Gitters; Bq, die alle in einer Ebene liegen, werden mit diesem Grund abgelehnt statt „Punkte fehlen“.
- **NTO-Cubes ohne MO-Nummer:** Loch und Teilchen werden nicht mehr aus der Auswahlreihenfolge geraten (nur aus
  „hole“/„particle“ im Dateinamen, sonst Meldung); das Gewicht aus der Ausgabe vergleicht auch den Spin (α/β).
- **DFT-Tab einer Verbindung:** mit zwei oder mehr Opt/Freq-Rechnungen kam ein Energieprofil, das der Tab nicht mehr
  zeigt, in Einzel- und Gesamt-SI und in den Export (mit verschiedenen Molekülen oder Methoden sinnlose Werte). Das
  Profil gehört in den Reaktionspfad; in einer Verbindung zählt nur ein schon gespeichertes Profil (ältere Projekte).
- **SI, EPR-Rechnung ohne gemessene Spektren:** ihre Abbildungen kamen ohne Methodentext; der Methodentext folgt jetzt
  derselben Bedingung wie die Abbildungen.
- **Zahlen nahe null:** kein „−0.000“/„−0.0“ mehr (CV-E½ nahe der Referenz, HR-MS-Abweichung, ε einer Bande ohne
  Absorption, HOMA, NICS-Spalten, EA-Δ).
- **HR-MS:** der Status ≤ 5 ppm wird an der gedruckten Abweichung geprüft (+5.0 ppm ist immer „≤ 5 ppm“, wie bei der
  Elementaranalyse); der Export schreibt kein leeres `_data.csv` mehr (das Linienspektrum steht in `_sticks.csv`).
- **Fluoreszenz:** Bild, Kachel und Projekt-Vergleich runden λabs, λem und ε wie die Kennwerte-Tabelle
  (kaufmännisch, 452.5 → 453; vorher zeigte das Bild 452 und für ε = 12344.5 den Wert 12344); die Lebensdauer-Kachel
  nimmt die Einheit der Tabellen (µs ab 1000 ns).
- **Word:** Namen in Tabellenunterschriften stehen wie eingegeben („S3_opt_freq“, nicht „S3\\_opt\\_freq“).
- **NMR, Prüfung des Achsenbereichs:** eine Zeile Integrale unter dem Spektrum mit mehr Zahlen als die
  Achsenbeschriftung konnte als Achse gelten; jetzt zählen nur gleichmäßig gestufte Beschriftungen.
- **SEC, BWSpec-Dateien:** eine Datei mit weniger Datenzeilen als der Pixelbereich im Dateikopf (abgeschnitten) wird
  mit Meldung abgelehnt, statt still mit einem Teil des Spektrums gelesen.
- **Gaussian-Orbitalenergien** einer Ausgabe mit reinem CR als Zeilenende nehmen die Zahlen hinter den
  Eigenwert-Zeilen nicht mehr als weitere Orbitale.
- **CV-Ergebnis-CSV** hängt nicht mehr von der Sprache ab: die Spalte `reference` enthält die Skala („Fc0/+“ oder die
  Referenzelektrode) statt des Hinweistexts.
- **Abgeschnittene Rechnungen:** X-Ray-Vergleich mit einer Rechnung und IR-Rechnung gegen Messung lehnen eine nicht
  normal beendete Ausgabe ab (Geometrie oder Moden können unvollständig sein).
- Kleinigkeiten: Elementaranalyse als Doppelbestimmung mit einem nur einmal bestimmten Element zeigt diesen Wert in der
  Spalte „Mittel bzw. Einzelwert“; die CV-Richtlinienprüfung nennt die Referenzelektrode des Aufbaus; NBO: Hinweis,
  wenn in der CML freie Elektronenpaare fehlen (keine Formalladungen); die Gesamt-SI hat keine leere „Synthesis of X“
  für Verbindungen ohne Synthese und Daten; der Standard-Reihenname „probe“ erscheint deutsch als „Probe“, englisch als
  „sample“, auch im Methodentext (der gespeicherte Schlüssel bleibt); EPR-Methodentext „from a calculation at the …
  level of theory“ (kein „a M06-2X“); der EasySpin-Export lässt Parameter ohne Wert weg („T [K]: None“); die
  Synthesetabelle rundet Ausbeute und Äquivalente kaufmännisch wie die SI-Zeile.
- Beispielprojekt: die EPR-Hyperfein-Zuordnung gehört wieder zur S = ½-Simulation (Seite „Hyperfein“ zeigt „(exp. …)“
  und die berechneten Mittel); das ¹H-Spektrum von S3 ist 0–10 ppm beschriftet (kein Bereichshinweis; S2 behält die
  kurze Achse 1–9 ppm als Warnfall); die ε-Serien nennen ihr Lösungsmittel (THF), Unterschrift und SI-Zeile sind
  vollständig.
- **ORCA-/Gaussian-Ausgaben mit mehreren Jobs** (ORCA `$new_job`/Compound, Gaussian `--Link1--` mit eigener Route):
  Ladung, Multiplizität und Methode kamen aus dem ersten Job, Energie, Geometrie und Frequenzen aus dem letzten. Jetzt
  stammt alles aus dem letzten vollständigen Job; Schritte, die Gaussian selbst anhängt (opt freq), bleiben ein Job.
- **Abgeschnittene ORCA-/Gaussian-Ausgaben:** ein mitten im Koordinatenblock abgeschnittener Block ergab eine
  Teilgeometrie; jetzt gilt der letzte vollständige Block (die Ausgabe gilt als nicht normal beendet).
- **Dateien, die vorzeitig enden oder unlesbare Zeilen enthalten, wurden still verkürzt oder falsch gelesen; jetzt
  werden sie mit Meldung abgelehnt:** TD-DFT-Tabelle von ORCA (fosc jetzt über ihren Spaltenkopf), ORCA-ESD-Spektrum
  (abgeschnittene oder gestörte Zeile, mit Zeilennummer), Cary-.DSW (weniger Spektren oder kürzeres letztes Spektrum),
  Gamry-Dateien der H-Zelle (Zeilenzahl aus dem Tabellenkopf der Schrittdateien; Hauptdatei mit weniger Halbzyklen als
  CYCLES und ohne Abbruchgrund), EPR-Textdateien (gemischte Dezimaltrenner,
  verschmolzene Zahlen wie „330.37-6.92“, Überlauf „****“, mit Zeilennummer), Cube-Dateien mit zu wenigen oder zu
  vielen Werten.
- **EPR-Textdateien:** die Feldeinheit kommt nur noch aus dem Kopf der Feldspalte („Amt“ oder ein Probenname mit „mt“
  bedeutet nicht mehr mT); ohne Einheit dort wird sie wie bisher angenommen und ist wählbar.
- **Cary-CSV aus deutschem Excel:** mit den Probennamen direkt über den Daten und „;“ plus Dezimalkomma wurde nur eine
  Probe gelesen; das Trennzeichen folgt jetzt dem Aufbau aller Zeilen.
- **Cary-Eclipse-CSV mit Spalte „Z Axis“ (eine Wellenlängenspalte, je Probe eine Intensitätsspalte):** nur die erste
  Probe wurde gelesen (ε, Fluoreszenz); jetzt alle Proben mit ihren Namen. Ein Aufbau, der weder zum paarweisen Export
  noch zu diesem passt, wird mit Meldung abgelehnt statt verkürzt gelesen. Ebenso eine Cary-CSV mit einer benannten
  Probe ohne Datenspalten (die Probe fiel still weg).
- **Textdateien für Raman, PXRD und Abklingkurven:** die Indexzeile der Z-Achse eines solchen Exports („,1,2“ unter
  den Probennamen) galt als Datenpunkt; eine Abklingkurve damit wurde abgelehnt. Die Zeiteinheit einer Abklingkurve
  kommt aus der Zeitspalte des Spaltenkopfs, auch über Zeilen mit Probennamen, und nie aus Metadaten darüber
  („Resolution [ns]“ über „Time,Counts“ ergab ns).
- **Klare Meldungen statt Python-Fehlertexten** bei Gamry- und BWSpec-Dateien mit Dezimalkomma, Cube-Dateien in UTF-16
  (werden jetzt gelesen), leeren oder abgeschnittenen Cube- und Molden-Dateien, beschädigtem MS-Bericht (.docx) und
  leerem OPUS-PDF.
- **X-Ray: „Kopieren“ der Bildunterschrift** kopierte die Unterschrift des Moleküls, während die Seite die der
  Packung zeigte; jetzt wird die angezeigte Unterschrift kopiert.
- **SEC: Referenz „aus CV-Tab“.** Das Feld „E(Fc⁺/Fc) gemessen“ zeigte 0.0, benutzt wurde der Wert des CV-Tabs;
  jetzt heißt es nach der im CV-Tab gewählten Referenz und zeigt deren E½ gegen die Elektrode („E½ Fc (CV)“, bei
  eigener Referenz „Referenz E½ (CV)“); bei Verschiebung von Hand oder ohne gefundene Referenz heißt es „Verschiebung
  (CV)“ und zeigt die benutzte Verschiebung (gesperrt, der eigene Wert gilt wieder ohne den Chip). Die Achse rechnet
  mit E½ minus dem Wert der Referenz gegen Fc⁺/Fc. Eine fehlende CV-Referenz nennen die Ergebnisse, statt sie zu
  verschlucken, und „Noch keine Ergebnisse“ bleibt über dem Referenzhinweis stehen; ohne Fc-Referenz nennt die Achse die
  Elektrode dieses Tabs statt der des CV-Tabs; die Vorschau folgt einer geänderten CV-Referenz beim nächsten Anzeigen
  (Export und SI taten das schon).
- **EPR › Hyperfein-Zuordnung:** Der Hinweis schickte in den Reiter „Hyperfein“, ohne Weg dorthin; der Reitername ist
  jetzt ein Link, der ihn zeigt. Die Wahl einer Gruppe wechselt weiterhin nichts von selbst. Das Ansehen des Reiters
  „Hyperfein“ erzeugt keinen Rückgängig-Schritt ohne sichtbare Änderung mehr.
- **Wahlen, die außer Sicht wirken, sagen es jetzt:** Die DFT-Seiten „Ladungen“ und „Multireferenz“ nennen ihre
  Rechnung (mit Link zur Tabelle der Strukturen; ihre Chips „In die SI“ gelten je Rechnung); X-Ray „Abstände in der
  Packung“ sagt beim Molekülbild, dass die Häkchen nur im Packungsbild wirken (Link zur Wahl der Abbildung); die Wahl
  der NICS-Abbildung sagt, dass Export und SI Scan und 3D enthalten; im Reaktionspfad nennt „Einfügen ›
  3D-/Orbitalansicht“ die gewählte 3D-Quelle.
- **Nacharbeiten Reaktionspfad:** Die Seite „Ladungen“ ist gleich beim Öffnen da (erschien erst nach dem ersten Besuch
  von „3D / Orbitale“); ein Pfad nur mit IRC zeigt einen blauen Knopf („Profil exportieren“), nicht zusätzlich den der
  Anleitung; eine IRC, deren Ausgabe geometrische Parameter auflistet, lässt sich wieder einsetzen (Stempel); „Stil auf
  Standard“ behält den eigenen Achsentitel und die Vorzeichen (+18.9, ±0.0: sie ändern gedruckte Werte); die Pfadliste
  (☰) ist eine Tabelle mit Kopf (Vorschau und Name linksbündig); Schließen eines Pfads ohne Änderung schreibt seine
  Projektdatei und Vorschau nicht mehr neu; ein Pfad zeichnet beim erneuten Anzeigen mit dem Textformat des Fensters
  (nach einem Sprach- oder Designwechsel in einer Verbindung mit eigenem Format behielt er deren Format); „Kopieren“
  einer eigenen Unterschrift der Komposition klappt auch mit veraltetem Profil; die eingebettete Orbitalansicht hält
  ihren Knopf ohne Python-Event-Filter grau.
- **Reaktionspfad, Gestalten:** „Bild bearbeiten …“ nennt, wo ein Profil bearbeitet wird („Rechendaten“, danach
  „Profile aktualisieren“), im Tooltip und in der Meldung beim Seitenwechsel; der Tooltip von „Zurücksetzen“ nennt beide
  Einträge.
- **Abgelegte Dateien ersetzen UV-Vis (ε) nicht mehr unbemerkt.** Messdateien, die auf den Tab UV-Vis-Kinetik gezogen
  werden, kommen dorthin; auf dem Tab Fluoreszenz bittet das Programm, in der Karte Daten Absorption oder Emission zu
  wählen, und lädt nichts. Messdaten ohne Konzentrationen, die die ε-Daten ersetzen, sind jetzt ein Rückgängig-Schritt
  (vorher brachte Rückgängig die vorherige ε-Auswertung nicht zurück).
- **Gesamt-SI:** Der Aufbau-Text des Tabs H-Zelle steht wie die der anderen Tabs in „Materials and Methods“.
- **SI (Word):** Die Abwahl „DFT“ unter „Abbildungen“ lässt auch die Orbital-, NBO- und Resonanzstruktur-Bilder der
  Rechnungen weg (Bild der Geometrie und Tabellen bleiben beim Teil „DFT“).
- **Projektseite und Übersicht:** „Exportieren (aktueller Tab)“, „SI-Abschnitt exportieren“, „Datenpaket (Zip) exportieren“ und „Schrift
  und Rahmen“ sind dort abgeschaltet (sie wirkten auf einen verborgenen Tab oder fragten nach einer neuen Verbindung);
  im offenen Vergleich exportiert Strg+E den Vergleich.
- Der Tooltip von „Vorlagen ▾ › speichern“ nennt keinen Speicherknopf in der Werkzeugleiste mehr.
- **UV-Vis (ε): Neue Messdaten behalten die Einstellungen einer Serie**, die darin weiter vorkommt (Foto, Lösungsmittel,
  Freistellung, Lösungsfarbe, „Struktur im Bild“); vorher setzte Laden oder Ablegen neuer Daten sie zurück, und das
  nächste Speichern machte den Verlust dauerhaft. Label-Positionen und Cutoff je Bande beginnen neu (sie gehören zu den
  alten Banden).
- **Weitere, Reiter SI-Text:** zeigt die Bildunterschrift der angezeigten Abbildung (auch in der Fußleiste); vorher
  stand dort „Noch keine Bildunterschrift“, obwohl die Abbildung eine hatte.
- **EPR, Reiter Ergebnisse:** die S = ½-Fits (g, ΔBpp, Kopplungen, R²) stehen als Tabelle mit denselben Zahlen wie in
  der Bildunterschrift; vorher meldete die Seite „Noch keine Ergebnisse“, obwohl ein Fit vorlag.
- **NMR mit Quelle MNova-SVG:** die Karten im Schritt Darstellung bleiben sichtbar, aber ausgegraut (Tooltip nennt den
  Grund), statt den Schritt leer zu lassen; im Schritt Auswertung nennt der Hinweis die Karten, für die er gilt.
- **NMR, Rohdaten:** das Ordnersymbol von „TopSpin-Daten …“ ist im hellen Design sichtbar.
- **DFT-Orbitale (auch Reaktionspfad):** das Feld Schwelle zeigt nur die nötigen Stellen („80 %“ statt „80.0000 %“).
- **NMR (Englisch):** die Strukturlage „auto (free space)“ wird nicht mehr abgeschnitten.
- **Dunkles Design:** Farbknöpfe haben einen hellen Rand; eine schwarze Linienfarbe wirkt nicht mehr wie ein leerer Knopf.
- **X-Ray/DFT:** der Knopf, der das Aussehen zurücksetzt, heißt „Auf Standard“ (vorher nur „Darstellung“).
- **NMR-Vorschau:** die Struktur wird vor dem Zeichnen glatt verkleinert; dünne Bindungen fallen nicht mehr aus.

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
