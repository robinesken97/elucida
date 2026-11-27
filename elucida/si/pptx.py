"""
elucida/si/pptx.py - PowerPoint-Datei (PPTX) mit einer Folie je Abbildung, ohne Zusatzpaket (kein python-pptx:
neue Abhängigkeit und PyInstaller-Falle). Eigenes Minimalgerüst (Entscheidung 50): nur die Teile und Elemente, die das
Schema verlangt (Präsentation, ein Master, Layout „Blank“, Design mit eigenen Farben/Arial), aus der früheren
Referenzdatei Element für Element abgeleitet; keine Office-Design-XML, keine presProps/viewProps/tableStyles.
docProps ohne Personen und Datum. Bild wie in Word: SVG (svgBlip), daneben nur ein kleines Ersatz-PNG
(Entscheidung 75), eingepasst im Seitenverhältnis; darunter die Unterschrift als bearbeitbares Textfeld
(fett/kursiv/tief/hoch als eigene Läufe).
"""
from __future__ import annotations

import html as _html
import math
import os
import zipfile
from pathlib import Path

from elucida.si.lines import html_runs
from elucida import replace_file

SLIDE_W, SLIDE_H = 12192000, 6858000      # 16:9 (EMU)
EMU_PT = 12700
MARGIN = 457200                           # 1.27 cm Rand
GAP = 91440                               # Bild – Unterschrift
CAP_PT = 14                               # Unterschrift
FALLBACK_DPI = 72                         # Ersatz-PNG neben dem SVG (Entscheidung 75: nur damit die Datei gültig bleibt)

_NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
       'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
_GRP = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm>'
        '<a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
# Gerüst: Pflichtelemente in Schemareihenfolge; Textfarbe der Unterschrift erbt von defaultTextStyle (tx1 = dk1)
_PRESENTATION = (
    _XML + f'<p:presentation {_NS} autoCompressPictures="0"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
    f'<p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle>'
    '<a:defPPr><a:defRPr lang="en-US"/></a:defPPr><a:lvl1pPr marL="0" algn="l" defTabSz="914400"><a:defRPr sz="1800" '
    'kern="1200"><a:solidFill><a:schemeClr val="tx1"/></a:solidFill><a:latin typeface="+mn-lt"/>'
    '<a:ea typeface="+mn-ea"/><a:cs typeface="+mn-cs"/></a:defRPr></a:lvl1pPr></p:defaultTextStyle></p:presentation>')
_MASTER = (
    _XML + f'<p:sldMaster {_NS}><p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>'
    f'<p:spTree>{_GRP}</p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
    'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" '
    'folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
    '<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>')
_LAYOUT = (_XML + f'<p:sldLayout {_NS} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>{_GRP}</p:spTree>'
           '</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')
_PH = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
_FONT = '<a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/>'
_THEME = (
    _XML + '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Elucida"><a:themeElements>'
    '<a:clrScheme name="Elucida">' + "".join(
        f'<a:{k}><a:srgbClr val="{v}"/></a:{k}>' for k, v in (
            ("dk1", "000000"), ("lt1", "FFFFFF"), ("dk2", "404040"), ("lt2", "F2F2F2"), ("accent1", "1F77B4"),
            ("accent2", "FF7F0E"), ("accent3", "2CA02C"), ("accent4", "D62728"), ("accent5", "9467BD"),
            ("accent6", "8C564B"), ("hlink", "1F77B4"), ("folHlink", "9467BD"))) +
    f'</a:clrScheme><a:fontScheme name="Elucida"><a:majorFont>{_FONT}</a:majorFont><a:minorFont>{_FONT}</a:minorFont>'
    f'</a:fontScheme><a:fmtScheme name="Elucida"><a:fillStyleLst>{_PH * 3}</a:fillStyleLst><a:lnStyleLst>' +
    f'<a:ln w="12700">{_PH}</a:ln>' * 3 + '</a:lnStyleLst><a:effectStyleLst>' +
    '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 + f'</a:effectStyleLst><a:bgFillStyleLst>{_PH * 3}'
    '</a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>')


def caption_lines(cap_html, width_emu):
    """Geschätzte Zeilen der Unterschrift (Arial: mittlere Zeichenbreite ~0.5 em); PowerPoint passt das Feld an."""
    text = "".join(t for t, st in html_runs(cap_html) if "br" not in st)
    per_line = max(20, int(width_emu / EMU_PT / (0.5 * CAP_PT)))
    return max(1, math.ceil(len(text) / per_line))


