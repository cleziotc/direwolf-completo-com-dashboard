import json
import os
import sqlite3

from contextlib import closing
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "aprs.db"

LOCAL_TIMEZONE = ZoneInfo(
    os.environ.get("APRS_TIMEZONE", "UTC")
)


# ============================================================
# CONEXAO
# ============================================================

def get_connection():

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        DB_PATH,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# INICIALIZACAO DO BANCO
# ============================================================

def init_db():

    with closing(
        get_connection()
    ) as conn:

        conn.execute(
            "PRAGMA journal_mode=WAL"
        )

        conn.execute(
            "PRAGMA synchronous=NORMAL"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                type TEXT NOT NULL,
                callsign TEXT,
                packet TEXT,
                raw TEXT NOT NULL,
                level INTEGER,
                detail TEXT,
                decoder TEXT,
                direwolf_time TEXT,
                extra_json TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_time
            ON events(time)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_type
            ON events(type)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_callsign
            ON events(callsign)
            """
        )

        conn.commit()


# ============================================================
# GRAVACAO DE EVENTOS
# ============================================================

def insert_event(event):

    known_fields = {
        "time",
        "type",
        "callsign",
        "packet",
        "raw",
        "level",
        "detail",
        "decoder",
        "direwolf_time",
    }

    extra = {
        key: value
        for key, value in event.items()
        if key not in known_fields
    }

    with closing(
        get_connection()
    ) as conn:

        conn.execute(
            """
            INSERT INTO events (
                time,
                type,
                callsign,
                packet,
                raw,
                level,
                detail,
                decoder,
                direwolf_time,
                extra_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.get("time"),
                event.get("type"),
                event.get("callsign"),
                event.get("packet"),
                event.get("raw"),
                event.get("level"),
                event.get("detail"),
                event.get("decoder"),
                event.get("direwolf_time"),

                json.dumps(
                    extra,
                    ensure_ascii=False
                ) if extra else None,
            )
        )

        conn.commit()


# ============================================================
# RECUPERACAO / CONTINUIDADE DO HISTORICO
# ============================================================

def get_last_event_time():

    with closing(
        get_connection()
    ) as conn:

        row = conn.execute(
            """
            SELECT MAX(time) AS last_time
            FROM events
            """
        ).fetchone()

    if not row:
        return None

    return row[
        "last_time"
    ]


def insert_event_if_missing(
    event,
    tolerance_seconds=3
):

    event_time = event.get(
        "time"
    )

    raw = event.get(
        "raw"
    )

    event_type = event.get(
        "type"
    )

    if (
        not event_time
        or
        raw is None
        or
        event_type is None
    ):

        insert_event(
            event
        )

        return True

    try:

        parsed_time = datetime.fromisoformat(
            event_time
        )

    except Exception:

        insert_event(
            event
        )

        return True

    if parsed_time.tzinfo is None:

        parsed_time = parsed_time.replace(
            tzinfo=timezone.utc
        )

    parsed_time = parsed_time.astimezone(
        timezone.utc
    )

    tolerance = timedelta(
        seconds=max(
            0,
            int(
                tolerance_seconds
            )
        )
    )

    start = (
        parsed_time
        - tolerance
    ).isoformat()

    end = (
        parsed_time
        + tolerance
    ).isoformat()

    with closing(
        get_connection()
    ) as conn:

        existing = conn.execute(
            """
            SELECT 1

            FROM events

            WHERE type = ?
              AND raw = ?
              AND time >= ?
              AND time <= ?

            LIMIT 1
            """,
            (
                event_type,
                raw,
                start,
                end,
            )
        ).fetchone()

    if existing:

        return False

    insert_event(
        event
    )

    return True


# ============================================================
# PERIODO DO DIA ATUAL
# ============================================================

def get_today_period_utc():

    now_local = datetime.now(
        LOCAL_TIMEZONE
    )

    start_local = now_local.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    end_local = (
        start_local
        + timedelta(days=1)
    )

    start_utc = (
        start_local.astimezone(
            timezone.utc
        )
    )

    end_utc = (
        end_local.astimezone(
            timezone.utc
        )
    )

    return (
        start_utc,
        end_utc
    )


# ============================================================
# ESTATISTICAS DO DIA
# ============================================================

