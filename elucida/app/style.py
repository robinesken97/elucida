"""Erscheinungsbild: Qt-Stil Fusion mit eigener Palette (hell/dunkel), zentralem Stylesheet und Symbolen.

Fusion sieht auf Windows, macOS und Linux gleich aus. Die Abbildungen (matplotlib) sind davon nicht betroffen.
Symbole sind kleine SVGs (Strichzeichnungen), werden in der Textfarbe gerendert und als PNG für das Stylesheet
abgelegt (PNG braucht kein Qt-Bildformat-Plugin)."""
from __future__ import annotations
import elucida

from pathlib import Path
import os

import shiboken6
from PySide6.QtCore import QByteArray, QEvent, QObject, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
                               QHeaderView,
                               QHBoxLayout, QLabel, QLineEdit, QMessageBox, QScrollArea, QSizePolicy, QPushButton, QStyle,
                               QStyledItemDelegate, QStyleFactory, QStyleOptionViewItem, QVBoxLayout, QWidget)

def _number_locale():
    """Dezimalpunkt in allen Zahlenfeldern (wissenschaftliche Konvention, Nutzerwunsch), ohne Tausendertrennzeichen –
    unabhängig von der Systemsprache; beim Import, also vor dem ersten Zahlenfeld."""
    from PySide6.QtCore import QLocale
    loc = QLocale(QLocale.C)
    loc.setNumberOptions(QLocale.OmitGroupSeparator | QLocale.RejectGroupSeparator)
    QLocale.setDefault(loc)


_number_locale()

