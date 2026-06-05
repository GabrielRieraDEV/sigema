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

    # Directorio de backups. Se acepta, en orden de prioridad:
    #   1. [app] backup_folder   (config.example.ini de producción)
    #   2. [backup] directorio   (alias histórico)
    #   3. carpeta 'backups' junto al ejecutable / raíz del proyecto
    if "app" in cfg and cfg["app"].get("backup_folder"):
        directorio = cfg["app"]["backup_folder"]
    elif "backup" in cfg and cfg["backup"].get("directorio"):
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
        "--encoding=UTF8",
        "--verbose",
    ]

    # Pasar contraseña via variable de entorno
    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    try:
        with open(ruta_archivo, "wb") as f_out:
            resultado = subprocess.run(
                cmd,
                env=env,
                stdout=f_out,
                stderr=subprocess.PIPE,
                timeout=300,
            )
            
        if resultado.returncode != 0:
            error_msg = resultado.stderr.decode("utf-8", errors="replace").strip()
            return False, f"pg_dump terminó con error (código {resultado.returncode}):\n{error_msg}"
            
    except FileNotFoundError:
        # Fallback: Intentar con Docker
        cmd_docker = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={params['password']}",
            "sigema_db",
            "pg_dump",
            "-U", params["user"],
            "-d", params["dbname"],
            "--no-password",
            "--encoding=UTF8",
            "--verbose",
        ]
        try:
            with open(ruta_archivo, "wb") as f_out:
                resultado = subprocess.run(
                    cmd_docker,
                    stdout=f_out,
                    stderr=subprocess.PIPE,
                    timeout=300,
                )
            if resultado.returncode != 0:
                error_msg = resultado.stderr.decode("utf-8", errors="replace").strip()
                return False, f"pg_dump (Docker) terminó con error:\n{error_msg}"
        except FileNotFoundError:
            return (
                False,
                "No se encontró 'pg_dump' ni 'docker'.\n"
                "Para hacer respaldos necesita PostgreSQL instalado localmente o Docker ejecutándose."
            )
        except subprocess.TimeoutExpired:
            return False, "El backup en Docker excedió el tiempo límite."
        except Exception as exc:
            return False, f"Error al ejecutar docker pg_dump: {exc}"

    except subprocess.TimeoutExpired:
        return False, "El backup excedió el tiempo límite de 5 minutos."
    except Exception as exc:
        return False, f"Error al ejecutar pg_dump: {exc}"

    # Verificar que el archivo fue creado y no está vacío
    if not os.path.isfile(ruta_archivo) or os.path.getsize(ruta_archivo) == 0:
        return False, "El comando se ejecutó pero el archivo de backup está vacío o no se creó."

    return True, ruta_archivo


def obtener_directorio_backup() -> str:
    """Retorna el directorio de backups configurado en config.ini."""
    try:
        _, directorio = _leer_config()
        return directorio
    except Exception:
        return ""
