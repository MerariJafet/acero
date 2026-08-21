#!/usr/bin/env bash
# El Auditor por cron: una pasada cada vez que se invoca, hasta que vence el
# plazo. Se auto-expira leyendo un archivo de deadline — una supervisión que
# corre para siempre deja de leerse y se vuelve ruido de fondo.
#
#   Instalar (8 h desde ahora, cada 15 min):
#     scripts/supervise_cron.sh --arm 8
#     (añade la línea de crontab y escribe el deadline)
#   Desactivar antes de tiempo:
#     scripts/supervise_cron.sh --disarm
set -uo pipefail

REPO="/home/merari-acero/Escritorio/Proyectos Vibe Coding/Proyecto Acero"
DEADLINE_FILE="$HOME/ACERO/supervision/.deadline"
LOG="$HOME/ACERO/supervision/cron.log"
CRON_TAG="# ACERO-SUPERVISOR"
CRON_LINE="*/15 * * * * \"$REPO/scripts/supervise_cron.sh\" >> \"$LOG\" 2>&1 $CRON_TAG"

mkdir -p "$(dirname "$DEADLINE_FILE")"

case "${1:-run}" in
  --arm)
    HOURS="${2:-8}"
    date -d "+${HOURS} hours" +%s > "$DEADLINE_FILE"
    # reemplaza cualquier entrada previa del auditor (idempotente)
    ( crontab -l 2>/dev/null | grep -v "$CRON_TAG"; echo "$CRON_LINE" ) | crontab -
    echo "auditor armado: cada 15 min hasta $(date -d "+${HOURS} hours" '+%F %T')"
    exit 0
    ;;
  --disarm)
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" | crontab -
    rm -f "$DEADLINE_FILE"
    echo "auditor desarmado"
    exit 0
    ;;
esac

# --- una pasada -------------------------------------------------------------
if [[ ! -f "$DEADLINE_FILE" ]]; then
  echo "$(date '+%F %T') sin deadline: el auditor no está armado"
  exit 0
fi
if [[ "$(date +%s)" -ge "$(cat "$DEADLINE_FILE")" ]]; then
  echo "$(date '+%F %T') plazo cumplido — el auditor se retira y limpia su cron"
  crontab -l 2>/dev/null | grep -v "$CRON_TAG" | crontab -
  rm -f "$DEADLINE_FILE"
  exit 0
fi

cd "$REPO" || exit 1
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null
# timeout de pared por debajo del intervalo: dos auditorías nunca se solapan
timeout 600 python -m acero.cli.main supervise --every-min 15
