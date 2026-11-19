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
- No per-switch setup: pick a switch in the card and its timer is created automatically.
- The card is registered automatically. It needs no extra Lovelace resource and no button-card, circular-timer-card or card-mod.

## Installation

1. Install with HACS (custom repository). _Details: TODO (v0.1.0)._
2. Restart Home Assistant.
3. Once: **Settings → Devices & services → Add integration → Switch Timer → Submit**. There is nothing to fill in.
   Switch Timer then appears under **Integrations**.
4. **Reload the browser page once** (F5), as the success message says. Home Assistant adds the card to pages
   loaded after setup; a page that was already open doesn't pick it up until it is reloaded. No restart is needed.

That's all the setup there is. Timers are created by picking a switch in a Switch Timer card (see [Card](#card)).

## Configuration

Every switch, light, fan or toggle picked in a card gets its own timer: a device named after the entity, with two
entities:

| Entity | Description |
|---|---|
| `number.<name>_run_time` | Run time in minutes, used when a run starts without `minutes`. Kept across restarts. |
| `sensor.<name>_ends_at` | When the current timed run ends; `unknown` when there is none. Attributes: `mode` (`off`, `timed` or `manual`), `duration` (seconds, including extensions), `started_at` and `controlled_entity_id`. |

New timers use the defaults: run time 30 min, range 1–240, step 1, extend 15. To change a timer, open
**Settings → Devices & services → Switch Timer → Configure**, pick the timer and edit its minimum, maximum and step,
default run time and extend step.

To remove a timer: **Settings → Devices & services → Switch Timer → ⋮** next to the timer → **Delete**.
A timer is also removed automatically when its switch is deleted from
Home Assistant, and follows the switch if its entity ID is renamed.

### How it behaves

| Situation | Result |
|---|---|
| Run started from the card or `switch_timer.start` | Turns on and starts a timed run. |
| Turned on anywhere else | Stays on with no timer (`manual`), even if a run was left over from before. |
| Turned off anywhere during a timed run | The run is cancelled. This includes coming back off after being unavailable; coming back on keeps the run. |
| End time reached | Turns off. If the entity is unavailable then, it's turned off when it comes back. |
| Home Assistant restarts during a timed run | The run is restored. If its end time passed meanwhile, the entity is turned off once it's available. If the entity is found off, the run is dropped. |
| Home Assistant restarts while on without a timer | Nothing happens. |

## Card

The integration loads the card itself; there's no Lovelace resource to add. It is available once the
integration is added and the page reloaded (Installation steps 3–4). On a dashboard, choose **Edit → Add card → By card → Switch Timer**, or use YAML:

```yaml
type: custom:switch-timer-card
entity: switch.my_pump
```

A new card starts without an entity and shows a demo (a switch running a timer) until you pick one, in the
card picker and in the editor. The demo is only a picture: it doesn't control or create anything.

Picking the entity is the only setup:

- **In the card editor**, the Entity picker lists every switch, light, fan and toggle; the text under it names
  the ones that already have a timer. When an admin picks one without a timer, it is created right away.
- **On the dashboard**, a card for an entity without a timer creates it when an admin opens the dashboard.
- Users who aren't admins see "Ask an admin to pick this switch once."

