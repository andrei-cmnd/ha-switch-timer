// Playwright (Firefox) checks against the test environment. Run via `scripts/test-env verify`.
// Env: HA_URL (e.g. http://ha-switch-timer-test:8123), MODE (provisioned | first-install),
//      REPORT_DIR (default /report). Writes <REPORT_DIR>/<MODE>.json and screenshots.
import fs from "node:fs";
import { firefox } from "playwright";

const HA = (process.env.HA_URL ?? "http://ha-switch-timer-test:8123").replace(/\/$/, "");
const MODE = process.env.MODE ?? "provisioned";
const OUT = process.env.REPORT_DIR ?? "/report";
const results = [];
const shots = [];
const pageErrors = []; // on a settled page: these fail the check
const loadErrors = []; // while a page loads / logs in (redirects abort chunk downloads)
let settling = false;
const ensureCalls = [];

const expect = (cond, message) => {
  if (!cond) throw new Error(message);
};
async function check(id, title, fn) {
  const started = Date.now();
  try {
    const detail = (await fn()) ?? "";
    results.push({ id, title, ok: true, detail, ms: Date.now() - started });
  } catch (err) {
    results.push({ id, title, ok: false, detail: String(err?.message ?? err).split("\n")[0], ms: Date.now() - started });
  }
  console.log(`${results.at(-1).ok ? "PASS" : "FAIL"} ${id} ${title} — ${results.at(-1).detail}`);
}
async function shot(name, caption) {
  const file = `${MODE}-${name}.png`;
  await page.screenshot({ path: `${OUT}/${file}` });
  shots.push({ file, caption });
}

const browser = await firefox.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
const page = await context.newPage();
const recordError = (message) => (settling ? loadErrors : pageErrors).push(message);
page.on("pageerror", (e) => recordError(e.message));
page.on("console", (m) => {
  if (m.type() === "error") recordError(`console.error: ${m.text()}`);
});
page.on("websocket", (sock) =>
  sock.on("framesent", (f) => {
    try {
      const m = JSON.parse(f.payload);
      if (m.type === "switch_timer/ensure_timer") ensureCalls.push(m.entity_id);
    } catch {}
  }),
);

// --- helpers ---------------------------------------------------------------------------
const connected = () =>
  page.waitForFunction(() => document.querySelector("home-assistant")?.hass?.connected, null, { timeout: 90000 });
/** Full page load (incl. HA's login redirect); errors until it has settled are load-time errors. */
async function open(path) {
  settling = true;
  try {
    await page.goto(`${HA}${path}`);
    await connected();
    await page.waitForTimeout(1000);
  } finally {
    settling = false;
  }
}
/** Text inside the first element with this tag (deep), e.g. the Integrations page itself. */
const scopedText = (tag) =>
  page.evaluate((t) => {
    const find = (r) => { for (const el of r.querySelectorAll("*")) { if (el.localName === t) return el; if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; } } return null; };
    const host = find(document);
    if (!host) return null;
    let text = "";
    const walk = (root) => { for (const el of root.querySelectorAll("*")) if (el.shadowRoot) walk(el.shadowRoot); text += " " + root.textContent; };
    walk(host.shadowRoot ?? host);
    if (host.shadowRoot) text += " " + host.textContent;
    return text.replace(/\s+/g, " ");
  }, tag);
async function listing() {
  await navigate("/config/integrations/dashboard");
  const integrations = await waitFor(() => scopedText("ha-config-integrations-dashboard"));
  expect(integrations !== null, "Integrations page not found");
  expect(integrations.includes("Switch Timer"), "not on the Integrations page");
  await shot("integrations", "Settings → Integrations");
  await navigate("/config/helpers");
  await page.waitForTimeout(1500);
  const helpers = await waitFor(() => scopedText("ha-config-helpers"));
  expect(helpers !== null, "Helpers page not found");
  expect(/Test pump/.test(helpers), "Helpers list did not load");
  expect(!helpers.includes("Switch Timer"), "listed in Helpers");
  await shot("helpers", "Settings → Helpers (no Switch Timer row)");
  return "on the Integrations page; not in the Helpers list";
}
const ws = (msg) => page.evaluate((m) => document.querySelector("home-assistant").hass.callWS(m), msg);
const navigate = (path) =>
  page.evaluate((p) => {
    history.pushState(null, "", p);
    window.dispatchEvent(new CustomEvent("location-changed"));
  }, path);
