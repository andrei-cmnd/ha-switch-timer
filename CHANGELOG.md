# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Repository scaffold: integration stub, dev container with a Home Assistant dev instance,
  CI validation (hassfest, HACS, ruff), README skeleton and the prototype blueprints.
- Integration: a single "Switch Timer" entry, added once (no fields, just Submit). Each controlled
  entity (switch, light, fan, input_boolean) gets a timer, a config subentry with its own device,
  created automatically when an admin picks the entity in a Switch Timer card. Non-admins are asked
  to have an admin pick the switch once. **Configure** on the entry edits one timer's settings.
- Timed runs that survive restarts, with `number.<name>_run_time` and `sensor.<name>_ends_at`.
- Actions `switch_timer.start`, `switch_timer.extend` and `switch_timer.stop`.
- Diagnostics.
- Test suite covering every row of the behavior table, run in CI.
- Lovelace card `custom:switch-timer-card`, loaded by the integration (no resource to add):
  off / timed / manual states, live countdown, segmented progress bar, presets, visual editor,
  dark-mode colors and `switch-timer-*` theme variables.
- `controlled_entity_id` attribute on the ends-at sensor.
- Card render tests (happy-dom) in CI.
- Card editor: the Entity picker lists all switches, lights, fans and toggles and names those that
  already have a timer.
- Admin-only websocket command `switch_timer/ensure_timer` used by the card to create timers.
- A timer is removed automatically when its controlled entity is deleted, and follows an entity ID rename.

### Fixed

- Turning the entity on from anywhere other than the card or `switch_timer.start` could continue a
  leftover timed run (after the entity came back from `unavailable` as off), showing a countdown and
  turning the entity off at the old end time. It is now always `manual` with no timer, and coming
  back off cancels the run (coming back on still keeps it).
- The card shows the countdown only when the sensor's `mode` is `timed`.
- "Custom element not found: switch-timer-card" in HA 2026.10: the frontend replaces its element
  registry after integration-loaded cards have run; the card now defines itself again on the new
  registry. Failed entity lookups show an error on the card instead of breaking it.
- The Switch Timer entry listed under Settings → Helpers with a red "!"; it is now an integration of type
  `hub` and lists under Integrations.
- Right after setup the card wasn't available until the page was reloaded. Home Assistant only adds the card
  to pages loaded after setup, so the success message now says to reload once (no restart needed).
- Card picker preview: a static demo ("Your selected switch", running a timer) that renders immediately,
  instead of a real entity (or nothing) on first display. It makes no calls and never creates a timer.
  New cards start without an entity; the editor asks to pick one.
- Narrow cards (e.g. the ~300px picker tile): compact layout, "Run time" and the off time no longer wrap.
- Dev config: `energy` is loaded, so the card picker no longer logs `unknown_command`
  (`energy/get_prefs`).
