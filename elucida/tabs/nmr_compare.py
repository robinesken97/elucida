"""
elucida/tabs/nmr_compare.py - NMR-Vergleiche (Einzeln · Überlagert · Gestapelt) eigener 1D-Spektren, Achsenbereich aus
der SI-Zeile und Octets NMR-Vorhersage als zusätzliche Spur (nur Ansicht).

Ein Vergleich je Kern: die angehakten eigenen 1D-Spektren (`st["cmp"]["members"]`, uids) desselben Kerns und
Lösungsmittels; die Temperatur darf je Spur abweichen. In die SI kommt jede Gruppe mit mindestens zwei Spuren, wenn der
Modus nicht „Einzeln“ ist und jede Spur Phase und Referenz bestätigt hat. Die Vorhersage steht nie im Zustand, in einer
Abbildung, der SI, Word, PPTX, dem Datenpaket oder der Zwischenablage: nur `NMRView` am Bildschirm zeichnet sie.
"""
from __future__ import annotations

import hashlib
import html as _h
import json
import math
import re
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal

from elucida.app.i18n import T

MODES = ("single", "overlay", "stack")
DEFAULT = dict(mode="single", members=[], offset=100, caption="", heading="NMR Comparisons", labels={})
COLORS = ("#1f5fa8", "#2e7d32", "#6a3d9a", "#b15928", "#008b8b", "#7f7f00")   # weitere Spuren (erste = Spektrumfarbe)
PRED_COLOR = "#d06d00"                     # Vorhersage: eigener Farbton (Magenta glich im dunklen Canvas der aktiven Spur)
PRED_H = 0.6                               # Höhe der Vorhersage-Spur relativ zu einer gemessenen Spur
PRED_NUCLEI = ("1H", "13C", "19F", "31P")  # Octet sagt diese Kerne vorher; ¹⁹F/³¹P mit sichtbarem Hinweis
NOTICE = ("Contains information from nmrshiftdb2 (www.nmrshiftdb.org), which is made available here under the "
          "nmrshiftdb2 Database License.")  # wörtlich wie Octet (spectrumplot.ts NOTICE)
OCTET_SOLVENTS = ("CDCl₃", "DMSO-d₆", "CD₃OD", "D₂O", "C₆D₆", "Acetone-d₆", "CD₃CN")   # wie spectrumplot.ts SOLVENTS
AUTO = {"1H": (0.0, 9.0, 0.5, 1.0), "13C": (0.0, 200.0, 5.0, 10.0)}   # Vorgabe von, bis, Rand, Raster [ppm]
_SUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def state(st):
    """Zustand des Vergleichs im Tab-Zustand (Vorgaben ergänzt; nur uids, keine Pfade)."""
    c = st.setdefault("cmp", {})
    for k, v in DEFAULT.items():
        c.setdefault(k, type(v)() if isinstance(v, (list, dict)) else v)
    return c


# -- Bereich der Achse aus der SI-Zeile ------------------------------------------------------------------------------
def signal_spans(blocks, nuc):
    """Signale der SI-Zeile eines Kerns -> [(lo, hi, Text)] (Multiplettbereich oder einzelne Lage)."""
    from elucida.app.comparison import _shift_range
    out = []
    for b in blocks:
        if b.get("nucleus") != nuc:
            continue
        for s in b.get("signals") or ():
            r = _shift_range(str(s.get("shift") or ""))
            if r is not None:
                out.append((r[0], r[1], str(s["shift"])))
    return out


def auto_xlim(nuc, spans, data=None):
    """„auto“: ¹H 9…0, ¹³C 200…0 ppm, erweitert, bis jedes Signal der SI-Zeile mit Rand (¹H 0.5, ¹³C 5 ppm) innen liegt,
    auf ganze Raster (¹H 1, ¹³C 10 ppm) gerundet; andere Kerne das ganze Spektrum. data = (min, max) der Achse begrenzt.
    -> (links, rechts) absteigend wie die Achse."""
    if nuc not in AUTO:
        return (data[1], data[0]) if data else None
    lo, hi, pad, grid = AUTO[nuc]
    if spans:
        lo = min(lo, math.floor((min(s[0] for s in spans) - pad) / grid) * grid)
        hi = max(hi, math.ceil((max(s[1] for s in spans) + pad) / grid) * grid)
    if data:
        lo, hi = max(lo, data[0]), min(hi, data[1])
    return (float(hi), float(lo))


