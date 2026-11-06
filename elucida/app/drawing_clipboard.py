"""Chemical clipboard formats used by ChemDraw/Octet, with Qt and Cocoa adapters."""
from __future__ import annotations
import base64
import sys
from PySide6.QtCore import QMimeData
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
    with fitz.open(stream=svg.encode(), filetype='svg') as doc:
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
        mime = QMimeData()
        for name, raw in data.items():
            mime.setData(name, raw)
        QApplication.clipboard().setMimeData(mime)
    return True


def paste_drawing():
    types = _types()
    if sys.platform == 'darwin':
        from AppKit import NSPasteboard
        board = NSPasteboard.generalPasteboard()
        def read(name):
            value = board.dataForType_(name)
            return bytes(value) if value is not None and len(value) <= MAX else None
    else:
        mime = QApplication.clipboard().mimeData()
        def read(name):
            return bytes(mime.data(name)) if mime and mime.hasFormat(name) and mime.data(name).size() <= MAX else None
    out = {k: None for k in ['octet', 'cdxml', 'cdx', 'molfile', 'smiles', 'text', 'picture']}
    for key in ['octet', 'cdxml', 'cdx', 'molfile', 'smiles', 'text']:
        raw = next((b for name in types[key] if (b := read(name))), None)
        if not raw:
            continue
        if key == 'cdx':
            if raw.startswith(b'VjCD0100'):
                out[key] = base64.b64encode(raw).decode()
            continue
        if key == 'molfile' and b'\n' not in raw:
            lines, i = [], 0
            while i < len(raw):
                n = raw[i]; i += 1
                if i+n > len(raw): break
                lines.append(raw[i:i+n]); i += n
            if i == len(raw): raw = b'\n'.join(lines)
        out[key] = raw.rstrip(b'\x00').decode('utf-8', errors='replace')
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
