"""Erscheinungsbild: Qt-Stil Fusion mit eigener Palette (hell/dunkel), zentralem Stylesheet und Symbolen.

Fusion sieht auf Windows, macOS und Linux gleich aus. Die Abbildungen (matplotlib) sind davon nicht betroffen.
Symbole sind kleine SVGs (Strichzeichnungen), werden in der Textfarbe gerendert und als PNG für das Stylesheet
abgelegt (PNG braucht kein Qt-Bildformat-Plugin)."""
from __future__ import annotations

from pathlib import Path

import shiboken6
from PySide6.QtCore import QByteArray, QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QMessageBox, QScrollArea, QSizePolicy, QPushButton, QStyle,
                               QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QVBoxLayout, QWidget)

COLORS = {
    # Abstufung wie im Entwurf: Seite < Karte, Felder etwas abgesetzt, warme Grautöne, dezente Ränder
    "light": dict(window="#F4F3EF", card="#FFFFFF", field="#FAF9F6", button="#FFFFFF", hover="#EFEEE9",
                  border="#E2E0DA", border_strong="#C8C6BE", text="#1F1E1C", text2="#6B6A64",
                  disabled="#ABA9A2", accent="#2E6BD6", accent_hover="#255BBB", on_accent="#FFFFFF",
                  alt="#F7F6F3", check_border="#9A988F"),
    "dark": dict(window="#141413", card="#1C1C1B", field="#111110", button="#232322", hover="#2B2B29",
                 border="#2D2D2B", border_strong="#42423F", text="#EDECE8", text2="#9D9B94",
                 disabled="#5E5D58", accent="#3D7CE0", accent_hover="#5089E6", on_accent="#FFFFFF",
                 alt="#181817", check_border="#7A7872"),
}

_SVG = {
    "open": '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l2 2h9A1.5 1.5 0 0 1 21 9.5v8a1.5 1.5 0 0 1-1.5 1.5h-15'
            'A1.5 1.5 0 0 1 3 17.5z"/>',
    "export": '<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 20h14"/>',
    "reveal": '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l2 2h9A1.5 1.5 0 0 1 21 9.5v8a1.5 1.5 0 0 1-1.5 1.5h-15'
              'A1.5 1.5 0 0 1 3 17.5z"/><path d="M10 16l4.5-4.5M11.5 11.5h3v3"/>',
    "reset": '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3"/><path d="M4.5 4.5v4h4"/>',
    "compound": '<path d="M12 3l7.8 4.5v9L12 21l-7.8-4.5v-9z"/><circle cx="12" cy="12" r="3.6"/>',
    "new": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M13 12v6M10 15h6"/>',
    "save": '<path d="M5 4h11l3 3v13H5z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>',
    "undo": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "redo": '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
    "add": '<path d="M12 5v14M5 12h14"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6"/><path d="M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    "move_up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "move_down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "up": '<path d="M7 14.5 12 9.5l5 5"/>',
    "down": '<path d="M7 9.5l5 5 5-5"/>',
    "check": '<path d="M6 12.5l4 4 8-9"/>',
    "dash": '<path d="M7 12h10"/>',
    "copy": '<rect x="8.5" y="8.5" width="11" height="11" rx="1.5"/>'
            '<path d="M15.5 8.5V6A1.5 1.5 0 0 0 14 4.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
}

HINT_CSS = "color: gray;"            # Hinweistexte
WARN_CSS = "color: #d9534f;"         # Warnungen (fehlende Molmasse, Farbe unvollständig)
NOTE_CSS = "color: #c77c0e;"         # Hinweise, die man beachten sollte, aber kein Fehler sind (orange)


def make_form(parent=None):
    """QFormLayout mit gleichem Aussehen auf allen Systemen (macOS: sonst rechtsbündige Beschriftungen und
    Felder in Mindestbreite, dadurch abgeschnittene Platzhalter)."""
    f = QFormLayout(parent)
    f.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    f.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
    f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    f.setRowWrapPolicy(QFormLayout.DontWrapRows)
    return f


def align_forms(forms):
    """Beschriftungsspalte aller Formulare gleich breit machen."""
    labels = [f.itemAt(i, QFormLayout.LabelRole).widget() for f in forms for i in range(f.rowCount())
              if f.itemAt(i, QFormLayout.LabelRole) and f.itemAt(i, QFormLayout.LabelRole).widget()]
    width = max((lb.sizeHint().width() for lb in labels), default=0)
    # höchstens ~32 Zeichen breit: längere Beschriftungen brechen um, statt die Spalte (und damit die Abbildung) zu
    # verbreitern – wichtig bei breiterer Schrift (Windows)
    if labels:
        width = min(width, labels[0].fontMetrics().averageCharWidth() * 32)
    for lb in labels:
        if isinstance(lb, QLabel):
            lb.setWordWrap(True)
        lb.setMinimumWidth(width)
        lb.setMaximumWidth(width)
        lb.setProperty("formlabel", True)


def compact(*spins):
    """Zahlenfelder nicht über die ganze Breite ziehen."""
    for sp in spins:
        sp.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sp.setMinimumWidth(90)


_mode = "light"
base_style = ""                      # Name des Qt-Stils (app.style() ist mit Stylesheet ein Proxy)


def colors():
    return COLORS[_mode]


