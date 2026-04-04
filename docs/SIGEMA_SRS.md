# SIGEMA — Especificación de Requerimientos del Sistema (SRS)
**Versión 1.0 — Marzo 2026**
Instituto Autónomo Minas Bolívar · División de Control de Bienes

---

## 1. Control de versiones

| Versión | Fecha | Descripción | Autor |
|---|---|---|---|
| 1.0 | Marzo 2026 | Versión inicial basada en levantamiento de información | Equipo de desarrollo SIGEMA |

---

## 2. Introducción

### 2.1 Propósito
Este documento define los requerimientos funcionales y no funcionales del sistema SIGEMA para el Instituto Autónomo Minas Bolívar. Está destinado al equipo de desarrollo como referencia técnica principal durante todo el ciclo de vida del proyecto.

### 2.2 Alcance
SIGEMA es una aplicación de escritorio Windows que cubre:
- Control de bienes muebles con trazabilidad completa de movimientos.
- Generación e impresión de formularios oficiales BM-1, BM-2, BM-3 y BM-4 con códigos GOB-900-FM.
- Gestión de usuarios con perfiles y niveles de acceso.
- Migración de datos históricos del sistema anterior.

**Fuera del alcance en la versión 1.0:**
- Módulo de almacén de consumibles (papelería, insumos mineros) — fase posterior.
- Cálculo automático de depreciación mensual — fase posterior.
- Integración con sistemas externos (SIGRE, SIMA, Gobernación).

### 2.3 Definiciones y abreviaturas

| Término | Definición |
|---|---|
| BM | Bienes Muebles — denominación de los formularios oficiales de control de activos. |
| SRS | Software Requirements Specification — Especificación de Requerimientos del Software. |
| OC | Orden de Compra — documento que respalda el ingreso de un bien. |
| Concepto 60 | Denominación oficial para bienes faltantes no localizados en inventario. |
| GOB-900-FM | Prefijo de los códigos oficiales de formularios de la Gobernación del estado Bolívar. |
| LAN | Local Area Network — red de área local del instituto. |
| SKU | Stock Keeping Unit — código único de identificación de un artículo. |

---

## 3. Descripción general del sistema

### 3.1 Contexto operativo
El Instituto Autónomo Minas Bolívar lleva actualmente el control de bienes muebles de forma manual con formularios impresos. Los formularios en uso están desactualizados y el registro de bienes históricos presenta dificultades por la antigüedad de los activos. No existe un sistema digital centralizado. SIGEMA reemplazará este proceso manual.

### 3.2 Perfiles de usuario

| Perfil | Usuarios | Acceso |
|---|---|---|
| Administrador | Jefe División Control de Bienes | Acceso total: configuración, catálogos, usuarios, reportes y todos los módulos |
| Almacenista | Encargados de bienes y formularios BM (4–6 personas) | Registro de bienes, movimientos y generación de formularios BM. Sin acceso a configuración |
| Consulta | Personal autorizado de otros departamentos | Solo lectura: consulta de existencias y estado de bienes de su departamento |

> **Contexto operativo:** El sistema tendrá entre 4 y 6 usuarios activos directos. Los equipos se comparten por departamento. Todos tienen red LAN operativa y soporte técnico disponible en el instituto.

### 3.3 Restricciones del sistema
- Operación 100% en red local LAN, sin requerir conexión a internet.
- Sin integración con sistemas externos de la Gobernación en esta versión.
- Los formularios BM mantienen los códigos GOB-900-FM originales.
- El precio unitario siempre se registra sin IVA, conforme al manual del SIMA.
- No se eliminan bienes del sistema — solo se cambia su estado.

---

## 4. Requerimientos funcionales

### 4.1 Módulo A — Bienes Muebles

#### 4.1.1 Registro de bienes
Cada bien mueble se registra con los siguientes campos:

| Campo | Descripción | Tipo | Obligatorio |
|---|---|---|---|
| Código de nivel | Clasificador 2-1-214-XX | Texto | Sí |
| Código activo | Código único del bien | Texto | Sí |
| Descripción | Nombre y descripción | Texto | Sí |
| Categoría | Mobiliario, equipo, etc. | Lista | Sí |
| Marca | Fabricante del bien | Texto | No |
| Modelo | Modelo del equipo | Texto | No |
| Serial | N° serial del bien | Texto | No |
| Color | Color del bien | Texto | No |
| Tipo | Administrativo, ejecutivo, etc. | Lista | No |
| N° de piezas | Cantidad (1 por defecto) | Número | Sí |
| N° Orden de Compra | N° de la OC (referencia opcional) | Texto | No |
| Fecha de compra | Fecha de adquisición | Fecha | Sí |
| Precio unitario (sin IVA) | Costo histórico inicial | Decimal | Sí |
| Moneda | Bolívares o Dólares | Lista | Sí |
| Vida útil (meses) | Estándar: 60 meses | Número | Sí |
| Ubicación / Destino | Departamento asignado | Lista | Sí |
| Cuenta contable | 2-1-214-XX del clasificador | Lista | Sí |
| Estado del bien | Activo, En desuso, Faltante | Lista | Sí |
| Observaciones | Notas adicionales | Texto largo | No |

