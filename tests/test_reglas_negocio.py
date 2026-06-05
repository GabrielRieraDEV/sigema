"""
test_reglas_negocio.py — Una prueba por cada regla de negocio (RN-01 a RN-13).

Las reglas provienen del SRS (§ Reglas de Negocio):

    RN-01  Código activo único.
    RN-02  No se elimina un bien; solo se cambia su estado.
    RN-03  La orden de compra es una referencia opcional.
    RN-04  Toda desincorporación registra motivo.
    RN-05  El precio se registra siempre sin IVA (> 0 en compras).
    RN-06  Vida útil estándar de 60 meses por defecto.
    RN-07  Los formularios mantienen los códigos GOB-900-FM.
    RN-08  El BM-4 calcula: anterior + incorporaciones - desincorporaciones.
    RN-09  Los formularios emitidos no se modifican, solo se anulan.
    RN-10  El perfil Consulta no puede crear/modificar/eliminar.
    RN-11  Solo el Administrador gestiona cuentas de usuario.
    RN-12  Toda operación queda en el log de auditoría (usuario, fecha, hora).
    RN-13  Los bienes migrados entran con estado '01' y código original.
"""

from __future__ import annotations

from datetime import date

from src.core.auth import Session


# ===========================================================================
# RN-01 — Código activo único
# ===========================================================================
def test_rn01_codigo_activo_unico(bien_service, bien_dict, datos_base):
    uid = datos_base["usuario_id"]

    ok, _, _ = bien_service.registrar_bien(
        bien_dict(codigo_activo="ACT-0001"), uid
    )
    assert ok is True

    # Segundo bien con el mismo código activo: debe rechazarse.
    ok2, msg2, bid2 = bien_service.registrar_bien(
        bien_dict(codigo_activo="ACT-0001", codigo_nivel="N-0002"), uid
    )
    assert ok2 is False
    assert bid2 is None
    assert "RN-01" in msg2 or "único" in msg2.lower()


# ===========================================================================
# RN-02 — No se elimina un bien; solo se cambia su estado
# ===========================================================================
def test_rn02_no_se_elimina_solo_cambia_estado(
    bien_service, bien_dict, datos_base, db
):
    from src.db.bien_repository import BienRepository

    uid = datos_base["usuario_id"]
    ok, _, bid = bien_service.registrar_bien(bien_dict(), uid)
    assert ok is True

    # El repositorio no expone ninguna operación de borrado.
    repo = BienRepository(db)
    assert not hasattr(repo, "eliminar")
    assert not hasattr(repo, "borrar")
    assert not hasattr(repo, "delete")

    # Desincorporar (estado 07) cambia el estado pero el registro persiste.
    ok2, _ = bien_service.actualizar_estado(bid, "07", "Equipo obsoleto", uid)
    assert ok2 is True

    bien = bien_service.obtener_bien_por_id(bid)
    assert bien is not None
    assert bien["estado"] == "07"


# ===========================================================================
# RN-03 — La orden de compra es opcional
# ===========================================================================
def test_rn03_orden_compra_opcional(bien_service, bien_dict, datos_base):
    uid = datos_base["usuario_id"]
    datos = bien_dict()
    datos.pop("orden_compra", None)  # sin orden de compra

    ok, _, bid = bien_service.registrar_bien(datos, uid)
    assert ok is True

    bien = bien_service.obtener_bien_por_id(bid)
    assert bien["orden_compra"] is None


# ===========================================================================
# RN-04 — Toda desincorporación registra el motivo
# ===========================================================================
def test_rn04_desincorporacion_requiere_motivo(
    bien_service, bien_dict, datos_base
):
    uid = datos_base["usuario_id"]
    ok, _, bid = bien_service.registrar_bien(bien_dict(), uid)
    assert ok is True

    # Pasar a 07 (desincorporado) sin motivo: rechazado.
    ok2, msg2 = bien_service.actualizar_estado(bid, "07", "", uid)
    assert ok2 is False
    assert "motivo" in msg2.lower()

    # Con motivo: aceptado.
    ok3, _ = bien_service.actualizar_estado(
        bid, "07", "Baja por obsolescencia", uid
    )
    assert ok3 is True