COLORS = {
    # Abstufung wie im Entwurf: Seite < Karte, Felder etwas abgesetzt, warme Grautöne, dezente Ränder
    "light": dict(window="#F4F3EF", card="#FFFFFF", field="#FAF9F6", button="#FFFFFF", hover="#EFEEE9",
                  border="#E2E0DA", border_strong="#C8C6BE", text="#1F1E1C", text2="#62615B",
                  disabled="#ABA9A2", accent="#2E6BD6", accent_hover="#255BBB", on_accent="#FFFFFF",
                  alt="#F7F6F3", check_border="#9A988F", side="#ECEBE5", sel="#DDDBD3", ok="#1A7F52", on_ok="#FFFFFF"),
    "dark": dict(window="#141413", card="#1C1C1B", field="#111110", button="#232322", hover="#2B2B29",
                 border="#2D2D2B", border_strong="#42423F", text="#EDECE8", text2="#9D9B94",
                 disabled="#5E5D58", accent="#3D7CE0", accent_hover="#5089E6", on_accent="#FFFFFF",
                 alt="#181817", check_border="#7A7872", side="#181817", sel="#2F2F2C", ok="#55C795", on_ok="#101010"),
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
    "grid": '<path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "open_check": '<path d="M21 12a9 9 0 1 1-9-9M8 12l3 3 8-9"/>',
    "flask": '<path d="M9 3h6M10 3v6L4.5 18.5A1.5 1.5 0 0 0 5.8 21h12.4a1.5 1.5 0 0 0 1.3-2.5L14 9V3M7.5 15h9"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.1 1-1.1 1.8M12 17h.01"/>',
    "theme": '<circle cx="12" cy="12" r="9"/><path d="M12 3v18" /><path d="M12 7h6M12 12h9M12 17h6"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8'
           'M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/>',
    "moon": '<path d="M20.5 13.2A8.6 8.6 0 1 1 10.8 3.5a6.8 6.8 0 0 0 9.7 9.7z"/>',
    "chevron": '<path d="m7 9.5 5 5 5-5"/>',
    "home": '<path d="M3.5 11.5 12 4l8.5 7.5M6 9.5V20h12V9.5"/>',
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
    labels = [item_at(f, i, QFormLayout.LabelRole).widget() for f in forms for i in range(f.rowCount())
              if item_at(f, i, QFormLayout.LabelRole) and item_at(f, i, QFormLayout.LabelRole).widget()]
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


def set_accent(button, on, icon_name=None):
    """Hauptknopf (blau) an/aus: je Ansicht genau einer. icon_name: Symbol passend zur Fläche neu setzen."""
    button.setProperty("accent", bool(on))
    if icon_name:
        button.setIcon(icon(icon_name, "#FFFFFF" if on else None))
    button.style().unpolish(button)
    button.style().polish(button)


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


class _EmptyNote(QObject):
    """Grauer Platzhalter mitten in einer leeren Tabelle, Liste oder einem leeren Textfeld; verschwindet mit dem ersten
    Inhalt (grafische Sichtung 2026-11-11: leere Tabellen zeigten nur ihren Kopf)."""

    def __init__(self, view, text):
        super().__init__(view)
        from PySide6.QtWidgets import QAbstractItemView
        self.view = view
        self.label = QLabel(text, view.viewport())
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: gray; font-size: 14px; background: transparent;")
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        view.viewport().installEventFilter(self)
        if isinstance(view, QAbstractItemView):
            m = view.model()
            self.empty = lambda: m.rowCount() == 0
            for sig in (m.rowsInserted, m.rowsRemoved, m.modelReset):
                sig.connect(self.sync)
        else:                                                # QTextEdit/QTextBrowser
            self.empty = lambda: view.document().isEmpty()
            view.textChanged.connect(self.sync)
        self.sync()

    def sync(self, *_):
        if not shiboken6.isValid(self.view):                 # Neuaufbau: gelöscht
            return
        self.label.setVisible(self.empty())
        self.label.setGeometry(self.view.viewport().rect().adjusted(12, 0, -12, 0))

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Resize:
            self.sync()
        return False


def empty_note(view, text):
    """Platzhalter für eine leere Tabelle/Liste/ein leeres Textfeld setzen (siehe _EmptyNote)."""
    view._empty_note = _EmptyNote(view, text)
    return view


def hide_when_empty(table):
    """Dateiliste ohne Einträge ausblenden (Leer-Zustand: die Anleitung rechts nennt Dateien und ersten Schritt)."""
    upd = lambda *_: shiboken6.isValid(table) and table.setVisible(table.model().rowCount() > 0)   # Neuaufbau: gelöscht
    m = table.model()
    for sig in (m.rowsInserted, m.rowsRemoved, m.modelReset):
        sig.connect(upd)
    upd()


class _CellDelegate(QStyledItemDelegate):
    """Tabellenzellen mittig wie die Spaltenüberschriften (Nutzerwunsch); Kästchen ohne Text mittig in der Zelle (Qt
    setzt es sonst an den linken Rand) – Zeichnen und Klicken über dasselbe Rechteck."""

    PAD = 12        # Luft links und rechts in jeder Zelle: Spalten nach Inhalt standen sonst Zahl an Zahl

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        return QSize(s.width() + 2 * self.PAD, s.height())

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
        self._paint(painter, option, index)
        painter.save()                                       # feine Linie unter jeder Zeile statt eines Gitters:
        painter.setPen(QColor(colors()["border"]))           # alle Tabellen sehen gleich aus (Nutzerwunsch)
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        painter.restore()

    def _paint(self, painter, option, index):
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


CHECK_ROW_H = 30
CHECK_COL_W = 44          # Spalte nur für das Kästchen: genug Fläche zum Treffen, überall gleich


def check_columns(table):
    """Kästchen stehen in einer eigenen schmalen Spalte ohne Kopftext, nie mit Text in einer Zelle (Nutzerwunsch
    2026-11-11): jede Spalte ohne Kopftext bekommt die feste Breite CHECK_COL_W."""
    from PySide6.QtWidgets import QHeaderView
    hh = table.horizontalHeader()
    for i in range(table.columnCount()):
        it = table.horizontalHeaderItem(i)
        if it is not None and not it.text():
            hh.setSectionResizeMode(i, QHeaderView.Fixed)
            hh.resizeSection(i, CHECK_COL_W)


def center_corner(tabs):
    """Knöpfe neben den Reitern auf derselben Mittellinie wie die Reiter."""
    corner = tabs.cornerWidget(Qt.TopRightCorner)
    if corner is None:
        return
    corner.layout().setContentsMargins(0, 0, 0, 0)
    corner.layout().setAlignment(Qt.AlignVCenter)
    tabs.tabBar().ensurePolished()
    corner.setFixedHeight(tabs.tabBar().sizeHint().height())


class RichDelegate(_CellDelegate):
    """Zelle als Rich-Text gezeichnet (`fmt`: Text -> HTML, z. B. Formeln mit tiefgestellten Zahlen, kursive
    Lokanten); bearbeitet wird weiter der reine Text. Kein Umbruch: was nicht passt, wird am Rand abgeschnitten
    (ganzer Text im Tooltip der Zelle)."""

    def __init__(self, parent, fmt):
        super().__init__(parent)
        self.fmt = fmt

    def _doc(self, option, index, color=None):
        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setDocumentMargin(0)
        h = self.fmt(str(index.data(Qt.DisplayRole) or ""))
        doc.setHtml(f"<span style='color:{color}'>{h}</span>" if color else h)
        return doc

    def sizeHint(self, option, index):
        o = QStyleOptionViewItem(option)
        self.initStyleOption(o, index)
        s = super().sizeHint(option, index)
        return QSize(int(self._doc(o, index).idealWidth()) + 2 * self.PAD, s.height())

    def _paint(self, painter, option, index):
        o = QStyleOptionViewItem(option)
        self.initStyleOption(o, index)
        o.text = ""
        st = option.widget.style() if option.widget is not None else QApplication.style()
        st.drawControl(QStyle.CE_ItemViewItem, o, painter, option.widget)     # Hintergrund, Auswahl
        fg = index.data(Qt.ForegroundRole)
        col = (o.palette.highlightedText().color() if o.state & QStyle.State_Selected
               else fg.color() if fg is not None else o.palette.text().color())
        doc = self._doc(o, index, col.name())
        w, h = doc.idealWidth(), doc.size().height()
        r = option.rect
        painter.save()
        painter.setClipRect(r.adjusted(self.PAD // 2, 0, -self.PAD // 2, 0))
        painter.translate(r.x() + max(self.PAD // 2, (r.width() - w) / 2), r.y() + (r.height() - h) / 2)
        doc.drawContents(painter)
        painter.restore()


def check_table(headers):
    """Auswahl mit Häkchen, überall gleich: Häkchen vorn, Zellen mittig, Datenspalten gleich breit, nichts markierbar."""
    from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget
    t = QTableWidget(0, len(headers) + 1)
    t.setHorizontalHeaderLabels([""] + list(headers))
    t.verticalHeader().hide()
    t.verticalHeader().setDefaultSectionSize(CHECK_ROW_H)
    t.setShowGrid(False)
    t.setSelectionMode(QAbstractItemView.NoSelection)
    t.setFocusPolicy(Qt.NoFocus)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
    t.setColumnWidth(0, CHECK_COL_W)
    t.setItemDelegate(_CellDelegate(t))
    return t


def check_row(table, data, texts, checked=True):
    """Zeile anhängen: Häkchen (Qt.UserRole = data) in Spalte 0, danach die Texte."""
    from PySide6.QtWidgets import QTableWidgetItem
    r = table.rowCount()
    table.insertRow(r)
    it = QTableWidgetItem()
    it.setData(Qt.UserRole, data)
    it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
    it.setCheckState(Qt.Checked if checked else Qt.Unchecked)
    table.setItem(r, 0, it)
    for c, text in enumerate(texts, 1):
        x = QTableWidgetItem(text)
        x.setFlags(Qt.ItemIsEnabled)
        table.setItem(r, c, x)
    return it


def fit_check_table(table, rows=6):
    """Höhe passend zum Inhalt, ab `rows` Zeilen scrollen."""
    table.setFixedHeight(table.horizontalHeader().sizeHint().height() + min(table.rowCount(), rows) * CHECK_ROW_H + 2)


class HintLabel(QLabel):
    """Hinweiszeile, die ohne Text samt Zeilenabstand verschwindet (keine Leerzeile im Formular)."""

    def setText(self, text):
        _set_sci(self, text)                                 # Formelzeichen wie im Satz (λ, ε, R², E₁/₂ …)
        self.sync()

    def text(self):                                          # wer den Text liest (Kacheln, Tests), bekommt ihn ohne HTML
        return getattr(self, "_plain", QLabel.text(self))

    def sync_align(self):
        """Hinweise mittig, auch mehrzeilige (Nutzerwunsch)."""
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

    def _has_text(self):
        return bool(self.text())

    def sync(self):
        p = self.parentWidget()
        if p is None:
            return
        vis = self._has_text()
        if self.property("centered"):
            self.sync_align()
        form = next((fl for fl in p.findChildren(QFormLayout) if fl.indexOf(self) >= 0), None)
        if form is not None:
            form.setRowVisible(self, vis)
        else:
            self.setVisible(vis)


def sci_html(h):
    """Wie sci(), aber für HTML: Formelzeichen nur in den Textstücken zwischen den Tags setzen."""
    import re as _re
    return "".join(p if p.startswith("<") else sci(p, escape=False) for p in _re.split(r"(<[^>]+>)", str(h)))


def si_display(text):
    """SI-Text für die Anzeige (Nutzerwunsch 2026-11-11): Blocksatz, Formelzeichen wie im Satz (Größen kursiv, Exponenten
    hochgestellt). HTML bleibt HTML; kopiert und exportiert wird weiter der gesetzte Text."""
    import re as _re
    t = str(text or "")
    if not t:
        return ""
    if "<" in t or "&" in t:
        h = sci_html(t)
    else:
        h = sci(t).replace("\n", "<br>")
        h = _re.sub(r"\bE1/2", "<i>E</i><sub>1/2</sub>", h).replace("Fc0/+", "Fc<sup>0/+</sup>")   # Schreibweise der Methodentexte
    h = _re.sub(r"\b(cm|M|s|mL|L|mol|g|K|min|mm)-(\d)\b", r"\1<sup>−\2</sup>", h)
    # hoch-/tiefgestellte Stücke nie umbrechen („Fc⁰/⁺“ trennte Qt nach dem Schrägstrich): Wortverbinder dahinter
    h = _re.sub(r"<(su[bp])>([^<]*)</\1>", lambda m: f"<{m.group(1)}>" + m.group(2).replace("/", "/\u2060") + f"</{m.group(1)}>", h)
    return f"<div align='justify'>{h}</div>"


class SiText(HintLabel):
    """SI-Text zum Lesen und Kopieren (Bildunterschrift, Methodentext, SI-Zeile): in der Anzeige Blocksatz und
    Formelzeichen wie im Satz; text() gibt den gesetzten Text zurück."""

    def __init__(self, text="", empty=""):
        super().__init__()
        self.empty = empty                                   # grauer Platzhalter, solange es keinen Text gibt
        self.setWordWrap(True)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setProperty("plaintext", True)                  # tidy: nicht mittig setzen
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setText(text)                                   # auch ohne Text: der Platzhalter steht von Anfang an da

    def _has_text(self):
        return bool(getattr(self, "_plain", "") or self.empty)

    def setText(self, text):
        import html as _html
        self._plain = text or ""
        hold = bool(self.empty) and not self._plain             # Platzhalter: grau, etwas größer, mittig in der Karte
        QLabel.setText(self, f"<span style='color:gray; font-size:14px'>{_html.escape(self.empty)}</span>" if hold
                       else si_display(self._plain))
        if hold != getattr(self, "_hold", None):
            self._hold = hold
            self.setAlignment(Qt.AlignCenter if hold else Qt.AlignLeft | Qt.AlignTop)
        self.sync()


_SUB_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_PLAIN_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


class ChemEdit(QLineEdit):
    """Eingabefeld für Formeln, Lösungsmittel und Texte der Bildunterschrift: die Ziffern einer Formel stehen schon beim
    Tippen tiefgestellt (CH₂Cl₂, n-Bu₄NPF₆; Nutzerwunsch 2026-11-11). Nur Anzeige: text() gibt die Schreibweise mit
    normalen Ziffern zurück, gespeichert wird wie bisher."""

    def __init__(self, text=""):
        super().__init__()
        self.textEdited.connect(self._typed)
        if text:
            self.setText(text)

    @staticmethod
    def _shown(text):
        from elucida.si import lines as SI
        plain = str(text or "").translate(_PLAIN_DIGITS)
        shown = SI.chem_plain(plain)
        return shown if shown.translate(_PLAIN_DIGITS) == plain else plain       # nur Ziffern dürfen sich ändern

    def _typed(self, _text):
        t = QLineEdit.text(self)
        new = self._shown(t)
        if new != t:
            pos = self.cursorPosition()
            QLineEdit.setText(self, new)
            self.setCursorPosition(pos)
            self.setModified(True)                           # setText setzt „geändert“ zurück: es wurde aber getippt

    def setText(self, text):
        QLineEdit.setText(self, self._shown(text))

    def setPlaceholderText(self, text):
        import re as _re                                     # auch das Beispiel im leeren Feld: CH₂Cl₂, mg mL⁻¹
        QLineEdit.setPlaceholderText(self, _re.sub(r"(?<=[A-Za-z])-1\b", "⁻¹", self._shown(text)))

    def text(self):
        return QLineEdit.text(self).translate(_PLAIN_DIGITS)


class _CardActions(QObject):
    """Hält die Knöpfe einer Karte oben rechts auf der Titelzeile (siehe card_actions)."""

    def __init__(self, card, box):
        super().__init__(box)
        self.card, self.box, self.title = card, box, None
        self.title_text = card.title() if hasattr(card, "title") else ""       # Titel beim Anlegen (siehe place)
        card.installEventFilter(self)
        self.place()

    def place(self):
        from PySide6.QtWidgets import QGroupBox
        self.box.adjustSize()
        self.box.move(self.card.width() - CARD_PAD - self.box.width(), 6)      # Mitte der Titelzeile (12 + halbe Zeile)
        self.box.raise_()
        lay = self.card.layout()
        if isinstance(self.card, QGroupBox) and lay is not None:
            # Ergebnisseiten nehmen ihrer Karte den Titel (der Reiter nennt ihn schon). Mit Knöpfen bekommt sie die
            # Titelzeile zurück – sonst stünden die Knöpfe im Inhalt –, und der Inhalt beginnt wie in allen Karten darunter.
            bare = not self.card.title() and bool(self.title_text)
            if bare and self.title is None:
                self.title = QLabel(self.title_text, self.card, objectName="cardTitle")
                self.top0 = lay.contentsMargins().top()
            if self.title is not None:
                self.title.setVisible(bare)
                self.title.adjustSize()
                self.title.move(CARD_PAD, 12)
                m = lay.contentsMargins()
                want = self.top0 + (22 if bare else 0)           # Inhalt 39 unter der Kartenkante wie mit Titel
                if m.top() != want:
                    lay.setContentsMargins(m.left(), want, m.right(), m.bottom())

    def eventFilter(self, w, ev):
        if ev.type() in (QEvent.Resize, QEvent.Show, QEvent.LayoutRequest):
            try:
                self.place()
            except RuntimeError:                             # Karte wird gerade gelöscht
                pass
        return False


def card_actions(card, *buttons):
    """Aktionen einer Karte („Kopieren“) kompakt oben rechts auf der Titelzeile, in jeder Karte an derselben Stelle
    (Nutzerwunsch 2026-11-11: die Knöpfe standen je Tab woanders). Der Inhalt nutzt die ganze Kartenbreite; der Knopf
    für das Kopieren steht als letzter ganz rechts. Für QGroupBox und `card()`."""
    box = QWidget(card)
    h = QHBoxLayout(box)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    for b in buttons:
        _head_button(b)
        h.addWidget(b)
    box.show()
    card._actions = _CardActions(card, box)
    return box


HEAD_BTN_H = 28           # Knöpfe auf Titel- und Kopfzeilen: genug Höhe für Unterlängen („Kopieren“, „Word speichern …“)


def _head_button(b):
    b.setProperty("cellcss", "head")                         # tidy: nicht auf die Feldhöhe setzen
    # Höhe im Stylesheet selbst: dessen min-/max-height überstimmt setFixedHeight (die Knöpfe waren sonst nur 18 hoch)
    b.setStyleSheet(f"min-height: {HEAD_BTN_H - 2}px; max-height: {HEAD_BTN_H - 2}px; padding: 0px 12px; "
                    "border-radius: 8px;")
    b.setCursor(Qt.PointingHandCursor)


def text_head(label, *buttons):
    """Kopfzeile direkt über einem Textfeld: links, was darin steht („IR-Zeile“), rechts die Aktionen dazu („Kopieren“).
    Für Karten, in denen das Textfeld nur ein Teil ist (Nutzerwunsch 2026-11-11: „Kopieren“ auf der Titelzeile der ganzen
    Karte war dort irreführend)."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 4, 0, 0)
    h.setSpacing(6)
    lb = QLabel(label)
    lb.setProperty("formlabel", True)
    h.addWidget(lb)
    h.addStretch(1)
    for b in buttons:
        _head_button(b)
        h.addWidget(b)
    return w


def copy_button(tip=""):
    """Der eine Knopf „Kopieren“ für alle Karten: Symbol + kurzes Wort, Langform im Tooltip."""
    from elucida.app.i18n import T
    b = QPushButton(icon("copy"), T("si_copy"))
    b.setToolTip(tip)
    return b


def card(title):
    """Gruppe als Karte, Titel und Ränder wie QGroupBox in den übrigen Tabs. Gibt (Karte, Inhalts-Widget) zurück."""
    frame = QFrame(objectName="card")
    v = QVBoxLayout(frame)
    v.setContentsMargins(CARD_PAD - 1, 12, CARD_PAD - 1, 12)   # Inhalt bündig mit QGroupBox (Rahmen 1 + Innenrand 16)
    v.setSpacing(10)                                         # Titel – Inhalt wie in QGroupBox
    head = QHBoxLayout()
    t = QLabel(title, objectName="cardTitle")
    head.addWidget(t)
    head.addStretch(1)
    v.addLayout(head)
    body = QWidget()
    v.addWidget(body)
    return frame, body


FIELD_W = 120                     # einheitliche Breite der Zahlenfelder (Raster der linken Spalte)
CONTROL_H = 32                     # Höhe aller Felder und Knöpfe in den Spalten
TOOLBAR_H = 52                     # Werkzeugleiste (Entwurf: 9 + 34 + 9), unter macOS = Titelleiste
BAR_H = 34                         # Knöpfe in Leisten (Werkzeugleiste, Fußleiste, Seitenkopf), Maß des Entwurfs
LABEL_W = 128                      # Beschriftungsspalte in allen Tabs gleich: Texte und Felder stehen überall gleich
FORM_GAP = 8                       # Abstand Beschriftung – Feld
COL_PAD = 14                       # Rand der Spalte um die Karten (rechts liegt darin die Bildlaufleiste)
CARD_PAD = 17                      # Kartenrand bis zum Inhalt: Rahmen 1 + Innenrand 16
GAP_W = 24                         # Lücke zwischen Feld A und B (Platz für „–“/„×“)
WIDE_W = 2 * FIELD_W + GAP_W       # Wertespalte: Listen, Textfelder, „[a] – [b]“ enden an einer Kante (Nutzerwunsch)
COLUMN_W = 538                    # linke Spalte in allen Tabs gleich breit, samt Bildlaufleiste (breiter nur, wenn Inhalt sonst abgeschnitten)
CARD_MARGINS = (12, 8, 12, 12)     # Layout-Rand in der Karte (dazu Rahmen 1 + Padding 4 seitlich, oben CARD_TITLE_H aus dem Stylesheet)
CARD_TITLE_H = 30                  # Titelzone: 12 oben + Titelzeile; Inhalt beginnt 39 unter der Kartenkante wie im Entwurf
ROW_GAP = 6                        # senkrechter Abstand zwischen Zeilen einer Karte (Entwurf: Zeilenraster 38 bei 32 hohen Feldern)
INNER_W = COLUMN_W - 2 * COL_PAD - 2 * CARD_PAD     # Karteninhalt: Beschriftung + Abstand + Wertespalte
VALUE_W = INNER_W - LABEL_W - FORM_GAP              # Wertespalte bei fester Beschriftungsspalte
CHECKS_IN_FIELD_COLUMN = True     # Häkchen-Zeilen in der Wertespalte (eine Kante für alle Bedienelemente)


def _release_item(it):
    if it is not None and it.layout() is None:
        shiboken6.invalidate(it)


def drop_taken(it):
    """Ein mit takeAt/takeRow entnommenes Layout-Element löschen, **bevor** sein Widget wieder eingefügt wird; gibt das
    Widget (oder Unter-Layout, sonst None) zurück. PySide gibt entnommene Elemente nicht frei: das alte bleibt am Widget
    eingetragen, das neue erfährt Größenänderungen nicht mehr und meldet veraltete Höhen (heightForWidth-Cache) – Karten
    wurden zusammengedrückt, Hinweise lagen über Tabellen."""
    if it is None:
        return None
    w = it.widget()
    if w is None:
        return it.layout()
    shiboken6.delete(it)
    return w


def take_row(fl, r):
    """fl.takeRow(r) als (Beschriftung, Feld), beides Widget/Layout/None, alte Elemente gelöscht (siehe drop_taken)."""
    res = fl.takeRow(r)
    return drop_taken(res.labelItem), drop_taken(res.fieldItem)


class _Item:
    """What callers read from a layout item (widget, sub-layout, spacer or not), without holding the item."""

    def __init__(self, it):
        self._widget, self._layout, self._spacer = it.widget(), it.layout(), it.spacerItem() is not None
        _release_item(it)

    def widget(self):
        return self._widget

    def layout(self):
        return self._layout

    def spacerItem(self):
        return self if self._spacer else None


def item_at(layout, *pos):
    """layout.itemAt(...), always instead of it. The layout keeps PySide's wrapper of the item alive, and Qt deletes the
    item without telling PySide (e.g. when its widget goes). The dead entry stays in PySide's address table, and a Python
    Qt object created later at that address segfaults (SignalManager::retrieveMetaObject). Selftest: 'layout items'."""
    it = layout.itemAt(*pos)
    return None if it is None else _Item(it)


def _fw(fl, r):
    """Breite einer Formularzeile aus Beschriftung + Feld (Hinweis für die Einrück-Regel)."""
    li, fi = fl.itemAt(r, QFormLayout.LabelRole), fl.itemAt(r, QFormLayout.FieldRole)
    w = 0 if li is None or fi is None else li.sizeHint().width() + fl.horizontalSpacing() + fi.sizeHint().width()
    _release_item(li)
    _release_item(fi)
    return w


def _cell(x, w):
    """Feld fest auf eine Rasterbreite setzen (Zahlenfelder setzt _WheelGuard nach dem Stylesheet erneut)."""
    x.setProperty("fieldw", w)
    x.setFixedWidth(w)


def _pairs(lay, ws, width, gap):
    """„C [■] H [■] …“ / „Absorption [■] Emission [■]“: Paare aus Beschriftung + Farbfeld gleichmäßig über width."""
    from PySide6.QtWidgets import QLineEdit
    swatch = lambda x: isinstance(x, QPushButton) and not x.text()
    val = lambda x: swatch(x) or isinstance(x, (QAbstractSpinBox, QComboBox, QLineEdit))
    if len(ws) < 4 or len(ws) % 2 or not all(isinstance(ws[i], QLabel) and val(ws[i + 1])
                                              for i in range(0, len(ws), 2)):
        return False
    n = len(ws) // 2
    cell = (width - gap * (n - 1)) // n
    lay.setSpacing(8)
    _strip_stretch(lay)
    for i in range(0, len(ws), 2):
        lb, x = ws[i], ws[i + 1]
        lb.setMinimumWidth(0)
        if swatch(x):                                     # „Absorption [■]“: Farbfeld rechts, Text füllt
            x.setFixedWidth(34)
            lb.setFixedWidth(max(16, cell - 34 - 8))
        else:                                             # „c [1 mM]“: kurze Beschriftung, Feld füllt
            lb.setFixedWidth(lb.sizeHint().width())
            _cell(x, max(40, cell - lb.sizeHint().width() - 8))
        if i:
            lay.insertSpacing(lay.indexOf(lb), gap - 8)
    return True


def _strip_stretch(lay):
    for i in reversed(range(lay.count())):
        if item_at(lay, i).spacerItem() is not None:
            lay.takeAt(i)


def _check_edge(root):
    """Kästchen in der Wertespalte minimal eingerückt: optisch bündig mit der Feldkante."""
    from PySide6.QtWidgets import QCheckBox
    for fl in root.findChildren(QFormLayout):
        for r in range(fl.rowCount()):
            for role in (QFormLayout.FieldRole, QFormLayout.SpanningRole):
                it = item_at(fl, r, role)
                if it is None:
                    continue
                lay = it.layout()
                ws = [it.widget()] if it.widget() is not None else \
                    [item_at(lay, i).widget() for i in range(lay.count())] if lay is not None else []
                inset = lay is not None and lay.contentsMargins().left() > 0
                for x in ws:
                    if isinstance(x, QCheckBox) and "indicator" not in x.styleSheet() and (
                            role == QFormLayout.FieldRole or inset or "margin-left" in x.styleSheet()):
                        x.setStyleSheet(x.styleSheet() + " QCheckBox::indicator { margin-left: 3px; }")


def _first_text(root):
    """Text am Kartenanfang (Hinweis, Erklärung): seine erste Zeile steht dort, wo der Text eines Felds stünde. Felder
    sind CONTROL_H hoch, eine Textzeile nur etwa halb so hoch – ohne Ausgleich klebte sie an der Überschrift und der
    Abstand zur nächsten Zeile war kleiner als zwischen Feldern (Nutzerwunsch 2026-11-11, senkrechtes Raster)."""
    from PySide6.QtWidgets import QGroupBox
    for g in root.findChildren(QGroupBox):
        w = g
        for _ in range(3):                                   # Karte -> ggf. Klappkörper/Halter -> erstes Widget
            lay = w.layout()
            if lay is None or not lay.count():
                w = None
                break
            it = item_at(lay, 0)
            w = it.widget() if it is not None else None
            if w is None or isinstance(w, QLabel) or type(w) is not QWidget:
                break
        if isinstance(w, QLabel) and w.wordWrap() and not w.property("formlabel") and not w.property("firsttext"):
            fl = w.parentWidget().layout()
            if isinstance(fl, QFormLayout) and fl.getWidgetPosition(w)[1] == QFormLayout.LabelRole:
                continue                                     # Beschriftung einer Feldzeile
            w.setProperty("firsttext", True)
            m = w.contentsMargins()
            w.setContentsMargins(m.left(), m.top() + 7, m.right(), m.bottom() + 3)


def _choose_rows(root):
    """Dateizeilen: „Wählen …“ in einer Spalte; ohne Papierkorb reicht der Knopf bis zu dessen rechter Kante."""
    from elucida.app.i18n import T
    rows = []
    for lay in root.findChildren(QHBoxLayout):
        ws = [item_at(lay, i).widget() for i in range(lay.count()) if item_at(lay, i).widget() is not None]
        for i, b in enumerate(ws):
            if isinstance(b, QPushButton) and (b.text() == T("choose") or b.property("chooselike")):
                t = ws[i + 1] if i + 1 < len(ws) and isinstance(ws[i + 1], QPushButton) and not ws[i + 1].text() else None
                rows.append((lay, b, t, ws[i - 1] if i and isinstance(ws[i - 1], QLabel) else None))
    if not rows:
        return
    bw = max(84, *(b.sizeHint().width() for _, b, _t, _l in rows))
    tw = max([t.width() if t.maximumWidth() < 10000 else t.sizeHint().width() for _, _b, t, _l in rows if t is not None], default=34)
    for lay, b, t, name in rows:
        lay.setSpacing(8)
        if t is not None:
            t.setFixedWidth(tw)
        b.setFixedWidth(bw if t is not None else bw + 8 + tw)
        if name is not None and isinstance(lay.parent(), QFormLayout):      # jede Zeile genau so breit wie die Wertespalte
            name.setFixedWidth(VALUE_W - 8 - bw - 8 - tw)


def _field_edge(root):
    """Zwei-Spalten-Raster der Wertespalte (Nutzerwunsch Symmetrie): Feld A = FIELD_W, Lücke GAP_W, Feld B = FIELD_W,
    zusammen WIDE_W. Einzelwert über die ganze Wertespalte; „[a] – [b]“, „[a] × [b]“, Auswahl + Wert und Wert + Häkchen in A und B; Listen,
    Textfelder und Dateizeilen genau bis zur Kante. Zwei Werte mit langer Zwischenbeschriftung („[a] Ränder [b]“)
    und „☑ gesamt [a] – [b]“ bekommen eine zweite Zeile. Feste Breiten statt Formularrand (der zöge die Spalte mit)."""
    from PySide6.QtWidgets import QAbstractItemView, QAbstractScrollArea, QCheckBox, QLineEdit
    from elucida.app.i18n import T, long_form
    G = GAP_W
    value = (QAbstractSpinBox, QComboBox, QLineEdit)
    for fl in [fl for fl in root.findChildren(QFormLayout) if fl.parentWidget() is not None]:
        fl.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        for r in range(1, fl.rowCount()):                     # Hinweis zu Feldern: mittig unter die Wertespalte, nicht
            it = item_at(fl, r, QFormLayout.SpanningRole)     # unter die ganze Karte (Nutzerwunsch)
            w = it.widget() if it is not None else None
            if (isinstance(w, QLabel) and (isinstance(w, HintLabel) or HINT_CSS in (w.styleSheet() or ""))
                    and item_at(fl, r - 1, QFormLayout.FieldRole) is not None
                    and item_at(fl, r - 1, QFormLayout.SpanningRole) is None):
                take_row(fl, r)
                fl.insertRow(r, "", w)
        # Wertespalte bis zum Kartenrand (Nutzerwunsch: Breite gleichmäßig nutzen): Spalte − Ränder − Beschriftungen
        labs = [item_at(fl, r, QFormLayout.LabelRole).widget() for r in range(fl.rowCount())
                if item_at(fl, r, QFormLayout.LabelRole) is not None and item_at(fl, r, QFormLayout.LabelRole).widget()]
        for x in labs:                                        # überall dieselbe Beschriftungsspalte (Nutzerwunsch Symmetrie)
            if isinstance(x, QLabel):
                x.ensurePolished()                            # Schrift des Stylesheets, sonst misst Qt zu schmal
                x.setWordWrap(x.fontMetrics().horizontalAdvance(x.text()) > LABEL_W)
                x.setFixedWidth(LABEL_W)
                if not x.toolTip() and long_form(x.text()):   # gekürzte Beschriftung: Langform im Tooltip
                    x.setToolTip(long_form(x.text()))
        lab = LABEL_W
        span_all = INNER_W                                    # ganze Kartenbreite innen
        W = max(WIDE_W, span_all - lab - fl.horizontalSpacing())
        U = (W - G) // 2
        W = 2 * U + G
        for sp in [item_at(fl, r, QFormLayout.FieldRole).widget() for r in range(fl.rowCount())
                   if item_at(fl, r, QFormLayout.FieldRole) is not None]:
            if isinstance(sp, QAbstractSpinBox):               # Einzelwert bis zur Kante wie die Auswahlfelder (Nutzerwunsch)
                _cell(sp, W)
        span = max(span_all, W)                               # ganze Breite (Beschriftung + Wertespalte)
        for r in reversed(range(fl.rowCount())):            # Häkchenreihen (≥ 3) zu zweit in Feld A und B
            it = item_at(fl, r, QFormLayout.SpanningRole)
            if it is not None and isinstance(it.widget(), QAbstractScrollArea):
                _cell(it.widget(), span)                      # Listen/Textfelder über die ganze Breite
                continue
            lay = it.layout() if it is not None else None
            if not isinstance(lay, QHBoxLayout):
                continue
            cbs = [item_at(lay, i).widget() for i in range(lay.count()) if item_at(lay, i).widget() is not None]
            if not lay.property("grid") and _pairs(lay, cbs, span, G):
                lay.setProperty("grid", True)
                continue
            if 2 <= len(cbs) <= 4 and all(isinstance(x, QPushButton) and x.text() for x in cbs) and \
                    not any(x.property("accent") for x in cbs):   # Knopfreihe: gleich breit über die ganze Breite
                _strip_stretch(lay)
                lay.setSpacing(8)
                lay.setContentsMargins(max(0, span - W), 0, 0, 0)   # in der Wertespalte wie die Häkchen darüber
                for x in cbs:
                    x.setFixedWidth((W - 8 * (len(cbs) - 1)) // len(cbs))
                    x.setStyleSheet("padding-left: 2px; padding-right: 2px;")   # langer Text wird nicht abgeschnitten
                continue
            if len(cbs) == 3 and isinstance(cbs[0], QCheckBox) and isinstance(cbs[1], QLabel) and \
                    isinstance(cbs[2], QAbstractSpinBox):             # „☐ Gestapelt  Abstand [1,20]“: Wert eigene Zeile
                lay.removeWidget(cbs[1])
                lay.removeWidget(cbs[2])
                cbs[1].setProperty("formlabel", True)
                cbs[1].setMinimumHeight(cbs[2].sizeHint().height())
                if labs and labs[0].maximumWidth() < 10000:
                    cbs[1].setFixedWidth(labs[0].maximumWidth())
                _cell(cbs[2], U)
                fl.insertRow(r + 1, cbs[1], cbs[2])
                continue
            if len(cbs) < 3 or not all(isinstance(x, QCheckBox) for x in cbs):
                continue
            for x in cbs:
                lay.removeWidget(x)
            fl.removeRow(r)                                   # leeres Layout weg (Widgets sind schon herausgenommen)
            for k in reversed(range(0, len(cbs), 2)):
                h = QHBoxLayout()
                h.setSpacing(0)
                h.setProperty("grid", True)
                cbs[k].setFixedWidth(U + G)
                h.addWidget(cbs[k])
                if k + 1 < len(cbs):
                    h.addWidget(cbs[k + 1])
                h.addStretch(1)
                fl.insertRow(r, "", h)
        for r in range(fl.rowCount()):                        # feste Werte fluchten mit dem Text in den Feldern, gleiche Zeilenhöhe
            it = item_at(fl, r, QFormLayout.FieldRole)
            if it is None or item_at(fl, r, QFormLayout.SpanningRole) is not None:
                continue
            x = it.widget() or next((item_at(it.layout(), i).widget() for i in range(it.layout().count())
                                     if item_at(it.layout(), i).widget() is not None), None) if it.layout() or it.widget() else None
            if isinstance(x, QLabel) and not isinstance(x, HintLabel) and HINT_CSS not in (x.styleSheet() or "") \
                    and not (x.wordWrap() and x.alignment() & Qt.AlignHCenter):
                x.setIndent(13)
                x.setMinimumHeight(CONTROL_H)
                lab = item_at(fl, r, QFormLayout.LabelRole)   # Beschriftung auf dieselbe Höhe (sonst 3 px höher)
                if lab is not None and isinstance(lab.widget(), QLabel):
                    lab.widget().setMinimumHeight(CONTROL_H)
                    lab.widget().setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        for r in reversed(range(fl.rowCount())):
            it = item_at(fl, r, QFormLayout.FieldRole)
            if it is None or item_at(fl, r, QFormLayout.SpanningRole) is not None:   # ganze Breite: oben erledigt
                continue
            w, lay = it.widget(), it.layout()
            if w is not None:
                if isinstance(w, QAbstractItemView):
                    lw, _ = take_row(fl, r)                   # Tabelle: Beschriftung darüber, Tabelle volle Breite
                    fl.insertRow(r, w)
                    if lw is not None and (not isinstance(lw, QLabel) or lw.text()):
                        fl.insertRow(r, lw)
                    _cell(w, max(span_all, W))
                elif isinstance(w, (QLineEdit, QComboBox, QAbstractSpinBox, QAbstractScrollArea)) and w.maximumWidth() != U:
                    _cell(w, W)
                elif isinstance(w, QPushButton) and not w.text() and w.icon().isNull():   # Farbfeld allein: volle Breite
                    w.setFixedWidth(W)
                elif isinstance(w, QLabel) and (isinstance(w, HintLabel) or HINT_CSS in (w.styleSheet() or "")
                                                or (w.wordWrap() and w.alignment() & Qt.AlignHCenter)):
                    w.setWordWrap(True)                       # Hinweis zu den Feldern darüber: mittig unter der ganzen Wertespalte
                    w.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                    _cell(w, W)
                elif type(w) in (QWidget, QFrame) or (type(w) is QLabel and not w.text()):   # Sammelfeld, Farbfeld
                    _cell(w, W)
                    il = w.layout()
                    if isinstance(il, QHBoxLayout):
                        _pairs(il, [item_at(il, i).widget() for i in range(il.count()) if item_at(il, i).widget()], W, G)
                continue
            if isinstance(lay, QVBoxLayout) and any(isinstance(item_at(lay, i).widget(), QAbstractScrollArea)
                                                    for i in range(lay.count())):
                lw, _ = take_row(fl, r)                       # Tabelle mit Beschriftung: Beschriftung darüber,
                                                              # Tabelle über die ganze Breite
                fl.insertRow(r, lay)
                if lw is not None:
                    fl.insertRow(r, lw)
                for i in range(lay.count()):
                    if isinstance(item_at(lay, i).widget(), QAbstractScrollArea):
                        _cell(item_at(lay, i).widget(), max(span_all, W))
                continue
            if not isinstance(lay, QHBoxLayout) or lay.property("grid"):
                continue
            lay.setProperty("grid", True)
            lw_ = item_at(fl, r, QFormLayout.LabelRole)
            lw_ = lw_.widget() if lw_ is not None else None
            bts = [item_at(lay, i).widget() for i in range(lay.count()) if item_at(lay, i).widget() is not None]
            if bts and all(isinstance(x, QPushButton) for x in bts) and (lw_ is None or (isinstance(lw_, QLabel)
                                                                                         and not lw_.text())):
                _strip_stretch(lay)                           # Knopfreihe ohne Beschriftung: Wertespalte, gleich breit
                lay.setSpacing(8)
                for x in bts:
                    x.setFixedWidth((W - 8 * (len(bts) - 1)) // len(bts))
                    x.setStyleSheet("padding-left: 2px; padding-right: 2px;")   # langer Text wird nicht abgeschnitten
                continue
            ws = [item_at(lay, i).widget() for i in range(lay.count()) if item_at(lay, i).widget() is not None]
            if len(ws) >= 3 and isinstance(ws[0], QCheckBox) and isinstance(ws[1], value):
                lay.removeWidget(ws[0])                        # „☑ gesamt“/„☑ einsetzen“ unter die Werte
                fl.insertRow(r + 1, "", ws[0])
                ws = ws[1:]
            if len(ws) == 3 and isinstance(ws[0], value) and isinstance(ws[1], QLabel) and isinstance(ws[2], value):
                a, mid, b = ws
                _cell(a, U)
                _cell(b, U)
                if len(mid.text().strip()) > 1:               # lange Zwischenbeschriftung: eigene Zeile
                    lay.removeWidget(mid)
                    lay.removeWidget(b)
                    _cell(a, W)                               # beide stehen jetzt allein: ganze Wertespalte wie alle
                    _cell(b, W)                               # Einzelfelder (Nutzerwunsch 2026-11-10)
                    _strip_stretch(lay)
                    lab = item_at(fl, r, QFormLayout.LabelRole)
                    lab = lab.widget() if lab is not None else None
                    mid.setWordWrap(True)
                    mid.setProperty("formlabel", True)
                    if lab is not None and lab.maximumWidth() < 10000:
                        mid.setMinimumWidth(lab.minimumWidth())
                        mid.setMaximumWidth(lab.maximumWidth())
                    mid.setMinimumHeight(b.sizeHint().height())
                    mid.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    mid.style().unpolish(mid)
                    mid.style().polish(mid)
                    fl.insertRow(r + 1, mid, b)
                else:
                    lay.setSpacing(0)
                    mid.setMinimumWidth(G)
                    mid.setMaximumWidth(G)
                    mid.setAlignment(Qt.AlignCenter)
                _strip_stretch(lay)
                continue
            if len(ws) == 1 and isinstance(ws[0], value):     # Einzelfeld: immer die ganze Wertespalte (Nutzerwunsch
                _cell(ws[0], W)                               # 2026-11-10: alle Felder gleich breit)
                _strip_stretch(lay)
                continue
            if len(ws) == 2 and isinstance(ws[0], value) and isinstance(ws[1], (QCheckBox,) + value):
                _cell(ws[0], U)
                if isinstance(ws[1], value):
                    _cell(ws[1], U)
                lay.setSpacing(G)
                _strip_stretch(lay)
                continue
            if 2 <= len(ws) <= 4 and all(isinstance(x, QCheckBox) for x in ws):   # PDF SVG PNG: gleich verteilt
                lay.setSpacing(0)
                _strip_stretch(lay)
                for x in ws:
                    x.setFixedWidth(W // len(ws))
                continue
            if _pairs(lay, ws, W, G):
                continue
            # Datei-, Einheits- und Auswahl+Knopf-Zeilen: das dehnbare Element füllt bis zur Kante
            fill = [x for x in ws if (isinstance(x, QLabel) and lay.stretch(lay.indexOf(x)) > 0)
                    or (isinstance(x, (QLineEdit, QComboBox)) and x.maximumWidth() != U)]
            if not fill:
                continue
            for x in ws:
                if isinstance(x, QPushButton) and x.text() == T("remove") and len(ws) > 2:
                    x.setToolTip(T("remove"))                 # Dateizeilen: Papierkorb statt Text (Platz für den Namen)
                    x.setText("")
                    x.setIcon(icon("trash"))
                    x.setFixedWidth(34)
            others = sum(x.minimumWidth() if x.minimumWidth() == x.maximumWidth() else x.sizeHint().width()
                         for x in ws if x is not fill[0]) + 8 * (len(ws) - 1)
            if W - others < 60:                               # passt nicht ins Raster: Zeile bleibt, wie sie ist
                continue
            lay.setSpacing(8)
            _strip_stretch(lay)
            fill[0].setMinimumWidth(0)
            fill[0].setFixedWidth(W - others)


def guard_fields(root):
    """Wheel guard per field: an application-wide Python event filter wraps WebEngine's private QObjects while they
    are built (native crash, PySide 6.12/macOS). Typed searches never wrap the other children."""
    guard = getattr(QApplication.instance(), "_wheel_guard", None)
    if guard is None or not elucida.octet_enabled():
        return
    for field in root.findChildren(QAbstractSpinBox) + root.findChildren(QComboBox):
        field.installEventFilter(guard)
        guard.eventFilter(field, QEvent(QEvent.Polish))


def _guard_dialog(*_):
    win = QApplication.activeWindow()
    if isinstance(win, QDialog):                               # Dialoge laufen nicht durch tidy
        guard_fields(win)
        QApplication.instance()._wheel_guard.eventFilter(win, QEvent(QEvent.Polish))   # Dialogränder


def _watch(obj, name, fn):
    """`fn()` nach jedem Aufruf von obj.<name>(…) aus Python (z. B. setChecked mit blockierten Signalen)."""
    orig = getattr(obj, name)

    def wrapped(*a, **k):
        out = orig(*a, **k)
        fn()
        return out
    setattr(obj, name, wrapped)


class SpecialReset(QObject):
    """Zahlenfeld, dessen unterster Wert „auto“ oder „aus“ heißt (Nutzerwunsch 2026-11-12: „schwer, wieder auf auto
    zu stellen“): ein Symbol im Feld stellt mit einem Klick zurück – sichtbar nur, solange ein eigener Wert gilt –, und
    ein geleertes Feld gilt beim Verlassen oder mit Enter ebenfalls als „auto“/„aus“ (Qt holte sonst still den alten
    Wert zurück). `tidy` hängt es an jedes Zahlenfeld mit Sondertext; AutoRange übergibt Zustand und Rücksetzen selbst."""

    def __init__(self, spin, is_special=None, reset=None, name=None):
        super().__init__(spin)
        from elucida.app.i18n import T
        self.spin = spin
        self.is_special = is_special or (lambda: spin.value() <= spin.minimum() + 1e-9)
        self.reset = reset or (lambda: spin.setValue(spin.minimum()))
        self.act = spin.lineEdit().addAction(icon("reset", colors()["text2"]), QLineEdit.TrailingPosition)
        self.act.setToolTip(T("reset_special_tip", what=name or spin.specialValueText() or T("auto")))
        self.act.triggered.connect(self.clicked)
        spin.valueChanged.connect(self.sync)
        spin.installEventFilter(self)                          # Fokus und Tasten gehen an das Zahlenfeld, nicht an sein Textfeld
        spin._special_reset = self
        self.sync()

    def clicked(self, *_):
        self.reset()
        self.sync()

    def sync(self, *_):
        self.act.setVisible(not self.is_special())

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QEvent.FocusOut or (t == QEvent.KeyPress and ev.key() in (Qt.Key_Return, Qt.Key_Enter)):
            if not self.spin.lineEdit().text().replace(self.spin.suffix(), "").replace(self.spin.prefix(), "").strip() \
                    and not self.is_special():
                self.clicked()                                 # Feld geleert: wieder „auto“/„aus“
        return False


def special_resets(root):
    """Jedes Zahlenfeld mit Sondertext („auto“, „aus“) bekommt das Rücksetz-Symbol (`SpecialReset`), einmal."""
    for sp in root.findChildren(QAbstractSpinBox):
        if sp.specialValueText() and getattr(sp, "_special_reset", None) is None and hasattr(sp, "minimum"):
            SpecialReset(sp)


class AutoRange(QObject):
    """Bereich ohne Kästchen „gesamt/auto“ (Nutzerwunsch 2026-11-10): ist der Bereich automatisch, zeigen beide Felder
    „auto“; ein Klick hinein schaltet auf eigene Grenzen (die zuletzt benutzten Werte), ein geleertes Feld zurück auf
    automatisch. Das Kästchen bleibt verborgen als Träger des Zustands: Signale, Speichern und Code der Tabs wie bisher."""

    def __init__(self, cb, spins):
        super().__init__(cb)
        from elucida.app.i18n import T
        self.cb, self.spins, self.ghosts = cb, list(spins), []
        cb.setProperty("nochip", True)
        cb.hide()
        for sp in self.spins:
            holder = QWidget(sp)                              # liegt über dem Zahlenfeld, solange „auto“ gilt; das Feld
            hl = QHBoxLayout(holder)                          # nicht direkt im Zahlenfeld: Qt zeichnete es dort ohne Fläche
            hl.setContentsMargins(0, 0, 0, 0)
            g = QLineEdit(holder)
            hl.addWidget(g)
            g.setReadOnly(True)
            g.setPlaceholderText(T("auto"))
            g.setToolTip(T("auto_range_tip"))
            g.installEventFilter(self)
            self.ghosts.append(g)
            sp.setToolTip((sp.toolTip() + "\n" if sp.toolTip() else "") + T("auto_range_clear_tip"))
            sp.installEventFilter(self)
            sp.lineEdit().installEventFilter(self)
            SpecialReset(sp, cb.isChecked, lambda: cb.setChecked(True), T("auto"))   # ein Klick zurück auf „auto“
        cb.toggled.connect(self.sync)
        _watch(cb, "setChecked", self.sync)
        self.sync()

    def sync(self, *_):
        auto = self.cb.isChecked()
        for g, sp in zip(self.ghosts, self.spins):
            if auto and not sp.isEnabled():
                sp.setEnabled(True)                           # der Tab sperrt die Felder bei „auto“: hier ersetzt das die Anzeige
            g.parentWidget().setGeometry(sp.rect())
            g.parentWidget().setVisible(auto)
            g.parentWidget().raise_()
            if getattr(sp, "_special_reset", None) is not None:
                sp._special_reset.sync()

    def eventFilter(self, obj, ev):
        t = ev.type()
        if obj in self.ghosts:
            if t == QEvent.MouseButtonPress or (t == QEvent.KeyPress and (ev.text().strip() or ev.key() in (
                    Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space))):
                sp = self.spins[self.ghosts.index(obj)]
                self.cb.setChecked(False)
                sp.setFocus()
                sp.selectAll()
                return True
        elif obj in self.spins:
            if t in (QEvent.Resize, QEvent.EnabledChange, QEvent.Show):
                self.sync()
        elif t == QEvent.FocusOut or (t == QEvent.KeyPress and ev.key() in (Qt.Key_Return, Qt.Key_Enter)):
            sp = next((x for x in self.spins if x.lineEdit() is obj), None)
            if sp is not None and not sp.cleanText().strip() and not self.cb.isChecked():
                self.cb.setChecked(True)                      # Feld geleert: wieder automatisch
        return False


def off_spin(cb, spin):
    """Schalter `cb` und sein Wert `spin` stehen in getrennten Zeilen: `tidy` macht daraus ein Feld mit „aus“ (OffSpin)."""
    cb._off_spin = spin


def _make_off_spin(cb, spin):
    """Ein Feld statt Kästchen + Zahlenfeld (Nutzerwunsch 2026-11-10): der unterste Wert zeigt „aus“. Kästchen und
    Zahlenfeld des Tabs bleiben verborgen als Träger des Zustands (Signale, Speichern, Code der Tabs wie bisher); der
    Wert bleibt erhalten, während „aus“ gilt."""
    from PySide6.QtWidgets import QDoubleSpinBox
    from elucida.app.i18n import T

    class OffSpin(QDoubleSpinBox):
        def stepBy(self, steps):
            if self.value() <= self.minimum() + 1e-9:         # aus → ein: der zuletzt benutzte Wert
                if steps > 0:
                    cb.setChecked(True)
                return
            super().stepBy(steps)

    f = OffSpin(spin.parentWidget())
    step = spin.singleStep()
    f.setDecimals(spin.decimals() if hasattr(spin, "decimals") else 0)
    f.setSingleStep(step)
    f.setRange(spin.minimum() - step, spin.maximum())
    f.setSuffix(spin.suffix())
    f.setPrefix(spin.prefix())
    f.setSpecialValueText(T("off"))
    f.setToolTip("\n".join(t for t in (cb.toolTip(), spin.toolTip()) if t))
    cb.setProperty("nochip", True)
    cb.hide()
    spin.hide()

    def sync(*_):
        f.blockSignals(True)
        f.setValue(spin.value() if cb.isChecked() else f.minimum())
        f.blockSignals(False)

    def to_model(v):
        if v <= f.minimum() + 1e-9:
            cb.setChecked(False)
        else:
            spin.setValue(v if hasattr(spin, "decimals") else int(round(v)))
            cb.setChecked(True)

    f.valueChanged.connect(to_model)
    cb.toggled.connect(sync)
    spin.valueChanged.connect(sync)
    _watch(cb, "setChecked", sync)
    _watch(spin, "setValue", sync)
    sync()
    f.model = (cb, spin)
    return f


def _make_off_combo(cb, combo):
    """Eine Auswahlliste statt Kästchen + Auswahlliste: erster Eintrag „aus“. Die Widgets des Tabs bleiben verborgen als
    Träger des Zustands (wie OffSpin)."""
    from elucida.app.i18n import T
    f = QComboBox(combo.parentWidget())
    f.addItem(T("off"))
    for i in range(combo.count()):
        f.addItem(combo.itemText(i))
    f.setToolTip("\n".join(t for t in (cb.toolTip(), combo.toolTip()) if t))
    cb.setProperty("nochip", True)
    cb.hide()
    combo.hide()

    def sync(*_):
        f.blockSignals(True)
        f.setCurrentIndex(combo.currentIndex() + 1 if cb.isChecked() else 0)
        f.blockSignals(False)

    def to_model(i):
        if i <= 0:
            cb.setChecked(False)
        else:
            combo.setCurrentIndex(i - 1)
            cb.setChecked(True)

    f.currentIndexChanged.connect(to_model)
    cb.toggled.connect(sync)
    combo.currentIndexChanged.connect(sync)
    _watch(cb, "setChecked", sync)
    _watch(combo, "setCurrentIndex", sync)
    sync()
    f.model = (cb, combo)
    return f


def _flow(widgets, width, apply, gap=6):
    """Widgets nebeneinander setzen, Umbruch am Rand; verborgene belegen keinen Platz. Gibt die Höhe zurück."""
    x, y, h = 0, 0, 0
    for b in widgets:
        if b.isHidden():
            continue
        b.ensurePolished()
        sz = b.sizeHint()
        if x > 0 and x + sz.width() > width:
            x, y, h = 0, y + h + gap, 0
        if apply:
            b.setGeometry(x, y, min(sz.width(), max(width, 1)), sz.height())
        x += sz.width() + gap
        h = max(h, sz.height())
    return y + h


# Formelzeichen wie im Satz (Nutzerwunsch 2026-11-11): Größen kursiv, Indizes tief, Einheiten steil. Nur für Texte, die
# ein QLabel als Rich-Text zeigt (Rechenweg, Kacheln, Beschriftungen); Tabellenköpfe und Auswahllisten können das nicht.
_SCI = [(r"Δ?E½", lambda m: ("Δ" if m.group(0).startswith("Δ") else "") + "<i>E</i><sub>1/2</sub>"),
        (r"ΔE[pP]\b", "Δ<i>E</i><sub>p</sub>"), (r"\bE(pa|pc|p)\b", r"<i>E</i><sub>\1</sub>"),
        (r"\bip,([rfac])\b", r"<i>i</i><sub>p,\1</sub>"),      # Nicholson: i_p,r / i_p,f – Index samt Komma tief
        (r"\bi(pa|pc|p)\b", r"<i>i</i><sub>\1</sub>"), (r"λ(max|em|ex)\b", r"<i>λ</i><sub>\1</sub>"),
        (r"R²", "<i>R</i>²"), (r"\bm/z\b", "<i>m</i>/<i>z</i>"), (r"ε(?![a-zäöü])", "<i>ε</i>"), (r"λ(?![a-zäöü<])", "<i>λ</i>"),
        (r"\bA/d\b", "<i>A</i>/<i>d</i>"), (r"\bE°", "<i>E</i>°"), (r"ṽ", "<i>ṽ</i>"), (r"ν(?![a-zäöü])", "<i>ν</i>"),
        # Größe vor ihrer Einheit „E [V]“, „m [mg]“, „ρ [g mL⁻¹]“ (nicht S: „S [%]“ ist Schwefel) und vor „=“/„≤“
        (r"(?<![A-Za-zäöüÄÖÜß>])([EMTJnjcdgvBVmhItiaAfkUDQρδ])(?= \[|-Bereich| range|-Korrektur| correction)", r"<i>\1</i>"),
        # nicht nach „_“: „E_a = …“ gehört der Indexregel am Ende (sonst blieb der Unterstrich stehen)
        (r"(?<![A-Za-zäöüÄÖÜß>_])([EMTJnjcdgvBSDaAkIt])(?= = | ≤ | ≥ | &gt; | &lt; )", r"<i>\1</i>"),
        # Kinetik (EPR-Zerfälle, Arrhenius): t½, 1/T, ln k, I0, I(t), Ea, 10^-4
        (r"\bt½", "<i>t</i><sub>1/2</sub>"), (r"\b1/T\b", "1/<i>T</i>"), (r"(?<=ln )([kA])\b", r"<i>\1</i>"),
        (r"(?<=ln\()A\b", "<i>A</i>"), (r"\bI0\b", "<i>I</i><sub>0</sub>"), (r"\bI(?=\([tT]\))", "<i>I</i>"),
        (r"\bA0\b", "<i>A</i><sub>0</sub>"), (r"\bA(?=\(t\))", "<i>A</i>"),                    # UV-Vis-Kinetik
        (r"\(([tT])\)", r"(<i>\1</i>)"), (r"·t\b", "·<i>t</i>"), (r"\bEa\b", "<i>E</i><sub>a</sub>"),
        (r"10\^(-?)(\d+)", lambda m: "10<sup>" + ("−" if m.group(1) else "") + m.group(2) + "</sup>"),
        (r"/RT\b", "/<i>RT</i>"), (r"β(?= = )", "<i>β</i>"), (r"(?<= of )k\b", "<i>k</i>"),
        (r"\bcm2\b", "cm²"), (r"(?<![A-Za-zäöüÄÖÜß>_])D(?= = )", "<i>D</i>"),                         # D = … cm2 s-1
        (r"(?<=Cutoff )A\b", "<i>A</i>"), (r"\b([BWH]) × (H)\b", r"<i>\1</i> × <i>\2</i>"),            # B × H
        (r"\((Δ?)A\)", r"(\1<i>A</i>)"), (r"%T\b", "%<i>T</i>"), (r"\|([A-Za-z])\|", r"|<i>\1</i>|"),   # (ΔA), %T, |E|
        (r"\bD(?= (?:und|and) \|)", "<i>D</i>"), (r"(?<=× )T\b", "<i>T</i>"), (r"(?<=/)T$", "<i>T</i>"),
        (r"(?<=[a-zäöüß] )([jfnAc])$", r"<i>\1</i>"),                                                    # „Stromdichte j“
        (r"(?<=gegen )(√?)([EvνT])\b", r"\1<i>\2</i>"), (r"(?<=against )(√?)([EvνTc])\b", r"\1<i>\2</i>"),
        (r"(?<=log )([vi])\b", r"<i>\1</i>"), (r"√([vν])", r"√<i>\1</i>"),
        (r"·c\b", "·<i>c</i>"), (r"(?<=\+ )b\b", "<i>b</i>"), (r"\bk(?=·)", "<i>k</i>"),               # A/d = ε·c + b
        (r"\(g, a, ", "(<i>g</i>, <i>a</i>, "), (r"\ba(?=/mT)", "<i>a</i>"), (r"^([TD])(?= aus | from )", r"<i>\1</i>"),
        (r"^([xyz])(?=[+−]$)", r"<i>\1</i>"), (r"^([cdgn])$", r"<i>\1</i>"), (r"^Δ([A-Z])$", r"Δ<i>\1</i>"),
        (r"\bA(?= bei | at )", "<i>A</i>"), (r"\bM(?= / )", "<i>M</i>"), (r"\bn/n\(", "<i>n</i>/<i>n</i>("),
        (r"\b([xy])(?=-Achse|-Größe|-Bereich| axis| range)", r"<i>\1</i>"),              # E [V], M = …, E-Bereich, y-Achse
        (r"(?<![A-Za-zäöüÄÖÜß>])([AEc])(?= gegen | vs\. | against |\()", r"<i>\1</i>"),    # A gegen E, E(Fc⁺/Fc)
        (r"ΔBpp\b", "Δ<i>B</i><sub>pp</sub>"), (r"\bisp\b", "<i>i</i><sub>sp</sub>"),                     # Methodentexte
        (r"\bv1/2\b", "<i>v</i><sup>1/2</sup>"), (r"\)0(?=[/\s,.;)])", ")<sub>0</sub>"),                 # v1/2, (i_sp)0
        (r"\^-½", "<sup>−½</sup>"), (r"\b(mV|V|mA|µA|mg|g) (s|mL|L|mol)-1\b", r"\1 \2<sup>−1</sup>"),    # mV s-1
        (r"(Δ?)([Ei])(?=[ₐₑₒₓₚ₁₂])", r"\1<i>\2</i>"),                                                 # ΔEₚ mit Unicode-Index
        # g_lit, n_app, A_red, i_p,r – nicht in Dateinamen („6d_IR.0“: Ziffer davor bzw. Endung dahinter)
        (r"(?<![A-Za-z0-9äöüÄÖÜß>])([A-Za-zνΔ])_([A-Za-z0-9]+(?:,[A-Za-z0-9]+)*)(?![A-Za-z0-9_-]*\.[A-Za-z0-9])",
         r"<i>\1</i><sub>\2</sub>")]


def _sci_changes(text):
    """HTML, wenn `text` Formelzeichen enthält, sonst None."""
    h = sci(text)
    return h if h != str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") else None


class _SciItems(QStyledItemDelegate):
    """Einträge einer Auswahlliste mit Formelzeichen wie im Satz (kursive Größen, tiefe Indizes)."""

    def paint(self, painter, option, index):
        from PySide6.QtGui import QTextDocument
        h = _sci_changes(str(index.data(Qt.DisplayRole) or ""))
        if h is None:
            return super().paint(painter, option, index)
        o = QStyleOptionViewItem(option)
        self.initStyleOption(o, index)
        st = o.widget.style() if o.widget is not None else QApplication.style()
        r = st.subElementRect(QStyle.SE_ItemViewItemText, o, o.widget)
        o.text = ""
        st.drawControl(QStyle.CE_ItemViewItem, o, painter, o.widget)
        col = (o.palette.highlightedText() if o.state & QStyle.State_Selected else o.palette.text()).color()
        doc = QTextDocument()
        doc.setDefaultFont(o.font)
        doc.setDocumentMargin(0)
        doc.setHtml(f"<span style='color:{col.name()}'>{h}</span>")
        painter.save()
        painter.setClipRect(r)
        painter.translate(r.x() + st.pixelMetric(QStyle.PM_FocusFrameHMargin, None, o.widget) + 1,
                          r.center().y() + 1 - doc.size().height() / 2)
        doc.drawContents(painter)
        painter.restore()


class _SciPaint(QObject):
    """Knöpfe, Chips und Auswahllisten zeichnen nur reinen Text. Enthält ihr Text Formelzeichen, zeichnet dieser Filter
    die Fläche über den Stil ohne Text und den Text selbst als Rich-Text: Größen kursiv, Indizes tief wie in den
    Beschriftungen (Nutzerwunsch 2026-11-11, „überall“). Der Text des Widgets bleibt der reine Text."""

    def eventFilter(self, w, ev):
        if ev.type() != QEvent.Paint:
            return False
        try:
            return self._paint(w)
        except RuntimeError:                                 # Widget wird gerade gelöscht
            return False

    @staticmethod
    def _paint(w):
        from PySide6.QtGui import QPalette, QTextDocument
        from PySide6.QtWidgets import QStyleOptionButton, QStyleOptionComboBox, QStylePainter
        combo = isinstance(w, QComboBox)
        h = _sci_changes(w.currentText() if combo else w.text())
        if h is None or (not combo and not w.icon().isNull()) or (combo and w.isEditable()):
            return False
        c = colors()
        p = QStylePainter(w)
        if combo:
            if not isinstance(w.itemDelegate(), _SciItems):
                w.setItemDelegate(_SciItems(w))
            o = QStyleOptionComboBox()
            w.initStyleOption(o)
            o.currentText = ""
            p.drawComplexControl(QStyle.CC_ComboBox, o)
            r = w.style().subControlRect(QStyle.CC_ComboBox, o, QStyle.SC_ComboBoxEditField, w)
        else:
            o = QStyleOptionButton()
            w.initStyleOption(o)
            o.text = ""
            p.drawControl(QStyle.CE_CheckBox if isinstance(w, QCheckBox) else QStyle.CE_PushButton, o)
            r = w.rect()
        if not w.isEnabled():
            col = c["disabled"]
        elif w.property("chip"):
            col = c["text"] if (w.isChecked() or w.underMouse()) else c["text2"]
        else:                                                # Farbe des Stylesheets steht in der Palette des Widgets
            col = w.palette().color(QPalette.Active, QPalette.Text if combo else QPalette.ButtonText).name()
        doc = QTextDocument()
        doc.setDefaultFont(w.font())
        doc.setDocumentMargin(0)
        doc.setHtml(f"<span style='color:{col}'>{h}</span>")
        x = r.x() if combo else r.x() + (r.width() - doc.idealWidth()) / 2
        p.setClipRect(r)
        p.translate(x, r.y() + (r.height() - doc.size().height()) / 2)
        doc.drawContents(p)
        return True


_sci_paint = None


def sci_widgets(root):
    """Knöpfe, Chips und Auswahllisten unter `root` zeichnen Formelzeichen wie im Satz (siehe _SciPaint)."""
    global _sci_paint
    if _sci_paint is None:
        _sci_paint = _SciPaint(QApplication.instance())
    for w in root.findChildren(QPushButton) + root.findChildren(QCheckBox) + root.findChildren(QComboBox):
        if not w.property("scipaint"):
            w.setProperty("scipaint", True)
            w.installEventFilter(_sci_paint)
        if isinstance(w, QComboBox) and not isinstance(w.itemDelegate(), _SciItems) and \
                any(_sci_changes(w.itemText(i)) for i in range(w.count())):
            w.setItemDelegate(_SciItems(w))


def sci_label(lb):
    """Beschriftung als Rich-Text setzen, wenn sie Formelzeichen enthält (sonst bleibt sie, wie sie ist)."""
    t = lb.text()
    if not t or "<" in t or lb.textFormat() == Qt.RichText:
        return
    h = sci(t)
    if h != t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"):
        lb.setTextFormat(Qt.RichText)
        lb._sci = True                                       # von hier gesetzt: beim nächsten Text wieder aufheben
        QLabel.setText(lb, h.replace("\n", "<br>"))


def _set_sci(lb, text):
    """setText für Texte, die sich ändern (Hinweise, Ergebniszeilen): Formelzeichen jedes Mal neu setzen."""
    if getattr(lb, "_sci", False):
        lb._sci = False
        lb.setTextFormat(Qt.AutoText)
    lb._plain = text                                         # text() gibt weiter den gesetzten Text zurück, nicht das HTML
    QLabel.setText(lb, text)
    sci_label(lb)


class SciLabel(QLabel):
    """Ergebnis- oder Infotext mit Formelzeichen wie im Satz (E₁/₂, ΔEₚ, R² …), bei jedem setText. `empty`: Text,
    solange es nichts zu zeigen gibt (sonst stünde auf der Ergebnisseite eine leere Karte)."""

    def __init__(self, text="", empty=""):
        super().__init__()
        self.empty = empty
        self.setText(text)

    def setText(self, text):
        shown = text or self.empty
        # Platzhalter und kurze Hinweise einer Ergebnisseite stehen groß in der Mitte der Karte (Nutzerwunsch 2026-11-11:
        # oben links wirkten sie verloren); mehrzeilige Ergebnisse wie bisher oben links
        short = bool(self.empty) and "\n" not in shown and len(shown) <= 180
        if short != getattr(self, "_short", None):
            self._short = short
            self.setAlignment(Qt.AlignCenter if short else Qt.AlignLeft | Qt.AlignTop)
            self.setStyleSheet("font-size: 15px; color: gray;" if short else "")
            if self.empty:
                self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        _set_sci(self, shown)

    def text(self):
        return getattr(self, "_plain", QLabel.text(self))


class RichHeader(QHeaderView):
    """Tabellenkopf, der Formelzeichen wie im Satz zeichnet (kursive Größen, tiefgestellte Indizes: Eₚₐ [V], R²).
    Köpfe ohne solche Zeichen zeichnet Qt wie immer."""

    def paintSection(self, painter, rect, index):
        from PySide6.QtGui import QTextDocument
        from PySide6.QtWidgets import QStyleOptionHeader
        text = str(self.model().headerData(index, self.orientation(), Qt.DisplayRole) or "")
        h = sci(text)
        if h == text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"):
            return super().paintSection(painter, rect, index)
        opt = QStyleOptionHeader()
        self.initStyleOption(opt)
        opt.rect, opt.section, opt.text = rect, index, ""
        painter.save()
        self.style().drawControl(QStyle.CE_Header, opt, painter, self)       # Hintergrund und Linien wie die anderen
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        doc.setDocumentMargin(0)
        doc.setHtml(f"<span style='color:{colors()['text2']}'>{h}</span>")
        painter.translate(rect.x() + (rect.width() - doc.idealWidth()) / 2, rect.y() + (rect.height() - doc.size().height()) / 2)
        doc.drawContents(painter)
        painter.restore()


def rich_header(t):
    """Kopf der Tabelle gegen einen RichHeader tauschen, wenn seine Texte Formelzeichen enthalten; Breiten, Modi und
    verborgene Spalten bleiben."""
    old = t.horizontalHeader()
    n = old.count()
    texts = [str(t.model().headerData(i, Qt.Horizontal, Qt.DisplayRole) or "") for i in range(n)]
    if isinstance(old, RichHeader) or not any(sci(x) != x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                              for x in texts):
        return
    modes = [old.sectionResizeMode(i) for i in range(n)]
    sizes = [old.sectionSize(i) for i in range(n)]
    hidden = [old.isSectionHidden(i) for i in range(n)]
    order = sorted(range(n), key=old.visualIndex)            # verschobene Spalten (Kästchen vorn) bleiben, wo sie sind
    new = RichHeader(Qt.Horizontal, t)
    new.setStretchLastSection(old.stretchLastSection())
    new.setMinimumSectionSize(old.minimumSectionSize())
    new.setDefaultSectionSize(old.defaultSectionSize())
    new.setDefaultAlignment(old.defaultAlignment())
    new.setSectionsClickable(old.sectionsClickable())
    new.setHighlightSections(old.highlightSections())
    vis = not old.isHidden()
    t.setHorizontalHeader(new)
    for i in range(n):
        new.setSectionResizeMode(i, modes[i])
        if modes[i] in (QHeaderView.Fixed, QHeaderView.Interactive):
            new.resizeSection(i, sizes[i])
        new.setSectionHidden(i, hidden[i])
    for v, i in enumerate(order):
        new.moveSection(new.visualIndex(i), v)
    new.setVisible(vis)                                      # den alten Kopf löscht Qt beim Tausch selbst


def sci(text, escape=True):
    """Text -> HTML mit Formelzeichen im wissenschaftlichen Satz (siehe _SCI). escape=False: `text` ist schon ein
    Textstück aus HTML (zwischen zwei Tags)."""
    import html as _html
    import re as _re
    out = _html.escape(str(text), quote=False) if escape else str(text)
    for pat, rep in _SCI:
        out = _re.sub(pat, rep, out)
    return out


class ChainRow(QWidget):
    """Rechenweg eines Tabs (Entwurf 2026-11): die Schritte der Auswertung als Kette, benutzte hervorgehoben. Nur
    Anzeige – geschaltet wird in den Feldern darunter. Ein Pfeil bleibt beim Umbruch vor seinem Schritt."""
    GAP = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.units, self.items, self.gap = [], None, self.GAP   # je Schritt (Pfeil oder None, Beschriftung)

    def set_items(self, items):
        items = [(str(t), bool(on)) for t, on in items]
        if items == self.items:
            return
        self.items = items
        for arrow, lb in self.units:
            for x in (arrow, lb):
                if x is not None:
                    x.hide()
                    x.deleteLater()
        self.units = []
        for i, (text, on) in enumerate(items):
            arrow = QLabel("→", self, objectName="chainArrow") if i else None
            lb = QLabel(sci(text), self, objectName="chainStep")
            lb.setTextFormat(Qt.RichText)
            lb.setProperty("on", on)
            for x in (arrow, lb):
                if x is not None:
                    x.show()
            self.units.append((arrow, lb))
        self.updateGeometry()
        self._place(self.width(), True)

    def _fit(self, width):
        """Passt die Kette nicht in eine Zeile, rückt sie zusammen (schmalere Pillen, kleinere Abstände); erst wenn das
        nicht reicht, bricht sie um."""
        for tight in ("", "1", "2"):                         # normal, enger, enger mit kleinerer Schrift
            self.gap = {"": self.GAP, "1": 3, "2": 2}[tight]
            for _a, lb in self.units:
                if (lb.property("tight") or "") != tight:
                    lb.setProperty("tight", tight)
                    lb.style().unpolish(lb)
                    lb.style().polish(lb)
                    self.updateGeometry()                    # Höhe der Karte folgt (eine Zeile statt zwei)
            need = sum(lb.sizeHint().width() + self.gap + (a.sizeHint().width() + self.gap if a is not None else 0)
                       for a, lb in self.units) - self.gap
            if need <= width:
                return

    def _place(self, width, apply):
        if apply:
            self._fit(width)
        x, y, h = 0, 0, 0
        for arrow, lb in self.units:
            lb.ensurePolished()
            sz = lb.sizeHint()
            aw = arrow.sizeHint().width() + self.gap if arrow is not None else 0
            if x > 0 and x + aw + sz.width() > width:
                x, y, h = 0, y + h + self.GAP, 0
            if arrow is not None:
                if apply:
                    arrow.setGeometry(x, y, aw - self.gap, sz.height())
                x += aw
            if apply:
                lb.setGeometry(x, y, min(sz.width(), max(width - x, 1)), sz.height())
            x += sz.width() + self.gap
            h = max(h, sz.height())
        return y + h

    def sizeHint(self):
        return QSize(INNER_W, self._place(self.width() if self.width() > 50 else INNER_W, False))

    def minimumSizeHint(self):
        return QSize(max((lb.sizeHint().width() for _a, lb in self.units), default=0) + 30, self.sizeHint().height())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._place(self.width(), True)


class ChipRow(QWidget):
    """Zeile aus Chips (an-/abwählbare Pillen statt Kästchen, Nutzerwunsch 2026-11-10), nebeneinander mit Umbruch am
    Rand. Die Chips sind weiter die QCheckBox-Objekte der Tabs: Zustand, Signale und Sichtbarkeit wie bisher. Ohne
    sichtbaren Chip entfällt die Zeile. Ohne QLayout: die Chips werden selbst gesetzt (ein eigenes Layout hielte
    Qt-eigene Elemente in Python fest, siehe item_at)."""
    GAP = 6

    def __init__(self, boxes, parent=None):
        super().__init__(parent)
        from elucida.app.i18n import long_form
        self.setObjectName("chips")
        self.boxes = list(boxes)
        for b in self.boxes:
            b.setProperty("chip", True)
            if "margin-left" in (b.styleSheet() or ""):
                b.setStyleSheet("")
            b.setCursor(Qt.PointingHandCursor)
            long = long_form(b.text())                        # gekürzter Text: Langform in den Tooltip
            if long and long not in (b.toolTip() or ""):
                b.setToolTip(long + ("\n" + b.toolTip() if b.toolTip() else ""))
            hidden = b.isHidden()
            b.setParent(self)
            b.setVisible(not hidden)
            b.installEventFilter(self)

    PADS = {"": 11, "1": 7, "2": 4}                          # Innenrand je Dichtestufe (wie im Stylesheet)

    def _fit(self, width):
        """Chips bleiben in einer Zeile (Nutzerwunsch 2026-11-11): reicht die Breite nicht, rücken sie in zwei Stufen
        zusammen (weniger Innenrand und Abstand). Passen sie auch dann nicht in eine Zeile, gilt die Stufe mit den
        wenigsten Zeilen, bei Gleichstand die lockerste. -> Abstand"""
        vis = [b for b in self.boxes if not b.isHidden()]
        if not vis:
            return self.GAP
        for b in vis:
            b.ensurePolished()
        now = vis[0].property("tight") or ""
        text = [b.sizeHint().width() - 2 * self.PADS[now] for b in vis]         # Breiten ohne Innenränder

        def rows(lv, gap):
            n, x = 1, 0
            for t in text:
                w = t + 2 * self.PADS[lv]
                if x > 0 and x + w > width:
                    n, x = n + 1, 0
                x += w + gap
            return n
        level, gap = min(((lv, g) for lv, g in (("", self.GAP), ("1", 5), ("2", 4))), key=lambda p: rows(*p))
        if level != now:
            for b in self.boxes:
                b.setProperty("tight", level)
                b.style().unpolish(b)
                b.style().polish(b)
        return gap

    def _place(self, width, apply):
        return _flow(self.boxes, width, apply, self._fit(width))

    def _widest(self):
        return max((b.sizeHint().width() for b in self.boxes if not b.isHidden()), default=0)

    def sizeHint(self):
        # Formulare geben Feldern ihre Wunschgröße: Breite der Wertespalte, Höhe nach dem Umbruch bei dieser Breite
        w = max(VALUE_W, self._widest())
        return QSize(w, self._place(w, False))

    def minimumSizeHint(self):
        return QSize(self._widest(), self.sizeHint().height())

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._place(self.width(), True)

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.ShowToParent, QEvent.HideToParent):
            self.sync()
        elif t in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick) \
                and ev.button() == Qt.LeftButton:
            # die ganze Pille schaltet (Qt nimmt bei Kästchen nur Klicks auf Text und Kästchen an, nicht auf den Rand)
            if t == QEvent.MouseButtonRelease and obj.rect().contains(ev.position().toPoint()):
                obj.click()
            return True
        return False

    def sync(self):
        p = self.parentWidget()
        if p is None:
            return
        self.updateGeometry()
        self._place(self.width(), True)
        vis = any(not b.isHidden() for b in self.boxes)
        form = next((fl for fl in p.findChildren(QFormLayout) if fl.indexOf(self) >= 0), None)
        if form is not None:
            form.setRowVisible(self, vis)
        else:
            self.setVisible(vis)


def _discard(w):
    """Widget entfernen; sofort verbergen, weil das Löschen erst mit der Ereignisschleife geschieht."""
    w.hide()
    w.deleteLater()


def _flabel(text):
    """Beschriftung einer Formularzeile, Farbe wie die übrigen (align_forms lief schon)."""
    lb = QLabel(text)
    lb.setProperty("formlabel", True)
    return lb


def _chips(root):
    """Vorlauf von `tidy`: Zeilen, die nur aus Kästchen bestehen, werden Chips. Unbeschriftete Kästchen einer Karte
    kommen gesammelt in eine Zeile hinter die Felder (vor Tabellen, Texte und Knopfreihen am Kartenende), beschriftete
    Zeilen (Formate) bleiben an ihrem Platz, ebenso Kästchen mit der Eigenschaft `chip_here` (gehört zum Feld direkt
    darüber). Ausnahme je Kästchen: Eigenschaft `nochip`. Beschriftung der Sammelzeile:
    Eigenschaft `chips_label` an der Karte, sonst „Optionen“."""
    from PySide6.QtWidgets import QAbstractScrollArea, QCheckBox
    from elucida.app.i18n import T

    def boxes(it):
        if it is None:
            return None, None
        w, lay = it.widget(), it.layout()
        if isinstance(w, QCheckBox):
            ws = [w]
        elif isinstance(lay, QHBoxLayout):
            ws = [x for x in (item_at(lay, i).widget() for i in range(lay.count())) if x is not None]
        else:
            return None, None
        ok = ws and all(isinstance(x, QCheckBox) and not x.property("nochip") and not x.property("chip") for x in ws)
        return (ws, lay) if ok else (None, None)

    def trailing(fl, r):
        it = item_at(fl, r, QFormLayout.SpanningRole) or item_at(fl, r, QFormLayout.FieldRole)
        if it is None:
            return True
        w, lay = it.widget(), it.layout()
        if w is not None and w.property("below_chips"):       # Feld gehört zu einem Chip der Zeile „Optionen“: bleibt darunter
            return True
        if w is not None:                                     # Tabelle, Text, Knopf, Hinweis, Unterbereich über die ganze Breite
            return isinstance(w, (QAbstractScrollArea, QPushButton)) or (
                item_at(fl, r, QFormLayout.SpanningRole) is not None
                and not isinstance(w, (QAbstractSpinBox, QComboBox, QLineEdit, ChipRow)))
        ws = [x for x in (item_at(lay, i).widget() for i in range(lay.count())) if x is not None] if lay is not None else []
        return bool(ws) and all(isinstance(x, QPushButton) for x in ws)

    for lay in root.findChildren(QHBoxLayout):                # ☑ gesamt [von] – [bis]: Felder zeigen „auto“, kein Kästchen
        ws = [x for x in (item_at(lay, i).widget() for i in range(lay.count())) if x is not None]
        if (len(ws) == 4 and isinstance(ws[0], QCheckBox) and isinstance(ws[1], QAbstractSpinBox)
                and isinstance(ws[2], QLabel) and isinstance(ws[3], QAbstractSpinBox)):
            lay.removeWidget(ws[0])
            AutoRange(ws[0], (ws[1], ws[3]))
    for fl in root.findChildren(QFormLayout):                 # ☑ Schalter [Wert]: ein Feld mit „aus“
        for r in reversed(range(fl.rowCount())):
            it = item_at(fl, r, QFormLayout.SpanningRole) or item_at(fl, r, QFormLayout.FieldRole)
            lay = it.layout() if it is not None else None
            ws = [x for x in (item_at(lay, i).widget() for i in range(lay.count())) if x is not None] \
                if isinstance(lay, QHBoxLayout) else [it.widget()] if it is not None and it.widget() is not None else []
            if not ws or not isinstance(ws[0], QCheckBox) or ws[0].property("off_done"):
                continue
            cb, rest = ws[0], ws[1:]
            if rest and isinstance(rest[0], QLabel) and len(rest) > 1 and isinstance(rest[1], QAbstractSpinBox):
                _discard(rest[0])                         # „Abstand“: steht jetzt als Beschriftung der Zeile
                rest = rest[1:]
            spin = rest[0] if rest and isinstance(rest[0], QAbstractSpinBox) else getattr(cb, "_off_spin", None)
            if spin is None or not all(isinstance(x, QCheckBox) for x in rest[1:]):
                continue
            cb.setProperty("off_done", True)
            label = _flabel(cb.text())
            if rest:                                          # alles in einer Zeile
                for x in ws:
                    lay.removeWidget(x)
                take_row(fl, r)
                shiboken6.delete(lay)
                at = r
            else:                                             # Wert in eigener Zeile (off_spin): Kästchen-Zeile entfällt
                take_row(fl, r)
                at, _ = fl.getWidgetPosition(spin)
                if at < 0:
                    continue
                old, _f = take_row(fl, at)
                if old is not None:
                    _discard(old)
            for x in (cb, spin):
                x.setParent(fl.parentWidget())
            fl.insertRow(at, label, _make_off_spin(cb, spin))
            extra = [x for x in rest[1:]]
            if extra:                                         # z. B. „im Bild zeigen“: gehört zu diesem Feld
                for x in extra:
                    x.setProperty("chip_here", True)
                fl.insertRow(at + 1, extra[0] if len(extra) == 1 else None)
    for fl in root.findChildren(QFormLayout):                 # [Feld] ☐ Zusatz in einer Zeile: Chip unter das Feld;
        for r in reversed(range(fl.rowCount())):              # ☑ Schalter [Auswahlliste]: Liste mit „aus“
            it = item_at(fl, r, QFormLayout.SpanningRole) or item_at(fl, r, QFormLayout.FieldRole)
            lay = it.layout() if it is not None else None
            if not isinstance(lay, QHBoxLayout):
                continue
            ws = [x for x in (item_at(lay, i).widget() for i in range(lay.count())) if x is not None]
            if len(ws) < 2:
                continue
            a, b = ws[0], ws[-1]
            if isinstance(b, QCheckBox) and not b.property("nochip") and not b.property("chip") and all(
                    isinstance(x, (QAbstractSpinBox, QComboBox, QLineEdit, QLabel)) for x in ws[:-1]) and any(
                    not isinstance(x, QLabel) for x in ws[:-1]):
                lay.removeWidget(b)
                b.setProperty("chip_here", True)
                fl.insertRow(r + 1, "", ChipRow([b]))
            elif len(ws) == 2 and isinstance(a, QCheckBox) and isinstance(b, QComboBox) and not a.property("off_done"):
                a.setProperty("off_done", True)
                for x in ws:
                    lay.removeWidget(x)
                lw, _ = take_row(fl, r)
                if lw is not None:
                    _discard(lw)
                shiboken6.delete(lay)
                for x in ws:
                    x.setParent(fl.parentWidget())
                fl.insertRow(r, _flabel(a.text()), _make_off_combo(a, b))
    for box in root.findChildren(QVBoxLayout):                # Kästchen direkt in einer Karte ohne Formular: Chip an ihrem Platz
        i = 0
        while i < box.count():
            x = item_at(box, i).widget()
            if isinstance(x, QCheckBox) and not x.property("nochip") and not x.property("chip") \
                    and not isinstance(x.parentWidget(), ChipRow):
                box.removeWidget(x)
                box.insertWidget(i, ChipRow([x]))
            i += 1
    for fl in root.findChildren(QFormLayout):
        found = []
        for r in range(fl.rowCount()):
            lab = item_at(fl, r, QFormLayout.LabelRole)
            lw = lab.widget() if lab is not None else None
            it = item_at(fl, r, QFormLayout.SpanningRole) or item_at(fl, r, QFormLayout.FieldRole)
            ws, lay = boxes(it)
            if ws:
                found.append((r, ws, lay, lw))
        loose = []
        for r, ws, lay, lw in reversed(found):
            for x in ws if lay is not None else []:
                lay.removeWidget(x)
            taken_label, _ = take_row(fl, r)
            if lay is not None:
                shiboken6.delete(lay)
            if isinstance(lw, QLabel) and lw.text().strip():   # beschriftete Zeile (Formate): an ihrem Platz
                fl.insertRow(r, lw, ChipRow(ws))
            elif any(x.property("chip_here") for x in ws):    # gehört zum Feld darüber: bleibt darunter
                if taken_label is not None:
                    _discard(taken_label)
                fl.insertRow(r, "", ChipRow(ws))
            else:
                loose[:0] = ws
                if taken_label is not None:
                    _discard(taken_label)
        if loose:
            end = fl.rowCount()
            while end > 0 and trailing(fl, end - 1):
                end -= 1
            p, label = fl.parentWidget(), None
            while p is not None and label is None:
                label, p = p.property("chips_label"), p.parentWidget()
            fl.insertRow(end, _flabel(label or T("chips_options")), ChipRow(loose))


def _wide_fields(root):
    """Karten über die ganze Seitenbreite (Bildunterschrift im Reiter „SI-Text“, Eigenschaft `widefields`): Textfelder
    reichen bis zum Kartenrand wie Text und Knopf darunter, nicht nur bis zur Rasterbreite der linken Spalte. Als letzter
    Schritt von tidy, weil _field_edge die Felder bei jedem Durchlauf wieder festsetzt."""
    from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QSizePolicy, QTextEdit
    for card in [w for w in [root] + root.findChildren(QWidget) if w.property("widefields")]:
        fl = card.layout()
        if not isinstance(fl, QFormLayout):
            continue
        fl.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        for r in range(fl.rowCount()):
            it = item_at(fl, r, QFormLayout.FieldRole)
            w = it.widget() if it is not None else None
            if isinstance(w, (QLineEdit, QComboBox, QPlainTextEdit, QTextEdit)):
                w.setProperty("fieldw", None)
                w.setMinimumWidth(0)
                w.setMaximumWidth(16777215)
                w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


def tidy(root):
    """Linke Spalte ruhiger: Zeilenabstand 8 px, einzelne Knöpfe in Formularen in natürlicher Breite statt als
    Balken über die ganze Karte, reine Symbol-Knöpfe (↑/↓) quadratisch. Vor dem Bestimmen der Spaltenbreite aufrufen."""
    from PySide6.QtWidgets import QGroupBox
    guard_fields(root)
    _chips(root)
    special_resets(root)                                      # nach _chips: die „aus“-Felder entstehen dort
    top = root.layout()
    if isinstance(top, QVBoxLayout):                          # Spalte: gleicher Rand und Abstand zwischen Karten
        top.setContentsMargins(COL_PAD, COL_PAD, 0, COL_PAD)   # rechts: Bildlaufleiste (ColumnFit), zusammen COL_PAD
        top.setSpacing(10)
    for g in root.findChildren(QGroupBox):                    # Karten: gleicher Innenrand (oben sitzt der Titel)
        if g.layout() is not None and not g.property("flat") and not any(isinstance(f, Fold) and f.group is g for f in g.children()):
            g.layout().setContentsMargins(*((12, 12, 12, 12) if g.objectName() == "resultCard" else CARD_MARGINS))
        if isinstance(g.layout(), QVBoxLayout) and g.objectName() != "resultCard":
            g.layout().setSpacing(ROW_GAP)                    # Knopfreihe, Liste, Hinweis: derselbe Abstand wie Formularzeilen
    for v_ in root.findChildren(QVBoxLayout):                 # geschachtelte Spalten in Karten ebenso
        if isinstance(v_.parentWidget(), QGroupBox) and v_.parentWidget().objectName() != "resultCard" and v_.spacing() != 0:
            v_.setSpacing(ROW_GAP)
    for fl in root.findChildren(QFormLayout):
        fl.setVerticalSpacing(ROW_GAP)
        fl.setHorizontalSpacing(FORM_GAP)
        for r in range(fl.rowCount()):
            it = item_at(fl, r, QFormLayout.SpanningRole)
            if it is not None and isinstance(it.widget(), QPushButton):
                it.widget().setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    from elucida.app.i18n import T
    for lay in root.findChildren(QHBoxLayout):                # Listenknöpfe in allen Tabs gleich wie list_button:
        ws = [item_at(lay, i).widget() for i in range(lay.count())]   # Plus, Pfeile als Symbol, Papierkorb
        ws = [x for x in ws if x is not None]
        if not all(isinstance(x, QPushButton) for x in ws) or not any(x.text() == T("remove") for x in ws):
            continue                                          # nur reine Knopfreihen über Listen, keine Dateizeilen
        if any(x.text() in ("↑", "↓") or (not x.text() and not x.icon().isNull()) for x in ws) and not lay.property("grid"):
            _strip_stretch(lay)                               # mit Pfeilen: Textknöpfe teilen sich die Breite, Pfeile quadratisch
            lay.setSpacing(8)
            for x in ws:
                if x.text() not in ("", "↑", "↓"):
                    x.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    lay.setStretchFactor(x, 1)
        ws = [x for x in ws if x.icon().isNull()]
        for x in ws:
            if x.text() in ("↑", "↓"):
                key = "move_up" if x.text() == "↑" else "move_down"
                x.setText("")
                x.setIcon(icon(key))
                x.setToolTip(x.toolTip() or T(key))
            elif x.text() == T("remove"):
                x.setIcon(icon("trash"))
            elif x.text().rstrip().endswith(("…", "...")):
                x.setIcon(icon("add"))
    for b in root.findChildren(QPushButton):
        if not b.text() and not b.icon().isNull():
            b.setFixedWidth(34)
    for x in root.findChildren(QAbstractSpinBox) + root.findChildren(QComboBox):
        x.setFocusPolicy(Qt.StrongFocus)                        # siehe _WheelGuard
    # Raster je Karte: alle Zahlenfelder gleich breit (FIELD_W), zweite Werte einer Zeile („[5] Ränder [5 %]“) in einer
    # gemeinsamen Spalte (Beschriftungen davor je Formular gleich breit), Text/Listen bis zum rechten Rand.
    from PySide6.QtWidgets import QCheckBox
    for sp in root.findChildren(QAbstractSpinBox):
        if type(sp.property("fieldw")) is int:                # schon im Raster (zweiter Aufruf von tidy): bleibt
            continue
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
            it = item_at(fl, r, QFormLayout.FieldRole) or item_at(fl, r, QFormLayout.SpanningRole)
            lay = it.layout() if it is not None else None
            if not isinstance(lay, QHBoxLayout):
                continue
            ws = [item_at(lay, i).widget() for i in range(lay.count()) if item_at(lay, i).widget() is not None]
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
        labels = [item_at(fl, r, QFormLayout.LabelRole).widget() for r in range(fl.rowCount())
                  if item_at(fl, r, QFormLayout.LabelRole) is not None]
        lab_w = max((lb.minimumWidth() or lb.sizeHint().width() for lb in labels if lb is not None), default=0)
        for r in range(fl.rowCount()):
            it = item_at(fl, r, QFormLayout.SpanningRole)
            lay = it.layout() if it is not None else None
            if not isinstance(lay, QHBoxLayout) or not lab_w or lay.count() < 2:
                continue
            first, second = item_at(lay, 0).widget(), item_at(lay, 1).widget()
            if isinstance(first, QCheckBox) and isinstance(second, QAbstractSpinBox):
                lay.setSpacing(8)                             # -1 (Stil-Standard) verschob den Wert um 1 px
                first.setMinimumWidth(LABEL_W + fl.horizontalSpacing() - lay.spacing())
                if lay.count() > 2 and not lay.property("grid"):   # drittes Element in Feld B
                    lay.setProperty("grid", True)
                    lay.insertSpacing(2, GAP_W - lay.spacing())
        # Beschriftung so hoch wie ihr Feld, Text darin mittig: Qt setzt Beschriftungen sonst mit einem festen Versatz,
        # der bei den höheren Feldern 2–3 px zu hoch liegt
        for r in range(fl.rowCount()):
            li, fi = item_at(fl, r, QFormLayout.LabelRole), item_at(fl, r, QFormLayout.FieldRole)
            if li is None or fi is None or not isinstance(li.widget(), QLabel):
                continue
            fw = fi.widget()
            parts = [fw] if fw is not None else [item_at(fi.layout(), i).widget() for i in range(fi.layout().count())]
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
            indent = LABEL_W + fl.horizontalSpacing()          # dieselbe Kante wie alle Felder (feste Beschriftungsspalte)
            room = INNER_W                                     # ganze Kartenbreite innen
            for r in range(fl.rowCount()):
                it = item_at(fl, r, QFormLayout.SpanningRole)
                if it is None:
                    continue
                if isinstance(it.widget(), QCheckBox):
                    if it.widget().sizeHint().width() + indent <= room:
                        it.widget().setStyleSheet(f"QCheckBox {{ margin-left: {indent}px; }}")
                elif isinstance(it.layout(), QHBoxLayout) and it.layout().count() > 1:
                    lay = it.layout()
                    first, second = item_at(lay, 0).widget(), item_at(lay, 1).widget()
                    if (isinstance(first, QCheckBox) and not isinstance(second, QAbstractSpinBox)
                            and lay.sizeHint().width() + indent <= room):
                        lay.setContentsMargins(indent, 0, 0, 0)
    _field_edge(root)
    _check_edge(root)
    from PySide6.QtWidgets import QLineEdit as _LE
    for x in root.findChildren(QAbstractSpinBox) + root.findChildren(QComboBox) + root.findChildren(_LE) + \
            root.findChildren(QPushButton):                   # alle Felder und Knöpfe gleich hoch (Nutzerwunsch)
        if not isinstance(x.parentWidget(), (QAbstractSpinBox, QComboBox)) and not x.property("cellcss") and \
                x.objectName() != "segBtn" and \
                x.parentWidget().objectName() != "bottomBar":   # Fußleiste, Schrittleiste: eigene Höhe (Stylesheet)
            x.setFixedHeight(CONTROL_H)
    from PySide6.QtWidgets import QTableWidget
    for t in root.findChildren(QTableWidget):                # Zellen und Kästchen mittig (alle Tabellen)
        if not isinstance(t.itemDelegate(), _CellDelegate):
            t.setItemDelegate(_CellDelegate(t))
        if not t.property("narrowcols"):                      # (Tabellen mit einem schmalen Streifen als Spalte ausgenommen)
            t.horizontalHeader().setMinimumSectionSize(44)    # Luft um die Häkchen, in allen Tabellen gleich
        t.setShowGrid(False)                                  # Zeilenlinien zeichnet _CellDelegate
        t.setWordWrap(False)                                  # eine Zeile je Eintrag: zu lange Texte enden mit „…“
        rich_header(t)                                        # Köpfe mit Formelzeichen (Eₚₐ [V], R²) wie im Satz
        check_columns(t)
        t.verticalHeader().setDefaultSectionSize(CHECK_ROW_H)
    _choose_rows(root)
    _first_text(root)
    sci_widgets(root)                                         # auch in Knöpfen, Chips und Auswahllisten
    _wide_fields(root)
    for fl in root.findChildren(QFormLayout):                 # Beschriftungen aller Formulare gedämpft (überall gleich)
        for r in range(fl.rowCount()):
            it = item_at(fl, r, QFormLayout.LabelRole)
            lb = it.widget() if it is not None else None
            if isinstance(lb, QLabel) and not lb.property("formlabel"):
                lb.setProperty("formlabel", True)
                lb.style().unpolish(lb)
                lb.style().polish(lb)
    for lb in root.findChildren(QLabel):                      # Beschriftungen: Größen kursiv, Indizes tief
        if lb.objectName() not in ("chainStep", "chainArrow", "kpi", "cardTitle") and not lb.property("plaintext"):
            sci_label(lb)
    for h in root.findChildren(HintLabel):                    # leere Hinweise ohne Zeile
        h.sync()
    from PySide6.QtWidgets import QGroupBox as _GB
    for lb in root.findChildren(QLabel):                      # Erklärtexte mittig (Nutzerwunsch), auch verborgene
        if lb.property("plaintext"):                          # Text zum Lesen und Kopieren (SI-Text): linksbündig
            continue
        if isinstance(lb, HintLabel):
            lb.setProperty("centered", True)
            lb.sync_align()
        elif lb.objectName() == "cardHint" or HINT_CSS in (lb.styleSheet() or ""):
            lb.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
    for lay in root.findChildren(QHBoxLayout):                # Knopfreihen in Karten: gleich breit über die Karte
        pw = lay.parentWidget()
        ws = [item_at(lay, i).widget() for i in range(lay.count()) if item_at(lay, i).widget() is not None]
        if (isinstance(pw, _GB) and pw.objectName() != "resultCard"       # Ergebnisseite: Knöpfe rechts, natürliche Breite
                and 2 <= len(ws) <= 4 and all(isinstance(x, QPushButton) and x.text() for x in ws)
                and not any(x.property("accent") for x in ws) and not lay.property("grid")):
            _strip_stretch(lay)
            for x in ws:
                x.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                lay.setStretchFactor(x, 1)
    for lay in root.findChildren(QHBoxLayout):
        items = [item_at(lay, i) for i in range(lay.count())]
        if not lay.property("grid") and any(isinstance(it.widget(), (QLabel, QCheckBox)) for it in items[1:]):   # Beschriftung nicht ankleben
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
            fw = obj.property("fieldw")
            if fw:                                              # Rasterbreite nach dem Stylesheet erneut festsetzen
                obj.setFixedWidth(fw if isinstance(fw, int) and not isinstance(fw, bool) else FIELD_W)
        elif (t == QEvent.Polish and isinstance(obj, QDialog) and not isinstance(obj, (QMessageBox, QFileDialog))
              and obj.layout() is not None):
            obj.layout().setContentsMargins(16, 16, 16, 16)
            for fl in obj.findChildren(QFormLayout):            # Zeilenabstände wie in den Spalten (gleichmäßig, Nutzerwunsch)
                fl.setVerticalSpacing(ROW_GAP)
                fl.setHorizontalSpacing(FORM_GAP)
        elif t == QEvent.Wheel and self._inner_scroll(obj, ev):
            return True
        elif t == QEvent.Wheel and isinstance(obj, (QAbstractSpinBox, QComboBox)) and not obj.hasFocus():
            p = obj.parentWidget()
            while p is not None and not isinstance(p, QScrollArea):
                p = p.parentWidget()
            if p is not None:
                QApplication.sendEvent(p.verticalScrollBar(), ev)
                return True
        return False


def _inner_scroll(self, obj, ev):
    """Mausrad über einer Tabelle, Liste oder einem Textfeld in einer scrollbaren Spalte: das Feld scrollt, und an seinem
    Ende bleibt die Spalte stehen (Nutzerwunsch 2026-11-11; Qt reicht das Rad sonst an die Spalte weiter). Felder ohne
    eigene Bildlaufleiste lassen die Spalte wie bisher scrollen."""
    from PySide6.QtWidgets import QAbstractScrollArea
    area = obj.parentWidget() if isinstance(obj, QWidget) else None
    if not isinstance(area, QAbstractScrollArea) or isinstance(area, QScrollArea) or area.viewport() is not obj:
        return False
    bar = area.verticalScrollBar() if abs(ev.angleDelta().y()) >= abs(ev.angleDelta().x()) else area.horizontalScrollBar()
    if bar.maximum() <= bar.minimum():
        return False
    p = area.parentWidget()
    while p is not None and not isinstance(p, QScrollArea):
        p = p.parentWidget()
    if p is None:
        return False
    QApplication.sendEvent(bar, ev)
    return True


_WheelGuard._inner_scroll = _inner_scroll


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
        splitter.setHandleWidth(1)                            # Trennlinie zwischen Eingaben und Ergebnis (Entwurf)
        splitter.setObjectName("tabSplit")
        self.fit()

    def needed(self):
        gutter = self.scroll.verticalScrollBar().sizeHint().width() + 4
        w = max(self.floor - gutter, self.content.minimumSizeHint().width(),
                (self.bar.minimumSizeHint().width() - gutter) if self.bar is not None else 0)
        return w + gutter

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
        need = self.needed()
        self.column.setFixedWidth(need)
        # Inhalt immer gleich breit: mit und ohne Bildlaufleiste steht die rechte Kante in allen Tabs gleich (Nutzerwunsch)
        self.content.setFixedWidth(need - self.scroll.verticalScrollBar().sizeHint().width() - 4)


def fit_column(content, scroll, bar, column, splitter):
    return ColumnFit(content, scroll, bar, column, splitter)


# ---------------------------------------------------------------------------- Karten einklappen / Zeilen verschieben
def _row_of(form, w):
    """Zeile eines QFormLayout, deren Feld das Widget w ist oder enthält (Feld als Layout) -> Index oder -1."""
    for r in range(form.rowCount()):
        for role in (QFormLayout.FieldRole, QFormLayout.SpanningRole):
            it = item_at(form, r, role)
            if it is None:
                continue
            if it.widget() is w:
                return r
            lay = it.layout()
            if lay is not None and any(item_at(lay, i).widget() is w for i in range(lay.count())):
                return r
    return -1


def _move_row(src, r, dst):
    """Zeile r aus dem QFormLayout src ans Ende von dst (Beschriftung und Feld bleiben dieselben Objekte)."""
    lw, fw = take_row(src, r)
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
                    nl.addWidget(drop_taken(it))
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
        l_, t_, r_, b_ = CARD_MARGINS
        lay.setContentsMargins(l_, t_ if self.opened else 0, r_, b_ if self.opened else 0)
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
        mark = f" ({T('adv_changed')})" if self.changed is not None and self.changed() else ""
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
        if elucida.octet_enabled():
            app.focusWindowChanged.connect(_guard_dialog)
        else:
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
    p = cache_dir / f"down_on_{_mode}.png"                   # Pfeil auf dem blauen Hauptknopf
    _render("down", c["on_accent"], 48, stroke=2.6).save(str(p))
    arrows["down_on"] = p.as_posix()
    app.setStyleSheet(stylesheet(c, arrows))
    return _mode


def _mix(a, b, t):
    """Farbe a mit Anteil t über b (Hex)."""
    ca, cb = QColor(a), QColor(b)
    return QColor(*(round(x * t + y * (1 - t)) for x, y in ((ca.red(), cb.red()), (ca.green(), cb.green()),
                                                             (ca.blue(), cb.blue())))).name()


def stylesheet(c, a):
    return f"""
QFrame#card {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px; }}
QLabel#cardTitle {{ font-weight: 600; }}
QLabel[formlabel="true"] {{ color: {c['text2']}; }}
QLabel#valueStrong {{ font-weight: 600; }}                     /* Angabe aus der Verbindung (Summenformel, Molmasse): gut sichtbar */
QGroupBox QLabel#valueStrong {{ font-weight: 600; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {c['field']}; border: 1px solid {c['border']}; border-radius: 7px;
    padding: 3px 10px; min-height: 18px; selection-background-color: {c['accent']}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {c['accent']}; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {c['disabled']}; background: {c['alt']}; }}
QSpinBox, QDoubleSpinBox {{ padding-top: 2px; padding-bottom: 1px; padding-right: 24px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right;
    width: 24px; border: none; background: transparent; }}
QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right;
    width: 24px; border: none; background: transparent; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{a['up']}"); width: 11px; height: 11px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{a['down']}"); width: 11px; height: 11px; }}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{ image: url("{a['up_dis']}"); }}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{ image: url("{a['down_dis']}"); }}
