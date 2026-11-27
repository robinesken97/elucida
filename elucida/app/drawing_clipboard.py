"""Chemical clipboard formats used by ChemDraw/Octet, with Qt and Cocoa adapters."""
from __future__ import annotations
import base64
import sys
from elucida.app import style as STYLE
from PySide6.QtWidgets import QApplication

MAX = 32 * 1024 * 1024
MAC_CDX = ['com.perkinelmer.chemdraw.cdx-clipboard', 'com.revvity.chemdraw.cdx-clipboard', 'com.cambridgesoft.cdx']
MAC_XML = ['com.perkinelmer.cdxml', 'com.revvity.cdxml', 'com.cambridgesoft.cdxml']
OWN = 'io.github.samchemman.octet.json'


def _win(name):
    return f'application/x-qt-windows-mime;value="{name}"'


def _types():
    if sys.platform == 'darwin':
        return {'cdx': MAC_CDX, 'cdxml': MAC_XML, 'octet': [OWN], 'molfile': ['com.mdli.molfile'],
                'smiles': ['org.opensmiles.smiles'], 'text': ['public.utf8-plain-text'], 'pdf': ['com.adobe.pdf']}
    return {'cdx': [_win('ChemDraw Interchange Format'), 'chemical/x-cdx'],
            'cdxml': [_win('CDXML'), 'chemical/x-cdxml'], 'octet': ['application/x-octet+json'],
            'molfile': [_win('MDLCT'), 'chemical/x-mdl-molfile'], 'smiles': [_win('SMILES'), 'chemical/x-daylight-smiles'],
            'text': ['text/plain'], 'pdf': ['application/pdf']}


def _pdf(svg, cdxml):
    import pymupdf as fitz
    from elucida.core.images import flatten_nested_svg
    with fitz.open(stream=flatten_nested_svg(svg).encode(), filetype='svg') as doc:
        data = doc.convert_to_pdf()
    with fitz.open(stream=data, filetype='pdf') as doc:
        if cdxml:
            x = doc.get_new_xref()
            doc.update_object(x, '<< /Type /Metadata /Subtype /XML >>')
            doc.update_stream(x, cdxml.encode())
            doc.xref_set_key(doc.pdf_catalog(), 'Metadata', f'{x} 0 R')
        return doc.tobytes()


def copy_drawing(payload):
    types = _types(); data = {}
    if payload.get('text') is not None:
        data[types['text'][0]] = payload['text'].encode()
    else:
        if payload.get('svg'):
            data[types['pdf'][0]] = _pdf(payload['svg'], payload.get('cdxml'))
            if sys.platform != 'darwin':
                data['image/svg+xml'] = payload['svg'].encode()
        for key, value in [('cdx', payload.get('cdx')), ('cdxml', payload.get('cdxml')), ('octet', payload.get('octetJson')),
                           ('smiles', payload.get('smiles')), ('molfile', payload.get('molfile'))]:
            if not value:
                continue
            raw = base64.b64decode(value, validate=True) if key == 'cdx' else value.encode()
            if len(raw) > MAX:
                raise ValueError('Clipboard item too large')
            if key == 'molfile' and sys.platform in ('darwin', 'win32'):
                lines = raw.splitlines()
                if any(len(line) > 255 for line in lines):
                    continue
                raw = b''.join(bytes([len(line)]) + line for line in lines)
            for name in types[key]:
                data[name] = raw
    if sys.platform == 'darwin':
        from AppKit import NSPasteboard
        from Foundation import NSData
        board = NSPasteboard.generalPasteboard()
        board.clearContents()
        board.declareTypes_owner_(list(data), None)
        for name, raw in data.items():
            if not board.setData_forType_(NSData.dataWithBytes_length_(raw, len(raw)), name):
                raise RuntimeError('macOS rejected a clipboard format')
    else:
        mime = STYLE.clip_mime()
        for name, raw in data.items():
            mime.setData(name, raw)
        QApplication.clipboard().setMimeData(mime)
    return True


