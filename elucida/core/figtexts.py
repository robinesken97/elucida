"""Eigene Texte für die festen Texte einer Abbildung (1.5.0): Achsentitel, Zweitachsen, Titel, Legende, Farbskala,
Inset (Achsen, Legende, Tabellenkopf). Ein Mechanismus für alle Tabs: nach dem Zeichnen werden die Texte der
matplotlib-Figur über stabile Schlüssel ersetzt; die Tabs selbst bleiben unverändert.

Schlüssel `txt:<Rolle>|<automatischer Text ohne Mathtext>` (z. B. `txt:x|wavelength [nm]`, `txt:inset.head|ε`):
die Rolle trennt gleiche Texte an verschiedenen Stellen, der automatische Text trennt die Ansichten eines Tabs (CV
„E [V vs. …]“ gegen „scan rate“) und lässt einen eigenen Text fallen, sobald der automatische etwas anderes sagt
(andere Referenz oder Einheit: der eigene Text wäre dann falsch). Eintrag {"text": …, "hidden": True} wie bei den
Labels (Karte „Beschriftungen im Bild“), Zustand `text_over` neben `label_over`, nur bei eigenem Wert gespeichert.
Ohne Eintrag wird nur gelesen, nie gesetzt: das Bild bleibt Pixel für Pixel gleich."""
from __future__ import annotations

import re

PREFIX = "txt:"


def is_text_key(key):
    return str(key).startswith(PREFIX)


_FONT_CMD = re.compile(r"\\(?:math[a-z]+|text[a-z]*)\{([^{}]*)\}")


def _plain(s):
    """Automatischer Text ohne Mathtext und ohne Schriftbefehle (\\mathtt{λ} der Symbolschrift, \\mathit{E}): derselbe
    Schlüssel mit und ohne Symbolschrift, kursiv/fett der Labels."""
    from elucida.core import tables as TBL
    prev = None
    while prev != s:
        prev, s = s, _FONT_CMD.sub(r"\1", s)
    return " ".join(TBL.plain(s.replace("{}", "")).split())


_I18N = None


def _text_id(plain):
    """Schlüsselteil eines automatischen Texts: ein deutscher Text aus der Übersetzung (z. B. „Spektrum Nr.“) wird zu
    seiner englischen Form („spectrum no.“), damit ein Sprachwechsel eigene Texte nicht verliert; englische
    Abbildungstexte bleiben, wie sie sind (unabhängig von anderen Übersetzungen).
    shortcut: nur ganze Texte; ein T()-Text mitten im Titel hinge an der Sprache – bisher gibt es keinen solchen."""
    global _I18N
    if _I18N is None:
        from elucida.app.i18n import TEXTS
        m = {}
        for k, v in sorted(TEXTS.items()):
            if isinstance(v, tuple) and len(v) >= 2 and all(isinstance(x, str) and "{" not in x for x in v[:2]):
                de, en = _plain(v[0]), _plain(v[1])
                if de != en:
                    m.setdefault(de, en)
        _I18N = m
    return _I18N.get(plain, plain)


def key_auto(key):
    """(Rolle, automatischer Text zur Anzeige) aus einem Schlüssel txt:<Rolle>|<Text>."""
    role, _, auto = str(key)[len(PREFIX):].partition("|")
    return role, auto


def _own(text, cfg):
    """Eigener Text gesetzt wie die automatischen Titel (Größen kursiv, Symbolschrift) -> Mathtext oder None, wenn er
    sich nicht setzen lässt (kaputter Text bricht nie Zeichnen oder Export)."""
    from elucida.core import uvvis as core
    if not isinstance(text, str) or not text.strip() or not core.label_text_ok(text):
        return None
    try:
        new = core.fmt_text(text, cfg)
    except Exception:
        return None
    return new if core.label_text_ok(new) else text


def _axes_names(fig, F):
    """id(Axes) -> Name: '' Hauptachse, 'r' Zweitachse, Namen aus F.axes_items (inset), 'cbar' Farbskala, sonst 'ax<i>'."""
    names = {}
    main = getattr(F, "ax", None)
    if main is not None:
        names[id(main)] = ""
    ax2 = getattr(F, "ax2", None)
    if ax2 is not None:
        names[id(ax2)] = "r"
    for k, a in (getattr(F, "axes_items", None) or {}).items():
        names.setdefault(id(a), str(k))
    n_cb = 0
    for i, a in enumerate(fig.axes):
        if id(a) in names:
            continue
        if getattr(a, "_colorbar", None) is not None:
            n_cb += 1
            names[id(a)] = "cbar" if n_cb == 1 else f"cbar{n_cb}"
        elif main is None and "" not in names.values():
            names[id(a)] = ""                              # Abbildungen ohne F.ax: die erste Achse ist die Hauptachse
        else:
            names[id(a)] = f"ax{i}"
    return names


