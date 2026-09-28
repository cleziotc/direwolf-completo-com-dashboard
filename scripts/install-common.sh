#!/usr/bin/env bash
set -Eeuo pipefail

PLATFORM="${1:-ubuntu}"
PROJECT_REPO="${PROJECT_REPO:-https://github.com/cleziotc/direwolf-completo-com-dashboard.git}"
PROJECT_BRANCH="${PROJECT_BRANCH:-main}"
APRS_USER="${APRS_USER:-aprs}"
APRS_HOME="${APRS_HOME:-/home/${APRS_USER}}"
INSTALL_DIR="${APRS_DASHBOARD_DIR:-${APRS_HOME}/aprs-dashboard}"
CONFIG_PATH="${DIREWOLF_CONFIG:-${APRS_HOME}/direwolf.conf}"
ENV_DIR="${APRS_HOME}/.config"
ENV_FILE="${ENV_DIR}/aprs-dashboard.env"
DIREWOLF_SRC="${DIREWOLF_SRC:-/usr/local/src/direwolf}"
DIREWOLF_REF="${DIREWOLF_REF:-master}"
DIREWOLF_REPO="${DIREWOLF_REPO:-https://github.com/wb2osz/direwolf.git}"

log(){ printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die(){ echo "ERRO: $*" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }

need_root(){
  [[ "${EUID}" -eq 0 ]] || die "Execute o instalador com sudo ou como root."
}

ask(){
  local var="$1" prompt="$2" default="${3:-}" value=""
  value="${!var:-}"
  if [[ -n "$value" ]]; then
    printf -v "$var" '%s' "$value"
    return
  fi
  if [[ "${APRS_NONINTERACTIVE:-0}" == "1" ]]; then
    [[ -n "$default" ]] || die "Variável obrigatória não definida: $var"
    printf -v "$var" '%s' "$default"
    return
  fi
  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " value
    value="${value:-$default}"
  else
    read -r -p "$prompt: " value
  fi
  printf -v "$var" '%s' "$value"
}

ask_yes_no(){
  local var="$1" prompt="$2" default="${3:-N}" value=""
  value="${!var:-}"
  if [[ -z "$value" && "${APRS_NONINTERACTIVE:-0}" != "1" ]]; then
    read -r -p "$prompt [${default}/${default/N/S}]: " value
  fi
  value="${value:-$default}"
  case "${value,,}" in
    s|sim|y|yes|1|true) printf -v "$var" '%s' "1" ;;
    *) printf -v "$var" '%s' "0" ;;
  esac
}

validate_number(){
  python3 - "$1" <<'PY'
import sys
try:
    float(sys.argv[1])
except Exception:
    raise SystemExit(1)
PY
}

compute_passcode(){
  python3 - "$1" <<'PY'
import sys
call=sys.argv[1].split("-",1)[0].upper()
h=0x73e2
for i in range(0,len(call),2):
    h ^= ord(call[i]) << 8
    if i+1 < len(call):
        h ^= ord(call[i+1])
print(h & 0x7fff)
PY
}

install_packages(){
  log "Instalando dependências do sistema..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y \
    ca-certificates curl git gcc g++ make cmake pkg-config \
    libasound2-dev libudev-dev libavahi-client-dev libgpiod-dev gpiod \
    python3 python3-venv python3-pip alsa-utils sudo jq
}

create_user(){
  if ! id "$APRS_USER" >/dev/null 2>&1; then
    log "Criando usuário de serviço $APRS_USER..."
    useradd --create-home --shell /bin/bash "$APRS_USER"
  fi

  local groups=(audio dialout)
  getent group systemd-journal >/dev/null 2>&1 && groups+=(systemd-journal)
  getent group gpio >/dev/null 2>&1 && groups+=(gpio)
  usermod -aG "$(IFS=,; echo "${groups[*]}")" "$APRS_USER"
  install -d -o "$APRS_USER" -g "$APRS_USER" "$APRS_HOME" "$ENV_DIR"
}

