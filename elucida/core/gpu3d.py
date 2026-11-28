"""3D-Orbitalbilder auf der Grafikkarte (QRhi, 1.5.0): derselbe Raycaster wie `orbitals.render`, nur für die sichtbare
Vorschau (Ziehen in voller Auflösung, Loslassen ohne Wartezeit). Alles, was auf die Platte geht (Export, SI, Word,
Kacheln, Selbsttest), rechnet weiter numpy – sonst hinge die Pixel-Basis vom Rechner ab.
Shader: `assets/shaders/orb.*` (Vulkan-GLSL), `.qsb` daraus mit `python tools/make_shaders.py`.
Ablauf: erst beim ersten 3D-Bild ein eigenes, nie gezeigtes Top-Level (WA_DontShowOnScreen, Qt.Tool) mit einem
QRhiWidget (im Hauptfenster würde Qt dessen natives Fenster neu anlegen; ganz ohne Fenster baut `grabFramebuffer` je Bild
eine neue QRhi). Danach ein Selbstcheck gegen numpy an einem kleinen Bild. Jeder Fehler -> CPU (Hintergrundrechnung).
Absturzschutz: vor Einrichtung und Selbstcheck steht `gpu/pending` in den Einstellungen; steht es beim Start noch da,
bleibt die GPU auf diesem Rechner aus, bis der Nutzer sie im Menü wieder einschaltet."""
from __future__ import annotations

import math
import sys
import time

import numpy as np

GPU_DEFAULT = True                             # Vorgabe der Einstellung „3D über die Grafikkarte“ (Robin entscheidet nach Windows)
SETTING = "ui/gpu"
PENDING = "gpu/pending"
CHECK_PX = (160, 120)                          # Selbstcheck: Bildgröße
CHECK_MEAN = 0.5                               # … mittlere Abweichung (vormultipliziert, /255) höchstens
CHECK_COVER = 0.002                            # … Anteil abweichender Deckung (Pixel mit/ohne Fläche) höchstens
LOG = print                                    # GUI ersetzt das durch ihr Protokoll

_S = {"settings": None, "force_off": False, "host": None, "w": None, "ok": None, "reason": "", "info": {}}


# ---------------------------------------------------------------------------- Schalter
def configure(settings):
    """Beim Start (MainWindow): Einstellungen merken; hängt der Marker eines abgebrochenen Starts noch, GPU aus."""
    _S["settings"] = settings
    if settings is not None and settings.value(PENDING):
        settings.setValue(SETTING, False)
        settings.remove(PENDING)
        settings.sync()
        _S["reason"] = "GPU off: the last GPU start did not finish (driver crash?); switch it on again in Format"
        LOG("3D: " + _S["reason"])


def setting_on():
    s = _S["settings"]
    v = GPU_DEFAULT if s is None else s.value(SETTING, GPU_DEFAULT)
    return str(v).lower() not in ("false", "0")


def set_setting(on):
    """Menü: Einstellung sofort speichern (nicht erst beim Beenden) und eine Protokollzeile; Einschalten versucht die
    GPU beim nächsten Bild neu."""
    s = _S["settings"]
    if s is not None:
        s.setValue(SETTING, bool(on))
        s.sync()
    if on and _S["ok"] is False:
        _S.update(ok=None, reason="")
    if not on:
        LOG("3D: CPU (switched off)")
    elif _S["ok"] and _S["reason"]:
        LOG("3D: GPU " + _S["reason"] + " (switched on)")
    else:
        LOG("3D: GPU (switched on, starts with the next 3D view)")


def wanted():
    """GPU erlaubt (Einstellung an, kein --disable-gpu, nicht im Selbsttest) und nicht gescheitert."""
    return (not _S["force_off"] and "--disable-gpu" not in sys.argv and setting_on() and _S["ok"] is not False)


def force_off(on=True):
    """Selbsttest: überall CPU (außer im eigenen Abschnitt)."""
    _S["force_off"] = on


def status():
    """(ok, Grund/Backend) für Protokoll und Selbsttest."""
    return _S["ok"], _S["reason"], dict(_S["info"])


