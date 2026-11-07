---
paths:
  - "elucida/tabs/epr.py"
  - "elucida/formats/epr.py"
---

# EPR: fachliche Regeln (nicht ändern ohne Rückfrage)

- EPR: Reihenfolge hell − k·dunkel → Basislinie → Ausblenden → Glätten → Normieren; Simulation mit dem
  Normierungsfaktor ihrer Messung (Verhältnis bleibt). Triplett-Simulation nicht selbst rechnen (EasySpin), nur
  importieren. Projekte kopieren BES3T-Partnerdateien (.dsc/.DTA/.YGF/.xml) mit.
- EPR S = ½: nur isotrop, erste Ordnung; Fit = Grobsuche (Lage, Kopplungsfaktor) + LM; Amplitude linear. Mehrere
  Komponenten je Messung immer gemeinsam linear skalieren. Kalibrierung: ΔB = B(g_fit, ν_ref) − B(g_lit, ν_ref),
  von allen Messungen außer der Referenz abziehen.
- EPR-Zerfall (Nachbau des MATLAB-Skripts der Arbeitsgruppe): Gauß+Gerade, Zentrum nur innerhalb der Messpunkte (sonst beliebige
  Amplitude bei Spektren ohne Signal); Fit-Start per Raster über E_a mit ln A aus T₅₀ (direkter Start scheitert an der
  Korrelation ≈ 1; ohne Halbwert aus dem Stand am Ende). Standard (Nutzerwunsch P6 R1 „akkurat und physikalisch
  sinnvoll“): kleinste Quadrate auf den gemessenen Intensitäten **ohne Min-Max**, Startintensität I0 linear mitgefittet,
  Integral über die Messzeit (beliebiges Temperaturprogramm, auch Haltephasen; Min-Max verschob E_a bei unvollständigem
  Zerfall um bis zu 40 %, 95-%-Intervall traf bei Rauschen nur 23 %), Intervall s²(JᵀJ)⁻¹ mit n − 3 und t-Quantil, Band
  aus der Kovarianz, Kurve an den Messpunkten; „wie Skript“ (Min-Max, konstante Heizrate, √|r|) nur zum Vergleich – hängt
  stark vom Optimierer und von Spektren ohne Signal ab.
