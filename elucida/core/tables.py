"""Tabellen als Dateien, eine Form für alle Tabs (Entscheidung 170): CSV mit Komma, Dezimalpunkt, UTF-8 mit BOM,
englischer Kopf „Name [Einheit]“ ohne Mathtext, volle Rohwerte. Kopf-Konvention (im Handbuch genannt): Buchstaben wie
λ, ε, Δ, Å, °, µ bleiben Unicode (die Datei ist UTF-8 mit BOM), Exponenten als „^-1“ (cm^-1, M^-1 cm^-1), Indizes als
„_“ (E_pa, ΔB_pp), Minus immer ASCII. Ohne Qt: auch `core.write_results` (ε) schreibt hierüber."""
import csv
import math
import re

GREEK = {"varepsilon": "ε", "epsilon": "ε", "lambda": "λ", "Delta": "Δ", "delta": "δ", "mu": "µ", "nu": "ν",
         "tau": "τ", "theta": "θ", "phi": "φ", "Phi": "Φ", "chi": "χ", "rho": "ρ", "sigma": "σ", "pi": "π",
         "alpha": "α", "beta": "β", "gamma": "γ", "omega": "ω", "Omega": "Ω", "eta": "η", "kappa": "κ",
         "circ": "°", "AA": "Å", "AA{}": "Å", "cdot": "·", "times": "×", "pm": "±", "minus": "-"}
_SUP = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+"))
_SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉₋₊ₐₑₒₓₕₖₗₘₙₚₛₜᵢⱼᵣᵤᵥ", "0123456789-+aeoxhklmnpstijruv"))
SPACES = {"\u00a0": " ", "\u2009": " ", "\u202f": " ", "\u200b": "", "\u2212": "-"}


def _mathtext(m):
    s = m.group(1)
    s = re.sub(r"\\(?:mathrm|mathit|mathbf|mathsf|text|it|rm|bf)\b", "", s)
    s = re.sub(r"\\tilde\{?\\nu\}?", "ṽ", s)
    s = re.sub(r"\\([A-Za-z]+)", lambda g: GREEK.get(g.group(1), g.group(1)), s)
    s = re.sub(r"\^\{([^}]*)\}", r"^\1", s)
    s = re.sub(r"_\{([^}]*)\}", r"_\1", s)
    return s.replace("{", "").replace("}", "").replace("\\,", " ").replace("\\ ", " ").replace("\\", "")


def plain(text):
    """Text für eine CSV-Zelle bzw. einen Kopf: Mathtext aufgelöst ($\\varepsilon$ -> ε, cm$^{-1}$ -> cm^-1), Hoch-
    und Tiefstellung als ^/_, Minus und Leerzeichen ASCII."""
    s = str(text)
    for a, b in SPACES.items():
        s = s.replace(a, b)
    s = re.sub(r"\$([^$]*)\$", _mathtext, s).replace("$", "")
    s = re.sub("[" + "".join(_SUP) + "]+", lambda m: "^" + "".join(_SUP[c] for c in m.group(0)), s)
    s = re.sub("[" + "".join(_SUB) + "]+", lambda m: "_" + "".join(_SUB[c] for c in m.group(0)), s)
    return s


def header(text):
    """Kopf „Name [Einheit]“: auch „Name / Einheit“ (SI-Schreibweise) wird so umgestellt."""
    s = plain(text).strip()
    m = re.fullmatch(r"(.+) / ([^/\[\]:]{1,20})", s)            # Einheit kurz, ohne Klammern (nicht „THF / MeCN: …“)
    return f"{m.group(1)} [{m.group(2)}]" if m else s


def cell(v):
    """Rohwert: Zahl mit 12 gültigen Stellen (nicht endlich = leer), Text ohne Satzzeichen der Anzeige."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int) or type(v).__name__.startswith(("int", "uint")):
        return str(int(v))
    if isinstance(v, float) or type(v).__name__.startswith("float"):
        v = float(v)
        return format(v, ".12g") if math.isfinite(v) else ""
    return plain(v)


def write_csv(path, head, rows):
    """Die eine CSV-Form aller Tabs (Komma, Punkt, UTF-8 mit BOM, Kopf `header`, Werte `cell`). -> path"""
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow([header(h) for h in head])
        for r in rows:
            w.writerow([cell(c) for c in r])
    return path


_NUM = re.compile(r"[-+]?(\d+(\.(\d*))?|\.(\d+))([eE][-+]?\d+)?")


def screen_number(text):
    """Zahl, wie sie auf dem Bildschirm steht -> (Wert, Excel-Zahlenformat mit denselben Stellen) oder None (Text)."""
    s = plain(text).strip()
    sci = re.fullmatch(r"(\S+) × 10\^([-+]?\d+)", s)        # „2.49 × 10⁸“ (Fluoreszenz k_r/k_nr)
    if sci and _NUM.fullmatch(sci.group(1)):
        m = _NUM.fullmatch(sci.group(1))
        dec = len(m.group(3) or m.group(4) or "")
        return float(f"{sci.group(1)}e{sci.group(2)}"), "0." + "0" * dec + "E+00" if dec else "0E+00"
    if not _NUM.fullmatch(s):
        return None
    m = _NUM.fullmatch(s)
    dec = len(m.group(3) or m.group(4) or "")
    if m.group(5):
        return float(s), "0." + "0" * dec + "E+00" if dec else "0E+00"
    return float(s), "0." + "0" * dec if dec else "0"


# Größen im Methodentext (Nutzerwunsch 2026-11-22, kursiv in Word und Vorschau): einzelne lateinische Buchstaben
# markiert die Quelle mit Backticks (`k`, `A`, `t`), weil der Kontext sie nicht von Einheiten/Wörtern trennt („17.8 d“
# Tage, „A/d“ Weglänge, „a g standard“); was an der Form erkennbar ist (τ, Φ, A_0, E1/2, Epa, ip, ΔBpp, v1/2), setzen
# die Regeln ohne Markierung (si.lines.methods_html). Klartext (Kopieren, _methods.txt, Selbsttest) ohne Backticks:
# `unmark`/`marks`.
MARK = re.compile(r"`([A-Za-z]{1,2})`")


def unmark(text):
    """Methodentext mit Markierung -> Klartext (Backticks um Größen weg)."""
    return MARK.sub(r"\1", text or "")


def marks(f):
    """methods_text(…, marked=False): Quelle schreibt `k`; ohne marked=True kommt Klartext (wie bisher) zurück."""
    import functools

    @functools.wraps(f)
    def g(*a, marked=False, **k):
        t = f(*a, **k)
        return t if marked else unmark(t)
    return g
