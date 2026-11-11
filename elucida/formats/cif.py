"""
elucida/formats/cif.py - CIF-Leser (eigener, Werte als Text wie in der Datei): Blöcke, Schleifen, Zahlen mit Standardabweichung.
"""
from __future__ import annotations

import re
from pathlib import Path


_NUM = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)(?:\((\d+)\))?$")


def _tokens(text):
    """-> (Token, in Anführungszeichen?) – Textfelder ;…; als ein Token."""
    lines = text.splitlines()
    i, n_lines = 0, len(lines)
    while i < n_lines:
        line = lines[i]
        if line.startswith(";"):
            buf = [line[1:]]
            i += 1
            while i < n_lines and not lines[i].startswith(";"):
                buf.append(lines[i])
                i += 1
            i += 1
            yield "\n".join(buf).strip("\n"), True
            continue
        p, n = 0, len(line)
        while p < n:
            c = line[p]
            if c.isspace():
                p += 1
                continue
            if c == "#":
                break
            if c in "'\"":
                j = p + 1
                while j < n and not (line[j] == c and (j + 1 == n or line[j + 1].isspace())):
                    j += 1
                yield line[p + 1:j], True
                p = j + 1
                continue
            j = p
            while j < n and not line[j].isspace():
                j += 1
            yield line[p:j], False
            p = j
        i += 1


class Block:
    """Ein data_-Block: Einzelwerte und Schleifen, Tags in Kleinbuchstaben."""

    def __init__(self, name):
        self.name = name
        self.items = {}          # tag -> Text
        self.loops = []          # [{tag: [Werte]}]
        self.loop_of = {}        # tag -> Schleife
        self.incomplete = set()  # Tags von Schleifen mit unvollständiger letzter Zeile (abgeschnittene Datei)

    def get(self, *tags):
        """Erster vorhandener Tag (Aliase DDL1/DDL2); '?' und '.' gelten als fehlend."""
        for t in tags:
            v = self.items.get(t.lower())
            if v is None and t.lower() in self.loop_of:
                col = self.loop_of[t.lower()][t.lower()]
                v = col[0] if len(col) == 1 else None
            if v is not None and v not in ("?", "."):
                return v
        return None

    def num(self, *tags):
        return num(self.get(*tags))

    def column(self, *tags):
        for t in tags:
            lp = self.loop_of.get(t.lower())
            if lp is not None:
                return lp[t.lower()]
            if t.lower() in self.items:
                return [self.items[t.lower()]]
        return None

    def rows(self, first, *more):
        """Zeilen der Schleife mit Tag 'first' als dicts (fehlende Spalten -> None)."""
        lp = self.loop_of.get(first.lower())
        if lp is None:
            if first.lower() not in self.items:
                return []
            lp = {t.lower(): [self.items[t.lower()]] for t in (first,) + more if t.lower() in self.items}
        n = len(lp[first.lower()])
        return [{k: v[i] for k, v in lp.items()} for i in range(n)]


def parse_cif_text(text) -> list[Block]:
    toks = list(_tokens(text))
    blocks, cur, i, n = [], None, 0, len(toks)

    def is_key(t, q):
        return not q and (t.startswith("_") or t.lower() == "loop_" or t.lower().startswith(("data_", "save_",
                                                                                              "global_")))
    while i < n:
        tok, quoted = toks[i]
        low = tok.lower()
        if not quoted and low.startswith("data_"):
            cur = Block(tok[5:])
            blocks.append(cur)
            i += 1
            continue
        if cur is None:
            cur = Block("global")
            blocks.append(cur)
        if not quoted and low == "loop_":
            i += 1
            tags = []
            while i < n and not toks[i][1] and toks[i][0].startswith("_"):
                tags.append(toks[i][0].lower())
                i += 1
            vals = []
            while i < n and not is_key(*toks[i]):
                vals.append(toks[i][0])
                i += 1
            if tags:
                m = len(vals) // len(tags)               # unvollständige letzte Zeile verwerfen (vermerkt)
                if len(vals) % len(tags):
                    cur.incomplete.update(tags)
                lp = {t: vals[k::len(tags)][:m] for k, t in enumerate(tags)}
                cur.loops.append(lp)
                for t in tags:
                    cur.loop_of[t] = lp
            continue
        if not quoted and tok.startswith("_"):
            if i + 1 < n and not is_key(*toks[i + 1]):
                cur.items[low] = toks[i + 1][0]
                i += 2
            else:
                i += 1
            continue
        i += 1
    return blocks


def read_cif(path) -> list[Block]:
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return parse_cif_text(text)


def num(s):
    """'1.392(3)' -> 1.392; '?'/'.'/None -> None."""
    if s is None:
        return None
    m = _NUM.match(str(s).strip())
    return float(m.group(1)) if m else None


def is_cif(path):
    return Path(path).suffix.lower() == ".cif" and Path(path).is_file()