QComboBox {{ padding-left: 12px; }}
QComboBox::drop-down {{ subcontrol-origin: border; subcontrol-position: center right; width: 24px; border: none; }}
QComboBox::down-arrow {{ image: url("{a['down']}"); width: 11px; height: 11px; }}
QComboBox::down-arrow:disabled {{ image: url("{a['down_dis']}"); }}
QComboBox QAbstractItemView {{ background: {c['card']}; border: 1px solid {c['border']};
    selection-background-color: {c['accent']}; selection-color: {c['on_accent']}; }}
QPushButton {{ background: {c['button']}; border: 1px solid {c['border']}; border-radius: 8px;
    padding: 5px 13px; min-height: 18px; font-weight: 500; }}
QPushButton:hover {{ background: {c['hover']}; border-color: {c['border_strong']}; }}
QPushButton:pressed {{ background: {c['border']}; }}
QPushButton:disabled {{ color: {c['disabled']}; background: {c['alt']}; }}
QPushButton[accent="true"] {{ background: {c['accent']}; color: {c['on_accent']}; border-color: {c['accent']};
    font-weight: 600; }}
QPushButton[accent="true"]:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QDialog QPushButton:default:enabled {{ background: {c['accent']}; color: {c['on_accent']}; border-color: {c['accent']};
    font-weight: 600; }}
