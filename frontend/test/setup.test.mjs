// One-click Switch Timer creation from the card and the editor (built card, happy-dom).
import { GlobalRegistrator } from "@happy-dom/global-registrator";
import assert from "node:assert/strict";
import { after, test } from "node:test";

GlobalRegistrator.register({ url: "http://localhost:8123/" });
await import("../../custom_components/switch_timer/frontend/switch-timer-card.js");
after(() => GlobalRegistrator.unregister());

const PUMP = "switch.garden_pump";
const SENSOR = "sensor.garden_pump_ends_at";
const NUMBER = "number.garden_pump_run_time";
const FLOW = "config/config_entries/flow";

/** hass for a pump with or without a Switch Timer; `api` answers callApi by path. */
function makeHass({ admin = true, timer = false, api = {} } = {}) {
  const calls = [];
  const states = {
    [PUMP]: { entity_id: PUMP, state: "off", attributes: { friendly_name: "Garden pump" } },
    "switch.other": { entity_id: "switch.other", state: "off", attributes: { friendly_name: "Other" } },
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
    callApi: async (method, path, data) => {
      calls.push([method, path, data]);
      const answer = api[`${method} ${path}`];
      if (answer instanceof Error) throw answer;
      return answer;
    },
  };
}

const tick = () => new Promise((r) => setTimeout(r, 0));

function mountCard(hass) {
  const card = document.createElement("switch-timer-card");
  card.setConfig({ type: "custom:switch-timer-card", entity: PUMP });
  card.hass = hass;
  document.body.append(card);
  after(() => card.remove());
  return card;
}

async function setupPrompt(host) {
  await host.updateComplete;
  const prompt = host.shadowRoot.querySelector("switch-timer-setup");
  assert.ok(prompt, "setup prompt rendered");
  await prompt.updateComplete;
  return prompt;
}

async function clickCreate(prompt) {
  const button = prompt.shadowRoot.querySelector("button");
  assert.equal(button.textContent.trim(), "Create Switch Timer");
  button.click();
  for (let i = 0; i < 5; i++) await tick();
  await prompt.updateComplete;
  return prompt.shadowRoot.querySelector(".error")?.textContent.trim();
}

const OK_API = {
  [`POST ${FLOW}`]: { type: "form", flow_id: "f1", step_id: "user" },
  [`POST ${FLOW}/f1`]: { type: "create_entry", title: "Garden pump" },
};

test("card without a Switch Timer: admins create one through the config flow", async () => {
  const hass = makeHass({ api: OK_API });
  const card = mountCard(hass);
  const prompt = await setupPrompt(card);
  assert.match(card.shadowRoot.querySelector(".warning").textContent, /No Switch Timer is set up for Garden pump/);

  let created;
  card.addEventListener("switch-timer-created", (e) => (created = e.detail));
  const error = await clickCreate(prompt);

  assert.equal(error, undefined);
  assert.deepEqual(hass.calls, [
    ["POST", FLOW, { handler: "switch_timer", show_advanced_options: false }],
    ["POST", `${FLOW}/f1`, { entity_id: PUMP, default_run_time: 30 }],
  ]);
  assert.deepEqual(created, { entityId: PUMP, title: "Garden pump" });

  // HA pushes the new entities: the card switches to its normal view.
  card.hass = makeHass({ timer: true });
  await card.updateComplete;
  assert.equal(card.shadowRoot.querySelector("switch-timer-setup"), null);
  assert.equal(card.shadowRoot.querySelector(".label").textContent.trim(), "Off · tap to run for 30 min");
});

test("already configured: clear message, nothing else sent", async () => {
  const hass = makeHass({
    api: { ...OK_API, [`POST ${FLOW}/f1`]: { type: "abort", reason: "already_configured" } },
  });
  const error = await clickCreate(await setupPrompt(mountCard(hass)));

  assert.equal(error, "This entity already has a Switch Timer.");
  assert.equal(hass.calls.length, 2);
});

test("other abort reasons are shown", async () => {
  const hass = makeHass({ api: { [`POST ${FLOW}`]: { type: "abort", reason: "single_instance_allowed" } } });
  const error = await clickCreate(await setupPrompt(mountCard(hass)));

  assert.equal(error, "Setup was aborted (single_instance_allowed).");
});

test("a flow that stops at a form is reported and deleted", async () => {
  const hass = makeHass({
    api: { ...OK_API, [`POST ${FLOW}/f1`]: { type: "form", flow_id: "f1", errors: { base: "unknown" } } },
  });
  const error = await clickCreate(await setupPrompt(mountCard(hass)));

  assert.equal(error, "Setup did not finish (unknown).");
  assert.deepEqual(hass.calls.at(-1), ["DELETE", `${FLOW}/f1`, undefined]);
});

test("a failed request is reported", async () => {
  const failure = Object.assign(new Error("401: Unauthorized"), { body: { message: "Unauthorized" } });
  const hass = makeHass({ api: { [`POST ${FLOW}`]: failure } });
  const error = await clickCreate(await setupPrompt(mountCard(hass)));

  assert.equal(error, "Could not create the Switch Timer: Unauthorized");
});

test("non-admins are asked to contact an admin, no button", async () => {
  const prompt = await setupPrompt(mountCard(makeHass({ admin: false })));

  assert.equal(prompt.shadowRoot.querySelector("button"), null);
  assert.equal(
    prompt.shadowRoot.querySelector("p").textContent.trim(),
    "Ask an admin to set up Switch Timer for this entity.",
  );
});

test("editor: create button for an entity without a Switch Timer, preview refreshed", async () => {
  const editor = document.createElement("switch-timer-card-editor");
  editor.hass = makeHass({ api: OK_API });
  editor.setConfig({ type: "custom:switch-timer-card", entity: PUMP });
  document.body.append(editor);
  after(() => editor.remove());

  const prompt = await setupPrompt(editor);
  assert.match(editor.shadowRoot.querySelector(".status").textContent, /Garden pump has no Switch Timer yet/);
  const changes = [];
  editor.addEventListener("config-changed", (e) => changes.push(e.detail.config));
  await clickCreate(prompt);

  assert.deepEqual(changes, [{ type: "custom:switch-timer-card", entity: PUMP }]);
  editor.hass = makeHass({ timer: true });
  await editor.updateComplete;
  assert.match(editor.shadowRoot.querySelector(".status").textContent, /✓ Garden pump has a Switch Timer/);
});

test("editor: entity picker allows all supported domains and names those with a timer", async () => {
  const editor = document.createElement("switch-timer-card-editor");
  editor.hass = makeHass({ timer: true });
  editor.setConfig({ type: "custom:switch-timer-card", entity: PUMP });
  document.body.append(editor);
  after(() => editor.remove());
  await editor.updateComplete;

  const form = editor.shadowRoot.querySelector("ha-form");
  const entityField = form.schema.find((field) => field.name === "entity");
  assert.deepEqual(entityField.selector.entity.filter, [{ domain: ["switch", "light", "fan", "input_boolean"] }]);
  assert.equal(
    form.computeHelper(entityField),
    "A switch, light, fan or toggle. With a Switch Timer: Garden pump.",
  );
});
