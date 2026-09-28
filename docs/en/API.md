# Dashboard API

The FastAPI application serves the API on the same port as the dashboard.

Typical base URL:

```text
http://DEVICE-IP:8088
```

## Status

```http
GET /api/status
```

Includes station identity, timezone, audio state, Direwolf state, APRS-IS state and PTT information.

Important PTT fields:

```text
ptt_mode
ptt_configured
ptt_online
ptt_label
ptt_device
gpio_chip
gpio_line
```

`ptt_mode` may be `none`, `serial` or `gpiod`.

Legacy `serial_*` fields remain available for compatibility.

## Statistics

```http
GET /api/stats
```

## Recent events

```http
GET /api/events?limit=120
```

## Map positions

```http
GET /api/map?hours=24&limit=250
```

## Overview

```http
GET /api/overview
```

Aggregates packet rates, minute series, top stations, recent stations, weather, TX state, uptime and CPU/RAM.

## Audio

```http
GET /api/audio
```

## Station configuration

```http
GET /api/station-config
GET /api/station-config/capabilities
POST /api/station-config/{section}
```

The hardware section supports disabled PTT, serial DTR/RTS and GPIOD.

Write operations are restricted to private/loopback clients by the current backend. Do not expose configuration write endpoints directly to the Internet.

## Offline maps

```http
GET    /api/offline-map/status
POST   /api/offline-map/estimate
POST   /api/offline-map/download
DELETE /api/offline-map/{kind}
```

Local tiles:

```http
GET /offline-map/{kind}/{zoom}/{x}/{y}.jpg
```

## OpenAPI

FastAPI documentation is normally available at:

```text
/docs
```
