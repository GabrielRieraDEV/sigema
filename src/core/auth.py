"""
auth.py — Autenticación y gestión de sesión de SIGEMA.

Implementa el Singleton Session que gestiona el usuario autenticado,
el control de inactividad (NF-05) y la verificación de permisos
por perfil (RN-10, RN-11).
"""

from __future__ import annotations

import configparser
import os
import threading
from datetime import datetime, timedelta
from typing import Any

import bcrypt

from src.db.connection import DBConnection


def _cargar_timeout_minutos(defecto: int = 30) -> int:
    """Lee [app] session_timeout_minutes de config.ini (NF-05).

    Si el archivo o la clave no existen, o el valor no es válido, devuelve
    el valor por defecto (30 minutos).
    """
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        candidate = os.path.join(current, "config.ini")
        if os.path.isfile(candidate):
            try:
                cfg = configparser.ConfigParser()
                cfg.read(candidate, encoding="utf-8")
                valor = cfg.get("app", "session_timeout_minutes", fallback=None)
                if valor is not None and int(valor) > 0:
                    return int(valor)
            except (ValueError, configparser.Error):
                pass
            break
        current = os.path.dirname(current)
    return defecto


# Tiempo máximo de inactividad en minutos (NF-05). Configurable vía
# config.ini → [app] session_timeout_minutes.
TIMEOUT_MINUTOS: int = _cargar_timeout_minutos()

# ---------------------------------------------------------------------------
# Tabla de permisos por perfil
# ---------------------------------------------------------------------------
_PERMISOS: dict[str, set[str]] = {
    "Administrador": {
        "bienes.ver",
        "bienes.crear",
        "bienes.editar_estado",
        "bienes.vida_util.editar",
        "formularios.ver",
        "formularios.generar",
        "usuarios.gestionar",
        "catalogos.gestionar",
        "auditoria.ver",
        "backup.ejecutar",
    },
    "Almacenista": {
        "bienes.ver",
        "bienes.crear",
        "bienes.editar_estado",
        "formularios.ver",
        "formularios.generar",
    },
    "Consulta": {
        "bienes.ver",
        "formularios.ver",
    },
}


class SesionError(Exception):
    """Error relacionado con la sesión de usuario."""


class Session:
    """Singleton que mantiene el estado de la sesión activa.

    Uso típico::

        ok = Session.login("admin", "admin123")
        if ok:
            s = Session.get_instance()
            print(s.usuario_actual["nombre"])

        Session.logout()
    """

    _instance: Session | None = None
    _lock = threading.Lock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------
    def __new__(cls) -> "Session":
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._reset()
                cls._instance = obj
            return cls._instance

    def _reset(self) -> None:
        """Limpia todos los datos de sesión."""
        self._usuario: dict[str, Any] | None = None
        self._perfil: str | None = None
        self._tiempo_inicio: datetime | None = None
        self._ultimo_actividad: datetime | None = None
        self._activa: bool = False

    @classmethod
    def get_instance(cls) -> "Session":
        """Retorna la instancia singleton (la crea si no existe)."""
        return cls()

    # ------------------------------------------------------------------
    # Propiedades de solo lectura
    # ------------------------------------------------------------------
    @property
    def usuario_actual(self) -> dict[str, Any] | None:
        """Diccionario completo del usuario autenticado."""
        return self._usuario

    @property
    def perfil(self) -> str | None:
        """Perfil del usuario: 'Administrador', 'Almacenista' o 'Consulta'."""
        return self._perfil

    @property
    def tiempo_inicio(self) -> datetime | None:
        """Fecha/hora en que se inició la sesión."""
        return self._tiempo_inicio

    @property
    def esta_activa(self) -> bool:
        """True si hay una sesión activa."""
        return self._activa

    @property
    def usuario_id(self) -> int | None:
        """ID del usuario autenticado."""
        if self._usuario:
            return self._usuario.get("id")
        return None

    # ------------------------------------------------------------------
    # Login / Logout
    # ------------------------------------------------------------------
    @classmethod
    def login(cls, username: str, password: str) -> bool:
        """Autentica al usuario contra la BD usando bcrypt.

        Parameters
        ----------
        username : str
            Nombre de usuario.
        password : str
            Contraseña en texto plano (se compara con el hash bcrypt).

        Returns
        -------
        bool
            True si las credenciales son correctas y el usuario está activo.
        """
        db = DBConnection()
        try:
            with db.get_cursor() as cur:
                cur.execute(
                    """
                    SELECT id, nombre, apellido, cargo, username,
                           password_hash, perfil, activo
                      FROM usuario
                     WHERE username = %s
                    """,
                    (username.strip(),),
                )
                row = cur.fetchone()
        except Exception:
            return False

        if row is None:
            return False

        cols = ["id", "nombre", "apellido", "cargo", "username",
                "password_hash", "perfil", "activo"]
        usuario = dict(zip(cols, row))

        if not usuario["activo"]:
            return False

        password_hash = usuario["password_hash"]
        if isinstance(password_hash, memoryview):
            password_hash = bytes(password_hash)
        if isinstance(password_hash, str):
            password_hash = password_hash.encode("utf-8")

        try:
            if not bcrypt.checkpw(password.encode("utf-8"), password_hash):
                return False
        except Exception:
            return False

        # Actualizar último acceso
        try:
            with db.get_cursor() as cur:
                cur.execute(
                    "UPDATE usuario SET ultimo_acceso = NOW() WHERE id = %s",
                    (usuario["id"],),
                )
        except Exception:
            pass

        # Establecer sesión
        session = cls.get_instance()
        with cls._lock:
            session._usuario = usuario
            session._perfil = usuario["perfil"]
            session._tiempo_inicio = datetime.now()
            session._ultimo_actividad = datetime.now()
            session._activa = True

        return True

    @classmethod
    def logout(cls) -> None:
        """Cierra la sesión activa."""
        instance = cls._instance
        if instance is not None:
            with cls._lock:
                instance._reset()

    # ------------------------------------------------------------------
    # Inactividad (NF-05)
    # ------------------------------------------------------------------
    def verificar_inactividad(self) -> bool:
        """Comprueba si la sesión expiró por inactividad.

        Returns
        -------
        bool
            True si la sesión debe cerrarse (≥ TIMEOUT_MINUTOS sin actividad).
        """
        if not self._activa or self._ultimo_actividad is None:
            return False
        delta = datetime.now() - self._ultimo_actividad
        return delta >= timedelta(minutes=TIMEOUT_MINUTOS)

    def refrescar_actividad(self) -> None:
        """Actualiza el timestamp de última actividad.

        Llamar en cada interacción del usuario (click, keystroke).
        """
        if self._activa:
            self._ultimo_actividad = datetime.now()

    # ------------------------------------------------------------------
    # Permisos (RN-10, RN-11)
    # ------------------------------------------------------------------
    def tiene_permiso(self, accion: str) -> bool:
        """Verifica si el usuario activo tiene permiso para la acción.

        Parameters
        ----------
        accion : str
            Identificador de la acción, p.ej. ``'bienes.crear'``.

        Returns
        -------
        bool
            True si el perfil tiene el permiso.
        """
        if not self._activa or self._perfil is None:
            return False
        return accion in _PERMISOS.get(self._perfil, set())

    # ------------------------------------------------------------------
    # Representación
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        if not self._activa:
            return "<Session: inactiva>"
        return (
            f"<Session: usuario={self._usuario.get('username')} "  # type: ignore[union-attr]
            f"perfil={self._perfil} "
            f"inicio={self._tiempo_inicio}>"
        )
