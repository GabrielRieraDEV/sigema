"""
bm2_movimientos.py — Generador PDF del formulario BM-2.

BM-2: Relación del Movimiento de Bienes Muebles (GOB-900-FM-085/15)
Incluye bloque Origen/Destino, campo Concepto destacado, y tabla
con 5 columnas.
"""

from __future__ import annotations

from typing import Any

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

from src.reports.bm_base import (
    BMBase, USABLE_WIDTH, MESES, COLOR_BORDER, COLOR_HIGHLIGHT,
)


class BM2Movimientos(BMBase):
    """Genera el formulario BM-2: Relación de Movimientos."""

    TIPO = "BM-2"
    TITULO = "RELACIÓN DEL MOVIMIENTO DE\nBIENES MUEBLES (BM-2)"
    CODIGO_GOB = "GOB-900-FM-085/15"
    FECHA_VIGENCIA = "11/07/2025"
    ACTUALIZACION = "04"

    COL_WIDTHS = [
        USABLE_WIDTH * 0.15,  # Clasificación / Código
        USABLE_WIDTH * 0.15,  # N° Identificación
        USABLE_WIDTH * 0.35,  # Descripción
        USABLE_WIDTH * 0.17,  # Precio Unitario
        USABLE_WIDTH * 0.18,  # Valor Total
    ]

    def generar(
        self,
        buffer,
        movimientos: list[dict[str, Any]],
        depto: dict[str, Any],
        mes: int,
        anio: int,
        concepto: str | None = None,
    ) -> None:
        """Genera el PDF del BM-2.

        Parameters
        ----------
        movimientos : list[dict]
            Movimientos del período.
        depto : dict
            Departamento.
        mes, anio : int
            Período del reporte.
        concepto : str | None
            'Incorporación', 'Desincorporación' o None (ambos).
        """
        self._crear_estilos()
        doc = self.crear_documento(buffer)
        elements = []

        # Encabezado
        elements.extend(self.crear_encabezado(
            self.TIPO, self.TITULO, self.CODIGO_GOB,
            self.FECHA_VIGENCIA, self.ACTUALIZACION,
        ))

        # Bloque de identificación
        elements.extend(self.crear_bloque_identificacion(depto))

        # Bloque Origen / Destino
        elements.extend(self._crear_bloque_origen_destino(
            movimientos, depto
        ))

        # Concepto destacado
        concepto_texto = concepto or "Incorporación / Desincorporación"
        periodo_texto = f"{MESES[mes]} {anio}"

        concepto_data = [[
            Paragraph(
                f"<b>Concepto:</b> "
                f"<font color='#{COLOR_HIGHLIGHT.hexval()[2:]}'>"
                f"<b>{concepto_texto}</b></font>",
                self.style_body,
            ),
            Paragraph(
                f"<b>Período:</b> {periodo_texto}",
                self.style_body,
            ),
        ]]
        concepto_table = Table(
            concepto_data,
            colWidths=[USABLE_WIDTH * 0.55, USABLE_WIDTH * 0.45],
        )
        concepto_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
        ]))
        elements.append(concepto_table)
        elements.append(Spacer(1, 4 * mm))

        # Tabla de datos
        headers = [
            "CLASIFICACIÓN\n/ CÓDIGO",
            "NÚMERO DE\nIDENTIFICACIÓN",
            "DESCRIPCIÓN DE\nLOS BIENES",
            "PRECIO\nUNITARIO",
            "VALOR\nTOTAL",
        ]

        data = []
        total_unitario = 0
        total_valor = 0

        for mov in movimientos:
            p_unit = float(mov.get("precio_unitario", 0))
            v_total = float(mov.get("valor_total", 0))
            total_unitario += p_unit
            total_valor += v_total

            row = [
                Paragraph(
                    f"{mov.get('clasificacion', '')}<br/>"
                    f"<font size='6'>{mov.get('codigo', '')}</font>",
                    self.style_body_center,
                ),
                Paragraph(
                    str(mov.get("numero_identificacion", "")),
                    self.style_body_center,
                ),
                Paragraph(
                    str(mov.get("descripcion", "")),
                    self.style_body,
                ),
                Paragraph(
                    self.formato_moneda(p_unit),
                    self.style_body_right,
                ),
                Paragraph(
                    self.formato_moneda(v_total),
                    self.style_body_right,
                ),
            ]
            data.append(row)

        fila_totales = [
            Paragraph("<b>TOTAL</b>", self.style_total),
            "",
            Paragraph("------------->", self.style_total),
            Paragraph(
                f"<b>{self.formato_moneda(total_unitario)}</b>",
                self.style_body_right,
            ),
            Paragraph(
                f"<b>{self.formato_moneda(total_valor)}</b>",
                self.style_body_right,
            ),
        ]

        tabla = self.crear_tabla_datos(
            headers, data, self.COL_WIDTHS,
            incluir_totales=True,
            fila_totales=fila_totales,
        )
        elements.append(tabla)

        # Firmas
        elements.extend(
            self.crear_firma("Jefe de la Unidad de Trabajo")
        )
        elements.extend(
            self.crear_firma("Dirección de Administración")
        )

        doc.build(elements)

    def _crear_bloque_origen_destino(
        self,
        movimientos: list[dict[str, Any]],
        depto: dict[str, Any],
    ) -> list:
        """Crea el bloque de Origen/Destino específico del BM-2."""
        # Usar los datos del primer movimiento como referencia
        primer = movimientos[0] if movimientos else {}
        origen = primer.get("origen_nombre", depto.get("nombre", ""))
        destino = primer.get("destino_nombre", depto.get("nombre", ""))

        od_data = [
            [
                Paragraph("<b>Origen:</b>", self.style_small),
                Paragraph(str(origen), self.style_body),
                Paragraph("<b>Destino:</b>", self.style_small),
                Paragraph(str(destino), self.style_body),
            ],
        ]
        od_table = Table(
            od_data,
            colWidths=[
                USABLE_WIDTH * 0.10, USABLE_WIDTH * 0.40,
                USABLE_WIDTH * 0.10, USABLE_WIDTH * 0.40,
            ],
        )
        od_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, COLOR_BORDER),
        ]))

        return [od_table, Spacer(1, 3 * mm)]
