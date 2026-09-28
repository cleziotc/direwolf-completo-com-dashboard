# Arquitetura do sistema

## Visão geral

A solução é dividida em quatro camadas independentes:

1. **RF e hardware** — rádio, interface de áudio e PTT;
2. **Direwolf** — modem/TNC, digipeater e iGate;
3. **coletor/API** — aplicação Python/FastAPI;
4. **interface web** — monitor e configuração.

Essa separação é proposital. Se o navegador for fechado, o Direwolf continua funcionando. Se o dashboard reiniciar, ele recupera do journal os eventos ainda não gravados no SQLite.

## Fluxo RX

```text
Rádio → áudio USB → ALSA → Direwolf → pacote AX.25/APRS
                                  │
                                  ├→ APRS-IS
                                  └→ journal do systemd
```

O dashboard acompanha `journalctl -u direwolf`. Cada linha relevante é convertida para um evento estruturado, como:

- `RF_RX`;
- `RF_TO_IS`;
- `IS_RX`;
- `TX_RF`;
- `DUPLICATE_DROP`;
- `AUDIO_LEVEL`.

Quando possível, o pacote é também interpretado pelo `aprslib` para extrair posição, símbolo, velocidade, curso, altitude, comentário e telemetria meteorológica.

## Fluxo TX

Quando TX é habilitado:

```text
APRS-IS → Direwolf → filtro → fila de TX → áudio → rádio
                                      │
                                      └→ PTT por DTR/RTS
```

O dashboard não gera PTT diretamente. Ele configura o Direwolf. O Direwolf é a fonte de verdade para transmissão.

## Banco de dados

O arquivo `database.py` usa SQLite em:

```text
/home/aprs/aprs-dashboard/data/aprs.db
```

São mantidos eventos de recepção, encaminhamento, transmissão, drops e telemetria. O banco usa WAL para melhorar a concorrência entre coleta e consultas.

O reset visual de KPIs diários não apaga o histórico.

## API

O FastAPI expõe, entre outros:

- `/api/status`;
- `/api/stats`;
- `/api/events`;
- `/api/map`;
- `/api/overview`;
- `/api/audio`;
- `/api/station-config`;
- `/api/offline-map/status`.

A interface web consome essas rotas periodicamente.

## Configuração

O arquivo principal é:

```text
/home/aprs/direwolf.conf
```

A página `/config` lê e altera seções controladas desse arquivo. Antes de gravar, é criado um backup em `data/config-backups/`.

O passcode do APRS-IS não é retornado pela API.

## Watchdog

O serviço `aprs-hardware-watchdog` lê `ADEVICE` e `PTT` do `direwolf.conf`. Ele observa a presença da placa de captura e da serial.

Quando um hardware que estava ausente reaparece e todos os dispositivos requeridos estão prontos, o watchdog reinicia o Direwolf. Isso resolve o caso comum em que um USB cai e volta, mas o processo não recupera a interface sozinho.

Além disso, um drop-in systemd mantém `Restart=always` para o Direwolf.

## Mapas

A interface usa Leaflet. Há duas categorias:

- mapas online para uso normal;
- pacotes locais em `data/offline-maps/`.

O cache offline é organizado por camada, zoom, X e Y.

## Princípios de projeto

- configuração local fora do Git;
- nenhum passcode no repositório;
- TX desabilitado por padrão;
- serviços separados;
- rollback em atualização;
- recuperação após falha de hardware;
- compatibilidade com VM, máquina física e Raspberry Pi.
