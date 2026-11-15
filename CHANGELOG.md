# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Repository scaffold: integration stub, dev container with a Home Assistant dev instance,
  CI validation (hassfest, HACS, ruff), README skeleton and the prototype blueprints.
- Integration: config flow and options flow, one entry per controlled entity
  (switch, light, fan, input_boolean).
- Timed runs that survive restarts, with `number.<name>_run_time` and `sensor.<name>_ends_at`.
- Actions `switch_timer.start`, `switch_timer.extend` and `switch_timer.stop`.
- Diagnostics.
- Test suite covering every row of the behavior table, run in CI.
- Lovelace card `custom:switch-timer-card`, loaded by the integration (no resource to add):
  off / timed / manual states, live countdown, segmented progress bar, presets, visual editor,
  dark-mode colors and `switch-timer-*` theme variables.
- `controlled_entity_id` attribute on the ends-at sensor.
- Card render tests (happy-dom) in CI.
- Quick setup from the card: the editor's Entity picker lists all switches, lights, fans and toggles and
  names those with a Switch Timer; a **Create Switch Timer** button (editor, and the card's
  "No Switch Timer" state, admins only) runs the config flow with the defaults. Non-admins are asked
  to contact an admin.

### Fixed

- Turning the entity on from anywhere other than the card or `switch_timer.start` could continue a
  leftover timed run (after the entity came back from `unavailable` as off), showing a countdown and
  turning the entity off at the old end time. It is now always `manual` with no timer, and coming
  back off cancels the run (coming back on still keeps it).
- The card shows the countdown only when the sensor's `mode` is `timed`.
- "Custom element not found: switch-timer-card" in HA 2026.10: the frontend replaces its element
  registry after integration-loaded cards have run; the card now defines itself again on the new
  registry. Failed entity lookups show an error on the card instead of breaking it.
- Dev config: `energy` is loaded, so the card picker no longer logs `unknown_command`
  (`energy/get_prefs`).
