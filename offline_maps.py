import json
import math
import os
import shutil
import threading
import time
import urllib.error
import urllib.request

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent

BASE_DIR = Path(
    os.environ.get(
        "APRS_OFFLINE_MAP_DIR",
        str(MODULE_DIR / "data" / "offline-maps")
    )
)

META_PATH = BASE_DIR / "metadata.json"

MAX_TILES = 40000

SOURCES = {
    "streets": {
        "label": "Ruas",
        "layer": "osm_3857",
        "extension": "jpg",
        "max_zoom": 15,
        "attribution": "OpenStreetMap contributors • rendering EOX",
    },
    "satellite": {
        "label": "Satélite",
        "layer": "s2cloudless-2025_3857",
        "extension": "jpg",
        "max_zoom": 14,
        "attribution": "Sentinel-2 cloudless 2025 by EOX IT Services GmbH (modified Copernicus Sentinel data 2025)",
    },
}

_state_lock = threading.Lock()

_runtime_state = {
    "active": False,
    "kind": None,
    "done": 0,
    "total": 0,
    "failed": 0,
    "message": "",
    "started_at": None,
    "finished_at": None,
}


def _load_metadata():

    if not META_PATH.exists():

        return {
            "packages": {}
        }

    try:

        return json.loads(
            META_PATH.read_text()
        )

    except Exception:

        return {
            "packages": {}
        }


def _save_metadata(
    data
):

    BASE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    tmp = META_PATH.with_suffix(
        ".tmp"
    )

    tmp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )
    )

    tmp.replace(
        META_PATH
    )


def _tile_xy(
    lat,
    lon,
    zoom
):

    lat = max(
        -85.05112878,
        min(
            85.05112878,
            float(
                lat
            )
        )
    )

    lon = max(
        -180.0,
        min(
            180.0,
            float(
                lon
            )
        )
    )

    n = 2 ** int(
        zoom
    )

    x = (
        lon
        + 180.0
    ) / 360.0 * n

    lat_rad = math.radians(
        lat
    )

    y = (
        1.0
        - math.asinh(
            math.tan(
                lat_rad
            )
        )
        / math.pi
    ) / 2.0 * n

    return (
        int(
            math.floor(
                x
            )
        ),
        int(
            math.floor(
                y
            )
        ),
    )


def _bbox_for_radius(
    lat,
    lon,
    radius_km
):

    lat = float(
        lat
    )

    lon = float(
        lon
    )

    radius_km = float(
        radius_km
    )

    dlat = (
        radius_km
        / 111.32
    )

    cos_lat = max(
        0.05,
        abs(
            math.cos(
                math.radians(
                    lat
                )
            )
        )
    )

    dlon = (
        radius_km
        / (
            111.32
            * cos_lat
        )
    )

    return (
        max(
            -85.0,
            lat - dlat
        ),
        max(
            -180.0,
            lon - dlon
        ),
        min(
            85.0,
            lat + dlat
        ),
        min(
            180.0,
            lon + dlon
        ),
    )


def _tile_ranges(
    lat,
    lon,
    radius_km,
    max_zoom
):

    min_lat, min_lon, max_lat, max_lon = (
        _bbox_for_radius(
            lat,
            lon,
            radius_km
        )
    )

    ranges = []

    total = 0

    for zoom in range(
        0,
        int(
            max_zoom
        )
        + 1
    ):

        min_x, max_y = _tile_xy(
            min_lat,
            min_lon,
            zoom
        )

        max_x, min_y = _tile_xy(
            max_lat,
            max_lon,
            zoom
        )

        n = (
            2 ** zoom
        )

        min_x = max(
            0,
            min(
                n - 1,
                min_x
            )
        )

        max_x = max(
            0,
            min(
                n - 1,
                max_x
            )
        )

        min_y = max(
            0,
            min(
                n - 1,
                min_y
            )
        )

        max_y = max(
            0,
            min(
                n - 1,
                max_y
            )
        )

        if max_x < min_x:

            min_x, max_x = (
                max_x,
                min_x,
            )

        if max_y < min_y:

            min_y, max_y = (
                max_y,
                min_y,
            )

        count = (
            max_x
            - min_x
            + 1
        ) * (
            max_y
            - min_y
            + 1
        )

        total += count

        ranges.append(
            {
                "zoom":
                    zoom,

                "min_x":
                    min_x,

                "max_x":
                    max_x,

                "min_y":
                    min_y,

                "max_y":
                    max_y,

                "count":
                    count,
            }
        )

    return (
        ranges,
        total,
    )


