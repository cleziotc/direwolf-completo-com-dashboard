# Direwolf completo com Dashboard

[Português](#português) • [English](#english)

---
<img width="1902" height="1188" alt="image" src="https://github.com/user-attachments/assets/06476445-670c-49d0-ab65-30b2039ef201" />



# Português

Projeto público para montar uma estação APRS baseada em **Direwolf + Linux**, com dashboard web moderno, configuração pelo navegador, histórico em SQLite, mapas, telemetria, monitoramento de hardware e recuperação automática.

O projeto nasceu de uma estação real e foi organizado por **Clézio da Cunha Costa, PP5CI**, com apoio do ChatGPT/OpenAI no desenvolvimento, testes, refatoração e documentação.

> **Crédito importante:** a configuração-base `direwolf.conf` utilizada como referência neste projeto foi originalmente programada pelo radioamador **Daniel, PP5BK**.

> O Direwolf é um projeto independente, mantido por WB2OSZ e colaboradores. Este repositório não redistribui o código-fonte do Direwolf; os instaladores clonam e compilam o repositório oficial.

## Objetivo

A proposta é oferecer à comunidade radioamadora uma solução que possa ser:

- instalada de forma automatizada;
- estudada e modificada;
- usada em máquina física, VM Ubuntu ou Raspberry Pi;
- operada como iGate RX-only;
- ampliada para iGate bidirecional, digipeater e beacon RF;
- monitorada e configurada por navegador;
- recuperada automaticamente após falhas de hardware.

## Principais recursos

- Direwolf compilado a partir do projeto oficial;
- iGate RF → APRS-IS;
- opção de APRS-IS → RF;
- digipeater APRS;
- beacon APRS-IS e beacon RF;
- PTT serial por DTR/RTS em Ubuntu/Linux;
- PTT por **GPIO nativo/GPIOD em Raspberry Pi**, sem necessidade de conversor serial;
- dashboard FastAPI;
- tráfego APRS em tempo real;
- estatísticas diárias e por minuto;
- histórico SQLite;
- mapa de estações;
- mapas de ruas e satélite;
- download de mapas para uso offline;
- APRS/WX;
- detalhes de posição, velocidade, rumo, altitude, path e comentário;
- monitoramento de CPU e RAM;
- monitoramento de áudio USB e PTT;
- VUs RX/TX;
- página de configuração do Direwolf;
- backup automático do `direwolf.conf`;
- watchdog de hardware;
- recuperação automática via systemd;
- atualizador com health check e rollback;
- instaladores separados para Ubuntu e Raspberry Pi OS.

## Segurança operacional

A instalação mantém **TX RF desabilitado por padrão**.

O usuário precisa confirmar explicitamente a ativação de PTT, digipeater e IS → RF. Antes de transmitir, confira:

- licença;
- legislação local;
- plano de banda;
- frequência APRS da sua região;
- potência;
- identificação;
- path;
- política de iGate/digipeater;
- aterramento e interface elétrica do PTT.

O passcode APRS-IS é calculado localmente pelo instalador e gravado somente no `/home/aprs/direwolf.conf` local. Ele não deve ser publicado no GitHub.

## Instalação rápida

### Ubuntu Server / Ubuntu Linux

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-ubuntu.sh | sudo bash
```

Guia completo: [docs/INSTALACAO-UBUNTU.md](docs/INSTALACAO-UBUNTU.md)

No Ubuntu, o caminho normal para TX é uma interface serial usando DTR ou RTS. O instalador procura primeiro nomes persistentes em `/dev/serial/by-id/`.

### Raspberry Pi OS

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-raspberry.sh | sudo bash
```

Guia completo: [docs/INSTALACAO-RASPBERRY.md](docs/INSTALACAO-RASPBERRY.md)

No Raspberry Pi, o instalador usa **PTT por GPIO nativo via libgpiod**. O padrão inicial é GPIO 25, e o `gpiochip` pode ser detectado ou informado pelo operador.

## O que o instalador faz

1. valida execução como root;
2. instala dependências;
3. cria o usuário de serviço `aprs`;
4. adiciona os grupos necessários, incluindo `audio`, `dialout` e `gpio` quando disponível;
5. baixa e compila o Direwolf oficial;
6. instala o dashboard em `/home/aprs/aprs-dashboard`;
7. cria o ambiente Python;
8. detecta a placa ALSA;
9. no Ubuntu, detecta uma serial para PTT;
10. no Raspberry, prepara PTT GPIOD;
11. pergunta indicativo, coordenadas e parâmetros da estação;
12. calcula o passcode APRS-IS localmente;
13. gera o `direwolf.conf`;
14. instala serviços systemd;
15. instala o watchdog de hardware;
16. habilita recuperação automática;
17. baixa Leaflet local;
18. inicia os serviços;
19. testa a API do dashboard.

Ao final:

```text
http://IP-DO-EQUIPAMENTO:8088/
http://IP-DO-EQUIPAMENTO:8088/config
```

## Instalação a partir de clone

```bash
git clone https://github.com/cleziotc/direwolf-completo-com-dashboard.git
cd direwolf-completo-com-dashboard
sudo bash install-ubuntu.sh
```

ou:

```bash
sudo bash install-raspberry.sh
```

## Instalação não interativa

Exemplo Ubuntu RX-only:

```bash
sudo env \
  APRS_NONINTERACTIVE=1 \
  APRS_CALLSIGN=PY1ABC-10 \
  APRS_LOCATION_LABEL="Minha cidade" \
  APRS_TIMEZONE=America/Sao_Paulo \
  APRS_LATITUDE=-23.5505 \
  APRS_LONGITUDE=-46.6333 \
  APRS_ENABLE_TX=N \
  bash install-ubuntu.sh
```

Exemplo Raspberry com PTT GPIO:

```bash
sudo env \
  APRS_NONINTERACTIVE=1 \
  APRS_CALLSIGN=PY1ABC-10 \
  APRS_LOCATION_LABEL="Minha cidade" \
  APRS_TIMEZONE=America/Sao_Paulo \
  APRS_LATITUDE=-23.5505 \
  APRS_LONGITUDE=-46.6333 \
  APRS_ENABLE_TX=S \
  APRS_GPIO_CHIP=/dev/gpiochip0 \
  APRS_GPIO_LINE=25 \
  APRS_GPIO_INVERT=N \
  bash install-raspberry.sh
```

## Arquitetura

```text
Rádio
  │
  ├── áudio RX/TX ── interface ALSA ── Direwolf
  │                                      │
  │                                      ├── APRS-IS
  │                                      ├── RF
  │                                      └── journal systemd
  │
  └── PTT
       ├── Ubuntu: serial DTR/RTS
       └── Raspberry: GPIO/GPIOD

journalctl -u direwolf
          │
          ▼
   Python / FastAPI
          │
          ├── SQLite
          ├── API REST
          └── Dashboard Web
```

O dashboard observa o journal do Direwolf, transforma linhas em eventos estruturados e mantém histórico local. Fechar o navegador não interrompe o Direwolf.

Mais detalhes: [docs/ARQUITETURA.md](docs/ARQUITETURA.md)

## Serviços instalados

```bash
systemctl status direwolf
systemctl status aprs-dashboard
systemctl status aprs-hardware-watchdog
```

Logs:

```bash
journalctl -u direwolf -f
journalctl -u aprs-dashboard -f
journalctl -u aprs-hardware-watchdog -f
```

## Atualização

```bash
sudo -u aprs aprs-update
```

O atualizador:

- verifica se o clone está limpo;
- busca `origin/main`;
- aplica a nova versão;
- valida Python;
- reinicia o dashboard;
- executa health checks;
- faz rollback automático em caso de falha.

## Estrutura do repositório

```text
.
├── app.py
├── database.py
├── dashboard_extensions.py
├── audio_control.py
├── station_config.py
├── offline_maps.py
├── static/
├── scripts/
│   ├── install-common.sh
│   ├── aprs-update.sh
│   └── direwolf-hardware-watchdog.py
├── systemd/
├── install-ubuntu.sh
├── install-raspberry.sh
├── direwolf.conf.example
├── .env.example
├── docs/
│   ├── documentação em português
│   └── en/  documentação em inglês
└── NOTICE.md
```

## Documentação em português

- [Arquitetura](docs/ARQUITETURA.md)
- [Instalação Ubuntu](docs/INSTALACAO-UBUNTU.md)
- [Instalação Raspberry Pi](docs/INSTALACAO-RASPBERRY.md)
- [Configuração](docs/CONFIGURACAO.md)
- [Hardware e PTT](docs/HARDWARE-E-PTT.md)
- [Watchdog e recuperação](docs/WATCHDOG-E-RECUPERACAO.md)
- [Mapas offline](docs/MAPAS-OFFLINE.md)
- [Solução de problemas](docs/SOLUCAO-DE-PROBLEMAS.md)
- [API](docs/API.md)
- [Desenvolvimento](docs/DESENVOLVIMENTO.md)

## Hardware

### Ubuntu

Para PTT serial, prefira um nome persistente:

```text
/dev/serial/by-id/...
```

em vez de depender de `/dev/ttyUSB0`.

### Raspberry Pi

Não é necessário usar uma porta serial apenas para PTT. O Direwolf atual suporta libgpiod:

```text
PTT GPIOD /dev/gpiochip0 25
```

A linha negativa representa inversão:

```text
PTT GPIOD /dev/gpiochip0 -25
```

Confirme o chip e as linhas disponíveis com `gpioinfo`.

## Dados locais

- SQLite: `data/aprs.db`;
- mapas offline: `data/offline-maps/`;
- backups: `data/config-backups/`.

Esses dados não devem ser commitados.

## Créditos

- **Daniel, PP5BK** — programação da configuração-base `direwolf.conf`;
- **Clézio da Cunha Costa, PP5CI** — dashboard, integração e projeto público;
- **ChatGPT/OpenAI** — apoio no desenvolvimento, testes, refatoração e documentação;
- **WB2OSZ e colaboradores** — Direwolf.

Mais detalhes em [NOTICE.md](NOTICE.md).

---

# English

Public project for building an APRS station based on **Direwolf + Linux**, with a modern web dashboard, browser-based configuration, SQLite history, maps, telemetry, hardware monitoring and automatic recovery.

The project grew from a real APRS station and was organized by **Clézio da Cunha Costa, PP5CI**, with ChatGPT/OpenAI supporting development, testing, refactoring and documentation.

> **Important credit:** the base `direwolf.conf` configuration used as the reference for this project was originally programmed by amateur radio operator **Daniel, PP5BK**.

> Direwolf is an independent project maintained by WB2OSZ and contributors. This repository does not redistribute the Direwolf source code; the installers clone and build the official project.

## Goals

The project is intended to be:

- automatically installable;
- easy to study and modify;
- usable on physical Linux hosts, Ubuntu VMs and Raspberry Pi;
- usable as an RX-only iGate;
- expandable to bidirectional iGate, digipeater and RF beacon operation;
- monitored and configured through a browser;
- automatically recoverable after hardware failures.

## Main features

- Direwolf built from the official source;
- RF → APRS-IS iGate;
- optional APRS-IS → RF;
- APRS digipeater;
- APRS-IS and RF beacons;
- serial DTR/RTS PTT on Ubuntu/Linux;
- **native GPIO/GPIOD PTT on Raspberry Pi**, with no serial adapter required;
- FastAPI dashboard;
- real-time APRS traffic;
- SQLite history;
- station map;
- online and offline maps;
- APRS/WX telemetry;
- station details;
- CPU/RAM monitoring;
- USB audio and PTT monitoring;
- RX/TX activity meters;
- browser-based Direwolf configuration;
- automatic `direwolf.conf` backups;
- hardware watchdog;
- systemd recovery;
- updater with health checks and rollback;
- dedicated Ubuntu and Raspberry Pi installers.

## Operational safety

RF TX is **disabled by default**.

Before enabling transmission, verify your license, local regulations, band plan, APRS frequency, power, identification, path settings and local iGate/digipeater policy.

The APRS-IS passcode is calculated locally by the installer and written only to the local `/home/aprs/direwolf.conf`. Do not publish it.

## Quick installation

### Ubuntu

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-ubuntu.sh | sudo bash
```

Detailed guide: [docs/en/INSTALL-UBUNTU.md](docs/en/INSTALL-UBUNTU.md)

Ubuntu normally uses a serial adapter with DTR or RTS for PTT.

### Raspberry Pi OS

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-raspberry.sh | sudo bash
```

Detailed guide: [docs/en/INSTALL-RASPBERRY.md](docs/en/INSTALL-RASPBERRY.md)

Raspberry Pi uses native **GPIOD GPIO PTT** by default. GPIO 25 is the initial default and the gpiochip can be detected or supplied by the operator.

## What the installer does

The installer:

1. installs dependencies;
2. creates the `aprs` service user;
3. builds official Direwolf;
4. installs the dashboard;
5. creates the Python environment;
6. detects ALSA capture hardware;
7. detects serial PTT on Ubuntu or prepares GPIO PTT on Raspberry Pi;
8. collects station parameters;
9. calculates the APRS-IS passcode locally;
10. generates `direwolf.conf`;
11. installs systemd services;
12. installs the hardware watchdog;
13. enables automatic recovery;
14. installs local Leaflet assets;
15. starts services;
16. validates the dashboard API.

Default URLs:

```text
http://DEVICE-IP:8088/
http://DEVICE-IP:8088/config
```

## Architecture

```text
Radio
  │
  ├── RX/TX audio ── ALSA interface ── Direwolf
  │                                      │
  │                                      ├── APRS-IS
  │                                      ├── RF
  │                                      └── systemd journal
  │
  └── PTT
       ├── Ubuntu: serial DTR/RTS
       └── Raspberry Pi: GPIO/GPIOD

journalctl -u direwolf
          │
          ▼
     Python / FastAPI
          │
          ├── SQLite
          ├── REST API
          └── Web dashboard
```

## Services

```bash
systemctl status direwolf
systemctl status aprs-dashboard
systemctl status aprs-hardware-watchdog
```

## Updating

```bash
sudo -u aprs aprs-update
```

The updater validates the working tree, downloads the new revision, validates Python, restarts the dashboard, runs health checks and rolls back if needed.

## English documentation

- [Architecture](docs/en/ARCHITECTURE.md)
- [Ubuntu installation](docs/en/INSTALL-UBUNTU.md)
- [Raspberry Pi installation](docs/en/INSTALL-RASPBERRY.md)
- [Configuration](docs/en/CONFIGURATION.md)
- [Hardware and PTT](docs/en/HARDWARE-PTT.md)
- [Watchdog and recovery](docs/en/WATCHDOG-RECOVERY.md)
- [Offline maps](docs/en/OFFLINE-MAPS.md)
- [Troubleshooting](docs/en/TROUBLESHOOTING.md)
- [API](docs/en/API.md)
- [Development](docs/en/DEVELOPMENT.md)

## Credits

- **Daniel, PP5BK** — original base `direwolf.conf` configuration;
- **Clézio da Cunha Costa, PP5CI** — dashboard, integration and public project;
- **ChatGPT/OpenAI** — development, testing, refactoring and documentation support;
- **WB2OSZ and contributors** — Direwolf.

See [NOTICE.md](NOTICE.md).
