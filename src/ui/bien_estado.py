"""
bien_estado.py — Diálogo de cambio de estado de un bien mueble.

Muestra el estado actual del bien (código + descripción completa, con
indicador de color) y permite seleccionar un nuevo estado entre las
transiciones permitidas según las reglas de :mod:`src.core.estados`:

- 01–04 (operativos): cambian libremente entre sí; sin campos extra.
- 05 / 06 (inoperativos): exigen "Descripción del daño".
- 07 (desincorporado): exige "Motivo de desincorporación".
- 06 solo puede pasar a 07; 07 es terminal.
"""
from __future__ import annotations
from typing import Any
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)
from src.core import estados
from src.core.bien_service import BienService


def _btn_style(color: str, hover: str) -> str:
    return (
        f"QPushButton {{ background:{color}; color:white; font-weight:bold;"
        f" padding:5px 14px; border-radius:4px; }}"
        f"QPushButton:hover {{ background:{hover}; }}"
    )


class BienEstadoDialog(QDialog):
    """Diálogo para cambiar el estado de un bien mueble.

    Parameters
    ----------
    bien_service : BienService
        Servicio de lógica de negocio.
    bien_data : dict
        Datos completos del bien a modificar (incluye ``estado`` como
        código y, opcionalmente, ``estado_descripcion``).
    usuario_id : int
        ID del usuario autenticado.
    """

    def __init__(self, bien_service: BienService, bien_data: dict[str, Any],
                 usuario_id: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._service = bien_service
        self._bien = bien_data
        self._usuario_id = usuario_id
        self._estado_actual = bien_data.get("estado") or ""
        # Mapa código -> descripción (desde catálogo, con respaldo en memoria).
        self._desc_por_codigo = self._cargar_descripciones()
        self._init_ui()

    # ------------------------------------------------------------------
    # Carga de descripciones del catálogo
    # ------------------------------------------------------------------
    def _cargar_descripciones(self) -> dict[str, str]:
        mapa = dict(estados.ESTADOS)
        try:
            for est in self._service.obtener_estados():
                if est.get("codigo"):
                    mapa[est["codigo"]] = est.get("descripcion", "")
        except Exception:
            pass
        return mapa

    def _desc(self, codigo: str | None) -> str:
        if not codigo:
            return ""
        return self._desc_por_codigo.get(codigo, estados.descripcion(codigo))

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        self.setWindowTitle("Cambiar Estado del Bien")
        self.setMinimumWidth(520)
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

        # Estado actual con código + descripción completa y color
        etiqueta_actual = estados.etiqueta(
            self._estado_actual, self._desc(self._estado_actual)
        )
        self._lbl_estado_actual = QLabel(etiqueta_actual or "—")
        self._lbl_estado_actual.setWordWrap(True)
        self._lbl_estado_actual.setStyleSheet(
            f"color:{estados.color_indicador(self._estado_actual)};"
            " font-weight:bold;"
        )
        form_actual.addRow("Estado actual:", self._lbl_estado_actual)

        layout.addWidget(grp_actual)

        # --- Nuevo estado ---
        grp_nuevo = QGroupBox("Nuevo estado")
        form_nuevo = QFormLayout(grp_nuevo)

        self._cmb_estado = QComboBox()
        permitidas = estados.transiciones_permitidas(self._estado_actual)
        for codigo in permitidas:
            self._cmb_estado.addItem(
                estados.etiqueta(codigo, self._desc(codigo)), codigo
            )
        self._cmb_estado.currentIndexChanged.connect(self._on_estado_changed)
        form_nuevo.addRow("Nuevo estado:", self._cmb_estado)

        # Campo: Descripción del daño (estados 05 y 06)
        self._lbl_dano = QLabel("Descripción del daño (*):")
        self._txt_dano = QTextEdit()
        self._txt_dano.setMaximumHeight(80)
        self._txt_dano.setPlaceholderText(
            "Describa el daño del bien (obligatorio para estados 05 y 06)")
        form_nuevo.addRow(self._lbl_dano, self._txt_dano)

        # Campo: Motivo de desincorporación (estado 07)
        self._lbl_motivo = QLabel("Motivo de desincorporación (*):")
        self._txt_motivo = QTextEdit()
        self._txt_motivo.setMaximumHeight(80)
        self._txt_motivo.setPlaceholderText(
            "Indique el motivo de la desincorporación (obligatorio, estado 07)")
        form_nuevo.addRow(self._lbl_motivo, self._txt_motivo)

        layout.addWidget(grp_nuevo)

        # --- Botones ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_confirmar = QPushButton("✔ Confirmar")
        self._btn_confirmar.setStyleSheet(_btn_style("#1B7F3A", "#238C47"))
        self._btn_confirmar.clicked.connect(self._on_confirmar)
        btn_layout.addWidget(self._btn_confirmar)

        btn_cancelar = QPushButton("✖ Cancelar")
        btn_cancelar.setStyleSheet(_btn_style("#CC0000", "#FF3333"))
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        layout.addLayout(btn_layout)

        # Estado terminal / sin transiciones disponibles
        if not permitidas:
            self._cmb_estado.setEnabled(False)
            self._btn_confirmar.setEnabled(False)
            aviso = QLabel(
                "Este bien está en un estado que no admite cambios "
                "(estado terminal o bloqueado)."
            )
            aviso.setWordWrap(True)
            aviso.setStyleSheet("color:#CC0000; font-style:italic;")
            layout.addWidget(aviso)
            self._lbl_dano.setVisible(False)
            self._txt_dano.setVisible(False)
            self._lbl_motivo.setVisible(False)
            self._txt_motivo.setVisible(False)
        else:
            self._on_estado_changed()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_estado_changed(self, *_args) -> None:
        """Muestra/oculta los campos condicionales según el estado destino."""
        nuevo = self._cmb_estado.currentData()
        requiere_dano = nuevo in estados.REQUIERE_DESCRIPCION_DANO
        requiere_motivo = nuevo == estados.REQUIERE_MOTIVO_DESINCORPORACION

        self._lbl_dano.setVisible(requiere_dano)
        self._txt_dano.setVisible(requiere_dano)
        self._lbl_motivo.setVisible(requiere_motivo)
        self._txt_motivo.setVisible(requiere_motivo)

    def _on_confirmar(self) -> None:
        """Valida y llama a bien_service.actualizar_estado()."""
        nuevo_estado = self._cmb_estado.currentData()
        if not nuevo_estado:
            QMessageBox.warning(
                self, "Validación", "Seleccione un nuevo estado.")
            return

        # El "motivo" depende del estado destino
        if nuevo_estado in estados.REQUIERE_DESCRIPCION_DANO:
            detalle = self._txt_dano.toPlainText().strip()
            if not detalle:
                QMessageBox.warning(
                    self, "Validación",
                    "Debe indicar la descripción del daño (estados 05 y 06).")
                self._txt_dano.setFocus()
                return
        elif nuevo_estado == estados.REQUIERE_MOTIVO_DESINCORPORACION:
            detalle = self._txt_motivo.toPlainText().strip()
            if not detalle:
                QMessageBox.warning(
                    self, "Validación",
                    "Debe indicar el motivo de desincorporación (estado 07).")
                self._txt_motivo.setFocus()
                return
        else:
            detalle = None

        ok, mensaje = self._service.actualizar_estado(
            bien_id=self._bien["id"],
            nuevo_estado=nuevo_estado,
            motivo=detalle,
            usuario_id=self._usuario_id,
        )

        if ok:
            QMessageBox.information(self, "Estado actualizado", mensaje)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", mensaje)