QDialog QPushButton:default:enabled:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: 12px; background: {c['window']}; top: -1px; }}
QTabWidget#resultTabs::pane {{ border: none; top: 0; }}
QTabWidget#resultTabs::tab-bar {{ left: 14px; }}
/* Reiter mittig auf der Höhe der Schrittleiste links (34 hoch) und Seite darunter auf der Höhe der ersten Karte */
QTabWidget#resultTabs > QTabBar::tab {{ margin: 3px 2px 13px 0; }}
QTabBar::tab {{ background: transparent; color: {c['text2']}; border: 1px solid transparent; border-radius: 6px;
    padding: 0 12px; margin: 3px 1px; min-height: 26px; max-height: 26px; font-weight: 500; }}
QTabBar::tab:selected {{ background: {c['sel']}; color: {c['text']}; font-weight: 600; }}
QTabBar::tab:hover:!selected {{ background: {c['hover']}; color: {c['text']}; }}
QTableWidget, QTableView, QListWidget, QTreeWidget, QPlainTextEdit, QTextEdit {{
    background: {c['field']}; border: 1px solid {c['border']}; border-radius: 8px; gridline-color: {c['border']};
    selection-background-color: {c['accent']}; selection-color: {c['on_accent']}; }}
QHeaderView::section {{ background: {c['card']}; color: {c['text2']}; border: none;
    border-bottom: 1px solid {c['border']}; padding: 4px 6px; }}        /* kein Gitter, auch nicht im Kopf */
