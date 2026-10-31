"""elucida/tabs/other.py - Tab „Weitere“: fremde Abbildungen (PDF/SVG/PNG aus anderen Programmen) unverändert in die SI,
je mit Unterschrift und Kapitel (bestehendes SI-Kapitel oder eigene Überschrift; in der Gesamt-SI eigenes Kapitel am
Ende). Seitenverhältnis bleibt, zwei Abbildungen je Seite wie alle anderen (SI.two_per_page). Nie im Datenpaket.
"""
from __future__ import annotations

import html
import shutil
import uuid
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLineEdit, QListWidget, QPushButton,
                               QVBoxLayout)

from elucida.app import project as PRJ
from elucida.app.i18n import T
from elucida.app.style import make_form
from elucida.tabs import base as TABS

EXTS = (".pdf", ".svg", ".png")
# Kapitel der SI (Schlüssel wie si/publication_si.SECTIONS) für fremde Abbildungen; „new“ = eigene Überschrift
CHAPTERS = (("nmr", "NMR Spectra"), ("irms", "IR and Mass Spectra"), ("uvvis", "UV-Vis Spectroscopy"),
            ("epr", "EPR Spectroscopy"), ("cv", "Cyclic Voltammetry"), ("sec", "Spectroelectrochemistry"),
            ("xray", "X-Ray Characterization Data"), ("dft", "Computational Section"), ("new", ""))
RENDER_DPI = 200


def render_rgba(path, dpi=RENDER_DPI):
    """Erste Seite (PDF/SVG) bzw. das Bild (PNG) als RGBA-Array für die Vorschau/den PNG-Ersatz."""
    import pymupdf
    if Path(path).suffix.lower() == ".png":
        from PIL import Image
        with Image.open(path) as im:
            return np.asarray(im.convert("RGBA"))
    with pymupdf.open(str(path)) as doc:
        pix = doc[0].get_pixmap(dpi=int(dpi), alpha=True)
        return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)


def natural_cm(path):
    """Natürliche Größe [cm] (Breite, Höhe): PDF/SVG aus der Seite (pt), PNG aus Pixeln und dpi (sonst 300 dpi)."""
    if Path(path).suffix.lower() == ".png":
        from PIL import Image
        with Image.open(path) as im:
            dpi = (im.info.get("dpi") or (300, 300))[0] or 300
            return im.width / dpi * 2.54, im.height / dpi * 2.54
    import pymupdf
    with pymupdf.open(str(path)) as doc:
        r = doc[0].rect
        return r.width / 72 * 2.54, r.height / 72 * 2.54