def estimate_offline_map(
    kind,
    latitude,
    longitude,
    radius_km,
    max_zoom
):

    if kind not in SOURCES:

        raise ValueError(
            "Tipo de mapa inválido."
        )

    latitude = float(
        latitude
    )

    longitude = float(
        longitude
    )

    radius_km = float(
        radius_km
    )

    max_zoom = int(
        max_zoom
    )

    source = SOURCES[
        kind
    ]

    if not (
        -90
        <= latitude
        <= 90
    ):

        raise ValueError(
            "Latitude inválida."
        )

    if not (
        -180
        <= longitude
        <= 180
    ):

        raise ValueError(
            "Longitude inválida."
        )

    if not (
        1
        <= radius_km
        <= 500
    ):

        raise ValueError(
            "Raio offline deve ficar entre 1 e 500 km."
        )

    if not (
        0
        <= max_zoom
        <= source[
            "max_zoom"
        ]
    ):

        raise ValueError(
            "Nível máximo de zoom inválido para este mapa."
        )

    ranges, total = _tile_ranges(
        latitude,
        longitude,
        radius_km,
        max_zoom
    )

    # Estimativa deliberadamente conservadora. Os JPEGs variam
    # bastante conforme o conteúdo.
    average_kb = (
        34
        if kind == "streets"
        else 52
    )

    estimated_mb = (
        total
        * average_kb
        / 1024.0
    )

    return {
        "kind":
            kind,

        "label":
            source[
                "label"
            ],

        "latitude":
            latitude,

        "longitude":
            longitude,

        "radius_km":
            radius_km,

        "max_zoom":
            max_zoom,

        "tile_count":
            total,

        "estimated_mb":
            round(
                estimated_mb,
                1
            ),

        "allowed":
            total
            <= MAX_TILES,

        "max_tiles":
            MAX_TILES,

        "ranges":
            ranges,
    }


def _tile_url(
    kind,
    zoom,
    x,
    y
):

    source = SOURCES[
        kind
    ]

    return (
        "https://tiles.maps.eox.at/"
        "wmts/1.0.0/"
        + source[
            "layer"
        ]
        + "/default/g/"
        + str(
            zoom
        )
        + "/"
        + str(
            y
        )
        + "/"
        + str(
            x
        )
        + "."
        + source[
            "extension"
        ]
    )


