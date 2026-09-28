import asyncio
import json
import os
import re
import subprocess

from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

import aprslib

from fastapi import FastAPI
from fastapi.responses import FileResponse

from database import (
    init_db,
    insert_event,
    get_stats,
    get_recent_events,
    get_hourly_activity,
    get_map_positions,
    get_last_event_time,
    insert_event_if_missing,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# ============================================================
# HARDWARE DO IGATE
# ============================================================

DIREWOLF_CONFIG_PATH = Path(os.environ.get("DIREWOLF_CONFIG", "/home/aprs/direwolf.conf"))

STATION_CALLSIGN = os.environ.get("APRS_CALLSIGN", "").strip().upper()
if not STATION_CALLSIGN:
    try:
        for _line in DIREWOLF_CONFIG_PATH.read_text(errors="replace").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and _line.upper().startswith("MYCALL "):
                STATION_CALLSIGN = _line.split()[1].upper()
                break
    except OSError:
        pass
if not STATION_CALLSIGN:
    STATION_CALLSIGN = "N0CALL-10"

STATION_LOCATION_LABEL = os.environ.get("APRS_LOCATION_LABEL", "Estação APRS").strip()
APP_TIMEZONE = os.environ.get("APRS_TIMEZONE", "UTC").strip() or "UTC"

AUDIO_USB_VENDOR_ID = os.environ.get("APRS_AUDIO_USB_VENDOR_ID", "").strip().lower()
AUDIO_USB_PRODUCT_ID = os.environ.get("APRS_AUDIO_USB_PRODUCT_ID", "").strip().lower()
AUDIO_ALSA_DEVICE = os.environ.get("APRS_AUDIO_DEVICE", "plughw:0,0").strip()
AUDIO_ALSA_CARD_NAME = os.environ.get("APRS_AUDIO_CARD_NAME", "").strip()

try:
    AUDIO_ALSA_CARD = int(os.environ.get("APRS_ALSA_CARD", "0"))
except ValueError:
    AUDIO_ALSA_CARD = 0

try:
    AUDIO_ALSA_DEVICE_INDEX = int(os.environ.get("APRS_ALSA_DEVICE_INDEX", "0"))
except ValueError:
    AUDIO_ALSA_DEVICE_INDEX = 0

AUDIO_CAPTURE_PATH = Path(f"/proc/asound/card{AUDIO_ALSA_CARD}/pcm{AUDIO_ALSA_DEVICE_INDEX}c")

SERIAL_USB_VENDOR_ID = os.environ.get("APRS_SERIAL_USB_VENDOR_ID", "").strip().lower()
SERIAL_USB_PRODUCT_ID = os.environ.get("APRS_SERIAL_USB_PRODUCT_ID", "").strip().lower()
SERIAL_PTT_PORT_TEXT = os.environ.get("APRS_SERIAL_PORT", "").strip()
SERIAL_PTT_PORT = Path(SERIAL_PTT_PORT_TEXT) if SERIAL_PTT_PORT_TEXT else None

PTT_MODE = os.environ.get("APRS_PTT_MODE", "").strip().lower()
GPIO_PTT_CHIP = os.environ.get("APRS_GPIO_CHIP", "").strip()
GPIO_PTT_LINE = os.environ.get("APRS_GPIO_LINE", "").strip()
GPIO_PTT_INVERT = os.environ.get("APRS_GPIO_INVERT", "0").strip().lower() in ("1", "true", "yes", "sim")

if not PTT_MODE:
    try:
        for _line in DIREWOLF_CONFIG_PATH.read_text(errors="replace").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or not _line.upper().startswith("PTT "):
                continue
            _parts = _line.split()
            if len(_parts) >= 4 and _parts[1].upper() == "GPIOD":
                PTT_MODE = "gpiod"
                GPIO_PTT_CHIP = GPIO_PTT_CHIP or _parts[2]
                GPIO_PTT_LINE = GPIO_PTT_LINE or _parts[3].lstrip("-")
                GPIO_PTT_INVERT = GPIO_PTT_INVERT or _parts[3].startswith("-")
            elif len(_parts) >= 3:
                PTT_MODE = "serial"
                SERIAL_PTT_PORT_TEXT = SERIAL_PTT_PORT_TEXT or _parts[1]
                SERIAL_PTT_PORT = Path(SERIAL_PTT_PORT_TEXT)
            break
    except OSError:
        pass

if not PTT_MODE:
    PTT_MODE = "none"

if GPIO_PTT_CHIP and not GPIO_PTT_CHIP.startswith("/"):
    GPIO_PTT_CHIP = "/dev/" + GPIO_PTT_CHIP

USB_SYSFS_ROOT = Path("/sys/bus/usb/devices")

raw_events = deque(maxlen=500)
events = deque(maxlen=500)


runtime_state = {
    "aprs_is_verified": False,
    "aprs_is_server": None,
    "last_verified": None,
}


# ============================================================
# FUNCOES AUXILIARES
# ============================================================

def now_iso():

    return datetime.now(
        timezone.utc
    ).isoformat()


def extract_callsign(packet: str):

    match = re.match(
        r"^([A-Za-z0-9-]+)>",
        packet
    )

    if match:
        return match.group(1).upper()

    return None


def restore_control_characters(packet: str):

    """
    O Direwolf mostra alguns caracteres de controle assim:

        <0x1c>
        <0x0d>
        <0x1d>

    Pacotes Mic-E podem conter esses bytes.
    Para o aprslib reconstruimos o caractere original.
    """

    def replace_hex(match):

        try:

            return chr(
                int(
                    match.group(1),
                    16
                )
            )

        except Exception:

            return match.group(0)


    return re.sub(
        r"<0x([0-9A-Fa-f]{2})>",
        replace_hex,
        packet
    )


# ============================================================
# DECODIFICACAO APRS
# ============================================================

def enrich_aprs_event(event):

    """
    Decodifica um pacote APRS usando aprslib.

    Campos gerais:

        latitude
        longitude
        aprs_format
        symbol
        symbol_table
        comment
        altitude
        mic_e_status

    Estacoes moveis:

        speed
        course

    Estacoes meteorologicas:

        is_weather = True

        weather = {
            temperature
            humidity
            pressure
            wind_direction
            wind_speed
            wind_gust
            rain_1h
            rain_24h
            rain_since_midnight
        }

    No aprslib 0.7.2, para pacotes WX como os do WeeWX,
    direcao e velocidade do vento aparecem nos campos:

        course
        speed

    Nesses casos:

        course -> wind_direction
        speed km/h -> wind_speed m/s
    """

    packet = event.get(
        "packet"
    )


    if not packet:

        return event


    try:

        decoded_packet = (
            restore_control_characters(
                packet
            )
        )


        parsed = aprslib.parse(
            decoded_packet
        )


        # ====================================================
        # POSICAO
        # ====================================================

        latitude = parsed.get(
            "latitude"
        )

        longitude = parsed.get(
            "longitude"
        )


        if latitude is not None:

            event["latitude"] = float(
                latitude
            )


        if longitude is not None:

            event["longitude"] = float(
                longitude
            )


        # ====================================================
        # FORMATO
        # ====================================================

        aprs_format = parsed.get(
            "format"
        )


        if aprs_format is not None:

            event["aprs_format"] = (
                aprs_format
            )


        # ====================================================
        # SIMBOLO APRS
        # ====================================================

        symbol = parsed.get(
            "symbol"
        )


        if symbol is not None:

            event["symbol"] = (
                symbol
            )


        symbol_table = parsed.get(
            "symbol_table"
        )


        if symbol_table is not None:

            event["symbol_table"] = (
                symbol_table
            )


        # ====================================================
        # COMENTARIO
        # ====================================================

        comment = parsed.get(
            "comment"
        )


        if comment is not None:

            event["comment"] = (
                comment
            )


        # ====================================================
        # ALTITUDE
        # ====================================================

        altitude = parsed.get(
            "altitude"
        )


        if altitude is not None:

            event["altitude"] = (
                altitude
            )


        # ====================================================
        # MIC-E
        # ====================================================

        mtype = parsed.get(
            "mtype"
        )


        if mtype is not None:

            event["mic_e_status"] = (
                mtype
            )


        # ====================================================
        # TIMESTAMP APRS
        # ====================================================

        timestamp = parsed.get(
            "timestamp"
        )


        if timestamp is not None:

            event["aprs_timestamp"] = (
                timestamp
            )


        raw_timestamp = parsed.get(
            "raw_timestamp"
        )


        if raw_timestamp is not None:

            event["raw_timestamp"] = (
                raw_timestamp
            )


        # ====================================================
        # WEATHER
        # ====================================================

        weather = parsed.get(
            "weather"
        )


        if isinstance(
            weather,
            dict
        ):

            clean_weather = {}


            # ------------------------------------------------
            # CAMPOS QUE O APRSLIB JA ENTREGA DENTRO
            # DE weather
            # ------------------------------------------------

            weather_fields = [

                "temperature",

                "humidity",

                "pressure",

                "wind_direction",

                "wind_speed",

                "wind_gust",

                "rain_1h",

                "rain_24h",

                "rain_since_midnight",

            ]


            for field in weather_fields:

                value = weather.get(
                    field
                )


                if value is not None:

                    clean_weather[
                        field
                    ] = value


            # ------------------------------------------------
            # APRSLIB 0.7.2
            #
            # Exemplo de estação meteorológica:
            #
            # course = 269
            # speed  = 7.408 km/h
            #
            # Como existe weather, esses valores representam
            # vento e NAO deslocamento da estacao.
            # ------------------------------------------------

            course = parsed.get(
                "course"
            )


            if (
                course is not None
                and
                "wind_direction"
                not in clean_weather
            ):

                clean_weather[
                    "wind_direction"
                ] = float(
                    course
                )


            speed = parsed.get(
                "speed"
            )


            if (
                speed is not None
                and
                "wind_speed"
                not in clean_weather
            ):

                clean_weather[
                    "wind_speed"
                ] = (
                    float(speed)
                    / 3.6
                )


            # ------------------------------------------------
            # MARCA O EVENTO COMO METEOROLOGICO
            # ------------------------------------------------

            event["is_weather"] = (
                True
            )


            event["weather"] = (
                clean_weather
            )


        # ====================================================
        # MOVIMENTO NORMAL
        #
        # Somente quando NAO e pacote meteorologico.
        # ====================================================

        else:

            speed = parsed.get(
                "speed"
            )


            if speed is not None:

                event["speed"] = (
                    speed
                )


            course = parsed.get(
                "course"
            )


            if course is not None:

                event["course"] = (
                    course
                )


    except Exception:

        # Pacotes incompletos ou formatos que o aprslib
        # nao consegue interpretar nao podem interromper
        # o coletor.

        pass


    return event


# ============================================================
# HARDWARE
# ============================================================

def usb_device_present(
    vendor_id: str,
    product_id: str
):

    """
    Verifica diretamente no sysfs se um dispositivo USB
    com o VID:PID informado esta enumerado dentro da VM.

    Esta verificacao nao depende da numeracao Bus/Device do lsusb,
    que pode mudar a cada reconexao.
    """

    vendor_id = (
        vendor_id
        .strip()
        .lower()
    )

    product_id = (
        product_id
        .strip()
        .lower()
    )

    try:

        for device in USB_SYSFS_ROOT.iterdir():

            vendor_file = (
                device /
                "idVendor"
            )

            product_file = (
                device /
                "idProduct"
            )

            if (
                not vendor_file.exists()
                or
                not product_file.exists()
            ):

                continue

            try:

                current_vendor = (
                    vendor_file
                    .read_text()
                    .strip()
                    .lower()
                )

                current_product = (
                    product_file
                    .read_text()
                    .strip()
                    .lower()
                )

            except OSError:

                continue

            if (
                current_vendor == vendor_id
                and
                current_product == product_id
            ):

                return True

    except OSError:

        return False

    return False


def alsa_capture_present():

    """
    Confirma que a placa USB foi registrada pelo ALSA
    e que o dispositivo de captura card 0 / device 0 existe.
    """

    cards_file = Path(
        "/proc/asound/cards"
    )

    if not cards_file.exists():

        return False

    if not AUDIO_CAPTURE_PATH.exists():

        return False

    try:

        cards_text = (
            cards_file
            .read_text(
                errors="replace"
            )
        )

    except OSError:

        return False

    return (
        AUDIO_ALSA_CARD_NAME
        in cards_text
    )


def get_current_ptt_config():

    fallback = {
        "mode":
            PTT_MODE,

        "serial_port":
            SERIAL_PTT_PORT_TEXT,

        "gpio_chip":
            GPIO_PTT_CHIP,

        "gpio_line":
            GPIO_PTT_LINE,

        "invert":
            GPIO_PTT_INVERT,
    }

    try:

        lines = DIREWOLF_CONFIG_PATH.read_text(
            errors="replace"
        ).splitlines()

    except OSError:

        return fallback

    for raw in lines:

        line = raw.strip()

        if (
            not line
            or line.startswith("#")
            or not line.upper().startswith(
                "PTT "
            )
        ):

            continue

        parts = line.split()

        if (
            len(parts) >= 4
            and parts[1].upper()
            == "GPIOD"
        ):

            chip = parts[2]

            if (
                chip
                and not chip.startswith(
                    "/"
                )
            ):

                chip = (
                    "/dev/"
                    + chip
                )

            raw_line = parts[3]

            return {
                "mode":
                    "gpiod",

                "serial_port":
                    "",

                "gpio_chip":
                    chip,

                "gpio_line":
                    raw_line.lstrip(
                        "-"
                    ),

                "invert":
                    raw_line.startswith(
                        "-"
                    ),
            }

        if len(parts) >= 3:

            return {
                "mode":
                    "serial",

                "serial_port":
                    parts[1],

                "gpio_chip":
                    "",

                "gpio_line":
                    "",

                "invert":
                    parts[2].startswith(
                        "-"
                    ),
            }

    return {
        "mode":
            "none",

        "serial_port":
            "",

        "gpio_chip":
            "",

        "gpio_line":
            "",

        "invert":
            False,
    }


def get_hardware_status():

    ptt_config = (
        get_current_ptt_config()
    )

    ptt_mode = ptt_config.get(
        "mode",
        "none"
    )

    serial_port_text = ptt_config.get(
        "serial_port",
        ""
    )

    serial_port = (
        Path(
            serial_port_text
        )
        if serial_port_text
        else None
    )

    gpio_chip = ptt_config.get(
        "gpio_chip",
        ""
    )

    gpio_line = str(
        ptt_config.get(
            "gpio_line",
            ""
        )
        or ""
    )

    audio_usb_present = (
        usb_device_present(
            AUDIO_USB_VENDOR_ID,
            AUDIO_USB_PRODUCT_ID
        )
        if (
            AUDIO_USB_VENDOR_ID
            and AUDIO_USB_PRODUCT_ID
        )
        else True
    )

    audio_capture_present = (
        alsa_capture_present()
    )

    serial_usb_present = False
    serial_port_present = False
    gpio_chip_present = False
    ptt_online = False
    ptt_device = ""
    ptt_label = "PTT"

    if ptt_mode == "serial":

        serial_usb_present = (
            usb_device_present(
                SERIAL_USB_VENDOR_ID,
                SERIAL_USB_PRODUCT_ID
            )
            if (
                SERIAL_USB_VENDOR_ID
                and SERIAL_USB_PRODUCT_ID
            )
            else bool(
                serial_port
                and serial_port.exists()
            )
        )

        serial_port_present = bool(
            serial_port
            and serial_port.exists()
        )

        ptt_online = (
            serial_usb_present
            and serial_port_present
        )

        ptt_device = (
            serial_port_text
            or "serial não definida"
        )

        ptt_label = "SERIAL / PTT"

    elif ptt_mode == "gpiod":

        gpio_chip_present = bool(
            gpio_chip
            and Path(
                gpio_chip
            ).exists()
        )

        ptt_online = (
            gpio_chip_present
            and gpio_line.isdigit()
        )

        ptt_device = (
            f"{gpio_chip or 'gpiochip'}"
            f" • GPIO {gpio_line or '?'}"
        )

        ptt_label = "GPIO / PTT"

    return {

        "audio_usb_present":
            audio_usb_present,

        "audio_capture_present":
            audio_capture_present,

        "audio_online":
            (
                audio_usb_present
                and
                audio_capture_present
            ),

        "audio_usb_id":
            (
                f"{AUDIO_USB_VENDOR_ID}:"
                f"{AUDIO_USB_PRODUCT_ID}"
                if (
                    AUDIO_USB_VENDOR_ID
                    and AUDIO_USB_PRODUCT_ID
                )
                else "ALSA"
            ),

        "audio_device":
            AUDIO_ALSA_DEVICE,

        "ptt_mode":
            ptt_mode,

        "ptt_configured":
            ptt_mode in (
                "serial",
                "gpiod",
            ),

        "ptt_online":
            ptt_online,

        "ptt_label":
            ptt_label,

        "ptt_device":
            ptt_device,

        "gpio_chip_present":
            gpio_chip_present,

        "gpio_chip":
            gpio_chip,

        "gpio_line":
            gpio_line,

        # Campos legados mantidos para compatibilidade.
        "serial_usb_present":
            serial_usb_present,

        "serial_port_present":
            serial_port_present,

        "serial_ptt_online":
            ptt_online,

        "serial_usb_id":
            (
                f"{SERIAL_USB_VENDOR_ID}:"
                f"{SERIAL_USB_PRODUCT_ID}"
                if (
                    SERIAL_USB_VENDOR_ID
                    and SERIAL_USB_PRODUCT_ID
                )
                else ""
            ),

        "serial_port":
            serial_port_text,
    }


# ============================================================
# DIREWOLF
# ============================================================

def direwolf_service_active():

    try:

        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "--quiet",
                "direwolf"
            ],
            timeout=2
        )

        return (
            result.returncode == 0
        )

    except Exception:

        return False


