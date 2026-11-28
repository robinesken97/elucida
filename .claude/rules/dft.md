---
paths:
  - "elucida/tabs/dft.py"
  - "elucida/tabs/dft_pages.py"
  - "elucida/tabs/profile_*.py"
  - "elucida/tabs/diagram_layout.py"
  - "elucida/tabs/multireference.py"
  - "elucida/tabs/xray.py"
  - "elucida/core/orbitals.py"
  - "elucida/core/minao.py"
  - "elucida/formats/calc.py"
  - "elucida/formats/orbital_files.py"
  - "elucida/formats/multireference.py"
  - "elucida/formats/nbo.py"
  - "elucida/tabs/dft_nbo.py"
---

# DFT: fachliche Regeln (nicht ändern ohne Rückfrage)

- DFT-Tab (xyz): Ansicht über `XyzMolecule` mit der X-Ray-Schnittstelle (`XrayFigure`/`XrayMouse`), Startansicht
  **mit** H (jedes Atom muss anklickbar sein). Umnummerieren: angeklickte Atome der Reihe nach vorn, Rest in bisheriger
  Reihenfolge (optional „H folgen ihrem Atom“: übrige Schweratome, dann alle nicht angeklickten H nach ihrem Atom geordnet –
  angeklickte behalten die Klicknummern, Nutzerwunsch P5 „wissenschaftliche Konvention“); gespeichert als `order`
  (Dateiindizes), Atom-Schlüssel `a<Index>` bleibt.
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
- DFT-Orbitale (`core/orbitals`, Nutzerwunsch: Aussehen **wie IboView**, Werte aus dessen Quellcode 2021-10-19 nur
  gelesen, GPL – kein Code übernommen): Isofläche umschließt 80 % von Σψ² (`iso_for_fraction`, wahlweise fester
  Isowert); Farben je Orbital (`orbital_colors`: Farbton −120°·(k+1) ± 25°, S 0.6, Deckkraft 0.6); Licht = drei
  Lichter (`IBO_LIGHTS`, Haupt­licht **oben rechts**), diffus 0.7·c^0.8, Glanz k·(−0.5c¹⁶+1.2c⁶⁴) nur über n·L;
  Deckkraft = α·D/|n_z| (Ränder deckender), nur Vorderseiten, die **hintersten 4** Schichten vor dem Atom; Aufhellung
  ab 1 Bohr hinter der Mitte über 22 Bohr. Atome mit Orbital immer Stil `iboview` (Radius 0.4 × IboView-Tabelle,
  RasMol-Farben, Stab 0.148 Å zur Mitte auf 72 % verjüngt). Nutzerwunsch „genauso wie IboView“: geprüft gegen ein
  lokal kompiliertes IboView (Scratchpad, nie ins Repo) mit gleicher Kamera – Kugeln pixelgenau (p95 < 1.2 %),
  Isowerte gleich. Kugeln = Höhenlinien der fertigen Farbe mit Löchern (`ibo_sphere_layers`), Stäbe = Längsstreifen
  mit exakter Zylinderfarbe auch schräg (`ibo_rod_colors`); Stäbe liegen VOR ihrer Kugel ab der Austrittskurve, sobald der
  Austritt auf der Vorderseite liegt, auch leicht nach hinten zeigend (`atom_rods_over`, je Streifen wie der Tiefenpuffer; nur nach der Richtung zu schalten ploppte beim Drehen). Mit Molden: Bindungen/-ordnungen wie IboView = Wiberg in
  IAO (MINAO aus `core/minao`, `iao_bond_orders`, ≥ 0.2; ±0.2 an ganzer Zahl → ganz), n Stäbe à 1.4/n nebeneinander
  (Abstand 0.7 Stabradien, Richtung `ibo_tan_u`), Teilbindung < 0.8 gestrichelt; Cube: Einfachbindungen. Element-
  symbole (C/Heteroatome, 0.8 Bohr, Atomfarbe −20 %, schwarzer Rand) abschaltbar (`orb_labels`). Orbital = Rasterbild
  (`OrbitalImage`, Raycasting auf dem Gitter, Kanten 2×2 nachgerechnet, beim Zeichnen in Zielauflösung, Export ≤
  `ORB_MAX_DPI` 300, beim Ziehen ohne GPU 1/4, mit GPU volle Auflösung (`core/gpu3d.py`, gleicher Algorithmus wie `ORB.render`; nur Vorschau: Export, SI, Word und Vorschaubilder rechnet immer numpy, pixelgleich mit GPU an/aus; ACID-Netz bleibt CPU). NTO-Anordnung folgt immer der automatischen Ansicht, nicht der Drehung; Labels in 3D-Figuren immer bei `TABS.PREVIEW_DPI` platzieren) über den Vektor-Atomen; Verdeckung über Tiefenkarte (Nutzer-OK: Raster im PDF).
  Cube: MO aus MO-Liste/Dateiname (ORCA „mo21a“, ab 0), HOMO/LUMO aus der Ausgabe der Geometrie. Molden: eigene
  Gauß-Auswertung bis g; Konvention (Primitive normiert/roh, ORCA-Vorzeichen f/g ±3/±4) über CᵀSC = 1 gewählt,
  > 1e-3 **ablehnen**. Geprüft gegen PySCF (cc-pVTZ kartesisch/kugelförmig, def2-QZVP mit g: Werte wie deren Cubes,
  ±2e-5); echte ORCA-Molden-Datei noch ungeprüft. Gitter 0.1 Å (IboView 12/Å). Gleiche Atome/Koordinaten (± 0.02 Å)
  → an die gewählte Geometrie hängen, sonst neue Geometrie. Export: Struktur ohne Orbital + je Orbital ein Bild.
