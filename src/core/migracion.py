"""
migracion.py — Herramienta de migración de datos del sistema anterior.

El sistema anterior era **FoxPro**, por lo que el formato principal es
``.dbf`` (dBASE/Visual FoxPro).  También se aceptan CSV, Excel (.xlsx) y
JSON por si los datos se exportan.  Cada registro se valida contra los
catálogos de SIGEMA y, si es válido, se inserta en la tabla ``bien``
preservando el código original.

El lector de DBF usa la librería ``dbfread`` si está instalada (maneja
memos .fpt y tipos de Visual FoxPro); si no, recurre a un parser DBF
propio en Python puro (tipos C/N/F/D/L/I/B/Y y memo .fpt básico).

Notas de diseño
---------------
- **Estado**: tras el rediseño de estados, ``bien.estado`` es un código
  ``VARCHAR(2)`` con CHECK ('01'..'07').  Los bienes migrados se insertan
  con ``estado = '01'`` (OPERATIVO, EN USO, EXCELENTE ESTADO), equivalente
  al antiguo "Activo" del SRS.
- **Origen**: los bienes migrados se marcan como ``origen = 'COMPRA'``.
- **Auditoría**: la inserción usa ``BienRepository.crear`` (decorado con
  ``@auditar``), por lo que cada inserción queda registrada en auditoría.

Mapa de columnas
----------------
``COLUMN_ALIASES`` traduce los encabezados del archivo anterior a los
campos canónicos de ``bien``.  El emparejamiento es **insensible a
mayúsculas, espacios, guiones y acentos**.  Si los encabezados reales del
export difieren, basta con agregar el alias correspondiente aquí.
"""

from __future__ import annotations

import csv
import os
import struct
import tempfile
import unicodedata
from datetime import date, datetime
from typing import Any, Callable

from src.core import estados
from src.db.bien_repository import BienRepository
from src.db.catalogo_repository import CatalogoRepository
from src.db.connection import DBConnection


# ----------------------------------------------------------------------
# Mapa de alias de columnas (sistema anterior -> campo canónico de bien)
# ----------------------------------------------------------------------
COLUMN_ALIASES: dict[str, list[str]] = {
    "codigo_activo": [
        "codigo_activo", "codigo", "cod_activo", "codigo_bien", "codbien",
        "codigo_del_bien", "activo", "bien", "id_bien", "cod_bien",
        "cod", "nro_bien", "num_bien", "numero", "nro", "no_bien",
    ],
    "codigo_nivel": ["codigo_nivel", "nivel", "cod_nivel"],
    "descripcion": [
        "descripcion", "descripcio", "descrip", "desc", "nombre", "detalle",
        "denominacion", "nombre_descripcion", "nombre_del_bien", "nombre_bie",
    ],
    "categoria": ["categoria", "categori", "tipo_bien", "clase", "rubro", "grupo"],
    "marca": ["marca"],
    "modelo": ["modelo"],
    "serial_bien": [
        "serial", "serial_bien", "nro_serial", "n_serie", "serie",
        "nro_serie", "num_serie", "serial_no",
    ],
    "color": ["color"],
    "tipo": ["tipo"],
    "num_piezas": [
        "num_piezas", "piezas", "cantidad", "cant", "nro_piezas",
        "existencia", "stock",
    ],
    "orden_compra": [
        "orden_compra", "orden_comp", "oc", "orden", "nro_orden",
        "n_orden_compra", "numero_orden", "nro_oc",
    ],
    "fecha_compra": [
        "fecha_compra", "fecha_comp", "fec_compra", "fecha", "fecha_adquisicion",
        "fecha_adq", "fec_adq", "fecha_ingreso", "fec_ingreso", "fecha_registro",
        "ano", "anio", "year", "ejercicio",
    ],
    "precio_sin_iva": [
        "precio_sin_iva", "precio", "precio_uni", "precio_unitario", "valor",
        "valor_unit", "valor_unitario", "valor_bien", "monto", "monto_bien",
        "costo", "costo_unit",
    ],
    "moneda": ["moneda"],
    "vida_util_meses": ["vida_util_meses", "vida_util", "vidautil", "vida"],
    "departamento": [
        "departamento", "departamen", "depto", "dep", "depend", "cod_depto",
        "cod_dep", "dependencia", "dependenci", "unidad", "unidad_adm",
        "ubicacion", "gerencia", "oficina", "ofic",
    ],
    "cuenta_contable": [
        "cuenta_contable", "cuenta_con", "cuentacont", "cta_contab", "ctacontabl",
        "cuenta", "cta", "codigo_contable", "cod_cuenta", "cuenta_cont",
        "clasificacion", "clasificac", "clasif", "codigo_cuenta",
    ],
    "observaciones": [
        "observaciones", "observacio", "observacion", "observa", "obs",
        "notas", "nota",
    ],
    # Campos del sistema anterior (FoxPro) que se transforman luego.
    "estado_texto": ["estado", "estatus", "situacion", "condicion"],
    "subgrupo": ["subgrupo", "sub_grupo", "subgrup"],
}

