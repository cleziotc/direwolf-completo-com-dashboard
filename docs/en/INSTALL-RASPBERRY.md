# Raspberry Pi installation

## Key difference

Raspberry Pi does **not need a USB serial adapter only for PTT**. The installer uses native GPIO through libgpiod.

## Automatic installation

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-raspberry.sh | sudo bash
```

## GPIO PTT

Default example:

```text
PTT GPIOD /dev/gpiochip0 25
```

Inverted logic:

```text
PTT GPIOD /dev/gpiochip0 -25
```

GPIO 25 is the initial default. The gpiochip may vary between Raspberry Pi models and kernel versions.

Inspect available chips with:

```bash
gpioinfo
ls -l /dev/gpiochip*
```

## Non-interactive example

```bash
sudo env \
  APRS_NONINTERACTIVE=1 \
  APRS_CALLSIGN=PY1ABC-10 \
  APRS_LOCATION_LABEL="My city" \
  APRS_TIMEZONE=America/Sao_Paulo \
  APRS_LATITUDE=-23.5505 \
  APRS_LONGITUDE=-46.6333 \
  APRS_ENABLE_TX=Y \
  APRS_GPIO_CHIP=/dev/gpiochip0 \
  APRS_GPIO_LINE=25 \
  APRS_GPIO_INVERT=N \
  bash install-raspberry.sh
```

## Low-memory models

The installer reduces build parallelism on low-memory Raspberry Pi systems. Raspberry Pi OS Lite is recommended for small models.

## Power

Where available:

```bash
vcgencmd get_throttled
```

A stable power supply is important because undervoltage can look like USB or peripheral failure.

## Electrical interface

Do not connect a Raspberry Pi GPIO directly to an unknown radio PTT circuit. Use an appropriate transistor, MOSFET, optocoupler or isolated interface and verify voltage, current, logic polarity and grounding.
