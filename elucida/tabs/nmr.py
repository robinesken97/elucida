"""elucida/tabs/nmr.py - NMR für die SI: Spektren als Mnova-SVG, NMR-Zeile aus dem Mnova-Multiplettbericht, Parameter aus Bruker.

Auswertung bleibt in MestReNova. Hier: SVG-Exporte einsammeln (Kern aus der Achsenbeschriftung „δ ¹H (ppm)“, sonst von
Hand; 2D, wenn eine senkrechte δ-Achse vorkommt; Art aus dem Dateinamen), sortieren (¹H, ¹³C, übrige Kerne nach
Massenzahl, dann 2D), Bildunterschriften im Stil der SI („Figure Sn: ¹H NMR (500 MHz, CDCl₃, 298 K) of Name.“),
Word-Seiten mit zwei Spektren. Mnova-Text („1H NMR (501 MHz, CDCl3) δ 7.52 – 7.45 (m, 2H), …“) wird in Signale
zerlegt, je Signal eine Zuordnung ergänzt und als „¹H NMR (500 MHz, CDCl₃): δ [ppm] = … (m, 2H, Zuordnung)“
ausgegeben. Werte bleiben Text wie im Bericht. Bruker acqus/acqu2s (JCAMP) liefern T, SFO1, O1P, SW, NS … zur Kontrolle.
"""
from __future__ import annotations

import html as _h
import re
import uuid
from pathlib import Path

from elucida.tabs import xray as XRAY
from elucida.app.i18n import T
from elucida.formats.topspin import (read_jcamp_params, acq_params, bruker_dir, find_experiments, experiment_kind, experiment_name, parse_nucleus)  # noqa: E402,F401  (Leser in elucida/formats)
from elucida.formats.mnova import (svg_info, svg_peaks, emf_info, is_emf, is_nmr_svg, spectrum_info, _NUC)  # noqa: E402,F401  (Leser in elucida/formats)

KINDS_2D = ("COSY", "HSQC", "HMQC", "HMBC", "NOESY", "ROESY", "TOCSY", "HOESY", "INADEQUATE", "2D")
_KIND_ORDER = {k: i for i, k in enumerate(("COSY", "TOCSY", "HSQC", "HMQC", "HMBC", "NOESY", "ROESY", "HOESY",
                                           "INADEQUATE", "2D"))}


# ---------------------------------------------------------------------------- Kerne


def nuc_mass(nuc):
    m = re.match(r"(\d+)", nuc or "")
    return int(m.group(1)) if m else 999


def nuc_markup(nuc):
    """„13C“ -> „^{13}C“ (Auszeichnung wie im X-Ray-Tab)."""
    m = re.match(r"(\d+)([A-Za-z]+)", nuc or "")
    return f"^{{{m.group(1)}}}{m.group(2)}" if m else str(nuc or "")


def nuc_rank(nuc):
    """¹H zuerst, dann ¹³C, dann die übrigen Kerne nach Massenzahl."""
    return 0 if nuc == "1H" else 1 if nuc == "13C" else 2 + nuc_mass(nuc)


def sort_key(spec):
    nuc = spec.get("nuclei") or []
    if spec.get("kind", "1D") == "1D":
        return (0, nuc_rank(nuc[0] if nuc else ""), 0)
    return (1, _KIND_ORDER.get(spec.get("kind"), 99), sum(nuc_rank(n) for n in nuc))


def kind_from_name(name):
    up = Path(name).stem.upper()
    for k in KINDS_2D[:-1]:
        if k in up:
            return k
    return None


# ---------------------------------------------------------------------------- SVG


# Larmorfrequenz relativ zu ¹H (für die Nennfrequenz anderer Kerne, wenn kein Bruker-Ordner da ist)
GAMMA_REL = {"2H": 0.15351, "7Li": 0.38864, "11B": 0.32084, "13C": 0.25145, "15N": 0.10137, "19F": 0.94094,
             "27Al": 0.26057, "29Si": 0.19867, "31P": 0.40481, "77Se": 0.19072, "103Rh": 0.03186, "117Sn": 0.35632,
             "119Sn": 0.37291, "125Te": 0.31549, "195Pt": 0.21496, "199Hg": 0.17911}


def svg_png(svg, png, dpi=200):
    """PNG-Ersatz für Word (das SVG selbst bleibt die eigentliche Grafik)."""
    import pymupdf
    pymupdf.open(str(svg))[0].get_pixmap(dpi=dpi).save(str(png))
    return Path(png)


# ---------------------------------------------------------------------------- Bruker-Parameter


def spectrum_kind(spec):
    """Art eines Mnova-Spektrums im Sinne von experiment_kind (1D: Kern, 2D: COSY/HSQC …)."""
    nuc = spec.get("nuclei") or []
    if spec.get("kind", "1D") == "1D":
        return nuc[0] if nuc else "1D"
    return spec.get("kind") or "2D"


def match_experiment(spec, raws, spectra=()):
    """Das eine TopSpin-Experiment, das zu einem Spektrum passt (gleiche Art), sonst None (keins oder mehrdeutig, auch
    wenn ein anderes Spektrum dieselbe Art hat, z. B. ¹³C + DEPT, oder das Experiment schon verknüpft ist)."""
    k = spectrum_kind(spec)
    others = [t for t in spectra if t is not spec]
    if any(spectrum_kind(t) == k for t in others):
        return None
    taken = {t.get("bruker") for t in others}
    hits = [r for r in raws if r.get("kind") == k and r.get("path") not in taken]
    return hits[0] if len(hits) == 1 else None


def params_html(p):
    """Kleine Tabelle für die Anzeige im Tab."""
    rows = []

    def add(lab, val):
        if val not in (None, ""):
            rows.append(f"<tr><td>{_h.escape(lab)}</td><td>{_h.escape(str(val))}</td></tr>")
    add(T("nmr_p_nuc"), p.get("nucleus") + (f" / {p['nucleus2']}" if p.get("nucleus2") else "") if p.get("nucleus") else "")
    add(T("nmr_p_pulprog"), p.get("pulprog"))
    add(T("nmr_p_solvent"), p.get("solvent"))
    add("T", f"{p['te']:.1f} K" if p.get("te") else "")
    add("SFO1", f"{p['sfo1']:.4f} MHz" if p.get("sfo1") else "")
    add("O1P", f"{p['o1p']:.3f} ppm" if p.get("o1p") is not None else "")
    add("SW", f"{p['sw']:.2f} ppm" if p.get("sw") else "")
    add("NS / DS", f"{p.get('ns')} / {p.get('ds')}" if p.get("ns") else "")
    add("TD", p.get("td"))
    add("D1", f"{p['d1']:g} s" if p.get("d1") is not None else "")
    add("AQ", f"{p['aq']:.2f} s" if p.get("aq") else "")
    add("RG", p.get("rg"))
    if p.get("sfo1_2"):
        add("F1: SFO1 / SW", f"{p['sfo1_2']:.4f} MHz / {p.get('sw2') or 0:.1f} ppm")
    add(T("nmr_p_probe"), p.get("probe"))
    return "<table cellspacing='0' cellpadding='1'>" + "".join(rows) + "</table>"


# ---------------------------------------------------------------------------- Mnova-Text
_HEAD = re.compile(r"(?P<mass>\d{1,3})\s*(?P<el>[A-Z][a-z]?)\s*(?P<dec>\{[^}]*\})?\s*NMR\s*\(\s*(?P<freq>[\d.]+)\s*MHz\s*,"
                   r"\s*(?P<solv>[^)]+?)\s*\)\s*:?\s*δ\s*(?:\[\s*ppm\s*\]\s*=|\(\s*ppm\s*\)|=)?\s*", re.S)
