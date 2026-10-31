"""elucida/formats/cdxml.py - CDXML (ChemDraw) direkt zeichnen: Bindungen, Atomlabels, Texte, Reaktionspfeile.

Für Reaktionsschemata ohne ChemDraw-Export daneben: RDKit zeichnet nur die Moleküle (ohne Pfeil und Bedingungen)
und löst Abkürzungen wie TMS auf. Hier wird alles an den Koordinaten der CDXML gezeichnet, Texte wie geschrieben
(Formelstil: Ziffern tiefgestellt), Linienbreite, Bindungsabstand und Schrift aus den Dokumentangaben.
Nicht unterstützte Objekte (Bilder, Klammern, Kurvenpfeile …) werden gemeldet statt geraten.
"""
from __future__ import annotations

import html
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

PAD = 2.0                                        # Rand um den Inhalt [pt]


# ---------------------------------------------------------------------------- Text
def _font(bold):
    import pymupdf
    return pymupdf.Font("hebo" if bold else "helv")          # Metrik wie Arial/Helvetica


def _formula_parts(text):
    """Formelstil (face 96): Ziffern nach Buchstaben/Klammern tiefgestellt (K2CO3, n-Bu4NPF6), sonst normal."""
    out = []
    for m in re.finditer(r"(?P<sub>(?<=[A-Za-z)\]])\d+)|.", text, re.S):
        sub = m.group("sub") is not None
        if out and out[-1][1] == sub:
            out[-1][0] += m.group(0)
        else:
            out.append([m.group(0), sub])
    return [(t, "sub" if s else "") for t, s in out]


def _runs(t_el, size0=10.0, face0=0, color0="#000000", colors=None):
    """<t> -> Zeilen aus Läufen (Text, Größe, fett, kursiv, sub/sup, Farbe)."""
    lines = [[]]
    for s in t_el.iter("s"):
        txt = s.text or ""
        size = float(s.get("size", size0))
        face = int(s.get("face", face0))
        col = _color(s.get("color"), colors) or color0
        bold, italic = bool(face & 1), bool(face & 2)
        if face & 96 == 96:
            parts = _formula_parts(txt)
        else:
            parts = [(txt, "sub" if face & 32 else "sup" if face & 64 else "")]
        for part, va in parts:
            for k, piece in enumerate(part.replace("\r", "\n").split("\n")):
                if k:
                    lines.append([])
                if piece:
                    lines[-1].append((piece, size, bold, italic, va, col))
    return [ln for ln in lines] if any(lines) else []


def _run_width(r):
    txt, size, bold, _, va, _ = r
    return _font(bold).text_length(txt, fontsize=size * (0.75 if va else 1.0))


def _text_svg(t_el, colors, justify_key="Justification", size0=10.0, face0=0):
    """<t> als SVG-Textelemente; Lage über die BoundingBox der CDXML (x) und p (Grundlinie der ersten Zeile)."""
    lines = _runs(t_el, size0, face0, "#000000", colors)
    if not lines:
        return ""
    p = [float(v) for v in t_el.get("p", "0 0").split()[:2]]
    bb = [float(v) for v in t_el.get("BoundingBox", "").split()] or None
    just = (t_el.get(justify_key) or t_el.get("CaptionJustification") or t_el.get("LabelJustification")
            or t_el.get("Justification") or "Left")
    maxsize = max(r[1] for ln in lines for r in ln)
    lh = t_el.get("LineHeight")
    lh = float(lh) if lh and lh not in ("auto", "variable") else 1.15 * maxsize
    out = []
    for k, ln in enumerate(lines):
        w = sum(_run_width(r) for r in ln)
        if bb:
            x0, x1 = min(bb[0], bb[2]), max(bb[0], bb[2])
            x = (x0 + x1 - w) / 2 if just == "Center" else (x1 - w if just == "Right" else x0)
        else:
            x = p[0] - w / 2 if just == "Center" else (p[0] - w if just == "Right" else p[0])
        y = p[1] + k * lh
        for txt, size, bold, italic, va, col in ln:
            fs = size * (0.75 if va else 1.0)
            dy = 0.25 * size if va == "sub" else (-0.4 * size if va == "sup" else 0.0)
            out.append(f'<text x="{x:.2f}" y="{y + dy:.2f}" font-family="Arial, Helvetica, sans-serif" '
                       f'font-size="{fs:.2f}"' + (' font-weight="bold"' if bold else "")
                       + (' font-style="italic"' if italic else "")
                       + f' fill="{col}">{html.escape(txt).replace(" ", chr(160))}</text>')   # Leerzeichen bleiben
            x += _run_width((txt, size, bold, italic, va, col))
    return "".join(out)


