"""
movimiento_repository.py — Repositorio para la tabla 'movimiento'.

Registra incorporaciones, desincorporaciones, marcados como faltante
y cambios de departamento de los bienes muebles.
"""

from __future__ import annotations

from typing import Any

from src.db.connection import DBConnection


class MovimientoRepository:
    """Acceso a datos de la tabla ``movimiento``."""

    def __init__(self, db: DBConnection):
        self._db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _rows_to_list(cursor, rows) -> list[dict[str, Any]]:
        """Convierte múltiples filas del cursor en lista de diccionarios."""
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------
    def registrar(
        self,
        bien_id: int,
        tipo: str,
        dept_origen: int | None,
        dept_destino: int | None,
        motivo: str | None,
        responsable: str | None,
        usuario_id: int,
        observaciones: str | None = None,
    ) -> int:
        """Registra un nuevo movimiento y retorna su id.

        Parameters
        ----------
        bien_id : int
            FK al bien afectado.
        tipo : str
            Uno de: 'Incorporación', 'Desincorporación',
            'Marcado como faltante', 'Cambio de departamento destino'.
        dept_origen : int | None
            Departamento de origen (puede ser None en incorporaciones).
        dept_destino : int | None
            Departamento de destino (puede ser None en desincorporaciones).
        motivo : str | None
            Motivo del movimiento.
        responsable : str | None
            Responsable del faltante (solo para tipo 'Marcado como faltante').
        usuario_id : int
            FK al usuario que registra el movimiento.
        observaciones : str | None
            Notas adicionales.

        Returns
        -------
        int
            El ``id`` del movimiento creado.
        """
        sql = """
            INSERT INTO movimiento (
                bien_id, tipo_movimiento,
                departamento_origen, departamento_destino,
                motivo, responsable_faltante,
                registrado_por, observaciones
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (
                bien_id, tipo,
                dept_origen, dept_destino,
                motivo, responsable,
                usuario_id, observaciones,
            ))
            return cur.fetchone()[0]

    def listar_por_bien(self, bien_id: int) -> list[dict[str, Any]]:
        """Lista todos los movimientos de un bien, con nombres de
        departamentos origen/destino y usuario registrante.

        Ordenados del más reciente al más antiguo.
        """
        sql = """
            SELECT
                m.id,
                m.tipo_movimiento,
                d_orig.nombre  AS departamento_origen_nombre,
                d_dest.nombre  AS departamento_destino_nombre,
                m.motivo,
                m.responsable_faltante,
                u.nombre || ' ' || u.apellido AS registrado_por_nombre,
                m.fecha_movimiento,
                m.observaciones
            FROM movimiento m
            LEFT JOIN departamento d_orig ON m.departamento_origen  = d_orig.id
            LEFT JOIN departamento d_dest ON m.departamento_destino = d_dest.id
            JOIN usuario u            ON m.registrado_por       = u.id
            WHERE m.bien_id = %s
            ORDER BY m.fecha_movimiento DESC
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (bien_id,))
            return self._rows_to_list(cur, cur.fetchall())
