# Orchestra Platform Documentation

[![Built with Starlight](https://astro.badg.es/v2/built-with-starlight/tiny.svg)](https://starlight.astro.build)
[![Netlify Status](https://api.netlify.com/api/v1/badges/60e9ed33-676c-4e4c-84ab-7980d564e880/deploy-status)](https://app.netlify.com/projects/orchestraplatform-docs/deploys)

This repository contains the documentation for the Orchestra Platform, built with [Astro](https://astro.build/) and [Starlight](https://starlight.astro.build/).

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

### Netlify Deployment

This site is configured for automatic deployment to Netlify:

1. **Connect Repository**: Link your GitHub repository to Netlify
2. **Build Settings**: 
   - Build command: `npm run build`
   - Publish directory: `dist`
   - Node version: 18
3. **Custom Domain**: Configure `docs.orchestraplatform.org` as a custom domain
4. **SSL**: Netlify will automatically provision SSL certificates

### Manual Build

```bash
npm run build
```

The built site will be in the `dist/` directory.

```bash
netlify deploy --prod
```

will deploy the site to production. 

### Custom Domain Setup

To configure `docs.orchestraplatform.org`:

1. **In Netlify Dashboard**:
   - Go to Site settings → Domain management
   - Add custom domain: `docs.orchestraplatform.org`
   - You'll probably need to verify ownership via DNS TXT record or email verification.

2. **DNS Configuration**:
   - Add a CNAME record in your DNS provider:
   ```
   docs.orchestraplatform.org → YOUR_NETLIFY_SITE.netlify.app
   ```

3. **SSL Certificate**:
   - Netlify will automatically provision a Let's Encrypt SSL certificate
   - Your site will be available at `https://docs.orchestraplatform.org`
   - In some cases like with Cloudflare, it will handle SSL certificates automatically.

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

All commands are run from the root of the project, from a terminal:

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Installs dependencies                            |
| `npm run dev`             | Starts local dev server at `localhost:4321`      |
| `npm run build`           | Build your production site to `./dist/`          |
| `npm run preview`         | Preview your build locally, before deploying     |
| `npm run astro ...`       | Run CLI commands like `astro add`, `astro check` |
| `npm run astro -- --help` | Get help using the Astro CLI                     |
| `netlify deploy --prod`   | Deploy the site to production on Netlify         |

## 👀 Want to learn more?

Check out [Starlight’s docs](https://starlight.astro.build/), read [the Astro documentation](https://docs.astro.build), or jump into the [Astro Discord server](https://astro.build/chat).
