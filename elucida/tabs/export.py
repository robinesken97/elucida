"""Tab „Export“ (letzter Tab, Gruppe „Ausgabe“; Entscheidungen 64–68, 93): links Formate der Bilder und der SI-Abschnitt
dieser Verbindung, rechts eine Galerie mit einer Karte je Abbildung bzw. Bericht, nach Tab gruppiert (Entwurf v3,
audit/export-tab-skizze.html). Klick wählt aus; „n exportieren“ bzw. „Alles exportieren“ (Hauptknopf) schreibt genau die
Dateien der gewählten Karten, „Folien aus Auswahl (PPTX)“ eine Foliendatei. Die Pille „SI“ an einer Karte ist der eine Ort
für die SI-Auswahl (Entscheidung 67): Abbildungen eines Tabs (`export_state.si_off`, mit der Verbindung gespeichert, gilt
auch für die Gesamt-SI), Packung/PXRD (X-Ray) und NTO (TD-DFT) über ihre bisherigen Schlüssel im Zustand.

Zeigen baut keine anderen Tabs: Karten aus den Punkten der Tab-Leiste und dem gespeicherten Zustand, Vorschaubilder aus dem
letzten Export (figures/*.png), sonst aus der SI (.elucida/si) oder dem Bild, das beim Speichern für den offenen Tab
entsteht (.elucida/thumbs), sonst ein Platzhalter."""
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (QCheckBox, QFontComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSplitter, QVBoxLayout, QWidget)

from elucida.app import style as STYLE
from elucida.app.i18n import T
from elucida.app.tiles import Tile, TileGrid
from elucida.tabs import base as TABS
from elucida.tabs.compound import SI_FIG_KEYS

FMTS = ("svg", "pdf", "png")                             # PPTX: „Folien aus Auswahl“ statt Format je Bild
PPTX_KEYS = SI_FIG_KEYS[:-1] + ("xray", "dft")          # Tabs, deren Abbildungen auf Folien können (export_pptx_slides)
PART_COST_MAX = 0.3                                     # s: teurere Teilbilder nicht beim Zeigen zeichnen
WORD_KEYS = ("syn", "nmr")                              # Bericht als Word-Datei statt Abbildung
TABLE_SUFFIXES = ("_captions", "_HOMA", "_crystal_data", "_parameters", "_tables")      # X-Ray: Tabellen und Texte


def parts(main, key):
    """Zeilen eines Tabs: [(Teil, Test auf den Dateinamen oder None)] – eine Zeile je Abbildung/Bericht, soweit der
    gespeicherte Zustand sie nennt (baut keinen Tab); None = der ganze Tab bzw. alles, was keine andere Zeile nimmt.
    Der Test gilt für die Dateien, die der Export des Tabs schreibt (`MainWindow.place_exports` legt nur diese ab)."""
    from elucida.app import project as PRJ
    from elucida.core import uvvis as core
    if key == "eps":
        gs = list(main.groups)
        return [(g, lambda n, s=PRJ.export_stem(g, "eps"): n.startswith(s + ".") or n.startswith(s + "_"))
                for g in gs] if len(gs) > 1 else [("", None)]
    if key in WORD_KEYS:
        return [("", None)]
    _, cls, st_attr, _ = main._tab_spec(key)
    st = getattr(main, st_attr) or {}
    stem = PRJ.export_stem(main.export_name(), cls.STATE_KEY)

    def rest(n):                                         # Dateiname ohne Endung und ohne <Verbindung>_<Tab>
        b = n.rsplit(".", 1)[0]
        return b[len(stem):] if b.startswith(stem) else None

    def has(part):
        return lambda n: part in (rest(n) or "")
    out = []
    if key == "fluo" and st.get("decay_file"):
        out = [(T("export_part_spectra"), None), (T("export_part_decay"), has("_decay"))]
    elif key == "epr" and st.get("calc"):
        out = [(T("export_part_spectra"), None), (T("export_part_hfc"), has("_hfc")), (T("export_part_spin"), has("_spin"))]
    elif key == "overlay" and (st.get("nto") or {}).get("items"):
        out = [(T("export_part_spectra"), None), ("NTO", has("_NTO"))]
    elif key == "xray":
        es = st.get("entries") or []
        out = [(T("export_part_structure"), None)]
        if any((e.get("pack") or {}).get(f) for e in es for f in ("on", "used", "si")):   # Pille aus: bleibt (B1)
            out.append((T("export_part_packing"), has("_packing")))
        if any((e.get("pxrd") or {}).get("file") for e in es):
            out.append(("PXRD", has("_pxrd")))
        out.append((T("export_part_tables"), lambda n: (rest(n) or "").endswith(TABLE_SUFFIXES)))
    elif key == "dft":
        for e in st.get("entries") or []:
            nm = core.safe_name(e.get("name") or Path(e.get("file") or "").stem)
            out.append((T("export_part_geometry", name=nm), lambda n, nm=nm: rest(n) == "_" + nm))
            if e.get("orbitals"):
                out.append((T("export_part_orbitals", name=nm), lambda n, nm=nm: (rest(n) or "").startswith(f"_{nm}_")))
        if (st.get("nics") or {}).get("files"):
            out.append(("NICS", has("_NICS")))
        out.append((T("export_part_report"), None))
    elif key == "other":
        es = [e for e in st.get("entries") or [] if Path(e.get("file") or "").exists()]
        if len(es) > 1:                                   # wie OtherTab.export_to: <Stamm>_<k>.<Endung>
            out = [(Path(e["file"]).name, lambda n, k=k: rest(n) == f"_{k}") for k, e in enumerate(es, 1)]
    if len(out) < 2:
        return [("", None)]
    taken = [p for _, p in out if p is not None]
    return [(lab, p if p is not None else (lambda n, ps=taken: not any(q(n) for q in ps))) for lab, p in out]


