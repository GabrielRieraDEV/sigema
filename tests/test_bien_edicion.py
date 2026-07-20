"""
test_bien_edicion.py — Edición (corrección) de un bien por el Administrador.

Verifica:
- Que se corrijan los campos editables.
- Que los campos inmutables (código, precio, estado) NO cambien aunque se
  envíen.
- Que el cambio quede en auditoría (RN-12).
- Que Administrador y Almacenista tengan 'bienes.editar', y Consulta no.
"""

from __future__ import annotations

from src.core.auth import Session


def _crear_bien(bien_service, bien_dict, datos_base) -> int:
    ok, msg, bid = bien_service.registrar_bien(
        bien_dict(), datos_base["usuario_id"])
    assert ok is True, msg
    return bid


def test_actualizar_bien_corrige_campos(bien_service, bien_dict, datos_base):
    uid = datos_base["usuario_id"]
    bid = _crear_bien(bien_service, bien_dict, datos_base)

    ok, msg = bien_service.actualizar_bien(bid, {
        "descripcion": "Silla ergonómica CORREGIDA",
        "categoria_id": datos_base["categoria_id"],
        "marca": "Marca Nueva",
        "num_piezas": 3,
        "cuenta_contable": datos_base["cuenta_contable"],
        "vida_util_meses": 48,
        "observaciones": "Corregido por el administrador",
    }, uid)
    assert ok is True, msg

    bien = bien_service.obtener_bien_por_id(bid)
    assert bien["descripcion"] == "Silla ergonómica CORREGIDA"
    assert bien["marca"] == "Marca Nueva"
    assert bien["num_piezas"] == 3
    assert bien["vida_util_meses"] == 48
    assert bien["observaciones"] == "Corregido por el administrador"


def test_actualizar_bien_no_toca_campos_inmutables(
    bien_service, bien_dict, datos_base
):
    uid = datos_base["usuario_id"]
    bid = _crear_bien(bien_service, bien_dict, datos_base)
    original = bien_service.obtener_bien_por_id(bid)

    # Se intentan cambiar campos inmutables: deben ignorarse por completo.
    ok, msg = bien_service.actualizar_bien(bid, {
        "descripcion": "Descripción nueva",
        "categoria_id": datos_base["categoria_id"],
        "cuenta_contable": datos_base["cuenta_contable"],
        "codigo_activo": "HACK-999",      # inmutable
        "precio_sin_iva": 999999,         # inmutable
        "estado": "07",                   # inmutable (tiene su propio flujo)
    }, uid)
    assert ok is True, msg

    bien = bien_service.obtener_bien_por_id(bid)
    assert bien["codigo_activo"] == original["codigo_activo"]
    assert float(bien["precio_sin_iva"]) == float(original["precio_sin_iva"])
    assert bien["estado"] == original["estado"]      # sigue '01', no '07'
    assert bien["descripcion"] == "Descripción nueva"  # lo editable sí cambió


def test_actualizar_bien_requiere_descripcion(bien_service, bien_dict, datos_base):
    uid = datos_base["usuario_id"]
    bid = _crear_bien(bien_service, bien_dict, datos_base)

    ok, msg = bien_service.actualizar_bien(bid, {
        "descripcion": "   ",
        "categoria_id": datos_base["categoria_id"],
        "cuenta_contable": datos_base["cuenta_contable"],
    }, uid)
    assert ok is False
    assert "descripci" in msg.lower()


def test_actualizar_bien_registra_auditoria(
    bien_service, bien_dict, datos_base, db
):
    from src.db.auditoria_repository import AuditoriaRepository

    uid = datos_base["usuario_id"]
    bid = _crear_bien(bien_service, bien_dict, datos_base)

    ok, _ = bien_service.actualizar_bien(bid, {
        "descripcion": "Editado para auditoría",
        "categoria_id": datos_base["categoria_id"],
        "cuenta_contable": datos_base["cuenta_contable"],
    }, uid)
    assert ok is True

    registros = AuditoriaRepository(db).listar_con_filtros(tabla="bien")
    assert any(
        r["accion"] == "ACTUALIZAR" and r["tabla_afectada"] == "bien"
        for r in registros
    )


def test_quien_puede_editar(crear_usuario):
    crear_usuario("adm_e", "clave_segura", "Administrador")
    crear_usuario("alm_e", "clave_segura", "Almacenista")
    crear_usuario("con_e", "clave_segura", "Consulta")

    Session.login("adm_e", "clave_segura")
    assert Session.get_instance().tiene_permiso("bienes.editar") is True
    Session.logout()

    Session.login("alm_e", "clave_segura")
    assert Session.get_instance().tiene_permiso("bienes.editar") is True
    Session.logout()

    Session.login("con_e", "clave_segura")
    assert Session.get_instance().tiene_permiso("bienes.editar") is False