const pageText = () =>
  page.evaluate(() => {
    let text = "";
    const walk = (root) => {
      for (const el of root.querySelectorAll("*")) {
        if (el.shadowRoot) walk(el.shadowRoot);
      }
      text += " " + (root.textContent ?? "");
    };
    walk(document);
    return text.replace(/\s+/g, " ");
  });
/** Info about switch-timer-card elements (optionally only inside a host element). */
const cards = (within) =>
  page.evaluate((w) => {
    const all = [];
    const walk = (root, out) => {
      for (const el of root.querySelectorAll("*")) {
        if (el.localName === "switch-timer-card") out.push(el);
        if (el.shadowRoot) walk(el.shadowRoot, out);
      }
    };
    let root = document;
    if (w) {
      const hosts = [];
      const find = (r) => { for (const el of r.querySelectorAll("*")) { if (el.localName === w) hosts.push(el); if (el.shadowRoot) find(el.shadowRoot); } };
      find(document);
      if (!hosts.length) return [];
      root = hosts[0].shadowRoot ?? hosts[0];
    }
    walk(root, all);
    return all.map((el) => {
      const sr = el.shadowRoot;
      const t = (s) => sr?.querySelector(s)?.textContent.trim().replace(/\s+/g, " ") ?? null;
      const box = sr?.querySelector("ha-card")?.getBoundingClientRect();
      const overflow = box
        ? [...sr.querySelectorAll("*")].filter((e) => e.getClientRects().length).filter((e) => { const r = e.getBoundingClientRect(); return r.right > box.right + 0.5 || r.left < box.left - 0.5; }).length
        : null;
      const time = sr?.querySelector(".label .time");
      return {
        entity: el._config?.entity ?? null,
        name: t(".name"),
        label: t(".label"),
        countdown: t(".countdown"),
        warning: t(".warning"),
        width: box ? Math.round(box.width) : null,
        overflow,
        timeFragments: time ? time.getClientRects().length : null,
      };
    });
  }, within ?? null);
const editorStatus = () =>
  page.evaluate(() => {
    const find = (r) => { for (const el of r.querySelectorAll("*")) { if (el.localName === "switch-timer-card-editor") return el; if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; } } return null; };
    return find(document)?.shadowRoot.querySelector(".status")?.textContent.trim() ?? null;
  });
