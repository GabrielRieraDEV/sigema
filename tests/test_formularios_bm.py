"""
test_formularios_bm.py — Pruebas de generación de formularios BM-1 a BM-4.

Verifica que:
- Cada formulario se genera sin errores y produce un PDF válido.
- El contenido (parámetros y metadatos) es el esperado.
- Los casos de error (departamento vacío, sin datos) se manejan bien.
- El PDF emitido se persiste y se recupera idéntico (RN-09 / NF).
"""

from __future__ import annotations

from datetime import date

import pytest


# ---------------------------------------------------------------------------
# Utilidad
# ---------------------------------------------------------------------------
def _es_pdf_valido(contenido: bytes) -> bool:
    """True si ``contenido`` parece un PDF bien formado y no trivial."""
    return (
        isinstance(contenido, (bytes, bytearray))
        and bytes(contenido).startswith(b"%PDF-")
        and b"%%EOF" in bytes(contenido)
        and len(contenido) > 800
    )


def _registrar_bien(bien_service, bien_dict, uid, **over):
    """Helper: registra un bien y devuelve su id, fallando si hay error."""
    ok, msg, bid = bien_service.registrar_bien(bien_dict(**over), uid)
    assert ok is True, msg
    return bid


# ===========================================================================
# BM-1 — Inventario
# ===========================================================================
def test_bm1_genera_pdf_valido(bien_service, formulario_service, bien_dict, datos_base):
    dep = datos_base["departamento_id"]
    uid = datos_base["usuario_id"]
    _registrar_bien(bien_service, bien_dict, uid)
    _registrar_bien(bien_service, bien_dict, uid,
                    codigo_activo="ACT-0002", codigo_nivel="N-0002")

    resultado = formulario_service.generar_bm1(dep, uid)
    ok, mensaje, pdf, parametros = resultado

    assert ok is True, mensaje
    assert _es_pdf_valido(pdf)
    assert parametros["total_bienes"] == 2
    assert parametros["departamento_id"] == dep
    assert parametros["departamento_nombre"] == "Almacén Central"


def test_bm1_departamento_sin_bienes(formulario_service, datos_base):
    """Un departamento sin bienes activos no genera BM-1."""
    resultado = formulario_service.generar_bm1(
        datos_base["departamento_id"], datos_base["usuario_id"]
    )
    assert resultado[0] is False


# ===========================================================================
# BM-2 — Movimientos
# ===========================================================================
def test_bm2_genera_pdf_valido(bien_service, formulario_service, bien_dict, datos_base):
    dep = datos_base["departamento_id"]
    uid = datos_base["usuario_id"]
    # Al registrar un bien se crea automáticamente un movimiento de
    # Incorporación en el mes actual.
    _registrar_bien(bien_service, bien_dict, uid)

    hoy = date.today()
    resultado = formulario_service.generar_bm2(
        dep, hoy.month, hoy.year, concepto=None, usuario_id=uid
    )
    ok, mensaje, pdf, parametros = resultado

    assert ok is True, mensaje
    assert _es_pdf_valido(pdf)
    assert parametros["total_movimientos"] >= 1
    assert parametros["mes"] == hoy.month
    assert parametros["anio"] == hoy.year


def test_bm2_sin_movimientos_en_periodo(
    bien_service, formulario_service, bien_dict, datos_base
):
    """Un período sin movimientos no genera BM-2."""
    dep = datos_base["departamento_id"]
    uid = datos_base["usuario_id"]
    _registrar_bien(bien_service, bien_dict, uid)

    # Período antiguo, garantizado sin movimientos.
    resultado = formulario_service.generar_bm2(
        dep, 1, 2000, concepto=None, usuario_id=uid
    )
    assert resultado[0] is False