def _download_one(
    kind,
    zoom,
    x,
    y
):

    source = SOURCES[
        kind
    ]

    target = (
        BASE_DIR
        / kind
        / str(
            zoom
        )
        / str(
            x
        )
        / (
            str(
                y
            )
            + "."
            + source[
                "extension"
            ]
        )
    )

    if (
        target.exists()
        and
        target.stat().st_size
        > 200
    ):

        return (
            True,
            False,
        )

    target.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    request = urllib.request.Request(
        _tile_url(
            kind,
            zoom,
            x,
            y
        ),
        headers={
            "User-Agent":
                "Direwolf-APRS-Dashboard/1.0 offline-map-cache",
        },
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            data = response.read()

    except Exception:

        return (
            False,
            False,
        )

    if len(
        data
    ) < 200:

        return (
            False,
            False,
        )

    tmp = target.with_suffix(
        target.suffix
        + ".tmp"
    )

    tmp.write_bytes(
        data
    )

    tmp.replace(
        target
    )

    return (
        True,
        True,
    )


def _iter_tiles(
    ranges
):

    for item in ranges:

        zoom = item[
            "zoom"
        ]

        for x in range(
            item[
                "min_x"
            ],
            item[
                "max_x"
            ]
            + 1
        ):

            for y in range(
                item[
                    "min_y"
                ],
                item[
                    "max_y"
                ]
                + 1
            ):

                yield (
                    zoom,
                    x,
                    y,
                )


def _package_size_bytes(
    kind
):

    root = (
        BASE_DIR
        / kind
    )

    if not root.exists():

        return 0

    total = 0

    for path in root.rglob(
        "*"
    ):

        if path.is_file():

            try:

                total += (
                    path.stat()
                    .st_size
                )

            except OSError:

                pass

    return total


def _download_worker(
    estimate
):

    kind = estimate[
        "kind"
    ]

    ranges = estimate[
        "ranges"
    ]

    total = estimate[
        "tile_count"
    ]

    with _state_lock:

        _runtime_state.update(
            {
                "active":
                    True,

                "kind":
                    kind,

                "done":
                    0,

                "total":
                    total,

                "failed":
                    0,

                "message":
                    "Baixando mapa offline...",

                "started_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "finished_at":
                    None,
            }
        )

    downloaded = 0

    failed = 0

    tasks = list(
        _iter_tiles(
            ranges
        )
    )

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:

        futures = [
            executor.submit(
                _download_one,
                kind,
                zoom,
                x,
                y
            )
            for zoom, x, y in tasks
        ]

        for future in as_completed(
            futures
        ):

            try:

                ok, fresh = future.result()

            except Exception:

                ok = False
                fresh = False

            if ok:

                if fresh:

                    downloaded += 1

            else:

                failed += 1

            with _state_lock:

                _runtime_state[
                    "done"
                ] += 1

                _runtime_state[
                    "failed"
                ] = failed

    metadata = _load_metadata()

    metadata.setdefault(
        "packages",
        {}
    )

    metadata[
        "packages"
    ][
        kind
    ] = {
        "kind":
            kind,

        "label":
            SOURCES[
                kind
            ][
                "label"
            ],

        "latitude":
            estimate[
                "latitude"
            ],

        "longitude":
            estimate[
                "longitude"
            ],

        "radius_km":
            estimate[
                "radius_km"
            ],

        "max_zoom":
            estimate[
                "max_zoom"
            ],

        "tile_count":
            total
            - failed,

        "failed":
            failed,

        "size_bytes":
            _package_size_bytes(
                kind
            ),

        "updated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "attribution":
            SOURCES[
                kind
            ][
                "attribution"
            ],
    }

    _save_metadata(
        metadata
    )

    with _state_lock:

        _runtime_state.update(
            {
                "active":
                    False,

                "message":
                    (
                        "Mapa offline concluído."
                        if failed == 0
                        else
                        "Mapa offline concluído com algumas falhas."
                    ),

                "finished_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            }
        )


def start_offline_download(
    payload
):

    kind = str(
        payload.get(
            "kind"
        )
        or ""
    ).strip().lower()

    estimate = estimate_offline_map(
        kind,
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

    if not estimate[
        "allowed"
    ]:

        raise ValueError(
            (
                "A área escolhida geraria "
                + str(
                    estimate[
                        "tile_count"
                    ]
                )
                + " tiles. Reduza o raio ou o zoom máximo."
            )
        )

    with _state_lock:

        if _runtime_state[
            "active"
        ]:

            raise RuntimeError(
                "Já existe um download de mapa offline em andamento."
            )

    thread = threading.Thread(
        target=_download_worker,
        args=(
            estimate,
        ),
        daemon=True,
        name=(
            "offline-map-"
            + kind
        ),
    )

    thread.start()

    return {
        "started":
            True,

        "estimate":
            estimate,
    }


def offline_map_status():

    metadata = _load_metadata()

    packages = metadata.get(
        "packages",
        {}
    )

    for kind, package in packages.items():

        package[
            "size_mb"
        ] = round(
            package.get(
                "size_bytes",
                0
            )
            / 1024.0
            / 1024.0,
            1
        )

    with _state_lock:

        runtime = dict(
            _runtime_state
        )

    if runtime[
        "total"
    ]:

        runtime[
            "progress_percent"
        ] = round(
            runtime[
                "done"
            ]
            / runtime[
                "total"
            ]
            * 100.0,
            1
        )

    else:

        runtime[
            "progress_percent"
        ] = 0.0

    return {
        "packages":
            packages,

        "download":
            runtime,

        "sources": {
            kind: {
                "label":
                    value[
                        "label"
                    ],

                "max_zoom":
                    value[
                        "max_zoom"
                    ],

                "attribution":
                    value[
                        "attribution"
                    ],
            }
            for kind, value in SOURCES.items()
        },
    }


def offline_tile_path(
    kind,
    zoom,
    x,
    y
):

    if kind not in SOURCES:

        return None

    try:

        zoom = int(
            zoom
        )

        x = int(
            x
        )

        y = int(
            y
        )

    except Exception:

        return None

    if (
        zoom < 0
        or
        x < 0
        or
        y < 0
    ):

        return None

    source = SOURCES[
        kind
    ]

    path = (
        BASE_DIR
        / kind
        / str(
            zoom
        )
        / str(
            x
        )
        / (
            str(
                y
            )
            + "."
            + source[
                "extension"
            ]
        )
    )

    try:

        resolved = path.resolve()

        root = (
            BASE_DIR
            / kind
        ).resolve()

        resolved.relative_to(
            root
        )

    except Exception:

        return None

    if not resolved.exists():

        return None

    return resolved


def delete_offline_package(
    kind
):

    if kind not in SOURCES:

        raise ValueError(
            "Tipo de mapa inválido."
        )

    with _state_lock:

        if (
            _runtime_state[
                "active"
            ]
            and
            _runtime_state[
                "kind"
            ]
            == kind
        ):

            raise RuntimeError(
                "Não é possível excluir o mapa enquanto o download está ativo."
            )

    root = (
        BASE_DIR
        / kind
    )

    if root.exists():

        shutil.rmtree(
            root
        )

    metadata = _load_metadata()

    metadata.setdefault(
        "packages",
        {}
    ).pop(
        kind,
        None
    )

    _save_metadata(
        metadata
    )

    return {
        "deleted":
            True,

        "kind":
            kind,
    }
