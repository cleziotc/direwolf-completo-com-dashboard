import ipaddress
import os
import re
import subprocess
import time

from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

from audio_control import (
    get_audio_console_state,
    set_audio_gain,
)

from station_config import (
    load_station_config,
    get_station_capabilities,
    save_station_section,
)

from offline_maps import (
    estimate_offline_map,
    start_offline_download,
    offline_map_status,
    offline_tile_path,
    delete_offline_package,
)

from database import (
    get_packet_rate,
    get_minute_activity,
    get_top_stations,
    get_recent_stations,
    get_weather_stations,
    get_station_detail,
    get_stats,
    get_tx_activity,
    get_kpi_trends,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

STARTED_AT = datetime.now(
    timezone.utc
)

_LAST_CPU_SAMPLE = None


def _read_cpu_sample():

    try:

        first = (
            Path(
                "/proc/stat"
            )
            .read_text()
            .splitlines()[0]
            .split()
        )

        if (
            not first
            or
            first[0] != "cpu"
        ):

            return None

        values = [
            int(
                value
            )
            for value in first[1:]
        ]

        if len(
            values
        ) < 4:

            return None

        idle = (
            values[3]
            + (
                values[4]
                if len(
                    values
                ) > 4
                else 0
            )
        )

        total = sum(
            values
        )

        return (
            total,
            idle,
        )

    except Exception:

        return None


def _cpu_percent():

    global _LAST_CPU_SAMPLE

    current = _read_cpu_sample()

    if current is None:

        return None

    previous = _LAST_CPU_SAMPLE

    if previous is None:

        _LAST_CPU_SAMPLE = current

        time.sleep(
            0.05
        )

        current = _read_cpu_sample()

        previous = _LAST_CPU_SAMPLE

        if current is None:

            return None

    _LAST_CPU_SAMPLE = current

    total_delta = (
        current[0]
        - previous[0]
    )

    idle_delta = (
        current[1]
        - previous[1]
    )

    if total_delta <= 0:

        return 0.0

    busy = (
        total_delta
        - idle_delta
    )

    return round(
        max(
            0.0,
            min(
                100.0,
                busy
                / total_delta
                * 100.0
            )
        ),
        1
    )


def _memory_status():

    try:

        values = {}

        for line in (
            Path(
                "/proc/meminfo"
            )
            .read_text()
            .splitlines()
        ):

            if ":" not in line:

                continue

            key, raw = line.split(
                ":",
                1
            )

            number = (
                raw.strip()
                .split()[0]
            )

            values[
                key
            ] = int(
                number
            )

        total_kb = values.get(
            "MemTotal"
        )

        available_kb = values.get(
            "MemAvailable"
        )

        if (
            not total_kb
            or
            available_kb is None
        ):

            return {
                "percent":
                    None,

                "used_mb":
                    None,

                "total_mb":
                    None,
            }

        used_kb = max(
            0,
            total_kb
            - available_kb
        )

        return {
            "percent":
                round(
                    used_kb
                    / total_kb
                    * 100.0,
                    1
                ),

            "used_mb":
                round(
                    used_kb
                    / 1024.0,
                    1
                ),

            "total_mb":
                round(
                    total_kb
                    / 1024.0,
                    1
                ),
        }

    except Exception:

        return {
            "percent":
                None,

            "used_mb":
                None,

            "total_mb":
                None,
        }


def get_system_resources():

    memory = _memory_status()

    return {
        "cpu_percent":
            _cpu_percent(),

        "ram_percent":
            memory[
                "percent"
            ],

        "ram_used_mb":
            memory[
                "used_mb"
            ],

        "ram_total_mb":
            memory[
                "total_mb"
            ],
    }


def dashboard_uptime_seconds():

    return max(
        0,
        int(
            (
                datetime.now(
                    timezone.utc
                )
                - STARTED_AT
            ).total_seconds()
        )
    )


def systemd_service_uptime_seconds(
    service_name: str
):

    try:

        state = subprocess.run(
            [
                "systemctl",
                "is-active",
                "--quiet",
                service_name
            ],
            timeout=2
        )

        if state.returncode != 0:
            return None

        result = subprocess.run(
            [
                "systemctl",
                "show",
                service_name,
                "--property=ActiveEnterTimestampMonotonic",
                "--value"
            ],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode != 0:
            return None

        value = result.stdout.strip()

        if not value:
            return None

        active_enter_us = int(
            value
        )

        if active_enter_us <= 0:
            return None

        host_uptime_seconds = float(
            Path(
                "/proc/uptime"
            )
            .read_text()
            .split()[0]
        )

        service_started_seconds = (
            active_enter_us
            / 1_000_000.0
        )

        return max(
            0,
            int(
                host_uptime_seconds
                - service_started_seconds
            )
        )

    except Exception:

        return None


def direwolf_tx_config_status():

    config_path = Path(
        os.environ.get(
            "DIREWOLF_CONFIG",
            "/home/aprs/direwolf.conf"
        )
    )

    try:

        lines = (
            config_path
            .read_text(
                errors="replace"
            )
            .splitlines()
        )

    except OSError:

        return {
            "enabled":
                False,

            "igate_rx":
                False,

            "igate_tx":
                False,

            "igate_mode":
                "OFF",

            "ig_to_rf":
                False,

            "digipeater":
                False,

            "rf_beacon":
                False,
        }

    active_lines = []

    for line in lines:

        stripped = line.strip()

        if (
            not stripped
            or
            stripped.startswith(
                "#"
            )
        ):
            continue

        active_lines.append(
            stripped
        )

    igate_rx = (
        any(
            line.upper().startswith(
                "IGLOGIN "
            )
            for line in active_lines
        )
        and
        any(
            line.upper().startswith(
                "IGSERVER "
            )
            for line in active_lines
        )
    )

    ig_to_rf = any(
        line.upper().startswith(
            "IGTXVIA "
        )
        for line in active_lines
    )

    if (
        igate_rx
        and ig_to_rf
    ):

        igate_mode = (
            "RX + TX"
        )

    elif igate_rx:

        igate_mode = (
            "RX"
        )

    elif ig_to_rf:

        igate_mode = (
            "TX"
        )

    else:

        igate_mode = (
            "OFF"
        )

    digipeater = any(
        line.upper().startswith(
            "DIGIPEAT "
        )
        for line in active_lines
    )

    rf_beacon = any(
        line.upper().startswith(
            "OBEACON "
        )
        and "SENDTO=0" in line.upper()
        for line in active_lines
    )

    return {
        "enabled":
            (
                ig_to_rf
                or
                digipeater
                or
                rf_beacon
            ),

        "igate_rx":
            igate_rx,

        "igate_tx":
            ig_to_rf,

        "igate_mode":
            igate_mode,

        "ig_to_rf":
            ig_to_rf,

        "digipeater":
            digipeater,

        "rf_beacon":
            rf_beacon,
    }


def request_is_local(
    request
):

    try:

        address = ipaddress.ip_address(
            request.client.host
        )

        return (
            address.is_private
            or
            address.is_loopback
        )

    except Exception:

        return False


def register_routes(app):

    @app.get(
        "/static/vendor/leaflet/{filename}",
        include_in_schema=False
    )
    def dashboard_leaflet_vendor(
        filename: str
    ):

        allowed = {
            "leaflet.js":
                "application/javascript",

            "leaflet.css":
                "text/css",
        }

        media_type = allowed.get(
            filename
        )

        if media_type is None:

            raise HTTPException(
                status_code=404,
                detail="Arquivo não encontrado."
            )

        path = (
            STATIC_DIR
            / "vendor"
            / "leaflet"
            / filename
        )

        if not path.exists():

            raise HTTPException(
                status_code=404,
                detail="Leaflet local ainda não instalado."
            )

        return FileResponse(
            path,
            media_type=media_type
        )


    @app.get(
        "/static/dashboard-v2.css",
        include_in_schema=False
    )
    def dashboard_v2_css():

        return FileResponse(
            STATIC_DIR /
            "dashboard-v2.css",
            media_type="text/css"
        )


    @app.get(
        "/static/dashboard-v2.js",
        include_in_schema=False
    )
    def dashboard_v2_js():

        return FileResponse(
            STATIC_DIR /
            "dashboard-v2.js",
            media_type="application/javascript"
        )


    @app.get(
        "/config",
        include_in_schema=False
    )
    def dashboard_config_page():

        return FileResponse(
            STATIC_DIR /
            "config.html",
            media_type="text/html"
        )


    @app.get(
        "/api/station-config"
    )
    def dashboard_station_config():

        return load_station_config()


    @app.get(
        "/api/station-config/capabilities"
    )
    def dashboard_station_capabilities():

        return get_station_capabilities()


    @app.post(
        "/api/station-config/{section}"
    )
    def dashboard_station_config_save(
        section: str,
        payload: dict,
        request: Request
    ):

        if not request_is_local(
            request
        ):

            raise HTTPException(
                status_code=403,
                detail="Alterações de configuração são permitidas somente pela rede local."
            )

        try:

            return save_station_section(
                section,
                payload
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc)
            )

        except RuntimeError as exc:

            raise HTTPException(
                status_code=503,
                detail=str(exc)
            )


    @app.get(
        "/api/offline-map/status"
    )
    def dashboard_offline_map_status():

        return offline_map_status()


    @app.post(
        "/api/offline-map/estimate"
    )
    def dashboard_offline_map_estimate(
        payload: dict
    ):

        try:

            return estimate_offline_map(
                str(
                    payload.get(
                        "kind"
                    )
                    or ""
                ).strip().lower(),
                payload.get(
                    "latitude"
                ),
                payload.get(
                    "longitude"
                ),
                payload.get(
                    "radius_km"
                ),
                payload.get(
                    "max_zoom"
                ),
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc)
            )


    @app.post(
        "/api/offline-map/download"
    )
    def dashboard_offline_map_download(
        payload: dict,
        request: Request
    ):

        if not request_is_local(
            request
        ):

            raise HTTPException(
                status_code=403,
                detail="Download de mapa offline permitido somente pela rede local."
            )

        try:

            return start_offline_download(
                payload
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc)
            )

        except RuntimeError as exc:

            raise HTTPException(
                status_code=409,
                detail=str(exc)
            )


    @app.delete(
        "/api/offline-map/{kind}"
    )
    def dashboard_offline_map_delete(
        kind: str,
        request: Request
    ):

        if not request_is_local(
            request
        ):

            raise HTTPException(
                status_code=403,
                detail="Exclusão de mapa offline permitida somente pela rede local."
            )

        try:

            return delete_offline_package(
                kind.strip().lower()
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc)
            )

        except RuntimeError as exc:

            raise HTTPException(
                status_code=409,
                detail=str(exc)
            )


    @app.get(
        "/offline-map/{kind}/{zoom}/{x}/{y}.jpg",
        include_in_schema=False
    )
    def dashboard_offline_tile(
        kind: str,
        zoom: int,
        x: int,
        y: int
    ):

        path = offline_tile_path(
            kind.strip().lower(),
            zoom,
            x,
            y
        )

        if path is None:

            raise HTTPException(
                status_code=404,
                detail="Tile offline não encontrado."
            )

        return FileResponse(
            path,
            media_type="image/jpeg"
        )


    @app.get(
        "/api/audio"
    )
    def dashboard_audio_state():

        return get_audio_console_state()


    @app.post(
        "/api/audio/gain/{role}"
    )
    def dashboard_audio_gain(
        role: str,
        percent: int
    ):

        try:

            return set_audio_gain(
                role,
                percent
            )

        except ValueError as exc:

            raise HTTPException(
                status_code=400,
                detail=str(exc)
            )

        except RuntimeError as exc:

            raise HTTPException(
                status_code=503,
                detail=str(exc)
            )


    @app.get(
        "/api/overview"
    )
    def dashboard_overview():

        tx_config = (
            direwolf_tx_config_status()
        )

        tx_activity = (
            get_tx_activity(
                60
            )
        )

        stats = (
            get_stats()
        )

        return {
            "time":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "packet_rate":
                get_packet_rate(),

            "kpi_trends":
                get_kpi_trends(
                    60
                ),

            "minute_activity":
                get_minute_activity(
                    60
                ),

            "top_stations":
                get_top_stations(
                    hours=1,
                    limit=5
                ),

            "recent_stations":
                get_recent_stations(
                    hours=24,
                    limit=10
                ),

            "weather_stations":
                get_weather_stations(
                    hours=24,
                    limit=12
                ),

            "tx": {
                **tx_config,

                "is_to_rf_today":
                    tx_activity[
                        "is_to_rf_today"
                    ],

                "tx_rf_today":
                    stats.get(
                        "tx_rf",
                        0
                    ),

                "minute_activity":
                    tx_activity[
                        "series"
                    ],
            },

            "uptime": {
                "dashboard_seconds":
                    dashboard_uptime_seconds(),

                "direwolf_seconds":
                    systemd_service_uptime_seconds(
                        "direwolf"
                    ),
            },

            "system":
                get_system_resources(),
        }


    @app.get(
        "/api/station/{callsign}"
    )
    def dashboard_station_detail(
        callsign: str,
        hours: int = 24
    ):

        normalized = (
            callsign
            .strip()
            .upper()
        )

        if not re.fullmatch(
            r"[A-Z0-9-]{1,15}",
            normalized
        ):

            raise HTTPException(
                status_code=400,
                detail="Indicativo invalido"
            )

        detail = get_station_detail(
            normalized,
            hours=hours
        )

        if detail is None:

            raise HTTPException(
                status_code=404,
                detail="Estacao nao encontrada no periodo"
            )

        return detail
