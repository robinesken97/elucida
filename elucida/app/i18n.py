"""elucida/app/i18n.py - Übersetzungen DE/EN. T(key, **kw) liefert den Text in der aktiven Sprache."""
from __future__ import annotations

import os

_LANG = os.environ.get("UVVIS_LANG", "de")[:2].lower()

TEXTS = {
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
    "no_fit": ("kein Fit: nur {n} Punkte unter A = {cut:g} (min. {min})",
               "no fit: only {n} points below A = {cut:g} (min. {min})"),
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
    "cdxml_dummies": ("{n} Platzhalteratom(e) (Abkürzung wie Dipp/Mes nicht aufgelöst?) – "
                      "Molmasse bitte manuell eingeben",
                      "{n} placeholder atom(s) (abbreviation like Dipp/Mes not expanded?) – "
                      "please enter molar mass manually"),
    "cdxml_redrawn": ("Zeichnung von RDKit neu erzeugt (weicht von ChemDraw ab). Für das Original "
                      "die Struktur in ChemDraw zusätzlich als „{name}.svg“, „.pdf“ oder „.png“ "
                      "neben die CDXML speichern.",
                      "Drawing regenerated by RDKit (differs from ChemDraw). For the original, also "
                      "save the structure from ChemDraw as “{name}.svg”, “.pdf” or “.png” next to the CDXML."),
    "cdxml_drawn": ("Gezeichnet aus den Koordinaten der CDXML (wie in ChemDraw, Schrift Helvetica). Exakt: „{name}.svg“ "
                    "oder „.pdf“ aus ChemDraw daneben speichern.", "Drawn from the CDXML coordinates (as in ChemDraw, "
                    "Helvetica font). Exact: save “{name}.svg” or “.pdf” from ChemDraw next to it."),
    "cdxml_own_failed": ("Eigene Zeichnung nicht möglich ({what}).", "Own drawing not possible ({what})."),
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
    "act_open": ("Messdaten öffnen…", "Open measurement data…"),
    "act_new_project": ("Neue Verbindung…",
                        "New compound…"),
    "act_save_copy": ("Verbindung als Kopie speichern…",
                      "Save compound copy…"),
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
    "act_open_project": ("Öffnen…",
                         "Open…"),
    "act_recent": ("Zuletzt geöffnet",
                   "Recently opened"),
    "act_save_project": ("Speichern",
                         "Save"),
    "act_save_project_as": ("Speichern unter…",
                            "Save as…"),
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
    "grp_compound": ("Verbindung", "Compound"),
    "structure": ("Struktur", "Structure"),
    "photo": ("Küvettenfoto", "Cuvette photo"),
    "choose": ("Wählen…", "Choose…"),
    "remove": ("Entfernen", "Remove"),
    "molar_mass": ("Molmasse [g/mol]", "Molar mass [g/mol]"),
    "molar_mass_short": ("Molmasse", "Molar mass"),
    "img_size_struct": ("Größe Struktur", "Structure size"),
    "img_size_photo": ("Größe Foto", "Photo size"),
    "adv_images": ("Bildgrößen und Freistellung", "Image sizes and background"),
    "adv_eval": ("Erweitert: min. Punkte, min. R², Schultern", "Advanced: min. points, min. R², shoulders"),
    "adv_plot": ("Inset, Fehler, R²-Anzeige, Formate", "Inset, errors, R² display, formats"),
    "adv_changed": ("geändert", "changed"),
    "menu_theme": ("Erscheinungsbild", "Appearance"),
    "move_up": ("Nach oben", "Move up"),
    "move_down": ("Nach unten", "Move down"),
    "toolbar": ("Werkzeugleiste", "Toolbar"),
    "theme_system": ("wie System", "follow system"),
    "theme_light": ("hell", "light"),
    "theme_dark": ("dunkel", "dark"),
    "empty_title": ("Messdaten hierher ziehen", "Drop measurement data here"),
    "empty_formats": ("Cary-CSV, DSW/BSW, Eclipse-CSV oder Ordner einer Verbindung\nKonzentration aus dem Probennamen, z. "
                      "B. ABC-1-0p5mgml_THF = 0,5 mg/mL (sonst Tabelle zum Eintragen)",
                      "Cary CSV, DSW/BSW, Eclipse CSV or compound folder\nConcentration from the sample name, e.g. "
                      "ABC-1-0p5mgml_THF = 0.5 mg/mL (otherwise a table to fill in)"),
    "mw_from_cdxml": ("aus CDXML", "from CDXML"),
    "mw_hint_none": ("leer = spezifischer Koeffizient a statt ε", "empty = specific coefficient a instead of ε"),
    "bg_method": ("Freistellung", "Background"),
    "bg_auto": ("automatisch", "automatic"),
    "bg_isnet": ("KI (ISNet)", "AI (ISNet)"),
    "bg_grabcut": ("GrabCut", "GrabCut"),
    "bg_border": ("Randfarbe", "Border colour"),
    "bg_off": ("keine", "none"),
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
    "min_r2_tip": ("Banden mit kleinerem R² stehen in Tabelle, CSV und Excel-Report, aber nicht in der Abbildung. 0 = alle zeigen.",
                   "Bands with a lower R² are listed in the table, CSV and Excel report but not shown in the figure. 0 = show all."),
    "wavelengths": ("Banden [nm]", "Bands [nm]"),
    "wavelengths_ph": ("z. B. Schultern: 350, 660", "e.g. shoulders: 350, 660"),
    "baseline": ("Basislinie", "Baseline"),
    "baseline_tip": ("Wird vor dem Fit von jedem Spektrum abgezogen, gemessen in einem Fenster, in dem die Probe kaum "
                     "absorbiert.\nautomatisch (Reihe): nur der konzentrationsunabhängige Versatz (Restabsorption der "
                     "Probe bleibt)\nautomatisch (einfach): der ganze Wert im Fenster\nmanuelles Fenster: Bereich "
                     "darunter selbst wählen",
                     "Subtracted from every spectrum before the fit, measured in a window where the sample barely "
                     "absorbs.\nautomatic (series): only the concentration-independent offset (residual absorption of "
                     "the sample stays)\nautomatic (simple): the whole value in the window\nmanual window: choose the "
                     "range below"),
    "bl_series": ("automatisch (Reihe)", "automatic (series)"),
    "bl_simple": ("automatisch (einfach)", "automatic (simple)"),
    "bl_manual": ("manuelles Fenster", "manual window"),
    "bl_off": ("aus", "off"),
    "grp_plot": ("Darstellung", "Plot"),
    "ymax": ("y-Achse max", "y-axis max"),
    "r2_mode": ("R² anzeigen", "Show R²"),
    "r2_legend": ("in Inset-Legende (wenn keine Tabelle)", "in inset legend (if no table)"),
    "r2_label": ("im Bandenlabel", "in band label"),
    "r2_off": ("aus", "off"),
    "show_err": ("ε mit Fehler", "ε with error"),
    "inset_show": ("Regression (Inset) anzeigen", "Show regression (inset)"),
    "inset_table": ("Tabelle im Inset", "table in inset"),
    "btn_update": ("Aktualisieren", "Update"),
    "btn_reset_layout": ("Layout zurücksetzen", "Reset layout"),
    "btn_reset": ("Zurücksetzen", "Reset"),
    "btn_reset_defaults": ("Alles auf Standard", "Reset all to defaults"),
    "btn_reset_defaults_tip": ("„Layout zurücksetzen“: nur die Lage von Labels, Inset und Bildern.\n"
                               "„Alles auf Standard“: alle Einstellungen dieses Tabs (Darstellung und Auswertung) auf\n"
                               "Standard. Daten und Angaben zur Messung bleiben (Dateien, Referenz/Kalibrierung, Schichtdicke,\n"
                               "eingegebene Werte, Bildunterschrift, Exportgröße). Rückgängig (Strg+Z) holt alles zurück.",
                               "“Reset layout”: only the positions of labels, inset and images.\n"
                               "“Reset all to defaults”: all settings of this tab (display and analysis) back to defaults.\n"
                               "Data and measurement details stay (files, reference/calibration, path length, entered\n"
                               "values, caption, export size). Undo (Ctrl+Z) brings everything back."),
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
    "downloading": ("Modell wird geladen…", "Downloading model…"),
    "cancel": ("Abbrechen", "Cancel"),
    "working": ("Rechne…", "Working…"),
    "err_title": ("Fehler", "Error"),
    "exported_to": ("Exportiert nach:\n{p}", "Exported to:\n{p}"),
    "mw_formula": ("{f}, M = {mw:.2f} g/mol", "{f}, M = {mw:.2f} g/mol"),
    "about": ("Elucida {v} (früher Spectravolt)\nVon der Synthese zur SI: Auswertung und publikationsfertige Abbildungen "
              "für UV-Vis, NMR, IR, HRMS, Fluoreszenz, CV, SEC, EPR, Röntgenstruktur und DFT – als SI-Abschnitt in Word.",
              "Elucida {v} (formerly Spectravolt)\nFrom synthesis to SI: evaluation and publication-ready figures for "
              "UV-Vis, NMR, IR, HRMS, fluorescence, CV, SEC, EPR, X-ray and DFT – exported as an SI section in Word."),
    "load_first": ("Bitte zuerst eine CSV öffnen.", "Please open a CSV first."),
    "tab_eps": ("UV-Vis (ε)", "UV-Vis (ε)"),
    "tab_overlay": ("UV-Vis-Overlay", "UV-Vis overlay"),
    "tab_fluo": ("Fluoreszenz", "Fluorescence"),
    "tab_save": ("Vorlage speichern…", "Save preset…"),
    "tab_load": ("Vorlage laden…", "Load preset…"),
    "tab_presets": ("Vorlagen", "Presets"),
    "welcome_sub": ("Von der Synthese zur SI: Auswertung und Abbildungen für UV-Vis, NMR, IR, HRMS, CV, EPR, X-Ray, DFT "
                    "und mehr. Eine Verbindung sammelt alle ihre Daten, ein Projekt die Verbindungen einer "
                    "Veröffentlichung.",
                    "From synthesis to the SI: analysis and figures for UV-Vis, NMR, IR, HRMS, CV, EPR, X-ray, DFT and "
                    "more. A compound collects all its data, a project the compounds of a paper."),
    "welcome_recent": ("Zuletzt geöffnete Verbindungen", "Recently opened compounds"),
    "compound_note": ("Notiz", "Note"),
    "compound_oil": ("Öl", "Oil"),
    "compound_oil_tip": ("Öl bei Raumtemperatur: in der SI steht „m.p. <25 °C“",
                         "Oil at room temperature: the SI reads “m.p. <25 °C”"),
    "compound_known": ("Literaturbekannt", "Known from the literature"),
    "compound_known_tip": ("Für die Checkliste des Projekts: bekannte Verbindungen brauchen nur ¹H- und ¹³C-NMR",
                           "For the checklist of the project: known compounds only need ¹H and ¹³C NMR"),
    "compound_lit": ("Literatur", "Reference"),
    "compound_lit_ph": ("Zitat oder DOI, z. B. J. Org. Chem. 2020, 85, 1234", "Citation or DOI, e.g. J. Org. Chem. 2020, 85, 1234"),
    "compound_note_ph": ("z. B. Radikalkation von 6m", "e.g. radical cation of 6m"),
    "compound_note_tip": ("Was ist das? Steht auf dem Startbildschirm und in der Titelleiste, geht an Characterization "
                          "(elucida.json) – nicht in SI, Word-Export oder Datenpaket.",
                          "What is it? Shown on the welcome page and in the title bar, passed to Characterization "
                          "(elucida.json) – not into the SI, Word export or data package."),
    "recent_search_ph": ("Suchen in allen Projekten: Name/Nummer, Laborkürzel (z. B. RE-3-150), Summenformel, Notiz, "
                         "Projekt …",
                         "Search all projects: name/number, lab code (e.g. RE-3-150), formula, note, project …"),
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
    "grp_export": ("Achsen, Größe und Formate", "Axes, size and formats"),
    "grp_export_size": ("Größe und Formate", "Size and formats"),
    "grp_refs": ("Referenzierung", "Referencing"),
    "grp_more_display": ("Weitere Darstellung", "More display options"),
    "grp_highlight": ("Hervorheben und Labels", "Highlighting and labels"),
    "grp_intensity": ("Intensität und Kinetik", "Intensity and kinetics"),
    "grp_atoms": ("Atome und Fragmente", "Atoms and fragments"),
    "tab_presets_tip": ("Einstellungen dieses Tabs als Vorlage speichern oder laden (Daten bleiben unberührt)",
                        "Save or load this tab's settings as a preset (data are not affected)"),
    "card_select_first": ("{t}: erst einen Eintrag in der Liste oben auswählen.",
                          "{t}: first select an entry in the list above."),
    "nav_grp_syn": ("Synthese & Analytik", "Synthesis & analysis"),
    "nav_grp_uv": ("UV-Vis & Photophysik", "UV-Vis & photophysics"),
    "nav_grp_ec": ("Elektrochemie & EPR", "Electrochemistry & EPR"),
    "nav_grp_struct": ("Struktur & Rechnung", "Structure & computation"),
    "tab_save_tip": ("Einstellungen dieses Tabs als Vorlage (YAML) speichern, z. B. für andere Verbindungen. Daten und "
                     "Verbindung bleiben unberührt – gespeichert wird über die Werkzeugleiste.",
                     "Save this tab's settings as a preset (YAML), e.g. for other compounds. Data and compound are not "
                     "affected – the toolbar saves the compound."),
    "tab_load_tip": ("Einstellungen aus einer Vorlage (YAML) übernehmen; geladene Daten bleiben",
                     "Apply settings from a preset (YAML); loaded data stay"),
    "tab_empty": ("Noch keine Daten – links Dateien hinzufügen.", "No data yet – add files on the left."),
    "guide_syn_title": ('Synthese: „Synthesis of …“ mit Schema und Vorschrift für die SI', 'Synthesis: “Synthesis of …” with scheme and procedure for the SI'),
    "guide_syn_files": ('Dateien: ChemDraw-Schema als CDXML – das Bild zeichnet Elucida daraus; optional mit gleichem Namen daneben: SVG/PDF (Bild hat Vorrang), .cdx (in Word bearbeitbares Objekt), .emf (dessen Vorschau)', 'Files: ChemDraw scheme as CDXML – Elucida draws the picture from it; optionally next to it with the same name: SVG/PDF (picture takes precedence), .cdx (object editable in Word), .emf (its preview)'),
    "guide_syn_steps": ("Namen eintragen (Vorgabe: Name der Verbindung)\nSchema wählen und die Vorschrift schreiben – Mengen "
                        "wie „(1.03 g, 5.00 mmol, 1.0 eq.)“\nReagenzien eintragen oder „Aus Schema“ – die Mengen in der "
                        "Vorschrift werden geprüft\nAusgabe: „Exportieren“ unten (Word-Datei) oder SI (Word) in der "
                        "Werkzeugleiste",
                        "Enter the name (default: name of the compound)\nChoose the scheme and write the procedure – amounts "
                        "like “(1.03 g, 5.00 mmol, 1.0 eq.)”\nEnter reagents or use “From scheme” – the amounts in the "
                        "procedure are checked\nOutput: “Export” at the bottom (Word file) or SI (Word) in the toolbar"),
    "guide_nmr_title": ('NMR: Spektren aus MestReNova mit Struktur und die NMR-Zeile', 'NMR: spectra from MestReNova with structure, and the NMR line'),
    "guide_nmr_files": ('Dateien: SVG-Export aus MestReNova (Datei → Speichern unter → SVG; EMF geht unverändert nach Word), auch per Ziehen ins Fenster; optional TopSpin-Daten und Mnova-Dokumente (Reiter Rohdaten)', 'Files: SVG export from MestReNova (File → Save as → SVG; EMF goes into Word unchanged), also by dragging into the window; optionally TopSpin data and Mnova documents (Raw data tab)'),
    "guide_nmr_steps": ("SVG hinzufügen – Kern und Reihenfolge erkennt das Programm\nStruktur kommt aus dem Dialog "
                        "Verbindung; Lage automatisch oder in der Vorschau ziehen\nMultiplettbericht aus Mnova unter "
                        "„NMR-Zeile“ einfügen (¹³C auch „Zeile aus Peaklabels“)\nWord speichern (zwei Spektren je Seite) oder "
                        "über SI (Word)",
                        "Add the SVG – nucleus and order are recognised\nThe structure comes from the Compound dialog; placed "
                        "automatically or dragged in the preview\nPaste the Mnova multiplet report under “NMR line” (¹³C also "
                        "“line from peak labels”)\nSave Word (two spectra per page) or via SI (Word)"),
    "guide_irms_title": ('IR + EA: IR-Peakliste und Elementaranalyse als SI-Zeilen', 'IR + EA: IR peak list and elemental analysis as SI lines'),
    "guide_irms_files": ("Dateien: Bruker-OPUS-Datei (*.0) und/oder OPUS-PDF mit Peakbeschriftung, auch per Ziehen ins "
                         "Fenster; für die EA die Summenformel der Verbindung (Werkzeugleiste)",
                         "Files: Bruker OPUS file (*.0) and/or OPUS PDF with peak labels, also by dragging into the window; "
                         "for the EA the formula of the compound (toolbar)"),
    "guide_irms_steps": ('IR-Daten wählen – mit PDF gelten genau die OPUS-Peaks, sonst sucht das Programm die Banden (Peakschwelle)\nBanden, die nicht in die Liste sollen, abhaken; Intensitäten w/m/s/br optional\nEA: gefundene C/H/N/S-Werte eintragen, ggf. Solvat; Abweichungen über 0,4 % werden markiert\nZeilen kopieren (Formatierung bleibt in Word) oder über SI (Word)', 'Choose the IR data – with the PDF the OPUS peaks are used exactly, otherwise bands are searched (peak threshold)\nUntick bands that should not be listed; intensities w/m/s/br optional\nEA: enter the found C/H/N/S values, a solvate if needed; deviations above 0.4 % are marked\nCopy the lines (formatting is kept in Word) or via SI (Word)'),
    "guide_hrms_title": ('HRMS: HR-MS-Zeile (calc./found) mit Spektrum und Isotopenmuster', 'HRMS: HR-MS line (calc./found) with spectrum and isotope pattern'),
    "guide_hrms_files": ('Dateien: Word-Bericht der Massenabteilung (.docx) und/oder Bruker-Messordner (.d), auch per Ziehen ins Fenster', 'Files: report of the mass spectrometry service (.docx) and/or Bruker measurement folder (.d), also by dragging'),
    "guide_hrms_steps": ("Bericht und/oder Rohdaten wählen\nSummenformel prüfen (aus der Verbindung oder „Verbindung aus dem "
                         "MS-Bericht übernehmen“)\nIon wählen; found ist vorgewählt – mit Rohdaten den LC-Bereich im "
                         "Chromatogramm ziehen oder einen Peak anklicken\nHRMS-Zeile kopieren, Abbildung exportieren oder über "
                         "SI (Word)",
                         "Choose the report and/or raw data\nCheck the formula (from the compound or “Take compound from the "
                         "MS report”)\nChoose the ion; found is preselected – with raw data drag the LC range in the "
                         "chromatogram or click a peak\nCopy the HRMS line, export the figure or via SI (Word)"),
    "guide_eps_title": ('UV-Vis (ε): Absorptionskoeffizienten aus einer Verdünnungsreihe, Abbildung im Origin-Stil', 'UV-Vis (ε): absorption coefficients from a dilution series, figure in Origin style'),
    "guide_eps_files": ('Dateien: Cary-CSV/TXT, DSW/BSW oder Eclipse-CSV, auch per Ziehen ins Fenster. Konzentration aus dem Probennamen, z. B. ABC-1-0p5mgml_THF = 0,5 mg/mL – sonst Tabelle zum Eintragen', 'Files: Cary CSV/TXT, DSW/BSW or Eclipse CSV, also by dragging into the window. Concentration from the sample name, e.g. ABC-1-0p5mgml_THF = 0.5 mg/mL – otherwise a table to fill in'),
    "guide_eps_steps": ('Messdaten öffnen, Konzentrationen und Einheit prüfen\nVerbindung: Struktur (CDXML) und bei mg/mL die Molmasse, optional Küvettenfoto\nSchichtdicke und Cutoff prüfen; Banden in der Ergebnistabelle an- oder abwählen\nExportieren; die UV-Vis-Zeile für die SI steht unter „SI-Zeile“', 'Open the measurement data, check concentrations and unit\nCompound: structure (CDXML) and, for mg/mL, the molar mass; optionally a cuvette photo\nCheck path length and cutoff; tick or untick bands in the results table\nExport; the UV-Vis line for the SI is under “SI line”'),
    "guide_overlay_title": ('Overlay: mehrere UV-Vis-Spektren in einer Abbildung – gemessen, TD-DFT und SEC', 'Overlay: several UV-Vis spectra in one figure – measured, TD-DFT and SEC'),
    "guide_overlay_files": ('Dateien: Messungen (CSV/TXT/DSW/BSW), TD-DFT-Ausgaben von ORCA oder Gaussian, Spektren aus dem SEC-Tab', 'Files: measurements (CSV/TXT/DSW/BSW), TD-DFT outputs from ORCA or Gaussian, spectra from the SEC tab'),
    "guide_overlay_steps": ('Spektren mit „Messung…“, „TD-DFT…“ oder „SEC…“ hinzufügen\nNormiert (auf die Bande im Normierungsbereich) oder als ε – für ε je Messung Konzentration und Schichtdicke eintragen\nTD-DFT: Bandenbreite (FWHM) und Verschiebung je Rechnung, Übergänge optional als Striche\nReihenfolge, Farben, Stapeln – dann Exportieren', 'Add spectra with “Measurement…”, “TD-DFT…” or “SEC…”\nNormalised (to the band in the normalisation range) or as ε – for ε enter concentration and path length per measurement\nTD-DFT: band width (FWHM) and shift per calculation, transitions optionally as sticks\nOrder, colours, stacking – then Export'),
    "guide_fluo_title": ('Fluoreszenz: Absorption und Emission mit Stokes-Verschiebung', 'Fluorescence: absorption and emission with Stokes shift'),
    "guide_fluo_files": ('Dateien: Absorption als beliebige UV-Vis-Datei, Emission als Cary-Eclipse-CSV oder .FBSW; optional zwei Küvettenfotos (Tageslicht und UV)', 'Files: absorption as any UV-Vis file, emission as Cary Eclipse CSV or .FBSW; optionally two cuvette photos (daylight and UV)'),
    "guide_fluo_steps": ('Links Absorptions- und Emissionsdatei wählen (λex kommt aus der Emissionsdatei)\n„Bande von Interesse“ für die Normierung der Absorption prüfen\nStokes-Verschiebung und Absorbanz bei λex ablesen (Warnung ab A = 0,1)\nFotos und Struktur, dann Exportieren', 'Choose the absorption and emission files on the left (λex comes from the emission file)\nCheck the “band of interest” used to normalise the absorption\nRead the Stokes shift and the absorbance at λex (warning from A = 0.1)\nPhotos and structure, then Export'),
    "guide_cv_title": ('CV: Cyclovoltammogramme mit E½, ΔEₚ, Nicholson und Scanraten-Auswertung', 'CV: cyclic voltammograms with E½, ΔEₚ, Nicholson and scan-rate analysis'),
    "guide_cv_files": ('Dateien: Gamry-.DTA (Scanrate und Elektrodenfläche kommen aus der Datei)', 'Files: Gamry .DTA (scan rate and electrode area come from the file)'),
    "guide_cv_steps": ('Eine oder mehrere Messungen hinzufügen, z. B. eine Scanraten-Serie\nRedoxpaare: „Vorschlagen“ oder Fenster von Hand (von–bis)\nReferenz: wie gemessen, intern (Fc oder Ac₂Fc) oder feste Verschiebung\nAuftragung wählen, SI-Text kopieren, Exportieren', 'Add one or more measurements, e.g. a scan-rate series\nRedox couples: “Suggest” or windows by hand (from–to)\nReference: as measured, internal (Fc or Ac₂Fc) or a fixed shift\nChoose the plot, copy the SI text, Export'),
    "guide_sec_title": ('SEC: UV-Vis-Spektren während eines Potentialscans', 'SEC: UV-Vis spectra during a potential scan'),
    "guide_sec_files": ('Dateien: Spektrenserie aus B&W-Tek-BWSpec (Textexport) und die Gamry-.DTA des Potentialscans', 'Files: spectrum series from B&W Tek BWSpec (text export) and the Gamry .DTA of the potential scan'),
    "guide_sec_steps": ('Spektren und Potentialdatei wählen – jedes Spektrum bekommt sein Potential über die Uhrzeit\nAnsicht: Spektrenserie, Differenzspektren oder A bei λ gegen E (scheinbarer Nernst-Fit)\nZwischenspezies über ihr Potential hervorheben, Felder der Bildunterschrift ausfüllen\nExportieren', 'Choose spectra and potential file – each spectrum gets its potential from the clock time\nView: spectrum series, difference spectra or A at λ versus E (apparent Nernst fit)\nHighlight intermediate species by their potential, fill in the caption fields\nExport'),
    "guide_epr_title": ('EPR: CW-EPR-Spektren mit Simulation, S = ½-Fit und Kinetik', 'EPR: CW EPR spectra with simulation, S = ½ fit and kinetics'),
    "guide_epr_files": ('Dateien: Bruker BES3T (.dsc + .DTA) oder zweispaltiger Text (z. B. MS400); Simulationen aus EasySpin als Text', 'Files: Bruker BES3T (.dsc + .DTA) or two-column text (e.g. MS400); simulations from EasySpin as text'),
    "guide_epr_steps": ('Messung hinzufügen; optional ein Dunkelspektrum abziehen\nBasislinie, Ausblenden und Glätten unter „Verarbeitung“\nSimulation laden oder eine S = ½-Simulation anlegen und fitten; Feldkalibrierung mit TEMPO möglich\nExportieren (Abbildung und Textdateien für EasySpin)', 'Add a measurement; optionally subtract a dark spectrum\nBaseline, masking and smoothing under “Processing”\nLoad a simulation or create and fit an S = ½ simulation; field calibration with TEMPO possible\nExport (figure and text files for EasySpin)'),
    "guide_xray_title": ('X-Ray: ORTEP-Abbildung und Kristalldatentabellen aus der CIF', 'X-ray: ORTEP figure and crystal data tables from the CIF'),
    "guide_xray_files": ('Dateien: CIF, auch per Ziehen ins Fenster; jeder data_-Block mit Atomen wird ein Eintrag', 'Files: CIF, also by dragging into the window; every data_ block with atoms becomes an entry'),
    "guide_xray_steps": ('CIF hinzufügen\nZiehen dreht, rechte Taste verschiebt, Mausrad zoomt; Stil, Labels und ausgeblendete Atome links\nAtome anklicken: 2 = Abstand, 3 = Winkel, 4 = Diederwinkel – Werte mit esd aus der CIF\nTabellen kopieren, Exportieren oder über SI (Word)', 'Add a CIF\nDrag rotates, right button pans, wheel zooms; style, labels and hidden atoms on the left\nClick atoms: 2 = distance, 3 = angle, 4 = torsion – values with esd from the CIF\nCopy the tables, Export or via SI (Word)'),
    "guide_dft_title": ('DFT: Geometrien darstellen, umnummerieren und den SI-Block (Koordinaten, Energien) erzeugen', 'DFT: show geometries, renumber them and create the SI block (coordinates, energies)'),
    "guide_dft_files": ('Dateien: xyz (auch Trajektorien), ORCA-6-Ausgabe (.out) oder Gaussian-Ausgabe (.log), auch per Ziehen ins Fenster', 'Files: xyz (also trajectories), ORCA 6 output (.out) or Gaussian output (.log), also by dragging into the window'),
    "guide_dft_steps": ('Datei hinzufügen\nDrehen und messen wie im X-Ray-Tab\nOptional umnummerieren: „Nummerieren“ und die Atome der Reihe nach anklicken, oder „Wie Vorlage“\nSI-Text kopieren, Word speichern oder über SI (Word)', 'Add a file\nRotate and measure as in the X-ray tab\nOptionally renumber: “Number atoms” and click the atoms in order, or “Like template”\nCopy the SI text, save Word or via SI (Word)'),
    "guide_more": ("Ausführliche Anleitung (README) öffnen", "Open the detailed guide (README)"),
    "guide_add": ("Dateien hinzufügen…", "Add files…"),
    "note_error": ("Fehler beim Zeichnen: {e} – Details unter Hilfe → Protokoll", "Error while drawing: {e} – details under Help → Log"),
    "act_log": ("Protokoll…", "Log…"),
    "log_title": ("Protokoll", "Log"),
    "drag_hint_tab": ("Legende, Labels und Bilder lassen sich mit der Maus verschieben, Bilder per "
                      "Mausrad skalieren. Über den Kurven zeigt eine Einblendung unten rechts λ und den Wert.",
                      "Legend, labels and images can be dragged with the mouse; scroll over images to "
                      "resize. Over the curves a box at the bottom right shows λ and the value."),
    "auto": ("auto", "auto"),
    "ov_curves": ("Spektren", "Spectra"),
    "tab_irms": ("IR + EA", "IR + EA"),
    "tab_hrms": ("HRMS", "HRMS"),
    "ms_xrange": ("m/z-Bereich (Bild)", "m/z range (figure)"),
    "ms_chrom": ("Chromatogramm", "Chromatogram"),
    "ms_chrom_tip": ("Gesamt-Ionenstrom (grau) und Ionenstrom des gesuchten Ions (rot, ± 10 ppm); blau = LC-Bereich "
                     "für das gemittelte Spektrum. Mit der Maus ziehen, um den Bereich zu wählen.",
                     "Total ion current (grey) and ion current of the target ion (red, ± 10 ppm); blue = LC range used "
                     "for the averaged spectrum. Drag with the mouse to choose the range."),
    "ms_display": ("Spektrum", "Spectrum"),
    "ms_show_calc": ("Berechnetes Isotopenmuster (gespiegelt, rot)", "Calculated isotope pattern (mirrored, red)"),
    "ms_mz_labels": ("m/z an den größten Peaks", "m/z at the largest peaks"),
    "ms_pick_hint": ("Peak im Spektrum anklicken, um ihn als found zu übernehmen; im Chromatogramm ziehen setzt den "
                     "LC-Bereich. Spektrum = Mittel der Linienspektren des Geräts im LC-Bereich (keine Profilkurve).",
                     "Click a peak in the spectrum to use it as found; drag in the chromatogram to set the LC range. "
                     "Spectrum = mean of the instrument's line spectra in the LC range (no profile curve)."),
    "ms_pick_entry": ("Im Spektrum gewählt: {mz}  ({ppm} ppm)", "Picked in the spectrum: {mz}  ({ppm} ppm)"),
    "ms_iso_info": ("Isotope (gemessen / berechnet, relativ zu M): {items}",
                    "Isotopes (measured / calculated, relative to M): {items}"),
    "ir_group": ("IR", "IR"),
    "ir_files": ("IR-Daten", "IR data"),
    "flt_ir": ("Bruker OPUS / PDF (*.0 *.1 *.2 *.3 *.4 *.5 *.6 *.7 *.8 *.9 *.pdf)", "Bruker OPUS / PDF (*.0 *.1 *.2 *.3 *.4 *.5 *.6 *.7 *.8 *.9 *.pdf)"),
    "ir_pdf_empty": ("keine Peakwerte im PDF gefunden (OPUS-Ausdruck mit Peakbeschriftung nötig)",
                     "no peak values found in the PDF (OPUS print-out with peak labels needed)"),
    "ir_pdf_ambiguous": ("mehrere Spektren ausgewählt: das PDF heißt nicht wie das übernommene (letzte) "
                         "Spektrum und wurde nicht übernommen – PDF einzeln zum Spektrum laden",
                         "several spectra selected: the PDF is not named like the spectrum kept (the last one) "
                         "and was not used – load the PDF on its own with its spectrum"),
    "ir_full": ("gesamt", "full"),
    "ir_range": ("Bereich", "Range"),
    "ir_xrange": ("ṽ-Bereich (Bild) [cm⁻¹]", "ṽ range (figure) [cm⁻¹]"),
    "ir_prom": ("Peakschwelle", "Peak threshold"),
    "ir_prom_tip": ("Mindesttiefe einer Bande relativ zur stärksten (kleiner = mehr Peaks). Nur bei eigener Peaksuche "
                    "in der OPUS-Datei; mit PDF gilt die Peakliste aus OPUS.",
                    "Minimum depth of a band relative to the strongest one (smaller = more peaks). Only for the own peak "
                    "search in the OPUS file; with a PDF the OPUS peak list is used."),
    "ir_with_int": ("Intensitäten angeben (w/m/s, br)", "Give intensities (w/m/s, br)"),
    "ir_with_int_tip": ("Aus der relativen Tiefe: s ≥ 60 %, m ≥ 30 %, sonst w; br bei Halbwertsbreite > 120 cm⁻¹. "
                        "Braucht die OPUS-Datei (Spektrum).",
                        "From the relative depth: s ≥ 60 %, m ≥ 30 %, otherwise w; br for half widths > 120 cm⁻¹. "
                        "Needs the OPUS file (spectrum)."),
    "ir_labels": ("Wellenzahlen im Bild beschriften", "Label wavenumbers in the figure"),
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
    "ir_labels_clamped": ("{n} Wellenzahl-Label(s) passen nicht in den festen y-Bereich und liegen am Rand – "
                          "min verkleinern oder „auto“ wählen.",
                          "{n} wavenumber label(s) do not fit into the fixed y range and sit at the edge – "
                          "lower min or choose “auto”."),
    "ir_intensity": ("Intensität", "Intensity"),
    "si_copy": ("In Zwischenablage (mit Formatierung für Word)", "Copy to clipboard (formatted for Word)"),
    "ea_group": ("Elementaranalyse", "Elemental analysis"),
    "ea_solvate": ("Solvat", "Solvate"),
    "ea_solvate_ph": ("z. B. 0.5 CH2Cl2 (optional)", "e.g. 0.5 CH2Cl2 (optional)"),
    "ea_solvate_tip": ("Wird zur Formel addiert (berechnete Werte und Zeile), mehrere mit Komma: 0.5 CH2Cl2, H2O",
                       "Added to the formula (calculated values and line); several separated by commas: 0.5 CH2Cl2, H2O"),
    "ea_calc": ("berechnet", "calculated"),
    "ea_found": ("gefunden", "found"),
    "ea_enter": ("Gefundene Werte eintragen (nur die gemessenen Elemente).",
                 "Enter the found values (only the measured elements)."),
    "ea_ok": ("Alle Abweichungen ≤ 0.4 % (übliche Grenze der Journals).",
              "All deviations ≤ 0.4 % (usual limit of the journals)."),
    "ea_dev": ("⚠ Abweichung > 0.4 %: {els} – viele Journals verlangen ≤ 0.4 %; ggf. Solvat prüfen.",
               "⚠ deviation > 0.4 %: {els} – many journals require ≤ 0.4 %; check for a solvate."),
    "tab_si_line": ("SI-Zeile", "SI line"),
    "si_solvent": ("Lösungsmittel", "Solvent"),
    "si_solvent_ph": ("optional, z. B. THF → „UV-Vis (THF): …“", "optional, e.g. THF → “UV-Vis (THF): …”"),
    "si_uv_hint": ("Banden wie im Bild (abgewählte und solche unter der R²-Schwelle fehlen), aufsteigend; ε gerundet "
                   "auf die Genauigkeit des Standardfehlers, ohne ±.",
                   "Bands as in the figure (deselected ones and those below the R² threshold are left out), "
                   "ascending; ε rounded to the precision of the standard error, without ±."),
    "si_uv_none": ("Noch keine Banden mit Fit.", "No fitted bands yet."),
    "act_export_si": ("SI-Abschnitt exportieren (Word) …", "Export SI section (Word) …"),
    "act_datapack": ("Datenpaket (Zip) exportieren …", "Export data package (zip) …"),
    "dp_title": ("Datenpaket (Zip) exportieren", "Export data package (zip)"),
    "dp_hint": ("Rohdaten dieser Verbindung als Zip für ein Datenrepositorium (z. B. TUDOdata), je Analytik ein Ordner "
                "wie NMR/1H/10, IR, MS, UV-Vis, CV/<Lösungsmittel>, EPR. X-Ray (CCDC) und Synthese gehören nicht hinein. "
                "Laborkürzel werden in Namen und Textdateien durch die Verbindung ersetzt.",
                "Raw data of this compound as a zip for a data repository (e.g. TUDOdata), one folder per technique "
                "like NMR/1H/10, IR, MS, UV-Vis, CV/<solvent>, EPR. X-ray (CCDC) and synthesis are not included. "
                "Lab codes are replaced by the compound in names and text files."),
    "dp_name": ("Name (Zip und Ordner)", "Name (zip and folder)"),
    "dp_name_tip": ("Wie in der Publikation, z. B. 6m – ergibt 6m.zip mit dem Ordner 6m/",
                    "As in the publication, e.g. 6m – gives 6m.zip with the folder 6m/"),
    "dp_col_file": ("Im Zip", "In the zip"),
    "dp_col_size": ("Größe", "Size"),
    "dp_codes": ("Laborkürzel ersetzen", "Replace lab codes"),
    "dp_code": ("Kürzel", "Code"),
    "dp_code_name": ("in Datei-/Ordnernamen", "in file/folder names"),
    "dp_code_text": ("im Inhalt", "in the contents"),
    "dp_code_add": ("Kürzel hinzufügen", "Add code"),
    "dp_text": ("auch im Inhalt: Kürzel → „Compound …“, Datum und Uhrzeit löschen (Textdateien, TopSpin-Parameter, "
                "MS-Bericht, OPUS)",
                "also in the contents: codes → “Compound …”, delete date and time (text files, TopSpin parameters, "
                "MS report, OPUS)"),
    "dp_text_tip": ("Messwerte (FID, ser, Spektren) bleiben bytegleich. Im MS-Bericht auch Ersteller und Datum der "
                    "Datei. PDF, Mnova und Bruker-.d lassen sich nicht bearbeiten; ein Kürzel darin steht danach im "
                    "Protokoll",
                    "Measured values (FID, ser, spectra) stay byte-identical. In the MS report also the file's author "
                    "and date. PDF, Mnova and Bruker .d cannot be edited; a code in them is listed in the log"),
    "dp_export": ("Exportieren …", "Export …"),
    "dp_size": ("{n} Einträge, {size} (vor dem Packen)", "{n} entries, {size} (before compression)"),
    "dp_writing": ("Datenpaket wird geschrieben …", "Writing the data package …"),
    "dp_done": ("Datenpaket gespeichert: {p} ({n} Dateien, {size}; Kürzel in {t} Textdateien ersetzt)",
                "Data package saved: {p} ({n} files, {size}; codes replaced in {t} text files)"),
    "dp_kept": ("Kürzel noch enthalten (Binärdateien, unverändert):\n  {files}",
                "Codes still contained (binary files, unchanged):\n  {files}"),
    "dp_grp_nmr": ("NMR (TopSpin, Mnova)", "NMR (TopSpin, Mnova)"),
    "dp_grp_ir": ("IR", "IR"),
    "dp_grp_ms": ("MS (Bericht, Rohdaten)", "MS (report, raw data)"),
    "dp_grp_uvvis": ("UV-Vis", "UV-Vis"),
    "dp_grp_overlay": ("UV-Vis-Overlay (auch Vergleichsspektren)", "UV-Vis overlay (also comparison spectra)"),
    "dp_grp_fluo": ("Fluoreszenz", "Fluorescence"),
    "dp_grp_cv": ("CV", "CV"),
    "dp_grp_sec": ("SEC", "SEC"),
    "dp_grp_epr": ("EPR", "EPR"),
    "dp_grp_dft": ("DFT (Rechnungen)", "DFT (calculations)"),
    "dp_grp_elucida": ("Ergebnisse aus Elucida (Abbildungen, SI)", "Results from Elucida (figures, SI)"),
    "si_written": ("SI-Abschnitt gespeichert: {p}", "SI section saved: {p}"),
    "act_si_short": ("SI (Word)", "SI (Word)"),
    "act_si_tip": ("SI-Abschnitt der Verbindung als Word-Datei; Teile auswählbar (Charakterisierung, X-Ray, DFT)",
                   "SI section of the compound as a Word file; parts selectable (characterisation, X-ray, DFT)"),
    "si_parts_head": ("In die SI übernehmen:", "Include in the SI:"),
    "si_part_char": ("Charakterisierung (m.p., NMR, IR, HR-MS, UV-Vis, Elementaranalyse)",
                     "Characterisation (m.p., NMR, IR, HR-MS, UV-Vis, elemental analysis)"),
    "si_part_nmr": ("NMR-Spektren (zwei je Seite)", "NMR spectra (two per page)"),
    "si_part_figs": ("Abbildungen aller Tabs (UV-Vis, IR, HR-MS, Fluoreszenz, CV, SEC, EPR; zwei je Seite)",
                     "Figures from all tabs (UV-Vis, IR, HR-MS, fluorescence, CV, SEC, EPR; two per page)"),
    "cap_box": ("Bildunterschrift (SI-Export)", "Figure caption (SI export)"),
    "cv_cap_tip": ("Unterschrift wie in der SI der Gruppe. Vorschubgeschwindigkeit, iR-Kompensation (aus der Gamry-"
                   "Datei), Referenz und Pfeile kommen aus den sichtbaren Messungen, der Rest aus diesen Feldern.",
                   "Caption as in the group's SI. Scan rate, iR compensation (from the Gamry file), reference and "
                   "arrows come from the visible measurements, the rest from these fields."),
    "cap_conc": ("Konzentration", "Concentration"),
    "cap_conc_ph": ("z. B. 1.7±0.1 mg mL-1", "e.g. 1.7±0.1 mg mL-1"),
    "cap_solvent": ("Lösungsmittel", "Solvent"),
    "cv_cap_solvent_ph": ("leer = Gruppe der Messungen (mehrere: „different solvents“)",
                          "empty = group of the measurements (several: “different solvents”)"),
    "cap_solvent_ph": ("z. B. THF", "e.g. THF"),
    "sec_cap_tip": ("Unterschrift wie in der SI der Gruppe. Start-/Endpotential kommen aus dem Scan (erstes/letztes "
                    "gezeigtes Spektrum, Referenz wie die Achse); die Farbcodierung (blau/rot) nur mit hervorgehobenem "
                    "ersten/letzten Spektrum; Zwischenspektren (grün …) nur, wenn sie im Bild hervorgehoben sind.",
                    "Caption as in the group's SI. Start/end potentials come from the scan "
                    "(first/last spectrum shown, reference as on the axis); colour coding (blue/red) only with the "
                    "first/last spectrum highlighted; intermediate spectra (green …) only if highlighted in the figure."),
    "cap_start": ("Spezies am Anfang", "Species at start"),
    "cap_start_ph": ("z. B. neutral", "e.g. neutral"),
    "cap_mid": ("Spezies Zwischenstufe", "Intermediate species"),
    "cap_mid_ph": ("z. B. radical cation (mehrere mit „;“)", "e.g. radical cation (several with “;”)"),
    "cap_end": ("Spezies am Ende", "Species at end"),
    "cap_end_ph": ("z. B. dication", "e.g. dication"),
    "epr_cap_tip": ("Unterschrift wie in der SI der Gruppe. Band aus der Mikrowellenfrequenz; Parameter (g, ΔB_pp, "
                    "Kopplungen in MHz) nur aus eigenen S = ½-Fits, ohne Fehlerangabe. EasySpin-Simulationen bitte "
                    "selbst ergänzen.", "Caption as in the group's SI. Band from the microwave frequency; parameters "
                    "(g, ΔB_pp, couplings in MHz) only from own S = ½ fits, without uncertainties. Please add "
                    "EasySpin simulations yourself."),
    "cap_species": ("Spezies", "Species"),
    "cap_species_ph": ("leer = Verbindung; z. B. 6m^{•+} (^{…} hochgestellt)",
                       "empty = compound; e.g. 6m^{•+} (^{…} superscript)"),
    "cap_el": ("Leitsalz", "Electrolyte"),
    "cap_el_ph": ("z. B. 0.1 M n-Bu4NPF6 (wird gemerkt)", "e.g. 0.1 M n-Bu4NPF6 (remembered)"),
    "cap_temp": ("Temperatur", "Temperature"),
    "cap_cuvette": ("Küvette", "Cuvette"),
    "cap_cuvette_ph": ("leer = 1 cm", "empty = 1 cm"),
    "fluorescence_cap_conc_ph": ("z. B. 10 µM", "e.g. 10 µM"),
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
    "nmr_peaks_tip": ("Für das gewählte 1D-Spektrum (z. B. ¹³C): Verschiebungen aus den Peaklabels des Mnova-SVG als "
                      "Zeile „13C NMR (… MHz, …) δ …“ ins Textfeld (ersetzt eine vorhandene Zeile desselben Kerns). Ein "
                      "beschriftetes Lösungsmittelsignal („77.16 CDCl3“) fällt weg, unbeschriftete bitte löschen.",
                      "For the selected 1D spectrum (e.g. ¹³C): shifts from the peak labels of the Mnova SVG as a line "
                      "“13C NMR (… MHz, …) δ …” in the text field (replaces an existing line of that nucleus). A "
                      "labelled solvent signal (“77.16 CDCl3”) is dropped; please delete unlabelled ones."),
    "nmr_peaks_need": ("Erst ein 1D-Spektrum mit Kern wählen.", "Select a 1D spectrum with a nucleus first."),
    "nmr_peaks_1h": ("Für ¹H bitte den Multiplettbericht aus Mnova einfügen (Peaklabels kennen keine Multipletts).",
                     "For ¹H please paste the multiplet report from Mnova (peak labels have no multiplets)."),
    "nmr_peaks_none": ("Keine Peaklabels in {f} gefunden (in Mnova Peaks beschriften und neu exportieren).",
                       "No peak labels found in {f} (label the peaks in Mnova and export again)."),
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
    "compound_mp": ("Schmelzpunkt", "Melting point"),
    "compound_mp_ph": ("z. B. 67 °C oder 218 °C (decomp.)", "e.g. 67 °C or 218 °C (decomp.)"),
    "ms_group": ("HRMS", "HRMS"),
    "ms_file": ("MS-Bericht", "MS report"),
    "ms_file_tip": ("Bericht der Massenabteilung (.docx): Summenformel, Ion und found. Mit Bericht und Rohdaten ist der "
                    "Wert aus dem Bericht vorgewählt; der aus den Rohdaten steht unter „gefunden“ zur Auswahl.",
                    "Report of the mass spectrometry service (.docx): formula, ion and found. With report and raw data, "
                    "the report value is preselected; the raw-data value can be chosen under “found”."),
    "ms_copy": ("HRMS-Zeile kopieren (für Word)", "Copy HRMS line (for Word)"),
    "ir_copy": ("IR-Zeile kopieren (für Word)", "Copy IR line (for Word)"),
    "ea_copy": ("EA-Zeile kopieren (für Word)", "Copy EA line (for Word)"),
    "uv_copy": ("UV-Vis-Zeile kopieren (für Word)", "Copy UV-Vis line (for Word)"),
    "ms_raw": ("MS-Rohdaten (.d)", "MS raw data (.d)"),
    "ms_raw_tip": ("Bruker-Messordner (.d) mit analysis.baf und analysis.sqlite (z. B. timsTOF); gelesen werden die "
                   "Linienspektren des Geräts. In die Verbindung kommen nur diese beiden Dateien.",
                   "Bruker measurement folder (.d) with analysis.baf and analysis.sqlite (e.g. timsTOF); the "
                   "instrument's line spectra are read. Only these two files are copied into the compound."),
    "ms_raw_bad": ("kein Bruker-Messordner mit analysis.baf und analysis.sqlite",
                   "not a Bruker measurement folder with analysis.baf and analysis.sqlite"),
    "ms_rt": ("LC-Peak (RT)", "LC peak (RT)"),
    "ms_rt_auto": ("automatisch", "automatic"),
    "ms_rt_auto_tip": ("Zusammenhängende Spektren um das Maximum des Ionenstroms (± 10 ppm um calc.) mit mindestens "
                       "50 % der Maximalintensität", "Contiguous spectra around the maximum of the ion current "
                       "(± 10 ppm around calc.) with at least 50 % of the maximum intensity"),
    "ms_raw_entry": ("Rohdaten: {mz}  (Mittel über {n} Spektren, {ppm} ppm)",
                     "Raw data: {mz}  (mean over {n} spectra, {ppm} ppm)"),
    "ms_raw_info": ("Rohdaten: {n} Spektren, RT {rt0}–{rt1} min; Einzelscans {lo}–{hi}, Streuung ± {sd} mDa "
                    "(± {sdp} ppm). found = intensitätsgewichtetes Mittel; einzelne Scans können in der 4. "
                    "Nachkommastelle abweichen.",
                    "Raw data: {n} spectra, RT {rt0}–{rt1} min; single scans {lo}–{hi}, scatter ± {sd} mDa "
                    "(± {sdp} ppm). found = intensity-weighted mean; single scans may differ in the 4th decimal."),
    "ms_raw_few": ("Nur {n} Spektren im LC-Peak – das Mittel ist unsicher.",
                   "Only {n} spectra in the LC peak – the mean is uncertain."),
    "ms_raw_vs_rep": ("Mittel aus den Rohdaten weicht um {d} mDa vom Wert im Bericht ab.",
                      "Mean from the raw data differs by {d} mDa from the value in the report."),
    "ms_raw_none": ("Ion in den Rohdaten nicht gefunden (± 10 ppm um calc.).",
                    "Ion not found in the raw data (± 10 ppm around calc.)."),
    "ms_polarity_raw": ("⚠ die Rohdaten sind im Modus {rep}MS gemessen", "⚠ the raw data were measured in {rep}MS mode"),
    "compound_formula": ("Summenformel", "Formula"),
    "ms_adduct": ("Ion", "Ion"),
    "ms_found": ("gefunden (m/z)", "found (m/z)"),
    "ms_found_tip": ("Gemessene m/z aus den Spektren im Bericht und das Mittel aus den Rohdaten; vorgewählt ist der "
                     "Wert im Bericht am nächsten am berechneten, ohne Bericht das Mittel aus den Rohdaten",
                     "Measured m/z from the spectra in the report and the mean from the raw data; preselected is the "
                     "report value closest to the calculated one, without a report the raw-data mean"),
    "ms_no_formula": ("keine – Verbindung (Werkzeugleiste) festlegen oder MS-Bericht laden",
                      "none – set the compound (toolbar) or load an MS report"),
    "ea_no_formula": ("keine – Verbindung (Werkzeugleiste) festlegen oder im Tab HRMS den MS-Bericht laden",
                      "none – set the compound (toolbar) or load the MS report in the HRMS tab"),
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
               "deviation found − calc = {ppm} ppm (check only, not part of the line)"),
    "ms_dev_high": ("⚠ Abweichung über 5 ppm", "⚠ deviation above 5 ppm"),
    "compound_none": ("Verbindung …", "Compound …"),
    "compound_tip": ("Diese Verbindung (Name, ChemDraw, Formel, Molmasse): Vorgabe für alle Tabs, z. B. ε, Fluoreszenz, IR "
                     "+ EA, HRMS und die SI",
                     "This compound (name, ChemDraw, formula, molar mass): default for all tabs, e.g. ε, fluorescence, IR "
                     "+ EA, HRMS and the SI"),
    "compound_set": ("Verbindung: {c}", "Compound: {c}"),
    "stick_mode_tip": ("Ein gemeinsamer Faktor für Kurve und Striche: Kurvenmaximum = 1 (höchste Stelle der verbreiterten "
                       "Kurve im Normierungsbereich), stärkster Übergang = 1 oder Kurvenmaximum = 1 mit "
                       "Oszillatorstärke f als zweiter Skala rechts (jeder Strich so hoch wie seine Bande)",
                       "One common factor for curve and sticks: curve maximum = 1 (highest point "
                       "of the broadened curve in the normalisation range), strongest transition = 1, or curve "
                       "maximum = 1 with oscillator strength f as a second scale on the right (each stick as high "
                       "as its band)"),
    "xr_prob_ball": ("gilt nur für die Stile Mercury und flach (Kugel-Stab: feste Kugelgröße)",
                     "only for the Mercury and flat styles (ball and stick: fixed sphere size)"),
    "syn_output_hint": ("Erscheint im SI-Export (Werkzeugleiste: SI (Word)); eigene Word-Datei: „Exportieren“ unten.",
                        "Appears in the SI export (toolbar: SI (Word)); own Word file: “Export” at the bottom."),
    "compound_title": ("Verbindung",
                       "Compound"),
    "compound_name": ("Name / Probe", "Name / sample"),
    "compound_name_ph": ("z. B. Probennummer", "e.g. sample number"),
    "compound_hint": ("Formel und Molmasse kommen aus der ChemDraw-Datei (Isotope wie D inklusive) und sind änderbar. "
                      "Tabs, in denen schon eine Struktur oder Molmasse gewählt ist, behalten ihre eigene.",
                      "Formula and molar mass come from the ChemDraw file (isotopes such as D included) and can be edited. "
                      "Tabs that already have a structure or molar mass keep their own."),
    "cv_group": ("Gruppe", "Group"),
    "cv_group_tip": ("Freies Feld, z. B. Lösungsmittel (THF, MeCN …): Datenreihe in den Auftragungen gegen die Scanrate",
                     "Free field, e.g. solvent (THF, MeCN …): data series in the plots against scan rate"),
    "cv_file_ref": ("Referenz der ausgewählten Messung", "Reference of the selected measurement"),
    "cv_fref_global": ("wie unter „Auswertung“ (für alle)", "as under “Analysis” (for all)"),
    "cv_fref_internal": ("eigener interner Standard", "own internal standard"),
    "cv_fref_manual": ("eigene feste Verschiebung", "own fixed shift"),
    "cv_ref_mixed": ("Achtung: Messungen mit unterschiedlicher Referenz (Fc⁺/Fc und Referenzelektrode) in einer Abbildung.",
                     "Note: measurements with different references (Fc⁺/Fc and reference electrode) in one figure."),
    "cv_plot": ("Auftragung", "Plot"),
    "cv_plot_cv": ("Cyclovoltammogramm", "Cyclic voltammogram"),
    "cv_plot_dep": ("Elektrochem. Reversibilität: ΔE_p gegen v", "Electrochem. reversibility: ΔE_p vs. v"),
    "cv_plot_rs": ("Randles-Ševčík: i_p gegen √v", "Randles–Ševčík: i_p vs. √v"),
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
    "cv_e12_each": ("E½ an jeder Kurve beschriften", "Label E½ on every curve"),
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
    "ov_add_exp": ("Messung…", "Measurement…"),
    "ov_add_sec": ("SEC…", "SEC…"),
    "ov_sec_none": ("Im SEC-Tab sind noch keine Spektren geladen.", "No spectra loaded in the SEC tab yet."),
    "ov_sec_pick": ("Serie: Bereich vom ersten bis zum letzten markierten Spektrum, ohne Markierung die ganze Serie; "
                    "alle Spektren mit demselben Faktor auf das Startspektrum normiert (Intensitätsverhältnisse und "
                    "isosbestische Punkte bleiben). Einzelne Spektren: jedes markierte für sich. SEC wird nie als ε "
                    "gezeigt (Schichtdicke und umgesetzte Konzentration der Dünnschichtzelle sind nicht genau bekannt).",
                    "Series: range from the first to the last marked spectrum, without marking the whole series; all "
                    "spectra normalised with the same factor to the start spectrum (intensity ratios and isosbestic "
                    "points are kept). Single spectra: each marked one on its own. SEC is never shown as ε (path "
                    "length and converted concentration in the thin-layer cell are not known exactly)."),
    "ov_sec_series": ("SEC-Serie", "SEC series"),
    "ov_sec_series_label": ("SEC {rng} ({n} Spektren)", "SEC {rng} ({n} spectra)"),
    "ov_sec_mode_all": ("Serie: alle Spektren (gemeinsam normiert)", "Series: all spectra (normalised together)"),
    "ov_sec_mode_ends": ("Serie: nur Anfang und Ende (gemeinsam normiert)",
                         "Series: start and end only (normalised together)"),
    "ov_sec_mode_single": ("Einzelne Spektren (jedes für sich normiert)", "Single spectra (each normalised on its own)"),
    "ov_sec_no_eps": ("„{name}“: SEC-Spektren nur normiert, nicht als ε – ausgelassen",
                      "“{name}”: SEC spectra only normalised, not as ε – skipped"),
    "ov_add_calc": ("TD-DFT…", "TD-DFT…"),
    "ov_name": ("Name", "Name"),
    "ov_color": ("Farbe", "Colour"),
    "ov_type": ("Typ", "Type"),
    "ov_exp": ("Messung", "measured"),
    "ov_states": ("Zustände", "states"),
    "ov_details": ("Ausgewähltes Spektrum", "Selected spectrum"),
    "ov_own_norm": ("eigener (statt „Normierung“ unten)", "own (instead of “Normalisation” below)"),
    "ov_norm_window": ("Normierungsbereich [nm]", "Normalisation range [nm]"),
    "ov_fwhm": ("Breite (FWHM)", "Width (FWHM)"),
    "ov_shift": ("Verschiebung", "Shift"),
    "ov_display": ("Normierung", "Normalisation"),
    "ov_ymode": ("y-Größe", "y quantity"),
    "ov_y_norm": ("normiert (auf die Bande von Interesse)", "normalised (to the band of interest)"),
    "ov_y_eps": ("ε [10³ M⁻¹ cm⁻¹]", "ε [10³ M⁻¹ cm⁻¹]"),
    "ov_y_abs": ("Absorbanz (wie gemessen)", "absorbance (as measured)"),
    "ov_ymode_tip": ("ε: Messungen brauchen Konzentration und Schichtdicke (SEC entfällt). Absorbanz: Messungen und "
                     "SEC wie gemessen, ohne TD-DFT.",
                     "ε: measurements need concentration and path length (SEC is left out). Absorbance: measurements "
                     "and SEC as measured, without TD-DFT."),
    "ov_calc_no_abs": ("„{name}“: TD-DFT hat keine Absorbanz (c, d unbekannt) – ε oder normiert wählen",
                       "“{name}”: TD-DFT has no absorbance (c, d unknown) – choose ε or normalised"),
    "ov_triplets": ("Triplett-Zustände markieren (f = 0)", "Mark triplet states (f = 0)"),
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
    "ov_baseline": ("Basislinie (Offset) abziehen", "Subtract baseline (offset)"),
    "ov_sticks": ("TD-DFT-Übergänge als Striche", "TD-DFT transitions as sticks"),
    "ov_no_signal": ("„{name}“: kein Signal im Normierungsbereich {lo:g}–{hi:g} nm – ausgelassen",
                     "“{name}”: no signal in the normalisation range {lo:g}–{hi:g} nm – skipped"),
    "ov_need_conc": ("„{name}“: für ε Konzentration (und bei mg/mL Molmasse) eintragen – ausgelassen",
                     "“{name}”: enter concentration (and molar mass for mg/mL) for ε – skipped"),
    "ov_struct_color": ("Struktur in Kurvenfarbe", "Structure in curve colour"),
    "ov_soc": ("Spin-Bahn-Kopplung", "Spin–orbit coupling"),
    "soc_soc": ("mit SOC", "with SOC"),
    "soc_nosoc": ("ohne SOC", "without SOC"),
    "ov_scale_offset": ("Skalierung / Versatz", "Scale / offset"),
    "ov_line": ("Linie", "Line"),
    "ls_solid": ("durchgezogen", "solid"),
    "ls_dashed": ("gestrichelt", "dashed"),
    "ls_dotted": ("gepunktet", "dotted"),
    "ls_dashdot": ("Strich-Punkt", "dash-dot"),
    "stick_mode": ("TD-DFT-Normierung", "TD-DFT normalisation"),
    "stick_max": ("stärkster Übergang = 1", "strongest transition = 1"),
    "stick_band": ("Kurvenmaximum = 1", "curve maximum = 1"),
    "stick_faxis": ("Kurvenmaximum = 1, rechts zusätzlich f", "curve maximum = 1, f on the right axis"),
    "ov_faxis_mixed": ("f-Achse ausgelassen: die Rechnungen haben verschiedene Maßstäbe (FWHM/Normierung)",
                       "f axis omitted: the calculations use different scales (FWHM/normalisation)"),
    "fl_data": ("Spektren", "Spectra"),
    "fl_abs": ("Absorption", "Absorption"),
    "fl_em": ("Emission", "Emission"),
    "fl_ex": ("Anregung λex", "Excitation λex"),
    "fl_mask": ("Streulicht bei λex und 2·λex ausblenden", "Hide scattered light at λex and 2·λex"),
    "fl_abs_window": ("Bande von Interesse [nm]", "Band of interest [nm]"),
    "fl_eps_ph": ("optional, z. B. 23604", "optional, e.g. 23604"),
    "fl_stokes_label": ("Stokes-Verschiebung im Bild (am Emissionslabel)",
                        "Stokes shift in the figure (at the emission label)"),
    "fl_stokes": ("Stokes-Verschiebung: {cm} cm⁻¹ ({nm:.0f} nm)", "Stokes shift: {cm} cm⁻¹ ({nm:.0f} nm)"),
    "fl_a_ex": ("Absorbanz bei λex = {ex:.0f} nm: {a:.3f}", "Absorbance at λex = {ex:.0f} nm: {a:.3f}"),
    "fl_inner_filter": ("⚠ A > {lim:g}: Innenfiltereffekt möglich (Emission verzerrt, Quantenausbeute zu "
                        "niedrig) – gilt nur, wenn Absorption und Emission von derselben Lösung stammen.",
                        "⚠ A > {lim:g}: inner-filter effect possible (distorted emission, quantum yield too "
                        "low) – only applies if absorption and emission were measured on the same solution."),
    "fl_images": ("Bilder", "Images"),
    "fl_photo_day": ("Foto Tageslicht", "Photo daylight"),
    "fl_photo_uv": ("Foto unter UV", "Photo under UV"),
    "bands_add": ("zusätzlich zu den automatisch gefundenen", "in addition to automatically found bands"),
    "find_shoulders": ("Schultern automatisch suchen", "Find shoulders automatically"),
    "mark_sh": ("Schultern im Bild mit „(sh)“ kennzeichnen", "Mark shoulders with “(sh)” in figure"),
    "label_index": ("λ und ε im Bild nummerieren (λ₁, ε₁ …)", "Number λ and ε in the figure (λ₁, ε₁ …)"),
    "label_index_tip": ("Indizes aufsteigend nach Wellenlänge, nur für Banden im Bild", "Indices in order of increasing "
                        "wavelength, only for bands shown in the figure"),
    "show_excl": ("ausgeschlossene Punkte im Inset (hohl)", "excluded points in inset (open symbols)"),
    "col_cut": ("Cutoff A", "Cutoff A"),
    "cut_tip": ("Häkchen bei λ: Bande im Bild zeigen. Doppelklick auf „Cutoff A“: eigener Cutoff für "
                "diese Bande (leer = global).",
                "Tick at λ: show band in figure. Double-click “Cutoff A”: own cutoff for this band "
                "(empty = global)."),
    "act_conc": ("Konzentrationen…", "Concentrations…"),
    "size": ("Größe", "Size"),
    "size_std": ("Standard (eng zugeschnitten)", "Standard (tight crop)"),
    "size_half_a4": ("Word: halbe A4-Seite (16 × 11 cm)", "Word: half A4 page (16 × 11 cm)"),
    "size_custom": ("benutzerdefiniert", "custom"),
    "size_wh": ("Breite × Höhe [cm]", "Width × height [cm]"),
    "formats": ("Formate", "Formats"),
    "img_size": ("Größe [% Plotbreite]", "Size [% of plot width]"),
    "xrange": ("λ-Bereich [nm]", "λ range [nm]"),
    "xrange_auto": ("gesamt", "full"),
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
    "unit_choose": ("– bitte wählen –", "– please choose –"),
    "unit_missing": ("Bitte die Konzentrationseinheit wählen.", "Please choose the concentration unit."),
    "start_missing": ("Bitte zuerst die Startkonzentration eintragen.", "Please enter the start concentration first."),
    "act_restart": ("Eingaben zu diesen Messdaten verwerfen…",
                    "Discard inputs for this measurement…"),
    "restart_q": ("Alle Eingaben zu „{name}“ verwerfen?\n\n"
                  "Konzentrationen, Molmassen, Strukturen, Fotos, Einstellungen und Layout im ε-Tab "
                  "werden zurückgesetzt. Die Messdateien bleiben unverändert.",
                  "Discard all inputs for “{name}”?\n\n"
                  "Concentrations, molar masses, structures, photos, settings and layout in the ε tab "
                  "are reset. The measurement files are not changed."),
    "mw_needed": ("⚠ Keine Molmasse: Ausgabe als a [L g⁻¹ cm⁻¹]. Für ε [M⁻¹ cm⁻¹] Molmasse eintragen "
                  "oder CDXML laden.",
                  "⚠ No molar mass: reported as a [L g⁻¹ cm⁻¹]. Enter the molar mass or load a CDXML "
                  "to get ε [M⁻¹ cm⁻¹]."),
    "mw_unused": ("Molmasse wird nicht verwendet: Konzentrationen sind in {u} angegeben.",
                  "Molar mass is not used: concentrations are given in {u}."),
    "dil_factor": ("Faktor", "Factor"),
    "dil_fill": ("Verdünnungsreihe ausfüllen", "Fill dilution series"),
    "dil_hint": ("füllt die markierten Zeilen (oder alle) von oben nach unten: Start, Start/Faktor, …",
                 "fills the selected rows (or all) top to bottom: start, start/factor, …"),
    "conc_none": ("Keine Probe mit Konzentration – nichts auszuwerten.",
                  "No sample with a concentration – nothing to analyse."),
    # ---- Format (Schrift, Rahmen) -----------------------------------------
    "menu_format": ("F&ormat", "F&ormat"),
    "act_text_format": ("Schrift und Rahmen…", "Fonts and frames…"),
    "tf_title": ("Schrift und Rahmen", "Fonts and frames"),
    "tf_scope": ("Gilt für", "Applies to"),
    "tf_scope_global": ("alle Tabs (Standard)", "all tabs (default)"),
    "tf_scope_own": ("nur diesen Tab ({tab})", "this tab only ({tab})"),
    "tf_scope_hint": ("„alle Tabs“ ändert den Standard für jeden Tab ohne eigenes Format. Gezeigt wird nur, was dieser "
                      "Tab im Bild hat.", "“all tabs” changes the default for every tab without its own format. Only "
                      "what this tab has in its figure is shown."),
    "tf_no_text": ("Der Tab „{tab}“ hat keine eigene Textformatierung (Bilder kommen fertig aus MestReNova bzw. "
                   "ChemDraw). Änderungen gelten für alle Tabs.", "The “{tab}” tab has no text formatting of its own "
                   "(figures come ready-made from MestReNova or ChemDraw). Changes apply to all tabs."),
    "tf_grp_labels_cv": ("Labels an den Peaks (E½, E_p)", "Peak labels (E½, E_p)"),
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
    "tf_auto": ("automatisch", "automatic"),
    "tf_bold": ("fett", "bold"),
    "tf_italic": ("kursiv", "italic"),
    "tf_color": ("Farbe", "Colour"),
    "tf_grp_frames": ("Rahmen", "Frames"),
    "tf_axes_frame": ("Geschlossener Rahmen um den Plot (auch oben und rechts)",
                      "Closed frame around the plot (top and right too)"),
    "tf_struct_frame": ("Abgerundeter Rahmen um die Struktur", "Rounded frame around the structure"),
    # ---- Overlay: Stapeln --------------------------------------------------
    "ov_stack_grp": ("Stapeln und Achsen", "Stacking and axes"),
    "ov_stack": ("Gestapelt", "Stacked"),
    "ov_stack_tip": ("Kurven senkrecht übereinander, in der Reihenfolge der Liste (oben = oben).\n"
                     "Zusätzlich gilt der Versatz der einzelnen Kurve.",
                     "Curves stacked vertically in list order (top = top).\n"
                     "The offset of each curve is added on top."),
    "ov_gap": ("Abstand", "Spacing"),
    "ov_gap_tip": ("Abstand der Ebenen in y-Einheiten (normiert: 1 = eine Kurvenhöhe; ε-Modus: 10³ M⁻¹ cm⁻¹)",
                   "Spacing of the levels in y units (normalised: 1 = one curve height; ε mode: 10³ M⁻¹ cm⁻¹)"),
    "ov_yaxis": ("y-Achse", "y axis"),
    "yaxis_auto": ("automatisch (gestapelt: ohne Zahlen)", "automatic (stacked: no numbers)"),
    "yaxis_numbers": ("mit Zahlen", "with numbers"),
    "yaxis_no_numbers": ("ohne Zahlen und Teilstriche", "without numbers and ticks"),
    "yaxis_off": ("ausblenden", "hide"),
    "ov_curve_labels": ("Namen an den Kurven statt Legende", "Names at the curves instead of a legend"),
    "ov_zero_lines": ("Nulllinie je Ebene (gestrichelt)", "Zero line per level (dashed)"),
    "ov_same_level": ("Gleiche Stapelebene wie die Kurve darüber", "Same stacking level as the curve above"),
    "ov_same_level_tip": ("z. B. TD-DFT direkt unter der zugehörigen Messung",
                          "e.g. TD-DFT directly with its measurement"),
    # ---- Cyclovoltammetrie -------------------------------------------------
    "tab_cv": ("CV", "CV"),
    "cv_files": ("Messungen (Gamry .DTA)", "Measurements (Gamry .DTA)"),
    "cv_add": ("Messung…", "Measurement…"),
    "cv_xrange": ("E-Bereich [V]", "E range [V]"),
    "cv_analysis": ("Auswertung", "Analysis"),
    "cv_cycle": ("Zyklus", "Cycle"),
    "cv_cycle_tip": ("Welcher Zyklus gezeigt und ausgewertet wird (zu groß = letzter vorhandener).",
                     "Which cycle is shown and analysed (too large = last available)."),
    "cv_couples": ("Redoxpaare", "Redox couples"),
    "cv_from": ("von [V]", "from [V]"),
    "cv_to": ("bis [V]", "to [V]"),
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
    "cv_ref_none": ("wie gemessen (Referenzelektrode)", "as measured (reference electrode)"),
    "cv_ref_internal": ("intern (Fc / Ac₂Fc in einer Messung)", "internal (Fc / Ac₂Fc in one measurement)"),
    "cv_ref_manual": ("Verschiebung von Hand", "manual shift"),
    "cv_ref_file": ("Messung mit Referenz", "Measurement with reference"),
    "cv_ref_window": ("Fenster Referenz [V, gemessen]", "Reference window [V, measured]"),
    "cv_ref_compound": ("Referenz E° vs. Fc⁺/Fc", "Reference E° vs. Fc⁺/Fc"),
    "cv_ref_custom": ("eigene", "custom"),
    "cv_ref_value_tip": ("E½ der Referenzverbindung gegen Fc⁺/Fc. Ac₂Fc (1,1'-Diacetylferrocen): Vorgabe +0,49 V;\n"
                         "lösungsmittelabhängig – mit der verwendeten Literatur abgleichen.",
                         "E½ of the reference compound vs. Fc⁺/Fc. Ac₂Fc (1,1'-diacetylferrocene): default +0.49 V;\n"
                         "solvent dependent – check against the literature you use."),
    "cv_offset": ("E(Fc⁺/Fc) gemessen", "E(Fc⁺/Fc) measured"),
    "cv_offset_tip": ("Lage von Fc⁺/Fc gegen die Referenzelektrode; wird von allen Potentialen abgezogen.",
                      "Position of Fc⁺/Fc vs. the reference electrode; subtracted from all potentials."),
    "cv_electrode": ("Referenzelektrode", "Reference electrode"),
    "cv_display": ("Darstellung CV", "CV display"),
    "cv_gradient": ("Farbverlauf nach Scanrate (blau → rot)", "Colour gradient by scan rate (blue → red)"),
    "cv_density": ("Stromdichte j [mA cm⁻²] (Elektrodenfläche aus der Datei)",
                   "Current density j [mA cm⁻²] (electrode area from the file)"),
    "cv_show_e12": ("E½ im Bild", "E½ in the figure"),
    "cv_arrow": ("Pfeil für die Scanrichtung", "Arrow for the scan direction"),
    "cv_invert": ("Strom invertieren (US-Konvention)", "Invert current (US convention)"),
    "cv_invert_tip": ("Standard: wie aufgezeichnet (Gamry: IUPAC, anodisch positiv).",
                      "Default: as recorded (Gamry: IUPAC, anodic positive)."),
    "cv_results": ("Ergebnisse", "Results"),
    "cv_ratio_tip": ("Rückpeak/Hinpeak nach Nicholson (Anal. Chem. 1966): berücksichtigt den abklingenden Strom\n"
                     "des Hinlaufs. ≈ 1: chemisch reversibel. i_pa/i_pc mit Basislinie (falls eingeschaltet).",
                     "Reverse/forward peak ratio after Nicholson (Anal. Chem. 1966): accounts for the decaying\n"
                     "forward current. ≈ 1: chemically reversible. i_pa/i_pc with baseline (if enabled)."),
    "cv_ref_note": ("Referenz: {name} bei E½ = {e12} V vs. {el} (ΔE_p = {dep} mV) ≙ {val} V vs. Fc⁺/Fc",
                    "Reference: {name} at E½ = {e12} V vs. {el} (ΔE_p = {dep} mV) ≙ {val} V vs. Fc⁺/Fc"),
    "cv_ref_missing": ("⚠ Referenz nicht gefunden (Messung oder Fenster prüfen) – Achse wie gemessen.",
                       "⚠ Reference not found (check measurement or window) – axis as measured."),
    "cv_edge": ("⚠ Peak am Fensterrand", "⚠ peak at the window edge"),
    "cv_area_missing": ("⚠ Keine Elektrodenfläche in {files} – Strom statt Stromdichte.",
                        "⚠ No electrode area in {files} – current instead of current density."),
    "cv_cycle_missing": ("⚠ {files}: Zyklus {n} fehlt – letzter Zyklus ausgewertet.",
                         "⚠ {files}: cycle {n} missing – last cycle evaluated."),
    "cv_fit_line": ("Paar {n}, i_p{p} ({k} Scanraten): gegen √v Steigung {m} µA (V/s)^-½, Achsenabschnitt {b} µA, "
                    "R² = {r2}; log-log-Steigung {ll} (95-%-KI)",
                    "Couple {n}, i_p{p} ({k} scan rates): vs. √v slope {m} µA (V/s)^-½, intercept {b} µA, "
                    "R² = {r2}; log–log slope {ll} (95% CI)"),
    "cv_baseline": ("Basislinie", "Baseline"),
    "cv_baseline_tip": ("i_p gegen eine Gerade durch den Strom vor dem Hinpeak (Ladestrom + Untergrund), extrapoliert\n"
                        "unter den Peak. Rückpeak: dieselbe Gerade, verschoben um den Sprung des Ladestroms am\n"
                        "Umkehrpunkt (2·C·v); den abklingenden Hinlaufstrom korrigiert Nicholson. Peakpotentiale\n"
                        "bleiben unverändert. Aus: Ströme von null gemessen.",
                        "i_p against a straight line through the current before the forward peak (charging current +\n"
                        "background), extrapolated beneath the peak. Reverse peak: the same line, shifted by the step of\n"
                        "the charging current at the switching potential (2·C·v); the decaying forward current is\n"
                        "corrected by Nicholson. Peak potentials are unchanged. Off: currents measured from zero."),
    "cv_bl_gap_tip": ("Die Basislinie endet mindestens so weit vor dem Hinpeak (Standard 0,15 V: Fuß einer reversiblen\n"
                      "Welle) und in jedem Fall vor dem Anstieg der Welle (2 % der Peakhöhe; breite Wellen, iR-Abfall).\n"
                      "Braucht im Fenster mindestens 30 mV Vorlauf ohne Peak.",
                      "The baseline ends at least this far before the forward peak (default 0.15 V: foot of a reversible\n"
                      "wave) and in any case before the wave rises (2% of the peak height; broad waves, iR drop).\n"
                      "Needs at least 30 mV of peak-free current in the window."),
    "cv_show_bl": ("im Bild zeigen", "show in figure"),
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
    # ---- Spektroelektrochemie ----------------------------------------------
    "tab_sec": ("SEC", "SEC"),
    "sec_data": ("Daten", "Data"),
    "sec_spectra": ("Spektren (BWSpec .txt)", "Spectra (BWSpec .txt)"),
    "sec_n_spectra": ("{n} Spektren", "{n} spectra"),
    "sec_potential": ("Potential (Gamry .DTA)", "Potential (Gamry .DTA)"),
    "sec_offset": ("Zeitversatz", "Time offset"),
    "sec_offset_tip": ("Wird zur Zeit jedes Spektrums addiert, bevor das Potential aus der Gamry-Messung gelesen wird\n"
                       "(z. B. Wartezeit vor dem Scan oder unterschiedliche PC-Uhren). Bei 2 mV/s: 10 s ≙ 20 mV.",
                       "Added to each spectrum's time before the potential is read from the Gamry run\n"
                       "(e.g. waiting time before the scan or different PC clocks). At 2 mV/s: 10 s ≙ 20 mV."),
    "sec_shift": ("E(Fc⁺/Fc) gemessen", "E(Fc⁺/Fc) measured"),
    "sec_shift_tip": ("Lage von Fc⁺/Fc gegen die Referenzelektrode; wird abgezogen (0 = Achse wie gemessen).",
                      "Position of Fc⁺/Fc vs. the reference electrode; subtracted (0 = axis as measured)."),
    "sec_from_cv": ("aus CV-Tab", "from CV tab"),
    "sec_display": ("Darstellung SEC", "SEC display"),
    "sec_mode": ("Ansicht", "View"),
    "sec_mode_spectra": ("Spektrenserie", "Spectral series"),
    "sec_mode_trace": ("A bei λ gegen E", "A at λ vs. E"),
    "sec_range": ("Spektren (Nr.)", "Spectra (no.)"),
    "sec_last_all": ("bis Ende", "to end"),
    "sec_range_info_e": ("{n} Spektren, {a} V → {b} V", "{n} spectra, {a} V → {b} V"),
    "sec_range_info": ("{n} Spektren", "{n} spectra"),
    "sec_highlight": ("Erstes und letztes Spektrum hervorheben (blau/rot), übrige grau",
                      "Highlight first and last spectrum (blue/red), others grey"),
    "sec_gradient": ("Farbverlauf nach Potential", "Colour gradient by potential"),
    "sec_diff": ("Differenzspektren (ΔA gegen erstes Spektrum)", "Difference spectra (ΔA vs. first spectrum)"),
    "sec_baseline": ("Nullpunkt: Mittel 780–820 nm abziehen", "Zero: subtract mean of 780–820 nm"),
    "cv_color_gradient_tip": ("Farbverlauf nach Scanrate ist an: Farbe kommt aus dem Verlauf. Für eigene Farben "
                              "„Farbverlauf“ ausschalten.", "Colour gradient by scan rate is on: the colour comes from "
                              "the gradient. Switch off “gradient” to use your own colours."),
    "sec_mid": ("Zwischenspektren", "Intermediate spectra"),
    "sec_mid_ph_e": ("Potential [V], z. B. −0.45", "potential [V], e.g. −0.45"),
    "sec_mid_ph_n": ("Nr. des Spektrums, z. B. 35", "spectrum no., e.g. 35"),
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
    "sec_bands_ph": ("z. B. 373, 432", "e.g. 373, 432"),
    "sec_trace": ("λ für A gegen E [nm]", "λ for A vs. E [nm]"),
    "sec_trace_ph": ("leer = größte Änderung", "empty = largest change"),
    "sec_fit": ("Scheinbares E½ (Nernst-Fit)", "Apparent E½ (Nernst fit)"),
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
    # ---- EPR ---------------------------------------------------------------
    "tab_epr": ("EPR", "EPR"),
    "off": ("aus", "off"),
    "epr_entries": ("Spektren", "Spectra"),
    "epr_add_exp": ("Messung…", "Measurement…"),
    "epr_add_sim": ("Simulation…", "Simulation…"),
    "epr_add_sim_tip": ("Fertige Simulation als ASCII-Datei laden (z. B. aus EasySpin)",
                        "Load a finished simulation as an ASCII file (e.g. from EasySpin)"),
    "epr_kind_exp": ("Messung", "Measured"),
    "epr_kind_sim": ("Simulation", "Simulation"),
    "epr_none": ("– keine –", "– none –"),
    "epr_dark": ("Dunkelspektrum abziehen", "Subtract dark spectrum"),
    "epr_dark_tip": ("Messung vor dem Bestrahlen (ohne Triplett) als Hintergrund: hell − k·dunkel, auf das Feldraster\n"
                     "der Messung interpoliert. Gleiche Frequenz, Modulation und Leistung nötig (sonst Warnung).",
                     "Measurement before irradiation (no triplet) as background: light − k·dark, interpolated onto the\n"
                     "field grid of the measurement. Same frequency, modulation and power required (warning otherwise)."),
    "epr_dark_mismatch": ("⚠ {name}: Dunkelspektrum mit anderem {what} gemessen.",
                          "⚠ {name}: dark spectrum recorded with different {what}."),
    "epr_fit_to": ("An Messung anpassen", "Scale to measurement"),
    "epr_fit_tip": ("Skalierung der Simulation per kleinsten Quadraten an die gewählte Messung (nach deren Verarbeitung);\n"
                    "Simulation liegt dann auf derselben Stapelebene.",
                    "Least-squares scaling of the simulation to the selected measurement (after its processing);\n"
                    "the simulation is then drawn on the same stacking level."),
    "epr_scale": ("Faktor / Verschiebung", "Factor / shift"),
    "epr_shift": ("ΔB", "ΔB"),
    "epr_params": ("EasySpin-Parameter", "EasySpin parameters"),
    "epr_processing": ("Verarbeitung", "Processing"),
    "epr_bl_order": ("Basislinie (Polynomgrad)", "Baseline (polynomial order)"),
    "epr_bl_edge": ("Ränder", "edges"),
    "epr_bl_regions": ("Basislinie aus Bereichen", "Baseline from ranges"),
    "epr_bl_regions_tip": ("Signalfreie Feldbereiche für die Basislinie (Achseneinheit mT), z. B. '400-430, 560-600'.\n"
                           "Leer: die äußeren Ränder des Sweeps (Prozent links und rechts).",
                           "Signal-free field ranges for the baseline (axis unit mT), e.g. '400-430, 560-600'.\n"
                           "Empty: the outer edges of the sweep (percent left and right)."),
    "epr_regions_ph": ("z. B. 330-340, 480-485 (mT)", "e.g. 330-340, 480-485 (mT)"),
    "epr_exclude": ("Bereiche ausblenden", "Hide ranges"),
    "epr_exclude_tip": ("Feldbereiche, die nicht gezeichnet werden (mT), z. B. das scharfe Radikalsignal bei g ≈ 2.",
                        "Field ranges that are not drawn (mT), e.g. the sharp radical signal at g ≈ 2."),
    "epr_smooth": ("Glätten (gleitender Mittelwert)", "Smoothing (moving average)"),
    "epr_display": ("Darstellung EPR", "EPR display"),
    "epr_xrange": ("B-Bereich", "B range"),
    "epr_unit": ("Feldeinheit", "Field unit"),
    "epr_normalize": ("Normieren (Messung: max |I| = 1, Simulation mit demselben Faktor)",
                      "Normalise (measurement: max |I| = 1, simulation with the same factor)"),
    "epr_labels": ("Labels", "Labels"),
    "epr_labels_ph": ("z. B. Z⁻@122, Y⁺@400, X⁺@450", "e.g. Z⁻@122, Y⁺@400, X⁺@450"),
    "epr_labels_tip": ("Text@Feld (in der Achseneinheit), durch Kommas getrennt – z. B. kanonische Positionen.",
                       "Text@field (in axis units), comma separated – e.g. canonical positions."),
    "epr_show_params": ("D und |E| der Simulation im Bild (aus den EasySpin-Parametern)",
                        "D and |E| of the simulation in the figure (from the EasySpin parameters)"),
    "epr_dark_all": ("Dunkelspektrum für alle Messungen übernehmen", "Use this dark spectrum for all measurements"),
    "epr_dark_all_tip": ("Setzt Dunkelspektrum und Faktor dieses Eintrags bei allen anderen Messungen (z. B. Kinetik-Serie).",
                         "Sets dark spectrum and factor of this entry for all other measurements (e.g. a kinetic series)."),
    "epr_mode_spectra": ("Spektren", "Spectra"),
    "epr_mode_intensity": ("Intensität gegen Zeit/T", "Intensity vs. time/T"),
    "epr_int_window": ("Feldfenster Intensität", "Field window for intensity"),
    "epr_int_window_ph": ("z. B. 445-500 (mT), leer = ganzer Sweep", "e.g. 445-500 (mT), empty = whole sweep"),
    "epr_int_window_tip": ("Bereich, über den integriert bzw. Peak-zu-Peak bestimmt wird (mT). Ausgeblendete Bereiche zählen mit;\n"
                           "für Tripletts das Radikalsignal also über das Fenster ausschließen.",
                           "Range used for integration or peak-to-peak (mT). Hidden ranges are included;\n"
                           "for triplets exclude the radical signal via the window."),
    "epr_int_method": ("Größe", "Quantity"),
    "epr_int_double": ("Doppelintegral", "double integral"),
    "epr_int_pp": ("Peak-zu-Peak", "peak-to-peak"),
    "epr_against": ("gegen", "vs."),
    "epr_x_time": ("Zeit [min]", "time [min]"),
    "epr_x_T": ("Temperatur [K]", "temperature [K]"),
    "epr_x_index": ("Nr.", "no."),
    "epr_curie": ("× T (Curie-Korrektur)", "× T (Curie correction)"),
    "epr_curie_tip": ("Intensität mal Temperatur: bei Curie-Verhalten konstant, solange die Spezies erhalten bleibt\n"
                      "(wie I × T in Zerfallsmessungen).",
                      "Intensity times temperature: constant for Curie behaviour as long as the species persists\n"
                      "(like I × T in decay measurements)."),
    "epr_int_none": ("Keine Werte (Zeit- bzw. Temperaturangaben fehlen?).", "No values (time or temperature missing?)."),
    "epr_int_info": ("{n} Spektren, {method} (Spektren nach Dunkelspektrum und Basislinie).",
                     "{n} spectra, {method} (spectra after dark spectrum and baseline)."),
    "epr_add_iso": ("S = ½-Simulation", "S = ½ simulation"),
    "epr_add_iso_tip": ("Eigene isotrope S = ½-Simulation anlegen und an eine Messung anpassen (Fit von g, Linienbreite, "
                        "Kopplungen)", "Create an own isotropic S = ½ simulation and fit it to a measurement (g, "
                        "linewidth, couplings)"),
    "epr_kind_iso": ("S = ½ (eigen)", "S = ½ (own)"),
    "epr_iso": ("Isotrope S = ½-Simulation (erste Ordnung)", "Isotropic S = ½ simulation (first order)"),
    "epr_lw": ("ΔB_pp", "ΔB_pp"),
    "epr_lorentz": ("Lorentz-Anteil", "Lorentzian fraction"),
    "epr_fit_lor": ("mitfitten", "fit as well"),
    "epr_nuclei": ("Kerne (Anzahl Isotop a/mT)", "Nuclei (number isotope a/mT)"),
    "epr_nuclei_ph": ("z. B. 2 14N 0.65; 4 1H 0.32", "e.g. 2 14N 0.65; 4 1H 0.32"),
    "epr_nuclei_tip": ("Gruppen äquivalenter Kerne: Anzahl, Isotop (1H, 2H, 13C, 14N, 15N, 19F, 31P, 63Cu, …) oder I=…,\n"
                       "Kopplung a in mT; Gruppen mit ';' trennen. Erste Ordnung, isotrop (Lösung, schnelle Rotation).",
                       "Groups of equivalent nuclei: number, isotope (1H, 2H, 13C, 14N, 15N, 19F, 31P, 63Cu, …) or I=…,\n"
                       "coupling a in mT; separate groups with ';'. First order, isotropic (solution, fast tumbling)."),
    "epr_fit_btn": ("An Messung fitten (g, a, ΔB_pp)", "Fit to measurement (g, a, ΔB_pp)"),
    "epr_iso_need_exp": ("Bitte zuerst eine Messung laden bzw. auswählen.", "Please load or select a measurement first."),
    "epr_iso_need_mw": ("Für die Simulation wird die Mikrowellenfrequenz der Messung gebraucht (fehlt in der Datei).",
                        "The simulation needs the microwave frequency of the measurement (missing in the file)."),
    "epr_calib": ("Feldkalibrierung", "Field calibration"),
    "epr_calib_tip": ("Gefittete S = ½-Simulation einer Referenz (z. B. TEMPO in MeCN, g = 2.0055) wählen: ΔB = B(g_fit) − B(g_lit)\n"
                      "wird von allen anderen Messungen abgezogen; deren Fits liefern dann kalibrierte g-Werte.",
                      "Choose the fitted S = ½ simulation of a reference (e.g. TEMPO in MeCN, g = 2.0055): ΔB = B(g_fit) − B(g_lit)\n"
                      "is subtracted from all other measurements; their fits then give calibrated g values."),
    "epr_calib_info": ("Feldkorrektur ΔB = {dB} mT (Referenz g_fit = {g} → g_lit = {glit}).",
                       "Field correction ΔB = {dB} mT (reference g_fit = {g} → g_lit = {glit})."),
    "epr_show_sum": ("Summe der Komponenten", "Sum of components"),
    "epr_show_residual": ("Rest (Messung − Summe)", "Residual (measured − sum)"),
    "epr_sum": ("Summe", "sum"),
    "epr_residual": ("Rest", "residual"),
    "epr_fractions": ("{name}: Anteile (Doppelintegral) {parts}", "{name}: fractions (double integral) {parts}"),
    "epr_ref_freq": ("Feld auf Frequenz skalieren", "Scale field to frequency"),
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
    "epr_int_center": ("Merkmal bei (Gauß-Fit)", "Feature at (Gaussian fit)"),
    "epr_kin_fit": ("Zerfall fitten (Arrhenius, konstante Heizrate)", "Fit decay (Arrhenius, constant heating rate)"),
    "epr_kin_tip": ("I(T) = exp(−A·∫exp(−E_a/RT)/β dT), erste Ordnung; Heizrate β aus mittlerem T- und Zeitschritt.\n"
                    "Intensität vorher min-max normiert (wie im MATLAB-Skript); nur mit x-Achse Temperatur.\n"
                    "Die gepunkteten Grenzen setzen beide Intervallenden von E_a und ln A ein (wie im Skript) – wegen der\n"
                    "starken Kopplung liegen sie fast auf der Kurve und sind kein Unsicherheitsband der Kurve.",
                    "I(T) = exp(−A·∫exp(−E_a/RT)/β dT), first order; heating rate β from mean T and time step.\n"
                    "Intensity min–max normalised first (like the MATLAB script); only with temperature as x axis.\n"
                    "The dotted limits insert both interval ends of E_a and ln A (as in the script) – because of the strong\n"
                    "coupling they lie almost on the curve and are not an uncertainty band of the curve."),
    "epr_kin_script": ("wie Skript (√|r|)", "as script (√|r|)"),
    "epr_kin_lsq": ("kleinste Quadrate", "least squares"),
    "epr_kin_norm_tip": ("„wie Skript“: lsqnonlin auf √|Modell − Messung| (L1-Norm), Intervall formal aus der Jacobi-Matrix –\n"
                         "reproduziert die bisherigen Zahlen, unterschätzt aber die Unsicherheit stark.\n"
                         "„kleinste Quadrate“: übliche Kovarianz s²·(JᵀJ)⁻¹ mit t-Quantil – belastbareres Intervall.\n"
                         "E_a und ln A sind fast vollständig korreliert (Kompensationseffekt).",
                         "'as script': lsqnonlin on √|model − data| (L1 norm), interval formally from the Jacobian –\n"
                         "reproduces previous numbers but strongly underestimates the uncertainty.\n"
                         "'least squares': standard covariance s²·(JᵀJ)⁻¹ with t quantile – more reliable interval.\n"
                         "E_a and ln A are almost completely correlated (compensation effect)."),
    "epr_kin_data": ("Messung", "data"),
    "epr_kin_fitcurve": ("Fit", "fit"),
    "epr_kin_band": ("95-%-Grenzen", "95 % limits"),
    "epr_kin_result": ("E_a = {Ea} kJ/mol = {kcal} kcal/mol (95 %: {lo}–{hi}), A = {A} s⁻¹, β = {beta} K/min, "
                       "Korrelation E_a/ln A = {corr} [{how}]",
                       "E_a = {Ea} kJ/mol = {kcal} kcal/mol (95 %: {lo}–{hi}), A = {A} s⁻¹, β = {beta} K/min, "
                       "correlation E_a/ln A = {corr} [{how}]"),
    "epr_gauss_edge": ("⚠ {n} Spektren: Gauß-Zentrum am Rand des Messbereichs – dort kein klares Merkmal (Rauschen).",
                       "⚠ {n} spectra: Gaussian centre at the edge of the measured range – no clear feature there (noise)."),
    "epr_kin_need_T": ("Zerfallsfit nur mit x-Achse Temperatur.", "Decay fit only with temperature as x axis."),
    # ---- Farbe der Lösung ---------------------------------------------------
    "color_show": ("Farbe in Lösung anzeigen (Vorhersage)", "Show colour in solution (prediction)"),
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
    "act_check_updates": ("Nach Updates suchen…", "Check for updates…"),
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
    "xr_npd": ("nicht positiv definit (als Kugel aus U_iso gezeichnet): {atoms}",
               "non-positive definite (drawn as sphere from U_iso): {atoms}"),
    "xr_no_symops": ("keine Symmetrieoperationen in der CIF – als P1 gezeigt, Molekül evtl. unvollständig",
                     "no symmetry operations in the CIF – shown as P1, molecule may be incomplete"),
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
    "xr_dis_main": ("nur Hauptteil", "major part only"),
    "xr_dis_all": ("alle Teile (PART)", "all parts (PART)"),
    "xr_dis_minor": ("Nebenteil", "minor part"),
    "xr_show_h": ("H-Atome", "H atoms"),
    "xr_labels": ("Labels", "Labels"),
    "xr_h_labels": ("H-Labels", "H labels"),
    "xr_bond_lw": ("Bindungsdicke", "Bond thickness"),
    "xr_label_size": ("Labelgröße", "Label size"),
    "xr_label_size_std": ("wie Textformat", "as text format"),
    "xr_label_size_tip": ("Schriftgröße der Atomlabels in diesem Tab; ganz links = Größe aus Format → Text",
                          "Font size of the atom labels in this tab; leftmost = size from Format → Text"),
    "xr_frags": ("Fragmente", "Fragments"),
    "xr_frags_tip": ("Getrennte Fragmente (Lösungsmittel, Gegenionen) ein-/ausblenden",
                     "Show/hide separate fragments (solvent, counter-ions)"),
    "xr_main_frag": ("größtes", "largest"),
    "xr_reset_view": ("Ansicht zurücksetzen", "Reset view"),
    "xr_reset_view_tip": ("Drehung, Zoom und Lage der Labels der gewählten Struktur auf den Start.",
                          "Rotation, zoom and label positions of the selected structure back to the start."),
    "xr_reset_display": ("Darstellung auf Standard", "Reset display to defaults"),
    "xr_reset_display_tip": ("Alle Einstellungen der Darstellung auf Standard (Stil, Ellipsoide/Radien, Bindungsdicke,\n"
                             "Labels, Labelgröße, Fehlordnung, H-Atome …) und für die gewählte Struktur Ansicht,\n"
                             "ausgeblendete Atome/Fragmente, Labels je Atom und Drahtmodell. Dateien, Namen, Nummerierung,\n"
                             "ausgewählte Parameter und Exportgröße bleiben. Rückgängig (Strg+Z) holt alles zurück.",
                             "All display settings back to defaults (style, ellipsoids/radii, bond thickness, labels,\n"
                             "label size, disorder, H atoms …) and, for the selected structure, view, hidden atoms/\n"
                             "fragments, labels per atom and wireframe. Files, names, numbering, selected parameters and\n"
                             "export size stay. Undo (Ctrl+Z) brings everything back."),
    "xr_reset_display_done": ("Darstellung auf Standard gesetzt – Rückgängig mit Strg+Z.",
                              "Display reset to defaults – undo with Ctrl+Z."),
    "xr_mouse_hint": ("Ziehen = drehen, rechte Taste = verschieben, Mausrad = Zoom, Klick = Atom wählen "
                      "(2 = Abstand, 3 = Winkel, 4 = Diederwinkel), Doppelklick = Label an/aus, Shift + Rahmen = Labels "
                      "mehrerer Atome an/aus, Labels lassen sich verschieben.",
                      "Drag = rotate, right button = pan, wheel = zoom, click = pick atom "
                      "(2 = distance, 3 = angle, 4 = torsion), double-click = label on/off, Shift + drag a box = labels "
                      "of several atoms on/off; labels can be dragged."),
    "xr_box_labels_off": ("Labels ausblenden ({n} Atome)", "Hide labels ({n} atoms)"),
    "xr_box_labels_on": ("Labels zeigen ({n} Atome)", "Show labels ({n} atoms)"),
    "xr_colors": ("Atomfarben", "Atom colours"),
    "xr_colors_reset": ("Olex2-Standardfarben", "Olex2 default colours"),
    "xr_select": ("Ausgewählte Parameter", "Selected parameters"),
    "dft_measure": ("Messen (Abstand, Winkel, Diederwinkel)", "Measure (distance, angle, dihedral)"),
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
    "xr_tables": ("Tabellen für die SI", "Tables for the SI"),
    "xr_copy_crystal": ("Kristalldaten kopieren", "Copy crystal data"),
    "xr_copy_params": ("Parameter kopieren", "Copy parameters"),
    "xr_excel": ("Excel speichern", "Save Excel"),
    "xr_info": ("{n} Atome in der asymmetrischen Einheit, {m} gezeigt/erzeugt, Raumgruppe {sg}",
                "{n} atoms in the asymmetric unit, {m} shown/generated, space group {sg}"),
    "xr_sym_info": ("Symmetrieerzeugt: {ops}", "Symmetry-generated: {ops}"),
    "xr_parts_info": ("Fehlordnung: PART {parts}", "Disorder: PART {parts}"),
    "xr_no_geom": ("keine _geom_bond-Tabelle – Bindungen aus kovalenten Radien, Abstände ohne esd",
                   "no _geom_bond table – bonds from covalent radii, distances without s.u."),
    "xr_no_torsion": ("keine _geom_torsion-Tabelle (CONF fehlt) – Diederwinkel ohne esd",
                      "no _geom_torsion table (CONF missing) – torsion angles without s.u."),
    "xr_style": ("Stil", "Style"),
    "xr_label_color": ("Labelfarbe", "Label colour"),
    "xr_label_color_black": ("Schwarz", "Black"),
    "xr_label_color_atom": ("Wie das Atom", "Like the atom"),
    "xr_label_color_color": ("Eigene Farbe …", "Custom colour …"),
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
    "xr_atom_shown": ("zeigen", "show"),
    "xr_atom_label": ("Label", "Label"),
    "xr_atoms_tip": ("Einzelne Atome (z. B. H) ausblenden und Labels je Atom an-/abschalten; "
                     "Doppelklick auf ein Atom in der Abbildung schaltet sein Label um, Shift + Rahmen ziehen die Labels "
                     "mehrerer Atome.",
                     "Hide single atoms (e.g. H) and switch labels per atom; "
                     "double-click an atom in the figure to toggle its label, Shift + drag a box for several atoms."),
    "xr_labels_all": ("Alle Labels", "All labels"),
    "xr_labels_none": ("Keine Labels", "No labels"),
    "xr_atoms_reset": ("Standard", "Default"),
    "xr_label_mode": ("Labels für", "Labels for"),
    "xr_lab_all": ("alle Nicht-H-Atome", "all non-H atoms"),
    "xr_lab_hetero": ("nur Heteroatome (ohne C)", "heteroatoms only (no C)"),
    "xr_hide_solv": ("Lösungsmittel ausblenden", "Hide solvent"),
    "xr_hide_ions": ("Gegenionen ausblenden", "Hide counterions"),
    "xr_hide_tip": ("Erkannt über die Summenformel des Fragments (THF, Et₂O, CH₂Cl₂, Toluol …; OTf⁻, BF₄⁻, PF₆⁻, "
                    "BArF⁻ …). Weitere Fragmente einzeln in der Liste abhaken.",
                    "Recognised from the fragment's formula (THF, Et₂O, CH₂Cl₂, toluene …; OTf⁻, BF₄⁻, PF₆⁻, BArF⁻ …). "
                    "Untick other fragments individually in the list."),
    "xr_kind_molecule": ("weiteres Molekül, Z′ > 1", "further molecule, Z′ > 1"),
    "xr_kind_solvent": ("Lösungsmittel", "solvent"),
    "xr_kind_ion": ("Gegenion", "counterion"),
    "xr_atom_wire": ("Draht", "wire"),
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
    "xr_wire_name_ph": ("Bezeichnung für die Bildunterschrift, z. B. Dipp groups",
                        "Name for the caption, e.g. Dipp groups"),
    "xr_caption": ("Bildunterschrift (Vorschlag)", "Caption (suggestion)"),
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
    "xr_truncated": ("Polymer/Netzwerk: Vervollständigung abgebrochen", "polymer/network: growing stopped"),

    # ---- Synthese ----------------------------------------------------------
    "tab_syn": ("Synthese", "Synthesis"),
    "syn_title_grp": ("Überschrift", "Heading"),
    "syn_name_tip": ("Name/Nummer der Verbindung in „Synthesis of …“ (leer = Name unter „Verbindung“)",
                     "Name/number of the compound in “Synthesis of …” (empty = name under “Compound”)"),
    "syn_name_ph": ("z. B. S2", "e.g. S2"),
    "syn_scheme": ("Reaktionsschema (ChemDraw)", "Reaction scheme (ChemDraw)"),
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
    "syn_reagents": ("Reagenzien (Mengen berechnen)", "Reagents (calculate amounts)"),
    "syn_col_name": ("Name", "Name"),
    "syn_col_M": ("M / Formel", "M / formula"),
    "syn_col_role": ("Rolle", "Role"),
    "syn_col_eq": ("eq. / %", "eq. / %"),
    "syn_role_ref": ("Bezug (1.0 eq.)", "reference (1.0 eq.)"),
    "syn_role_reagent": ("Reagenz", "reagent"),
    "syn_role_product": ("Produkt", "product"),
    "syn_role_other": ("sonstiges", "other"),
    "syn_table_tip": ("M als Zahl (g/mol) oder Summenformel; n aus m/M, V·c oder V·ρ/M; eq. bzw. Ausbeute bezogen auf "
                      "die Zeile „Bezug“. Die Namen dienen auch der Prüfung der Vorschrift.",
                      "M as number (g/mol) or formula; n from m/M, V·c or V·ρ/M; eq. or yield relative to the "
                      "“reference” row. The names are also used to check the procedure."),
    "syn_M_bad": ("Molmasse nicht lesbar (Zahl oder Summenformel)", "molar mass not readable (number or formula)"),
    "syn_row_add": ("Zeile +", "Row +"),
    "syn_from_scheme": ("Aus Schema", "From scheme"),
    "syn_from_scheme_tip": ("Edukte (erstes = Bezug), Reagenzien und Lösungsmittel über/unter dem Pfeil und das Produkt "
                            "als Zeilen anlegen; Bedingungen (rt, 1 h …) fallen weg, Namen der Moleküle selbst eintragen.",
                            "Add reactants (first = reference), reagents and solvents above/below the arrow and the "
                            "product as rows; conditions (rt, 1 h …) are skipped, enter the molecule names yourself."),
    "syn_insert": ("Klammer einfügen", "Insert amounts"),
    "syn_insert_tip": ("„(1.03 g, 5.00 mmol, 1.0 eq.)“ der gewählten Zeile an der Schreibmarke einfügen",
                       "Insert “(1.03 g, 5.00 mmol, 1.0 eq.)” of the selected row at the cursor"),
    "syn_no_mass": ("keine Atommasse für {el}", "no atomic mass for {el}"),
    "syn_chk_mass_ok": ("{name}: Masse und mmol passen zu M = {M} g/mol.", "{name}: mass and mmol match M = {M} g/mol."),
    "syn_chk_mass_bad": ("{name}: Masse passt nicht zu mmol (mit M = {M} g/mol wären es {n} mmol).",
                         "{name}: mass does not match mmol (with M = {M} g/mol it would be {n} mmol)."),
    "syn_chk_mass_implied": ("{name}: Masse/mmol ergibt M = {lo}–{hi} g/mol (Molmasse in der Tabelle eintragen zum "
                             "Prüfen).", "{name}: mass/mmol gives M = {lo}–{hi} g/mol (enter the molar mass in the "
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
    "nmr_empty": ("Mnova-SVG hinzufügen oder hineinziehen (in MestReNova: Datei → Speichern unter → SVG).",
                  "Add or drop a Mnova SVG (in MestReNova: File → Save As → SVG)."),
    "nmr_spectra": ("Spektren (SVG/EMF aus MestReNova)", "Spectra (SVG/EMF from MestReNova)"),
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
    "nmr_selected": ("Ausgewähltes Spektrum", "Selected spectrum"),
    "nmr_nuc_from_axis": ("Kern aus der Achsenbeschriftung erkannt.", "Nucleus recognised from the axis label."),
    "nmr_nuc_manual": ("Kern von Hand eingetragen.", "Nucleus entered by hand."),
    "nmr_nuc_missing": ("⚠ Kern nicht in der Achse gefunden – bitte eintragen (z. B. 1H oder 1H/13C).",
                        "⚠ nucleus not found in the axis label – please enter it (e.g. 1H or 1H/13C)."),
    "nmr_temp": ("Temperatur", "Temperature"),
    "nmr_freq": ("Frequenz [MHz]", "Frequency [MHz]"),
    "nmr_freq_ph": ("aus dem Mnova-Text bzw. Bruker", "from the Mnova text or Bruker"),
    "nmr_freq_tip": ("Nur nötig, wenn der Mnova-Text den Kern nicht enthält; 2D: 500/126",
                     "Only needed if the Mnova text lacks the nucleus; 2D: 500/126"),
    "nmr_solvent": ("Lösungsmittel", "Solvent"),
    "nmr_solv_ph": ("aus dem Mnova-Text (z. B. CDCl3)", "from the Mnova text (e.g. CDCl3)"),
    "nmr_bruker": ("Bruker-Ordner …", "Bruker folder …"),
    "nmr_bruker_tip": ("Experimentordner (mit acqus) diesem Spektrum zuordnen: Parameterübersicht; der Ordner kommt ganz in "
                       "die Verbindung (data/nmr/<Art>)",
                       "Assign the experiment folder (with acqus) to this spectrum: parameter overview; the whole folder is "
                       "copied into the compound (data/nmr/<kind>)"),
    "nmr_raw": ("Rohdaten", "Raw data"),
    "nmr_spec_flt": ("Mnova-Spektren", "Mnova spectra"),
    "nmr_emf_bad": ("keine EMF-Datei", "not an EMF file"),
    "nmr_emf_preview": ("{f}\n\nEMF: keine Vorschau in Elucida – das Spektrum geht unverändert nach Word (ohne eingesetzte "
                        "Struktur). Für Vorschau und Struktur das Spektrum als SVG aus Mnova speichern.",
                        "{f}\n\nEMF: no preview in Elucida – the spectrum goes into Word unchanged (without the inserted "
                        "structure). For a preview and the structure, save the spectrum as SVG from Mnova."),
    "nmr_emf_nopeaks": ("Peaklabels lassen sich nur aus SVG lesen – das Spektrum als SVG aus Mnova speichern.",
                        "Peak labels can only be read from SVG – save the spectrum as SVG from Mnova."),
    "nmr_raw_hint": ("TopSpin-Experimente und Mnova-Dokumente werden ganz in die Verbindung übernommen und nach Art "
                     "abgelegt (data/nmr/1H, 13C, HSQC …). Ausgewertet werden weiter die Mnova-SVGs; passt genau ein "
                     "Experiment zu einem Spektrum, wird es zugeordnet (Parameter, Temperatur).",
                     "TopSpin experiments and Mnova documents are copied into the compound as a whole and sorted by kind "
                     "(data/nmr/1H, 13C, HSQC …). The Mnova SVGs are still what is evaluated; if exactly one experiment "
                     "fits a spectrum, it is assigned (parameters, temperature)."),
    "nmr_topspin": ("TopSpin-Daten …", "TopSpin data …"),
    "nmr_topspin_tip": ("Ein Experiment (Ordner mit acqus), einen Datensatz (10, 11, …) oder einen Ordner mit mehreren "
                        "Datensätzen wählen – auch per Ziehen ins Fenster",
                        "Choose an experiment (folder with acqus), a dataset (10, 11, …) or a folder with several "
                        "datasets – also by dragging into the window"),
    "nmr_mnova": ("Mnova-Datei …", "Mnova file …"),
    "nmr_mnova_tip": ("MestReNova-Dokument (.mnova) in die Verbindung übernehmen (data/nmr/mnova); Doppelklick öffnet es",
                      "Copy a MestReNova document (.mnova) into the compound (data/nmr/mnova); double-click opens it"),
    "nmr_raw_remove_tip": ("Eintrag aus der Liste nehmen; die Dateien im Ordner der Verbindung bleiben",
                           "Remove the entry from the list; the files in the compound folder stay"),
    "nmr_raw_open_tip": ("Doppelklick: Ordner bzw. Datei öffnen", "Double-click: open folder or file"),
    "nmr_raw_kind": ("Art", "Kind"),
    "nmr_raw_name": ("Name", "Name"),
    "nmr_raw_pulprog": ("Pulsprogramm", "Pulse program"),
    "nmr_raw_spectrum": ("Spektrum", "Spectrum"),
    "nmr_raw_imported": ("NMR-Rohdaten: {n} Experiment(e) übernommen ({kinds})",
                         "NMR raw data: {n} experiment(s) copied ({kinds})"),
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
    "nmr_text": ("NMR-Zeile (Mnova-Multiplettbericht)", "NMR line (Mnova multiplet report)"),
    "nmr_text_hint": ("Alle Kerne in dieses eine Feld, je Kern eine Zeile (¹H, darunter ¹³C …): in Mnova „Multiplets → "
                      "Copy“ bzw. „Peaks → Copy“ (Journal-Format) und einfügen, für ¹³C & Co. auch „Zeile aus "
                      "Peaklabels“. Zuordnungen in der Tabelle ergänzen: *kursiv*, _{tief}, ^{hoch}.",
                      "All nuclei go into this one field, one line per nucleus (¹H, then ¹³C …): in Mnova use "
                      "“Multiplets → Copy” or “Peaks → Copy” (journal format) and paste, for ¹³C etc. also “Line from "
                      "peak labels”. Add assignments in the table: *italic*, _{sub}, ^{sup}."),
    "nmr_nuc_short": ("Kern", "Nuc."),
    "nmr_mult": ("Mult.", "Mult."),
    "nmr_assign": ("Zuordnung", "Assignment"),
    "nmr_assign_tip": ("Zuordnung je Signal, z. B. ImPy-H oder ImPy-*C*_{q}", "Assignment per signal, e.g. ImPy-H or "
                                                                              "ImPy-*C*_{q}"),
    "nmr_text_empty": ("Noch kein Mnova-Text.", "No Mnova text yet."),
    "nmr_copy": ("NMR-Zeile kopieren", "Copy NMR line"),
    "nmr_struct": ("Struktur", "Structure"),
    "nmr_struct_on": ("einsetzen", "insert"),
    "nmr_struct_tip": ("Struktur als Vektorgrafik ins Spektrum setzen (ersetzt den Schritt in Inkscape). „automatisch“ "
                       "sucht die freie Stelle möglichst weit oben links, ohne Signale, Labels oder Integrale zu "
                       "verdecken; in der Vorschau lässt sie sich mit der Maus verschieben, das Mausrad über der Struktur ändert die Größe (% der Bildbreite).",
                       "Insert the structure as vector graphics into the spectrum (replaces the Inkscape step). "
                       "“automatic” finds the free space nearest the top left without covering signals, labels or "
                       "integrals; it can be dragged in the preview; the mouse wheel over the structure changes its size (% of the figure width)."),
    "nmr_pos_auto": ("automatisch (frei)", "automatic (free space)"),
    "nmr_pos_manual": ("von Hand (gezogen)", "by hand (dragged)"),
    "nmr_pos_tl": ("oben links", "top left"),
    "nmr_pos_tc": ("oben Mitte", "top centre"),
    "nmr_pos_tr": ("oben rechts", "top right"),
    "nmr_struct_pick": ("Andere Struktur …", "Other structure …"),
    "nmr_struct_pick_tip": ("Sonst gilt die Struktur der Verbindung (Werkzeugleiste „Verbindung“)",
                            "Otherwise the structure of the compound is used (toolbar “Compound”)"),
    "nmr_struct_flt": ("Struktur", "Structure"),
    "nmr_struct_from": ("Struktur: {f}", "Structure: {f}"),
    "nmr_struct_none": ("Keine Struktur (unter „Verbindung“ oder hier wählen).",
                        "No structure (choose under “Compound” or here)."),
    "nmr_word": ("Word speichern", "Save Word"),
    "nmr_word_tip": ("Alle Spektren mit Bildunterschrift, zwei je Seite (SI/<Name>_NMR.docx)",
                     "All spectra with captions, two per page (SI/<name>_NMR.docx)"),

    # ---- DFT (xyz) ---------------------------------------------------------
    "tab_dft": ("DFT", "DFT"),
    "dft_structures": ("Geometrien und Rechnungen", "Geometries and calculations"),
    "dft_add": ("xyz/.out/.log hinzufügen …", "Add xyz/.out/.log …"),
    "dft_flt": ("xyz, ORCA/Gaussian-Ausgabe, Cube, Molden", "xyz, ORCA/Gaussian output, cube, Molden"),
    "dft_orbitals": ("Orbitale", "Orbitals"),
    "dft_orb_add": ("Cube/Molden hinzufügen …", "Add cube/Molden …"),
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
                            "Basis-function convention not recognised (orbitals not orthonormal, deviation {err}) – "
                            "file rejected."),
    "dft_orb_molden_ok": ("Molden: Konvention {v}, CᵀSC = 1 bis auf {err}", "Molden: convention {v}, CᵀSC = 1 within {err}"),
    "dft_orb_select": ("Orbital", "Orbital"),
    "dft_orb_select_tip": ("Gezeigtes Orbital. HOMO/LUMO und Energie aus der ORCA/Gaussian-Ausgabe der Geometrie, "
                           "MO-Nummer aus dem Cube bzw. dem Dateinamen (ORCA: name.mo21a.cube).",
                           "Orbital shown. HOMO/LUMO and energy from the ORCA/Gaussian output of the geometry, MO "
                           "number from the cube or the file name (ORCA: name.mo21a.cube)."),
    "dft_orb_none": ("– keins –", "– none –"),
    "dft_orb_iso": ("Isofläche", "Isosurface"),
    "dft_orb_iso_frac": ("Anteil der Dichte", "Density fraction"),
    "dft_orb_iso_abs": ("Isowert", "Isovalue"),
    "dft_orb_iso_tip": ("Wie IboView: die Fläche umschließt diesen Anteil von |ψ|² (Standard 80 %). Alternativ ein "
                        "fester Isowert ±ψ in a.u. (üblich 0.02–0.05).",
                        "As in IboView: the surface encloses this fraction of |ψ|² (default 80%). Alternatively a "
                        "fixed isovalue ±ψ in a.u. (typically 0.02–0.05)."),
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
                     "normalised); the density fraction is then wrong. Use a larger grid or a fixed isovalue."),
    "dft_orb_coarse": ("Grobes Gitter ({h} Å): Fläche kantig. orca_plot: Gitterpunkte erhöhen (z. B. 100).",
                       "Coarse grid ({h} Å): surface looks faceted. orca_plot: increase the grid points (e.g. 100)."),
    "dft_orb_new_entry": ("{f} passt nicht zur gewählten Geometrie – neue Geometrie aus dem Cube angelegt.",
                          "{f} does not match the selected geometry – new geometry created from the cube."),
    "dft_orb_missing": ("Cube fehlt: {f}", "Cube missing: {f}"),
    "dft_orb_style": ("Mit Orbital werden die Atome wie in IboView gezeichnet.",
                      "With an orbital, atoms are drawn as in IboView."),
    "xr_style_iboview": ("IboView", "IboView"),
    "dft_orb_labels": ("Elementsymbole wie IboView", "Element symbols as in IboView"),
    "dft_orb_labels_tip": ("Buchstaben auf C und Heteroatomen (nicht H), wie IboView sie standardmäßig zeigt.",
                           "Letters on C and heteroatoms (not H), as IboView shows them by default."),
    "dft_si": ("Rechnung für die SI", "Calculation for the SI"),
    "dft_si_hint": ("Für den SI-Block eine ORCA-6- oder Gaussian-Ausgabe (.out/.log) laden; reine xyz-Dateien "
                    "enthalten keine Angaben zur Rechnung.",
                    "Load an ORCA 6 or Gaussian output (.out/.log) for the SI block; plain xyz files contain no "
                    "information about the calculation."),
    "dft_si_with": ("Im SI-Text:", "In the SI text:"),
    "dft_si_zpe": ("ZPE-Spalte", "ZPE column"),
    "dft_method_each": ("Methode je Struktur", "method per structure"),
    "dft_method_top": ("Methode einmal oben", "method once at the top"),
    "dft_method_off": ("ohne Methode", "no method"),
    "dft_method_tip": ("„einmal oben“: Abschnitt „Computational details“ mit jeder verschiedenen Eingabezeile (bei "
                       "mehreren Methoden mit den zugehörigen Strukturen), wie „Sample Input Files“ in einer SI.",
                       "“once at the top”: section “Computational details” with each different input line (with the "
                       "structures concerned if there are several methods), like “Sample Input Files” in an SI."),
    "dft_si_conv": ("Konvergenz", "convergence"),
    "dft_si_freq": ("Frequenzen", "frequencies"),
    "dft_partner_used": ("Koordinaten aus der gleichnamigen xyz (volle Stellenzahl, passt zur Endgeometrie).",
                         "coordinates from the xyz of the same name (full precision, matches the final geometry)."),
    "dft_partner_none": ("Koordinaten aus der Ausgabe (6 Nachkommastellen); die gleichnamige xyz von ORCA daneben "
                         "legen für volle Stellenzahl.",
                         "coordinates from the output (6 decimals); place ORCA's xyz of the same name next to it for "
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
    "dft_w_partly": ("Hinweis: ORCA hat die Optimierung als konvergiert beendet, obwohl nicht alle Kriterien „YES“ "
                     "zeigen (übererfüllter Gradient) – die Tabelle zeigt die Werte unverändert.",
                     "Note: ORCA finished the optimisation as converged although not all criteria show “YES” "
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
                   "trajectory with {n} frames: the last is shown, all are saved in the new order."),
    "dft_comment": ("Kommentar: {c}", "comment: {c}"),
    "dft_fragments": ("{n} getrennte Fragmente", "{n} separate fragments"),
    "dft_renumbered": ("Nummerierung geändert (noch nicht gespeichert, siehe „xyz speichern“).",
                       "numbering changed (not yet saved, see “Save xyz”)."),
    "dft_file_order": ("Nummerierung wie in der Datei.", "numbering as in the file."),
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
    "dft_w_not_converged": ("⚠ Optimierung nicht konvergiert.", "⚠ optimisation not converged."),
    "dft_w_orca_version": ("⚠ ORCA {v}: geprüft ist nur ORCA 6 – Werte im SI-Text mit der Ausgabe vergleichen.",
                           "⚠ ORCA {v}: only ORCA 6 has been verified – compare the SI values with the output."),
    "dft_w_no_opt": ("Keine Optimierung in dieser Ausgabe: Geometrie = Eingabegeometrie.",
                     "No optimisation in this output: geometry = input geometry."),
    "dft_w_no_freq": ("⚠ Frequenzrechnung angefordert, aber keine Frequenzen gefunden.",
                      "⚠ frequency calculation requested but no frequencies found."),
    "dft_w_imag": ("⚠ {n} imaginäre Frequenz(en): {v} cm⁻¹ – kein Minimum; H/G gelten nicht für ein Minimum.",
                   "⚠ {n} imaginary frequenc(y/ies): {v} cm⁻¹ – not a minimum; H/G do not refer to a minimum."),
    "dft_w_no_thermo": ("⚠ Thermochemie (H, G) fehlt.", "⚠ thermochemistry (H, G) missing."),
    "dft_w_solv_cpcm": ("CPCM: angegeben ist der dielektrische Beitrag (in E(el) enthalten), keine Solvatationsenergie "
                        "ΔG_solv – dafür braucht es dieselbe Rechnung in der Gasphase.",
                        "CPCM: the dielectric contribution (contained in E(el)) is given, not a solvation energy "
                        "ΔG_solv – that requires the same calculation in the gas phase."),
    "dft_w_solv_smd": ("SMD: dielektrischer Beitrag und Kavitäts-/Dispersionsterm angegeben; ΔG_solv nur aus dem "
                       "Vergleich mit der Gasphasenrechnung.",
                       "SMD: dielectric contribution and cavity/dispersion term given; ΔG_solv only from comparison "
                       "with the gas-phase calculation."),
    "dft_label_style": ("Label", "Label"),
    "dft_export_labels": ("Labels im Export und in Word", "Labels in export and Word"),
    "dft_export_labels_tip": ("Ohne Häkchen sind Abbildungen in Export und Word-SI ohne Labels (übliche SI-Darstellung); "
                              "die Vorschau zeigt sie weiter zum Nummerieren.",
                              "Unchecked: figures in the export and Word SI have no labels (usual SI style); the "
                              "preview keeps showing them for numbering."),
    "dft_lab_el_num": ("Element + Nummer (C12)", "element + number (C12)"),
    "dft_lab_num": ("nur Nummer (12)", "number only (12)"),
    "dft_lab_ref": ("Labels der Vorlage (CIF)", "labels of the template (CIF)"),
    "dft_lab_ref_tip": ("„Labels der Vorlage“: nach „Wie Vorlage nummerieren“ mit einer CIF die Atomnamen der "
                        "Kristallstruktur (C1, N2, H3A …); Atome ohne Gegenstück behalten Element + Nummer.",
                        "“labels of the template”: after “Number like template” with a CIF, the atom names of the "
                        "crystal structure (C1, N2, H3A …); atoms without a counterpart keep element + number."),
    "dft_ref": ("Wie Vorlage:", "Like template:"),
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
    "dft_zero_based": ("Zählung ab 0 (wie ORCA)", "count from 0 (as ORCA)"),
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
    "pub_info": ("Angaben …", "Details …"),
    "pub_info_missing": ("Noch keine Angaben – Titel, Autoren, DOI unter „Angaben …“",
                         "No details yet – title, authors, DOI under “Details …”"),
    "pub_info_hint": ("Angaben für README.txt des Datensatzes (Aufbau wie die Datensätze der Gruppe auf TUDOdata) und "
                      "die Titelseite der Gesamt-SI. Leere Felder fallen weg.",
                      "Details for the README.txt of the dataset (layout as the group's datasets on TUDOdata) and "
                      "the title page of the complete SI. Empty fields are left out."),
    "pub_f_paper_title": ("Titel des Artikels", "Title of the paper"),
    "pub_ph_paper_title": ("für das Titelblatt der SI; kursiv mit <i>…</i>", "for the SI title page; italics with <i>…</i>"),
    "pub_f_title": ("Titel des Datensatzes", "Title of the dataset"),
    "pub_f_authors": ("Autoren", "Authors"),
    "pub_f_affiliation": ("Adresse", "Affiliation"),
    "pub_f_contact": ("Kontakt (E-Mail)", "Contact (email)"),
    "pub_f_orcid": ("ORCID", "ORCID"),
    "pub_f_doi": ("DOI des Datensatzes", "DOI of the dataset"),
    "pub_f_related": ("Zugehörige Publikation", "Related publication"),
    "pub_f_project_description": ("Projektbeschreibung", "Project description"),
    "pub_f_dataset_description": ("Datensatzbeschreibung", "Dataset description"),
    "pub_f_license": ("Lizenz", "License"),
    "pub_ph_title": ("leer = Electronic supplement to <Titel des Artikels>",
                     "empty = Electronic supplement to <title of the paper>"),
    "pub_ph_authors": ("Vorname Name, Vorname Name and Vorname Name", "First Last, First Last and First Last"),
    "pub_ph_doi": ("z. B. 10.17877/RESOLV-…", "e.g. 10.17877/RESOLV-…"),
    "pub_ph_related": ("Zitat und DOI des Artikels", "Citation and DOI of the article"),
    "pub_ph_project_description": ("z. B. Abstract des Artikels", "e.g. abstract of the article"),
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
    "pub_new_compound_q": ("Name der Verbindung (auch Ordnername), z. B. 6m:",
                           "Name of the compound (also the folder name), e.g. 6m:"),
    "pub_add_project": ("Verbindung hinzufügen …",
                        "Add compound …"),
    "pub_add_project_tip": ("Vorhandene Verbindung aufnehmen (der Ordner bleibt, wo er ist). Verbindungen in Unterordnern des "
                            "Projekts werden automatisch aufgenommen.",
                            "Add an existing compound (the folder stays where it is). Compounds in subfolders of the project are "
                            "added automatically."),
    "pub_datapack": ("Datenpakete (Zip) …", "Data packages (zip) …"),
    "pub_datapack_tip": ("Rohdaten aller Verbindungen wie der Datensatz der Gruppe: je Verbindung ein Zip, "
                         "CompChem.zip, README.txt und Lizenz",
                         "Raw data of all compounds like the group's dataset: one zip per compound, CompChem.zip, "
                         "README.txt and license"),
    "pub_si": ("Gesamt-SI (Word) …", "Complete SI (Word) …"),
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
                  "Organise compounds (e.g. precursors, salts, NHOs): right-click a compound → Group, or drag it into a "
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
                      "vorhandene Daten. Literaturbekannt im Dialog Verbindung setzen.",
                      "Required: ¹H, ¹³C, 2D NMR, HRMS, IR, m.p. (known compounds: only ¹H, ¹³C); grey = further "
                      "data present. Set “known” in the Compound dialog."),
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
    "pub_tpl_group": ("Gruppe (wie die eigene Angewandte-SI; Figure S1:)", "Group (as the own Angewandte SI; Figure S1:)"),
    "pub_tpl_wiley": ("Wiley (Supporting Information, Figure S1.)", "Wiley (Supporting Information, Figure S1.)"),
    "pub_tpl_acs": ("ACS (Supporting Information, Figure S1., Seiten S1 …)",
                    "ACS (Supporting Information, Figure S1., pages S1 …)"),
    "pub_tpl_rsc": ("RSC (Supplementary Information, Fig. S1)", "RSC (Supplementary Information, Fig. S1)"),
    "pub_tpl_nature": ("Nature (Supplementary Figure 1 |)", "Nature (Supplementary Figure 1 |)"),
    "pub_si_toc": ("Titelseite und Inhaltsverzeichnis", "Title page and table of contents"),
    "pub_si_methods": ("Auswertungstexte (Fits) je Verbindung in den Kapiteln",
                       "Data processing texts (fits) per compound in the chapters"),
    "pub_si_write": ("Word-Datei schreiben", "Write Word file"),
    "pub_si_writing": ("Gesamt-SI wird erstellt …", "Creating complete SI …"),
    "pub_si_compound": ("Verbindung {name} …", "Compound {name} …"),
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
}


def set_lang(lang: str):
    global _LANG
    _LANG = "en" if str(lang).lower().startswith("en") else "de"


def get_lang() -> str:
    return _LANG


def T(_key: str, **kw) -> str:
    de, en = TEXTS.get(_key, (_key, _key))
    txt = en if _LANG == "en" else de
    return txt.format(**kw) if kw else txt
