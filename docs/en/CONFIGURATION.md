# Station configuration

## Base configuration credit

The base `direwolf.conf` used as a reference for this project was originally programmed by amateur radio operator **Daniel, PP5BK**.

The public project turns that base into a parameterized template and installation wizard.

## Web page

```text
http://DEVICE-IP:8088/config
```

The page edits only known directives and creates a backup before writing.

## Identification and APRS-IS

Main directives:

- `MYCALL`;
- `IGLOGIN`;
- `IGSERVER`;
- `IGFILTER`.

The APRS-IS passcode is not returned by the API. Leaving the credential field blank preserves the existing credential.

## Location and beacons

The UI configures latitude, longitude, altitude, antenna height, gain and transmitter power.

`PBEACON` is used for APRS-IS. `OBEACON` is used for RF.

## Digipeater and IS to RF

Typical directives include:

```text
DIGIPEAT 0 0 ^WIDE$ ^WIDE[1-2]-[1-2]$ TRACE
IGTXVIA 0 WIDE1-1
FILTER IG 0 1
IGTXLIMIT 20 80
```

Do not copy paths or policies blindly between regions.

## Audio

Example:

```text
ADEVICE plughw:0,0
ACHANNELS 1
ARATE 48000
CHANNEL 0
MODEM 1200
```

Discover capture devices with `arecord -l`.

## Serial PTT

```text
PTT /dev/serial/by-id/usb-... DTR
```

RTS and inverted DTR/RTS are supported.

## GPIO/GPIOD PTT

Raspberry Pi example:

```text
PTT GPIOD /dev/gpiochip0 25
```

Inverted:

```text
PTT GPIOD /dev/gpiochip0 -25
```

The web page supports disabled PTT, serial PTT and GPIOD PTT.

## Backups

Configuration backups are stored in:

```text
/home/aprs/aprs-dashboard/data/config-backups/
```

If a new configuration prevents Direwolf from starting, the backend attempts to restore the previous configuration.
