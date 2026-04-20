"""
bm4_resumen.py — Generador PDF del formulario BM-4.

BM-4: Resumen de la Cuenta de Bienes Muebles (GOB-900-FM-077/15)
Formulario de campos individuales (sin tabla de múltiples filas).
Fórmula automática:
  Existencia Final = Existencia Anterior
                   + Incorporaciones
                   - Desincorporaciones
                   - Faltantes Concepto 60
"""

from __future__ import annotations

from typing import Any

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm
from reportlab.lib import colors

from src.reports.bm_base import (
    BMBase, USABLE_WIDTH, MESES,
    COLOR_BORDER, COLOR_TOTAL_BG, COLOR_HEADER_BG,
)


class BM4Resumen(BMBase):
    """Genera el formulario BM-4: Resumen de la Cuenta de Bienes."""

    TIPO = "BM-4"
    TITULO = "RESUMEN DE LA CUENTA DE\nBIENES MUEBLES (BM-4)"
    CODIGO_GOB = "GOB-900-FM-077/15"
    FECHA_VIGENCIA = "19/08/2025"
    ACTUALIZACION = "04"

    def generar(
        self,
        buffer,
        resumen: dict[str, Any],
        depto: dict[str, Any],
        mes: int,
        anio: int,
    ) -> None:
        """Genera el PDF del BM-4.

        Parameters
        ----------
        resumen : dict
            Datos calculados del resumen mensual.
        depto : dict
            Departamento.
        mes, anio : int
            Mes y año del cierre.
        """
        self._crear_estilos()
        doc = self.crear_documento(buffer)
        elements = []

        # Encabezado
        elements.extend(self.crear_encabezado(
            self.TIPO, self.TITULO, self.CODIGO_GOB,
            self.FECHA_VIGENCIA, self.ACTUALIZACION,
        ))

        # Bloque de identificación con mes
        elements.extend(self._crear_identificacion_bm4(depto, mes, anio))

        # Cuerpo del formulario — campos individuales
        elements.extend(self._crear_cuerpo_resumen(resumen, mes))

        # Firma y sello
        elements.extend(self._crear_bloque_sello_firma())

        doc.build(elements)

    def _crear_identificacion_bm4(
        self,
        depto: dict[str, Any],
        mes: int,
        anio: int,
    ) -> list:
        """Bloque de identificación específico del BM-4."""
        id_data = [
            [
                Paragraph("<b>Estado:</b>", self.style_small),
                Paragraph("Bolívar", self.style_body),
                Paragraph("<b>Municipio:</b>", self.style_small),
                Paragraph("Heres", self.style_body),
            ],
            [
                Paragraph(
                    "<b>Correspondiente al mes de:</b>",
                    self.style_small,
                ),
                Paragraph(
                    f"<b>{MESES[mes]}</b>", self.style_body,
                ),
                Paragraph("<b>del:</b>", self.style_small),
                Paragraph(str(anio), self.style_body),
            ],
            [
                Paragraph("<b>Unidad de Trabajo:</b>", self.style_small),
                Paragraph(depto.get("nombre", ""), self.style_body),
                Paragraph("<b>Código:</b>", self.style_small),
                Paragraph(depto.get("codigo", ""), self.style_body),
            ],
        ]

        id_table = Table(
            id_data,
            colWidths=[
                USABLE_WIDTH * 0.22, USABLE_WIDTH * 0.33,
                USABLE_WIDTH * 0.15, USABLE_WIDTH * 0.30,
            ],
        )
        id_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, COLOR_BORDER),
        ]))

        return [id_table, Spacer(1, 8 * mm)]

    def _crear_cuerpo_resumen(
        self,
        resumen: dict[str, Any],
        mes: int,
    ) -> list:
        """Crea el cuerpo del formulario con los campos de resumen."""
        existencia_ant = resumen.get("existencia_anterior", 0)
        incorporaciones = resumen.get("incorporaciones", 0)
        desincorporaciones = resumen.get("desincorporaciones", 0)
        faltantes = resumen.get("faltantes_concepto_60", 0)
        existencia_final = resumen.get("existencia_final", 0)

        mes_nombre = MESES[mes]

        filas = [
            # Existencia anterior
            [
                Paragraph(
                    "<b>Existencia Anterior</b>",
                    self.style_body,
                ),
                Paragraph("------------->", self.style_body_right),
                Paragraph(
                    f"<b>{existencia_ant}</b>",
                    self.style_body_center,
                ),
            ],
            # Espaciador
            ["", "", ""],
            # Incorporaciones
            [
                Paragraph(
                    f"<b>Incorporaciones en el mes de {mes_nombre}</b>"
                    "<br/>de la Cuenta por todos los conceptos",
                    self.style_body,
                ),
                Paragraph("------------->", self.style_body_right),
                Paragraph(
                    f"<b>{incorporaciones}</b>",
                    self.style_body_center,
                ),
            ],
            # Espaciador
            ["", "", ""],
            # Desincorporaciones
            [
                Paragraph(
                    f"<b>Desincorporaciones en el mes de {mes_nombre}</b>"
                    "<br/>de la cuenta por todos los conceptos",
                    self.style_body,
                ),
                Paragraph("------------->", self.style_body_right),
                Paragraph(
                    f"<b>{desincorporaciones}</b>",
                    self.style_body_center,
                ),
            ],
            # Espaciador
            ["", "", ""],
            # Faltantes Concepto 60
            [
                Paragraph(
                    f"<b>Desincorporaciones en el mes de {mes_nombre}</b>"
                    '<br/>por el 60 "Faltante de Bienes por Investigar"',
                    self.style_body,
                ),
                Paragraph("------------->", self.style_body_right),
                Paragraph(
                    f"<b>{faltantes}</b>",
                    self.style_body_center,
                ),
            ],
            # Espaciador
            ["", "", ""],
            # Existencia Final (destacada)
            [
                Paragraph(
                    "<b>Existencia Final</b>",
                    self.style_body,
                ),
                Paragraph("------------->", self.style_body_right),
                Paragraph(
                    f"<b>{existencia_final}</b>",
                    self.style_body_center,
                ),
            ],
        ]

        table = Table(
            filas,
            colWidths=[
                USABLE_WIDTH * 0.55,
                USABLE_WIDTH * 0.20,
                USABLE_WIDTH * 0.25,
            ],
        )

        # Índice de la fila "Existencia Final" (última fila = 8)
        ultima = len(filas) - 1

        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, COLOR_BORDER),
            ("LINEBELOW", (0, 2), (-1, 2), 0.5, COLOR_BORDER),
            ("LINEBELOW", (0, 4), (-1, 4), 0.5, COLOR_BORDER),
            ("LINEBELOW", (0, 6), (-1, 6), 0.5, COLOR_BORDER),
            # Celda valor con borde
            ("BOX", (2, 0), (2, 0), 0.5, COLOR_BORDER),
            ("BOX", (2, 2), (2, 2), 0.5, COLOR_BORDER),
            ("BOX", (2, 4), (2, 4), 0.5, COLOR_BORDER),
            ("BOX", (2, 6), (2, 6), 0.5, COLOR_BORDER),
            # Existencia Final — destacada
            ("BACKGROUND", (0, ultima), (-1, ultima), COLOR_TOTAL_BG),
            ("BOX", (0, ultima), (-1, ultima), 2, COLOR_HEADER_BG),
            ("BOX", (2, ultima), (2, ultima), 2, COLOR_HEADER_BG),
        ]))

        return [table, Spacer(1, 10 * mm)]

    def _crear_bloque_sello_firma(self) -> list:
        """Crea el bloque de sello y firma del BM-4."""
        sello_data = [
            [
                Paragraph(
                    "<b>SELLO DE LA OFICINA:</b>",
                    self.style_body,
                ),
                "",  # Espacio para sello
            ],
        ]
        sello_table = Table(
            sello_data,
            colWidths=[USABLE_WIDTH * 0.35, USABLE_WIDTH * 0.65],
        )
        sello_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (1, 0), (1, 0), 50),  # espacio generoso
            ("BOX", (1, 0), (1, 0), 0.5, COLOR_BORDER),
        ]))

        firma_elements = self.crear_firma(
            "Firma del Jefe Responsable de la Unidad de Trabajo "
            "o Departamento"
        )

        return [sello_table] + firma_elements
