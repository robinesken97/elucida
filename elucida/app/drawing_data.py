"""Transfer Octet's solved table without guessing compound identity from molar mass."""
def clone_table(existing, table, source):
    prefix = f'{source}#{table["arrow"]}#'
    old = {r.get('octet_source'): r for r in existing}
    copied = []
    from elucida.tabs.synthesis import fmt_sig
    def number(value, factor=1, typed=True):
        # Eingegebenes bleibt, wie es war; Berechnetes mit 3 gültigen Stellen (Regel der Reagenzientabelle).
        if value is None:
            return ''
        return f'{value * factor:.10g}' if typed else fmt_sig(value * factor)
    for c in table['components']:
        key = prefix + c['key']
        v = c['values']
        product = c['product']
        n = v.get('productMoles') if product else v.get('moles')
        given = c.get('typed') or {}
        row = dict(name=c['name'], M=c['formula'] or number(c['mw']),
                   m_mg=number(v.get('measured') if product else v.get('mass'), 1000, 'measured' in given if product else 'mass' in given),
                   V_mL=number(v.get('volume'), 1, 'volume' in given), rho=number(v.get('density')), c_M=number(v.get('molarity')),
                   n_mmol=number(n, 1000, 'moles' in given), role='product' if product else 'ref' if c['limiting'] else 'reagent',
                   octet_source=key, octet_values=dict(mmol=None if n is None else n*1000,
                     eq=v.get('equiv') if not product else None,
                     yld=None if v.get('yield') is None else v['yield']*100))
        # Keep a locally supplied compound label when the source only supplies a formula.
        previous = old.get(key)
        if previous and c['name'] == c['formula'] and previous.get('name'):
            row['name'] = previous['name']
        copied.append(row)
    kept = [r for r in existing if not str(r.get('octet_source', '')).startswith(prefix)]
    if any(r['role'] == 'ref' for r in copied):
        kept = [dict(r, role='reagent') if r.get('role') == 'ref' else r for r in kept]
    return kept + copied
