"""Punto de entrada para PyInstaller.

PyInstaller necesita un script, no un módulo dentro de un paquete. Este archivo
solo delega en verbasizer.desktop.
"""

from verbasizer.desktop import main

if __name__ == "__main__":
    raise SystemExit(main())