# ---------------------------------------------------------------------------- Farben, Geometrie
def _color(idx, colors):
    """CDXML-Farbindex: 0 = schwarz, 1 = weiß, ab 2 die Einträge der Farbtabelle."""
    if idx is None:
        return None
    i = int(idx)
    if i == 0:
        return "#000000"
    if i == 1:
        return "#ffffff"
    if colors and 0 <= i - 2 < len(colors):
        return colors[i - 2]
    return "#000000"


def _pt(s):
    v = [float(x) for x in s.split()]
    return v[0], v[1]


def _exit_t(a, b, rect):
    """Anteil t in [0, 1], an dem die Strecke a->b das Rechteck (um a) verlässt; 0, wenn a draußen liegt."""
    x0, y0, x1, y1 = rect
    if not (x0 <= a[0] <= x1 and y0 <= a[1] <= y1):
        return 0.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    ts = []
    if dx > 1e-9:
        ts.append((x1 - a[0]) / dx)
    elif dx < -1e-9:
        ts.append((x0 - a[0]) / dx)
    if dy > 1e-9:
        ts.append((y1 - a[1]) / dy)
    elif dy < -1e-9:
        ts.append((y0 - a[1]) / dy)
    return min([t for t in ts if t >= 0] or [0.0])


def _clip(a, b, ra, rb):
    """Strecke an den Labelrechtecken beider Enden kürzen -> (a', b') oder None (ganz verdeckt)."""
    t0 = _exit_t(a, b, ra) if ra else 0.0
    t1 = 1.0 - (_exit_t(b, a, rb) if rb else 0.0)
    if t1 - t0 < 0.02:
        return None
    lerp = lambda t: (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)  # noqa: E731
    return lerp(t0), lerp(t1)


