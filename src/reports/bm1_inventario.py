"""
bm1_inventario.py — Generador PDF del formulario BM-1.

BM-1: Inventario de Bienes Muebles (GOB-900-FM-086/15)
Tabla con 6 columnas: Clasificación/Código, N° Identificación,
Cantidad, Nombre y Descripción, Valor Unitario, Valor Total.
"""

from __future__ import annotations

from typing import Any

from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import mm

from src.reports.bm_base import BMBase, USABLE_WIDTH


class BM1Inventario(BMBase):
    """Genera el formulario BM-1: Inventario de Bienes Muebles."""

    # Metadatos del formulario
    TIPO = "BM-1"
    TITULO = "INVENTARIO DE BIENES MUEBLES (BM-1)"
    CODIGO_GOB = "GOB-900-FM-086/15"
    FECHA_VIGENCIA = "11/07/2025"
    ACTUALIZACION = "05"

    # Anchos de columna (proporcionales al ancho utilizable)
    COL_WIDTHS = [
        USABLE_WIDTH * 0.15,  # Clasificación / Código
        USABLE_WIDTH * 0.15,  # N° Identificación
        USABLE_WIDTH * 0.08,  # Cantidad
        USABLE_WIDTH * 0.32,  # Nombre y Descripción
        USABLE_WIDTH * 0.15,  # Valor Unitario
        USABLE_WIDTH * 0.15,  # Valor Total
    ]

    def generar(
        self,
        buffer,
        bienes: list[dict[str, Any]],
        depto: dict[str, Any],
    ) -> None:
        """Genera el PDF del BM-1 y lo escribe en el buffer.

        Parameters
        ----------
        buffer : io.BytesIO
            Buffer donde se escribirá el PDF.
        bienes : list[dict]
            Lista de bienes del departamento (del repository).
        depto : dict
            Datos del departamento.
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

        # Preparar datos de la tabla
        headers = [
            "CLASIFICACIÓN\n/ CÓDIGO",
            "NÚMERO DE\nIDENTIFICACIÓN",
            "CANTIDAD",
            "NOMBRE Y DESCRIPCIÓN\nDE LOS ELEMENTOS",
            "VALOR\nUNITARIO",
            "VALOR\nTOTAL",
        ]

        data = []
        total_unitario = 0
        total_valor = 0

        for bien in bienes:
            valor_unit = float(bien.get("valor_unitario", 0))
            valor_tot = float(bien.get("valor_total", 0))
            total_unitario += valor_unit
            total_valor += valor_tot

            row = [
                Paragraph(
                    f"{bien.get('clasificacion', '')}<br/>"
                    f"<font size='6'>{bien.get('codigo', '')}</font>",
                    self.style_body_center,
                ),
                Paragraph(
                    str(bien.get("numero_identificacion", "")),
                    self.style_body_center,
                ),
                Paragraph(
                    str(bien.get("cantidad", 1)),
                    self.style_body_center,
                ),
                Paragraph(
                    str(bien.get("nombre_descripcion", "")),
                    self.style_body,
                ),
                Paragraph(
                    self.formato_moneda(valor_unit),
                    self.style_body_right,
                ),
                Paragraph(
                    self.formato_moneda(valor_tot),
                    self.style_body_right,
                ),
            ]
            data.append(row)

        # Fila de totales
        fila_totales = [
            Paragraph("<b>TOTAL</b>", self.style_total),
            "",
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

        # Crear tabla
        tabla = self.crear_tabla_datos(
            headers, data, self.COL_WIDTHS,
            incluir_totales=True,
            fila_totales=fila_totales,
        )
        elements.append(tabla)

        # Firma
        elements.extend(
            self.crear_firma("JEFE DE LA UNIDAD DE TRABAJO")
        )

        # Construir PDF
        doc.build(elements)
