"""
formulario_bm_repository.py — Repositorio para la tabla 'formulario_bm'
y queries de datos para la generación de formularios BM-1 al BM-4.

Aplica RN-09: formularios emitidos no se modifican, solo se anulan
con justificación registrada por el Administrador.
"""

from __future__ import annotations

import json
from typing import Any

from src.db.connection import DBConnection


class FormularioBMRepository:
    """Acceso a datos para formularios BM y queries de generación."""

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
    # CRUD — Formularios BM
    # ------------------------------------------------------------------
    def registrar(
        self,
        tipo_bm: str,
        generado_por: int,
        parametros: dict[str, Any] | None = None,
    ) -> int:
        """Inserta un formulario con estado 'Vigente' y retorna su id.

        Parameters
        ----------
        tipo_bm : str
            Uno de 'BM-1', 'BM-2', 'BM-3', 'BM-4'.
        generado_por : int
            FK al usuario que genera el formulario.
        parametros : dict | None
            Parámetros usados para la generación (se guardan como JSONB).
        """
        sql = """
            INSERT INTO formulario_bm (tipo_bm, generado_por, estado, parametros)
            VALUES (%s, %s, 'Vigente', %s)
            RETURNING id
        """
        params_json = json.dumps(parametros) if parametros else None
        with self._db.get_cursor() as cur:
            cur.execute(sql, (tipo_bm, generado_por, params_json))
            return cur.fetchone()[0]

    def anular(
        self,
        formulario_id: int,
        motivo: str,
    ) -> bool:
        """Cambia estado a 'Anulado' con justificación (RN-09).

        Returns
        -------
        bool
            True si se actualizó exactamente una fila.
        """
        sql = """
            UPDATE formulario_bm
               SET estado = 'Anulado',
                   motivo_anulacion = %s
             WHERE id = %s
               AND estado = 'Vigente'
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (motivo, formulario_id))
            return cur.rowcount == 1

    def buscar_por_id(self, formulario_id: int) -> dict[str, Any] | None:
        """Busca un formulario por su id."""
        sql = """
            SELECT f.*,
                   u.nombre || ' ' || u.apellido AS generado_por_nombre
              FROM formulario_bm f
              JOIN usuario u ON f.generado_por = u.id
             WHERE f.id = %s
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (formulario_id,))
            return self._row_to_dict(cur, cur.fetchone())

    def listar_todos(
        self, tipo_bm: str | None = None
    ) -> list[dict[str, Any]]:
        """Lista formularios con JOIN a usuario, filtro opcional por tipo."""
        conditions = []
        params: list[Any] = []

        if tipo_bm:
            conditions.append("f.tipo_bm = %s")
            params.append(tipo_bm)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        sql = f"""
            SELECT f.id, f.tipo_bm, f.fecha_generacion,
                   u.nombre || ' ' || u.apellido AS generado_por_nombre,
                   f.estado, f.motivo_anulacion
              FROM formulario_bm f
              JOIN usuario u ON f.generado_por = u.id
              {where}
             ORDER BY f.fecha_generacion DESC
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, params)
            return self._rows_to_list(cur, cur.fetchall())

    # ------------------------------------------------------------------
    # Queries de datos para generación de formularios
    # ------------------------------------------------------------------
    def obtener_bienes_por_departamento(
        self, departamento_id: int
    ) -> list[dict[str, Any]]:
        """Datos para BM-1: todos los bienes activos de un departamento.

        Retorna clasificación (cuenta_contable), código activo, serial,
        cantidad, descripción, precio unitario y valor total.
        """
        sql = """
            SELECT
                b.cuenta_contable       AS clasificacion,
                b.codigo_activo         AS codigo,
                COALESCE(b.serial_bien, 'N/A') AS numero_identificacion,
                b.num_piezas            AS cantidad,
                b.descripcion           AS nombre_descripcion,
                b.precio_sin_iva        AS valor_unitario,
                (b.precio_sin_iva * b.num_piezas) AS valor_total
            FROM bien b
            WHERE b.departamento_id = %s
              AND b.estado = 'Activo'
            ORDER BY b.cuenta_contable, b.codigo_activo
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (departamento_id,))
            return self._rows_to_list(cur, cur.fetchall())

    def obtener_movimientos_periodo(
        self,
        departamento_id: int,
        fecha_inicio: str,
        fecha_fin: str,
        concepto: str | None = None,
    ) -> list[dict[str, Any]]:
        """Datos para BM-2: movimientos de un período y departamento.

        Parameters
        ----------
        concepto : str | None
            'Incorporación' o 'Desincorporación'.  None = ambos.
        """
        conditions = [
            "m.fecha_movimiento >= %s",
            "m.fecha_movimiento <= %s",
            "(m.departamento_origen = %s OR m.departamento_destino = %s)",
        ]
        params: list[Any] = [fecha_inicio, fecha_fin,
                              departamento_id, departamento_id]

        if concepto:
            conditions.append("m.tipo_movimiento = %s")
            params.append(concepto)
        else:
            conditions.append(
                "m.tipo_movimiento IN ('Incorporación', 'Desincorporación')"
            )

        where = " AND ".join(conditions)

        sql = f"""
            SELECT
                b.cuenta_contable       AS clasificacion,
                b.codigo_activo         AS codigo,
                COALESCE(b.serial_bien, 'N/A') AS numero_identificacion,
                b.descripcion           AS descripcion,
                b.precio_sin_iva        AS precio_unitario,
                (b.precio_sin_iva * b.num_piezas) AS valor_total,
                m.tipo_movimiento       AS concepto,
                d_orig.nombre               AS origen_nombre,
                d_dest.nombre               AS destino_nombre
            FROM movimiento m
            JOIN bien b         ON m.bien_id            = b.id
            LEFT JOIN departamento d_orig ON m.departamento_origen  = d_orig.id
            LEFT JOIN departamento d_dest ON m.departamento_destino = d_dest.id
            WHERE {where}
            ORDER BY m.fecha_movimiento
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, params)
            return self._rows_to_list(cur, cur.fetchall())

    def obtener_faltantes(
        self, departamento_id: int
    ) -> list[dict[str, Any]]:
        """Datos para BM-3: bienes faltantes (Concepto 60) de un depto.

        Incluye el último movimiento de tipo 'Marcado como faltante'
        para obtener el responsable.
        """
        sql = """
            SELECT
                b.cuenta_contable       AS clasificacion,
                b.codigo_activo         AS codigo,
                COALESCE(b.serial_bien, 'N/A') AS numero_identificacion,
                b.descripcion           AS descripcion,
                0                       AS existencia_fisica,
                b.num_piezas            AS registros_contables,
                b.precio_sin_iva        AS valor_unitario,
                b.num_piezas            AS cantidad_faltante,
                (b.precio_sin_iva * b.num_piezas) AS valor_total,
                m.responsable_faltante  AS responsable,
                m.motivo                AS observaciones_faltante
            FROM bien b
            LEFT JOIN LATERAL (
                SELECT mov.responsable_faltante, mov.motivo
                  FROM movimiento mov
                 WHERE mov.bien_id = b.id
                   AND mov.tipo_movimiento = 'Marcado como faltante'
                 ORDER BY mov.fecha_movimiento DESC
                 LIMIT 1
            ) m ON TRUE
            WHERE b.departamento_id = %s
              AND b.estado = 'Faltante'
            ORDER BY b.cuenta_contable, b.codigo_activo
        """
        with self._db.get_cursor() as cur:
            cur.execute(sql, (departamento_id,))
            return self._rows_to_list(cur, cur.fetchall())

    def obtener_resumen_mensual(
        self,
        departamento_id: int,
        mes: int,
        anio: int,
    ) -> dict[str, Any]:
        """Datos para BM-4: resumen de la cuenta de bienes del mes.

        Calcula:
        - existencia_anterior: bienes activos antes del primer día del mes
        - incorporaciones: movimientos de incorporación en el mes
        - desincorporaciones: desincorporaciones (sin Concepto 60) en el mes
        - faltantes_concepto_60: marcados como faltante en el mes
        - existencia_final: cálculo automático (RN-08)
        """
        # Primer y último día del mes
        fecha_inicio = f"{anio}-{mes:02d}-01"
        if mes == 12:
            fecha_fin = f"{anio + 1}-01-01"
        else:
            fecha_fin = f"{anio}-{mes + 1:02d}-01"

        # Existencia anterior: bienes activos del depto creados antes del mes
        sql_anterior = """
            SELECT COUNT(*) AS total
              FROM bien
             WHERE departamento_id = %s
               AND created_at < %s
               AND estado IN ('Activo', 'En desuso', 'Faltante')
        """

        # Incorporaciones en el mes
        sql_incorporaciones = """
            SELECT COUNT(*) AS total
              FROM movimiento
             WHERE departamento_destino = %s
               AND tipo_movimiento = 'Incorporación'
               AND fecha_movimiento >= %s
               AND fecha_movimiento < %s
        """

        # Desincorporaciones en el mes (sin Concepto 60)
        sql_desincorporaciones = """
            SELECT COUNT(*) AS total
              FROM movimiento
             WHERE departamento_origen = %s
               AND tipo_movimiento = 'Desincorporación'
               AND fecha_movimiento >= %s
               AND fecha_movimiento < %s
        """

        # Faltantes Concepto 60 en el mes
        sql_faltantes = """
            SELECT COUNT(*) AS total
              FROM movimiento
             WHERE departamento_origen = %s
               AND tipo_movimiento = 'Marcado como faltante'
               AND fecha_movimiento >= %s
               AND fecha_movimiento < %s
        """

        with self._db.get_cursor() as cur:
            cur.execute(sql_anterior, (departamento_id, fecha_inicio))
            existencia_anterior = cur.fetchone()[0]

            cur.execute(sql_incorporaciones,
                        (departamento_id, fecha_inicio, fecha_fin))
            incorporaciones = cur.fetchone()[0]

            cur.execute(sql_desincorporaciones,
                        (departamento_id, fecha_inicio, fecha_fin))
            desincorporaciones = cur.fetchone()[0]

            cur.execute(sql_faltantes,
                        (departamento_id, fecha_inicio, fecha_fin))
            faltantes = cur.fetchone()[0]

        existencia_final = (
            existencia_anterior
            + incorporaciones
            - desincorporaciones
            - faltantes
        )

        return {
            "existencia_anterior": existencia_anterior,
            "incorporaciones": incorporaciones,
            "desincorporaciones": desincorporaciones,
            "faltantes_concepto_60": faltantes,
            "existencia_final": existencia_final,
        }

    def obtener_departamento(
        self, departamento_id: int
    ) -> dict[str, Any] | None:
        """Obtiene nombre y código de un departamento."""
        sql = "SELECT id, codigo, nombre FROM departamento WHERE id = %s"
        with self._db.get_cursor() as cur:
            cur.execute(sql, (departamento_id,))
            return self._row_to_dict(cur, cur.fetchone())
