import { LitElement, html, nothing, type PropertyValues, type TemplateResult } from "lit";
import { keyed } from "lit/directives/keyed.js";

import "./editor";
import { cardStyles, tokens } from "./styles";
import {
  DEFAULT_EXTEND_MINUTES,
  DEFAULT_ICON,
  DEFAULT_PRESETS,
  DOMAIN,
  type HomeAssistant,
  type SwitchTimerCardConfig,
  type TimerEntities,
  controlledEntities,
  findTimerEntities,
  formatMinutes,
} from "./types";

type Mode = "off" | "timed" | "manual" | "unavailable";

const HOLD_MS = 500; // header hold → more-info; −/+ hold → start repeating
const REPEAT_MS = 150; // −/+ repeat rate while held
const SEND_MS = 500; // at most one number.set_value per this interval while held

class SwitchTimerCard extends LitElement {
  static override properties = {
    hass: { attribute: false },
    _config: { state: true },
    _now: { state: true },
    _localRunTime: { state: true },
  };

  static override styles = [tokens, cardStyles];

  hass?: HomeAssistant;
  private _config?: SwitchTimerCardConfig;
  private _now = Date.now();
  /** Run time shown while −/+ are being pressed, before HA has the new value. */
  private _localRunTime?: number;

  private _timerEntities?: TimerEntities;
  private _lookupKey?: unknown;
  private _tick?: number;
  private _bar?: { key: string; style: string };

  private _headerHold?: number;
  private _headerHeld = false;
  private _repeatDelay?: number;
  private _repeatTimer?: number;
  private _lastSent = 0;
  private _stepping = false;

  static getConfigElement(): HTMLElement {
    return document.createElement("switch-timer-card-editor");
  }

  static getStubConfig(hass: HomeAssistant): Partial<SwitchTimerCardConfig> {
    return { entity: controlledEntities(hass)[0] ?? "" };
  }

  setConfig(config: SwitchTimerCardConfig): void {
    if (!config?.entity) throw new Error("Set the entity controlled by a Switch Timer");
    if (
      config.presets !== undefined &&
      (!Array.isArray(config.presets) ||
        config.presets.some((m) => typeof m !== "number" || !(m > 0)))
    ) {
      throw new Error("presets must be a list of minutes, e.g. [15, 30, 60, 120]");
    }
    this._config = config;
  }

  getCardSize(): number {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this._stopTicking();
    this._endStep(false);
    clearTimeout(this._headerHold);
  }

  override connectedCallback(): void {
    super.connectedCallback();
    if (this.hasUpdated) this.requestUpdate();
  }

  protected override willUpdate(changed: PropertyValues): void {
    if (!this.hass || !this._config) return;
    this.toggleAttribute("dark", Boolean(this.hass.themes?.darkMode));

    // Re-resolve the Switch Timer entities when the registry or the config changes.
    const key = `${this._config.entity}|${Object.keys(this.hass.entities ?? {}).length}`;
    if (changed.has("_config") || this._lookupKey !== key || !this._timerEntities) {
      this._lookupKey = key;
      this._timerEntities = findTimerEntities(this.hass, this._config.entity);
    }

    // Drop the local run time once HA reports it (and nothing is held).
    const number = this._numberState();
    if (
      this._localRunTime !== undefined &&
      !this._stepping &&
      number &&
      Number(number.state) === this._localRunTime
    ) {
      this._localRunTime = undefined;
    }
  }

  protected override updated(): void {
    if (this._mode() === "timed") this._startTicking();
    else this._stopTicking();
  }

  // --- State --------------------------------------------------------------------

  private _entityState() {
    return this._config ? this.hass?.states[this._config.entity] : undefined;
  }

  private _sensorState() {
    return this._timerEntities ? this.hass?.states[this._timerEntities.sensor] : undefined;
  }

  private _numberState() {
    const id = this._timerEntities?.number;
    return id ? this.hass?.states[id] : undefined;
  }