_MULT = re.compile(r"^(?:br\.?\s*)?(?:app\.?\s*)?(?:[sdtqp]{1,4}|m|quint|sext|sept|hept|br|br s|brs|bs|m_c|AB|ABq|"
                   r"AA'BB'|AA′BB′)$", re.I)


def _split_top(s, sep=","):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def parse_signal(txt):
    """„6.91 (dd, J = 7.0, 1.5 Hz, 1H)“ -> dict(shift, mult, J, nH, assign)."""
    m = re.match(r"^\s*(?P<shift>[−-]?\d+(?:\.\d+)?(?:\s*[–—-]\s*[−-]?\d+(?:\.\d+)?)?)\s*(?:\((?P<par>.*)\))?\s*$",
                 txt, re.S)
    if not m:
        return dict(shift=txt.strip(), mult="", J="", nH="", assign="")
    shift = re.sub(r"\s*[–—]\s*", " – ", m.group("shift").strip())
    shift = re.sub(r"(\d)\s+-\s+([−-]?\d)", r"\1 – \2", shift)
    sig = dict(shift=shift, mult="", J="", nH="", assign="")
    toks = _split_top(m.group("par") or "")
    rest, i = [], 0
    while i < len(toks):
        t = toks[i]
        if re.match(r"^J\b|^\d?J\s*\(|^J\s*=", t):
            parts = [t]
            while not re.search(r"Hz\s*$", parts[-1]) and i + 1 < len(toks) and re.fullmatch(r"[\d.]+(\s*Hz)?",
                                                                                          toks[i + 1]):
                i += 1
                parts.append(toks[i])
            vals = re.sub(r"^.*?=\s*", "", ", ".join(parts))
            sig["J"] = (sig["J"] + "; " if sig["J"] else "") + re.sub(r"\s*Hz\s*$", "", vals).strip()
        elif not sig["mult"] and not sig["J"] and _MULT.match(t):
            sig["mult"] = t
        elif re.fullmatch(r"\d+(\.\d+)?\s*H", t):
            sig["nH"] = t.replace(" ", "")
        else:
            rest.append(t)
        i += 1
    sig["assign"] = ", ".join(rest)
    return sig


def parse_mnova(text):
    """Multiplettbericht(e) von Mnova (auch mehrere Kerne hintereinander) -> [dict(nucleus, dec, freq, solvent,
    signals)]."""
    blocks = []
    heads = list(_HEAD.finditer(text or ""))
    for k, m in enumerate(heads):
        body = text[m.end(): heads[k + 1].start() if k + 1 < len(heads) else len(text)].strip()
        body = re.split(r"\.\s*\n", body)[0]          # Satzende: danach z. B. „(13C Peak Report)“ von Mnova
        body = re.sub(r"[.;]\s*$", "", body.strip())
        sigs = [parse_signal(s) for s in _split_top(body)]
        blocks.append(dict(nucleus=f"{m.group('mass')}{m.group('el')}", dec=m.group("dec") or "",
                           freq=m.group("freq"), solvent=m.group("solv").strip(), signals=sigs))
    return blocks


def nominal_freq(nuc, freq):
    """¹H auf die Nennfrequenz (501 -> 500 MHz), andere Kerne ganzzahlig wie im Bericht."""
    try:
        f = float(freq)
    except (TypeError, ValueError):
        return str(freq or "")
    if nuc == "1H":
        return f"{round(f / 50) * 50:d}" if f >= 100 else f"{round(f):d}"
    return f"{round(f):d}"


def solvent_markup(s):
    """CDCl3 -> CDCl_{3}, DMSO-d6 -> DMSO-*d*_{6}, C6D6 -> C_{6}D_{6}."""
    s = (s or "").strip()
    s = re.sub(r"-d(\d+)\b", r"-*d*_{\1}", s)
    return re.sub(r"(?<=[A-Za-z)])(\d+)", r"_{\1}", s)


def signal_markup(sig, assign=None):
    a = sig["assign"] if assign is None else assign
    parts = [p for p in (sig["mult"], f"*J* = {sig['J']} Hz" if sig["J"] else "", sig["nH"], a) if p]
    sh = XRAY.minus(sig["shift"])
    return sh + (f" ({', '.join(parts)})" if parts else "")


def nmr_line(block, assigns=None):
    """-> (Klartext, HTML) im SI-Stil: „¹H NMR (500 MHz, CDCl₃): δ [ppm] = 7.39 – 7.36 (m, 2H, ImPy-H), …“."""
    assigns = assigns or {}
    nuc = block["nucleus"]
    dec = block.get("dec") or ""
    dec_m = re.sub(r"\{(\d+)([A-Z][a-z]?)\}", r"{^{\1}\2}", dec)
    head = nuc_markup(nuc) + dec_m + " NMR"
    cond = f"{nominal_freq(nuc, block['freq'])} MHz, {solvent_markup(block['solvent'])}"
    sigs = [signal_markup(s, assigns.get(sig_key(nuc, s))) for s in block["signals"]]
    body = "δ [ppm] = " + ", ".join(sigs)
    markup_plain = f"{head} ({cond}): {body}"
    html = f"<b>{XRAY.to_html(head)}</b> ({XRAY.to_html(cond)}): {XRAY.to_html(body)}"
    return XRAY.to_plain(markup_plain), html


def sig_key(nuc, sig):
    return f"{nuc}|{sig['shift']}"


# ---------------------------------------------------------------------------- Bildunterschriften
def spectrum_freqs(spec, blocks):
    """Frequenzen je Kern: Eingabe im Tab > Mnova-Text > Bruker (SFO1)."""
    out = {}
    by = {b["nucleus"]: b for b in blocks}
    pr = spec.get("params") or {}
    for i, nuc in enumerate(spec.get("nuclei") or []):
        man = (spec.get("freqs") or {}).get(nuc)
        if man:
            out[nuc] = str(man)
        elif nuc in by:
            out[nuc] = nominal_freq(nuc, by[nuc]["freq"])
        else:
            sf = pr.get("sfo1") if (pr.get("nucleus") == nuc) else pr.get("sfo1_2") if pr.get("nucleus2") == nuc else None
            if sf:
                out[nuc] = nominal_freq(nuc, sf)
    return out


def caption_html(spec, blocks, name):
    """„¹H NMR (500 MHz, CDCl₃, 298 K) of <b>Name</b>.“ bzw. „¹H/¹³C HSQC (500/126 MHz, …)“."""
    nuc = spec.get("nuclei") or []
    fr = spectrum_freqs(spec, blocks)
    solv = spec.get("solvent") or next((b["solvent"] for b in blocks if b["solvent"]), "") \
        or (spec.get("params") or {}).get("solvent", "")
    temp = spec.get("temp") or 298
    if spec.get("kind", "1D") == "1D":
        head = nuc_markup(nuc[0]) + " NMR" if nuc else "NMR"
        f = fr.get(nuc[0]) if nuc else None
    else:
        head = "/".join(nuc_markup(n) for n in nuc) + f" {spec.get('kind')}"
        f = "/".join(fr.get(n, "?") for n in nuc) if nuc and any(n in fr for n in nuc) else None
    cond = ", ".join(x for x in (f"{f} MHz" if f else "", solvent_markup(solv), f"{float(temp):.0f} K") if x)
    return f"{XRAY.to_html(head)} ({XRAY.to_html(cond)}) of <b>{_h.escape(name)}</b>."


