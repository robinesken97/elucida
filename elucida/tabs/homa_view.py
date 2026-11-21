"""HOMA in den Tabs X-Ray und DFT (Paket A 1.2.0): Karte „Aromatizität (HOMA)“ im Schritt Auswertung, Seite „HOMA“
rechts (Tabelle je Ring), Werte wahlweise in der Ringmitte des Molekülbilds (ziehbar), SI-Tabelle und CSV.
Rechnung in `core/homa.py`; Ringe wie im Packungsbild (`xray.mol_rings`: ebene 5–7-Ringe ohne Sehne)."""
from pathlib import Path

import matplotlib.patheffects as PE
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QVBoxLayout

from elucida.app import style as STYLE
from elucida.app.i18n import T
from elucida.core import homa as H
from elucida.tabs import xray as XRAY

DEFAULTS = dict(homa_var="homa", homa_fig=False, homa_si=False)
NICS_KEYS = ("0", "1", "1zz")


def ring_name(labels):
    """Ringatome kurz wie in Kristallstrukturberichten: drei und mehr fortlaufende Nummern desselben Elements als
    Bereich („C2–C5, N2, C16“), sonst einzeln; Reihenfolge entlang des Rings."""
    import re

    def key(x):
        m = re.match(r"^([A-Za-z]+)(\d+)(.*)$", x)
        return (m.group(1), int(m.group(2)), m.group(3)) if m else None

    ks = [key(x) for x in labels]

    def step(a, b):
        if ks[a] is None or ks[b] is None or ks[a][0] != ks[b][0] or ks[a][2] != ks[b][2]:
            return 0
        d = ks[b][1] - ks[a][1]
        return d if d in (1, -1) else 0
    out, i = [], 0
    while i < len(labels):
        j = i
        d = step(i, i + 1) if i + 1 < len(labels) else 0
        while d and j + 1 < len(labels) and step(j, j + 1) == d:
            j += 1
        if j - i >= 2:
            out.append(f"{labels[i]}–{labels[j]}")
            i = j + 1
        else:
            out.append(labels[i])
            i += 1
    if len(out) == 1 and ks[0] and ks[-1] and ks[0][1] > ks[-1][1]:     # ganzer Ring ein Bereich: aufsteigend
        out = [f"{labels[-1]}–{labels[0]}"]
    return ", ".join(out)


def ring_id(mol, ring):
    return "homa_" + "-".join(sorted(mol.atoms[k]["key"] for k in ring))