# Campos obligatorios para poder migrar un registro.
# (la categoría no es obligatoria: en migración se asigna una por defecto.)
_CAMPOS_OBLIGATORIOS = [
    "codigo_activo",
    "descripcion",
    "departamento",
    "cuenta_contable",
]


def _norm(valor: Any) -> str:
    """Normaliza texto: minúsculas, sin acentos, espacios/guiones -> '_'."""
    s = str(valor or "").strip().lower()
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )
    for ch in (" ", "-", ".", "/"):
        s = s.replace(ch, "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


# Índice inverso: encabezado_normalizado -> campo canónico.
_ALIAS_INDEX = {
    _norm(alias): canon
    for canon, aliases in COLUMN_ALIASES.items()
    for alias in aliases
}


def _decode_txt(b: bytes) -> str:
    """Decodifica bytes de un DBF FoxPro probando codificaciones comunes."""
    if isinstance(b, str):
        return b
    for enc in ("cp1252", "cp850", "latin-1"):
        try:
            return b.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode("latin-1", "ignore")


# Mapa inverso descripción->código de estado (para traducir el ESTADO texto
# del sistema anterior al código del catálogo de SIGEMA).
_ESTADO_POR_TEXTO = {_norm(desc): cod for cod, desc in estados.ESTADOS.items()}


def _estado_desde_texto(texto: Any) -> str:
    """Traduce el texto de estado del sistema anterior a su código (01..07)."""
    if not texto:
        return estados.ESTADO_DEFECTO
    return _ESTADO_POR_TEXTO.get(_norm(texto), estados.ESTADO_DEFECTO)


def _parse_decimal(valor: Any) -> float:
    """Convierte texto monetario a float, tolerando formatos es/en."""
    if valor is None or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip()
    s = "".join(c for c in s if c.isdigit() or c in ".,-")
    if not s:
        return 0.0
    if "," in s and "." in s:
        # El último separador es el decimal.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_fecha(valor: Any) -> str | None:
    """Devuelve una fecha 'YYYY-MM-DD' a partir de varios formatos."""
    if valor is None or str(valor).strip() == "":
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    s = str(valor).strip()[:19]
    # Año solo (p.ej. '2013' del campo AÑO de FoxPro) -> 1 de enero.
    if len(s) == 4 and s.isdigit() and "1900" <= s <= "2099":
        return f"{s}-01-01"
    formatos = (
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d",
        "%m/%d/%Y", "%d/%m/%y", "%Y-%m-%d %H:%M:%S",
    )
    for fmt in formatos:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


class Migrador:
    """Orquesta la migración del sistema anterior a SIGEMA.

    Expone los métodos solicitados: :meth:`leer_archivo`,
    :meth:`validar_registro`, :meth:`migrar` y
    :meth:`generar_reporte_errores`.
    """

    def __init__(
        self,
        db: DBConnection,
        usuario_id: int,
        auto_crear_catalogos: bool = True,
        sufijo_duplicados: bool = True,
        cuenta_defecto: str | None = None,
    ):
        self._db = db
        self._usuario_id = usuario_id
        self._bien_repo = BienRepository(db)
        self._catalogo_repo = CatalogoRepository(db)
        # Cuenta contable a asignar a todos los bienes migrados. El SUBGRUPO
        # del sistema anterior es inconsistente, así que se usa una cuenta
        # por defecto y se reclasifica luego desde SIGEMA (el SUBGRUPO
        # original queda anotado en observaciones para referencia).
        self._cuenta_defecto = cuenta_defecto
        # Comportamiento de migración (confirmado con el usuario):
        #  - auto_crear_catalogos: crea departamentos faltantes y la
        #    categoría 'Migrado' en lugar de marcar error.
        #  - sufijo_duplicados: a los códigos repetidos les agrega -1, -2…
        self._auto_crear = auto_crear_catalogos
        self._sufijo_duplicados = sufijo_duplicados
        # Lookups de catálogos (se cargan perezosamente).
        self._cuentas: set[str] | None = None
        self._cuentas_por_desc: dict[str, str] | None = None
        self._departamentos: dict[str, int] | None = None
        self._categorias: dict[str, int] | None = None
        self._codigos_existentes: set[str] | None = None
        self._dept_codigos: set[str] = set()
        self._dept_seq = 0
        self._categoria_migrado_id: int | None = None
        # Estado para detectar duplicados dentro del propio archivo.
        self._codigos_vistos: set[str] = set()

    # ------------------------------------------------------------------
    # Carga de catálogos
    # ------------------------------------------------------------------
    def _cargar_catalogos(self) -> None:
        if self._cuentas is not None:
            return
        cuentas = self._catalogo_repo.listar_cuentas()
        self._cuentas = {_norm(c["codigo"]) for c in cuentas}
        self._cuentas_por_desc = {
            _norm(c["descripcion"]): c["codigo"] for c in cuentas
        }
        self._cuentas_codigo_real = {_norm(c["codigo"]): c["codigo"] for c in cuentas}

        deps = self._catalogo_repo.listar_departamentos()
        self._departamentos = {}
        self._dept_codigos = set()
        for d in deps:
            self._departamentos[_norm(d["codigo"])] = d["id"]
            self._departamentos[_norm(d["nombre"])] = d["id"]
            self._dept_codigos.add(_norm(d["codigo"]))

        cats = self._catalogo_repo.listar_categorias()
        self._categorias = {_norm(c["nombre"]): c["id"] for c in cats}

        with self._db.get_cursor() as cur:
            cur.execute("SELECT codigo_activo FROM bien")
            self._codigos_existentes = {_norm(r[0]) for r in cur.fetchall()}

    # ------------------------------------------------------------------
    # Resolución de catálogos
    # ------------------------------------------------------------------
    def _resolver_cuenta(self, valor: Any) -> str | None:
        """Devuelve el código de cuenta contable real, o None si no existe."""
        self._cargar_catalogos()
        clave = _norm(valor)
        if clave in self._cuentas:
            return self._cuentas_codigo_real[clave]
        if clave in (self._cuentas_por_desc or {}):
            return self._cuentas_por_desc[clave]
        return None

    def _resolver_departamento(self, valor: Any) -> int | None:
        self._cargar_catalogos()
        return (self._departamentos or {}).get(_norm(valor))

    def _resolver_categoria(self, valor: Any) -> int | None:
        self._cargar_catalogos()
        return (self._categorias or {}).get(_norm(valor))

    # ------------------------------------------------------------------
    # Auto-creación de catálogos (departamentos y categoría 'Migrado')
    # ------------------------------------------------------------------
    def _siguiente_codigo_dept(self) -> str:
        """Genera un código de departamento único (MIG-001, MIG-002…)."""
        while True:
            self._dept_seq += 1
            codigo = f"MIG-{self._dept_seq:03d}"
            if _norm(codigo) not in self._dept_codigos:
                self._dept_codigos.add(_norm(codigo))
                return codigo

    def _resolver_o_crear_departamento(self, nombre: Any) -> int | None:
        """Resuelve un departamento por nombre/código; lo crea si no existe."""
        if nombre is None or str(nombre).strip() == "":
            return None
        self._cargar_catalogos()
        clave = _norm(nombre)
        existente = (self._departamentos or {}).get(clave)
        if existente is not None:
            return existente
        codigo = self._siguiente_codigo_dept()
        nuevo_id = self._catalogo_repo.crear_departamento({
            "codigo": codigo,
            "nombre": str(nombre).strip(),
            "descripcion": "Creado por migración del sistema anterior.",
        })
        self._departamentos[clave] = nuevo_id
        return nuevo_id

    def _asegurar_categoria_migrado(self) -> int:
        """Devuelve el id de la categoría 'Migrado', creándola si hace falta."""
        if self._categoria_migrado_id is not None:
            return self._categoria_migrado_id
        self._cargar_catalogos()
        existente = (self._categorias or {}).get(_norm("Migrado"))
        if existente is not None:
            self._categoria_migrado_id = existente
            return existente
        nuevo_id = self._catalogo_repo.crear_categoria({
            "nombre": "Migrado",
            "descripcion": "Bienes migrados del sistema anterior (FoxPro).",
        })
        self._categorias[_norm("Migrado")] = nuevo_id
        self._categoria_migrado_id = nuevo_id
        return nuevo_id

    # ------------------------------------------------------------------
    # 1. Lectura del archivo
    # ------------------------------------------------------------------
    def leer_archivo(self, ruta: str) -> list[dict[str, Any]]:
        """Lee y normaliza los registros del sistema anterior.

        Soporta **DBF (FoxPro/dBASE)**, CSV, Excel (.xlsx) y JSON.  Devuelve
        una lista de dicts con los campos canónicos de ``bien`` más la clave
        ``_fila`` (número de fila/registro en el archivo, para el reporte de
        errores).
        """
        if not ruta or not os.path.isfile(ruta):
            raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

        ext = os.path.splitext(ruta)[1].lower()
        if ext == ".dbf":
            filas = self._leer_dbf(ruta)
        elif ext == ".csv":
            filas = self._leer_csv(ruta)
        elif ext in (".xlsx", ".xlsm"):
            filas = self._leer_xlsx(ruta)
        elif ext == ".json":
            filas = self._leer_json(ruta)
        else:
            raise ValueError(
                f"Formato no soportado: '{ext}'. Use DBF (FoxPro), CSV, "
                f"XLSX o JSON.")

        # Numeración para el reporte: en DBF/JSON es el N° de registro (1..n);
        # en CSV/XLSX la fila 1 son los encabezados, así que los datos van 2..n.
        inicio = 1 if ext in (".dbf", ".json") else 2
        registros = []
        for i, fila in enumerate(filas, start=inicio):
            registro = self._mapear(fila)
            self._postprocesar(registro)
            registro["_fila"] = i
            registros.append(registro)
        # Resolver códigos duplicados (sufijo -1, -2…) antes de validar.
        self._resolver_duplicados(registros)
        return registros

    def _postprocesar(self, registro: dict[str, Any]) -> None:
        """Transforma los campos heredados (estado texto, cuenta desde subgrupo)."""
        # Estado: el sistema anterior guarda el texto; traducir al código.
        if registro.get("estado_texto") and not registro.get("estado"):
            registro["estado"] = _estado_desde_texto(registro["estado_texto"])
        # Cuenta contable:
        #  - Si hay cuenta_defecto, se asigna a todos (caso FoxPro maestro).
        #  - Si no, se deriva 2-1-214-NN desde SUBGRUPO (otros formatos).
        if self._cuenta_defecto:
            registro["cuenta_contable"] = self._cuenta_defecto
        elif not registro.get("cuenta_contable") and registro.get("subgrupo"):
            sg = str(registro["subgrupo"]).strip()
            if sg:
                registro["cuenta_contable"] = f"2-1-214-{sg}"

    def _resolver_duplicados(self, registros: list[dict[str, Any]]) -> None:
        """Hace únicos los códigos repetidos agregando sufijo -1, -2…"""
        if not self._sufijo_duplicados:
            return
        contador: dict[str, int] = {}
        for r in registros:
            cod = str(r.get("codigo_activo", "")).strip()
            if not cod:
                continue
            n = contador.get(cod, 0)
            contador[cod] = n + 1
            if n > 0:
                nuevo = f"{cod}-{n}"
                r["codigo_activo"] = nuevo
                r["_codigo_original"] = cod
                r["_nota"] = (
                    f"Código original '{cod}' duplicado en el sistema "
                    f"anterior; renombrado a '{nuevo}' en la migración."
                )

    @staticmethod
    def _leer_csv(ruta: str) -> list[dict[str, Any]]:
        with open(ruta, "r", encoding="utf-8-sig", newline="") as f:
            muestra = f.read(4096)
            f.seek(0)
            try:
                dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t|")
            except csv.Error:
                dialecto = csv.excel
            return list(csv.DictReader(f, dialect=dialecto))

    @staticmethod
    def _leer_xlsx(ruta: str) -> list[dict[str, Any]]:
        try:
            import openpyxl  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Para leer archivos Excel instale 'openpyxl' "
                "(pip install openpyxl)."
            ) from exc
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        ws = wb.active
        filas_iter = ws.iter_rows(values_only=True)
        try:
            encabezados = [str(c) if c is not None else "" for c in next(filas_iter)]
        except StopIteration:
            return []
        resultado = []
        for fila in filas_iter:
            if fila is None or all(c is None for c in fila):
                continue
            resultado.append(dict(zip(encabezados, fila)))
        wb.close()
        return resultado

    @staticmethod
    def _leer_json(ruta: str) -> list[dict[str, Any]]:
        import json
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict):
            for clave in ("data", "registros", "bienes", "items"):
                if isinstance(datos.get(clave), list):
                    return datos[clave]
            return [datos]
        if isinstance(datos, list):
            return datos
        raise ValueError("El JSON no contiene una lista de registros.")

    # ------------------------------------------------------------------
    # Lectura de DBF (FoxPro / dBASE)
    # ------------------------------------------------------------------
    @staticmethod
    def _leer_dbf(ruta: str) -> list[dict[str, Any]]:
        """Lee un .dbf usando dbfread si está disponible, o el parser propio."""
        try:
            from dbfread import DBF  # type: ignore
        except ImportError:
            return Migrador._leer_dbf_builtin(ruta)
        try:
            tabla = DBF(
                ruta,
                load=True,
                ignore_missing_memofile=True,
                char_decode_errors="ignore",
            )
            return [dict(rec) for rec in tabla]
        except Exception:
            # Cualquier problema con dbfread -> intentar parser propio.
            return Migrador._leer_dbf_builtin(ruta)

    @staticmethod
    def _leer_dbf_builtin(ruta: str) -> list[dict[str, Any]]:
        """Parser DBF en Python puro (sin dependencias externas)."""
        with open(ruta, "rb") as f:
            data = f.read()
        if len(data) < 32:
            raise ValueError("Archivo DBF inválido o vacío.")

        num_records = struct.unpack("<I", data[4:8])[0]
        header_size = struct.unpack("<H", data[8:10])[0]
        record_size = struct.unpack("<H", data[10:12])[0]

        # Descriptores de campo (32 bytes c/u hasta 0x0D).
        campos: list[tuple[str, str, int, int]] = []
        pos = 32
        while pos < header_size - 1 and data[pos] != 0x0D:
            desc = data[pos:pos + 32]
            if len(desc) < 32:
                break
            nombre = _decode_txt(desc[0:11].split(b"\x00")[0]).strip()
            ftype = chr(desc[11])
            flen = desc[16]
            fdec = desc[17]
            campos.append((nombre, ftype, flen, fdec))
            pos += 32

        # Archivo de memos (.fpt) si existe.
        fpt = None
        base = os.path.splitext(ruta)[0]
        for ext in (".fpt", ".FPT"):
            if os.path.exists(base + ext):
                try:
                    fpt = Migrador._abrir_fpt(base + ext)
                except Exception:
                    fpt = None
                break

        registros: list[dict[str, Any]] = []
        offset = header_size
        for _ in range(num_records):
            rec = data[offset:offset + record_size]
            offset += record_size
            if len(rec) < record_size:
                break
            if rec[0:1] == b"*":          # registro borrado
                continue
            fila: dict[str, Any] = {}
            p = 1
            for nombre, ftype, flen, fdec in campos:
                raw = rec[p:p + flen]
                p += flen
                fila[nombre] = Migrador._parse_dbf_value(raw, ftype, fdec, fpt)
            registros.append(fila)
        return registros

    @staticmethod
    def _parse_dbf_value(raw: bytes, ftype: str, fdec: int, fpt):
        """Convierte el valor crudo de un campo DBF a un valor de Python."""
        if ftype == "C":                                  # carácter
            return _decode_txt(raw).strip()
        if ftype in ("N", "F"):                           # numérico/float
            s = raw.decode("ascii", "ignore").strip()
            if not s:
                return None
            try:
                return float(s) if (fdec or "." in s) else int(s)
            except ValueError:
                return None
        if ftype == "B":                                  # double (VFP)
            try:
                return struct.unpack("<d", raw[:8])[0]
            except struct.error:
                return None
        if ftype == "I":                                  # entero (VFP)
            try:
                return struct.unpack("<i", raw[:4])[0]
            except struct.error:
                return None
        if ftype == "Y":                                  # moneda (VFP)
            try:
                return struct.unpack("<q", raw[:8])[0] / 10000.0
            except struct.error:
                return None
        if ftype == "D":                                  # fecha YYYYMMDD
            s = raw.decode("ascii", "ignore").strip()
            if len(s) == 8 and s.isdigit():
                return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
            return None
        if ftype == "L":                                  # lógico
            return raw.decode("ascii", "ignore").strip().upper() in ("T", "Y")
        if ftype in ("M", "G", "P"):                      # memo
            if fpt is None:
                return ""
            s = raw.decode("ascii", "ignore").strip()
            if s.isdigit():
                bloque = int(s)
            elif len(raw) >= 4:
                bloque = struct.unpack("<I", raw[:4])[0]
            else:
                bloque = 0
            if not bloque:
                return ""
            try:
                return Migrador._leer_memo(fpt, bloque)
            except Exception:
                return ""
        # Tipos no manejados (T datetime, etc.)
        return _decode_txt(raw).strip()

    @staticmethod
    def _abrir_fpt(path: str):
        """Abre un archivo de memos .fpt y devuelve (datos, tamaño_bloque)."""
        with open(path, "rb") as f:
            data = f.read()
        blocksize = struct.unpack(">H", data[6:8])[0] or 64
        return (data, blocksize)

    @staticmethod
    def _leer_memo(fpt, bloque: int) -> str:
        data, blocksize = fpt
        inicio = bloque * blocksize
        if inicio + 8 > len(data):
            return ""
        _tipo, longitud = struct.unpack(">II", data[inicio:inicio + 8])
        contenido = data[inicio + 8:inicio + 8 + longitud]
        return _decode_txt(contenido).strip()

    @staticmethod
    def _mapear(fila: dict[str, Any]) -> dict[str, Any]:
        """Traduce los encabezados del archivo a campos canónicos."""
        registro: dict[str, Any] = {}
        for clave, valor in fila.items():
            canon = _ALIAS_INDEX.get(_norm(clave))
            if canon and registro.get(canon) in (None, ""):
                registro[canon] = valor
        return registro

    # ------------------------------------------------------------------
    # 2. Validación
    # ------------------------------------------------------------------
    def reiniciar_validacion(self) -> None:
        """Reinicia el control de duplicados dentro del archivo."""
        self._codigos_vistos = set()

    def validar_registro(self, registro: dict[str, Any]) -> list[str]:
        """Valida un registro y devuelve la lista de errores (vacía si OK)."""
        self._cargar_catalogos()
        errores: list[str] = []

        # Campos obligatorios vacíos
        for campo in _CAMPOS_OBLIGATORIOS:
            valor = registro.get(campo)
            if valor is None or str(valor).strip() == "":
                errores.append(f"Campo obligatorio vacío: {campo}")

        # Código activo duplicado (en BD o dentro del propio archivo)
        codigo = _norm(registro.get("codigo_activo"))
        if codigo:
            if codigo in (self._codigos_existentes or set()):
                errores.append(
                    "Código activo ya existe en el sistema (duplicado en BD)")
            elif codigo in self._codigos_vistos:
                errores.append("Código activo duplicado dentro del archivo")
            else:
                self._codigos_vistos.add(codigo)

        # Cuenta contable no existe en catálogo
        if registro.get("cuenta_contable"):
            if self._resolver_cuenta(registro["cuenta_contable"]) is None:
                errores.append(
                    f"Cuenta contable inexistente: "
                    f"'{registro['cuenta_contable']}'")

        # Departamento: solo se exige que exista si NO se autocrean catálogos.
        if not self._auto_crear and registro.get("departamento"):
            if self._resolver_departamento(registro["departamento"]) is None:
                errores.append(
                    f"Departamento inexistente: '{registro['departamento']}'")

        # Categoría: solo se valida si NO se autocrea y viene en el archivo.
        if not self._auto_crear and registro.get("categoria"):
            if self._resolver_categoria(registro["categoria"]) is None:
                errores.append(
                    f"Categoría inexistente: '{registro['categoria']}'")

        return errores

    def validar_todos(
        self, registros: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Valida todos los registros.

        Returns
        -------
        (validos, errores)
            ``validos`` = registros sin errores listos para migrar.
            ``errores`` = lista de dicts {fila, campo, motivo_error}.
        """
        self.reiniciar_validacion()
        validos: list[dict[str, Any]] = []
        errores: list[dict[str, Any]] = []
        for registro in registros:
            fallos = self.validar_registro(registro)
            if fallos:
                for f in fallos:
                    campo, _, motivo = f.partition(":")
                    errores.append({
                        "fila": registro.get("_fila", ""),
                        "campo": campo.strip(),
                        "motivo_error": (motivo.strip() or campo.strip()),
                    })
            else:
                validos.append(registro)
        return validos, errores

    # ------------------------------------------------------------------
    # 3. Migración
    # ------------------------------------------------------------------
    def migrar(
        self,
        registros_validos: list[dict[str, Any]],
        usuario_id: int | None = None,
        progreso: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """Inserta los registros válidos en la tabla ``bien``.

        Cada bien se crea con estado '01', origen 'COMPRA', creado_por el
        usuario indicado y created_at automático (fecha actual).  La
        inserción queda auditada (``BienRepository.crear`` es ``@auditar``).

        Returns
        -------
        dict
            {insertados, fallidos, total, errores: [...]}
        """
        self._cargar_catalogos()
        uid = usuario_id if usuario_id is not None else self._usuario_id
        cat_defecto = (
            self._asegurar_categoria_migrado() if self._auto_crear else None
        )
        total = len(registros_validos)
        insertados = 0
        errores: list[dict[str, Any]] = []

        for idx, registro in enumerate(registros_validos, start=1):
            try:
                bien = self._construir_bien(registro, uid, cat_defecto)
                self._bien_repo.crear(bien)
                insertados += 1
            except Exception as exc:
                errores.append({
                    "fila": registro.get("_fila", ""),
                    "campo": "(inserción)",
                    "motivo_error": str(exc),
                })
            if progreso is not None:
                progreso(idx, total)

        return {
            "insertados": insertados,
            "fallidos": len(errores),
            "total": total,
            "errores": errores,
        }

    def _construir_bien(
        self,
        registro: dict[str, Any],
        usuario_id: int,
        categoria_defecto: int | None = None,
    ) -> dict[str, Any]:
        """Construye el dict de ``bien`` listo para insertar."""
        cuenta = self._resolver_cuenta(registro.get("cuenta_contable"))
        if self._auto_crear:
            dept_id = self._resolver_o_crear_departamento(
                registro.get("departamento"))
        else:
            dept_id = self._resolver_departamento(registro.get("departamento"))
        cat_id = self._resolver_categoria(registro.get("categoria")) or categoria_defecto

        codigo_activo = str(registro.get("codigo_activo", "")).strip()
        codigo_nivel = (
            str(registro.get("codigo_nivel") or "").strip() or cuenta or "N/A"
        )
        fecha = _parse_fecha(registro.get("fecha_compra")) or date.today().isoformat()

        # Estado: ya viene como código (mapeado desde el texto del FoxPro).
        estado = registro.get("estado") or estados.ESTADO_DEFECTO

        # Observaciones: combinar obs original + clasificación FoxPro original
        # (para reclasificar después) + nota de duplicado, si las hubiera.
        notas = []
        if registro.get("observaciones"):
            notas.append(str(registro["observaciones"]).strip())
        if registro.get("subgrupo"):
            notas.append(f"[FoxPro SUBGRUPO={str(registro['subgrupo']).strip()}]")
        if registro.get("_nota"):
            notas.append(registro["_nota"])
        obs = " ".join(n for n in notas if n) or None

        return {
            "codigo_activo": codigo_activo,          # se preserva el original
            "codigo_nivel": codigo_nivel,
            "descripcion": str(registro.get("descripcion", "")).strip(),
            "categoria_id": cat_id,
            "marca": (str(registro["marca"]).strip() if registro.get("marca") else None),
            "modelo": (str(registro["modelo"]).strip() if registro.get("modelo") else None),
            "serial_bien": (str(registro["serial_bien"]).strip() if registro.get("serial_bien") else None),
            "color": (str(registro["color"]).strip() if registro.get("color") else None),
            "tipo": (str(registro["tipo"]).strip() if registro.get("tipo") else None),
            "num_piezas": self._a_entero(registro.get("num_piezas"), 1),
            "orden_compra": (str(registro["orden_compra"]).strip() if registro.get("orden_compra") else None),
            "fecha_compra": fecha,
            "precio_sin_iva": _parse_decimal(registro.get("precio_sin_iva")),
            "moneda": self._normalizar_moneda(registro.get("moneda")),
            "vida_util_meses": self._a_entero(registro.get("vida_util_meses"), 60),
            "departamento_id": dept_id,
            "cuenta_contable": cuenta,
            "estado": estado,                        # código mapeado (01/06/07…)
            "origen": "COMPRA",
            "observaciones": obs,
            "creado_por": usuario_id,
        }

    @staticmethod
    def _a_entero(valor: Any, defecto: int) -> int:
        try:
            n = int(float(valor))
            return n if n > 0 else defecto
        except (ValueError, TypeError):
            return defecto

    @staticmethod
    def _normalizar_moneda(valor: Any) -> str:
        s = _norm(valor)
        if s in ("dolares", "dolar", "usd", "us", "$"):
            return "Dólares"
        return "Bolívares"

    # ------------------------------------------------------------------
    # 4. Reporte de errores
    # ------------------------------------------------------------------
    @staticmethod
    def generar_reporte_errores(
        errores: list[dict[str, Any]], ruta: str | None = None
    ) -> str:
        """Genera un CSV con columnas fila, campo, motivo_error.

        Si ``ruta`` es None, escribe en un archivo temporal y devuelve su
        ruta.
        """
        if ruta is None:
            fd, ruta = tempfile.mkstemp(
                suffix=".csv", prefix="sigema_migracion_errores_")
            os.close(fd)
        with open(ruta, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["fila", "campo", "motivo_error"])
            for e in errores:
                writer.writerow([
                    e.get("fila", ""),
                    e.get("campo", ""),
                    e.get("motivo_error", ""),
                ])
        return ruta
