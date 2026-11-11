"""Integration boundary tests, independent of a GUI or installed ChemDraw."""
import base64
import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
import olefile
from elucida.formats.reagent_labels import parse_labels
from elucida.app.drawing_editor import save_bundle, fingerprint
from elucida.formats.ole import write_cfb, chemdraw_streams

class Reagents(unittest.TestCase):
    def test_amounts_and_chemical_brackets(self):
        rows = parse_labels('NaBH4 (1,5 Äq.); Pd(PPh3)4 (5 mol%), MeOH')
        self.assertEqual([r['substance'] for r in rows], ['NaBH4', 'Pd(PPh3)4', 'MeOH'])
        self.assertEqual([r['equiv'] for r in rows], [1.5, .05, None])
        self.assertEqual(rows[0]['text'], 'NaBH4 (1,5 Äq.)')

    def test_parentheses_not_amounts(self):
        self.assertEqual(parse_labels('Pd(PPh3)4; catalyst (aq.)')[1]['substance'], 'catalyst (aq.)')
        self.assertEqual(len(parse_labels('1,2-dichloroethane')), 1)

class Persistence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'scheme.cdxml'
        self.path.write_text('<CDXML><page/></CDXML>')
        self.old = self.path.read_bytes()
        self.expected = fingerprint(self.path)
        self.bundle = dict(cdxml='<CDXML><page id="1"/></CDXML>',
                           svg='<svg xmlns="http://www.w3.org/2000/svg"/>',
                           cdx=base64.b64encode(b'VjCD0100' + bytes(64)).decode(), reagents=[])

    def test_publish_and_backup(self):
        save_bundle(self.path, self.bundle, self.expected)
        self.assertEqual(self.path.read_text(), self.bundle['cdxml'])
        self.assertEqual(self.path.stat().st_mtime_ns, self.path.with_suffix('.cdx').stat().st_mtime_ns)
        backups = list((self.path.parent / '.editor-backups').glob('*/scheme.cdxml'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.old)

    def test_external_edit_is_not_overwritten(self):
        self.path.write_text('<CDXML>external</CDXML>')
        with self.assertRaises(ValueError):
            save_bundle(self.path, self.bundle, self.expected)
        self.assertEqual(self.path.read_text(), '<CDXML>external</CDXML>')

    def test_bad_bundle_does_not_touch_files(self):
        for key, bad in [('cdx', 'd3Jvbmc='), ('svg', '<html/>'), ('cdxml', '<wrong/>')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                save_bundle(self.path, dict(self.bundle, **{key: bad}), self.expected)
            self.assertEqual(self.path.read_bytes(), self.old)

    def test_partial_publish_rolls_back(self):
        import os
        original = os.replace
        def replace(source, target):
            if Path(target) == self.path:
                raise PermissionError('simulated file lock')
            original(source, target)
        with patch('elucida.app.drawing_editor.os.replace', side_effect=replace):
            with self.assertRaises(PermissionError):
                save_bundle(self.path, self.bundle, self.expected)
        self.assertEqual(self.path.read_bytes(), self.old)
        self.assertFalse(self.path.with_suffix('.cdx').exists())
        self.assertFalse(self.path.with_suffix('.svg').exists())

    def test_ole_preserves_cdx_payload(self):
        cdx = base64.b64decode(self.bundle['cdx'])
        with olefile.OleFileIO(io.BytesIO(write_cfb(chemdraw_streams(cdx)))) as obj:
            self.assertEqual(obj.openstream('CONTENTS').read(), cdx)

    def test_project_import_keeps_editable_sidecars(self):
        from elucida.app import project as PRJ
        save_bundle(self.path, self.bundle, self.expected)
        for via_save in (False, True):
            project = Path(self.tmp.name) / ('saved-project' if via_save else 'imported-project')
            if via_save:
                state = {'compound': {'structure': str(self.path)}}
                PRJ.save(project, state)
                target = next(project.rglob('scheme.cdxml'))
            else:
                target = Path(PRJ.import_file(project, self.path, PRJ.STRUCTURES))
            for ext in ('.cdxml', '.cdx', '.svg', '.elucida-drawing.json'):
                self.assertEqual(target.with_suffix(ext).read_bytes(), self.path.with_suffix(ext).read_bytes())

    def test_word_export_keeps_portable_drawings_and_moves_them(self):
        from PIL import Image
        from elucida.si import lines as SI
        from elucida.app import project as PRJ
        from elucida.formats.ole import editable_directory, copy_editable_companions
        save_bundle(self.path, self.bundle, self.expected)
        preview = self.path.with_suffix('.png')
        Image.new('RGB', (100, 50), 'white').save(preview)
        project = Path(self.tmp.name) / 'project'
        word = PRJ.staging(project, 'synthesis') / 'test.docx'
        SI.write_docx(word, [('ole', self.path.with_suffix('.cdx'), preview, 8, 4)])
        def check(path):
            folder = editable_directory(path)
            self.assertEqual((folder / 'drawing_001.cdxml').read_text(), self.bundle['cdxml'])
            cdx = (folder / 'drawing_001.cdx').read_bytes()
            self.assertEqual(cdx, base64.b64decode(self.bundle['cdx']))
            with zipfile.ZipFile(path) as archive:
                with olefile.OleFileIO(io.BytesIO(archive.read('word/embeddings/oleObject1.bin'))) as obj:
                    self.assertEqual(obj.openstream('CONTENTS').read(), cdx)
        check(word)
        moved = PRJ.place_exports(project, [word])[0]
        check(moved)
        quick = Path(self.tmp.name) / 'quick' / moved.name
        quick.parent.mkdir()
        copy_editable_companions(moved, quick)
        quick.write_bytes(moved.read_bytes())
        check(quick)
        plain = quick.with_name('text-only.docx')
        SI.write_docx(plain, [('text', 'No reaction drawing')])
        self.assertFalse(editable_directory(plain).exists())

if __name__ == '__main__':
    unittest.main()
