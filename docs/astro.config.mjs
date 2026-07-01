import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
const googleAnalyticsId = 'G-KLLV1GCF4E';

export default defineConfig({
  site: 'https://orchestraplatform.org',
  integrations: [
    starlight({
      title: 'Orchestra Platform',
      description:
        'Documentation for the Orchestra Platform - Bioinformatics and Data Science Learning Environment',
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
      // Audience: people who deploy, operate, and build Orchestra
      // (installers, instance maintainers, developers) — not workshop end-users.
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            {
              label: 'Introduction',
              link: '/docs/getting-started/introduction/',
            },
            {
              label: 'Installation',
              link: '/docs/getting-started/installation/',
            },
          ],
        },
        {
          label: 'Deploying Orchestra',
          items: [
            {
              label: '1. Overview & prerequisites',
              link: '/docs/deployment/overview/',
            },
            {
              label: '2. Cluster setup (GKE Standard)',
              link: '/docs/deployment/cluster-setup/',
            },
            {
              label: '3. Install Orchestra (Helm)',
              link: '/docs/deployment/install/',
            },
            {
              label: '4. Ingress, TLS & auth',
              link: '/docs/deployment/ingress-tls-auth/',
            },
            { label: '5. DNS cutover', link: '/docs/deployment/dns-cutover/' },
            { label: '6. CI/CD', link: '/docs/deployment/github-cicd/' },
            {
              label: '7. Troubleshooting & gotchas',
              link: '/docs/deployment/troubleshooting/',
            },
          ],
        },
        {
          label: 'Deployment reference',
          items: [
            { label: 'Helm chart values', link: '/docs/deployment/helm/' },
            {
              label: 'Ingress controllers',
              link: '/docs/deployment/ingress/',
            },
            { label: 'oauth2-proxy', link: '/docs/deployment/oauth2-proxy/' },
            {
              label: 'GCP Autopilot (legacy)',
              link: '/docs/deployment/gcp/',
            },
          ],
        },
        {
          label: 'Operating an Instance',
          items: [
            {
              label: 'Configuring Workshop Images',
              link: '/docs/user-guide/configuring-images/',
            },
            {
              label: 'Authoring Workshop Templates',
              link: '/docs/user-guide/authoring-workshop-templates/',
            },
          ],
        },
        {
          label: 'Architecture',
          items: [
            {
              label: 'Platform Overview',
              link: '/docs/architecture/platform-overview/',
            },
            {
              label: 'Domain Structure',
              link: '/docs/architecture/domain-structure/',
            },
            { label: 'Data Model', link: '/docs/architecture/data-model/' },
            {
              label: 'Authentication',
              link: '/docs/architecture/authentication/',
            },
            {
              label: 'Authorization',
              link: '/docs/architecture/authorization/',
            },
          ],
        },
        {
          label: 'API Reference',
          items: [
            { label: 'REST API', link: '/docs/api/rest-api/' },
            { label: 'CRD Reference', link: '/docs/api/crds/' },
          ],
        },
        {
          label: 'Development',
          items: [
            {
              label: 'Local Development',
              link: '/docs/development/local-development/',
            },
            { label: 'Contributing', link: '/docs/development/contributing/' },
            { label: 'Testing', link: '/docs/contributing/testing/' },
          ],
        },
        {
          label: 'Architecture Decision Records',
          items: [
            {
              label: 'ADR-0001: oauth2-proxy at ingress',
              link: '/docs/adr/0001-oauth2-proxy-at-ingress/',
            },
            {
              label: 'ADR-0002: spec.owner on CRD',
              link: '/docs/adr/0002-spec-owner-on-crd/',
            },
            {
              label: 'ADR-0003: Helm install method',
              link: '/docs/adr/0003-helm-as-install-method/',
            },
            {
              label: 'ADR-0004: Template/instance split',
              link: '/docs/adr/0004-template-instance-split/',
            },
            {
              label: 'ADR-0005: GKE Standard tenant pools',
              link: '/docs/adr/0005-gke-standard-tenant-pools/',
            },
            {
              label: 'ADR-0006: YAML workshop templates',
              link: '/docs/adr/0006-yaml-workshop-templates/',
            },
            {
              label: 'ADR-0007: External workshop-templates repo',
              link: '/docs/adr/0007-external-template-repo/',
            },
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
        '127.0.0.1',
      ],
    },
  },
});
