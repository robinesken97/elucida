"""elucida/formats/ole.py - Bearbeitbare ChemDraw-Objekte in Word: OLE-Container (Compound File Binary, Version 3) schreiben.

Aufbau wie ein in Word eingefügtes ChemDraw-Objekt (ProgID „ChemDraw.Document.6.0“): Streams „\\x01CompObj“
(Klassenname), „\\x01Ole“, „\\x03ObjInfo“, „\\x03EPRINT“ (EMF-Vorschau, optional) und „CONTENTS“ (die Zeichnung, bei
ChemDraw selbst CDX). Sektoren 512 B, Streams < 4096 B im Ministream (64-B-Sektoren), Verzeichnis als ausgeglichener
Rot-Schwarz-Baum (Vergleich: Länge des Namens, dann Großbuchstaben).
"""
from __future__ import annotations

import struct
import uuid

SECT, MINI, CUTOFF = 512, 64, 4096
FREESECT, ENDOFCHAIN, FATSECT, NOSTREAM = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFF

CHEMDRAW_CLSID = "41BA6D21-A02E-11CE-8FD9-0020AFD1F20C"
CHEMDRAW_PROGID = "ChemDraw.Document.6.0"


def _compobj(clsid, user_type, clipboard, progid):
    """Stream \\x01CompObj wie von ChemDraw geschrieben."""
    def lp(s):
        b = s.encode("latin-1") + b"\x00"
        return struct.pack("<I", len(b)) + b
    return (struct.pack("<HHI", 1, 0xFFFE, 0x0A03) + struct.pack("<i", -1) + uuid.UUID(clsid).bytes_le
            + lp(user_type) + lp(clipboard) + lp(progid) + struct.pack("<I", 0x71B239F4) + b"\x00" * 12)


def chemdraw_streams(contents: bytes, preview_emf: bytes | None = None):
    """Streams eines ChemDraw-OLE-Objekts. contents = CDX (oder versuchsweise CDXML)."""
    st = {"\x01CompObj": _compobj(CHEMDRAW_CLSID, "CS ChemDraw Drawing", "ChemDraw Interchange Format",
                                  CHEMDRAW_PROGID),
          "\x01Ole": struct.pack("<II", 0x02000001, 0) + b"\x00" * 12,
          "\x03ObjInfo": b"\x00\x00\x03\x00\x0d\x00",
          "CONTENTS": contents}
    if preview_emf:
        st["\x03EPRINT"] = preview_emf
    return st


def _key(name):
    return (len(name), name.upper())


def write_cfb(streams: dict, clsid: str = CHEMDRAW_CLSID) -> bytes:
    """Compound File mit einer Ebene Streams unter dem Root -> Bytes."""
    names = sorted(streams, key=_key)
    data = {n: bytes(streams[n]) for n in names}
    # Ministream: kleine Streams hintereinander in 64-B-Sektoren
    mini, minifat, mini_start = bytearray(), [], {}
    for n in names:
        d = data[n]
        if len(d) < CUTOFF:
            k = (len(d) + MINI - 1) // MINI or 0
            mini_start[n] = len(minifat) if k else ENDOFCHAIN
            for i in range(k):
                minifat.append(len(minifat) + 1 if i < k - 1 else ENDOFCHAIN)
            mini += d + b"\x00" * (k * MINI - len(d))
    # Reguläre Sektoren: Verzeichnis, MiniFAT, Ministream-Container, große Streams (FAT kommt davor)
    n_dir = (len(names) + 1 + 3) // 4
    blobs = [("dir", None), ("minifat", bytes(b"".join(struct.pack("<I", x) for x in minifat))),
             ("ministream", bytes(mini))] + [(n, data[n]) for n in names if len(data[n]) >= CUTOFF]

    def nsec(b):
        return (len(b) + SECT - 1) // SECT
    sizes = {"dir": n_dir}
    for key, b in blobs[1:]:
        sizes[key] = nsec(b)
    body = sum(sizes.values())
    n_fat = 1
    while n_fat * (SECT // 4) < body + n_fat:
        n_fat += 1
    if n_fat > 109:
        raise ValueError("Objekt zu groß für einen einfachen OLE-Container")
    fat = [FATSECT] * n_fat
    start = {}
    for key, _ in blobs:
        k = sizes[key]
        start[key] = len(fat) if k else ENDOFCHAIN
        fat += [len(fat) + i + 1 if i < k - 1 else ENDOFCHAIN for i in range(k)]
    fat += [FREESECT] * (n_fat * (SECT // 4) - len(fat))

    # Verzeichnis: 0 = Root, dann Streams als ausgeglichener Baum (tiefste Ebene rot, sonst schwarz)
    ids = {n: i + 1 for i, n in enumerate(names)}
    left, right, color = {}, {}, {}

    def build(lo, hi, depth, maxd):
        if lo > hi:
            return NOSTREAM
        mid = (lo + hi) // 2
        n = names[mid]
        left[n] = build(lo, mid - 1, depth + 1, maxd)
        right[n] = build(mid + 1, hi, depth + 1, maxd)
        color[n] = 0 if depth == maxd and (len(names) + 1) & len(names) else 1        # 0 = rot, 1 = schwarz
        return ids[n]
    maxd = max(0, len(names).bit_length() - 1)
    root_child = build(0, len(names) - 1, 0, maxd)

    def entry(name, typ, col, l_, r_, child, clsid_b, start_sec, size):
        nm = name.encode("utf-16-le")
        return (nm + b"\x00" * (64 - len(nm)) + struct.pack("<HBB", len(nm) + 2, typ, col)
                + struct.pack("<III", l_, r_, child) + clsid_b + b"\x00" * 4 + b"\x00" * 16
                + struct.pack("<IIi", start_sec, size, 0))
    dirb = entry("Root Entry", 5, 1, NOSTREAM, NOSTREAM, root_child, uuid.UUID(clsid).bytes_le,
                 start["ministream"] if mini else ENDOFCHAIN, len(mini))
    for n in names:
        small = len(data[n]) < CUTOFF
        dirb += entry(n, 2, color[n], left[n], right[n], NOSTREAM, b"\x00" * 16,
                      mini_start[n] if small else start[n], len(data[n]))
    dirb += b"\x00" * (n_dir * SECT - len(dirb))
    for i in range(len(names) + 1, n_dir * 4):                # leere Einträge: Geschwister = NOSTREAM
        o = i * 128
        dirb = dirb[:o + 68] + struct.pack("<III", NOSTREAM, NOSTREAM, NOSTREAM) + dirb[o + 80:]

    hdr = (bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 16 + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6)
           + b"\x00" * 6 + struct.pack("<I", 0) + struct.pack("<I", n_fat) + struct.pack("<I", start["dir"])
           + struct.pack("<I", 0) + struct.pack("<I", CUTOFF)
           + struct.pack("<I", start["minifat"] if minifat else ENDOFCHAIN) + struct.pack("<I", sizes["minifat"])
           + struct.pack("<I", ENDOFCHAIN) + struct.pack("<I", 0)
           + b"".join(struct.pack("<I", i if i < n_fat else FREESECT) for i in range(109)))
    out = bytearray(hdr)
    out += b"".join(struct.pack("<I", x) for x in fat)
    for key, b in blobs:
        b = dirb if key == "dir" else b
        out += b + b"\x00" * (sizes[key] * SECT - len(b))
    return bytes(out)
