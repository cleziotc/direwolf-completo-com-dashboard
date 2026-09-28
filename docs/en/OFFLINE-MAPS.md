# Offline maps

## Purpose

The dashboard can store map tiles on the local server so the map remains usable when the online tile provider is unavailable.

This does not make APRS-IS itself offline; it only preserves previously downloaded map layers.

## Layers

The system supports offline packages for:

- street maps;
- satellite imagery.

Files are stored under:

```text
/home/aprs/aprs-dashboard/data/offline-maps/
```

## Download from the configuration page

On `/config`:

1. select the package center;
2. choose a radius;
3. choose the maximum zoom;
4. request an estimate;
5. start the download.

The offline-package center is independent from the official station coordinates.

## Safety limit

The backend limits the maximum number of tiles in one package to prevent accidental massive downloads.

Disk usage grows quickly with larger radius and higher zoom.

## Raspberry Pi

Use conservative radius and zoom values on small SD cards to reduce disk consumption and flash writes.

## Deleting packages

Offline packages can be removed from the web interface. Deleting a package removes its local tile cache.

## Fallback

The dashboard normally uses online tiles. When a remote tile fails, it can fall back to an equivalent local tile if available.
