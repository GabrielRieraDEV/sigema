"""
auditoria.py — Decorador y utilidades de auditoría automática.

El decorador @auditar(accion, tabla) intercepta métodos de repositorio
que mutan datos y registra automáticamente en la tabla `auditoria`:
  - usuario_id (leído del Session singleton)
  - tabla_afectada
  - accion
  - registro_id
  - datos_antes / datos_despues (JSON)
  - fecha_hora (AUTO por PostgreSQL)

El log nunca puede borrarse ni modificarse (RN-12, §4.4).
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def auditar(accion: str, tabla: str):
    """Decorador de auditoría automática para métodos de repositorio.

    Parámetros
    ----------
    accion : str
        Descripción de la acción, p.ej. ``'CREAR'``, ``'ACTUALIZAR'``,
        ``'CAMBIAR_ESTADO'``.
    tabla : str
        Nombre de la tabla afectada, p.ej. ``'bien'``, ``'usuario'``.

    Uso
    ---
    En un repositorio::

        @auditar("CREAR", "bien")
        def crear(self, bien: dict) -> int:
            ...

    El decorador:
      1. Obtiene el ``usuario_id`` del singleton ``Session``.
      2. Ejecuta el método original.
      3. Inserta en ``auditoria`` usando ``AuditoriaRepository``.

    Si el método falla, la excepción se propaga normalmente.
    El fallo de auditoría NO interrumpe la operación (se loguea y continúa).

    Compatibilidad
    --------------
    - Para métodos que retornan el id del registro nuevo (INSERT → int):
      se registra como ``registro_id``.
    - Para UPDATE/DELETE que retornan bool: ``registro_id`` se infiere del
      primer argumento posicional entero después de ``self``.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Importaciones tardías para evitar ciclos de importación
            from src.core.auth import Session
            from src.db.auditoria_repository import AuditoriaRepository
            from src.db.connection import DBConnection

            session = Session.get_instance()
            usuario_id = session.usuario_id

            # Ejecutar la operación principal
            resultado = func(self, *args, **kwargs)

            # Intentar auditar sin interrumpir el flujo
            if usuario_id is not None:
                try:
                    # Inferir registro_id:
                    # - Si el resultado es un int (INSERT RETURNING id) → ese es el id.
                    # - Si el primer argumento posicional es int → es el id del registro.
                    registro_id: int | None = None
                    if isinstance(resultado, int) and resultado > 0:
                        registro_id = resultado
                    elif args and isinstance(args[0], int):
                        registro_id = args[0]

                    db = DBConnection()
                    auditoria_repo = AuditoriaRepository(db)
                    auditoria_repo.registrar(
                        usuario_id=usuario_id,
                        tabla_afectada=tabla,
                        accion=accion,
                        registro_id=registro_id,
                        datos_antes=None,
                        datos_despues=None,
                    )
                except Exception as exc:
                    logger.warning(
                        "Fallo al registrar auditoría [%s/%s]: %s",
                        tabla, accion, exc,
                    )

            return resultado

        return wrapper

    return decorator


def registrar_auditoria(
    usuario_id: int,
    tabla: str,
    accion: str,
    registro_id: int | None = None,
    datos_antes: dict | None = None,
    datos_despues: dict | None = None,
) -> None:
    """Registra una entrada de auditoría de forma manual.

    Usar cuando el decorador ``@auditar`` no sea suficiente,
    por ejemplo en operaciones complejas de servicio donde se
    necesita capturar datos_antes y datos_despues explícitamente.

    Parameters
    ----------
    usuario_id : int
        ID del usuario que realiza la acción.
    tabla : str
        Nombre de la tabla afectada.
    accion : str
        Tipo de acción realizada.
    registro_id : int | None
        PK del registro afectado.
    datos_antes : dict | None
        Estado del registro antes del cambio.
    datos_despues : dict | None
        Estado del registro después del cambio.
    """
    from src.db.auditoria_repository import AuditoriaRepository
    from src.db.connection import DBConnection

    try:
        db = DBConnection()
        repo = AuditoriaRepository(db)
        repo.registrar(
            usuario_id=usuario_id,
            tabla_afectada=tabla,
            accion=accion,
            registro_id=registro_id,
            datos_antes=datos_antes,
            datos_despues=datos_despues,
        )
    except Exception as exc:
        logger.warning("Fallo al registrar auditoría manual [%s/%s]: %s", tabla, accion, exc)
