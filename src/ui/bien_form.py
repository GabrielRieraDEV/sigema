"""
bien_form.py — Formulario de registro / visualización de un bien mueble.

Modo 'nuevo': campos vacíos y editables.  Modo 'ver': campos precargados solo lectura.
Combos cargados desde BD: categoría, departamento, cuenta_contable, moneda, tipo, estado.
"""
from __future__ import annotations
from datetime import date
from typing import Any
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)
from src.core.bien_service import BienService

class BienFormDialog(QDialog):
    _MONEDAS = ["Bolívares", "Dólares"]
    _TIPOS = ["", "Administrativo", "Ejecutivo", "Operativo", "Técnico"]
    _ESTADOS = [
        "01) OPERATIVO, EN USO, EXCELENTE ESTADO",
        "02) OPERATIVO, EN USO PERO REQUIERE REPARACIÓN",
        "03) OPERATIVO, SIN USO, EN EXCELENTE ESTADO",
        "04) OPERATIVO, SIN USO, PERO REQUIERE REPARACIÓN",
        "05) INOPERATIVO, PERO RECUPERABLE",
        "06) INOPERATIVO, IRRECUPERABLE",
        "07) DESINCORPORADO EN DESUSO",
        "Faltante"
    ]

    def __init__(self, bien_service: BienService, usuario_id: int,
                 modo: str = "nuevo", bien_data: dict[str, Any] | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._service = bien_service
        self._usuario_id = usuario_id
        self._modo = modo
        self._bien_data = bien_data or {}
        self._init_ui()
        self._cargar_combos()
        if self._modo == "ver":
            self._cargar_datos()
            self._bloquear_campos()
        elif self._modo == "nuevo":
            try:
                siguiente_activo = self._service.obtener_siguiente_codigo_activo()
                self._txt_codigo_activo.setText(siguiente_activo)
                siguiente_nivel = self._service.obtener_siguiente_codigo_nivel()
                self._txt_codigo_nivel.setText(siguiente_nivel)
            except Exception:
                pass

    def _init_ui(self) -> None:
        titulo = "Nuevo Bien Mueble" if self._modo == "nuevo" else "Detalle del Bien"
        self.setWindowTitle(titulo)
        self.resize(700, 750)
        self.setMinimumWidth(650)

        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        # Identificación
        grp_id = QGroupBox("Identificación")
        form_id = QFormLayout(grp_id)
        self._txt_codigo_nivel = QLineEdit()
        self._txt_codigo_nivel.setPlaceholderText("Ej: 2-1-214-01")
        form_id.addRow("Código de nivel (*):", self._txt_codigo_nivel)
        self._txt_codigo_activo = QLineEdit()
        self._txt_codigo_activo.setPlaceholderText("Código único del bien")
        form_id.addRow("Código activo (*):", self._txt_codigo_activo)
        self._txt_descripcion = QTextEdit()
        self._txt_descripcion.setMaximumHeight(60)
        form_id.addRow("Descripción (*):", self._txt_descripcion)
        self._cmb_categoria = QComboBox()
        form_id.addRow("Categoría (*):", self._cmb_categoria)
        layout.addWidget(grp_id)

        # Características
        grp_c = QGroupBox("Características")
        form_c = QFormLayout(grp_c)
        self._txt_marca = QLineEdit()
        form_c.addRow("Marca:", self._txt_marca)
        self._txt_modelo = QLineEdit()
        form_c.addRow("Modelo:", self._txt_modelo)
        self._txt_serial = QLineEdit()
        form_c.addRow("Serial:", self._txt_serial)
        self._txt_color = QLineEdit()
        form_c.addRow("Color:", self._txt_color)
        self._cmb_tipo = QComboBox()
        self._cmb_tipo.addItems(self._TIPOS)
        form_c.addRow("Tipo:", self._cmb_tipo)
        self._spn_piezas = QSpinBox()
        self._spn_piezas.setMinimum(1)
        self._spn_piezas.setMaximum(9999)
        self._spn_piezas.setValue(1)
        form_c.addRow("N° de piezas (*):", self._spn_piezas)
        layout.addWidget(grp_c)

        # Adquisición
        grp_a = QGroupBox("Adquisición")
        form_a = QFormLayout(grp_a)
        self._txt_orden_compra = QLineEdit()
        self._txt_orden_compra.setPlaceholderText("Referencia opcional (RN-03)")
        form_a.addRow("N° Orden de Compra:", self._txt_orden_compra)
        self._date_compra = QDateEdit()
        self._date_compra.setCalendarPopup(True)
        self._date_compra.setDate(QDate.currentDate())
        self._date_compra.setDisplayFormat("dd/MM/yyyy")
        form_a.addRow("Fecha de compra (*):", self._date_compra)
        self._spn_precio = QDoubleSpinBox()
        self._spn_precio.setMinimum(0.01)
        self._spn_precio.setMaximum(999_999_999.99)
        self._spn_precio.setDecimals(2)
        form_a.addRow("Precio sin IVA (*):", self._spn_precio)
        self._cmb_moneda = QComboBox()
        self._cmb_moneda.addItems(self._MONEDAS)
        form_a.addRow("Moneda (*):", self._cmb_moneda)
        self._spn_vida_util = QSpinBox()
        self._spn_vida_util.setMinimum(1)
        self._spn_vida_util.setMaximum(600)
        self._spn_vida_util.setValue(60)
        self._spn_vida_util.setSuffix(" meses")
        form_a.addRow("Vida útil (*):", self._spn_vida_util)
        layout.addWidget(grp_a)

        # Ubicación y contabilidad
        grp_u = QGroupBox("Ubicación y Contabilidad")
        form_u = QFormLayout(grp_u)
        self._cmb_departamento = QComboBox()
        form_u.addRow("Departamento (*):", self._cmb_departamento)
        self._cmb_cuenta = QComboBox()
        form_u.addRow("Cuenta contable (*):", self._cmb_cuenta)
        self._cmb_estado = QComboBox()
        self._cmb_estado.addItems(self._ESTADOS)
        form_u.addRow("Estado (*):", self._cmb_estado)
        layout.addWidget(grp_u)

        # Observaciones
        grp_o = QGroupBox("Observaciones")
        lo = QVBoxLayout(grp_o)
        self._txt_observaciones = QTextEdit()
        self._txt_observaciones.setMaximumHeight(60)
        lo.addWidget(self._txt_observaciones)
        layout.addWidget(grp_o)

        layout.addWidget(QLabel("(*) Campos obligatorios"))

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Botones
        bl = QHBoxLayout()
        bl.addStretch()
        if self._modo == "nuevo":
            btn_g = QPushButton("Guardar")
            btn_g.clicked.connect(self._on_guardar)
            bl.addWidget(btn_g)
        btn_c = QPushButton("Cerrar" if self._modo == "ver" else "Cancelar")
        btn_c.clicked.connect(self.reject)
        bl.addWidget(btn_c)
        main_layout.addLayout(bl)

    def _cargar_combos(self) -> None:
        self._cmb_categoria.clear()
        try:
            for cat in self._service.obtener_categorias():
                self._cmb_categoria.addItem(cat["nombre"], cat["id"])
        except Exception:
            pass
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
        self._cmb_cuenta.clear()
        try:
            for cc in self._service.obtener_cuentas_contables():
                self._cmb_cuenta.addItem(
                    f"{cc['codigo']} — {cc['descripcion']}", cc["codigo"])
        except Exception:
            pass

    def _cargar_datos(self) -> None:
        d = self._bien_data
        self._txt_codigo_nivel.setText(d.get("codigo_nivel", ""))
        self._txt_codigo_activo.setText(d.get("codigo_activo", ""))
        self._txt_descripcion.setPlainText(d.get("descripcion", ""))
        idx = self._cmb_categoria.findData(d.get("categoria_id"))
        if idx >= 0:
            self._cmb_categoria.setCurrentIndex(idx)
        self._txt_marca.setText(d.get("marca", "") or "")
        self._txt_modelo.setText(d.get("modelo", "") or "")
        self._txt_serial.setText(d.get("serial_bien", "") or "")
        self._txt_color.setText(d.get("color", "") or "")
        idx_t = self._cmb_tipo.findText(d.get("tipo", "") or "")
        if idx_t >= 0:
            self._cmb_tipo.setCurrentIndex(idx_t)
        self._spn_piezas.setValue(d.get("num_piezas", 1))
        self._txt_orden_compra.setText(d.get("orden_compra", "") or "")
        fecha = d.get("fecha_compra")
        if fecha:
            if isinstance(fecha, date):
                self._date_compra.setDate(
                    QDate(fecha.year, fecha.month, fecha.day))
            else:
                try:
                    p = str(fecha)[:10].split("-")
                    self._date_compra.setDate(QDate(int(p[0]), int(p[1]), int(p[2])))
                except (IndexError, ValueError):
                    pass
        self._spn_precio.setValue(float(d.get("precio_sin_iva", 0)))
        idx_m = self._cmb_moneda.findText(d.get("moneda", "Bolívares"))
        if idx_m >= 0:
            self._cmb_moneda.setCurrentIndex(idx_m)
        self._spn_vida_util.setValue(d.get("vida_util_meses", 60))
        idx_d = self._cmb_departamento.findData(d.get("departamento_id"))
        if idx_d >= 0:
            self._cmb_departamento.setCurrentIndex(idx_d)
        idx_cc = self._cmb_cuenta.findData(d.get("cuenta_contable"))
        if idx_cc >= 0:
            self._cmb_cuenta.setCurrentIndex(idx_cc)
        idx_e = self._cmb_estado.findText(d.get("estado", "Activo"))
        if idx_e >= 0:
            self._cmb_estado.setCurrentIndex(idx_e)
        self._txt_observaciones.setPlainText(d.get("observaciones", "") or "")

    def _bloquear_campos(self) -> None:
        for w in self.findChildren(QLineEdit):
            w.setReadOnly(True)
        for w in self.findChildren(QTextEdit):
            w.setReadOnly(True)
        for w in self.findChildren(QComboBox):
            w.setEnabled(False)
        for w in self.findChildren(QSpinBox):
            w.setReadOnly(True)
            w.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        for w in self.findChildren(QDoubleSpinBox):
            w.setReadOnly(True)
            w.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        for w in self.findChildren(QDateEdit):
            w.setReadOnly(True)
            w.setButtonSymbols(QDateEdit.ButtonSymbols.NoButtons)
            w.setCalendarPopup(False)

    def _on_guardar(self) -> None:
        datos = {
            "codigo_nivel": self._txt_codigo_nivel.text().strip(),
            "codigo_activo": self._txt_codigo_activo.text().strip(),
            "descripcion": self._txt_descripcion.toPlainText().strip(),
            "categoria_id": self._cmb_categoria.currentData(),
            "marca": self._txt_marca.text().strip() or None,
            "modelo": self._txt_modelo.text().strip() or None,
            "serial_bien": self._txt_serial.text().strip() or None,
            "color": self._txt_color.text().strip() or None,
            "tipo": self._cmb_tipo.currentText() or None,
            "num_piezas": self._spn_piezas.value(),
            "orden_compra": self._txt_orden_compra.text().strip() or None,
            "fecha_compra": self._date_compra.date().toString("yyyy-MM-dd"),
            "precio_sin_iva": self._spn_precio.value(),
            "moneda": self._cmb_moneda.currentText(),
            "vida_util_meses": self._spn_vida_util.value(),
            "departamento_id": self._cmb_departamento.currentData(),
            "cuenta_contable": self._cmb_cuenta.currentData(),
            "estado": self._cmb_estado.currentText(),
            "observaciones": self._txt_observaciones.toPlainText().strip() or None,
        }
        # Validación UI
        if not datos["codigo_nivel"]:
            QMessageBox.warning(self, "Validación", "Ingrese el código de nivel.")
            return
        if not datos["codigo_activo"]:
            QMessageBox.warning(self, "Validación", "Ingrese el código activo.")
            return
        if not datos["descripcion"]:
            QMessageBox.warning(self, "Validación", "Ingrese la descripción.")
            return
        if datos["categoria_id"] is None:
            QMessageBox.warning(self, "Validación", "Seleccione una categoría.")
            return
        if datos["departamento_id"] is None:
            QMessageBox.warning(self, "Validación", "Seleccione un departamento.")
            return
        if datos["cuenta_contable"] is None:
            QMessageBox.warning(self, "Validación", "Seleccione una cuenta contable.")
            return

        ok, mensaje, bien_id = self._service.registrar_bien(datos, self._usuario_id)
        if ok:
            QMessageBox.information(self, "Bien registrado",
                                    f"{mensaje}\nID asignado: {bien_id}")
            self.accept()
        else:
            QMessageBox.warning(self, "Error de validación", mensaje)
