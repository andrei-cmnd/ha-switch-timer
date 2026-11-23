# Test environment: the official Home Assistant image with Switch Timer and its card built in.
# Build context: the repo root (see docker-compose.yml). HA_VERSION comes from requirements.txt
# (scripts/test-env reads it), so the test env runs the same HA version as the tests.

ARG HA_VERSION=2026.10.2

# --- Stage 1: build the card, the same way CI does ---------------------------------------
FROM node:24-bookworm AS card
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --no-audit --no-fund
COPY frontend/ ./
COPY custom_components/ /src/custom_components/
RUN npm run build

# --- Stage 2: Home Assistant ---------------------------------------------------------------
FROM ghcr.io/home-assistant/home-assistant:${HA_VERSION}
COPY --from=card /src/custom_components/switch_timer /opt/switch-timer-test/switch_timer
COPY test-env/config/configuration.yaml /opt/switch-timer-test/configuration.yaml
COPY test-env/provision.py /opt/switch-timer-test/provision.py
COPY --chmod=755 test-env/entrypoint.sh /opt/switch-timer-test/entrypoint.sh

# Runs as root, as the official image requires (s6 /init). Test env only: nothing from the
# host is mounted; all state lives in the ha-switch-timer-test-config volume.
ENTRYPOINT ["/opt/switch-timer-test/entrypoint.sh"]
