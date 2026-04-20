"""
bm_base.py — Clase base para la generación de formularios BM en PDF.

Centraliza encabezado, bloque de identificación, firmas, estilos de
tabla y configuración de página.  Todos los generadores BM-1 al BM-4
heredan de esta clase.

Configuración según SIGEMA_Formularios_BM.md:
- Página: Letter (21.59 × 27.94 cm), orientación portrait
- Márgenes: 1.5 cm laterales, 2.0 cm superior e inferior
- Fuentes: Helvetica-Bold (encabezados), Helvetica (datos)
- Colores: azul oscuro header, gris alterno filas, azul claro totales
"""

from __future__ import annotations

from datetime import date
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ======================================================================
# Constantes de diseño
# ======================================================================

PAGE_WIDTH, PAGE_HEIGHT = letter  # 21.59 cm × 27.94 cm

MARGIN_LEFT = 1.5 * cm
MARGIN_RIGHT = 1.5 * cm
MARGIN_TOP = 2.0 * cm
MARGIN_BOTTOM = 2.0 * cm

# Ancho utilizable
USABLE_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT

# Fuentes (nombre, tamaño)
FONT_HEADER = ("Helvetica-Bold", 8)
FONT_SUBHEADER = ("Helvetica-Bold", 7)
FONT_BODY = ("Helvetica", 7)
FONT_SMALL = ("Helvetica", 6)
FONT_TITLE = ("Helvetica-Bold", 10)

# Colores exactos del documento SIGEMA_Formularios_BM.md
COLOR_HEADER_BG = colors.HexColor("#1B3A5C")    # azul oscuro — encabezado tabla
COLOR_HEADER_TEXT = colors.white
COLOR_ROW_ODD = colors.white
COLOR_ROW_EVEN = colors.HexColor("#F4F4F4")     # gris muy claro
COLOR_BORDER = colors.HexColor("#CCCCCC")        # gris — bordes
COLOR_TOTAL_BG = colors.HexColor("#D6E4F0")      # azul claro — totales
COLOR_HIGHLIGHT = colors.HexColor("#1B3A5C")      # para texto destacado

# Nombre de la institución
INSTITUCION = "Instituto Autónomo Minas Bolívar"
GOBERNACION = "Gobernación de Bolívar"
LEMA = "Transformación y Producción"

# Meses en español
MESES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


