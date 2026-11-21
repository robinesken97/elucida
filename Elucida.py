"""Startdatei: python Elucida.py [VERBINDUNGSORDNER [--tab KEY] | MESSDATEI]
[--selftest ORDNER [--selftest-group NAME[,NAME…]]] (auch Einstieg für PyInstaller, siehe tools/build.py)."""
from elucida.app.main_window import main

if __name__ == "__main__":
    main()
