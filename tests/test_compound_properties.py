"""A valid graph must retain its properties even when its preview cannot render."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from elucida.core import chem


class CompoundProperties(unittest.TestCase):
    def test_render_failure_does_not_discard_properties(self):
        # Synthetic benzene; coincident coordinates reproduce RDKit's failure
        # after the comma-locale CDXML parser collapsed the drawing coordinates.
        nodes = ''.join(f'<n id="{i+2}" p="0 0" Element="6"/>' for i in range(6))
        bonds = ''.join(f'<b id="{i+8}" B="{i+2}" E="{(i+1)%6+2}" Order="{2 if i%2==0 else 1}"/>' for i in range(6))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'benzene.cdxml'
            path.write_text('<CDXML BondLength="14.4"><page id="1"><fragment id="20">' + nodes + bonds + '</fragment></page></CDXML>')
            self.assertEqual(chem.load_cdxml(path, render=False)['formula'], 'C6H6')
            self.assertAlmostEqual(chem.load_cdxml(path, render=False)['mw'], 78.114, places=3)
            # The drawing path is separate and must not reuse the properties-only cache.
            with patch('rdkit.Chem.Draw.rdMolDraw2D.MolDraw2DSVG', side_effect=RuntimeError('Cannot normalize a zero length vector')):
                with self.assertRaisesRegex(RuntimeError, 'zero length'):
                    chem.load_cdxml(path)
                self.assertEqual(chem.load_cdxml(path, render=False)['formula'], 'C6H6')


if __name__ == '__main__':
    unittest.main()
