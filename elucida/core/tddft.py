"""
elucida/core/tddft.py - Overlay- und Fluoreszenz-Abbildungen.

- TD-DFT-Ausgaben von ORCA (4–6) und Gaussian lesen, Oszillatorstärken zu ε(λ) verbreitern
- Fotopaar (Tageslicht -> UV) mit Pfeil und Anregungswellenlänge als ein Bildelement
- SimpleFigure: Linienplot mit Legende, Labels, Bildern; Layout/Export/Ziehen wie im Hauptplot
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from elucida.core import uvvis as core
from elucida.formats.calc import read_text

EV_TO_CM = 8065.544          # 1 eV in cm⁻¹
EPS_CONST = 1.3062974e8      # L mol⁻¹ cm⁻² ; ε(ν̃) = C · Σ f/σ · exp(−((ν̃−ν̃ᵢ)/σ)²), σ in cm⁻¹

TDDFT_EXT = {".out", ".log", ".txt"}


# ----------------------------------------------------------------------------
# TD-DFT
# ----------------------------------------------------------------------------
_G_STATE = re.compile(r"Excited State\s+(\d+):\s+(\S+)\s+([-\d.]+)\s+eV\s+([-\d.]+)\s+nm\s+f=\s*([-\d.]+)")
_ORCA_STATE_LABEL = re.compile(r"^\d+-(\d+)(?:\.\d+)?")      # ORCA 5/6: "1-3A" -> Multiplizität 3
_ORCA_TRIPLET_HEAD = "EXCITED STATES (TRIPLETS)"
_ORCA_STATE_LINE = re.compile(r"^STATE\s+\d+:\s+E=\s*[-\d.]+\s+au\s+([-\d.]+)\s+eV")
_ORCA_HEAD = "ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS"
_ORCA_SOC_HEAD = "SOC CORRECTED ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS"
_FLOAT = re.compile(r"-?\d+\.\d+(?:[eE][-+]?\d+)?")


def _orca_table(lines):
    """Zeilen einer ORCA-Absorptionstabelle (ab Titel) -> (E [eV], f, Multiplizität oder None)."""
    dashes, E, f, mult = 0, [], [], []
    for ln in lines[1:]:
        s = ln.strip()
        if s.startswith("---"):
            dashes += 1
            if dashes >= 3:
                break
            continue
        if dashes < 2:
            continue                                   # Kopfzeilen
        if not s:
            break
        if "->" in s:                                  # ORCA 5/6: Zustandsbezeichnungen vor den Zahlen
            ref, _, rest = s.partition("->")
            parts = rest.split(None, 1)
            m = _ORCA_STATE_LABEL.match(parts[0]) if parts else None
            ref = _ORCA_STATE_LABEL.match(ref.strip())
            nums = [float(v) for v in _FLOAT.findall(parts[1])] if len(parts) > 1 else []
            if len(nums) >= 4:                         # eV, cm-1, nm, fosc
                E.append(nums[0])
                f.append(nums[3])
                mv = int(m.group(1)) if m else None
                # offenschalige Referenz ("0-3A -> 1-3A", z. B. UKS-Triplett): alle Zustände spinerlaubt mit dem
                # gedruckten f, kein Triplett im Sinn der Marken -> None. Die Multiplizität im Label schätzt ORCA dort
                # nur aus <S**2> ("RELEVANCE IS LIMITED"), ein abweichendes Label macht den Zustand nicht spinverboten.
                mult.append(None if ref and int(ref.group(1)) != 1 else mv)
            continue
        parts = s.split()
        nums = [float(v) for v in _FLOAT.findall(" ".join(parts[1:]))]   # ORCA 4: Index, cm-1, nm, fosc
        if len(nums) >= 3:
            E.append(nums[0] / EV_TO_CM)
            f.append(nums[2])
            mult.append(None)
    return np.array(E), np.array(f), mult


def _orca_triplets(lines):
    """ORCA 4/5: Triplett-Energien [eV] aus dem Block „EXCITED STATES (TRIPLETS)“ (letzter Block).
    Sie stehen dort nicht in der Absorptionstabelle (f = 0, spinverboten)."""
    heads = [i for i, ln in enumerate(lines) if _ORCA_TRIPLET_HEAD in ln]
    if not heads:
        return []
    out = []
    for ln in lines[heads[-1] + 1:]:
        if "EXCITED STATES" in ln or "SPECTRUM" in ln:
            break
        m = _ORCA_STATE_LINE.match(ln.strip())
        if m:
            out.append(float(m.group(1)))
    return out


def tddft_variants(path) -> list:
    """Welche Spektren enthält die Datei? -> ['soc', 'nosoc'] / ['nosoc']."""
    txt = read_text(path)                          # erkennt UTF-16 (Windows-PowerShell-Umleitung)
    if _G_STATE.search(txt):
        return ["nosoc"]
    spectra = _orca_spectra(txt.splitlines())
    if any(s["method"] for s in spectra):
        return list(dict.fromkeys(s["key"] for s in spectra))
    out = []
    if _ORCA_SOC_HEAD in txt:
        out.append("soc")
    if any(_ORCA_HEAD in ln and "SOC" not in ln for ln in txt.splitlines()):
        out.append("nosoc")
    return out


def _orca_spectra(lines):
    """Scope spectra to ORCA's explicit CASSCF/NEVPT2 property headings."""
    method, spectra, counts = "", [], {}
    for i, ln in enumerate(lines):
        s = ln.strip()
        if "$new_job" in s.lower():                    # eine TD-DFT nach CASSCF ist kein CASSCF-Spektrum
            method = ""
        if "UV, CD spectra and dipole moments" in s:
            method = ("QD-NEVPT2" if s.startswith("QDNEVPT2") else
                      "NEVPT2" if "NEVPT2 diagonal energies" in s else
                      "CASSCF" if s.startswith("CASSCF") else "")
        if _ORCA_HEAD in s:
            variant = "soc" if _ORCA_SOC_HEAD in s else "nosoc"
            stem = f"mr:{method}:{variant}" if method else variant
            occurrence = counts.get(stem, 0)
            counts[stem] = occurrence + 1
            key = f"{stem}:{occurrence}" if method else stem
            spectra.append(dict(key=key, method=method, variant=variant, index=i))
    return spectra


