# System architecture

## Overview

The solution is divided into four layers:

1. RF and hardware;
2. Direwolf;
3. Python collector/API;
4. web interface.

The browser is not part of the critical RF path. Closing the dashboard does not stop Direwolf.

## Receive path

```text
Radio → audio → ALSA → Direwolf → AX.25/APRS
                              │
                              ├→ APRS-IS
                              └→ systemd journal
```

The dashboard follows `journalctl -u direwolf` and converts relevant lines into structured events such as `RF_RX`, `RF_TO_IS`, `IS_RX`, `TX_RF`, `DUPLICATE_DROP` and `AUDIO_LEVEL`.

When possible, `aprslib` extracts position, symbol, speed, course, altitude, comment and weather data.

## Transmit path

```text
APRS-IS → Direwolf → filters/protection → audio → radio
                                           │
                                           └→ PTT
```

PTT methods:

- Ubuntu/Linux: serial DTR/RTS;
- Raspberry Pi: GPIO through GPIOD.

The dashboard does not key PTT directly. Direwolf remains the authoritative transmitter controller.

## SQLite

The local database is:

```text
/home/aprs/aprs-dashboard/data/aprs.db
```

WAL mode is used for better read/write concurrency.

## Services

```text
direwolf.service
aprs-dashboard.service
aprs-hardware-watchdog.service
```

The hardware watchdog understands ALSA capture, serial PTT, GPIOD PTT and RX-only operation without PTT.
