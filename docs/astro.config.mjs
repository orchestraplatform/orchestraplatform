import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
const googleAnalyticsId = 'G-KLLV1GCF4E';

export default defineConfig({
  site: 'https://orchestraplatform.org',
  integrations: [
    starlight({
      title: 'Orchestra Platform',
      description: 'Documentation for the Orchestra Platform - Bioinformatics and Data Science Learning Environment',
      customCss: ['./src/styles/custom.css'],
      head: [
        // Adding google analytics
        {
          tag: 'script',
          attrs: {
            src: `https://www.googletagmanager.com/gtag/js?id=${googleAnalyticsId}`,
          },
        },
        {
          tag: 'script',
          content: `
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());

          gtag('config', '${googleAnalyticsId}');
          `,
        },
      ],
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/seandavi/orchestra-operator',
        },
      ],
      // Docs live under /docs (the apex root is the marketing landing page).
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Introduction', link: '/docs/getting-started/introduction/' },
            { label: 'Installation', link: '/docs/getting-started/installation/' },
          ],
        },
        {
          label: 'Architecture',
          items: [
            { label: 'Platform Overview', link: '/docs/architecture/platform-overview/' },
            { label: 'Domain Structure', link: '/docs/architecture/domain-structure/' },
            { label: 'Data Model', link: '/docs/architecture/data-model/' },
            { label: 'Components', link: '/docs/architecture/components/' },
            { label: 'Authentication', link: '/docs/architecture/authentication/' },
            { label: 'Authorization', link: '/docs/architecture/authorization/' },
          ],
        },
        {
          label: 'User Guide',
          items: [
            { label: 'Creating Workshops', link: '/docs/user-guide/creating-workshops/' },
            { label: 'Managing Workshops', link: '/docs/user-guide/managing-workshops/' },
            { label: 'Configuring a Workshop Image', link: '/docs/user-guide/configuring-images/' },
          ],
        },
        {
          label: 'API Reference',
          items: [
            { label: 'REST API', link: '/docs/api/rest-api/' },
            { label: 'Kubernetes CRDs', link: '/docs/api/crds/' },
          ],
        },
        {
          label: 'Deployment',
          items: [
            { label: 'Helm Install', link: '/docs/deployment/helm/' },
            { label: 'Ingress Controller Guide', link: '/docs/deployment/ingress/' },
            { label: 'GCP Autopilot', link: '/docs/deployment/gcp/' },
            { label: 'oauth2-proxy Setup', link: '/docs/deployment/oauth2-proxy/' },
          ],
        },
        {
          label: 'Contributing',
          items: [
            { label: 'Testing Guide', link: '/docs/contributing/testing/' },
            { label: 'Contributing', link: '/docs/development/contributing/' },
            { label: 'Local Development', link: '/docs/development/local-development/' },
          ],
        },
        {
          label: 'Architecture Decision Records',
          items: [
            { label: 'ADR-0001: oauth2-proxy at ingress', link: '/docs/adr/0001-oauth2-proxy-at-ingress/' },
            { label: 'ADR-0002: spec.owner on CRD', link: '/docs/adr/0002-spec-owner-on-crd/' },
            { label: 'ADR-0003: Helm install method', link: '/docs/adr/0003-helm-as-install-method/' },
            { label: 'ADR-0004: Template/instance split', link: '/docs/adr/0004-template-instance-split/' },
          ],
        },
      ],
    }),
  ],
  vite: {
    server: {
      host: true,
      allowedHosts: [
        'dev-docs.orchestraplatform.org',
        'docs.orchestraplatform.org',
        'localhost',
        '127.0.0.1'
      ],
    },
  },
});
