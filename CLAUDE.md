# CLAUDE.md – Elucida (früher Spectravolt, davor UVVisTool)

PySide6-Desktop-App (Windows wichtigste Plattform, dazu macOS arm64, macOS Intel ab 14 und Linux) für UV-Vis-Verdünnungsreihen:
Lambert-Beer-Auswertung (ε bzw. a) und Abbildung im Origin-Stil (Spektren, λ/ε-Labels, Inset mit Regression
und Tabelle, ChemDraw-Struktur, Küvettenfoto). Dazu Tabs für Synthese (Schema, Vorschrift, Mengenprüfung), NMR (Mnova-SVG), IR + EA, HRMS, Overlay (gemessen + TD-DFT),
Fluoreszenz, CV, SEC, EPR, X-Ray (CIF) und DFT (xyz); SI-Abschnitt als Word-Datei.
Öffentliches Repo, AGPL-3.0. Maintainer: Robin (Chemiker, kein Softwareentwickler; Git-Einsteiger).

## Zusammenarbeit
- Antworten auf Deutsch, direkt und technisch präzise. Aussagen mit [Certain]/[Likely]/[Guessing] kennzeichnen.
- Keine Zustimmungsfloskeln. Wenn ein Wunsch fachlich fragwürdig ist (z. B. Statistik), das zuerst sagen,
  dann umsetzen.
- Git-Schritte (commit, tag, push, Release) kurz erklären und vor dem Push bestätigen lassen.
- Testdaten des Nutzers sind unveröffentlicht oder gehören Studierenden: **nie** CSV/DSW/BSW/HEIC/CDXML/ORCA-Ausgaben
  committen (siehe `.gitignore`). Keine Probennummern, Verbindungsnamen, Messwerte unveröffentlichter Arbeiten oder
  Namen von Mitarbeitenden in README/CHANGELOG/CLAUDE.md/Code (öffentliches Repo).

## Fachliche Regeln (nicht ändern ohne Rückfrage)
- ε (M⁻¹ cm⁻¹) **nie mit Nachkommastellen** anzeigen; Rundung auf die Genauigkeit des Standardfehlers
  (`core.fmt_ve`, `eps_max_decimals`). Sehr kleine Fehler auf 1 Einheit aufrunden, nie „± 0“.
- Fit: A/d = m·c + b (OLS); ε = m / f_c (f_c: mM 1e-3, µM 1e-6, M 1; mg/mL über die Molmasse; ohne Molmasse
  spezifischer Koeffizient a in L g⁻¹ cm⁻¹). 95-%-KI = t(0,975; n−2)·SE (eigene `t_quantile`).
- Cutoff global (Standard A = 1) und pro Bande; Banden mit R² < `min_r2` (einstellbar, Standard 0,98) stehen in
  Tabelle/CSV/Excel, aber nicht im Bild. Bei 4 Punkten ist R² wenig aussagekräftig, KI zählt.
- Konzentrationsdialog: **keine** vorbelegte Einheit/Startkonzentration (führte früher zu falschem ε).
- ChemDraw-Struktur **unverändert** übernehmen: gleichnamige SVG/PDF/PNG neben der CDXML hat Vorrang; sonst eigene
  Zeichnung aus den CDXML-Koordinaten (`uvvis_cdxml`, Abkürzungen wie TMS/Dipp bleiben, Pfeile und Texte im Schema);
  RDKit (ACS1996-Modus, keine eigene Bindungslänge) nur, wenn der Zeichner etwas nicht darstellen kann (Hinweise) –
  im Syntheseschema nie (Pfeil/Bedingungen gingen verloren), dort Warnung. Bilder behalten immer ihr Seitenverhältnis
  (gespeichert wird nur die Breite).
- „(sh)“ für Schultern ist abschaltbar; Indizes λ₁/ε₁ … (`label_index`, Standard aus, aufsteigend nach λ, nur Banden
  im Bild; SI-Zeile ohne Indizes); Molmasse aus CDXML inkl. Isotopen.
- TD-DFT: Gauß-Verbreiterung in Energie; Kurve und Sticks teilen **immer einen** Skalierungsfaktor
  (Modi `band` Standard, `max`, `faxis`). ORCA 5/6-Zustandslabels („0-1A -> 1-1A“) nach „->“ splitten; SOC-Tabelle.
  Multiplizität aus dem Label („1-3A“ = Triplett), ORCA 4/5 aus dem TRIPLETS-Block, Gaussian aus „Triplet-A“;
  Tripletts (f = 0) nur als Marken, nie in der Gauß-Kurve; mit SOC keine Multiplizität (gemischte Zustände).
  Kombinieren: Übergänge mehrerer Rechnungen (`sources`, je Gewicht) erst zusammenführen, dann verbreitern.
  Lösungsfarbe aus TD-DFT (Overlay-Details, `calc_color`): ε mit FWHM/Verschiebung des Eintrags, A = ε·c·d, Standard
  1 mM, 1 cm (`color_c`/`color_d`); nur qualitativ.
