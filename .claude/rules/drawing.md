---
paths:
  - "elucida/app/drawing_*.py"
  - "elucida/app/canvas_theme.py"
  - "elucida/app/reaction_paths.py"
  - "elucida/app/path_composition.py"
  - "elucida/core/chem.py"
  - "elucida/core/images.py"
  - "elucida/formats/cdxml.py"
  - "elucida/formats/ole.py"
  - "elucida/tabs/synthesis.py"
  - "frontend/octet/**"
---

# Strukturen und Zeichnen (ChemDraw, Octet): fachliche Regeln (nicht ändern ohne Rückfrage)

- ChemDraw-Struktur **unverändert** übernehmen: gleichnamige SVG/PDF/PNG neben der CDXML hat Vorrang, aber nur wenn nicht
  älter als die CDXML (`IMG.is_fresh`, sonst veraltet nach Bearbeiten in ChemDraw; gilt auch für .cdx/.emf des Schemas);
  leere ACS-1996-Vorlagen je Verbindung (`PRJ.ensure_templates`), „In ChemDraw bearbeiten“ + `QFileSystemWatcher`
  (`watch_chemdraw`/`chemdraw_saved`, leere Vorlage zählt nicht: `cdxml_has_content`); sonst eigene
  Zeichnung aus den CDXML-Koordinaten (`formats/cdxml.py`, Abkürzungen wie TMS/Dipp bleiben, Pfeile und Texte im Schema);
  RDKit (ACS1996-Modus, keine eigene Bindungslänge) nur, wenn der Zeichner etwas nicht darstellen kann (Hinweise) –
  im Syntheseschema nie (Pfeil/Bedingungen gingen verloren), dort Warnung. Bilder behalten immer ihr Seitenverhältnis
  (gespeichert wird nur die Breite).
- Octet Draw ist Standard (`elucida.octet_enabled()`, `ELUCIDA_OCTET=0` schaltet ab; Upstream-Stand und Änderungen in
  `frontend/octet/UPSTREAM.md`, Details `docs/octet-integration.md`). Kein Anwendungs-Eventfilter (nativer Absturz mit
  WebEngine, PySide 6.12/macOS): Mausrad-Schutz je Feld über `STYLE.guard_fields`. Canvas dunkel = `canvas_theme.dark_pixels`
  (HSL-Helligkeit spiegeln, Farbton bleibt, Weiß = #000000, Nutzerwunsch „im Dunkeln alles erkennen“); nur Anzeige.
  Reaktionspfade (`app/reaction_paths.py`, `path_composition.py`): keine Pop-up-Fenster, Höhe gehört dem Canvas
  (Nutzerwunsch: Aktionen neben den Reitern, Pfadliste über ☰). Neue Zeichenfläche eines Pfads mit Rechendaten: das
  Energieprofil wird von selbst eingesetzt (`CompositionEditor.auto_profile`; nie auf einer Fläche, die es schon gab). Backups: je Speichern Rücksetzkopie, Verlauf höchstens
  alle `BACKUP_GAP_S`, `BACKUP_KEEP` Stände.
- Lage nach dem Öffnen (Nutzerwunsch 2026-11-10, `DrawingEditor.place`): Octet zentriert in der Seitengröße zum Ladezeitpunkt
  (verborgen oder noch nicht ausgelegt = beliebige Stelle). Deshalb nach dem Anzeigen neu setzen: waagerecht mittig, ein
  Reaktionsschema im oberen Drittel (`top_third`, Platz für die Tabelle darunter), sonst mittig; bleibt bis zur ersten Eingabe
  verankert. Komposition des Reaktionspfads zeigt stattdessen alles (`fit_view`). Meldungen des Editors in Tabs und im
  Reaktionspfad als Einblendung (`status_to`, nur Hinweise und Fehler), keine ständige Zeile; im Dialog Verbindung bleibt sie.
