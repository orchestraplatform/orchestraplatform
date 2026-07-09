import { afterEach, describe, expect, it, vi } from 'vitest';

// analytics.ts only touches window/document inside its functions, so minimal
// stubs are enough — no jsdom needed. Each test re-imports the module via
// vi.resetModules() to reset its `enabled` state.

interface StubScript {
  src?: string;
  async?: boolean;
}

function stubDom(config?: { gaMeasurementId?: string }) {
  const appended: StubScript[] = [];
  const win = {
    __ORCHESTRA_CONFIG__: config,
    location: { origin: 'https://app.example.org' },
  } as unknown as Window & typeof globalThis;
  vi.stubGlobal('window', win);
  vi.stubGlobal('document', {
    title: 'Orchestra - Workshop Management',
    createElement: () => ({}) as StubScript,
    head: { appendChild: (el: StubScript) => appended.push(el) },
  });
  return { win, appended };
}

async function loadAnalytics() {
  vi.resetModules();
  return await import('./analytics');
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('analytics', () => {
  it('is completely inert when no measurement ID is configured', async () => {
    const { win, appended } = stubDom();
    const { initAnalytics, track } = await loadAnalytics();

    initAnalytics();
    track('workshop_launch', { template_slug: 'jupyter' });

    expect(appended).toHaveLength(0);
    expect(win.gtag).toBeUndefined();
    expect(win.dataLayer).toBeUndefined();
  });

  it('injects gtag.js and queues events when the ID is set', async () => {
    const { win, appended } = stubDom({ gaMeasurementId: 'G-TEST123' });
    const { initAnalytics, track } = await loadAnalytics();

    initAnalytics();

    expect(appended).toHaveLength(1);
    expect(appended[0].src).toBe('https://www.googletagmanager.com/gtag/js?id=G-TEST123');
    expect(appended[0].async).toBe(true);

    track('workshop_launch', { template_slug: 'jupyter', replace_existing: false });

    const calls = win.dataLayer!.map((a) => Array.from(a as IArguments));
    expect(calls[0][0]).toBe('js');
    // Manual SPA page views: the config call must disable the automatic one.
    expect(calls[1]).toEqual(['config', 'G-TEST123', { send_page_view: false }]);
    expect(calls[2]).toEqual([
      'event',
      'workshop_launch',
      { template_slug: 'jupyter', replace_existing: false },
    ]);
  });

  it('trackPageView sends page_view with path and title', async () => {
    const { win } = stubDom({ gaMeasurementId: 'G-TEST123' });
    const { initAnalytics, trackPageView } = await loadAnalytics();

    initAnalytics();
    trackPageView('/templates');

    const last = Array.from(win.dataLayer![win.dataLayer!.length - 1] as IArguments);
    expect(last).toEqual([
      'event',
      'page_view',
      {
        page_path: '/templates',
        page_title: 'Orchestra - Workshop Management',
        page_location: 'https://app.example.org/templates',
      },
    ]);
  });

  it('initAnalytics is idempotent', async () => {
    const { appended } = stubDom({ gaMeasurementId: 'G-TEST123' });
    const { initAnalytics } = await loadAnalytics();

    initAnalytics();
    initAnalytics();

    expect(appended).toHaveLength(1);
  });
});
