// Minimal Home Assistant frontend types used by the card (no external type packages).

export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, any>;
}

export interface EntityRegistryDisplayEntry {
  entity_id: string;
  device_id?: string;
  platform?: string;
  translation_key?: string;
}

export interface HomeAssistant {
  states: Record<string, HassEntity>;
  entities: Record<string, EntityRegistryDisplayEntry>;
  locale: { language: string; time_format?: string };
  themes: { darkMode?: boolean };
  callService(
    domain: string,
    service: string,
    data?: Record<string, unknown>,
  ): Promise<unknown>;
}

export interface SwitchTimerCardConfig {
  type: string;
  entity: string;
  name?: string;
  icon?: string;
  presets?: number[];
  extend_minutes?: number;
  show_hints?: boolean;
}

export const DOMAIN = "switch_timer";
export const DEFAULT_ICON = "mdi:power";
export const DEFAULT_PRESETS = [15, 30, 60, 120];
export const DEFAULT_EXTEND_MINUTES = 15;

/** The Switch Timer entities that belong to one controlled entity. */
export interface TimerEntities {
  sensor: string;
  number?: string;
}

/** Find the ends-at sensor (linked by attribute) and the run-time number (same device). */
export function findTimerEntities(
  hass: HomeAssistant,
  entityId: string,
): TimerEntities | undefined {
  const entries = Object.values(hass.entities ?? {});
  const sensor = entries.find(
    (e) =>
      e.platform === DOMAIN &&
      e.translation_key === "ends_at" &&
      hass.states[e.entity_id]?.attributes.controlled_entity_id === entityId,
  );
  if (!sensor) return undefined;
  const number = entries.find(
    (e) =>
      e.platform === DOMAIN &&
      e.translation_key === "run_time" &&
      e.device_id !== undefined &&
      e.device_id === sensor.device_id,
  );
  return { sensor: sensor.entity_id, number: number?.entity_id };
}

/** Controlled entity ids that have a Switch Timer. */
export function controlledEntities(hass: HomeAssistant): string[] {
  return Object.values(hass.entities ?? {})
    .filter((e) => e.platform === DOMAIN && e.translation_key === "ends_at")
    .map((e) => hass.states[e.entity_id]?.attributes.controlled_entity_id)
    .filter((id): id is string => typeof id === "string");
}

/** "15 min", "1 h", "2 h", "90 min". */
export function formatMinutes(minutes: number): string {
  return minutes >= 60 && minutes % 60 === 0 ? `${minutes / 60} h` : `${minutes} min`;
}
