"""
connection.py — Conexión a PostgreSQL con pool de conexiones.

Singleton que lee la configuración desde config.ini y mantiene un
ThreadedConnectionPool para soportar múltiples usuarios en LAN (NF-02).
"""

import os
import configparser
import threading

import psycopg2
from psycopg2 import pool, OperationalError, DatabaseError
from contextlib import contextmanager


class DBConnection:
    """Administra el pool de conexiones a PostgreSQL.

    Uso típico::

        db = DBConnection()

        with db.get_cursor() as cur:
            cur.execute("SELECT * FROM bien WHERE id = %s", (1,))
            row = cur.fetchone()
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, config_path: str | None = None):
        """Patrón Singleton — una sola instancia del pool por proceso."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_path: str | None = None):
        if self._initialized:
            return

        self._config_path = config_path or self._find_config()
        self._pool: pool.ThreadedConnectionPool | None = None
        self._connect()
        self._initialized = True

    # ------------------------------------------------------------------
    # Localización del archivo config.ini
    # ------------------------------------------------------------------
    @staticmethod
    def _find_config() -> str:
        """Busca config.ini subiendo desde el directorio del paquete
        hasta la raíz del proyecto."""
        # Empezar desde el directorio de este archivo (src/db/)
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):  # máximo 5 niveles
            candidate = os.path.join(current, "config.ini")
            if os.path.isfile(candidate):
                return candidate
            current = os.path.dirname(current)

        raise FileNotFoundError(
            "No se encontró el archivo config.ini.\n"
            "Copie config.example.ini como config.ini en la raíz del "
            "proyecto y configure los datos de conexión a PostgreSQL."
        )

    # ------------------------------------------------------------------
    # Creación del pool
    # ------------------------------------------------------------------
    def _connect(self) -> None:
        """Crea el pool de conexiones leyendo config.ini."""
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path, encoding="utf-8")

        if "database" not in cfg:
            raise ValueError(
                f"El archivo {self._config_path} no contiene la sección "
                "[database]. Verifique la configuración."
            )

        db = cfg["database"]

        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=int(db.get("min_connections", "2")),
                maxconn=int(db.get("max_connections", "10")),
                host=db.get("host", "localhost"),
                port=int(db.get("port", "5432")),
                dbname=db.get("dbname", "sigema"),
                user=db.get("user", "sigema_user"),
                password=db.get("password", ""),
            )
        except OperationalError as exc:
            raise ConnectionError(
                "No se pudo conectar a la base de datos PostgreSQL.\n\n"
                f"Detalles: {exc}\n\n"
                "Verifique que:\n"
                "  1. El servidor PostgreSQL está encendido.\n"
                "  2. Los datos en config.ini son correctos.\n"
                "  3. La red LAN está operativa."
            ) from exc

    # ------------------------------------------------------------------
    # Obtener / devolver conexiones
    # ------------------------------------------------------------------
    def get_connection(self):
        """Obtiene una conexión del pool.

        El llamador es responsable de devolverla con release_connection().
        """
        if self._pool is None or self._pool.closed:
            raise ConnectionError(
                "El pool de conexiones está cerrado. "
                "Reinicie la aplicación."
            )
        try:
            return self._pool.getconn()
        except OperationalError as exc:
            raise ConnectionError(
                "No se pudo obtener una conexión de la base de datos.\n"
                f"Detalle: {exc}"
            ) from exc

    def release_connection(self, conn) -> None:
        """Devuelve una conexión al pool."""
        if self._pool is not None and not self._pool.closed:
            self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self):
        """Context manager que entrega un cursor con commit/rollback
        automático.

        Ejemplo::

            with db.get_cursor() as cur:
                cur.execute("INSERT INTO bien (...) VALUES (...)")
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                yield cur
                conn.commit()
        except (DatabaseError, Exception):
            conn.rollback()
            raise
        finally:
            self.release_connection(conn)

    # ------------------------------------------------------------------
    # Cierre del pool
    # ------------------------------------------------------------------
    def close_pool(self) -> None:
        """Cierra todas las conexiones del pool.  Llamar al salir de la app."""
        if self._pool is not None and not self._pool.closed:
            self._pool.closeall()

    @classmethod
    def reset_instance(cls) -> None:
        """Destruye el singleton (útil para tests)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close_pool()
                cls._instance = None
