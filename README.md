# SIGEMA
### Sistema de Gestión de Almacén
**Instituto Autónomo Minas Bolívar**

---

## Descripción

SIGEMA es una aplicación de escritorio para Windows desarrollada para modernizar el control de bienes muebles del Instituto Autónomo Minas Bolívar. Reemplaza el proceso manual de formularios físicos por un sistema digital centralizado que mantiene trazabilidad completa de todos los activos del instituto.

El sistema genera los formularios oficiales **BM-1, BM-2, BM-3 y BM-4** conforme a los estándares de la Gobernación del estado Bolívar (códigos GOB-900-FM), listos para impresión y firma física.

---

## Características principales

- Registro completo de bienes muebles con plan de cuentas 2-1-214-XX preconfigurado
- Control de incorporaciones, desincorporaciones y bienes faltantes (Concepto 60)
- Generación e impresión de formularios BM-1 al BM-4 en PDF
- Historial de movimientos por bien con trazabilidad completa
- Gestión de usuarios con tres perfiles: Administrador, Almacenista y Consulta
- Log de auditoría de todas las acciones del sistema
- Herramienta de migración de datos históricos del sistema anterior
- Operación 100% en red local LAN, sin dependencia de internet

---

## Tecnología

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Interfaz | PyQt6 |
| Base de datos | PostgreSQL 15 |
| Reportes PDF | ReportLab |
| Empaquetado | PyInstaller |
| Control de versiones | Git / GitHub |

---

## Arquitectura de instalación

SIGEMA funciona en red local con una arquitectura cliente-servidor simple:

```
                    RED LOCAL (LAN)
                         │
          ┌──────────────┼──────────────┐
          │              │              │
     PC usuario 1   PC usuario 2   PC usuario 3
     sigema.exe     sigema.exe     sigema.exe
          │              │              │
          └──────────────┼──────────────┘
                         │
                  PC SERVIDOR
               PostgreSQL 15
               Base de datos
                  sigema
```

- **Un solo servidor** con PostgreSQL donde vive la base de datos
- **Cada PC de usuario** tiene el ejecutable `sigema.exe` instalado
- Comunicación por red LAN interna — no requiere internet

---

## Instalación

### Parte 1 — Servidor (solo una vez, lo realiza el encargado de IT)

**Requisitos del servidor:**
- Windows 10 / 11
- Mínimo 4 GB RAM
- Conectado a la red local LAN
- IP fija en la red local

**Pasos:**