def _render(name, color, px, stroke=1.8):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
           f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{_SVG[name]}</svg>')
    img = QImage(px, px, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(0, 0, px, px))
    p.end()
    return img


def icon(name, color=None):
    """QIcon in Textfarbe (oder `color`), scharf auch auf HiDPI-Bildschirmen."""
    ic = QIcon()
    for px in (16, 32, 48, 64):
        ic.addPixmap(QPixmap.fromImage(_render(name, color or colors()["text"], px)))
    return ic


def pixmap(name, size=16, color=None):
    ratio = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
    pm = QPixmap.fromImage(_render(name, color or colors()["text"], int(round(size * ratio))))
    pm.setDevicePixelRatio(ratio)
    return pm


def list_button(txt):
    """Knopf über einer Liste: ↑/↓ nur als Symbol (mit Tooltip), Entfernen mit Papierkorb,
    Hinzufügen („…“) mit Plus."""
    from elucida.app.i18n import T
    b = QPushButton(txt)
    if txt in ("↑", "↓"):
        b.setText("")
        b.setIcon(icon("move_up" if txt == "↑" else "move_down"))
        b.setToolTip(T("move_up" if txt == "↑" else "move_down"))
    elif txt == T("remove"):
        b.setIcon(icon("trash"))
    elif txt.endswith("…"):
        b.setIcon(icon("add"))
    return b


def hide_when_empty(table):
    """Dateiliste ohne Einträge ausblenden (Leer-Zustand: die Anleitung rechts nennt Dateien und ersten Schritt)."""
    upd = lambda *_: shiboken6.isValid(table) and table.setVisible(table.model().rowCount() > 0)   # Neuaufbau: gelöscht
    m = table.model()
    for sig in (m.rowsInserted, m.rowsRemoved, m.modelReset):
        sig.connect(upd)
    upd()


class _CheckDelegate(QStyledItemDelegate):
    """Kästchen ohne Text mittig in der Zelle (Qt setzt es sonst an den linken Rand, z. B. unter breiten Überschriften).
    Zeichnen und Klicken über dasselbe Rechteck; Zellen mit Text bleiben unverändert."""

    def _box(self, option, index):
        if index.data(Qt.DisplayRole) or index.data(Qt.CheckStateRole) is None:
            return None
        o = QStyleOptionViewItem(option)
        o.features |= QStyleOptionViewItem.HasCheckIndicator
        st = option.widget.style() if option.widget is not None else QApplication.style()
        r = st.subElementRect(QStyle.SE_ItemViewItemCheckIndicator, o, option.widget)
        r.moveCenter(option.rect.center())
        return r

    def paint(self, painter, option, index):
        r = self._box(option, index)
        if r is None:
            return super().paint(painter, option, index)
        st = option.widget.style() if option.widget is not None else QApplication.style()
        o = QStyleOptionViewItem(option)
        self.initStyleOption(o, index)
        o.features &= ~QStyleOptionViewItem.HasCheckIndicator      # nur Hintergrund/Auswahl der Zelle
        st.drawControl(QStyle.CE_ItemViewItem, o, painter, option.widget)
        c = QStyleOptionViewItem(option)
        c.rect = r
        cs = Qt.CheckState(index.data(Qt.CheckStateRole))
        c.state &= ~(QStyle.State_On | QStyle.State_Off | QStyle.State_NoChange)
        c.state |= {Qt.Checked: QStyle.State_On, Qt.PartiallyChecked: QStyle.State_NoChange}.get(cs, QStyle.State_Off)
        st.drawPrimitive(QStyle.PE_IndicatorItemViewItemCheck, c, painter, option.widget)

    def editorEvent(self, event, model, option, index):
        r = self._box(option, index)
        if r is not None and event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
                                              QEvent.MouseButtonDblClick):
            if event.button() != Qt.LeftButton or not r.contains(event.position().toPoint()):
                return False
            fl = index.flags()
            if event.type() == QEvent.MouseButtonRelease and fl & Qt.ItemIsUserCheckable and fl & Qt.ItemIsEnabled:
                cs = Qt.CheckState(index.data(Qt.CheckStateRole))
                model.setData(index, (Qt.Unchecked if cs == Qt.Checked else Qt.Checked).value, Qt.CheckStateRole)
            return True
        return super().editorEvent(event, model, option, index)


class HintLabel(QLabel):
    """Hinweiszeile, die ohne Text samt Zeilenabstand verschwindet (keine Leerzeile im Formular)."""

    def setText(self, text):
        super().setText(text)
        self.sync()

    def sync(self):
        p = self.parentWidget()
        if p is None:
            return
        vis = bool(self.text())
        form = next((fl for fl in p.findChildren(QFormLayout) if fl.indexOf(self) >= 0), None)
        if form is not None:
            form.setRowVisible(self, vis)
        else:
            self.setVisible(vis)


def card(title):
    """Gruppe als Karte, Titel und Ränder wie QGroupBox in den übrigen Tabs. Gibt (Karte, Inhalts-Widget) zurück."""
    frame = QFrame(objectName="card")
    v = QVBoxLayout(frame)
    v.setContentsMargins(20, 12, 20, 16)                     # Inhalt bündig mit QGroupBox (Rahmen + Padding)
    v.setSpacing(8)
    head = QHBoxLayout()
    t = QLabel(title, objectName="cardTitle")
    head.addWidget(t)
    head.addStretch(1)
    v.addLayout(head)
    body = QWidget()
    v.addWidget(body)
    return frame, body


