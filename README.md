# Direwolf completo com Dashboard

Projeto público para montar uma estação APRS baseada em **Direwolf + Linux**, com dashboard web moderno, configuração pelo navegador, histórico em SQLite, mapas, telemetria, monitoramento de hardware e recuperação automática quando áudio USB ou serial/PTT retornam.

O projeto nasceu de uma estação real e foi desenvolvido por **Clézio da Cunha Costa (PP5CI)**, com apoio do ChatGPT/OpenAI no desenvolvimento, testes e documentação. A proposta deste repositório é devolver à comunidade radioamadora uma solução reproduzível, estudável e modificável.

> O Direwolf é um projeto independente, mantido por seus próprios autores. Este repositório não inclui o código-fonte do Direwolf; os instaladores clonam e compilam o projeto oficial `wb2osz/direwolf`.

## Principais recursos

- Direwolf compilado a partir do repositório oficial.
- iGate APRS RF → APRS-IS.
- Opção de IS → RF.
- Digipeater APRS.
- Beacon para APRS-IS e beacon RF.
- PTT por serial usando DTR ou RTS.
- Dashboard web em FastAPI.
- Tráfego APRS em tempo real.
- Estatísticas diárias e por minuto.
- Histórico SQLite.
- Mapa de estações.
- Cartas de ruas e satélite.
- Download de mapas para operação offline.
- Telemetria meteorológica APRS/WX.
- Detalhes de estação, posição, velocidade, rumo e path.
- Monitoramento de CPU e RAM.
- Monitoramento do áudio USB e da serial/PTT.
- VUs RX/TX no dashboard.
- Página de configuração do Direwolf.
- Backup automático do `direwolf.conf` antes de alterações.
- Watchdog de hardware.
- Reinício automático do Direwolf após reconexão de áudio/serial.
- Recuperação automática do serviço via systemd.
- Atualizador com health check e rollback.
- Instaladores separados para Ubuntu e Raspberry Pi OS.

## Segurança operacional

A instalação mantém **TX RF desabilitado por padrão**. Durante o assistente de instalação é necessário confirmar explicitamente para habilitar PTT, digipeater e IS → RF.

Antes de transmitir, confira sua licença, legislação local, plano de banda, frequência APRS da sua região, potência, identificação, configuração de path e políticas de iGate/digipeater.

O passcode APRS-IS é calculado localmente pelo instalador. Ele é gravado somente no `/home/aprs/direwolf.conf` da sua estação e não deve ser enviado ao GitHub.

## Instalação rápida

### Ubuntu Server / Ubuntu Linux

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-ubuntu.sh | sudo bash
```

Guia completo: [docs/INSTALACAO-UBUNTU.md](docs/INSTALACAO-UBUNTU.md)

### Raspberry Pi OS

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-raspberry.sh | sudo bash
```

Guia completo: [docs/INSTALACAO-RASPBERRY.md](docs/INSTALACAO-RASPBERRY.md)

## O que o instalador faz

O instalador:

1. instala as dependências;
2. cria o usuário de serviço `aprs`;
3. baixa e compila o Direwolf oficial;
4. instala o dashboard em `/home/aprs/aprs-dashboard`;
5. cria o ambiente Python;
6. detecta a placa de áudio;
7. detecta uma interface serial para PTT, quando disponível;
8. pergunta indicativo, coordenadas e parâmetros da estação;
9. calcula o passcode APRS-IS localmente;
10. gera o `direwolf.conf`;
11. instala os serviços systemd;
12. instala o watchdog de hardware;
13. habilita recuperação automática;
14. baixa Leaflet para o servidor;
15. inicia os serviços;
16. testa a API do dashboard.

Ao final, o painel normalmente estará em:

```text
http://IP-DO-EQUIPAMENTO:8088/
```

E a configuração em:

```text
http://IP-DO-EQUIPAMENTO:8088/config
```

## Instalação sem perguntas