def word_image(path, out_dir, stem):
    """-> ("image", PNG, b, h, SVG|None) für SI.write_docx: PNG unverändert; SVG unverändert + PNG-Ersatz; PDF als
    Vektor (SVG, Text als Pfade) + PNG-Ersatz. Breite höchstens Satzspiegel, Seitenverhältnis wie die Datei."""
    import pymupdf
    p, out_dir = Path(path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    w, h = natural_cm(p)
    if w > TABS.SI_MAX_W_CM:
        w, h = TABS.SI_MAX_W_CM, h * TABS.SI_MAX_W_CM / w
    ext = p.suffix.lower()
    if ext == ".png":
        return ("image", str(p), w, h, None)
    png = out_dir / f"{stem}.png"
    with pymupdf.open(str(p)) as doc:
        doc[0].get_pixmap(dpi=300, alpha=False).save(str(png))
        if ext == ".svg":
            svg = p
        else:
            svg = out_dir / f"{stem}.svg"
            svg.write_text(doc[0].get_svg_image(text_as_path=True), encoding="utf-8")
    return ("image", str(png), w, h, str(svg))


def heading_of(e):
    return (e.get("heading") or "").strip() if e.get("chapter") == "new" else ""


class OtherTab(TABS.FigureTab):
    """Tab „Weitere“ (ganz am Ende): Abbildungen anderer Programme mit Unterschrift und Kapitel."""
    STATE_KEY = "other"
    GUIDE, GUIDE_ACTION = "other", ("guide_add", "add_files")
    RESET_KEEP = ("entries", "current")
    DEFAULT_STATE = dict(TABS.COMMON_DEFAULTS, entries=[], current=None)

    def common_box(self):                     # Dateien bleiben unverändert: keine Achsen/Größe/Formate
        g = QGroupBox()
        g.hide()
        return g

    def _sync_common(self):
        pass

    def collect_common(self):
        pass

    def arrange(self):
        pass

    def build_controls(self):
        g = QGroupBox(T("other_group"))
        v = QVBoxLayout(g)
        self.lst = QListWidget()
        self.lst.setMinimumHeight(120)
        self.lst.currentRowChanged.connect(self.entry_selected)
        v.addWidget(self.lst)
        row = QHBoxLayout()
        for txt, fn in ((T("other_add"), self.add_files), (T("other_up"), self.move_up), (T("remove"), self.remove)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.lv.addWidget(g)
        self.det = QGroupBox(T("other_details"))
        f = make_form(self.det)
        self.ed_cap = QLineEdit()
        self.ed_cap.setPlaceholderText(T("other_cap_ph"))
        self.ed_cap.setToolTip(T("other_cap_tip"))
        f.addRow(T("other_cap"), self.ed_cap)
        self.cmb_chap = QComboBox()
        for k, title in CHAPTERS:
            self.cmb_chap.addItem(title or T("other_new_heading"), k)
        f.addRow(T("other_chapter"), self.cmb_chap)
        self.ed_head = QLineEdit()
        self.ed_head.setPlaceholderText(T("other_heading_ph"))
        f.addRow(T("other_heading"), self.ed_head)
        self.lv.addWidget(self.det)
        self.ed_cap.editingFinished.connect(self.details_changed)
        self.ed_head.editingFinished.connect(self.details_changed)
        self.cmb_chap.currentIndexChanged.connect(self.details_changed)
        self.sync_widgets()

    # -- Daten ------------------------------------------------------------------------------
    def entries(self):
        return self.st["entries"]

    def entry(self):
        return next((e for e in self.entries() if e["uid"] == self.st.get("current")), None)

    def add_files(self):
        if not self.main.ensure_project():
            return
        ps, _ = QFileDialog.getOpenFileNames(self, T("other_add"), self.main.settings.value("last_dir", ""),
                                             f"{T('other_flt')} (*.pdf *.svg *.png);;{T('flt_all')}")
        self.load_files(ps)

    def load_files(self, ps):
        for p in ps:
            if Path(p).suffix.lower() not in EXTS:
                self.main.error(T("other_bad_ext", name=Path(p).name))
                continue
            p = self.main.import_file(p, PRJ.data_sub(self.STATE_KEY))
            try:
                natural_cm(p)
            except Exception as ex:
                self.main.error(f"{Path(p).name}: {ex}")
                continue
            e = dict(uid=uuid.uuid4().hex[:8], file=p, caption="", chapter="new", heading="")
            self.entries().append(e)
            self.st["current"] = e["uid"]
        self.sync_widgets()
        self.render()

    def move_up(self):
        es, e = self.entries(), self.entry()
        i = es.index(e) if e in es else -1
        if i > 0:
            es[i - 1], es[i] = es[i], es[i - 1]
            self.sync_widgets()
            self.render()

    def remove(self):
        e = self.entry()
        if e is not None:
            self.st["entries"] = [x for x in self.entries() if x is not e]
            self.st["current"] = None
            self.sync_widgets()
            self.render()

    def entry_selected(self, i):
        if self._loading or not 0 <= i < len(self.entries()):
            return
        self.st["current"] = self.entries()[i]["uid"]
        self.sync_widgets()
        self.render()

    def details_changed(self, *_):
        e = self.entry()
        if self._loading or e is None:
            return
        e.update(caption=self.ed_cap.text().strip(), chapter=self.cmb_chap.currentData(),
                 heading=self.ed_head.text().strip())
        self.sync_widgets()
        self.render()

    def sync_widgets(self):
        self._loading = True
        es, e = self.entries(), self.entry()
        self.lst.clear()
        self.lst.addItems([Path(x["file"]).name + (f" – {x['caption'][:40]}" if x.get("caption") else "") for x in es])
        if e is not None:
            self.lst.setCurrentRow(es.index(e))
        self.det.setEnabled(e is not None)
        self.ed_cap.setText((e or {}).get("caption", ""))
        self.cmb_chap.setCurrentIndex(max(0, self.cmb_chap.findData((e or {}).get("chapter", "new"))))
        self.ed_head.setText((e or {}).get("heading", ""))
        self.ed_head.setEnabled(e is not None and e.get("chapter") == "new")
        self._loading = False

    # -- Vorschau ------------------------------------------------------------------------------
    def render(self):
        """Gewählte (sonst erste) Abbildung unverändert anzeigen; leer -> Anleitung."""
        self.notes_begin()
        e = self.entry() or (self.entries()[0] if self.entries() else None)
        self.fig.clear()
        self.F = None
        try:
            if e is not None and Path(e["file"]).exists():
                img = self.cache(("otherimg", e["file"]), lambda: render_rgba(e["file"], 100))
                w, h = natural_cm(e["file"])
                self.host.set_figure_size(w / 2.54, h / 2.54)
                ax = self.fig.add_axes([0, 0, 1, 1])
                ax.imshow(img)
                ax.set_axis_off()
                self.F = ax
            elif e is not None:
                self.add_note(T("missing_file", p=e["file"]))
            self.preview_stack.setCurrentIndex(0 if self.F is None else 1)
            self.canvas.draw_idle()
            self.notes_show()
        except Exception as ex:
            self.notes_show(error=ex)
        self.main.push_undo()

    # -- Export / SI ------------------------------------------------------------------------------
    def export_to(self, base: Path):
        """Dateien unverändert kopieren: <base>_1.pdf, <base>_2.png …"""
        base = Path(base)
        base.parent.mkdir(parents=True, exist_ok=True)
        files = []
        es = [e for e in self.entries() if Path(e["file"]).exists()]
        if not es:
            raise RuntimeError(T("tab_empty"))
        for k, e in enumerate(es, 1):
            dst = base.with_name(f"{base.name}_{k}{Path(e['file']).suffix.lower()}")
            shutil.copyfile(e["file"], dst)
            files.append(dst)
        return files

    def caption_html(self, e):
        return html.escape(e.get("caption") or "")

    def chapter_blocks(self, out_dir, name):
        """-> [(Kapitelschlüssel bzw. „new:<Überschrift>“, [image, figcap])] in Reihenfolge der Liste."""
        out = []
        for k, e in enumerate(self.entries()):
            if not Path(e["file"]).exists():
                continue
            img = word_image(e["file"], out_dir, f"{TABS.core.safe_name(name)}_other_{k}")
            key = "new:" + (heading_of(e) or "Further figures") if e.get("chapter", "new") == "new" else e["chapter"]
            out.append((key, [img, ("figcap", self.caption_html(e))]))
        return out

    def si_figure(self, out_dir, name):
        """Einzel-SI: Abbildungen in Listenfolge, eigene Überschriften davor (einmal je Überschrift)."""
        out, seen = [], set()
        for key, bl in self.chapter_blocks(out_dir, name):
            if key.startswith("new:") and key not in seen:
                seen.add(key)
                out.append(("heading", html.escape(key[4:])))
            out += bl
        return out