> **Caso especial — bienes históricos:** Los bienes con mucha antigüedad sin registro previo se cargarán con la herramienta de migración o manualmente por el Administrador, indicando la fecha de carga como fecha de registro.

#### 4.1.2 Estados de un bien
Cada bien tendrá en todo momento uno de los siguientes estados:
- **Activo** — bien en uso, asignado a un departamento.
- **En desuso** — bien que ya no se utiliza. Se registra motivo y fecha.
- **Faltante (Concepto 60)** — bien no localizado. Se registra responsable.

Ningún estado puede eliminarse. El historial de cambios de estado queda registrado.

#### 4.1.3 Tipos de movimiento
- **Incorporación** — alta de bien nuevo (genera entrada en BM-2).
- **Desincorporación** — baja o traslado (genera entrada en BM-2).
- **Marcado como faltante** — genera entrada en BM-3.
- **Cambio de departamento destino** — registrado en historial del bien.

---

### 4.2 Módulo B — Formularios oficiales BM

| Formulario | Nombre | Contenido principal | Cuándo se genera |
|---|---|---|---|
| BM-1 | Inventario de Bienes Muebles | Lista completa por unidad. Columnas: clasificación, código, N° identificación, cantidad, nombre/descripción, valor unitario, valor total. | Inventario periódico o a solicitud del jefe de unidad |
| BM-2 | Relación de Movimiento de Bienes | Incorporaciones y desincorporaciones del período. Origen, destino, precio unitario y valor total. | Cada incorporación o desincorporación registrada |
| BM-3 | Bienes Muebles Faltantes | Bienes Concepto 60 no localizados. Existencia física vs. registros, valor, cantidad y responsable. | Al detectar un bien faltante en inventario |
| BM-4 | Resumen de la Cuenta de Bienes | Existencia anterior + Incorporaciones − Desincorporaciones = Existencia final. Sello y firma del jefe. | Cierre de cada mes |

Todos los formularios generados quedan almacenados digitalmente con fecha, usuario y estado (vigente / anulado). No se pueden modificar una vez emitidos.

---

### 4.3 Módulo C — Catálogos maestros
El Administrador mantendrá los siguientes catálogos:
- **Departamentos / Centros de costo:** código y nombre de cada unidad.
- **Categorías de bienes:** lista editable de clasificaciones.
- **Cuentas contables:** catálogo 2-1-214-XX preconfigurado, modificable por Admin.
- **Usuarios:** nombre, cargo, perfil, estado activo/inactivo.

---

### 4.4 Módulo D — Auditoría
El sistema registrará automáticamente:
- Usuario que realizó la acción.
- Tipo de acción (crear, modificar, cambiar estado, generar formulario, etc.).
- Fecha y hora exacta.
- Datos antes y después del cambio (para modificaciones).

El log de auditoría no puede modificarse ni eliminarse. Solo el Administrador puede consultarlo.

---

### 4.5 Migración de datos históricos
El sistema proveerá una herramienta de importación que:
1. Lee los datos del sistema anterior (formato a definir en Fase 2).
2. Valida que no haya códigos duplicados.
3. Carga los bienes con estado 'Activo' y fecha de carga indicada.
4. Genera reporte de errores para registros que no pudieron migrarse.
5. Preserva el código original del bien del sistema anterior.

---

## 5. Plan de cuentas contables
Catálogo preconfigurado correspondiente al clasificador presupuestario 2-1-214 de Bienes Nacionales:

| Código | Descripción |
|---|---|
| 2-1-214-01 | Máquinas muebles y demás equipos de oficina |
| 2-1-214-02 | Mobiliario y enseres de alojamiento |
| 2-1-214-03 | Maquinarias y demás equipos de construcción |
| 2-1-214-04 | Equipos de transporte |
| 2-1-214-05 | Equipos de comunicación y señalamiento |
| 2-1-214-06 | Equipos médicos quirúrgicos dentales |
| 2-1-214-07 | Colecciones culturales, artísticas e históricas |
| 2-1-214-08 | Armamento y material de defensa |
| 2-1-214-09 | Instalaciones provisionales |
| 2-1-214-10 | Semovientes |
| 2-1-214-11 | (Reservado) |
| 2-1-214-13 | Equipos de procesamiento de datos |

