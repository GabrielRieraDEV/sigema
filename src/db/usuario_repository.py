"""
usuario_repository.py — Repositorio CRUD para la tabla 'usuario'.

Reglas de negocio aplicadas:
- RN-11: Solo el Administrador puede crear/modificar/desactivar usuarios.
  (Esta restricción se verifica en la UI y en el servicio, no aquí.)
- Los usuarios nunca se eliminan — solo se desactivan (activo = FALSE).
"""

from __future__ import annotations

from typing import Any

from src.db.connection import DBConnection
from src.core.auditoria import auditar


class UsuarioRepository:
    """Acceso a datos de la tabla ``usuario``."""

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
    # SELECT
    # ------------------------------------------------------------------
    def listar_todos(self) -> list[dict[str, Any]]:
        """Retorna todos los usuarios (activos e inactivos)."""
        sql = """
            SELECT id, nombre, apellido, cargo, username,
                   perfil, activo, ultimo_acceso, created_at
              FROM usuario
             ORDER BY apellido, nombre
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql)
            return self._rows_to_list(cur, cur.fetchall())

    def buscar_por_id(self, usuario_id: int) -> dict[str, Any] | None:
        """Busca un usuario por su PK."""
        sql = """
            SELECT id, nombre, apellido, cargo, username,
                   perfil, activo, ultimo_acceso, created_at
              FROM usuario
             WHERE id = %s
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (usuario_id,))
            return self._row_to_dict(cur, cur.fetchone())

    def buscar_por_username(self, username: str) -> dict[str, Any] | None:
        """Busca un usuario por username (sensible a mayúsculas)."""
        sql = """
            SELECT id, nombre, apellido, cargo, username,
                   password_hash, perfil, activo, ultimo_acceso, created_at
              FROM usuario
             WHERE username = %s
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (username,))
            return self._row_to_dict(cur, cur.fetchone())

    def username_existe(self, username: str, excluir_id: int | None = None) -> bool:
        """Verifica si el username ya está en uso.

        Parameters
        ----------
        username : str
            Username a verificar.
        excluir_id : int | None
            Si se proporciona, excluye ese ID (útil al editar un usuario
            existente para no fallar en su propio username).
        """
        if excluir_id is not None:
            sql = "SELECT 1 FROM usuario WHERE username = %s AND id != %s"
            params = (username, excluir_id)
        else:
            sql = "SELECT 1 FROM usuario WHERE username = %s"
            params = (username,)

        with self._db.get_cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() is not None

    # ------------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------------
    @auditar("CREAR", "usuario")
    def crear(self, datos: dict[str, Any]) -> int:
        """Inserta un nuevo usuario y retorna su id.

        Parameters
        ----------
        datos : dict
            Debe contener: nombre, apellido, cargo, username,
            password_hash, perfil, activo.
        """
        sql = """
            INSERT INTO usuario (
                nombre, apellido, cargo, username,
                password_hash, perfil, activo
            ) VALUES (
                %(nombre)s, %(apellido)s, %(cargo)s, %(username)s,
                %(password_hash)s, %(perfil)s, %(activo)s
            )
            RETURNING id
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, datos)
            return cur.fetchone()[0]

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    @auditar("ACTUALIZAR", "usuario")
    def actualizar(self, usuario_id: int, datos: dict[str, Any]) -> bool:
        """Actualiza datos de un usuario existente.

        Parameters
        ----------
        datos : dict
            Puede contener: nombre, apellido, cargo, username,
            perfil, activo. Si incluye password_hash, también se actualiza.
        """
        campos = ["nombre", "apellido", "cargo", "username", "perfil", "activo"]
        if "password_hash" in datos:
            campos.append("password_hash")

        set_clause = ", ".join(f"{c} = %({c})s" for c in campos)
        sql = f"""
            UPDATE usuario
               SET {set_clause}
             WHERE id = %(id)s
        """
        datos["id"] = usuario_id
        with self._db.get_cursor() as cur:
            cur.execute(sql, datos)
            return cur.rowcount == 1

    @auditar("CAMBIAR_ESTADO", "usuario")
    def cambiar_estado(self, usuario_id: int, activo: bool) -> bool:
        """Activa o desactiva un usuario (RN-02 aplicado a usuarios).

        Los usuarios nunca se eliminan de la BD.
        """
        sql = "UPDATE usuario SET activo = %s WHERE id = %s"
        with self._db.get_cursor() as cur:
            cur.execute(sql, (activo, usuario_id))
            return cur.rowcount == 1

    def actualizar_ultimo_acceso(self, usuario_id: int) -> None:
        """Actualiza el campo ultimo_acceso al momento actual."""
        sql = "UPDATE usuario SET ultimo_acceso = NOW() WHERE id = %s"
        with self._db.get_cursor() as cur:
            cur.execute(sql, (usuario_id,))