def get_stats(hours=24):

    start_utc, end_utc = (
        get_today_period_utc()
    )

    with closing(
        get_connection()
    ) as conn:

        row = conn.execute(
            """
            SELECT

                COUNT(
                    CASE
                        WHEN type = 'RF_RX'
                        THEN 1
                    END
                ) AS rf_rx,

                COUNT(
                    CASE
                        WHEN type = 'RF_TO_IS'
                        THEN 1
                    END
                ) AS rf_to_is,

                COUNT(
                    CASE
                        WHEN type = 'IS_RX'
                        THEN 1
                    END
                ) AS is_rx,

                COUNT(
                    CASE
                        WHEN type = 'DUPLICATE_DROP'
                        THEN 1
                    END
                ) AS duplicate_drop,

                COUNT(
                    CASE
                        WHEN type = 'TX_RF'
                        THEN 1
                    END
                ) AS tx_rf,

                COUNT(
                    DISTINCT CASE
                        WHEN type = 'RF_RX'
                        THEN callsign
                    END
                ) AS unique_rf_stations

            FROM events

            WHERE time >= ?
              AND time < ?
            """,
            (
                start_utc.isoformat(),
                end_utc.isoformat(),
            )
        ).fetchone()

    return {

        "period":
            "today",

        "day_start_utc":
            start_utc.isoformat(),

        "rf_rx":
            row["rf_rx"] or 0,

        "rf_to_is":
            row["rf_to_is"] or 0,

        "is_rx":
            row["is_rx"] or 0,

        "duplicate_drop":
            row["duplicate_drop"] or 0,

        "tx_rf":
            row["tx_rf"] or 0,

        "unique_rf_stations":
            row["unique_rf_stations"] or 0,
    }


# ============================================================
# ATIVIDADE POR HORA
# ============================================================

def get_hourly_activity():

    start_utc, end_utc = (
        get_today_period_utc()
    )

    now_local = datetime.now(
        LOCAL_TIMEZONE
    )

    hours = []

    for hour in range(24):

        hours.append(
            {
                "hour":
                    f"{hour:02d}:00",

                "rf_rx":
                    0,

                "rf_to_is":
                    0,

                "is_rx":
                    0,
            }
        )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                time,
                type

            FROM events

            WHERE time >= ?
              AND time < ?

              AND type IN (
                  'RF_RX',
                  'RF_TO_IS',
                  'IS_RX'
              )

            ORDER BY time
            """,
            (
                start_utc.isoformat(),
                end_utc.isoformat(),
            )
        ).fetchall()

    for row in rows:

        try:

            event_time = (
                datetime.fromisoformat(
                    row["time"]
                )
            )

        except ValueError:

            continue

        if event_time.tzinfo is None:

            event_time = (
                event_time.replace(
                    tzinfo=timezone.utc
                )
            )

        local_time = (
            event_time.astimezone(
                LOCAL_TIMEZONE
            )
        )

        hour = (
            local_time.hour
        )

        event_type = (
            row["type"]
        )

        if event_type == "RF_RX":

            hours[
                hour
            ][
                "rf_rx"
            ] += 1

        elif event_type == "RF_TO_IS":

            hours[
                hour
            ][
                "rf_to_is"
            ] += 1

        elif event_type == "IS_RX":

            hours[
                hour
            ][
                "is_rx"
            ] += 1

    return {

        "date":
            now_local.date().isoformat(),

        "timezone":
            LOCAL_TIMEZONE.key,

        "hours":
            hours,
    }


# ============================================================
# EVENTOS RECENTES
# ============================================================

def get_recent_events(
    limit=60
):

    limit = int(
        limit
    )

    if limit < 1:
        limit = 1

    if limit > 500:
        limit = 500

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                time,
                type,
                callsign,
                packet,
                raw,
                level,
                detail,
                decoder,
                direwolf_time,
                extra_json

            FROM events

            WHERE type IN (
                'RF_RX',
                'RF_TO_IS',
                'IS_RX',
                'TX_RF',
                'AUDIO_LEVEL',
                'DUPLICATE_DROP'
            )

            ORDER BY id DESC

            LIMIT ?
            """,
            (
                limit,
            )
        ).fetchall()

    result = []

    for row in reversed(
        rows
    ):

        event = dict(
            row
        )

        extra_json = (
            event.pop(
                "extra_json",
                None
            )
        )

        if extra_json:

            try:

                extra = json.loads(
                    extra_json
                )

                event.update(
                    extra
                )

            except json.JSONDecodeError:

                pass

        result.append(
            event
        )

    return result


# ============================================================
# POSICOES PARA O MAPA
# ============================================================

