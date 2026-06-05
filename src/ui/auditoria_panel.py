"""
auditoria_panel.py — Panel de consulta del log de auditoría (Módulo D, §4.4).

Solo visible para el perfil Administrador.
El log es inmutable: solo lectura y exportación a CSV.
"""

from __future__ import annotations

import csv
import os
from datetime import date

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.db.auditoria_repository import AuditoriaRepository


class AuditoriaPanelWidget(QWidget):
    """Panel de auditoría con filtros y exportación CSV."""

    _COLS = ["ID", "Fecha / Hora", "Usuario", "Acción", "Tabla", "Registro ID", "IP origen"]

    # Acciones conocidas del sistema (código en BD -> etiqueta legible).
    # Siempre se ofrecen en el combo, aunque todavía no estén en el log.
    _ACCIONES_CONOCIDAS = [
        ("CREAR", "Crear"),
        ("ACTUALIZAR", "Actualizar"),
        ("ACTUALIZAR_ESTADO", "Actualizar estado"),
        ("CAMBIAR_ESTADO", "Cambiar estado (activar/desactivar)"),
    ]

    def __init__(self, auditoria_repo: AuditoriaRepository, parent=None):
        super().__init__(parent)
        self._repo = auditoria_repo
        self._setup_ui()
        self.buscar()  # Carga inicial con datos recientes

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Filtros ──────────────────────────────────────────────────────
        grp_filtros = QGroupBox("Filtros de búsqueda")
        filtros_layout = QHBoxLayout(grp_filtros)
        filtros_layout.setSpacing(10)

        filtros_layout.addWidget(QLabel("Usuario:"))
        self._combo_usuario = QComboBox()
        self._combo_usuario.setMinimumWidth(160)
        self._combo_usuario.addItem("— Todos —", None)
        self._cargar_usuarios_combo()
        filtros_layout.addWidget(self._combo_usuario)

        filtros_layout.addWidget(QLabel("Desde:"))
        self._fecha_desde = QDateEdit()
        self._fecha_desde.setDisplayFormat("dd/MM/yyyy")
        self._fecha_desde.setCalendarPopup(True)
        self._fecha_desde.setDate(QDate.currentDate().addDays(-30))
        filtros_layout.addWidget(self._fecha_desde)

        filtros_layout.addWidget(QLabel("Hasta:"))
        self._fecha_hasta = QDateEdit()
        self._fecha_hasta.setDisplayFormat("dd/MM/yyyy")
        self._fecha_hasta.setCalendarPopup(True)
        self._fecha_hasta.setDate(QDate.currentDate())
        filtros_layout.addWidget(self._fecha_hasta)

        filtros_layout.addWidget(QLabel("Acción:"))
        self._combo_accion = QComboBox()
        self._combo_accion.setMinimumWidth(130)
        self._combo_accion.addItem("— Todas —", None)
        self._cargar_acciones_combo()
        filtros_layout.addWidget(self._combo_accion)

        filtros_layout.addStretch()

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.setStyleSheet(
            "QPushButton { background:#1B3A5C; color:white; font-weight:bold;"
            " padding:5px 14px; border-radius:4px; }"
            "QPushButton:hover { background:#245280; }"
        )
        btn_buscar.clicked.connect(self.buscar)
        filtros_layout.addWidget(btn_buscar)

        btn_actualizar = QPushButton("🔄 Actualizar")
        btn_actualizar.setStyleSheet(
            "QPushButton { background:#6c757d; color:white; font-weight:bold;"
            " padding:5px 14px; border-radius:4px; }"
            "QPushButton:hover { background:#5a6268; }"
        )
        btn_actualizar.clicked.connect(self.buscar)
        filtros_layout.addWidget(btn_actualizar)

        btn_csv = QPushButton("📄 Exportar CSV")
        btn_csv.setStyleSheet(
            "QPushButton { background:#1B7F3A; color:white; font-weight:bold;"
            " padding:5px 14px; border-radius:4px; }"
            "QPushButton:hover { background:#238C47; }"
        )
        btn_csv.clicked.connect(self._exportar_csv)
        filtros_layout.addWidget(btn_csv)

        layout.addWidget(grp_filtros)

        # ── Contador de resultados ───────────────────────────────────────
        self._count_lbl = QLabel("Sin resultados")
        self._count_lbl.setStyleSheet("font-size:11px; color:#555;")
        layout.addWidget(self._count_lbl)

        # ── Tabla ────────────────────────────────────────────────────────
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self._COLS))
        self._tabla.setHorizontalHeaderLabels(self._COLS)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        header = self._tabla.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Fecha/Hora
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Usuario
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Acción
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)           # Tabla
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Registro ID
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # IP origen
        self._tabla.setColumnHidden(0, True)  # ID oculto
        layout.addWidget(self._tabla)

    # ------------------------------------------------------------------
    # Carga de combos
    # ------------------------------------------------------------------
    def _cargar_usuarios_combo(self) -> None:
        try:
            usuarios = self._repo.listar_usuarios_auditados()
            for u in usuarios:
                self._combo_usuario.addItem(
                    f"{u['nombre_completo']} ({u['username']})", u["id"]
                )
        except Exception:
            pass

    def _cargar_acciones_combo(self) -> None:
        vistos: set[str] = set()
        # 1. Acciones conocidas del sistema (siempre seleccionables).
        for codigo, etiqueta in self._ACCIONES_CONOCIDAS:
            self._combo_accion.addItem(etiqueta, codigo)
            vistos.add(codigo)
        # 2. Cualquier otra acción presente en el log que no esté en la lista.
        try:
            for a in self._repo.listar_acciones_distintas():
                if a and a not in vistos:
                    self._combo_accion.addItem(a, a)
                    vistos.add(a)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Búsqueda
    # ------------------------------------------------------------------
    def buscar(self) -> None:
        """Ejecuta la búsqueda con los filtros actuales."""
        usuario_id = self._combo_usuario.currentData()
        fecha_desde = self._fecha_desde.date().toPyDate()
        fecha_hasta = self._fecha_hasta.date().toPyDate()
        accion = self._combo_accion.currentData()

        if fecha_desde > fecha_hasta:
            QMessageBox.warning(
                self, "Fechas inválidas",
                "La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'."
            )
            return

        try:
            registros = self._repo.listar_con_filtros(
                usuario_id=usuario_id,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                accion=accion,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo consultar auditoría:\n{exc}")
            return

        self._poblar_tabla(registros)

        n = len(registros)
        self._count_lbl.setText(
            f"{n} registro{'s' if n != 1 else ''} encontrado{'s' if n != 1 else ''}."
            + (" (máx. 500 — use filtros para acotar)" if n == 500 else "")
        )

    def _poblar_tabla(self, registros: list[dict]) -> None:
        self._tabla.setRowCount(0)
        for r in registros:
            row = self._tabla.rowCount()
            self._tabla.insertRow(row)

            fecha_str = ""
            if r.get("fecha_hora"):
                try:
                    fecha_str = r["fecha_hora"].strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    fecha_str = str(r["fecha_hora"])

            nombre_usuario = (
                f"{r.get('usuario_nombre', '')} "
                f"({r.get('usuario_username', '')})"
            ).strip()

            items = [
                str(r.get("id", "")),
                fecha_str,
                nombre_usuario,
                r.get("accion", ""),
                r.get("tabla_afectada", ""),
                str(r.get("registro_id", "")) if r.get("registro_id") is not None else "—",
                r.get("ip_origen", ""),
            ]
            for col, txt in enumerate(items):
                item = QTableWidgetItem(txt)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._tabla.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Exportar CSV (para contraloría interna)
    # ------------------------------------------------------------------
    def _exportar_csv(self) -> None:
        if self._tabla.rowCount() == 0:
            QMessageBox.information(
                self, "Sin datos",
                "No hay registros para exportar. Realice una búsqueda primero."
            )
            return

        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar auditoría a CSV",
            os.path.expanduser("~/auditoria_sigema.csv"),
            "Archivo CSV (*.csv)",
        )
        if not ruta:
            return

        # Columnas visibles (excluir col 0 = ID oculto)
        cabeceras = ["Fecha / Hora", "Usuario", "Acción", "Tabla", "Registro ID", "IP origen"]

        try:
            with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
                # utf-8-sig agrega el BOM para que Excel lo abra correctamente
                writer = csv.writer(f, delimiter=";")
                writer.writerow(cabeceras)
                for row in range(self._tabla.rowCount()):
                    fila = []
                    for col in range(1, len(self._COLS)):  # Saltar col 0 (ID)
                        item = self._tabla.item(row, col)
                        fila.append(item.text() if item else "")
                    writer.writerow(fila)

            QMessageBox.information(
                self,
                "Exportación exitosa",
                f"Archivo exportado correctamente:\n{ruta}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "Error al exportar", f"No se pudo guardar el archivo:\n{exc}"
            )
