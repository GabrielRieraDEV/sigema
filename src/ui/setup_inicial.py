"""
setup_inicial.py — Pantalla de configuración inicial de SIGEMA.

Se muestra en el primer arranque cuando config.ini no existe o
no contiene la sección [database]. Permite al usuario configurar
la conexión a PostgreSQL y verificarla antes de guardar.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path

import psycopg2
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from src.paths import resource_path


def _config_path() -> str:
    """Retorna la ruta donde se guarda config.ini.

    En modo congelado (.exe) es la carpeta del ejecutable; en desarrollo,
    la raíz del proyecto.
    """
    try:
        from src.paths import config_path
        return str(config_path())
    except Exception:
        pass
    current = Path(__file__).resolve().parent
    for _ in range(6):
        # Buscamos la raíz del proyecto (donde está requirements.txt)
        if (current / "requirements.txt").is_file():
            return str(current / "config.ini")
        current = current.parent
    # Fallback: junto al ejecutable
    return str(Path(__file__).resolve().parent.parent.parent / "config.ini")


class SetupInicialDialog(QDialog):
    """Diálogo de configuración inicial de la conexión a PostgreSQL.

    Se muestra cuando config.ini no existe o está incompleto.
    Al guardar exitosamente, escribe config.ini y llama a ``accept()``.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SIGEMA — Configuración inicial")
        self.setMinimumWidth(520)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowIcon(QIcon(str(resource_path("assets/icono.ico"))))
        self._config_path = _config_path()
        self._setup_ui()
        self._cargar_valores_existentes()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 20)

        # ── Header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        logo_lbl = QLabel()
        pixmap = QPixmap(str(resource_path("assets/logo.png")))
        if not pixmap.isNull():
            logo_lbl.setPixmap(
                pixmap.scaledToHeight(64, Qt.TransformationMode.SmoothTransformation)
            )
        header.addWidget(logo_lbl)

        title_lbl = QLabel(
            "<b style='font-size:16px;color:#1B3A5C;'>SIGEMA</b>"
            "<br><span style='font-size:11px;color:#555;'>"
            "Sistema de Gestión de Bienes Muebles</span>"
        )
        title_lbl.setTextFormat(Qt.TextFormat.RichText)
        header.addWidget(title_lbl)
        header.addStretch()
        root.addLayout(header)

        # ── Subtítulo ───────────────────────────────────────────────────
        sub_lbl = QLabel(
            "Primera ejecución detectada. Configure la conexión a la "
            "base de datos PostgreSQL."
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color:#444; font-size:11px;")
        root.addWidget(sub_lbl)

        # ── Grupo: Conexión BD ───────────────────────────────────────────
        grp_db = QGroupBox("Conexión a PostgreSQL")
        form_db = QFormLayout(grp_db)
        form_db.setSpacing(10)

        self._ip_edit = QLineEdit("localhost")
        self._ip_edit.setPlaceholderText("Ej: 192.168.1.10")
        form_db.addRow("Servidor (IP/Host):", self._ip_edit)

        self._port_edit = QLineEdit("5432")
        self._port_edit.setPlaceholderText("5432")
        self._port_edit.setMaximumWidth(90)
        form_db.addRow("Puerto:", self._port_edit)

        self._db_edit = QLineEdit("sigema")
        self._db_edit.setPlaceholderText("Nombre de la base de datos")
        form_db.addRow("Base de datos:", self._db_edit)

        self._user_edit = QLineEdit("sigema_user")
        self._user_edit.setPlaceholderText("Usuario PostgreSQL")
        form_db.addRow("Usuario BD:", self._user_edit)

        self._pass_edit = QLineEdit()
        self._pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_edit.setPlaceholderText("Contraseña del usuario BD")
        form_db.addRow("Contraseña BD:", self._pass_edit)

        root.addWidget(grp_db)

        # ── Grupo: Respaldos ─────────────────────────────────────────────
        grp_bk = QGroupBox("Directorio de respaldos (backup)")
        form_bk = QFormLayout(grp_bk)
        form_bk.setSpacing(10)

        bk_row = QHBoxLayout()
        self._backup_edit = QLineEdit()
        self._backup_edit.setPlaceholderText(
            "Carpeta donde se guardarán los backups"
        )
        bk_row.addWidget(self._backup_edit)

        btn_browse = QPushButton("…")
        btn_browse.setFixedWidth(36)
        btn_browse.setToolTip("Seleccionar carpeta")
        btn_browse.clicked.connect(self._seleccionar_carpeta)
        bk_row.addWidget(btn_browse)

        bk_widget = QWidget()
        bk_widget.setLayout(bk_row)
        form_bk.addRow("Directorio:", bk_widget)
        root.addWidget(grp_bk)

        # ── Botón Probar conexión ────────────────────────────────────────
        self._status_lbl = QLabel("")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet("font-size:11px;")
        root.addWidget(self._status_lbl)

        btn_test = QPushButton("🔌  Probar conexión")
        btn_test.setStyleSheet(
            "QPushButton { background:#1B3A5C; color:white; font-weight:bold;"
            " padding:6px 16px; border-radius:4px; }"
            "QPushButton:hover { background:#245280; }"
        )
        btn_test.clicked.connect(self._probar_conexion)
        root.addWidget(btn_test, alignment=Qt.AlignmentFlag.AlignLeft)

        root.addSpacerItem(
            QSpacerItem(0, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        # ── Botones Guardar / Cancelar ───────────────────────────────────
        self._btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._btn_box.button(QDialogButtonBox.StandardButton.Save).setText(
            "Guardar y continuar"
        )
        self._btn_box.button(QDialogButtonBox.StandardButton.Save).setStyleSheet(
            "QPushButton { background:#1B7F3A; color:white; font-weight:bold;"
            " padding:6px 16px; border-radius:4px; }"
            "QPushButton:hover { background:#238C47; }"
        )
        self._btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "✖ Cancelar"
        )
        self._btn_box.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet(
            "QPushButton { background:#CC0000; color:white; font-weight:bold;"
            " padding:6px 16px; border-radius:4px; }"
            "QPushButton:hover { background:#FF3333; }"
        )
        self._btn_box.accepted.connect(self._guardar)
        self._btn_box.rejected.connect(self.reject)
        root.addWidget(self._btn_box)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _cargar_valores_existentes(self) -> None:
        """Si ya existe un config.ini, rellena los campos con sus valores."""
        if not os.path.isfile(self._config_path):
            # Default backup dir
            self._backup_edit.setText(
                str(Path(self._config_path).parent / "backups")
            )
            return

        cfg = configparser.ConfigParser()
        cfg.read(self._config_path, encoding="utf-8")

        if "database" in cfg:
            db = cfg["database"]
            self._ip_edit.setText(db.get("host", "localhost"))
            self._port_edit.setText(db.get("port", "5432"))
            self._db_edit.setText(db.get("dbname", "sigema"))
            self._user_edit.setText(db.get("user", "sigema_user"))
            self._pass_edit.setText(db.get("password", ""))

        if "backup" in cfg:
            self._backup_edit.setText(cfg["backup"].get("directorio", ""))
        else:
            self._backup_edit.setText(
                str(Path(self._config_path).parent / "backups")
            )

    def _seleccionar_carpeta(self) -> None:
        carpeta = QFileDialog.getExistingDirectory(
            self, "Seleccionar directorio de backups"
        )
        if carpeta:
            self._backup_edit.setText(carpeta)

    def _obtener_datos(self) -> dict:
        return {
            "host": self._ip_edit.text().strip(),
            "port": self._port_edit.text().strip(),
            "dbname": self._db_edit.text().strip(),
            "user": self._user_edit.text().strip(),
            "password": self._pass_edit.text(),
            "backup_dir": self._backup_edit.text().strip(),
        }

    def _validar(self, datos: dict) -> str | None:
        """Retorna mensaje de error si hay campos inválidos."""
        if not datos["host"]:
            return "El campo 'Servidor' es obligatorio."
        if not datos["port"].isdigit():
            return "El puerto debe ser un número válido."
        if not datos["dbname"]:
            return "El campo 'Base de datos' es obligatorio."
        if not datos["user"]:
            return "El campo 'Usuario BD' es obligatorio."
        return None

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _probar_conexion(self) -> None:
        datos = self._obtener_datos()
        error = self._validar(datos)
        if error:
            self._status_lbl.setText(f"<span style='color:red;'>⚠ {error}</span>")
            return

        self._status_lbl.setText(
            "<span style='color:#555;'>Conectando…</span>"
        )
        try:
            conn = psycopg2.connect(
                host=datos["host"],
                port=int(datos["port"]),
                dbname=datos["dbname"],
                user=datos["user"],
                password=datos["password"],
                connect_timeout=5,
            )
            conn.close()
            self._status_lbl.setText(
                "<span style='color:green;'>✔ Conexión exitosa. "
                "Puede guardar la configuración.</span>"
            )
        except Exception as exc:
            self._status_lbl.setText(
                f"<span style='color:red;'>✘ Error: {exc}</span>"
            )

    def _guardar(self) -> None:
        datos = self._obtener_datos()
        error = self._validar(datos)
        if error:
            QMessageBox.warning(self, "Datos incompletos", error)
            return

        cfg = configparser.ConfigParser()
        cfg["database"] = {
            "host": datos["host"],
            "port": datos["port"],
            "dbname": datos["dbname"],
            "user": datos["user"],
            "password": datos["password"],
            "min_connections": "2",
            "max_connections": "10",
        }
        cfg["app"] = {
            "session_timeout_minutes": "30",
            "backup_folder": datos["backup_dir"],
        }
        cfg["backup"] = {
            "directorio": datos["backup_dir"],
        }

        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                cfg.write(f)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Error al guardar",
                f"No se pudo escribir config.ini:\n{exc}",
            )
            return

        self.accept()