FIELD_W = 120                     # einheitliche Breite der Zahlenfelder (Raster der linken Spalte)
WIDE_W = 2 * FIELD_W + 24          # Wertespalte: Listen, Textfelder, „[a] – [b]“ enden an einer Kante (Nutzerwunsch)
COLUMN_W = 538                    # linke Spalte in allen Tabs gleich breit (breiter nur, wenn Inhalt sonst abgeschnitten)
CHECKS_IN_FIELD_COLUMN = True     # Häkchen-Zeilen in der Wertespalte (eine Kante für alle Bedienelemente)


def _fw(fl, r):
    """Breite einer Formularzeile aus Beschriftung + Feld (Hinweis für die Einrück-Regel)."""
    li, fi = fl.itemAt(r, QFormLayout.LabelRole), fl.itemAt(r, QFormLayout.FieldRole)
    if li is None or fi is None:
        return 0
    return li.sizeHint().width() + fl.horizontalSpacing() + fi.sizeHint().width()


def _field_edge(root):
    """Wertespalte je Tab an einer Kante (siehe unten): Listen und Textfelder
    genau so breit, in Zeilen mit mehreren Teilen wächst das erste dehnbare Element (Dateiname, Textfeld, Lücke vor
    den Knöpfen) auf die Kante. Feste Breiten statt Formularrand: der würde die Mindestbreite der Spalte mitziehen."""
    from PySide6.QtWidgets import QAbstractScrollArea, QLineEdit
    forms = [fl for fl in root.findChildren(QFormLayout) if fl.parentWidget() is not None]
    items = [it for fl in forms for it in (fl.itemAt(r, QFormLayout.FieldRole) for r in range(fl.rowCount()))
             if it is not None]
    if not items:
        return
    for it in items:
        if it.widget() is not None:
            it.widget().ensurePolished()
    # Kante je Tab: mindestens WIDE_W, sonst die breiteste Zeile aus mehreren Teilen („[a] Ränder [b]“), aber nie
    # breiter als die feste Spalte (COLUMN_W abzüglich Ränder und Beschriftungsspalte) – die Abbildung bleibt gleich groß
    lab = max((fl.itemAt(r, QFormLayout.LabelRole).widget().minimumWidth() for fl in forms for r in range(fl.rowCount())
               if fl.itemAt(r, QFormLayout.LabelRole) is not None and fl.itemAt(r, QFormLayout.LabelRole).widget()),
              default=0)
    room = COLUMN_W - 2 * 12 - 2 * 16 - lab - 12 - 10          # Reserve: verschachtelte Karten, Klappkarten
    wide = max([WIDE_W] + [h for h in (it.sizeHint().width() for it in items if it.layout() is not None) if h <= room])
    stretchy = (QLineEdit, QComboBox, QAbstractScrollArea)
    for fl in forms:
        fl.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
    for it in items:
        w, lay = it.widget(), it.layout()
        if isinstance(w, stretchy) and w.maximumWidth() != FIELD_W:
            w.setFixedWidth(wide)
        elif isinstance(lay, QHBoxLayout) and lay.sizeHint().width() < wide:
            extra = wide - lay.sizeHint().width()
            for i in range(lay.count()):
                sub_ = lay.itemAt(i)
                x = sub_.widget()
                if sub_.spacerItem() is not None and sub_.expandingDirections() & Qt.Horizontal:
                    sp = sub_.spacerItem()
                    sp.changeSize(sp.sizeHint().width() + extra, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
                elif (isinstance(x, stretchy) or (isinstance(x, QLabel) and lay.stretch(i) > 0)) and \
                        x.maximumWidth() != FIELD_W:
                    x.setFixedWidth(x.sizeHint().width() + extra)
                else:
                    continue
                lay.invalidate()
                break


def tidy(root):
    """Linke Spalte ruhiger: Zeilenabstand 8 px, einzelne Knöpfe in Formularen in natürlicher Breite statt als
    Balken über die ganze Karte, reine Symbol-Knöpfe (↑/↓) quadratisch. Vor dem Bestimmen der Spaltenbreite aufrufen."""
    from PySide6.QtWidgets import QGroupBox
    top = root.layout()
    if isinstance(top, QVBoxLayout):                          # Spalte: gleicher Rand und Abstand zwischen Karten
        top.setContentsMargins(12, 12, 12, 12)
        top.setSpacing(12)
    for g in root.findChildren(QGroupBox):                    # Karten: gleicher Innenrand (oben sitzt der Titel)
        if g.layout() is not None and not any(isinstance(f, Fold) and f.group is g for f in g.children()):
            g.layout().setContentsMargins(16, 8, 16, 16)       # Raster 4/8/12/16
    for fl in root.findChildren(QFormLayout):
        fl.setVerticalSpacing(8)
        fl.setHorizontalSpacing(12)
        for r in range(fl.rowCount()):
            it = fl.itemAt(r, QFormLayout.SpanningRole)
            if it is not None and isinstance(it.widget(), QPushButton):
                it.widget().setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    for b in root.findChildren(QPushButton):
        if not b.text() and not b.icon().isNull():
            b.setFixedWidth(34)
    for x in root.findChildren(QAbstractSpinBox) + root.findChildren(QComboBox):
        x.setFocusPolicy(Qt.StrongFocus)                        # siehe _WheelGuard
    # Raster je Karte: alle Zahlenfelder gleich breit (FIELD_W), zweite Werte einer Zeile („[5] Ränder [5 %]“) in einer
    # gemeinsamen Spalte (Beschriftungen davor je Formular gleich breit), Text/Listen bis zum rechten Rand.
    from PySide6.QtWidgets import QCheckBox
    for sp in root.findChildren(QAbstractSpinBox):
        sp.setProperty("fieldw", True)                       # _WheelGuard setzt die Breite nach dem Stylesheet erneut
        sp.setFixedWidth(FIELD_W)
    # Auswahllisten dürfen schmaler sein als ihr längster Eintrag (Text wird gekürzt, die aufgeklappte Liste zeigt alles):
    # sonst bestimmt der längste Eintrag die Spaltenbreite – unter Windows (breitere Schrift) bis 470 px, Abbildung −35 %
    for cb in root.findChildren(QComboBox):
        cb.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        cb.setMinimumContentsLength(10)
    for fl in root.findChildren(QFormLayout):
        inner = []                                           # Beschriftungen zwischen zwei Werten
        for r in range(fl.rowCount()):
            it = fl.itemAt(r, QFormLayout.FieldRole) or fl.itemAt(r, QFormLayout.SpanningRole)
            lay = it.layout() if it is not None else None
            if not isinstance(lay, QHBoxLayout):
                continue
            ws = [lay.itemAt(i).widget() for i in range(lay.count()) if lay.itemAt(i).widget() is not None]
            if not any(isinstance(x, QAbstractSpinBox) for x in ws):
                continue
            for i, x in enumerate(ws):
                if 0 < i < len(ws) - 1 and isinstance(x, QLabel) and len(x.text().strip()) > 2:
                    inner.append(x)
                    if isinstance(ws[i - 1], QComboBox):     # „[keine ▾] g_lit [2,0055]“: Auswahl so breit wie ein Wert
                        ws[i - 1].setProperty("fieldw", True)
                        ws[i - 1].setFixedWidth(FIELD_W)
        if inner:
            wmax = max(x.sizeHint().width() for x in inner)
            for x in inner:
                x.setMinimumWidth(wmax)
        # „☑ Basislinie [0,15 V]“ (Zeile über die ganze Breite): Häkchen so breit wie die Beschriftungsspalte, damit
        # der Wert in der Wertespalte steht
        labels = [fl.itemAt(r, QFormLayout.LabelRole).widget() for r in range(fl.rowCount())
                  if fl.itemAt(r, QFormLayout.LabelRole) is not None]
        lab_w = max((lb.minimumWidth() or lb.sizeHint().width() for lb in labels if lb is not None), default=0)
        for r in range(fl.rowCount()):
            it = fl.itemAt(r, QFormLayout.SpanningRole)
            lay = it.layout() if it is not None else None
            if not isinstance(lay, QHBoxLayout) or not lab_w or lay.count() < 2:
                continue
            first, second = lay.itemAt(0).widget(), lay.itemAt(1).widget()
            if isinstance(first, QCheckBox) and isinstance(second, QAbstractSpinBox):
                lay.setSpacing(8)                             # -1 (Stil-Standard) verschob den Wert um 1 px
                first.setMinimumWidth(lab_w + fl.horizontalSpacing() - lay.spacing())
        # Beschriftung so hoch wie ihr Feld, Text darin mittig: Qt setzt Beschriftungen sonst mit einem festen Versatz,
        # der bei den höheren Feldern 2–3 px zu hoch liegt
        for r in range(fl.rowCount()):
            li, fi = fl.itemAt(r, QFormLayout.LabelRole), fl.itemAt(r, QFormLayout.FieldRole)
            if li is None or fi is None or not isinstance(li.widget(), QLabel):
                continue
            fw = fi.widget()
            parts = [fw] if fw is not None else [fi.layout().itemAt(i).widget() for i in range(fi.layout().count())]
            parts = [x for x in parts if x is not None]
            for x in parts:
                x.ensurePolished()
            h = max((x.sizeHint().height() for x in parts), default=0)
            if 0 < h <= 48:                                   # Tabellen/Textfelder: Beschriftung bleibt oben
                li.widget().setMinimumHeight(h)
                li.widget().setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # Häkchen-Zeilen in die Wertespalte einrücken: alle Bedienelemente beginnen an derselben Kante
        # (nur wenn die Zeile eingerückt in die vorhandene Breite passt – die Spalte darf nicht breiter werden, sonst
        # schrumpft die Abbildung; gemessen −7 % im X-Ray-Tab bei der langen Häkchen-Zeile)
        if lab_w and CHECKS_IN_FIELD_COLUMN:
            indent = lab_w + fl.horizontalSpacing()
            room = max(_fw(fl, r) for r in range(fl.rowCount())) if fl.rowCount() else 0   # nur die eigene Karte
            for r in range(fl.rowCount()):
                it = fl.itemAt(r, QFormLayout.SpanningRole)
                if it is None:
                    continue
                if isinstance(it.widget(), QCheckBox):
                    if it.widget().sizeHint().width() + indent <= room:
                        it.widget().setStyleSheet(f"QCheckBox {{ margin-left: {indent}px; }}")
                elif isinstance(it.layout(), QHBoxLayout) and it.layout().count() > 1:
                    lay = it.layout()
                    first, second = lay.itemAt(0).widget(), lay.itemAt(1).widget()
                    if (isinstance(first, QCheckBox) and not isinstance(second, QAbstractSpinBox)
                            and lay.sizeHint().width() + indent <= room):
                        lay.setContentsMargins(indent, 0, 0, 0)
    _field_edge(root)
    from PySide6.QtWidgets import QTableWidget
    for t in root.findChildren(QTableWidget):                # Kästchen ohne Text mittig (alle Listen)
        if not isinstance(t.itemDelegate(), _CheckDelegate):
            t.setItemDelegate(_CheckDelegate(t))
    for h in root.findChildren(HintLabel):                    # leere Hinweise ohne Zeile
        h.sync()
    for lay in root.findChildren(QHBoxLayout):
        items = [lay.itemAt(i) for i in range(lay.count())]
        if any(isinstance(it.widget(), (QLabel, QCheckBox)) for it in items[1:]):   # Beschriftung nicht ankleben
            lay.setSpacing(max(lay.spacing(), 8))
        ws = [it.widget() for it in items if it.widget() is not None]
        # nur feste Elemente: links zusammenhalten statt über die Breite verteilen
        if (ws and any(isinstance(x, QAbstractSpinBox) for x in ws) and not any(it.spacerItem() for it in items)
                and all(isinstance(x, (QAbstractSpinBox, QLabel, QCheckBox))
                        or (isinstance(x, QComboBox) and x.maximumWidth() == FIELD_W) for x in ws)):
            lay.addStretch(1)


class _WheelGuard(QObject):
    """Mausrad über Zahlenfeldern und Auswahllisten in einer scrollbaren Spalte: ohne Fokus scrollt die Spalte weiter,
    statt beim Darüberfahren den Wert zu verstellen. Erst nach Anklicken (Fokus) ändert das Mausrad den Wert.
    Dazu einheitliche Dialogränder (16 px wie die Karten). Einmal für die ganze Anwendung (apply)."""

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.Polish and isinstance(obj, (QAbstractSpinBox, QComboBox)):
            obj.setFocusPolicy(Qt.StrongFocus)                  # Mausrad gibt keinen Fokus (Qt-Standard: doch)
            if isinstance(obj, QAbstractSpinBox):               # linksbündig wie Text- und Auswahlfelder (Nutzerwunsch)
                obj.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                obj.lineEdit().setTextMargins(11, 0, 0, 0)      # Stylesheet-Padding gilt nicht für das innere Feld
            if obj.property("fieldw"):                          # Rasterbreite nach dem Stylesheet erneut festsetzen
                obj.setFixedWidth(FIELD_W)
        elif (t == QEvent.Polish and isinstance(obj, QDialog) and not isinstance(obj, (QMessageBox, QFileDialog))
              and obj.layout() is not None):
            obj.layout().setContentsMargins(16, 16, 16, 16)
        elif t == QEvent.Wheel and isinstance(obj, (QAbstractSpinBox, QComboBox)) and not obj.hasFocus():
            p = obj.parentWidget()
            while p is not None and not isinstance(p, QScrollArea):
                p = p.parentWidget()
            if p is not None:
                QApplication.sendEvent(p.verticalScrollBar(), ev)
                return True
        return False


class _DisabledHint(QObject):
    """Karte, die ohne Auswahl ausgegraut wäre: stattdessen ausblenden und einen Satz zeigen, was zu tun ist."""

    def __init__(self, group, text):
        super().__init__(group)
        self.group = group
        self.label = QLabel(text, objectName="cardHint", wordWrap=True)
        lay = group.parentWidget().layout()
        lay.insertWidget(lay.indexOf(group), self.label)
        group.installEventFilter(self)
        self.update()

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.EnabledChange:
            self.update()
        return False

    def update(self):
        off = self.group.testAttribute(Qt.WA_ForceDisabled)          # selbst abgeschaltet, nicht über den Tab
        self.group.setVisible(not off)
        self.label.setVisible(off)


def hint_when_disabled(group, text):
    return _DisabledHint(group, text)


class ColumnFit(QObject):
    """Linke Spalte fest COLUMN_W breit (alle Tabs gleich, Trennlinie nicht verschiebbar, Nutzerwunsch); breiter nur,
    wenn der Inhalt sonst abgeschnitten würde – nie waagerecht scrollen, der Rest geht an die Abbildung. Beobachtet den
    Inhalt (Stylesheet, aufgeklappte Karten, eingeblendete Zeilen, Sprache)."""

    def __init__(self, content, scroll, bar, column, splitter):
        super().__init__(column)
        self.content, self.scroll, self.bar, self.column, self.split = content, scroll, bar, column, splitter
        self.floor, self._pending = COLUMN_W, False
        content.installEventFilter(self)
        column.installEventFilter(self)
        splitter.handle(1).setEnabled(False)
        splitter.handle(1).setCursor(Qt.ArrowCursor)
        self.fit()

    def needed(self):
        w = max(self.floor, self.content.minimumSizeHint().width(),
                self.bar.minimumSizeHint().width() if self.bar is not None else 0)
        return w + self.scroll.verticalScrollBar().sizeHint().width() + 4

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.LayoutRequest, QEvent.Show, QEvent.FontChange, QEvent.StyleChange) and not self._pending:
            self._pending = True
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self, self.fit)                # Kontext: verfällt mit der Spalte
        return False

    def alive(self):
        """Nach einem Neuaufbau der Tabs (Projekt öffnen, Sprache) können Spalte/Inhalt schon gelöscht sein."""
        return all(shiboken6.isValid(o) for o in (self, self.content, self.scroll, self.column, self.split)
                   if o is not None) and (self.bar is None or shiboken6.isValid(self.bar))

    def fit(self):
        self._pending = False
        if not self.alive():
            return
        self.column.setFixedWidth(self.needed())