- CV: Strom wie aufgezeichnet (Gamry IUPAC, anodisch positiv); Paare nur im Fenster (gespeichert in gemessenen
  Potentialen, angezeigt in Achsenskala); i_pc/i_pa nach Nicholson; Referenz E_Fc = E − (E½,ref − E°ref);
  Basislinie (Standard an): Gerade durch den Vorlauf des Hinpeaks (bis 0,15 V davor **und** vor dem Anstieg der Welle,
  2 % der Peakhöhe – sonst überkorrigiert sie breite Wellen, echte THF-Daten), Rückbasislinie = dieselbe minus
  Ladestromsprung am Umkehrpunkt (2·C·v); Nicholson auf die korrigierten Ströme, **keine** zusätzliche extrapolierte
  Rückbasislinie (doppelt korrigiert); Peakpotentiale aus dem Rohstrom. Regressionen gegen v je Gruppe, mit 95-%-KI.
  Nicholson nur ohne weiteren Prozess zwischen Hinpeak und Umkehrpotential (Strom steigt um > 10 % der Peakhöhe wieder
  an → „–“). E½ im Bild und alle Mittelwerte je Gruppe, nie über Lösungsmittel gemittelt.
  Ac₂Fc-Vorgabe +0,49 V vs. Fc⁺/Fc (ergibt die publizierten −1,10 V für 6m), immer änderbar lassen.
- SEC-Farben wie die SI: Start blau, Zwischenstufen (`mid`, Potential in Achsenskala → nächstes gezeigtes Spektrum, ohne
  Potentiale Nummer) grün/`MID_COLORS`, Ende rot; Unterschrift nennt nur Farben, die im Bild vorkommen (`cap_mid`, „;“).
- SEC: Nernst-Fit aus kontinuierlichem Scan nur als „scheinbar“ ausweisen (Nachhinken in der Dünnschichtzelle:
  6m in THF E½ ≈ −0,76 V statt −0,89 V im CV, n ≈ 0,45); CV-Werte haben Vorrang.
- EPR: Reihenfolge hell − k·dunkel → Basislinie → Ausblenden → Glätten → Normieren; Simulation mit dem
  Normierungsfaktor ihrer Messung (Verhältnis bleibt). Triplett-Simulation nicht selbst rechnen (EasySpin), nur
  importieren. Projekte kopieren BES3T-Partnerdateien (.dsc/.DTA/.YGF/.xml) mit.
- EPR S = ½: nur isotrop, erste Ordnung; Fit = Grobsuche (Lage, Kopplungsfaktor) + LM; Amplitude linear. Mehrere
  Komponenten je Messung immer gemeinsam linear skalieren. Kalibrierung: ΔB = B(g_fit, ν_ref) − B(g_lit, ν_ref),
  von allen Messungen außer der Referenz abziehen (MS400-Beispiel: +3,41 mT, 6m•+ danach g ≈ 2,0026).
- EPR-Zerfall (Nachbau des MATLAB-Skripts der Arbeitsgruppe): Gauß+Gerade, Zentrum nur innerhalb der Messpunkte (sonst beliebige
  Amplitude bei Spektren ohne Signal); Min-Max-Normierung; Fit-Start per Raster über E_a mit ln A aus T₅₀ (direkter
  Start scheitert an der Korrelation ≈ 1). Standard: kleinste Quadrate (belastbares Intervall, t-Quantil); „wie Skript“
  (√|r|) nur zum Vergleich – hängt stark vom Optimierer und von Spektren ohne Signal ab.
- Export: Standard 16 × 11 cm (halbe A4-Seite in Word, zwei Abbildungen pro Seite), minimale Ränder; PDF/SVG
  vektoriell, Text in SVG als Pfade. Exporte überschreiben im Projektordner unter `exports/…`.
- HRMS: calc. = monoisotopisch **mit Elektronenmasse** ([M+H]⁺ = M + 1.007276), calc./found immer 4 Nachkommastellen;
  ppm zur Kontrolle als found − calc (die Massenabteilung gibt das umgekehrte Vorzeichen an). IR: ganze Zahlen,
  absteigend; Bereich standardmäßig der ganze gemessene; mit OPUS-PDF gelten dessen Peakwerte.
- HRMS-Tab (seit 1.21) und IR + EA getrennt; `irms`-Zustand alter Projekte: MS-Schlüssel nach `hrms` übernehmen (set_state).
  Spektrum = Linienspektren (Centroide), keine Profilkurve; Isotopenmuster nur zum Vergleich, found bleibt gemessen.
- X-Ray ausrichten: Bildkoordinaten x rechts, y oben, z zum Betrachter; Bindung/Ebene über kleinste Drehung
  (`rot_between`); ChemDraw-Vorlage: RDKit-CDXML (y bereits nach oben), Schweratome, Graph-Abgleich (sonst MCS ≥ 60 %),
  Kabsch auf die 2D-Koordinaten; mehrdeutige Zuordnung melden statt still wählen.
