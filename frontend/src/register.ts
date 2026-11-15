/**
 * Define a custom element now, and again if the page later swaps its registry.
 *
 * Home Assistant's frontend replaces `window.customElements` with its own registry
 * after integration-loaded modules (frontend extra module URLs, like this card) have
 * already run. Elements defined on the original registry are then invisible to
 * `customElements.get` and to HA's card loader ("Custom element not found").
 * So: define synchronously at load, then watch for a new registry for a while and
 * define there too.
 */
const WATCH_MS = 60_000;
const POLL_MS = 100;

export function defineElement(name: string, ctor: CustomElementConstructor): void {
  const defined = new WeakSet<CustomElementRegistry>();
  let first = true;

  const define = (): void => {
    const registry = window.customElements;
    if (defined.has(registry)) return;
    defined.add(registry);
    if (registry.get(name)) return;
    try {
      // A registry may refuse a constructor already used elsewhere: use a fresh subclass
      // for every registry after the first.
      const fresh = class extends (ctor as typeof HTMLElement) {} as CustomElementConstructor;
      registry.define(name, first ? ctor : fresh);
      first = false;
    } catch (err) {
      console.error(`switch-timer-card: could not define <${name}>`, err);
    }
  };

  define();
  const timer = window.setInterval(define, POLL_MS);
  window.setTimeout(() => window.clearInterval(timer), WATCH_MS);
  window.addEventListener("load", define, { once: true });
}
