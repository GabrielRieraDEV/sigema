"""
sticker.py — Generación de etiquetas (stickers) físicas de bienes muebles.

Cada sticker mide 10 cm × 4 cm y replica el diseño oficial:

    ┌───────────┬───────────────────────────────────────────┐
    │  [LOGO]   │  INSTITUTO AUTÓNOMO MINAS BOLÍVAR          │
    │ Gob.      │  DESCRIPCIÓN  MARCA  MODELO                │
    │ Bolívar   │  NOMBRE DE LA GERENCIA / DEPARTAMENTO      │
    │           │            CÓDIGO DEL BIEN                 │
    └───────────┴───────────────────────────────────────────┘

- Logo a la izquierda (~30 % del ancho); si no hay imagen, se imprime
  el texto "GOBERNACIÓN DE BOLÍVAR".
- Texto a la derecha en 4 líneas, todo en MAYÚSCULAS.
- Helvetica-Bold para institución y código; Helvetica para
  descripción y gerencia.
- Sin colores (impresión en blanco y negro).

Funciones públicas
------------------
- ``generar_sticker(bien)`` -> bytes   : PDF de 1 sticker (página 10×4 cm).
- ``generar_sticker_hoja(bienes)`` -> bytes : hoja carta con 2×6 = 12
  stickers por página, lista para imprimir en papel de etiquetas o
  papel normal para recortar.
"""

from __future__ import annotations

import io
import os
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate,
    Paragraph, Table, TableStyle,
)

# ----------------------------------------------------------------------
# Constantes de diseño
# ----------------------------------------------------------------------
STICKER_WIDTH = 10 * cm
STICKER_HEIGHT = 4 * cm

# Grilla de la hoja carta: 2 columnas × 6 filas = 12 stickers.
COLS = 2
ROWS = 6
PER_SHEET = COLS * ROWS

INSTITUCION = "INSTITUTO AUTÓNOMO MINAS BOLÍVAR"
try:
    from src.paths import resource_path
    LOGO_PATH = str(resource_path("assets/logo.png"))
except Exception:
    LOGO_PATH = "assets/logo.png"

# Longitud máxima de la línea de características para no desbordar.
_MAX_CARACTERISTICAS = 90

# ----------------------------------------------------------------------
# Estilos (blanco y negro)
# ----------------------------------------------------------------------
_STYLE_INSTITUCION = ParagraphStyle(
    "StkInstitucion", fontName="Helvetica-Bold",
    fontSize=8.5, leading=10, alignment=TA_LEFT, textColor=colors.black,
)
_STYLE_TEXTO = ParagraphStyle(
    "StkTexto", fontName="Helvetica",
    fontSize=7, leading=8.5, alignment=TA_LEFT, textColor=colors.black,
)
_STYLE_CODIGO = ParagraphStyle(
    "StkCodigo", fontName="Helvetica-Bold",
    fontSize=12, leading=13, alignment=TA_CENTER, textColor=colors.black,
)
_STYLE_LOGO = ParagraphStyle(
    "StkLogo", fontName="Helvetica-Bold",
    fontSize=6.5, leading=8, alignment=TA_CENTER, textColor=colors.black,
)


# ----------------------------------------------------------------------
# Helpers de contenido
# ----------------------------------------------------------------------
def _mayus(valor: Any) -> str:
    return str(valor or "").strip().upper()


def _caracteristicas(bien: dict[str, Any]) -> str:
    """Combina descripción + marca + modelo en una sola línea (MAYÚSCULAS)."""
    partes = [
        bien.get("descripcion", ""),
        bien.get("marca", ""),
        bien.get("modelo", ""),
    ]
    texto = " ".join(p.strip() for p in partes if p and str(p).strip())
    texto = texto.upper()
    if len(texto) > _MAX_CARACTERISTICAS:
        texto = texto[: _MAX_CARACTERISTICAS - 1].rstrip() + "…"
    return texto


