<#
================================================================================
 SIGEMA - Instalacion del SERVIDOR (PostgreSQL 15 + base de datos sigema)
================================================================================

 Este script automatiza TODO lo necesario en la computadora que hara de
 SERVIDOR de SIGEMA en la red local:

   1. Descarga PostgreSQL 15 (instalador oficial de EDB).
   2. Lo instala en silencio (sin ventanas).
   3. Crea el usuario de base de datos 'sigema_user'.
   4. Crea la base de datos 'sigema' y ejecuta schema.sql.
   5. Configura PostgreSQL para aceptar conexiones de la red local (LAN).
   6. Abre el puerto 5432 en el Firewall de Windows.
   7. Muestra la IP del servidor para configurar las computadoras cliente.

 USO (clic derecho > "Ejecutar con PowerShell" como Administrador), o:

     powershell -ExecutionPolicy Bypass -File .\install_server.ps1

 Se puede personalizar la contrasena:

     .\install_server.ps1 -SigemaUserPassword "MiClaveSegura123"

================================================================================
#>

#Requires -RunAsAdministrator

[CmdletBinding()]
param(
    # Contrasena del superusuario 'postgres' (administrador de PostgreSQL).
    [string]$SuperPassword = "Postgres_SIGEMA_2026",

    # Contrasena del usuario de la aplicacion 'sigema_user'.
    # IMPORTANTE: esta misma clave va en el config.ini de cada cliente.
    [string]$SigemaUserPassword = "sigema_pass",

    # Puerto de PostgreSQL.
    [int]$Port = 5432,

    # Rango de la red local autorizado (CIDR). "auto" lo detecta solo.
    [string]$LanCidr = "auto",

    # URL del instalador de PostgreSQL 15 (EDB).
    [string]$InstallerUrl = "https://get.enterprisedb.com/postgresql/postgresql-15.8-1-windows-x64.exe",

    # Carpeta de instalacion de PostgreSQL.
    [string]$InstallDir = "C:\Program Files\PostgreSQL\15",

    # Nombre del servicio de Windows.
    [string]$ServiceName = "postgresql-15"
)

$ErrorActionPreference = "Stop"
$DataDir    = Join-Path $InstallDir "data"
$BinDir     = Join-Path $InstallDir "bin"
$Psql       = Join-Path $BinDir "psql.exe"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$SchemaFile = Join-Path $ScriptDir "schema.sql"

function Write-Paso  ($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Write-Ok    ($m) { Write-Host "    [OK] $m" -ForegroundColor Green }
function Write-Aviso ($m) { Write-Host "    [!]  $m" -ForegroundColor Yellow }

Write-Host "================================================================" -ForegroundColor White
Write-Host "  SIGEMA - Instalacion del Servidor (PostgreSQL 15)" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor White

# ---------------------------------------------------------------------------
# 0. Verificaciones previas
# ---------------------------------------------------------------------------
if (-not (Test-Path $SchemaFile)) {
    throw "No se encontro schema.sql junto a este script ($SchemaFile)."
}

# ---------------------------------------------------------------------------
# 1 y 2. Descargar e instalar PostgreSQL (si no esta instalado)
# ---------------------------------------------------------------------------
if (Test-Path $Psql) {
    Write-Aviso "PostgreSQL ya esta instalado en $InstallDir. Se omite la instalacion."
}
else {
    Write-Paso "Descargando el instalador de PostgreSQL 15..."
    $installer = Join-Path $env:TEMP "postgresql-15-setup.exe"
    if (-not (Test-Path $installer)) {
        # TLS 1.2 para descargas en Windows 10.
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $InstallerUrl -OutFile $installer -UseBasicParsing
    }
    Write-Ok "Instalador descargado: $installer"

    Write-Paso "Instalando PostgreSQL en silencio (esto puede tardar varios minutos)..."
    $argumentos = @(
        "--mode", "unattended",
        "--unattendedmodeui", "none",
        "--superpassword", $SuperPassword,
        "--servicename", $ServiceName,
        "--serverport", "$Port",
        "--prefix", $InstallDir,
        "--datadir", $DataDir,
        "--enable-components", "server,commandlinetools",
        "--disable-components", "pgAdmin,stackbuilder"
    )
    $proc = Start-Process -FilePath $installer -ArgumentList $argumentos -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "El instalador de PostgreSQL termino con codigo $($proc.ExitCode)."
    }
    Write-Ok "PostgreSQL 15 instalado."
}

