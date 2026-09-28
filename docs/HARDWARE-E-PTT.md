# Hardware, áudio e PTT

## Cadeia básica

Uma estação típica utiliza transceptor VHF/UHF, interface de áudio compatível com ALSA, computador Ubuntu ou Raspberry Pi, interface elétrica de PTT e rede quando APRS-IS estiver habilitado.

## Áudio USB

```bash
lsusb
arecord -l
aplay -l
cat /proc/asound/cards
```

Exemplo:

```text
ADEVICE plughw:0,0
```

O instalador registra card/device e, quando possível, VID/PID USB.

## Nível de RX

O VU RX usa o valor relativo publicado pelo Direwolf. Ele **não é um medidor calibrado em dBFS**. Serve para perceber ausência de áudio, comparar ajustes, observar atividade e identificar níveis claramente inadequados.

## VU TX

O dashboard não recebe a amplitude PCM real da transmissão. O VU TX representa atividade de TX, não uma medição absoluta de modulação.

# PTT no Ubuntu/Linux

O caminho normal é serial DTR/RTS:

```text
PTT /dev/serial/by-id/usb-... DTR
PTT /dev/serial/by-id/usb-... RTS
PTT /dev/serial/by-id/usb-... -DTR
PTT /dev/serial/by-id/usb-... -RTS
```

Para instalações permanentes:

```bash
ls -l /dev/serial/by-id/
```

Prefira `/dev/serial/by-id/...` a `/dev/ttyUSB0`.

# PTT no Raspberry Pi

O Raspberry possui GPIO nativo. O projeto utiliza libgpiod:

```text
PTT GPIOD /dev/gpiochip0 25
```

Lógica invertida:

```text
PTT GPIOD /dev/gpiochip0 -25
```

Confira os chips:

```bash
gpioinfo
ls -l /dev/gpiochip*
```

O chip pode variar conforme modelo e kernel.

## Interface elétrica

Não ligue DTR/RTS ou GPIO diretamente ao PTT do rádio sem conhecer os níveis envolvidos. Use um estágio apropriado de chaveamento e confira tensão, corrente, polaridade, nível lógico, isolamento, terra e retorno de RF.

## EMI / RF

Mensagens como:

```text
USB disconnect
device descriptor read/64, error -71
Device not responding to setup address
```

indicam falha abaixo do Direwolf.

Investigue mau contato, cabo USB, porta USB, alimentação, EMI/RF, loops de terra, conversor e controlador USB.

Medidas úteis:

- cabo curto;
- ferrites;
- bom aterramento;
- separação entre RF e USB;
- outra porta;
- outra interface;
- teste com o fio de PTT desconectado do rádio.

## VM / passthrough

Host:

```bash
lsusb -t
journalctl -k -f
```

Guest:

```bash
lsusb
arecord -l
dmesg -wT
```

Se o host já perde o dispositivo físico, alterar o Direwolf dentro da VM não corrige a causa.

## Watchdog

No Ubuntu, o watchdog observa a serial quando uma diretiva PTT serial existe.

No Raspberry, ele observa o `gpiochip` quando existe `PTT GPIOD`.

Em RX-only, PTT não é requisito.