Cuenta a abonar en incorporaciones: `2-3-299-01-XX` (Hacienda del Estado Superior), donde los dos últimos dígitos corresponden al año fiscal en curso.

---

## 6. Reglas de negocio

| ID | Módulo | Regla |
|---|---|---|
| RN-01 | Bienes Muebles | El código activo de cada bien debe ser único. No se permite duplicar. |
| RN-02 | Bienes Muebles | No se puede eliminar un bien. Solo se cambia su estado a 'En desuso' o 'Faltante'. |
| RN-03 | Bienes Muebles | Toda incorporación debe tener una Orden de Compra como referencia (campo opcional). |
| RN-04 | Bienes Muebles | Toda desincorporación debe registrar el motivo y el departamento destino o tipo de baja. |
| RN-05 | Bienes Muebles | El precio unitario se registra siempre sin IVA, conforme al manual del SIMA. |
| RN-06 | Bienes Muebles | La vida útil estándar es 60 meses. Solo el Administrador puede modificarla. |
| RN-07 | Formularios BM | Los formularios mantienen los códigos GOB-900-FM de la Gobernación del estado Bolívar. |
| RN-08 | Formularios BM | El BM-4 solo puede generarse al cierre de mes. El cálculo es automático: Existencia anterior + Incorporaciones − Desincorporaciones = Existencia final. |
| RN-09 | Formularios BM | Los formularios emitidos no pueden modificarse. Solo pueden anularse con justificación registrada. |
| RN-10 | Usuarios | El perfil Consulta no puede crear, modificar ni eliminar ningún registro. |
| RN-11 | Usuarios | Solo el Administrador puede crear, modificar o desactivar cuentas de usuario. |
| RN-12 | Auditoría | Todo registro, modificación o cambio de estado queda en el log con usuario, fecha y hora. |
| RN-13 | Migración | Los bienes del sistema anterior se importan con estado 'Activo'. El código original se preserva. |

---

## 7. Casos de uso

| ID | Nombre | Actor | Descripción breve |
|---|---|---|---|
| CU-01 | Registrar bien mueble | Almacenista | Ingresa datos del bien y lo incorpora al inventario generando movimiento BM-2. |
| CU-02 | Consultar bien | Almacenista / Consulta | Busca bien por código, descripción, departamento o estado. |
| CU-03 | Desincorporar bien | Almacenista | Cambia estado a 'En desuso', registra motivo y fecha. |
| CU-04 | Registrar bien faltante | Almacenista | Marca bien como Concepto 60 e identifica al responsable. |
| CU-05 | Generar BM-1 | Almacenista / Admin | Genera inventario por unidad en PDF imprimible. |
| CU-06 | Generar BM-2 | Almacenista / Admin | Genera relación de movimientos del período en PDF. |
| CU-07 | Generar BM-3 | Almacenista / Admin | Genera relación de bienes faltantes en PDF. |
| CU-08 | Generar BM-4 | Administrador | Genera resumen mensual con existencia final calculada. |
| CU-09 | Gestionar usuarios | Administrador | Crea, modifica o desactiva cuentas y perfiles de acceso. |
| CU-10 | Migrar datos históricos | Administrador | Importa registros del sistema anterior al SIGEMA. |
| CU-11 | Gestionar catálogos | Administrador | Mantiene catálogos de departamentos, cuentas y categorías. |
| CU-12 | Consultar auditoría | Administrador | Consulta log de todas las acciones de los usuarios. |

### 7.1 Detalle: CU-01 Registrar bien mueble

| Campo | Detalle |
|---|---|
| Actor principal | Almacenista |
| Precondición | Usuario autenticado con perfil Almacenista o Administrador |
| Flujo principal | 1. Selecciona 'Nuevo bien' en el módulo de Bienes Muebles. 2. Ingresa todos los campos obligatorios. 3. Selecciona la cuenta contable 2-1-214-XX. 4. Selecciona el departamento destino. 5. Confirma el registro. 6. El sistema asigna correlativo, registra la incorporación y actualiza el inventario. |
| Flujo alternativo | Si el código activo ya existe, el sistema muestra error y no permite continuar. |
| Postcondición | El bien queda en estado 'Activo'. El movimiento queda disponible para BM-2. |

---