def fit_column(content, scroll, bar, column, splitter):
    return ColumnFit(content, scroll, bar, column, splitter)


# ---------------------------------------------------------------------------- Karten einklappen / Zeilen verschieben
def _row_of(form, w):
    """Zeile eines QFormLayout, deren Feld das Widget w ist oder enthält (Feld als Layout) -> Index oder -1."""
    for r in range(form.rowCount()):
        for role in (QFormLayout.FieldRole, QFormLayout.SpanningRole):
            it = form.itemAt(r, role)
            if it is None:
                continue
            if it.widget() is w:
                return r
            lay = it.layout()
            if lay is not None and any(lay.itemAt(i).widget() is w for i in range(lay.count())):
                return r
    return -1


def _move_row(src, r, dst):
    """Zeile r aus dem QFormLayout src ans Ende von dst (Beschriftung und Feld bleiben dieselben Objekte)."""
    res = src.takeRow(r)
    lw = res.labelItem.widget() if res.labelItem is not None else None
    fi = res.fieldItem
    fw = (fi.widget() or fi.layout()) if fi is not None else None
    if lw is not None and fw is not None:
        dst.addRow(lw, fw)
    elif fw is not None:
        dst.addRow(fw)
    elif lw is not None:
        dst.addRow(lw)


def split_group(group, first, last, title, n=None):
    """Zeilen von `first` bis `last` (Feld-Widgets; oder `n` Zeilen ab `first`) aus der Karte `group` in eine neue
    Karte direkt darunter verschieben (z. B. „Referenzierung“ aus „Auswertung“). -> neue QGroupBox."""
    from PySide6.QtWidgets import QGroupBox
    src = group.layout()
    r0 = _row_of(src, first)
    r1 = r0 + n - 1 if n else _row_of(src, last)
    assert 0 <= r0 <= r1, (title, r0, r1)
    new = QGroupBox(title)
    dst = make_form(new)
    for _ in range(r1 - r0 + 1):
        _move_row(src, r0, dst)
    lay = group.parentWidget().layout()
    lay.insertWidget(lay.indexOf(group) + 1, new)
    return new