  private _endsAt(): number | undefined {
    const ends = Date.parse(this._sensorState()?.state ?? "");
    return Number.isNaN(ends) ? undefined : ends;
  }

  private _mode(): Mode {
    const state = this._entityState()?.state;
    if (state === undefined || state === "unavailable" || state === "unknown") {
      return "unavailable";
    }
    if (state !== "on") return "off";
    return this._endsAt() !== undefined ? "timed" : "manual";
  }

  private _runTime(): number {
    if (this._localRunTime !== undefined) return this._localRunTime;
    const value = Number(this._numberState()?.state);
    return Number.isFinite(value) ? value : 30;
  }

  // --- Actions ------------------------------------------------------------------

  private _call(service: string, data: Record<string, unknown> = {}): void {
    if (!this.hass || !this._config) return;
    this.hass.callService(DOMAIN, service, { entity_id: this._config.entity, ...data });
  }

  private _moreInfo(entityId: string | undefined): void {
    if (!entityId) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _haptic(): void {
    window.dispatchEvent(new CustomEvent("haptic", { detail: "medium" }));
  }

  private _toggle(): void {
    const mode = this._mode();
    if (mode === "unavailable") return;
    this._haptic();
    this._call(mode === "off" ? "start" : "stop");
  }

  private _startPreset(minutes: number): void {
    const number = this._numberState();
    const { min, max } = number?.attributes ?? {};
    // Like the prototype, a preset also becomes the run time (when it fits the range).
    if (number && minutes !== this._runTime() && minutes >= (min ?? 1) && minutes <= (max ?? Infinity)) {
      this.hass?.callService("number", "set_value", {
        entity_id: number.entity_id,
        value: minutes,
      });
    }
    this._haptic();
    this._call("start", { minutes });
  }

  // --- Header: tap / hold -------------------------------------------------------

  private _onHeaderDown(ev: PointerEvent): void {
    if (ev.button !== 0) return;
    this._headerHeld = false;
    clearTimeout(this._headerHold);
    this._headerHold = window.setTimeout(() => {
      this._headerHeld = true;
      this._moreInfo(this._config?.entity);
    }, HOLD_MS);
  }

  private _onHeaderUp(): void {
    if (this._headerHold === undefined) return;
    clearTimeout(this._headerHold);
    this._headerHold = undefined;
    if (!this._headerHeld) this._toggle();
  }

  private _onHeaderCancel(): void {
    clearTimeout(this._headerHold);
    this._headerHold = undefined;
  }

  private _onHeaderKey(ev: KeyboardEvent): void {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      this._toggle();
    }
  }

  // --- Run time −/+: local value while held, throttled set_value -------------------

  private _step(direction: 1 | -1): void {
    const attrs = this._numberState()?.attributes ?? {};
    const step = Number(attrs.step) || 1;
    const min = Number(attrs.min ?? 1);
    const max = Number(attrs.max ?? 240);
    const next = Math.min(max, Math.max(min, this._runTime() + direction * step));
    this._localRunTime = Math.round(next * 1000) / 1000;
  }

  private _send(): void {
    const number = this._numberState();
    this._lastSent = Date.now();
    if (!number || this._localRunTime === undefined) return;
    if (Number(number.state) === this._localRunTime) return;
    this.hass
      ?.callService("number", "set_value", {
        entity_id: number.entity_id,
        value: this._localRunTime,
      })
      .catch(() => {
        this._localRunTime = undefined;
      });
  }

  private _onStepDown(ev: PointerEvent, direction: 1 | -1): void {
    if (ev.button !== 0) return;
    ev.preventDefault();
    (ev.currentTarget as HTMLElement).setPointerCapture?.(ev.pointerId);
    this._stepping = true;
    this._lastSent = Date.now();
    this._step(direction);
    this._repeatDelay = window.setTimeout(() => {
      this._repeatTimer = window.setInterval(() => {
        this._step(direction);
        if (Date.now() - this._lastSent >= SEND_MS) this._send();
      }, REPEAT_MS);
    }, HOLD_MS);
  }

