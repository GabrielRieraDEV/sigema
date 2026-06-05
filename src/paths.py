"""
paths.py — Resolución de rutas robusta para desarrollo y para el .exe.

Cuando SIGEMA corre empaquetado con PyInstaller en modo *onefile*, el código
y los recursos se extraen a una carpeta temporal (``sys._MEIPASS``) que se
borra al cerrar el programa.  El ejecutable, en cambio, vive en una carpeta
estable elegida por el usuario.

Consecuencias:
- ``config.ini`` debe vivir JUNTO al ejecutable (carpeta estable) para que
  la configuración persista entre ejecuciones.
- Los recursos empaquetados (``assets/``, ``sql/``) viven DENTRO de
  ``_MEIPASS`` en modo congelado.

Este módulo centraliza ambas resoluciones para que el resto del código no
tenga que preocuparse por el modo de ejecución.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True si el programa corre empaquetado (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def app_base_dir() -> Path:
    """Carpeta estable de la aplicación.

    - Congelado: la carpeta donde está el ``sigema.exe``.
    - Desarrollo: la raíz del proyecto (donde está ``requirements.txt``).
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent

    current = Path(__file__).resolve().parent
    for _ in range(6):
        if (current / "requirements.txt").is_file():
            return current
        current = current.parent
    # Fallback: la carpeta que contiene el paquete 'src'.
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    """Ruta de ``config.ini`` (siempre junto al ejecutable / raíz del proyecto)."""
    return app_base_dir() / "config.ini"


def resource_path(rel: str) -> Path:
    """Ruta a un recurso empaquetado (p. ej. ``"assets/logo.png"``).

    En modo congelado busca dentro de ``_MEIPASS``; si no está ahí, o en
    desarrollo, lo busca relativo a la carpeta base de la aplicación.
    """
    rel_norm = rel.replace("/", os.sep)
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cand = Path(meipass) / rel_norm
            if cand.exists():
                return cand
    return app_base_dir() / rel_norm
