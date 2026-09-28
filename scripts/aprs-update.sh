#!/usr/bin/env bash

set -uo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
DEFAULT_REPO="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
REPO="${APRS_DASHBOARD_DIR:-$DEFAULT_REPO}"
REMOTE="origin"
BRANCH="main"
SERVICE="aprs-dashboard.service"
PYTHON="$REPO/venv/bin/python"
HEALTH_URL="http://127.0.0.1:8088/api/status"
OVERVIEW_URL="http://127.0.0.1:8088/api/overview"
AUDIO_URL="http://127.0.0.1:8088/api/audio"
CONFIG_URL="http://127.0.0.1:8088/api/station-config"
CONFIG_CAPS_URL="http://127.0.0.1:8088/api/station-config/capabilities"
CONFIG_PAGE_URL="http://127.0.0.1:8088/config"
OFFLINE_MAP_URL="http://127.0.0.1:8088/api/offline-map/status"
LEAFLET_JS_URL="http://127.0.0.1:8088/static/vendor/leaflet/leaflet.js"
JS_URL="http://127.0.0.1:8088/static/dashboard-v2.js"
ROOT_URL="http://127.0.0.1:8088/"
LOG_FILE="$REPO/update.log"

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log() {
    echo "[$(timestamp)] $*"
}

health_check() {
    local attempt

    for attempt in $(seq 1 15); do
        if curl -fsS --max-time 3 "$HEALTH_URL" 2>/dev/null | \
            "$PYTHON" -c '
import json
import sys

data = json.load(sys.stdin)

if not data.get("station"):
    raise SystemExit(1)
' >/dev/null 2>&1 \
        && curl -fsS --max-time 3 "$OVERVIEW_URL" 2>/dev/null | "$PYTHON" -c '
import json
import sys
data = json.load(sys.stdin)
system = data.get("system") or {}
tx = data.get("tx") or {}
if "cpu_percent" not in system or "ram_percent" not in system:
    raise SystemExit(1)
if "igate_mode" not in tx or "digipeater" not in tx:
    raise SystemExit(1)
' >/dev/null 2>&1 \
        && curl -fsS --max-time 3 "$AUDIO_URL" >/dev/null 2>&1 \
        && curl -fsS --max-time 3 "$CONFIG_URL" >/dev/null 2>&1 \
        && curl -fsS --max-time 3 "$CONFIG_CAPS_URL" >/dev/null 2>&1 \
        && curl -fsS --max-time 3 "$CONFIG_PAGE_URL" 2>/dev/null | grep -q "Mapa offline da estação" \
        && curl -fsS --max-time 3 "$OFFLINE_MAP_URL" >/dev/null 2>&1 \
        && curl -fsS --max-time 3 "$JS_URL" >/dev/null 2>&1 \
        && curl -fsS --max-time 3 "$ROOT_URL" 2>/dev/null | grep -q "APRS Monitor"; then
            return 0
        fi

        sleep 1
    done

    return 1
}

ensure_leaflet_assets() {
    mkdir -p static/vendor/leaflet

    if [[ ! -s static/vendor/leaflet/leaflet.js ]]; then
        log "Baixando leaflet.js local..."
        curl -fL --retry 3 --connect-timeout 10 --max-time 60 \
            -o static/vendor/leaflet/leaflet.js \
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" || return 1
    fi

    if [[ ! -s static/vendor/leaflet/leaflet.css ]]; then
        log "Baixando leaflet.css local..."
        curl -fL --retry 3 --connect-timeout 10 --max-time 60 \
            -o static/vendor/leaflet/leaflet.css \
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" || return 1
    fi

    return 0
}

rollback() {
    local reason="$1"

    log "ERRO: $reason"
    log "Iniciando rollback para $OLD_COMMIT..."

    if ! git reset --hard "$OLD_COMMIT"; then
        log "FALHA CRITICA: nao foi possivel restaurar o commit anterior."
        exit 2
    fi

    if ! sudo systemctl restart "$SERVICE"; then
        log "FALHA CRITICA: arquivos restaurados, mas o servico nao reiniciou."
        exit 3
    fi

    if health_check; then
        log "Rollback concluido. Dashboard restaurado em $OLD_COMMIT."
    else
        log "FALHA CRITICA: rollback aplicado, mas a API nao respondeu."
        exit 4
    fi

    exit 1
}

