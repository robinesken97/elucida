"""Presentation-only energy-profile layout; calculation values are never edited here."""
import math

import numpy as np
from matplotlib.colors import is_color_like
from elucida.app.i18n import T
from elucida.tabs import base as TABS

SCHEMATIC_NOTE = 'Schematic profile; vertical spacing is not to scale.'


def number(obj, key, default, low=-1e5, high=1e5):
    value = obj.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid diagram layout: ' + key)
    return value


def arranged(rows, layout, factor=1.):
    """Return drawing coordinates separately from each unmodified energy value. factor: Einheit des Bildes (Werte und
    gespeicherte Höhen bleiben kcal/mol, gezeichnet wird in der gewählten Einheit)."""
    if layout.get('mode', 'scaled') not in ('scaled', 'schematic'):
        raise ValueError('Invalid diagram presentation mode')
    schematic = layout.get('mode', 'scaled') == 'schematic'
    result = []
    for r in rows:
        node = layout.get('nodes', {}).get(r['uid'], {})
        offsets = {}
        for key, default in [('energy_dx', 0.), ('energy_dy', .025), ('label_dx', 0.), ('label_dy', -.025)]:
            offsets[key] = number(node, key, default, -1, 1)
        color = node.get('color')
        if color and not is_color_like(color): raise ValueError('Invalid diagram colour')
        result.append(dict(r, x=number(node, 'x', r['step']),
                           plot_y=(number(node, 'y', r['value']) if schematic else r['value']) * factor,
                           width=number(node, 'width', number(layout, 'level_width', .7, .05, 20), .05, 20), color=color,
                           break_after=bool(node.get('break_after')) and schematic, **offsets))
    return result


EDGE_LINES = ('--', '-', ':', 'curve', 'wavy', 'none')


def implied_edges(rows):
    """Verbinder aus Schritt und Pfadbuchstaben (bis 2.7.1 die einzige Art): je Pfad die Stufen in ihrer Reihenfolge.
    Row/path order is scientific input: moving a plateau must not reorder a mechanism."""
    out, seen = [], set()
    for p in sorted({p for r in rows for p in r['paths']}):
        branch = [r for r in rows if p in r['paths']]
        for a, b in zip(branch, branch[1:]):
            if (a['uid'], b['uid']) not in seen:
                seen.add((a['uid'], b['uid']))
                out.append(dict(a=a['uid'], b=b['uid'], path=p))
    return out


def edges_of(prof, rows):
    """Verbinder des Profils: ausdrücklich gesetzte (`prof["edges"]`, Plateaus als Knoten verknüpft), sonst die aus
    Schritt und Pfad abgeleiteten. Je Verbinder: a, b (uid), line (EDGE_LINES oder None = Stil des Diagramms),
    arrow, color, label."""
    if prof.get('edges') is None:
        return implied_edges(rows)
    uids = {r['uid'] for r in rows}
    out = []
    for e in prof['edges']:
        if e.get('a') in uids and e.get('b') in uids and e['a'] != e['b']:
            if e.get('line') not in (None, *EDGE_LINES): raise ValueError('Invalid connector style')
            if e.get('color') and not is_color_like(e['color']): raise ValueError('Invalid diagram colour')
            out.append(dict(e))
    return out


VERTICAL_SLOTS = (.82, .18, .66, .34, .5)     # Stellen entlang des Plateaus für senkrechte Übergänge (nie zuerst die Mitte)


def is_vertical(a, b):
    """Liegen zwei Plateaus übereinander (gleiche Stelle, z. B. Singulett/Triplett oder S2/S1)?"""
    return abs(b['x'] - a['x']) < (a['width'] + b['width']) / 4


