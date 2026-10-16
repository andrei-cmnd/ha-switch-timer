# Switch Timer — Home Assistant integration + Lovelace card

Turn a switch on **from a dashboard card** for a configurable time; it turns off automatically.
Turning the switch on from anywhere else must NOT start a timer.

This repo replaces a working prototype built from helpers + 2 blueprints + a custom:button-card
(see `prototype/` if present). The prototype's behavior is the specification below.

## Target
- Home Assistant 2026.10+ (`custom_components/switch_timer`), installable via HACS (custom repository).
- One config entry per controlled entity, created in the UI.
- A bundled Lovelace card `custom:switch-timer-card` that the integration registers itself
  (no manual Lovelace resource). Card config minimum: `entity: switch.xxx`.
- No runtime dependency on button-card, circular-timer-card or card-mod.

## Behavior spec (validated in the prototype — implement exactly)
| Situation | Result |
|---|---|
| Run started via card / `switch_timer.start` | turn entity on + start a **timed run** (minutes = argument, else run-time number) |
| Entity turned on anywhere else | stays on, **no timer** (mode = `manual`) |
| Entity turned off anywhere during a timed run | cancel the run, clear state |
| `switch_timer.extend` (minutes, default 15) | only if a timed run is active: end time += minutes |
| `switch_timer.stop` | turn entity off, clear run |
| Timed run reaches end time | turn entity off, clear run |
| HA restart during a timed run | restore saved end time: if past → turn off (after entity becomes available); else keep counting |
| HA restart while entity on with no timed run | do nothing |

Implementation notes:
- Persist `{ends_at, duration, started_at}` per entry (`homeassistant.helpers.storage.Store` or `RestoreEntity`).
- Schedule with `async_track_point_in_utc_time`; cancel/reschedule on extend/stop.
- Listen only for the controlled entity going `on → off` (to cancel). Never start a run on `off → on`.
- Use `homeassistant.turn_on` / `turn_off` so `switch`, `light`, `fan`, `input_boolean` all work.
- Ignore transitions to/from `unavailable`/`unknown`.

## Entities per config entry
- `number.<name>_run_time` — minutes, RestoreNumber, min/max/step from options (default 1/240/1, value 30), mode box.
- `sensor.<name>_ends_at` — device_class timestamp; `None` when no timed run.
  Attributes: `mode` (`off` | `timed` | `manual`), `duration` (seconds of current run), `started_at`.

## Actions (services)
- `switch_timer.start` — target: config entry's sensor or the controlled entity; optional `minutes`.
- `switch_timer.extend` — optional `minutes` (default from options, 15).
- `switch_timer.stop`.

## Config flow
User step: pick entity (switch/light/fan/input_boolean), name (default: entity friendly name),
default run time. Options flow: min/max/step, default run time, extend minutes. Unique id = controlled entity_id.

## Card design (approved mockup)
Outer frame: white, 2px #C9CDD2 border, radius 20px, padding 16px.
- Header row (tap: off → start timed run; on → stop. hold: more-info):
  48px circle icon (mdi:power) | name 20px/600 + label 14px | pill ON/OFF.
  Off: bg #F4F5F7, icon circle #DADDE1, label "Off · tap to run for N min", pill #E4E6EA/#555B63.
  On: bg #E5F4EB, border 2px #2E9E5B, icon circle #2E9E5B (white icon), label #1E5A37, pill #1F7A45/white.
  Label on timed: "On · turns off at HH:MM"; on manual: "On · no timer".
- OFF state:
  - Run time row: "Run time" (16px/500) left, then 44px square "−", value "30 min" (20px/600, dashed box, tap opens number more-info to type), 44px square "+". ±1 per tap, hold repeats.
  - Presets grid of 4 (default 15 min / 30 min / 1 h / 2 h), 48px high, radius 10px; the one equal to the current run time is filled #1F2328 with white text.
  - Hint: "Tap the card to start · hold for details" 13px #555B63.
- ON + timed:
  - Grey box (#F4F5F7, radius 12px, padding 12px 14px): 40px circle #D3ECDD with green timer icon | "Time left" 15px/600 | live countdown m:ss right (20px/600 #1F7A45, tabular nums, ticks every second).
    Below the text: segmented progress bar, 8px high, segments 6px wide with 2px gaps (fixed px, not %), remaining #2E9E5B, elapsed #D3ECDD, shrinking smoothly.
  - Buttons: "+15 min" (white, border) and "Stop now" (#1F2328, white text), 48px, 2 columns.
  - Hint: "Tap the card to stop".
- ON + manual: buttons "Start N min timer" (white, green border/text) and "Turn off" (dark).
Card options: `entity` (required), `name`, `icon`, `presets` (list of minutes), `extend_minutes`, `show_hints`.
Visual editor required. Respect HA theme where sensible but default to the colors above.

## Repo layout
```
custom_components/switch_timer/   __init__.py manifest.json config_flow.py const.py manager.py
                                  number.py sensor.py services.py services.yaml strings.json
                                  translations/en.json icons.json diagnostics.py frontend/ (built JS)
frontend/                         src/switch-timer-card.ts editor.ts styles.ts types.ts; rollup → ../custom_components/switch_timer/frontend/
tests/                            test_config_flow.py test_manager.py test_restore.py
blueprints/                       the prototype blueprints (no-install alternative)
.devcontainer/  .github/workflows/(validate.yml tests.yml release.yml)  hacs.json  README.md  CHANGELOG.md  LICENSE
```

## Phases (stop for user validation after each)
0. Scaffold: repo files, devcontainer (HA dev instance on :8123), CI (hassfest + HACS action), README skeleton.
1. Integration + tests covering every row of the behavior table.
2. Card + editor matching the design above.
3. Release v0.1.0, HACS instructions, screenshots.
4. Migration guide for the existing LG4 prototype (switch.pm4_lg).

## Open decisions (ask the user before Phase 0 if still open)
- Names: repo `ha-switch-timer`, display "Switch Timer", domain `switch_timer` (check HACS for conflicts).
- Supported domains: switch only, or also light/fan/input_boolean.
- Defaults: presets 15/30/60/120, extend 15, run time 30, range 1–240.
- Public + MIT?  Keep blueprints in repo?

## Conventions
- Python: HA core style, type hints, async only, no blocking I/O; ruff.
- TypeScript + Lit; no external UI libs.
- Small focused commits; never commit built JS except in release workflow output.
