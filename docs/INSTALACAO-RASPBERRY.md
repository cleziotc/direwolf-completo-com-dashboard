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

Confirme a interface de áudio:

```bash
arecord -l
aplay -l
cat /proc/asound/cards
```

Confira os GPIO chips:

```bash
gpioinfo
ls -l /dev/gpiochip*
```

## Instalação automática

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-raspberry.sh | sudo bash
```

O instalador instala as dependências, cria o usuário `aprs`, compila o Direwolf oficial, instala o dashboard, detecta ALSA, prepara GPIOD, gera a configuração, instala systemd/watchdog e valida a API.

## PTT por GPIO

Forma padrão:

```text
PTT GPIOD /dev/gpiochip0 25
```

Para lógica invertida:

```text
PTT GPIOD /dev/gpiochip0 -25
```

O padrão inicial do instalador é GPIO 25. O sinal negativo é interpretado pelo Direwolf como inversão.

## Por que não usar serial no Raspberry?

O Raspberry já possui GPIO no conector de expansão. Adicionar um conversor USB/serial apenas para obter DTR/RTS aumenta cabos, consumo USB e pontos de falha. Por isso o instalador Raspberry usa GPIO nativo como padrão.

## Escolha do gpiochip

O número do gpiochip pode variar conforme modelo e kernel.

Confira:

```bash
gpioinfo
for c in /sys/class/gpio/gpiochip*; do
  echo "$c label=$(cat "$c/label" 2>/dev/null) ngpio=$(cat "$c/ngpio" 2>/dev/null)"
done
```

O instalador tenta localizar automaticamente um chip `pinctrl`. Se necessário, informe manualmente `/dev/gpiochip0`, `/dev/gpiochip4` ou o dispositivo correto do seu sistema.

## Instalação não interativa

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

Para RX-only, use `APRS_ENABLE_TX=N`.

## Raspberry Pi Zero

Em pouca RAM, o instalador reduz automaticamente o paralelismo de compilação. Prefira Raspberry Pi OS Lite, espaço livre no cartão e raio de mapas offline conservador.

## Alimentação

```bash
vcgencmd get_throttled
```

Quando disponível, `0x0` indica ausência de flags atuais ou históricas de undervoltage/throttling.

## Teste após instalação

```bash
systemctl status direwolf --no-pager
systemctl status aprs-dashboard --no-pager
systemctl status aprs-hardware-watchdog --no-pager
grep '^PTT' /home/aprs/direwolf.conf
journalctl -u direwolf -f
```

## Interface elétrica do PTT

O GPIO não deve ser conectado indiscriminadamente ao PTT do rádio. Use transistor, MOSFET, optoacoplador ou interface apropriada. Verifique tensão, corrente, polaridade, aterramento e retorno de RF.

## Operação 24/7

O watchdog entende `PTT GPIOD` e observa o gpiochip. Em RX-only, PTT não é requisito.
