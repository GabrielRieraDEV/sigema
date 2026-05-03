"""
backup.py — Respaldo de la base de datos usando pg_dump.

Implementa NF-04: generar backup desde la interfaz de administración.
El archivo se guarda con el nombre:
    sigema_backup_YYYYMMDD_HHMMSS.sql
en el directorio configurado en config.ini bajo [backup] → directorio.
"""

from __future__ import annotations

import configparser
import os
import subprocess
from datetime import datetime
from pathlib import Path


def _leer_config() -> tuple[dict, str]:
    """Lee la configuración de la BD y el directorio de backups.

    Returns
    -------
    tuple[dict, str]
        (parametros_bd, directorio_backup)
    """
    # Buscar config.ini subiendo desde este archivo
    current = Path(__file__).resolve().parent
    config_path: Path | None = None
    for _ in range(6):
        candidate = current / "config.ini"
        if candidate.is_file():
            config_path = candidate
            break
        current = current.parent

    if config_path is None:
        raise FileNotFoundError("No se encontró config.ini.")

    cfg = configparser.ConfigParser()
    cfg.read(str(config_path), encoding="utf-8")

    if "database" not in cfg:
        raise ValueError("config.ini no contiene la sección [database].")

    db = cfg["database"]
    params = {
        "host": db.get("host", "localhost"),
        "port": db.get("port", "5432"),
        "dbname": db.get("dbname", "sigema"),
        "user": db.get("user", "sigema_user"),
        "password": db.get("password", ""),
    }

    # Directorio de backups: sección [backup] → directorio
    # Default: carpeta 'backups' al lado del ejecutable / raíz del proyecto
    if "backup" in cfg and cfg["backup"].get("directorio"):
        directorio = cfg["backup"]["directorio"]
    else:
        directorio = str(Path(config_path).parent / "backups")

    return params, directorio


def ejecutar_backup() -> tuple[bool, str]:
    """Ejecuta pg_dump y guarda el archivo de respaldo.

    Llama a ``pg_dump`` pasando las credenciales de config.ini.
    La contraseña se pasa via variable de entorno ``PGPASSWORD``
    para evitar exposición en la línea de comandos.

    Returns
    -------
    tuple[bool, str]
        ``(True, ruta_del_archivo)`` si tuvo éxito.
        ``(False, mensaje_de_error)`` si ocurrió un error.
    """
    try:
        params, directorio = _leer_config()
    except (FileNotFoundError, ValueError) as exc:
        return False, str(exc)

    # Crear directorio si no existe
    try:
        os.makedirs(directorio, exist_ok=True)
    except OSError as exc:
        return False, f"No se pudo crear el directorio de backups:\n{exc}"

    # Nombre del archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"sigema_backup_{timestamp}.sql"
    ruta_archivo = os.path.join(directorio, nombre_archivo)

    # Construir comando pg_dump
    cmd = [
        "pg_dump",
        "-h", params["host"],
        "-p", params["port"],
        "-U", params["user"],
        "-d", params["dbname"],
        "--no-password",
        "-f", ruta_archivo,
        "--encoding=UTF8",
        "--verbose",
    ]

    # Pasar contraseña via variable de entorno (seguro, no aparece en ps/tasklist)
    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    try:
        resultado = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutos máximo
        )
    except FileNotFoundError:
        return (
            False,
            "No se encontró el ejecutable 'pg_dump'.\n"
            "Asegúrese de que PostgreSQL está instalado y que 'pg_dump' "
            "está en el PATH del sistema.",
        )
    except subprocess.TimeoutExpired:
        return False, "El backup excedió el tiempo límite de 5 minutos."
    except Exception as exc:
        return False, f"Error al ejecutar pg_dump: {exc}"

    if resultado.returncode != 0:
        error_msg = resultado.stderr.strip() or "Error desconocido en pg_dump."
        return False, f"pg_dump terminó con error (código {resultado.returncode}):\n{error_msg}"

    # Verificar que el archivo fue creado y no está vacío
    if not os.path.isfile(ruta_archivo):
        return False, "pg_dump ejecutó pero el archivo no fue creado."

    tamaño_kb = os.path.getsize(ruta_archivo) // 1024

    return True, ruta_archivo


def obtener_directorio_backup() -> str:
    """Retorna el directorio de backups configurado en config.ini."""
    try:
        _, directorio = _leer_config()
        return directorio
    except Exception:
        return ""
