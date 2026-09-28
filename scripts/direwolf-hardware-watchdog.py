#!/usr/bin/env python3

import os
import re
import subprocess
import time

from datetime import datetime
from pathlib import Path


CONFIG_PATH = Path(
    os.environ.get(
        "DIREWOLF_CONFIG",
        "/home/aprs/direwolf.conf"
    )
)
POLL_SECONDS = 2.0
RECONNECT_SETTLE_SECONDS = 1.5
RESTART_COOLDOWN_SECONDS = 6.0


def log(message):

    stamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    print(
        f"[{stamp}] {message}",
        flush=True
    )


def read_config():

    try:

        lines = CONFIG_PATH.read_text(
            errors="replace"
        ).splitlines()

    except OSError:

        return {
            "audio_device": None,
            "ptt_mode": "none",
            "ptt_device": None,
            "ptt_line": None,
        }

    audio_device = None
    ptt_mode = "none"
    ptt_device = None
    ptt_line = None

    for raw in lines:

        line = raw.strip()

        if (
            not line
            or line.startswith("#")
        ):

            continue

        upper = line.upper()

        if (
            audio_device is None
            and upper.startswith("ADEVICE ")
        ):

            parts = line.split()

            if len(parts) >= 2:

                audio_device = parts[1]

        elif (
            ptt_mode == "none"
            and upper.startswith("PTT ")
        ):

            parts = line.split()

            if (
                len(parts) >= 4
                and parts[1].upper() == "GPIOD"
            ):

                ptt_mode = "gpiod"
                ptt_device = parts[2]

                if not ptt_device.startswith("/"):

                    ptt_device = (
                        "/dev/"
                        + ptt_device
                    )

                ptt_line = parts[3]

            elif len(parts) >= 3:

                ptt_mode = "serial"
                ptt_device = parts[1]

    return {
        "audio_device": audio_device,
        "ptt_mode": ptt_mode,
        "ptt_device": ptt_device,
        "ptt_line": ptt_line,
    }


def parse_numeric_alsa_device(
    value
):

    if not value:

        return None

    match = re.fullmatch(
        r"(?:plug)?hw:(\d+),(\d+)",
        value,
        re.IGNORECASE
    )

    if not match:

        return None

    return (
        int(
            match.group(1)
        ),
        int(
            match.group(2)
        ),
    )


def audio_present(
    value
):

    if not value:

        return False

    numeric = parse_numeric_alsa_device(
        value
    )

    try:

        result = subprocess.run(
            [
                "arecord",
                "-l",
            ],
            capture_output=True,
            text=True,
            timeout=4,
        )

    except Exception:

        return False

    listing = (
        result.stdout
        + "\n"
        + result.stderr
    )

    if numeric is not None:

        card, device = numeric

        pattern = re.compile(
            rf"card\s+{card}:.*device\s+{device}:",
            re.IGNORECASE
        )

        return bool(
            pattern.search(
                listing
            )
        )

    # Para formatos ALSA não numéricos, ao menos confirma que
    # a enumeração de captura existe. O Direwolf fará a validação final.
    return (
        result.returncode
        == 0
        and "card " in listing.lower()
    )


def ptt_present(
    mode,
    device
):

    if mode == "none":

        return True

    if not device:

        return False

    if mode in (
        "serial",
        "gpiod",
    ):

        try:

            return Path(
                device
            ).exists()

        except Exception:

            return False

    return False


def service_active():

    try:

        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "--quiet",
                "direwolf.service",
            ],
            timeout=5,
        )

    except Exception:

        return False

    return (
        result.returncode
        == 0
    )


def restart_direwolf(
    reason
):

    log(
        "Reiniciando Direwolf: "
        + reason
    )

    try:

        result = subprocess.run(
            [
                "systemctl",
                "restart",
                "direwolf.service",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )

    except Exception as exc:

        log(
            "Falha ao executar restart: "
            + str(exc)
        )

        return False

    if result.returncode != 0:

        detail = (
            result.stderr
            or result.stdout
            or ""
        ).strip()

        log(
            "Restart retornou erro"
            + (
                ": "
                + detail
                if detail
                else "."
            )
        )

        return False

    time.sleep(
        1.0
    )

    if service_active():

        log(
            "Direwolf ativo novamente."
        )

        return True

    log(
        "Direwolf ainda está inativo após o restart."
    )

    return False


def main():

    log(
        "Watchdog de hardware do Direwolf iniciado."
    )

    previous_audio = None
    previous_ptt = None
    last_restart = 0.0

    while True:

        config = read_config()

        audio_device = config.get(
            "audio_device"
        )

        ptt_mode = config.get(
            "ptt_mode",
            "none"
        )

        ptt_device = config.get(
            "ptt_device"
        )

        audio_required = bool(
            audio_device
        )

        ptt_required = (
            ptt_mode
            != "none"
        )

        audio_ok = (
            audio_present(
                audio_device
            )
            if audio_required
            else True
        )

        ptt_ok = (
            ptt_present(
                ptt_mode,
                ptt_device
            )
            if ptt_required
            else True
        )

        now = time.monotonic()

        if (
            audio_required
            and previous_audio is not None
            and previous_audio != audio_ok
        ):

            log(
                (
                    "Áudio reconectado: "
                    if audio_ok
                    else "Áudio desconectado: "
                )
                + str(
                    audio_device
                )
            )

        if (
            ptt_required
            and previous_ptt is not None
            and previous_ptt != ptt_ok
        ):

            label = (
                "GPIO/PTT"
                if ptt_mode == "gpiod"
                else "Serial/PTT"
            )

            log(
                (
                    label
                    + " reconectado: "
                    if ptt_ok
                    else label
                    + " desconectado: "
                )
                + str(
                    ptt_device
                )
            )

        audio_reconnected = (
            previous_audio is False
            and audio_ok
        )

        ptt_reconnected = (
            previous_ptt is False
            and ptt_ok
        )

        all_ready = (
            audio_ok
            and ptt_ok
        )

        cooldown_ok = (
            now
            - last_restart
            >= RESTART_COOLDOWN_SECONDS
        )

        if (
            all_ready
            and cooldown_ok
            and (
                audio_reconnected
                or ptt_reconnected
            )
        ):

            time.sleep(
                RECONNECT_SETTLE_SECONDS
            )

            if restart_direwolf(
                "hardware reconectado"
            ):

                last_restart = (
                    time.monotonic()
                )

        elif (
            all_ready
            and cooldown_ok
            and not service_active()
        ):

            if restart_direwolf(
                "serviço inativo com hardware disponível"
            ):

                last_restart = (
                    time.monotonic()
                )

        previous_audio = audio_ok
        previous_ptt = ptt_ok

        time.sleep(
            POLL_SECONDS
        )


if __name__ == "__main__":

    main()
