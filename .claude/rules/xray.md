---
paths:
  - "elucida/tabs/xray.py"
  - "elucida/tabs/dft.py"
  - "elucida/formats/cif.py"
---

# X-Ray und Moleküldarstellung: fachliche Regeln (nicht ändern ohne Rückfrage)

- X-Ray ausrichten: Bildkoordinaten x rechts, y oben, z zum Betrachter; Bindung/Ebene über kleinste Drehung
  (`rot_between`); ChemDraw-Vorlage: RDKit-CDXML (y bereits nach oben), Schweratome, Graph-Abgleich (sonst MCS ≥ 60 %),
  Kabsch auf die 2D-Koordinaten; mehrdeutige Zuordnung melden statt still wählen.
- X-Ray: Standardabweichungen **nur aus der CIF** (`_geom_bond/_angle/_torsion`, Text unverändert, z. B. „1.392(3)“),
  **nie schätzen**; fehlt ein Wert, selbst rechnen und ohne esd markieren (Torsion: Hinweis „CONF setzen“), in Tabellen
  und Unterschrift mit Fußnote a („Calculated from the atomic coordinates; no s.u. in the CIF“, Audit P4: Transparenz).
  Symmetrie: Molekül über Bindungen × Symmetrieoperationen vervollständigen; Abgleich mit geom-Einträgen über
  Transformationen (zuerst exakt T_k = G∘S_k, sonst über die Lagen mit 2e-4 für spezielle Lagen, auch rückwärts;
  uneigentliches G kehrt das Torsionsvorzeichen um), Codes `n_klm` über `_space_group_symop_id` (555 = keine
  Translation, „n“ allein ebenso). Erzeugte Atome mit römischer Hochzahl je Operation; Symmetriecode **nie im Bild**
  (Nutzerwunsch 2.3, wirkte wie ein loses „xyz“), in den Parametertabellen (auch Word) und – wie in Acta Cryst./SI
  üblich – in der Unterschrift, wenn dort genannte Werte erzeugte Atome enthalten („Symmetry code: (i) −x, −y, −z.“,
  Audit P4). Fehlordnung Standard: PART 0 + je `disorder_assembly` der Teil mit der größten Besetzung; ohne assembly
  („.“, Olex2) je räumlich getrennte vollständige Gruppe (≥ 2 PARTs, Σ Besetzung ≈ 1, `disorder_sites`), unvollständige
  Gruppen gemeinsam (Audit P4). Ellipsoide: k = √χ²₃(p) (50 % → 1.5382), Umriss = 2×2-Block
  von R·U·Rᵀ. Aussehen Standard **wie Mercury** (Nutzerwunsch): schattierte Schichten (`shade_layers`, Licht oben
  links, matt, Schichten immer innerhalb des Umrisses, keine Clip-Pfade), H-Radius 0.09 Å, Bindungsdicke in Å
  (`bond_w`, Standard 0.12 seit 2.0, skaliert mit dem Zoom wie Mercurys Zylinder); seit 2.0 nach Nutzervorlage
  Bindungen schwarz, Labels fett ohne Rand – Elementfarben bleiben (C grau, Nutzerwunsch); „flach“ = Olex2 (fett,
  weißer Rand). Auswahl je Tab (Nutzerwunsch): X-Ray nur Mercury/Olex2 (`XRAY_STYLES`), DFT Mercury/Olex2/
  Kugel-Stab „depth“/Strichzeichnung „cartoon“/„iboview“ (`DFT_STYLES`; IboView auch ohne Orbital wählbar); alte Projekte über `allowed_style` (X-Ray → Mercury,
  DFT „ballstick“ → „depth“). „cartoon“ nach JOC-Vorlage: weiße Kugeln mit schwarzem Umriss, hohle Stäbe
  (je Bindung ein Stab, Enden am 3D-Austritt aus der Kugel, Tiefe = Bindungsmitte; Rand = Kugelumriss `_cartoon_edge`,
  Nutzerfeedback), Perspektive (`PERSPECTIVE`); „depth“ nach der Kugel-Stab-Abbildung im ORCA-6-Handbuch (gemessen: Jmol-Farben
  `ORCA_COLORS`, Licht 47°, weicher Glanzpunkt `soft`/`spot`, kein Umriss, keine Aufhellung `FOG_STYLES`).
  Labelfarbe schwarz oder Atomfarbe (`label_color`, helle Farben abgedunkelt). Kugel-Stil (`BALL_STYLES`, nach Vorlagebildern des Nutzers): „ballstick“ wie IboView (Schattenrand unten
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
- Labelgröße je Tab (`label_pt`, 0 = Textformat) in X-Ray und DFT über `label_size` in den opts von `XrayFigure`.
- X-Ray Stufe 3 (Vergleich mit Rechnung, Karte im Schritt Auswertung, Nutzerauftrag 2026-11-13): Geometrie aus dem
  Zustand des DFT-Tabs (`dft_state`, nie der Tab) oder als Datei (xyz, ORCA, Gaussian; Kopie in data/xray). Geisteratome
  (Bq/X aus NICS/ACID) fallen beim Lesen weg (`read_calc_geometry`). Zuordnung nur über den Graphen (`match_calc`):
  gleiche Schweratome, isomorphes Bindungsnetz der Schweratome; nie nach Abstand oder Reihenfolge. Passt das Gerüst
  nicht: ablehnen und die Stelle nennen (Formeln, abweichende Atome über MCS). **Andere H-Zahl an einem Schweratom wird
  gemeldet, nicht abgelehnt** (`h_diff`, Hinweis im Tab und Fußnote der Tabelle; geprüft an einer hinterlegten CIF, der
  ein H fehlte – es kann aber auch eine andere Spezies sein, deshalb nie still): überzählige H bleiben ohne Partner,
  Parameter mit ihnen bleiben leer. Mehrere Fragmente (Lösungsmittel, Ionen, Z′ > 1): Fragment wählen lassen, sonst keine
  Zuordnung; Fehlordnung: Teil über „Fehlordnung“. Unter mehreren Graph-Zuordnungen die mit der kleinsten Kabsch-RMSD der
  Schweratome (Spiegelung nur wie `DFT.kabsch`, dann Hinweis Torsionsvorzeichen); gleichwertige innerhalb `CALC_TOL`
  speichern (≤ `CALC_ALTS`) und melden, ob die gewählten Parameter gleich sind (`CALC_SAME`). RMSD unter
  `CALC_SAME_GEOM` (0.01 Å): Hinweis, dass die Rechnung ein Einzelpunkt auf den Kristallkoordinaten ist und nichts
  vergleicht. Zuordnung (`entry["calc"]["map"]`, Atom-Schlüssel → Dateiindex) wird gespeichert und beim Öffnen
  unverändert benutzt. Rechenwerte ohne Standardabweichung mit fester Stellenzahl (`CALC_DEC`: Bindungen 3
  Nachkommastellen in Å, Winkel/Torsionen 1 in °), Δ = Rechnung − Kristall wahlweise (Standard aus). Kopf = Methode wie
  `level_of_theory`, reine xyz „calc.“; Fußnote: Geometrie wie die Rechnung angibt (optimiert nur bei konvergierter
  Optimierung, Gasphase oder solvatisiert) und RMSD der Schweratome; nie das Programm. Mit Rechnung stehen die Werte
  immer in der Tabelle (auch ≤ `CAPTION_MAX`), nicht in der Bildunterschrift.
