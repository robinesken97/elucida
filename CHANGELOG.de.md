[English](CHANGELOG.md) | **Deutsch**

# Änderungen

## 2.1.0 – 24.10.2026

### Neu
- **Orbitale im DFT-Tab, Aussehen wie IboView:** Isoflächen von Molekülorbitalen über der Struktur. Eingabe als
  Molden-Datei (ORCA: `orca_2mkl name -molden`; alle MOs, HOMO und LUMO werden angelegt, weitere aus einer Liste)
  oder als Gaussian-Cube (ORCA: `orca_plot`, Gaussian: `cubegen`). Isofläche wie IboView mit 80 % der Orbitaldichte
  (einstellbar, oder fester Isowert), IboView-Farben je Orbital, durchscheinend mit deckenderen Rändern, Licht und
  Aufhellung nach hinten wie IboView; Atome wie in IboView (zur Mitte verjüngte Stäbe, Elementbuchstaben, Doppel- und
  Teilbindungen aus der Wellenfunktion wie IboViews IAO-Bindungsordnungen). Direkt mit IboView verglichen.
- **NMR-Rohdaten:** TopSpin-Experimente (auch ganze Datensätze oder mehrere auf einmal, auch per Ziehen) kommen
  vollständig ins Projekt, nach Art sortiert (`data/nmr/1H`, `13C`, `DEPT135`, `HSQC` …), stehen im neuen Reiter
  **Rohdaten** neben der Abbildung und werden dem passenden Spektrum automatisch zugeordnet (Parameter, Temperatur).
  Mnova-Dokumente (`.mnova`) lassen sich ebenfalls ablegen.
- NMR-Spektren können auch **EMF**-Dateien aus Mnova sein; sie gehen unverändert nach Word.
- Das IboView-Aussehen ist im DFT-Tab auch als Stil für jede Struktur wählbar, mit oder ohne Orbitale.
- HOMO/LUMO-Bezeichnung und Orbitalenergien aus der Molden-Datei bzw. der ORCA/Gaussian-Ausgabe der Geometrie.
- Export: je Orbital eine Abbildung (PDF/SVG mit dem Orbital als eingebettetem 300-dpi-Bild, Atome und Labels bleiben
  Vektor); Word-SI: Orbitalbilder mit Unterschrift unter der jeweiligen Rechnung.
- Molden-Dateien werden geprüft: die Konvention der Basisfunktionen (Standard oder ORCA) ergibt sich aus der
  Orthonormalität der Orbitale; passt keine bekannte, wird die Datei abgelehnt.
- **elucida.json** im Projektordner: eine Zusammenfassung für das Programm Characterization (Verbindung mit
  SMILES/InChIKey, welche Analytik vorliegt und wo ihre Dateien liegen, HR-MS- und Elementaranalysewerte, die SI-Zeilen
  und der Absatz, die SI-Word-Datei und die letzten Abbildungen). Wird beim Speichern, nach Exporten und kurz nach dem
  automatischen Speichern geschrieben; Characterization liest sie nur.

### Geändert
- **Übersichtlicherer Projektordner:** Exporte sind nach Art sortiert – `SI/` (Word-Dateien, SI-Texte), `figures/`
  (PDF/SVG/PNG) und `tables/` (CSV, Excel, xyz) – und nach der Verbindung benannt (z. B. `S2_CV.pdf`, `S2_SI.docx`;
  UV-Vis je Serie `<Serie>_UV-Vis.pdf`). Messdaten kommen nach `data/<Analytik>/` (nmr, ir, hrms, uvvis, cv …),
  Strukturen, Schemata und Fotos nach `structures/`. Zwischenbilder für Word, der Foto-Cache und die Sicherung liegen
  im versteckten Ordner `.elucida/`. Ordner entstehen erst, wenn etwas hineinkommt.
- Die Projektdatei heißt jetzt **`project.elucida`**. Projekte älterer Versionen (`project.uvvis`) öffnen wie bisher;
  beim Speichern entsteht die neue Datei, die alte bleibt als Sicherung in `.elucida/`. Elucida 2.0 und älter können
  mit 2.1 gespeicherte Projekte nicht öffnen.
