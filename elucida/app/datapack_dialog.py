"""
elucida/app/datapack_dialog.py - Dialog „Datenpaket (Zip) exportieren“: Auswahl je Analytik/Datei, Laborkürzel ersetzen.
Logik ohne Qt in elucida/exchange/datapack.py.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QProgressDialog, QPushButton,
                               QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from elucida.app import style as STYLE
from elucida.app.i18n import T
from elucida.exchange import datapack as DP


def selection_key(project_dir):
    """QSettings-Schlüssel der gemerkten Auswahl eines Projekts (auch für die Datenpakete der Publikation)."""
    h = hashlib.md5(str(Path(project_dir or ".").resolve()).encode()).hexdigest()[:12]
    return f"datapack/{h}"


def saved_selection(settings, project_dir) -> dict:
    try:
        return json.loads(settings.value(selection_key(project_dir), "{}") or "{}")
    except (TypeError, ValueError):
        return {}


def _mb(n):
    return f"{n / 1e6:.1f} MB" if n >= 1e5 else f"{n / 1e3:.0f} kB"


class DatapackDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.setWindowTitle(T("dp_title"))
        self.resize(760, 680)
        self.items = DP.collect(main.get_state(), main.project_dir)
        self._apply_saved()
        v = QVBoxLayout(self)
        hint = QLabel(T("dp_hint"), wordWrap=True)
        hint.setStyleSheet(STYLE.HINT_CSS)
        v.addWidget(hint)
        f = QFormLayout()
        self.ed_name = QLineEdit(main.export_name())
        self.ed_name.setToolTip(T("dp_name_tip"))
        f.addRow(T("dp_name"), self.ed_name)
        v.addLayout(f)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([T("dp_col_file"), T("dp_col_size")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._fill_tree()
        self.tree.itemChanged.connect(self._changed)
        v.addWidget(self.tree, 3)

        v.addWidget(QLabel(f"<b>{T('dp_codes')}</b>"))
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels([T("dp_code"), T("dp_code_name"), T("dp_code_text")])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setMinimumHeight(90)
        name = main.export_name()
        for code in DP.find_codes(self.items):
            self._add_code(code, name, f"Compound {name}")
        v.addWidget(self.tbl, 1)
        row = QHBoxLayout()
        b = QPushButton(T("dp_code_add"))
        b.clicked.connect(lambda: self._add_code("", name, f"Compound {name}"))
        row.addWidget(b)
        self.cb_text = QCheckBox(T("dp_text"))
        self.cb_text.setToolTip(T("dp_text_tip"))
        self.cb_text.setChecked(True)
        row.addWidget(self.cb_text)
        row.addStretch(1)
        v.addLayout(row)

        self.lbl_size = QLabel("")
        v.addWidget(self.lbl_size)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.btn_ok = bb.addButton(T("dp_export"), QDialogButtonBox.AcceptRole)
        self.btn_ok.setProperty("accent", True)
        self.btn_ok.setIcon(STYLE.icon("export", "#FFFFFF"))
        bb.accepted.connect(self.export)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._update_size()
        self.report = None

    # -- Auswahl --------------------------------------------------------------------------
    def _settings_key(self):
        return selection_key(self.main.project_dir)

    def _apply_saved(self):
        saved = saved_selection(self.main.settings, self.main.project_dir)
        for it in self.items:
            if it.key in saved:
                it.on = bool(saved[it.key])

    def _save(self):
        self.main.settings.setValue(self._settings_key(), json.dumps({it.key: it.on for it in self.items}))

    def _fill_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        self._node = {}
        for g, folder, _ in DP.GROUPS:
            its = [i for i in self.items if i.group == g]
            if not its:
                continue
            top = QTreeWidgetItem([T("dp_grp_" + g), ""])
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            self.tree.addTopLevelItem(top)
            for it in its:
                ch = QTreeWidgetItem([it.arc, _mb(it.size)])
                ch.setFlags(ch.flags() | Qt.ItemIsUserCheckable)
                ch.setCheckState(0, Qt.Checked if it.on else Qt.Unchecked)
                ch.setToolTip(0, str(it.src))
                top.addChild(ch)
                self._node[id(ch)] = it
            n_on = sum(i.on for i in its)                 # Gruppe: an / aus / teilweise
            top.setCheckState(0, Qt.Checked if n_on == len(its) else Qt.Unchecked if not n_on else Qt.PartiallyChecked)
            top.setExpanded(g not in ("elucida",))
        self.tree.blockSignals(False)

    def _changed(self, node, col):
        it = self._node.get(id(node))
        if it is not None:
            it.on = node.checkState(0) == Qt.Checked
        self._update_size()

    def _update_size(self):
        on = [i for i in self.items if i.on]
        self.lbl_size.setText(T("dp_size", n=len(on), size=_mb(sum(i.size for i in on))))
        self.btn_ok.setEnabled(bool(on))

    def _add_code(self, code, name, text):
        r = self.tbl.rowCount()
        self.tbl.insertRow(r)
        for c, val in enumerate((code, name, text)):
            self.tbl.setItem(r, c, QTableWidgetItem(val))

    def replacements(self):
        """(Ersatz in Namen, Ersatz im Text) je Kürzel aus der Tabelle; leere Kürzel fallen weg."""
        names, texts = {}, {}
        for r in range(self.tbl.rowCount()):
            code = (self.tbl.item(r, 0).text() if self.tbl.item(r, 0) else "").strip()
            if not code:
                continue
            names[code] = (self.tbl.item(r, 1).text() if self.tbl.item(r, 1) else "").strip() or code
            texts[code] = (self.tbl.item(r, 2).text() if self.tbl.item(r, 2) else "").strip() or names[code]
        return names, texts

    # -- Export ---------------------------------------------------------------------------
    def export(self, path=None):
        root = self.ed_name.text().strip() or self.main.export_name()
        names, texts = self.replacements()
        root = DP.replace_codes(root, names)
        if path is None:
            start = self.main.settings.value("datapack_dir", "") or str(Path(self.main.project_dir or ".").parent)
            path, _ = QFileDialog.getSaveFileName(self, T("dp_title"), str(Path(start) / f"{root}.zip"), "Zip (*.zip)")
            if not path:
                return None
            self.main.settings.setValue("datapack_dir", str(Path(path).parent))
        self._save()
        dlg = QProgressDialog(T("dp_writing"), T("cancel"), 0, 100, self)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(400)

        def progress(i, n):
            dlg.setMaximum(n)
            dlg.setValue(i)
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            return not dlg.wasCanceled()
        try:
            self.report = DP.write_zip(self.items, path, root, names, texts if self.cb_text.isChecked() else None,
                                       progress)
        except PermissionError:
            self.main.error(T("report_locked", p=path))
            return None
        finally:
            dlg.close()
        if self.report.get("cancelled"):
            return None
        rep = self.report
        self.main.log_signal.emit(T("dp_done", p=rep["path"], n=rep["files"], size=_mb(rep["bytes"]),
                                    t=len(rep["text_replaced"])))
        if rep["kept"]:
            self.main.log_signal.emit(T("dp_kept", files="\n  ".join(rep["kept"][:30])))
        self.accept()
        self.main.exported([Path(rep["path"]).parent])
        return rep
