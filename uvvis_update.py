"""uvvis_update.py - Prüfen, ob auf GitHub eine neuere Version veröffentlicht ist.

Fragt nur die öffentliche GitHub-API ab (neuestes Release, ohne Entwürfe/Vorabversionen) und
sendet dabei nichts außer der Programmversion im User-Agent. Herunterladen/Installieren macht
der Nutzer selbst über die Release-Seite.
"""
from __future__ import annotations

import json
import platform
import re
import sys
import urllib.request

REPO = "robinesken97/uvvis-tool"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"


def parse_version(s):
    """'v1.3.0' -> (1, 3, 0), '1.3' -> (1, 3, 0), '1.4.0-beta' -> (1, 4, 0); unlesbar -> ()."""
    m = re.match(r"\s*v?(\d+(?:\.\d+)*)", str(s or ""))
    if not m:
        return ()
    nums = [int(x) for x in m.group(1).split(".")]
    return tuple(nums + [0] * (3 - len(nums)))


def is_newer(latest, current):
    a, b = parse_version(latest), parse_version(current)
    return bool(a) and bool(b) and a > b


def platform_label():
    """Name des Release-Pakets für dieses System (wie in .github/workflows/build.yml)."""
    if sys.platform.startswith("win"):
        return "windows-x64"
    if sys.platform == "darwin":
        return "macos-arm64" if platform.machine().lower() in ("arm64", "aarch64") else "macos-x64"
    return "linux-x64"


def parse_release(data):
    """GitHub-API-Antwort -> {version, url, asset}. asset = Dateiname für dieses System oder None."""
    tag = data.get("tag_name") or ""
    label = platform_label()
    names = [a.get("name") or "" for a in data.get("assets") or [] if label in (a.get("name") or "")]
    asset = next((n for n in names if n.endswith(".AppImage")), None) or next(iter(names), None)  # Linux: AppImage
    return {"version": tag.lstrip("v"), "url": data.get("html_url") or RELEASES_URL, "asset": asset}


def fetch_latest(current, timeout=8.0):
    req = urllib.request.Request(API_URL, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": f"UVVisTool/{current}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return parse_release(json.loads(r.read().decode("utf-8")))