def copy_picture(svg, png):
    """Abbildung (Entscheidung 128): SVG (Vektor) + PNG-Ersatz; macOS zusätzlich PDF aus dem SVG wie copy_drawing
    (Office für Mac fügt PDF als Vektor ein). svg/png: Bytes."""
    if sys.platform == 'darwin':
        from AppKit import NSPasteboard
        from Foundation import NSData
        data = {'com.adobe.pdf': _pdf(svg.decode('utf-8'), None), 'public.svg-image': svg, 'public.png': png}
        board = NSPasteboard.generalPasteboard()
        board.clearContents()
        board.declareTypes_owner_(list(data), None)
        for name, raw in data.items():
            if not board.setData_forType_(NSData.dataWithBytes_length_(raw, len(raw)), name):
                raise RuntimeError('macOS rejected a clipboard format')
    else:                                   # shortcut: Windows/Linux-Typen nicht in Office geprüft; prüfen, sobald ein Windows-Rechner bereitsteht
        from PySide6.QtGui import QImage
        mime = STYLE.clip_mime()
        mime.setData('image/svg+xml', svg)
        mime.setData('image/png', png)
        mime.setImageData(QImage.fromData(png, 'PNG'))
        QApplication.clipboard().setMimeData(mime)
    return True


def _molfile_text(raw):
    """Molfile von der Zwischenablage wie Octets Tauri-Host (clipboard.rs molfile_text): erst NULs am Ende weg, dann
    ChemDraws MDLCT (je Zeile ein Längenbyte, keine Zeilenenden) oder gewöhnlicher Text. Früher entschied ein
    Zeilenumbruch im Ganzen, und das Längenbyte 10 ist selbst ein Zeilenumbruch."""
    raw = raw.rstrip(b'\x00')
    if not raw:
        return None
    lines, i = [], 0
    while i < len(raw):
        n = raw[i]
        line = raw[i + 1:i + 1 + n]
        if len(line) < n or b'\r' in line or b'\n' in line:
            lines = []
            break
        lines.append(line)
        i += 1 + n
    text = (b'\n'.join(lines).decode('utf-8', errors='replace') if lines else
            raw.decode('utf-8', errors='replace').replace('\r\n', '\n').replace('\r', '\n'))
    return text if text.endswith('\n') else text + '\n'


def _smiles_text(raw):
    """SMILES wie clipboard.rs smiles_text: ASCII, ohne NULs und Leerraum am Rand, sonst None."""
    try:
        s = raw.decode('utf-8').strip('\x00 \t\r\n')
    except UnicodeDecodeError:
        return None
    return s if s and s.isascii() and '\x00' not in s else None


def paste_drawing():
    """Was Octet aus der Zwischenablage einfügen kann (wie Octets Tauri-Host). `filled`: die Zwischenablage hält etwas,
    lesbar oder nicht – Octet sagt dann „cannot read“ statt still nichts zu tun (Windows-Bericht 1.4.0, Punkt 11);
    `present`: die Namen aller Formate, fürs Protokoll, wenn nichts davon lesbar war."""
    types = _types()
    if sys.platform == 'darwin':
        from AppKit import NSPasteboard
        board = NSPasteboard.generalPasteboard()
        present = [str(x) for x in (board.types() or [])]
        def read(name):
            value = board.dataForType_(name)
            return bytes(value) if value is not None and len(value) <= MAX else None
    else:
        mime = QApplication.clipboard().mimeData()
        present = list(mime.formats()) if mime else []
        by_lower = {f.lower(): f for f in present}         # Qt nennt Windows-Formate je nach Weg anders geschrieben
        def read(name):
            f = by_lower.get(name.lower(), name)
            if not mime or not mime.hasFormat(f):
                return None
            data = mime.data(f)
            return bytes(data) if 0 < data.size() <= MAX else None
    out = {k: None for k in ['octet', 'cdxml', 'cdx', 'molfile', 'smiles', 'text', 'picture']}
    for key in ['octet', 'cdxml', 'cdx', 'molfile', 'smiles', 'text']:
        raw = next((b for name in types[key] if (b := read(name))), None)
        if not raw:
            continue
        if key == 'cdx':
            if raw.startswith(b'VjCD0100'):
                out[key] = base64.b64encode(raw).decode()
            continue
        out[key] = _molfile_text(raw) if key == 'molfile' else _smiles_text(raw) if key == 'smiles' else \
            raw.rstrip(b'\x00').decode('utf-8', errors='replace')
    out['filled'] = bool(present)
    out['present'] = present[:40]
    if not out['cdxml'] and not out['cdx']:
        raw = next((b for name in types['pdf'] if (b := read(name))), None)
        if raw:
            try:
                import pymupdf as fitz
                with fitz.open(stream=raw, filetype='pdf') as doc:
                    kind, ref = doc.xref_get_key(doc.pdf_catalog(), 'Metadata')
                    if kind == 'xref':
                        xml = doc.xref_stream(int(ref.split()[0]))
                        if xml and len(xml) <= MAX and b'<CDXML' in xml:
                            out['cdxml'] = xml.decode('utf-8')
            except Exception:
                pass
    return out
