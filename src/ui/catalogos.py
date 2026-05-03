"""
catalogos.py — Gestión de catálogos maestros (Módulo C, §4.3).

Pestañas:
  1. Departamentos / Subdepartamentos — CRUD completo con jerarquía.
  2. Categorías — CRUD completo.
  3. Cuentas Contables — solo activar/desactivar.

Solo visible para Administrador.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from src.core.auditoria import registrar_auditoria
from src.core.auth import Session
from src.db.catalogo_repository import CatalogoRepository


# ---------------------------------------------------------------------------
# Helper UI
# ---------------------------------------------------------------------------
def _btn_style(color: str, hover: str) -> str:
    return (
        f"QPushButton {{ background:{color}; color:white; font-weight:bold;"
        f" padding:5px 14px; border-radius:4px; }}"
        f"QPushButton:hover {{ background:{hover}; }}"
    )


# ===========================================================================
# Widget principal — Catálogos
# ===========================================================================
class CatalogosWidget(QWidget):
    """Panel de catálogos maestros con tres pestañas."""

    def __init__(self, catalogo_repo: CatalogoRepository, parent=None):
        super().__init__(parent)
        self._repo = catalogo_repo
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        tabs = QTabWidget()
        tabs.addTab(DepartamentosTab(self._repo), "Departamentos")
        tabs.addTab(CategoriasTab(self._repo), "Categorías")
        tabs.addTab(CuentasTab(self._repo), "Cuentas Contables")
        layout.addWidget(tabs)


# ===========================================================================
# Pestaña Departamentos
# ===========================================================================
class DepartamentosTab(QWidget):
    _COLS = ["ID", "Código", "Nombre", "Subdpto. de", "Estado"]

    def __init__(self, repo: CatalogoRepository, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._setup_ui()
        self.cargar_datos()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self._btn_nuevo = QPushButton("➕ Nuevo")
        self._btn_nuevo.setStyleSheet(_btn_style("#1B7F3A", "#238C47"))
        self._btn_nuevo.clicked.connect(self._nuevo)
        toolbar.addWidget(self._btn_nuevo)

        self._btn_editar = QPushButton("✏ Editar")
        self._btn_editar.setStyleSheet(_btn_style("#1B3A5C", "#245280"))
        self._btn_editar.clicked.connect(self._editar)
        toolbar.addWidget(self._btn_editar)

        self._btn_toggle = QPushButton("⏸ Activar/Desactivar")
        self._btn_toggle.setStyleSheet(_btn_style("#8B4513", "#A0522D"))
        self._btn_toggle.clicked.connect(self._toggle_estado)
        toolbar.addWidget(self._btn_toggle)

        toolbar.addStretch()
        btn_ref = QPushButton("↺ Actualizar")
        btn_ref.setStyleSheet(_btn_style("#5C6B73", "#6D7F88"))
        btn_ref.clicked.connect(self.cargar_datos)
        toolbar.addWidget(btn_ref)
        layout.addLayout(toolbar)

        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self._COLS))
        self._tabla.setHorizontalHeaderLabels(self._COLS)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._tabla.setColumnHidden(0, True)
        self._tabla.doubleClicked.connect(self._editar)
        layout.addWidget(self._tabla)

    def cargar_datos(self) -> None:
        try:
            depts = self._repo.listar_departamentos()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return

        self._tabla.setRowCount(0)
        for d in depts:
            row = self._tabla.rowCount()
            self._tabla.insertRow(row)
            items = [
                str(d["id"]),
                d.get("codigo", ""),
                d.get("nombre", ""),
                d.get("parent_nombre") or "—",
                "Activo" if d.get("activo") else "Inactivo",
            ]
            for col, txt in enumerate(items):
                item = QTableWidgetItem(txt)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if txt == "Inactivo":
                    item.setForeground(QColor("#888"))
                self._tabla.setItem(row, col, item)
        self._tabla.resizeColumnsToContents()

    def _seleccionado(self) -> dict | None:
        fila = self._tabla.currentRow()
        if fila < 0:
            return None
        return self._repo.buscar_departamento_por_id(
            int(self._tabla.item(fila, 0).text())
        )

    def _nuevo(self) -> None:
        dlg = DepartamentoFormDialog(self._repo, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

    def _editar(self) -> None:
        d = self._seleccionado()
        if d is None:
            QMessageBox.information(self, "Aviso", "Seleccione un departamento.")
            return
        dlg = DepartamentoFormDialog(self._repo, departamento=d, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

    def _toggle_estado(self) -> None:
        d = self._seleccionado()
        if d is None:
            QMessageBox.information(self, "Aviso", "Seleccione un departamento.")
            return
        nuevo = not d.get("activo", True)
        verbo = "activar" if nuevo else "desactivar"
        if QMessageBox.question(
            self, "Confirmar", f"¿Desea {verbo} '{d['nombre']}'?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            session = Session.get_instance()
            ok = self._repo.cambiar_estado_departamento(d["id"], nuevo)
            if ok:
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="departamento",
                    accion="CAMBIAR_ESTADO", registro_id=d["id"],
                    datos_antes={"activo": d.get("activo")},
                    datos_despues={"activo": nuevo},
                )
                self.cargar_datos()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))


class DepartamentoFormDialog(QDialog):
    def __init__(self, repo: CatalogoRepository, departamento: dict | None = None, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._dept = departamento
        self._es_nuevo = departamento is None
        self.setWindowTitle("SIGEMA — " + ("Nuevo departamento" if self._es_nuevo else "Editar departamento"))
        self.setMinimumWidth(420)
        self._setup_ui()
        if not self._es_nuevo:
            self._cargar_datos()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        grp = QGroupBox("Datos del departamento")
        form = QFormLayout(grp)
        form.setSpacing(10)

        self._codigo_edit = QLineEdit()
        self._codigo_edit.setPlaceholderText("Ej: DCB-01")
        form.addRow("Código *:", self._codigo_edit)

        self._nombre_edit = QLineEdit()
        self._nombre_edit.setPlaceholderText("Nombre del departamento")
        form.addRow("Nombre *:", self._nombre_edit)

        self._desc_edit = QTextEdit()
        self._desc_edit.setFixedHeight(60)
        self._desc_edit.setPlaceholderText("Descripción (opcional)")
        form.addRow("Descripción:", self._desc_edit)

        self._parent_combo = QComboBox()
        self._parent_combo.addItem("— Sin dependencia (nivel raíz) —", None)
        try:
            # Solo departamentos raíz como posibles padres (sin parent_id)
            depts = self._repo.listar_departamentos()
            for d in depts:
                es_raiz = d.get("parent_id") is None
                no_es_el_mismo = self._dept is None or d["id"] != self._dept.get("id")
                if es_raiz and no_es_el_mismo:
                    self._parent_combo.addItem(d["nombre"], d["id"])
        except Exception:
            pass
        form.addRow("Subdepartamento de:", self._parent_combo)

        root.addWidget(grp)
        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet("color:red; font-size:11px;")
        root.addWidget(self._error_lbl)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        btn_box.accepted.connect(self._guardar)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    def _cargar_datos(self) -> None:
        self._codigo_edit.setText(self._dept.get("codigo", ""))
        self._nombre_edit.setText(self._dept.get("nombre", ""))
        self._desc_edit.setPlainText(self._dept.get("descripcion") or "")
        parent_id = self._dept.get("parent_id")
        if parent_id:
            idx = self._parent_combo.findData(parent_id)
            if idx >= 0:
                self._parent_combo.setCurrentIndex(idx)

    def _guardar(self) -> None:
        session = Session.get_instance()
        codigo = self._codigo_edit.text().strip()
        nombre = self._nombre_edit.text().strip()
        desc = self._desc_edit.toPlainText().strip()
        parent_id = self._parent_combo.currentData()

        if not codigo:
            return self._error_lbl.setText("⚠ El código es obligatorio.")
        if not nombre:
            return self._error_lbl.setText("⚠ El nombre es obligatorio.")

        excluir = self._dept["id"] if not self._es_nuevo else None
        if self._repo.codigo_departamento_existe(codigo, excluir_id=excluir):
            return self._error_lbl.setText("⚠ El código ya está en uso.")

        datos = {"codigo": codigo, "nombre": nombre,
                 "descripcion": desc or None, "parent_id": parent_id}
        try:
            if self._es_nuevo:
                nuevo_id = self._repo.crear_departamento(datos)
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="departamento",
                    accion="CREAR", registro_id=nuevo_id, datos_despues=datos,
                )
            else:
                self._repo.actualizar_departamento(self._dept["id"], datos)
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="departamento",
                    accion="ACTUALIZAR", registro_id=self._dept["id"],
                    datos_antes=self._dept, datos_despues=datos,
                )
            self.accept()
        except Exception as exc:
            self._error_lbl.setText(f"⚠ Error: {exc}")


# ===========================================================================
# Pestaña Categorías
# ===========================================================================
class CategoriasTab(QWidget):
    _COLS = ["ID", "Nombre", "Descripción", "Estado"]

    def __init__(self, repo: CatalogoRepository, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._setup_ui()
        self.cargar_datos()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self._btn_nuevo = QPushButton("➕ Nueva")
        self._btn_nuevo.setStyleSheet(_btn_style("#1B7F3A", "#238C47"))
        self._btn_nuevo.clicked.connect(self._nueva)
        toolbar.addWidget(self._btn_nuevo)

        self._btn_editar = QPushButton("✏ Editar")
        self._btn_editar.setStyleSheet(_btn_style("#1B3A5C", "#245280"))
        self._btn_editar.clicked.connect(self._editar)
        toolbar.addWidget(self._btn_editar)

        self._btn_toggle = QPushButton("⏸ Activar/Desactivar")
        self._btn_toggle.setStyleSheet(_btn_style("#8B4513", "#A0522D"))
        self._btn_toggle.clicked.connect(self._toggle_estado)
        toolbar.addWidget(self._btn_toggle)

        toolbar.addStretch()
        btn_ref = QPushButton("↺ Actualizar")
        btn_ref.setStyleSheet(_btn_style("#5C6B73", "#6D7F88"))
        btn_ref.clicked.connect(self.cargar_datos)
        toolbar.addWidget(btn_ref)
        layout.addLayout(toolbar)

        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self._COLS))
        self._tabla.setHorizontalHeaderLabels(self._COLS)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tabla.setColumnHidden(0, True)
        self._tabla.doubleClicked.connect(self._editar)
        layout.addWidget(self._tabla)

    def cargar_datos(self) -> None:
        try:
            cats = self._repo.listar_categorias()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._tabla.setRowCount(0)
        for c in cats:
            row = self._tabla.rowCount()
            self._tabla.insertRow(row)
            items = [
                str(c["id"]), c.get("nombre", ""),
                c.get("descripcion") or "",
                "Activo" if c.get("activo") else "Inactivo",
            ]
            for col, txt in enumerate(items):
                item = QTableWidgetItem(txt)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if txt == "Inactivo":
                    item.setForeground(QColor("#888"))
                self._tabla.setItem(row, col, item)
        self._tabla.resizeColumnsToContents()

    def _seleccionada(self) -> dict | None:
        fila = self._tabla.currentRow()
        if fila < 0:
            return None
        return self._repo.buscar_categoria_por_id(int(self._tabla.item(fila, 0).text()))

    def _nueva(self) -> None:
        dlg = CategoriaFormDialog(self._repo, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

    def _editar(self) -> None:
        cat = self._seleccionada()
        if cat is None:
            QMessageBox.information(self, "Aviso", "Seleccione una categoría.")
            return
        dlg = CategoriaFormDialog(self._repo, categoria=cat, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

    def _toggle_estado(self) -> None:
        cat = self._seleccionada()
        if cat is None:
            QMessageBox.information(self, "Aviso", "Seleccione una categoría.")
            return
        nuevo = not cat.get("activo", True)
        verbo = "activar" if nuevo else "desactivar"
        if QMessageBox.question(
            self, "Confirmar", f"¿Desea {verbo} '{cat['nombre']}'?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            session = Session.get_instance()
            ok = self._repo.cambiar_estado_categoria(cat["id"], nuevo)
            if ok:
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="categoria",
                    accion="CAMBIAR_ESTADO", registro_id=cat["id"],
                    datos_antes={"activo": cat.get("activo")},
                    datos_despues={"activo": nuevo},
                )
                self.cargar_datos()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))


class CategoriaFormDialog(QDialog):
    def __init__(self, repo: CatalogoRepository, categoria: dict | None = None, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._cat = categoria
        self._es_nuevo = categoria is None
        self.setWindowTitle("SIGEMA — " + ("Nueva categoría" if self._es_nuevo else "Editar categoría"))
        self.setMinimumWidth(400)
        self._setup_ui()
        if not self._es_nuevo:
            self._cargar_datos()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        grp = QGroupBox("Datos de la categoría")
        form = QFormLayout(grp)
        form.setSpacing(10)

        self._nombre_edit = QLineEdit()
        form.addRow("Nombre *:", self._nombre_edit)

        self._desc_edit = QTextEdit()
        self._desc_edit.setFixedHeight(70)
        form.addRow("Descripción:", self._desc_edit)
        root.addWidget(grp)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet("color:red; font-size:11px;")
        root.addWidget(self._error_lbl)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        btn_box.accepted.connect(self._guardar)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

    def _cargar_datos(self) -> None:
        self._nombre_edit.setText(self._cat.get("nombre", ""))
        self._desc_edit.setPlainText(self._cat.get("descripcion") or "")

    def _guardar(self) -> None:
        session = Session.get_instance()
        nombre = self._nombre_edit.text().strip()
        desc = self._desc_edit.toPlainText().strip()

        if not nombre:
            return self._error_lbl.setText("⚠ El nombre es obligatorio.")

        excluir = self._cat["id"] if not self._es_nuevo else None
        if self._repo.nombre_categoria_existe(nombre, excluir_id=excluir):
            return self._error_lbl.setText("⚠ El nombre ya está en uso.")

        datos = {"nombre": nombre, "descripcion": desc or None}
        try:
            if self._es_nuevo:
                nuevo_id = self._repo.crear_categoria(datos)
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="categoria",
                    accion="CREAR", registro_id=nuevo_id, datos_despues=datos,
                )
            else:
                self._repo.actualizar_categoria(self._cat["id"], datos)
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="categoria",
                    accion="ACTUALIZAR", registro_id=self._cat["id"],
                    datos_antes=self._cat, datos_despues=datos,
                )
            self.accept()
        except Exception as exc:
            self._error_lbl.setText(f"⚠ Error: {exc}")


# ===========================================================================
# Pestaña Cuentas Contables
# ===========================================================================
class CuentasTab(QWidget):
    _COLS = ["Código", "Descripción", "Estado"]

    def __init__(self, repo: CatalogoRepository, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._setup_ui()
        self.cargar_datos()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        info = QLabel(
            "ℹ Las cuentas contables son el catálogo oficial 2-1-214-XX del Estado. "
            "Solo puede activarlas o desactivarlas."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size:11px; color:#555; padding:6px; "
                           "background:#f0f4ff; border-radius:4px;")
        layout.addWidget(info)

        toolbar = QHBoxLayout()
        self._btn_toggle = QPushButton("⏸ Activar / Desactivar")
        self._btn_toggle.setStyleSheet(_btn_style("#8B4513", "#A0522D"))
        self._btn_toggle.clicked.connect(self._toggle_estado)
        toolbar.addWidget(self._btn_toggle)
        toolbar.addStretch()
        btn_ref = QPushButton("↺ Actualizar")
        btn_ref.setStyleSheet(_btn_style("#5C6B73", "#6D7F88"))
        btn_ref.clicked.connect(self.cargar_datos)
        toolbar.addWidget(btn_ref)
        layout.addLayout(toolbar)

        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self._COLS))
        self._tabla.setHorizontalHeaderLabels(self._COLS)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._tabla)

    def cargar_datos(self) -> None:
        try:
            cuentas = self._repo.listar_cuentas()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._tabla.setRowCount(0)
        for c in cuentas:
            row = self._tabla.rowCount()
            self._tabla.insertRow(row)
            items = [
                c.get("codigo", ""),
                c.get("descripcion", ""),
                "Activo" if c.get("activo") else "Inactivo",
            ]
            for col, txt in enumerate(items):
                item = QTableWidgetItem(txt)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if txt == "Inactivo":
                    item.setForeground(QColor("#888"))
                self._tabla.setItem(row, col, item)
        self._tabla.resizeColumnsToContents()

    def _seleccionada(self) -> dict | None:
        fila = self._tabla.currentRow()
        if fila < 0:
            return None
        codigo = self._tabla.item(fila, 0).text()
        cuentas = self._repo.listar_cuentas()
        return next((c for c in cuentas if c["codigo"] == codigo), None)

    def _toggle_estado(self) -> None:
        cuenta = self._seleccionada()
        if cuenta is None:
            QMessageBox.information(self, "Aviso", "Seleccione una cuenta contable.")
            return
        nuevo = not cuenta.get("activo", True)
        verbo = "activar" if nuevo else "desactivar"
        if QMessageBox.question(
            self, "Confirmar",
            f"¿Desea {verbo} la cuenta '{cuenta['codigo']} — {cuenta['descripcion']}'?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            session = Session.get_instance()
            ok = self._repo.cambiar_estado_cuenta(cuenta["codigo"], nuevo)
            if ok:
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="cuenta_contable",
                    accion="CAMBIAR_ESTADO", registro_id=None,
                    datos_antes={"codigo": cuenta["codigo"], "activo": cuenta.get("activo")},
                    datos_despues={"codigo": cuenta["codigo"], "activo": nuevo},
                )
                self.cargar_datos()
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
