"""Synthetic GUI regression: profile redraw at HiDPI, assigned structures and portable exports."""
import io
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['ELUCIDA_OCTET'] = '1'
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QTimer, QPoint, Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from elucida.app import main_window as MW, project as PRJ
from elucida.app.demo import mol_cdxml
from elucida.app.canvas_theme import configure
from elucida.tabs import dft as DFT
from rdkit import Chem
from rdkit.Chem import AllChem

folder = Path(tempfile.mkdtemp(prefix='elucida-dft-profile-'))
MW.SETTINGS_FILE = folder / 'settings.ini'
app = QApplication([])
w = MW.MainWindow()
w.show()

def figure():
    fig = Figure()
    FigureCanvasAgg(fig)
    return fig

try:
    assert w.create_project(folder / 'project')
    tab = w.dft_tab
    template = Path(DFT.make_test_orca(folder / 'template.out')).read_bytes()[2:].decode('utf-16-le')
    for label, delta in [('A', 0), ('TS', .03), ('B', -.02)]:
        text = template
        for value in ('-539.987654321098', '-539.98765432', '-539.91765432', '-539.91670987', '-539.94683332'):
            text = text.replace(value, f'{float(value)+delta:.{len(value.split(".")[1])}f}')
        path = folder / (label+'.out')
        path.write_bytes(b'\xff\xfe'+text.encode('utf-16-le'))
        tab.load_xyz(str(path))
    pg = tab.pages
    w.main_tabs.setCurrentWidget(tab)
    # Show this real tab's profile page independently of tab-bar labels/language.
    pg.prof_group.setParent(None)
    pg.prof_group.resize(1150, 850)
    pg.prof_group.show()
    QTest.qWait(200)
    pg.refresh()
    QTest.qWait(200)
    values = [r['value'] for r in pg.levels_spec()[0]]
    for size in [(1150, 850), (720, 600), (1000, 720)]:
        pg.prof_group.resize(*size)
        QTest.qWait(100)
        pg.refresh()
        QTest.qWait(100)
        pg.canvas.draw()
        buffer = pg.canvas.buffer_rgba()
        ratio = pg.canvas.device_pixel_ratio
        assert buffer.shape[1] == int(pg.canvas.width()*ratio), 'renderer/widget width mismatch'
        assert buffer.shape[0] == int(pg.canvas.height()*ratio), 'renderer/widget height mismatch'
    molecule = Chem.MolFromSmiles('c1ccccc1')
    AllChem.Compute2DCoords(molecule)
    structure = folder / 'benzene.cdxml'
    structure.write_text(mol_cdxml(molecule))
    uid = pg.items()[1]['uid']
    pg.assign_structure(uid, structure)
    QTest.qWait(200)
    assert [r['value'] for r in pg.levels_spec()[0]] == values, 'structures changed energies'
    F, notes = pg.build_levels(figure())
    assert not notes, notes
    key = 'image_profile_'+uid
    assert key in F.axes_items
    image_ax = F.axes_items[key]
    assert image_ax._vector is not None, 'structure lost vector export'
    assert image_ax.get_position().y1 <= F.ax.get_position().y1+.01, 'structure extends outside axes'
    blob = io.BytesIO()
    F.fig.savefig(blob, format='png')
    light = blob.getvalue()
    configure(True)
    QTest.qWait(100)
    blob = io.BytesIO()
    F.fig.savefig(blob, format='png')
    assert blob.getvalue() == light, 'canvas inversion changed export'
    w.save_project()
    loaded = PRJ.load(w.project_dir)
    assert Path(loaded['dft']['profile']['species'][uid]['structure']).exists()
    PRJ.save(folder / 'copied-project', loaded)
    moved = PRJ.load(folder / 'copied-project')['dft']['profile']['species'][uid]['structure']
    assert Path(moved).is_relative_to((folder/'copied-project').resolve()) and Path(moved).exists()
    F.cfg['output'] = str(folder / 'profile.pdf')
    F.cfg['extra_formats'] = ['svg', 'png']
    F.export()
    assert all((folder/f'profile.{ext}').is_file() for ext in ('pdf','svg','png'))
    assert any(b[0]=='image' for b in pg.si_figures(folder,'Synthetic'))
    configure(False)
    QTest.qWait(100)
    pg.prof_group.grab().save(str(folder/'profile-ui.png'))
    pg.remove_structure(uid)
    assert key not in pg.build_levels(figure())[0].axes_items
    # Real per-plateau drawing dialog: blank file -> benzene -> autosave -> Close.
    from elucida.app.drawing_editor import DrawingDialog
    errors = []
    deadline = time.monotonic()+45
    def draw_plateau():
        dialog = next((d for d in app.topLevelWidgets() if isinstance(d, DrawingDialog)), None)
        try:
            assert time.monotonic()<deadline, 'plateau editor did not load'
            if dialog is None or not (dialog.editor.ready and dialog.editor.path):
                QTimer.singleShot(100, draw_plateau)
                return
            editor=dialog.editor
            target=editor.view.focusProxy() or editor.view
            editor.view.setFocus()
            point=QPoint(target.width()*2//3,target.height()//2)
            QTest.mouseMove(target,point)
            QTest.keyClick(target,Qt.Key_J)
            QTest.qWait(100)
            QTest.mouseClick(target,Qt.LeftButton,pos=point)
            QTest.qWait(1800)
            assert not editor.dirty and PRJ.cdxml_has_content(editor.path)
            dialog.reject()
        except Exception as ex:
            errors.append(ex)
            if dialog:
                dialog.reject()
    QTimer.singleShot(100,draw_plateau)
    pg.draw_structure(uid)
    if errors:
        raise errors[0]
    assert key in pg.build_levels(figure())[0].axes_items, 'drawing not assigned to plateau'
    pg.prof_group.close()
    pg.prof_group.deleteLater()
    print('OK: profile redraw/HiDPI, plateau structure, project copy, PDF/SVG/PNG/SI, theme-neutral export',folder,flush=True)
finally:
    MW.release_widgets(app)