## 8. Requerimientos no funcionales

| ID | Categoría | Requerimiento |
|---|---|---|
| NF-01 | Plataforma | Aplicación de escritorio Windows 10 / 11. Compatible con equipos existentes del instituto. |
| NF-02 | Concurrencia | Soportar 4 a 6 usuarios simultáneos en red local LAN sin degradación de rendimiento. |
| NF-03 | Base de datos | PostgreSQL 15. La BD reside en un servidor local del instituto. |
| NF-04 | Respaldo | Generar backup de la base de datos desde la interfaz de administración. |
| NF-05 | Seguridad | Acceso por usuario y contraseña. Contraseñas con hash bcrypt. Sesión expira a los 30 min de inactividad. |
| NF-06 | Reportes | Formularios BM-1 al BM-4 generados en PDF listo para imprimir, con formato oficial GOB-900-FM. |
| NF-07 | Usabilidad | Interfaz de escritorio clásica estilo FoxPro/Windows, acorde al perfil de los usuarios actuales. |
| NF-08 | Migración | Herramienta de importación para cargar datos históricos del sistema anterior. |
| NF-09 | Auditoría | Registro automático de toda acción: usuario, acción, fecha/hora y datos afectados. |
| NF-10 | Soporte | El encargado de IT del instituto puede instalar y configurar el sistema con la documentación provista. |

---

## 9. Base de datos — 8 tablas

### Tablas principales
- `bien` — tabla central, 22 campos
- `movimiento` — incorporaciones, desincorporaciones y faltantes
- `formulario_bm` — registro de formularios BM generados

### Catálogos
- `departamento` — unidades organizativas
- `categoria` — clasificación de bienes
- `cuenta_contable` — plan de cuentas 2-1-214-XX

### Seguridad
- `usuario` — cuentas con hash bcrypt y perfil de acceso
- `auditoria` — log de todas las acciones con datos_antes y datos_despues en JSON

---

## 10. Plan de implementación

| Fase | Actividades | Entregable | Duración | Estado |
|---|---|---|---|---|
| 1 | Levantamiento de información, validación de catálogos | Guía de reunión firmada + SRS aprobado | 1 sem. | ✅ Completada |
| 2 | Diseño de BD PostgreSQL y ERD | script SQL + ERD validado | 1 sem. | 🔄 En progreso |
| 3 | Desarrollo Módulo A: registro de bienes y movimientos | Módulo A funcional | 3 sem. | ⏳ Pendiente |
| 4 | Desarrollo generación de formularios BM-1 al BM-4 en PDF | Formularios correctos e imprimibles | 1 sem. | ⏳ Pendiente |
| 5 | Desarrollo Módulo C: usuarios, catálogos y auditoría | Sistema completo integrado | 1 sem. | ⏳ Pendiente |
| 6 | Migración de datos históricos del sistema anterior | Datos migrados y verificados | 1 sem. | ⏳ Pendiente |
| 7 | Pruebas, correcciones y empaquetado | Sistema en producción (.exe + install_server.ps1) | 1 sem. | ⏳ Pendiente |

---

## 11. Instalación en producción

### Arquitectura
- **Servidor:** PostgreSQL 15 en un PC con IP fija en la red LAN
- **Clientes:** `sigema.exe` generado con PyInstaller en cada PC de usuario
- **Sin internet:** operación 100% en red local

### Distribución
```
instalacion/
├── servidor/
│   ├── install_server.ps1       # instala PostgreSQL y crea la BD automáticamente
│   ├── schema.sql
│   └── INSTRUCCIONES_SERVIDOR.txt
└── cliente/
    ├── sigema.exe               # incluye Python y todas las dependencias
    └── INSTRUCCIONES_CLIENTE.txt
```

---

## 12. Pendientes y decisiones abiertas

| ID | Decisión pendiente | Responsable | Para la fase |
|---|---|---|---|
| DP-01 | Definir formato exacto de los datos del sistema anterior para planificar la migración. | Luigger / Encargado IT | Fase 2 |
| DP-02 | Confirmar número exacto de SKUs (artículos distintos) que maneja el instituto. | Encargado de bienes | Fase 2 |
| DP-03 | Definir si los materiales e insumos mineros se incorporan en una fase posterior. | Dirección del instituto | Fase 2+ |
| DP-04 | Confirmar si se requiere módulo de depreciación automática en versiones futuras. | Dirección del instituto | Fase 2+ |
| DP-05 | Validar con el jefe de unidad el flujo exacto de autorización de los formularios BM. | Jefe División Control Bienes | Fase 3 |