  private _endStep(send = true): void {
    if (!this._stepping) return;
    clearTimeout(this._repeatDelay);
    clearInterval(this._repeatTimer);
    this._stepping = false;
    if (send) this._send();
  }

  private _onStepClick(ev: MouseEvent, direction: 1 | -1): void {
    // Pointer presses are handled above; this is keyboard activation (Enter/Space).
    if (ev.detail !== 0) return;
    this._step(direction);
    this._send();
  }

  // --- Countdown ----------------------------------------------------------------

  private _startTicking(): void {
    if (this._tick !== undefined) return;
    const tick = () => {
      this._now = Date.now();
      // Re-arm on the next whole second so the display changes in step with the clock.
      this._tick = window.setTimeout(tick, 1000 - (Date.now() % 1000) + 10);
    };
    tick();
  }

  private _stopTicking(): void {
    clearTimeout(this._tick);
    this._tick = undefined;
  }

  private _barStyle(endsAt: number, duration: number): { key: string; style: string } {
    // Computed once per run (or extension); the CSS animation shrinks it smoothly from there.
    const key = `${endsAt}|${duration}`;
    if (this._bar?.key !== key) {
      const leftMs = Math.max(0, endsAt - Date.now());
      const pct = duration > 0 ? Math.min(100, (leftMs / (duration * 1000)) * 100) : 0;
      this._bar = { key, style: `width:${pct}%;animation-duration:${leftMs}ms` };
    }
    return this._bar;
  }

  // --- Rendering ----------------------------------------------------------------

  private _formatTime(ms: number): string {
    const timeFormat = this.hass?.locale.time_format;
    return new Intl.DateTimeFormat(this.hass?.locale.language, {
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: timeFormat === "12" ? "h12" : timeFormat === "24" ? "h23" : undefined,
    }).format(ms);
  }

  private _label(mode: Mode): string {
    switch (mode) {
      case "timed":
        return `On · turns off at ${this._formatTime(this._endsAt()!)}`;
      case "manual":
        return "On · no timer";
      case "off":
        return `Off · tap to run for ${this._runTime()} min`;
      default:
        return "Unavailable";
    }
  }

  protected override render(): TemplateResult | typeof nothing {
    if (!this.hass || !this._config) return nothing;
    const entity = this._entityState();
    if (!this._timerEntities) {
      return html`<ha-card>
        <div class="warning">
          No Switch Timer is set up for ${this._config.entity}. Add one in Settings → Devices &
          services → Switch Timer.
        </div>
      </ha-card>`;
    }
    const mode = this._mode();
    const on = mode === "timed" || mode === "manual";
    const name = this._config.name || entity?.attributes.friendly_name || this._config.entity;

    return html`<ha-card>
      <div
        class="header ${on ? "on" : ""} ${mode === "unavailable" ? "unavailable" : ""}"
        role="button"
        tabindex="0"
        aria-label=${`${name}: ${this._label(mode)}`}
        @pointerdown=${this._onHeaderDown}
        @pointerup=${this._onHeaderUp}
        @pointerleave=${this._onHeaderCancel}
        @pointercancel=${this._onHeaderCancel}
        @contextmenu=${(ev: Event) => ev.preventDefault()}
        @keydown=${this._onHeaderKey}
      >
        <div class="icon-circle">
          <ha-icon .icon=${this._config.icon || DEFAULT_ICON}></ha-icon>
        </div>
        <div class="titles">
          <div class="name">${name}</div>
          <div class="label">${this._label(mode)}</div>
        </div>
        <div class="pill">${mode === "unavailable" ? "N/A" : on ? "ON" : "OFF"}</div>
      </div>
      ${mode === "off"
        ? this._renderOff()
        : mode === "timed"
          ? this._renderTimed()
          : mode === "manual"
            ? this._renderManual()
            : nothing}
    </ha-card>`;
  }