def edge_ends(a, b, slot=0, rows=(), gap=0., pad=None, segments=()):
    """Anfang und Ende eines Verbinders. Nebeneinander: vom Ende des einen Plateaus zum Anfang des anderen.
    Übereinander (Übergänge wie im Jablonski-Diagramm): senkrecht in der Spalte, seitlich versetzt an den Linien
    angesetzt statt durch die Mitte – nie über einer Beschriftung (`text_half` der Plateaus = halbe Textbreite); mehrere
    Übergänge nebeneinander (`slot`). Ein Niveau dazwischen wird gekreuzt wie von den Pfeilen im Jablonski-Diagramm (der
    Zeichner unterbricht dort dessen Linie); zwischen den Spalten laufen nur die Verbinder. Ohne freie Stelle in der
    Spalte (breite Texte): dicht außen am Stapel vorbei (Abstand `pad`), auf der Seite, auf der weniger Verbinder
    (`segments`) gekreuzt werden. In der Spalte beginnt der Übergang mit dem Abstand `gap` über/unter der Startlinie und
    endet auf der Ziellinie."""
    if not is_vertical(a, b):
        sa, sb = (1, -1) if b['x'] > a['x'] else (-1, 1)
        return (np.array([a['x'] + sa * a['width'] / 2, a['plot_y']]), np.array([b['x'] + sb * b['width'] / 2, b['plot_y']]))
    left = max(a['x'] - a['width'] / 2, b['x'] - b['width'] / 2)
    right = min(a['x'] + a['width'] / 2, b['x'] + b['width'] / 2)
    lo, hi = sorted((a['plot_y'], b['plot_y']))
    between = [r for r in rows if lo < r['plot_y'] < hi                      # Plateaus derselben Spalte dazwischen
               and r['x'] + r['width'] / 2 > left and r['x'] - r['width'] / 2 < right]
    order = VERTICAL_SLOTS[slot % len(VERTICAL_SLOTS):] + VERTICAL_SLOTS[:slot % len(VERTICAL_SLOTS)]
    margin = 0. if pad is None else .5 * pad

    def clear(x):
        return all(abs(x - r['x']) > r.get('text_half', 0.) + margin for r in [a, b] + between)
    free = [x for x in (left + f * (right - left) for f in order) if clear(x)]
    if free:
        up = 1 if b['plot_y'] > a['plot_y'] else -1
        return np.array([free[0], a['plot_y'] + up * gap]), np.array([free[0], b['plot_y']])
    step = (.10 * (right - left) if pad is None else pad) * (1 + 1.2 * slot)
    stack = [a, b] + between

    def crossings(x):
        n = 0
        for p, q in segments:
            if min(p[0], q[0]) < x < max(p[0], q[0]):
                n += lo < p[1] + (x - p[0]) / (q[0] - p[0]) * (q[1] - p[1]) < hi
        return n
    x_right = max(r['x'] + r['width'] / 2 for r in stack) + step
    x_left = min(r['x'] - r['width'] / 2 for r in stack) - step
    x = x_left if crossings(x_left) < crossings(x_right) else x_right
    return np.array([x, a['plot_y']]), np.array([x, b['plot_y']])


def wave(start, end, xlim, ylim, aspect, straight=.14):
    """Wellenlinie von start nach end (strahlungsloser Übergang wie im Jablonski-Diagramm): gleichmäßig in der
    Bildebene, das letzte Stück gerade für die Pfeilspitze. aspect = Breite/Höhe der Achse."""
    sx, sy = xlim[1] - xlim[0], ylim[1] - ylim[0]
    u0 = np.array([(start[0] - xlim[0]) / sx * aspect, (start[1] - ylim[0]) / sy])
    u1 = np.array([(end[0] - xlim[0]) / sx * aspect, (end[1] - ylim[0]) / sy])
    d = u1 - u0
    length = float(np.hypot(*d)) or 1e-9
    normal = np.array([-d[1], d[0]]) / length
    n = max(3, round(length / .045))
    t = np.linspace(0, 1, 40 * n + 1)
    envelope = np.clip((1 - straight - t) / .06, 0, 1) * np.clip(t / .04, 0, 1)
    pts = u0 + np.outer(t, d) + np.outer(.011 * np.sin(2 * np.pi * n * t / (1 - straight)) * envelope, normal)
    return pts[:, 0] / aspect * sx + xlim[0], pts[:, 1] * sy + ylim[0]


def _text_width(text, size):
    """Breite eines Texts in Punkten ohne Renderer (für die Lage der Übergänge neben den Beschriftungen)."""
    try:
        from matplotlib.textpath import TextPath
        return float(TextPath((0, 0), text, size=size).get_extents().width) if text else 0.
    except Exception:
        return .6 * size * len(text or '')


