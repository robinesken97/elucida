"""Erscheinungsbild: Qt-Stil Fusion mit eigener Palette (hell/dunkel), zentralem Stylesheet und Symbolen.

Fusion sieht auf Windows, macOS und Linux gleich aus. Die Abbildungen (matplotlib) sind davon nicht betroffen.
Symbole sind kleine SVGs (Strichzeichnungen), werden in der Textfarbe gerendert und als PNG für das Stylesheet
abgelegt (PNG braucht kein Qt-Bildformat-Plugin)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QFormLayout, QFrame, QHBoxLayout, QLabel, QSizePolicy,
                               QPushButton, QStyleFactory, QVBoxLayout, QWidget)

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
    "data": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
    "compound": '<path d="M12 3l7.8 4.5v9L12 21l-7.8-4.5v-9z"/><circle cx="12" cy="12" r="3.6"/>',
    "eval": '<path d="M4 4v16h16"/><path d="M6.5 17.5 19 6"/><circle cx="9" cy="14.6" r="1.1"/>'
            '<circle cx="13" cy="11.3" r="1.1"/><circle cx="16.6" cy="8.1" r="1.1"/>',
    "plot": '<path d="M4 4v16h16"/><path d="M6 18c2.5 0 3-10 5.5-10S14 18 17 18c1.2 0 2-1 2.5-2"/>',
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
}

HINT_CSS = "color: gray;"            # Hinweistexte
WARN_CSS = "color: #d9534f;"         # Warnungen (fehlende Molmasse, Farbe unvollständig)


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
    for lb in labels:
        lb.setMinimumWidth(width)
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
    from uvvis_i18n import T
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


def card(title, icon_name=None):
    """Gruppe als Karte mit Symbol im Titel. Gibt (Karte, Inhalts-Widget) zurück."""
    frame = QFrame(objectName="card")
    v = QVBoxLayout(frame)
    v.setContentsMargins(12, 10, 12, 10)
    v.setSpacing(6)
    head = QHBoxLayout()
    head.setSpacing(6)
    if icon_name:
        lb = QLabel(objectName="cardIcon")
        lb.setPixmap(pixmap(icon_name, 16))
        head.addWidget(lb)
    t = QLabel(title, objectName="cardTitle")
    head.addWidget(t)
    head.addStretch(1)
    v.addLayout(head)
    body = QWidget()
    v.addWidget(body)
    return frame, body


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
    app.setStyleSheet(stylesheet(c, arrows))
    return _mode


def stylesheet(c, a):
    return f"""
QFrame#card {{ background: {c['card']}; border: 1px solid {c['border']}; border-radius: 8px; }}
QLabel#cardTitle {{ font-weight: bold; }}
QLabel[formlabel="true"] {{ color: {c['text2']}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {c['field']}; border: 1px solid {c['border']}; border-radius: 5px;
    padding: 3px 6px; min-height: 18px; selection-background-color: {c['accent']}; }}
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
QFrame#bottomBar {{ background: {c['window']}; border-top: 1px solid {c['border']}; }}
"""
