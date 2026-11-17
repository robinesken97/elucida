"""Kachelraster der beiden Export-Tabs (Verbindung › Export, Projektseite › Export; Entscheidungen 96–100, Skizze
audit/export-skizze-3.html): kleine Kacheln in EINEM Raster ohne Rahmen um Gruppen. Volle Zeilen sind gleich breit (die
Spalten teilen die Breite), nur die letzte Zeile einer Gruppe darf kürzer sein; Kopfzeilen (Gruppen der Publikation)
stehen über die volle Breite.

Kante (Robin): Kopfzeile, ihre Linie, Legende, Kartenkante (Vorschau), Name und Marke beginnen an derselben linken Kante
`EDGE`; die Kachel reicht um ihren Auswahlrahmen (STYLE.TILE_SEL) darüber hinaus, der Rahmen liegt also außen.
Verbindung: oben Punkt + Datenart in ihrer Farbe (STYLE.method_color), Vorschau im Ton der Datenart, Pille „SI“.
Projekt: oben rechts die Zahl der Abbildungen in der SI, unten an der Vorschau ein Farbstreifen mit festen Plätzen je
Datenart (vorhanden = Farbe, sonst Linienfarbe), darunter Nummer + Summenformel."""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from elucida.app import style as STYLE
from elucida.app.i18n import T

EDGE = STYLE.TILE_SEL                                     # linke Kante aller Inhalte im Raster (Platz für den Rahmen)


_CACHE = {}                                               # (Pfad, mtime, Größe, Faktor, Struktur, dunkel) -> QPixmap


def _cache_key(path, label, structure):
    from elucida.app import canvas_theme as CANVAS
    try:
        mt = path.stat().st_mtime_ns if hasattr(path, "stat") else __import__("os").stat(path).st_mtime_ns
    except OSError:
        return None
    return (str(path), mt, max(1.0, label.devicePixelRatioF()), structure, STYLE._mode == "dark" and CANVAS._dark)


def cached_pixmap(path, label, structure=False):
    """Schon gelesenes Vorschaubild (unverändert seit dem Lesen) oder None."""
    k = _cache_key(path, label, structure)
    return _CACHE.get(k) if k else None


def tile_pixmap(path, label, structure=False):
    k = _cache_key(path, label, structure)
    if k in _CACHE:
        return _CACHE[k]
    pm = _tile_pixmap(path, label, structure)
    if k is not None:
        if len(_CACHE) > 400:                             # shortcut: grob geleert statt LRU, reicht für ein Projekt
            _CACHE.clear()
        _CACHE[k] = pm
    return pm


def _tile_pixmap(path, label, structure=False):
    """Vorschaubild einer Kachel, nie beim Anzeigen gerendert. structure (Projektkacheln, .elucida/thumb.png): dieselbe
    Skalierung wie die Karten der Übersicht (welcome.scaled, ganze Struktur mit Rand). Abbildungen: füllen die Fläche
    (Seitenverhältnis, 3 px Rand), gelesen in Zielgröße (QImageReader; SVG wie die Mnova-Spektren scharf statt
    hochgezogen). Dunkler Canvas: nur das Bild wird umgerechnet (canvas_theme.dark_image)."""
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QImageReader
    from elucida.app import canvas_theme as CANVAS
    from elucida.app.welcome import scaled
    ratio = max(1.0, label.devicePixelRatioF())
    if structure:
        pm = scaled(str(path), STYLE.TILE_W - 16, STYLE.TILE_THUMB_H - round(STYLE.TILE_THUMB_H * 44 / 148), ratio)
    else:
        w, h = (STYLE.TILE_W - 6) * ratio, (STYLE.TILE_THUMB_H - 6) * ratio
        r = QImageReader(str(path))
        size = r.size()
        if size.isValid() and size.width() > 0 and size.height() > 0:
            f = min(w / size.width(), h / size.height())
            r.setScaledSize(QSize(max(1, round(size.width() * f)), max(1, round(size.height() * f))))
        img = r.read()
        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(ratio)
    if pm.isNull() or not (STYLE._mode == "dark" and CANVAS._dark):
        return pm
    out = QPixmap.fromImage(CANVAS.dark_image(pm.toImage()))
    out.setDevicePixelRatio(ratio)
    return out


