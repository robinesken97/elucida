"""Screen-only inversion. Never mutate figures, pixmaps or export data."""
import elucida
import os
import weakref
import numpy as np
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QImage, QPainter
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


def dark_image(picture, half=False, opaque=False):
    """Bild für den dunklen Canvas umrechnen (neues QImage, gleiche Fläche auf dem Bildschirm). half: in halber Auflösung
    – beim Drehen, weil die Umrechnung bei voller HiDPI-Auflösung ~45–65 ms je Bild kostet (gemessen, 3000 × 2200).
    opaque: Zeichenfläche (kein Vorschaubild) – durchsichtige oder nicht gezeichnete Pixel gelten als weißes Papier und
    werden schwarz; sonst blieb dort der alte Bildschirminhalt stehen (helle Zeile am Rand der Zeichenfläche)."""
    size, ratio = picture.size(), picture.devicePixelRatio()
    if opaque and picture.hasAlphaChannel():
        flat = QImage(size, QImage.Format_RGB32)
        flat.fill(Qt.white)
        picture.setDevicePixelRatio(1.0)
        p = QPainter(flat)
        p.drawImage(0, 0, picture)
        p.end()
        picture = flat
    if half and size.width() * size.height() > 1_000_000:
        picture = picture.scaled(size.width() // 2, size.height() // 2, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        ratio = ratio * picture.width() / size.width()         # dieselbe Fläche: Pixel je Punkt halbieren sich mit
    # Farben ohne vorab eingerechnete Deckkraft umrechnen: Vorschaubilder haben durchsichtigen Grund, dessen Pixel
    # (0, 0, 0, 0) sonst zu Weiß mit Deckkraft 0 würden (ungültig, zerstörte die Bilder des Startbildschirms)
    if picture.format() not in (QImage.Format_RGB32, QImage.Format_ARGB32):
        picture = picture.convertToFormat(QImage.Format_ARGB32)
    view = np.frombuffer(picture.bits(), np.uint8).reshape(picture.height(), picture.bytesPerLine() // 4, 4)
    view[:, :, 2::-1] = dark_pixels(view[:, :, 2::-1])          # Bytefolge B, G, R, A: als R, G, B rechnen
    picture.setDevicePixelRatio(ratio)
    return picture


class CanvasInvert(QGraphicsEffect):
    suspended = False
    fast = False        # beim Drehen: in halber Auflösung umrechnen (siehe moving)
    opaque = True       # Zeichenfläche; False: Bild mit durchsichtigem Grund (QLabel, Vorschaubilder)

    def draw(self, painter):
        # In Gerätepixeln: mit logischen Koordinaten blieb am unteren Rand eine Zeile des hellen Originals stehen (Rundung
        # auf HiDPI), die beim Drehen flackerte.
        from PySide6.QtGui import QTransform
        offset = QPoint()
        pixmap = self.sourcePixmap(Qt.DeviceCoordinates, offset, QGraphicsEffect.NoPad)
        if pixmap.isNull():
            return
        picture = dark_image(pixmap.toImage(), self.fast, self.opaque)
        painter.setWorldTransform(QTransform())
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.opaque:                                    # Fläche zuerst schwarz, einen Punkt über den Rand: deckt das Bild
            ratio = picture.devicePixelRatio()             # eine Zeile nicht (Rundung), bleibt nichts Helles stehen
            painter.fillRect(QRectF(offset.x(), offset.y(), picture.width() / ratio + 1, picture.height() / ratio + 1),
                             Qt.black)
        painter.drawImage(offset, picture)


def register(widget):
    if elucida.octet_enabled():
        effect = CanvasInvert()                            # setGraphicsEffect übernimmt den Besitz
        from PySide6.QtWidgets import QLabel
        effect.opaque = not isinstance(widget, QLabel)
        widget.setGraphicsEffect(effect)
        widget._canvas_invert = effect
        effect.setEnabled(_dark)
        _effects.add(effect)
    return widget


def moving(widget, on):
    """Während im Bild gedreht wird (viele Bilder je Sekunde), rechnet der Effekt in halber Auflösung; beim Loslassen
    wieder in voller."""
    effect = getattr(widget, '_canvas_invert', None)
    if effect is not None and effect.fast != bool(on):
        effect.fast = bool(on)
        if not on:
            widget.update()


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
