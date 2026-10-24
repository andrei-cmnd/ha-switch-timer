import { LitElement, html, nothing, type TemplateResult } from "lit";

import {
  DEFAULT_EXTEND_MINUTES,
  DEFAULT_ICON,
  DEFAULT_PRESETS,
  type HomeAssistant,
  type SwitchTimerCardConfig,
  controlledEntities,
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
  entity: "A switch, light, fan or toggle that has a Switch Timer.",
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
    const helpers = await (window as any).loadCardHelpers?.();
    const card = await helpers?.createCardElement({ type: "entities", entities: [] });
    await card?.constructor?.getConfigElement?.();
    this.requestUpdate();
  }

  private _schema(): unknown[] {
    return [
      {
        name: "entity",
        required: true,
        selector: { entity: { include_entities: this.hass ? controlledEntities(this.hass) : [] } },
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
      .computeHelper=${(s: { name: string }) => HELPERS[s.name]}
      @value-changed=${this._valueChanged}
    ></ha-form>`;
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

if (!customElements.get("switch-timer-card-editor")) {
  customElements.define("switch-timer-card-editor", SwitchTimerCardEditor);
}