def variant_label(variant):
    from elucida.app.i18n import T
    if variant.startswith("mr:"):
        _, method, spin, occurrence = variant.split(":")
        return f"{method} · {T('soc_' + spin)} · {int(occurrence) + 1}"
    return T("soc_" + variant)


def parse_tddft(path, variant=None) -> dict:
    """-> dict(program, E [eV], f, mult, variant). Gaussian: letzter Zustandsblock.
    ORCA: SOC-korrigiertes Spektrum (variant='soc', Standard falls vorhanden) oder ohne SOC.
    mult: Spinmultiplizität je Zustand (1, 3, …) oder None, wenn unbekannt; mit SOC immer None
    (Zustände sind gemischt und haben dort echte Intensität), ebenso None für Zustände mit der
    Multiplizität einer offenschaligen Referenz (ORCA 6 „0-3A -> 1-3A“: spinerlaubt, keine Marke)."""
    txt = read_text(path)                          # erkennt UTF-16 (Windows-PowerShell-Umleitung)
    ms = list(_G_STATE.finditer(txt))
    if ms:
        starts = [i for i, m in enumerate(ms) if m.group(1) == "1"]
        ms = ms[starts[-1]:] if starts else ms
        E = np.array([float(m.group(3)) for m in ms])
        f = np.array([float(m.group(5)) for m in ms])
        names = {"singlet": 1, "doublet": 2, "triplet": 3, "quartet": 4, "quintet": 5}
        mult = [names.get(m.group(2).split("-")[0].lower()) for m in ms]
        return {"program": "Gaussian", "E": E, "f": f, "mult": mult, "variant": "nosoc"}
    lines = txt.splitlines()
    spectra = _orca_spectra(lines)
    if any(s["method"] for s in spectra):
        if variant and variant.startswith("mr:"):
            chosen = next((s for s in spectra if s["key"] == variant), None)
            if chosen is None:
                raise ValueError("Selected multireference spectrum is no longer present in the output")
        else:
            spin = variant or ("soc" if any(s["variant"] == "soc" for s in spectra) else "nosoc")
            available = [s for s in spectra if s["variant"] == spin]
            chosen = (available or spectra)[-1]  # preserve the result in existing projects
        E, f, mult = _orca_table(lines[chosen["index"]:])
        if chosen["variant"] == "soc":
            mult = [None] * len(E)
        if not len(E):
            raise ValueError("Selected multireference spectrum contains no transitions")
        return dict(program="ORCA", E=E, f=f, mult=mult, variant=chosen["key"], method=chosen["method"])
    if variant and variant.startswith("mr:"):          # Datei ersetzt: nie still eine andere Tabelle liefern
        raise ValueError("Selected multireference spectrum is no longer present in the output")
    soc_idx = [i for i, ln in enumerate(lines) if _ORCA_SOC_HEAD in ln]
    plain_idx = [i for i, ln in enumerate(lines) if _ORCA_HEAD in ln and "SOC" not in ln]
    if variant is None:
        variant = "soc" if soc_idx else "nosoc"
    idx = soc_idx if variant == "soc" else plain_idx
    if not idx:
        idx, variant = (plain_idx, "nosoc") if plain_idx else (soc_idx, "soc")
    if idx:
        E, f, mult = _orca_table(lines[idx[-1]:])
        if variant == "soc" or "SPIN FLIP" in lines[idx[-1]]:
            mult = [None] * len(E)                     # SOC: gemischt; Spin-Flip: Label = Referenz, nicht der Zustand
        elif not any(m == 3 for m in mult):            # ORCA 4/5: Tripletts nur im eigenen Block
            trip = _orca_triplets(lines)
            if trip:
                mult = [m or 1 for m in mult] + [3] * len(trip)
                E, f = np.append(E, trip), np.append(f, np.zeros(len(trip)))
        if len(E):
            return {"program": "ORCA", "E": E, "f": f, "mult": mult, "variant": variant}
    raise ValueError(f"{Path(path).name}: keine TD-DFT-Anregungen gefunden (ORCA/Gaussian)")


