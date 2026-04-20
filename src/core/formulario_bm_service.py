"""
formulario_bm_service.py — Lógica de negocio para el Módulo B (Formularios BM).

Orquesta la generación de formularios BM-1 al BM-4, aplicando:
- RN-07: códigos GOB-900-FM oficiales
- RN-08: BM-4 solo al cierre de mes
- RN-09: formularios emitidos no se modifican, solo se anulan
"""

from __future__ import annotations

import io
from datetime import date
from typing import Any

from src.db.formulario_bm_repository import FormularioBMRepository
from src.reports.bm1_inventario import BM1Inventario
from src.reports.bm2_movimientos import BM2Movimientos
from src.reports.bm3_faltantes import BM3Faltantes
from src.reports.bm4_resumen import BM4Resumen


class FormularioBMService:
    """Servicio que orquesta la generación y gestión de formularios BM."""

    def __init__(self, formulario_repo: FormularioBMRepository):
        self._repo = formulario_repo

    # ------------------------------------------------------------------
    # Generación de formularios
    # ------------------------------------------------------------------
    def generar_bm1(
        self,
        departamento_id: int,
        usuario_id: int,
    ) -> tuple[bool, str, bytes | None]:
        """Genera BM-1: Inventario de Bienes Muebles.

        Returns
        -------
        tuple[bool, str, bytes | None]
            (éxito, mensaje, bytes_del_pdf)
        """
        try:
            # Obtener datos
            bienes = self._repo.obtener_bienes_por_departamento(
                departamento_id
            )
            depto = self._repo.obtener_departamento(departamento_id)
            if depto is None:
                return (False, "Departamento no encontrado.", None)

            if not bienes:
                return (
                    False,
                    "No hay bienes activos en este departamento para "
                    "generar el BM-1.",
                    None,
                )

            # Generar PDF
            buffer = io.BytesIO()
            generador = BM1Inventario()
            generador.generar(buffer, bienes, depto)
            pdf_bytes = buffer.getvalue()

            # Registrar en BD (RN-09)
            parametros = {
                "departamento_id": departamento_id,
                "departamento_nombre": depto["nombre"],
                "total_bienes": len(bienes),
            }
            self._repo.registrar("BM-1", usuario_id, parametros)

            return (True, "BM-1 generado exitosamente.", pdf_bytes)

        except Exception as exc:
            return (False, f"Error al generar BM-1: {exc}", None)

    def generar_bm2(
        self,
        departamento_id: int,
        mes: int,
        anio: int,
        concepto: str | None,
        usuario_id: int,
    ) -> tuple[bool, str, bytes | None]:
        """Genera BM-2: Relación de Movimiento de Bienes Muebles."""
        try:
            depto = self._repo.obtener_departamento(departamento_id)
            if depto is None:
                return (False, "Departamento no encontrado.", None)

            fecha_inicio = f"{anio}-{mes:02d}-01"
            if mes == 12:
                fecha_fin = f"{anio + 1}-01-01"
            else:
                fecha_fin = f"{anio}-{mes + 1:02d}-01"

            movimientos = self._repo.obtener_movimientos_periodo(
                departamento_id, fecha_inicio, fecha_fin, concepto
            )

            if not movimientos:
                return (
                    False,
                    "No hay movimientos en el período seleccionado.",
                    None,
                )

            buffer = io.BytesIO()
            generador = BM2Movimientos()
            generador.generar(buffer, movimientos, depto, mes, anio, concepto)
            pdf_bytes = buffer.getvalue()

            parametros = {
                "departamento_id": departamento_id,
                "departamento_nombre": depto["nombre"],
                "mes": mes,
                "anio": anio,
                "concepto": concepto,
                "total_movimientos": len(movimientos),
            }
            self._repo.registrar("BM-2", usuario_id, parametros)

            return (True, "BM-2 generado exitosamente.", pdf_bytes)

        except Exception as exc:
            return (False, f"Error al generar BM-2: {exc}", None)

    def generar_bm3(
        self,
        departamento_id: int,
        usuario_id: int,
    ) -> tuple[bool, str, bytes | None]:
        """Genera BM-3: Bienes Muebles Faltantes (Concepto 60)."""
        try:
            depto = self._repo.obtener_departamento(departamento_id)
            if depto is None:
                return (False, "Departamento no encontrado.", None)

            faltantes = self._repo.obtener_faltantes(departamento_id)

            if not faltantes:
                return (
                    False,
                    "No hay bienes faltantes (Concepto 60) en este "
                    "departamento.",
                    None,
                )

            buffer = io.BytesIO()
            generador = BM3Faltantes()
            generador.generar(buffer, faltantes, depto)
            pdf_bytes = buffer.getvalue()

            parametros = {
                "departamento_id": departamento_id,
                "departamento_nombre": depto["nombre"],
                "total_faltantes": len(faltantes),
            }
            self._repo.registrar("BM-3", usuario_id, parametros)

            return (True, "BM-3 generado exitosamente.", pdf_bytes)

        except Exception as exc:
            return (False, f"Error al generar BM-3: {exc}", None)

    def generar_bm4(
        self,
        departamento_id: int,
        mes: int,
        anio: int,
        usuario_id: int,
    ) -> tuple[bool, str, bytes | None]:
        """Genera BM-4: Resumen de la Cuenta de Bienes Muebles.

        Aplica RN-08: solo se genera al cierre de mes.
        """
        try:
            depto = self._repo.obtener_departamento(departamento_id)
            if depto is None:
                return (False, "Departamento no encontrado.", None)

            resumen = self._repo.obtener_resumen_mensual(
                departamento_id, mes, anio
            )

            buffer = io.BytesIO()
            generador = BM4Resumen()
            generador.generar(buffer, resumen, depto, mes, anio)
            pdf_bytes = buffer.getvalue()

            parametros = {
                "departamento_id": departamento_id,
                "departamento_nombre": depto["nombre"],
                "mes": mes,
                "anio": anio,
                **resumen,
            }
            self._repo.registrar("BM-4", usuario_id, parametros)

            return (True, "BM-4 generado exitosamente.", pdf_bytes)

        except Exception as exc:
            return (False, f"Error al generar BM-4: {exc}", None)

    # ------------------------------------------------------------------
    # Gestión de formularios emitidos (RN-09)
    # ------------------------------------------------------------------
    def anular_formulario(
        self,
        formulario_id: int,
        motivo: str,
    ) -> tuple[bool, str]:
        """Anula un formulario emitido con justificación.

        Solo formularios con estado 'Vigente' pueden anularse.
        """
        if not motivo or not motivo.strip():
            return (
                False,
                "Debe indicar el motivo de anulación (RN-09).",
            )

        try:
            ok = self._repo.anular(formulario_id, motivo.strip())
            if ok:
                return (True, "Formulario anulado exitosamente.")
            else:
                return (
                    False,
                    "No se pudo anular el formulario. "
                    "Puede que ya esté anulado.",
                )
        except Exception as exc:
            return (False, f"Error al anular formulario: {exc}")

    def listar_formularios(
        self, tipo_bm: str | None = None
    ) -> list[dict[str, Any]]:
        """Lista historial de formularios emitidos."""
        return self._repo.listar_todos(tipo_bm)

    # ------------------------------------------------------------------
    # Catálogos (para poblar combos en la UI)
    # ------------------------------------------------------------------
    def obtener_departamentos(self) -> list[dict[str, Any]]:
        """Retorna departamentos activos para combo."""
        sql = """
            SELECT id, nombre
              FROM departamento
             WHERE activo = TRUE
             ORDER BY nombre
        """
        with self._repo._db.get_cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
