"""GUI regression: upper reaction SI, theme-neutral exports, grid amounts and autosave."""
import json, sys, tempfile, subprocess
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,QCoreApplication,QEvent
from PySide6.QtTest import QTest
from elucida.app.drawing_editor import DrawingEditor
from elucida.app.demo import scheme_cdxml
from elucida.app.drawing_data import clone_table
from elucida.formats import cdxml
out=Path(tempfile.mkdtemp(prefix='elucida-features-'));p=out/'drawing.cdxml'
scheme_cdxml(p)
subprocess.run(['node',str(ROOT/'tools/make_drawing_fixture.mjs'),str(p)],check=True)
app=QApplication([]);w=DrawingEditor();w.resize(1200,800);w.open_path(p);w.show()
def check():
 try:
  light=w._js('window.elucida.snapshot()')
  assert w._js('Array.from(document.querySelectorAll("svg.canvas .pages, svg.canvas .guide")).every(e => getComputedStyle(e).display === "none")'), 'guide lines visible'
  assert light['si'], 'upper reaction missing'
  assert 'NOT_FOR_SI' in light['cdxml'] and 'NOT_FOR_SI' not in light['si']['cdxml']
  assert light['si']['cdxml'].count('<fragment') * 2 == light['cdxml'].count('<fragment'), 'lower reaction retained'
  assert 'stoich' not in light['si']['svg'] and 'Density' not in light['si']['svg']
  assert 'NOT_FOR_SI' not in light['si']['svg'], 'lower drawing leaked into SI preview'
  # Check the actual renderer used for Word, not just SVG source text.
  import pymupdf
  with pymupdf.open(stream=light['si']['svg'].encode(), filetype='svg') as vector:
   pdf=vector.convert_to_pdf()
  with pymupdf.open(stream=pdf, filetype='pdf') as rendered:
   page=rendered[0]
   assert 'K2CO3 (1.2 eq.)' in page.get_text(), 'arrow caption split/overlapped'
   spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
   caption=next(i for i,s in enumerate(spans) if s['text']=='K')
   runs=spans[caption:caption+5]
   assert [s['text'] for s in runs]==['K','2','CO','3',' (1.2 eq.)']
   assert all(a['bbox'][2] <= b['bbox'][0]+.05 for a,b in zip(runs,runs[1:])), 'subscripts overlap'
   assert all(s['color']==0 for s in runs), 'export ink is not black'
   page.get_pixmap(dpi=200).save(str(out/'si-caption.png'))
  assert 'Density' in light['svg'] and 'Volume' in light['svg'], 'grid fields not visible'
  table=light['tables'][0]; reagent=next(c for c in table['components'] if c['name']=='K2CO3')
  assert reagent['typed']['equiv']==1.2 and abs(reagent['values']['moles']-.006)<1e-8
  assert reagent['values']['volume']>0 and reagent['values']['density']==2.43
  rows=clone_table([],table,str(p)); rows2=clone_table(rows,table,str(p))
  assert rows==rows2 and len(rows)==len(table['components']), 'clone duplicates'
  w.set_canvas_dark(True);QTest.qWait(150)
  assert w._js('document.querySelector("svg.canvas").getAttribute("data-theme")')=='dark'
  assert w._js('getComputedStyle(document.querySelector("svg.canvas")).backgroundColor')=='rgb(0, 0, 0)', 'canvas must be pure black'
  dark=w._js('window.elucida.snapshot()')
  for key in ('cdxml','cdx','svg'):
   assert dark[key]==light[key], 'theme changed '+key
   assert dark['si'][key]==light['si'][key], 'theme changed SI '+key
  w.persist(dark);w._js('window.elucida.markSaved()')
  before=p.read_bytes()
  w.command('select_all');QTest.qWait(100);w.command('flip_h')
  QTest.qWait(2000)
  assert p.read_bytes()!=before and not w.dirty, 'autosave failed'
  saved=json.loads(p.with_suffix('.elucida-drawing.json').read_text())
  assert 'NOT_FOR_SI' not in saved['si']['svg'], 'autosaved SI preview contains lower drawing'
  external=p.read_text().replace('<CDXML ', '<CDXML external="yes" ', 1)
  p.write_text(external)
  copy=out/'recovered.cdxml'
  with patch('elucida.app.drawing_editor.QFileDialog.getSaveFileName', return_value=(str(copy),'')):
   w.export_files()
  assert copy.exists() and copy.with_suffix('.cdx').exists(), 'conflict recovery copy failed'
  assert p.read_text()==external, 'copy export overwrote external changes'
  w.grab().save(str(out/'dark-canvas.png'))
  lossy=out/'unsupported.cdxml'
  scheme_cdxml(lossy)
  lossy.write_text(lossy.read_text().replace('</page>', '<unknownthing id="99999"/></page>', 1))
  original=lossy.read_bytes()
  assert w.open_path(lossy) and w.lossy, 'unsupported import was not reported'
  try:
   w.persist(w._js('window.elucida.snapshot()'))
  except ValueError:
   pass
  else:
   raise AssertionError('lossy original was not protected')
  assert lossy.read_bytes()==original
  print('OK: SI top reaction only; density/volume/eq; clone; theme-neutral exports; autosave',out,flush=True)
  app.exit(0)
 except Exception as ex:
  import traceback;traceback.print_exc();app.exit(1)
def tick():
 if w.ready and w.path:
  poll.stop();QTimer.singleShot(600,check)
poll=QTimer(interval=200);poll.timeout.connect(tick);poll.start()
QTimer.singleShot(60000,lambda:app.exit(1))
rc=app.exec();w.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);sys.exit(rc)
