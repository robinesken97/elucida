"""Parse explicit amount suffixes without removing chemical brackets or changing displayed text."""
from __future__ import annotations
import re

_AMOUNT = re.compile(r'\s*\(\s*(\d+(?:[.,]\d+)?)\s*(eq\.?|equiv\.?|Äq\.?|mol\s*%)\s*\)\s*$', re.I)


def parse_labels(text):
    parts, start, depth = [], 0, 0
    for i, c in enumerate(text):
        if c in '([': depth += 1
        elif c in ')]': depth = max(0, depth-1)
        decimal = c == ',' and i > 0 and i+1 < len(text) and text[i-1].isdigit() and text[i+1].isdigit()
        if depth == 0 and (c in ';\n' or c == ',' and not decimal):
            parts.append(text[start:i]); start = i+1
    parts.append(text[start:])
    out = []
    for part in parts:
        part = part.strip()
        if not part: continue
        match = _AMOUNT.search(part)
        substance = part[:match.start()].strip() if match else part
        equiv = float(match[1].replace(',', '.')) * (0.01 if 'mol' in match[2].lower() else 1) if match else None
        out.append(dict(text=part, substance=substance, equiv=equiv))
    return out