- Projekte aus älteren Versionen öffnen wie bisher; ihre Dateien bleiben liegen, nur neue Dateien und Exporte kommen in
  den neuen Aufbau.
- Quellcode neu geordnet im Paket `elucida/` (app, core, tabs, formats, si, exchange); Start aus dem Quellcode mit
  `python Elucida.py`. Für die installierte App ändert sich nichts.

## 2.0.3 – 23.10.2026

### Neu
- **Strichzeichnung** als Stil im DFT-Tab, wie in klassischen Zeitschriftenabbildungen: weiße Kugeln mit Umriss,
  hohle Stäbe, vordere Atome etwas größer.
- **Labelfarbe** in X-Ray und DFT: schwarz oder wie das Atom (helle Farben abgedunkelt, damit sie lesbar bleiben).
- X-Ray und DFT: **Shift + Rahmen ziehen** blendet die Labels mehrerer Atome auf einmal aus oder ein.

### Geändert
- **Kugel-Stab** im DFT-Tab sieht aus wie die Abbildungen im ORCA-6-Handbuch (Farben, Licht, weicher Glanzpunkt,
  Proportionen); der IboView-ähnliche Stil ist entfernt. X-Ray bietet nur noch Mercury und Olex2; Projekte mit einem
  älteren Stil öffnen mit dem nächstliegenden.
- **Ergebnis-Reiter in allen Tabs gleich:** Die Karte füllt die Seite, Tabellen nutzen die volle Höhe, Knöpfe stehen
  rechts unten, der wichtigste blau. UV-Vis (ε) zeigt Ergebnisse und SI-Zeile neben der Abbildung statt darunter, die
  Abbildung wird dadurch größer; das Protokoll steht unter Hilfe → Protokoll.
- Die Anleitungen in leeren Tabs sehen überall gleich aus (auch Synthese und NMR) und stehen in der Mitte der Fläche.
- Meldungen erscheinen als kleines Feld unten rechts; der leere Statusstreifen unter den Fußleisten ist weg.

### Behoben
- Beim Öffnen eines Projekts konnte der Fehler „Internal C++ object already deleted“ erscheinen.
- macOS Intel: Das Beispielprojekt ließ sich nicht anlegen (ältere RDKit).
- Eine Abbildung konnte zu klein bleiben, nachdem sie hinter einem anderen Reiter verborgen war.

## 2.0.2 – 23.10.2026

### Neu
- **Startbildschirm** ohne Projekt: was das Programm kann, Neues Projekt / Projekt öffnen / Beispielprojekt ansehen und
  die zuletzt geöffneten Projekte.
- **Beispielprojekt** mit künstlichen Daten für alle Tabs (Hilfe → Beispielprojekt ansehen) – zum Ausprobieren.
- **Hilfe-Menü:** Anleitung zum aktuellen Tab (F1), Schnellstart, Beispielprojekt, Protokoll.
- **README:** Schnellstart in sechs Schritten und Schritt-für-Schritt-Anleitungen (Deutsch und Englisch) für Synthese bis
  zur SI, UV-Vis ε, CV und SEC, EPR, Kristallstruktur und DFT.
- Nach dem Export bietet die Meldung **Ordner öffnen** an; Synthese und NMR haben dieselbe Fußleiste
  mit **Exportieren** wie die anderen Tabs.

### Geändert
- Die **linke Spalte passt sich immer ihrem Inhalt an** – nichts wird rechts abgeschnitten, auch auf kleineren
  Laptop-Bildschirmen und bei breiterer Schrift (Windows); die übrige Breite bekommt die Abbildung.
- Knöpfe sind nur aktiv, wenn sie etwas tun können („Kombinieren“ ab zwei markierten TD-DFT-Einträgen, „Aus Schema“ mit
  Schema).

### Behoben
- UV-Vis (ε): Die linke Spalte konnte auf einem MacBook abgeschnitten sein („Konzentrationen…“, „g/mol“, „Entfernen“).

## 2.0.1 – 23.10.2026

### Neu
- **Übersichtlichere, ruhigere Oberfläche:** Die zwölf Tabs stehen wie die SI in Gruppen in einer Leiste oben (Synthese
  & Analytik, UV-Vis & Photophysik, Elektrochemie & EPR, Struktur & Rechnung); **SI (Word)** ist der Hauptknopf in der
  Werkzeugleiste. Die Abbildung bleibt so groß wie bisher – die neue Leiste kostet Höhe, nicht Breite.