def items(fig, F=None):
    """[(Rolle, Text-Artist)] aller ersetzbaren Texte in fester Reihenfolge (Hauptachse zuerst)."""
    names = _axes_names(fig, F)
    out = []
    for a in sorted(fig.axes, key=lambda a: (names[id(a)] != "", names[id(a)] != "r")):
        n = names[id(a)]
        pre = n + "." if n else ""
        out += [(pre + "x", a.xaxis.label), (pre + "y", a.yaxis.label)]
        out += [(pre + "title", t) for t in (a.title, a._left_title, a._right_title)]
        leg = a.get_legend()
        if leg is not None:
            out += [(pre + "legend", t) for t in leg.get_texts()]
        # Texte, die ein Tab selbst als festen Text meldet (`t._elu_role`, z. B. NTO „hole“ quer neben dem Bild)
        out += [(pre + t._elu_role, t) for t in a.texts if getattr(t, "_elu_role", None)]
        for tab in a.tables:                               # Tabellenkopf (Zeile 0); Zellen mit Werten bleiben fest
            cells = tab.get_celld()
            out += [(pre + "head", cells[k].get_text()) for k in sorted(cells) if k[0] == 0]
    for leg in fig.legends:
        out += [("fig.legend", t) for t in leg.get_texts()]
    out += [("fig." + t._elu_role, t) for t in fig.texts if getattr(t, "_elu_role", None)]   # z. B. NMR-Titel
    if getattr(fig, "_suptitle", None) is not None:
        out.append(("fig.title", fig._suptitle))
    # Texte mit eigenem Feld der Seite (Energieprofil: Achsentitel); über cfg, damit es schon vor dem Layout gilt
    skip = set(getattr(F, "text_skip", ()) or (getattr(F, "cfg", None) or {}).get("text_skip") or ())
    return [x for x in out if x[0] not in skip] if skip else out


def apply(fig, F=None, over=None, cfg=None):
    """Eigene Texte setzen (idempotent, beliebig oft je Zeichnen: vor dem Einpassen der Achse, vor dem Platzieren,
    danach) -> Zeilen für die Karte [{key, auto, text, hidden, role}] (je Schlüssel einmal).
    Merkt den automatischen Text am Artist; setzt ein Tab den Text danach neu, gilt der neue als automatisch."""
    if fig is None:
        return []
    over = over or {}
    cfg = cfg if cfg is not None else (getattr(F, "cfg", None) or {})
    rows, seen = [], set()
    try:
        found = items(fig, F)
    except Exception:                                      # fremde Figur: lieber keine Zeilen als kein Bild
        return []
    for role, t in found:
        cur = t.get_text()
        if getattr(t, "_elu_shown", None) != cur:
            t._elu_auto = cur
        auto = t._elu_auto
        plain = _plain(auto) if isinstance(auto, str) else ""
        if not plain:
            t._elu_shown = cur
            continue
        key = f"{PREFIX}{role}|{_text_id(plain)}"
        t._elu_key = key                                   # Rechtsklick im Bild -> Zeile der Karte
        o = over.get(key)
        o = o if isinstance(o, dict) else {}
        own = _own(o.get("text"), cfg)
        new = auto if own is None else own
        if new != cur:
            t.set_text(new)
        t._elu_shown = new
        if o.get("hidden"):
            t.set_visible(False)
            t._elu_hid = True
        elif getattr(t, "_elu_hid", False):               # bleibender Artist (NMR-Ansicht): wieder zeigen
            t.set_visible(True)
            t._elu_hid = False
        own = o["text"] if own is not None else None
        if key not in seen:
            seen.add(key)
            rows.append({"key": key, "auto": plain, "text": own, "hidden": bool(o.get("hidden")), "role": role,
                         "id": None})
    return rows


def key_at(fig, F, ev):
    """Schlüssel des festen Texts unter der Maus (sichtbar, schon einmal über apply gesetzt) oder None."""
    try:
        return next((t._elu_key for _, t in items(fig, F) if getattr(t, "_elu_key", None) and t.get_visible()
                     and t.contains(ev)[0]), None)
    except Exception:
        return None


def apply_to(F, fig=None, over=None):
    """Nach dem Zeichnen (Vorschau, Export, SI, Kopieren): Texte setzen und die Zeilen an F merken (`F.text_rows`)."""
    fig = fig if fig is not None else getattr(F, "fig", None)
    rows = apply(fig, F, over)
    if F is not None:
        try:
            F.text_rows = rows
        except AttributeError:                             # F ohne __dict__: Zeilen nur zurückgeben
            pass
    return rows