- Energiediagramm (Nutzerwunsch 2026-11-11; `tabs/diagram_layout.py` zeichnet, `tabs/dft_pages.py` ist die Seite): gehört in
  den **Reaktionspfad** des Projekts (Computerchemie) und ist nur dort bedienbar; im DFT-Tab einer Verbindung gibt es den
  Reiter nicht mehr (`show_profile_tab` nimmt ihn heraus, nicht nur verbergen: verborgene Seiten zählen zur Mindestbreite
  des Fensters). Gespeicherte Profildaten einer Verbindung bleiben in ihrer Projektdatei (nichts umräumen, nichts löschen). **Ein** Zeichenwerk für DFT-Tab und Pfad-Abbildungen (`DL.build_levels`, `images=True`
  nur in der Seite). Darstellung getrennt von den Werten: `prof["layout"]` (Stufenbild) / `prof["layout_irc"]` – Stil
  gehört zum Profil, nicht mehr zur einzelnen eingefügten Abbildung (`style_of`; alte Abbildungen ohne Profilstil behalten
  ihren). Verbinder: `prof["edges"]` = None → aus Schritt und Pfadbuchstaben (`implied_edges`, wie bis 2.7.1), sonst
  Liste {a, b, line, arrow, color, label, label_dx/dy}; Plateaus sind Knoten (im Bild an den Enden ziehen = verknüpfen: `LinkMouse`, oder
  Tabelle; an der Linie ziehen = verschieben, Nutzerwunsch 2026-11-13: `on_move` -> `DftPages.level_moved`, x im Raster
  `SNAP`, y nur im schematischen Bild, automatischer Wert bleibt ungesetzt, Energie nie geändert). Linien `EDGE_LINES` (gestrichelt, durchgezogen, gepunktet, geschwungen, Wellenlinie = strahlungslos wie im
  Jablonski-Diagramm, keine). Senkrechte Übergänge (Plateaus übereinander) laufen **in der Spalte**, seitlich an den
  Linien angesetzt (`VERTICAL_SLOTS`, mehrere nebeneinander), nie über einer Beschriftung (`text_half`), und enden auf
  der Ziellinie; ein Niveau dazwischen wird gekreuzt wie von den Pfeilen im Jablonski-Diagramm, seine Linie ist dort
  unterbrochen. Zwischen den Spalten laufen nur die Verbinder; nur ohne freie Stelle in der Spalte geht der Übergang
  dicht außen am Stapel vorbei (Seite mit weniger Kreuzungen). Wellenlinien und Übergänge liegen über gekreuzten
  Verbindern (heller Saum). Beschriftungen der Verbinder stehen **neben** der Linie, nie auf einem Strich, Plateau oder
  anderen Text (`_edge_labels`: erste freie Stelle entlang des Verbinders; Nutzerwunsch „nicht über den
  Zeichenelementen“). Energie-, Namens- und Verbinder-Labels sind ziehbare Anmerkungen (Abstand zum Plateau bzw. zur
  Mitte des Verbinders in Achsenbruchteilen; ein gezogenes Label bleibt, wo es liegt).
  Je Plateau (Nutzerwunsch 2026-11-11, ersetzt den früheren `DiagramLayoutEditor` mit Übernehmen/Abbrechen): in der
  Tabelle der Rechnungen wählen, Felder darunter (`level_selected`/`level_field`/`_level_set`, wie die Verbinder) setzen
  `prof["layout"]["nodes"][uid]` = x (Lage in Schritten), width, color, schematisch auch y und break_after; fehlender
  Schlüssel = automatisch (`DL.arranged`: x = Schritt, Breite 0.7, Farbe des Pfads), ein Wert gleich dem automatischen wird
  nicht gespeichert, „Plateau automatisch“ (`level_auto`) entfernt alle. Über den Feldern steht, zu welchem Plateau sie gehören (`lbl_level`); die Tabelle markiert die ganze Zeile; Farbfeld in normaler Größe, der einzelne Knopf über die Wertespalte (Sichtprüfung 2026-11-12). Ein Profil in „Gestalten“ bearbeiten zeigt
  diese Seite. Stilvorlagen `PRESETS` (Auswahlliste `cmb_preset`, „eigene“ nach
  einer Änderung) setzen nur Stil, nie Lage oder Werte; „article“ = ohne Rahmen, Name und Wert fett-kursiv unter dem
  Plateau. Jede Eigenschaft einer Vorlage ist ein eigenes Feld (Nutzerwunsch 2026-11-13: Graphen voll einstellbar):
  `labels` (split/below/above), `label_font`, `signed` (+18.9, ±0.0), `level_width`, `axis_title` („ | “ = Zeilenumbruch;
  ohne Rahmen: Pfeil oben links, Titel daneben); `prof["sections"]` = Balken unter dem Profil {text, a, b, color}.
  Einheit `prof["unit"]` (`UNITS`: kcal/kJ/eV): gerechnet und gespeichert wird immer in kcal/mol (auch die schematische
  Höhe), umgerechnet erst für Bild, Achse, Feld „Höhe“ und Unterschrift (`energy_text`, `arranged(factor)`).
  Neue Karten der Seite brauchen ihren Titel in `TABS.STEP_TITLES` (sonst landen sie im ersten Schritt). Ob ein Übergang ISC/IC ist, schreibt der Nutzer als Text;
  das Programm leitet es nie aus den Rechnungen ab. Stempel der Abbildungen (`profile_stamp`) enthält `edges`/`layout` nur,
  wenn gesetzt (alte Stempel bleiben gültig).
