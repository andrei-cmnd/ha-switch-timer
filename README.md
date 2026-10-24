# Switch Timer

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/andrei-cmnd/ha-switch-timer/actions/workflows/validate.yml/badge.svg)](https://github.com/andrei-cmnd/ha-switch-timer/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Turn a switch on **from a dashboard card** for a set time. It turns off by itself when the time is up.
Turning the switch on from anywhere else does **not** start a timer.

A Home Assistant integration (2026.10+) with a bundled Lovelace card, `custom:switch-timer-card`.

> **Status:** early development. Nothing is released yet.

## Features

- Start a timed run from the card or with the `switch_timer.start` action.
- Turning the device on anywhere else keeps it on with **no timer** (manual mode).
- Turning the device off from anywhere cancels the timed run.
- Extend a running timer (`+15 min` by default) or stop it right away.
- Survives restarts: if a timed run ended while Home Assistant was down, the device is turned off as soon as it becomes available.
- Works with `switch`, `light`, `fan` and `input_boolean` entities.
- The card is registered automatically. It needs no extra Lovelace resource and no button-card, circular-timer-card or card-mod.

## Installation

### HACS (custom repository)

_TODO (v0.1.0)._

### Manual

_TODO (v0.1.0)._

## Configuration

Go to **Settings → Devices & services → Add integration → Switch Timer** and fill in:

- **Entity**: the switch, light, fan or toggle helper to control. Each entity can have one Switch Timer.
- **Name**: optional. Defaults to the entity's name.
- **Default run time**: how many minutes a run lasts when no time is given (default 30).

Each entry creates a device with two entities:

| Entity | Description |
|---|---|
| `number.<name>_run_time` | Run time in minutes, used when a run starts without `minutes`. Kept across restarts. |
| `sensor.<name>_ends_at` | When the current timed run ends; `unknown` when there is none. Attributes: `mode` (`off`, `timed` or `manual`), `duration` (seconds, including extensions) and `started_at`. |

**Configure** on the entry sets the run time's minimum, maximum and step (default 1–240, step 1), the default run
time, and the extend step (default 15 minutes).

### How it behaves

| Situation | Result |
|---|---|
| Run started from the card or `switch_timer.start` | Turns on and starts a timed run. |
| Turned on anywhere else | Stays on with no timer (`manual`). |
| Turned off anywhere during a timed run | The run is cancelled. |
| End time reached | Turns off. If the entity is unavailable then, it's turned off when it comes back. |
| Home Assistant restarts during a timed run | The run is restored. If its end time passed meanwhile, the entity is turned off once it's available. If the entity is found off, the run is dropped. |
| Home Assistant restarts while on without a timer | Nothing happens. |

## Card

_TODO._

```yaml
type: custom:switch-timer-card
entity: switch.my_pump
```

| Option | Description |
|---|---|
| `entity` | **Required.** The controlled entity. |
| `name` | Card title (default: entry name). |
| `icon` | Header icon (default: `mdi:power`). |
| `presets` | Preset buttons in minutes (default: `[15, 30, 60, 120]`). |
| `extend_minutes` | Minutes added by the extend button (default: `15`). |
| `show_hints` | Show the hint line (default: `true`). |

## Actions

Target either the controlled entity or one of the Switch Timer's own entities.

| Action | Description |
|---|---|
| `switch_timer.start` | Turn on and start a timed run. `minutes` is optional and defaults to the run time number. |
| `switch_timer.extend` | Add `minutes` (default: the extend step, 15) to the active timed run. Does nothing without one. |
| `switch_timer.stop` | Turn off and clear the run. Also turns off an entity that was turned on manually. |

```yaml
action: switch_timer.start
target:
  entity_id: switch.my_pump
data:
  minutes: 45
```

## Without installing: blueprints

The original version of this feature is two blueprints plus helpers (a timer and a toggle per switch).
They are kept in [`blueprints/`](blueprints) for people who don't want a custom integration:

- [Timed switch – auto off (automation)](blueprints/automation/switch_timer/timed_switch_auto_off.yaml)
  [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fandrei-cmnd%2Fha-switch-timer%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fswitch_timer%2Ftimed_switch_auto_off.yaml)
- [Timed switch – control (script)](blueprints/script/switch_timer/timed_switch_control.yaml)
  [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fandrei-cmnd%2Fha-switch-timer%2Fblob%2Fmain%2Fblueprints%2Fscript%2Fswitch_timer%2Ftimed_switch_control.yaml)

## Development

1. Open the repo in VS Code and choose **Reopen in Container**. This needs Docker and the Dev Containers extension.
2. Run the task **Run Home Assistant on port 8123** (or `scripts/develop`).
3. Open <http://localhost:8123> and finish onboarding. `custom_components/switch_timer` is loaded from the
   working tree, and a test device `switch.test_pump` is available.

Restart Home Assistant (stop the task and start it again) after you change Python code. `scripts/lint` formats and lints the code with ruff.
`scripts/test` runs the tests with coverage.

Never run `hass` or the tests as root or with `sudo`: root-owned files in `config/` make Home Assistant fail with a
`PermissionError`. Both scripts refuse to run as root. `scripts/develop` takes back ownership of `config/` (using
`sudo chown`) if it finds files there that you don't own.

## License

[MIT](LICENSE)
