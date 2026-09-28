import os
import re
import shutil
import subprocess
import time

from database import get_audio_activity_state


try:
    ALSA_CARD = int(os.environ.get("APRS_ALSA_CARD", "0"))
except ValueError:
    ALSA_CARD = 0
DISCOVERY_TTL_SECONDS = 30

RX_CONTROL_CANDIDATES = [
    "Mic",
    "Capture",
    "Line",
    "Line In",
    "Input Gain",
    "ADC",
]

TX_CONTROL_CANDIDATES = [
    "Speaker",
    "PCM",
    "Master",
    "Playback",
    "Headphone",
    "Line Out",
    "DAC",
]

_discovery_cache = {
    "time": 0.0,
    "value": None,
}


def _run_amixer(*args, timeout=3):

    if shutil.which("amixer") is None:

        return None

    try:

        result = subprocess.run(
            [
                "amixer",
                "-c",
                str(ALSA_CARD),
                *args,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    except Exception:

        return None

    if result.returncode != 0:

        return None

    return result.stdout


def _list_controls():

    output = _run_amixer(
        "scontrols"
    )

    if not output:

        return []

    names = []

    for line in output.splitlines():

        match = re.search(
            r"Simple mixer control '([^']+)'",
            line
        )

        if match:

            names.append(
                match.group(1)
            )

    return names


def _control_dump(
    name
):

    return _run_amixer(
        "get",
        name
    )


def _score_control(
    name,
    dump,
    role
):

    if not dump:

        return -1000

    lower_name = name.lower()
    lower_dump = dump.lower()

    if role == "rx":

        score = (
            40
            if "capture" in lower_dump
            else 0
        )

        candidates = (
            RX_CONTROL_CANDIDATES
        )

        if (
            "playback" in lower_dump
            and
            "capture" not in lower_dump
        ):

            score -= 20

    else:

        score = (
            40
            if "playback" in lower_dump
            else 0
        )

        candidates = (
            TX_CONTROL_CANDIDATES
        )

        if (
            "capture" in lower_dump
            and
            "playback" not in lower_dump
        ):

            score -= 20

    for index, candidate in enumerate(
        candidates
    ):

        candidate_lower = (
            candidate.lower()
        )

        if lower_name == candidate_lower:

            score += (
                100
                - index * 5
            )

        elif candidate_lower in lower_name:

            score += (
                50
                - index * 3
            )

    if re.search(
        r"\[[0-9]{1,3}%\]",
        dump
    ):

        score += 15

    return score


def _resolve_role_control(
    controls,
    role
):

    best = None
    best_score = -1000

    for name in controls:

        dump = _control_dump(
            name
        )

        score = _score_control(
            name,
            dump,
            role
        )

        if score > best_score:

            best = {
                "name": name,
                "dump": dump,
            }

            best_score = score

    if (
        best is None
        or
        best_score < 25
    ):

        return None

    return best[
        "name"
    ]


def discover_audio_controls(
    force=False
):

    now = time.monotonic()

    cached = _discovery_cache[
        "value"
    ]

    if (
        not force
        and
        cached is not None
        and
        now
        - _discovery_cache[
            "time"
        ]
        < DISCOVERY_TTL_SECONDS
    ):

        return cached

    controls = _list_controls()

    value = {
        "amixer_available":
            shutil.which(
                "amixer"
            ) is not None,

        "card":
            ALSA_CARD,

        "rx_control":
            _resolve_role_control(
                controls,
                "rx"
            ),

        "tx_control":
            _resolve_role_control(
                controls,
                "tx"
            ),

        "controls":
            controls,
    }

    _discovery_cache[
        "time"
    ] = now

    _discovery_cache[
        "value"
    ] = value

    return value


def _read_percent(
    control_name
):

    if not control_name:

        return None

    dump = _control_dump(
        control_name
    )

    if not dump:

        return None

    values = [
        int(value)
        for value in re.findall(
            r"\[([0-9]{1,3})%\]",
            dump
        )
    ]

    if not values:

        return None

    return round(
        sum(values)
        / len(values)
    )


def set_audio_gain(
    role,
    percent
):

    role = (
        str(role)
        .strip()
        .lower()
    )

    if role not in {
        "rx",
        "tx",
    }:

        raise ValueError(
            "role deve ser rx ou tx"
        )

    percent = int(
        percent
    )

    percent = max(
        0,
        min(
            100,
            percent
        )
    )

    controls = discover_audio_controls(
        force=True
    )

    control_name = controls[
        (
            "rx_control"
            if role == "rx"
            else "tx_control"
        )
    ]

    if not control_name:

        raise RuntimeError(
            "controle ALSA não encontrado"
        )

    output = _run_amixer(
        "sset",
        control_name,
        f"{percent}%"
    )

    if output is None:

        raise RuntimeError(
            "falha ao ajustar controle ALSA"
        )

    return {
        "role":
            role,

        "control":
            control_name,

        "percent":
            _read_percent(
                control_name
            ),
    }


def get_audio_console_state():

    controls = discover_audio_controls()

    rx_control = controls[
        "rx_control"
    ]

    tx_control = controls[
        "tx_control"
    ]

    activity = (
        get_audio_activity_state()
    )

    rx_level = activity.get(
        "audio_level"
    )

    audio_age = activity.get(
        "audio_age_seconds"
    )

    if (
        audio_age is None
        or
        audio_age > 3.0
    ):

        rx_level = 0

    try:

        rx_level = int(
            rx_level or 0
        )

    except Exception:

        rx_level = 0

    # O Direwolf informa um valor relativo de nível de áudio,
    # não dBFS. Mantemos o valor bruto e convertemos apenas
    # para preencher visualmente o VU.
    rx_meter_percent = max(
        0,
        min(
            100,
            round(
                rx_level
                / 120
                * 100
            )
        )
    )

    tx_active = bool(
        activity.get(
            "tx_active"
        )
    )

    # O Direwolf não publica a amplitude PCM do áudio transmitido.
    # O VU TX, portanto, representa atividade de transmissão;
    # o indicador TX ON continua sendo a fonte de verdade.
    tx_meter_percent = (
        82
        if tx_active
        else 0
    )

    return {
        "available":
            controls[
                "amixer_available"
            ],

        "card":
            ALSA_CARD,

        "rx": {
            "available":
                rx_control is not None,

            "control":
                rx_control,

            "gain_percent":
                _read_percent(
                    rx_control
                ),

            "active":
                bool(
                    activity.get(
                        "rx_active"
                    )
                ),

            "direwolf_level":
                rx_level,

            "meter_percent":
                rx_meter_percent,

            "age_seconds":
                activity.get(
                    "rf_age_seconds"
                ),
        },

        "tx": {
            "available":
                tx_control is not None,

            "control":
                tx_control,

            "gain_percent":
                _read_percent(
                    tx_control
                ),

            "active":
                tx_active,

            "meter_percent":
                tx_meter_percent,

            "age_seconds":
                activity.get(
                    "tx_age_seconds"
                ),

            "meter_mode":
                "activity",
        },

        "controls":
            controls[
                "controls"
            ],
    }
