"""Elucida: von der Synthese zur SI – Auswertung und Abbildungen für Charakterisierungsdaten."""
import os
from pathlib import Path

APP_NAME = "Elucida"
APP_VERSION = "2.6.2"
def octet_enabled():
    """Integrierter Zeichner, Standard an; ELUCIDA_OCTET=0 schaltet ihn ab (Fehlersuche)."""
    return os.environ.get("ELUCIDA_OCTET", "1") != "0"


ROOT = Path(__file__).resolve().parent.parent       # Repo-Wurzel (assets/, README, tools/); gebaut: sys._MEIPASS