def _line(a, b, w, col, dash=None):
    return (f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="{col}" '
            f'stroke-width="{w:.2f}" stroke-linecap="round"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")


def _poly(pts, col):
    return '<polygon points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + f'" fill="{col}" stroke="none"/>'


# Elementsymbole und übliche Wertigkeit – nur für CDXML ohne Atomlabels (z. B. von RDKit geschrieben)
_SYMBOLS = {1: "H", 3: "Li", 5: "B", 7: "N", 8: "O", 9: "F", 11: "Na", 12: "Mg", 13: "Al", 14: "Si", 15: "P",
            16: "S", 17: "Cl", 19: "K", 26: "Fe", 29: "Cu", 30: "Zn", 33: "As", 34: "Se", 35: "Br", 44: "Ru", 45: "Rh",
            46: "Pd", 47: "Ag", 50: "Sn", 52: "Te", 53: "I", 77: "Ir", 78: "Pt", 79: "Au", 80: "Hg"}
_VALENCE = {1: 1, 5: 3, 7: 3, 8: 2, 9: 1, 14: 4, 15: 3, 16: 2, 17: 1, 34: 2, 35: 1, 52: 2, 53: 1}


def _make_label(n, nodes, bonds, size):
    """Atomlabel für einen Knoten ohne <t> (Heteroatom): Symbol + implizite H (NumHydrogens oder Wertigkeit),
    H auf der Seite ohne Bindungen; Lage wie bei ChemDraw (erstes Symbol mittig auf dem Atom)."""
    z = int(n.get("Element", 6))
    if z == 6 or z not in _SYMBOLS:
        return None
    sym = _SYMBOLS[z]
    ch = int(n.get("Charge", 0) or 0)
    if n.get("NumHydrogens") is not None:
        nh = int(n.get("NumHydrogens"))
    elif z in _VALENCE:
        used = sum({"2": 2, "3": 3, "1.5": 1.5}.get(b.get("Order", "1"), 1) for b in bonds
                   if n.get("id") in (b.get("B"), b.get("E")))
        nh = max(0, int(round(_VALENCE[z] + (ch if z in (7, 15) else -abs(ch)) - used)))
    else:
        nh = 0
    x, y = nodes[n.get("id")]
    nb = [nodes[b.get("E") if b.get("B") == n.get("id") else b.get("B")] for b in bonds
          if n.get("id") in (b.get("B"), b.get("E"))]
    h = ("H" + (str(nh) if nh > 1 else "")) if nh else ""
    left = bool(h) and nb and all(q[0] > x + 1e-6 for q in nb)          # alle Bindungen rechts -> „HO“
    text = (h + sym) if left else (sym + h)
    f = _font(False)
    w_sym = f.text_length(sym, fontsize=size)
    w_all = sum(_run_width((t_, size, False, False, va, "")) for t_, va in _formula_parts(text))
    x0 = x - w_sym / 2 - (w_all - w_sym if left else 0.0)
    t = ET.Element("t", {"p": f"{x0:.2f} {y + 0.35 * size:.2f}", "LabelJustification": "Left",
                         "BoundingBox": f"{x0:.2f} {y - 0.4 * size:.2f} {x0 + w_all:.2f} {y + 0.4 * size:.2f}"})
    ET.SubElement(t, "s", {"size": str(size), "face": "96"}).text = text
    return t


# ---------------------------------------------------------------------------- Zeichnen
class _Doc:
    def __init__(self, root):
        self.root = root
        self.lw = float(root.get("LineWidth", 0.6))
        self.bold_w = float(root.get("BoldWidth", 2.0))
        self.spacing = float(root.get("BondSpacing", 18)) / 100.0
        self.hash = float(root.get("HashSpacing", 2.5))
        self.margin = float(root.get("MarginWidth", 1.6))
        self.label_size = float(root.get("LabelSize", 10))
        self.caption_size = float(root.get("CaptionSize", 10))
        ct = root.find("colortable")
        self.colors = ["#%02x%02x%02x" % tuple(int(round(float(c.get(k, 0)) * 255)) for k in "rgb")
                       for c in (ct.findall("color") if ct is not None else [])]
        self.out, self.notes, self.pts = [], [], []

    def add_pts(self, *pts):
        self.pts.extend(pts)

    # -- Moleküle ----------------------------------------------------------------------------------
    def fragment(self, frag):
        nodes, labels = {}, {}
        for n in frag.findall("n"):
            if n.get("NodeType") != "ExternalConnectionPoint" and n.get("p") is not None:
                nodes[n.get("id")] = _pt(n.get("p"))
        all_bonds = frag.findall("b")
        for n in frag.findall("n"):                   # nur oberste Ebene: Abkürzungen (TMS) bleiben Label
            if n.get("id") not in nodes:
                continue
            t = n.find("t")
            if t is None or not "".join(s.text or "" for s in t.iter("s")).strip():
                t = _make_label(n, nodes, all_bonds, self.label_size)
            if t is not None and "".join(s.text or "" for s in t.iter("s")).strip():
                bb = [float(v) for v in t.get("BoundingBox", "").split()]
                if bb:
                    m = self.margin
                    labels[n.get("id")] = (min(bb[0], bb[2]) - m, min(bb[1], bb[3]) - m,
                                           max(bb[0], bb[2]) + m, max(bb[1], bb[3]) + m)
                    self.add_pts((bb[0], bb[1]), (bb[2], bb[3]))
                self.out.append(_text_svg(t, self.colors, "LabelJustification", self.label_size, 96))
            self.add_pts(nodes[n.get("id")])
            ch = int(n.get("Charge", 0) or 0)
            if ch and not (t is not None and re.search(r"[+\-−]", "".join(s.text or "" for s in t.iter("s")))):
                x, y = nodes[n.get("id")]
                r = labels.get(n.get("id"))
                x, y = (r[2], r[1] + 2) if r else (x + 3, y - 3)
                sign = ("" if abs(ch) == 1 else str(abs(ch))) + ("+" if ch > 0 else "−")
                self.out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, Helvetica, sans-serif" '
                                f'font-size="{0.75 * self.label_size:.2f}">{sign}</text>')
        bonds = [b for b in frag.findall("b") if b.get("B") in nodes and b.get("E") in nodes]
        adj = {k: set() for k in nodes}
        for b in bonds:
            adj[b.get("B")].add(b.get("E"))
            adj[b.get("E")].add(b.get("B"))
        for b in bonds:
            self.bond(b, nodes, labels, adj)

    def ring_center(self, u, v, nodes, adj, max_len=8):
        """Mitte des kleinsten Rings mit der Bindung u-v (Breitensuche ohne die Bindung selbst) oder None."""
        prev, front = {u: None}, [u]
        for _ in range(max_len):
            nxt = []
            for a in front:
                for c in adj[a]:
                    if (a == u and c == v) or c in prev:
                        continue
                    prev[c] = a
                    if c == v:
                        path, k = [], v
                        while k is not None:
                            path.append(k)
                            k = prev[k]
                        xs = [nodes[k][0] for k in path]
                        ys = [nodes[k][1] for k in path]
                        return sum(xs) / len(xs), sum(ys) / len(ys)
                    nxt.append(c)
            front = nxt
        return None

    def bond(self, b, nodes, labels, adj):
        u, v = b.get("B"), b.get("E")
        a, c = nodes[u], nodes[v]
        ra, rc = labels.get(u), labels.get(v)
        col = _color(b.get("color"), self.colors) or "#000000"
        order = b.get("Order", "1")
        disp = b.get("Display", "")
        dx, dy = c[0] - a[0], c[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L                       # „rechts“ in Bildschirmkoordinaten (y nach unten)
        s = self.spacing * L
        lw = self.lw

        def off(p, k):
            return p[0] + nx * k, p[1] + ny * k

        def seg(p, q, w=lw, dash=None, ra_=ra, rc_=rc):
            cl = _clip(p, q, ra_, rc_)
            if cl:
                self.out.append(_line(cl[0], cl[1], w, col, dash))

        if disp in ("WedgeBegin", "WedgeEnd", "WedgedHashBegin", "WedgedHashEnd"):
            p, q = (a, c) if disp.endswith("Begin") else (c, a)
            rp, rq = (ra, rc) if disp.endswith("Begin") else (rc, ra)
            cl = _clip(p, q, rp, rq)
            if not cl:
                return
            p, q = cl
            hw = 0.75 * self.bold_w
            if disp.startswith("Wedge") and "Hash" not in disp:
                self.out.append(_poly([p, off(q, hw), off(q, -hw)], col))
            else:
                n_ = max(3, int(math.hypot(q[0] - p[0], q[1] - p[1]) / self.hash))
                for k in range(1, n_ + 1):
                    t = k / n_
                    m = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                    self.out.append(_line(off(m, hw * t), off(m, -hw * t), lw, col))
            return
        if order in ("2", "1.5"):
            pos = b.get("DoublePosition")
            side = 0
            if pos in ("Right", "Left"):
                side = 1 if pos == "Right" else -1
            elif pos != "Center":
                rc_ = self.ring_center(u, v, nodes, adj)
                if rc_ is not None:
                    side = 1 if (rc_[0] - a[0]) * nx + (rc_[1] - a[1]) * ny > 0 else -1
                elif len(adj[u]) > 1 and len(adj[v]) > 1:
                    w_ = sum((nodes[k][0] - a[0]) * nx + (nodes[k][1] - a[1]) * ny
                             for k in (adj[u] | adj[v]) - {u, v})
                    side = 1 if w_ > 0 else -1
            if side == 0:                              # mittig (z. B. C=O am Rand)
                seg(off(a, s / 2), off(c, s / 2))
                seg(off(a, -s / 2), off(c, -s / 2), dash="1.5,1.5" if order == "1.5" else None)
                return
            seg(a, c, dash="1.5,1.5" if disp == "Dash" else None)
            ins = s * 0.577                            # innere Linie wie im Sechsring eingerückt
            ka = ins if len(adj[u]) > 1 and not ra else 0.0
            kc = ins if len(adj[v]) > 1 and not rc else 0.0
            ia = (a[0] + dx / L * ka, a[1] + dy / L * ka)
            ic = (c[0] - dx / L * kc, c[1] - dy / L * kc)
            seg(off(ia, side * s), off(ic, side * s), dash="1.5,1.5" if order == "1.5" else None,
                ra_=_shift(ra, nx * side * s, ny * side * s), rc_=_shift(rc, nx * side * s, ny * side * s))
            return
        if order == "3":
            seg(a, c)
            seg(off(a, s), off(c, s))
            seg(off(a, -s), off(c, -s))
            return
        if disp == "Bold":
            seg(a, c, w=self.bold_w)
        elif disp in ("Dash", "Hash"):
            seg(a, c, dash="1.5,1.5")
        else:
            if disp == "Wavy":
                self.notes.append("wavy bond drawn straight")
            seg(a, c)

    # -- Schema --------------------------------------------------------------------------------------
    def arrow(self, el):
        if el.get("Head3D") and el.get("Tail3D"):
            head = _pt(el.get("Head3D"))
            tail = _pt(el.get("Tail3D"))
        else:
            return
        if el.get("AngularSize") and abs(float(el.get("AngularSize"))) > 1e-3:
            self.notes.append("curved arrow drawn straight")
        col = _color(el.get("color"), self.colors) or "#000000"
        lw = self.lw
        hl = float(el.get("HeadSize", 1000)) / 100.0 * lw
        hc = float(el.get("ArrowheadCenterSize", 875)) / 100.0 * lw
        hw = float(el.get("ArrowheadWidth", 250)) / 100.0 * lw
        self.add_pts(head, tail)
        dx, dy = head[0] - tail[0], head[1] - tail[1]
        L = math.hypot(dx, dy) or 1.0
        ux, uy, nx, ny = dx / L, dy / L, -dy / L, dx / L

        def tip(p, kind, sign):
            """Pfeilspitze an p in Richtung sign·u; kind Full/HalfLeft/HalfRight."""
            bx, by = p[0] - sign * ux * hl, p[1] - sign * uy * hl
            cx, cy = p[0] - sign * ux * hc, p[1] - sign * uy * hc
            left, right = (bx + nx * hw * 2, by + ny * hw * 2), (bx - nx * hw * 2, by - ny * hw * 2)
            if kind == "HalfLeft":
                right = (cx, cy)
            elif kind == "HalfRight":
                left = (cx, cy)
            self.out.append(_poly([p, left, (cx, cy), right], col))
            return (cx, cy)
        h_kind, t_kind = el.get("ArrowheadHead", "Full"), el.get("ArrowheadTail")
        a, b = tail, head
        if h_kind and h_kind != "None":
            b = tip(head, h_kind, 1)
        if t_kind and t_kind != "None":
            a = tip(tail, t_kind, -1)
        self.out.append(_line(a, b, lw, col))

    def graphic(self, el):
        if el.get("SupersededBy"):
            return
        kind = el.get("GraphicType")
        bb = [float(v) for v in el.get("BoundingBox", "").split()]
        if kind == "Line" and len(bb) == 4:
            head, tail = (bb[0], bb[1]), (bb[2], bb[3])
            if el.get("ArrowType") in ("FullHead", "HalfHead", "Resonance", "Equilibrium", "RetroSynthetic"):
                fake = ET.Element("arrow", {"Head3D": f"{head[0]} {head[1]} 0", "Tail3D": f"{tail[0]} {tail[1]} 0"})
                if el.get("ArrowType") == "Resonance":
                    fake.set("ArrowheadTail", "Full")
                self.arrow(fake)
            else:
                self.add_pts(head, tail)
                self.out.append(_line(head, tail, self.lw, "#000000"))
        elif kind == "Symbol" and el.get("SymbolType") in ("Plus", "Minus") and len(bb) >= 2:
            sign = "+" if el.get("SymbolType") == "Plus" else "−"
            self.out.append(f'<text x="{bb[0]:.2f}" y="{bb[1]:.2f}" font-family="Arial, Helvetica, sans-serif" '
                            f'font-size="{0.75 * self.label_size:.2f}">{sign}</text>')
        elif kind == "Rectangle" and len(bb) == 4:
            x0, x1 = sorted((bb[0], bb[2]))
            y0, y1 = sorted((bb[1], bb[3]))
            self.add_pts((x0, y0), (x1, y1))
            self.out.append(f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" '
                            f'fill="none" stroke="#000000" stroke-width="{self.lw:.2f}"/>')
        else:
            self.notes.append(f"graphic '{kind}' not drawn")

    def caption(self, t):
        bb = [float(v) for v in t.get("BoundingBox", "").split()]
        if bb:
            self.add_pts((bb[0], bb[1]), (bb[2], bb[3]))
        self.out.append(_text_svg(t, self.colors, "CaptionJustification", self.caption_size, 0))


def _shift(rect, dx, dy):
    return None if rect is None else (rect[0] + dx, rect[1] + dy, rect[2] + dx, rect[3] + dy)


def render_svg(path):
    """CDXML -> (SVG-Text, Hinweise auf nicht gezeichnete Objekte)."""
    root = ET.parse(str(path)).getroot()
    d = _Doc(root)
    def draw(parent):
        for el in parent:
            tag = el.tag
            if tag == "fragment":
                d.fragment(el)
            elif tag == "t":
                d.caption(el)
            elif tag == "arrow":
                d.arrow(el)
            elif tag == "graphic":
                d.graphic(el)
            elif tag == "group":                   # gruppierte Bedingungen (auch verschachtelt): alles darin zeichnen
                draw(el)
            elif tag in ("scheme", "chemicalproperty", "objecttag"):
                continue
            else:
                d.notes.append(f"<{tag}> not drawn")
    for page in root.iter("page"):
        draw(page)
    if not d.pts:
        raise ValueError(f"{Path(path).name}: nothing to draw")
    xs = [p[0] for p in d.pts]
    ys = [p[1] for p in d.pts]
    x0, y0, x1, y1 = min(xs) - PAD, min(ys) - PAD, max(xs) + PAD, max(ys) + PAD
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1 - x0:.2f}pt" height="{y1 - y0:.2f}pt" '
           f'viewBox="{x0:.2f} {y0:.2f} {x1 - x0:.2f} {y1 - y0:.2f}">' + "".join(d.out) + "</svg>")
    return svg, sorted(set(d.notes))


