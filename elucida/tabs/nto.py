"""NTO-Bilder zur TD-DFT-Tabelle (Paket B 1.2.0, Overlay-Tab): Karte „Übergangsorbitale (NTO)“ im Schritt Auswertung,
Seite „NTO“ rechts mit den Paaren Loch → Teilchen eines Zustands und ihren Gewichten.

Elucida rechnet keine NTOs, es zeigt, was die Rechnung liefert:
- ORCA (`%tddft DoNTO true end`): je Zustand eine .nto-Datei (gbw-Format), vom Nutzer mit orca_2mkl in Molden
  umgewandelt; Paare und Gewichte n aus dem NTO-Block der Ausgabe (`formats/nto.py`), Zuordnung über die Energie.
- Cubes (orca_plot aus der .nto, Gaussian cubegen aus `Pop=(NTO,SaveNTO)`): zwei Dateien = ein Paar (Loch = kleinere
  MO-Nummer); Gewicht aus dem NTO-Block, wenn die Nummern dort ein Paar sind, sonst vom Nutzer (ohne Eingabe keins).
Gezeichnet mit dem Orbital-Rendering des DFT-Tabs (IboView-Stil), gleiche Ansicht und gleicher Maßstab für alle Bilder.
"""
import html
import io
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as MplFigure
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QCheckBox)

from elucida.app import project as PRJ
from elucida.app import style as STYLE
from elucida.app.i18n import T
from elucida.core import orbitals as ORB
from elucida.core import tddft as X
from elucida.formats import nto as NTO
from elucida.formats.calc import read_text
from elucida.formats.elements import BOHR
from elucida.tabs import xray as XRAY

DEFAULTS = dict(items={}, sel=None, wmin=10.0, iso=0.0, si=True)
MAX_PAIRS = 4                                    # mehr Paare über der Schwelle sind praktisch nie sinnvoll lesbar
IMG_DPI = 200
DRAG_DPI = 100                                   # Ziehbild (4 Zoll) höchstens so fein: Drehen bleibt flüssig


def state_key(src, k):
    """Schlüssel eines Zustands: Dateiname (nicht Pfad: Projekte speichern Pfade relativ) | Variante | Index."""
    return f"{Path(src['file']).name}|{src.get('variant') or ''}|{k}"


