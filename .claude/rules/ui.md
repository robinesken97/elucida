---
paths:
  - "elucida/app/**"
  - "elucida/tabs/*.py"
---

# Oberfläche und Navigation: fachliche Regeln (nicht ändern ohne Rückfrage)

- Textformat (Menü Format): global `text_fmt`, je Tab optional eigenes (`tab_fmt[STATE_KEY]`, ε = `epsilon`, gespeichert als
  `text_tabs`); `main.text_format(key)` mischt. Der Dialog zeigt nur `TEXT_OPTS` des Tabs. Geschlossener Rahmen
  (`axes_frame`) Standard seit 1.24.
- Navigation (Nutzerwunsch 2.3.1): Pfadleiste in der Werkzeugleiste (Fensterbreite) `⌂ Übersicht › Projekt › Verbindung ▾`
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
- Startbildschirm (`app/welcome.py`, F5): Projektkacheln (`PublicationTile`, höchstens zwei Reihen à `PUB_TILE_COLS`,
  Fortschritt = vollständig laut `checklist`), darunter Verbindungen (volle Zeilen, Robin) mit Filtern `WELCOME_FILTERS` (Alle =
  `search_index` nach Stand, 20 + „Mehr“); Projektliste aus der Projektdatei (Verbindung, Analytik-Abzeichen, Stand),
  Strukturbild nur aus `.elucida/thumb.png` (`write_thumb` beim Speichern, nur wenn die Struktur neuer ist) – nie beim
  Anzeigen rendern; bis 20 Projekte.
- Navigation: Tabs in vier Gruppen als Leiste **oben** (`nav_bar`, `NAV_GROUPS`), Reiter ausgeblendet. Keine Leisten
  links/rechts: die Vorschau ist in der Breite begrenzt (Seitenleiste −20 % Abbildung, gemessen); Selbsttest verlangt
  bei 1440 × 900 Abbildungsbreite ≥ halbe Fensterbreite. Leere Tabs: Anleitung (`EmptyGuide`, `guide_<tab>_*`), Hinweise
  beim Zeichnen über `add_note` unter der Vorschau.
- Linke Spalte (`FigureTab.arrange`): „Achsen, Größe und Formate“ und Bildunterschrift eingeklappt (`STYLE.Fold`,
  Zustand in QSettings `fold/<Tab>/<Name>`, „(geändert)“ über Zustandsschlüssel gegen DEFAULT_STATE); seltene Zeilen
  per `split_group` in eigene Karten (CV Referenzierung, SEC Hervorheben, EPR Intensität, X-Ray Atome); Ergebnisse/
  Tabellen/SI-Text als Reiter neben „Abbildung“ (`to_right`/`move_right`, auch ε) – nie unter die Abbildung (Höhe
  begrenzt sie dann, −28 % gemessen). Jede Ergebnisseite über `result_page`: Karte füllt die Seite, Tabellen/Texte
  wachsen mit, reine Knopfreihen rechts, erster Knopf der letzten Reihe = Hauptknopf (blau, Symbol). Protokoll nur
  über Hilfe → Protokoll. Meldungen als Einblendung unten rechts (`_toast`), keine Statusleiste. Neue Karten dort einordnen; Abstände zentral in `STYLE.tidy`.
  Spalte in allen Tabs gleich breit (`STYLE.COLUMN_W`, Trennlinie fest, Nutzerwunsch; breiter nur, wenn sonst
  abgeschnitten): lange Beschriftungen kürzen (Langform in den Tooltip), Zahlenfelder `FIELD_W` 120, Listen/Textfelder/
  Bereiche im Zwei-Spalten-Raster A | `GAP_W` | B = `WIDE_W` (`_field_edge` in `tidy`: lange Zwischenbeschriftung
  und „☑ gesamt“ → eigene Zeile, Häkchenreihen zu zweit, Dateizeilen bis zur Kante); Text in allen Feldern linksbündig mit
  gleichem Einzug (Nutzerwunsch, nicht zentrieren), Hinweiszeilen als `STYLE.HintLabel` (leer = keine Zeile), Tabellenzellen
  und Kästchen ohne Text mittig (`_CellDelegate`, von `tidy` gesetzt – keine eigenen Delegates ohne Rücksicht darauf), Listenknöpfe
  in zwei Reihen (Hinzufügen / Auswahl). Leere Dateilisten ausgeblendet (`STYLE.hide_when_empty`). Fenster bedienbar
  ab ~960 px (halber 1920er-Bildschirm): Tab-Leiste und Startbildschirm nicht breiter machen.
- Tab-Reihenfolge wie die SI: Synthese · NMR · IR + EA · HRMS · UV-Vis (ε) · Overlay · Fluoreszenz · CV · SEC · EPR ·
  X-Ray · DFT · Weitere; offener Tab als Name (`tab`, alte Projekte: Index in der alten Reihenfolge umrechnen).
- „Alles auf Standard“ (`FigureTab.reset_defaults`): alle Schlüssel von DEFAULT_STATE außer `RESET_KEEP` des Tabs, Exportgröße/
  -formate und `cap_*`. In `RESET_KEEP` gehört, was Daten oder Angaben zur Messung sind (Dateien, Referenz/Kalibrierung,
  eingegebene Werte, gewählte Messdaten wie CV `cycle`, SEC `mid`, EPR `ref_freq`; Nutzerwunsch P9 R2) – neue Schlüssel
  dort einordnen. Vorlagen (`save_setup`/`load_setup`) nur ohne diese Schlüssel und ohne `cap_*`. X-Ray/DFT: `XRAY.reset_display` (+ Ansicht/Atom-Auswahl der
  gewählten Struktur; DFT behält Nummerierung, `label_style`, `zero_based`); ε: `MainWindow.reset_defaults` (DEFAULT_GLOB ohne
  Schichtdicke/Export). Immer `push_undo`.
