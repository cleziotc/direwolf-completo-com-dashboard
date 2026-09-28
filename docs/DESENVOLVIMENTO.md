# Desenvolvimento e contribuição

## Preparar ambiente

```bash
git clone https://github.com/cleziotc/direwolf-completo-com-dashboard.git
cd direwolf-completo-com-dashboard
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Validar sintaxe

```bash
python3 -m py_compile \
  app.py database.py dashboard_extensions.py audio_control.py \
  station_config.py offline_maps.py scripts/direwolf-hardware-watchdog.py
```

Scripts:

```bash
bash -n install-ubuntu.sh
bash -n install-raspberry.sh
bash -n scripts/*.sh
```

O repositório possui GitHub Actions para executar essas verificações.

## Não commitar

A lista inclui:

- `.env`;
- banco SQLite;
- mapas baixados;
- logs;
- backups;
- venv;
- credenciais.

Confira sempre:

```bash
git status
git diff
```

antes de publicar.

## Pull requests

Uma boa PR deve explicar:

- problema;
- solução;
- hardware/OS testado;
- impacto em RX/TX;
- como reproduzir;
- como validar.

Para mudanças em TX, PTT, filtros ou digipeater, inclua atenção especial a comportamento de segurança e compatibilidade com configurações existentes.

## Compatibilidade

Evite hardcode de:

- indicativo;
- coordenadas;
- timezone;
- VID/PID;
- card ALSA;
- serial;
- gpiochip;
- linha GPIO.

Esses dados pertencem ao ambiente local e devem vir de configuração.

## Filosofia

O projeto privilegia:

- instalação reproduzível;
- operação 24/7;
- rollback;
- observabilidade;
- proteção contra perda de configuração;
- documentação principal em português;
- documentação equivalente em inglês sob `docs/en/`;
- compartilhamento com a comunidade radioamadora.