- DFT-Energieprofil/IRC/NICS (F4, `tabs/dft_pages.py`, Reiter neben „Abbildung“): Spezies = Opt/Freq-Einträge,
  Einzelpunkte nur über gleiche Atome/Koordinaten (± 0.02 Å, nie Dateinamen); G = E(SP) + (G − E_el), H analog, ΔE = E(SP);
  haben einige Spezies SP, fallen die übrigen weg (Hinweis, nie mischen); SP ohne Lösungsmittel bei SMD/CPCM-Opt nur
  Hinweis. kcal mol⁻¹, eine Nachkommastelle, echtes Minus, Bezug = erste Spezies; Unterschrift „<SP>//<Opt> level of
  theory“ (übliche Reihenfolge, Robin) mit T/p; Methode aus den „!“-Zeilen (`level_of_theory`, Schreibweise wie in der
  Eingabe). IRC nur ΔE_el (nie mit G-Stufen), x = Σ|ΔR| der Trajektorie (TS = 0) oder Bindungsspalte, verschiedene
  Methoden ablehnen. NICS = −σ_iso, NICSzz = −n·σ·n (n = Ebene der Schweratome < 2,5 Å um das Bq), Scan ab 10 Bq
  (NICS schwarz, NICSzz rot). Isowert-Bedienung wie IboView („Threshold Type“ density/absolute, absolut Standard 0.01).
