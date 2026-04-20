"""
main.py — Punto de entrada de SIGEMA.

Inicializa la aplicación PyQt6, la conexión a BD, los repositorios,
el servicio de negocio y la ventana principal con el módulo de Bienes Muebles.
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from src.db.connection import DBConnection
from src.db.bien_repository import BienRepository
from src.db.movimiento_repository import MovimientoRepository
from src.core.bien_service import BienService
from src.ui.bien_listado import BienListadoWidget


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

    # --- Ventana principal ---
    window = QMainWindow()
    window.setWindowTitle(
        "SIGEMA — Sistema de Gestión de Bienes Muebles")
    window.resize(1024, 640)

    listado = BienListadoWidget(
        bien_service=bien_service,
        usuario_id=_USUARIO_ID_TEMPORAL,
    )
    window.setCentralWidget(listado)
    window.show()

    # --- Ejecución ---
    exit_code = app.exec()

    # --- Limpieza ---
    db.close_pool()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