install_direwolf(){
  log "Instalando/atualizando Direwolf a partir do projeto oficial..."
  install -d /usr/local/src

  if [[ -d "$DIREWOLF_SRC/.git" ]]; then
    git -C "$DIREWOLF_SRC" fetch --tags --prune origin
  else
    rm -rf "$DIREWOLF_SRC"
    git clone "$DIREWOLF_REPO" "$DIREWOLF_SRC"
  fi

  git -C "$DIREWOLF_SRC" checkout "$DIREWOLF_REF"
  if [[ "$DIREWOLF_REF" == "master" || "$DIREWOLF_REF" == "dev" ]]; then
    git -C "$DIREWOLF_SRC" pull --ff-only origin "$DIREWOLF_REF"
  fi

  rm -rf "$DIREWOLF_SRC/build"
  mkdir -p "$DIREWOLF_SRC/build"
  cd "$DIREWOLF_SRC/build"
  cmake ..

  local jobs
  jobs="$(nproc)"
  if [[ "$PLATFORM" == "raspberry" ]]; then
    local mem_kb
    mem_kb="$(awk '/MemTotal/{print $2}' /proc/meminfo)"
    if (( mem_kb < 900000 )); then jobs=1
    elif (( jobs > 2 )); then jobs=2
    fi
  elif (( jobs > 4 )); then
    jobs=4
  fi

  make -j"$jobs"
  make install
  ldconfig || true
  [[ -x /usr/local/bin/direwolf ]] || die "Direwolf não foi instalado em /usr/local/bin/direwolf."
  /usr/local/bin/direwolf -h 2>&1 | head -n 2 || true
}

install_dashboard(){
  log "Instalando dashboard em $INSTALL_DIR..."
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    if [[ -n "$(git -C "$INSTALL_DIR" status --porcelain)" ]]; then
      die "Há alterações locais em $INSTALL_DIR. Faça backup/commit antes de reinstalar."
    fi
    git -C "$INSTALL_DIR" fetch --prune origin "$PROJECT_BRANCH"
    git -C "$INSTALL_DIR" reset --hard "origin/$PROJECT_BRANCH"
  elif [[ -e "$INSTALL_DIR" ]]; then
    die "$INSTALL_DIR já existe e não é um clone Git."
  else
    git clone --branch "$PROJECT_BRANCH" "$PROJECT_REPO" "$INSTALL_DIR"
  fi

  python3 -m venv "$INSTALL_DIR/venv"
  "$INSTALL_DIR/venv/bin/pip" install --upgrade pip wheel
  "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

  mkdir -p "$INSTALL_DIR/static/vendor/leaflet"
  curl -fL --retry 3 -o "$INSTALL_DIR/static/vendor/leaflet/leaflet.js" \
    https://unpkg.com/leaflet@1.9.4/dist/leaflet.js
  curl -fL --retry 3 -o "$INSTALL_DIR/static/vendor/leaflet/leaflet.css" \
    https://unpkg.com/leaflet@1.9.4/dist/leaflet.css

  mkdir -p "$INSTALL_DIR/data"
  chmod +x "$INSTALL_DIR/scripts/"*.sh "$INSTALL_DIR/scripts/"*.py 2>/dev/null || true
  chown -R "$APRS_USER:$APRS_USER" "$INSTALL_DIR"
}

detect_audio(){
  local line sys_path p
  APRS_ALSA_CARD="${APRS_ALSA_CARD:-}"
  APRS_ALSA_DEVICE_INDEX="${APRS_ALSA_DEVICE_INDEX:-}"
  APRS_AUDIO_DEVICE="${APRS_AUDIO_DEVICE:-}"
  APRS_AUDIO_CARD_NAME="${APRS_AUDIO_CARD_NAME:-}"
  APRS_AUDIO_USB_VENDOR_ID="${APRS_AUDIO_USB_VENDOR_ID:-}"
  APRS_AUDIO_USB_PRODUCT_ID="${APRS_AUDIO_USB_PRODUCT_ID:-}"

  if [[ -z "$APRS_ALSA_CARD" ]]; then
    line="$(arecord -l 2>/dev/null | grep -m1 -E '^card [0-9]+:' || true)"
    if [[ -n "$line" ]]; then
      APRS_ALSA_CARD="$(sed -n 's/^card \([0-9][0-9]*\):.*/\1/p' <<<"$line")"
      APRS_ALSA_DEVICE_INDEX="$(sed -n 's/.*device \([0-9][0-9]*\):.*/\1/p' <<<"$line")"
    fi
  fi

  APRS_ALSA_CARD="${APRS_ALSA_CARD:-0}"
  APRS_ALSA_DEVICE_INDEX="${APRS_ALSA_DEVICE_INDEX:-0}"
  APRS_AUDIO_DEVICE="${APRS_AUDIO_DEVICE:-plughw:${APRS_ALSA_CARD},${APRS_ALSA_DEVICE_INDEX}}"
  APRS_AUDIO_CARD_NAME="${APRS_AUDIO_CARD_NAME:-$(sed -n "s/^ *${APRS_ALSA_CARD} \[\([^]]*\)\].*/\1/p" /proc/asound/cards 2>/dev/null | head -n1)}"

  sys_path="$(readlink -f "/sys/class/sound/card${APRS_ALSA_CARD}/device" 2>/dev/null || true)"
  p="$sys_path"
  while [[ -n "$p" && "$p" != "/" ]]; do
    if [[ -f "$p/idVendor" && -f "$p/idProduct" ]]; then
      APRS_AUDIO_USB_VENDOR_ID="${APRS_AUDIO_USB_VENDOR_ID:-$(cat "$p/idVendor")}"
      APRS_AUDIO_USB_PRODUCT_ID="${APRS_AUDIO_USB_PRODUCT_ID:-$(cat "$p/idProduct")}"
      break
    fi
    p="$(dirname "$p")"
  done

  log "Áudio detectado: $APRS_AUDIO_DEVICE  USB ${APRS_AUDIO_USB_VENDOR_ID:-?}:${APRS_AUDIO_USB_PRODUCT_ID:-?}"
}