QGroupBox {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px;
    margin-top: 0; padding: 2.1em 4px 4px 4px; }}
QGroupBox::title {{ subcontrol-origin: padding; subcontrol-position: top left; left: 12px; top: 9px;
    font-weight: bold; }}
QGroupBox::title:disabled {{ color: {c['disabled']}; }}
QCheckBox::indicator, QAbstractItemView::indicator, QGroupBox::indicator {{ width: 16px; height: 16px;
    border: 1px solid {c['check_border']}; border-radius: 5px; background: {c['field']}; }}
QCheckBox::indicator:hover, QAbstractItemView::indicator:hover {{ border-color: {c['accent']}; }}
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked, QGroupBox::indicator:checked {{
    background: {c['accent']}; border-color: {c['accent']}; image: url("{a['check']}"); }}
QCheckBox::indicator:indeterminate, QAbstractItemView::indicator:indeterminate {{
    background: {c['accent']}; border-color: {c['accent']}; image: url("{a['dash']}"); }}
QCheckBox::indicator:disabled, QAbstractItemView::indicator:disabled {{ background: {c['alt']};
    border-color: {c['border_strong']}; }}
QCheckBox::indicator:checked:disabled, QAbstractItemView::indicator:checked:disabled {{
    background: {c['disabled']}; border-color: {c['disabled']}; image: url("{a['check_dis']}"); }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {c['border_strong']}; border-radius: 3px; }}
