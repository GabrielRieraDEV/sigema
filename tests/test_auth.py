"""
test_auth.py — Pruebas de autenticación, sesión e inactividad.

Cubre:
- Login correcto / incorrecto / usuario inexistente / usuario inactivo.
- Cierre de sesión (logout).
- Expiración por inactividad (NF-05, 30 min).
- Refresco de actividad.
- Singleton de sesión.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.core.auth import Session, TIMEOUT_MINUTOS


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def test_login_correcto(crear_usuario):
    """Credenciales válidas de un usuario activo inician la sesión."""
    crear_usuario("jperez", "clave_segura", "Almacenista",
                  nombre="Juan", apellido="Pérez")

    assert Session.login("jperez", "clave_segura") is True

    s = Session.get_instance()
    assert s.esta_activa is True
    assert s.perfil == "Almacenista"
    assert s.usuario_actual["username"] == "jperez"
    assert s.usuario_actual["nombre"] == "Juan"
    assert s.usuario_id is not None
    assert s.tiempo_inicio is not None


def test_login_password_incorrecta(crear_usuario):
    """Una contraseña incorrecta no inicia sesión."""
    crear_usuario("jperez", "clave_segura", "Consulta")

    assert Session.login("jperez", "clave_equivocada") is False
    assert Session.get_instance().esta_activa is False


def test_login_usuario_inexistente():
    """Un username que no existe no inicia sesión."""
    assert Session.login("fantasma", "lo_que_sea") is False
    assert Session.get_instance().esta_activa is False


def test_login_usuario_inactivo(crear_usuario):
    """Un usuario desactivado (activo = FALSE) no puede iniciar sesión."""
    crear_usuario("inactivo", "clave_segura", "Consulta", activo=False)

    assert Session.login("inactivo", "clave_segura") is False
    assert Session.get_instance().esta_activa is False


def test_login_recorta_espacios(crear_usuario):
    """El username se normaliza con strip()."""
    crear_usuario("jperez", "clave_segura", "Consulta")

    assert Session.login("  jperez  ", "clave_segura") is True


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
def test_logout_limpia_sesion(crear_usuario):
    """logout() desactiva la sesión y limpia el usuario."""
    crear_usuario("jperez", "clave_segura", "Administrador")
    Session.login("jperez", "clave_segura")
    assert Session.get_instance().esta_activa is True

    Session.logout()

    s = Session.get_instance()
    assert s.esta_activa is False
    assert s.usuario_actual is None
    assert s.perfil is None
    assert s.usuario_id is None


# ---------------------------------------------------------------------------
# Inactividad (NF-05)
# ---------------------------------------------------------------------------
def test_inactividad_no_expira_recien_iniciada(crear_usuario):
    """Una sesión recién iniciada no se considera expirada."""
    crear_usuario("jperez", "clave_segura", "Consulta")
    Session.login("jperez", "clave_segura")

    assert Session.get_instance().verificar_inactividad() is False


def test_inactividad_expira_pasado_el_timeout(crear_usuario):
    """Tras superar TIMEOUT_MINUTOS sin actividad, la sesión expira."""
    crear_usuario("jperez", "clave_segura", "Consulta")
    Session.login("jperez", "clave_segura")

    s = Session.get_instance()
    # Simular inactividad: última actividad muy en el pasado.
    s._ultimo_actividad = datetime.now() - timedelta(
        minutes=TIMEOUT_MINUTOS + 1
    )

    assert s.verificar_inactividad() is True


def test_refrescar_actividad_evita_expiracion(crear_usuario):
    """refrescar_actividad() reinicia el contador de inactividad."""
    crear_usuario("jperez", "clave_segura", "Consulta")
    Session.login("jperez", "clave_segura")

    s = Session.get_instance()
    s._ultimo_actividad = datetime.now() - timedelta(
        minutes=TIMEOUT_MINUTOS + 1
    )
    assert s.verificar_inactividad() is True

    s.refrescar_actividad()
    assert s.verificar_inactividad() is False


def test_inactividad_sin_sesion_no_expira():
    """Sin sesión activa, verificar_inactividad() devuelve False."""
    Session.logout()
    assert Session.get_instance().verificar_inactividad() is False


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
def test_session_es_singleton():
    """get_instance() siempre devuelve la misma instancia."""
    assert Session.get_instance() is Session.get_instance()
    assert Session() is Session.get_instance()