def _edge_labels(F, items, curves, size):
    """Beschriftungen der Verbinder (ISC, IC, hν …) NEBEN die Linie setzen – nie auf einen Strich, ein Plateau oder eine
    andere Beschriftung (Nutzerwunsch, wie in Jablonski-Diagrammen): entlang des Verbinders die erste freie Stelle auf
    einer der beiden Seiten. Verschobene Labels (label_dx/dy, Abstand zur Mitte) bleiben, wo sie hingezogen wurden."""
    if not items:
        return
    ax, cfg = F.ax, F.cfg
    x0, x1 = cfg['xlim']; y0, y1 = cfg['ylim']
    canvas = F.fig.canvas
    renderer = canvas.get_renderer() if hasattr(canvas, 'get_renderer') else F.fig._get_renderer()
    pt = F.fig.dpi / 72
    to_px = ax.transData.transform
    boxes = [t.get_window_extent(renderer).padded(1.5 * pt) for t in ax.texts if t.get_text()]
    dots = []
    for c in curves:                                          # alle Striche (Verbinder und Plateaus) als Punktfolge
        x, y = np.asarray(c['x'], float), np.asarray(c['y'], float)
        if len(x) == 2:
            x, y = np.linspace(x[0], x[1], 120), np.linspace(y[0], y[1], 120)
        dots.append(to_px(np.column_stack([x, y])))
    dots = np.vstack(dots) if dots else np.zeros((0, 2))
    frame = ax.get_window_extent(renderer)
    to_af = ax.transAxes.inverted().transform
    for start, end, e, color, side, wavy in items:
        mid = .5 * (start + end)
        anchor = ((mid[0] - x0) / (x1 - x0), (mid[1] - y0) / (y1 - y0))
        ann = ax.annotate(e['label'], xy=tuple(mid), xycoords='data', xytext=anchor, textcoords='axes fraction',
                          ha='center', va='center', fontsize=size, color=color, annotation_clip=False)
        ann._anchor_af = anchor
        F.ann_items[f"edge_{e['a']}_{e['b']}"] = ann
        if 'label_dx' in e or 'label_dy' in e:
            ann.xyann = (anchor[0] + number(e, 'label_dx', 0., -1, 1), anchor[1] + number(e, 'label_dy', 0., -1, 1))
        else:
            box = ann.get_window_extent(renderer)
            w, h = box.width + 8 * pt, box.height + 8 * pt     # Luft zu Strichen (auch deren Dicke) und Texten
            p, q = to_px(start), to_px(end)
            d = q - p
            normal = np.array([-d[1], d[0]]) / (float(np.hypot(*d)) or 1.)
            if (side and normal[0] * side < 0) or (not side and normal[1] < 0):
                normal = -normal                             # senkrecht: zuerst nach außen, sonst zuerst über die Linie
            dist = abs(normal[0]) * w / 2 + abs(normal[1]) * h / 2 + 2 * pt + (.011 * frame.height if wavy else 0)
            spots = [p + t * d + sign * dist * normal for t in (.5, .36, .64, .24, .76) for sign in (1, -1)]

            def free(c):
                lo, hi = c - (w / 2, h / 2), c + (w / 2, h / 2)
                if lo[0] < frame.x0 or hi[0] > frame.x1 or lo[1] < frame.y0 or hi[1] > frame.y1:
                    return False
                if len(dots) and np.any(np.all((dots > lo) & (dots < hi), axis=1)):
                    return False
                return not any(b.x0 < hi[0] and b.x1 > lo[0] and b.y0 < hi[1] and b.y1 > lo[1] for b in boxes)
            ann.xyann = tuple(to_af(next((c for c in spots if free(c)), spots[0])))
        boxes.append(ann.get_window_extent(renderer).padded(1.5 * pt))


