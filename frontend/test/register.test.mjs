// HA's frontend swaps window.customElements after integration modules have run.
// The card must end up defined on the new registry too (real-browser bug, Firefox + HA 2026.10).
import { GlobalRegistrator } from "@happy-dom/global-registrator";
import assert from "node:assert/strict";
import { after, test } from "node:test";

GlobalRegistrator.register({ url: "http://localhost:8123/" });
after(() => GlobalRegistrator.unregister());

test("elements are defined again when the page replaces its registry", async () => {
  await import("../../custom_components/switch_timer/frontend/switch-timer-card.js");
  assert.ok(customElements.get("switch-timer-card"), "defined synchronously at load");

  // What HA's frontend does: install its own, empty registry object.
  const defs = new Map();
  const replacement = {
    get: (name) => defs.get(name),
    define(name, ctor) {
      if (defs.has(name)) throw new Error(`${name} already defined`);
      defs.set(name, ctor);
    },
  };
  const original = window.customElements;
  Object.defineProperty(window, "customElements", { value: replacement, configurable: true });
  after(() => Object.defineProperty(window, "customElements", { value: original, configurable: true }));
  assert.equal(customElements.get("switch-timer-card"), undefined);

  await new Promise((r) => setTimeout(r, 300));

  assert.ok(replacement.get("switch-timer-card"), "card defined on the new registry");
  assert.ok(replacement.get("switch-timer-card-editor"), "editor defined on the new registry");
  const Card = replacement.get("switch-timer-card");
  assert.equal(typeof Card.prototype.setConfig, "function", "the card class (a fresh subclass)");
  assert.notEqual(Card, original.get("switch-timer-card"));
});
