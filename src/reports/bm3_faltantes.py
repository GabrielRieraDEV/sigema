"""
bm3_faltantes.py — Generador PDF del formulario BM-3.

BM-3: Relación del Movimiento de Bienes Muebles Faltantes
(GOB-900-FM-078/15, Concepto 60)
Tabla con 8 columnas incluyendo Existencia Física y Registros Contables.
Bloque obligatorio de responsable y observaciones.
"""

from __future__ import annotations

from typing import Any

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import mm

from src.reports.bm_base import (
    BMBase, USABLE_WIDTH, COLOR_BORDER, COLOR_HIGHLIGHT,
)


class BM3Faltantes(BMBase):
    """Genera el formulario BM-3: Bienes Muebles Faltantes."""

    TIPO = "BM-3"
    TITULO = "RELACIÓN DEL MOVIMIENTO DE BIENES\nMUEBLES FALTANTES (BM-3)"
    CODIGO_GOB = "GOB-900-FM-078/15"
    FECHA_VIGENCIA = "11/07/2025"
    ACTUALIZACION = "04"

    COL_WIDTHS = [
        USABLE_WIDTH * 0.12,  # Clasificación / Código
        USABLE_WIDTH * 0.13,  # N° Identificación
        USABLE_WIDTH * 0.25,  # Descripción
        USABLE_WIDTH * 0.08,  # Existencia Física
        USABLE_WIDTH * 0.08,  # Registros Contables
        USABLE_WIDTH * 0.12,  # Valor Unitario
        USABLE_WIDTH * 0.10,  # Cantidad
        USABLE_WIDTH * 0.12,  # Valor Total
    ]

    def generar(
        self,
        buffer,
        faltantes: list[dict[str, Any]],
        depto: dict[str, Any],
    ) -> None:
        """Genera el PDF del BM-3.

        Parameters
        ----------
        faltantes : list[dict]
            Lista de bienes faltantes.
        depto : dict
            Departamento.
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

        # Concepto 60 destacado
        concepto_data = [[
            Paragraph(
                "<b>Concepto:</b> "
                f"<font color='#{COLOR_HIGHLIGHT.hexval()[2:]}'>"
                "<b>60 — Faltante por investigar</b></font>",
                self.style_body,
            ),
        ]]
        concepto_table = Table(
            concepto_data,
            colWidths=[USABLE_WIDTH],
        )
        concepto_table.setStyle(TableStyle([
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
            "EXISTENCIA\nFÍSICA",
            "REGISTROS\nCONTABLES",
            "VALOR\nUNITARIO",
            "CANTIDAD",
            "VALOR\nTOTAL",
        ]

        data = []
        total_unitario = 0
        total_cantidad = 0
        total_valor = 0

        for f in faltantes:
            v_unit = float(f.get("valor_unitario", 0))
            cant = int(f.get("cantidad_faltante", 0))
            v_total = float(f.get("valor_total", 0))
            total_unitario += v_unit
            total_cantidad += cant
            total_valor += v_total

            row = [
                Paragraph(
                    f"{f.get('clasificacion', '')}<br/>"
                    f"<font size='6'>{f.get('codigo', '')}</font>",
                    self.style_body_center,
                ),
                Paragraph(
                    str(f.get("numero_identificacion", "")),
                    self.style_body_center,
                ),
                Paragraph(
                    str(f.get("descripcion", "")),
                    self.style_body,
                ),
                Paragraph(
                    str(f.get("existencia_fisica", 0)),
                    self.style_body_center,
                ),
                Paragraph(
                    str(f.get("registros_contables", 0)),
                    self.style_body_center,
                ),
                Paragraph(
                    self.formato_moneda(v_unit),
                    self.style_body_right,
                ),
                Paragraph(str(cant), self.style_body_center),
                Paragraph(
                    self.formato_moneda(v_total),
                    self.style_body_right,
                ),
            ]
            data.append(row)

        fila_totales = [
            Paragraph("<b>TOTAL</b>", self.style_total),
            "",
            "",
            "",
            Paragraph("--->", self.style_total),
            Paragraph(
                f"<b>{self.formato_moneda(total_unitario)}</b>",
                self.style_body_right,
            ),
            Paragraph(
                f"<b>{total_cantidad}</b>",
                self.style_body_center,
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

        # Bloque de responsable (obligatorio)
        elements.extend(
            self._crear_bloque_responsable(faltantes)
        )

        # Firma con sello
        elements.extend(self._crear_firma_con_sello())

        doc.build(elements)

    def _crear_bloque_responsable(
        self, faltantes: list[dict[str, Any]]
    ) -> list:
        """Crea el bloque obligatorio de responsable y observaciones."""
        # Tomar responsable del primer faltante como referencia
        primer = faltantes[0] if faltantes else {}
        responsable = primer.get("responsable", "") or ""
        observaciones = primer.get("observaciones_faltante", "") or ""

        resp_data = [
            [
                Paragraph(
                    "<b>Faltante Determinado por:</b>",
                    self.style_header,
                ),
                "",
            ],
            [
                Paragraph(
                    "<b>Cargo que Desempeña:</b>",
                    self.style_small,
                ),
                Paragraph(responsable, self.style_body),
            ],
            [
                Paragraph(
                    "<b>Dependencia a la cual está Adscrito:</b>",
                    self.style_small,
                ),
                Paragraph("", self.style_body),
            ],
            [
                Paragraph(
                    "<b>Observaciones:</b>",
                    self.style_small,
                ),
                Paragraph(observaciones, self.style_body),
            ],
        ]

        resp_table = Table(
            resp_data,
            colWidths=[USABLE_WIDTH * 0.35, USABLE_WIDTH * 0.65],
        )
        resp_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, COLOR_BORDER),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ]))

        return [Spacer(1, 6 * mm), resp_table]

    def _crear_firma_con_sello(self) -> list:
        """Crea firma con espacio para sello."""
        firma_data = [
            [
                Paragraph(
                    "<b>Usuario responsable del (los) bien(es):</b>",
                    self.style_body,
                ),
                Paragraph("<b>Firma:</b> _______________", self.style_body),
                Paragraph("<b>Sello:</b>", self.style_body),
            ],
        ]
        firma_table = Table(
            firma_data,
            colWidths=[
                USABLE_WIDTH * 0.40,
                USABLE_WIDTH * 0.30,
                USABLE_WIDTH * 0.30,
            ],
        )
        firma_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("TOPPADDING", (0, 0), (-1, -1), 15),
            ("BOX", (2, 0), (2, 0), 0.5, COLOR_BORDER),
            ("BOTTOMPADDING", (2, 0), (2, 0), 30),
        ]))

        return [Spacer(1, 10 * mm), firma_table]
