"""Regression check: native Qt events must reach Octet, not the surrounding window."""
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest


def check_drawing_keys(window):
    editor = window.syn_tab.drawing_editor
    start_page = window.center.currentIndex()
    editor._js('(() => {window.__keys = []; document.addEventListener("keydown", e => window.__keys.push(e.key), true)})()')
    window.activateWindow()
    window.btn_home.setFocus()
    QTest.qWait(100)
    target = editor.view.focusProxy() or editor.view
    QTest.mouseMove(window.btn_home, QPoint(10, 10))
    QTest.qWait(150)
    QTest.mouseMove(target, QPoint(250, 150))
    # Deliver the boundary crossing explicitly: macOS coalesces cursor moves
    # in GUI tests whose window was launched without activating the application.
    QApplication.sendEvent(editor.view, QEnterEvent(QPointF(250, 150), QPointF(250, 150), QPointF(250, 150)))
    QTest.qWait(200)
    focus = QApplication.focusWidget()
    print('Drawing focus:', type(focus).__name__, flush=True)
    assert focus is not None and (focus == editor.view or editor.view.isAncestorOf(focus)), 'canvas hover left focus on the navigation button'
    assert not window.act_home.shortcuts(), 'host shortcut remained registered in drawing'
    QTest.keyClick(focus, Qt.Key_X)
    QTest.qWait(100)
    QTest.keyClick(focus, Qt.Key_Space)
    QTest.qWait(200)
    assert window.center.currentIndex() == start_page, 'Space opened the application home page'
    assert ' ' in editor._js('window.__keys'), 'Space did not reach Octet'
    selected = editor._js('document.querySelector("button.tool[aria-pressed=true]")?.getAttribute("aria-label")')
    assert selected and selected.lower().startswith('select'), f'Space did not select Octet selection tool: {selected}'
    # Elucida assigns this key to Home; Octet assigns it to horizontal flip.
    QTest.keyClick(focus, Qt.Key_H, Qt.ControlModifier | Qt.ShiftModifier)
    QTest.qWait(200)
    assert window.center.currentIndex() == start_page, 'application shortcut stole Octet horizontal flip'
    window.syn_tab.ed_proc.setFocus()
    QApplication.sendEvent(editor.view, QEnterEvent(QPointF(), QPointF(), QPointF()))
    assert QApplication.focusWidget() == window.syn_tab.ed_proc, 'hover stole focus from procedure text'
    assert window.act_home.shortcuts(), 'host shortcut was not restored outside drawing'
    print('OK: Space selects Octet Select; app shortcut isolated; text focus preserved', flush=True)
