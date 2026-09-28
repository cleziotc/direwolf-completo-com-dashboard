# Hardware, audio and PTT

## Audio interface

Useful commands:

```bash
lsusb
arecord -l
aplay -l
cat /proc/asound/cards
```

Typical Direwolf setting:

```text
ADEVICE plughw:0,0
```

The RX meter in the dashboard uses Direwolf's relative audio level. It is not a calibrated dBFS meter. The TX meter indicates transmission activity and is not an absolute modulation measurement.

## Ubuntu serial PTT

Examples:

```text
PTT /dev/serial/by-id/usb-... DTR
PTT /dev/serial/by-id/usb-... RTS
PTT /dev/serial/by-id/usb-... -DTR
PTT /dev/serial/by-id/usb-... -RTS
```

Prefer persistent `/dev/serial/by-id/...` names.

## Raspberry Pi GPIO PTT

Native GPIO through libgpiod:

```text
PTT GPIOD /dev/gpiochip0 25
```

Inverted logic:

```text
PTT GPIOD /dev/gpiochip0 -25
```

Inspect chips with:

```bash
gpioinfo
ls -l /dev/gpiochip*
```

## Electrical interface

Do not connect serial control lines or GPIO directly to a radio PTT input without verifying electrical requirements. Use an appropriate switching or isolation stage.

## EMI and USB faults

Kernel messages such as:

```text
USB disconnect
device descriptor read/64, error -71
Device not responding to setup address
```

occur below Direwolf. Investigate connectors, USB cables, ports, power, grounding, RF/EMI, converters and host controllers.

## Virtual machines

Compare host and guest logs. If the host loses the physical USB device, changing Direwolf inside the guest cannot fix the underlying fault.