detect_serial(){
  APRS_SERIAL_PORT="${APRS_SERIAL_PORT:-}"
  APRS_SERIAL_USB_VENDOR_ID="${APRS_SERIAL_USB_VENDOR_ID:-}"
  APRS_SERIAL_USB_PRODUCT_ID="${APRS_SERIAL_USB_PRODUCT_ID:-}"

  if [[ -z "$APRS_SERIAL_PORT" ]]; then
    if compgen -G '/dev/serial/by-id/*' >/dev/null; then
      APRS_SERIAL_PORT="$(compgen -G '/dev/serial/by-id/*' | head -n1)"
    elif compgen -G '/dev/ttyUSB*' >/dev/null; then
      APRS_SERIAL_PORT="$(compgen -G '/dev/ttyUSB*' | head -n1)"
    elif compgen -G '/dev/ttyACM*' >/dev/null; then
      APRS_SERIAL_PORT="$(compgen -G '/dev/ttyACM*' | head -n1)"
    fi
  fi

  if [[ -n "$APRS_SERIAL_PORT" && -e "$APRS_SERIAL_PORT" ]]; then
    local props
    props="$(udevadm info -q property -n "$APRS_SERIAL_PORT" 2>/dev/null || true)"
    APRS_SERIAL_USB_VENDOR_ID="${APRS_SERIAL_USB_VENDOR_ID:-$(awk -F= '$1=="ID_VENDOR_ID"{print $2}' <<<"$props")}"
    APRS_SERIAL_USB_PRODUCT_ID="${APRS_SERIAL_USB_PRODUCT_ID:-$(awk -F= '$1=="ID_MODEL_ID"{print $2}' <<<"$props")}"
    log "Serial detectada: $APRS_SERIAL_PORT  USB ${APRS_SERIAL_USB_VENDOR_ID:-?}:${APRS_SERIAL_USB_PRODUCT_ID:-?}"
  else
    log "Nenhuma interface serial detectada. RX/iGate somente recepção continua disponível."
  fi
}