def get_map_positions(
    hours=24,
    limit=250
):

    try:

        hours = int(
            hours
        )

    except Exception:

        hours = 24

    if hours < 1:
        hours = 1

    if hours > 168:
        hours = 168

    try:

        limit = int(
            limit
        )

    except Exception:

        limit = 250

    if limit < 1:
        limit = 1

    if limit > 1000:
        limit = 1000

    cutoff = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            hours=hours
        )
    )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                time,
                type,
                callsign,
                packet,
                extra_json

            FROM events

            WHERE time >= ?

              AND type IN (
                  'RF_RX',
                  'IS_RX'
              )

              AND callsign IS NOT NULL

              AND extra_json IS NOT NULL

              AND json_extract(
                    extra_json,
                    '$.latitude'
                  ) IS NOT NULL

              AND json_extract(
                    extra_json,
                    '$.longitude'
                  ) IS NOT NULL

            ORDER BY id DESC

            LIMIT 5000
            """,
            (
                cutoff.isoformat(),
            )
        ).fetchall()

    stations = {}

    rf_count = 0
    is_count = 0

    for row in rows:

        callsign = (
            row["callsign"]
            or ""
        ).strip().upper()

        if not callsign:

            continue

        if callsign in stations:

            continue

        try:

            extra = json.loads(
                row["extra_json"]
            )

        except Exception:

            continue

        latitude = extra.get(
            "latitude"
        )

        longitude = extra.get(
            "longitude"
        )

        if (
            latitude is None
            or
            longitude is None
        ):

            continue

        try:

            latitude = float(
                latitude
            )

            longitude = float(
                longitude
            )

        except Exception:

            continue

        if not (
            -90 <= latitude <= 90
            and
            -180 <= longitude <= 180
        ):

            continue

        event_type = (
            row["type"]
        )

        if event_type == "RF_RX":

            source = (
                "RF"
            )

            rf_count += 1

        else:

            source = (
                "APRS_IS"
            )

            is_count += 1

        is_weather = bool(
            extra.get(
                "is_weather",
                False
            )
        )

        weather = extra.get(
            "weather"
        )

        if not isinstance(
            weather,
            dict
        ):

            weather = None

        station = {

            "callsign":
                callsign,

            "source":
                source,

            "time":
                row["time"],

            "latitude":
                latitude,

            "longitude":
                longitude,

            "packet":
                row["packet"],

            "aprs_format":
                extra.get(
                    "aprs_format"
                ),

            "symbol":
                extra.get(
                    "symbol"
                ),

            "symbol_table":
                extra.get(
                    "symbol_table"
                ),

            "comment":
                extra.get(
                    "comment"
                ),

            "speed":
                extra.get(
                    "speed"
                ),

            "course":
                extra.get(
                    "course"
                ),

            "altitude":
                extra.get(
                    "altitude"
                ),

            "mic_e_status":
                extra.get(
                    "mic_e_status"
                ),

            "is_weather":
                is_weather,

            "weather":
                weather,

            "aprs_timestamp":
                extra.get(
                    "aprs_timestamp"
                ),

            "raw_timestamp":
                extra.get(
                    "raw_timestamp"
                ),
        }

        stations[
            callsign
        ] = station

        if len(
            stations
        ) >= limit:

            break

    return {

        "hours":
            hours,

        "count":
            len(
                stations
            ),

        "rf_count":
            rf_count,

        "is_count":
            is_count,

        "stations":
            list(
                stations.values()
            ),
    }

# ============================================================
# PAINEL OPERACIONAL / INTELIGENCIA DE ESTACOES
# ============================================================

def _bounded_int(value, default, minimum, maximum):

    try:
        value = int(value)
    except Exception:
        value = default

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def _decode_extra_json(value):

    if not value:
        return {}

    try:
        extra = json.loads(value)
    except Exception:
        return {}

    if not isinstance(extra, dict):
        return {}

    return extra


def get_packet_rate():

    now = datetime.now(
        timezone.utc
    )

    cutoff = (
        now
        - timedelta(seconds=60)
    )

    with closing(
        get_connection()
    ) as conn:

        row = conn.execute(
            """
            SELECT
                COUNT(
                    CASE
                        WHEN type = 'RF_RX'
                        THEN 1
                    END
                ) AS rf_rx,

                COUNT(
                    CASE
                        WHEN type = 'IS_RX'
                        THEN 1
                    END
                ) AS is_rx,

                COUNT(
                    CASE
                        WHEN type = 'RF_TO_IS'
                        THEN 1
                    END
                ) AS rf_to_is,

                COUNT(
                    CASE
                        WHEN type = 'DUPLICATE_DROP'
                        THEN 1
                    END
                ) AS duplicate_drop

            FROM events

            WHERE time >= ?
            """,
            (
                cutoff.isoformat(),
            )
        ).fetchone()

    rf_rx = row["rf_rx"] or 0
    is_rx = row["is_rx"] or 0

    return {
        "window_seconds":
            60,

        "packets_per_minute":
            rf_rx + is_rx,

        "rf_rx":
            rf_rx,

        "is_rx":
            is_rx,

        "rf_to_is":
            row["rf_to_is"] or 0,

        "duplicate_drop":
            row["duplicate_drop"] or 0,
    }


def get_minute_activity(minutes=30):

    minutes = _bounded_int(
        minutes,
        30,
        5,
        120
    )

    now = datetime.now(
        timezone.utc
    ).replace(
        second=0,
        microsecond=0
    )

    start = (
        now
        - timedelta(
            minutes=minutes - 1
        )
    )

    series = []
    buckets = {}

    for offset in range(minutes):

        moment = (
            start
            + timedelta(
                minutes=offset
            )
        )

        key = moment.isoformat()

        item = {
            "time":
                key,

            "rf_rx":
                0,

            "rf_to_is":
                0,

            "is_rx":
                0,

            "duplicate_drop":
                0,

            "tx_rf":
                0,
        }

        buckets[
            key
        ] = item

        series.append(
            item
        )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                time,
                type

            FROM events

            WHERE time >= ?
              AND type IN (
                  'RF_RX',
                  'RF_TO_IS',
                  'IS_RX',
                  'DUPLICATE_DROP',
                  'TX_RF'
              )

            ORDER BY time
            """,
            (
                start.isoformat(),
            )
        ).fetchall()

    field_by_type = {
        "RF_RX":
            "rf_rx",

        "RF_TO_IS":
            "rf_to_is",

        "IS_RX":
            "is_rx",

        "DUPLICATE_DROP":
            "duplicate_drop",

        "TX_RF":
            "tx_rf",
    }

    for row in rows:

        try:
            event_time = datetime.fromisoformat(
                row["time"]
            )
        except Exception:
            continue

        if event_time.tzinfo is None:
            event_time = event_time.replace(
                tzinfo=timezone.utc
            )

        minute_key = (
            event_time
            .astimezone(
                timezone.utc
            )
            .replace(
                second=0,
                microsecond=0
            )
            .isoformat()
        )

        bucket = buckets.get(
            minute_key
        )

        if not bucket:
            continue

        field = field_by_type.get(
            row["type"]
        )

        if field:
            bucket[
                field
            ] += 1

    return {
        "minutes":
            minutes,

        "series":
            series,
    }