class NtoView:
    def __init__(self, tab, lay):
        self.tab = tab
        st = tab.st.setdefault("nto", {})
        for k, v in DEFAULTS.items():
            st.setdefault(k, dict(v) if isinstance(v, dict) else v)
        g = QGroupBox(T("nto_card"))
        g.setToolTip(T("nto_card_tip"))
        f = STYLE.make_form(g)
        self.cmb_state = QComboBox()
        self.cmb_state.setToolTip(T("nto_state_tip"))
        f.addRow(T("nto_state"), self.cmb_state)
        row = QHBoxLayout()
        self.btn_molden = QPushButton(T("nto_molden"))
        self.btn_molden.setToolTip(T("nto_molden_tip"))
        self.btn_cubes = QPushButton(T("nto_cubes"))
        self.btn_cubes.setToolTip(T("nto_cubes_tip"))
        self.btn_remove = QPushButton(STYLE.icon("trash", lone=True), "")
        self.btn_remove.setToolTip(T("remove"))
        frow = QHBoxLayout()                                   # Dateizeile wie in den Nachbarkarten: Name, Papierkorb
        self.lbl_names = QLabel("–")
        self.lbl_names.setWordWrap(True)
        frow.addWidget(self.lbl_names, 1)
        frow.addWidget(self.btn_remove)
        f.addRow(T("nto_file"), frow)
        row.addWidget(self.btn_molden)                         # Knopfreihe ohne Beschriftung: teilt die Wertespalte
        row.addWidget(self.btn_cubes)
        f.addRow("", row)
        self.lbl_file = STYLE.HintLabel("")
        self.lbl_file.setWordWrap(True)
        self.lbl_file.setStyleSheet(STYLE.HINT_CSS)
        f.addRow(self.lbl_file)
        self.sp_w = QDoubleSpinBox(decimals=0, minimum=0, maximum=100, singleStep=1, suffix=" %")
        self.sp_w.setSpecialValueText(T("nto_weight_none"))
        self.sp_w.setToolTip(T("nto_weight_tip"))
        f.addRow(T("nto_weight"), self.sp_w)
        self.sp_wmin = QDoubleSpinBox(decimals=0, minimum=1, maximum=100, singleStep=5, suffix=" %")
        self.sp_wmin.setToolTip(T("nto_wmin_tip"))
        f.addRow(T("nto_wmin"), self.sp_wmin)
        self.sp_iso = QDoubleSpinBox(decimals=3, minimum=0.0, maximum=0.5, singleStep=0.005)
        self.sp_iso.setSpecialValueText(T("nto_iso_auto", p=f"{ORB.ISO_FRACTION:g}"))
        self.sp_iso.setToolTip(T("nto_iso_tip"))
        f.addRow(T("nto_iso"), self.sp_iso)
        self.btn_view = QPushButton(STYLE.icon("reset"), T("xr_reset_view"))
        self.btn_view.setToolTip(T("nto_view_reset_tip"))
        self.btn_view.setFixedWidth(STYLE.VALUE_W)            # einzelner Knopf: ganze Wertespalte wie die Dateiknöpfe
        f.addRow(T("nto_view"), self.btn_view)
        self.cb_si = QCheckBox(T("nto_si"))
        self.cb_si.setToolTip(T("nto_si_tip"))
        f.addRow(self.cb_si)
        from elucida.tabs.base import si_elsewhere
        si_elsewhere(f, self.cb_si, tab, "overlay", "NTO")
        lay.addWidget(g)
        self.card = g
        from elucida.tabs.base import PageTexts               # feste Texte des Bilds („hole“, „particle“)
        self.text_rows = []
        self.texts = PageTexts(tab, lambda: "nto", self.refresh, "lab_card_nto")
        lay.addWidget(self.texts.box)
        self.texts.box.hide()                                  # erst mit Bild
        self.cmb_state.currentIndexChanged.connect(self.state_chosen)
        self.btn_molden.clicked.connect(self.add_molden)
        self.btn_cubes.clicked.connect(self.add_cubes)
        self.btn_remove.clicked.connect(self.remove)
        self.btn_view.clicked.connect(self.reset_view)
        self.sp_w.valueChanged.connect(self.weight_changed)
        for w in (self.sp_wmin, self.sp_iso):
            w.valueChanged.connect(self.changed)
        self.cb_si.toggled.connect(self.changed)
        # Ergebnisseite (arrange -> to_right): Bild der Paare, darunter die Bildunterschrift
        self.page = QGroupBox(T("nto_page"))
        v = QVBoxLayout(self.page)
        self.fig = MplFigure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumSize(1, 1)
        from elucida.app.canvas_theme import register
        register(self.canvas)
        v.addWidget(self.canvas, 1)
        self.lbl_empty = STYLE.SciLabel(empty=T("nto_none"))
        v.addWidget(self.lbl_empty)
        self.txt_cap = STYLE.SiText(empty=T("nto_cap_empty"))
        self.txt_cap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        v.addWidget(self.txt_cap)
        b = STYLE.copy_button(T("nto_copy_tip"))
        from elucida.tabs.ir_ea import copy_rich
        b.clicked.connect(lambda: copy_rich(STYLE_plain(self.caption_html()), self.caption_html()))
        STYLE.card_actions(self.page, b)
        lay.addWidget(self.page)
        self._states = []
        self._pending = False
        self._ims = []                                         # [(Achse, Bild)] der Orbitale auf self.fig (Drehen)
        self._drag_key = None
        self.mouse = _NtoMouse(_DragView(self), _NtoTarget(self))
        from elucida.tabs.base import ShowHook
        ShowHook(self.page, lambda: self._pending and self.refresh())   # aufgeschobenes Bild beim Anzeigen

    # -- Zustand ---------------------------------------------------------------------------------
    @property
    def st(self):
        return self.tab.st["nto"]

    def states(self):
        """Alle Zustände der sichtbaren TD-DFT-Einträge -> [dict(key, label, name, E, lam, f, mult, src, entry)]
        (Zustandsnamen wie in der Tabelle „Anregungen“: S1, T1 … je Multiplizität gezählt)."""
        out = []
        ents = [e for e in self.tab.st["entries"] if e.get("kind") == "calc" and e.get("visible", True)]
        for e in ents:
            for s_ in self.tab.sources(e):
                try:
                    r = self.tab.cache(("tddft", s_["file"], s_.get("variant")),
                                       lambda s_=s_: X.parse_tddft(s_["file"], s_.get("variant")))
                except Exception:
                    continue
                mult = list(r.get("mult") or [None] * len(r["E"]))
                count = {}
                name = e["label"].replace(" (TD-DFT)", "")
                for k, (E, f, m) in enumerate(zip(r["E"], r["f"], mult)):
                    count[m] = count.get(m, 0) + 1
                    st_name = {1: "S", 3: "T"}.get(m, "") + str(count[m] if m in (1, 3) else k + 1)
                    out.append(dict(key=state_key(s_, k), name=st_name, E=float(E), f=float(f), mult=m, src=s_,
                                    entry=name, lam=1239.84198 / E if E > 0 else float("nan"),
                                    label=f"{st_name} · {E:.2f} eV · {name}"))
        return out

    def current(self):
        key = self.st.get("sel")
        return next((s for s in self._states if s["key"] == key), None)

    def item(self, s=None):
        s = s or self.current()
        return self.st["items"].get(s["key"]) if s else None

    def sync(self):
        self._states = self.states()
        ws = (self.cmb_state, self.sp_w, self.sp_wmin, self.sp_iso, self.cb_si)
        for w in ws:
            w.blockSignals(True)
        try:
            keys = [s["key"] for s in self._states]
            if self.st.get("sel") not in keys:                 # Vorgabe: erster Zustand mit Datei, sonst der erste
                self.st["sel"] = next((k for k in keys if k in self.st["items"]), keys[0] if keys else None)
            self.cmb_state.clear()
            for s in self._states:
                self.cmb_state.addItem(s["label"] + ("  ●" if s["key"] in self.st["items"] else ""), s["key"])
            self.cmb_state.setCurrentIndex(max(0, self.cmb_state.findData(self.st.get("sel"))))
            it = self.item()
            self.sp_w.setValue(float(it.get("weight") or 0.0) if it else 0.0)
            self.sp_wmin.setValue(float(self.st.get("wmin", 10.0)))
            self.sp_iso.setValue(float(self.st.get("iso", 0.0)))
            self.cb_si.setChecked(bool(self.st.get("si", True)))
        finally:
            for w in ws:
                w.blockSignals(False)
        on = self.current() is not None
        for w in (self.cmb_state, self.btn_molden, self.btn_cubes):
            w.setEnabled(on)
        it = self.item()
        self.btn_remove.setEnabled(it is not None)
        self.btn_view.setEnabled(bool(it and it.get("view")))
        # Gewicht von Hand nur für Cubes, deren Paar nicht im NTO-Block der Ausgabe steht
        self.sp_w.setEnabled(bool(it) and it["kind"] == "cube" and self.out_weight(self.current(), it) is None)

    def state_chosen(self, *_):
        self.st["sel"] = self.cmb_state.currentData()
        self.changed()

    def changed(self, *_):
        self.st.update(wmin=self.sp_wmin.value(), iso=self.sp_iso.value(), si=self.cb_si.isChecked())
        self.refresh()
        self.tab.main.push_undo()

    def weight_changed(self, *_):
        it = self.item()
        if it is not None and it["kind"] == "cube":
            it["weight"] = self.sp_w.value() or None
            self.changed()

    def reset_view(self):
        it = self.item()
        if it is not None and it.pop("view", None) is not None:
            self.refresh()
            self.tab.main.push_undo()

    def view_changed(self, R):
        """Eigene Drehung (Ziehen im Bild): gilt für Loch und Teilchen, gespeichert nur jetzt (alte Projekte ohne)."""
        it = self.item()
        if it is not None:
            it["view"] = [round(float(v), 6) for v in np.asarray(R).ravel()]
            self.refresh()
            self.tab.main.push_undo()

    # -- Dateien ---------------------------------------------------------------------------------
    def _pick(self, title, flt, many):
        last = self.tab.main.settings.value("last_dir", "")
        if many:
            ps, _ = QFileDialog.getOpenFileNames(self.tab, title, last, flt + ";;" + T("flt_all"))
            return ps
        p, _ = QFileDialog.getOpenFileName(self.tab, title, last, flt + ";;" + T("flt_all"))
        return [p] if p else []

    def add_molden(self, path=None):
        s = self.current()
        if s is None or not self.tab.main.ensure_project():
            return
        ps = [path] if path else self._pick(T("nto_molden"), "Molden (*.molden *.molden.input *.mold *.input)", False)
        if not ps:
            return
        try:
            m = ORB.parse_molden(read_text(ps[0]))
            if not self.blocks(s):
                raise ValueError(T("nto_no_block"))
            p = self.tab.main.import_file(ps[0], PRJ.data_sub(self.tab.STATE_KEY))
        except Exception as ex:
            self.tab.main.error(str(ex))
            return
        self.st["items"][s["key"]] = dict(kind="molden", file=p, state=s["name"], title=m.get("title", ""))
        self.refresh()
        self.tab.main.push_undo()

    def add_cubes(self, paths=None):
        s = self.current()
        if s is None or not self.tab.main.ensure_project():
            return
        ps = list(paths) if paths else self._pick(T("nto_cubes"), "Cube (*.cube *.cub)", True)
        if not ps:
            return
        try:
            ps, nos = self.cube_pair(ps)
            ps = [self.tab.main.import_file(p, PRJ.data_sub(self.tab.STATE_KEY)) for p in ps]
        except Exception as ex:
            self.tab.main.error(str(ex))
            return
        self.st["items"][s["key"]] = dict(kind="cube", files=ps, mos=nos, state=s["name"], weight=None)
        self.refresh()
        self.tab.main.push_undo()

    @staticmethod
    def cube_pair(ps):
        """Zwei Cubes -> ([Loch, Teilchen], [MO-Nummern]): Loch = kleinere Nummer (besetzt); ohne Nummer nur über
        „hole“/„particle“ im Dateinamen, nie nach der Auswahlreihenfolge. Gleiche Geometrie nötig."""
        if len(ps) != 2:
            raise ValueError(T("nto_two_cubes"))
        cubes = [ORB.read_cube(p) for p in ps]
        nos = [ORB.cube_mo(p, c)[0] for p, c in zip(ps, cubes)]
        if None in nos:
            role = [("hole" in Path(p).name.lower()) - ("particle" in Path(p).name.lower()) for p in ps]
            if sorted(role) != [-1, 1]:
                raise ValueError(T("fixd_nto_order"))
            if role[0] < 0:
                ps, nos = list(ps)[::-1], nos[::-1]
        elif nos[0] > nos[1]:
            ps, nos = list(ps)[::-1], nos[::-1]
        if len(cubes[0]["els"]) != len(cubes[1]["els"]) or \
                np.abs(np.asarray(cubes[0]["xyz"]) - np.asarray(cubes[1]["xyz"])).max() > 0.02:
            raise ValueError(T("nto_cube_geom"))
        return list(ps), nos

    def remove(self):
        s = self.current()
        if s is not None and self.st["items"].pop(s["key"], None) is not None:
            self.refresh()
            self.tab.main.push_undo()

    # -- Paare -----------------------------------------------------------------------------------
    def blocks(self, s):
        try:
            return self.tab.cache(("ntoblocks", s["src"]["file"]),
                                  lambda: NTO.orca_nto_blocks(read_text(s["src"]["file"])))
        except Exception:
            return []

    def block(self, s):
        return NTO.block_for(self.blocks(s), s["E"], X.MATCH_EV)

    def out_weight(self, s, it):
        """Gewicht eines Cube-Paars aus dem NTO-Block (Nummern als Paar dort gedruckt) oder None."""
        if s is None or it is None or it["kind"] != "cube" or None in (it.get("mos") or [None]):
            return None
        b = self.block(s)
        if b is None:
            return None
        sp = [ORB.cube_mo(f)[1] for f in it.get("files") or ["", ""]]       # Spin aus dem Namen (mo61a), sonst offen
        return next((n for h, hs, p, ps_, n in b["pairs"] if (h, p) == tuple(it["mos"])
                     and all(not a or a == c for a, c in zip(sp, (hs, ps_)))), None)

    def pairs(self, s=None):
        """-> (Paare [dict(hole, particle (Orbital-Quellen), w (Anteil oder None), names)], Hinweise)."""
        s = s or self.current()
        it = self.item(s)
        if it is None:
            return [], []
        notes = []
        if it["kind"] == "cube":
            if not all(Path(p).exists() for p in it["files"]):
                return [], [T("nto_missing")]
            w = self.out_weight(s, it)
            if w is None and it.get("weight"):
                w = it["weight"] / 100
                notes.append(T("nto_weight_user"))
            names = [f"{n}" if n is not None else Path(p).stem for n, p in zip(it["mos"], it["files"])]
            return [dict(hole=dict(cube=it["files"][0]), particle=dict(cube=it["files"][1]), w=w, names=names)], notes
        if not Path(it["file"]).exists():
            return [], [T("nto_missing")]
        b = self.block(s)
        if b is None:
            return [], [T("nto_no_match")]
        wmin = self.st.get("wmin", 10.0) / 100
        m = self.molden(it["file"])
        out = []
        for h, hs, p, ps, n in b["pairs"]:
            if n < wmin or len(out) >= MAX_PAIRS:
                continue
            ih, ip = self.mo_index(m, h, hs), self.mo_index(m, p, ps)
            if ih is None or ip is None:
                notes.append(T("nto_no_mo", h=h, p=p))
                continue
            out.append(dict(hole=dict(molden=it["file"], mo=ih), particle=dict(molden=it["file"], mo=ip), w=n,
                            names=[f"{h}{hs}", f"{p}{ps}"]))
        if b.get("file") and Path(b["file"]).stem.split(".")[-1] not in Path(it["file"]).name:
            notes.append(T("nto_file_name", f=b["file"]))       # .s3.nto zu Zustand 1? Nur Hinweis, Namen sind frei
        return out, notes

    def molden(self, p):
        return self.tab.cache(("molden", p), lambda: ORB.parse_molden(read_text(p)))

    @staticmethod
    def mo_index(m, no, spin):
        """Index in m["mos"] für eine Orbitalnummer des NTO-Blocks: ORCA zählt je Spin ab 0 (wie in der .nto-Datei,
        die orca_2mkl in derselben Reihenfolge schreibt), unabhängig davon, ob der Titel „orca“ nennt."""
        k = 0
        for i, mo in enumerate(m["mos"]):
            if mo["spin"] == (spin or "a"):
                if k == no:
                    return i
                k += 1
        return None

    def geometry(self, src):
        """(Elemente, Koordinaten Å) der Orbitaldatei."""
        if "cube" in src:
            c = self.tab.cache(("cube", src["cube"]), lambda: ORB.read_cube(src["cube"]))
            return list(c["els"]), np.asarray(c["xyz"], float)
        m = self.molden(src["molden"])
        return list(m["els"]), np.asarray(m["xyz"], float) * BOHR

    def volume(self, src):
        if "cube" in src:
            c = self.tab.cache(("cube", src["cube"]), lambda: ORB.read_cube(src["cube"]))
            return self.tab.cache(("ntovol", src["cube"]), lambda: ORB.Volume(c["data"][0], c["origin"], c["axes"]))

        def make():
            b = ORB.Basis(self.molden(src["molden"]))
            err = b.setup()
            if err > ORB.Basis.MAX_ORTH_ERR:
                raise ValueError(T("dft_orb_molden_conv", err=f"{err:.1e}"))
            data, origin, axes = ORB.molden_grid(b, b.m["mos"][src["mo"]]["c"], ORB.MOLDEN_SPACING)
            return ORB.Volume(data, origin, axes)
        return self.tab.cache(("ntovol", src["molden"], src["mo"]), make)

    def iso(self, vol):
        v = float(self.st.get("iso", 0.0))
        return v if v > 0 else ORB.iso_for_fraction(vol.data, ORB.ISO_FRACTION)

    # -- Bilder ----------------------------------------------------------------------------------
    def _orbital_figure(self, els, xyz, vol, iso, R, fig, ext=None):
        from elucida.tabs import base as TABS, xray as XRAY
        from elucida.tabs.dft import XyzMolecule, bonds_of
        mol = XyzMolecule(els, xyz, bonds_of(els, xyz), list(els), uiso=(0.25 / XRAY.chi2_scale(0.5)) ** 2)
        plus, minus, alpha = ORB.orbital_colors(0)
        o = dict(prob=50, show_h=True, labels=False, h_labels=False, colors={}, bond_w=0.08, hidden_frags=[],
                 style="iboview", hidden_atoms=[], label_on={}, wire=set(), wire_h=False, label_mode="all",
                 hide_kinds=[], label_size=0.0, label_color="black", label_colors={}, cartoon_color=False,
                 h_radius=0.1375, bg="transparent", ball_scale=1.0, rod_scale=1.0, elem_labels=False,
                 orbital=dict(vol=vol, iso=iso, plus=plus, minus=minus, alpha=alpha))
        cfg = TABS.FigureTab.base_cfg(self.tab)
        cfg["figsize_in"] = [4.0, 4.0]
        if R is None:
            R = XRAY.default_view(mol, use=list(range(len(mol.atoms))))
        return XRAY.XrayFigure(cfg, mol, R, o, {}, fig, ext=ext), R

    def images(self, pairs, s=None):
        """RGBA-Bilder aller Orbitale (Loch, Teilchen je Paar): gleiche Ansicht, gleicher Maßstab, gleicher Ausschnitt."""
        return self.rendered(pairs, s)["imgs"]

    def rendered(self, pairs, s=None):
        """-> dict(imgs, R, ext, crop (x0, y0) in Pixeln des vollen Bilds); Ansicht = eigene Drehung des Zustands
        (`view` im Eintrag) oder automatisch."""
        srcs = [p[r] for p in pairs for r in ("hole", "particle")]
        view = (self.item(s) or {}).get("view")
        key = ("ntoimg", repr(srcs), float(self.st.get("iso", 0.0)), repr(view))

        def make():
            R = np.array(view, float).reshape(3, 3) if view and len(view) == 9 else None
            ext, figs = [0.0, 0.0], []
            for src in srcs:                                      # 1) gemeinsame Ansicht und Ausdehnung
                els, xyz = self.geometry(src)
                vol = self.volume(src)
                fig = MplFigure(figsize=(4, 4), dpi=IMG_DPI / 2)
                FigureCanvasAgg(fig)
                F, R = self._orbital_figure(els, xyz, vol, self.iso(vol), R, fig)
                ext = [max(ext[0], F.ext[0]), max(ext[1], F.ext[1])]
                figs.append((els, xyz, vol))
            e = max(ext)
            out = []
            for els, xyz, vol in figs:                            # 2) zeichnen mit derselben Ausdehnung
                fig = MplFigure(figsize=(4, 4), dpi=IMG_DPI / 2)
                FigureCanvasAgg(fig)
                self._orbital_figure(els, xyz, vol, self.iso(vol), R, fig, ext=(e, e))
                buf = io.BytesIO()
                fig.savefig(buf, format="png", transparent=True, dpi=IMG_DPI)
                from PIL import Image
                out.append(np.asarray(Image.open(buf).convert("RGBA")).copy())
            alpha = np.max([im[:, :, 3] for im in out], axis=0)    # gemeinsamer Ausschnitt um alles Sichtbare
            y, x = np.nonzero(alpha)
            y0 = x0 = 0
            if len(x):
                pad = 6
                y0, y1, x0, x1 = max(0, y.min() - pad), y.max() + pad + 1, max(0, x.min() - pad), x.max() + pad + 1
                out = [im[y0:y1, x0:x1] for im in out]
            return dict(imgs=out, R=R, ext=(e, e), crop=(int(x0), int(y0)), full=alpha.shape[:2])
        return self.tab.cache(key, make)

    @staticmethod
    def wide(imgs):
        """Langgestrecktes Molekül (Bild deutlich breiter als hoch): Loch über Teilchen statt nebeneinander, damit das
        Bild die Fläche füllt."""
        h, w = imgs[0].shape[:2]
        return w > 1.6 * h

    def draw(self, fig, pairs, imgs):
        """Je Paar Loch → Teilchen mit Gewicht über dem Pfeil. Normal: Paare untereinander (Loch | Pfeil | Teilchen);
        langgestreckt: Paare nebeneinander (Loch über Pfeil über Teilchen). Köpfe „hole“/„particle“."""
        fig.clear()
        ims = []
        n, fs, wide = len(pairs), 11, self.wide(imgs)
        if wide:
            gs = fig.add_gridspec(3, n, height_ratios=[1, 0.3, 1], left=0.07, right=0.99, top=0.99, bottom=0.01,
                                  wspace=0.06, hspace=0.02)
        else:
            gs = fig.add_gridspec(n, 3, width_ratios=[1, 0.32, 1], left=0.01, right=0.99, top=0.93, bottom=0.01,
                                  wspace=0.02, hspace=0.08)
        for i, (p, (a, b)) in enumerate(zip(pairs, zip(imgs[0::2], imgs[1::2]))):
            for j, im in ((0, a), (2, b)):
                ax = fig.add_subplot(gs[j, i] if wide else gs[i, j])
                ims.append((ax, ax.imshow(im, interpolation="lanczos")))
                ax.set_axis_off()
                if i == 0:
                    lab = "hole" if j == 0 else "particle"
                    if wide:                          # wie der Titel: derselbe Schlüssel in beiden Anordnungen
                        ax.text(-0.02, 0.5, lab, transform=ax.transAxes, rotation=90, ha="right", va="center",
                                fontsize=fs)._elu_role = "title"
                    else:
                        ax.set_title(lab, fontsize=fs)
            ax = fig.add_subplot(gs[1, i] if wide else gs[i, 1])
            ax.set_axis_off()
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            arrow = dict(arrowstyle="-|>", lw=1.4, color="black", mutation_scale=14)
            if wide:
                ax.annotate("", xy=(0.5, 0.08), xytext=(0.5, 0.92), arrowprops=arrow)
            else:
                ax.annotate("", xy=(0.92, 0.5), xytext=(0.08, 0.5), arrowprops=arrow)
            if p["w"] is not None:
                t = f"{p['w'] * 100:.0f}%"
                if wide:
                    ax.text(0.54, 0.5, t, ha="left", va="center", fontsize=fs)
                else:
                    ax.text(0.5, 0.58, t, ha="center", va="bottom", fontsize=fs)
        from elucida.core import figtexts as FT            # eigene Texte (Karte „Beschriftungen: NTO“), auch Export/SI
        self.text_rows = FT.apply(fig, None, self.tab.st.get("text_over"), {})
        return ims

    def fig_size(self, n, imgs, w_cm=16.0):
        """Exportgröße: 16 cm breit, Höhe aus Seitenverhältnis der Bilder und Anordnung (wie `draw`)."""
        h, w = imgs[0].shape[:2]
        if self.wide(imgs):
            col = (w_cm * 0.92 - 0.3 * (n - 1)) / n
            return w_cm / 2.54, (2.35 * col * h / w + 0.3) / 2.54
        img = w_cm * 0.98 / 2.36
        return w_cm / 2.54, (n * img * h / w * 1.1 + 0.8) / 2.54

    def refresh(self):
        self.sync()
        s = self.current()
        pairs, notes = self.pairs(s) if s else ([], [])
        it = self.item(s)
        files = ([Path(it["file"]).name] if it and it["kind"] == "molden" else
                 [Path(p).name for p in it["files"]] if it else [])
        self.lbl_names.setText("; ".join(files) if files else "–")
        self.lbl_file.setText("\n".join(notes))
        self.texts.box.setVisible(bool(pairs))
        self._pending = bool(pairs) and not self.page.isVisible()
        if self._pending:                                     # Bilder (Raycasting) erst beim Anzeigen der Seite
            return
        self._ims = []
        if not pairs:
            self.fig.clear()
            self.canvas.hide()
            self.lbl_empty.show()
            self.txt_cap.setText("")
            self.lbl_empty.setText(notes[0] if (it and notes) else "")
            self.canvas.draw_idle()
            return
        try:
            imgs = self.images(pairs, s)
        except Exception as ex:
            self.tab.main.log_signal.emit(f"NTO: {ex}")
            self.canvas.hide()
            self.lbl_empty.show()
            self.lbl_empty.setText(str(ex))
            return
        self.lbl_empty.hide()
        self.canvas.show()
        self._ims = self.draw(self.fig, pairs, imgs)
        self.texts.fill(self)
        self._drag_key = (s["key"], repr(pairs), float(self.st.get("iso", 0.0)), repr(self.item(s).get("view")))
        self.canvas.draw_idle()
        cap = self.caption_html(s, pairs)
        self.txt_cap.setText("<b>Figure Sn</b>: " + cap)

    # -- Unterschrift, SI, Export ------------------------------------------------------------------
    def level(self, s):
        try:
            from elucida.tabs.dft import read_calc
            from elucida.tabs.dft_pages import level_of_theory
            return level_of_theory(self.tab.cache(("ntocalc", s["src"]["file"]), lambda: read_calc(s["src"]["file"])))
        except Exception:
            return ""

    def caption_html(self, s=None, pairs=None, name=None):
        s = s or self.current()
        if s is None:
            return ""
        if pairs is None:
            pairs = self.pairs(s)[0]
        if not pairs:
            return ""
        name = name or self.tab.main.export_name()
        lev = self.level(s)
        ws = [p["w"] for p in pairs]
        iso = float(self.st.get("iso", 0.0))
        iso_t = (f"isovalue ±{iso:g} a.u." if iso > 0 else
                 f"isosurfaces enclosing {ORB.ISO_FRACTION:g}% of the orbital density")
        txt = (f"Natural transition orbitals of <b>{html.escape(name)}</b> for the {s['name']} state "
               f"({s['E']:.2f} eV, {s['lam']:.0f} nm, <i>f</i> = {s['f']:.3f})")
        if lev:
            txt += f" at the {html.escape(lev)} level of theory"
        try:
            wide = self.wide(self.images(pairs, s))
        except Exception:
            wide = False
        txt += ": hole (top) and particle (bottom)" if wide else ": hole (left) and particle (right)"
        if all(w is not None for w in ws):
            txt += (", weights " if len(ws) > 1 else ", weight ") + ", ".join(f"{w * 100:.0f}%" for w in ws)
            it = self.item(s)
            if it and it["kind"] == "molden":
                txt += f" (pairs with a weight of at least {self.st.get('wmin', 10.0):.0f}%)"
        return txt + f"; {iso_t}."

    def export_figure(self, path_stem, s=None):
        """Bild der Paare als PNG und SVG (16 cm breit) -> [Pfade] oder []."""
        s = s or self.current()
        pairs = self.pairs(s)[0] if s else []
        if not pairs:
            return []
        imgs = self.images(pairs, s)
        fig = MplFigure(figsize=self.fig_size(len(pairs), imgs), dpi=100)
        FigureCanvasAgg(fig)
        self.draw(fig, pairs, imgs)
        out = []
        for ext in ("png", "svg"):
            p = Path(f"{path_stem}.{ext}")
            p.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(p, dpi=300, facecolor="white")
            out.append(p)
        return out

    def export_to(self, base):
        """Alle Zustände mit NTO-Datei: Bild + Unterschrift (Text)."""
        base = Path(base)
        files, caps = [], []
        self._states = self.states()
        for s in self._states:
            if s["key"] not in self.st["items"]:
                continue
            stem = base.with_name(f"{base.name}_NTO_{s['name']}")
            got = self.export_figure(stem, s)
            if got:
                files += got
                caps.append(f"{s['name']}: " + STYLE_plain(self.caption_html(s)))
        if caps:
            p = base.with_name(base.name + "_NTO_captions.txt")
            p.write_text("\n\n".join(caps) + "\n", encoding="utf-8")
            files.append(p)
        return files

    def si_blocks(self, out_dir, name):
        """SI (Word): je Zustand mit NTO-Datei Bild + „Figure Sn: …“ (Haken „In die SI“)."""
        if not self.st.get("si", True) or out_dir is None:
            return []
        out = []
        self._states = self.states()
        for s in self._states:
            if s["key"] not in self.st["items"]:
                continue
            pairs = self.pairs(s)[0]
            if not pairs:
                continue
            from elucida.core import uvvis as core
            got = self.export_figure(Path(out_dir) / f"{core.safe_name(name)}_NTO_{s['name']}", s)
            if not got:
                continue
            w_in, h_in = self.fig_size(len(pairs), self.images(pairs, s))
            out += [("image", got[0], w_in * 2.54, h_in * 2.54, got[1]), ("figcap", self.caption_html(s, pairs, name))]
        return out


