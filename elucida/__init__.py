"""Elucida: von der Synthese zur SI – Auswertung und Abbildungen für Charakterisierungsdaten."""
import os
import time
from pathlib import Path

APP_NAME = "Elucida"
APP_VERSION = "1.5.0"
def octet_enabled():
    """Integrierter Zeichner, Standard an; ELUCIDA_OCTET=0 schaltet ihn ab (Fehlersuche)."""
    return os.environ.get("ELUCIDA_OCTET", "1") != "0"


ROOT = Path(__file__).resolve().parent.parent       # Repo-Wurzel (assets/, README, tools/); gebaut: sys._MEIPASS


# Windows: Indexer, Virenscanner oder Explorer halten eine eben geschriebene Datei kurz offen (WinError 5 beim Umbenennen)
REPLACE_TRIES = 10 if os.name == "nt" else 1


def replace_file(src, dst):
    """Atomares Ersetzen tmp -> Ziel (os.replace); unter Windows bei PermissionError bis ~1 s erneut versuchen. Danach der
    letzte Fehler; die tmp-Datei bleibt dann liegen (sie enthält den neuen Stand), das Ziel bleibt unverändert."""
    for i in range(REPLACE_TRIES):
        try:
            return os.replace(src, dst)
        except PermissionError:
            if i == REPLACE_TRIES - 1:
                raise
            time.sleep(0.1)
