import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";

import { defineElement } from "./register";
import { createSwitchTimer } from "./setup";
import type { HomeAssistant } from "./types";

/**
 * "Create Switch Timer" for admins, "Ask an admin…" for everyone else.
 * Fires `switch-timer-created` ({ entityId, title }) after the entry is created.
 */
class SwitchTimerSetup extends LitElement {
  static override properties = {
    hass: { attribute: false },
    entityId: { attribute: false },
    _busy: { state: true },
    _error: { state: true },
  };

  static override styles = css`
    :host {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }
    button {
      height: 40px;
      padding: 0 16px;
      border: none;
      border-radius: 10px;
      background: var(--st-strong-bg, #1f2328);
      color: var(--st-strong-text, #ffffff);
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }
    button:disabled {
      cursor: default;
      opacity: 0.6;
    }
    p {
      margin: 0;
      font-size: 14px;
      color: var(--st-text-secondary, var(--secondary-text-color, #555b63));
    }
    .error {
      color: var(--error-color, #db4437);
    }
  `;

  hass?: HomeAssistant;
  entityId?: string;
  private _busy = false;
  private _error?: string;

  protected override willUpdate(changed: PropertyValues): void {
    if (changed.has("entityId")) this._error = undefined;
  }

  protected override render(): TemplateResult | typeof nothing {
    if (!this.hass || !this.entityId) return nothing;
    if (!this.hass.user?.is_admin) {
      return html`<p>Ask an admin to set up Switch Timer for this entity.</p>`;
    }
    return html`
      <button ?disabled=${this._busy} @click=${this._create}>
        ${this._busy ? "Creating…" : "Create Switch Timer"}
      </button>
      ${this._error ? html`<p class="error" role="alert">${this._error}</p>` : nothing}
    `;
  }

  private async _create(): Promise<void> {
    if (!this.hass || !this.entityId || this._busy) return;
    const entityId = this.entityId;
    this._busy = true;
    this._error = undefined;
    const result = await createSwitchTimer(this.hass, entityId);
    this._busy = false;
    if (!result.ok) {
      this._error = result.message;
      return;
    }
    this.dispatchEvent(
      new CustomEvent("switch-timer-created", {
        detail: { entityId, title: result.title },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

defineElement("switch-timer-setup", SwitchTimerSetup);
