---
paths:
  - "elucida/app/**"
  - "elucida/tabs/*.py"
---

# Oberfläche und Navigation: fachliche Regeln (nicht ändern ohne Rückfrage)

- Textformat (Menü Format): global `text_fmt`, je Tab optional eigenes (`tab_fmt[STATE_KEY]`, ε = `epsilon`, gespeichert als
  `text_tabs`); `main.text_format(key)` mischt. Die Karte (`TABS.TextFormatCard`) zeigt nur `TEXT_OPTS` des Tabs. Geschlossener Rahmen
  (`axes_frame`) Standard seit 1.24.
- Navigation (Nutzerwunsch 2.3.1): Pfadleiste in der Werkzeugleiste (Fensterbreite) `Übersicht › Projekt › Verbindung ▾` (Haus als Symbol in Leistengröße, nicht als Zeichen ⌂: Ersatzschrift hob die Grundlinie)
  (`btn_home`/`btn_pub`/`btn_comp`, `_update_crumbs`, Verbindungsmenü `_fill_comp_menu`), `go_home`. Beispiele
  (`demo.is_demo`, Datenordner) nie in den Zuletzt-Listen. Löschen nur in den Papierkorb (`trash_folder`,
  `QFile.moveToTrash`, Nachfrage mit Dateien/Größe), nie endgültig; im Selbsttest nur mit Attrappe.
  Jede Verbindung gehört zu einem Projekt (Nutzerwunsch): Zugehörigkeit = Ordner im Projektordner; neue Verbindung nur
  über `choose_publication` + `new_compound_in_publication`; `move_compound` (verschieben/kopieren/zuordnen,
  `PUB.move_compound_to`/`copy_compound_to`, Kopie ohne `.elucida`, freier Name `unique_dest`); alte Verbindungen ohne
  Projekt beim Öffnen anbieten (`_ask_assign`), nie erzwingen (sonst kein Zugriff auf alte Daten).
  Suche (`search_index`, `WEL.info_matches`): alle Verbindungen der bekannten Projekte + zuletzt geöffnete; Felder Name,
  Ordner, Notiz, Formel, Literatur, Projekt, Gruppe, Laborkürzel (`CODE_RE` über die Projektdatei), Analytik; alle Wörter.
  Gruppen (Nutzerwunsch 2.3.3): `groups` (Reihenfolge) + `group_of` (Eintrag -> Gruppe) im Index; `sync` ordnet nach
  Gruppe, ohne Gruppe am Ende; Gesamt-SI: Unterkapitel (`subsection`, Überschrift 2, TOC-Ebene 2) nur in Synthese und NMR.
  docx: Seitenumbruch als `pageBreakBefore` am nächsten Absatz (`_page_break_before`), pPr in Schema-Reihenfolge (`_ppr`).
- Übersicht (`app/welcome.py`, Nutzerwunsch Redesign 2026-11): Seitenleiste `MainWindow.sidebar` nur auf Startbildschirm und
  Projektseite, nie in den Tabs oder bei offenem Pfad (`_update_crumbs`): Filter `WELCOME_FILTERS` (Alle = `search_index` nach
  Stand, 20 + „Mehr“), Projekte (`PublicationTile`, Ring = vollständig laut `checklist`). Verbindungen als Galerie
  (`CompoundCard`, `Gallery`: Spalten je Breite) oder Liste, beide zeigen, was fehlt; Liste und Projektseite als Matrix
  (`RecentRow`, Spalten `REQUIRED_NEW` + weitere Analytik). Eine Werkzeugleiste: Übersicht/Projekt = Suche, Ansicht, Öffnen,
  Neu (darin die Schnellauswertung); Arbeit = Pfadleiste, Bearbeiten. Projektseite: dieselbe Suche filtert. Computerchemie:
  Pfade als Karten (`PathCard`), Cluster daneben, Pfadliste nur über ☰. Strukturbild nur aus `.elucida/thumb.png`
  (`write_thumb` beim Speichern, wenn die Struktur neuer oder das Bild kleiner als `THUMB_PX` ist) – nie beim Anzeigen
  rendern; bis 20 Projekte.
- Ein Hauptknopf (blau) je Ansicht (Nutzerwunsch Redesign): Verbindung = „Exportieren“, ohne Daten stattdessen der Knopf der
  Anleitung (`EmptyGuide`), Startbildschirm = „Neu“, Projektseite = „Neu“ und „Gesamt-SI“ (Nutzerwunsch), offener Pfad = „Profil exportieren“.
  HRMS und Weitere (`MAIN_SI`, Nutzerwunsch 2026-11-10): Ergebnis geht nur in die SI, dort ist „SI (Word)“ in der Leiste der
  Hauptknopf statt „Exportieren“, **nur wenn Daten da sind** (Abbildung sichtbar oder gespeicherte Daten; `sync_main_button`),
  sonst der Knopf der Anleitung. Hauptknopf gleich groß wie die anderen, Schrift 600 statt 500, nie fett. Tabs
  behalten die Gruppenüberschriften (Nutzerwunsch); Tab-Text hell = dort liegen Daten, gedimmt = leer (`NavTab`, Tab bleibt symmetrisch). Auswahl mit
  Häkchen immer als Tabelle (`STYLE.check_table`/`check_row`: mittig, Datenspalten gleich breit, Nutzerwunsch).
