// Automatic timer creation from the card and the editor (built card, happy-dom).
import { GlobalRegistrator } from "@happy-dom/global-registrator";
import assert from "node:assert/strict";
import { after, test } from "node:test";

GlobalRegistrator.register({ url: "http://localhost:8123/" });
await import("../../custom_components/switch_timer/frontend/switch-timer-card.js");
after(() => GlobalRegistrator.unregister());

const PUMP = "switch.garden_pump";
const SENSOR = "sensor.garden_pump_ends_at";
const NUMBER = "number.garden_pump_run_time";
const ENSURE = { type: "switch_timer/ensure_timer", entity_id: PUMP };

/** hass for a pump with or without a timer; `ws` answers callWS (value, Error-like or function). */
function makeHass({ admin = true, timer = false, ws } = {}) {
  const calls = [];
  const states = {
    [PUMP]: { entity_id: PUMP, state: "off", attributes: { friendly_name: "Garden pump" } },
  };
  const entities = {};
  if (timer) {
    states[SENSOR] = { entity_id: SENSOR, state: "unknown", attributes: { controlled_entity_id: PUMP, mode: "off" } };
    states[NUMBER] = { entity_id: NUMBER, state: "30", attributes: { min: 1, max: 240, step: 1 } };
    entities[SENSOR] = { entity_id: SENSOR, device_id: "d1", platform: "switch_timer", translation_key: "ends_at" };
    entities[NUMBER] = { entity_id: NUMBER, device_id: "d1", platform: "switch_timer", translation_key: "run_time" };
  }
  return {
    calls,
    states,
    entities,
    user: { is_admin: admin },
    locale: { language: "en", time_format: "24" },
    themes: { darkMode: false },
    callService: async (...args) => calls.push(["service", ...args]),
    callWS: async (message) => {
      calls.push(message);
      const answer = typeof ws === "function" ? await ws(message) : ws;
      if (answer?.code) throw answer;
      return answer ?? { created: true, subentry_id: "s1" };
    },
  };
}

const settle = async () => {
  for (let i = 0; i < 5; i++) await new Promise((r) => setTimeout(r, 0));
};

function mount(tag, hass, entity = PUMP) {
  const el = document.createElement(tag);
  el.setConfig({ type: "custom:switch-timer-card", entity });
  el.hass = hass;
  document.body.append(el);
  after(() => el.remove());
  return el;
}

const text = (el, sel) => el.shadowRoot.querySelector(sel)?.textContent.trim().replace(/\s+/g, " ");

test("admin card without a timer creates one automatically, once", async () => {
  const hass = makeHass();
  const card = mount("switch-timer-card", hass);
  await card.updateComplete;
  assert.equal(text(card, ".warning"), "Setting up Switch Timer for Garden pump…");

  await settle();
  card.hass = { ...hass, states: { ...hass.states } }; // an unrelated hass update
  await card.updateComplete;
  await settle();
  assert.deepEqual(hass.calls, [ENSURE]);

  // HA reports the new entities: normal view.
  card.hass = makeHass({ timer: true });
  await card.updateComplete;
  assert.equal(text(card, ".label"), "Off · tap to run for 30 min");
});

test("an entity that already has a timer creates nothing", async () => {
  const hass = makeHass({ timer: true });
  const card = mount("switch-timer-card", hass);
  await card.updateComplete;
  await settle();

  assert.deepEqual(hass.calls, []);
});

test("editor and preview asking at the same time send one request", async () => {
  let release;
  const pending = new Promise((r) => (release = r));
  const hass = makeHass({ ws: () => pending });
  const editor = mount("switch-timer-card-editor", hass);
  const preview = mount("switch-timer-card", hass);
  await editor.updateComplete;
  await preview.updateComplete;
  release({ created: true, subentry_id: "s1" });
  await settle();

  assert.deepEqual(hass.calls, [ENSURE]);
});

for (const [code, expected] of [
  ["unknown_command", /can't create timers from the card\. Update it/],
  ["not_supported", /^Switch Timer works with switches, lights, fans and toggles\.$/],
  ["not_found", /^Entity not found: switch\.garden_pump$/],
  ["not_loaded", /isn't loaded/],
  ["unauthorized", /^Only an admin can set up a Switch Timer/],
  ["home_assistant_error", /^Could not set up the Switch Timer: boom$/],
]) {
  test(`error ${code} is shown on the card`, async () => {
    const card = mount("switch-timer-card", makeHass({ ws: { code, message: "boom" } }));
    await card.updateComplete;
    await settle();
    await card.updateComplete;

    assert.match(text(card, ".warning"), expected);
  });
}

test("non-admins are asked to contact an admin; nothing is created", async () => {
  const hass = makeHass({ admin: false });
  const card = mount("switch-timer-card", hass);
  await card.updateComplete;
  await settle();

  assert.equal(
    text(card, ".warning"),
    "Garden pump has no Switch Timer yet. Ask an admin to pick this switch once.",
  );
  assert.deepEqual(hass.calls, []);
});

test("editor: picking an entity creates its timer and refreshes the preview", async () => {
  const hass = makeHass();
  const editor = mount("switch-timer-card-editor", hass);
  const changes = [];
  editor.addEventListener("config-changed", (e) => changes.push(e.detail.config));
  await editor.updateComplete;
  assert.equal(text(editor, ".status"), "Setting up Switch Timer for Garden pump…");

  await settle();
  assert.deepEqual(hass.calls, [ENSURE]);
  assert.deepEqual(changes, [{ type: "custom:switch-timer-card", entity: PUMP }]);

  editor.hass = makeHass({ timer: true });
  await editor.updateComplete;
  assert.equal(text(editor, ".status"), "✓ Garden pump has a Switch Timer.");
});

test("editor: non-admin sees the ask-an-admin status", async () => {
  const hass = makeHass({ admin: false });
  const editor = mount("switch-timer-card-editor", hass);
  await editor.updateComplete;
  await settle();

  assert.equal(
    text(editor, ".status"),
    "Garden pump has no Switch Timer yet. Ask an admin to pick this switch once.",
  );
  assert.deepEqual(hass.calls, []);
});
