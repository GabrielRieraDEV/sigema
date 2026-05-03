"""
usuarios.py — Gestión de usuarios (Módulo C, §4.3).

Solo visible para el perfil Administrador (RN-11).
Los usuarios nunca se eliminan — solo se activan/desactivan (RN-02).
"""

from __future__ import annotations

import bcrypt
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from src.core.auditoria import registrar_auditoria
from src.core.auth import Session
from src.db.usuario_repository import UsuarioRepository


class UsuariosWidget(QWidget):
    """Panel de gestión de usuarios — solo Administrador."""

    _COLS = ["ID", "Nombre completo", "Cargo", "Username", "Perfil", "Estado"]

    def __init__(self, usuario_repo: UsuarioRepository, parent=None):
        super().__init__(parent)
        self._repo = usuario_repo
        self._setup_ui()
        self.cargar_datos()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self._btn_nuevo = QPushButton("➕  Nuevo usuario")
        self._btn_nuevo.setStyleSheet(self._btn_style("#1B7F3A", "#238C47"))
        self._btn_nuevo.clicked.connect(self._nuevo_usuario)
        toolbar.addWidget(self._btn_nuevo)

        self._btn_editar = QPushButton("✏  Editar")
        self._btn_editar.setStyleSheet(self._btn_style("#1B3A5C", "#245280"))
        self._btn_editar.clicked.connect(self._editar_usuario)
        toolbar.addWidget(self._btn_editar)

        self._btn_toggle = QPushButton("⏸  Activar / Desactivar")
        self._btn_toggle.setStyleSheet(self._btn_style("#8B4513", "#A0522D"))
        self._btn_toggle.clicked.connect(self._toggle_estado)
        toolbar.addWidget(self._btn_toggle)

        toolbar.addStretch()
        btn_refresh = QPushButton("↺ Actualizar")
        btn_refresh.setStyleSheet(self._btn_style("#5C6B73", "#6D7F88"))
        btn_refresh.clicked.connect(self.cargar_datos)
        toolbar.addWidget(btn_refresh)
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
        self._tabla.doubleClicked.connect(self._editar_usuario)
        layout.addWidget(self._tabla)

    @staticmethod
    def _btn_style(color: str, hover: str) -> str:
        return (
            f"QPushButton {{ background:{color}; color:white; font-weight:bold;"
            f" padding:5px 14px; border-radius:4px; }}"
            f"QPushButton:hover {{ background:{hover}; }}"
        )

    def cargar_datos(self) -> None:
        try:
            usuarios = self._repo.listar_todos()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo cargar usuarios:\n{exc}")
            return

        self._tabla.setRowCount(0)
        for u in usuarios:
            row = self._tabla.rowCount()
            self._tabla.insertRow(row)
            items = [
                str(u["id"]),
                f"{u['nombre']} {u['apellido']}",
                u.get("cargo") or "",
                u.get("username") or "",
                u.get("perfil") or "",
                "Activo" if u.get("activo") else "Inactivo",
            ]
            for col, texto in enumerate(items):
                item = QTableWidgetItem(texto)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if texto == "Inactivo":
                    item.setForeground(QColor("#888"))
                self._tabla.setItem(row, col, item)
        self._tabla.resizeColumnsToContents()

    def _usuario_seleccionado(self) -> dict | None:
        fila = self._tabla.currentRow()
        if fila < 0:
            return None
        return self._repo.buscar_por_id(int(self._tabla.item(fila, 0).text()))

    def _nuevo_usuario(self) -> None:
        dlg = UsuarioFormDialog(self._repo, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

    def _editar_usuario(self) -> None:
        usuario = self._usuario_seleccionado()
        if usuario is None:
            QMessageBox.information(self, "Aviso", "Seleccione un usuario para editar.")
            return
        dlg = UsuarioFormDialog(self._repo, usuario=usuario, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.cargar_datos()

    def _toggle_estado(self) -> None:
        usuario = self._usuario_seleccionado()
        if usuario is None:
            QMessageBox.information(self, "Aviso", "Seleccione un usuario para cambiar su estado.")
            return
        session = Session.get_instance()
        if usuario["id"] == session.usuario_id:
            QMessageBox.warning(self, "No permitido", "No puede desactivar su propia cuenta.")
            return
        nuevo_estado = not usuario.get("activo", True)
        verbo = "activar" if nuevo_estado else "desactivar"
        if QMessageBox.question(
            self, "Confirmar", f"¿Desea {verbo} al usuario '{usuario.get('username')}'?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            datos_antes = {k: v for k, v in usuario.items() if k != "password_hash"}
            ok = self._repo.cambiar_estado(usuario["id"], nuevo_estado)
            if ok:
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="usuario",
                    accion="CAMBIAR_ESTADO", registro_id=usuario["id"],
                    datos_antes=datos_antes, datos_despues={"activo": nuevo_estado},
                )
                self.cargar_datos()
            else:
                QMessageBox.warning(self, "Error", "No se pudo cambiar el estado.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))


class UsuarioFormDialog(QDialog):
    """Formulario para crear o editar un usuario."""

    _PERFILES = ["Administrador", "Almacenista", "Consulta"]

    def __init__(self, repo: UsuarioRepository, usuario: dict | None = None, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._usuario = usuario
        self._es_nuevo = usuario is None
        self.setWindowTitle("SIGEMA — " + ("Nuevo usuario" if self._es_nuevo else "Editar usuario"))
        self.setMinimumWidth(440)
        self._setup_ui()
        if not self._es_nuevo:
            self._cargar_datos()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        grp = QGroupBox("Datos del usuario")
        form = QFormLayout(grp)
        form.setSpacing(10)

        self._nombre_edit = QLineEdit()
        form.addRow("Nombre *:", self._nombre_edit)

        self._apellido_edit = QLineEdit()
        form.addRow("Apellido *:", self._apellido_edit)

        self._cargo_edit = QLineEdit()
        form.addRow("Cargo:", self._cargo_edit)

        self._username_edit = QLineEdit()
        form.addRow("Username *:", self._username_edit)

        self._perfil_combo = QComboBox()
        self._perfil_combo.addItems(self._PERFILES)
        form.addRow("Perfil *:", self._perfil_combo)

        self._pass_edit = QLineEdit()
        self._pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        if not self._es_nuevo:
            self._pass_edit.setPlaceholderText("Dejar vacío para no cambiar")
        form.addRow("Contraseña *:" if self._es_nuevo else "Nueva contraseña:", self._pass_edit)

        self._pass2_edit = QLineEdit()
        self._pass2_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Confirmar contraseña *:" if self._es_nuevo else "Confirmar:", self._pass2_edit)

        self._activo_check = QCheckBox("Usuario activo")
        self._activo_check.setChecked(True)
        form.addRow("Estado:", self._activo_check)
        root.addWidget(grp)

        self._error_lbl = QLabel("")
        self._error_lbl.setWordWrap(True)
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
        u = self._usuario
        self._nombre_edit.setText(u.get("nombre", ""))
        self._apellido_edit.setText(u.get("apellido", ""))
        self._cargo_edit.setText(u.get("cargo") or "")
        self._username_edit.setText(u.get("username", ""))
        idx = self._perfil_combo.findText(u.get("perfil", ""))
        if idx >= 0:
            self._perfil_combo.setCurrentIndex(idx)
        self._activo_check.setChecked(bool(u.get("activo", True)))

    def _guardar(self) -> None:
        session = Session.get_instance()
        nombre = self._nombre_edit.text().strip()
        apellido = self._apellido_edit.text().strip()
        cargo = self._cargo_edit.text().strip()
        username = self._username_edit.text().strip()
        perfil = self._perfil_combo.currentText()
        activo = self._activo_check.isChecked()
        password = self._pass_edit.text()
        password2 = self._pass2_edit.text()

        if not nombre:
            return self._error_lbl.setText("⚠ El nombre es obligatorio.")
        if not apellido:
            return self._error_lbl.setText("⚠ El apellido es obligatorio.")
        if not username:
            return self._error_lbl.setText("⚠ El username es obligatorio.")
        if self._es_nuevo and not password:
            return self._error_lbl.setText("⚠ La contraseña es obligatoria.")
        if password and password != password2:
            self._pass_edit.clear(); self._pass2_edit.clear()
            return self._error_lbl.setText("⚠ Las contraseñas no coinciden.")
        if password and len(password) < 6:
            return self._error_lbl.setText("⚠ La contraseña debe tener al menos 6 caracteres.")

        excluir_id = self._usuario["id"] if not self._es_nuevo else None
        if self._repo.username_existe(username, excluir_id=excluir_id):
            return self._error_lbl.setText("⚠ El username ya está en uso.")

        datos: dict = {
            "nombre": nombre, "apellido": apellido,
            "cargo": cargo or None, "username": username,
            "perfil": perfil, "activo": activo,
        }
        if password:
            datos["password_hash"] = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

        try:
            if self._es_nuevo:
                nuevo_id = self._repo.crear(datos)
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="usuario", accion="CREAR",
                    registro_id=nuevo_id,
                    datos_despues={k: v for k, v in datos.items() if k != "password_hash"},
                )
            else:
                datos_antes = {k: v for k, v in self._usuario.items() if k != "password_hash"}
                self._repo.actualizar(self._usuario["id"], datos)
                registrar_auditoria(
                    usuario_id=session.usuario_id, tabla="usuario", accion="ACTUALIZAR",
                    registro_id=self._usuario["id"], datos_antes=datos_antes,
                    datos_despues={k: v for k, v in datos.items() if k != "password_hash"},
                )
            self.accept()
        except Exception as exc:
            self._error_lbl.setText(f"⚠ Error al guardar: {exc}")
