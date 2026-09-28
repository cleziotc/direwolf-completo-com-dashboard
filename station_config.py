import os
import re
import shlex
import subprocess
import time

from datetime import datetime
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent

CONFIG_PATH = Path(
    os.environ.get(
        "DIREWOLF_CONFIG",
        "/home/aprs/direwolf.conf"
    )
)

BACKUP_DIR = Path(
    os.environ.get(
        "APRS_CONFIG_BACKUP_DIR",
        str(MODULE_DIR / "data" / "config-backups")
    )
)

SAMPLE_RATES = [
    11025,
    22050,
    44100,
    48000,
]

VIA_OPTIONS = [
    {
        "value": "WIDE1-1",
        "label": "WIDE1-1",
        "help": "Um salto local. É a opção mais conservadora para colocar tráfego do iGate no RF.",
    },
    {
        "value": "WIDE2-1",
        "label": "WIDE2-1",
        "help": "Um salto por digipeater de área ampla. Use quando a cobertura local exigir.",
    },
    {
        "value": "WIDE1-1,WIDE2-1",
        "label": "WIDE1-1, WIDE2-1",
        "help": "Até dois saltos. Aumenta bastante a ocupação do canal e deve ser usado com critério.",
    },
]

SYMBOL_CHOICES = [
    {
        "value": "I#",
        "label": "Digipeater / iGate",
        "icon": "📡",
        "help": "Símbolo de digipeater com overlay I, adequado a uma estação digipeater/iGate.",
    },
    {
        "value": "I&",
        "label": "iGate genérico",
        "icon": "🌐",
        "help": "iGate genérico.",
    },
    {
        "value": "R&",
        "label": "iGate somente RX",
        "icon": "⇣",
        "help": "iGate de recepção, sem retorno de mensagens ao RF.",
    },
    {
        "value": "T&",
        "label": "iGate TX 1 hop",
        "icon": "⇡",
        "help": "iGate com transmissão para RF e caminho de um salto.",
    },
    {
        "value": "/-",
        "label": "Estação fixa / Casa",
        "icon": "⌂",
        "help": "Símbolo APRS de residência ou estação fixa.",
    },
    {
        "value": "/>",
        "label": "Veículo",
        "icon": "🚗",
        "help": "Símbolo APRS de automóvel.",
    },
    {
        "value": "/_",
        "label": "Estação meteorológica",
        "icon": "🌤",
        "help": "Símbolo APRS de estação meteorológica.",
    },
]


def _read_raw_lines():

    try:

        return CONFIG_PATH.read_text(
            errors="replace"
        ).splitlines()

    except OSError:

        return []


def _active_lines():

    return [
        line.strip()
        for line in _read_raw_lines()
        if line.strip()
        and not line.strip().startswith("#")
    ]


def _first(
    lines,
    name
):

    prefix = (
        name.upper()
        + " "
    )

    for line in lines:

        if line.upper().startswith(
            prefix
        ):

            return line

    return None


def _tokens(
    line
):

    if not line:

        return []

    try:

        return shlex.split(
            line
        )

    except Exception:

        return line.split()


def _value(
    lines,
    name,
    index=1
):

    values = _tokens(
        _first(
            lines,
            name
        )
    )

    if len(values) <= index:

        return None

    return values[
        index
    ]


def _to_float(
    value
):

    try:

        return float(
            value
        )

    except Exception:

        return None


def _to_int(
    value
):

    try:

        return int(
            float(
                value
            )
        )

    except Exception:

        return None


def _kv(
    line
):

    result = {}

    for token in _tokens(
        line
    )[1:]:

        if "=" not in token:

            continue

        key, value = token.split(
            "=",
            1
        )

        result[
            key.upper()
        ] = value

    return result


def _beacon(
    line
):

    values = _kv(
        line
    )

    return {
        "enabled":
            bool(
                line
            ),

        "raw":
            line,

        "slot":
            values.get(
                "SLOT"
            ),

        "every_minutes":
            _to_int(
                values.get(
                    "EVERY"
                )
            ),

        "symbol":
            values.get(
                "SYMBOL"
            ),

        "overlay":
            values.get(
                "OVERLAY"
            ),

        "latitude":
            _to_float(
                values.get(
                    "LAT"
                )
            ),

        "longitude":
            _to_float(
                values.get(
                    "LONG"
                )
            ),

        "altitude_m":
            _to_float(
                values.get(
                    "ALT"
                )
            ),

        "power_w":
            _to_float(
                values.get(
                    "POWER"
                )
            ),

        "height_m":
            _to_float(
                values.get(
                    "HEIGHT"
                )
            ),

        "gain_dbi":
            _to_float(
                values.get(
                    "GAIN"
                )
            ),

        "comment":
            values.get(
                "COMMENT"
            ),

        "compress":
            values.get(
                "COMPRESS"
            ),

        "via":
            values.get(
                "VIA"
            ),

        "object_name":
            values.get(
                "OBJNAME"
            ),
    }


