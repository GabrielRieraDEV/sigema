"""
migracion_panel.py — Panel de migración de datos del sistema anterior.

Flujo:
  1. Seleccionar archivo (CSV / Excel / JSON).
  2. Validar → muestra total, válidos y errores con detalle.
  3. Ejecutar migración (solo si hay válidos) con barra de progreso.
  4. Al finalizar, resumen y descarga del reporte de errores (si los hubo).

Es una herramienta de administrador: inserta directamente en la tabla
``bien``.  Cada inserción queda auditada.
"""

from __future__ import annotations

import os
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.migracion import Migrador
from src.db.connection import DBConnection


def _btn_style(color: str, hover: str) -> str:
    return (
        f"QPushButton {{ background:{color}; color:white; font-weight:bold;"
        f" padding:6px 16px; border-radius:4px; }}"
        f"QPushButton:hover {{ background:{hover}; }}"
        f"QPushButton:disabled {{ background:#B8C0C7; color:#EEE; }}"
    )


class MigracionPanelWidget(QWidget):
    """Asistente de migración de datos del sistema anterior."""

    def __init__(
        self,
        db: DBConnection,
        usuario_id: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._migrador = Migrador(db, usuario_id)
        self._usuario_id = usuario_id

        self._ruta: str | None = None
        self._registros: list[dict] = []
        self._validos: list[dict] = []
        self._errores: list[dict] = []          # validación + inserción

        self._init_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        intro = QLabel(
            "<b>Migración de datos del sistema anterior</b><br>"
            "Seleccione el archivo del sistema anterior FoxPro (.dbf) — "
            "también acepta CSV/Excel/JSON —, valide su contenido y ejecute "
            "la migración. Los bienes se insertan con "
            "estado <b>01 (Operativo, en uso)</b> y origen <b>Compra</b>, "
            "preservando el código original."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # --- Selección de archivo ---
        grp_archivo = QGroupBox("1. Archivo de origen")
        h_arch = QHBoxLayout(grp_archivo)
        self._lbl_ruta = QLabel("Ningún archivo seleccionado.")
        self._lbl_ruta.setStyleSheet("color:#555;")
        h_arch.addWidget(self._lbl_ruta, stretch=1)
        btn_sel = QPushButton("📂 Seleccionar archivo")
        btn_sel.setStyleSheet(_btn_style("#1B3A5C", "#245280"))
        btn_sel.clicked.connect(self._on_seleccionar)
        h_arch.addWidget(btn_sel)
        layout.addWidget(grp_archivo)

        # --- Acciones ---
        h_acc = QHBoxLayout()
        self._btn_validar = QPushButton("✓ Validar")
        self._btn_validar.setStyleSheet(_btn_style("#1B3A5C", "#245280"))
        self._btn_validar.clicked.connect(self._on_validar)
        self._btn_validar.setEnabled(False)
        h_acc.addWidget(self._btn_validar)

        self._btn_migrar = QPushButton("⏩ Ejecutar migración")
        self._btn_migrar.setStyleSheet(_btn_style("#1B7F3A", "#238C47"))
        self._btn_migrar.clicked.connect(self._on_migrar)
        self._btn_migrar.setEnabled(False)
        h_acc.addWidget(self._btn_migrar)

        h_acc.addStretch()

        self._btn_reporte = QPushButton("📄 Descargar reporte de errores")
        self._btn_reporte.setStyleSheet(_btn_style("#8B4513", "#A0522D"))
        self._btn_reporte.clicked.connect(self._on_descargar_reporte)
        self._btn_reporte.setEnabled(False)
        h_acc.addWidget(self._btn_reporte)
        layout.addLayout(h_acc)

        # --- Progreso ---
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # --- Resumen / detalle ---
        grp_res = QGroupBox("Resumen")
        v_res = QVBoxLayout(grp_res)
        self._txt_resumen = QTextEdit()
        self._txt_resumen.setReadOnly(True)
        v_res.addWidget(self._txt_resumen)
        layout.addWidget(grp_res, stretch=1)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_seleccionar(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo del sistema anterior",
            "",
            "FoxPro/dBASE (*.dbf);;Datos (*.dbf *.csv *.xlsx *.xlsm *.json)"
            ";;Todos los archivos (*.*)",
        )
        if not ruta:
            return
        self._ruta = ruta
        self._lbl_ruta.setText(ruta)
        self._registros = []
        self._validos = []
        self._errores = []
        self._btn_validar.setEnabled(True)
        self._btn_migrar.setEnabled(False)
        self._btn_reporte.setEnabled(False)
        self._txt_resumen.clear()
        self._progress.setVisible(False)

    def _on_validar(self) -> None:
        if not self._ruta:
            return
        try:
            self._registros = self._migrador.leer_archivo(self._ruta)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error al leer", f"No se pudo leer el archivo:\n{exc}")
            return

        if not self._registros:
            QMessageBox.warning(
                self, "Sin datos",
                "El archivo no contiene registros legibles.")
            return

        self._validos, self._errores = self._migrador.validar_todos(
            self._registros)

        total = len(self._registros)
        n_val = len(self._validos)
        n_err_reg = total - n_val

        partes = [
            f"<b>Total de registros encontrados:</b> {total}",
            f"<b>Registros válidos para migrar:</b> "
            f"<span style='color:#1B7F3A;'>{n_val}</span>",
            f"<b>Registros con errores:</b> "
            f"<span style='color:#CC0000;'>{n_err_reg}</span>",
        ]
        if self._errores:
            partes.append("<br><b>Detalle de errores:</b>")
            for e in self._errores[:200]:
                partes.append(
                    f"&nbsp;&nbsp;• Fila {e['fila']} — "
                    f"{e['campo']}: {e['motivo_error']}")
            if len(self._errores) > 200:
                partes.append(
                    f"&nbsp;&nbsp;… y {len(self._errores) - 200} más "
                    "(ver reporte CSV).")
        self._txt_resumen.setHtml("<br>".join(partes))

        self._btn_migrar.setEnabled(n_val > 0)
        self._btn_reporte.setEnabled(bool(self._errores))

    def _on_migrar(self) -> None:
        if not self._validos:
            return
        resp = QMessageBox.question(
            self,
            "Confirmar migración",
            f"Se insertarán {len(self._validos)} bienes en el sistema.\n"
            "Esta acción queda registrada en auditoría.\n\n¿Desea continuar?",
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self._btn_migrar.setEnabled(False)
        self._btn_validar.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, len(self._validos))
        self._progress.setValue(0)

        def _progreso(done: int, total: int) -> None:
            self._progress.setValue(done)
            QApplication.processEvents()

        try:
            resultado = self._migrador.migrar(
                self._validos, self._usuario_id, progreso=_progreso)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error en migración",
                f"La migración falló:\n{exc}")
            self._btn_validar.setEnabled(True)
            return

        # Combinar errores de validación + de inserción para el reporte.
        errores_insercion = resultado.get("errores", [])
        self._errores = self._errores + errores_insercion

        resumen = [
            "<b>Migración finalizada.</b>",
            f"<b>Insertados correctamente:</b> "
            f"<span style='color:#1B7F3A;'>{resultado['insertados']}</span>",
            f"<b>Fallidos en inserción:</b> "
            f"<span style='color:#CC0000;'>{resultado['fallidos']}</span>",
        ]
        if errores_insercion:
            resumen.append("<br><b>Errores de inserción:</b>")
            for e in errores_insercion[:100]:
                resumen.append(
                    f"&nbsp;&nbsp;• Fila {e['fila']}: {e['motivo_error']}")
        self._txt_resumen.setHtml("<br>".join(resumen))

        self._btn_reporte.setEnabled(bool(self._errores))
        QMessageBox.information(
            self, "Migración completada",
            f"Se insertaron {resultado['insertados']} de "
            f"{resultado['total']} registros.")

    def _on_descargar_reporte(self) -> None:
        if not self._errores:
            QMessageBox.information(
                self, "Sin errores", "No hay errores para reportar.")
            return
        try:
            temp = self._migrador.generar_reporte_errores(self._errores)
        except Exception as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudo generar el reporte:\n{exc}")
            return

        destino, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar reporte de errores",
            "migracion_errores.csv",
            "Archivos CSV (*.csv)",
        )
        if not destino:
            return
        try:
            shutil.copyfile(temp, destino)
            QMessageBox.information(
                self, "Reporte guardado",
                f"Reporte de errores guardado en:\n{destino}")
            if hasattr(os, "startfile"):
                os.startfile(destino)  # type: ignore[attr-defined]
        except OSError as exc:
            QMessageBox.critical(
                self, "Error", f"No se pudo guardar el reporte:\n{exc}")