def outside(spans, rng):
    """Signale der SI-Zeile außerhalb des Bereichs (min, max) -> Texte der Lagen."""
    if rng is None:
        return []
    a, b = min(rng), max(rng)
    return [t for lo, hi, t in spans if lo < a - 1e-9 or hi > b + 1e-9]


# -- Gruppen, Freigabe, Unterschrift -----------------------------------------------------------------------------------
def own_1d(s):
    return s.get("source") == "bruker" and bool(s.get("proc")) and s.get("kind", "1D") == "1D"


def nucleus(s):
    return (s.get("nuclei") or [""])[0]


def solvent_key(s):
    return re.sub(r"[\s\-]", "", (s.get("solvent") or "").translate(_SUB)).lower()


def groups(spectra, cmp_):
    """Angehakte eigene 1D-Spektren je Kern (Reihenfolge der Liste) -> {Kern: [Spektren]}."""
    on = set(cmp_.get("members") or ())
    out = {}
    for s in spectra:
        if s["uid"] in on and own_1d(s):
            out.setdefault(nucleus(s), []).append(s)
    return out


def refusal(specs):
    """Warum eine Gruppe keine Vergleichsabbildung ergibt -> i18n-Schlüssel oder None."""
    if len(specs) < 2:
        return "nmr_cmp_few"
    if len({solvent_key(s) for s in specs}) > 1:
        return "nmr_cmp_solvent"
    if any(not (s.get("proc") or {}).get("phase_ok") or (s.get("proc") or {}).get("ref_status") != "confirmed"
           for s in specs):
        return "nmr_cmp_unconfirmed"
    return None


def label_of(s, specs, cmp_):
    """Beschriftung einer Spur im Bild: eigener Text, sonst die Temperatur (wenn sie sich unterscheidet), sonst der
    Dateiname."""
    own = (cmp_.get("labels") or {}).get(s["uid"])
    if own:
        return own
    temps = {round(float(x.get("temp") or 298)) for x in specs}
    if len(temps) > 1:
        return f"{round(float(s.get('temp') or 298))} K"
    return Path(s.get("file") or s.get("bruker") or "").stem or s["uid"][:6]


def caption_head(specs, blocks):
    """Fester Teil der Unterschrift: „¹H NMR (500 MHz, CDCl₃, 193–298 K)“ als HTML (Temperatur als Bereich)."""
    from elucida.tabs import nmr as NMR
    from elucida.tabs import xray as XRAY
    nuc = nucleus(specs[0])
    freqs = [f for f in dict.fromkeys(NMR.spectrum_freqs(s, blocks).get(nuc) or "" for s in specs) if f]
    solv = next((s.get("solvent") for s in specs if s.get("solvent")), "")
    temps = sorted({round(float(s.get("temp") or 298)) for s in specs})
    tt = f"{temps[0]} K" if len(temps) == 1 else f"{temps[0]}–{temps[-1]} K"
    cond = ", ".join(x for x in ("/".join(freqs) + " MHz" if freqs else "", NMR.solvent_markup(solv), tt) if x)
    return f"{XRAY.to_html(NMR.nuc_markup(nuc) + ' NMR')} ({XRAY.to_html(cond)})"


def caption_html(specs, blocks, name, cmp_):
    """„¹H NMR (500 MHz, CDCl₃, 193–298 K) of <b>X</b>. Freier Satz.“"""
    from elucida.si import lines as SI
    free = (cmp_.get("caption") or "").strip()
    free = " " + SI.chem_html(free if free.endswith((".", "!", "?")) else free + ".") if free else ""
    return f"{caption_head(specs, blocks)} of <b>{_h.escape(name)}</b>.{free}"


# -- Vorhersage (Octet) ----------------------------------------------------------------------------------------------
def octet_solvent(solvent):
    """Lösungsmittel im Namen, den Octets Tabelle kennt (Unicode), sonst None (dann Verschiebungen aller Lösungsmittel)."""
    k = re.sub(r"[\s\-]", "", (solvent or "").translate(_SUB)).lower()
    return next((s for s in OCTET_SOLVENTS if re.sub(r"[\s\-]", "", s.translate(_SUB)).lower() == k), None) if k else None


def table_version():
    """Version der Verschiebungstabelle: Name der gebauten Datei (Vite hängt einen Inhalts-Hash an)."""
    import elucida
    hits = sorted((Path(elucida.ROOT) / "assets" / "octet" / "assets").glob("shifts.bin*"))
    return hits[0].name if hits else ""


