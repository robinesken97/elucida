import unittest
from elucida.app.drawing_data import clone_table
from elucida.tabs.synthesis import row_amounts

class TableCopy(unittest.TestCase):
    def test_units_update_identity_and_purity(self):
        source='drawing.cdxml'
        table=dict(arrow=4,components=[dict(key='r:A', name='A',formula='C2H6O',mw=46.069, product=False,limiting=True,typed=dict(mass=.092138,moles=.001,volume=.12),
            values=dict(mass=.092138,moles=.001,equiv=1,volume=.12,density=.7678,purity=.5))])
        rows=clone_table([],table,source)
        self.assertEqual(rows[0]['m_mg'],'92.138')
        self.assertEqual(rows[0]['n_mmol'],'1')
        self.assertEqual(rows[0]['V_mL'],'0.12')
        self.assertEqual(row_amounts(rows[0])['mmol'],1) # retain purity-corrected Octet result
        table['components'][0]['values']['moles']=.002
        rows2=clone_table(rows,table,source)
        self.assertEqual(len(rows2),1)
        self.assertEqual(row_amounts(rows2[0])['mmol'],2)
        self.assertEqual(clone_table(rows2,dict(arrow=4,components=[]),source),[])
        # computed values: 3 significant digits, never 10-digit noise in the SI
        table['components'][0].update(typed={}); table['components'][0]['values']['mass']=.1234567891
        self.assertEqual(clone_table([],table,source)[0]['m_mg'],'123')

if __name__=='__main__':unittest.main()
