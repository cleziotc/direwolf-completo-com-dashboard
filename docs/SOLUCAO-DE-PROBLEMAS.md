# Solução de problemas

## Dashboard não abre

```bash
systemctl status aprs-dashboard --no-pager
journalctl -u aprs-dashboard -n 100 --no-pager
curl -v http://127.0.0.1:8088/api/status
```

Confira se a porta está ouvindo:

```bash
ss -lntp | grep 8088
```

## Direwolf não inicia

```bash
systemctl status direwolf --no-pager
journalctl -u direwolf -n 150 --no-pager
```

Teste manualmente como usuário APRS:

```bash
sudo -u aprs /usr/local/bin/direwolf -c /home/aprs/direwolf.conf
```

Pare o serviço antes do teste manual para evitar conflito de áudio/serial.

## Sem áudio

```bash
arecord -l
cat /proc/asound/cards
grep '^ADEVICE' /home/aprs/direwolf.conf
```

Teste gravação:

```bash
arecord -D plughw:0,0 -f S16_LE -r 48000 -c 1 -d 5 /tmp/teste.wav
```

Ajuste card/device conforme seu sistema.

## Serial some

Guest:

```bash
dmesg -wT | grep -iE 'usb|ttyUSB|ttyACM|disconnect|reset|error'
```

Host, quando houver VM:

```bash
journalctl -k -f
```

Se o host mostra `USB disconnect` e erros de descriptor, a falha é anterior ao Direwolf.

## APRS-IS desconectado

```bash
journalctl -u direwolf -f | grep -iE 'igate|server|logresp|connect'
```

Confira:

- Internet/DNS;
- `IGSERVER`;
- indicativo;
- passcode;
- firewall de saída.

## RX funciona, mas não decodifica bem

Verifique:

- nível de áudio;
- squelch;
- de-emphasis/pre-emphasis conforme interface;
- largura de banda;
- frequência;
- ruído;
- ganho da interface.

O VU do dashboard é apenas referência operacional.

## PTT não aciona

Confira a linha:

```bash
grep '^PTT' /home/aprs/direwolf.conf
```

Teste se o dispositivo existe:

```bash
ls -l /dev/serial/by-id/ /dev/ttyUSB* 2>/dev/null
```

Possíveis causas:

- DTR em vez de RTS;
- necessidade de inversão;
- falta de permissão;
- transistor/opto incorreto;
- serial diferente;
- interface desconectada.

## Atualização fez rollback

Veja:

```bash
tail -n 200 /home/aprs/aprs-dashboard/update.log
```

O updater retorna ao commit anterior quando um health check falha.

## SQLite

Para verificar o banco:

```bash
ls -lh /home/aprs/aprs-dashboard/data/aprs.db*
```

Nunca copie apenas o arquivo principal enquanto WAL está ativo se você precisa de uma cópia consistente. Pare o dashboard ou use mecanismos adequados de backup SQLite.

## Informações úteis ao abrir issue

```bash
uname -a
cat /etc/os-release
/usr/local/bin/direwolf -h 2>&1 | head
arecord -l
lsusb
systemctl status direwolf --no-pager
systemctl status aprs-dashboard --no-pager
```

Remova qualquer credencial antes de publicar logs.