def _celda_logo():
    """Devuelve el flowable del logo o su texto de respaldo."""
    if os.path.exists(LOGO_PATH):
        try:
            img = Image(
                LOGO_PATH, width=2.5 * cm, height=2.5 * cm, kind="proportional"
            )
            img.hAlign = "CENTER"
            return img
        except Exception:
            pass
    return Paragraph("GOBERNACIÓN<br/>DE BOLÍVAR", _STYLE_LOGO)


def _sticker_flowable(bien: dict[str, Any]) -> Table:
    """Construye un sticker (10×4 cm) como tabla flowable de ReportLab."""
    # Columna derecha: 4 líneas apiladas.
    derecha_data = [
        [Paragraph(INSTITUCION, _STYLE_INSTITUCION)],
        [Paragraph(_caracteristicas(bien) or "&nbsp;", _STYLE_TEXTO)],
        [Paragraph(_mayus(bien.get("departamento_nombre")) or "&nbsp;",
                   _STYLE_TEXTO)],
        [Paragraph(_mayus(bien.get("codigo_activo")), _STYLE_CODIGO)],
    ]
    derecha = Table(derecha_data, colWidths=[STICKER_WIDTH * 0.70])
    derecha.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 2), "LEFT"),
        ("ALIGN", (0, 3), (0, 3), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))

    sticker = Table(
        [[_celda_logo(), derecha]],
        colWidths=[STICKER_WIDTH * 0.30, STICKER_WIDTH * 0.70],
        rowHeights=[STICKER_HEIGHT],
    )
    sticker.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
        ("LINEAFTER", (0, 0), (0, 0), 0.5, colors.black),
        ("LEFTPADDING", (0, 0), (0, 0), 2),
        ("RIGHTPADDING", (0, 0), (0, 0), 2),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return sticker


# ----------------------------------------------------------------------
# API pública
# ----------------------------------------------------------------------
def generar_sticker(bien: dict[str, Any]) -> bytes:
    """Genera el PDF (en memoria) de un único sticker de 10×4 cm."""
    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=(STICKER_WIDTH, STICKER_HEIGHT),
        title="SIGEMA — Sticker de bien",
    )
    frame = Frame(
        0, 0, STICKER_WIDTH, STICKER_HEIGHT,
        leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0,
        id="sticker",
    )
    doc.addPageTemplates([PageTemplate(id="sticker", frames=[frame])])
    doc.build([_sticker_flowable(bien)])
    return buffer.getvalue()


def generar_sticker_hoja(bienes: list[dict[str, Any]]) -> bytes:
    """Genera una hoja carta con una grilla de 2×6 = 12 stickers por página.

    Si hay más de 12 bienes, se agregan páginas adicionales.
    """
    if not bienes:
        raise ValueError("No hay bienes para generar la hoja de stickers.")

    buffer = io.BytesIO()
    grid_w = COLS * STICKER_WIDTH
    grid_h = ROWS * STICKER_HEIGHT
    x = (letter[0] - grid_w) / 2
    y = (letter[1] - grid_h) / 2

    doc = BaseDocTemplate(
        buffer, pagesize=letter, title="SIGEMA — Hoja de stickers",
    )
    frame = Frame(
        x, y, grid_w, grid_h,
        leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0,
        id="grid",
    )
    doc.addPageTemplates([PageTemplate(id="grid", frames=[frame])])

    elements: list = []
    for inicio in range(0, len(bienes), PER_SHEET):
        grupo = bienes[inicio:inicio + PER_SHEET]
        filas = []
        for r in range(ROWS):
            fila = []
            for c in range(COLS):
                idx = r * COLS + c
                if idx < len(grupo):
                    fila.append(_sticker_flowable(grupo[idx]))
                else:
                    fila.append("")  # celda vacía
            filas.append(fila)

        grid = Table(
            filas,
            colWidths=[STICKER_WIDTH] * COLS,
            rowHeights=[STICKER_HEIGHT] * ROWS,
        )
        grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(grid)
        if inicio + PER_SHEET < len(bienes):
            elements.append(PageBreak())

    doc.build(elements)
    return buffer.getvalue()
