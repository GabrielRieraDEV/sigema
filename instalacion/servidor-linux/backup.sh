#!/usr/bin/env bash
# =============================================================================
# SIGEMA - Respaldo de la base de datos (servidor Linux con Docker)
#
# Genera un archivo .sql con todo el contenido de la base 'sigema' usando
# pg_dump DENTRO del contenedor (no requiere PostgreSQL instalado en el host).
#
# Uso:
#     ./backup.sh                 # guarda en ./backups
#     ./backup.sh /ruta/destino   # guarda en otra carpeta
#
# Para respaldos automaticos diarios, agreguelo a cron (ejemplo a las 23:00):
#     0 23 * * *  /ruta/a/instalacion/servidor-linux/backup.sh >> /var/log/sigema_backup.log 2>&1
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cargar usuario/base desde .env si existe.
if [ -f .env ]; then set -a; . ./.env; set +a; fi
USER_DB="${POSTGRES_USER:-sigema_user}"
NAME_DB="${POSTGRES_DB:-sigema}"

DEST="${1:-$SCRIPT_DIR/backups}"
mkdir -p "$DEST"

TS="$(date +%Y%m%d_%H%M%S)"
OUT="$DEST/sigema_backup_${TS}.sql"

if ! docker ps --format '{{.Names}}' | grep -qx "sigema_db"; then
    echo "ERROR: el contenedor 'sigema_db' no esta corriendo."
    echo "Levantelo con:  docker compose up -d"
    exit 1
fi

echo "Generando respaldo de la base '$NAME_DB'..."
docker exec -t sigema_db pg_dump -U "$USER_DB" -d "$NAME_DB" --encoding=UTF8 > "$OUT"

if [ -s "$OUT" ]; then
    echo "Respaldo creado correctamente:"
    echo "    $OUT  ($(du -h "$OUT" | cut -f1))"
else
    echo "ERROR: el respaldo quedo vacio."
    rm -f "$OUT"
    exit 1
fi