if [[ "${EUID}" -eq 0 ]]; then
    echo "Execute este comando como o usuario de servico APRS, sem sudo."
    exit 1
fi

cd "$REPO" || exit 1

touch "$LOG_FILE" 2>/dev/null || true
exec > >(tee -a "$LOG_FILE") 2>&1

log "===== APRS Dashboard Update ====="

if [[ ! -x "$PYTHON" ]]; then
    log "ERRO: Python do venv nao encontrado em $PYTHON."
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    log "ERRO: existem alteracoes locais nao commitadas."
    git status --short
    log "Atualizacao cancelada para evitar perda de arquivos."
    exit 1
fi

OLD_COMMIT="$(git rev-parse HEAD)"

log "Versao atual: $OLD_COMMIT"
log "Buscando atualizacoes em $REMOTE/$BRANCH..."

if ! git fetch --prune "$REMOTE" "$BRANCH"; then
    log "ERRO: falha ao acessar o GitHub. Nada foi alterado."
    exit 1
fi

TARGET_COMMIT="$(git rev-parse "$REMOTE/$BRANCH")"

if [[ "$TARGET_COMMIT" == "$OLD_COMMIT" ]]; then
    log "Nenhuma atualizacao disponivel."
    if ! ensure_leaflet_assets; then
        log "AVISO: nao foi possivel preparar Leaflet local. O dashboard usara o fallback online."
    fi
    exit 0
fi

log "Nova versao: $TARGET_COMMIT"
log "Aplicando arquivos..."

if ! git reset --hard "$TARGET_COMMIT"; then
    rollback "falha ao aplicar o novo commit"
fi

log "Preparando Leaflet local para operacao sem internet..."

if ! ensure_leaflet_assets; then
    log "AVISO: nao foi possivel preparar Leaflet local. O dashboard usara o fallback online."
fi

log "Validando Python..."

if ! "$PYTHON" -m py_compile app.py database.py dashboard_extensions.py audio_control.py station_config.py offline_maps.py scripts/direwolf-hardware-watchdog.py; then
    rollback "erro de sintaxe Python"
fi

if ! "$PYTHON" -c 'import app, database, dashboard_extensions, audio_control, station_config, offline_maps' >/dev/null 2>&1; then
    rollback "erro ao importar modulos Python"
fi

if [[ ! -s static/index.html ]]; then
    rollback "static/index.html ausente ou vazio"
fi

log "Validacoes de arquivos OK."
log "Reiniciando $SERVICE..."

if ! sudo systemctl restart "$SERVICE"; then
    rollback "systemd nao conseguiu reiniciar o dashboard"
fi

if ! systemctl is-active --quiet "$SERVICE"; then
    rollback "servico ficou inativo apos o restart"
fi

log "Testando API..."

if ! health_check; then
    rollback "API /api/status nao respondeu corretamente"
fi

if systemctl cat aprs-hardware-watchdog.service >/dev/null 2>&1; then
    if ! sudo systemctl restart aprs-hardware-watchdog.service; then
        log "ERRO: dashboard atualizado, mas o watchdog de hardware nao reiniciou."
        exit 1
    fi

    if ! systemctl is-active --quiet aprs-hardware-watchdog.service; then
        log "ERRO: dashboard atualizado, mas o watchdog de hardware ficou inativo."
        exit 1
    fi

    log "Watchdog de hardware reiniciado e ativo."
else
    log "AVISO: aprs-hardware-watchdog.service nao esta instalado; execute novamente o instalador para instalar os servicos atuais."
fi

NEW_COMMIT="$(git rev-parse --short HEAD)"
OLD_SHORT="$(git rev-parse --short "$OLD_COMMIT")"

log "SUCESSO: dashboard atualizado de $OLD_SHORT para $NEW_COMMIT."
log "API operacional: $HEALTH_URL"
log "================================="
