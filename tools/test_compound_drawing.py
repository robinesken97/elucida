"""GUI regression for the inline compound editor, Cancel, OK and macOS title chrome."""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['ELUCIDA_OCTET'] = '1'
from PySide6.QtWidgets import QApplication, QDialog, QMenu
from PySide6.QtTest import QTest
from elucida.app import main_window as MW, project as PRJ, macos as MAC
from elucida.app.demo import mol_cdxml
from rdkit import Chem
from rdkit.Chem import AllChem

folder = Path(tempfile.mkdtemp(prefix='elucida-compound-test-'))
MW.SETTINGS_FILE = folder / 'settings.ini'
app = QApplication([])
w = MW.MainWindow()
w.show()

def ready(editor):
    deadline = time.monotonic() + 40
    while not (editor.ready and editor.path):
        if time.monotonic() > deadline:
            editor.window().grab().save(str(folder / 'load-failure.png'))
            raise AssertionError(f'Editor did not load: ready={editor.ready}, path={editor.path}, status={editor.status.text()}, artifacts={folder}')
        QTest.qWait(100)
    QTest.qWait(300)

def change(editor):
    editor.command('select_all')
    QTest.qWait(100)
    editor.command('flip_h')
    QTest.qWait(1600)
    assert not editor.dirty, 'draft autosave failed'

try:
    assert w.create_project(folder / 'project')
    path = PRJ.ensure_templates(w.project_dir)[0]
    molecule = Chem.MolFromSmiles('CCO')
    AllChem.Compute2DCoords(molecule)
    path.write_text(mol_cdxml(molecule), encoding='utf-8')
    w.set_compound(dict(name='Test', structure=str(path)))
    before = path.read_bytes()
    for accept in (False, True):
        dlg = MW.CompoundDialog(w, w.compound)
        dlg.show()
        ready(dlg.drawing_editor)
        assert dlg.drawing_editor.isVisible()
        assert dlg.ed_formula.text() == 'C2H6O', 'existing structure did not fill formula'
        assert abs(float(dlg.ed_mw.text()) - 46.069) < .02, 'existing structure did not fill mass'
        assert '<fragment' in dlg.drawing_editor._js('window.elucida.snapshot()')['cdxml']
        assert all(a.text() != MW.T('draw_copy_table') for m in dlg.drawing_editor.findChildren(QMenu) for a in m.actions())
        dlg.ed_formula.clear()
        dlg.ed_mw.clear()
        change(dlg.drawing_editor)
        assert dlg.ed_formula.text() == 'C2H6O', 'autosave did not update formula beside the editor'
        assert abs(float(dlg.ed_mw.text()) - 46.069) < .02, 'autosave did not update mass'
        assert path.read_bytes() == before, 'draft changed original before OK'
        dlg.grab().save(str(folder / 'compound.png'))
        if accept:
            dlg.ed_mw.setText('47.00')  # Explicit manual override after drawing autosave.
        dlg.done(QDialog.Accepted if accept else QDialog.Rejected)
        assert (path.read_bytes() != before) == accept, 'Cancel/OK persistence mismatch'
        if accept:
            assert path.with_suffix('.cdx').is_file()
            assert dlg.result_compound()['structure'] == str(path)
            assert dlg.result_compound()['mw'] == 47.0, 'OK replaced a manual mass correction'
        dlg.cleanup()
        dlg.deleteLater()
        QTest.qWait(100)
    w.setWindowTitle('Title update regression')
    QTest.qWait(200)
    if MAC.enabled() and w._title_h:
        assert MAC._msg(MAC._msg(int(w.winId()), 'window'), 'titleVisibility') == MAC._NS_TITLE_HIDDEN
    w.grab().save(str(folder / 'main.png'))
    print('OK: inline compound; draft autosave; Cancel preserves original; OK publishes; title hidden', folder, flush=True)
finally:
    MW.release_widgets(app)
