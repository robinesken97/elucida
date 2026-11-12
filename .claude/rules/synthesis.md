---
paths:
  - "elucida/tabs/synthesis.py"
  - "elucida/formats/reagent_labels.py"
  - "elucida/formats/ole.py"
---

# Synthese: fachliche Regeln (nicht ändern ohne Rückfrage)

- Synthese-Tab: Schema über `scheme_files` (CDXML + gleichnamige SVG/PDF, .cdx, .emf). Word-OLE nur mit CDX (CDXML
  öffnet Word nicht als ChemDraw-Objekt, vom Nutzer geprüft); Vorschau EMF (Vektor) sonst PNG; OLE-Container eigener
  CFB-Schreiber (`formats/ole.py`). Mengenprüfung mit Rundungsintervallen der angegebenen Stellen (1.03 g = 1.025–1.035 g),
  darüber hinaus nur 0,01 % Spielraum (`TOL`, Atommassen-Tabellen; bis 1.0 waren es 0,5 % bzw. 1 % bei Äquivalenten und
  Ausbeute, Nutzerentscheidung 2026-11-12),
  Bezug = erste Zeile mit 1.0 eq.; eingefügte eq. mit zwei Stellen, eine Null am Ende weg (1.05, 1.1; Nutzerwunsch P7) „Aus Schema“: Rollen aus dem Reaktionsschritt (RDKit `CDX_PRODUCT_ID`/`CDX_REAGENT_ID`),
  Pfeiltexte über `scheme_reagents` (Bedingungen weg, Lösungsmittel-Kürzel → Formel). Vorschau: nur das Schema auf
  Weiß (ausgeblendet ohne Schema), Text im Theme.
  Mengenzellen dürfen eine Einheit tragen („1.03 g“, „150 µL“, „800 mM“; `UNITS`, `split_unit`), ohne Einheit gilt die
  Spalte (alte Projekte); SI wie eingegeben; n eintragbar (`n_mmol`, zählt, wenn n nicht aus m/V berechenbar ist, z. B. Harz ohne M; SI wie eingegeben). ChemDraw-Reagenzientabelle
  (`<stoichiometrygrid>` in der Schema-CDXML, `CDX.stoich_grid`/`grid_row`): Moleküle/Formeln von dort, limitierend =
  Bezug, eingegebene Werte roh, berechnete 3 gültige Stellen, Produkt nur Produktmasse, nur leere Zellen füllen (F1).
  Allgemeine Vorschriften (Nutzerwunsch F1): im Projekt (`procedures`), je Verbindung `syn.gp` (Knopf „GP ▾“); Kürzel
  wie Variablen (Robin): Umbenennen zieht in allen Verbindungen mit (`gp` und „GP A“ im Text, Tausch möglich;
  `PUB.rename_procedures`, offene Verbindung über ihren Zustand + Undo); Gesamt-SI
  einmal direkt vor der ersten Verbindung, die sie benutzt (nie umsortieren), Einzel-SI davor; Gruppen-Unterkapitel
  abschaltbar (`group_headings`). „Substanz übrig“ (`compound.sample`/`sample_no`, wie Characterization): nur intern
  (Startbildschirm ⚗, Suche, Checkliste gelb statt rot), nie SI/Datenpaket.