- Navigation: Tabs in vier Gruppen als Leiste **oben** (`nav_bar`, `NAV_GROUPS`), Reiter ausgeblendet. Keine Leisten
  links/rechts: die Vorschau ist in der Breite begrenzt (Seitenleiste −20 % Abbildung, gemessen); Selbsttest verlangt
  bei 1440 × 900 Abbildungsbreite ≥ halbe Fensterbreite. Leere Tabs: Anleitung (`EmptyGuide`, `guide_<tab>_*`), Hinweise
  beim Zeichnen über `add_note` unter der Vorschau.
- Linke Spalte (`FigureTab.arrange`): „Achsen, Größe und Formate“ eingeklappt (Bildunterschrift: Reiter „SI-Text“ rechts) (`STYLE.Fold`,
  Zustand in QSettings `fold/<Tab>/<Name>`, „(geändert)“ über Zustandsschlüssel gegen DEFAULT_STATE); seltene Zeilen
  per `split_group` in eigene Karten (CV Referenzierung, SEC Hervorheben, EPR Intensität, X-Ray Atome); Ergebnisse/
  Tabellen/SI-Text als Reiter neben „Abbildung“ (`to_right`/`move_right`, auch ε) – nie unter die Abbildung (Höhe
  begrenzt sie dann, −28 % gemessen). Jede Ergebnisseite über `result_page`: Karte füllt die Seite, Tabellen/Texte
  wachsen mit, reine Knopfreihen rechts, erster Knopf der letzten Reihe mit Symbol. Protokoll nur
  über Hilfe → Protokoll. Meldungen als Einblendung unten rechts (`_toast`), keine Statusleiste. Neue Karten dort einordnen; Abstände zentral in `STYLE.tidy`.
  Spalte in allen Tabs gleich breit (`STYLE.COLUMN_W`, Trennlinie fest, Nutzerwunsch; breiter nur, wenn sonst
  abgeschnitten): lange Beschriftungen kürzen (Langform in den Tooltip), Symmetrie (Nutzerwunsch Redesign): feste Beschriftungsspalte `LABEL_W`, Inhalt mit und ohne Bildlaufleiste gleich breit, Einzelwerte, Häkchen und Hinweise an denselben Kanten der Wertespalte, Felder in Paaren je halbe Breite, Listen/Textfelder/
  Bereiche im Zwei-Spalten-Raster A | `GAP_W` | B = `WIDE_W` (`_field_edge` in `tidy`: lange Zwischenbeschriftung
  → eigene Zeile, Dateizeilen bis zur Kante; Kästchen siehe „Keine Kästchen in den Spalten“); Text in allen Feldern linksbündig mit
  gleichem Einzug (Nutzerwunsch, nicht zentrieren), Hinweiszeilen als `STYLE.HintLabel` (leer = keine Zeile), Tabellenzellen
  und Kästchen ohne Text mittig (`_CellDelegate`, von `tidy` gesetzt – keine eigenen Delegates ohne Rücksicht darauf), Listenknöpfe
  in zwei Reihen (Hinzufügen / Auswahl). Leere Dateilisten ausgeblendet (`STYLE.hide_when_empty`). Fenster bedienbar
  ab ~960 px (halber 1920er-Bildschirm): Tab-Leiste und Startbildschirm nicht breiter machen.
- Maße des Entwurfs (Nutzerwunsch 2026-11-10 „Maße des Mockups“, waagerecht **und** senkrecht gleichmäßig), nur zentral in
  `STYLE`, keine lokalen Größen oder Stylesheets: Spalte `COLUMN_W` 538 **samt** Bildlaufleiste (`ColumnFit`), Rand um die
  Karten `COL_PAD` 14, Karteninhalt 17 vom Kartenrand (`CARD_PAD`, links = rechts), Beschriftungsspalte `LABEL_W` 128 +
  `FORM_GAP` 8, Rest `VALUE_W`; Felder und Knöpfe in Karten `CONTROL_H` 32, Knöpfe in Leisten (Werkzeugleiste, Fußleiste,
  Seitenkopf) `BAR_H` 34, Werkzeugleiste `TOOLBAR_H` 52. Senkrecht: Titelzone `CARD_TITLE_H` (px, nicht em: em folgte der
  Schrifthöhe), Inhalt 39 unter der Kartenkante, Zeilenabstand `ROW_GAP` 6 in Formularen und zwischen Knopfreihe, Liste und
  Hinweis, unten 13; Dialoge bekommen dieselben Abstände und 32 hohe Felder (`_WheelGuard`, Stylesheet). macOS: die hohe
  NSToolbar wäre 66 px, deshalb bleibt die kompakte (40 px) und `_fit_toolbar` setzt die Leistenknöpfe dort auf 32.
  Hinweis nach einer Feldzeile steht mittig unter der **Wertespalte** (`_field_edge`), nicht unter der ganzen Karte. Pfeile von
  Auswahllisten und Zahlenfeldern auf einer Achse (beide 24 px ab Rahmen). Reine Knopfreihen über Listen in allen Tabs gleich
  (`tidy`: Plus, Pfeile als Symbol, Papierkorb; Textknöpfe teilen die Breite). Beschriftung breiter als `LABEL_W`: kürzen,
  Langform als Eintrag `<key>_long` (Tooltip über `i18n.long_form`); der Selbsttest „design measures“ verlangt: passt oder bricht um.
  Rechte Seite in allen Tabs gleich (`tabs/base.py`): oben `PAGE_TOP` 12, Reiter über `result_tabs` (Segmentstil, links 14),
  Abbildung, Anleitung und Ergebniskarten mit `PAGE_INSET` (14/0/14/14, `CanvasHost(page=True)`, `page_wrap`); Ergebniskarte
  ringsum 17, Tabellen ohne eigene dehnbare Spalte verteilen ihre Spalten über die ganze Breite (Nutzerwunsch), Knöpfe rechts in
  natürlicher Breite. Leiste: Mond/Sonne schaltet das Design, der Canvas-Knopf zeigt mit demselben Symbol seinen Zustand
  (Symbol = aktueller Zustand). Windows/Linux: Marke der Seitenleiste oben links auf Höhe der Werkzeugleiste.
