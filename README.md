# OctoPrint-PotatoRelay

An [OctoRelay](https://github.com/borisbu/OctoRelay)-style relay control plugin for OctoPrint,
built for the **Libre Computer "Le Potato" (AML-S905X-CC)**, using
[`libregpio`](https://libregpio.readthedocs.io/) instead of `RPi.GPIO`/`lgpio`.

## Features

- Up to 8 relays, each independently configurable
- Custom labels and ON/OFF icons (emoji or HTML), shown as buttons in the navbar
- Toggle relays from:
  - The navbar buttons
  - GCODE: `@OCTORELAY r1 [ON|OFF]` (omit ON/OFF to toggle)
  - The REST API (`update`, `getStatus`, `listAllStatus` , same shape as OctoRelay's API)
- Inverted output support (for normally-closed relays)
- Optional confirmation dialog before turning a relay OFF
- "Printer relay" mode: disconnects the printer when turned OFF, and
  reconnects (after an optional delay) when turned ON
- Automation events per relay: on Startup, on Printing Started, on Printing
  Stopped, and a delayed action after being turned ON
- Optional shell command side effects on ON/OFF

## Requirements

- A Libre Computer Le Potato (or compatible AML-S905X-CC board) running OctoPrint
- Python 3
- [`libregpio`](https://libregpio.readthedocs.io/en/latest/installation.html) , installed via `apt` as a dependency
- The `octoprint` user needs permission to access `/dev/gpiochip*`. If relays
  don't respond, add the user running OctoPrint to the `gpio` group (create it
  if it doesn't exist) and reboot:

  ```bash
  sudo groupadd -f gpio
  sudo usermod -aG gpio octoprint
  sudo reboot
  ```

## Installation

From the plugin's source directory:

```bash
~/oprint/bin/pip install .
```

Or via the OctoPrint Plugin Manager's
"Install from URL" using the archive URL of your repo.

## Configuring pins

Unlike Raspberry Pi's numeric GPIO scheme, `libregpio` addresses pins by
**name**, e.g. `GPIOX_4`, `GPIOX_5`, `GPIOAO_2`. Enter the pin name (not a
number) in each relay's "GPIO pin name" field. See the Libre Computer GPIO
header reference for the Le Potato to find the correct pin names:
<https://docs.google.com/spreadsheets/d/1U3z0Gb8HUEfCIMkvqzmhMpJfzRqjPXq7mFLC-hvbKlE/edit?pli=1&gid=0#gid=0/>

## API

Same request/response shape as OctoRelay:

```bash
curl 'http://octopi.local/api/plugin/potatorelay' \
  -H 'X-Api-Key: YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{ "command": "update", "subject": "r1", "target": false }'
```

Commands: `update` (subject, optional target bool), `getStatus` (subject),
`listAllStatus`.

## Notes / limitations vs. upstream OctoRelay

- Pin naming uses libregpio's string pin names instead of BCM numbers.
- The settings UI here is simplified (a single set of tabbed fields) rather
  than OctoRelay's full multi-widget settings panel , all the same
  per-relay options are present, just laid out more plainly.
- "Alert on switches ahead" (from upstream OctoRelay) isn't implemented.
- `libregpio`'s PWM class is explicitly noted upstream as unreliable, so PWM
  dimming isn't exposed here , only straightforward ON/OFF switching.
- This hasn't been hardware-tested against a live Le Potato + relay board ,
  treat it as a solid starting point and check `~/.octoprint/logs/octoprint.log`
  while wiring things up.