def scheme_texts(path):
    """Texte über/unter den Reaktionspfeilen (ReactionStepObjectsAbove/BelowArrow) -> [Text, …]."""
    root = ET.parse(str(path)).getroot()
    texts = {t.get("id"): "".join(s.text or "" for s in t.iter("s")) for t in root.iter("t") if t.get("id")}
    out = []
    for step in root.iter("step"):
        for key in ("ReactionStepObjectsAboveArrow", "ReactionStepObjectsBelowArrow"):
            for i in (step.get(key) or "").split():
                if i in texts and texts[i].strip():
                    out.append(texts[i].strip())
    return out


SOLVENTS = {"MeOH": "CH4O", "EtOH": "C2H6O", "iPrOH": "C3H8O", "THF": "C4H8O", "DCM": "CH2Cl2", "CH2Cl2": "CH2Cl2",
            "MeCN": "C2H3N", "CH3CN": "C2H3N", "DMF": "C3H7NO", "DMSO": "C2H6OS", "Et2O": "C4H10O",
            "toluene": "C7H8", "PhMe": "C7H8", "acetone": "C3H6O", "H2O": "H2O", "hexane": "C6H14",
            "n-hexane": "C6H14", "pentane": "C5H12", "EtOAc": "C4H8O2", "CHCl3": "CHCl3", "benzene": "C6H6",
            "dioxane": "C4H8O2", "1,4-dioxane": "C4H8O2", "pyridine": "C5H5N", "DME": "C4H10O2", "MTBE": "C5H12O"}
