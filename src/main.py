"""
main.py — Punto de entrada de SIGEMA.

Inicializa la aplicación PyQt6, la conexión a BD, los repositorios,
los servicios de negocio y la ventana principal con pestañas para
el módulo de Bienes Muebles y el módulo de Formularios BM.
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTabWidget
from src.db.connection import DBConnection
from src.db.bien_repository import BienRepository
from src.db.movimiento_repository import MovimientoRepository
from src.db.formulario_bm_repository import FormularioBMRepository
from src.core.bien_service import BienService
from src.core.formulario_bm_service import FormularioBMService
from src.ui.bien_listado import BienListadoWidget
from src.ui.formularios_bm import FormulariosBMWidget


# ID del usuario autenticado (temporal — se reemplazará con módulo de login)
_USUARIO_ID_TEMPORAL = 1


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SIGEMA")
    app.setApplicationDisplayName(
        "SIGEMA — Sistema de Gestión de Bienes Muebles")

    # --- Conexión a BD ---
    try:
        db = DBConnection()
    except (FileNotFoundError, ValueError, ConnectionError) as exc:
        QMessageBox.critical(None, "Error de conexión", str(exc))
        sys.exit(1)

    # --- Capas de la aplicación ---
    bien_repo = BienRepository(db)
    mov_repo = MovimientoRepository(db)
    bien_service = BienService(bien_repo, mov_repo)

    formulario_repo = FormularioBMRepository(db)
    formulario_service = FormularioBMService(formulario_repo)

    # --- Ventana principal ---
    window = QMainWindow()
    window.setWindowTitle(
        "SIGEMA — Sistema de Gestión de Bienes Muebles")
    window.resize(1024, 640)

    # --- Pestañas ---
    tabs = QTabWidget()

    # Tab 1: Bienes Muebles (Módulo A)
    listado = BienListadoWidget(
        bien_service=bien_service,
        usuario_id=_USUARIO_ID_TEMPORAL,
    )
    tabs.addTab(listado, "Bienes Muebles")

    # Tab 2: Formularios BM (Módulo B)
    formularios = FormulariosBMWidget(
        bm_service=formulario_service,
        usuario_id=_USUARIO_ID_TEMPORAL,
    )
    tabs.addTab(formularios, "Formularios BM")

    window.setCentralWidget(tabs)
    window.show()

    # --- Ejecución ---
    exit_code = app.exec()

    # --- Limpieza ---
    db.close_pool()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