- Rechenweg, Kacheln, SI-Text (Entwurf `Tabs.dc.html`, Nutzerwunsch 2026-11-10; `FigureTab` in `tabs/base.py`, ε-Tab
  ebenso in `main_window.py`): `chain()` → [(Schritt, benutzt)] aus dem Zustand, Karte „Rechenweg“ als erste im Schritt
  Auswertung (`STYLE.ChainRow`, nur Anzeige; nur Tabs, die `chain` überschreiben: ε, Overlay, CV, EPR – neue Auswerteschritte
  dort eintragen). `kpis()` → höchstens zwei (Bezeichnung, Wert) aus den **angezeigten** Ergebnissen (dieselbe Zahl wie
  Tabelle/Bild), als Kacheln rechts in der Reiterzeile (`kpi_corner`); nie eigene Rechnung dafür. Reiter „SI-Text“
  (`_build_si_page`): Bildunterschrift mit ihren `cap_*`-Feldern (die Klappkarte links entfällt) und `methods_text()`, je mit
  „Kopieren“; X-Ray/DFT behalten ihre eigenen Reiter (`SI_PAGE = False`). Alles wird nach jedem Zeichnen über
  `refresh_summary` nachgezogen; Fehler darin dürfen das Zeichnen nie stören.
- Keine Kästchen in den Spalten (Nutzerwunsch 2026-11-10, drei Muster; alles zentral im Vorlauf `STYLE._chips` von `tidy`,
  die Tabs bauen weiter QCheckBox + Feld und behalten Zustandsschlüssel, Signale und Code): (1) Zeilen nur aus Kästchen
  werden **Chips** (`ChipRow`, die QCheckBox-Objekte mit Eigenschaft `chip`, die ganze Pille schaltet) gesammelt in einer
  Zeile „Optionen“ hinter den Feldern der Karte, im Schritt Darstellung „Im Bild“; beschriftete Zeilen (Formate) bleiben
  an ihrem Platz, ebenso Kästchen mit `chip_here` (gehört zum Feld direkt darüber) und Kästchen neben einem Feld (Chip
  darunter). Chip-Text kurz (≤ ~25 Zeichen), Langform als `<key>_long`. (2) Schalter + Wert = **ein Feld mit „aus“**
  (`_make_off_spin`: ☑ + Zahlenfeld in einer Zeile automatisch, getrennte Zeilen über `STYLE.off_spin(cb, spin)`; ☑ +
  Auswahlliste: `_make_off_combo`); Kästchen und Feld des Tabs bleiben verborgen als Träger, der Wert bleibt bei „aus“
  erhalten. (3) ☑ gesamt/auto + von–bis = **Felder zeigen „auto“** (`AutoRange`; Klick = eigene Grenzen, geleertes Feld =
  automatisch). Programmatische Änderungen erreichen die Ersatzfelder auch bei blockierten Signalen (`_watch`). Ausnahme:
  Eigenschaft `nochip`. Kästchen bleiben in Tabellenzeilen und Dialogen. Der Selbsttest verlangt: kein sichtbares Kästchen
  in einer linken Spalte.
- Felder mit „auto“ oder „aus“ (Nutzerwunsch 2026-11-12 „schwer, wieder auf auto zu stellen“, gilt in allen Tabs):
  jedes Zahlenfeld mit Sondertext und jeder `AutoRange`-Bereich trägt `STYLE.SpecialReset` – ein Rücksetz-Symbol im Feld,
  sichtbar nur bei eigenem Wert, ein Klick stellt zurück; ein geleertes Feld gilt beim Verlassen oder mit Enter ebenfalls
  als „auto“/„aus“ (Filter am Zahlenfeld selbst: Fokus und Tasten erreichen sein Textfeld nicht). `tidy` hängt es
  zentral an (`special_resets`, nach `_chips`); nie je Tab nachbauen. Der Selbsttest verlangt: kein Feld mit Sondertext
  ohne das Symbol.
- Schreibweise wie im Satz (Nutzerwunsch 2026-11-11, „wissenschaftlich korrekt“): Größen kursiv, Indizes tief, Einheiten steil
  und mit negativem Exponenten (mg mL⁻¹, mV s⁻¹, g mol⁻¹), nie mit Schrägstrich. Zentral in `STYLE.sci` (`_SCI`: E₁/₂, ΔEₚ,
  λₑₘ, R², m/z, „E [V]“, „g_lit“ …): `tidy` setzt alle Beschriftungen, `HintLabel`/`SciLabel` bei jedem `setText`,
  `RichHeader` die Tabellenköpfe, Rechenweg und Kacheln ebenso. Neue Zeichen dort eintragen, nicht im Text formatieren.
  Chips, Knöpfe und Auswahllisten können kein Rich-Text: dort ohne Unterstrich schreiben („ΔEp“, „E½“). Einheiten der
  Konzentration: Schlüssel bleiben („mg/mL“, „uM“), Anzeige über `core.unit_text`, im Bild `core.unit_math`
  (Mathtext: Arial hat kein hochgestelltes Minus). Stoffnamen und Formeln, die nur angezeigt werden: `SI.chem_name_html`
  (Tabellen über `STYLE.RichDelegate`) bzw. `SI.chem_plain` (tiefgestellte Ziffern, kursive Lokanten N,N-, tert-, n-).
