---
paths:
  - "elucida/core/tddft.py"
  - "elucida/core/color.py"
  - "elucida/tabs/base.py"
---

# TD-DFT, Overlay, ESD: fachliche Regeln (nicht ändern ohne Rückfrage)

- TD-DFT: Gauß-Verbreiterung in Energie; Kurve und Sticks teilen **immer einen** Skalierungsfaktor
  (Modi `band` Standard, `max`, `faxis`; `faxis` seit P1: Striche wie `band` auf der linken Achse, f rechts nur als
  zweite Skala `cfg["f_axis"]`, entfällt mit Hinweis bei verschiedenen Maßstäben der Rechnungen). Overlay-y-Größe
  `mode`: `norm` (Standard), `eps`, `abs` (Absorbanz wie gemessen, ohne TD-DFT; Nutzerfeedback „y-Achse immer ε“). Übernahme aus Tabs (F2, „Aus Tabs ▾“):
  ε-Serien **verknüpft** (`link` „eps“, ohne Datei; Messung/c/d/M beim Zeichnen aus dem ε-Tab, `eps_linked`; Messung
  wählbar, automatisch = höchste Konzentration mit Maximum ab 230 nm ≤ Cutoff), TD-DFT = Datei des DFT-Tabs. ORCA 5/6-Zustandslabels („0-1A -> 1-1A“) nach „->“ splitten; SOC-Tabelle.
  Multiplizität aus dem Label („1-3A“ = Triplett), ORCA 4/5 aus dem TRIPLETS-Block, Gaussian aus „Triplet-A“;
  Tripletts (f = 0) nur als Marken, nie in der Gauß-Kurve; mit SOC keine Multiplizität (gemischte Zustände).
  Marken gibt es nur bei Singulett-Referenz („0-1A -> 1-3A“). Offenschalige Referenz (`* xyz 0 3`, UKS, ORCA 6
  „0-3A -> n-3A“; Nutzerwunsch 2026-11-10): alle Zustände spin-erlaubt (`mult` None in `_orca_table`), also Striche mit dem
  gedruckten f und Kurve wie bei Singuletts; die Multiplizität im Label ist dort nur ORCAs Schätzung aus <S²> und macht keinen
  Zustand spin-verboten. Geprüft mit einer echten ORCA-6.1.1-UKS-Triplett-Ausgabe (TDA, 20 Zustände).
  Kombinieren: Übergänge mehrerer Rechnungen (`sources`, je Gewicht) erst zusammenführen, dann verbreitern.
  Lösungsfarbe aus TD-DFT (Overlay-Details, `calc_color`): ε mit FWHM/Verschiebung des Eintrags, A = ε·c·d, Standard
  1 mM, 1 cm (`color_c`/`color_d`); nur qualitativ.
  ORCA-ESD (`.spectrum`, `CALC.read_esd_spectrum`, seit 2.5): Spalte TotalSpectrum, x-Einheit steht nicht in der Datei
  (`%ESD UNIT` aus .inp/.out daneben, sonst Wertebereich; beim Laden bestimmen und im Eintrag speichern, nur die
  .spectrum wird kopiert). Intensitätseinheit unbestätigt → nur normiert (kein ε/Absorbanz). Overlay `kind` „esd“,
  Fluoreszenz `esd_file` (gestrichelt, Verschiebung in der Unterschrift); Verschiebung in eV wie TD-DFT.
- SORCI im Overlay nur aus einer Absorptionstabelle nach „S O R C I (DDCI3-STEP)“ und nur, wenn jede Zeile E·λ = hc
  erfüllt; DDCI2 nie; Tabellen nach dem ersten SORCI-Marker nie als TD-DFT lesen. Layout nur synthetisch geprüft.
- Overlay-Export (Auftrag 2026-11-13, ACS: Anregungsenergien und Oszillatorstärken maschinenlesbar): zusätzlich
  `…_transitions.csv` je TD-DFT-Rechnung (auch jede Quelle eines kombinierten Eintrags): Zustand, E [eV], λ [nm], f,
  Multiplizität wie von `parse_tddft` gelesen, ohne Verschiebung und Gewicht der Abbildung.