def build_levels(pages, fig, layout, images=False):
    """Stufenbild eines Energieprofils – das eine Zeichenwerk für den DFT-Tab (images=True: Strukturen und Bilder an den
    Plateaus) und für die Abbildungen des Reaktionspfads. Energien kommen unverändert aus `levels_spec`; `layout` ist
    nur Darstellung (Stil, Lage der Plateaus und Labels)."""
    from elucida.tabs.dft_pages import KINDS, UNITS, energy_text
    source, paths, notes = pages.levels_spec()
    if not source: return None, notes
    unit = pages.unit()
    rows = arranged(source, layout, UNITS[unit][2])
    schematic = layout.get('mode', 'scaled') == 'schematic'
    cfg = pages.cfg('levels')
    cfg['images'] = []
    cfg['ylabel'] = KINDS[pages.prof['y']][0] + f' [{UNITS[unit][0]}]'
    if schematic and not layout.get('axis_title'): cfg['ylabel'] += ' (schematic)'
    xs = [r['x'] - r['width']/2 for r in rows] + [r['x'] + r['width']/2 for r in rows]
    ys = [r['plot_y'] for r in rows]
    xspan, yspan = max(max(xs)-min(xs), 1), max(max(ys)-min(ys), 1)
    label_pos = layout.get('labels', 'split')                # Wert oben + Name unten | beide unter | beide über dem Plateau
    if label_pos not in ('split', 'below', 'above'): raise ValueError('Invalid label position')
    sections = [sec for sec in (pages.prof.get('sections') or []) if sec.get('b', 0) > sec.get('a', 0)]
    cfg['xlim'] = [min(xs)-.12*xspan, max(xs)+.12*xspan]
    low = (.3 if label_pos == 'below' else .12 if label_pos == 'above' else .2) + (.14 if sections else 0)
    cfg['ylim'] = [min(ys)-low*yspan, max(ys)+(.12 if label_pos == 'below' else .3 if label_pos == 'above' else .2)*yspan]
    title = layout.get('axis_title')                         # eigener Achsentitel; „ | “ = Zeilenumbruch
    if title:
        cfg['ylabel'] = str(title).replace(' | ', '\n').replace('{unit}', UNITS[unit][0])
    if images:
        notes = notes + _images(pages, cfg, rows, yspan)
    width = number(layout, 'line_width', 2.2, .1, 10)
    connector_width = number(layout, 'connector_width', .8, .1, 10)
    fs = number(layout, 'font_size', cfg['labels']['font_size'], 4, 40)
    linestyle = layout.get('connector_style', '--')
    if linestyle not in EDGE_LINES: raise ValueError('Invalid connector style')
    default = layout.get('color', 'black')
    if not is_color_like(default): raise ValueError('Invalid diagram colour')
    curves, breaks, heads, edge_labels, bridges = [], [], [], [], []
    # Pfadfarben: eigene Farbe des Pfads, sonst die Palette (DFT-Tab, Stil „Farbig je Pfad“) oder die Diagrammfarbe
    palette = layout.get('path_colors', images)
    colors = {p: pages.prof.get('colors', {}).get(p) or (pages.path_color(p, k) if palette else default)
              for k, p in enumerate(paths)}
    by_uid = {r['uid']: r for r in rows}
    fw, fh = cfg['figsize_in']
    aspect = fw * cfg['axes_rect'][2] / (fh * cfg['axes_rect'][3])
    slots = {}                                                # senkrechte Übergänge je Spalte nebeneinander
    xw = cfg['xlim'][1] - cfg['xlim'][0]
    for r in rows:                                            # halbe Breite der Beschriftungen: Übergänge setzen daneben an
        r['text_half'] = max(_text_width(t, fs) for t in (energy_text(r['value'], unit), r['label'])) / 144 / (fw * cfg['axes_rect'][2]) * xw
    pad = .023 / aspect * xw                                  # Wellenlinie (Ausschlag .011) plus Luft
    edges = edges_of(pages.prof, rows)
    segments = [edge_ends(by_uid[e['a']], by_uid[e['b']]) for e in edges
                if (e.get('line') or linestyle) != 'none' and not is_vertical(by_uid[e['a']], by_uid[e['b']])]
    for e in edges:
        a, b = by_uid[e['a']], by_uid[e['b']]
        path = e.get('path') or next((p for p in a['paths'] if p in b['paths']), a['paths'][0])
        col = e.get('color') or a['color'] or colors.get(path, default)
        style = e.get('line') or linestyle
        column = round(.5 * (a['x'] + b['x']), 2)
        slot = slots.get(column, 0)
        if is_vertical(a, b):
            slots[column] = slot + 1
        start, end = edge_ends(a, b, slot, rows, .012 * (cfg['ylim'][1] - cfg['ylim'][0]), pad, segments)
        vertical = abs(end[0] - start[0]) < 1e-9
        if e.get('label'):
            edge_labels.append((start, end, e, col, np.sign(start[0] - .5 * (a['x'] + b['x'])) if vertical else 0,
                                style == 'wavy'))
        if style == 'none': continue
        first = len(curves)
        if style == 'wavy':
            wx, wy = wave(start, end, cfg['xlim'], cfg['ylim'], aspect)
            curves.append(dict(x=wx, y=wy, color=col, ls='-', lw=connector_width, label=None))
        elif style == 'curve' and abs(end[0] - start[0]) > 1e-9:    # weicher Übergang: waagerecht aus dem Plateau heraus
            t = np.linspace(0, 1, 60)
            curves.append(dict(x=start[0] + t * (end[0] - start[0]),
                               y=start[1] + (3 * t ** 2 - 2 * t ** 3) * (end[1] - start[1]),
                               color=col, ls='-', lw=connector_width, label=None))
        else:
            style = '-' if style == 'curve' else style
            segments = [(start, end)]
            if a['break_after']:
                segments = [(start, start+.44*(end-start)), (start+.56*(end-start), end)]
                breaks.append((.5*(start+end), col))
            for left, right in segments:
                curves.append(dict(x=np.array([left[0], right[0]]), y=np.array([left[1], right[1]]),
                                   color=col, ls=style, lw=connector_width, label=None))
        crossed = [r for r in rows if vertical and min(start[1], end[1]) < r['plot_y'] < max(start[1], end[1])
                   and abs(start[0] - r['x']) < r['width'] / 2]
        for r in crossed:                                     # Niveau dazwischen: dessen Linie ist am Übergang unterbrochen
            bridges.append((start[0], r['plot_y'], (.75 if style == 'wavy' else .4) * pad))
        if vertical or style == 'wavy':                       # Übergänge liegen über den Verbindern, die sie kreuzen
            for c in curves[first:]: c['over' if crossed else 'halo'] = True
        if e.get('arrow'):
            heads.append((start + .9 * (end - start), end, col))
    n_edges = len(curves)
    for r in rows:
        color = r['color'] or (colors[r['paths'][0]] if len(r['paths']) == 1 else default)
        curves.append(dict(x=np.array([r['x']-r['width']/2, r['x']+r['width']/2]),
                           y=np.array([r['plot_y']]*2), color=color, ls='-', lw=width, label=None))
    F = TABS.X.SimpleFigure(TABS.plt, cfg, curves, [], {}, fig=fig, legend=False)
    if len(F.ax.lines) == len(curves):
        from matplotlib import patheffects
        for line, c in zip(F.ax.lines, curves):
            if c.get('halo'):                                # kreuzt ein Übergang einen Verbinder, ist der unterbrochen
                line.set_zorder(2.2)
                line.set_path_effects([patheffects.withStroke(linewidth=c['lw'] + 3.2, foreground=F.ax.get_facecolor())])
            elif c.get('over'):
                line.set_zorder(2.6)
        for line in F.ax.lines[n_edges:]:
            line.set_zorder(2.4)                             # Plateaus über den Verbindern
    for x, y, half in bridges:
        F.ax.plot([x - half, x + half], [y, y], color=F.ax.get_facecolor(), lw=width + 1, zorder=2.5, solid_capstyle='butt')
    F.profile_rows = rows                                    # Lage der Plateaus (Verknüpfen mit der Maus)
    F.ax.set_xticks([])
    if schematic:
        F.ax.set_yticks([])
        F.fig.text(.5, .025, SCHEMATIC_NOTE, ha='center', va='bottom', fontsize=max(7, fs*.8))
    if not layout.get('frame', True):                        # ohne Rahmen: nur ein Pfeil mit der Größe an der Seite
        for spine in F.ax.spines.values(): spine.set_visible(False)
        F.ax.set_yticks([])
        F.ax.set_xlabel('')
        ylabel = F.ax.get_ylabel()
        F.ax.set_ylabel('')
        # Pfeil oben links, der Titel rechts daneben (mehrzeilig möglich), wie in Profilen ohne Achse üblich
        F.ax.annotate('', xy=(-.06, .99), xytext=(-.06, .74), xycoords='axes fraction',
                      arrowprops=dict(arrowstyle='-|>', color='black', lw=1.4), annotation_clip=False)
        F.ax.text(-.045, .985, ylabel, transform=F.ax.transAxes, ha='left', va='top', fontsize=max(7, fs * .85),
                  fontweight='bold' if 'bold' in layout.get('label_font', '') else 'normal', linespacing=1.3)
    x0, x1 = cfg['xlim']; y0, y1 = cfg['ylim']
    style = layout.get('label_font', 'normal')
    if style not in ('normal', 'bold', 'italic', 'bold italic'): raise ValueError('Invalid label font')
    font = dict(fontweight='bold' if 'bold' in style else 'normal', fontstyle='italic' if 'italic' in style else 'normal')
    line_af = 1.35 * fs / 72 / (fh * cfg['axes_rect'][3])    # eine Textzeile in Achsenbruchteilen
    nodes = layout.get('nodes', {})

    def value_text(v):                                       # „Vorzeichen“: +18.9, ±0.0, −50.1
        t = energy_text(v, unit)
        return t if not layout.get('signed') else '±' + t if float(t.replace('−', '-')) == 0 else t if t.startswith('−') else '+' + t
    for r in rows:
        color = r['color'] or 'black'
        anchor = ((r['x'] - x0) / (x1 - x0), (r['plot_y'] - y0) / (y1 - y0))
        own = nodes.get(r['uid'], {})
        e_dy, e_va, l_dy, l_va = r['energy_dy'], 'bottom', r['label_dy'], 'top'
        if label_pos == 'below':                             # Wert in der Zeile unter dem Namen, solange nicht verschoben
            e_va = 'top'
            if 'energy_dy' not in own: e_dy = l_dy - line_af
        elif label_pos == 'above':                           # Name in der Zeile über dem Wert
            l_va = 'bottom'
            if 'label_dy' not in own: l_dy = e_dy + line_af
        # Labels als Anmerkungen in Achsenbruchteilen: mit der Maus verschiebbar (liegen zwei Plateaus eng, überlagert
        # sich die Schrift sonst); gespeichert wird der Abstand zum Plateau (layout.nodes[uid].energy_dx …)
        for key, text, dx, dy, va in (('energy', value_text(r['value']), r['energy_dx'], e_dy, e_va),
                                      ('label', r['label'], r['label_dx'], l_dy, l_va)):
            ann = F.ax.annotate(text, xy=(r['x'], r['plot_y']), xycoords='data', xytext=(anchor[0] + dx, anchor[1] + dy),
                                textcoords='axes fraction', ha='center', va=va, fontsize=fs, color=color,
                                gid=f"{key}-{r['uid']}", annotation_clip=False, **font)
            ann._anchor_af = anchor
            F.ann_items[f"{key}_{r['uid']}"] = ann
    for start, end, color in heads:
        F.ax.annotate('', xy=tuple(end), xytext=tuple(start), xycoords='data', textcoords='data', annotation_clip=False,
                      arrowprops=dict(arrowstyle='-|>', color=color, lw=connector_width, shrinkA=0, shrinkB=0,
                                      mutation_scale=7 + 3 * connector_width))
    _edge_labels(F, edge_labels, curves, fs * .9)
    for sec in sections:                                     # Abschnitte: Balken mit Endpunkten unter dem Profil, Text darunter
        col = sec.get('color') or 'black'
        if not is_color_like(col): raise ValueError('Invalid section colour')
        blend = F.ax.get_xaxis_transform()                   # x in Schritten wie die Plateaus, y in Achsenbruchteilen
        F.ax.plot([sec['a'], sec['b']], [.075, .075], transform=blend, color=col, lw=max(1.2, width * .6), marker='o',
                  ms=5, mfc=col, mec=col, clip_on=False, zorder=3, solid_capstyle='butt')
        if sec.get('text'):
            F.ax.text(.5 * (sec['a'] + sec['b']), .055, sec['text'], transform=blend, ha='center', va='top', fontsize=fs,
                      color=col, **font)
    for point, color in breaks:
        x, y = (point[0]-x0)/(x1-x0), (point[1]-y0)/(y1-y0)
        for shift in (-.006, .006):
            F.ax.plot([x-.013, x+.013], [y+shift-.009, y+shift+.009], transform=F.ax.transAxes,
                      color=color, lw=connector_width, clip_on=False)
    return F, notes


