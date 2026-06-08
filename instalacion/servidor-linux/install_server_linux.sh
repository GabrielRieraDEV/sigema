#!/usr/bin/env bash
# =============================================================================
# SIGEMA - Instalacion del SERVIDOR en Linux (PostgreSQL 15 con Docker)
#
# Este script deja la base de datos de SIGEMA corriendo en esta maquina Linux:
#   1. Verifica que Docker este instalado.
#   2. Prepara el archivo .env (contrasena de la base).
#   3. Levanta PostgreSQL 15 en un contenedor (datos persistentes).
#   4. Abre el puerto 5432 en el firewall si esta activo (ufw).
#   5. Muestra la IP del servidor para configurar las computadoras cliente.
#
# Uso:
#     chmod +x install_server_linux.sh
#     ./install_server_linux.sh
#
# Si Docker requiere permisos de administrador, ejecute con sudo:
#     sudo ./install_server_linux.sh
# =============================================================================

set -euo pipefail

# Carpeta donde esta este script (para que funcione desde cualquier ruta).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

c_cyan="\033[36m"; c_green="\033[32m"; c_yellow="\033[33m"; c_reset="\033[0m"
paso()  { echo -e "\n${c_cyan}==> $1${c_reset}"; }
ok()    { echo -e "    ${c_green}[OK] $1${c_reset}"; }
aviso() { echo -e "    ${c_yellow}[!]  $1${c_reset}"; }

echo "================================================================"
echo "  SIGEMA - Instalacion del Servidor en Linux (Docker)"
echo "================================================================"

# ---------------------------------------------------------------------------
# 1. Verificar Docker y Docker Compose
# ---------------------------------------------------------------------------
paso "Verificando Docker..."
if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker no esta instalado."
    echo "Instalelo con la guia oficial: https://docs.docker.com/engine/install/"
    echo "En Ubuntu/Debian rapido:   curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Detectar 'docker compose' (plugin nuevo) o 'docker-compose' (antiguo).
if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "ERROR: No se encontro 'docker compose' ni 'docker-compose'."
    echo "Instale el plugin de Compose de Docker."
    exit 1
fi
ok "Docker disponible ($COMPOSE)."

# ---------------------------------------------------------------------------
# 2. Preparar el archivo .env
# ---------------------------------------------------------------------------
paso "Preparando la configuracion (.env)..."
if [ ! -f .env ]; then
    cp .env.example .env
    # Generar una contrasena aleatoria segura por defecto.
    if command -v openssl >/dev/null 2>&1; then
        NUEVA_CLAVE="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)"
        sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${NUEVA_CLAVE}|" .env
        aviso "Se genero una contrasena automatica en .env."
    else
        aviso "Edite .env y cambie POSTGRES_PASSWORD antes de continuar."
    fi
    ok "Archivo .env creado."
else
    aviso "Ya existe .env; se usa el actual (no se modifica)."
fi

# Cargar variables para mostrarlas al final.
set -a; . ./.env; set +a
POSTGRES_USER="${POSTGRES_USER:-sigema_user}"
POSTGRES_DB="${POSTGRES_DB:-sigema}"

# ---------------------------------------------------------------------------
# 3. Levantar PostgreSQL
# ---------------------------------------------------------------------------
paso "Levantando PostgreSQL 15 en Docker..."
$COMPOSE up -d

paso "Esperando a que la base de datos este lista..."
for i in $(seq 1 30); do
    estado="$(docker inspect -f '{{.State.Health.Status}}' sigema_db 2>/dev/null || echo starting)"
    if [ "$estado" = "healthy" ]; then break; fi
    sleep 2
done
if [ "${estado:-}" = "healthy" ]; then
    ok "Base de datos lista y operativa."
else
    aviso "La base aun no reporta 'healthy'. Revise:  $COMPOSE logs db"
fi

# ---------------------------------------------------------------------------
# 4. Firewall (best-effort)
# ---------------------------------------------------------------------------
paso "Configurando el firewall (si aplica)..."
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -qi "Status: active"; then
    ufw allow 5432/tcp >/dev/null 2>&1 && ok "ufw: puerto 5432 abierto." || aviso "No se pudo modificar ufw (ejecute con sudo)."
elif command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
    firewall-cmd --permanent --add-port=5432/tcp >/dev/null 2>&1 && firewall-cmd --reload >/dev/null 2>&1 \
        && ok "firewalld: puerto 5432 abierto." || aviso "No se pudo modificar firewalld (ejecute con sudo)."
else
    aviso "No hay firewall activo conocido (ufw/firewalld) o no requiere cambios."
fi

# ---------------------------------------------------------------------------
# 5. Mostrar datos del servidor
# ---------------------------------------------------------------------------
echo ""
echo "================================================================"
echo -e "${c_green}  INSTALACION COMPLETADA${c_reset}"
echo "================================================================"
echo ""
echo "  Datos para configurar cada computadora CLIENTE (Windows):"
echo ""
IPS="$(hostname -I 2>/dev/null || ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1)"
for ip in $IPS; do
    echo -e "    IP del servidor : ${c_yellow}${ip}${c_reset}"
done
echo -e "    Puerto          : ${c_yellow}5432${c_reset}"
echo -e "    Base de datos   : ${c_yellow}${POSTGRES_DB}${c_reset}"
echo -e "    Usuario BD      : ${c_yellow}${POSTGRES_USER}${c_reset}"
echo -e "    Contrasena BD   : ${c_yellow}${POSTGRES_PASSWORD}${c_reset}"
echo ""
echo "    Usuario inicial de la aplicacion: admin  /  admin"
echo ""
echo "  Comandos utiles:"
echo "    Ver estado    : $COMPOSE ps"
echo "    Ver registros : $COMPOSE logs -f db"
echo "    Detener       : $COMPOSE down        (los datos se conservan)"
echo "    Respaldar     : ./backup.sh"
echo "================================================================"
