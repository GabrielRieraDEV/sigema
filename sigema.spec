# -*- mode: python ; coding: utf-8 -*-
"""
sigema.spec — Especificación de PyInstaller para SIGEMA.

Construye un ÚNICO ejecutable de Windows, sin consola (modo producción):

    pyinstaller sigema.spec --clean

Resultado:  dist\\sigema.exe

Notas:
- PostgreSQL NO se empaqueta: corre en el servidor (ver instalacion/servidor).
- config.ini NO se incluye: se genera en el primer arranque junto al .exe.
  Sí se incluye config.example.ini como referencia.
- Para que el icono funcione, lo ideal es un .ico. Si solo hay .png, se usa
  igual (puede requerir Pillow). Si no hay icono, se omite sin fallar.
"""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = os.path.abspath(os.getcwd())

# ---------------------------------------------------------------------------
# Recursos a empaquetar dentro del .exe
# ---------------------------------------------------------------------------
datas = [
    ("assets", "assets"),                  # logos e icono
    ("sql/schema.sql", "sql"),             # esquema (referencia)
    ("config.example.ini", "."),           # plantilla de configuración
]
# Fuentes y datos internos de ReportLab (necesarios para los PDF).
datas += collect_data_files("reportlab")

# ---------------------------------------------------------------------------
# Imports que el analizador podría no detectar (imports tardíos / dinámicos)
# ---------------------------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("src")
hiddenimports += [
    "src.ui.setup_inicial",   # importado dentro de main()
    "src.ui.login",           # importado dentro de main()
    "psycopg2",
    "dbfread",                # lectura de .dbf en la migración
    "openpyxl",               # lectura de .xlsx en la migración
]

# ---------------------------------------------------------------------------
# Icono de la aplicación
# ---------------------------------------------------------------------------
def _resolver_icono():
    for cand in ("assets/icono.ico", "assets/icono .png", "assets/logo.png"):
        if os.path.isfile(cand):
            return cand
    return None


ICON = _resolver_icono()


block_cipher = None

a = Analysis(
    ["src/main.py"],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PySide6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# EXE en modo onefile: incluye binaries, zipfiles y datas dentro del .exe.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="sigema",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # --windowed (sin ventana de consola)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
