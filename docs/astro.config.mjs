import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
const googleAnalyticsId = 'G-KLLV1GCF4E';

export default defineConfig({
  site: 'https://orchestraplatform.org',
  // Keep old URLs resolving after the persona reorg (issue #67). Sibling of
  // `integrations`, NOT inside starlight().
  redirects: {
    // Testing moved from the stray `contributing/` dir into `development/`.
    '/docs/contributing/testing/': '/docs/development/testing/',
  },
  integrations: [
    starlight({
      title: 'Orchestra Platform',
      description:
        'Documentation for the Orchestra Platform - Bioinformatics and Data Science Learning Environment',
      customCss: ['./src/styles/custom.css'],
      components: {
        // Default the docs to dark, matching the marketing site (see the file).
        ThemeProvider: './src/components/ThemeProvider.astro',
      },
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
          href: 'https://github.com/orchestraplatform',
        },
      ],
      // Docs live under /docs (the apex root is the marketing landing page).
      // Two realms: "Using Orchestra" (the hosted platform at
      // orchestraplatform.org — no cluster, no shell) and "Running Orchestra"
      // (deploy, administer, and develop your own instance — kubectl/Helm/just).
      // The split keeps admin/self-host commands out of the common visitor path.
      sidebar: [
        {
          label: 'Using Orchestra',
          items: [
            {
              label: 'Using a Workshop',
              items: [
                {
                  label: 'Using a Workshop Session',
                  link: '/docs/participant/using-a-session/',
                },
              ],
            },
            {
              label: 'Contribute a Workshop',
              items: [
                { label: 'Overview', link: '/docs/contribute/overview/' },
                {
                  label: 'Build a Bioconductor workshop',
                  link: '/docs/contribute/build-bioc-workshop/',
                },
                {
                  label: 'Bring your own container',
                  link: '/docs/contribute/bring-your-own-container/',
                },
                {
                  label: 'Make the image Orchestra-ready',
                  link: '/docs/user-guide/configuring-images/',
                },
                {
                  label: 'Author a workshop template',
                  link: '/docs/user-guide/authoring-workshop-templates/',
                },
                { label: 'Submit it', link: '/docs/contribute/submit/' },
              ],
            },
            {
              label: 'Teach a Workshop',
              items: [
                {
                  label: 'Planning & Teaching a Workshop',
                  link: '/docs/host/running-an-event/',
                },
              ],
            },
          ],
        },
        {
          label: 'Running Orchestra',
          items: [
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
              label: 'Administer & Operate',
              items: [
                {
                  label: 'Operating a Workshop Event',
                  link: '/docs/operate/workshop-events/',
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
                { label: 'Testing', link: '/docs/development/testing/' },
              ],
            },
            {
              label: 'Decision Records',
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
                {
                  label: 'ADR-0008: Cluster provisioning boundary',
                  link: '/docs/adr/0008-cluster-provisioning-boundary/',
                },
                {
                  label: 'ADR-0009: Template submission front door',
                  link: '/docs/adr/0009-template-front-door/',
                },
                {
                  label: 'ADR-0010: Per-(user, workshop) persistent workspace',
                  link: '/docs/adr/0010-persistent-workspace/',
                },
              ],
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
