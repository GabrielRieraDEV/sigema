"""
conftest.py — Configuración global de pytest para SIGEMA.

Estrategia de base de datos de prueba
-------------------------------------
- Se usa una base de datos PostgreSQL **separada** llamada ``sigema_test``
  (configurable con la variable de entorno ``SIGEMA_TEST_DB``).
- La base se crea una sola vez por sesión (drop + create) y se elimina
  al terminar.
- Antes de **cada** test se vuelve a aplicar ``sql/schema.sql``, de modo
  que cada prueba arranca con el esquema y los datos semilla recién
  creados (catálogos, usuario admin, etc.). Esto garantiza que cada test
  sea totalmente independiente (setup + teardown limpios).

Credenciales
------------
La conexión de mantenimiento (para crear/eliminar la base y aplicar el
esquema) se toma de variables de entorno con valores por defecto típicos
de una instalación local:

    SIGEMA_TEST_HOST      (default: localhost)
    SIGEMA_TEST_PORT      (default: 5432)
    SIGEMA_TEST_USER      (default: postgres)
    SIGEMA_TEST_PASSWORD  (default: postgres)
    SIGEMA_TEST_DB        (default: sigema_test)

Ejecución
---------
    pytest                      # toda la suite
    pytest tests/test_auth.py   # un archivo
    pytest -k RN_01             # un test por nombre
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Asegurar que la raíz del proyecto esté en sys.path para "import src...".
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bcrypt  # noqa: E402
import psycopg2  # noqa: E402

from src.db.connection import DBConnection  # noqa: E402
from src.core.auth import Session  # noqa: E402

SCHEMA_SQL = PROJECT_ROOT / "sql" / "schema.sql"

# ---------------------------------------------------------------------------
# Parámetros de conexión (mantenimiento)
# ---------------------------------------------------------------------------
TEST_DB = os.environ.get("SIGEMA_TEST_DB", "sigema_test")
PG_PARAMS = {
    "host": os.environ.get("SIGEMA_TEST_HOST", "localhost"),
    "port": int(os.environ.get("SIGEMA_TEST_PORT", "5432")),
    "user": os.environ.get("SIGEMA_TEST_USER", "postgres"),
    "password": os.environ.get("SIGEMA_TEST_PASSWORD", "postgres"),
}

# Cuenta contable existente en los datos semilla (sql/schema.sql §5.1).
CUENTA_SEED = "2-1-214-01"


# ===========================================================================
# Utilidades internas
# ===========================================================================
def _conectar(dbname: str):
    """Abre una conexión psycopg2 directa (autocommit) a ``dbname``."""
    conn = psycopg2.connect(dbname=dbname, **PG_PARAMS)
    conn.autocommit = True
    return conn


def _aplicar_esquema() -> None:
    """Aplica ``sql/schema.sql`` sobre la base de prueba (drop + create + seed).

    El script ya hace ``DROP TABLE IF EXISTS ... CASCADE`` al inicio, por lo
    que ejecutarlo deja la base en un estado conocido y reproducible.
    """
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    conn = _conectar(TEST_DB)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.close()


def _escribir_config_test(ruta: Path) -> Path:
    """Escribe un config.ini temporal apuntando a la base de prueba."""
    contenido = (
        "[database]\n"
        f"host = {PG_PARAMS['host']}\n"
        f"port = {PG_PARAMS['port']}\n"
        f"dbname = {TEST_DB}\n"
        f"user = {PG_PARAMS['user']}\n"
        f"password = {PG_PARAMS['password']}\n"
        "min_connections = 1\n"
        "max_connections = 5\n"
    )
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


# ===========================================================================
# Fixtures de sesión: crear / destruir la base de prueba
# ===========================================================================
@pytest.fixture(scope="session", autouse=True)
def _base_de_datos_test(tmp_path_factory):
    """Crea la base ``sigema_test`` y configura el pool de SIGEMA hacia ella.

    Se ejecuta una sola vez por sesión de pytest.
    """
    # 1. Crear la base de datos (drop + create) desde la base de mantenimiento.
    admin = _conectar("postgres")
    try:
        with admin.cursor() as cur:
            # Cortar conexiones existentes y recrear.
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (TEST_DB,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}"')
            cur.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        admin.close()

    # 2. Configurar el singleton DBConnection apuntando a la base de prueba.
    config_path = _escribir_config_test(
        tmp_path_factory.mktemp("config") / "config.ini"
    )
    DBConnection.reset_instance()
    DBConnection(config_path=str(config_path))

    yield

    # 3. Teardown: cerrar pool y eliminar la base.
    DBConnection.reset_instance()
    admin = _conectar("postgres")
    try:
        with admin.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (TEST_DB,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}"')
    finally:
        admin.close()


@pytest.fixture(autouse=True)
def _esquema_limpio(_base_de_datos_test):
    """Reaplica el esquema y cierra cualquier sesión antes de cada test."""
    _aplicar_esquema()
    Session.logout()
    yield
    Session.logout()


# ===========================================================================
# Fixtures de acceso a datos
# ===========================================================================
@pytest.fixture
def db() -> DBConnection:
    """Devuelve el singleton DBConnection (ya apuntando a sigema_test)."""
    return DBConnection()


@pytest.fixture
def admin_id(db) -> int:
    """ID del usuario administrador sembrado por schema.sql."""
    with db.get_cursor() as cur:
        cur.execute("SELECT id FROM usuario WHERE username = 'admin'")
        return cur.fetchone()[0]


@pytest.fixture
def datos_base(db, admin_id) -> dict:
    """Crea un departamento de prueba y devuelve los IDs base para un bien.

    Returns
    -------
    dict
        ``{departamento_id, categoria_id, cuenta_contable, usuario_id}``
    """
    with db.get_cursor() as cur:
        cur.execute(
            "INSERT INTO departamento (codigo, nombre) VALUES (%s, %s) "
            "RETURNING id",
            ("DEP-01", "Almacén Central"),
        )
        departamento_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM categoria ORDER BY id LIMIT 1")
        categoria_id = cur.fetchone()[0]
    return {
        "departamento_id": departamento_id,
        "categoria_id": categoria_id,
        "cuenta_contable": CUENTA_SEED,
        "usuario_id": admin_id,
    }


# ===========================================================================
# Helpers reutilizables (expuestos como fixtures de fábrica)
# ===========================================================================
@pytest.fixture
def crear_usuario(db):
    """Fábrica para crear usuarios con contraseña conocida (hash bcrypt real)."""
    def _crear(
        username: str,
        password: str = "secreto123",
        perfil: str = "Administrador",
        activo: bool = True,
        nombre: str = "Usuario",
        apellido: str = "Prueba",
        cargo: str = "Tester",
    ) -> int:
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        with db.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuario
                    (nombre, apellido, cargo, username, password_hash,
                     perfil, activo)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (nombre, apellido, cargo, username, password_hash,
                 perfil, activo),
            )
            return cur.fetchone()[0]

    return _crear


@pytest.fixture
def bien_dict(datos_base):
    """Fábrica que devuelve un dict de bien válido (sobreescribible)."""
    from datetime import date

    def _bien(**overrides) -> dict:
        datos = {
            "codigo_activo": "ACT-0001",
            "codigo_nivel": "N-0001",
            "descripcion": "Silla ergonómica de oficina",
            "categoria_id": datos_base["categoria_id"],
            "fecha_compra": date.today().isoformat(),
            "precio_sin_iva": 150.00,
            "moneda": "Bolívares",
            "departamento_id": datos_base["departamento_id"],
            "cuenta_contable": datos_base["cuenta_contable"],
        }
        datos.update(overrides)
        return datos

    return _bien


@pytest.fixture
def sesion_admin(db, crear_usuario):
    """Crea un administrador, inicia sesión y devuelve su ID.

    Útil para tests que requieren una sesión activa (p. ej. auditoría).
    """
    uid = crear_usuario("tester_admin", "secreto123", "Administrador")
    assert Session.login("tester_admin", "secreto123") is True
    yield uid
    Session.logout()


# ===========================================================================
# Fixtures de servicios
# ===========================================================================
@pytest.fixture
def bien_service(db):
    from src.core.bien_service import BienService
    from src.db.bien_repository import BienRepository
    from src.db.movimiento_repository import MovimientoRepository

    return BienService(BienRepository(db), MovimientoRepository(db))


@pytest.fixture
def formulario_service(db):
    from src.core.formulario_bm_service import FormularioBMService
    from src.db.formulario_bm_repository import FormularioBMRepository

    return FormularioBMService(FormularioBMRepository(db))


@pytest.fixture
def formulario_repo(db):
    from src.db.formulario_bm_repository import FormularioBMRepository

    return FormularioBMRepository(db)


@pytest.fixture
def donacion_service(db, bien_service):
    from src.core.donacion_service import DonacionService
    from src.db.donacion_repository import DonacionRepository

    return DonacionService(bien_service, DonacionRepository(db))
