"""Regression: draw a benzene in the empty editor of the Compound tab with real Qt input (needs a real window).

Checks that the drawing saves itself, that formula and molar mass follow it, that a molar mass entered by hand
survives the next drawing edit and that a cleared field takes the drawn value again."""
import os
import sys
import tempfile
import time
import locale
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['ELUCIDA_OCTET'] = '1'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from elucida.app import main_window as MW, project as PRJ
from elucida.core import chem as CHEM

folder = Path(tempfile.mkdtemp(prefix='elucida-new-compound-'))
MW.SETTINGS_FILE = folder / 'settings.ini'
app = QApplication([])
w = MW.MainWindow()
assert locale.setlocale(locale.LC_NUMERIC) == 'C', 'native chemistry must use decimal points after Qt startup'
w.resize(1400, 900)
w.show()


def click_ring(target, fx):
    point = QPoint(int(target.width() * fx), target.height() // 2)
    QTest.mouseMove(target, point)
    QTest.keyClick(target, Qt.Key_J)  # Octet's benzene tool
    QTest.qWait(150)
    QTest.mouseClick(target, Qt.LeftButton, pos=point)
    QTest.qWait(2600)                 # autosave 1 s + file watcher 0.8 s


def type_into(field, text):
    field.setFocus()
    field.selectAll()
    QTest.keyClicks(field, text) if text else QTest.keyClick(field, Qt.Key_Delete)
    QTest.keyClick(field, Qt.Key_Return)
    QTest.qWait(200)


try:
    assert w.create_project(folder / 'project')
    QTest.qWait(500)
    assert w._tab_keys[w.main_tabs.currentIndex()] == 'compound', 'a new compound opens in the Compound tab'
    path = PRJ.ensure_templates(w.project_dir)[0]
    assert not PRJ.cdxml_has_content(path), 'test must start with an empty document'
    tab = w.comp_tab
    editor = tab.drawing_editor
    deadline = time.monotonic() + 40
    while not (editor.ready and editor.path):
        assert time.monotonic() < deadline, f'Editor did not load: {folder}'
        QTest.qWait(100)
    QTest.qWait(300)
    saves = []
    editor.saved.connect(saves.append)
    target = editor.view.focusProxy() or editor.view
    editor.view.setFocus()
    click_ring(target, 0.5)
    print('saves', saves, 'dirty', editor.dirty, 'compound', w.compound, flush=True)
    w.grab().save(str(folder / 'new-compound.png'))
    assert saves and not editor.dirty, 'new molecule did not autosave'
    assert w.compound.get('formula') == 'C6H6', f'benzene formula missing: {folder}'
    assert abs(w.compound['mw'] - 78.11) < .02, f'benzene mass missing: {folder}'
    assert tab.fields['formula'].text() == 'C6H6' and tab.ed_mw.text() == '78.11', (tab.fields['formula'].text(), tab.ed_mw.text())
    assert Path(w.compound['structure']).resolve() == Path(path).resolve() and CHEM.load_cdxml(path)['formula'] == 'C6H6'
    steps = len(w._undo)
    QTest.qWait(1500)
    assert len(w._undo) == steps, 'the file watcher must not add a second undo step for the same save'
    # a molar mass entered by hand survives the next edit of the drawing, the formula still follows
    type_into(tab.ed_mw, '80')
    assert w.compound['mw'] == 80, w.compound
    editor.view.setFocus()
    click_ring(target, 0.75)
    print('second ring', w.compound, flush=True)
    assert w.compound['formula'] == 'C12H12' and w.compound['mw'] == 80, w.compound
    # cleared field: the drawn value again
    type_into(tab.ed_mw, '')
    assert abs(w.compound['mw'] - 156.22) < .03 and tab.ed_mw.text() == f"{w.compound['mw']:g}", (w.compound, tab.ed_mw.text())
    # invalid molar mass: old value stays
    type_into(tab.ed_mw, 'abc')
    assert abs(w.compound['mw'] - 156.22) < .03 and tab.ed_mw.text() == f"{w.compound['mw']:g}", (w.compound, tab.ed_mw.text())
    # name: applies on leaving the field and shows on the tab, undo takes it back
    type_into(tab.fields['name'], 'B-7')
    nav = w.nav_buttons[w._tab_keys.index('compound')]
    assert w.compound['name'] == 'B-7' and nav.full_text == 'B-7 · C₁₂H₁₂', (w.compound, nav.full_text)
    w.undo()
    QTest.qWait(800)
    assert not w.compound.get('name') and w._tab_keys[w.main_tabs.currentIndex()] == 'compound', w.compound
    assert w.comp_tab.fields['name'].text() == '' and w.comp_tab.fields['formula'].text() == 'C12H12'
    w.grab().save(str(folder / 'after-undo.png'))
    print('OK', folder, flush=True)
finally:
    w._restoring = True               # no questions while closing
    w.close()