class Fold(QObject):
    """Karte (QGroupBox) zum Einklappen: Klick auf den Titel klappt auf/zu, „▸/▾“ davor, „(geändert)“ dahinter,
    wenn `changed()` meldet, dass darin etwas vom Standard abweicht. Zustand je Karte in QSettings gemerkt.
    Der Inhalt wandert in ein eigenes Widget (dieselben Objekte, nur umgehängt)."""

    def __init__(self, group, name, settings=None, changed=None, opened=False):
        super().__init__(group)
        self.group, self.name, self.settings, self.changed = group, name, settings, changed
        self.base = group.title()
        lay = group.layout()
        self.body = QWidget()
        if isinstance(lay, QFormLayout):
            nf = make_form(self.body)
            nf.setContentsMargins(0, 0, 0, 0)
            while lay.rowCount():
                _move_row(lay, 0, nf)
            lay.addRow(self.body)
        else:
            nl = QVBoxLayout(self.body)
            nl.setContentsMargins(0, 0, 0, 0)
            nl.setSpacing(lay.spacing())
            while lay.count():
                it = lay.takeAt(0)
                if it.widget() is not None:
                    nl.addWidget(it.widget())
                elif it.layout() is not None:
                    nl.addLayout(it.layout())
                else:
                    nl.addItem(it)
            lay.addWidget(self.body)
        group.installEventFilter(self)
        if settings is not None:
            opened = str(settings.value(f"fold/{name}", opened)).lower() in ("true", "1")
        self.set_open(opened, remember=False)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonRelease and ev.position().y() < 36:
            self.set_open(not self.opened)
            return True
        return False

    def set_open(self, on, remember=True):
        self.opened = bool(on)
        self.body.setVisible(self.opened)
        lay = self.group.layout()                             # zugeklappt: nur die Titelzeile, kein leerer Innenrand
        lay.setContentsMargins(16, 8 if self.opened else 0, 16, 16 if self.opened else 0)
        if self.opened:
            self.group.setMinimumHeight(0)
            self.group.setMaximumHeight(16777215)
        else:
            self.group.setFixedHeight(self.group.fontMetrics().height() + 26)
        self.group.setCursor(Qt.ArrowCursor if self.opened else Qt.PointingHandCursor)
        if remember and self.settings is not None:
            self.settings.setValue(f"fold/{self.name}", self.opened)
        self.refresh()

    def refresh(self):
        from elucida.app.i18n import T
        mark = f"   ({T('adv_changed')})" if self.changed is not None and self.changed() else ""
        self.group.setTitle(("▼  " if self.opened else "▶  ") + self.base + mark)