# ============================================================
# ESTADO APRS-IS
# ============================================================

def update_runtime_state(line: str):

    if (
        "Now connected to IGate server"
        in line
    ):

        runtime_state[
            "aprs_is_verified"
        ] = False


        match = re.search(
            r"IGate server\s+([^\s]+)",
            line
        )


        if match:

            runtime_state[
                "aprs_is_server"
            ] = match.group(1)


    if re.search(
        r"\blogresp\s+\S+\s+verified\b",
        line,
        re.IGNORECASE
    ):

        runtime_state[
            "aprs_is_verified"
        ] = True


        runtime_state[
            "last_verified"
        ] = now_iso()


    lower = line.lower()


    if (
        "igate server" in lower
        and (
            "disconnect" in lower
            or "connection lost" in lower
            or "failed" in lower
            or "closed" in lower
        )
    ):

        runtime_state[
            "aprs_is_verified"
        ] = False


# ============================================================
# ESTADO DO DIREWOLF AO INICIAR
# ============================================================

def bootstrap_runtime_state():

    if not direwolf_service_active():

        return


    try:

        start_result = subprocess.run(
            [
                "systemctl",
                "show",
                "direwolf",
                "--property=ActiveEnterTimestamp",
                "--value"
            ],
            capture_output=True,
            text=True,
            timeout=2
        )


        service_start = (
            start_result.stdout.strip()
        )


        if not service_start:

            return


        journal_result = subprocess.run(
            [
                "journalctl",
                "-u",
                "direwolf",
                "--since",
                service_start,
                "-o",
                "cat",
                "--no-pager"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )


        for line in (
            journal_result.stdout.splitlines()
        ):

            update_runtime_state(
                line
            )


    except Exception:

        pass


# ============================================================
# INTERPRETACAO DO JOURNAL
# ============================================================

def parse_direwolf_line(line: str):

    event = {

        "time":
            now_iso(),

        "type":
            "OTHER",

        "callsign":
            None,

        "raw":
            line,

    }


    # --------------------------------------------------------
    # NIVEL DE AUDIO
    # --------------------------------------------------------

    match = re.match(
        r"^([A-Za-z0-9-]+) audio level = ([0-9]+)\(([^)]*)\)",
        line,
    )


    if match:

        event["type"] = (
            "AUDIO_LEVEL"
        )


        event["callsign"] = (
            match.group(1).upper()
        )


        event["level"] = int(
            match.group(2)
        )


        event["detail"] = (
            match.group(3)
        )


        return event


    # --------------------------------------------------------
    # PACOTE TRANSMITIDO POR RF
    # --------------------------------------------------------

    match = re.match(
        r"^\[([0-9]+)L(?:\s+([^\]]+))?\]\s+(.+)$",
        line,
    )

    if match:

        packet = (
            match.group(3)
        )

        event["type"] = (
            "TX_RF"
        )

        event["decoder"] = (
            match.group(1)
        )

        event["direwolf_time"] = (
            match.group(2)
        )

        event["packet"] = (
            packet
        )

        event["callsign"] = (
            extract_callsign(
                packet
            )
        )

        return enrich_aprs_event(
            event
        )


    # --------------------------------------------------------
    # PACOTE RECEBIDO POR RF
    # --------------------------------------------------------

    match = re.match(
        r"^\[([0-9.]+)\s+([^\]]+)\]\s+(.+)$",
        line,
    )


    if match:

        packet = (
            match.group(3)
        )


        event["type"] = (
            "RF_RX"
        )


        event["decoder"] = (
            match.group(1)
        )


        event["direwolf_time"] = (
            match.group(2)
        )


        event["packet"] = (
            packet
        )


        event["callsign"] = (
            extract_callsign(
                packet
            )
        )


        return enrich_aprs_event(
            event
        )


    # --------------------------------------------------------
    # RF -> APRS-IS
    # --------------------------------------------------------

    if line.startswith(
        "[rx>ig] "
    ):

        packet = line[
            len("[rx>ig] "):
        ].strip()


        if packet == "#":

            event["type"] = (
                "IGATE_DEBUG"
            )

            return event


        if packet.startswith(
            "user "
        ):

            event["type"] = (
                "IGATE_DEBUG"
            )

            return event


        event["type"] = (
            "RF_TO_IS"
        )


        event["packet"] = (
            packet
        )


        event["callsign"] = (
            extract_callsign(
                packet
            )
        )


        return enrich_aprs_event(
            event
        )


    # --------------------------------------------------------
    # APRS-IS -> DIREWOLF
    # --------------------------------------------------------

    if line.startswith(
        "[ig>tx] "
    ):

        packet = line[
            len("[ig>tx] "):
        ].strip()


        event["type"] = (
            "IS_RX"
        )


        event["packet"] = (
            packet
        )


        event["callsign"] = (
            extract_callsign(
                packet
            )
        )


        return enrich_aprs_event(
            event
        )


    # --------------------------------------------------------
    # DUPLICADO
    # --------------------------------------------------------

    if (
        "Drop duplicate packet"
        in line
    ):

        event["type"] = (
            "DUPLICATE_DROP"
        )


        return event


    # --------------------------------------------------------
    # CONEXAO APRS-IS
    # --------------------------------------------------------

    if (
        "Now connected to IGate server"
        in line
    ):

        event["type"] = (
            "IGATE_CONNECTED"
        )


        return event


    if re.search(
        r"\blogresp\s+\S+\s+verified\b",
        line,
        re.IGNORECASE
    ):

        event["type"] = (
            "IGATE_VERIFIED"
        )


        return event


    # --------------------------------------------------------
    # DETALHES GERADOS PELO DIREWOLF
    # --------------------------------------------------------

    if line.startswith(
        "MIC-E"
    ):

        event["type"] = (
            "RF_DETAIL"
        )


        event["detail_type"] = (
            "MIC_E"
        )


        return event


    if re.match(
        r"^[NS]\s+[0-9]",
        line
    ):

        event["type"] = (
            "RF_DETAIL"
        )


        event["detail_type"] = (
            "POSITION"
        )


        return event


    return event


# ============================================================
# RECUPERACAO DO HISTORICO DO JOURNAL
# ============================================================

def recover_direwolf_history():

    last_time = (
        get_last_event_time()
    )

    try:

        if last_time:

            start_time = datetime.fromisoformat(
                last_time
            )

            if start_time.tzinfo is None:

                start_time = start_time.replace(
                    tzinfo=timezone.utc
                )

            start_time = (
                start_time
                .astimezone(
                    timezone.utc
                )
                - timedelta(
                    seconds=2
                )
            )

        else:

            start_time = (
                datetime.now(
                    timezone.utc
                )
                - timedelta(
                    hours=24
                )
            )

        since_value = (
            "@"
            + str(
                int(
                    start_time.timestamp()
                )
            )
        )

        result = subprocess.run(
            [
                "journalctl",
                "-u",
                "direwolf",
                "--since",
                since_value,
                "-o",
                "json",
                "--no-pager",
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:

            print(
                "[history] journalctl retornou erro: "
                + result.stderr.strip(),
                flush=True
            )

            return

        recovered = 0

        for raw_line in result.stdout.splitlines():

            if not raw_line.strip():

                continue

            try:

                record = json.loads(
                    raw_line
                )

            except Exception:

                continue

            message = record.get(
                "MESSAGE"
            )

            realtime = record.get(
                "__REALTIME_TIMESTAMP"
            )

            if not message or not realtime:

                continue

            try:

                event_time = datetime.fromtimestamp(
                    int(
                        realtime
                    )
                    / 1_000_000.0,
                    tz=timezone.utc
                )

            except Exception:

                continue

            event = parse_direwolf_line(
                str(
                    message
                )
            )

            event[
                "time"
            ] = event_time.isoformat()

            if insert_event_if_missing(
                event
            ):

                recovered += 1

        if recovered:

            print(
                f"[history] {recovered} eventos recuperados do journal.",
                flush=True
            )

    except Exception as exc:

        print(
            f"[history] falha na recuperacao: {exc}",
            flush=True
        )


# ============================================================
# COLETOR DO JOURNAL
# ============================================================

async def read_direwolf_journal():

    process = (
        await asyncio.create_subprocess_exec(

            "journalctl",
            "-u",
            "direwolf",
            "-f",
            "-o",
            "cat",
            "-n",
            "0",
            "--no-pager",

            stdout=(
                asyncio.subprocess.PIPE
            ),

            stderr=(
                asyncio.subprocess.STDOUT
            ),

        )
    )


    try:

        while True:

            line = (
                await process.stdout.readline()
            )


            if not line:

                await asyncio.sleep(
                    0.1
                )

                continue


            text = line.decode(
                "utf-8",
                errors="replace"
            ).rstrip()


            if not text:

                continue


            update_runtime_state(
                text
            )


            raw_events.append(
                text
            )


            event = (
                parse_direwolf_line(
                    text
                )
            )


            events.append(
                event
            )


            insert_event(
                event
            )


            print(
                f"[{event['type']}] {text}",
                flush=True
            )


    finally:

        if (
            process.returncode
            is None
        ):

            process.terminate()

            await process.wait()


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI
):

    init_db()


    recover_direwolf_history()


    bootstrap_runtime_state()


    task = asyncio.create_task(
        read_direwolf_journal()
    )


    yield


    task.cancel()


    try:

        await task

    except asyncio.CancelledError:

        pass


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title=f"{STATION_CALLSIGN} APRS Dashboard",
    lifespan=lifespan
)


# ============================================================
# DASHBOARD
# ============================================================

@app.get(
    "/",
    include_in_schema=False
)
def dashboard():

    return FileResponse(
        STATIC_DIR /
        "index.html"
    )


# ============================================================
# STATUS
# ============================================================

@app.get(
    "/api/status"
)
def status():

    hardware = (
        get_hardware_status()
    )

    direwolf_online = (
        direwolf_service_active()
    )

    # Compatibilidade com o frontend atual.
    # RF ONLINE significa que o processo do Direwolf esta ativo
    # e a cadeia de captura de audio esta disponivel.
    rf_online = (
        direwolf_online
        and hardware[
            "audio_online"
        ]
    )

    aprs_is_online = (

        direwolf_online

        and runtime_state[
            "aprs_is_verified"
        ]

    )


    return {

        "station":
            STATION_CALLSIGN,

        "location_label":
            STATION_LOCATION_LABEL,

        "timezone":
            APP_TIMEZONE,

        "audio_online":
            hardware[
                "audio_online"
            ],

        "audio_usb_present":
            hardware[
                "audio_usb_present"
            ],

        "audio_capture_present":
            hardware[
                "audio_capture_present"
            ],

        "audio_usb_id":
            hardware[
                "audio_usb_id"
            ],

        "audio_device":
            hardware[
                "audio_device"
            ],

        "ptt_mode":
            hardware[
                "ptt_mode"
            ],

        "ptt_configured":
            hardware[
                "ptt_configured"
            ],

        "ptt_online":
            hardware[
                "ptt_online"
            ],

        "ptt_label":
            hardware[
                "ptt_label"
            ],

        "ptt_device":
            hardware[
                "ptt_device"
            ],

        "gpio_chip":
            hardware[
                "gpio_chip"
            ],

        "gpio_line":
            hardware[
                "gpio_line"
            ],

        "serial_ptt_online":
            hardware[
                "serial_ptt_online"
            ],

        "serial_usb_present":
            hardware[
                "serial_usb_present"
            ],

        "serial_port_present":
            hardware[
                "serial_port_present"
            ],

        "serial_usb_id":
            hardware[
                "serial_usb_id"
            ],

        "serial_port":
            hardware[
                "serial_port"
            ],

        "direwolf_online":
            direwolf_online,

        "rf_online":
            rf_online,

        "aprs_is_online":
            aprs_is_online,

        "aprs_is_server":
            runtime_state[
                "aprs_is_server"
            ],

        "last_verified":
            runtime_state[
                "last_verified"
            ],

    }


# ============================================================
# LIVE TRAFFIC
# ============================================================

@app.get(
    "/api/events"
)
def get_events(
    limit: int = 60
):

    recent = (
        get_recent_events(
            limit
        )
    )


    return {

        "count":
            len(
                recent
            ),

        "events":
            recent,

    }


# ============================================================
# JOURNAL BRUTO
# ============================================================

@app.get(
    "/api/raw"
)
def get_raw():

    return {

        "count":
            len(
                raw_events
            ),

        "events":
            list(
                raw_events
            ),

    }


# ============================================================
# ESTATISTICAS
# ============================================================

@app.get(
    "/api/stats"
)
def stats(
    hours: int = 24
):

    return get_stats(
        hours
    )


# ============================================================
# ATIVIDADE POR HORA
# ============================================================

@app.get(
    "/api/hourly"
)
def hourly_activity():

    return (
        get_hourly_activity()
    )


# ============================================================
# MAPA
# ============================================================

@app.get(
    "/api/map"
)
def map_positions(
    hours: int = 24,
    limit: int = 250
):

    return get_map_positions(

        hours=hours,

        limit=limit

    )

# ============================================================
# EXTENSOES DO DASHBOARD
# ============================================================

try:
    from dashboard_extensions import register_routes

    register_routes(
        app
    )

except Exception as exc:

    print(
        f"[dashboard_extensions] {exc}",
        flush=True
    )