- **Aufgeräumte linke Spalte in allen Tabs:** Selten gebrauchte Karten sind eingeklappt (Achsen, Größe und Formate;
  Bildunterschrift; CV-Referenzierung; SEC Hervorheben; EPR Intensität und Kinetik; X-Ray Atome, Ausrichten, Farben …).
  Eine eingeklappte Karte zeigt **„(geändert)“**, wenn darin etwas vom Standard abweicht. Ergebnisse, Tabellen und
  SI-Text stehen als Reiter neben der Abbildung (CV-Ergebnisse, X-Ray-Unterschrift und -Tabellen, DFT-SI-Text).
  Gleichmäßige Abstände, alle Zahlenfelder gleich breit und rechtsbündig, Beschriftungen auf Höhe ihrer Felder.
- **Anleitung in leeren Tabs:** was der Tab erzeugt, welche Dateien er braucht und woher sie kommen, vier Schritte, ein
  Link zum passenden README-Abschnitt und ein Knopf „Dateien hinzufügen…“.
- **Hinweise dort, wo sie entstehen:** Lässt z. B. das Overlay eine Kurve weg (keine Konzentration für ε), steht der
  Grund unter der Vorschau; **Hilfe → Protokoll…** zeigt das Protokoll aller Tabs.
- **X-Ray und DFT:** **Hintergrund** wählbar (weiß, transparent, Farbe) für Vorschau, PDF/SVG/PNG und Word.
- **Overlay:** vorhergesagte **Farbe in Lösung** für TD-DFT-Spektren (A = ε·c·d, Standard 1 mM in 1 cm; qualitativ).
- **UV-Vis (ε):** optionale **Indizes λ₁/ε₁ …** an den Bandenlabels.
- **Neues Icon:** Spektrum mit Pyridinring.

### Geändert
- **Kugel-Stab (X-Ray, DFT):** Atomradius und Bindungsdicke wirken jetzt, relativ zum Standard (die Standardwerte
  ergeben das bisherige Aussehen).
- **Schnelleres Drehen** in den Kugel-Stab-Stilen (etwa 20 ms statt 140 ms je Schritt bei 80 Atomen); Abbildungen und
  Exporte pixelgleich.
- Das Mausrad scrollt die linke Spalte und verstellt ein Feld erst, nachdem es angeklickt wurde.
- Klarere Bezeichnungen und Tooltips („Vorlage speichern…“ statt „Speichern…“, „Peakschwelle“, eindeutige
  Kopier-Knöpfe, ε-Befehle unter Datei → UV-Vis (ε), „Exportieren (aktueller Tab)“ …).

### Behoben
- Nach dem Ziehen eines Labels oder Bildes wird die Abbildung ganz neu gezeichnet; nichts verschwindet mehr bis zum
  nächsten Klick.
- CV: „wie oben“ bei der Referenz einer Messung verwies auf eine Einstellung weiter unten.

## 2.0.0 – 22.10.2026

### Neu
- **DFT-Tab: Messen und Ausrichten** wie im X-Ray-Tab – Abstand, Winkel und Diederwinkel durch Anklicken von 2/3/4 Atomen
  (Werte aus der Geometrie), Bindungsrichtung, Ebene von vorn, schrittweise drehen, wenden und ChemDraw-Vorlage. Beide
  Tabs nutzen denselben Code und verhalten sich gleich.
- **Neue Stile für Strukturen** im X-Ray- und DFT-Tab (Vorschau, PDF/SVG/PNG, Word): **Kugel-Stab, glänzend** (wie
  IboView: glänzende Kugeln mit Schattenrand und Glanzpunkt, dünne Stäbe in Atomfarben mit Glanzstreifen) und **Kugel-Stab
  mit Tiefe** (matte Kugeln, dicke Stäbe, weiter hinten liegende Atome heller).

### Geändert
- **Mercury-Stil** sieht jetzt aus wie Mercury-Abbildungen: schwarze Bindungen und fette Labels; Standard-Bindungsdicke
  0.12 Å (bestehende Projekte behalten ihre Einstellung). Elementfarben unverändert.
