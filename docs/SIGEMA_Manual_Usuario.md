# Manual de Usuario — SIGEMA

### Sistema de Gestión de Bienes Muebles
**Instituto Autónomo Minas Bolívar**
División de Control de Bienes — Gobernación del estado Bolívar

Versión 1.0

---

## Índice

1. [Introducción](#1-introducción)
2. [Conceptos básicos](#2-conceptos-básicos)
3. [Perfiles de usuario y permisos](#3-perfiles-de-usuario-y-permisos)
4. [Primer arranque y configuración inicial](#4-primer-arranque-y-configuración-inicial)
5. [Iniciar sesión](#5-iniciar-sesión)
6. [La ventana principal](#6-la-ventana-principal)
7. [Módulo Bienes Muebles](#7-módulo-bienes-muebles)
8. [Estados de un bien](#8-estados-de-un-bien)
9. [Módulo Donaciones](#9-módulo-donaciones)
10. [Stickers de identificación](#10-stickers-de-identificación)
11. [Módulo Formularios BM](#11-módulo-formularios-bm)
12. [Módulo Usuarios (Administrador)](#12-módulo-usuarios-administrador)
13. [Módulo Catálogos (Administrador)](#13-módulo-catálogos-administrador)
14. [Módulo Auditoría (Administrador)](#14-módulo-auditoría-administrador)
15. [Migración de datos (Administrador)](#15-migración-de-datos-administrador)
16. [Respaldo (Backup) de la base de datos](#16-respaldo-backup-de-la-base-de-datos)
17. [Cierre de sesión y expiración](#17-cierre-de-sesión-y-expiración)
18. [Preguntas frecuentes y solución de problemas](#18-preguntas-frecuentes-y-solución-de-problemas)

---

## 1. Introducción

SIGEMA es la aplicación de escritorio que el Instituto Autónomo Minas Bolívar
usa para llevar el control de todos sus **bienes muebles** (mobiliario,
equipos, vehículos, herramientas, etc.). Reemplaza los formularios físicos
por un registro digital centralizado y permite generar los formularios
oficiales **BM-1, BM-2, BM-3 y BM-4** de la Gobernación del estado Bolívar,
listos para imprimir y firmar.

Este manual está dirigido a las **personas que usan el programa en su día a
día**: almacenistas, personal de consulta y administradores. No requiere
conocimientos técnicos.

> 📷 **[Captura 1 — Pantalla principal de SIGEMA con un bien seleccionado]**

> **Cómo funciona en la oficina:** existe **una sola base de datos** en el
> equipo servidor y cada computador tiene instalado el programa `sigema.exe`.
> Todos trabajan sobre la misma información a través de la red local. No se
> necesita internet.

---

## 2. Conceptos básicos

| Término | Qué significa |
|---|---|
| **Bien mueble** | Cualquier activo del instituto que se registra y controla (equipo, mobiliario, vehículo, etc.). |
| **Código activo** | Identificador único de cada bien. El sistema lo sugiere automáticamente al registrar. |
| **Departamento** | Unidad o dependencia donde se encuentra el bien. Puede tener subdepartamentos. |
| **Categoría** | Clasificación del bien (ej.: mobiliario, equipos de computación). |
| **Cuenta contable** | Código del plan de cuentas oficial **2-1-214-XX** al que pertenece el bien. |
| **Estado** | Condición actual del bien (operativo, dañado, desincorporado, etc.). Ver [sección 8](#8-estados-de-un-bien). |
| **Formulario BM** | Documento oficial que el sistema genera en PDF (BM-1 a BM-4). |
| **Origen** | Indica si el bien fue adquirido por **Compra** o por **Donación**. |

Los campos marcados con **(\*)** en las pantallas son **obligatorios**.

---

## 3. Perfiles de usuario y permisos

Cada usuario tiene **un perfil** que determina qué pestañas ve y qué acciones
puede realizar:

| Acción | Administrador | Almacenista | Consulta |
|---|:---:|:---:|:---:|
| Ver bienes y formularios | ✅ | ✅ | ✅ |
| Registrar bienes nuevos | ✅ | ✅ | ❌ |
| Cambiar el estado de un bien | ✅ | ✅ | ❌ |
| Editar/corregir datos de un bien | ✅ | ❌ | ❌ |
| Generar e imprimir formularios BM | ✅ | ✅ | ❌ |
| Anular formularios | ✅ | ✅ | ❌ |
| Imprimir stickers | ✅ | ✅ | ✅ |
| Gestionar usuarios | ✅ | ❌ | ❌ |
| Gestionar catálogos | ✅ | ❌ | ❌ |
| Ver auditoría | ✅ | ❌ | ❌ |
| Migrar datos históricos | ✅ | ❌ | ❌ |
| Realizar respaldo (backup) | ✅ | ❌ | ❌ |

El perfil **Consulta** solo puede ver y consultar: los botones de creación y
edición permanecen ocultos para este perfil.

---

## 4. Primer arranque y configuración inicial

La **primera vez** que se abre `sigema.exe` en un computador, aparece la
pantalla **Configuración inicial** porque el programa aún no sabe dónde está la
base de datos.

> Esta pantalla normalmente la completa el encargado de informática **una sola
> vez por equipo**. Una vez configurada, no vuelve a aparecer.

Pasos:

1. En **Conexión a PostgreSQL**, llene los datos:

   | Campo | Valor típico |
   |---|---|
   | Servidor (IP/Host) | La IP del equipo servidor (ej.: `192.168.1.10`) |
   | Puerto | `5432` |
   | Base de datos | `sigema` |
   | Usuario BD | `sigema_user` |
   | Contraseña BD | La definida al instalar el servidor |

2. En **Directorio de respaldos**, elija (con el botón **…**) la carpeta donde
   se guardarán los backups. El sistema propone una carpeta `backups` por
   defecto.
3. Haga clic en **🔌 Probar conexión**. Debe aparecer el mensaje verde
   *"✔ Conexión exitosa"*. Si sale un error rojo, revise la IP, el usuario o la
   contraseña con el encargado de IT.
4. Haga clic en **Guardar y continuar**. El programa guarda la configuración y
   abre la pantalla de inicio de sesión.

> 📷 **[Captura 2 — Pantalla de Configuración inicial con la prueba de conexión exitosa]**

---

## 5. Iniciar sesión

En la pantalla de inicio de sesión:

1. Escriba su **Usuario** y su **Contraseña**.
2. Puede pulsar el botón **👁** para mostrar u ocultar la contraseña.
3. Haga clic en **Ingresar** (o presione **Enter**).

**Usuario inicial del sistema:** `admin` / `admin123`.

> ⚠️ **Importante:** por seguridad, cambie la contraseña del administrador en
> el primer uso (ver [Módulo Usuarios](#12-módulo-usuarios-administrador)).

Si los datos son incorrectos o la cuenta está inactiva, aparecerá el mensaje
*"Usuario o contraseña incorrectos, o cuenta inactiva."*

> 📷 **[Captura 3 — Pantalla de inicio de sesión]**

---

## 6. La ventana principal

Tras iniciar sesión se abre la ventana principal:

- **Encabezado:** logo del instituto, nombre del sistema y, a la derecha, su
  **nombre y perfil** activos.
- **Pestañas:** una por cada módulo al que tiene acceso (varían según su
  perfil).
- **Menú 🔧 Herramientas** (arriba): permite **Realizar Backup** (solo
  Administrador) y **Cerrar sesión**.
- **Barra de estado** (abajo): muestra su usuario y perfil.

Las pestañas que puede ver son:

| Pestaña | Perfiles que la ven |
|---|---|
| Bienes Muebles | Todos |
| Donaciones | Todos |
| Formularios BM | Administrador y Almacenista |
| Usuarios | Solo Administrador |
| Catálogos | Solo Administrador |
| Auditoría | Solo Administrador |
| Migración | Solo Administrador |

> **Cierre automático por inactividad:** si deja el programa abierto sin usarlo
> durante **30 minutos**, la sesión se cierra automáticamente y deberá volver
> a iniciar sesión.

> 📷 **[Captura 4 — Ventana principal señalando encabezado, pestañas, menú Herramientas y barra de estado]**

---

## 7. Módulo Bienes Muebles

Es la pestaña principal. Muestra una **tabla** con todos los bienes y sus
columnas: Código Activo, Descripción, Categoría, Departamento, Estado y Fecha
de Registro.

> Las filas se **colorean según el estado** del bien: amarillo para
> inoperativos recuperables (05), rojo para irrecuperables (06) y gris para
> desincorporados (07). Ver [sección 8](#8-estados-de-un-bien).

### 7.1 Buscar bienes

En el área **Filtros de búsqueda** puede combinar:

- **Código:** parte del código del bien.
- **Descripción:** parte del nombre o descripción.
- **Departamento:** elija uno de la lista.
- **Estado:** elija un estado o "Todos".

Haga clic en **🔍 Buscar** para aplicar los filtros. El botón **↺ Actualizar**
recarga la lista completa (sin filtros).

> 📷 **[Captura 5 — Listado de bienes con el área de filtros y la barra de botones de acción]**

### 7.2 Registrar un bien nuevo

> Disponible para Administrador y Almacenista.

1. Haga clic en **➕ Nuevo**. Se abre el formulario **Nuevo Bien Mueble**.
2. Seleccione el **Origen del bien**: **Compra** o **Donación**. Según lo que
   elija, cambian algunos campos (ver más abajo).
3. Complete los datos. El sistema sugiere automáticamente el **Código de
   nivel** y el **Código activo**, que puede ajustar si hace falta.

**Campos por sección:**

- **Identificación:** código de nivel (\*), código activo (\*), descripción
  (\*), categoría (\*).
- **Características:** marca, modelo, serial, color, tipo y N° de piezas (\*).
- **Adquisición:**
  - Si es **Compra:** N° de orden de compra (opcional), fecha de compra (\*),
    precio sin IVA (\*), moneda (\*) y vida útil en meses (\*).
  - Si es **Donación:** en lugar de la orden y la fecha de compra, se usan los
    **Datos de la donación** (ver abajo). El campo de precio pasa a llamarse
    *"Valor estimado"*.
- **Datos de la donación** (solo si el origen es Donación): nombre del donante
  (\*), tipo de donante (Institución / Persona natural), N° de acta (opcional),
  fecha de donación (\*) y observaciones.
- **Ubicación y Contabilidad:** departamento (\*), cuenta contable (\*) y
  estado (\*). Los bienes nuevos quedan por defecto en estado **01 – Operativo,
  en uso, excelente estado**.
- **Observaciones:** notas libres opcionales.

4. Haga clic en **💾 Guardar**. Si falta algún campo obligatorio, el sistema lo
   avisará. Al guardar correctamente, se muestra el ID asignado y el bien
   aparece en la tabla.

> 📷 **[Captura 6 — Formulario "Nuevo Bien Mueble" en origen Compra]**
>
> 📷 **[Captura 7 — Formulario "Nuevo Bien Mueble" en origen Donación, mostrando la sección "Datos de la donación"]**

### 7.3 Ver o editar un bien

1. Seleccione un bien en la tabla.
2. Haga clic en **👁 Ver / ✏ Editar**.
   - Si es **Administrador**, el formulario se abre en modo **edición**.
   - Para los demás perfiles, se abre en modo **solo lectura** (el botón
     aparece como *"👁 Ver detalle"*).

**Qué se puede corregir (solo Administrador):** descripción, categoría, marca,
modelo, serial, color, tipo, N° de piezas, orden de compra, cuenta contable,
vida útil y observaciones.

**Qué queda fijo** (no se puede cambiar desde aquí): origen, código activo,
código de nivel, fecha de compra, precio, moneda, departamento y estado. El
departamento y el estado tienen sus propios flujos (cambio de estado), y los
datos de la donación se consultan desde el módulo de Donaciones.

Pulse **💾 Guardar cambios** para confirmar.

### 7.4 Cambiar el estado de un bien

Vea la sección dedicada: [Estados de un bien](#8-estados-de-un-bien).

### 7.5 Imprimir stickers

Seleccione un bien y pulse **🏷 Sticker**. Vea la sección
[Stickers de identificación](#10-stickers-de-identificación).

---

## 8. Estados de un bien

Cada bien tiene un **estado** que refleja su condición. Existen **7 estados
oficiales**:

| Código | Estado | Color en la lista |
|:---:|---|---|
| 01 | Operativo, en uso, excelente estado | — |
| 02 | Operativo, en uso pero requiere reparación | — |
| 03 | Operativo, sin uso, en excelente estado | — |
| 04 | Operativo, sin uso, pero requiere reparación | — |
| 05 | Inoperativo, pero recuperable | Amarillo |
| 06 | Inoperativo, irrecuperable | Rojo |
| 07 | Desincorporado en desuso | Gris |

### 8.1 Reglas de cambio de estado

El sistema solo permite los cambios que tienen sentido:

- **01–04 (operativos):** pueden pasar libremente a cualquier otro estado.
- **05 (recuperable):** puede recuperarse (01–04), agravarse (06) o
  desincorporarse (07). **Requiere describir el daño.**
- **06 (irrecuperable):** solo puede pasar a **07**. Genera una entrada en el
  formulario **BM-3** (Concepto 60 — faltantes). **Requiere describir el daño.**
- **07 (desincorporado):** es un estado **final**, no admite más cambios.
  Genera una entrada en el formulario **BM-2**. **Requiere indicar el motivo de
  desincorporación.**

### 8.2 Cómo cambiar el estado

> Disponible para Administrador y Almacenista.

1. En la pestaña **Bienes Muebles**, seleccione el bien.
2. Haga clic en **⏸ Cambiar Estado**.
3. La ventana muestra los **datos actuales** y el **estado actual** (con su
   color).
4. En **Nuevo estado**, elija uno de los estados permitidos (el sistema solo
   lista los válidos).
5. Según el estado elegido, complete el campo que aparezca:
   - **Descripción del daño** (\*) si pasa a 05 o 06.
   - **Motivo de desincorporación** (\*) si pasa a 07.
6. Pulse **✔ Confirmar**.

Si el bien está en un estado final (07) o bloqueado, el sistema lo indicará y
no permitirá cambios.

> 📷 **[Captura 8 — Diálogo "Cambiar Estado del Bien" mostrando el campo de descripción del daño / motivo]**

---

## 9. Módulo Donaciones

La pestaña **Donaciones** muestra, en modo **solo lectura**, todos los bienes
que ingresaron por donación.

> Los bienes donados se **registran** desde el formulario de bien nuevo
> eligiendo origen **Donación** (ver [sección 7.2](#72-registrar-un-bien-nuevo)).
> Desde esta pestaña solo se consultan; no se modifican.

Columnas: Código Bien, Descripción, Donante, Tipo, Fecha de Donación y N° de
Acta.

**Filtros disponibles:**

- **Donante:** parte del nombre del donante.
- **Filtrar por fecha:** marque la casilla y elija el rango **Desde / Hasta**.

Pulse **🔍 Buscar** para filtrar y **↺ Actualizar** para recargar todo.

Para ver la ficha completa del bien donado, selecciónelo y pulse
**👁 Ver bien** (se abre en modo solo lectura).

> 📷 **[Captura 9 — Listado de Donaciones con los filtros por donante y fecha]**

---

## 10. Stickers de identificación

Los stickers son etiquetas físicas que se pegan a los bienes. Se accede al
diálogo desde el botón **🏷 Sticker** del listado de bienes o desde el botón
**🏷 Imprimir Sticker** dentro del detalle de un bien.

> La impresión de stickers es solo de consulta: **no modifica datos ni genera
> registros de auditoría**. Está disponible para todos los perfiles.

**Dos modos:**

- **Sticker individual (1 bien):** genera la etiqueta de un solo bien
  (10 × 4 cm).
- **Hoja de stickers:** seleccione **varios** bienes (con **Ctrl** o **Shift**)
  para generar una hoja carta con hasta **12 stickers por página**.

Pasos:

1. Elija el modo arriba.
2. Use el campo **Buscar** (por código o descripción) para encontrar los
   bienes. Si abrió el diálogo desde un bien, este ya aparece preseleccionado.
3. Seleccione el o los bienes en la tabla.
4. Pulse **👁 Vista previa** para revisar el PDF, o **🖨 Imprimir** para
   enviarlo directamente a la impresora.

> 📷 **[Captura 10 — Diálogo "Stickers de Bienes" con el modo y la selección de bienes]**

---

## 11. Módulo Formularios BM

> Disponible para Administrador y Almacenista (generar/anular). El perfil
> Consulta solo ve el historial.

La pestaña **Formularios BM** permite generar los cuatro formularios oficiales
y consultar el historial de los emitidos.

### 11.1 Los cuatro formularios

| Tipo | Código GOB | Qué contiene | Parámetros que pide |
|---|---|---|---|
| **BM-1** | GOB-900-FM-086/15 | Inventario general por unidad de trabajo | Departamento |
| **BM-2** | GOB-900-FM-085/15 | Relación de movimientos del período | Departamento, Mes, Año y Concepto |
| **BM-3** | GOB-900-FM-078/15 | Relación de bienes faltantes (Concepto 60) | Departamento |
| **BM-4** | GOB-900-FM-077/15 | Resumen mensual de la cuenta de bienes | Departamento, Mes, Año |

El formulario va mostrando solo los campos que necesita: el **período (Mes/Año)**
aparece para BM-2 y BM-4, y el **Concepto** (Todos / Incorporación /
Desincorporación) solo para BM-2.

> 📷 **[Captura 11 — Pestaña Formularios BM: sección de generación e historial de emitidos]**

### 11.2 Generar un formulario

1. En **Generar formulario BM**, elija el **Tipo** y el **Departamento**.
2. Complete el período y/o concepto si el tipo lo requiere.
3. Pulse una de las dos opciones:
   - **📑 Generar PDF:** abre una **vista previa** del documento en su visor de
     PDF.
   - **🖨 Imprimir:** envía el documento directamente a la impresora.
4. En ambos casos, el sistema pregunta si desea **GUARDAR Y EMITIR** el
   formulario de forma permanente.
   - Pulse **Save (Guardar)** para registrarlo oficialmente en el historial.
   - Pulse **Cancel (Cancelar)** si solo era una revisión: no se guardará nada.

> ⚠️ **RN-09:** emitir un formulario es una acción **irreversible**. Una vez
> emitido, queda en el historial y solo podrá **anularse** (no borrarse).

> 📷 **[Captura 12 — Diálogo "Confirmar Emisión" tras la vista previa del PDF]**

### 11.3 Historial de formularios

La tabla inferior lista todos los formularios emitidos con: ID, Tipo, Fecha de
generación, quién lo generó, Estado (Emitido / Anulado) y Motivo de anulación.

- **📄 Ver / Descargar PDF:** seleccione un formulario y descargue su PDF
  guardado. (Los formularios muy antiguos podrían no tener PDF almacenado.)
- **↺ Actualizar:** recarga el historial.

### 11.4 Anular un formulario

> Disponible para Administrador y Almacenista.

1. Seleccione el formulario en la tabla.
2. Pulse **🚫 Anular Formulario**.
3. Escriba el **motivo de anulación** (obligatorio) y confirme.

El formulario no se elimina: queda marcado como **Anulado** con su motivo, para
mantener la trazabilidad. Un formulario ya anulado no puede anularse de nuevo.

---

## 12. Módulo Usuarios (Administrador)

> Solo visible para el perfil Administrador. Los usuarios **nunca se eliminan**:
> se **activan o desactivan**.

La pestaña **Usuarios** lista todas las cuentas con: Nombre completo, Cargo,
Username, Perfil y Estado (Activo / Inactivo).

### 12.1 Crear un usuario

1. Pulse **➕ Nuevo usuario**.
2. Complete: Nombre (\*), Apellido (\*), Cargo, Username (\*), Perfil (\*),
   Contraseña (\*) y su confirmación.
3. Pulse **Guardar**.

> 📷 **[Captura 13 — Pestaña Usuarios y formulario "Nuevo usuario"]**

Reglas:
- El **username** no puede repetirse.
- La contraseña debe tener **al menos 6 caracteres** y coincidir con su
  confirmación.

### 12.2 Editar un usuario

1. Seleccione el usuario (o haga doble clic) y pulse **✏ Editar**.
2. Modifique los datos necesarios.
3. Para **cambiar la contraseña**, escriba la nueva; para **dejarla igual**,
   deje el campo vacío.
4. Pulse **Guardar**.

### 12.3 Activar o desactivar un usuario

1. Seleccione el usuario y pulse **⏸ Activar / Desactivar**.
2. Confirme.

Un usuario **inactivo** no puede iniciar sesión. **No puede desactivar su
propia cuenta.**

---

## 13. Módulo Catálogos (Administrador)

> Solo visible para el perfil Administrador.

La pestaña **Catálogos** organiza los datos maestros en tres sub-pestañas.

### 13.1 Departamentos

CRUD completo con jerarquía (departamentos y subdepartamentos).

- **➕ Nuevo:** código (\*), nombre (\*), descripción y, opcionalmente,
  *"Subdepartamento de"* para colgarlo de un departamento raíz.
- **✏ Editar:** modifica un departamento existente (o doble clic).
- **⏸ Activar/Desactivar:** habilita o deshabilita un departamento.

El **código** de departamento no puede repetirse.

### 13.2 Categorías

CRUD completo de categorías de bienes.

- **➕ Nueva:** nombre (\*) y descripción.
- **✏ Editar** y **⏸ Activar/Desactivar** como en Departamentos.

El **nombre** de categoría no puede repetirse.

### 13.3 Cuentas Contables

Es el catálogo oficial **2-1-214-XX** del Estado. **No se crean ni editan**
cuentas: solo se pueden **⏸ Activar / Desactivar** según se necesiten.

> 📷 **[Captura 14 — Pestaña Catálogos mostrando las sub-pestañas Departamentos, Categorías y Cuentas Contables]**

---

## 14. Módulo Auditoría (Administrador)

> Solo visible para el perfil Administrador. El registro es **inmutable**: solo
> se consulta y se exporta.

La pestaña **Auditoría** muestra el historial de acciones del sistema (quién
hizo qué y cuándo), con columnas: Fecha/Hora, Usuario, Acción, Tabla, Registro
ID e IP de origen.

**Filtros:**

- **Usuario:** filtra por quién realizó la acción.
- **Desde / Hasta:** rango de fechas (por defecto, los últimos 30 días).
- **Acción:** Crear, Actualizar, Actualizar estado, Cambiar estado, etc.

Pulse **🔍 Buscar** para aplicar. El contador indica cuántos registros se
encontraron (la consulta muestra hasta **500**; si llega a ese tope, acote con
los filtros).

**📄 Exportar CSV:** guarda los resultados visibles en un archivo CSV (separado
por `;`, compatible con Excel) para entregar a contraloría interna.

> 📷 **[Captura 15 — Panel de Auditoría con filtros y resultados]**

---

## 15. Migración de datos (Administrador)

> Solo visible para el perfil Administrador. Es una herramienta para cargar al
> sistema los bienes que venían del **sistema anterior (FoxPro)**.

La pestaña **Migración** acepta archivos **.dbf** del FoxPro (con su `.fpt` al
lado) y también **CSV, Excel (.xlsx/.xlsm) y JSON**.

Al migrar se preserva el código original, el estado real del FoxPro y el origen
**Compra**; la cuenta contable se asigna por defecto a **2-1-214-01** (puede
reclasificarse luego en SIGEMA). Cada inserción queda registrada en auditoría.

**Pasos:**

1. **Seleccionar archivo:** pulse **📂 Seleccionar archivo** y elija el archivo
   de origen.
2. **Validar:** pulse **✓ Validar**. El sistema lee el archivo y muestra:
   - Total de registros encontrados.
   - Registros **válidos** para migrar.
   - Registros **con errores**, con el detalle (fila, campo y motivo).
3. **Ejecutar migración:** si hay registros válidos, pulse **⏩ Ejecutar
   migración** y confirme. Una barra de progreso muestra el avance.
4. Al terminar, se muestra cuántos se **insertaron** y cuántos **fallaron**.
5. **Descargar reporte de errores:** si hubo errores, pulse **📄 Descargar
   reporte de errores** para guardar un CSV con el detalle y corregir el origen.

> 📷 **[Captura 16 — Panel de Migración tras validar, mostrando totales, válidos y errores]**

---

## 16. Respaldo (Backup) de la base de datos

> Disponible solo para el perfil Administrador.

1. En el menú **🔧 Herramientas**, elija **💾 Realizar Backup**.
2. Confirme con **Sí**.
3. El sistema genera el respaldo en la carpeta configurada (ver
   [sección 4](#4-primer-arranque-y-configuración-inicial)) y muestra la ruta
   del archivo generado.

> 📷 **[Captura 17 — Menú Herramientas → Realizar Backup y mensaje de respaldo exitoso]**

Se recomienda hacer respaldos periódicos y guardarlos en un lugar seguro.

---

## 17. Cierre de sesión y expiración

- **Cerrar sesión manualmente:** menú **🔧 Herramientas → 🔒 Cerrar sesión**.
  Vuelve a la pantalla de inicio de sesión.
- **Expiración automática:** tras **30 minutos** de inactividad, la sesión se
  cierra sola por seguridad y aparece el aviso *"Su sesión expiró por
  inactividad"*. Deberá iniciar sesión de nuevo.

---

## 18. Preguntas frecuentes y solución de problemas

**No puedo iniciar sesión.**
Verifique usuario y contraseña (use el botón 👁 para revisar lo que escribe).
Si la cuenta fue desactivada, contacte al Administrador. El usuario inicial es
`admin` / `admin123`.

**Al abrir el programa aparece "Error de conexión".**
El equipo no logra contactar la base de datos. Verifique que el servidor esté
encendido y conectado a la red. Si persiste, el encargado de IT debe revisar la
configuración (IP, usuario, contraseña).

**No veo la pestaña de Usuarios / Catálogos / Auditoría / Migración.**
Esas pestañas solo están disponibles para el perfil **Administrador**.

**No aparecen los botones "Nuevo" o "Cambiar Estado".**
Su perfil es **Consulta**, que es de solo lectura. Pida a un Administrador o
Almacenista que realice la operación, o que ajuste su perfil.

**Generé un formulario pero no quedó guardado.**
Al generar, el sistema pregunta si desea **Guardar y emitir**. Si pulsó
*Cancelar*, el formulario no se guarda. Vuelva a generarlo y pulse *Guardar*.

**¿Puedo borrar un bien, un usuario o un formulario?**
No. Por trazabilidad, los bienes se **desincorporan** (estado 07), los usuarios
se **desactivan** y los formularios se **anulan**. Nada se elimina físicamente.

**¿Por qué algunas filas de bienes salen en color?**
El color indica el estado: **amarillo** = inoperativo recuperable (05),
**rojo** = inoperativo irrecuperable (06), **gris** = desincorporado (07).

**Se cerró la sesión sola.**
Es normal tras 30 minutos sin actividad. Inicie sesión nuevamente.

---

*Documento de uso interno — Instituto Autónomo Minas Bolívar. Todos los
derechos reservados.*
