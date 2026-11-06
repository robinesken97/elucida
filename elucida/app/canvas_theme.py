"""Screen-only inversion. Never mutate figures, pixmaps or export data."""
import elucida
import os
import weakref
import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QGraphicsEffect

_dark = False
_effects = weakref.WeakSet()

MIN_LUMA = 110      # dunkle gesättigte Farben auf Schwarz (reines Blau) sonst kaum lesbar


def dark_pixels(rgb):
    """Screen colours for a black canvas: mirror HSL lightness, keep the hue (red stays red, white -> #000000),
    then lift dark saturated colours. rgb: uint8 array (..., 3). Grey pixels (almost all of a plot) take the fast
    path, so rotating a molecule stays smooth."""
    out = 255 - rgb
    coloured = (rgb[..., 0] != rgb[..., 1]) | (rgb[..., 1] != rgb[..., 2])
    if coloured.any():
        c = rgb[coloured].astype(np.int16)
        hi, lo = c.max(-1), c.min(-1)
        c += (255 - hi - lo)[:, None]
        luma = (54 * c[:, 0] + 183 * c[:, 1] + 19 * c[:, 2]) >> 8
        dim = (luma < MIN_LUMA) & (hi - lo > 32)
        t = (MIN_LUMA - luma[dim]) / (255.0 - luma[dim])
        c[dim] += ((255 - c[dim]) * t[:, None]).astype(np.int16)
        out[coloured] = c
    return out


class CanvasInvert(QGraphicsEffect):
    suspended = False

    def draw(self, painter):
        offset = QPoint()
        pixmap = self.sourcePixmap(Qt.LogicalCoordinates, offset, QGraphicsEffect.NoPad)
        if pixmap.isNull():
            return
        picture = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        view = np.frombuffer(picture.bits(), np.uint8).reshape(picture.height(), picture.bytesPerLine() // 4, 4)
        view[:, :, :3] = dark_pixels(view[:, :, :3])
        inverted = QPixmap.fromImage(picture)
        inverted.setDevicePixelRatio(pixmap.devicePixelRatio())
        painter.drawPixmap(offset, inverted)


def register(widget):
    if elucida.octet_enabled():
        effect = CanvasInvert(widget)
        widget.setGraphicsEffect(effect)
        widget._canvas_invert = effect
        effect.setEnabled(_dark)
        _effects.add(effect)
    return widget


def suspend(widget, off):
    """Text statt Bild im Widget: das Theme sorgt schon für Lesbarkeit."""
    effect = getattr(widget, '_canvas_invert', None)
    if effect is not None:
        effect.suspended = off
        effect.setEnabled(_dark and not off)


def configure(dark):
    global _dark
    _dark = bool(dark)
    for effect in list(_effects):
        try:
            effect.setEnabled(_dark and not effect.suspended)
        except RuntimeError:
            _effects.discard(effect)