def _server(
    value
):

    if not value:

        return {
            "host": None,
            "port": None,
        }

    if ":" not in value:

        return {
            "host": value,
            "port": None,
        }

    host, port = value.rsplit(
        ":",
        1
    )

    return {
        "host":
            host,

        "port":
            _to_int(
                port
            ),
    }


def _filter(
    value
):

    result = {
        "raw":
            value,

        "latitude":
            None,

        "longitude":
            None,

        "radius_km":
            None,
    }

    if (
        not value
        or
        not value.startswith(
            "r/"
        )
    ):

        return result

    parts = value.split(
        "/"
    )

    if len(parts) < 4:

        return result

    result[
        "latitude"
    ] = _to_float(
        parts[1]
    )

    result[
        "longitude"
    ] = _to_float(
        parts[2]
    )

    result[
        "radius_km"
    ] = _to_float(
        parts[3]
    )

    return result


def _ptt(
    line
):

    values = _tokens(
        line
    )

    if len(values) < 2:

        return {
            "mode": "none",
            "port": None,
            "signal": None,
            "invert": False,
            "gpio_chip": None,
            "gpio_line": None,
        }

    if (
        values[1].upper()
        == "GPIOD"
        and len(values) >= 4
    ):

        raw_line = values[3]
        invert = raw_line.startswith(
            "-"
        )

        return {
            "mode": "gpiod",
            "port": None,
            "signal": None,
            "invert": invert,
            "gpio_chip": values[2],
            "gpio_line": _to_int(
                raw_line.lstrip(
                    "-"
                )
            ),
        }

    if len(values) < 3:

        return {
            "mode": "none",
            "port": None,
            "signal": None,
            "invert": False,
            "gpio_chip": None,
            "gpio_line": None,
        }

    signal = values[
        2
    ]

    invert = signal.startswith(
        "-"
    )

    return {
        "mode": "serial",
        "port":
            values[
                1
            ],

        "signal":
            signal.lstrip(
                "-"
            ).upper(),

        "invert":
            invert,

        "gpio_chip": None,

        "gpio_line": None,
    }


def _body_for_match(
    line
):

    stripped = line.strip()

    active = not stripped.startswith(
        "#"
    )

    body = stripped

    if not active:

        body = stripped.lstrip(
            "#"
        ).strip()

    return (
        active,
        body
    )


def _line_matches(
    line,
    directive
):

    _active, body = _body_for_match(
        line
    )

    prefix = directive.upper()

    upper = body.upper()

    return (
        upper == prefix
        or
        upper.startswith(
            prefix
            + " "
        )
    )


def _set_directive(
    lines,
    directive,
    new_line,
    enabled=True
):

    active_indexes = []
    commented_indexes = []

    for index, line in enumerate(
        lines
    ):

        if not _line_matches(
            line,
            directive
        ):

            continue

        active, _body = _body_for_match(
            line
        )

        if active:

            active_indexes.append(
                index
            )

        else:

            commented_indexes.append(
                index
            )

    if active_indexes:

        index = active_indexes[
            0
        ]

    elif commented_indexes:

        index = commented_indexes[
            0
        ]

    else:

        index = None

    replacement = (
        new_line
        if enabled
        else "#"
        + new_line
    )

    if index is None:

        lines.append(
            replacement
        )

    else:

        lines[
            index
        ] = replacement

    return lines


def _fmt_number(
    value
):

    number = float(
        value
    )

    if number.is_integer():

        return str(
            int(
                number
            )
        )

    return (
        f"{number:.6f}"
        .rstrip(
            "0"
        )
        .rstrip(
            "."
        )
    )


def _quote(
    value
):

    text = str(
        value or ""
    )

    text = text.replace(
        "\\",
        "\\\\"
    ).replace(
        '"',
        '\\"'
    )

    return (
        '"'
        + text
        + '"'
    )