- Tabellen überall gleich (zentral in `tidy`): kein Gitter, feine Linie unter jeder Zeile und Luft in den Zellen
  (`_CellDelegate`), kein Zeilenumbruch in Zellen; Tabellen der linken Spalte nie mit Querrollen (schmale Spalten nach
  Inhalt, eine nimmt den Rest). Kästchen stehen in einer **eigenen schmalen Spalte ohne Kopftext** (`STYLE.check_columns`,
  feste Breite `CHECK_COL_W`), nie mit Text in einer Zelle (Nutzerwunsch 2026-11-11, „genug Platz zum Abwählen“); soll die
  Textspalte ihre Nummer behalten, kommt der Text in eine neue letzte Spalte, die mit `moveSection` gleich hinter dem
  Kästchen angezeigt wird (ε-Ergebnisse: λ = Spalte 7; Rechnungen des Energiediagramms: Name = Spalte 6). Tabellen zeigen
  und wählen nur; Auswahlfelder gehören nicht in Zellen, den gewählten Eintrag ändern Felder unter der Tabelle (Farbfeld
  in der Zelle ist die Ausnahme, wie in CV/EPR/Overlay).
- Einzelfelder füllen immer die ganze Wertespalte `VALUE_W` (Nutzerwunsch 2026-11-10 „Leisten gleich breit“); halbe Breite
  nur für zwei Felder in einer Zeile.
- Keine Popups (Nutzerwunsch 2026-11-11, gilt allgemein): neue Eingaben nie als modaler Dialog, sondern als Tab, Karte
  oder Klappbereich im Raster. Umgesetzt: Tab „Verbindung“ (unten); Konzentrationen als Klappbereich in der Karte Daten des
  ε-Tabs (`sec_conc`, klappt selbst auf, wenn die Probennamen keine Konzentration nennen, gilt sobald eine Einheit gewählt
  ist); Energiediagramm ohne „Große Arbeitsfläche“. Seit 2026-11-11 außerdem: **Schrift und Rahmen** als Klappkarte
  `TABS.TextFormatCard` (letzte Karte im Schritt Darstellung jedes Tabs mit `TEXT_OPTS`, auch ε; Chip „Nur dieser Tab“ =
  `tab_fmt[key]`, sonst `text_fmt`; Änderung → `main.update_text_format`/`set_own_text_format` → `text_format_changed`:
  alle gebauten Tabs neu, ein `push_undo`, `sync_text_cards`; Zahlenfelder nach 350 ms gesammelt; Menü Format zeigt nur
  die Karte, Tabs ohne Karte melden das; „Weitere“ hat `TEXT_OPTS = ()`); **Projektangaben** als dritte Seite „Angaben“
  der Projektseite (`PublicationInfoPage`, Feld gilt beim Verlassen, `edit_info` zeigt die Seite); **SI-Export** als Karte
  „SI-Export (Word)“ im Tab Verbindung (Chips für `SI_PARTS` und Abbildungen je Tab, Schriftart; QSettings `si_parts`/
  `si_figs_off`/`si_font` wie bisher), „SI (Word)“ exportiert direkt (`export_si_dialog`, Teile ohne Daten als Hinweis).
  Dialoge bleiben (bewusst, vorerst): SI-Texte, Vorschriften, Datenpakete, Gesamt-SI, Anmerkung, Orbitalansicht,
  Zeichner, Rückfragen/Meldungen und Dateiauswahl. Vorhandene Dialoge bei Gelegenheit ebenso umbauen, nicht ungefragt.
