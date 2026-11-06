"""Presentation changes must not alter energies or mechanism ordering."""
from copy import deepcopy
import unittest

from elucida.tabs.diagram_layout import arranged


class DiagramLayoutTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(uid='a', step=0, value=0., paths=['A'], label='A'),
                     dict(uid='ts', step=1, value=12.5, paths=['A'], label='TS'),
                     dict(uid='b', step=2, value=-8.4, paths=['A'], label='B')]

    def test_scaled_ignores_saved_schematic_heights_and_breaks(self):
        layout = dict(nodes={'ts': dict(y=1., break_after=True)})
        plotted = arranged(self.rows, layout)
        self.assertEqual([r['plot_y'] for r in plotted], [0., 12.5, -8.4])
        self.assertFalse(any(r['break_after'] for r in plotted))

    def test_schematic_preserves_energy_values_and_input(self):
        layout = dict(mode='schematic', nodes={'ts': dict(y=1., width=1.2, break_after=True)})
        rows_before, layout_before = deepcopy(self.rows), deepcopy(layout)
        plotted = arranged(self.rows, layout)
        self.assertEqual(plotted[1]['plot_y'], 1.)
        self.assertEqual(plotted[1]['value'], 12.5)
        self.assertTrue(plotted[1]['break_after'])
        self.assertEqual(self.rows, rows_before)
        self.assertEqual(layout, layout_before)

    def test_horizontal_edits_never_reorder_mechanism(self):
        plotted = arranged(self.rows, dict(nodes={'a': dict(x=4.), 'b': dict(x=-1.)}))
        self.assertEqual([r['uid'] for r in plotted], ['a', 'ts', 'b'])
        self.assertEqual([r['value'] for r in plotted], [0., 12.5, -8.4])

    def test_invalid_coordinates_are_rejected(self):
        for key, value in [('x', float('nan')), ('x', float('inf')), ('y', True),
                           ('width', 0.), ('label_dx', 2.), ('energy_dy', '0')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                arranged(self.rows, dict(mode='schematic', nodes={'a': {key: value}}))
        with self.assertRaises(ValueError):
            arranged(self.rows, dict(mode='unlabelled'))


if __name__ == '__main__': unittest.main()