class ExportCard(Tile):
    """Kachel einer Abbildung bzw. eines Berichts (gemeinsames Kachelraster `app/tiles.py`): Marke der Datenart, Pille
    „SI“, Vorschau, Teilname. Nur-SI-Kacheln (Tabellen ohne eigene Dateien) sind nicht wählbar."""

    def __init__(self, tab, key, idx, label, name, pred, report, si, si_only=False):
        super().__init__((tab._name(key), key), name, si, selectable=not si_only,
                         tip=T("export_si_only_tip") if si_only else
                         ("" if si is not None else T("export_si_parts_tip") if key in ("syn", "nmr", "xray") else ""))
        self.tab, self.key, self.idx, self.label, self.pred, self.report, self.si = tab, key, idx, label, pred, report, si
        self.si_only = si_only
        if self.pill is not None:
            self.pill.setToolTip(T("export_si_pill_tip"))

    def set_thumb(self, path):
        """Vorschau aus dem Bild, sonst Platzhalter je Art in der Farbe der Datenart."""
        from elucida.app.tiles import tile_pixmap
        self.set_pixmap(tile_pixmap(path, self.pic) if path else None)

    def set_pixmap(self, pm):
        super().set_thumb(pm, self.kind(), self.key)

    def kind(self):
        """Platzhalter-Form je Datenart und Teil (tiles.kind_pixmap)."""
        lab = self.label
        if lab.endswith(T("export_part_report")):
            return "page"
        if self.si_only or lab.endswith((T("export_part_tables"), "HOMA")):
            return "table"
        if lab.endswith((T("export_part_hfc"), T("export_part_spin"), "NTO")) or \
                T("export_part_orbitals", name="") in lab:
            return "lobes"
        if lab.endswith((T("export_part_structure"), T("export_part_packing"))) or \
                T("export_part_geometry", name="") in lab:
            return "molecule"
        if lab.endswith("PXRD"):
            return "stick"
        if lab.endswith(T("export_part_decay")):
            return "decay"
        return {"syn": "arrow", "nmr": "stick", "irms": "stick", "hrms": "stick", "eps": "band", "overlay": "band",
                "sec": "band", "uvkin": "decay", "fluo": "twopeaks", "cv": "loop", "hcell": "loop",
                "epr": "derivative", "xray": "molecule", "dft": "band", "other": "curve"}.get(self.key, "curve")


