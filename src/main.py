"""
main.py — Punto de entrada de SIGEMA.

Flujo de arranque:
  1. Verificar config.ini → si no existe, mostrar SetupInicialDialog.
  2. Inicializar DBConnection.
  3. Mostrar LoginDialog.
  4. Abrir MainWindow con las pestañas según el perfil del usuario.

MainWindow incluye:
  - Control de inactividad por QTimer (NF-05, 30 min).
  - Menú Herramientas → Realizar Backup, Cerrar Sesión.
  - Status bar con usuario y perfil activos.
  - Pestañas de Usuarios, Catálogos y Auditoría solo para Administrador.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from src.paths import resource_path
from src.core.auth import Session
from src.core.backup import ejecutar_backup
from src.db.connection import DBConnection
from src.db.bien_repository import BienRepository
from src.db.movimiento_repository import MovimientoRepository
from src.db.formulario_bm_repository import FormularioBMRepository
from src.db.donacion_repository import DonacionRepository
from src.db.usuario_repository import UsuarioRepository
from src.db.catalogo_repository import CatalogoRepository
from src.db.auditoria_repository import AuditoriaRepository
from src.core.bien_service import BienService
from src.core.formulario_bm_service import FormularioBMService
from src.core.donacion_service import DonacionService
from src.ui.bien_listado import BienListadoWidget
from src.ui.donaciones_listado import DonacionesListadoWidget
from src.ui.formularios_bm import FormulariosBMWidget
from src.ui.usuarios import UsuariosWidget
from src.ui.catalogos import CatalogosWidget
from src.ui.auditoria_panel import AuditoriaPanelWidget
from src.ui.migracion_panel import MigracionPanelWidget

# Intervalo del timer de inactividad (ms). Comprueba cada 60 seg.
_TIMER_INTERVAL_MS = 60_000


def _config_existe() -> bool:
    """Retorna True si config.ini existe y tiene la sección [database]."""
    import configparser

    candidatos = []
    # En modo congelado (.exe), config.ini vive junto al ejecutable.
    try:
        from src.paths import config_path
        candidatos.append(config_path())
    except Exception:
        pass
    current = Path(__file__).resolve().parent
    for _ in range(6):
        candidatos.append(current / "config.ini")
        current = current.parent

    for candidate in candidatos:
        if candidate.is_file():
            cfg = configparser.ConfigParser()
            cfg.read(str(candidate), encoding="utf-8")
            return "database" in cfg
    return False


# ===========================================================================
# Ventana principal
# ===========================================================================
class MainWindow(QMainWindow):
    """Ventana principal de SIGEMA con control de inactividad."""

    def __init__(
        self,
        db: DBConnection,
        bien_service: BienService,
        formulario_service: FormularioBMService,
        donacion_service: DonacionService,
        usuario_repo: UsuarioRepository,
        catalogo_repo: CatalogoRepository,
        auditoria_repo: AuditoriaRepository,
    ):
        super().__init__()
        self._db = db
        self._bien_service = bien_service
        self._formulario_service = formulario_service
        self._donacion_service = donacion_service
        self._usuario_repo = usuario_repo
        self._catalogo_repo = catalogo_repo
        self._auditoria_repo = auditoria_repo

        session = Session.get_instance()
        self._perfil = session.perfil or ""
        self._usuario_id = session.usuario_id

        self._setup_ui()
        self._setup_inactividad_timer()

        # Interceptar eventos de la ventana para refrescar actividad
        self.installEventFilter(self)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        session = Session.get_instance()
        usuario = session.usuario_actual or {}
        nombre_completo = f"{usuario.get('nombre', '')} {usuario.get('apellido', '')}".strip()

        self.setWindowTitle("SIGEMA — Sistema de Gestión de Bienes Muebles")
        self.setWindowIcon(QIcon(str(resource_path("assets/icono.ico"))))
        self.resize(1100, 680)

        # ── Widget central ───────────────────────────────────────────────
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        # ── Header ───────────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        logo_lbl = QLabel()
        pixmap = QPixmap(str(resource_path("assets/logo.png")))
        if not pixmap.isNull():
            logo_lbl.setPixmap(
                pixmap.scaledToHeight(70, Qt.TransformationMode.SmoothTransformation)
            )
        header_layout.addWidget(logo_lbl)

        title_lbl = QLabel(
            "<b>SIGEMA</b><br>Sistema de Gestión de Bienes Muebles"
        )
        title_lbl.setStyleSheet("font-size:17px; color:#1B3A5C;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        user_lbl = QLabel(
            f"<span style='color:#555; font-size:11px;'>"
            f"👤 <b>{nombre_completo}</b> — {self._perfil}</span>"
        )
        user_lbl.setTextFormat(Qt.TextFormat.RichText)
        header_layout.addWidget(user_lbl)
        main_layout.addLayout(header_layout)

        # ── Pestañas (Diseño Premium) ───────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CCC;
                top: -1px;
                background: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #F0F0F0;
                border: 1px solid #CCC;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                color: #666;
            }
            QTabBar::tab:selected {
                background: #1B3A5C;
                color: white;
                border-bottom-color: #1B3A5C;
            }
            QTabBar::tab:hover:!selected {
                background: #E5E5E5;
                color: #333;
            }
        """)

        # Bienes Muebles — todos los perfiles
        listado = BienListadoWidget(
            bien_service=self._bien_service,
            usuario_id=self._usuario_id,
            donacion_service=self._donacion_service,
        )
        self._tabs.addTab(listado, "Bienes Muebles")

        # Donaciones — todos los perfiles con acceso a bienes
        if session.tiene_permiso("bienes.ver"):
            donaciones = DonacionesListadoWidget(
                bien_service=self._bien_service,
                donacion_service=self._donacion_service,
                usuario_id=self._usuario_id,
            )
            self._tabs.addTab(donaciones, "Donaciones")

        # Formularios BM — Almacenista y Administrador
        if session.tiene_permiso("formularios.generar") or session.tiene_permiso("formularios.ver"):
            formularios = FormulariosBMWidget(
                bm_service=self._formulario_service,
                usuario_id=self._usuario_id,
            )
            self._tabs.addTab(formularios, "Formularios BM")

        # Usuarios — solo Administrador
        if session.tiene_permiso("usuarios.gestionar"):
            self._tabs.addTab(
                UsuariosWidget(self._usuario_repo),
                "Usuarios"
            )

        # Catálogos — solo Administrador
        if session.tiene_permiso("catalogos.gestionar"):
            self._tabs.addTab(
                CatalogosWidget(self._catalogo_repo),
                "Catálogos"
            )

        # Auditoría — solo Administrador
        if session.tiene_permiso("auditoria.ver"):
            self._tabs.addTab(
                AuditoriaPanelWidget(self._auditoria_repo),
                "Auditoría"
            )

        # Migración de datos — solo Administrador
        if session.tiene_permiso("usuarios.gestionar"):
            self._tabs.addTab(
                MigracionPanelWidget(self._db, self._usuario_id),
                "Migración"
            )

        main_layout.addWidget(self._tabs)
        self.setCentralWidget(central)

        # ── Menú Herramientas (Diseño Premium) ───────────────────────────
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #F8F9FA;
                border-bottom: 1px solid #DDD;
                padding: 2px;
                font-weight: 500;
            }
            QMenuBar::item {
                background: transparent;
                padding: 6px 12px;
                border-radius: 4px;
                color: #333;
            }
            QMenuBar::item:selected {
                background: #E9ECEF;
            }
            QMenu {
                background-color: white;
                border: 1px solid #DDD;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 30px 6px 20px;
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected {
                background-color: #1B3A5C;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #EEE;
                margin: 4px 10px;
            }
        """)
        menu_herram = menu_bar.addMenu("🔧 Herramientas")

        if session.tiene_permiso("backup.ejecutar"):
            act_backup = menu_herram.addAction("💾  Realizar Backup")
            act_backup.triggered.connect(self._realizar_backup)
            menu_herram.addSeparator()

        act_logout = menu_herram.addAction("🔒  Cerrar sesión")
        act_logout.triggered.connect(self._cerrar_sesion)

        # ── Status bar ───────────────────────────────────────────────────
        self.statusBar().showMessage(
            f"Usuario: {nombre_completo} | Perfil: {self._perfil}"
        )

    # ------------------------------------------------------------------
    # Inactividad (NF-05)
    # ------------------------------------------------------------------
    def _setup_inactividad_timer(self) -> None:
        self._timer_inactividad = QTimer(self)
        self._timer_inactividad.setInterval(_TIMER_INTERVAL_MS)
        self._timer_inactividad.timeout.connect(self._verificar_inactividad)
        self._timer_inactividad.start()

    def _verificar_inactividad(self) -> None:
        session = Session.get_instance()
        if session.verificar_inactividad():
            self._timer_inactividad.stop()
            QMessageBox.warning(
                self,
                "Sesión expirada",
                "Su sesión expiró por inactividad (30 minutos).\n"
                "Será redirigido al inicio de sesión.",
            )
            self._cerrar_sesion()

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        """Refresca la actividad en cualquier interacción del usuario."""
        if event.type() in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.KeyPress,
            QEvent.Type.Wheel,
        ):
            Session.get_instance().refrescar_actividad()
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Acciones de menú
    # ------------------------------------------------------------------
    def _realizar_backup(self) -> None:
        Session.get_instance().refrescar_actividad()
        resp = QMessageBox.question(
            self,
            "Realizar Backup",
            "¿Desea generar un respaldo de la base de datos ahora?",
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self.statusBar().showMessage("Generando backup…")
        ok, resultado = ejecutar_backup()
        self.statusBar().showMessage(
            f"Usuario: {Session.get_instance().usuario_actual.get('username', '')} "
            f"| Perfil: {self._perfil}"
        )

        if ok:
            QMessageBox.information(
                self,
                "Backup exitoso",
                f"Respaldo generado correctamente:\n\n{resultado}",
            )
        else:
            QMessageBox.critical(
                self,
                "Error en Backup",
                f"No se pudo generar el respaldo:\n\n{resultado}",
            )

    def _cerrar_sesion(self) -> None:
        """Cierra la sesión y relanza el flujo de login."""
        self._timer_inactividad.stop()
        Session.logout()
        DBConnection.reset_instance()
        self.close()
        # Relanzar el flujo de autenticación
        _arrancar_flujo_login()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer_inactividad.stop()
        self._db.close_pool()
        super().closeEvent(event)


# ===========================================================================
# Flujo de arranque
# ===========================================================================
def _arrancar_flujo_login() -> None:
    """Muestra LoginDialog y si OK abre MainWindow."""
    from src.ui.login import LoginDialog

    # Reinicializar DBConnection tras logout
    try:
        db = DBConnection()
    except (FileNotFoundError, ValueError, ConnectionError) as exc:
        QMessageBox.critical(None, "Error de conexión", str(exc))
        sys.exit(1)

    login_dlg = LoginDialog()
    if login_dlg.exec() != login_dlg.DialogCode.Accepted:
        db.close_pool()
        QApplication.instance().quit()
        return

    _abrir_ventana_principal(db)


def _abrir_ventana_principal(db: DBConnection) -> None:
    """Construye e instancia MainWindow con todas sus dependencias."""
    # Repositorios
    bien_repo = BienRepository(db)
    mov_repo = MovimientoRepository(db)
    formulario_repo = FormularioBMRepository(db)
    donacion_repo = DonacionRepository(db)
    usuario_repo = UsuarioRepository(db)
    catalogo_repo = CatalogoRepository(db)
    auditoria_repo = AuditoriaRepository(db)

    # Servicios
    bien_service = BienService(bien_repo, mov_repo)
    formulario_service = FormularioBMService(formulario_repo)
    donacion_service = DonacionService(bien_service, donacion_repo)

    window = MainWindow(
        db=db,
        bien_service=bien_service,
        formulario_service=formulario_service,
        donacion_service=donacion_service,
        usuario_repo=usuario_repo,
        catalogo_repo=catalogo_repo,
        auditoria_repo=auditoria_repo,
    )
    window.show()

    # Mantener referencia para evitar garbage collection
    QApplication.instance()._main_window = window  # type: ignore[attr-defined]


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SIGEMA")
    app.setApplicationDisplayName("SIGEMA — Sistema de Gestión de Bienes Muebles")

    # ── 1. Configuración inicial (primer arranque) ───────────────────────
    if not _config_existe():
        from src.ui.setup_inicial import SetupInicialDialog
        setup_dlg = SetupInicialDialog()
        if setup_dlg.exec() != setup_dlg.DialogCode.Accepted:
            sys.exit(0)

    # ── 2. Conexión a BD ─────────────────────────────────────────────────
    try:
        db = DBConnection()
    except (FileNotFoundError, ValueError, ConnectionError) as exc:
        QMessageBox.critical(None, "Error de conexión", str(exc))
        sys.exit(1)

    # ── 3. Login ─────────────────────────────────────────────────────────
    from src.ui.login import LoginDialog
    login_dlg = LoginDialog()
    if login_dlg.exec() != login_dlg.DialogCode.Accepted:
        db.close_pool()
        sys.exit(0)

    # ── 4. Ventana principal ─────────────────────────────────────────────
    _abrir_ventana_principal(db)

    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
