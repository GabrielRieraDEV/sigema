"""
bien_repository.py — Repositorio CRUD para la tabla 'bien'.

Todas las queries usan parámetros (%s) para prevenir SQL injection.
Los resultados se retornan como diccionarios mapeados desde cursor.description.
"""

from __future__ import annotations

from typing import Any

from src.db.connection import DBConnection


class BienRepository:
    """Acceso a datos de la tabla ``bien`` y catálogos relacionados."""

    def __init__(self, db: DBConnection):
        self._db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_dict(cursor, row) -> dict[str, Any] | None:
        """Convierte una fila del cursor en un diccionario."""
        if row is None:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    @staticmethod
    def _rows_to_list(cursor, rows) -> list[dict[str, Any]]:
        """Convierte múltiples filas del cursor en lista de diccionarios."""
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    # ------------------------------------------------------------------
    # CRUD — Bienes
    # ------------------------------------------------------------------
    def crear(self, bien: dict[str, Any]) -> int:
        """Inserta un nuevo bien y retorna su id.

        Parameters
        ----------
        bien : dict
            Diccionario con las columnas de la tabla ``bien``.
            Debe incluir al menos los campos obligatorios.

        Returns
        -------
        int
            El ``id`` del bien recién creado.
        """
        sql = """
            INSERT INTO bien (
                codigo_activo, codigo_nivel, descripcion,
                categoria_id, marca, modelo, serial_bien, color,
                tipo, num_piezas, orden_compra, fecha_compra,
                precio_sin_iva, moneda, vida_util_meses,
                departamento_id, cuenta_contable, estado,
                observaciones, creado_por
            ) VALUES (
                %(codigo_activo)s, %(codigo_nivel)s, %(descripcion)s,
                %(categoria_id)s, %(marca)s, %(modelo)s, %(serial_bien)s,
                %(color)s, %(tipo)s, %(num_piezas)s, %(orden_compra)s,
                %(fecha_compra)s, %(precio_sin_iva)s, %(moneda)s,
                %(vida_util_meses)s, %(departamento_id)s,
                %(cuenta_contable)s, %(estado)s, %(observaciones)s,
                %(creado_por)s
            )
            RETURNING id
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, bien)
            return cur.fetchone()[0]

    def buscar_por_codigo(self, codigo_activo: str) -> dict[str, Any] | None:
        """Busca un bien por su código activo (único).

        Incluye JOIN a categoría, departamento y cuenta contable para
        obtener nombres descriptivos.
        """
        sql = """
            SELECT
                b.*,
                c.nombre        AS categoria_nombre,
                d.nombre        AS departamento_nombre,
                cc.descripcion  AS cuenta_contable_descripcion
            FROM bien b
            JOIN categoria c       ON b.categoria_id   = c.id
            JOIN departamento d    ON b.departamento_id = d.id
            JOIN cuenta_contable cc ON b.cuenta_contable = cc.codigo
            WHERE b.codigo_activo = %s
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (codigo_activo,))
            return self._row_to_dict(cur, cur.fetchone())

    def buscar_por_id(self, bien_id: int) -> dict[str, Any] | None:
        """Busca un bien por su id (PK).

        Incluye JOIN a catálogos para nombres descriptivos.
        """
        sql = """
            SELECT
                b.*,
                c.nombre        AS categoria_nombre,
                d.nombre        AS departamento_nombre,
                cc.descripcion  AS cuenta_contable_descripcion
            FROM bien b
            JOIN categoria c       ON b.categoria_id   = c.id
            JOIN departamento d    ON b.departamento_id = d.id
            JOIN cuenta_contable cc ON b.cuenta_contable = cc.codigo
            WHERE b.id = %s
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (bien_id,))
            return self._row_to_dict(cur, cur.fetchone())

    def buscar_por_filtros(
        self,
        codigo: str | None = None,
        descripcion: str | None = None,
        departamento_id: int | None = None,
        estado: str | None = None,
    ) -> list[dict[str, Any]]:
        """Búsqueda dinámica con filtros opcionales.

        Los filtros de texto usan ILIKE para búsqueda parcial
        case-insensitive.
        """
        conditions: list[str] = []
        params: list[Any] = []

        if codigo:
            conditions.append("b.codigo_activo ILIKE %s")
            params.append(f"%{codigo}%")
        if descripcion:
            conditions.append("b.descripcion ILIKE %s")
            params.append(f"%{descripcion}%")
        if departamento_id is not None:
            conditions.append("b.departamento_id = %s")
            params.append(departamento_id)
        if estado:
            conditions.append("b.estado = %s")
            params.append(estado)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        sql = f"""
            SELECT
                b.id, b.codigo_activo, b.descripcion,
                c.nombre        AS categoria_nombre,
                d.nombre        AS departamento_nombre,
                b.estado, b.created_at
            FROM bien b
            JOIN categoria c    ON b.categoria_id   = c.id
            JOIN departamento d ON b.departamento_id = d.id
            {where}
            ORDER BY b.created_at DESC
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, params)
            return self._rows_to_list(cur, cur.fetchall())

    def actualizar_estado(
        self,
        bien_id: int,
        estado: str,
        motivo: str,
        usuario_id: int,
    ) -> bool:
        """Actualiza el estado de un bien.

        No elimina registros (RN-02). Solo modifica la columna ``estado``.

        Returns
        -------
        bool
            True si se actualizó exactamente una fila.
        """
        sql = """
            UPDATE bien
               SET estado = %s
             WHERE id = %s
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (estado, bien_id))
            return cur.rowcount == 1

    def listar_por_departamento(
        self, departamento_id: int
    ) -> list[dict[str, Any]]:
        """Lista todos los bienes de un departamento."""
        sql = """
            SELECT
                b.id, b.codigo_activo, b.descripcion,
                c.nombre        AS categoria_nombre,
                d.nombre        AS departamento_nombre,
                b.estado, b.created_at
            FROM bien b
            JOIN categoria c    ON b.categoria_id   = c.id
            JOIN departamento d ON b.departamento_id = d.id
            WHERE b.departamento_id = %s
            ORDER BY b.codigo_activo
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (departamento_id,))
            return self._rows_to_list(cur, cur.fetchall())

    # ------------------------------------------------------------------
    # Catálogos auxiliares (para poblar combos en la UI)
    # ------------------------------------------------------------------
    def listar_categorias(self) -> list[dict[str, Any]]:
        """Retorna todas las categorías activas."""
        sql = "SELECT id, nombre FROM categoria WHERE activo = TRUE ORDER BY nombre"
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return self._rows_to_list(cur, cur.fetchall())

    def listar_departamentos(self) -> list[dict[str, Any]]:
        """Retorna todos los departamentos activos con su jerarquía."""
        sql = "SELECT id, nombre, parent_id FROM departamento WHERE activo = TRUE ORDER BY parent_id NULLS FIRST, nombre"
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return self._rows_to_list(cur, cur.fetchall())

    def obtener_siguiente_codigo_activo(self) -> str:
        """Obtiene el siguiente código correlativo de bien (ej. ACT-0016)."""
        sql = "SELECT codigo_activo FROM bien ORDER BY id DESC LIMIT 1"
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            if not row or not row[0]:
                return "ACT-0001"
            
            last_code = row[0]
            parts = last_code.split("-")
            if len(parts) == 2 and parts[1].isdigit():
                next_num = int(parts[1]) + 1
                return f"{parts[0]}-{next_num:04d}"
            
            return "ACT-0001"

    def listar_cuentas_contables(self) -> list[dict[str, Any]]:
        """Retorna todas las cuentas contables activas."""
        sql = """
            SELECT codigo, descripcion
              FROM cuenta_contable
             WHERE activo = TRUE
             ORDER BY codigo
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return self._rows_to_list(cur, cur.fetchall())