class BMBase:
    """Clase base para todos los generadores de formularios BM.

    Provee métodos reutilizables para encabezado, identificación,
    tabla y firmas.
    """

    def _crear_estilos(self):
        """Crea los estilos de párrafo reutilizables."""
        styles = getSampleStyleSheet()

        from reportlab.lib.styles import ParagraphStyle

        self.style_title = ParagraphStyle(
            "BMTitle",
            parent=styles["Normal"],
            fontName=FONT_TITLE[0],
            fontSize=FONT_TITLE[1],
            alignment=TA_CENTER,
            spaceAfter=2 * mm,
        )
        self.style_header = ParagraphStyle(
            "BMHeader",
            parent=styles["Normal"],
            fontName=FONT_HEADER[0],
            fontSize=FONT_HEADER[1],
            alignment=TA_LEFT,
        )
        self.style_body = ParagraphStyle(
            "BMBody",
            parent=styles["Normal"],
            fontName=FONT_BODY[0],
            fontSize=FONT_BODY[1],
            alignment=TA_LEFT,
        )
        self.style_body_center = ParagraphStyle(
            "BMBodyCenter",
            parent=styles["Normal"],
            fontName=FONT_BODY[0],
            fontSize=FONT_BODY[1],
            alignment=TA_CENTER,
        )
        self.style_body_right = ParagraphStyle(
            "BMBodyRight",
            parent=styles["Normal"],
            fontName=FONT_BODY[0],
            fontSize=FONT_BODY[1],
            alignment=TA_RIGHT,
        )
        self.style_small = ParagraphStyle(
            "BMSmall",
            parent=styles["Normal"],
            fontName=FONT_SMALL[0],
            fontSize=FONT_SMALL[1],
            alignment=TA_LEFT,
        )
        self.style_table_header = ParagraphStyle(
            "BMTableHeader",
            parent=styles["Normal"],
            fontName=FONT_HEADER[0],
            fontSize=FONT_HEADER[1],
            alignment=TA_CENTER,
            textColor=COLOR_HEADER_TEXT,
        )
        self.style_total = ParagraphStyle(
            "BMTotal",
            parent=styles["Normal"],
            fontName=FONT_HEADER[0],
            fontSize=FONT_HEADER[1],
            alignment=TA_RIGHT,
        )

    # ------------------------------------------------------------------
    # Encabezado del formulario
    # ------------------------------------------------------------------
    def crear_encabezado(
        self,
        tipo_bm: str,
        titulo: str,
        codigo_gob: str,
        fecha_vigencia: str,
        actualizacion: str,
    ) -> list:
        """Crea los elementos del encabezado como flowables de ReportLab.

        Returns
        -------
        list
            Lista de flowables (Table + Spacer) para el encabezado.
        """
        # Bloque izquierdo: institución
        izq = Paragraph(
            f"<b>{GOBERNACION}</b><br/>{LEMA}<br/><br/>"
            f"<b>{INSTITUCION}</b>",
            self.style_small,
        )

        # Bloque centro: título del formulario
        centro = Paragraph(
            f"<b>{titulo}</b>",
            self.style_title,
        )

        # Bloque derecho: metadatos
        der = Paragraph(
            f"<b>Código:</b> {codigo_gob}<br/>"
            f"<b>Fecha de Vigencia:</b> {fecha_vigencia}<br/>"
            f"<b>Actualización N°:</b> {actualizacion}",
            self.style_small,
        )

        header_table = Table(
            [[izq, centro, der]],
            colWidths=[USABLE_WIDTH * 0.25, USABLE_WIDTH * 0.50,
                       USABLE_WIDTH * 0.25],
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ("LINEBELOW", (0, 0), (-1, 0), 1, COLOR_HEADER_BG),
        ]))

        return [header_table, Spacer(1, 6 * mm)]

    # ------------------------------------------------------------------
    # Bloque de identificación
    # ------------------------------------------------------------------
    def crear_bloque_identificacion(
        self,
        depto: dict[str, Any],
        fecha_inventario: str | None = None,
    ) -> list:
        """Crea el bloque de identificación común a todos los formularios.

        Parameters
        ----------
        depto : dict
            Diccionario con 'nombre' y 'codigo' del departamento.
        fecha_inventario : str | None
            Fecha del inventario. Si None, usa la fecha actual.
        """
        fecha = fecha_inventario or date.today().strftime("%d/%m/%Y")

        campos = [
            ["Dirección Administrativa:", INSTITUCION,
             "Código:", depto.get("codigo", "")],
            ["Unidad de Trabajo:", depto.get("nombre", ""),
             "Fecha de Inventario:", fecha],
        ]

        rows = []
        for fila in campos:
            row = []
            for i, val in enumerate(fila):
                if i % 2 == 0:
                    row.append(Paragraph(f"<b>{val}</b>", self.style_small))
                else:
                    row.append(Paragraph(val, self.style_body))
            rows.append(row)

        id_table = Table(
            rows,
            colWidths=[
                USABLE_WIDTH * 0.20, USABLE_WIDTH * 0.35,
                USABLE_WIDTH * 0.18, USABLE_WIDTH * 0.27,
            ],
        )
        id_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, COLOR_BORDER),
        ]))

        return [id_table, Spacer(1, 4 * mm)]

    # ------------------------------------------------------------------
    # Tabla de datos con estilos base
    # ------------------------------------------------------------------
    def crear_tabla_datos(
        self,
        headers: list[str],
        data: list[list],
        col_widths: list[float],
        incluir_totales: bool = True,
        fila_totales: list | None = None,
    ) -> Table:
        """Crea una tabla formateada con encabezado oscuro, filas alternas
        y fila opcional de totales.

        Parameters
        ----------
        headers : list[str]
            Encabezados de columna (texto plano).
        data : list[list]
            Filas de datos (pueden contener Paragraph o strings).
        col_widths : list[float]
            Anchos de columna en puntos.
        incluir_totales : bool
            Si True, agrega la fila de totales.
        fila_totales : list | None
            Datos de la fila de totales.
        """
        # Encabezado
        header_row = [
            Paragraph(h, self.style_table_header) for h in headers
        ]

        table_data = [header_row] + data
        if incluir_totales and fila_totales:
            table_data.append(fila_totales)

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Estilos base
        estilo = [
            # Encabezado
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_HEADER_TEXT),
            ("FONTNAME", (0, 0), (-1, 0), FONT_HEADER[0]),
            ("FONTSIZE", (0, 0), (-1, 0), FONT_HEADER[1]),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            # Bordes
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            # Padding
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]

        # Filas alternas
        for i in range(1, len(table_data)):
            if incluir_totales and fila_totales and i == len(table_data) - 1:
                estilo.append(
                    ("BACKGROUND", (0, i), (-1, i), COLOR_TOTAL_BG)
                )
                estilo.append(
                    ("FONTNAME", (0, i), (-1, i), FONT_HEADER[0])
                )
            elif i % 2 == 0:
                estilo.append(
                    ("BACKGROUND", (0, i), (-1, i), COLOR_ROW_EVEN)
                )

        table.setStyle(TableStyle(estilo))
        return table

    # ------------------------------------------------------------------
    # Firmas
    # ------------------------------------------------------------------
    def crear_firma(self, etiqueta: str) -> list:
        """Crea un bloque de firma con línea y etiqueta."""
        firma_data = [
            ["", ""],
            [
                Paragraph(
                    f"<b>{etiqueta}:</b>",
                    self.style_body,
                ),
                "______________________________________",
            ],
        ]
        firma_table = Table(
            firma_data,
            colWidths=[USABLE_WIDTH * 0.45, USABLE_WIDTH * 0.55],
        )
        firma_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
        ]))
        return [Spacer(1, 10 * mm), firma_table]

    # ------------------------------------------------------------------
    # Documento base
    # ------------------------------------------------------------------
    def crear_documento(self, buffer) -> SimpleDocTemplate:
        """Crea el documento PDF base con la configuración de página."""
        return SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="SIGEMA — Formulario BM",
            author=INSTITUCION,
        )

    # ------------------------------------------------------------------
    # Formato de moneda
    # ------------------------------------------------------------------
    @staticmethod
    def formato_moneda(valor) -> str:
        """Formatea un valor numérico como moneda."""
        try:
            return f"{float(valor):,.2f}"
        except (ValueError, TypeError):
            return "0.00"
