"""Independent, editable orbital views for reaction profiles (no live DFT links)."""
from copy import deepcopy
import io
import json
import hashlib
from pathlib import Path
from elucida.app.i18n import T

import numpy as np
from PIL import Image
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                               QDoubleSpinBox, QDialogButtonBox, QPushButton)
from elucida.core import orbitals as ORB
from elucida.app.canvas_theme import register
from elucida.tabs import base as TABS, xray as XRAY


def snapshot(tab, entry, orbital):
    """Capture geometry, source orbital, camera and all drawing options by value."""
    # A user can recapture a file edited outside Elucida. Never attach a new hash
    # to an old cached volume or old Molden bond orders.
    paths = {str(o['file']) for o in entry.get('orbitals', [])}
    if entry.get('molden'):
        paths.add(str(entry['molden']))
    cache = tab.main.extra_cache
    for key in list(cache):
        if isinstance(key, tuple) and any(isinstance(v, str) and v in paths for v in key):
            del cache[key]
    mol = tab.molecule(entry, interactive=False)
    opts = tab.opts(entry, interactive=False, orb=orbital)
    orb = opts.pop("orbital")
    if orb is None and orbital is not None:
        raise ValueError(T('rp_load_an_available_orbital_first'))
    if orb is None:
        plus, minus, alpha = ORB.orbital_colors(0)
        orb = dict(plus=plus, minus=minus, alpha=alpha)
        opts['style'] = 'iboview'
    opts["wire"] = list(opts.get("wire") or [])
    opts["bg"] = "transparent"
    # Freeze bonds too: changing the main viewer must not alter this image.
    bo = tab.bond_orders(entry)
    bonds = [list(x) for x in (sorted(bo) if bo is not None else mol.bonds)]
    geometry = tab.geometry(entry)
    data = dict(version=1, show_orbital=orbital is not None,
                source=deepcopy(entry["orbitals"][orbital]) if orbital is not None else dict(file=entry['file']),
                name=tab.orb_name(entry, entry["orbitals"][orbital]) if orbital is not None else entry.get('name', T('rp_geometry_only')),
                geometry=dict(els=list(geometry[1]), xyz=np.asarray(geometry[2]).tolist(), bonds=bonds,
                              labels=[a["label"] for a in mol.atoms]),
                options=opts, view=tab.view_of(entry, mol).reshape(-1).tolist(),
                zoom=entry.get("zoom", 1.0), pan=deepcopy(entry.get("pan") or [0., 0.]),
                iso_mode=tab.st.get("orb_iso_mode", "frac"), fraction=tab.st.get("orb_frac", ORB.ISO_FRACTION),
                absolute=tab.st.get("orb_abs", ORB.ISO_ABS),
                plus=list(orb["plus"]), minus=list(orb["minus"]), alpha=orb["alpha"],
                radius=tab.st.get("radius", .25), layout={})
    data["source_sha256"] = hashlib.sha256(Path(data["source"]["file"]).read_bytes()).hexdigest()
    data["cfg"] = deepcopy(TABS.FigureTab.base_cfg(tab))
    data["cfg"]["_base_dir"] = "."
    data["cfg"]["output"] = "orbital.png"
    data["cfg"]["figsize_in"] = [4., 4.]
    if bo is not None:
        data["bond_orders"] = [[a, b, value] for (a, b), value in bo.items()]
    json.dumps(data)  # reject nonportable data before it enters project state
    return data


def build(tab, data, fig):
    from elucida.tabs.dft import XyzMolecule
    g = data["geometry"]
    mol = XyzMolecule(g["els"], np.asarray(g["xyz"]), [tuple(x) for x in g["bonds"]], g["labels"],
                      uiso=(data["radius"] / XRAY.chi2_scale(.5)) ** 2)
    opts = deepcopy(data["options"])
    path = Path(data["source"]["file"])
    stat = path.stat()
    digest = tab.cache(("profile-source-hash", str(path), stat.st_size, stat.st_mtime_ns),
                       lambda: hashlib.sha256(path.read_bytes()).hexdigest())
    if digest != data["source_sha256"]:
        raise ValueError(T('rp_the_orbital_file_changed_please_capture_a_new_view'))
    opts['orbital'] = None
    if data.get('show_orbital', True):
        volume = tab.orb_volume(data["source"])
        iso = data["absolute"] if data["iso_mode"] == "abs" else ORB.iso_for_fraction(volume.data, data["fraction"])
        opts["orbital"] = dict(vol=volume, iso=iso, plus=data["plus"], minus=data["minus"], alpha=data["alpha"])
    if data.get("bond_orders"):
        opts["bond_orders"] = {(a, b): v for a, b, v in data["bond_orders"]}
    cfg = deepcopy(data["cfg"])
    F = XRAY.XrayFigure(cfg, mol, np.asarray(data["view"]).reshape(3, 3), opts, deepcopy(data["layout"]), fig,
                        zoom=data.get("zoom", 1.), pan=data.get("pan", [0., 0.]))
    return F


