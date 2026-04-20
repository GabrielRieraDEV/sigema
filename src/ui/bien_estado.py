"""
bien_estado.py — Diálogo de cambio de estado de un bien mueble.

Muestra datos actuales del bien (solo lectura) y permite seleccionar
un nuevo estado (En desuso / Faltante) con motivo obligatorio.
Si el estado es 'Faltante', el campo responsable es obligatorio.
"""
from __future__ import annotations
from typing import Any
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)
from src.core.bien_service import BienService


class BienEstadoDialog(QDialog):
    """Diálogo para cambiar el estado de un bien mueble.

    Parameters
    ----------
    bien_service : BienService
        Servicio de lógica de negocio.
    bien_data : dict
        Datos completos del bien a modificar.
    usuario_id : int
        ID del usuario autenticado.
    """

    def __init__(self, bien_service: BienService, bien_data: dict[str, Any],
                 usuario_id: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = bien_service
        self._bien = bien_data
        self._usuario_id = usuario_id
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle("Cambiar Estado del Bien")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        # --- Datos actuales (solo lectura) ---
        grp_actual = QGroupBox("Datos actuales del bien")
        form_actual = QFormLayout(grp_actual)

        lbl_codigo = QLineEdit(self._bien.get("codigo_activo", ""))
        lbl_codigo.setReadOnly(True)
        form_actual.addRow("Código activo:", lbl_codigo)

        lbl_desc = QLineEdit(self._bien.get("descripcion", "")[:80])
        lbl_desc.setReadOnly(True)
        form_actual.addRow("Descripción:", lbl_desc)

        lbl_dep = QLineEdit(self._bien.get("departamento_nombre", ""))
        lbl_dep.setReadOnly(True)
        form_actual.addRow("Departamento:", lbl_dep)

        lbl_estado = QLineEdit(self._bien.get("estado", ""))
        lbl_estado.setReadOnly(True)
        form_actual.addRow("Estado actual:", lbl_estado)

        layout.addWidget(grp_actual)

        # --- Nuevo estado ---
        grp_nuevo = QGroupBox("Nuevo estado")
        form_nuevo = QFormLayout(grp_nuevo)

        self._cmb_estado = QComboBox()
        self._cmb_estado.addItems(["En desuso", "Faltante"])
        self._cmb_estado.currentTextChanged.connect(self._on_estado_changed)
        form_nuevo.addRow("Nuevo estado:", self._cmb_estado)

        self._txt_motivo = QTextEdit()
        self._txt_motivo.setMaximumHeight(80)
        self._txt_motivo.setPlaceholderText(
            "Motivo del cambio de estado (obligatorio — RN-04)")
        form_nuevo.addRow("Motivo (*):", self._txt_motivo)

        self._lbl_responsable = QLabel("Responsable (*):")
        self._txt_responsable = QLineEdit()
        self._txt_responsable.setPlaceholderText(
            "Nombre del responsable (Concepto 60)")
        form_nuevo.addRow(self._lbl_responsable, self._txt_responsable)

        # Inicialmente ocultar responsable si no es Faltante
        self._on_estado_changed(self._cmb_estado.currentText())

        layout.addWidget(grp_nuevo)

        # --- Botones ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_confirmar = QPushButton("Confirmar")
        btn_confirmar.clicked.connect(self._on_confirmar)
        btn_layout.addWidget(btn_confirmar)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        layout.addLayout(btn_layout)

    def _on_estado_changed(self, estado: str) -> None:
        """Muestra/oculta el campo responsable según el estado."""
        es_faltante = estado == "Faltante"
        self._lbl_responsable.setVisible(es_faltante)
        self._txt_responsable.setVisible(es_faltante)

    def _on_confirmar(self) -> None:
        """Valida y llama a bien_service.actualizar_estado()."""
        nuevo_estado = self._cmb_estado.currentText()
        motivo = self._txt_motivo.toPlainText().strip()
        responsable = self._txt_responsable.text().strip() or None

        # Validación UI
        if not motivo:
            QMessageBox.warning(
                self, "Validación",
                "Debe indicar el motivo del cambio de estado (RN-04).")
            self._txt_motivo.setFocus()
            return

        if nuevo_estado == "Faltante" and not responsable:
            QMessageBox.warning(
                self, "Validación",
                "Debe indicar el responsable del bien faltante (Concepto 60).")
            self._txt_responsable.setFocus()
            return

        ok, mensaje = self._service.actualizar_estado(
            bien_id=self._bien["id"],
            nuevo_estado=nuevo_estado,
            motivo=motivo,
            responsable=responsable,
            usuario_id=self._usuario_id,
        )

        if ok:
            QMessageBox.information(self, "Estado actualizado", mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", mensaje)
