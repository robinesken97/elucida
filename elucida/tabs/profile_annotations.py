"""Profile image placement, keyed to species IDs or IRC frame indices."""
from copy import deepcopy
from pathlib import Path
from elucida.app.i18n import T
import uuid

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
                               QDoubleSpinBox, QListWidget, QPushButton, QFileDialog, QDialogButtonBox, QLabel)
from elucida.app import project as PRJ
from elucida.tabs import profile_orbitals as PO


def anchor_key(anchor):
    return ("species", anchor["species"]) if "species" in anchor else ("irc", anchor["irc"], anchor["frame"])


def append_images(pages, cfg, anchors, mode):
    """Image offsets and widths use axes fractions; chemistry coordinates stay fixed."""
    from elucida.core import images as IMG
    notes = []
    for a in pages.prof.get("annotations", []):
        if a["mode"] != mode:
            continue
        xy = anchors.get(anchor_key(a["anchor"]))
        if xy is None:
            notes.append(T('rp_image_anchor_missing_from_current_profile') + a.get("label", ""))
            continue
        try:
            asset = PO.asset(pages.tab, a["orbital"]) if a["kind"] == "orbital" else IMG.load_structure(a["structure"])
            if asset is None:
                raise ValueError(T('rp_image_unreadable'))
            dx, dy = a.get("offset", [-.09, .085])
            x0, x1 = cfg["xlim"]
            y0, y1 = cfg["ylim"]
            anchor = [(xy[0]-x0)/(x1-x0), (xy[1]-y0)/(y1-y0)]
            cfg["images"].append(dict(id="annotation_" + a["uid"], file=a.get("structure", "orbital"),
                                      _asset=asset, frame=False, width=a.get("width", .18),
                                      _anchor_af=anchor, pos=[anchor[0]+dx, anchor[1]+dy]))
        except Exception as ex:
            notes.append(a.get("label", "") + ": " + str(ex))
    return notes


