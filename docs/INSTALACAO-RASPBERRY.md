# Instalação no Raspberry Pi

## Objetivo

O instalador Raspberry prepara uma estação APRS completa com Direwolf, dashboard, SQLite, mapas, watchdog e serviços systemd.

A diferença principal em relação ao Ubuntu é o PTT: **no Raspberry Pi não é necessário usar uma porta serial apenas para chavear o transmissor**. O instalador utiliza GPIO nativo através de **libgpiod**.

## Sistemas e arquiteturas

O objetivo é suportar Raspberry Pi OS baseado em Debian em 32 e 64 bits.

Modelos com pouca RAM, como Pi Zero/Zero 2, podem ser utilizados, mas a compilação do Direwolf e a geração de mapas offline demoram mais.

## Preparação recomendada

Atualize o sistema:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

Depois conecte a interface de áudio USB e confirme:

```bash
arecord -l
aplay -l
cat /proc/asound/cards
```

Para PTT GPIO, confira os chips disponíveis:

```bash
gpioinfo
ls -l /dev/gpiochip*
```

## Instalação automática

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-raspberry.sh | sudo bash
```

O instalador:

1. instala compiladores, ALSA, libudev, Avahi, Python e **libgpiod**;
2. cria o usuário `aprs`;
3. adiciona o usuário aos grupos necessários, inclusive `gpio` quando disponível;
4. compila o Direwolf oficial;
5. instala o dashboard;
6. detecta a placa ALSA;
7. prepara PTT GPIOD;
8. pergunta os dados da estação;
9. gera o `direwolf.conf`;
10. instala os serviços;
11. valida a API.

## PTT por GPIO

A forma moderna utilizada pelo projeto é:

```text
PTT GPIOD /dev/gpiochip0 25
```

O número final é a linha GPIO. O padrão do instalador é GPIO 25.

Para lógica invertida:

```text
PTT GPIOD /dev/gpiochip0 -25
```

O sinal negativo é interpretado pelo Direwolf como inversão do PTT.

### Por que não usar serial no Raspberry?

O Raspberry já possui GPIO no conector de expansão. Adicionar um conversor USB/serial somente para produzir DTR ou RTS aumenta:

- número de cabos;
- consumo USB;
- pontos de falha;
- risco de mudança de `ttyUSB0`;
- necessidade de watchdog para uma interface que não é necessária.

Por isso o instalador Raspberry usa GPIO nativo como padrão.

## Escolha do gpiochip

Dependendo do modelo e do kernel, o chip responsável pelo header pode não ter sempre o mesmo número.

Confira:

```bash
gpioinfo
for c in /sys/class/gpio/gpiochip*; do
  echo "$c  label=$(cat "$c/label" 2>/dev/null)  ngpio=$(cat "$c/ngpio" 2>/dev/null)"
done
```

O instalador tenta localizar um chip `pinctrl` adequado. Se necessário, informe manualmente:

```text
/dev/gpiochip0
/dev/gpiochip4
```

Use a saída real do seu Raspberry como referência.

## Instalação não interativa

Exemplo:

```bash
sudo env \
  APRS_NONINTERACTIVE=1 \
  APRS_CALLSIGN=PY1ABC-10 \
  APRS_LOCATION_LABEL="Minha cidade" \
  APRS_TIMEZONE=America/Sao_Paulo \
  APRS_LATITUDE=-23.5505 \
  APRS_LONGITUDE=-46.6333 \
  APRS_ALTITUDE_M=760 \
  APRS_ANTENNA_HEIGHT_M=20 \
  APRS_ANTENNA_GAIN_DBI=3 \
  APRS_POWER_W=5 \
  APRS_FILTER_RADIUS_KM=100 \
  APRS_ENABLE_TX=S \
  APRS_GPIO_CHIP=/dev/gpiochip0 \
  APRS_GPIO_LINE=25 \
  APRS_GPIO_INVERT=N \
  bash install-raspberry.sh
```

Para RX-only, use:

```text
APRS_ENABLE_TX=N
```

Nesse caso nenhuma linha PTT é exigida.

## Raspberry Pi Zero

O instalador reduz automaticamente o paralelismo da compilação quando detecta pouca RAM.

Recomendações:

- Raspberry Pi OS Lite;
- cartão com espaço livre;
- nenhuma compilação pesada paralela;
- raio de mapas offline conservador;
- fonte de alimentação estável.

## Alimentação

Problemas de alimentação podem causar quedas USB e comportamento instável.

Quando disponível:

```bash
vcgencmd get_throttled
```

`0x0` indica ausência de flags atuais ou históricas de undervoltage/throttling.

## Teste após instalação

```bash
systemctl status direwolf --no-pager
systemctl status aprs-dashboard --no-pager
systemctl status aprs-hardware-watchdog --no-pager
```

Confira a configuração de PTT:

```bash
grep '^PTT' /home/aprs/direwolf.conf
```

Confira logs:

```bash
journalctl -u direwolf -f
```

## Interface elétrica do PTT

O GPIO não deve ser conectado indiscriminadamente ao PTT do rádio.

Utilize circuito compatível, por exemplo:

- transistor;
- MOSFET adequado;
- optoacoplador;
- interface isolada.

Observe tensão, corrente, polaridade, aterramento e retorno de RF.

## Operação 24/7

```bash
systemctl is-enabled direwolf
systemctl is-enabled aprs-dashboard
systemctl is-enabled aprs-hardware-watchdog
```

O watchdog considera o `gpiochip` como recurso de PTT. Se o sistema for RX-only, PTT não é requisito para manter o Direwolf ativo.