def broaden(E_ev, f, fwhm_ev=0.3, shift_ev=0.0, lam=None):
    """Gauß-Verbreiterung in der Energie. -> (λ-Gitter, ε(λ), Stick-λ, Stick-Höhen ε)."""
    if lam is None:
        lam = np.arange(150.0, 1200.01, 0.5)
    sigma_cm = fwhm_ev / (2 * np.sqrt(np.log(2))) * EV_TO_CM
    nu = 1e7 / lam
    nu_i = (np.asarray(E_ev) + shift_ev) * EV_TO_CM
    amp = EPS_CONST * np.asarray(f) / sigma_cm
    eps = (amp[:, None] * np.exp(-((nu[None, :] - nu_i[:, None]) / sigma_cm) ** 2)).sum(0)
    return lam, eps, 1e7 / nu_i, amp


# ----------------------------------------------------------------------------
# Fotopaar mit Pfeil
# ----------------------------------------------------------------------------
def _font(px):
    from matplotlib import font_manager as fm
    for fam in ("Arial", "Liberation Sans", "DejaVu Sans"):
        try:
            path = fm.findfont(fm.FontProperties(family=fam), fallback_to_default=False)
            return ImageFont.truetype(path, px)
        except Exception:
            continue
    return ImageFont.load_default()


