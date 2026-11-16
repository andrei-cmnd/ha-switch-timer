// Automatic timer creation: the integration's admin-only `switch_timer/ensure_timer`
// creates a timer with the defaults (or returns the existing one).
import { DOMAIN, type HomeAssistant } from "./types";

export type EnsureResult = { ok: true; created: boolean } | { ok: false; message: string };

const inflight = new Map<string, Promise<EnsureResult>>();

/** One request per entity at a time (the editor and its preview may both ask). */
export function ensureTimer(hass: HomeAssistant, entityId: string): Promise<EnsureResult> {
  let request = inflight.get(entityId);
  if (!request) {
    request = hass
      .callWS<{ created: boolean; subentry_id: string }>({
        type: `${DOMAIN}/ensure_timer`,
        entity_id: entityId,
      })
      .then((result): EnsureResult => ({ ok: true, created: result.created }))
      .catch((err): EnsureResult => ({ ok: false, message: messageFor(err, entityId) }))
      .finally(() => inflight.delete(entityId));
    inflight.set(entityId, request);
  }
  return request;
}

const MESSAGES: Record<string, string> = {
  unknown_command:
    "This version of the Switch Timer integration can't create timers from the card. " +
    "Update it and restart Home Assistant.",
  unauthorized: "Only an admin can set up a Switch Timer. Ask an admin to pick this switch once.",
  not_supported: "Switch Timer works with switches, lights, fans and toggles.",
  not_loaded:
    "The Switch Timer integration isn't loaded. Check Settings → Devices & services → Switch Timer.",
};

function messageFor(err: unknown, entityId: string): string {
  const { code, message } = (err ?? {}) as { code?: string; message?: string };
  if (code === "not_found") return `Entity not found: ${entityId}`;
  return MESSAGES[code ?? ""] ?? `Could not set up the Switch Timer: ${message ?? String(err)}`;
}
