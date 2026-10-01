import { afterEach, describe, expect, it, vi } from 'vitest';

// analytics.ts only touches window/document inside its functions, so minimal
// stubs are enough — no jsdom needed. Each test re-imports the module via
// vi.resetModules() to reset its `enabled` state.

interface StubScript {
  src?: string;
  async?: boolean;
}

function stubDom(hostname = 'app.orchestraplatform.org') {
  const appended: StubScript[] = [];
  const win = {
    location: { hostname, origin: `https://${hostname}` },
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
  it.each(['localhost', '127.0.0.1', '10.0.0.5', 'orchestra.example.workers.dev', 'box.tail1.ts.net'])(
    'is completely inert on non-production host %s',
    async (host) => {
      const { win, appended } = stubDom(host);
      const { initAnalytics, track } = await loadAnalytics();

      initAnalytics();
      track('workshop_launch', { template_slug: 'jupyter' });

      expect(appended).toHaveLength(0);
      expect(win.gtag).toBeUndefined();
      expect(win.dataLayer).toBeUndefined();
    },
  );

  it('injects gtag.js and queues events on the production host', async () => {
    const { win, appended } = stubDom();
    const { initAnalytics, track } = await loadAnalytics();

    initAnalytics();

    expect(appended).toHaveLength(1);
    expect(appended[0].src).toBe('https://www.googletagmanager.com/gtag/js?id=G-KLLV1GCF4E');
    expect(appended[0].async).toBe(true);

    track('workshop_launch', { template_slug: 'jupyter', replace_existing: false });

    const calls = win.dataLayer!.map((a) => Array.from(a as IArguments));
    expect(calls[0][0]).toBe('js');
    // Manual SPA page views: the config call must disable the automatic one.
    expect(calls[1]).toEqual([
      'config',
      'G-KLLV1GCF4E',
      { send_page_view: false, content_group: 'orchestraplatform' },
    ]);
    expect(calls[2]).toEqual([
      'event',
      'workshop_launch',
      { template_slug: 'jupyter', replace_existing: false },
    ]);
  });

  it('trackPageView sends page_view with path and title', async () => {
    const { win } = stubDom();
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
        page_location: 'https://app.orchestraplatform.org/templates',
      },
    ]);
  });

  it('initAnalytics is idempotent', async () => {
    const { appended } = stubDom();
    const { initAnalytics } = await loadAnalytics();

    initAnalytics();
    initAnalytics();

    expect(appended).toHaveLength(1);
  });
});