def fail(reason):
    """GPU für diesen Lauf aus (Rückfall CPU), eine Protokollzeile."""
    if _S["ok"] is not False:
        _S.update(ok=False, reason=reason)
        LOG("3D: CPU (" + reason + ")")


# ---------------------------------------------------------------------------- Bild
def render(vol, iso, R, center, zoff, xlim, ylim, W, H, cplus, cminus, alpha=0.6, occ=None, max_layers=4,
           step_frac=0.5, budget=None, occ2=None, aa=True, cancel=None):
    """Wie `orbitals.render` (gleiche Eingaben, gleiches RGBA), gerechnet auf der GPU. Fehler -> Ausnahme."""
    from elucida.core import orbitals as ORB
    if not wanted():
        raise RuntimeError("GPU off")
    if _S["ok"] is None:
        _start()
    if max_layers > 4:
        raise ValueError("max_layers > 4")
    R = np.asarray(R, float)
    center = np.asarray(center, float)
    if iso <= 0 or W < 1 or H < 1 or not len(ORB.surface_points(vol, iso)):
        return np.zeros((H, W, 4), np.float32)
    tiles, TILE = _tiles(vol, iso, R, center, xlim, ylim, W, H, exact=aa)
    if not tiles[..., 2].any():
        return np.zeros((H, W, 4), np.float32)
    inv = vol.inv
    ub = np.zeros((20, 4), np.float32)
    ub[0, :3] = (center - vol.origin) @ inv.T
    ub[1, :3], ub[2, :3], ub[3, :3] = R[0] @ inv.T, R[1] @ inv.T, R[2] @ inv.T
    M = inv @ R.T
    ub[4, :3], ub[5, :3], ub[6, :3] = M[0], M[1], M[2]
    ub[7] = (xlim[0], ylim[0], (xlim[1] - xlim[0]) / W, (ylim[1] - ylim[0]) / H)
    ub[8, :3] = (W, H, TILE)
    ub[9] = (*vol.n, vol.step * step_frac)
    al = alpha if isinstance(alpha, (tuple, list)) else (alpha, alpha)
    ub[10] = (iso, al[0], al[1], zoff)
    ub[11] = (*np.asarray(cplus[:3], np.float32), 1.0 if aa else 0.0)
    ub[12] = (*np.asarray(cminus[:3], np.float32), 1.0 if occ2 is not None else 0.0)
    for i, (L, w) in enumerate(ORB.IBO_LIGHTS):
        ub[13 + i] = (*L, w)
    ub[16] = ORB.IBO_REG["orbital"]
    ub[17] = (ORB.IBO_FADE[0], ORB.IBO_FADE[1], max_layers, ORB.AA_EDGE)
    big = -1e30                                                   # −inf (frei) als große Zahl in der Textur
    o1 = np.full((H, W), big, np.float32) if occ is None else np.maximum(occ, big).astype(np.float32)
    o2 = np.full((2, 2), big, np.float32) if occ2 is None else np.maximum(occ2, big).astype(np.float32)
    return _S["w"].run(dict(vol=vol.data, vol_key=vol, tiles=tiles, occ=o1, occ2=o2, ubo=ub), W, H).copy()


