[English](epr.en.md) | **Deutsch** · [zurück zur Übersicht](../../README.de.md#anleitungen)

# EPR: Spektren, Simulation und Fit

**Was herauskommt:** CW-EPR-Abbildungen (überlagert oder gestapelt) mit Simulationen, g-Werte und Kopplungen aus einem
eigenen S = ½-Fit, Anteile mehrerer Spezies und – wenn nötig – Intensität gegen Zeit oder Temperatur.

**Was du brauchst:** Bruker-BES3T-Dateien (.dsc + .DTA) oder zweispaltigen Text (z. B. MS400); optional ein
Dunkelspektrum (vor dem Bestrahlen) und Simulationen aus EasySpin als Text.

![EPR-Tab mit Beispieldaten](../screenshots/epr_light_de.png)

## 1. Messungen laden

Im Tab **EPR** über **Messung…** die Dateien hinzufügen. Frequenz, Temperatur, Modulation und Leistung stehen je
Spektrum dabei.

## 2. Verarbeiten

Messung anklicken: **Dunkelspektrum abziehen** (hell − k·dunkel). Unter **Verarbeitung**: Polynom-Basislinie aus den
Rändern oder aus signalfreien Bereichen, Bereiche ausblenden, glätten. Die Reihenfolge ist fest: Dunkelspektrum →
Basislinie → Ausblenden → Glätten → Normieren.

## 3. Simulation

- **Simulation…** lädt eine fertige Simulation aus EasySpin (zweispaltig, B in mT). Sie wird an die gewählte Messung
  angepasst; mehrere Simulationen je Messung werden gemeinsam skaliert (Anteile der Spezies).
- **S = ½-Simulation** legt eine eigene isotrope Simulation an: g, Kerne (z. B. `2 14N 0.65; 4 1H 0.32`, a in mT),
  Linienbreite. **An Messung fitten (g, a, ΔB_pp)** verfeinert die Werte.

## 4. Feldkalibrierung (optional)

Mit einer Referenz wie TEMPO: Referenz mit einer S = ½-Simulation fitten und unter **Feldkalibrierung** mit ihrem
Literatur-g wählen. Die Verschiebung wird von allen anderen Messungen abgezogen, deren Fits dann kalibrierte g-Werte
liefern.

## 5. Intensität und Kinetik (optional)

**Intensität und Kinetik** (eingeklappt) wertet Doppelintegral oder Peak-zu-Peak je Spektrum aus – gegen Zeit oder
Temperatur, optional × T (Curie) und mit Zerfallsfit.

## 6. Export und SI

**Exportieren** schreibt die Abbildung und jede Messung als Text für EasySpin. Die Unterschrift nimmt g, ΔB_pp und
Kopplungen aus deinen S = ½-Fits; Spezies, Lösungsmittel und Konzentration trägst du unter **Bildunterschrift** ein.
