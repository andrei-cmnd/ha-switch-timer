// The demo shown without an entity (card picker preview, new card in the editor).
// Built card in happy-dom.
import { GlobalRegistrator } from "@happy-dom/global-registrator";
import assert from "node:assert/strict";
import { after, test } from "node:test";

GlobalRegistrator.register({ url: "http://localhost:8123/" });
await import("../../custom_components/switch_timer/frontend/switch-timer-card.js");
after(() => GlobalRegistrator.unregister());

const PUMP = "switch.garden_pump";

/** An admin hass with an existing timer; every call is recorded. */
function makeHass() {
  const calls = [];
  const SENSOR = "sensor.garden_pump_ends_at";
  return {
    calls,
    states: {
      [PUMP]: { entity_id: PUMP, state: "on", attributes: { friendly_name: "Garden pump" } },
      [SENSOR]: { entity_id: SENSOR, state: "unknown", attributes: { controlled_entity_id: PUMP, mode: "manual" } },
    },
    entities: {
      [SENSOR]: { entity_id: SENSOR, device_id: "d1", platform: "switch_timer", translation_key: "ends_at" },
    },
    user: { is_admin: true },
    locale: { language: "en", time_format: "24" },
    themes: { darkMode: false },
    callService: async (...args) => calls.push(["service", ...args]),
    callWS: async (msg) => calls.push(["ws", msg]),
    callApi: async (...args) => calls.push(["api", ...args]),
  };
}

const Card = () => customElements.get("switch-timer-card");

function mountDemo({ hass } = {}) {
  const card = document.createElement("switch-timer-card");
  card.setConfig({ type: "custom:switch-timer-card", ...Card().getStubConfig(hass) });
  if (hass) card.hass = hass;
  document.body.append(card);
  after(() => card.remove());
  return card;
}

const text = (card, sel) => card.shadowRoot.querySelector(sel)?.textContent.trim().replace(/\s+/g, " ");

test("getStubConfig never picks an entity, even when timers exist", () => {
  assert.deepEqual(Card().getStubConfig(makeHass()), {});
  assert.deepEqual(Card().getStubConfig(), {});
});

test("the demo renders immediately, before hass arrives", async () => {
  const card = mountDemo(); // no hass at all
  await card.updateComplete;

  assert.equal(text(card, ".name"), "Your selected switch");
  // Without hass the time uses the browser locale (12 or 24 h).
  assert.match(text(card, ".label"), /^On · turns off at \d{1,2}:\d\d( [AP]M)?$/);
  assert.equal(text(card, ".pill"), "ON");
  assert.ok(card.shadowRoot.querySelector(".header.on"));
  assert.equal(text(card, ".countdown"), "18:24");
  assert.ok(card.shadowRoot.querySelector(".bar .bar-remaining"));
  const buttons = [...card.shadowRoot.querySelectorAll(".buttons .btn")].map((b) => b.textContent.trim());
  assert.deepEqual(buttons, ["+15 min", "Stop now"]);
  assert.equal(card.shadowRoot.querySelector(".run-time"), null);
  assert.equal(card.shadowRoot.querySelector(".warning"), null);
});

test("the demo countdown ticks", async () => {
  const card = mountDemo();
  await card.updateComplete;
  await new Promise((r) => setTimeout(r, 1200));
  await card.updateComplete;

  assert.equal(text(card, ".countdown"), "18:23");
});

test("the demo makes no calls and never creates a timer, even when clicked", async () => {
  const hass = makeHass();
  const card = mountDemo({ hass });
  const events = [];
  card.addEventListener("hass-more-info", () => events.push("more-info"));
  await card.updateComplete;

  const header = card.shadowRoot.querySelector(".header");
  header.dispatchEvent(new PointerEvent("pointerdown", { button: 0, bubbles: true }));
  header.dispatchEvent(new PointerEvent("pointerup", { button: 0, bubbles: true }));
  header.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  for (const button of card.shadowRoot.querySelectorAll("button")) button.click();
  card.hass = { ...hass }; // hass updates arrive
  await card.updateComplete;
  await new Promise((r) => setTimeout(r, 50));

  assert.deepEqual(hass.calls, []);
  assert.deepEqual(events, []);
  assert.equal(text(card, ".name"), "Your selected switch"); // no real entity shown
});

test("editor for a new card: pick prompt, nothing created", async () => {
  const hass = makeHass();
  const editor = document.createElement("switch-timer-card-editor");
  editor.hass = hass;
  editor.setConfig({ type: "custom:switch-timer-card", ...Card().getStubConfig(hass) });
  document.body.append(editor);
  after(() => editor.remove());
  await editor.updateComplete;
  await new Promise((r) => setTimeout(r, 50));

  assert.equal(text(editor, ".status"), "Pick a switch, light, fan or toggle.");
  assert.deepEqual(hass.calls, []);
});

test("a second new card starts empty with the demo, not the first card's entity", async () => {
  const hass = makeHass(); // the first card's entity already has a timer
  const first = document.createElement("switch-timer-card");
  first.setConfig({ type: "custom:switch-timer-card", entity: PUMP });
  first.hass = hass;
  document.body.append(first);
  after(() => first.remove());

  const second = mountDemo({ hass });
  await second.updateComplete;

  assert.equal(second._config.entity, undefined);
  assert.equal(text(second, ".name"), "Your selected switch");
});