def place(w, h, cap_html):
    """Bild (w × h, beliebige Einheit) samt Unterschrift auf der Folie: -> (x, y, cx, cy) des Bildes und
    (x, y, cx, cy) des Textfelds (oder None) in EMU; Seitenverhältnis bleibt, Block senkrecht mittig."""
    box_w = SLIDE_W - 2 * MARGIN
    cap_h = int(caption_lines(cap_html, box_w) * CAP_PT * 1.2 * EMU_PT + 2 * 45720) if cap_html else 0
    box_h = SLIDE_H - 2 * MARGIN - (cap_h + GAP if cap_html else 0)
    s = min(box_w / w, box_h / h)
    cx, cy = int(w * s), int(h * s)
    top = (SLIDE_H - (cy + (GAP + cap_h if cap_html else 0))) // 2
    pic = ((SLIDE_W - cx) // 2, top, cx, cy)
    cap = (MARGIN, top + cy + GAP, box_w, cap_h) if cap_html else None
    return pic, cap


def fallback_png(png_b, cx_emu):
    """Ersatz-PNG für Programme ohne SVG: höchstens FALLBACK_DPI bei der Breite auf der Folie, nie vergrößert;
    nur im Speicher (die Datei auf der Platte kann die des Nutzers sein)."""
    import io
    from PIL import Image
    with Image.open(io.BytesIO(png_b)) as im:
        px = max(1, int(cx_emu / 914400 * FALLBACK_DPI))
        if im.width <= px:
            return png_b
        im = im.resize((px, max(1, round(im.height * px / im.width))), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True, dpi=(FALLBACK_DPI, FALLBACK_DPI))
        return buf.getvalue()


def _runs_xml(cap_html):
    out = []
    for text, st in html_runs(cap_html):
        if "br" in st:
            out.append("<a:br><a:rPr lang=\"en-US\" sz=\"%d\"/></a:br>" % (CAP_PT * 100))
            continue
        attrs = f' sz="{CAP_PT * 100}"' + (' b="1"' if "b" in st else "") + (' i="1"' if "i" in st else "")
        attrs += ' baseline="-25000"' if "sub" in st else ' baseline="30000"' if "sup" in st else ""
        out.append(f'<a:r><a:rPr lang="en-US"{attrs} dirty="0"><a:latin typeface="Arial"/><a:cs typeface="Arial"/>'
                   f'</a:rPr><a:t>{_html.escape(text, quote=False)}</a:t></a:r>')
    return "".join(out)


def _xfrm(x, y, cx, cy):
    return f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'


def slide_xml(n, pic, cap, cap_html, svg):
    blip = '<a:blip r:embed="rId2">' + (
        '<a:extLst><a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}"><asvg:svgBlip '
        'xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" r:embed="rId3"/></a:ext></a:extLst>'
        if svg else "") + "</a:blip>"
    tree = (f'<p:pic><p:nvPicPr><p:cNvPr id="2" name="Figure {n}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/>'
            f'</p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill>{blip}<a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr>{_xfrm(*pic)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')
    if cap:
        tree += (f'<p:sp><p:nvSpPr><p:cNvPr id="3" name="Caption {n}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
                 f'<p:spPr>{_xfrm(*cap)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
                 '<p:txBody><a:bodyPr wrap="square" rtlCol="0"><a:spAutoFit/></a:bodyPr><a:lstStyle/>'
                 f'<a:p><a:pPr algn="just"/>{_runs_xml(cap_html)}</a:p></p:txBody></p:sp>')
    return (_XML + f'<p:sld {_NS}><p:cSld><p:spTree>{_GRP}{tree}</p:spTree></p:cSld><p:clrMapOvr>'
            '<a:masterClrMapping/></p:clrMapOvr></p:sld>')


def write_pptx(path, figures):
    """figures: [(PNG, Breite, Höhe, SVG oder None, Unterschrift-HTML ohne „Figure Sn:“ oder "")] -> Pfad.
    Eine Folie je Abbildung; atomar geschrieben (offene Datei: PermissionError, die alte bleibt)."""
    if not figures:
        raise ValueError("no figures")
    n = len(figures)
    pres = _PRESENTATION.replace(
        "</p:sldMasterIdLst>", "</p:sldMasterIdLst><p:sldIdLst>" +
        "".join(f'<p:sldId id="{256 + i}" r:id="rId{100 + i}"/>' for i in range(1, n + 1)) + "</p:sldIdLst>", 1)
    pres_rels = (_XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 f'<Relationship Id="rId1" Type="{_REL}/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
                 f'<Relationship Id="rId2" Type="{_REL}/theme" Target="theme/theme1.xml"/>' +
                 "".join(f'<Relationship Id="rId{100 + i}" Type="{_REL}/slide" Target="slides/slide{i}.xml"/>'
                         for i in range(1, n + 1)) + "</Relationships>")
    ct = "application/vnd.openxmlformats-officedocument.presentationml."
    types = (_XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Default Extension="png" ContentType="image/png"/><Default Extension="svg" ContentType="image/svg+xml"/>'
             f'<Override PartName="/ppt/presentation.xml" ContentType="{ct}presentation.main+xml"/>'
             f'<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="{ct}slideMaster+xml"/>'
             f'<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="{ct}slideLayout+xml"/>'
             '<Override PartName="/ppt/theme/theme1.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>' +
             "".join(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="{ct}slide+xml"/>'
                     for i in range(1, n + 1)) +
             '<Override PartName="/docProps/core.xml" '
             'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
             '<Override PartName="/docProps/app.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')
    rels = (_XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{_REL}/officeDocument" Target="ppt/presentation.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/'
            'core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="{_REL}/extended-properties" Target="docProps/app.xml"/></Relationships>')
    # eigene docProps: keine Personen, kein Datum (die Vorlage trug den Kontonamen)
    core_ = (_XML + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/'
             'core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
             'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title></dc:title><cp:revision>1</cp:revision>'
             '</cp:coreProperties>')
    app = (_XML + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           f'<TotalTime>0</TotalTime><PresentationFormat>Widescreen</PresentationFormat><Slides>{n}</Slides>'
           '<Notes>0</Notes><HiddenSlides>0</HiddenSlides></Properties>')
    master_rels = (_XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'<Relationship Id="rId1" Type="{_REL}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
                   f'<Relationship Id="rId2" Type="{_REL}/theme" Target="../theme/theme1.xml"/></Relationships>')
    layout_rels = (_XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'<Relationship Id="rId1" Type="{_REL}/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
                   '</Relationships>')
    media = []                                        # fehlt ein Bild: Fehler, bevor die alte Datei weg ist
    for png, w, h, svg, cap_html in figures:
        svg_b = Path(svg).read_bytes() if svg and Path(svg).is_file() else None
        png_b = Path(png).read_bytes()
        if svg_b is not None:                         # angezeigt wird das SVG: PNG nur als kleiner Ersatz (Entscheidung 75)
            png_b = fallback_png(png_b, place(w, h, cap_html)[0][2])
        media.append((png_b, svg_b))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("docProps/core.xml", core_)
        z.writestr("docProps/app.xml", app)
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        z.writestr("ppt/slideMasters/slideMaster1.xml", _MASTER)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", _LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        z.writestr("ppt/theme/theme1.xml", _THEME)
        for i, ((png, w, h, svg, cap_html), (png_b, svg_b)) in enumerate(zip(figures, media), 1):
            pic, cap = place(w, h, cap_html)
            z.writestr(f"ppt/slides/slide{i}.xml", slide_xml(i, pic, cap, cap_html, svg_b is not None))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", _XML +
                       '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       f'<Relationship Id="rId1" Type="{_REL}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
                       f'<Relationship Id="rId2" Type="{_REL}/image" Target="../media/image{i}.png"/>' +
                       (f'<Relationship Id="rId3" Type="{_REL}/image" Target="../media/image{i}.svg"/>' if svg_b else "")
                       + "</Relationships>")
            z.writestr(f"ppt/media/image{i}.png", png_b)
            if svg_b is not None:
                z.writestr(f"ppt/media/image{i}.svg", svg_b)
    replace_file(tmp, path)
    return path


def figures_from_blocks(blocks):
    """SI-Blöcke ([("image", PNG, b, h[, SVG]), ("figcap", HTML)] …) -> Abbildungen für write_pptx; andere Blöcke
    (Aufbau-Text, Seitenumbrüche) fallen weg."""
    out = []
    for k, b in enumerate(blocks):
        if b[0] == "image":
            cap = blocks[k + 1][1] if k + 1 < len(blocks) and blocks[k + 1][0] == "figcap" else ""
            out.append((b[1], b[2], b[3], b[4] if len(b) > 4 else None, cap))
    return out