QScrollBar::handle:vertical {{ min-height: 32px; }}
QScrollBar::handle:horizontal {{ min-width: 32px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background: transparent; }}
QSplitter#tabSplit::handle {{ background: {c['border']}; }}
QToolTip {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 4px; }}
QToolBar {{ background: {c['window']}; border: none; border-bottom: 1px solid {c['border']};
    padding: 9px 14px; spacing: 6px; }}
QToolBar QToolButton {{ border: 1px solid transparent; border-radius: 7px; padding: 0 9px; min-height: 30px; max-height: 30px;
    min-width: 12px; font-size: 13px; font-weight: 500; color: {c['text2']}; }}
QToolBar QToolButton:hover {{ color: {c['text']}; }}
QToolBar QToolButton#barTool {{ background: {c['button']}; border-color: {c['border']}; border-radius: 8px; padding: 0 13px;
    min-height: {BAR_H - 2}px; max-height: {BAR_H - 2}px; color: {c['text']}; }}
QPushButton#crumb {{ background: transparent; border: none; border-radius: 7px; padding: 0 8px; color: {c['text2']}; min-height: 30px; max-height: 30px; }}
QPushButton#crumb:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#crumbNow {{ background: transparent; border: none; border-radius: 7px; padding: 0 8px; font-weight: 600; min-height: 30px; max-height: 30px; }}
QLabel#crumbSep {{ color: {c['text2']}; font-size: 13px; min-height: 30px; max-height: 30px; }}
QToolBar QToolButton:hover {{ background: {c['hover']}; border-color: {c['border']}; }}
QToolBar QToolButton:pressed {{ background: {c['border']}; }}
QToolBar::separator {{ background: {c['border']}; width: 1px; margin: 5px 6px; }}
QLabel#toast {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QWidget#recentRow {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px; }}
QWidget#recentRow:hover {{ border-color: {c['border_strong']}; }}
QLabel#recentMono {{ background: {c['alt']}; color: {c['text2']}; border: 1px solid {c['border']}; border-radius: 8px;
    font-weight: bold; font-size: 18px; }}
