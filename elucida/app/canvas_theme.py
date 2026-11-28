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
        c = rgb[coloured].astype(np.int32)       # int32: in int16 lief die Helligkeitssumme ab 128 über (weiße Säume)
        hi, lo = c.max(-1), c.min(-1)
        c += (255 - hi - lo)[:, None]
        luma = (54 * c[:, 0] + 183 * c[:, 1] + 19 * c[:, 2]) >> 8
        dim = (luma < MIN_LUMA) & (hi - lo > 32)
        t = (MIN_LUMA - luma[dim]) / (255.0 - luma[dim])
        c[dim] += ((255 - c[dim]) * t[:, None]).astype(np.int32)
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


def _photo_boxes(effect, source):
    """Fotos (Achsen mit `_photo`, core.uvvis._images) im Bild des Widgets: [(Zeilen, Spalten, Original-RGB, Deckkraft
    0..1)]. Die Abbildung bleibt unverändert; nur die Bildschirmpixel werden danach zurückgesetzt."""
    widget = effect._widget() if getattr(effect, "_widget", None) else None
    fig = getattr(widget, "figure", None)
    if fig is None:
        return []
    axes = [a for a in fig.axes if getattr(a, "_photo", None) is not None and a.get_visible() and a.images]
    if not axes:
        return []
    img = source.convertToFormat(QImage.Format_ARGB32)
    view = np.frombuffer(img.bits(), np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)
    H, W = img.height(), img.width()
    out = []
    for a in axes:
        bb = a.bbox                                        # Pixel der Abbildung = Gerätepixel (dpi mit devicePixelRatio)
        mask = a._photo if isinstance(a._photo, np.ndarray) else np.asarray(a.images[0].get_array())[..., 3]
        r0, r1 = max(0, int(round(H - bb.y1))), min(H, int(round(H - bb.y0)))
        c0, c1 = max(0, int(round(bb.x0))), min(W, int(round(bb.x1)))
        if r1 <= r0 or c1 <= c0 or bb.width <= 0 or bb.height <= 0:
            continue
        ys = ((np.arange(r0, r1) + 0.5 - (H - bb.y1)) * mask.shape[0] / bb.height).astype(int).clip(0, mask.shape[0] - 1)
        xs = ((np.arange(c0, c1) + 0.5 - bb.x0) * mask.shape[1] / bb.width).astype(int).clip(0, mask.shape[1] - 1)
        out.append((slice(r0, r1), slice(c0, c1), view[r0:r1, c0:c1, :3].astype(np.int32),
                    mask[ys][:, xs].astype(np.float32) / 255))
    return out


def _keep_photos(picture, photos):
    """Fotopixel wie im hellen Bild; durchsichtige Teile (freigestellt) zeigen das dunkle Bild darunter: hell = a·Foto +
    (1−a)·Grund, dunkel(Grund) = 255 − Grund (grau) -> hell + (1−a)·(2·dunkel − 255)."""
    view = np.frombuffer(picture.bits(), np.uint8).reshape(picture.height(), picture.bytesPerLine() // 4, 4)
    for rows, cols, light, alpha in photos:
        dark = view[rows, cols, :3].astype(np.int32)
        view[rows, cols, :3] = np.clip(light + (1 - alpha[..., None]) * (2 * dark - 255), 0, 255).astype(np.uint8)


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
        source = pixmap.toImage()
        ratio = source.devicePixelRatio()                  # vor dark_image (setzt es bei opaque auf 1)
        area = QRectF(offset.x(), offset.y(), source.width() / ratio, source.height() / ratio)
        photos = _photo_boxes(self, source)
        picture = dark_image(source, self.fast, self.opaque)
        # shortcut: in halber Auflösung (Drehen; nur X-Ray/NMR, ohne Fotos) bleiben Fotos umgerechnet, sonst Kästen skalieren
        if photos and picture.size() == source.size():
            _keep_photos(picture, photos)
        painter.setWorldTransform(QTransform())
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        # Zielfläche aus dem Quellbild, nicht aus devicePixelRatio des halben Bilds: bei 100 % (Verhältnis 0,5) zeichnete
        # Qt es in halber Größe links oben (Windows-Bericht 1.5.0)
        if self.opaque:                                    # Fläche zuerst schwarz, einen Punkt über den Rand: deckt das Bild
            painter.fillRect(area.adjusted(0, 0, 1, 1), Qt.black)   # eine Zeile nicht (Rundung), bleibt nichts Helles stehen
        painter.drawImage(area, picture)


def register(widget):
    if elucida.octet_enabled():
        effect = CanvasInvert()                            # setGraphicsEffect übernimmt den Besitz
        from PySide6.QtWidgets import QLabel
        effect.opaque = not isinstance(widget, QLabel)
        widget.setGraphicsEffect(effect)
        widget._canvas_invert = effect
        effect._widget = weakref.ref(widget)               # Abbildung des Widgets: Fotos bleiben unverändert
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
