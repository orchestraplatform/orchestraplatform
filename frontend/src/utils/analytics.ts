/**
 * Google Analytics 4 — no SDK, just the standard gtag.js bootstrap.
 *
 * Sends to the shared "Sean Davis — web" GA4 property (public ID, hardcoded)
 * with content_group 'orchestraplatform'. On non-production hosts (localhost,
 * raw IPs, *.workers.dev / *.netlify.app / *.ts.net) analytics is completely
 * inert: no script tag is injected, no network calls happen, and track() is a
 * no-op.
 *
 * Event params must NEVER contain PII — template slugs, phases, and booleans
 * are fine; emails, tokens, and per-session instance URLs are not.
 */

export type EventParams = Record<string, string | number | boolean>;

declare global {
  interface Window {
    __ORCHESTRA_CONFIG__?: { apiUrl?: string };
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

const GA_ID = 'G-KLLV1GCF4E';
const NON_PRODUCTION_HOST =
  /^(localhost|127\.0\.0\.1|\[::1\]|\d+(\.\d+){3})$|\.(workers\.dev|netlify\.app|ts\.net)$/;

let enabled = false;

/** Inject gtag.js and start the command queue. Call once at startup. */
export function initAnalytics(): void {
  if (enabled || NON_PRODUCTION_HOST.test(window.location.hostname)) return;

  window.dataLayer = window.dataLayer || [];
  window.gtag = function () {
    // gtag.js requires the Arguments object itself, not a spread array.
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer!.push(arguments);
  };
  window.gtag('js', new Date());
  // SPA: the default snippet only records the first page, so page_view is sent
  // manually on every route change instead (PageTracker in App.tsx).
  window.gtag('config', GA_ID, { send_page_view: false, content_group: 'orchestraplatform' });

  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
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
