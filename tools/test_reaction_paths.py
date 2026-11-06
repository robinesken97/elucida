"""Synthetic project-path import, persistence, undo, removal and SI regressions."""
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QListWidget
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from elucida.app import main_window as MW, project as PRJ, publication as PUB, reaction_paths as RP
from elucida.app.publication_view import PublicationSIDialog
from elucida.tabs import dft as DFT
from elucida.core import orbitals as ORB
from elucida.si import publication_si as PSI, lines as SI


def fail(message):
    raise AssertionError(message)


folder = Path(tempfile.mkdtemp(prefix='elucida-reaction-paths-'))
MW.SETTINGS_FILE = folder / 'settings.ini'
app = QApplication([])
w = MW.MainWindow()
w.error = fail
w.exported = lambda _: None
w.show()
try:
    pub = PUB.create(folder / 'publication', 'Synthetic project')
    assert w.create_project(pub / 'Synthetic compound')
    PUB.add_compound(pub, w.project_dir)
    w.dft_tab.load_xyz(str(DFT.make_test_orca(folder / 'calc.out')))
    w.dft_tab.load_cube(str(ORB.make_test_cube(folder / 'orb.cube', n=20)))
    w.save_project()
    original = deepcopy(w.dft_tab.st)
    compound_file = PRJ.project_file(w.project_dir)
    original_bytes = compound_file.read_bytes()
    item = RP.create(pub, 'Synthetic pathway')
    assert [d.resolve() for d in PUB.sync(pub)[0]] == [Path(w.project_dir).resolve()], 'path directory mistaken for compound'
    dialog = RP.PathWorkspace(w, pub, item)
    dialog.show()
    QTest.qWait(100)

    dialog.from_compounds()
    dialog.import_list.selectAll()
    dialog.import_selected()
    host, pg = dialog.host, dialog.host.tab.pages
    assert len(host.tab.entries()) == len(original['entries'])
    assert not ({e['uid'] for e in host.tab.entries()} & {e['uid'] for e in original['entries']})
    for entry in host.tab.entries():
        assert entry['origin']['compound'] == 'Synthetic compound'
        for path in [entry['file']] + [o['file'] for o in entry.get('orbitals', [])]:
            assert Path(path).is_relative_to(host.project_dir.resolve()) and Path(path).is_file()
    assert w.dft_tab.st == original and compound_file.read_bytes() == original_bytes
    assert pg.levels_spec()[0]
    pg.tbl_sp.selectRow(0)
    uid = host.tab.entries()[0]['uid']
    uid_ = pg.tbl_sp.item(pg.tbl_sp.currentRow(), 0).data(Qt.UserRole)
    pg.prof['species'][uid_] = dict(pg.prof['species'].get(uid_, {}), label='TS1', step=3)
    pg.remove_level()
    pg.cmb_level_restore.setCurrentIndex(pg.cmb_level_restore.findData(uid_))
    pg.restore_level()
    assert pg.prof['species'][uid_]['label'] == 'TS1' and pg.prof['species'][uid_]['step'] == 3
    before = deepcopy(host.state)
    pg.sync(); pg.tbl_sp.selectRow(next(i for i in range(pg.tbl_sp.rowCount()) if pg.tbl_sp.item(i, 0).data(Qt.UserRole) == uid_))
    pg.remove_level()
    assert uid not in {e['uid'] for e in pg.profile_entries()}
    assert any(e['uid'] == uid for e in host.tab.entries()), 'removed raw calculation'
    host.restore(-1)
    assert host.state == before
    host.restore(1)
    assert uid not in {e['uid'] for e in pg.profile_entries()}
    host.restore(-1)
    assert host.save()
    pg.refresh()
    QTest.qWait(100)
    pg.canvas.draw()
    ratio = pg.canvas.device_pixel_ratio
    assert pg.canvas.buffer_rgba().shape[:2] == (int(pg.canvas.height()*ratio), int(pg.canvas.width()*ratio))
    dialog.grab().save(str(folder / 'workspace.png'))
    # Companion viewer may open/close without deleting or reparenting away the profile.
    dialog.calculations()
    assert dialog.tabs.currentWidget() is host.tab
    dialog.tabs.setCurrentWidget(pg.prof_group)
    assert not pg.prof_group.isWindow()
    dialog.accept()
    dialog.deleteLater()
    QTest.qWait(50)
    loaded = PRJ.load(RP.directory(pub, item['uid']))
    assert loaded['dft']['entries'][0]['origin']['compound'] == 'Synthetic compound'
    RP.set_removed(pub, item['uid'], True)
    assert not PUB.load(pub).get('reaction_paths')
    assert RP.directory(pub, item['uid']).is_dir()
    RP.set_removed(pub, item['uid'], False)
    assert PUB.load(pub)['reaction_paths'] == [item]
    # One project-wide section; compounds and the original open viewer remain independent.
    paths = RP.si_blocks(w, pub)
    assert sum(b[0] == 'image' for b in paths) == 1
    assert w.dft_tab.st == original
    meta = PUB.load(pub)
    meta['si_texts'] = {'dft': 'Synthetic computational methods.'}
    comps = [('A', {'dft': [('heading', 'Individual calculation A')]}),
             ('B', {'dft': [('heading', 'Individual calculation B')]})]
    for position in ('before', 'after'):
        meta['reaction_paths_si'] = dict(include=True, position=position)
        blocks = PSI.assemble(meta, comps, ['dft'], toc=False, reaction_paths=paths)
        assert sum(b == ('heading', 'Synthetic pathway') for b in blocks) == 1
        path_index = blocks.index(('heading', 'Synthetic pathway'))
        calc_index = blocks.index(('heading', 'Individual calculation A'))
        assert (path_index < calc_index) == (position == 'before')
        intro = next(b for b in blocks if b[0] == 'char')
        assert 'Synthetic computational methods' in intro[1] and blocks.index(intro) < path_index
        assert next(b for b in reversed(blocks[:path_index]) if b[0] == 'columns') == ('columns', 1)
        outfile = folder / f'paths-{position}.docx'
        SI.write_docx(outfile, blocks)
        with ZipFile(outfile) as z:
            doc = z.read('word/document.xml').decode()
            assert doc.count('Synthetic pathway') == 2  # heading and caption
            assert 'Individual calculation A' in doc and 'w:num="2"' in doc
    meta['reaction_paths_si']['include'] = False
    assert ('heading', 'Synthetic pathway') not in PSI.assemble(meta, comps, ['dft'], reaction_paths=paths)
    assert ('heading', 'Synthetic pathway') not in PSI.assemble(meta, comps, ['nmr'], reaction_paths=paths)
    # A project containing paths only is still exportable through the real main-window entry point.
    out = w.export_publication_si(pub, [], ['dft'], toc=False, path=folder/'paths-only.docx')
    assert out and out.exists()
    chooser = PublicationSIDialog(w, pub)
    chooser.cbs['dft'].setChecked(False)
    assert not chooser.cb_paths.isEnabled() and not chooser.cmb_paths.isEnabled()
    chooser.reject(); chooser.deleteLater()
    assert compound_file.read_bytes() == original_bytes
    print('Project import isolation, files, undo, removal/restore, SI order and inclusion: OK', flush=True)
    print(folder, flush=True)
finally:
    w._closing = True
    w.close()
    MW.release_widgets(app)
