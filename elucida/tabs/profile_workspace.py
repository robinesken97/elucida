"""Display zoom + scrolling independent of physical export dimensions."""
from elucida.app.i18n import T
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QComboBox, QLabel


class ProfileWorkspace(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        row.addWidget(QLabel(T('rp_view_zoom')))
        self.zoom = QComboBox()
        for x in (100, 125, 150, 200, 300): self.zoom.addItem(f"{x} %", x/100)
        row.addWidget(self.zoom); row.addStretch(1); v.addLayout(row)
        self.scroll = QScrollArea()
        self.fit_timer = QTimer(self, singleShot=True, interval=0)
        self.fit_timer.timeout.connect(self.fit)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(host)
        self.scroll.viewport().installEventFilter(self)
        v.addWidget(self.scroll, 1)
        self.zoom.currentIndexChanged.connect(self.fit)
        self.setMinimumHeight(280)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.fit_timer.start()
        return super().eventFilter(obj, event)

    def fit(self, *_):
        z = self.zoom.currentData() or 1.
        vp = self.scroll.viewport()
        self.host.setMinimumSize(max(200, int(vp.width()*z)-2), max(150, int(vp.height()*z)-2))
        self.host.fit()
