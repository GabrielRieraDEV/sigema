# Formularios oficiales BM — Especificación de diseño para ReportLab
**Instituto Autónomo Minas Bolívar — Gobernación del estado Bolívar**

Este documento describe campo por campo el diseño exacto de cada formulario
BM oficial. Úsalo como referencia para reproducirlos en PDF con ReportLab.

---

## Elementos comunes a todos los formularios

### Encabezado (parte superior de cada página)
- **Izquierda:** Logo de la Gobernación del estado Bolívar + texto "Gobernación de Bolívar / Transformación y Producción"
- **Centro:** Nombre del formulario en mayúsculas y negrita (ej. "INVENTARIO DE BIENES MUEBLES (BM-1)")
- **Derecha (bloque de metadatos):**
  ```
  Código:     GOB-900-FM-XXX/15
  Fecha de Vigencia:  DD/MM/AAAA
  Actualización N°:   0X
  Página N°:          ___
  ```

### Bloque de identificación (debajo del encabezado)
Todos los formularios incluyen estos campos antes de la tabla de datos:
```
Dirección Administrativa: _______________
Dirección o Lugar:        _______________
Código:                   _______________
Municipio:                _______________
Unidad de Trabajo:        _______________
Fecha de Inventario:      _______________
```

### Pie de página
- Línea de total al final de la tabla
- Espacio para firma del responsable
- En BM-1: "JEFE DE LA UNIDAD DE TRABAJO: _______________"

---

## BM-1 — Inventario de Bienes Muebles
**Código:** GOB-900-FM-086/15
**Fecha de vigencia:** 11/07/2025
**Actualización N°:** 05

### Propósito
Lista completa de todos los bienes muebles asignados a una unidad de trabajo.
Se genera al realizar el inventario periódico o cuando lo solicite el jefe de unidad.

### Estructura de la tabla de datos

La tabla ocupa el ancho completo de la página y tiene las siguientes columnas
en este orden exacto de izquierda a derecha:

| N° | Columna | Ancho relativo | Notas |
|---|---|---|---|
| 1 | CLASIFICACIÓN / CÓDIGO | ~15% | Dos sub-columnas apiladas verticalmente: "CLASIFICACIÓN" arriba, "CÓDIGO" abajo |
| 2 | NÚMERO DE IDENTIFICACIÓN | ~15% | N° de serial o placa del bien |
| 3 | CANTIDAD | ~8% | Cantidad de unidades |
| 4 | NOMBRE Y DESCRIPCIÓN DE LOS ELEMENTOS | ~32% | Descripción completa del bien |
| 5 | VALOR UNITARIO | ~15% | Precio unitario sin IVA |
| 6 | VALOR TOTAL | ~15% | Precio unitario × cantidad |

### Fila de totales
Al final de la tabla, una fila que abarca las columnas de valor:
```
TOTAL ---------> | [suma valor unitario] | [suma valor total] |
```

### Firma al pie
```
JEFE DE LA UNIDAD DE TRABAJO: _______________________________
```

### Notas de diseño
- Encabezado de tabla con fondo gris oscuro, texto blanco, en mayúsculas
- Filas de datos con bordes finos en todas las celdas
- La columna "CLASIFICACIÓN / CÓDIGO" tiene una línea horizontal que la divide en dos
- Orientación: vertical (portrait)
- Papel: carta (Letter)

---

## BM-2 — Relación del Movimiento de Bienes Muebles
**Código:** GOB-900-FM-085/15
**Fecha de vigencia:** 11/07/2025
**Actualización N°:** 04

### Propósito
Registra todos los movimientos de bienes (incorporaciones y desincorporaciones)
del período. Se genera cada vez que se registra una incorporación o desincorporación.

### Bloque de identificación adicional
Además del bloque común, incluye:
```
Origen:
  Dirección:  _______________
  Municipio:  _______________
  Código:     _______________

Destino:
  Dirección:  _______________
  Municipio:  _______________
  Código:     _______________

Observaciones: _______________

Concepto:   _______________     Página N°: ___
```

El campo **Concepto** indica si el movimiento es:
- Incorporación
- Desincorporación

### Estructura de la tabla de datos

| N° | Columna | Ancho relativo | Notas |
|---|---|---|---|
| 1 | CLASIFICACIÓN / CÓDIGO | ~15% | Dos sub-columnas apiladas: "CLASIFICACIÓN" arriba, "CÓDIGO" abajo |
| 2 | NÚMERO DE IDENTIFICACIÓN | ~15% | N° de serial o identificación del bien |
| 3 | DESCRIPCIÓN DE LOS BIENES | ~35% | Nombre y descripción completa |
| 4 | PRECIO UNITARIO | ~17% | Precio sin IVA |
| 5 | VALOR TOTAL | ~18% | Total del movimiento |

### Fila de totales
```
Total ---------> | [suma precio unitario] | [suma valor total] |
```

### Firmas al pie
```
Jefe de la Unidad de Trabajo: _______________
Dirección de Administración:  _______________
```

### Notas de diseño
- Misma estructura visual que BM-1
- El campo "Concepto" se imprime destacado antes de la tabla
- Orientación: vertical (portrait)

---

## BM-3 — Relación del Movimiento de Bienes Muebles Faltantes
**Código:** GOB-900-FM-078/15
**Concepto:** 60 — Faltante por investigar
**Fecha de vigencia:** 11/07/2025
**Actualización N°:** 04

### Propósito
Documenta los bienes no localizados en inventario (Concepto 60).
Se genera cuando se detecta un bien faltante.

### Bloque de identificación adicional
```
Origen:
  Dirección:  _______________
  Municipio:  _______________
  Código:     _______________

Concepto: 60        Página N°: ___    Fecha: ___
```