- Festlegungen vom 2026-11-11 (Durchgang „alles einheitlich, schön und aligned“):
  - Farben frei wählbar je Eintrag (ε: Liste „Messungen“, „Farben zurücksetzen“); die Legende der Konzentrationen steht
    nur auf Wunsch im Bild (`cb_conc_legend`, Standard aus).
  - Texte zum Lesen stehen als Textkarte (ε-Reiter „SI-Text“ aus `STYLE.card`, X-Ray-Bildunterschrift), nicht als loses
    Textfeld; eine Karte mit wenig Inhalt ist nur so hoch wie ihr Inhalt (`result_page`, Eigenschaft `hug`). Text am Anfang
    einer Karte bekommt denselben Abstand zum Titel wie Felder (`_first_text` in `tidy`).
  - Der Rechenweg bricht nie um (`ChainRow._fit`: drei Dichtestufen, Schrittnamen kurz halten).
  - Vorschrift (Synthese) im Blocksatz (`ProcEdit`; „Zeilen verbinden“ entfernt feste Zeilenenden), unabhängig vom
    SI-Export, der immer Blocksatz und geschützte Leerzeichen setzt. Mengentabelle zeigt Masse und Volumen immer
    (`show_amount_columns`), Namen nicht gequetscht und chemisch gesetzt.
  - Tabellen der linken Spalte sind so hoch wie ihre Zeilen (Mengentabelle; Verbinder 3–8 Zeilen, darüber scrollen): nie
    eine halb sichtbare Zeile.
  - Ganze Seiten mit eigener Spalte (Energiediagramm: Eigenschaft `rawpage` + `StepColumn`) folgen demselben Raster wie die
    Tabs: Karten über `make_form`, Knopfreihen in der Wertespalte, mehrere gleichartige Knöpfe (Stilvorlagen) gleich breit
    über die ganze Wertespalte, nichts abgeschnitten.
  - Farbfelder: in Tabellen `color_button(cell=True)`, neben Feldern die normale Größe, neben einem Buchstaben oder kurzen
    Text flach (`color_button(small=True)`, 18 hoch): ein Farbfeld ragt nie über seine Zeile hinaus.
  - Tab-Knöpfe mit wechselndem Text für die angewählte, halbfette Schrift bemessen (`NameTab.sizeHint`), sonst schneidet
    der Tab beim Anwählen ab.
  - Einheiten in Namen und Texten ohne Schrägstrich, auch als Vorgabe („50 mV s-1“, Anzeige „50 mV s⁻¹“).
  - In Abbildungen steht eine Beschriftung nie auf einem Strich oder einer anderen Beschriftung (Energiediagramm:
    `_edge_labels`, siehe `dft.md`).
  - Kursiv/steil gilt **überall** (zweite Runde 2026-11-11): Chips, Knöpfe und Auswahllisten zeichnen Texte mit
    Formelzeichen selbst als Rich-Text (`STYLE._SciPaint`/`_SciItems`, von `tidy` über `sci_widgets` gesetzt; der Text des
    Widgets bleibt reiner Text) – dort also wie überall „E_pa“, „E½“ schreiben und die Regel in `_SCI` ergänzen, nicht
    mehr ausweichen. Steil bleiben Einheiten (G, K, V, M), Elementsymbole („S [%]“, „H-Atome“), Addukte ([M+H]⁺),
    Zustandsnamen in Klammern (E(S)) und beschreibende Indizes. Texte, die nach `tidy` gesetzt werden: `STYLE.SciLabel`
    oder `HintLabel` nehmen (reines `QLabel.setText` setzt nichts). Ausnahmen bisher: Titel von QGroupBox und
    Klappkarten (können kein Rich-Text). Prüfen mit einem Skript, das alle Texte einsammelt (Muster im Selbsttest
    „Typesetting everywhere“).
  - Abbildungen ebenso (`core.fmt_text` → `math_symbols`): Größen kursiv (`E [V]`, `ΔG`, `A/d`, `i$_p$` mit steilem
    Index), griechische Größen kursiv in der Symbolschrift (`_GREEK_QTY`: λ, ε, ν, δ, τ, φ, θ, χ, ρ; Mathtext-Platz `tt`,
    in Labels `sf`), übrige griechische Zeichen (Δ, µ, Ω, σ, π) steil (`cal`); chemische Formeln (Index nur Ziffern)
    bleiben steil. Gespeicherte Achsentexte ändern sich nicht, nur ihr Satz.
  - SI-Texte in den Reitern „SI-Text“/„Bildunterschrift“: `STYLE.SiText` (Anzeige im Blocksatz und gesetzt wie im Druck
    über `si_display`; `text()` und Kopieren liefern den gesetzten Text), über die ganze Kartenbreite.
  - „Kopieren“ steht in **jeder** Karte an derselben Stelle (Nutzerwunsch 2026-11-11, nach zwei Anläufen): kompakt oben
    rechts auf der Titelzeile (`STYLE.card_actions(karte, …, kopieren)`, der Kopieren-Knopf als letzter ganz rechts),
    immer derselbe Knopf (`STYLE.copy_button(tip)`: Symbol + „Kopieren“, die Langform „IR-Zeile kopieren (für Word)“ nur
    im Tooltip). Die Titelzeile gilt nur, wenn die Karte **der** Text ist (SI-Text-Karten, Ergebnisseiten). Ist das
    Textfeld nur ein Teil der Karte (IR, EA, HRMS, NMR mit ihren Eingaben), steht „Kopieren“ in einer Kopfzeile direkt
    über dem Textfeld (`STYLE.text_head("IR-Zeile für die SI", knopf)`): auf der Titelzeile wäre unklar, was kopiert wird
    (Nutzerwunsch). Höhe dieser Knöpfe `HEAD_BTN_H`, im Stylesheet gesetzt (dessen min-/max-height überstimmt
    `setFixedHeight`). Ausnahme: Aktionszeilen ganzer Ergebnisseiten unten rechts (X-Ray-Tabellen).
  - Felder für Formeln, Lösungsmittel und die Texte der Bildunterschrift: `STYLE.ChemEdit` (Ziffern einer Formel schon
    beim Tippen tiefgestellt; `text()` liefert normale Ziffern, der Zustand bleibt wie bisher). Fußleiste mit der
    Bildunterschrift ebenso (`CaptionLabel` über `SI.chem_plain`).
  - Tabellen in Textfeldern (X-Ray: Kristalldaten, Parameter) im Stil der übrigen Tabellen: Zeilenlinien, Luft, **alle
    Zellen mittig**, ganze Breite (`table_view_html`); die Zwischenablage behält die Dreilinien-Tabelle.
  - Chips bleiben in einer Zeile (`ChipRow._fit`: zwei Dichtestufen über die Eigenschaft `tight`, Innenrand 11/7/4);
    passen sie auch eng nicht, gilt die Stufe mit den wenigsten Zeilen. Chip-Texte deshalb kurz halten.
  - Platzhalter und kurze Hinweise einer Ergebnisseite stehen groß und grau in der Mitte der Karte
    (`SciLabel(text, empty)`: einzeiliger Text bis 180 Zeichen), mehrzeilige Ergebnisse oben links.
  - Zwei Tabellen untereinander in einer Karte (X-Ray/DFT „Fragmente“ über „Atome“) haben dieselbe Spaltenfolge und
    -breite: erste Spalte der Name, dann die Kästchen mit Kopftext („zeigen“); hat die untere eine Bildlaufleiste, bleibt
    in der oberen derselbe Streifen frei (leere Spalte, Tabelleneigenschaft `narrowcols`). Die Regel „Kästchen in eigener
    schmaler Spalte ohne Kopftext“ gilt für Tabellen mit **einem** Kästchen je Zeile.
  - Molmasse in Feldern immer mit zwei Nachkommastellen (`.2f`, nie `:g`).
  - Reaktionspfad (Computerchemie): nur Energieprofil/IRC, Abbildungen und 3D-/Orbitalansichten; NICS und
    Multireferenz gehören zur einzelnen Verbindung und stehen dort nicht (`PathWorkspace` nimmt die Reiter heraus).
  - Namen einer Verbindung vergibt nur der Tab „Verbindung“ (kein „Synthese von“ mehr). Ein alter abweichender Name im
    Zustand der Synthese (`st["name"]`) gilt weiter und wird nie still geändert: Hinweis mit „übernehmen“/„verwerfen“
    (`sync_old_name`).
  - Mausrad über Tabellen, Listen und Textfeldern in einer scrollbaren Spalte: das Feld scrollt, an seinem Ende bleibt die
    Spalte stehen (`_WheelGuard._inner_scroll`); Felder ohne eigene Bildlaufleiste lassen die Spalte scrollen.
  - Ergebniskarten mit Aktionen behalten ihre Titelzeile (`card_actions` setzt den Titel selbst, wenn `result_page` ihn
    entfernt hat); ohne Daten steht statt eines leeren Textfelds ein Platzhalter (`SciLabel(text, empty)` in einem Stapel).
  - Dunkler Canvas (`app/canvas_theme.py`): Effekt in Gerätepixeln (sonst helle Zeile am Rand auf HiDPI); beim Drehen
    halbe Auflösung (`moving(widget, an)`, von `XrayMouse` gesetzt), weil die Umrechnung bei voller Auflösung ~45–65 ms
    je Bild kostet (gemessen 3000 × 2200). Die Farbabbildung `dark_pixels` bleibt dieselbe. Umgerechnet wird immer ohne
    vorab eingerechnete Deckkraft (`dark_image`: Format ARGB32; Zeichenflächen `opaque`: Durchsichtiges gilt als weißes
    Papier und die Fläche wird vorher schwarz gefüllt, sonst bleibt am Rand eine helle Zeile stehen) – mit vormultiplizierten Pixeln wurden die durchsichtigen
    Vorschaubilder des Startbildschirms zerstört; die halbe Auflösung behält die Fläche über `devicePixelRatio`.
  - Ergebnis der grafischen Sichtung 2026-11-11 (alle Tabs, Reiter, Start, Projekt, Reaktionspfad):
    Tabellenköpfe ohne senkrechte Trennlinien; leere Tabellen/Listen/Textfelder zeigen einen grauen Platzhalter in der
    Mitte (`STYLE.empty_note(feld, text)`); Auslassungspunkte immer mit Leerzeichen davor („Wählen …“); Beschriftungen
    aller Formulare gedämpft (`tidy` setzt `formlabel`); Fußnote unter den Karten je Tab (`DRAG_HINT`: Tabs ohne Kurven
    `drag_hint_plain`); ohne Abbildung weder Bildunterschrift noch Methodentext (Platzhalter über `SiText(empty=…)`);
    Bildunterschrift-Karten mit Eingabefeldern haben „Kopieren“ in der Kopfzeile über dem Text, reine Textkarten auf der
    Titelzeile. Die Karte „Ausrichten“ (X-Ray/DFT) bleibt mittig Zeile für Zeile (früherer Nutzerwunsch Symmetrie).
    Sichten: `audit_shots.py`-Muster (jede linke Spalte je Schritt in voller Länge, jede rechte Seite je Reiter, mit und
    ohne Daten; im Skript gelöschte Tabs wirklich löschen, sonst laden verwaiste Zeichner und der Lauf hängt).
  - Zeichenpuffer = Zeichenfläche (`CanvasHost.match_buffer`, vor **jedem** Zeichnen): Abbildungen setzen beim
    Neuaufbau ihre Nenngröße, der Agg-Puffer wurde dann eine Pixelzeile kürzer als die Fläche, sobald deren Höhe
    aufgerundet war; matplotlib füllt die Lücke mit der Hintergrundfarbe des Designs – im dunklen Canvas eine helle
    Linie am unteren Rand, die beim Drehen flackerte (nur bei manchen Fenstergrößen; Nachstellen: mehrere Größen,
    danach `render()`).
  - Karten über die ganze Seitenbreite mit Eingabefeldern (Bildunterschrift): Eigenschaft `widefields`, Felder reichen
    bis zum Kartenrand (`_wide_fields`, letzter Schritt von `tidy`). Einzelne Knöpfe und Knopfpaare einer Karte der
    linken Spalte stehen in der Wertespalte bzw. teilen die Kartenbreite, nie lose in natürlicher Breite am linken Rand
    (DFT „Umnummerieren“, „Messen“); Wertegitter (EA) beginnen an der Wertespalte. Ein Tab ohne Fußleistenknöpfe
    (Verbindung) zeigt keine leere Fußleiste.
  - Felder, die zu einem Chip der Zeile „Optionen“ gehören (ε: c und d der Lösungsfarbe), tragen die Eigenschaft
    `below_chips` und bleiben unter der Chip-Zeile (`_chips`/`trailing`). Zahlenfelder mit vielen möglichen Stellen
    zeigen nur die nötigen (`TrimSpin` in `main_window.py`: „100 µM“, nicht „100.0000 µM“).
  - Hinweistexte in Karten sind grau (`HintLabel` + `HINT_CSS`; `HintLabel` allein färbt nicht). Seiten über die ganze
    Breite (Projekt → „Angaben“) begrenzen die Karte auf Lesebreite und setzen `widefields`; `_wide_fields` gilt für
    Text-, Auswahl- und mehrzeilige Felder.
  - Der ε-Tab leert Ergebnistabelle, Kacheln und SI-Texte, sobald es keine Messdaten gibt (`clear_results`): nie die
    Zahlen der zuvor geöffneten Verbindung stehen lassen.
  - `tidy` ruft `guard_fields` ein zweites Mal nach `_chips`: Felder, die erst dort entstehen (OffSpin, OffCombo),
    bekamen sonst weder Einzug noch Mausrad-Schutz (Zahl klebte am linken Rand).
  - Feste Feldhöhe überlebt das Umhängen nicht von selbst: `QStyleSheetStyle` setzt bei jedem `StyleChange` (Einhängen
    in ein anderes Elternteil) `min-height` aus dem Stylesheet neu. `field_heights` markiert Felder mit `fieldh`,
    `_WheelGuard` setzt die Höhe bei `StyleChange` wieder fest (ε-Tab und Vergleich laufen vor dem Einhängen durch
    `tidy` und waren 28–30 statt 32 px hoch). Seiten ohne `tidy` (Cluster-Karte) rufen `field_heights` selbst.
  - Messungslisten (Häkchen · Name · Farbe · …): nach dem Füllen `STYLE.fit_columns(table)` – Nebenspalten nach Inhalt
    mit Luft, freier Platz gleichmäßig auf alle Textspalten, die dehnbare Namensspalte nimmt den Rest (Nutzerwunsch
    2026-11-13: keine Spalte viel zu breit, keine ohne Platz). Nie `resizeColumnToContents` einzeln.
  - Auswahl- und Wertelisten in den Spalten sind immer `QTableWidget` mit Kopf (nie `QListWidget`): X-Ray „Ausgewählte
    Parameter“, „Weitere“ → Abbildungen. Mehrzeilige Textfelder haben per Stylesheet denselben Texteinzug (13 px) wie
    einzeilige. Eine Zeile, die mit ihrem Modus verschwindet, blendet **alle** ihre Teile aus (auch den „–“ eines Paars).
  - Einheitliche Tabellen (Nutzerwunsch 2026-11-13, „alle Tabellen im gesamten Programm“): Ergebnistabellen der
    rechten Seiten sind `STYLE.FitGrid` (`fit()` nach dem Füllen: gleich breite Spalten, solange die breiteste passt;
    sonst nach Inhalt mit gleichmäßig verteiltem Rest; sonst Bildlaufleiste – nie Leerraum rechts, nie abgeschnitten;
    Kästchenspalten bleiben fest). Angaben je Reihe/Paar/Messung nie als Textzeilen unter der Tabelle, sondern als
    zweite Tabelle (`STYLE.summary_grid`/`fill_summary`: CV Scanraten-Analyse, UV-Vis-Kinetik, H-Cell); darunter nur
    Sätze (Referenz) und Warnungen (rot, eigene Zeile). Tabellen in Textvorschauen über `XRAY.table_view_html` (X-Ray,
    DFT „Rechnung für die SI“ mit `si_html(view=True)` inkl. Koordinaten); Zwischenablage und Word behalten die
    SI-Form. Breite 99 % statt 100 % (Qt rechnet sonst 1 px zu viel: Querrollbalken). Verbliebene `QListWidget`
    bekommen in `tidy` Zeilen wie Tabellen (`_ListDelegate`). Offen: EPR-Zerfälle je Temperatur stehen noch als Text.
  - Selbsttest „design measures“ prüft je Tab und für die Projektseite: Einzug der Zahlenfelder, feste Feldhöhe,
    umbrochene Beschriftungen ohne zu breites Wort, Nebenspalten der Messungslisten mit Luft.
  - Die Tab-Leiste liegt in `WEL.NavScroll` (seit 1.1.0, 16 Tabs: sonst 1461 px Mindestbreite, unter Windows 2048 px):
    sie darf schmaler sein als ihr Inhalt, zeigt am abgeschnittenen Rand einen Pfeil, folgt Mausrad/Trackpad und hält den
    gewählten Tab sichtbar (`reveal`). Zeilen der Verbindungsliste melden `ROW_MIN_W`, nie die Breite der Matrix. Der
    Selbsttest verlangt: Fenster nimmt 1440 px an, Leiste bestimmt die Mindestbreite nicht.
  - Kein Tab darf die Mindestbreite des Fensters hochtreiben (alle Tabs teilen einen Stapel, auch verborgene Seiten
    zählen): Bilder in QLabel mit `setMinimumWidth(1)`, nicht gebrauchte Seiten herausnehmen statt verbergen. Sonst wächst
    das Fenster beim Wechsel der Seite („Fensterverhältnisse ändern sich“).