const waitFor = async (fn, timeout = 20000) => {
  const end = Date.now() + timeout;
  let last;
  while (Date.now() < end) {
    last = await fn();
    if (last) return last;
    await page.waitForTimeout(300);
  }
  return last;
};
const hubEntries = () => ws({ type: "config_entries/get", domain: "switch_timer" });
const timers = async () => {
  const [hub] = await hubEntries();
  return hub ? ws({ type: "config_entries/subentries/list", entry_id: hub.entry_id }) : [];
};
async function openPicker() {
  await page.getByRole("button", { name: /add card/i }).first().click({ force: true });
  await page.waitForTimeout(600);
  await page.getByRole("tab", { name: /by card/i }).click({ force: true });
  await page.locator("hui-card-picker").getByPlaceholder(/search/i).first().fill("Switch Timer");
}
async function addSwitchTimerCard() {
  await page.locator("hui-card-picker").getByText("Switch Timer", { exact: true }).first().click({ force: true });
  await page.waitForTimeout(2000);
}
async function pickEntity(label) {
  await page.locator("hui-dialog-edit-card ha-entity-picker").first().click({ force: true });
  await page.waitForTimeout(600);
  await page.keyboard.type(label);
  await page.waitForTimeout(800);
  await page
    .locator("ha-combo-box-item")
    .filter({ hasText: label })
    .filter({ hasNotText: "state" })
    .first()
    .click({ force: true, timeout: 5000 });
}
async function saveCard() {
  await page.getByRole("button", { name: /^save$/i }).click({ force: true });
  await page.waitForTimeout(1500);
}
async function cancelDialog() {
  await page.getByRole("button", { name: /^cancel$/i }).first().click({ force: true });
  await page.waitForTimeout(800);
}
async function pickerDemoCheck(tag) {
  await openPicker();
  await page.waitForTimeout(250);
  const [first] = await cards("hui-card-picker");
  await shot(`${tag}-picker`, "Card picker: demo preview on first display");
  expect(first, "no Switch Timer preview in the card picker");
  expect(!first.entity, `preview uses an entity (${first.entity})`);
  expect(first.name === "Your selected switch", `preview name is ${JSON.stringify(first.name)}`);
  expect(first.countdown, "no countdown in the preview");
  await page.waitForTimeout(1500);
  const [later] = await cards("hui-card-picker");
  expect(later.countdown !== first.countdown, `countdown did not tick (${first.countdown})`);
  expect(later.overflow === 0, `${later.overflow} elements overflow the ${later.width}px preview`);
  expect(later.timeFragments === 1, "the off time is split across lines");
  return `"${first.name}", ${first.label}, ${first.countdown} → ${later.countdown}, ${later.width}px wide, no overflow`;
}

// --- 1. login without a password (trusted_networks bypass) -----------------------------
await check("login", "Opens without a login screen (trusted_networks bypass)", async () => {
  await open("/");
  const user = await page.evaluate(() => document.querySelector("home-assistant").hass.user);
  expect(user?.is_admin, "not logged in as an admin");
  return `logged in as "${user.name}" (admin) without credentials`;
});
await page.waitForTimeout(1500);
const haVersion = await page.evaluate(() => document.querySelector("home-assistant")?.hass?.config?.version).catch(() => null);