# -- Editor (Nutzerwunsch 1.5.0: Feld „Eigener Text“ mit dem Texteditor der Synthese, ohne Syntax) ----------------
# Gespeichert bleibt Mathtext wie bisher (alte Projekte, Zeichnen, Export unverändert); nur das Feld zeigt und
# liefert Formatierung (fett, kursiv, tief, hoch). Ungeformter Text geht wörtlich durch: „$…$“ von Hand gilt weiter.
_ESC = {"\\": r"\backslash ", "{": r"\lbrace ", "}": r"\rbrace ", "_": r"\_", "^": r"\textasciicircum ", "$": r"\$",
        "#": r"\#", "%": r"\%", " ": r"\ ", "~": r"\sim "}
_FONT_OF = {frozenset("i"): "mathit", frozenset("b"): "mathbf", frozenset("bi"): "mathbfit"}


def _runs_of_html(h):
    """Kleines Editor-HTML (b, i, sub, sup, br wie synthesis.doc_to_html) -> [(Text, {Formate})]."""
    from html.parser import HTMLParser
    runs, stack = [], []

    class _P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "br":
                runs.append(("\n", frozenset()))
            elif tag in ("b", "i", "sub", "sup"):
                stack.append(tag)

        def handle_endtag(self, tag):
            if tag in stack:
                del stack[len(stack) - 1 - stack[::-1].index(tag)]

        def handle_data(self, data):
            runs.append((data.replace(" ", "\n"), frozenset("b" if t == "b" else "i" if t == "i" else t
                                                                   for t in stack)))
    p = _P(convert_charrefs=True)
    p.feed(str(h or ""))
    p.close()
    return runs


def from_html(h):
    """Editor-HTML -> Abbildungstext (Mathtext): Formatiertes als $…$ (Sonderzeichen darin maskiert), nie über ein
    Zeilenende; ungeformter Text wörtlich, auch ein getipptes $ (als \\$, Nutzerwunsch: Format nur über die Knöpfe)."""
    out, math = [], []                                     # math: [(Art '', 'sub', 'sup'), Inhalt]

    def flush():
        if math:
            out.append("$" + "".join(b if k == "" else ("_{%s}" if k == "sub" else "^{%s}") % b for k, b in math) + "$")
            math.clear()
    for text, f in _runs_of_html(h):
        for i, part in enumerate(text.split("\n")):
            if i:
                flush()
                out.append("\n")
            if not part:
                continue
            if not f:
                flush()
                # shortcut: a plain backslash right before "$" or a formatted run escapes that "$"; handle if it comes up
                out.append(part.replace("$", r"\$"))
                continue
            body = "".join(_ESC.get(c, c) for c in part)
            # ohne B/I steil (\\mathrm): Mathtext setzte Buchstaben sonst kursiv, und die Regel „Größe mit Index kursiv“
            # (core.math_symbols) griffe auf ein getipptes „a“ vor tiefem „b“ – kursiv nur, was der Nutzer kursiv setzt
            body = "\\%s{%s}" % (_FONT_OF.get(f & {"b", "i"}, "mathrm"), body)
            kind = "sub" if "sub" in f else "sup" if "sup" in f else ""
            if math and kind and math[-1][0] == kind:      # gleiche Stufe weiter: ein Index (sonst „Double subscript“)
                math[-1] = [kind, math[-1][1] + body]
                continue
            if math and kind and math[-1][0]:              # hoch nach tief (oder umgekehrt): eigener leerer Kern
                math.append(["", "{}"])
            math.append([kind, body])
    flush()
    return "".join(out)


_SYM = None


