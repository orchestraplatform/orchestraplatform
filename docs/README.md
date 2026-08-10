# Orchestra Platform Documentation

[![Built with Starlight](https://astro.badg.es/v2/built-with-starlight/tiny.svg)](https://starlight.astro.build)

This directory contains the public site for the Orchestra Platform, built with [Astro](https://astro.build/) and [Starlight](https://starlight.astro.build/). It serves the apex landing page (`src/pages/index.astro`) and the docs under `/docs`. The authenticated app lives at `app.orchestraplatform.org` and is deployed separately to GKE.

## 🚀 Quick Start

### Prerequisites

- Node.js 18 or higher  
- npm or yarn

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

This starts the development server at `http://localhost:4321`.

## 🚀 Deployment

The site is a Cloudflare Worker serving static assets — Astro builds to `docs/dist` and Cloudflare serves it directly (no Worker script, no Astro Cloudflare adapter). Configuration lives in [`wrangler.jsonc`](../wrangler.jsonc) at the **repo root**, not in this directory, because Workers Builds runs from the repo root in this monorepo.

Deploys are automatic: Workers Builds is connected to the GitHub repo and rebuilds on push. Pushes to `main` publish to production; other branches produce preview deployments, so PRs touching this directory get a preview URL in their checks.

- Build command: `cd docs && npm ci && npm run build`
- Deploy command: `npx wrangler deploy` (reads the root `wrangler.jsonc`)
- Assets directory: `docs/dist`
- Custom domain: `orchestraplatform.org` (apex). `app.` and `api.` stay on GKE.

### Manual build and deploy

```bash
npm run build          # from docs/ — output lands in docs/dist
npx wrangler deploy    # from the repo root
```

Prefer letting Workers Builds handle production; a manual `wrangler deploy` publishes whatever is in your local `docs/dist`, which may not match `main`.

### Analytics

The GA4 measurement ID is hardcoded in two places that must stay in sync: `astro.config.mjs` and `src/pages/index.astro`. There is no env/secret wiring — rotate the property by editing both.

## 📁 Project Structure

Inside of your Astro + Starlight project, you'll see the following folders and files:

```
.
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   ├── content/
│   │   └── docs/
│   └── content.config.ts
├── astro.config.mjs
├── package.json
└── tsconfig.json
```

Starlight looks for `.md` or `.mdx` files in the `src/content/docs/` directory. Each file is exposed as a route based on its file name.

Images can be added to `src/assets/` and embedded in Markdown with a relative link.

Static assets, like favicons, can be placed in the `public/` directory.

## 🧞 Commands

All commands are run from this `docs/` directory, from a terminal:

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Installs dependencies                            |
| `npm run dev`             | Starts local dev server at `localhost:4321`      |
| `npm run build`           | Build your production site to `./dist/`          |
| `npm run preview`         | Preview your build locally, before deploying     |
| `npm run astro ...`       | Run CLI commands like `astro add`, `astro check` |
| `npm run astro -- --help` | Get help using the Astro CLI                     |

## 👀 Want to learn more?

Check out [Starlight’s docs](https://starlight.astro.build/), read [the Astro documentation](https://docs.astro.build), or jump into the [Astro Discord server](https://astro.build/chat).