# ===========================================================================
# BM-3 — Faltantes (Concepto 60, estado 06)
# ===========================================================================
def test_bm3_genera_pdf_valido(bien_service, formulario_service, bien_dict, datos_base):
    dep = datos_base["departamento_id"]
    uid = datos_base["usuario_id"]
    bid = _registrar_bien(bien_service, bien_dict, uid)

    # Pasar a estado 06 (inoperativo irrecuperable) requiere descripción del daño.
    ok, msg = bien_service.actualizar_estado(
        bid, "06", "Carcasa destruida, sin repuestos", uid
    )
    assert ok is True, msg

    resultado = formulario_service.generar_bm3(dep, uid)
    ok2, mensaje, pdf, parametros = resultado

    assert ok2 is True, mensaje
    assert _es_pdf_valido(pdf)
    assert parametros["total_faltantes"] == 1


def test_bm3_sin_faltantes(formulario_service, bien_service, bien_dict, datos_base):
    """Sin bienes en estado 06, no se genera BM-3."""
    uid = datos_base["usuario_id"]
    _registrar_bien(bien_service, bien_dict, uid)  # estado 01 por defecto

    resultado = formulario_service.generar_bm3(
        datos_base["departamento_id"], uid
    )
    assert resultado[0] is False


# ===========================================================================
# BM-4 — Resumen mensual (RN-08)
# ===========================================================================
def test_bm4_genera_pdf_valido(bien_service, formulario_service, bien_dict, datos_base):
    dep = datos_base["departamento_id"]
    uid = datos_base["usuario_id"]
    _registrar_bien(bien_service, bien_dict, uid)
    _registrar_bien(bien_service, bien_dict, uid,
                    codigo_activo="ACT-0002", codigo_nivel="N-0002")

    hoy = date.today()
    resultado = formulario_service.generar_bm4(dep, hoy.month, hoy.year, uid)
    ok, mensaje, pdf, parametros = resultado

    assert ok is True, mensaje
    assert _es_pdf_valido(pdf)
    assert parametros["incorporaciones"] == 2
    assert parametros["existencia_final"] == 2


# ===========================================================================
# Persistencia del PDF emitido
# ===========================================================================
def test_guardar_y_recuperar_pdf(formulario_service, sesion_admin):
    """El PDF emitido se guarda y se recupera idéntico desde la BD."""
    uid = sesion_admin
    contenido = b"%PDF-1.4 contenido de prueba\n%%EOF"

    ok, _ = formulario_service.guardar_formulario(
        "BM-1", uid, {"departamento_id": 1, "total_bienes": 5}, contenido
    )
    assert ok is True

    formularios = formulario_service.listar_formularios("BM-1")
    assert len(formularios) == 1
    fid = formularios[0]["id"]

    recuperado = formulario_service.obtener_pdf_por_id(fid)
    assert recuperado == contenido


# ===========================================================================
# Generadores a nivel unitario (sin BD): producen PDFs válidos
# ===========================================================================
def test_generadores_producen_pdf_directo():
    """Cada generador escribe un PDF válido a partir de datos en memoria."""
    import io

    from src.reports.bm1_inventario import BM1Inventario
    from src.reports.bm4_resumen import BM4Resumen

    depto = {"id": 1, "codigo": "DEP-01", "nombre": "Almacén Central"}

    # BM-1 con un bien de ejemplo.
    bienes = [{
        "clasificacion": "2-1-214-01",
        "codigo": "ACT-0001",
        "numero_identificacion": "SN-123",
        "cantidad": 1,
        "nombre_descripcion": "Silla de oficina",
        "valor_unitario": 100.0,
        "valor_total": 100.0,
        "estado": "01",
        "estado_descripcion": "OPERATIVO, EN USO, EXCELENTE ESTADO",
    }]
    buffer = io.BytesIO()
    BM1Inventario().generar(buffer, bienes, depto)
    assert _es_pdf_valido(buffer.getvalue())

    # BM-4 con un resumen de ejemplo.
    resumen = {
        "existencia_anterior": 10,
        "incorporaciones": 3,
        "desincorporaciones": 1,
        "faltantes_concepto_60": 0,
        "existencia_final": 12,
    }
    buffer4 = io.BytesIO()
    BM4Resumen().generar(buffer4, resumen, depto, 6, 2026)
    assert _es_pdf_valido(buffer4.getvalue())
