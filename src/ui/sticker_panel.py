"""
sticker_panel.py — Diálogo para generar e imprimir stickers de bienes.

Se accede desde el listado de bienes o desde el detalle de un bien.
Permite dos modos:

- **Sticker individual**: genera el PDF de 1 sticker para el bien
  seleccionado.
- **Hoja de stickers**: selecciona varios bienes y genera una hoja
  carta con 12 stickers por página (grilla 2×6).

La generación de stickers es solo impresión: NO registra auditoría ni
genera movimientos de datos (solo consulta los bienes).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.bien_service import BienService
from src.reports.sticker import generar_sticker, generar_sticker_hoja


def _btn_style(color: str, hover: str) -> str:
    return (
        f"QPushButton {{ background:{color}; color:white; font-weight:bold;"
        f" padding:5px 14px; border-radius:4px; }}"
        f"QPushButton:hover {{ background:{hover}; }}"
    )


class StickerDialog(QDialog):
    """Diálogo de generación/impresión de stickers de bienes.

    Parameters
    ----------
    bien_service : BienService
        Servicio de bienes (solo se usan operaciones de lectura).
    usuario_id : int
        ID del usuario autenticado (no se audita esta operación).
    bien_inicial : dict | None
        Bien a preseleccionar (p.ej. al abrir desde el detalle).
    """

    _COLUMNAS = ["Código Activo", "Descripción", "Departamento"]

    def __init__(
        self,
        bien_service: BienService,
        usuario_id: int,
        bien_inicial: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._service = bien_service
        self._usuario_id = usuario_id
        self._bien_inicial = bien_inicial or {}
        self._datos: list[dict] = []

        self._init_ui()
        self._cargar_bienes()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        self.setWindowTitle("Stickers de Bienes")
        self.setMinimumSize(720, 520)
        layout = QVBoxLayout(self)

        # --- Modo ---
        grp_modo = QGroupBox("Modo de impresión")
        modo_layout = QHBoxLayout(grp_modo)
        self._rb_individual = QRadioButton("Sticker individual (1 bien)")
        self._rb_hoja = QRadioButton(
            "Hoja de stickers (selección múltiple, 12 por hoja)")
        self._rb_individual.setChecked(True)
        self._grupo_modo = QButtonGroup(self)
        self._grupo_modo.addButton(self._rb_individual)
        self._grupo_modo.addButton(self._rb_hoja)
        self._rb_individual.toggled.connect(self._on_modo_cambiado)
        modo_layout.addWidget(self._rb_individual)
        modo_layout.addWidget(self._rb_hoja)
        modo_layout.addStretch()
        layout.addWidget(grp_modo)

        # --- Filtro rápido ---
        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel("Buscar:"))
        self._filtro = QLineEdit()
        self._filtro.setPlaceholderText("Código o descripción…")
        self._filtro.returnPressed.connect(self._on_buscar)
        filtro_layout.addWidget(self._filtro)
        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.setStyleSheet(_btn_style("#1B3A5C", "#245280"))
        btn_buscar.clicked.connect(self._on_buscar)
        filtro_layout.addWidget(btn_buscar)
        layout.addLayout(filtro_layout)

        # --- Tabla de bienes ---
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self._COLUMNAS))
        self._tabla.setHorizontalHeaderLabels(self._COLUMNAS)
        self._tabla.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)
        header = self._tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._tabla)

        self._lbl_ayuda = QLabel()
        self._lbl_ayuda.setStyleSheet("color:#555; font-size:11px;")
        layout.addWidget(self._lbl_ayuda)

        # --- Botones ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_preview = QPushButton("👁 Vista previa")
        btn_preview.setStyleSheet(_btn_style("#1B3A5C", "#245280"))
        btn_preview.clicked.connect(self._on_vista_previa)
        btn_layout.addWidget(btn_preview)

        btn_imprimir = QPushButton("🖨 Imprimir")
        btn_imprimir.setStyleSheet(_btn_style("#1B7F3A", "#238C47"))
        btn_imprimir.clicked.connect(self._on_imprimir)
        btn_layout.addWidget(btn_imprimir)

        btn_cerrar = QPushButton("✖ Cerrar")
        btn_cerrar.setStyleSheet(_btn_style("#CC0000", "#FF3333"))
        btn_cerrar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cerrar)

        layout.addLayout(btn_layout)

        self._on_modo_cambiado()

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------
    def _cargar_bienes(self, codigo=None, descripcion=None) -> None:
        try:
            self._datos = self._service.buscar_bienes(
                codigo=codigo, descripcion=descripcion
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudieron cargar los bienes:\n{exc}")
            self._datos = []
        self._poblar_tabla()
        self._preseleccionar()

    def _poblar_tabla(self) -> None:
        self._tabla.setRowCount(0)
        for fila, bien in enumerate(self._datos):
            self._tabla.insertRow(fila)
            items = [
                bien.get("codigo_activo", ""),
                bien.get("descripcion", ""),
                bien.get("departamento_nombre", ""),
            ]
            for col, texto in enumerate(items):
                item = QTableWidgetItem(str(texto))
                self._tabla.setItem(fila, col, item)

    def _preseleccionar(self) -> None:
        """Selecciona la fila del bien inicial, si se proporcionó."""
        codigo = self._bien_inicial.get("codigo_activo")
        if not codigo:
            return
        for fila, bien in enumerate(self._datos):
            if bien.get("codigo_activo") == codigo:
                self._tabla.selectRow(fila)
                self._tabla.scrollToItem(self._tabla.item(fila, 0))
                break

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_modo_cambiado(self, *_args) -> None:
        if self._rb_individual.isChecked():
            self._tabla.setSelectionMode(
                QTableWidget.SelectionMode.SingleSelection)
            self._lbl_ayuda.setText(
                "Seleccione un bien para imprimir su sticker individual "
                "(10 × 4 cm).")
        else:
            self._tabla.setSelectionMode(
                QTableWidget.SelectionMode.ExtendedSelection)
            self._lbl_ayuda.setText(
                "Seleccione uno o más bienes (Ctrl/Shift) para la hoja de "
                "stickers — 12 por hoja carta.")

    def _on_buscar(self) -> None:
        texto = self._filtro.text().strip() or None
        # Buscamos por código y por descripción con el mismo término.
        try:
            por_codigo = self._service.buscar_bienes(codigo=texto) if texto else []
            por_desc = self._service.buscar_bienes(descripcion=texto) if texto else []
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Error en la búsqueda:\n{exc}")
            return

        if texto is None:
            self._cargar_bienes()
            return

        # Unir resultados sin duplicar (por id).
        vistos, union = set(), []
        for b in (por_codigo + por_desc):
            if b.get("id") not in vistos:
                vistos.add(b.get("id"))
                union.append(b)
        self._datos = union
        self._poblar_tabla()

    def _bienes_seleccionados_completos(self) -> list[dict] | None:
        """Devuelve los datos COMPLETOS de los bienes seleccionados.

        Vuelve a consultar cada bien por su código para garantizar que
        marca/modelo/departamento estén presentes (el listado resumido
        no los incluye).
        """
        filas = sorted({idx.row() for idx in self._tabla.selectedIndexes()})
        if not filas:
            QMessageBox.warning(
                self, "Selección requerida",
                "Seleccione al menos un bien de la tabla.")
            return None

        completos = []
        for fila in filas:
            if fila >= len(self._datos):
                continue
            codigo = self._datos[fila].get("codigo_activo")
            bien = None
            try:
                bien = self._service.obtener_bien(codigo)
            except Exception:
                bien = None
            completos.append(bien or self._datos[fila])
        return completos

    def _generar_pdf(self) -> bytes | None:
        """Genera los bytes del PDF según el modo y la selección."""
        bienes = self._bienes_seleccionados_completos()
        if not bienes:
            return None

        try:
            if self._rb_individual.isChecked():
                if len(bienes) != 1:
                    QMessageBox.warning(
                        self, "Selección",
                        "El modo individual requiere seleccionar un solo bien.")
                    return None
                return generar_sticker(bienes[0])
            return generar_sticker_hoja(bienes)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudo generar el sticker:\n{exc}")
            return None

    def _on_vista_previa(self) -> None:
        pdf_bytes = self._generar_pdf()
        if not pdf_bytes:
            return
        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", delete=False, prefix="sigema_sticker_")
            tmp.write(pdf_bytes)
            tmp.close()
            if hasattr(os, "startfile"):
                os.startfile(tmp.name)  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", tmp.name], check=True)
        except Exception as exc:
            QMessageBox.warning(
                self, "Vista previa",
                f"No se pudo abrir la vista previa:\n{exc}")

    def _on_imprimir(self) -> None:
        pdf_bytes = self._generar_pdf()
        if not pdf_bytes:
            return
        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", delete=False, prefix="sigema_sticker_")
            tmp.write(pdf_bytes)
            tmp.close()
        except Exception as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudo preparar el archivo:\n{exc}")
            return

        try:
            os.startfile(tmp.name, "print")  # type: ignore[attr-defined]
            QMessageBox.information(
                self, "Impresión",
                "El sticker se envió a la impresora del sistema.")
        except AttributeError:
            # No estamos en Windows: intentar con lpr.
            try:
                subprocess.run(["lpr", tmp.name], check=True)
                QMessageBox.information(
                    self, "Impresión",
                    "El sticker se envió a la impresora (lpr).")
            except Exception as exc:
                QMessageBox.warning(
                    self, "Impresión",
                    f"No se pudo imprimir automáticamente:\n{exc}\n\n"
                    "Use la vista previa para imprimir manualmente.")
        except Exception as exc:
            QMessageBox.critical(
                self, "Error de impresión",
                f"Error al enviar a impresora:\n{exc}")