1. Copiar la carpeta `instalacion/servidor/` al equipo servidor
2. Abrir PowerShell como Administrador
3. Ejecutar el script de instalación:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install_server.ps1
```

El script instala PostgreSQL 15, crea la base de datos `sigema`, crea el usuario de acceso y configura la red local automáticamente.

4. Anotar la IP del servidor (se necesita para configurar los clientes):

```powershell
ipconfig
```

---

### Parte 2 — Clientes (cada PC de usuario)

**Requisitos de cada cliente:**
- Windows 10 / 11
- Conectado a la misma red LAN que el servidor

**Pasos:**

1. Copiar `sigema.exe` al escritorio del equipo
2. Ejecutar `sigema.exe` por primera vez
3. Completar la pantalla de configuración inicial:

| Campo | Valor |
|---|---|
| IP del servidor | (la IP anotada en el paso anterior) |
| Puerto | 5432 |
| Base de datos | sigema |
| Usuario | sigema_user |
| Contraseña | (la definida durante la instalación del servidor) |

4. Hacer clic en **Conectar** — el sistema guarda la configuración y abre el login
5. Ingresar con el usuario inicial: `admin` / `admin123`

> **Importante:** Cambiar la contraseña del administrador al primer inicio de sesión.

---

## Estructura del proyecto

```
sigema/
├── src/
│   ├── core/              # lógica de negocio y reglas del sistema
│   ├── db/                # conexión y queries PostgreSQL
│   ├── ui/                # pantallas y componentes de interfaz
│   └── reports/           # generación de formularios BM en PDF
├── docs/                  # documentación del proyecto
│   ├── SIGEMA_Propuesta.docx
│   ├── SIGEMA_SRS.docx
│   └── SIGEMA_Guia_Reunion.docx
├── sql/
│   └── schema.sql         # script de creación de base de datos
├── instalacion/
│   ├── servidor/
│   │   ├── install_server.ps1
│   │   ├── schema.sql
│   │   └── INSTRUCCIONES_SERVIDOR.txt
│   └── cliente/
│       ├── sigema.exe
│       └── INSTRUCCIONES_CLIENTE.txt
├── tests/                 # pruebas unitarias
├── requirements.txt       # dependencias Python
├── config.example.ini     # plantilla de configuración
└── README.md
```

---

## Módulos del sistema

### Módulo A — Bienes Muebles
Registro y control de todos los activos del instituto. Cada bien se identifica con un código único, se asigna a un departamento y cuenta con historial completo de movimientos.

### Módulo B — Formularios oficiales BM
Generación automática de los cuatro formularios oficiales:

| Formulario | Código GOB | Descripción |
|---|---|---|
| BM-1 | GOB-900-FM-086/15 | Inventario general por unidad de trabajo |
| BM-2 | GOB-900-FM-085/15 | Relación de movimientos del período |
| BM-3 | GOB-900-FM-078/15 | Relación de bienes faltantes (Concepto 60) |
| BM-4 | GOB-900-FM-077/15 | Resumen mensual de la cuenta de bienes |

### Módulo C — Catálogos y administración
Gestión de departamentos, categorías, cuentas contables y usuarios del sistema.

### Módulo D — Auditoría
Registro automático de todas las acciones realizadas en el sistema con usuario, fecha, hora y datos modificados.

---

## Base de datos

El sistema usa PostgreSQL 15 con 8 tablas:

| Tabla | Descripción |
|---|---|
| `bien` | Tabla central de activos del instituto |
| `movimiento` | Historial de incorporaciones, bajas y faltantes |
| `formulario_bm` | Registro de formularios BM generados |
| `usuario` | Cuentas y perfiles de acceso |
| `departamento` | Unidades organizativas del instituto |
| `categoria` | Clasificación de bienes |
| `cuenta_contable` | Plan de cuentas 2-1-214-XX |
| `auditoria` | Log completo de acciones del sistema |

Para crear la base de datos manualmente:

```bash
psql -U postgres -f sql/schema.sql
```

---

## Desarrollo local

```bash
# 1. Clonar el repositorio
git clone https://github.com/TU_USUARIO/sigema.git
cd sigema

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear la base de datos local
psql -U postgres -f sql/schema.sql

# 5. Configurar conexión
cp config.example.ini config.ini
# Editar config.ini con los datos de tu BD local

# 6. Opcional: Insertar datos de prueba
psql -U postgres -d sigema -f dummy_data.sql

# 7. Ejecutar en modo desarrollo (como módulo para evitar errores de importación)
python -m src.main
```

---

## Documentación

La carpeta `docs/` contiene la documentación completa del proyecto:

| Documento | Descripción |
|---|---|
| `SIGEMA_Propuesta.docx` | Propuesta inicial del sistema |
| `SIGEMA_SRS.docx` | Especificación de Requerimientos (SRS v1.0) |
| `SIGEMA_Guia_Reunion.docx` | Acta de levantamiento de información |

---

## Estado del proyecto

| Fase | Descripción | Estado |
|---|---|---|
| 1 | Levantamiento de información y SRS | ✅ Completada |
| 2 | Diseño de base de datos y ERD | ✅ Completada |
| 3 | Desarrollo Módulo A — Bienes Muebles | ✅ Completada |
| 4 | Desarrollo formularios BM-1 al BM-4 | ⏳ Pendiente |
| 5 | Desarrollo Módulo C — Administración | ⏳ Pendiente |
| 6 | Migración de datos históricos | ⏳ Pendiente |
| 7 | Pruebas y empaquetado | ⏳ Pendiente |

---

## Equipo

Desarrollado para el **Instituto Autónomo Minas Bolívar**
División de Control de Bienes — Gobernación del estado Bolívar, Venezuela

---

## Licencia

Uso interno — Instituto Autónomo Minas Bolívar. Todos los derechos reservados.