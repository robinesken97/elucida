"""
elucida/app/welcome.py - Startbildschirm: Übersicht der zuletzt geöffneten Projekte (Verbindung, Struktur, Analytik,
Stand) als Galerie oder Matrix, Seitenleiste. Daten aus der Projektdatei, Strukturbild aus dem beim Speichern abgelegten Vorschaubild (.elucida/thumb.png,
write_thumb) – der Startbildschirm rendert nichts selbst und bleibt schnell.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import yaml
from PySide6.QtCore import QSize, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

from elucida.app import canvas_theme as CANVAS
from elucida.app.canvas_theme import register as register_canvas
from elucida.app import project as PRJ
from elucida.app import publication as PUB
from elucida.app import style as STYLE
from elucida.app.i18n import T

# Analytik im Projekt -> Abzeichen (Reihenfolge wie die Tabs/SI)
BADGES = (("syn", "Synthese", "Synthesis"), ("nmr", "NMR", "NMR"), ("ir", "IR", "IR"), ("ms", "MS", "MS"),
          ("uvvis", "UV-Vis", "UV-Vis"), ("uvkin", "UV-Vis-Kinetik", "UV-Vis kinetics"),
          ("fluo", "Fluoreszenz", "Fluorescence"), ("cv", "CV", "CV"),
          ("sec", "SEC", "SEC"), ("hcell", "H-Cell", "H-Cell"), ("epr", "EPR", "EPR"), ("xray", "X-Ray", "X-ray"), ("dft", "DFT", "DFT"))


THUMB = "thumb.png"                   # in .elucida/: Struktur der Verbindung, beim Speichern erzeugt
THUMB_PX = 320                        # Galerie: scharf auch auf HiDPI
SIDE_W = 240                          # Seitenleiste (Fenster bleibt ab ~960 px bedienbar)
CARD_W, CARD_H, CARD_GAP = 236, 244, 14
THUMB_H = 148                         # Strukturbild der Galerie
CHECK_W, MORE_MIN_W = 40, 860         # Matrix: Spaltenbreite, ab dieser Zeilenbreite „Weitere Analytik“
SHORT = {"1H": "¹H", "13C": "¹³C", "2D": "2D", "ms": "HRMS", "ir": "IR", "mp": "m.p."}
MORE = ("uvvis", "uvkin", "fluo", "cv", "sec", "hcell", "epr", "xray", "dft")
REDO_COLOR = "#d9a400"                # Pflichtteil fehlt, Substanz ist aber noch da
_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def thumb_path(pdir) -> Path:
    return Path(pdir) / PRJ.WORK / THUMB


def write_thumb(pdir, structure, log=None) -> Path | None:
    """Vorschaubild der Struktur fürs Projekt (nur neu, wenn die Struktur neuer ist als das Bild). Transparenter Rand
    weg, auf THUMB_PX eingepasst. Fehler nur ins Protokoll – Speichern bricht nie daran ab."""
    if not structure or not Path(structure).exists():
        return None
    out = thumb_path(pdir)
    try:
        src_t = max(s.stat().st_mtime for s in Path(structure).parent.glob(Path(structure).stem + ".*"))
        import numpy as np
        from PIL import Image
        if out.exists() and out.stat().st_mtime >= src_t:
            with Image.open(out) as old:                       # kleinere Bilder alter Versionen einmal ersetzen
                if max(old.size) >= THUMB_PX:
                    return out
        from elucida.core import images as IMG
        res = IMG.load_structure(structure, target_px=600)
        a = res.get("rgba")
        if a is None:
            return None
        a = np.asarray(a)
        ys, xs = np.nonzero(a[..., 3] > 10)
        if len(xs):
            a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        im = Image.fromarray(a, "RGBA")
        im.thumbnail((THUMB_PX, THUMB_PX), Image.LANCZOS)
        PRJ.work_dir(pdir)
        im.save(out)
        return out
    except Exception as e:
        if log:
            log(f"thumb: {e}")
        return None


def project_info(path) -> dict | None:
    """Kurzinfo eines Projektordners: name (Verbindung, sonst Ordner), folder, path, modified (datetime),
    badges (Schlüssel aus BADGES). None, wenn kein Projekt."""
    pdir = PRJ.is_project(path)
    if pdir is None:
        return None
    pf = PRJ.project_file(pdir)
    try:
        raw = pf.read_text(encoding="utf-8")
        st = yaml.safe_load(raw) or {}
    except Exception:
        raw, st = "", {}
    g = lambda *ks: _get(st, *ks)                                  # noqa: E731
    has = {
        "syn": bool(g("syn", "proc") or g("syn", "scheme")),
        "nmr": bool(g("nmr", "spectra") or g("nmr", "raw") or g("nmr", "mnova")),
        "ir": bool(g("irms", "ir_file") or g("irms", "ir_pdf")),
        "ms": bool(g("hrms", "ms_file") or g("hrms", "ms_raw") or g("irms", "ms_file") or g("irms", "ms_raw")),
        "uvvis": bool(g("eps", "files")),
        "uvkin": bool(g("uvkin", "entries")),
        "fluo": bool(g("fluo", "abs_file") or g("fluo", "em_file")),
        "cv": bool(g("cv", "files")),
        "sec": bool(g("sec", "spec_files") or g("sec", "dta")),
        "hcell": bool(g("hcell", "entries")),
        "epr": bool(g("epr", "entries")),
        "xray": bool(g("xray", "entries")),
        "dft": bool(g("dft", "entries")),
    }
    name = (g("compound", "name") or g("syn", "name") or "").strip()
    note = (g("compound", "note") or "").strip()
    th = thumb_path(pdir)
    check = PUB.checklist_of(st)
    from elucida.exchange.datapack import CODE_RE      # Laborkürzel (AB-1-234) in Dateinamen, Vorschrift … – für die Suche
    comp = g("compound") or {}
    return dict(path=str(pdir), folder=pdir.name, name=name or pdir.name, has_compound=bool(name), note=note,
                formula=str(comp.get("formula") or ""), lit=str(comp.get("lit") or ""),
                sample=bool(comp.get("sample")), sample_no=str(comp.get("sample_no") or ""),
                labbook=str(comp.get("labbook") or ""),
                codes=sorted(set(CODE_RE.findall(raw))), check=check,
                modified=dt.datetime.fromtimestamp(pf.stat().st_mtime), badges=[k for k, _, _ in BADGES if has[k]],
                thumb=str(th) if th.exists() else None)


def _get(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def relative_time(t: dt.datetime, now: dt.datetime | None = None) -> str:
    """„heute 14:32“, „gestern 09:10“, „vor 5 Tagen“, sonst das Datum."""
    now = now or dt.datetime.now()
    days = (now.date() - t.date()).days
    if days == 0:
        return T("time_today", t=t.strftime("%H:%M"))
    if days == 1:
        return T("time_yesterday", t=t.strftime("%H:%M"))
    if 1 < days < 7:
        return T("time_days", n=days)
    return t.strftime("%d.%m.%Y")


def badge_label(key):
    from elucida.app.i18n import get_lang
    row = next(b for b in BADGES if b[0] == key)
    return row[1] if get_lang() == "de" else row[2]


def short_path(p) -> str:
    """Pfad mit ~ für den Benutzerordner."""
    p, home = str(p), str(Path.home())
    return "~" + p[len(home):] if p.startswith(home) else p


def info_matches(info, text) -> bool:
    """Suche (Startbildschirm, Projektseite): Name/Nummer, Ordner, Notiz, Summenformel, Literatur, Projekt,
    Laborkürzel aus der Verbindung, Analytik; mehrere Wörter müssen alle passen, Groß-/Kleinschreibung egal."""
    hay = " ".join([info.get("name", ""), Path(info.get("path", "")).name, info.get("note", ""),
                    info.get("formula", ""), info.get("lit", ""), info.get("publication", ""), info.get("group", ""),
                    info.get("sample_no", ""), info.get("labbook", "")]
                   + list(info.get("codes") or []) + [badge_label(k) for k in info.get("badges") or []]).lower()
    return all(w in hay for w in text.lower().split())


def formula_text(f) -> str:
    """Summenformel für die Anzeige mit tiefgestellten Zahlen."""
    return re.sub(r"(?<=[A-Za-z)])\d+", lambda m: m.group().translate(_SUB), f)


def info_line(info) -> str:
    return "  ·  ".join(x for x in (formula_text(info.get("formula", "")), info.get("labbook", ""), info.get("note", "")) if x)


def required(check):
    return PUB.REQUIRED_KNOWN if check["known"] else PUB.REQUIRED_NEW


def status_text(check) -> str:
    if not check["missing"]:
        return T("welcome_complete")
    if not check["have"]:
        return T("welcome_no_analytics")
    return T("welcome_missing", items=", ".join(SHORT[k] for k in check["missing"]))


def scaled(path, w, h, ratio):
    pm = QPixmap(path).scaled(int(w * ratio), int(h * ratio), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pm.setDevicePixelRatio(ratio)
    return pm


def card_picture(path, h=THUMB_H):
    """Bild oben in einer Karte, auf Weiß wie in ChemDraw; bei dunklem Canvas invertiert (nur Anzeige)."""
    pic = QLabel(objectName="cardThumb", alignment=Qt.AlignCenter)
    pic.setFixedHeight(h)
    if path:
        pic.setPixmap(scaled(path, 200, h - 44, max(1.0, pic.devicePixelRatioF())))   # Luft über und unter der Struktur
    return canvas_picture(pic)


def canvas_picture(pic):
    """Dunkler Canvas: Linien hell direkt auf der Karte statt schwarzer Kasten; heller Canvas: auf Weiß."""
    if STYLE._mode == "light":                          # helle Ansicht: immer dunkle Linien auf Weiß, auch bei dunklem Canvas
        return pic
    if CANVAS._dark:
        pic.setStyleSheet("background: transparent;")
    return register_canvas(pic)


class ElidedLabel(QLabel):
    """Einzeilig, in der Mitte gekürzt (…), wenn der Platz nicht reicht – die Zeile wird nie breiter als die Liste."""
    MODE = Qt.ElideMiddle

    def __init__(self, text="", **kw):
        super().__init__(**kw)
        self._full = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)
        self.setToolTip(text)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.setText(self.fontMetrics().elidedText(self._full, self.MODE, max(10, self.width())))


class EndElided(ElidedLabel):
    MODE = Qt.ElideRight


class SideRow(QPushButton):
    """Zeile der Seitenleiste: Symbol, Text, rechts die Anzahl."""

    def __init__(self, text, count="", icon=None, lead=None, checkable=True):
        super().__init__(objectName="sideItem", checkable=checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(text)
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 0, 10, 0)
        h.setSpacing(9)
        if icon:
            lead = QLabel()
            lead.setPixmap(STYLE.pixmap(icon, 17, STYLE.colors()["accent" if checkable else "text2"]))
        if lead is not None:
            lead.setAttribute(Qt.WA_TransparentForMouseEvents)
            h.addWidget(lead)
        self.label = EndElided(text)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        h.addWidget(self.label, 1)
        self.count = QLabel(str(count), objectName="sideCount")
        self.count.setAttribute(Qt.WA_TransparentForMouseEvents)
        h.addWidget(self.count)


TAB_OF = {"syn": "syn", "nmr": "nmr", "ir": "irms", "ms": "hrms", "uvvis": "eps", "uvkin": "uvkin", "fluo": "fluo", "cv": "cv",
          "sec": "sec", "hcell": "hcell", "epr": "epr", "xray": "xray", "dft": "dft"}      # Abzeichen -> Tab


class NavTab(QPushButton):
    """Tab der Leiste: mit Daten heller Text, leer gedimmt (kein Zeichen neben dem Text, der Tab bleibt symmetrisch)."""

    def __init__(self, text):
        super().__init__(text, objectName="navTab", checkable=True)
        self.has_data = False

    def set_data(self, on):
        if on != self.has_data:
            self.has_data = on
            self.setProperty("hasData", on)
            self.style().unpolish(self)
            self.style().polish(self)


class NavScroll(QScrollArea):
    """Tab-Leiste, die schmaler werden darf als ihr Inhalt: 16 Tabs erzwangen sonst die Fensterbreite (1.1.0: 1461 px,
    unter Windows 2048 px – breiter als ein Laptop-Bildschirm). Passt nicht alles, lässt sich die Leiste waagerecht
    schieben (Mausrad, Trackpad) und zeigt am abgeschnittenen Rand einen Pfeil; der gewählte Tab bleibt sichtbar."""
    ARROW_W = 26

    def __init__(self, inner):
        super().__init__()
        self.setWidget(inner)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("navScroll")
        inner.setObjectName("navInner")
        self.arrows = []
        for d, sym in ((-1, "‹"), (1, "›")):
            b = QPushButton(sym, self, objectName="navMore")
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setToolTip(T("nav_more_tip"))
            b.clicked.connect(lambda _=False, d=d: self.step(d))
            b.hide()
            self.arrows.append(b)
        sb = self.horizontalScrollBar()
        sb.valueChanged.connect(self._sync)
        sb.rangeChanged.connect(self._sync)

    def sizeHint(self):
        return self.widget().sizeHint()

    def minimumSizeHint(self):
        return QSize(240, self.widget().minimumSizeHint().height())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._sync()

    def _sync(self, *_):
        sb, (left, right) = self.horizontalScrollBar(), self.arrows
        left.setVisible(sb.value() > sb.minimum())
        right.setVisible(sb.value() < sb.maximum())
        left.setGeometry(0, 0, self.ARROW_W, self.height() - 1)          # −1: Linie unter der Leiste bleibt frei
        right.setGeometry(self.width() - self.ARROW_W, 0, self.ARROW_W, self.height() - 1)
        for b in self.arrows:
            b.raise_()

    def step(self, d):
        sb = self.horizontalScrollBar()
        sb.setValue(sb.value() + d * int(0.6 * self.viewport().width()))

    def wheelEvent(self, ev):
        d = ev.angleDelta()
        sb = self.horizontalScrollBar()
        if sb.maximum() > sb.minimum() and (d.x() or d.y()):
            sb.setValue(sb.value() - (d.x() or d.y()))
            ev.accept()
        else:
            ev.ignore()

    def reveal(self, widget):
        """Gewählten Tab ganz zeigen (mit Luft für den Pfeil am Rand)."""
        self.ensureWidgetVisible(widget, self.ARROW_W + 12, 0)


SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


class NameTab(NavTab):
    """Tab „Verbindung“: Nummer · Summenformel (Zahlen tiefgestellt), nie gekürzt (Nutzerwunsch 2026-11-11). Nummer = die
    der SI (Feld Name), sonst die Laborbuchnummer, sonst der Ordner. Ohne Summenformel ein Platzhalter, gedimmt wie ein
    leerer Tab."""

    def __init__(self):
        super().__init__("")
        self.full_text = ""

    def set_compound(self, number, formula):
        self.full_text = " · ".join(x for x in (number, (formula or "").translate(SUBSCRIPT) or T("compound_tab_empty")) if x)
        self.setText(self.full_text)
        self.set_data(bool(formula))
        self.updateGeometry()

    def sizeHint(self):
        """Breite für die angewählte Schrift (halbfett, breiter als die normale): sonst schneidet der Tab den Text ab,
        sobald man ihn anwählt."""
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QFont, QFontMetrics
        s = super().sizeHint()
        bold = QFont(self.font())
        bold.setWeight(QFont.DemiBold)
        extra = QFontMetrics(bold).horizontalAdvance(self.text()) - self.fontMetrics().horizontalAdvance(self.text())
        return QSize(s.width() + max(0, extra) + 2, s.height())

    def minimumSizeHint(self):
        return self.sizeHint()


class Ring(QWidget):
    """Fortschritt eines Projekts: vollständige Verbindungen als Ring."""

    def __init__(self, done, n):
        super().__init__()
        self.frac = done / n if n else 0
        self.setFixedSize(17, 17)

    def paintEvent(self, ev):
        c = STYLE.colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(2, 2, 13, 13)
        p.setPen(QPen(QColor(c["border_strong"]), 3))
        p.drawEllipse(r)
        p.setPen(QPen(QColor(c["ok"]), 3))
        p.drawArc(r, 90 * 16, int(-self.frac * 360 * 16))


class Ticks(QWidget):
    """Pflichtteile der Checkliste als Balken auf der Karte."""

    def __init__(self, check):
        super().__init__()
        self.done = [k in check["have"] for k in required(check)]
        self.setFixedSize(15 * len(self.done), 12)

    def paintEvent(self, ev):
        c = STYLE.colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        for i, on in enumerate(self.done):
            p.setBrush(QColor(c["ok" if on else "border_strong"]))
            p.drawRoundedRect(QRectF(i * 15, 4, 13, 4), 2, 2)


class CheckDot(QWidget):
    """Zelle der Matrix: gefüllt mit Haken = vorhanden, Kreis = fehlt, Strich = nicht nötig, feiner Punkt = weitere
    Methode ohne Daten (Form, nicht nur Farbe)."""

    def __init__(self, state, tip, redo=False):
        super().__init__()
        self.state, self.redo = state, redo
        self.setFixedSize(CHECK_W, 22)
        self.setToolTip(tip)

    def paintEvent(self, ev):
        c = STYLE.colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m = QPointF(self.width() / 2, self.height() / 2)
        if self.state == "none":                             # weitere Methode ohne Daten: ruhiger Platzhalter im Raster
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(c["border_strong"]))
            p.drawEllipse(m, 1.8, 1.8)
        elif self.state == "na":
            p.setPen(QPen(QColor(c["border_strong"]), 1.5))
            p.drawLine(m + QPointF(-4.5, 0), m + QPointF(4.5, 0))
        elif self.state == "off":
            p.setPen(QPen(QColor(REDO_COLOR if self.redo else c["border_strong"]), 1.5))
            p.drawEllipse(m, 9, 9)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(c["ok"]))
            p.drawEllipse(m, 10, 10)
            pen = QPen(QColor(c["on_ok"]), 2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPolyline([m + QPointF(-4.5, 0.3), m + QPointF(-1.2, 3.6), m + QPointF(4.6, -3)])


class Gallery(QWidget):
    """Karten im Raster: so viele Spalten, wie in die Breite passen; columns=1 für Zeilen."""

    def __init__(self):
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.items, self.cols, self.single = [], 0, False

    def _columns(self):
        return 1 if self.single else max(1, (self.width() + CARD_GAP) // (CARD_W + CARD_GAP))

    def set_single(self, on):
        """Eine Spalte als zusammenhängende Tabelle (Rahmen ums Ganze), sonst Kartenraster."""
        self.single = on
        self.setObjectName("matrixPanel" if on else "")
        self.setAttribute(Qt.WA_StyledBackground, on)
        self.style().unpolish(self)
        self.style().polish(self)
        self.grid.setSpacing(0 if on else CARD_GAP)
        self.grid.setContentsMargins(*((1, 1, 1, 1) if on else (0, 0, 0, 0)))

    def add(self, w):
        self.items.append(w)
        self._reflow()

    def set_items(self, widgets):
        self.remove_all()
        self.items = list(widgets)
        self._reflow()

    def remove_all(self):
        for w in self.items:
            self.grid.removeWidget(w)
        self.items = []

    def _reflow(self):
        self.cols = self._columns()
        for w in self.items:
            self.grid.removeWidget(w)
        for i, w in enumerate(self.items):
            self.grid.addWidget(w, i // self.cols, i % self.cols)
        for c in range(max(self.grid.columnCount(), self.cols)):       # leere Spalten behalten ihre Breite
            on = c < self.cols
            self.grid.setColumnStretch(c, 1 if on else 0)
            self.grid.setColumnMinimumWidth(c, 0 if self.single or not on else CARD_W)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._columns() != self.cols:
            self._reflow()


class ClickCard(QWidget):
    """Karte/Zeile: Linksklick öffnet (info["path"])."""
    opened = Signal(str)

    def _setup(self, info):
        self.info = info
        self.setObjectName("recentRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.opened.emit(self.info["path"])
        super().mouseReleaseEvent(ev)

    def matches(self, text):
        return info_matches(self.info, text)


def status_row(check):
    h = QHBoxLayout()
    h.setSpacing(8)
    h.addWidget(Ticks(check))
    lab = EndElided(status_text(check), objectName="statusOk" if not check["missing"] else "statusOpen")
    lab.setToolTip(status_text(check))
    h.addWidget(lab, 1)
    return h


class CompoundCard(ClickCard):
    """Karte der Galerie: Struktur, Name, Stand, Formel/Notiz, Projekt, was noch fehlt."""

    def __init__(self, info):
        super().__init__()
        self._setup(info)
        self.setFixedHeight(CARD_H)
        self.setMinimumWidth(CARD_W)
        v = QVBoxLayout(self)
        v.setContentsMargins(1, 1, 1, 1)
        v.setSpacing(0)
        if info.get("thumb"):
            v.addWidget(card_picture(info["thumb"]))
        else:
            pic = QLabel((info["name"][:2] or "?").upper(), objectName="recentMono", alignment=Qt.AlignCenter)
            pic.setFixedHeight(THUMB_H)
            v.addWidget(pic)
        b = QVBoxLayout()
        b.setContentsMargins(12, 9, 12, 10)
        b.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(6)
        top.addWidget(EndElided(info["name"], objectName="cardName"), 1)
        if info.get("sample"):
            top.addWidget(sample_label(info))
        when = QLabel(relative_time(info["modified"]), objectName="recentWhen")
        when.setToolTip(info["modified"].strftime("%d.%m.%Y %H:%M"))
        top.addWidget(when)
        b.addLayout(top)
        b.addWidget(EndElided(info_line(info) or short_path(Path(info["path"]).parent), objectName="recentSub"))
        b.addWidget(EndElided(info.get("publication", ""), objectName="recentSub"))
        b.addStretch(1)
        b.addLayout(status_row(info["check"]))
        v.addLayout(b, 1)


def sample_label(info):
    lab = QLabel("⚗" + (" " + info["sample_no"] if info.get("sample_no") else ""), objectName="recentNote")
    lab.setToolTip(T("compound_sample_badge"))
    return lab


# Matrix der Verbindungsliste (Nutzerwunsch 2026-11-12, „stimmig“): rechts vom Namen ein einziges Raster mittiger
# Spalten – Pflichtteile, dann jede weitere Methode als eigene Spalte mit Punkt (statt eines freien Textes), „Geändert“.
# Links die Verbindung selbst (Nummer, Bild, Name) linksbündig wie ein Zeilenkopf.
SHORT_MORE = {"uvvis": "UV-Vis", "uvkin": ("Kinetik", "Kinet."), "fluo": "Fluor.", "cv": "CV", "sec": "SEC",
              "hcell": "H-Cell", "epr": "EPR", "xray": "X-Ray", "dft": "DFT"}      # (DE, EN), wo sie sich unterscheiden


def short_more(key):
    from elucida.app.i18n import get_lang
    v = SHORT_MORE[key]
    return v if isinstance(v, str) else v[0 if get_lang() == "de" else 1]
GROUP_GAP = 10                     # Luft zwischen Pflichtteilen und weiteren Methoden
CHECK_W_MAX = 56                   # breite Fenster: Spalten wachsen bis hierher, erst danach der Name
NAME_MIN, NAME_TARGET = 140, 260   # Platz für Name und Formel: mindestens / bevor die Spalten wachsen
ROW_MIN_W = 640                    # Mindestbreite von Kopf und Zeile: nie die der Matrix – sonst erzwingen die festen
# Spalten die Fensterbreite (1.1.0: Fenster ließ sich nicht unter 1461 px ziehen, unter Windows 2048 px) und die
# Umschaltung auf den Text bzw. die schmalen Spalten käme nie zum Zug. Was passt, entscheidet allein fit_more.


def _row_min(widget, base):
    return QSize(ROW_MIN_W, base.height())


def fit_more(row):
    """Raster der Zeile (Kopf und Zeilen rechnen gleich): passen alle Methoden als Spalten, stehen sie als Punkte da
    und teilen sich mit den Pflichtteilen eine Spaltenbreite, die mit dem Fenster wächst; in schmalen Fenstern
    stattdessen die Methoden als gekürzter Text („Weitere Analytik“), darunter gar nicht."""
    w, n = row.width(), len(row.dots) + len(row.opt)

    def base(cells, cw):                                 # Breite der Zeile ohne den Namen
        return 28 + (34 if row.numbered else 0) + 84 + 96 + 12 * (cells + 2) + GROUP_GAP + cells * cw
    matrix = base(n, CHECK_W) + NAME_MIN <= w
    cw = max(CHECK_W, min(CHECK_W_MAX, (w - base(n, 0) - NAME_TARGET) // n)) if matrix else CHECK_W
    for d in row.opt:
        d.setVisible(matrix)
    row.more.setVisible(not matrix and w >= MORE_MIN_W)
    for d in row.dots + row.opt:
        d.setFixedWidth(cw)


class MatrixHeader(QWidget):
    """Kopf der Matrix (gleiche Spalten wie RecentRow)."""

    def __init__(self, numbered=False):
        super().__init__()
        self.numbered = numbered
        self.setFixedHeight(32)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 0, 14, 0)
        h.setSpacing(12)
        if numbered:
            h.addSpacing(22 + 12)
        h.addSpacing(84 + 12)
        h.addWidget(QLabel(T("col_compound"), objectName="recentHint"), 1)
        self.dots = []
        for k in PUB.REQUIRED_NEW:
            lab = QLabel(SHORT[k], objectName="recentHint", alignment=Qt.AlignCenter)
            lab.setFixedWidth(CHECK_W)
            h.addWidget(lab)
            self.dots.append(lab)
        h.addSpacing(GROUP_GAP)
        self.opt = []                                    # weitere Methoden: je eine Spalte (Kurzname, ganzer im Tooltip)
        for k in MORE:
            lab = QLabel(short_more(k), objectName="recentHint", alignment=Qt.AlignCenter)
            lab.setToolTip(badge_label(k))
            lab.setFixedWidth(CHECK_W)
            h.addWidget(lab)
            self.opt.append(lab)
        self.more = QLabel(T("col_more"), objectName="recentHint", alignment=Qt.AlignCenter)   # schmale Fenster: Text
        self.more.setFixedWidth(230)                     # „UV-Vis · Fluoreszenz · CV“ ungekürzt
        h.addWidget(self.more)
        when = QLabel(T("col_changed"), objectName="recentHint", alignment=Qt.AlignCenter)
        when.setFixedWidth(96)
        h.addWidget(when)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        fit_more(self)

    def minimumSizeHint(self):
        return _row_min(self, super().minimumSizeHint())


class RecentRow(ClickCard):
    """Zeile der Matrix (Liste und Projektseite): Struktur, Verbindung, Pflichtteile, weitere Analytik, Stand."""

    def __init__(self, info, number=None):
        super().__init__()
        self.numbered = number is not None
        self._setup(info)
        self.setObjectName("matrixRow")
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 6, 14, 6)
        h.setSpacing(12)
        if number is not None:                         # Projektseite: Platz in der Reihenfolge
            lab = QLabel(str(number), objectName="recentWhen", alignment=Qt.AlignCenter)
            lab.setFixedWidth(22)
            h.addWidget(lab)
        if info.get("thumb"):                          # Struktur (beim Speichern abgelegt), auf Weiß wie in ChemDraw
            pic = QLabel(objectName="recentThumb", alignment=Qt.AlignCenter)
            pic.setFixedSize(84, 60)
            pic.setPixmap(scaled(info["thumb"], 78, 54, max(1.0, self.devicePixelRatioF())))
            canvas_picture(pic)
        else:                                          # ohne Strukturbild: Kürzel in gleich großer Kachel
            pic = QLabel((info["name"][:2] or "?").upper(), objectName="recentMono", alignment=Qt.AlignCenter)
            pic.setFixedSize(84, 60)
        h.addWidget(pic)
        v = QVBoxLayout()
        v.setSpacing(2)
        title = QHBoxLayout()
        title.setSpacing(6)
        title.addWidget(QLabel(info["name"], objectName="recentTitle"))
        check = info["check"]
        if check["known"]:
            tag = QLabel(T("tag_known"), objectName="recentBadge")
            tag.setToolTip(check.get("lit", ""))
            title.addWidget(tag)
        if info.get("sample"):                         # Substanz übrig: ⚗ + Probennummer (wie Characterization)
            title.addWidget(sample_label(info))
        title.addStretch(1)
        v.addLayout(title)
        parts = [info_line(info), info.get("publication", "")]
        sub = EndElided("  ·  ".join(x for x in parts if x) or short_path(Path(info["path"]).parent), objectName="recentSub")
        sub.setToolTip(info["path"])
        v.addWidget(sub)
        h.addLayout(v, 1)
        need = required(check)
        self.dots = []
        for k in PUB.REQUIRED_NEW:
            have, req = k in check["have"], k in need
            state, key = ("on", "check_have") if have else ("off", "check_missing") if req else ("na", "check_na")
            self.dots.append(CheckDot(state, T(key, item=SHORT[k]), redo=bool(check.get("sample"))))
            h.addWidget(self.dots[-1])
        h.addSpacing(GROUP_GAP)
        self.opt = []                                    # weitere Methoden: Haken = Daten da, feiner Punkt = keine
        for k in MORE:
            on = k in info["badges"]
            self.opt.append(CheckDot("on" if on else "none", T("check_have" if on else "check_none", item=badge_label(k))))
            h.addWidget(self.opt[-1])
        self.more = EndElided(" · ".join(badge_label(k) for k in MORE if k in info["badges"]) or "–", objectName="recentSub")
        self.more.setFixedWidth(230)                     # „UV-Vis · Fluoreszenz · CV“ ungekürzt
        self.more.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)      # „Ignored“ bekäme neben Dehnfeldern 0 px
        self.more.setToolTip(self.more._full)
        self.more.setAlignment(Qt.AlignCenter)
        h.addWidget(self.more)
        when = QLabel(relative_time(info["modified"]), objectName="recentWhen", alignment=Qt.AlignCenter)
        when.setFixedWidth(96)
        when.setToolTip(info["modified"].strftime("%d.%m.%Y %H:%M"))
        h.addWidget(when)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        fit_more(self)

    def minimumSizeHint(self):
        return _row_min(self, super().minimumSizeHint())

    draggable = False                                  # Projektseite: Reihenfolge per Ziehen ändern
    DRAG_MIME = "application/x-elucida-compound"

    def mousePressEvent(self, ev):
        self._press = ev.position().toPoint() if ev.button() == Qt.LeftButton else None
        self._dragged = False
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        from PySide6.QtCore import QMimeData
        from PySide6.QtGui import QDrag
        from PySide6.QtWidgets import QApplication
        p0 = getattr(self, "_press", None)
        if self.draggable and p0 is not None and (ev.position().toPoint() - p0).manhattanLength() >= \
                QApplication.startDragDistance():
            self._dragged = True
            md = QMimeData()
            md.setData(self.DRAG_MIME, self.info["path"].encode("utf-8"))
            drag = QDrag(self)
            drag.setMimeData(md)
            drag.setPixmap(self.grab().scaledToWidth(min(420, self.width()), Qt.SmoothTransformation))
            drag.setHotSpot(p0 * min(420, self.width()) / max(1, self.width()))
            self._press = None
            drag.exec(Qt.MoveAction)
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton and not getattr(self, "_dragged", False):
            self.opened.emit(self.info["path"])
        self._press = None
        QWidget.mouseReleaseEvent(self, ev)
