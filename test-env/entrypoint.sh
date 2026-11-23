#!/bin/sh
# Prepare /config (the test volume), then start Home Assistant as the official image does.
set -e

SRC=/opt/switch-timer-test

mkdir -p /config/custom_components

# First start only: the test configuration. Later edits in the volume are kept.
if [ ! -f /config/configuration.yaml ]; then
    cp "$SRC/configuration.yaml" /config/configuration.yaml
fi

# Every start: the integration (and card) from this image, so `up` after a code change
# tests the new code while keeping onboarding, timers and dashboards.
rm -rf /config/custom_components/switch_timer
cp -r "$SRC/switch_timer" /config/custom_components/switch_timer

exec /init "$@"
