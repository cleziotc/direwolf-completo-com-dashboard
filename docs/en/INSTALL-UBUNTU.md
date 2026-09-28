# Ubuntu installation

## Supported environment

The installer targets modern Ubuntu Server/Desktop systems on x86_64 or ARM64. A VM is supported as long as the required USB audio interface and optional serial PTT interface are passed through correctly.

## Before installation

Prepare:

- APRS callsign and SSID;
- latitude and longitude;
- station altitude;
- antenna height and gain;
- transmitter power;
- USB audio interface;
- serial PTT interface if RF TX will be enabled.

For RX-only iGate operation, no serial interface is required.

## Automatic installation

```bash
curl -fsSL https://raw.githubusercontent.com/cleziotc/direwolf-completo-com-dashboard/main/install-ubuntu.sh | sudo bash
```

The installer builds the official Direwolf source, installs the dashboard, detects ALSA and serial hardware, generates `direwolf.conf`, installs systemd services and validates the API.

## Serial PTT

Persistent device names are strongly recommended:

```bash
ls -l /dev/serial/by-id/
```

Typical Direwolf configuration:

```text
PTT /dev/serial/by-id/usb-... DTR
```

RTS and inverted DTR/RTS are also supported.

## VM / Proxmox

Verify the USB device both on the host and inside the guest. If the host kernel already reports USB disconnects or descriptor errors, the fault exists below Direwolf and must be solved at the USB/hardware layer.

## Validation

```bash
systemctl status direwolf --no-pager
systemctl status aprs-dashboard --no-pager
systemctl status aprs-hardware-watchdog --no-pager
curl -fsS http://127.0.0.1:8088/api/status
```

Dashboard:

```text
http://DEVICE-IP:8088/
```
