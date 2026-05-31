"""
donacion_repository.py — Repositorio CRUD para la tabla 'donacion'.

Una donación es la incorporación de un bien SIN orden de compra ni
proveedor comercial: en su lugar hay un donante y, opcionalmente, un
acta o documento de donación.

Las donaciones son inmutables una vez registradas (solo lectura desde
la aplicación); por eso este repositorio expone únicamente registrar y
consultas.
"""

from __future__ import annotations

from typing import Any

from src.db.connection import DBConnection
from src.core.auditoria import auditar


class DonacionRepository:
    """Acceso a datos de la tabla ``donacion``."""

    def __init__(self, db: DBConnection):
        self._db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_dict(cursor, row) -> dict[str, Any] | None:
        if row is None:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    @staticmethod
    def _rows_to_list(cursor, rows) -> list[dict[str, Any]]:
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------
    @auditar("CREAR", "donacion")
    def registrar(self, donacion: dict[str, Any]) -> int:
        """Inserta una donación y retorna su id.

        Parameters
        ----------
        donacion : dict
            Debe incluir: bien_id, donante, fecha_donacion.
            Opcionales: tipo_donante, acta_numero, descripcion,
            registrado_por.
        """
        donacion.setdefault("tipo_donante", None)
        donacion.setdefault("acta_numero", None)
        donacion.setdefault("descripcion", None)
        donacion.setdefault("registrado_por", None)
        sql = """
            INSERT INTO donacion (
                bien_id, donante, tipo_donante, acta_numero,
                fecha_donacion, descripcion, registrado_por
            ) VALUES (
                %(bien_id)s, %(donante)s, %(tipo_donante)s, %(acta_numero)s,
                %(fecha_donacion)s, %(descripcion)s, %(registrado_por)s
            )
            RETURNING id
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, donacion)
            return cur.fetchone()[0]

    def buscar_por_bien(self, bien_id: int) -> dict[str, Any] | None:
        """Devuelve la donación asociada a un bien (la más reciente)."""
        sql = """
            SELECT d.*,
                   u.nombre || ' ' || u.apellido AS registrado_por_nombre
              FROM donacion d
              LEFT JOIN usuario u ON d.registrado_por = u.id
             WHERE d.bien_id = %s
             ORDER BY d.id DESC
             LIMIT 1
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (bien_id,))
            return self._row_to_dict(cur, cur.fetchone())

    def listar_todos(
        self,
        donante: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista las donaciones con datos del bien, filtros opcionales.

        Parameters
        ----------
        donante : str | None
            Filtro parcial (ILIKE) por nombre del donante.
        fecha_desde, fecha_hasta : str | None
            Rango de ``fecha_donacion`` (formato 'YYYY-MM-DD').
        """
        conditions: list[str] = []
        params: list[Any] = []

        if donante:
            conditions.append("d.donante ILIKE %s")
            params.append(f"%{donante}%")
        if fecha_desde:
            conditions.append("d.fecha_donacion >= %s")
            params.append(fecha_desde)
        if fecha_hasta:
            conditions.append("d.fecha_donacion <= %s")
            params.append(fecha_hasta)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        sql = f"""
            SELECT
                d.id,
                d.bien_id,
                b.codigo_activo,
                b.descripcion           AS bien_descripcion,
                d.donante,
                d.tipo_donante,
                d.acta_numero,
                d.fecha_donacion,
                d.descripcion,
                u.nombre || ' ' || u.apellido AS registrado_por_nombre,
                d.created_at
            FROM donacion d
            JOIN bien b        ON d.bien_id = b.id
            LEFT JOIN usuario u ON d.registrado_por = u.id
            {where}
            ORDER BY d.fecha_donacion DESC, d.id DESC
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, params)
            return self._rows_to_list(cur, cur.fetchall())