def asset(tab, data):
    """Transparent export-neutral rendering; cache includes source modification time."""
    path = Path(data["source"]["file"])
    stat = path.stat()
    key = json.dumps(data, sort_keys=True)
    def render():
        fig = Figure(figsize=(4, 4), dpi=150)
        FigureCanvasAgg(fig)
        build(tab, data, fig)
        stream = io.BytesIO()
        fig.savefig(stream, format="png", transparent=True, dpi=300)
        rgba = np.asarray(Image.open(stream).convert("RGBA")).copy()
        y, x = np.nonzero(rgba[:, :, 3])
        if len(x):
            rgba = rgba[max(0, y.min()-8):y.max()+9, max(0, x.min()-8):x.max()+9].copy()
        return dict(rgba=rgba, pdf=None, clip=None)
    return tab.cache(("profile-orbital", str(path), stat.st_size, stat.st_mtime_ns, key), render)


class OrbitalViewDialog(QDialog):
    """Edits a private copy. Cancel does not mutate the annotation or DFT state."""
    def __init__(self, tab, data):
        super().__init__(tab)
        self.tab, self.data, self.dragger = tab, deepcopy(data), None
        self.setWindowTitle(T('rp_profile_orbital_view'))
        self.resize(850, 730)
        self.setSizeGripEnabled(True)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12); v.setSpacing(10)
        v.addWidget(QLabel(data["name"], objectName="cardTitle"))
        source = self.data["source"]
        self.mo = QComboBox()
        if not data.get('show_orbital', True):
            self.mo.addItem(T('rp_geometry_only'))
            self.mo.setEnabled(False)
        elif "mo" in source:
            m = tab.molden_of(source["file"])
            for i in range(len(m["mos"])):
                self.mo.addItem(tab.mo_label(m, i), i)
            self.mo.setCurrentIndex(source["mo"])
        else:
            c = tab.cube_of(source["file"])
            for i in range(len(c["data"])):
                self.mo.addItem(f"MO {c['mos'][i]}" if c.get('mos') else f"Orbital {i+1}", i)
            self.mo.setCurrentIndex(source.get("idx", 0))
        self.mo.currentIndexChanged.connect(self.orbital_changed)
        v.addWidget(self.mo)
        hint = QLabel(T('rp_drag_rotate_right_button_pan_wheel_zoom_this_view_remains_independent'))
        hint.setWordWrap(True); hint.setProperty("formlabel", True)
        v.addWidget(hint)
        row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItem(T('rp_density_fraction'), "frac")
        self.mode.addItem(T('rp_isovalue_a_u'), "abs")
        self.mode.setCurrentIndex(self.mode.findData(data["iso_mode"]))
        self.value = QDoubleSpinBox()
        self.alpha = QDoubleSpinBox()
        self.alpha.setRange(.01, 1.)
        self.alpha.setSingleStep(.05)
        self.alpha.setValue(data["alpha"])
        for w in (self.mode, self.value, QLabel(T('dft_orb_alpha')), self.alpha): row.addWidget(w)
        from matplotlib.colors import to_hex
        for key in ("plus", "minus"):
            row.addWidget(TABS.color_button(to_hex(data[key]), lambda c, key=key: self.color(key, c)))
        v.addLayout(row)
        if not data.get('show_orbital', True):
            for i in range(row.count()):
                STYLE.item_at(row, i).widget().setVisible(False)
        self.fig = Figure(figsize=(4, 4), dpi=100)
        self.canvas = register(FigureCanvasQTAgg(self.fig))
        self.host = TABS.CanvasHost(self.canvas, self.fig)
        v.addWidget(self.host, 1)
        self.error = QLabel()
        self.error.setWordWrap(True)
        v.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setProperty("accent", True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        v.addWidget(self.buttons)
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.value.editingFinished.connect(self.settings_changed)
        self.alpha.editingFinished.connect(self.settings_changed)
        self.mode_changed()

    def mode_changed(self, *_):
        frac = self.mode.currentData() == "frac"
        self.value.setDecimals(2 if frac else 5)
        self.value.setRange(.1 if frac else .00001, 99.9 if frac else 10.)
        self.value.setSingleStep(1. if frac else .005)
        self.value.setValue(self.data["fraction" if frac else "absolute"])
        self.settings_changed()

    def settings_changed(self):
        self.data["iso_mode"] = self.mode.currentData()
        self.data["fraction" if self.data["iso_mode"] == "frac" else "absolute"] = self.value.value()
        self.data["alpha"] = self.alpha.value()
        self.render()

    def orbital_changed(self, *_):
        source = self.data["source"]
        source["mo" if "mo" in source else "idx"] = self.mo.currentData()
        self.data["name"] = self.mo.currentText()
        self.render()

    def color(self, key, color):
        from matplotlib.colors import to_rgb
        self.data[key] = list(to_rgb(color))
        self.render()

    def render(self):
        if self.dragger:
            self.dragger.disconnect()
            self.dragger = None
        try:
            F = build(self.tab, self.data, self.fig)
            self.dragger = XRAY.XrayMouse(F, self)
            self.host.set_figure_size(4, 4)
            self.error.clear()
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        except Exception as ex:
            self.error.setText(str(ex))
            self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)

    def view_changed(self, matrix): self.data["view"] = matrix.reshape(-1).tolist()
    def pan_changed(self, pan): self.data["pan"] = list(pan)
    def zoom_changed(self, zoom): self.data["zoom"] = zoom
    def labels_moved(self, layout): self.data["layout"] = layout
    def hover_atom(self, *_): pass
    def atom_clicked(self, *_): pass
    def atom_double_clicked(self, *_): pass
    def atoms_boxed(self, *_): pass

    def done(self, result):
        if self.dragger:
            self.dragger.disconnect()
        super().done(result)