STRUCT_POS = ("auto", "tl", "tc", "tr", "manual")     # frei suchen / feste Ecken oben / gezogen
_FIXED = {"tl": (0.07, 0.12), "tc": (None, 0.12), "tr": (None, 0.12)}


def svg_viewbox(svg_text):
    m = re.search(r'viewBox="\s*([-\d.]+)[\s,]+([-\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)', svg_text)
    if m:
        return tuple(map(float, m.groups()))
    w = re.search(r'<svg[^>]*\swidth="([\d.]+)', svg_text)
    h = re.search(r'<svg[^>]*\sheight="([\d.]+)', svg_text)
    return (0.0, 0.0, float(w.group(1)) if w else 1000.0, float(h.group(1)) if h else 700.0)


def occupancy(spec_svg, px_w=400):
    """Belegte Fläche des Spektrums (alles, was nicht weiß ist: Signale, Labels, Integrale, Achsen, Insets) -> bool[H, W]."""
    import numpy as np
    import pymupdf
    page = pymupdf.open(str(spec_svg))[0]
    pix = page.get_pixmap(dpi=max(10, int(px_w / max(page.rect.width, 1) * 72)), colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    return a < 235


def auto_place(mask, width, aspect, margin=0.015):
    """Freie Stelle für die Struktur (Breite = Anteil der Bildbreite, aspect = Höhe/Breite): am wenigsten Überdeckung
    mit Rand, bei Gleichstand möglichst weit oben links. -> (fx, fy) linke obere Ecke als Anteil von Breite/Höhe."""
    import numpy as np
    H, W = mask.shape
    w = max(2, int(round(width * W)))
    h = max(2, int(round(w * aspect)))
    m = max(1, int(round(margin * W)))
    if w + 2 * m >= W or h + 2 * m >= H:
        return 0.02, 0.02
    ii = np.zeros((H + 1, W + 1), np.int64)
    ii[1:, 1:] = mask.cumsum(0).cumsum(1)
    best, step = None, max(1, W // 120)
    for y in range(m, H - h - m + 1, step):
        y0, y1 = y - m, y + h + m
        for x in range(m, W - w - m + 1, step):
            x0, x1 = x - m, x + w + m
            occ = ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]
            key = (occ, y / H + x / W)
            if best is None or key < best[0]:
                best = (key, x, y)
    _, x, y = best
    return x / W, y / H


def struct_aspect(struct):
    cx0, cy0, cx1, cy1 = struct["clip"]
    return (cy1 - cy0) / max(cx1 - cx0, 1e-6)


def place_structure(spec_svg, struct, pos="auto", width=0.2, xy=None):
    """Lage der Struktur als (fx, fy) – gezogen (manual), feste Ecke oder frei gesucht (auto)."""
    if pos == "manual" and xy:
        return float(xy[0]), float(xy[1])
    if pos in _FIXED:
        fx, fy = _FIXED[pos]
        if pos == "tc":
            fx = (1 - width) / 2
        elif pos == "tr":
            fx = 0.93 - width
        return fx, fy
    return auto_place(occupancy(spec_svg), width, struct_aspect(struct))   # Pixelmaske: x und y gleich skaliert


def compose_structure(spec_svg, struct, out_svg, xy=(0.07, 0.12), width=0.2):
    """Struktur (dict aus IMG.load_structure: pdf + clip) als Vektorgruppe in das Mnova-SVG setzen – ersetzt den
    Inkscape-Schritt. xy = linke obere Ecke als Anteil der Bildbreite/-höhe, width = Anteil der Bildbreite."""
    from elucida.core import images as IMG
    txt = Path(spec_svg).read_text(encoding="utf-8", errors="replace")
    vx, vy, vw, vh = svg_viewbox(txt)
    w = vw * width
    h = w * struct_aspect(struct)
    x0, y0 = vx + xy[0] * vw, vy + xy[1] * vh
    Path(out_svg).parent.mkdir(parents=True, exist_ok=True)
    Path(out_svg).write_text(txt, encoding="utf-8")
    IMG.overlay_vectors_svg(out_svg, [((x0, y0, x0 + w, y0 + h), struct["pdf"], struct["clip"])])
    return Path(out_svg)


def new_spectrum(path, info, kind=None):
    k = kind or ("1D" if not info["is2d"] else (kind_from_name(path) or "2D"))
    return dict(uid=uuid.uuid4().hex[:8], file=str(path), nuclei=list(info["nuclei"]), kind=k, temp=298.0,
                bruker=None, params=None, freqs={}, solvent="", size=list(info["size_cm"]), struct_on=True,
                struct_pos="auto", struct_xy=None, struct_w=20.0)


def make_test_svg(path, nuclei=("1H",), axis=True, peaks=()):
    """Künstliches Mnova-ähnliches SVG (Achsenbeschriftung als Text wie bei Mnova, eine Kurve). Kein echter Datensatz."""
    w, h = 1088, 759
    lab = lambda n, x, y, rot="": (f'<text x="{x}" y="{y}" font-size="14" {rot}>δ <tspan dy="-4" font-size="9">'  # noqa: E731
                                   f'{re.match(r"(\d+)", n).group(1)}</tspan><tspan dy="4">'
                                   f'{re.sub(r"^\d+", "", n)} (ppm)</tspan></text>')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="287.867mm" height="200.819mm" viewBox="0 0 {w} {h}">',
             '<title>MestReNova SVG (test)</title>',
             '<polyline fill="none" stroke="#800000" points="50,700 300,700 310,200 320,700 1040,700"/>']
    for k, txt in enumerate(peaks):                        # senkrechte Peaklabels wie bei Mnova
        x = 300 + 40 * k
        parts.append(f'<text x="{x}" y="60" font-size="9" transform="rotate(-90 {x} 60)">{txt}</text>')
    if axis:
        parts.append(lab(nuclei[0], 500, 745))
        if len(nuclei) > 1:
            parts.append(lab(nuclei[1], 1070, 380, 'transform="rotate(90 1070 380)"'))
    parts.append("</svg>")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(parts), encoding="utf-8")
    return Path(path)


