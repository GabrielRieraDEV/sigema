"""
bien_service.py — Lógica de negocio para el Módulo A (Bienes Muebles).

Aplica todas las reglas del SRS antes de delegar a los repositorios:

- RN-01: código activo único
- RN-02: nunca eliminar, solo cambiar estado
- RN-03: orden de compra es referencia opcional
- RN-04: desincorporación requiere motivo
- RN-05: precio siempre sin IVA
- RN-06: vida útil default 60 meses
"""

from __future__ import annotations

from typing import Any

from src.db.bien_repository import BienRepository
from src.db.movimiento_repository import MovimientoRepository


# Campos obligatorios al registrar un bien (SRS §4.1.1)
_CAMPOS_OBLIGATORIOS = [
    "codigo_activo",
    "codigo_nivel",
    "descripcion",
    "categoria_id",
    "fecha_compra",
    "precio_sin_iva",
    "moneda",
    "departamento_id",
    "cuenta_contable",
]


class BienService:
    """Orquesta las operaciones de bienes muebles con validaciones
    de reglas de negocio.

    Todos los métodos públicos retornan tuplas ``(ok, mensaje[, dato])``
    para que la UI pueda mostrar el resultado sin atrapar excepciones.
    """

    def __init__(
        self,
        bien_repo: BienRepository,
        movimiento_repo: MovimientoRepository,
    ):
        self._bien_repo = bien_repo
        self._mov_repo = movimiento_repo

    # ------------------------------------------------------------------
    # Registrar bien (CU-01)
    # ------------------------------------------------------------------
    def registrar_bien(
        self, datos: dict[str, Any], usuario_id: int
    ) -> tuple[bool, str, int | None]:
        """Registra un nuevo bien mueble.

        Validaciones aplicadas:
        - Campos obligatorios presentes y no vacíos.
        - RN-01: código activo no duplicado.
        - RN-05: precio > 0.
        - RN-06: vida útil default 60 meses si no se proporciona.

        Al crear el bien, también registra un movimiento de tipo
        'Incorporación'.

        Returns
        -------
        tuple[bool, str, int | None]
            (éxito, mensaje, id_del_bien_o_None)
        """
        # --- Campos obligatorios ---
        for campo in _CAMPOS_OBLIGATORIOS:
            valor = datos.get(campo)
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                return (
                    False,
                    f"El campo '{campo}' es obligatorio y no puede estar vacío.",
                    None,
                )

        # --- RN-01: código activo único ---
        existente = self._bien_repo.buscar_por_codigo(datos["codigo_activo"])
        if existente is not None:
            return (
                False,
                f"Ya existe un bien con el código activo "
                f"'{datos['codigo_activo']}'. El código debe ser único (RN-01).",
                None,
            )

        # --- RN-05: precio sin IVA > 0 ---
        try:
            precio = float(datos["precio_sin_iva"])
        except (ValueError, TypeError):
            return (False, "El precio unitario debe ser un número válido.", None)

        if precio <= 0:
            return (
                False,
                "El precio unitario (sin IVA) debe ser mayor que cero (RN-05).",
                None,
            )

        # --- RN-06: vida útil default 60 meses ---
        if not datos.get("vida_util_meses"):
            datos["vida_util_meses"] = 60

        # --- Defaults para campos opcionales ---
        datos.setdefault("marca", None)
        datos.setdefault("modelo", None)
        datos.setdefault("serial_bien", None)
        datos.setdefault("color", None)
        datos.setdefault("tipo", None)
        datos.setdefault("num_piezas", 1)
        datos.setdefault("orden_compra", None)       # RN-03: opcional
        datos.setdefault("observaciones", None)
        datos.setdefault("estado", "Activo")
        datos["creado_por"] = usuario_id

        # --- Persistir ---
        try:
            bien_id = self._bien_repo.crear(datos)

            # Registrar movimiento de Incorporación (CU-01 postcondición)
            self._mov_repo.registrar(
                bien_id=bien_id,
                tipo="Incorporación",
                dept_origen=None,
                dept_destino=datos["departamento_id"],
                motivo="Alta de bien nuevo",
                responsable=None,
                usuario_id=usuario_id,
            )

            return (True, "Bien registrado exitosamente.", bien_id)

        except Exception as exc:
            return (False, f"Error al registrar el bien: {exc}", None)

    # ------------------------------------------------------------------
    # Actualizar estado (CU-03, CU-04)
    # ------------------------------------------------------------------
    def actualizar_estado(
        self,
        bien_id: int,
        nuevo_estado: str,
        motivo: str | None,
        responsable: str | None,
        usuario_id: int,
    ) -> tuple[bool, str]:
        """Cambia el estado de un bien aplicando reglas de negocio.

        - RN-02: no se elimina, solo se cambia el estado.
        - RN-04: desincorporación requiere motivo.
        - Si nuevo_estado == 'Faltante', requiere motivo Y responsable.

        Returns
        -------
        tuple[bool, str]
            (éxito, mensaje)
        """
        # Validar que el estado sea válido
        estados_validos = {"Activo", "En desuso", "Faltante"}
        if nuevo_estado not in estados_validos:
            return (
                False,
                f"Estado '{nuevo_estado}' no válido. "
                f"Use: {', '.join(sorted(estados_validos))}.",
            )

        # RN-04: motivo obligatorio para En desuso y Faltante
        if nuevo_estado in ("En desuso", "Faltante"):
            if not motivo or not motivo.strip():
                return (
                    False,
                    "Debe indicar un motivo para el cambio de estado (RN-04).",
                )

        # Faltante requiere responsable
        if nuevo_estado == "Faltante":
            if not responsable or not responsable.strip():
                return (
                    False,
                    "Debe indicar el responsable del bien faltante "
                    "(Concepto 60).",
                )

        # Obtener datos actuales del bien
        bien = self._bien_repo.buscar_por_id(bien_id)
        if bien is None:
            return (False, f"No se encontró un bien con id {bien_id}.")

        if bien["estado"] == nuevo_estado:
            return (False, f"El bien ya se encuentra en estado '{nuevo_estado}'.")

        # Determinar tipo de movimiento
        if nuevo_estado == "En desuso":
            tipo_mov = "Desincorporación"
        elif nuevo_estado == "Faltante":
            tipo_mov = "Marcado como faltante"
        else:
            tipo_mov = "Incorporación"  # Reactivación

        try:
            # Actualizar estado en tabla bien
            ok = self._bien_repo.actualizar_estado(
                bien_id, nuevo_estado, motivo, usuario_id
            )
            if not ok:
                return (False, "No se pudo actualizar el estado del bien.")

            # Registrar movimiento
            self._mov_repo.registrar(
                bien_id=bien_id,
                tipo=tipo_mov,
                dept_origen=bien["departamento_id"],
                dept_destino=bien["departamento_id"],
                motivo=motivo,
                responsable=responsable if nuevo_estado == "Faltante" else None,
                usuario_id=usuario_id,
            )

            return (True, f"Estado actualizado a '{nuevo_estado}' correctamente.")

        except Exception as exc:
            return (False, f"Error al actualizar el estado: {exc}")

    # ------------------------------------------------------------------
    # Consultas (CU-02)
    # ------------------------------------------------------------------
    def buscar_bienes(
        self,
        codigo: str | None = None,
        descripcion: str | None = None,
        departamento_id: int | None = None,
        estado: str | None = None,
    ) -> list[dict[str, Any]]:
        """Busca bienes aplicando filtros opcionales."""
        return self._bien_repo.buscar_por_filtros(
            codigo=codigo,
            descripcion=descripcion,
            departamento_id=departamento_id,
            estado=estado,
        )

    def obtener_bien(self, codigo_activo: str) -> dict[str, Any] | None:
        """Obtiene un bien por su código activo."""
        return self._bien_repo.buscar_por_codigo(codigo_activo)

    def obtener_bien_por_id(self, bien_id: int) -> dict[str, Any] | None:
        """Obtiene un bien por su id."""
        return self._bien_repo.buscar_por_id(bien_id)

    # ------------------------------------------------------------------
    # Catálogos (para poblar combos en la UI)
    # ------------------------------------------------------------------
    def obtener_categorias(self) -> list[dict[str, Any]]:
        """Retorna categorías activas para combo."""
        return self._bien_repo.listar_categorias()

    def obtener_departamentos(self) -> list[dict[str, Any]]:
        """Retorna departamentos activos para combo."""
        return self._bien_repo.listar_departamentos()

    def obtener_cuentas_contables(self) -> list[dict[str, Any]]:
        """Retorna cuentas contables activas para combo."""
        return self._bien_repo.listar_cuentas_contables()