### Estructura de la tabla de datos

| N° | Columna | Ancho relativo | Notas |
|---|---|---|---|
| 1 | CLASIFICACIÓN / CÓDIGO | ~12% | Dos sub-columnas: "CLASIFICACIÓN" arriba, "CÓDIGO" abajo |
| 2 | NÚMERO DE IDENTIFICACIÓN | ~13% | N° de serial o placa |
| 3 | DESCRIPCIÓN DE LOS BIENES | ~25% | Nombre y descripción |
| 4 | EXISTENCIA FÍSICA | ~10% | Cantidad encontrada físicamente |
| 5 | REGISTROS CONTABLES | ~10% | Cantidad según registros |
| 6 | VALOR UNITARIO | ~12% | Precio unitario del bien |
| 7 | CANTIDAD | ~8% | Cantidad faltante |
| 8 | VALOR TOTAL | ~10% | Valor total del faltante |

### Fila de totales
```
Total ---------> | [suma valor unitario] | [total cantidad] | [suma valor total] |
```

### Bloque de responsable (debajo de la tabla)
```
Faltante Determinado por:
  Cargo que Desempeña:           _______________
  Dependencia a la cual está Adscrito: _______________

Observaciones: _______________________________________________
```

### Firmas al pie
```
Usuario responsable del (los) bien(es):   Firma: ___    Sello: ___
```

### Notas de diseño
- La columna "EXISTENCIA FÍSICA / REGISTROS CONTABLES" puede agruparse
  con un encabezado superior compartido
- El bloque de responsable es obligatorio — siempre debe aparecer
- Orientación: vertical (portrait)

---

## BM-4 — Resumen de la Cuenta de Bienes Muebles
**Código:** GOB-900-FM-077/15
**Fecha de vigencia:** 19/08/2025
**Actualización N°:** 04

### Propósito
Resumen mensual de cierre de la cuenta de bienes.
Solo puede generarse al cierre de mes. El sistema calcula automáticamente la existencia final.

### Bloque de identificación
```
Estado:     _______________
Municipio:  _______________
Correspondiente al mes de: _______________ del: _______________
```

### Estructura principal
Este formulario NO tiene tabla de múltiples filas.
Es un formulario de resumen con campos individuales en este orden:

```
┌─────────────────────────────────────────────────────┐
│                                                      │
│  Existencia Anterior          ─────────────> [  ]   │
│                                                      │
│  Incorporaciones en el mes de la Cuenta              │
│  por todos los conceptos      ─────────────> [  ]   │
│                                                      │
│  Desincorporaciones en el mes de la cuenta           │
│  por el 60 "Faltante de Bienes por Investigar"       │
│                               ─────────────> [  ]   │
│                                                      │
│  Desincorporaciones en el mes de la cuenta           │
│  por el 60 "Faltante" de Bienes por Investigar       │
│                               ─────────────> [  ]   │
│                                                      │
│  Existencia Final             ─────────────> [  ]   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Fórmula de cálculo (el sistema la aplica automáticamente)
```
Existencia Final = Existencia Anterior
                 + Incorporaciones
                 - Desincorporaciones (todos los conceptos)
                 - Desincorporaciones por Concepto 60
```

### Bloque de cierre y firma
```
SELLO DE LA OFICINA:  [espacio para sello]

Firma del Jefe Responsable de la Unidad de Trabajo
o Departamento: _______________________________
```

### Notas de diseño
- Formulario de una sola página
- Los valores se muestran alineados a la derecha
- Las flechas (→) son guías visuales hacia el campo de valor
- El campo "Existencia Final" se resalta con fondo diferente o borde más grueso
- Espacio generoso para el sello físico de la oficina
- Orientación: vertical (portrait)

---

## Instrucciones de implementación con ReportLab

### Configuración de página
```python
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm

PAGE_WIDTH, PAGE_HEIGHT = letter   # 21.59 cm × 27.94 cm
MARGIN_LEFT   = 1.5 * cm
MARGIN_RIGHT  = 1.5 * cm
MARGIN_TOP    = 2.0 * cm
MARGIN_BOTTOM = 2.0 * cm
```

### Fuentes recomendadas
```python
# Usar Helvetica (disponible en ReportLab sin instalación extra)
FONT_HEADER   = ("Helvetica-Bold", 8)
FONT_SUBHEADER= ("Helvetica-Bold", 7)
FONT_BODY     = ("Helvetica", 7)
FONT_SMALL    = ("Helvetica", 6)
```

### Colores
```python
from reportlab.lib import colors

COLOR_HEADER_BG   = colors.HexColor("#1B3A5C")   # azul oscuro — fondo encabezado tabla
COLOR_HEADER_TEXT = colors.white
COLOR_ROW_ODD     = colors.white
COLOR_ROW_EVEN    = colors.HexColor("#F4F4F4")   # gris muy claro — filas alternas
COLOR_BORDER      = colors.HexColor("#CCCCCC")   # gris — bordes de tabla
COLOR_TOTAL_BG    = colors.HexColor("#D6E4F0")   # azul claro — fila de totales
```

### Orden de construcción de cada formulario
1. Dibujar encabezado con logo y metadatos
2. Dibujar bloque de identificación
3. Dibujar tabla de datos con `reportlab.platypus.Table`
4. Dibujar fila de totales
5. Dibujar bloques de firma y sello
6. Registrar el formulario en la tabla `formulario_bm` de la BD (RN-09)

### Regla crítica (RN-09 del SRS)
Una vez generado y guardado el PDF, el formulario queda con estado `vigente`
en la BD y **no puede regenerarse ni modificarse**. Solo puede anularse
con justificación registrada por el Administrador.
