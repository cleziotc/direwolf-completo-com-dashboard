# Solução de problemas

## Dashboard não abre

```bash
systemctl status aprs-dashboard --no-pager
journalctl -u aprs-dashboard -n 100 --no-pager
curl -v http://127.0.0.1:8088/api/status
ss -lntp | grep 8088
```

## Direwolf não inicia

```bash
systemctl status direwolf --no-pager
journalctl -u direwolf -n 150 --no-pager
```

Teste manual:

```bash
sudo systemctl stop direwolf
sudo -u aprs /usr/local/bin/direwolf -c /home/aprs/direwolf.conf
```

Depois reative o serviço.

## Sem áudio

```bash
arecord -l
cat /proc/asound/cards
grep '^ADEVICE' /home/aprs/direwolf.conf
```

Teste de captura:

```bash
arecord -D plughw:0,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/teste.wav
```

Ajuste card/device conforme seu sistema.

## Serial some no Ubuntu/VM

Guest:

```bash
dmesg -wT | grep -iE 'usb|ttyUSB|ttyACM|disconnect|reset|error'
```

Host, quando houver VM:

```bash
journalctl -k -f
```

Se o host mostra `USB disconnect` e erros de descriptor, a falha é anterior ao Direwolf.

## GPIO/PTT no Raspberry não funciona

Confira:

```bash
grep '^PTT' /home/aprs/direwolf.conf
gpioinfo
ls -l /dev/gpiochip*
id aprs
```

Exemplo esperado:

```text
PTT GPIOD /dev/gpiochip0 25
```

Verifique:

- gpiochip correto;
- número da linha;
- necessidade de inversão;
- grupo `gpio`;
- interface elétrica;
- transistor/opto;
- aterramento;
- retorno de RF.

Para inverter:

```text
PTT GPIOD /dev/gpiochip0 -25
```

## PTT serial não aciona

```bash
grep '^PTT' /home/aprs/direwolf.conf
ls -l /dev/serial/by-id/ /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Possíveis causas:

- DTR em vez de RTS;
- inversão necessária;
- porta diferente;
- falta de permissão;
- interface elétrica incorreta;
- USB desconectado.

## APRS-IS desconectado

```bash
journalctl -u direwolf -f | grep -iE 'igate|server|logresp|connect'
```

Confira Internet/DNS, `IGSERVER`, indicativo, passcode e firewall de saída.

## RX funciona, mas decodifica pouco

Verifique nível de áudio, squelch, frequência, largura de banda, ruído e ganho da interface.

O VU é uma referência operacional, não um instrumento calibrado.

## Watchdog

```bash
systemctl status aprs-hardware-watchdog --no-pager
journalctl -u aprs-hardware-watchdog -n 100 --no-pager
```

O watchdog lê `ADEVICE` e `PTT` do `direwolf.conf`. Em RX-only, não exige PTT.

## Atualização fez rollback

```bash
tail -n 200 /home/aprs/aprs-dashboard/update.log
```

O updater retorna ao commit anterior quando o health check falha.

## SQLite

```bash
ls -lh /home/aprs/aprs-dashboard/data/aprs.db*
```

Com WAL ativo, evite copiar apenas o arquivo principal para backup consistente. Pare o dashboard ou use mecanismos adequados de backup SQLite.

## Informações úteis ao abrir issue

```bash
uname -a
cat /etc/os-release
/usr/local/bin/direwolf -h 2>&1 | head
arecord -l
lsusb
systemctl status direwolf --no-pager
systemctl status aprs-dashboard --no-pager
systemctl status aprs-hardware-watchdog --no-pager
```

No Raspberry, inclua também:

```bash
gpioinfo
vcgencmd get_throttled 2>/dev/null || true
```

Remova passcodes, tokens e outras credenciais antes de publicar logs.
