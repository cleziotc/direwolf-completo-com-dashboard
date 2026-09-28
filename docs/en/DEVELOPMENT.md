# Development and contributions

## Development environment

```bash
git clone https://github.com/cleziotc/direwolf-completo-com-dashboard.git
cd direwolf-completo-com-dashboard
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Python validation

```bash
python3 -m py_compile \
  app.py database.py dashboard_extensions.py audio_control.py \
  station_config.py offline_maps.py scripts/direwolf-hardware-watchdog.py
```

## Shell validation

```bash
bash -n install-ubuntu.sh
bash -n install-raspberry.sh
bash -n scripts/*.sh
```

GitHub Actions performs the project CI checks.

## Do not hard-code local station data

Avoid hard-coding:

- callsign;
- APRS-IS passcode;
- coordinates;
- timezone;
- USB VID/PID;
- ALSA card number;
- serial port;
- gpiochip;
- GPIO line.

These belong to local runtime configuration.

## Do not commit operational data

Do not commit databases, offline map tiles, logs, backups, Python virtual environments, credentials or real station configuration files containing secrets.

## Pull requests

A useful PR should describe:

- the problem;
- the proposed solution;
- OS/hardware tested;
- RX/TX impact;
- reproduction steps;
- validation steps.

Changes affecting TX, PTT, APRS-IS to RF or digipeater behavior require extra care.

## Documentation policy

Portuguese is the primary project documentation. Equivalent English documentation is kept under `docs/en/`.

## Project philosophy

The project prioritizes reproducible installation, 24/7 operation, rollback, observability, safe configuration handling and sharing useful tooling with the amateur radio community.