- Tab „Verbindung“ statt Dialog (Nutzerwunsch 2026-11-11 „ich mag Popups nicht“; `tabs/compound.py`, Schlüssel `compound`,
  Zustand = `main.compound`): erster Eintrag der Tab-Leiste in eigener Gruppe, der Knopf (`WEL.NameTab`) trägt Nummer · Summenformel mit
  tiefgestellten Zahlen und wird **nie gekürzt** (Nutzerwunsch): Nummer = die der SI (Feld Name), sonst die
  Laborbuchnummer, sonst der Ordner; ohne Summenformel der Platzhalter „Struktur zeichnen“, gedimmt; der frühere Knopf „Verbindung: …“ der Werkzeugleiste entfällt. Links Karten Bezeichnung · Struktur · Für die SI, rechts der Zeichner wie im Synthese-Tab (ohne
  Reiterzeile, damit beide Zeichner auf derselben Höhe beginnen). Kein OK/Abbrechen: Felder gelten beim Verlassen
  (`apply`), Chips sofort, die Zeichnung speichert sich selbst (`_drawing_saved` → `chemdraw_saved`); jede Änderung ist
  ein Rückgängig-Schritt, ein Feld ohne Änderung keiner. Summenformel/Molmasse folgen der Zeichnung, außer sie weichen von
  dem ab, was die Zeichnung zuletzt ergab (`main._drawn`, von Hand geändert); geleert = wieder der Wert der Zeichnung.
  `edit_compound` („Ändern …“ im ε-Tab) zeigt nur noch den Tab. Neue Verbindungen beginnen dort
  (`create_project`). Kein eigener Export: `MAIN_SI`, „SI (Word)“ ist der Hauptknopf. Neue Angaben zur Verbindung als Feld
  in diesem Tab, nie wieder als Dialog.