class LinkMouse:
    """Plateaus im Bild verknüpfen (Nutzerwunsch 2026-11-11, „node-artig“): am Ende eines Plateaus drücken, auf ein
    anderes Plateau ziehen, loslassen -> on_link(uid_von, uid_nach). Die Plateaulinie selbst greifen und ziehen
    verschiebt das Plateau (Nutzerwunsch 2026-11-13): waagerecht im Raster `SNAP`, mit `free_y` (schematisches Bild)
    auch in der Höhe -> on_move(uid, x, y oder None). Nur in der Vorschau, nie im Export."""
    GRAB = 10                                                # Fangweite in Pixeln
    SNAP = .05                                               # Raster der Position beim Ziehen (Schritte)

    def __init__(self, F, rows, on_link, on_move=None, free_y=False):
        self.F, self.rows, self.on_link, self.src, self.line = F, rows, on_link, None, None
        self.on_move, self.free_y, self.drag, self.ghost = on_move, free_y, None, None
        c = F.fig.canvas
        self.cids = [c.mpl_connect('button_press_event', self.press), c.mpl_connect('motion_notify_event', self.move),
                     c.mpl_connect('button_release_event', self.release)]
        xs = [r['x'] + s * r['width'] / 2 for r in rows for s in (-1, 1)]
        ys = [r['plot_y'] for r in rows for _ in (0, 1)]
        self.handles, = F.ax.plot(xs, ys, 'o', mfc='white', mec='#4d8fdc', ms=4.5, mew=1, zorder=7, clip_on=False)

    def disconnect(self):
        for cid in self.cids:
            self.F.fig.canvas.mpl_disconnect(cid)

    def _px(self, x, y):
        return self.F.ax.transData.transform((x, y))

    def end_at(self, ev):
        for r in self.rows:
            for side in (-1, 1):
                px = self._px(r['x'] + side * r['width'] / 2, r['plot_y'])
                if abs(px[0] - ev.x) <= self.GRAB and abs(px[1] - ev.y) <= self.GRAB:
                    return r, side
        return None

    def row_at(self, ev, tol=None):
        tol = self.GRAB + 4 if tol is None else tol
        for r in self.rows:
            left, right = self._px(r['x'] - r['width'] / 2, r['plot_y']), self._px(r['x'] + r['width'] / 2, r['plot_y'])
            if left[0] - self.GRAB <= ev.x <= right[0] + self.GRAB and abs(left[1] - ev.y) <= tol:
                return r
        return None

    def press(self, ev):
        hit = self.end_at(ev) if ev.button == 1 and ev.x is not None else None
        if hit:
            r, side = hit
            self.src = r
            x, y = r['x'] + side * r['width'] / 2, r['plot_y']
            self.line, = self.F.ax.plot([x, x], [y, y], color='#4d8fdc', lw=1.2, ls=':', zorder=8, clip_on=False)
            return
        if self.on_move is None or ev.button != 1 or ev.x is None or ev.xdata is None:
            return
        if any(a.get_window_extent().contains(ev.x, ev.y) for a in self.F.ann_items.values()):
            return                                           # auf einer Beschriftung: die zieht der Dragger
        r = self.row_at(ev, 6)
        if r is not None:
            self.drag = (r, ev.xdata - r['x'], ev.ydata - r['plot_y'], ev.x, ev.y)
            self.ghost, = self.F.ax.plot([r['x'] - r['width'] / 2, r['x'] + r['width'] / 2], [r['plot_y']] * 2,
                                         color='#4d8fdc', lw=2.4, zorder=8, clip_on=False, solid_capstyle='butt')

    def _drag_pos(self, ev):
        r, dx, dy, *_ = self.drag
        return round((ev.xdata - dx) / self.SNAP) * self.SNAP, (ev.ydata - dy) if self.free_y else r['plot_y']

    def move(self, ev):
        if self.drag is not None:
            if ev.xdata is not None:
                x, y = self._drag_pos(ev)
                half = self.drag[0]['width'] / 2
                self.ghost.set_data([x - half, x + half], [y, y])
                self.F.fig.canvas.draw_idle()
            return
        if self.src is None or ev.xdata is None:
            return
        x0, y0 = self.line.get_xdata()[0], self.line.get_ydata()[0]
        self.line.set_data([x0, ev.xdata], [y0, ev.ydata])
        self.F.fig.canvas.draw_idle()

    def release(self, ev):
        if self.drag is not None:
            r, _dx, _dy, px, py = self.drag
            moved = ev.x is not None and ev.xdata is not None and (abs(ev.x - px) > 3 or abs(ev.y - py) > 3)
            pos = self._drag_pos(ev) if moved else None
            self.drag = None
            self.ghost.remove()
            self.ghost = None
            self.F.fig.canvas.draw_idle()
            if pos is not None:
                self.on_move(r['uid'], round(pos[0], 2), round(pos[1], 2) if self.free_y else None)
            return
        if self.src is None:
            return
        src, self.src = self.src, None
        self.line.remove()
        self.line = None
        target = self.row_at(ev) if ev.x is not None else None
        self.F.fig.canvas.draw_idle()
        if target is not None and target['uid'] != src['uid']:
            self.on_link(src['uid'], target['uid'])