# Reagenzkürzel, die sich sonst als Summenformel lesen ließen (NBS = N+B+S)
REAGENTS = {"NBS": "C4H4BrNO2", "NCS": "C4H4ClNO2", "NIS": "C4H4INO2", "DCC": "C13H22N2", "DIC": "C7H14N2",
            "PCC": "C5H6ClCrNO3", "CDI": "C7H6N4O", "COD": "C8H12", "NMO": "C5H11NO2", "DIBAL": "C8H19Al"}
_CONDITION = re.compile(r"^(r\.?\s?t\.?|reflux|overnight|o\.?n\.?|hv|hν|Δ|N2|Ar|air|dark|in the dark|"
                        r"[-−–]?\d+(?:[.,]\d+)?\s*(?:°C|K|h|min|d|s|days?|hours?|bar|atm|W)\b.*|"
                        r"\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?\s*(?:°C|h|min).*)$", re.I)


def scheme_reagents(path):
    """Reagenzien und Lösungsmittel aus den Pfeiltexten -> [(Name, Formel oder "", Rolle)], Bedingungen
    (rt, 1 h, 80 °C …) fallen weg. „K2CO3 (1.2 eq.)“ -> ("K2CO3", "K2CO3", "reagent")."""
    out = []
    for txt in scheme_texts(path):
        for part in re.split(r"[,;\n]+(?![^(]*\))", txt):
            part = part.strip()
            if not part or _CONDITION.match(part):
                continue
            name = re.sub(r"\s*\([^)]*\)\s*$", "", part).strip()
            if not name or _CONDITION.match(name):
                continue
            if name in SOLVENTS:
                out.append((name, SOLVENTS[name], "other"))
                continue
            formula = REAGENTS.get(name) or \
                (name if re.fullmatch(r"(?:[A-Z][a-z]?\d*|\((?:[A-Z][a-z]?\d*)+\)\d*)+", name) else "")
            out.append((name, formula, "reagent"))
    return out