def get_top_stations(hours=24, limit=10):

    hours = _bounded_int(
        hours,
        24,
        1,
        168
    )

    limit = _bounded_int(
        limit,
        10,
        1,
        50
    )

    cutoff = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            hours=hours
        )
    )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                callsign,
                COUNT(*) AS packets,

                COUNT(
                    CASE
                        WHEN type = 'RF_RX'
                        THEN 1
                    END
                ) AS rf_packets,

                COUNT(
                    CASE
                        WHEN type = 'IS_RX'
                        THEN 1
                    END
                ) AS is_packets,

                MAX(time) AS last_seen

            FROM events

            WHERE time >= ?
              AND callsign IS NOT NULL
              AND callsign <> ''
              AND type IN (
                  'RF_RX',
                  'IS_RX'
              )

            GROUP BY callsign

            ORDER BY
                packets DESC,
                last_seen DESC

            LIMIT ?
            """,
            (
                cutoff.isoformat(),
                limit,
            )
        ).fetchall()

    stations = []

    for row in rows:

        stations.append(
            {
                "callsign":
                    row["callsign"],

                "packets":
                    row["packets"] or 0,

                "rf_packets":
                    row["rf_packets"] or 0,

                "is_packets":
                    row["is_packets"] or 0,

                "last_seen":
                    row["last_seen"],
            }
        )

    return {
        "hours":
            hours,

        "count":
            len(
                stations
            ),

        "stations":
            stations,
    }


def get_recent_stations(hours=24, limit=12):

    hours = _bounded_int(
        hours,
        24,
        1,
        168
    )

    limit = _bounded_int(
        limit,
        12,
        1,
        50
    )

    cutoff = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            hours=hours
        )
    )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                time,
                type,
                callsign,
                packet,
                extra_json

            FROM events

            WHERE time >= ?
              AND callsign IS NOT NULL
              AND callsign <> ''
              AND type IN (
                  'RF_RX',
                  'IS_RX'
              )

            ORDER BY id DESC

            LIMIT 2000
            """,
            (
                cutoff.isoformat(),
            )
        ).fetchall()

    seen = set()
    stations = []

    for row in rows:

        callsign = (
            row["callsign"]
            or ""
        ).strip().upper()

        if not callsign:
            continue

        if callsign in seen:
            continue

        seen.add(
            callsign
        )

        extra = _decode_extra_json(
            row["extra_json"]
        )

        weather = extra.get(
            "weather"
        )

        if not isinstance(
            weather,
            dict
        ):
            weather = None

        stations.append(
            {
                "callsign":
                    callsign,

                "time":
                    row["time"],

                "source":
                    (
                        "RF"
                        if row["type"] == "RF_RX"
                        else "APRS_IS"
                    ),

                "packet":
                    row["packet"],

                "latitude":
                    extra.get(
                        "latitude"
                    ),

                "longitude":
                    extra.get(
                        "longitude"
                    ),

                "aprs_format":
                    extra.get(
                        "aprs_format"
                    ),

                "symbol":
                    extra.get(
                        "symbol"
                    ),

                "symbol_table":
                    extra.get(
                        "symbol_table"
                    ),

                "speed":
                    extra.get(
                        "speed"
                    ),

                "course":
                    extra.get(
                        "course"
                    ),

                "altitude":
                    extra.get(
                        "altitude"
                    ),

                "mic_e_status":
                    extra.get(
                        "mic_e_status"
                    ),

                "comment":
                    extra.get(
                        "comment"
                    ),

                "is_weather":
                    bool(
                        extra.get(
                            "is_weather",
                            False
                        )
                    ),

                "weather":
                    weather,
            }
        )

        if len(
            stations
        ) >= limit:
            break

    return {
        "hours":
            hours,

        "count":
            len(
                stations
            ),

        "stations":
            stations,
    }


