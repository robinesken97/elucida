"""Live Qt/WebEngine round-trip smoke test with synthetic data (45 s watchdog)."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QCoreApplication, QEvent
from elucida.app.drawing_editor import DrawingEditor
from elucida.app.demo import scheme_cdxml

app = QApplication([])
out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix='elucida-editor-test-'))
out.mkdir(parents=True, exist_ok=True)
p = out / 'drawing.cdxml'
scheme_cdxml(p)
w = DrawingEditor()
w.resize(1200, 800)
w.open_path(p)
w.show()

def fail():
    print('FAIL: WebEngine timeout', flush=True)
    app.exit(1)
watchdog = QTimer(singleShot=True, interval=45000)
watchdog.timeout.connect(fail)
watchdog.start()

def verify():
    try:
        print('Checking JS', w._js('1+1'), flush=True)
        print('Checking snapshot', flush=True)
        data = w._js('window.elucida.snapshot()')
        assert '<fragment' in data['cdxml'], 'synthetic molecule missing'
        assert 'svg' in data['svg']
        w.persist(data)
        w._js('window.elucida.load(' + json.dumps(data['cdxml']) + ', ' + json.dumps(p.stem) + ')' )
        again = w._js('window.elucida.snapshot()')
        assert again['cdx'] == data['cdx'], 'CDX round-trip changed'
        w.grab().save(str(out / 'editor.png'))
        print(f'OK: editor, CDXML/CDX round-trip, SVG and save; artifacts: {out}', flush=True)
        app.exit(0)
    except Exception as ex:
        print(f'FAIL: {ex}', flush=True)
        app.exit(1)

def tick():
    if w.ready and w.path is not None:
        timer.stop()
        QTimer.singleShot(500, verify)
timer = QTimer(interval=200)
timer.timeout.connect(tick)
timer.start()
print('Starting WebEngine test', flush=True)
code = app.exec()
w.close()
w.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
sys.exit(code)
