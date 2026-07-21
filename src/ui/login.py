"""
login.py — Pantalla de autenticación de SIGEMA.

Presenta el formulario de usuario/contraseña y delega en Session.login().
Al autenticar exitosamente: accept().
Al cancelar o cerrar: reject() → la aplicación termina.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from src.core.auth import Session
from src.paths import resource_path


class LoginDialog(QDialog):
    """Diálogo de autenticación.

    Uso::

        dlg = LoginDialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = Session.get_instance()
            # abrir ventana principal
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SIGEMA — Iniciar sesión")
        self.setFixedSize(400, 480)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowIcon(QIcon(str(resource_path("assets/icono.ico"))))
        self._intentos_fallidos = 0
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 28)
        root.setSpacing(0)

        # ── Logo / Encabezado ────────────────────────────────────────────
        logo_lbl = QLabel()
        pixmap = QPixmap(str(resource_path("assets/logo.png")))
        if not pixmap.isNull():
            logo_lbl.setPixmap(
                pixmap.scaledToHeight(72, Qt.TransformationMode.SmoothTransformation)
            )
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(logo_lbl)
            root.addSpacing(12)

        title_lbl = QLabel("SIGEMA")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            "font-size:22px; font-weight:bold; color:#1B3A5C;"
        )
        root.addWidget(title_lbl)

        sub_lbl = QLabel("Sistema de Gestión de Bienes Muebles")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet("font-size:11px; color:#666; margin-bottom:4px;")
        root.addWidget(sub_lbl)

        inst_lbl = QLabel("Instituto Autónomo Minas Bolívar")
        inst_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inst_lbl.setStyleSheet("font-size:10px; color:#888;")
        root.addWidget(inst_lbl)

        root.addSpacing(28)

        # ── Campos de login ──────────────────────────────────────────────
        lbl_user = QLabel("Usuario")
        lbl_user.setStyleSheet("font-size:11px; font-weight:bold; color:#333;")
        root.addWidget(lbl_user)
        root.addSpacing(4)

        self._user_edit = QLineEdit()
        self._user_edit.setPlaceholderText("Ingrese su nombre de usuario")
        self._user_edit.setFixedHeight(36)
        self._user_edit.setStyleSheet(
            "QLineEdit { border:1px solid #ccc; border-radius:4px;"
            " padding:4px 8px; font-size:12px; }"
            "QLineEdit:focus { border-color:#1B3A5C; }"
        )
        root.addWidget(self._user_edit)

        root.addSpacing(12)

        lbl_pass = QLabel("Contraseña")
        lbl_pass.setStyleSheet("font-size:11px; font-weight:bold; color:#333;")
        root.addWidget(lbl_pass)
        root.addSpacing(4)

        pass_layout = QHBoxLayout()
        pass_layout.setSpacing(4)

        self._pass_edit = QLineEdit()
        self._pass_edit.setPlaceholderText("Ingrese su contraseña")
        self._pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_edit.setFixedHeight(36)
        self._pass_edit.setStyleSheet(
            "QLineEdit { border:1px solid #ccc; border-radius:4px;"
            " padding:4px 8px; font-size:12px; }"
            "QLineEdit:focus { border-color:#1B3A5C; }"
        )
        pass_layout.addWidget(self._pass_edit)

        self._btn_ver_pass = QPushButton("👁")
        self._btn_ver_pass.setFixedSize(36, 36)
        self._btn_ver_pass.setToolTip("Mostrar/Ocultar contraseña")
        self._btn_ver_pass.setCheckable(True)
        self._btn_ver_pass.setStyleSheet(
            "QPushButton { border:1px solid #ccc; border-radius:4px; font-size:16px; background: white; }"
            "QPushButton:checked { background: #e0e0e0; }"
        )
        self._btn_ver_pass.toggled.connect(self._toggle_password_visibility)
        pass_layout.addWidget(self._btn_ver_pass)

        root.addLayout(pass_layout)

        root.addSpacing(8)

        # ── Etiqueta de error ────────────────────────────────────────────
        self._error_lbl = QLabel("")
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setStyleSheet(
            "font-size:11px; color:#CC0000; min-height:18px;"
        )
        self._error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._error_lbl)

        root.addSpacing(12)

        # ── Botón Ingresar ───────────────────────────────────────────────
        self._btn_login = QPushButton("Ingresar")
        self._btn_login.setFixedHeight(40)
        self._btn_login.setStyleSheet(
            "QPushButton { background:#1B3A5C; color:white; font-weight:bold;"
            " font-size:13px; border-radius:4px; }"
            "QPushButton:hover { background:#245280; }"
            "QPushButton:pressed { background:#142d47; }"
            "QPushButton:disabled { background:#aaa; }"
        )
        self._btn_login.clicked.connect(self._intentar_login)
        root.addWidget(self._btn_login)

        root.addStretch()

        # ── Versión ──────────────────────────────────────────────────────
        ver_lbl = QLabel("v1.2.1 — División de Control de Bienes")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet("font-size:9px; color:#aaa;")
        root.addWidget(ver_lbl)

        # Permitir Enter en cualquier campo
        self._user_edit.returnPressed.connect(self._intentar_login)
        self._pass_edit.returnPressed.connect(self._intentar_login)

        # Foco inicial
        self._user_edit.setFocus()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _intentar_login(self) -> None:
        username = self._user_edit.text().strip()
        password = self._pass_edit.text()

        if not username:
            self._mostrar_error("Ingrese su nombre de usuario.")
            self._user_edit.setFocus()
            return

        if not password:
            self._mostrar_error("Ingrese su contraseña.")
            self._pass_edit.setFocus()
            return

        self._btn_login.setEnabled(False)
        self._btn_login.setText("Verificando…")
        self._error_lbl.setText("")

        ok = Session.login(username, password)

        self._btn_login.setEnabled(True)
        self._btn_login.setText("Ingresar")

        if ok:
            self.accept()
        else:
            self._intentos_fallidos += 1
            self._pass_edit.clear()
            self._mostrar_error(
                "Usuario o contraseña incorrectos, o cuenta inactiva."
            )
            self._pass_edit.setFocus()

    def _mostrar_error(self, mensaje: str) -> None:
        self._error_lbl.setText(f"⚠ {mensaje}")

    def _toggle_password_visibility(self, checked: bool) -> None:
        """Alterna el modo de visualización de la contraseña."""
        if checked:
            self._pass_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._btn_ver_pass.setText("🙈")
        else:
            self._pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._btn_ver_pass.setText("👁")