- TD-DFT-Tabelle (Paket A 1.2.0, Reiter „Anregungen“, Karte „TD-DFT-Tabelle“, `tdt_*`): Hauptanteile nur, wenn die
  Ausgabe sie enthält (`X.tddft_parts`): ORCA aus den Blöcken „… EXCITED STATES (SINGLETS/TRIPLETS)“ vor der gewählten
  Absorptionstabelle (letzter Lauf), Zuordnung über die Energie (`MATCH_EV`) und Multiplizität, Gewicht wie gedruckt;
  Gaussian 2c² (geschlossen) bzw. c² je Spin (offen, Buchstabe A/B), „<-“ nie. SOC, Spin-Flip, Multireferenz: keine
  Anteile. HOMO/LUMO über `ORB.frontier_name` aus den Besetzungen (ORCA: Orbitalblock vor der Tabelle). Tabelle eine
  Zeile je Anteil, Werte ohne Verschiebung; Filter f/λ-Bereich (λ-Bereich mit Verschiebung = was im Bild steht);
  Tripletts mit f = 0 nur bei `triplets`. SI: `si_table_blocks` (Einzel-SI nach den Abbildungen, Gesamt-SI Kapitel
  Rechnungen vor dem zweispaltigen Teil), Rechenregel als Fußnote ohne Programmnamen; CSV mit allen Anteilen ohne Schwelle.
- NTO-Bilder (Paket B 1.2.0, Karte „Übergangsorbitale (NTO)“, Seite „NTO“, `tabs/nto.py`, Leser `formats/nto.py`):
  nichts wird gerechnet. Paare und Gewichte nur aus dem NTO-Block der ORCA-Ausgabe („NATURAL TRANSITION ORBITALS FOR
  STATE“, „E= … au“, „61a -> 62a : n= …“; geprüft an echten ORCA-6-Ausgaben), zugeordnet über die Energie (eindeutig
  innerhalb `MATCH_EV`, sonst keine Zuordnung; Spin-Flip passt nie). Molden (orca_2mkl aus der .nto): Orbitalnummern
  wie im Block ab 0 je Spin (`NtoView.mo_index`); Besetzungen der Molden-Datei werden nicht als Gewicht benutzt
  (unbelegt). Cubes: genau zwei, Loch = kleinere MO-Nummer, Gewicht aus dem Block oder von Hand (Unterschrift sagt
  nichts dazu, Hinweis in der Karte). Bilder mit dem Orbital-Rendering (IboView-Stil) über `XrayFigure`, gemeinsame
  Ansicht (`default_view`), gemeinsame Ausdehnung und gemeinsamer Ausschnitt; langgestreckt (b > 1.6 h): Loch über
  Teilchen. Schlüssel je Zustand = Dateiname|Variante|Index (nicht der Pfad); Dateien in `project._path_slots`.
  Echte NTO-Molden-/Cube-Dateien und Gaussian-NTO ungeprüft.
- Umbenennung und Abgrenzung (Nutzerentscheid 1.2.0, wörtlich: Tab „UV-Vis-Overlay“ heißt künftig „TD-DFT“, „das
  Verbindungen vergleichen aber aus dem Tab rausnehmen“): sichtbar überall „TD-DFT“ (`tab_overlay`, Handbuch
  „TD-DFT-Tab“/„TD-DFT tab“, `GUIDE_HEAD`, README-Bild `tddft_*`); intern bleibt alles (`ov_state`, STATE_KEY
  „overlay“, `ov_*`-Schlüssel, `data/overlay`, Export `<Verbindung>_Overlay`, `SI_CAPTION`), sonst bräuchte jedes
  Projekt eine Migration. Der Tab vergleicht Messung gegen Rechnung **einer** Verbindung; mehrere Messungen derselben
  Verbindung bleiben (Grenze bei den Funktionen, nicht bei der Zahl der Spektren). Entfernt, weil der Projekt-Vergleich
  es besser macht: nur die Struktur je Spektrum (`structure`/`struct_color` im Eintrag). Statt dessen Zeile „Vergleich“
  im Schritt Daten mit „Öffnen …“ (Projektseite › Vergleich, nur mit Projekt). Alte Zustände: `figure_spec` liest die
  Schlüssel weiter (Bild/SI wie bisher), nichts schreibt sie (`detail_changed`); Hinweis `ov_cmp_old` (`legacy_compare`).
  Stapeln samt y-Achse/Namen an den Kurven/Nulllinien und „Ebene wie darüber“ (`stack_with_prev`) wieder eingebaut
  (Nutzerentscheid 1.2.0, wörtlich „Wieder einbauen so wie du vorgeschlagen hast“): mehrere Spektren derselben Verbindung
  (Lösungsmittel, vor/nach Reaktion, gemessen gegen gerechnet) gestapelt sind sinnvoll; Karte „Stapeln und Achsen“ mit
  den alten Schlüsseln, normale Schlüssel (Vorlagen speichern/setzen sie).

## Prüfstand (aus CLAUDE.md)
- Echte Gaussian-TD-DFT-Ausgabe noch nicht getestet (nur ORCA inkl. SOC); DFT-Tab: Gaussian-Leser mit einer Opt+Freq geprüft.