A picked entity keeps its timer even if you then cancel the editor; delete it as described in
[Configuration](#configuration) if you don't want it.

| Option | Description |
|---|---|
| `entity` | **Required.** The controlled entity. |
| `name` | Card title (default: the entity's name). |
| `icon` | Header icon (default: `mdi:power`). |
| `presets` | Preset buttons in minutes (default: `[15, 30, 60, 120]`). |
| `extend_minutes` | Minutes added by the extend button (default: `15`). |
| `show_hints` | Show the hint line (default: `true`). |

Using the card:

- **Tap the header** to start a run with the current run time, or to turn the device off while it's on.
  **Hold the header** to open the entity's details.
- **Run time**: `−` / `+` change it (hold to repeat). Tap the value to type one.
- **Presets** set the run time and start a run of that length.
- **During a run**: a live countdown and progress bar, **+N min** (extend, `extend_minutes`) and **Stop now**.
- **Turned on elsewhere** (no timer): **Start N min timer** and **Turn off**.

The card follows Home Assistant's dark mode. Every color can be changed in a theme with a
`switch-timer-<name>` variable, for example:

```yaml
my-theme:
  switch-timer-accent: "#0B84F3"        # progress bar, on border and icon
  switch-timer-on-bg: "#E3F0FD"         # header background while on
```

Variables: `frame-bg`, `frame-border`, `text`, `text-secondary`, `header-bg`, `icon-bg`, `icon-color`,
`pill-bg`, `pill-text`, `on-bg`, `on-border`, `on-icon-bg`, `on-icon-color`, `on-label`, `on-pill-bg`,
`on-pill-text`, `control-bg`, `control-border`, `strong-bg`, `strong-text`, `box-bg`, `accent`,
`accent-text`, `accent-soft`.

## Actions

Target either the controlled entity or one of its timer's entities.

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

## Test environment

A ready-to-use Home Assistant with Switch Timer, without the dev container. It needs only Docker.

```powershell
scripts	est-env.ps1 up        # Windows PowerShell
```
```bash
scripts/test-env up            # Linux, macOS, Git Bash
```

`up` builds the card, starts the official `ghcr.io/home-assistant/home-assistant` image (same version as
`requirements.txt`) as the container `ha-switch-timer-test`, waits until it answers and prints
`Ready: http://localhost:8123`. On first start it is set up for you:

- onboarding done, user **test** / **test-pass-123**; from this machine you are logged in automatically;
- test devices `switch.test_pump` and `fan.test_fan` (backed by toggle helpers);
- the Switch Timer integration added, and a dashboard **Switch Timer test** with a card for each device.
  Opening it creates both timers, as the card does for any admin.

| Command (bash / PowerShell) | What it does |
|---|---|
| `up` | Build and start (keeps existing data). Rebuild after code changes with `up` again. |
| `reset` | Delete the test volume and start fresh: a true first start. |
| `down` | Stop. The data volume is kept. |
| `logs` | Follow Home Assistant's log. |
| `verify` | `reset`, then Playwright checks in Firefox for both modes; writes `verify-report/report.md` with screenshots. |

**First-install mode** (`up --first-install` / `up -FirstInstall`, same for `reset` and `verify`) only does the
onboarding, so you can test **Add integration → Switch Timer → Submit**, the page reload and the card picker yourself.

If port 8123 is taken (for example by the dev container's Home Assistant), `up` says so and stops. Stop the other
Home Assistant first.

> [!WARNING]
> Test environment only. It logs in **without a password** from this machine (`trusted_networks` with
> `allow_bypass_login`, see `test-env/config/configuration.yaml`). The port is published on **127.0.0.1 only**,
> so other devices on your network can't reach it. Home Assistant runs as root inside its container, as the
> official image requires; nothing from your disk is mounted, all data is in the Docker volume
> `ha-switch-timer-test-config`. Your dev `config/` is never touched.

## Development

1. Open the repo in VS Code and choose **Reopen in Container**. This needs Docker and the Dev Containers extension.
2. Run the task **Run Home Assistant on port 8123** (or `scripts/develop`).
3. Open <http://localhost:8123> and finish onboarding. `custom_components/switch_timer` is loaded from the
   working tree, and test devices `switch.test_pump` and `fan.test_fan` are available.

Restart Home Assistant (stop the task and start it again) after you change Python code. `scripts/lint` formats and lints the code with ruff.
`scripts/test` runs the tests with coverage.

Never run `hass` or the tests as root or with `sudo`: root-owned files in `config/` make Home Assistant fail with a
`PermissionError`. Both scripts refuse to run as root. `scripts/develop` takes back ownership of `config/` (using
`sudo chown`) if it finds files there that you don't own.

### Card development

The card's source is in [`frontend/`](frontend) (TypeScript + Lit). `scripts/setup` installs it and builds it once.

1. Run the task **Watch card** (`npm run watch --prefix frontend`). It rebuilds
   `custom_components/switch_timer/frontend/switch-timer-card.js` on every save.
2. Run **Run Home Assistant on port 8123** in a second terminal. HA loads the card when it starts, if the JS
   file exists and the Switch Timer integration is added (Add integration → Switch Timer → Submit).
3. Add the card to a dashboard of your own (**Settings → Dashboards → Add dashboard**); the default Overview is
   generated automatically. Pick **Add card → By card → Switch Timer**, or paste
   `type: custom:switch-timer-card` / `entity: switch.test_pump` in the code editor.
4. After a rebuild, reload the dashboard with the browser cache disabled (DevTools open → Network → **Disable cache**).
   The card's URL carries a hash of the file taken when HA starts, so without that you'd need to restart HA.

`npm run typecheck --prefix frontend` type-checks the code, `npm test --prefix frontend` builds the card and
checks how it renders each state (and that it survives HA replacing its element registry), and
`npm run build --prefix frontend` makes the minified build.

## License

[MIT](LICENSE)