def _build_beacon_line(
    kind,
    data
):

    tokens = [
        kind,
    ]

    if kind == "PBEACON":

        tokens.append(
            "SENDTO="
            + str(
                data.get(
                    "sendto"
                )
                or "IG"
            )
        )

    if kind == "OBEACON":

        tokens.append(
            "SENDTO="
            + str(
                data.get(
                    "sendto"
                )
                or "0"
            )
        )

        if data.get(
            "object_name"
        ):

            tokens.append(
                "OBJNAME="
                + str(
                    data[
                        "object_name"
                    ]
                )
            )

    if data.get(
        "slot"
    ):

        tokens.append(
            "SLOT="
            + str(
                data[
                    "slot"
                ]
            )
        )

    if data.get(
        "every_minutes"
    ) is not None:

        tokens.append(
            "EVERY="
            + str(
                int(
                    data[
                        "every_minutes"
                    ]
                )
            )
        )

    if data.get(
        "symbol"
    ):

        tokens.append(
            "SYMBOL="
            + str(
                data[
                    "symbol"
                ]
            )
        )

    if data.get(
        "overlay"
    ):

        tokens.append(
            "OVERLAY="
            + str(
                data[
                    "overlay"
                ]
            )
        )

    mapping = [
        (
            "latitude",
            "LAT"
        ),
        (
            "longitude",
            "LONG"
        ),
        (
            "altitude_m",
            "ALT"
        ),
        (
            "power_w",
            "POWER"
        ),
        (
            "height_m",
            "HEIGHT"
        ),
        (
            "gain_dbi",
            "GAIN"
        ),
    ]

    for key, name in mapping:

        if data.get(
            key
        ) is not None:

            tokens.append(
                name
                + "="
                + _fmt_number(
                    data[
                        key
                    ]
                )
            )

    if data.get(
        "comment"
    ) is not None:

        tokens.append(
            "COMMENT="
            + _quote(
                data[
                    "comment"
                ]
            )
        )

    if data.get(
        "compress"
    ) is not None:

        tokens.append(
            "COMPRESS="
            + str(
                int(
                    bool(
                        int(
                            data[
                                "compress"
                            ]
                        )
                    )
                )
            )
        )

    if data.get(
        "via"
    ):

        tokens.append(
            "VIA="
            + str(
                data[
                    "via"
                ]
            )
        )

    return " ".join(
        tokens
    )


def _validate_callsign(
    value
):

    callsign = (
        str(
            value or ""
        )
        .strip()
        .upper()
    )

    if not re.fullmatch(
        r"[A-Z0-9]{1,6}(?:-[0-9]{1,2})?",
        callsign
    ):

        raise ValueError(
            "Indicativo inválido."
        )

    return callsign


def _number(
    payload,
    key,
    minimum,
    maximum,
    integer=False
):

    try:

        value = float(
            payload[
                key
            ]
        )

    except Exception:

        raise ValueError(
            f"Valor inválido em {key}."
        )

    if (
        value < minimum
        or
        value > maximum
    ):

        raise ValueError(
            f"{key} fora da faixa permitida."
        )

    if integer:

        return int(
            round(
                value
            )
        )

    return value


def _render_lines(
    lines
):

    return (
        "\n".join(
            lines
        )
        + "\n"
    )


def _write_lines(
    lines
):

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    stamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    backup = BACKUP_DIR / (
        "direwolf.conf."
        + stamp
        + ".bak"
    )

    original = CONFIG_PATH.read_text(
        errors="replace"
    )

    backup.write_text(
        original
    )

    temp = CONFIG_PATH.with_suffix(
        ".conf.tmp"
    )

    temp.write_text(
        _render_lines(
            lines
        )
    )

    temp.replace(
        CONFIG_PATH
    )

    return backup


def _service_is_active():

    try:

        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "--quiet",
                "direwolf.service",
            ],
            timeout=4,
        )

    except Exception:

        return False

    return (
        result.returncode
        == 0
    )