def _tiles(vol, iso, R, center, xlim, ylim, W, H, exact=True):
    """Tiefenbereiche je Kachel genau wie `orbitals.render` (gleiche Stützstellen) -> RGBA32F (lo, hi, aktiv).
    exact=False (Ziehbild): eine Kachel über alles mit dem ganzen Tiefenbereich (die GPU läuft die Strahlen ohnehin
    schnell ab; spart die Kachelrechnung, ~15 ms bei 2 MPx)."""
    from elucida.core import orbitals as ORB
    S = (ORB.surface_points(vol, iso) - center) @ R.T
    m = float(np.linalg.norm(vol.axes.sum(axis=0)))
    if not exact:
        return np.array([[[S[:, 2].min() - m, S[:, 2].max() + m, 1.0, 0.0]]], np.float32), 1 << 24
    TILE = ORB.TILE
    px = (xlim[1] - xlim[0]) / W
    py = (ylim[1] - ylim[0]) / H
    TW, TH = (W + TILE - 1) // TILE, (H + TILE - 1) // TILE
    zmin = np.full((TH, TW), np.inf)
    zmax = np.full((TH, TW), -np.inf)
    tx = np.floor((S[:, 0] - xlim[0]) / (px * TILE)).astype(int)
    ty = np.floor((S[:, 1] - ylim[0]) / (py * TILE)).astype(int)
    k = int(math.ceil(m / min(px, py) / TILE)) + 1
    ok = (tx >= -k) & (tx < TW + k) & (ty >= -k) & (ty < TH + k)
    tx, ty, sz = tx[ok], ty[ok], S[ok, 2]
    for dx in range(-k, k + 1):
        for dy in range(-k, k + 1):
            a, b = tx + dx, ty + dy
            o = (a >= 0) & (a < TW) & (b >= 0) & (b < TH)
            np.minimum.at(zmin, (b[o], a[o]), sz[o])
            np.maximum.at(zmax, (b[o], a[o]), sz[o])
    act = np.isfinite(zmin)
    t = np.zeros((TH, TW, 4), np.float32)
    t[..., 0] = np.where(act, zmin - m, 0)
    t[..., 1] = np.where(act, zmax + m, 0)
    t[..., 2] = act
    return t, TILE


# ---------------------------------------------------------------------------- Einrichtung, Selbstcheck
def _mark(on):
    s = _S["settings"]
    if s is None:
        return
    if on:
        s.setValue(PENDING, "1")
    else:
        s.remove(PENDING)
    s.sync()                                                      # vor einem möglichen Treiberabsturz auf der Platte


def _start():
    """Erstes 3D-Bild: Top-Level + QRhiWidget anlegen, Selbstcheck gegen numpy. Fehler -> fail() und Ausnahme."""
    _mark(True)
    try:
        _S["host"], _S["w"] = _make_host()
        _S["ok"] = True                                           # für den Selbstcheck selbst
        d, cover = compare(*check_scene(*CHECK_PX))
        if not (d.mean() <= CHECK_MEAN and cover <= CHECK_COVER):
            raise RuntimeError(f"self-check differs from CPU (mean {d.mean():.3f}/255, coverage {cover:.4f})")
        info = _S["w"].info
        _S["reason"] = f"{info.get('backend')} on {info.get('adapter')}"
        LOG("3D: GPU " + _S["reason"])
    except Exception as ex:                                       # noqa: BLE001 – jeder Fehler: CPU
        _S["ok"] = None
        fail(str(ex) or type(ex).__name__)
        release()
        raise
    finally:
        _mark(False)


def release():
    """Top-Level löschen (MainWindow.release_widgets, Fehler)."""
    host = _S.get("host")
    _S.update(host=None, w=None)
    if host is not None:
        import shiboken6
        if shiboken6.isValid(host):
            host.close()
            shiboken6.delete(host)


def compare(cpu, gpu):
    """-> (Abweichung je Pixel auf vormultipliziertem RGBA × 255, Anteil Pixel mit Fläche nur in einem Bild)."""
    pc, pg = cpu[..., :3] * cpu[..., 3:], gpu[..., :3] * gpu[..., 3:]
    d = np.abs(np.concatenate([pc - pg, cpu[..., 3:] - gpu[..., 3:]], -1)).max(-1) * 255
    cover = float(((cpu[..., 3] > 0) != (gpu[..., 3] > 0)).mean())
    return d, cover


def test_volume(n=(64, 40, 32)):
    """Erfundenes Orbital (zwei Lappen mit Vorzeichen, ein Nebenlappen) auf einem schiefen Gitter (Å)."""
    from elucida.core import orbitals as ORB
    axes = np.array([[0.2, 0.0, 0.0], [0.02, 0.2, 0.0], [0.0, 0.01, 0.2]])
    origin = -0.5 * (np.array(n) - 1) @ axes
    idx = np.stack(np.meshgrid(*[np.arange(k) for k in n], indexing="ij"), -1)
    P = origin + idx @ axes
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    psi = (x * np.exp(-0.6 * (x * x + y * y + z * z)) - 0.35 * np.exp(-1.5 * ((x - 2.2) ** 2 + (y - 0.8) ** 2 + z * z)))
    return ORB.Volume(psi.astype(np.float32), origin, axes)


