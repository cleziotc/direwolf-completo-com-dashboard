# Changelog

## 1.0.2 - 2026-09-28

Hardening complementar após auditoria da branch antiga:

- mantém a renderização systemd já adotada na `main` e completa o `sudoers` para os três serviços gerenciados;
- torna `aprs-update` e o instalador legado de hooks independentes de `/home/aprs/aprs-dashboard`;
- evita que o atualizador sobrescreva unidades systemd já renderizadas para instalações com caminhos personalizados;
- uniformiza os nomes completos `.service` nas operações systemd;
- troca o timezone do arquivo de exemplo para `UTC`;
- adiciona auditoria genérica contra SSID de desenvolvimento, passcodes APRS-IS literais, coordenadas Direwolf literais, tokens e chaves privadas;
- remove do próprio CI os valores privados que anteriormente eram usados como padrões literais de bloqueio.

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