class HomaView:
    def __init__(self, tab, lay, nics=False):
        self.tab, self.nics = tab, nics
        for k, v in DEFAULTS.items():
            tab.st.setdefault(k, v)
        g = QGroupBox(T("homa_card"))
        g.setToolTip(T("homa_card_tip"))
        f = STYLE.make_form(g)
        self.cmb_var = QComboBox()
        for key in H.PARAMS:
            self.cmb_var.addItem(T("homa_var_" + key), key)
        self.cmb_var.setToolTip(T("homa_var_tip"))
        f.addRow(T("homa_var"), self.cmb_var)
        self.cb_fig = QCheckBox(T("homa_fig"))
        self.cb_fig.setToolTip(T("homa_fig_tip"))
        self.cb_si = QCheckBox(T("homa_si"))
        self.cb_si.setToolTip(T("homa_si_tip"))
        f.addRow(self.cb_fig)
        f.addRow(self.cb_si)
        from elucida.tabs.base import si_elsewhere
        si_elsewhere(f, self.cb_si, tab, tab.STATE_KEY, "HOMA")
        self.lbl_hint = STYLE.HintLabel("")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet(STYLE.HINT_CSS)
        f.addRow(self.lbl_hint)
        lay.addWidget(g)
        self.card = g
        self.cmb_var.currentIndexChanged.connect(self.changed)
        self.cb_fig.toggled.connect(self.changed)
        self.cb_si.toggled.connect(self.changed)
        # Ergebnisseite (arrange -> to_right)
        self.page = QGroupBox(T("homa_page"))
        self.page.setProperty("hug", True)
        v = QVBoxLayout(self.page)
        heads = [T("homa_col_ring"), "n" + STYLE.QTY, "HOMA", "EN", "GEO", "R_av [Å]",
                 "NICS(0) [ppm]", "NICS(1) [ppm]", "NICS(1)zz [ppm]", T("homa_col_note")]
        self.tbl = STYLE.name_table(STYLE.summary_grid(heads), "HOMA", "HOMA")   # Rohwerte: _HOMA.csv
        self.tbl.elide_col = 0                              # lange Ringe gekürzt, voller Name im Tooltip
        STYLE.rich_header(self.tbl)
        v.addWidget(self.tbl)
        self.lbl = STYLE.SciLabel(empty=T("homa_none"))
        self.lbl.setWordWrap(True)
        v.addWidget(self.lbl)
        lay.addWidget(self.page)

    # -- Zustand ---------------------------------------------------------------------------
    def sync(self):
        st = self.tab.st
        for w in (self.cmb_var, self.cb_fig, self.cb_si):
            w.blockSignals(True)
        self.cmb_var.setCurrentIndex(max(0, self.cmb_var.findData(st.get("homa_var", "homa"))))
        self.cb_fig.setChecked(bool(st.get("homa_fig")))
        self.cb_si.setChecked(bool(st.get("homa_si")))
        for w in (self.cmb_var, self.cb_fig, self.cb_si):
            w.blockSignals(False)

    def changed(self, *_):
        self.tab.st.update(homa_var=self.cmb_var.currentData(), homa_fig=self.cb_fig.isChecked(),
                           homa_si=self.cb_si.isChecked())
        self.tab.render()

    # -- Rechnung --------------------------------------------------------------------------
    def molecule(self, e):
        if e is None:
            return None
        try:
            return self.tab.molecule(e, interactive=False)
        except TypeError:                                     # X-Ray: molecule(e)
            return self.tab.molecule(e)

    def rings(self, e, mol=None):
        """-> [dict(ring, id, name, res, nics)] in fester Reihenfolge (wie Cg1, Cg2 … im Packungsbild)."""
        mol = mol or self.molecule(e)
        if mol is None:
            return []
        els = [a["el"] for a in mol.atoms]
        xyz = [a["xyz"] for a in mol.atoms]
        var = self.tab.st.get("homa_var", "homa")
        nics = self.nics_points(e) if self.nics else []
        out = []
        for r in XRAY.mol_rings(mol):
            res = H.homa(H.ring_bonds(els, xyz, r), var)
            nv = {}
            for pts in nics:
                nv.update({k: v for k, v in H.nics_for_ring(xyz, r, pts).items() if k not in nv})
            out.append(dict(ring=r, id=ring_id(mol, r), res=res, nics=nv,
                            name=ring_name([XRAY.atom_name(mol.atoms[k]) for k in r])))
        return out

    def nics_points(self, e):
        """NICS-Punkte des DFT-Tabs, deren Rechnung dieselbe Geometrie hat (gleiche Atome, ± 0.02 Å); sonst keine."""
        import numpy as np
        try:
            data, _ = self.tab.pages.nics_data()
            g = self.tab.geometry(e)
        except Exception:
            return []
        if g is None:
            return []
        from elucida.formats.calc import parse_nics, read_text
        out = []
        for d in data:
            if d.get("grid") or d.get("pts") is None:          # 3D-Gitter: keine Einzelpunkte über den Ringen
                continue
            n = self.tab.cache(("nics", d["file"]), lambda p=d["file"]: parse_nics(read_text(p)))   # wie dft_pages
            xyz = np.asarray(n["xyz"], float)
            if list(n["els"]) != list(g[1]) or xyz.shape != np.shape(g[2]) \
                    or np.abs(xyz - np.asarray(g[2], float)).max() > 0.02:
                continue
            out.append(d["pts"])
        return out

    # -- Seite und Karte -------------------------------------------------------------------
    def refresh(self):
        self.sync()
        e = self.tab.entry()
        rows = self.rings(e) if e is not None else []
        table, hidden = [], set()
        for r in rows:
            res = r["res"]
            note = T("homa_missing", bonds=", ".join(H.bond_name(t) for t in res["missing"])) if res["missing"] else ""
            table.append([r["name"], str(res["n"]), H.fmt(res["value"]), H.fmt(res["en"]), H.fmt(res["geo"]),
                          H.fmt(res["mean"])] + [XRAY.core.fmt_num(r["nics"][k], 1) if k in r["nics"] else "–"
                                                  for k in NICS_KEYS] + [note])
        for j, k in enumerate(NICS_KEYS):
            if not any(k in r["nics"] for r in rows):
                hidden.add(6 + j)
        if not any(t[-1] for t in table):
            hidden.add(9)
        STYLE.fill_summary(self.tbl, table, hidden)
        notes = []
        if rows:
            notes.append(self.method_sentence())
        self.lbl.setText("\n".join(notes), plain=bool(rows))
        n_ok = sum(r["res"]["value"] is not None for r in rows)
        self.lbl_hint.setText(T("homa_hint", n=len(rows), ok=n_ok) if e is not None else "")

    def method_sentence(self, markup=False):
        """Satz unter der Tabelle (markup=False, Formelzeichen über SciLabel) bzw. Fußnote der SI-Tabelle (Markup);
        englisch, ohne Programmnamen, mit Zitat."""
        p = H.PARAMS[self.tab.st.get("homa_var", "homa")]
        src = "calculated geometry" if self.nics else "atomic coordinates"
        if markup:
            f = (f"{p['name']} = 1 − (1/*n*) Σ *α*(*R*_{{opt}} − *R*_{{i}})^{{2}} with *R*_{{opt}} and *α* per bond "
                 f"type from {XRAY.esc_markup(p['cite'])}")
            ri = "*R*_{i}"
        else:
            f = f"{p['name']} = 1 − (1/n) Σ α (R_opt − R_i)² with R_opt and α per bond type from {p['cite']}"
            ri = "R_i"
        return (f"{f}; bond lengths {ri} from the {src}. EN and GEO (HOMA = 1 − EN − GEO; {H.EN_GEO_CITE}) are given "
                "only for rings with a single bond type; rings with a bond type without parameters have no value.")

    # -- Abbildung -------------------------------------------------------------------------
    def reserve(self, opts, e, mol):
        """Ringmitten mit Wert vor dem Platzieren der Atomlabels belegen (opts["ring_marks"], XrayFigure._labels)."""
        if self.tab.st.get("homa_fig") and e is not None and mol is not None:
            opts["ring_marks"] = [tuple(r["ring"]) for r in self.rings(e, mol) if r["res"]["value"] is not None]

    def annotate(self, F, e):
        """Wert in der Ringmitte (ziehbar wie die Atomlabels; Versatz im Layout unter „homa_…“)."""
        if F is None or not self.tab.st.get("homa_fig") or e is None:
            return
        o = F.opts
        fs = o.get("label_size") or F.cfg["labels"]["font_size"]
        halo = [PE.withStroke(linewidth=2.2 * F.cfg.get("scale", 1.0), foreground=F.bg_show)]
        if not hasattr(F, "auto_pos"):
            F.auto_pos = {}
        for r in self.rings(e, F.mol):
            if r["res"]["value"] is None or any(k not in F.scene["by_k"] for k in r["ring"]):
                continue
            key = r["id"]
            pos = F.layout.get(key) or [0.0, 0.0]
            ann = F.ax.annotate(H.fmt(r["res"]["value"]), xy=F._anchor(tuple(r["ring"])), xycoords="data",
                                xytext=tuple(pos), textcoords="offset points", ha="center", va="center",
                                fontsize=fs, zorder=61, color="black", annotation_clip=False, path_effects=halo)
            ann._atom = tuple(r["ring"])
            F.ann_items[key] = ann
            F.order.append(ann)
            F.auto_pos[key] = [0.0, 0.0]

    # -- SI und Export ---------------------------------------------------------------------
    def table(self, e):
        """-> (Kopf, Zeilen als Markup, NICS-Spalten) wie in der SI."""
        rows = self.rings(e)
        keys = [k for k in NICS_KEYS if any(k in r["nics"] for r in rows)]
        p = H.PARAMS[self.tab.st.get("homa_var", "homa")]
        head = ["Ring", "*n*", p["name"], "EN", "GEO", "*R*_{av} / Å"] + \
               [{"0": "NICS(0) / ppm", "1": "NICS(1) / ppm", "1zz": "NICS(1)_{zz} / ppm"}[k] for k in keys]
        out = []
        for r in rows:
            res = r["res"]
            out.append([XRAY.esc_markup(r["name"]), str(res["n"]), H.fmt(res["value"]), H.fmt(res["en"]),
                        H.fmt(res["geo"]), H.fmt(res["mean"])]
                       + [XRAY.core.fmt_num(r["nics"][k], 1) if k in r["nics"] else "–" for k in keys])
        return head, out, rows

    def si_blocks(self, e, name):
        if not self.tab.st.get("homa_si") or e is None:
            return []
        head, rows, rr = self.table(e)
        if not rows:
            return []
        notes = [self.method_sentence(markup=True)]
        miss = sorted({t for r in rr for t in r["res"]["missing"]})
        if miss:
            notes.append("Bond types without parameters: " + ", ".join(H.bond_name(t) for t in miss) + ".")
        return [("tabcap", "HOMA values of the rings of", name),
                ("params", head, rows, {"fit": True})] + [("note", n) for n in notes]

    def export_csv(self, path, items):
        """items = [(Name, Eintrag)] -> CSV mit allen Ringen (gleiche Zahlen wie Tabelle/SI, ASCII-Minus)."""
        lines = []
        for name, e in items:
            for r in self.rings(e):
                res = r["res"]
                lines.append([name, r["name"], res["n"]] + [("" if v is None else f"{v:.3f}") for v in
                             (res["value"], res["en"], res["geo"], res["mean"])]
                             + [f"{r['nics'][k]:.1f}" if k in r["nics"] else "" for k in NICS_KEYS]
                             + ["; ".join(H.bond_name(t) for t in res["missing"])])
        if not lines:
            return []
        from elucida.core import tables as TBL
        path = TBL.write_csv(Path(path), ["Structure", "Ring", "n", H.PARAMS[self.tab.st.get("homa_var", "homa")]["name"],
                                          "EN", "GEO", "R_av [Å]", "NICS(0) [ppm]", "NICS(1) [ppm]", "NICS(1)zz [ppm]",
                                          "Missing parameters"], lines)
        return [path]
