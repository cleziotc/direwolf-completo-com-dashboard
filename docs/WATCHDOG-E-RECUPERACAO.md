# Watchdog e recuperação automática

## Objetivo

Dispositivos USB podem cair e voltar. Dependendo do driver e do estado do Direwolf, o processo pode continuar ativo sem recuperar corretamente áudio ou PTT.

O projeto adiciona duas camadas de recuperação.

## 1. Restart do systemd

O arquivo:

```text
systemd/direwolf-recovery.conf
```

aplica:

```ini
[Unit]
StartLimitIntervalSec=0

[Service]
Restart=always
RestartSec=5
```

Isso recupera o processo quando ele encerra.

## 2. Watchdog de hardware

O serviço:

```text
aprs-hardware-watchdog.service
```

executa:

```text
scripts/direwolf-hardware-watchdog.py
```

O script lê `ADEVICE` e `PTT` do `direwolf.conf`.

Ele verifica periodicamente:

- se a captura ALSA requerida existe;
- se a serial/PTT configurada existe;
- se o serviço Direwolf está ativo.

Quando um dispositivo anteriormente ausente reaparece e os requisitos estão atendidos, o Direwolf é reiniciado após um pequeno tempo de estabilização.

Em configuração RX-only sem `PTT`, a serial não é tratada como requisito.

## Status

```bash
systemctl status aprs-hardware-watchdog
```

Logs:

```bash
journalctl -u aprs-hardware-watchdog -f
```

## Teste controlado

Para testar uma serial/PTT:

1. acompanhe o watchdog em um terminal;
2. desconecte apenas a serial;
3. confirme o evento de desconexão;
4. reconecte;
5. confirme o restart do Direwolf;
6. valide o serviço.

```bash
journalctl -u aprs-hardware-watchdog -f
```

Não faça esse teste durante uma transmissão crítica.

## O que o watchdog não resolve

Ele não corrige:

- cabo defeituoso;
- mau contato;
- undervoltage;
- falha do conversor;
- EMI;
- erro de enumeração USB no host;
- configuração incorreta de PTT.

O watchdog recupera a aplicação **depois** que o hardware volta a estar disponível.