def compose_photo_pair(day, uv, text, height=900):
    """Zwei Küvettenfotos nebeneinander, dazwischen Pfeil mit Beschriftung (z. B. '352 nm')."""
    def fit(a):
        im = Image.fromarray(a).convert("RGBA")
        return im.resize((max(1, int(im.width * height / im.height)), height), Image.LANCZOS)
    a, b = fit(day), fit(uv)
    gap = int(0.62 * height)
    W = a.width + gap + b.width
    out = Image.new("RGBA", (W, height), (0, 0, 0, 0))
    out.paste(a, (0, 0), a)
    out.paste(b, (a.width + gap, 0), b)
    d = ImageDraw.Draw(out)
    y = int(height * 0.58)
    x0, x1 = a.width + int(0.12 * gap), a.width + int(0.88 * gap)
    lw = max(2, height // 220)
    head = int(height * 0.035)
    d.line([(x0, y), (x1 - head, y)], fill=(0, 0, 0, 255), width=lw)
    d.polygon([(x1, y), (x1 - head, y - head // 2), (x1 - head, y + head // 2)], fill=(0, 0, 0, 255))
    if text:
        fnt = _font(int(height * 0.075))
        tb = d.textbbox((0, 0), text, font=fnt)
        d.text(((x0 + x1) / 2 - (tb[2] - tb[0]) / 2, y - (tb[3] - tb[1]) - int(height * 0.04)),
               text, font=fnt, fill=(0, 0, 0, 255))
    return np.asarray(out)


# ----------------------------------------------------------------------------
# Abbildung
# ----------------------------------------------------------------------------
class SimpleFigure(core.Figure):
    """Mehrere Kurven + Legende + verankerte Labels + Bilder.
    curves: [dict(x, y, color, label, ls, lw)], sticks: [dict(x, h, color)],
    labels: [dict(key, text, lam)]."""

    def __init__(self, plt, cfg, curves, labels, layout, fig=None, sticks=None, legend=True):
        self.plt, self.cfg, self.layout = plt, cfg, layout or {}
        self.results = []
        self.curves = curves
        self.spectra = [c for c in curves if len(c["x"])]
        if fig is None:
            fig = plt.figure(figsize=cfg["figsize_in"])
        else:
            fig.clear()
            fig.set_size_inches(cfg["figsize_in"], forward=False)
        self.fig = fig
        self.ax = fig.add_axes(cfg["axes_rect"])
        self.axes_items, self.tight_off, self.ann_items = {}, {}, {}
        self._inset_table = None
        self.legend = None
        self.ax2 = None
        self.curve_texts = []
        self._plot(sticks or [])
        self._fit_axes(0.01 if cfg.get("size_cm") else 0.06)
        self._curve_labels()
        if legend and cfg.get("legend", True):
            self._legend()
        self._make_labels(labels or [])
        self._images()
        self._place()

    def _plot(self, sticks):
        cfg, ax = self.cfg, self.ax
        xs = np.concatenate([c["x"] for c in self.curves]) if self.curves else np.array([200.0, 800.0])
        xlim = cfg["xlim"] or (float(np.nanmin(xs)), float(np.nanmax(xs)))
        ylim = cfg["ylim"] or (0, 1.1)
        for c in self.curves:
            cx, cy = core.clip_polyline(c["x"], c["y"], xlim, ylim)
            label = c.get("label")
            if label and str(label).startswith("_"):          # matplotlib versteckt Namen mit "_" am Anfang
                label = "\u200b" + str(label)
            ax.plot(cx, cy, color=c.get("color") or "black", lw=c.get("lw", cfg["line_width"] * 1.3),
                    ls=c.get("ls", "-"), label=core.math_symbols(label), solid_joinstyle="round",
                    marker=c.get("marker"), ms=c.get("ms", 4) * cfg.get("scale", 1.0) if c.get("marker") else None)
        f_sticks = [st for st in sticks if st.get("axis2")]
        for st in sticks:
            if st.get("axis2"):
                continue
            sel = (st["x"] >= min(xlim)) & (st["x"] <= max(xlim))
            if sel.any():
                base = st.get("base", 0.0)
                ax.vlines(st["x"][sel], max(base, ylim[0]), np.minimum(base + st["h"][sel], ylim[1]),
                          color=st.get("color", "gray"), lw=max(0.6, cfg["line_width"]), alpha=0.8,
                          linestyles=st.get("ls", "solid"))
        if f_sticks:                                       # Oszillatorstärken auf eigener Achse rechts
            ax2 = ax.twinx()
            fmax = 0.0
            for st in f_sticks:
                sel = (st["x"] >= min(xlim)) & (st["x"] <= max(xlim))
                if sel.any():
                    ax2.vlines(st["x"][sel], 0, st["h"][sel], color=st.get("color", "gray"),
                               lw=max(0.6, cfg["line_width"]), alpha=0.8)
                    fmax = max(fmax, float(st["h"][sel].max()))
            ax2.set_ylim(0, (fmax or 1.0) * 1.1)
            ax2.set_ylabel(core.fmt_text("oscillator strength f", cfg), fontsize=cfg["font_size"] * 1.3)
            sc = cfg.get("scale", 1.0)
            ax2.tick_params(direction=cfg["tick_direction"], length=6 * sc, width=max(0.6, sc))
            ax2.spines["top"].set_visible(False)
            self.ax2 = ax2
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        if cfg.get("f_axis") and self.ax2 is None:      # f als zweite Skala derselben Striche (ein Faktor)
            ax2 = ax.twinx()
            ax2.set_ylim(ylim[0] * cfg["f_axis"], ylim[1] * cfg["f_axis"])
            ax2.set_ylabel(core.fmt_text("oscillator strength f", cfg), fontsize=cfg["font_size"] * 1.3)
            sc = cfg.get("scale", 1.0)
            ax2.tick_params(direction=cfg["tick_direction"], length=6 * sc, width=max(0.6, sc))
            ax2.spines["top"].set_visible(False)
            self.ax2 = ax2
        if cfg.get("right_ticks") and self.ax2 is None:
            # Beschriftung je Kurve rechts neben der Achse statt einer Legende (EPR-Messreihe: Name, Zeit, Temperatur):
            # (y, Text, Farbe); liegt nie über den Kurven. Schrift höchstens so groß wie der kleinste Abstand.
            ys, texts, colors = zip(*cfg["right_ticks"])
            ax2 = ax.twinx()
            ax2.set_ylim(ylim)
            size = cfg["font_size"] * 0.8
            if len(set(ys)) > 1:
                h_pt = self.fig.get_size_inches()[1] * 72 * ax.get_position().height
                size = min(size, 0.9 * h_pt * float(np.min(np.diff(sorted(set(ys))))) / abs(ylim[1] - ylim[0]))
            ax2.set_yticks(ys)
            for t, c in zip(ax2.set_yticklabels([core.fmt_text(str(t), cfg) for t in texts], fontsize=size), colors):
                t.set_color(c or "black")
            if cfg.get("right_label"):
                ax2.set_ylabel(core.fmt_text(cfg["right_label"], cfg), fontsize=cfg["font_size"] * 1.3)
            sc = cfg.get("scale", 1.0)
            ax2.tick_params(direction=cfg["tick_direction"], length=3 * sc, width=max(0.5, 0.8 * sc))
            for sp in ax2.spines.values():               # Rahmen zeichnet die Hauptachse
                sp.set_visible(False)
            self.ax2 = ax2
        ax.set_xlabel(core.fmt_text(cfg["xlabel"], cfg), fontsize=cfg["font_size"] * 1.3)
        ax.set_ylabel(core.fmt_text(cfg["ylabel"], cfg), fontsize=cfg["font_size"] * 1.3)
        ax.minorticks_on()
        ax.tick_params(which="both", direction=cfg["tick_direction"], top=False, right=False)
        sc = cfg.get("scale", 1.0)
        ax.tick_params(which="major", length=6 * sc, width=max(0.6, sc))
        ax.tick_params(which="minor", length=3 * sc, width=max(0.5, 0.8 * sc))
        if not cfg["frame"]:
            ax.spines["top"].set_visible(False)
            if not f_sticks:
                ax.spines["right"].set_visible(False)
        if f_sticks:
            ax.tick_params(which="both", right=False)
        for (x0, y0, x1, y1) in cfg.get("arrows") or []:     # z. B. Scanrichtung im CV
            ax.annotate("", xy=(x1, y1), xytext=(x0, y0), annotation_clip=False,
                        arrowprops=dict(arrowstyle="-|>", color="black", lw=max(0.6, 0.8 * sc),
                                        mutation_scale=10 * sc, shrinkA=0, shrinkB=0))
        for y0 in cfg.get("zero_lines") or []:             # Nulllinie je Stapelebene
            if ylim[0] <= y0 <= ylim[1]:
                ax.axhline(y0, color="0.6", lw=max(0.5, 0.6 * sc), ls=(0, (4, 3)), zorder=0.5)
        y_axis = cfg.get("y_axis", "numbers")              # numbers | no_numbers | off
        if y_axis in ("no_numbers", "off"):
            # gestapelte/versetzte Kurven: Zahlen auf der y-Achse wären irreführend
            ax.tick_params(axis="y", which="both", left=False, labelleft=False)
        if y_axis == "off":
            ax.spines["left"].set_visible(False)
            ax.set_ylabel("")

    def _fit_axes(self, pad_in=0.06):
        """Wie im Hauptplot, berücksichtigt aber auch die rechte f-Achse."""
        if self.ax2 is None:
            return super()._fit_axes(pad_in)
        from matplotlib.transforms import Bbox
        rend = self._renderer()
        fw, fh = self.fig.get_size_inches() * self.fig.dpi
        tb = Bbox.union([self.ax.get_tightbbox(rend), self.ax2.get_tightbbox(rend)])
        ab = self.ax.get_window_extent(rend)
        pad = pad_in * self.fig.dpi
        left = (ab.x0 - tb.x0 + pad) / fw
        bottom = (ab.y0 - tb.y0 + pad) / fh
        right = 1 - (tb.x1 - ab.x1 + pad) / fw
        top = 1 - (tb.y1 - ab.y1 + pad) / fh
        if right - left > 0.3 and top - bottom > 0.3:
            for a in (self.ax, self.ax2):
                a.set_position([left, bottom, right - left, top - bottom])

    def _curve_labels(self):
        """Kurvennamen rechts über dem Kurvenende (statt Legende), in Kurvenfarbe."""
        if not self.cfg.get("curve_labels"):
            return
        ax = self.ax
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        lo, hi = min(x0, x1), max(x0, x1)
        for c in self.curves:
            if not c.get("tag"):
                continue
            x, y = np.asarray(c["x"], float), np.asarray(c["y"], float)
            sel = (x >= hi - 0.15 * (hi - lo)) & (x <= hi) & np.isfinite(y)
            if not sel.any():
                continue
            yt = min(float(np.nanmax(y[sel])), y1) + 0.03 * (y1 - y0)
            self.curve_texts.append(ax.text(hi - 0.01 * (hi - lo), yt, core.fmt_text(c["tag"], self.cfg),
                                            ha="right", va="bottom", color=c.get("color") or "black",
                                            fontsize=self.cfg["font_size"] * 0.8, zorder=5))

    def _extra_blocks(self, rend):
        return [self._measure_af(t.get_window_extent(rend)) for t in self.curve_texts]

    def _legend(self, scale=1.0):
        handles = [h for h in self.ax.get_lines() if h.get_label() and not h.get_label().startswith("_")]
        if not handles:
            return
        loc = self.layout.get("legend")
        self.legend = self.ax.legend(handles=handles, loc=tuple(loc) if loc else "best",
                                     fontsize=self.cfg["font_size"] * 0.8 * scale, frameon=False,
                                     handlelength=1.8)
        self.legend.set_draggable(True, use_blit=True, update="loc")

    def _make_labels(self, labels):
        for lab in labels:
            kw = core.label_kw(self.cfg)
            if lab.get("color"):                      # z. B. SEC: Label in der Farbe des zugehörigen Spektrums
                kw["color"] = lab["color"]
            ann = self.ax.annotate(core.fmt_text(lab["text"], self.cfg, label=True), xy=(lab["lam"], lab.get("y", 0)),
                                   xycoords="data", xytext=(0.5, 0.5), textcoords="axes fraction",
                                   ha="left", va="bottom", linespacing=1.4, annotation_clip=False,
                                   zorder=5, **kw)
            ann._anchor_y = lab.get("y")             # None: über der Hüllkurve aller Kurven platzieren
            ann._anchor_side = lab.get("side", "above")
            self.ann_items[lab["key"]] = ann

    def _place(self):
        super()._place()
        beside = self._legend_beside()
        if beside:                                         # Achse ist schmaler: Labels und Bilder dort neu setzen
            super()._place()
        self._scan_arrow()                                 # nach der Platzierung: der Pfeil ist kein Label
        if not beside:
            self._place_legend()

    def _legend_beside(self):
        """cfg["legend_beside"]: findet die Legende keine freie Stelle, kommt sie nicht über die Kurven (wie das Inset
        der ε-Abbildung), sondern rechts neben die dafür schmalere Achse; eine dorthin gezogene (x ≥ 1) bleibt dort.
        -> True, wenn die Achse verkleinert wurde."""
        saved = self.layout.get("legend")
        if self.legend is None or not self.cfg.get("legend_beside"):
            return False
        if (saved[0] < 1) if saved else (self._legend_spot() is not None):
            return False
        rend = self._renderer()
        lb, ab = self.legend.get_window_extent(rend), self.ax.get_window_extent(rend)
        axes = [a for a in (self.ax, self.ax2) if a is not None]
        gap = 0.08 * self.fig.dpi
        # Überstand rechts: Zahlen bzw. zweite Achse (ohne Legende und Labels)
        over = max(a.get_tightbbox(rend, bbox_extra_artists=[]).x1 for a in axes) - ab.x1
        fw = self.fig.get_size_inches()[0] * self.fig.dpi
        f = min(0.45 * fw / lb.width, ab.height / lb.height)
        if f < 1:                                          # lange Namen/viele Einträge: kleinere Schrift statt Abschneiden
            self.legend.set_draggable(False)
            self._legend(f)
            lb = self.legend.get_window_extent(rend)
        p = self.ax.get_position()
        width = max(0.3, p.width - (lb.width + gap) / fw)
        for a in axes:
            a.set_position([p.x0, p.y0, width, p.height])
        k = width / p.width
        for a in self.axes_items.values():                 # Bildgrößen sind Achsenbruchteile: Seitenverhältnis halten
            if hasattr(a, "_img_wh"):
                a._img_wh = (a._img_wh[0], a._img_wh[1] * k)
        if not saved:
            h = lb.height / ab.height                      # oben bündig; höher als die Achse: mittig
            # ab ist die mitlaufende Achsenbox: ab.width ist hier schon die neue Breite
            self.legend.set_loc((1 + (over + gap) / ab.width, 1 - h if h <= 1 else (1 - h) / 2))
        return True

    def _scan_arrow(self):
        """Messrichtung als ziehbares Element: Anfang in Achsenanteilen (wie Labels, Schlüssel arrow_scan), die Spitze
        folgt dem Anfang mit fester Länge. Ohne Verschieben liegt er am ersten Messpunkt."""
        # cfg["scan_arrows"]: mehrere Pfeile [(Schlüssel, x0, y0, x1, Farbe)] (Vergleich: einer je Kurve)
        arrows = [("arrow_scan", *self.cfg["scan_arrow"], "black")] if self.cfg.get("scan_arrow") else []
        arrows += list(self.cfg.get("scan_arrows") or [])
        for key, x0, y0, x1, color in arrows:
            self._one_scan_arrow(key, x0, y0, x1, color)

    def _one_scan_arrow(self, key, x0, y0, x1, color):
        from matplotlib.transforms import Affine2D
        ax, sc = self.ax, self.cfg.get("scale", 1.0)
        start, end = ax.transData.transform([(x0, y0), (x1, y0)])
        length = end[0] - start[0]                         # Pixel: auch bei umgekehrter Achse in Messrichtung
        pos = self.layout.get(key) or ax.transAxes.inverted().transform(start)
        frac = length / ax.bbox.width

        def head(_renderer):
            p = ax.transAxes.transform(ann.xyann)
            return Affine2D().translate(p[0] + frac * ax.bbox.width, p[1])
        ann = ax.annotate("     ", xy=(0, 0), xycoords=head, xytext=(float(pos[0]), float(pos[1])),
                          textcoords="axes fraction", ha="center", va="center", annotation_clip=False, zorder=5,
                          fontsize=self.cfg["font_size"],
                          arrowprops=dict(arrowstyle="-|>", color=color, lw=max(0.6, 0.8 * sc), mutation_scale=10 * sc,
                                          shrinkA=0, shrinkB=0, relpos=(0.5, 0.5)))
        self.ann_items[key] = ann


def normalize(x, y, lo, hi, min_signal=0.01):
    """Auf das Maximum im Fenster [lo, hi] normieren (Bande von Interesse).
    None, wenn dort kein Signal ist (Normieren von Rauschen wäre sinnlos)."""
    sel = (x >= min(lo, hi)) & (x <= max(lo, hi)) & np.isfinite(y)
    m = np.nanmax(y[sel]) if sel.any() else np.nan
    if not np.isfinite(m) or m <= 0:
        return None
    noise = np.nanmax(np.abs(y[np.isfinite(y)])) if np.isfinite(y).any() else 0
    if m < min_signal * noise and m < 0.005:
        return None
    return y / m


def peak_in(x, y, lo, hi):
    sel = (x >= min(lo, hi)) & (x <= max(lo, hi)) & np.isfinite(y)
    if not sel.any():
        return None
    return float(x[sel][np.nanargmax(y[sel])])