def _images(pages, cfg, rows, span):
    """Strukturen an den Plateaus und Bilder (Orbitale, Strukturen) des Profils: Platz darüber reservieren, über den
    Bildweg der Abbildung laufen lassen (Bildschirmfarben berühren Exporte nie). -> Hinweise"""
    from pathlib import Path
    from elucida.app import project as PRJ
    from elucida.core import images as IMG
    notes, structures = [], []
    for r in rows:
        path = r.get('structure')
        if not path or (Path(path).exists() and Path(path).suffix.lower() == '.cdxml'
                        and not PRJ.cdxml_has_content(path)):
            continue
        try:
            asset = IMG.load_structure(path)
            if asset is None:
                raise ValueError(T('dft_prof_structure_unreadable'))
            structures.append((r, asset))
        except Exception as ex:
            notes.append(f"{r['label']}: {ex}")
    xspan = cfg['xlim'][1] - cfg['xlim'][0]
    if any(a['mode'] == 'levels' for a in pages.prof.get('annotations', [])):
        cfg['ylim'][1] += .75 * span
    elif structures:
        cfg['ylim'][1] += .45 * span
    yspan = cfg['ylim'][1] - cfg['ylim'][0]
    placed = []
    for r, asset in structures:
        width = min(.22, .68 / xspan)
        ratio = asset['rgba'].shape[0] / asset['rgba'].shape[1]
        fw, fh = cfg['figsize_in']
        axratio = fw * cfg['axes_rect'][2] / (fh * cfg['axes_rect'][3])
        height = width * ratio * axratio
        if height > .22:
            width *= .22 / height
        width = r.get('structure_width') or width
        anchor = [(r['x']-cfg['xlim'][0])/xspan, (r['plot_y']-cfg['ylim'][0])/yspan]
        offset = r.get('structure_offset') or [-width/2, .085]
        pos = [anchor[0]+offset[0], anchor[1]+offset[1]]
        if not r.get('structure_offset'):              # gleiche Stufe auf zwei Pfaden: nebeneinander statt übereinander
            while any(abs(pos[0]-q[0]) < width and abs(pos[1]-q[1]) < height for q in placed):
                pos[0] += width * 1.05
        placed.append(pos)
        cfg['images'].append(dict(id='profile_' + r['uid'], file=r['structure'], _asset=asset,
                                  width=width, frame=False, _anchor_af=anchor, pos=pos))
    from elucida.tabs.profile_annotations import append_images
    notes += append_images(pages, cfg, {('species', r['uid']): (r['x'], r['plot_y']) for r in rows}, mode='levels')
    return notes