Os dois instaladores também aceitam variáveis de ambiente. Exemplo:

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

Para TX, também pode ser necessário informar `APRS_SERIAL_PORT`, principalmente quando houver mais de uma interface serial.

## Arquitetura

```text
Rádio
  │
  ├── Áudio RX/TX ── Placa de som USB
  │                     │
  │                     ▼
  │                  Direwolf
  │                     │
  ├── PTT ───────── Serial DTR/RTS
  │                     │
  │                     ├── APRS-IS
  │                     ├── Journal do systemd
  │                     └── RF
  │
  └─────────────────────────────

journalctl -u direwolf
          │
          ▼
   Coletor Python/FastAPI
          │
          ├── SQLite
          ├── API REST
          └── Dashboard Web
```

O dashboard não substitui o Direwolf. Ele observa o journal do serviço, interpreta os eventos, mantém histórico e apresenta a operação em uma interface web.

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

Depois de instalado:

```bash
sudo -u aprs aprs-update
```

O atualizador verifica o GitHub, aplica a nova versão, reinicia o dashboard, testa APIs e páginas e executa rollback se o novo código não ficar saudável.

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
│   ├── index.html
│   ├── config.html
│   ├── dashboard-v2.css
│   └── dashboard-v2.js
├── scripts/
│   ├── install-common.sh
│   ├── aprs-update.sh
│   └── direwolf-hardware-watchdog.py
├── systemd/
│   ├── direwolf.service
│   ├── direwolf-recovery.conf
│   ├── aprs-dashboard.service
│   └── aprs-hardware-watchdog.service
├── install-ubuntu.sh
├── install-raspberry.sh
├── direwolf.conf.example
├── .env.example
└── docs/
```

## Documentação

- [Arquitetura](docs/ARQUITETURA.md)
- [Instalação no Ubuntu](docs/INSTALACAO-UBUNTU.md)
- [Instalação no Raspberry Pi](docs/INSTALACAO-RASPBERRY.md)
- [Configuração da estação](docs/CONFIGURACAO.md)
- [Hardware e PTT](docs/HARDWARE-E-PTT.md)
- [Watchdog e recuperação](docs/WATCHDOG-E-RECUPERACAO.md)
- [Mapas offline](docs/MAPAS-OFFLINE.md)
- [Solução de problemas](docs/SOLUCAO-DE-PROBLEMAS.md)
- [API do dashboard](docs/API.md)
- [Desenvolvimento e contribuição](docs/DESENVOLVIMENTO.md)

## Observações sobre hardware

O projeto foi pensado para interfaces de áudio reconhecidas pelo ALSA e para PTT serial por DTR/RTS. O instalador tenta detectar ambos automaticamente.

Para instalações permanentes, prefira nomes persistentes como:

```text
/dev/serial/by-id/...
```

em vez de depender exclusivamente de `/dev/ttyUSB0`.

## Dados e privacidade

Os dados operacionais ficam localmente no servidor:

- banco SQLite: `data/aprs.db`;
- mapas offline: `data/offline-maps/`;
- backups de configuração: `data/config-backups/`.

Esses diretórios são ignorados pelo Git para evitar que histórico, mapas e configurações locais sejam publicados por engano.

## Contribuições

Issues, correções de documentação, melhorias de hardware, suporte a novas placas de áudio e melhorias no dashboard são bem-vindas.

Ao reportar problemas, informe:

- distribuição e versão;
- arquitetura (`amd64`, `arm64`, `armhf`);
- versão do Direwolf;
- saída de `arecord -l`;
- saída de `lsusb`;
- trecho relevante de `journalctl`;
- e remova passcodes, tokens ou outras credenciais.

## Créditos

- Direwolf: projeto oficial de WB2OSZ e colaboradores.
- Dashboard e integração: Clézio da Cunha Costa, PP5CI.
- Apoio ao desenvolvimento e documentação: ChatGPT/OpenAI.

Veja também [NOTICE.md](NOTICE.md).
