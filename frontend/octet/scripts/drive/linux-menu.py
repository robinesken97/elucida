#!/usr/bin/env python3
# Clicks an item in Octet's menu bar on Linux, through the accessibility bus (AT-SPI) as a screen reader does: the
# item's own click action, so GTK runs the item as a click with the mouse would (scripts/drive/drive.mjs).
#
#   linux-menu.py PID Edit Paste      the Edit menu's Paste item in the window of process PID
#   linux-menu.py PID File New*       the first item whose name starts with New and that is not a submenu
#   linux-menu.py PID                 the name of the process's window in front
#
# Octet has a window for Home and one for each drawing. The menu bar used is the one of the window in front, as a
# person uses it; Octet sends each menu command to the window in front (src-tauri/src/windows.rs).
import sys
import time

import pyatspi


def children(node):
    try:
        return [node.getChildAtIndex(i) for i in range(node.childCount)]
    except Exception:
        return []


def walk(node, depth=0):
    if node is None or depth > 30:
        return
    yield node
    for child in children(node):
        yield from walk(child, depth + 1)


def matches(node, want, roles):
    name = (node.name or "").strip()
    if node.getRoleName() not in roles:
        return False
    return name.startswith(want[:-1]) if want.endswith("*") else name == want


def octet(pid):
    for app in children(pyatspi.Registry.getDesktop(0)):
        try:
            if app is not None and str(app.get_process_id()) == pid:
                return app
        except Exception:
            continue
    return None


def main():
    pid, path = sys.argv[1], sys.argv[2:]
    app = None
    # The app joins the bus a moment after its window shows.
    for _ in range(40):
        app = octet(pid)
        if app is not None:
            break
        time.sleep(0.25)
    if app is None:
        sys.exit(f"AT-SPI shows no application for process {pid}")
    frames = [n for n in children(app) if n.getRoleName() == "frame"]
    front = next((f for f in frames if f.getState().contains(pyatspi.STATE_ACTIVE)), None)
    if not path:
        print(front.name if front else "")
        return
    bar = next((n for n in walk(front or app) if n.getRoleName() == "menu bar"), None)
    if bar is None:
        sys.exit("Octet's window has no menu bar on the accessibility bus")
    node = bar
    for k, want in enumerate(path):
        leaf = k == len(path) - 1
        roles = ("menu item", "check menu item") if leaf else ("menu",)
        found = next((n for n in walk(node) if n is not node and matches(n, want, roles)), None)
        if found is None:
            names = sorted({(n.name or "") for n in walk(node) if n.getRoleName() in ("menu", "menu item", "check menu item")})
            sys.exit(f"no {' > '.join(path[:k + 1])} in the menu bar; it has: {', '.join(names)}")
        node = found
    action = node.queryAction()
    for i in range(action.nActions):
        if action.getName(i) in ("click", "activate", "press"):
            action.doAction(i)
            time.sleep(0.5)
            return
    sys.exit(f"{' > '.join(path)} has no click action")


main()
