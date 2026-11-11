"""Native Qt/WebEngine regression for a free, data-backed Octet composition."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['ELUCIDA_OCTET'] = '1'
from PySide6.QtCore import QTimer, QPoint, QPointF, Qt, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from elucida.app import main_window as MW, publication as PUB, project as PRJ, reaction_paths as RP
from elucida.app import path_composition as PC
from elucida.tabs import dft as DFT, profile_orbitals as PO
from elucida.core import orbitals as ORB

folder = Path(tempfile.mkdtemp(prefix='elucida-path-composition-'))
MW.SETTINGS_FILE = folder/'settings.ini'
app = QApplication([])
w = MW.MainWindow()
w.show()
errors = []
qt_errors = []
original_hook = sys.excepthook
def record_error(kind, value, tb):
    qt_errors.append(str(value)); original_hook(kind, value, tb)
sys.excepthook = record_error
w.error = lambda message: errors.append(message)
w.exported = lambda _: None


def wait_for(predicate, seconds=45):
    end = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < end, 'Timed out waiting for editor'
        QTest.qWait(50)


try:
    pub = PUB.create(folder/'publication', 'Synthetic project')
    item = RP.create(pub, 'Synthetic composition')
    assert w.open_publication(pub)
    w.resize(1600,1000)
    w.pub_page.open_path(item)
    d = w.pub_page.path_workspace
    assert d.window() is w and not d.isWindow()
    t, pg = d.host.tab, d.host.tab.pages
    template = DFT.read_text(DFT.make_test_orca(folder/'template.out'))
    for name, delta in [('A', 0), ('TS', .02), ('B', -.03)]:
        text = template
        for value in ('-539.987654321098', '-539.98765432', '-539.91765432', '-539.91670987', '-539.94683332'):
            text = text.replace(value, f'{float(value)+delta:.{len(value.split(".")[1])}f}')
        path = folder/f'{name}.out'; path.write_text(text)
        t.load_xyz(str(path))
    c, editor = d.composition, d.composition.editor
    wait_for(lambda: editor.ready and editor.path)
    assert not d.profile.isVisible(), 'calculation page overlays the canvas'
    c.insert_profile()
    QTest.qWait(1000)                                    # zoom_fit folgt dem Rendern
    assert not errors, errors
    refs = editor._js('window.elucida.assets()')
    assert len(refs) == 1 and refs[0]['kind'] == 'profile'
    profile_key = refs[0]['key']
    svg = editor.path.with_suffix('.svg').read_text()
    assert 'elucida_' in svg and '<path' in svg
    with __import__('pymupdf').open(str(editor.path.with_suffix('.svg'))) as doc:
        assert doc[0].rect.width < 1500 and doc[0].rect.height < 1000, doc[0].rect
        assert len(doc[0].get_drawings()) > 5, 'profile was rasterized'
    # Octet move and update: preserve the placed object's box and independent ink.
    rect = editor._js("JSON.stringify(document.querySelector('[data-elucida-asset]').getBoundingClientRect().toJSON())")
    rect = json.loads(rect)
    size = editor._js('({w:innerWidth,h:innerHeight})')
    assert 0 <= rect['x'] < size['w'] and rect['x']+rect['width'] <= size['w']+2, (rect,size)
    assert 0 <= rect['y'] < size['h'] and rect['y']+rect['height'] <= size['h']+2, (rect,size)
    initial_box = ET.parse(editor.path).getroot().find('.//embeddedobject').get('BoundingBox')
    target = editor.view.focusProxy() or editor.view
    point = QPoint(int(rect['x']+rect['width']*.5), int(rect['y']+rect['height']*.5))
    QTest.mousePress(target, Qt.LeftButton, pos=point)
    QTest.qWait(100)
    end = point + QPoint(35,-25)
    app.sendEvent(target, QMouseEvent(QEvent.MouseMove, QPointF(end), QPointF(target.mapToGlobal(end)),
                                     Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    QTest.qWait(100)
    QTest.mouseRelease(target, Qt.LeftButton, pos=point+QPoint(35,-25))
    QTest.qWait(200)
    editor.save_sync()
    bbox = ET.parse(editor.path).getroot().find('.//embeddedobject').get('BoundingBox')
    assert bbox != initial_box, 'mouse drag did not move the figure'
    pg.prof['species'][t.entries()[1]['uid']] = dict(step=1, label='Transition state')
    try: PC.composition_blocks(d.host)
    except ValueError: pass
    else: raise AssertionError('stale profile silently exported')
    c.update_profiles()
    assert not errors, errors
    assert ET.parse(editor.path).getroot().find('.//embeddedobject').get('BoundingBox') == bbox
    assert editor._js('window.elucida.assets()')[0]['key'] != profile_key
    # Inline diagram layout edits are reversible and never change source energies.
    energies = [r['value'] for r in pg.levels_spec()[0]]
    profile_ref = editor._js('window.elucida.assets()')[0]
    c.edit_asset(profile_ref['key'], profile_ref['shapeId'])
    panel = c.diagram_editor
    assert panel and panel.window() is w and not panel.isWindow()
    QTest.qWait(100)
    w.grab().save(str(folder/'diagram-layout-ui.png'))
    assert not panel.fields['y'].isEnabled(), 'quantitative plot allows arbitrary heights'
    panel.fields['width'].setValue(1.1)
    panel.fields['x'].setValue(-.3)
    panel.changed()
    panel.presentation.setCurrentIndex(panel.presentation.findData('schematic'))
    panel.fields['y'].setValue(4.)
    panel.fields['label_dx'].setValue(5.)
    panel.break_after.setChecked(True)
    panel.set_color('#888888'); panel.changed()
    assert panel.fields['y'].isEnabled()
    assert c.finish_diagram(True)
    assert [r['value'] for r in pg.levels_spec()[0]] == energies
    changed_ref = editor._js('window.elucida.assets()')[0]
    layout = pg.prof['composition_assets'][changed_ref['key']]['layout']
    assert layout['mode'] == 'schematic' and layout['nodes'][t.entries()[0]['uid']]['width'] == 1.1
    assert 'vertical spacing is not to scale' in PC.composition_blocks(d.host)[-1][1]
    c.caption.setText('Synthetic custom caption'); c.save_caption()
    assert 'vertical spacing is not to scale' in PC.composition_blocks(d.host)[-1][1]
    w.undo(); QTest.qWait(100)
    assert editor._js('window.elucida.assets()')[0]['key'] == profile_ref['key']
    w.redo(); QTest.qWait(100)
    c.update_profiles()
    updated_ref = editor._js('window.elucida.assets()')[0]
    assert pg.prof['composition_assets'][updated_ref['key']]['layout'] == layout
    c.edit_asset(updated_ref['key'], updated_ref['shapeId'])
    c.diagram_editor.fields['width'].setValue(1.8); c.diagram_editor.changed()
    c.finish_diagram(False)
    assert editor._js('window.elucida.assets()')[0]['key'] == updated_ref['key']
    # Independent orbital snapshot; the immutable old revision survives Octet undo.
    e = t.load_cube(str(ORB.make_test_cube(folder/'orbital.cube', n=24)))
    view = PO.snapshot(t, e, 0)
    shape = c.put(*PC.orbital_asset(d.host, view))
    assert len(editor._js('window.elucida.assets()')) == 2
    editor.command('undo'); QTest.qWait(100)
    assert len(editor._js('window.elucida.assets()')) == 1
    editor.command('redo'); QTest.qWait(100)
    refs = editor._js('window.elucida.assets()')
    assert len(refs) == 2
    ref = next(r for r in refs if r['kind'] == 'orbital')
    c.edit_asset(ref['key'], ref['shapeId'])
    dialog = c.view_editor
    assert dialog and dialog.window() is w and not dialog.isWindow()
    frozen_view = json.dumps(dialog.data, sort_keys=True)
    w.set_canvas_mode('dark'); QTest.qWait(150)
    assert dialog.canvas._canvas_invert.isEnabled()
    dark_view = dialog.canvas.grab().toImage()
    assert dark_view.pixelColor(5,5).name() == '#000000', dark_view.pixelColor(5,5).name()
    w.set_canvas_mode('light'); QTest.qWait(100)
    assert not dialog.canvas._canvas_invert.isEnabled()
    assert json.dumps(dialog.data, sort_keys=True) == frozen_view
    dialog.data['alpha'] = .1
    dialog.reject()
    assert pg.prof['composition_assets'][ref['key']]['orbital']['alpha'] == view['alpha']
    geometry = PO.snapshot(t, t.entries()[0], None)
    assert geometry['show_orbital'] is False
    assert PC.orbital_asset(d.host, geometry)[0]['png'].startswith('89504e47')
    # Host-loaded vector payloads remain inert, including imported native files.
    unsafe = dict(key='synthetic-unsafe', kind='profile', width=40, height=40,
                  png=PC.orbital_asset(d.host, view)[0]['png'],
                  svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
                      '<script>window.untrustedExecuted=1</script><foreignObject width="40" height="40">'
                      '<div xmlns="http://www.w3.org/1999/xhtml">bad</div></foreignObject>'
                      '<path d="M0 0L40 40" onclick="window.untrustedExecuted=1"/>'
                      '<image href="https://invalid.example/track.png" width="40" height="40"/>'
                      '<rect width="40" height="40" style="fill:url(https://invalid.example/x);position:fixed"/></svg>')
    editor._js(f'window.elucida.putAsset({json.dumps(unsafe)})')
    safe = editor._js("document.querySelector('[data-elucida-asset=synthetic-unsafe]').outerHTML")
    assert not any(x in safe for x in ('<script','foreignObject','onclick','invalid.example','position:fixed')), safe
    assert not editor._js('!!window.untrustedExecuted')
    editor.command('undo'); QTest.qWait(100)
    # Free chemical drawing on the same canvas, using the normal Octet shortcut.
    editor.command('zoom_fit'); QTest.qWait(200)
    point = QPoint(target.width()-100, target.height()-100)
    QTest.mouseMove(target, point); QTest.keyClick(target, Qt.Key_J); QTest.qWait(100)
    QTest.mouseClick(target, Qt.LeftButton, pos=point); QTest.qWait(200)
    assert editor.save_sync()
    assert ET.parse(editor.path).getroot().find('.//fragment') is not None
    light = editor._js('window.elucida.snapshot()')['svg']
    w.set_canvas_mode('dark'); QTest.qWait(100)
    dark = editor._js('window.elucida.snapshot()')['svg']
    assert light == dark, 'display inversion leaked into SVG'
    w.set_canvas_mode('light')
    QTest.qWait(200)
    files = c.export()
    assert {p.suffix for p in files} == {'.pdf','.svg','.png','.cdxml','.cdx'}
    with __import__('pymupdf').open(str(next(p for p in files if p.suffix=='.pdf'))) as doc:
        assert doc[0].rect.width < 1500 and doc[0].rect.height < 1000, doc[0].rect
    assert len(RP.si_blocks(w,pub)) == 3, 'whole composition should be a single SI figure'
    from elucida.si import lines as SI
    from elucida.formats.ole import editable_directory
    docx = folder/'composition.docx'
    SI.write_docx(docx, RP.si_blocks(w,pub))
    assert list(editable_directory(docx).glob('*.cdxml')) and list(editable_directory(docx).glob('*.cdx'))
    w.grab().save(str(folder/'composition-ui.png'))
    for theme in ('light', 'dark'):
        w.switch_theme(theme)
        d = w.pub_page.path_workspace
        c, editor = d.composition, d.composition.editor
        t, pg = d.host.tab, d.host.tab.pages
        wait_for(lambda: editor.ready and editor.path)
        QTest.qWait(200)
        assert len(editor._js('window.elucida.assets()')) == 2
        visible = editor._js("Array.from(document.querySelectorAll('[data-elucida-asset]')).map(e => {const r=e.getBoundingClientRect(); return r.width>0 && r.height>0 && r.left>=0 && r.top>=0 && r.right<=innerWidth+2 && r.bottom<=innerHeight+2})")
        assert len(visible) == 2 and all(visible), 'reopened composition clipped its figures'
        w.grab().save(str(folder/f'composition-ui-{theme}.png'))
    d.calculations(); QTest.qWait(100)
    assert d.tabs.currentWidget() is d.host.tab and d.host.tab.window() is w
    d.tabs.setCurrentWidget(c)
    assert w.save_project()
    d.accept(); QTest.qWait(100)
    assert w.pub_page.path_workspace is None
    # Portable copy includes canvas, native payload, orbital files and settings.
    source = RP.directory(pub,item['uid'])
    copied = PRJ.save(folder/'copy', PRJ.load(source))
    assert not PRJ.missing_files(copied)
    copied_view = next(a['orbital'] for a in copied['dft']['profile']['composition_assets'].values() if a['kind']=='orbital')
    assert Path(copied_view['source']['file']).is_relative_to((folder/'copy').resolve())
    w.pub_page.open_path(item); d2 = w.pub_page.path_workspace
    wait_for(lambda:d2.composition.editor.ready and d2.composition.editor.path)
    ed2 = d2.composition.editor
    assert len(ed2._js('window.elucida.assets()')) == 2
    ed2.command('select_all'); QTest.qWait(100)
    target2 = ed2.view.focusProxy() or ed2.view
    target2.setFocus(); QTest.keyClick(target2, Qt.Key_Backspace); QTest.qWait(100)
    assert ed2.save_sync()
    assert PC.composition_blocks(d2.host) == [], 'clearing canvas resurrected automatic profile'
    ed2.command('undo'); QTest.qWait(100); assert ed2.save_sync()
    # Theme/UI rebuild preserves the selected project tab and saved composition.
    w.build_ui(); QTest.qWait(100)
    d3 = w.pub_page.path_workspace
    assert d3 and d3.window() is w
    wait_for(lambda:d3.composition.editor.ready and d3.composition.editor.path)
    assert len(d3.composition.editor._js('window.elucida.assets()')) == 2
    assert w.go_home() is not False
    assert w.pub_page.path_workspace is None
    assert not errors, errors
    assert not qt_errors, qt_errors
    print('OK: native composition, vector profile, update/move, orbital undo/edit, free drawing, SI, copy, reopen',folder,flush=True)
finally:
    MW.release_widgets(app)