class CardArea(QWidget):
    """Inhalt der Galerie: Tastatur (Pfeile, Leertaste, Strg+A) für die Auswahl."""

    def __init__(self, tab):
        super().__init__()
        self.tab = tab
        self.setFocusPolicy(Qt.StrongFocus)

    def keyPressEvent(self, ev):
        t, cards = self.tab, self.tab.shown()
        if not cards:
            return super().keyPressEvent(ev)
        if ev.key() == Qt.Key_A and ev.modifiers() & Qt.ControlModifier:
            return t.select_all(True)
        moves = {Qt.Key_Left: -1, Qt.Key_Right: 1}
        if ev.key() in moves or ev.key() in (Qt.Key_Up, Qt.Key_Down):
            c_cur = t.cards[t.current] if t.current is not None else None
            cur = cards.index(c_cur) if c_cur in cards else -1
            if ev.key() in moves:
                nxt = cur + moves[ev.key()]
            else:                                         # eine Zeile: Karte darüber/darunter (nächste in x)
                c0 = cards[max(cur, 0)]
                x0 = c0.mapTo(self, c0.rect().center()).x()
                y0 = c0.mapTo(self, c0.rect().center()).y()
                up = ev.key() == Qt.Key_Up
                cand = [(abs(c.mapTo(self, c.rect().center()).x() - x0), abs(c.mapTo(self, c.rect().center()).y() - y0), i)
                        for i, c in enumerate(cards)
                        if (c.mapTo(self, c.rect().center()).y() < y0) == up and c.mapTo(self, c.rect().center()).y() != y0]
                nxt = min(cand, key=lambda x: (x[1], x[0]))[2] if cand else cur
            t.set_current(t.cards.index(cards[max(0, min(len(cards) - 1, nxt))]))
            return None
        if ev.key() == Qt.Key_Space and t.current is not None:
            return t.toggle(t.cards[t.current])
        return super().keyPressEvent(ev)


