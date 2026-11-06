"""Regression: draw a benzene in a previously empty Compound editor with real Qt input."""
import os
import sys
import tempfile
import time
import locale
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['ELUCIDA_OCTET'] = '1'
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from elucida.app import main_window as MW, project as PRJ
from elucida.core import chem as CHEM

folder = Path(tempfile.mkdtemp(prefix='elucida-new-compound-'))
MW.SETTINGS_FILE = folder / 'settings.ini'
app = QApplication([])
w = MW.MainWindow()
assert locale.setlocale(locale.LC_NUMERIC) == 'C', 'native chemistry must use decimal points after Qt startup'
w.show()

try:
    assert w.create_project(folder / 'project')
    path = PRJ.ensure_templates(w.project_dir)[0]
    assert not PRJ.cdxml_has_content(path), 'test must start with an empty document'
    dlg = MW.CompoundDialog(w, dict(structure=str(path)))
    dlg.show()
    editor = dlg.drawing_editor
    deadline = time.monotonic() + 40
    while not (editor.ready and editor.path):
        assert time.monotonic() < deadline, f'Editor did not load: {folder}'
        QTest.qWait(100)
    QTest.qWait(300)
    saves = []
    editor.saved.connect(saves.append)
    target = editor.view.focusProxy() or editor.view
    editor.view.setFocus()
    point = QPoint(target.width() * 2 // 3, target.height() // 2)
    QTest.mouseMove(target, point)
    QTest.keyClick(target, Qt.Key_J)  # Octet's benzene tool
    QTest.qWait(150)
    QTest.mouseClick(target, Qt.LeftButton, pos=point)
    QTest.qWait(2200)
    print('draft', editor.path, 'saves', saves, 'dirty', editor.dirty,
          'fields', repr(dlg.ed_formula.text()), repr(dlg.ed_mw.text()), flush=True)
    print('calculated', MW.compound_from_structure(editor.path), flush=True)
    dlg.grab().save(str(folder / 'new-compound.png'))
    assert saves and not editor.dirty, 'new molecule did not autosave'
    assert dlg.ed_formula.text() == 'C6H6', f'benzene formula missing: {folder}'
    assert abs(float(dlg.ed_mw.text()) - 78.114) < .02, f'benzene mass missing: {folder}'
    assert not PRJ.cdxml_has_content(path), 'drawing wrote to original before OK'
    dlg.done(QDialog.Accepted)
    assert dlg.result_compound()['formula'] == 'C6H6'
    assert abs(dlg.result_compound()['mw'] - 78.114) < .02
    assert CHEM.load_cdxml(path)['formula'] == 'C6H6'
    dlg.cleanup()
    dlg.deleteLater()
    QTest.qWait(100)
    print('OK: new benzene updates formula/mass and OK publishes the compound', folder, flush=True)
finally:
    MW.release_widgets(app)