  private _renderOff(): TemplateResult {
    const runTime = this._runTime();
    const presets = this._config!.presets ?? DEFAULT_PRESETS;
    return html`
      ${this._numberState()
        ? html`<div class="run-time">
            <div class="run-time-title">Run time</div>
            <button
              class="square"
              aria-label="Decrease run time"
              @pointerdown=${(ev: PointerEvent) => this._onStepDown(ev, -1)}
              @pointerup=${() => this._endStep()}
              @pointercancel=${() => this._endStep()}
              @click=${(ev: MouseEvent) => this._onStepClick(ev, -1)}
            >
              −
            </button>
            <button
              class="value"
              aria-label="Set run time"
              @click=${() => this._moreInfo(this._timerEntities?.number)}
            >
              ${runTime} min
            </button>
            <button
              class="square"
              aria-label="Increase run time"
              @pointerdown=${(ev: PointerEvent) => this._onStepDown(ev, 1)}
              @pointerup=${() => this._endStep()}
              @pointercancel=${() => this._endStep()}
              @click=${(ev: MouseEvent) => this._onStepClick(ev, 1)}
            >
              +
            </button>
          </div>`
        : nothing}
      <div class="presets">
        ${presets.map(
          (minutes) =>
            html`<button
              class="preset ${minutes === runTime ? "selected" : ""}"
              @click=${() => this._startPreset(minutes)}
            >
              ${formatMinutes(minutes)}
            </button>`,
        )}
      </div>
      ${this._hint("Tap the card to start · hold for details")}
    `;
  }

  private _renderTimed(): TemplateResult {
    const endsAt = this._endsAt()!;
    const duration = Number(this._sensorState()?.attributes.duration) || 0;
    const left = Math.max(0, Math.ceil((endsAt - this._now) / 1000));
    const countdown = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;
    const bar = this._barStyle(endsAt, duration);
    const extend = this._config!.extend_minutes ?? DEFAULT_EXTEND_MINUTES;
    return html`
      <div class="time-box">
        <div class="timer-icon"><ha-icon icon="mdi:timer-outline"></ha-icon></div>
        <div class="time-left">Time left</div>
        <div class="countdown" role="timer">${countdown}</div>
        <div class="bar">
          ${keyed(bar.key, html`<div class="bar-remaining" style=${bar.style}></div>`)}
        </div>
      </div>
      <div class="buttons">
        <button class="btn" @click=${() => this._call("extend", { minutes: extend })}>
          +${extend} min
        </button>
        <button class="btn strong" @click=${() => this._call("stop")}>Stop now</button>
      </div>
      ${this._hint("Tap the card to stop")}
    `;
  }

  private _renderManual(): TemplateResult {
    return html`<div class="buttons">
      <button class="btn accent" @click=${() => this._call("start")}>
        Start ${this._runTime()} min timer
      </button>
      <button class="btn strong" @click=${() => this._call("stop")}>Turn off</button>
    </div>`;
  }

  private _hint(text: string): TemplateResult | typeof nothing {
    return this._config!.show_hints === false ? nothing : html`<div class="hint">${text}</div>`;
  }
}

if (!customElements.get("switch-timer-card")) {
  customElements.define("switch-timer-card", SwitchTimerCard);
}

declare global {
  interface Window {
    customCards?: Array<Record<string, unknown>>;
  }
}

window.customCards = window.customCards ?? [];
if (!window.customCards.some((card) => card.type === "switch-timer-card")) {
  window.customCards.push({
    type: "switch-timer-card",
    name: "Switch Timer",
    description: "Turn a device on for a set time from the dashboard.",
    preview: true,
    documentationURL: "https://github.com/andrei-cmnd/ha-switch-timer",
  });
}
