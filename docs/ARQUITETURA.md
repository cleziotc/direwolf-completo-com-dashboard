# Arquitetura do sistema

## Visão geral

A solução é dividida em quatro camadas:

1. RF e hardware;
2. Direwolf;
3. coletor/API Python;
4. interface web.

O navegador não participa da operação crítica. Fechar o dashboard não interrompe o Direwolf.

## Fluxo RX

```text
Rádio → áudio → ALSA → Direwolf → AX.25/APRS
                              │
                              ├→ APRS-IS
                              └→ journal systemd
```

O dashboard acompanha `journalctl -u direwolf` e transforma linhas em eventos como:

- `RF_RX`;
- `RF_TO_IS`;
- `IS_RX`;
- `TX_RF`;
- `DUPLICATE_DROP`;
- `AUDIO_LEVEL`.

O `aprslib` é usado para extrair posição, símbolo, velocidade, curso, altitude, comentário e WX quando disponível.

## Fluxo TX

```text
APRS-IS → Direwolf → filtros/proteções → áudio → rádio
                                         │
                                         └→ PTT
```

PTT pode ser:

- **Ubuntu/Linux:** serial DTR/RTS;
- **Raspberry Pi:** GPIO via GPIOD.

O dashboard não chaveia PTT diretamente; ele configura o Direwolf.

## SQLite

Banco:

```text
/home/aprs/aprs-dashboard/data/aprs.db
```

O banco usa WAL e mantém o histórico mesmo quando KPIs diários são reiniciados visualmente.

## API

Principais rotas:

- `/api/status`;
- `/api/stats`;
- `/api/events`;
- `/api/map`;
- `/api/overview`;
- `/api/audio`;
- `/api/station-config`;
- `/api/offline-map/status`.

## Configuração

Arquivo principal:

```text
/home/aprs/direwolf.conf
```

A página `/config` lê e grava seções controladas. O passcode APRS-IS não é retornado ao navegador.

## Watchdog

O watchdog interpreta `ADEVICE` e `PTT` do próprio `direwolf.conf`.

Ele suporta:

- captura ALSA;
- PTT serial;
- PTT GPIOD;
- ausência de PTT em RX-only.

Quando hardware necessário reaparece, o Direwolf é reiniciado após tempo de estabilização.

## systemd

Serviços:

```text
direwolf.service
aprs-dashboard.service
aprs-hardware-watchdog.service
```

Um drop-in adiciona política de recuperação ao Direwolf.

## Mapas

Leaflet é instalado localmente. A interface pode usar mapas online e pacotes offline em:

```text
data/offline-maps/
```

## Princípios do projeto

- parâmetros locais fora do Git;
- nenhum passcode no repositório;
- TX desabilitado por padrão;
- separação entre modem e dashboard;
- recuperação automática;
- rollback de atualização;
- compatibilidade com VM, bare metal e Raspberry Pi;
- PTT nativo no Raspberry para reduzir hardware desnecessário.