def check_scene(W, H, aa=True):
    """CPU- und GPU-Bild derselben erfundenen Szene (Orbital, zwei verdeckende Kugeln) -> (cpu, gpu)."""
    from elucida.core import orbitals as ORB
    vol = test_volume()
    iso = 0.05
    c, s = math.cos(0.5), math.sin(0.5)
    R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]) @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    e = 3.6
    xlim, ylim = (-e, e), (-e * H / W, e * H / W)
    sph = [(0.3, 0.2, 0.4, 0.5), (-1.2, -0.4, -0.2, 0.4)]
    occ = ORB.occluder_depth(sph, [], xlim, ylim, W, H)
    occ2 = ORB.occluder_depth(sph, [], xlim, ylim, 2 * W, 2 * H) if aa else None
    args = (vol, iso, R, np.zeros(3), 0.0, xlim, ylim, W, H, (0.9, 0.3, 0.2), (0.2, 0.4, 0.9))
    kw = dict(alpha=0.6, occ=occ, occ2=occ2, aa=aa, step_frac=0.5)
    return ORB.render(*args, **kw), render(*args, **kw)


# ---------------------------------------------------------------------------- Qt
def _make_host():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QVBoxLayout, QWidget
    host = QWidget(None, Qt.WindowType.Tool)
    host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    host.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
    host.setObjectName("elucida_gpu3d")
    lay = QVBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    w = _widget_class()()
    lay.addWidget(w)
    host.resize(16, 16)
    host.show()
    return host, w


_CLS = []


