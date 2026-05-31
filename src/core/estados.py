"""
estados.py — Catálogo y reglas de negocio de los estados del bien mueble.

Fuente única de verdad (en la capa Python) de los 7 estados oficiales y
de las transiciones permitidas entre ellos.  La tabla ``catalogo_estado``
en la base de datos replica estos mismos códigos/descripciones para poder
hacer JOIN en las consultas y reportes.

Estados oficiales
-----------------
    01 - OPERATIVO, EN USO, EXCELENTE ESTADO
    02 - OPERATIVO, EN USO PERO REQUIERE REPARACIÓN
    03 - OPERATIVO, SIN USO, EN EXCELENTE ESTADO
    04 - OPERATIVO, SIN USO, PERO REQUIERE REPARACIÓN
    05 - INOPERATIVO, PERO RECUPERABLE
    06 - INOPERATIVO, IRRECUPERABLE
    07 - DESINCORPORADO EN DESUSO

Reglas
------
- 01–04 (OPERATIVO): pueden cambiar libremente entre sí. No generan BM-2.
- 05 (INOPERATIVO RECUPERABLE): requiere descripción del daño. No genera BM-2.
- 06 (INOPERATIVO IRRECUPERABLE): requiere descripción del daño, genera
  entrada en BM-3 (Concepto 60) y queda bloqueado (solo puede pasar a 07).
- 07 (DESINCORPORADO EN DESUSO): requiere motivo de desincorporación,
  genera entrada en BM-2 y es un estado terminal.
"""

from __future__ import annotations

# Código de estado por defecto al registrar un bien nuevo.
ESTADO_DEFECTO = "01"

# Descripciones oficiales (código -> descripción completa).
ESTADOS: dict[str, str] = {
    "01": "OPERATIVO, EN USO, EXCELENTE ESTADO",
    "02": "OPERATIVO, EN USO PERO REQUIERE REPARACIÓN",
    "03": "OPERATIVO, SIN USO, EN EXCELENTE ESTADO",
    "04": "OPERATIVO, SIN USO, PERO REQUIERE REPARACIÓN",
    "05": "INOPERATIVO, PERO RECUPERABLE",
    "06": "INOPERATIVO, IRRECUPERABLE",
    "07": "DESINCORPORADO EN DESUSO",
}

# Agrupaciones por naturaleza del estado.
OPERATIVOS = frozenset({"01", "02", "03", "04"})
INOPERATIVOS = frozenset({"05", "06"})
DESINCORPORADO = "07"

# Estados que exigen "descripción del daño".
REQUIERE_DESCRIPCION_DANO = frozenset({"05", "06"})
# Estado que exige "motivo de desincorporación".
REQUIERE_MOTIVO_DESINCORPORACION = "07"

# Estados que disparan generación automática de formularios.
GENERA_BM3 = "06"   # entra en BM-3 (Concepto 60)
GENERA_BM2 = "07"   # entra en BM-2


def descripcion(codigo: str | None) -> str:
    """Devuelve la descripción completa de un código de estado."""
    if not codigo:
        return ""
    return ESTADOS.get(codigo, codigo)


def etiqueta(codigo: str | None, desc: str | None = None) -> str:
    """Construye la etiqueta "código - DESCRIPCIÓN" usada en la UI y PDFs.

    Si ``desc`` se proporciona (p.ej. proveniente de catalogo_estado),
    se usa; de lo contrario se toma de :data:`ESTADOS`.
    """
    if not codigo:
        return ""
    texto = desc if desc else ESTADOS.get(codigo, "")
    return f"{codigo} - {texto}" if texto else codigo


def es_valido(codigo: str | None) -> bool:
    """True si el código pertenece a los 7 estados oficiales."""
    return codigo in ESTADOS


def transiciones_permitidas(actual: str | None) -> list[str]:
    """Devuelve los códigos a los que ``actual`` puede transicionar.

    Reglas:
    - 07 es terminal -> no permite ninguna transición.
    - 06 solo puede pasar a 07.
    - 01–04 pueden pasar a cualquier otro estado (libre entre operativos
      y degradación a 05/06/07).
    - 05 puede recuperarse (01–04), agravarse (06) o desincorporarse (07).
    """
    if actual == DESINCORPORADO:  # 07 terminal
        return []
    if actual == "06":
        return ["07"]
    if actual in OPERATIVOS:
        return [c for c in ESTADOS if c != actual]
    if actual == "05":
        return ["01", "02", "03", "04", "06", "07"]
    # Estado desconocido / heredado: permitir cualquier estado válido.
    return [c for c in ESTADOS if c != actual]


def transicion_valida(actual: str | None, nuevo: str | None) -> bool:
    """True si se permite pasar de ``actual`` a ``nuevo``."""
    return nuevo in transiciones_permitidas(actual)


def color_fondo(codigo: str | None) -> str | None:
    """Color de fondo de fila/indicador según el estado (o None).

    - 01–04 (operativos): sin color especial.
    - 05: amarillo claro.
    - 06: rojo claro.
    - 07: gris claro.
    """
    return {
        "05": "#FFF4CC",  # amarillo claro
        "06": "#F8D2D2",  # rojo claro
        "07": "#E0E0E0",  # gris claro
    }.get(codigo or "")


def color_indicador(codigo: str | None) -> str:
    """Color del texto/indicador del estado en el diálogo de cambio.

    Operativos en verde, inoperativos en amarillo/rojo, desincorporado gris.
    """
    if codigo in OPERATIVOS:
        return "#1B7F3A"   # verde
    if codigo == "05":
        return "#B8860B"   # amarillo oscuro (legible)
    if codigo == "06":
        return "#CC0000"   # rojo
    if codigo == DESINCORPORADO:
        return "#5C6B73"   # gris
    return "#333333"
