"""Local Octet host. Files and clipboard are owned by Qt, never by arbitrary JS paths."""
from __future__ import annotations

import base64
import functools
import hashlib
import http.server
import json
import math
import os
import re
from pathlib import Path
import shutil
import sys
import threading
import time
import uuid
import weakref
import xml.etree.ElementTree as ET

from PySide6.QtCore import QObject, Signal, Slot, QUrl, QTimer, QEventLoop, QEvent, Qt, QFile, QIODevice
from shiboken6 import delete, isValid
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QDialog, QApplication, QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox, QMenu, QFileDialog
from elucida import ROOT
from elucida.app.i18n import T, get_lang

MAX_BYTES = 32 * 1024 * 1024
BACKUP_DIR, BACKUP_KEEP, BACKUP_GAP_S = '.editor-backups', 20, 300
DRAWING_VERSION = 3  # Regenerate old SI previews: filtered drawing and positioned text runs.
_SERVER = None
# Octet's own layers, not part of the drawing (frontend/octet/src/export.ts, UI).
_UI = ','.join('.' + c for c in (
    'pages grid selection-marks frame-marks nmr-marks nmr-shift problem-mark mark arrow-mark suggested ghost pen-points '
    'mapping handle turn-handle turn-centre turn-angle box trail erase-marks brush count guide snap-point spot-picked '
    'lane-picked group-frame grid-pick interpretation').split()) + ',defs,mask,clipPath,pattern,marker,symbol,filter'
# (w, h, top, move): distance of the drawing from its place in the canvas, [] without a drawing, false while the page
# does not have the size of the view yet. Place: horizontally centred; vertically centred in the upper third (top) or
# in the canvas, never above the edge. Octet has no call for the view; a plain wheel event pans it 1:1 (onWheel).
_PLACE = """((w, h, top, move) => {
  const world = document.querySelector('#world'), svg = world && world.ownerSVGElement;
  if (!svg || Math.abs(innerWidth - w) > 2 || Math.abs(innerHeight - h) > 2) return false;
  const c = svg.getBoundingClientRect();
  let b;
  for (const el of world.querySelectorAll('path,polygon,polyline,line,rect,circle,ellipse,text,image,use')) {
    if (el.closest(%s)) continue;
    const r = el.getBoundingClientRect();
    if (r.width || r.height) b = b ? [Math.min(b[0], r.left), Math.min(b[1], r.top), Math.max(b[2], r.right), Math.max(b[3], r.bottom)]
                                   : [r.left, r.top, r.right, r.bottom];
  }
  if (!b) return [];
  const room = top ? c.height / 3 : c.height;
  const d = [(c.left + c.right - b[0] - b[2]) / 2, c.top + Math.max((room - b[3] + b[1]) / 2, c.height / 24) - b[1]];
  if (move) svg.dispatchEvent(new WheelEvent('wheel', {deltaX: -d[0], deltaY: -d[1], bubbles: true, cancelable: true}));
  return d;
})""" % json.dumps(_UI)


