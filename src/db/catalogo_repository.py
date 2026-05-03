"""
catalogo_repository.py — Repositorio para catálogos maestros.

Gestiona tres catálogos del Módulo C (§4.3):
  - departamento: CRUD completo, con soporte de jerarquía (parent_id).
  - categoria: CRUD completo.
  - cuenta_contable: solo activar/desactivar (son cuentas oficiales del Estado).
"""

from __future__ import annotations

from typing import Any

from src.db.connection import DBConnection


class CatalogoRepository:
    """Acceso a las tablas de catálogos maestros."""

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

    # ==================================================================
    # DEPARTAMENTOS
    # ==================================================================
    def listar_departamentos(self, solo_activos: bool = False) -> list[dict[str, Any]]:
        """Retorna todos los departamentos.

        Parameters
        ----------
        solo_activos : bool
            Si True, filtra solo los activos.
        """
        where = "WHERE d.activo = TRUE" if solo_activos else ""
        sql = f"""
            SELECT
                d.id, d.codigo, d.nombre, d.descripcion,
                d.parent_id, d.activo,
                p.nombre AS parent_nombre
            FROM departamento d
            LEFT JOIN departamento p ON d.parent_id = p.id
            {where}
            ORDER BY d.parent_id NULLS FIRST, d.nombre
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return self._rows_to_list(cur, cur.fetchall())

    def buscar_departamento_por_id(self, dept_id: int) -> dict[str, Any] | None:
        """Busca un departamento por su PK."""
        sql = """
            SELECT id, codigo, nombre, descripcion, parent_id, activo
              FROM departamento
             WHERE id = %s
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (dept_id,))
            return self._row_to_dict(cur, cur.fetchone())

    def codigo_departamento_existe(
        self, codigo: str, excluir_id: int | None = None
    ) -> bool:
        """Verifica si el código de departamento ya está en uso."""
        if excluir_id is not None:
            sql = "SELECT 1 FROM departamento WHERE codigo = %s AND id != %s"
            params = (codigo, excluir_id)
        else:
            sql = "SELECT 1 FROM departamento WHERE codigo = %s"
            params = (codigo,)
        with self._db.get_cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() is not None

    def crear_departamento(self, datos: dict[str, Any]) -> int:
        """Inserta un nuevo departamento y retorna su id.

        Parameters
        ----------
        datos : dict
            Debe contener: codigo, nombre.
            Opcionales: descripcion, parent_id, activo.
        """
        datos.setdefault("descripcion", None)
        datos.setdefault("parent_id", None)
        datos.setdefault("activo", True)
        sql = """
            INSERT INTO departamento (codigo, nombre, descripcion, parent_id, activo)
            VALUES (%(codigo)s, %(nombre)s, %(descripcion)s, %(parent_id)s, %(activo)s)
            RETURNING id
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, datos)
            return cur.fetchone()[0]

    def actualizar_departamento(self, dept_id: int, datos: dict[str, Any]) -> bool:
        """Actualiza un departamento existente."""
        sql = """
            UPDATE departamento
               SET codigo = %(codigo)s,
                   nombre = %(nombre)s,
                   descripcion = %(descripcion)s,
                   parent_id = %(parent_id)s
             WHERE id = %(id)s
        """
        datos["id"] = dept_id
        datos.setdefault("descripcion", None)
        datos.setdefault("parent_id", None)
        with self._db.get_cursor() as cur:
            cur.execute(sql, datos)
            return cur.rowcount == 1

    def cambiar_estado_departamento(self, dept_id: int, activo: bool) -> bool:
        """Activa o desactiva un departamento."""
        sql = "UPDATE departamento SET activo = %s WHERE id = %s"
        with self._db.get_cursor() as cur:
            cur.execute(sql, (activo, dept_id))
            return cur.rowcount == 1

    # ==================================================================
    # CATEGORÍAS
    # ==================================================================
    def listar_categorias(self, solo_activas: bool = False) -> list[dict[str, Any]]:
        """Retorna todas las categorías."""
        where = "WHERE activo = TRUE" if solo_activas else ""
        sql = f"""
            SELECT id, nombre, descripcion, activo
              FROM categoria
            {where}
             ORDER BY nombre
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return self._rows_to_list(cur, cur.fetchall())

    def buscar_categoria_por_id(self, cat_id: int) -> dict[str, Any] | None:
        """Busca una categoría por su PK."""
        sql = "SELECT id, nombre, descripcion, activo FROM categoria WHERE id = %s"
        with self._db.get_cursor() as cur:
            cur.execute(sql, (cat_id,))
            return self._row_to_dict(cur, cur.fetchone())

    def nombre_categoria_existe(
        self, nombre: str, excluir_id: int | None = None
    ) -> bool:
        """Verifica si el nombre de categoría ya existe (UNIQUE en BD)."""
        if excluir_id is not None:
            sql = "SELECT 1 FROM categoria WHERE nombre = %s AND id != %s"
            params = (nombre, excluir_id)
        else:
            sql = "SELECT 1 FROM categoria WHERE nombre = %s"
            params = (nombre,)
        with self._db.get_cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() is not None

    def crear_categoria(self, datos: dict[str, Any]) -> int:
        """Inserta una nueva categoría y retorna su id."""
        datos.setdefault("descripcion", None)
        datos.setdefault("activo", True)
        sql = """
            INSERT INTO categoria (nombre, descripcion, activo)
            VALUES (%(nombre)s, %(descripcion)s, %(activo)s)
            RETURNING id
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, datos)
            return cur.fetchone()[0]

    def actualizar_categoria(self, cat_id: int, datos: dict[str, Any]) -> bool:
        """Actualiza nombre y descripción de una categoría."""
        sql = """
            UPDATE categoria
               SET nombre = %(nombre)s,
                   descripcion = %(descripcion)s
             WHERE id = %(id)s
        """
        datos["id"] = cat_id
        datos.setdefault("descripcion", None)
        with self._db.get_cursor() as cur:
            cur.execute(sql, datos)
            return cur.rowcount == 1

    def cambiar_estado_categoria(self, cat_id: int, activo: bool) -> bool:
        """Activa o desactiva una categoría."""
        sql = "UPDATE categoria SET activo = %s WHERE id = %s"
        with self._db.get_cursor() as cur:
            cur.execute(sql, (activo, cat_id))
            return cur.rowcount == 1

    # ==================================================================
    # CUENTAS CONTABLES
    # Solo se permite activar/desactivar (son cuentas oficiales del Estado)
    # ==================================================================
    def listar_cuentas(self, solo_activas: bool = False) -> list[dict[str, Any]]:
        """Retorna todas las cuentas contables."""
        where = "WHERE activo = TRUE" if solo_activas else ""
        sql = f"""
            SELECT codigo, descripcion, activo
              FROM cuenta_contable
            {where}
             ORDER BY codigo
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return self._rows_to_list(cur, cur.fetchall())

    def cambiar_estado_cuenta(self, codigo: str, activo: bool) -> bool:
        """Activa o desactiva una cuenta contable.

        Las cuentas NO se crean ni eliminan desde la aplicación —
        son el plan de cuentas oficial 2-1-214-XX preconfigurado.
        """
        sql = "UPDATE cuenta_contable SET activo = %s WHERE codigo = %s"
        with self._db.get_cursor() as cur:
            cur.execute(sql, (activo, codigo))
            return cur.rowcount == 1
