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

from src.core import estados
from src.core.auditoria import registrar_auditoria
from src.db.bien_repository import BienRepository, CAMPOS_EDITABLES
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
        self,
        datos: dict[str, Any],
        usuario_id: int,
        motivo_incorporacion: str = "Alta de bien nuevo",
    ) -> tuple[bool, str, int | None]:
        """Registra un nuevo bien mueble.

        Validaciones aplicadas:
        - Campos obligatorios presentes y no vacíos.
        - RN-01: código activo no duplicado.
        - RN-05: precio > 0 para compras (las donaciones admiten 0).
        - RN-06: vida útil default 60 meses si no se proporciona.

        Al crear el bien, también registra un movimiento de tipo
        'Incorporación'.  El texto ``motivo_incorporacion`` se usa como
        motivo de ese movimiento (p.ej. el módulo de donaciones pasa
        ``"DONACIÓN - <donante>"`` para que aparezca así en el BM-2).

        ``datos['origen']`` indica el origen del bien ('COMPRA' por
        defecto o 'DONACION').

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

        # --- Origen del bien (COMPRA por defecto / DONACION) ---
        origen = (datos.get("origen") or "COMPRA").upper()
        if origen not in ("COMPRA", "DONACION"):
            return (False, f"Origen '{origen}' no válido (COMPRA/DONACION).", None)

        # --- RN-05: precio sin IVA > 0 (las donaciones admiten 0) ---
        try:
            precio = float(datos.get("precio_sin_iva") or 0)
        except (ValueError, TypeError):
            return (False, "El precio unitario debe ser un número válido.", None)

        if origen == "DONACION":
            if precio < 0:
                return (False, "El valor estimado no puede ser negativo.", None)
        elif precio <= 0:
            return (
                False,
                "El precio unitario (sin IVA) debe ser mayor que cero (RN-05).",
                None,
            )
        datos["precio_sin_iva"] = precio

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
        datos["origen"] = origen

        # Estado inicial: por defecto 01 (operativo). Validar contra el
        # catálogo de los 7 estados oficiales.
        estado_inicial = datos.get("estado") or estados.ESTADO_DEFECTO
        if not estados.es_valido(estado_inicial):
            return (
                False,
                f"El estado '{estado_inicial}' no es válido. "
                f"Use un código del catálogo (01–07).",
                None,
            )
        datos["estado"] = estado_inicial
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
                motivo=motivo_incorporacion,
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
        usuario_id: int,
    ) -> tuple[bool, str]:
        """Cambia el estado de un bien aplicando las reglas de los 7 estados.

        Reglas (ver :mod:`src.core.estados`):
        - 01–04 (operativos): cambian libremente entre sí; no generan BM-2.
        - 05 (inoperativo recuperable): requiere descripción del daño; no
          genera BM-2 todavía.
        - 06 (inoperativo irrecuperable): requiere descripción del daño,
          genera entrada en BM-3 (Concepto 60) y queda bloqueado salvo a 07.
        - 07 (desincorporado en desuso): requiere motivo de desincorporación,
          genera entrada en BM-2 y es terminal.

        El parámetro ``motivo`` transporta la descripción del daño (05/06)
        o el motivo de desincorporación (07) según el estado destino.

        Returns
        -------
        tuple[bool, str]
            (éxito, mensaje)
        """
        # Validar que el código de estado destino sea oficial
        if not estados.es_valido(nuevo_estado):
            return (
                False,
                f"Estado '{nuevo_estado}' no válido. "
                f"Use un código del catálogo (01–07).",
            )

        # Obtener datos actuales del bien
        bien = self._bien_repo.buscar_por_id(bien_id)
        if bien is None:
            return (False, f"No se encontró un bien con id {bien_id}.")

        actual = bien.get("estado")
        if actual == nuevo_estado:
            return (
                False,
                f"El bien ya se encuentra en el estado "
                f"{estados.etiqueta(nuevo_estado)}.",
            )

        # Validar transición permitida
        if not estados.transicion_valida(actual, nuevo_estado):
            if actual == estados.DESINCORPORADO:
                return (
                    False,
                    "El bien está DESINCORPORADO (07): es un estado terminal "
                    "y no puede cambiar a ningún otro estado.",
                )
            if actual == "06":
                return (
                    False,
                    "El bien está INOPERATIVO IRRECUPERABLE (06): solo puede "
                    "pasar a DESINCORPORADO EN DESUSO (07).",
                )
            return (
                False,
                f"No se permite cambiar del estado {estados.etiqueta(actual)} "
                f"al estado {estados.etiqueta(nuevo_estado)}.",
            )

        motivo = (motivo or "").strip()

        # Campos obligatorios según el estado destino
        if nuevo_estado in estados.REQUIERE_DESCRIPCION_DANO and not motivo:
            return (
                False,
                "Debe indicar la descripción del daño para los estados "
                "INOPERATIVOS (05/06).",
            )
        if nuevo_estado == estados.REQUIERE_MOTIVO_DESINCORPORACION and not motivo:
            return (
                False,
                "Debe indicar el motivo de desincorporación (estado 07).",
            )

        try:
            # Actualizar estado en la tabla bien
            ok = self._bien_repo.actualizar_estado(
                bien_id, nuevo_estado, motivo or None, usuario_id
            )
            if not ok:
                return (False, "No se pudo actualizar el estado del bien.")

            # Movimientos automáticos:
            #  - 07 -> Desincorporación (entra en BM-2)
            #  - 06 -> Marcado como faltante / Concepto 60 (entra en BM-3)
            #  - 01-04 y 05 -> no generan movimiento en BM-2
            dept = bien["departamento_id"]
            if nuevo_estado == estados.GENERA_BM2:  # 07
                self._mov_repo.registrar(
                    bien_id=bien_id,
                    tipo="Desincorporación",
                    dept_origen=dept,
                    dept_destino=dept,
                    motivo=motivo,
                    responsable=None,
                    usuario_id=usuario_id,
                    observaciones="Desincorporación por estado 07 (en desuso).",
                )
            elif nuevo_estado == estados.GENERA_BM3:  # 06
                self._mov_repo.registrar(
                    bien_id=bien_id,
                    tipo="Marcado como faltante",
                    dept_origen=dept,
                    dept_destino=dept,
                    motivo=motivo,
                    responsable=None,
                    usuario_id=usuario_id,
                    observaciones=(
                        "Inoperativo irrecuperable (Concepto 60) — entra en BM-3."
                    ),
                )

            return (
                True,
                f"Estado actualizado a {estados.etiqueta(nuevo_estado)} "
                f"correctamente.",
            )

        except Exception as exc:
            return (False, f"Error al actualizar el estado: {exc}")

    # ------------------------------------------------------------------
    # Editar bien (corrección de datos — Administrador y Almacenista)
    # ------------------------------------------------------------------
    def actualizar_bien(
        self,
        bien_id: int,
        datos: dict[str, Any],
        usuario_id: int,
    ) -> tuple[bool, str]:
        """Corrige los datos editables de un bien ya registrado.

        Permite enmendar errores de carga o reclasificar la cuenta contable
        sin alterar la identidad (código), la contabilidad (precio, fecha,
        moneda), el estado ni el origen, que permanecen inmutables.

        Cada cambio queda registrado en auditoría con sus valores anterior
        y nuevo (RN-12). El cambio de estado y el de departamento tienen sus
        propios flujos (no se hacen aquí).

        Returns
        -------
        tuple[bool, str]
            (éxito, mensaje)
        """
        bien_antes = self._bien_repo.buscar_por_id(bien_id)
        if bien_antes is None:
            return (False, f"No se encontró un bien con id {bien_id}.")

        # --- Validaciones de los campos obligatorios editables ---
        descripcion = (datos.get("descripcion") or "").strip()
        if not descripcion:
            return (False, "La descripción es obligatoria.")
        if datos.get("categoria_id") is None:
            return (False, "Debe seleccionar una categoría.")
        if not datos.get("cuenta_contable"):
            return (False, "Debe seleccionar una cuenta contable.")

        try:
            num_piezas = int(datos.get("num_piezas") or 1)
        except (ValueError, TypeError):
            return (False, "El número de piezas debe ser un entero válido.")
        if num_piezas < 1:
            return (False, "El número de piezas debe ser al menos 1.")

        try:
            vida_util = int(datos.get("vida_util_meses") or 60)
        except (ValueError, TypeError):
            return (False, "La vida útil debe expresarse en meses (número).")
        if vida_util <= 0:
            return (False, "La vida útil debe ser mayor que cero (RN-06).")

        datos["descripcion"] = descripcion
        datos["num_piezas"] = num_piezas
        datos["vida_util_meses"] = vida_util

        # Solo se persisten los campos permitidos (lista blanca del repo).
        cambios = {c: datos[c] for c in CAMPOS_EDITABLES if c in datos}
        if not cambios:
            return (False, "No hay cambios que guardar.")

        try:
            ok = self._bien_repo.actualizar(bien_id, cambios)
            if not ok:
                return (False, "No se pudo actualizar el bien.")

            # Auditoría: valores anteriores vs nuevos (solo campos editados).
            datos_antes = {c: bien_antes.get(c) for c in cambios}
            registrar_auditoria(
                usuario_id,
                "bien",
                "ACTUALIZAR",
                registro_id=bien_id,
                datos_antes=datos_antes,
                datos_despues=cambios,
            )
            return (True, "Bien actualizado correctamente.")
        except Exception as exc:
            return (False, f"Error al actualizar el bien: {exc}")

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

    def obtener_siguiente_codigo_activo(self) -> str:
        """Obtiene el siguiente código correlativo de bien (ej. ACT-0016)."""
        return self._bien_repo.obtener_siguiente_codigo_activo()

    def obtener_siguiente_codigo_nivel(self) -> str:
        """Obtiene el siguiente código correlativo de nivel (ej. N-0004)."""
        return self._bien_repo.obtener_siguiente_codigo_nivel()

    # ------------------------------------------------------------------
    # Catálogos (para poblar combos en la UI)
    # ------------------------------------------------------------------
    def obtener_categorias(self) -> list[dict[str, Any]]:
        """Retorna categorías activas para combo."""
        return self._bien_repo.listar_categorias()

    def obtener_estados(self) -> list[dict[str, Any]]:
        """Retorna los estados del catálogo (código y descripción) para combos.

        Intenta leerlos de ``catalogo_estado``; si la consulta falla
        (p.ej. base de datos sin migrar), usa el catálogo en memoria.
        """
        try:
            filas = self._bien_repo.listar_estados()
            if filas:
                return filas
        except Exception:
            pass
        return [
            {"codigo": c, "descripcion": d}
            for c, d in estados.ESTADOS.items()
        ]

    def obtener_departamentos(self) -> list[dict[str, Any]]:
        """Retorna departamentos activos para combo."""
        return self._bien_repo.listar_departamentos()

    def obtener_cuentas_contables(self) -> list[dict[str, Any]]:
        """Retorna cuentas contables activas para combo."""
        return self._bien_repo.listar_cuentas_contables()