def resolve(mode):
    """'system' | 'light' | 'dark' -> 'light' | 'dark'."""
    if mode in ("light", "dark"):
        return mode
    hints = QGuiApplication.styleHints()
    return "dark" if hints.colorScheme() == Qt.ColorScheme.Dark else "light"


def apply(mode, cache_dir: Path):
    """Fusion, Palette und Stylesheet für die ganze Anwendung setzen."""
    global _mode, base_style
    app = QApplication.instance()
    if getattr(app, "_wheel_guard", None) is None:
        app._wheel_guard = _WheelGuard(app)
        app.installEventFilter(app._wheel_guard)
    hints = QGuiApplication.styleHints()
    # Fensterrahmen/Titelleiste passend; "system" folgt wieder dem Betriebssystem
    hints.setColorScheme({"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(
        mode, Qt.ColorScheme.Unknown))
    _mode = resolve(mode)
    c = colors()
    style = QStyleFactory.create("Fusion")
    base_style = style.name().lower()
    app.setStyle(style)
    pal = QPalette()
    for role, key in ((QPalette.Window, "window"), (QPalette.WindowText, "text"), (QPalette.Base, "field"),
                      (QPalette.AlternateBase, "alt"), (QPalette.Text, "text"), (QPalette.Button, "button"),
                      (QPalette.ButtonText, "text"), (QPalette.Highlight, "accent"),
                      (QPalette.HighlightedText, "on_accent"), (QPalette.PlaceholderText, "disabled"),
                      (QPalette.ToolTipBase, "card"), (QPalette.ToolTipText, "text"), (QPalette.Link, "accent"),
                      (QPalette.Mid, "border_strong"), (QPalette.Midlight, "border"), (QPalette.Dark, "border_strong"),
                      (QPalette.Light, "card"), (QPalette.Shadow, "border_strong"), (QPalette.BrightText, "on_accent")):
        pal.setColor(role, QColor(c[key]))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor(c["disabled"]))
    app.setPalette(pal)
    cache_dir.mkdir(parents=True, exist_ok=True)
    arrows = {}
    for name in ("up", "down"):
        for state, col in (("", c["text2"]), ("_dis", c["disabled"])):
            p = cache_dir / f"{name}{state}_{_mode}.png"
            _render(name, col, 48, stroke=2.6).save(str(p))   # kräftiger, weil klein
            arrows[name + state] = p.as_posix()
    for state, col in (("", c["on_accent"]), ("_dis", c["card"])):      # Haken auf Akzent- bzw. Grau-Fläche
        p = cache_dir / f"check{state}_{_mode}.png"
        _render("check", col, 48, stroke=3.2).save(str(p))
        arrows["check" + state] = p.as_posix()
        p = cache_dir / f"dash{state}_{_mode}.png"                          # teilweise (Gruppe in Bäumen)
        _render("dash", col, 48, stroke=3.2).save(str(p))
        arrows["dash" + state] = p.as_posix()
    app.setStyleSheet(stylesheet(c, arrows))
    return _mode