- HRMS aus Bruker-.d (BAF): nur Linienspektren (MS1, ohne Steps); m/z aus Transformator-Blob (Variante int 10,
  112 B): t = Delay + Takt·Index, t = c0 + √(1e12·m'/c1) + c2·m' (Newton), m/z = m' − c6. Geprüft gegen CompassXport
  (eine Messung, alle Peaks auf 4 Nachkommastellen). Unbekannte Varianten **ablehnen**, nicht raten. found = mit der
  Intensität gewichtetes Mittel über den LC-Peak (≥ 50 % des Maximums, zusammenhängend, ± 10 ppm um calc.); Streuung
  immer mit anzeigen. Bericht der Massenabteilung bleibt vorgewählt.
- X-Ray: Standardabweichungen **nur aus der CIF** (`_geom_bond/_angle/_torsion`, Text unverändert, z. B. „1.392(3)“),
  **nie schätzen**; fehlt ein Wert, selbst rechnen und ohne esd markieren (Torsion: Hinweis „CONF setzen“).
  Symmetrie: Molekül über Bindungen × Symmetrieoperationen vervollständigen; Abgleich mit geom-Einträgen über
  Transformationen (gesucht G mit T_k = G∘S_k, auch rückwärts), Codes `n_klm` (555 = keine Translation, „n“ allein
  ebenso). Erzeugte Atome mit römischer Hochzahl je Operation + Fußnote. Fehlordnung Standard: PART 0 + je
  `disorder_assembly` der Teil mit der größten Besetzung. Ellipsoide: k = √χ²₃(p) (50 % → 1.5382), Umriss = 2×2-Block
  von R·U·Rᵀ. Aussehen Standard **wie Mercury** (Nutzerwunsch): schattierte Schichten (`shade_layers`, Licht oben
  links, matt, Schichten immer innerhalb des Umrisses, keine Clip-Pfade), H-Radius 0.09 Å, Bindungsdicke in Å
  (`bond_w`, Standard 0.12 seit 2.0, skaliert mit dem Zoom wie Mercurys Zylinder); seit 2.0 nach Nutzervorlage
  Bindungen schwarz, Labels fett ohne Rand – Elementfarben bleiben (C grau, Nutzerwunsch); „flach“ = Olex2 (fett,
  weißer Rand). Kugel-Stil (`BALL_STYLES`, nach Vorlagebildern des Nutzers): „ballstick“ wie IboView (Schattenrand unten
  rechts, Glanzpunkt, feiner Umriss, dünne Stäbe 0.2 Å mit Glanzstreifen zur Lichtseite), „depth“ matt mit dicken Stäben
  (0.36 Å) und Aufhellung nach hinten (`DEPTH_A` = 6 Å bis `DEPTH_MAX`). Schattierung = Phong (`SHADE`, an die
  IboView-Vorlage gefittet: Licht 40° über der Bildebene aus `LIGHT`, ka/kd aus der C-Kugel, Glanz schwach und eng,
  damit nur die Mitte weiß wird; Kugeln ohne Umriss, nur die Stäbe mit feinem Rand); Kugelschichten = Höhenlinien (`sphere_unit_layers`, contourpy, gecacht), Stäbe =
  Zylinderprofil je Lage zum Licht (`rod_layouts`, vektorisiert, bei jeder Drehung neu; exakt, kein Winkelraster). Schnelles Drehen: Stabschichten je Atom eine LineCollection auf einem gemeinsamen Puffer (`_place_rods`), Kugeln = Einheitspolygone + Transform (`sphere_tr`); nur während des Ziehens vereinfachte Kugelpolygone (`set_drag`, ≤ `DRAG_TOL_PX`), Ruhebild und Export pixelgleich zur Einzellinien-Version. Stäbe von Mitte zu Mitte, jede Hälfte direkt
  unter ihrem Atom (`atom_rods`, `_zorders`); Radius `ball_radius(el, style)` (Faktor × kovalent, H ≥ 0.2 Å); `bond_w`
  wirkt dort relativ: Stabdicke = `ROD_W` × bond_w/Standard des Tabs, im DFT-Tab Kugelradius × radius/0.25
  (`rod_scale`/`ball_scale`; Standardwerte = abgenommenes Aussehen). Hintergrund je Tab (`bg`: white/transparent/#hex,
  `BackgroundCombo`, `bg_parts`; Vorschau bei transparent weiß, Label-Ränder in Hintergrundfarbe). Messen/Ausrichten gemeinsam für X-Ray und DFT (`MeasureAlign`;
  DFT: `MEASURE_ESD = False`, Klick = Auswahl, im Nummerier-Modus = Nummer).
  Labels/Atome je Atom über `label_on`/`hidden_atoms` (Schlüssel Label|Operation). Tabellen englisch beschriftet, Zahlen exakt wie in der CIF, echtes Minus (U+2212).
  Drahtmodell (`wire`, Atom-Schlüssel): Bindung → kleinere Seite (`Molecule.substituent`), in Ringen das Ringsystem hinter
  dem ersten Atom (`beyond`, höchstens halbes Fragment); H daran nur mit `wire_h`. Fragmentart über die Summenformel
  (`SOLVENTS`/`IONS`, auch ohne H); gleiche Schweratomformel wie das Hauptmolekül = Z′ > 1, nie automatisch ausblenden.
  Ausblenden/Drahtmodell ändern nur das Bild, nie Tabellen oder Messwerte; die Bildunterschrift (`caption`) folgt dem Bild.
- DFT-Tab (xyz): Ansicht über `XyzMolecule` mit der X-Ray-Schnittstelle (`XrayFigure`/`XrayMouse`), Startansicht
  **mit** H (jedes Atom muss anklickbar sein). Umnummerieren: angeklickte Atome der Reihe nach vorn, Rest in bisheriger
  Reihenfolge (optional H hinter ihr Atom); gespeichert als `order` (Dateiindizes), Atom-Schlüssel `a<Index>` bleibt.
  xyz-Zeilen beim Speichern **unverändert** (nur umsortiert, alle Bilder einer Trajektorie), geladene Datei nie
  überschreiben. Anzeige ab 1, optional ab 0 (ORCA).
- DFT-Rechnungen (SI-Block): nur ORCA 6 (geprüft mit 6.1.1), ORCA 5 bewusst nicht; Gaussian (siehe unten).
  Kodierung erkennen (PowerShell-Umleitung schreibt UTF-16). Alle Werte **als Text wie in der Ausgabe** (keine Rundung),
  echtes Minus. Eingabezeile(n) „!“ aus dem ersten INPUT FILE; Ladung/Multiplizität aus „Total Charge/Multiplicity ....“;
  letzte Konvergenztabelle unverändert (auch „NO“ bei übererfüllter Konvergenz, dazu Hinweis); letzte Koordinaten;
  Frequenzen + Thermochemie (E(el), ZPE, H, G mit T/p/qRRHO). CPCM: nur „CPCM Dielectric“ (in E(el) enthalten) –
  **nie** als Solvatationsenergie ausgeben (ΔG_solv braucht die Gasphasenrechnung). Warnungen (abgebrochen, nicht
  konvergiert, imaginäre Frequenzen, Thermochemie fehlt) nur in der Anzeige, nicht im SI-Text. Koordinaten im SI-Text
  in der aktuellen Nummerierung; Abbildungen in Export/Word standardmäßig ohne Labels (`export_labels`).
  Layout nach der Beispiel-SI der Gruppe: Word zweispaltig; Name fett, Bild, „Charge: … Multiplicity: … Point group: …“
  (Tabstopps, Punktgruppe kursiv mit tiefgestelltem Rest), Koordinaten in Courier (Größe passt die längste Zeile in
  die Spalte), Energietabelle E_el/H/G. Methode, Konvergenz, Frequenzen zusätzlich (Wunsch), je abschaltbar (`si_*`).
  Gleichnamige xyz neben der .out (ORCA, 14 Stellen) wird mitkopiert und nur benutzt, wenn sie zur Endgeometrie passt.
  Energietabelle E_el/H/G, ZPE-Spalte schaltbar (Standard aus; U bewusst nicht – für Aussagen zählen ΔH/ΔG). G gilt für
  1 atm (Standardzustand nicht umrechnen, Bedingungen stehen im Text). Methode: je Struktur (Standard) / einmal oben als
  „Computational details“ (je verschiedene Eingabezeile, bei mehreren mit den Strukturen) / aus. Imaginäre Frequenzen
  nur melden, nie bewerten. Gaussian geprüft mit einer echten Opt+Freq/SMD-Ausgabe (G16 C.01; zwei Jobs über „Link1“ –
  normal beendet erst, wenn der letzte Job normal endet).
- DFT-Vergleichsmodus („Wie Vorlage“): Vorlage = andere Geometrie des Tabs oder CIF aus dem X-Ray-Tab (Hauptfragment,
  Labels wie `atom_name`). Schweratome über das Bindungsnetz (RDKit-Substruktur, sonst MCS ≥ 80 %), unter mehreren
  Zuordnungen (bis `MATCH_MAX`) die mit der kleinsten Kabsch-Abweichung; Kabsch immer mit echter Drehung, Spiegelung nur
  bei deutlich besserer Passung (ebene Schweratome: sonst H ober-/unterhalb vertauscht). Nächstbeste andere Zuordnung
  immer melden, innerhalb `AMBIG_TOL` (0.05 Å) als mehrdeutig mit den betroffenen Atomen warnen, nie still wählen.
  H über ihr Schweratom und den Abstand nach Überlagerung; Atome ohne Gegenstück ans Ende. CIF-Labels als `ref_labels`
  (Schlüssel Dateiindex) und Labelstil „ref“; Reihenfolge der Datei setzt beides zurück.
- SI-Export (Werkzeugleiste „SI (Word)“ und Menü): Teile wählbar (Charakterisierung, NMR, Abbildungen aller Tabs,
  X-Ray, DFT; Auswahl in QSettings `si_parts`); DFT zweispaltig über fortlaufenden Abschnittswechsel (`("columns", 2)`
  in `write_docx`). Ohne Charakterisierung nur der Name als Überschrift. `settings.xml` mit compatibilityMode 15
  (sonst Kompatibilitätsmodus).
- SI-Abbildungen (Nutzerwunsch): **immer zwei je Seite** (`SI.two_per_page`: Text vor Abbildungen beginnt eine Seite und
  zählt mit; Bilder im Seitenverhältnis verkleinern, bis Bild + Unterschrift passen – 16 × 11 cm mit zweizeiliger
  Unterschrift sind zu zweit zu hoch). Reihenfolge `figure_tabs` (IR, HRMS, ε je Serie, Overlay, Fluoreszenz, CV, SEC,
  EPR). Unterschriften je Tab (`si_caption`): ε „UV-Vis spectra of **X** in THF, measured in 0.1 cm quartz cuvettes.“
  (Lösungsmittel je Serie im Abschnitt Auswertung); CV/SEC/EPR wie die SI der Gruppe aus den Daten (Vorschub,
  iR-Kompensation nur wenn für alle gleich, interne Referenz, Start-/Endpotential, Band aus ν, g/ΔBpp/Kopplungen nur aus
  eigenen S = ½-Fits) plus Felder `cap_*` (`CAP_FIELDS`, Leitsalz gemerkt); `chem_html` stellt Formeln tief, „-1“ hoch.
  Aufbau-Texte (Geräte) nur in QSettings `si_setup/<Tab>` (lokal, nie im Code/Projekt), im Export vor den Abbildungen.
- Geschützte Leerzeichen (`SI.nbsp`, U+00A0) zentral in `write_docx` (Absätze, Unterschriften, Text) und `copy_rich`:
  Zahl ↔ Einheit, um „=“/„±“, in zusammengesetzten Einheiten (cm-1 M-1), Elementaranalyse „C 81.78“, „m.p.“.
  Nicht in Tabellen und Koordinaten (Festbreite). Neue Einheiten in `_UNITS` ergänzen.
- Labelgröße je Tab (`label_pt`, 0 = Textformat) in X-Ray und DFT über `label_size` in den opts von `XrayFigure`.
- Textformat (Menü Format): global `text_fmt`, je Tab optional eigenes (`tab_fmt[STATE_KEY]`, ε = `epsilon`, gespeichert als
  `text_tabs`); `main.text_format(key)` mischt. Der Dialog zeigt nur `TEXT_OPTS` des Tabs. Geschlossener Rahmen
  (`axes_frame`) Standard seit 1.24.
- Navigation: Tabs in vier Gruppen als Leiste **oben** (`nav_bar`, `NAV_GROUPS`), Reiter ausgeblendet. Keine Leisten
  links/rechts: die Vorschau ist in der Breite begrenzt (Seitenleiste −20 % Abbildung, gemessen); Selbsttest verlangt
  bei 1440 × 900 Abbildungsbreite ≥ halbe Fensterbreite. Leere Tabs: Anleitung (`EmptyGuide`, `guide_<tab>_*`), Hinweise
  beim Zeichnen über `add_note` unter der Vorschau.
- Linke Spalte (`FigureTab.arrange`): „Achsen, Größe und Formate“ und Bildunterschrift eingeklappt (`STYLE.Fold`,
  Zustand in QSettings `fold/<Tab>/<Name>`, „(geändert)“ über Zustandsschlüssel gegen DEFAULT_STATE); seltene Zeilen
  per `split_group` in eigene Karten (CV Referenzierung, SEC Hervorheben, EPR Intensität, X-Ray Atome); Ergebnisse/
  Tabellen/SI-Text als Reiter neben „Abbildung“ (`to_right`/`move_right`) – nie unter die Abbildung (Höhe begrenzt
  sie dann, −28 % gemessen). Neue Karten dort einordnen; Abstände zentral in `STYLE.tidy`.
- Tab-Reihenfolge wie die SI: Synthese · NMR · IR + EA · HRMS · UV-Vis (ε) · Overlay · Fluoreszenz · CV · SEC · EPR ·
  X-Ray · DFT; offener Tab als Name (`tab`, alte Projekte: Index in der alten Reihenfolge umrechnen).
- NMR-Tab: Abbildungen = Mnova-SVG (nicht aus Bruker 1r rechnen: Referenzierung weicht ab). Kern aus der Achse
  („δ ¹H (ppm)“, senkrecht = 2D), sonst von Hand; Reihenfolge ¹H, ¹³C, übrige nach Massenzahl, dann 2D (`sort_key`).
  NMR-Zeile aus dem Mnova-Bericht (alle Kerne in einem Feld), ¹H-Frequenz auf 50 MHz gerundet (501 → 500); ¹³C auch aus
  den Peaklabels (`svg_peaks`, beschriftetes Lösungsmittelsignal fällt weg). Temperatur 298 K oder aus acqus; ins Projekt
  nur acqus/acqu2s/pulseprogram (kein FID). Struktur als Vektor ins SVG (`compose_structure`), Lage `auto` = freie
  Stelle über Belegungsmaske (`auto_place`, oben links bevorzugt), ziehbar (`manual`), Größe `struct_w` für alle Spektren
  gleich. Unterschrift „¹H NMR (500 MHz, CDCl₃, 298 K) of **X**.“
- Synthese-Tab: Schema über `scheme_files` (CDXML + gleichnamige SVG/PDF, .cdx, .emf). Word-OLE nur mit CDX (CDXML
  öffnet Word nicht als ChemDraw-Objekt, vom Nutzer geprüft); Vorschau EMF (Vektor) sonst PNG; OLE-Container eigener
  CFB-Schreiber (`uvvis_ole`). Mengenprüfung mit Rundungsintervallen der angegebenen Stellen (1.03 g = 1.025–1.035 g),
  Bezug = erste Zeile mit 1.0 eq. „Aus Schema“: Rollen aus dem Reaktionsschritt (RDKit `CDX_PRODUCT_ID`/`CDX_REAGENT_ID`),
  Pfeiltexte über `scheme_reagents` (Bedingungen weg, Lösungsmittel-Kürzel → Formel). Vorschau: nur das Schema auf
  Weiß (ausgeblendet ohne Schema), Text im Theme.
- SI-Methodentexte („SI-Text kopieren“, beim Export `…_methods.txt`): jeder Tab, der fittet (ε, CV, SEC, EPR), beschreibt
  englisch **nur die tatsächlich benutzten** Schritte mit den aktuellen Parametern, dann die Ergebnisse; Aufbau/Geräte
  stehen in der SI der Gruppe und nicht im Code. Keine Unsicherheiten erfinden (EPR-S = ½-Fit: ausdrücklich keine).
  Neue Fits → Satz in `methods_text` des Tabs ergänzen. Exponenten als „-1“ wie in der SI. Im Word-Export als Teil
  `methods` („Data processing and fitting“, `si_methods_blocks`, `SI.methods_html`; neue Fit-Tabs dort eintragen).
- SI-Stil (aus den SI der Gruppe): Absatz „m.p. …; IR …; HR-MS …; UV-Vis: λmax: 331 nm (ε = 8443 cm-1 M-1), …“, durch
  „; “ getrennt, Punkt am Ende. UV-Vis-Zeile nur mit den Banden des Bildes, aufsteigend, ε wie in der Tabelle gerundet
  (ohne ±). EA: „Elemental analysis calcd (%) for …: C …; found: …“, 2 Nachkommastellen, Warnung > 0.4 %.
  Word-Export exakt wie die SI-PDF der Gruppe: A4, Ränder 2.5 cm, Arial 11 (Schriftart wählbar über `SI.set_font`/QSettings
  `si_font`, Größe fest wegen `two_per_page`), Blocksatz, 1.5-zeilig; „Synthesis of **Name**“,
  Absatz mit fettem **m.p.**/**IR**/**HR-MS-ESI(+)**/**UV-Vis**/**λ**max, Exponenten als „-1“; „**Figure Sn**: X-ray solid state
  structure of **Name**. Thermal ellipsoids are shown with 50% probability.“ (Besetzung bei Fehlordnung „95% (A) and 5% (B)“);
  ≤ 8 ausgewählte Werte in der Unterschrift, sonst „**Table Sn:** Selected bond lengths/angles for **Name**.“ (Atom | … |
  Length / Å); Kristalldaten mit zentrierter erster Spalte, „a / Å“ usw.; Nummern als Word-SEQ-Felder (fortlaufend).
- „Alles auf Standard“ (`FigureTab.reset_defaults`): alle Schlüssel von DEFAULT_STATE außer `RESET_KEEP` des Tabs, Exportgröße/
  -formate und `cap_*`. In `RESET_KEEP` gehört, was Daten oder Angaben zur Messung sind (Dateien, Referenz/Kalibrierung,
  eingegebene Werte) – neue Schlüssel dort einordnen. X-Ray/DFT: `XRAY.reset_display` (+ Ansicht/Atom-Auswahl der
  gewählten Struktur; DFT behält Nummerierung, `label_style`, `zero_based`); ε: `MainWindow.reset_defaults` (DEFAULT_GLOB ohne
  Schichtdicke/Export). Immer `push_undo`.
- Verbindung des Projekts (`compound`) ist nur Vorgabe: Tabs mit eigener Struktur/Molmasse behalten diese.
- UI zweisprachig: jeder sichtbare Text über `uvvis_i18n.T(key)` mit DE **und** EN-Eintrag.

## Architektur
| Datei | Inhalt |
|---|---|
| `uvvis_gui.py` | Hauptfenster, ε-Tab, Projektlogik, Undo/Redo (JSON-Snapshots von `get_state`), Autosave, `selftest()`. `APP_VERSION` steht hier. |
| `uvvis_core.py` | `DEFAULTS`, Reader (Cary CSV, DSW/BSW/FBSW via `parseuv_lite`, Eclipse CSV), Basislinie, Peak-/Schultersuche, `linfit`, `evaluate`, `Figure` (Platzierung über FreeSpace-Raster, gespeicherte Positionen zuerst reservieren), Export, `Dragger`. |
| `uvvis_tabs.py` | `CanvasHost` (Vorschau maßstabsgetreu, dynamische DPI), `FigureTab` (Basis inkl. `methods_text`/`methods_button`, Export `_methods.txt`), Overlay- und Fluoreszenz-Tab. |
| `uvvis_extra.py` | TD-DFT-Parser (ORCA/Gaussian), Verbreiterung, `SimpleFigure`, Fotopaar mit Pfeil. |
| `uvvis_images.py` | Bilder laden (HEIC, EXIF), Hintergrund entfernen (ISNet-ONNX → GrabCut → Rand), Struktur-Rendering (PyMuPDF), Vektor-Overlay in PDF/SVG. |
| `uvvis_chem.py` | CDXML über RDKit: Formel, Molmasse, Ersatzzeichnung. |
| `uvvis_project.py` | Projektordner (`project.uvvis`, `data/`, `exports/`), relative Pfade, Backup. |
| `uvvis_report.py` | Excel-Report (openpyxl): Werte blau, Kontrollformeln schwarz, native Diagramme; Sprache = Programmsprache. |
| `uvvis_cv.py` | Cyclovoltammetrie: Gamry-.DTA-Leser (CURVEn oder CURVE+Cycle), `analyze_couple` (E_pa/E_pc/E½/ΔE_p, Nicholson), `suggest_couples`, Randles-Ševčík, `CVTab`. |
| `uvvis_sec.py` | Spektroelektrochemie: BWSpec-Leser (λ aus coefs_a0…a3), Potential je Spektrum über Uhrzeit (Gamry DATE/TIME + T), scheinbarer Nernst-Fit (Raster E½/n), `SECTab`. |
| `uvvis_epr.py` | CW-EPR: BES3T-Leser (.dsc/.DTA, LIT/BIG, D/F/I, 2D+YGF), ASCII (MS400, EasySpin), EasySpin-Parameter (`Sys.D` MHz → cm⁻¹), Dunkelspektrum, Basislinie, Ausblenden, Glätten, `fit_scale`, `EPRTab`. Felder intern in mT. |
| `uvvis_color.py` | Farbe der Lösung: T = 10^(−A) × Planck 6504 K, CIE-1931-Kurven (Näherung Wyman 2013), Bradford → sRGB; Kanäle > 1 gemeinsam skalieren. |
| `uvvis_update.py` | Update-Prüfung: neuestes GitHub-Release (API), Versionsvergleich, Paketname je System. Automatisch max. 1×/Tag, im Selbsttest ohne Netz. |
| `uvvis_irms.py` | IR + MS: OPUS-Leser (Blockverzeichnis, T als Anteil → %), OPUS-PDF-Peaks, Peaksuche (Parabel, w/m/s/br), MS-Bericht (docx: Text + EMF-Beschriftungen, CDX-Objekt), Bruker-.d-Leser (BAF-Linienspektren, eigene Kalibrierung), `lc_found`, Ionenmassen, SI-Zeilen, `IRMSTab`. |
| `uvvis_xray.py` | X-Ray: eigener CIF-Leser (`Block`, Werte als Text), `Structure` (Zelle, U_kart, Symmetrie, geom-Tabellen), `Molecule` (Vervollständigung, Fehlordnung, Fragmente), `measure`, `project`/`pick` (ORTEP-Projektion), Tabellen-Markup (`runs` → HTML/Unicode/openpyxl), `XrayFigure`, `XrayMouse` (Drehen mit Blitting), `XrayTab`, `make_test_cif`. |
| `uvvis_hrms.py` | Tab HRMS: Chromatogramm (TIC/XIC, LC-Bereich per `SpanSelector`), gemitteltes Linienspektrum (`averaged_spectrum`, 5 ppm), Peak per Klick, Isotopenmuster (`isotope_pattern`, Isotope aus RDKit, Feinstruktur bis m/20000 zusammengefasst). Leser/Ionenmassen in `uvvis_irms`. |
| `uvvis_dft.py` | Tab DFT: xyz-Leser (mehrere Bilder, Ordnungszahlen), `read_text` (UTF-16), `parse_orca`/`parse_gaussian`/`read_calc`, `si_parts`/`computational_details` (SI-Block, englisch), `match_reference`/`kabsch` (Vergleichsmodus), `bonds_of` (kovalente Radien wie X-Ray), `XyzMolecule`, `renumber`, `write_xyz`, `DFTTab` (Klick-Nummerierung, SI kopieren, Word), `make_test_xyz`/`make_test_orca`/`make_test_gaussian`. Zuschnitt der SI-Bilder: `XRAY.save_tight`. |
| `uvvis_nmr.py` | Tab NMR: `svg_info`/`svg_peaks` (Mnova-SVG), Bruker `acq_params`, `parse_mnova`/`nmr_line`, `caption_html`, Strukturplatzierung (`occupancy`, `auto_place`, `compose_structure`), `NMRTab`, `make_test_svg`/`make_test_acqus`. |
| `uvvis_synth.py` | Tab Synthese: `parse_amounts`/`check_amounts` (Rundung), `row_amounts`/`amount_text`, `scheme_files`/`scheme_molecules`/`scheme_drawing`, `doc_to_html`, `SynthTab`. |
| `uvvis_cdxml.py` | CDXML selbst zeichnen (`render_svg`: Bindungen, Labels, Formelstil, Pfeile, Texte; Labels für CDXML ohne `<t>`), `scheme_texts`/`scheme_reagents`. |
| `uvvis_ole.py` | OLE-Container (CFB v3) für bearbeitbare ChemDraw-Objekte in Word (`chemdraw_streams`, `write_cfb`). |
| `uvvis_si.py` | SI-Zeilen: Elementaranalyse (mittlere Atommassen, Solvat, Grenze 0.4 %), UV-Vis-Zeile aus den ε-Ergebnissen, Absatz (`join_lines`) und eigener docx-Schreiber (`write_docx`, ohne Zusatzpaket; Dreilinien-Tabellen, OLE, Seitenumbruch), `two_per_page`, `chem_html`. |
| `uvvis_style.py` | Erscheinungsbild: Fusion + eigene Palette (hell/dunkel/System, Menü Format), zentrales Stylesheet, Karten (`card`), SVG-Symbole (`icon`), `tidy` (linke Spalte: Zahlenfelder ≤ 160 px, Knöpfe in natürlicher Breite), `hint_when_disabled` (Detailkarte erst nach Auswahl). Betrifft alle Tabs, nicht die Abbildungen. |
| `release_notes.py` | Release-Titel/-Notes für GitHub aus `CHANGELOG.md` + `CHANGELOG.de.md` (Release-Job in `build.yml`; fehlt die Version, scheitert das Release). |
| `uvvis_i18n.py` | Texte DE/EN; `T(_key, **kw)` (Parameter heißt `_key`, damit `key=` als Format-Argument geht). |
| `parseuv_lite/` | Vendorte parseuv-1.0.4-Version (BSD-3), angepasst. |

## Befehle
```bash
pip install -r requirements.txt                       # Python 3.12 (wie CI)
python uvvis_gui.py                                   # App starten
QT_QPA_PLATFORM=offscreen python uvvis_gui.py --selftest selftest_out   # MUSS vor jedem Commit „OK“ melden
python build.py                                       # PyInstaller-Build (braucht: pip install pyinstaller)
python tools/make_screenshots.py                       # README-Screenshots (docs/screenshots), nur künstliche Daten
```
- Neue Funktion → eigener Abschnitt im `selftest()` (Muster: `report.append("…: OK")`).
- Der Selbsttest läuft in CI auch mit der **fertig gebauten** App auf allen drei Systemen.

## Release-Ablauf
1. `APP_VERSION` in `uvvis_gui.py` erhöhen.
2. `CHANGELOG.md` **und** `CHANGELOG.de.md` ergänzen; bei sichtbaren Änderungen `README.md` **und** `README.de.md`.
3. Selbsttest, commit, dann `git tag vX.Y.Z && git push && git push --tags` → GitHub Actions baut und erstellt
   das Release; Titel und Notes erzeugt `release_notes.py` aus den Changelogs (also beide Changelogs vollständig pflegen).
   Ohne lokales Tag (z. B. aus einer Cloud-Sitzung, die nur ihren Branch pushen darf): nach dem Merge auf `main` unter
   Actions → „Build Elucida“ → Run workflow (Branch `main`, Eingabe `release` = `vX.Y.Z`); der Release-Job legt das
   Tag selbst an. Der Job bricht ab, wenn das Tag nicht zu `APP_VERSION` passt.

## Bekannte Fallen
- **Umbenennungen (1.16 UVVisTool → Spectravolt, 2.0 → Elucida):** Programm heißt Elucida, Repo
  `robinesken97/elucida`. Intern bleiben `uvvis_*.py` und `project.uvvis`. Alte Einstellungen (`OLD_APP_NAMES`:
  zuerst `QSettings("Spectravolt")`, dann `"UVVisTool"`, `migrate_settings`) und der Datenordner (`app_data_dir`:
  `…/Spectravolt`, sonst `…/UVVisTool`) werden beim ersten Start übernommen. Alte Versionen fragen die GitHub-API unter
  den alten Repo-Namen ab (GitHub leitet um) – Repo **nie** neu unter `spectravolt` oder `uvvis-tool` anlegen. Der
  Updater sucht Pakete nur über die Systemkennung (`windows-x64` …), nicht über den Programmnamen. Icon: Quelle
  `assets/icon.svg`, PNG mit `python tools/make_icon.py`.
- **Windows-Zeilenenden:** CSVs in Tests mit `newline=""` schreiben; Reader überspringt leere Zeilen
  (früher Windows-CI-Abbruch durch `\r\r\n`).
- **AppImage (Linux):** in CI aus dem PyInstaller-Ordner gebaut; appimagetool und type2-Runtime mit fester
  Version und SHA-256 in `build.yml` – bei Updates beide Prüfsummen neu eintragen.
- **Windows-Konsole (cp1252):** Selbsttest-Meldungen nur mit ASCII/cp1252-Zeichen (kein λ, ε); die
  Ausgabe ersetzt sonst Zeichen, früher brach CI am `print` ab.
- **PyInstaller:** neue Imports, die nur lazy geladen werden, als `--hidden-import` in `build.py` eintragen.
- **MuPDF:** ignoriert SVG-Clip-Pfade → Kurven geometrisch clippen (`clip_polyline`); Rechtecke mit Breite 0
  fallen bei `|=` weg → Koordinaten-Union; Alpha ist premultipliziert → beim Einfärben un-premultiplizieren.
- **Label-Kollisionen:** gespeicherte Positionen von Labels, Inset und Bildern vor neuen Elementen reservieren.
- **Mausereignisse (matplotlib):** `LocationEvent` rundet x/y auf ganze Pixel; Messpunkte liegen in der Vorschau
  < 1 px auseinander. Tests mit simulierten Klicks/Hover nur auf ±1 Messpunkt prüfen und dann, dass die Anzeige
  genau den getroffenen Punkt zeigt (CI-Systeme treffen sonst unterschiedliche Nachbarn).
- **Undo:** während `set_state` greift `_restoring`; Änderungen über `QTimer` verzögert erfassen.
- **macOS-Version:** `build.py` liest `APP_VERSION` und schreibt sie nach dem Build in die `Info.plist`,
  danach `codesign --force --deep --sign -` (Signatur schließt die Info.plist ein).
- **pymupdf:** `get_pixmap(dpi=…)` nur mit ganzen Zahlen (die Windows-Version wirft sonst TypeError; lokal unbemerkt).
- macOS-Build ist unsigniert (Gatekeeper: Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“).
  Trackpad-Zoom und HiDPI-Vorschau auf echter Mac-Hardware sind noch nicht verifiziert.
- **macOS Intel** (`macos-15-intel`-Runner): rdkit nur bis 2025.9.3, onnxruntime nur bis 1.23.2 als
  x86_64-Wheel (pip wählt sie automatisch); numpy/PySide6/opencv verlangen macOS 14. Der Runner ist
  befristet – fällt er weg, Intel-Build aus der Matrix nehmen.

## Offene Punkte
- CV geprüft mit echten Gamry-Serien (MeCN, DCM, THF, DMF; 25–500 mV/s, Ac₂Fc/Fc-Zusatz): 6m in MeCN E½ = −1,10 V vs.
  Fc⁺/Fc. THF bei ≥ 400 mV/s iR-dominiert (ΔE_p bis ≈ 600 mV) – „Vorschlag“ findet dort zu Recht kein Paar.
- X-Ray geprüft mit künstlicher CIF, einer Olex2-CIF und einer CCDC-CIF mit Fehlordnung (95:5) und THF; Symmetrieerzeugung
  nur künstlich; Polymere werden
  abgebrochen (`max_factor`). Stufe 3 (Vergleich mit DFT-Geometrie, ORCA-xyz) vorbereitet: `measure` arbeitet nur
  mit Atom-Schlüsseln (Label|Operation) und `param_label`; ein xyz-Molekül mit denselben Labels kann eine eigene
  Spalte liefern (Zuordnung der Atome noch offen).
- BSW-Datei mit Sprung in Spektrum 60 (CSV-Export zum Vergleich fehlt).
- Echte Gaussian-TD-DFT-Ausgabe noch nicht getestet (nur ORCA inkl. SOC); DFT-Tab: Gaussian-Leser mit einer Opt+Freq geprüft.
- DFT-Tab: IboView wird bewusst nicht angesteuert (eigenes Rendering). Multireferenz-Auswertung (CASSCF/NEVPT2/SORCI,
  z. B. Diradikaloide, Triplett-Vinylidene) zurückgestellt: großer Parser, bisher Abschreiben der ORCA-Tabellen.
  Vergleichsmodus mit echter CIF noch ungeprüft (nur künstliche CIF und echte DFT-Paare).
