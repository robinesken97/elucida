"""macOS: Fensterinhalt bis ganz nach oben (wie die Claude-App), Ampelknöpfe liegen auf der Werkzeugleiste.

Qt (ab 6.9) zieht den Inhalt per `ExpandedClientAreaHint` unter die Titelleiste; Titel ausblenden und die Höhe der
Titelleiste (leere kompakte NSToolbar, Ampelknöpfe dann mittig in ~40 pt) gehen nur über AppKit – hier per ctypes,
ohne pyobjc. Windows/Linux behalten die normale Titelleiste (rahmenloses Fenster hieße Snap/Größe nachbauen).
"""
import ctypes
import ctypes.util
import sys

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QAbstractButton

def enabled():
    """Nur mit echtem Cocoa-Fenster (nicht offscreen im Selbsttest: winId wäre dort kein NSView)."""
    return (sys.platform == "darwin" and hasattr(Qt.WindowType, "ExpandedClientAreaHint")
            and QGuiApplication.platformName() == "cocoa")

INSET = 78                    # Platz links für die drei Ampelknöpfe (px)
_NS_TITLE_HIDDEN = 1          # NSWindowTitleHidden
_NS_TOOLBAR_COMPACT = 4       # NSWindowToolbarStyleUnifiedCompact


def _msg(obj, sel, *args, argtypes=()):
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.sel_registerName.restype = ctypes.c_void_p
    f = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, *argtypes)(("objc_msgSend", objc))
    return f(obj, objc.sel_registerName(sel.encode()), *args)


def _ns_class(name):
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.objc_getClass.restype = ctypes.c_void_p
    return objc.objc_getClass(name.encode())


def prepare(win):
    """Vor dem ersten Anzeigen: Inhalt unter die (durchsichtige) Titelleiste ziehen."""
    if not enabled():
        return
    win.setWindowFlag(Qt.ExpandedClientAreaHint, True)
    win.setWindowFlag(Qt.NoTitleBarBackgroundHint, True)
    win.setAttribute(Qt.WA_ContentsMarginsRespectsSafeArea, False)


def finish(win):
    """Nach dem Anzeigen: Titel ausblenden, Titelleiste auf Werkzeugleistenhöhe. -> Höhe in px, 0 = nicht aktiv.
    Scheitert AppKit, rückt der Inhalt wieder unter die Titelleiste (Titel überdeckt sonst die Knöpfe)."""
    if not enabled():
        return 0
    try:
        ns_win = _msg(int(win.winId()), "window")
        if not ns_win:
            raise RuntimeError("kein NSWindow")
        _msg(ns_win, "setTitleVisibility:", _NS_TITLE_HIDDEN, argtypes=(ctypes.c_long,))
        bar = _msg(_msg(_ns_class("NSToolbar"), "alloc"), "init")
        _msg(ns_win, "setToolbar:", bar, argtypes=(ctypes.c_void_p,))
        _msg(ns_win, "setToolbarStyle:", _NS_TOOLBAR_COMPACT, argtypes=(ctypes.c_long,))
        return win.windowHandle().safeAreaMargins().top()
    except Exception:
        win.setAttribute(Qt.WA_ContentsMarginsRespectsSafeArea, True)
        return 0


def set_toolbar_visible(win, on):
    """Leere NSToolbar im Vollbild aus: macOS zeigt sie dort sonst als grauen Balken über dem Inhalt."""
    try:
        bar = _msg(_msg(int(win.winId()), "window"), "toolbar")
        if bar:
            _msg(bar, "setVisible:", bool(on), argtypes=(ctypes.c_bool,))
    except Exception:
        pass


class TitleDrag(QObject):
    """Werkzeugleiste als Titelleiste: an freien Stellen ziehen = Fenster verschieben, Doppelklick = Zoomen."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick) and ev.button() == Qt.LeftButton:
            child = obj.childAt(ev.position().toPoint())
            if isinstance(child, QAbstractButton):
                return False                            # Knopf getroffen
            if t == QEvent.MouseButtonDblClick:
                self.win.showNormal() if self.win.isMaximized() else self.win.showMaximized()
            else:
                self.win.windowHandle().startSystemMove()
            return True
        return False
