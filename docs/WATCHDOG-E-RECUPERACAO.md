# Watchdog e recuperação automática

## Objetivo

Interfaces USB e outros recursos de hardware podem desaparecer e voltar. O Direwolf nem sempre recupera automaticamente um dispositivo removido durante a execução.

O projeto adiciona duas camadas de recuperação.

## 1. Recuperação pelo systemd

```text
systemd/direwolf-recovery.conf
```

Aplica:

```ini
[Unit]
StartLimitIntervalSec=0

[Service]
Restart=always
RestartSec=5
```

Isso recupera o processo quando ele encerra.

## 2. Watchdog de hardware

Serviço:

```text
aprs-hardware-watchdog.service
```

Script:

```text
scripts/direwolf-hardware-watchdog.py
```

O watchdog lê o `direwolf.conf` e identifica `ADEVICE` e o método de PTT.

### Áudio

Para ALSA numérico, como `plughw:0,0`, o watchdog procura o card/device em `arecord -l`.

### PTT serial

Quando existe:

```text
PTT /dev/serial/by-id/... DTR
```

a porta passa a ser requisito. Se desaparecer e reaparecer, o watchdog reinicia o Direwolf quando todo o hardware necessário está novamente disponível.

### PTT GPIOD

Quando existe:

```text
PTT GPIOD /dev/gpiochip0 25
```

o watchdog verifica a disponibilidade do gpiochip.

### RX-only

Sem diretiva `PTT`, nenhum recurso de PTT é exigido. Apenas o áudio necessário à recepção é monitorado.

## Estado do serviço

```bash
systemctl status aprs-hardware-watchdog
journalctl -u aprs-hardware-watchdog -f
```

## Teste controlado de serial

1. acompanhe o journal;
2. remova a interface serial;
3. aguarde o evento;
4. reconecte;
5. confira o restart;
6. valide o Direwolf.

## Teste de GPIO

Não é necessário desconectar fisicamente um GPIO. Para validar GPIOD:

```bash
ls -l /dev/gpiochip*
gpioinfo
grep '^PTT' /home/aprs/direwolf.conf
systemctl restart direwolf
systemctl status direwolf --no-pager
```

Faça o teste elétrico com interface adequada e sem gerar transmissão indevida.

## O que o watchdog não resolve

Ele não corrige:

- cabo defeituoso;
- mau contato;
- undervoltage;
- EMI;
- falha do conversor;
- configuração elétrica incorreta;
- erro de enumeração USB no host;
- gpiochip/linha escolhidos incorretamente.

O watchdog recupera software quando o recurso volta a ficar disponível; ele não elimina a causa física.
