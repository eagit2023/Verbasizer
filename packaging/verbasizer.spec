# -*- mode: python ; coding: utf-8 -*-
"""Configuración de PyInstaller para Verbasizer.

Produce:
  macOS    dist/Verbasizer.app
  Windows  dist/Verbasizer/Verbasizer.exe   (carpeta; se distribuye comprimida)

Se compila desde la raíz del repositorio:
  pyinstaller packaging/verbasizer.spec --noconfirm

Requiere instalados los extras `desktop` y `build`, y los dos modelos de spaCy.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

ROOT = Path(SPECPATH).parent  # noqa: F821 — SPECPATH lo define PyInstaller
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

datas = [(str(ROOT / "web"), "web")]
binaries = []
hiddenimports = []

# spaCy y thinc tienen hooks en pyinstaller-hooks-contrib (código y datos).
# Lo que esos hooks NO cubren:
#   - los modelos de idioma, que son paquetes aparte;
#   - los metadatos de los paquetes que registran componentes de spaCy por
#     entry points (spacy-legacy, spacy-loggers) — sin ellos, spacy.load()
#     falla al resolver arquitecturas.
for package in ("es_core_news_sm", "en_core_web_sm"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

for package in ("spacy", "spacy_legacy", "spacy_loggers", "thinc", "catalogue", "confection"):
    datas += copy_metadata(package)

hiddenimports += ["spacy_legacy", "spacy_loggers"]

# PyInstaller arrastra cualquier dependencia que encuentre aunque no se use
# (lo advierte la documentación de pywebview). Excluimos explícitamente lo que
# este proyecto no necesita en ninguna plataforma.
excludes = [
    "tkinter",
    "torch", "tensorflow", "jax",
    "matplotlib", "IPython", "notebook", "pandas",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "qtpy",
    "cefpython3",
    "pytest",
]
if not sys.platform.startswith("linux"):
    excludes.append("gi")  # GTK solo se usaría en Linux

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Verbasizer",
    console=False,          # aplicación de ventana, sin terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    upx=False,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Verbasizer",
)

if IS_MAC:
    app = BUNDLE(  # noqa: F821
        coll,
        name="Verbasizer.app",
        bundle_identifier="io.github.eagit2023.verbasizer",
        info_plist={
            "CFBundleName": "Verbasizer",
            "CFBundleDisplayName": "Verbasizer",
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
