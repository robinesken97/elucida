"""Presentation-only energy-profile layout; calculation values are never edited here."""
from copy import deepcopy
import math

import numpy as np
from matplotlib.colors import is_color_like
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
                               QDoubleSpinBox, QCheckBox, QPushButton, QLabel, QDialogButtonBox, QScrollArea, QFrame)
from elucida.app.i18n import T
from elucida.app import style as STYLE
from elucida.app.canvas_theme import register
from elucida.tabs import base as TABS

SCHEMATIC_NOTE = 'Schematic profile; vertical spacing is not to scale.'


def number(obj, key, default, low=-1e5, high=1e5):
    value = obj.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid diagram layout: ' + key)
    return value


def arranged(rows, layout):
    """Return drawing coordinates separately from each unmodified energy value."""
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
                           plot_y=number(node, 'y', r['value']) if schematic else r['value'],
                           width=number(node, 'width', .7, .05, 20), color=color,
                           break_after=bool(node.get('break_after')) and schematic, **offsets))
    return result


def build_levels(pages, fig, layout):
    from elucida.tabs.dft_pages import KINDS, kcal
    source, paths, notes = pages.levels_spec()
    if not source: return None, notes
    rows = arranged(source, layout)
    schematic = layout.get('mode', 'scaled') == 'schematic'
    cfg = pages.cfg('levels')
    cfg['images'] = []  # molecules and orbital images live on the free canvas
    cfg['ylabel'] = KINDS[pages.prof['y']][0] + ' [kcal mol$^{-1}$]'
    if schematic: cfg['ylabel'] += ' (schematic)'
    xs = [r['x'] - r['width']/2 for r in rows] + [r['x'] + r['width']/2 for r in rows]
    ys = [r['plot_y'] for r in rows]
    xspan, yspan = max(max(xs)-min(xs), 1), max(max(ys)-min(ys), 1)
    cfg['xlim'] = [min(xs)-.12*xspan, max(xs)+.12*xspan]
    cfg['ylim'] = [min(ys)-.2*yspan, max(ys)+.2*yspan]
    width = number(layout, 'line_width', 2.2, .1, 10)
    connector_width = number(layout, 'connector_width', .8, .1, 10)
    fs = number(layout, 'font_size', cfg['labels']['font_size'], 4, 40)
    linestyle = layout.get('connector_style', '--')
    if linestyle not in ('-', '--', ':', 'none'): raise ValueError('Invalid connector style')
    default = layout.get('color', 'black')
    if not is_color_like(default): raise ValueError('Invalid diagram colour')
    curves, breaks = [], []
    colors = {p: pages.prof.get('colors', {}).get(p, default) for p in paths}
    for p in paths:
        # Row/path order is scientific input. Moving a plateau must not reorder a mechanism.
        branch = [r for r in rows if p in r['paths']]
        for a, b in zip(branch, branch[1:]):
            start = np.array([a['x']+a['width']/2, a['plot_y']])
            end = np.array([b['x']-b['width']/2, b['plot_y']])
            col = a['color'] or colors[p]
            if linestyle == 'none': continue
            segments = [(start, end)]
            if a['break_after']:
                segments = [(start, start+.44*(end-start)), (start+.56*(end-start), end)]
                breaks.append((.5*(start+end), col))
            for left, right in segments:
                curves.append(dict(x=np.array([left[0], right[0]]), y=np.array([left[1], right[1]]),
                                   color=col, ls=linestyle, lw=connector_width, label=None))
    for r in rows:
        color = r['color'] or (colors[r['paths'][0]] if len(r['paths']) == 1 else default)
        curves.append(dict(x=np.array([r['x']-r['width']/2, r['x']+r['width']/2]),
                           y=np.array([r['plot_y']]*2), color=color, ls='-', lw=width, label=None))
    F = TABS.X.SimpleFigure(TABS.plt, cfg, curves, [], {}, fig=fig, legend=False)
    F.ax.set_xticks([])
    if schematic:
        F.ax.set_yticks([])
        F.fig.text(.5, .025, SCHEMATIC_NOTE, ha='center', va='bottom', fontsize=max(7, fs*.8))
    x0, x1 = cfg['xlim']; y0, y1 = cfg['ylim']
    for r in rows:
        color = r['color'] or 'black'
        F.ax.text(r['x']+r['energy_dx']*(x1-x0), r['plot_y']+r['energy_dy']*(y1-y0),
                  kcal(r['value']), ha='center', va='bottom', fontsize=fs, color=color,
                  gid='energy-'+r['uid'])
        F.ax.text(r['x']+r['label_dx']*(x1-x0), r['plot_y']+r['label_dy']*(y1-y0),
                  r['label'], ha='center', va='top', fontsize=fs, color=color, gid='label-'+r['uid'])
    for point, color in breaks:
        x, y = (point[0]-x0)/(x1-x0), (point[1]-y0)/(y1-y0)
        for shift in (-.006, .006):
            F.ax.plot([x-.013, x+.013], [y+shift-.009, y+shift+.009], transform=F.ax.transAxes,
                      color=color, lw=connector_width, clip_on=False)
    return F, notes