- **Neuer Name: Elucida** (früher Spectravolt). Das Programm ist von UV-Vis und Elektrochemie zu einer ganzen
  Charakterisierungs-Suite gewachsen (Synthese, NMR, IR, HRMS, UV-Vis, Fluoreszenz, CV, SEC, EPR, Röntgenstruktur, DFT).
  Einstellungen, zuletzt geöffnete Projekte und der Datenordner (z. B. das Modell zur Freistellung) werden beim ersten
  Start automatisch übernommen; Projekte öffnen wie bisher. Das Repository heißt jetzt `robinesken97/elucida`; alte
  Links und die Update-Prüfung älterer Versionen leitet GitHub weiter.
- Neues Icon: Das sichtbare Spektrum bleibt, ein Benzolring ersetzt den Blitz.
- Downloads heißen jetzt `Elucida-<System>.zip` (Windows/macOS), `.AppImage` und `.tar.gz` (Linux). Auf dem Mac heißt die
  App `Elucida.app`; die alte `Spectravolt.app` kann nach dem ersten Start gelöscht werden.

## 1.25.1 – 22.10.2026

### Neu
- Knopf **Projektordner anzeigen** in der Werkzeugleiste: öffnet den Projektordner im Finder (macOS), Explorer (Windows)
  bzw. im Standard-Dateimanager (Linux, z. B. Dolphin oder Nautilus); ohne Projekt gesperrt.

## 1.25.0 – 22.10.2026

### Neu
- **Alles auf Standard:** Der Knopf „Zurücksetzen“ (unten links in jedem Tab mit Abbildung, auch UV-Vis (ε)) hat ein Menü:
  „Layout zurücksetzen“ wie bisher oder „Alles auf Standard“ für alle Einstellungen des Tabs (Darstellung und
  Auswertung). Daten und Angaben zur Messung bleiben: Dateien, Referenz und Kalibrierung (CV, SEC, EPR), Schichtdicke,
  eingegebene Werte (ε, λex, Addukt, entfernte IR-Peaks), Bildunterschriften und Exportgröße. Rückgängig holt alles zurück.
- **X-Ray und DFT:** „Darstellung auf Standard“ neben „Ansicht zurücksetzen“: Stil, Ellipsoide/Radien, Bindungsdicke,
  Labels, Labelgröße, Fehlordnung, H-Atome und – für die gewählte Struktur – Ansicht, ausgeblendete Atome/Fragmente,
  Labels je Atom und Drahtmodell. CIF-/xyz-Dateien, Namen, Nummerierung und ausgewählte Parameter bleiben.

## 1.24.1 – 22.10.2026

### Neu
- **SEC: Zwischenspezies hervorheben.** Neben dem ersten (blau) und letzten Spektrum (rot) lassen sich ein oder mehrere
  Zwischenspektren grün hervorheben (weitere orange, violett, türkis), z. B. für das Radikalkation. Auswahl über das
  Potential (Achsenskala; genommen wird das Spektrum mit dem nächstliegenden Potential) oder ohne Potentialdatei über die
  Nummer des Spektrums. Potential-Label wie bei Start/Ende; λ-Labels in der Farbe des hervorgehobenen Spektrums mit der
  größten Absorbanz. Feld „Spezies Zwischenstufe“ in der Bildunterschrift: „Color coding: **neutral** (blue),
  **radical cation** (green), **dication** (red).“ – nur Farben, die im Bild vorkommen. Ohne Eingabe bleibt alles wie
  bisher.
- **SI (Word): Datenverarbeitung und Fits.** Neuer wählbarer Teil: die Methodentexte aller Tabs, die fitten (UV-Vis (ε),
  CV, SEC, EPR – derselbe Text wie „SI-Text kopieren“: nur benutzte Schritte, aktuelle Parameter, danach die Ergebnisse)
  als Abschnitt „Data processing and fitting“ hinter den Abbildungen.
- **Schriftart der Word-Exporte** im Dialog SI (Word) wählbar (Standard Arial); die Größe bleibt 11 pt.

