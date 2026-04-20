"""
bien_listado.py — Pantalla principal del Módulo A: listado de bienes muebles.

Tabla con columnas: código, descripción, categoría, departamento, estado,
fecha registro.  Filtros en la parte superior y botones de acción en la
parte inferior.

Estilo de escritorio clásico (NF-07) — sin estilos modernos.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
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
from src.ui.bien_estado import BienEstadoDialog
from src.ui.bien_form import BienFormDialog


class BienListadoWidget(QWidget):
    """Widget principal del módulo Bienes Muebles.

    Muestra la tabla de bienes con filtros y acciones CRUD.
    Se integra como widget central de la QMainWindow.
    """

    # Columnas de la tabla
    _COLUMNAS = [
        "Código Activo",
        "Descripción",
        "Categoría",
        "Departamento",
        "Estado",
        "Fecha Registro",
    ]

    def __init__(
        self,
        bien_service: BienService,
        usuario_id: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._service = bien_service
        self._usuario_id = usuario_id

        # Datos en memoria para la tabla
        self._datos: list[dict] = []

        self._init_ui()
        self._cargar_combos()
        self._actualizar_tabla()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Filtros ---
        layout.addWidget(self._crear_filtros())

        # --- Tabla ---
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self._COLUMNAS))
        self._tabla.setHorizontalHeaderLabels(self._COLUMNAS)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)

        # Ajustar columnas
        header = self._tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._tabla)

        # --- Barra de acciones ---
        layout.addLayout(self._crear_acciones())

    def _crear_filtros(self) -> QGroupBox:
        """Crea el grupo de filtros superiores."""
        grupo = QGroupBox("Filtros de búsqueda")
        h_layout = QHBoxLayout(grupo)

        # Código
        h_layout.addWidget(QLabel("Código:"))
        self._filtro_codigo = QLineEdit()
        self._filtro_codigo.setPlaceholderText("Código activo")
        self._filtro_codigo.setMaximumWidth(150)
        h_layout.addWidget(self._filtro_codigo)

        # Descripción
        h_layout.addWidget(QLabel("Descripción:"))
        self._filtro_descripcion = QLineEdit()
        self._filtro_descripcion.setPlaceholderText("Nombre o descripción")
        self._filtro_descripcion.setMaximumWidth(200)
        h_layout.addWidget(self._filtro_descripcion)

        # Departamento
        h_layout.addWidget(QLabel("Departamento:"))
        self._filtro_departamento = QComboBox()
        self._filtro_departamento.setMinimumWidth(160)
        h_layout.addWidget(self._filtro_departamento)

        # Estado
        h_layout.addWidget(QLabel("Estado:"))
        self._filtro_estado = QComboBox()
        self._filtro_estado.addItems(["Todos", "Activo", "En desuso", "Faltante"])
        h_layout.addWidget(self._filtro_estado)

        # Botón buscar
        btn_buscar = QPushButton("Buscar")
        btn_buscar.clicked.connect(self._on_buscar)
        h_layout.addWidget(btn_buscar)

        return grupo

    def _crear_acciones(self) -> QHBoxLayout:
        """Crea la barra de botones de acción."""
        h_layout = QHBoxLayout()

        btn_nuevo = QPushButton("Nuevo")
        btn_nuevo.clicked.connect(self._on_nuevo)
        h_layout.addWidget(btn_nuevo)

        btn_ver = QPushButton("Ver / Editar")
        btn_ver.clicked.connect(self._on_ver_editar)
        h_layout.addWidget(btn_ver)

        btn_estado = QPushButton("Cambiar Estado")
        btn_estado.clicked.connect(self._on_cambiar_estado)
        h_layout.addWidget(btn_estado)

        h_layout.addStretch()

        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.clicked.connect(self._actualizar_tabla)
        h_layout.addWidget(btn_actualizar)

        return h_layout

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------
    def _cargar_combos(self) -> None:
        """Carga los combos de filtro desde la BD."""
        # Departamentos
        self._filtro_departamento.clear()
        self._filtro_departamento.addItem("Todos", None)
        try:
            departamentos = self._service.obtener_departamentos()
            for dep in departamentos:
                self._filtro_departamento.addItem(dep["nombre"], dep["id"])
        except Exception:
            pass  # Si falla, el combo queda solo con "Todos"

    def _actualizar_tabla(self) -> None:
        """Recarga la tabla con todos los bienes (sin filtros)."""
        try:
            self._datos = self._service.buscar_bienes()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudieron cargar los bienes:\n{exc}",
            )
            self._datos = []

        self._poblar_tabla()

    def _poblar_tabla(self) -> None:
        """Llena la tabla con los datos actuales en self._datos."""
        self._tabla.setRowCount(0)

        for fila, bien in enumerate(self._datos):
            self._tabla.insertRow(fila)

            items = [
                bien.get("codigo_activo", ""),
                bien.get("descripcion", ""),
                bien.get("categoria_nombre", ""),
                bien.get("departamento_nombre", ""),
                bien.get("estado", ""),
                str(bien.get("created_at", ""))[:10],  # solo fecha
            ]

            for col, texto in enumerate(items):
                item = QTableWidgetItem(str(texto))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._tabla.setItem(fila, col, item)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_buscar(self) -> None:
        """Aplica los filtros y recarga la tabla."""
        codigo = self._filtro_codigo.text().strip() or None
        descripcion = self._filtro_descripcion.text().strip() or None

        dep_id = self._filtro_departamento.currentData()

        estado_txt = self._filtro_estado.currentText()
        estado = estado_txt if estado_txt != "Todos" else None

        try:
            self._datos = self._service.buscar_bienes(
                codigo=codigo,
                descripcion=descripcion,
                departamento_id=dep_id,
                estado=estado,
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Error", f"Error en la búsqueda:\n{exc}"
            )
            self._datos = []

        self._poblar_tabla()

    def _obtener_bien_seleccionado(self) -> dict | None:
        """Retorna el dict del bien seleccionado o None."""
        fila = self._tabla.currentRow()
        if fila < 0 or fila >= len(self._datos):
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Seleccione un bien de la tabla.",
            )
            return None
        return self._datos[fila]

    def _on_nuevo(self) -> None:
        """Abre el formulario en modo Nuevo."""
        dialog = BienFormDialog(
            bien_service=self._service,
            usuario_id=self._usuario_id,
            modo="nuevo",
            parent=self,
        )
        if dialog.exec():
            self._actualizar_tabla()

    def _on_ver_editar(self) -> None:
        """Abre el formulario en modo Ver con el bien seleccionado."""
        bien_resumen = self._obtener_bien_seleccionado()
        if bien_resumen is None:
            return

        # Obtener datos completos del bien
        bien = self._service.obtener_bien(bien_resumen["codigo_activo"])
        if bien is None:
            QMessageBox.warning(
                self,
                "No encontrado",
                "No se pudo cargar la información completa del bien.",
            )
            return

        dialog = BienFormDialog(
            bien_service=self._service,
            usuario_id=self._usuario_id,
            modo="ver",
            bien_data=bien,
            parent=self,
        )
        dialog.exec()

    def _on_cambiar_estado(self) -> None:
        """Abre el diálogo de cambio de estado."""
        bien_resumen = self._obtener_bien_seleccionado()
        if bien_resumen is None:
            return

        # Obtener datos completos
        bien = self._service.obtener_bien(bien_resumen["codigo_activo"])
        if bien is None:
            QMessageBox.warning(
                self,
                "No encontrado",
                "No se pudo cargar la información completa del bien.",
            )
            return

        dialog = BienEstadoDialog(
            bien_service=self._service,
            bien_data=bien,
            usuario_id=self._usuario_id,
            parent=self,
        )
        if dialog.exec():
            self._actualizar_tabla()
