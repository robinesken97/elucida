---
paths:
  - "elucida/tabs/nmr.py"
  - "elucida/formats/mnova.py"
  - "elucida/formats/topspin.py"
---

# NMR: fachliche Regeln (nicht ändern ohne Rückfrage)

- NMR-Tab: Abbildungen = Mnova-SVG (nicht aus Bruker 1r rechnen: Referenzierung weicht ab). Kern aus der Achse
  („δ ¹H (ppm)“, senkrecht = 2D), sonst von Hand; Reihenfolge ¹H, ¹³C, übrige nach Massenzahl, dann 2D (`sort_key`).
  NMR-Zeile aus dem Mnova-Bericht (alle Kerne in einem Feld), ¹H-Frequenz auf 50 MHz gerundet (501 → 500; nur bis ±5 MHz daneben, 270/360 bleiben, Nutzerwunsch P7); ¹³C auch aus
  den Peaklabels (`svg_peaks`, beschriftetes Lösungsmittelsignal fällt weg). Temperatur 298 K oder aus acqus. Rohdaten
  (Nutzerwunsch 2.1, Reiter „Rohdaten“ neben der Abbildung): TopSpin-Experimente **ganz** (FID/ser, pdata) nach
  `data/nmr/<Art>/<Datensatz>_<Nr.>` (`experiment_kind` aus acqus: 1D = Kern, DEPT/APT, 2D aus dem Pulsprogramm),
  `find_experiments` (Experiment, Datensatz, Ordner mit Datensätzen); genau ein passendes Experiment je Spektrum wird
  zugeordnet (`match_experiment`), sonst von Hand. Mnova-Dokumente nach `data/nmr/mnova` (nur ablegen). EMF-Spektren:
  Kern aus den EMF-Texten (`emf_info`), keine Vorschau, unverändert nach Word (`_media_ext`), ohne Struktur;
  EMF→SVG-Wandler vorgemerkt (Nutzer: später). Struktur als Vektor ins SVG (`compose_structure`), Lage `auto` = freie
  Stelle über Belegungsmaske (`auto_place`, oben links bevorzugt), ziehbar (`manual`), Größe `struct_w` für alle Spektren
  gleich. Unterschrift „¹H NMR (500 MHz, CDCl₃, 298 K) of **X**.“
