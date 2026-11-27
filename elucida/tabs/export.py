"""Tab „Export“ (letzter Tab, Gruppe „Ausgabe“; Entscheidungen 64–68, 93): links Formate der Bilder und der SI-Abschnitt
dieser Verbindung, rechts eine Galerie mit einer Karte je Abbildung bzw. Bericht, nach Tab gruppiert (Entwurf v3,
audit/export-tab-skizze.html). Eine gespeicherte Auswahl (Entscheidungen 182/183): Klick auf eine Karte wählt sie aus
oder ab (Rückgängig), die Fußleiste hat vier gleichrangige Knöpfe Bilder · Tabellen · PPTX · SI (Word); `feeds` sagt,
welche Karte welchen Knopf speist. Die Auswahl ist zugleich die SI-Auswahl (SI-Abschnitt und Gesamt-SI), gespeichert als
Abwahl in `export_state.si_off` (Tab = alle Karten, „Tab:Kennung“ = eine Karte); Packung/PXRD (X-Ray), NTO und die
Nur-SI-Tabellen über ihre bisherigen Schlüssel im Zustand ihres Tabs.

Zeigen baut keine anderen Tabs: Karten aus den Punkten der Tab-Leiste und dem gespeicherten Zustand, Vorschaubilder aus dem
letzten Export (figures/*.png), sonst aus der SI (.elucida/si) oder dem Bild, das beim Speichern für den offenen Tab
entsteht (.elucida/thumbs), sonst ein Platzhalter."""
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (QCheckBox, QFontComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget)

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
    """Zeilen eines Tabs: [(Teil, Test auf den Dateinamen oder None, Kennung)] – eine Zeile je Abbildung/Bericht, soweit
    der gespeicherte Zustand sie nennt (baut keinen Tab); None = der ganze Tab bzw. alles, was keine andere Zeile nimmt.
    Der Test gilt für die Dateien, die der Export des Tabs schreibt (`MainWindow.place_exports` legt nur diese ab).
    Kennung: sprachunabhängig (gespeicherte Auswahl `card_id`), "" = einzige Karte des Tabs."""
    from elucida.app import project as PRJ
    from elucida.core import uvvis as core
    if key == "eps":
        gs = list(main.groups)
        return [(g, lambda n, s=PRJ.export_stem(g, "eps"): n.startswith(s + ".") or n.startswith(s + "_"), g)
                for g in gs] if len(gs) > 1 else [("", None, "")]
    if key in WORD_KEYS:
        return [("", None, "")]
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
        out = [(T("export_part_spectra"), None, "spectra"), (T("export_part_decay"), has("_decay"), "decay")]
    elif key == "epr" and st.get("calc"):
        out = [(T("export_part_spectra"), None, "spectra"), (T("export_part_hfc"), has("_hfc"), "hfc"),
               (T("export_part_spin"), has("_spin"), "spin")]
    elif key == "overlay" and (st.get("nto") or {}).get("items"):
        out = [(T("export_part_spectra"), None, "spectra"), ("NTO", has("_NTO"), "nto")]
    elif key == "xray":
        es = st.get("entries") or []
        out = [(T("export_part_structure"), None, "structure")]
        if any((e.get("pack") or {}).get(f) for e in es for f in ("on", "used", "si")):   # abgewählt: bleibt (B1)
            out.append((T("export_part_packing"), has("_packing"), "packing"))
        if any((e.get("pxrd") or {}).get("file") for e in es):
            out.append(("PXRD", has("_pxrd"), "pxrd"))
        out.append((T("export_part_tables"), lambda n: (rest(n) or "").endswith(TABLE_SUFFIXES), "tables"))
    elif key == "dft":
        for e in st.get("entries") or []:
            nm = core.safe_name(e.get("name") or Path(e.get("file") or "").stem)
            out.append((T("export_part_geometry", name=nm), lambda n, nm=nm: rest(n) == "_" + nm, "geom:" + nm))
            if e.get("orbitals"):
                out.append((T("export_part_orbitals", name=nm), lambda n, nm=nm: (rest(n) or "").startswith(f"_{nm}_"),
                            "orb:" + nm))
        if (st.get("nics") or {}).get("files"):
            out.append(("NICS", has("_NICS"), "nics"))
        out.append((T("export_part_report"), None, "report"))
    elif key == "other":
        es = [e for e in st.get("entries") or [] if Path(e.get("file") or "").exists()]
        if len(es) > 1:                                   # wie OtherTab.export_to: <Stamm>_<k>.<Endung>
            out = [(Path(e["file"]).name, lambda n, k=k: rest(n) == f"_{k}", Path(e["file"]).name)
                   for k, e in enumerate(es, 1)]
    if len(out) < 2:
        return [("", None, "")]
    taken = [p for _, p, _ in out if p is not None]
    return [(lab, p if p is not None else (lambda n, ps=taken: not any(q(n) for q in ps)), pid) for lab, p, pid in out]