class DiagramLayoutEditor(QWidget):
    """Private draft with an inline preview, Apply/Cancel, no modal window."""
    finished = Signal(bool)

    def __init__(self, host, mode, layout, frame):
        super().__init__()
        self.host, self.mode, self.data, self.loading = host, mode, deepcopy(layout), True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(12)
        hint = QLabel(T('rp_layout_hint')); hint.setWordWrap(True)
        hint.setProperty('formlabel', True); outer.addWidget(hint)
        body = QHBoxLayout(); outer.addLayout(body, 1)
        settings_card, controls = STYLE.card(T('rp_layout_settings'))
        form = QFormLayout(controls); form.setContentsMargins(0, 0, 0, 0)
        form.setVerticalSpacing(10); form.setHorizontalSpacing(12)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(settings_card); scroll.setMinimumWidth(310); scroll.setMaximumWidth(380)
        body.addWidget(scroll)
        self.presentation = QComboBox()
        for key in ('scaled', 'schematic'): self.presentation.addItem(T('rp_layout_'+key), key)
        self.presentation.setCurrentIndex(self.presentation.findData(self.data.get('mode', 'scaled')))
        self.presentation.setEnabled(mode == 'levels')
        form.addRow(T('rp_layout_mode'), self.presentation)
        self.frame = QCheckBox(); self.frame.setChecked(frame); form.addRow(T('rp_show_diagram_frame'), self.frame)
        self.frame.setEnabled(mode == 'levels')
        self.defaults = dict(line_width=2.2 if mode == 'levels' else 1.2, connector_width=.8,
                             font_size=host.tab.pages.cfg(mode)['labels']['font_size'])
        self.default_style = '--' if mode == 'levels' else '-'
        self.global_fields = {}
        for key, text, low, high in [('line_width', 'rp_plateau_line', .1, 10),
                ('connector_width', 'rp_connector_line', .1, 10), ('font_size', 'rp_layout_font', 4, 40)]:
            spin = QDoubleSpinBox(); spin.setRange(low, high); spin.setDecimals(1); spin.setValue(self.data.get(key, self.defaults[key]))
            spin.setSingleStep(.1 if high == 10 else 1)
            spin.editingFinished.connect(self.changed); form.addRow(T(text), spin); self.global_fields[key] = spin
        self.connector = QComboBox()
        for key, text in [('--', 'rp_line_dashed'), ('-', 'rp_line_solid'), (':', 'rp_line_dotted'), ('none', 'rp_line_none')]:
            self.connector.addItem(T(text), key)
        self.connector.setCurrentIndex(max(0, self.connector.findData(self.data.get('connector_style', self.default_style))))
        form.addRow(T('rp_connector_style'), self.connector)
        self.node = QComboBox()
        self.rows = host.tab.pages.levels_spec()[0] if mode == 'levels' else []
        for r in self.rows: self.node.addItem(r['label'], r['uid'])
        form.addRow(T('rp_layout_plateau'), self.node)
        self.fields = {}
        for key, text, low, high, decimals in [('x', 'rp_layout_x', -1000, 1000, 2),
                ('width', 'rp_plateau_width', .05, 20, 2), ('y', 'rp_layout_height', -10000, 10000, 2),
                ('energy_dx', 'rp_energy_dx', -50, 50, 1), ('energy_dy', 'rp_energy_dy', -50, 50, 1),
                ('label_dx', 'rp_label_dx', -50, 50, 1), ('label_dy', 'rp_label_dy', -50, 50, 1)]:
            spin = QDoubleSpinBox(); spin.setRange(low, high); spin.setDecimals(decimals); spin.setSingleStep(.1 if decimals==2 else 1)
            if key.endswith(('dx', 'dy')): spin.setSuffix(' %')
            spin.editingFinished.connect(self.changed); form.addRow(T(text), spin); self.fields[key] = spin
        self.break_after = QCheckBox(); form.addRow(T('rp_break_after'), self.break_after)
        row = QHBoxLayout()
        self.color_button = QPushButton(T('rp_plateau_color')); self.color_button.clicked.connect(self.choose_color)
        reset_color = QPushButton(T('rp_auto_color')); reset_color.clicked.connect(lambda: self.set_color(None))
        row.addWidget(self.color_button); row.addWidget(reset_color); form.addRow(row)
        reset = QPushButton(T('rp_reset_layout')); reset.clicked.connect(self.reset); form.addRow(reset)
        if mode != 'levels':
            for widget in [self.node, *self.fields.values(), self.break_after, self.global_fields['connector_width']]:
                widget.hide()
                label = form.labelForField(widget)
                if label: label.hide()
            self.color_button.setText(T('rp_curve_color'))
        self.fig = Figure(); self.canvas = register(FigureCanvasQTAgg(self.fig))
        self.preview = TABS.CanvasHost(self.canvas, self.fig); body.addWidget(self.preview, 1)
        self.error = QLabel(); self.error.setWordWrap(True); outer.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText(T('rp_apply_layout'))
        self.buttons.button(QDialogButtonBox.Ok).setProperty('accent', True)
        self.buttons.button(QDialogButtonBox.Ok).setIcon(STYLE.icon('check'))
        self.buttons.accepted.connect(lambda: self.finished.emit(True))
        self.buttons.rejected.connect(lambda: self.finished.emit(False)); outer.addWidget(self.buttons)
        self.node.currentIndexChanged.connect(self.select_node)
        self.presentation.currentIndexChanged.connect(self.mode_changed)
        self.connector.currentIndexChanged.connect(self.changed)
        self.frame.toggled.connect(self.changed); self.break_after.toggled.connect(self.changed)
        self.loading = False
        self.select_node()

    def node_data(self):
        return self.data.setdefault('nodes', {}).setdefault(self.node.currentData(), {})

    def select_node(self, *_):
        self.loading = True
        if self.rows:
            r = self.rows[self.node.currentIndex()]; node = self.node_data()
            for key, spin in self.fields.items():
                default = dict(x=r['step'], width=.7, y=r['value'], energy_dx=0, energy_dy=.025, label_dx=0, label_dy=-.025)[key]
                spin.setValue(node.get(key, default) * (100 if key.endswith(('dx','dy')) else 1))
            self.break_after.setChecked(bool(node.get('break_after')))
        for widget in [self.node, *self.fields.values(), self.break_after]: widget.setEnabled(bool(self.rows))
        self.loading = False
        self.render()

    def changed(self, *_):
        if self.loading: return
        self.data['mode'] = self.presentation.currentData() if self.mode == 'levels' else 'scaled'
        for key, spin in self.global_fields.items(): self.data[key] = spin.value()
        self.data['connector_style'] = self.connector.currentData()
        if self.rows:
            node = self.node_data()
            for key, spin in self.fields.items():
                if key == 'y' and self.data['mode'] != 'schematic': continue
                node[key] = spin.value() / (100 if key.endswith(('dx','dy')) else 1)
            node['break_after'] = self.break_after.isChecked()
        self.render()

    def mode_changed(self, *_):
        if self.loading: return
        self.loading = True
        if self.rows:
            r = self.rows[self.node.currentIndex()]
            self.fields['y'].setValue(self.node_data().get('y', r['value']) if self.presentation.currentData() == 'schematic' else r['value'])
        self.loading = False
        self.changed()

    def choose_color(self):
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor
        current = self.node_data() if self.rows else self.data
        color = QColorDialog.getColor(QColor(current.get('color') or 'black'), self, T('rp_plateau_color'))
        if color.isValid(): self.set_color(color.name())

    def set_color(self, color):
        if self.rows:
            self.node_data()['color'] = color
        else: self.data['color'] = color or 'black'
        self.render()

    def reset(self):
        self.data = {}
        self.loading = True
        self.presentation.setCurrentIndex(0)
        self.connector.setCurrentIndex(self.connector.findData(self.default_style))
        for key, spin in self.global_fields.items(): spin.setValue(self.defaults[key])
        self.loading = False; self.select_node()

    def render(self):
        schematic = self.data.get('mode', 'scaled') == 'schematic' and self.mode == 'levels'
        self.fields['y'].setEnabled(schematic); self.break_after.setEnabled(schematic)
        try:
            from elucida.app.path_composition import profile_figure
            F, _ = profile_figure(self.host, self.mode, self.frame.isChecked(), self.data, self.fig)
            self.preview.set_figure_size(*F.fig.get_size_inches())
            self.error.clear(); self.buttons.button(QDialogButtonBox.Ok).setEnabled(True)
        except Exception as ex:
            self.error.setText(str(ex)); self.buttons.button(QDialogButtonBox.Ok).setEnabled(False)