def STYLE_plain(h):
    """HTML der Unterschrift -> reiner Text."""
    import re
    return html.unescape(re.sub(r"<[^>]+>", "", h))


class _DragView:
    """Schnittstelle von `xray.XrayMouse` für das NTO-Bild (mehrere Orbitale auf einer Abbildung): Drehen setzt die
    Ansicht aller Orbitale zugleich. Beim Ziehen je Orbital eine feste XrayFigure (Orbital gröber, Maßstab und Ausschnitt
    vom Ruhebild), ihr Bild ersetzt das Ruhebild in dessen Achse; nach dem Loslassen zeichnet `refresh` alles neu."""

    ann_items = {}
    scene = orb_art = None
    pan, zoom = [0.0, 0.0], 1.0

    def __init__(self, view):
        self.v, self.fig, self.R = view, view.fig, None
        self._figs, self._for = [], None

    @property
    def ax(self):
        return self.v._ims[0][0] if self.v._ims else self.fig.gca()

    def artists(self):
        return [im for _, im in self.v._ims]

    def data_per_px(self):
        return 1.0

    def set_zoom_pan(self, zoom=None, pan=None):
        pass

    def start(self):
        """Beim Drücken: Ansicht des Ruhebilds (eigene oder automatische)."""
        v = self.v
        s = v.current()
        pairs = v.pairs(s)[0] if s else []
        if not pairs or not v._ims:
            return False
        self._pairs, self._r = pairs, v.rendered(pairs, s)
        self.R = self._r["R"].copy()
        return True

    def set_drag(self, on):
        if not on or self._for == self.v._drag_key:
            return
        v, r = self.v, self._r
        ax = v._ims[0][0]
        crop_w = max(1, v._ims[0][1].get_array().shape[1])
        dpi = int(min(DRAG_DPI, max(30, IMG_DPI * ax.bbox.width / crop_w)))   # höchstens Bildschirmauflösung
        for _, im in v._ims:
            im.set_interpolation("bilinear")                      # Lanczos kostete beim Ziehen ~10 ms je Bild
        self._figs = []
        for src in [p[k] for p in self._pairs for k in ("hole", "particle")]:
            els, xyz = v.geometry(src)
            vol = v.volume(src)
            fig = MplFigure(figsize=(4, 4), dpi=dpi)
            FigureCanvasAgg(fig)
            F, _ = v._orbital_figure(els, xyz, vol, v.iso(vol), r["R"], fig, ext=r["ext"])
            fig.patch.set_alpha(0.0)
            F.set_drag(True)
            self._figs.append(F)
        self._for = v._drag_key

    def set_view(self, R):
        self.R = XRAY.orthonormalize(R)
        H, W = self._r["full"]
        x0, y0 = self._r["crop"]
        for F, (ax, im) in zip(self._figs, self.v._ims):
            F.set_view(self.R)
            F.fig.canvas.draw()
            ax.set_autoscale_on(False)                            # Achse behält den Ausschnitt des Ruhebilds
            im.set_data(np.asarray(F.fig.canvas.buffer_rgba()))
            im.set_extent((-0.5 - x0, W - 0.5 - x0, H - 0.5 - y0, -0.5 - y0))


class _NtoMouse(XRAY.XrayMouse):
    """Nur Drehen mit der linken Taste (kein Verschieben, Zoomen, Rahmen, Atomwahl); Empfänger = NtoView."""

    def press(self, ev):
        if ev.button != 1 or ev.dblclick or "shift" in (ev.key or "") or not self.F.start():
            self.mode = None
            return
        super().press(ev)

    def scroll(self, ev):
        pass


class _NtoTarget:
    """Empfänger für `_NtoMouse` (wie `_AcidMouse`): nur die Ansicht."""

    def __init__(self, view):
        self.v = view

    def hover_atom(self, k):
        pass

    atom_clicked = atom_double_clicked = atoms_boxed = labels_moved = pan_changed = zoom_changed = hover_atom

    def view_changed(self, R):
        self.v.view_changed(R)