# ChemDraw-Reagenzientabelle: SGPropertyType -> Bedeutung (Rohwerte mol, g, mL, mol/L, g/mL; Anteile 1 = 100 %)
GRID_MW, GRID_LIMITING, GRID_EQ, GRID_SAMPLE_MASS, GRID_WEIGHT, GRID_VOLUME, GRID_MOLARITY, GRID_DENSITY = \
    2, 4, 6, 7, 8, 9, 10, 12
GRID_REACTANT_MASS, GRID_PURITY, GRID_PRODUCT_MASS = 14, 18, 19


def stoich_grid(path):
    """Reagenzientabelle (<stoichiometrygrid>) in der CDXML des Schemas -> [dict(grid, formula, reactant, values)]
    je Verbindung (Beschriftungsspalten fallen weg); values: Typ -> (Rohwert, vom Nutzer eingegeben)."""
    out = []
    for g in ET.parse(str(path)).getroot().iter("stoichiometrygrid"):
        for c in g.iter("sgcomponent"):
            if c.get("ComponentIsHeader") == "yes":
                continue
            formula, vals = "", {}
            for d in c.iter("sgdatum"):
                t = int(d.get("SGPropertyType") or 0)
                if t == 1:                               # Formel nur als Text
                    formula = "".join(s.text or "" for s in d.iter("s")).strip()
                    continue
                try:
                    vals[t] = (float(d.get("SGDataValue")), d.get("IsEdited") == "yes")
                except (TypeError, ValueError):
                    continue
            out.append(dict(grid=g.get("id"), formula=formula, reactant=c.get("ComponentIsReactant") == "yes",
                            values=vals))
    return out