# ---------------------------------------------------------------------------
# Asegurar que el servicio este corriendo
# ---------------------------------------------------------------------------
Write-Paso "Iniciando el servicio de PostgreSQL..."
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($null -eq $svc) {
    # Algunos instaladores usan el nombre 'postgresql-x64-15'.
    $svc = Get-Service | Where-Object { $_.Name -like "postgresql*15*" } | Select-Object -First 1
    if ($svc) { $ServiceName = $svc.Name }
}
if ($null -eq $svc) { throw "No se encontro el servicio de PostgreSQL." }
if ($svc.Status -ne "Running") { Start-Service -Name $ServiceName }
Start-Sleep -Seconds 3
Write-Ok "Servicio '$ServiceName' en ejecucion."

# ---------------------------------------------------------------------------
# 3 y 4. Crear usuario, base de datos y ejecutar el esquema
# ---------------------------------------------------------------------------
# Para autenticarnos como 'postgres' usamos PGPASSWORD por variable de entorno.
$env:PGPASSWORD = $SuperPassword

function Invoke-Psql {
    param([string]$Db = "postgres", [string]$Sql)
    & $Psql -h "localhost" -p $Port -U "postgres" -d $Db -v ON_ERROR_STOP=1 -c $Sql
    if ($LASTEXITCODE -ne 0) { throw "psql fallo ejecutando: $Sql" }
}

Write-Paso "Creando el usuario 'sigema_user'..."
$existeRol = (& $Psql -h "localhost" -p $Port -U "postgres" -tAc `
    "SELECT 1 FROM pg_roles WHERE rolname = 'sigema_user'")
if ($existeRol -match "1") {
    Write-Aviso "El usuario 'sigema_user' ya existe. Se actualiza su contrasena."
    Invoke-Psql -Sql "ALTER ROLE sigema_user WITH LOGIN PASSWORD '$SigemaUserPassword';"
}
else {
    Invoke-Psql -Sql "CREATE ROLE sigema_user WITH LOGIN PASSWORD '$SigemaUserPassword';"
}
Write-Ok "Usuario 'sigema_user' listo."

Write-Paso "Creando la base de datos 'sigema'..."
$existeDb = (& $Psql -h "localhost" -p $Port -U "postgres" -tAc `
    "SELECT 1 FROM pg_database WHERE datname = 'sigema'")
if ($existeDb -match "1") {
    Write-Aviso "La base de datos 'sigema' ya existe. Se omite su creacion."
}
else {
    Invoke-Psql -Sql "CREATE DATABASE sigema OWNER sigema_user ENCODING 'UTF8';"
    Write-Ok "Base de datos 'sigema' creada."
}

Write-Paso "Aplicando el esquema (schema.sql) y datos iniciales..."
# Se ejecuta como 'sigema_user' para que las tablas le pertenezcan.
$env:PGPASSWORD = $SigemaUserPassword
& $Psql -h "localhost" -p $Port -U "sigema_user" -d "sigema" -v ON_ERROR_STOP=1 -f $SchemaFile
if ($LASTEXITCODE -ne 0) { throw "Fallo la ejecucion de schema.sql." }
Write-Ok "Esquema aplicado. (Usuario inicial de la app: admin / admin)"

# ---------------------------------------------------------------------------
# 5. Configurar PostgreSQL para la red local
# ---------------------------------------------------------------------------
Write-Paso "Configurando PostgreSQL para aceptar conexiones de la LAN..."

# Detectar el CIDR de la red local si no se especifico.
$ipObj = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } | Select-Object -First 1

