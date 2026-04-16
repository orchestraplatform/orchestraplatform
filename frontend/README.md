# Orchestra Frontend

React + TypeScript dashboard for the Orchestra monorepo.

## Features

- **Template Catalog**: Browse curated workshop templates
- **Instance Management**: Launch, view, and terminate workshop sessions
- **Real-time Updates**: Live status monitoring with React Query
- **Modern UI**: Built with TailwindCSS and shadcn/ui components
- **Type Safety**: Full TypeScript support
- **Responsive Design**: Works on desktop and mobile devices

## Quick Start

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

3. **Open browser**: Navigate to `http://localhost:3000`

## Development

### Environment Variables

Create a `.env.local` file:

```env
VITE_API_URL=http://localhost:8080
```

Use `http://localhost:8080` when running the full monorepo from the root via
`just dev`. If you run the API directly with `cd server && just dev`, use
`http://localhost:8000` instead.

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix linting issues
- `npm run format` - Format code with Prettier
- `npm run type-check` - Run TypeScript checks
- `npm run test` - Run tests

### Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Base UI components
│   ├── workshop/       # Workshop-specific components
│   └── layout/         # Layout components
├── pages/              # Page components
├── hooks/              # Custom React hooks
├── utils/              # Utility functions
├── api/generated/      # OpenAPI-generated client
└── App.tsx             # Main application component
```

## Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Docker

Build the container:

```bash
docker build -t orchestra-frontend .
```

Run the container:

```bash
docker run -p 80:80 orchestra-frontend
```

## Integration with Orchestra API

The frontend communicates with the Orchestra API backend. Make sure the API is running and accessible at the configured `VITE_API_URL`.

### API Endpoints Used

- `GET /auth/me`
- `GET /auth/auth-config`
- `GET /workshops/`
- `GET /workshops/{template_id}`
- `POST /workshops/{template_id}/launch`
- `GET /instances/`
- `DELETE /instances/{k8s_name}`
- `GET /health/`
- `GET /health/ready`

## Authentication

Authentication is handled by oauth2-proxy at ingress. In local dev, the API can
run in a dev-identity bypass mode and the frontend surfaces that state via the
`/auth/auth-config` endpoint.
