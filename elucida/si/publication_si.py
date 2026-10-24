"""
elucida/si/publication_si.py - Gesamt-SI einer Publikation (alle Verbindungen in einer Word-Datei).

Aufbau wie die SI der Gruppe (Inhaltsverzeichnis: 1. Materials and Methods, 2. Synthetic Procedures and
Characterization Data, 3. NMR Spectra, 4. UV-Vis Spectroscopy, 5. EPR Spectroscopy, 6. Cyclic Voltammetry,
7. Spectroelectrochemistry, 8. X-Ray Characterization Data, 9. Computational Section). Innerhalb eines Kapitels die
Verbindungen in der Reihenfolge der Publikation; Kapitel ohne Inhalt fallen weg, die Nummern rücken nach. IR-/MS-Spektren
als Abbildungen (nicht in der SI der Gruppe) nur auf Wunsch, nach den NMR-Spektren. Abbildungen zwei je Seite
(SI.two_per_page), Nummern fortlaufend (SEQ-Felder). Kristalldaten aller Verbindungen in gemeinsamen Tabellen
(höchstens CRYSTAL_COLS Strukturen je Tabelle).
Ohne Qt: die Blöcke je Verbindung liefert das Hauptfenster (MainWindow.si_compound_parts).
"""
from __future__ import annotations

from elucida.si import lines as SI

# (Schlüssel, Kapitel, Standard an)
SECTIONS = (("methods", "Materials and Methods", True),
            ("char", "Synthetic Procedures and Characterization Data", True),
            ("nmr", "NMR Spectra", True),
            ("irms", "IR and Mass Spectra", False),
            ("uvvis", "UV-Vis Spectroscopy", True),
            ("epr", "EPR Spectroscopy", True),
            ("cv", "Cyclic Voltammetry", True),
            ("sec", "Spectroelectrochemistry", True),
            ("xray", "X-Ray Characterization Data", True),
            ("dft", "Computational Section", True))
FIGURE_SECTIONS = ("nmr", "irms", "uvvis", "epr", "cv", "sec")
CRYSTAL_COLS = 3
# Aufbau-Texte (lokal hinterlegt, si_setup/<Tab>) in „Materials and Methods“, in der Reihenfolge der SI
SETUP_KEYS = ("irms", "hrms", "overlay", "fluorescence", "epr", "cv", "sec")
METHODS_PLACEHOLDER = "[General information: solvents, reagents and instruments.]"


def merge_crystal(tables):
    """[(Kopf, Zeilen)] je Verbindung -> Tabellen mit höchstens CRYSTAL_COLS Strukturen (Zeilen gleich: CRYSTAL_ROWS)."""
    cols, labels = [], None
    for head, rows in tables:
        if not rows or len(head) < 2:
            continue
        labels = labels or [r[0] for r in rows]
        by_label = {r[0]: r for r in rows}
        for j in range(1, len(head)):
            cols.append((head[j], [by_label.get(lab, [lab] + [""] * len(head))[j] for lab in labels]))
    out = []
    for k in range(0, len(cols), CRYSTAL_COLS):
        part = cols[k:k + CRYSTAL_COLS]
        out.append((["Compound"] + [c[0] for c in part],
                    [[lab] + [c[1][i] for c in part] for i, lab in enumerate(labels)]))
    return out


def text_blocks(txt):
    """Freitext (Absätze durch Leerzeilen getrennt) -> Absätze wie der Charakterisierungsabsatz."""
    return [("char", SI.chem_html(p.strip())) for p in (txt or "").split("\n\n") if p.strip()]


def assemble(meta, compounds, sections, setup_texts=(), toc=True, methods=True):
    """meta: Angaben der Publikation (title, authors, affiliation). compounds: [(Name, Teile)] mit Teile =
    {char, nmr, irms, uvvis, epr, cv, sec: Blöcke; xray: Blöcke ohne Kristalltabelle; crystal: (Kopf, Zeilen) | None;
    dft: Blöcke; methods_<sec>: Blöcke}. sections: gewählte Kapitel. -> Blöcke für SI.write_docx."""
    from elucida.app.publication import paper_title
    blocks = []
    if paper_title(meta):                    # Titelblatt wie die SI der Gruppe: Titel des Artikels
        blocks.append(("title", paper_title(meta), meta.get("authors", ""), meta.get("affiliation", "")))
    if toc:
        blocks.append(("toc",))
    groups_on = any(parts.get("_group") for _, parts in compounds)   # Gruppen im Projekt -> Unterkapitel

    def grouped(blocks_of):
        """Blöcke aller Verbindungen; mit Gruppen vor jeder neuen Gruppe ein Unterkapitel (Nummer folgt später)."""
        out, cur = [], object()
        for _, parts in compounds:
            bl = blocks_of(parts)
            if not bl:
                continue
            g = parts.get("_group")
            if groups_on and g != cur:
                cur = g
                out.append(("subsection", g or "Further compounds"))
            out += bl
        return out
    n = 0
    for key, title, _ in SECTIONS:
        if key not in sections:
            continue
        intro = text_blocks((meta.get("si_texts") or {}).get(key, ""))   # Text der Publikation unter dem Kapitel
        body = []
        if key == "methods":
            body = intro or [("char", SI.chem_html(t)) for t in setup_texts if t] or [("char", METHODS_PLACEHOLDER)]
            intro = []
        elif key == "char":                          # Synthese: Unterkapitel je Gruppe (wie die SI der Gruppe)
            body = grouped(lambda parts: parts.get("char") or [])
        elif key in FIGURE_SECTIONS:
            def fig_blocks(parts, key=key):
                fb = [b for b in parts.get(key) or [] if b[0] != "pagebreak"]
                mb = (parts.get("methods_" + key) or []) if methods else []
                return mb + fb
            if key == "nmr":                         # NMR ebenfalls je Gruppe
                figs = grouped(fig_blocks)
            else:
                figs = [b for _, parts in compounds for b in fig_blocks(parts)]
            body = SI.two_per_page(intro + figs) if figs else []     # Einleitung zählt bei der Seitenaufteilung mit
            intro = []
        elif key == "xray":
            tables = []
            for _, parts in compounds:
                body += parts.get("xray") or []
                if parts.get("crystal"):
                    tables.append(parts["crystal"])
            for head, rows in merge_crystal(tables):
                body += [("gap",), ("tabcap", "Crystal data and structure refinement", ", ".join(head[1:])),
                         ("crystal", head, rows)]
        elif key == "dft":
            for _, parts in compounds:
                body += parts.get("dft") or []
            body = [("columns", 2)] + body if body else []
        if not body:
            continue
        body = intro + body                                   # DFT: Einleitung noch einspaltig
        n += 1
        k_sub = 0
        for i, b in enumerate(body):                          # Unterkapitel nummerieren: 2.1, 2.2 …
            if b[0] == "subsection":
                k_sub += 1
                body[i] = ("subsection", f"{n}.{k_sub} {b[1]}")
        blocks += [("section", f"{n}. {title}")] + body      # DFT: zweispaltig erst nach der Überschrift
    return blocks
