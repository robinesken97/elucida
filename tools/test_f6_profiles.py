"""Synthetic GUI + export regressions for MR selection and independent profile views."""
import io
import json
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest
from PySide6.QtCore import QTimer
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from elucida.app import main_window as MW, project as PRJ
from elucida.app.canvas_theme import configure
from elucida.tabs import dft as DFT, profile_orbitals as PO
from elucida.tabs.profile_annotations import AnnotationDialog
from elucida.formats.multireference import make_test_mr
from elucida.core import orbitals as ORB


def figure():
    f = Figure(); FigureCanvasAgg(f); return f


folder = Path(tempfile.mkdtemp(prefix="elucida-f6-profiles-"))
MW.SETTINGS_FILE = folder / "settings.ini"
app = QApplication([])
w = MW.MainWindow()
w.show()
try:
    assert w.create_project(folder / "project")
    t = w.dft_tab
    template = DFT.read_text(DFT.make_test_orca(folder / "calc.out"))
    for name, delta in (("A", 0), ("TS", .03), ("B", -.02)):
        text = template
        for value in ('-539.987654321098', '-539.98765432', '-539.91765432', '-539.91670987', '-539.94683332'):
            text = text.replace(value, f'{float(value)+delta:.{len(value.split(".")[1])}f}')
        p = folder / f"{name}.out"; p.write_text(text)
        t.load_xyz(str(p))
    pg = t.pages
    values = [r['value'] for r in pg.levels_spec()[0]]
    uid = t.entries()[1]['uid']
    e = t.load_cube(str(ORB.make_test_cube(folder / 'synthetic.cube', n=24)))
    view = PO.snapshot(t, e, 0)
    json.dumps(view)
    pg.prof['annotations'] = [dict(uid='orb1', mode='levels', anchor=dict(species=uid),
                                   kind='orbital', orbital=view, label='Synthetic orbital', width=.18,
                                   offset=[-.09, .085])]
    F, notes = pg.build_levels(figure())
    assert not notes, notes
    assert 'image_annotation_orb1' in F.axes_items
    assert [r['value'] for r in pg.levels_spec()[0]] == values
    first = PO.asset(t, view)['rgba'].copy()
    t.st.update(orb_frac=65, orb_alpha=.2, radius=.4, bg='black')
    e['view'] = [1,0,0,0,-1,0,0,0,-1]
    t.main.extra_cache = {}  # force a rebuild; cached pixels cannot hide accidental live links
    second = PO.asset(t, view)['rgba']
    assert (first == second).all(), 'main viewer changed captured view'
    print('Independent orbital rendering: OK', flush=True)
    d = PO.OrbitalViewDialog(t, view)
    d.data['alpha'] = .12
    d.reject()
    assert view['alpha'] != .12
    d.deleteLater()
    manager = AnnotationDialog(pg)
    manager.items[0]['width'] = .3
    manager.reject()
    assert pg.prof['annotations'][0]['width'] == .18
    manager.deleteLater()
    pg.prof['size_cm'] = [30., 18.]
    F, notes = pg.build_levels(figure())
    assert not notes, notes
    assert abs(F.fig.get_figwidth()*2.54-30) < 1e-8
    stream = io.BytesIO(); F.fig.savefig(stream, format='png'); before = stream.getvalue()
    configure(True)
    stream = io.BytesIO(); F.fig.savefig(stream, format='png')
    assert before == stream.getvalue(), 'display inversion changed export'
    configure(False)
    F.cfg.update(output=str(folder/'profile.pdf'), extra_formats=['svg','png'])
    F.export()
    assert all((folder/f'profile.{ext}').is_file() for ext in ('pdf','svg','png'))
    # Known synthetic IRC data at stable IDs exercises both mode-specific builders.
    import numpy as np
    irc = dict(uid='curve1', label='Synthetic IRC', method='Test', s=np.array([-1.,0.,1.]),
               E=np.array([-10.,-9.99,-10.01]), ts=1, cols={})
    pg.irc_data = lambda: ([irc], [])
    pg.prof['annotations'].append(dict(uid='orb2', mode='irc', anchor=dict(irc='curve1', frame=1),
                                      kind='orbital', orbital=deepcopy(view), width=.2, offset=[-.1,.08]))
    F, notes = pg.build_irc(figure())
    assert not notes, notes
    assert 'image_annotation_orb2' in F.axes_items and 'image_annotation_orb1' not in F.axes_items
    w.save_project()
    saved = PRJ.load(w.project_dir)
    PRJ.save(folder/'copy', saved)
    copied = PRJ.load(folder/'copy')
    a = copied['dft']['profile']['annotations'][0]
    assert Path(a['orbital']['source']['file']).is_relative_to((folder/'copy').resolve())
    assert Path(a['orbital']['source']['file']).is_file()
    assert a['orbital']['source_sha256'] == view['source_sha256']
    print('Level/IRC anchors, PDF/SVG/PNG, display theme, project copy: OK', flush=True)
    # MR page selection is propagated identically into preview and Word blocks.
    mr = DFT.read_text(make_test_mr(folder/'mr.out'))
    p = folder/'mr_geometry.out'; p.write_text(template + '\n' + mr)
    t.load_xyz(str(p)); e = t.entry(); page = t.mr_page
    page.choice.setCurrentIndex(2); page.si.setChecked(True)
    assert e['mr_result'] == 'mr-1'
    parts = t.si_of(e)
    assert parts['energies'] is None
    assert 'SC-NEVPT2' in DFT.si_plain(parts) and '-10.300000000123'.replace('-', '−') in DFT.si_plain(parts)
    assert '-10.310000000123'.replace('-', '−') not in DFT.si_plain(parts)
    out = t.save_docx(folder/'mr.docx'); assert out.exists()
    print('MR UI / SI selection and Word: OK', flush=True)
    # Workspace zoom changes display dimensions only; modal returns the original widget.
    pg.prof_group.setParent(None); pg.prof_group.resize(1150,850); pg.prof_group.show()
    QTest.qWait(100); pg.refresh(); QTest.qWait(100)
    pg.workspace.zoom.setCurrentIndex(3); QTest.qWait(100)
    assert pg.prof['size_cm'] == [30.,18.]
    pg.canvas.draw()
    assert abs(pg.canvas.buffer_rgba().shape[1] - pg.canvas.width()*pg.canvas.device_pixel_ratio) <= 2
    pg.prof_group.grab().save(str(folder/'profile-ui.png'))
    pg.prof_group.close()
    # Changing an underlying orbital file is detected rather than silently repainting it.
    source = Path(view['source']['file']); source.write_bytes(source.read_bytes()+b'\n')
    try: PO.asset(t,view)
    except ValueError: pass
    else: raise AssertionError('changed source silently reused')
    print('Workspace / file-change guard: OK', flush=True)
    print(folder, flush=True)
finally:
    w._closing = True; w.close()
    MW.release_widgets(app)