### Geändert
- Synthese-Tab: Nur das Reaktionsschema steht auf weißem Grund (und nur, wenn eines geladen ist); der Vorschautext folgt
  wieder dem hellen/dunklen Erscheinungsbild.
- README: neue Screenshots aller Tabs (auch Synthese und NMR), erzeugt mit `tools/make_screenshots.py` nur aus
  künstlichen Daten.
- Checkboxen mit eigenem Rand und Haken in Akzentfarbe (nicht angehakte waren im dunklen Modus kaum zu sehen).

### Behoben
- UV-Vis (ε): Hinweise zur Struktur (Formel, „aus den CDXML-Koordinaten gezeichnet“, Warnungen) folgen jetzt einem
  Sprachwechsel.
- CV: Mit Farbverlauf nach Scanrate zeigen die Farbfelder der Liste die Farben des Bildes und sind gesperrt (vorher
  standen dort Farben, die nicht benutzt wurden).

## 1.24.0 – 22.10.2026

### Neu
- **Synthese-Tab:** „Synthesis of **Name**“, Reaktionsschema aus ChemDraw und Vorschrift mit Formatierung (fett,
  kursiv, tief-/hochgestellt). Mit einer gleichnamigen `.cdx` neben der CDXML wird das Schema in Word ein
  **bearbeitbares ChemDraw-Objekt** (Doppelklick öffnet ChemDraw; eine `.emf` aus ChemDraw gibt eine scharfe Vorschau).
  **Mengenprüfung:** „(1.03 g, 5.00 mmol, 1.0 eq.)“ und Ausbeuten in der Vorschrift werden mit der
  Reagenzientabelle verglichen, unter Berücksichtigung der Rundung der angegebenen Stellen. Reagenzientabelle aus dem
  Schema (Edukte, Reagenzien über/unter dem Pfeil wie K2CO3, Lösungsmittel, Produkt).
- **NMR-Tab:** SVG-Exporte aus MestReNova; Kern aus der Achsenbeschriftung (oder von Hand), Reihenfolge ¹H, ¹³C,
  übrige Kerne nach Massenzahl, dann 2D (HSQC, HMBC …). Mnova-Multiplettbericht → NMR-Zeile im Stil der SI, mit
  Zuordnung je Signal; ¹³C-Zeile auch aus den Peaklabels des Spektrums. Temperatur 298 K oder aus dem Bruker-Ordner
  (acqus) mit Parameterübersicht. Die Struktur wird automatisch an eine freie Stelle gesetzt (keine Signale, Labels oder
  Integrale verdeckt), lässt sich ziehen, und ihre Größe (Mausrad) ist in allen Spektren gleich. Word: zwei Spektren je
  Seite, „Figure Sn: ¹H NMR (500 MHz, CDCl₃, 298 K) of **Name**.“
- **SI (Word) mit allen Abbildungen:** UV-Vis (ε), IR, HR-MS, Overlay, Fluoreszenz, CV, SEC, EPR und NMR – immer zwei je
  Seite (falls nötig verkleinert), mit Unterschriften im Stil der SI. CV, SEC und EPR füllen ihre Unterschrift aus den
  Daten (Vorschub, iR-Kompensation, Referenz, Potentialbereich, Band, g und Kopplungen) und wenigen Feldern
  (Konzentration, Lösungsmittel, Leitsalz, Spezies). UV-Vis: „… in THF, measured in 0.1 cm quartz cuvettes.“
- **Aufbau-Text (SI)** je Tab (CV, SEC, EPR): den Absatz zu Gerät und Aufbau einmal einfügen; er wird nur auf dem
  eigenen Rechner gespeichert und vor die Abbildungen dieses Tabs gesetzt.
- **Schrift und Rahmen je Tab:** Format → „Schrift und Rahmen…“ gilt für alle Tabs oder nur den offenen und zeigt nur,
  was dieser Tab im Bild hat.
- Strukturen ohne ChemDraw-Export werden jetzt **aus den CDXML-Koordinaten gezeichnet** (Abkürzungen wie TMS oder Dipp
  bleiben, Pfeile und Bedingungen im Schema); RDKit nur noch als Rückfall.

