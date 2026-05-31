"""
donacion_service.py — Lógica de negocio del módulo de Donaciones.

Una donación es una incorporación de bien SIN orden de compra ni
proveedor comercial.  En su lugar tiene un donante y un acta/documento.

Reglas (RD):
- RD-01: requiere nombre del donante (obligatorio).
- RD-02: el bien donado se registra con estado 01 (operativo, en uso,
  excelente estado) por defecto.
- RD-03: no requiere orden de compra ni precio si se desconoce — el
  precio puede ser 0 o el valor estimado.
- RD-04: genera automáticamente la entrada en BM-2 como incorporación
  con concepto "DONACIÓN - <donante>" (vía el movimiento del bien).
- RD-05: queda en auditoría igual que cualquier incorporación
  (auditoría del bien + auditoría de la donación).
"""

from __future__ import annotations

from typing import Any

from src.core import estados
from src.core.bien_service import BienService
from src.db.donacion_repository import DonacionRepository


class DonacionService:
    """Orquesta el registro y la consulta de donaciones.

    Reutiliza :class:`BienService` para crear el bien (validaciones,
    movimiento de incorporación y auditoría) y agrega el registro de la
    donación.
    """

    def __init__(
        self,
        bien_service: BienService,
        donacion_repo: DonacionRepository,
    ):
        self._bien_service = bien_service
        self._donacion_repo = donacion_repo

    @property
    def bien_service(self) -> BienService:
        return self._bien_service

    # ------------------------------------------------------------------
    # Registro de donación
    # ------------------------------------------------------------------
    def registrar_donacion(
        self,
        datos_bien: dict[str, Any],
        datos_donacion: dict[str, Any],
        usuario_id: int,
    ) -> tuple[bool, str, int | None]:
        """Registra un bien recibido en donación y su acta de donación.

        Returns
        -------
        tuple[bool, str, int | None]
            (éxito, mensaje, id_del_bien_o_None)
        """
        # RD-01: donante obligatorio
        donante = (datos_donacion.get("donante") or "").strip()
        if not donante:
            return (False, "El nombre del donante es obligatorio (RD-01).", None)

        fecha_donacion = datos_donacion.get("fecha_donacion")
        if not fecha_donacion:
            return (False, "La fecha de donación es obligatoria.", None)

        # Preparar datos del bien según reglas de donación.
        datos = dict(datos_bien)
        datos["origen"] = "DONACION"
        datos["estado"] = estados.ESTADO_DEFECTO          # RD-02: estado 01
        datos["orden_compra"] = None                      # RD-03: sin OC
        if not datos.get("precio_sin_iva"):
            datos["precio_sin_iva"] = 0                    # RD-03: valor estimado

        # RD-04: concepto del movimiento de incorporación para el BM-2.
        motivo = f"DONACIÓN - {donante}"

        # Crear el bien (valida, registra movimiento BM-2 y audita: RD-05).
        ok, mensaje, bien_id = self._bien_service.registrar_bien(
            datos, usuario_id, motivo_incorporacion=motivo
        )
        if not ok or bien_id is None:
            return (False, mensaje, None)

        # Registrar la donación (también auditada: RD-05).
        try:
            self._donacion_repo.registrar({
                "bien_id": bien_id,
                "donante": donante,
                "tipo_donante": datos_donacion.get("tipo_donante"),
                "acta_numero": datos_donacion.get("acta_numero"),
                "fecha_donacion": fecha_donacion,
                "descripcion": datos_donacion.get("descripcion"),
                "registrado_por": usuario_id,
            })
        except Exception as exc:
            return (
                True,
                f"El bien donado se registró (id {bien_id}), pero falló el "
                f"registro del acta de donación: {exc}",
                bien_id,
            )

        return (True, "Donación registrada exitosamente.", bien_id)

    # ------------------------------------------------------------------
    # Consultas (solo lectura)
    # ------------------------------------------------------------------
    def listar_donaciones(
        self,
        donante: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista donaciones con filtros opcionales."""
        return self._donacion_repo.listar_todos(donante, fecha_desde, fecha_hasta)

    def obtener_donacion_por_bien(self, bien_id: int) -> dict[str, Any] | None:
        """Devuelve la donación asociada a un bien, si existe."""
        return self._donacion_repo.buscar_por_bien(bien_id)

    def obtener_bien_por_id(self, bien_id: int) -> dict[str, Any] | None:
        """Atajo para abrir el detalle del bien donado."""
        return self._bien_service.obtener_bien_por_id(bien_id)
