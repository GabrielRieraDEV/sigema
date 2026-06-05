"""
auditoria_repository.py — Repositorio para la tabla 'auditoria'.

El log de auditoría es INMUTABLE: solo INSERT y SELECT (RN-12, §4.4).
Ningún método de este repositorio modifica ni elimina registros.
"""

from __future__ import annotations

import json
import socket
from datetime import date, datetime
from typing import Any

from src.db.connection import DBConnection


class AuditoriaRepository:
    """Acceso de solo escritura/lectura a la tabla ``auditoria``."""

    def __init__(self, db: DBConnection):
        self._db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _rows_to_list(cursor, rows) -> list[dict[str, Any]]:
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def _ip_local() -> str:
        """Obtiene la IP local de la máquina cliente."""
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

    # ------------------------------------------------------------------
    # INSERT — registro de auditoría (inmutable)
    # ------------------------------------------------------------------
    def registrar(
        self,
        usuario_id: int,
        tabla_afectada: str,
        accion: str,
        registro_id: int | None = None,
        datos_antes: dict | None = None,
        datos_despues: dict | None = None,
    ) -> None:
        """Inserta un registro de auditoría.

        Este es el ÚNICO método de escritura. No existe actualizar ni
        eliminar para garantizar la integridad del log (RN-12, §4.4).

        Parameters
        ----------
        usuario_id : int
            ID del usuario que realizó la acción.
        tabla_afectada : str
            Nombre de la tabla afectada (p.ej. ``'bien'``).
        accion : str
            Tipo de acción (p.ej. ``'CREAR'``, ``'ACTUALIZAR'``).
        registro_id : int | None
            PK del registro afectado.
        datos_antes : dict | None
            Estado del registro antes del cambio (para UPDATE).
        datos_despues : dict | None
            Estado del registro después del cambio.
        """
        sql = """
            INSERT INTO auditoria (
                usuario_id, tabla_afectada, accion,
                registro_id, datos_antes, datos_despues,
                fecha_hora, ip_origen
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s,
                NOW(), %s
            )
        """

        def _serializable(obj):
            """Convierte tipos no serializables a string."""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return str(obj)

        antes_json = (
            json.dumps(datos_antes, default=_serializable, ensure_ascii=False)
            if datos_antes is not None
            else None
        )
        despues_json = (
            json.dumps(datos_despues, default=_serializable, ensure_ascii=False)
            if datos_despues is not None
            else None
        )

        try:
            with self._db.get_cursor() as cur:
                cur.execute(
                    sql,
                    (
                        usuario_id,
                        tabla_afectada,
                        accion,
                        registro_id,
                        antes_json,
                        despues_json,
                        self._ip_local(),
                    ),
                )
        except Exception:
            # El fallo de auditoría nunca debe interrumpir la operación principal
            pass

    # ------------------------------------------------------------------
    # SELECT — consultas con filtros
    # ------------------------------------------------------------------
    def listar_con_filtros(
        self,
        usuario_id: int | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        accion: str | None = None,
        tabla: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Consulta el log de auditoría con filtros opcionales.

        Parameters
        ----------
        usuario_id : int | None
            Filtrar por usuario específico.
        fecha_desde : date | None
            Fecha de inicio del rango.
        fecha_hasta : date | None
            Fecha de fin del rango (inclusive, hasta las 23:59:59).
        accion : str | None
            Tipo de acción a filtrar.
        tabla : str | None
            Tabla afectada a filtrar.
        limit : int
            Máximo de registros a retornar. Default 500.

        Returns
        -------
        list[dict]
            Registros de auditoría con nombre de usuario resuelto.
        """
        conditions: list[str] = []
        params: list[Any] = []

        if usuario_id is not None:
            conditions.append("a.usuario_id = %s")
            params.append(usuario_id)

        if fecha_desde is not None:
            conditions.append("a.fecha_hora >= %s")
            params.append(datetime.combine(fecha_desde, datetime.min.time()))

        if fecha_hasta is not None:
            conditions.append("a.fecha_hora <= %s")
            params.append(
                datetime.combine(fecha_hasta, datetime.max.time().replace(microsecond=0))
            )

        if accion and accion.strip():
            # Coincidencia exacta: el combo entrega el código de acción.
            conditions.append("a.accion = %s")
            params.append(accion.strip())

        if tabla and tabla.strip():
            conditions.append("a.tabla_afectada ILIKE %s")
            params.append(f"%{tabla.strip()}%")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        sql = f"""
            SELECT
                a.id,
                a.fecha_hora,
                u.username      AS usuario_username,
                u.nombre || ' ' || u.apellido AS usuario_nombre,
                a.accion,
                a.tabla_afectada,
                a.registro_id,
                a.datos_antes,
                a.datos_despues,
                a.ip_origen
            FROM auditoria a
            JOIN usuario u ON a.usuario_id = u.id
            {where}
            ORDER BY a.fecha_hora DESC
            LIMIT %s
        """
        params.append(limit)

        with self._db.get_cursor() as cur:
            cur.execute(sql, params)
            return self._rows_to_list(cur, cur.fetchall())

    def listar_usuarios_auditados(self) -> list[dict[str, Any]]:
        """Retorna lista de usuarios que tienen entradas en auditoría.

        Útil para poblar el combo de filtro en el panel de auditoría.
        """
        sql = """
            SELECT DISTINCT
                u.id,
                u.username,
                u.nombre || ' ' || u.apellido AS nombre_completo
            FROM auditoria a
            JOIN usuario u ON a.usuario_id = u.id
            ORDER BY u.username
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return self._rows_to_list(cur, cur.fetchall())

    def listar_acciones_distintas(self) -> list[str]:
        """Retorna los tipos de acción únicos registrados en auditoría."""
        sql = """
            SELECT DISTINCT accion
            FROM auditoria
            ORDER BY accion
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return [row[0] for row in cur.fetchall()]
