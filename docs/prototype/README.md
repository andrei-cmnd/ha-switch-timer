# Prototype (reference)

The original helper-based setup that Switch Timer replaces. Its behavior is the specification
for the integration, and `lg4_card.yaml` is the visual reference for the card.

- `lg4_card.yaml`: the custom:button-card dashboard card for `switch.pm4_lg` (needs button-card).
- `timed_switch_control.yaml`: script blueprint called by the card (start / tap / extend / stop).
- `timed_switch_auto_off.yaml`: automation blueprint that ends runs and handles restarts.

Installable copies of the blueprints live in [`blueprints/`](../../blueprints).
