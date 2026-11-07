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
  `ORB_MAX_DPI` 300, beim Ziehen 1/4) über den Vektor-Atomen; Verdeckung über Tiefenkarte (Nutzer-OK: Raster im PDF).
  Cube: MO aus MO-Liste/Dateiname (ORCA „mo21a“, ab 0), HOMO/LUMO aus der Ausgabe der Geometrie. Molden: eigene
  Gauß-Auswertung bis g; Konvention (Primitive normiert/roh, ORCA-Vorzeichen f/g ±3/±4) über CᵀSC = 1 gewählt,
  > 1e-3 **ablehnen**. Geprüft gegen PySCF (cc-pVTZ kartesisch/kugelförmig, def2-QZVP mit g: Werte wie deren Cubes,
  ±2e-5); echte ORCA-Molden-Datei noch ungeprüft. Gitter 0.1 Å (IboView 12/Å). Gleiche Atome/Koordinaten (± 0.02 Å)
  → an die gewählte Geometrie hängen, sonst neue Geometrie. Export: Struktur ohne Orbital + je Orbital ein Bild.
- DFT-Energieprofil/IRC/NICS (F4, `tabs/dft_pages.py`, Reiter neben „Abbildung“): Spezies = Opt/Freq-Einträge,
  Einzelpunkte nur über gleiche Atome/Koordinaten (± 0.02 Å, nie Dateinamen); G = E(SP) + (G − E_el), H analog, ΔE = E(SP);
  haben einige Spezies SP, fallen die übrigen weg (Hinweis, nie mischen); SP ohne Lösungsmittel bei SMD/CPCM-Opt nur
  Hinweis. kcal mol⁻¹, eine Nachkommastelle, echtes Minus, Bezug = erste Spezies; Unterschrift „<SP>//<Opt> level of
  theory“ (übliche Reihenfolge, Robin) mit T/p; Methode aus den „!“-Zeilen (`level_of_theory`, Schreibweise wie in der
  Eingabe). IRC nur ΔE_el (nie mit G-Stufen), x = Σ|ΔR| der Trajektorie (TS = 0) oder Bindungsspalte, verschiedene
  Methoden ablehnen. NICS = −σ_iso, NICSzz = −n·σ·n (n = Ebene der Schweratome < 2,5 Å um das Bq), Scan ab 10 Bq
  (NICS schwarz, NICSzz rot). Isowert-Bedienung wie IboView („Threshold Type“ density/absolute, absolut Standard 0.01).