def lorentz(lines, lo, hi):
    """Octets Linienform h·w²/((x−δ)²+w²) auf eigenem Raster mit jeder Linienmitte und ihren Flanken (das Messraster träfe
    schmale ¹³C-Linien in zufälliger Höhe) -> (x absteigend, y)."""
    xs = [np.linspace(lo, hi, 40000)]
    for l_ in lines:
        xs.append(l_["ppm"] + l_["w"] * np.concatenate([np.linspace(-40, 40, 161), [0.0]]))
    x = np.unique(np.concatenate(xs))
    y = np.zeros_like(x)
    for l_ in lines:
        y += l_["h"] * l_["w"] ** 2 / ((x - l_["ppm"]) ** 2 + l_["w"] ** 2)
    return x[::-1], y[::-1]


class Predictor(QObject):
    """Octets Vorhersage über einen verborgenen Zeichner: Struktur laden, `window.elucida.predict` starten; die Antwort
    kommt über die Brücke (`Bridge.call` „prediction“ -> `DrawingEditor.predicted`). Zwischenspeicher je Graph der
    Struktur + Kern + Lösungsmittel + Entkopplung + MHz + Tabellenversion; (Datei, Stand) -> Graph merkt sich, welcher
    Graph zu einer Datei gehört, damit ein zweiter Klick ohne Zeichner antwortet."""
    done = Signal(object, object)                       # Anfrage, Ergebnis (dict) oder Fehlertext

    def __init__(self, parent=None, store=None):
        super().__init__(parent)
        store = {} if store is None else store             # Zwischenspeicher überlebt den Neuaufbau des Tabs (Fenster)
        self.cache, self.graphs = store.setdefault("cache", {}), store.setdefault("graphs", {})
        self.editor, self.pending, self._token, self._parent = None, {}, 0, parent

    @staticmethod
    def key_of(graph, req):
        g = hashlib.sha1(json.dumps(graph, sort_keys=True).encode()).hexdigest()
        return (g, req["nucleus"], req["solvent"] or "", bool(req["decouple"]), int(req["mhz"]), table_version())

    def cached(self, req):
        p = Path(req["structure"])
        try:
            g = self.graphs.get((str(p), p.stat().st_mtime_ns))
        except OSError:
            return None
        return self.cache.get((g,) + self.key_of(None, req)[1:]) if g else None

    def request(self, req):
        """req: dict(structure, nucleus, solvent, decouple, mhz). Antwort über `done` (auch sofort aus dem Speicher)."""
        hit = self.cached(req)
        if hit is not None:
            return QTimer.singleShot(0, self, lambda: self.done.emit(req, hit))
        from elucida.app.drawing_editor import DrawingEditor
        if self.editor is None:
            self.editor = DrawingEditor(self._parent, scheme_actions=False)   # nie gezeigt, stirbt mit dem Tab
            self.editor.hide()
            self.editor.resize(900, 600)
            self.editor.predicted.connect(self._answer)
        self._token += 1
        self.pending[self._token] = req
        self._start(self._token, 0)

    def _start(self, token, tries):
        ed, req = self.editor, self.pending.get(token)
        if ed is None or req is None:
            return
        if not ed.ready or ed.path is None or ed.path != Path(req["structure"]).resolve():
            if tries == 0:                                  # nicht bereit: der Zeichner öffnet sie, sobald er es ist
                ed.open_path(req["structure"])
            if tries > 600:                                 # 60 s ohne Zeichner
                self.pending.pop(token, None)
                return self.done.emit(req, T("nmr_pred_failed", e=T("draw_load_error")))
            return QTimer.singleShot(100, self, lambda: self._start(token, tries + 1))
        args = ", ".join(json.dumps(v) for v in (token, req["nucleus"], req["solvent"] or "", req["decouple"],
                                                  int(req["mhz"])))
        ed.page.runJavaScript(f"window.elucida.predict({args})")

    def _answer(self, data):
        req = self.pending.pop(int(data.get("token") or 0), None)
        if req is None:
            return
        if data.get("error") or not isinstance(data.get("value"), dict):
            return self.done.emit(req, T("nmr_pred_failed", e=data.get("error") or "?"))
        v = data["value"]
        try:
            p = Path(req["structure"])
            g = self.key_of(v.get("graph"), req)
            self.graphs[(str(p), p.stat().st_mtime_ns)] = g[0]
            self.cache[g] = v
        except OSError:
            pass
        self.done.emit(req, v)

    def close(self):
        if self.editor is not None:
            self.editor.deleteLater()
            self.editor = None