QLabel#recentThumb, QFrame#recentThumb {{ background: #ffffff; border: 1px solid #dddddd; border-radius: 8px; }}
QLabel#recentTitle {{ font-size: 15px; font-weight: bold; background: transparent; }}
QLabel#recentNote {{ color: {c['text2']}; font-size: 14px; font-style: italic; background: transparent; }}
QLabel#recentSub, QLabel#recentWhen {{ color: {c['text2']}; background: transparent; }}
QLabel#recentBadge {{ color: {c['text2']}; background: {c['hover']}; border-radius: 5px; padding: 0 6px; font-size: 11px; }}
QLabel#recentHead {{ font-size: 14px; }}
QFrame#bottomBar {{ background: {c['window']}; border-top: 1px solid {c['border']}; }}
QFrame#bottomBar QPushButton {{ min-height: {BAR_H - 2}px; max-height: {BAR_H - 2}px; padding: 0 13px; }}
QFrame#bottomBar QPushButton#ghost {{ min-height: {BAR_H}px; max-height: {BAR_H}px; padding: 0 10px; }}   /* ohne Rahmen: volle Höhe */
QGroupBox {{ font-weight: 600; padding: {CARD_TITLE_H}px 4px 0 4px; }}
QGroupBox::title {{ left: 14px; top: 12px; }}                 /* bündig mit dem Karteninhalt (CARD_PAD) */
QGroupBox#resultCard {{ padding: 4px; }}                    /* mit Layout-Rand 12: ringsum 17 */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton {{ min-height: 20px; }}   /* Knopf frei: 20 + 2·5 + 2 = CONTROL_H */
QDialog QLineEdit, QDialog QComboBox {{ min-height: 24px; }}    /* Dialoge laufen nicht durch tidy: Felder so hoch wie Knöpfe */
QDialog QSpinBox, QDialog QDoubleSpinBox {{ min-height: 27px; }}
QGroupBox QWidget {{ font-weight: normal; }}
QGroupBox QPushButton {{ font-weight: 500; }}
QGroupBox QPushButton[accent="true"] {{ font-weight: 600; }}
QGroupBox QGroupBox {{ font-weight: 600; }}
QLabel#cardHint {{ color: {c['text2']}; background: {c['card']}; border: 1px solid {c['border']};
    border-radius: 12px; padding: 10px 14px; }}