# -- Eine gespeicherte Auswahl (Entscheidungen 182/183): gilt für Bilder, Tabellen, PPTX und SI (Word) ------------------
# Gespeichert als Abwahl in `export_state.si_off` (wie bisher der Tab-Schalter): ein Tabschlüssel = alle Karten des Tabs
# aus (alte Projekte, unverändert gültig), „<Tab>:<Kennung>“ = eine Karte aus. Neue Karten sind gewählt (wie bisher: in
# der SI). Karten mit eigenem SI-Schlüssel im Zustand ihres Tabs (Packung, PXRD, NTO, Nur-SI-Tabellen) lesen und setzen
# diesen Schlüssel; die Tabs lesen ihn selbst.
SI_ONLY = {"tdt": ("overlay", "tdt_si", True), "irc": ("irms", "irc_si", True), "homa": (None, "homa_si", False)}


def card_id(key, pid):
    return f"{key}:{pid}" if pid else key


def flag(main, key, pid):
    """(lesen, setzen) einer Karte mit eigenem SI-Schlüssel, sonst None. Lesen ändert den Zustand nie."""
    if key == "xray" and pid in ("packing", "pxrd"):
        sub = "pack" if pid == "packing" else "pxrd"
        es = [e for e in main.xray_state.get("entries") or []          # nur Strukturen, die die Karte haben (wie parts)
              if ((e.get(sub) or {}).get("file") if sub == "pxrd" else e.get(sub))]
        # shortcut: eine Karte für alle Strukturen; wieder an schaltet alle betroffenen an, auch eine zuvor einzeln abgewählte
        return (lambda: any(e[sub].get("si", sub == "pxrd") for e in es),
                lambda on: [e[sub].__setitem__("si", on) for e in es])
    if key == "overlay" and pid == "nto":
        return (lambda: (main.ov_state.get("nto") or {}).get("si", True),
                lambda on: main.ov_state.setdefault("nto", {}).__setitem__("si", on))
    if pid in SI_ONLY and (SI_ONLY[pid][0] in (None, key)):
        st, sk, default = getattr(main, main._tab_spec(key)[2]), SI_ONLY[pid][1], SI_ONLY[pid][2]
        return (lambda: bool(st.get(sk, default)), lambda on: st.__setitem__(sk, on))
    return None


def is_on(main, key, pid):
    """Karte gewählt? (gespeichert mit der Verbindung)"""
    f = flag(main, key, pid)
    if f is not None:
        return bool(f[0]())
    off = main.si_figs_off()
    return key not in off and card_id(key, pid) not in off


def set_on(main, changes):
    """Auswahl ändern: [(Tab, Kennung, an)] -> ein Rückgängig-Schritt (Klick, Alle, Keine). Ein Tab-Schalter alter
    Projekte wird erst beim ersten Klick auf eine Karte seines Tabs in Karten aufgelöst. -> True, wenn sich etwas änderte."""
    off0 = main.si_figs_off()
    off, touched = set(off0), []
    for key, pid, on in changes:
        f = flag(main, key, pid)
        if f is not None:
            if bool(f[0]()) != bool(on):
                f[1](bool(on))
                touched.append(key)
            continue
        if on and pid and key in off:                     # alter Tab-Schalter: übrige Karten des Tabs bleiben aus
            off.discard(key)
            off |= {card_id(key, p) for _, _, p in parts(main, key) if p and flag(main, key, p) is None}
        (off.discard if on else off.add)(card_id(key, pid))
    if off == off0 and not touched:
        return False
    if off != off0:
        main.export_state["si_off"] = sorted(off)
    main.export_state["si_mark"] = main.export_state.get("si_mark", 0) + 1     # Rückgängig bleibt im Tab „Export“
    for key in dict.fromkeys(touched):
        if main._built(key):
            main.replace_tab(key)
    main.push_undo()
    return True