def get_weather_stations(hours=24, limit=6):

    hours = _bounded_int(
        hours,
        24,
        1,
        168
    )

    limit = _bounded_int(
        limit,
        6,
        1,
        30
    )

    cutoff = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            hours=hours
        )
    )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                time,
                type,
                callsign,
                packet,
                extra_json

            FROM events

            WHERE time >= ?
              AND callsign IS NOT NULL
              AND callsign <> ''
              AND type IN (
                  'RF_RX',
                  'IS_RX'
              )
              AND extra_json IS NOT NULL
              AND json_extract(
                    extra_json,
                    '$.is_weather'
                  ) = 1

            ORDER BY id DESC

            LIMIT 2000
            """,
            (
                cutoff.isoformat(),
            )
        ).fetchall()

    seen = set()
    stations = []

    for row in rows:

        callsign = (
            row["callsign"]
            or ""
        ).strip().upper()

        if not callsign:
            continue

        if callsign in seen:
            continue

        seen.add(
            callsign
        )

        extra = _decode_extra_json(
            row["extra_json"]
        )

        weather = extra.get(
            "weather"
        )

        if not isinstance(
            weather,
            dict
        ):
            continue

        stations.append(
            {
                "callsign":
                    callsign,

                "time":
                    row["time"],

                "source":
                    (
                        "RF"
                        if row["type"] == "RF_RX"
                        else "APRS_IS"
                    ),

                "latitude":
                    extra.get(
                        "latitude"
                    ),

                "longitude":
                    extra.get(
                        "longitude"
                    ),

                "aprs_format":
                    extra.get(
                        "aprs_format"
                    ),

                "symbol":
                    extra.get(
                        "symbol"
                    ),

                "symbol_table":
                    extra.get(
                        "symbol_table"
                    ),

                "comment":
                    extra.get(
                        "comment"
                    ),

                "weather":
                    weather,
            }
        )

        if len(
            stations
        ) >= limit:
            break

    return {
        "hours":
            hours,

        "count":
            len(
                stations
            ),

        "stations":
            stations,
    }


def get_station_detail(callsign, hours=24):

    callsign = (
        str(
            callsign
        )
        .strip()
        .upper()
    )

    hours = _bounded_int(
        hours,
        24,
        1,
        720
    )

    cutoff = (
        datetime.now(
            timezone.utc
        )
        - timedelta(
            hours=hours
        )
    )

    with closing(
        get_connection()
    ) as conn:

        summary = conn.execute(
            """
            SELECT
                COUNT(*) AS packets,

                COUNT(
                    CASE
                        WHEN type = 'RF_RX'
                        THEN 1
                    END
                ) AS rf_packets,

                COUNT(
                    CASE
                        WHEN type = 'IS_RX'
                        THEN 1
                    END
                ) AS is_packets,

                MIN(time) AS first_seen,
                MAX(time) AS last_seen

            FROM events

            WHERE time >= ?
              AND callsign = ?
              AND type IN (
                  'RF_RX',
                  'IS_RX'
              )
            """,
            (
                cutoff.isoformat(),
                callsign,
            )
        ).fetchone()

        if not summary or not (
            summary["packets"]
            or 0
        ):
            return None

        latest = conn.execute(
            """
            SELECT
                id,
                time,
                type,
                packet,
                raw,
                level,
                detail,
                decoder,
                extra_json

            FROM events

            WHERE time >= ?
              AND callsign = ?
              AND type IN (
                  'RF_RX',
                  'IS_RX'
              )

            ORDER BY id DESC
            LIMIT 1
            """,
            (
                cutoff.isoformat(),
                callsign,
            )
        ).fetchone()

        latest_position = conn.execute(
            """
            SELECT
                id,
                time,
                type,
                packet,
                extra_json

            FROM events

            WHERE time >= ?
              AND callsign = ?
              AND type IN (
                  'RF_RX',
                  'IS_RX'
              )
              AND extra_json IS NOT NULL
              AND json_extract(
                    extra_json,
                    '$.latitude'
                  ) IS NOT NULL
              AND json_extract(
                    extra_json,
                    '$.longitude'
                  ) IS NOT NULL

            ORDER BY id DESC
            LIMIT 1
            """,
            (
                cutoff.isoformat(),
                callsign,
            )
        ).fetchone()

    latest_event = None

    if latest:

        latest_extra = _decode_extra_json(
            latest["extra_json"]
        )

        latest_event = {
            "time":
                latest["time"],

            "source":
                (
                    "RF"
                    if latest["type"] == "RF_RX"
                    else "APRS_IS"
                ),

            "packet":
                latest["packet"],

            "level":
                latest["level"],

            "detail":
                latest["detail"],

            "decoder":
                latest["decoder"],

            "aprs_format":
                latest_extra.get(
                    "aprs_format"
                ),

            "symbol":
                latest_extra.get(
                    "symbol"
                ),

            "symbol_table":
                latest_extra.get(
                    "symbol_table"
                ),

            "comment":
                latest_extra.get(
                    "comment"
                ),

            "speed":
                latest_extra.get(
                    "speed"
                ),

            "course":
                latest_extra.get(
                    "course"
                ),

            "altitude":
                latest_extra.get(
                    "altitude"
                ),

            "mic_e_status":
                latest_extra.get(
                    "mic_e_status"
                ),

            "is_weather":
                bool(
                    latest_extra.get(
                        "is_weather",
                        False
                    )
                ),

            "weather":
                latest_extra.get(
                    "weather"
                ),
        }

    position = None

    if latest_position:

        position_extra = _decode_extra_json(
            latest_position[
                "extra_json"
            ]
        )

        position = {
            "time":
                latest_position["time"],

            "source":
                (
                    "RF"
                    if latest_position["type"] == "RF_RX"
                    else "APRS_IS"
                ),

            "packet":
                latest_position["packet"],

            "latitude":
                position_extra.get(
                    "latitude"
                ),

            "longitude":
                position_extra.get(
                    "longitude"
                ),

            "speed":
                position_extra.get(
                    "speed"
                ),

            "course":
                position_extra.get(
                    "course"
                ),

            "altitude":
                position_extra.get(
                    "altitude"
                ),

            "symbol":
                position_extra.get(
                    "symbol"
                ),

            "symbol_table":
                position_extra.get(
                    "symbol_table"
                ),

            "aprs_format":
                position_extra.get(
                    "aprs_format"
                ),

            "comment":
                position_extra.get(
                    "comment"
                ),

            "mic_e_status":
                position_extra.get(
                    "mic_e_status"
                ),
        }

    return {
        "callsign":
            callsign,

        "hours":
            hours,

        "packets":
            summary["packets"] or 0,

        "rf_packets":
            summary["rf_packets"] or 0,

        "is_packets":
            summary["is_packets"] or 0,

        "first_seen":
            summary["first_seen"],

        "last_seen":
            summary["last_seen"],

        "latest":
            latest_event,

        "position":
            position,
    }



# ============================================================
# ATIVIDADE DE TRANSMISSAO RF
# ============================================================

def _packet_identity(packet):

    if not packet:
        return None

    packet = str(
        packet
    ).strip()

    if ">" not in packet or ":" not in packet:
        return None

    header, payload = packet.split(
        ":",
        1
    )

    # Pacotes APRS-IS encaminhados ao RF pelo Direwolf saem
    # encapsulados como third-party:
    #
    # N0CALL-10>APDW19,WIDE1-1:}ORIGEM>DEST,...:payload
    #
    # Para correlacionar o TX com o pacote que chegou do APRS-IS,
    # removemos o envelope e usamos ORIGEM + payload interno.
    if payload.startswith(
        "}"
    ):

        inner_packet = (
            payload[1:]
            .strip()
        )

        if (
            ">" in inner_packet
            and
            ":" in inner_packet
        ):

            return _packet_identity(
                inner_packet
            )

    source = header.split(
        ">",
        1
    )[0].strip().upper()

    if not source:
        return None

    return (
        source
        + ":"
        + payload
    )


def get_tx_activity(minutes=60):

    minutes = _bounded_int(
        minutes,
        60,
        5,
        120
    )

    start_utc, end_utc = (
        get_today_period_utc()
    )

    now = datetime.now(
        timezone.utc
    )

    minute_start = (
        now
        .replace(
            second=0,
            microsecond=0
        )
        - timedelta(
            minutes=minutes - 1
        )
    )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                time,
                type,
                packet

            FROM events

            WHERE time >= ?
              AND time < ?
              AND type IN (
                  'IS_RX',
                  'TX_RF'
              )

            ORDER BY time
            """,
            (
                start_utc.isoformat(),
                end_utc.isoformat(),
            )
        ).fetchall()

    pending_is = {}
    tx_rf_today = 0
    is_to_rf_today = 0

    series = []
    buckets = {}

    for offset in range(minutes):

        moment = (
            minute_start
            + timedelta(
                minutes=offset
            )
        )

        key = moment.isoformat()

        item = {
            "time":
                key,

            "tx_rf":
                0,

            "is_to_rf":
                0,
        }

        buckets[
            key
        ] = item

        series.append(
            item
        )

    for row in rows:

        try:

            event_time = datetime.fromisoformat(
                row["time"]
            )

        except Exception:

            continue

        if event_time.tzinfo is None:

            event_time = event_time.replace(
                tzinfo=timezone.utc
            )

        event_time = event_time.astimezone(
            timezone.utc
        )

        identity = _packet_identity(
            row["packet"]
        )

        if row["type"] == "IS_RX":

            if identity:

                pending_is[
                    identity
                ] = event_time

            continue

        if row["type"] != "TX_RF":

            continue

        tx_rf_today += 1

        matched_is = False

        if identity:

            source_time = pending_is.get(
                identity
            )

            if source_time is not None:

                delta = (
                    event_time
                    - source_time
                ).total_seconds()

                if 0 <= delta <= 20:

                    matched_is = True
                    is_to_rf_today += 1

        minute_key = (
            event_time
            .replace(
                second=0,
                microsecond=0
            )
            .isoformat()
        )

        bucket = buckets.get(
            minute_key
        )

        if bucket:

            bucket[
                "tx_rf"
            ] += 1

            if matched_is:

                bucket[
                    "is_to_rf"
                ] += 1

    return {
        "minutes":
            minutes,

        "tx_rf_today":
            tx_rf_today,

        "is_to_rf_today":
            is_to_rf_today,

        "series":
            series,
    }