class ExportTab(QWidget):
    STATE_KEY = "export"
    STEP_LABELS = ("step_export",)
    TEXT_OPTS = ()

    def __init__(self, main, state):
        super().__init__()
        self.main = main
        self._loading = False
        self.cards, self.current = [], None
        left = QWidget()
        self.lv = QVBoxLayout(left)
        g = QGroupBox(T("export_grp_formats"))
        f = STYLE.make_form(g)
        row = QHBoxLayout()
        self.cb_fmt = {}
        for e in FMTS:
            cb = self.cb_fmt[e] = QCheckBox(e.upper())
            cb.setToolTip(T("export_fmt_tip_" + e))
            cb.toggled.connect(self._fmt_changed)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("formats"), row)
        hint = STYLE.HintLabel(T("export_formats_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(STYLE.HINT_CSS)
        f.addRow(hint)
        self.grp_formats = g
        self.lv.addWidget(g)
        self.grp_si = self.si_card()
        self.lv.addWidget(self.grp_si)
        self.lv.addStretch(1)
        ls = QScrollArea()
        ls.setWidget(left)
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.NoFrame)
        ls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # rechts: Kopfzeile (Hinweis · Alle · Keine), Abschnitt je Tab mit Kartenraster, Fußleiste mit der Aktion
        page = QWidget()
        pv = QVBoxLayout(page)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(STYLE.ROW_GAP)
        top = QHBoxLayout()
        hint = STYLE.HintLabel(T("export_cards_hint"))
        hint.setStyleSheet(STYLE.HINT_CSS)
        hint.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hint.setProperty("plaintext", True)
        hint.setWordWrap(True)
        from elucida.app.tiles import EDGE
        top.setContentsMargins(EDGE, 0, 0, 0)                    # dieselbe linke Kante wie die Karten
        top.addWidget(hint, 1)
        for text, on in ((T("export_select_all"), True), (T("export_select_none"), False)):
            b = QPushButton(text, objectName="ghost")
            b.clicked.connect(lambda _=False, on=on: self.select_all(on))
            top.addWidget(b)
        pv.addLayout(top)
        self.area = CardArea(self)
        self.av = QVBoxLayout(self.area)
        self.av.setContentsMargins(0, 0, 0, 0)
        self.av.setSpacing(STYLE.ROW_GAP)
        self.grid = TileGrid()                                   # ein Raster für alle Kacheln (auch Projektseite)
        self.av.addWidget(self.grid)
        self.lbl_empty = STYLE.HintLabel("")
        self.av.addWidget(self.lbl_empty)
        self.av.addStretch(1)
        sa = QScrollArea()
        sa.setWidget(self.area)
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll = sa
        pv.addWidget(sa, 1)
        # Segmente (Entscheidung 102): Reiter über dem einen Raster, sie filtern nur (eine Auswahl über alle)
        self.segments = [("all", None)] + [(head, keys) for head, keys in main.NAV_GROUPS
                                            if head not in ("nav_grp_compound", "nav_grp_out")]
        self.content = TABS.page_wrap(page)
        self.right_tabs = TABS.result_tabs()
        for sid, _ in self.segments:
            holder = QWidget()
            QVBoxLayout(holder).setContentsMargins(0, 0, 0, 0)
            self.right_tabs.addTab(holder, "")
        # Zahl der gewählten Kacheln je Segment: kleine Pille im Segment direkt hinter dem Text (Platz über Leerzeichen)
        self.seg_counts = [QLabel(self.right_tabs.tabBar(), objectName="segCount", alignment=Qt.AlignCenter)
                           for _ in self.segments]
        for c_ in self.seg_counts:
            c_.setAttribute(Qt.WA_TransparentForMouseEvents)
            c_.hide()
        self._seg_labels(short=False)
        seg = str(main.settings.value("step/ExportSegment", "all") or "all")
        self.right_tabs.setCurrentIndex(next((i for i, (sid, _) in enumerate(self.segments) if sid == seg), 0))
        self.right_tabs.widget(self.right_tabs.currentIndex()).layout().addWidget(self.content)
        self.right_tabs.currentChanged.connect(self._segment_changed)
        self.lbl_count = QLabel(objectName="recentSub")
        self.btn_slides = QPushButton(T("export_slides_sel"))
        self.btn_slides.setToolTip(T("export_slides_sel_tip"))
        self.btn_slides.clicked.connect(self.run_slides)
        self.btn_main = QPushButton(STYLE.icon("export", "#FFFFFF"), T("export_all"))
        self.btn_main.setProperty("accent", True)                # Hauptknopf dieser Ansicht
        self.btn_main.setToolTip(T("export_all_tip"))
        self.btn_main.clicked.connect(self.run)
        self.btn_all = self.btn_main
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, TABS.PAGE_TOP, 0, 0)
        rv.setSpacing(0)
        rv.addWidget(self.right_tabs, 1)
        rv.addWidget(TABS.side_bar(self.lbl_count, self.btn_slides, self.btn_main, stretch_at=1))
        split = QSplitter(Qt.Horizontal)
        split.addWidget(TABS.footer(self, ls))                   # Spalte mit Schrittleiste wie in allen Tabs
        split.addWidget(right)
        split.setSizes([620, 800])
        TABS.fit_footer_column(self, split)
        self._footer_parts[1].hide()                             # ein Schritt, keine Knöpfe links: keine leere Fußleiste
        lay = QHBoxLayout(self)                                  # kein QVBoxLayout: tidy(Tab) rückt sonst alles ein
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(split)
        self.refresh()

    # -- Formate --------------------------------------------------------------------------
    def sync_formats(self):
        self._loading = True
        try:
            fmt = self.main.export_fmt()
            for e, cb in self.cb_fmt.items():
                cb.setChecked(bool(fmt.get(e)))
        finally:
            self._loading = False

    def _fmt_changed(self, *_):
        if self._loading:
            return
        self.main.set_export_fmt({e: cb.isChecked() for e, cb in self.cb_fmt.items()})

    # -- SI (Word) dieser Verbindung: Teile, Schrift, SI und Datenpaket ------------------------------------------------
    def si_card(self):
        from elucida.app.main_window import SI_PARTS
        g = QGroupBox(T("export_grp_si"))
        f = STYLE.make_form(g)
        self.si_parts = {}
        row = QHBoxLayout()
        for k in SI_PARTS:
            cb = self.si_parts[k] = QCheckBox(T("si_chip_" + k))
            cb.toggled.connect(self._si_parts_changed)
            row.addWidget(cb)
        row.addStretch(1)
        f.addRow(T("si_export_parts"), row)
        self.cmb_si_font = QFontComboBox()
        self.cmb_si_font.setToolTip(T("si_font_tip"))
        self.cmb_si_font.currentFontChanged.connect(self._si_font_changed)
        f.addRow(T("si_font"), self.cmb_si_font)
        row = QHBoxLayout()
        self.btn_si = QPushButton(T("export_si_btn"))           # graue Knöpfe (Entscheidung 68)
        self.btn_si.setToolTip(T("act_si_tip"))
        self.btn_si.clicked.connect(self.main.export_si_dialog)
        self.btn_dp = QPushButton(T("export_dp_btn"))
        self.btn_dp.setToolTip(T("export_dp_tip"))
        self.btn_dp.clicked.connect(self.main.export_datapack)
        row.addWidget(self.btn_si)
        row.addWidget(self.btn_dp)
        f.addRow("", row)
        hint = STYLE.HintLabel(T("export_si_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(STYLE.HINT_CSS)
        f.addRow(hint)
        return g

    def sync_si(self):
        self._loading = True
        try:
            saved = self.main.si_parts_saved()
            for k, cb in self.si_parts.items():
                cb.setChecked(k in saved)
            self.cmb_si_font.setCurrentFont(QFont(str(self.main.settings.value("si_font", "Arial") or "Arial")))
        finally:
            self._loading = False

    def _si_parts_changed(self, *_):
        if not self._loading:
            self.main.set_si_parts([k for k, cb in self.si_parts.items() if cb.isChecked()])
            self.sync_pills()

    def _si_font_changed(self, font):
        if self._loading:
            return
        from elucida.si import lines as SI
        self.main.settings.setValue("si_font", font.family())
        SI.set_font(font.family())

    # -- Karten ---------------------------------------------------------------------------
    def _name(self, k):
        return T("tab_eps") if k == "eps" else T(self.main._tab_spec(k)[3])

    def _items(self, k):
        """Kacheln eines Tabs: [(Teil-Index, Bezeichnung „Tab · Teil“, Name auf der Kachel, Test)]; ein Bild: der
        Tabname (die Marke oben nennt den Tab ohnehin)."""
        ps, name = parts(self.main, k), self._name(k)
        if len(ps) == 1 and not ps[0][0]:
            return [(0, name, name, None)]
        return [(i, f"{name} · {lab}", lab, p) for i, (lab, p) in enumerate(ps)]

    def _si_only(self, k):
        """Tabellen/Texte, die nur in die SI gehen (früher Haken im Tab, jetzt die Pille hier): [(Name, (lesen, setzen))]."""
        m, name, out = self.main, self._name(k), []

        def flag(key, st, default):
            return (lambda: bool(st.get(key, default)), lambda on: self._mark(k, lambda: st.__setitem__(key, on)))
        if k == "overlay" and any(e.get("kind") == "calc" for e in m.ov_state.get("entries") or []):
            out.append((f"{name} · {T('export_part_tdt')}", flag("tdt_si", m.ov_state, True)))
        if k == "irms" and m.irms_state.get("irc_file"):
            out.append((f"{name} · {T('export_part_irc')}", flag("irc_si", m.irms_state, True)))
        if k in ("xray", "dft") and (getattr(m, m._tab_spec(k)[2]).get("entries")):
            out.append((f"{name} · HOMA", flag("homa_si", getattr(m, m._tab_spec(k)[2]), False)))
        return out

    def _si(self, k, label):
        """Pille „SI“ einer Karte -> (lesen, setzen) oder None (Teile links: Synthese, NMR, Struktur)."""
        m = self.main
        if k == "xray" and label.endswith((T("export_part_packing"), "PXRD")):
            sub = "pack" if not label.endswith("PXRD") else "pxrd"
            es = (m.xray_state.get("entries") or [])
            return (lambda: any((e.get(sub) or {}).get("si", sub == "pxrd") for e in es),
                    lambda on: self._mark("xray", lambda: [e.setdefault(sub, {}).__setitem__("si", on) for e in es]))
        if k == "overlay" and label.endswith("NTO"):
            nto = m.ov_state.setdefault("nto", {})
            return (lambda: nto.get("si", True), lambda on: self._mark("overlay", lambda: nto.__setitem__("si", on)))
        if k in SI_FIG_KEYS:                                     # Abbildungen des Tabs (alle Karten des Tabs zusammen)
            return (lambda: k not in m.si_figs_off(),
                    lambda on: (m.set_si_figs_off(m.si_figs_off() - {k} | (set() if on else {k})),
                                QTimer.singleShot(0, self.sync_pills)))
        return None

    def _mark(self, key, change):
        """SI-Schalter im Zustand eines Tabs ändern (der eine Ort für die SI-Auswahl), Tab neu, ein Rückgängig-Schritt."""
        change()
        self.main.export_state["si_mark"] = self.main.export_state.get("si_mark", 0) + 1   # Rückgängig bleibt hier
        if self.main._built(key):
            self.main.replace_tab(key)
        self.main.push_undo()
        QTimer.singleShot(0, self.sync_pills)

    def sync_pills(self):
        """Pillen aus dem Zustand. Ist der Teil der SI (Chip links, nur dieser Rechner) aus, bleiben sie bedienbar: die
        Gesamt-SI kennt die Chips nicht und richtet sich nach den Pillen; der Hinweis sagt das (B1)."""
        saved = self.main.si_parts_saved()
        for c in self.cards:
            if c.pill is not None:
                c.pill.blockSignals(True)
                c.pill.setChecked(bool(c.si[0]()))
                c.pill.blockSignals(False)
                part = "xray" if c.key == "xray" else "dft" if c.key == "dft" and c.label.endswith("HOMA") else "figs"
                c.pill.setToolTip(T("export_si_pill_tip") if part in saved else
                                  T("export_si_pill_off_tip", chip=T("si_chip_" + part)))

    def thumb(self, k, idx, pred):
        """Vorschaubild ohne den Tab zu bauen: letzter Export, SI-Bild, Bild vom Speichern; sonst None."""
        from elucida.app import project as PRJ
        from elucida.core import uvvis as core
        if not self.main.project_dir:
            return None
        if k in WORD_KEYS:                                # Bericht: vorhandene Bilder, die nichts kosten
            st = self.main.nmr_state if k == "nmr" else self.main.syn_state
            files = [s_.get("file") for s_ in st.get("spectra") or []] if k == "nmr" else \
                [str(Path(st["scheme"]).with_suffix(e)) for e in (".svg", ".png")] if st.get("scheme") else []
            p = next((Path(f) for f in files if f and Path(f).suffix.lower() in (".svg", ".png") and Path(f).exists()),
                     None)
            return p                                      # NMR: Mnova-SVG, Synthese: Bild des Schemas daneben
        pdir = Path(self.main.project_dir)
        if k == "eps":
            stem = PRJ.export_stem(list(self.main.groups)[idx] if self.main.groups else self.main.export_name(), "eps")
        else:
            stem = PRJ.export_stem(self.main.export_name(), self.main._tab_spec(k)[1].STATE_KEY)
        figs = pdir / PRJ.FIGURES
        hits = sorted((p for p in figs.glob(stem + "*.png") if (pred(p.name) if pred else p.stem.startswith(stem))),
                      key=lambda p: len(p.name)) if figs.is_dir() else []      # ohne Test: das Hauptbild (kürzester Name)
        cand = hits[:1]
        if pred is not None and (pdir / PRJ.WORK / "thumbs" / f"{k}_{idx}.png").exists():   # Teil: beim Zeigen gerendert
            cand.append(pdir / PRJ.WORK / "thumbs" / f"{k}_{idx}.png")
        if idx == 0:                                      # Hauptbild: auch SI-Bild und Bild vom Speichern
            name = core.safe_name((self.main.compound or {}).get("name") or self.main.export_name())
            sk = "epsilon" if k == "eps" else self.main._tab_spec(k)[1].STATE_KEY
            cand += [p for p in (pdir / PRJ.WORK / "si" / f"{name}_{sk}.png", pdir / PRJ.WORK / "thumbs" / f"{k}.png")
                     if p.exists()]
        return max(cand, key=lambda p: p.stat().st_mtime) if cand else None    # nie veraltet: das neueste gewinnt

    def refresh(self):
        """Formate, SI-Teile und Kacheln aus dem Zustand (Punkte der Leiste, ε-Serien); baut nichts. Die Auswahl bleibt
        (nach Art und Teil), nur eine andere Verbindung beginnt ohne. Vorschaubilder: aus dem Zwischenspeicher sofort,
        sonst erst ein Symbol und das Bild danach einzeln je Durchlauf der Ereignisschleife (nie sekundenlang lesen)."""
        from elucida.app.tiles import cached_pixmap
        self.sync_formats()
        self.sync_si()
        old = self.cards[self.current] if self.current is not None and self.current < len(self.cards) else None
        old = old and (old.key, old.label)                      # Markierung (Link „In die SI“) übersteht Auffrischen
        same = getattr(self, "_sel_dir", None) == self.main.project_dir
        keep = {(c.key, c.label) for c in self.cards if c.selected} if same else set()
        self._sel_dir = self.main.project_dir
        self.cards, self.current, self._thumb_queue = [], None, []
        for k in self.main.export_keys():
            for i, lab, name, pred in self._items(k):
                c = ExportCard(self, k, i, lab, name, pred, k in WORD_KEYS, self._si(k, lab))
                path = self.thumb(k, i, pred)
                pm = cached_pixmap(path, c.pic) if path else None
                c.set_thumb(None) if path and pm is None else c.set_pixmap(pm)
                if path and pm is None:
                    self._thumb_queue.append((c, path))
                c.set_selected((k, lab) in keep)
                self.cards.append(c)
            for lab, si in self._si_only(k):
                c = ExportCard(self, k, -1, lab, lab.split(" · ", 1)[-1], None, True, si, si_only=True)
                c.set_thumb(None)
                self.cards.append(c)
        for c in self.cards:
            c.clicked.connect(self._card_clicked)
        self.grid.set_rows([(None, self.cards)])
        self.grid.set_filter(None if self.segment()[1] is None else self.shown())
        if old is not None:
            i = next((i for i, c in enumerate(self.cards) if (c.key, c.label) == old), None)
            if i is not None and self.cards[i] in self.shown():
                self.set_current(i)
        self.lbl_empty.setText("" if self.cards else T("export_none"))
        self.sync_pills()
        self.sync_button()
        if not hasattr(self, "_thumb_timer"):
            self._thumb_timer = QTimer(self, singleShot=True, interval=0, timeout=self._next_thumb)
        self._thumb_timer.start()

    def _next_thumb(self):
        """Ein Vorschaubild je Durchlauf (große PNG aus figures/ brauchen ~70 ms zum Lesen)."""
        while self._thumb_queue:
            c, path = self._thumb_queue.pop(0)
            if c in self.cards:
                c.set_thumb(path)
                break
        if self._thumb_queue:
            self._thumb_timer.start()

    def _card_clicked(self, card, ev):
        self.set_current(self.cards.index(card))
        self.area.setFocus()
        self.toggle(card)

    def toggle(self, card):
        card.set_selected(not card.selected)
        self.sync_button()

    def set_current(self, i):
        if self.current is not None and self.current < len(self.cards):
            self.cards[self.current].set_current(False)
        self.current = i
        self.cards[i].set_current(True)
        self.scroll.ensureWidgetVisible(self.cards[i])

    # -- Segmente (Entscheidung 102) -------------------------------------------------------------------------------
    SEG_PAD = "\u2003\u2003"                           # Platz für die Zahl hinter dem Text (zwei Geviert)

    def _seg_labels(self, short):
        bar = self.right_tabs.tabBar()
        self._seg_text = []
        for i, (sid, _) in enumerate(self.segments):
            long_ = T("export_seg_all") if sid == "all" else T(sid)
            text = T("export_seg_short_" + sid.replace("nav_grp_", "")) if short and sid != "all" else long_
            n = getattr(self, "seg_counts", None) and self.seg_counts[i].text() not in ("", "0")
            self._seg_text.append(text)
            self.right_tabs.setTabText(i, text.replace("&", "&&") + (self.SEG_PAD if n else ""))   # „&“: kein Kürzel
            self.right_tabs.setTabToolTip(i, long_)
        self._short = short
        bar.updateGeometry()

    def _place_counts(self):
        """Zahl hinter dem Text des Segments, auf dessen Mittellinie, innerhalb des Segments."""
        bar = self.right_tabs.tabBar()
        for i, c_ in enumerate(self.seg_counts):
            if c_.text() in ("", "0") or not self.right_tabs.isTabVisible(i):
                c_.hide()
                continue
            f = QFont(bar.font())
            if i == self.right_tabs.currentIndex():
                f.setWeight(QFont.DemiBold)
            fm = QFontMetrics(f)
            r = bar.tabRect(i).adjusted(0, STYLE.RESULT_TAB_MT, 0, -STYLE.RESULT_TAB_MB)   # sichtbarer Reiter
            full = fm.horizontalAdvance(self._seg_text[i] + self.SEG_PAD)
            end = r.center().x() - full / 2 + fm.horizontalAdvance(self._seg_text[i])
            c_.adjustSize()
            c_.move(round(end + 4), r.center().y() - c_.height() // 2)
            c_.show()
            c_.raise_()

    def segment(self):
        return self.segments[max(0, self.right_tabs.currentIndex())]

    def shown(self):
        """Kacheln des offenen Segments (in der Reihenfolge der Leiste)."""
        keys = self.segment()[1]
        return [c for c in self.cards if keys is None or c.key in keys]

    def _segment_changed(self, i):
        page = self.right_tabs.widget(i)
        if page is not None and self.content.parentWidget() is not page:
            page.layout().addWidget(self.content)
        self.main.settings.setValue("step/ExportSegment", self.segments[i][0])
        QTimer.singleShot(0, self._place_counts)                 # der offene Reiter ist halbfett
        self.grid.set_filter(None if self.segments[i][1] is None else self.shown())
        if self.current is not None and self.cards[self.current] not in self.shown():
            self.cards[self.current].set_current(False)
            self.current = None

    def sync_segments(self):
        """Zahl der gewählten Kacheln je Segment (kleine Pille, bei 0 aus); Segmente ohne Daten gedimmt."""
        bar, have = self.right_tabs.tabBar(), {c.key for c in self.cards}
        for i, (sid, keys) in enumerate(self.segments):
            n = sum(1 for c in self.cards if c.selected and (keys is None or c.key in keys))
            self.seg_counts[i].setText(str(n) if n else "")
            bar.setTabTextColor(i, QColor(STYLE.colors()["text" if keys is None or have & set(keys) else "disabled"]))
        self._fit_segments()
        self._place_counts()                                     # Zahl sofort (0 = aus), nicht erst nach dem Zeichnen

    def _fit_segments(self):
        """Passen die langen Namen nicht in die Breite (1200 px), kurze Namen (lange im Tooltip)."""
        avail = self.right_tabs.width() - TABS.PAGE_INSET[0] - 8
        if avail <= 0:
            return
        bar = self.right_tabs.tabBar()
        self._seg_labels(short=False)
        need = sum(bar.tabSizeHint(i).width() for i in range(bar.count()))   # alle Reiter, auch in „Mehr ▾“
        if need > avail:
            self._seg_labels(short=True)
        self.right_tabs.fit()
        QTimer.singleShot(0, self._place_counts)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        QTimer.singleShot(0, self._fit_segments)

    def select_all(self, on):
        """„Alle · Keine“: nur das offene Segment."""
        for c in self.shown():
            c.set_selected(on)
        self.sync_button()

    def chosen(self):
        return [c for c in self.cards if c.selected]

    def sync_button(self, *_):
        self.sync_segments()
        n = len(self.chosen())
        self.lbl_count.setText(T("export_n_selected", n=n) if n else T("export_none_selected"))
        self.btn_main.setText(T("export_n", n=n) if n else T("export_all"))
        self.btn_main.setEnabled(bool(self.cards))
        self.btn_slides.setEnabled(any(c.key in PPTX_KEYS for c in (self.chosen() or self.cards)))

    def run(self):
        sel = self.chosen()
        items = [(c.key, c.pred) for c in sel] or None
        return self.main.export_all_tabs(items)

    def run_slides(self):
        keys = [c.key for c in self.chosen() if c.key in PPTX_KEYS]
        return self.main.export_pptx_slides(list(dict.fromkeys(keys)) or None)

    def showEvent(self, ev):
        super().showEvent(ev)
        self.refresh()                                           # Daten, Vorschaubilder; Auswahl bleibt
        # fehlende oder veraltete Teilbilder nur gebauter Tabs nacheinander nachziehen (nie einen Tab bauen)
        # nur billige Arten (gemessene Dauer des Exports < PART_COST_MAX, je Sitzung); unbekannt oder teuer (EPR ~4 s,
        # DFT ~14 s): exportierte Datei aus figures/ oder Symbol – Zeigen blockiert nie sekundenlang (Messen hieße blockieren)
        cost = self.main.__dict__.get("_part_cost", {})
        self._sub_queue = [k for k in dict.fromkeys(c.key for c in self.cards if c.pred is not None)
                           if k in self.main._TAB_BUILD_ORDER and self.main._built(k)   # ε: Serien sind keine Teile
                           and (cost.get(k, PART_COST_MAX) < PART_COST_MAX or self.main.quick_parts(k))]   # 132
        self._sub_dir = self.main.project_dir                    # nur in den Ordner der Verbindung von jetzt
        if not hasattr(self, "_sub_timer"):                      # Kind des Tabs: stirbt mit ihm (Verbindung gewechselt)
            self._sub_timer = QTimer(self, singleShot=True, timeout=self._next_subthumb)
        self._sub_timer.start(200)

    def hideEvent(self, ev):
        super().hideEvent(ev)
        self._sub_queue = []                                     # Tab verlassen: nichts mehr nachziehen
        if hasattr(self, "_sub_timer"):
            self._sub_timer.stop()

    def _next_subthumb(self):
        if not self.isVisible() or not getattr(self, "_sub_queue", None) or self.main.project_dir != self._sub_dir:
            self._sub_queue = []
            return
        k = self._sub_queue.pop(0)
        try:
            if self.main.render_part_thumbs(k):
                for c in self.cards:
                    if c.key == k and c.pred is not None:
                        c.set_thumb(self.thumb(k, c.idx, c.pred))
        except Exception:                                        # Vorschau ist nur Anzeige
            pass
        self._sub_timer.start(0)                                 # ein Teil je Durchlauf der Ereignisschleife

    def show_card(self, key, label=None):
        """Hinweis in einem Tab („In die SI: Karte im Tab Export“): Karte zeigen und markieren."""
        c = next((c for c in self.cards if c.key == key and (label is None or c.label.endswith(label))), None)
        if c is not None:
            if c not in self.shown():
                self.right_tabs.setCurrentIndex(0)             # Segment „Alle“, sonst bliebe die Karte verborgen
            self.set_current(self.cards.index(c))

    def compound_changed(self):
        self.refresh()

    def export_dialog(self):
        return self.run()
