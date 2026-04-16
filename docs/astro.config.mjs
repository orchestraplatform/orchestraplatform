import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
const googleAnalyticsId = 'G-KLLV1GCF4E';

export default defineConfig({
  site: 'https://docs.orchestraplatform.org',
  integrations: [
    starlight({
      title: 'Orchestra Platform',
      description: 'Documentation for the Orchestra Platform - Bioinformatics and Data Science Learning Environment',
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
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Introduction', link: '/getting-started/introduction/' },
            { label: 'Installation', link: '/getting-started/installation/' },
          ],
        },
        {
          label: 'Architecture',
          items: [
            { label: 'Platform Overview', link: '/architecture/platform-overview/' },
            { label: 'Domain Structure', link: '/architecture/domain-structure/' },
            { label: 'Data Model', link: '/architecture/data-model/' },
            { label: 'Components', link: '/architecture/components/' },
            { label: 'Authentication', link: '/architecture/authentication/' },
            { label: 'Authorization', link: '/architecture/authorization/' },
          ],
        },
        {
          label: 'User Guide',
          items: [
            { label: 'Creating Workshops', link: '/user-guide/creating-workshops/' },
            { label: 'Managing Workshops', link: '/user-guide/managing-workshops/' },
          ],
        },
        {
          label: 'API Reference',
          items: [
            { label: 'REST API', link: '/api/rest-api/' },
            { label: 'Kubernetes CRDs', link: '/api/crds/' },
          ],
        },
        {
          label: 'Deployment',
          items: [
            { label: 'Helm Install', link: '/deployment/helm/' },
            { label: 'oauth2-proxy Setup', link: '/deployment/oauth2-proxy/' },
          ],
        },
        {
          label: 'Contributing',
          items: [
            { label: 'Testing Guide', link: '/contributing/testing/' },
            { label: 'Contributing', link: '/development/contributing/' },
            { label: 'Local Development', link: '/development/local-development/' },
          ],
        },
        {
          label: 'Architecture Decision Records',
          items: [
            { label: 'ADR-0001: oauth2-proxy at ingress', link: '/adr/0001-oauth2-proxy-at-ingress/' },
            { label: 'ADR-0002: spec.owner on CRD', link: '/adr/0002-spec-owner-on-crd/' },
            { label: 'ADR-0003: Helm install method', link: '/adr/0003-helm-as-install-method/' },
            { label: 'ADR-0004: Template/instance split', link: '/adr/0004-template-instance-split/' },
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
