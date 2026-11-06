"""Synthetic scientific regressions; no unpublished calculation files."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from elucida.formats.multireference import make_test_mr, parse_orca_mr, luno_indicator, spin_gap
from elucida.formats.calc import read_text
from elucida.core.tddft import parse_tddft, tddft_variants


class MultireferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = make_test_mr(Path(self.tmp.name) / "synthetic.out")
        self.text = read_text(self.path)

    def test_method_root_precision_and_weights(self):
        r = parse_orca_mr(self.text)
        self.assertEqual([x['method'] for x in r], ['CASSCF', 'SC-NEVPT2', 'QD-SC-NEVPT2'])
        self.assertEqual(r[0]['states'][0]['energy'], '-10.100000000123')
        self.assertEqual(r[0]['states'][0]['configurations'][0]['weight'], '0.90000')
        self.assertEqual(r[0]['states'][0]['irrep'], 'Ag')
        self.assertEqual(r[1]['states'][0]['energy'], '-10.300000000123')
        self.assertEqual(r[2]['states'][0]['energy'], '-10.310000000123')
        self.assertEqual(luno_indicator(r[0])['value'], '0.2000')
        self.assertIsNone(luno_indicator(r[1]))

    def test_no_false_noon(self):
        for text in (self.text.replace('... natural', '... unchanged'),
                     self.text.replace('NROOTS= 1', 'NROOTS= 5'),
                     self.text.replace('MULT= 1', 'MULT= 3'),
                     self.text.replace('2 0.2000', '2 0.8000')):
            self.assertIsNone(luno_indicator(parse_orca_mr(text)[0]))

    def test_initial_ci_ignored_and_utf16(self):
        self.path.write_bytes(self.text.encode('utf-16'))
        r = parse_orca_mr(read_text(self.path))
        self.assertEqual(len(r[0]['states']), 1)
        self.assertNotEqual(r[0]['states'][0]['energy'], '-99.000000')
        self.assertEqual(parse_orca_mr(self.text.replace('6.1.1','5.0.4')), [])

    def test_repeated_blocks_and_fixed_orbitals(self):
        r = parse_orca_mr(self.text + self.text.replace('... 100', '... 1'))
        self.assertEqual(len(r), 6)
        self.assertEqual(r[-1]['convergence'], 'fixed-orbitals')
        self.assertNotEqual(r[0]['group'], r[3]['group'])
        self.assertEqual(len({x['id'] for x in r}), 6)

    def test_spin_gap_sign(self):
        r = parse_orca_mr(self.text)[0]
        t = deepcopy(r['states'][0]); t.update(multiplicity=3, energy='-10.110000000123')
        r['states'].append(t)
        self.assertEqual(spin_gap(r, 0, 1), Decimal('0.010000000000'))
        self.assertEqual(spin_gap(r, 0, 1, 'T-S'), Decimal('-0.010000000000'))
        with self.assertRaises(ValueError): spin_gap(r, 1, 0)

    def test_explicit_spectrum_selection(self):
        text = ''
        for heading, energy in [('CASSCF', '2.1000'), ('CASSCF (NEVPT2 diagonal energies)', '3.2000'), ('QDNEVPT2', '4.3000')]:
            text += f'''{heading} UV, CD spectra and dipole moments
ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS
---------
Transition Energy eV cm-1 nm fosc
---------
0-1A -> 1-1A  {energy} 20000.000 500.000 0.10000

'''
        self.path.write_text(text)
        variants = tddft_variants(self.path)
        self.assertEqual(len(variants), 3)
        self.assertEqual([parse_tddft(self.path, v)['E'][0] for v in variants], [2.1, 3.2, 4.3])
        self.assertEqual(parse_tddft(self.path, 'nosoc')['variant'], variants[-1])
        with self.assertRaises(ValueError): parse_tddft(self.path, 'mr:absent:nosoc:0')


if __name__ == '__main__': unittest.main()
