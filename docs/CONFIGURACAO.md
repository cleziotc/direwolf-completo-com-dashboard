# Configuração da estação

## Página web

Acesse:

```text
http://IP-DO-EQUIPAMENTO:8088/config
```

A página organiza a configuração em blocos e grava somente diretivas conhecidas.

## Identificação e APRS-IS

Principais campos:

- `MYCALL`: indicativo e SSID da estação;
- `IGLOGIN`: login e passcode;
- `IGSERVER`: servidor e porta APRS-IS;
- `IGFILTER`: filtro entregue pelo servidor.

O passcode não é exibido de volta pela API. Se o campo de credencial ficar vazio durante uma alteração, a credencial existente é preservada.

## Localização

São configurados:

- latitude;
- longitude;
- altitude;
- altura da antena;
- ganho;
- potência.

As coordenadas também alimentam o centro do mapa e o filtro APRS-IS.

## Beacon

O projeto suporta:

- `PBEACON` para APRS-IS;
- `OBEACON` para RF.

Antes de habilitar beacon RF, confira frequência, intervalo e política local.

## Digipeater

A diretiva `DIGIPEAT` determina se o Direwolf retransmite pacotes no canal RF.

Uma configuração típica APRS pode usar:

```text
DIGIPEAT 0 0 ^WIDE$ ^WIDE[1-2]-[1-2]$ TRACE
```

Não copie paths indiscriminadamente para regiões com regras diferentes.

## IS → RF

Diretivas relacionadas:

```text
IGTXVIA 0 WIDE1-1
FILTER IG 0 1
IGTXLIMIT 20 80
```

`IGTXLIMIT` limita a quantidade de pacotes que podem sair por RF.

## Áudio

Exemplo:

```text
ADEVICE plughw:0,0
ACHANNELS 1
ARATE 48000
CHANNEL 0
MODEM 1200
```

Confirme o card/device com:

```bash
arecord -l
```

## PTT serial

Exemplo DTR:

```text
PTT /dev/serial/by-id/usb-... DTR
```

Exemplo RTS:

```text
PTT /dev/serial/by-id/usb-... RTS
```

Algumas interfaces necessitam inversão:

```text
PTT /dev/serial/by-id/usb-... -DTR
```

ou:

```text
PTT /dev/serial/by-id/usb-... -RTS
```

## Temporizações

As opções mais comuns são:

- `DWAIT`;
- `SLOTTIME`;
- `PERSIST`;
- `TXDELAY`;
- `TXTAIL`;
- `DEDUPE`.

No Direwolf, `TXDELAY` é configurado em unidades próprias do programa; a página web apresenta o valor de forma mais amigável.

## Backup e rollback

Cada gravação que realmente altera o `direwolf.conf` gera uma cópia em:

```text
/home/aprs/aprs-dashboard/data/config-backups/
```

Se a configuração nova impedir o Direwolf de subir, o backend tenta restaurar o backup anterior.

## Arquivo de runtime do dashboard

```text
/home/aprs/.config/aprs-dashboard.env
```

Esse arquivo guarda parâmetros de hardware e interface do dashboard, mas não precisa conter o passcode APRS-IS.