def feeds(key, pid, si_only=False):
    """Knöpfe, die eine Karte speist: img (Bilder: alle Dateien der Karte außer Tabellen, also auch Methodentext,
    Bildunterschriften, Word-Berichte), tab (Tabellen: CSV/Excel ihres Tabs), pptx (Folien), si (Abbildung bzw. Tabelle
    in der SI). Was nicht in „si“ steht, kommt über die Teile links in die SI (Synthese, NMR, Kristallstruktur, DFT)."""
    if si_only:
        return {"si"}                                     # TD-DFT-, IR-Rechnungs-, HOMA-Tabelle: Text der SI, keine Datei
    if key in WORD_KEYS:
        return {"img"}
    out = {"img", "tab"} if key != "other" else {"img"}   # Weitere: fremde Bilder, keine Tabellen
    if key == "xray":
        return out | ({"pptx"} if pid == "structure" else {"si"} if pid in ("packing", "pxrd") else set())
    if key == "dft":
        return out | ({"pptx", "si"} if pid in ("nics", "report") else {"si"} if pid.startswith("orb:") else set())
    if key == "overlay" and pid == "nto":
        return out | {"si"}                               # NTO-Bilder: SI über si_calc_tables, keine Folie
    return out | {"si"} | ({"pptx"} if key in PPTX_KEYS else set())


def si_pid(main, key, stem):
    """Kennung der Karte zu einem SI-Bild (Dateiname ohne Endung, wie ihn die Tabs für die SI schreiben)."""
    from elucida.core import uvvis as core
    if key == "eps":
        return next((g for g in main.groups if stem.endswith("_epsilon_" + core.safe_name(g))), "")
    if key == "fluo":
        return "decay" if stem.endswith("_fluorescence_decay") else "spectra"
    if key == "overlay":
        return "nto" if "_NTO_" in stem else "spectra"
    if key == "epr":
        return next((k for k in ("hfc", "spin") if stem.endswith("_epr_" + k)), "spectra")
    if key == "other" and "_other_" in stem:
        k = stem.rsplit("_other_", 1)[1]
        es = getattr(main, main._tab_spec("other")[2]).get("entries") or []
        return Path(es[int(k)]["file"]).name if k.isdigit() and int(k) < len(es) else ""
    if key == "dft":
        if "_dft_NICS" in stem:
            return "nics"
        head, _, tail = stem.partition("_")
        es = main.dft_state.get("entries") or []
        if head.isdigit() and int(head) < len(es) and not stem.endswith("_dft") and "_nbo" not in stem \
                and "_dft_" not in stem:
            e = es[int(head)]                             # Orbitalbild `<n>_<Name>_<Orbital>` (DFTTab.orbital_blocks)
            return "orb:" + core.safe_name(e.get("name") or Path(e.get("file") or "").stem)
        return "geom" if stem.endswith("_dft") else "report"
    return ""


def si_keep(main, key, blocks):
    """SI-/Folien-Blöcke eines Tabs ohne die Abbildungen abgewählter Karten (Bild samt folgender Unterschrift). Den
    ganzen Tab (Tabschlüssel in der Abwahl) prüfen die Aufrufer wie bisher; Geometrie, Koordinaten, Tabellen bleiben."""
    off = {pid for _, _, pid in parts(main, key) if pid and "si" in feeds(key, pid) and flag(main, key, pid) is None
           and not is_on(main, key, pid)}
    if not off or not blocks:
        return blocks
    out, drop = [], False
    for b in blocks:
        if b[0] == "image":
            drop = si_pid(main, key, Path(str(b[1])).stem) in off
            if not drop:
                out.append(b)
        elif drop and b[0] in ("figcap", "text"):         # Unterschrift des weggelassenen Bilds (Orbitale: „text“)
            drop = False
        else:
            drop = False
            out.append(b)
    if key == "other":                                    # eigene Überschrift ohne Abbildung darunter: weg
        out = [b for i, b in enumerate(out) if b[0] != "heading" or (i + 1 < len(out) and out[i + 1][0] != "heading")]
    return out


