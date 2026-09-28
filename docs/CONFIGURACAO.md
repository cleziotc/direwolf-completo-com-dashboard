# Configuração da estação

## Origem da configuração-base

A configuração-base `direwolf.conf` que serviu de referência para este projeto foi originalmente programada pelo radioamador **Daniel, PP5BK**.

O projeto público transforma essa base em um template parametrizado e em um assistente automatizado.

## Página web

```text
http://IP-DO-EQUIPAMENTO:8088/config
```

A interface altera somente diretivas conhecidas e cria backup antes de gravar.

## Identificação e APRS-IS

Campos principais:

- `MYCALL`;
- `IGLOGIN`;
- `IGSERVER`;
- `IGFILTER`.

O passcode não é devolvido pela API. Se o campo de credencial for deixado em branco durante uma alteração, a credencial existente é preservada.

## Localização

A interface permite configurar latitude, longitude, altitude, altura da antena, ganho e potência.

As coordenadas alimentam os beacons e o filtro APRS-IS.

## Beacon

- `PBEACON`: APRS-IS;
- `OBEACON`: RF.

Confira intervalo, símbolo, potência, path e política regional antes de ativar RF.

## Digipeater

Exemplo:

```text
DIGIPEAT 0 0 ^WIDE$ ^WIDE[1-2]-[1-2]$ TRACE
```

Não copie regras de path indiscriminadamente para outra região.

## IS → RF

Diretivas típicas:

```text
IGTXVIA 0 WIDE1-1
FILTER IG 0 1
IGTXLIMIT 20 80
```

`IGTXLIMIT` protege o canal contra tráfego excessivo.

## Áudio

```text
ADEVICE plughw:0,0
ACHANNELS 1
ARATE 48000
CHANNEL 0
MODEM 1200
```

Descubra dispositivos com:

```bash
arecord -l
```

## PTT serial

Exemplo:

```text
PTT /dev/serial/by-id/usb-... DTR
```

Também são aceitos RTS e inversão com `-DTR` ou `-RTS`.

## PTT GPIO/GPIOD

No Raspberry:

```text
PTT GPIOD /dev/gpiochip0 25
```

Invertido:

```text
PTT GPIOD /dev/gpiochip0 -25
```

A página web permite escolher:

- PTT desabilitado;
- serial DTR/RTS;
- GPIO/GPIOD;
- gpiochip;
- linha GPIO;
- lógica normal ou invertida.

## Temporizações

Principais opções:

- `DWAIT`;
- `SLOTTIME`;
- `PERSIST`;
- `TXDELAY`;
- `TXTAIL`;
- `DEDUPE`.

A interface apresenta TXDELAY em milissegundos e converte para a unidade do Direwolf.

## Backup e rollback

Backups:

```text
/home/aprs/aprs-dashboard/data/config-backups/
```

Se uma configuração nova impedir o Direwolf de subir, o backend tenta restaurar o arquivo anterior.

## Runtime do dashboard

```text
/home/aprs/.config/aprs-dashboard.env
```

Esse arquivo contém parâmetros locais de hardware e apresentação. O passcode APRS-IS permanece no `direwolf.conf`.

## Exemplo público

Veja `direwolf.conf.example`. Ele não contém passcode real nem coordenadas de uma estação específica.
