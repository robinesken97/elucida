"""
elucida/app/welcome.py - Startbildschirm: Übersicht der zuletzt geöffneten Projekte (Verbindung, Struktur, Analytik,
Stand). Daten aus der Projektdatei, Strukturbild aus dem beim Speichern abgelegten Vorschaubild (.elucida/thumb.png,
write_thumb) – der Startbildschirm rendert nichts selbst und bleibt schnell.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from elucida.app import project as PRJ
from elucida.app.i18n import T

# Analytik im Projekt -> Abzeichen (Reihenfolge wie die Tabs/SI)
BADGES = (("syn", "Synthese", "Synthesis"), ("nmr", "NMR", "NMR"), ("ir", "IR", "IR"), ("ms", "MS", "MS"),
          ("uvvis", "UV-Vis", "UV-Vis"), ("fluo", "Fluoreszenz", "Fluorescence"), ("cv", "CV", "CV"),
          ("sec", "SEC", "SEC"), ("epr", "EPR", "EPR"), ("xray", "X-Ray", "X-ray"), ("dft", "DFT", "DFT"))


THUMB = "thumb.png"                   # in .elucida/: Struktur der Verbindung, beim Speichern erzeugt
THUMB_PX = 128


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
        if out.exists() and out.stat().st_mtime >= src_t:
            return out
        import numpy as np
        from PIL import Image
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
        st = yaml.safe_load(pf.read_text(encoding="utf-8")) or {}
    except Exception:
        st = {}
    g = lambda *ks: _get(st, *ks)                                  # noqa: E731
    has = {
        "syn": bool(g("syn", "proc") or g("syn", "scheme")),
        "nmr": bool(g("nmr", "spectra") or g("nmr", "raw") or g("nmr", "mnova")),
        "ir": bool(g("irms", "ir_file") or g("irms", "ir_pdf")),
        "ms": bool(g("hrms", "ms_file") or g("hrms", "ms_raw") or g("irms", "ms_file") or g("irms", "ms_raw")),
        "uvvis": bool(g("eps", "files")),
        "fluo": bool(g("fluo", "abs_file") or g("fluo", "em_file")),
        "cv": bool(g("cv", "files")),
        "sec": bool(g("sec", "spec_files") or g("sec", "dta")),
        "epr": bool(g("epr", "entries")),
        "xray": bool(g("xray", "entries")),
        "dft": bool(g("dft", "entries")),
    }
    name = (g("compound", "name") or g("syn", "name") or "").strip()
    note = (g("compound", "note") or "").strip()
    th = thumb_path(pdir)
    return dict(path=str(pdir), folder=pdir.name, name=name or pdir.name, has_compound=bool(name), note=note,
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


class ElidedLabel(QLabel):
    """Einzeilig, in der Mitte gekürzt (…), wenn der Platz nicht reicht – die Zeile wird nie breiter als die Liste."""

    def __init__(self, text="", **kw):
        super().__init__(**kw)
        self._full = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)
        self.setToolTip(text)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.setText(self.fontMetrics().elidedText(self._full, Qt.ElideMiddle, max(10, self.width())))


class RecentRow(QWidget):
    """Eine Zeile der Projektliste: Verbindung, Ordner/Pfad, Analytik-Abzeichen, zuletzt geändert."""
    opened = Signal(str)

    def __init__(self, info):
        super().__init__()
        self.info = info
        self.setObjectName("recentRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 10, 14, 10)
        h.setSpacing(14)
        if info.get("thumb"):                          # Struktur (beim Speichern abgelegt), auf Weiß wie in ChemDraw
            pic = QLabel(objectName="recentThumb", alignment=Qt.AlignCenter)
            pic.setFixedSize(64, 64)
            dpr = max(1.0, self.devicePixelRatioF())
            pm = QPixmap(info["thumb"]).scaled(int(58 * dpr), int(58 * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pm.setDevicePixelRatio(dpr)
            pic.setPixmap(pm)
        else:                                          # ohne Strukturbild: Kürzel in gleich großer Kachel
            pic = QLabel((info["name"][:2] or "?").upper(), objectName="recentMono", alignment=Qt.AlignCenter)
            pic.setFixedSize(64, 64)
        h.addWidget(pic)
        v = QVBoxLayout()
        v.setSpacing(2)
        title = QHBoxLayout()
        title.setSpacing(8)
        name_lbl = QLabel(info["name"], objectName="recentTitle")
        title.addWidget(name_lbl)
        if info.get("note"):                           # Notiz zur Verbindung neben dem Namen
            title.addWidget(ElidedLabel("·  " + info["note"], objectName="recentNote"), 1)
        else:
            title.addStretch(1)
        parent = short_path(Path(info["path"]).parent)
        sub = ElidedLabel((info["folder"] + "  ·  " if info["has_compound"] else "") + parent, objectName="recentSub")
        sub.setToolTip(info["path"])
        badges = QHBoxLayout()
        badges.setSpacing(4)
        for k in info["badges"]:
            badges.addWidget(QLabel(badge_label(k), objectName="recentBadge"))
        if not info["badges"]:
            badges.addWidget(QLabel(T("recent_empty_project"), objectName="recentSub"))
        badges.addStretch(1)
        v.addLayout(title)
        v.addWidget(sub)
        v.addLayout(badges)
        h.addLayout(v, 1)
        when = QLabel(relative_time(info["modified"]), objectName="recentWhen", alignment=Qt.AlignRight | Qt.AlignTop)
        when.setToolTip(info["modified"].strftime("%d.%m.%Y %H:%M"))
        h.addWidget(when, 0, Qt.AlignTop)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.opened.emit(self.info["path"])
        super().mouseReleaseEvent(ev)

    def matches(self, text):
        t = text.strip().lower()
        return not t or any(t in s.lower() for s in (self.info["name"], self.info["path"], self.info.get("note", ""))) or any(
            t in badge_label(k).lower() for k in self.info["badges"])
