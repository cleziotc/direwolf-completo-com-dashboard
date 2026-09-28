# API do dashboard

A API é servida pelo FastAPI na mesma porta do painel.

Base típica:

```text
http://IP:8088
```

## Status

```http
GET /api/status
```

Retorna estado de:

- estação;
- hardware de áudio;
- serial/PTT;
- Direwolf;
- APRS-IS;
- timezone.

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

Agrega:

- taxa de pacotes;
- séries por minuto;
- top estações;
- estações recentes;
- WX;
- TX;
- uptime;
- CPU/RAM.

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

As alterações são limitadas a requisições oriundas de endereços privados/loopback pelo backend atual.

Não exponha essa API de escrita diretamente à Internet.

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

Como o FastAPI mantém OpenAPI, a documentação automática normalmente pode ser consultada em:

```text
/docs
```

em uma instalação padrão.