def _restart_after_save(
    backup
):

    try:

        result = subprocess.run(
            [
                "sudo",
                "-n",
                "systemctl",
                "restart",
                "direwolf.service",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

    except Exception as exc:

        return {
            "applied":
                False,

            "restart_required":
                True,

            "message":
                (
                    "Configuração salva. "
                    "Não foi possível reiniciar automaticamente: "
                    + str(
                        exc
                    )
                ),
        }

    if result.returncode != 0:

        error_text = (
            result.stderr
            or result.stdout
            or ""
        )

        error_lower = (
            error_text.lower()
        )

        if (
            "password" in error_lower
            or
            "not allowed" in error_lower
        ):

            return {
                "applied":
                    False,

                "restart_required":
                    True,

                "message":
                    "Configuração salva. Reinicie o Direwolf para aplicar.",
            }

        if _service_is_active():

            detail = (
                error_text.strip()
            )

            message = (
                "Configuração salva, mas o reinício automático não foi confirmado."
            )

            if detail:

                message += (
                    " "
                    + detail[:180]
                )

            return {
                "applied":
                    False,

                "restart_required":
                    True,

                "message":
                    message,
            }

        CONFIG_PATH.write_text(
            backup.read_text()
        )

        subprocess.run(
            [
                "sudo",
                "-n",
                "systemctl",
                "restart",
                "direwolf.service",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        raise RuntimeError(
            "O Direwolf não iniciou com a nova configuração. Backup restaurado."
        )

    time.sleep(
        1.2
    )

    if not _service_is_active():

        CONFIG_PATH.write_text(
            backup.read_text()
        )

        subprocess.run(
            [
                "sudo",
                "-n",
                "systemctl",
                "restart",
                "direwolf.service",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        raise RuntimeError(
            "O Direwolf não voltou após a alteração. Backup restaurado."
        )

    return {
        "applied":
            True,

        "restart_required":
            False,

        "message":
            "Configuração salva e Direwolf reiniciado.",
    }


def _list_audio_devices():

    devices = {}

    pattern = re.compile(
        r"card\s+(\d+):\s+([^\[]+)\s+\[([^\]]+)\],\s+device\s+(\d+):\s+([^\[]+)\s+\[([^\]]+)\]",
        re.IGNORECASE,
    )

    for command in (
        [
            "arecord",
            "-l",
        ],
        [
            "aplay",
            "-l",
        ],
    ):

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=4,
            )

        except Exception:

            continue

        text = (
            result.stdout
            + "\n"
            + result.stderr
        )

        for match in pattern.finditer(
            text
        ):

            card = int(
                match.group(
                    1
                )
            )

            device = int(
                match.group(
                    4
                )
            )

            value = (
                f"plughw:{card},{device}"
            )

            label = (
                match.group(
                    3
                ).strip()
                + " — "
                + match.group(
                    6
                ).strip()
                + " ("
                + value
                + ")"
            )

            devices[
                value
            ] = {
                "value":
                    value,

                "label":
                    label,
            }

    current = load_station_config().get(
        "radio",
        {}
    ).get(
        "audio_device"
    )

    if (
        current
        and
        current not in devices
    ):

        devices[
            current
        ] = {
            "value":
                current,

            "label":
                current
                + " — configuração atual",
        }

    return list(
        devices.values()
    )


def _list_serial_ports():

    ports = []

    for pattern in (
        "ttyUSB*",
        "ttyACM*",
    ):

        for path in sorted(
            Path(
                "/dev"
            ).glob(
                pattern
            )
        ):

            ports.append(
                str(
                    path
                )
            )

    by_id = Path(
        "/dev/serial/by-id"
    )

    if by_id.exists():

        for path in sorted(
            by_id.iterdir()
        ):

            ports.append(
                str(
                    path
                )
            )

    current = load_station_config().get(
        "radio",
        {}
    ).get(
        "ptt_port"
    )

    if (
        current
        and
        current not in ports
    ):

        ports.append(
            current
        )

    return [
        {
            "value":
                value,

            "label":
                value,
        }
        for value in dict.fromkeys(
            ports
        )
    ]


def _list_gpio_chips():

    chips = []

    for path in sorted(
        Path(
            "/dev"
        ).glob(
            "gpiochip*"
        )
    ):

        chips.append(
            {
                "value":
                    str(
                        path
                    ),

                "label":
                    str(
                        path
                    ),
            }
        )

    current = load_station_config().get(
        "radio",
        {}
    ).get(
        "gpio_chip"
    )

    if (
        current
        and all(
            item[
                "value"
            ]
            != current
            for item in chips
        )
    ):

        chips.append(
            {
                "value":
                    current,

                "label":
                    current,
            }
        )

    return chips


def get_station_capabilities():

    return {
        "audio_devices":
            _list_audio_devices(),

        "serial_ports":
            _list_serial_ports(),

        "gpio_chips":
            _list_gpio_chips(),

        "ptt_modes": [
            "none",
            "serial",
            "gpiod",
        ],

        "sample_rates":
            SAMPLE_RATES,

        "channels": [
            1,
            2,
        ],

        "ptt_signals": [
            "DTR",
            "RTS",
        ],

        "via_options":
            VIA_OPTIONS,

        "symbols":
            SYMBOL_CHOICES,
    }


def load_station_config():

    lines = _active_lines()

    server = _server(
        _value(
            lines,
            "IGSERVER"
        )
    )

    aprs_filter = _filter(
        _value(
            lines,
            "IGFILTER"
        )
    )

    beacon_is = _beacon(
        _first(
            lines,
            "PBEACON"
        )
    )

    beacon_rf = _beacon(
        _first(
            lines,
            "OBEACON"
        )
    )

    tx_limit = _tokens(
        _first(
            lines,
            "IGTXLIMIT"
        )
    )

    ptt = _ptt(
        _first(
            lines,
            "PTT"
        )
    )

    latitude = beacon_is.get(
        "latitude"
    )

    longitude = beacon_is.get(
        "longitude"
    )

    if latitude is None:

        latitude = aprs_filter.get(
            "latitude"
        )

    if longitude is None:

        longitude = aprs_filter.get(
            "longitude"
        )

    return {
        "config_path":
            str(
                CONFIG_PATH
            ),

        "station": {
            "callsign":
                _value(
                    lines,
                    "MYCALL"
                ),

            "latitude":
                latitude,

            "longitude":
                longitude,

            "altitude_m":
                beacon_is.get(
                    "altitude_m"
                ),

            "antenna_height_m":
                beacon_is.get(
                    "height_m"
                ),

            "antenna_gain_dbi":
                beacon_is.get(
                    "gain_dbi"
                ),

            "power_w":
                beacon_is.get(
                    "power_w"
                ),
        },

        "aprs_is": {
            "server":
                server[
                    "host"
                ],

            "port":
                server[
                    "port"
                ],

            "credential_configured":
                bool(
                    _first(
                        lines,
                        "IGLOGIN"
                    )
                ),

            "filter":
                aprs_filter,
        },

        "beacon_is":
            beacon_is,

        "beacon_rf":
            beacon_rf,

        "digipeater": {
            "enabled":
                bool(
                    _first(
                        lines,
                        "DIGIPEAT"
                    )
                ),

            "raw":
                _first(
                    lines,
                    "DIGIPEAT"
                ),
        },

        "igate_tx": {
            "enabled":
                bool(
                    _first(
                        lines,
                        "IGTXVIA"
                    )
                ),

            "via":
                _value(
                    lines,
                    "IGTXVIA",
                    2
                ),

            "filter_raw":
                _first(
                    lines,
                    "FILTER IG"
                ),

            "limit_1m":
                (
                    _to_int(
                        tx_limit[
                            1
                        ]
                    )
                    if len(
                        tx_limit
                    ) >= 2
                    else None
                ),

            "limit_5m":
                (
                    _to_int(
                        tx_limit[
                            2
                        ]
                    )
                    if len(
                        tx_limit
                    ) >= 3
                    else None
                ),
        },

        "radio": {
            "audio_device":
                _value(
                    lines,
                    "ADEVICE"
                ),

            "audio_channels":
                _to_int(
                    _value(
                        lines,
                        "ACHANNELS"
                    )
                ),

            "sample_rate":
                _to_int(
                    _value(
                        lines,
                        "ARATE"
                    )
                ),

            "ptt_raw":
                _first(
                    lines,
                    "PTT"
                ),

            "ptt_mode":
                ptt[
                    "mode"
                ],

            "ptt_port":
                ptt[
                    "port"
                ],

            "ptt_signal":
                ptt[
                    "signal"
                ],

            "ptt_invert":
                ptt[
                    "invert"
                ],

            "gpio_chip":
                ptt[
                    "gpio_chip"
                ],

            "gpio_line":
                ptt[
                    "gpio_line"
                ],

            "dwait":
                _to_int(
                    _value(
                        lines,
                        "DWAIT"
                    )
                ),

            "slottime":
                _to_int(
                    _value(
                        lines,
                        "SLOTTIME"
                    )
                ),

            "persist":
                _to_int(
                    _value(
                        lines,
                        "PERSIST"
                    )
                ),

            "txdelay":
                _to_int(
                    _value(
                        lines,
                        "TXDELAY"
                    )
                ),

            "txdelay_ms":
                (
                    _to_int(
                        _value(
                            lines,
                            "TXDELAY"
                        )
                    )
                    or 0
                )
                * 10,

            "txtail":
                _to_int(
                    _value(
                        lines,
                        "TXTAIL"
                    )
                ),

            "dedupe":
                _to_int(
                    _value(
                        lines,
                        "DEDUPE"
                    )
                ),
        },
    }


def _save_identification(
    lines,
    payload
):

    current = load_station_config()

    callsign = _validate_callsign(
        payload.get(
            "callsign"
        )
        or current[
            "station"
        ][
            "callsign"
        ]
    )

    server = str(
        payload.get(
            "server"
        )
        or ""
    ).strip()

    if not re.fullmatch(
        r"[A-Za-z0-9.-]+",
        server
    ):

        raise ValueError(
            "Servidor APRS-IS inválido."
        )

    port = _number(
        payload,
        "port",
        1,
        65535,
        integer=True
    )

    radius = _number(
        payload,
        "radius_km",
        1,
        500,
        integer=False
    )

    latitude = current[
        "station"
    ][
        "latitude"
    ]

    longitude = current[
        "station"
    ][
        "longitude"
    ]

    if (
        latitude is None
        or
        longitude is None
    ):

        raise ValueError(
            "Defina a localização antes de alterar o filtro."
        )

    active = _active_lines()

    login_tokens = _tokens(
        _first(
            active,
            "IGLOGIN"
        )
    )

    current_passcode = (
        login_tokens[
            2
        ]
        if len(
            login_tokens
        ) >= 3
        else None
    )

    new_passcode = str(
        payload.get(
            "passcode"
        )
        or ""
    ).strip()

    if new_passcode:

        if not re.fullmatch(
            r"[0-9]{1,5}",
            new_passcode
        ):

            raise ValueError(
                "Passcode APRS-IS inválido."
            )

        passcode = new_passcode

    else:

        passcode = current_passcode

    if not passcode:

        raise ValueError(
            "O passcode APRS-IS precisa estar configurado."
        )

    _set_directive(
        lines,
        "MYCALL",
        "MYCALL "
        + callsign,
    )

    _set_directive(
        lines,
        "IGLOGIN",
        "IGLOGIN "
        + callsign
        + " "
        + passcode,
    )

    _set_directive(
        lines,
        "IGSERVER",
        "IGSERVER "
        + server
        + ":"
        + str(
            port
        ),
    )

    _set_directive(
        lines,
        "IGFILTER",
        (
            "IGFILTER r/"
            + f"{latitude:.5f}"
            + "/"
            + f"{longitude:.5f}"
            + "/"
            + _fmt_number(
                radius
            )
        ),
    )


def _save_location(
    lines,
    payload
):

    current = load_station_config()

    latitude = _number(
        payload,
        "latitude",
        -90,
        90
    )

    longitude = _number(
        payload,
        "longitude",
        -180,
        180
    )

    altitude = _number(
        payload,
        "altitude_m",
        -500,
        10000
    )

    height = _number(
        payload,
        "antenna_height_m",
        0,
        1000
    )

    gain = _number(
        payload,
        "antenna_gain_dbi",
        -20,
        50
    )

    power = _number(
        payload,
        "power_w",
        0,
        10000
    )

    radius = (
        current[
            "aprs_is"
        ][
            "filter"
        ][
            "radius_km"
        ]
        or 100
    )

    _set_directive(
        lines,
        "IGFILTER",
        (
            "IGFILTER r/"
            + f"{latitude:.5f}"
            + "/"
            + f"{longitude:.5f}"
            + "/"
            + _fmt_number(
                radius
            )
        ),
    )

    for kind, key in (
        (
            "PBEACON",
            "beacon_is"
        ),
        (
            "OBEACON",
            "beacon_rf"
        ),
    ):

        data = dict(
            current[
                key
            ]
        )

        data.update(
            {
                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "altitude_m":
                    altitude,

                "height_m":
                    height,

                "gain_dbi":
                    gain,

                "power_w":
                    power,
            }
        )

        if kind == "PBEACON":

            data[
                "sendto"
            ] = "IG"

        else:

            data[
                "sendto"
            ] = "0"

        _set_directive(
            lines,
            kind,
            _build_beacon_line(
                kind,
                data
            ),
            enabled=data.get(
                "enabled",
                True
            ),
        )


def _save_beacon(
    lines,
    payload
):

    current = load_station_config()

    comment = str(
        payload.get(
            "comment"
        )
        or ""
    ).strip()

    if len(
        comment
    ) > 80:

        raise ValueError(
            "Comentário do beacon muito longo."
        )

    symbol = str(
        payload.get(
            "symbol"
        )
        or ""
    ).strip()

    allowed_symbols = {
        item[
            "value"
        ]
        for item in SYMBOL_CHOICES
    }

    current_symbol = current[
        "beacon_is"
    ].get(
        "symbol"
    )

    if (
        symbol not in allowed_symbols
        and
        symbol != current_symbol
    ):

        raise ValueError(
            "Símbolo APRS não reconhecido."
        )

    every = _number(
        payload,
        "every_minutes",
        1,
        1440,
        integer=True
    )

    slot = str(
        payload.get(
            "slot"
        )
        or ""
    ).strip()

    if not re.fullmatch(
        r"[0-9]{1,2}:[0-9]{2}",
        slot
    ):

        raise ValueError(
            "SLOT deve usar o formato mm:ss."
        )

    compress = (
        1
        if bool(
            payload.get(
                "compress"
            )
        )
        else 0
    )

    pbeacon = dict(
        current[
            "beacon_is"
        ]
    )

    pbeacon.update(
        {
            "sendto":
                "IG",

            "comment":
                comment,

            "symbol":
                symbol,

            "overlay":
                None,

            "every_minutes":
                every,

            "slot":
                slot,

            "compress":
                compress,
        }
    )

    _set_directive(
        lines,
        "PBEACON",
        _build_beacon_line(
            "PBEACON",
            pbeacon
        ),
        enabled=True,
    )

    rf = dict(
        current[
            "beacon_rf"
        ]
    )

    if rf.get(
        "raw"
    ):

        rf.update(
            {
                "sendto":
                    "0",

                "comment":
                    comment,

                "symbol":
                    symbol,

                "overlay":
                    None,

                "compress":
                    compress,
            }
        )

        _set_directive(
            lines,
            "OBEACON",
            _build_beacon_line(
                "OBEACON",
                rf
            ),
            enabled=rf.get(
                "enabled",
                True
            ),
        )


def _save_digipeater(
    lines,
    payload
):

    current = load_station_config()

    digi_enabled = bool(
        payload.get(
            "digipeater_enabled"
        )
    )

    igate_enabled = bool(
        payload.get(
            "igate_enabled"
        )
    )

    via = str(
        payload.get(
            "via"
        )
        or ""
    ).strip()

    allowed_via = {
        item[
            "value"
        ]
        for item in VIA_OPTIONS
    }

    if via not in allowed_via:

        raise ValueError(
            "Caminho VIA inválido."
        )

    limit_1m = _number(
        payload,
        "limit_1m",
        1,
        999,
        integer=True
    )

    limit_5m = _number(
        payload,
        "limit_5m",
        limit_1m,
        5000,
        integer=True
    )

    digi_line = (
        current[
            "digipeater"
        ].get(
            "raw"
        )
        or "DIGIPEAT 0 0 ^WIDE$ ^WIDE[1-2]-[1-2]$ TRACE"
    )

    _set_directive(
        lines,
        "DIGIPEAT",
        digi_line,
        enabled=digi_enabled,
    )

    _set_directive(
        lines,
        "IGTXVIA",
        "IGTXVIA 0 "
        + via,
        enabled=igate_enabled,
    )

    _set_directive(
        lines,
        "FILTER IG",
        "FILTER IG 0 1",
        enabled=igate_enabled,
    )

    _set_directive(
        lines,
        "IGTXLIMIT",
        (
            "IGTXLIMIT "
            + str(
                limit_1m
            )
            + " "
            + str(
                limit_5m
            )
        ),
        enabled=True,
    )


def _save_hardware(
    lines,
    payload
):

    current = load_station_config()

    audio_device = str(
        payload.get(
            "audio_device"
        )
        or ""
    ).strip()

    allowed_audio = {
        item[
            "value"
        ]
        for item in _list_audio_devices()
    }

    if (
        audio_device not in allowed_audio
        and
        audio_device
        != current[
            "radio"
        ][
            "audio_device"
        ]
    ):

        raise ValueError(
            "Dispositivo de áudio não encontrado."
        )

    sample_rate = int(
        payload.get(
            "sample_rate"
        )
        or 0
    )

    if sample_rate not in SAMPLE_RATES:

        raise ValueError(
            "Sample rate inválido."
        )

    channels = int(
        payload.get(
            "audio_channels"
        )
        or 0
    )

    if channels not in (
        1,
        2,
    ):

        raise ValueError(
            "Número de canais inválido."
        )

    ptt_mode = str(
        payload.get(
            "ptt_mode"
        )
        or current[
            "radio"
        ].get(
            "ptt_mode"
        )
        or "none"
    ).strip().lower()

    if ptt_mode not in (
        "none",
        "serial",
        "gpiod",
    ):

        raise ValueError(
            "Método de PTT inválido."
        )

    serial_port = str(
        payload.get(
            "ptt_port"
        )
        or ""
    ).strip()

    signal = str(
        payload.get(
            "ptt_signal"
        )
        or "DTR"
    ).strip().upper()

    gpio_chip = str(
        payload.get(
            "gpio_chip"
        )
        or ""
    ).strip()

    gpio_line_raw = payload.get(
        "gpio_line"
    )

    gpio_line = None

    invert = bool(
        payload.get(
            "ptt_invert"
        )
    )

    if ptt_mode == "serial":

        allowed_ports = {
            item[
                "value"
            ]
            for item in _list_serial_ports()
        }

        if (
            serial_port not in allowed_ports
            and
            serial_port
            != current[
                "radio"
            ][
                "ptt_port"
            ]
        ):

            raise ValueError(
                "Porta serial de PTT não encontrada."
            )

        if signal not in (
            "DTR",
            "RTS",
        ):

            raise ValueError(
                "Sinal de PTT inválido."
            )

    elif ptt_mode == "gpiod":

        if not gpio_chip:

            raise ValueError(
                "GPIO chip do PTT não informado."
            )

        if not gpio_chip.startswith(
            "/"
        ):

            gpio_chip = (
                "/dev/"
                + gpio_chip
            )

        allowed_chips = {
            item[
                "value"
            ]
            for item in _list_gpio_chips()
        }

        current_chip = current[
            "radio"
        ].get(
            "gpio_chip"
        )

        if (
            gpio_chip not in allowed_chips
            and gpio_chip
            != current_chip
        ):

            raise ValueError(
                "GPIO chip do PTT não encontrado."
            )

        try:

            gpio_line = int(
                gpio_line_raw
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "Linha GPIO do PTT inválida."
            )

        if not (
            0
            <= gpio_line
            <= 255
        ):

            raise ValueError(
                "Linha GPIO do PTT fora do intervalo permitido."
            )

    dwait = _number(
        payload,
        "dwait",
        0,
        255,
        integer=True
    )

    slottime = _number(
        payload,
        "slottime",
        0,
        255,
        integer=True
    )

    persist_raw = payload.get(
        "persist"
    )

    if (
        persist_raw is None
        or
        str(
            persist_raw
        ).strip() == ""
    ):

        persist = current[
            "radio"
        ][
            "persist"
        ]

    else:

        persist = _number(
            payload,
            "persist",
            0,
            255,
            integer=True
        )

    txdelay_ms = _number(
        payload,
        "txdelay_ms",
        0,
        2000,
        integer=True
    )

    txtail = _number(
        payload,
        "txtail",
        0,
        255,
        integer=True
    )

    dedupe = _number(
        payload,
        "dedupe",
        0,
        3600,
        integer=True
    )

    txdelay_units = int(
        round(
            txdelay_ms
            / 10
        )
    )

    _set_directive(
        lines,
        "ADEVICE",
        "ADEVICE "
        + audio_device,
    )

    _set_directive(
        lines,
        "ARATE",
        "ARATE "
        + str(
            sample_rate
        ),
    )

    _set_directive(
        lines,
        "ACHANNELS",
        "ACHANNELS "
        + str(
            channels
        ),
    )

    if ptt_mode == "serial":

        ptt_signal = (
            "-"
            if invert
            else ""
        ) + signal

        _set_directive(
            lines,
            "PTT",
            (
                "PTT "
                + serial_port
                + " "
                + ptt_signal
            ),
        )

    elif ptt_mode == "gpiod":

        gpio_value = (
            "-"
            if invert
            else ""
        ) + str(
            gpio_line
        )

        _set_directive(
            lines,
            "PTT",
            (
                "PTT GPIOD "
                + gpio_chip
                + " "
                + gpio_value
            ),
        )

    else:

        current_ptt = (
            current[
                "radio"
            ].get(
                "ptt_raw"
            )
            or "PTT /dev/ttyUSB0 DTR"
        )

        _set_directive(
            lines,
            "PTT",
            current_ptt,
            enabled=False
        )


    values = {
        "DWAIT":
            dwait,

        "SLOTTIME":
            slottime,

        "PERSIST":
            persist,

        "TXDELAY":
            txdelay_units,

        "TXTAIL":
            txtail,

        "DEDUPE":
            dedupe,
    }

    for directive, value in values.items():

        if value is None:

            continue

        _set_directive(
            lines,
            directive,
            directive
            + " "
            + str(
                value
            ),
        )


def save_station_section(
    section,
    payload
):

    if not isinstance(
        payload,
        dict
    ):

        raise ValueError(
            "Payload inválido."
        )

    lines = _read_raw_lines()

    if not lines:

        raise RuntimeError(
            "Não foi possível ler o direwolf.conf."
        )

    section = str(
        section
    ).strip().lower()

    if section == "identification":

        _save_identification(
            lines,
            payload
        )

    elif section == "location":

        _save_location(
            lines,
            payload
        )

    elif section == "beacon":

        _save_beacon(
            lines,
            payload
        )

    elif section == "digipeater":

        _save_digipeater(
            lines,
            payload
        )

    elif section == "hardware":

        _save_hardware(
            lines,
            payload
        )

    else:

        raise ValueError(
            "Seção de configuração desconhecida."
        )

    original = CONFIG_PATH.read_text(
        errors="replace"
    )

    candidate = _render_lines(
        lines
    )

    if candidate == original:

        return {
            "saved":
                False,

            "changed":
                False,

            "section":
                section,

            "backup":
                None,

            "applied":
                False,

            "restart_required":
                False,

            "message":
                "Nenhuma alteração detectada.",

            "config":
                load_station_config(),
        }

    backup = _write_lines(
        lines
    )

    apply_result = _restart_after_save(
        backup
    )

    return {
        "saved":
            True,

        "changed":
            True,

        "section":
            section,

        "backup":
            str(
                backup
            ),

        **apply_result,

        "config":
            load_station_config(),
    }
