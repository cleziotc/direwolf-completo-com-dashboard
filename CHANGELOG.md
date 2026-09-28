# Changelog

## 1.0.1 - 2026-09-28

Hardening pós-publicação:

- renderização dos serviços systemd com usuário, grupo e caminhos configurados pelo instalador;
- criação consistente do grupo do usuário de serviço;
- suporte real a `APRS_USER`, `APRS_HOME` e `APRS_DASHBOARD_DIR` personalizados;
- restauração do CI contra dados da estação original sem bloquear o crédito público a PP5CI;
- verificação de padrões comuns de tokens acidentalmente publicados.

## 1.0.0 - 2026-09-28

Primeira publicação comunitária.

Inclui:

- dashboard APRS derivado de uma estação real;
- parametrização de indicativo, timezone, coordenadas e hardware;
- configuração web;
- histórico SQLite;
- telemetria APRS/WX;
- mapas online e offline;
- iGate RF → APRS-IS;
- opção de APRS-IS → RF;
- digipeater;
- monitoramento de CPU/RAM;
- console de áudio com VUs;
- PTT serial DTR/RTS em Ubuntu/Linux;
- PTT nativo GPIO/GPIOD em Raspberry Pi;
- watchdog compatível com áudio, serial, GPIO e RX-only;
- recuperação systemd;
- atualizador com health check e rollback;
- instalador Ubuntu automatizado;
- instalador Raspberry Pi OS automatizado;
- TX desabilitado por padrão;
- documentação detalhada em português;
- documentação equivalente em inglês sob `docs/en/`;
- CI de Python e Bash;
- template público de `direwolf.conf` sem credenciais;
- crédito a **Daniel, PP5BK**, pela programação da configuração-base `direwolf.conf`.