def off_names(main, feed="si"):
    """Abgewählte Karten mit Daten, deren Abbildung sonst in der SI (bzw. `feed`) stünde (Meldungen): Tab bzw.
    „Tab · Teil“; auch Karten mit eigenem Schlüssel (Packung, PXRD, NTO)."""
    out = []
    for k in main.export_keys():
        tab = T("tab_eps") if k == "eps" else T(main._tab_spec(k)[3])
        ps = parts(main, k)
        if k not in SI_FIG_KEYS + ("xray",):                # X-Ray: Packung, PXRD
            continue
        if k in main.si_figs_off():
            out.append(tab)
            continue
        out += [f"{tab} · {lab}" for lab, _, pid in ps
                if pid and feed in feeds(k, pid) and not is_on(main, k, pid)]
    return out


def two_lines(text, fm, width):
    """Teilname auf höchstens zwei Zeilen: Umbruch am letzten Leerzeichen, das passt, sonst mitten im Wort (Dateinamen);
    Zeile 2 in der Mitte gekürzt: das Ende eines Dateinamens unterscheidet die Rechnungen (Sichtung 1.4.0, 1500 px)."""
    if fm.horizontalAdvance(text) <= width:
        return [text]
    k = max([i for i in range(1, len(text) + 1) if fm.horizontalAdvance(text[:i]) <= width] or [1])
    sp = text.rfind(" ", 0, k + 1)
    cut = sp if sp > 0 else k
    return [text[:cut].rstrip(), _elide_middle(text[cut:].lstrip(), fm, width)]


def _elide_middle(s, fm, width):
    """Wie elidedText(ElideMiddle), aber jede Probe als ganze Zeile mit `fm` gemessen: elidedText rechnet die Laufweite
    nicht mit ein, die Zeile war breiter als das Label (CI Linux, 130 % Laufweite; Arial 150 % auch unter macOS)."""
    if fm.horizontalAdvance(s) <= width:
        return s
    for keep in range(len(s) - 1, 0, -1):
        head = keep // 2
        c = s[:head] + "…" + s[len(s) - (keep - head):]
        if fm.horizontalAdvance(c) <= width:
            return c
    return "…"


class TwoLineName(QLabel):
    """Name der Export-Kachel in zwei Zeilen (Nutzerwunsch: lange Teilnamen nicht nach einer Zeile kürzen); immer zwei
    Zeilen hoch, damit alle Kacheln gleich hoch sind und beim Reiterwechsel nichts springt. Voller Name im Tooltip."""

    def __init__(self, text, **kw):
        super().__init__(**kw)
        self._full = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.ensurePolished()                              # Schriftgröße aus dem Stylesheet (#tileName) vor dem Messen
        self.setFixedHeight(2 * self.fontMetrics().lineSpacing())

    def _fit(self):
        self.setText("\n".join(two_lines(self._full, self.fontMetrics(), max(10, self.width()))))

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._fit()

    def changeEvent(self, ev):                             # Schrift geändert (Theme, Systemschrift): neu umbrechen
        super().changeEvent(ev)
        if ev.type() == QEvent.FontChange:
            self.setFixedHeight(2 * self.fontMetrics().lineSpacing())
            self._fit()


class ExportCard(Tile):
    """Kachel einer Abbildung, eines Berichts oder einer Nur-SI-Tabelle (gemeinsames Kachelraster `app/tiles.py`):
    Marke der Datenart, Vorschau, Teilname. Klick = gespeicherte Auswahl (`set_on`); Tooltip nennt die Knöpfe."""

    def __init__(self, tab, key, idx, label, name, pred, report, pid="", si_only=False):
        self.pid, self.si_only = pid, si_only
        self.feeds = feeds(key, pid, si_only)
        tips = [T("export_feeds", items=", ".join(T("export_btn_" + b) for b in ("img", "tab", "pptx", "si")
                                                  if b in self.feeds))]
        if si_only:
            tips.append(T("export_si_only_tip"))
        elif key in SI_FIG_KEYS + ("xray",) and "si" not in self.feeds or key in WORD_KEYS:
            tips.append(T("export_si_parts_tip"))
        super().__init__((tab._name(key), key), name, None, tip="\n".join(tips))
        self.tab, self.key, self.idx, self.label, self.pred, self.report = tab, key, idx, label, pred, report
        self.cid = card_id(key, pid)
        one = self.name
        self.name = TwoLineName(name, objectName="tileName")
        v = self.layout()
        i = v.indexOf(one)
        v.removeWidget(one)                                  # nicht replaceWidget: dessen altes Element bliebe in PySide
        one.deleteLater()
        v.insertWidget(i, self.name)
        self.setFixedHeight(self.height() + self.name.fontMetrics().lineSpacing())   # eine Zeile mehr als die Kachel sonst

    def set_thumb(self, path):
        """Vorschau aus dem Bild, sonst grauer Platzhalter je Art."""
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