# ===========================================================================
# RN-05 — El precio se registra sin IVA y debe ser > 0 en compras
# ===========================================================================
def test_rn05_precio_sin_iva_positivo(bien_service, bien_dict, datos_base):
    uid = datos_base["usuario_id"]

    # Precio 0 en una compra: rechazado.
    ok, msg, _ = bien_service.registrar_bien(
        bien_dict(precio_sin_iva=0), uid
    )
    assert ok is False
    assert "RN-05" in msg or "cero" in msg.lower()

    # Precio positivo: aceptado y almacenado tal cual (sin transformación IVA).
    ok2, _, bid = bien_service.registrar_bien(
        bien_dict(precio_sin_iva=250.50), uid
    )
    assert ok2 is True
    bien = bien_service.obtener_bien_por_id(bid)
    assert float(bien["precio_sin_iva"]) == 250.50


# ===========================================================================
# RN-06 — Vida útil estándar de 60 meses por defecto
# ===========================================================================
def test_rn06_vida_util_default_60(bien_service, bien_dict, datos_base):
    uid = datos_base["usuario_id"]

    datos = bien_dict()
    datos.pop("vida_util_meses", None)  # no se especifica
    ok, _, bid = bien_service.registrar_bien(datos, uid)
    assert ok is True
    assert bien_service.obtener_bien_por_id(bid)["vida_util_meses"] == 60

    # Si se especifica, se respeta el valor indicado.
    ok2, _, bid2 = bien_service.registrar_bien(
        bien_dict(codigo_activo="ACT-0002", codigo_nivel="N-0002",
                  vida_util_meses=36),
        uid,
    )
    assert ok2 is True
    assert bien_service.obtener_bien_por_id(bid2)["vida_util_meses"] == 36


# ===========================================================================
# RN-07 — Los formularios mantienen los códigos GOB-900-FM
# ===========================================================================
def test_rn07_codigos_gob_en_formularios():
    from src.reports.bm1_inventario import BM1Inventario
    from src.reports.bm2_movimientos import BM2Movimientos
    from src.reports.bm3_faltantes import BM3Faltantes
    from src.reports.bm4_resumen import BM4Resumen

    for cls in (BM1Inventario, BM2Movimientos, BM3Faltantes, BM4Resumen):
        assert cls.CODIGO_GOB.startswith("GOB-900-FM"), cls.__name__


# ===========================================================================
# RN-08 — BM-4: existencia_final = anterior + incorporaciones - desincorp.
# ===========================================================================
def test_rn08_bm4_calculo_existencia(
    bien_service, bien_dict, formulario_repo, datos_base
):
    dep = datos_base["departamento_id"]
    uid = datos_base["usuario_id"]

    # 3 incorporaciones (bienes nuevos) en el mes actual.
    ids = []
    for i in range(3):
        ok, msg, bid = bien_service.registrar_bien(
            bien_dict(codigo_activo=f"ACT-200{i}", codigo_nivel=f"N-200{i}"),
            uid,
        )
        assert ok is True, msg
        ids.append(bid)

    # 1 desincorporación en el mes.
    ok, msg = bien_service.actualizar_estado(ids[0], "07", "Baja", uid)
    assert ok is True, msg

    hoy = date.today()
    resumen = formulario_repo.obtener_resumen_mensual(dep, hoy.month, hoy.year)

    assert resumen["incorporaciones"] == 3
    assert resumen["desincorporaciones"] == 1
    assert resumen["faltantes_concepto_60"] == 0
    # Todos creados este mes -> sin existencia anterior.
    assert resumen["existencia_anterior"] == 0

    esperado = (
        resumen["existencia_anterior"]
        + resumen["incorporaciones"]
        - resumen["desincorporaciones"]
        - resumen["faltantes_concepto_60"]
    )
    assert resumen["existencia_final"] == esperado
    assert resumen["existencia_final"] == 2


# ===========================================================================
# RN-09 — Los formularios emitidos no se modifican, solo se anulan
# ===========================================================================
def test_rn09_formularios_solo_se_anulan(formulario_service, sesion_admin):
    uid = sesion_admin

    ok, _ = formulario_service.guardar_formulario(
        "BM-1", uid, {"departamento_id": 1}, b"%PDF-1.4 contenido"
    )
    assert ok is True

    formularios = formulario_service.listar_formularios("BM-1")
    assert len(formularios) == 1
    fid = formularios[0]["id"]
    assert formularios[0]["estado"] == "Vigente"

    # Anular sin motivo: rechazado (RN-09).
    ok2, msg2 = formulario_service.anular_formulario(fid, "")
    assert ok2 is False
    assert "motivo" in msg2.lower()

    # Anular con motivo: aceptado.
    ok3, _ = formulario_service.anular_formulario(fid, "Error en los datos")
    assert ok3 is True
    assert formulario_service.listar_formularios("BM-1")[0]["estado"] == "Anulado"

    # Anular de nuevo: ya está anulado.
    ok4, _ = formulario_service.anular_formulario(fid, "otra razón")
    assert ok4 is False

    # No existe ningún método de modificación de formularios emitidos.
    assert not hasattr(formulario_service._repo, "actualizar")
    assert not hasattr(formulario_service._repo, "modificar")