def kind_pixmap(kind, key, ratio=1.0):
    """Platzhalter je Art in der Farbe der Datenart (eine Funktion, hell/dunkel gleich; Formen der Skizze
    export-skizze-2): stick (NMR, IR, MS, PXRD), band (UV-Vis, TD-DFT, SEC, NICS), twopeaks (Fluoreszenz), decay
    (Kinetik, Abklingkurve), loop (CV, H-Cell), derivative (EPR), molecule (Struktur, Packung, Geometrie), lobes
    (Orbitale, Spindichte, Hyperfein, NTO), table (Tabellen), arrow (Synthese A → B), page (Berichte), curve (sonst)."""
    from PySide6.QtGui import QPainterPath
    w, h = 64, 40
    pm = QPixmap(round(w * ratio), round(h * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    col = QColor(STYLE.method_color(key))
    p.setPen(QPen(col, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    def path(*pts):                                      # (x, y) und Kurven ((c1, c2, end))
        pp = QPainterPath(QPointF(*pts[0]))
        for q in pts[1:]:
            if len(q) == 3:
                pp.cubicTo(QPointF(*q[0]), QPointF(*q[1]), QPointF(*q[2]))
            else:
                pp.lineTo(QPointF(*q))
        p.drawPath(pp)
    if kind == "stick":
        p.drawLine(QPointF(4, 36), QPointF(60, 36))
        for x, y in ((12, 20), (20, 8), (27, 26), (36, 14), (44, 28), (52, 18)):
            p.drawLine(QPointF(x, 36), QPointF(x, y))
    elif kind == "band":
        path((4, 34), ((20, 34), (22, 6), (32, 6)), ((42, 6), (44, 30), (60, 30)))
    elif kind == "twopeaks":
        path((4, 34), ((14, 34), (16, 8), (22, 8)), ((28, 8), (28, 34), (34, 34)))
        path((30, 34), ((40, 34), (42, 14), (48, 14)), ((54, 14), (54, 34), (60, 34)))
    elif kind == "decay":
        path((6, 6), ((18, 30), (30, 34), (60, 35)))
        p.drawLine(QPointF(4, 36), QPointF(60, 36))
    elif kind == "loop":
        path((6, 26), ((24, 26), (30, 6), (40, 8)), ((50, 10), (52, 16), (58, 16)))
        path((58, 20), ((50, 20), (46, 34), (36, 32)), ((26, 30), (22, 22), (6, 22)))
    elif kind == "derivative":
        path((4, 20), (20, 20), ((26, 20), (26, 4), (30, 4)), ((34, 4), (34, 36), (38, 36)),
             ((42, 36), (42, 20), (48, 20)), (60, 20))
    elif kind == "molecule":
        pts = [(12, 26), (24, 12), (38, 22), (52, 10), (40, 34)]
        for a, b in ((0, 1), (1, 2), (2, 3), (2, 4)):
            p.drawLine(QPointF(*pts[a]), QPointF(*pts[b]))
        p.setBrush(col)
        for x, y in pts:
            p.drawEllipse(QPointF(x, y), 3.6, 3.6)
    elif kind == "lobes":
        p.drawEllipse(QRectF(10, 8, 20, 24))
        p.drawEllipse(QRectF(34, 8, 20, 24))
        p.drawLine(QPointF(30, 20), QPointF(34, 20))
    elif kind == "table":
        p.drawRoundedRect(QRectF(8, 4, 48, 32), 2, 2)
        for y in (12, 20, 28):
            p.drawLine(QPointF(8, y), QPointF(56, y))
        for x in (24, 40):
            p.drawLine(QPointF(x, 4), QPointF(x, 36))
    elif kind == "arrow":
        f = QFont()
        f.setPixelSize(13)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(2, 8, 14, 24), Qt.AlignCenter, "A")
        p.drawText(QRectF(48, 8, 14, 24), Qt.AlignCenter, "B")
        p.drawLine(QPointF(18, 20), QPointF(45, 20))
        p.drawLine(QPointF(40, 15), QPointF(45, 20))
        p.drawLine(QPointF(40, 25), QPointF(45, 20))
    elif kind == "page":
        p.drawRoundedRect(QRectF(20, 3, 24, 34), 2, 2)
        for y in (11, 17, 23, 29):
            p.drawLine(QPointF(25, y), QPointF(39, y))
    else:                                                 # „curve“
        path((4, 30), ((16, 30), (20, 12), (30, 16)), ((40, 20), (46, 8), (60, 10)))
    p.end()
    return pm


class SlotBar(QWidget):
    """Farbstreifen am unteren Rand der Vorschau: feste Plätze [(Name, Methodenschlüssel, vorhanden)], 1 px Lücke."""

    def __init__(self, slots, parent):
        super().__init__(parent)
        self.slots = slots
        self.setFixedHeight(STYLE.TILE_SLOT_H)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, ev):
        p = QPainter(self)
        n = len(self.slots)
        w = (self.width() - (n - 1)) / max(1, n)
        for i, (_, key, on) in enumerate(self.slots):
            p.fillRect(QRectF(i * (w + 1), 0, w, self.height()),
                       QColor(STYLE.method_color(key) if on else STYLE.colors()["border"]))


class Legend(QWidget):
    """Eine Zeile über dem Raster: kleines Quadrat + Kürzel je Platz des Farbstreifens."""

    def __init__(self, slots):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(EDGE, 0, 0, 0)
        h.setSpacing(4)
        for text, key in slots:
            sq = QLabel(objectName="tileDot")
            sq.setFixedSize(8, 8)
            sq.setStyleSheet(f"background: {STYLE.method_color(key)};")
            h.addWidget(sq)
            h.addWidget(QLabel(text, objectName="tileLegend"))
            h.addSpacing(6)
        h.addStretch(1)


class Tile(QWidget):
    """Eine Kachel. mark: (Text, Methodenschlüssel) oder None; pill: None, (lesen, setzen) für „SI“ oder ein Text (Zahl);
    slots: Farbstreifen der Projektseite oder None."""
    clicked = Signal(object, object)                    # Kachel, Mausereignis

    def __init__(self, mark, name, pill=None, rich_name=False, selectable=True, tip="", slots=None, zip_pill=None):
        super().__init__()
        self.setObjectName("tile")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.selectable, self.selected = selectable, False
        self.setCursor(Qt.PointingHandCursor if selectable else Qt.ArrowCursor)
        self.setToolTip(tip)
        self.setFixedHeight(STYLE.TILE_H + 2 * STYLE.TILE_SEL)
        v = QVBoxLayout(self)
        v.setContentsMargins(*(STYLE.TILE_SEL,) * 4)    # Inhalt genau auf der Kante, der Rahmen liegt außen
        v.setSpacing(2)
        cap = QHBoxLayout()
        cap.setContentsMargins(0, 0, 0, 0)
        cap.setSpacing(4)
        if mark is not None:
            dot = QLabel(objectName="tileDot")
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background: {STYLE.method_color(mark[1])};")
            cap.addWidget(dot)
            m = QLabel(mark[0], objectName="tileCap")
            m.setStyleSheet(f"color: {STYLE.method_color(mark[1])};")
            cap.addWidget(m)
        cap.addStretch(1)
        capw = QWidget()
        capw.setFixedHeight(STYLE.TILE_CAP_H)
        capw.setLayout(cap)
        v.addWidget(capw)
        self.sel = QFrame(self, objectName="tileSel")     # Auswahlrahmen nur um die Vorschau, 3 px außen (Entwurf)
        self.sel.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.pic = QLabel(objectName="tileThumb", alignment=Qt.AlignCenter)
        self.pic.setFixedHeight(STYLE.TILE_THUMB_H)
        if mark is not None:                             # Vorschaufläche im Ton der Datenart (Entscheidung 99)
            self.pic.setStyleSheet(f"background: {STYLE.method_tint(mark[1])};")
        v.addWidget(self.pic)
        self.slotbar = SlotBar(slots, self) if slots else None   # nicht über den Canvas-Effekt der Vorschau
        from elucida.app.welcome import EndElided
        self.name = QLabel(name, objectName="tileName") if rich_name else EndElided(name, objectName="tileName")
        if rich_name:
            self.name.setTextFormat(Qt.RichText)
        v.addWidget(self.name)
        self.pill, self.pill_top = None, False           # Pille/Zahl in der Vorschau oben rechts
        if isinstance(pill, tuple):                      # „SI“: schaltet (lesen, setzen)
            self.pill = QPushButton("SI", self, objectName="siPill", checkable=True)
            self.pill.setCursor(Qt.PointingHandCursor)
            self.pill.setFocusPolicy(Qt.NoFocus)
            self.pill.setChecked(bool(pill[0]()))
            self.pill.toggled.connect(lambda on: pill[1](on))
        elif pill is not None:                           # Zahl (Projekt: Abbildungen in der SI)
            self.pill = QLabel(str(pill), self, objectName="tileCount", alignment=Qt.AlignCenter)
        self.zip = None                                  # Projekt: Pille „Zip“ oben links = im Datensatz (118)
        if zip_pill is not None:
            self.zip = QPushButton(T("pub_exp_zip"), self, objectName="siPill", checkable=True)
            self.zip.setCursor(Qt.PointingHandCursor)
            self.zip.setFocusPolicy(Qt.NoFocus)
            self.zip.setChecked(bool(zip_pill[0]()))
            self.zip.toggled.connect(lambda on: zip_pill[1](on))
        self.set_selected(False)

    def set_thumb(self, pixmap, kind=None, key="other"):
        """Vorschau (QPixmap) oder Platzhalter der Art `kind` in der Farbe von `key` (kind_pixmap)."""
        if pixmap is None or pixmap.isNull():
            self.pic.setProperty("placeholder", True)
            self.pic.setPixmap(kind_pixmap(kind or "curve", key, max(1.0, self.pic.devicePixelRatioF())))
        else:
            self.pic.setPixmap(pixmap)

    def set_selected(self, on):
        self.selected = bool(on) and self.selectable            # nicht wählbare Kacheln (Tabellen) nie: Alle, Leertaste
        self.setProperty("selected", self.selected)
        self.sel.setProperty("selected", self.selected)
        self.sel.style().unpolish(self.sel)
        self.sel.style().polish(self.sel)

    def set_current(self, on):
        self.setProperty("current", bool(on))
        self.sel.setProperty("current", bool(on))
        self.sel.style().unpolish(self.sel)
        self.sel.style().polish(self.sel)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        s = STYLE.TILE_SEL
        self.layout().activate()                         # Vorschau an ihrem Platz, bevor der Rahmen ihr folgt
        self.sel.setGeometry(self.pic.geometry().adjusted(-s, -s, s, s))
        self.sel.lower()
        if self.slotbar is not None:                     # am unteren Rand der Vorschau, innerhalb ihres Rahmens
            g = self.pic.geometry()
            self.slotbar.setGeometry(g.x() + 1, g.bottom() - STYLE.TILE_SLOT_H, g.width() - 2, STYLE.TILE_SLOT_H)
            self.slotbar.raise_()
        if self.pill is not None:
            self.pill.adjustSize()
            top = STYLE.TILE_SEL if self.pill_top else STYLE.TILE_SEL + STYLE.TILE_CAP_H + 5
            self.pill.move(self.width() - self.pill.width() - STYLE.TILE_SEL - (0 if self.pill_top else 4), top)
            self.pill.raise_()
        if self.zip is not None:                         # gegenüber der Zahl, auf derselben Höhe
            self.zip.adjustSize()
            self.zip.move(STYLE.TILE_SEL + 4, STYLE.TILE_SEL + STYLE.TILE_CAP_H + 5)
            self.zip.raise_()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton and self.selectable:
            self.clicked.emit(self, ev)
        super().mouseReleaseEvent(ev)


class TileGrid(QWidget):
    """Raster aus Kacheln und Kopfzeilen (`set_rows([(Kopf oder None, [Kacheln])])`). Spaltenzahl nach der Breite
    (Mindestbreite STYLE.TILE_W), Kartenbreite = Breite / Spalten: alle vollen Zeilen enden an derselben Kante. Karten,
    Kopfzeilen und Linie beginnen bei EDGE; die Kachel liegt um TILE_SEL weiter außen (Auswahlrahmen außen)."""

    def __init__(self):
        super().__init__()
        self.groups, self.tiles, self.cols, self.only = [], [], 1, None

    def set_filter(self, tiles):
        """Nur diese Kacheln zeigen (Segmente im Tab „Export“, Entscheidung 102); None = alle. Die Kacheln bleiben
        dieselben Objekte (Auswahl und Pillen bleiben)."""
        self.only = None if tiles is None else {id(t) for t in tiles}
        self._place()

    def set_rows(self, groups):
        for w in self.children():
            if isinstance(w, QWidget):
                w.hide()
                w.deleteLater()
        self.groups, self.links = [], {}
        for head, tiles in groups:
            right = None
            if isinstance(head, tuple):                   # (Text, Verweise rechts als Rich-Text, Klick(href))
                head, rhtml, on_link = head
                right = QLabel(rhtml, self, objectName="tileGroupLinks")
                right.setTextFormat(Qt.RichText)
                right.linkActivated.connect(on_link)
            lab = QLabel(head, self, objectName="tileGroup") if head else None
            if lab is not None:
                lab.setIndent(0)                          # QLabel rückt Text mit Rahmenlinie sonst um ½ „x“ ein
                if right is not None:
                    self.links[id(lab)] = right
                    right.show()
            for t in tiles:
                t.setParent(self)
                t.show()
            if lab is not None:
                lab.show()
            self.groups.append((lab, tiles))
        self.tiles = [t for _, ts in self.groups for t in ts]
        self._place()

    def _place(self):
        s, gx, gy = STYLE.TILE_SEL, STYLE.TILE_GAP_X, STYLE.TILE_GAP_Y
        W = max(self.width() - 2 * EDGE, STYLE.TILE_W)  # Breite der Karten (ohne die Ränder für den Rahmen)
        self.cols = cols = max(1, (W + gx) // (STYLE.TILE_W + gx))
        tw = (W - (cols - 1) * gx) / cols
        y = 0
        for lab, all_tiles in self.groups:
            tiles = [t for t in all_tiles if self.only is None or id(t) in self.only]
            for t in all_tiles:
                t.setVisible(self.only is None or id(t) in self.only)
            if lab is not None:
                lab.setVisible(bool(tiles))
                right = self.links.get(id(lab))
                if right is not None:
                    right.setVisible(bool(tiles))
                if not tiles:
                    continue
                h = lab.sizeHint().height()
                lab.setGeometry(EDGE, y, W, h)
                if right is not None:                     # rechts auf der Kopfzeile, über der Linie
                    right.adjustSize()
                    right.move(EDGE + W - right.width(), y + (h - right.height()) // 2 - 1)
                    right.raise_()
                y += h + gy
            th = max((t.height() for t in tiles), default=STYLE.TILE_H + 2 * s)
            for i, t in enumerate(tiles):
                r, c = divmod(i, cols)
                x0 = EDGE + round(c * (tw + gx))
                x1 = EDGE + round(c * (tw + gx) + tw)
                t.setGeometry(x0 - s, y + r * (th + gy), x1 - x0 + 2 * s, th)
            if tiles:
                y += (-(-len(tiles) // cols)) * (th + gy)
        self.setMinimumHeight(y)
        self.setFixedHeight(y)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._place()
