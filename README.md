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

_TODO._ Add the integration in **Settings → Devices & services → Add integration → Switch Timer** and pick the
entity to control. Each controlled entity gets its own entry with:

- `number.<name>_run_time`: the run time in minutes.
- `sensor.<name>_ends_at`: when the current timed run ends.

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

_TODO._

| Action | Description |
|---|---|
| `switch_timer.start` | Turn on and start a timed run (`minutes` optional). |
| `switch_timer.extend` | Add `minutes` (default 15) to an active timed run. |
| `switch_timer.stop` | Turn off and clear the run. |

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

## License

[MIT](LICENSE)
