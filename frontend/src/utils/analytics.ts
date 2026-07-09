/**
 * Google Analytics 4 — no SDK, just the standard gtag.js bootstrap.
 *
 * The measurement ID comes from runtime config (`window.__ORCHESTRA_CONFIG__`,
 * written by docker-entrypoint.sh from the VITE_GA_MEASUREMENT_ID container env
 * var that the Helm chart sets — same mechanism as apiUrl) or, for local dev,
 * from the VITE_GA_MEASUREMENT_ID build-time env var. When neither is set
 * (local dev, CI, tests) analytics is completely inert: no script tag is
 * injected, no network calls happen, and track() is a no-op.
 *
 * Event params must NEVER contain PII — template slugs, phases, and booleans
 * are fine; emails, tokens, and per-session instance URLs are not.
 */

export type EventParams = Record<string, string | number | boolean>;

declare global {
  interface Window {
    __ORCHESTRA_CONFIG__?: { apiUrl?: string; gaMeasurementId?: string };
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

let enabled = false;

/** Inject gtag.js and start the command queue. Call once at startup. */
export function initAnalytics(): void {
  const id =
    window.__ORCHESTRA_CONFIG__?.gaMeasurementId ||
    import.meta.env.VITE_GA_MEASUREMENT_ID ||
    '';
  if (!id || enabled) return;

  window.dataLayer = window.dataLayer || [];
  window.gtag = function () {
    // gtag.js requires the Arguments object itself, not a spread array.
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer!.push(arguments);
  };
  window.gtag('js', new Date());
  // SPA: the default snippet only records the first page, so page_view is sent
  // manually on every route change instead (PageTracker in App.tsx).
  window.gtag('config', id, { send_page_view: false });

  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.appendChild(script);
  enabled = true;
}

/** Send a GA4 event. No-op when analytics is off. Params must contain no PII. */
export function track(event: string, params?: EventParams): void {
  if (!enabled) return;
  window.gtag?.('event', event, params);
}

/** Manual SPA page view (init disables automatic ones via send_page_view: false). */
export function trackPageView(path: string): void {
  track('page_view', {
    page_path: path,
    page_title: document.title,
    page_location: window.location.origin + path,
  });
}
