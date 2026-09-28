# API do dashboard

A API FastAPI é servida na mesma porta do painel.

Base típica:

```text
http://IP:8088
```

## Status

```http
GET /api/status
```

Retorna, entre outros:

- indicativo da estação;
- rótulo/localização;
- timezone;
- estado do áudio;
- estado do Direwolf;
- estado APRS-IS;
- método de PTT;
- disponibilidade do PTT;
- dados legados de serial quando aplicáveis.

Campos de PTT relevantes:

```text
ptt_mode
ptt_configured
ptt_online
ptt_label
ptt_device
gpio_chip
gpio_line
```

`ptt_mode` pode ser `none`, `serial` ou `gpiod`.

Os campos `serial_*` são mantidos para compatibilidade com clientes antigos.

## Estatísticas

```http
GET /api/stats
```

Contadores de eventos e KPIs.

## Eventos recentes

```http
GET /api/events?limit=120
```

Eventos estruturados vindos do journal do Direwolf.

## Mapa

```http
GET /api/map?hours=24&limit=250
```

Posições recentes para renderização.

## Overview

```http
GET /api/overview
```

Agrega taxa de pacotes, séries por minuto, top estações, estações recentes, WX, TX, uptime e CPU/RAM.

## Áudio

```http
GET /api/audio
```

Estado do console de áudio.

## Configuração

```http
GET /api/station-config
GET /api/station-config/capabilities
POST /api/station-config/{section}
```

A seção de hardware suporta PTT desabilitado, serial DTR/RTS e GPIOD.

As alterações de escrita são limitadas a endereços privados/loopback pelo backend atual. Não exponha a API de escrita diretamente à Internet.

## Mapas offline

```http
GET    /api/offline-map/status
POST   /api/offline-map/estimate
POST   /api/offline-map/download
DELETE /api/offline-map/{kind}
```

Tiles locais:

```http
GET /offline-map/{kind}/{zoom}/{x}/{y}.jpg
```

## Swagger/OpenAPI

```text
/docs
```

O FastAPI mantém a especificação OpenAPI automaticamente.
