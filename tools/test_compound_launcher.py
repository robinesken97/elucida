"""Exercise the real preview launcher and modal Compound workflow on synthetic data.

Run on macOS with LANG=de_DE.UTF-8 to cover the reported comma-locale failure.
The user's preview, settings and molecules are never opened or modified.
"""
import os
import runpy
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['ELUCIDA_PREVIEW_DIR'] = tempfile.mkdtemp(prefix='elucida-launcher-test-')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt, QPoint
from PySide6.QtTest import QTest
from elucida.app import main_window as MW

failures = []
original_dialog = MW.CompoundDialog


class ProbeDialog(original_dialog):
    def __init__(self, *args):
        super().__init__(*args)
        self.deadline = time.monotonic() + 35
        QTimer.singleShot(100, self.probe)

    def probe(self):
        try:
            editor = self.drawing_editor
            if not (editor.ready and editor.path):
                assert time.monotonic() < self.deadline, 'editor did not load: ' + editor.status.text()
                QTimer.singleShot(100, self.probe)
                return
            assert self.ed_formula.text() == 'C6H6' and self.ed_mw.text() == '78.11', 'existing drawing properties missing'
            self.activateWindow()
            editor.view.setFocus()
            target = editor.view.focusProxy() or editor.view
            editor.command('select_all')
            QTest.qWait(150)
            QTest.keyClick(target, Qt.Key_Backspace)
            QTest.qWait(1800)
            assert not self.ed_formula.text() and not self.ed_mw.text(), 'deleted molecule kept stale properties'
            point = QPoint(target.width()*2//3, target.height()//2)
            QTest.mouseMove(target, point)
            QTest.keyClick(target, Qt.Key_J)
            QTest.qWait(150)
            QTest.mouseClick(target, Qt.LeftButton, pos=point)
            QTest.qWait(2000)
            assert self.ed_formula.text() == 'C6H6' and self.ed_mw.text() == '78.11', 'redrawn molecule did not fill properties'
            self.accept()
        except Exception:
            failures.append(traceback.format_exc())
            print(failures[-1], flush=True)
            self.reject()


MW.CompoundDialog = ProbeDialog
original_exec = QApplication.exec


def check():
    try:
        w = next(w for w in QApplication.topLevelWidgets() if isinstance(w, MW.MainWindow))
        path = Path(w.chemdraw_file('structure'))
        # Explicit decimals: a comma locale collapses these RDKit coordinates.
        points = [(100.5, 100.5), (113.0, 107.7), (113.0, 122.1),
                  (100.5, 129.3), (88.0, 122.1), (88.0, 107.7)]
        nodes = ''.join(f'<n id="{i+2}" p="{x} {y}" Element="6"/>' for i, (x, y) in enumerate(points))
        bonds = ''.join(f'<b id="{i+8}" B="{i+2}" E="{(i+1)%6+2}" Order="{2 if i%2==0 else 1}"/>' for i in range(6))
        path.write_text('<CDXML BondLength="14.4"><page id="1"><fragment id="20">' + nodes + bonds + '</fragment></page></CDXML>')
        w.set_compound(dict(structure=str(path), formula='', mw=None))
        w.save_project()
        w.open_project(w.project_dir, ask=False, recent=False)
        for _ in range(2):
            w.edit_compound()
            assert w.compound['formula'] == 'C6H6' and w.compound['mw'] == 78.11
            w.save_project()
        print('OK: real launcher; loaded project; modal delete/redraw/OK/reopen; formula and mass', flush=True)
    except Exception:
        failures.append(traceback.format_exc())
        print(failures[-1], flush=True)
    QApplication.instance().exit(bool(failures))


def test_exec(self):
    QTimer.singleShot(2000, check)
    QTimer.singleShot(60000, lambda: self.exit(3))
    return original_exec()


QApplication.exec = test_exec
runpy.run_path(str(ROOT / 'tools/run_octet_preview.py'), run_name='__main__')