# ============================================================
# TENDENCIA DOS CARDS PRINCIPAIS
# ============================================================

def _trend_record(
    current,
    previous
):

    current = int(
        current or 0
    )

    previous = int(
        previous or 0
    )

    if previous == 0:

        if current == 0:

            percent = 0.0

        else:

            percent = 100.0

    else:

        percent = (
            (
                current
                - previous
            )
            / previous
            * 100.0
        )

    if current > previous:

        direction = "up"

    elif current < previous:

        direction = "down"

    else:

        direction = "flat"

    return {
        "current":
            current,

        "previous":
            previous,

        "percent":
            round(
                percent,
                1
            ),

        "direction":
            direction,
    }


def get_kpi_trends(
    window_seconds=60
):

    window_seconds = max(
        30,
        min(
            3600,
            int(
                window_seconds
            )
        )
    )

    now = datetime.now(
        timezone.utc
    )

    current_start = (
        now
        - timedelta(
            seconds=window_seconds
        )
    )

    previous_start = (
        current_start
        - timedelta(
            seconds=window_seconds
        )
    )

    query_start = (
        previous_start
        - timedelta(
            seconds=20
        )
    )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                time,
                type,
                callsign,
                packet

            FROM events

            WHERE time >= ?
              AND time < ?
              AND type IN (
                  'RF_RX',
                  'IS_RX',
                  'TX_RF',
                  'DUPLICATE_DROP'
              )

            ORDER BY time
            """,
            (
                query_start.isoformat(),
                now.isoformat(),
            )
        ).fetchall()

    current_counts = {
        "rf_rx": 0,
        "is_to_rf": 0,
        "tx_rf": 0,
        "duplicate_drop": 0,
        "packets_per_minute": 0,
    }

    previous_counts = {
        "rf_rx": 0,
        "is_to_rf": 0,
        "tx_rf": 0,
        "duplicate_drop": 0,
        "packets_per_minute": 0,
    }

    current_unique = set()
    previous_unique = set()
    pending_is = {}

    for row in rows:

        try:

            event_time = datetime.fromisoformat(
                row["time"]
            )

        except Exception:

            continue

        if event_time.tzinfo is None:

            event_time = event_time.replace(
                tzinfo=timezone.utc
            )

        event_time = event_time.astimezone(
            timezone.utc
        )

        event_type = row[
            "type"
        ]

        identity = _packet_identity(
            row["packet"]
        )

        if event_type == "IS_RX":

            if identity:

                pending_is[
                    identity
                ] = event_time

        if (
            current_start
            <= event_time
            < now
        ):

            target = current_counts
            unique_target = current_unique

        elif (
            previous_start
            <= event_time
            < current_start
        ):

            target = previous_counts
            unique_target = previous_unique

        else:

            continue

        if event_type == "RF_RX":

            target[
                "rf_rx"
            ] += 1

            target[
                "packets_per_minute"
            ] += 1

            callsign = (
                row["callsign"]
                or ""
            ).strip().upper()

            if callsign:

                unique_target.add(
                    callsign
                )

        elif event_type == "IS_RX":

            target[
                "packets_per_minute"
            ] += 1

        elif event_type == "TX_RF":

            target[
                "tx_rf"
            ] += 1

            if identity:

                source_time = pending_is.get(
                    identity
                )

                if source_time is not None:

                    delta = (
                        event_time
                        - source_time
                    ).total_seconds()

                    if 0 <= delta <= 20:

                        target[
                            "is_to_rf"
                        ] += 1

        elif event_type == "DUPLICATE_DROP":

            target[
                "duplicate_drop"
            ] += 1

    current_counts[
        "unique_rf_stations"
    ] = len(
        current_unique
    )

    previous_counts[
        "unique_rf_stations"
    ] = len(
        previous_unique
    )

    return {
        "window_seconds":
            window_seconds,

        "current_start":
            current_start.isoformat(),

        "previous_start":
            previous_start.isoformat(),

        "metrics": {
            key:
                _trend_record(
                    current_counts.get(
                        key,
                        0
                    ),
                    previous_counts.get(
                        key,
                        0
                    )
                )
            for key in (
                "rf_rx",
                "is_to_rf",
                "tx_rf",
                "unique_rf_stations",
                "duplicate_drop",
                "packets_per_minute",
            )
        },
    }



# ============================================================
# ESTADO DE ATIVIDADE DE AUDIO / RX / TX
# ============================================================

def get_audio_activity_state():

    now = datetime.now(
        timezone.utc
    )

    with closing(
        get_connection()
    ) as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                time,
                type,
                level

            FROM events

            WHERE type IN (
                'AUDIO_LEVEL',
                'RF_RX',
                'TX_RF'
            )

            ORDER BY id DESC

            LIMIT 300
            """
        ).fetchall()

    latest = {
        "AUDIO_LEVEL": None,
        "RF_RX": None,
        "TX_RF": None,
    }

    for row in rows:

        event_type = row[
            "type"
        ]

        if (
            event_type in latest
            and
            latest[
                event_type
            ] is None
        ):

            latest[
                event_type
            ] = row

        if all(
            value is not None
            for value in latest.values()
        ):

            break

    def event_age(
        row
    ):

        if row is None:

            return None

        try:

            event_time = datetime.fromisoformat(
                row[
                    "time"
                ]
            )

        except Exception:

            return None

        if event_time.tzinfo is None:

            event_time = event_time.replace(
                tzinfo=timezone.utc
            )

        return max(
            0.0,
            (
                now
                - event_time.astimezone(
                    timezone.utc
                )
            ).total_seconds()
        )

    audio_row = latest[
        "AUDIO_LEVEL"
    ]

    rf_row = latest[
        "RF_RX"
    ]

    tx_row = latest[
        "TX_RF"
    ]

    audio_age = event_age(
        audio_row
    )

    rf_age = event_age(
        rf_row
    )

    tx_age = event_age(
        tx_row
    )

    audio_level = None

    if audio_row is not None:

        audio_level = audio_row[
            "level"
        ]

    return {
        "audio_level":
            audio_level,

        "audio_age_seconds":
            audio_age,

        "rf_age_seconds":
            rf_age,

        "tx_age_seconds":
            tx_age,

        "rx_active":
            (
                (
                    rf_age is not None
                    and
                    rf_age <= 2.5
                )
                or
                (
                    audio_age is not None
                    and
                    audio_age <= 2.5
                )
            ),

        "tx_active":
            (
                tx_age is not None
                and
                tx_age <= 2.5
            ),
    }