class SameWidthButton(QPushButton):
    """Ausgabeknopf der Fußleiste: so breit wie der breiteste der Reihe (Windows-Bericht 1.4.0: 79–110 px)."""
    row = ()

    def sizeHint(self):
        s = super().sizeHint()
        s.setWidth(max([QPushButton.sizeHint(b).width() for b in self.row if not b.isHidden()] or [s.width()]))
        return s


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
        # Fußleiste (Entscheidung 182, Variante A): vier gleichrangige Ausgabeknöpfe, kein blauer Hauptknopf (Blau =
        # ausgewählt, Ausnahme in ui.md); Zahlen im Tooltip, ohne passende Auswahl grau mit Grund im Tooltip
        self.lbl_count = QLabel(objectName="recentSub")
        self.btn_img, self.btn_tables, self.btn_slides, self.btn_si = (
            SameWidthButton(T("export_btn_" + b)) for b in ("img", "tab", "pptx", "si"))
        row_ = (self.btn_img, self.btn_tables, self.btn_slides, self.btn_si)
        for b_ in row_:
            b_.row = row_
        self.btn_img.clicked.connect(self.run)
        self.btn_tables.clicked.connect(self.run_tables)
        self.btn_slides.clicked.connect(self.run_slides)
        self.btn_si.clicked.connect(self.run_si)
        self.out_buttons = {"img": self.btn_img, "tab": self.btn_tables, "pptx": self.btn_slides, "si": self.btn_si}
        self.btn_all = self.btn_img                              # export_all_tabs sperrt ihn während des Exports
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, TABS.PAGE_TOP, 0, 0)
        rv.setSpacing(0)
        rv.addWidget(self.right_tabs, 1)
        rv.addWidget(TABS.side_bar(self.lbl_count, *self.out_buttons.values(), stretch_at=1))
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
        row = QHBoxLayout()                                     # „SI (Word)“ steht in der Fußleiste (Entscheidung 182)
        self.btn_dp = QPushButton(T("export_dp_btn"))
        self.btn_dp.setToolTip(T("export_dp_tip"))
        self.btn_dp.clicked.connect(self.main.export_datapack)
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
        """Kacheln eines Tabs: [(Teil-Index, Bezeichnung „Tab · Teil“, Name auf der Kachel, Test, Kennung)]; ein Bild:
        der Tabname (die Marke oben nennt den Tab ohnehin)."""
        ps, name = parts(self.main, k), self._name(k)
        if len(ps) == 1 and not ps[0][0]:
            return [(0, name, name, None, "")]
        return [(i, f"{name} · {lab}", lab, p, pid) for i, (lab, p, pid) in enumerate(ps)]

    def _si_only(self, k):
        """Tabellen/Texte nur für die SI (Schlüssel im Tab, Auswahl hier): [(Bezeichnung, Kennung)]."""
        m, name, out = self.main, self._name(k), []
        if k == "overlay" and any(e.get("kind") == "calc" for e in m.ov_state.get("entries") or []):
            out.append((f"{name} · {T('export_part_tdt')}", "tdt"))
        if k == "irms" and m.irms_state.get("irc_file"):
            out.append((f"{name} · {T('export_part_irc')}", "irc"))
        if k in ("xray", "dft") and (getattr(m, m._tab_spec(k)[2]).get("entries")):
            out.append((f"{name} · HOMA", "homa"))
        return out

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
        """Formate, SI-Teile und Kacheln aus dem Zustand (Punkte der Leiste, ε-Serien); baut nichts und schreibt nichts.
        Die Auswahl ist gespeichert (`is_on`, Entscheidung 182). Vorschaubilder: aus dem Zwischenspeicher sofort,
        sonst erst ein Symbol und das Bild danach einzeln je Durchlauf der Ereignisschleife (nie sekundenlang lesen)."""
        from elucida.app.tiles import cached_pixmap
        self.sync_formats()
        self.sync_si()
        old = self.cards[self.current] if self.current is not None and self.current < len(self.cards) else None
        old = old and (old.key, old.label)                      # Markierung (Link „In die SI“) übersteht Auffrischen
        self.cards, self.current, self._thumb_queue = [], None, []
        for k in self.main.export_keys():
            for i, lab, name, pred, pid in self._items(k):
                c = ExportCard(self, k, i, lab, name, pred, k in WORD_KEYS, pid)
                path = self.thumb(k, i, pred)
                pm = cached_pixmap(path, c.pic) if path else None
                c.set_thumb(None) if path and pm is None else c.set_pixmap(pm)
                if path and pm is None:
                    self._thumb_queue.append((c, path))
                self.cards.append(c)
            for lab, pid in self._si_only(k):
                c = ExportCard(self, k, -1, lab, lab.split(" · ", 1)[-1], None, True, pid, si_only=True)
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
        self.sync_selection()
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
        """Klick, Leertaste: gespeicherte Änderung mit Rückgängig (Entscheidung 182)."""
        set_on(self.main, [(card.key, card.pid, not card.selected)])
        self.sync_selection()

    def sync_selection(self):
        """Auswahl aller Kacheln aus dem Zustand, dann Zahl und Knöpfe."""
        for c in self.cards:
            c.set_selected(is_on(self.main, c.key, c.pid))
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
        QTimer.singleShot(0, self, self._place_counts)                 # der offene Reiter ist halbfett
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
        QTimer.singleShot(0, self, self._place_counts)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        QTimer.singleShot(0, self, self._fit_segments)

    def select_all(self, on):
        """„Alle · Keine“: nur das offene Segment; ein Rückgängig-Schritt."""
        set_on(self.main, [(c.key, c.pid, on) for c in self.shown()])
        self.sync_selection()

    def chosen(self):
        return [c for c in self.cards if c.selected]

    def counts(self):
        """Zahl je Knopf aus der Auswahl: Karten (Bilder, PPTX, SI) bzw. Tabs (Tabellen)."""
        sel = self.chosen()
        return {b: len({c.key for c in sel if b in c.feeds}) if b == "tab" else sum(b in c.feeds for c in sel)
                for b in self.out_buttons}

    def sync_button(self, *_):
        self.sync_segments()
        sel = self.chosen()
        self.lbl_count.setText(T("export_n_of", n=len(sel), m=len(self.cards)))
        for b, n in self.counts().items():
            btn, on = self.out_buttons[b], bool(n or b == "si" and sel)   # SI: Teile links auch ohne gewählte Abbildung
            btn.setEnabled(on)                                   # ohne Wirkung: grau, Tooltip nennt den Grund
            btn.setToolTip(T(f"export_btn_{b}_tip", n=n) if on else
                           T("export_btn_none_tip") if not sel else T(f"export_btn_{b}_empty"))

    def jobs(self, button):
        """[(Tab, Test auf den Dateinamen)] für „Bilder“ (Dateien der gewählten Karten außer Tabellen) bzw.
        „Tabellen“ (Tabellen der Tabs mit gewählter Karte); je Tab ein Export. Der Test ist nie None: ein Export aus
        diesem Tab legt nichts in den Papierkorb (Kachel-Export, `retire_exports`)."""
        from elucida.app import project as PRJ
        table = lambda n: PRJ.export_kind(n) == PRJ.TABLES                # noqa: E731
        preds = {}
        for c in self.chosen():
            if button in c.feeds:
                preds.setdefault(c.key, []).append(c.pred)
        if button == "tab":
            return [(k, table) for k in preds]
        return [(k, lambda n, ps=None if None in ps else tuple(ps): not table(n) and (ps is None or any(p(n) for p in ps)))
                for k, ps in preds.items()]

    def run(self):
        """„Bilder“ (auch Strg+E in diesem Tab)."""
        jobs = self.jobs("img")
        return self.main.export_all_tabs(jobs) if jobs else self.main.notify(T("export_btn_none_tip"))

    def run_tables(self):
        jobs = self.jobs("tab")
        return self.main.export_all_tabs(jobs) if jobs else self.main.notify(T("export_btn_none_tip"))

    def run_slides(self):
        keys = list(dict.fromkeys(c.key for c in self.chosen() if "pptx" in c.feeds))
        return self.main.export_pptx_slides(keys, cards=True) if keys else self.main.notify(T("export_btn_none_tip"))

    def run_si(self):
        return self.main.export_si_dialog()

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