detect_gpio(){
  APRS_PTT_MODE="gpiod"
  APRS_GPIO_LINE="${APRS_GPIO_LINE:-25}"
  APRS_GPIO_CHIP="${APRS_GPIO_CHIP:-}"
  APRS_GPIO_INVERT="${APRS_GPIO_INVERT:-0}"

  if [[ -z "$APRS_GPIO_CHIP" ]]; then
    local dev name label ngpio
    for dev in /dev/gpiochip*; do
      [[ -e "$dev" ]] || continue
      name="$(basename "$dev")"
      label="$(cat "/sys/class/gpio/$name/label" 2>/dev/null || true)"
      ngpio="$(cat "/sys/class/gpio/$name/ngpio" 2>/dev/null || echo 0)"
      if [[ "$label" == *pinctrl* ]] && [[ "$ngpio" =~ ^[0-9]+$ ]] && (( ngpio > APRS_GPIO_LINE )); then
        APRS_GPIO_CHIP="$dev"
        break
      fi
    done
  fi

  if [[ -z "$APRS_GPIO_CHIP" ]]; then
    APRS_GPIO_CHIP="/dev/gpiochip0"
  elif [[ "$APRS_GPIO_CHIP" != /dev/* ]]; then
    APRS_GPIO_CHIP="/dev/${APRS_GPIO_CHIP}"
  fi

  log "PTT Raspberry: GPIOD $APRS_GPIO_CHIP linha BCM/GPIO $APRS_GPIO_LINE"
}

collect_station_config(){
  local tz_default
  tz_default="$(timedatectl show -p Timezone --value 2>/dev/null || true)"
  tz_default="${tz_default:-UTC}"

  ask APRS_CALLSIGN "Indicativo APRS com SSID (ex.: PY1ABC-10)" "${APRS_CALLSIGN:-}"
  APRS_CALLSIGN="${APRS_CALLSIGN^^}"
  [[ "$APRS_CALLSIGN" =~ ^[A-Z0-9]{1,6}(-[0-9]{1,2})?$ ]] || die "Indicativo inválido: $APRS_CALLSIGN"

  ask APRS_LOCATION_LABEL "Cidade/descrição curta exibida no dashboard" "${APRS_LOCATION_LABEL:-Estação APRS}"
  ask APRS_TIMEZONE "Timezone IANA" "${APRS_TIMEZONE:-$tz_default}"
  ask APRS_LATITUDE "Latitude decimal (sul = negativa)" "${APRS_LATITUDE:-}"
  ask APRS_LONGITUDE "Longitude decimal (oeste = negativa)" "${APRS_LONGITUDE:-}"
  validate_number "$APRS_LATITUDE" || die "Latitude inválida."
  validate_number "$APRS_LONGITUDE" || die "Longitude inválida."

  ask APRS_ALTITUDE_M "Altitude da estação em metros" "${APRS_ALTITUDE_M:-0}"
  ask APRS_ANTENNA_HEIGHT_M "Altura da antena em metros" "${APRS_ANTENNA_HEIGHT_M:-10}"
  ask APRS_ANTENNA_GAIN_DBI "Ganho da antena em dBi" "${APRS_ANTENNA_GAIN_DBI:-0}"
  ask APRS_POWER_W "Potência do transmissor em watts" "${APRS_POWER_W:-5}"
  ask APRS_FILTER_RADIUS_KM "Raio do filtro APRS-IS em km" "${APRS_FILTER_RADIUS_KM:-100}"
  ask APRS_SERVER "Servidor APRS-IS" "${APRS_SERVER:-rotate.aprs.net}"
  ask APRS_SERVER_PORT "Porta APRS-IS" "${APRS_SERVER_PORT:-14580}"

  APRS_PASSCODE="${APRS_PASSCODE:-$(compute_passcode "$APRS_CALLSIGN")}"

  ask_yes_no APRS_ENABLE_TX "Ativar PTT, digipeater e IS→RF?" "${APRS_ENABLE_TX:-N}"

  if [[ "$APRS_ENABLE_TX" != "1" ]]; then
    APRS_PTT_MODE="none"
  elif [[ "$PLATFORM" == "raspberry" ]]; then
    APRS_PTT_MODE="gpiod"
    ask APRS_GPIO_CHIP "GPIO chip para o PTT" "${APRS_GPIO_CHIP:-/dev/gpiochip0}"
    [[ "$APRS_GPIO_CHIP" == /dev/* ]] || APRS_GPIO_CHIP="/dev/$APRS_GPIO_CHIP"
    ask APRS_GPIO_LINE "GPIO BCM/linha para o PTT" "${APRS_GPIO_LINE:-25}"
    [[ "$APRS_GPIO_LINE" =~ ^[0-9]+$ ]] || die "GPIO inválido: $APRS_GPIO_LINE"
    ask_yes_no APRS_GPIO_INVERT "Inverter a lógica do GPIO de PTT?" "${APRS_GPIO_INVERT:-N}"
    [[ -e "$APRS_GPIO_CHIP" ]] || log "AVISO: $APRS_GPIO_CHIP ainda não existe. Confirme com gpioinfo antes de transmitir."
  else
    APRS_PTT_MODE="serial"
    APRS_PTT_SIGNAL="${APRS_PTT_SIGNAL:-DTR}"
    if [[ -z "${APRS_SERIAL_PORT:-}" ]]; then
      die "TX foi habilitado, mas nenhuma serial/PTT foi detectada. Defina APRS_SERIAL_PORT e execute novamente."
    fi
  fi
}

write_environment(){
  log "Gravando configuração de runtime..."
  cat >"$ENV_FILE" <<EOF
APRS_CALLSIGN=$APRS_CALLSIGN
APRS_LOCATION_LABEL=$APRS_LOCATION_LABEL
APRS_TIMEZONE=$APRS_TIMEZONE
DIREWOLF_CONFIG=$CONFIG_PATH
APRS_DASHBOARD_DIR=$INSTALL_DIR
APRS_ALSA_CARD=$APRS_ALSA_CARD
APRS_ALSA_DEVICE_INDEX=$APRS_ALSA_DEVICE_INDEX
APRS_AUDIO_DEVICE=$APRS_AUDIO_DEVICE
APRS_AUDIO_CARD_NAME=$APRS_AUDIO_CARD_NAME
APRS_AUDIO_USB_VENDOR_ID=$APRS_AUDIO_USB_VENDOR_ID
APRS_AUDIO_USB_PRODUCT_ID=$APRS_AUDIO_USB_PRODUCT_ID
APRS_PTT_MODE=${APRS_PTT_MODE:-none}
APRS_GPIO_CHIP=${APRS_GPIO_CHIP:-}
APRS_GPIO_LINE=${APRS_GPIO_LINE:-}
APRS_GPIO_INVERT=${APRS_GPIO_INVERT:-0}
APRS_SERIAL_PORT=${APRS_SERIAL_PORT:-}
APRS_SERIAL_USB_VENDOR_ID=${APRS_SERIAL_USB_VENDOR_ID:-}
APRS_SERIAL_USB_PRODUCT_ID=${APRS_SERIAL_USB_PRODUCT_ID:-}
APRS_CONFIG_BACKUP_DIR=$INSTALL_DIR/data/config-backups
APRS_OFFLINE_MAP_DIR=$INSTALL_DIR/data/offline-maps
EOF
  chmod 0640 "$ENV_FILE"
  chown "$APRS_USER:$APRS_USER" "$ENV_FILE"
}

write_direwolf_config(){
  log "Gerando $CONFIG_PATH..."
  local comment
  comment="${APRS_LOCATION_LABEL//\"/'}"

  cat >"$CONFIG_PATH" <<EOF
# ============================================================
# Direwolf configuration generated by direwolf-completo-com-dashboard
# Configuração-base originalmente programada por Daniel, PP5BK.
# Projeto/dashboard e automação: Clézio da Cunha Costa, PP5CI.
# Ajuste os parâmetros à sua estação e às regras da sua região.
# ============================================================

MYCALL $APRS_CALLSIGN
IGLOGIN $APRS_CALLSIGN $APRS_PASSCODE
IGSERVER $APRS_SERVER:$APRS_SERVER_PORT
IGFILTER r/$APRS_LATITUDE/$APRS_LONGITUDE/$APRS_FILTER_RADIUS_KM

PBEACON SENDTO=IG SLOT=0:01 EVERY=30 SYMBOL=I# LAT=$APRS_LATITUDE LONG=$APRS_LONGITUDE ALT=$APRS_ALTITUDE_M POWER=$APRS_POWER_W HEIGHT=$APRS_ANTENNA_HEIGHT_M GAIN=$APRS_ANTENNA_GAIN_DBI COMMENT="$comment" COMPRESS=0

ADEVICE $APRS_AUDIO_DEVICE
ACHANNELS 1
ARATE 48000
FULLDUP OFF
CHANNEL 0
MODEM 1200
EOF

  if [[ "$APRS_ENABLE_TX" == "1" ]]; then
    if [[ "$PLATFORM" == "raspberry" ]]; then
      local gpio_line="$APRS_GPIO_LINE"
      [[ "${APRS_GPIO_INVERT:-0}" == "1" ]] && gpio_line="-$gpio_line"
      cat >>"$CONFIG_PATH" <<EOF
PTT GPIOD $APRS_GPIO_CHIP $gpio_line
EOF
    else
      cat >>"$CONFIG_PATH" <<EOF
PTT $APRS_SERIAL_PORT $APRS_PTT_SIGNAL
EOF
    fi

    cat >>"$CONFIG_PATH" <<EOF
OBEACON SENDTO=0 OBJNAME=iGate SLOT=0:10 EVERY=15 SYMBOL=I# LAT=$APRS_LATITUDE LONG=$APRS_LONGITUDE ALT=$APRS_ALTITUDE_M POWER=$APRS_POWER_W HEIGHT=$APRS_ANTENNA_HEIGHT_M GAIN=$APRS_ANTENNA_GAIN_DBI COMMENT="$comment" COMPRESS=0 VIA=RFONLY
DIGIPEAT 0 0 ^WIDE$ ^WIDE[1-2]-[1-2]$ TRACE
IGTXVIA 0 WIDE1-1
FILTER IG 0 1
DWAIT 10
SLOTTIME 10
#PERSIST 78
TXDELAY 99
TXTAIL 10
DEDUPE 20
IGTXLIMIT 20 80
EOF
  else
    cat >>"$CONFIG_PATH" <<'EOF'
# TX RF desabilitado pelo instalador.
# Habilite depois pela página Configuração ou edite o direwolf.conf conscientemente.
EOF
  fi

  cat >>"$CONFIG_PATH" <<EOF
DTMF
IGMSP 5
LOGDIR /var/log/direwolf/
EOF

  chmod 0640 "$CONFIG_PATH"
  chown "$APRS_USER:$APRS_USER" "$CONFIG_PATH"
  install -d -o "$APRS_USER" -g "$APRS_USER" /var/log/direwolf
}

install_systemd(){
  log "Instalando serviços systemd..."
  install -m 0644 "$INSTALL_DIR/systemd/direwolf.service" /etc/systemd/system/direwolf.service
  install -m 0644 "$INSTALL_DIR/systemd/aprs-dashboard.service" /etc/systemd/system/aprs-dashboard.service
  install -d /etc/systemd/system/direwolf.service.d
  install -m 0644 "$INSTALL_DIR/systemd/direwolf-recovery.conf" /etc/systemd/system/direwolf.service.d/recovery.conf
  install -m 0644 "$INSTALL_DIR/systemd/aprs-hardware-watchdog.service" /etc/systemd/system/aprs-hardware-watchdog.service

  local systemctl_bin
  systemctl_bin="$(command -v systemctl)"
  cat >/etc/sudoers.d/aprs-dashboard <<EOF
$APRS_USER ALL=(root) NOPASSWD: $systemctl_bin restart direwolf
EOF
  chmod 0440 /etc/sudoers.d/aprs-dashboard
  visudo -cf /etc/sudoers.d/aprs-dashboard >/dev/null

  ln -sfn "$INSTALL_DIR/scripts/aprs-update.sh" /usr/local/bin/aprs-update

  systemctl daemon-reload
  systemctl enable direwolf.service aprs-dashboard.service aprs-hardware-watchdog.service
  systemctl restart direwolf.service
  sleep 2
  systemctl restart aprs-dashboard.service
  systemctl restart aprs-hardware-watchdog.service
}

validate_install(){
  log "Validando instalação..."
  systemctl is-active --quiet direwolf.service || {
    systemctl --no-pager --full status direwolf.service || true
    die "Direwolf não ficou ativo."
  }
  systemctl is-active --quiet aprs-dashboard.service || {
    systemctl --no-pager --full status aprs-dashboard.service || true
    die "Dashboard não ficou ativo."
  }

  local ok=0
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 3 http://127.0.0.1:8088/api/status | \
       python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("station")' >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 1
  done
  [[ "$ok" == "1" ]] || die "A API do dashboard não respondeu corretamente."

  local ip
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  echo
  echo "============================================================"
  echo " Instalação concluída"
  echo " Indicativo : $APRS_CALLSIGN"
  echo " Dashboard  : http://${ip:-IP-DO-EQUIPAMENTO}:8088/"
  echo " Configuração: http://${ip:-IP-DO-EQUIPAMENTO}:8088/config"
  echo " Direwolf   : systemctl status direwolf"
  echo " Dashboard  : systemctl status aprs-dashboard"
  echo " Watchdog   : systemctl status aprs-hardware-watchdog"
  echo " Atualização: aprs-update"
  echo "============================================================"
}

main(){
  need_root

  if [[ "$PLATFORM" == "raspberry" ]]; then
    if [[ -r /proc/device-tree/model ]]; then
      grep -qi "raspberry" /proc/device-tree/model || log "AVISO: hardware não identificado como Raspberry Pi."
    fi
  fi

  install_packages
  create_user
  install_direwolf
  install_dashboard
  detect_audio
  if [[ "$PLATFORM" == "raspberry" ]]; then
    detect_gpio
  else
    detect_serial
  fi
  collect_station_config
  write_environment
  write_direwolf_config
  install_systemd
  validate_install
}

main "$@"
