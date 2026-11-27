"""elucida/app/i18n.py - Übersetzungen DE/EN. T(key, **kw) liefert den Text in der aktiven Sprache."""
from __future__ import annotations

import os

_LANG = os.environ.get("UVVIS_LANG", "de")[:2].lower()

TEXTS = {
    # NBO (Reiter im DFT-Tab, tabs/dft_nbo.py; Leser formats/nbo.py)
    "nbo_tab": ("NBO", "NBO"),
    "nbo_card": ("NBO-Rechnungen", "NBO Calculations"),
    "nbo_display": ("NBO-Darstellung", "NBO Display"),
    "nbo_add": ("ORCA-Ausgabe mit NBO-Analyse hinzufügen …", "Add ORCA output with NBO analysis …"),
    "nbo_file": ("Datei", "File"),
    "nbo_sections": ("Abschnitte", "Sections"),
    "nbo_start": ("ORCA-6-Ausgabe mit NBO 7 laden", "Load an ORCA 6 output with NBO 7"),
    "nbo_empty": ("Keine NBO-Rechnung: im Schritt Daten eine ORCA-6-Ausgabe mit NBO 7 laden (Karte „NBO-Rechnungen“).",
                  "No NBO calculation: load an ORCA 6 output with NBO 7 in the Data step (card “NBO Calculations”)."),
    "nbo_atoms": ("Atome", "Atoms"),
    "nbo_atoms_charge": ("Natürliche Ladung (NPA)", "Natural charge (NPA)"),
    "nbo_atoms_spin": ("Natürliche Spindichte (NPA)", "Natural spin density (NPA)"),
    "nbo_col_spin": ("Spindichte (NPA)", "Spin density (NPA)"),
    "nbo_spin": ("Spin", "Spin"),
    "nbo_spin_total": ("Gesamt", "Total"),
    "nbo_spin_alpha": ("α-Spin", "α spin"),
    "nbo_spin_beta": ("β-Spin", "β spin"),
    "nbo_spin_tip": ("Offenschalig: NBO-Liste und E(2) gibt es je Spin (gesamt = α und β untereinander), Wiberg gesamt, α "
                     "oder β", "Open-shell: NBO list and E(2) exist per spin (total = α and β one below the other), Wiberg "
                     "total, α or β"),
    "nbo_wb_spin_total": ("Gesamtmatrix (α + β).", "Total matrix (α + β)."),
    "nbo_wb_spin_alpha": ("Matrix der α-Spinorbitale.", "Matrix of the α spin orbitals."),
    "nbo_wb_spin_beta": ("Matrix der β-Spinorbitale.", "Matrix of the β spin orbitals."),
    "nbo_wb_spin_missing": ("Die Matrix dieses Spins war nicht lesbar: gezeigt ist die Gesamtmatrix.",
                            "The matrix of this spin was not readable: the total matrix is shown."),
    "nbo_atoms_name": ("Atomname", "Atom name"),
    "nbo_atoms_none": ("Keine Beschriftung", "No labels"),
    "nbo_atoms_tip": ("Beschriftung der Atome aus der Natural Population Analysis der Ausgabe: natürliche Ladung oder "
                      "(offenschalig) natürliche Spindichte – nicht die Mulliken-Spinpopulation des EPR-Tabs",
                      "Atom labels from the Natural Population Analysis of the output: natural charge or (open-shell) "
                      "natural spin density – not the Mulliken spin population of the EPR tab"),
    "nbo_bonds": ("Bindungen", "Bonds"),
    "nbo_bonds_nrt": ("NRT-Bindungsordnung (gesamt)", "NRT bond order (total)"),
    "nbo_bonds_none": ("Keine Beschriftung", "No labels"),
    "nbo_bonds_tip": ("Bindungsbeschriftung aus der Ausgabe: natürliche Bindungsordnung der NRT-Analyse oder Wiberg-Index "
                      "(NBO, NAO-Basis, Schlüsselwort BNDIDX) – beide nicht die IAO-Wiberg-Bindungsordnung, die Elucida "
                      "im Orbitalbild aus einer Molden-Datei berechnet",
                      "Bond labels from the output: natural bond order of the NRT analysis or Wiberg index (NBO, NAO "
                      "basis, keyword BNDIDX) – neither is the IAO Wiberg bond order that Elucida computes for the "
                      "orbital view from a Molden file"),
    "nbo_bonds_wiberg": ("Wiberg-Index (NBO, NAO-Basis)", "Wiberg index (NBO, NAO basis)"),
    "nbo_col_wiberg": ("Wiberg-Index (NAO)", "Wiberg index (NAO)"),
    "nbo_col_wiberg_sum": ("Summe je Atom", "Total by atom"),
    "nbo_wb_note": ("Wiberg-Indizes aus der NBO-Analyse (NAO-Basis, BNDIDX) ab {thr}, wie gedruckt; die volle Matrix "
                    "steht in der CSV. Nicht die IAO-Wiberg-Bindungsordnung des Orbitalbilds.",
                    "Wiberg indices from the NBO analysis (NAO basis, BNDIDX) from {thr}, as printed; the full matrix "
                    "is in the CSV. Not the IAO Wiberg bond order of the orbital view."),
    "nbo_thr": ("Schwelle", "Threshold"),
    "nbo_thr_tip": ("Bindungsordnungen ab diesem Wert beschriften (Abbildung, Tabelle, SI)",
                    "Label bond orders from this value (figure, table, SI)"),
    "nbo_dec": ("Nachkommastellen", "Decimals"),
    "nbo_els": ("Elemente", "Elements"),
    "nbo_els_ph": ("Alle (z. B. N, O)", "All (e.g. N, O)"),
    "nbo_els_tip": ("Nur diese Elemente beschriften (durch Komma getrennt), leer = alle",
                    "Label only these elements (comma separated), empty = all"),
    "nbo_colors": ("Farben", "Colours"),
    "nbo_color_q": ("Farbe der Atomwerte", "Colour of the atom values"),
    "nbo_color_bo": ("Farbe der Bindungsordnungen", "Colour of the bond orders"),
    "nbo_e2_min": ("E(2) ab [kcal mol⁻¹]", "E(2) from [kcal mol⁻¹]"),
    "nbo_e2_min_tip": ("Tabelle E(2) und SI: nur Wechselwirkungen ab diesem Wert (die CSV enthält alle gedruckten)",
                       "E(2) table and SI: only interactions from this value (the CSV contains all printed ones)"),
    "nbo_rs_max": ("Strukturen", "Structures"),
    "nbo_rs_max_tip": ("Höchstens so viele Resonanzstrukturen der CML-Datei zeichnen (in deren Reihenfolge)",
                       "Draw at most this many resonance structures of the CML file (in its order)"),
    "nbo_show_h": ("H zeigen", "Show H"),
    "nbo_h_labels": ("H beschriften", "Label H"),
    "nbo_sub_fig": ("Abbildung", "Figure"),
    "nbo_sub_rs": ("Resonanzstrukturen", "Resonance Structures"),
    "nbo_sub_si": ("SI-Text", "SI Text"),
    "nbo_col_atom": ("Atom", "Atom"),
    "nbo_col_core": ("Rumpf", "Core"),
    "nbo_col_valence": ("Valenz", "Valence"),
    "nbo_col_total": ("Gesamt", "Total"),
    "nbo_col_lewis": ("Anteil", "Part"),
    "nbo_col_occ": ("Besetzung", "Occupancy"),
    "nbo_col_energy": ("Energie", "Energy"),
    "nbo_col_hyb": ("Hybride (Polarisation)", "Hybrids (polarization)"),
    "nbo_col_acceptor": ("Akzeptor", "Acceptor"),
    "nbo_col_weight": ("Gewicht", "Weight"),
    "nbo_col_change": ("Hinzu (entfernt) gegenüber RS 1", "Added (removed) vs. RS 1"),
    "nbo_col_bond": ("Bindung", "Bond"),
    "nbo_col_bo_t": ("Gesamt", "Total"),
    "nbo_col_bo_c": ("Kovalent", "Covalent"),
    "nbo_col_bo_i": ("Ionisch", "Ionic"),
    "nbo_lewis_total": ("Lewis gesamt", "Total Lewis"),
    "nbo_lewis_valence": ("Valenz, Nicht-Lewis", "Valence non-Lewis"),
    "nbo_lewis_rydberg": ("Rydberg, Nicht-Lewis", "Rydberg non-Lewis"),
    "nbo_others": ("Übrige", "Others"),
    "nbo_npa_note": ("Natürliche Ladungen und Populationen wie in der Ausgabe (Summary of Natural Population Analysis).",
                     "Natural charges and populations as printed (Summary of Natural Population Analysis)."),
    "nbo_list_note": ("Ohne Rumpf- (CR) und Rydberg-Orbitale (RY); alle stehen in der CSV. Hybride wie gedruckt (sp^λ "
                      "mit λ aus der Ausgabe; übergelaufene Verhältnisse als Anteile).",
                      "Without core (CR) and Rydberg (RY) orbitals; all are in the CSV. Hybrids as printed (sp^λ with "
                      "λ from the output; overflowed ratios as percentages)."),
    "nbo_e2_note": ("{n} von {m} Wechselwirkungen ab {thr} kcal mol⁻¹, größte zuerst (die Ausgabe druckt ab {out} "
                    "kcal mol⁻¹).",
                    "{n} of {m} interactions from {thr} kcal mol⁻¹, largest first (the output prints from {out} "
                    "kcal mol⁻¹)."),
    "nbo_nrt_note": ("Bindungsordnungen ab {thr} (Schwelle der Abbildung). NRT-Einstellungen: {par}.",
                     "Bond orders from {thr} (threshold of the figure). NRT settings: {par}."),
    "nbo_fig_hint": ("Ziehen dreht, Mausrad zoomt, Labels lassen sich verschieben. Bindungen: NRT-Bindungsordnung bzw. "
                     "Wiberg-Index (NBO, NAO-Basis) aus der Ausgabe – nicht die IAO-Wiberg-Bindungsordnung des Orbitalbilds.",
                     "Drag rotates, the wheel zooms, labels can be moved. Bonds: NRT bond order or Wiberg index (NBO, NAO "
                     "basis) from the output – not the IAO Wiberg bond order of the orbital view."),
    "nbo_wiberg_none": ("Wiberg-Indizes: nicht in der Ausgabe (Schlüsselwort BNDIDX in der NBOKEYLIST).",
                        "Wiberg indices: not in the output (keyword BNDIDX in the NBOKEYLIST)."),
    "nbo_wiberg_bad": ("Wiberg-Block folgt nicht dem geprüften Layout (NBO 7.0, BNDIDX): nicht gelesen.",
                       "Wiberg block does not follow the checked layout (NBO 7.0, BNDIDX): not read."),
    "nbo_not_normal": ("ORCA endete nicht normal: Werte trotzdem wie gedruckt.",
                       "ORCA did not terminate normally: values shown as printed anyway."),
    "nbo_cml_none": ("Resonanzstrukturen: {name} liegt nicht neben der Ausgabe – nur die Tabelle.",
                     "Resonance structures: {name} is not next to the output – table only."),
    "nbo_copy_tip": ("SI-Text der NBO-Analyse kopieren (für Word)", "Copy the SI text of the NBO analysis (for Word)"),
    "nbo_copied": ("NBO-SI-Text kopiert", "NBO SI text copied"),
    "nbo_none": ("Keine NBO-Analyse in der Ausgabe gefunden.", "No NBO analysis found in the output."),
    "nbo_several": ("{n} NBO-Analysen in einer Ausgabe: nicht unterstützt (ungeprüft).",
                    "{n} NBO analyses in one output: not supported (unchecked)."),
    "nbo_program": ("Nur ORCA-Ausgaben mit NBO werden gelesen (Gaussian/GENNBO-Layout ungeprüft).",
                    "Only ORCA outputs with NBO are read (Gaussian/GENNBO layout unchecked)."),
    "nbo_orca_version": ("ORCA {v}: nur ORCA 6 wird gelesen.", "ORCA {v}: only ORCA 6 is read."),
    "nbo_open_shell": ("Offenschalige NBO-Ausgabe (Multiplizität {m}): nur Dubletts im Layout von ORCA 6 + NBO 7.0 "
                       "(Gesamtteil, dann „Alpha/Beta spin orbitals“) werden gelesen.",
                       "Open-shell NBO output (multiplicity {m}): only doublets in the layout of ORCA 6 + NBO 7.0 (total "
                       "part, then “Alpha/Beta spin orbitals”) are read."),
    "nbo_nrt_open": ("NRT einer offenschaligen Rechnung: an keiner echten Ausgabe geprüft, nicht gelesen.",
                     "NRT of an open-shell calculation: not checked against a real output, not read."),
    "nbo_open_lists": ("NBO-Liste und E(2) je Spin nur am Layout von NBO 6 (Gaussian) geprüft; Werte gegen die Ausgabe "
                       "vergleichen.",
                       "NBO list and E(2) per spin checked only against the layout of NBO 6 (Gaussian); compare values "
                       "with the output."),
    "nbo_version": ("NBO {v}: nur NBO 7.0 wird gelesen (andere Versionen ungeprüft).",
                    "NBO {v}: only NBO 7.0 is read (other versions unchecked)."),
    "nbo_e2_overflow": ("E(2)-Zeile mit übergelaufenem Wert ausgelassen: {row}", "E(2) row with overflowed value skipped: {row}"),
    "nbo_nrt_several": ("Mehrere NRT-Abschnitte: NRT nicht gelesen (ungeprüft).",
                        "Several NRT sections: NRT not read (unchecked)."),
    "nbo_no_npa": ("Natural Population Analysis fehlt in der Ausgabe.", "Natural Population Analysis missing in the output."),
    "nbo_atom_count": ("NPA nennt {n} Atome, die Geometrie {m}.", "NPA lists {n} atoms, the geometry {m}."),
    "nbo_cml_bad": ("CML-Datei ohne NRT-Strukturen (Titel „Wgt=…%“).", "CML file without NRT structures (title “Wgt=…%”)."),
    "nbo_cml_atoms": ("CML-Datei passt nicht zur Ausgabe (Atome oder Koordinaten verschieden): keine Strukturen gezeichnet.",
                      "CML file does not match the output (atoms or coordinates differ): no structures drawn."),
    "nbo_cml_weight": ("CML-Datei gehört zu einer anderen NRT-Rechnung (erste Struktur {a} %, RS 1 der Ausgabe {b} %): "
                       "keine Strukturen gezeichnet.",
                       "CML file belongs to another NRT run (first structure {a} %, RS 1 of the output {b} %): no "
                       "structures drawn."),
    'rp_mr_results': ('Methode und Zustände', 'Method and states'),
    'rp_gap_convention': ('Vorzeichenkonvention', 'Sign convention'),
    'rp_layout_font': ('Schriftgröße [pt]', 'Font size [pt]'),
    'rp_connector_style': ('Linienart', 'Line style'),
    'rp_layout_x': ('Position', 'Position'),
    'rp_layout_x_tip': ('Waagerechte Lage des Plateaus in Schritten (automatisch: sein Schritt). Verschieben, damit Beschriftungen oder senkrechte Übergänge nicht kollidieren.', 'Horizontal position of the level in steps (automatic: its step). Move it so that labels or vertical transitions do not collide.'),
    'rp_plateau_width': ('Breite', 'Width'),
    'rp_plateau_width_tip': ('Länge der Plateaulinie in Schritten (automatisch 0.70).', 'Length of the level line in steps (automatic 0.70).'),
    'rp_layout_height': ('Höhe', 'Height'),
    'rp_layout_height_tip': ('Zeichenhöhe im schematischen Bild (automatisch: die Energie). Der Energiewert am Plateau bleibt unverändert.', 'Drawing height in the schematic diagram (automatic: the energy). The energy value at the level stays unchanged.'),
    'rp_break_after': ('Verbinder unterbrechen', 'Break connector'),
    'rp_break_after_long': ('Folgenden Verbinder mit Achsenbruch zeichnen', 'Draw the following connector with an axis break'),
    'rp_plateau_color': ('Farbe', 'Colour'),
    "rp_level_of": ("Plateau „{name}“: Lage, Breite und Farbe", "Level “{name}”: position, width and colour"),
    "rp_level_pick": ("Plateau in der Tabelle wählen, um Lage, Breite und Farbe zu ändern.",
                      "Select a level in the table to change its position, width and colour."),
    "rp_level_of_mr": ("Plateau „{name}“: Zustand, Lage, Breite und Farbe",
                       "Level “{name}”: state, position, width and colour"),
    "rp_level_mr": ("Methode", "Method"),
    "rp_level_mr_tip": ("Multireferenz-Ergebnis, dessen Zustandsenergie das Plateau zeigt (Vorgabe: höchste Theorie der "
                        "Datei, NEVPT2 vor CASSCF).",
                        "Multireference result whose state energy the level shows (default: highest level of theory in "
                        "the file, NEVPT2 before CASSCF)."),
    "rp_level_root": ("Zustand", "State"),
    "rp_level_root_tip": ("Zustand (Root wie gedruckt); das Profil nimmt seine Gesamtenergie, nur elektronisch.",
                          "State (root as printed); the profile uses its total energy, electronic only."),
    "rp_level_root_item": ("Root {root} · M = {mult} · {E} Eh", "Root {root} · M = {mult} · {E} Eh"),
    'rp_auto_level': ('Plateau automatisch', 'Automatic level'),
    'rp_auto_level_tip': ('Lage, Breite, Höhe und Farbe dieses Plateaus wieder automatisch (Beschriftungen: „Beschriftungen zurücksetzen“).', 'Position, width, height and colour of this level back to automatic (labels: “Reset labels”).'),
    'rp_3d_orbitals': ('3D / Orbitale', '3D / Orbitals'),
    'rp_insert': ('Einfügen', 'Insert'),
    'rp_data': ('Daten', 'Data'),
    'rp_toggle_list': ('Pfadliste ein- oder ausblenden', 'Show or hide the path list'),
    'rp_back_to_paths': ('Pfad schließen', 'Close path'),
    'rp_select_path': ('Links einen Reaktionspfad öffnen oder neu anlegen.', 'Open or create a reaction path on the left.'),
    'rp_view_source': ('3D-Quelle', '3D source'),
    'rp_load_view_source': ('Zuerst Rechendateien laden. Orbitale können unter „3D / Orbitale“ ergänzt werden.', 'Load calculation files first. Orbitals can be added under 3D / Orbitals.'),
    'rp_apply_view': ('Ansicht übernehmen', 'Apply view'),
    'rp_compose': ('Gestalten', 'Compose'),
    'rp_calculation_data': ('Rechendaten', 'Calculation Data'),
    'rp_insert_diagram': ('Aktuelles Profil einfügen', 'Insert current profile'),
    'rp_update_diagrams': ('Profile aktualisieren', 'Update profiles'),
    'rp_insert_orbital': ('3D-/Orbitalansicht einfügen …', 'Insert 3D/orbital view …'),
    'rp_geometry_only': ('Geometrie ohne Orbital', 'Geometry without orbital'),
    'rp_edit_figure': ('Bild bearbeiten …', 'Edit figure …'),
    'rp_calculation_data_sub': ('Rechnungen dieses Pfads, aus den Verbindungen oder aus Dateien', 'Calculations of this path, from the compounds or from files'),
    'rp_edit_selected': ('Gewähltes Bild bearbeiten …', 'Edit selected figure …'),
    'rp_select_figure': ('Zuerst ein Profil oder eine Orbitalansicht mit dem Auswahlwerkzeug markieren.', 'First select a profile or orbital view with the selection tool.'),
    'rp_show_diagram_frame': ('Diagrammrahmen', 'Diagram frame'),
    'rp_composition_hint': ('Profile und Bilder frei platzieren; Moleküle, Texte und Pfeile direkt zeichnen. Doppelklick auf ein Profil oder eine Orbitalansicht öffnet die Bearbeitung. Die SI übernimmt die gesamte Abbildung.', 'Place profiles and images freely; draw molecules, text and arrows directly. Double-click a profile or orbital view to edit it. SI includes the entire figure.'),
    'rp_composition_caption': ('SI-Unterschrift', 'SI caption'),
    'rp_caption_auto': ('Leer: automatisch aus den eingefügten Profilen', 'Empty: automatic caption from inserted profiles'),
    'rp_composition_reopen': ('Die Zeichnung wurde extern geändert. Bitte im Reaktionspfad öffnen und erneut speichern.', 'The drawing changed externally. Please reopen and save it in the reaction path.'),
    'rp_composition_missing_source': ('Die Quelldaten eines Bildobjekts fehlen. Bitte das Objekt neu aus den Rechendaten einfügen.', 'Source data for a figure are missing. Please insert the object again from the calculation data.'),
    'rp_composition_stale': ('Die Rechendaten wurden geändert. Bitte im Reaktionspfad unter „Gestalten“ auf „Profile aktualisieren“ klicken.', 'Calculation data changed. In the reaction path, choose Compose → Update profiles.'),
    'rp_calculations_and_orbitals_of_this_path': ('Rechnungen und Orbitale dieses Pfads', 'Calculations and Orbitals of This Path'),
    'rp_close': ('Schließen', 'Close'),
    'rp_energy_profiles_and_irc_across_multiple_compounds': ('Stufenprofile und IRC über mehrere Verbindungen hinweg.', 'Energy profiles and IRC across multiple compounds.'),
    'rp_export_profile': ('Profil exportieren', 'Export profile'),
    'rp_import_calculations': ('Rechnungen übernehmen', 'Import Calculations'),
    'rp_import_from_compounds': ('Aus Verbindungen übernehmen …', 'Import from compounds …'),
    'rp_load_calculation_files': ('Neue Rechendateien laden …', 'Load calculation files …'),
    'rp_new_path': ('Neuer Pfad …', 'New path …'),
    'rp_new_reaction_path': ('Neuer Reaktionspfad', 'New Reaction Path'),
    'rp_no_dft_calculations_have_been_loaded_in_the_compounds_yet': ('In den Verbindungen sind noch keine DFT-Rechnungen geladen.', 'No DFT calculations have been loaded in the compounds yet.'),
    'rp_open': ('Öffnen', 'Open'),
    'rp_orbitals_individual_calculations': ('Orbitale / Einzelrechnungen …', 'Orbitals / individual calculations …'),
    'rp_reaction_path': ('Reaktionspfad', 'Reaction Path'),
    'rp_computational_chemistry': ('Computerchemie', 'Computational Chemistry'),
    'rp_reaction_paths': ('Reaktionspfade', 'Reaction Paths'),
    'rp_rename_path': ('Pfad umbenennen', 'Rename Path'),
    'rp_restore': ('Wiederherstellen …', 'Restore …'),
    'rp_restore_path': ('Pfad wiederherstellen', 'Restore Path'),
    'rp_saved_automatically_in_the_project_imports_are_independent_copies': ('Automatisch gespeichert im Projekt · Übernahmen sind eigenständige Kopien.', 'Saved automatically in the project · Imports are independent copies.'),
    'rp_view_zoom': ('Ansichtszoom', 'View zoom'),
    'rp_choose_orbital': ('Orbital wählen', 'Choose Orbital'),
    'rp_choose_structure_image': ('Struktur/Bild wählen …', 'Choose structure/image …'),
    'rp_draw_in_octet': ('Octet zeichnen …', 'Draw in Octet …'),
    'rp_each_image_belongs_to_a_level_or_irc_point_octet_drawings_and_independ': ('Jedes Bild gehört zu einer Stufe oder einem IRC-Punkt. Octet-Zeichnungen und eigene Orbitalansichten können am selben Punkt stehen. Versatz und Breite beziehen sich auf die Diagrammfläche.', 'Each image belongs to a level or IRC point. Octet drawings and independent orbital views can share a point. Offset and width are fractions of the plotting area.'),
    'rp_edit': ('Bearbeiten …', 'Edit …'),
    'rp_first_load_a_cube_or_molden_file_in_the_dft_tab_and_select_an_orbital': ('Zuerst im DFT-Tab eine Cube- oder Molden-Datei laden und ein Orbital wählen.', 'First load a Cube or Molden file in the DFT tab and select an orbital.'),
    'rp_horizontal_offset': ('Versatz horizontal', 'Horizontal offset'),
    'rp_image_anchor_missing_from_current_profile': ('Bildanker nicht im aktuellen Profil: ', 'Image anchor missing from current profile: '),
    'rp_image_unreadable': ('Bild nicht lesbar', 'Image unreadable'),
    'rp_level': ('Stufe: ', 'Level: '),
    'rp_missing_anchor': ('Anker fehlt', 'Missing anchor'),
    'rp_octet_drawing': ('Octet-Zeichnung', 'Octet drawing'),
    'rp_orbital_view': ('Orbitalansicht …', 'Orbital view …'),
    'rp_reaction_profile_images': ('Bilder im Reaktionsprofil', 'Reaction Profile Images'),
    'rp_structure_image': ('Struktur/Bild', 'Structure/Image'),
    'rp_vertical_offset': ('Versatz vertikal', 'Vertical offset'),
    'rp_width': ('Breite', 'Width'),
    'rp_density_fraction': ('Dichteanteil [%]', 'Density fraction [%]'),
    'rp_drag_rotate_right_button_pan_wheel_zoom_this_view_remains_independent': ('Ziehen: drehen · rechte Taste: verschieben · Mausrad: zoomen. Diese Ansicht bleibt eigenständig.', 'Drag: rotate · right button: pan · wheel: zoom. This view remains independent.'),
    'rp_isovalue_a_u': ('Isowert [a.u.]', 'Isovalue [a.u.]'),
    'rp_load_an_available_orbital_first': ('Zuerst ein verfügbares Orbital laden.', 'Load an available orbital first.'),
    'rp_profile_orbital_view': ('Orbitalansicht im Profil', 'Profile Orbital View'),
    'rp_the_orbital_file_changed_please_capture_a_new_view': ('Die Orbitaldatei wurde geändert. Ansicht bitte neu übernehmen.', 'The orbital file changed. Please capture a new view.'),
    'rp_include_selected_result_in_si': ('Gewähltes Ergebnis in SI', 'Include selected result in SI'),
    'rp_no_multireference_result_selected_supported_orca_6_casscf_sc_nevpt2_an': ('Kein Multireferenzergebnis gewählt. Unterstützt: ORCA 6 CASSCF, SC-\u2060NEVPT2, QD-\u2060SC-\u2060NEVPT2 und SORCI.', 'No multireference result selected. Supported: ORCA 6 CASSCF, SC-\u2060NEVPT2, QD-\u2060SC-\u2060NEVPT2 and SORCI.'),
    'rp_select_a_method_and_result_block_explicitly_energies_and_weights_retai': ('Methode und Ergebnisblock explizit wählen. Energien und Gewichte bleiben wie in der Ausgabe. Orbitalbesetzungen ohne eindeutige Zustandszuordnung werden nicht als Diradikalcharakter ausgegeben.', 'Select a method and result block explicitly. Energies and weights retain output precision. Occupations without an unambiguous state assignment are not reported as diradical character.'),
    'rp_select_result': ('Ergebnis wählen …', 'Select result …'),
    'rp_select_singlet': ('Singulett wählen …', 'Select singlet …'),
    'rp_select_triplet': ('Triplett wählen …', 'Select triplet …'),
    'rp_add_level': ('Stufe hinzufügen', 'Add Level'),
    'rp_export_cm': ('Export [cm]', 'Export [cm]'),
    'rp_large_workspace': ('Große Arbeitsfläche …', 'Large workspace …'),
    'rp_profile_images': ('Bilder im Profil …', 'Profile images …'),
    'rp_reaction_profile_workspace': ('Reaktionsprofil – Arbeitsfläche', 'Reaction Profile Workspace'),
    'rp_remove_irc_curve': ('IRC-Kurve entfernen', 'Remove IRC curve'),
    'rp_remove_level_from_profile': ('Stufe aus Profil entfernen', 'Remove level from profile'),
    'rp_restore_removed_level': ('Entfernte Stufe hinzufügen …', 'Restore removed level …'),
    'rp_multireference': ('Multireferenz', 'Multireference'),
    'rp_reaction_paths_in_computational_section': ('Reaktionspfade im CompChem-Kapitel', 'Reaction paths in Computational Section'),
    'rp_before_individual_calculations': ('Vor den Einzelrechnungen', 'Before individual calculations'),
    'rp_after_individual_calculations': ('Nach den Einzelrechnungen', 'After individual calculations'),
    "draw_saving": ("Speichert …", "Saving …"),
    'draw_canvas': ('Zeichenfläche', 'Canvas'),
    'draw_canvas_dark': ('Canvas dunkel', 'Dark canvas'),
    'draw_follow_theme': ('App-Design folgen', 'Follow app theme'),
    'draw_export_files': ('Als CDXML / CDX exportieren …', 'Export as CDXML / CDX …'),
    'draw_save_failed': ('Speichern fehlgeschlagen', 'Save failed'),
    'draw_copy_table': ('Aus Octet-Tabelle übernehmen', 'Copy from Octet table'),
    'draw_invalid_mw': ('Bitte eine positive Molmasse eingeben oder das Feld leer lassen.', 'Enter a positive molar mass or leave the field empty.'),
    'draw_take_from': ('Übernehmen aus …', 'Import from …'),
    'draw_no_table': ('Zuerst in Octet eine Stöchiometrietabelle erzeugen.', 'Create a stoichiometry table in Octet first.'),
    'draw_choose_table': ('Welche Reaktionstabelle?', 'Which reaction table?'),
    'draw_no_si': ('Kein oberstes Reaktionsschema für die SI erkannt. Bitte Reaktionspfeil, Edukte und Produkte im Editor prüfen.', 'No top reaction found for SI. Check the reaction arrow, reactants and products in the editor.'),
    'draw_synthesis_of': ('Synthese von', 'Synthesis of'),
    'draw_procedure': ('Vorgang / Prozedur', 'Procedure'),
    'draw_files': ('Dateien & ChemDraw', 'Files & ChemDraw'),
    'draw_more_amounts': ('Weitere Mengenfelder', 'More quantity fields'),
    'draw_into_text': ('In Text', 'Into text'),
    'draw_reagent_options': ('Rolle und Mengenfelder', 'Role and quantity fields'),
    'draw_title': ('Zeichnung bearbeiten', 'Edit Drawing'),
    'draw_check': ('Struktur prüfen', 'Check Structure'),
    'draw_cleanup': ('Clean up', 'Clean Up'),
    'draw_name': ('Name → Struktur', 'Name → Structure'),
    'draw_save': ('Übernehmen', 'Apply'),
    'draw_enlarge': ('Vergrößern', 'Enlarge'),
    'draw_loading': ('Zeicheneditor wird geladen …', 'Loading drawing editor …'),
    'draw_discard_close': ('Die Zeichnung konnte nicht gespeichert werden. Schließen und die Änderungen verwerfen? '
                           'Vorher lässt sich über ⋯ eine Kopie exportieren.',
                           'The drawing could not be saved. Close and discard the changes? '
                           'You can export a copy from the ⋯ menu first.'),
    'draw_table_isomers': ('Die Tabelle enthält gleiche Formeln. Sie werden nur nach ihrer Spalte zugeordnet: '
                           'bitte Namen und Mengen prüfen.',
                           'The table contains identical formulas. They are matched by column only: '
                           'please check names and amounts.'),
    'rp_import_failed': ('{name}: Quelldatei fehlt, nichts übernommen ({error}).',
                         '{name}: source file missing, nothing imported ({error}).'),
    'draw_invalid': ('Die Zeichnung ist ungültig oder beschädigt.', 'The drawing is invalid or damaged.'),
    'draw_too_large': ('Die Zeichnung ist zu groß.', 'The drawing is too large.'),
    'draw_load_error': ('Der Zeicheneditor konnte nicht geladen werden.', 'The drawing editor could not be loaded.'),
    'draw_unsaved': ('Ungespeicherte Zeichnung', 'Unsaved drawing'),
    'draw_saved': ('Zeichnung gespeichert', 'Drawing saved'),
    'draw_draft_saved': ('Entwurf gespeichert · Mit OK übernehmen', 'Draft saved · Confirm with OK'),
    'draw_properties_unavailable': ('Zeichnung gespeichert · Formel oder Molmasse nicht bestimmbar. Bitte Struktur prüfen.',
                                     'Drawing saved · Formula or molar mass unavailable. Please check the structure.'),
    'draw_conflict': ('Die Datei wurde außerhalb des Editors geändert. Bitte Zeichnung separat sichern und neu öffnen.', 'The file changed outside the editor. Save a separate copy and reopen it.'),
    'draw_lossy': ('Octet kann Teile dieser Datei nicht darstellen. Das Original wird nicht überschrieben; bitte über ⋯ eine separate Kopie exportieren.', 'Octet cannot represent parts of this file. The original is protected; export a separate copy via ⋯.'),
    'draw_no_file': ('Zuerst eine Verbindung öffnen.', 'Open a compound first.'),
    'draw_build_missing': ('Editor fehlt. Bitte tools/build_octet.py ausführen.', 'Editor is missing. Run tools/build_octet.py.'),
    'draw_open': ('In Elucida zeichnen', 'Draw in Elucida'),
    'draw_reload': ('Datei neu laden', 'Reload File'),

    # ---- Kern / Log ------------------------------------------------------
    "no_conc_in_name": ("Probe '{name}': keine Konzentration im Namen",
                        "sample '{name}': no concentration in name"),
    "no_baseline_window": ("WARNUNG: kein Basislinienfenster gefunden – keine Korrektur",
                           "WARNING: no baseline window found – no correction"),
    "baseline_window": ("Basislinie: Fenster {a:.0f}–{b:.0f} nm, Offsets {offs}",
                        "Baseline: window {a:.0f}–{b:.0f} nm, offsets {offs}"),
    "baseline_kept": ("Basislinie: im Fenster absorbiert die Probe noch ({k:.4f} pro {u}) – "
                      "dieser Anteil bleibt erhalten",
                      "Baseline: sample still absorbs in the window ({k:.4f} per {u}) – "
                      "this part is kept"),
    "r2_hidden": ("{lam:g} nm: R² = {r2:.3f} < {min:g} – nicht im Bild",
                  "{lam:g} nm: R² = {r2:.3f} < {min:g} – not shown in figure"),
    "hdr_intercept": ("Achsenabschn.", "intercept"),
    "no_fit": ("kein Fit: zu wenige Punkte unter A = {cut:g} ({n}, min. {min})",
               "no fit: too few points below A = {cut:g} ({n}, min. {min})"),
    "few_points": ("nur {n} Punkte im Fit", "only {n} points in fit"),
    "no_fit_conc": ("kein Fit: alle Konzentrationen gleich", "no fit: all concentrations are equal"),
    "baseline_outside": ("Basislinienfenster {a:g}–{b:g} nm liegt nicht in allen Spektren – keine Korrektur",
                         "baseline window {a:g}–{b:g} nm is not inside every spectrum – no correction"),
    "intercept_sig": ("Achsenabschnitt {b:.3g} ± {e:.2g} signifikant ≠ 0 (Basislinie/Nichtlinearität?)",
                      "intercept {b:.3g} ± {e:.2g} significantly ≠ 0 (baseline/non-linearity?)"),
    "inset_shrunk": ("Hinweis: Inset auf {f:.0%}{tab}, um Platz zu finden",
                     "Note: inset scaled to {f:.0%}{tab} to find space"),
    "without_table": (" ohne Tabelle", " without table"),
    "image_shrunk": ("Hinweis: '{key}' auf {f:.0%} verkleinert, um Platz zu finden",
                     "Note: '{key}' scaled to {f:.0%} to find space"),
    "no_space": ("WARNUNG: kein freier Platz für '{key}' – liegt über Spektren, bitte verschieben",
                 "WARNING: no free space for '{key}' – overlaps spectra, please move it"),
    "overlap": ("WARNUNG: Überlappung {pair} – bitte verschieben",
                "WARNING: overlap {pair} – please move"),
    "saved": ("gespeichert: {p}", "saved: {p}"),
    "series_head": ("=== {tag}: {n} Spektren, d = {d:g} cm, c in {u} ===",
                    "=== {tag}: {n} spectra, d = {d:g} cm, c in {u} ==="),
    "no_mw": ("WARNUNG: keine Molmasse -> Ausgabe als spezifischer Absorptionskoeffizient "
              "a [L g⁻¹ cm⁻¹], NICHT ε",
              "WARNING: no molar mass -> reported as specific absorption coefficient "
              "a [L g⁻¹ cm⁻¹], NOT ε"),
    "peaks_found": ("automatisch gefundene Banden: {l} nm", "automatically found bands: {l} nm"),
    "cary_series": ("Cary-Datei {name}: Serien {s}", "Cary file {name}: series {s}"),
    "mixed_units": ("Serie {g}: gemischte Einheiten {u}", "series {g}: mixed units {u}"),
    "bg_none": ("WARNUNG: keine Freistellungsmethode verfügbar – Hintergrund bleibt",
                "WARNING: no background removal method available – background kept"),
    "bg_implausible": ("Freistellung mit {m} unplausibel ({f:.0%} Objektfläche), nächste Methode",
                       "background removal with {m} implausible ({f:.0%} object area), trying next"),
    "bg_failed": ("Freistellung mit {m} fehlgeschlagen: {e}", "background removal with {m} failed: {e}"),
    "bg_giveup": ("WARNUNG: Hintergrund konnte nicht entfernt werden ({e})",
                  "WARNING: background could not be removed ({e})"),
    "need_rdkit": ("CDXML braucht RDKit (pip install rdkit)", "CDXML requires RDKit (pip install rdkit)"),
    "cdxml_unsanitized": ("Struktur chemisch nicht vollständig interpretierbar – Molmasse nicht berechnet",
                          "structure could not be fully interpreted – molar mass not computed"),
    "cdxml_empty": ("{name}: keine Struktur in CDXML gefunden", "{name}: no structure found in CDXML"),
    "cdxml_fragments": ("{n} Fragmente – Molmasse ist die Summe (Salz/Gegenion?)",
                        "{n} fragments – molar mass is the sum (salt/counter-ion?)"),
    "cdxml_label_unknown": ("Beschriftung „{names}“ nicht aufgelöst (kein Element, keine Atome dahinter) – Summenformel und "
                            "Molmasse bitte im Tab Verbindung eintragen",
                            "Label “{names}” not resolved (no element, no atoms behind it) – please enter formula and "
                            "molar mass in the Compound tab"),
    "cdxml_charge_ambiguous": ("Ladung von „{names}“ mehrdeutig – Leerzeichen vor die Ladung setzen (z. B. SO4 2-); "
                               "Summenformel und Ladungsbilanz bleiben leer",
                               "Charge of “{names}” is ambiguous – put a space before the charge (e.g. SO4 2-); "
                               "formula and charge balance stay empty"),
    "cdxml_dummies": ("Platzhalteratome (Abkürzung wie Dipp/Mes nicht aufgelöst?): {n} – Molmasse bitte manuell "
                      "eingeben",
                      "Placeholder atoms (abbreviation like Dipp/Mes not expanded?): {n} – please enter molar mass "
                      "manually"),
    "cdxml_redrawn": ("Zeichnung von RDKit neu erzeugt (weicht von ChemDraw ab). Für das Original "
                      "die Struktur in ChemDraw zusätzlich als „{name}.svg“, „.pdf“ oder „.png“ "
                      "neben die CDXML speichern.",
                      "Drawing regenerated by RDKit (differs from ChemDraw). For the original, also "
                      "save the structure from ChemDraw as “{name}.svg”, “.pdf” or “.png” next to the CDXML."),
    "cdxml_drawn": ("Gezeichnet aus den Koordinaten der CDXML (wie in ChemDraw, Schrift Helvetica). Exakt: „{name}.svg“ "
                    "oder „.pdf“ aus ChemDraw daneben speichern.", "Drawn from the CDXML coordinates (as in ChemDraw, "
                    "Helvetica font). Exact: save “{name}.svg” or “.pdf” from ChemDraw next to it."),
    "cdxml_own_failed": ("Eigene Zeichnung nicht möglich ({what}).", "Own drawing not possible ({what})."),
    "cdxml_draw_failed": ("RDKit kann die Struktur nicht zeichnen ({e}) – Zeichnung in ChemDraw prüfen.",
                          "RDKit cannot draw the structure ({e}) – check the drawing in ChemDraw."),
    "drawing_from": ("Zeichnung: Original aus {name}", "Drawing: original from {name}"),
    "files_loaded": ("{n} Dateien: {names}", "{n} files: {names}"),
    "cdx_binary": ("Binäres .cdx wird nicht gelesen – in ChemDraw als .cdxml oder .svg speichern",
                   "binary .cdx is not supported – save as .cdxml or .svg in ChemDraw"),
    "need_pymupdf": ("SVG/PDF/CDXML brauchen PyMuPDF", "SVG/PDF/CDXML require PyMuPDF"),
    "need_heif": ("{name}: für HEIC/HEIF wird pillow-heif benötigt", "{name}: HEIC/HEIF requires pillow-heif"),
    "bad_image": ("{name}: Bildformat nicht lesbar ({e})", "{name}: image format not readable ({e})"),
    "model_missing": ("ISNet-Modell nicht vorhanden", "ISNet model not available"),
    "download_cancelled": ("Download abgebrochen", "download cancelled"),

    # ---- GUI -------------------------------------------------------------
    "app_title": ("Elucida", "Elucida"),
    "menu_file": ("&Datei", "&File"),
    "menu_lang": ("&Sprache", "&Language"),
    "menu_help": ("&Hilfe", "&Help"),
    "act_open": ("Messdaten öffnen …", "Open measurement data …"),
    "act_new_project": ("Neue Verbindung …",
                        "New compound …"),
    "act_save_copy": ("Verbindung als Kopie speichern …",
                      "Save compound copy …"),
    "act_show_folder": ("Ordner der Verbindung anzeigen",
                        "Show compound folder"),
    "act_show_folder_tip": ("Ordner der Verbindung im {fm} öffnen (SI, Abbildungen, Tabellen, Messdaten)",
                            "Open the compound folder in {fm} (SI, figures, tables, data)"),
    "fm_finder": ("Finder", "Finder"),
    "fm_explorer": ("Explorer", "Explorer"),
    "fm_linux": ("Dateimanager", "file manager"),
    "no_project_title": ("keine Verbindung",
                         "no compound"),
    "need_project_q": ("Für die Auswertung wird ein Ordner für die Verbindung benötigt. Eingelesene Dateien werden dort "
                       "hineinkopiert (data/, structures/), Exporte landen in SI/, figures/ und tables/.\n\nJetzt einen "
                       "Ordner wählen oder neu anlegen?",
                       "A compound folder is needed. Loaded files are copied into it (data/, structures/) and exports go to "
                       "SI/, figures/ and tables/.\n\nChoose or create a folder now?"),
    "choose_project_dir": ("Ordner der Verbindung wählen oder neu anlegen",
                           "Choose or create compound folder"),
    "make_project_q": ("{p} ist noch keine Verbindung. Hier eine neue Verbindung anlegen?",
                       "{p} is not a compound yet. Create a new compound here?"),
    "project_created": ("Verbindung angelegt: {p}",
                        "Compound created: {p}"),
    "file_imported": ("{src} in die Verbindung kopiert: {dst}",
                      "{src} copied into the compound: {dst}"),
    "autosaved": ("Gespeichert",
                  "Saved"),
    "report_locked": ("{p} ist geöffnet (z. B. in Excel) und konnte nicht überschrieben werden.",
                      "{p} is open (e.g. in Excel) and could not be overwritten."),
    "act_open_project": ("Öffnen …",
                         "Open …"),
    "act_recent": ("Zuletzt geöffnet",
                   "Recently opened"),
    "act_save_project": ("Speichern",
                         "Save"),
    "act_save_project_as": ("Speichern unter …",
                            "Save as …"),
    "menu_edit": ("&Bearbeiten", "&Edit"),
    "act_undo": ("Rückgängig", "Undo"),
    "act_redo": ("Wiederholen", "Redo"),
    "untitled": ("Unbenannte Verbindung",
                 "Untitled compound"),
    "save_changes_q": ("Die Verbindung enthält ungespeicherte Änderungen. Speichern?",
                       "The compound has unsaved changes. Save?"),
    "flt_project": ("Ordner der Verbindung (*)",
                    "Compound folder (*)"),
    "no_project": ("Keine Elucida-Verbindung und kein Projekt: {p}",
                   "Not an Elucida compound or project: {p}"),
    "missing_file": ("Datei fehlt: {p}", "File missing: {p}"),
    "project_dir_not_empty": ("Der Ordner {p} ist nicht leer und keine Verbindung – bitte einen neuen Namen wählen.",
                              "Folder {p} is not empty and not a compound – please choose a new name."),
    "project_saved": ("Verbindung gespeichert: {p}",
                      "Compound saved: {p}"),
    "act_export": ("Exportieren (aktueller Tab)", "Export (current tab)"),
    "menu_eps": ("UV-Vis (ε)", "UV-Vis (ε)"),
    "act_quit": ("Beenden", "Quit"),
    "act_about": ("Über", "About"),
    "lang_restart": ("Die Sprache wird sofort umgestellt.", "Language switched."),
    "grp_data": ("Daten", "Data"),
    "no_file": ("keine Datei geladen", "no file loaded"),
    "series": ("Serie", "Series"),
    "conc_list": ("Messungen", "Measurements"),
    "conc_col": ("Konzentration", "Concentration"),
    "conc_col_unit": ("Einheit", "Unit"),
    "cluster_jobs": ("Jobs", "Jobs"),
    "cluster_st_running": ("läuft", "running"),
    "cluster_st_pending": ("wartet", "waiting"),
    "cluster_st_done": ("fertig", "finished"),
    "cluster_summary": ("{r} laufen, {w} wartet", "{r} running, {w} waiting"),
    "cluster_as_of": ("Stand {t}", "as of {t}"),
    "cluster_job_files": ("{job}: Dateien im Ordner des Jobs, Ziel ist eine Verbindung oder ein Reaktionspfad.",
                          "{job}: files in the job folder; the target is a compound or a reaction path."),
    "xr_frag_no": ("Nr.", "No."),
    "xr_frag_formula": ("Formel", "Formula"),
    "xr_frag_kind": ("Art", "Type"),
    "cluster_col_file": ("Datei", "File"),
    "cluster_col_size": ("Größe", "Size"),
    "conc_list_tip": ("Abgewählte Konzentrationen zählen nirgends mit: nicht im Bild, nicht im Fit, nicht in Tabellen und SI.\n"
                      "Die Messdatei bleibt unverändert.",
                      "Unticked concentrations count nowhere: not in the figure, the fit, tables or the SI.\n"
                      "The data file stays unchanged."),
    "conc_last": ("Mindestens eine Messung bleibt in der Serie.", "At least one measurement stays in the series."),
    "grp_compound": ("Verbindung", "Compound"),
    "structure": ("Struktur", "Structure"),
    "photo": ("Küvettenfoto", "Cuvette photo"),
    "choose": ("Wählen …", "Choose …"),
    "remove": ("Entfernen", "Remove"),
    "molar_mass": ("Molmasse [g mol⁻¹]", "Molar mass [g mol⁻¹]"),
    "molar_mass_short": ("Molmasse", "Molar mass"),
    "img_size_struct": ("Größe Struktur", "Structure size"),
    "img_size_photo": ("Größe Foto", "Photo size"),
    "adv_images": ('Bildgrößen und Freistellung', 'Image Sizes and Background'),
    "adv_eval": ('Erweitert: min. Punkte, min. R², Schultern', 'Advanced: Min. Points, Min. R², Shoulders'),
    "adv_plot": ('Inset, Fehler, R²-Anzeige, Formate', 'Inset, Errors, R² Display, Formats'),
    "adv_changed": ("geändert", "changed"),
    "menu_theme": ("Erscheinungsbild", "Appearance"),
    "menu_ui_scale": ("Oberflächengröße", "Interface Size"),
    "ui_scale_value": ("{v} %", "{v}%"),
    "ui_scale_note": ("Gilt nach dem Neustart, nur auf diesem Rechner", "Applies after restart, on this computer only"),
    "ui_scale_restart": ("Oberflächengröße {v} %: gilt nach dem Neustart von Elucida", "Interface size {v}%: applies after restarting Elucida"),
    "restart_now": ("Jetzt neu starten", "Restart Now"),
    "restart_failed": ("Elucida ließ sich nicht neu starten. Bitte von Hand neu starten.",
                       "Could not restart Elucida. Please restart it manually."),
    "move_up": ("Nach oben", "Move up"),
    "move_down": ("Nach unten", "Move down"),
    "toolbar": ("Werkzeugleiste", "Toolbar"),
    "theme_system": ("wie System", "follow system"),
    "theme_light": ("hell", "light"),
    "theme_dark": ("dunkel", "dark"),
    "theme_now_dark": ("Dunkles Design – klicken für hell", "Dark theme – click for light"),
    "theme_now_light": ("Helles Design – klicken für dunkel", "Light theme – click for dark"),
    "canvas_now_dark": ("Canvas dunkel", "Canvas dark"),
    "canvas_now_light": ("Canvas hell", "Canvas light"),
    "canvas_toggle_tip": ("Zeichenfläche und Vorschau hell oder dunkel anzeigen (nur Anzeige, der Export bleibt gleich) – klicken zum Umschalten",
                          "Show drawing area and preview light or dark (display only, exports stay the same) – click to switch"),
    "empty_title": ("Messdaten hierher ziehen", "Drop measurement data here"),
    "empty_formats": ("Cary-CSV, DSW/BSW, Eclipse-CSV oder Ordner einer Verbindung\nKonzentration aus dem Probennamen, z. "
                      "B. ABC-1-0p5mgml_THF = 0,5 mg mL⁻¹ (sonst Tabelle zum Eintragen)",
                      "Cary CSV, DSW/BSW, Eclipse CSV or compound folder\nConcentration from the sample name, e.g. "
                      "ABC-1-0p5mgml_THF = 0.5 mg mL⁻¹ (otherwise a table to fill in)"),
    "mw_from_cdxml": ("aus CDXML", "from CDXML"),
    "mw_hint_none": ("Leer = spezifischer Koeffizient a statt ε", "Empty = specific coefficient a instead of ε"),
    "bg_method": ("Freistellung", "Background"),
    "bg_auto": ("Automatisch", "Automatic"),
    "bg_isnet": ("KI (ISNet)", "AI (ISNet)"),
    "bg_grabcut": ("GrabCut", "GrabCut"),
    "bg_border": ("Randfarbe", "Border colour"),
    "bg_off": ("Keine", "None"),
    "grp_eval": ("Auswertung", "Analysis"),
    "path_length": ("Schichtdicke [cm]", "Path length [cm]"),
    "path_length_short": ("Schichtdicke", "Path length"),
    "cutoff": ("Fit-Cutoff A", "Fit cutoff A"),
    "cutoff_tip": ("Messpunkte mit höherer Absorbanz gehen nicht in den Fit ein (Detektor nicht mehr linear).\n"
                   "Je Bande änderbar: Doppelklick auf „Cutoff A“ in der Ergebnistabelle.",
                   "Points with higher absorbance are left out of the fit (detector no longer linear).\n"
                   "Per band: double-click “Cutoff A” in the results table."),
    "min_points": ("min. Punkte", "min. points"),
    "r2_below": ("R² < {min:g} – Bande wird nicht im Bild gezeigt (Schwelle: Auswertung → Erweitert → min. R² fürs Bild)",
                 "R² < {min:g} – band not shown in the figure (threshold: Analysis → Advanced → min. R² for figure)"),
    "min_r2": ("min. R² fürs Bild", "min. R² for figure"),
    "r2_digits": ("R²-Stellen", "R² decimals"),
    "r2_digits_tip": ("Nachkommastellen von R² in Tabelle, Abbildung und SI-Texten; gilt für alle Tabs dieser Verbindung "
                      "(UV-Vis, CV, SEC, EPR). CSV und Excel-Report behalten den vollen Wert.",
                      "Decimal places of R² in table, figure and SI texts; applies to all tabs of this compound "
                      "(UV-Vis, CV, SEC, EPR). CSV and Excel report keep the full value."),
    "min_r2_tip": ("Banden mit kleinerem R² stehen in Tabelle, CSV und Excel-Report, aber nicht in der Abbildung. 0 = alle zeigen.",
                   "Bands with a lower R² are listed in the table, CSV and Excel report but not shown in the figure. 0 = show all."),
    "wavelengths": ("Banden [nm]", "Bands [nm]"),
    "wavelengths_ph": ("Z. B. Schultern: 350, 660", "E.g. shoulders: 350, 660"),
    "baseline": ("Basislinie", "Baseline"),
    "baseline_tip": ("Wird vor dem Fit von jedem Spektrum abgezogen, gemessen in einem Fenster, in dem die Probe kaum "
                     "absorbiert.\nautomatisch (Reihe): nur der konzentrationsunabhängige Versatz (Restabsorption der "
                     "Probe bleibt)\nautomatisch (einfach): der ganze Wert im Fenster\nmanuelles Fenster: Bereich "
                     "darunter selbst wählen",
                     "Subtracted from every spectrum before the fit, measured in a window where the sample barely "
                     "absorbs.\nautomatic (series): only the concentration-independent offset (residual absorption of "
                     "the sample stays)\nautomatic (simple): the whole value in the window\nmanual window: choose the "
                     "range below"),
    "bl_series": ("Automatisch (Reihe)", "Automatic (series)"),
    "bl_simple": ("Automatisch (einfach)", "Automatic (simple)"),
    "bl_manual": ("Manuelles Fenster", "Manual window"),
    "bl_off": ("Aus", "Off"),
    "grp_plot": ("Darstellung", "Plot"),
    "ymax": ("y-Achse max", "y axis max"),
    "r2_mode": ("R² anzeigen", "Show R²"),
    "r2_legend": ("In Inset-Legende (wenn keine Tabelle)", "In inset legend (if no table)"),
    "r2_label": ("Im Bandenlabel", "In band label"),
    "r2_off": ("Aus", "Off"),
    "show_err": ("ε mit Fehler", "ε with error"),
    "conc_colors": ("Konzentrationen farbig", "Concentrations in colour"),
    "conc_legend": ("Legende", "Legend"),
    "conc_legend_tip": ("Legende mit den Konzentrationen im Bild (mit der Maus verschiebbar)",
                        "Legend with the concentrations in the figure (can be dragged)"),
    "conc_col_color": ("Farbe", "Colour"),
    "conc_colors_reset": ("Farben zurücksetzen", "Reset colours"),
    "conc_enter": ("Konzentrationen fehlen: links unter „Konzentrationen eingeben“ eintragen.",
                   "Concentrations are missing: enter them on the left under “Enter concentrations”."),
    "conc_colors_long": ("Konzentrationen in Farben (mit Legende)", "Concentrations in colours (with legend)"),
    "inset_show": ("Regression (Inset)", "Regression (inset)"),
    "inset_show_long": ("Regression (Inset) anzeigen", "Show regression (inset)"),
    "inset_table": ("Tabelle im Inset", "Table in inset"),
    "btn_update": ("Aktualisieren", "Update"),
    "btn_reset_layout": ("Layout zurücksetzen", "Reset layout"),
    "btn_reset": ("Zurücksetzen", "Reset"),
    "btn_reset_defaults": ("Darstellung zurücksetzen", "Reset display"),
    "btn_clear_tab": ("Tab leeren (Daten und Einstellungen)", "Clear Tab (Data and Settings)"),
    "btn_clear_tab_tip": ("Entfernt alle geladenen Dateien aus diesem Tab und setzt seine Einstellungen auf Standard,\n"
                          "wie bei einem neuen Tab. Die Dateien bleiben im Ordner der Verbindung. Rückgängig mit Strg+Z.",
                          "Removes all loaded files from this tab and resets its settings to defaults,\n"
                          "like a new tab. The files stay in the compound folder. Undo with Ctrl+Z."),
    "btn_clear_compound_tip": ("Leert alle Angaben zur Verbindung außer dem Namen (Summenformel, Molmasse, Struktur, Schmelzpunkt,\n"
                               "Reinheit …); Summenformel und Struktur fehlen dann in allen Tabs. Die Dateien bleiben im Ordner\n"
                               "der Verbindung. Rückgängig mit Strg+Z.",
                               "Clears everything about the compound except its name (formula, molar mass, structure, melting\n"
                               "point, purity …); formula and structure are then missing in every tab. The files stay in the\n"
                               "compound folder. Undo with Ctrl+Z."),
    "btn_reset_clear_tip": ("„Tab leeren“: Dateien und Einstellungen dieses Tabs entfernen (Dateien bleiben im Ordner).",
                            "“Clear tab”: remove this tab's files and settings (the files stay in the folder)."),
    "tab_cleared": ("Tab geleert – die Dateien bleiben im Ordner. Rückgängig mit Strg+Z.",
                    "Tab cleared – the files stay in the folder. Undo with Ctrl+Z."),
    "btn_reset_defaults_tip": ("„Layout zurücksetzen“: nur die Lage von Labels, Inset und Bildern.\n"
                               "„Darstellung zurücksetzen“: nur das Aussehen der Abbildung auf Standard (Farben, Achsen,\n"
                               "Beschriftungen …). Nichts Wissenschaftliches ändert sich: Daten, Auswertung (Bereiche,\n"
                               "Basislinie, Fit, Schwellen), Angaben zur Messung, Bildunterschrift und Exportgröße bleiben,\n"
                               "ebenso jede Zahl in Tabellen, Kacheln, Methodentext und SI. Rückgängig mit Strg+Z.",
                               "“Reset layout”: only the positions of labels, inset and images.\n"
                               "“Reset display”: only the look of the figure back to defaults (colours, axes, labels …).\n"
                               "Nothing scientific changes: data, analysis (ranges, baseline, fit, thresholds), measurement\n"
                               "details, caption and export size stay, as does every number in tables, tiles, methods text\n"
                               "and SI. Undo with Ctrl+Z."),
    "btn_export": ("Exportieren", "Export"),
    "btn_export_tip": ("Schreibt die gewählten Formate in den Ordner der Verbindung: Abbildungen nach „figures“, Tabellen "
                       "nach „tables“, Texte nach „SI“ (vorhandene Dateien werden überschrieben)",
                       "Writes the chosen formats to the compound folder: figures to “figures”, tables to “tables”, texts to "
                       "“SI” (existing files are overwritten)"),
    "drag_hint": ("Maus: Inset, Bilder und Labels ziehen zum Verschieben, Mausrad über Inset/Bild "
                  "ändert die Größe. Über den Spektren zeigt eine Einblendung unten rechts λ und A des nächsten "
                  "Messpunkts, Doppelklick fügt dort eine Bande hinzu. CSV, Struktur und Foto können ins "
                  "Fenster gezogen werden.",
                  "Mouse: drag inset, images and labels to move them; scroll over inset/image to "
                  "resize. Over the spectra a box at the bottom right shows λ and A of the nearest data point; "
                  "double-click adds a band there. CSV, structure and photo can be dropped onto the window."),
    "tab_results": ("Ergebnisse", "Results"),
    "tab_log": ("Protokoll", "Log"),
    "col_lam": ("λ [nm]", "λ [nm]"),
    "col_n": ("n", "n"),
    "col_coeff": ("ε / a", "ε / a"),
    "col_intercept": ("Achsenabschnitt", "Intercept"),
    "col_r2": ("R²", "R²"),
    "col_warn": ("Hinweise", "Notes"),
    "dlg_open_csv": ("UV-Vis-Daten öffnen", "Open UV-Vis data"),
    "dlg_structure": ("Struktur wählen", "Choose structure"),
    "dlg_photo": ("Küvettenfoto wählen", "Choose cuvette photo"),
    "dlg_export": ("Export-Ordner wählen", "Choose export folder"),
    "flt_csv": ("Spektren (*.csv *.txt *.dsw *.bsw *.fbsw *.DSW *.BSW *.FBSW)", "Spectra (*.csv *.txt *.dsw *.bsw *.fbsw *.DSW *.BSW *.FBSW)"),
    "flt_struct": ("Strukturen (*.cdxml *.svg *.pdf *.png *.jpg *.jpeg *.tif *.tiff)",
                   "Structures (*.cdxml *.svg *.pdf *.png *.jpg *.jpeg *.tif *.tiff)"),
    "flt_photo": ("Bilder (*.heic *.heif *.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.avif)",
                  "Images (*.heic *.heif *.jpg *.jpeg *.png *.tif *.tiff *.webp *.bmp *.avif)"),
    "flt_all": ("Alle Dateien (*)", "All files (*)"),
    "model_q_title": ("KI-Freistellung", "AI background removal"),
    "model_q": ("Für die beste Freistellung wird einmalig ein Modell (~{mb} MB) heruntergeladen.\n"
                "Jetzt laden? (Nein = einfachere Methode GrabCut)",
                "The best background removal needs a one-time model download (~{mb} MB).\n"
                "Download now? (No = simpler GrabCut method)"),
    "downloading": ("Modell wird geladen …", "Downloading model …"),
    "cancel": ("Abbrechen", "Cancel"),
    "working": ("Rechne …", "Working …"),
    "err_title": ("Fehler", "Error"),
    "exported_to": ("Exportiert nach:\n{p}", "Exported to:\n{p}"),
    "mw_formula": ("{f}, M = {mw:.2f} g mol⁻¹", "{f}, M = {mw:.2f} g mol⁻¹"),
    "about": ("Elucida {v} (früher Spectravolt)\nVon der Synthese zur SI: Auswertung und publikationsfertige Abbildungen "
              "für UV-Vis, NMR, IR, HRMS, Fluoreszenz, CV, SEC, EPR, Röntgenstruktur und DFT – als SI-Abschnitt in Word.",
              "Elucida {v} (formerly Spectravolt)\nFrom synthesis to SI: evaluation and publication-ready figures for "
              "UV-Vis, NMR, IR, HRMS, fluorescence, CV, SEC, EPR, X-ray and DFT – exported as an SI section in Word."),
    "load_first": ("Bitte zuerst eine CSV öffnen.", "Please open a CSV first."),
    "tab_eps": ("UV-Vis (ε)", "UV-Vis (ε)"),
    "tab_overlay": ("TD-DFT", "TD-DFT"),
    "tab_fluo": ("Fluoreszenz", "Fluorescence"),
    "tab_uvkin": ("UV-Vis-Kinetik", "UV-Vis Kinetics"),
    # Tab-Leiste: unter der Gruppe „UV-Vis & Photophysik“ genügt der kurze Name (voller Name im Tooltip)
    "nav_tab_overlay": ("TD-DFT", "TD-DFT"),
    "nav_tab_uvkin": ("Kinetik", "Kinetics"),
    "tab_save": ("Vorlage speichern …", "Save preset …"),
    "tab_load": ("Vorlage laden …", "Load preset …"),
    "tab_presets": ("Vorlagen", "Presets"),
    "welcome_sub": ("Von der Synthese zur SI: Auswertung und Abbildungen für UV-Vis, NMR, IR, HRMS, CV, EPR, X-Ray, DFT "
                    "und mehr. Eine Verbindung sammelt alle ihre Daten, ein Projekt die Verbindungen einer "
                    "Veröffentlichung.",
                    "From synthesis to the SI: analysis and figures for UV-Vis, NMR, IR, HRMS, CV, EPR, X-ray, DFT and "
                    "more. A compound collects all its data, a project the compounds of a paper."),
    "welcome_recent": ("Zuletzt geöffnete Verbindungen", "Recently opened compounds"),
    "compound_note": ("Notiz", "Note"),
    "compound_mw_replaced": ("Molmasse der Serie {s} folgt der Verbindung: {old} → {new} g mol⁻¹{more}",
                             "Molar mass of series {s} follows the compound: {old} → {new} g mol⁻¹{more}"),
    "compound_mw_more": (" (und {n} weitere)", " (and {n} more)"),
    "compound_labbook": ("Laborbuch-Nr.", "Lab notebook no."),
    "compound_labbook_ph": ("Z. B. AB-1-234", "E.g. AB-1-234"),
    "compound_labbook_tip": ("Laborbuchnummer zusätzlich zur Nummer in der SI. Nur intern: steht in der Übersicht und wird von "
                             "der Suche gefunden, nie in SI, Word oder Datenpaket.",
                             "Lab notebook number in addition to the number used in the SI. Internal only: shown in the overview "
                             "and found by the search, never in the SI, Word or the data package."),
    "compound_oil": ("Öl", "Oil"),
    "compound_oil_tip": ("Öl bei Raumtemperatur: in der SI steht „m.p. <25 °C“",
                         "Oil at room temperature: the SI reads “m.p. <25 °C”"),
    "compound_known": ("Literaturbekannt", "Known from the literature"),
    "compound_known_tip": ("Für die Checkliste des Projekts: bekannte Verbindungen brauchen nur ¹H- und ¹³C-NMR",
                           "For the checklist of the project: known compounds only need ¹H and ¹³C NMR"),
    "compound_lit": ("Literatur", "Reference"),
    "compound_lit_ph": ("Zitat oder DOI, z. B. J. Org. Chem. 2020, 85, 1234", "Citation or DOI, e.g. J. Org. Chem. 2020, 85, 1234"),
    # -- DFT: Ladungen und Spinpopulationen --------------------------------------------------------------------
    "dft_pop_tab": ("Ladungen", "Charges"),
    "dft_pop_si": ("In die SI", "Include in SI"),
    "dft_pop_si_tip": ("Tabelle dieser Rechnung in den SI-Export (Word, Gesamt-SI) übernehmen",
                       "Add the table of this calculation to the SI export (Word, combined SI)"),
    "dft_pop_none": ("Keine Ladungen in dieser Rechnung. Gelesen werden ORCA (Mulliken, Löwdin, mit Spinpopulationen) "
                     "und Gaussian (Mulliken, mit Spindichten); Hirshfeld wird noch nicht gelesen.",
                     "No charges in this calculation. Read are ORCA (Mulliken, Löwdin, with spin populations) and "
                     "Gaussian (Mulliken, with spin densities); Hirshfeld is not read yet."),
    "dft_pop_note": ("Werte wie in der Ausgabe (letzter Block = Endgeometrie), auf drei Stellen gerundet; die CSV des "
                     "Exports behält alle gedruckten Stellen. Reihenfolge und Labels wie die Nummerierung im Tab.",
                     "Values as printed (last block = final geometry), rounded to three decimals; the exported CSV keeps "
                     "all printed digits. Order and labels follow the numbering in the tab."),
    "dft_pop_copy_tip": ("Ladungstabelle kopieren (für Word)", "Copy the charge table (for Word)"),
    "dft_pop_copied": ("Ladungstabelle kopiert", "Charge table copied"),
    "dft_pop_atom": ("Atom", "Atom"),
    "dft_pop_h_charge": ("{s}-Ladung", "{s} charge"),
    "dft_pop_h_spin": ("{s}-Spinpopulation", "{s} spin population"),
    # -- FID for Publication (Datenpakete des Projekts) ---------------------------------------------------------
    "fidpack_cb": ("FID for Publication (ACS)", "FID for Publication (ACS)"),
    "fidpack_cb_tip": ("Zusätzlich „FID for Publication.zip“ nach den ACS-Richtlinien: ein Ordner je Verbindung, darin "
                       "je NMR-Experiment (1H, 13C, DEPT, COSY …) das ganze TopSpin-Experiment, die Struktur als MolFile "
                       "und die Messparameter als Text. Nur Experimente, die im NMR-Tab zugeordnet sind (Kopien).",
                       "Also writes “FID for Publication.zip” following the ACS guidelines: one folder per compound, "
                       "inside each NMR experiment (1H, 13C, DEPT, COSY …) as the complete TopSpin experiment, the "
                       "structure as MolFile and the acquisition parameters as text. Only experiments assigned in the "
                       "NMR tab (copies)."),
    "fidpack_done": ("FID for Publication geschrieben: {p} ({n} Verbindungen)",
                     "FID for Publication written: {p} ({n} compounds)"),
    # -- Bezeichner der Gesamt-SI ---------------------------------------------------------------------------------
    "sinames_grp": ("Gesamt-SI: Bezeichner", "Combined SI: Labels"),
    "sinames_hint": ("Gilt für Unterschriften und Verweise im Text der Gesamt-SI. Nature-Zeitschriften verlangen "
                     "„Supplementary Figure 1“ mit eigener Zählung.",
                     "Applies to captions and references in the text of the combined SI. Nature journals require "
                     "“Supplementary Figure 1” with its own numbering."),
    "sinames_label": ("Bezeichner", "Labels"),
    "sinames_tpl": ("Wie die Vorlage der Gesamt-SI", "As the template of the combined SI"),
    "sinames_s": ("Figure S1 / Table S1", "Figure S1 / Table S1"),
    "sinames_supplementary": ("Supplementary Figure 1 / Supplementary Table 1",
                              "Supplementary Figure 1 / Supplementary Table 1"),
    # -- Data Availability Statement ------------------------------------------------------------------------------
    "das_grp": ("Data Availability Statement", "Data Availability Statement"),
    "das_hint": ("Gehört ins Manuskript (ACS: unter „Associated Content“), nicht in die SI. Es stehen nur Bausteine "
                 "darin, die hier oder im Projekt eingetragen sind; ohne eigenen Link gilt die DOI des Datensatzes "
                 "(Karte oben).",
                 "Belongs in the manuscript (ACS: under “Associated Content”), not in the SI. It only contains parts "
                 "entered here or in the project; without a link of its own the DOI of the dataset (card above) is used."),
    "das_repo": ("Repository", "Repository"),
    "das_ph_repo": ("Z. B. Zenodo, RADAR4Chem, TUDOdata", "E.g. Zenodo, RADAR4Chem, TUDOdata"),
    "das_link": ("DOI oder Link", "DOI or link"),
    "das_ph_link": ("Z. B. 10.5281/zenodo.1234567", "E.g. 10.5281/zenodo.1234567"),
    "das_auto": ("Einfügen", "Include"),
    "das_cb_ccdc": ("CCDC-Nummern", "CCDC numbers"),
    "das_cb_ccdc_tip": ("Nummern aus den X-Ray-Angaben der Verbindungen (Spalte CCDC oder die CIF), je Nummer einzeln "
                        "mit dem Standardsatz von CCDC/FIZ",
                        "Numbers from the X-ray entries of the compounds (column CCDC or the CIF), each listed with the "
                        "standard CCDC/FIZ sentence"),
    "das_cb_fid": ("FID-Paket", "FID package"),
    "das_cb_fid_tip": ("Hinweis auf „FID for Publication“, sobald es mit den Datenpaketen geschrieben wurde",
                       "Mentions “FID for Publication” once it has been written with the data packages"),
    "das_extra": ("Weiterer Text", "Further text"),
    "das_ph_extra": ("Wird unverändert angehängt (englisch)", "Appended as is"),
    "das_out": ("Statement für das Manuskript", "Statement for the manuscript"),
    "das_empty": ("Noch keine Bausteine: Repository, DOI oder Link eintragen.",
                  "No parts yet: enter a repository, DOI or link."),
    "das_copy_tip": ("Data Availability Statement kopieren (für das Manuskript)",
                     "Copy the Data Availability Statement (for the manuscript)"),
    "das_copied": ("Data Availability Statement kopiert", "Data Availability Statement copied"),
    # -- Reinheit (Tab Verbindung) ------------------------------------------------------------------------------
    "purity_grp": ("Reinheit", "Purity"),
    "purity_by": ("Belegt durch", "Shown by"),
    "purity_m_1H": ("¹H-NMR", "¹H NMR"),
    "purity_m_13C": ("¹³C-NMR", "¹³C NMR"),
    "purity_m_qnmr": ("qNMR", "qNMR"),
    "purity_m_ea": ("Elementaranalyse", "Elemental analysis"),
    "purity_m_hplc": ("HPLC", "HPLC"),
    "purity_m_gc": ("GC", "GC"),
    "purity_other": ("Weitere", "Other"),
    "purity_other_ph": ("Z. B. powder X-ray diffraction (englisch, wie in der SI)",
                        "E.g. powder X-ray diffraction (as in the SI)"),
    "purity_other_tip": ("Freitext, steht so im Satz der SI („Purity was established by …“)",
                         "Free text, used as is in the SI sentence (“Purity was established by …”)"),
    "purity_apply": ("Vorschlag übernehmen", "Use suggestion"),
    "purity_apply_tip": ("Setzt die vorgeschlagenen Nachweise; nichts wird ohne diesen Klick eingetragen",
                         "Sets the suggested methods; nothing is entered without this click"),
    "purity_suggest": ("Vorschlag aus den Daten: {m}. Erst nach Bestätigung in der SI.",
                       "Suggestion from the data: {m}. Appears in the SI only after you confirm it."),
    "purity_si": ("In der SI: {s}", "In the SI: {s}"),
    "purity_none": ("Ohne Angabe steht in der SI kein Satz zur Reinheit (ACS und Angewandte verlangen einen Nachweis).",
                    "Without an entry the SI has no sentence on purity (ACS and Angewandte ask for evidence)."),
    "compound_note_ph": ("Z. B. Radikalkation von 3b", "E.g. radical cation of 3b"),
    "compound_note_tip": ("Was ist das? Steht auf dem Startbildschirm und in der Titelleiste – "
                          "nicht in SI, Word-Export oder Datenpaket.",
                          "What is it? Shown on the welcome page and in the title bar – "
                          "not into the SI, Word export or data package."),
    "recent_search_ph": ("Alle Projekte durchsuchen: Name, Laborkürzel, Formel, Notiz …",
                         "Search all projects: name, lab code, formula, note …"),
    "search_hits": ("Treffer", "Results"),
    "act_search": ("Verbindung suchen …", "Find compound …"),
    "search_none": ("Keine Verbindung gefunden.", "No compound found."),
    "pub_filter_ph": ("Verbindungen filtern: Name, Laborkürzel, Formel, Notiz …",
                      "Filter compounds: name, lab code, formula, note …"),
    "recent_none": ("Noch nichts geöffnet – lege eine Verbindung oder ein Projekt an oder sieh dir die Beispiele an.",
                    "Nothing opened yet – create a compound or a project, or have a look at the examples."),
    "recent_empty_project": ("noch keine Daten", "no data yet"),
    "recent_reveal": ("Im Ordner zeigen", "Show in folder"),
    "recent_remove": ("Aus der Liste entfernen", "Remove from the list"),
    "recent_trash": ("In den Papierkorb verschieben …", "Move to trash …"),
    "trash_q": ("Den Ordner der Verbindung in den Papierkorb verschieben?\n\n{p}\n{n} Dateien, {size}\n\nAus dem "
                "Papierkorb lässt er sich wiederherstellen.",
                "Move the compound folder to the trash?\n\n{p}\n{n} files, {size}\n\nIt can be restored from the "
                "trash."),
    "trash_pub_q": ("Den Projektordner mit allem darin in den Papierkorb verschieben?\n\n{p}\n{n} Dateien, {size}\n"
                    "Verbindungen darin ({k}): {names}\n\nVerbindungen außerhalb des Ordners bleiben. Aus dem "
                    "Papierkorb lässt sich alles wiederherstellen.",
                    "Move the project folder with everything in it to the trash?\n\n{p}\n{n} files, {size}\n"
                    "Compounds inside ({k}): {names}\n\nCompounds outside the folder stay. Everything can be "
                    "restored from the trash."),
    "trash_failed": ("{p} konnte nicht in den Papierkorb verschoben werden.", "{p} could not be moved to the trash."),
    "trashed": ("In den Papierkorb verschoben: {p}", "Moved to the trash: {p}"),
    "time_today": ("heute {t}", "today {t}"),
    "time_yesterday": ("gestern {t}", "yesterday {t}"),
    "time_days": ("vor {n} Tagen", "{n} days ago"),
    "welcome_hint": ("Ordner von Verbindungen und Projekten oder Messdateien lassen sich auch einfach ins Fenster ziehen. "
                     "<a href='{url}'>Schnellstart in 6 Schritten</a>",
                     "You can also simply drag a compound or project folder or measurement files into the window. <a "
                     "href='{url}'>Quick start in 6 steps</a>"),
    "readme_quickstart": ("Schnellstart: von der leeren Verbindung zur SI",
                          "Quick start: from an empty compound to the SI"),
    "act_demo": ("Beispielverbindung ansehen",
                 "Open example compound"),
    "act_demo_pub": ("Beispielprojekt ansehen",
                     "Open example project"),
    "act_demo_pub_tip": ("Legt ein Projekt mit zwei Verbindungen (künstliche Daten) an – Gesamt-SI und Datenpakete zum "
                         "Ausprobieren",
                         "Creates a project with two compounds (artificial data) – to try the complete SI and data packages"),
    "demo_building": ("Beispielprojekt wird angelegt (einmal je Version) … {p} %",
                      "Creating the example project (once per version) … {p} %"),
    "demo_pub_done": ("Beispielprojekt (künstliche Daten) geöffnet: {p}",
                      "Example project (artificial data) opened: {p}"),
    "act_demo_tip": ("Legt eine Verbindung mit künstlichen Daten für alle Tabs an – zum Ausprobieren",
                     "Creates a compound with artificial data for all tabs – to try things out"),
    "demo_done": ("Beispielverbindung (künstliche Daten) geöffnet: {p}",
                  "Example compound (artificial data) opened: {p}"),
    "act_guide_tab": ("Anleitung zu diesem Tab", "Guide for this tab"),
    "act_quickstart": ("Schnellstart (README)", "Quick start (README)"),
    "open_folder": ("Ordner öffnen", "Open folder"),
    "btn_export_word_tip": ("Schreibt die Word-Datei dieses Tabs in den Ordner der Verbindung unter „SI“ (überschreibt sie)",
                            "Writes this tab's Word file to the compound folder under “SI” (overwrites it)"),
    "syn_need_scheme": ("Erst ein Reaktionsschema (CDXML) wählen", "Choose a reaction scheme (CDXML) first"),
    "tab_figure": ("Abbildung", "Figure"),
    "grp_export": ('Achsen, Größe und Formate', 'Axes, Size and Formats'),
    "grp_export_size": ('Größe und Formate', 'Size and Formats'),
    "grp_refs": ("Referenzierung", "Referencing"),
    "grp_diffusion": ("Diffusion und k⁰", "Diffusion and k⁰"),
    "grp_more_display": ('Weitere Darstellung', 'More Display Options'),
    "grp_highlight": ('Hervorheben und Labels', 'Highlighting and Labels'),
    "grp_intensity": ('Intensität und Kinetik', 'Intensity and Kinetics'),
    "grp_simulation": ('Simulationen', 'Simulations'),
    # EPR: Messparameter und Einheit der Kopplungen in Bildunterschrift/SI (Karte Bildunterschrift)
    "epr_acq_unit": ("Kopplungen in", "Couplings in"),
    "epr_acq_unit_tip": ("Einheit der Hyperfeinkopplungen in Bildunterschrift (und G auch im Methodentext); MHz mit dem "
                         "gefitteten g, mT/G als Aufspaltung a.",
                         "Unit of the hyperfine couplings in the caption (and G also in the methods text); MHz with the "
                         "fitted g, mT/G as splitting a."),
    "epr_acq_cap": ("Messparameter", "Acquisition parameters"),
    "epr_acq_cap_tip": ("Mikrowellenfrequenz, Modulationsamplitude, Leistung, Zahl der Scans und Temperatur aus den "
                        "Messdateien in die Bildunterschrift (nur, was in allen gezeigten Messungen steht und gleich ist).",
                        "Microwave frequency, modulation amplitude, power, number of scans and temperature from the "
                        "measurement files in the caption (only what all shown measurements contain, with equal values)."),
    "grp_atoms": ('Atome und Fragmente', 'Atoms and Fragments'),
    "tab_presets_tip": ("Darstellung dieses Tabs als Vorlage speichern oder laden (Daten und Auswertung bleiben unberührt)",
                        "Save or load this tab's display as a preset (data and analysis are not affected)"),
    "card_select_first": ("Erst einen Eintrag in der Liste oben wählen.", "Select an entry in the list above first."),
    "nav_grp_syn": ("Synthese & Analytik", "Synthesis & analysis"),
    "nav_grp_uv": ("UV-Vis & Photophysik", "UV-Vis & photophysics"),
    "nav_grp_ec": ("Elektrochemie & EPR", "Electrochemistry & EPR"),
    "nav_grp_struct": ("Struktur & Rechnung", "Structure & computation"),
    "tab_load_tip": ("Darstellung aus einer Vorlage (YAML) übernehmen; Daten und Auswertung bleiben (auch bei alten "
                     "Vorlagen, die mehr enthalten)",
                     "Apply the display from a preset (YAML); data and analysis stay (also with older presets that "
                     "contain more)"),
    "tab_empty": ("Noch keine Daten – links Dateien hinzufügen.", "No data yet – add files on the left."),
    "guide_syn_title": ('Synthese: „Synthesis of …“ mit Schema und Vorschrift für die SI', 'Synthesis: “Synthesis of …” with scheme and procedure for the SI'),
    "guide_syn_files": ('Dateien: ChemDraw-Schema als CDXML – das Bild zeichnet Elucida daraus; optional mit gleichem Namen daneben: SVG/PDF (Bild hat Vorrang), .cdx (in Word bearbeitbares Objekt), .emf (dessen Vorschau)', 'Files: ChemDraw scheme as CDXML – Elucida draws the picture from it; optionally next to it with the same name: SVG/PDF (picture takes precedence), .cdx (object editable in Word), .emf (its preview)'),
    "guide_syn_steps": ("Namen eintragen (Vorgabe: Name der Verbindung)\nSchema wählen und die Vorschrift schreiben – Mengen "
                        "wie „(1.03 g, 5.00 mmol, 1.0 eq.)“\nReagenzien eintragen oder „Aus Schema“ – die Mengen in der "
                        "Vorschrift werden geprüft\nAusgabe: Tab „Export“ (Word-Datei) oder Datei → SI-Abschnitt "
                        "exportieren (Word)",
                        "Enter the name (default: name of the compound)\nChoose the scheme and write the procedure – amounts "
                        "like “(1.03 g, 5.00 mmol, 1.0 eq.)”\nEnter reagents or use “From scheme” – the amounts in the "
                        "procedure are checked\nOutput: tab “Export” (Word file) or File → Export SI section (Word)"),
    "guide_nmr_title": ('NMR: Spektren aus MestReNova mit Struktur und die NMR-Zeile', 'NMR: spectra from MestReNova with structure, and the NMR line'),
    "guide_nmr_files": ('Dateien: SVG-Export aus MestReNova (Datei → Speichern unter → SVG; EMF geht unverändert nach Word), auch per Ziehen ins Fenster; optional MNova-Dokumente (links oben) und TopSpin-Daten (Reiter Rohdaten)', 'Files: SVG export from MestReNova (File → Save as → SVG; EMF goes into Word unchanged), also by dragging into the window; optionally MNova documents (top left) and TopSpin data (Raw data tab)'),
    "guide_nmr_steps": ("SVG hinzufügen – Kern und Reihenfolge erkennt das Programm\nStruktur kommt aus dem Tab "
                        "Verbindung; Lage automatisch oder in der Vorschau ziehen\nMultiplettbericht aus MNova unter "
                        "„NMR-Zeile“ einfügen (¹³C auch „Zeile aus Peaklabels“)\nSI (Word) im Tab „Export“ (zwei Spektren je Seite)",
                        "Add the SVG – nucleus and order are recognized\nThe structure comes from the Compound tab; placed "
                        "automatically or dragged in the preview\nPaste the MNova multiplet report under “NMR line” (¹³C also "
                        "“line from peak labels”)\nSI (Word) in the Export tab (two spectra per page)"),
    "guide_irms_title": ('IR + EA: IR-Peakliste und Elementaranalyse als SI-Zeilen', 'IR + EA: IR peak list and elemental analysis as SI lines'),
    "guide_irms_files": ("Dateien: Bruker-OPUS-Datei (*.0) und/oder OPUS-PDF mit Peakbeschriftung, auch per Ziehen ins "
                         "Fenster; für die EA die Summenformel der Verbindung (Tab Verbindung)",
                         "Files: Bruker OPUS file (*.0) and/or OPUS PDF with peak labels, also by dragging into the window; "
                         "for the EA the formula of the compound (Compound tab)"),
    "guide_irms_steps": ('IR-Daten wählen – mit PDF gelten genau die OPUS-Peaks, sonst sucht das Programm die Banden (Peakschwelle)\nBanden, die nicht in die Liste sollen, abhaken; Intensitäten w/m/s/br optional\nEA: gefundene C/H/N/S-Werte eintragen, ggf. Solvat; Abweichungen über 0,4 % werden markiert\nZeilen kopieren (Formatierung bleibt in Word) oder SI (Word) im Tab „Export“', 'Choose the IR data – with the PDF the OPUS peaks are used exactly, otherwise bands are searched (peak threshold)\nUntick bands that should not be listed; intensities w/m/s/br optional\nEA: enter the found C/H/N/S values, a solvate if needed; deviations above 0.4 % are marked\nCopy the lines (formatting is kept in Word) or SI (Word) in the Export tab'),
    "guide_hrms_title": ('HRMS: HR-MS-Zeile (calc./found) mit Spektrum und Isotopenmuster', 'HRMS: HR-MS line (calc./found) with spectrum and isotope pattern'),
    "guide_hrms_files": ('Dateien: Bericht der Massenabteilung (.docx oder PDF) und/oder Bruker-Messordner (.d), auch per Ziehen ins Fenster', 'Files: report of the mass spectrometry service (.docx or PDF) and/or Bruker measurement folder (.d), also by dragging'),
    "guide_hrms_steps": ("Bericht und/oder Rohdaten wählen\nSummenformel prüfen (aus der Verbindung oder „Verbindung aus dem "
                         "MS-Bericht übernehmen“)\nIon wählen; found aus einem bekannten Bericht ist vorgewählt, aus einem "
                         "anderen PDF einen Kandidaten anklicken, sonst von Hand eintragen – mit Rohdaten den LC-Bereich im "
                         "Chromatogramm ziehen oder einen Peak anklicken\nHRMS-Zeile kopieren; Abbildung und SI (Word) "
                         "im Tab „Export“ (Strg+E exportiert den Tab)",
                         "Choose the report and/or raw data\nCheck the formula (from the compound or “Take compound from the "
                         "MS report”)\nChoose the ion; found from a known report is preselected, from another PDF click a "
                         "candidate, otherwise enter it manually – with raw data drag the LC range in the "
                         "chromatogram or click a peak\nCopy the HRMS line; figure and SI (Word) in the Export tab (Ctrl+E exports the tab)"),
    "guide_eps_title": ('UV-Vis (ε): Absorptionskoeffizienten aus einer Verdünnungsreihe, Abbildung im Origin-Stil', 'UV-Vis (ε): absorption coefficients from a dilution series, figure in Origin style'),
    "guide_eps_files": ('Dateien: Cary-CSV/TXT, DSW/BSW oder Eclipse-CSV, auch per Ziehen ins Fenster. Konzentration aus dem Probennamen, z. B. ABC-1-0p5mgml_THF = 0,5 mg mL⁻¹ – sonst Tabelle zum Eintragen', 'Files: Cary CSV/TXT, DSW/BSW or Eclipse CSV, also by dragging into the window. Concentration from the sample name, e.g. ABC-1-0p5mgml_THF = 0.5 mg mL⁻¹ – otherwise a table to fill in'),
    "guide_eps_steps": ('Messdaten öffnen, Konzentrationen und Einheit prüfen\nVerbindung: Struktur (CDXML) und bei mg mL⁻¹ die Molmasse, optional Küvettenfoto\nSchichtdicke und Cutoff prüfen; Banden in der Ergebnistabelle an- oder abwählen\nExportieren (Strg+E oder Tab „Export“); die UV-Vis-Zeile für die SI steht unter „SI-Zeile“', 'Open the measurement data, check concentrations and unit\nCompound: structure (CDXML) and, for mg mL⁻¹, the molar mass; optionally a cuvette photo\nCheck path length and cutoff; tick or untick bands in the results table\nExport (Ctrl+E or the Export tab); the UV-Vis line for the SI is under “SI line”'),
    "guide_overlay_title": ('TD-DFT: gemessene Spektren und Rechnung einer Verbindung in einer Abbildung', 'TD-DFT: measured spectra and calculation of one compound in one figure'),
    "guide_overlay_files": ('Dateien: Messungen (CSV/TXT/DSW/BSW), TD-DFT-Ausgaben von ORCA oder Gaussian, Spektren aus dem SEC-Tab', 'Files: measurements (CSV/TXT/DSW/BSW), TD-DFT outputs from ORCA or Gaussian, spectra from the SEC tab'),
    "guide_overlay_steps": ('Spektren mit „Messung …“, „TD-DFT …“ oder „SEC …“ hinzufügen\nNormiert (auf die Bande im Normierungsbereich) oder als ε – für ε je Messung Konzentration und Schichtdicke eintragen\nTD-DFT: Bandenbreite (FWHM) und Verschiebung je Rechnung, Übergänge optional als Striche\nReihenfolge, Farben, Stapeln – dann exportieren (Strg+E oder Tab „Export“); Verbindungen vergleicht das Projekt (Reiter Vergleich)', 'Add spectra with “Measurement …”, “TD-DFT …” or “SEC …”\nNormalized (to the band in the normalization range) or as ε – for ε enter concentration and path length per measurement\nTD-DFT: band width (FWHM) and shift per calculation, transitions optionally as sticks\nOrder, colours, stacking – then export (Ctrl+E or the Export tab); compounds are compared in the project (Comparison tab)'),
    "guide_fluo_title": ('Fluoreszenz: Absorption und Emission mit Stokes-Verschiebung', 'Fluorescence: absorption and emission with Stokes shift'),
    "guide_fluo_files": ('Dateien: Absorption als beliebige UV-Vis-Datei, Emission (und Anregung) als Cary-Eclipse-CSV oder .FBSW; optional Abklingkurve und IRF als Textdatei (Zeit, Zählrate) und zwei Küvettenfotos (Tageslicht und UV)', 'Files: absorption as any UV-Vis file, emission (and excitation) as Cary Eclipse CSV or .FBSW; optionally a decay and IRF as text file (time, counts) and two cuvette photos (daylight and UV)'),
    "guide_fluo_steps": ('Links Absorptions- und Emissionsdatei wählen (λex kommt aus der Emissionsdatei)\n„Bande von Interesse“ für die Normierung der Absorption prüfen\nStokes-Verschiebung und Absorbanz bei λex ablesen (Warnung ab A = 0,1)\nFotos und Struktur, dann exportieren (Strg+E oder Tab „Export“)', 'Choose the absorption and emission files on the left (λex comes from the emission file)\nCheck the “band of interest” used to normalize the absorption\nRead the Stokes shift and the absorbance at λex (warning from A = 0.1)\nPhotos and structure, then export (Ctrl+E or the Export tab)'),
    "guide_cv_title": ('CV: Cyclovoltammogramme mit E½, ΔEₚ, Nicholson und Scanraten-Auswertung', 'CV: cyclic voltammograms with E½, ΔEₚ, Nicholson and scan-rate analysis'),
    "guide_cv_files": ('Dateien: Gamry-.DTA (Scanrate und Elektrodenfläche kommen aus der Datei)', 'Files: Gamry .DTA (scan rate and electrode area come from the file)'),
    "guide_cv_steps": ('Eine oder mehrere Messungen hinzufügen, z. B. eine Scanraten-Serie\nRedoxpaare: „Vorschlagen“ oder Fenster von Hand (von–bis)\nReferenz: wie gemessen, intern (Fc oder Ac₂Fc) oder feste Verschiebung\nAuftragung wählen, SI-Text kopieren, exportieren (Strg+E oder Tab „Export“)', 'Add one or more measurements, e.g. a scan-rate series\nRedox couples: “Suggest” or windows by hand (from–to)\nReference: as measured, internal (Fc or Ac₂Fc) or a fixed shift\nChoose the plot, copy the SI text, export (Ctrl+E or the Export tab)'),
    "guide_sec_title": ('SEC: UV-Vis-Spektren während eines Potentialscans', 'SEC: UV-Vis spectra during a potential scan'),
    "guide_sec_files": ('Dateien: Spektrenserie aus B&W-Tek-BWSpec (Textexport) und die Gamry-.DTA des Potentialscans', 'Files: spectrum series from B&W Tek BWSpec (text export) and the Gamry .DTA of the potential scan'),
    "guide_uvkin_title": ('UV-Vis-Kinetik: wie sich die Spektren einer Lösung über die Zeit ändern',
                          'UV-Vis kinetics: how the spectra of a solution change over time'),
    "guide_uvkin_files": ('Dateien: Cary-Exporte als CSV (Aufnahmezeit je Spektrum aus „Collection Time“), auch mehrere '
                          'Dateien, z. B. eine je Tag; .DSW/.BSW ohne Zeit',
                          'Files: Cary exports as CSV (acquisition time per spectrum from “Collection Time”), also several '
                          'files, e.g. one per day; .DSW/.BSW without time'),
    "guide_uvkin_steps": ('Dateien hinzufügen – jedes Spektrum wird eine Zeile mit seiner Aufnahmezeit\n'
                          'Reihe eintragen (z. B. Konzentration), mehrere Zeilen markieren und „Für die Auswahl setzen“; '
                          'gesättigte Spektren abwählen\n'
                          'Ansicht: Spektren einer Reihe über die Zeit oder Absorbanz bei λ gegen die Zeit, optional '
                          'Zerfall erster Ordnung fitten\nExportieren (Strg+E oder Tab „Export“)',
                          'Add files – each spectrum becomes a row with its acquisition time\n'
                          'Enter the series (e.g. concentration), select several rows and “Set for selection”; uncheck '
                          'saturated spectra\n'
                          'View: spectra of one series over time or absorbance at λ against time, optionally fit a '
                          'first-order decay\nExport (Ctrl+E or the Export tab)'),
    "guide_sec_steps": ('Spektren und Potentialdatei wählen – jedes Spektrum bekommt sein Potential über die Uhrzeit\nAnsicht: Spektrenserie, Differenzspektren oder A bei λ gegen E (scheinbarer Nernst-Fit)\nZwischenspezies über ihr Potential hervorheben, Felder der Bildunterschrift ausfüllen\nExportieren (Strg+E oder Tab „Export“)', 'Choose spectra and potential file – each spectrum gets its potential from the clock time\nView: spectrum series, difference spectra or A at λ versus E (apparent Nernst fit)\nHighlight intermediate species by their potential, fill in the caption fields\nExport (Ctrl+E or the Export tab)'),
    "guide_epr_title": ('EPR: CW-EPR-Spektren mit Simulation, S = ½-Fit und Kinetik', 'EPR: CW EPR spectra with simulation, S = ½ fit and kinetics'),
    "guide_epr_files": ('Dateien: Bruker BES3T (.dsc + .DTA) oder zweispaltiger Text (z. B. MS400); Simulationen aus EasySpin als Text', 'Files: Bruker BES3T (.dsc + .DTA) or two-column text (e.g. MS400); simulations from EasySpin as text'),
    "guide_epr_steps": ('Messung hinzufügen; optional ein Dunkelspektrum abziehen\nBasislinie, Ausblenden und Glätten unter „Verarbeitung“\nSimulation laden oder eine S = ½-Simulation anlegen und fitten; Feldkalibrierung mit TEMPO möglich\nExportieren mit Strg+E oder im Tab „Export“ (Abbildung und Textdateien für EasySpin)', 'Add a measurement; optionally subtract a dark spectrum\nBaseline, masking and smoothing under “Processing”\nLoad a simulation or create and fit an S = ½ simulation; field calibration with TEMPO possible\nExport with Ctrl+E or in the Export tab (figure and text files for EasySpin)'),
    "guide_xray_title": ('X-Ray: ORTEP-Abbildung und Kristalldatentabellen aus der CIF', 'X-ray: ORTEP figure and crystal data tables from the CIF'),
    "guide_xray_files": ('Dateien: CIF, auch per Ziehen ins Fenster; jeder data_-Block mit Atomen wird ein Eintrag', 'Files: CIF, also by dragging into the window; every data_ block with atoms becomes an entry'),
    "guide_xray_steps": ('CIF hinzufügen\nZiehen dreht, rechte Taste verschiebt, Mausrad zoomt; Stil, Labels und ausgeblendete Atome links\nAtome anklicken: 2 = Abstand, 3 = Winkel, 4 = Diederwinkel – Werte mit esd aus der CIF\nTabellen kopieren; Exportieren und SI (Word) im Tab „Export“ (Strg+E exportiert den Tab)', 'Add a CIF\nDrag rotates, right button pans, wheel zooms; style, labels and hidden atoms on the left\nClick atoms: 2 = distance, 3 = angle, 4 = torsion – values with esd from the CIF\nCopy the tables; Export and SI (Word) in the Export tab (Ctrl+E exports the tab)'),
    "guide_dft_title": ('DFT: Geometrien darstellen, umnummerieren und den SI-Block (Koordinaten, Energien) erzeugen', 'DFT: show geometries, renumber them and create the SI block (coordinates, energies)'),
    "guide_dft_files": ('Dateien: xyz (auch Trajektorien), ORCA-6-Ausgabe (.out) oder Gaussian-Ausgabe (.log), auch per Ziehen ins Fenster', 'Files: xyz (also trajectories), ORCA 6 output (.out) or Gaussian output (.log), also by dragging into the window'),
    "guide_dft_steps": ('Datei hinzufügen\nDrehen und messen wie im X-Ray-Tab\nOptional umnummerieren: „Nummerieren“ und die Atome der Reihe nach anklicken, oder „Wie Vorlage“\nSI-Text kopieren, „Word speichern …“ in der Karte oder SI (Word) im Tab „Export“', 'Add a file\nRotate and measure as in the X-ray tab\nOptionally renumber: “Number atoms” and click the atoms in order, or “Like template”\nCopy the SI text, “Save Word …” in the card or SI (Word) in the Export tab'),
    "guide_more": ("Ausführliche Anleitung (README) öffnen", "Open the detailed guide (README)"),
    "guide_add": ("Dateien hinzufügen …", "Add files …"),
    "note_error": ("Fehler beim Zeichnen: {e} – Details unter Hilfe → Protokoll", "Error while drawing: {e} – details under Help → Log"),
    "act_log": ("Protokoll …", "Log …"),
    "act_shortcuts": ("Maus und Tastenkürzel …", "Mouse and keyboard shortcuts …"),
    "shortcuts_mouse": ("Maus im offenen Tab", "Mouse in the open tab"),
    "shortcuts_keys": ("Tastenkürzel", "Keyboard shortcuts"),
    "log_title": ("Protokoll", "Log"),
    "drag_hint_tab": ("Legende, Labels und Bilder lassen sich mit der Maus verschieben, Bilder per "
                      "Mausrad skalieren. Über den Kurven zeigt eine Einblendung unten rechts die Werte unter dem Mauszeiger.",
                      "Legend, labels and images can be dragged with the mouse; scroll over images to "
                      "resize. Over the curves a box at the bottom right shows the values under the pointer."),
    "drag_hint_plain": ("Labels und Bilder lassen sich mit der Maus verschieben, Bilder per Mausrad skalieren.",
                        "Labels and images can be dragged with the mouse; scroll over images to resize."),
    "auto": ("Auto", "Auto"),
    "ov_curves": ("Spektren", "Spectra"),
    "tab_irms": ("IR + EA", "IR + EA"),
    "tab_hrms": ("HRMS", "HRMS"),
    "ms_xrange": ("m/z-Bereich (Bild)", "m/z range (figure)"),
    "ms_chrom": ("Chromatogramm", "Chromatogram"),
    "ms_chrom_tip": ("Gesamt-Ionenstrom (grau) und Ionenstrom des gesuchten Ions (± 10 ppm); blau = LC-Bereich "
                     "für das gemittelte Spektrum. Mit der Maus ziehen, um den Bereich zu wählen.",
                     "Total ion current (grey) and ion current of the target ion (± 10 ppm); blue = LC range used "
                     "for the averaged spectrum. Drag with the mouse to choose the range."),
    "ms_display": ("Spektrum", "Spectrum"),
    "ms_show_calc": ("Isotopenmuster", "Isotope pattern"),
    "ms_show_calc_long": ("Berechnetes Isotopenmuster (gespiegelt)", "Calculated isotope pattern (mirrored)"),
    "ms_mz_labels": ("m/z an Peaks", "m/z at peaks"),
    "ms_mz_labels_long": ("m/z an den größten Peaks", "m/z at the largest peaks"),
    "ms_pick_hint": ("Peak im Spektrum anklicken, um ihn als found zu übernehmen; im Chromatogramm ziehen setzt den "
                     "LC-Bereich. Spektrum = Mittel der Linienspektren des Geräts im LC-Bereich (keine Profilkurve).",
                     "Click a peak in the spectrum to use it as found; drag in the chromatogram to set the LC range. "
                     "Spectrum = mean of the instrument's line spectra in the LC range (no profile curve)."),
    "ms_pick_entry": ("Im Spektrum gewählt: {mz}  ({ppm} ppm)", "Picked in the spectrum: {mz}  ({ppm} ppm)"),
    "ms_iso_col": ("Isotop", "Isotope"),
    "ms_iso_meas": ("Gemessen [%]", "Measured [%]"),
    "ms_iso_calc": ("Berechnet [%]", "Calculated [%]"),
    "ms_iso_tip": ("Isotopenpeaks relativ zum monoisotopischen Peak M, gemessen gegen berechnet aus der Formel",
                   "Isotope peaks relative to the monoisotopic peak M, measured against calculated from the formula"),
    "ir_group": ("IR", "IR"),
    "ir_files": ("IR-Daten", "IR data"),
    "flt_ir": ("Bruker OPUS / PDF (*.0 *.1 *.2 *.3 *.4 *.5 *.6 *.7 *.8 *.9 *.pdf)", "Bruker OPUS / PDF (*.0 *.1 *.2 *.3 *.4 *.5 *.6 *.7 *.8 *.9 *.pdf)"),
    "ir_pdf_empty": ("keine Peakwerte im PDF gefunden (OPUS-Ausdruck mit Peakbeschriftung nötig)",
                     "no peak values found in the PDF (OPUS print-out with peak labels needed)"),
    "ir_pdf_ambiguous": ("mehrere Spektren ausgewählt: das PDF heißt nicht wie das übernommene (letzte) "
                         "Spektrum und wurde nicht übernommen – PDF einzeln zum Spektrum laden",
                         "several spectra selected: the PDF is not named like the spectrum kept (the last one) "
                         "and was not used – load the PDF on its own with its spectrum"),
    "ir_full": ("Gesamt", "Full"),
    "ir_range": ("Bereich", "Range"),
    "ir_xrange": ("ṽ-Bereich [cm⁻¹]", "ṽ range [cm⁻¹]"),
    "ir_prom": ("Peakschwelle", "Peak threshold"),
    "ir_base": ("Basislinie korrigieren", "Correct baseline"),
    "ir_base_long": ("Basislinie korrigieren (wie OPUS)", "Correct baseline (as in OPUS)"),
    "ir_base_tip": ("Konkaves Gummiband wie OPUS-Basislinienmethode 3 (Stützpunkte/Iterationen aus dem OPUS-Verlauf, "
                    "sonst 128/50), in Absorbanz gerechnet. Wirkt auf Bild und Peaksuche, nie auf die Datei; mit OPUS-PDF "
                    "gelten dessen Peakwerte.",
                    "Concave rubberband as in OPUS baseline method 3 (points/iterations from the OPUS history, otherwise "
                    "128/50), computed in absorbance. Affects figure and peak search, never the file; with an OPUS PDF its "
                    "peak values apply."),
    "ir_base_hint": ("Laut OPUS-Verlauf wurde die Basislinie in OPUS korrigiert, die Datei enthält aber das Rohspektrum – "
                     "Haken „Basislinie korrigieren“ setzen?",
                     "According to the OPUS history the baseline was corrected in OPUS, but the file holds the raw "
                     "spectrum – tick “Correct baseline”?"),
    "ir_thr": ("Schwelle setzen", "Set threshold"),
    "ir_thr_tip": ("Im Bild: Klick = Stützpunkt der Schwellenlinie, Rechtsklick = nächsten entfernen. Peaks = Minima "
                   "(%T) bzw. Maxima (A) jenseits der Linie; ersetzt die Mindesttiefe, solange Stützpunkte da sind.",
                   "In the figure: click = threshold point, right-click = remove the nearest. Peaks = minima (%T) or "
                   "maxima (A) beyond the line; replaces the minimum depth while points exist."),
    "ir_thr_clear": ("Schwelle löschen", "Clear threshold"),
    "ir_thr_pdf": ("Schwellenlinie wirkt nicht: mit OPUS-PDF gelten dessen Peakwerte.",
                   "Threshold line has no effect: with an OPUS PDF its peak values apply."),
    "ir_pdf_layout": ("Kurve im PDF nicht lesbar (kein OPUS-Ausdruck mit Achsenbeschriftung und einer Spektrenseite)",
                      "curve in the PDF not readable (no OPUS print-out with axis labels and one spectrum page)"),
    "ir_pdf_curve_none": ("Nur Peakwerte aus dem PDF, kein Bild: {e}", "Only peak values from the PDF, no figure: {e}"),
    "ir_prom_tip": ("Mindesttiefe einer Bande relativ zur stärksten (kleiner = mehr Peaks). Nur bei eigener Peaksuche "
                    "in der OPUS-Datei; mit PDF gilt die Peakliste aus OPUS.",
                    "Minimum depth of a band relative to the strongest one (smaller = more peaks). Only for the own peak "
                    "search in the OPUS file; with a PDF the OPUS peak list is used."),
    "ir_with_int": ("Intensitäten", "Intensities"),
    "ir_with_int_long": ("Intensitäten angeben (w/m/s, br)", "Give intensities (w/m/s, br)"),
    "ir_with_int_tip": ("Aus der relativen Tiefe: s ≥ 60 %, m ≥ 30 %, sonst w; br bei Halbwertsbreite > 120 cm⁻¹. "
                        "Braucht die OPUS-Datei (Spektrum).",
                        "From the relative depth: s ≥ 60 %, m ≥ 30 %, otherwise w; br for half widths > 120 cm⁻¹. "
                        "Needs the OPUS file (spectrum)."),
    "ir_labels": ("Wellenzahlen im Bild", "Wavenumbers in figure"),
    "ir_labels_long": ("Wellenzahlen im Bild beschriften", "Label wavenumbers in the figure"),
    "ir_struct": ("Struktur im Bild", "Structure in figure"),
    "ir_struct_tip": ("Struktur der Verbindung (ChemDraw) in Vorschau und Export einsetzen",
                      "Insert the compound's structure (ChemDraw) in preview and export"),
    "ir_mode": ("y-Achse", "y axis"),
    "ir_mode_T": ("Transmission (%T)", "Transmittance (%T)"),
    "ir_mode_A": ("Absorbanz (A)", "Absorbance (A)"),
    "ir_mode_tip": ("Nur die Darstellung im Bild: A = −log₁₀(T/100). Peaksuche, Peakwerte und SI-Zeile bleiben gleich "
                    "(immer aus den gemessenen Daten).",
                    "Display only: A = −log₁₀(T/100). Peak search, peak values and SI line stay the same "
                    "(always from the measured data)."),
    "ir_yrange": ("y-Bereich", "y range"),
    "ir_yrange_tip": ("auto: Transmission oben 100 %, unten mit Platz für die Labels; Absorbanz unten 0, oben nach den "
                      "Daten. Ohne Haken gelten min und max exakt (Transmission 0–100 %).",
                      "auto: transmittance top 100 %, bottom with room for the labels; absorbance bottom 0, top from "
                      "the data. Unchecked, min and max are used exactly (transmittance 0–100 %)."),
    "ir_yrange_bad": ("y-Bereich ungültig (min muss kleiner als max sein) – automatisch.",
                      "Invalid y range (min must be below max) – set automatically."),
    "ir_labels_clamped": ("Wellenzahl-Labels außerhalb des festen y-Bereichs (liegen am Rand): {n} – min verkleinern "
                          "oder „Auto“ wählen.",
                          "Wavenumber labels outside the fixed y range (placed at the edge): {n} – lower min or "
                          "choose “Auto”."),
    "ir_intensity": ("Intensität", "Intensity"),
    "ea_group": ('Elementaranalyse', 'Elemental Analysis'),
    "ea_solvate": ("Solvat", "Solvate"),
    "ea_solvate_ph": ("Z. B. 0.5 CH2Cl2 (optional)", "E.g. 0.5 CH2Cl2 (optional)"),
    "ea_solvate_tip": ("Wird zur Formel addiert (berechnete Werte und Zeile), mehrere mit Komma: 0.5 CH2Cl2, H2O",
                       "Added to the formula (calculated values and line); several separated by commas: 0.5 CH2Cl2, H2O"),
    # EA- und HRMS-Prüfung nach den Richtlinien (ACS: ≤ 0.4 %; Angew.: Doppelbestimmung mit Mittel; HRMS ≤ 5 ppm)
    "ea_chk_found2": ("2. Messung", "2nd run"),
    "ea_chk_found2_tip": ("Optional: zweiter Wertesatz der Doppelbestimmung (Angewandte verlangt beide Sätze und das "
                          "Mittel). Die SI-Zeile nennt dann beide und das Mittel; geprüft wird das Mittel.",
                          "Optional: second set of the duplicate analysis (Angewandte asks for both sets and the "
                          "average). The SI line then gives both and the average; the average is checked."),
    "ea_chk_el": ("Element", "Element"),
    "ea_chk_f1": ("Gefunden", "Found"),
    "ea_chk_mean": ("Mittel", "Average"),
    "ea_chk_status": ("Status", "Status"),
    "ea_chk_ok": ("≤ 0.4 %", "≤ 0.4 %"),
    "ea_chk_bad": ("> 0.4 %", "> 0.4 %"),
    "ea_chk_tip": ("Gefunden (bzw. Mittel der Doppelbestimmung) minus berechnet, wie gedruckt; ACS und viele Journals "
                   "verlangen höchstens 0.4 %.",
                   "Found (or average of the duplicate analysis) minus calculated, as printed; ACS and many journals "
                   "require at most 0.4 %."),
    "ea_chk_kpi": ("EA", "EA"),
    "ea_chk_reason": ("Ohne EA, weil", "No EA, because"),
    "ea_chk_reason_ph": ("Z. B. not obtained (air-sensitive); purity by ¹H NMR",
                         "E.g. not obtained (air-sensitive); purity by ¹H NMR"),
    "ea_chk_reason_tip": ("Englischer Text für die SI, wenn es keine Elementaranalyse gibt (Angewandte und ACS verlangen "
                          "dann eine Begründung). Gilt nur ohne gefundene Werte.",
                          "Text for the SI when there is no elemental analysis (Angewandte and ACS then ask for a "
                          "reason). Used only without found values."),
    "ea_chk_ms_ion": ("Ion", "Ion"),
    "ea_chk_ms_dev": ("Δ [ppm]", "Δ [ppm]"),
    "ea_chk_ms_status": ("Status", "Status"),
    "ea_chk_ms_ok": ("≤ 5 ppm", "≤ 5 ppm"),
    "ea_chk_ms_bad": ("> 5 ppm", "> 5 ppm"),
    "ea_chk_ms_tip": ("found − calc. in ppm; Angewandte nennt 5 ppm als Grenze hoher Auflösung.",
                   "found − calc. in ppm; Angewandte names 5 ppm as the limit of high resolution."),
    "ea_chk_ms_kpi": ("Δ", "Δ"),
    "ea_calc": ("Berechnet", "Calculated"),
    "ea_found": ("Gefunden", "Found"),
    "ea_enter": ("Gefundene Werte eintragen (nur die gemessenen Elemente).",
                 "Enter the found values (only the measured elements)."),
    "ea_ok": ("Alle Abweichungen ≤ 0.4 % (übliche Grenze der Journals).",
              "All deviations ≤ 0.4 % (usual limit of the journals)."),
    "ea_dev": ("⚠ Abweichung > 0.4 %: {els} – viele Journals verlangen ≤ 0.4 %; ggf. Solvat prüfen.",
               "⚠ deviation > 0.4 %: {els} – many journals require ≤ 0.4 %; check for a solvate."),
    "tab_si_line": ("SI-Zeile", "SI line"),
    "si_solvent": ("Lösungsmittel", "Solvent"),
    "si_solvent_ph": ("Optional, z. B. THF → „UV-Vis (THF): …“", "Optional, e.g. THF → “UV-Vis (THF): …”"),
    "si_uv_hint": ("Banden wie im Bild (abgewählte und solche unter der R²-Schwelle fehlen), aufsteigend; ε gerundet "
                   "auf die Genauigkeit des Standardfehlers, ohne ±.",
                   "Bands as in the figure (deselected ones and those below the R² threshold are left out), "
                   "ascending; ε rounded to the precision of the standard error, without ±."),
    "si_uv_none": ("Noch keine Banden mit Fit.", "No fitted bands yet."),
    "si_uv_title": ("UV-Vis-Zeile", "UV-Vis Line"),
    "act_export_si": ("SI-Abschnitt exportieren (Word) …", "Export SI section (Word) …"),
    "act_datapack": ("Datenpaket (Zip) exportieren …", "Export data package (zip) …"),
    "dp_title": ("Datenpaket (Zip) exportieren", "Export data package (zip)"),
    "dp_hint": ("Rohdaten dieser Verbindung als Zip für ein Datenrepositorium, je Analytik ein Ordner (z. B. "
                "NMR/1H/10, IR, CV/<Lösungsmittel>); ohne X-Ray (CCDC) und Synthese. Laborkürzel werden durch die "
                "Verbindung ersetzt.",
                "Raw data of this compound as a zip for a data repository, one folder per technique (e.g. NMR/1H/10, "
                "IR, CV/<solvent>); without X-ray (CCDC) and synthesis. Lab codes are replaced by the compound."),
    "dp_name": ("Name (Zip und Ordner)", "Name (zip and folder)"),
    "dp_name_tip": ("Wie in der Publikation, z. B. 3b – ergibt 3b.zip mit dem Ordner 3b/",
                    "As in the publication, e.g. 3b – gives 3b.zip with the folder 3b/"),
    "dp_col_file": ("Im Zip", "In the zip"),
    "dp_col_size": ("Größe", "Size"),
    "dp_codes": ("Laborkürzel ersetzen", "Replace lab codes"),
    "dp_code": ("Kürzel", "Code"),
    "dp_code_name": ("In Datei-/Ordnernamen", "In file/folder names"),
    "dp_code_text": ("Im Inhalt", "In the contents"),
    "dp_code_add": ("Kürzel hinzufügen", "Add code"),
    "dp_text": ("Auch im Inhalt: Kürzel → „Compound …“, Datum und Uhrzeit löschen (Textdateien, TopSpin-Parameter, "
                "MS-Bericht, OPUS)",
                "Also in the contents: codes → “Compound …”, delete date and time (text files, TopSpin parameters, "
                "MS report, OPUS)"),
    "dp_text_tip": ("Messwerte (FID, ser, Spektren) bleiben bytegleich. Im MS-Bericht auch Ersteller und Datum der "
                    "Datei. PDF, MNova und Bruker-.d lassen sich nicht bearbeiten; ein Kürzel darin steht danach im "
                    "Protokoll",
                    "Measured values (FID, ser, spectra) stay byte-identical. In the MS report also the file's author "
                    "and date. PDF, MNova and Bruker .d cannot be edited; a code in them is listed in the log"),
    "dp_export": ("Exportieren …", "Export …"),
    "dp_size": ("{n} Einträge, {size} (vor dem Packen)", "{n} entries, {size} (before compression)"),
    "dp_writing": ("Datenpaket wird geschrieben …", "Writing the data package …"),
    "dp_done": ("Datenpaket gespeichert: {p} ({n} Dateien, {size}; Kürzel in {t} Textdateien ersetzt)",
                "Data package saved: {p} ({n} files, {size}; codes replaced in {t} text files)"),
    "dp_kept": ("Kürzel noch enthalten (Binärdateien, unverändert):\n  {files}",
                "Codes still contained (binary files, unchanged):\n  {files}"),
    "dp_grp_nmr": ("NMR (TopSpin, MNova)", "NMR (TopSpin, MNova)"),
    "dp_grp_ir": ("IR", "IR"),
    "dp_grp_ms": ("MS (Bericht, Rohdaten)", "MS (report, raw data)"),
    "dp_grp_uvvis": ("UV-Vis", "UV-Vis"),
    "dp_grp_overlay": ("TD-DFT-Tab (gemessene Spektren)", "TD-DFT tab (measured spectra)"),
    "dp_grp_fluo": ("Fluoreszenz", "Fluorescence"),
    "dp_grp_cv": ("CV", "CV"),
    "dp_grp_sec": ("SEC", "SEC"),
    "dp_grp_epr": ("EPR", "EPR"),
    "dp_grp_dft": ("DFT (Rechnungen)", "DFT (calculations)"),
    "dp_grp_elucida": ("Ergebnisse aus Elucida (Abbildungen, SI)", "Results from Elucida (figures, SI)"),
    "si_written": ("SI-Abschnitt gespeichert: {p}", "SI section saved: {p}"),
    "act_si_short": ("SI (Word)", "SI (Word)"),
    "act_si_tip": ("SI-Abschnitt der Verbindung als Word-Datei; Teile auswählbar (Charakterisierung, X-Ray, DFT)",
                   "SI section of the compound as a Word file; parts selectable (characterization, X-ray, DFT)"),
    "si_parts_head": ("In die SI übernehmen:", "Include in the SI:"),
    "si_part_char": ("Charakterisierung (m.p., NMR, IR, HR-MS, UV-Vis, Elementaranalyse)",
                     "Characterization (m.p., NMR, IR, HR-MS, UV-Vis, elemental analysis)"),
    "si_part_nmr": ("NMR-Spektren (zwei je Seite)", "NMR spectra (two per page)"),
    "si_part_figs": ("Abbildungen aller Tabs (UV-Vis, IR, HR-MS, Fluoreszenz, CV, SEC, EPR; zwei je Seite)",
                     "Figures from all tabs (UV-Vis, IR, HR-MS, fluorescence, CV, SEC, EPR; two per page)"),
    "cap_box": ('Bildunterschrift (SI-Export)', 'Figure Caption (SI Export)'),
    "cv_cap_tip": ("Unterschrift wie in der SI der Gruppe. Vorschubgeschwindigkeit, iR-Kompensation (aus der Gamry-"
                   "Datei), Referenz und Pfeile kommen aus den sichtbaren Messungen, der Rest aus diesen Feldern.",
                   "Caption as in the group's SI. Scan rate, iR compensation (from the Gamry file), reference and "
                   "arrows come from the visible measurements, the rest from these fields."),
    "cap_conc": ("Konzentration", "Concentration"),
    "cap_conc_ph": ("Z. B. 1.7±0.1 mg mL-1", "E.g. 1.7±0.1 mg mL-1"),
    "cap_solvent": ("Lösungsmittel", "Solvent"),
    "cv_cap_solvent_ph": ("Leer = Gruppe der Messungen (mehrere: „different solvents“)",
                          "Empty = group of the measurements (several: “different solvents”)"),
    "cap_solvent_ph": ("Z. B. THF", "E.g. THF"),
    "sec_cap_tip": ("Unterschrift wie in der SI der Gruppe. Start-/Endpotential kommen aus dem Scan (erstes/letztes "
                    "gezeigtes Spektrum, Referenz wie die Achse); die Farbcodierung (blau/rot, mit eigener Farbe ohne Farbwort) nur "
                    "mit hervorgehobenem ersten/letzten Spektrum; Zwischenspektren (grün …) nur, wenn sie im Bild hervorgehoben sind.",
                    "Caption as in the group's SI. Start/end potentials come from the scan "
                    "(first/last spectrum shown, reference as on the axis); colour coding (blue/red, without a colour word for your "
                    "own colour) only with the first/last spectrum highlighted; intermediate spectra (green …) only if highlighted in the figure."),
    "cap_start": ("Spezies am Anfang", "Species at start"),
    "cap_start_ph": ("Z. B. neutral", "E.g. neutral"),
    "cap_mid": ("Zwischenstufe", "Intermediate"),
    "cap_mid_long": ("Spezies Zwischenstufe", "Intermediate species"),
    "cap_mid_ph": ("Z. B. radical cation (mehrere mit „;“)", "E.g. radical cation (several with “;”)"),
    "cap_end": ("Spezies am Ende", "Species at end"),
    "cap_end_ph": ("Z. B. dication", "E.g. dication"),
    "epr_cap_tip": ("Unterschrift wie in der SI der Gruppe. Band aus der Mikrowellenfrequenz; Parameter (g, ΔB_pp, "
                    "Kopplungen in MHz) nur aus eigenen S = ½-Fits, ohne Fehlerangabe. EasySpin-Simulationen bitte "
                    "selbst ergänzen.", "Caption as in the group's SI. Band from the microwave frequency; parameters "
                    "(g, ΔB_pp, couplings in MHz) only from own S = ½ fits, without uncertainties. Please add "
                    "EasySpin simulations yourself."),
    "cap_species": ("Spezies", "Species"),
    "cap_species_ph": ("Leer = Verbindung; z. B. 3b•+, „•+“ mit X² hochstellen",
                       "Empty = compound; e.g. 3b•+, raise “•+” with X²"),
    "cap_el": ("Leitsalz", "Electrolyte"),
    "cap_el_ph": ("Z. B. 0.1 M n-Bu4NPF6 (wird gemerkt)", "E.g. 0.1 M n-Bu4NPF6 (remembered)"),
    "cap_temp": ("Temperatur", "Temperature"),
    "cap_cuvette": ("Küvette", "Cuvette"),
    "cap_cuvette_ph": ("Leer = 1 cm", "Empty = 1 cm"),
    "fluorescence_cap_conc_ph": ("Z. B. 10 µM", "E.g. 10 µM"),
    "fluorescence_cap_tip": ("Angaben für die Bildunterschrift im SI-Export (Lösungsmittel, Konzentration, Küvette); "
                             "Farben und λex kommen aus dem Bild",
                             "Details for the caption in the SI export (solvent, concentration, cuvette); colours "
                             "and λex come from the figure"),
    "cap_temp_ph": ("rt", "rt"),
    "si_setup_btn": ("Aufbau-Text (SI) …", "Setup text (SI) …"),
    "si_setup_tip": ("Allgemeinen Absatz zu Gerät und Aufbau hinterlegen; er steht im SI-Export vor den Abbildungen "
                     "dieses Tabs.", "Store a general paragraph on instrument and setup; the SI export puts it "
                     "before this tab's figures."),
    "si_setup_title": ("Aufbau-Text für die SI", "Setup text for the SI"),
    "si_setup_hint": ("Wird nur auf diesem Rechner gespeichert (nicht in der Verbindung) und im SI-Export vor die "
                      "Abbildungen gesetzt. Formeln wie AgNO3 oder nBu4NPF6 werden tiefgestellt, „mL-1“ hochgestellt. Leer "
                      "= kein Absatz.",
                      "Stored on this computer only (not in the compound) and placed before the figures in the SI export. "
                      "Formulas such as AgNO3 or nBu4NPF6 are subscripted, “mL-1” superscripted. Empty = no paragraph."),
    "si_uv_no_solvent": ("Hinweis: Serie „{g}“ ohne Lösungsmittel – im ε-Tab unter „SI-Zeile“ eintragen, dann steht es "
                         "in der UV-Vis-Zeile und in der Bildunterschrift.", "Note: series “{g}” has no solvent – enter "
                         "it in the ε tab under “SI line” to get it into the UV-Vis line and the figure caption."),
    "nmr_peaks": ("Zeile aus Peaklabels", "Line from peak labels"),
    "nmr_peaks_tip": ("Für das gewählte 1D-Spektrum (z. B. ¹³C): Verschiebungen aus den Peaklabels des MNova-SVG als "
                      "Zeile „13C NMR (… MHz, …) δ …“ ins Textfeld (ersetzt eine vorhandene Zeile desselben Kerns). Ein "
                      "beschriftetes Lösungsmittelsignal („77.16 CDCl3“) fällt weg, unbeschriftete bitte löschen.",
                      "For the selected 1D spectrum (e.g. ¹³C): shifts from the peak labels of the MNova SVG as a line "
                      "“13C NMR (… MHz, …) δ …” in the text field (replaces an existing line of that nucleus). A "
                      "labelled solvent signal (“77.16 CDCl3”) is dropped; please delete unlabelled ones."),
    "nmr_peaks_need": ("Erst ein 1D-Spektrum mit Kern wählen.", "Select a 1D spectrum with a nucleus first."),
    "nmr_peaks_1h": ("Für ¹H bitte den Multiplettbericht aus MNova einfügen (Peaklabels kennen keine Multipletts).",
                     "For ¹H please paste the multiplet report from MNova (peak labels have no multiplets)."),
    "nmr_peaks_none": ("Keine Peaklabels in {f} gefunden (in MNova Peaks beschriften und neu exportieren).",
                       "No peak labels found in {f} (label the peaks in MNova and export again)."),
    "nmr_peaks_done": ("{n} Signale ({nuc}) aus den Peaklabels übernommen – bitte prüfen.",
                       "{n} signals ({nuc}) taken from the peak labels – please check."),
    "si_part_methods": ("Methodik der Auswertung und Fits (Text aus „SI-Text kopieren“ aller Tabs)",
                        "Data processing and fitting (text of “Copy SI text” from all tabs)"),
    "si_font": ("Schriftart (Word)", "Font (Word)"),
    "si_font_tip": ("Gilt für alle Word-Exporte (SI, DFT, Synthese, NMR) und wird gemerkt. Standard Arial wie die SI\n"
                    "der Gruppe. Die Größe bleibt 11 pt: „zwei Abbildungen je Seite“ rechnet mit dieser Zeilenhöhe.",
                    "Applies to all Word exports (SI, DFT, synthesis, NMR) and is remembered. Default Arial as in the\n"
                    "group's SI. The size stays 11 pt: “two figures per page” is calculated with this line height."),
    "si_part_xray": ("Kristallstruktur(en) aus dem Tab X-Ray", "Crystal structure(s) from the X-Ray tab"),
    "si_part_dft": ("DFT-Rechnungen aus dem Tab DFT (zweispaltig)", "DFT calculations from the DFT tab (two columns)"),
    "si_part_empty": ("Keine Daten in diesem Tab.", "No data in this tab."),
    "si_missing": ("Noch nicht vorhanden: {parts}", "Not available yet: {parts}"),
    "skip_item": ("{f}: {e}", "{f}: {e}"),
    "dft_prof_unreadable": ("nicht lesbar, Energieprofil nicht gezeichnet (ohne diese Stufe änderten sich Bezug und "
                            "Werte)", "unreadable, energy profile not drawn (without this level the reference and the "
                            "values would change)"),
    "parts_skipped": ("Nicht lesbar und deshalb ausgelassen:\n{items}", "Unreadable and therefore left out:\n{items}"),
    "compound_mp": ("Schmelzpunkt", "Melting point"),
    "compound_mp_ph": ("Z. B. 67 °C oder 218 °C (decomp.)", "E.g. 67 °C or 218 °C (decomp.)"),
    "ms_group": ("HRMS", "HRMS"),
    "ms_file": ("MS-Bericht", "MS report"),
    "ms_file_tip": ("Bericht der Massenabteilung (.docx) oder PDF: Summenformel, Ion und found. Mit Bericht und Rohdaten "
                    "ist der Wert aus dem Bericht vorgewählt; der aus den Rohdaten steht unter „gefunden“ zur Auswahl. "
                    "PDF: Bruker-SmartFormula-Bericht wird automatisch gelesen (calc. rechnet das Programm nach), bei "
                    "anderen PDFs übernimmt nur ein Klick in die Kandidatenliste einen Wert. Kopfdaten (Probe, Pfad, "
                    "Bearbeiter) werden nie übernommen.",
                    "Report of the mass spectrometry service (.docx) or PDF: formula, ion and found. With report and raw "
                    "data, the report value is preselected; the raw-data value can be chosen under “found”. PDF: a Bruker "
                    "SmartFormula report is read automatically (calc. is recomputed), for other PDFs only a click in "
                    "the candidate list takes a value. Header data (sample, path, operator) are never taken over."),
    "ms_img": ("Bild aus PDF", "Image from PDF"),
    "ms_img_tip": ("Eingebettetes Bild des PDF-Berichts als Abbildung (unverändert, in der SI als Bild aus dem Bericht "
                   "gekennzeichnet); ganze Seiten und kleine Logos werden nie angeboten",
                   "Embedded image of the PDF report as the figure (unchanged, marked in the SI as an image from the "
                   "report); whole pages and small logos are never offered"),
    "hrms_no_spectrum": ("Kein Spektrum gewählt – links ein Bild aus dem PDF wählen oder MS-Rohdaten (.d) laden.",
                         "No spectrum selected – choose an image from the PDF on the left or load MS raw data (.d)."),
    "ms_img_none": ("Keins (Spektrum aus den Rohdaten)", "None (spectrum from the raw data)"),
    "ms_img_none_plain": ("Keins", "None"),
    "ms_img_item": ("Bild {k} · Seite {page} · {w} × {h} px", "Image {k} · page {page} · {w} × {h} px"),
    "ms_cand_head": ("Kandidaten aus dem PDF (Klick übernimmt)", "Candidates from the PDF (click to take)"),
    "ms_cand_mz": ("m/z", "m/z"),
    "ms_cand_ppm": ("Δ [ppm]", "Δ [ppm]"),
    "ms_cand_line": ("Zeile im PDF", "Line in the PDF"),
    "ms_cand_tip": ("Zahlen mit mindestens drei Nachkommastellen bis ± 2 Da um calc., mit ihrer Textzeile und der "
                    "Abweichung found − calc.; nichts ist vorgewählt, ein Klick übernimmt den Wert als found "
                    "(„aus PDF gewählt“). Zeilen mit Kopfdaten (Probe, Name, Pfad, Datum) fehlen bewusst.",
                    "Numbers with at least three decimals within ± 2 Da of calc., with their text line and the "
                    "deviation found − calc.; nothing is preselected, a click takes the value as found (“from PDF”). "
                    "Lines with header data (sample, name, path, date) are left out on purpose."),
    "ms_cand_is_calc": ("= calc.", "= calc."),
    "ms_cand_is_calc_tip": ("Gleich dem berechneten Wert auf 4 Stellen: vermutlich calc. im PDF, kein gemessener Wert",
                            "Equal to the calculated value at 4 decimals: probably calc. in the PDF, not a measured value"),
    "ms_cand_need_formula": ("PDF-Kandidaten erscheinen mit der Summenformel (Tab Verbindung)",
                             "PDF candidates appear once the formula is set (Compound tab)"),
    "ms_cand_none": ("⚠ im PDF keine Zahl bis ± {d} Da um calc. – Ion/Addukt prüfen oder found von Hand eintragen",
                     "⚠ no number within ± {d} Da of calc. in the PDF – check the ion/adduct or enter found manually"),
    "ms_cand_choose": ("found: Wert in der Kandidatenliste anklicken oder von Hand eintragen",
                       "found: click a value in the candidate list or enter it manually"),
    "ms_pdf_entry": ("Aus PDF gewählt: {mz}  ({ppm} ppm)", "From PDF: {mz}  ({ppm} ppm)"),
    "ms_manual": ("Manuell (m/z)", "Manual (m/z)"),
    "ms_manual_long": ("found von Hand (m/z)", "found entered manually (m/z)"),
    "ms_manual_none": ("Kein Wert", "No value"),
    "ms_manual_tip": ("Gemessenes m/z von Hand eintragen (4 Nachkommastellen); wird als found gewählt und als „manuell“ "
                      "gekennzeichnet. 0 bzw. leeren nimmt den Wert zurück.",
                      "Enter the measured m/z manually (4 decimals); it is chosen as found and marked “manual”. 0 or "
                      "clearing removes the value."),
    "ms_manual_entry": ("Manuell: {mz}  ({ppm} ppm)", "Manual: {mz}  ({ppm} ppm)"),
    "ms_pdf_kind_smartformula": ("SmartFormula", "SmartFormula"),
    "ms_pdf_kind_text": ("per Klick", "by click"),
    "ms_found_none": ("Nicht gewählt", "Not chosen"),
    "ms_sf_ion_differs": ("⚠ Ionenformel im Bericht ({rep}) passt nicht zum gewählten Ion ({own})",
                          "⚠ ion formula in the report ({rep}) does not match the chosen ion ({own})"),
    "ms_sf_calc_differs": ("⚠ calc. im Bericht ({rep}) weicht vom berechneten Wert ({own}) ab – in der Zeile steht {own}",
                           "⚠ calc. in the report ({rep}) differs from the computed value ({own}) – the line uses {own}"),
    "ms_pdf_ionis": ("⚠ Ionisierung im Bericht nicht eindeutig: {ion} angenommen", "⚠ ionization not clear in the report: {ion} assumed"),
    "ms_pdf_bad": ("{name}: kein lesbares PDF", "{name}: not a readable PDF"),
    "ms_pdf_no_text": ("{name}: PDF ohne Textebene (Scan) – Werte von Hand eintragen", "{name}: PDF without a text layer (scan) – enter the values manually"),
    "line_ir": ("IR-Zeile für die SI", "IR line for the SI"),
    "line_ea": ("EA-Zeile für die SI", "EA line for the SI"),
    "line_ms": ("HRMS-Zeile für die SI", "HRMS line for the SI"),
    "line_nmr": ("NMR-Zeile für die SI", "NMR line for the SI"),
    "si_caption_text": ("Fertige Unterschrift", "Finished caption"),
    "si_caption_empty": ("Noch keine Bildunterschrift: sie erscheint mit der ersten Abbildung.",
                         "No caption yet: it appears with the first figure."),
    "ms_copy": ("HRMS-Zeile kopieren (für Word)", "Copy HRMS line (for Word)"),
    "ir_copy": ("IR-Zeile kopieren (für Word)", "Copy IR line (for Word)"),
    "ea_copy": ("EA-Zeile kopieren (für Word)", "Copy EA line (for Word)"),
    "uv_copy": ("UV-Vis-Zeile kopieren (für Word)", "Copy UV-Vis line (for Word)"),
    "ms_raw": ("MS-Rohdaten (.d)", "MS raw data (.d)"),
    "ms_raw_tip": ("Bruker-Messordner (.d) mit analysis.baf und analysis.sqlite (z. B. timsTOF); gelesen werden die "
                   "Linienspektren des Geräts. In die Verbindung kommen nur diese beiden Dateien. Mit Bericht der Massenabteilung "
                   "bleibt dessen found vorgewählt; die .d liefert Spektrum, Chromatogramm und den Vergleichswert.",
                   "Bruker measurement folder (.d) with analysis.baf and analysis.sqlite (e.g. timsTOF); the "
                   "instrument's line spectra are read. Only these two files are copied into the compound. With a report from "
                   "the MS department its found value stays preselected; the .d gives the spectrum, chromatogram and the "
                   "value for comparison."),
    "ms_raw_bad": ("kein Bruker-Messordner mit analysis.baf und analysis.sqlite",
                   "not a Bruker measurement folder with analysis.baf and analysis.sqlite"),
    "ms_rt": ("LC-Peak (RT)", "LC peak (RT)"),
    "ms_rt_auto": ("Automatisch", "Automatic"),
    "ms_rt_auto_tip": ("Zusammenhängende Spektren um das Maximum des Ionenstroms (± 10 ppm um calc.) mit mindestens "
                       "50 % der Maximalintensität", "Contiguous spectra around the maximum of the ion current "
                       "(± 10 ppm around calc.) with at least 50 % of the maximum intensity"),
    "ms_raw_entry": ("Rohdaten: {mz}  (Mittel über {n} Spektren, {ppm} ppm)",
                     "Raw data: {mz}  (mean over {n} spectra, {ppm} ppm)"),
    "ms_raw_col_n": ("Spektren", "Spectra"),
    "ms_raw_col_scans": ("Einzelscans (m/z)", "Single scans (m/z)"),
    "ms_raw_col_sd": ("Streuung", "Scatter"),
    "ms_raw_note": ("Rohdaten: found = intensitätsgewichtetes Mittel; einzelne Scans können in der 4. Nachkommastelle "
                    "abweichen.",
                    "Raw data: found = intensity-weighted mean; single scans may differ in the 4th decimal."),
    "ms_raw_few": ("Nur {n} Spektren im LC-Peak – das Mittel ist unsicher.",
                   "Only {n} spectra in the LC peak – the mean is uncertain."),
    "ms_raw_vs_rep": ("Mittel aus den Rohdaten weicht um {d} mDa vom Wert im Bericht ab.",
                      "Mean from the raw data differs by {d} mDa from the value in the report."),
    "ms_raw_none": ("Ion in den Rohdaten nicht gefunden (± 10 ppm um calc.).",
                    "Ion not found in the raw data (± 10 ppm around calc.)."),
    "ms_polarity_raw": ("⚠ die Rohdaten sind im Modus {rep}MS gemessen", "⚠ the raw data were measured in {rep}MS mode"),
    "compound_formula": ("Summenformel", "Formula"),
    "ms_adduct": ("Ion", "Ion"),
    "ms_part": ("Ion des Salzes", "Salt ion"),
    "ms_part_tip": ("Die Verbindung ist ein Salz: gemessen wird ein geladener Teil (Kation im positiven, Anion im negativen "
                    "Modus). Molmasse und Elementaranalyse gelten weiter für das ganze Salz.",
                    "The compound is a salt: what is measured is one charged part (cation in positive, anion in negative "
                    "mode). Molar mass and elemental analysis still refer to the whole salt."),
    "ms_part_cation": ("Kation {f}", "Cation {f}"),
    "ms_part_anion": ("Anion {f}", "Anion {f}"),
    "ms_part_salt": ("Ganzes Salz {f}", "Whole salt {f}"),
    "formula_salt_bad": ("Salz {f} nicht lesbar – Schreibweise z. B. [C10H16N]+ [PF6]- oder [C8H22N2]2+ 2[PF6]-",
                         "Salt {f} not readable – write e.g. [C10H16N]+ [PF6]- or [C8H22N2]2+ 2[PF6]-"),
    "ms_found": ("Gefunden (m/z)", "Found (m/z)"),
    "ms_found_tip": ("Gemessene m/z aus den Spektren im Bericht und das Mittel aus den Rohdaten; vorgewählt ist der "
                     "Wert im Bericht am nächsten am berechneten (SmartFormula-PDF: die Zeile des gewählten Ions), ohne "
                     "Bericht das Mittel aus den Rohdaten. Aus einem anderen PDF nur per Klick; dazu der Wert von Hand.",
                     "Measured m/z from the spectra in the report and the mean from the raw data; preselected is the "
                     "report value closest to the calculated one (SmartFormula PDF: the row of the chosen ion), without "
                     "a report the raw-data mean. From another PDF only by a click; plus the manual value."),
    "ms_no_formula": ("keine – im Tab Verbindung festlegen oder MS-Bericht laden",
                      "none – set it in the Compound tab or load an MS report"),
    "ea_no_formula": ("keine – im Tab Verbindung festlegen oder im Tab HRMS den MS-Bericht laden",
                      "none – set it in the Compound tab or load the MS report in the HRMS tab"),
    "ms_src_project": ("Verbindung",
                       "compound"),
    "ms_src_report_struct": ("aus der Struktur im MS-Bericht", "from the structure in the MS report"),
    "ms_take_compound": ("Verbindung aus dem MS-Bericht übernehmen", "Take the compound from the MS report"),
    "ms_take_compound_tip": ("Name, Formel und Molmasse aus dem ChemDraw-Objekt im Bericht. Die Struktur wird über RDKit "
                             "neu gezeichnet (Ersatzzeichnung) – für Abbildungen die eigene CDXML (mit SVG/PDF) nehmen.",
                             "Name, formula and molar mass from the ChemDraw object in the report. The structure is redrawn "
                             "with RDKit (substitute drawing) – for figures use your own CDXML (with SVG/PDF)."),
    "ms_take_replace": ("Die Verbindung hat schon eine Struktur. Durch die aus dem MS-Bericht ersetzen (Ersatzzeichnung)?",
                        "The compound already has a structure. Replace it with the one from the MS report (substitute "
                        "drawing)?"),
    "ms_form_vs_struct": ("⚠ im Bericht passen Formelfeld ({f}) und Struktur ({s}) nicht zusammen",
                          "⚠ in the report, formula field ({f}) and structure ({s}) do not match"),
    "ms_src_report": ("aus dem MS-Bericht", "from the MS report"),
    "ms_formula_mismatch": ("⚠ Formel im Bericht ({rep}) passt nicht zur Verbindung ({prj}) – richtiger Bericht?",
                            "⚠ formula in the report ({rep}) does not match the compound ({prj}) – right report?"),
    "ms_no_match": ("⚠ kein gemessenes m/z innerhalb 20 ppm – Ion/Addukt prüfen", "⚠ no measured m/z within 20 ppm – check the ion/adduct"),
    "ms_polarity": ("⚠ der Bericht ist im Modus {rep}MS gemessen", "⚠ the report was measured in {rep}MS mode"),
    "ms_dev": ("Abweichung found − calc = {ppm} ppm (nur zur Kontrolle, steht nicht in der Zeile)",
               "Deviation found − calc = {ppm} ppm (check only, not part of the line)"),
    "ms_dev_high": ("⚠ Abweichung über 5 ppm", "⚠ deviation above 5 ppm"),
    "compound_tip": ("Diese Verbindung (Name, ChemDraw, Formel, Molmasse): gilt in allen Tabs, z. B. ε, Fluoreszenz, IR "
                     "+ EA, HRMS und die SI",
                     "This compound (name, ChemDraw, formula, molar mass): applies in all tabs, e.g. ε, fluorescence, IR "
                     "+ EA, HRMS and the SI"),
    "stick_mode_tip": ("Ein gemeinsamer Faktor für Kurve und Striche: Kurvenmaximum = 1 (höchste Stelle der verbreiterten "
                       "Kurve im Normierungsbereich), stärkster Übergang = 1 oder Kurvenmaximum = 1 mit "
                       "Oszillatorstärke f als zweiter Skala rechts (jeder Strich so hoch wie seine Bande)",
                       "One common factor for curve and sticks: curve maximum = 1 (highest point "
                       "of the broadened curve in the normalization range), strongest transition = 1, or curve "
                       "maximum = 1 with oscillator strength f as a second scale on the right (each stick as high "
                       "as its band)"),
    "xr_prob_ball": ("gilt nur für die Stile Mercury und flach (Kugel-Stab: feste Kugelgröße)",
                     "only for the Mercury and flat styles (ball and stick: fixed sphere size)"),
    "syn_output_hint": ("Erscheint im SI-Export (Datei → SI-Abschnitt exportieren); eigene Word-Datei: Tab „Export“.",
                        "Appears in the SI export (File → Export SI section); own Word file: tab “Export”."),
    "compound_title": ("Verbindung",
                       "Compound"),
    "compound_name": ("Name / Probe", "Name / sample"),
    "compound_name_ph": ("Z. B. Probennummer", "E.g. sample number"),
    "guide_compound_title": ("Verbindung: Nummer, Struktur und Angaben für die SI",
                             "Compound: number, structure and details for the SI"),
    "guide_compound_files": ("Dateien: ChemDraw (CDXML) oder ein Bild der Struktur (SVG, PDF, PNG); Summenformel und "
                             "Molmasse kommen aus der CDXML (Isotope wie D inklusive) und sind änderbar",
                             "Files: ChemDraw (CDXML) or a picture of the structure (SVG, PDF, PNG); formula and molar "
                             "mass come from the CDXML (isotopes such as D included) and can be edited"),
    "guide_compound_steps": ("Nummer eintragen (die der SI, z. B. 3a), dazu die Laborbuch-Nr.\n"
                             "Struktur zeichnen oder mit „Wählen …“ laden\n"
                             "Schmelzpunkt und Literatur für die SI ergänzen",
                             "Enter the number (the one used in the SI, e.g. 3a) and the lab notebook no.\n"
                             "Draw the structure or load it with “Choose …”\n"
                             "Add melting point and reference for the SI"),
    "tab_compound": ("Verbindung", "Compound"),
    "step_path": ("Pfad", "Path"),
    "dft_prof_kind": ("Diagramm", "Diagram"),
    "dft_prof_energy": ("Energie", "Energy"),
    "dft_prof_sp_add_short": ("Einzelpunkte …", "Single points …"),
    "dft_prof_sp_rm_short": ("Einzelpunkte weg", "Drop single points"),
    "dft_prof_level_remove": ("Stufe entfernen", "Remove level"),
    "dft_prof_level_restore": ("Stufe zurückholen", "Restore level"),
    "dft_prof_preset": ("Vorlage", "Preset"),
    "dft_prof_w_level": ("Plateau [pt]", "Level [pt]"),
    "dft_prof_w_connector": ("Verbinder [pt]", "Connector [pt]"),
    "dft_prof_card_levels": ("Stufen und Rechnungen", "Levels and Calculations"),
    "dft_prof_card_edges": ("Verbinder", "Connectors"),
    "dft_prof_card_style": ("Stil des Diagramms", "Diagram Style"),
    "dft_prof_card_size": ("Größe", "Size"),
    "dft_prof_edges_hint": ("Im Bild am Ende eines Plateaus ziehen und auf einem anderen loslassen, oder hier zwei "
                            "Plateaus wählen. Den gewählten Verbinder ändern die Felder unter der Tabelle.",
                            "Drag from the end of a plateau onto another one in the figure, or choose two plateaus "
                            "here. The fields below the table change the selected connector."),
    "dft_prof_edge_from": ("Von", "From"),
    "dft_prof_edge_to": ("Nach", "To"),
    "dft_prof_edge_line": ("Linie", "Line"),
    "dft_prof_edge_arrow": ("Pfeilspitze", "Arrowhead"),
    "dft_prof_edge_text": ("Text", "Text"),
    "dft_prof_edge_add": ("Verbinden", "Connect"),
    "dft_prof_edge_reset": ("Aus Schritt und Pfad", "From step and path"),
    "dft_prof_edge_reset_tip": ("Eigene Verbinder verwerfen: wieder je Pfadbuchstabe in der Reihenfolge der Schritte",
                                "Discard own connectors: again per path letter in the order of the steps"),
    "dft_prof_line_default": ("Standard", "Default"),
    "dft_prof_line_dashed": ("Gestrichelt", "Dashed"),
    "dft_prof_line_solid": ("Durchgezogen", "Solid"),
    "dft_prof_line_dotted": ("Gepunktet", "Dotted"),
    "dft_prof_line_curve": ("Geschwungen", "Curved"),
    "dft_prof_line_wavy": ("Wellenlinie", "Wavy"),
    "dft_prof_line_none": ("Keine", "None"),
    "dft_prof_preset_classic": ("Klassisch", "Classic"),
    "dft_prof_preset_curves": ("Kurven", "Curves"),
    "dft_prof_preset_colour": ("Farbig", "Colour"),
    "dft_prof_preset_minimal": ("Minimal", "Minimal"),
    "dft_prof_preset_article": ("Artikel", "Article"),
    "dft_prof_unit": ("Einheit", "Unit"),
    "dft_prof_unit_tip": ("Einheit der Energien im Bild, an der Achse und in der Unterschrift. Umgerechnet wird aus den\n"
                          "Rechnungen: 1 kcal = 4.184 kJ, 1 eV = 96.4853 kJ mol⁻¹ (eV mit zwei Nachkommastellen).",
                          "Unit of the energies in the figure, on the axis and in the caption. Converted from the\n"
                          "calculations: 1 kcal = 4.184 kJ, 1 eV = 96.4853 kJ mol⁻¹ (eV with two decimals)."),
    "dft_prof_level_width": ("Plateaubreite", "Level width"),
    "dft_prof_level_width_tip": ("Länge der Plateaulinien in Schritten (ein Plateau mit eigener Breite behält sie).",
                                 "Length of the level lines in steps (a level with its own width keeps it)."),
    "dft_prof_card_labels": ("Beschriftung", "Labels"),
    "dft_prof_label_pos": ("Lage", "Position"),
    "dft_prof_labels_split": ("Wert oben, Name unten", "Value above, name below"),
    "dft_prof_labels_below": ("Beide unter dem Plateau", "Both below the level"),
    "dft_prof_labels_above": ("Beide über dem Plateau", "Both above the level"),
    "dft_prof_label_font": ("Schrift", "Font"),
    "dft_prof_font_normal": ("Normal", "Regular"),
    "dft_prof_font_bold": ("Fett", "Bold"),
    "dft_prof_font_italic": ("Kursiv", "Italic"),
    "dft_prof_font_bold_italic": ("Fett kursiv", "Bold italic"),
    "dft_prof_axis_title": ("Achsentitel", "Axis title"),
    "dft_prof_axis_title_tip": ("Eigener Titel der Energieachse, z. B. „ΔG (298.15 K) | ({unit})“: „ | “ beginnt eine neue\n"
                                "Zeile, {unit} wird durch die gewählte Einheit ersetzt. Leer = automatisch.",
                                "Own title of the energy axis, e.g. \"ΔG (298.15 K) | ({unit})\": \" | \" starts a new\n"
                                "line, {unit} is replaced by the chosen unit. Empty = automatic."),
    "dft_prof_signed": ("Vorzeichen", "Signs"),
    "dft_prof_signed_tip": ("Werte mit Vorzeichen: +18.9, ±0.0, −50.1.", "Values with a sign: +18.9, ±0.0, −50.1."),
    "dft_prof_card_sections": ("Abschnitte", "Sections"),
    "dft_prof_section_add": ("Abschnitt …", "Section …"),
    "dft_prof_section_text": ("Text", "Text"),
    "dft_prof_section_from": ("Von", "From"),
    "dft_prof_section_to": ("Bis", "To"),
    "dft_prof_sections_none": ("Keine Abschnitte.", "No sections."),
    "dft_prof_sections_tip": ("Balken unter dem Profil mit Text, z. B. für zwei Reaktionswege. „von“ und „bis“ sind\n"
                              "Positionen in Schritten wie bei den Plateaus; Doppelklick ändert eine Zelle.",
                              "Bar below the profile with a text, e.g. for two reaction channels. \"from\" and \"to\" are\n"
                              "positions in steps like those of the levels; double-click edits a cell."),
    "dft_prof_preset_own": ("Eigene", "Custom"),
    "dft_prof_preset_tip": ("Stil in einem Zug setzen; Lage der Plateaus und Beschriftungen bleibt.\n"
                            "Artikel: ohne Rahmen, kräftige Plateaus, Name und Wert fett-kursiv unter dem Plateau.",
                            "Sets the style in one go; positions of levels and labels stay.\n"
                            "Article: no frame, heavy levels, name and value in bold italics below the level."),
    "dft_prof_scaled": ("Maßstäblich", "To scale"),
    "dft_prof_scaled_tip": ("Aus: schematisch, Höhen frei wählbar (steht dann im Bild und in der Unterschrift)",
                            "Off: schematic, heights can be chosen freely (stated in the figure and the caption)"),
    "dft_prof_path_colors": ("Farbe je Pfad", "Colour per path"),
    "dft_prof_labels_reset": ("Beschriftungen zurücksetzen", "Reset labels"),
    "dft_prof_labels_reset_tip": ("Verschobene Energien, Namen und Verbinder-Texte wieder an ihren Platz",
                                  "Put moved energies, names and connector texts back in place"),
    "compound_tab_empty": ("Struktur zeichnen", "Draw structure"),
    "compound_mw_ph": ("Aus der Zeichnung", "From the drawing"),
    "nav_grp_compound": ("Verbindung", "Compound"),
    "step_details": ("Angaben", "Details"),
    "compound_grp_name": ("Bezeichnung", "Name"),
    "compound_grp_si": ("Für die SI", "For the SI"),
    "compound_sample_no": ("Probennummer", "Sample number"),
    "compound_several": ("Die Zeichnung enthält {n} Moleküle: Summenformel und Molmasse gelten für alle zusammen. Für eine "
                         "Verbindung nur ein Molekül zeichnen (Salze ausgenommen).",
                         "The drawing contains {n} molecules: formula and molar mass refer to all of them together. Draw "
                         "one molecule per compound (salts excepted)."),
    "compound_charge_sum": ("Ladungen ergeben nicht null ({q}) – Gegenion fehlt?",
                            "Charges do not sum to zero ({q}) – counter-ion missing?"),
    "compound_file": ("Datei", "File"),
    "ir_linewidth": ("Linienbreite", "Line width"),
    "cv_group": ("Gruppe", "Group"),
    "cv_group_tip": ("Freies Feld, z. B. Lösungsmittel (THF, MeCN …): Datenreihe in den Auftragungen gegen die Scanrate",
                     "Free field, e.g. solvent (THF, MeCN …): data series in the plots against scan rate"),
    "cv_file_ref": ('Referenz der ausgewählten Messung', 'Reference of the Selected Measurement'),
    "cv_fref_global": ("Wie unter „Referenzierung“ (für alle)", "As under “Referencing” (for all)"),
    "cv_fref_internal": ("Eigener interner Standard", "Own internal standard"),
    "cv_fref_manual": ("Eigene feste Verschiebung", "Own fixed shift"),
    "cv_ref_mixed": ("Achtung: Messungen mit unterschiedlicher Referenz (Fc⁰/⁺ und Referenzelektrode) in einer Abbildung.",
                     "Note: measurements with different references (Fc⁰/⁺ and reference electrode) in one figure."),
    "cv_plot": ("Auftragung", "Plot"),
    "sec_gone": ("{n} Spektren fehlen im Projektordner und werden nicht gezeigt.", "{n} spectra are missing from the project folder and are not shown."),
    "drop_unknown": ("{name}: Dateityp nicht erkannt, nichts geladen.", "{name}: file type not recognized, nothing loaded."),
    "file_gone": ("{name} fehlt im Projektordner.", "{name} is missing from the project folder."),
    "si_series_failed": ("Serie {name} fehlt in der SI: {error}", "Series {name} is missing from the SI: {error}"),
    "dp_missing": ("Eingetragene Dateien fehlen und kommen nicht ins Datenpaket ({n}): {names}",
                   "Listed files are missing and will not be in the data package ({n}): {names}"),
    "sec_flt": ("Spektren", "Spectra"),
    "sec_merged_bad": ("{f}: Zeile {n} passt nicht zum Format „Merged spectral data“.",
                       "{f}: line {n} does not match the “Merged spectral data” format."),
    "sec_merged_axis": ("{f}: Wellenlängen fehlen oder steigen nicht an.",
                        "{f}: wavelengths are missing or not ascending."),
    "sec_none_read": ("Keine lesbaren Spektren: keine Datei ist BWSpec oder „Merged spectral data“ (geprüft: {n}).",
                      "No readable spectra: no file is BWSpec or “Merged spectral data” (checked: {n})."),
    "sec_mixed": ("BWSpec-Spektren und zusammengeführte Spektren nicht in einer Serie mischen.",
                  "Do not mix BWSpec and merged spectra in one series."),
    "sec_skipped": ("Nicht lesbare Dateien ausgelassen: {n}.", "Unreadable files skipped: {n}."),
    "sec_q_abs": ("Absorbanz", "absorbance"),
    "sec_q_raw": ("Rohsignal", "raw signal"),
    "sec_q_ask": ("Welche Messgröße enthalten die Dateien?", "Which quantity do the files contain?"),
    "sec_gap": ("Nummern lückenhaft: {n} Spektren fehlen in der Folge.", "Numbering has gaps: {n} spectra are missing."),
    "sec_time_break": ("Dateizeiten springen zwischen {a} und {b}: vielleicht zwei Messungen. Bitte prüfen.",
                       "File times jump between {a} and {b}: possibly two measurements. Please check."),
    "sec_map": ("Potentialzuordnung", "Potential Assignment"),
    "sec_map_mode": ("Zuordnung", "Assignment"),
    "sec_map_none": ("Keine (nur nach Nummer)", "None (by number only)"),
    "sec_map_interval": ("Start + Intervall", "Start + interval"),
    "sec_map_time": ("Tabelle: Nr. → Zeit", "Table: no. → time"),
    "sec_map_potential": ("Tabelle: Nr. → Potential", "Table: no. → potential"),
    "sec_map_start": ("Erstes Spektrum", "First spectrum"),
    "sec_map_start_tip": ("Zeit des ersten Spektrums auf der Zeitachse der Potentiostat-Datei (Spalte T).",
                          "Time of the first spectrum on the potentiostat time axis (column T)."),
    "sec_map_step": ("Intervall", "Interval"),
    "sec_map_step_tip": ("Abstand zweier Spektren. Die Integrationszeit ist kein Aufnahmeintervall.",
                         "Time between two spectra. The integration time is not the acquisition interval."),
    "sec_map_table_ph": ("Je Zeile: Nr; Wert oder von-bis; Wert\nz. B. 1-31; 0.95", "One per line: no; value or from-to; value\ne.g. 1-31; 0.95"),
    "sec_map_ok": ("Angaben bestätigt", "Details confirmed"),
    "sec_map_ok_tip": ("Die Dateien enthalten keine Zeiten. Erst mit dieser Bestätigung gilt die Zuordnung.",
                       "The files contain no times. The assignment only applies once confirmed."),
    "sec_map_bad": ("Zuordnung, Zeile {n}: erwartet „Nr; Wert“ oder „von-bis; Wert“.",
                    "Assignment, line {n}: expected “no; value” or “from-to; value”."),
    "sec_map_no_dta": ("Für diese Zuordnung fehlt die Potentiostat-Datei.", "This assignment needs the potentiostat file."),
    "sec_map_no_step": ("Intervall fehlt.", "Interval missing."),
    "sec_map_partial": ("{k} von {n} Spektren haben ein Potential; die übrigen liegen außerhalb der Messung oder der "
                        "Tabelle und werden nicht gezeigt.",
                        "{k} of {n} spectra have a potential; the others lie outside the measurement or the table "
                        "and are not shown."),
    "sec_map_empty": ("Kein Spektrum liegt in der Messung: Zuordnung prüfen.", "No spectrum lies within the measurement: check the assignment."),
    "sec_no_map": ("Keine Zeiten in den Dateien: Spektren nach Nummer, ohne Potential und ohne A(E)-Auswertung.",
                   "No times in the files: spectra by number, without potentials and without A(E) evaluation."),
    "ov_sec_raw": ("Rohsignal ist keine Absorbanz und kann nicht in den TD-DFT-Tab übernommen werden.",
                   "A raw signal is not absorbance and cannot be added to the TD-DFT tab."),
    "cv_plot_cv": ("Cyclovoltammogramm", "Cyclic voltammogram"),
    "cv_plot_dep": ("Elektrochem. Reversibilität: ΔEp gegen ν", "Electrochem. reversibility: ΔE_p vs. v"),
    "cv_plot_rs": ("Randles-Ševčík: i_p gegen √v", "Randles–Ševčík: i_p vs. √v"),
    "cv_plot_rs_v": ("Randles-Ševčík: i_p gegen v", "Randles–Ševčík: i_p vs. v"),
    "cv_plot_loglog": ("Diffusion: log i_p gegen log v", "Diffusion: log i_p vs. log v"),
    "cv_plot_ratio": ("Chem. Reversibilität: i_r/i_f gegen v", "Chem. reversibility: i_r/i_f vs. v"),
    "cv_plot_trumpet": ("Trumpet-Plot: E_p gegen log v", "Trumpet plot: E_p vs. log v"),
    "cv_plot_tip": ("Auftragungen gegen die Scanrate aus den Redoxpaaren aller sichtbaren Messungen, eine Datenreihe je "
                    "Gruppe. ΔE_p enthält auch den iR-Abfall (v. a. in THF); der Trumpet-Plot ist ohne k⁰-Auswertung "
                    "(dafür wären mehrere Dekaden Scanrate nötig).",
                    "Plots against scan rate from the redox couples of all visible measurements, one data series per "
                    "group. ΔE_p also contains the iR drop (especially in THF); the trumpet plot has no k⁰ analysis "
                    "(that would need several decades of scan rate)."),
    "cv_stack": ("Gestapelt", "Stacked"),
    "cv_stack_gap_tip": ("Abstand der gestapelten Kurven (1 = größte Kurvenhöhe)", "Gap between stacked curves (1 = largest curve height)"),
    "cv_e12_each": ("E½ an jeder Kurve", "E½ on every curve"),
    "cv_e12_each_long": ("E½ an jeder Kurve beschriften", "Label E½ on every curve"),
    "cv_peaklab": ("Beschriftung", "Labels"),
    "cv_peaklab_e12": ("E½ je Redoxpaar", "E½ per redox couple"),
    "cv_peaklab_epa": ("E_pa an den anodischen Peaks", "E_pa at the anodic peaks"),
    "cv_peaklab_epc": ("E_pc an den kathodischen Peaks", "E_pc at the cathodic peaks"),
    "cv_peaklab_both": ("E_pa und E_pc", "E_pa and E_pc"),
    "cv_peaklab_tip": ("Peakpotentiale als Zahl am jeweiligen Peak jeder Kurve, z. B. Probe und Ac₂Fc in einer Messung "
                       "(Redoxpaar für die Referenz dann ebenfalls als Fenster anlegen)",
                       "Peak potentials as a number at each peak of every curve, e.g. sample and Ac₂Fc in one "
                       "measurement (then also add a window for the reference couple)"),
    "cv_rates_needed": ("Für diese Auftragung mindestens zwei Scanraten je Gruppe mit ausgewertetem Redoxpaar laden.",
                        "For this plot, load at least two scan rates per group with an analysed redox couple."),
    "ov_add_exp": ("Messung …", "Measurement …"),
    "ov_add_sec": ("SEC …", "SEC …"),
    "ov_from_tabs": ("Aus Tabs", "From tabs"),
    "ov_from_tabs_tip": ("Serien aus UV-Vis (ε) und TD-DFT-Rechnungen aus dem DFT-Tab übernehmen, ohne sie neu zu laden "
                         "(Haken = schon in diesem Tab, Haken weg = entfernen). ε-Serien bleiben verknüpft: Messung, "
                         "Konzentration und Schichtdicke kommen immer aus dem ε-Tab.",
                         "Take series from UV-Vis (ε) and TD-DFT calculations from the DFT tab without loading them "
                         "again (tick = already in this tab, untick = remove). ε series stay linked: measurement, "
                         "concentration and path length always come from the ε tab."),
    "ov_from_tabs_none": ("Keine ε-Serie und keine TD-DFT-Rechnung in den Tabs",
                          "No ε series and no TD-DFT calculation in the tabs"),
    "ov_eps_linked": ("UV-Vis (ε)", "UV-Vis (ε)"),
    "ov_eps_pick": ("Messung", "Measurement"),
    "ov_eps_pick_tip": ("Welche Messung der ε-Serie gezeigt wird. Automatisch: höchste Konzentration, deren Maximum ab "
                        "230 nm den Cutoff des ε-Tabs nicht überschreitet (gesättigte UV-Banden fallen so weg).",
                        "Which measurement of the ε series is shown. Automatic: highest concentration whose maximum "
                        "from 230 nm does not exceed the cutoff of the ε tab (saturated UV bands are skipped)."),
    "ov_eps_auto": ("Automatisch", "Automatic"),
    "ov_eps_gone": ("{name}: Serie nicht mehr im ε-Tab", "{name}: series no longer in the ε tab"),
    "ov_sec_none": ("Im SEC-Tab sind noch keine Spektren geladen.", "No spectra loaded in the SEC tab yet."),
    "ov_sec_pick": ("Serie: Bereich vom ersten bis zum letzten markierten Spektrum, ohne Markierung die ganze Serie; "
                    "alle Spektren mit demselben Faktor auf das Startspektrum normiert (Intensitätsverhältnisse und "
                    "isosbestische Punkte bleiben). Einzelne Spektren: jedes markierte für sich. SEC wird nie als ε "
                    "gezeigt (Schichtdicke und umgesetzte Konzentration der Dünnschichtzelle sind nicht genau bekannt).",
                    "Series: range from the first to the last marked spectrum, without marking the whole series; all "
                    "spectra normalized with the same factor to the start spectrum (intensity ratios and isosbestic "
                    "points are kept). Single spectra: each marked one on its own. SEC is never shown as ε (path "
                    "length and converted concentration in the thin-layer cell are not known exactly)."),
    "ov_sec_series": ("SEC-Serie", "SEC series"),
    "ov_sec_series_label": ("SEC {rng} ({n} Spektren)", "SEC {rng} ({n} spectra)"),
    "ov_sec_mode_all": ("Serie: alle Spektren (gemeinsam normiert)", "Series: all spectra (normalized together)"),
    "ov_sec_mode_ends": ("Serie: nur Anfang und Ende (gemeinsam normiert)",
                         "Series: start and end only (normalized together)"),
    "ov_sec_mode_single": ("Einzelne Spektren (jedes für sich normiert)", "Single spectra (each normalized on its own)"),
    "ov_sec_no_eps": ("„{name}“: SEC-Spektren nur normiert, nicht als ε – ausgelassen",
                      "“{name}”: SEC spectra only normalized, not as ε – skipped"),
    "ov_add_calc": ("TD-DFT …", "TD-DFT …"),
    "ov_add_esd": ("ESD …", "ESD …"),
    "ov_add_esd_tip": ("Vibronisches Spektrum aus ORCA ESD(ABS) (.spectrum, auch .spectrum.rootN) – fertig "
                       "verbreitert, nur normiert vergleichbar", "Vibronic spectrum from ORCA ESD(ABS) (.spectrum, "
                       "also .spectrum.rootN) – already broadened, comparable only when normalized"),
    "ov_esd_unit": ("Einheit der Datei", "File unit"),
    "ov_esd_unit_tip": ("x-Einheit der .spectrum-Datei (ORCA %ESD UNIT; steht nicht in der Datei). Beim Laden aus "
                        "der .inp/.out daneben, sonst aus dem Wertebereich bestimmt.",
                        "x unit of the .spectrum file (ORCA %ESD UNIT; not stored in the file). Taken from the "
                        ".inp/.out next to it when loading, otherwise from the value range."),
    "ov_esd_read": ("{name}: ESD-Spektrum, x in {unit} ({src})", "{name}: ESD spectrum, x in {unit} ({src})"),
    "ov_esd_src_input": ("aus der Eingabe", "from the input"),
    "ov_esd_src_range": ("aus dem Wertebereich – bitte prüfen", "from the value range – please check"),
    "ov_esd_src_user": ("vorgegeben", "set by user"),
    "ov_esd_norm_only": ("„{name}“: ESD-Intensität ohne gesicherte Einheit – nur im Modus „Normiert“ gezeigt",
                         "“{name}”: ESD intensity has no confirmed unit – shown only in “Normalized” mode"),
    "esd_bad": ("{name}: kein ORCA-ESD-Spektrum (Kopf „Energy TotalSpectrum …“ fehlt).",
                "{name}: not an ORCA ESD spectrum (header “Energy TotalSpectrum …” missing)."),
    "fl_esd": ("Berechnet (ESD)", "Calculated (ESD)"),
    "fl_esd_shift_tip": ("Berechnete Emission (ORCA ESD(FLUOR), .spectrum) in der Energie verschieben; wird in der "
                         "Bildunterschrift genannt", "Shift the calculated emission (ORCA ESD(FLUOR), .spectrum) in "
                         "energy; stated in the caption"),
    "ov_name": ("Name", "Name"),
    "ov_color": ("Farbe", "Colour"),
    "ov_type": ("Typ", "Type"),
    "ov_exp": ("Messung", "measured"),
    "ov_states": ("Zustände", "states"),
    "ov_details": ('Ausgewähltes Spektrum', 'Selected Spectrum'),
    # Verbindungen vergleicht das Projekt (Projektseite › Vergleich), nicht mehr der TD-DFT-Tab (1.2.0)
    "ov_cmp": ("Vergleich", "Comparison"),
    "ov_cmp_where": ("Verbindungen im Projekt", "Compounds in the project"),
    "ov_cmp_open": ("Öffnen …", "Open …"),
    "ov_cmp_open_tip": ("Zur Projektseite, Reiter „Vergleich“: Spektren mehrerer Verbindungen in einem Bild, normiert auf\n"
                        "eine Bande, Strukturen in Kurvenfarbe, auch in der Gesamt-SI.",
                        "To the project page, tab “Comparison”: spectra of several compounds in one figure, normalized to\n"
                        "one band, structures in curve colour, also in the combined SI."),
    "ov_cmp_old": ("Ältere Abbildung: ihre Struktur je Spektrum bleibt so; neue Vergleiche verschiedener Verbindungen "
                   "im Projekt.",
                   "Older figure: its structure per spectrum stays as it is; new comparisons of different compounds "
                   "in the project."),
    "ov_own_norm": ("Eigener (statt „Normierung“ unten)", "Own (instead of “Normalization” below)"),
    "ov_norm_window": ("Normierung [nm]", "Normalization [nm]"),
    "ov_norm_window_long": ("Normierungsbereich [nm]", "Normalization range [nm]"),
    "ov_fwhm": ("Breite (FWHM)", "Width (FWHM)"),
    "ov_shift": ("Verschiebung", "Shift"),
    "ov_display": ("Normierung", "Normalization"),
    "ov_ymode": ("y-Größe", "y quantity"),
    "ov_y_norm": ("Normiert (auf die Bande von Interesse)", "Normalized (to the band of interest)"),
    "ov_y_eps": ("ε [10³ M⁻¹ cm⁻¹]", "ε [10³ M⁻¹ cm⁻¹]"),
    "ov_y_abs": ("Absorbanz (wie gemessen)", "Absorbance (as measured)"),
    "ov_ymode_tip": ("ε: Messungen brauchen Konzentration und Schichtdicke (SEC entfällt). Absorbanz: Messungen und "
                     "SEC wie gemessen, ohne TD-DFT.",
                     "ε: measurements need concentration and path length (SEC is left out). Absorbance: measurements "
                     "and SEC as measured, without TD-DFT."),
    "ov_calc_no_abs": ("„{name}“: TD-DFT hat keine Absorbanz (c, d unbekannt) – ε oder normiert wählen",
                       "“{name}”: TD-DFT has no absorbance (c, d unknown) – choose ε or normalized"),
    "ov_triplets": ("Tripletts markieren", "Mark triplets"),
    "ov_triplets_long": ("Triplett-Zustände markieren (f = 0)", "Mark triplet states (f = 0)"),
    "ov_triplets_tip": ("Formal spinverbotene Triplett-Anregungen als gestrichelte Marken fester Höhe;\n"
                        "sie tragen nicht zur Kurve bei. Nur Rechnungen ohne SOC (mit SOC haben die\n"
                        "gemischten Zustände echte Intensität).",
                        "Formally spin-forbidden triplet excitations as dashed marks of fixed height;\n"
                        "they do not contribute to the curve. Only calculations without SOC (with SOC the\n"
                        "mixed states have real intensity)."),
    "ov_combine": ("Kombinieren", "Combine"),
    "ov_combine_tip": ("Markierte TD-DFT-Rechnungen (Strg/Shift) zu einem Spektrum zusammenführen: erst alle\n"
                       "Übergänge sammeln, dann gemeinsam verbreitern. Die Originale werden ausgeblendet.",
                       "Merge the selected TD-DFT calculations (Ctrl/Shift) into one spectrum: collect all\n"
                       "transitions first, then broaden them together. The originals are hidden."),
    "ov_combine_need2": ("Bitte mindestens zwei TD-DFT-Einträge markieren (Strg- bzw. Shift-Klick).",
                         "Please select at least two TD-DFT entries (Ctrl or Shift click)."),
    "ov_combine_dup": ("WARNUNG: {a} und {b} enthalten {n} gleiche Zustände – diese zählen jetzt doppelt.",
                       "WARNING: {a} and {b} share {n} identical states – they are now counted twice."),
    "ov_weights": ("Gewichte", "Weights"),
    "ov_weights_tip": ("Ein Faktor je Rechnung, auf die Oszillatorstärken angewandt (Standard 1 = Summe).\n"
                       "Konformere/Spezies z. B. 0.7 0.3 (Boltzmann- oder Molenbruch).",
                       "One factor per calculation, applied to the oscillator strengths (default 1 = sum).\n"
                       "Conformers/species e.g. 0.7 0.3 (Boltzmann or mole fraction)."),
    "ov_baseline": ("Basislinie abziehen", "Subtract baseline"),
    "ov_baseline_long": ("Basislinie (Offset) abziehen", "Subtract baseline (offset)"),
    "ov_sticks": ("TD-DFT-Striche", "TD-DFT sticks"),
    "ov_sticks_long": ("TD-DFT-Übergänge als Striche", "TD-DFT transitions as sticks"),
    "ov_no_signal": ("„{name}“: kein Signal im Normierungsbereich {lo:g}–{hi:g} nm – ausgelassen",
                     "“{name}”: no signal in the normalization range {lo:g}–{hi:g} nm – skipped"),
    "ov_need_conc": ("„{name}“: für ε Konzentration (und bei mg mL⁻¹ Molmasse) eintragen – ausgelassen",
                     "“{name}”: enter concentration (and molar mass for mg mL⁻¹) for ε – skipped"),
    "ov_struct_color": ("Struktur in Kurvenfarbe", "Structure in curve colour"),
    "ov_soc": ("Spin-Bahn-Kopplung", "Spin–orbit coupling"),
    "soc_soc": ("mit SOC", "with SOC"),
    "soc_nosoc": ("ohne SOC", "without SOC"),
    "ov_scale_offset": ("Skalierung / Versatz", "Scale / offset"),
    "ov_line": ("Linie", "Line"),
    "ls_solid": ("Durchgezogen", "Solid"),
    "ls_dashed": ("Gestrichelt", "Dashed"),
    "ls_dotted": ("Gepunktet", "Dotted"),
    "ls_dashdot": ("Strich-Punkt", "Dash-dot"),
    "stick_mode": ("TD-DFT-Normierung", "TD-DFT scaling"),
    "stick_mode_long": ("TD-DFT-Normierung", "TD-DFT normalization"),
    "stick_max": ("Stärkster Übergang = 1", "Strongest transition = 1"),
    "stick_band": ("Kurvenmaximum = 1", "Curve maximum = 1"),
    "stick_faxis": ("Kurvenmaximum = 1, rechts zusätzlich f", "Curve maximum = 1, f on the right axis"),
    "ov_faxis_stack": ("f-Achse ausgelassen: gestapelt bzw. mit Versatz beginnt die Kurve nicht bei y = 0 "
                       "(Striche wie „Kurvenmaximum = 1“)",
                       "f axis omitted: stacked or offset curves do not start at y = 0 (sticks as “Curve maximum = 1”)"),
    "ov_faxis_mixed": ("f-Achse ausgelassen: die Rechnungen haben verschiedene Maßstäbe (FWHM/Normierung)",
                       "f axis omitted: the calculations use different scales (FWHM/normalization)"),
    "fl_data": ("Spektren", "Spectra"),
    "fl_abs": ("Absorption", "Absorption"),
    "fl_em": ("Emission", "Emission"),
    "fl_ex": ("Anregung λex", "Excitation λex"),
    "fl_mask": ("Streulicht ausblenden", "Hide scattered light"),
    "fl_mask_long": ("Streulicht bei λex und 2·λex ausblenden", "Hide scattered light at λex and 2·λex"),
    "fl_abs_window": ("Bande [nm]", "Band [nm]"),
    "fl_abs_window_long": ("Bande von Interesse [nm]", "Band of interest [nm]"),
    "fl_ex_tip": ("Für A(λex) mit Innenfilter-Hinweis und für die Streulicht-Maske; die Kurven ändert es sonst nicht.",
                  "Used for A(λex) with the inner-filter warning and for the scattered-light mask; it does not "
                  "change the curves otherwise."),
    "fl_abs_window_tip": ("Die Absorption wird in diesem Fenster auf ihr Maximum = 1 normiert, dort liegt λabs. "
                          "Die Emission wird auf ihr Maximum im ganzen Spektrum normiert.",
                          "The absorption is normalized to its maximum = 1 in this window, where λabs is taken. "
                          "The emission is normalized to its maximum over the whole spectrum."),
    "fl_eps_tip": ("Nur Beschriftung am Absorptionslabel (z. B. aus dem Tab UV-Vis (ε)), wird nicht gerechnet.",
                   "Label text at the absorption label only (e.g. from the UV-Vis (ε) tab), not used in any "
                   "calculation."),
    "fl_eps_ph": ("Optional, z. B. 23604", "Optional, e.g. 23604"),
    "fl_stokes_label": ("Stokes-Verschiebung",
                        "Stokes shift"),
    "fl_stokes_label_long": ("Stokes-Verschiebung im Bild", "Stokes shift in the figure"),
    "fl_stokes": ("Stokes-Verschiebung: {cm} cm⁻¹ ({nm:.0f} nm)", "Stokes shift: {cm} cm⁻¹ ({nm:.0f} nm)"),
    "fl_a_ex": ("Absorbanz bei λex = {ex:.0f} nm: {a:.3f}", "Absorbance at λex = {ex:.0f} nm: {a:.3f}"),
    "fl_inner_filter": ("⚠ A > {lim:g}: Innenfiltereffekt möglich (Emission verzerrt, Quantenausbeute zu "
                        "niedrig) – gilt nur, wenn Absorption und Emission von derselben Lösung stammen.",
                        "⚠ A > {lim:g}: inner-filter effect possible (distorted emission, quantum yield too "
                        "low) – only applies if absorption and emission were measured on the same solution."),
    "fl_images": ("Bilder", "Images"),
    "fl_photo_day": ("Foto Tageslicht", "Photo daylight"),
    "fl_photo_uv": ("Foto unter UV", "Photo under UV"),
    # Fluoreszenz, zeitaufgelöst und Kennwerte (tabs/fluo_tau.py)
    "fluo_tau_exc": ("Anregung", "Excitation"),
    "fluo_tau_exc_short": ("Anr.", "Exc."),
    "fluo_tau_exc_det": ("Detektion λem", "Detection λem"),
    "fluo_tau_exc_det_tip": ("Emissionswellenlänge, bei der das Anregungsspektrum aufgenommen wurde (nur für die "
                             "Bildunterschrift).", "Emission wavelength at which the excitation spectrum was recorded "
                             "(caption only)."),
    "fluo_tau_none": ("Keine Angabe", "Not given"),
    "fluo_tau_data": ("Abklingkurve", "Decay"),
    "fluo_tau_decay": ("Abklingkurve", "Decay"),
    "fluo_tau_irf": ("IRF", "IRF"),
    "fluo_tau_flt": ("Textdateien (*.txt *.csv *.dat *.asc)", "Text files (*.txt *.csv *.dat *.asc)"),
    "fluo_tau_unit": ("Zeit in der Datei", "Time in file"),
    "fluo_tau_unit_tip": ("Einheit der ersten Spalte. Nennt der Spaltenkopf ps, ns oder µs, wird sie beim Laden "
                          "übernommen.", "Unit of the first column. Taken over on loading when the column header names "
                          "ps, ns or µs."),
    "fluo_tau_ex": ("Anregung λex", "Excitation λex"),
    "fluo_tau_em": ("Detektion λem", "Detection λem"),
    "fluo_tau_fit": ("Lebensdauer", "Lifetime"),
    "fluo_tau_model": ("Modell", "Model"),
    "fluo_tau_n1": ("1 Exponential", "1 exponential"),
    "fluo_tau_n2": ("2 Exponentiale", "2 exponentials"),
    "fluo_tau_n_tip": ("I(t) = Σ A_i·exp(−t/τ_i) + B mit konstantem Untergrund B. Mit IRF: Faltung mit der IRF über die "
                       "ganze Kurve; ohne IRF: Fit ab dem Startpunkt nach dem Maximum.",
                       "I(t) = Σ A_i·exp(−t/τ_i) + B with constant background B. With IRF: reconvolution with the IRF "
                       "over the whole decay; without IRF: fit from the start point after the maximum."),
    "fluo_tau_start": ("Start nach Max.", "Start after max."),
    "fluo_tau_start_long": ("Fitbeginn nach dem Maximum", "Fit start after the maximum"),
    "fluo_tau_start_tip": ("Ohne IRF beginnt der Fit so viele ns nach dem Maximum der Kurve (Schwanzfit, keine "
                           "Entfaltung). Mit IRF entfällt das Feld.", "Without IRF the fit starts this many ns after "
                           "the maximum of the decay (tail fit, no deconvolution). Hidden with an IRF."),
    "fluo_tau_avg": ("τ für k_r, k_nr", "τ for k_r, k_nr"),
    "fluo_tau_avg_amp": ("Amplitudengewichtet", "Amplitude-weighted"),
    "fluo_tau_avg_int": ("Intensitätsgewichtet", "Intensity-weighted"),
    "fluo_tau_avg_tip": ("Bei zwei Exponentialen: welche mittlere Lebensdauer k_r = Φ/τ und k_nr = (1 − Φ)/τ verwenden. "
                         "amplitudengewichtet ΣA_iτ_i/ΣA_i, intensitätsgewichtet ΣA_iτ_i²/ΣA_iτ_i; beide stehen in der "
                         "Tabelle.", "With two exponentials: which average lifetime k_r = Φ/τ and k_nr = (1 − Φ)/τ use. "
                         "Amplitude-weighted ΣA_iτ_i/ΣA_i, intensity-weighted ΣA_iτ_i²/ΣA_iτ_i; both are in the table."),
    "fluo_tau_phi": ("Quantenausbeute", "Quantum yield"),
    "fluo_tau_phi_long": ("Fluoreszenzquantenausbeute Φ", "Fluorescence quantum yield Φ"),
    "fluo_tau_phi_ph": ("Φ, z. B. 0.42 (leer = keine)", "Φ, e.g. 0.42 (empty = none)"),
    "fluo_tau_phi_tip": ("Eigene Angabe (wird hier nicht bestimmt): 0 < Φ ≤ 1 oder in %. Nur für die Kennwerte "
                         "k_r und k_nr.", "Your value (not determined here): 0 < Φ ≤ 1 or in %. Only for k_r and k_nr."),
    "fluo_tau_page": ("Abklingkurve", "Decay"),
    "fluo_tau_empty": ("Keine Abklingkurve – links unter „Abklingkurve“ eine Textdatei (Zeit, Zählrate) laden.",
                       "No decay – load a text file (time, counts) under “Decay” on the left."),
    "fluo_tau_props": ("Kennwerte", "Properties"),
    "fluo_tau_props_empty": ("Noch keine Kennwerte – Absorption, Emission, Abklingkurve oder Φ angeben.",
                             "No properties yet – load absorption, emission, a decay or enter Φ."),
    "fluo_tau_col_comp": ("Komponente", "Component"),
    "fluo_tau_col_ci": ("95 % (τ) [ns]", "95% (τ) [ns]"),
    "fluo_tau_col_frac": ("Intensität [%]", "Intensity [%]"),
    "fluo_tau_c_abs": ("Abs.", "Abs."),
    "fluo_tau_c_em": ("Em.", "Em."),
    "fluo_tau_bg": ("Untergrund B", "Background B"),
    "fluo_tau_shift": ("IRF-Versatz [ps]", "IRF shift [ps]"),
    "fluo_tau_npts": ("Punkte im Fit", "Points in fit"),
    "fluo_tau_note_irf": ("Fit mit IRF-Faltung über die ganze Kurve.", "Fit with IRF reconvolution over the whole decay."),
    "fluo_tau_note_tail": ("Fit ohne IRF ab {s} ns nach dem Maximum (keine Entfaltung).",
                           "Fit without IRF from {s} ns after the maximum (no deconvolution)."),
    "fluo_tau_note_w": ("Poisson-gewichtet (Zählraten), Residuen gewichtet.",
                        "Poisson-weighted (counts), weighted residuals."),
    "fluo_tau_note_unw": ("Keine Zählraten: ungewichtet, kein χ².", "Not photon counts: unweighted, no χ²."),
    "fluo_tau_cols": ("Datei hat {n} Spalten: Zeit = Spalte 1, Intensität = Spalte 2.",
                      "File has {n} columns: time = column 1, intensity = column 2."),
    "fluo_tau_fit_fail": ("Kein Fit: {e}", "No fit: {e}"),
    "fluo_tau_bound": ("⚠ Eine Lebensdauer liegt am Rand des Suchbereichs: Modell oder Startpunkt prüfen.",
                       "⚠ A lifetime is at the edge of the search range: check model or start point."),
    "fluo_tau_phi_bad": ("⚠ Φ nicht verwendet: 0 < Φ ≤ 1 (oder in %).", "⚠ Φ not used: 0 < Φ ≤ 1 (or in %)."),
    "fluo_tau_rates_amp": ("k_r und k_nr mit der amplitudengewichteten mittleren Lebensdauer.",
                           "k_r and k_nr with the amplitude-weighted average lifetime."),
    "fluo_tau_rates_int": ("k_r und k_nr mit der intensitätsgewichteten mittleren Lebensdauer.",
                           "k_r and k_nr with the intensity-weighted average lifetime."),
    "fluo_tau_neg_amp": ("Eine Amplitude ist negativ (Anstieg): keine mittlere Lebensdauer, kein k_r/k_nr.",
                         "One amplitude is negative (rise): no average lifetime, no k_r/k_nr."),
    "fluo_tau_read_none": ("keine Zahlenspalten gefunden", "no numeric columns found"),
    "fluo_tau_read_short": ("nur {n} Datenzeilen (mindestens {m})", "only {n} data rows (at least {m})"),
    "fluo_tau_read_order": ("Zeit (Spalte 1) steigt nicht streng an", "time (column 1) is not strictly increasing"),
    "bands_add": ("Zusätzlich zu gefundenen", "In addition to found"),
    "bands_add_long": ("zusätzlich zu den automatisch gefundenen", "in addition to automatically found bands"),
    "find_shoulders": ("Schultern suchen", "Find shoulders"),
    "find_shoulders_long": ("Schultern automatisch suchen", "Find shoulders automatically"),
    "mark_sh": ("Schultern mit „(sh)“", "Shoulders with “(sh)”"),
    "mark_sh_long": ("Schultern im Bild mit „(sh)“ kennzeichnen", "Mark shoulders with “(sh)” in figure"),
    "label_index": ("λ und ε nummerieren", "Number λ and ε"),
    "label_index_long": ("λ und ε im Bild nummerieren (λ₁, ε₁ …)", "Number λ and ε in the figure (λ₁, ε₁ …)"),
    "label_index_tip": ("Indizes aufsteigend nach Wellenlänge, nur für Banden im Bild", "Indices in order of increasing "
                        "wavelength, only for bands shown in the figure"),
    "show_excl": ("Ausgeschlossene Punkte", "Excluded points"),
    "show_excl_long": ("ausgeschlossene Punkte im Inset (hohl)", "excluded points in inset (open symbols)"),
    "col_cut": ("Cutoff A", "Cutoff A"),
    "cut_tip": ("Häkchen bei λ: Bande im Bild zeigen. Doppelklick auf „Cutoff A“: eigener Cutoff für "
                "diese Bande (leer = global).",
                "Tick at λ: show band in figure. Double-click “Cutoff A”: own cutoff for this band "
                "(empty = global)."),
    "act_conc": ("Konzentrationen …", "Concentrations …"),
    "size": ("Größe", "Size"),
    "size_std": ("Standard (eng zugeschnitten)", "Standard (tight crop)"),
    "size_half_a4": ("Word: halbe A4-Seite (16 × 11 cm)", "Word: half A4 page (16 × 11 cm)"),
    "size_custom": ("Benutzerdefiniert", "Custom"),
    "size_wh": ("B × H", "W × H"),
    "formats": ("Formate", "Formats"),
    "chips_options": ("Optionen", "Options"),
    "chain_title": ("Rechenweg", "Processing Chain"),
    "chain_tip": ("So wird gerechnet: hervorgehobene Schritte sind mit den aktuellen Einstellungen aktiv.",
                  "How the data are processed: highlighted steps are active with the current settings."),
    "chain_dark": ("− k·dunkel", "− k·dark"),
    "chain_baseline": ("Basislinie", "Baseline"),
    "chain_mask": ("Ausblenden", "Masking"),
    "chain_smooth": ("Glätten", "Smoothing"),
    "chain_norm": ("Normieren", "Normalize"),
    "chain_cycle": ("Zyklus {n}", "Cycle {n}"),
    "chain_ref": ("Referenz Fc⁰/⁺", "Reference Fc⁰/⁺"),
    "chain_broad": ("Verbreiterung", "Broadening"),
    "chain_shift": ("Verschiebung", "Shift"),
    "chain_bands": ("Banden suchen", "Find bands"),
    "chain_ci": ("95-%-KI", "95% CI"),
    "tab_si_text": ("SI-Text", "SI Text"),
    "si_caption_title": ("Bildunterschrift", "Caption"),
    "si_methods_title": ("Methodentext", "Methods Text"),
    "si_copy": ("Kopieren", "Copy"),
    "si_caption_copied": ("Bildunterschrift kopiert", "Caption copied"),
    "si_caption_none": ("Noch keine Abbildung – keine Bildunterschrift.", "No figure yet – no caption."),
    "kpi_spectra": ("Spektren", "Spectra"),
    "kpi_sims": ("Simulationen", "Simulations"),
    "kpi_found": ("Gefunden", "Found"),
    "auto_range_tip": ("Automatisch: ganzer Bereich. Klicken für eigene Grenzen.",
                       "Automatic: full range. Click to set your own limits."),
    "auto_range_clear_tip": ("Feld leeren = wieder automatisch", "Clear the field = automatic again"),
    "reset_special_tip": ("Zurück auf „{what}“ (oder das Feld leeren)", "Back to '{what}' (or clear the field)"),
    "chips_figure": ("Im Bild", "In figure"),
    "img_size": ("Größe [% Plotbreite]", "Size [% of plot width]"),
    "struct_w_group_tip": ("Breite der breitesten Struktur. Mehrere Strukturen in einem Bild haben immer denselben\n"
                           "Maßstab (gleiche Bindungslänge); das Mausrad auf einer Struktur ändert alle.",
                           "Width of the widest structure. Several structures in one figure always share the same\n"
                           "scale (equal bond length); the mouse wheel on one structure changes all."),
    "xrange": ("λ-Bereich [nm]", "λ range [nm]"),
    "xrange_auto": ("Gesamt", "Full"),
    "conc_title": ("Konzentrationen eingeben", "Enter concentrations"),
    "conc_intro": ("Die Probennamen enthalten keine (vollständigen) Konzentrationsangaben. Bitte Konzentrationen "
                   "eintragen – Proben ohne Wert (z. B. Blindprobe) werden ignoriert. Die Angaben werden mit der "
                   "Verbindung gespeichert.",
                   "The sample names do not contain (complete) concentration information. Please enter concentrations – "
                   "samples without a value (e.g. blank) are ignored. The values are saved with the compound."),
    "col_sample": ("Probe", "Sample"),
    "col_series": ("Serie", "Series"),
    "col_conc": ("Konzentration", "Concentration"),
    "unit": ("Einheit", "Unit"),
    "dil_start": ("Start", "Start"),
    "unit_choose": ("– Bitte wählen –", "– Please choose –"),
    "unit_missing": ("Bitte die Konzentrationseinheit wählen.", "Please choose the concentration unit."),
    "start_missing": ("Bitte zuerst die Startkonzentration eintragen.", "Please enter the start concentration first."),
    "act_restart": ("Eingaben zu diesen Messdaten verwerfen …",
                    "Discard inputs for this measurement …"),
    "restart_q": ("Alle Eingaben zu „{name}“ verwerfen?\n\n"
                  "Konzentrationen, Molmassen, Strukturen, Fotos, Einstellungen und Layout im ε-Tab "
                  "werden zurückgesetzt. Die Messdateien bleiben unverändert.",
                  "Discard all inputs for “{name}”?\n\n"
                  "Concentrations, molar masses, structures, photos, settings and layout in the ε tab "
                  "are reset. The measurement files are not changed."),
    "mw_needed": ("⚠ Keine Molmasse: Ausgabe als a [L g⁻¹ cm⁻¹]. Für ε [M⁻¹ cm⁻¹] die Molmasse in der "
                  "Verbindung eintragen (Ändern …).",
                  "⚠ No molar mass: reported as a [L g⁻¹ cm⁻¹]. Enter the molar mass in the compound "
                  "(Edit …) to get ε [M⁻¹ cm⁻¹]."),
    "mw_differs": ("Diese Serie rechnet noch mit einem eigenen Wert, die Verbindung nennt {m} g mol⁻¹. "
                   "Verbindung ändern oder mit OK bestätigen, dann folgt die Serie.",
                   "This series still uses its own value, the compound says {m} g mol⁻¹. Change the compound or "
                   "confirm it with OK and the series follows."),
    "compound_edit": ("Ändern …", "Edit …"),
    "step_data": ("Daten", "Data"),
    "step_eval": ("Auswertung", "Evaluation"),
    "step_display": ("Darstellung", "Display"),
    "step_procedure": ("Vorschrift", "Procedure"),
    "step_amounts": ("Mengen", "Amounts"),
    "step_spectra": ("Spektren", "Spectra"),
    "step_nmr_line": ("NMR-Zeile", "NMR line"),
    "step_ir": ("IR", "IR"),
    "step_ea": ("Elementaranalyse", "Elemental analysis"),
    "step_next": ("Weiter: {s} →", "Next: {s} →"),
    "step_changed_tip": ("Hier weicht etwas vom Standard ab", "Something here differs from the default"),
    "caption_bar": ("Bildunterschrift", "Caption"),
    "mw_unused": ("Molmasse wird nicht verwendet: Konzentrationen sind in {u} angegeben.",
                  "Molar mass is not used: concentrations are given in {u}."),
    "dil_factor": ("Faktor", "Factor"),
    "dil_fill": ("Verdünnungsreihe ausfüllen", "Fill dilution series"),
    "dil_hint": ("Füllt die markierten Zeilen (oder alle) von oben nach unten: Start, Start/Faktor, …",
                 "Fills the selected rows (or all) top to bottom: start, start/factor, …"),
    "conc_none": ("Keine Probe mit Konzentration – nichts auszuwerten.",
                  "No sample with a concentration – nothing to analyse."),
    # ---- Format (Schrift, Rahmen) -----------------------------------------
    "menu_format": ("F&ormat", "F&ormat"),
    "act_text_format": ("Schrift und Rahmen …", "Fonts and frames …"),
    "tf_title": ("Schrift und Rahmen", "Fonts and Frames"),
    "tf_scope": ("Gilt für", "Applies to"),
    "tf_scope_global": ("alle Tabs (Standard)", "all tabs (default)"),
    "tf_scope_own": ("nur diesen Tab ({tab})", "this tab only ({tab})"),
    "tf_scope_hint": ("„alle Tabs“ ändert den Standard für jeden Tab ohne eigenes Format. Gezeigt wird nur, was dieser "
                      "Tab im Bild hat.", "“all tabs” changes the default for every tab without its own format. Only "
                      "what this tab has in its figure is shown."),
    "tf_no_text": ("Der Tab „{tab}“ hat keine Textformatierung (Abbildungen kommen fertig aus anderen Programmen). "
                   "Schrift und Rahmen stehen in den Tabs mit Abbildung im Schritt Darstellung.",
                   "The “{tab}” tab has no text formatting (figures come ready-made from other programs). Fonts and "
                   "frames are in the tabs with a figure, step Display."),
    "tf_grp_labels_cv": ("Labels an den Peaks (E½, Ep)", "Peak labels (E½, E_p)"),
    "tf_grp_labels_sec": ("Labels an den Banden (λ)", "Band labels (λ)"),
    "tf_grp_labels_epr": ("Labels im Spektrum", "Labels in the spectrum"),
    "tf_grp_labels_irms": ("Labels an den Banden (cm⁻¹)", "Band labels (cm⁻¹)"),
    "tf_grp_labels_hrms": ("Labels an den Peaks (m/z)", "Peak labels (m/z)"),
    "tf_grp_labels_xray": ("Atomlabels (Größe im Tab)", "Atom labels (size in the tab)"),
    "tf_grp_labels_dft": ("Atomlabels (Größe im Tab)", "Atom labels (size in the tab)"),
    "tf_grp_fonts": ("Schriften", "Fonts"),
    "tf_font": ("Textschrift", "Text font"),
    "tf_symbol_font": ("Symbolschrift", "Symbol font"),
    "tf_greek": ("Griechische Buchstaben (λ, ε) in der Symbolschrift",
                 "Greek letters (λ, ε) in the symbol font"),
    "tf_grp_labels": ("Labels an den Banden (λ / ε)", "Band labels (λ / ε)"),
    "tf_label_size": ("Schriftgröße", "Font size"),
    "tf_auto": ("Automatisch", "Automatic"),
    "tf_bold": ("Fett", "Bold"),
    "tf_italic": ("Kursiv", "Italic"),
    "tf_color": ("Farbe", "Colour"),
    "tf_grp_frames": ("Rahmen", "Frames"),
    "tf_axes_frame": ("Geschlossener Rahmen um den Plot (auch oben und rechts)",
                      "Closed frame around the plot (top and right too)"),
    "tf_struct_frame": ("Abgerundeter Rahmen um die Struktur", "Rounded frame around the structure"),
    # ---- Overlay: Stapeln --------------------------------------------------
    "ov_stack_grp": ('Stapeln und Achsen', 'Stacking and Axes'),
    "ov_stack": ("Gestapelt", "Stacked"),
    "ov_stack_tip": ("Kurven senkrecht übereinander, in der Reihenfolge der Liste (oben = oben).\n"
                     "Zusätzlich gilt der Versatz der einzelnen Kurve.",
                     "Curves stacked vertically in list order (top = top).\n"
                     "The offset of each curve is added on top."),
    "ov_gap": ("Abstand", "Spacing"),
    "ov_gap_tip": ("Abstand der Ebenen in y-Einheiten (normiert: 1 = eine Kurvenhöhe; ε-Modus: 10³ M⁻¹ cm⁻¹)",
                   "Spacing of the levels in y units (normalized: 1 = one curve height; ε mode: 10³ M⁻¹ cm⁻¹)"),
    "ov_yaxis": ("y-Achse", "y axis"),
    "yaxis_auto": ("Automatisch (gestapelt: ohne Zahlen)", "Automatic (stacked: no numbers)"),
    "yaxis_numbers": ("Mit Zahlen", "With numbers"),
    "yaxis_no_numbers": ("Ohne Zahlen und Teilstriche", "Without numbers and ticks"),
    "yaxis_off": ("Ausblenden", "Hide"),
    "ov_curve_labels": ("Namen an den Kurven", "Names at the curves"),
    "ov_curve_labels_long": ("Namen an den Kurven statt Legende", "Names at the curves instead of a legend"),
    "ov_zero_lines": ("Nulllinie je Ebene", "Zero line per level"),
    "ov_zero_lines_long": ("Nulllinie je Ebene (gestrichelt)", "Zero line per level (dashed)"),
    "ov_same_level": ("Ebene wie darüber", "Level as above"),
    "ov_same_level_long": ("Gleiche Stapelebene wie die Kurve darüber", "Same stacking level as the curve above"),
    "ov_same_level_tip": ("Z. B. TD-DFT direkt unter der zugehörigen Messung",
                          "E.g. TD-DFT directly with its measurement"),
    # ---- Cyclovoltammetrie -------------------------------------------------
    "tab_cv": ("CV", "CV"),
    "cv_files": ("Messungen (Gamry .DTA)", "Measurements (Gamry .DTA)"),
    "cv_add": ("Messung …", "Measurement …"),
    "cv_xrange": ("E-Bereich [V]", "E range [V]"),
    "cv_analysis": ("Auswertung", "Analysis"),
    "cv_cycle": ("Zyklus", "Cycle"),
    "cv_cycle_tip": ("Welcher Zyklus gezeigt und ausgewertet wird (zu groß = letzter vorhandener).",
                     "Which cycle is shown and analysed (too large = last available)."),
    "cv_couples": ("Redoxpaare", "Redox couples"),
    "cv_from": ("Von [V, Achse]", "From [V, axis]"),
    "cv_to": ("Bis [V, Achse]", "To [V, axis]"),
    "cv_couples_tip": ("Potentialfenster je Redoxpaar in der Achsenskala. Im Fenster: E_pa = Strommaximum im\n"
                       "Hinlauf, E_pc = Minimum im Rücklauf, E½ = Mittelwert, ΔE_p = Differenz.\n"
                       "Rot in den Ergebnissen: Peak am Fensterrand – Fenster anpassen.",
                       "Potential window per redox couple in axis units. Within the window: E_pa = current\n"
                       "maximum in the forward scan, E_pc = minimum in the reverse scan, E½ = mean, ΔE_p = difference.\n"
                       "Red in the results: peak at the window edge – adjust the window."),
    "cv_suggest": ("Vorschlagen", "Suggest"),
    "cv_suggest_tip": ("Redoxpaare automatisch aus der ausgewählten Messung vorschlagen",
                       "Suggest redox couples automatically from the selected measurement"),
    "cv_ref": ("Referenz", "Reference"),
    "cv_ref_none": ("Wie gemessen (Referenzelektrode)", "As measured (reference electrode)"),
    "cv_ref_internal": ("Intern (Fc / Ac₂Fc in einer Messung)", "Internal (Fc / Ac₂Fc in one measurement)"),
    "cv_ref_manual": ("Verschiebung von Hand", "Manual shift"),
    "cv_ref_file": ("Referenzmessung", "Reference run"),
    "cv_ref_file_long": ("Messung mit Referenz", "Measurement with reference"),
    "cv_ref_window": ("Referenzfenster [V]", "Reference window [V]"),
    "cv_ref_window_long": ("Fenster Referenz [V, gemessen]", "Reference window [V, measured]"),
    "cv_ref_compound": ("E° Ref. vs. Fc⁰/⁺", "E° ref. vs. Fc⁰/⁺"),
    "cv_ref_compound_long": ("Referenz E° vs. Fc⁰/⁺", "Reference E° vs. Fc⁰/⁺"),
    "cv_ref_custom": ("Eigene", "Custom"),
    "cv_ref_value_tip": ("E½ der Referenzverbindung gegen Fc⁰/⁺. Ac₂Fc (1,1'-Diacetylferrocen): Vorgabe +0,49 V;\n"
                         "lösungsmittelabhängig – mit der verwendeten Literatur abgleichen.",
                         "E½ of the reference compound vs. Fc⁰/⁺. Ac₂Fc (1,1'-diacetylferrocene): default +0.49 V;\n"
                         "solvent dependent – check against the literature you use."),
    "cv_offset": ("E(Fc⁰/⁺) gemessen", "E(Fc⁰/⁺) measured"),
    "cv_offset_tip": ("Lage von Fc⁰/⁺ gegen die Referenzelektrode; wird von allen Potentialen abgezogen.",
                      "Position of Fc⁰/⁺ vs. the reference electrode; subtracted from all potentials."),
    "cv_electrode": ("Referenzelektrode", "Reference electrode"),
    "cv_display": ("Darstellung", "Display"),
    "cv_gradient": ("Farbverlauf nach Scanrate", "Gradient by scan rate"),
    "cv_gradient_long": ("Farbverlauf nach Scanrate (blau → rot)", "Colour gradient by scan rate (blue → red)"),
    "cv_density": ("Stromdichte j", "Current density j"),
    "cv_density_long": ("Stromdichte j [mA cm⁻²]", "Current density j [mA cm⁻²]"),
    "cv_show_e12": ("E½ im Bild", "E½ in the figure"),
    "cv_arrow": ("Scanrichtung", "Scan direction"),
    "cv_arrow_long": ("Pfeil für die Scanrichtung", "Arrow for the scan direction"),
    "cv_invert": ("US-Konvention", "US convention"),
    "cv_invert_long": ("Strom invertieren (US-Konvention)", "Invert current (US convention)"),
    "cv_invert_tip": ("Standard: wie aufgezeichnet (Gamry: IUPAC, anodisch positiv).",
                      "Default: as recorded (Gamry: IUPAC, anodic positive)."),
    "cv_results": ("Ergebnisse", "Results"),
    "cv_ratio_tip": ("Rückpeak/Hinpeak nach Nicholson (Anal. Chem. 1966): berücksichtigt den abklingenden Strom\n"
                     "des Hinlaufs. ≈ 1: chemisch reversibel. i_pa/i_pc mit Basislinie (falls eingeschaltet).",
                     "Reverse/forward peak ratio after Nicholson (Anal. Chem. 1966): accounts for the decaying\n"
                     "forward current. ≈ 1: chemically reversible. i_pa/i_pc with baseline (if enabled)."),
    "cv_ref_note": ("Referenz: {name} bei E½ = {e12} V vs. {el} (ΔE_p = {dep} mV) ≙ {val} V vs. Fc⁰/⁺",
                    "Reference: {name} at E½ = {e12} V vs. {el} (ΔE_p = {dep} mV) ≙ {val} V vs. Fc⁰/⁺"),
    "cv_ref_own": ("eigene Referenz dieser Messung: E(Fc⁰/⁺) gemessen = {off} V (nicht die für alle)",
                   "own reference of this measurement: E(Fc⁰/⁺) measured = {off} V (not the one for all)"),
    "cv_ref_missing": ("⚠ Referenz nicht gefunden (Messung oder Fenster prüfen) – Achse wie gemessen.",
                       "⚠ Reference not found (check measurement or window) – axis as measured."),
    "cv_edge": ("⚠ Peak am Fensterrand", "⚠ peak at the window edge"),
    "cv_area_from_file": ("Stromdichte mit der Fläche aus der Messdatei ({A} cm²) – dort steht oft der Vorgabewert. "
                          "Eigene Fläche: Auswertung → Diffusion und k⁰ → Fläche A.",
                          "Current density with the area from the measurement file ({A} cm²) – often the default value. "
                          "Own area: Evaluation → Diffusion and k⁰ → Area A."),
    "cv_area_missing": ("⚠ Keine Elektrodenfläche in {files} – Strom statt Stromdichte.",
                        "⚠ No electrode area in {files} – current instead of current density."),
    "cv_cycle_missing": ("⚠ {files}: Zyklus {n} fehlt – letzter Zyklus ausgewertet.",
                         "⚠ {files}: cycle {n} missing – last cycle evaluated."),
    "cv_rs_n": ("Elektronen n", "Electrons n"),
    "cv_rs_area": ("Fläche A", "Area A"),
    "cv_rs_area_tip": ("Geometrische Fläche der Arbeitselektrode, gilt für den Diffusionskoeffizienten und die Stromdichte.\n"
                       "Für D wird sie nie aus der Messdatei übernommen (dort steht oft der Vorgabewert der Messsoftware);\n"
                       "die Stromdichte nimmt ohne Eintrag die Fläche der Datei und sagt das unter der Vorschau.",
                       "Geometric area of the working electrode, used for the diffusion coefficient and the current density.\n"
                       "For D it is never taken from the measurement file (it often holds the software default); without an\n"
                       "entry the current density uses the file's area and says so below the preview."),
    "cv_rs_conc": ("Konzentration c", "Concentration c"),
    "cv_rs_temp": ("Temperatur", "Temperature"),
    "cv_rs_hint": ("D aus der Randles–Ševčík-Steigung des Hinpeaks (reversibles, frei diffundierendes Paar, ab drei Scanraten). "
                   "Erst mit Fläche und Konzentration. k⁰ aus ΔE_p mit diesem oder dem eingegebenen D; die Ergebnisse stehen im Reiter Ergebnisse.",
                   "D from the Randles–Ševčík slope of the forward peak (reversible, freely diffusing couple, from three scan rates). "
                   "Only with area and concentration. k⁰ from ΔE_p with this or the entered D; the results are shown in the Results tab."),
    # CV: Angaben, die ACS/Angew. zum Voltammogramm und in der SI verlangen (Karte „Messbedingungen“)
    "cv_acs_group": ("Messbedingungen", "Measurement Conditions"),
    "cv_acs_in_project": ("Der Messaufbau steht einmal im Projekt (Projektseite → Angaben) und in der Gesamt-SI am Anfang "
                          "des Kapitels:", "The setup is recorded once in the project (project page → Details) and "
                          "opens the chapter of the combined SI:"),
    "cv_acs_in_project_none": ("Der Messaufbau steht einmal im Projekt (Projektseite → Angaben), dort ist noch nichts "
                               "eingetragen.", "The setup is recorded once in the project (project page → Details); "
                               "nothing entered there yet."),
    "cv_acs_ir_differs": ("Das Projekt nennt eine iR-Kompensation, diese Messung wurde ohne aufgezeichnet.",
                          "The project states an iR compensation, this measurement was recorded without."),
    "pub_cv_grp": ("Cyclovoltammetrie: Messaufbau", "Cyclic Voltammetry: Setup"),
    "pub_cv_hint": ("Einmal für das Projekt. Daraus entsteht ein Fließtext als erster Absatz des Kapitels „Cyclic "
                    "Voltammetry“ der Gesamt-SI (englisch eintragen); ein leeres Feld lässt seinen Satzteil weg.",
                    "Once for the project. The fields form a running text that opens the chapter “Cyclic Voltammetry” "
                    "of the combined SI; an empty field drops its part of the sentence."),
    "pub_cv_device": ("Gerät", "Instrument"),
    "pub_cv_we": ("Arbeitselektrode", "Working electrode"),
    "pub_cv_area": ("Fläche", "Area"),
    "pub_cv_more": ("Weitere Angaben", "Further details"),
    "pub_cv_ph_more": ("Ganze Sätze, z. B. Präparation der Referenzelektrode, Vorbehandlung des Leitsalzes (englisch)",
                       "Full sentences, e.g. preparation of the reference electrode, pretreatment of the electrolyte"),
    "pub_cv_polish": ("Politur", "Polishing"),
    "pub_cv_ce": ("Gegenelektrode", "Counter electrode"),
    "pub_cv_ref": ("Referenzelektrode", "Reference electrode"),
    "pub_cv_gas": ("Atmosphäre", "Atmosphere"),
    "pub_cv_ir": ("iR-Kompensation", "iR compensation"),
    "pub_cv_conv": ("Konvention", "Convention"),
    "pub_cv_conv_none": ("Nicht angegeben (steht dann in jeder Bildunterschrift)", "Not stated (then given in every caption)"),
    "pub_cv_conv_iupac": ("IUPAC (anodische Ströme positiv)", "IUPAC (anodic currents positive)"),
    "pub_cv_conv_polar": ("Polarographisch (kathodische Ströme positiv)", "Polarographic (cathodic currents positive)"),
    "cv_cap_start": ("Start und Richtung", "Start and direction"),
    "cv_cap_start_long": ("Startpotential und Richtung des Scans in die Bildunterschrift schreiben (aus der Messdatei). "
                          "Vorgabe aus: der Pfeil in der Abbildung zeigt die Richtung.",
                          "Write starting potential and direction of the scan into the caption (from the measurement "
                          "file). Off by default: the arrow in the figure shows the direction."),
    "pub_cv_ph_device": ("Hersteller, Modell", "Manufacturer, model"),
    "pub_cv_ph_we": ("Z. B. glassy carbon, 3 mm diameter", "E.g. glassy carbon, 3 mm diameter"),
    "pub_cv_ph_area": ("Z. B. 0.0707 (cm2) oder 7.07 mm2", "E.g. 0.0707 (cm2) or 7.07 mm2"),
    "pub_cv_ph_polish": ("Z. B. 0.05 µm Al2O3", "E.g. 0.05 µm Al2O3"),
    "pub_cv_ph_ce": ("Z. B. Pt wire", "E.g. Pt wire"),
    "pub_cv_ph_ref": ("Z. B. Ag/AgNO3 (0.01 M in MeCN)", "E.g. Ag/AgNO3 (0.01 M in MeCN)"),
    "pub_cv_ph_gas": ("Z. B. argon, glovebox", "E.g. argon, glovebox"),
    "pub_cv_ph_ir": ("Z. B. positive feedback, 85%", "E.g. positive feedback, 85%"),
    "cv_acs_we": ("Arbeitselektrode", "Working electrode"),
    "cv_acs_we_ph": ("Z. B. Glaskohlenstoff, Ø 3 mm", "E.g. glassy carbon, 3 mm diameter"),
    "cv_acs_ce": ("Gegenelektrode", "Counter electrode"),
    "cv_acs_ce_ph": ("Z. B. Pt-Draht", "E.g. Pt wire"),
    "cv_acs_gas": ("Spülgas", "Purge gas"),
    "cv_acs_gas_ph": ("Z. B. Argon", "E.g. argon"),
    "cv_acs_device": ("Gerät", "Instrument"),
    "cv_acs_device_ph": ("Hersteller, Modell", "Manufacturer, model"),
    "cv_acs_polish": ("Politur", "Polishing"),
    "cv_acs_polish_ph": ("Z. B. 0.05 µm Al2O3", "E.g. 0.05 µm Al2O3"),
    "cv_acs_from_file": ("Aus den Messdateien: {items}.", "From the measurement files: {items}."),
    "cv_acs_start": ("Start bei {E} V vs. {ref}", "start at {E} V vs. {ref}"),
    "cv_acs_dir_pos": ("Scan in positiver Richtung", "scan in the positive direction"),
    "cv_acs_dir_neg": ("Scan in negativer Richtung", "scan in the negative direction"),
    "cv_acs_ir_on": ("mit iR-Kompensation", "with iR compensation"),
    "cv_acs_ir_off": ("ohne iR-Kompensation", "without iR compensation"),
    "cv_acs_ir_mixed": ("iR-Kompensation nicht in allen Messungen gleich", "iR compensation differs between measurements"),
    "cv_acs_missing": ("Für die Richtlinien (ACS, Angew.) fehlt noch: {items}.",
                       "Still missing for the guidelines (ACS, Angew.): {items}."),
    "cv_acs_n_solvent": ("Lösungsmittel", "solvent"),
    "cv_acs_n_el": ("Leitsalz mit Konzentration", "electrolyte with concentration"),
    "cv_acs_n_conc": ("Konzentration des Analyten", "analyte concentration"),
    "cv_acs_n_we": ("Arbeitselektrode", "working electrode"),
    "cv_acs_n_ce": ("Gegenelektrode", "counter electrode"),
    "cv_acs_n_gas": ("Spülgas", "purge gas"),
    "cv_acs_n_device": ("Gerät", "instrument"),
    "cv_acs_n_area": ("Fläche der Arbeitselektrode (Diffusion und k⁰)", "working electrode area (Diffusion and k⁰)"),
    "cv_acs_n_polish": ("Politur", "polishing"),
    "cv_fit_title": ("Scanraten-Analyse: i_p gegen √v (Steigung, Achsenabschnitt, R²) und Steigung von log i_p gegen log v; "
                     "± = 95-%-Intervall",
                     "Scan-rate analysis: i_p vs. √v (slope, intercept, R²) and slope of log i_p vs. log v; "
                     "± = 95% interval"),
    "cv_fit_couple": ("Paar", "Couple"),
    "cv_fit_peak": ("Peak", "Peak"),
    "cv_fit_n": ("Anzahl der Messungen in der Regression", "Number of measurements in the regression"),
    "cv_dk_title": ("Diffusionskoeffizient und k⁰ je Paar", "Diffusion coefficient and k⁰ per couple"),
    "cv_dk_status": ("Bewertung", "Assessment"),
    "cv_dk_D_ok": ("D: Ergebnis", "D: result"),
    "cv_dk_D_app": ("D: scheinbar", "D: apparent"),
    "cv_dk_k0_ok": ("k⁰: Ergebnis", "k⁰: result"),
    "cv_dk_k0_app": ("k⁰: scheinbar", "k⁰: apparent"),
    "cv_dk_skip_rev": ("{n}× kein k⁰ (zu reversibel)", "{n}× no k⁰ (too reversible)"),
    "cv_dk_skip_alpha": ("{n}× kein k⁰ (α fehlt)", "{n}× no k⁰ (α missing)"),
    "cv_dk_falls": ("k⁰ fällt mit v", "k⁰ falls with v"),
    "cv_w_bl_fail": ("Zeilen ohne Basislinie: {n}", "Rows without baseline: {n}"),
    "cv_w_bl_short": ("Zeilen mit kurzer Basislinie (i_p etwas zu klein): {n}",
                      "Rows with short baseline (i_p slightly too small): {n}"),
    "cv_w_two_waves": ("Zeilen mit zwei Wellen im Fenster (nicht ausgewertet): {n}",
                       "Rows with two waves in the window (not evaluated): {n}"),
    "cv_w_D": ("Paare mit nur scheinbarem D: {n}", "Couples with only apparent D: {n}"),
    "cv_w_k0": ("Paare mit nur scheinbarem k⁰: {n}", "Couples with only apparent k⁰: {n}"),
    "cv_w_k0_falls": ("Paare, bei denen k⁰ mit der Scanrate fällt (iR-Abfall?): {n}",
                      "Couples where k⁰ falls with scan rate (iR drop?): {n}"),
    "cv_fit_slope": ("Steigung [µA (V s⁻¹)^-½]", "Slope [µA (V s⁻¹)^-½]"),
    "cv_fit_icpt": ("Abschnitt [µA]", "Intercept [µA]"),
    "cv_fit_icpt_tip": ("y-Achsenabschnitt der Regression (Strom bei v = 0)", "y intercept of the regression (current at v = 0)"),
    "cv_fit_ll": ("Log-log-Steigung", "Log–log slope"),
    "cv_fit_D_tip": ("Diffusionskoeffizient aus der Randles–Ševčík-Steigung des Hinpeaks; in Klammern die 95-%-Grenzen "
                     "(nur aus der Unsicherheit der Steigung).",
                     "Diffusion coefficient from the Randles–Ševčík slope of the forward peak; 95% limits in brackets "
                     "(from the uncertainty of the slope only)."),
    "cv_fit_k0_tip": ("Heterogene Geschwindigkeitskonstante k⁰ aus ΔE_p, Bereich über die Scanraten (nie ±): "
                      "Nicholson-ψ nach Lavagnini (n·ΔE_p 66–160 mV), darüber Klingler–Kochi (nur mit α).",
                      "Heterogeneous rate constant k⁰ from ΔE_p, range over the scan rates (never ±): Nicholson ψ "
                      "after Lavagnini (n·ΔE_p 66–160 mV), above that Klingler–Kochi (only with α)."),
    "cv_two_waves": ("⚠ zwei Wellen im Fenster", "⚠ two waves in the window"),
    "cv_two_waves_warn": ("⚠ Zeilen mit zwei Wellen im Fenster: {n}. E_pa und E_pc kämen von verschiedenen Paaren – "
                          "nicht ausgewertet. Fenster je Paar enger setzen oder „Vorschlagen“.",
                          "⚠ Rows with two waves in the window: {n}. E_pa and E_pc would come from different couples "
                          "– not evaluated. Narrow the window of each couple or use “Suggest”."),
    "cv_D_apparent_warn": ("⚠ Paar {couple}: D nur scheinbar – bei {rates} mV s⁻¹ nicht reversibel (ΔE_p mehr als 10 mV "
                           "über dem der Referenz derselben Messung oder einer eigenen Messung mit gleicher Scanrate bzw. "
                           "über 2,22·RT/(nF)); langsamer Elektronentransfer oder iR-Abfall machen D zu klein.",
                           "⚠ Couple {couple}: D is only apparent – not reversible at {rates} mV s⁻¹ (ΔE_p more than "
                           "10 mV above that of the reference in the same measurement or in a separate measurement at the "
                           "same scan rate, or above 2.22·RT/(nF)); slow electron transfer or iR drop make D too small."),
    "cv_dk_ref_rate": ("Referenz in eigener Messung, andere Scanrate: bei {rates} mV s⁻¹ gilt 2,22·RT/(nF) + 10 mV.",
                       "Reference in a separate run at another scan rate: at {rates} mV s⁻¹ the limit 2.22·RT/(nF) + "
                       "10 mV applies."),
    "cv_ref_col": ("Ref.", "Ref."),
    "cv_ref_col_tip": ("Messung, die den internen Standard enthält (Fc oder Ac₂Fc, Karte Referenz): eine je Reihe\n"
                       "(Gruppe). Danach „Referenz setzen“ und die beiden Peaks des Standards in der Vorschau anklicken.",
                       "Run that contains the internal standard (Fc or Ac₂Fc, card Reference): one per series (group).\n"
                       "Then “Set reference” and click the two peaks of the standard in the preview."),
    "cv_ref_pick": ("Referenz setzen", "Set Reference"),
    "cv_ref_pick_tip": ("Oxidations- und Reduktionspeak des Standards in der Referenzmessung anklicken: jeder Klick springt\n"
                        "auf den Peak in der Nähe (±80 mV), E½ = Mittelwert. Esc bricht ab.",
                        "Click the oxidation and the reduction peak of the standard in the reference run: each click\n"
                        "snaps to the nearby peak (±80 mV), E½ = their mean. Esc cancels."),
    "cv_ref_pick_none": ("Erst in der Liste die Messung mit dem Standard anhaken (Spalte Fc).",
                         "First tick the run containing the standard in the list (column Fc)."),
    "cv_ref_pick_hidden": ("Die Referenzmessung ist ausgeblendet: in der Liste einblenden, dann „Referenz setzen“.",
                           "The reference run is hidden: show it in the list, then “Set reference”."),
    "cv_ref_pick_plot": ("Referenz setzen geht nur in der Ansicht Cyclovoltammogramm.",
                         "Setting the reference works only in the cyclic voltammogram view."),
    "cv_ref_pick_hint": ("Referenz setzen: in „{name}“ nahe den Oxidations- und den Reduktionspeak des Standards klicken "
                         "(Esc bricht ab).",
                         "Set reference: click near the oxidation and the reduction peak of the standard in “{name}” "
                         "(Esc cancels)."),
    "cv_ref_pick_a": ("Oxidationspeak", "Oxidation peak"),
    "cv_ref_pick_c": ("Reduktionspeak", "Reduction peak"),
    "cv_ref_pick_next": ("{which} bei {e} V (gemessen) – jetzt den anderen Peak anklicken.",
                         "{which} at {e} V (measured) – now click the other peak."),
    "cv_ref_pick_nopeak": ("Dort ist kein Peak: näher an die Spitze klicken.", "No peak there: click closer to its tip."),
    "cv_ref_pick_fail": ("Kein Fenster findet genau diese beiden Peaks (andere Welle zu nah?) – Fenster von Hand eingeben.",
                         "No window finds exactly these two peaks (another wave too close?) – enter the window by hand."),
    "cv_ref_pick_done": ("Referenz gesetzt: E½ = {e12} V (gemessen), ΔE_p = {dep} mV.",
                         "Reference set: E½ = {e12} V (measured), ΔE_p = {dep} mV."),
    "cv_ref_rate_out": ("Messungen mit internem Standard zählen nur als Referenz: {rates} mV s⁻¹ fehlt deshalb in der "
                        "Scanraten-Analyse.",
                        "Runs with the internal standard count as reference only: {rates} mV s⁻¹ is therefore missing "
                        "from the scan-rate analysis."),
    "cv_ref_marker": ("Struktur des Standards", "Standard structure"),
    "cv_ref_marker_long": ("Struktur des internen Standards (Fc bzw. Ac₂Fc) an seiner Welle, im Maßstab der Struktur der "
                           "Verbindung.",
                           "Structure of the internal standard (Fc or Ac₂Fc) at its wave, at the scale of the compound's "
                           "structure."),
    "cv_ref_color": ("Standard in Kurvenfarbe", "Standard in curve colour"),
    "cv_ref_color_tip": ("Struktur des Standards in der Farbe der Referenzmessung; aus = schwarz (auf dunkler "
                         "Zeichenfläche weiß, in Grafik und SI immer schwarz).",
                         "Standard structure in the colour of the reference measurement; off = black (white on a dark "
                         "canvas, always black in figures and the SI)."),
    "cv_k0_skip_rev": ("Paar {couple}: kein k⁰ bei {rates} mV s⁻¹ – zu nah am reversiblen Grenzwert (n·ΔE_p < 66 mV).",
                       "Couple {couple}: no k⁰ at {rates} mV s⁻¹ – too close to reversible to determine (n·ΔE_p < 66 mV)."),
    "cv_k0_skip_alpha": ("Paar {couple}: kein k⁰ bei {rates} mV s⁻¹ – n·ΔE_p > 160 mV braucht Klingler–Kochi mit α "
                         "(Karte Diffusion und k⁰).",
                         "Couple {couple}: no k⁰ at {rates} mV s⁻¹ – n·ΔE_p > 160 mV needs Klingler–Kochi with α "
                         "(card Diffusion and k⁰)."),
    "cv_k0_apparent_warn": ("⚠ Paar {couple}: k⁰ nur scheinbar – {why}.", "⚠ Couple {couple}: k⁰ is only apparent – {why}."),
    "cv_k0_why_ir": ("ohne iR-Kompensation aufgenommen", "recorded without iR compensation"),
    "cv_k0_why_ref": ("ΔE_p der Referenz zeigt unkompensierten Widerstand", "ΔE_p of the reference shows uncompensated "
                      "resistance"),
    "cv_k0_why_D": ("D aus einem nicht reversiblen Paar (zu klein; D eingeben)", "D from a couple that is not reversible "
                    "(too small; enter D)"),
    "cv_k0_falls": ("⚠ Paar {couple}: k⁰ fällt mit steigender Scanrate um mehr als {pct} % – Zeichen für iR-Abfall.",
                    "⚠ Couple {couple}: k⁰ falls by more than {pct} % with increasing scan rate – a sign of iR drop."),
    "cv_k0_D": ("D\u200b für k⁰", "D\u200b for k⁰"),
    "cv_k0_D_rs": ("Aus Randles–Ševčík", "From Randles–Ševčík"),
    "cv_k0_D_tip": ("Diffusionskoeffizient für k⁰ (D_O = D_R), z. B. aus einer reversiblen Messung oder Chronoamperometrie.\n"
                    "Leer: D aus der Randles–Ševčík-Steigung des Paars (bei nicht reversiblem Paar zu klein: k⁰ scheinbar).",
                    "Diffusion coefficient for k⁰ (D_O = D_R), e.g. from a reversible measurement or chronoamperometry.\n"
                    "Empty: D from the Randles–Ševčík slope of the couple (too small for a couple that is not "
                    "reversible: k⁰ apparent)."),
    "cv_k0_alpha": ("α (Klingler–Kochi)", "α (Klingler–Kochi)"),
    "cv_k0_alpha_tip": ("Durchtrittsfaktor α für k⁰ nach Klingler–Kochi (n·ΔE_p > 160 mV). Nie vorbelegt: ohne α dort kein k⁰.",
                        "Transfer coefficient α for k⁰ after Klingler–Kochi (n·ΔE_p > 160 mV). Never prefilled: without α "
                        "no k⁰ there."),
    "cv_baseline": ("Basislinie", "Baseline"),
    "cv_baseline_tip": ("i_p gegen eine Gerade durch den Strom vor dem Hinpeak (Ladestrom + Untergrund), extrapoliert\n"
                        "unter den Peak. Rückpeak: dieselbe Gerade, verschoben um den Sprung des Ladestroms am\n"
                        "Umkehrpunkt (2·C·v); den abklingenden Hinlaufstrom korrigiert Nicholson. Peakpotentiale\n"
                        "bleiben unverändert. Aus: Ströme von null gemessen.",
                        "i_p against a straight line through the current before the forward peak (charging current +\n"
                        "background), extrapolated beneath the peak. Reverse peak: the same line, shifted by the step of\n"
                        "the charging current at the switching potential (2·C·v); the decaying forward current is\n"
                        "corrected by Nicholson. Peak potentials are unchanged. Off: currents measured from zero."),
    "cv_bl_gap_tip": ("Die Basislinie endet mindestens so weit vor dem Hinpeak (Standard 0,20 V: dort trägt eine\n"
                      "reversible Welle noch etwa 0,3 % des Peakstroms) und in jedem Fall vor dem Anstieg der Welle (2 % der Peakhöhe; breite Wellen, iR-Abfall).\n"
                      "Braucht im Fenster mindestens 30 mV Vorlauf ohne Peak.",
                      "The baseline ends at least this far before the forward peak (default 0.20 V: a reversible wave\n"
                      "still carries about 0.3% of the peak current there) and in any case before the wave rises (2% of the peak height; broad waves, iR drop).\n"
                      "Needs at least 30 mV of peak-free current in the window."),
    "cv_show_bl": ("Im Bild zeigen", "Show in figure"),
    "cv_bl_short": ("⚠ Messungen, bei denen der Vorlauf im Fenster nur für eine Basislinie bis {gap} V vor dem Peak "
                    "reicht: {n}. i_p dort bis etwa 6 % zu klein. Fenster zur Startseite des Hinpeaks erweitern.",
                    "⚠ Measurements where the range before the wave only allows a baseline up to {gap} V before the "
                    "peak: {n}. i_p is up to about 6 % too small there. Extend the window towards the start of the "
                    "forward peak."),
    "cv_bl_fail": ("⚠ Basislinie nicht möglich (zu wenig Vorlauf im Fenster) – Ströme von null gemessen, nicht in den "
                   "Regressionen. Fenster zur Startseite des Hinpeaks erweitern.",
                   "⚠ baseline not possible (too little current before the peak in the window) – currents from zero, "
                   "excluded from the regressions. Extend the window towards the start of the forward peak."),
    "cv_ratio_invalid": ("Kein Nicholson-Verhältnis: Zwischen Hinpeak und Umkehrpotential liegt ein weiterer Prozess\n"
                         "(z. B. Referenz oder zweite Welle). Dafür eine Messung mit Umkehr kurz hinter diesem Paar nehmen.",
                         "No Nicholson ratio: another process lies between the forward peak and the switching potential\n"
                         "(e.g. reference or a second wave). Use a measurement switching shortly after this couple."),
    "si_copy_methods": ("SI-Text kopieren", "Copy SI text"),
    "si_copy_methods_tip": ("Methodenabsatz zu allen Fits und Auswerteschritten dieses Tabs (englisch, zum Anhängen an\n"
                            "den Aufbau-Absatz des passenden SI-Abschnitts), danach die Ergebnisse. Richtet sich nach\n"
                            "den aktuellen Einstellungen; wird beim Export als …_methods.txt mitgeschrieben.",
                            "Methods paragraph on all fits and evaluation steps of this tab (English, to append to the\n"
                            "setup paragraph of the matching SI section), followed by the results. Follows the current\n"
                            "settings; also written as …_methods.txt on export."),
    "si_methods_copied": ("SI-Text in der Zwischenablage.", "SI text copied to the clipboard."),
    "si_methods_none": ("Nichts gefittet – kein SI-Text.", "Nothing fitted – no SI text."),
    "results_none_plain": ("Noch keine Ergebnisse: in Schritt „Darstellung“ die Ansicht „A bei λ gegen E“ wählen.",
                           "No results yet: choose the view “A at λ vs. E” in step “Display”."),
    "sec_go_display": ("Schritt „Darstellung“ öffnen", "Open step “Display”"),
    "results_none": ("Noch keine Ergebnisse: Auswertung links einschalten (Schritt Auswertung).",
                     "No results yet: switch on the evaluation on the left (step Evaluation)."),
    # ---- Spektroelektrochemie ----------------------------------------------
    "tab_sec": ("SEC", "SEC"),
    "sec_data": ("Daten", "Data"),
    "sec_spectra": ("Spektren (BWSpec)", "Spectra (BWSpec)"),
    "sec_spectra_long": ("Spektren (BWSpec .txt)", "Spectra (BWSpec .txt)"),
    "sec_n_spectra": ("{n} Spektren", "{n} spectra"),
    "sec_potential": ("Potential (Gamry)", "Potential (Gamry)"),
    "sec_potential_long": ("Potential (Gamry .DTA)", "Potential (Gamry .DTA)"),
    "sec_offset": ("Zeitversatz", "Time offset"),
    "sec_offset_tip": ("Wird zur Zeit jedes Spektrums addiert, bevor das Potential aus der Gamry-Messung gelesen wird\n"
                       "(z. B. Wartezeit vor dem Scan oder unterschiedliche PC-Uhren). Bei 2 mV s⁻¹: 10 s ≙ 20 mV.",
                       "Added to each spectrum's time before the potential is read from the Gamry run\n"
                       "(e.g. waiting time before the scan or different PC clocks). At 2 mV s⁻¹: 10 s ≙ 20 mV."),
    "sec_shift": ("E(Fc⁰/⁺) gemessen", "E(Fc⁰/⁺) measured"),
    "sec_shift_tip": ("Lage von Fc⁰/⁺ gegen die Referenzelektrode; wird abgezogen (0 = Achse wie gemessen).",
                      "Position of Fc⁰/⁺ vs. the reference electrode; subtracted (0 = axis as measured)."),
    "sec_from_cv": ("Aus CV-Tab", "From CV tab"),
    "sec_display": ("Darstellung", "Display"),
    "sec_mode": ("Ansicht", "View"),
    "sec_mode_spectra": ("Spektrenserie", "Spectral series"),
    "sec_mode_trace": ("A bei λ gegen E", "A at λ vs. E"),
    "sec_mode_heatmap": ("Heatmap (λ gegen Verlauf)", "Heatmap (λ vs. course)"),
    "sec_hm_value": ("Farbe zeigt", "Colour shows"),
    "sec_hm_abs": ("Werte wie gemessen", "Values as measured"),
    "sec_hm_diff": ("Differenz zum ersten Spektrum (Δ)", "Difference to first spectrum (Δ)"),
    "sec_hm_cmap": ("Farbskala", "Colour map"),
    "sec_hm_cmap_tip": ("Absorbanz: sequentielle Skala. ΔA (Differenzspektren an): divergierende Skala mit 0 in der "
                        "Mitte.", "Absorbance: sequential map. ΔA (difference spectra on): diverging map centred "
                        "at 0."),
    "sec_hm_cmax": ("Farbe bis", "Colour up to"),
    "sec_hm_cmax_tip": ("Oberes Ende der Farbskala; auto = größter Wert. Bei ΔA gilt der Bereich symmetrisch "
                        "−Wert … +Wert.", "Upper end of the colour map; auto = largest value. For ΔA the range "
                        "is symmetric, −value … +value."),
    "sec_hover_heat": ("λ = {lam:.1f} nm    {y}    {q} = {v}", "λ = {lam:.1f} nm    {y}    {q} = {v}"),
    "sec_range": ("Spektren (Nr.)", "Spectra (no.)"),
    "sec_last_all": ("Bis Ende", "To end"),
    "sec_range_info_e": ("{n} Spektren, {a} V → {b} V", "{n} spectra, {a} V → {b} V"),
    "sec_range_info": ("{n} Spektren", "{n} spectra"),
    "sec_highlight": ("Erstes/letztes hervorheben", "Highlight first/last"),
    "sec_highlight_long": ("Erstes und letztes Spektrum hervorheben", "Highlight first and last spectrum"),
    "sec_gradient": ("Farbverlauf nach Potential", "Colour gradient by potential"),
    "sec_diff": ("Differenzspektren (ΔA)", "Difference spectra (ΔA)"),
    "sec_baseline": ("Nullpunkt 780–820 nm", "Zero at 780–820 nm"),
    "sec_baseline_long": ("Nullpunkt: Mittel 780–820 nm abziehen", "Zero: subtract mean of 780–820 nm"),
    "cv_color_gradient_tip": ("Farbverlauf nach Scanrate ist an: Farbe kommt aus dem Verlauf. Für eigene Farben "
                              "„Farbverlauf“ ausschalten.", "Colour gradient by scan rate is on: the colour comes from "
                              "the gradient. Switch off “gradient” to use your own colours."),
    "sec_mid": ("Zwischenspektren", "Intermediate spectra"),
    "sec_mid_ph_e": ("Potential [V], z. B. −0.45", "Potential [V], e.g. −0.45"),
    "sec_mid_ph_n": ("Nr. des Spektrums, z. B. 35", "Spectrum no., e.g. 35"),
    "sec_mid_tip": ("Zusätzlich hervorgehobene Spektren, z. B. für eine Zwischenstufe (Radikalkation): grün, weitere\n"
                    "in Orange, Violett, Türkis. Eingabe als Potential in V in der Skala der Achse (mit Referenz);\n"
                    "genommen wird das gezeigte Spektrum mit dem nächstliegenden Potential (bei Hin- und Rückscan das\n"
                    "erste). Ohne Potentialdatei die Nummer des Spektrums. Mehrere durch Komma trennen; leer = nur\n"
                    "erstes und letztes. Wirkt nur mit „hervorheben“.",
                    "Additionally highlighted spectra, e.g. for an intermediate (radical cation): green, further ones\n"
                    "in orange, purple, teal. Enter the potential in V on the axis scale (with reference); the shown\n"
                    "spectrum with the nearest potential is used (with forward and reverse scan the first one).\n"
                    "Without a potential file, the spectrum number. Separate several by commas; empty = first and\n"
                    "last only. Only with “highlight”."),
    "sec_mid_info": ("Zwischenspektren: {items}", "Intermediate spectra: {items}"),
    "sec_bands": ("λ-Labels [nm]", "λ labels [nm]"),
    "sec_bands_ph": ("Z. B. 373, 432", "E.g. 373, 432"),
    "sec_trace": ("λ für A gegen E [nm]", "λ for A vs. E [nm]"),
    "sec_trace_ph": ("Leer = größte Änderung", "Empty = largest change"),
    "sec_fit": ("Scheinbares E½", "Apparent E½"),
    "sec_fit_long": ("Scheinbares E½ (Nernst-Fit)", "Apparent E½ (Nernst fit)"),
    "sec_fit_tip": ("A = A_red + (A_ox − A_red)/(1 + exp(−nF(E − E½)/RT)). Bei kontinuierlichem Scan hinkt die\n"
                    "Elektrolyse in der Dünnschichtzelle nach: E½ verschoben, n < 1 – nur mit Potentialstufen im\n"
                    "Gleichgewicht ist das ein echter Nernst-Wert. CV-Werte haben Vorrang.",
                    "A = A_red + (A_ox − A_red)/(1 + exp(−nF(E − E½)/RT)). In a continuous scan the electrolysis in\n"
                    "the thin-layer cell lags behind: E½ shifted, n < 1 – only potential steps at equilibrium give a true\n"
                    "Nernst value. CV values take precedence."),
    "sec_fit_info": ("{lam} nm: scheinbares E½ = {e12} V, n = {n}, R² = {r2}",
                     "{lam} nm: apparent E½ = {e12} V, n = {n}, R² = {r2}"),
    "sec_outside": ("⚠ {n} Spektren außerhalb der Potentialmessung – Start- bzw. Endpotential angenommen "
                    "(Datum/Uhrzeit oder Zeitversatz prüfen).",
                    "⚠ {n} spectra outside the potential record – start or end potential assumed "
                    "(check date/time or time offset)."),
    "sec_fit_bound": ("⚠ {lam} nm: Fit am Rand des Suchbereichs (E½ außerhalb der Messpunkte oder n außerhalb "
                      "0,3–3) – nicht bestimmbar, nicht angegeben.",
                      "⚠ {lam} nm: fit at the edge of the search range (E½ outside the data or n outside 0.3–3) – "
                      "not determinable, not reported."),
    "sec_no_time": ("⚠ Keine Zeitangaben – Potentiale nicht zuordenbar.", "⚠ No time stamps – potentials cannot be assigned."),
    "sec_index": ("Spektrum Nr.", "Spectrum no."),
    # ---- H-Zelle (Laden/Entladen) ---------------------------------------------
    "tab_hcell": ("H-Cell", "H-Cell"),
    "dp_grp_hcell": ("H-Cell", "H-Cell"),
    "guide_hcell_title": ("H-Cell: Kapazität und Coulomb-Effizienz beim Laden und Entladen",
                          "H-Cell: capacity and Coulombic efficiency during charge–discharge cycling"),
    "guide_hcell_files": ("Dateien: Gamry-.DTA „Cyclic Charge Discharge“ (Hauptdatei) mit dem Ordner CHARGE_DISCHARGE "
                          "daneben (CHARGE_#n/DISCHARGE_#n.DTA)",
                          "Files: Gamry .DTA “Cyclic Charge Discharge” (main file) with the folder CHARGE_DISCHARGE "
                          "next to it (CHARGE_#n/DISCHARGE_#n.DTA)"),
    "guide_hcell_steps": ("Hauptdatei hinzufügen – die Schrittdateien kommen mit\nAnsicht: Kapazität gegen Zyklus oder "
                          "Potential gegen Zeit\nTheoretische Kapazität prüfen (aus der Datei oder eigener Wert)\n"
                          "Felder der Bildunterschrift ausfüllen, exportieren (Strg+E oder Tab „Export“)",
                          "Add the main file – the step files come along\nView: capacity vs. cycle or potential vs. "
                          "time\nCheck the theoretical capacity (from the file or your own value)\nFill in the caption "
                          "fields, export (Ctrl+E or the Export tab)"),
    "hcell_cap_tip": ("Unterschrift wie in der SI der Gruppe. Kapazität: Konzentration und Elektrolyt aus den Feldern; "
                      "Potential: Abbruchpotentiale und Strom aus der Datei.",
                      "Caption as in the group's SI. Capacity: concentration and electrolyte from the fields; "
                      "potential: cut-off potentials and current from the file."),
    "hcell_cap_solvent": ("Elektrolyt", "Electrolyte"),
    "hcell_cap_solvent_ph": ("Z. B. MeCN, 0.1 M n-Bu4NClO4", "E.g. MeCN, 0.1 M n-Bu4NClO4"),
    "hcell_cap_conc_ph": ("Z. B. 10 mM", "E.g. 10 mM"),
    "hcell_xrange": ("Zyklen (Achse)", "Cycles (axis)"),
    "hcell_data": ("Messungen", "Measurements"),
    "hcell_add": ("Messung …", "Measurement …"),
    "hcell_n_cycles": ("Zyklen", "Cycles"),
    "hcell_eval": ("Auswertung", "Evaluation"),
    "hcell_view_capacity": ("Kapazität gegen Zyklus", "Capacity vs. cycle"),
    "hcell_view_potential": ("Potential gegen Zeit", "Potential vs. time"),
    "hcell_from_file": ("Aus Datei", "From file"),
    "hcell_qtheo": ("Q_theo", "Q_theo"),
    "hcell_qtheo_long": ("Theoretische Kapazität Q_theo", "Theoretical capacity Q_theo"),
    "hcell_qtheo_tip": ("Theoretische Kapazität der gewählten Messung (100 %). „Aus Datei“ = Wert, der im Gerät\n"
                        "eingestellt war (CAPACITY). Gilt nur für die gewählte Messung.",
                        "Theoretical capacity of the selected measurement (100 %). “From file” = value set in the\n"
                        "instrument (CAPACITY). Applies only to the selected measurement."),
    "hcell_unit": ("Kapazität", "Capacity"),
    "hcell_cycles": ("Zyklen", "Cycles"),
    "hcell_cycles_ph": ("Leer = automatisch (1, 2 … letzter)", "Empty = automatic (1, 2 … last)"),
    "hcell_cycles_tip": ("Gezeigte Zyklen, z. B. 1, 2, 50, 100 oder 1-3. Leer: erster, zweiter und gleichmäßig\n"
                         "verteilt bis zum letzten (höchstens fünf).",
                         "Cycles shown, e.g. 1, 2, 50, 100 or 1-3. Empty: first, second and evenly spaced up to\n"
                         "the last (at most five)."),
    "hcell_ref": ("Referenz", "Reference"),
    "hcell_ref_ph": ("Leer = E [V], z. B. Ag0/+", "Empty = E [V], e.g. Ag0/+"),
    "hcell_ref_tip": ("Referenz der Potentialachse wie im CV-Tab („Ag0/+“ wird zu Ag⁰/⁺). Leer: E [V].",
                      "Reference of the potential axis as in the CV tab (“Ag0/+” becomes Ag⁰/⁺). Empty: E [V]."),
    "hcell_show_ce": ("Coulomb-Effizienz", "Coulombic efficiency"),
    "hcell_results": ("Ergebnisse je Zyklus", "Results per Cycle"),
    "hcell_results_none": ("Noch keine Messung.", "No measurement yet."),
    "hcell_meas": ("Messung", "Measurement"),
    "hcell_pct_col": ("Kapazität [%]", "Capacity [%]"),
    "hcell_pct_tip": ("Entladekapazität relativ zur theoretischen Kapazität dieser Messung",
                      "Discharge capacity relative to the theoretical capacity of this measurement"),
    "hcell_ce_tip": ("Coulomb-Effizienz = Q_discharge / Q_charge desselben Zyklus",
                     "Coulombic efficiency = Q_discharge / Q_charge of the same cycle"),
    "hcell_gone": ("Datei fehlt: {f}", "File missing: {f}"),
    "hcell_no_qtheo": ("Keine theoretische Kapazität (Datei ohne CAPACITY, kein eigener Wert): Kapazität in mAh.",
                       "No theoretical capacity (file without CAPACITY, no own value): capacity in mAh."),
    "hcell_cycles_bad": ("Zyklen nicht verstanden: {t}", "Cycles not understood: {t}"),
    "hcell_first_only": ("Potential gegen Zeit zeigt nur die gewählte Messung ({name}).",
                         "Potential vs. time shows only the selected measurement ({name})."),
    "hcell_no_cycle": ("Zyklus {n} gibt es in der Messung nicht.", "Cycle {n} is not in the measurement."),
    "hcell_step_missing": ("Zyklus {n}: {kind} fehlt ({f}) – nicht gezeichnet.",
                           "Cycle {n}: {kind} missing ({f}) – not drawn."),
    "hcell_charge": ("Ladekurve", "charge curve"),
    "hcell_discharge": ("Entladekurve", "discharge curve"),
    "hcell_no_curves": ("Keine Schrittdateien für die gewählten Zyklen.", "No step files for the selected cycles."),
    "hcell_src_file": ("aus Datei", "from file"),
    "hcell_src_entered": ("eingegeben", "entered"),
    "hcell_col_first": ("Entladen, erster Zyklus [mAh]", "Discharge, first cycle [mAh]"),
    "hcell_col_last": ("Entladen, letzter Zyklus [mAh]", "Discharge, last cycle [mAh]"),
    "hcell_col_ret": ("Erhalt [%]", "Retention [%]"),
    "hcell_col_ce": ("Mittlere CE [%]", "Mean CE [%]"),
    "hcell_col_n": ("Zyklen", "Cycles"),
    "hcell_col_h": ("Dauer [h]", "Duration [h]"),
    "hcell_kpi_ret": ("Erhalt", "Retention"),
    "hcell_kpi_ce": ("Coulomb-Eff.", "Coulombic eff."),
    "hcell_bad_tag": ("{f}: keine Gamry-Lade/Entlade-Datei (TAG {tag}). Erwartet: Cyclic Charge Discharge (Hauptdatei).",
                      "{f}: not a Gamry charge–discharge file (TAG {tag}). Expected: Cyclic Charge Discharge (main file)."),
    "hcell_no_table": ("{f}: Tabelle {t} fehlt oder unvollständig.", "{f}: table {t} missing or incomplete."),
    "hcell_bad_type": ("{f}: unbekannte Variante der Kapazitätstabelle (Art oder Zyklus).",
                       "{f}: unknown variant of the capacity table (type or cycle)."),
    "hcell_no_offset": ("{f}: STARTTIMEOFFSET fehlt – keine echte Zeitachse.",
                        "{f}: STARTTIMEOFFSET missing – no true time axis."),
    # ---- EPR ---------------------------------------------------------------
    "tab_epr": ("EPR", "EPR"),
    "off": ("Aus", "Off"),
    "epr_entries": ("Spektren", "Spectra"),
    "epr_add_exp": ("Messung …", "Measurement …"),
    "epr_add_sim": ("Simulation laden …", "Load simulation …"),
    "epr_add_sim_tip": ("Fertige Simulation als ASCII-Datei laden (z. B. aus EasySpin)",
                        "Load a finished simulation as an ASCII file (e.g. from EasySpin)"),
    "epr_kind_exp": ("Messung", "Measured"),
    "epr_kind_sim": ("Simulation", "Simulation"),
    "epr_none": ("– Keine –", "– None –"),
    "epr_funit": ("Feldeinheit der Datei", "Field unit of the file"),
    "epr_funit_tip": ("Die Textdatei nennt die Einheit des Magnetfelds nicht. Die Wahl hier gilt für diese Messung;\n"
                      "Fits an dieser Messung werden danach verworfen.",
                      "The text file does not state the unit of the magnetic field. The choice applies to this "
                      "measurement;\nfits to this measurement are discarded afterwards."),
    "epr_funit_assumed": ("Feldeinheit steht nicht in der Datei: als {unit} angenommen (Feldwerte über 1500 gelten "
                          "als G). Bitte unter „Feldeinheit der Datei“ bestätigen oder ändern.",
                          "The file does not state the field unit: {unit} assumed (field values above 1500 count "
                          "as G). Please confirm or change it under “Field unit of the file”."),
    "epr_dark": ("Dunkelspektrum", "Dark spectrum"),
    "epr_dark_tip": ("Messung vor dem Bestrahlen (ohne Triplett) als Hintergrund: hell − k·dunkel, auf das Feldraster\n"
                     "der Messung interpoliert. Gleiche Frequenz, Modulation und Leistung nötig (sonst Warnung).",
                     "Measurement before irradiation (no triplet) as background: light − k·dark, interpolated onto the\n"
                     "field grid of the measurement. Same frequency, modulation and power required (warning otherwise)."),
    "epr_dark_mismatch": ("⚠ {name}: Dunkelspektrum mit anderem {what} gemessen.",
                          "⚠ {name}: dark spectrum recorded with different {what}."),
    "epr_fit_to": ("Anpassen an", "Scale to"),
    "epr_fit_tip": ("Skalierung der Simulation per kleinsten Quadraten an die gewählte Messung (nach deren Verarbeitung);\n"
                    "Simulation liegt dann auf derselben Stapelebene.",
                    "Least-squares scaling of the simulation to the selected measurement (after its processing);\n"
                    "the simulation is then drawn on the same stacking level."),
    "epr_scale": ("Faktor / Versatz", "Factor / shift"),
    "epr_shift": ("ΔB", "ΔB"),
    "epr_scale_tip": ("Faktor der Simulation (gesperrt, solange sie an eine Messung angepasst wird)",
                      "Factor of the simulation (locked while it is scaled to a measurement)"),
    "epr_shift_tip": ("Feldverschiebung nur dieser Simulation (nicht die Feldkalibrierung)",
                      "Field shift of this simulation only (not the field calibration)"),
    "epr_params": ("EasySpin-Parameter", "EasySpin parameters"),
    "epr_processing": ("Verarbeitung", "Processing"),
    "epr_bl_method": ("Basislinie", "Baseline"),
    "epr_bl_method_tip": ("Polynom: durch signalfreie Bereiche oder die Ränder des Sweeps.\n"
                          "Glatt: folgt breitem Untergrund (Resonator) und lässt schmale Linien stehen; kein "
                          "Dunkelspektrum nötig.\n"
                          "Spline: durch die Mittel der signalfreien Bereiche (mindestens zwei).",
                          "Polynomial: through signal-free ranges or the edges of the sweep.\n"
                          "Smooth: follows a broad background (resonator) and keeps narrow lines; no dark spectrum "
                          "needed.\n"
                          "Spline: through the means of the signal-free ranges (at least two)."),
    "epr_bl_poly": ("Polynom", "Polynomial"),
    "epr_bl_smooth": ("Glatt", "Smooth"),
    "epr_bl_spline": ("Spline", "Spline"),
    "epr_bl_order": ("Grad", "Order"),
    "epr_bl_edge": ("Ränder", "Edges"),
    "epr_bl_edge_tip": ("Ohne Bereiche: Anteil des Sweeps links und rechts, durch den das Polynom gelegt wird.",
                        "Without ranges: share of the sweep on the left and right that the polynomial is fitted to."),
    "epr_bl_width": ("Breite", "Width"),
    "epr_bl_width_tip": ("Was schmaler ist, bleibt Signal; was breiter ist, gilt als Untergrund und wird abgezogen.\n"
                         "Größer wählen als die breiteste echte Linie – auch breite Triplett-Anteile verschwinden sonst.",
                         "Narrower features stay as signal; broader ones count as background and are subtracted.\n"
                         "Choose it larger than the broadest real line - broad triplet features vanish otherwise."),
    "epr_bl_spline_need": ("Spline-Basislinie: mindestens zwei signalfreie Bereiche angeben (noch keine Basislinie abgezogen).",
                           "Spline baseline: enter at least two signal-free ranges (no baseline subtracted yet)."),
    "epr_bl_regions": ("Basislinie: Bereiche", "Baseline ranges"),
    "epr_bl_regions_tip": ("Signalfreie Feldbereiche für die Basislinie (Achseneinheit mT), z. B. '400-430, 560-600'.\n"
                           "Polynom, leer: die äußeren Ränder des Sweeps. Spline: je Bereich eine Stützstelle "
                           "(kurze Bereiche wählen).",
                           "Signal-free field ranges for the baseline (axis unit mT), e.g. '400-430, 560-600'.\n"
                           "Polynomial, empty: the outer edges of the sweep. Spline: one anchor per range "
                           "(choose short ranges)."),
    "epr_regions_ph": ("Z. B. 330-340, 480-485 (mT)", "E.g. 330-340, 480-485 (mT)"),
    "epr_exclude": ("Bereiche ausblenden", "Hide ranges"),
    "epr_exclude_tip": ("Feldbereiche, die nicht gezeichnet werden (mT), z. B. das scharfe Radikalsignal bei g ≈ 2.",
                        "Field ranges that are not drawn (mT), e.g. the sharp radical signal at g ≈ 2."),
    "epr_smooth": ("Glätten", "Smoothing"),
    "epr_smooth_tip": ("Gleitender Mittelwert über diese Feldbreite", "Moving average over this field width"),
    "epr_display": ("Darstellung", "Display"),
    "epr_xrange": ("B-Bereich", "B range"),
    "epr_unit": ("Feldeinheit", "Field unit"),
    "epr_normalize": ("Normieren", "Normalize"),
    "epr_normalize_long": ("Normieren (max |I| = 1)", "Normalize (max |I| = 1)"),
    "epr_labels": ("Labels", "Labels"),
    "epr_labels_ph": ("Z. B. Z⁻@122, Y⁺@400, X⁺@450", "E.g. Z⁻@122, Y⁺@400, X⁺@450"),
    "epr_labels_tip": ("Text@Feld (in der Achseneinheit), durch Kommas getrennt – z. B. kanonische Positionen.",
                       "Text@field (in axis units), comma separated – e.g. canonical positions."),
    "epr_show_params": ("D und |E| im Bild", "D and |E| in the figure"),
    "epr_reverse": ("Umkehren", "Reverse"),
    "epr_reverse_tip": ("Reihenfolge der ganzen Liste umkehren (oberster Eintrag = oberste Kurve im Stapel)",
                        "Reverse the order of the whole list (first entry = top trace of the stack)"),
    "epr_name_tip": ("Doppelklick: umbenennen – der Name steht in der Legende bzw. neben der Kurve",
                     "Double-click to rename – the name appears in the legend or next to the trace"),
    "epr_trace_label": ("Beschriftung", "Trace labels"),
    "epr_trace_label_tip": ("Was in der Legende steht – bei einer gestapelten Messreihe rechts neben jeder Kurve statt\n"
                            "einer Legende: der Name aus der Liste oder Zeit/Temperatur aus der Messdatei\n"
                            "(Zeit seit dem frühesten Spektrum im Tab; Temperatur mit T-Korrektur).",
                            "What the legend shows – for a stacked series of measurements to the right of each trace\n"
                            "instead of a legend: the name from the list or time/temperature from the measurement file\n"
                            "(time since the earliest spectrum in the tab; temperature with T correction)."),
    "epr_ramp": ("Farbverlauf", "Colour gradient"),
    "epr_ramp_tip": ("Messungen in der Reihenfolge der Liste einfärben (z. B. Zeit- oder Temperaturserie);\n"
                     "aus = Farben der Liste.",
                     "Colour the measurements in list order (e.g. a time or temperature series);\n"
                     "off = colours of the list."),
    "epr_no_trace_value": ("Zeit bzw. Temperatur steht nicht in den Messdateien – Namen gezeigt.",
                           "Time or temperature is not in the measurement files – names shown."),
    "epr_dark_all": ("Dunkelspektrum für alle Messungen übernehmen", "Use this dark spectrum for all measurements"),
    "epr_dark_all_tip": ("Setzt Dunkelspektrum und Faktor dieses Eintrags bei allen anderen Messungen (z. B. Kinetik-Serie).\n"
                         "Das Dunkelspektrum selbst wird im Bild ausgeblendet; das Häkchen in der Liste zeigt es wieder.",
                         "Sets dark spectrum and factor of this entry for all other measurements (e.g. a kinetic series).\n"
                         "The dark spectrum itself is hidden in the figure; its check box in the list shows it again."),
    "epr_int_window": ("Feldfenster", "Field window"),
    "epr_int_window_ph": ("Z. B. 445-500 (mT), leer = ganzer Sweep", "E.g. 445-500 (mT), empty = whole sweep"),
    "epr_int_window_tip": ("Bereich, über den integriert bzw. Peak-zu-Peak bestimmt wird (mT). Ausgeblendete Bereiche zählen mit;\n"
                           "für Tripletts das Radikalsignal also über das Fenster ausschließen.",
                           "Range used for integration or peak-to-peak (mT). Hidden ranges are included;\n"
                           "for triplets exclude the radical signal via the window."),
    "epr_int_method": ("Größe", "Quantity"),
    "epr_int_double": ("Doppelintegral", "Double integral"),
    "epr_int_pp": ("Peak-zu-Peak", "Peak-to-peak"),
    "epr_x_time": ("Zeit [min]", "Time [min]"),
    "epr_x_T": ("Temperatur [K]", "Temperature [K]"),
    "epr_view_spectra": ("Spektren", "Spectra"),
    "epr_view_time": ("Intensität gegen Zeit", "Intensity against time"),
    "epr_view_T": ("Intensität gegen Temperatur", "Intensity against temperature"),
    "epr_view_arr": ("Arrhenius (ln k gegen 1/T)", "Arrhenius (ln k against 1/T)"),
    "epr_view_index": ("Intensität gegen Nr.", "Intensity against no."),
    "epr_view_conc": ("Spinzählung (gegen Konzentration)", "Spin counting (against concentration)"),
    "epr_conc": ("c (bekannt)", "c (known)"),
    "epr_conc_long": ("Bekannte Konzentration (Referenz der Spinzählung)", "Known concentration (reference for spin counting)"),
    "epr_conc_ph": ("Leer = Probe", "Empty = sample"),
    "epr_conc_tip": ("Bekannte Konzentration dieser Messung: sie wird Referenzpunkt der Kalibrierung in der Ansicht "
                     "„Spinzählung“. Leer: die Messung ist eine Probe, ihre Konzentration wird abgelesen.",
                     "Known concentration of this measurement: it becomes a reference point of the calibration in the "
                     "view “Spin counting”. Empty: the measurement is a sample whose concentration is read off."),
    "epr_conc_unit_tip": ("Einheit aller bekannten Konzentrationen dieses Tabs", "Unit of all known concentrations of this tab"),
    "epr_spin_di": ("Doppelintegral", "Double integral"),
    "epr_spin_known": ("c (bekannt)", "c (known)"),
    "epr_spin_found": ("c (Kalibrierung)", "c (calibration)"),
    "epr_spin_refs": ("Referenz", "reference"),
    "epr_spin_samples": ("Probe", "sample"),
    "epr_spin_line": ("Kalibrierung", "calibration"),
    "epr_spin_none": ("Spinzählung: mindestens eine Messung braucht eine bekannte Konzentration (Feld „c bekannt“ in "
                      "„Ausgewähltes Spektrum“).", "Spin counting: at least one measurement needs a known concentration "
                      "(field “Known c” under the selected spectrum)."),
    "epr_spin_need_double": ("Spinzählung braucht das Doppelintegral ohne I·T (Karte „Intensität und Kinetik“).",
                             "Spin counting needs the double integral without I·T (card “Intensity and Kinetics”)."),
    "epr_spin_info": ("Referenzmessungen für die Kalibrierung: {n}, {how}; keine Unsicherheiten.",
                      "Reference measurements for the calibration: {n}, {how}; no uncertainties."),
    "epr_spin_origin": ("Gerade durch den Ursprung", "straight line through the origin"),
    "epr_spin_fit": ("Ausgleichsgerade mit Achsenabschnitt", "least-squares line with intercept"),
    "epr_spin_differ": ("Die Messungen unterscheiden sich in: {what}. Die Intensitäten werden nicht umgerechnet.",
                        "The measurements differ in: {what}. The intensities are not corrected."),
    "epr_view_tip": ("Was die Abbildung zeigt. Intensität: ein Wert je sichtbarer Messung (Feldfenster und Größe darunter).\n"
                     "Gegen Zeit mit „Zerfall fitten“: isotherm, k je Temperatur. Gegen Temperatur mit „Zerfall fitten“:\n"
                     "Rampe (E_a, A). Arrhenius: ln k gegen 1/T aus den isothermen Zerfällen.",
                     "What the figure shows. Intensity: one value per visible measurement (field window and quantity below).\n"
                     "Against time with 'Fit decay': isothermal, k per temperature. Against temperature with 'Fit decay':\n"
                     "ramp (E_a, A). Arrhenius: ln k against 1/T from the isothermal decays."),
    "epr_kin_norm_label": ("Zielfunktion", "Objective"),
    "epr_fit_joint_need": ("Braucht zwei S = ½-Simulationen an derselben Messung.",
                           "Needs two S = ½ simulations assigned to the same measurement."),
    "epr_x_index": ("Nr.", "no."),
    "epr_curie": ("× T (Curie-Korrektur)", "× T (Curie correction)"),
    "epr_curie_tip": ("Intensität mal Temperatur: bei Curie-Verhalten konstant, solange die Spezies erhalten bleibt\n"
                      "(wie I × T in Zerfallsmessungen).",
                      "Intensity times temperature: constant for Curie behaviour as long as the species persists\n"
                      "(like I × T in decay measurements)."),
    "epr_int_none": ("Keine Werte (Zeit- bzw. Temperaturangaben fehlen?).", "No values (time or temperature missing?)."),
    "epr_int_info": ("{n} Spektren · {method} (Spektren nach Dunkelspektrum und Basislinie).",
                     "{n} spectra · {method} (spectra after dark spectrum and baseline)."),
    "epr_calc_box": ("Rechnung (DFT)", "Calculation (DFT)"),
    "epr_calc_file": ("Ausgabe", "Output"),
    "epr_calc_file_ph": ("Gaussian- oder ORCA-Ausgabe", "Gaussian or ORCA output"),
    "epr_calc_file_tip": ("Ausgabe einer offenschaligen Rechnung: Mulliken-Spinpopulationen, isotrope "
                          "Fermi-Kontakt-Kopplungen und Dipolkopplungen (Gaussian 16: Prop=EPR; ORCA 4.0–4.2, 5.0, 6.0, 6.1: "
                          "%eprnmr Nuclei = all H {aiso, adip} end)",
                          "Output of an open-shell calculation: Mulliken spin populations, isotropic Fermi contact "
                          "couplings and dipole couplings (Gaussian 16: Prop=EPR; ORCA 4.0–4.2, 5.0, 6.0, 6.1: "
                          "%eprnmr Nuclei = all H {aiso, adip} end)"),
    "epr_calc_orb": ("Orbitale", "Orbitals"),
    "epr_calc_orb_ph": ("Molden oder Cube (optional)", "Molden or cube (optional)"),
    "epr_calc_orb_tip": ("Molden-Datei (Spindichte und SOMO werden daraus gerechnet) oder Cube-Datei derselben Geometrie",
                         "Molden file (spin density and SOMO are computed from it) or cube file of the same geometry"),
    "epr_calc_remove": ("Rechnung entfernen", "Remove calculation"),
    "epr_calc_info": ("Ladung {charge}, Multiplizität {mult}, {n} Atome",
                      "charge {charge}, multiplicity {mult}, {n} atoms"),
    "epr_calc_missing": ("Datei fehlt: {f}", "File missing: {f}"),
    "epr_calc_not_gaussian": ("Keine Gaussian-Ausgabe. Spindichten und Kopplungen werden bisher nur aus Gaussian 16 "
                              "gelesen.", "Not a Gaussian output. Spin densities and couplings are read from "
                              "Gaussian 16 only so far."),
    "epr_calc_orca_not_supported": ("Weder Gaussian- noch ORCA-Ausgabe. Spindichten und Kopplungen werden aus Gaussian 16 "
                                    "und ORCA (4.0–4.2, 5.0, 6.0, 6.1) gelesen.", "Neither a Gaussian nor an ORCA output. "
                                    "Spin densities and couplings are read from Gaussian 16 and ORCA (4.0–4.2, 5.0, 6.0, 6.1)."),
    "epr_calc_orca_version": ("ORCA {v}: Spinpopulationen und Hyperfeinblock werden nur aus ORCA 4.0–4.2, 5.0, 6.0 und "
                              "6.1 gelesen (Layouts bekannt); andere Versionen nicht ungeprüft.",
                              "ORCA {v}: spin populations and the hyperfine block are read from ORCA 4.0–4.2, 5.0, 6.0 "
                              "and 6.1 only (known layouts); other versions are not read unchecked."),
    "epr_calc_orca_unchecked": ("Layout für ORCA 6.1 nicht an einer echten Ausgabe geprüft; Werte gegen die Ausgabe "
                                "vergleichen.", "Layout for ORCA 6.1 not checked against a real output; compare the "
                                "values with the output."),
    "epr_calc_orca_layout": ("ORCA {v}: unbekanntes Layout des Hyperfeinblocks (Zeile {line}); die Datei wird nicht "
                             "gelesen.", "ORCA {v}: unknown layout of the hyperfine block (line {line}); the file is "
                             "not read."),
    "epr_calc_orca_no_hfc": ("Die ORCA-Ausgabe enthält keinen Hyperfeinblock. Für Kopplungen in der Eingabe z. B. "
                             "„%eprnmr Nuclei = all H {aiso, adip} end“ ergänzen (je Element eine Zeile „Nuclei = all "
                             "N {aiso, adip}“).", "The ORCA output contains no hyperfine block. For couplings add e.g. "
                             "“%eprnmr Nuclei = all H {aiso, adip} end” to the input (one line “Nuclei = all N {aiso, "
                             "adip}” per element)."),
    "epr_calc_orca_no_dipole": ("Dipol-Hauptwerte fehlen bei Kernen mit A(ORB) (ORCA druckt A(SD) dann im Achsensystem "
                                "des Gesamttensors); dafür ohne „aorb“ rechnen.", "Dipole principal values are left out "
                                "for nuclei with A(ORB) (ORCA then prints A(SD) in the axes of the total tensor); compute "
                                "without “aorb” to get them."),
    "epr_calc_no_spin": ("Keine Mulliken-Spinpopulationen in der Ausgabe (geschlossenschalige Rechnung?).",
                         "No Mulliken spin populations in the output (closed-shell calculation?)."),
    "epr_calc_need_file": ("Zuerst die Ausgabe der Rechnung wählen.", "Choose the calculation output first."),
    "epr_calc_orb_mismatch": ("Atome oder Koordinaten der Orbitaldatei passen nicht zur Rechnung (± 0.02 Å).",
                              "Atoms or coordinates of the orbital file do not match the calculation (± 0.02 Å)."),
    "epr_calc_no_orb": ("Ohne Molden- oder Cube-Datei nur das Molekül mit den Werten.",
                        "Without a Molden or cube file only the molecule with the values."),
    "epr_calc_assign": ("Hyperfein-Zuordnung", "Hyperfine Assignment"),
    "epr_calc_sim": ("Simulation", "Simulation"),
    "epr_calc_sim_tip": ("S = ½-Simulation, deren Kopplungen als experimentelle Werte gelten",
                         "S = ½ simulation whose couplings serve as experimental values"),
    "epr_calc_group": ("Gruppe", "Group"),
    "epr_calc_atoms": ("Atome", "Atoms"),
    "epr_calc_mean": ("Berechnet", "Calculated"),
    "epr_calc_exp": ("Experimentell", "Experimental"),
    "epr_calc_no_groups": ("Keine S = ½-Simulation mit Kopplungen", "No S = ½ simulation with couplings"),
    "epr_calc_count": ("{group}: {m} statt {n} Kerne zugeordnet", "{group}: {m} instead of {n} nuclei assigned"),
    "epr_calc_clear": ("Zuordnung der Gruppe löschen", "Clear group assignment"),
    "epr_calc_clear_tip": ("Alle Kerne der gewählten Gruppe wieder lösen", "Release all nuclei of the selected group"),
    "epr_calc_es": ("EasySpin-Skript speichern …", "Save EasySpin script …"),
    "epr_calc_es_tip": ("Startskript für EasySpin (garlic, isotrop): Kerne, Anzahl und gemittelte Kopplungen in MHz der "
                        "zugeordneten Gruppen (ohne Zuordnung: die Kerne im Bild), g aus dem Fit der S = ½-Simulation, "
                        "Frequenz und Feldbereich aus ihrer Messung; was fehlt, steht als Platzhalter im Skript. "
                        "Anisotrope Tensoren werden nicht ausgegeben. Der Export schreibt das Skript mit.",
                        "Start script for EasySpin (garlic, isotropic): nuclei, numbers and averaged couplings in MHz of "
                        "the assigned groups (without assignment: the nuclei in the figure), g from the fit of the S = ½ "
                        "simulation, frequency and field range from its measurement; anything missing is a placeholder "
                        "in the script. Anisotropic tensors are not written. Export includes the script."),
    "epr_calc_es_none": ("Keine Kopplung für das EasySpin-Skript (Gruppe zuordnen oder „Ab Kopplung“ senken).",
                         "No coupling for the EasySpin script (assign a group or lower “From coupling”)."),
    "epr_calc_pick_group": ("Zuerst links unter „Hyperfein-Zuordnung“ eine Gruppe wählen.",
                            "First select a group under “Hyperfine Assignment” on the left."),
    "epr_calc_wrong_el": ("{atom} ist kein {group}-Kern.", "{atom} is not a {group} nucleus."),
    "epr_calc_display": ("Spindichte und Hyperfein", "Spin Density and Hyperfine"),
    "epr_calc_surface": ("Fläche", "Surface"),
    "epr_calc_surface_tip": ("Isofläche auf dem Molekül (Reiter „Spindichte“). Eine Cube-Datei wird gezeigt, wie sie ist; "
                             "die Auswahl sagt, was sie enthält.", "Isosurface on the molecule (“Spin Density” page). A "
                             "cube file is shown as it is; the choice states what it contains."),
    "epr_calc_surf_spin": ("Spindichte", "Spin density"),
    "epr_calc_surf_somo": ("SOMO", "SOMO"),
    "epr_calc_surf_none": ("Keine", "None"),
    "epr_calc_iso": ("Isowert", "Isovalue"),
    "epr_calc_alpha": ("Deckkraft", "Opacity"),
    "epr_calc_colors": ("Farben", "Colours"),
    "epr_calc_spin_plus": ("Positiver Teil der Fläche", "Positive part of the surface"),
    "epr_calc_spin_minus": ("Negativer Teil der Fläche", "Negative part of the surface"),
    "epr_calc_thresh": ("Schwelle", "Threshold"),
    "epr_calc_thresh_tip": ("Im Bild stehen nur Spinpopulationen ab diesem Betrag (in % der Summe aller Atome); die "
                            "Tabelle zeigt alle.", "The figure shows spin populations from this magnitude on (in % of "
                            "the sum over all atoms); the table lists all."),
    "epr_calc_unit": ("Einheit", "Unit"),
    "epr_calc_nuclei": ("Kerne", "Nuclei"),
    "epr_calc_nuclei_ph": ("Automatisch (z. B. H, N)", "Automatic (e.g. H, N)"),
    "epr_calc_nuclei_tip": ("Elemente, deren nicht zugeordnete Kerne im Bild stehen; leer = die Elemente der "
                            "experimentellen Gruppen, ohne Simulation alle außer C und O (¹³C, ¹⁷O sind selten)", "Elements whose "
                            "unassigned nuclei appear in the figure; empty = the elements of the experimental "
                            "groups, without a simulation all except C and O (¹³C, ¹⁷O are rare)"),
    "epr_calc_min": ("Ab Kopplung", "From coupling"),
    "epr_calc_min_tip": ("Nicht zugeordnete Kerne stehen erst ab diesem Betrag der berechneten Kopplung im Bild; "
                         "zugeordnete immer.", "Unassigned nuclei appear in the figure from this magnitude of the "
                         "calculated coupling on; assigned ones always."),
    "epr_calc_signed": ("Vorzeichen", "Signs"),
    "epr_calc_signed_long": ("Berechnete Kopplungen im Bild mit Vorzeichen; sonst Beträge wie die experimentellen "
                             "Werte. Die Tabelle zeigt immer das Vorzeichen.", "Calculated couplings in the figure "
                             "with their signs; otherwise absolute values like the experimental ones. The table "
                             "always shows the sign."),
    "epr_calc_dipole": ("Dipolkopplung", "Dipole coupling"),
    "epr_calc_dipole_long": ("Hauptwerte der anisotropen Dipolkopplung als drei Spalten in der Tabelle; die CSV enthält "
                             "sie immer.", "Principal values of the anisotropic dipole coupling as three columns in "
                             "the table; the CSV always contains them."),
    "epr_calc_tab_spin": ("Spindichte", "Spin Density"),
    "epr_calc_tab_hfc": ("Hyperfein", "Hyperfine"),
    "epr_calc_start": ("Im Schritt Daten unter „Rechnung (DFT)“ eine Gaussian- oder ORCA-Ausgabe wählen.",
                       "Choose a Gaussian or ORCA output under “Calculation (DFT)” in the Data step."),
    "epr_calc_copy_tip": ("Tabelle kopieren", "Copy table"),
    "epr_calc_atom": ("Atom", "Atom"),
    "epr_calc_pop": ("Spinpopulation", "Spin population"),
    "epr_calc_pct": ("Anteil [%]", "Share [%]"),
    "epr_calc_nucleus": ("Kern", "Nucleus"),
    "epr_add_iso": ("S = ½-Simulation", "S = ½ simulation"),
    "epr_add_iso_tip": ("Eigene isotrope S = ½-Simulation anlegen und an eine Messung anpassen (Fit von g, Linienbreite, "
                        "Kopplungen)", "Create an own isotropic S = ½ simulation and fit it to a measurement (g, "
                        "linewidth, couplings)"),
    "epr_kind_iso": ("S = ½ (eigen)", "S = ½ (own)"),
    "epr_iso": ('Isotrope S = ½-Simulation (erste Ordnung)', 'Isotropic S = ½ Simulation (First Order)'),
    "epr_lw": ("ΔB_pp", "ΔB_pp"),
    "epr_lorentz": ("Lorentz-Anteil", "Lorentzian fraction"),
    "epr_fit_lor": ("Mitfitten", "Fit as well"),
    "epr_nuclei": ("Kerne (a/mT)", "Nuclei (a/mT)"),
    "epr_nuclei_ph": ("Z. B. 2 14N 0.65; 4 1H 0.32", "E.g. 2 14N 0.65; 4 1H 0.32"),
    "epr_nuclei_tip": ("Gruppen äquivalenter Kerne: Anzahl, Isotop (1H, 2H, 11B, 13C, 14N, 15N, 19F, 31P, 63Cu, …) oder I=… (auch I=3/2),\n"
                       "Kopplung a in mT; Gruppen mit ';' trennen. Erste Ordnung, isotrop (Lösung, schnelle Rotation).",
                       "Groups of equivalent nuclei: number, isotope (1H, 2H, 11B, 13C, 14N, 15N, 19F, 31P, 63Cu, …) or I=… (also I=3/2),\n"
                       "coupling a in mT; separate groups with ';'. First order, isotropic (solution, fast tumbling)."),
    "epr_fit_btn": ("An Messung fitten (g, a, ΔB_pp)", "Fit to measurement (g, a, ΔB_pp)"),
    "epr_iso_need_exp": ("Erst eine Messung laden oder wählen.", "Load or select a measurement first."),
    "epr_iso_need_mw": ("Für die Simulation wird die Mikrowellenfrequenz der Messung gebraucht (fehlt in der Datei).",
                        "The simulation needs the microwave frequency of the measurement (missing in the file)."),
    "epr_calib": ("Feldkalibrierung", "Field calibration"),
    "epr_calib_tip": ("Gefittete S = ½-Simulation einer Referenz (z. B. TEMPO in MeCN, g = 2.0055) wählen: ΔB = B(g_fit) − B(g_lit)\n"
                      "wird von allen anderen Messungen abgezogen; deren Fits liefern dann kalibrierte g-Faktoren.",
                      "Choose the fitted S = ½ simulation of a reference (e.g. TEMPO in MeCN, g = 2.0055): ΔB = B(g_fit) − B(g_lit)\n"
                      "is subtracted from all other measurements; their fits then give calibrated g-factors."),
    "epr_calib_info": ("Feldkorrektur ΔB = {dB} mT (Referenz g_fit = {g} → g_lit = {glit}).",
                       "Field correction ΔB = {dB} mT (reference g_fit = {g} → g_lit = {glit})."),
    "epr_show_sum": ("Summe der Komponenten", "Sum of components"),
    "epr_show_residual": ("Rest (Messung − Summe)", "Residual (measured − sum)"),
    "epr_sim_below": ("Simulation unter der Messung", "Simulation below the measurement"),
    "epr_sim_below_tip": ("Gestapelt: jede Simulation auf einer eigenen Ebene direkt unter ihrer Messung statt auf ihr.",
                          "Stacked: each simulation on a level of its own directly below its measurement instead of on it."),
    "epr_sim_gap_tip": ("Abstand zwischen Messung und Simulation als Vielfaches des Stapelabstands.",
                        "Distance between measurement and simulation as a multiple of the stack gap."),
    "epr_sum": ("Summe", "sum"),
    "epr_residual": ("Rest", "residual"),
    "epr_negative_weight": ("{name}: eine Komponente hat ein negatives Gewicht – keine Anteile angegeben (Komponenten "
                            "prüfen).", "{name}: a component has a negative weight – no fractions given (check the "
                            "components)."),
    "epr_nuclei_unknown": ("Kern nicht erkannt: {parts} (Schreibweise z. B. „2 14N 0.65“ oder „2 I=1 0.65“).",
                           "Nucleus not recognized: {parts} (write e.g. “2 14N 0.65” or “2 I=1 0.65”)."),
    "epr_fractions": ("{name}: Anteile (Doppelintegral) {parts}", "{name}: fractions (double integral) {parts}"),
    "epr_ref_freq": ("Frequenz angleichen", "Scale to frequency"),
    "epr_ref_freq_tip": ("B·ν_ref/ν: Spektren mit leicht unterschiedlicher Mikrowellenfrequenz vergleichbar machen\n"
                         "(z. B. Temperaturserien; im MATLAB-Skript 9,3 GHz).",
                         "B·ν_ref/ν: makes spectra with slightly different microwave frequency comparable\n"
                         "(e.g. temperature series; 9.3 GHz in the MATLAB script)."),
    "epr_T_offset": ("T-Korrektur", "T correction"),
    "epr_T_offset_tip": ("Wird zur Temperatur aus der Datei addiert (Sensorkalibrierung; im MATLAB-Skript −1,5 K).",
                         "Added to the temperature from the file (sensor calibration; −1.5 K in the MATLAB script)."),
    "epr_int_gauss": ("Gauß-Fit an Merkmal", "Gaussian fit to feature"),
    "epr_int_method_tip": ("Doppelintegral: Spinmenge. Peak-zu-Peak: einfach, linienbreitenabhängig. Gauß-Fit: Gauß + Gerade an ein\n"
                           "Merkmal im Feldfenster, Intensität = |Amplitude| (wie das MATLAB-Skript, z. B. X-Merkmal bei 487 mT).",
                           "Double integral: spin amount. Peak-to-peak: simple, depends on linewidth. Gaussian fit: Gaussian + line\n"
                           "fitted to a feature in the field window, intensity = |amplitude| (like the MATLAB script, e.g. X feature at 487 mT)."),
    "epr_int_center": ("Merkmal bei", "Feature at"),
    "epr_int_center_tip": ("Lage des Merkmals für den Gauß-Fit", "Position of the feature for the Gaussian fit"),
    "epr_kin_fit": ("Zerfall fitten", "Fit decay"),
    "epr_kin_fit_long": ("Zerfall fitten: gegen Temperatur die Rampe (E_a, A), gegen Zeit isotherm (k je Temperatur)",
                         "Fit decay: against temperature the ramp (E_a, A), against time isothermal (k per temperature)"),
    "epr_kin_loss": ("Fit bis Verlust", "Fit up to loss"),
    "epr_kin_loss_tip": ("Isotherme Zerfälle (gegen Zeit, Arrhenius): nur die Punkte vom Anfang einer Serie, bis die\n"
                         "Intensität um diesen Anteil unter den ersten Punkt gefallen ist. 100 % = alle Punkte.",
                         "Isothermal decays (against time, Arrhenius): only the points from the start of a series until\n"
                         "the intensity has dropped by this share below the first point. 100 % = all points."),
    "epr_iso_short": ("kein Fit (mindestens drei Punkte nötig)", "no fit (at least three points needed)"),
    "epr_col_T": ("Temperatur", "Temperature"),
    "epr_col_pts": ("Punkte", "Points"),
    "epr_col_hfc": ("Kopplungen", "Couplings"),
    "epr_arr_result": ("Arrhenius: E_a = {Ea} kJ mol⁻¹ = {kcal} kcal mol⁻¹ (95 %: {ci}), ln A = {lnA}, "
                       "{n} Temperaturen, R² = {r2}",
                       "Arrhenius: E_a = {Ea} kJ mol⁻¹ = {kcal} kcal mol⁻¹ (95 %: {ci}), ln A = {lnA}, "
                       "{n} temperatures, R² = {r2}"),
    "epr_arr_need": ("Arrhenius braucht Zerfälle bei mindestens zwei Temperaturen (je mindestens drei Spektren, k > 0); "
                     "die Temperatur kommt aus der Messdatei.",
                     "Arrhenius needs decays at two or more temperatures (at least three spectra each, k > 0); the "
                     "temperature is read from the measurement file."),
    "epr_fit_joint": ("Gemeinsam fitten", "Fit together"),
    "epr_fit_joint_tip": ("Alle S = ½-Simulationen, die derselben Messung zugeordnet sind, gleichzeitig fitten.\n"
                          "Startwerte sind ihre aktuellen Werte: vorher einzeln grob einstellen oder fitten.",
                          "Fit all S = ½ simulations assigned to the same measurement at once.\n"
                          "Start values are their current values: set or fit them roughly one by one first."),
    "epr_fit_joint_note": ("(gemeinsam, {n} Spezies)", "(joint, {n} species)"),
    "epr_fit_stale": ("⚠ Vor einer Änderung der Feldkalibrierung oder Referenzfrequenz gefittet: g gilt für die alte "
                      "Feldachse und wird nicht berichtet. Bitte neu fitten.",
                      "⚠ Fitted before the field calibration or reference frequency was changed: g belongs to the "
                      "old field axis and is not reported. Please fit again."),
    "epr_kin_tip": ("Gegen Zeit: isotherm, je Temperatur I(t) = I0·exp(−k·t) (die Auswahl rechts gilt dort nicht);\n"
                    "die Ansicht 1/T (Arrhenius) fittet immer, auch wenn hier „Aus“ steht.\n"
                    "Gegen Temperatur (Rampe): I(T) = exp(−A·∫exp(−E_a/RT)/β dT), erste Ordnung; Heizrate β aus mittlerem\n"
                    "T- und Zeitschritt; bei „Wie Skript“ Intensität vorher min-max normiert (wie im MATLAB-Skript).\n"
                    "Die gepunkteten Grenzen setzen beide Intervallenden von E_a und ln A ein (wie im Skript) – wegen der\n"
                    "starken Kopplung liegen sie fast auf der Kurve und sind kein Unsicherheitsband der Kurve.",
                    "Against time: isothermal, per temperature I(t) = I0·exp(−k·t) (the choice on the right does not apply);\n"
                    "the view 1/T (Arrhenius) always fits, even if this says 'Off'.\n"
                    "Against temperature (ramp): I(T) = exp(−A·∫exp(−E_a/RT)/β dT), first order; heating rate β from mean T\n"
                    "and time step; with 'As script' the intensity is min–max normalized first (like the MATLAB script).\n"
                    "The dotted limits insert both interval ends of E_a and ln A (as in the script) – because of the strong\n"
                    "coupling they lie almost on the curve and are not an uncertainty band of the curve."),
    "epr_kin_script": ("Wie Skript (√|r|)", "As script (√|r|)"),
    "epr_kin_lsq": ("Kleinste Quadrate", "Least squares"),
    "epr_kin_norm_tip": ("„Wie Skript“: lsqnonlin auf √|Modell − Messung| (L1-Norm), Intervall formal aus der Jacobi-Matrix –\n"
                         "reproduziert die bisherigen Zahlen, unterschätzt aber die Unsicherheit stark.\n"
                         "„Kleinste Quadrate“: gemessene Intensitäten ohne Min-Max, Startintensität mitgefittet, Integral\n"
                         "über die Messzeit (auch Haltephasen); Kovarianz s²·(JᵀJ)⁻¹ mit t-Quantil – belastbares Intervall.\n"
                         "E_a und ln A sind fast vollständig korreliert (Kompensationseffekt).",
                         "'As script': lsqnonlin on √|model − data| (L1 norm), interval formally from the Jacobian –\n"
                         "reproduces previous numbers but strongly underestimates the uncertainty.\n"
                         "'Least squares': measured intensities without min–max, initial intensity fitted, integral over\n"
                         "the measured time (also holds); covariance s²·(JᵀJ)⁻¹ with t quantile – reliable interval.\n"
                         "E_a and ln A are almost completely correlated (compensation effect)."),
    "epr_kin_data": ("Messung", "data"),
    "epr_kin_fitcurve": ("Fit", "fit"),
    "epr_kin_band": ("95-%-Grenzen", "95 % limits"),
    "epr_kin_result": ("E_a = {Ea} kJ mol⁻¹ = {kcal} kcal mol⁻¹ (95 %: {lo}–{hi}), A = {A} s⁻¹, β = {beta} K min⁻¹, "
                       "Korrelation E_a/ln A = {corr} [{how}]",
                       "E_a = {Ea} kJ mol⁻¹ = {kcal} kcal mol⁻¹ (95 %: {lo}–{hi}), A = {A} s⁻¹, β = {beta} K min⁻¹, "
                       "correlation E_a/ln A = {corr} [{how}]"),
    "epr_gauss_edge": ("⚠ {n} Spektren: Gauß-Zentrum am Rand des Messbereichs – dort kein klares Merkmal (Rauschen).",
                       "⚠ {n} spectra: Gaussian centre at the edge of the measured range – no clear feature there (noise)."),
    # ---- Farbe der Lösung ---------------------------------------------------
    "color_show": ("Farbe in Lösung", "Colour in solution"),
    "color_show_long": ("Farbe in Lösung anzeigen (Vorhersage)", "Show colour in solution (prediction)"),
    "color_tip": ("Aus dem Spektrum berechnet: Transmission 10^(−A) unter Tageslicht, CIE-1931-Farbmetrik → sRGB.\n"
                  "c und d frei wählbar (Lambert-Beer, Standard: höchste gemessene Konzentration in 1 cm).\n"
                  "Fluoreszenz und Streuung werden nicht berücksichtigt; Bildschirmfarben sind nicht kalibriert.\n"
                  "Nur Anzeige, erscheint nicht in der Abbildung.",
                  "Calculated from the spectrum: transmission 10^(−A) under daylight, CIE 1931 colorimetry → sRGB.\n"
                  "c and d can be chosen freely (Beer–Lambert; default: highest measured concentration in 1 cm).\n"
                  "Fluorescence and scattering are ignored; screen colours are not calibrated.\n"
                  "Display only, not part of the figure."),
    "color_info": ("{hex}  (c = {c} {unit}, d = {d} cm, Tageslicht)", "{hex}  (c = {c} {unit}, d = {d} cm, daylight)"),
    "ov_calc_color": ("Farbe in Lösung", "Colour in solution"),
    "ov_calc_color_tip": ("Vorhersage aus dem gerechneten Spektrum: A(λ) = ε(λ)·c·d, Transmission unter Tageslicht, "
                          "CIE 1931 → sRGB (wie im ε-Tab). Standard 1 mM in 1 cm.",
                          "Prediction from the calculated spectrum: A(λ) = ε(λ)·c·d, transmission under daylight, "
                          "CIE 1931 → sRGB (as in the ε tab). Default 1 mM in 1 cm."),
    "ov_calc_color_hint": ("Hängt von FWHM und Verschiebung ab; TD-DFT-Energien liegen oft 0,2–0,3 eV daneben – "
                           "nur qualitativ.",
                           "Depends on FWHM and shift; TD-DFT energies are often off by 0.2–0.3 eV – qualitative only."),
    "color_partial": ("⚠ Spektrum deckt nur {p} % von 380–780 nm ab – Rest als farblos gerechnet.",
                      "⚠ Spectrum covers only {p} % of 380–780 nm – the rest is treated as colourless."),
    "color_gamut": ("Sehr gesättigte Farbe: außerhalb des Bildschirm-Farbraums (sRGB), angenähert.",
                    "Very saturated colour: outside the screen gamut (sRGB), approximated."),
    # ---- Hover-Anzeige -----------------------------------------------------
    "hover_lam": ("λ = {lam:.1f} nm", "λ = {lam:.1f} nm"),
    "hover_abs": ("λ = {lam:.1f} nm    A = {a:.4f}    ({name})   –   Doppelklick: Bande hinzufügen/entfernen",
                  "λ = {lam:.1f} nm    A = {a:.4f}    ({name})   –   double-click: add/remove band"),
    "hover_y": ("λ = {lam:.1f} nm    y = {y:.3f}    {name}", "λ = {lam:.1f} nm    y = {y:.3f}    {name}"),
    "hover_eps": ("λ = {lam:.1f} nm    ε = {eps:.2f}·10³ M⁻¹ cm⁻¹    {name}",
                  "λ = {lam:.1f} nm    ε = {eps:.2f}·10³ M⁻¹ cm⁻¹    {name}"),
    "band_added": ("Bande {lam} nm hinzugefügt (erneuter Doppelklick entfernt sie).",
                   "Band {lam} nm added (double-click again to remove it)."),
    "band_removed": ("Bande {lam} nm entfernt.", "Band {lam} nm removed."),
    # ---- Update-Prüfung ---------------------------------------------------
    "act_check_updates": ("Nach Updates suchen …", "Check for updates …"),
    "act_auto_updates": ("Beim Start automatisch nach Updates suchen", "Check for updates on startup"),
    "upd_title": ("Update", "Update"),
    "upd_available": ("Version {new} ist verfügbar (installiert: {cur}).\n\nAuf der Release-Seite herunterladen: "
                      "{file}\nVerbindungen, Projekte und Einstellungen bleiben erhalten.",
                      "Version {new} is available (installed: {cur}).\n\nDownload from the release page: {file}\nCompounds, "
                      "projects and settings are kept."),
    "upd_no_asset": ("die Datei für dein System", "the file for your system"),
    "upd_current": ("Du hast die aktuelle Version ({cur}).", "You have the latest version ({cur})."),
    "upd_failed": ("Update-Prüfung fehlgeschlagen (keine Internetverbindung?):\n{err}",
                   "Update check failed (no internet connection?):\n{err}"),
    "upd_open": ("Release-Seite öffnen", "Open release page"),
    "upd_skip": ("Diese Version überspringen", "Skip this version"),
    "upd_later": ("Später", "Later"),
    "tf_missing": ("Schrift „{name}“ nicht gefunden – Ersatzschrift wird verwendet.",
                   "Font “{name}” not found – using a fallback font."),
    # ---- X-Ray -------------------------------------------------------------
    "tab_xray": ("X-Ray", "X-Ray"),
    "xr_structures": ("Strukturen (CIF)", "Structures (CIF)"),
    "xr_add": ("CIF hinzufügen …", "Add CIF …"),
    "xr_name": ("Name (in Tabellen)", "Name (in tables)"),
    "xr_ref": ("Interne Referenz", "Internal reference"),
    "xr_npd": ("Nicht positiv definit (als Kugel aus U_iso gezeichnet): {atoms}",
               "Non-positive definite (drawn as sphere from U_iso): {atoms}"),
    "xr_no_symops": ("Keine Symmetrieoperationen in der CIF – als P1 gezeigt, Molekül evtl. unvollständig",
                     "No symmetry operations in the CIF – shown as P1, molecule may be incomplete"),
    "xr_align_collinear": ("Die gewählten Atome liegen auf einer Linie – keine Ebene.",
                           "The selected atoms are collinear – no plane."),
    "xr_cif_truncated": ("CIF unvollständig: Schleife {tag} endet mitten in einer Zeile",
                         "incomplete CIF: loop {tag} ends in the middle of a row"),
    "xr_no_atoms": ("keine Atome (_atom_site_fract_x) in der Datei", "no atoms (_atom_site_fract_x) in the file"),
    "xr_display": ("Darstellung", "Display"),
    "xr_prob": ("Ellipsoide", "Ellipsoids"),
    "xr_prob_tip": ("Aufenthaltswahrscheinlichkeit der Schwingungsellipsoide (üblich: 50 %)",
                    "Probability level of the displacement ellipsoids (usual: 50 %)"),
    "xr_disorder": ("Fehlordnung", "Disorder"),
    "xr_dis_main": ("Nur Hauptteil", "Major part only"),
    "xr_dis_all": ("Alle Teile (PART)", "All parts (PART)"),
    "xr_dis_minor": ("Nebenteil", "Minor part"),
    "xr_show_h": ("H-Atome", "H atoms"),
    "xr_labels": ("Labels", "Labels"),
    "xr_h_labels": ("H-Labels", "H labels"),
    "xr_bond_lw": ("Bindungsdicke", "Bond thickness"),
    "xr_label_size": ("Labelgröße", "Label size"),
    "xr_label_size_std": ("Wie Textformat", "As text format"),
    "xr_label_size_tip": ("Schriftgröße der Atomlabels in diesem Tab; ganz links = Größe aus Format → Text",
                          "Font size of the atom labels in this tab; leftmost = size from Format → Text"),
    "xr_frags": ("Fragmente", "Fragments"),
    "xr_frags_tip": ("Getrennte Fragmente (Lösungsmittel, Gegenionen) ein-/ausblenden",
                     "Show/hide separate fragments (solvent, counter-ions)"),
    "xr_main_frag": ("Größtes", "Largest"),
    "xr_prev_view": ("Vorige Ansicht", "Previous view"),
    "xr_prev_view_tip": ("Letzte Drehung, Verschiebung oder Zoomänderung der gewählten Struktur zurücknehmen "
                         "(mehrfach möglich).",
                         "Undo the last rotation, pan or zoom of the selected structure (repeatable)."),
    "xr_prev_view_none": ("Keine frühere Ansicht.", "No earlier view."),
    "xr_reset_view": ("Startansicht", "Reset view"),
    "xr_reset_view_tip": ("Drehung, Zoom und Lage der Labels der gewählten Struktur auf den Start.",
                          "Rotation, zoom and label positions of the selected structure back to the start."),
    "xr_reset_display": ("Auf Standard", "Reset display"),
    "xr_reset_display_tip": ("Darstellung zurücksetzen: Aussehen auf Standard (Stil, Ellipsoide/Radien, Bindungsdicke,\n"
                             "Labels, Labelgröße, H-Atome, Farben …) und für die gewählte Struktur Ansicht, Labels je Atom\n"
                             "und Drahtmodell. Nichts Wissenschaftliches ändert sich: Dateien, Namen, Nummerierung,\n"
                             "Fehlordnung, ausgeblendete Atome/Fragmente, Spalten der Rechnung, ausgewählte Parameter und\n"
                             "Exportgröße bleiben. Rückgängig mit Strg+Z.",
                             "Reset display: the look back to defaults (style, ellipsoids/radii, bond thickness, labels,\n"
                             "label size, H atoms, colours …) and, for the selected structure, view, labels per atom and\n"
                             "wireframe. Nothing scientific changes: files, names, numbering, disorder, hidden atoms/\n"
                             "fragments, calculation columns, selected parameters and export size stay. Undo with Ctrl+Z."),
    "xr_reset_display_done": ("Darstellung auf Standard gesetzt, Auswertung unverändert – Rückgängig mit Strg+Z.",
                              "Display reset to defaults, analysis unchanged – undo with Ctrl+Z."),
    "xr_mouse_hint": ("Ziehen = drehen, rechte Taste = verschieben, Mausrad = Zoom, Klick = Atom wählen "
                      "(2 = Abstand, 3 = Winkel, 4 = Diederwinkel), Doppelklick = Label an/aus, Shift + Rahmen = Labels "
                      "mehrerer Atome an/aus, Labels lassen sich verschieben.",
                      "Drag = rotate, right button = pan, wheel = zoom, click = pick atom "
                      "(2 = distance, 3 = angle, 4 = torsion), double-click = label on/off, Shift + drag a box = labels "
                      "of several atoms on/off; labels can be dragged."),
    "xr_box_labels_off": ("Labels ausblenden ({n} Atome)", "Hide labels ({n} atoms)"),
    "xr_box_labels_on": ("Labels zeigen ({n} Atome)", "Show labels ({n} atoms)"),
    "xr_colors": ('Atomfarben', 'Atom Colours'),
    "xr_colors_reset": ("Olex2-Standardfarben", "Olex2 default colours"),
    "xr_select": ("Ausgewählte Parameter", "Selected Parameters"),
    "xr_calc": ("Vergleich mit Rechnung", "Comparison with Calculation"),
    "xr_calc_src": ("Rechnung", "Calculation"),
    "xr_calc_src_tip": ("Berechnete Geometrie derselben Verbindung: aus dem DFT-Tab oder als Datei (xyz, ORCA, Gaussian)",
                        "Calculated geometry of the same compound: from the DFT tab or as a file (xyz, ORCA, Gaussian)"),
    "xr_calc_none": ("Keine", "None"),
    "xr_calc_file": ("Datei …", "File …"),
    "xr_calc_file_tip": ("Berechnete Geometrie laden (xyz, ORCA- oder Gaussian-Ausgabe); die Datei bleibt unverändert",
                         "Load a calculated geometry (xyz, ORCA or Gaussian output); the file is not changed"),
    "xr_calc_file_item": ("Datei: ", "File: "),
    "xr_calc_flt": ("Geometrie oder Rechnung", "Geometry or calculation"),
    "xr_calc_frag": ("Fragment", "Fragment"),
    "xr_calc_frag_tip": ("Teil der Kristallstruktur, der der Rechnung entspricht; weitere Moleküle (Lösungsmittel, "
                         "Gegenionen) bleiben dann unberücksichtigt",
                         "Part of the crystal structure that corresponds to the calculation; further molecules "
                         "(solvent, counter-ions) are then ignored"),
    "xr_calc_frag_pick": ("Wählen …", "Choose …"),
    "xr_calc_map": ("Zuordnung", "Assignment"),
    "xr_calc_map_tip": ("Atom der Kristallstruktur ↔ Atom der Rechnung (Nummer wie in der Datei)",
                        "Atom of the crystal structure ↔ atom of the calculation (number as in the file)"),
    "xr_calc_map_cif": ("CIF", "CIF"),
    "xr_calc_map_no": ("Nr. (Rechnung)", "No. (calc.)"),
    "xr_calc_map_el": ("Element", "Element"),
    "xr_calc_cols": ("Spalte Rechnung", "Calc. column"),
    "xr_calc_cols_long": ("Rechenwerte als Spalte neben den Kristallwerten (Tabellen, Excel/CSV, Word)",
                          "Calculated values as a column next to the crystal values (tables, Excel/CSV, Word)"),
    "xr_calc_delta": ("Spalte Δ", "Δ column"),
    "xr_calc_delta_long": ("Zusätzliche Spalte Δ = Rechnung − Kristall", "Additional column Δ = calc. − X-ray"),
    "xr_calc_done": ("{nh} Schweratome und {nH} H über das Bindungsnetz zugeordnet; RMSD der Schweratome nach "
                     "Überlagerung {rmsd} Å.",
                     "{nh} heavy atoms and {nH} H assigned via the bond network; heavy-atom RMSD after superposition "
                     "{rmsd} Å."),
    "xr_calc_equiv": ("{n} gleichwertige Zuordnungen (Symmetrie des Moleküls): die gewählten Parameter sind für alle "
                      "gleich.",
                      "{n} equivalent assignments (molecular symmetry): the selected parameters are identical for "
                      "all of them."),
    "xr_calc_amb": ("Gleich gute Zuordnungen ergeben verschiedene Werte für: {params}. Die Zuordnung mit der "
                    "kleinsten Abweichung ist gewählt – bitte prüfen.",
                    "Equally good assignments give different values for: {params}. The assignment with the smallest "
                    "deviation is used – please check."),
    "xr_calc_next": ("Nächstbeste Zuordnung: RMSD {alt} Å.", "Next best assignment: RMSD {alt} Å."),
    "xr_calc_mirror": ("Die Rechnung ist das Spiegelbild der Kristallstruktur: Torsionswinkel haben das umgekehrte "
                       "Vorzeichen.",
                       "The calculation is the mirror image of the crystal structure: torsion angles have the "
                       "opposite sign."),
    "xr_calc_formula": ("Zusammensetzung verschieden: Kristall {cif}, Rechnung {calc}. Nicht zugeordnet.",
                        "Different composition: crystal {cif}, calculation {calc}. Not assigned."),
    "xr_calc_graph": ("Bindungsnetz verschieden (Kristall {nr}, Rechnung {nt} Bindungen zwischen Schweratomen); "
                      "abweichend: {atoms}. Nicht zugeordnet.",
                      "Different bond network (crystal {nr}, calculation {nt} bonds between heavy atoms); "
                      "differing: {atoms}. Not assigned."),
    "xr_calc_h": ("{atom}: {nr} H im Kristall, {nt} in der Rechnung. Nicht zugeordnet.",
                  "{atom}: {nr} H in the crystal, {nt} in the calculation. Not assigned."),
    "xr_calc_same_geom": ("Die Geometrie der Rechnung ist praktisch die Kristallgeometrie (RMSD {rmsd} Å): vermutlich "
                          "ein Einzelpunkt auf den Kristallkoordinaten. Die Spalte vergleicht dann nichts; für den "
                          "Vergleich die optimierte Geometrie wählen.",
                          "The geometry of the calculation is practically the crystal geometry (RMSD {rmsd} Å): "
                          "probably a single point on the crystal coordinates. The column then compares nothing; "
                          "choose the optimized geometry for the comparison."),
    "xr_calc_hdiff": ("Zahl der H-Atome verschieden – {atoms}. Das Gerüst ist zugeordnet, überzählige H bleiben ohne "
                      "Partner. Prüfen, ob es dieselbe Spezies ist (in hinterlegten CIFs fehlt manchmal ein H).",
                      "Number of H atoms differs – {atoms}. The framework is assigned, surplus H stay without a "
                      "partner. Check that it is the same species (deposited CIFs sometimes lack an H)."),
    "xr_calc_hdiff_at": ("{atom}: Kristall {nr}, Rechnung {nt}", "{atom}: crystal {nr}, calculation {nt}"),
    "xr_calc_h_free": ("{n} H-Atome ohne Bindung zu einem Schweratom. Nicht zugeordnet.",
                       "{n} H atoms not bonded to a heavy atom. Not assigned."),
    "xr_calc_need_frag": ("Die Kristallstruktur hat {n} Fragmente (z. B. Lösungsmittel, Gegenionen): Fragment wählen, "
                          "das der Rechnung entspricht.",
                          "The crystal structure has {n} fragments (e.g. solvent, counter-ions): choose the fragment "
                          "that corresponds to the calculation."),
    "xr_calc_dis_hint": ("Fehlordnung: unter Darstellung → Fehlordnung einen Teil wählen, nicht alle Teile.",
                         "Disorder: choose one part under Display → Disorder, not all parts."),
    "xr_calc_no_cif": ("Kristallstruktur nicht lesbar.", "Crystal structure not readable."),
    "xr_calc_missing": ("Datei der Rechnung fehlt: {f}", "Calculation file missing: {f}"),
    "xr_calc_stale": ("Die Zuordnung passt nicht zur gezeigten Struktur: Rechnung neu wählen.",
                      "The assignment does not fit the structure shown: choose the calculation again."),
    "dft_measure": ('Messen (Abstand, Winkel, Diederwinkel)', 'Measure (Distance, Angle, Dihedral)'),
    "xr_select_hint": ("Atome in der Abbildung anklicken.", "Click atoms in the figure."),
    "xr_take": ("In Liste übernehmen", "Add to list"),
    "xr_clear_sel": ("Auswahl aufheben", "Clear selection"),
    "xr_kind_bond": ("Abstand", "Distance"),
    "xr_kind_angle": ("Winkel", "Angle"),
    "xr_kind_torsion": ("Diederwinkel", "Torsion angle"),
    "xr_no_esd": ("nicht in der CIF – aus den Koordinaten berechnet, ohne Standardabweichung",
                  "not in the CIF – calculated from the coordinates, without s.u."),
    "xr_no_esd_torsion": ("nicht in der CIF – ohne Standardabweichung berechnet; für Werte mit esd CONF in "
                          "Olex2/SHELXL setzen und neu verfeinern",
                          "not in the CIF – calculated without s.u.; for values with s.u. set CONF in "
                          "Olex2/SHELXL and refine again"),
    "xr_cif_no_esd": ("Wert aus der CIF (ohne Standardabweichung, z. B. reitendes H)",
                      "value from the CIF (no s.u., e.g. riding H)"),
    "xr_tables": ("Tabellen", "Tables"),
    "xr_copy_crystal": ("Kristalldaten kopieren", "Copy crystal data"),
    "xr_copy_params": ("Parameter kopieren", "Copy parameters"),
    "xr_excel": ("Excel speichern", "Save Excel"),
    "xr_info": ("{n} Atome in der asymmetrischen Einheit, {m} gezeigt/erzeugt, Raumgruppe {sg}",
                "{n} atoms in the asymmetric unit, {m} shown/generated, space group {sg}"),
    "xr_sym_info": ("Symmetrieerzeugt: {ops}", "Symmetry-generated: {ops}"),
    "xr_parts_info": ("Fehlordnung: PART {parts}", "Disorder: PART {parts}"),
    "xr_no_geom": ("Keine _geom_bond-Tabelle – Bindungen aus kovalenten Radien, Abstände ohne esd",
                   "No _geom_bond table – bonds from covalent radii, distances without s.u."),
    "xr_no_torsion": ("Keine _geom_torsion-Tabelle (CONF fehlt) – Diederwinkel ohne esd",
                      "No _geom_torsion table (CONF missing) – torsion angles without s.u."),
    "xr_style": ("Stil", "Style"),
    "xr_label_color": ("Labelfarbe", "Label colour"),
    "xr_label_color_black": ("Schwarz", "Black"),
    "xr_label_color_atom": ("Wie das Atom", "Like the atom"),
    "xr_label_color_color": ("Eigene Farbe …", "Custom colour …"),
    "xr_label_color_element": ("Je Element …", "Per element …"),
    "xr_label_color_pick": ("Labelfarbe", "Label colour"),
    "xr_style_mercury": ("Mercury (schattiert)", "Mercury (shaded)"),
    "xr_style_flat": ("Olex2 (flach, fette Labels)", "Olex2 (flat, bold labels)"),
    "xr_style_ballstick": ("Kugel-Stab, glänzend (wie IboView)", "Ball and stick, glossy (like IboView)"),
    "xr_style_depth": ("Kugel-Stab (wie ORCA-Handbuch)", "Ball and stick (like the ORCA manual)"),
    "xr_style_cartoon": ("Strichzeichnung (weiß, hohle Stäbe)", "Line drawing (white, hollow sticks)"),
    "dft_cartoon_color": ("Atome in Elementfarben", "Atoms in element colours"),
    "dft_cartoon_color_tip": ("Strichzeichnung: Kugeln in den Elementfarben statt weiß (Umriss und Stäbe bleiben)",
                              "Line drawing: balls in element colours instead of white (outline and sticks stay)"),
    "xr_atoms": ("Atome", "Atoms"),
    "xr_atom": ("Atom", "Atom"),
    "xr_atom_shown": ("Zeigen", "Show"),
    "xr_atom_label": ("Label", "Label"),
    "xr_atoms_tip": ("Einzelne Atome (z. B. H) ausblenden und Labels je Atom an-/abschalten; "
                     "Doppelklick auf ein Atom in der Abbildung schaltet sein Label um, Shift + Rahmen ziehen die Labels "
                     "mehrerer Atome. Draht: Atom im Drahtmodell zeigen (nur das Bild).",
                     "Hide single atoms (e.g. H) and switch labels per atom; "
                     "double-click an atom in the figure to toggle its label, Shift + drag a box for several atoms. "
                     "Wire: show the atom as wireframe (figure only)."),
    "xr_labels_all": ("Alle Labels", "All labels"),
    "xr_labels_none": ("Keine Labels", "No labels"),
    "xr_atoms_reset": ("Standard", "Default"),
    "xr_label_mode": ("Labels für", "Labels for"),
    "xr_lab_all": ("Alle Nicht-H-Atome", "All non-H atoms"),
    "xr_lab_hetero": ("Nur Heteroatome (ohne C)", "Heteroatoms only (no C)"),
    "xr_hide_solv": ("Lösungsmittel ausblenden", "Hide solvent"),
    "xr_hide_ions": ("Gegenionen ausblenden", "Hide counterions"),
    "xr_hide_tip": ("Erkannt über die Summenformel des Fragments (THF, Et₂O, CH₂Cl₂, Toluol …; OTf⁻, BF₄⁻, PF₆⁻, "
                    "BArF⁻ …). Weitere Fragmente einzeln in der Liste abhaken.",
                    "Recognized from the fragment's formula (THF, Et₂O, CH₂Cl₂, toluene …; OTf⁻, BF₄⁻, PF₆⁻, BArF⁻ …). "
                    "Untick other fragments individually in the list."),
    "xr_kind_molecule": ("Weiteres Molekül, Z′ > 1", "Further molecule, Z′ > 1"),
    "xr_kind_solvent": ("Lösungsmittel", "solvent"),
    "xr_kind_ion": ("Gegenion", "counterion"),
    "xr_atom_wire": ("Draht", "Wire"),
    "xr_wire": ("Als Drahtmodell", "As wireframe"),
    "xr_wire_tip": ("Bindung zum Substituenten wählen, Atom am Kern zuerst (z. B. N, dann C_ipso): alles dahinter wird "
                    "als Drahtmodell gezeigt. Liegt die Bindung in einem Ring (z. B. Spiro-C, dann ein Atom des "
                    "Ringsystems), wird das Ringsystem hinter dem ersten Atom Drahtmodell. Sonst die gewählten Atome.",
                    "Select the bond to the substituent, core atom first (e.g. N, then C_ipso): everything behind it "
                    "is shown as wireframe. If the bond is part of a ring (e.g. spiro C, then an atom of the ring "
                    "system), the ring system behind the first atom becomes wireframe. Otherwise the selected atoms."),
    "xr_unwire": ("Drahtmodell aufheben", "Remove wireframe"),
    "xr_unwire_tip": ("Für die gewählten Atome bzw. den Substituent hinter der gewählten Bindung; ohne Auswahl für alle",
                      "For the selected atoms or the substituent behind the selected bond; without selection for all"),
    "xr_wire_hint": ("Erst eine Bindung (2 Atome) oder Atome in der Abbildung anklicken.",
                     "First click a bond (2 atoms) or atoms in the figure."),
    "xr_wire_ring": ("Hinter dieser Bindung lässt sich nichts abtrennen (Ring im Kern). Einzelne Atome wählen oder in "
                     "der Atomliste „Draht“ ankreuzen.",
                     "Nothing can be separated behind this bond (ring in the core). Select individual atoms or tick "
                     "“wire” in the atom list."),
    "xr_wire_h": ("H am Drahtmodell", "H on wireframe"),
    "xr_wire_h_tip": ("H-Atome an Drahtmodell-Gruppen zeigen (sonst ausgeblendet)",
                      "Show H atoms on wireframe groups (hidden otherwise)"),
    "xr_wire_name": ("Drahtmodell-Gruppen", "Wireframe groups"),
    "xr_wire_name_ph": ("Z. B. Dipp groups", "E.g. Dipp groups"),
    "xr_wire_name_tip": ("Bezeichnung der Drahtmodell-Gruppen für die Bildunterschrift", "Name of the wireframe groups for the caption"),
    "xr_par_head": ("Parameter", "Parameter"),
    "xr_par_value": ("Wert", "Value"),
    "xr_par_empty": ("Gemessene Abstände und Winkel erscheinen hier.", "Measured distances and angles appear here."),
    "tbl_empty_results": ("Noch keine Ergebnisse.", "No results yet."),
    "tbl_empty_raw": ("Noch keine Rohdaten: TopSpin-Daten hinzufügen.", "No raw data yet: add TopSpin data."),
    "tbl_empty_amounts": ("Noch keine Reagenzien: mit + hinzufügen oder aus dem Schema übernehmen.",
                          "No reagents yet: add with + or take them from the scheme."),
    "tbl_empty_calcs": ("Noch keine Rechnungen: oben übernehmen oder laden.", "No calculations yet: import or load them above."),
    "tbl_empty_tables": ("Noch keine Tabellen: sie erscheinen mit der ersten Struktur.", "No tables yet: they appear with the first structure."),
    "xr_caption": ("Bildunterschrift", "Caption"),
    "xr_caption_copy": ("Bildunterschrift kopieren", "Copy caption"),
    "xr_align": ("Ausrichten", "Orientation"),
    "xr_align_bond": ("Bindung zeigt", "Bond points"),
    "xr_align_bond_tip": ("2 Atome anklicken (erst Start-, dann Endatom): die Bindung zeigt danach im Bild nach unten, "
                          "oben, links oder rechts und liegt in der Bildebene",
                          "Click 2 atoms (start atom first, then end atom): the bond then points down, up, left or "
                          "right in the image and lies in the image plane"),
    "xr_align_plane": ("Ebene von vorn (≥ 3 gewählte Atome)", "Plane face-on (≥ 3 selected atoms)"),
    "xr_align_plane_tip": ("Blick senkrecht auf die Ebene durch die gewählten Atome, z. B. einen Ring; danach lässt sich "
                           "eine Bindung in dieser Ebene mit den Pfeilen ausrichten, ohne die Ebene zu kippen",
                           "View perpendicular to the plane through the selected atoms, e.g. a ring; a bond within this "
                           "plane can then be aligned with the arrows without tilting the plane"),
    "xr_rotate": ("Drehen um", "Rotate about"),
    "xr_rot_tip": ("x = waagerecht, y = senkrecht, z = Blickrichtung", "x = horizontal, y = vertical, z = view axis"),
    "xr_flip": ("Von hinten (180°)", "From behind (180°)"),
    "xr_flip_tip": ("Um die senkrechte Achse um 180° drehen", "Rotate by 180° about the vertical axis"),
    "xr_template": ("Wie ChemDraw ausrichten …", "Orient like ChemDraw …"),
    "xr_template_tip": ("Lage wie in der ChemDraw-Zeichnung (CDXML der Verbindung, sonst Datei wählen). Zuordnung über "
                        "Elemente und Verknüpfung, H und Bindungsordnungen zählen nicht.",
                        "Orientation as in the ChemDraw drawing (CDXML of the compound, otherwise choose a file). Matched by "
                        "elements and connectivity; H atoms and bond orders do not count."),
    "xr_template_done": ("Wie {f} ausgerichtet: {n} von {nt} Atomen zugeordnet, Abweichung der Projektion {rmsd} Å.",
                         "Oriented like {f}: {n} of {nt} atoms matched, deviation of the projection {rmsd} Å."),
    "xr_template_amb": ("⚠ Zuordnung nicht eindeutig (symmetrisches Molekül) – Ansicht prüfen, ggf. „Von hinten“.",
                        "⚠ matching not unique (symmetric molecule) – check the view, use “From behind” if needed."),
    "xr_template_fail": ("⚠ Ausrichten nach ChemDraw nicht möglich: {err}", "⚠ cannot orient like ChemDraw: {err}"),
    "xr_align_need2": ("Erst 2 Atome anklicken (Start- und Endatom der Bindung).",
                       "First click 2 atoms (start and end atom of the bond)."),
    "xr_align_need3": ("Erst mindestens 3 Atome der Ebene anklicken.", "First click at least 3 atoms of the plane."),
    "xr_align_done_bond": ("{bond} zeigt jetzt in die gewählte Richtung.", "{bond} now points in the chosen direction."),
    "xr_align_done_plane": ("Ebene durch {atoms} liegt jetzt in der Bildebene.",
                            "Plane through {atoms} now lies in the image plane."),
    "xr_truncated": ("Polymer/Netzwerk: Vervollständigung abgebrochen", "Polymer/network: growing stopped"),

    # ---- Synthese ----------------------------------------------------------
    "tab_syn": ("Synthese", "Synthesis"),
    "syn_title_grp": ("Überschrift", "Heading"),
    "syn_name_tip": ("Name/Nummer der Verbindung in „Synthesis of …“ (leer = Name unter „Verbindung“)",
                     "Name/number of the compound in “Synthesis of …” (empty = name under “Compound”)"),
    "syn_name_ph": ("Z. B. S2", "E.g. S2"),
    "syn_old_name": ("Diese Vorschrift heißt noch „Synthesis of {name}“ (früher hier eingetragen). Namen vergibt jetzt nur "
                     "der Tab „Verbindung“.",
                     "This procedure is still titled “Synthesis of {name}” (entered here earlier). Names are now assigned "
                     "only on the Compound tab."),
    "syn_old_name_adopt": ("Als Name der Verbindung übernehmen", "Use as the compound's name"),
    "syn_old_name_drop": ("Verwerfen", "Discard"),
    "syn_scheme": ('Reaktionsschema (ChemDraw)', 'Reaction Scheme (ChemDraw)'),
    "syn_scheme_pick": ("Schema wählen …", "Choose scheme …"),
    "syn_scheme_hint": ("CDXML wählen oder „In ChemDraw bearbeiten“ (Speichern übernimmt das Schema). Das Bild "
                        "zeichnet Elucida aus der CDXML; eine gleichnamige SVG/PDF daneben hat Vorrang und wird "
                        "unverändert übernommen. Optional, ebenfalls gleichnamig: .cdx = in Word bearbeitbares "
                        "ChemDraw-Objekt, .emf = dessen scharfe Vorschau. Dateien, die älter als die CDXML sind, "
                        "werden ignoriert.",
                        "Choose the CDXML or use “Edit in ChemDraw” (saving takes over the scheme). Elucida draws the "
                        "picture from the CDXML; an SVG/PDF of the same name next to it takes precedence and is used "
                        "unchanged. Optional, also with the same name: .cdx = ChemDraw object editable in Word, "
                        ".emf = its sharp preview. Files older than the CDXML are ignored."),
    "syn_scheme_hint_short": ("CDXML wählen oder „In ChemDraw bearbeiten“ (Speichern übernimmt das Schema; "
                              "gleichnamige SVG/PDF, .cdx, .emf: siehe Tooltip).",
                              "Choose the CDXML or use “Edit in ChemDraw” (saving takes over the scheme; SVG/PDF, "
                              ".cdx, .emf of the same name: see tooltip)."),
    "syn_scheme_none": ("Kein Schema gewählt.", "No scheme chosen."),
    "syn_scheme_pic": ("Bild: {f}", "Picture: {f}"),
    "syn_scheme_nopic": ("Gezeichnet aus den Koordinaten der CDXML (Bindungen, Labels, Pfeil, Bedingungen). Ein SVG/PDF "
                         "aus ChemDraw daneben wird unverändert übernommen.",
                         "Drawn from the CDXML coordinates (bonds, labels, arrow, conditions). An SVG/PDF exported "
                         "from ChemDraw next to it is used unchanged."),
    "syn_scheme_notdrawn": ("Nicht gezeichnet: {what} – dafür SVG/PDF aus ChemDraw daneben speichern.",
                            "Not drawn: {what} – save an SVG/PDF from ChemDraw next to it."),
    "syn_scheme_cdx": ("Word: bearbeitbares ChemDraw-Objekt (CDX gefunden),", "Word: editable ChemDraw object (CDX "
                                                                              "found),"),
    "syn_scheme_emf": ("Vorschau als Vektor (EMF).", "vector preview (EMF)."),
    "syn_scheme_png": ("Vorschau als Bild (für Vektor-Vorschau .emf aus ChemDraw daneben legen).",
                       "picture preview (place an .emf from ChemDraw next to it for a vector preview)."),
    "syn_scheme_nocdx": ("Word: Bild (für ein bearbeitbares Objekt die .cdx aus ChemDraw daneben legen).",
                         "Word: picture (place the .cdx from ChemDraw next to it for an editable object)."),
    "syn_need_cdxml": ("Für die Molmassen eine CDXML als Schema wählen.", "Choose a CDXML scheme for the molar masses."),
    "syn_proc": ("Vorschrift", "Procedure"),
    "syn_proc_ph": ("In a round-bottom flask S1 (1.03 g, 5.00 mmol, 1.0 eq.) was dissolved in …",
                    "In a round-bottom flask S1 (1.03 g, 5.00 mmol, 1.0 eq.) was dissolved in …"),
    "syn_bold": ("Fett (Verbindungsnummern)", "Bold (compound numbers)"),
    "syn_italic": ("Kursiv", "Italic"),
    "syn_sub": ("Tiefgestellt", "Subscript"),
    "syn_sup": ("Hochgestellt", "Superscript"),
    "syn_check_none": ("Keine Mengenangaben „(… mg, … mmol, … eq.)“ in der Vorschrift.",
                       "No amounts “(… mg, … mmol, … eq.)” in the procedure."),
    "syn_reagents": ('Reagenzien (Mengen berechnen)', 'Reagents (Calculate Amounts)'),
    "syn_col_name": ("Name", "Name"),
    "syn_col_M": ("M / Formel", "M / formula"),
    "syn_col_role": ("Rolle", "Role"),
    "syn_col_eq": ("eq. / %", "eq. / %"),
    "syn_role_ref": ("Bezug (1.0 eq.)", "Reference (1.0 eq.)"),
    "syn_role_reagent": ("Reagenz", "Reagent"),
    "syn_role_product": ("Produkt", "Product"),
    "syn_role_other": ("Sonstiges", "Other"),
    "syn_table_tip": ("M als Zahl (g mol⁻¹) oder Summenformel; n aus m/M, V·c oder V·ρ/M; eq. bzw. Ausbeute bezogen auf "
                      "die Zeile „Bezug“. Die Namen dienen auch der Prüfung der Vorschrift.\nAusfüllen: m + M, V + c oder V + ρ + M "
                      "(m hat Vorrang) oder n direkt (zählt, wenn n nicht aus m/V berechenbar ist); fehlt eine Angabe, bleiben n und eq. leer („–“)."
                      "\nEinheit darf in der Zelle stehen („1.03 g“, „150 µL“, „800 mM“, „0.5 mol“), sonst gilt die Spalte; "
                      "in die SI kommt der Wert wie eingegeben.",
                      "M as number (g mol⁻¹) or formula; n from m/M, V·c or V·ρ/M; eq. or yield relative to the "
                      "“reference” row. The names are also used to check the procedure.\nFill in: m + M, V + c or V + ρ + M "
                      "(m takes precedence) or n directly (counts when n cannot be computed from m/V); if one is missing, n and eq. stay "
                      "empty (“–”).\nA unit may follow the number (“1.03 g”, “150 µL”, “800 mM”, “0.5 mol”), otherwise the "
                      "column unit applies; the SI shows the value as entered."),
    "syn_gp_tip": ("Allgemeine Vorschrift (GP) des Projekts wählen und „according to GP A“ an der Schreibmarke "
                   "einfügen. Die GP steht in der SI vor dieser Verbindung (Gesamt-SI: einmal, vor der ersten Verbindung, "
                   "die sie benutzt).",
                   "Choose a general procedure (GP) of the project and insert “according to GP A” at the cursor. The "
                   "GP precedes this compound in the SI (combined SI: once, before the first compound using it)."),
    "syn_gp_none_defined": ("Keine GP im Projekt", "No GP in the project"),
    "syn_gp_left": ("Die Vorschrift verweist noch auf GP {key} – Text anpassen.",
                    "The procedure still refers to GP {key} – edit the text."),
    "syn_gp_off": ("Keine GP", "No GP"),
    "syn_M_bad": ("Molmasse nicht lesbar (Zahl oder Summenformel)", "molar mass not readable (number or formula)"),
    "syn_row_add": ("Zeile +", "Row +"),
    "syn_from_scheme": ("Aus Schema", "From scheme"),
    "syn_from_scheme_tip": ("Edukte (erstes = Bezug), Reagenzien und Lösungsmittel über/unter dem Pfeil und das Produkt "
                            "als Zeilen anlegen; Bedingungen (rt, 1 h …) fallen weg, Namen der Moleküle selbst eintragen. "
                            "Mit ChemDraw-Reagenzientabelle in derselben CDXML: Mengen daraus (nur leere Zellen, "
                            "limitierend = Bezug).",
                            "Add reactants (first = reference), reagents and solvents above/below the arrow and the "
                            "product as rows; conditions (rt, 1 h …) are skipped, enter the molecule names yourself. "
                            "With a ChemDraw stoichiometry table in the same CDXML: amounts from it (empty cells only, "
                            "limiting = reference)."),
    "syn_grid_purity": ("{f}: {what} in ChemDraw nicht 100 % – Elucida rechnet ohne Reinheit, Menge prüfen.",
                        "{f}: {what} in ChemDraw is not 100% – Elucida ignores purity, check the amount."),
    "syn_grid_many": ("Mehrere ChemDraw-Reagenzientabellen in der CDXML – alle übernommen, Zeilen prüfen.",
                      "Several ChemDraw stoichiometry tables in the CDXML – all imported, check the rows."),
    "syn_insert": ("Klammer einfügen", "Insert amounts"),
    "syn_insert_tip": ("„(1.03 g, 5.00 mmol, 1.0 eq.)“ der gewählten Zeile an der Schreibmarke einfügen",
                       "Insert “(1.03 g, 5.00 mmol, 1.0 eq.)” of the selected row at the cursor"),
    "syn_no_mass": ("keine Atommasse für {el}", "no atomic mass for {el}"),
    "syn_chk_mass_ok": ("{name}: Masse und mmol passen zu M = {M} g mol⁻¹.", "{name}: mass and mmol match M = {M} g mol⁻¹."),
    "syn_chk_mass_bad": ("{name}: Masse passt nicht zu mmol (mit M = {M} g mol⁻¹ wären es {n} mmol).",
                         "{name}: mass does not match mmol (with M = {M} g mol⁻¹ it would be {n} mmol)."),
    "syn_chk_mass_implied": ("{name}: Masse/mmol ergibt M = {lo}–{hi} g mol⁻¹ (Molmasse in der Tabelle eintragen zum "
                             "Prüfen).", "{name}: mass/mmol gives M = {lo}–{hi} g mol⁻¹ (enter the molar mass in the "
                                         "table to check)."),
    "syn_chk_conc_ok": ("{name}: Volumen × Konzentration passt zu mmol.", "{name}: volume × concentration matches mmol."),
    "syn_chk_conc_bad": ("{name}: Volumen × Konzentration ergibt {n} mmol.",
                         "{name}: volume × concentration gives {n} mmol."),
    "syn_chk_dens_ok": ("{name}: Volumen × Dichte / M passt zu mmol.", "{name}: volume × density / M matches mmol."),
    "syn_chk_dens_bad": ("{name}: Volumen × Dichte / M ergibt {n} mmol.", "{name}: volume × density / M gives {n} mmol."),
    "syn_chk_vol_unknown": ("{name}: Volumen ohne Konzentration oder Dichte – nicht prüfbar.",
                            "{name}: volume without concentration or density – cannot be checked."),
    "syn_chk_eq_ok": ("{name}: eq. passt (n/n({ref}) = {eq}).", "{name}: eq. matches (n/n({ref}) = {eq})."),
    "syn_chk_eq_bad": ("{name}: eq. passt nicht – n/n({ref}) = {eq}.", "{name}: eq. does not match – n/n({ref}) = {eq}."),
    "syn_chk_yield_ok": ("{name}: Ausbeute passt ({y} % bezogen auf {ref}).", "{name}: yield matches ({y}% based on "
                                                                              "{ref})."),
    "syn_chk_yield_bad": ("{name}: Ausbeute passt nicht – {y} % bezogen auf {ref}.",
                          "{name}: yield does not match – {y}% based on {ref}."),
    "syn_chk_no_mmol": ("{name}: eq./Ausbeute ohne mmol – nicht prüfbar.", "{name}: eq./yield without mmol – cannot be "
                                                                          "checked."),
    "si_part_syn": ("Synthese (Schema, Vorschrift)", "Synthesis (scheme, procedure)"),

    # ---- NMR ---------------------------------------------------------------
    "tab_nmr": ("NMR", "NMR"),
    "nmr_empty": ("MNova-SVG hinzufügen oder hineinziehen (in MestReNova: Datei → Speichern unter → SVG).",
                  "Add or drop an MNova SVG (in MestReNova: File → Save As → SVG)."),
    "nmr_spectra": ("Spektren", "Spectra"),             # Mnova-Exporte und eigene Spektren aus Rohdaten
    "nmr_add": ("Spektrum hinzufügen …", "Add spectrum …"),
    "nmr_file": ("Datei", "File"),
    "nmr_nuclei": ("Kern(e)", "Nucleus/nuclei"),
    "nmr_nuclei_tip": ("1D: z. B. 1H, 13C, 19F; 2D: zuerst die waagerechte, dann die senkrechte Achse, z. B. 1H/13C",
                       "1D: e.g. 1H, 13C, 19F; 2D: horizontal axis first, then vertical, e.g. 1H/13C"),
    "nmr_kind": ("Art", "Type"),
    "nmr_order_hint": ("Reihenfolge automatisch: ¹H, ¹³C, übrige Kerne nach Massenzahl, dann 2D (COSY, HSQC, HMBC, "
                       "NOESY …). In Word zwei Spektren je Seite.",
                       "Order is automatic: ¹H, ¹³C, other nuclei by mass number, then 2D (COSY, HSQC, HMBC, NOESY …). "
                       "Two spectra per page in Word."),
    "nmr_selected": ('Ausgewähltes Spektrum', 'Selected Spectrum'),
    "nmr_nuc_from_axis": ("Kern aus der Achsenbeschriftung erkannt.", "Nucleus recognized from the axis label."),
    "nmr_nuc_manual": ("Kern von Hand eingetragen.", "Nucleus entered by hand."),
    "nmr_nuc_missing": ("⚠ Kern nicht in der Achse gefunden – bitte eintragen (z. B. 1H oder 1H/13C).",
                        "⚠ nucleus not found in the axis label – please enter it (e.g. 1H or 1H/13C)."),
    "nmr_temp": ("Temperatur", "Temperature"),
    "nmr_freq": ("Frequenz [MHz]", "Frequency [MHz]"),
    "nmr_freq_ph": ("Aus dem MNova-Text bzw. Bruker", "From the MNova text or Bruker"),
    "nmr_freq_tip": ("Nur nötig, wenn der MNova-Text den Kern nicht enthält; 2D: 500/126",
                     "Only needed if the MNova text lacks the nucleus; 2D: 500/126"),
    "nmr_solvent": ("Lösungsmittel", "Solvent"),
    "nmr_solv_ph": ("Aus dem MNova-Text (z. B. CDCl3)", "From the MNova text (e.g. CDCl3)"),
    "nmr_bruker": ("Bruker-Ordner …", "Bruker folder …"),
    "nmr_bruker_tip": ("Experimentordner (mit acqus) diesem Spektrum zuordnen: Parameterübersicht; der Ordner kommt ganz in "
                       "die Verbindung (data/nmr/<Art>)",
                       "Assign the experiment folder (with acqus) to this spectrum: parameter overview; the whole folder is "
                       "copied into the compound (data/nmr/<kind>)"),
    "nmr_raw": ('Rohdaten', 'Raw Data'),
    "nmr_spec_flt": ("MNova-Spektren", "MNova spectra"),
    "nmr_emf_bad": ("keine EMF-Datei", "not an EMF file"),
    "nmr_emf_preview": ("{f}\n\nEMF: keine Vorschau in Elucida – das Spektrum geht unverändert nach Word (ohne eingesetzte "
                        "Struktur). Für Vorschau und Struktur das Spektrum als SVG aus MNova speichern.",
                        "{f}\n\nEMF: no preview in Elucida – the spectrum goes into Word unchanged (without the inserted "
                        "structure). For a preview and the structure, save the spectrum as SVG from MNova."),
    "nmr_emf_nopeaks": ("Peaklabels lassen sich nur aus SVG lesen – das Spektrum als SVG aus MNova speichern.",
                        "Peak labels can only be read from SVG – save the spectrum as SVG from MNova."),
    "nmr_raw_hint": ("TopSpin-Experimente und MNova-Dokumente werden ganz in die Verbindung übernommen und nach Art "
                     "abgelegt (data/nmr/1H, 13C, HSQC …). Aus MNova-Dokumenten wird jedes lesbare 1D-Spektrum mit FID "
                     "als eigenes Spektrum gezeigt; passt genau ein "
                     "Experiment zu einem Spektrum, wird es zugeordnet (Parameter, Temperatur).",
                     "TopSpin experiments and MNova documents are copied into the compound as a whole and sorted by kind "
                     "(data/nmr/1H, 13C, HSQC …). Every readable 1D spectrum with FID in an MNova document is shown as an "
                     "own spectrum; if exactly one experiment "
                     "fits a spectrum, it is assigned (parameters, temperature)."),
    "nmr_topspin": ("TopSpin-Daten …", "TopSpin data …"),
    "nmr_topspin_tip": ("Ein Experiment (Ordner mit acqus), einen Datensatz (10, 11, …) oder einen Ordner mit mehreren "
                        "Datensätzen wählen – auch per Ziehen ins Fenster",
                        "Choose an experiment (folder with acqus), a dataset (10, 11, …) or a folder with several "
                        "datasets – also by dragging into the window"),
    "nmr_mnova_tip": ("MestReNova-Dokument (.mnova) in die Verbindung übernehmen (data/nmr/mnova). Mit installiertem MNova "
                      "exportiert MNova eine Kopie: jede Seite mit Spektrum wird ein Spektrum, die NMR-Zeile kommt aus "
                      "MNovas Berichten, die FIDs hängen als Rohdaten daran. Ohne MNova wird jedes lesbare 1D-Spektrum mit "
                      "FID selbst verarbeitet (MNovas Referenzierung nur als Vorschlag). Die Datei selbst bleibt unverändert.",
                      "Copy a MestReNova document (.mnova) into the compound (data/nmr/mnova). With MNova installed, MNova "
                      "exports a copy: every page with a spectrum becomes a spectrum, the NMR line comes from MNova's "
                      "reports, the FIDs are attached as raw data. Without MNova every readable 1D spectrum with FID is "
                      "processed here (MNova's referencing only as a suggestion). The file itself stays unchanged."),
    "nmr_raw_remove_tip": ("Eintrag aus der Liste nehmen; die Dateien im Ordner der Verbindung bleiben",
                           "Remove the entry from the list; the files in the compound folder stay"),
    "nmr_raw_open_tip": ("Doppelklick: Ordner bzw. Datei öffnen", "Double-click: open folder or file"),
    "nmr_raw_kind": ("Art", "Kind"),
    "nmr_raw_name": ("Name", "Name"),
    "nmr_raw_pulprog": ("Pulsprogramm", "Pulse program"),
    "nmr_raw_spectrum": ("Spektrum", "Spectrum"),
    "nmr_raw_imported": ("NMR-Rohdaten, übernommene Experimente: {n} ({kinds})",
                         "NMR raw data, experiments copied: {n} ({kinds})"),
    "nmr_bruker_temp": ("T aus Bruker", "T from Bruker"),
    "nmr_bruker_temp_tip": ("Temperatur der Messung (TE) für die Bildunterschrift übernehmen",
                            "Use the measured temperature (TE) for the caption"),
    "nmr_no_bruker": ("Kein Bruker-Ordner zugeordnet (Temperatur Standard 298 K).",
                      "No Bruker folder assigned (temperature 298 K by default)."),
    "nmr_no_acqus": ("{p}: kein Bruker-Experiment (acqus fehlt)", "{p}: not a Bruker experiment (acqus missing)"),
    "nmr_p_nuc": ("Kern", "Nucleus"),
    "nmr_p_pulprog": ("Pulsprogramm", "Pulse program"),
    "nmr_p_solvent": ("Lösungsmittel", "Solvent"),
    "nmr_p_probe": ("Probenkopf", "Probe"),
    "nmr_text": ('NMR-Zeile (MNova-Multiplettbericht)', 'NMR Line (MNova Multiplet Report)'),
    "nmr_text_hint": ("Alle Kerne in dieses eine Feld, je Kern eine Zeile (¹H, darunter ¹³C …): in MNova „Multiplets → "
                      "Copy“ bzw. „Peaks → Copy“ (Journal-Format) und einfügen, für ¹³C & Co. auch „Zeile aus "
                      "Peaklabels“. Zuordnungen in der Tabelle ergänzen: *kursiv*, _{tief}, ^{hoch}.",
                      "All nuclei go into this one field, one line per nucleus (¹H, then ¹³C …): in MNova use "
                      "“Multiplets → Copy” or “Peaks → Copy” (journal format) and paste, for ¹³C etc. also “Line from "
                      "peak labels”. Add assignments in the table: *italic*, _{sub}, ^{sup}."),
    "nmr_text_short": ("MNova-Bericht einfügen (Multiplets → Copy), je Kern eine Zeile. Zuordnungen in der Tabelle.",
                       "Paste the MNova report (Multiplets → Copy), one line per nucleus. Assignments go into the table."),
    "syn_join_lines": ("Zeilen verbinden", "Join lines"),
    "syn_join_lines_tip": ("Feste Zeilenenden entfernen (Text aus einer PDF): einzelne Umbrüche werden Leerzeichen, "
                           "Leerzeilen bleiben Absätze",
                           "Remove hard line ends (text from a PDF): single breaks become spaces, blank lines stay "
                           "paragraphs"),
    "nmr_nuc_short": ("Kern", "Nuc."),
    "nmr_mult": ("Mult.", "Mult."),
    "nmr_assign": ("Zuordnung", "Assignment"),
    "nmr_assign_tip": ("Zuordnung je Signal, z. B. ImPy-H oder ImPy-*C*_{q}", "Assignment per signal, e.g. ImPy-H or "
                                                                              "ImPy-*C*_{q}"),
    "nmr_label_no": ("Nummer", "Number"),
    "nmr_label_no_long": ("Nummer der Verbindung fett unter der Struktur im Spektrum (ACS, Angew.: Strukturbild und "
                          "Verbindungsnummer auf jedem Spektrum)", "Compound number in bold below the structure in the "
                          "spectrum (ACS, Angew.: structure and compound number on every spectrum)"),
    "nmr_label_info": ("Messangaben", "Conditions"),
    "nmr_label_info_long": ("Kern, Frequenz und Lösungsmittel unter der Struktur im Spektrum",
                            "Nucleus, frequency and solvent below the structure in the spectrum"),
    "nmr_range": ("Bereich [ppm]", "Range [ppm]"),
    "nmr_range_tip": ("Bereich der Achse. MNova-Bild: üblich sind mindestens −1…10 ppm (¹H) und 0…200 ppm (¹³C; Angew. "
                      "−10…200); eigenes Spektrum: Bereich der SI-Abbildung. ⚠ = die Beschriftung reicht nicht bis 0 bzw. "
                      "10/200 oder ein Signal der SI-Zeile liegt außerhalb. Nur ein Hinweis.",
                      "Range of the axis. MNova image: usual are at least −1…10 ppm (¹H) and 0…200 ppm (¹³C; Angew. "
                      "−10…200); own spectrum: range of the SI figure. ⚠ = the labels do not reach 0 or 10/200, or a signal "
                      "of the SI line lies outside. A note only."),
    "nmr_count_tip": ("Vergleich der NMR-Zeilen mit der Summenformel der Verbindung. ¹H: Summe der H-Zahlen; andere "
                      "Kerne: Zahl der Signale gegen die Atome des Elements. Nur ein Hinweis.",
                      "Comparison of the NMR lines with the molecular formula of the compound. ¹H: sum of the H "
                      "counts; other nuclei: number of signals against the atoms of the element. A note only."),
    "nmr_count_noformula": ("Kernzahl nicht geprüft: die Verbindung hat noch keine Summenformel (Tab Verbindung).",
                            "Nucleus count not checked: the compound has no molecular formula yet (Compound tab)."),
    "nmr_count_found": ("NMR-Zeile", "NMR line"),
    "nmr_count_formula": ("Summenformel", "Formula"),
    "nmr_count_note": ("Hinweis", "Note"),
    "nmr_count_signals": ("{n} Signale", "{n} signals"),
    "nmr_count_ok": ("Passt", "Matches"),
    "nmr_count_less_h": ("Austauschbare H?", "Exchangeable H?"),
    "nmr_count_open": ("{n} Vorschläge offen", "{n} suggestions open"),
    "nmr_count_more_h": ("Zu viele H", "Too many H"),
    "nmr_count_no_nh": ("{k} ohne H-Zahl", "{k} without H count"),
    "nmr_count_none": ("Kein {el} in der Formel", "No {el} in the formula"),
    "nmr_count_more": ("Mehr Signale als {el}", "More signals than {el}"),
    "nmr_count_fewer": ("Symmetrie möglich", "Symmetry possible"),
    # ¹³C-Signale und freie ¹H-Peaks gegen Restsignale und Verunreinigungen (Fulmer 2010, core/nmr_impurities.py);
    # Stoffnamen fulmer_<Name>
    "nmr_imp_chip": ("Verunreinigungen", "Impurities"),
    "nmr_imp_chip_long": ("¹³C-Signale und freie ¹H-Peaks mit den Restsignalen des Lösungsmittels und häufigen "
                          "Verunreinigungen in diesem Lösungsmittel vergleichen (Fulmer et al., Organometallics 2010, 29, "
                          "2176)",
                          "Compare the ¹³C signals and free ¹H peaks with the residual solvent signals and common "
                          "impurities in this solvent (Fulmer et al., Organometallics 2010, 29, 2176)"),
    "nmr_imp_tip": ("¹³C-Signale, die bis auf 0.02 ppm (plus die halbe letzte angegebene Stelle) einem Restsignal des "
                    "Lösungsmittels oder einer Verunreinigung in diesem Lösungsmittel entsprechen (Fulmer et al., "
                    "Organometallics 2010, 29, 2176). Ein Stoff zählt erst, wenn alle seine C mit H passen. ¹H: nur "
                    "Peaks außerhalb der Multipletts der Zeile; ein Stoff zählt, wenn jede seiner Gruppen einen solchen "
                    "Peak trifft, Stoffe mit einem Signal sind nur „möglich“ (grau). Nur ein Hinweis: nichts wird "
                    "geändert oder aus der SI entfernt. Unbekanntes Lösungsmittel: keine Prüfung.",
                    "¹³C signals within 0.02 ppm (plus half the last given digit) of a residual solvent signal or an "
                    "impurity in this solvent (Fulmer et al., Organometallics 2010, 29, 2176). A substance counts only "
                    "when all its C bearing H match. ¹H: only peaks outside the multiplets of the line; a substance "
                    "counts when each of its groups matches such a peak, substances with one signal are only "
                    "\"possible\" (grey). A note only: nothing is changed or removed from the SI. Unknown solvent: no "
                    "check."),
    "nmr_imp_lit": ("Fulmer 2010 [ppm]", "Fulmer 2010 [ppm]"),
    "nmr_imp_match": ("Passt zu", "Matches"),
    "nmr_imp_solvent": ("Restsignal des Lösungsmittels", "residual solvent signal"),
    "nmr_imp_possible": ("{name} (möglich)", "{name} (possible)"),
    "nmr_imp_1h_nopeaks": ("¹H: kein Abgleich ohne Peakliste (MNova-Export mit Peakbericht).",
                           "¹H: no comparison without a peak list (MNova export with peak report)."),
    "nmr_imp_1h_nofreq": ("¹H: kein Abgleich ohne Frequenz in der Zeile.",
                          "¹H: no comparison without a frequency in the line."),
    "nmr_imp_offset": ("¹³C: Abgleich mit um {d} ppm versetzter Referenz: Lösungsmittelsignal im Spektrum bei {v} ppm "
                       "beschriftet, Fulmer 2010: {r} ppm.",
                       "¹³C: compared with the reference shifted by {d} ppm: solvent signal labelled at {v} ppm in the "
                       "spectrum, Fulmer 2010: {r} ppm."),
    "nmr_imp_offset_bad": ("¹³C: kein Abgleich: Lösungsmittelsignal im Spektrum bei {v} ppm beschriftet, Fulmer 2010: {r} ppm "
                           "(mehr als {m} ppm daneben).",
                           "¹³C: no comparison: solvent signal labelled at {v} ppm in the spectrum, Fulmer 2010: {r} ppm "
                           "(more than {m} ppm apart)."),
    "fulmer_acetic acid": ("Essigsäure", "acetic acid"),
    "fulmer_water": ("Wasser", "water"),
    "fulmer_hydrogen": ("Wasserstoff", "hydrogen"),
    "fulmer_acetone": ("Aceton", "acetone"),
    "fulmer_acetonitrile": ("Acetonitril", "acetonitrile"),
    "fulmer_benzene": ("Benzol", "benzene"),
    "fulmer_tert-butyl alcohol": ("tert-Butanol", "tert-butyl alcohol"),
    "fulmer_carbon dioxide": ("Kohlenstoffdioxid", "carbon dioxide"),
    "fulmer_carbon disulfide": ("Schwefelkohlenstoff", "carbon disulfide"),
    "fulmer_carbon tetrachloride": ("Tetrachlormethan", "carbon tetrachloride"),
    "fulmer_chloroform": ("Chloroform", "chloroform"),
    "fulmer_18-crown-6": ("18-Krone-6", "18-crown-6"),
    "fulmer_cyclohexane": ("Cyclohexan", "cyclohexane"),
    "fulmer_1,2-dichloroethane": ("1,2-Dichlorethan", "1,2-dichloroethane"),
    "fulmer_dichloromethane": ("Dichlormethan", "dichloromethane"),
    "fulmer_diethyl ether": ("Diethylether", "diethyl ether"),
    "fulmer_diglyme": ("Diglyme", "diglyme"),
    "fulmer_dimethylformamide": ("Dimethylformamid", "dimethylformamide"),
    "fulmer_1,4-dioxane": ("1,4-Dioxan", "1,4-dioxane"),
    "fulmer_DME": ("DME", "DME"),
    "fulmer_ethane": ("Ethan", "ethane"),
    "fulmer_ethanol": ("Ethanol", "ethanol"),
    "fulmer_ethyl acetate": ("Ethylacetat", "ethyl acetate"),
    "fulmer_ethylene": ("Ethylen", "ethylene"),
    "fulmer_ethylene glycol": ("Ethylenglycol", "ethylene glycol"),
    "fulmer_H grease": ("Schlifffett (Apiezon H)", "Apiezon H grease"),
    "fulmer_hexamethylbenzene": ("Hexamethylbenzol", "hexamethylbenzene"),
    "fulmer_n-hexane": ("n-Hexan", "n-hexane"),
    "fulmer_HMDSO": ("HMDSO", "HMDSO"),
    "fulmer_HMPA": ("HMPA", "HMPA"),
    "fulmer_imidazole": ("Imidazol", "imidazole"),
    "fulmer_methane": ("Methan", "methane"),
    "fulmer_methanol": ("Methanol", "methanol"),
    "fulmer_nitromethane": ("Nitromethan", "nitromethane"),
    "fulmer_n-pentane": ("n-Pentan", "n-pentane"),
    "fulmer_propane": ("Propan", "propane"),
    "fulmer_2-propanol": ("2-Propanol", "2-propanol"),
    "fulmer_propylene": ("Propen", "propylene"),
    "fulmer_pyridine": ("Pyridin", "pyridine"),
    "fulmer_pyrrole": ("Pyrrol", "pyrrole"),
    "fulmer_pyrrolidine": ("Pyrrolidin", "pyrrolidine"),
    "fulmer_silicone grease": ("Silikonfett", "silicone grease"),
    "fulmer_tetrahydrofuran": ("Tetrahydrofuran", "tetrahydrofuran"),
    "fulmer_toluene": ("Toluol", "toluene"),
    "fulmer_triethylamine": ("Triethylamin", "triethylamine"),
    "nmr_text_empty": ("Noch kein MNova-Text.", "No MNova text yet."),
    "nmr_copy": ("NMR-Zeile kopieren", "Copy NMR line"),
    "nmr_struct": ("Struktur", "Structure"),
    "nmr_struct_on": ("Einsetzen", "Insert"),
    "nmr_struct_tip": ("Struktur als Vektorgrafik ins Spektrum setzen (ersetzt den Schritt in Inkscape). „Automatisch“ "
                       "sucht die freie Stelle möglichst weit oben links, ohne Signale, Labels oder Integrale zu "
                       "verdecken; in der Vorschau lässt sie sich mit der Maus verschieben, das Mausrad über der Struktur ändert die Größe (% der Bildbreite).",
                       "Insert the structure as vector graphics into the spectrum (replaces the Inkscape step). "
                       "“Automatic” finds the free space nearest the top left without covering signals, labels or "
                       "integrals; it can be dragged in the preview; the mouse wheel over the structure changes its size (% of the figure width)."),
    "nmr_pos_auto": ("Automatisch (frei)", "Auto (free space)"),
    "nmr_pos_manual": ("Von Hand (gezogen)", "By hand (dragged)"),
    "nmr_pos_tl": ("Oben links", "Top left"),
    "nmr_pos_tc": ("Oben Mitte", "Top centre"),
    "nmr_pos_tr": ("Oben rechts", "Top right"),
    "nmr_struct_pick": ("Andere Struktur …", "Other structure …"),
    "nmr_struct_pick_tip": ("Sonst gilt die Struktur der Verbindung (Werkzeugleiste „Verbindung“)",
                            "Otherwise the structure of the compound is used (toolbar “Compound”)"),
    "nmr_struct_flt": ("Struktur", "Structure"),
    "nmr_struct_from": ("Struktur: {f}", "Structure: {f}"),
    "nmr_select_first": ("Erst ein Spektrum laden bzw. in der Liste wählen.", "Load or select a spectrum first."),
    "nmr_struct_none": ("Keine Struktur (unter „Verbindung“ oder hier wählen).",
                        "No structure (choose under “Compound” or here)."),
    "nmr_word": ("Word speichern", "Save Word"),
    "nmr_word_tip": ("Alle Spektren mit Bildunterschrift, zwei je Seite (SI/<Name>_NMR.docx)",
                     "All spectra with captions, two per page (SI/<name>_NMR.docx)"),

    # ---- DFT (xyz) ---------------------------------------------------------
    "tab_dft": ("DFT", "DFT"),
    "tab_other": ("Weitere", "Other"),
    "guide_other_title": ("Weitere: Abbildungen aus anderen Programmen unverändert in die SI",
                          "Other: figures from other programs into the SI unchanged"),
    "guide_other_files": ("Dateien: PDF, SVG oder PNG (z. B. aus Origin, MNova, ChemDraw, Gerätesoftware)",
                          "Files: PDF, SVG or PNG (e.g. from Origin, MNova, ChemDraw, instrument software)"),
    "guide_other_steps": ("Abbildung hinzufügen\nUnterschrift eintragen\nKapitel wählen: ein vorhandenes SI-Kapitel oder eine "
                          "eigene Überschrift (Gesamt-SI: eigenes Kapitel am Ende)\nSI (Word): zwei Abbildungen je Seite wie alle "
                          "anderen",
                          "Add a figure\nEnter the caption\nChoose the chapter: an existing SI chapter or a heading of your own "
                          "(full SI: own chapter at the end)\nSI (Word): two figures per page like all others"),
    "other_group": ("Abbildungen", "Figures"),
    "cv_couple_add": ("Paar", "Pair"),
    "other_add": ("Abbildung hinzufügen …", "Add figure …"),
    "other_details": ('Gewählte Abbildung', 'Selected Figure'),
    "other_cap": ("Unterschrift", "Caption"),
    "other_cap_ph": ("Z. B. DSC trace of 3b (10 K min-1).", "E.g. DSC trace of 3b (10 K min-1)."),
    "other_cap_tip": ("Englisch wie die übrigen Unterschriften; „Figure Sn:“ setzt der Export davor.",
                      "English like the other captions; the export adds “Figure Sn:”."),
    "other_cap_empty": ("Noch keine Bildunterschrift: links unter „Unterschrift“ eintragen.",
                        "No caption yet: enter it on the left under “Caption”."),
    "other_chapter": ("Kapitel", "Chapter"),
    "other_new_heading": ("Neue Überschrift …", "New heading …"),
    "other_heading": ("Überschrift", "Heading"),
    "other_heading_ph": ("Z. B. Thermal Analysis", "E.g. Thermal Analysis"),
    "other_flt": ("Abbildungen", "Figures"),
    "other_bad_ext": ("{name}: nur PDF, SVG oder PNG", "{name}: PDF, SVG or PNG only"),
    "act_quick": ("Schnellauswertung", "Quick evaluation"),
    "act_quick_tip": ("Neue Verbindung „Auswertung <Datum>“ im internen Projekt „Einzelauswertungen“ – ohne Projekt zu "
                      "wählen; Exporte fragen nach dem Zielordner, später in ein echtes Projekt verschieben.",
                      "New compound “Evaluation <date>” in the internal project “Quick evaluations” – no project to "
                      "choose; exports ask for the target folder, move it into a real project later."),
    "quick_title": ("Einzelauswertungen", "Quick evaluations"),
    "quick_name": ("Auswertung {date}", "Evaluation {date}"),
    "quick_export": ("Exportieren nach …", "Export to …"),
    "welcome_compounds": ("Verbindungen", "Compounds"),
    "welcome_f_all": ("Alle Verbindungen", "All compounds"),
    "side_library": ("Bibliothek", "Library"),
    "welcome_count": ("{n} Verbindungen, zuletzt geänderte zuerst", "{n} compounds, most recently changed first"),
    "welcome_search_ph": ("Name, Laborkürzel, Summenformel, Notiz …", "Name, lab code, formula, note …"),
    "welcome_gallery": ("Galerie", "Gallery"),
    "welcome_list": ("Liste", "List"),
    "welcome_new": ("Neu", "New"),
    "welcome_add_hint": ("Oder Ordner und Messdateien hierher\u00a0ziehen", "Or drop folders and data files\u00a0here"),
    "welcome_complete": ("Vollständig", "Complete"),
    "welcome_missing": ("Fehlt: {items}", "Missing: {items}"),
    "welcome_no_analytics": ("Noch keine Analytik", "No analytics yet"),
    "welcome_theme_light": ("Helle Ansicht", "Light view"),
    "welcome_theme_dark": ("Dunkle Ansicht", "Dark view"),
    "side_quickstart": ("Schnellstart", "Quick start"),
    "side_demo": ("Beispielprojekt", "Example project"),
    "col_compound": ("Verbindung", "Compound"),
    "col_more": ("Weitere Analytik", "Other analytics"),
    "col_changed": ("Geändert", "Changed"),
    "tag_known": ("bekannt", "known"),
    "check_have": ("{item}: vorhanden", "{item}: present"),
    "check_none": ("{item}: keine Daten", "{item}: no data"),
    "nav_more_tip": ("Weitere Tabs (auch mit dem Mausrad über der Leiste)", "More tabs (also with the mouse wheel over the bar)"),
    "check_missing": ("{item}: fehlt", "{item}: missing"),
    "check_na": ("{item}: nicht nötig (bekannte Verbindung)", "{item}: not needed (known compound)"),
    "rp_changed": ("Geändert {t}", "Changed {t}"),
    "rp_rename_q": ("Neuer Name des Pfads:", "New name of the path:"),
    "pub_progress": ("{k} von {n} Verbindungen vollständig", "{k} of {n} compounds complete"),
    "welcome_f_recent": ("Zuletzt", "Recent"),
    "welcome_f_incomplete": ("Unvollständig", "Incomplete"),
    "welcome_f_sample": ("Substanz übrig", "Sample left"),
    "welcome_more": ("Mehr", "More"),
    "tabs_more": ("Mehr ▾", "More ▾"),
    "tabs_more_tip": ("Weitere Seiten (die Reiterzeile ist zu schmal für alle)", "More pages (the tab row is too narrow for all)"),
    "pub_tile_sub": ("{n} Verbindungen · {k} vollständig", "{n} compounds · {k} complete"),
    "pub_tile_progress": ("{k} von {n} Verbindungen vollständig laut Checkliste (¹H, ¹³C, 2D, HRMS, IR, m.p.)",
                          "{k} of {n} compounds complete according to the checklist (¹H, ¹³C, 2D, HRMS, IR, m.p.)"),
    "mnova_store": ("MNova-Dokument …", "MNova document …"),
    "mnova_open": ("In MNova öffnen", "Open in MNova"),
    "mnova_open_tip": ("Gewähltes MNova-Dokument (sonst Auswahl) mit dem Standardprogramm öffnen",
                       "Open the selected MNova document (otherwise a choice) with the default program"),
    "mnova_none": ("Kein MNova-Dokument abgelegt.", "No MNova document stored."),
    "mnova_pick": ("Dokument:", "Document:"),
    "mnova_noapp": ("{name} konnte nicht geöffnet werden – ist MNova installiert und für .mnova zuständig?",
                    "{name} could not be opened – is MNova installed and associated with .mnova?"),
    "dft_structures": ('Geometrien und Rechnungen', 'Geometries and Calculations'),
    "dft_add": ("xyz/.out/.log hinzufügen …", "Add xyz/.out/.log …"),
    "dft_flt": ("xyz, ORCA/Gaussian-Ausgabe, Cube, Molden", "xyz, ORCA/Gaussian output, cube, Molden"),
    "dft_orbitals": ("Orbitale", "Orbitals"),
    "dft_orb_add": ("Cube/Molden …", "Cube/Molden …"),
    "dft_orb_add_tip": ("Orbitale als Gaussian-Cube (ORCA: orca_plot, Gaussian: cubegen) oder Molden-Datei (ORCA: "
                        "orca_2mkl name -molden; alle MOs, HOMO und LUMO werden angelegt). Passt die Datei zur gewählten "
                        "Geometrie, wird sie dort angehängt, sonst entsteht eine neue Geometrie.",
                        "Orbitals as Gaussian cube (ORCA: orca_plot, Gaussian: cubegen) or Molden file (ORCA: "
                        "orca_2mkl name -molden; all MOs, HOMO and LUMO are added). If the file matches the selected "
                        "geometry it is attached there, otherwise a new geometry is created."),
    "dft_orb_flt": ("Gaussian-Cube, Molden", "Gaussian cube, Molden"),
    "dft_orb_mo": ("Aus Molden", "From Molden"),
    "dft_orb_mo_tip": ("Alle MOs der Molden-Datei; „+“ legt das gewählte als weiteres Orbital an.",
                       "All MOs of the Molden file; “+” adds the selected one as a further orbital."),
    "dft_orb_mo_add": ("+", "+"),
    "dft_orb_molden_conv": ("Konvention der Basisfunktionen nicht erkannt (Orbitale nicht orthonormal, Abweichung {err}) "
                            "– Datei abgelehnt.",
                            "Basis-function convention not recognized (orbitals not orthonormal, deviation {err}) – "
                            "file rejected."),
    "dft_orb_molden_ok": ("Molden: Konvention {v}, CᵀSC = 1 bis auf {err}", "Molden: convention {v}, CᵀSC = 1 within {err}"),
    "dft_orb_select": ("Orbital", "Orbital"),
    "dft_orb_select_tip": ("Gezeigtes Orbital. HOMO/LUMO und Energie aus der ORCA/Gaussian-Ausgabe der Geometrie, "
                           "MO-Nummer aus dem Cube bzw. dem Dateinamen (ORCA: name.mo21a.cube).",
                           "Orbital shown. HOMO/LUMO and energy from the ORCA/Gaussian output of the geometry, MO "
                           "number from the cube or the file name (ORCA: name.mo21a.cube)."),
    "dft_orb_none": ("– Keins –", "– None –"),
    "dft_profile": ('Energieprofil', 'Energy Profile'),
    "dft_prof_mode": ("Darstellung", "Display"),
    "dft_prof_mode_levels": ("Stufen (Opt/Freq)", "Levels (opt/freq)"),
    "dft_prof_mode_irc": ("IRC", "IRC"),
    "dft_prof_y": ("Größe", "Quantity"),
    "dft_prof_y_tip": ("ΔG (Standard), ΔH oder ΔE in kcal mol⁻¹ relativ zur ersten Spezies; mit Einzelpunkt "
                       "G = E(SP) + (G − E_el) der Opt/Freq-Rechnung.",
                       "ΔG (default), ΔH or ΔE in kcal mol⁻¹ relative to the first species; with a single point "
                       "G = E(SP) + (G − E_el) of the opt/freq calculation."),
    "dft_prof_species": ("Rechnung", "Calculation"),
    "dft_prof_label": ("Label", "Label"),
    "dft_prof_step": ("Schritt", "Step"),
    "dft_prof_paths": ("Pfad(e)", "Path(s)"),
    "dft_prof_sp": ("Einzelpunkt", "Single point"),
    "dft_prof_structure_add": ("Hinzufügen …", "Add …"),
    "dft_prof_structure_set": ("Struktur …", "Structure …"),
    "dft_prof_draw_structure": ("Struktur zeichnen / bearbeiten", "Draw / edit structure"),
    "dft_prof_structure_tip": ("Eine 2D-Struktur über diesem Plateau anzeigen – zeichnen oder Datei wählen.",
                               "Show a 2D structure above this plateau – draw it or choose a file."),
    "dft_prof_structure_unreadable": ("Struktur kann nicht gelesen werden", "Cannot read structure"),
    "dft_prof_tbl_tip": ("Haken = im Profil; Label frei (Hochzahlen wie „TS6¹“), Schritt = x-Position, Pfade durch "
                         "Komma getrennt (gemeinsame Spezies: „A,B“). Einzelpunkte werden über gleiche "
                         "Atome/Koordinaten (± 0.02 Å) zugeordnet, nie über Dateinamen.",
                         "Tick = in the profile; free label (superscripts like “TS6¹”), step = x position, paths "
                         "separated by commas (shared species: “A,B”). Single points are matched by identical "
                         "atoms/coordinates (± 0.02 Å), never by file name."),
    "dft_prof_sp_add": ("Einzelpunkte hinzufügen …", "Add single points …"),
    "dft_prof_sp_rm": ("Einzelpunkte entfernen", "Remove single points"),
    "dft_prof_no_sp": ("Ohne Einzelpunkt, nicht im Profil (nie gemischt): {names}",
                       "No single point, left out of the profile (never mixed): {names}"),
    "dft_prof_no_kind": ("{name}: {kind} fehlt (Frequenzrechnung nötig), nicht im Profil",
                         "{name}: {kind} missing (frequency calculation needed), left out"),
    "dft_prof_mr_el": ("{name}: Multireferenz ohne Frequenzrechnung – nur die elektronische Energie statt {kind} "
                       "(steht in der Unterschrift)",
                       "{name}: multireference without frequency calculation – electronic energy instead of {kind} "
                       "(stated in the caption)"),
    "dft_prof_mixed": ("Spezies mit verschiedenen Methoden – Unterschrift nennt nur die erste.",
                       "Species with different methods – the caption names only the first."),
    "dft_prof_sp_solv": ("Einzelpunkt ohne Lösungsmittel, Geometrie mit SMD/CPCM: Solvatation ist in E(SP) nicht "
                         "enthalten (keine Korrektur).",
                         "Single point without solvent, geometry with SMD/CPCM: solvation is not included in E(SP) "
                         "(no correction applied)."),
    "dft_prof_colors": ("Pfadfarben", "Path colours"),
    "dft_prof_empty": ("Rechnungen (Opt/Freq) laden – Energieprofil erscheint hier",
                       "Load calculations (opt/freq) – the energy profile appears here"),
    "dft_irc_tip": ("ORCA-IRC (.out mit „IRC PATH SUMMARY“ und <Name>_IRC_Full_trj.xyz daneben), mehrere "
                    "nacheinander auf einer Achse (Reihenfolge mit ↑). Nur ΔE (entlang der IRC gibt es kein G).",
                    "ORCA IRC (.out with “IRC PATH SUMMARY” and <name>_IRC_Full_trj.xyz next to it), several in a "
                    "row on one axis (order with ↑). ΔE only (there is no G along an IRC)."),
    "dft_irc_add": ("IRC hinzufügen …", "Add IRC …"),
    "dft_irc_up": ("↑", "↑"),
    "dft_irc_x": ("x-Achse", "x axis"),
    "dft_irc_rc": ("Reaktionskoordinate [Å]", "Reaction coordinate [Å]"),
    "dft_irc_ref": ("Bezug", "Reference"),
    "dft_irc_ref_first": ("Erster Punkt", "First point"),
    "dft_irc_ref_ts": ("Übergangszustand", "Transition state"),
    "dft_irc_none": ("keine IRC-Tabelle („IRC PATH SUMMARY“ mit TS-Zeile) gefunden",
                     "no IRC table (“IRC PATH SUMMARY” with TS row) found"),
    "dft_irc_trj": ("Trajektorie {name} fehlt (gehört neben die .out)", "trajectory {name} missing (belongs next to the .out)"),
    "dft_irc_trj_bad": ("Trajektorie hat {n} Bilder, die IRC-Tabelle {m} Schritte",
                        "trajectory has {n} frames, the IRC table {m} steps"),
    "dft_irc_method": ("IRCs mit verschiedenen Methoden gehören nicht auf eine Achse",
                       "IRCs with different methods do not belong on one axis"),
    "dft_irc_no_col": ("{name}: keine Spalte „{col}“, nicht im Bild", "{name}: no column “{col}”, left out"),
    "dft_nics": ("NICS", "NICS"),
    "dft_nics_start": ("Gaussian-NMR-Ausgaben mit Bq-Atomen hinzufügen (Schritt Daten, Karte NICS-Rechnungen)",
                       "Add Gaussian NMR outputs with Bq atoms (Data step, card NICS Calculations)"),
    "dft_nics_files": ("Dateien", "Files"),
    "mr_card": ("Multireferenz", "Multireference"),
    "mr_result": ("Ergebnis", "Result"),
    # Eintrag der Listen Singulett/Triplett: Wurzel (root) wie von ORCA gezählt, Energie wie gedruckt (echtes Minus)
    "mr_root_item": ("Root {root}{irrep} · {energy} Eh", "Root {root}{irrep} · {energy} Eh"),
    "mr_singlet": ("Singulett", "Singlet"),
    "mr_triplet": ("Triplett", "Triplet"),
    "mr_sign": ("Vorzeichen", "Sign"),
    "dft_nics3d": ("3D-NICS", "3D NICS"),
    "dft_nics_card": ("NICS-Rechnungen", "NICS Calculations"),
    "dft_nics_display": ("NICS-Abbildung", "NICS Figure"),
    "dft_nics_kind": ("Art", "Kind"),
    "dft_nics_add_short": ("Hinzufügen …", "Add …"),
    "dft_nics_points": ("Einzelpunkte", "Single points"),
    "dft_nics_scan": ("Scan", "Scan"),
    "dft_nics_show": ("Abbildung", "Figure"),
    "dft_nics3d_iso": ("Isoflächen", "Isosurfaces"),
    "dft_nics3d_pos_tip": ("Isofläche bei positivem NICS (entschirmt)", "Isosurface at positive NICS (deshielded)"),
    "dft_nics3d_neg_tip": ("Isofläche bei negativem NICS (abgeschirmt)", "Isosurface at negative NICS (shielded)"),
    "dft_nics3d_colors": ("Farben", "Colours"),
    "dft_nics3d_alpha": ("Deckkraft", "Opacity"),
    "dft_nics3d_geom": ("Die Teilrechnungen des 3D-NICS-Gitters haben verschiedene Geometrien.",
                        "The partial calculations of the 3D NICS grid have different geometries."),
    "dft_nics3d_irregular": ("3D-NICS: {n} Gitterpunkte geladen, ein vollständiges Gitter hätte {full}. Fehlen "
                             "Teilrechnungen?", "3D NICS: {n} grid points loaded, a complete grid would have {full}. "
                             "Are partial calculations missing?"),
    "dft_nics_add": ("Gaussian-NMR (Bq) hinzufügen …", "Add Gaussian NMR (Bq) …"),
    "dft_nics_geom": ("Geometrie-Methode", "Geometry method"),
    "dft_nics_geom_ph": ("Z. B. r2SCAN-3c(SMD:THF)", "E.g. r2SCAN-3c(SMD:THF)"),
    "dft_nics_geom_tip": ("Für die Unterschrift „<NMR-Methode>//<Geometrie>“ (die NMR-Ausgabe kennt die Methode der "
                          "Optimierung nicht).",
                          "For the caption “<NMR method>//<geometry>” (the NMR output does not know the "
                          "optimization method)."),
    "dft_nics_file": ("Datei", "File"),
    "dft_nics_pair": ("Mittel ober-/unterhalb", "Average above/below"),
    "dft_nics_empty": ("NICS-Scan (Gaussian-NMR mit ≥ 10 Bq) erscheint hier; Einzelpunkte in der Tabelle",
                       "NICS scan (Gaussian NMR with ≥ 10 Bq) appears here; single points in the table"),
    "dft_nics_none": ("keine Abschirmungen von Geisteratomen (Bq) gefunden", "no ghost-atom (Bq) shieldings found"),
    "acid": ("ACID", "ACID"),
    "acid_card": ("ACID-Rechnung", "ACID Calculation"),
    "acid_display": ("ACID-Abbildung", "ACID Figure"),
    "acid_add": ("AICD-Ausgabe (Isoober.inc), ACID-Cube oder Gaussian-Ausgabe (CSGT) hinzufügen …",
                 "Add AICD output (Isoober.inc), ACID cube or Gaussian output (CSGT) …"),
    "acid_filter": ("AICD-Ausgabe, ACID-Cube, Gaussian-Ausgabe", "AICD output, ACID cube, Gaussian output"),
    "acid_start": ("Isoober.inc aus dem Ordner <Name>.d des AICD-Laufs hinzufügen (Molekuel.inc kommt mit) oder "
                   "einen Cube mit dem ACID-Skalarfeld (Schritt Daten, Karte ACID-Rechnung), dazu die "
                   "Gaussian-Ausgabe der CSGT-Rechnung für die Unterschrift",
                   "Add Isoober.inc from the <name>.d folder of the AICD run (Molekuel.inc comes along) or a cube "
                   "with the ACID scalar field (Data step, card ACID Calculation), plus the Gaussian output of the "
                   "CSGT calculation for the caption"),
    "acid_arrows_card": ("ACID-Pfeile", "ACID Arrows"),
    "acid_arrows": ("Pfeile", "Arrows"),
    "acid_arrow_size_tip": ("Stromdichtepfeile aus der AICD-Datei, um ihren Anfang skaliert (1 × = wie von AICD "
                            "geschrieben)", "Current density arrows from the AICD file, scaled about their start "
                            "(1 × = as written by AICD)"),
    "acid_density": ("Pfeildichte", "Arrow density"),
    "acid_density_tip": ("Anteil der Pfeile aus der Datei, die gezeigt werden (ausgedünnt, nichts neu berechnet)",
                         "Share of the arrows from the file that are shown (thinned out, nothing recomputed)"),
    "acid_arrow_colors": ("Farben", "Colours"),
    "acid_shaft_tip": ("Schaft der Pfeile", "Arrow shafts"),
    "acid_head_tip": ("Spitze der Pfeile", "Arrow heads"),
    "acid_field": ("Magnetfeld B", "Magnetic field B"),
    "acid_field_tip": ("Richtung des Magnetfelds aus der AICD-Datei (Symbol unten links). Ablesen: zeigt B zum "
                       "Betrachter, läuft ein diatroper Ringstrom im Uhrzeigersinn, ein paratroper gegen ihn.",
                       "Direction of the magnetic field from the AICD file (symbol at the bottom left). Reading: with "
                       "B pointing towards the viewer, a diatropic ring current runs clockwise, a paratropic one "
                       "anticlockwise."),
    "acid_kind_inc": ("AICD-Fläche und Pfeile", "AICD surface and arrows"),
    "acid_kind_mol": ("AICD-Molekül", "AICD molecule"),
    "acid_bad_inc": ("keine AICD-Isoober.inc im bekannten Aufbau (mesh aus smooth_triangle, Pfeile als Zylinder + "
                     "Kegel)", "not an AICD Isoober.inc in the known layout (mesh of smooth_triangle, arrows as "
                     "cylinder + cone)"),
    "acid_bad_mol": ("keine Molekuel.inc von PovChem (Atome „object { Atom_… translate <x, y, z> }“)",
                     "not a PovChem Molekuel.inc (atoms “object { Atom_… translate <x, y, z> }”)"),
    "acid_no_mol": ("Molekuel.inc aus demselben AICD-Ordner fehlt: ohne Atome keine Abbildung",
                    "Molekuel.inc from the same AICD folder is missing: no figure without atoms"),
    "acid_cube_unused": ("Die AICD-Fläche wird gezeigt, der Cube nicht", "The AICD surface is shown, not the cube"),
    "acid_iso_unknown": ("Isowert steht nicht in der AICD-Datei: Unterschrift ohne Isowert",
                         "The isovalue is not in the AICD file: caption without isovalue"),
    "acid_iso_file": ("Isowert {v} (aus der AICD-Datei, liegt in der Fläche fest)",
                      "Isovalue {v} (from the AICD file, fixed in the surface)"),
    "acid_geom_tip": ("Für die Unterschrift „<CSGT-Methode>//<Geometrie>“ (die NMR-Ausgabe kennt die Methode der "
                      "Optimierung nicht).",
                      "For the caption “<CSGT method>//<geometry>” (the NMR output does not know the "
                      "optimization method)."),
    "acid_iso": ("Isowert", "Isovalue"),
    "acid_iso_tip": ("Isofläche bei diesem ACID-Wert (Einheit wie im Cube)",
                     "Isosurface at this ACID value (unit as in the cube)"),
    "acid_color": ("Farbe", "Colour"),
    "acid_kind_cube": ("ACID-Gitter", "ACID grid"),
    "acid_kind_log": ("CSGT-Rechnung", "CSGT calculation"),
    "acid_bad_cube": ("kein ACID-Skalarfeld (ein Datensatz, nie negativ, mit Atomen)",
                      "not an ACID scalar field (one data set, never negative, with atoms)"),
    "acid_bad_log": ("keine Gaussian-Rechnung mit NMR=CSGT und IOp(10/93)",
                     "not a Gaussian calculation with NMR=CSGT and IOp(10/93)"),
    "acid_no_log": ("Gaussian-Ausgabe der CSGT-Rechnung fehlt: Unterschrift ohne Rechenniveau",
                    "Gaussian output of the CSGT calculation missing: caption without level of theory"),
    "acid_atoms_differ": ("Cube hat {n} Atome, die Gaussian-Ausgabe {m}: gehören sie zusammen?",
                          "the cube has {n} atoms, the Gaussian output {m}: do they belong together?"),
    "acid_empty": ("ACID-Abbildung erscheint hier, sobald eine AICD-Ausgabe oder ein ACID-Cube geladen ist",
                   "The ACID figure appears here once an AICD output or an ACID cube is loaded"),
    "dft_orb_iso": ("Schwellentyp", "Threshold type"),
    "dft_orb_iso_frac": ("Dichte", "Density"),
    "dft_orb_iso_abs": ("Absolut", "Absolute"),
    "dft_orb_thr": ("Schwelle", "Threshold"),
    "dft_orb_iso_tip": ("Wie IboView: „Dichte“ = die Fläche umschließt diesen Anteil von |ψ|² (Standard 80 %); "
                        "„Absolut“ = fester Isowert ±ψ in a.u. (Standard 0.01, üblich 0.02–0.05).",
                        "As in IboView: “Density” = the surface encloses this fraction of |ψ|² (default 80%); "
                        "“Absolute” = fixed isovalue ±ψ in a.u. (default 0.01, typically 0.02–0.05)."),
    "dft_orb_alpha": ("Deckkraft", "Opacity"),
    "dft_orb_alpha_tip": ("Deckkraft der Isoflächen (IboView: 0.6); Ränder werden wie in IboView deckender.",
                          "Opacity of the isosurfaces (IboView: 0.6); edges become more opaque as in IboView."),
    "dft_orb_scheme": ("Farben", "Colours"),
    "dft_orb_scheme_hue": ("IboView (Farbton je Orbital)", "IboView (hue per orbital)"),
    "dft_orb_scheme_sat": ("IboView (Sättigung)", "IboView (saturation)"),
    "dft_orb_scheme_opposite": ("IboView (Gegenfarben)", "IboView (opposite colours)"),
    "dft_orb_hint": ("Orbitale als Molden-Datei (ORCA: orca_2mkl name -molden) oder Cube laden (ORCA: orca_plot "
                     "name.gbw -i, Gaussian: cubegen). Gezeigt wird mit Atomen wie in IboView.",
                     "Load orbitals as Molden file (ORCA: orca_2mkl name -molden) or cube (ORCA: orca_plot name.gbw -i, "
                     "Gaussian: cubegen). Shown with atoms as in IboView."),
    "dft_orb_info": ("Isowert ±{iso} a.u.; Gitter {n}, Schritt {h} Å", "Isovalue ±{iso} a.u.; grid {n}, step {h} Å"),
    "dft_orb_norm": ("Achtung: Σψ²·dV = {v} statt 1 – das Gitter enthält nicht das ganze Orbital (oder ψ ist nicht "
                     "normiert); der Anteil der Dichte stimmt dann nicht. Größeres Gitter oder festen Isowert nehmen.",
                     "Caution: Σψ²·dV = {v} instead of 1 – the grid does not contain the whole orbital (or ψ is not "
                     "normalized); the density fraction is then wrong. Use a larger grid or a fixed isovalue."),
    "dft_orb_coarse": ("Grobes Gitter ({h} Å): Fläche kantig. orca_plot: Gitterpunkte erhöhen (z. B. 100).",
                       "Coarse grid ({h} Å): surface looks faceted. orca_plot: increase the grid points (e.g. 100)."),
    "dft_orb_new_entry": ("{f} passt nicht zur gewählten Geometrie – neue Geometrie aus dem Cube angelegt.",
                          "{f} does not match the selected geometry – new geometry created from the cube."),
    "dft_orb_missing": ("Cube fehlt: {f}", "Cube missing: {f}"),
    "dft_orb_style": ("Mit Orbital werden die Atome wie in IboView gezeichnet.",
                      "With an orbital, atoms are drawn as in IboView."),
    "xr_style_iboview": ("IboView", "IboView"),
    "dft_orb_labels": ("Symbole wie IboView", "Symbols as in IboView"),
    "dft_orb_labels_long": ("Elementsymbole wie IboView", "Element symbols as in IboView"),
    "dft_orb_labels_tip": ("Buchstaben auf C und Heteroatomen (nicht H), wie IboView sie standardmäßig zeigt.",
                           "Letters on C and heteroatoms (not H), as IboView shows them by default."),
    "dft_si": ("Rechnung für die SI", "Calculation for the SI"),
    "cluster_title": ("Cluster", "Cluster"),
    "cluster_access": ("Zugang", "Access"),
    "cluster_back": ("‹ Zum Pfad", "‹ Back to path"),
    "cluster_guide": ("Anleitung zur Einrichtung", "Setup guide"),
    "cluster_manual_head": ("Cluster-Anbindung", "Cluster connection"),
    "cluster_notify": ("Fertige Jobs melden", "Report finished jobs"),
    "cluster_notify_tip": ("Mitteilung des Systems, wenn Elucida gerade nicht im Vordergrund ist.",
                           "System notification when Elucida is not in the foreground."),
    "cluster_target": ("Ziel", "Target"),
    "cluster_pick_job": ("Job wählen oder Ordner eintragen", "Pick a job or enter a folder"),
    "cluster_card": ("{n} laufen · {m} fertig", "{n} running · {m} finished"),
    "cluster_card_idle": ("Jobs und Ergebnisse holen", "Jobs and fetching results"),
    "cluster_card_off": ("Keine Verbindung", "Not connected"),
    "cluster_loose": ("Nur als Datei in data/dft: {files}", "Stored in data/dft only: {files}"),
    "cluster_host": ("Host", "Host"),
    "cluster_user": ("Benutzer", "User"),
    "cluster_dir": ("Ordner", "Folder"),
    "cluster_host_ph": ("Login-Knoten des Clusters", "Login node of the cluster"),
    "cluster_user_ph": ("Konto auf dem Cluster", "Account on the cluster"),
    "cluster_dir_ph": ("Ordner auf dem Cluster", "Folder on the cluster"),
    "cluster_col_id": ("Job", "Job"),
    "cluster_col_name": ("Name", "Name"),
    "cluster_col_state": ("Zustand", "State"),
    "cluster_col_time": ("Laufzeit / Ende", "Run time / end"),
    "cluster_col_dir": ("Ordner", "Folder"),
    "cluster_refresh": ("Aktualisieren", "Refresh"),
    "cluster_files": ("Ordner zeigen", "Show folder"),
    "cluster_fetch": ("Ergebnisse holen", "Fetch results"),
    "cluster_bad_login": ("Host und Benutzer eintragen (nur Buchstaben, Ziffern, Punkt, Binde- und Unterstrich).",
                          "Enter host and user (letters, digits, dot, hyphen and underscore only)."),
    "cluster_bad_dir": ("Der Ordner muss ein absoluter Pfad sein.", "The folder must be an absolute path."),
    "cluster_no_ssh": ("Kein ssh-Programm gefunden. Unter Windows: OpenSSH-Client in den optionalen Features aktivieren.",
                       "No ssh program found. On Windows: enable the OpenSSH client in the optional features."),
    "cluster_failed": ("Keine Verbindung: {err}. Prüfen: VPN oder Uni-Netz, SSH-Schlüssel im Agenten, Host einmal im "
                       "Terminal bestätigt.",
                       "No connection: {err}. Check: VPN or university network, SSH key in the agent, host confirmed "
                       "once in a terminal."),
    "cluster_paused": ("Automatische Abfrage angehalten, damit der Server die IP nicht sperrt. Nach dem Beheben: Aktualisieren.",
                       "Automatic checks paused so that the server does not block your IP. After fixing it: Refresh."),
    "cluster_timeout": ("Zeitüberschreitung", "timed out"),
    "cluster_status": ("{n} Jobs laufen oder warten, {m} beendet (letzte 7 Tage).",
                       "{n} jobs running or waiting, {m} finished (last 7 days)."),
    "cluster_ended": ("Fertig: {jobs}", "Finished: {jobs}"),
    "cluster_files_found": ("{n} Dateien. Ziel wählen und „Ergebnisse holen“.", "{n} files. Choose the target and use \"Fetch results\"."),
    "cluster_files_none": ("Keine passenden Dateien in diesem Ordner.", "No matching files in this folder."),
    "cluster_pick": ("Zuerst Dateien anhaken und ein Ziel wählen.", "Tick files and choose a target first."),
    "cluster_fetching": ("Hole {name} …", "Fetching {name} …"),
    "cluster_fetched": ("{n} Dateien nach {target} geholt.", "{n} files fetched to {target}."),
    "cluster_incomplete": ("{name} kam unvollständig an und wurde nicht übernommen.",
                           "{name} arrived incomplete and was not added."),
    "dft_si_hint": ("Für den SI-Block eine ORCA-6- oder Gaussian-Ausgabe (.out/.log) laden; reine xyz-Dateien "
                    "enthalten keine Angaben zur Rechnung.",
                    "Load an ORCA 6 or Gaussian output (.out/.log) for the SI block; plain xyz files contain no "
                    "information about the calculation."),
    "dft_si_with": ("Im SI-Text:", "In the SI text:"),
    "dft_si_zpe": ("ZPE-Spalte", "ZPE column"),
    "dft_method_each": ("Methode je Struktur", "Method per structure"),
    "dft_method_top": ("Methode einmal oben", "Method once at the top"),
    "dft_method_off": ("Ohne Methode", "No method"),
    "dft_method_tip": ("„einmal oben“: Abschnitt „Computational details“ mit jeder verschiedenen Eingabezeile (bei "
                       "mehreren Methoden mit den zugehörigen Strukturen), wie „Sample Input Files“ in einer SI.",
                       "“once at the top”: section “Computational details” with each different input line (with the "
                       "structures concerned if there are several methods), like “Sample Input Files” in an SI."),
    "dft_si_conv": ("Konvergenz", "Convergence"),
    "dft_si_freq": ("Frequenzen", "Frequencies"),
    "dft_partner_used": ("Koordinaten aus der gleichnamigen xyz (volle Stellenzahl, passt zur Endgeometrie).",
                         "Coordinates from the xyz of the same name (full precision, matches the final geometry)."),
    "dft_partner_none": ("Koordinaten aus der Ausgabe (6 Nachkommastellen); die gleichnamige xyz von ORCA daneben "
                         "legen für volle Stellenzahl.",
                         "Coordinates from the output (6 decimals); place ORCA's xyz of the same name next to it for "
                         "full precision."),
    "dft_si_copy": ("SI-Text kopieren", "Copy SI text"),
    "dft_si_copy_tip": ("Block dieser Rechnung formatiert kopieren (in Word einfügen); Tabellen als Tabulator-Text.",
                        "Copy the block of this calculation with formatting (paste into Word); tables as tab text."),
    "dft_si_copied": ("SI-Text in der Zwischenablage.", "SI text copied to the clipboard."),
    "dft_si_word": ("Word speichern …", "Save Word …"),
    "dft_si_word_tip": ("Alle Rechnungen als Word-Datei: Name, Abbildung, Methode, Konvergenz, Frequenzen, Energien, "
                        "Koordinaten (in der aktuellen Nummerierung).",
                        "All calculations as a Word file: name, figure, method, convergence, frequencies, energies, "
                        "coordinates (in the current numbering)."),
    # Pflichtangaben der Zeitschriften (ACS, Org. Lett., Angew.): Energietabelle, Sammel-xyz, Eingabedateien
    "dft_si_tbl": ("Energietabelle", "Energy Table"),
    "dft_si_tbl_none": ("Noch keine Rechnung (ORCA-6- oder Gaussian-Ausgabe) geladen.",
                        "No calculation (ORCA 6 or Gaussian output) loaded yet."),
    "dft_si_tbl_copy_tip": ("Tabelle aller Rechnungen kopieren (Word: Dreilinien-Tabelle; sonst Tabulator-Text).",
                            "Copy the table of all calculations (Word: three-line table; otherwise tab-separated text)."),
    "dft_si_xyz": ("Alle als xyz …", "All as xyz …"),
    "dft_si_xyz_tip": ("Alle Strukturen des Tabs in EINER xyz-Datei (Name und E_el in der Kommentarzeile), wie ACS "
                       "und Org. Lett. sie verlangen. Der Export schreibt sie immer mit (…_structures.xyz).",
                       "All structures of the tab in ONE xyz file (name and E_el in the comment line), as required by "
                       "ACS and Org. Lett. The export always writes it too (…_structures.xyz)."),
    "dft_si_xyz_note": ("Export und Datenpaket enthalten alle {n} Strukturen in einer xyz-Datei.",
                        "Export and data package contain all {n} structures in one xyz file."),
    "dft_si_col_name": ("Struktur", "Structure"),
    "dft_si_col_prog": ("Programm", "Program"),
    "dft_si_col_input": ("Eingabe", "Input"),
    "dft_si_inp_yes": ("Vorhanden", "Present"),
    "dft_si_kpi_input": ("Eingabe", "Input"),
    "dft_si_units": ("Alle Energien in Eₕ.", "All energies in Eₕ."),
    "dft_si_prog": ("Programm: {p}.", "Program: {p}."),
    "dft_si_inp_tip": ("Gesucht wird eine Eingabedatei mit gleichem Namen neben der Ausgabe (.inp, .gjf, .com).",
                       "Looked for: an input file with the same name next to the output (.inp, .gjf, .com)."),
    "dft_si_inp_all": ("Die Eingabedateien aller Rechnungen liegen bei.", "Input files of all calculations are present."),
    "dft_si_inp_missing": ("Rechnungen ohne Eingabedatei: {n}; ACS verlangt sie im Datenpaket.",
                           "Calculations without input file: {n}; ACS requires it in the data package."),
    "dft_w_partly": ("Hinweis: ORCA hat die Optimierung als konvergiert beendet, obwohl nicht alle Kriterien „YES“ "
                     "zeigen (übererfüllter Gradient) – die Tabelle zeigt die Werte unverändert.",
                     "Note: ORCA finished the optimization as converged although not all criteria show “YES” "
                     "(gradient overachieved) – the table shows the values unchanged."),
    "dft_name": ("Name", "Name"),
    "dft_file": ("Datei", "File"),
    "dft_bad_xyz": ("keine xyz-Datei (Zeile {line}: Atomzahl erwartet)",
                    "not an xyz file (line {line}: atom count expected)"),
    "dft_short_xyz": ("xyz unvollständig: {n} Atome angekündigt (Zeile {line}), weniger Zeilen vorhanden",
                      "incomplete xyz: {n} atoms announced (line {line}), fewer lines present"),
    "dft_bad_atom": ("Zeile {line}: erwartet „Element x y z“", "line {line}: expected “element x y z”"),
    "dft_no_atoms": ("keine Atome in der Datei", "no atoms in the file"),
    "dft_frames_differ": ("Bilder der Trajektorie haben unterschiedliche Atome",
                          "trajectory frames contain different atoms"),
    "dft_info": ("{n} Atome, {formula}", "{n} atoms, {formula}"),
    "dft_frames": ("Trajektorie mit {n} Bildern: gezeigt das letzte, gespeichert werden alle in der neuen Reihenfolge.",
                   "Trajectory with {n} frames: the last is shown, all are saved in the new order."),
    "dft_comment": ("Kommentar: {c}", "Comment: {c}"),
    "dft_fragments": ("{n} getrennte Fragmente", "{n} separate fragments"),
    "dft_renumbered": ("Nummerierung geändert (noch nicht gespeichert, siehe „xyz speichern“).",
                       "Numbering changed (not yet saved, see “Save xyz”)."),
    "dft_file_order": ("Nummerierung wie in der Datei.", "Numbering as in the file."),
    "dft_numbering": ("Umnummerieren", "Renumber"),
    "dft_num_start": ("Nummerieren", "Number atoms"),
    "dft_num_cancel": ("Nummerieren abbrechen", "Cancel numbering"),
    "dft_num_tip": ("Atome in der gewünschten Reihenfolge anklicken: das erste wird Atom 1, das zweite Atom 2 … "
                    "Erneuter Klick nimmt ein Atom wieder heraus.",
                    "Click the atoms in the desired order: the first becomes atom 1, the second atom 2 … "
                    "Clicking an atom again removes it."),
    "dft_num_hint": ("„Nummerieren“ drücken und die Atome der Reihe nach anklicken. Gespeichert wird eine neue "
                     "xyz-Datei mit umsortierten Zeilen; Koordinaten bleiben unverändert.",
                     "Press “Number atoms” and click the atoms in order. A new xyz file with reordered lines is "
                     "saved; coordinates are unchanged."),
    "dft_num_next": ("Als Nächstes: Atom {next} ({k} von {n} vergeben).", "Next: atom {next} ({k} of {n} assigned)."),
    "dft_num_rest": ("Nicht angeklickte Atome erhalten {a}–{b} in ihrer bisherigen Reihenfolge.",
                     "Atoms not clicked get {a}–{b} in their previous order."),
    "dft_num_rest_h": ("Nicht angeklickte Atome erhalten {a}–{b}; H-Atome am Ende, nach ihrem Atom geordnet.",
                       "Atoms not clicked get {a}–{b}; H atoms at the end, ordered by their atom."),
    "dft_num_back": ("Letztes zurück", "Undo last"),
    "dft_num_apply": ("Übernehmen", "Apply"),
    "dft_num_done": ("Neue Nummerierung übernommen.", "New numbering applied."),
    "dft_h_follow": ("H-Atome folgen ihrem Atom", "H atoms follow their atom"),
    "dft_h_follow_tip": ("Angeklickte Atome behalten ihre Nummern, dann die übrigen Schweratome; nicht angeklickte "
                         "H-Atome kommen ans Ende, geordnet nach dem Atom, an dem sie sitzen (sonst behalten sie ihre "
                         "bisherige Reihenfolge).",
                         "Clicked atoms keep their numbers, then the other heavy atoms; H atoms that were not clicked "
                         "go to the end, ordered by the atom they are bonded to (otherwise they keep their previous "
                         "order)."),
    "dft_order_reset": ("Reihenfolge der Datei", "File order"),
    "dft_order_reset_tip": ("Nummerierung wie in der geladenen Datei wiederherstellen",
                            "Restore the numbering of the loaded file"),
    "dft_save_xyz": ("xyz speichern …", "Save xyz …"),
    "dft_save_xyz_tip": ("Neue xyz-Datei in der aktuellen Reihenfolge (Standard: „tables“ der Verbindung). Die geladene Datei "
                         "bleibt unverändert.",
                         "New xyz file in the current order (default: “tables” of the compound). The loaded file stays "
                         "unchanged."),
    "dft_no_overwrite": ("Die geladene Datei wird nicht überschrieben – bitte einen anderen Namen wählen.",
                         "The loaded file is not overwritten – please choose a different name."),
    "dft_not_calc": ("weder xyz noch ORCA-/Gaussian-Ausgabe", "neither xyz nor ORCA/Gaussian output"),
    "dft_no_geometry": ("keine Koordinaten in der Ausgabe", "no coordinates in the output"),
    "dft_w_abnormal": ("⚠ Rechnung nicht normal beendet (abgebrochen oder Datei unvollständig) – Werte aus dem letzten "
                       "vollständigen Abschnitt.",
                       "⚠ calculation did not terminate normally (aborted or file incomplete) – values from the last "
                       "complete section."),
    "dft_w_not_converged": ("⚠ Optimierung nicht konvergiert.", "⚠ optimization not converged."),
    "dft_w_orca_version": ("⚠ ORCA {v}: geprüft ist nur ORCA 6 – Werte im SI-Text mit der Ausgabe vergleichen.",
                           "⚠ ORCA {v}: only ORCA 6 has been verified – compare the SI values with the output."),
    "dft_w_no_opt": ("Keine Optimierung in dieser Ausgabe: Geometrie = Eingabegeometrie.",
                     "No optimization in this output: geometry = input geometry."),
    "dft_w_no_freq": ("⚠ Frequenzrechnung angefordert, aber keine Frequenzen gefunden.",
                      "⚠ frequency calculation requested but no frequencies found."),
    "dft_w_imag": ("⚠ Imaginäre Frequenzen: {n} ({v} cm⁻¹) – kein Minimum; H/G gelten nicht für ein Minimum.",
                   "⚠ Imaginary frequencies: {n} ({v} cm⁻¹) – not a minimum; H/G do not refer to a minimum."),
    "dft_w_no_thermo": ("⚠ Thermochemie (H, G) fehlt.", "⚠ thermochemistry (H, G) missing."),
    "dft_w_solv_cpcm": ("CPCM: angegeben ist der dielektrische Beitrag (in E_el enthalten), keine Solvatationsenergie "
                        "ΔG_solv – dafür braucht es dieselbe Rechnung in der Gasphase.",
                        "CPCM: the dielectric contribution (contained in E_el) is given, not a solvation energy "
                        "ΔG_solv – that requires the same calculation in the gas phase."),
    "dft_w_solv_smd": ("SMD: dielektrischer Beitrag und Kavitäts-/Dispersionsterm angegeben; ΔG_solv nur aus dem "
                       "Vergleich mit der Gasphasenrechnung.",
                       "SMD: dielectric contribution and cavity/dispersion term given; ΔG_solv only from comparison "
                       "with the gas-phase calculation."),
    "dft_label_style": ("Label", "Label"),
    "dft_export_labels": ("Labels im Export", "Labels in export"),
    "dft_export_labels_long": ("Labels im Export und in Word", "Labels in export and Word"),
    "dft_export_labels_tip": ("Ohne Häkchen sind Abbildungen in Export und Word-SI ohne Labels (übliche SI-Darstellung); "
                              "die Vorschau zeigt sie weiter zum Nummerieren.",
                              "Unchecked: figures in the export and Word SI have no labels (usual SI style); the "
                              "preview keeps showing them for numbering."),
    "dft_lab_el_num": ("Element + Nummer (C12)", "Element + number (C12)"),
    "dft_lab_num": ("Nur Nummer (12)", "Number only (12)"),
    "dft_lab_ref": ("Labels der Vorlage (CIF)", "Labels of the template (CIF)"),
    "dft_lab_ref_tip": ("„Labels der Vorlage“: nach „Wie Vorlage nummerieren“ mit einer CIF die Atomnamen der "
                        "Kristallstruktur (C1, N2, H3A …); Atome ohne Gegenstück behalten Element + Nummer.",
                        "“labels of the template”: after “Number like template” with a CIF, the atom names of the "
                        "crystal structure (C1, N2, H3A …); atoms without a counterpart keep element + number."),
    "dft_ref": ("Wie Vorlage", "Like template"),
    "dft_ref_tip": ("Nummerierung einer anderen Geometrie (DFT) oder einer Kristallstruktur (Tab X-Ray) übernehmen: "
                    "Zuordnung über das Bindungsnetz, bei Symmetrie nach der Geometrie (kleinste Abweichung nach "
                    "Überlagerung), H über ihr Nachbaratom.",
                    "Take over the numbering of another geometry (DFT) or a crystal structure (X-Ray tab): matching "
                    "by connectivity, for symmetric molecules by geometry (smallest deviation after superposition), "
                    "H via their neighbour atom."),
    "dft_ref_apply": ("Zuordnen", "Match"),
    "dft_ref_apply_tip": ("Nummerierung von der Vorlage übernehmen (andere Geometrie dieses Tabs oder CIF aus dem "
                          "X-Ray-Tab)", "Take the numbering from the template (another geometry of this tab or a CIF "
                          "from the X-ray tab)"),
    "dft_ref_missing": ("Vorlage nicht lesbar", "template not readable"),
    "dft_ref_fail": ("⚠ Zuordnung nicht möglich: {err}", "⚠ matching not possible: {err}"),
    "dft_match_none": ("Bindungsnetz passt nicht zur Vorlage (weniger als 80 % der Schweratome zuzuordnen)",
                       "connectivity does not match the template (less than 80 % of the heavy atoms can be matched)"),
    "dft_ref_done": ("Wie {ref} nummeriert: {n} Schweratome zugeordnet (Vorlage {nr}, hier {nt}), {nh} H; "
                     "Abweichung nach Überlagerung {rmsd} Å.",
                     "Numbered like {ref}: {n} heavy atoms matched (template {nr}, here {nt}), {nh} H; deviation "
                     "after superposition {rmsd} Å."),
    "dft_ref_sym": ("Bindungsnetz symmetrisch: gewählt nach Geometrie, nächstbeste andere Zuordnung {alt} Å.",
                    "symmetric connectivity: chosen by geometry, next best other assignment {alt} Å."),
    "dft_ref_amb": ("⚠ praktisch gleich gute Zuordnung – gleichwertige Atome prüfen: {atoms}",
                    "⚠ practically equal assignment – check equivalent atoms: {atoms}"),
    "dft_ref_partial": ("⚠ nur Teilübereinstimmung (gemeinsamer Teil des Bindungsnetzes).",
                        "⚠ partial match only (common part of the connectivity)."),
    "dft_ref_truncated": ("⚠ mehr als {n} mögliche Zuordnungen – nur die ersten geprüft.",
                          "⚠ more than {n} possible assignments – only the first were checked."),
    "dft_ref_rest": ("{n} Atome ohne Gegenstück stehen am Ende in ihrer bisherigen Reihenfolge.",
                     "{n} atoms without a counterpart are placed at the end in their previous order."),
    "dft_zero_based": ("Zählung ab 0", "Count from 0"),
    "dft_zero_based_long": ("Zählung ab 0 (wie ORCA)", "count from 0 (as ORCA)"),
    "dft_zero_based_tip": ("ORCA zählt Atome ab 0 (z. B. in %geom Constraints), Gaussian und die meisten Programme "
                           "ab 1. Ändert nur die Anzeige.",
                           "ORCA counts atoms from 0 (e.g. in %geom constraints), Gaussian and most programs from 1. "
                           "Changes the display only."),
    "dft_radius": ("Atomradius", "Atom radius"),
    "bg_label": ("Hintergrund", "Background"),
    "bg_white": ("Weiß", "White"),
    "bg_transparent": ("Transparent", "Transparent"),
    "bg_color": ("Farbe …", "Colour …"),
    "bg_color_x": ("Farbe {c} …", "Colour {c} …"),
    "bg_pick": ("Hintergrundfarbe", "Background colour"),
    "bg_tip": ("Hintergrund der Abbildung in Vorschau, PDF/SVG/PNG und Word (transparent: Vorschau weiß)",
               "Figure background in preview, PDF/SVG/PNG and Word (transparent: preview white)"),
    "ball_rel_tip": ("Kugel-Stab-Stile: relativ zum Standardwert ({std} Å = Größe wie im Stil vorgesehen)",
                     "Ball-and-stick styles: relative to the default ({std} Å = size as designed for the style)"),
    "dft_hover_file": ("(in der Datei: {lab})", "(in the file: {lab})"),
    "dft_mouse_hint": ("Ziehen = drehen, rechte Taste = verschieben, Mausrad = Zoom, Klick = Atom zum Messen/Ausrichten "
                       "wählen (beim Nummerieren: nummerieren), Doppelklick = Label an/aus, Shift + Rahmen = Labels mehrerer "
                       "Atome an/aus, Labels lassen sich verschieben.",
                       "Drag = rotate, right button = pan, wheel = zoom, click = select atom to measure/align (while "
                       "numbering: number it), double-click = label on/off, Shift + drag a box = labels of several "
                       "atoms on/off; labels can be dragged."),
    # -- Publikation (seit 2.3) -------------------------------------------------------------------------------
    "act_new_publication": ("Neues Projekt …",
                            "New project …"),
    "act_new_publication_tip": ("Projekt = Ordner für alle Verbindungen einer Veröffentlichung: Gesamt-SI und Datenpakete aller "
                                "Verbindungen auf einmal",
                                "Project = folder for all compounds of a paper: complete SI and data packages of all compounds at "
                                "once"),
    "act_to_publication": ("Zum Projekt",
                           "Back to project"),
    "welcome_publications": ("Projekte",
                             "Projects"),
    "pub_mono": ("P", "P"),
    "pub_n_compounds": ("{n} Verbindungen", "{n} compounds"),
    "pub_part_of": ("Teil des Projekts „{t}“",
                    "Part of the project “{t}”"),
    "pub_is_project": ("Dieser Ordner ist schon eine Verbindung. Bitte den übergeordneten Ordner wählen.",
                       "This folder already is a compound. Please choose its parent folder."),
    "copy_target_used": ("In {p} liegt schon eine Verbindung oder ein Projekt. Bitte einen leeren Ordner wählen.",
                         "{p} already holds a compound or project. Please choose an empty folder."),
    "pub_info": ("Angaben …", "Details …"),
    "pub_info_missing": ("Noch keine Angaben – Titel, Autoren, DOI auf der Seite „Angaben“",
                         "No details yet – title, authors, DOI on the “Details” page"),
    "pub_info_hint": ("Angaben für README.txt des Datensatzes und die Titelseite der Gesamt-SI. Leere Felder fallen "
                      "weg.",
                      "Details for the README.txt of the dataset and the title page of the complete SI. Empty fields "
                      "are left out."),
    "pub_f_paper_title": ("Titel des Artikels", "Title of the paper"),
    "pub_ph_paper_title": ("Für das Titelblatt der SI; kursiv mit <i>…</i>", "For the SI title page; italics with <i>…</i>"),
    "pub_f_title": ("Titel des Datensatzes", "Title of the dataset"),
    "pub_f_authors": ("Autoren", "Authors"),
    "pub_f_affiliation": ("Adresse", "Affiliation"),
    "pub_f_contact": ("Kontakt (E-Mail)", "Contact (email)"),
    "pub_f_orcid": ("ORCID", "ORCID"),
    "pub_f_doi": ("DOI des Datensatzes", "DOI of the dataset"),
    "pub_f_related": ("Zugehörige Publikation", "Related publication"),
    "pub_f_project_description": ("Projektbeschreibung", "Project description"),
    "pub_f_dataset_description": ("Beschreibung des Datensatzes", "Dataset description"),   # ein Wort war breiter als die Spalte
    "pub_f_license": ("Lizenz", "License"),
    "pub_ph_title": ("Leer = Electronic supplement to <Titel des Artikels>",
                     "Empty = Electronic supplement to <title of the paper>"),
    "pub_ph_authors": ("Vorname Name, Vorname Name and Vorname Name", "First Last, First Last and First Last"),
    "pub_ph_doi": ("Z. B. 10.17877/RESOLV-…", "E.g. 10.17877/RESOLV-…"),
    "pub_ph_related": ("Zitat und DOI des Artikels", "Citation and DOI of the article"),
    "pub_ph_project_description": ("Z. B. Abstract des Artikels", "E.g. abstract of the article"),
    "pub_ph_dataset_description": ("Leer = automatisch aus den Datenarten (NMR, IR, UV-Vis, CV …) und Verbindungen",
                                   "Empty = generated from the data kinds (NMR, IR, UV-Vis, CV …) and compounds"),
    "nav_home": ("Übersicht", "Overview"),
    "chemdraw_edit": ("In ChemDraw bearbeiten", "Edit in ChemDraw"),
    "chemdraw_edit_tip": ("Öffnet die Struktur der Verbindung in ChemDraw (eine leere Datei liegt schon bereit). Beim "
                          "Speichern übernimmt Elucida Struktur, Formel und Molmasse automatisch.",
                          "Opens the structure of the compound in ChemDraw (an empty file is already prepared). When "
                          "you save, Elucida takes over structure, formula and molar mass automatically."),
    "chemdraw_edit_scheme_tip": ("Öffnet das Reaktionsschema in ChemDraw (eine leere Datei liegt schon bereit). Beim "
                                 "Speichern übernimmt Elucida das Schema automatisch. Für das bearbeitbare Objekt in "
                                 "Word zusätzlich als .cdx, für die Vorschau als .emf speichern.",
                                 "Opens the reaction scheme in ChemDraw (an empty file is already prepared). When you "
                                 "save, Elucida takes over the scheme automatically. For the editable object in Word "
                                 "also save as .cdx, for the preview as .emf."),
    "chemdraw_opened": ("{name} in ChemDraw geöffnet – Speichern übernimmt die Änderung", "{name} opened in ChemDraw – "
                        "saving takes over the change"),
    "chemdraw_taken": ("Aus ChemDraw übernommen: {name}", "Taken over from ChemDraw: {name}"),
    "chemdraw_open_failed": ("{p} ließ sich nicht öffnen – ist ChemDraw das Standardprogramm für .cdxml?",
                             "{p} could not be opened – is ChemDraw the default application for .cdxml?"),
    "export_stale": ("{name} ist älter als die CDXML (in ChemDraw bearbeitet) und wird nicht verwendet – für die exakte "
                     "ChemDraw-Grafik neu exportieren",
                     "{name} is older than the CDXML (edited in ChemDraw) and is not used – export it again for the "
                     "exact ChemDraw drawing"),
    "nav_no_project": ("ohne Projekt", "no project"),
    "choose_pub_new": ("Projekt für die neue Verbindung", "Project for the new compound"),
    "choose_pub_hint": ("Jede Verbindung gehört zu einem Projekt (Ordner der Veröffentlichung). Projekt wählen:",
                        "Every compound belongs to a project (folder of the paper). Choose the project:"),
    "choose_pub_other": ("Anderes Projekt öffnen …", "Open another project …"),
    "move_title": ("In anderes Projekt verschieben …", "Move to another project …"),
    "move_copy_title": ("In anderes Projekt kopieren …", "Copy to another project …"),
    "assign_title": ("Einem Projekt zuordnen …", "Assign to a project …"),
    "orphan_q": ("Diese Verbindung gehört noch zu keinem Projekt. Jetzt einem Projekt zuordnen? Der Ordner wird dafür in "
                 "den Projektordner verschoben.",
                 "This compound does not belong to a project yet. Assign it to a project now? Its folder is moved into "
                 "the project folder."),
    "compound_moved": ("Verbindung verschoben: {src} → {dst}", "Compound moved: {src} → {dst}"),
    "compound_copied": ("Verbindung kopiert: {src} → {dst}", "Compound copied: {src} → {dst}"),
    "add_move_copy_q": ("{p}\n\nliegt außerhalb des Projekts. In den Projektordner verschieben oder eine Kopie "
                        "anlegen (z. B. für ein zweites Paper)?",
                        "{p}\n\nis outside the project. Move it into the project folder or make a copy (e.g. for a "
                        "second paper)?"),
    "add_move": ("Verschieben", "Move"),
    "add_copy": ("Kopieren", "Copy"),
    "act_to_overview": ("Zur Übersicht", "Back to overview"),
    "nav_switch_tip": ("Zu einer anderen Verbindung des Projekts wechseln", "Switch to another compound of the project"),
    "pub_new_compound": ("Neue Verbindung", "New compound"),
    "pub_new_compound_q": ("Name der Verbindung (auch Ordnername), z. B. 3b:",
                           "Name of the compound (also the folder name), e.g. 3b:"),
    "pub_add_project": ("Verbindung hinzufügen …",
                        "Add compound …"),
    "pub_add_project_tip": ("Vorhandene Verbindung aufnehmen (der Ordner bleibt, wo er ist). Verbindungen in Unterordnern des "
                            "Projekts werden automatisch aufgenommen.",
                            "Add an existing compound (the folder stays where it is). Compounds in subfolders of the project are "
                            "added automatically."),
    "pub_datapack": ("Datenpakete (Zip)", "Data packages (zip)"),
    "pub_datapack_tip": ("Rohdaten aller Verbindungen wie der Datensatz der Gruppe: je Verbindung ein Zip, "
                         "CompChem.zip, README.txt und Lizenz",
                         "Raw data of all compounds like the group's dataset: one zip per compound, CompChem.zip, "
                         "README.txt and license"),
    "pub_si": ("Gesamt-SI (Word)", "Complete SI (Word)"),
    "pub_si_tip": ("Eine Word-Datei für alle Verbindungen, Kapitel wie die SI der Gruppe",
                   "One Word file for all compounds, chapters as in the group's SI"),
    "pub_compounds": ("Verbindungen", "Compounds"),
    "pub_empty": ("Noch keine Verbindungen. „Neue Verbindung“ legt einen Unterordner an; vorhandene Verbindungsordner "
                  "hierher verschieben oder über „Verbindung hinzufügen“ aufnehmen.",
                  "No compounds yet. “New compound” creates a subfolder; move existing compound folders here or use "
                  "“Add compound”."),
    "pub_missing": ("Nicht gefunden: {p}", "Not found: {p}"),
    "pub_hint": ("Reihenfolge = Reihenfolge in Gesamt-SI und Datensatz (Zeilen mit der Maus ziehen oder nach Name sortieren). Jede Verbindung "
                 "bleibt eigenständig und lässt sich auch allein öffnen.",
                 "Order = order in the complete SI and the dataset (drag rows with the mouse or sort by name). Each compound stays "
                 "self-contained and can also be opened on its own."),
    "pub_up": ("Nach oben", "Move up"),
    "pub_sort_name": ("Nach Name sortieren", "Sort by name"),
    "group_menu": ("Gruppe", "Group"),
    "group_new": ("Neue Gruppe", "New group"),
    "group_none": ("Ohne Gruppe", "No group"),
    "group_name_q": ("Name der Gruppe (z. B. Precursor, Salze, NHOs):", "Name of the group (e.g. precursors, salts, NHOs):"),
    "group_rename": ("Umbenennen …", "Rename …"),
    "group_delete": ("Gruppe auflösen (Verbindungen bleiben)", "Dissolve group (compounds stay)"),
    "group_exists": ("Eine Gruppe „{g}“ gibt es schon.", "A group “{g}” already exists."),
    "group_tip": ("Verbindungen gliedern (z. B. Precursor, Salze, NHOs): Rechtsklick auf eine Verbindung → Gruppe, oder "
                  "in eine Gruppe ziehen. Die Reihenfolge der Gruppen gilt für Gesamt-SI und Datensatz.",
                  "Organize compounds (e.g. precursors, salts, NHOs): right-click a compound → Group, or drag it into a "
                  "group. The order of the groups applies to the complete SI and the dataset."),
    "pub_sort_tip": ("Reihenfolge nach dem Namen der Verbindung (1a, 1b, 2a … 10a); einzeln lassen sich Verbindungen mit "
                     "der Maus an eine andere Stelle ziehen",
                     "Order by compound name (1a, 1b, 2a … 10a); single compounds can be dragged to another place with "
                     "the mouse"),
    "inset_beside": ("Inset: im Bild kein freier Platz ohne Kurven – steht rechts neben dem Spektrum",
                     "Inset: no free space without curves in the plot – placed to the right of the spectrum"),
    "pub_check_summary": ("{ok} von {n} vollständig", "{ok} of {n} complete"),
    "pub_check_gaps": ("fehlt: {gaps}", "missing: {gaps}"),
    "pub_check_known": ("literaturbekannt", "known"),
    "pub_check_tip": ("Pflicht: ¹H, ¹³C, 2D-NMR, HRMS, IR, m.p. (literaturbekannt: nur ¹H, ¹³C); grau = weitere "
                      "vorhandene Daten. Literaturbekannt im Tab Verbindung setzen.",
                      "Required: ¹H, ¹³C, 2D NMR, HRMS, IR, m.p. (known compounds: only ¹H, ¹³C); grey = further "
                      "data present. Set “known” in the Compound tab."),
    "pub_down": ("Nach unten", "Move down"),
    "pub_remove": ("Aus dem Projekt nehmen (Ordner bleibt)",
                   "Remove from the project (folder stays)"),
    "pub_dp_hint": ("Je Verbindung ein Zip <Name>.zip (Aufbau wie beim Einzelpaket), DFT-Rechnungen aller Verbindungen in "
                    "CompChem.zip, dazu README.txt aus den Angaben und der Lizenztext. Die Auswahl einzelner Dateien aus "
                    "„Datenpaket (Zip)“ der Verbindung gilt weiter. Laborkürzel werden der Verbindung zugeordnet, in "
                    "deren Dateinamen sie stehen.",
                    "One zip <name>.zip per compound (as the single package), DFT calculations of all compounds in "
                    "CompChem.zip, plus README.txt from the details and the license text. File choices made in the "
                    "compound's “Data package (zip)” still apply. Lab codes are assigned to the compound whose file names "
                    "contain them."),
    "pub_dp_groups": ("Datenarten", "Data kinds"),
    "pub_dp_dft": ("DFT → CompChem.zip", "DFT → CompChem.zip"),
    "pub_dp_readme": ("README.txt und Lizenz", "README.txt and license"),
    "pub_dp_dir": ("Zielordner", "Target folder"),
    "pub_dp_size": ("{z} Zip-Dateien, {n} Einträge, {size}", "{z} zip files, {n} entries, {size}"),
    "pub_dp_writing": ("Schreibe {name}.zip …", "Writing {name}.zip …"),
    "pub_dp_done": ("Datensatz geschrieben: {p} ({z} Zip-Dateien, {n} Dateien, {size})",
                    "Dataset written: {p} ({z} zip files, {n} files, {size})"),
    "pub_si_hint": ("Kapitel wie die SI der Gruppe: Materials and Methods, Synthesis and Characterization, NMR, UV-Vis, "
                    "EPR, CV, SEC, X-Ray, Computational. In jedem Kapitel die Verbindungen in der Reihenfolge des "
                    "Projekts; leere Kapitel fallen weg. Texte zu Methoden und Kapiteln unter „SI-Texte …“.",
                    "Chapters as in the group's SI: Materials and Methods, Synthesis and Characterization, NMR, UV-Vis, "
                    "EPR, CV, SEC, X-ray, Computational. Within each chapter the compounds in the order of the project; "
                    "empty chapters are left out. Texts for methods and chapters under “SI texts …”."),
    "pub_si_sections": ("Kapitel", "Chapters"),
    "pub_si_template": ("Vorlage", "Template"),
    "pub_si_template_tip": ("Titelblatt und Bezeichnung der Abbildungen/Tabellen; Kapitel, Schrift und Seitenaufteilung "
                            "bleiben wie die SI der Gruppe",
                            "Title page and labels of figures/tables; chapters, font and page layout stay as in the "
                            "group's SI"),
    "pub_tpl_group": ("Gruppe", "Group"),                # kurz: die Auswahlliste schneidet nichts ab
    "pub_tpl_wiley": ("Wiley", "Wiley"),
    "pub_tpl_acs": ("ACS", "ACS"),
    "pub_tpl_rsc": ("RSC", "RSC"),
    "pub_tpl_nature": ("Nature", "Nature"),
    "pub_tpl_group_long": ("Wie die eigene Angewandte-SI; „Figure S1:“", "As the own Angewandte SI; “Figure S1:”"),
    "pub_tpl_wiley_long": ("Supporting Information, „Figure S1.“", "Supporting Information, “Figure S1.”"),
    "pub_tpl_acs_long": ("Supporting Information, „Figure S1.“, Seiten S1 …", "Supporting Information, “Figure S1.”, pages S1 …"),
    "pub_tpl_rsc_long": ("Supplementary Information, „Fig. S1“", "Supplementary Information, “Fig. S1”"),
    "pub_tpl_nature_long": ("Supplementary Information, „Supplementary Figure 1 |“",
                            "Supplementary Information, “Supplementary Figure 1 |”"),
    "pub_si_toc": ("Titelseite und Inhaltsverzeichnis", "Title page and table of contents"),
    "pub_si_methods": ("Auswertungstexte (Fits) je Verbindung in den Kapiteln",
                       "Data processing texts (fits) per compound in the chapters"),
    "pub_si_write": ("Word-Datei schreiben", "Write Word file"),
    "pub_si_writing": ("Gesamt-SI wird erstellt …", "Creating complete SI …"),
    "pub_si_compound": ("Verbindung {name} …", "Compound {name} …"),
    "compound_sample": ("Substanz übrig", "Sample left"),
    "compound_sample_ph": ("Probennummer (optional)", "Sample number (optional)"),
    "compound_sample_tip": ("Noch Substanz vorhanden (nur intern: Startbildschirm, Projektseite, Suche; nie "
                            "SI oder Datenpaket). Fehlende Analytik erscheint dann gelb statt rot (nachholbar).",
                            "Some compound left (internal only: start screen, project page, search; never "
                            "SI or data package). Missing analytics then show yellow instead of red (can be measured)."),
    "compound_sample_badge": ("Noch Substanz übrig", "Sample of this compound still left"),
    "pub_procs": ("Allgemeine Vorschriften", "General procedures"),
    "pub_procs_hint": ("Je Reaktionstyp eine Vorschrift (GP A, GP B …). Im Synthese-Tab wählt jede Verbindung ihre GP "
                       "(Knopf „GP“); dort stehen nur die spezifischen Angaben. In der Gesamt-SI steht die GP einmal, "
                       "direkt vor der ersten Verbindung, die sie benutzt. Absätze durch Leerzeilen, Formeln wie CH2Cl2. "
                       "Ein umbenanntes Kürzel ändert sich in allen Verbindungen mit (Zuordnung und „GP A“ im Text).",
                       "One procedure per reaction type (GP A, GP B …). In the Synthesis tab each compound chooses its GP "
                       "(button “GP”) and holds only the specific details. The combined SI shows each GP once, right "
                       "before the first compound using it. Paragraphs separated by blank lines, formulas like CH2Cl2. "
                       "A renamed key changes in all compounds (assignment and “GP A” in the text)."),
    "pub_procs_add": ("Neu", "New"),
    "pub_procs_key": ("Kürzel", "Label"),
    "pub_procs_title": ("Titel", "Title"),
    "pub_procs_title_ph": ("Z. B. Suzuki coupling (optional)", "E.g. Suzuki coupling (optional)"),
    "pub_procs_text_ph": ("Text der Vorschrift (englisch, wie in der SI)", "Procedure text (as in the SI)"),
    "pub_si_groups": ("Gruppen als Unterkapitel", "Groups as subsections"),
    "pub_si_groups_tip": ("Aus: Gruppen ordnen nur die Projektseite, die SI hat keine Unterkapitel (Reihenfolge bleibt). "
                          "Gilt für dieses Projekt.",
                          "Off: groups only organize the project page, the SI has no subsections (order unchanged). "
                          "Applies to this project."),
    "pub_texts": ("SI-Texte …", "SI texts …"),
    "pub_texts_hint": ("Texte, die zum Projekt gehören: „Materials and Methods“ und je Kapitel eine Einleitung (steht unter "
                       "der Kapitelüberschrift vor den Verbindungen). Absätze durch Leerzeilen trennen; Formeln wie CH2Cl2 "
                       "und Exponenten wie cm-1 werden wie in den Unterschriften gesetzt. Gespeichert in "
                       "publication.elucida.",
                       "Texts that belong to the project: “Materials and Methods” and an introduction per chapter (below the "
                       "chapter heading, before the compounds). Separate paragraphs by blank lines; formulas such as CH2Cl2 "
                       "and exponents such as cm-1 are set as in the captions. Stored in publication.elucida."),
    "pub_texts_ph": ("Einleitung des Kapitels (optional)", "Introduction of the chapter (optional)"),
    "pub_texts_ph_methods": ("Lösungsmittel, Reagenzien, Geräte … (leer = Aufbau-Texte der Tabs)",
                             "Solvents, reagents, instruments … (empty = setup texts of the tabs)"),
    "pub_texts_setup": ("Aufbau-Texte der Tabs übernehmen", "Insert setup texts of the tabs"),
    "pub_texts_setup_tip": ("Hängt die in den Tabs hinterlegten Aufbau-Texte (Geräte) an",
                            "Appends the setup texts (instruments) stored in the tabs"),
    # ---- Karten statt Dialoge (Nutzerwunsch 2026-11-11: keine Popups) ------------------------------------------------
    "tf_own": ("Nur dieser Tab", "This tab only"),
    "tf_own_hint": ("Ohne „Nur dieser Tab“ gilt jede Änderung für alle Tabs ohne eigenes Format.",
                    "Without “This tab only”, every change applies to all tabs without their own format."),
    "tf_greek_c": ("λ, ε in Symbolschrift", "λ, ε in symbol font"),
    "tf_label_size_row": ("Labelgröße", "Label size"),
    "tf_label_style": ("Labelstil", "Label style"),
    "tf_label_color": ("Labelfarbe", "Label colour"),
    "tf_axes_frame_c": ("Plot geschlossen", "Closed plot frame"),
    "tf_struct_frame_c": ("Um die Struktur", "Around structure"),
    "tf_defaults": ("Auf Standard zurücksetzen", "Reset to defaults"),
    "si_export_grp": ("SI-Export (Word)", "SI Export (Word)"),
    "si_export_parts": ("Teile", "Parts"),
    "si_export_figs": ("Abbildungen von", "Figures from"),
    "si_figs_tip": ("Abbildung dieses Tabs in die SI übernehmen (gilt mit dem Teil „Abbildungen“).",
                    "Include this tab's figure in the SI (applies with the part “Figures”)."),
    "si_export_hint": ("Datei → SI-Abschnitt exportieren (Word) exportiert sofort mit dieser Auswahl; sie gilt für alle "
                       "Verbindungen.",
                       "File → Export SI section (Word) exports right away with this selection; it applies to all "
                       "compounds."),
    "si_chip_char": ("Charakterisierung", "Characterization"),
    "si_chip_nmr": ("NMR-Spektren", "NMR spectra"),
    "si_chip_figs": ("Abbildungen", "Figures"),
    "si_chip_methods": ("Methodik", "Methods"),
    "si_chip_xray": ("Kristallstruktur", "Crystal structure"),
    "si_chip_dft": ("DFT", "DFT"),
    "si_nothing_selected": ("Für die SI ist kein Teil mit Daten gewählt (Tab Verbindung, Karte „SI-Export (Word)“).",
                            "No part with data is selected for the SI (Compound tab, card “SI Export (Word)”)."),
    "si_parts_without_data": ("Ohne Daten, nicht exportiert: {parts}", "No data, not exported: {parts}"),
    "pub_details_tab": ("Angaben", "Details"),
    "pub_details_grp": ("Angaben zum Projekt", "Project Details"),
    # Projektseite „Vergleich“ (app/comparison.py)
    "pub_compare_tab": ("Vergleich", "Comparison"),
    "cmp_snapshot_failed": ("Stand für den Vergleich nicht geschrieben (das Projekt ist gespeichert):",
                            "Comparison snapshot not written (the project was saved):"),
    "guide_compare_title": ("Vergleich: Verbindungen des Projekts in einem Bild oder einer Tabelle",
                            "Comparison: compounds of the project in one figure or table"),
    "guide_compare_files": ("Daten: die Auswertungen der Verbindungen (CV, UV-Vis, Fluoreszenz, EPR), nichts wird neu "
                            "berechnet",
                            "Data: the evaluations of the compounds (CV, UV-Vis, fluorescence, EPR); nothing is "
                            "evaluated again"),
    "guide_compare_steps": ("Links einen Vergleich anlegen: CV-Stapel, Spektren oder Tabelle\nVerbindungen wählen und "
                            "ordnen\nFehlt ein Stand oder ist er veraltet: „Aktualisieren“\nExportieren (Abbildung bzw. "
                            "Word, Excel, CSV)",
                            "Create a comparison on the left: CV stack, spectra or table\nChoose and order the "
                            "compounds\nIf a snapshot is missing or outdated: “Refresh”\nExport (figure, or Word, Excel, "
                            "CSV)"),
    "cmp_list": ("Vergleiche", "Comparisons"),
    "cmp_list_empty": ("Noch kein Vergleich", "No comparison yet"),
    "cmp_new_cv": ("CV-Stapel", "CV Stack"),
    "cmp_new_spectra": ("Spektren", "Spectra"),
    "cmp_new_table": ("Tabelle", "Table"),
    "cmp_new": ("Neuer Vergleich …", "New comparison …"),
    "cmp_new_hint": ("CV-Stapel, Spektren, H-Zelle, UV-Vis-Kinetik oder Eigenschaftstabelle über mehrere Verbindungen "
                     "hinweg.", "CV stack, spectra, H-Cell, UV-Vis kinetics or property table across several compounds."),
    "cmp_new_cv_tip": ("Neuer Vergleich: je Verbindung ein Cyclovoltammogramm, versetzt übereinander",
                       "New comparison: one cyclic voltammogram per compound, stacked"),
    "cmp_new_spectra_tip": ("Neuer Vergleich: UV-Vis- und/oder Emissionsspektren mehrerer Verbindungen in einem Bild",
                            "New comparison: UV-Vis and/or emission spectra of several compounds in one figure"),
    "cmp_new_table_tip": ("Neuer Vergleich: Tabelle mit Werten aus den Tabs und eigenen Spalten",
                          "New comparison: table with values from the tabs and columns of your own"),
    "cmp_kind_cv": ("CV-Stapel", "CV stack"),
    "cmp_kind_spectra": ("Spektren", "Spectra"),
    "cmp_kind_table": ("Tabelle", "Table"),
    "cmp_name": ("Name", "Name"),
    "cmp_kind": ("Art", "Kind"),
    "cmp_remove_tip": ("Vergleich aus dem Projekt nehmen (exportierte Dateien bleiben)",
                       "Remove the comparison from the project (exported files stay)"),
    "cmp_compounds": ("Verbindungen", "Compounds"),
    "cmp_compound": ("Verbindung", "Compound"),
    "cmp_status": ("Stand", "Snapshot"),
    "cmp_st_ok": ("Aktuell", "Current"),
    "cmp_st_outdated": ("Veraltet", "Outdated"),
    "cmp_st_missing": ("Fehlt", "Missing"),
    "cmp_st_none": ("Keine Daten", "No data"),
    "cmp_st_tip": ("Die Verbindung wurde seit ihrem letzten Stand geändert oder hat noch keinen: „Aktualisieren“",
                   "The compound changed since its last snapshot or has none yet: “Refresh”"),
    "cmp_need_refresh": ("Ohne aktuellen Stand (nicht im Vergleich): {names}",
                         "Without a current snapshot (not in the comparison): {names}"),
    "cmp_refresh": ("Aktualisieren", "Refresh"),
    "cmp_refresh_tip": ("Verbindungen ohne oder mit veraltetem Stand kurz öffnen und ihren Stand neu schreiben",
                        "Briefly open compounds without or with an outdated snapshot and write it again"),
    "cmp_refreshed": ("Stand erneuert, Verbindungen: {n}", "Snapshot renewed, compounds: {n}"),
    "cmp_member": ("Gewählte Verbindung", "Selected Compound"),
    "cmp_measurement": ("Messung", "Measurement"),
    "cmp_couple": ("Redoxpaar", "Redox couple"),
    "cmp_label": ("Beschriftung", "Label"),
    "cmp_lab_fwd": ("Hinpeak", "Forward peak"),
    "cmp_lab_epa": ("E_pa", "E_pa"),
    "cmp_lab_epc": ("E_pc", "E_pc"),
    "cmp_lab_e12": ("E½", "E½"),
    "cmp_lab_none": ("Keine", "None"),
    "cmp_gap": ("Abstand", "Gap"),
    "cmp_gap_tip": ("Abstand der Kurven in Vielfachen der größten Kurvenhöhe",
                    "Gap between the curves in multiples of the largest curve height"),
    "cmp_normalize": ("Normiert", "Normalized"),
    "cmp_normalize_long": ("Jede Kurve auf ihren größten Betrag des Stroms normiert",
                           "Each curve normalized to its largest absolute current"),
    "cmp_arrow": ("Scanpfeil", "Scan arrow"),
    "cmp_structures": ("Strukturen", "Structures"),
    "cmp_struct_color": ("Struktur in Kurvenfarbe", "Structure in curve colour"),
    "cmp_std_struct": ("Struktur des Standards", "Standard structure"),
    "cmp_legend": ("Legende", "Legend"),
    "cmp_missing_note": ("Ohne aktuellen Stand, nicht gezeigt: {names} („Aktualisieren“)",
                         "Without a current snapshot, not shown: {names} (“Refresh”)"),
    "cmp_ref_refused": ("Andere Referenzskala als die erste Kurve ({ref}), nicht gezeigt (nie umgerechnet): {names}",
                        "Reference scale differs from the first curve ({ref}), not shown (never converted): {names}"),
    "cmp_edge_note": ("{name}: Peak am Rand des Fensters des Redoxpaars oder zwei Wellen im Fenster, keine Beschriftung",
                      "{name}: peak at the edge of the redox couple window or two waves in the window, no label"),
    "cmp_series": ("Serie (UV-Vis)", "Series (UV-Vis)"),
    "cmp_content": ("Inhalt", "Content"),
    "cmp_content_eps": ("UV-Vis (ε)", "UV-Vis (ε)"),
    "cmp_content_abs_norm": ("UV-Vis normiert", "UV-Vis normalized"),
    "cmp_content_em": ("Emission normiert", "Emission normalized"),
    "cmp_content_abs_em": ("UV-Vis + Emission (normiert)", "UV-Vis + emission (normalized)"),
    "cmp_stack": ("Gestapelt", "Stacked"),
    "cmp_norm_tip": ("Bereich, dessen höchste Absorbanz auf 1 gesetzt wird (z. B. die Bande über 400 nm statt der im UV).\n"
                     "Feld leeren = auto: Maximum der ganzen Messung ab dem Anfang des Peakbereichs.",
                     "Range whose highest absorbance is set to 1 (e.g. the band above 400 nm instead of the UV band).\n"
                     "Clear the field = auto: maximum of the whole measurement from the start of the peak range."),
    "cmp_norm_outside": ("Keine Bande im Normierungsbereich {lo}–{hi} nm (außerhalb der Messung oder unter 2 % des "
                         "Maximums), nicht gezeigt: {names}",
                         "No band within the normalization range {lo}–{hi} nm (outside the measurement or below 2% of "
                         "the maximum), not shown: {names}"),
    "cmp_no_eps": ("Ohne ε (Konzentration oder Molmasse fehlt im ε-Tab), nicht gezeigt: {names}",
                   "No ε (concentration or molar mass missing in the ε tab), not shown: {names}"),
    "cmp_step_table": ("Tabelle", "Table"),
    "cmp_columns": ("Größen", "Quantities"),
    "cmp_add_auto": ("Aus den Tabs", "From the Tabs"),
    "cmp_add_auto_tip": ("Größe hinzufügen, deren Werte aus den Tabs der Verbindungen kommen (λmax, ε, E½, g …)",
                         "Add a quantity whose values come from the tabs of the compounds (λmax, ε, E½, g …)"),
    "cmp_add_free": ("Eigene", "Own"),
    "cmp_add_free_tip": ("Eigene Größe hinzufügen: Name und Einheit hier, Werte in der Tabelle rechts eintippen "
                         "(z. B. Rechnung, Literatur)",
                         "Add your own quantity: name and unit here, type the values into the table on the right "
                         "(e.g. calculation, literature)"),
    "cmp_free_col": ("Größe", "Quantity"),
    "cmp_cols_empty": ("Noch keine Größe: „Aus den Tabs“ oder „Eigene“", "No quantity yet: “From the Tabs” or “Own”"),
    "cmp_source": ("Herkunft", "Source"),
    "cmp_src_compound": ("Verbindung", "Compound"),
    "cmp_src_own": ("eigene", "own"),
    "cmp_group_head": ("Gruppenkopf", "Group header"),
    "cmp_auto_fixed": ("Name und Einheit kommen aus dem Tab und stehen fest; für freie Angaben „Eigene“ wählen",
                       "Name and unit come from the tab and are fixed; choose “Own” for free entries"),
    "cmp_head": ("Größe", "Quantity"),
    "cmp_unit": ("Einheit", "Unit"),
    "cmp_group": ("Gruppe", "Group"),
    "cmp_head_ph": ("Z. B. IR (CN2)", "E.g. IR (CN2)"),
    "cmp_unit_ph": ("Z. B. cm-1", "E.g. cm-1"),
    "cmp_group_ph": ("Z. B. Experimental (leer = keiner)", "E.g. Experimental (empty = none)"),
    "cmp_rows": ("Weitere Verbindungen", "Further Compounds"),
    "cmp_rows_empty": ("Keine weiteren Verbindungen", "No further compounds"),
    "cmp_row_ph": ("Name, z. B. Literaturverbindung", "Name, e.g. literature compound"),
    "cmp_row_name": ("Verbindung", "Compound"),
    "cmp_add_row": ("Verbindung", "Compound"),
    "cmp_add_row_tip": ("Zeile für eine Verbindung, die nicht im Projekt liegt (z. B. Literatur); ihre Werte rechts "
                        "in der Tabelle eintippen",
                        "Row for a compound that is not in the project (e.g. literature); type its values into the "
                        "table on the right"),
    "cmp_cells": ("Zellen und Anordnung", "Cells and Layout"),
    "cmp_cell": ("Zelle", "Cell"),
    "cmp_reset_cell": ("Wert des Tabs", "Value of the tab"),
    "cmp_cell_tab": ("Wert im Tab: {v}", "Value in the tab: {v}"),
    "cmp_cell_over": ("Von Hand überschrieben", "Overwritten by hand"),
    "cmp_cell_hint": ("Zellen der Tabelle rechts direkt bearbeiten (Doppelklick); überschriebene Werte aus den Tabs "
                      "stehen orange.",
                      "Edit cells of the table on the right directly (double-click); overwritten values from the tabs "
                      "are shown in orange."),
    "cmp_over_tip": ("Von Hand überschrieben; Wert im Tab: {v}", "Overwritten by hand; value in the tab: {v}"),
    "cmp_transpose": ("Verbindungen als Spalten", "Compounds as columns"),
    "cmp_layout": ("Anordnung", "Layout"),
    "cmp_table": ("Tabelle", "Table"),
    "cmp_copy_tip": ("Tabelle als formatierten Text kopieren (für Word)", "Copy the table as rich text (for Word)"),
    "cmp_copied": ("Tabelle kopiert", "Table copied"),
    "cmp_table_empty": ("Die Tabelle ist leer: Zeilen und Spalten wählen", "The table is empty: choose rows and columns"),
    "cmp_col_formula": ("Summenformel", "Formula"),
    "cmp_col_mw": ("Molmasse", "Molar mass"),
    "cmp_col_mp": ("Schmelzpunkt", "Melting point"),
    "cmp_col_uv_lam": ("UV-Vis: λmax", "UV-Vis: λmax"),
    "cmp_col_uv_eps": ("UV-Vis: ε", "UV-Vis: ε"),
    "cmp_col_uv_solv": ("UV-Vis: Lösungsmittel", "UV-Vis: solvent"),
    "cmp_col_fl_abs": ("Fluoreszenz: λabs", "Fluorescence: λabs"),
    "cmp_col_fl_em": ("Fluoreszenz: λem", "Fluorescence: λem"),
    "cmp_col_fl_stokes": ("Fluoreszenz: Stokes", "Fluorescence: Stokes shift"),
    "cmp_col_e12": ("CV: E½ (Paar {n})", "CV: E½ (couple {n})"),
    "cmp_col_epa": ("CV: E_pa (Paar {n})", "CV: E_pa (couple {n})"),
    "cmp_col_epc": ("CV: E_pc (Paar {n})", "CV: E_pc (couple {n})"),
    "cmp_col_dep": ("CV: ΔEp (Paar {n})", "CV: ΔEp (couple {n})"),
    "cmp_col_cv_ref": ("CV: Referenz", "CV: reference"),
    "cmp_col_epr_g": ("EPR: g", "EPR: g"),
    "cmp_col_epr_a": ("EPR: Kopplungen", "EPR: hyperfine couplings"),
    "cmp_col_epr_D": ("EPR: D", "EPR: D"),
    "cmp_col_epr_ED": ("EPR: |E/D|", "EPR: |E/D|"),
    "cmp_col_ir_band": ("IR: Bande (Ziel ± Toleranz)", "IR: band (target ± tolerance)"),
    "cmp_col_nmr_shift": ("NMR: Verschiebung (Ziel ± Toleranz)", "NMR: shift (target ± tolerance)"),
    "cmp_col_xr_param": ("X-Ray: {p}", "X-Ray: {p}"),
    "cmp_col_xr_sg": ("X-Ray: Raumgruppe", "X-Ray: space group"),
    "cmp_col_xr_system": ("X-Ray: Kristallsystem", "X-Ray: crystal system"),
    "cmp_col_dft_method": ("DFT: Methode", "DFT: method"),
    "cmp_col_dft_eel": ("DFT: E(el)", "DFT: E(el)"),
    "cmp_col_dft_g": ("DFT: G", "DFT: G"),
    "cmp_col_dft_homo": ("DFT: HOMO", "DFT: HOMO"),
    "cmp_col_dft_lumo": ("DFT: LUMO", "DFT: LUMO"),
    "cmp_no_target": ("ohne Ziel", "no target"),
    "cmp_nuc": ("Kern", "Nucleus"),
    "cmp_target": ("Ziel", "Target"),
    "cmp_target_tip": ("Gesuchte Lage: die Zelle zeigt die Bande bzw. das Signal aus der Liste des Tabs, das ihr am "
                       "nächsten liegt – nur innerhalb der Toleranz, sonst bleibt sie leer",
                       "Position looked for: the cell shows the band or signal from the tab's list closest to it – only "
                       "within the tolerance, otherwise it stays empty"),
    "cmp_target_ph_ir": ("Z. B. 2100 (cm-1)", "E.g. 2100 (cm-1)"),
    "cmp_target_ph_nmr": ("Z. B. 7.26 (ppm)", "E.g. 7.26 (ppm)"),
    "cmp_tol": ("Toleranz", "Tolerance"),
    "cmp_tol_tip": ("Größter Abstand zum Ziel (Grenze eingeschlossen); Vorgabe IR ±15 cm-1, ¹H ±0.5 ppm, andere "
                    "Kerne ±2 ppm", "Largest distance from the target (limit included); default IR ±15 cm-1, ¹H ±0.5 "
                    "ppm, other nuclei ±2 ppm"),
    "cmp_xr_struct": ("Struktur (X-Ray)", "Structure (X-Ray)"),
    "cmp_xr_struct_tip": ("Struktur des X-Ray-Tabs, deren Werte die Tabelle zeigt (Vorgabe: die erste)",
                          "Structure of the X-Ray tab whose values the table shows (default: the first)"),
    "cmp_dft_calc": ("Rechnung (DFT)", "Calculation (DFT)"),
    "cmp_dft_calc_tip": ("Rechnung des DFT-Tabs, deren Werte die Tabelle zeigt (Vorgabe: die erste)",
                         "Calculation of the DFT tab whose values the table shows (default: the first)"),
    "cmp_cycle": ("Zyklus", "Cycle"),
    "cmp_cycle_tip": ("Gezeigter Zyklus dieser Messung. Der Stand enthält die ersten {n} Zyklen und den ausgewerteten; "
                      "Zahlen am Peak gibt es nur für den Zyklus, den der CV-Tab ausgewertet hat",
                      "Cycle shown for this measurement. The snapshot holds the first {n} cycles and the evaluated "
                      "one; peak numbers exist only for the cycle the CV tab evaluated"),
    "cmp_cycle_eval": ("{n} (ausgewertet)", "{n} (evaluated)"),
    "cmp_cycle_hint": ("Nicht ausgewertet (der CV-Tab wertet Zyklus {n} aus): keine Zahl am Peak",
                       "Not evaluated (the CV tab evaluates cycle {n}): no number at the peak"),
    "cmp_cycle_gone": ("{name}: Zyklus {n} fehlt im Stand, gezeigt ist der ausgewertete Zyklus {ev}",
                       "{name}: cycle {n} is not in the snapshot, the evaluated cycle {ev} is shown"),
    "cmp_epr_trace": ("Messung (EPR)", "Measurement (EPR)"),
    "cmp_ref_freq_tip": ("Feldachsen wie im EPR-Tab auf diese Mikrowellenfrequenz skalieren (B·ν_ref/ν). „Aus“: nur "
                         "Spektren mit derselben Frequenz wie das erste; andere werden nicht gezeigt",
                         "Scale field axes to this microwave frequency as the EPR tab does (B·ν_ref/ν). “Off”: only "
                         "spectra with the same frequency as the first; others are not shown"),
    "cmp_content_ir": ("IR", "IR"),
    "cmp_content_epr": ("EPR (Feld, normiert)", "EPR (field, normalized)"),
    "cmp_content_epr_g": ("EPR (g, normiert)", "EPR (g, normalized)"),
    "cmp_ir_refused": ("Andere Darstellung als das erste IR-Spektrum ({mode}), nicht gezeigt (nie umgerechnet): {names}",
                       "Other display than the first IR spectrum ({mode}), not shown (never converted): {names}"),
    "cmp_ir_mode_T": ("Transmission", "transmittance"),
    "cmp_ir_mode_A": ("Absorbanz", "absorbance"),
    "cmp_epr_no_nu": ("Ohne Mikrowellenfrequenz in der Datei (keine g-Achse, keine Skalierung), nicht gezeigt: {names}",
                      "No microwave frequency in the file (no g axis, no scaling), not shown: {names}"),
    "cmp_epr_other_nu": ("Andere Mikrowellenfrequenz als das erste Spektrum ({nu} GHz), nicht gezeigt (nie still "
                         "gemischt; „Frequenz angleichen“ oder g-Achse): {names}",
                         "Other microwave frequency than the first spectrum ({nu} GHz), not shown (never mixed "
                         "silently; “Scale to frequency” or g axis): {names}"),
    "cmp_si": ("Gesamt-SI", "Combined SI"),
    "cmp_si_on": ("Aufnehmen", "Include"),
    "cmp_si_on_tip": ("Vergleich in die Gesamt-SI des Projekts aufnehmen (Abbildung mit „Figure Sn“, Tabelle mit "
                      "„Table Sn“), im gewählten Kapitel nach den Verbindungen",
                      "Include the comparison in the project's combined SI (figure with “Figure Sn”, table with "
                      "“Table Sn”), in the chosen chapter after the compounds"),
    "cmp_si_heading_tip": ("Überschrift des eigenen Kapitels am Ende der Gesamt-SI (leer: Name des Vergleichs)",
                           "Heading of the own chapter at the end of the combined SI (empty: name of the comparison)"),
    # UV-Vis-Kinetik (tabs/uvkin.py)
    "uvkin_spectra": ("Spektren", "Spectra"),
    "uvkin_series": ("Reihe", "Series"),
    "uvkin_series_tip": ("Reihe, zu der das Spektrum gehört (z. B. Konzentration), frei wählbar. Vorbelegt nur, wenn der "
                         "Probenname eine Konzentration eindeutig nennt; ohne Reihe wird die Zeile nicht ausgewertet.",
                         "Series the spectrum belongs to (e.g. concentration), free text. Prefilled only when the sample "
                         "name states a concentration unambiguously; rows without a series are not evaluated."),
    "uvkin_time": ("Aufnahme", "Recorded"),
    "uvkin_time_tip": ("Aufnahmezeit aus der Messdatei (Cary-CSV „Collection Time“); „–“: die Datei nennt keine Zeit "
                       "(.DSW/.BSW, andere Exporte). Nie aus Dateinamen oder Dateidatum.",
                       "Acquisition time from the measurement file (Cary CSV “Collection Time”); “–”: the file states no "
                       "time (.DSW/.BSW, other exports). Never from file names or file dates."),
    "uvkin_sel": ("Auswahl", "Selection"),
    "uvkin_series_ph": ("Z. B. 0.5 mM", "E.g. 0.5 mM"),
    "uvkin_series_apply": ("Für die Auswahl setzen", "Set for Selection"),
    "uvkin_series_apply_tip": ("Reihe für alle markierten Zeilen der Tabelle setzen (Strg/Shift-Klick markiert mehrere).",
                               "Set the series for all selected rows of the table (Ctrl/Shift-click selects several)."),
    "uvkin_eval": ("Auswertung", "Evaluation"),
    "uvkin_view_spectra": ("Spektren über die Zeit", "Spectra over time"),
    "uvkin_view_trace": ("Absorbanz gegen Zeit", "Absorbance against time"),
    "uvkin_view_tip": ("Spektren einer Reihe im Farbverlauf der Zeit, oder die Absorbanz bei λ aller Reihen gegen die Zeit "
                       "seit ihrem ersten Spektrum.",
                       "Spectra of one series coloured along time, or the absorbance at λ of all series against the time "
                       "since their first spectrum."),
    "uvkin_series_pick_tip": ("Reihe, deren Spektren die Abbildung zeigt.", "Series whose spectra the figure shows."),
    "uvkin_lam": ("Wellenlänge", "Wavelength"),
    "uvkin_lam_tip": ("Wellenlänge, bei der die Absorbanz abgelesen wird (ganzzahlig). auto: Maximum des ersten Spektrums "
                      "der ersten Reihe im gezeigten Bereich (ab 300 nm).",
                      "Wavelength at which the absorbance is read (integer). auto: maximum of the first spectrum of the "
                      "first series within the shown range (from 300 nm)."),
    "uvkin_win": ("Maximum ±", "Maximum ±"),
    "uvkin_win_long": ("Maximum im Bereich ± n nm", "Maximum within ± n nm"),
    "uvkin_win_tip": ("aus: Wert genau bei der Wellenlänge (linear interpoliert). Sonst das Maximum jedes Spektrums im "
                      "Bereich λ ± n nm (folgt einer leicht wandernden Bande).",
                      "off: value exactly at the wavelength (linearly interpolated). Otherwise the maximum of each spectrum "
                      "within λ ± n nm (follows a slightly shifting band)."),
    "uvkin_y": ("y-Achse", "y axis"),
    "uvkin_y_abs": ("Absorbanz wie gemessen", "Absorbance as measured"),
    "uvkin_y_rel": ("Relativ zum ersten Spektrum [%]", "Relative to the first spectrum [%]"),
    "uvkin_unit": ("Zeiteinheit", "Time unit"),
    "uvkin_fit_tip": ("Je Reihe A(t) = A0·exp(−k·t) an die gemessenen Absorbanzen (kleinste Quadrate, 95-%-Intervall); "
                      "ab drei Punkten. Steigt die Reihe, ist k < 0 und es gibt keine Halbwertszeit.",
                      "Per series A(t) = A0·exp(−k·t) fitted to the measured absorbances (least squares, 95% interval); "
                      "from three points. If the series rises, k < 0 and there is no half-life."),
    "uvkin_cap_tip": ("Bildunterschrift für den SI-Export.", "Caption for the SI export."),
    "uvkin_results_none": ("Noch keine Reihe mit Aufnahmezeiten.", "No series with acquisition times yet."),
    "uvkin_rel_col": ("Relativ [%]", "Relative [%]"),
    "uvkin_read_fail": ("Nicht gelesen:\n{files}", "Not read:\n{files}"),
    "uvkin_missing": ("Datei fehlt oder ist nicht lesbar.", "File missing or unreadable."),
    "uvkin_no_series": ("{n} Spektren ohne Reihe werden nicht ausgewertet – Reihe in der Tabelle oder unter „Auswahl“ "
                        "eintragen.",
                        "{n} spectra without a series are not evaluated – enter the series in the table or under "
                        "“Selection”."),
    "uvkin_gone": ("{n} Spektren: Datei fehlt (verschoben oder gelöscht).", "{n} spectra: file missing (moved or deleted)."),
    "uvkin_untimed": ("{n} Spektren ohne Aufnahmezeit in der Datei fehlen in dieser Ansicht.",
                      "{n} spectra without an acquisition time in the file are left out of this view."),
    "uvkin_fit_short": ("Reihe {s}: {n} Punkte – kein Fit (mindestens drei nötig).",
                        "Series {s}: {n} points – no fit (at least three needed)."),
    "uvkin_no_time": ("Keine Reihe hat Spektren mit Aufnahmezeit – die Ansicht „Spektren über die Zeit“ zeigt sie.",
                      "No series has spectra with an acquisition time – the view “Spectra over time” shows them."),
    "uvkin_sum_none": ("keine Spektren mit Aufnahmezeit", "no spectra with acquisition time"),
    "uvkin_sum_rise": ("Absorbanz steigt (k < 0): keine Halbwertszeit", "absorbance rises (k < 0): no half-life"),
    "uvkin_sum_nofit": ("kein Fit (weniger als drei Punkte)", "no fit (fewer than three points)"),
    "uvkin_col_a0": ("A (Anfang)", "A (start)"),
    "uvkin_col_a1": ("A (Ende)", "A (end)"),
    "uvkin_col_rest": ("Rest [%]", "Remaining [%]"),
    "uvkin_col_dur": ("Dauer", "Duration"),
    "uvkin_col_n": ("Spektren", "Spectra"),
    "uvkin_col_ci": ("95 % (k)", "95% (k)"),
    "uvkin_kpi_rest": ("Rest {s}", "Remaining {s}"),
    # UV-Vis-Titration im Kinetik-Tab (Spektren gegen Äquivalente)
    "uvtit_eq_col": ("Äq.", "Equiv."),
    "uvtit_eq_tip": ("Zugegebene Äquivalente des Reagenz (z. B. Oxidationsmittel) für die Titration; vorgeschlagen, wenn "
                     "der Name eindeutig „0.5eq“, „1,5 equiv“ o. ä. nennt. Zeilen mit Äquivalenten brauchen keine Reihe.",
                     "Equivalents of the reagent added (e.g. oxidant) for the titration; suggested when the name clearly "
                     "says “0.5eq”, “1.5 equiv” or similar. Rows with equivalents need no series."),
    "uvtit_view_titr": ("Titration: Spektren", "Titration: spectra"),
    "uvtit_view_titr_trace": ("Titration: Absorbanz gegen Äq.", "Titration: absorbance against equiv."),
    "uvtit_tol": ("Isosbest. Punkte", "Isosbestic points"),
    "uvtit_tol_long": ("Toleranz für isosbestische Punkte", "Tolerance for isosbestic points"),
    "uvtit_tol_tip": ("Ein isosbestischer Punkt wird nur markiert, wo alle Spektren innerhalb dieser Spannweite (Absorbanz, "
                      "max − min) übereinstimmen und sich die Änderung zwischen erstem und letztem Spektrum umkehrt; sonst "
                      "keiner. aus: keine Markierung.", "An isosbestic point is only marked where all spectra agree within "
                      "this range (absorbance, max − min) and the change between the first and last spectrum reverses; "
                      "otherwise none. off: no marking."),
    "uvtit_col_spread": ("Spannweite", "Spread"),
    "uvtit_none": ("Keine Zeile mit Äquivalenten – in der Tabelle in der Spalte „Äq.“ eintragen.",
                   "No row with equivalents – enter them in the “Equiv.” column of the table."),
    "uvtit_lam_out": ("{lam} nm liegt außerhalb der Spektren.", "{lam} nm is outside the spectra."),
    "uvtit_kpi_n": ("Spektren", "Spectra"),
    "uvtit_kpi_none": ("keiner", "none"),
    "uvkin_cap_reagent": ("Reagenz", "Reagent"),
    "uvkin_cap_reagent_ph": ("Titration, z. B. NOSbF6", "Titration, e.g. NOSbF6"),
    # -- TD-DFT-Tabelle im Overlay (Paket A 1.2.0) --------------------------------------------------------
    "tddft_tab_card": ("TD-DFT-Tabelle", "TD-DFT Table"),
    "tddft_tab_card_tip": ("Welche Anregungen der TD-DFT-Rechnungen im Reiter „Anregungen“ und in der SI stehen",
                           "Which TD-DFT excitations appear on the “Excitations” page and in the SI"),
    "tddft_tab_page": ("Anregungen", "Excitations"),
    "tddft_tab_f": ("f\u200b ab", "f\u200b from"),          # \u200b: f kursiv (STYLE.QTY)
    "tddft_tab_f_tip": ("Nur Zustände mit Oszillatorstärke f ab diesem Wert; „Aus“ = alle Zustände",
                        "Only states with oscillator strength f at or above this value; “Off” = all states"),
    "tddft_tab_w": ("Anteile ab", "Contributions from"),
    "tddft_tab_w_tip": ("Hauptanteile (Orbital → Orbital) ab diesem Gewicht in der Tabelle",
                        "Main contributions (orbital → orbital) from this weight on in the table"),
    "tddft_tab_range": ("Nur λ-Bereich des Bildes", "Only λ range of the figure"),
    "tddft_tab_range_tip": ("Nur Zustände, deren Strich im gezeigten Bereich der Abbildung liegt (mit Verschiebung)",
                            "Only states whose stick lies in the shown range of the figure (with shift)"),
    "tddft_tab_si": ("In die SI (Word)", "In the SI (Word)"),
    "tddft_tab_si_tip": ("Tabelle der Anregungen im SI-Export nach den Abbildungen bzw. im Kapitel Rechnungen",
                         "Table of excitations in the SI export after the figures or in the computational chapter"),
    "tddft_tab_none": ("Keine TD-DFT-Rechnung: in der Karte Kurven über „TD-DFT“ hinzufügen",
                       "No TD-DFT calculation: add one with “TD-DFT” in the Curves card"),
    "tddft_tab_col_calc": ("Rechnung", "Calculation"),
    "tddft_tab_col_state": ("Zustand", "State"),
    "tddft_tab_col_trans": ("Übergang", "Transition"),
    "tddft_tab_col_weight": ("Gewicht [%]", "Weight [%]"),
    "tddft_tab_count": ("{n} von {m} Zuständen gezeigt (Schwelle und Bereich links in der Karte TD-DFT-Tabelle).",
                        "{n} of {m} states shown (threshold and range in the TD-DFT Table card on the left)."),
    "tddft_tab_rule_printed": ("Hauptanteile ab {w} %: Gewichte der Einfachanregungen wie in der Ausgabe gedruckt.",
                               "Main contributions from {w}%: weights of the single excitations as printed in the output."),
    "tddft_tab_rule_2c2": ("Hauptanteile ab {w} %: Gewicht = 2c² aus den gedruckten Koeffizienten c (geschlossene Schale).",
                           "Main contributions from {w}%: weight = 2c² from the printed coefficients c (closed shell)."),
    "tddft_tab_rule_c2": ("Hauptanteile ab {w} %: Gewicht = c² je Spin aus den gedruckten Koeffizienten c (offene Schale).",
                          "Main contributions from {w}%: weight = c² per spin from the printed coefficients c (open shell)."),
    "tddft_tab_noparts": ("Eine Ausgabe enthält keine Zusammensetzung der Zustände (oder SOC/Spin-Flip): dort ohne Anteile.",
                          "One output has no state composition (or SOC/spin flip): no contributions there."),
    "tddft_tab_shift": ("Energien ohne die Verschiebung der Abbildung ({s} eV).",
                        "Energies without the shift of the figure ({s} eV)."),
    # -- IR berechnet gegen gemessen (Paket B 1.2.0) ------------------------------------------------------
    "ir_calc_card": ("IR-Rechnung", "IR Calculation"),
    "ir_calc_card_tip": ("Frequenzrechnung (ORCA/Gaussian) mit IR-Intensitäten über dem gemessenen Spektrum",
                         "Frequency calculation (ORCA/Gaussian) with IR intensities over the measured spectrum"),
    "ir_calc_page": ("IR-Rechnung", "IR Calculation"),
    "ir_calc_file": ("Rechnung", "Calculation"),
    "ir_calc_scale": ("Skalierung", "Scaling"),
    "ir_calc_scale_tip": ("Faktor für die berechneten Frequenzen; hängt von Methode und Basis ab, deshalb hier selbst "
                          "eintragen (Vorgabe 1.000 = unskaliert)",
                          "Factor for the calculated frequencies; it depends on method and basis set, so enter it here "
                          "yourself (default 1.000 = unscaled)"),
    "ir_calc_fwhm": ("Verbreiterung", "Broadening"),
    "ir_calc_fwhm_tip": ("Lorentz-Profile mit dieser Halbwertsbreite; „Aus“ = Linienspektrum",
                         "Lorentzian profiles with this full width at half maximum; “Off” = line spectrum"),
    "ir_calc_tol": ("Toleranz", "Tolerance"),
    "ir_calc_tol_tip": ("Automatisch zugeordnet wird nur, was eindeutig ist: genau eine berechnete Mode (ab 5 % der "
                        "stärksten) innerhalb ± Toleranz, und sie liegt nur bei dieser Bande; „Aus“ = nur von Hand",
                        "Assigned automatically only when unique: exactly one calculated mode (from 5% of the strongest) "
                        "within ± tolerance, and it lies only at this band; “Off” = manual only"),
    "ir_calc_band": ("Bande", "Band"),
    "ir_calc_band_tip": ("Gemessene Bande für die Zuordnung von Hand", "Measured band for a manual assignment"),
    "ir_calc_mode": ("Mode", "Mode"),
    "ir_calc_mode_tip": ("Berechnete Mode (skaliert), die nächsten zuerst", "Calculated mode (scaled), nearest first"),
    "ir_calc_mode_item": ("{w} cm⁻¹ · {i} km mol⁻¹", "{w} cm⁻¹ · {i} km mol⁻¹"),
    "ir_calc_pair": ("Zuordnen", "Assign"),
    "ir_calc_unpair": ("Lösen", "Unassign"),
    "ir_calc_si": ("In die SI (Word)", "In the SI (Word)"),
    "ir_calc_si_tip": ("Tabelle der zugeordneten Banden im SI-Export", "Table of the assigned bands in the SI export"),
    "ir_calc_col_meas": ("ṽ gemessen [cm⁻¹]", "ṽ measured [cm⁻¹]"),
    "ir_calc_col_calc": ("ṽ berechnet [cm⁻¹]", "ṽ calculated [cm⁻¹]"),
    "ir_calc_col_how": ("Zuordnung", "Assignment"),
    "ir_calc_how_manual": ("Von Hand", "Manual"),
    "ir_calc_how_auto": ("Eindeutig", "Unique"),
    "ir_calc_none": ("Keine Rechnung: in der Karte IR-Rechnung eine Frequenzrechnung wählen",
                     "No calculation: choose a frequency calculation in the IR Calculation card"),
    "ir_calc_info": ("{n} berechnete Moden, skaliert mit {s}; automatisch nur eindeutige Paare (Moden ab {pct} % der "
                     "stärksten), Δṽ = gemessen − berechnet.",
                     "{n} calculated modes, scaled by {s}; automatic only for unique pairs (modes from {pct}% of the "
                     "strongest), Δṽ = measured − calculated."),
    "ir_calc_mad": ("{n} Banden zugeordnet, mittlere |Δṽ| = {d} cm⁻¹.", "{n} bands assigned, mean |Δṽ| = {d} cm⁻¹."),
    "ir_calc_imag": ("Imaginäre Frequenzen der Rechnung: {n} – nicht im Spektrum.",
                     "Imaginary frequencies of the calculation: {n} – not in the spectrum."),
    "ir_calc_scale_hint": ("Skalierung 1.000: ungeskalierte Frequenzen. Den Faktor zum Rechenniveau selbst eintragen.",
                           "Scaling 1.000: unscaled frequencies. Enter the factor for the level of theory yourself."),
    "ir_calc_bad": ("Rechnung nicht lesbar: {e}", "Calculation not readable: {e}"),
    "ir_calc_unreadable": ("Die IR-Rechnung ist nicht lesbar (Hinweis im Reiter IR-Rechnung).",
                           "The IR calculation cannot be read (note on the IR Calculation page)."),
    "ir_calc_out_of_range": ("Keine berechnete Mode im gezeigten Bereich.", "No calculated mode in the shown range."),
    "ir_calc_no_freq": ("keine Frequenzen in der Ausgabe", "no frequencies in the output"),
    "ir_calc_no_int": ("keine IR-Intensitäten in bekanntem Format (ORCA 5/6 „IR SPECTRUM“ mit km/mol, Gaussian „IR Inten“)",
                       "no IR intensities in a known format (ORCA 5/6 “IR SPECTRUM” with km/mol, Gaussian “IR Inten”)"),
    "ir_calc_mismatch": ("IR-Intensitäten passen nicht zu den Frequenzen", "IR intensities do not match the frequencies"),
    "ir_calc_kpi": ("IR zugeordnet", "IR assigned"),
    # -- Packungsbild im X-Ray-Tab (Paket C 1.2.0) --------------------------------------------------------
    "xray_pack_card": ("Packung", "Packing"),
    "xray_pack_card_tip": ("Elementarzelle mit ihrem Inhalt statt des einzelnen Moleküls",
                           "Unit cell with its content instead of the single molecule"),
    "xray_pack_fig": ("Abbildung", "Figure"),
    "xray_pack_fig_mol": ("Molekül", "Molecule"),
    "xray_pack_fig_pack": ("Packung (Elementarzelle)", "Packing (unit cell)"),
    "xray_pack_axis": ("Blickrichtung", "View"),
    "xray_pack_axis_tip": ("Blick entlang einer Zellachse; Drehen mit der Maus ergibt „frei“",
                           "View along a cell axis; rotating with the mouse gives “free”"),
    "xray_pack_along": ("Entlang {a}", "Along {a}"),
    "xray_pack_free": ("Frei gedreht", "Freely rotated"),
    "xray_pack_rule": ("Moleküle", "Molecules"),
    "xray_pack_rule_tip": ("Welche ganzen Moleküle gezeigt werden: Schwerpunkt in der Zelle oder mindestens ein Atom "
                           "in der Zelle. Partner gezeigter Abstände kommen immer dazu.",
                           "Which whole molecules are shown: centroid in the cell or at least one atom in the cell. "
                           "Partners of shown distances are always added."),
    "xray_pack_rule_centroid": ("Schwerpunkt in der Zelle", "Centroid in the cell"),
    "xray_pack_rule_touch": ("Berühren die Zelle", "Touching the cell"),
    "xray_pack_color": ("Farbe Abstände", "Distance colour"),
    "xray_pack_h": ("H-Atome", "H atoms"),
    "xray_pack_si": ("In die SI (Word)", "In the SI (Word)"),
    "xray_pack_si_tip": ("Packungsbild mit Unterschrift nach dem Molekülbild in der SI und im Export",
                         "Packing figure with caption after the molecule figure in the SI and the export"),
    "xray_pack_contacts": ("Abstände in der Packung", "Distances in the Packing"),
    "xray_pack_contacts_tip": ("Abstände zwischen Molekülen: Vorschläge ankreuzen oder zwei Atome im Packungsbild wählen",
                               "Distances between molecules: tick suggestions or pick two atoms in the packing figure"),
    "xray_pack_tol": ("Toleranz vdW", "vdW tolerance"),
    "xray_pack_tol_tip": ("Vorschlag, wenn d ≤ Summe der van-der-Waals-Radien (Bondi) + Toleranz; je Molekülpaar der "
                          "kürzeste Kontakt",
                          "Suggested when d ≤ sum of the van der Waals radii (Bondi) + tolerance; the shortest contact "
                          "per molecule pair"),
    "xray_pack_cg": ("Cg···Cg bis", "Cg···Cg up to"),
    "xray_pack_cg_tip": ("Ringpaare (ebene 5- bis 7-Ringe) mit Schwerpunktabstand bis zu diesem Wert",
                         "Ring pairs (planar 5- to 7-membered rings) with centroid distance up to this value"),
    "xray_pack_ang": ("Parallel bis", "Parallel up to"),
    "xray_pack_ang_tip": ("Ebenenabstand nur, wenn die Ringebenen höchstens so weit gegeneinander geneigt sind; sonst "
                          "wird der Winkel genannt",
                          "Interplanar distance only if the ring planes are inclined by at most this angle; otherwise "
                          "the angle is given"),
    "xray_pack_heavy": ("Nur Nicht-H-Atome", "Non-H atoms only"),
    "xray_pack_heavy_tip": ("Atom-Atom-Kontakte ohne Wasserstoff vorschlagen", "Suggest atom–atom contacts without hydrogen"),
    "xray_pack_tbl_tip": ("Häkchen = Abstand im Packungsbild, in der Unterschrift und der Tabelle",
                          "Tick = distance in the packing figure, the caption and the table"),
    "xray_pack_none": ("Keine Kontakte unter der Summe der vdW-Radien + Toleranz",
                       "No contacts below the sum of the vdW radii + tolerance"),
    "xray_pack_col_kind": ("Art", "Type"),
    "xray_pack_col_contact": ("Kontakt", "Contact"),
    "xray_pack_col_angle": ("Winkel [°]", "Angle [°]"),
    "xray_pack_col_slip": ("Versatz [Å]", "Slip [Å]"),
    "xray_pack_col_sym": ("Symmetrie", "Symmetry"),
    "xray_pack_kind_atoms": ("Atom···Atom", "atom···atom"),
    "xray_pack_kind_cent": ("Cg···Cg", "Cg···Cg"),
    "xray_pack_kind_plane": ("Ebene–Ebene", "plane–plane"),
    "xray_pack_add": ("Zwei gewählte Atome", "Two picked atoms"),
    "xray_pack_add_tip": ("Abstand zwischen zwei im Packungsbild angeklickten Atomen verschiedener Moleküle hinzufügen",
                          "Add the distance between two atoms of different molecules picked in the packing figure"),
    "xray_pack_add_need": ("Im Packungsbild genau zwei Atome anklicken.", "Pick exactly two atoms in the packing figure."),
    "xray_pack_add_same": ("Die beiden Atome gehören zum selben Molekül (dafür: Messen).",
                           "Both atoms belong to the same molecule (use Measure for that)."),
    "xray_pack_clear": ("Alle abwählen", "Untick all"),
    "xray_pack_page": ("Abstände", "Distances"),
    "xray_pack_res_none": ("Keine Abstände gewählt: links in der Karte „Abstände in der Packung“ ankreuzen",
                           "No distances chosen: tick them in the card “Distances in the Packing” on the left"),
    # 1.2.0-Review (x-ray/SI)
    "fixx_pxrd_no_u": ("Atome ohne Auslenkungsparameter in der CIF: {n} ({atoms}); ohne Temperaturfaktor gerechnet (U "
                       "= 0, kein Wert angenommen) – Intensitäten bei hohen Winkeln zu hoch. Steht im Methodentext.",
                       "Atoms without displacement parameters in the CIF: {n} ({atoms}); calculated without a "
                       "temperature factor (U = 0, no value assumed) – intensities at high angles too high. Stated in "
                       "the methods text."),
    "xray_pack_cg_def": ("Cg{n}: Schwerpunkt von {atoms}", "Cg{n}: centroid of {atoms}"),
    "xray_pack_calc_note": ("Abstände aus den Atomkoordinaten gerechnet, ohne Standardabweichung (keine in der CIF); "
                            "Versatz = Abstand der Schwerpunkte parallel zur Ebene des ersten Rings.",
                            "Distances calculated from the atomic coordinates, without s.u. (none in the CIF); slip = "
                            "centroid offset parallel to the plane of the first ring."),
    "xray_pack_bondi": ("van-der-Waals-Radien: {ref}.", "van der Waals radii: {ref}."),
    "xray_pack_truncated": ("Polymer/Netzwerk: das Modell wurde abgebrochen, die Packung ist unvollständig.",
                            "Polymer/network: the model was truncated, the packing is incomplete."),
    # Raman im Tab IR + EA (1.2.0)
    "raman_card": ("Raman", "Raman"),
    "raman_card_tip": ("Raman-Spektrum als Textdatei (Spalten Raman-Verschiebung und Intensität): eigene Peakliste, "
                       "SI-Zeile und Abbildung, wahlweise unter dem IR-Spektrum",
                       "Raman spectrum as a text file (columns Raman shift and intensity): own peak list, SI line and "
                       "figure, optionally below the IR spectrum"),
    "raman_file": ("Raman-Spektrum", "Raman spectrum"),
    "raman_flt": ("Textspalten (*.txt *.csv *.dat *.xy *.asc)", "Text columns (*.txt *.csv *.dat *.xy *.asc)"),
    "raman_exc": ("Anregung", "Excitation"),
    "raman_exc_tip": ("Wellenlänge des Lasers (λexc), steht in der SI-Zeile und der Bildunterschrift",
                      "Laser wavelength (λexc), given in the SI line and the caption"),
    "raman_prom_tip": ("Mindesthöhe eines Raman-Peaks über seiner Umgebung, relativ zum stärksten Peak im Bereich",
                       "Minimum height of a Raman peak above its surroundings, relative to the strongest peak in the range"),
    "raman_view": ("Abbildung", "Figure"),
    "raman_view_tip": ("Was die Abbildung des Tabs zeigt: IR, Raman oder beide übereinander (gemeinsame Wellenzahlachse)",
                       "What the figure of the tab shows: IR, Raman or both stacked (common wavenumber axis)"),
    "raman_view_ir": ("IR", "IR"),
    "raman_view_raman": ("Raman", "Raman"),
    "raman_view_stack": ("IR und Raman übereinander", "IR and Raman stacked"),
    "raman_calc": ("Raman-Rechnung", "Raman calculation"),
    "raman_calc_tip": ("Berechnetes Raman-Spektrum (Aktivitäten) aus der Rechnung der Karte IR-Rechnung, mit deren "
                       "Skalierung und Verbreiterung; nur wenn die Ausgabe Raman-Aktivitäten enthält",
                       "Calculated Raman spectrum (activities) from the calculation of the card IR Calculation, with its "
                       "scaling and broadening; only if the output contains Raman activities"),
    "raman_none": ("Kein Raman-Spektrum geladen", "No Raman spectrum loaded"),
    "raman_copy": ("Raman-Zeile kopieren (für Word)", "Copy Raman line (for Word)"),
    "raman_line": ("Raman-Zeile für die SI", "Raman line for the SI"),
    "raman_calc_none": ("Die Rechnung enthält keine Raman-Aktivitäten (ORCA „RAMAN SPECTRUM“, Gaussian „Raman Activ“): "
                        "kein berechnetes Raman-Spektrum.",
                        "The calculation contains no Raman activities (ORCA “RAMAN SPECTRUM”, Gaussian “Raman Activ”): "
                        "no calculated Raman spectrum."),
    "raman_unreadable": ("Das Raman-Spektrum ist nicht lesbar.", "The Raman spectrum cannot be read."),
    "raman_stack_no_ir": ("Kein IR-Spektrum: nur Raman gezeigt.", "No IR spectrum: Raman shown alone."),
    "raman_view_no_data": ("Kein Raman-Spektrum: IR gezeigt.", "No Raman spectrum: IR shown."),
    "raman_xy_binary": ("keine Textdatei (Binärformat eines Geräts wird nicht gelesen; als Text/CSV exportieren)",
                        "not a text file (instrument binary formats are not read; export as text/CSV)"),
    "raman_xy_short": ("weniger als {n} Zeilen mit zwei Zahlen", "fewer than {n} lines with two numbers"),
    # Fehlerbehebung 1.2.0, Leser (formats/xy, decay, calc; tabs/fluo_tau)
    "fixr_mixed_decimal": ("Zahlenformat nicht eindeutig: Zeile {line} passt nicht zu Dezimalzeichen und Trennern der "
                           "übrigen Zahlenzeilen (Dezimalpunkt und -komma gemischt?)",
                           "ambiguous number format: line {line} does not match the decimal mark and separators of the "
                           "other numeric lines (decimal point and comma mixed?)"),
    "fixr_decay_row": ("Zeile {line} hat nicht {n} endliche Zahlen wie die erste Datenzeile",
                       "line {line} does not have {n} finite numbers like the first data line"),
    "fixr_epr_gauss_overflow": ("Mulliken-Spinpopulation in Zeile {line} nicht lesbar (Überlauf „****“ in der "
                                "Gaussian-Ausgabe).",
                                "Mulliken spin population in line {line} not readable (overflow “****” in the Gaussian "
                                "output)."),
    "fixr_epr_gauss_count": ("Hyperfeintabelle der Gaussian-Ausgabe unvollständig: {n} von {m} Kernen (Überlauf „****“?).",
                             "Hyperfine table of the Gaussian output incomplete: {n} of {m} nuclei (overflow “****”?)."),
    "fixr_overflow": ("Zeile {line}: Überlauf „****“ statt einer Zahl", "line {line}: overflow “****” instead of a number"),
    "fixr_decay_unit": ("⚠ Keine Zeiteinheit im Kopf der Zeitspalte: Zeit in {u} gelesen – unter „Zeit in der Datei“ "
                        "prüfen.", "⚠ No time unit in the header of the time column: time read in {u} – check “Time in "
                        "file”."),
    "fixr_irf_unit": ("IRF-Datei ohne Zeiteinheit im Spaltenkopf: wie die Abklingkurve in {u} gelesen.",
                      "IRF file without time unit in the column header: read in {u} like the decay."),
    # Pulverdiffraktogramm im Tab X-Ray (1.2.0)
    "pxrd_card": ("Pulverdiffraktogramm (PXRD)", "Powder Pattern (PXRD)"),
    "pxrd_card_tip": ("Pulverdiffraktogramm aus der Einkristallstruktur berechnen und gegen ein gemessenes legen "
                      "(Rechnung, kein Rietveld-Fit)",
                      "Calculate the powder pattern from the single-crystal structure and compare it with a measured "
                      "one (calculation, no Rietveld fit)"),
    "pxrd_file": ("Messung", "Measured"),
    "pxrd_flt": ("Diffraktogramm (*.xy *.xye *.txt *.csv *.dat)", "Diffractogram (*.xy *.xye *.txt *.csv *.dat)"),
    "pxrd_not_2theta": ("erste Spalte ist kein 2θ in Grad (0–180°)", "first column is not 2θ in degrees (0–180°)"),
    "pxrd_anode": ("Strahlung", "Radiation"),
    "pxrd_anode_item": ("{a} Kα ({l1}/{l2} Å)", "{a} Kα ({l1}/{l2} Å)"),
    "pxrd_anode_tip": ("Anode der Pulvermessung; Kα1/Kα2 nach International Tables Vol. C",
                       "Anode of the powder measurement; Kα1/Kα2 from International Tables Vol. C"),
    "pxrd_ka2": ("Kα2 (halbe Intensität)", "Kα2 (half intensity)"),
    "pxrd_ka2_tip": ("Kα1/Kα2-Dublett rechnen (Kα2/Kα1 = 0.5); aus = nur Kα1 (monochromatisierte Messung)",
                     "Calculate the Kα1/Kα2 doublet (Kα2/Kα1 = 0.5); off = Kα1 only (monochromated measurement)"),
    "pxrd_fwhm": ("Halbwertsbreite", "FWHM"),
    "pxrd_fwhm_tip": ("Halbwertsbreite der Reflexe in ° 2θ (Pseudo-Voigt, für alle Reflexe gleich)",
                      "Full width at half maximum of the reflections in ° 2θ (pseudo-Voigt, the same for all)"),
    "pxrd_eta": ("Lorentz-Anteil η", "Lorentz fraction η"),
    "pxrd_eta_tip": ("Anteil des Lorentz-Profils im Pseudo-Voigt (0 = Gauß, 1 = Lorentz)",
                     "Fraction of the Lorentzian in the pseudo-Voigt profile (0 = Gaussian, 1 = Lorentzian)"),
    "pxrd_range": ("Bereich 2θ", "Range 2θ"),
    "pxrd_zero": ("Nullpunkt", "Zero point"),
    "pxrd_zero_tip": ("Verschiebt die berechneten Reflexe um diesen Wert in 2θ (Nullpunktfehler der Messung); wird "
                      "nicht angepasst, nur eingegeben",
                      "Shifts the calculated reflections by this value in 2θ (zero-point error of the measurement); "
                      "entered, never fitted"),
    "pxrd_hint": ("Struktur bei {t} bestimmt. Pulver bei Raumtemperatur: Reflexe meist bei etwas kleinerem 2θ "
                  "(Ausdehnung der Zelle); bevorzugte Orientierung ändert Intensitäten. Beides wird nicht korrigiert.",
                  "Structure determined at {t}. Powder at room temperature: reflections usually at slightly lower 2θ "
                  "(cell expansion); preferred orientation changes intensities. Neither is corrected."),
    "pxrd_meas_bad": ("Messung nicht lesbar: {e}", "Measurement not readable: {e}"),
    "pxrd_no_f0": ("Kein Atomformfaktor für {el}: keine Rechnung.", "No atomic scattering factor for {el}: no calculation."),
    "pxrd_fig_card": ("PXRD-Abbildung", "PXRD Figure"),
    "pxrd_view": ("Anordnung", "Arrangement"),
    "pxrd_stack": ("Gemessen oben, berechnet unten", "Measured above, calculated below"),
    "pxrd_overlay": ("Überlagert", "Overlaid"),
    "pxrd_c_meas": ("Farbe gemessen", "Colour measured"),
    "pxrd_c_calc": ("Farbe berechnet", "Colour calculated"),
    "pxrd_ticks": ("Reflexmarken", "Reflection ticks"),
    "pxrd_si": ("In die SI (Word)", "In the SI (Word)"),
    "pxrd_si_tip": ("Pulverdiffraktogramm mit Unterschrift und Methodensatz in der SI und im Export",
                    "Powder pattern with caption and methods sentence in the SI and the export"),
    "pxrd_page": ("PXRD", "PXRD"),
    "pxrd_none": ("Keine Struktur: links unter „Strukturen“ eine CIF hinzufügen",
                  "No structure: add a CIF under “Structures” on the left"),
    "pxrd_res_note": ("{n} Reflexe (Kα1) im Bereich; Formfaktoren: {src}. Skaliert auf das stärkste Maximum, nichts "
                      "angepasst.",
                      "{n} reflections (Kα1) in the range; scattering factors: {src}. Scaled to the strongest maximum, "
                      "nothing refined."),
    # HOMA (Paket A 1.2.0, X-Ray und DFT)
    "homa_card": ("Aromatizität (HOMA)", "Aromaticity (HOMA)"),
    "homa_card_tip": ("HOMA je Ring aus den Bindungslängen (ebene 5- bis 7-Ringe wie im Packungsbild). Bindungstypen "
                      "ohne Literaturparameter geben keinen Wert.",
                      "HOMA per ring from the bond lengths (planar 5- to 7-membered rings as in the packing figure). "
                      "Bond types without literature parameters give no value."),
    "homa_var": ("Parameter", "Parameters"),
    "homa_var_homa": ("HOMA (Krygowski 1993)", "HOMA (Krygowski 1993)"),
    "homa_var_homac": ("HOMAc (Arpa 2025)", "HOMAc (Arpa 2025)"),
    "homa_var_tip": ("HOMA: Krygowski, J. Chem. Inf. Comput. Sci. 1993 (CC, CN, CO, CP, CS, NN, NO). HOMAc: Arpa, "
                     "Stafström, Durbeej, J. Org. Chem. 2025 (nur CC, CN, NN, CO; aus CASPT2-Geometrien).",
                     "HOMA: Krygowski, J. Chem. Inf. Comput. Sci. 1993 (CC, CN, CO, CP, CS, NN, NO). HOMAc: Arpa, "
                     "Stafström, Durbeej, J. Org. Chem. 2025 (CC, CN, NN, CO only; from CASPT2 geometries)."),
    "homa_fig": ("Werte im Bild", "Values in figure"),
    "homa_fig_tip": ("HOMA in der Ringmitte; mit der Maus verschiebbar wie die Atomlabels",
                     "HOMA at the ring centre; can be dragged like the atom labels"),
    "homa_si": ("In die SI", "Into the SI"),
    "homa_si_tip": ("Tabelle der Ringe in die SI (Word) und als CSV in den Export",
                    "Table of the rings into the SI (Word) and as CSV into the export"),
    "homa_hint": ("{n} Ringe, davon {ok} mit HOMA", "{n} rings, {ok} of them with HOMA"),
    "homa_page": ("HOMA", "HOMA"),
    "homa_col_ring": ("Ring", "Ring"),
    "homa_col_note": ("Hinweis", "Note"),
    "homa_none": ("Keine ebenen 5- bis 7-Ringe in der gewählten Struktur",
                  "No planar 5- to 7-membered rings in the selected structure"),
    "homa_missing": ("Nicht parametrisiert: {bonds}", "Not parametrized: {bonds}"),
    # Satz unter der HOMA-Tabelle in der Oberfläche (die SI-Fußnote bleibt englisch, homa_view.method_sentence)
    "homa_method": ("{name} = 1 − (1/n) Σ α (R_opt − R_i)² mit R_opt und α je Bindungstyp aus {cite}; Bindungslängen R_i "
                    "aus {src}. EN und GEO (HOMA = 1 − EN − GEO; {engeo}) nur für Ringe mit einem einzigen Bindungstyp; "
                    "Ringe mit einem Bindungstyp ohne Parameter haben keinen Wert.",
                    "{name} = 1 − (1/n) Σ α (R_opt − R_i)² with R_opt and α per bond type from {cite}; bond lengths R_i "
                    "from {src}. EN and GEO (HOMA = 1 − EN − GEO; {engeo}) are given only for rings with a single bond "
                    "type; rings with a bond type without parameters have no value."),
    "homa_src_xray": ("den Atomkoordinaten", "the atomic coordinates"),
    "homa_src_calc": ("der berechneten Geometrie", "the calculated geometry"),
    # NTO (Paket B 1.2.0, Overlay)
    "nto_card": ("Übergangsorbitale (NTO)", "Transition Orbitals (NTO)"),
    "nto_card_tip": ("Natürliche Übergangsorbitale je Anregung aus der Rechnung zeigen (berechnet werden sie nicht): "
                     "ORCA-.nto als Molden (orca_2mkl) mit den Gewichten aus dem NTO-Block der Ausgabe, oder zwei Cubes "
                     "(Loch, Teilchen)",
                     "Show natural transition orbitals per excitation from the calculation (they are not computed "
                     "here): ORCA .nto as Molden (orca_2mkl) with the weights from the NTO block of the output, or two "
                     "cubes (hole, particle)"),
    "nto_state": ("Zustand", "State"),
    "nto_state_tip": ("Anregung der sichtbaren TD-DFT-Rechnungen; ● = NTO-Datei geladen",
                      "Excitation of the visible TD-DFT calculations; ● = NTO file loaded"),
    "nto_file": ("Datei", "File"),
    "nto_molden": ("Molden …", "Molden …"),
    "nto_molden_tip": ("NTO-Datei des Zustands als Molden (ORCA: name.sN.nto mit orca_2mkl umgewandelt); Paare und "
                       "Gewichte aus dem NTO-Block der TD-DFT-Ausgabe",
                       "NTO file of the state as Molden (ORCA: name.sN.nto converted with orca_2mkl); pairs and weights "
                       "from the NTO block of the TD-DFT output"),
    "nto_cubes": ("Cubes …", "Cubes …"),
    "nto_cubes_tip": ("Zwei Cube-Dateien eines Paars (Loch und Teilchen, z. B. orca_plot oder Gaussian cubegen); "
                      "Loch = kleinere MO-Nummer",
                      "Two cube files of one pair (hole and particle, e.g. orca_plot or Gaussian cubegen); hole = "
                      "lower MO number"),
    "nto_weight": ("Gewicht", "Weight"),
    "nto_weight_none": ("Keins", "None"),
    "nto_weight_tip": ("Nur für Cubes, deren Paar nicht im NTO-Block der Ausgabe steht: Gewicht wie in der Rechnung "
                       "angegeben (0 = keins zeigen)",
                       "Only for cubes whose pair is not in the NTO block of the output: weight as given by the "
                       "calculation (0 = show none)"),
    "nto_wmin": ("Paare ab", "Pairs from"),
    "nto_wmin_tip": ("Molden: Paare mit mindestens diesem Gewicht zeigen (höchstens vier)",
                     "Molden: show pairs with at least this weight (four at most)"),
    "nto_iso": ("Isowert", "Isovalue"),
    "nto_iso_auto": ("Auto ({p} % Dichte)", "Auto ({p}% density)"),
    "nto_iso_tip": ("Fester Isowert in a.u. für Loch und Teilchen; leer = Fläche umschließt 80 % der Orbitaldichte "
                    "(wie im DFT-Tab)",
                    "Fixed isovalue in a.u. for hole and particle; empty = surface encloses 80% of the orbital "
                    "density (as in the DFT tab)"),
    "nto_si": ("In die SI", "Into the SI"),
    "nto_si_tip": ("Bild und Unterschrift je Zustand mit NTO-Datei in die SI (Word) und in den Export",
                   "Figure and caption per state with an NTO file into the SI (Word) and the export"),
    "nto_page": ("NTO", "NTO"),
    "nto_none": ("Keine NTO-Datei zum gewählten Zustand: links in der Karte „Übergangsorbitale (NTO)“ laden",
                 "No NTO file for the chosen state: load one in the card “Transition Orbitals (NTO)” on the left"),
    "nto_cap_empty": ("Ohne NTO-Bild keine Bildunterschrift", "No caption without an NTO figure"),
    "nto_copy_tip": ("Bildunterschrift kopieren (für Word)", "Copy the caption (for Word)"),
    "nto_no_block": ("Die TD-DFT-Ausgabe enthält keinen NTO-Block (ORCA: %tddft DoNTO true end): ohne ihn sind Paare "
                     "und Gewichte unbekannt. Stattdessen zwei Cubes laden.",
                     "The TD-DFT output has no NTO block (ORCA: %tddft DoNTO true end): without it, pairs and weights "
                     "are unknown. Load two cubes instead."),
    "nto_no_match": ("Kein NTO-Block der Ausgabe passt eindeutig zur Energie dieses Zustands",
                     "No NTO block of the output matches the energy of this state unambiguously"),
    "nto_no_mo": ("Orbital {h} oder {p} fehlt in der Molden-Datei", "Orbital {h} or {p} is missing in the Molden file"),
    "nto_file_name": ("Hinweis: laut Ausgabe gehört zu diesem Zustand {f}", "Note: according to the output this state "
                      "belongs to {f}"),
    "nto_two_cubes": ("Bitte genau zwei Cubes wählen (Loch und Teilchen)", "Please pick exactly two cubes (hole and "
                      "particle)"),
    "nto_cube_geom": ("Die beiden Cubes haben verschiedene Geometrien", "The two cubes have different geometries"),
    "nto_missing": ("NTO-Datei fehlt", "NTO file missing"),
    "nto_weight_user": ("Gewicht von Hand eingegeben (nicht aus der Ausgabe)", "Weight entered by hand (not from the "
                        "output)"),
    # fixd_: Behebungen 1.2.0 (Projekt, Datenpaket, DFT)
    "dp_grp_pxrd": ("PXRD (Pulverdiffraktogramme)", "PXRD (powder patterns)"),
    "fixd_nbo_no_geom": ("Die NBO-Ausgabe enthält keine Geometrie: keine Abbildung, Tabellen und CSV wie gedruckt.",
                         "The NBO output contains no geometry: no figure; tables and CSV as printed."),
    "fixd_nics_plane": ("NICS: alle {n} Bq liegen in einer Ebene. 2D-Karten werden nicht dargestellt; für ein 3D-Gitter "
                        "alle Teilrechnungen laden.", "NICS: all {n} Bq lie in one plane. 2D maps are not shown; for a "
                        "3D grid load all partial calculations."),
    "fixd_nto_order": ("Ohne MO-Nummer (Dateiname „mo61a“ oder MO-Liste im Cube) ist unklar, welcher Cube das Loch ist. "
                       "Bitte Cubes mit Nummer wählen oder mit „hole“/„particle“ im Dateinamen.",
                       "Without an MO number (file name “mo61a” or MO list in the cube) it is unclear which cube is "
                       "the hole. Please choose cubes with a number or with “hole”/“particle” in the file name."),
}
# Fehlerbehebungen 1.2.0 (Gruppe Tabs: EPR, NMR, CV, Raman)
TEXTS.update({
    "fixt_epr_assign_bad": ("Zuordnung von {group} passt nicht mehr zur Simulation (anderes Element): ohne Beschriftung, "
                            "bitte neu zuordnen", "Assignment of {group} no longer matches the simulation (different "
                            "element): not labelled, please assign again"),
    "fixt_epr_spin_scale": ("Die Messungen unterscheiden sich in: {what}. Sind die Spektren nicht darauf normiert, sind "
                            "die Konzentrationen um dieses Verhältnis falsch; nicht umgerechnet.",
                            "The measurements differ in: {what}. If the spectra are not normalized for this, the "
                            "concentrations are wrong by that ratio; not corrected."),
    "fixt_epr_n_scans": ("Zahl der Scans", "number of scans"),
    "fixt_epr_gain_dB": ("Empfängerverstärkung", "receiver gain"),
    "fixt_epr_conv_ms": ("Konversionszeit", "conversion time"),
    "fixt_epr_spin_extra": ("Außerhalb der Kalibrierung (extrapoliert): {what}", "Outside the calibration range "
                            "(extrapolated): {what}"),
    "fixt_epr_spin_neg": ("Negative Konzentration (unter dem Achsenabschnitt): {what}", "Negative concentration (below "
                          "the intercept): {what}"),
    "fixt_epr_kin_rise": ("Intensität steigt (k < 0), keine Halbwertszeit: {what}", "Intensity increased (k < 0), no "
                          "half-life: {what}"),
    "fixt_nmr_count_multi_h": ("Mehrere H-Zahlen in einem Signal", "Several H counts in one signal"),
    "fixt_raman_exc_none": ("Nicht angegeben", "Not given"),
    "fixt_cv_acs_ref": ("Referenz", "Reference"),
    "fixt_cv_acs_ref_long": ("Referenzelektrode im Messaufbau", "Reference electrode of the setup"),
    "fixt_cv_acs_ref_ph": ("Z. B. Ag/AgNO₃ (0.01 M in MeCN)", "E.g. Ag/AgNO₃ (0.01 M in MeCN)"),
    "fixt_cv_conv_file": ("Stromkonvention der Datei (CONVENTION {v}) ist nicht die geprüfte (1 = anodisch positiv): "
                          "Vorzeichen der Ströme prüfen", "Current convention of the file (CONVENTION {v}) is not the "
                          "checked one (1 = anodic positive): check the sign of the currents"),
})
# r2a_: Fehlerbehebung Runde 2 vor 1.2.0 (Anzeige, Zahlenformat, Texte)
TEXTS.update({
    "r2a_calc_abnormal": ("Rechnung nicht normal beendet (abgebrochen oder Datei unvollständig): Geometrie bzw. Moden "
                          "können unvollständig sein, nicht übernommen.",
                          "calculation did not terminate normally (aborted or file incomplete): geometry or modes may "
                          "be incomplete, not used."),
    "r2a_nbo_no_lp": ("In der CML fehlen freie Elektronenpaare (lonePair): Formalladungen werden nicht gezeigt.",
                      "The CML lacks lone pairs (lonePair): formal charges are not shown."),
    "r2a_ea_mean_single": ("Mittel bzw. Einzelwert", "Average or single value"),
    "r2a_series_sample": ("Probe", "sample"),
    "cv_acs_n_ref": ("Referenzelektrode", "reference electrode"),
})
# Fehlerbehebungen 1.2.0, Runde 2 (Dateileser): abgelehnt statt still falsch/verkürzt oder roher Python-Text
TEXTS.update({
    "r2l_ir_incomplete": ("IR-Tabelle der ORCA-Ausgabe unvollständig (Datei abgeschnitten?): nicht gelesen.",
                          "IR table of the ORCA output incomplete (file truncated?): not read."),
    "r2l_ir_overflow": ("Frequenzen/IR-Intensitäten in Zeile {line} nicht lesbar (Überlauf „****“).",
                        "Frequencies/IR intensities in line {line} not readable (overflow “****”)."),
    "r2l_esd_line": ("{name}: Zeile {line} ist keine vollständige Zahlenzeile (abgeschnitten oder Störzeile): Datei "
                     "nicht gelesen.", "{name}: line {line} is not a complete row of numbers (truncated or corrupt): "
                     "file not read."),
    "r2l_tddft_row": ("TD-DFT-Tabelle: Zeile „{text}“ nicht lesbar (Überlauf „****“ oder fehlende Spalte).",
                      "TD-DFT table: row “{text}” not readable (overflow “****” or missing column)."),
    "r2l_tddft_incomplete": ("TD-DFT-Tabelle unvollständig: {n} Zustände gelesen{req}, Ausgabe abgeschnitten.",
                             "TD-DFT table incomplete: {n} states read{req}, output truncated."),
    "r2l_tddft_req": (" (NRoots {n})", " (NRoots {n})"),
    "r2l_epr_hfc_incomplete": ("Hyperfeinblock der ORCA-Ausgabe unvollständig (Rechnung nicht normal beendet): nicht "
                               "gelesen.", "Hyperfine block of the ORCA output incomplete (calculation did not "
                               "terminate normally): not read."),
    "r2l_epr_ascii_line": ("{name}: Zeile {line} („{text}“) passt nicht zu den übrigen Zahlenzeilen (gemischte "
                           "Dezimaltrenner, verschmolzene Zahlen oder Überlauf „****“): Datei nicht gelesen.",
                           "{name}: line {line} (“{text}”) does not match the other numeric rows (mixed decimal "
                           "separators, merged numbers or overflow “****”): file not read."),
    "r2l_dsw_incomplete": ("{name}: Cary-Datei unvollständig (abgeschnitten): Spektren oder ihre Angaben fehlen, nicht "
                           "gelesen.", "{name}: Cary file incomplete (truncated): spectra or their records are "
                           "missing, not read."),
    "r4_eclipse_layout": ("{name}: Aufbau des Cary-Eclipse-Exports nicht erkannt (Probennamen, Index der Z-Achse und "
                          "Datenspalten passen nicht zusammen): nicht gelesen.",
                          "{name}: layout of the Cary Eclipse export not recognized (sample names, Z-axis index and "
                          "data columns do not match): not read."),
    "r4_cary_no_data": ("{name}: Probe „{sample}“ ohne Datenspalten (Datei abgeschnitten oder anderer Aufbau): nicht "
                        "gelesen.", "{name}: sample “{sample}” has no data columns (file truncated or another layout): "
                        "not read."),
    "r2l_gamry_number": ("{name}: Zahl im Gamry-Format nicht lesbar (Dezimalkomma oder Überlauf „****“?): Datei nicht "
                         "gelesen.", "{name}: number in the Gamry file not readable (decimal comma or overflow "
                         "“****”?): file not read."),
    "r2l_gamry_rows": ("{name}: Tabelle {table} hat {n} statt der angegebenen {m} Zeilen (Datei abgeschnitten?): nicht "
                       "gelesen.", "{name}: table {table} has {n} instead of the stated {m} rows (file truncated?): "
                       "not read."),
    "r2l_gamry_none": ("{name}: keine CV-Daten (Gamry .DTA) gefunden.", "{name}: no CV data (Gamry .DTA) found."),
    "r2l_hcell_incomplete": ("{name}: {n} von {m} Halbzyklen und kein Abbruchgrund (STOPREASON): Datei abgeschnitten, "
                             "nicht gelesen.", "{name}: {n} of {m} half-cycles and no stop reason (STOPREASON): file "
                             "truncated, not read."),
    "r2l_bwspec_number": ("{name}: Zahl nicht lesbar (Dezimalkomma oder zwei Exporte in einer Datei?): nicht gelesen.",
                          "{name}: number not readable (decimal comma or two exports in one file?): not read."),
    "r3_bwspec_rows": ("{name}: {n} Datenzeilen, der Dateikopf nennt {m} Pixel (Datei abgeschnitten?): nicht gelesen.",
                       "{name}: {n} data rows, the file header names {m} pixels (file truncated?): not read."),
    "r2l_cube_count": ("{name}: Cube-Datei hat {n} Werte, das Gitter braucht {m}: nicht gelesen.",
                       "{name}: cube file has {n} values, the grid needs {m}: not read."),
    "r2l_cube_bad": ("{name}: keine lesbare Cube-Datei (leer, abgeschnitten oder unbekannte Kodierung).",
                     "{name}: not a readable cube file (empty, truncated or unknown encoding)."),
    "r2l_molden_bad": ("Molden-Datei unvollständig oder beschädigt (abgeschnitten?): nicht gelesen.",
                       "Molden file incomplete or damaged (truncated?): not read."),
    "r2l_molden_shell": ("Molden-Datei: Schalentyp „{t}“ wird nicht unterstützt (s–g).",
                         "Molden file: shell type “{t}” is not supported (s–g)."),
    "r2l_molden_missing": ("Molden-Datei ohne [Atoms], [GTO] oder [MO].", "Molden file without [Atoms], [GTO] or [MO]."),
    "r2l_cml_bad": ("{name}: keine lesbare CML-Datei (leer oder abgeschnitten).",
                    "{name}: not a readable CML file (empty or truncated)."),
    "r2l_docx_bad": ("{name}: kein lesbares Word-Dokument (.docx).", "{name}: not a readable Word document (.docx)."),
    "r2l_pdf_bad": ("{name}: kein lesbares PDF (leer oder beschädigt).", "{name}: not a readable PDF (empty or damaged)."),
})
# b1nmr_: Bruker-NMR-Leser und eigene 1D-Verarbeitung (1.3.0, formats/bruker_nmr.py, core/nmr_proc.py)
TEXTS.update({
    "b1nmr_missing": ("{name}: Datei {file} fehlt: nicht gelesen.", "{name}: file {file} is missing: not read."),
    "b1nmr_only_bak": ("{name}: nur {file}.bak vorhanden (Messung abgebrochen oder umkopiert): nicht gelesen.",
                       "{name}: only {file}.bak present (acquisition aborted or copied): not read."),
    "b1nmr_param": ("{name}: Parameter {key} fehlt oder ist keine Zahl: nicht gelesen.",
                    "{name}: parameter {key} is missing or not a number: not read."),
    "b1nmr_dtype": ("{name}: Datentyp {key} = {v} ist nicht geprüft (bekannt: 0 = int32, 2 = float64): nicht gelesen.",
                    "{name}: data type {key} = {v} is not checked (known: 0 = int32, 2 = float64): not read."),
    "b1nmr_unchecked": ("{name}: {key} = {v} ist nicht geprüft: nicht gelesen.",
                        "{name}: {key} = {v} is not checked: not read."),
    "b1nmr_td": ("{name}: TD = {v} ist keine gültige Punktzahl (positiv, für Re/Im-Paare gerade): nicht gelesen.",
                 "{name}: TD = {v} is not a valid number of points (positive, even for Re/Im pairs): not read."),
    "b1nmr_strip": ("{name}: Strip-FT (STSI = {v}, SI = {si}) ist nicht geprüft: nicht gelesen.",
                    "{name}: strip FT (STSI = {v}, SI = {si}) is not checked: not read."),
    "b1nmr_size": ("{name}: {n} Werte, erwartet {m} (Datei abgeschnitten oder Parameter passen nicht): nicht gelesen.",
                   "{name}: {n} values, expected {m} (file truncated or parameters do not match): not read."),
    "b1nmr_xdim": ("{name}: Größe {si} ist kein Vielfaches der Untermatrix XDIM {x}: nicht gelesen.",
                   "{name}: size {si} is not a multiple of the submatrix XDIM {x}: not read."),
    "b1nmr_nus": ("{name}: NUS-Messung (FnTYPE 2): wird nicht selbst verarbeitet, nur TopSpins {file} kann gezeigt werden.",
                  "{name}: NUS acquisition (FnTYPE 2): not processed here, only TopSpin's {file} can be shown."),
    "b1nmr_nbl": ("{name}: unaufgeteiltes NOAH-Experiment (NBL = {n}): bitte in TopSpin mit splitx_au aufteilen.",
                  "{name}: NOAH experiment not split (NBL = {n}): please split it in TopSpin with splitx_au."),
    "b1nmr_own": ("{name}: eigene Verarbeitung nicht geprüft für {why}: nur TopSpins {file} kann gezeigt werden.",
                  "{name}: own processing not checked for {why}: only TopSpin's {file} can be shown."),
    "b1nmr_why_nus": ("NUS (FnTYPE 2)", "NUS (FnTYPE 2)"),
    "b1nmr_why_nbl": ("unaufgeteiltes NOAH (NBL = {n})", "unsplit NOAH (NBL = {n})"),
    "b1nmr_why_lp": ("Linear Prediction in {dim} (ME_mod = {v})", "linear prediction in {dim} (ME_mod = {v})"),
    "b1nmr_why_grpdly": ("fehlende Gruppenlaufzeit (GRPDLY; DSPFVS {v}, DECIM {d} nicht in der geprüften Tabelle)",
                         "missing group delay (GRPDLY; DSPFVS {v}, DECIM {d} not in the checked table)"),
    "b1nmr_why_grpdly_2d": ("fehlende Gruppenlaufzeit (GRPDLY; Tabelle für 2D nicht geprüft)",
                            "missing group delay (GRPDLY; table not checked for 2D)"),
    "b1nmr_why_grpdly_odd": ("Gruppenlaufzeit GRPDLY = {v} (geprüft: höchstens {tol} neben einer geraden Zahl)",
                             "group delay GRPDLY = {v} (checked: at most {tol} from an even number)"),
    "b1nmr_why_digmod": ("analogen Filter (DIGMOD 0): Gruppenlaufzeit nicht geprüft",
                         "analogue filter (DIGMOD 0): group delay not checked"),
    "b1nmr_why_si": ("SI = {si} (geprüft: Zweierpotenz)", "SI = {si} (checked: power of two)"),
    "b1nmr_why_strip_f1": ("Strip-FT in F1 (FTSIZE = {v}, SI = {si})", "strip FT in F1 (FTSIZE = {v}, SI = {si})"),
    "b1nmr_why_f1mode": ("F1-Quadraturmodus {v} (kein geprüfter Satz)", "F1 quadrature mode {v} (no checked data set)"),
    "b1nmr_why_pseudo": ("Pseudo-2D oder J-res (Pulsprogramm {pp})", "pseudo-2D or J-res (pulse program {pp})"),
    "b1nmr_why_symtilt": ("in TopSpin nachbearbeitetes 2rr ({cmd})", "2rr post-processed in TopSpin ({cmd})"),
    "b1nmr_why_no2d": ("2D (eigene 2D-Verarbeitung noch nicht verfügbar)", "2D (own 2D processing not yet available)"),
    "b1nmr_why_value": ("{key} = {v} (geprüft: {ok})", "{key} = {v} (checked: {ok})"),
    "b1nmr_why_strip": ("Strip-FT (STSI = {v}, SI = {si})", "strip FT (STSI = {v}, SI = {si})"),
    "b1nmr_why_missing": ("fehlenden Parameter {key}", "missing parameter {key}"),
})
# Elucida 1.3.0, Reaktionspfad an die Designlogik der Tabs (Spur P)
TEXTS.update({
    "p13p_import_from_compounds": ("Aus Verbindungen übernehmen (Rechendaten) …", "Import from compounds (Calculation Data) …"),
    "p13p_tbl_empty_calcs": ("Noch keine Rechnungen: über „Daten ▾“ übernehmen oder laden.",
                             "No calculations yet: import or load them via “Data ▾”."),
    "p13p_irc_curve": ("IRC-Kurve", "IRC curve"),
    "p13p_reset_style": ("Stil auf Standard", "Style to defaults"),
    "p13p_reset_style_tip": ("Stil des gezeigten Diagramms (Linien, Schrift, Beschriftung, Rahmen) auf Standard. Werte, "
                             "Vorzeichen, Lage der Plateaus, maßstäblich/schematisch, Verbinder und Abschnitte bleiben. Rückgängig mit Strg+Z.",
                             "Resets the style of the diagram shown (lines, font, labels, frame). Values, signs, plateau positions, "
                             "scaled/schematic, connectors and sections stay. Undo with Ctrl+Z."),
    "p13p_copy_caption_tip": ("SI-Unterschrift der Komposition kopieren (für Word)", "Copy the SI caption of the composition (for Word)"),
    "p13p_orbital": ("Orbital", "Orbital"),
    "p13p_isosurface": ("Isofläche", "Isosurface"),
    "p13p_orb_colors": ("Farben ±", "Colours ±"),
})
# c2d_: eigene 2D-Verarbeitung aus ser (1.3.0, core/nmr2d.py)
TEXTS.update({
    "c2d_noah_unchecked": ("{name}: NOAH-Satz {pp} mit NBL = {n} ist nicht geprüft (nur noah2_SB/noah2_BS mit NBL 2): "
                           "nicht aufgeteilt.",
                           "{name}: NOAH data set {pp} with NBL = {n} is not checked (only noah2_SB/noah2_BS with "
                           "NBL 2): not split."),
    "c2d_noah_phase": ("{name}: Phase ausstehend: Die Phase des {module}-Blocks steht nicht im Datensatz, bitte in "
                       "{dims} setzen (F1 ist um 180° mehrdeutig: Vorzeichen z. B. gegen einen aufgeteilten Teilsatz "
                       "prüfen).",
                       "{name}: phase pending: the phase of the {module} block is not stored in the data set, please "
                       "set it in {dims} (F1 is ambiguous by 180°: check the sign, e.g. against a split "
                       "sub-dataset)."),
    "c2d_noah_k": ("{name}: Block {k} gibt es nicht (NOAH-Satz mit {n} Blöcken, gezählt ab 1).",
                   "{name}: block {k} does not exist (NOAH data set with {n} blocks, counted from 1)."),
    "c2d_sign": ("{name}: eigene Verarbeitung hat das umgekehrte Vorzeichen von TopSpins 2rr (r = {r}): nur TopSpins "
                 "2rr kann gezeigt werden.",
                 "{name}: own processing has the opposite sign of TopSpin's 2rr (r = {r}): only TopSpin's 2rr can "
                 "be shown."),
    "c2d_lp_f2": ("{name}: Linear Prediction in F2 (ME_mod = {v}) lässt sich nicht abschalten (ohne LP nur in F1 "
                  "geprüft): nur TopSpins 2rr kann gezeigt werden.",
                  "{name}: linear prediction in F2 (ME_mod = {v}) cannot be switched off (without LP checked in F1 "
                  "only): only TopSpin's 2rr can be shown."),
    "c2d_why_mem": ("Größe {si} (geschätzter Speicher {gb} GB, höchstens {max} GB)",
                    "size {si} (estimated memory {gb} GB, at most {max} GB)"),
    "c2d_override": ("{name}: eigener Wert {dim} {key} = {v} (Datensatz bzw. Vorgabe: {old}).",
                     "{name}: own value {dim} {key} = {v} (data set or default: {old})."),
    "c2d_o1": ("{name}: Senderfrequenz in F1 (acqu2s) weicht um {d} Hz von acqus ab: F1-Achse mit SFO1 aus acqus.",
               "{name}: carrier frequency in F1 (acqu2s) differs by {d} Hz from acqus: F1 axis uses SFO1 from acqus."),
})
# b2nmr_: NMR-Auswertung (1.3.0, core/nmr_analysis.py)
TEXTS.update({
    "b2nmr_ref_unchecked": ("{nuc}: Restsignal für {solvent} nicht geprüft: kein Referenzvorschlag, bitte die Referenz "
                            "setzen.", "{nuc}: residual signal for {solvent} not checked: no reference suggestion, "
                            "please set the reference."),
    "b2nmr_ref_outside": ("Restsignal ({ref} ppm) liegt außerhalb des Spektrums: kein Referenzvorschlag.",
                          "Residual signal ({ref} ppm) is outside the spectrum: no reference suggestion."),
    "b2nmr_bl_dense": ("Basislinie nicht korrigiert: nur {pct} % des Spektrums sind signalfrei (Rauschen nicht "
                       "bestimmbar).", "Baseline not corrected: only {pct} % of the spectrum is free of signals (noise "
                       "cannot be determined)."),
    "b2nmr_bl_unknown": ("Basislinie „{m}“ unbekannt: Polynom 5. Grades verwendet.",
                         "Baseline “{m}” unknown: fifth-order polynomial used."),
    "b2nmr_bl_few": ("Basislinie nicht korrigiert: zu wenige signalfreie Punkte.",
                     "Baseline not corrected: too few signal-free points."),
    "b2nmr_fit_unresolved": ("J = {j} Hz eingegeben, nicht gemessen (Linien nicht getrennt).",
                             "J = {j} Hz entered, not measured (lines not resolved)."),
    "b2nmr_int_overlap": ("Integralbereiche überlappen oder liegen ineinander: bitte trennen.",
                          "Integral ranges overlap or are nested: please separate them."),
    "b2nmr_norm_zero": ("Bezugsintegral ist null oder negativ: keine Normierung möglich.",
                        "Reference integral is zero or negative: cannot normalize."),
    "b2nmr_ref_weak": ("Restsignal ({ref} ppm) im Suchfenster nicht deutlich: kein Referenzvorschlag.",
                       "Residual signal ({ref} ppm) not distinct in the search window: no reference suggestion."),
    "b2nmr_int_broad": ("Integral einer breiten Linie (Halbwertsbreite > {hz} Hz): Genauigkeit ±2 % nicht belegt.",
                        "Integral of a broad line (half width > {hz} Hz): ±2 % accuracy not established."),
    "b2nmr_fit_class": ("Klasse „{mult}“ passt nicht zu {n} J-Werten.", "Class “{mult}” does not match {n} J values."),
    "b2nmr_fit_lines": ("Keine Linien im Bereich.", "No lines in the range."),
    "b2nmr_fit_none": ("Muster „{mult}“ im Bereich nicht gefunden.", "Pattern “{mult}” not found in the range."),
    "b2nmr_fit_ambiguous": ("Muster „{mult}“ im Bereich mehrdeutig: Bereich enger ziehen.",
                            "Pattern “{mult}” is ambiguous in the range: narrow the range."),
    "b2nmr_unconfirmed": ("Signal nicht bestätigt und ohne Bereich: δ wird nicht gedruckt.",
                          "Signal not confirmed and without a range: δ is not printed."),
})
# Langformen gekürzter Chips (Tooltip über long_form): dieselben Texte wie zuvor im Dialog
for _k in ("char", "nmr", "figs", "methods", "xray", "dft"):
    TEXTS[f"si_chip_{_k}_long"] = TEXTS[f"si_part_{_k}"]
for _k in ("greek", "axes_frame", "struct_frame"):
    TEXTS[f"tf_{_k}_c_long"] = TEXTS[f"tf_{_k}"]


def set_lang(lang: str):
    global _LANG
    _LANG = "en" if str(lang).lower().startswith("en") else "de"


def get_lang() -> str:
    return _LANG


def long_form(text: str) -> str:
    """Langform einer gekürzten Beschriftung (Eintrag `<key>_long`) für den Tooltip, sonst ''."""
    i = 1 if _LANG == "en" else 0
    for key, pair in TEXTS.items():
        if pair[i] == text and key + "_long" in TEXTS:
            return TEXTS[key + "_long"][i]
    return ""


def T_en(_key: str, **kw) -> str:
    """Englischer Text unabhängig von der Programmsprache (Dateien wie CSV sind immer englisch)."""
    en = TEXTS.get(_key, (_key, _key))[1]
    return en.format(**kw) if kw else en


_TO_EN = {}


def to_en(text: str) -> str:
    """Angezeigten Text (Tabellenkopf, Hinweis) auf Englisch für Dateien: ganzer Eintrag oder der Teil vor „ [Einheit]“;
    Unbekanntes bleibt."""
    if _LANG == "en" or not text:
        return text
    if not _TO_EN:
        _TO_EN.update({de.replace("\u200b", ""): en for de, en in TEXTS.values()
                       if isinstance(de, str) and "{" not in de})
    text = text.replace("\u200b", "")                 # STYLE.QTY (Satzmarke) gehört nicht zum Wort
    if text in _TO_EN:
        return _TO_EN[text]
    head, sep, unit = text.partition(" [")
    return _TO_EN.get(head, head) + sep + unit if sep else text


def T(_key: str, **kw) -> str:
    de, en = TEXTS.get(_key, (_key, _key))
    txt = en if _LANG == "en" else de
    return txt.format(**kw) if kw else txt
# nmrv_: interaktive NMR-Ansicht (tabs/nmr_view.py, Spur D1 1.3.0); Tasten wie Mnova
TEXTS.update({
    "nmrv_display": ("Anzeige", "Display"),
    "nmrv_show_int_curves": ("Integralkurven", "Integral curves"),
    "nmrv_show_int_values": ("Integralwerte", "Integral values"),
    "nmrv_show_peak_labels": ("Peak-Labels", "Peak labels"),
    "nmrv_show_mult_labels": ("Multipletts", "Multiplets"),
    "nmrv_show_mult_labels_long": ("Multiplett-Labels", "Multiplet labels"),
    "nmrv_show_y_axis": ("Intensitätsachse", "Intensity axis"),
    "nmrv_show_grid": ("Gitter", "Grid"),
    "nmrv_show_title": ("Titel", "Title"),
    "nmrv_show_solvents": ("Lösungsmittel", "Solvent"),
    "nmrv_show_solvents_long": ("Lösungsmittelmarken", "Solvent marks"),
    "nmrv_ml_delta": ("δ", "δ"),
    "nmrv_ml_cls": ("Klasse", "Class"),
    "nmrv_ml_delta_cls": ("δ (Klasse)", "δ (class)"),
    "nmrv_ml_delta_full": ("δ (Klasse, nH)", "δ (class, nH)"),
    "nmrv_ml_range": ("Bereich", "Range"),
    "nmrv_ml_range_full": ("Bereich (Klasse, nH)", "Range (class, nH)"),
    "nmrv_ml_tip": ("Inhalt der Multiplett-Labels (wie MNova „Multiplet Label“)",
                    "Content of the multiplet labels (as MNova “Multiplet Label”)"),
    "nmrv_pointer_tip": ("Zeiger (Esc): beendet jeden Modus", "Pointer (Esc): leaves any mode"),
    "nmrv_zoom_tip": ("Zoom (Z): Bereich aufziehen; Z erneut wechselt waagerecht → senkrecht → Rechteck",
                      "Zoom (Z): drag over the region; Z again switches horizontal → vertical → box"),
    "nmrv_pan_tip": ("Verschieben (P): ziehen; P erneut wechselt frei → waagerecht → senkrecht",
                     "Pan (P): drag; P again switches free → horizontal → vertical"),
    "nmrv_integral_tip": ("Integration (I): Bereich aufziehen; Bereich anklicken, Ränder oder Mitte ziehen, Entf löscht",
                          "Integration (I): drag over the region; click a range, drag its edges or middle, Del removes it"),
    "nmrv_peaks_tip": ("Peak-Picking (K): Bereich aufziehen, die Höhe der Maus beim Loslassen ist die Schwelle; Klick "
                       "ins Leere fügt einen Peak hinzu (Umschalt: ohne Einrasten, für Schultern); Peak anklicken + Entf "
                       "löscht", "Peak picking (K): drag over the region, the mouse height on release is the threshold; a "
                       "click on an empty spot adds a peak (Shift: without snapping, for shoulders); click a peak + Del "
                       "removes it"),
    "nmrv_multiplet_tip": ("Multiplett (J): Bereich aufziehen, die Höhe der Maus beim Loslassen ist die Schwelle",
                           "Multiplet (J): drag over the region, the mouse height on release is the threshold"),
    "nmrv_reference_tip": ("Referenz (R oder L): Peak anklicken", "Reference (R or L): click a peak"),
    "nmrv_cursor_tip": ("Fadenkreuz (C): zwei Klicks messen den Abstand (J in Hz)",
                        "Crosshair (C): two clicks measure the distance (J in Hz)"),
    "nmrv_cut_tip": ("Ausblenden (X): Bereich aufziehen; Lücke anklicken + Entf blendet wieder ein; in einem Ausschnitt "
                     "aufgezogen: schneidet den Bereich aus dem Ausschnitt (Bruch „//“)",
                     "Cut (X): drag over the region; click the gap + Del shows it again; dragged inside an inset: cuts "
                     "the region out of the inset (break “//”)"),
    "nmrv_inset_tip": ("Ausschnitt (E): Bereich aufziehen, er erscheint vergrößert im Spektrum",
                       "Inset (E): drag over the region, it appears enlarged in the spectrum"),
    "nmrv_phase_tip": ("Phase (Umschalt+P): linke Maustaste 0. Ordnung, rechte 1. Ordnung, mit Strg fein; Klick "
                       "setzt den Drehpunkt", "Phase (Shift+P): left mouse button 0th order, right 1st order, Ctrl "
                       "for fine steps; a click sets the pivot"),
    "nmrv_zoom_out_tip": ("Herauszoomen (Umschalt+Z)", "Zoom out (Shift+Z)"),
    "nmrv_full_tip": ("Ganzes Spektrum (F, auch Doppelklick)", "Full spectrum (F, also double click)"),
    "nmrv_highest_tip": ("Höchster Peak auf Fensterhöhe (H)", "Highest peak to window height (H)"),
    "nmrv_prev_tip": ("Vorige Zoomstufe (< oder Alt+←)", "Previous zoom level (< or Alt+←)"),
    "nmrv_next_tip": ("Nächste Zoomstufe (> oder Alt+→)", "Next zoom level (> or Alt+→)"),
    "nmrv_delete": ("Gewählten Bereich oder Peak löschen (Entf)", "Delete the selected range or peak (Del)"),
    "nmrv_hint_pointer": ("Doppelklick: ganzes Spektrum · Mausrad: Intensität",
                          "Double click: full spectrum · mouse wheel: intensity"),
    "nmrv_hint_zoom_h": ("Zoom waagerecht: Bereich aufziehen …", "Horizontal zoom: drag over the region …"),
    "nmrv_hint_zoom_v": ("Zoom senkrecht: Bereich aufziehen …", "Vertical zoom: drag over the region …"),
    "nmrv_hint_zoom_box": ("Zoom Rechteck: Rechteck aufziehen …", "Box zoom: drag a box …"),
    "nmrv_hint_pan_free": ("Verschieben frei: ziehen …", "Pan freely: drag …"),
    "nmrv_hint_pan_h": ("Verschieben waagerecht: ziehen …", "Pan horizontally: drag …"),
    "nmrv_hint_pan_v": ("Verschieben senkrecht: ziehen …", "Pan vertically: drag …"),
    "nmrv_hint_integral": ("Integration: Bereich aufziehen …", "Integration: drag over the region …"),
    "nmrv_hint_peaks": ("Peak-Picking: Bereich aufziehen, Höhe beim Loslassen = Schwelle …",
                        "Peak picking: drag over the region, height on release = threshold …"),
    "nmrv_hint_multiplet": ("Multiplett: Bereich aufziehen, Höhe beim Loslassen = Schwelle …",
                            "Multiplet: drag over the region, height on release = threshold …"),
    "nmrv_hint_reference": ("Referenz: Peak anklicken …", "Reference: click a peak …"),
    "nmrv_hint_cursor": ("Fadenkreuz: zwei Punkte anklicken …", "Crosshair: click two points …"),
    "nmrv_hint_cut": ("Ausblenden: Bereich aufziehen (im Ausschnitt: aus dem Ausschnitt schneiden) …",
                      "Cut: drag over the region (inside an inset: cut it out of the inset) …"),
    "nmrv_hint_inset": ("Ausschnitt: Bereich aufziehen …", "Inset: drag over the region …"),
    "nmrv_hint_phase": ("Phase: links ziehen 0. Ordnung, rechts 1. Ordnung, Strg fein …",
                        "Phase: drag left 0th order, right 1st order, Ctrl fine …"),
    "nmrv_ref_done": ("Referenzpeak bei {x} ppm gewählt", "Reference peak at {x} ppm selected"),
    "nmrv_dist_ppm": ("Abstand {d} ppm", "distance {d} ppm"),
    "nmrv_phase_read": ("Phase 0. Ordnung {ph0}°, 1. Ordnung {ph1}°", "phase 0th order {ph0}°, 1st order {ph1}°"),
    "nmrv_style": ("Aussehen", "Appearance"),
    "nmrv_st_spectrum": ("Spektrum", "Spectrum"),
    "nmrv_st_labels": ("Peak-Labels", "Peak labels"),
    "nmrv_st_solvent": ("Lösungsmittel", "Solvent"),
    "nmrv_st_axis": ("Achse", "Axis"),
    "nmrv_st_bracket": ("Integralklammer", "Integral bracket"),
    "nmrv_st_values": ("Integralwerte", "Integral values"),
    "nmrv_st_color": ("Farbe", "Colour"),
    "nmrv_st_width": ("Dicke", "Width"),
    "nmrv_st_size": ("Größe", "Size"),
    "nmrv_st_spectrum_color": ("Linienfarbe des Spektrums", "Line colour of the spectrum"),
    "nmrv_st_spectrum_width": ("Liniendicke des Spektrums", "Line width of the spectrum"),
    "nmrv_st_peak_label_color": ("Farbe der Peak-Labels und ihrer Leitlinien", "Colour of the peak labels and leaders"),
    "nmrv_st_peak_label_size": ("Schriftgröße der Peak-Labels", "Font size of the peak labels"),
    "nmrv_st_integral_bracket_color": ("Farbe der Integralklammern", "Colour of the integral brackets"),
    "nmrv_st_integral_bracket_width": ("Strichdicke der Integralklammern", "Line width of the integral brackets"),
    "nmrv_st_integral_value_color": ("Farbe der Integralwerte", "Colour of the integral values"),
    "nmrv_st_integral_value_size": ("Schriftgröße der Integralwerte", "Font size of the integral values"),
    "nmrv_st_solvent_label_color": ("Farbe der Lösungsmittel-Labels", "Colour of the solvent labels"),
    "nmrv_st_solvent_label_size": ("Schriftgröße der Lösungsmittel-Labels", "Font size of the solvent labels"),
    "nmrv_st_axis_color": ("Farbe der Achse", "Colour of the axis"),
    "nmrv_st_axis_font_size": ("Schriftgröße der Achse", "Font size of the axis"),
    "nmrv_mark_tip": ("Marke (T): Klick über ein Signal setzt eine Marke (Zeichen in der Karte Anzeige), ziehen "
                      "verschiebt, Entf löscht", "Mark (T): a click on a signal sets a mark (symbol in the Display "
                      "card), drag to move, Del removes it"),
    "nmrv_hint_mark": ("Marke: Signal anklicken …", "Mark: click a signal …"),
    "nmrv_mark_symbol": ("Marke", "Mark"),
    "nmrv_mark_symbol_tip": ("Zeichen neuer Marken über Signalen (Verunreinigungen; die Bedeutung, z. B. „* = H₂O“, "
                             "steht in der Bildunterschrift)", "Symbol of new marks above signals (impurities; the "
                             "meaning, e.g. “* = H₂O”, goes into the caption)"),
    "nmrv_st_marks": ("Marken", "Marks"),
    "nmrv_st_mark_color": ("Farbe der Marken", "Colour of the marks"),
    "nmrv_st_mark_size": ("Schriftgröße der Marken", "Font size of the marks"),
})


# Spur T (1.3.0): Tabs X-Ray, SEC, EPR, DFT, Reaktionspfad, Vergleich
TEXTS.update({
    "epr_calc_assign_hint_link": ("Gruppe wählen, dann ihre Kerne im Reiter <a href=\"hfc\">„Hyperfein“</a> anklicken "
                                  "(Shift + Rahmen: mehrere).",
                                  "Select a group, then click its nuclei on the <a href=\"hfc\">“Hyperfine”</a> page "
                                  "(Shift + frame: several)."),
    "dft_page_calc": ("Rechnung: <b>{name}</b> · <a href=\"structures\">Andere wählen</a>",
                      "Calculation: <b>{name}</b> · <a href=\"structures\">Choose another</a>"),
    "xray_pack_off_hint": ("Häkchen wirken nur im Packungsbild (<a href=\"pack\">Abbildung: Packung</a>).",
                           "Ticks act only on the packing figure (<a href=\"pack\">Figure: Packing</a>)."),
    "dft_nics_show_hint": ("Nur für die Vorschau; Export und SI: Scan und 3D.",
                           "Preview only; export and SI: scan and 3D."),
    "rp_insert_orbital_src": ("3D-/Orbitalansicht einfügen ({src}; Wahl unter „3D-Quelle“) …",
                              "Insert 3D/orbital view ({src}; choose under “3D source”) …"),
    "rp_edit_selected_target": ("Gewähltes Bild bearbeiten: 3D-Ansicht hier, Energieprofil in „Rechendaten“",
                                "Edit the selected figure: 3D view here, energy profile in “Calculation Data”"),
    "rp_edit_in_calc": ("Profil in „Rechendaten“ bearbeiten, danach „Profile aktualisieren“",
                        "Edit the profile in “Calculation Data”, then “Update profiles”"),
    "dft_prof_reset_tip": ("„Layout zurücksetzen“: verschobene Beschriftungen an ihren Platz. „Stil auf Standard“: Linien, "
                           "Schrift und Rahmen; Werte, Vorzeichen, Plateaus und der eigene Achsentitel bleiben.",
                           "“Reset layout”: moved labels back in place. “Style to defaults”: lines, font and frame; values, signs, "
                           "plateaus and your axis title stay."),
})


# Spur A (1.3.0): Ablegen, Ansichten, Exportmeldung, PPTX
TEXTS.update({
    "tab_save_tip": ("Darstellung dieses Tabs als Vorlage (YAML) speichern, z. B. für andere Verbindungen. Dateien, "
                     "Auswertung und Bildunterschrift kommen nicht hinein – die Verbindung selbst speichert sich "
                     "automatisch (Strg+S speichert sofort).",
                     "Save this tab's display as a preset (YAML), e.g. for other compounds. Files, analysis and caption "
                     "are not included – the compound itself is saved automatically (Ctrl+S saves at once)."),
    "drop_fluo_choose": ("Fluoreszenz: Ist die Datei Absorption oder Emission? Bitte in der Karte Daten über „{a}“ "
                         "bzw. „{e}“ wählen – nichts geladen.",
                         "Fluorescence: is the file absorption or emission? Please choose it in the Data card under "
                         "“{a}” or “{e}” – nothing loaded."),
})
TEXTS.update({
    "card_acts_on": ("Ergebnis rechts im Reiter {t}.", "Result on the right in the tab {t}."),
})
TEXTS.update({
    "notice_show": ("Anzeigen", "Show"),
    "conc_enter_elsewhere": ("Messdaten in „UV-Vis (ε)“ geladen: Die Probennamen nennen keine Konzentrationen.",
                             "Measurement data loaded into “UV-Vis (ε)”: the sample names state no concentrations."),
    "conc_enter_link": ("Konzentrationen eintragen", "Enter concentrations"),
})
TEXTS.update({
    "export_formats": ("Formate: {f}", "Formats: {f}"),
    "export_change_formats": ("Formate ändern", "Change formats"),
    "export_eps_series": ("Alle {n} Serien exportiert.", "All {n} series exported."),
    "si_card_link": ("Auswahl ändern (Karte „SI-Export“)", "Change selection (card “SI Export”)"),
    "si_used_parts": ("Teile: {parts}", "Parts: {parts}"),
    "si_used_figs_off": ("Abgewählte Abbildungen (nicht in der Datei): {tabs}",
                         "Deselected figures (not in the file): {tabs}"),
    "si_used_tables": ("Tabellen mit eigenem „In die SI“: {t}", "Tables with their own “In the SI”: {t}"),
    "pub_si_used": ("Verbindungen: {n}; Kapitel: {parts}", "Compounds: {n}; chapters: {parts}"),
    "pub_si_change": ("Auswahl ändern …", "Change selection …"),
    "dp_used_text": ("Laborkürzel auch im Inhalt ersetzt", "Lab codes also replaced in the content"),
    "dp_change": ("Auswahl ändern …", "Change selection …"),
    "pub_dp_used_off": ("Je Verbindung abgewählt (Datenpaket der Verbindung): {items}",
                        "Deselected per compound (the compound's data package): {items}"),
})
TEXTS.update({
    "pptx_grp": ("Folien (PPTX)", "Slides (PPTX)"),
    "pptx_figs_tip": ("Abbildung dieses Tabs auf die Folien (eine Folie je Abbildung, mit Unterschrift); eigene Auswahl, "
                      "unabhängig von der SI",
                      "Put this tab's figure on the slides (one slide per figure, with caption); own selection, "
                      "independent of the SI"),
    "pptx_export": ("Folien exportieren", "Export slides"),
    "pptx_export_tip": ("Schreibt die gewählten Abbildungen als PowerPoint-Datei (eine Folie je Abbildung, Unterschrift "
                        "als bearbeitbares Textfeld) nach figures/",
                        "Writes the selected figures as a PowerPoint file (one slide per figure, caption as an editable "
                        "text box) to figures/"),
    "pptx_none": ("Keine Abbildung für die Folien gewählt oder vorhanden.", "No figure selected or available for the slides."),
    "pptx_used": ("Folien: {n}, je Abbildung eine", "Slides: {n}, one per figure"),
})
TEXTS.update({"notice_close": ("Schließen", "Close")})
TEXTS.update({
    "drop_part_1": ("1 Datei in „{tab}“", "1 file into “{tab}”"),
    "drop_part_n": ("{n} Dateien in „{tab}“", "{n} files into “{tab}”"),
    "drop_and": (" und ", " and "),
    "drop_loaded2": ("{parts} geladen.", "Loaded {parts}."),
    "notice_show_tab": ("„{tab}“ anzeigen", "Show “{tab}”"),
    "dp_used": ("Datenpaket: {n} Dateien im Zip ({sel} von {total} Einträgen gewählt)",
                "Data package: {n} files in the zip ({sel} of {total} entries selected)"),
})
TEXTS.update({
    "pptx_hint": ("Schreibt figures/<Verbindung>_slides.pptx: eine Folie je gewählter Abbildung mit Bildunterschrift; "
                  "eigene Auswahl, unabhängig von der SI.",
                  "Writes figures/<compound>_slides.pptx: one slide per selected figure with its caption; own "
                  "selection, independent of the SI."),
})
TEXTS.update({                                      # Spur A2: zugeklappte Exportmeldung (Entscheidung 57)
    "notice_details": ("Details", "Details"),
    "notice_hints": ("{head} – {n} Hinweise", "{head} – {n} notes"),
    "notice_hints_1": ("{head} – 1 Hinweis", "{head} – 1 note"),
    "notice_si_saved": ("SI gespeichert", "SI saved"),
    "notice_exported": ("Exportiert", "Exported"),
})
TEXTS.update({                                      # Spur A2, Punkt 3a: Tab „Export“ (Entscheidungen 64–66)
    "tab_export": ("Export", "Export"),
    "nav_grp_out": ("Ausgabe", "Output"),
    "step_export": ("Optionen", "Options"),
    "grp_axes_size": ("Achsen und Größe", "Axes and Size"),
    "export_fmt_tip_pdf": ("Vektorgrafik (Text als Text)", "Vector graphic (text as text)"),
    "export_fmt_tip_svg": ("Vektorgrafik, Text als Pfade", "Vector graphic, text as paths"),
    "export_fmt_tip_png": ("Pixelbild", "Pixel image"),
    "export_fmt_tip_pptx": ("Je Abbildung eine Folie mit Bild und Unterschrift (<Name>_<Tab>.pptx)",
                            "One slide with figure and caption per figure (<name>_<tab>.pptx)"),
    "export_grp_items": ("Abbildungen und Berichte", "Figures and Reports"),
    "export_col_item": ("Abbildung / Bericht", "Figure / Report"),
    "export_col_files": ("Formate", "Formats"),
    "export_col_slides": ("Folien", "Slides"),
    "export_row": ("Exportieren", "Export"),
    "export_row_tip": ("Schreibt die Dateien von „{tab}“ in den Ordner der Verbindung (figures, tables, SI; überschreibt sie)",
                       "Writes the files of “{tab}” to the compound folder (figures, tables, SI; overwrites them)"),
    "export_items_hint": ("Eine Zeile je Abbildung bzw. Bericht. „Exportieren“ schreibt die Dateien dieser Zeile nach figures/, tables/ "
                          "und SI/ der Verbindung (überschreibt sie). „Folien“ wählt aus, was „Folien (PPTX)“ in eine "
                          "Datei schreibt (Auswahl gilt auf diesem Rechner).",
                          "One row per figure or report. “Export” writes the files of that row to figures/, tables/ and SI/ "
                          "of the compound (overwrites them). “Slides” selects what “Slides (PPTX)” writes into one file "
                          "(the selection applies on this computer)."),
    "export_none": ("Noch keine Daten: Messungen in die Tabs laden", "No data yet: load measurements into the tabs"),
    "export_pptx": ("Folien (PPTX)", "Slides (PPTX)"),
    "export_pptx_tip": ("Eine PPTX-Datei mit einer Folie je Abbildung mit Häkchen bei „Folien“ (figures/<Verbindung>_slides.pptx)",
                        "One PPTX file with one slide per figure ticked under “Slides” (figures/<compound>_slides.pptx)"),
    "export_all": ("Alles exportieren", "Export All"),
    "export_all_tip": ("Jede Zeile wie ihr „Exportieren“, eine Meldung für alle (Strg+E in diesem Tab)",
                       "Every row like its “Export”, one message for all (Ctrl+E in this tab)"),
    "export_all_used": ("Exportiert: {tabs}", "Exported: {tabs}"),
    "export_all_missing": ("Nicht exportiert: {tabs}", "Not exported: {tabs}"),
    "export_all_none": ("Nichts zu exportieren: noch keine Daten in den Tabs.", "Nothing to export: no data in the tabs yet."),
})
TEXTS.update({                                      # Spur A2, Punkt 3b: SI-Auswahl je Verbindung, SI/Datenpaket im Tab „Export“
    "pub_si_figs_off": ("Abgewählte Abbildungen (Auswahl im Tab „Export“ der Verbindung): {items}",
                        "Deselected figures (selection in the compound's Export tab): {items}"),
    "export_col_si": ("SI", "SI"),
    "export_si_tip": ("Abbildung in die SI (SI-Abschnitt und Gesamt-SI); gespeichert mit der Verbindung",
                      "Figure in the SI (SI section and complete SI); saved with the compound"),
    "export_si_btn": ("SI (Word)", "SI (Word)"),
    "export_dp_btn": ("Datenpaket", "Data Package"),
    "export_dp_tip": ("Rohdaten dieser Verbindung als Zip mit der gespeicherten Auswahl (Auswahl ändern: Projektseite → Export)",
                      "Raw data of this compound as a zip with the saved selection (change the selection: project page → Export)"),
})
TEXTS.update({"dp_nothing": ("Datenpaket: keine Dateien gewählt", "Data package: no files selected")})
TEXTS.update({                                      # Spur A2, Punkt 3c: Reiter „Export“ der Projektseite (Entscheidung 69)
    "pub_export_tab": ("Export", "Export"),
    "pub_exp_si_grp": ("Gesamt-SI (Word)", "Complete SI (Word)"),
    "pub_exp_dp_grp": ("Datensätze (Zip)", "Datasets (Zip)"),
    "pub_exp_toc": ("Verzeichnis", "Contents"),
    "pub_exp_methods": ("Auswertungstexte", "Analysis texts"),
    "pub_exp_options": ("Optionen", "Options"),
    "pub_exp_paths": ("Reaktionspfade", "Reaction paths"),
    "pub_exp_paths_off": ("Nicht in die SI", "Not in the SI"),
    "pub_exp_text": ("Auch im Inhalt", "Also in content"),
    "pub_exp_dp_write": ("Datensätze schreiben", "Write datasets"),
    "pub_exp_change": ("Auswahl ändern (Reiter „Export“)", "Change selection (tab “Export”)"),
})
TEXTS.update({"pub_exp_no_codes": ("Keine Laborkürzel gefunden", "No lab codes found")})
TEXTS.update({                                      # Spur A2, Punkt 3 (Rest): Zeile je Abbildung/Bericht, Fortschritt
    "export_part_spectra": ("Spektren", "Spectra"),
    "export_part_decay": ("Abklingkurve", "Decay"),
    "export_part_hfc": ("Hyperfein", "Hyperfine"),
    "export_part_spin": ("Spindichte", "Spin density"),
    "export_part_structure": ("Struktur", "Structure"),
    "export_part_packing": ("Packung", "Packing"),
    "export_part_tables": ("Tabellen", "Tables"),
    "export_part_geometry": ("Geometrie {name}", "Geometry {name}"),
    "export_part_orbitals": ("Orbitale {name}", "Orbitals {name}"),
    "export_part_report": ("Bericht, NBO, ACID", "Report, NBO, ACID"),
    "export_all_progress": ("Exportiere {i}/{n}: {tab} …", "Exporting {i}/{n}: {tab} …"),
})
TEXTS.update({                                      # Spur A2, Export-Tab Entwurf v2 (Reiter je Ziel)
    "export_page_img": ("Bilder", "Images"),
    "export_page_slides": ("Folien", "Slides"),
    "export_page_si": ("SI (Word)", "SI (Word)"),
    "export_hint_img": ("Zeilen auswählen (Strg/Umschalt für mehrere, Tabname = ganzer Tab) und unten exportieren; ohne "
                        "Auswahl wird alles exportiert. Ziel: figures/, tables/ und SI/ der Verbindung (überschreibt).",
                        "Select rows (Ctrl/Shift for several, tab name = whole tab) and export below; without a selection "
                        "everything is exported. Target: figures/, tables/ and SI/ of the compound (overwrites)."),
    "export_hint_slides": ("Häkchen am Tab: seine Abbildungen kommen in figures/<Verbindung>_slides.pptx (eine Folie je "
                           "Abbildung mit Unterschrift). Auswahl gilt auf diesem Rechner.",
                           "Tick at a tab: its figures go into figures/<compound>_slides.pptx (one slide per figure with "
                           "caption). The selection applies on this computer."),
    "export_hint_si": ("Häkchen am Tab: seine Abbildungen kommen in den SI-Abschnitt und die Gesamt-SI (mit der Verbindung "
                       "gespeichert). Synthese, NMR und X-Ray steuern die Teile links.",
                       "Tick at a tab: its figures go into the SI section and the complete SI (saved with the compound). "
                       "Synthesis, NMR and X-ray are controlled by the parts on the left."),
    "export_no_slides": ("Dieser Tab hat keine Folie", "This tab has no slide"),
    "export_no_si": ("Über die Teile links (SI (Word): Teile und Schrift)", "Via the parts on the left (SI (Word): Parts and Font)"),
    "export_item_figure": ("Abbildung", "Figure"),
    "export_item_report": ("Bericht (Word)", "Report (Word)"),
    "export_n": ("{n} exportieren", "Export {n}"),
    "export_slides_n": ("Folien (PPTX) – {n}", "Slides (PPTX) – {n}"),
})
TEXTS.update({                                      # Spur A2, Export-Tab v3 (Karten-Galerie, Entscheidung 93)
    "export_page": ("Abbildungen und Berichte", "Figures and Reports"),
    "export_cards_hint": ("Klick wählt aus · die Auswahl gilt für Bilder, Tabellen, PPTX und SI",
                          "Click selects · the selection drives images, tables, PPTX and SI"),
    "export_select_all": ("Alle", "All"),
    "export_select_none": ("Keine", "None"),
    "export_n_selected": ("{n} ausgewählt", "{n} selected"),
    "export_none_selected": ("Nichts ausgewählt", "Nothing selected"),
    "export_slides_sel": ("Folien aus Auswahl (PPTX)", "Slides from Selection (PPTX)"),
    "export_slides_sel_tip": ("figures/<Verbindung>_slides.pptx mit einer Folie je Abbildung der gewählten Tabs (ohne "
                              "Auswahl: alle)", "figures/<compound>_slides.pptx with one slide per figure of the selected "
                              "tabs (without a selection: all)"),
    "export_si_parts_tip": ("In die SI über die Teile links (SI (Word) dieser Verbindung)",
                            "Into the SI via the parts on the left (SI (Word) of this compound)"),
    "export_item_series": ("Serie {s}", "Series {s}"),
    "export_grp_formats": ("Formate (Bilder)", "Formats (Images)"),
    "export_grp_si": ("SI (Word) dieser Verbindung", "SI (Word) of This Compound"),
    "export_formats_hint": ("Gilt für „exportieren“ und Strg+E in den Tabs.", "Applies to “Export” and Ctrl+E in the tabs."),
    "export_si_hint": ("Abbildungen = ausgewählte Karten. Die Gesamt-SI wählt ihre Kapitel auf der Projektseite.",
                       "Figures = selected cards. The complete SI picks its chapters on the project page."),
})
TEXTS.update({                                      # Spur A2: ein Ort für die SI-Auswahl (Entscheidungen 67/93)
    "si_elsewhere": ("In die SI: Karte im Tab <a href=\"export\">Export</a> auswählen",
                     "Into the SI: select the card in the <a href=\"export\">Export</a> tab"),
    "export_part_tdt": ("Anregungen (Tabelle)", "Excitations (table)"),
    "export_part_irc": ("IR-Rechnung (Tabelle)", "IR calculation (table)"),
    "export_si_only_tip": ("Tabelle bzw. Text nur für die SI (keine eigenen Dateien)",
                           "Table or text for the SI only (no files of its own)"),
    "export_btn_img": ("Bilder", "Images"),
    "export_btn_tab": ("Tabellen", "Tables"),
    "export_btn_pptx": ("PPTX", "PPTX"),
    "export_btn_si": ("SI (Word)", "SI (Word)"),
    "export_btn_img_tip": ("Dateien der gewählten Karten ({n}): Abbildungen nach figures/ (Formate links), "
                           "Methodentexte, Bildunterschriften und Berichte nach SI/; ohne Tabellen (Strg+E)",
                           "Files of the selected cards ({n}): figures to figures/ (formats on the left), methods "
                           "texts, captions and reports to SI/; no tables (Ctrl+E)"),
    "export_btn_tab_tip": ("CSV und Excel-Mappe der Tabs mit gewählter Karte ({n}) nach tables/",
                           "CSV and Excel workbook of the tabs with a selected card ({n}) to tables/"),
    "export_btn_pptx_tip": ("figures/<Verbindung>_slides.pptx: eine Folie je gewählter Abbildung ({n})",
                            "figures/<compound>_slides.pptx: one slide per selected figure ({n})"),
    "export_btn_si_tip": ("SI-Abschnitt dieser Verbindung (Teile links) mit {n} gewählten Abbildungen bzw. Tabellen; "
                          "die Auswahl gilt auch für die Gesamt-SI",
                          "SI section of this compound (parts on the left) with {n} selected figures or tables; the "
                          "selection also applies to the complete SI"),
    "export_btn_none_tip": ("Erst Karten auswählen", "Select cards first"),
    "export_btn_img_empty": ("Die Auswahl hat keine Dateien (nur Tabellen für die SI)",
                             "The selection has no files (SI tables only)"),
    "export_btn_tab_empty": ("Die Auswahl hat keine Tabellen (Synthese, NMR, Weitere und SI-Tabellen schreiben keine)",
                             "The selection has no tables (synthesis, NMR, further figures and SI tables write none)"),
    "export_btn_pptx_empty": ("Die Auswahl hat keine Abbildung für Folien", "The selection has no figure for slides"),
    "export_n_of": ("{n} von {m} ausgewählt", "{n} of {m} selected"),
    "export_feeds": ("Gilt für: {items}", "Used by: {items}"),
})
TEXTS.update({                                      # Spur A2, Export v4: Kachelraster der Projektseite
    "pub_exp_tiles_hint": ("Kachel = Verbindung · Farbstreifen = vorhandene Daten · Zahl = Abbildungen in der SI · Klick "
                           "öffnet ihren Export-Tab", "Tile = compound · colour bar = data present · number = figures in the "
                           "SI · click opens its Export tab"),
    "pub_exp_n": ("{n} Verbindungen", "{n} compounds"),
    "pub_exp_count": ("Gesamt-SI mit {n} Verbindungen", "Complete SI with {n} compounds"),
    "pub_exp_dp_btn": ("Datensätze", "Datasets"),
    "pub_exp_tile_tip": ("{name}: Klick öffnet den Export-Tab der Verbindung", "{name}: click opens the compound's Export tab"),
    "pub_exp_count_tip": ("Abbildungen dieser Verbindung in der SI (Pille „SI“ in ihrem Export-Tab)",
                          "Figures of this compound in the SI (pill “SI” in its Export tab)"),
    "pub_exp_no_group": ("Ohne Gruppe", "No group"),
})
TEXTS.update({                                      # Spur A2, Entscheidung 100: Farbstreifen der Projektkacheln
    "slot_nmr": ("NMR", "NMR"), "slot_ir": ("IR", "IR"), "slot_ms": ("MS", "MS"), "slot_uvvis": ("UV-Vis", "UV-Vis"),
    "slot_uvkin": ("Kinetik", "Kinetics"), "slot_fluo": ("Fluoreszenz", "Fluorescence"), "slot_cv": ("CV", "CV"),
    "slot_sec": ("SEC", "SEC"), "slot_hcell": ("H-Cell", "H-Cell"), "slot_epr": ("EPR", "EPR"),
    "slot_xray": ("X-Ray", "X-Ray"), "slot_dft": ("DFT", "DFT"),
})
TEXTS.update({                                      # Spur A2, Punkt 4: Stilkarte (Linien je Tab)
    "tf_title_lines": ("Schrift und Linien", "Fonts and Lines"),
    "tf_title_colors": ("Schrift, Linien und Farben", "Fonts, Lines and Colours"),   # R8: nur Tabs mit Farbrollen
    "tf_line_w": ("Kurvenbreite", "Curve width"),
    "tf_line_w_tip": ("Linienbreite aller Kurven dieses Tabs als Faktor (1 × = wie gezeichnet); gilt für Vorschau, Export "
                      "und Word", "Line width of all curves of this tab as a factor (1 × = as drawn); applies to preview, "
                      "export and Word"),
    "tf_axis_w": ("Achsenlinien", "Axis lines"),
    "tf_axis_w_tip": ("Breite von Achsen, Rahmen und Strichen in pt; „Auto“ = wie gezeichnet",
                      "Width of axes, frame and ticks in pt; “Auto” = as drawn"),
})
TEXTS.update({                                      # Spur A2, Entscheidung 102: Segmente im Tab „Export“
    "export_seg_all": ("Alle", "All"),
    "export_seg_short_syn": ("Analytik", "Analysis"),
    "export_seg_short_uv": ("Photophysik", "Photophysics"),
    "export_seg_short_ec": ("Elektrochemie", "Electrochemistry"),
    "export_seg_short_struct": ("Struktur", "Structure"),
})
# nmrraw_: NMR-Tab, eigene Spektren aus Bruker-Rohdaten (1.3.0, Spur N; tabs/nmr.py)
TEXTS.update({
    "nmr_add_raw": ("Rohdaten …", "Raw data …"),
    "nmr_add_raw_tip": ("Bruker-Experiment (Ordner mit acqus und fid) als eigenes Spektrum: Fourier-Transformation, Phase "
                        "und Basislinie in Elucida, Referenz als Vorschlag. MNova-SVG bleibt der Standard.",
                        "Bruker experiment (folder with acqus and fid) as an own spectrum: Fourier transform, phase and "
                        "baseline in Elucida, reference as a suggestion. MNova SVG stays the default."),
    "nmr_raw_show": ("Als Spektrum", "As spectrum"),
    "nmr_raw_show_tip": ("Gewähltes 1D-Experiment als eigenes Spektrum zeigen (Bruker-Rohdaten statt MNova-SVG).",
                         "Show the selected 1D experiment as an own spectrum (Bruker raw data instead of MNova SVG)."),
    "nmr_raw_show_need": ("Erst ein TopSpin-Experiment in der Tabelle wählen.", "Select a TopSpin experiment in the table "
                          "first."),
    "nmr_src": ("Quelle", "Source"),
    "nmr_src_mnova": ("MNova-SVG", "MNova SVG"),
    "nmr_src_bruker": ("Bruker-Rohdaten", "Bruker raw data"),
    "nmr_src_tip": ("Abbildung und Auswertung aus dem MNova-Export (Standard) oder aus den Bruker-Rohdaten des "
                    "verknüpften Experiments.", "Figure and evaluation from the MNova export (default) or from the "
                    "Bruker raw data of the linked experiment."),
    "nmr_src_need_raw": ("Kein Bruker-Experiment verknüpft: erst unter „Rohdaten“ ablegen.",
                         "No Bruker experiment linked: add it under “Raw data” first."),
    "nmr_src_row": ("{n} (Rohdaten)", "{n} (raw data)"),
    "nmr_src_row_mnova": ("{n} (MNova)", "{n} (MNova)"),                # Langform: nmr_src_mnova_doc (Tooltip)
    "nmr_src_mnova_doc": ("Rohdaten aus MNova-Dokument", "Raw data from MNova document"),
    "nmr_mnova_refused": ("{name}: nicht gelesen ({n})", "{name}: not read ({n})"),
    # MNova-Export (MNova exportiert eine Kopie des Dokuments headless: Seiten als SVG, Berichte)
    "nmr_mx_use": ("SI-Zeile", "SI line"),
    "nmr_mx_use_mult": ("Multipletts", "Multiplets"),
    "nmr_mx_use_peaks": ("Peaks", "Peaks"),
    "nmr_mx_use_tip": ("Zeile dieses Kerns aus MNovas Multiplettbericht oder aus den Peaklabels der Abbildung",
                       "Line for this nucleus from MNova's multiplet report or from the peak labels of the figure"),
    "nmr_mx_page": ("Seite {p} ({doc})", "Page {p} ({doc})"),
    "nmr_mx_pages": ("Seiten {p} ({doc})", "Pages {p} ({doc})"),
    "nmr_mx_mixed": ("{page}: verschiedene Spektren auf einer Seite ({what}) – kein Bericht übernommen",
                     "{page}: different spectra on one page ({what}) – no report taken"),
    "nmr_mx_no_mult": ("{page}: keine Multiplettanalyse in MNova – nicht für die SI-Zeile",
                       "{page}: no multiplet analysis in MNova – not used for the SI line"),
    "nmr_mx_mult_bad": ("{page}: Multiplettbericht passt nicht zur Achse – nicht übernommen",
                        "{page}: multiplet report does not match the axis – not taken"),
    "nmr_mx_second": ("{page}: weiteres {nuc}-Spektrum mit Bericht – die Zeile kommt aus {first}",
                      "{page}: another {nuc} spectrum with a report – the line comes from {first}"),
    "nmr_mx_pending": ("MNova-Export: neue NMR-Zeilen – das Feld enthält schon Text.",
                       "MNova export: new NMR lines – the field already contains text."),
    "nmr_mx_adopt": ("Übernehmen", "Adopt"),
    "nmr_mx_keep": ("Behalten", "Keep"),
    "nmr_mx_running": ("MNova exportiert {name} … ({s} s)", "MNova is exporting {name} … ({s} s)"),
    "nmr_mx_started": ("MNova exportiert {name} … (Fortschritt in der Karte MNova)",
                       "MNova is exporting {name} … (progress in the MNova card)"),
    "nmr_mx_waiting": ("{name}: wartet auf MNova …", "{name}: waiting for MNova …"),
    "nmr_mx_done": ("{name}: {n} Spektren aus MNova übernommen.", "{name}: {n} spectra taken from MNova."),
    "nmr_mx_again": ("{name} ist schon übernommen.", "{name} has already been taken over."),
    "nmr_mx_queued": ("{name} wird schon exportiert.", "{name} is already being exported."),
    "nmr_mx_dropped": ("{name}: MNova-Export verworfen – die Verbindung wurde gewechselt.",
                       "{name}: MNova export discarded – the compound was changed."),
    "nmr_mx_fallback": ("{name}: ohne MNova-Export gelesen ({why}) – nur FIDs, eigene Verarbeitung.",
                        "{name}: read without MNova export ({why}) – FIDs only, own processing."),
    "nmr_mx_skipped": ("{page}: nicht übernommen (keine lesbare NMR-Abbildung)",
                       "{page}: not taken (no readable NMR figure)"),
    "nmr_mx_fid_open": ("Ohne eindeutig passendes Spektrum (von Hand über „Bruker-Ordner …“): {f}",
                        "Without a unique matching spectrum (link by hand via “Bruker folder …”): {f}"),
    "nmr_mx_none": ("MNova nicht gefunden", "MNova not found"),
    "nmr_mx_script": ("Exportskript fehlt", "export script missing"),
    "nmr_mx_comma": ("Komma im Pfad des Temp-Ordners", "comma in the temporary folder path"),
    "nmr_mx_failed": ("Fehler in MNova", "error in MNova"),
    "nmr_mx_exit": ("MNova ohne Ergebnis beendet", "MNova ended without a result"),
    "nmr_mx_timeout": ("Zeitgrenze überschritten", "time limit exceeded"),
    "nmr_mx_gui": ("MNova lief mit Oberfläche – bitte MNova schließen", "MNova ran with its window – please close MNova"),
    "nmr_mx_doc": ("MNova hat ein anderes Dokument geöffnet", "MNova opened a different document"),
    "nmr_mx_open": ("MNova konnte die Kopie nicht öffnen", "MNova could not open the copy"),
    "nmr_mx_empty": ("keine Seite mit Spektrum", "no page with a spectrum"),
    "nmr_raw_display": ("Darstellung", "Display"),
    "nmr_raw_style": ("Spektrum", "Spectrum"),
    "nmr_raw_only_cards": ("Verarbeitung, Referenzierung und Auswertung gelten nur für Spektren aus Bruker-Rohdaten "
                           "(Quelle im ausgewählten Spektrum).",
                           "Processing, referencing and evaluation apply only to spectra from Bruker raw data "
                           "(source in the selected spectrum)."),
    "nmr_raw_only": ("Gilt für Spektren aus Bruker-Rohdaten (Quelle im ausgewählten Spektrum).",
                     "Applies to spectra from Bruker raw data (source in the selected spectrum)."),
    "nmr_proc_card": ("Verarbeitung", "Processing"),
    "nmr_phase": ("Phase", "Phase"),
    "nmr_phase_ok": ("Bestätigen", "Confirm"),
    "nmr_phase_ok_tip": ("Phase ansehen und bestätigen (TopSpins Phase ist oft nicht gut, vor allem bei ¹³C).",
                         "Check and confirm the phase (TopSpin's phase is often poor, above all for ¹³C)."),
    "nmr_phase_acme": ("Vorschlag", "Suggest"),
    "nmr_phase_acme_tip": ("Automatischer Phasenvorschlag (ACME, Chen 2002): nur ein Vorschlag, nicht belastbar.",
                           "Automatic phase suggestion (ACME, Chen 2002): only a suggestion, not reliable."),
    "nmr_phase_acme_busy": ("Rechnet …", "Working …"),
    "nmr_phase_manual": ("Von Hand (⇧P)", "Manual (⇧P)"),
    "nmr_phase_manual_tip": ("Phase im Bild ziehen: linke Taste 0. Ordnung, rechte 1. Ordnung, Klick setzt den Drehpunkt "
                             "(wie MNova Shift+P).", "Drag the phase in the figure: left button zero order, right button "
                             "first order, a click sets the pivot (like MNova Shift+P)."),
    "nmr_phst_procs": ("Aus procs ({ph})", "From procs ({ph})"),
    "nmr_phst_manual": ("Von Hand ({ph})", "Manual ({ph})"),
    "nmr_phst_topspin": ("TopSpins Spektrum (1r), zusätzlich {ph}", "TopSpin's spectrum (1r), additional {ph}"),
    "nmr_phst_none": ("procs ohne Phase: {ph}", "procs without phase: {ph}"),
    "nmr_phst_acme": ("ACME-Vorschlag ({ph})", "ACME suggestion ({ph})"),
    "nmr_ok": ("bestätigt", "confirmed"),
    "nmr_not_ok": ("nicht bestätigt", "not confirmed"),
    "nmr_baseline": ("Basislinie", "Baseline"),
    "nmr_baseline_auto": ("Automatisch (Polynom 5. Grades)", "Automatic (fifth-order polynomial)"),
    "nmr_baseline_off": ("Aus", "Off"),
    "nmr_baseline_bernstein3": ("Bernstein 3. Grades (MNova)", "Third-order Bernstein (MNova)"),
    "nmr_nuc_from_acqus": ("Kern aus acqus (NUC1).", "Nucleus from acqus (NUC1)."),
    "nmr_baseline_long": ("Basislinie durch die signalfreien Punkte (Golotvin–Williams). Standard: Polynom 5. Grades wie "
                          "TopSpin ABSG 5 (an TopSpin geprüft). Bernstein 3. Grades ist MNovas Vorgabe „Advised“: "
                          "dasselbe Modell, MNovas Punktwahl ist nicht nachgebaut und nicht geprüft. Ohne Korrektur "
                          "liegen Integrale im Mittel um 11 % daneben.",
                          "Baseline through the signal-free points (Golotvin–Williams). Default: fifth-order polynomial "
                          "like TopSpin ABSG 5 (checked against TopSpin). Third-order Bernstein is MNova's “Advised” "
                          "setting: the same model, MNova's choice of points is not rebuilt and not checked. Without "
                          "correction integrals are off by 11 % on average."),
    "nmr_signed_note": ("DEPT/APT: Vorzeichen zählt, Phase nur aus procs, keine Integrale.",
                        "DEPT/APT: the sign matters, phase only from procs, no integrals."),
    "nmr_ref_card": ("Referenzierung", "Referencing"),
    "nmr_ref_state": ("Referenz", "Reference"),
    "nmr_ref_target": ("Sollwert", "Target δ"),
    "nmr_ref_target_tip": ("δ, das die Referenzspitze bekommt (Vorgabe: Restsignal nach Fulmer 2010). Klick im Modus R "
                           "setzt die getroffene Spitze auf diesen Wert.", "δ given to the reference peak (default: "
                           "residual signal after Fulmer 2010). A click in mode R puts the hit peak on this value."),
    "nmr_ref_ok": ("Bestätigen", "Confirm"),
    "nmr_ref_ok_tip": ("Gefundenes Restsignal als Referenz übernehmen. Liegt es in einem Signal der Verbindung, ist der "
                       "Vorschlag verschoben: dann im Modus R die richtige Spitze anklicken.",
                       "Take the found residual signal as reference. If it lies in a signal of the compound, the "
                       "suggestion is shifted: then click the right peak in mode R."),
    "nmr_ref_click": ("Spitze wählen (R)", "Pick peak (R)"),
    "nmr_ref_click_tip": ("Modus R: Spitze im Bild anklicken, sie bekommt den Sollwert (wie MNova).",
                          "Mode R: click a peak in the figure, it gets the target δ (like MNova)."),
    "nmr_ref_none": ("nicht gesetzt: Achse unkalibriert (SF = BF1, TopSpins Kalibrierung wird nie übernommen)",
                     "not set: axis uncalibrated (SF = BF1, TopSpin's calibration is never used)"),
    "nmr_refst_fulmer": ("Restsignal bei {f} → {t} ppm (Verschiebung {d} ppm)", "residual signal at {f} → {t} ppm "
                         "(shift {d} ppm)"),
    "nmr_refst_click": ("gewählte Spitze → {t} ppm (Verschiebung {d} ppm)", "picked peak → {t} ppm (shift {d} ppm)"),
    "nmr_ref_nominal": ("{nuc}: kein Lösungsmittelsignal als Referenz; Achse nominell, nicht probenkalibriert.",
                        "{nuc}: no solvent signal as reference; axis nominal, not calibrated on the sample."),
    "nmr_raw_is_2d": ("{name}: 2D-Experiment: eigene Darstellung folgt; vorerst als Rohdaten abgelegt.",
                      "{name}: 2D experiment: own display to follow; stored as raw data for now."),
    "nmr_raw_missing": ("{name}: Experimentordner fehlt oder ohne acqus.", "{name}: experiment folder missing or "
                        "without acqus."),
    "nmr_ana_card": ("Auswertung", "Evaluation"),
    "nmr_mult_auto": ("Multipletts vorschlagen", "Suggest multiplets"),
    "nmr_mult_auto_tip": ("Signale erster Ordnung (Hoye 1994) suchen, Unsicheres als „m“. Nur Vorschläge: jedes Signal "
                          "einzeln prüfen und bestätigen. Bestätigte und von Hand gesetzte Signale bleiben.",
                          "Find first-order signals (Hoye 1994), uncertain ones as “m”. Only suggestions: check and "
                          "confirm every signal. Confirmed and manually set signals are kept."),
    "nmr_peaks_auto": ("Peaks vorschlagen", "Suggest peaks"),
    "nmr_peaks_auto_tip": ("Alle Peaks ab 5σ (¹³C-Liste) ohne das Restsignal; Überzähliges im Modus K wählen und mit "
                           "Entf löschen.", "All peaks from 5σ (¹³C list) without the residual signal; pick extra ones "
                           "in mode K and delete them with Del."),
    "nmr_sig_status": ("Status", "Status"),
    "nmr_sig_empty": ("Keine Signale: „Multipletts vorschlagen“ oder im Bild J drücken und einen Bereich aufziehen.",
                      "No signals: “Suggest multiplets” or press J in the figure and drag a range."),
    "nmr_cls_tip": ("Klasse des gewählten Signals (s, d, t, q, p, dd, dt …, m). „m“ = Bereich + m ohne J.",
                    "Class of the selected signal (s, d, t, q, p, dd, dt …, m). “m” = range + m without J."),
    "nmr_j_tip": ("Kopplungen in Hz, durch Komma getrennt, für „Muster anpassen“.",
                  "Couplings in Hz, separated by commas, for “Fit pattern”."),
    "nmr_nh": ("Kerne", "Nuclei"),
    "nmr_nh_tip": ("Anzahl H des Signals; „Auto“ = Integral × Normierung, gerundet.",
                   "Number of H of the signal; “Auto” = integral × normalization, rounded."),
    "nmr_fit": ("Muster anpassen", "Fit pattern"),
    "nmr_fit_tip": ("Klasse und J im Bereich des Signals suchen; die gefundenen Linien stehen als Striche über dem "
                    "Spektrum (orange = Vorschlag).", "Search class and J in the range of the signal; the found lines "
                    "are drawn as ticks above the spectrum (orange = suggestion)."),
    "nmr_sig_ok": ("Bestätigen", "Confirm"),
    "nmr_sig_ok_tip": ("Nur dieses Signal bestätigen (Linien im Bild ansehen). Gedruckt werden δ und J nur bestätigter "
                       "Signale, sonst Bereich + m.", "Confirm only this signal (look at the lines in the figure). δ "
                       "and J are printed only for confirmed signals, otherwise range + m."),
    "nmr_j_take": ("J übernehmen", "Take J"),
    "nmr_j_take_tip": ("Eingegebene Kopplung, deren Linien nicht getrennt sind, trotzdem drucken (eigene Entscheidung, "
                       "nicht Teil von „Bestätigen“).", "Print an entered coupling whose lines are not resolved "
                       "anyway (own decision, not part of “Confirm”)."),
    "nmr_j_drop": ("Ohne dieses J", "Without this J"),
    "nmr_j_drop_tip": ("Muster ohne das nicht gemessene J neu anpassen (z. B. dd -> d): δ und die getrennten J bleiben, "
                       "danach wie üblich bestätigen.", "Fit the pattern again without the unmeasured J (e.g. dd -> d): "
                       "δ and the resolved J stay, then confirm as usual."),
    "nmr_sig_del_tip": ("Gewähltes Signal entfernen.", "Remove the selected signal."),
    "nmr_norm": ("Normierung", "Normalization"),
    "nmr_norm_set": ("Setzen", "Set"),
    "nmr_norm_tip": ("Gewähltes Integral (Modus I) oder gewähltes Signal hat so viele Kerne; alle Integrale und nH "
                     "folgen.", "The selected integral (mode I) or selected signal has this many nuclei; all "
                     "integrals and nH follow."),
    "nmr_norm_need": ("Erst ein Integral (Modus I) oder ein Signal wählen.", "Select an integral (mode I) or a signal "
                      "first."),
    "nmr_norm_state": ("Normiert: {lo} – {hi} ppm = {n} H.", "Normalized: {lo} – {hi} ppm = {n} H."),
    "nmr_norm_none": ("Nicht normiert: Kerne erst nach „Normierung“ (Integrale zeigen das erste = 1).",
                      "Not normalized: nuclei only after “Normalization” (integrals show the first = 1)."),
    "nmr_mult_found": ("{n} Signale vorgeschlagen.", "{n} signals suggested."),
    "nmr_peaks_found": ("{n} Peaks vorgeschlagen.", "{n} peaks suggested."),
    "nmr_peaks_rest": ("{n} weitere Maxima über 5σ liegen näher als 1 Hz an einem höheren (Rauschen auf Flanken): "
                       "bei Bedarf im Modus K wählen.", "{n} further maxima above 5σ lie closer than 1 Hz to a higher one "
                       "(noise on flanks): pick them in mode K if needed."),
    "nmr_j_bad": ("J nicht lesbar: Zahlen durch Komma trennen.", "J not readable: separate numbers by commas."),
    "nmr_sigst_confirmed": ("bestätigt", "confirmed"),
    "nmr_sigst_suggested": ("Vorschlag", "suggestion"),
    "nmr_sigst_unmeasured": ("J nicht gemessen", "J not measured"),
    "nmr_si_fig": ("SI-Abbildung", "SI Figure"),
    "nmr_raw_assign_tip": ("Zuordnung des Signals für die SI-Zeile (*kursiv*, _{tief}, ^{hoch}).",
                       "Assignment of the signal for the SI line (*italic*, _{sub}, ^{sup})."),
    "nmr_marks_note": ("Marken", "Marks"),
    "nmr_si_range": ("Bereich", "Range"),
    "nmr_si_range_tip": ("Bereich der SI-Abbildung in ppm. „Auto“: 9 bis 0 ppm (¹H) bzw. 200 bis 0 ppm (¹³C), erweitert, bis "
                         "jedes Signal der SI-Zeile mit Rand innen liegt (Hydride, Carbene); andere Kerne das ganze Spektrum. "
                         "Ein eigener Bereich bleibt, ein Signal außerhalb wird gemeldet. Zoomen in der Ansicht ändert die "
                         "Abbildung nicht.",
                         "Range of the SI figure in ppm. “Auto”: 9 to 0 ppm (¹H) or 200 to 0 ppm (¹³C), widened until every "
                         "signal of the SI line lies inside with a margin (hydrides, carbenes); other nuclei the whole spectrum. "
                         "An own range stays; a signal outside it is reported. Zooming in the view does not change the figure."),
    "nmr_marks_ph": ("* = H2O", "* = H2O"),
    "nmr_marks_tip": ("Bedeutung der Marken (Modus T) für die Bildunterschrift, z. B. „* = H2O, † = Et2O“.",
                      "Meaning of the marks (mode T) for the caption, e.g. “* = H2O, † = Et2O”."),
    "nmr_sig_unprintable": ("Signal bei {d} ppm nicht schreibbar ({e}): fehlt in der Zeile.",
                            "Signal at {d} ppm cannot be written ({e}): left out of the line."),
    "nmr_own_line": ("{nuc}: Zeile aus den Rohdaten (ersetzt den MNova-Text dieses Kerns).",
                     "{nuc}: line from the raw data (replaces the MNova text of this nucleus)."),
    "nmr_own_ref": ("Referenz nicht bestätigt", "reference not confirmed"),
    "nmr_own_phase": ("Phase nicht bestätigt", "phase not confirmed"),
    "nmrv_labels_crowded": ("Zu viele Labels für die Breite – Ausschnitt anlegen oder Peaks ausdünnen.",
                            "Too many labels for the width – add an inset or thin out the peaks."),
    "nmrv_inset_nofree": ("Ausschnitt: kein freier Platz über dem Spektrum, verkleinert an die Labelreihe gesetzt "
                          "(im Bild ziehen oder Bereich ändern).", "Inset: no free space above the spectrum, made smaller "
                          "and put at the label row (drag it in the figure or change the range)."),
    "nmr_2d_own": ("2D aus ser selbst verarbeitet.", "2D processed from ser."),
    "nmr_2d_2rr": ("TopSpins 2rr (eigene Verarbeitung nicht geprüft für diesen Satz).",
                   "TopSpin's 2rr (own processing not checked for this set)."),
    "nmr_2d_cal": ("{dim} über das bestätigte {nuc}-Spektrum referenziert ({d} ppm).",
                   "{dim} referenced via the confirmed {nuc} spectrum ({d} ppm)."),
    "nmr_2d_uncal": ("{dim} unkalibriert (SF = BF1): erst ein eigenes {nuc}-Spektrum desselben Magneten referenzieren.",
                     "{dim} uncalibrated (SF = BF1): reference an own {nuc} spectrum of the same magnet first."),
    "nmr_xi_btn": ("Über ¹H (Ξ)", "Via ¹H (Ξ)"),
    "nmr_xi_tip": ("Achse auf die IUPAC-Skala (Ξ, Harris 2001) über das eigene ¹H-Spektrum derselben Probe am selben "
                   "Magneten mit bestätigter Referenz; danach bestätigen. Ohne das bleibt die Achse nominell, nicht "
                   "probenkalibriert.", "Axis on the IUPAC scale (Ξ, Harris 2001) via the own ¹H spectrum of the same "
                   "sample on the same magnet with a confirmed reference; confirm it afterwards. Without it the axis "
                   "stays nominal, not calibrated on the sample."),
    "nmr_xi15": ("¹⁵N-Skala", "¹⁵N scale"),
    "nmr_xi15_MeNO2": ("¹⁵N gegen MeNO2", "¹⁵N vs. MeNO2"),
    "nmr_xi15_NH3": ("¹⁵N gegen NH3 (flüssig)", "¹⁵N vs. NH3 (liquid)"),
    "nmr_xi15_tip": ("Bezug der ¹⁵N-Skala (Ξ 10.136767 bzw. 10.132912).", "Reference of the ¹⁵N scale (Ξ 10.136767 or "
                     "10.132912)."),
    "nmr_xi_none": ("{nuc}: kein doppelt geprüfter Ξ-Wert: Unified Scale nicht möglich, Referenz von Hand setzen.",
                    "{nuc}: no double-checked Ξ value: unified scale not possible, set the reference by hand."),
    "nmr_xi_ratio": ("BF1-Verhältnis {r} passt nicht zu Ξ/100 = {xi}: anderer Magnet oder Kern.",
                     "BF1 ratio {r} does not match Ξ/100 = {xi}: another magnet or nucleus."),
    "nmr_xi_noh": ("Kein eigenes ¹H-Spektrum derselben Probe mit bestätigter Referenz: erst das ¹H referenzieren.",
                   "No own ¹H spectrum of the same sample with a confirmed reference: reference the ¹H first."),
    "nmr_xi_done": ("Unified Scale über {h} (Ξ = {xi} %).", "Unified scale via {h} (Ξ = {xi} %)."),
    "nmr_refst_unified": ("Unified Scale (Verschiebung {d} ppm)", "unified scale (shift {d} ppm)"),
    "nmr_refst_mnova": ("Referenzierung aus dem MNova-Dokument (Verschiebung {d} ppm)",
                        "referencing from the MNova document (shift {d} ppm)"),
    "nmr_peaks_ok": ("Peaks bestätigen", "Confirm peaks"),
    "nmr_peaks_ok_tip": ("Peakliste so in die SI-Zeile übernehmen (vorher Überzähliges im Modus K wählen und löschen); "
                         "jede Änderung der Peaks hebt das wieder auf.", "Take the peak list as it is into the SI line "
                         "(first pick extra peaks in mode K and delete them); every change of the peaks undoes this."),
    "nmr_raw_reverse": ("{name}: gespeichertes Spektrum gespiegelt oder als Streifen gerechnet ({why}): Achse nicht "
                        "bestimmbar, nicht gezeigt.", "{name}: stored spectrum reversed or strip-transformed ({why}): "
                        "axis cannot be determined, not shown."),
    "nmr_si_use": ("Eigene Verarbeitung für die SI", "Use own processing in SI"),   # R7: ob NMR in die SI kommt,
                                                    # entscheidet der Teil „NMR-Spektren“ im Tab Export (Vorschlag)
    "nmr_si_use_long": ("Dieses eigene Spektrum ersetzt Zeile und Abbildung des Kerns in der SI, sobald Phase und Referenz "
                        "bestätigt sind (je Kern höchstens eines). Sonst bleibt der MNova-Export.",
                        "This own spectrum replaces line and figure of its nucleus in the SI once phase and reference are "
                        "confirmed (at most one per nucleus). Otherwise the MNova export stays."),
    "nmr_own_none": ("kein eigenes Spektrum", "no own spectrum"),
    "nmr_own_not_chosen": ("nicht „für die SI“ gewählt", "not chosen “for the SI”"),
    "nmr_own_held": ("{nuc}: {f} nicht in der SI ({why}); es bleibt der MNova-Export.",
                     "{nuc}: {f} not in the SI ({why}); the MNova export stays."),
    "nmr_own_second": ("{nuc}: {f} ebenfalls „für die SI“ gewählt, aber nur ein eigenes Spektrum je Kern: nicht in der SI.",
                       "{nuc}: {f} also chosen “for the SI”, but only one own spectrum per nucleus: not in the SI."),
    "nmr_own_open": ("{nuc}: {n} Vorschläge offen (nicht gedruckt, erst bestätigen).",
                     "{nuc}: {n} suggestions open (not printed, confirm them first)."),
    "nmr_own_empty": ("{nuc}: noch kein bestätigtes Signal: es bleibt der MNova-Text.",
                      "{nuc}: no confirmed signal yet: the MNova text stays."),
    "nmr_fig_mnova": ("MNova-Abbildung statt der eigenen ({why}).", "MNova figure instead of the own one ({why})."),
    "nmr_held_line": ("Zurückgehalten, eigene Abbildungen ohne Freigabe (nicht in Word): {n}.",
                      "Withheld, own figures without release (not in Word): {n}."),
    "nmr_held_head": ("Zurückgehalten (eigene Abbildung nicht freigegeben):", "Withheld (own figure not released):"),
    "nmr_details": ("Details", "Details"),
    "nmr_fig_none": ("Eigene Abbildung nicht in Word ({why}).", "Own figure not in Word ({why})."),
    "nmr_no_1i": ("TopSpins 1r ohne 1i: Phase nicht änderbar (kein Imaginärteil).",
                  "TopSpin's 1r without 1i: phase cannot be changed (no imaginary part)."),
    "nmr_refst_nominal": ("nominelle Achse (Verschiebung {d} ppm)", "nominal axis (shift {d} ppm)"),
    "nmr_sigst_taken": ("J übernommen", "J taken"),
    "nmr_2d_nominal": ("Achsen nominell", "Nominal axes"),
    "nmr_2d_nominal_long": ("Eigenes 2D ohne referenziertes eigenes 1D desselben Magneten: die nominellen Achsen (SF = BF1) "
                            "ausdrücklich für die SI übernehmen.", "Own 2D without a referenced own 1D of the same magnet: "
                            "take the nominal axes (SF = BF1) explicitly for the SI."),
    "nmr_2d_uncal_held": ("2D-Achsen unkalibriert: erst ein eigenes 1D desselben Magneten referenzieren oder „Achsen "
                          "nominell“ wählen", "2D axes uncalibrated: reference an own 1D of the same magnet first or choose "
                          "“Nominal axes”"),
    "nmr_raw_unreadable": ("Rohdaten nicht lesbar", "raw data not readable"),
    "nmr_peaks_svg_only": ("Peaks aus den Beschriftungen gibt es nur für MNova-SVG.",
                           "Peaks from labels exist only for MNova SVG."),
})

# Stilkarte: Farbrollen je Tab (feste Standardfarben ohne Messungsliste)
TEXTS.update({
    "tf_col_start": ("Farbe Start", "Start Colour"),
    "tf_col_end": ("Farbe Ende", "End Colour"),
    "tf_col_charge": ("Farbe Laden", "Charge Colour"),
    "tf_col_discharge": ("Farbe Entladen", "Discharge Colour"),
    "tf_col_ce": ("Farbe CE", "CE Colour"),
    "tf_col_meas": ("Farbe gemessen", "Measured Colour"),
    "tf_col_calc": ("Farbe berechnet", "Calculated Colour"),
    "tf_col_fit": ("Farbe Fit", "Fit Colour"),
    # R8 (Entscheidung 155): Grund im Tooltip eines ausgegrauten Farbknopfs der Stilkarte
    "tf_idle_many": ("Mehrere Messungen: jede in ihrer Farbe aus der Messungsliste",
                     "Several measurements: each in its colour from the measurement list"),
    "tf_idle_own": ("Die Messung hat eine eigene Farbe (Messungsliste)", "The measurement has its own colour (measurement list)"),
    "tf_idle_ce": ("CE ist nicht im Bild", "CE is not in the figure"),
    "tf_idle_series": ("Mehrere Reihen: jeder Fit in der Farbe seiner Reihe", "Several series: each fit in the colour of its series"),
    "tf_idle_fit": ("Keine Fitkurve im Bild", "No fit curve in the figure"),
    "tf_idle_calc": ("Kein berechnetes Isotopenmuster im Bild", "No calculated isotope pattern in the figure"),
    "tf_idle_spectra": ("Nur in der Ansicht „Spektrenserie“", "Only in the “Spectral series” view"),
    "tf_idle_sec_curves": ("Wirkt nur mit „Erstes/letztes hervorheben“ ohne Farbverlauf oder mit λ-Labels",
                           "Only applies with “Highlight first/last” without colour gradient, or with λ labels"),
    "tf_idle_single": ("Nur ein Spektrum: es trägt die Endfarbe", "Only one spectrum: it uses the end colour"),
})

# Nachzügler Z1 (1.3.0): SEC-Referenzfeld (Entscheidung 82), Pfadliste als Tabelle (R12)
TEXTS.update({
    "z1_sec_ref_e12": ("Referenz E½ (CV)", "Reference E½ (CV)"),
    "z1_sec_ref_e12_long": ("Referenz E½ (aus CV)", "Reference E½ (from CV)"),
    "z1_sec_ref_e12_named": ("E½ {name} (CV)", "E½ {name} (CV)"),
    "z1_sec_ref_e12_named_long": ("E½ {name} (aus CV)", "E½ {name} (from CV)"),
    "z1_sec_ref_shift": ("Verschiebung (CV)", "Shift (CV)"),
    "z1_sec_ref_shift_long": ("Verschiebung aus dem CV-Tab", "Shift from the CV tab"),
    "z1_sec_ref_shift_tip": ("Verschiebung, mit der der CV-Tab rechnet (von Hand, ohne gefundene Referenz 0): dort ändern. "
                             "Der eigene Wert gilt wieder ohne den Chip.",
                             "Shift used by the CV tab (manual, 0 without a reference found): change it there. Your own "
                             "value applies again without the chip."),
    "z1_sec_ref_e12_tip": ("E½ der im CV-Tab gewählten Referenz, gemessen gegen die Elektrode: dort ändern. Die Achse "
                           "rechnet mit E½ minus dem Wert der Referenz gegen Fc⁰/⁺. Der eigene Wert gilt wieder ohne "
                           "den Chip.",
                           "E½ of the reference chosen in the CV tab, measured against the electrode: change it there. "
                           "The axis uses E½ minus the value of the reference vs. Fc⁰/⁺. Your own value applies again "
                           "without the chip."),
    "z1_rp_paths_head": ("Reaktionspfad", "Reaction path"),
})

# mnovadoc_: FID + Bruker-Parameter aus einem Mnova-Dokument (1.3.0, formats/mnova_doc.py, Entscheidungen 54/95)
TEXTS.update({
    "mnovadoc_not_mnova": ("{name}: kein MNova-Dokument (Kennung fehlt): nicht gelesen.",
                           "{name}: not an MNova document (signature missing): not read."),
    "mnovadoc_version": ("{name}: MNova-Version {v} wird nicht gelesen (unterstützt: MNova {ok}).",
                         "{name}: MNova version {v} is not read (supported: MNova {ok})."),
    "mnovadoc_where": ("{name}, Datensatz {k}", "{name}, data set {k}"),
    "mnovadoc_no_params": ("{where}: nicht übernommen (kein Messspektrum: Daten ohne acqus/procs).",
                           "{where}: not taken (no measured spectrum: data without acqus/procs)."),
    "mnovadoc_pseudo": ("{where} ({what}): nicht übernommen (kein Messspektrum: Pseudo-2D/Reihe).",
                        "{where} ({what}): not taken (no measured spectrum: pseudo-2D/series)."),
    "mnovadoc_copies": ("{where}: gespeicherte Kopien von acqus/procs unterscheiden sich: nicht gelesen.",
                        "{where}: stored copies of acqus/procs differ: not read."),
    "mnovadoc_2d": ("{where} ({what}): 2D-Spektrum, aus einem MNova-Dokument nicht gelesen (TopSpin-Ordner verwenden).",
                    "{where} ({what}): 2D spectrum, not read from an MNova document (use the TopSpin folder)."),
    "mnovadoc_not_raw": ("{where}: Werte sind keine ganzen Zahlen (kein Bruker-FID): nicht gelesen.",
                         "{where}: values are not integers (not a Bruker FID): not read."),
    "mnovadoc_none": ("{name}: kein 1D-Spektrum mit Rohdaten (FID + acqus/procs) gefunden.",
                      "{name}: no 1D spectrum with raw data (FID + acqus/procs) found."),
    "mnovadoc_ref_unmatched": ("MNovas Achse: kein Eintrag gleich der Bruker-Referenzierung, kein Referenzvorschlag aus "
                               "MNova.", "MNova axis: no entry equals the Bruker referencing, no reference suggestion "
                               "from MNova."),
    "mnovadoc_ref_ambiguous": ("MNovas Achse: mehrere abweichende Einträge, kein Referenzvorschlag aus MNova.",
                               "MNova axis: several differing entries, no reference suggestion from MNova."),
    "mnovadoc_param": ("{name}: Parameter {key} = {v} ist ungültig (endliche Zahl > 0, SI ganzzahlig bis 2^22): nicht "
                       "gelesen.", "{name}: parameter {key} = {v} is invalid (finite number > 0, SI an integer up to "
                       "2^22): not read."),
    "mnovadoc_file_big": ("{where}: eingebettete Datei {file} größer als {mb} MB: nicht gelesen.",
                          "{where}: embedded file {file} larger than {mb} MB: not read."),
    "mnovadoc_param_dsp": ("{name}: Parameter {key} = {v} ist ungültig (endliche Zahl erwartet): nicht gelesen.",
                           "{name}: parameter {key} = {v} is invalid (finite number expected): not read."),
    "mnovadoc_unpack_total": ("{name}: eingebettete Dateien zusammen größer als {mb} MB: Dokument nicht gelesen.",
                              "{name}: embedded files larger than {mb} MB in total: document not read."),
    "mnovadoc_item_error": ("{where}: unerwarteter Fehler beim Lesen ({err}): nicht gelesen.",
                            "{where}: unexpected error while reading ({err}): not read."),
    "mnovadoc_ref_large": ("MNovas Achse: |Verschiebung| ({v} ppm) größer als {max} ppm, kein Referenzvorschlag aus "
                           "MNova.", "MNova axis: |shift| ({v} ppm) larger than {max} ppm, no reference suggestion from "
                           "MNova."),
    "mnovadoc_temp": ("{name}: temporärer Ordner nicht nutzbar ({err}): Dokument nicht gelesen.",
                      "{name}: temporary folder not usable ({err}): document not read."),
    "mnovadoc_not_finite": ("{where}: Werte enthalten NaN oder unendlich: nicht gelesen.",
                            "{where}: values contain NaN or infinity: not read."),
    "mnovadoc_int_range": ("{where}: ganze Zahlen ab 2^24 sind als float32 nicht genau prüfbar: nicht gelesen.",
                           "{where}: integers from 2^24 on cannot be checked exactly as float32: not read."),
    "mnovadoc_not_fid": ("{where}: Daten sehen nicht wie ein FID aus (Maximum bei Punkt {i}, Gruppenlaufzeit {g}): "
                         "nicht gelesen.", "{where}: data do not look like a FID (maximum at point {i}, group delay "
                         "{g}): not read."),
})

# Projekt-Datensätze: Verbindungen abwählbar (Entscheidungen 118/120)
TEXTS.update({
    "pub_exp_zip": ("Zip", "Zip"),
    "act_copy_figure": ("Abbildung kopieren (SVG)", "Copy Figure (SVG)"),
    "copy_fig_done": ("Abbildung als SVG kopiert (mit PNG-Ersatz).", "Figure copied as SVG (with PNG fallback)."),
    "copy_fig_none": ("Hier ist keine Abbildung zum Kopieren.", "There is no figure here to copy."),
    "copy_fig_page": ("Auf dieser Seite lässt sich keine Abbildung kopieren – rechts den Reiter „Abbildung“ wählen.",
                      "No figure to copy on this page – choose the “Figure” tab on the right."),
    "copy_fig_held": ("Nicht kopiert: eigene Abbildung nicht freigegeben ({why}).",
                      "Not copied: own figure not released ({why})."),
    "copy_fig_failed": ("Abbildung nicht kopiert: {e}", "Figure not copied: {e}"),
    "pub_exp_zip_tip": ("Im Datensatz (Zip) – Klick nimmt die Verbindung heraus. Gespeichert im Projekt; eine "
                        "abgewählte Verbindung bekommt keine eigenen Dateien (Zip, CompChem, FID, README). Ihr "
                        "Kürzel wird in den übrigen Dateien weiter ersetzt.",
                        "In the dataset (zip) – click takes the compound out. Saved with the project; a deselected "
                        "compound gets no files of its own (zip, CompChem, FID, README). Its lab code is still "
                        "replaced in the other files."),
    "pub_dp_leftover": ("Ältere Dateien abgewählter Verbindungen liegen noch im Ordner (nicht gelöscht): {files}",
                        "Older files of deselected compounds are still in the folder (not deleted): {files}"),
    "pub_exp_zip_links": ("Zip: <a href=\"all\">Alle</a> · <a href=\"none\">Keine</a>",
                          "Zip: <a href=\"all\">All</a> · <a href=\"none\">None</a>"),
    "pub_exp_dp_btn_n": ("Datensätze ({n} von {m})", "Datasets ({n} of {m})"),
})

TEXTS.update({                                            # NMR-Vergleiche und Vorhersage (Nutzerentscheid 2026-11-20)
    "nmr_cmp_single": ("Einzeln", "Single"),
    "nmr_cmp_overlay": ("Überlagert", "Overlaid"),
    "nmr_cmp_stack": ("Gestapelt", "Stacked"),
    "nmr_cmp_offset": ("Versatz", "Offset"),
    "nmr_cmp_offset_tip": ("Abstand der gestapelten Spuren in % ihrer Höhe.", "Spacing of the stacked traces in % of their height."),
    "nmr_cmp_mode_tip": ("Eigene 1D-Spektren desselben Kerns und Lösungsmittels einzeln, überlagert oder gestapelt zeigen; "
                         "welche, wählt das Häkchen in der Liste „Spektren“. Überlagert und Gestapelt kommen als Abbildung "
                         "in Export und SI.",
                         "Show own 1D spectra of the same nucleus and solvent single, overlaid or stacked; the tick in the "
                         "“Spectra” list chooses which. Overlaid and Stacked go into export and SI as a figure."),
    "nmr_cmp_need_own": ("Nur für eigene 1D-Spektren (Bruker-FID oder FID aus .mnova): ein MNova-Bild ist eine Grafik und "
                         "lässt sich nicht überlagern.",
                         "Only for own 1D spectra (Bruker FID or FID from .mnova): an MNova image is a picture and cannot "
                         "be overlaid."),
    "nmr_cmp_check_tip": ("Spektrum im Vergleich (Überlagert, Gestapelt)", "Spectrum in the comparison (Overlaid, Stacked)"),
    "nmr_cmp_card": ("NMR-Vergleich", "NMR Comparison"),
    "nmr_cmp_label": ("Beschriftung", "Label"),
    "nmr_cmp_label_tip": ("Beschriftung der gewählten Spur im Bild; leer = Temperatur (wenn sie sich unterscheidet), sonst "
                          "der Dateiname.",
                          "Label of the selected trace in the figure; empty = temperature (if it differs), otherwise the "
                          "file name."),
    "nmr_cmp_caption": ("Satz", "Sentence"),
    "nmr_cmp_caption_long": ("Satz der Bildunterschrift (nach den Messangaben)", "Sentence of the caption (after the measurement data)"),
    "nmr_cmp_caption_ph": ("Z. B. Signale der Vorstufe mit * markiert.", "E.g. Signals of the precursor marked with *."),
    "nmr_cmp_heading": ("SI-Überschrift", "SI heading"),
    "nmr_cmp_heading_tip": ("Überschrift der Vergleiche in der SI (Einzel-SI nach den Spektren, Gesamt-SI als Unterkapitel am "
                            "Ende des NMR-Kapitels).",
                            "Heading of the comparisons in the SI (single SI after the spectra, complete SI as a subchapter "
                            "at the end of the NMR chapter)."),
    "nmr_cmp_hint": ("Häkchen in der Liste „Spektren“ wählen die Spuren; ein Vergleich je Kern. In die SI nur mit bestätigter "
                     "Phase und Referenz jeder Spur.",
                     "Ticks in the “Spectra” list choose the traces; one comparison per nucleus. Into the SI only with "
                     "confirmed phase and reference of every trace."),
    "nmr_cmp_active": ("aktiv", "active"),
    "nmr_cmp_not_member": ("Das gewählte Spektrum ist nicht angehakt: es steht in der Ansicht oben, aber nicht in der Abbildung.",
                           "The selected spectrum is not ticked: it is on top in the view but not in the figure."),
    "nmr_cmp_ref": ("Referenz nicht bestätigt: {names}. Lage gegenüber {what} unsicher.",
                    "Reference not confirmed: {names}. Position relative to {what} uncertain."),
    "nmr_cmp_ref_pred": ("der Vorhersage", "the prediction"),
    "nmr_cmp_ref_other": ("den anderen Spektren", "the other spectra"),
    "nmr_cmp_ref_both": ("Vorhersage und anderen Spektren", "prediction and other spectra"),
    "nmr_cmp_few": ("Vergleich {nuc}: weniger als zwei Spektren angehakt", "Comparison {nuc}: fewer than two spectra ticked"),
    "nmr_cmp_solvent": ("Vergleich {nuc}: Spektren in verschiedenen Lösungsmitteln", "Comparison {nuc}: spectra in different solvents"),
    "nmr_cmp_unconfirmed": ("Vergleich {nuc}: Phase oder Referenz nicht bei jeder Spur bestätigt",
                            "Comparison {nuc}: phase or reference not confirmed for every trace"),
    "nmr_cmp_withheld": ("{why} – nicht in Export und SI.", "{why} – not in export and SI."),
    "nmr_rng_out": ("Signal δ {sig} außerhalb des Bildbereichs", "Signal δ {sig} outside the image range"),
    "nmr_pred": ("Vorhersage", "Prediction"),
    "nmr_pred_lane": ("Vorhersage (Octet)", "Prediction (Octet)"),
    "nmr_pred_tip": ("Octets NMR-Vorhersage für die Struktur der Verbindung als zusätzliche Spur (nur auf Klick, nur Ansicht: "
                     "nie in Export, SI, Word, PPTX, Datenpaket oder Zwischenablage).",
                     "Octet's NMR prediction for the compound's structure as an extra trace (on click only, view only: "
                     "never in export, SI, Word, PPTX, data package or clipboard)."),
    "nmr_pred_need_struct": ("Vorhersage braucht eine gezeichnete Struktur (CDXML) der Verbindung.",
                             "Prediction needs a drawn structure (CDXML) of the compound."),
    "nmr_pred_need_nuc": ("Vorhersage nur für ¹H, ¹³C, ¹⁹F und ³¹P.", "Prediction only for ¹H, ¹³C, ¹⁹F and ³¹P."),
    "nmr_pred_running": ("Vorhersage wird gerechnet …", "Computing the prediction …"),
    "nmr_pred_failed": ("Vorhersage nicht möglich: {e}", "Prediction not possible: {e}"),
    "nmr_pred_none": ("Octet hat für diese Struktur keine Vorhersage ({nuc}).", "Octet has no prediction for this structure ({nuc})."),
    "nmr_pred_frame": ("Vorhersage von Octet für die Struktur der Verbindung: nur Ansicht, nie in Export oder SI.",
                       "Octet's prediction for the compound's structure: view only, never in export or SI."),
    "nmr_pred_xnuc": ("{nuc}-Vorhersage: Octets Tabelle ist für diesen Kern klein, Lagen können deutlich abweichen.",
                      "{nuc} prediction: Octet's table is small for this nucleus, shifts can deviate markedly."),
    "nmr_pred_solv_any": ("Lösungsmittel „{solv}“ kennt Octets Tabelle nicht: Verschiebungen aus allen Lösungsmitteln.",
                          "Octet's table does not know the solvent “{solv}”: shifts from all solvents."),
})
# lab_: Karte „Beschriftungen im Bild“ (eigener Text / ausblenden je Label, tabs/base.py LabelCard)
TEXTS.update({
    "lab_card": ("Beschriftungen im Bild", "Figure Labels"),
    "lab_col_text": ("Beschriftung", "Label"),
    "lab_table_tip": ("Häkchen = Label im Bild. Ausblenden betrifft nur die Abbildung: Tabelle, SI-Zeile und Excel "
                      "behalten den Wert (anders als eine abgewählte Bande).",
                      "Tick = label shown in the figure. Hiding affects only the figure: table, SI line and Excel keep "
                      "the value (unlike a deselected band)."),
    "lab_empty": ("Keine Labels im Bild", "No labels in the figure"),
    "lab_text": ("Eigener Text", "Own text"),
    "lab_text_tip": ("Text im Bild für die gewählte Beschriftung; gilt beim Verlassen des Felds. Leer = automatischer "
                     "Text. Formeln wie im Bild zwischen $…$.",
                     "Text in the figure for the selected label; applies when leaving the field. Empty = automatic "
                     "text. Formulas as in the figure between $…$."),
    "lab_reset": ("Zurücksetzen", "Reset"),
    "lab_reset_tip": ("Automatischer Text und wieder im Bild", "Automatic text and shown again"),
    "lab_reset_all": ("Alle zurücksetzen", "Reset all"),
    "lab_reset_all_tip": ("Alle Beschriftungen wieder automatisch und im Bild", "All labels automatic and shown again"),
    "lab_reset_none": ("Nichts zurückzusetzen: automatischer Text, im Bild", "Nothing to reset: automatic text, shown"),
    "lab_pick_first": ("Erst eine Beschriftung in der Tabelle wählen", "Select a label in the table first"),
    "lab_auto": ("Automatisch: {t}", "Automatic: {t}"),
    "lab_hint": ("Rechtsklick auf ein Label im Bild: Text bearbeiten, im Bild ausblenden, zurücksetzen. Rechtsklick auf "
                 "eine freie Stelle: eigenes Label einfügen.",
                 "Right-click a label in the figure: edit text, hide in figure, reset. Right-click an empty spot: add "
                 "your own label."),
    "lab_num_differs": ("Label „{label}“ hat einen eigenen Text und weicht von Tabelle/SI ab (dort stehen die "
                        "berechneten Werte).",
                        "Label “{label}” has its own text and differs from the table/SI (they keep the computed "
                        "values)."),
    "lab_bad_math": ("Eigener Text nicht übernommen: die Formel zwischen $…$ lässt sich nicht setzen.",
                     "Own text not applied: the formula between $…$ cannot be typeset."),
    "lab_menu_edit": ("Text bearbeiten", "Edit text"),
    "lab_menu_hide": ("Im Bild ausblenden", "Hide in figure"),
    "lab_menu_reset": ("Zurücksetzen", "Reset"),
    "lab_menu_add": ("Label hier einfügen", "Add Label Here"),
    "lab_menu_remove": ("Label entfernen", "Remove Label"),
    "lab_new": ("Text", "Text"),
    "lab_extra_tip": ("Eigenes Label: Text im Feld darunter, ziehen zum Verschieben, Zurücksetzen entfernt es. Steht nur "
                      "im Bild, nie in Unterschrift oder SI-Text.",
                      "Own label: text in the field below, drag to move, Reset removes it. Only in the figure, never "
                      "in the caption or SI text."),
    "lab_extra_reset_tip": ("Dieses eigene Label entfernen", "Remove this own label"),
    "lab_extra_off": ("Eigene Labels entfernen", "Remove own labels"),
    "lab_extra_off_tip": ("Alle eigenen Labels dieser Abbildung entfernen", "Remove all own labels of this figure"),
    "lab_extra_none": ("Keine eigenen Labels: Rechtsklick auf eine freie Stelle der Vorschau fügt eines ein",
                       "No own labels: right-click an empty spot of the preview to add one"),
})
# tbl_: Ergebnistabellen als Datei und in der Zwischenablage (Entscheidung 170)
TEXTS.update({
    "tbl_copy_one": ("Tabelle kopieren (Word und Excel)", "Copy table (Word and Excel)"),
    "tbl_copy_tip": ("Tabellen dieser Karte kopieren: Word erhält eine formatierte Tabelle, Excel Zahlen mit "
                     "Dezimalpunkt", "Copy the tables of this card: Word gets a formatted table, Excel numbers with a "
                     "decimal point"),
    "export_retired": ("Nicht mehr erzeugt, in den Papierkorb: {f}", "No longer written, moved to the Trash: {f}"),
    "export_retired_failed": ("Nicht mehr erzeugt, Papierkorb fehlgeschlagen (bleibt liegen): {f}",
                              "No longer written, could not move to the Trash (left in place): {f}"),
    "export_counts": ("Dateien: {c}", "Files: {c}"),
    "open_tables": ("tables/ öffnen", "Open tables/"),
    "tbl_head_check": ("Prüfung", "Check"),
    "tbl_excel_hint": ("Für Excel <Verbindung>_<Tab>_tables.xlsx öffnen; CSV-Dateien sind für Origin/Python (in Excel "
                       "über Daten > Aus Text/CSV)",
                       "For Excel open <compound>_<Tab>_tables.xlsx; CSV files are for Origin/Python (in Excel via "
                       "Data > From Text/CSV)"),
})
TEXTS.update({                                            # HRMS: eigenes Ion, Fremdpeaks, OCR (Spur hrms2)
    "ms_own_item": ("Eigenes Ion …", "Own ion …"),
    "ms_own": ("Eigenes Ion", "Own ion"),
    "ms_own_z": ("z =", "z ="),
    "ms_own_tip": ("Ion als Ausdruck aus M und Gruppen, z. B. M+Na+MeOH, 2M+H, M-H2O+H, M+2H (Ladung 2); Gruppen: "
                   "Summenformeln und MeOH, MeCN, H2O, HCOO, DMSO, FA (Ameisensäure). z = Ladung des Ions.",
                   "Ion as an expression of M and groups, e.g. M+Na+MeOH, 2M+H, M-H2O+H, M+2H (charge 2); groups: "
                   "formulas and MeOH, MeCN, H2O, HCOO, DMSO, FA (formic acid). z = charge of the ion."),
    "ms_own_bad": ("⚠ Ion nicht lesbar oder ohne Ladung – Beispiel: M+Na+MeOH mit z = 1",
                   "⚠ ion not readable or without charge – example: M+Na+MeOH with z = 1"),
    "ms_flag_card": ("Fremdpeaks und Reagenzien", "Contaminants and Reagents"),
    "ms_flag_ppm": ("Fenster", "Window"),
    "ms_flag_ppm_tip": ("Höchstabstand eines Peaks zu einem bekannten Fremd-Ion, Reagenz oder Bruchstück (found − calc), "
                        "Vorgabe 5 ppm; gilt für diesen Tab", "Largest distance of a peak to a known contaminant ion, "
                        "reagent or fragment (found − calc), default 5 ppm; applies to this tab"),
    "ms_flag_hint": ("Hinweis", "Hint"),
    "ms_flag_src": ("Quelle", "Source"),
    "ms_flag_dev": ("Δ [ppm]", "Δ [ppm]"),
    "ms_flag_src_raw": ("Rohdaten", "raw data"),
    "ms_flag_src_report": ("Bericht", "report"),
    "ms_flag_src_pdf": ("PDF", "PDF"),
    "ms_flag_tip": ("Peaks, die zu einem bekannten Fremd-Ion (Keller et al. 2008 u. a.), einem eigenen Eintrag, einem "
                    "Edukt/Reagenz des Syntheseschemas oder einem Bruchstück der Verbindung (−N2, −H2O, −CO, −CO2) passen. "
                    "Nur Hinweis: nichts wird ausgeblendet, nichts steht in SI-Zeile oder Export.",
                    "Peaks that match a known contaminant ion (Keller et al. 2008 and others), an own entry, a starting "
                    "material/reagent of the synthesis scheme or a fragment of the compound (−N2, −H2O, −CO, −CO2). Hint "
                    "only: nothing is hidden, nothing goes into the SI line or the export."),
    "ms_flag_none": ("Kein Peak passt innerhalb ± {ppm} ppm zu einem Fremd-Ion, Reagenz oder Bruchstück.",
                     "No peak matches a contaminant, reagent or fragment within ± {ppm} ppm."),
    "ms_flag_nopeaks": ("Hinweise erscheinen, sobald Rohdaten (.d) oder ein Bericht mit Zahlen geladen sind.",
                        "Hints appear once raw data (.d) or a report with numbers is loaded."),
    "ms_own_card": ("Eigene Fremdpeaks", "Own Contaminants"),
    "ms_own_card_tip": ("Eigene Einträge für die Hinweise, gespeichert auf diesem Computer (nicht im Projekt). Ionen mit "
                        "Semikolon getrennt, z. B. M+H;M+Na;2M+H;M-H.", "Own entries for the hints, stored on this "
                        "computer (not in the project). Ions separated by semicolons, e.g. M+H;M+Na;2M+H;M-H."),
    "ms_own_name": ("Name", "Name"),
    "ms_own_formula": ("Formel", "Formula"),
    "ms_own_ions": ("Ionen", "Ions"),
    "ms_own_empty": ("Keine eigenen Einträge – es gilt die mitgelieferte Liste", "No own entries – the shipped list applies"),
    "ms_own_add": ("Eintrag hinzufügen", "Add entry"),
    "ms_own_reset": ("Nur mitgelieferte Liste", "Shipped list only"),
    "ms_own_reset_tip": ("Eigene Einträge dieses Computers entfernen; es gilt wieder nur die mitgelieferte Liste.",
                         "Remove the own entries of this computer; only the shipped list applies again."),
    "ms_own_entry_bad": ("⚠ nicht rechenbar (ohne Hinweis): {items}", "⚠ cannot be computed (no hint): {items}"),
    "ms_pdf_kind_ocr": ("per OCR", "by OCR"),
    "ms_cand_head_ocr": ("Per OCR erkannt (Klick übernimmt)", "Recognized by OCR (click to take)"),
    "ms_ocr_entry": ("Per OCR erkannt: {mz}  ({ppm} ppm)", "Recognized by OCR: {mz}  ({ppm} ppm)"),
    "ms_ocr_running": ("Texterkennung läuft …", "Text recognition running …"),
    "ocr_missing": ("⚠ Texterkennung nicht installiert (Paket rapidocr) – Werte von Hand eintragen",
                    "⚠ text recognition not installed (package rapidocr) – enter the values manually"),
    "ocr_failed": ("⚠ Texterkennung fehlgeschlagen: {e}", "⚠ text recognition failed: {e}"),
    "flt_ocr_img": ("Bild für Texterkennung", "Image for text recognition"),
    "ir_doc_head_pdf": ("Zahlen aus dem PDF (Häkchen übernimmt sie in die IR-Zeile)",
                        "Numbers from the PDF (tick to take them into the IR line)"),
    "ir_doc_head_ocr": ("Per OCR erkannt (Häkchen übernimmt sie in die IR-Zeile)",
                        "Recognized by OCR (tick to take them into the IR line)"),
    "ir_doc_wn": ("ṽ [cm⁻¹]", "ṽ [cm⁻¹]"),
    "ir_doc_tip": ("Zahlen zwischen 350 und 4500 aus dem Dokument; nichts ist vorgewählt. Zeile und Ausschnitt stehen im "
                   "Tooltip jeder Zeile: vergleichen, bevor du sie übernimmst.", "Numbers between 350 and 4500 from the document; nothing is preselected. "
                   "Line and detail are in each row's tooltip: compare before taking them."),
    "ir_doc_none": ("⚠ keine Zahlen zwischen 350 und 4500 im Dokument gefunden – Werte von Hand eintragen",
                    "⚠ no numbers between 350 and 4500 found in the document – enter the values manually"),
    "hrms_no_spectrum_img": ("Kein Spektrum – für eine Abbildung MS-Rohdaten (.d) laden.",
                             "No spectrum – load MS raw data (.d) for a figure."),
    "hrms_no_spectrum_raw": ("Kein Spektrum – das Ion ist in den MS-Rohdaten nicht zu finden. Summenformel und Ion links "
                             "prüfen.", "No spectrum – the ion is not found in the MS raw data. Check the formula and "
                             "ion on the left."),
    "dp_pdf_check": ("PDF-Köpfe prüfen (MS-Bericht als Bild oder mit unbekanntem Aufbau, Inhalt unverändert):\n  {files}",
                     "check PDF headers (MS report as image or with unknown layout, content unchanged):\n  {files}"),
})
# txt_: feste Texte der Abbildung in der Karte „Beschriftungen im Bild“ (core/figtexts.py, Spur s3texte 1.5.0)
TEXTS.update({
    "lab_col_what": ("Element", "Element"),
    "lab_kind_label": ("Label", "Label"),
    "lab_kind_extra": ("Eigenes Label", "Own label"),
    "txt_part_x": ("X-Achse", "X-axis"),
    "txt_part_y": ("Y-Achse", "Y-axis"),
    "txt_part_title": ("Titel", "title"),
    "txt_part_legend": ("Legende", "legend"),
    "txt_part_head": ("Tabellenkopf", "table header"),
    "txt_ax_r": ("rechte", "right"),
    "txt_ax_inset": ("Inset", "inset"),
    "txt_ax_cbar": ("Farbskala", "Color scale"),
    "txt_ax_fig": ("Abbildung", "figure"),
    "txt_ax_n": ("Teilbild {n}", "panel {n}"),
})
TEXTS.update({                                            # s3texte: Einträge „nicht im Bild“, Übernehmen
    "lab_stale": ("{el} · nicht im Bild", "{el} · not in figure"),
    "lab_stale_tip": ("Eigener Text, der gerade nicht im Bild steht (Element aus, andere Daten oder geänderter "
                      "automatischer Text). Er bleibt gespeichert: Übernehmen oder Zurücksetzen.",
                      "Own text that is currently not in the figure (element off, other data or changed automatic "
                      "text). It stays saved: adopt or reset."),
    "lab_stale_info": ("Nicht im Bild – eigener Text für „{t}“", "Not in the figure – own text for “{t}”"),
    "lab_stale_reset_tip": ("Eigenen Text verwerfen", "Discard the own text"),
    "lab_adopt": ("Übernehmen", "Adopt"),
    "lab_adopt_tip": ("Eigenen Text für „{el}“ im Bild verwenden", "Use the own text for “{el}” in the figure"),
    "lab_adopt_none": ("Kein eindeutiges Element ohne eigenen Text im Bild: Text kopieren und in der passenden Zeile "
                       "eintragen", "No single element without own text in the figure: copy the text and enter it in "
                       "the matching row"),
    "lab_adopt_only": ("Nur für Zeilen „nicht im Bild“", "Only for rows “not in figure”"),
})
TEXTS.update({                                            # s3texte: Karten fester Texte auf Seiten mit eigener Abbildung
    "lab_card_nics": ("Beschriftungen: NICS-Scan", "Labels: NICS Scan"),
    "lab_card_pxrd": ("Beschriftungen: PXRD", "Labels: PXRD"),
    "lab_card_decay": ("Beschriftungen: Abklingkurve", "Labels: Decay Curve"),
    "lab_grp_labels": ("Labels", "Labels"),
    "lab_grp_axes": ("Achsen und Legende", "Axes and Legend"),
    "lab_grp_inset": ("Inset", "Inset"),
    "lab_grp_tip": ("Klicken: auf- oder zuklappen", "Click to expand or collapse"),
    "lab_card_nto": ("Beschriftungen: NTO", "Labels: NTO"),
})

TEXTS.update({                                      # Spur s1vergleich (1.5.0): Tabellenspalten der neuen Quellen
    "cmp_col_syn_yield": ("Synthese: Ausbeute [%]", "Synthesis: yield [%]"),
    "cmp_col_hrms_ion": ("HRMS: Ion", "HRMS: ion"),
    "cmp_col_hrms_calc": ("HRMS: m/z ber.", "HRMS: m/z calc."),
    "cmp_col_hrms_found": ("HRMS: m/z gef.", "HRMS: m/z found"),
    "cmp_col_hrms_dev": ("HRMS: Δ [ppm]", "HRMS: Δ [ppm]"),
    "cmp_col_td_lam": ("TD-DFT: λ des stärksten Übergangs", "TD-DFT: λ of the strongest transition"),
    "cmp_col_td_f": ("TD-DFT: f des stärksten Übergangs", "TD-DFT: f of the strongest transition"),
    "cmp_col_td_E": ("TD-DFT: E des stärksten Übergangs", "TD-DFT: E of the strongest transition"),
    "cmp_col_uk_lam": ("Kinetik: λ", "Kinetics: λ"),
    "cmp_col_uk_rest": ("Kinetik: verbleibend [%]", "Kinetics: remaining [%]"),
    "cmp_col_uk_half": ("Kinetik: t½", "Kinetics: t½"),
    "cmp_col_sec_e12": ("SEC: E½ (scheinbar, Nernst-Fit)", "SEC: E½ (apparent, Nernst fit)"),
    "cmp_col_sec_ref": ("SEC: Referenz", "SEC: reference"),
    "cmp_col_hc_q": ("H-Zelle: Q_theo [mAh]", "H-Cell: Q_theo [mAh]"),
    "cmp_col_hc_first": ("H-Zelle: Entladen, 1. Zyklus [mAh]", "H-Cell: discharge, first cycle [mAh]"),
    "cmp_col_hc_last": ("H-Zelle: Entladen, letzter Zyklus [mAh]", "H-Cell: discharge, last cycle [mAh]"),
    "cmp_col_hc_ret": ("H-Zelle: Erhalt [%]", "H-Cell: retention [%]"),
    "cmp_col_hc_ce": ("H-Zelle: mittlere CE [%]", "H-Cell: mean CE [%]"),
    "cmp_col_hc_n": ("H-Zelle: Zyklen", "H-Cell: cycles"),
    "cmp_col_hc_h": ("H-Zelle: Dauer [h]", "H-Cell: duration [h]"),
})

TEXTS.update({                                      # Spur s1vergleich (1.5.0): Schnellvergleich, Gründe „nicht erkannt“
    "qc_why_folder": ("Ordner ohne erkannte Messung (TopSpin-NMR, Bruker-.d oder H-Zelle mit CHARGE_DISCHARGE/)",
                      "Folder without a recognized measurement (TopSpin NMR, Bruker .d or H-Cell with CHARGE_DISCHARGE/)"),
    "qc_why_missing": ("Datei nicht gefunden", "File not found"),
    "qc_why_hcell": ("Lade/Entlade-Messung ohne Ordner CHARGE_DISCHARGE/ daneben – den ganzen Ordner ablegen",
                     "Charge/discharge measurement without the CHARGE_DISCHARGE/ folder next to it – drop the whole folder"),
    "qc_why_pdf": ("PDF: HRMS-Bericht oder IR-Spektrum? Nicht eindeutig", "PDF: HRMS report or IR spectrum? Not unique"),
    "qc_why_unknown": ("Unbekanntes Dateiformat", "Unknown file format"),
    "qc_why_create": ("Verbindung konnte nicht angelegt werden", "Compound could not be created"),
})

TEXTS.update({                                      # Spur s1vergleich (1.5.0): Vergleichsart H-Zelle
    "cmp_new_hcell": ("H-Zelle", "H-Cell"),
    "cmp_new_hcell_tip": ("Neuer Vergleich: Kapazität gegen Zyklus mehrerer Lade/Entlade-Messungen in einem Bild",
                          "New comparison: capacity versus cycle of several charge/discharge measurements in one figure"),
    "cmp_kind_hcell": ("H-Zelle", "H-Cell"),
    "cmp_hc_unit": ("Kapazität", "Capacity"),
    "cmp_hc_ce": ("Coulomb-Effizienz (rechte Achse)", "Coulombic efficiency (right axis)"),
})

TEXTS.update({                                      # Spur s1vergleich (1.5.0): mehrere Messungen einer Verbindung
    "cmp_title": ("Beschriftung", "Label"),
    "cmp_title_tip": ("Beschriftung im Bild, in der Legende und in der Unterschrift (Doppelklick ändert; leer = "
                      "Name der Verbindung, bei mehreren Zeilen mit der Messung)",
                      "Label in the figure, legend and caption (double-click to change; empty = name of the compound, "
                      "with the measurement when it has several rows)"),
    "cmp_add_meas": ("+ Messung", "+ Measurement"),
    "cmp_add_meas_tip": ("Weitere Messung der gewählten Verbindung als eigene Zeile; welche, wählt die Karte darunter",
                         "Another measurement of the selected compound as its own row; choose which in the card below"),
    "cmp_del_meas_tip": ("Diese weitere Zeile der Verbindung entfernen", "Remove this additional row of the compound"),
})

TEXTS.update({                                      # Spur s1vergleich (1.5.0): Schnellvergleich (Oberfläche)
    "qc_new": ("Schnellvergleich", "Quick comparison"),
    "qc_new_tip": ("Dateien ablegen und sofort vergleichen – jede Datei wird eine Einzelauswertung im internen Projekt "
                   "„Einzelauswertungen“", "Drop files and compare them at once – each file becomes a quick evaluation "
                   "in the internal project “Quick evaluations”"),
    "qc_name": ("Schnellvergleich {date}", "Quick comparison {date}"),
    "qc_add": ("Dateien hinzufügen", "Add Files"),
    "qc_drop": ("Dateien oder Ordner hierher ziehen", "Drop files or folders here"),
    "qc_drop_sub": ("CV, H-Zelle, UV-Vis, IR, EPR, SEC, NMR, HRMS, X-Ray, DFT – die Art wird aus der Datei erkannt",
                    "CV, H-cell, UV-Vis, IR, EPR, SEC, NMR, HRMS, X-ray, DFT – the kind is read from the file"),
    "qc_choose": ("Dateien wählen …", "Choose files …"),
    "qc_choose_dir": ("Ordner wählen …", "Choose folder …"),
    "qc_files": ("Dateien", "Files"),
    "qc_file": ("Datei", "File"),
    "qc_reason": ("Grund", "Reason"),
    "qc_kind": ("Art", "Kind"),
    "qc_unrec": ("Nicht erkannt", "Not Recognized"),
    "qc_unrec_hint": ("Nicht geraten: Art wählen, wo zwei in Frage kommen, oder die Datei im passenden Tab einer "
                      "Verbindung öffnen.", "Not guessed: choose the kind where two are possible, or open the file in "
                      "the matching tab of a compound."),
    "qc_unrec_clear": ("Liste leeren", "Clear list"),
    "qc_pick": ("Art wählen …", "Choose kind …"),
    "qc_src_hrms": ("HRMS-Bericht", "HRMS report"),
    "qc_src_irms": ("IR-Spektrum", "IR spectrum"),
    "qc_remove_tip": ("Gewählte Datei entfernen (ihre Einzelauswertung kommt in den Papierkorb)",
                      "Remove the selected file (its quick evaluation goes to the trash)"),
    "qc_part_cv": ("CV", "CV"),
    "qc_part_hcell": ("H-Zelle", "H-Cell"),
    "qc_part_eps": ("UV-Vis", "UV-Vis"),
    "qc_part_irms": ("IR", "IR"),
    "qc_part_epr": ("EPR", "EPR"),
    "qc_part_table": ("Tabelle", "Table"),
    "guide_quick_title": ("Schnellvergleich: Dateien ablegen, gleiche Arten kommen in ein Bild",
                          "Quick comparison: drop files, files of one kind share a figure"),
    "guide_quick_files": ("Daten: Messdateien und -ordner (CV, H-Zelle, UV-Vis, IR, EPR, SEC, NMR, HRMS, X-Ray, DFT); "
                          "jede wird eine Einzelauswertung, ausgewertet wie im Tab",
                          "Data: measurement files and folders (CV, H-cell, UV-Vis, IR, EPR, SEC, NMR, HRMS, X-ray, DFT); "
                          "each becomes a quick evaluation, evaluated like in the tab"),
    "guide_quick_steps": ("Dateien links ablegen oder „Dateien wählen …“\nJe Art ein Reiter rechts; Beschriftung und "
                          "Farbe in der Liste ändern\nExportieren wie jeden Vergleich",
                          "Drop files on the left or use “Choose Files …”\nOne tab per kind on the right; change label "
                          "and colour in the list\nExport like any comparison"),
})

TEXTS.update({                                      # Spur s1vergleich (1.5.0): Vergleichsart UV-Vis-Kinetik
    "cmp_new_uvkin": ("UV-Vis-Kinetik", "UV-Vis Kinetics"),
    "cmp_new_uvkin_tip": ("Neuer Vergleich: Absorbanz gegen die Zeit mehrerer Kinetik-Reihen in einem Bild",
                          "New comparison: absorbance against time of several kinetics series in one figure"),
    "cmp_kind_uvkin": ("UV-Vis-Kinetik", "UV-Vis kinetics"),
    "cmp_uk_series": ("Reihe", "Series"),
    "cmp_uk_tunit": ("Zeiteinheit", "Time unit"),
    "cmp_uk_y": ("Absorbanz", "Absorbance"),
    "cmp_uk_rel": ("relativ zum ersten Spektrum [%]", "relative to the first spectrum [%]"),
    "cmp_uk_abs": ("absolut", "absolute"),
})
TEXTS.update({"cmp_uk_tauto": ("wie im Tab (erste Zeile)", "as in the tab (first row)")})   # Spur s1vergleich
TEXTS.update({"cmp_hrms_dev_tip": ("Abweichung über 5 ppm (wie in der Prüftabelle des HRMS-Tabs)",   # Spur s1vergleich
                                   "Deviation above 5 ppm (as in the check table of the HRMS tab)")})
TEXTS.update({                                      # Spur s1vergleich (1.5.0): SEC und TD-DFT im Spektrenvergleich
    "cmp_content_sec": ("SEC: Endspektrum (normiert)", "SEC: end spectrum (normalized)"),
    "cmp_content_td": ("TD-DFT: berechnetes Spektrum (ε)", "TD-DFT: calculated spectrum (ε)"),
    "cmp_sec_refused": ("Nicht im Bild (SEC als Rohsignal, nicht als Absorbanz): {names}",
                        "Not in the figure (SEC as raw signal, not absorbance): {names}"),
})
TEXTS.update({"qc_part_sec": ("SEC", "SEC")})       # Spur s1vergleich: Reiter des Schnellvergleichs
TEXTS.update({                                      # Spur s1vergleich: Grund je Datei im Schnellvergleich
    "qc_st_novalues": ("ohne Werte", "no values"),
    "qc_why_eps_conc": ("Gelesen, aber ohne Konzentrationen: kein ε. Doppelklick auf die Datei öffnet die "
                        "Einzelauswertung zum Eintragen.", "Read, but without concentrations: no ε. Double-click the "
                        "file to open the quick evaluation and enter them."),
    "qc_why_novalues": ("Gelesen, aber ohne auswertbare Werte (Doppelklick auf die Datei öffnet die Einzelauswertung)",
                        "Read, but without values to compare (double-click the file to open the quick evaluation)"),
})
TEXTS.update({                                      # Spur s1vergleich: Hinweise zu Regeln ui.md
    "cmp_del_meas_off": ("Nur weitere Messungen einer Verbindung lassen sich entfernen; die letzte Zeile abwählen",
                         "Only additional measurements of a compound can be removed; untick the last row instead"),
    "qc_pick_none": ("Für diese Datei gibt es keine Wahl: im passenden Tab einer Verbindung öffnen",
                     "No choice for this file: open it in the matching tab of a compound"),
})
TEXTS.update({"cmp_uk_fits": ("Fits zeigen", "Show fits")})   # Spur s1vergleich: Kinetik-Vergleich (Robin 2026-11-27)
# NTO-Strukturen drehbar (1.5.0, Spur s2bnto)
TEXTS.update({
    "nto_view": ("Ansicht", "View"),
    "view_row": ("Ansicht", "View"),
    "view_reset_tip": ("Drehung, Zoom und Verschiebung des Bilds auf die automatische Ansicht (Ziehen im Bild dreht, "
                       "Mausrad zoomt).", "Rotation, zoom and shift of the figure back to the automatic view (drag in the "
                       "figure to rotate, mouse wheel to zoom)."),
    "nto_view_reset_tip": ("Im Bild ziehen dreht Loch und Teilchen gemeinsam (gilt auch für Export und SI). Der Knopf "
                           "stellt die automatische Ansicht wieder her.",
                           "Dragging in the figure rotates hole and particle together (also used for export and SI). "
                           "The button restores the automatic view."),
})

# Ruhigere Oberfläche (1.5.0, Spur s4unslop)
TEXTS.update({
    "nmr_si_need_raw": ("Nur für Spektren aus Rohdaten mit eigener Verarbeitung: unter „Spektren“ eine Rohdaten-Zeile "
                        "wählen.", "Only for raw-data spectra with own processing: select a raw-data row under "
                        "“Spectra”."),
})

# CV: Elektronenzahl n je Welle gegen den internen Standard und aus der Coulometrie (1.5.0, Spur s5cvn)
TEXTS.update({
    "grp_electrons": ("Elektronenzahl n", "Electron Count n"),
    "cv_n_cstd": ("Konzentration Standard", "Standard concentration"),
    "cv_n_D": ("D\u200b der Probe", "D\u200b of sample"),          # \u200b: D kursiv (STYLE.QTY)
    "cv_n_Dstd": ("D\u200b des Standards", "D\u200b of standard"),
    "cv_n_D_tip": ("Selbst eingeben (z. B. aus DOSY, gleiches Lösungsmittel und gleiche Temperatur); nie aus der CV "
                   "geschätzt. Gilt nur für n, nicht für D und k⁰.",
                   "Enter yourself (e.g. from DOSY, same solvent and temperature); never estimated from the CV. Used "
                   "for n only, not for D and k⁰."),
    "cv_n_hint": ("n aus dem Hinpeakstrom gegen den Standard (Fc, Ac₂Fc) im selben Voltammogramm (Randles–Ševčík). "
                  "c der Probe: Karte „Diffusion und k⁰“. D selbst eingeben (z. B. DOSY), nie aus der CV.",
                  "n from the forward peak current vs. the standard (Fc, Ac₂Fc) in the same voltammogram "
                  "(Randles–Ševčík). c of the sample: card “Diffusion and k⁰”. Enter D yourself (e.g. DOSY), never "
                  "from the CV."),
    "cv_n_coul_couple": ("Coulometrie, Paar", "Coulometry, couple"),
    "cv_n_coul_q": ("Ladung Q\u200b", "Charge Q\u200b"),
    "cv_n_coul_mol": ("Stoffmenge N\u200b", "Amount N\u200b"),
    "cv_n_coul_tip": ("Bulk-Elektrolyse: n = Q/(F·N) aus der umgesetzten Ladung (Hintergrund abgezogen) und der "
                      "Stoffmenge, nur aus diesen Angaben.",
                      "Bulk electrolysis: n = Q/(F·N) from the charge passed (background subtracted) and the amount "
                      "of substance, from these entries only."),
    "cv_n_title": ("Elektronenzahl n je Welle", "Electron count n per wave"),
    "cv_n_meas": ("Messung", "Measurement"),
    "cv_n_status": ("Bewertung", "Assessment"),
    "cv_n_coul_row": ("Coulometrie (Q = {q} mC, N = {mol} µmol)", "Coulometry (Q = {q} mC, N = {mol} µmol)"),
    "cv_n_ok": ("Ergebnis", "Result"),
    "cv_n_apparent": ("scheinbar", "apparent"),
    "cv_n_apparent_tip": ("ΔEp des Standards ({dep} mV) liegt über 2,22·RT/F + 10 mV (unkompensierter Widerstand); n "
                          "daher nur scheinbar, wie k⁰.",
                          "ΔEp of the standard ({dep} mV) is above 2.22·RT/F + 10 mV (uncompensated resistance); n is "
                          "therefore only apparent, like k⁰."),
    "cv_n_bl_short_tip": ("Basislinie des Standards: Vorlauf nur 0,15 V (i_p bis etwa 6 % zu klein).",
                          "Baseline of the standard: only 0.15 V before the peak (i_p up to about 6 % too small)."),
    "cv_n_tip": ("n = [(i_p/i_p,Std)·(D_Std/D)^½·(c_Std/c)]^⅔ (Randles–Ševčík), Hinpeaks gegen die Basislinie, nicht "
                 "gerundet. Liegt eine Welle auf dem abklingenden Strom einer vorangehenden, misst die lineare "
                 "Basislinie ihr i_p etwa 2–4 % zu groß (simuliert); das wird nicht korrigiert.",
                 "n = [(i_p/i_p,std)·(D_std/D)^½·(c_std/c)]^⅔ (Randles–Ševčík), forward peaks against the baseline, "
                 "not rounded. If a wave sits on the decaying current of a preceding one, the linear baseline measures "
                 "its i_p about 2–4 % too large (simulated); this is not corrected."),
    "cv_n_why_separate": ("Standard getrennt", "standard separate"),
    "cv_n_why_std_custom": ("eigener Standard", "custom standard"),
    "cv_n_why_baseline": ("Basislinie fehlt", "no baseline"),
    "cv_n_why_invalid": ("Rand/zwei Wellen", "edge/two waves"),
    "cv_n_why_std_invalid": ("Standard ungültig", "standard invalid"),
    "cv_n_why_overlap": ("Wellen überlappen", "waves overlap"),
    "cv_n_why_not_rev": ("nicht reversibel", "not reversible"),
    "cv_n_why_inputs": ("c oder D fehlt", "c or D missing"),
    "cv_n_whyl_separate": ("Der Standard steht in einer anderen Messung: n nur aus Probe und Standard im selben "
                           "Voltammogramm.", "The standard is in another measurement: n only from sample and standard "
                           "in the same voltammogram."),
    "cv_n_whyl_std_custom": ("Eigener Standard: seine Elektronenzahl ist nicht bekannt (n nur gegen Fc oder Ac₂Fc).",
                             "Custom standard: its electron count is not known (n only vs. Fc or Ac₂Fc)."),
    "cv_n_whyl_baseline": ("Ohne Basislinie (aus oder zu wenig Vorlauf) sind die Peakströme nicht vergleichbar.",
                           "Without a baseline (off or too little scan before the wave) the peak currents are not "
                           "comparable."),
    "cv_n_whyl_invalid": ("Peak am Fensterrand oder zwei Wellen im Fenster des Paars.",
                          "Peak at the window edge or two waves in the window of the couple."),
    "cv_n_whyl_std_invalid": ("Im Fenster des Standards liegt kein gültiges Paar.",
                              "The window of the standard holds no valid couple."),
    "cv_n_whyl_overlap": ("Ein Peak der Welle liegt im Fenster des Standards oder umgekehrt.",
                          "A peak of the wave lies in the window of the standard or vice versa."),
    "cv_n_whyl_not_rev": ("ΔEp ({dep} mV) liegt mehr als 10 mV über ΔEp des Standards ({dep_std} mV): Welle nicht "
                          "reversibel, Randles–Ševčík gilt nicht.",
                          "ΔEp ({dep} mV) is more than 10 mV above ΔEp of the standard ({dep_std} mV): wave not "
                          "reversible, Randles–Ševčík does not apply."),
    "cv_n_whyl_inputs": ("Konzentration der Probe (Karte „Diffusion und k⁰“), Konzentration des Standards und beide D "
                         "eingeben.", "Enter the concentration of the sample (card “Diffusion and k⁰”), the "
                         "concentration of the standard and both D."),
    "cv_n_only_separate": ("Keine Messung enthält Probe und Standard zugleich: n nur aus demselben Voltammogramm.",
                           "No measurement contains sample and standard together: n only from the same voltammogram."),
    "cv_w_n_rs": ("Wellen, bei denen das berechnete n vom eingegebenen abweicht (D, k⁰): {n}",
                  "Waves where the computed n differs from the entered n (D, k⁰): {n}"),
    "cv_n_rs_detail": ("Paar {couple}: n = {n} ({src}), eingegeben n = {rs} – Angabe in „Diffusion und k⁰“ prüfen, "
                       "sie wird nicht still übernommen.",
                       "Couple {couple}: n = {n} ({src}), entered n = {rs} – check the entry in “Diffusion and k⁰”; "
                       "it is never adopted silently."),
    # tf_*_pt: Schriftgrößen der Achsen in der Karte „Schrift und Linien“ (core.SIZE_KEYS, Spur s3c 1.5.0)
    "tf_axis_pt": ("Größe Achsentitel", "Axis title size"),
    "tf_tick_pt": ("Größe Achsenzahlen", "Tick label size"),
    "tf_legend_pt": ("Größe Legende", "Legend size"),
    "tf_axis_pt_tip": ("Schriftgröße der Achsentitel (auch Zweitachse und Farbskala) in pt; „Automatisch“ = "
                       "aus der Bildgröße wie bisher",
                       "Font size of the axis titles (also secondary axis and colour scale) in pt; “Automatic” = "
                       "from the figure size as before"),
    "tf_tick_pt_tip": ("Schriftgröße der Zahlen an den Achsen in pt; „Automatisch“ = aus der Bildgröße wie "
                       "bisher", "Font size of the numbers on the axes in pt; “Automatic” = from the figure size as "
                       "before"),
    "tf_legend_pt_tip": ("Schriftgröße der Legende (auch Kurvennamen statt Legende) in pt; „Automatisch“ = "
                         "aus der Bildgröße wie bisher",
                         "Font size of the legend (also curve names instead of a legend) in pt; “Automatic” = "
                         "from the figure size as before"),
    "tf_axis_pt_tip_xray": (
        "Schriftgröße der Achsentitel in pt, gilt im X-Ray-Tab nur für das Pulverdiffraktogramm (PXRD); "
        "„Automatisch“ = aus der Bildgröße wie bisher",
        "Font size of the axis titles in pt; applies in the X-Ray tab only to the powder pattern (PXRD); "
        "“Automatic” = from the figure size as before"),
    "tf_axis_pt_tip_dft": (
        "Schriftgröße der Achsentitel in pt, gilt im DFT-Tab nur für IRC und NICS-Scan; "
        "„Automatisch“ = aus der Bildgröße wie bisher",
        "Font size of the axis titles in pt; applies in the DFT tab only to the IRC and the NICS scan; "
        "“Automatic” = from the figure size as before"),
    "tf_tick_pt_tip_xray": (
        "Schriftgröße der Zahlen an den Achsen in pt, gilt im X-Ray-Tab nur für das Pulverdiffraktogramm (PXRD); "
        "„Automatisch“ = aus der Bildgröße wie bisher",
        "Font size of the numbers on the axes in pt; applies in the X-Ray tab only to the powder pattern (PXRD); "
        "“Automatic” = from the figure size as before"),
    "tf_tick_pt_tip_dft": (
        "Schriftgröße der Zahlen an den Achsen in pt, gilt im DFT-Tab nur für IRC und NICS-Scan; "
        "„Automatisch“ = aus der Bildgröße wie bisher",
        "Font size of the numbers on the axes in pt; applies in the DFT tab only to the IRC and the NICS scan; "
        "“Automatic” = from the figure size as before"),
    "tf_legend_pt_tip_xray": (
        "Schriftgröße der Legende in pt, gilt im X-Ray-Tab nur für das Pulverdiffraktogramm (PXRD); "
        "„Automatisch“ = aus der Bildgröße wie bisher",
        "Font size of the legend in pt; applies in the X-Ray tab only to the powder pattern (PXRD); "
        "“Automatic” = from the figure size as before"),
    "tf_legend_pt_tip_dft": (
        "Schriftgröße der Legende in pt, gilt im DFT-Tab nur für IRC und NICS-Scan; "
        "„Automatisch“ = aus der Bildgröße wie bisher",
        "Font size of the legend in pt; applies in the DFT tab only to the IRC and the NICS scan; "
        "“Automatic” = from the figure size as before"),
})

# Spur s2fehler (1.5.0)
TEXTS.update({
    "draw_paste_formats": ("Zeichenfläche: nichts Lesbares in der Zwischenablage. Formate: {f}",
                           "Drawing: nothing readable on the clipboard. Formats: {f}"),
    "si_progress": ("SI (Word) wird geschrieben … {part}", "Writing SI (Word) … {part}"),
})