if ($LanCidr -eq "auto") {
    if ($ipObj) {
        $octetos = $ipObj.IPAddress.Split(".")
        $LanCidr = "$($octetos[0]).$($octetos[1]).$($octetos[2]).0/24"
    }
    else {
        $LanCidr = "192.168.0.0/16"
        Write-Aviso "No se pudo detectar la red; se usa $LanCidr."
    }
}

# postgresql.conf -> escuchar en todas las interfaces.
$pgConf = Join-Path $DataDir "postgresql.conf"
$conf = Get-Content $pgConf
if ($conf -notmatch "^\s*listen_addresses\s*=\s*'\*'") {
    $conf = $conf -replace "^\s*#?\s*listen_addresses\s*=.*", "listen_addresses = '*'"
    if ($conf -notmatch "listen_addresses\s*=\s*'\*'") {
        $conf += "listen_addresses = '*'"
    }
    Set-Content -Path $pgConf -Value $conf -Encoding ascii
    Write-Ok "postgresql.conf: listen_addresses = '*'"
}
else {
    Write-Aviso "postgresql.conf ya escucha en todas las interfaces."
}

# pg_hba.conf -> permitir la red local con autenticacion por contrasena.
$hbaConf = Join-Path $DataDir "pg_hba.conf"
$reglaHba = "host    all             all             $LanCidr            scram-sha-256"
$hba = Get-Content $hbaConf
if ($hba -notmatch [Regex]::Escape($LanCidr)) {
    Add-Content -Path $hbaConf -Value "`r`n# SIGEMA - acceso desde la red local`r`n$reglaHba`r`n" -Encoding ascii
    Write-Ok "pg_hba.conf: autorizada la red $LanCidr"
}
else {
    Write-Aviso "pg_hba.conf ya autoriza la red $LanCidr."
}

# Aplicar los cambios reiniciando el servicio.
Write-Paso "Reiniciando PostgreSQL para aplicar la configuracion de red..."
Restart-Service -Name $ServiceName
Start-Sleep -Seconds 3
Write-Ok "Servicio reiniciado."

# ---------------------------------------------------------------------------
# 6. Abrir el puerto en el Firewall de Windows
# ---------------------------------------------------------------------------
Write-Paso "Abriendo el puerto $Port en el Firewall de Windows..."
$reglaFw = "SIGEMA PostgreSQL ($Port)"
if (-not (Get-NetFirewallRule -DisplayName $reglaFw -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $reglaFw -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort $Port -Profile Any | Out-Null
    Write-Ok "Regla de firewall creada para el puerto $Port."
}
else {
    Write-Aviso "La regla de firewall para el puerto $Port ya existia."
}

# Limpiar la variable de entorno con la contrasena.
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue

# ---------------------------------------------------------------------------
# 7. Mostrar la informacion del servidor
# ---------------------------------------------------------------------------
Write-Host "`n================================================================" -ForegroundColor Green
Write-Host "  INSTALACION COMPLETADA" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Datos para configurar cada computadora CLIENTE:" -ForegroundColor White
Write-Host ""
$ips = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" }
foreach ($ip in $ips) {
    Write-Host ("    IP del servidor : {0}" -f $ip.IPAddress) -ForegroundColor Yellow
}
Write-Host ("    Puerto          : {0}" -f $Port) -ForegroundColor Yellow
Write-Host  "    Base de datos   : sigema"             -ForegroundColor Yellow
Write-Host  "    Usuario BD      : sigema_user"        -ForegroundColor Yellow
Write-Host ("    Contrasena BD   : {0}" -f $SigemaUserPassword) -ForegroundColor Yellow
Write-Host ""
Write-Host  "    Usuario inicial de la aplicacion: admin  /  admin" -ForegroundColor White
Write-Host  "    (cambie esta contrasena despues del primer ingreso)" -ForegroundColor White
Write-Host ""
Write-Host  "  Anote la IP del servidor: la necesitara en cada cliente." -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Green