if (MODE === "provisioned") {
  await check("hub", "Switch Timer hub is set up, listed under Integrations, not in Helpers", async () => {
    const entries = await hubEntries();
    expect(entries.length === 1 && entries[0].state === "loaded", `entries: ${JSON.stringify(entries.map((e) => e.state))}`);
    return `1 entry, loaded; ${await listing()}`;
  });

  await check("timers", "Opening the test dashboard creates both timers automatically", async () => {
    await open("/switch-timer-test/test");
    const ready = await waitFor(async () => {
      const c = await cards();
      return c.length === 2 && c.every((x) => x.label) ? c : null;
    });
    expect(ready, `cards did not reach their normal view: ${JSON.stringify(await cards())}`);
    const list = await timers();
    expect(list.length === 2, `${list.length} timers`);
    await shot("dashboard", "Dashboard “Switch Timer test”: both cards, timers created");
    return `timers: ${list.map((t) => t.title).join(", ")}; cards: ${ready.map((c) => `${c.name} — ${c.label}`).join("; ")}`;
  });

  await check("run", "Tap starts a timed run with a ticking countdown; Stop now turns it off", async () => {
    await page.locator("switch-timer-card").first().locator(".header").click({ force: true });
    const on = await waitFor(async () => {
      const [c] = await cards();
      return c?.label?.startsWith("On · turns off at") && c.countdown ? c : null;
    });
    expect(on, `not timed after tap: ${JSON.stringify((await cards())[0])}`);
    await page.waitForTimeout(1500);
    const later = (await cards())[0];
    expect(later.countdown !== on.countdown, "countdown did not tick");
    await shot("timed", "Timed run");
    await page.locator("switch-timer-card").first().locator(".btn.strong").click({ force: true });
    const off = await waitFor(async () => ((await cards())[0]?.label?.startsWith("Off") ? (await cards())[0] : null));
    expect(off, "still on after Stop now");
    return `${on.label}, ${on.countdown} → ${later.countdown}; after Stop now: ${off.label}`;
  });

  await check("manual", "Turned on elsewhere: “On · no timer”, sensor mode manual", async () => {
    await ws({ type: "call_service", domain: "switch", service: "turn_on", target: { entity_id: "switch.test_pump" } });
    const manual = await waitFor(async () => ((await cards())[0]?.label === "On · no timer" ? (await cards())[0] : null));
    const mode = await page.evaluate(() => document.querySelector("home-assistant").hass.states["sensor.test_pump_ends_at"]?.attributes.mode);
    await ws({ type: "call_service", domain: "switch", service: "turn_off", target: { entity_id: "switch.test_pump" } });
    expect(manual, "card did not show the manual state");
    expect(mode === "manual", `sensor mode is ${mode}`);
    return "card “On · no timer”, sensor mode manual";
  });

  const ensureBefore = ensureCalls.length;
  await check("picker", "Card picker preview is the demo, renders on first display", async () => {
    await open("/switch-timer-test/test?edit=1");
    return pickerDemoCheck("p");
  });
  await check("new-card", "A new card starts empty: demo + “Pick a switch…”, no timer created", async () => {
    await addSwitchTimerCard();
    const status = await editorStatus();
    const [preview] = await cards("hui-dialog-edit-card");
    await shot("editor-new", "Editor for a new card");
    await cancelDialog();
    expect(status === "Pick a switch, light, fan or toggle.", `status: ${status}`);
    expect(preview && !preview.entity && preview.name === "Your selected switch", `preview: ${JSON.stringify(preview)}`);
    expect(ensureCalls.length === ensureBefore, `ensure_timer called: ${ensureCalls.slice(ensureBefore)}`);
    return `status “${status}”, preview demo, 0 ensure_timer calls from picker/editor`;
  });
} else {
  await check("clean", "Clean first start: no hub, no card loaded", async () => {
    expect((await hubEntries()).length === 0, "a Switch Timer entry exists");
    expect(!(await page.evaluate(() => Boolean(customElements.get("switch-timer-card")))), "card already defined");
    return "no switch_timer entry; card not loaded";
  });

  await check("add-hub", "Add integration → Switch Timer → Submit; success message says to reload", async () => {
    await navigate("/config/integrations/dashboard/add?domain=switch_timer");
    await page.waitForTimeout(2000);
    const ok = page.getByRole("button", { name: /^ok$/i });
    if (await ok.count()) await ok.first().click({ force: true });
    await page.waitForTimeout(1500);
    await shot("hub-step", "Setup step: no fields, just Submit");
    await page.getByRole("button", { name: /submit/i }).click({ force: true });
    await page.waitForTimeout(2500);
    await shot("hub-done", "Success dialog");
    const text = await pageText();
    expect(text.includes("Reload this page"), "success dialog has no reload hint");
    await page.getByRole("button", { name: /^finish$/i }).first().click({ force: true }).catch(() => {});
    await page.waitForTimeout(1000);
    const entries = await hubEntries();
    expect(entries.length === 1 && entries[0].state === "loaded", "hub not loaded");
    return "hub loaded; dialog: “Switch Timer is ready. Reload this page (F5) once …”";
  });

  await check("listing", "Listed under Integrations, not in Helpers", listing);

  await check("reload", "Card available after one page reload (expected: not before)", async () => {
    const before = await page.evaluate(() => Boolean(customElements.get("switch-timer-card")));
    await ws({ type: "lovelace/dashboards/create", url_path: "my-timers", title: "My timers", mode: "storage", show_in_sidebar: true, require_admin: false });
    await ws({ type: "lovelace/config/save", url_path: "my-timers", config: { views: [{ title: "Test", path: "test", cards: [] }] } });
    await open("/my-timers/test?edit=1");
    const after = await page.evaluate(() => Boolean(customElements.get("switch-timer-card")));
    expect(after, "card not defined after reload");
    return `before reload: ${before ? "defined" : "not defined (as documented)"}; after reload: defined`;
  });

  await check("picker", "Card picker preview is the demo, renders on first display", () => pickerDemoCheck("f"));

  await check("first-card", "New card: demo + prompt; picking Test pump creates its timer", async () => {
    await addSwitchTimerCard();
    const status = await editorStatus();
    expect(status === "Pick a switch, light, fan or toggle.", `status before pick: ${status}`);
    expect(ensureCalls.length === 0, `ensure_timer before pick: ${ensureCalls}`);
    await shot("editor-new", "Editor for a new card (before a pick)");
    await pickEntity("Test pump");
    const done = await waitFor(async () => ((await editorStatus())?.startsWith("✓") ? editorStatus() : null));
    const [preview] = await cards("hui-dialog-edit-card");
    await shot("editor-picked", "After picking Test pump");
    await saveCard();
    expect(done === "✓ Test pump has a Switch Timer.", `status after pick: ${await editorStatus()}`);
    expect(preview?.entity === "switch.test_pump" && preview.label, `preview: ${JSON.stringify(preview)}`);
    return `“${done}”; preview ${preview.name} — ${preview.label}`;
  });

  await check("second-card", "Second card starts empty (demo), picking Test fan creates its timer", async () => {
    await openPicker();
    await page.waitForTimeout(400);
    const [tile] = await cards("hui-card-picker");
    expect(tile && !tile.entity && tile.name === "Your selected switch", `picker preview: ${JSON.stringify(tile)}`);
    await addSwitchTimerCard();
    const status = await editorStatus();
    const [preview] = await cards("hui-dialog-edit-card");
    expect(status === "Pick a switch, light, fan or toggle.", `status: ${status}`);
    expect(preview && !preview.entity, `second card preview uses ${preview?.entity}`);
    await pickEntity("Test fan");
    const done = await waitFor(async () => ((await editorStatus())?.startsWith("✓") ? editorStatus() : null));
    await saveCard();
    expect(done === "✓ Test fan has a Switch Timer.", `status after pick: ${await editorStatus()}`);
    await page.waitForTimeout(1500);
    await shot("dashboard", "Dashboard with both cards");
    return `started empty (demo); “${done}”`;
  });

  await check("ensure-calls", "Exactly one timer creation per picked entity", async () => {
    const list = await timers();
    expect(JSON.stringify(ensureCalls) === JSON.stringify(["switch.test_pump", "fan.test_fan"]), `ensure_timer calls: ${JSON.stringify(ensureCalls)}`);
    expect(list.length === 2, `${list.length} timers`);
    return `ensure_timer: ${ensureCalls.join(", ")}; timers: ${list.map((t) => t.title).join(", ")}`;
  });
}

await check("errors", "No page errors once pages have loaded", async () => {
  expect(pageErrors.length === 0, pageErrors.slice(0, 3).join(" | "));
  const ignored = [...new Set(loadErrors.map((e) => e.replace(/\/frontend_latest\/[\w.]+\.js/, "/frontend_latest/<chunk>.js")))];
  return loadErrors.length
    ? `none; ignored ${loadErrors.length} load-time error(s) from HA's login redirect aborting chunk downloads: ${ignored.join(" | ")}`
    : "none";
});

const cardHash = await page
  // HA loads extra modules with import(), so look at the fetched resources, not <script> tags.
  .evaluate(() => performance.getEntriesByType("resource").map((e) => e.name).find((n) => n.includes("switch-timer-card.js")) ?? null)
  .catch(() => null);
fs.writeFileSync(
  `${OUT}/${MODE}.json`,
  JSON.stringify({ mode: MODE, haVersion, cardUrl: cardHash, finished: new Date().toISOString(), results, shots }, null, 2),
);
await browser.close();
process.exit(results.every((r) => r.ok) ? 0 : 1);