- Tab-Rahmen in Schritten (Nutzerwunsch 2026-11-10, Entwurf `Tabs.dc.html` im Mockup; `tabs/base.py`): links
  `StepColumn` verteilt die Karten nach Titel (`STEP_TITLES`) auf bis zu drei Seiten, Standard Daten · Auswertung ·
  Darstellung, je Tab eigene Namen über `STEP_LABELS`; neue Karten dort eintragen, sonst landen sie im ersten Schritt. Die
  Schrittleiste steht immer (auch bei einem Schritt): Karten links und Seite rechts beginnen in jedem Tab auf derselben Höhe.
  Punkt am Schritt = Abweichung vom Standard, Schritt je Tab in QSettings `step/<Tab>`; ein Feld in einem anderen Schritt vor
  dem Fokussieren mit `steps.reveal(widget)` zeigen. Rechts immer `result_tabs` (auch mit nur „Abbildung“). Fußleisten links
  und rechts über `side_bar` gleich hoch (`BAR_MIN_H`), alle Knöpfe darin `BAR_H`: links Zurücksetzen, Vorlagen, „Weiter: …“,
  rechts Bildunterschrift (`CaptionLabel`) und der Hauptknopf. Der Selbsttest misst die Kanten nicht je Tab einzeln neu:
  Maße nur zentral ändern.
