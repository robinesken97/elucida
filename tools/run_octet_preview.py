"""Start the experimental integration with isolated settings and a synthetic project."""
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ['ELUCIDA_OCTET'] = '1'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from elucida.app import main_window as MW
from elucida.app.demo import scheme_cdxml
from elucida.app import project as PRJ

if not (ROOT / 'assets/octet/embedded.html').exists():
    raise SystemExit('First run: python tools/build_octet.py')
import tempfile
preview = (Path(os.environ['ELUCIDA_PREVIEW_DIR']).resolve() if os.environ.get('ELUCIDA_PREVIEW_DIR') else
           Path(tempfile.mkdtemp(prefix='elucida-key-test-')) if '--smoke-keys' in sys.argv else ROOT / '.octet-preview')
preview.mkdir(exist_ok=True)
# Keep failures from the normal .command/.cmd workflow inspectable. No drawing
# contents or calculated properties are recorded; the file stays in the preview.
import hashlib
import logging
from logging.handlers import RotatingFileHandler
diagnostics = logging.getLogger('elucida.drawing')
diagnostics.setLevel(logging.INFO)
handler = RotatingFileHandler(preview / 'drawing-diagnostics.log', maxBytes=1_000_000, backupCount=1, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
diagnostics.addHandler(handler)
diagnostics.info('Start pid=%s python=%s source=%s sha256=%s', os.getpid(), sys.executable,
                 MW.__file__, hashlib.sha256(Path(MW.__file__).read_bytes()).hexdigest())
MW.SETTINGS_FILE = preview / 'settings.ini'
app = QApplication(sys.argv[:1])
w = MW.MainWindow()
w.show()
project = preview / 'project'
if not (project / 'project.elucida').exists():
    if not w.create_project(project):
        raise SystemExit('Could not create the preview project')
    path = project / PRJ.STRUCTURES / 'test-reaction.cdxml'
    path.parent.mkdir(parents=True, exist_ok=True)
    scheme_cdxml(path)
    w.syn_tab.set_scheme(path)
    w.save_project()
else:
    w.open_project(project, ask=False, recent=False)
# Seed only the untouched, synthetic preview once; never replace the user's edits.
seeded = preview / '.sample-seeded'
if not seeded.exists():
    if not w.syn_state.get('proc') and not w.syn_state.get('reagents'):
        w.syn_state.update(name='S2',
            proc='<b>S1</b> (5.00 mmol, 1.0 eq.) was dissolved in MeOH (10 mL). '
                 'K<sub>2</sub>CO<sub>3</sub> (6.00 mmol, 1.2 eq.) was added and the mixture '
                 'was stirred at room temperature for 1 h. After work-up, <b>S2</b> '
                 'was obtained as a colourless solid. <i>Synthetic demonstration data.</i>',
            reagents=[dict(name='S1', M='C11H15NSi', n_mmol='5.00', role='ref'),
                      dict(name='K2CO3', M='K2CO3', label_equiv=1.2, role='reagent')])
        w.syn_tab.sync_widgets()
        w.save_project()
    seeded.touch()
# Explicitly select synthesis without changing the user's normal app settings.
w.main_tabs.setCurrentWidget(w.syn_tab)
if '--smoke' in sys.argv or '--smoke-keys' in sys.argv:
    def finish_test():
        editor = w.syn_tab.drawing_editor
        if not editor or not editor.ready or editor.path is None:
            return
        probe.stop()
        if '--smoke-keys' in sys.argv:
            from check_drawing_keys import check_drawing_keys
            try:
                check_drawing_keys(w)
            except Exception as ex:
                print('FAIL: ' + str(ex), flush=True)
                app.exit(1)
                return
        if not editor.save_sync():
            print('FAIL: integrated save', flush=True)
            app.exit(1)
            return
        def capture():
            import base64, json
            blocks = w.syn_tab.si_blocks(preview / 'si-check')
            embedded = next(b for b in blocks if b[0] == 'ole')
            metadata = json.loads(editor.path.with_suffix('.elucida-drawing.json').read_text())
            assert Path(embedded[1]).read_bytes() == base64.b64decode(metadata['si']['cdx'])
            w.grab().save(str(preview / 'preview.png'))
            print('OK: integrated synthesis editor saved; screenshot: ' + str(preview / 'preview.png'), flush=True)
            app.exit(0)
        QTimer.singleShot(500, capture)
    probe = QTimer(interval=1000)
    probe.timeout.connect(finish_test)
    probe.start()
    QTimer.singleShot(45000, lambda: app.exit(1))
code = app.exec()
MW.release_widgets(app)
sys.exit(code)
