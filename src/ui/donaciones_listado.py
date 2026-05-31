"""
donaciones_listado.py — Pantalla del módulo de Donaciones (solo lectura).

Lista todas las donaciones registradas con filtros por donante y por
rango de fechas.  Desde aquí se puede abrir el detalle del bien donado.
Las donaciones registradas no se pueden modificar.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.bien_service import BienService
from src.ui.bien_form import BienFormDialog


def _btn_style(color: str, hover: str) -> str:
    return (
        f"QPushButton {{ background:{color}; color:white; font-weight:bold;"
        f" padding:5px 14px; border-radius:4px; }}"
        f"QPushButton:hover {{ background:{hover}; }}"
    )


class DonacionesListadoWidget(QWidget):
    """Listado de donaciones registradas (solo lectura)."""

    _COLUMNAS = [
        "Código Bien",
        "Descripción",
        "Donante",
        "Tipo",
        "Fecha Donación",
        "N° Acta",
    ]

    def __init__(
        self,
        bien_service: BienService,
        donacion_service,
        usuario_id: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._bien_service = bien_service
        self._donacion_service = donacion_service
        self._usuario_id = usuario_id
        self._datos: list[dict] = []

        self._init_ui()
        self._actualizar_tabla()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._crear_filtros())

        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self._COLUMNAS))
        self._tabla.setHorizontalHeaderLabels(self._COLUMNAS)
        self._tabla.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)
        header = self._tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._tabla)

        layout.addLayout(self._crear_acciones())

    def _crear_filtros(self) -> QGroupBox:
        grupo = QGroupBox("Filtros de búsqueda")
        h = QHBoxLayout(grupo)

        h.addWidget(QLabel("Donante:"))
        self._filtro_donante = QLineEdit()
        self._filtro_donante.setPlaceholderText("Nombre del donante")
        self._filtro_donante.setMaximumWidth(220)
        self._filtro_donante.returnPressed.connect(self._on_buscar)
        h.addWidget(self._filtro_donante)

        self._chk_fechas = QCheckBox("Filtrar por fecha:")
        self._chk_fechas.toggled.connect(self._on_toggle_fechas)
        h.addWidget(self._chk_fechas)

        h.addWidget(QLabel("Desde:"))
        self._date_desde = QDateEdit()
        self._date_desde.setCalendarPopup(True)
        self._date_desde.setDisplayFormat("dd/MM/yyyy")
        self._date_desde.setDate(QDate.currentDate().addMonths(-12))
        self._date_desde.setEnabled(False)
        h.addWidget(self._date_desde)

        h.addWidget(QLabel("Hasta:"))
        self._date_hasta = QDateEdit()
        self._date_hasta.setCalendarPopup(True)
        self._date_hasta.setDisplayFormat("dd/MM/yyyy")
        self._date_hasta.setDate(QDate.currentDate())
        self._date_hasta.setEnabled(False)
        h.addWidget(self._date_hasta)

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.setStyleSheet(_btn_style("#1B3A5C", "#245280"))
        btn_buscar.clicked.connect(self._on_buscar)
        h.addWidget(btn_buscar)
        h.addStretch()

        return grupo

    def _crear_acciones(self) -> QHBoxLayout:
        h = QHBoxLayout()
        btn_ver = QPushButton("👁 Ver bien")
        btn_ver.setStyleSheet(_btn_style("#1B3A5C", "#245280"))
        btn_ver.clicked.connect(self._on_ver_bien)
        h.addWidget(btn_ver)
        h.addStretch()
        btn_actualizar = QPushButton("↺ Actualizar")
        btn_actualizar.setStyleSheet(_btn_style("#5C6B73", "#6D7F88"))
        btn_actualizar.clicked.connect(self._actualizar_tabla)
        h.addWidget(btn_actualizar)
        return h

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------
    def _on_toggle_fechas(self, activo: bool) -> None:
        self._date_desde.setEnabled(activo)
        self._date_hasta.setEnabled(activo)

    def _actualizar_tabla(self) -> None:
        self._cargar(donante=None, desde=None, hasta=None)

    def _on_buscar(self) -> None:
        donante = self._filtro_donante.text().strip() or None
        desde = hasta = None
        if self._chk_fechas.isChecked():
            desde = self._date_desde.date().toString("yyyy-MM-dd")
            hasta = self._date_hasta.date().toString("yyyy-MM-dd")
        self._cargar(donante=donante, desde=desde, hasta=hasta)

    def _cargar(self, donante, desde, hasta) -> None:
        try:
            self._datos = self._donacion_service.listar_donaciones(
                donante=donante, fecha_desde=desde, fecha_hasta=hasta)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudieron cargar las donaciones:\n{exc}")
            self._datos = []
        self._poblar_tabla()

    def _poblar_tabla(self) -> None:
        self._tabla.setRowCount(0)
        for fila, don in enumerate(self._datos):
            self._tabla.insertRow(fila)
            items = [
                don.get("codigo_activo", ""),
                don.get("bien_descripcion", ""),
                don.get("donante", ""),
                don.get("tipo_donante", "") or "",
                str(don.get("fecha_donacion", ""))[:10],
                don.get("acta_numero", "") or "",
            ]
            for col, texto in enumerate(items):
                item = QTableWidgetItem(str(texto))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._tabla.setItem(fila, col, item)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _on_ver_bien(self) -> None:
        fila = self._tabla.currentRow()
        if fila < 0 or fila >= len(self._datos):
            QMessageBox.warning(
                self, "Selección requerida",
                "Seleccione una donación de la tabla.")
            return

        bien_id = self._datos[fila].get("bien_id")
        try:
            bien = self._bien_service.obtener_bien_por_id(bien_id)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudo cargar el bien:\n{exc}")
            return

        if bien is None:
            QMessageBox.warning(
                self, "No encontrado",
                "No se pudo cargar la información del bien donado.")
            return

        dialog = BienFormDialog(
            bien_service=self._bien_service,
            usuario_id=self._usuario_id,
            modo="ver",
            bien_data=bien,
            parent=self,
            donacion_service=self._donacion_service,
        )
        dialog.exec()