- Gaussian-Energie (Literaturprüfung 2026-11-12): bei MP2, Doppelhybriden und CCSD(T) ist `energy` die letzte
  Gesamtenergie mit Korrelationsanteil („EUMP2 =“, „E(B2PLYP) =“ nach „E2(“, „CCSD(T)=“; Ziffern wie gedruckt, nur der
  D-Exponent aufgelöst), nicht „SCF Done“. Formate aus dem Gedächtnis, nur mit künstlichen Zeilen geprüft: echte
  Gaussian-MP2-/Doppelhybrid-Ausgabe steht aus. ORCA nimmt weiter FINAL SINGLE POINT ENERGY.
- Multireferenz im Stufenbild (Nutzerauftrag 2026-11-13): Plateaus mit CASSCF/NEVPT2/SORCI-Ergebnis (Einzelpunkt vor der
  Rechnung selbst) nehmen die Gesamtenergie eines Zustands; Wahl je Plateau in der Karte (`mr_result`/`mr_state` in
  `prof["species"][uid]`, Vorgabe nicht gespeichert: höchste Theorie QD-NEVPT2 > NEVPT2 > SORCI > CASSCF, bei gleicher
  die letzte, Wurzel 0). Nur elektronisch; G/H = E(Zustand) + Korrektur der eigenen Frequenzrechnung, ohne sie E_el mit
  Hinweis und Satz in der Unterschrift (`el_only`). Unterschrift nennt Methode, Wurzel und Multiplizität. Nur
  synthetisch geprüft.
- NICS-Unterschrift aus den Bq (`nics_geometry`, nie aus Dateinamen): ptp(h) < max(0.1 Å, 5 % des Wegs) = in einer Höhe,
  ptp(h) > 95 % des Wegs = entlang der Normalen, sonst „along the scan path“. Die lokale Normale zeigt zur Seite der
  globalen.
- Gaussian-Methode (`level_of_theory`): Token „Methode/Basis“ der Route, auch direkt am „#“; Optionen mit „/“ wie
  `iop(10/93=1)` nie. Ein Energieprofil mit einer einzigen Stufe kommt nicht in die SI.
- 3D-NICS (1.2.0, Nutzerauftrag 2026-11-13 mit Vorlagebild; `dft_pages.nics_grid`/`build_nics3d`): Dateien ab
  `NICS_GRID_MIN` (200) Bq sind Teile eines Gitters (keine Ebenen je Punkt, nicht in der Tabelle), außer die Punkte
  liegen auf einer Linie mit gleichmäßigen Schritten ohne Sprung (gerade oder geknickt, `nics_is_path`): dann ist es ein
  Scan, auch mit ≥ 200 Bq (Nutzerentscheidung 2026-11-14); Bq in einer einzigen Ebene werden mit eigener Meldung abgelehnt. Alle Teile müssen
  dieselbe Geometrie haben (± 1e-3 Å) und zusammen ein vollständiges regelmäßiges Gitter ergeben, sonst ablehnen und
  die Punktzahl nennen (nie fehlende Punkte ergänzen). NICS = −σ_iso (geprüft an einem Punkt gegen die Logdatei).
  Bild wie die Vorlage: Kugel-Stab („depth“), zwei Isoflächen +`iso_pos` (Standard 5, rot, entschirmt) und −`iso_neg`
  (Standard 15, blau, abgeschirmt), eine Deckkraft; umgesetzt als ein Feld Wert/Isowert mit Fläche bei ±1 über das
  Orbital-Rendering. Unterschrift nennt beide Isowerte mit Farbnamen, Gitterabstand und Rechenniveau (`lev//geom` wie
  beim Scan). Scan und Gitter zugleich: Auswahl „Abbildung“ im Reiter, Export/SI beide; Export zusätzlich als Cube.
  Geprüft mit zwei echten Gittern (16 und 29 Teilrechnungen, 0.2 Å).
- ACID (1.2.0, Nutzerauftrag 2026-11-13 mit Vorlage aus der eigenen SI; `tabs/dft_acid.py`, Leser `formats/aicd.py`,
  Reiter „ACID“, Zustand `acid`): Nichts wird gerechnet. Quellen: (1) AICD-Ausgabe (Ordner `<Name>.d` aus
  `AICD --povrayinput -c …`): `Isoober.inc` (`read_isoober`: `#declare Isooberflaeche = mesh` nur aus `smooth_triangle`
  mit 6 Vektoren, `#declare Pfeile = union` je Zeile Zylinder (Green) + Kegel (Red) ab dem Zylinderende +
  „// Länge: x“, `Magnetfeldvektor` Zylinder + Kegel, `Aufrufzeile`) und `Molekuel.inc` (PovChem, `object { Atom_<Name>
  translate <x, y, z> }`, Namen über RDKit); Isowert aus dem internen Aufruf „-- <iso> <Bx> <By> <Bz>“ nur, wenn B zum
  Magnetfeldvektor passt. Layout geprüft an einer echten öffentlichen AICD-3.0.4-Ausgabe (mit `-s`, 825 Dreiecke,
  149 Pfeile; GitHub LRG-computational/deloc-vis, 2026-11-14); anderes ablehnen. Gaussian-Hilfsdatei (`.txt`,
  „Stromdichtetensor“-Blöcke) nie lesen. (2) Cube mit dem ACID-Skalarfeld (`read_acid_cube`: ein Datensatz, mit Atomen,
  min ≥ −1e-3·max). AICD geht dem Cube vor (Hinweis). Optional Gaussian-Ausgabe der CSGT-Rechnung (`read_acid_log`:
  NMR=CSGT + IOp(10/93); nur Methode/Basis, IOp(10/93=2) = „selected orbitals“).
  Bild: Kugel-Stab „depth“; AICD-Netz eigenes Raster (`mesh_render`, Tiefenpuffer, Atome davor verdecken, 2×2
  Unterabtastung, Pfeile als Band + Dreieck knapp vor der Fläche, mindestens `MIN_ARROW_PX`) als Bild über den Atomen
  wie die Orbitale (`MeshImage.attach` setzt `F.orb_art`, xray.py unverändert); Cube über das Orbital-Rendering (eine
  Fläche bei Feld/Isowert = 1). Vorgaben wie die Vorlage: gelb `#e6d81e`, Deckkraft 0.9, Pfeile `#00ff00`/`#ff0000`
  (POV Green/Red), Magnetfeld `#008000`; Cube-Isowert 0.045. Pfeile nur ausgedünnt (fester Zufall, Anteil in %) oder
  um ihren Anfang skaliert. Magnetfeld als Symbol unten links (projizierter Pfeil, ⊙/⊗ bei Blick entlang B), nie
  diatrop/paratrop behaupten (Ableseregel nur im Tooltip/Handbuch). Unterschrift: Isowert (Cube: Feld; AICD: aus der
  Datei, sonst weggelassen), „based on a CSGT calculation at the <lev>//<geom> level of theory“, Pfeile/Magnetfeld je
  ein Satzteil mit Farbnamen, Zitate Herges/Geuenich 2001 und Geuenich et al. 2005 (Methode, nicht Programm).
  Export/SI über `DftPages.figures` (Kürzel „ACID“); im Reaktionspfad aus. Robins eigene AICD-Ausgaben ungeprüft.
- Pflichtangaben der Zeitschriften (Auftrag 2026-11-13, ACS Research Data Guidelines, Org. Lett., Angew. Anhang F):
  Reiter „Energietabelle“ (`grp_si_tbl`, `si_table_row`, `SI_TABLE_HEAD`): je Rechnung N_imag, E_el, E_nuc, H, G, H_corr,
  −TS als Text wie in der Ausgabe, fehlend = „–“ (`DASH`; CSV: leere Zelle), nie berechnet oder geschätzt.
  E_nuc: ORCA „Nuclear Repulsion … Eh“ (letzte), Gaussian „nuclear repulsion energy … Hartrees“ (die des Frequenzjobs wie
  E_el). H_corr nur Gaussian „Thermal correction to Enthalpy=“ (ORCA druckt H − E_el nicht; „Thermal Enthalpy
  correction“ ist nur kB·T und gehört nicht hierher). −TS: ORCA „Total entropy correction“, sonst „Final entropy term“
  mit umgekehrtem Vorzeichen (Text, keine Rechnung); Gaussian druckt −TS nicht in Hartree. Multireferenz: E_el/H/G/
  Korrekturen leer wie im SI-Block. Programm mit Version als Satz unter der Tabelle (`program_note`; Gaussian-Revision aus
  „Gaussian 16:  ES64L-G16RevC.01“). Word: Tabelle einspaltig nach den Strukturen (`docx_blocks` beginnt mit
  `("columns", 2)`, damit in der Gesamt-SI die nächste Verbindung wieder zweispaltig steht). Alle Geometrien des Tabs
  als EINE xyz (`collection_text`: Atomzahl, „Name  E_el = … Eh“, „El x y z“ mit den Ziffern der Datei, ASCII-Minus) im
  Export (`…_structures.xyz`) und im Datenpaket (`DFT/structures.xyz` aus dem Zustand über `collection_from_state`,
  geschrieben nach `.elucida/dft/`). Eingabedateien (`INPUT_EXT`: .inp/.gjf/.com, gleicher Name neben der Ausgabe)
  kopiert `PRJ.import_file` mit (nie überschreiben) und das Datenpaket nimmt sie auf; fehlende nur als Hinweis, nie
  erfinden. App-Ansicht (Abnahme new-views, 2026-11-13): zwei `summary_grid` (Energien; E_nuc/Korrekturen/Programm/
  Eingabe), Köpfe ohne Einheit („Alle Energien in Eₕ“ als Satz), Namensspalte kürzt (`FitGrid.elide_col`, Tooltip),
  bei 1200 und 1500 px ohne Querrollen; Kachel „Eingabe n/m“ in Warnfarbe (`kpis`, drittes Element). Nur mit künstlichen Ausgaben geprüft (Zeilenformat von E_nuc/Korrekturen aus dem Gedächtnis).
- Ladungen (1.2.0, Auftrag 2026-11-13; `formats/calc.parse_populations`, Reiter `tabs/dft_pop.py`): nur an echten Ausgaben
  geprüfte Layouts – ORCA Mulliken/Löwdin (mit Spinpopulationen), Gaussian „Mulliken charges[ and spin densities]:“;
  jeweils letzter Block. Hirshfeld nicht gelesen (keine echte Ausgabe); NPA/NBO gehört zum eigenen NBO-Leser. Neues
  Schema = Eintrag in `POP_SCHEMES` + Leser. Atomzahl ≠ Geometrie → keine Tabelle. SI-Tabelle nur mit `pop_si` je
  Eintrag (ORCA druckt immer), CSV `<Name>_charges.csv` mit den gedruckten Werten.
- HOMA im DFT-Tab (Paket A 1.2.0): wie X-Ray (`xray.md`), Geometrie der Rechnung. NICS desselben Rings nur aus Dateien
  der Seite NICS mit gleichen Atomen/Koordinaten (± 0.02 Å), Bq seitlich ≤ 0.3 Å von der Ringnormalen, Höhe 0 bzw.
  1 ± 0.1 Å, Mittel beider Seiten (`homa.nics_for_ring`); 3D-Gitter nicht. Der NICS-Code bleibt unverändert.
- NBO (1.2.0, Nutzerauftrag 2026-11-13; Leser `formats/nbo.py`, Reiter `tabs/dft_nbo.py`, Zustand `st["nbo"]`): Elucida
  **liest nur**, rechnet nichts. Geprüft an echten Ausgaben von **NBO 7.0.10 über ORCA 6.0.0** (geschlossenschalig, eine
  NBO-Analyse je Datei, UTF-8 und UTF-16): NPA-Zusammenfassung, Hauptliste (Besetzung, Hybride je Zentrum), NBO-Summary
  (Energie, Lewis-Anteile), E(2), NRT (Gewichte mit Added(Removed), Bindungsordnungen t/c/i, Valenzen). Andere
  NBO-Versionen, Gaussian/GENNBO, ORCA ≠ 6, Multiplizität ≠ 1 und mehrere NBO-/NRT-Abschnitte werden mit Meldung abgelehnt.
  Wiberg (BNDIDX, Folgeauftrag 2026-11-14): Layout nach NBO-7.0-Handbuch B.6.5, geprüft an öffentlichen echten Ausgaben
  (ORCA 6.1.1 + NBO 7.0, ORCA 5.0.4 + NBO 7.0.5, GenNBO 7.0.10; Quellen in Elucida-Audit/nbo-public/QUELLEN.txt, nie ins
  Repo); streng (`_parse_wiberg`: Spaltenblöcke vollständig, Werte d.dddd, symmetrisch, Diagonale 0, Summen für
  dieselben Atome, Atome wie NPA), sonst nicht gelesen + Hinweis. Bindungsbeschriftung wählbar NRT gesamt / „Wiberg-Index
  (NBO, NAO-Basis)“ / keine (`bond_source`: fehlt die gewählte Quelle, die vorhandene); Unterreiter „Wiberg“ (Bindungen ab
  Schwelle + Summen je Atom), CSV volle Matrix. „Alles auf Standard“ setzt `st["nbo"]` außer Dateien zurück. Ohne
  Zitierblock (gekürzte Ausgabe) gilt die Version des Kopfs („NBO 7.0“). Offenschalig (Folgeauftrag 2026-11-14):
  nur Dubletts; Block = Gesamtteil + „Alpha spin orbitals“ + „Beta  spin orbitals“ (sonst ablehnen). Gesamt-NPA mit 8.
  Spalte „Natural Spin Density“ (Pflicht) und Wiberg gesamt geprüft an echter ORCA-6.1.1+NBO-7.0-Ausgabe; Alpha/Beta-
  NBO-Liste und E(2) nur am NBO-6-Layout (Gaussian) geprüft -> Hinweis `nbo_open_lists`; offenschalige NRT: Hinweis,
  nicht gelesen; Gaussian weiter abgelehnt. Oberfläche: Feld „Spin“ (gesamt/α/β) nur offenschalig, Spalte Spin in
  Tabellen nur offenschalig, Atombeschriftung „natürliche Spindichte (NPA)“ mit Vorzeichen, nie „Mulliken“ (das ist der
  EPR-Tab). Werte als Text wie gedruckt;
  Hybride als sp^λ mit gedrucktem λ (s/p bei 100 %/0 %, sp^0.00 = s, übergelaufenes λ „99.99“ → Anteile wie gedruckt).
  Bindungsordnungen im Bild = NRT gesamt (nur gezeichnete Bindungen, ab Schwelle, X–H nur mit „H beschriften“), überall
  als „NRT“ benannt – die IAO-Wiberg-Ordnungen des Orbitalbilds bleiben unverändert und sind etwas anderes.
  Resonanzstrukturen nur aus der CML von NRTCML (`<FILE>-nrt.cml` neben der Ausgabe, FILE aus der NBOKEYLIST), und nur wenn
  sie passt (Elemente, Koordinaten ± 0.01 Å, erste Struktur = Gewicht von RS 1), sonst nur Tabelle mit Hinweis; Formalladungen
  = Valenzelektronen − 2·freie Paare − Σ Bindungsordnungen (nur H/B/C/N/O/F/Si/P/S/Cl/Br/I). Methodensatz: Programm,
  NBO-Version, Zitate **wie in der Ausgabe gedruckt**, Niveau (`level_of_theory` ohne „NBO“), NBOKEYLIST ohne FILE= (Pfad
  des Nutzers). E(2)-Tabelle ab `e2_min` (Standard 5 kcal/mol; Robins SI zeigt keine E(2)-Tabelle), größte zuerst; CSV
  enthält alles. Im Reaktionspfad aus (wie NICS). Beispielprojekt: `demo.make_nbo` (erfunden, Layout wie echt).

## Prüfstand (aus CLAUDE.md)
- Echte Gaussian-TD-DFT-Ausgabe noch nicht getestet (nur ORCA inkl. SOC); DFT-Tab: Gaussian-Leser mit einer Opt+Freq geprüft.
- DFT-Tab: IboView wird bewusst nicht angesteuert (eigenes Rendering, Orbitale wie IboView). Orbitale: echte ORCA-Molden-
  Datei und ORCA-Cube noch nicht gegen orca_plot geprüft (PySCF-Molden ja, inkl. g). MR-Ausgaben (ORCA 6 CASSCF/SC-NEVPT2/QD-SC-NEVPT2,
  `formats/multireference.py`) gegen synthetische Layouts und eine öffentliche ORCA-6.1.1-Ausgabe (CASSCF + DLPNO-NEVPT2) geprüft;
  SORCI (nur der DDCI3-Schritt, Energie = gedruckter STATE-Wert inkl. Davidson-Korrektur wie in der Übergangstabelle, CI-Energie daneben) gegen eine echte
  H2-Ausgabe (ORCA 6.0.1) geprüft: ohne innere Orbitale, ohne Symmetrie, ohne Spektren; im Overlay nicht wählbar. Orbitale, die beim Einlesen nicht
  orthogonal waren (`redoing schmidt`, > `MAX_SCHMIDT`), gibt der Parser als Warnung aus: ORCA endet trotzdem normal.
