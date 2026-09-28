# Troubleshooting

## Dashboard does not open

```bash
systemctl status aprs-dashboard --no-pager
journalctl -u aprs-dashboard -n 100 --no-pager
curl -v http://127.0.0.1:8088/api/status
ss -lntp | grep 8088
```

## Direwolf does not start

```bash
systemctl status direwolf --no-pager
journalctl -u direwolf -n 150 --no-pager
```

Manual test:

```bash
sudo systemctl stop direwolf
sudo -u aprs /usr/local/bin/direwolf -c /home/aprs/direwolf.conf
```

## No audio

```bash
arecord -l
cat /proc/asound/cards
grep '^ADEVICE' /home/aprs/direwolf.conf
```

## Serial PTT disappears

Inside the guest:

```bash
dmesg -wT | grep -iE 'usb|ttyUSB|ttyACM|disconnect|reset|error'
```

On the virtualization host:

```bash
journalctl -k -f
```

If the host already reports a physical USB disconnect, the problem is below Direwolf.

## Raspberry GPIO PTT does not work

```bash
grep '^PTT' /home/aprs/direwolf.conf
gpioinfo
ls -l /dev/gpiochip*
id aprs
```

Check gpiochip, line number, inversion, `gpio` group membership, electrical interface, grounding and RF feedback.

## APRS-IS disconnected

```bash
journalctl -u direwolf -f | grep -iE 'igate|server|logresp|connect'
```

Check Internet/DNS, `IGSERVER`, callsign, passcode and outbound firewall policy.

## Updater rolled back

```bash
tail -n 200 /home/aprs/aprs-dashboard/update.log
```

The updater restores the previous commit when a health check fails.

## Information for an issue

```bash
uname -a
cat /etc/os-release
/usr/local/bin/direwolf -h 2>&1 | head
arecord -l
lsusb
systemctl status direwolf --no-pager
systemctl status aprs-dashboard --no-pager
systemctl status aprs-hardware-watchdog --no-pager
```

Remove passcodes, tokens and other credentials before publishing logs.