QToolButton[accent="true"], QToolBar QToolButton#barTool[accent="true"] {{ background: {c['accent']}; color: {c['on_accent']};
    border-color: {c['accent']}; font-weight: 600; }}
QToolBar QToolButton#barTool[accent="true"]:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QToolButton[accent="true"]:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QFrame#navBar {{ background: {c['window']}; border-bottom: 1px solid {c['border']}; }}
QLabel#navGroup {{ color: {c['text2']}; font-size: 10px; font-weight: 600; padding: 0 3px; }}
QPushButton#navTab {{ background: transparent; border: 1px solid transparent; border-radius: 7px; padding: 0 9px;
    color: {c['text2']}; min-height: 28px; max-height: 28px; font-weight: 500; }}
QPushButton#navTab[hasData="true"] {{ color: {c['text']}; }}
QPushButton#navTab:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#navTab:checked {{ background: {c['sel']}; color: {c['text']}; font-weight: 600; }}
QFrame#navSep {{ background: {c['border']}; }}
QFrame#sideBar {{ background: {c['side']}; border: none; border-right: 1px solid {c['border']}; }}
QLabel#sideCap {{ color: {c['text2']}; font-size: 11px; font-weight: bold; padding: 0 10px 3px 10px; background: transparent; }}
QLabel#sideBrand {{ font-size: 15px; font-weight: bold; background: transparent; }}
QPushButton#sideItem {{ background: transparent; border: none; border-radius: 7px; padding: 0; min-height: 34px; }}
QPushButton#sideItem:hover {{ background: {c['hover']}; }}
QPushButton#sideItem:checked {{ background: {c['sel']}; }}
QPushButton#sideItem QLabel {{ background: transparent; }}
QLabel#sideCount {{ color: {c['text2']}; }}
QLabel#pageTitle {{ font-size: 26px; font-weight: bold; }}
QLabel#pageSub {{ color: {c['text2']}; font-size: 14px; }}
QFrame#seg {{ background: {c['field']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QPushButton#segBtn {{ background: transparent; border: none; border-radius: 6px; padding: 0 12px; color: {c['text2']}; min-height: 28px; max-height: 28px; }}
QPushButton#segBtn:checked {{ background: {c['hover']}; color: {c['text']}; font-weight: 600; }}
QCheckBox::indicator {{ background: {c['button']}; border: 1px solid {c['border_strong']}; }}
QCheckBox[chip="true"] {{ spacing: 0; padding: 0 11px; min-height: 24px; max-height: 24px; border-radius: 13px;
    border: 1px solid {c['border_strong']}; color: {c['text2']}; background: transparent; }}
QCheckBox[chip="true"][tight="1"] {{ padding: 0 7px; }}
QCheckBox[chip="true"][tight="2"] {{ padding: 0 4px; }}
QCheckBox[chip="true"]::indicator {{ width: 0; height: 0; border: none; margin: 0; background: transparent; image: none; }}
QCheckBox[chip="true"]:hover {{ border-color: {c['accent']}; color: {c['text']}; }}
QCheckBox[chip="true"]:checked {{ background: {_mix(c['accent'], c['card'], 0.16)}; border-color: {c['accent']}; color: {c['text']}; }}
QCheckBox[chip="true"]:disabled {{ color: {c['disabled']}; border-color: {c['border']}; background: transparent; }}
QLabel#chainStep {{ padding: 0 10px; min-height: 24px; max-height: 24px; border-radius: 13px;
    border: 1px solid {c['border']}; color: {c['disabled']}; background: transparent; }}
QLabel#chainStep[on="true"] {{ border-color: {c['border_strong']}; color: {c['text']}; background: {c['alt']}; }}
QLabel#chainStep[tight="1"] {{ padding: 0 6px; }}
QLabel#chainStep[tight="2"] {{ padding: 0 5px; font-size: 11px; }}
QLabel#chainArrow {{ color: {c['text2']}; min-height: 24px; max-height: 24px; }}
QLabel#kpi {{ padding: 0 10px; min-height: 24px; max-height: 24px; border-radius: 8px; border: 1px solid {c['border']};
    background: {c['card']}; color: {c['text2']}; }}
QLineEdit#searchField {{ min-height: {BAR_H - 2}px; max-height: {BAR_H - 2}px; padding: 0 12px; border-radius: 8px; }}
QPushButton#barBtn {{ min-height: {BAR_H - 2}px; max-height: {BAR_H - 2}px; padding: 0 13px; border-radius: 8px; font-weight: 500; }}
QPushButton#newBtn {{ min-height: {BAR_H - 2}px; max-height: {BAR_H - 2}px; padding: 0 28px 0 13px; border-radius: 8px; font-weight: 600; }}
QPushButton#newBtn::menu-indicator {{ image: url("{a['down']}"); subcontrol-origin: padding; subcontrol-position: center right; right: 9px; width: 11px; height: 11px; }}
QPushButton#newBtn[accent="true"]::menu-indicator {{ image: url("{a['down_on']}"); }}
QFrame#panelHead {{ border: none; border-bottom: 1px solid {c['border']}; border-radius: 0; background: transparent; }}
QFrame#panelFoot {{ border: none; border-top: 1px solid {c['border']}; border-radius: 0; background: transparent; }}
QFrame#jobRow {{ border: none; border-bottom: 1px solid {c['border']}; background: transparent; }}
QPushButton#ghost {{ background: transparent; border: none; border-radius: 7px; color: {c['text2']}; padding: 0 10px; min-height: 30px; max-height: 30px; }}
QPushButton#ghost:hover {{ background: {c['hover']}; color: {c['text']}; }}
QPushButton#addCard {{ background: transparent; border: 1px dashed {c['border_strong']}; border-radius: 12px; color: {c['text2']}; }}
QPushButton#addCard:hover {{ background: {c['card']}; color: {c['text']}; }}
QPushButton#addCard QLabel {{ background: transparent; }}
QWidget#matrixPanel, QFrame#matrixPanel {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px; }}
QWidget#matrixRow {{ background: transparent; border: none; border-top: 1px solid {c['border']}; border-radius: 0; }}
QWidget#matrixRow:hover {{ background: {c['hover']}; }}
QLabel#cardThumb {{ background: #ffffff; border: none; border-bottom: 1px solid #dddddd;
    border-top-left-radius: 11px; border-top-right-radius: 11px; }}
QLabel#cardName {{ font-size: 15px; font-weight: bold; background: transparent; }}
QLabel#statusOk {{ color: {c['ok']}; font-size: 12px; font-weight: bold; background: transparent; }}
QLabel#statusOpen, QLabel#recentHint {{ color: {c['text2']}; font-size: 12px; background: transparent; }}
QProgressBar#pubProgress {{ background: {c['border']}; border: none; border-radius: 3px; }}
QProgressBar#pubProgress::chunk {{ background: {c['ok']}; border-radius: 3px; }}
"""
