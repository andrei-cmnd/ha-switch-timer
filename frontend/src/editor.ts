import { LitElement, css, html, nothing, type TemplateResult } from "lit";

import { defineElement } from "./register";
import "./setup-prompt";
import {
  DEFAULT_EXTEND_MINUTES,
  DEFAULT_ICON,
  DEFAULT_PRESETS,
  SUPPORTED_DOMAINS,
  type HomeAssistant,
  type SwitchTimerCardConfig,
  controlledEntities,
  findTimerEntities,
} from "./types";

const LABELS: Record<string, string> = {
  entity: "Entity",
  name: "Name",
  icon: "Icon",
  presets: "Presets",
  extend_minutes: "Extend step",
  show_hints: "Show hints",
};

const HELPERS: Record<string, string> = {
  name: "Leave empty to use the entity's name.",
  presets: "Minutes, separated by commas.",
  extend_minutes: "Minutes added by the extend button.",
};

/** Form values; presets are edited as text ("15, 30, 60, 120"). */
interface FormData {
  entity: string;
  name?: string;
  icon?: string;
  presets: string;
  extend_minutes: number;
  show_hints: boolean;
}

function parsePresets(text: string): number[] {
  return text
    .split(/[,\s]+/)
    .map(Number)
    .filter((minutes) => Number.isFinite(minutes) && minutes > 0);
}

class SwitchTimerCardEditor extends LitElement {
  static override properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  static override styles = css`
    .status {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 16px;
      font-size: 14px;
    }
    .has-timer {
      color: var(--success-color, #1f7a45);
    }
  `;

  hass?: HomeAssistant;
  private _config?: SwitchTimerCardConfig;

  setConfig(config: SwitchTimerCardConfig): void {
    this._config = config;
  }

  override connectedCallback(): void {
    super.connectedCallback();
    void this._loadHaForm();
  }

  /** ha-form is lazy-loaded by HA; opening a built-in card editor once makes it available. */
  private async _loadHaForm(): Promise<void> {
    if (customElements.get("ha-form")) return;
    try {
      const helpers = await (window as any).loadCardHelpers?.();
      const card = await helpers?.createCardElement({ type: "entities", entities: [] });
      await card?.constructor?.getConfigElement?.();
    } catch (err) {
      console.warn("switch-timer-card: could not preload ha-form", err);
    }
    this.requestUpdate();
  }

  private _schema(): unknown[] {
    return [
      {
        name: "entity",
        required: true,
        selector: { entity: { filter: [{ domain: SUPPORTED_DOMAINS }] } },
      },
      {
        type: "grid",
        name: "",
        schema: [
          { name: "name", selector: { text: {} } },
          { name: "icon", selector: { icon: { placeholder: DEFAULT_ICON } } },
        ],
      },
      { name: "presets", selector: { text: {} } },
      {
        type: "grid",
        name: "",
        schema: [
          {
            name: "extend_minutes",
            selector: { number: { min: 1, max: 240, mode: "box", unit_of_measurement: "min" } },
          },
          { name: "show_hints", selector: { boolean: {} } },
        ],
      },
    ];
  }

  protected override render(): TemplateResult | typeof nothing {
    if (!this.hass || !this._config) return nothing;
    const data: FormData = {
      entity: this._config.entity ?? "",
      name: this._config.name ?? "",
      icon: this._config.icon ?? "",
      presets: (this._config.presets ?? DEFAULT_PRESETS).join(", "),
      extend_minutes: this._config.extend_minutes ?? DEFAULT_EXTEND_MINUTES,
      show_hints: this._config.show_hints ?? true,
    };
    return html`<ha-form
      .hass=${this.hass}
      .data=${data}
      .schema=${this._schema()}
      .computeLabel=${(s: { name: string }) => LABELS[s.name] ?? s.name}
      .computeHelper=${(s: { name: string }) =>
        s.name === "entity" ? this._entityHelper() : HELPERS[s.name]}
      @value-changed=${this._valueChanged}
    ></ha-form>
    ${this._renderStatus()}`;
  }

  private _name(entityId: string): string {
    return this.hass?.states[entityId]?.attributes.friendly_name ?? entityId;
  }

  /** Mark which entities already have a Switch Timer. */
  private _entityHelper(): string {
    const names = controlledEntities(this.hass!).map((id) => this._name(id)).sort();
    if (!names.length) return "A switch, light, fan or toggle. None has a Switch Timer yet.";
    const shown = names.slice(0, 5).join(", ");
    const more = names.length > 5 ? ` and ${names.length - 5} more` : "";
    return `A switch, light, fan or toggle. With a Switch Timer: ${shown}${more}.`;
  }

  private _renderStatus(): TemplateResult | typeof nothing {
    const entityId = this._config?.entity;
    if (!entityId || !this.hass?.states[entityId]) return nothing;
    if (findTimerEntities(this.hass, entityId)) {
      return html`<div class="status has-timer">✓ ${this._name(entityId)} has a Switch Timer.</div>`;
    }
    return html`<div class="status">
      <div>${this._name(entityId)} has no Switch Timer yet.</div>
      <switch-timer-setup
        .hass=${this.hass}
        .entityId=${entityId}
        @switch-timer-created=${this._created}
      ></switch-timer-setup>
    </div>`;
  }

  private _created(): void {
    // Re-send the same config so HA rebuilds the preview with the new entities.
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: { ...this._config } },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _valueChanged(ev: CustomEvent<{ value: FormData }>): void {
    ev.stopPropagation();
    const value = ev.detail.value;
    // Keep the YAML minimal: options equal to their defaults are left out.
    const config: SwitchTimerCardConfig = { type: this._config!.type, entity: value.entity };
    if (value.name) config.name = value.name;
    if (value.icon) config.icon = value.icon;
    const presets = parsePresets(value.presets ?? "");
    if (presets.length && presets.join() !== DEFAULT_PRESETS.join()) config.presets = presets;
    if (value.extend_minutes && value.extend_minutes !== DEFAULT_EXTEND_MINUTES) {
      config.extend_minutes = value.extend_minutes;
    }
    if (value.show_hints === false) config.show_hints = false;
    this._config = config;
    this.dispatchEvent(
      new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }),
    );
  }
}

defineElement("switch-timer-card-editor", SwitchTimerCardEditor);
