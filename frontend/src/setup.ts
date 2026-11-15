// One-click Switch Timer creation from the frontend, through the standard config flow.
// The flow's own defaults supply name (= entity name), min 1, max 240, step 1, extend 15.
import { DOMAIN, type HomeAssistant } from "./types";

export const DEFAULT_RUN_TIME = 30;

export type CreateResult = { ok: true; title: string } | { ok: false; message: string };

interface FlowResult {
  type: "form" | "create_entry" | "abort" | string;
  flow_id?: string;
  reason?: string;
  title?: string;
  errors?: Record<string, string> | null;
}

const ABORT_MESSAGES: Record<string, string> = {
  already_configured: "This entity already has a Switch Timer.",
};

/** Start the switch_timer config flow for `entityId` and finish it with defaults. Admins only. */
export async function createSwitchTimer(
  hass: HomeAssistant,
  entityId: string,
): Promise<CreateResult> {
  let flowId: string | undefined;
  try {
    const start = await hass.callApi<FlowResult>("POST", "config/config_entries/flow", {
      handler: DOMAIN,
      show_advanced_options: false,
    });
    if (start.type !== "form" || !start.flow_id) return failed(start);
    flowId = start.flow_id;

    const result = await hass.callApi<FlowResult>(
      "POST",
      `config/config_entries/flow/${flowId}`,
      { entity_id: entityId, default_run_time: DEFAULT_RUN_TIME },
    );
    if (result.type !== "form") flowId = undefined; // finished: nothing to clean up
    if (result.type === "create_entry") return { ok: true, title: result.title ?? entityId };
    return failed(result);
  } catch (err) {
    return { ok: false, message: `Could not create the Switch Timer: ${errorText(err)}` };
  } finally {
    // A flow that stopped at a form (e.g. a validation error) would stay open; close it.
    if (flowId) {
      hass.callApi("DELETE", `config/config_entries/flow/${flowId}`).catch(() => undefined);
    }
  }
}

function failed(result: FlowResult): CreateResult {
  if (result.type === "abort") {
    const reason = result.reason ?? "unknown";
    return { ok: false, message: ABORT_MESSAGES[reason] ?? `Setup was aborted (${reason}).` };
  }
  const errors = Object.values(result.errors ?? {}).join(", ");
  return { ok: false, message: `Setup did not finish${errors ? ` (${errors})` : ""}.` };
}

function errorText(err: unknown): string {
  if (err && typeof err === "object") {
    const e = err as { body?: { message?: string }; message?: string; error?: string };
    return e.body?.message ?? e.message ?? e.error ?? JSON.stringify(err);
  }
  return String(err);
}