- Widgets nie mit `takeAt`/`takeRow` entnehmen und wieder einfügen, ohne das alte Element zu löschen (`STYLE.drop_taken`,
  `STYLE.take_row`, oder `removeWidget`): PySide gibt entnommene Elemente nicht frei, das Widget meldet Größenänderungen dann
  an das alte Element und das neue rechnet mit veralteten Höhen (heightForWidth-Cache; Karten zusammengedrückt, Hinweise über
  Tabellen). Selbsttest „step pages follow …“.
- Listen mit mehreren Einträgen (Overlay, CV, EPR, X-Ray, Weitere): Umsortieren mit Pfeilen **und** durch Ziehen einer Zeile
  (`TABS.RowDrag` + `move_row(von, nach)` des Tabs, Nutzerwunsch 2026-11-10); Qt verschiebt dabei nichts selbst.
- Tab-Reihenfolge wie die SI, davor die Verbindung selbst: Verbindung · Synthese · NMR · IR + EA · HRMS · UV-Vis (ε) · Overlay · UV-Vis-Kinetik · Fluoreszenz · CV · SEC · H-Cell · EPR ·
  X-Ray · DFT · Weitere; offener Tab als Name (`tab`, alte Projekte: Index in der alten Reihenfolge umrechnen).
- „Alles auf Standard“ (`FigureTab.reset_defaults`): alle Schlüssel von DEFAULT_STATE außer `RESET_KEEP` des Tabs, Exportgröße/
  -formate und `cap_*`. In `RESET_KEEP` gehört, was Daten oder Angaben zur Messung sind (Dateien, Referenz/Kalibrierung,
  eingegebene Werte, gewählte Messdaten wie CV `cycle`, SEC `mid`, EPR `ref_freq`; Nutzerwunsch P9 R2) – neue Schlüssel
  dort einordnen. Vorlagen (`save_setup`/`load_setup`) nur ohne diese Schlüssel und ohne `cap_*`. X-Ray/DFT: `XRAY.reset_display` (+ Ansicht/Atom-Auswahl der
  gewählten Struktur; DFT behält Nummerierung, `label_style`, `zero_based`); ε: `MainWindow.reset_defaults` (DEFAULT_GLOB ohne
  Schichtdicke/Export). Immer `push_undo`.
