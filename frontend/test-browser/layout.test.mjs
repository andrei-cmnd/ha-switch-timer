// Layout of the built card in a real browser engine (Firefox via Playwright):
// narrow widths like the card picker tile must not wrap "Run time" or overflow.
// Run: npm run build && npm run test:browser  (needs `npx playwright install firefox`)
import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { firefox } from "playwright";

const CARD_JS = fileURLToPath(
  new URL("../../custom_components/switch_timer/frontend/switch-timer-card.js", import.meta.url),
);

const PAGE = `<!doctype html><html><head><meta charset="utf-8">
<style>body { margin: 0; font-family: Roboto, Arial, sans-serif; } .slot { margin: 12px; }</style>
<script>
  // Minimal stand-ins for HA's elements.
  customElements.define("ha-card", class extends HTMLElement {
    constructor() { super(); this.attachShadow({ mode: "open" }).innerHTML = "<style>:host{display:block}</style><slot></slot>"; }
  });
  customElements.define("ha-icon", class extends HTMLElement {
    connectedCallback() { this.style.cssText = "display:inline-block;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px)"; }
  });
  window.calls = [];
  window.makeHass = (pump, mode, endsInS) => {
    const ends = endsInS === undefined ? "unknown" : new Date(Date.now() + endsInS * 1000).toISOString();
    return {
      states: {
        "switch.pump": { entity_id: "switch.pump", state: pump, attributes: { friendly_name: "Garden irrigation pump" } },
        "sensor.pump_ends_at": { entity_id: "sensor.pump_ends_at", state: ends, attributes: { controlled_entity_id: "switch.pump", mode, duration: 1800 } },
        "number.pump_run_time": { entity_id: "number.pump_run_time", state: "120", attributes: { min: 1, max: 240, step: 1 } },
      },
      entities: {
        "sensor.pump_ends_at": { entity_id: "sensor.pump_ends_at", device_id: "d", platform: "switch_timer", translation_key: "ends_at" },
        "number.pump_run_time": { entity_id: "number.pump_run_time", device_id: "d", platform: "switch_timer", translation_key: "run_time" },
      },
      user: { is_admin: true },
      locale: { language: "en-US", time_format: "12" },
      themes: { darkMode: false },
      callService: async (...a) => window.calls.push(a),
      callWS: async (m) => window.calls.push(m),
    };
  };
  window.mount = async (width, entity, hassArgs) => {
    const slot = document.createElement("div");
    slot.className = "slot";
    slot.style.width = width + "px";
    const card = document.createElement("switch-timer-card");
    card.setConfig(entity ? { type: "custom:switch-timer-card", entity } : { type: "custom:switch-timer-card" });
    if (hassArgs) card.hass = window.makeHass(...hassArgs);
    slot.append(card);
    document.body.append(slot);
    await card.updateComplete;
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const root = card.shadowRoot;
    const box = root.querySelector("ha-card").getBoundingClientRect();
    const lines = (el) => {
      if (!el) return null;
      const lh = parseFloat(getComputedStyle(el).lineHeight) || parseFloat(getComputedStyle(el).fontSize) * 1.2;
      return Math.round(el.getBoundingClientRect().height / lh);
    };
    const overflow = [...root.querySelectorAll("*")]
      .filter((el) => el.getClientRects().length)
      .filter((el) => { const r = el.getBoundingClientRect(); return r.left < box.left - 0.5 || r.right > box.right + 0.5; })
      .map((el) => el.className || el.localName);
    const time = root.querySelector(".label .time");
    return {
      width: Math.round(box.width),
      overflow,
      nameLines: lines(root.querySelector(".name")),
      runTimeTitleLines: lines(root.querySelector(".run-time-title")),
      timeFragments: time ? time.getClientRects().length : null,
      iconSize: Math.round(root.querySelector(".icon-circle").getBoundingClientRect().width),
      presetsRowHeight: root.querySelector(".presets") ? Math.round(root.querySelector(".presets").getBoundingClientRect().height) : null,
      hasRunTime: Boolean(root.querySelector(".run-time")),
    };
  };
</script>
<script type="module" src="/card.js"></script></head><body></body></html>`;

let server;
let browser;
let page;

before(async () => {
  server = http
    .createServer((req, res) => {
      if (req.url === "/card.js") res.writeHead(200, { "Content-Type": "text/javascript" }).end(fs.readFileSync(CARD_JS));
      else res.writeHead(200, { "Content-Type": "text/html" }).end(PAGE);
    })
    .listen(0);
  browser = await firefox.launch();
  page = await browser.newPage({ viewport: { width: 1000, height: 1200 } });
  await page.goto(`http://localhost:${server.address().port}/`);
  await page.waitForFunction(() => customElements.get("switch-timer-card"));
});

after(async () => {
  await browser?.close();
  server?.close();
});

const mount = (width, entity, hassArgs) =>
  page.evaluate(([w, e, h]) => window.mount(w, e, h), [width, entity, hassArgs]);

for (const width of [286, 300, 360, 450]) {
  test(`demo at ${width}px: no overflow, name ≤ 2 lines, time not split`, async () => {
    const r = await mount(width, null, null);

    assert.deepEqual(r.overflow, []);
    assert.ok(r.nameLines <= 2, `name took ${r.nameLines} lines`);
    assert.equal(r.timeFragments, 1, "the off time is on one line");
    assert.equal(r.hasRunTime, false);
  });

  test(`off at ${width}px: "Run time" on one line, presets in one row, no overflow`, async () => {
    const r = await mount(width, "switch.pump", ["off", "off"]);

    assert.deepEqual(r.overflow, []);
    assert.equal(r.runTimeTitleLines, 1, `"Run time" took ${r.runTimeTitleLines} lines`);
    assert.ok(r.presetsRowHeight <= 48, `presets wrapped (${r.presetsRowHeight}px high)`);
    assert.ok(r.nameLines <= 2);
  });

  test(`timed and manual at ${width}px: no overflow`, async () => {
    const timed = await mount(width, "switch.pump", ["on", "timed", 1104]);
    const manual = await mount(width, "switch.pump", ["on", "manual"]);

    assert.deepEqual(timed.overflow, []);
    assert.equal(timed.timeFragments, 1);
    assert.deepEqual(manual.overflow, []);
  });
}

test("the narrow layout applies below 360px only", async () => {
  assert.equal((await mount(300, null, null)).iconSize, 40);
  assert.equal((await mount(450, null, null)).iconSize, 48);
});

test("the demo makes no calls in a real browser either", async () => {
  await mount(300, null, ["on", "manual"]);
  await page.waitForTimeout(1200);

  assert.deepEqual(await page.evaluate(() => window.calls), []);
});