class AnnotationDialog(QDialog):
    def __init__(self, pages):
        super().__init__(pages.tab)
        self.pages, self.items = pages, deepcopy(pages.prof.get("annotations", []))
        self.loading = False
        self.setWindowTitle(T('rp_reaction_profile_images'))
        self.resize(780, 620)
        v = QVBoxLayout(self)
        hint = QLabel(T('rp_each_image_belongs_to_a_level_or_irc_point_octet_drawings_and_independ'))
        hint.setWordWrap(True)
        v.addWidget(hint)
        self.anchor = QComboBox()
        for i, e in enumerate(pages.profile_entries()):
            self.anchor.addItem(T('rp_level') + pages.spec(e, i)["label"],
                                dict(mode="levels", anchor=dict(species=e["uid"])))
        for c in pages.irc_data()[0]:
            for i in range(len(c["E"])):
                self.anchor.addItem(f"IRC: {c['label']} · {i+1}" + (" (TS)" if i == c['ts'] else ""),
                                    dict(mode="irc", anchor=dict(irc=c["uid"], frame=i)))
        v.addWidget(self.anchor)
        row = QHBoxLayout()
        for key, fn in (('rp_draw_in_octet', self.draw),
                           ('rp_choose_structure_image', self.choose),
                           ('rp_orbital_view', self.orbital)):
            b = QPushButton(T(key)); b.clicked.connect(fn); row.addWidget(b)
        v.addLayout(row)
        self.list = QListWidget()
        v.addWidget(self.list, 1)
        form = QFormLayout()
        self.width, self.dx, self.dy = QDoubleSpinBox(), QDoubleSpinBox(), QDoubleSpinBox()
        for w in (self.width, self.dx, self.dy):
            w.setRange(-100, 100); w.setDecimals(1); w.setSuffix(" %")
            w.editingFinished.connect(self.place)
        self.width.setRange(1, 100)
        form.addRow(T('rp_width'), self.width)
        form.addRow(T('rp_horizontal_offset'), self.dx)
        form.addRow(T('rp_vertical_offset'), self.dy)
        v.addLayout(form)
        row = QHBoxLayout()
        for key, fn in (('rp_edit', self.edit), ('remove', self.remove)):
            b = QPushButton(T(key)); b.clicked.connect(fn); row.addWidget(b)
        v.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        v.addWidget(buttons)
        self.list.currentRowChanged.connect(self.selection)
        self.sync()

    def sync(self, row=0):
        self.list.clear()
        for a in self.items:
            key = anchor_key(a['anchor'])
            target = next((self.anchor.itemText(i) for i in range(self.anchor.count())
                           if anchor_key(self.anchor.itemData(i)['anchor']) == key), T('rp_missing_anchor'))
            self.list.addItem(f"{target} — {a.get('label', a['kind'])}")
        self.list.setCurrentRow(min(row, len(self.items)-1))

    def selection(self, row):
        self.loading = True
        a = self.items[row] if 0 <= row < len(self.items) else {}
        self.width.setValue(a.get("width", .18)*100)
        dx, dy = a.get("offset", [-.09, .085])
        self.dx.setValue(dx*100); self.dy.setValue(dy*100)
        self.loading = False

    def place(self):
        i = self.list.currentRow()
        if not self.loading and 0 <= i < len(self.items):
            self.items[i].update(width=self.width.value()/100, offset=[self.dx.value()/100, self.dy.value()/100])

    def add(self, **values):
        target = self.anchor.currentData()
        if target is None: return
        self.items.append(dict(uid=uuid.uuid4().hex, width=.18, offset=[-.09, .085], **deepcopy(target), **values))
        self.sync(len(self.items)-1)

    def choose(self):
        if self.anchor.currentData() is None: return
        p, _ = QFileDialog.getOpenFileName(self, T('rp_structure_image'), "",
                                           "Structures (*.cdxml *.cdx *.svg *.pdf *.png *.jpg)")
        if p:
            p = self.pages.tab.main.import_file(p, PRJ.STRUCTURES)
            self.add(kind="structure", structure=p, label=Path(p).stem)

    def drawing(self, original=None):
        """Edit a new copy, so cancelling either dialog preserves the old drawing."""
        from elucida.app.drawing_editor import DrawingDialog, DrawingEditor
        import shutil
        main = self.pages.tab.main
        if not main.ensure_project(): return None
        p = Path(main.project_dir) / PRJ.STRUCTURES / ("profile_"+uuid.uuid4().hex[:12]+".cdxml")
        p.parent.mkdir(parents=True, exist_ok=True)
        if original:
            shutil.copy2(original, p)
        else:
            p.write_text(PRJ.EMPTY_CDXML, encoding="utf-8")
        d = DrawingDialog(self)
        d.resize(900, 620); d.setSizeGripEnabled(True)
        v = QVBoxLayout(d)
        editor = DrawingEditor(d, scheme_actions=False); d.editor = editor
        editor.set_canvas_dark(main.canvas_is_dark()); editor.open_path(p)
        v.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); v.addWidget(buttons)
        ok = d.exec() == QDialog.Accepted
        d.deleteLater()
        return str(p) if ok and PRJ.cdxml_has_content(p) else None

    def draw(self):
        if self.anchor.currentData() is None: return
        p = self.drawing()
        if p: self.add(kind="structure", structure=p, label=T('rp_octet_drawing'))

    def orbital(self):
        from PySide6.QtWidgets import QInputDialog
        if self.anchor.currentData() is None: return
        t = self.pages.tab
        sources = [(e, k, f"{e.get('name', '')} · {t.orb_name(e, orb)}")
                   for e in t.entries() for k, orb in enumerate(e.get("orbitals") or [])]
        if not sources:
            t.main.error(T('rp_first_load_a_cube_or_molden_file_in_the_dft_tab_and_select_an_orbital'))
            return
        labels = [f"{i+1}: {label}" for i, (_, _, label) in enumerate(sources)]
        label, ok = QInputDialog.getItem(self, T('rp_choose_orbital'), "Orbital", labels, 0, False)
        if not ok: return
        e, k, _ = sources[labels.index(label)]
        try:
            data = PO.snapshot(t, e, k)
            dialog = PO.OrbitalViewDialog(t, data)
            if dialog.exec() == QDialog.Accepted:
                self.add(kind="orbital", orbital=dialog.data, label=dialog.data["name"])
            dialog.deleteLater()
        except Exception as ex:
            t.main.error(str(ex))

    def edit(self):
        i = self.list.currentRow()
        if not 0 <= i < len(self.items): return
        a = self.items[i]
        if a["kind"] == "orbital":
            dialog = PO.OrbitalViewDialog(self.pages.tab, a["orbital"])
            if dialog.exec() == QDialog.Accepted:
                a["orbital"], a["label"] = dialog.data, dialog.data["name"]
            dialog.deleteLater()
        elif Path(a["structure"]).suffix.lower() == ".cdxml":
            p = self.drawing(a["structure"])
            if p: a["structure"] = p
        self.sync(i)

    def remove(self):
        i = self.list.currentRow()
        if 0 <= i < len(self.items):
            del self.items[i]; self.sync(i)