### Geändert
- Neues App-Icon (Spektrum in den Farben des sichtbaren Bereichs mit Blitz) und neue Kurzbeschreibung „Von der Synthese zur SI“.
- Reihenfolge der Tabs wie in der SI: Synthese · NMR · IR + EA · HRMS · UV-Vis (ε) · Overlay · Fluoreszenz · CV · SEC ·
  EPR · X-Ray · DFT. Der offene Tab wird über seinen Namen gemerkt.
- Geschlossener Rahmen um den Plot ist jetzt Standard (wie in den Origin-Abbildungen der SI); bestehende Projekte
  behalten ihre Einstellung.
- UV-Vis (ε): Feld für das Lösungsmittel unter „Auswertung“ (neben der Schichtdicke).

### Behoben
- Word-Dateien öffnen nicht mehr im Kompatibilitätsmodus.

## 1.23.0 – 22.10.2026

### Neu
- **Tab DFT:** xyz-Dateien und Ausgaben von **ORCA 6** und **Gaussian** laden (UTF-16-Dateien aus einer
  PowerShell-Umleitung werden erkannt); drehbare Abbildung im Stil des X-Ray-Tabs.
- DFT: **Atome per Klick umnummerieren** in der gewünschten Reihenfolge; die übrigen Atome behalten ihre Reihenfolge
  (wahlweise H direkt hinter ihrem Atom). Gespeichert wird eine neue xyz mit unveränderten Zeilen (nur umsortiert, alle
  Bilder einer Trajektorie); Zählung ab 0 wie ORCA wählbar.
- DFT: **wie Vorlage nummerieren** – Nummerierung einer anderen Geometrie oder einer Kristallstruktur aus dem X-Ray-Tab
  übernehmen (dann mit den Atomnamen der CIF). Zuordnung über das Bindungsnetz, bei symmetrischen Molekülen nach der
  Geometrie; gleichwertige Zuordnungen werden gemeldet, nie still gewählt.
- DFT: **SI-Block** je Rechnung wie in der SI der Gruppe: Name, Abbildung, Ladung/Multiplizität/Punktgruppe,
  kartesische Koordinaten, Tabelle E_el/H/G (ZPE optional); Methodenzeile (je Struktur oder einmal als „Computational
  details“), Konvergenztabelle und Frequenzergebnis schaltbar. Werte exakt wie in der Ausgabe. Warnungen bei
  abgebrochenen Rechnungen, nicht konvergierter Optimierung und imaginären Frequenzen. Word-Datei zweispaltig.
- Knopf **SI (Word)** in der Werkzeugleiste: Teile des SI-Abschnitts wählbar (Charakterisierung, X-Ray, DFT).
- Labelgröße im X-Ray- und DFT-Tab einstellbar.
- SI-Texte (Word und Kopieren) mit **geschützten Leerzeichen** zwischen Zahl und Einheit, um „=“ und „±“, in
  zusammengesetzten Einheiten und in der Elementaranalyse.

### Behoben
- X-Ray: SI-Abbildungen ohne Labels wurden am Rand abgeschnitten.

## 1.22.1 – 22.10.2026

### Behoben
- CV-Basislinie: endet jetzt auch vor dem Anstieg der Welle (2 % der Peakhöhe). Bei breiten Wellen (iR-Abfall,
  ΔE_p > 100 mV, z. B. in THF) lag sie vorher im Fuß der Welle und hat i_pa um bis zu 36 % zu klein gemacht.
- CV: kein Nicholson-Verhältnis mehr, wenn zwischen Hinpeak und Umkehrpotential ein weiterer Prozess liegt (z. B.
  Ac₂Fc oder eine zweite Welle) – die Formel gilt dann nicht; Anzeige „–“, nicht im i_r/i_f-Plot.
- CV: E½ im Bild je Gruppe (vorher über alle Gruppen, z. B. Lösungsmittel, gemittelt).
- SI-Text: Scanraten gerundet (Gamry speichert z. B. 499,999 mV/s).

## 1.22.0 – 21.10.2026

### Neu
- CV: **Basislinienkorrektur** der Peakströme (Standard an): Gerade durch den Strom vor dem Hinpeak, für den Rückpeak um
  den Ladestromsprung am Umkehrpunkt verschoben; Nicholson-Verhältnis aus den korrigierten Strömen. Basislinien optional
  im Bild.