# ===========================================================================
# RN-10 — El perfil Consulta no puede crear/modificar/eliminar
# ===========================================================================
def test_rn10_perfil_consulta_solo_lectura(crear_usuario):
    crear_usuario("consulta1", "clave_segura", "Consulta")
    assert Session.login("consulta1", "clave_segura") is True

    s = Session.get_instance()
    # Puede ver.
    assert s.tiene_permiso("bienes.ver") is True
    assert s.tiene_permiso("formularios.ver") is True
    # No puede modificar nada.
    assert s.tiene_permiso("bienes.crear") is False
    assert s.tiene_permiso("bienes.editar_estado") is False
    assert s.tiene_permiso("formularios.generar") is False
    assert s.tiene_permiso("usuarios.gestionar") is False


# ===========================================================================
# RN-11 — Solo el Administrador gestiona cuentas de usuario
# ===========================================================================
def test_rn11_solo_admin_gestiona_usuarios(crear_usuario):
    crear_usuario("admin1", "clave_segura", "Administrador")
    crear_usuario("almacen1", "clave_segura", "Almacenista")
    crear_usuario("consulta1", "clave_segura", "Consulta")

    Session.login("admin1", "clave_segura")
    assert Session.get_instance().tiene_permiso("usuarios.gestionar") is True
    Session.logout()

    Session.login("almacen1", "clave_segura")
    assert Session.get_instance().tiene_permiso("usuarios.gestionar") is False
    Session.logout()

    Session.login("consulta1", "clave_segura")
    assert Session.get_instance().tiene_permiso("usuarios.gestionar") is False


# ===========================================================================
# RN-12 — Toda operación queda en auditoría (usuario, fecha, hora)
# ===========================================================================
def test_rn12_auditoria_registra_operaciones(
    bien_service, bien_dict, sesion_admin, db
):
    from src.db.auditoria_repository import AuditoriaRepository

    # Crear un bien con sesión activa debe generar un registro de auditoría.
    ok, msg, _ = bien_service.registrar_bien(bien_dict(), sesion_admin)
    assert ok is True, msg

    registros = AuditoriaRepository(db).listar_con_filtros(tabla="bien")
    coincidencias = [
        r for r in registros
        if r["accion"] == "CREAR" and r["tabla_afectada"] == "bien"
    ]
    assert coincidencias, "No se registró la auditoría de creación del bien"

    entrada = coincidencias[0]
    assert entrada["usuario_username"] == "tester_admin"
    assert entrada["fecha_hora"] is not None


# ===========================================================================
# RN-13 — Bienes migrados entran con estado '01' y código original preservado
# ===========================================================================
def test_rn13_migracion_estado_activo_preserva_codigo(db, datos_base):
    from src.core.migracion import Migrador
    from src.db.bien_repository import BienRepository

    uid = datos_base["usuario_id"]
    migrador = Migrador(db, usuario_id=uid, auto_crear_catalogos=True)

    registros = [{
        "codigo_activo": "FOX-001",
        "descripcion": "Escritorio de madera del sistema anterior",
        "departamento": "Administración",
        "cuenta_contable": "2-1-214-01",
        "_fila": 1,
    }]

    validos, errores = migrador.validar_todos(registros)
    assert errores == [], errores
    assert len(validos) == 1

    resultado = migrador.migrar(validos, usuario_id=uid)
    assert resultado["insertados"] == 1
    assert resultado["fallidos"] == 0

    bien = BienRepository(db).buscar_por_codigo("FOX-001")
    assert bien is not None
    assert bien["codigo_activo"] == "FOX-001"   # código original preservado
    assert bien["estado"] == "01"               # estado 'Activo' (operativo)
    assert bien["origen"] == "COMPRA"
