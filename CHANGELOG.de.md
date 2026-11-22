[English](CHANGELOG.md) | **Deutsch**

# Änderungen

## 1.4.0 – 2026-11-22

### Neu

#### Abbildungen und Beschriftungen
- **Beschriftungen im Bild in jedem Tab mit Abbildung** (UV-Vis, Fluoreszenz, HRMS, IR, CV, SEC, H-Cell, EPR, TD-DFT,
  Kinetik, Vergleichsstapel): eigener Text, Ausblenden und Zurücksetzen je Label (Karte und Rechtsklickmenü). **Eigene
  Zusatzlabels:** Rechtsklick auf eine freie Stelle, **Label hier einfügen**; ziehen, ausblenden, entfernen
  (**Eigene Labels entfernen**). Nie in Unterschriften oder Methodentexten.

#### Export und Tabellen
- **Tabellen je Tab:** ein CSV-Format (Komma, Dezimalpunkt, UTF-8, Köpfe „Name [Einheit]“, Rohwerte), eine Mappe
  `<Verbindung>_<Tab>_tables.xlsx` mit den Zahlen vom Bildschirm als Zahlenzellen, **Kopieren** an jeder Ergebnistabelle
  (Word und Excel).
- **Tab „Export“:** eine Karte je Abbildung und Tabelle; die Auswahl steuert **Bilder**, **Tabellen**, **PPTX** und
  **SI (Word)** über vier gleich große Knöpfe; **Alle**/**Keine**; ausgegraute Knöpfe nennen den Grund. **Alles
  exportieren** schreibt auch Tabellen.
- **Beispielprojekt** wird einmal je Version angelegt: erneutes Öffnen dauert etwa 0,2 s statt 19 s; der erste Aufbau zeigt den Fortschritt.

#### NMR
- **Vergleich eigener 1D-Spektren** (ein Kern, ein Lösungsmittel): **Einzeln**, **Überlagert** oder **Gestapelt**; mit
  Vergleichsunterkapitel in der SI exportierbar. Unterschrift mit Temperaturbereich und freiem Satz; zurückgehalten, bis
  Phase und Referenz jeder Spur bestätigt sind.
- **Octet-Vorhersage als Spur** auf Klick (nur Ansicht, nie in einer Ausgabe); Automatikbereich ¹H 9..0, ¹³C 200..0,
  erweitert um die Signale.
- Beispielprojekt: erfundene Temperaturreihe in S3.

#### HRMS
- **PDF-Berichte:** Bruker-SmartFormula-Layout wird automatisch gelesen (found aus dem Bericht, calc immer hier gerechnet,
  Warnung bei abweichendem calc des Berichts, Spektrenbild des Geräts wählbar); Kopfdaten (Pfad, Bediener, Probe) werden nie übernommen.
- **Unbekannte PDFs:** Kandidatenliste (Zeile, ppm gegen calc), nichts vorgewählt, Übernahme per Klick; **Texterkennung
  (OCR)** für Scans, auch für IR-Peakwerte. Feld für found von Hand immer verfügbar.
- **Mehr Addukte** (MeOH, MeCN, H2O, 2M, 2+, Formiat) und ein freies eigenes Ion.
- **Fremdpeaks und Reagenzien:** Hinweise auf Peaks, die zu bekannten Fremd-Ionen, Reagenzien oder Bruchstücken passen
  (5 ppm, einstellbar); nur am Bildschirm, nie in SI oder Exporten; **Eigene Fremdpeaks** je Rechner.

#### CV
- **Referenz per Klick:** Spalte Fc, **Referenz setzen** rastet auf die Peaks des Standards ein (Esc bricht ab); die
  Struktur des Standards steht über seiner Welle, in der Farbe der Referenzmessung oder schwarz.
- **D und k0 je Paar** in eigener Tabelle; k0 erst ab drei Vorschüben, als Bereich aus dEp, ohne iR-Kompensation als
  scheinbar gekennzeichnet; D nur für reversible Paare; neue `<name>_rate_fits.csv`.
- Abgelegte `.DTA`-Dateien werden nach Inhalt zugeordnet: Gamry-CV zu CV, zyklisches Laden/Entladen zu H-Cell, Bruker BES3T zu EPR.

#### Oberfläche
- **Rücksetzmenü der Tabs: Tab leeren (Daten und Einstellungen)** in jedem Tab (ein Rückgängig-Schritt, Dateien bleiben im Ordner; die Verbindung behält ihren Namen, ihre Zeichnungsdatei bleibt unverändert).
- **Menü Format, Oberflächengröße** 100/110/125/150 % je Rechner; **Jetzt neu starten** öffnet dieselbe Verbindung und denselben Tab oder die Projektseite wieder.

#### Strukturen und Salze
- **Gegenionen:** gängige Abkürzungen werden in Labels und Formeln aufgelöst (PF6, SbF6, AsF6, BF4, ClO4, OTf, NTf2,
  BArF, BPh4, OAc, NO3, HSO4, I3, SO4, N3); die Ladung wird aus dem Label gelesen (einstellige Ladung nur an einem
  einatomigen Ion wie Fe2+, „SO4 2-“ mit Leerzeichen). Mehrdeutige Labels wie SO42- und unausgeglichene Ladungen
  bekommen einen Hinweis statt einer Vermutung.
- **HRMS, Ion des Salzes:** Kation [M]+, Anion [M]- oder 2+/2-; Vorgabe ist der kohlenstoffhaltige Teil, Projekte mit
  ausgewertetem Bericht behalten das ganze Salz.
- **ChemDraw-Import:** aus ChemDraw eingefügte Ringe behalten ihre Doppelbindungen innen; ein Minus steht so hoch wie ein Plus.
- **Octet und eigener Strukturzeichner:** Doppelbindungen in Ringen beliebiger Größe (auch Makrozyklen) liegen innen; mittige Doppelbindungslinien (z. B. C=O) laufen bis zur Achse der Nachbarbindung.

### Geändert
- **Wechsel hell/dunkel** färbt das offene Fenster an Ort und Stelle um, statt es neu aufzubauen, und ist dadurch schneller.
- **Oberflächendurchsicht:** Tabellen, Listen und Bäume mit runden Ecken wie die Felder; die Tab-Leiste wird erst
  enger, dann geschoben (passt bei 1200 px); Meldungen stehen einzeilig in der Fußleiste („Details“ wächst nach oben);
  Ergebnistabellen ziehen erst die Zellen zusammen, dann zweizeilige Köpfe, bevor sie seitwärts scrollen; leere
  Spalten ohne Eingabe sind am Bildschirm verborgen (Dateien behalten sie); HRMS-Rohdaten und Isotope als Tabellen.
- Methodentexte und Unterschriften setzen Größen in Word und Vorschau kursiv; IR-/Raman-Peaks überall ganzzahlig.
- Einheitliche Großschreibung bei Chips, Platzhaltern, Tabellenköpfen, Hinweisen, Auswahlpunkten und Zellwerten (Symbole, Einheiten und Abkürzungen bleiben); Synthese-Spaltenkopf „eq. / %“; Schreibweise „MNova“.
- Export-Kacheln: Namen in zwei Zeilen, Symbole an die Vorschaufläche angepasst; DFT-Multireferenz-Auswertung als Karte in der linken Spalte; Abstände auf der Detailseite; einzelne Farbfelder.
- Linke Spalte in jedem Tab gleich breit; NMR-Aufnahmeparameter als Tabelle; Atomlabels in X-Ray/DFT halten Abstand;
  Labelabstände in UV-Vis/CV wachsen mit der Labelschrift.
- IR: eine PDF gilt nur an ihrem Layout als OPUS-Ausdruck; andere PDFs bieten ihre Werte als Kandidaten an.
- HRMS-Abbildungsseite: ein Satz statt der Anleitung, wenn ein Bericht oder Rohdaten kein Spektrum haben.
- CV: Zwei-Wellen-Schutz: ein Fenster mit zwei Paaren wird wie ein Randpeak markiert; vorgeschlagene Fenster enden auf halbem Weg zur Nachbarwelle.
- Tabellen nehmen weniger Zellrand, bevor sie seitwärts scrollen; kein fetter Kopf bei Auswahl.
- Beim Schließen oder Anlegen einer Verbindung werden verborgene Tabs zu Platzhaltern statt neu gebaut.
- CV: reine Referenzmessungen verlassen die Vorschubanalyse; Pfeil der Messrichtung oben links.
- Ergebnisseiten: die UV-Vis-Ergebnistabelle steht oben, **Kopieren** in ihrer Titelzeile; X-Ray-Tabellen stapeln sich
  bei schmalem Fenster; DFT-Energietabellen teilen die Namensspalte; Dateilisten so hoch wie ihre Zeilen.
- Schreibweise: „arb. u.“ für willkürliche Einheiten in Abbildungen, schmale Leerzeichen in n × Kern, Fc⁰/⁺ überall
  gleich, englische Texte mit -ize; die Wellenlänge des Raman-Lasers erscheint ganzzahlig.

### Behoben
- UV-Vis-Tab blieb nach dem Wechsel hell/dunkel leer.
- Octet: eine leere Zeichnung löscht Strukturdatei, Formel und Masse, statt „keine Struktur gefunden“ zu melden.
- „Alles zurücksetzen“ in der Label-Karte brachte den alten Text zurück; der IR-Tab verlor die Werte der Elementaranalyse (EA-Satz fehlte in der SI).
- Titelleiste über dem Bildschirmrand bei 150 % Skalierung (Startgeometrie begrenzt).
- MNova-SVGs mit „MS Shell Dlg 2“ oder ohne Schriftfamilie erscheinen in PDF und Word mit Arial.
- Dunkle Zeichenfläche: keine weißlichen dunklen Blau-/Grüntöne; Absturz beim Beenden durch WebEngine-Seiten; Absturz beim Beenden durch die Zwischenablage.
- Eigene NBO-Unterschriften und Dateinamen bei zwei Rechnungen; E1/2-Mittel in Abbildung und Methodentext gleich.
- Linke Spalte behält ihre Scrollposition nach dem Neuaufbau auch bei langsamem ersten Zeichnen.
- Absturz beim Zeichnen von Strukturen, die RDKit nicht bereinigen kann; Import scheiterte, wenn die Verbindung über einen Symlink geöffnet war.
- Breite Schriften (Windows): Fußleistenmeldung, NMR-Parameterspalte und gesetzte Zellen kürzen sauber.
- CV-Methodentext war in seiner Karte abgeschnitten; 3D-Atomlabels im Reaktionspfad überlappten; Namen der Export-Kacheln liefen unter Linux über ihre Karte.

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
