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
