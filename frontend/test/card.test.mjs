// Renders the built card (custom_components/switch_timer/frontend/switch-timer-card.js) in happy-dom.
// Run with `npm test` (builds first).
import { GlobalRegistrator } from "@happy-dom/global-registrator";
import assert from "node:assert/strict";
import { after, test } from "node:test";

GlobalRegistrator.register({ url: "http://localhost:8123/" });
await import("../../custom_components/switch_timer/frontend/switch-timer-card.js");
after(() => GlobalRegistrator.unregister());

const PUMP = "switch.test_pump";
const SENSOR = "sensor.test_pump_ends_at";
const NUMBER = "number.test_pump_run_time";

/** A minimal hass object; `calls` records every service call the card makes. */
function makeHass({ pump, mode = "off", endsAt = "unknown", duration = null, runTime = "30" }) {
  const calls = [];
  return {
    calls,
    states: {
      [PUMP]: { entity_id: PUMP, state: pump, attributes: { friendly_name: "Test pump" } },
      [SENSOR]: {
        entity_id: SENSOR,
        state: endsAt,
        attributes: { controlled_entity_id: PUMP, mode, duration },
      },
      [NUMBER]: { entity_id: NUMBER, state: runTime, attributes: { min: 1, max: 240, step: 1 } },
    },
    entities: {
      [SENSOR]: { entity_id: SENSOR, device_id: "d1", platform: "switch_timer", translation_key: "ends_at" },
      [NUMBER]: { entity_id: NUMBER, device_id: "d1", platform: "switch_timer", translation_key: "run_time" },
    },
    locale: { language: "en", time_format: "24" },
    themes: { darkMode: false },
    callService: async (...args) => calls.push(args),
  };
}

/** A fresh card per test, so one test's state can't leak into the next. */
function mount() {
  const card = document.createElement("switch-timer-card");
  card.setConfig({ type: "custom:switch-timer-card", entity: PUMP });
  document.body.append(card);
  after(() => card.remove());
  return card;
}

async function render(hass, card = mount()) {
  card.hass = hass;
  await card.updateComplete;
  const root = card.shadowRoot;
  const text = (sel) => root.querySelector(sel)?.textContent.trim().replace(/\s+/g, " ");
  return {
    root,
    label: text(".label"),
    pill: text(".pill"),
    buttons: [...root.querySelectorAll(".buttons .btn")].map((b) => b.textContent.trim()),
    countdown: root.querySelector(".countdown"),
    bar: root.querySelector(".bar"),
  };
}

test("on with no timed run renders the manual state", async () => {
  const view = await render(makeHass({ pump: "on", mode: "manual" }));

  assert.equal(view.label, "On · no timer");
  assert.equal(view.pill, "ON");
  assert.deepEqual(view.buttons, ["Start 30 min timer", "Turn off"]);
  assert.equal(view.countdown, null);
  assert.equal(view.bar, null);
});

test("turned on elsewhere: manual state, and the card calls no service", async () => {
  const card = mount();
  const off = makeHass({ pump: "off" });
  await render(off, card);
  // The pump is switched on by another button; HA pushes the new states to the same card.
  const on = makeHass({ pump: "on", mode: "manual" });
  const view = await render(on, card);
  await new Promise((r) => setTimeout(r, 1100)); // past one countdown tick

  assert.equal(view.label, "On · no timer");
  assert.equal(view.countdown, null);
  assert.deepEqual([...off.calls, ...on.calls], []);
});

test("an end time with mode manual still renders manual, not a countdown", async () => {
  const endsAt = new Date(Date.now() + 10 * 60_000).toISOString();
  const view = await render(makeHass({ pump: "on", mode: "manual", endsAt, duration: 600 }));

  assert.equal(view.label, "On · no timer");
  assert.equal(view.countdown, null);
});

test("a timed run renders the countdown and progress bar", async () => {
  const endsAt = new Date(Date.now() + 7.5 * 60_000).toISOString();
  const view = await render(makeHass({ pump: "on", mode: "timed", endsAt, duration: 900 }));

  assert.match(view.label, /^On · turns off at \d\d:\d\d$/);
  assert.match(view.countdown.textContent.trim(), /^7:(30|29)$/);
  assert.ok(view.bar);
  assert.deepEqual(view.buttons, ["+15 min", "Stop now"]);
});

test("off renders the run time and presets", async () => {
  const view = await render(makeHass({ pump: "off" }));

  assert.equal(view.label, "Off · tap to run for 30 min");
  assert.equal(view.pill, "OFF");
  const presets = [...view.root.querySelectorAll(".preset")].map((b) => b.textContent.trim());
  assert.deepEqual(presets, ["15 min", "30 min", "1 h", "2 h"]);
  assert.equal(view.root.querySelector(".preset.selected").textContent.trim(), "30 min");
});
