# Watchdog and automatic recovery

## Purpose

USB and other hardware resources may disappear and return while Direwolf is running. The project adds two recovery layers.

## systemd recovery

The `direwolf-recovery.conf` drop-in sets:

```ini
[Unit]
StartLimitIntervalSec=0

[Service]
Restart=always
RestartSec=5
```

## Hardware watchdog

`aprs-hardware-watchdog.service` runs `scripts/direwolf-hardware-watchdog.py`.

The script reads `ADEVICE` and `PTT` directly from `direwolf.conf`.

It supports:

- ALSA capture devices;
- serial PTT;
- GPIOD PTT;
- RX-only operation without PTT.

For serial PTT, the configured device path must exist. For GPIOD, the gpiochip device must exist. When a required device returns and all required hardware is available, Direwolf is restarted after a short stabilization delay.

## Status and logs

```bash
systemctl status aprs-hardware-watchdog
journalctl -u aprs-hardware-watchdog -f
```

## Limitations

The watchdog does not fix bad cables, poor contacts, undervoltage, RF interference, broken USB adapters, wrong GPIO selection or electrical interface problems. It only recovers software after the required resource becomes available again.
