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