def fingerprint(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def asset_references(value):
    """Accept only bounded references, never file paths from the drawing host."""
    if not isinstance(value, list) or len(value) > 10000:
        raise ValueError('Invalid figure metadata')
    ids = set()
    for ref in value:
        if (not isinstance(ref, dict) or type(ref.get('shapeId')) is not int
                or not 0 <= ref['shapeId'] < 2**53 or ref['shapeId'] in ids
                or not isinstance(ref.get('key'), str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', ref['key'])
                or ref.get('kind') not in ('profile', 'orbital')):
            raise ValueError('Invalid figure reference')
        ids.add(ref['shapeId'])
    return [dict(shapeId=r['shapeId'], key=r['key'], kind=r['kind']) for r in value]


def save_bundle(path, bundle, expected):
    """Validate first; retain a complete previous generation, then publish CDXML last.

    Each file is replaced atomically. The backup allows recovery if the process dies between replaces.
    External changes are rejected rather than overwritten. SVG/CDX are newer than CDXML for Elucida's cache.
    """
    path = Path(path)
    if path.suffix.lower() != '.cdxml':
        raise ValueError(T('draw_invalid'))
    if fingerprint(path) != expected:
        raise ValueError(T('draw_conflict'))
    xml, svg = bundle['cdxml'], bundle['svg']
    if not isinstance(xml, str) or not isinstance(svg, str) or max(len(xml), len(svg)) > MAX_BYTES:
        raise ValueError(T('draw_too_large'))
    if '<!ENTITY' in xml.upper() or '<!ENTITY' in svg.upper():
        raise ValueError(T('draw_invalid'))
    if ET.fromstring(xml).tag != 'CDXML' or ET.fromstring(svg).tag.split('}')[-1] != 'svg':
        raise ValueError(T('draw_invalid'))
    cdx = base64.b64decode(bundle['cdx'], validate=True)
    if not cdx.startswith(b'VjCD0100') or len(cdx) > MAX_BYTES:
        raise ValueError(T('draw_invalid'))
    reagents = bundle.get('reagents', [])
    if not isinstance(reagents, list) or len(reagents) > 10000:
        raise ValueError('Invalid reagent metadata')
    assets = asset_references(bundle.get('assets', []))
    payload = {'.cdxml': xml.encode(), '.svg': svg.encode(), '.cdx': cdx,
               '.elucida-drawing.json': json.dumps({'version': DRAWING_VERSION, 'reagents': reagents, 'si': bundle.get('si'), 'tables': bundle.get('tables', []), 'assets': assets, 'source_sha': hashlib.sha256(xml.encode()).hexdigest()}, ensure_ascii=False).encode()}
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.parent / BACKUP_DIR / (path.stem + '-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    backup.mkdir(parents=True)
    for ext in (*payload, '.pdf', '.png', '.emf'):
        p = path.with_suffix(ext)
        if p.exists():
            shutil.copy2(p, backup / p.name)
    temp = {}
    published = []
    try:
        for ext, content in payload.items():
            target = path.with_suffix(ext)
            p = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
            with p.open('wb') as f:
                f.write(content); f.flush(); os.fsync(f.fileno())
            temp[ext] = p
        if fingerprint(path) != expected:
            raise ValueError(T('draw_conflict'))
        for ext in ('.svg', '.cdx', '.elucida-drawing.json', '.cdxml'):
            os.replace(temp[ext], path.with_suffix(ext))
            published.append(ext)
        stamp = path.stat().st_mtime_ns
        for ext in ('.svg', '.cdx'):
            os.utime(path.with_suffix(ext), ns=(stamp, stamp))
        # Older renderings must never override the newly exported SVG.
        for ext in ('.pdf', '.png', '.emf'):
            p = path.with_suffix(ext)
            if p.exists():
                os.utime(p, ns=(max(0, stamp-2_000_000_000), max(0, stamp-2_000_000_000)))
    except Exception:
        # Restore any files already published if a later replace fails (e.g. a locked CDXML).
        for ext in reversed(published):
            target = path.with_suffix(ext)
            previous = backup / target.name
            if previous.exists():
                recovery = target.with_name(target.name + '.recover.tmp')
                shutil.copy2(previous, recovery)
                os.replace(recovery, target)
            else:
                target.unlink(missing_ok=True)
        raise
    finally:
        for p in temp.values():
            p.unlink(missing_ok=True)
    _thin_backups(backup)
    return fingerprint(path)


def _thin_backups(newest):
    """Every save needs a rollback copy, the history does not: 1 s autosave would fill the project folder."""
    stem = newest.name.rsplit('-', 3)[0]
    same = sorted(p for p in newest.parent.iterdir() if p.is_dir() and p != newest
                  and re.fullmatch(re.escape(stem) + r'-\d{8}-\d{6}-[0-9a-f]{6}', p.name))
    if not any(newest.iterdir()) or same and newest.stat().st_mtime - same[-1].stat().st_mtime < BACKUP_GAP_S:
        shutil.rmtree(newest, ignore_errors=True)
    for p in same[:-BACKUP_KEEP]:
        shutil.rmtree(p, ignore_errors=True)


class _Assets(http.server.SimpleHTTPRequestHandler):
    # Windows reads MIME types from the registry; text/plain there blanks the editor (module scripts).
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm'}

    def log_message(self, *_):
        pass

    def copyfile(self, source, outputfile):
        try:
            outputfile.write(source.read())   # one send: small chunks wait for the GIL while the GUI thread is busy
        except ConnectionError:
            pass  # WebEngine cancels pending asset reads when the editor closes.

    def list_directory(self, path):
        self.send_error(403)
        return None


class _AssetServer(http.server.ThreadingHTTPServer):
    # Default backlog is 5: two editors starting together dropped requests, and a lost bridge.js left an editor dead.
    request_queue_size = 256
    daemon_threads = True

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], ConnectionError):   # Editor beim Laden geschlossen
            super().handle_error(request, client_address)


def asset_url():
    global _SERVER
    folder = ROOT / 'assets' / 'octet'
    if not (folder / 'embedded.html').exists():
        raise RuntimeError(T('draw_build_missing'))
    if _SERVER is None:
        _SERVER = _AssetServer(('127.0.0.1', 0), functools.partial(_Assets, directory=str(folder)))
        threading.Thread(target=_SERVER.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{_SERVER.server_port}/embedded.html?elucida&editor&lang={get_lang()}'


_WEB_CLASSES = []


def _web_classes():
    """Created once, not per editor. Lazy, WebEngine is a heavy import."""
    if not _WEB_CLASSES:
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineUrlRequestInterceptor

        class LocalOnly(QWebEngineUrlRequestInterceptor):
            def __init__(self, port, parent):
                super().__init__(parent)
                self.port = port

            def interceptRequest(self, info):
                u = info.requestUrl()
                allow = u.scheme() in ('qrc', 'data', 'blob') or (u.scheme() == 'http' and u.host() == '127.0.0.1' and u.port() == self.port)
                info.block(not allow)

        class Page(QWebEnginePage):
            def __init__(self, port, profile, parent):
                super().__init__(profile, parent)
                self.port = port

            def acceptNavigationRequest(self, u, kind, main):
                return not main or (u.host() == '127.0.0.1' and u.port() == self.port and u.path() == '/embedded.html')

            def javaScriptConsoleMessage(self, level, message, line, source):
                if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                    print(f'Octet JS: {message} ({line})')

        _WEB_CLASSES.extend((LocalOnly, Page))
    return _WEB_CLASSES


class Bridge(QObject):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner

    @Slot(bool)
    def state(self, dirty):
        self.owner.dirty = dirty
        self.owner.status.setText(T('draw_lossy') if self.owner.lossy else T('draw_unsaved') if dirty else self.owner.saved_message)
        if dirty:
            self.owner.autosave.start()
        else:
            self.owner.autosave.stop()
        # JavaScript has finished acknowledging the saved revision. Deliver the
        # saved data in this dialog's event loop, not through an unbound timer.
        self.owner.notify_saved()

    @Slot(str, str, result=str)
    def call(self, method, raw):
        try:
            if len(raw) > MAX_BYTES * 4:
                raise ValueError('Message too large')
            data = json.loads(raw)
            if method == 'save':
                if self.owner._saving:
                    raise RuntimeError(T('draw_saving'))
                self.owner.persist(data)
                value = True
            elif method in ('copy', 'paste'):
                from elucida.app.drawing_clipboard import copy_drawing, paste_drawing
                value = copy_drawing(data) if method == 'copy' else paste_drawing()
            elif method == 'edit_asset':
                key, shape_id = data.get('key'), data.get('shapeId')
                if not isinstance(key, str) or len(key) > 80 or not isinstance(shape_id, int):
                    raise ValueError('Invalid figure reference')
                QTimer.singleShot(0, lambda: self.owner.asset_edit_requested.emit(key, shape_id))
                value = True
            else:
                raise ValueError('Unsupported editor command')
            return json.dumps({'value': value})
        except Exception as ex:
            return json.dumps({'error': str(ex)})


class DrawingShortcutScope(QObject):
    """Keep host actions clickable but give their keyboard combinations to Octet.

    One coordinator also handles switching between embedded and
    compound editors without restoring another editor's suspended keys.
    """
    def __init__(self, app):
        super().__init__(app)
        self.root = None
        self.views = weakref.WeakSet()
        self.saved = None
        QApplication.instance().focusChanged.connect(self.refresh)

    def register(self, view):
        self.views.add(view)
        self.refresh()

    def refresh(self, *_):
        focus = QApplication.focusWidget()
        root = None
        if focus:
            for view in list(self.views):
                try:
                    if focus == view or view.isAncestorOf(focus):
                        root = view
                        while root.parentWidget() is not None:
                            root = root.parentWidget()
                        break
                except RuntimeError:
                    self.views.discard(view)
        if self.saved is not None and root != self.root:
            saved, self.saved = self.saved, None
            for action, shortcuts in saved:
                try:
                    action.setShortcuts(shortcuts)
                except RuntimeError:
                    pass  # Host menus may have been rebuilt while focus changed.
        self.root = root
        if root is not None and self.saved is None:
            self.saved = []
            for action in root.findChildren(QAction):
                shortcuts = action.shortcuts()
                if shortcuts:
                    self.saved.append((action, shortcuts))
                    action.setShortcuts([])



class StatusLabel(QLabel):
    """State of the editor. A host with a toast hides the line and shows `changed` there."""
    changed = Signal(str)

    def setText(self, text):
        super().setText(text)
        self.changed.emit(text)


class DrawingEditor(QWidget):
    saved = Signal(str)
    import_requested = Signal()
    external_requested = Signal()
    remove_requested = Signal()
    asset_edit_requested = Signal(str, int)
    fit_view = False                                        # True: show the whole drawing (zoom) instead of placing it

    def __init__(self, parent=None, *, scheme_actions=True, draft=False):
        super().__init__(parent)
        self.path = None
        self.expected = None
        self.lossy = {}
        self.dirty = False
        self.ready = False
        self._saving = False
        self._pending = None
        self._saved_pending = None
        self._unplaced = self._anchored = False
        self.top_third = scheme_actions                     # reaction scheme: upper third, room for the table below
        self.canvas_dark = False
        self.saved_message = T('draw_draft_saved' if draft else 'draw_saved')
        self.export_directory = None
        self.autosave = QTimer(self, singleShot=True, interval=1000)
        self.autosave.timeout.connect(lambda: self.save_sync(quiet=True) if self.dirty else None)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.action_bar = QWidget()
        bar = QHBoxLayout(self.action_bar)
        bar.setContentsMargins(0, 0, 0, 0)
        for label, command in [('draw_check', 'check_structure'), ('draw_cleanup', 'clean_up'), ('draw_name', 'name_to_structure')]:
            b = QPushButton(T(label)); b.clicked.connect(lambda _=False, c=command: self.command(c)); bar.addWidget(b)
        bar.addStretch()
        more = QPushButton("⋯")
        more.setToolTip(T('draw_files'))
        menu = QMenu(more)
        if scheme_actions:
            menu.addAction(T('syn_scheme_pick'), self.import_requested.emit)
        menu.addAction(T('draw_export_files'), self.export_files)
        menu.addAction(T('chemdraw_edit'), lambda: self.external_requested.emit() if self.save_sync() else None)
        if scheme_actions:
            menu.addSeparator()
            menu.addAction(T('remove'), self.remove_requested.emit)
        more.setMenu(menu)
        self.more_menu = menu
        bar.addWidget(more)
        lay.addWidget(self.action_bar)
        self.status = StatusLabel(T('draw_loading'))
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True)
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineScript
            from PySide6.QtWebChannel import QWebChannel
            url = asset_url()
            port = QUrl(url).port()

            LocalOnly, Page = _web_classes()
            self.profile = QWebEngineProfile(self)
            self.interceptor = LocalOnly(port, self.profile)
            self.profile.setUrlRequestInterceptor(self.interceptor)
            self.view = QWebEngineView(self)
            self.view.setFocusPolicy(Qt.StrongFocus)
            self.page = Page(port, self.profile, self.view)
            self.view.setPage(self.page)
            # QObject deletes children in insertion order: destroy the page before its profile.
            self.profile.setParent(self.view)
            self.channel = QWebChannel(self.page)
            self.bridge = Bridge(self)
            self.channel.registerObject('elucidaHost', self.bridge)
            self.page.setWebChannel(self.channel)
            resource = QFile(':/qtwebchannel/qwebchannel.js')
            if not resource.open(QIODevice.ReadOnly):
                raise RuntimeError('Qt WebChannel script is missing')
            script = QWebEngineScript()
            script.setName('Elucida WebChannel')
            script.setInjectionPoint(QWebEngineScript.DocumentCreation)
            script.setWorldId(QWebEngineScript.MainWorld)
            script.setSourceCode(bytes(resource.readAll()).decode())
            self.page.scripts().insert(script)
            self.view.installEventFilter(self)
            app = QApplication.instance()
            scope = getattr(app, '_drawing_shortcut_scope', None)
            if scope is None:
                scope = DrawingShortcutScope(app)
                app._drawing_shortcut_scope = scope
            scope.register(self.view)
            lay.addWidget(self.view, 1)
            self.page.loadFinished.connect(self._loaded)
            self.view.setUrl(QUrl(url))
            self._loaded(True)
        except (ImportError, RuntimeError, OSError) as ex:
            self.view = None
            lay.addWidget(QLabel(str(ex), wordWrap=True), 1)
            more.setEnabled(False)
        lay.addWidget(self.status)

    def focus_canvas_if_idle(self):
        # Octet uses keys at the hovered atom/bond. A navigation button must not
        # retain Space while the pointer is over the canvas; text entry keeps focus.
        focus = QApplication.focusWidget()
        if self.view and self.isVisible() and not isinstance(
                focus, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox, QMenu, QFileDialog)):
            self.view.setFocus(Qt.MouseFocusReason)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self.focus_canvas_if_idle()
        # The layout settles after the first show (column width, restored window): keep the drawing in place until the
        # user moves the view or draws.
        if event.type() in (QEvent.MouseButtonPress, QEvent.Wheel, QEvent.KeyPress, QEvent.NativeGesture):
            self._anchored = False
        elif event.type() == QEvent.Resize and obj is self.view and self._anchored:
            self._unplaced = True
            QTimer.singleShot(0, self.place)
        # A trackpad pinch (macOS) reaches Chromium as page zoom, which scales Octet's panels off screen. Hand it to
        # Octet as Ctrl+wheel instead, which zooms the drawing (Octet: zoom = exp(-deltaY / 100)).
        if event.type() == QEvent.NativeGesture and getattr(self, "page", None) is not None and event.gestureType() in (
                Qt.ZoomNativeGesture, Qt.SmartZoomNativeGesture):
            if event.gestureType() == Qt.ZoomNativeGesture and event.value() > -1:
                p = event.position()
                self.page.runJavaScript(
                    f'document.elementFromPoint({p.x():.1f}, {p.y():.1f})?.dispatchEvent(new WheelEvent("wheel", '
                    f'{{ctrlKey: true, bubbles: true, cancelable: true, clientX: {p.x():.1f}, clientY: {p.y():.1f}, '
                    f'deltaY: {-100 * math.log1p(event.value()):.3f}}}))')
            return True
        # Keep drawing shortcuts in the web view; global Qt Undo/Save must not take them.
        if event.type() == QEvent.ShortcutOverride and self.view and (obj is self.view or isinstance(obj, QWidget) and self.view.isAncestorOf(obj)):
            event.accept()
            return True
        return super().eventFilter(obj, event)

    def _loaded(self, ok):
        if not ok:
            self.status.setText(T('draw_load_error')); return
        if hasattr(self, "poll"):
            return
        self._poll_count = 0
        self.poll = QTimer(self, interval=100)
        self.poll.timeout.connect(self._poll)
        self.poll.start()

    def _poll(self):
        self._poll_count += 1
        if self._poll_count == 300:                  # slow start is not failure: keep looking, less often
            self.status.setText(T('draw_load_error')); self.poll.setInterval(1000)
        elif self._poll_count > 900:
            self.poll.stop(); return
        self.page.runJavaScript('!!(window.elucida && window.elucidaHost)', self._ready)

    def _ready(self, ok):
        # The answer can arrive after a tab rebuild deleted this editor (language or theme switch, undo).
        if not ok or self.ready or not isValid(self):
            return
        self.poll.stop(); self.ready = True
        proxy = self.view.focusProxy()
        if proxy:
            proxy.installEventFilter(self)
        if self.view.underMouse():
            self.focus_canvas_if_idle()
        self.set_canvas_dark(self.canvas_dark)
        self.status.setText(self.saved_message)
        if self._pending:
            QTimer.singleShot(0, self._open_pending)

    def _open_pending(self):
        if isValid(self) and self._pending:
            self.open_path(self._pending)

    def open_path(self, path):
        p = Path(path).resolve()
        if self.path == p and self.expected == fingerprint(p):
            return True
        if self.dirty and not self.save_sync():
            return False
        if not self.ready:
            self._pending = p; return True
        if getattr(self, '_opening', False):
            # Schon beim Laden: _js wartet in einer eigenen Ereignisschleife, in der ein weiteres _open_pending feuern kann.
            # Verschachtelt warten die Aufrufe aufeinander (je bis 15 s, das Fenster hängt): stattdessen vormerken.
            self._pending = p; return True
        self._opening, self._pending = True, None
        try:
            text = p.read_text(encoding='utf-8')
            if p.suffix.lower() != '.cdxml' or ET.fromstring(text).tag != 'CDXML':
                raise ValueError(T('draw_invalid'))
            expected = fingerprint(p)
            lost = self._js(f'window.elucida.load({json.dumps(text)}, {json.dumps(p.stem)})') or {}
        except Exception as ex:
            if isValid(self):                              # während des Wartens kann der Tab neu gebaut worden sein
                self.status.setText(str(ex))
            return False
        finally:
            if isValid(self):
                self._opening = False
                if self._pending and self._pending != p:   # währenddessen wurde eine andere Datei verlangt
                    QTimer.singleShot(0, self._open_pending)
                else:
                    self._pending = None
        self.path, self.expected = p, expected
        self.lossy = lost
        if lost:
            self.status.setText(T('draw_lossy'))
        self.dirty = False
        self._unplaced = self._anchored = True
        self.place()
        return True

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.place)

    def status_to(self, show):
        """Host with a toast: hide the status line and pass on notes and errors only (saved/unsaved/saving change all
        the time with autosave)."""
        self.status.hide()
        routine = lambda: (self.saved_message, T('draw_unsaved'), T('draw_saving'), T('draw_loading'))
        self.status.changed.connect(lambda t: bool(t) and t not in routine() and show(t))

    def place(self, tries=100):
        """Octet centres a loaded drawing in the size its page has at that moment: a hidden or not yet laid out
        editor gave any position. Place it once the page has the size of the view."""
        if not (isValid(self) and self._unplaced and self.ready and self.view.isVisible()):
            return                                         # hidden: showEvent asks again
        self._unplaced = False                             # one request at a time: a second one would move twice
        def done(distance):
            if not isValid(self):
                return
            if distance is False and tries:
                self._unplaced = True
                QTimer.singleShot(50, lambda: self.place(tries - 1))
            elif self.fit_view:
                self.command('zoom_fit')
        self.page.runJavaScript(self.place_code(not self.fit_view), done)

    def place_code(self, move):
        return f'{_PLACE}({self.view.width()}, {self.view.height()}, {json.dumps(self.top_third)}, {json.dumps(move)})'

    def _js(self, expression):
        result = []
        loop = QEventLoop()
        timer = QTimer(singleShot=True, interval=15000)
        timer.timeout.connect(loop.quit)
        self.destroyed.connect(loop.quit)                  # sonst wartet die Schleife die vollen 15 s
        def done(raw):
            result.append(raw)
            loop.quit()
        code = '(() => {try {const value = (' + expression + '); return JSON.stringify({value})} catch(e) {return JSON.stringify({error:String(e)})}})()'
        self.page.runJavaScript(code, done)
        timer.start()
        if not result:
            loop.exec()
        timer.stop()
        if not result or not result[0]:
            raise RuntimeError(T('draw_load_error'))
        answer = json.loads(result[0])
        if answer.get('error'):
            raise ValueError(answer['error'])
        return answer.get('value')

    def command(self, name):
        if self.ready:
            self.page.runJavaScript(f'window.elucida.command({json.dumps(name)})')
            self.view.setFocus()

    def persist(self, bundle):
        if self.path is None:
            raise ValueError(T('draw_no_file'))
        if self.lossy:
            raise ValueError(T('draw_lossy'))
        self.expected = save_bundle(self.path, bundle, self.expected)
        self.dirty = False
        self.status.setText(self.saved_message)
        # Notify after the JS acknowledgement, or synchronously before save_sync
        # returns. A caller accepting a modal dialog must already have its fields.
        self._saved_pending = str(self.path)

    def notify_saved(self):
        path, self._saved_pending = self._saved_pending, None
        if path:
            self.saved.emit(path)

    def wait_ready(self, seconds=30):
        """Export right after opening a compound: the page may still be loading."""
        end = time.monotonic() + seconds
        while not (self.ready and self.path) and time.monotonic() < end:
            QApplication.processEvents()
            time.sleep(0.02)
        return bool(self.ready and self.path)

    def save_sync(self, quiet=False):
        if self._saving:
            return False
        if not self.ready:
            self.status.setText(T('draw_loading'))
            return False
        self._saving = True
        self.status.setText(T("draw_saving"))
        try:
            self.persist(self._js('window.elucida.snapshot()'))
            self._js('window.elucida.markSaved()')
            self.notify_saved()
            return True
        except Exception as ex:
            self.status.setText(T('draw_save_failed') + ': ' + str(ex))
            if not quiet:
                QMessageBox.warning(self, T('draw_title'), str(ex))
            return False
        finally:
            self._saving = False

    def set_canvas_dark(self, dark):
        self.canvas_dark = bool(dark)
        if self.ready:
            self.page.runJavaScript('window.elucida.theme(' + json.dumps(self.canvas_dark) + ')')

    def export_files(self):
        if not self.ready or not self.path:
            return
        default = Path(self.export_directory or self.path.parent) / (self.path.stem + '_copy.cdxml')
        name, _ = QFileDialog.getSaveFileName(self, T('draw_export_files'), str(default), 'ChemDraw (*.cdxml *.cdx)')
        if name:
            target = Path(name)
            if target.suffix.lower() not in ('.cdxml', '.cdx'):
                target = target.with_suffix('.cdxml')
            if target.resolve() in (self.path, self.path.with_suffix('.cdx')):
                self.save_sync()
                return
            try:
                # A separate copy must work even when the original has an external-edit conflict.
                bundle = self._js('window.elucida.snapshot()')
                if target.suffix.lower() == '.cdxml':
                    save_bundle(target, bundle, fingerprint(target))
                else:
                    data = base64.b64decode(bundle['cdx'], validate=True)
                    temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
                    try:
                        temporary.write_bytes(data)
                        os.replace(temporary, target)
                    finally:
                        temporary.unlink(missing_ok=True)
            except Exception as ex:
                QMessageBox.warning(self, T('draw_title'), str(ex))


def release_pages(app):
    """At quit, before the windows go: pages first, then give Chromium a moment. A page and its profile deleted in one
    step while the page was still loading ended the app on Windows (0x80000003, Chromium's fatal check)."""
    editors = [e for t in app.topLevelWidgets() for e in t.findChildren(DrawingEditor) if e.view is not None]
    for e in editors:
        e.poll.stop()
        e.autosave.stop()
        delete(e.page)
    end = time.monotonic() + (0.3 if editors else 0)
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


class DrawingDialog(QDialog):
    """Reject closing when saving fails; keep the unsaved editor available for recovery."""
    editor = None

    def done(self, result):
        if self.editor and self.editor.dirty and not self.editor.save_sync():
            # A conflict can be permanent: export a copy first, but never trap the user in here.
            if QMessageBox.question(self, T('draw_title'), T('draw_discard_close'),
                                    QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel) != QMessageBox.Discard:
                return
        super().done(result)