- CV: neue Auftragungen **log i_p gegen log v** (Diffusion/Adsorption) und **i_r/i_f gegen v** (chemische Reversibilität).
- CV: Regressionen gegen die Scanrate mit **95-%-Konfidenzintervall** für Steigung und Achsenabschnitt.
- **SI-Text kopieren** in allen Tabs, die fitten (UV-Vis (ε), CV, SEC, EPR): englischer Methodenabsatz mit genau den
  benutzten Auswerteschritten und Einstellungen, danach die Ergebnisse; beim Export als `…_methods.txt`.

### Geändert
- CV: i_pa, i_pc und i_r/i_f ändern sich in bestehenden Projekten durch die Basislinie (abschaltbar); Peakpotentiale
  und E½ bleiben gleich. Die Ergebniszeile wertet jetzt je Gruppe aus (vorher wurden Gruppen, z. B. Lösungsmittel,
  in einer Randles-Ševčík-Regression gemischt).
- CV-Ergebnistabelle: Spalte „i_r/i_f“ statt „i_pc/i_pa“ (Rück-/Hinpeak, auch bei kathodischem Start richtig benannt).

## 1.21.0 – 21.10.2026

### Neu
- Neuer Tab **HRMS** (MS-Teil des bisherigen Tabs IR + MS): mit Bruker-Rohdaten ein Chromatogramm (TIC und Ionenstrom)
  mit per Ziehen wählbarem Bereich, das gemittelte Spektrum über den LC-Bereich, Peak per Klick als *found* und das
  berechnete Isotopenmuster des Ions (gespiegelt) mit gemessenen/berechneten Isotopenverhältnissen.
- X-Ray **Ausrichten**: Bindung (erstes → zweites Atom) nach unten/oben/links/rechts, Ebene durch ≥ 3 Atome von vorn,
  Drehen in Schritten um x/y/z, Ansicht von hinten und **Ausrichten wie eine ChemDraw-Zeichnung** (CDXML der Verbindung
  des Projekts; Zuordnung über Elemente und Verknüpfung).

### Geändert
- Der Tab IR + MS + EA heißt jetzt **IR + EA**; alte Projekte übernehmen ihre MS-Daten in den Tab HRMS.

## 1.20.0 – 21.10.2026

### Neu
- **Elementaranalyse** im jetzt **IR + MS + EA** genannten Tab: berechnet aus der Formel des Projekts (optional mit
  Solvat wie 0.5 CH2Cl2), gefundene Werte eingeben, Abweichungen > 0.4 % markiert; Zeile für die SI.
- **UV-Vis-Zeile für die SI** (Seite *SI-Zeile* im ε-Tab, optional mit Lösungsmittel): λmax mit ε wie im Bild,
  aufsteigend.
- **Datei → SI-Abschnitt exportieren (Word)**: Charakterisierungsabsatz (m.p.; IR; HR-MS; UV-Vis; Elementaranalyse)
  plus X-Ray-Teil als .docx im Layout der SI der Gruppe (Arial 11, 1.5-zeilig; ORTEP-Abbildung als Vektorgrafik,
  beschnitten; „Figure Sn: X-ray solid state structure of …“ mit Besetzung fehlgeordneter Teile; ausgewählte Parameter in
  der Unterschrift oder ab 9 Werten als „Table Sn: Selected bond lengths/angles for …“; Kristalldaten-Tabelle mit den
  Spaltenbreiten der SI; Nummern als Word-Felder).
- Schmelzpunkt unter **Verbindung …**.

### Geändert
- Tabs umbenannt: **UV-Vis (ε)** (vorher ε-Auswertung) und **UV-Vis-Overlay** (vorher Overlay).
- X-Ray: Bildunterschrift und Beschriftung der Kristalldaten im Stil der SI („Thermal ellipsoids are shown with 50%
  probability“, „*a* / Å“); ausgewählte Parameter in der Atomreihenfolge der CIF.

### Behoben
- X-Ray: Labels berühren keine Bindungen mehr (genaue Kollisionsprüfung); gespeicherte Label-Positionen, die nach dem
  Drehen auf einer Bindung oder einem Atom liegen, werden neu platziert.

## 1.19.0 – 21.10.2026

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
