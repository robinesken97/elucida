---
paths:
  - "elucida/tabs/*.py"
  - "elucida/app/comparison.py"
  - "elucida/app/publication_view.py"
  - "elucida/app/demo.py"
---

# Neue Ansichten, Reiter, Karten und Tabellen: Abnahme vor der Meldung „fertig“

Anlass (Nutzer, 2026-11-13): neu gebaute Ansichten kamen wiederholt mit denselben Fehlern zurück (Einstellungen auf der
Ergebnisseite, winziges Bild, schmale Formulare neben leerer Fläche, unausgewogene Tabellenspalten, Angaben als
Textzeile). Diese Liste gilt für alles Neue und für jede umgebaute Ansicht; Einzelheiten und Helfer stehen in `ui.md`.
Eine Ansicht ist erst fertig, wenn jeder Punkt an einem Bild geprüft ist, nicht am Code.

## Aufbau
- **Links stellen, rechts sehen.** Alle Eingaben, Dateien, Schalter, Farben, Schwellen stehen als Karten in der linken
  Spalte, im passenden Schritt (Daten: laden/entfernen · Auswertung: rechnen/zuordnen · Darstellung: Aussehen; Titel in
  `STEP_TITLES` eintragen, sonst landet die Karte in Schritt 1). Die rechte Seite zeigt nur Ergebnisse: Abbildung,
  Tabelle, SI-Text, je als eigener Reiter (`to_right`), jede Seite über `result_page`. Nie ein Formular auf der rechten Seite.
- **Karten wie alle Karten:** `make_form`, feste Beschriftungsspalte (`STYLE.LABEL_W`), Felder in der Wertespalte in
  voller Breite, Schalter + Wert als ein Feld mit „aus“, Farbfelder und Knopfreihen wie in den Nachbarkarten desselben
  Tabs. Keine schmale Spalte neben leerer Fläche, kein einzelnes zentriertes Kästchen.
- **Keine Pop-ups** für Eingaben; nichts erscheint oder verschwindet sprunghaft beim Wechsel einer Ansicht.

## Abbildung
- Das Bild füllt die Seite; der Inhalt (Molekül, Kurven, Flächen samt Beschriftung) füllt das Bild bis auf einen
  gleichmäßigen Rand. Viel leere Fläche um ein kleines Motiv ist ein Fehler, auch in der SI-Abbildung.
- Beschriftungen berühren sich nicht, liegen nicht auf dem Motiv, Pfeile kreuzen sich nicht; geprüft mit so vielen
  Beschriftungen, wie echte Daten liefern, nicht nur mit dem kleinen Testfall.
- Gibt es eine Vorlage des Nutzers, muss das Bild ihr ähneln (Art der Darstellung, Farben, was beschriftet ist);
  Abweichungen nennen. Alles Sichtbare ist einstellbar (Farben, Schwellen, Größen, an/aus), Vorgabe = Vorlage.
- Hell und dunkel: Zeichenfläche folgt dem Canvas-Theme, in der SI weiß.

## Tabellen und Kennzahlen
- Jede Tabelle über die gemeinsamen Helfer (`STYLE.FitGrid`, `summary_grid`, `fit_columns`, `check_table`), nie ein
  rohes `QTableWidget` mit eigenen Breiten. Spalten ausgewogen: keine viel zu breit neben einer gequetschten, kein
  Leerraum rechts, nichts abgeschnitten, keine dauerhaft leere Spalte (erst zeigen, wenn sie Inhalt hat).
- Angaben je Reihe/Kern/Messung stehen in einer Tabelle, nie als Textzeile darunter. Was man auf einen Blick wissen
  soll (stimmt / stimmt nicht, Anzahl), zusätzlich als Kachel in der Reiterzeile (`kpi_corner`), Abweichung in der
  Warnfarbe.
- Wenig Zeilen: die Tabelle ist so hoch wie ihr Inhalt, der Platz geht ans Bild; kein leerer Streifen.
- Leerer Zustand: ein Satz, was fehlt und wo man es lädt; keine leere Fläche.
- **Größen kursiv** (Nutzer, 2026-11-13: „Größen etc. kursiv, denk daran“): Größensymbole kursiv, Indizes, Einheiten und
  Zahlen aufrecht (*E*el, *H*, *G*, −*TS*, *A*iso, *g*, *J*, *T*, *k*, δ/λ/ε nach `ui.md`), überall gleich: Tabellenköpfe,
  Hinweise, Kacheln, Bildunterschriften, SI-Text, Word. Über den vorhandenen Weg (`RichHeader`, `SciLabel`,
  Zeichentabelle), nie von Hand im Text formatiert; ein Kopf mit kursivem *E* neben aufrechtem H ist ein Fehler.
- Jede neue Ergebnistabelle bekommt mit `name_table` einen Dateinamen und ein Blatt, zeigt „Kopieren“ und steht im Selbsttest-Abschnitt „Tables (decision 170)“ (Datei vorhanden, Mappe = Bildschirm). Angezeigte Zahlen mit Rohwert über `STYLE.num`, Texte der Zellen (Status, Hinweise) für Dateien englisch über `T_en`. Schreibt eine neue Ansicht Kurvenpunkte als CSV, kommt ihre Endung in `TABS.CURVE_CSV` (Blatt „data“ in der Mappe, Selbsttest vergleicht mit der CSV).

## Beispielprojekt
- Jede neue Ansicht hat erfundene Daten im Beispielprojekt (`app/demo.py`), an denen ihr Normalfall und, wo es einen
  gibt, ein Warnfall sichtbar sind. Die erfundenen Daten müssen ein typisches Bild ergeben (nicht zwei Kugeln statt
  einer Fläche). Nichts aus Nutzerdaten.

## Prüfen (selbst, vor der Meldung)
- Bildschirmfotos der ganzen Fensteransicht mit dem Beispielprojekt: jede neue rechte Seite und jede neue Karte je
  Schritt, in DE und EN, hell und dunkel, bei 1200 px und bei 1500 px Fensterbreite. Jedes Bild ansehen und gegen
  diese Liste gehen; zusätzlich einmal mit echten Daten, wenn welche vorliegen (Bilder davon bleiben außerhalb des Repos).
- Geschwister suchen: tritt ein Fehler an einer Stelle auf, alle gleichartigen Stellen im Programm prüfen und zentral
  beheben; wenn sich der Fehler messen lässt, eine Prüfung in den Selbsttest (unter `win32` ohne Schriftmaße).
- In der Abschlussmeldung stehen: welche Ansichten angesehen wurden, was von der Vorlage abweicht, was ungeprüft blieb.
