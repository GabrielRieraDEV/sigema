"""Prueba de la edición total de un bien (correcciones de carga).

No requiere PostgreSQL: usa un repositorio falso en memoria para verificar
que actualizar_bien ahora persiste código, precio, fecha, departamento y
estado, y que sigue rechazando un código activo duplicado (RN-01).
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.bien_repository import CAMPOS_EDITABLES
from src.core.bien_service import BienService


class _RepoFalso:
    def __init__(self):
        self.bienes = {
            1: {"id": 1, "codigo_activo": "2-13-001", "descripcion": "viejo",
                "categoria_id": 5, "cuenta_contable": "9010",
                "num_piezas": 1, "vida_util_meses": 60, "precio_sin_iva": 10.0,
                "estado": "01", "departamento_id": 3},
            2: {"id": 2, "codigo_activo": "2-13-002"},  # el "otro" bien
        }
        self.ultimo_update = None

    def buscar_por_id(self, bid):
        return self.bienes.get(bid)

    def buscar_por_codigo(self, cod):
        return next((b for b in self.bienes.values()
                     if b["codigo_activo"] == cod), None)

    def actualizar(self, bid, cambios):
        self.ultimo_update = cambios
        self.bienes[bid].update(cambios)
        return True


def _servicio(repo):
    import src.core.bien_service as m
    m.registrar_auditoria = lambda *a, **k: None  # no auditoría en el test
    return BienService(repo, movimiento_repo=None)


def test_persiste_campos_antes_bloqueados():
    repo = _RepoFalso()
    ok, msg = _servicio(repo).actualizar_bien(1, {
        "codigo_activo": "2-13-999", "codigo_nivel": "N1",
        "descripcion": "corregido", "categoria_id": 5,
        "cuenta_contable": "9010", "num_piezas": 1, "vida_util_meses": 60,
        "precio_sin_iva": 250.0, "fecha_compra": "2026-01-10",
        "moneda": "VES", "departamento_id": 7, "estado": "03",
    }, usuario_id=1)
    assert ok, msg
    u = repo.ultimo_update
    # Los campos antes inmutables ahora sí se guardan
    for campo in ("codigo_activo", "precio_sin_iva", "fecha_compra",
                  "departamento_id", "estado"):
        assert campo in u, f"{campo} no se persistió"
    assert u["precio_sin_iva"] == 250.0
    assert u["estado"] == "03"
    # 'origen' sigue fuera de la lista blanca
    assert "origen" not in CAMPOS_EDITABLES


def test_codigo_duplicado_rechazado():
    repo = _RepoFalso()
    ok, msg = _servicio(repo).actualizar_bien(1, {
        "codigo_activo": "2-13-002",  # ya lo tiene el bien 2
        "descripcion": "x", "categoria_id": 5, "cuenta_contable": "9010",
    }, usuario_id=1)
    assert not ok
    assert "único" in msg or "RN-01" in msg


if __name__ == "__main__":
    test_persiste_campos_antes_bloqueados()
    test_codigo_duplicado_rechazado()
    print("OK — edición total y RN-01 verificados sin BD")