def _math_runs(src, fmt, out):
    """Mathtext zwischen $…$ -> Läufe; ValueError bei Unbekanntem (\\frac, \\sqrt …)."""
    global _SYM
    if _SYM is None:
        from elucida.core.tables import GREEK
        _SYM = dict(GREEK, backslash="\\", textasciicircum="^", sim="~", lbrace="{", rbrace="}")
    i, n = 0, len(src)

    def group(i, f):
        """Gruppe ab src[i] == '{' (oder ein Zeichen/Befehl) mit Format f -> Index danach."""
        if src[i] == "{":
            depth, j = 1, i + 1
            while j < n and depth:
                if src[j] == "\\":
                    j += 2
                    continue
                depth += {"{": 1, "}": -1}.get(src[j], 0)
                j += 1
            if depth:
                raise ValueError("brace")
            _math_runs(src[i + 1:j - 1], f, out)
            return j
        if src[i] == "\\":
            m = re.match(r"\\([A-Za-z]+)", src[i:])
            j = i + (len(m.group(0)) if m else 2)
            _math_runs(src[i:j], f, out)
            return j
        out.append((src[i], f))
        return i + 1
    while i < n:
        c = src[i]
        if c == " ":
            i += 1
        elif c == "{":
            i = group(i, fmt)
        elif c in "_^":
            if i + 1 >= n:
                raise ValueError("index")
            i = group(i + 1, (fmt - {"sub", "sup"}) | {"sub" if c == "_" else "sup"})
        elif c == "\\":
            m = re.match(r"\\([A-Za-z]+)", src[i:])
            if not m:
                ch = src[i + 1:i + 2]
                if ch not in "{}_$#% ,;!":
                    raise ValueError(src[i:i + 2])
                if ch != "!":
                    out.append((" " if ch in ",; " else ch, fmt))
                i += 2
                continue
            name, i = m.group(1), i + len(m.group(0))
            if name in ("mathit", "mathbf", "mathbfit", "mathrm", "mathsf", "mathtt", "mathcal", "mathregular",
                        "mathnormal", "text", "textrm", "textit", "textbf"):
                while i < n and src[i] == " ":
                    i += 1
                if i >= n:
                    raise ValueError(name)
                f = fmt - {"i", "b"}
                f |= {"i"} if name in ("mathit", "mathbfit", "textit") else set()
                f |= {"b"} if name in ("mathbf", "mathbfit", "textbf") else set()
                i = group(i, frozenset(f))
            elif name in _SYM:
                out.append((_SYM[name], fmt))
            else:
                raise ValueError(name)
        elif c == "}":
            raise ValueError("brace")
        else:
            out.append((c, fmt))
            i += 1
    return out


def text_runs(s):
    """Abbildungstext -> [(Text, Format)] mit Format aus b, i, sub, sup („\n“ = Zeilenende), gleiche Formate
    zusammengefasst; None, wenn er sich so nicht zeigen lässt (\\frac, unpaariges $ …)."""
    runs = []
    try:
        for li, line in enumerate(str(s or "").split("\n")):
            if li:
                runs.append(("\n", frozenset()))
            parts = re.split(r"(?<!\\)\$", line)
            if len(parts) % 2 == 0:
                return None
            for k, p in enumerate(parts):
                if k % 2 == 0:
                    if p:
                        runs.append((p.replace(r"\$", "$"), frozenset()))
                else:
                    _math_runs(p, frozenset(), runs)
    except (ValueError, IndexError):
        return None
    merged = []
    for text, f in runs:                                   # gleiche Formatierung zusammen (ein <sub> für „1/2“)
        if merged and text != "\n" and merged[-1][0] != "\n" and merged[-1][1] == f:
            merged[-1] = (merged[-1][0] + text, f)
        else:
            merged.append((text, f))
    return merged


_SUP_MAP = str.maketrans("0123456789+-−=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾ⁿ")
_SUB_MAP = str.maketrans("0123456789+-−=()", "₀₁₂₃₄₅₆₇₈₉₊₋₋₌₍₎")


def to_plain(s):
    """Abbildungstext als Klartext für Listen und Meldungen (ohne $, ^, _, Befehle): Hoch-/Tiefgestelltes aus Ziffern
    und Zeichen als Unicode (cm⁻¹, E₁/₂), sonst als normale Zeichen; None, wenn er sich nicht lesen lässt."""
    runs = text_runs(s)
    if runs is None:
        return None
    out = []
    for text, f in runs:
        m = _SUP_MAP if "sup" in f else _SUB_MAP if "sub" in f else None
        out.append(text.translate(m) if m and all(ch in "0123456789+-−=()/" or (m is _SUP_MAP and ch == "n")
                                                  for ch in text) else text)
    return "".join(out)


def to_html(s):
    """Abbildungstext -> Editor-HTML (b, i, sub, sup, <br>) oder None, wenn er sich nicht so zeigen lässt (\\frac,
    unpaariges $ …: dann steht der Text als Quelltext im Feld)."""
    import html as _h
    merged = text_runs(s)
    if merged is None:
        return None
    html_ = []
    for text, f in merged:
        if text == "\n":
            html_.append("<br>")
            continue
        t = _h.escape(text, quote=False)
        t = f"<sub>{t}</sub>" if "sub" in f else f"<sup>{t}</sup>" if "sup" in f else t
        t = f"<i>{t}</i>" if "i" in f else t
        html_.append(f"<b>{t}</b>" if "b" in f else t)
    return "".join(html_)