def stylesheet(c, a):
    return f"""
QFrame#card {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QLabel#cardTitle {{ font-weight: bold; }}
QLabel[formlabel="true"] {{ color: {c['text2']}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {c['field']}; border: 1px solid {c['border']}; border-radius: 5px;
    padding: 3px 10px; min-height: 18px; selection-background-color: {c['accent']}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {c['accent']}; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {c['disabled']}; background: {c['alt']}; }}
QSpinBox, QDoubleSpinBox {{ padding-top: 2px; padding-bottom: 1px; padding-right: 20px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right;
    width: 18px; border: none; background: transparent; }}
QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right;
    width: 18px; border: none; background: transparent; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{a['up']}"); width: 11px; height: 11px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{a['down']}"); width: 11px; height: 11px; }}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{ image: url("{a['up_dis']}"); }}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{ image: url("{a['down_dis']}"); }}
QComboBox {{ padding-left: 12px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 20px; border: none; }}
QComboBox::down-arrow {{ image: url("{a['down']}"); width: 12px; height: 12px; }}
QComboBox::down-arrow:disabled {{ image: url("{a['down_dis']}"); }}
QComboBox QAbstractItemView {{ background: {c['card']}; border: 1px solid {c['border']};
    selection-background-color: {c['accent']}; selection-color: {c['on_accent']}; }}
QPushButton {{ background: {c['button']}; border: 1px solid {c['border']}; border-radius: 5px;
    padding: 4px 12px; min-height: 18px; }}
QPushButton:hover {{ background: {c['hover']}; border-color: {c['border_strong']}; }}
QPushButton:pressed {{ background: {c['border']}; }}
QPushButton:disabled {{ color: {c['disabled']}; background: {c['alt']}; }}
QPushButton[accent="true"] {{ background: {c['accent']}; color: {c['on_accent']}; border-color: {c['accent']};
    font-weight: bold; }}
QPushButton[accent="true"]:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QDialog QPushButton:default:enabled {{ background: {c['accent']}; color: {c['on_accent']}; border-color: {c['accent']};
    font-weight: bold; }}
QDialog QPushButton:default:enabled:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 8px; background: {c['window']}; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {c['text2']}; border: 1px solid transparent; border-radius: 6px;
    padding: 4px 12px; margin: 3px 2px; }}
QTabBar::tab:selected {{ background: {c['card']}; color: {c['text']}; border-color: {c['border']}; }}
QTabBar::tab:hover:!selected {{ background: {c['hover']}; color: {c['text']}; }}
QTableWidget, QTableView, QListWidget, QTreeWidget, QPlainTextEdit, QTextEdit {{
    background: {c['field']}; border: 1px solid {c['border']}; border-radius: 6px; gridline-color: {c['border']};
    selection-background-color: {c['accent']}; selection-color: {c['on_accent']}; }}
QHeaderView::section {{ background: {c['card']}; color: {c['text2']}; border: none;
    border-bottom: 1px solid {c['border']}; border-right: 1px solid {c['border']}; padding: 4px 6px; }}
QGroupBox {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 8px;
    margin-top: 0; padding: 2.1em 4px 4px 4px; }}
QGroupBox::title {{ subcontrol-origin: padding; subcontrol-position: top left; left: 12px; top: 9px;
    font-weight: bold; }}
QGroupBox::title:disabled {{ color: {c['disabled']}; }}
QCheckBox::indicator, QAbstractItemView::indicator, QGroupBox::indicator {{ width: 14px; height: 14px;
    border: 1px solid {c['check_border']}; border-radius: 3px; background: {c['field']}; }}
QCheckBox::indicator:hover, QAbstractItemView::indicator:hover {{ border-color: {c['accent']}; }}
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked, QGroupBox::indicator:checked {{
    background: {c['accent']}; border-color: {c['accent']}; image: url("{a['check']}"); }}
QCheckBox::indicator:indeterminate, QAbstractItemView::indicator:indeterminate {{
    background: {c['accent']}; border-color: {c['accent']}; image: url("{a['dash']}"); }}
QCheckBox::indicator:disabled, QAbstractItemView::indicator:disabled {{ background: {c['alt']};
    border-color: {c['border_strong']}; }}
QCheckBox::indicator:checked:disabled, QAbstractItemView::indicator:checked:disabled {{
    background: {c['disabled']}; border-color: {c['disabled']}; image: url("{a['check_dis']}"); }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background: transparent; }}
QToolTip {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 4px; }}
QToolBar {{ background: {c['window']}; border: none; border-bottom: 1px solid {c['border']};
    padding: 3px 6px; spacing: 2px; }}
QToolBar QToolButton {{ border: 1px solid transparent; border-radius: 5px; padding: 4px 6px; }}
QToolBar QToolButton:hover {{ background: {c['hover']}; border-color: {c['border']}; }}
QToolBar QToolButton:pressed {{ background: {c['border']}; }}
QToolBar::separator {{ background: {c['border']}; width: 1px; margin: 5px 6px; }}
QLabel#toast {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QWidget#recentRow {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 10px; }}
QWidget#recentRow:hover {{ border-color: {c['accent']}; background: {c['hover']}; }}
QLabel#recentMono {{ background: {c['accent']}; color: {c['on_accent']}; border-radius: 8px; font-weight: bold;
    font-size: 18px; }}
QLabel#recentThumb, QFrame#recentThumb {{ background: #ffffff; border: 1px solid {c['border']}; border-radius: 8px; }}
QLabel#recentTitle {{ font-size: 15px; font-weight: bold; background: transparent; }}
QLabel#recentNote {{ color: {c['text2']}; font-size: 14px; font-style: italic; background: transparent; }}
QLabel#recentSub, QLabel#recentWhen {{ color: {c['text2']}; background: transparent; }}
QLabel#recentBadge {{ color: {c['text2']}; background: {c['alt']}; border: 1px solid {c['border']}; border-radius: 8px;
    padding: 0px 7px; font-size: 11px; }}
QLabel#recentHead {{ font-size: 14px; }}
QFrame#bottomBar {{ background: {c['window']}; border-top: 1px solid {c['border']}; }}
QGroupBox {{ font-weight: bold; padding-top: 2.5em; }}
QGroupBox::title {{ left: 18px; top: 12px; }}                 /* bündig mit dem Karteninhalt */
QGroupBox#resultCard {{ padding-top: 8px; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton {{ min-height: 20px; }}
QGroupBox QWidget {{ font-weight: normal; }}
QGroupBox QGroupBox {{ font-weight: bold; }}
QLabel#cardHint {{ color: {c['text2']}; background: {c['card']}; border: 1px dashed {c['border_strong']};
    border-radius: 8px; padding: 10px 14px; }}
QToolButton[accent="true"] {{ background: {c['accent']}; color: {c['on_accent']}; border-color: {c['accent']};
    font-weight: bold; padding: 4px 10px; }}
QToolButton[accent="true"]:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QFrame#navBar {{ background: {c['window']}; border-bottom: 1px solid {c['border']}; }}
QLabel#navGroup {{ color: {c['text2']}; font-size: 10px; font-weight: bold; padding: 0 3px; }}
QPushButton#navTab {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 4px 8px;
    color: {c['text2']}; min-height: 16px; }}
QPushButton#navTab:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#navTab:checked {{ background: {c['card']}; color: {c['accent']}; border-color: {c['border']};
    border-bottom: 2px solid {c['accent']}; }}
QFrame#navSep {{ background: {c['border']}; }}
"""