def _widget_class():
    if _CLS:
        return _CLS[0]
    import shiboken6
    from PySide6.QtCore import QSize
    from PySide6.QtGui import (QColor, QImage, QRhi, QRhiBuffer, QRhiColorAttachment, QRhiDepthStencilClearValue,
                               QRhiSampler, QRhiShaderResourceBinding as B, QRhiShaderStage, QRhiTexture,
                               QRhiTextureRenderTargetDescription, QRhiTextureSubresourceUploadDescription,
                               QRhiTextureUploadEntry, QRhiVertexInputAttribute, QRhiVertexInputBinding,
                               QRhiVertexInputLayout, QRhiViewport, QShader)
    from PySide6.QtWidgets import QRhiWidget
    import elucida
    FRAG = B.StageFlag.FragmentStage
    SH = elucida.ROOT / "assets" / "shaders"

    class GpuOrb(QRhiWidget):
        """Zwei Durchgänge in RGBA32F: Strahl je Pixelmitte (vormultipliziert), dann Kanten 2×2 und Division durch die
        Deckkraft; Ergebnis über grabFramebuffer."""

        def __init__(self):
            super().__init__()
            self.setColorBufferFormat(QRhiWidget.TextureFormat.RGBA32F)
            self.job, self.err, self.info = None, None, {}
            self._rhi = self._ptr = self._size = self._first = self._pipes = self._vol_key = None
            self._tex = {}

        def initialize(self, cb):
            self._size = None                                     # Zielgröße neu: Zwischentextur neu

        def releaseResources(self):
            self._rhi = None

        def _init(self):
            rhi = self.rhi()
            if rhi is None:
                raise RuntimeError("no QRhi")
            ptr = shiboken6.getCppPointer(rhi)[0]
            if self._rhi is None or self._ptr != ptr:
                self._rhi, self._ptr, self._size, self._vol_key, self._tex = None, ptr, None, None, {}
                if not rhi.isFeatureSupported(QRhi.Feature.ThreeDimensionalTextures):
                    raise RuntimeError(f"{rhi.backendName()}: no 3D textures")
                if not rhi.isTextureFormatSupported(QRhiTexture.Format.RGBA32F, QRhiTexture.Flag.RenderTarget):
                    raise RuntimeError(f"{rhi.backendName()}: no RGBA32F render target")
                di = rhi.driverInfo()
                name = di.deviceName
                self.info = dict(backend=rhi.backendName(), adapter=bytes(name).decode(errors="replace"),
                                 yup=rhi.isYUpInFramebuffer())
                v = np.array([[-1, -1], [3, -1], [-1, 3]], np.float32)
                self.vbuf = rhi.newBuffer(QRhiBuffer.Type.Immutable, QRhiBuffer.UsageFlag.VertexBuffer, v.nbytes)
                self.vbuf.create()
                self._first = rhi.nextResourceUpdateBatch()
                self._first.uploadStaticBuffer(self.vbuf, v.tobytes())
                self.ubuf = rhi.newBuffer(QRhiBuffer.Type.Dynamic, QRhiBuffer.UsageFlag.UniformBuffer, 20 * 16)
                self.ubuf.create()
                self.samp = rhi.newSampler(QRhiSampler.Filter.Nearest, QRhiSampler.Filter.Nearest,
                                           QRhiSampler.Filter.None_, QRhiSampler.AddressMode.ClampToEdge,
                                           QRhiSampler.AddressMode.ClampToEdge)
                self.samp.create()
                self.sh = {}
                for n in ("orb.vert.qsb", "orb1.frag.qsb", "orb2.frag.qsb"):
                    s = QShader.fromSerialized((SH / n).read_bytes())
                    if not s.isValid():
                        raise RuntimeError("invalid shader " + n)
                    self.sh[n] = s
                self._rhi = rhi                                   # erst nach vollständiger Einrichtung
            sz = self.renderTarget().pixelSize()
            if self._size == sz.toTuple():
                return
            self._size = sz.toTuple()
            self.pre = rhi.newTexture(QRhiTexture.Format.RGBA32F, sz, 1, QRhiTexture.Flag.RenderTarget)
            self.pre.create()
            self.pre_rt = rhi.newTextureRenderTarget(QRhiTextureRenderTargetDescription(QRhiColorAttachment(self.pre)))
            self.pre_rp = self.pre_rt.newCompatibleRenderPassDescriptor()
            self.pre_rt.setRenderPassDescriptor(self.pre_rp)
            self.pre_rt.create()
            self._pipes = None

        def _texture(self, name, fmt, w, h, d=0):
            t = self._tex.get(name)
            if t is None or t[1] != (fmt, w, h, d):
                tex = (self._rhi.newTexture(fmt, w, h, d, 1, QRhiTexture.Flag.ThreeDimensional) if d else
                       self._rhi.newTexture(fmt, QSize(w, h), 1, QRhiTexture.Flag(0)))
                if not tex.create():
                    raise RuntimeError("texture " + name)
                t = self._tex[name] = (tex, (fmt, w, h, d))
                self._pipes = None
                if name == "vol":
                    self._vol_key = None
            return t[0]

        def _pipeline(self, frag, srb, rp):
            p = self._rhi.newGraphicsPipeline()
            p.setShaderStages([QRhiShaderStage(QRhiShaderStage.Type.Vertex, self.sh["orb.vert.qsb"]),
                               QRhiShaderStage(QRhiShaderStage.Type.Fragment, self.sh[frag])])
            lay = QRhiVertexInputLayout()
            lay.setBindings([QRhiVertexInputBinding(8)])
            lay.setAttributes([QRhiVertexInputAttribute(0, 0, QRhiVertexInputAttribute.Format.Float2, 0)])
            p.setVertexInputLayout(lay)
            p.setShaderResourceBindings(srb)
            p.setRenderPassDescriptor(rp)
            if not p.create():
                raise RuntimeError("pipeline " + frag)
            return p

        def render(self, cb):
            try:
                self._render(cb)
            except Exception as ex:                               # noqa: BLE001 – in run() gemeldet
                self.err = ex

        def _render(self, cb):
            self._init()
            j, rhi = self.job, self._rhi
            u = rhi.nextResourceUpdateBatch()
            if self._first is not None:
                u.merge(self._first)
                self._first = None
            if j is None:                                         # Zeichnen beim Zeigen: nur die Uploads abschicken
                cb.beginPass(self.renderTarget(), QColor(0, 0, 0, 0), QRhiDepthStencilClearValue(1.0, 0), u)
                cb.endPass()
                return
            vol = j["vol"]
            n0, n1, n2 = vol.shape
            vt = self._texture("vol", QRhiTexture.Format.R32F, n2, n1, n0)
            if self._vol_key is not j["vol_key"]:
                for i in range(n0):                               # 3D-Textur: eine Scheibe je Eintrag
                    u.uploadTexture(vt, QRhiTextureUploadEntry(i, 0, QRhiTextureSubresourceUploadDescription(
                        np.ascontiguousarray(vol[i]).tobytes())))
                self._vol_key = j["vol_key"]
            for name, arr, fmt in (("tiles", j["tiles"], QRhiTexture.Format.RGBA32F),
                                   ("occ", j["occ"], QRhiTexture.Format.R32F),
                                   ("occ2", j["occ2"], QRhiTexture.Format.R32F)):
                tx = self._texture(name, fmt, arr.shape[1], arr.shape[0])
                u.uploadTexture(tx, QRhiTextureUploadEntry(0, 0, QRhiTextureSubresourceUploadDescription(
                    np.ascontiguousarray(arr, np.float32).tobytes())))
            ub = j["ubo"].copy()
            ub[8, 3] = 1.0 if self.info["yup"] else 0.0
            u.updateDynamicBuffer(self.ubuf, 0, ub.tobytes())
            if self._pipes is None:
                T = {k: v[0] for k, v in self._tex.items()}
                b1 = [B.uniformBuffer(0, FRAG, self.ubuf)] + [B.sampledTexture(i + 1, FRAG, T[k], self.samp)
                                                              for i, k in enumerate(("vol", "tiles", "occ", "occ2"))]
                s1 = rhi.newShaderResourceBindings()
                s1.setBindings(b1)
                s1.create()
                s2 = rhi.newShaderResourceBindings()
                s2.setBindings(b1 + [B.sampledTexture(5, FRAG, self.pre, self.samp)])
                s2.create()
                self._pipes = (s1, s2, self._pipeline("orb1.frag.qsb", s1, self.pre_rp),
                               self._pipeline("orb2.frag.qsb", s2, self.renderTarget().renderPassDescriptor()))
            s1, s2, p1, p2 = self._pipes
            sz = self.renderTarget().pixelSize()
            vp = QRhiViewport(0, 0, sz.width(), sz.height())
            for rt, pipe, srb, ub_ in ((self.pre_rt, p1, s1, u), (self.renderTarget(), p2, s2, None)):
                cb.beginPass(rt, QColor(0, 0, 0, 0), QRhiDepthStencilClearValue(1.0, 0), ub_)
                cb.setGraphicsPipeline(pipe)
                cb.setViewport(vp)
                cb.setShaderResources(srb)
                cb.setVertexInput(0, [(self.vbuf, 0)])
                cb.draw(3)
                cb.endPass()

        def run(self, job, W, H):
            """Ein Bild rechnen -> RGBA mit gerader Deckkraft (H×W×4, Zeile 0 unten; Ansicht auf den QImage-Speicher)."""
            self.err, self.job = None, job
            try:
                self.setFixedColorBufferSize(W, H)
                img = self.grabFramebuffer()
            finally:
                self.job = None
            if self.err is not None:
                raise self.err
            if img.isNull() or (img.width(), img.height()) != (W, H):
                raise RuntimeError("no QRhi image (grabFramebuffer)")
            if img.format() != QImage.Format.Format_RGBA32FPx4:
                raise RuntimeError(f"grab format {img.format()}")
            self._img = img                                       # Speicher der Ansicht unten
            a = np.frombuffer(img.constBits(), np.float32).reshape(H, img.bytesPerLine() // 16, 4)[:, :W]
            # QImage von oben nach unten; der Shader legt Bildzeile 0 (unten) auf jedem Backend nach unten (`yup`)
            return a[::-1]

    _CLS.append(GpuOrb)
    return GpuOrb


# ---------------------------------------------------------------------------- --gpu-probe
def probe(folder):
    """Versteckte Option `--gpu-probe ORDNER` (Windows-Test): GPU- und CPU-Bild derselben erfundenen Szene, Zeiten,
    Backend und Grafikkarte nach ORDNER/result.txt (+ gpu.png, cpu.png, diff_x8.png). -> 0 bei PASS, sonst 1."""
    from pathlib import Path
    from PIL import Image
    import PySide6
    from PySide6.QtCore import qVersion
    from elucida import APP_VERSION
    from elucida.core import orbitals as ORB
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"Elucida {APP_VERSION} GPU probe ({time.strftime('%Y-%m-%d %H:%M:%S')})",
             f"system: {sys.platform}, Qt {qVersion()}, PySide6 {PySide6.__version__}, Python {sys.version.split()[0]}"]
    ok = False
    W, H = 1200, 800
    try:
        t = time.perf_counter()
        if _S["ok"] is None and wanted():
            _start()                                              # Einrichtung + Selbstcheck (klein, wie in der App)
        t_first = time.perf_counter() - t
        info = _S["w"].info
        lines.append(f"backend: {info.get('backend')}, adapter: {info.get('adapter')}")
        args = _probe_args(W, H)
        tg = []
        for _ in range(5):
            t = time.perf_counter()
            gpu = render(*args[0], **args[1])
            tg.append(time.perf_counter() - t)
        t = time.perf_counter()
        cpu = ORB.render(*args[0], **args[1])
        tc = time.perf_counter() - t
        d, cover = compare(cpu, gpu)
        ok = d.mean() <= CHECK_MEAN and cover <= CHECK_COVER
        lines += [f"image: {W} x {H} px, edges 2x2, occluding spheres",
                  f"time GPU: setup and self-check {t_first * 1000:.0f} ms; then mean "
                  f"{np.mean(tg) * 1000:.1f} ms, min {min(tg) * 1000:.1f} ms (5 images)",
                  f"time CPU (numpy): {tc * 1000:.0f} ms",
                  f"difference GPU vs CPU (premultiplied RGBA x 255): mean {d.mean():.4f}, max {d.max():.2f}, "
                  f"pixels > 2: {int((d > 2).sum())}",
                  f"coverage difference: {cover * 100:.3f} % of pixels (limit {CHECK_COVER * 100:.2f} %)",
                  f"limits: mean <= {CHECK_MEAN}, coverage <= {CHECK_COVER * 100:.2f} %"]
        for name, a in (("gpu.png", gpu), ("cpu.png", cpu)):
            Image.fromarray(np.clip(a[::-1] * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(out / name)
        Image.fromarray(np.clip(d[::-1] * 8, 0, 255).astype(np.uint8), "L").save(out / "diff_x8.png")
    except Exception as ex:                                       # noqa: BLE001 – Ergebnis in die Datei
        import traceback
        lines += [f"GPU not usable: {ex}", "", traceback.format_exc()]
    lines.insert(2, "RESULT: " + ("PASS" if ok else "FAIL"))
    (out / "result.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    release()
    print(out / "result.txt")
    return 0 if ok else 1


def _probe_args(W, H):
    from elucida.core import orbitals as ORB
    vol = test_volume((110, 58, 46))
    c, s = math.cos(0.7), math.sin(0.7)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]) @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    e = 5.0
    xlim, ylim = (-e, e), (-e * H / W, e * H / W)
    sph = [(x, y, z, 0.35) for x, y, z in ((0, 0, 0.5), (1.2, 0.4, 0), (-1.3, -0.6, 0.3), (2.4, 0.9, -0.4))]
    occ = ORB.occluder_depth(sph, [], xlim, ylim, W, H)
    occ2 = ORB.occluder_depth(sph, [], xlim, ylim, 2 * W, 2 * H)
    return ((vol, 0.05, R, np.zeros(3), 0.0, xlim, ylim, W, H, (0.9, 0.3, 0.2), (0.2, 0.4, 0.9)),
            dict(alpha=0.6, occ=occ, occ2=occ2, aa=True, step_frac=0.5))
