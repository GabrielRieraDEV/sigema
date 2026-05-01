"""
formularios_bm.py — Pantalla de generación y gestión de formularios BM.

Widget PyQt6 con:
- Sección de generación: tipo BM, período, departamento, concepto
- Botones: Generar PDF, Imprimir
- Tabla de historial de formularios emitidos con estado
- Botón de anulación (RN-09)
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.formulario_bm_service import FormularioBMService


class FormulariosBMWidget(QWidget):
    """Widget principal del módulo Formularios BM.

    Permite generar formularios BM-1 al BM-4 en PDF, enviarlos a
    impresión, y gestionar el historial de formularios emitidos.
    """

    _TIPOS_BM = ["BM-1", "BM-2", "BM-3", "BM-4"]

    _COLUMNAS_HISTORIAL = [
        "ID",
        "Tipo",
        "Fecha Generación",
        "Generado por",
        "Estado",
        "Motivo Anulación",
    ]

    _CONCEPTOS = [
        "Todos",
        "Incorporación",
        "Desincorporación",
    ]

    def __init__(
        self,
        bm_service: FormularioBMService,
        usuario_id: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._service = bm_service
        self._usuario_id = usuario_id
        self._historial: list[dict] = []
        self._ultimo_pdf: bytes | None = None

        self._init_ui()
        self._cargar_departamentos()
        self._actualizar_historial()
        self._on_tipo_cambiado()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- Sección de generación ---
        layout.addWidget(self._crear_seccion_generacion())

        # --- Tabla de historial ---
        grp_hist = QGroupBox("Historial de formularios emitidos")
        hist_layout = QVBoxLayout(grp_hist)

        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self._COLUMNAS_HISTORIAL))
        self._tabla.setHorizontalHeaderLabels(self._COLUMNAS_HISTORIAL)
        self._tabla.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._tabla.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._tabla.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._tabla.setAlternatingRowColors(True)

        header = self._tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        hist_layout.addWidget(self._tabla)

        # Botones del historial
        btn_hist_layout = QHBoxLayout()
        btn_hist_layout.addStretch()

        self._btn_anular = QPushButton("Anular Formulario")
        self._btn_anular.clicked.connect(self._on_anular)
        btn_hist_layout.addWidget(self._btn_anular)

        btn_descargar = QPushButton("Ver / Descargar PDF")
        btn_descargar.clicked.connect(self._on_descargar_pdf)
        btn_hist_layout.addWidget(btn_descargar)

        btn_actualizar = QPushButton("Actualizar")
        btn_actualizar.clicked.connect(self._actualizar_historial)
        btn_hist_layout.addWidget(btn_actualizar)

        hist_layout.addLayout(btn_hist_layout)
        layout.addWidget(grp_hist)

    def _crear_seccion_generacion(self) -> QGroupBox:
        """Crea la sección de parámetros para generar un formulario."""
        grp = QGroupBox("Generar formulario BM")
        layout = QVBoxLayout(grp)

        # Fila 1: Tipo + Departamento
        fila1 = QHBoxLayout()

        fila1.addWidget(QLabel("Tipo:"))
        self._cmb_tipo = QComboBox()
        self._cmb_tipo.addItems(self._TIPOS_BM)
        self._cmb_tipo.currentIndexChanged.connect(self._on_tipo_cambiado)
        self._cmb_tipo.setMinimumWidth(100)
        fila1.addWidget(self._cmb_tipo)

        fila1.addWidget(QLabel("Departamento:"))
        self._cmb_departamento = QComboBox()
        self._cmb_departamento.setMinimumWidth(200)
        fila1.addWidget(self._cmb_departamento)

        fila1.addStretch()
        layout.addLayout(fila1)

        # Fila 2: Período + Concepto
        fila2 = QHBoxLayout()

        self._lbl_mes = QLabel("Mes:")
        fila2.addWidget(self._lbl_mes)
        self._spn_mes = QSpinBox()
        self._spn_mes.setMinimum(1)
        self._spn_mes.setMaximum(12)
        self._spn_mes.setValue(QDate.currentDate().month())
        fila2.addWidget(self._spn_mes)

        self._lbl_anio = QLabel("Año:")
        fila2.addWidget(self._lbl_anio)
        self._spn_anio = QSpinBox()
        self._spn_anio.setMinimum(2000)
        self._spn_anio.setMaximum(2099)
        self._spn_anio.setValue(QDate.currentDate().year())
        fila2.addWidget(self._spn_anio)

        self._lbl_concepto = QLabel("Concepto:")
        fila2.addWidget(self._lbl_concepto)
        self._cmb_concepto = QComboBox()
        self._cmb_concepto.addItems(self._CONCEPTOS)
        self._cmb_concepto.setMinimumWidth(150)
        fila2.addWidget(self._cmb_concepto)

        fila2.addStretch()
        layout.addLayout(fila2)

        # Fila 3: Botones de acción
        fila3 = QHBoxLayout()
        fila3.addStretch()

        btn_generar = QPushButton("Generar PDF")
        btn_generar.clicked.connect(self._on_generar_pdf)
        fila3.addWidget(btn_generar)

        btn_imprimir = QPushButton("Imprimir")
        btn_imprimir.clicked.connect(self._on_imprimir)
        fila3.addWidget(btn_imprimir)

        layout.addLayout(fila3)

        return grp

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------
    def _cargar_departamentos(self) -> None:
        """Carga los departamentos en el combo respetando jerarquía."""
        self._cmb_departamento.clear()
        try:
            deps = self._service.obtener_departamentos()
            padres = [d for d in deps if not d.get("parent_id")]
            hijos = [d for d in deps if d.get("parent_id")]
            
            for p in padres:
                self._cmb_departamento.addItem(p["nombre"], p["id"])
                for h in hijos:
                    if h["parent_id"] == p["id"]:
                        self._cmb_departamento.addItem("  └─ " + h["nombre"], h["id"])
        except Exception:
            pass

    def _actualizar_historial(self) -> None:
        """Recarga la tabla de historial desde la BD."""
        try:
            tipo_filtro = None  # mostrar todos
            self._historial = self._service.listar_formularios(tipo_filtro)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo cargar el historial:\n{exc}",
            )
            self._historial = []

        self._poblar_historial()

    def _poblar_historial(self) -> None:
        """Llena la tabla con los datos del historial."""
        self._tabla.setRowCount(0)

        for fila, form in enumerate(self._historial):
            self._tabla.insertRow(fila)

            items = [
                str(form.get("id", "")),
                form.get("tipo_bm", ""),
                str(form.get("fecha_generacion", ""))[:19],
                form.get("generado_por_nombre", ""),
                form.get("estado", ""),
                form.get("motivo_anulacion", "") or "",
            ]

            for col, texto in enumerate(items):
                item = QTableWidgetItem(texto)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._tabla.setItem(fila, col, item)

    # ------------------------------------------------------------------
    # Visibilidad condicional de campos
    # ------------------------------------------------------------------
    def _on_tipo_cambiado(self) -> None:
        """Muestra/oculta campos según el tipo de formulario seleccionado."""
        tipo = self._cmb_tipo.currentText()

        # Período: visible para BM-2, BM-3, BM-4
        necesita_periodo = tipo in ("BM-2", "BM-4")
        self._lbl_mes.setVisible(necesita_periodo)
        self._spn_mes.setVisible(necesita_periodo)
        self._lbl_anio.setVisible(necesita_periodo)
        self._spn_anio.setVisible(necesita_periodo)

        # Concepto: solo visible para BM-2
        necesita_concepto = tipo == "BM-2"
        self._lbl_concepto.setVisible(necesita_concepto)
        self._cmb_concepto.setVisible(necesita_concepto)

    # ------------------------------------------------------------------
    # Generación de PDF
    # ------------------------------------------------------------------
    def _on_generar_pdf(self) -> None:
        """Genera el formulario seleccionado y abre diálogo para guardar."""
        tipo = self._cmb_tipo.currentText()
        dept_id = self._cmb_departamento.currentData()

        if dept_id is None:
            QMessageBox.warning(
                self, "Validación", "Seleccione un departamento."
            )
            return

        # Llamar al servicio según el tipo
        ok, mensaje, pdf_bytes, parametros = self._generar_segun_tipo(tipo, dept_id)

        if not ok or pdf_bytes is None or parametros is None:
            QMessageBox.warning(self, "Error", mensaje)
            return

        self._ultimo_pdf = pdf_bytes

        # Vista Previa (Guardar en temporal y abrir)
        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", delete=False, prefix="sigema_preview_"
            )
            tmp.write(pdf_bytes)
            tmp.close()

            # En Windows, abrir el archivo
            if hasattr(os, 'startfile'):
                os.startfile(tmp.name)  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", tmp.name], check=True)

            # Pedir confirmación (RN-09)
            respuesta = QMessageBox.question(
                self,
                "Confirmar Emisión",
                f"Se ha abierto una vista previa del documento en su visor de PDF.\n\n¿Desea GUARDAR Y EMITIR permanentemente este formulario {tipo}?\n(RN-09: Esta acción es irreversible)",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )

            if respuesta == QMessageBox.StandardButton.Save:
                guardado, msg_guardado = self._service.guardar_formulario(tipo, self._usuario_id, parametros, pdf_bytes)
                if guardado:
                    QMessageBox.information(self, "Emitido", msg_guardado)
                else:
                    QMessageBox.warning(self, "Error al guardar", msg_guardado)
            else:
                QMessageBox.information(self, "Cancelado", "El formulario no ha sido guardado ni emitido.")

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Vista previa",
                f"No se pudo abrir la vista previa:\n{exc}",
            )

        self._actualizar_historial()

    def _generar_segun_tipo(
        self, tipo: str, dept_id: int
    ) -> tuple[bool, str, bytes | None, dict[str, Any] | None]:
        """Despacha la generación al método correcto del servicio."""
        if tipo == "BM-1":
            return self._service.generar_bm1(dept_id, self._usuario_id)

        elif tipo == "BM-2":
            mes = self._spn_mes.value()
            anio = self._spn_anio.value()
            concepto_txt = self._cmb_concepto.currentText()
            concepto = concepto_txt if concepto_txt != "Todos" else None
            return self._service.generar_bm2(
                dept_id, mes, anio, concepto, self._usuario_id
            )

        elif tipo == "BM-3":
            return self._service.generar_bm3(dept_id, self._usuario_id)

        elif tipo == "BM-4":
            mes = self._spn_mes.value()
            anio = self._spn_anio.value()
            return self._service.generar_bm4(
                dept_id, mes, anio, self._usuario_id
            )

        return (False, f"Tipo de formulario '{tipo}' no reconocido.", None, None)

    # ------------------------------------------------------------------
    # Impresión directa
    # ------------------------------------------------------------------
    def _on_imprimir(self) -> None:
        """Genera el PDF e intenta enviarlo a la impresora del sistema."""
        tipo = self._cmb_tipo.currentText()
        dept_id = self._cmb_departamento.currentData()

        if dept_id is None:
            QMessageBox.warning(
                self, "Validación", "Seleccione un departamento."
            )
            return

        ok, mensaje, pdf_bytes, parametros = self._generar_segun_tipo(tipo, dept_id)

        if not ok:
            QMessageBox.warning(self, "Error", mensaje)
            return

        # Guardar en temporal y enviar a impresora
        try:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pdf", delete=False, prefix="sigema_"
            )
            tmp.write(pdf_bytes)
            tmp.close()

            # En Windows, usar el comando de impresión del sistema
            os.startfile(tmp.name, "print")  # type: ignore[attr-defined]

            # Pedir confirmación (RN-09)
            respuesta = QMessageBox.question(
                self,
                "Confirmar Emisión",
                f"El documento ha sido enviado a la impresora.\n\n¿Desea GUARDAR Y EMITIR permanentemente este formulario {tipo}?\n(RN-09: Esta acción es irreversible)",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )

            if respuesta == QMessageBox.StandardButton.Save:
                guardado, msg_guardado = self._service.guardar_formulario(tipo, self._usuario_id, parametros, pdf_bytes) # type: ignore
                if guardado:
                    QMessageBox.information(self, "Emitido", msg_guardado)
                else:
                    QMessageBox.warning(self, "Error al guardar", msg_guardado)
            else:
                QMessageBox.information(self, "Cancelado", "El formulario no ha sido guardado ni emitido.")
        except AttributeError:
            # Si no estamos en Windows, intentar con lpr
            try:
                subprocess.run(["lpr", tmp.name], check=True)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Impresión",
                    f"No se pudo imprimir automáticamente:\n{exc}\n\n"
                    "Genere el PDF y abra el archivo para imprimir.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error de impresión",
                f"Error al enviar a impresora:\n{exc}",
            )

        self._actualizar_historial()

    # ------------------------------------------------------------------
    # Anulación de formularios (RN-09)
    # ------------------------------------------------------------------
    def _on_anular(self) -> None:
        """Anula el formulario seleccionado pidiendo justificación."""
        fila = self._tabla.currentRow()
        if fila < 0 or fila >= len(self._historial):
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Seleccione un formulario de la tabla.",
            )
            return

        formulario = self._historial[fila]

        if formulario.get("estado") == "Anulado":
            QMessageBox.information(
                self,
                "Ya anulado",
                "Este formulario ya se encuentra anulado.",
            )
            return

        # Pedir justificación
        motivo, ok = QInputDialog.getMultiLineText(
            self,
            "Anular formulario",
            f"Indique el motivo de anulación del formulario "
            f"{formulario.get('tipo_bm', '')} #{formulario.get('id', '')}:"
            f"\n\n(RN-09: Esta acción es irreversible)",
        )

        if not ok or not motivo.strip():
            return

        resultado, mensaje = self._service.anular_formulario(
            formulario["id"], motivo.strip()
        )

        if resultado:
            QMessageBox.information(self, "Anulado", mensaje)
        else:
            QMessageBox.warning(self, "Error", mensaje)

        self._actualizar_historial()

    # ------------------------------------------------------------------
    # Descargar del historial
    # ------------------------------------------------------------------
    def _on_descargar_pdf(self) -> None:
        """Descarga el PDF histórico guardado en la base de datos."""
        fila = self._tabla.currentRow()
        if fila < 0 or fila >= len(self._historial):
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Seleccione un formulario de la tabla.",
            )
            return

        formulario = self._historial[fila]
        form_id = formulario.get("id")
        
        pdf_bytes = self._service.obtener_pdf_por_id(form_id)
        if not pdf_bytes:
            QMessageBox.information(
                self,
                "PDF No Disponible",
                "El PDF de este formulario no está disponible en la base de datos.\n"
                "(Probablemente fue generado antes de implementar esta función).",
            )
            return

        tipo = formulario.get("tipo_bm", "BM")
        nombre_default = f"{tipo.replace('-', '')}_historial_{form_id}.pdf"
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar formulario BM Histórico",
            nombre_default,
            "Archivos PDF (*.pdf)",
        )

        if filepath:
            try:
                with open(filepath, "wb") as f:
                    f.write(pdf_bytes)
                
                # Intentar abrir la vista previa
                if hasattr(os, 'startfile'):
                    os.startfile(filepath)  # type: ignore[attr-defined]
                else:
                    subprocess.run(["xdg-open", filepath], check=True)

            except IOError as exc:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"No se pudo guardar el archivo:\n{exc}",
                )