def make_test_acqus(d, nuc="1H", sfo1=500.503090587, te=298.1466, nuc2=None, pulprog="zg30"):
    """Künstlicher Bruker-Experimentordner mit acqus (und acqu2s). Kein echter Datensatz."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    txt = ["##TITLE= Parameter file", f"##$NUC1= <{nuc}>", f"##$PULPROG= <{pulprog}>", "##$SOLVENT= <CDCl3>",
           f"##$TE= {te}", f"##$SFO1= {sfo1}", "##$BF1= 500.5", f"##$O1= {6.175 * sfo1}", "##$SW= 19.9784",
           "##$NS= 16", "##$DS= 2", "##$TD= 65536", "##$RG= 101", "##$D= (0..63)", "0 1 0.03 0 0 0 0 0",
           "##$PROBHD= <test probe>", "##END="]
    (d / "acqus").write_text("\n".join(txt) + "\n", encoding="latin-1", newline="")      # wie TopSpin, auch unter Windows
    if nuc2:
        (d / "acqu2s").write_text(f"##$NUC1= <{nuc2}>\n##$SFO1= 125.8\n##$SW= 165\n##$TD= 256\n##END=\n",
                                  encoding="latin-1")
    return d


# ---------------------------------------------------------------------------- Tab
from PySide6.QtCore import QEvent, QRectF, Qt, QTimer  # noqa: E402
from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,  # noqa: E402
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QScrollArea, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout,
                               QSizePolicy, QStackedWidget, QWidget)

from elucida.app import project as PRJ  # noqa: E402
from elucida.app.style import HINT_CSS, make_form  # noqa: E402

FIG_W_CM = 16.0                    # Breite der Spektren in Word (zwei Abbildungen je Seite, wie in der SI)


class NMRTab(QWidget):
    STATE_KEY = "nmr"
    DEFAULT_STATE = dict(spectra=[], current=None, text="", assign={}, raw=[], mnova=[])

    def __init__(self, main, state):
        super().__init__()
        self.main, self.st = main, state
        for k, v in self.DEFAULT_STATE.items():
            self.st.setdefault(k, type(v)() if isinstance(v, (list, dict)) else v)
        self._loading = False
        self.text_timer = QTimer(self, singleShot=True, interval=500)
        self.text_timer.timeout.connect(self.text_changed)
        left = QWidget()
        self.lv = QVBoxLayout(left)
        self.build_controls()
        self.lv.addStretch(1)
        ls = QScrollArea()
        ls.setWidget(left)
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.NoFrame)
        ls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ls.setMinimumWidth(max(460, left.minimumSizeHint().width() + 24))
        from elucida.tabs.base import EmptyGuide
        prev = QWidget()
        rv = QVBoxLayout(prev)
        rv.setContentsMargins(0, 0, 0, 0)
        self.lbl_prev = QLabel("", alignment=Qt.AlignCenter, wordWrap=True)
        # Größe kommt vom Layout, nie vom Pixmap (sonst Mindestgröße = altes Bild: wächst nicht nach, schrumpft nicht)
        self.lbl_prev.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.lbl_prev.setMinimumSize(200, 200)
        self.lbl_prev.installEventFilter(self)             # Struktur in der Vorschau ziehen, Größenänderung
        self._drag_rect, self._drag, self._pm_size = None, None, (1, 1)
        rv.addWidget(self.lbl_prev, 1)
        self.lbl_cap = QLabel("", wordWrap=True)
        self.lbl_cap.setTextFormat(Qt.RichText)
        rv.addWidget(self.lbl_cap)
        right = QWidget()
        self.preview_stack = QStackedWidget()             # 0 = Anleitung (leerer Tab, wie die anderen Tabs), 1 = Vorschau
        self.preview_stack.addWidget(EmptyGuide("nmr", (T("nmr_add"), self.add_svg)))
        self.preview_stack.addWidget(prev)
        # Reiter neben der Abbildung wie die Ergebnisseiten der anderen Tabs: Rohdaten (TopSpin, Mnova)
        from elucida.tabs.base import result_page
        self.right_tabs = QTabWidget()
        self.right_tabs.setDocumentMode(True)
        self.right_tabs.addTab(self.preview_stack, T("tab_figure"))
        self.right_tabs.addTab(result_page(self.grp_raw), T("nmr_raw"))
        QVBoxLayout(right).addWidget(self.right_tabs)
        from elucida.tabs.base import footer
        split = QSplitter(Qt.Horizontal)
        split.addWidget(footer(self, ls))
        split.addWidget(right)
        split.setSizes([500, 900])
        from elucida.tabs.base import fit_footer_column
        fit_footer_column(self, split, 460)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)
        self.sync_widgets()

    # -- Bedienelemente -------------------------------------------------------------------
    def build_controls(self):
        g = QGroupBox(T("nmr_spectra"))
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        for txt, fn in ((T("nmr_add"), self.add_svg), (T("remove"), self.remove_spectrum)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels([T("nmr_file"), T("nmr_nuclei"), T("nmr_kind")])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.setMinimumHeight(130)
        self.tbl.itemSelectionChanged.connect(self.spectrum_selected)
        v.addWidget(self.tbl)
        hint = QLabel(T("nmr_order_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.lv.addWidget(g)

        # Rohdaten: TopSpin-Experimente (ganz, nach Art sortiert) und Mnova-Dokumente – nur ablegen, nicht auswerten;
        # als Reiter neben der Abbildung (siehe __init__), nicht in der linken Spalte
        g = QGroupBox(T("nmr_raw"))
        v = QVBoxLayout(g)
        hint = QLabel(T("nmr_raw_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.tbl_raw = QTableWidget(0, 4)
        self.tbl_raw.setHorizontalHeaderLabels([T("nmr_raw_kind"), T("nmr_raw_name"), T("nmr_raw_pulprog"),
                                                T("nmr_raw_spectrum")])
        self.tbl_raw.verticalHeader().setVisible(False)
        self.tbl_raw.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl_raw.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_raw.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_raw.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_raw.setToolTip(T("nmr_raw_open_tip"))
        self.tbl_raw.itemDoubleClicked.connect(lambda it: QDesktopServices.openUrl(
            QUrl.fromLocalFile(self.tbl_raw.item(it.row(), 0).data(Qt.UserRole))))
        v.addWidget(self.tbl_raw)
        row = QHBoxLayout()
        for txt, tip, fn, ic in ((T("nmr_topspin"), T("nmr_topspin_tip"), self.add_topspin, "open"),
                                 (T("nmr_mnova"), T("nmr_mnova_tip"), self.add_mnova, None),
                                 (T("remove"), T("nmr_raw_remove_tip"), self.remove_raw, None)):
            b = QPushButton(txt)
            if ic:
                from elucida.app import style as STYLE
                b.setIcon(STYLE.icon(ic, "#FFFFFF"))
            b.setToolTip(tip)
            b.clicked.connect(fn)
            row.addWidget(b)
        v.addLayout(row)
        self.grp_raw = g

        g = QGroupBox(T("nmr_selected"))
        f = make_form(g)
        self.ed_nuc = QLineEdit()
        self.ed_nuc.setPlaceholderText("1H  ·  13C  ·  1H/13C")
        self.ed_nuc.setToolTip(T("nmr_nuclei_tip"))
        self.ed_nuc.editingFinished.connect(self.spec_edited)
        f.addRow(T("nmr_nuclei"), self.ed_nuc)
        self.lbl_nuc = QLabel("", wordWrap=True)
        self.lbl_nuc.setStyleSheet(HINT_CSS)
        f.addRow(self.lbl_nuc)
        self.cmb_kind = QComboBox()
        for k in ("1D",) + KINDS_2D:
            self.cmb_kind.addItem(k, k)
        self.cmb_kind.currentIndexChanged.connect(self.spec_edited)
        f.addRow(T("nmr_kind"), self.cmb_kind)
        self.sp_temp = QDoubleSpinBox(decimals=0, minimum=100, maximum=500, singleStep=1, suffix=" K", value=298)
        self.sp_temp.valueChanged.connect(self.spec_edited)
        f.addRow(T("nmr_temp"), self.sp_temp)
        self.ed_freq = QLineEdit()
        self.ed_freq.setPlaceholderText(T("nmr_freq_ph"))
        self.ed_freq.setToolTip(T("nmr_freq_tip"))
        self.ed_freq.editingFinished.connect(self.spec_edited)
        f.addRow(T("nmr_freq"), self.ed_freq)
        self.ed_solv = QLineEdit()
        self.ed_solv.setPlaceholderText(T("nmr_solv_ph"))
        self.ed_solv.editingFinished.connect(self.spec_edited)
        f.addRow(T("nmr_solvent"), self.ed_solv)
        row = QHBoxLayout()
        b = QPushButton(T("nmr_bruker"))
        b.setToolTip(T("nmr_bruker_tip"))
        b.clicked.connect(self.add_bruker)
        row.addWidget(b)
        b = QPushButton(T("nmr_bruker_temp"))
        b.setToolTip(T("nmr_bruker_temp_tip"))
        b.clicked.connect(self.temp_from_bruker)
        row.addWidget(b)
        row.addStretch(1)
        f.addRow(row)
        self.lbl_par = QLabel("", wordWrap=True)
        self.lbl_par.setTextFormat(Qt.RichText)
        f.addRow(self.lbl_par)
        row = QHBoxLayout()
        self.cb_struct = QCheckBox(T("nmr_struct_on"))
        self.cb_struct.setToolTip(T("nmr_struct_tip"))
        self.cb_struct.toggled.connect(self.spec_edited)
        row.addWidget(self.cb_struct)
        self.cmb_spos = QComboBox()
        for k in STRUCT_POS:
            self.cmb_spos.addItem(T("nmr_pos_" + k), k)
        self.cmb_spos.currentIndexChanged.connect(self.spec_edited)
        row.addWidget(self.cmb_spos)
        self.sp_sw = QDoubleSpinBox(decimals=0, minimum=5, maximum=60, singleStep=1, suffix=" %", value=20)
        self.sp_sw.valueChanged.connect(self.spec_edited)
        row.addWidget(self.sp_sw)
        row.addStretch(1)
        f.addRow(T("nmr_struct"), row)
        row = QHBoxLayout()
        self.lbl_struct = QLabel("", wordWrap=True)
        self.lbl_struct.setStyleSheet(HINT_CSS)
        row.addWidget(self.lbl_struct, 1)
        b = QPushButton(T("nmr_struct_pick"))
        b.setToolTip(T("nmr_struct_pick_tip"))
        b.clicked.connect(self.pick_structure)
        row.addWidget(b)
        f.addRow(row)
        self.lv.addWidget(g)

        g = QGroupBox(T("nmr_text"))
        v = QVBoxLayout(g)
        hint = QLabel(T("nmr_text_hint"), wordWrap=True)
        hint.setStyleSheet(HINT_CSS)
        v.addWidget(hint)
        self.ed_text = QPlainTextEdit()
        self.ed_text.setPlaceholderText("1H NMR (501 MHz, CDCl3) δ 7.52 – 7.45 (m, 2H), …\n"
                                        "13C NMR (126 MHz, CDCl3) δ 141.20, 128.35, …")
        self.ed_text.setMaximumHeight(160)
        self.ed_text.textChanged.connect(lambda: None if self._loading else self.text_timer.start())
        v.addWidget(self.ed_text)
        self.tbl_sig = QTableWidget(0, 6)
        self.tbl_sig.setHorizontalHeaderLabels([T("nmr_nuc_short"), "δ [ppm]", T("nmr_mult"), "J [Hz]", "H",
                                                T("nmr_assign")])
        self.tbl_sig.verticalHeader().setVisible(False)
        self.tbl_sig.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.tbl_sig.setMinimumHeight(170)
        self.tbl_sig.setToolTip(T("nmr_assign_tip"))
        self.tbl_sig.itemChanged.connect(self.assign_edited)
        v.addWidget(self.tbl_sig)
        self.txt_line = QTextBrowser()
        self.txt_line.setMaximumHeight(120)
        v.addWidget(self.txt_line)
        row = QHBoxLayout()
        b = QPushButton(T("nmr_copy"))
        b.clicked.connect(self.copy_lines)
        row.addWidget(b)
        b = QPushButton(T("nmr_peaks"))
        b.setToolTip(T("nmr_peaks_tip"))
        b.clicked.connect(self.peaks_from_svg)
        row.addWidget(b)
        b = QPushButton(T("nmr_word"))
        b.setToolTip(T("nmr_word_tip"))
        b.clicked.connect(lambda: self.export_dialog())
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lv.addWidget(g)

    # -- Zustand --------------------------------------------------------------------------
    def spectra(self):
        return sorted(self.st["spectra"], key=sort_key)

    def current(self):
        for s in self.st["spectra"]:
            if s["uid"] == self.st.get("current"):
                return s
        sp = self.spectra()
        return sp[0] if sp else None

    def blocks(self):
        return parse_mnova(self.st.get("text") or "")

    def struct_w(self):
        """Größe der Struktur in % der Bildbreite – eine für alle Spektren (ältere Projekte: je Spektrum)."""
        if "struct_w" not in self.st:
            self.st["struct_w"] = float(next((s["struct_w"] for s in self.st["spectra"] if s.get("struct_w")), 20.0))
        return float(self.st["struct_w"])

    def peaks_from_svg(self):
        """Zeile „13C NMR (126 MHz, CDCl3) δ 141.20, …“ aus den Peaklabels des gewählten 1D-Spektrums (nicht ¹H:
        dort braucht es den Multiplettbericht); ersetzt eine vorhandene Zeile desselben Kerns."""
        s = self.current()
        if s is None or s.get("kind") != "1D" or not s.get("nuclei"):
            return self.main.error(T("nmr_peaks_need"))
        nuc = s["nuclei"][0]
        if nuc == "1H":
            return self.main.error(T("nmr_peaks_1h"))
        if is_emf(s["file"]):
            return self.main.error(T("nmr_emf_nopeaks"))
        vals, solv = svg_peaks(s["file"])
        if not vals:
            return self.main.error(T("nmr_peaks_none", f=Path(s["file"]).name))
        bl = {b["nucleus"]: b for b in self.blocks()}
        h1 = bl.get("1H") or {}
        freq = spectrum_freqs(s, []).get(nuc)                       # SFO1 nur vom selben Kern
        if not freq and h1.get("freq") and nuc in GAMMA_REL:
            freq = float(nominal_freq("1H", h1["freq"])) * GAMMA_REL[nuc]
        solv = s.get("solvent") or solv or h1.get("solvent") or ""
        head = f"{nuc} NMR" + (f" ({nominal_freq(nuc, freq)} MHz, {solv})" if freq else f" ({solv})" if solv else "")
        line = f"{head} δ " + ", ".join(vals) + "."
        lines = [ln for ln in (self.st.get("text") or "").splitlines() if ln.strip()
                 and not re.match(rf"\s*{re.escape(nuc)}\s*(?:\{{[^}}]*\}})?\s*NMR", ln)]
        self.ed_text.setPlainText("\n".join(lines + [line]))
        self.text_changed()
        self.main.statusBar().showMessage(T("nmr_peaks_done", n=len(vals), nuc=nuc), 8000)

    def compound_name(self):
        comp = getattr(self.main, "compound", None) or {}
        return comp.get("name") or (Path(self.main.project_dir).name if self.main.project_dir else "")

    def sync_widgets(self):
        self._loading = True
        sp = self.spectra()
        self.tbl.setRowCount(len(sp))
        for r, s in enumerate(sp):
            for c, val in enumerate((Path(s["file"]).name, "/".join(s.get("nuclei") or []) or "?", s.get("kind"))):
                it = QTableWidgetItem(val)
                if c == 1 and not s.get("nuclei"):
                    it.setToolTip(T("nmr_nuc_missing"))
                self.tbl.setItem(r, c, it)
        cur = self.current()
        if cur is not None:
            self.tbl.selectRow(sp.index(cur))
        if self.ed_text.toPlainText() != (self.st.get("text") or ""):
            self.ed_text.setPlainText(self.st.get("text") or "")
        self.fill_selected()
        self.fill_signals()
        self.fill_raw()
        self._loading = False
        self.update_preview()

    def fill_selected(self):
        s = self.current()
        for w in (self.ed_nuc, self.cmb_kind, self.sp_temp, self.ed_freq, self.ed_solv, self.cb_struct,
                  self.cmb_spos, self.sp_sw):
            w.setEnabled(s is not None)
        sp_ = self.structure_path()
        self.lbl_struct.setText(T("nmr_struct_from", f=Path(sp_).name) if sp_ else T("nmr_struct_none"))
        if s is None:
            self.lbl_par.setText("")
            self.lbl_nuc.setText("")
            return
        self.ed_nuc.setText("/".join(s.get("nuclei") or []))
        self.lbl_nuc.setText(T("nmr_nuc_from_axis") if s.get("nuc_auto") else T("nmr_nuc_manual"))
        self.lbl_nuc.setStyleSheet(HINT_CSS if s.get("nuclei") else "color: #d9534f;")
        if not s.get("nuclei"):
            self.lbl_nuc.setText(T("nmr_nuc_missing"))
        self.cmb_kind.setCurrentIndex(max(0, self.cmb_kind.findData(s.get("kind", "1D"))))
        self.sp_temp.setValue(float(s.get("temp") or 298))
        self.ed_freq.setText("/".join(str((s.get("freqs") or {}).get(n, "")) for n in s.get("nuclei") or []).strip("/"))
        self.ed_solv.setText(s.get("solvent") or "")
        self.cb_struct.setChecked(s.get("struct_on", True))
        self.cmb_spos.setCurrentIndex(max(0, self.cmb_spos.findData(s.get("struct_pos", "auto"))))
        self.sp_sw.setValue(self.struct_w())
        p = s.get("params")
        self.lbl_par.setText(params_html(p) if p else T("nmr_no_bruker"))

    def fill_signals(self):
        rows = [(b["nucleus"], sig) for b in self.blocks() for sig in b["signals"]]
        self.tbl_sig.setRowCount(len(rows))
        assign = self.st.get("assign") or {}
        for r, (nuc, sig) in enumerate(rows):
            vals = (nuc, sig["shift"], sig["mult"], sig["J"], sig["nH"],
                    assign.get(sig_key(nuc, sig), sig["assign"]))
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c < 5:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                else:
                    it.setData(Qt.UserRole, sig_key(nuc, sig))
                self.tbl_sig.setItem(r, c, it)
        lines = self.nmr_lines()
        self.txt_line.setHtml("<br>".join(h for _, h in lines) if lines else
                              f"<span style='color:gray'>{_h.escape(T('nmr_text_empty'))}</span>")

    def nmr_lines(self):
        """[(Klartext, HTML)] je Kern, sortiert wie die Spektren (¹H, ¹³C, übrige nach Massenzahl)."""
        return [line for _, line in self.nmr_lines_by_nucleus()]

    def nmr_lines_by_nucleus(self):
        """[(Kern, (Klartext, HTML))] in derselben Reihenfolge (Austauschdatei: Art der Zeile)."""
        assign = self.st.get("assign") or {}
        bl = sorted(self.blocks(), key=lambda b: nuc_rank(b["nucleus"]))
        return [(b["nucleus"], nmr_line(b, assign)) for b in bl if b["signals"]]

    def si_parts(self):
        return self.nmr_lines()

    # -- Aktionen -------------------------------------------------------------------------
    def add_svg(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("nmr_add"), self.main.settings.value("last_dir", ""),
                                             f"{T('nmr_spec_flt')} (*.svg *.emf);;{T('flt_all')}")
        for p in ps:
            self.load_svg(p)

    def load_svg(self, p):
        try:
            info = spectrum_info(p)
        except Exception as ex:
            self.main.error(f"{Path(p).name}: {ex}")
            return None
        p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
        s = new_spectrum(p, info)
        s["nuc_auto"] = bool(info["nuclei"])
        self.st["spectra"].append(s)
        self.st["current"] = s["uid"]
        self.link_raw()
        self.changed()
        return s

    # -- Rohdaten (TopSpin, Mnova) ----------------------------------------------------------
    def add_topspin(self):
        if not self.main.ensure_project():
            return
        d = QFileDialog.getExistingDirectory(self, T("nmr_topspin"), self.main.settings.value("last_dir", ""))
        if d:
            self.import_topspin(d)

    def import_topspin(self, path):
        """TopSpin-Experiment, -Datensatz oder Ordner mit Datensätzen: jedes Experiment ganz ins Projekt nach
        data/nmr/<Art>/<Datensatz>_<Nummer>, dann zu passenden Spektren zuordnen. -> Anzahl neuer Experimente."""
        exps = find_experiments(path)
        if not exps:
            self.main.error(T("nmr_no_acqus", p=Path(path).name))
            return 0
        raws = self.st.setdefault("raw", [])
        n0 = len(raws)
        for e in exps:
            try:
                self.import_experiment(e)
            except Exception as ex:
                self.main.log_signal.emit(f"  {e.name}: {ex}")
        n = len(raws) - n0
        self.main.log_signal.emit(T("nmr_raw_imported", n=n, kinds=", ".join(sorted({r["kind"] for r in raws}))))
        self.link_raw()
        self.changed()
        return n

    def link_raw(self):
        """Spektren ohne Bruker-Ordner mit dem einen passenden Experiment verknüpfen (Parameter, Temperatur)."""
        raws = [r for r in self.st.get("raw") or [] if Path(r["path"]).is_dir()]
        for s in self.spectra():
            if s.get("bruker"):
                continue
            r = match_experiment(s, raws, self.spectra())
            if r is not None:
                s["bruker"] = r["path"]
                s["params"] = acq_params(r["path"])
                if s["params"].get("te"):
                    s["temp"] = round(s["params"]["te"])

    def add_mnova(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("nmr_mnova"), self.main.settings.value("last_dir", ""),
                                             f"Mnova (*.mnova);;{T('flt_all')}")
        for p in ps:
            self.add_mnova_file(p)

    def add_mnova_file(self, p):
        dst = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY) + "/mnova")
        lst = self.st.setdefault("mnova", [])
        if dst not in lst:
            lst.append(dst)
        self.changed()
        return dst

    def remove_raw(self):
        """Eintrag aus der Liste nehmen (die Dateien im Projektordner bleiben liegen)."""
        r = self.tbl_raw.currentRow()
        if r < 0:
            return
        p = self.tbl_raw.item(r, 0).data(Qt.UserRole)
        for s in self.spectra():                         # Verknüpfung lösen
            if s.get("bruker") == p:
                s["bruker"], s["params"] = None, None
        self.st["raw"] = [r for r in self.st.get("raw") or [] if r["path"] != p]
        self.st["mnova"] = [m for m in self.st.get("mnova") or [] if m != p]
        self.changed()

    def raw_rows(self):
        """Zeilen der Rohdaten-Tabelle: (Art, Name, Pulsprogramm, verknüpftes Spektrum, Pfad)."""
        linked = {s.get("bruker"): Path(s["file"]).name for s in self.spectra() if s.get("bruker")}
        rows = []
        for r in self.st.get("raw") or []:
            pp = ""
            try:
                pp = acq_params(r["path"]).get("pulprog", "")
            except Exception:
                pass
            rows.append((r["kind"], r["name"], pp, linked.get(r["path"], ""), r["path"]))
        rows += [("Mnova", Path(m).name, "", "", m) for m in self.st.get("mnova") or []]
        return rows

    def fill_raw(self):
        rows = self.raw_rows()
        self.tbl_raw.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for c, val in enumerate(row[:4]):
                it = QTableWidgetItem(val)
                if c == 0:
                    it.setData(Qt.UserRole, row[4])
                self.tbl_raw.setItem(i, c, it)
        self.tbl_raw.resizeColumnsToContents()

    def remove_spectrum(self):
        s = self.current()
        if s is not None:
            self.st["spectra"] = [x for x in self.st["spectra"] if x["uid"] != s["uid"]]
            self.st["current"] = None
            self.changed()

    def spectrum_selected(self):
        if self._loading:
            return
        rows = self.tbl.selectionModel().selectedRows()
        sp = self.spectra()
        if rows and rows[0].row() < len(sp):
            self.st["current"] = sp[rows[0].row()]["uid"]
            self._loading = True
            self.fill_selected()
            self._loading = False
            self.update_preview()

    def spec_edited(self, *_):
        if self._loading:
            return
        s = self.current()
        if s is None:
            return
        nuc = [parse_nucleus(x) for x in re.split(r"[/,;\s]+", self.ed_nuc.text().strip()) if x]
        if all(nuc) and nuc != (s.get("nuclei") or []):
            s["nuclei"], s["nuc_auto"] = nuc, False
        s["kind"] = self.cmb_kind.currentData()
        if s["kind"] != "1D" and len(s.get("nuclei") or []) == 1:
            s["nuclei"] = s["nuclei"] * 2                          # homonuklear (COSY, NOESY …)
        s["temp"] = self.sp_temp.value()
        fr = [x.strip() for x in self.ed_freq.text().split("/")]
        s["freqs"] = {n: f for n, f in zip(s.get("nuclei") or [], fr) if f}
        s["solvent"] = self.ed_solv.text().strip()
        s.update(struct_on=self.cb_struct.isChecked(), struct_pos=self.cmb_spos.currentData())
        self.st["struct_w"] = self.sp_sw.value()                 # gleich groß in allen Spektren
        self.changed()

    # -- Struktur im Spektrum ---------------------------------------------------------------
    def structure_path(self):
        """Eigene Struktur des Tabs, sonst die der Verbindung (CDXML; gleichnamige ChemDraw-SVG/PDF hat Vorrang)."""
        p = self.st.get("structure") or (getattr(self.main, "compound", None) or {}).get("structure")
        return p if p and Path(p).exists() else None

    def pick_structure(self):
        p, _ = QFileDialog.getOpenFileName(self, T("nmr_struct_pick"), self.main.settings.value("last_dir", ""),
                                           f"{T('nmr_struct_flt')} (*.cdxml *.svg *.pdf *.png);;{T('flt_all')}")
        if p:
            self.st["structure"] = self.main.import_file(p, PRJ.STRUCTURES)      # ChemDraw-Exporte daneben kommen mit
            self.changed()

    def structure_asset(self):
        from elucida.core import images as IMG
        p = self.structure_path()
        if p is None:
            return None
        key = ("nmrstruct", p)
        if key not in self.main.extra_cache:
            self.main.extra_cache[key] = IMG.load_structure(p)
        st = self.main.extra_cache[key]
        return st if st.get("pdf") else None

    def struct_xy(self, s, st):
        """Lage der Struktur (fx, fy); „auto“ sucht die freie Stelle (Ergebnis zwischengespeichert)."""
        width = self.struct_w() / 100
        pos = s.get("struct_pos", "auto")
        if pos != "auto":
            return place_structure(s["file"], st, pos, width, s.get("struct_xy"))
        key = ("nmrauto", s["file"], self.structure_path(), round(width, 3))
        if key not in self.main.extra_cache:
            self.main.extra_cache[key] = place_structure(s["file"], st, "auto", width)
        return self.main.extra_cache[key]

    def figure_svg(self, s):
        """SVG für Word: Mnova-SVG, wahlweise mit eingesetzter Struktur (Datei unter .elucida/nmr)."""
        st = self.structure_asset() if s.get("struct_on", True) else None
        if st is None:
            return s["file"]
        fx, fy = self.struct_xy(s, st)
        width = self.struct_w() / 100
        cdir = PRJ.work_dir(self.main.project_dir or Path(s["file"]).parent, self.STATE_KEY)
        out = cdir / f"{Path(s['file']).stem}_{int(fx * 1000)}_{int(fy * 1000)}_{int(width * 1000)}.svg"
        key = ("nmrcomp", s["file"], self.structure_path(), out.name)
        if key not in self.main.extra_cache or not out.exists():
            self.main.extra_cache[key] = compose_structure(s["file"], st, out, (fx, fy), width)
        return str(out)

    def add_bruker(self):
        s = self.current()
        if s is None:
            return
        d = QFileDialog.getExistingDirectory(self, T("nmr_bruker"), self.main.settings.value("last_dir", ""))
        if d:
            self.set_bruker(s, d)

    def set_bruker(self, s, path):
        d = bruker_dir(path)
        if d is None:
            self.main.error(T("nmr_no_acqus", p=Path(path).name))
            return False
        d = Path(self.import_experiment(d))
        s["bruker"] = str(d)
        s["params"] = acq_params(d)
        self.changed()
        return True

    def import_experiment(self, e):
        """Ein Experiment ganz nach data/nmr/<Art>/<Datensatz>_<Nummer>, in die Rohdaten-Liste -> Pfad im Projekt."""
        kind = experiment_kind(acq_params(e))
        dst = self.main.import_file(str(e), PRJ.data_sub(self.STATE_KEY) + "/" + kind, name=experiment_name(e))
        raws = self.st.setdefault("raw", [])
        if not any(Path(r["path"]) == Path(dst) for r in raws):
            raws.append(dict(path=dst, kind=kind, name=Path(dst).name))
        return dst

    def temp_from_bruker(self):
        s = self.current()
        if s is not None and (s.get("params") or {}).get("te"):
            s["temp"] = round(s["params"]["te"])
            self.changed()

    def text_changed(self):
        self.st["text"] = self.ed_text.toPlainText()
        self._loading = True
        self.fill_signals()
        self._loading = False
        self.update_preview()
        self.main.push_undo()

    def assign_edited(self, item):
        if self._loading or item.column() != 5:
            return
        self.st.setdefault("assign", {})[item.data(Qt.UserRole)] = item.text().strip()
        self._loading = True
        lines = self.nmr_lines()
        self.txt_line.setHtml("<br>".join(h for _, h in lines))
        self._loading = False
        self.main.push_undo()

    def copy_lines(self):
        from elucida.tabs.ir_ea import copy_rich
        lines = self.nmr_lines()
        if lines:
            copy_rich("; ".join(p for p, _ in lines), "; ".join(h for _, h in lines))

    def changed(self):
        self.sync_widgets()
        self.main.push_undo()

    def update_preview(self, xy=None):
        """Vorschau = Spektrum (Mnova-SVG) + Struktur als Bild an ihrer Lage; die Struktur lässt sich ziehen."""
        if "spectra" not in self.st:                   # alter Tab nach dem Schließen der Verbindung (Zustand geleert,
            return                                     # der neue Tab ist schon gebaut): verspätete Vorschau überspringen
        s = self.current()
        self._drag_rect = None
        empty = s is None or not Path(s["file"]).is_file()
        self.preview_stack.setCurrentIndex(0 if empty else 1)
        if empty:
            self.lbl_prev.setPixmap(QPixmap())
            self.lbl_cap.setText("")
            return
        n = self.spectra().index(s) + 1
        if is_emf(s["file"]):                              # EMF: keine eigene Darstellung, geht unverändert nach Word
            self.lbl_prev.setPixmap(QPixmap())
            self.lbl_prev.setText(T("nmr_emf_preview", f=Path(s["file"]).name))
            self.lbl_cap.setText(f"<b>Figure S{n}</b>: " + caption_html(s, self.blocks(), self.compound_name()))
            return
        self.lbl_prev.setText("")
        import pymupdf
        # in Gerätepixeln rendern (HiDPI-Bildschirme), angezeigt in logischen Pixeln
        dpr = max(1.0, self.lbl_prev.devicePixelRatioF())
        cache = self.main.extra_cache
        akey = ("nmraspect", s["file"])
        if akey not in cache:
            r_ = pymupdf.open(s["file"])[0].rect
            cache[akey] = max(r_.width, 1) / max(r_.height, 1)
        # wie CanvasHost: ganzes Bild in die Fläche einpassen (Breite und Höhe), Seitenverhältnis der Mnova-Seite
        aw = max(100.0, self.lbl_prev.width() - 10.0)
        ah = max(80.0, self.lbl_prev.height() - 10.0)
        lw_ = float(int(min(aw, ah * cache[akey])))
        key = ("nmrprev", s["file"], int(lw_ * dpr) // 50)
        if key not in cache:
            page = pymupdf.open(s["file"])[0]
            dpi = int(round(max(60, min(600, lw_ * dpr / max(page.rect.width, 1) * 72))))   # pymupdf: nur ganze Zahl
            pix = page.get_pixmap(dpi=dpi)
            cache[key] = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        base = cache[key]
        pm = QPixmap.fromImage(base).scaledToWidth(int(lw_ * dpr), Qt.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        lh_ = pm.height() / dpr
        st = self.structure_asset() if s.get("struct_on", True) else None
        if st is not None and st.get("rgba") is not None:
            from PySide6.QtGui import QPainter
            fx, fy = xy or self.struct_xy(s, st)
            sw = lw_ * self.struct_w() / 100
            sh = sw * struct_aspect(st)
            a = st["rgba"]
            simg = QImage(a.data, a.shape[1], a.shape[0], a.strides[0], QImage.Format_RGBA8888).copy()
            p = QPainter(pm)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawImage(QRectF(fx * lw_, fy * lh_, sw, sh), simg)
            p.setPen(QColor("#2a7ae2"))
            p.drawRect(QRectF(fx * lw_, fy * lh_, sw, sh))
            p.end()
            self._drag_rect = (fx, fy, sw / lw_, sh / lh_)
        self.lbl_prev.setPixmap(pm)
        self._pm_size = (lw_, lh_)
        n = self.spectra().index(s) + 1
        self.lbl_cap.setText(f"<b>Figure S{n}</b>: " + caption_html(s, self.blocks(), self.compound_name()))

    def _frac(self, pos):
        """Mausposition in der Vorschau -> Anteil (x, y) des Spektrums (Bild ist im Label zentriert)."""
        pw, ph = self._pm_size
        ox = (self.lbl_prev.width() - pw) / 2
        oy = (self.lbl_prev.height() - ph) / 2
        return (pos.x() - ox) / max(pw, 1), (pos.y() - oy) / max(ph, 1)

    def eventFilter(self, obj, ev):
        if obj is self.lbl_prev and ev.type() == QEvent.Resize and getattr(self, "_drag", 1) is None:
            # sofort neu einpassen (auch bei Splitter/Reiter/verzögertem Layout, nicht nur beim Fenster): Bild passt
            # immer zur aktuellen Labelgröße; kein Rückkopplungsrisiko, die Labelgröße hängt nicht vom Pixmap ab
            self.update_preview()
        if obj is not self.lbl_prev or self._drag_rect is None:
            return super().eventFilter(obj, ev)
        t = ev.type()
        if t == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
            fx, fy = self._frac(ev.position())
            x, y, w, h = self._drag_rect
            if x <= fx <= x + w and y <= fy <= y + h:
                self._drag = (fx - x, fy - y)
                self.lbl_prev.setCursor(Qt.ClosedHandCursor)
                return True
        elif t == QEvent.Wheel and self._drag is None:
            fx, fy = self._frac(ev.position())
            x, y, w, h = self._drag_rect
            if x <= fx <= x + w and y <= fy <= y + h:
                steps = ev.angleDelta().y() / 120
                if steps:
                    self.sp_sw.setValue(self.sp_sw.value() + (1 if steps > 0 else -1) * max(1, round(abs(steps))))
                return True
        elif t == QEvent.MouseMove and self._drag is not None:
            fx, fy = self._frac(ev.position())
            x, y, w, h = self._drag_rect
            nx = min(max(fx - self._drag[0], 0.0), 1.0 - w)
            ny = min(max(fy - self._drag[1], 0.0), 1.0 - h)
            self.update_preview((nx, ny))
            return True
        elif t == QEvent.MouseButtonRelease and self._drag is not None:
            self._drag = None
            self.lbl_prev.unsetCursor()
            s = self.current()
            if s is not None and self._drag_rect is not None:
                s["struct_pos"] = "manual"
                s["struct_xy"] = [round(self._drag_rect[0], 4), round(self._drag_rect[1], 4)]
                self.changed()
            return True
        return super().eventFilter(obj, ev)

    # -- Export ---------------------------------------------------------------------------
    def docx_blocks(self, img_dir):
        """Zwei Spektren je Seite: Bild (SVG + PNG-Ersatz) 16 cm breit, darunter „Figure Sn: …“."""
        blocks = []
        name = self.compound_name()
        bl = self.blocks()
        from elucida.si import lines as SI
        for s in (x for x in self.spectra() if Path(x["file"]).is_file()):
            if is_emf(s["file"]):                          # unverändert (Vektor in Word, ohne eingesetzte Struktur)
                w, h = s.get("size") or emf_info(s["file"])["size_cm"]
                blocks += [("image", s["file"], FIG_W_CM, FIG_W_CM * h / w), ("figcap", caption_html(s, bl, name))]
                continue
            f = self.figure_svg(s)
            png = svg_png(f, Path(img_dir) / (Path(f).stem + "_nmr.png"))
            w, h = s.get("size") or spectrum_info(s["file"])["size_cm"]
            blocks += [("image", str(png), FIG_W_CM, FIG_W_CM * h / w, f), ("figcap", caption_html(s, bl, name))]
        return SI.two_per_page(blocks)

    def export_dialog(self, path=None):
        """Word-Datei mit allen Spektren und Unterschriften, dazu die NMR-Zeile als Text (SI/<Name>_NMR.*)."""
        from elucida.si import lines as SI
        if not self.main.ensure_project():
            return None
        if not self.spectra() and not self.nmr_lines():
            self.main.error(T("nmr_empty"))
            return None
        out = PRJ.export_dir(self.main.project_dir, PRJ.SI_DIR)
        base = PRJ.export_stem(self.compound_name() or self.main.export_name(), self.STATE_KEY)
        path = Path(path) if path else out / f"{base}.docx"
        try:
            SI.write_docx(path, self.docx_blocks(PRJ.work_dir(self.main.project_dir, self.STATE_KEY)))
        except PermissionError:
            self.main.error(T("report_locked", p=path))
            return None
        lines = self.nmr_lines()
        if lines:
            (out / f"{base}.txt").write_text("; ".join(p for p, _ in lines) + "\n", encoding="utf-8")
        self.main.log_signal.emit(T("saved", p=str(path)))
        return path

