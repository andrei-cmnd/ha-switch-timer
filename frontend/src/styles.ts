import { css, unsafeCSS } from "lit";

// Every color is a token with a light and a dark default. A theme can override any token
// with `--switch-timer-<name>`. Dark defaults lean on HA theme variables where it makes sense.
const TOKENS: Record<string, [light: string, dark: string]> = {
  "frame-bg": ["#FFFFFF", "var(--ha-card-background, var(--card-background-color, #1C1C1E))"],
  "frame-border": ["#C9CDD2", "#3B4047"],
  text: ["#1F2328", "var(--primary-text-color, #E6E8EB)"],
  "text-secondary": ["#555B63", "var(--secondary-text-color, #A3A9B1)"],
  "header-bg": ["#F4F5F7", "#2A2E34"],
  "icon-bg": ["#DADDE1", "#3B4047"],
  "icon-color": ["#4A5058", "#C9CDD2"],
  "pill-bg": ["#E4E6EA", "#3B4047"],
  "pill-text": ["#555B63", "#C9CDD2"],
  "on-bg": ["#E5F4EB", "rgba(46, 158, 91, 0.16)"],
  "on-border": ["#2E9E5B", "#2E9E5B"],
  "on-icon-bg": ["#2E9E5B", "#2E9E5B"],
  "on-icon-color": ["#FFFFFF", "#FFFFFF"],
  "on-label": ["#1E5A37", "#8FD6AB"],
  "on-pill-bg": ["#1F7A45", "#1F7A45"],
  "on-pill-text": ["#FFFFFF", "#FFFFFF"],
  "control-bg": ["#FFFFFF", "#2A2E34"],
  "control-border": ["#C9CDD2", "#4A5058"],
  "strong-bg": ["#1F2328", "#E6E8EB"],
  "strong-text": ["#FFFFFF", "#1F2328"],
  "box-bg": ["#F4F5F7", "#2A2E34"],
  accent: ["#2E9E5B", "#2E9E5B"],
  "accent-text": ["#1F7A45", "#5CC48A"],
  "accent-soft": ["#D3ECDD", "#1F3A2B"],
};

const declarations = (index: 0 | 1): string =>
  Object.entries(TOKENS)
    .map(([name, values]) => `--st-${name}: var(--switch-timer-${name}, ${values[index]});`)
    .join("\n");

export const tokens = unsafeCSS(`
  :host { ${declarations(0)} }
  :host([dark]) { ${declarations(1)} }
`);

export const cardStyles = css`
  :host {
    display: block;
  }
  ha-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    border: 2px solid var(--st-frame-border);
    border-radius: 20px;
    background: var(--st-frame-bg);
    box-shadow: none;
    color: var(--st-text);
  }
  button {
    font: inherit;
    color: inherit;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  button:disabled {
    cursor: default;
    opacity: 0.5;
  }
  :focus-visible {
    outline: 2px solid var(--st-accent);
    outline-offset: 2px;
  }

  /* Header */
  .header {
    display: grid;
    grid-template-columns: 48px 1fr auto;
    align-items: center;
    column-gap: 12px;
    padding: 14px;
    border: 2px solid transparent;
    border-radius: 16px;
    background: var(--st-header-bg);
    cursor: pointer;
    user-select: none;
    -webkit-user-select: none;
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }
  .header.unavailable {
    cursor: default;
    opacity: 0.6;
  }
  .icon-circle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: var(--st-icon-bg);
    color: var(--st-icon-color);
    --mdc-icon-size: 24px;
  }
  .titles {
    min-width: 0;
  }
  .name {
    overflow: hidden;
    font-size: 20px;
    font-weight: 600;
    line-height: 1.3;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .label {
    font-size: 14px;
    line-height: 1.4;
    color: var(--st-text-secondary);
  }
  .pill {
    padding: 6px 12px;
    border-radius: 999px;
    background: var(--st-pill-bg);
    color: var(--st-pill-text);
    font-size: 13px;
    font-weight: 600;
  }
  .header.on {
    border-color: var(--st-on-border);
    background: var(--st-on-bg);
  }
  .header.on .icon-circle {
    background: var(--st-on-icon-bg);
    color: var(--st-on-icon-color);
  }
  .header.on .label {
    color: var(--st-on-label);
  }
  .header.on .pill {
    background: var(--st-on-pill-bg);
    color: var(--st-on-pill-text);
  }

  /* Off: run time + presets */
  .run-time {
    display: grid;
    grid-template-columns: 1fr 44px 96px 44px;
    align-items: center;
    column-gap: 8px;
    padding: 4px;
  }
  .run-time-title {
    font-size: 16px;
    font-weight: 500;
  }
  .square {
    width: 44px;
    height: 44px;
    padding: 0;
    border: 1px solid var(--st-control-border);
    border-radius: 10px;
    background: var(--st-control-bg);
    color: var(--st-text);
    font-size: 22px;
    line-height: 1;
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
  }
  .value {
    height: 44px;
    padding: 0;
    border: 1px dashed var(--st-control-border);
    border-radius: 10px;
    background: none;
    color: var(--st-text);
    font-size: 20px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .presets {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
  }
  .preset {
    height: 48px;
    border: 1px solid var(--st-control-border);
    border-radius: 10px;
    background: var(--st-control-bg);
    color: var(--st-text);
    font-size: 14px;
  }
  .preset.selected {
    border-color: var(--st-strong-bg);
    background: var(--st-strong-bg);
    color: var(--st-strong-text);
  }

  /* On + timed: time left */
  .time-box {
    display: grid;
    grid-template-columns: 40px 1fr auto;
    grid-template-areas: "icon title countdown" "icon bar bar";
    align-items: center;
    column-gap: 12px;
    row-gap: 8px;
    padding: 12px 14px;
    border-radius: 12px;
    background: var(--st-box-bg);
  }
  .timer-icon {
    grid-area: icon;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--st-accent-soft);
    color: var(--st-accent-text);
    --mdc-icon-size: 20px;
  }
  .time-left {
    grid-area: title;
    font-size: 15px;
    font-weight: 600;
  }
  .countdown {
    grid-area: countdown;
    color: var(--st-accent-text);
    font-size: 20px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  /* Segments are fixed px (6px on, 2px gap), cut out of the bar with a mask. */
  .bar {
    grid-area: bar;
    position: relative;
    height: 8px;
    overflow: hidden;
    background: var(--st-accent-soft);
    -webkit-mask: repeating-linear-gradient(90deg, #000 0 6px, transparent 6px 8px);
    mask: repeating-linear-gradient(90deg, #000 0 6px, transparent 6px 8px);
  }
  .bar-remaining {
    position: absolute;
    inset: 0 auto 0 0;
    background: var(--st-accent);
    animation-name: shrink;
    animation-timing-function: linear;
    animation-fill-mode: forwards;
  }
  @keyframes shrink {
    to {
      width: 0;
    }
  }

  /* Buttons */
  .buttons {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .btn {
    height: 48px;
    border: 1px solid var(--st-control-border);
    border-radius: 10px;
    background: var(--st-control-bg);
    color: var(--st-text);
    font-size: 15px;
  }
  .btn.strong {
    border-color: var(--st-strong-bg);
    background: var(--st-strong-bg);
    color: var(--st-strong-text);
    font-weight: 600;
  }
  .btn.accent {
    border-color: var(--st-accent);
    color: var(--st-accent-text);
  }

  .hint {
    font-size: 13px;
    color: var(--st-text-secondary);
    text-align: center;
  }
  .warning {
    padding: 8px;
    color: var(--st-text-secondary);
  }
`;
